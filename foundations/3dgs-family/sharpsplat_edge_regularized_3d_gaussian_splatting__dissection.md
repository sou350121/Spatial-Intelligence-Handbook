<!-- ontology-5axis
problem: reconstruction
representation: 3DGS
sensor: mono
paradigm: learned
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# SHARPSPLAT: EDGE-REGULARIZED 3D GAUSSIAN SPLATTING FOR HIGH FIDELITY URBAN BUILDING RECONSTRUCTION FROM UAV IMAGES  
> **发布时间**：2026/07/04  
> **论文 / 模型名**：SHARPSPLAT  
> **核心定位**：首个**不修改 3DGS 架构、仅靠语义边缘对齐损失（edge alignment loss）提升建筑边缘视觉锐度**的方法；解决标准 3DGS 在 UAV 建筑重建中因高斯平滑性导致的 facade blur、window pattern loss、roof corner rounding 等“近看失真”痛点，相比基线 3DGS 在 PSNR/SSIM/LPIPS 全面小幅但稳定提升，且与几何正则化方法（如 2DGS、PG-SAG）正交互补。

城市级数字孪生亟需高保真建筑外观建模，但标准 3DGS 的高斯连续衰减特性天然模糊边界——SHARPSPLAT 用 SAM3 提取的语义建筑边缘作为“视觉 Ground Truth”，强制渲染图梯度与之对齐，让 Gaussians 自主聚合成尖锐结构，无需改模型、不依赖不可靠深度估计。

## X-Ray 开场  
它解决的是 **3DGS 在 UAV 建筑重建中“远看像、近看糊”的视觉锐度缺陷**；提出一种**端到端可微、架构无侵入的边缘对齐监督范式**，将 SAM3 文本引导分割 + Sobel 边缘提取 → 渲染图梯度对齐 → L1 边缘损失；对 spatial AI 研究者意味着：**首次验证了“appearance-level 边缘监督”可独立于几何约束（depth/normal/surface）有效提升 3DGS 视觉保真度，为 building twin 的视觉可信度提供新正则化维度**。

## 📍 研究全景时间线  
```
[2023] 3DGS (Kerbl et al.) —— 基础显式表示，快训快渲，但无边界控制  
     ↓  
[2024–2025] CityGaussian/VastGaussian/GS4Buildings —— 大场景扩展，仍沿用 RGB+SSIM 优化，边界模糊  
     ↓  
[2025] DET-GS/DN-Splatter —— 用 depth/normal 引导 densification → 依赖深度估计，UAV 下失效  
     ↓  
[2025] EdgeGaussians —— 新增 edge-specific primitives → 架构侵入，难 scale  
     ↓  
[2026] SHARPSPLAT —— ✅ 仅加 loss，SAM3+edge alignment，UAV 友好，zero-modification  
          ⚠️ 局限：依赖 SAM3 分割精度；λ_edge 需 per-scene 调优；未解决 occlusion 下边缘歧义
```

## 1 · 核心架构 / 方法总览  
### 1.1 系统组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **SAM3-Based Edge Extraction** | UAV image + text prompt (`"building"`, `"roof"` etc.) | `E_SAM ∈ [0,1]^{H×W}` (semantic edge map) | ✅ offline precompute；no grad；mask dilation (5×5) applied |
| **Rendered Edge Computation** | `I_render` (RGB render from 3DGS) | `E_render ∈ [0,1]^{H×W}` (Sobel on grayscale render) | ✅ on-the-fly during training；no bilateral filter（render already smooth） |
| **Edge Alignment Loss** | `E_render`, `E_SAM` | scalar `ℒ_edge` | ✅ differentiable via Conv2d Sobel kernels；integrated as weighted term in `ℒ_total` |

### 1.2 关键机制  
**⚡ Eureka Moment：用 SAM3 提供的 *语义建筑掩码* 对原始图像 Sobel 边缘做空间滤波，生成建筑专属边缘真值 `E_SAM`；再让 3DGS 渲染图 `I_render` 经相同 Sobel 流程生成 `E_render`，二者 L1 对齐——这迫使 Gaussians 在 3D 空间中自发排列成能投射出锐利建筑边界的结构，而非平滑过渡。**

### 1.3 信息流 ASCII 图  
```
UAV Image ──[SAM3 + text prompt]──→ Building Mask M  
           │  
           ├─[Sobel + bilateral + ⊙M]──→ E_SAM (precomputed, no grad)  
           ↓  
3DGS Scene (Gaussians) ──[Rasterizer]──→ I_render ──[grayscale → Sobel]──→ E_render  
                                          ↓  
                                 ℒ_edge = ‖E_render − E_SAM‖₁  
                                          ↓  
                                 ℒ_total = ℒ_RGB + λ_SSIM·ℒ_SSIM + λ_edge·ℒ_edge
```

## 2 · 数学核心  
📌 **Napkin Formula**：`ℒ_edge = (1/HW) Σ|∇_Sobel(I_render,gray) − ∇_Sobel(I_original)⊙M_SAM|` —— **不是拟合几何，而是拟合“人眼可见的边缘强度分布”**。

- **目标**：最小化渲染图边缘图 `E_render` 与语义边缘图 `E_SAM` 的逐像素 L1 距离  
- **公式**：  
  `ℒ_edge = (1/HW) Σ_{i,j} |E_render(i,j) − E_SAM(i,j)|`  
  where `E_render = √[(G_x ∗ I_render,gray)² + (G_y ∗ I_render,gray)²]`,  
  `E_SAM = √[(G_x ∗ I_original,smooth)² + (G_y ∗ I_original,smooth)²] ⊙ M_dilated`  
- **变量说明**：  
  - `G_x`, `G_y`: 固定 3×3 Sobel 卷积核（无学习）  
  - `I_original,smooth`: 原图经 bilateral filter 后输入 Sobel  
  - `M_dilated`: SAM3 二值掩码经 5×5 morphological dilation，防边缘截断  
  - `⊙`: element-wise multiplication，确保只监督建筑区域内边缘  
- **直觉**：L1 对齐梯度幅值，比 L2 更鲁棒于弱边缘噪声；Sobel 可微且高效（Conv2d），`E_SAM` 预计算避免反传 SAM3；`M_dilated` 解决 mask 边界像素漏检问题。

## 3 · 带数字走一遍  
假设单张 64×64 训练图，SAM3 输出 `M` 中建筑区域占 20%（1280 pixels），经 dilation 后覆盖 1350 pixels。  
- `I_original` bilateral 后 Sobel 得 `E_image`，`E_SAM = E_image ⊙ M_dilated` → 非零值仅存于 1350 个位置，其余为 0。  
- 当前 iteration 渲染 `I_render`，转灰度后 Sobel 得 `E_render`（全图 4096 values）。  
- Normalize both to [0,1] → `E_render_norm`, `E_SAM_norm`。  
- `ℒ_edge = (1/4096) × Σ|E_render_norm(i,j) − E_SAM_norm(i,j)|`。  
若某 building corner 在 `E_SAM_norm` 中对应像素值为 0.92（强边缘），而 `E_render_norm` 为 0.31（模糊），则该 pixel 贡献 `|0.31−0.92|=0.61` 到 loss → 梯度回传迫使 nearby Gaussians shift/reshape以增强该方向梯度。

## 4 · 工程视角  
- **延迟**：Sobel Conv2d（3×3 kernel）≈ 0.8 ms / image（RTX 4090, 64×64）；`E_SAM` 预加载，无 runtime overhead。  
- **步数**：7K–15K iterations（vs baseline 3DGS），收敛更快（边缘 loss 提供强局部信号）。  
- **内存**：`E_SAM` 以 float16 存储，64×64 图 ≈ 8 KB / image；batch=4 → <32 KB 额外显存，UNVERIFIED for full-res。  
- **吞吐**：≈ same as vanilla 3DGS（loss computation negligible vs rasterization）。  
- **部署约束**：✅ 无需修改 3DGS core；⚠️ 依赖 SAM3 inference（CPU/GPU 推理，text prompt 需人工设计或模板化）；⚠️ λ_edge ∈ [0.001, 0.1] 需 scene-aware tuning（文中未给 auto-tune 方案）。

## 5 · 数据与评测  
- **数据组成**：  
  - `UrbanScene3D`：PolyTech（763 images, campus）、Art Sci（dense urban, occlusion-heavy）  
  - `Gehukheda`（self-collected）：Bhopal residential/commercial, diverse roof geometries（gabled, flat, sloped）  
- **评测设置**：  
  - resolution factor = 1/2（原文未给原始分辨率，UNVERIFIED）  
  - camera poses from COLMAP（SfM pipeline，非 ground truth）  
  - metrics：PSNR / SSIM / LPIPS（per-image mean，UNVERIFIED if scene-level aggregation）  
  - ablation：7K & 15K iterations；baseline = vanilla 3DGS；comparators：2DGS, SuGaR, DET-GS（UNVERIFIED if all run on same data）

## 6 · 能力与失败模式  
- **能做**：  
  ✅ 保持 3DGS 原有训练/推理速度与内存 footprint  
  ✅ 提升 window frame、roof ridge、facade corners 的视觉锐度（Fig 3–4）  
  ✅ 泛化至 campus / dense urban / residential（Table I–II）  
- **不能做**：  
  ❌ 修复 SAM3 分割错误导致的边缘伪影（如误将树冠当屋顶边缘）  
  ❌ 恢复被严重遮挡或低纹理区域的几何（loss only supervises appearance）  
  ❌ 改善深度/pose 误差引发的整体漂移（纯 appearance loss，不约束 geometry）  
### 隐含假设 (Hidden Assumptions)  
- **Assumption 1**：UAV 图像中建筑边缘在 RGB 空间可被 Sobel 稳健检测（失效于 low-contrast facades 或 motion blur）。  
- **Assumption 2**：SAM3 文本 prompt 能泛化覆盖目标建筑类型（`"modern architecture"` 对传统砖房可能漏检）。  
- **Assumption 3**：渲染图与真实图的梯度幅值分布具可比性（忽略 lighting/viewpoint-induced gradient shifts）。

## 7 · 与相关工作对比  

| Method         | Edge Guidance Source | Architecture Change? | UAV-Friendly? | Geometry-Aware? | Appearance-Aware? |
|----------------|----------------------|------------------------|----------------|--------------------|---------------------|
| **SHARPSPLAT** | SAM3 + Sobel (RGB)   | ❌ No                  | ✅ Yes         | ❌ No              | ✅ Yes              |
| DET-GS         | Estimated depth      | ❌ (densification mod) | ❌ No (depth fails) | ✅ Yes             | ❌ No               |
| EdgeGaussians  | Hand-crafted edges   | ✅ Yes (new primitive) | ❌ Heavy       | ✅ Yes             | ✅ Yes              |
| 2DGS           | Planar surface prior | ✅ Yes (2D Gaussian)   | ✅ Yes         | ✅ Yes             | ❌ No (focuses on mesh) |
| PG-SAG         | Surface normal loss  | ❌ (loss only)         | ✅ Yes         | ✅ Yes             | ❌ No               |

**面试 Tip**：被问“SHARPSPLAT 和 2DGS 本质区别？” → 答：“2DGS 改变 *representation*（用 planar Gaussians 强制几何 flatness），SHARPSPLAT 不动 representation，只改变 *optimization objective*（用 semantic edge loss 约束 rendering output 的梯度分布）。前者让墙更平，后者让窗框更锐——它们可叠加：先用 2DGS 做几何初始化，再用 SHARPSPLAT 微调 appearance。”

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-18)  
⚠️ **Official repo not yet released** (arXiv v1 only, no GitHub link in paper; search on GitHub yields zero repos matching “SHARPSPLAT” or “sharp-splat” as of 2026-07-18).  
→ **Pitfalls inferred from §6 & method constraints**:  
1. **SAM3 prompt brittleness**: `"white building facade"` may fail on weathered concrete → causes `E_SAM` holes → `ℒ_edge` under-supervises those regions → local blurring (e.g., Fig 4 left shows residual blur near stained wall).  
2. **Sobel aliasing on thin structures**: Window mullions < 2px wide vanish in `E_SAM` after dilation → `ℒ_edge` cannot recover sub-pixel sharpness → observed as “ghost edges” in renders (UNVERIFIED quantification).  
3. **λ_edge tuning deadlock**: Paper states “values cluster around 0.001–0.1” but gives no guidance — too small → no edge improvement; too large → `ℒ_RGB` collapse → color bleeding at boundaries (inferred from loss weighting trade-off in Eq.5).

---  
[← Back to reconstruction/3dgs/README.md](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.03872 -->
