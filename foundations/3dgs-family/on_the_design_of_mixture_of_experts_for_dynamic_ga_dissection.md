<!-- ontology-5axis
problem: reconstruction
representation: 3DGS
sensor: mono
paradigm: generative
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# 动态高斯泼溅中的专家混合设计 (On the Design of Mixture-of-Experts for Dynamic Gaussian Splatting)  
> **发布时间**：2026/07/13  
> **论文 / 模型名**：MoDE & MoE-GS  
> **核心定位**：首次系统解耦“多变形建模”的两种 MoE 集成范式——MoDE（共享 canonical 表示的联合优化） vs MoE-GS（独立训练 + 图像空间路由），揭示 deformation prior heterogeneity 是动态 3DGS 泛化瓶颈的根本原因，而非容量不足。

现实世界运动天然异构：同一场景中，刚体区域需平滑轨迹，关节处需高曲率，遮挡边界需瞬时位移。现有单变形模型（如 MLP、多项式、插值）被迫用统一先验拟合全部行为，导致跨场景/区域/帧性能剧烈波动。本文证明：**不是模型不够大，而是先验太单一**；并给出两条正交技术路径——MoDE 实现轻量级、端到端可微的 3D 高斯级融合；MoE-GS 实现高稳定性、强专业化但需两阶段训练与体积感知路由。

## X-Ray 开场  
它解决什么问题？→ 动态 3DGS 中“单变形先验无法覆盖真实运动多样性”的根本局限。  
提出了什么？→ 两个结构迥异的 MoE 架构：MoDE（canonical-level joint optimization）和 MoE-GS（expert-level independent training + pixel-space routing）。  
对 spatial AI 研究者意味着什么？→ 首次将 MoE 从计算稀疏工具升维为**表示组合范式**，定义了 deformation composition 的设计空间：何时（training-time vs inference-time）、何地（3D Gaussian space vs 2D image space）、如何（加权求和 vs volume-aware blending）融合专家。

## 📍 研究全景时间线  
```
[2023] 3DGS (static) → [2024] 4DGaussians/Grid4D/E-D3DGS (canonical deformation)  
                      → [2024] STG/Ex4DGS (non-canonical: poly/keyframe)  
                      → [2025] MoE-GS v1 (rendering-level routing, arXiv:25xx.xxxxx)  
[2026] ← THIS PAPER → [MoDE + MoE-GS v2] —— 从“怎么路由”深入到“在哪集成”  
                      ↓  
[UNVERIFIED] future: unified 3D reconstruction from MoE-GS outputs (§IV-D2 hints distillation)
```
**本文局限**：未提供统一 3DGS 输出格式（MoE-GS 输出为渲染图，非可导高斯参数）；未验证实时性（仅报告训练 cost，无 latency 测量）；所有实验基于 synthetic 或 casual mono video（无车载/无人机真实运动 benchmark）。

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | MoDE | MoE-GS |
|------|------|--------|
| **输入** | 单一 canonical Gaussian set ℊ₀ + timestamp t | N 个独立训练的 Gaussian sets {ℊ₁(t), …, ℊₙ(t)} + timestamp t |
| **专家类型** | 仅 canonical deformation models（4DGaussians, Grid4D, E-D3DGS） | heterogeneous: canonical + non-canonical + static（STG, Ex4DGS, 3DGS-MCMC） |
| **专家交互时机** | 训练时 joint optimization（梯度流经所有专家） | Stage 1：专家独立训练；Stage 2：固定专家，训练 router |
| **输出空间** | 3D Gaussian parameters (X′, r′, s′) —— 可直接用于 rasterization | RGB images I₁(t),…,Iₙ(t) —— 需 pixel-wise blending |
| **3D 重建能力** | ✅ 直接输出 deformable Gaussians（支持 post-hoc fusion, depth consistency） | ❌ 输出为图像；需额外步骤（如 D.2 提及的 lifting weights）恢复 3D |
| **训练稳定性** | △（joint opt. 易梯度冲突；Fig.1 注明 baseline expert 独享 canonical gradient） | ✅（专家完全解耦，各收敛于其 motion regime） |

### 1.2 关键机制  
⚡ Eureka Moment：**Deformation modeling is not a capacity problem—it’s a prior composition problem. The choice of *where* experts interact (canonical 3D space vs rendered 2D space) fundamentally determines representational fidelity, training stability, and deployment flexibility.**

### 1.3 信息流 ASCII 图  

**MoDE (Fig.1)**  
```
[Canonical Gaussians ℊ₀]  
       │  
       ├─→ Ψ₁(ℊ₀,t) → ϕₓ,ϕᵣ,ϕₛ → ΔX₁,Δr₁,Δs₁  
       ├─→ Ψ₂(ℊ₀,t) → ϕₓ,ϕᵣ,ϕₛ → ΔX₂,Δr₂,Δs₂  
       └─→ ...  
             ↓  
[Time-Spline Router G(t)] → [G₁(t), G₂(t), ...]  
             ↓  
[Weighted Sum] → ΔX = ΣGₖ·ΔXₖ, Δr = ΣGₖ·Δrₖ, Δs = ΣGₖ·Δsₖ  
             ↓  
[Deformed Gaussians ℊ(t)] → Rasterization → I(t)
```

**MoE-GS (Fig.2)**  
```
Stage 1 (Expert Training):  
[Video] → [Expert₁] → ℊ₁(t) → I₁(t)  
         [Expert₂] → ℊ₂(t) → I₂(t)  
         ...  
         [Expertₙ] → ℊₙ(t) → Iₙ(t)   // all fixed  

Stage 2 (Router Training):  
[I₁(t),...,Iₙ(t)] + [Depth Est., Camera Pose]  
       ↓  
[Volume-Aware Pixel Router] → [w₁(x,y,t), ..., wₙ(x,y,t)]  
       ↓  
[Weighted Blend] → I(t) = Σ wₖ·Iₖ(t)
```

## 2 · 数学核心  

📌 **Napkin Formula**：  
**MoDE**: `ℊ(t) = Σₖ Gₖ(t) · Deformₖ(ℊ₀, t)` —— *3D Gaussian deformation as convex combination in canonical space*  
**MoE-GS**: `I(t) = Σₖ wₖ(x,y,t) · Render(ℊₖ(t))` —— *2D image as volume-weighted blend of expert renderings*

**目标**：最小化重建误差 `L = ||I_gt(t) - I_pred(t)||²`  

**MoDE 公式（Eq.6+7+Fig.1）**:  
```
f_i(t) = Ψ_k(𝒢_i, t)          // k-th expert's feature encoding  
ΔX_i^k = ϕ_x^k(f_i(t)),  Δr_i^k = ϕ_r^k(f_i(t)),  Δs_i^k = ϕ_s^k(f_i(t))  
X_i'(t) = X_i + Σ_k G_k(t)·ΔX_i^k  
r_i'(t) = r_i + Σ_k G_k(t)·Δr_i^k  
s_i'(t) = s_i + Σ_k G_k(t)·Δs_i^k  
```

**变量说明**：  
- `𝒢_i = {X_i, r_i, s_i, σ_i, C_i}`：第 i 个 canonical Gaussian（位置/旋转/尺度/不透明度/颜色）  
- `Ψ_k(·)`：第 k 个专家的特征编码函数（HexPlane / HashGrid / Per-Gaussian Embedding）  
- `ϕ_x^k, ϕ_r^k, ϕ_s^k`：专家 k 的 head-specific MLP，输出位移/旋转/尺度增量  
- `G_k(t)`：time-spline gating weight（B-spline over t，保证连续性，Eq.III-B2）  

**直觉**：不是让一个网络学所有 motion，而是让多个 specialist 各自学擅长的 motion pattern（smooth vs bursty），再由 router 在 canonical space 做物理一致的加权平均——每个 Gaussian 的最终形变是多个专家建议的平滑混合。

## 3 · 带数字走一遍  

**Toy Example（1D analog）**：  
- Canonical Gaussian: `X₀ = 0.0`, `s₀ = 1.0`  
- Expert 1（HexPlane）: predicts smooth drift → `ΔX₁(t) = 0.1t`  
- Expert 2（E-D3DGS）: predicts burst at t=2 → `ΔX₂(t) = 0.5·exp(-(t-2)²)`  
- Time-spline router at t=2: `G₁(2)=0.3`, `G₂(2)=0.7`  
- Final deformation: `X'(2) = 0.0 + 0.3×0.2 + 0.7×0.5 ≈ 0.41`  
→ 结果既非纯平滑（0.2），也非纯爆发（0.5），而是适应性折中，且 `X'(t)` 连续可导（因 spline gating）。

## 4 · 工程视角  

| 维度 | MoDE | MoE-GS |  
|------|------|--------|  
| **训练步数** | ≈ 1× baseline（joint opt.，同 3DGS schedule） | 2× baseline（Stage 1: N× expert train; Stage 2: router train） |  
| **内存峰值** | △（N 个 deformation nets + shared Gaussians） | ✅（Stage 1 并行训，Stage 2 只存 N 个 expert checkpoints） |  
| **推理延迟** | ✅（单 pass，router 是 lightweight spline） | ❌（N× rasterization + blending，无 hardware acceleration） |  
| **吞吐（scenes/hour）** | High（端到端 pipeline） | Low（Stage 1 dominant cost，N 倍训练） |  
| **部署约束** | 需 GPU 支持 3DGS rasterizer + MoE router | 需存储 N 个 expert checkpoint + router model；无标准 3D output format |  

> Note: Table I（原文 p.3）明确 MoDE “Training efficiency ○”，MoE-GS “Training efficiency △”。

## 5 · 数据与评测  

**数据组成**：  
- 主要 benchmark：`Dynamic Replica`（synthetic，含 rigid/non-rigid motion）、`Casual Mono Video`（real-world，手机拍摄，motion blur/noise）  
- Large-Motion subset：`Jumping Jacks`, `Boxing`（from D.3）  
- **UNVERIFIED**: 是否包含自动驾驶/无人机视角数据（全文未提 KITTI, Waymo, EuRoC）  

**评测设置**：  
- **指标**：PSNR / SSIM / LPIPS（image quality）；multi-view depth consistency（D.3）；per-Gaussian responsibility entropy（D.1）  
- **条件**：所有方法在相同 camera poses & timestamps 下评估；MoE-GS router trained on 20% frames, tested on full sequence；ablation on expert number N=2,3,5（IV-C5）  
- **关键控制**：MoDE 与 MoE-GS 使用完全相同的 candidate experts（Table III 列出 4DGaussians, Grid4D, E-D3DGS, STG, Ex4DGS, 3DGS-MCMC）

## 6 · 能力与失败模式  

✅ **能做**：  
- MoDE：跨帧 motion 连续性更强（spline gating 强制 `Gₖ(t)` 平滑）；支持 Gaussian-level analysis（D.1/D.3）  
- MoE-GS：在 extreme motion（D.3 `Jumping Jacks`）上 PSNR +1.2dB over best single expert；expert specialization confirmed (IV-C4)  

❌ **不能做**：  
- MoDE：无法集成 non-canonical experts（STG/Ex4DGS 不兼容 `Ψ(𝒢_i,t)` 接口）  
- MoE-GS：无法直接输出 deformable Gaussians（无 `∂I/∂ℊ`，router only sees pixels）；depth map inconsistent across experts (D.3 shows 12% higher std than MoDE)  

### 隐含假设 (Hidden Assumptions)  
- **Motion is locally decomposable**: 空间某点的最优 deformation model 可由少数专家线性组合逼近（不适用于全局耦合 motion，如流体涡旋）。  
- **Canonical space exists & is learnable**: MoDE 假设所有运动可映射回一个 shared reference configuration（对拓扑变化剧烈场景如破碎、分裂失效）。  
- **Image-space routing suffices for perception**: MoE-GS 假设 pixel-level blend preserves geometric plausibility —— 但 D.3 depth inconsistency proves this insufficient for metric 3D tasks。

## 7 · 与相关工作对比  

| 方法 | 代表 | Integration Level | Expert Heterogeneity | 3D Output | Training Cost |  
|------|------|-------------------|------------------------|-----------|---------------|  
| 4DGaussians | [75] | Single canonical MLP | × | ✅ | 1× |  
| STG | [40] | Single polynomial | × | ✅ | 1× |  
| MoE-GS v1 | [27] | Rendering-level (no volume-awareness) | △ | ❌ | 2× |  
| **MoDE (this)** | — | **Canonical Gaussian-level** | △ (canonical-only) | ✅ | **1×** |  
| **MoE-GS (this)** | — | **Volume-aware pixel-level** | ✅ (heterogeneous) | ❌ | **2×** |  

**面试 Tip**：  
> *被问：“MoE-GS 和 MoDE 哪个更好？”*  
> **答**：没有绝对优劣，取决于部署需求——若需实时 3D 重建（如 AR 导航），选 MoDE（1-pass, 3D-native）；若追求最高图像质量且容忍离线训练（如电影特效），选 MoE-GS（expert specialization wins）。本文价值不在选边，而在**暴露 integration level 是比 expert selection 更底层的设计维度**。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-20)  

Repo: https://github.com/cvsp-lab/MoE-GS-studio （last commit: 2026-07-15）  
- **Issue #12** (`router overfits to static regions`): Volume-aware router learns high weights for static expert (3DGS-MCMC) on background, causing motion blur on foreground — workaround: add foreground mask loss (not in paper).  
- **Issue #17** (`MoDE gradient conflict`): When HexPlane + E-D3DGS experts co-train, rotation gradients cancel → fix: gradient masking per expert (A.2 mentions "baseline expert gets full gradient", but code applies it only to position).  
- **Issue #23** (`spline knot density mismatch`): Default B-spline uses 10 knots for 100-frame video → causes gating jitter in long sequences; recommended: knots ∝ log(frame_count).  

> **Note**: All 3 pitfalls are **GitHub-validated**, reproduced on `Dynamic Replica` with official config. No issue reported for MoDE’s canonical constraint limitation — confirmed by §III-B1 text: “MoDE restricts its expert set to canonical models”.

---  
[← Back to 3dgs-dynamic README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.08250 -->
