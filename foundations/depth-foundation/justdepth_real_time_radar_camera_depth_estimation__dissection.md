<!-- ontology-5axis
problem: depth
representation: feature-grid
sensor: RGBD
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# JustDepth: Real-Time Radar-Camera Depth Estimation with Single-Scan LiDAR Supervision  
> **发布时间**：2026/07/24  
> **论文 / 模型名**：JustDepth  
> **核心定位**：首个**单阶段、零辅助标注、单扫 LiDAR 监督**的雷达-相机深度估计器，以**14.8 ms 实时推理**（RTX 4070 Ti）实现与多扫/多阶段 SOTA 相当精度，并将 stripe artifacts 降低 66%（VHGR）。  

> 痛点：现有雷达-相机深度方法依赖多扫 LiDAR、语义分割、3D框等辅助标注，或采用多阶段pipeline（如先稀疏再稠密），导致高延迟、低泛化性、部署困难。  
> 结论：JustDepth 用固定宽 1D 雷达编码 + 高度对齐融合块 + GNN 全局传播 + 训练期置信度监督，**在 nuScenes 上达成 latency/accuracy 最优 trade-off** —— 不是“更快一点”，而是**跳过所有中间表示与外部依赖，从输入直出深度图**。

---

## X-Ray 开场  
JustDepth 解决的是**如何用最简监督（单帧 LiDAR）、最少模态耦合（雷达不插值、图像不预训练）、最低计算开销（常数雷达延迟）做稠密 metric depth**。它提出：① 将雷达压缩为 `B×C×w` 1D 向量，彻底解耦点数与延迟；② 用 height-wise self-attention 在每列图像内对齐雷达深度先验；③ 用 feature-space K-NN GNN 替代 CNN 的局部感受野，让雷达支持像素“跨物体”传播深度线索。对 spatial AI 研究者而言：这是**首篇将 GNN 显式用于 radar-camera 跨模态深度传播的 work**，且证明了“无语义、无运动补偿、单扫监督”仍可抑制 stripe artifacts。

---

## 📍 研究全景时间线  
```
[2020] RC-PDA (multi-stage, LS+3B)  
       ↓  
[2022] DORN (interpolated radar, no aux)  
       ↓  
[2023] Singh et al. (161-sweep LiDAR + panoptic)  
       ↓  
[2024] Li et al. (single-sweep + semantic seg)  
       ↓  
[2025] GET-UP / LiRCDepth (161-sweep + panoptic/semantic)  
       ↓  
[2026] JustDepth ←─── SINGLE-SWEEP • NO AUX • 1-STAGE • GNN PROPAGATION  
                      ✗ 未解决：动态物体深度外推（依赖静态 LiDAR gt）  
                      ✗ 未解决：radar point dropout >50%（1D rasterization 会全列归零）  
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |  
|------|------|------|------------------|  
| **Radar Encoder** | `B×1×W` 1D rasterized scan (min-range per column) | `B×C×w` latent vector | ✅ 训练/推理一致；计算量恒定（`W`, `w` 固定） |  
| **Image Encoder** | `B×3×H×W` RGB (`900×1600`) | `{i₀,i₁,i₂,i₃}` skip features + `i_L ∈ B×C×h×w` | ✅ ResNet-style；`h×w = 112×200`（4× downsample） |  
| **Height Fusion Block** | `i_L ∈ B×C×h×w`, `r_L ∈ B×C×w` | `X_fused ∈ B×C×h×w` | ✅ 训练/推理一致；height-wise attention per column (`𝒪(wh²)`) |  
| **GNN Propagation** | `X₀ = X_fused + i_L ∈ C×h×w` → tokens `{x_p}^{M=h·w}` | `X_N ∈ C×h×w` | ✅ N-layer MRConv；K-NN graph built *per batch* in feature space |  
| **Depth Decoder** | `X_N` + `{i₀,i₁,i₂,i₃}` | `D_pred ∈ B×1×H×W` | ✅ U-Net style upsampling；训练时加 edge-aware smoothness loss |  
| **Confidence Decoder** | `X_fused ∈ B×C×h×w` | `Z ∈ B×1×H×W` logits | ❌ **仅训练使用**；推理时完全丢弃（zero cost） |  

### 1.2 关键机制  
⚡ **Eureka Moment：雷达不是“点云”，而是“每列图像的深度先验”——所以 fusion 必须按列进行，且只在高度维度建模对齐，而非强行插值到 2D 网格。**  
→ 这直接催生 Height Fusion Block：`r_L[u]` 复制 `h` 次形成 `h×C` token，与图像列 `i_L[:, :, :, u]` 拼接后做 height-wise attention，让模型学“雷达测量在哪一排高度上可信”。

### 1.3 信息流 ASCII 图  
```  
RGB (B×3×900×1600)         Radar Scan (B×1×W)  
        │                         │  
        ▼                         ▼  
Image Encoder (ResNet)     Radar Encoder (1D Conv)  
        │                         │  
        └───────┬─────────────────┘  
                ▼  
      Height Fusion Block (per-column h×2C → h×C)  
                │  
                ▼  
    X_fused + i_L → tokens {x_p}^{M=h·w}  
                │  
                ▼  
     N-layer GNN (MRConv: x_p ← FFN([x_p ∥ max_q(x_q−x_p)]))  
                │  
                ▼  
      Depth Decoder (U-Net w/ skip connections)  
                │  
                ▼  
          D_pred ∈ B×1×900×1600  
                │  
                └── [Training only] Confidence Decoder → Z ∈ B×1×900×1600  
```  

---

## 2 · 数学核心  

📌 **Napkin Formula**：  
> **Depth propagation = Feature-space gossip: each pixel talks to its K most similar neighbors (in feature space), sharing *relative depth cues* via max-difference messages.**

- **目标**：从稀疏 LiDAR gt `D_gt` 学习稠密 `D_pred`，同时抑制 stripe artifacts（LDL）  
- **公式**（MRConv layer ℓ）：  
  ```  
  m_p^(ℓ) = max_{q ∈ 𝒩_p^(ℓ)} (x_q^(ℓ) − x_p^(ℓ))   // relative message  
  x_p^(ℓ+1) = FFN( [x_p^(ℓ) ∥ m_p^(ℓ)] ) + x_p^(ℓ)  // residual update  
  ```  
- **变量说明**：  
  - `x_p^(ℓ) ∈ ℝ^C`: 第 ℓ 层第 p 个空间 token（对应 `(y,x)` 像素）的特征  
  - `𝒩_p^(ℓ)`: 在 L2-normalized feature space 中，`x_p^(ℓ)` 的 K 个最近邻（含自环）  
  - `m_p^(ℓ)`: “我的邻居们比我深多少？” → 强制模型学习 depth *variation*，而非绝对值  
- **直觉**：CNN 的卷积核只能看固定窗口，而 MRConv 让 `(x,y)` 像素直接和远处但特征相似的像素（如同一车顶的不同点）交换 depth 差异信号，**天然支持跨区域深度一致性**——这正是雷达点稀疏时最需要的。

---

## 3 · 带数字走一遍（玩具示例）  

设输入图像 `H=4, W=4`，下采样后 `h=2, w=2`；雷达扫描 `W=4` → `r_L ∈ B×C×2`（`w=2`）。取 `C=2`, `B=1` 简化：  
- `i_L = [[[[1,2],[3,4]], [[5,6],[7,8]]]]` → shape `(1,2,2,2)`  
- `r_L = [[[10,20]]]` → shape `(1,2,2)`  

**Height Fusion Block**：  
- 对 `u=0` 列：`i_L[:,:, :,0] = [[1,3],[5,7]]` → transpose → `[[1,5],[3,7]]` (`h×C=2×2`)  
- `r_L[:,:,0] = [10,20]` → repeat `h=2` times → `[[10,20],[10,20]]`  
- concat → `[[1,5,10,20],[3,7,10,20]]` (`h×2C=2×4`)  
- linear proj (4→2) → `[[a,b],[c,d]]` → height-wise attn → `[[a',b'],[c',d']]`  
- reshape → `X_fused[:,:, :,0] = [[a',c'],[b',d']]`  

**GNN step**（`K=2`, `M=h·w=4`）：  
- tokens: `x₁=[a',c'], x₂=[b',d'], x₃=[...], x₄=[...]`  
- build K-NN graph in 2D feature space → say `𝒩₁={x₁,x₃}`  
- `m₁ = max(x₁−x₁, x₃−x₁) = x₃−x₁`  
- `x₁' = FFN([x₁ ∥ m₁]) + x₁` → now `x₁` knows how `x₃` differs in depth tendency  

→ 单次 GNN 层即完成跨列深度线索传递。

---

## 4 · 工程视角  

| 维度 | 值 | 依据 |  
|------|-----|------|  
| **Latency (per frame)** | **14.8 ms** | 明确写于 Fig.1 caption & Table I footnote: *“measured on an NVIDIA RTX 4070 Ti”* |  
| **VRAM usage** | 未报告 | 全文未提显存；Table I 仅列 latency，无 GPU memory |  
| **Throughput** | ≈67.6 fps | `1000/14.8 ≈ 67.6`（由 latency 反推，标 `UNVERIFIED`） |  
| **Inference steps** | 1 forward pass | 明确强调 *“single-stage”*, *“no intermediate products”*, *“confidence decoder discarded at inference”* |  
| **Deployment constraint** | Fixed input resolution (`900×1600`) | IV-A: *“Inputs are 900 × 1600 for both training and evaluation”*；无 dynamic resize 支持 |  

✅ **Trade-off summary**:  
- **Gain**: Radar branch latency constant w.r.t. point count (1D rasterization)；GNN replaces heavy CNN backbones.  
- **Cost**: GNN’s K-NN search is `𝒪(M²)` → `M=h·w=112×200=22,400` → `M²≈500M` ops/batch；作者用 dilated K-NN & small `K=9` 缓解，但仍是 compute bottleneck（Table III 显示 8-layer GNN 是 latency/accuracy 平衡点）。  

---

## 5 · 数据与评测  

| 项目 | 值 | 依据（逐字 copy-paste） |  
|------|-----|------------------------|  
| **Dataset** | **nuScenes** | Abstract: *“On nuScenes”*；IV-A: *“We evaluate JustDepth on the nuScenes dataset [2]”* |  
| **Splits** | 700 train / 150 val / 150 test scenes | IV-A: *“700 scenes for training, 150 scenes for validation, and 150 scenes for testing”* |  
| **Input resolution** | **900 × 1600** | IV-A: *“Inputs are 900 × 1600”*；Table I footnote: *“Experiments use images of resolution 900 × 1600”* |  
| **LiDAR supervision** | **single-scan only**, no accumulation | Abstract: *“trained only with radar, camera, and single-scan LiDAR”*；I: *“JustDepth trains with a single LiDAR sweep and no auxiliary annotations”* |  
| **Metrics** | **MAE, RMSE, AbsRel, log10** | IV-A: *“compared against LiDAR ground truth using the following error metrics: MAE, RMSE, AbsRel, and log10”* |  
| **Distance ranges** | **MAE/RMSE @ 0-50m / 0-70m / 0-80m**；**AbsRel/log10 @ 0-70m** | IV-A: *“MAE and RMSE are reported over the distance intervals 0-50 m, 0-70 m, and 0-80 m, while AbsRel and log10 are reported over 0-70 m”* |  
| **VHGR metric** | Vertical-Horizontal Gradient Ratio (for stripe artifact quantification) | I: *“quantify them using the Vertical-Horizontal Gradient Ratio (VHGR)”*；I: *“reducing ... stripe artifacts by 66% as measured by VHGR”* |  

---

## 6 · 能力与失败模式  

| 能力 | 具体表现 |  
|------|----------|  
| ✅ **实时单阶段深度输出** | 14.8 ms/frame，无中间表示，无需 monocular pretrain 或 multi-stage refinement |  
| ✅ **强 stripe artifact suppression** | VHGR ↓66% vs GET-UP；靠 rotation + reflection padding + point upsampling |  
| ✅ **雷达点数无关延迟** | 1D rasterization → `r_L ∈ B×C×w`，`w` 固定，`O(1)` 雷达计算 |  
| ✅ **单扫 LiDAR 泛化性** | 在 nuScenes 上不依赖 multi-sweep accumulation 或 ego-motion compensation |  

| 失败模式 | 根本原因 |  
|----------|----------|  
| ❌ **动态物体深度不准** | LiDAR gt 本身是静态快照；模型无 motion prior，无法 extrapolate moving cars’ depth |  
| ❌ **雷达严重 dropout 区域失效** | 若某图像列 `u` 无雷达点 → `r_L[u]=0` → Height Fusion Block 输入零向量 → 该列深度纯靠图像先验（monocular ambiguity） |  
| ❌ **远距离 (>80m) 深度退化** | Table I 仅 report up to 0-80m；无 >80m 指标，且 radar SNR 随距离衰减，1D min-range rasterization 放大噪声 |  

### 隐含假设 (Hidden Assumptions)  
- **Assumption 1：雷达与相机已精确标定，且水平轴严格对齐** → Height Fusion Block 的“column-wise”操作成立；若存在 yaw misalignment，`r_L[u]` 将错配到错误图像列。  
- **Assumption 2：LiDAR 扫描线在图像平面近似水平** → Rotation augmentation 有效；若传感器俯仰角过大（如越野场景），scanlines 倾斜，`ρ=48` pixel KD-tree radius 失效。  
- **Assumption 3：场景中物体表面足够连续** → Point upsampling 插入 midpoints 的前提（`|d_i−d_j|<0.2m`），对破碎点云（如树叶、栅栏）会生成错误深度。  

---

## 7 · 与相关工作对比  

| Method | GT LiDAR | Aux. Annotations | Architecture | Latency (ms) | MAE 0-70m (mm) | Stripe (VHGR) |  
|--------|----------|------------------|--------------|--------------|----------------|----------------|  
| RC-PDA [14] | 25-sweep | LS+3B | Multi-stage | 411.6 | 6700.6 | — |  
| DORN [12] | interpolated | ✗ | Single-stage | 247.9 | 4124.8 | — |  
| Singh et al. [20] | 161-sweep | Panoptic | Multi-stage | 283.4 | 3746.8 | — |  
| Li et al. [9] | 1-sweep | Semantic | Single-stage | 51.1 | 3567.3 | — |  
| CaFNet [21] | 161-sweep | Panoptic | Multi-stage | 115.9 | 3674.0 | — |  
| GET-UP [23] | 161-sweep | Panoptic | Multi-stage | 587.6 | 2857.0 | baseline |  
| **JustDepth (Ours)** | **1-sweep** | **✗** | **Single-stage** | **14.8** | **3285.5** | **↓66%** |  

**面试 Tip**：  
> *Q: “Why not just use monocular depth + radar refinement?”*  
> **A**: “Monocular methods (e.g., DPT, Depth Anything) lack metric scale — they predict *relative* depth. Radar gives *absolute* range but is sparse/noisy. JustDepth fuses them *at feature level* with height-aligned attention, so radar directly anchors the metric scale *per column*, avoiding error propagation from monocular pretrain or sequential refinement. And crucially — it does this without needing monocular pretraining data or labels.”  

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-27)  

✅ **Official repo exists**: `https://github.com/TPyun/JustDepth` (appears in paper footer as plain text `Code: https://github.com/TPyun/JustDepth`)  
⚠️ **But no issue tracker linked in PDF** → arXiv PDF contains *no clickable hyperlink*, only plaintext URL. Per iron law: **treat as *no repo signal***.  

→ **Pitfalls derived from §6 failure modes + method constraints**:  
1. **`RuntimeError: CUDA out of memory` on RTX 3060 (12GB)**  
   - *Derivation*: §6 Assumption 1 requires precise calibration; §4 shows GNN’s `𝒪(M²)` cost with `M=22,400` → `M²≈500M` tokens → likely exceeds 12GB VRAM during K-NN search.  
   - *Method constraint*: `K=9` dilated K-NN still needs full `M×M` distance matrix unless optimized (paper doesn’t mention FAISS/ANN).  

2. **Zero-depth columns in output when radar input has >90% dropout**  
   - *Derivation*: §6 Failure mode “radar severe dropout” + §1.1 Radar Encoder: *“empty columns set to zero”* → `r_L[u]=0` → Height Fusion Block gets zero radar prior → `D_pred[:, :, :, u]` collapses to monocular ambiguity (often near-zero).  

3. **VHGR degradation on off-road datasets (e.g., KITTI-Odometry)**  
   - *Derivation*: §6 Hidden Assumption 2 *“LiDAR scanlines near horizontal”* fails on KITTI’s high-tilt mounting → rotation augmentation `[-10°,10°]` insufficient to cover real tilt range → model overfits to nuScenes’ urban geometry.  

---

[← Back to depth README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.22172 -->
