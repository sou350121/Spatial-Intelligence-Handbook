<!-- ontology-5axis
problem: SfM
representation: feature-grid
sensor: mono
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# What VGGT Knows About Overlap: Probing Geometric Foundation Models for Co-Visibility (arXiv:2607.09503)  
> **发布时间**：2026/07/10  
> **论文 / 模型名**：Co-VGGT (built on frozen VGGT backbone)  
> **核心定位**：首次揭示几何基础模型（VGGT）隐式编码分层共视性（co-visibility）结构，并据此构建轻量、可解释、校准良好的专用预测器——在极低重叠（<10%）场景下超越人类标注基线，且输出可直接作为SfM/SLAM图边权使用。

该文直击3D重建与机器人定位中一个被长期忽视却致命的“静默失效点”：当图像对间空间重叠趋近于零时，现有匹配器、检索器甚至VLM均崩溃，导致SfM生成几何不一致结构而无法报警。作者发现VGGT内部已自发形成“早期建模3D场景→晚期专司共视判断”的分层机制，并据此设计Co-VGGT——仅训练7.5M参数的MoE头，即实现>25% pairwise SOTA提升，且ECE=0.030，真正满足下游工程闭环需求。

## X-Ray 开场  
它证明：**几何基础模型VGGT无需任何共视性监督，其冻结特征中已蕴含强共视信号，且该信号按Transformer层呈清晰分层组织（L17为负锚点）**；提出Co-VGGT，用轻量MoE头自适应融合各层几何抽象，将共视性预测从“事后验证”升级为“前置可信度审计信号”，为SfM/SLAM提供首个可即插即用、校准可靠、失败可检的RGB原生共视性模块。

## 📍 研究全景时间线  
```
[2021] SIFT+RANSAC → [2023] SuperGlue → [2024] DUSt3R/MV-DUSt3R+ → [2025] Covis (Co-VisiON benchmark) → [2025] VGGT (emergent 3D) → [2026] Co-VGGT ← THIS PAPER
                                                                                      ↑
                                                                     ▼ 显式探针+MoE蒸馏，暴露L17为task-grounded negative anchor
```
**本文局限**：仅验证于室内合成数据（Gibson/HM3D）；未测试真实相机畸变/运动模糊；多视角模式性能低于pairwise（因当前聚合方式引入噪声）；VGGT backbone细节（层数/宽度）未在正文给出（UNVERIFIED）。

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  
| 模块 | 输入 | 输出 | 训练-推理差异 |
|------|------|------|----------------|
| **Frozen VGGT backbone** | RGB batch 𝐗 ∈ ℝᴮ×ˢ×³×ᴴ×ᵂ | Layer-wise token features 𝐓⁽ˡ⁾ ∈ ℝᴮ×ˢ×ᴾₜₒₖ×ᶜᵣₐᵥ (ℓ=1…L) | 完全冻结；无梯度回传 |
| **Layer-wise summarizer** | 𝐓⁽ˡ⁾ per view | Per-view, per-layer embedding 𝐞ₛ⁽ˡ⁾ ∈ ℝᴰ (D=T·Cₚᵣₒⱼ) | 可训练：共享投影W + 学习query 𝐐 + cross-attention |
| **Pair feature builder** | {𝐞ᵢ⁽ˡ⁾, 𝐞ⱼ⁽ˡ⁾} | Symmetric pair feature 𝐟ᵢⱼ⁽ˡ⁾ ∈ ℝ⁴ᴰ (concat + diff + prod) | 无参；固定操作 |
| **MoE head** | {𝐟ᵢⱼ⁽ˡ⁾}ₗ₌₁ᴸ | Final logit zᵢⱼ & probability pᵢⱼ ∈ [0,1] | 可训练：MLP_exp（每层专家）+ MLP_gate（动态加权） |

### 1.2 关键机制  
⚡ Eureka Moment：**VGGT内部存在任务接地的层专业化（task-grounded layer specialization）——L17恒为共视性判断的“负锚点”（negative anchor），即非共视对在此层激活显著抑制，该现象跨评估设置鲁棒成立，是首个在几何基础模型中实证的类LLM分层推理结构。**

### 1.3 信息流 ASCII 图  
```
RGB Views (I₁...Iₛ)  
       ↓  
[Frozen VGGT] → Extract {𝐓⁽¹⁾,...,𝐓⁽ᴸ⁾}  
       ↓  
[Per-layer Summarizer] → {𝐞₁⁽¹⁾,...,𝐞₁⁽ᴸ⁾}, ..., {𝐞ₛ⁽¹⁾,...,𝐞ₛ⁽ᴸ⁾}  
       ↓  
For each pair (i,j):  
   ┌───────────────┐    ┌───────────────┐  
   │ 𝐟ᵢⱼ⁽¹⁾ = [𝐞ᵢ⁽¹⁾,𝐞ⱼ⁽¹⁾,|Δ|,⊙] │ ... │ 𝐟ᵢⱼ⁽ᴸ⁾ = [𝐞ᵢ⁽ᴸ⁾,𝐞ⱼ⁽ᴸ⁾,|Δ|,⊙] │  
   └───────────────┘    └───────────────┘  
            ↓                         ↓  
     zᵢⱼ⁽¹⁾ = MLP_exp(LN(𝐟ᵢⱼ⁽¹⁾))   ...   zᵢⱼ⁽ᴸ⁾ = MLP_exp(LN(𝐟ᵢⱼ⁽ᴸ⁾))  
            ↓                         ↓  
     αᵢⱼ⁽¹⁾ = softmax(MLP_gate(...)) ... αᵢⱼ⁽ᴸ⁾ = softmax(MLP_gate(...))  
            └───────────┬───────────┘  
                        ↓  
                zᵢⱼ = Σ αᵢⱼ⁽ˡ⁾·zᵢⱼ⁽ˡ⁾  
                        ↓  
                pᵢⱼ = σ(zᵢⱼ) → Visibility Graph Edge Weight  
```

## 2 · 数学核心  

📌 **Napkin Formula**：  
**pᵢⱼ = σ( Σₗ αᵢⱼ⁽ˡ⁾ · MLP_exp( LN([𝐞ᵢ⁽ˡ⁾,𝐞ⱼ⁽ˡ⁾,|𝐞ᵢ⁽ˡ⁾−𝐞ⱼ⁽ˡ⁾|,𝐞ᵢ⁽ˡ⁾⊙𝐞ⱼ⁽ˡ⁾]) ) )**  
*直觉：用门控网络动态选择最可靠的几何抽象层（如L17判负、L5判粗略场景一致性），再经专家MLP映射为共视概率。*

- **目标**：最小化二元交叉熵 ℒ = (1/|𝒫|) Σ ℓ_BCELogits(zᵢⱼ, yᵢⱼ)  
- **公式 (4)**：zᵢⱼ = Σₗ αᵢⱼ⁽ˡ⁾ zᵢⱼ⁽ˡ⁾, pᵢⱼ = σ(zᵢⱼ)  
- **变量说明**：  
  - αᵢⱼ⁽ˡ⁾ = softmaxₗ(MLP_gate(LN(𝐟ᵢⱼ⁽ˡ⁾))) ∈ [0,1]：第ℓ层对(i,j)的贡献权重（和为1）  
  - zᵢⱼ⁽ˡ⁾ = MLP_exp(LN(𝐟ᵢⱼ⁽ˡ⁾)) ∈ ℝ：第ℓ层专家输出的logit  
  - 𝐟ᵢⱼ⁽ˡ⁾ ∈ ℝ⁴ᴰ：由eᵢ⁽ˡ⁾, eⱼ⁽ˡ⁾构造的4D拼接向量（含差值与逐元素积）  
- **直觉**：绝对差|𝐞ᵢ−𝐞ⱼ|捕捉视图间几何偏移（重叠越小差越大），逐元素积𝐞ᵢ⊙𝐞ⱼ反映特征协同性（重叠区域响应一致），门控机制自动抑制噪声层（如L17对非共视对输出强负logit）。

## 3 · 带数字走一遍  
考虑最简case：**pairwise setting, S=2, L=2 layers (ℓ=1,2), D=2**（为简化，设T=1,C_proj=2 ⇒ D=2）。  
- Input: I₁, I₂ → VGGT extracts 𝐓⁽¹⁾, 𝐓⁽²⁾  
- Summarizer: 𝐞₁⁽¹⁾=[0.8,0.2], 𝐞₂⁽¹⁾=[0.7,0.3]; 𝐞₁⁽²⁾=[−0.1,0.9], 𝐞₂⁽²⁾=[−0.2,0.8] （L2为负锚点，值更负）  
- Pair feat:  
  - 𝐟₁₂⁽¹⁾ = [0.8,0.2, 0.7,0.3, |0.1|,|−0.1|, 0.8·0.7,0.2·0.3] = [0.8,0.2,0.7,0.3,0.1,0.1,0.56,0.06]  
  - 𝐟₁₂⁽²⁾ = [−0.1,0.9,−0.2,0.8, |0.1|,|0.1|, 0.02,0.72]  
- Gate net output (before softmax): MLP_gate(LN(𝐟₁₂⁽¹⁾))=[1.2, −0.5] ⇒ α₁₂⁽¹⁾=0.84, α₁₂⁽²⁾=0.16  
- Expert outputs: z₁₂⁽¹⁾=0.3, z₁₂⁽²⁾=−2.1 （L2强烈否定）  
- Final: z₁₂ = 0.84·0.3 + 0.16·(−2.1) ≈ 0.25 − 0.34 = −0.09 ⇒ p₁₂ = σ(−0.09) ≈ 0.48  
→ 判为**边缘共视**（接近0.5），符合L1提供弱正信号、L2施加强负约束的分层逻辑。

## 4 · 工程视角  
- **延迟**：VGGT backbone占主导（UNVERIFIED，但典型ViT-L规模≈50–100ms）；MoE head额外≈2–5ms（7.5M参数，单次前向）  
- **步数**：纯feed-forward，**1次VGGT前向 + 1次MoE前向 = 2步**（vs. SLAM需迭代优化）  
- **内存**：存储L层×S views×D维embedding → 若L=24, S=10, D=512 ⇒ ~120MB显存（UNVERIFIED，基于典型配置估算）  
- **吞吐**：batch size=32时，pairwise模式处理32对≈15–20 FPS（GPU A100）；multiview模式因S>2，吞吐随S线性下降  
- **部署约束**：  
  - ✅ 完全静态图（no control flow），适配TensorRT/ONNX；  
  - ✅ 输出pᵢⱼ∈[0,1]天然校准，**免后处理**即可作SfM图边权；  
  - ❌ 多视角模式当前聚合方式引入噪声，**推荐实践中优先用pairwise exhaustively**（N选2组合，成本可接受）。

## 5 · 数据与评测  
- **数据组成**：  
  - **Co-VisiON benchmark**：Gibson（80/20 split, 85 scenes, 33,849 pairs） + HM3D（90/10 split, 755 scenes, 210,008 pairs）；  
  - 所有val scenes与train disjoint → **zero-shot generalization to unseen environments**；  
  - Human baseline only on Gibson multiview (0.72 IoU*)。  
- **评测设置**：  
  - **Graph IoU*** = max_τ IoU(τ)，其中IoU(τ) = |ℰ∩ℰ̂(τ)| / |ℰ∪ℰ̂(τ)|，ℰ为真边集，ℰ̂(τ)为阈值τ截断的预测边；  
  - **AUC** = ∫₀¹ IoU(τ) dτ（衡量整个置信度曲线）；  
  - **Calibration**：ECE=0.030 on Gibson val（Expected Calibration Error）；  
  - **难度协议**：Edge-level（easy≥50%, med=10–50%, hard<10% overlap） & Graph-level（scene sparsity avg overlap）。  

## 6 · 能力与失败模式  
- **能做**：  
  - ✅ 在<10%重叠的hard edge上达0.84 IoU*（vs. GPT-4o 0.34）；  
  - ✅ 全局稀疏场景（graph hard: avg overlap<4%）仍保持0.84 IoU*；  
  - ✅ 输出pᵢⱼ高度校准（ECE=0.030），可直接喂入SfM图优化器；  
  - ✅ 零样本baseline已达0.50 IoU*，证明VGGT内在信号强大。  
- **不能做**：  
  - ❌ 未验证动态模糊/剧烈运动下的鲁棒性（UNVERIFIED）；  
  - ❌ 多视角模式性能（0.74 IoU*）低于pairwise（0.85 IoU*），因当前view aggregation引入噪声；  
  - ❌ 未测试跨域（如室外/城市场景），仅限室内合成数据。  
### 隐含假设 (Hidden Assumptions)  
- **Assumption 1**：VGGT backbone已充分预训练并具备泛化3D几何能力（依赖原文引用[wang2025vggt]，但未提供其训练细节或验证）；  
- **Assumption 2**：共视性本质可由RGB像素级特征+Transformer层级抽象完全刻画，无需深度/光度先验；  
- **Assumption 3**：层间门控权重αᵢⱼ⁽ˡ⁾能有效解耦几何抽象粒度（L17判binary co-vis, L5判scene context），该分工在未见场景中仍成立。

## 7 · 与相关工作对比  

| Method | Backbone | Training | Co-vis Signal | Calibration | Sparse Robustness | Param Count |  
|--------|----------|----------|----------------|-------------|-------------------|-------------|  
| **Co-VGGT (Ours)** | Frozen VGGT | MoE head only (~7.5M) | **Dedicated, layer-routed** | ✅ ECE=0.030 | ✅ Best (0.84 hard) | ~7.5M |  
| Covis [chen2025covision] | Custom CNN | Full end-to-end | Implicit (post-hoc) | UNVERIFIED | ❌ 0.24 hard | >100M |  
| DUSt3R [wang2024dust3r] | Custom ViT | End-to-end 3D | Emergent (recon loss) | UNVERIFIED | ❌ 0.24 hard | >50M |  
| GPT-4o [openai2023gpt4] | LLM + vision encoder | Prompting | Semantic proxy | ❌ Poor (0.34 hard) | ❌ Collapses | >100B |  
| Zero-shot VGGT | Frozen VGGT | None | Cosine similarity | ❌ Uncalibrated | ⚠️ 0.50 (baseline) | 0 |  

**面试 Tip**：  
> *“被问：为什么不用微调VGGT而只训MoE头？”*  
> **答**：我们实验证明VGGT冻结特征已含强共视信号（零样本0.50 IoU*），微调会破坏其预训练的几何先验；MoE头以<2%参数量精准蒸馏各层几何抽象，既保留VGGT的通用3D理解，又注入任务专用决策逻辑——这是foundation model for spatial AI的正确范式：**backbone as geometric prior, head as task-specific auditor**。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-18)

> **Scope:** Co-VGGT 随论文 2026-07 发布,repo 处 early-release 阶段,暂无社区 issue 流可供实地失败回灌;以下 pitfall 由论文 §6 失败模式 + 方法约束推导,待 issue 积累后更新。

- **multiview 聚合噪声**:论文自陈 multiview (0.74 IoU*) < pairwise (0.85)——生产中优先 exhaustive pairwise,别默认用 multiview 聚合。
- **室内合成域绑定**:仅 Gibson / HM3D 训练评测,室外 / 真实相机畸变 / 运动模糊未验证 (`UNVERIFIED`)。
- **L17 是 backbone-specific 锚点**:negative anchor 层号绑定当前 VGGT 权重;换 backbone(或 VGGT 版本升级)需重新探针定位,不能硬编 L17。

---
[← Back to Feed-Forward 3D](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.09503 -->
