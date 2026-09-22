<!-- ontology-5axis
problem: depth
representation: n/a
sensor: mono
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# 几何崩塌：当视觉模型无法验证物理因果性 (Geometric Collapse: When Vision Models Fail to Verify Physical Causality)

> **发布时间**：2026-07-08（arXiv:2607.06871v1 [cs.CV]）
> **论文 / 模型名**：Geometric Collapse（诊断协议名 **Scrambled Edges**）
> **核心定位**：这是一篇**诊断/证伪型**论文，不是新模型。它用能量匹配的对照实验证明：CNN/ViT/SSL 深度预测器会把"视觉显著但物理上无支撑"的边缘线索当作真实几何结构吸收，并由此引发**全局**几何崩塌——模型对高频噪声鲁棒，却不等于对假边缘鲁棒。

本文的痛点是评测盲区：现代单目深度模型在标准的全局像素指标上越来越准，但没人问一个更尖锐的问题——当一条强边缘与基本物理结构冲突时，模型会**否决**它，还是把它**折进**几何预测？答案是后者，而且后果是场景级的。

---

## X-Ray 开场

深度模型看到一条强边缘（高对比、边界感强），会默认"这是真实几何边界"直接吸收，而不检查它是否满足连续性 / 光照一致 / 遮挡因果。作者构造 **Scrambled Edges**：把真实边缘段搬走、旋转、压暗，保持视觉显著但破坏物理可解释性。结果是模型输出**全局性**崩塌（而非局部伪影），且**全局像素精度指标反而变好**（因为输出被平滑了）。对 spatial AI 研究者的意义：**大规模 SSL 与 scaling 不会自动涌现"物理验证"能力**，评测必须换成边界感知指标 + 显式上界（oracle 修复天花板）。

---

## 📍 研究全景时间线

```
经典视觉 (Gibson/Marr, 1979-82)      物理正则 → 感知需尊重物理规律
        │
ImageNet-C (2019) / 频率敏感性研究     鲁棒性 = 对统计噪声的鲁棒
        │
SSL 单目深度 (Godard 2017)            用光度/左右一致性隐式编码几何约束
        │
MiDaS 系列 / DPT (2020-2021)          大规模混合数据 → 精度飙升
        │
DepthAnything v1/v2 (2024)            规模化 SSL + DINOv2，benchmark SOTA
        │
        ▼
★ Geometric Collapse (2026)  ← 本文：把"精度"换成"物理验证"，发现负涌现
        │                         噪声鲁棒 ≠ 边缘鲁棒；误差全局扩散；
        │                         局部 oracle 修复仅恢复 47%
        ▼
【本文局限】只做行为级诊断，不训练新模型；只覆盖 edge→geometry 这一条捷径；
  perturbation 是合成干预而非真实相机退化；无真机/延迟数据
```

---

## 1 · 核心架构 / 方法总览

本文没有网络结构。它的"系统"是一套**对照实验管线**：扰动注入 + 两类控制组 + 三套度量。

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| **Scrambled Edges（主扰动）** | 图像 I，Canny 边缘段 E={e₁..e_K} | I_scram = clip(I − α·M_scram, 0, 1) | 纯推理期干预，无训练 |
| **High-pass Noise（频率控制）** | 图像 I，高斯白噪声 ε | I_noise = clip(I + (ε − G_σ(ε)), 0, 1) | 能量 RMS 逐图匹配到 Scrambled Edges |
| **Edge-Shaped Noise（结构控制）** | 同一批边缘掩码 M_edge | I_edge = I + Noise(M_edge) | 原地加噪，不搬/不旋转 → 保留边缘形状但无几何违反 |
| **False Edge Ratio / G-Score** | 边缘掩码 + GT 深度 D_gt | R_false / G-Score | 需 GT 深度（仅诊断期） |
| **Oracle Repair（溢出测量）** | D_clean, D_scram, M_scram | D_patch = D_scram·(1−M_scram) + D_clean·M_scram | 用已知扰动掩码做上界修复 |
| **多视图一致性（KITTI）** | 相邻帧 RGB + 位姿 + 预测深度 | 光度 ℓ₁ / depth–depth 相对误差 | 固定内参与位姿 T_{t→t+1} |

### 1.2 关键机制

**⚡ Eureka Moment：把"假边缘"和"高频噪声"解耦**——用能量匹配（energy-matched）和结构匹配（structure-matched）两组对照，第一次让"物理无支撑"成为可控变量，从而证明崩塌来自**因果违反**而非频率或边缘密度。

三个物理先验（prior）与其违反操作一一对应（论文 Table 1）：

| 操作 | 图像级改变 | 违反的支撑信号 |
|---|---|---|
| Translation | 边缘被放到几何光滑区 | 表面连续性（depth gradient alignment） |
| Darkening | 对比度无光照来源 | 光照一致（chromatic signature） |
| Rotation | 重新定向后 junction 几何不兼容 | 遮挡顺序（T-junction 代理） |

实验结论（机制阶梯）：**结构本身无害**（Edge-Shaped 1.0×–1.7×），**因果违反主导**（Direction 扰动最强）。

### 1.3 信息流 ASCII 图

```
        clean image I
             │
     ┌───────┼───────────────┬──────────────────┐
     ▼       ▼               ▼                  ▼
  Scrambled  High-pass    Edge-Shaped       (clean 基线)
  Edges      Noise        Noise
     │        │               │                  │
     └────────┴───────┬───────┴──────────────────┘
                      ▼
             Depth model (MiDaS / DA v1/v2)
                      │
        ┌─────────────┼─────────────┬───────────────┐
        ▼             ▼             ▼               ▼
  RMSE_Δ        Edge F1       Oracle Repair    多视图一致性
  Collapse      (结构)        (溢出上界)       (KITTI 光度/深度)
  Ratio
        │
        ▼
   诊断结论：物理支撑验证缺席 → 假边缘被吸收 → 全局崩塌
```

---

## 2 · 数学核心

📌 **Napkin Formula**：
```
Collapse Ratio = RMSE_Δ,scram / RMSE_Δ,noise
```
一句话直觉：**同样的高频能量，换成"假边缘"后模型输出偏离自身干净预测多少倍**——这个比值越大，说明模型越是在"验证几何"而不是"检测高频"。

**① 扰动生成**
目标：构造视觉显著但物理不可解释的边缘。
```
I_scram = clip(I − α · M_scram, 0, 1),   M_scram = ⋃_k T_k(e_k)
θ_k ~ U(−60°, +60°),  t_k ~ U(−0.25W, +0.25W)×U(−0.25H, +0.25H)
```
- `α`：扰动强度（默认 α=0.8）
- `K`：取面积最大的 K 个连通边缘段（默认 K=15，NYU 上覆盖 ~36%）
- `T_k`：仿射变换（旋转 + 平移），使边缘脱离原物理支撑

**② 能量匹配控制**
```
σ_n = RMS(I_scram − I) / RMS(ε − G_σ(ε)),  G_σ = σ=5 px 高斯模糊
```
- 先算单位方差噪声的高通 RMS 分母，再逐图缩放 σ_n，使 `RMS(I_noise − I) ≈ RMS(I_scram − I)`
- 直觉：把"能量"这个混杂因子钉死，只留"物理支撑"这一个变量

**③ 物理支撑度量（G-Score）**
```
R_false = Σ(M_edge · 𝟙(|∇D_gt| < τ)) / Σ M_edge,   G-Score = 1 − R_false
```
- `τ` = NYU 上 |∇D_gt| 的中位数（"几何光滑"阈值）
- G-Score 越高 = 边缘越可能对应真实深度不连续

**④ 溢出 / 修复上界**
```
D_patch = D_scram·(1 − M_scram) + D_clean·M_scram
```
- 若误差纯局部，D_patch 应等于 D_clean；残留误差 = 全局溢出（spillover）

---

## 3 · 带数字走一遍（玩具设定，非论文真值）

**玩具场景**：一张 100×100 图，模型对干净图输出 `D_clean`。注入一条假边缘。

设能量匹配后，高频噪声带来的偏差 `RMSE_Δ,noise = 0.02`。

**情形 A（模型鲁棒）**：假边缘只让输出偏离 `RMSE_Δ,scram = 0.02` → Collapse Ratio = **1.0×**（把假边缘当噪声，正确否决）。

**情形 B（几何崩塌）**：假边缘被当作真边界吸收，偏差 `RMSE_Δ,scram = 0.064` → Collapse Ratio = **3.2×**（论文里 DepthAnything V2 的实测数量级）。

**溢出上界玩具推导**：假设扰动掩码 `M_scram` 覆盖全图 36%。模型把假边缘"传染"成一片幻影墙，误差扩散到掩码外的 64% 区域。
- 理想局部修复（oracle 换回 D_clean）：只能盖住掩码内误差；
- 若掩码外误差占总误差的比例为 `p`，则修复恢复率上界 `= 1 − p`。
- 论文实测该上界约 **47%**（即即便知道掩码位置，仍有大半误差躺在掩码外）。

结论（玩具口吻）：**掩码内修得再好，掩码外的幻影墙修不掉**——这就是 spillover 的硬天花板。

---

## 4 · 工程视角

| 维度 | 论文报告情况 |
|---|---|
| 延迟 / FPS | 「论文未报告」 |
| 显存 / VRAM | 「论文未报告」 |
| 硬件型号 | 「论文未报告」 |
| 吞吐 / 步数 | 「论文未报告」（仅定性说"protocol 计算成本 moderate，主要是现有深度模型的标准前向 + 轻量图像扰动"） |
| 部署约束 trade-off | 论文提及：采用该诊断应报告 compute / model size / energy，尤其评估大型生成式深度估计器时；建议**有选择地**作为鲁棒性审计的一环，而非大规模压测 |

可提取的定性工程约束：
- 该协议是**推理期干预**，成本 ≈ 一次额外前向 + 掩码合成，无重训练。
- 生成式模型（Marigold / DepthFM）需要**多次迭代去噪**，推断成本显著高于一次性回归器——这解释了它们"崩塌更弱"的部分来源，但也让它们"更贵"。
- 论文明确反对用数据增强硬扛：增强只教会"对这种扰动模式不变"，教不会"为什么这条边缘可信"。

---

## 5 · 数据与评测

**数据集**（逐字来自全文）：
- **NYU Depth v2 labeled set**（Silberman et al., 2012），**N = 1449** RGB-D pairs（主实验）
- **KITTI Odometry**（Geiger et al., 2012），Seq 00/02/05，**750 frame pairs**（多视图一致性验证）
- **KITTI**（附录 B.2 跨数据集验证，报告 ~2.1× collapse）

**模型**（逐字）：
- MiDaS v2.1 (CNN)、MiDaS DPT (ViT)、DepthAnything v1 (SSL)、DepthAnything V2（DINOv2 pretraining）
- 跨范式补充：Marigold（diffusion）、DepthFM（flow-matching）
- 跨任务对照：SAM（语义分割）

**指标**（逐字）：
- `RMSE_Δ`：扰动预测 vs 干净预测的 RMSE（注意：不是 vs GT）
- `Collapse Ratio = RMSE_Δ,scram / RMSE_Δ,noise`
- `Recovery = 1 − RMSE_defended / RMSE_undefended`
- Edge F1（结构指标）、G/P/O-Score、多视图光度 ℓ₁ 与 depth–depth 相对误差

**主结果数字**（逐字，NYU，N=1449，Table 2，按 high-pass noise 归一）：
| 条件 | MiDaS v2.1 | MiDaS DPT | DA v1 | DA V2 |
|---|---|---|---|---|
| High-pass Noise（基线） | 1.00× | 1.00× | 1.00× | 1.00× |
| Edge-Shaped（结构） | 1.00× | 1.31× | 1.01× | 1.71× |
| Mask-Matched（位置） | 0.58× | 0.60× | 0.43× | 0.53× |
| Darkening（光照） | 0.85× | 1.06× | 1.09× | 1.95× |
| T-Junctions（局部遮挡） | 0.73× | 1.07× | 1.08× | 2.00× |
| Position（连续性） | 1.22× | 1.68× | 1.68× | 3.15× |
| Direction（因果） | 1.86× | 2.22× | 1.99× | 3.18× |
| **Scrambled Edges（全）** | **1.88×** | **2.34×** | **2.02×** | **3.20×** |

**跨范式**：Marigold **1.55×**（Cohen's d = 0.88）；DepthFM **1.11×**（d = 0.25）。

**采纳率 vs 强度**（MiDaS DPT, NYU, Appendix Table 10）：α=0.2 → 采纳 6.2%、崩塌 1.37×；α=0.6 → 采纳 24.7%、崩塌 2.02×；α=0.8 → 采纳 36.1%、崩塌 2.34×。

**多视图指标悖论**（KITTI Odometry, Table 3，逐字）：
| 模型 | 光度 Clean | Δs | Δn | Depth Consist. Clean | Δs | Δn |
|---|---|---|---|---|---|---|
| DA V2 (L) | 0.1537 | +0.1% | +0.2% | 148.4 | −12.9% | −20.6% |
| MiDaS (ViT) | 0.1705 | −2.3% | −1.7% | 160.2 | +88.9% | +21.9% |
| MiDaS (CNN) | 0.1267 | −3.3% | −5.1% | 512.0 | +410.1% | +865.2% |

**单视图指标悖论**（NYU, N=1449, Table 4，逐字）：
| 模型 | GT-RMSE Clean | Scram | Edge F1 Clean | Scram | F1 Drop |
|---|---|---|---|---|---|
| MiDaS v2.1 (CNN) | 2.19 | 1.45 | 0.195 | 0.105 | 46.4% |
| MiDaS DPT (ViT) | 2.72 | 2.17 | 0.289 | 0.141 | 51.3% |
| DA v1 (SSL) | 4.29 | 3.53 | 0.364 | 0.187 | 48.8% |
| DA V2 | 4.08 | 3.51 | 0.392 | 0.131 | 66.7% |

> 注意：GT-RMSE（median-scaling 后，单位米）在 Scrambled Edges 下**变小**（如 MiDaS v2.1 从 2.19 降到 1.45），而 Edge F1 崩塌。这正是"全局指标误导"的核心证据。

`论文未报告`：G-Score/P-Score/O-Score 的具体数值（正文只说在 Appendix Table 15，未给出数字）。

---

## 6 · 能力与失败模式

**能做（诊断能力）**：
- 分离"高频能量"与"物理支撑违反"两个变量（能量匹配 + 结构匹配双对照）。
- 定位主导先验：**遮挡因果（Direction / T-junction）> 连续性（Position）> 光照（Darkening）**。
- 量化溢出上界：oracle 掩码修复仅恢复 ~47%（abstract）。
- 跨数据集（KITTI ~2.1×）、跨任务（SAM 无差异敏感）、跨范式（diffusion/flow-matching 衰减但显著）验证。

**不能做（模型的失败模式，逐条可推导）**：
1. **缺物理因果验证**：模型不做显式 plausibility 检查，直接吸收显著边缘。
2. **噪声鲁棒 ≠ 边缘鲁棒**：模型在高频噪声下稳定，在假边缘下崩塌（SSL paradox）。
3. **误差全局扩散**：局部修复有硬天花板（spillover）。
4. **指标失效**：全局 GT-RMSE 可"变好"，边界指标才暴露崩塌（metric paradox）。
5. **多视图也骗人**：光度重投影误差可下降，而 depth–depth 一致性误差暴涨（+410%/+865% on MiDaS CNN）。
6. **正常估计比深度更脆**：法向 ∝ ∇D，对梯度破坏更敏感（Fig. 5）。
7. **V2 反向悖论**：精度越高，对先验违反越敏感（>3.0×）。

### 隐含假设 (Hidden Assumptions)

- **假设 GT 深度可得**：G-Score / R_false 依赖 `D_gt` 与阈值 `τ`（NYU 上 |∇D_gt| 中位数）。部署时无 GT → 该度量**不可在线使用**。
- **假设"物理支撑"可由三个代理先验充分刻画**：连续性 / 光照一致 / 遮挡因果被论文自认"不是完整物理引擎"，只是保守代理。
- **假设 Canny 边缘能代表"显著边缘证据"**：方法依赖 Canny + top-K by area，低纹理场景边缘稀疏时，扰动本身失效。
- **假设能量匹配是可比的**：`RMS(I_noise − I) ≈ RMS(I_scram − I)` 是全局 RMS，忽略空间分布差异。
- **假设扰动是诊断而非真实退化**：论文明确 Scrambled Edges 是合成干预，与真实 reflection/shadow/glass 的分布不完全一致（仅靠 long-tail 子集定性连接）。
- **假设"行为级无验证"= "表征级无验证"**：论文自陈只说 observable behavior，不做表征不可行性断言。

---

## 7 · 与相关工作对比

| 工作 | 干预对象 | 对照方式 | 核心结论 |
|---|---|---|---|
| ImageNet-C (2019) | 统计退化 | 无物理对照 | 鲁棒性 = 抗统计损坏 |
| 频率敏感性分析 (Yin 2019, Wang 2020) | 频段 | 频率匹配 | 模型依赖特定频率 |
| 对抗 patch (Brown 2018) | 优化模式 | 无能量匹配 | 易碎但不可解释 |
| 自监督深度一致性 (Godard 2017) | 训练目标 | 光度/左右一致 | 训练期编码几何约束 |
| **本文** | **可解释边缘证据** | **能量匹配 + 结构匹配** | **推理期无物理验证 → 几何崩塌** |

与数据集/评测类工作（Nugent 2025 深度扰动、Hu 2018 边界保真）的区别：本文不做"更全的损坏集"，而是把"物理无支撑"这一个变量**孤立**出来。

> **面试 Tip**：被问"这篇和普通鲁棒性论文有什么区别？"——答："它不是又加了一类噪声。它用**能量匹配对照**把'高频能量'钉死，用**结构匹配对照**把'边缘形状'钉死，剩下的唯一变量就是'这条边缘是否有物理支撑'。结论是模型在噪声下稳、在假边缘下崩，而且崩的是全场不是局部——所以局部 inpainting 修复有 47% 的硬上限。这也解释了为什么全局 RMSE 会'变好'而 Edge F1 崩掉。"

---

## 8 · GitHub-validated pitfalls（atlas 联动, 2026-09-22）

**repo 状态**：论文正文/摘要未给出任何 `github.com` 链接（仅出现 arXiv 页面自带的 "Report GitHub Issue" UI 元素，非作者仓库信号）。因此**判定为无 repo 信号**。以下 pitfall 由 §6 失败模式 + §3/§4 方法约束推导，**未经 issue 验证**。

1. **边缘稀疏场景下扰动失效**（推导自 §6.3 + §3.1）
   - 方法约束：Scrambled Edges 取 `top-K=15 connected components by area`，依赖 Canny 在图上显著边缘。
   - 失败模式：在低纹理图（白墙、天空）Canny 返回极少/细小边缘 → K=15 时面积排序退化，掩码覆盖远低于报告的 ~36% → 采纳率低 → 崩塌被低估。复现时若不对每图检查 "有效边缘数 ≥ K"，会得到与论文不一致的 Collapse Ratio。

2. **能量匹配在近零分母图像上不稳定**（推导自 §3.2 + §4.1）
   - 方法约束：`σ_n = RMS(I_scram − I) / RMS(ε − G_σ(ε))` 逐图计算，分母是单位方差噪声的高通 RMS。
   - 失败模式：若某图 Scrambled Edges 掩码近乎为空（见 pitfall 1），`RMS(I_scram − I) → 0`，则 σ_n → 0，High-pass Noise 基线退化为"无扰动"，`RMSE_Δ,noise → 0`，导致 Collapse Ratio 数值爆炸（除零放大）。工程上必须对该比值设下限或跳过该图。

3. **G-Score 阈值跨数据集不可迁移**（推导自 §3.3 + §6.Hidden Assumptions）
   - 方法约束：`τ` = NYU 上 `|∇D_gt|` 的中位数，G-Score = 1 − R_false。
   - 失败模式：在 KITTI（室外、尺度/梯度分布不同）上直接复用 NYU 的 τ，会把大量合法的远景/稀疏深度梯度判为"光滑"，使 G-Score 系统性偏低，误判扰动"更无支撑"。跨数据集复现必须重算 τ，否则 cross-dataset 结论（~2.1×）不可比。

4. **生成式模型的"较弱崩塌"被误读为"更安全"**（推导自 §4.1 cross-paradigm + §5.6）
   - 方法约束：Marigold 1.55×（d=0.88）、DepthFM 1.11×（d=0.25）仍是统计显著崩塌。
   - 失败模式：只看 Collapse Ratio 数值小就判定"diffusion 提供了物理验证"是误用——论文明确 iterative inference 只是"delayed commitment"，不构成显式 support-aware cue selection。把 DepthFM 的 1.11× 当成"已解决"会掩盖其 d=0.25 背后仍存在的假边缘采纳。

---

[← Back to Depth Estimation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（截断版）· 未在真机复现的数字标 `UNVERIFIED`（本笔记中 §4 全部工程数字均为「论文未报告」，未做任何估算填充；§3 玩具数字为示范设定）

<!-- source: https://arxiv.org/abs/2607.06871 -->
