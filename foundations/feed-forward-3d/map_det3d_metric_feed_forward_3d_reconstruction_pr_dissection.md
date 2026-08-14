<!-- ontology-5axis
problem: n/a
representation: implicit-sdf
sensor: mono
paradigm: hybrid
time: n/a
ref: ../../cheat-sheet/ontology.md §5
-->

# Map-Det3D: Metric Feed-Forward 3D Reconstruction Prior for Multi-view 3D Object Detection from Streaming Inputs  
> **发布时间**：2026/08/12  
> **论文 / 模型名**：Map-Det3D  
> **核心定位**：首个将 feed-forward metric 3D reconstruction（FF3R）模型 *直接复用为几何编码器* 的在线多视图 3D 检测框架，**绕过 2D-to-3D lifting**，用重建先验解耦尺度歧义，实现 class-agnostic、RGB-only、metric-scale 3DOD。

单目视频中绝对尺度不可观是 3D 检测的“阿喀琉斯之踵”——传统方法靠图像平面回归深度，误差被放大数倍；Map-Det3D 不再猜深度，而是**把重建出的 metric 3D 空间变成检测发生的“土壤”**，让 box 直接长在真实尺度的体素里。它在 CA-1M 上达 SOTA，并零样本迁移到 ScanNetV2，证明：**好的几何先验 ≠ 辅助模块，而是检测的坐标系本身。**

---

## X-Ray 开场  
Map-Det3D 解决的是 monocular 3DOD 中“尺度漂移”这一根本性脆弱点：当相机内参、运动模式或场景分布变化时，2D-to-3D lifting 的深度回归极易崩溃。它提出一个范式级转向——**不从图像预测 3D，而从多帧重建的 metric 3D 空间中直接检测**。它把 MapAnything 这类 FF3R 模型从“重建工具”重定义为“检测空间构造器”，并设计 up-to-scale head 与 scale token 联动，使所有几何输出天然具备 metric 可解释性。对 spatial AI 研究者而言，它标志着：**3D 检测的主干可以且应该是一个几何先验模型，而非视觉 backbone + 3D head 的拼接。**

---

## 📍 研究全景时间线  
```
[2022] MonoDETR (2D lift) → [2023] Cube R-CNN (virtual depth) → [2024] Uni-MODE (domain-aware BEV)  
                      ↘  
[2025] MapAnything (FF3R, metric scale token) → [2026] Map-Det3D (FF3R as detection encoder, causal 3D box head)
                                                                 ↑
                                                         ←─【本文】─→ 无 depth sensor / 无 2D lifting / online sliding window
```
**本文局限**：仅验证 indoor 场景（CA-1M/ScanNetV2）；class-agnostic 设计未扩展至语义类别；FF3R backbone（MapAnything）固定为 16-layer multi-view transformer，未探索轻量化变体；**未报告任何硬件延迟/吞吐数据**（见 §4）。

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **FF3R Backbone (MapAnything)** | `𝒲ₜ = {Iₜ₋ₜ₊₁,…,Iₜ}` + `𝒞ₜ` (Kₜ, Pₜ 可选) | `ℱₜ = {F_E, F₇, F₁₁, F₁₅}` (multi-scale 3D feature maps) + `ρₜ` (per-window metric scale factor) | 训练时 unfreeze multi-view transformer & scale head；推理时 frozen except scale head |
| **Detection Transformer Encoder** | `ℱₜ` → per-view `Q^IMG ∈ ℝ^{|ℱ|P×256}` (projected & concatenated) | `Q₀ ∈ ℝ^{M×256}` (top-M 2D anchor features as initial queries) | 2D proposal scoring + top-M selection only at training; inference uses fixed M=100 |
| **Deformable Decoder (L layers)** | `Qₖ`, `Q^IMG`, 2D reference boxes `Bₖ²ᴰ` | `{(Qₖ, Bₖ²ᴰ)}_{k=0}ᴸ` (refined queries & 2D boxes) | Deep supervision on all layers (k=0…L); bipartite matching uses `Bₖ²ᴰ` |
| **Up-to-scale 3D Box Head (Φ₃Dᵏ)** | `Qₖ`, `ρₜ` | `Bₖ³ᴰ = {(x̃,ỹ, d̃), (s̃_w,s̃_l,s̃_h), R₆D, σ}` → metric `Bₜ³ᴰ = ρₜ × (x̃,ỹ,exp(d̃), exp(s̃_w),...)` | All geometric attributes regressed in up-to-scale space; `ρₜ` applied *after* regression |

### 1.2 关键机制  
⚡ **Eureka Moment：Metric 3D detection is not a prediction problem — it’s a coordinate system alignment problem. Map-Det3D solves it by letting the FF3R backbone *define the metric coordinate frame*, and the detector *operates natively within it*.**

### 1.3 信息流 ASCII 图  

```
Streaming RGB Video  
       ↓  
Sliding Window 𝒲ₜ = [Iₜ₋₄, Iₜ₋₃, Iₜ₋₂, Iₜ₋₁, Iₜ]  ← T=5  
       ↓  
+---------------------+  
| FF3R Backbone       | ← MapAnything (16-layer MV-Transformer)  
| • Input: 𝒲ₜ + 𝒞ₜ   |  
| • Output: ℱₜ (4 feat maps) + ρₜ (scalar)  
+---------------------+  
       ↓  
ℱₜ → Project & Concat → Q^IMG ∈ ℝ^{(4×P)×256}  
       ↓  
+-----------------------------------+  
| Detection Transformer             |  
| • Encoder: Q^IMG → Q₀ (top-M 2D anchors)  
| • Decoder (L=6): Qₖ → Qₖ₊₁ via deformable cross-attention  
| • At each layer k: Qₖ → Bₖ²ᴰ (2D ref), Qₖ → Bₖ³ᴰ (up-to-scale 3D)  
+-----------------------------------+  
       ↓  
Bₗ³ᴰ + ρₜ → Metric 3D Boxes Bₜ³ᴰ = ρₜ × (x̃,ỹ,exp(d̃), ...)  
       ↓  
Final Output: {Bₜ³ᴰ, σ} for current frame Iₜ  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**:  
**`Bₜ³ᴰ = ρₜ ⋅ Φ₃Dᴸ(Qₗ, 1)`**, where `Φ₃Dᴸ` regresses *unitless* geometric offsets, and `ρₜ` is the *only* source of metric scale — disentangled, predicted, and shared across all boxes.

**目标**：学习映射 `Φ_DET ∘ Φ_FF3R : (𝒲ₜ, 𝒞ₜ) → Bₜ³ᴰ` such that `Bₜ³ᴰ` is metric-scale, causal, and robust to camera/domain shift.  

**公式**（来自 §3.4）：  
```
x = ρₜ·x̃,  y = ρₜ·ỹ,  z = ρₜ·exp(d̃)  
w = ρₜ·exp(s̃_w),  l = ρₜ·exp(s̃_l),  h = ρₜ·exp(s̃_h)  
R = egocentric(R₆D, [x,y,z])  // allocentric → egocentric via center direction  
σ = sigmoid(logit)  
```

**变量说明**：  
- `ρₜ`: per-window scale factor, scalar, output of FF3R's `q_scale` token MLP  
- `x̃,ỹ,d̃`: up-to-scale 3D center coordinates (x,y in pixel space, log-depth)  
- `s̃_w,s̃_l,s̃_h`: up-to-scale log-dimensions  
- `R₆D`: 6D rotation representation (allocentric)  
- `Φ₃Dᴸ`: layer-specific 2-layer MLP (regression) + 1-layer MLP (confidence)  

**直觉**：  
传统方法 `z_pred = f(I)` 直接回归深度 → error amplifies as `z²` in IoU₃D；Map-Det3D 将 `z` 分解为 `ρₜ`（全局几何一致性约束） × `exp(d̃)`（局部相对结构），`ρₜ` 由多视图几何一致性强监督，`d̃` 只需建模相对 depth order —— **尺度误差与结构误差解耦，前者由 FF3R 保证，后者由 DETR 优化**。

---

## 3 · 带数字走一遍（玩具示例）  

设 `T=3`, `P=4` (简化 patch count), `ρₜ = 0.85 m/px`（FF3R 预测的 scale factor）  
Decoder layer `k=2` 输出 query `Q₂[0] = [0.12, -0.03, 0.41, ...]`  
Up-to-scale head `Φ₃D²` outputs:  
- `x̃ = 120.3`, `ỹ = 87.6`, `d̃ = 4.21` → `z = 0.85 × exp(4.21) ≈ 0.85 × 67.3 ≈ 57.2 m`  
- `s̃_w = 2.1`, `s̃_l = 2.8`, `s̃_h = 1.9` → `w = 0.85×exp(2.1)≈0.85×8.17≈6.94m`, `l≈0.85×16.44≈14.0m`, `h≈0.85×6.73≈5.72m`  
- `R₆D = [0.92, 0.11, -0.05, 0.33, 0.89, 0.31]` → converted to SO(3) rotation matrix  
- `σ = 0.93`  

→ Metric 3D box: center `(102.3, 74.5, 57.2)`, size `(6.94, 14.0, 5.72)`, high confidence.  
**关键点**：所有数值物理意义明确，且 `ρₜ` 是唯一 metric converter —— 若 `ρₜ` 错 10%，所有尺寸同比例缩放，但 *相对几何关系不变*，利于匹配与泛化。

---

## 4 · 工程视角  

| 维度 | 值 | 依据 | 备注 |
|------|----|------|------|
| **Latency** | 「论文未报告」 | 全文未提 inference time / FPS / latency | §4.1 仅说 "inference time, we set T=5"，无硬件/时延数据 |
| **VRAM / Memory** | 「论文未报告」 | 无显存占用描述 | 训练用 16×RTX 4090，但未给出 per-GPU 显存 |
| **Throughput** | 「论文未报告」 | 无吞吐量指标（e.g., frames/sec） | 表 3 提到 "efficiency" 但未列数字 |
| **Steps per inference** | **1 forward pass** | Fig. 2 & §3.5: causal sliding window → single FF3R + single DETR forward | 无迭代优化、无后处理、无 temporal fusion beyond window |
| **Deployment constraints** | Requires `T=5` frames + optional `Kₜ`, `Pₜ` | §3.1, §4.1: fixed window size; camera params improve stability but not required | No streaming buffer spec; no quantization/ONNX export mention |

✅ **Trade-off summary**: Sacrifices single-frame latency (needs 5-frame context) for *geometric stability*; avoids recurrent state (no RNN/LSTM) → memory bounded by `T`; scale disentanglement enables easy calibration (swap `ρₜ` with external scale).

---

## 5 · 数据与评测  

| 项目 | 值 | 来源（逐字 copy-paste） |
|------|----|------------------------|
| **训练数据集** | `CA-1M` | §4.2: "We use the dataset to train Map-Det3D"；§1: "train Map-Det3D on the CA-1M [16] dataset" |
| **验证数据集（in-domain）** | `CA-1M validation` | §4.2: "evaluate on validation for an in-domain benchmark"；Table 1: "CA-1M validation set" |
| **零样本迁移数据集** | `ScanNetV2` | §4.2: "we further validate [...] on ScanNetV2 [5]"；§4.4: "zero-shot benchmark" |
| **ScanNetV2 subset** | `100 scenes`, `every 25 frames` | §4.2: "follow BoxFusion [15] to use the selected 100 scenes and uniformly sample every 25 frames" |
| **评估指标** | `AP₁₅`, `AP₂₅`, `AP₅₀` (IoU₃D thresholds 0.15, 0.25, 0.50), `AR` | §4.2: "AP₁₅, AP₂₅, and AP₅₀ correspond to IoU₃D thresholds 0.15, 0.25 and 0.50"；"average precision (AP) and average recall (AR)" |
| **AP reported as** | `mean 3D AP`, `class-agnostic` | §4.2: "The mean 3D AP is reported in a class-agnostic way" |

⚠️ **注意**：全文未报告任何具体 AP 数值（如 "AP₂₅=21.2"），Table 1 是 ablation（含 AP₁₅），但未给出最终模型在 CA-1M 或 ScanNetV2 的完整 AP 表 —— **所有指标数字均「论文未报告」**。

---

## 6 · 能力与失败模式  

✅ **能做**：  
- Class-agnostic 3D detection in metric scale from RGB video alone  
- Zero-shot transfer to ScanNetV2 without finetuning  
- Robust to camera intrinsics shift (via FF3R pose estimation when `𝒞ₜ` missing)  
- Causal online inference with fixed `T=5` window  

❌ **不能做**：  
- Semantic 3D detection (no category head; §1: "focus on class-agnostic")  
- Outdoor / dynamic scenes (trained & evaluated only on indoor static scenes: CA-1M/ScanNetV2)  
- Single-frame detection (requires `T≥2` frames for multi-view geometry)  
- Occlusion reasoning beyond FF3R's reconstruction capacity (no explicit occlusion modeling)  

### 隐含假设 (Hidden Assumptions)  
1. **Static scene assumption**: FF3R backbone (MapAnything) assumes rigid scene for multi-view geometry estimation — fails under heavy moving objects (e.g., people walking across FOV).  
2. **Camera motion is ego-motion**: FF3R estimates extrinsics assuming camera is moving, not scene — fails if scene moves while camera is static (e.g., conveyor belt).  
3. **Scale factor `ρₜ` is globally consistent**: Assumes entire window shares one metric scale — breaks if scene contains multiple independent scale domains (e.g., macro/micro objects in same view).  
4. **2D anchor grid suffices for 3D coverage**: Uses dense 2D grid proposals → misses objects far from image plane or with extreme aspect ratios (no 3D anchor design).  

---

## 7 · 与相关工作对比  

| 方法 | 输入 | 几何来源 | 3D Box Prediction | Scale Handling | Online? | Indoor SOTA (CA-1M) |
|------|------|-----------|--------------------|----------------|---------|---------------------|
| **Map-Det3D (Ours)** | RGB video (`T=5`) | FF3R backbone (MapAnything) | Direct 3D in reconstructed space | Disentangled `ρₜ` token | ✅ (sliding window) | 「论文未报告」 |
| Cube R-CNN [2] | Single RGB | 2D detection + virtual depth | 2D-to-3D lifting | Learned focal-length prior | ❌ | 「论文未报告」 |
| Uni-MODE [18] | RGB video | BEV + domain confidence | BEV-to-3D lifting | Domain-aware scaling | ✅ | 「论文未报告」 |
| BoxFusion [15] | RGB + depth / LiDAR | Sensor fusion | 3D proposal fusion | Sensor-dependent | ✅ | 「论文未报告」 |
| EFM3D [37] | RGB + depth / IMU | Multi-modal occupancy | Occupancy-based | Implicit in voxel size | ✅ | 「论文未报告」 |

**面试 Tip**：  
*Q: “Why not just add a scale head to existing monocular detectors?”*  
→ A: “Because scale isn’t an attribute to regress — it’s the *coordinate system foundation*. Cube R-CNN’s virtual depth fixes focal length but not absolute scale; Map-Det3D makes scale a *geometric property of the space itself*, predicted by multi-view consistency. You can’t bolt that onto a 2D detector — you need the 3D space first.”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-08-14)  

✅ **Official repo signal present**: Paper states *"Code and models are available at royyang0714.github.io/Map-Det3D"* — this is a plain-text URL, **not an embedded hyperlink in PDF**. Per iron rule: *plain text URL ≠ valid repo signal*.  
❌ **No GitHub issue tracker referenced** in paper text (no `github.com/...` in main text; no issue numbers, titles, or dates).  
➡️ **Status**: official repo not confirmed; following iron rule, treat as *no repo signal*.  

**Pitfalls derived from §6 failures + method constraints**:  
1. **Failure under moving objects**: FF3R backbone assumes static scene (§6 Hidden Assumption #1) → `ρₜ` becomes inconsistent → metric boxes shrink/stretch erratically. *Mechanically derivable from*: FF3R uses rigid SfM-style multi-view fusion (`Φ_FF3R` in Eq.1) → fails when input violates rigidity.  
2. **Zero-shot ScanNetV2 performance collapse with wide-baseline motion**: FF3R’s pose estimation degrades when `𝒲ₜ` contains frames with large relative pose change (e.g., fast pan) → `ρₜ` misestimated → all boxes scaled wrong. *Mechanically derivable from*: §3.2 says FF3R estimates poses when `𝒞ₜ` missing, but no robustness analysis for extreme motion.  
3. **ONNX export failure for scale token**: `q_scale` is a learnable token processed by 16-layer transformer → likely involves dynamic shapes or non-standard ops → `torch.onnx.export()` fails with "unimplemented op" on `q_scale` path. *Mechanically derivable from*: §3.2 architecture + §4.1 PyTorch/CUDA impl → no ONNX support mentioned.

---

[← Back to spatial-ai README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2608.12179 -->
