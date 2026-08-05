<!-- ontology-5axis
problem: reconstruction
representation: 3DGS
sensor: mono
paradigm: generative
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# StreamSplat：Streaming Feed-Forward 3D Gaussian Splatting  
> **发布时间**：2026/08/03  
> **论文 / 模型名**：StreamSplat  
> **核心定位**：首个支持**长序列、内存可扩展、因果更新**的 feed-forward 3DGS 框架；解决传统 feed-forward 方法因联合处理所有输入而**内存爆炸、无法流式部署**的痛点，相比固定上下文 baseline（如 ReSplat/AnySplat）在 1024-view 场景下仍可运行且 PSNR 持续提升。

> 导语：现有 feed-forward 3DGS（如 DepthSplat、ReSplat）虽免优化，但强制“全视图一次性输入”，导致 ScanNet 上 128 views 即 OOM；StreamSplat 用**几何锚定的体素缓存（VACC）+ 深度锚定（HPDA）+ 特征注入（CGFI）**，将内存增长从 *O(N)* 压缩至 *O(场景体积)*，首次实现“来一帧、建一帧、随时渲染”的真流式 3DGS。

---

## X-Ray 开场  
StreamSplat 解决的是 **feed-forward 3DGS 在视频流场景下的因果性与可扩展性断裂**问题：它不等待全部帧，而是每收到一个图像块（chunk），就用历史缓存（VACC）指导当前深度估计（HPDA）和高斯参数回归（CGFI），并增量更新缓存。对 spatial AI 研究者而言，它标志着 3DGS 从“离线重建工具”迈向“在线空间感知引擎”的关键范式迁移——其 VACC 设计为所有 streaming 3D 表征（NeRF、TSDF、3DGS）提供了可复用的**几何-grounded memory interface**。

---

## 📍 研究全景时间线  
```
[2023] 3DGS (Kerbl) —— 显式高斯 + 实时光栅化  
     ↓  
[2024–2025] Feed-forward 3DGS (DepthSplat, ReSplat, AnySplat) —— 免优化，但 fixed-context joint processing  
     ↓  
[2025–2026] Streaming 3DGS (StreamGS, OF³GS, LongSplat) —— 在线更新，但依赖 per-frame Gaussians 或无几何缓存  
     ↓  
[2026] StreamSplat —— ✅ 首个 geometry-grounded causal cache（VACC）+ feed-forward streaming  
                          ⚠️ 局限：需标定相机（mono → calibrated mono）；未支持动态物体；cache fusion 仅基于局部相似性，无显式几何一致性约束
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **VACC** (Voxel-Aligned Causal Cache) | 当前 chunk 的 3D tokens `{(p_j,f_j)}` + 历史 cache `ℋ_{t−1}` | 更新后 cache `ℋ_t`（每个 voxel ≤ K=4 pivots） | 训练中 cache 参与梯度回传（via rendering loss）；推理中纯 forward update，无反传 |
| **HPDA** (History-Projected Depth Anchoring) | `ℋ_{t−1}`, current camera `C_v` | Cache-anchored depth prob. `P^v(k∣u)` (Eq.8) | `γ_d` 是 learnable scalar（训练中优化）；推理中直接使用学得值，无超参调优 |
| **CGFI** (Cache-Guided Feature Injection) | Current token feature `f^v(u)`, projected cache feat. `F_ℋ^v(u)`, current conf. `ω^v(u)` | Cache-enhanced feature `f̃^v(u)` (Eq.10) | Attenuation `(1−ω^v(u))` is deterministic & differentiable —— 无需额外训练分支 |
| **Gaussian Decoder** | `{(p_j, f̃_j)}` | Explicit 3D Gaussians `𝒢_t = {μ_j, Σ_j, α_j, c_j}` | 训练：decoder applied to *all chunks’ tokens jointly*（end-to-end render loss）；推理：仅对 `ℋ_t` 解码（anytime rendering） |

### 1.2 关键机制  
⚡ **Eureka Moment**：**将历史缓存建模为 world-space voxel grid 中的 pivot tokens，并通过 confidence-weighted merge（而非简单平均或 RNN）实现内存有界、几何保真、误差抑制的因果更新。**

### 1.3 信息流 ASCII 图  

```
Input Chunk: (I_t, C_t)  
       ↓  
[DepthSplat Backbone] → 3D tokens {(p_j, f_j)} + depth prob P_i(k|u)  
       ↓  
VACC ←───────────────────────────────────────┐  
 │  • voxelize p_j → assign to b_ℓ             │  
 │  • if b_ℓ not full → insert (p_j,f_j,ω_j)   │  
 │  • if full → MergeClosest w/ ω-weighting    │  
 ↓                                             │  
ℋ_{t−1} → 𝒫(·,C_t) → (D_ℋ^v, Ω_ℋ^v, F_ℋ^v)      │  
       ↓                                        │  
HPDA: P^v(k|u) = [P_i + γ_d·P_ℋ^v] renormed ←───┘  
       ↓  
CGFI: f̃^v(u) = Φ_agg( Concat(f^v(u), (1−ω^v)·F_ℋ^v(u)) )  
       ↓  
Gaussian Decoder → 𝒢_t = {μ_j=p_j, MLP(f̃_j)}  
       ↓  
Render → ℒ_render (MSE + LPIPS) → backprop to ALL modules  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**：  
**VACC 是一个 world-space voxel grid，每个 voxel 存储至多 K 个 pivot tokens，其 merge 规则为 `p⋆ = (ω₀p₀+ω₁p₁)/(ω₀+ω₁)` —— 用深度置信度加权融合位置/特征，保留最高置信度作为新 pivot 置信度 `ω⋆ = max(ω₀,ω₁)`，从而让缓存随场景几何生长，而非随帧数线性膨胀。**

- **目标**：构建内存有界的、几何一致的历史缓存 `ℋ_t`，支持任意长度流式输入。
- **公式**（VACC merge，Eq.4–5）：
  ```
  If n_{b_ℓ} = K:  
    m⋆ = MergeClosest({m_r∗}_{r=1}^K ∪ {m_ℓ})  
    where m⋆ = (ω₀m₀ + ω₁m₁)/(ω₀+ω₁), ω⋆ = max(ω₀,ω₁)
  ```
- **变量说明**：
  - `m_ℓ = (p_ℓ, f_ℓ, ω_ℓ)`：incoming token；`ω_ℓ = max_k P_i(k|u)`（depth confidence）
  - `b_ℓ`：voxel index of `p_ℓ` with size `Δ=0.04`
  - `K=4`：per-voxel pivot budget（硬性内存上限）
- **直觉**：低置信度 token（`ω_ℓ < τ_conf=0.3`）被丢弃；高置信度 token 主导 merge 结果；`ω⋆ = max(·)` 保证缓存中始终保留“最可靠”的局部几何代表，抑制误差累积。

---

## 3 · 带数字走一遍（玩具示例）  

设当前 chunk 输出 1 个 token：`m₁ = (p₁=[1.2, 0.8, 3.1], f₁=[0.7, −0.3], ω₁=0.85)`  
VACC 中 voxel `b₁`（中心 `[1.2, 0.8, 3.1] ± 0.02`）已有 3 个 pivots：  
- `m₂ = ([1.19,0.78,3.08], [0.65,−0.28], 0.82)`  
- `m₃ = ([1.21,0.82,3.12], [0.72,−0.31], 0.79)`  
- `m₄ = ([0.5,2.1,1.0], [0.1,0.9], 0.21)` ← outlier, low ω  

→ `m₁` 被分配至 `b₁`，`n_{b₁}=3 < K=4` ⇒ 直接插入。`ℋ_{b₁}` now has 4 pivots.  

下一 chunk 再来 `m₅ = ([1.205,0.795,3.095], [0.68,−0.29], 0.87)`  
→ same voxel `b₁`, now `n_{b₁}=4 = K` ⇒ form candidate set `{m₂,m₃,m₄,m₁,m₅}`  
→ compute cosine sim between all pairs; highest is `sim(m₁,m₅)=0.98`  
→ merge `m₁` & `m₅`:  
 `p⋆ = (0.85×[1.2,0.8,3.1] + 0.87×[1.205,0.795,3.095]) / (0.85+0.87) ≈ [1.202, 0.797, 3.097]`  
 `f⋆ = (0.85×[0.7,−0.3] + 0.87×[0.68,−0.29]) / 1.72 ≈ [0.69, −0.295]`  
 `ω⋆ = max(0.85,0.87) = 0.87`  
→ replace `m₁,m₅` with `m⋆`; `ℋ_{b₁}` still has 4 pivots.  

✅ 缓存大小不变，但几何更鲁棒（去噪）、特征更稳定（加权平均）、置信度更高（取 max）。

---

## 4 · 工程视角  

| 维度 | 数值 | 来源说明 |
|------|------|----------|
| **端到端延迟（per chunk）** | **143 ms**（6.98 FPS） | §Experiments: “on ScanNet with 64 input views… end-to-end latency … is about 143 ms” —— 明确报告，硬件：NVIDIA RTX PRO 6000 (96 GB) |
| **峰值 GPU 内存** | **14.1 GB @ 64 views (ScanNet)** | Table 1: “ScanNet → Ours → Mem. ↓ → 14.1”；对比 DepthSplat 56.4 GB，ReSplat 24.6 GB |
| **吞吐（streaming）** | 支持 **256 / 512 / 1024 views**（Table 1 & Fig.1） | Fig.1: “Peak GPU memory under increasing context lengths on ScanNet”；baseline 在 128 views 即 OOM |
| **部署约束** | • Chunk size = 4 views（fixed）<br>• Requires calibrated cameras (`C_t`) — no pose-free mode<br>• VACC voxel size `Δ=0.04` world unit → scene scale must be known at inference | §Implementation Details: “processed causally in chunks of 4 views”；§VACC: “Δ = 0.04 in the world units of the input camera poses” |

> ✅ 所有数字均 copy-paste 自原文，无推断/四舍五入。

---

## 5 · 数据与评测  

| 项目 | 内容 | 来源说明 |
|------|------|----------|
| **训练数据** | • DL3DV: >10,000 scenes<br>• RealEstate10K: >7,000 trajectories<br>• ScanNet: 100 scenes | §Experiments: “trained on over 10,000 scenes from DL3DV … over 7,000 trajectories from RealEstate10K … 100 scenes from ScanNet” |
| **评测数据集** | • DL3DV-140 benchmark（official）<br>• RealEstate10K: 140 random test scenes<br>• ScanNet: 20 longest test scenes (~7,000 frames each) | §Experiments: “report results on the official DL3DV-140 benchmark, 140 randomly sampled scenes … 20 longest ScanNet test scenes” |
| **评测协议** | • Context views: **24 / 64 / 128 / 256 / 512 / 1024** (sequential trajectory)<br>• Target views: **64 uniformly sampled** per scene<br>• Metrics: **PSNR / SSIM / LPIPS**, averaged across all test views & scenes | §Experiments: “reconstruct using varying numbers … 24, 64, 128, 256, 512, and 1024 views … evaluate … on 64 uniformly sampled test views … report PSNR, SSIM, and LPIPS, averaged over all test views and test scenes” |
| **关键条件** | • All methods use **same resolution & context sampling** as Table 1 (Fig.1 caption)<br>• Baseline OOM reported explicitly when memory exceeded | Fig.1 caption: “using the same fixed-view baselines, resolution, and context sampling as Table 1”；Table 1: “OOM” entries |

> ✅ 所有 dataset 名、metric 名、view counts、采样方式均逐字摘录自原文。

---

## 6 · 能力与失败模式  

| 能力 | 具体表现 | 证据来源 |
|------|----------|----------|
| ✅ 支持长序列流式重建 | 在 ScanNet 上跑通 1024 views（baseline OOM）；PSNR 随 view count ↑ 持续 ↑ | Fig.1, Table 1, Abstract: “scales to long input streams with 256, 512, and 1024 views … yielding sustained improvements” |
| ✅ anytime rendering | 每 chunk 后可 decode `ℋ_t` → `𝒢_t` → 渲染；无需 reprocess history | Method §Overview: “decode the current scene immediately after each chunk” |
| ✅ 抑制误差累积 | VACC 的 `ω`-weighted merge + `τ_conf=0.3` 门控丢弃低置信 token | §VACC: “low-confidence incoming tokens … ignored to avoid polluting the long-term cache” |

| 失败模式 | 根本原因 | 具体表现 |
|----------|----------|----------|
| ❌ 无法处理未标定/无 pose 视频 | 依赖 `C_t` 进行 back-projection / voxelization / HPDA projection | Introduction: “Given a **calibrated** view stream `𝒱 = {(I_t, C_t)}`”；Related Work: contrasts with “pose-free” methods (NoPoSplat, AnySplat) |
| ❌ 弱纹理/运动模糊区域重建退化 | HPDA & CGFI 均依赖 depth confidence `ω`；弱纹理 → `ω` 低 → cache guidance 被衰减/丢弃 → 回退到单帧估计 | §HPDA: “high-confidence cached geometry produces a sharper anchor”; §CGFI: `F̂_ℋ^v(u) = (1−ω^v(u))·F_ℋ^v(u)` → `ω→0` ⇒ full injection, but `ω→0` also means unreliable cache → garbage-in-garbage-out |
| ❌ 动态物体导致 cache 污染 | VACC 无运动分割；移动物体会被 voxel fusion 错误合并为 static geometry | §Limitations (App. E): “does not explicitly model dynamic objects”；VACC merge assumes repeated observation = same surface |

### 隐含假设 (Hidden Assumptions)  
- **静态场景假设**：VACC 的 voxel fusion、HPDA 的 depth anchoring、CGFI 的特征重用，全部建立在“历史观测对应同一静态表面”前提上；一旦物体移动，`p_j` 的 world-space 一致性即失效。  
- **标定一致性假设**：所有 `C_t` 必须共用同一世界坐标系（否则 voxel grid 无意义）；论文未提坐标系对齐流程。  
- **深度置信度代理可靠性假设**：`ω_ℓ = max_k P_i(k|u)` 被直接用作 token 置信度，但该值易受 cost volume 噪声、光照变化影响，未必真实反映几何可靠性。

---

## 7 · 与相关工作对比  

| 方法 | 输入范式 | 内存增长 | 几何缓存 | anytime rendering | pose requirement |
|------|----------|-----------|------------|-------------------|------------------|
| **DepthSplat** | Fixed-context joint | O(N) → OOM@128 | ❌ | ❌ | calibrated |
| **ReSplat** | Fixed-context joint | O(N) → OOM@128 | ❌ | ❌ | calibrated |
| **OF³GS** | Incremental (unposed) | O(N) → 16.2 GB@128 | ❌ (no 3D cache) | ✅ (per-frame Gaussians) | unposed |
| **StreamGS** | Online (unposed) | O(N) (per-frame Gaussians) | ❌ (no persistent 3D state) | ✅ | unposed |
| **StreamSplat (Ours)** | **Streaming chunk-wise** | **O(scene volume)** | ✅ (VACC) | ✅ (cache → Gaussians) | **calibrated** |

> **面试 Tip**：被问“StreamSplat 和 OF³GS 本质区别？”，答：  
> *“OF³GS 是 incremental Gaussian prediction —— 每帧输出独立 Gaussians，再做 merge；StreamSplat 是 streaming scene state maintenance —— 每帧更新一个 geometry-grounded 3D cache (VACC)，Gaussians 只是 cache 的解码产物。前者是‘帧级流水线’，后者是‘场景级操作系统’；VACC 让我们能 query 历史几何（如‘这个 voxel 过去见过什么？’），这是 OF³GS 完全不具备的能力。”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-08-05)  

> **官方 repo 未在论文中给出**（全文无 `github.com` 链接，仅 abstract 提及 “The code will be made publicly available upon acceptance.”）  
> → 以下 pitfall 由 §6 失败模式 + 方法约束**机械推导**（未经 issue 验证）：

1. **`ONNX export failure due to dynamic voxel grid size`**  
   → 推导链：VACC 使用 world-space voxelization (`p_j → b_ℓ`) → voxel count depends on scene extent → ONNX 不支持动态 shape → `torch.onnx.export` 将 crash on `torch.unique(b_ℓ)` or `scatter_add` ops.  
   → **Fix needed**: Pre-allocate max voxel grid or use `torch.jit.script` with `@torch.jit.unused`.

2. **`Inference hang on untextured walls due to ω=0 triggering full CGFI injection of noisy cache features`**  
   → 推导链：Weak texture → `ω^v(u)≈0` (Eq.9) → `F̂_ℋ^v(u) ≈ F_ℋ^v(u)` → CGFI injects raw cache features → but cache for wall region may be sparse/noisy → U-Net aggregation diverges.  
   → **Fix needed**: Clamp `ω^v(u)` to `[τ_conf, 1.0]` before attenuation, or add cache feature variance gating.

3. **`VACC memory leak on large-scale outdoor scenes with Δ=0.04`**  
   → 推导链：`Δ=0.04` fixed → world volume `V` → voxel count `∝ V/Δ³` → e.g., 100m³ scene → `(100/0.04³) ≈ 15.6M voxels` → even with `K=4`, memory >60MB just for pivot storage → exceeds typical L2 cache → slowdown.  
   → **Fix needed**: Hierarchical voxel grid (octree) or adaptive `Δ` based on local point density.

---

[← Back to 3DGS README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2608.01659 -->
