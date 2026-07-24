<!-- ontology-5axis
problem: n/a
representation: BEV
sensor: mono
paradigm: generative
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# Action Map Policy: Learning 3D Closed-loop Manipulation via Pixel Classification  
> **发布时间**：2026/07/12  
> **论文 / 模型名**：Action Map Policy (AMP)  
> **核心定位**：将3D闭环操作策略学习重构为**多视图图像平面上的像素级分类问题**，以规避连续高维动作空间离散化导致的组合爆炸，同时保留毫米级精度与多模态分布建模能力——比Diffusion Policy快、比Regression方法准、比Token-based方法更几何一致。

该文直击机器人策略学习中长期存在的“动作表征诅咒”：传统回归易坍缩均值、扩散模型需多步采样、离散token化引发维度灾难。AMP用一张像素热图（heatmap）替代一个6-DoF向量，让策略在图像空间里“看哪动哪”，首次实现**单次前向即输出全时序动作分布**，且天然支持激光点等细粒度视觉线索响应。

---

## 📍 X-Ray 开场  
AMP解决的是**3D闭环操作策略中高维连续动作空间难以高效、精确、多模态表征**的根本性瓶颈；它提出将末端执行器轨迹编码为多相机视角下的**时空关键点热图（spatiotemporal keypoint heatmaps）**，把策略学习降维为像素级分类任务；对 spatial AI 研究者而言，这意味着：**动作不再是抽象向量，而是可解释、可定位、可微分、可equivariant增强的图像结构**——策略真正“扎根于像素”。

---

## 📍 研究全景时间线  
```
[2020] ACT (regression + CVAE) → [2022] OAT (action tokenization) → [2023] DiffPo (diffusion over action tokens)  
                                     ↓  
                      [2024] Motion Track (diffused 2D keypoints)  
                                     ↓  
[2026] AMP ←─ "pixel-as-class" paradigm shift: dense heatmap classification in multi-view image space  
         │  
         └── 局限：依赖精确相机标定；仅支持固定抓取构型（5-keypoint gripper geometry）；未开放真实世界部署延迟数据
```

---

## ## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **X-Net backbone** | `n`张 `(H×W×3)` 多视图RGB图像（含1张in-hand + 2张side-view） | `n×l×m` 张 `(H×W)` 软热图（每张对应某相机、某时间步、某关键点） | 训练：端到端监督热图；推理：无变化，但需后处理 triangulation |
| **Heatmap predictor ψ** | X-Net encoder-decoder + Multi-View Transformer (MVT) | `𝐡̂_ijk ∈ ℝ^{H×W}`（归一化概率分布） | 全程使用 cross-entropy loss；无迭代采样 |
| **Action extractor f** | `{argmax(𝐡̂_ijk)}` → `(u,v)_ijk` 像素坐标 | `𝒜_t = {(T_i, R_i, w_i)}_{i=1..l}`（l步6-DoF动作序列） | **仅推理阶段启用**；训练中完全不参与，纯监督在热图空间 |

### 1.2 关键机制  
**⚡ Eureka Moment：**  
> **“不 discretize action space — instead, project 3D action trajectories onto camera image planes and treat each pixel as a class; the action is then a distribution over pixels across time and views.”**  
即：放弃在欧氏空间离散动作，转而在图像空间定义动作——每个像素是潜在动作终点的几何投影锚点，热图即动作概率密度，分类即动作选择。

### 1.3 信息流 ASCII 图  

```
[Multi-view RGB]  
     │  
     ▼  
U-Net Encoder → Flatten + PosEnc → Multi-View Transformer (MVT)  
     │                              ↗ (in-image attn)  
     │                            ↙ (cross-view attn)  
     ▼  
U-Net Decoder (w/ skip conn)  
     │  
     ▼  
[Side-view heatmaps: H×W×(l×m)]  
     │  
     ▼  
argmax → {(u,v)_ijk} → Triangulation 𝒯 → {p^j_i ∈ ℝ³}  
     │                             │  
     │                             ▼  
     │                     T_i = centroid(p¹..p⁴)  
     │                     R_i = Gram-Schmidt(v_antipodal, v_approach)  
     │                     w_i = d₊/(d₊+d₋)  
     ▼  
[Executable action chunk 𝒜_t = {(T_i,R_i,w_i)}]
```

---

## ## 2 · 数学核心  

📌 **Napkin Formula**：  
> **Action = Triangulation ∘ argmax ∘ softmax ∘ X-Net(Observation)**  
> *→ policy lives entirely in image space; geometry is recovered only at inference.*

**目标**：最小化热图预测与软标签之间的交叉熵，隐式学习3D动作在图像平面的投影分布。

**公式**：  
\[
\mathcal{L}_{\mathrm{CE}} = -\sum_{i=1}^{l}\sum_{j=1}^{m}\sum_{k=1}^{n}\sum_{u,v} \underbrace{\mathbf{h}_{ijk}(u,v)}_{\text{Gaussian soft label}} \cdot \log \underbrace{\hat{\mathbf{h}}_{ijk}(u,v)}_{\text{network output}}
\]

**变量说明**：  
- `l`：动作chunk长度（文中=12，执行取前8）  
- `m`：关键点数（固定=5：4个抓取点 + 1个宽度指示点）  
- `n`：相机数（实验=2 side-view，in-hand仅用于输入，不输出热图）  
- `h_{ijk}(u,v)`：第`i`步、第`j`个关键点、在第`k`个相机下的`(u,v)`像素处的高斯软标签（σ=2）  
- `ĥ_{ijk}`：网络预测的归一化热图（softmax over H×W）

**直觉**：  
损失函数不关心3D坐标本身，只惩罚“像素级投影偏差”。只要网络学会把正确3D动作映射到正确像素簇，triangulation自然恢复毫米级精度——**几何约束被编码在相机模型中，而非网络参数中**。

---

## ## 3 · 带数字走一遍（玩具示例）  

设：  
- 单侧相机 `H=W=224`, `l=1`, `m=1`, `n=1`（简化）  
- 真实3D关键点 `p = [0.3, 0.1, 0.5]^T m`，经内参 `K=[300,0,112; 0,300,112; 0,0,1]` 投影得 `u=112+0.3*300=202`, `v=112+0.1*300=142`  
- 软标签 `h(u,v)` 是以 `(202,142)` 为中心、σ=2 的2D高斯，在 `224×224` 网格上归一化  
- 网络输出 `ĥ` 在 `(202,142)` 处概率为 `0.08`，邻域 `(201,142)` 为 `0.06`，其余≈0  
- 则 CE loss ≈ `-0.08·log(0.08) ≈ 0.19`（主导项）；若预测偏移至 `(205,142)`，高斯衰减使 `h(205,142)≈0.02` → loss ≈ `-0.02·log(0.08)≈0.03`，但因 `h` 在该点本就小，实际梯度仍驱动回归中心  

→ **单步误差<1px ⇒ 3D重建误差≈1mm（见Table 1）**，验证像素精度到3D精度的线性映射关系。

---

## ## 4 · 工程视角  

| 维度 | 值 | 来源说明 |
|------|----|----------|
| **推理延迟** | `论文未报告` | 全文未提FPS/latency/hardware；仅称“substantially faster inference than diffusion policies”（定性） |
| **内存占用** | `论文未报告` | 未给出VRAM/params；X-Net含ResBlocks+MVT，但无具体规模描述 |
| **吞吐量** | `论文未报告` | 无batch size/FPS数据 |
| **步数开销** | **1 forward pass** | 明确对比Diffusion Policy需“multiple denoising steps”；AMP为feed-forward（ontology confirm） |
| **部署约束** | **需已知相机内外参** | triangulation依赖 `𝒯`，要求标定矩阵；未提在线标定或自标定模块 |
| **硬件依赖** | `论文未报告` | 未指定GPU型号/边缘设备适配性 |

✅ **Trade-off总结**：  
- ✅ 换来：单次前向、天然多模态、像素级可解释性、equivariant data augmentation友好  
- ❌ 付出：严格依赖标定质量；热图分辨率直接决定3D精度（无法超分）；`argmax` 引入量化误差（虽小但存在）

---

## ## 5 · 数据与评测  

| 项目 | 内容 | 来源确认 |
|------|------|----------|
| **仿真数据集** | **MimicGen**（6 tasks: `stack-three-d1`, `hammer-cleanup-d1`, `mug-cleanup-d1`, `coffee-d2`, `square-d2`, `threading-d2`） | ✅ 全文明确：“evaluate on six representative tasks from MimicGen [23]” |
| **真实世界数据** | 自建UR5+Gello平台；Dual RealSense D455（side）+ 1 in-hand cam；任务：`making-coffee`, `toast-bread`, `steam-egg`（截断前已列出） | ✅ “We conduct five real-world experiments… UR5 arm equipped with dual in-hand cameras… RealSense D455” |
| **评测指标** | **Success Rate (%)**（50 unseen tests per task） | ✅ Table 2标题：“Success rate (mean%) over 50 unseen tests” |
| **基线方法** | Diffusion Policy [3], ACT [43], OAT [22], Motion Track [30] | ✅ Section 4.2 “Baseline”段落逐条列出 |
| **训练样本量** | **100 demonstration episodes** | ✅ Table 2脚注：“100 Demo” & text：“with 100 demonstration episodes used for training” |

⚠️ 注意：所有 success rate 数字（如 `AMP: 90` on `stack-three-d1`）均**逐字复制自Table 2**，未四舍五入、未推断。

---

## ## 6 · 能力与失败模式  

### ✅ 能力  
- **毫米级3D精度**：224×224下达 `1.00±0.09 mm` 平移误差（Table 1）  
- **强空间敏感性**：能响应激光点等亚像素视觉线索（Intro段明确对比Diffusion Policy“largely ignores it”）  
- **多模态建模**：cross-entropy loss天然拟合多峰动作分布（e.g., multiple valid coffee-pod insertion paths）  
- **跨视图一致性**：MVT强制side-view间特征对齐，避免Motion Track的独立预测漂移（Section 4.2）  

### ❌ 不能做  
- **动态背景/运动模糊鲁棒性未验证**：全文未提动态场景测试，所有实验基于静态/慢速操作  
- **未知相机标定下的zero-shot泛化**：依赖 `𝒫, 𝒯` 精确逆变换；Table 1 footnote承认“imperfect calibration introduces small offsets”但未量化鲁棒边界  
- **非标准夹爪泛化**：关键点设计绑定5-point gripper geometry（Fig 3），未测试其他末端执行器  

### ### 隐含假设 (Hidden Assumptions)  
1. **静态 scene geometry**：triangulation假设所有相机观测同一刚体3D点，不支持动态形变物体（如布料、液体）  
2. **已知且固定 camera extrinsics**：MVT输入需预对齐特征，未提供在线外参估计或自适应模块  
3. **Gripper kinematics is rigid & known**：`v_antipodal`, `v_approach` 轴计算依赖4个抓取点的固定相对构型（“Points p¹–p⁴ are arranged in a fixed relative configuration”）  
4. **Pixel correspondence is unambiguous**：单像素可能对应多个3D点（depth ambiguity），但AMP未建模深度不确定性，全靠triangulation from ≥2 views resolve  

---

## ## 7 · 与相关工作对比  

| 方法 | 动作表征 | 训练目标 | 推理方式 | 多模态 | 几何一致性 |  
|--------|-----------|------------|-------------|----------|----------------|  
| **AMP (Ours)** | 2D heatmap over multi-view | Cross-entropy | **Single forward pass** | ✅ Explicit distribution | ✅ Triangulation-enforced |  
| Diffusion Policy [3] | Tokenized 6-DoF actions | Denoising objective | Iterative sampling (≥10 steps) | ✅ Implicit | ❌ No geometric constraint on tokens |  
| ACT [43] | Continuous 6-DoF vector | MSE regression | Single forward | ❌ Collapses to mean | ✅ Direct output |  
| OAT [22] | Discrete action tokens | Cross-entropy | Autoregressive token gen | ✅ | ❌ Token vocab loses geometry |  
| Motion Track [30] | Diffused 2D keypoint coords | Score matching | Per-view denoising → triangulate | ✅ | ⚠️ Independent per-view → inconsistent trajectories |  

**面试 Tip**：  
> *“被问‘为什么不用Diffusion？’时，答：AMP不是拒绝生成式建模，而是重构生成空间——把‘生成动作’变成‘生成像素分布’。这带来三重红利：(1) 推理从O(N)步降到O(1)；(2) 分布显式可查（热图即置信度）；(3) 几何先验由相机模型硬编码，比学习score field更鲁棒。代价是需要标定，但这是机器人系统的合理前提。”*

---

## ## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-24)  

🔍 **官方 repo 未在论文中给出**：全文无 `github.com` 链接（arXiv PDF中仅出现“Report GitHub Issue”按钮UI文字，非有效URL）；作者主页 `haojhuang.github.io/amp_page` 未嵌入代码库链接。  
→ **以下 pitfall 由 §6 失败模式 + 方法约束推导（未经 issue 验证）**：

1. **❌ ONNX export failure due to dynamic triangulation**  
   - *Derivation*: §6 隐含假设要求 `𝒯`（triangulation）作为确定性算子；但标准ONNX不支持SVD-based triangulation（需 `torch.linalg.svd`），而AMP原文Appendix 6.3 pseudocode含 `triangulate_from_multiple_views()` 调用；  
   - *Failure mode*: §6 “Known camera extrinsics” 假设被违反时，ONNX runtime无法fallback，export中断。

2. **❌ Real-time closed-loop stall under motion blur**  
   - *Derivation*: §6 “Static scene geometry” 假设 + §4.3 real-world实验仅含慢速操作；motion blur使 `argmax` 定位偏移 >1px → Table 1显示224×224下1px≈1mm，偏移直接导致3D误差超标；  
   - *Method constraint*: 网络无显式运动补偿模块（unlike VIO/SLAM），热图预测基于单帧，无时序建模。

3. **❌ Multi-object occlusion failure when in-hand view missing**  
   - *Derivation*: Table 3显示移除in-hand相机后 `coffee-d2` success ↓14%；§6 “fixed relative configuration” 假设要求4抓取点可见，但occlusion时 `argmax` 可能选错像素簇；  
   - *Method constraint*: X-Net decoder仅输出side-view热图，in-hand view纯作encoder输入，无热图监督，故丢失该视角的像素级动作锚点。

---

[← Back to manipulation README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.10706 -->
