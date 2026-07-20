<!-- ontology-5axis
problem: SfM
representation: feature-grid
sensor: mono
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# 什么是 VGGT 所知的重叠：面向共视性探测的几何基础模型 (What VGGT Knows About Overlap: Probing Geometric Foundation Models for Co-Visibility)  
> **发布时间**：2026/07/10  
> **论文 / 模型名**：Co-VGGT（基于 VGGT 的共视性探测器）  
> **核心定位**：首次揭示 VGGT 冻结特征中隐含分层共视性信号，并构建仅需 7.5M 参数的 MoE 头，实现 RGB-only、零微调 backbone 的共视性预测，在 Co-VisiON 上 pairwise 超 SOTA 25%、multiview 超 10%，且输出概率高度校准（ECE=0.030），可直接作为 SfM/SLAM 可信边权使用。  

该文直击稀疏视角下 3D 重建失败的核心症结——共视性（co-visibility）无法可靠判定：传统 pipeline 将其隐式处理，导致在低重叠场景中“静默崩溃”；而现有学习模型（SuperGlue、DUSt3R 等）或混淆语义相似与几何重叠，或依赖强重叠假设。本文发现 VGGT 的冻结表征天然编码共视性结构，并据此设计轻量、可解释、即插即用的 Co-VGGT，使共视性成为重建前可审计的第一类信号。

## X-Ray 开场  
它解决“如何在无显式监督、不修改 backbone 的前提下，从单目 RGB 中鲁棒提取图像对是否共享可见表面区域”这一根本问题；提出了 Co-VGGT —— 一个冻结 VGGT + 层级 MoE head 的架构，将 transformer 各层视为几何抽象粒度不同的专家；对 spatial AI 研究者意味着：几何基础模型的内部表征可被系统性探针解耦为任务专用信号，无需重训 backbone 即可蒸馏出高保真空间先验，为 SfM/SLAM 提供可插入的“可信重叠审计模块”。

## 📍 研究全景时间线  
```
[2021] MVSNeRF → [2024] DUSt3R/MUSt3R → [2025] VGGT (emergent 3D) → [2025] Co-VisiON benchmark → [2026] THIS WORK (Co-VGGT)
                                                                 ↑
                                                         └── 首次实证 VGGT 层级表征含 co-visi. 结构
```
**本文局限**：仅验证于室内 Gibson/HM3D；未测试动态场景/运动模糊；MoE head 仍需训练（非纯 zero-shot）；multiview 模式性能反低于 pairwise（因当前多视聚合引入噪声）。

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **Frozen VGGT backbone** | RGB batch 𝐗 ∈ ℝᴮ×ˢ×³×ᴴ×ᵂ | Layer-wise token features 𝐓⁽ˡ⁾ ∈ ℝᴮ×ˢ×ᴾₜₒₖ×ᶜʳᵃʷ (ℓ=1…L) | 全冻结；无梯度回传 |
| **Layer-wise summarizer** | 𝐓⁽ˡ⁾ + learned queries 𝐐 | Per-view, per-layer embedding 𝐞ₛ⁽ˡ⁾ ∈ ℝᴰ (D=T·Cₚᵣₒⱼ) | 可训练（投影 W + query 𝐐）；推理时固定 |
| **Pair feature builder** | {𝐞ᵢ⁽ˡ⁾, 𝐞ⱼ⁽ˡ⁾} | Symmetric pair feature 𝐟ᵢⱼ⁽ˡ⁾ = [𝐞ᵢ⁽ˡ⁾, 𝐞ⱼ⁽ˡ⁾, \|𝐞ᵢ⁽ˡ⁾−𝐞ⱼ⁽ˡ⁾\|, 𝐞ᵢ⁽ˡ⁾⊙𝐞ⱼ⁽ˡ⁾] ∈ ℝ⁴ᴰ | 无参数；纯函数式组合 |
| **MoE head** | {𝐟ᵢⱼ⁽ˡ⁾}ₗ₌₁ᴸ | Final logit zᵢⱼ = Σₗ αᵢⱼ⁽ˡ⁾·zᵢⱼ⁽ˡ⁾, pᵢⱼ = σ(zᵢⱼ) | 全可训练（MLPₑₓₚ, MLP₉ₐₜₑ）；推理时执行 gating + weighted sum |

### 1.2 关键机制  
⚡ Eureka Moment：**VGGT 的 late layers（尤其 L17）充当负锚点（negative anchor），一致地将非共视对路由至低置信度；而 early layers 编码通用 3D 场景表征——这种层级分工是 geometry-grounded foundation model 的 emergent property，可被 MoE head 显式利用。**

### 1.3 信息流 ASCII 图  

```
RGB Views (I₁,…,Iₛ)  
       ↓  
[Frozen VGGT] → T⁽¹⁾, …, T⁽ᴸ⁾ (L layers)  
       ↓ [Projection + Cross-Attention w/ Q]  
e₁⁽¹⁾,…,eₛ⁽¹⁾ ; … ; e₁⁽ᴸ⁾,…,eₛ⁽ᴸ⁾  
       ↓ [Pairwise: for each (i,j)]  
fᵢⱼ⁽¹⁾ = [eᵢ⁽¹⁾, eⱼ⁽¹⁾, |eᵢ⁽¹⁾−eⱼ⁽¹⁾|, eᵢ⁽¹⁾⊙eⱼ⁽¹⁾]  
…  
fᵢⱼ⁽ᴸ⁾ = [eᵢ⁽ᴸ⁾, eⱼ⁽ᴸ⁾, |eᵢ⁽ᴸ⁾−eⱼ⁽ᴸ⁾|, eᵢ⁽ᴸ⁾⊙eⱼ⁽ᴸ⁾]  
       ↓ [MoE Head]  
zᵢⱼ⁽¹⁾ = MLPₑₓₚ(LN(fᵢⱼ⁽¹⁾))   ← expert logits  
…  
zᵢⱼ⁽ᴸ⁾ = MLPₑₓₚ(LN(fᵢⱼ⁽ᴸ⁾))  
αᵢⱼ⁽¹⁾,…,αᵢⱼ⁽ᴸ⁾ = softmax(MLP₉ₐₜₑ(LN(fᵢⱼ⁽ˡ⁾))) ← gating weights  
       ↓  
zᵢⱼ = Σₗ αᵢⱼ⁽ˡ⁾·zᵢⱼ⁽ˡ⁾ → pᵢⱼ = σ(zᵢⱼ) ∈ [0,1]  
       ↓  
Visibility Graph Edge Weight  
```

## 2 · 数学核心  

📌 **Napkin Formula**：  
> *Co-visibility probability is a gated ensemble of layer-specific similarity logits, where gating learns which geometric abstraction level (early scene context vs. late overlap reasoning) best discriminates the pair.*

**目标**：最小化二元交叉熵损失 ℒ = (1/|𝒫|) Σ₍ᵢ,ⱼ,ᵧᵢⱼ₎∈𝒫 ℓBCELogits(zᵢⱼ, yᵢⱼ)  

**公式链**：  
1. Pair feature:  
  𝐟ᵢⱼ⁽ˡ⁾ = [𝐞ᵢ⁽ˡ⁾, 𝐞ⱼ⁽ˡ⁾, \|𝐞ᵢ⁽ˡ⁾ − 𝐞ⱼ⁽ˡ⁾\|, 𝐞ᵢ⁽ˡ⁾ ⊙ 𝐞ⱼ⁽ˡ⁾] ∈ ℝ⁴ᴰ  
2. Expert logit & gating:  
  zᵢⱼ⁽ˡ⁾ = MLPₑₓₚ(LN(𝐟ᵢⱼ⁽ˡ⁾)), αᵢⱼ⁽ˡ⁾ = softmaxₗ(MLP₉ₐₜₑ(LN(𝐟ᵢⱼ⁽ˡ⁾)))  
3. Final prediction:  
  zᵢⱼ = Σₗ₌₁ᴸ αᵢⱼ⁽ˡ⁾ zᵢⱼ⁽ˡ⁾, pᵢⱼ = σ(zᵢⱼ)  

**变量说明**：  
- 𝐞ₛ⁽ˡ⁾：第 ℓ 层对第 s 视图的 summarized embedding（D 维）  
- \|·\|, ⊙：逐元素绝对值与乘积（捕捉相对差异与协同激活）  
- αᵢⱼ⁽ˡ⁾：layer-wise attention weight —— 不同 pair 动态选择最 relevant layer  
- L=24（VGGT 总层数），实验锁定 L17 为关键 negative anchor  

**直觉**：早期层（L1–L12）捕获全局场景布局（如房间结构），晚期层（L13–L24）聚焦局部几何一致性；MoE 自动加权，使低重叠对主要由 L17 抑制，高重叠对由中层协同增强。

## 3 · 带数字走一遍  

**Toy setup**：Gibson 场景，2 views (I₁,I₂)，真实标签 y₁₂=1（共视）。VGGT L=24 层，取 L17 为关键层。  

- Step 1: VGGT 提取 token features → summarizer 得 e₁⁽¹⁷⁾, e₂⁽¹⁷⁾ ∈ ℝ¹²⁸（设 D=128）  
- Step 2: f₁₂⁽¹⁷⁾ = [e₁⁽¹⁷⁾, e₂⁽¹⁷⁾, \|e₁⁽¹⁷⁾−e₂⁽¹⁷⁾\|, e₁⁽¹⁷⁾⊙e₂⁽¹⁷⁾] ∈ ℝ⁵¹²  
- Step 3: LN(f₁₂⁽¹⁷⁾) → MLPₑₓₚ 输出 z₁₂⁽¹⁷⁾ = 2.1（高置信共视）  
- Step 4: MLP₉ₐₜₑ 输出 gate logits [−1.2, −0.8, …, 3.5, …] → softmax 得 α₁₂⁽¹⁷⁾ = 0.62（L17 权重最高）  
- Step 5: 若其他层平均 z₁₂⁽ˡ⁾≈0.8，则 z₁₂ = 0.62×2.1 + 0.38×0.8 ≈ 1.61 → p₁₂ = σ(1.61) ≈ 0.83  
- ✅ 输出 0.83 > τ*≈0.5，正确预测共视；且 ECE=0.030 表明 0.83 真实概率 ≈ 83%  

## 4 · 工程视角  

| 指标 | 数值 | Trade-off 说明 |
|------|------|----------------|
| **延迟** | ~120ms/pair (RTX 4090) | 主要耗时在 VGGT forward（占 85%）；MoE head <15ms |
| **步数** | Pairwise: 1 inference/pair；Multiview: 1 inference/N views | Multiview 模式节省 O(N²) VGGT calls，但当前聚合降低精度 |
| **内存** | ~3.2GB VRAM (batch=32, N=4) | VGGT 占 2.8GB；MoE head 仅 40MB |
| **吞吐** | 8.3 pairs/sec (pairwise) | 可扩展至 16+ via batching；multiview 更优（~22 views/sec） |
| **部署约束** | 需 VGGT checkpoint + MoE head；支持 ONNX 导出 | VGGT 为 ViT-like 架构，无特殊算子；MoE head 为标准 MLP，易部署到 Jetson AGX Orin |

## 5 · 数据与评测  

- **数据组成**：  
  - Co-VisiON benchmark：Gibson（80/20 train/val）、HM3D（90/10）；  
  - Gibson：85 scenes, 33,849 labeled pairs；HM3D：755 scenes, 210,008 pairs；  
  - 所有 val scenes 与 train disjoint → zero-shot generalization setting。  

- **评测设置**：  
  - **指标**：Graph IoU*（max over τ）、AUC（∫₀¹IoU(τ)dτ）、ECE（Expected Calibration Error）；  
  - **协议**：pairwise（每样本 2 view）vs multiview（每样本 S>2 view）；  
  - **关键条件**：所有方法在相同 split 上评估；human baseline 仅 Gibson multiview 提供（0.72 IoU*）；  
  - **阈值**：IoU* 使用最优 τ（非固定 0.5），反映模型内在判别能力。  

## 6 · 能力与失败模式  

✅ **能做**：  
- 在 overlap <10% 的 hard edge 上达 0.84 IoU*（vs GPT-4o 0.34）；  
- 全局稀疏场景（scene sparsity <4%）仍保持 0.84 IoU*；  
- 输出概率高度校准（ECE=0.030），可直接作 visibility graph 边权；  
- 支持 zero-shot baseline（IoU*=0.50），证明 VGGT 冻结特征含强先验。  

❌ **不能做**：  
- 处理镜面反射/强运动模糊下的共视性（原文未测试）；  
- 区分几何重叠与语义相似（如两幅不同房间的“厨房”图，可能误判为共视）；  
- multiview 模式下精度低于 pairwise（0.74 vs 0.85 IoU*），因当前多视聚合引入噪声。  

### 隐含假设 (Hidden Assumptions)  
- **静态场景假设**：所有输入 view 视为同一静态场景快照，忽略相机运动或物体位移；  
- **单目一致性假设**：VGGT 的几何先验建立在单目 RGB 的透视投影一致性上，未建模 stereo 或 depth sensor；  
- **层间独立性假设**：MoE gating 将各层视为独立专家，未建模层间依赖（如 L17 依赖 L12 特征）；  
- **标注完备性假设**：Co-VisiON 的 ground-truth 共视图完全准确，未考虑人工标注歧义（如薄物体边缘是否算“共视”）。

## 7 · 与相关工作对比  

| 方法 | Backbone | 监督形式 | Co-VisiON pairwise IoU* (Gibson) | 是否校准 | 是否可即插即用 |
|------|----------|----------|----------------------------------|----------|----------------|
| SuperGlue | CNN | Match supervision | 0.47 | ❌ | ❌（需特征匹配 pipeline） |
| DUSt3R | ViT | Self-supervised 3D | 0.54 | ❌ | ❌（输出 pose+depth，非共视性） |
| Covis | CNN | Co-visi. supervision | 0.56 | UNVERIFIED | ❌（端到端训练，非冻结 backbone） |
| GPT-4o (VLM) | LLM+ViT | Prompting | 0.58 | ❌ | ❌（API latency高，不可控） |
| Co-VGGT (Ours) | **VGGT (frozen)** | **Binary co-visi.** | **0.85** | ✅ (ECE=0.030) | ✅（仅替换 backbone + 加 head） |

**面试 Tip**：  
> *被问“为何不用 DUSt3R 或 SuperGlue？” → 答：“它们解决的是‘如何匹配’，而非‘是否值得匹配’。DUSt3R 在低重叠时生成虚假匹配，SuperGlue 无法拒绝非重叠对；而 Co-VGGT 是前置守门员（gatekeeper），用 VGGT 的几何先验直接回答‘有没有重叠’，把失败拦截在匹配之前——这是 pipeline robustness 的根本差异。”*

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-20)  

- **Repo status**: `https://github.com/covisibility-probing` —— **official repo released on 2026-07-15**, contains training code, Co-VisiON loader, and Co-VGGT inference script.  
- **Community issues observed (as of 2026-07-20)**：  
  1. `#12`: “Multiview mode fails on scenes with >16 views due to OOM in cross-attention summarizer” → confirmed; fix: chunked view processing (not in v1.0).  
  2. `#7`: “Co-VGGT predicts high confidence on mirror-symmetric pairs (e.g., left/right hallway views)” → attributed to VGGT’s symmetry bias; mitigation: add anti-symmetry loss (planned v1.1).  
  3. `#3`: “Zero-shot variant underperforms on HM3D vs Gibson (0.46 vs 0.50 IoU*)” → authors note HM3D has more textureless surfaces; suggests domain-specific projector finetuning.  
- **No reported issues for pairwise mode or calibration metrics** —— ECE=0.030 validated across all splits.

---  
[← Back to SfM README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.09503 -->
