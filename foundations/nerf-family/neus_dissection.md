<!-- ontology-5axis
problem: Surface reconstruction (neural implicit SDF)
representation: Implicit SDF (zero-level-set) + view-dependent radiance
sensor: RGB + poses (COLMAP)
paradigm: Hybrid-DiffRender (SDF + unbiased volume rendering + GD)
time: Per-scene optimization (~hours)
ref: ../../cheat-sheet/ontology.md §8.3
-->

# NeuS 解构 (NeuS: Learning Neural Implicit Surfaces by Volume Rendering for Multi-view Reconstruction)

> **Publication:** NeurIPS 2021
> **Paper:** Wang, Liu, Liu, Theobalt, Komura, Wenping Wang. arXiv: https://arxiv.org/abs/2106.10689 · Code: https://github.com/Totoro97/NeuS
> **Core position:** 把 NeRF 的"体密度场"换成"signed distance field" — 在保留 NeRF 体渲染可微特性的同时，让结果可以直接 marching cubes 出 mesh. NeRF 谱系里"能交付几何"的第一篇里程碑。

**Status:** v1 — 带立场。除非标 `UNVERIFIED`，数字来自论文。
**TL;DR:** NeRF 输出 density (体)，但 robotics / graphics 下游要 surface (2-manifold mesh). NeuS 用 SDF 替换 density，并推导出一种 **无偏 (unbiased)** 的 SDF→体渲染权重函数 — 这是关键贡献：之前 IDR / DVR 等用 surface rendering 需要 mask 监督；之前 UNISURF 等 SDF + 体渲染做法有 first-order bias（surface 估计有系统性偏移）. NeuS 证明并修复了这个 bias，让"无 mask、纯多视图 RGB → 高质量 mesh"第一次成立。同期 VolSDF (Yariv NeurIPS 2021) 平行抵达类似终点；两者并列成为 SDF-NeRF 学派的 founding pair.

**X-Ray.** NeRF 给体素流体；MVS 给水泥三角面；中间一直缺一座桥. NeuS 是桥. 体渲染 (NeRF) 损失 → SDF 网络梯度 (DeepSDF 谱系) → marching cubes (1987) 抽 zero-level-set → mesh. 三个老技术 + 一个新无偏权重公式 = 让 "几何可微优化" 第一次能直接产出 game/robot 能用的几何. 对空间智能工程师，这是 *表示选择决定下游可用性* 的教科书案例 — radiance vs surface 不是审美问题，是 "下游 collision check / physics sim 能不能用" 的硬约束.

## 📍 Research panorama timeline

```
2019            2020         2021                    2022         2023            2024
DeepSDF      ► NeRF       ► NeuS / VolSDF         ► MonoSDF    ► Neuralangelo  ► 2DGS / SuGaR
(implicit       (radiance,   YOU ARE HERE           (mono cue)   (high-fid       (3DGS-based
SDF, no         no mesh)     SDF + unbiased                       hash grid)     surface,
render)                      volume integral                                     real-time)
                             └─ NeRF 的 "几何分支" ─────────────────────────────┘
                                                                  └─ 3DGS 抢走多数应用 ┘
```

NeuS 在"radiance 谱系开始为 robotics / graphics 分叉出几何分支"的分水岭. 2023 后 Neuralangelo 接棒高保真；2024 后 2DGS / SuGaR 用 3DGS 表示重打这场仗 — NeuS 仍是教学与"小物体高精度 mesh" 的首选 baseline.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Input | Output |
|---|---|---|
| SDF MLP (`f`) | `(x,y,z)` | `s ∈ ℝ` (signed distance) + 256-d feat `UNVERIFIED` |
| Color MLP (`c`) | feat + `n = ∇f` + view dir `d` | RGB |
| SDF→density mapping `ϕ_s` | `s` | logistic density (sharpness `s` 可学) |
| Volume renderer | (α, RGB) along ray | Pixel color |
| Marching cubes (offline) | `f` 在 grid 上采样 | Triangle mesh |

8-layer SDF MLP + 4-layer color MLP；总参数级别同 NeRF 量级. 关键差别在 SDF MLP 的输出 `s` 同时承担两个角色：① SDF 函数本身（zero-level-set 即 surface）② 通过 logistic CDF `ϕ_s` 映射到一个 "concentrated near surface" 的 density-like 权重，喂给体渲染.

### 1.2 ⚡ Eureka moment

> **NeRF 输出 density (体)；mesh 要 surface (2-manifold). 用 SDF 取代 density 看起来直接 — 但 naive 做法 (UNISURF / IDR-volumetric) 的 surface 估计有 first-order bias. NeuS 推导出唯一 unbiased 的 SDF→volume weight 公式：让权重峰值精确落在 zero-level-set，且与 view direction 无关.**

bias-free 的证明是核心 — 不是工程优化是数学保证. 没有它，SDF 学到的 zero-level-set 会被 alpha-compositing 偏移；marching cubes 出来的 mesh 几何上不准. 有它，纯 RGB 监督就够，*不需要 mask 监督*（IDR / DVR 的老前提被打破）.

### 1.3 Flow diagram

```
   Camera pose                          Pixel color (GT)
        │                                       │
        ▼                                       │
   sample N points along ray                    │
        │                                       │
        ▼                                       │
   SDF MLP f(x) → s + feat                      │
        │                                       │
        ├──► n = ∇f(x)  (normal)                │
        │                                       │
        ▼                                       │
   Color MLP c(feat, n, d) → RGB                │
        │                                       │
        ▼                                       │
   ϕ_s(s) → density-like → α (unbiased!)        │
        │                                       │
        ▼                                       │
   Σ Tᵢ αᵢ cᵢ ──► Predicted RGB ──► MSE        │
                                                │
                                                ▼
                                  Backprop to SDF + Color MLP
                                                │
                                                ▼
                       (offline) marching cubes on f → mesh
```

note: `ϕ_s` 的 sharpness 参数 `1/s` 随训练 anneal（从粗到细），让早期梯度遍布全空间、后期集中到 surface 邻域.

---

## 2 · Math core

### 📌 Napkin Formula

```
ϕ_s(x) = s · e^(-sx) / (1 + e^(-sx))²        # logistic PDF, sharpness s
Φ_s(x) = (1 + e^(-sx))^(-1)                   # logistic CDF

# Unbiased SDF→opacity (NeuS 关键贡献):
α_i = max( (Φ_s(f(p_i)) − Φ_s(f(p_{i+1}))) / Φ_s(f(p_i)),  0 )

# 体渲染合成 (同 NeRF):
C(ray) = Σ Tᵢ αᵢ cᵢ,    Tᵢ = Π_{j<i} (1 − αⱼ)

# Eikonal 正则化 (DeepSDF 谱系标配):
L_eik = E_x [ (‖∇f(x)‖ − 1)² ]
```

第二行是论文的灵魂. naive 做法 `α_i = 1 − exp(−ϕ_s · δ)` 把 ϕ_s 当 density 来用，会给出 first-order biased weight peak（峰值不在 SDF=0 处）. NeuS 推导的 CDF-difference 形式被证明是 first-order unbiased 且 occlusion-aware.

### 2.1 Variables

| Symbol | Meaning |
|---|---|
| `f(x): ℝ³ → ℝ` | SDF MLP；`f(x) > 0` 在物体外，`f(x) = 0` 在 surface，`f(x) < 0` 在内 |
| `n = ∇f` | surface normal（隐式从 SDF 导出，不需独立输出） |
| `Φ_s` | logistic CDF；`s` = sharpness，可学的 trainable scalar |
| `ϕ_s` | logistic PDF（density-like） |
| `α_i` | 该采样点的 opacity（unbiased 公式） |
| `T_i` | 累积透射率 |
| `L_eik` | Eikonal 正则项，强制 `‖∇f‖ ≈ 1`（让 `f` 行为像真正的 SDF 而非任意 level-set） |

### 2.2 Why first-order bias matters

如果 weight peak 偏移 surface 0.5×δ（采样步长一半），mesh extraction 会把 surface 沿 view-ray 拉一层；多视图叠加 → mesh 系统性变胖 / 变瘦 / 变嵌套 ghost. NeuS 论文 §4.1 用 1D 玩具反例展示 naive 公式如何被 view-dependent shading 拖偏；CDF-difference 形式则在 first-order 完全消除该项. 这是为何同期 VolSDF (Yariv 2021) 平行抵达类似终点 — 两组人独立意识到 "bias-free integration" 是关键 unlock.

---

## 3 · Worked example: 一条射线，三个采样

穿过 t=2 处 SDF 球面（半径 1）的射线，球心在 t=2. 采样在 t = {1.0, 2.0, 3.0}.

| t | f(p) | Φ_s(f(p)) (s=20) | α_i (unbiased) | T_i | weight |
|---|---|---|---|---|---|
| 1.0 | +1.0 (球外远) | ≈ 1.0000 | — | 1.000 | ≈ 0 |
| 2.0 | 0.0 (恰在表面) | 0.5000 | (1.000−0.500)/1.000 = 0.500 | 1.000 | 0.500 |
| 3.0 | −1.0 (球内) | ≈ 0.0000 | (0.500−0.000)/0.500 = 1.000 | 0.500 | 0.500 |

像素 ≈ 0.5·c(t=2.0) + 0.5·c(t=3.0). **weight peak 精确落在 surface (t=2)**；naive 公式会把峰挪到 t=2.5（biased into the object）. 训练时这 0.5 weight 把 surface 处的颜色与 GT 对齐；同时 Eikonal 推 `‖∇f‖→1` 让 f 行为正常.

---

## 4 · Engineering view: 为何还是慢

| Cost | Default |
|---|---|
| Rays / iter | 512 `UNVERIFIED` |
| Samples / ray | 64 + 64 (hierarchical, importance) |
| Iterations | ~300k |
| Wall-clock | ~14h on single V100 per DTU scene `UNVERIFIED` |
| Mesh extraction | marching cubes on 512³ grid，~分钟级 |
| Inference render | 比 NeRF 更慢（每点要算 ∇f via autograd） |

NeuS 不是为速度设计的 — 它是 **几何质量 over 速度** 的取舍. Eikonal regularization + SDF normal 通过 autograd 反向 → 单 iter 比 NeRF 慢 ~1.5–2×. Neuralangelo (CVPR 2023) 把 hash grid + numerical gradient 引进来才把训练拉回数小时；2DGS / SuGaR (2024) 把这场仗整体搬到 3DGS 表示上.

---

## 5 · Data and evaluation

- **DTU (15 scans):** 室内桌面物体，固定环形多视图，COLMAP 位姿，GT 由结构光 scanner. Chamfer distance ↓ vs IDR / NeRF / VolSDF / UNISURF. NeuS 不需 mask 时 Chamfer ≈ 0.84 `UNVERIFIED`；用 mask 时进一步降.
- **BlendedMVS (7 scenes):** 更复杂多视图前景物体. NeuS 视觉质量明显胜 NeRF mesh extraction（NeRF 的 isosurface 几乎不可用）.
- **Metrics:** Chamfer distance 为主（surface reconstruction 协议）；novel-view PSNR / SSIM 作为附带验证.

只限有界、前景中心、静态、纹理足. 弱纹理大区域（白墙）SDF 学不准 → mesh 表面 wavy. 反射 / 透明 物体（与 NeRF 同病）的 view-dependent c 撑不住 → 几何被拉扭. MonoSDF (Yu 2022) 注入 monocular depth/normal 作为先验来缓解这些洞.

---

## 6 · Capabilities and failure modes

**Does:** 从 ~50 calibrated views 重建有界静态物体的 high-fidelity mesh；无需 mask；mesh 可直接进 Blender / Unity / Mujoco；同时附带 NeRF 级 novel-view radiance.

### 6.1 Hidden assumptions

NeuS 只在以下条件成立时 work；每条在实践中悄悄破坏：

- **Object-centric, bounded scene** — SDF MLP 在单位球内查询；远景 / 天空被 NeRF++ 风格 outer NeRF 替代或直接丢. 全景场景 → 表面 collapse.
- **Lambertian-ish 物体** — view-dep 颜色靠 4-layer 小 color MLP；金属、玻璃、高镜面 → 几何被拉成弯曲 ghost 来"解释"高光.
- **足够纹理多样性** — 大面积纯色墙 / 白瓷器 → SDF 没有梯度信号 → mesh wavy. 这是 MonoSDF 加先验来补的洞.
- **耐心 (~半天 GPU)** — per-scene 训练；切场景从零；不接受 → Neuralangelo / 2DGS 是下一站.
- **COLMAP 给得出位姿** — 反光 / 缺纹理物体 COLMAP 本身就失败；NeuS 无能力自救（不像 BARF / NeRF-- 联合优化位姿）.

### 6.2 Comparison vs sibling methods

| Method | Output | Mask 需要 | Bias-free | 速度 | 备注 |
|---|---|---|---|---|---|
| **NeRF** (ECCV 2020) | radiance (density) | ✗ | n/a | hours | mesh 不可用 |
| **IDR** (NeurIPS 2020) | SDF | ✓ 必需 | surface render | hours | mask 是硬门槛 |
| **UNISURF** (ICCV 2021) | occupancy | ✗ | first-order biased | hours | mesh 有偏 |
| **VolSDF** (NeurIPS 2021) | SDF | ✗ | bias-bounded (≠ 0) | hours | 与 NeuS 同代 |
| **NeuS** (NeurIPS 2021) | **SDF** | **✗** | **first-order unbiased** | **~14h** | 本篇 |
| **Neuralangelo** (CVPR 2023) | SDF + hash grid | ✗ | unbiased | ~hours | 高保真接棒 |
| **2DGS / SuGaR** (2024) | 2D Gaussian disk | ✗ | n/a | min–hours | 抢走多数应用 |

### 6.3 GitHub 实地失败（atlas 联动）

- **GitHub-validated**: `Totoro97/NeuS` (~1.8k★ / 224 fork / ~90 open issue) 的开源 repo 在 2024+ 基本进入"半归档"状态 — 维护者去做后续工作（VolSDF / Neuralangelo 谱系），issue 区的 [自定义数据 preprocess 示例 Drive 链接失效 (#142)](https://github.com/Totoro97/NeuS/issues/142)、[COLMAP `im2pose` 报错无回应 (#136)](https://github.com/Totoro97/NeuS/issues/136)、[mesh 是否带颜色的基础问题无回应 (#139)](https://github.com/Totoro97/NeuS/issues/139) 都呈"open 多月无 maintainer triage"形态. 2026 新读者跑 NeuS 复现 = 半天调环境（钉 PyTorch 1.8 / 老 CUDA）+ 半天对齐自定义位姿；想在生产线用建议直接走 `nerfstudio` 的 `neus-facto` 实现或 Neuralangelo / 2DGS.

---

## 7 · Comparison and interview tip

| Aspect | NeRF | NeuS | Neuralangelo | 2DGS |
|---|---|---|---|---|
| Output | radiance only | SDF + radiance | SDF + radiance | 2D Gaussians + surface |
| Mesh? | ✗ (isosurface 假) | ✓ marching cubes | ✓ 高保真 | ✓ 直接 |
| Mask 需要 | n/a | ✗ | ✗ | ✗ |
| Training | 1–2 day | ~14h `UNVERIFIED` | ~数小时 | 30 min–几小时 |
| Render | <1 FPS | <1 FPS | <1 FPS | 100+ FPS |
| Best for | NVS only | 小物体高精度 mesh | 高保真 mesh | 实时 + mesh |

> **🎤 Interview tip.** "为什么不直接 NeRF 跑完抽 isosurface？" — 正确答案：*"NeRF 的 density 不是 SDF — density 在表面前后都有非零值，isosurface 阈值无明确物理意义，每个场景要手调；而且 multi-view 一致性差，抽出来的 mesh 有 floating artifact 和 surface 厚度. NeuS 把表示直接换成 SDF (zero-level-set 严格定义 surface)，并证明了 unbiased 体渲染权重公式 — 让纯 RGB 监督就能学出 mesh-ready 的几何，无需 mask. 这是 representation choice 决定 downstream 可用性的教科书案例."* 错答："NeuS 比 NeRF 准". 准是结果，*为何准* 是 SDF + bias-free 整合.

> **🎤 Interview tip (follow-up).** "NeuS vs VolSDF 区别？" — 两者同年 NeurIPS 平行工作；都是 SDF + 体渲染，都不需 mask. 数学路线不同：NeuS 推导一个 first-order unbiased 的权重公式；VolSDF 用 Laplace-like 密度 + bounded sampling error. 工程上 NeuS 实现更简洁（更易复现），VolSDF 在某些 scan 上 Chamfer 略好. 选哪个看下游：教学 / baseline 通常 NeuS；想要更严格 sampling error bound 选 VolSDF.

---

## References

- **NeuS** — Wang et al. *NeurIPS 2021.* https://arxiv.org/abs/2106.10689
- **VolSDF** (并列) — Yariv et al. *NeurIPS 2021.* https://arxiv.org/abs/2106.12052
- **IDR** (前置, mask-based) — Yariv et al. *NeurIPS 2020.* https://arxiv.org/abs/2003.09852
- **UNISURF** (前置, biased) — Oechsle et al. *ICCV 2021.* https://arxiv.org/abs/2104.10078
- **MonoSDF** (后继, mono prior) — Yu et al. *NeurIPS 2022.* https://arxiv.org/abs/2206.00665
- **Neuralangelo** (后继, hash grid) — Li et al. *CVPR 2023.* https://research.nvidia.com/labs/dir/neuralangelo/
- **BakedSDF** (后继, real-time) — Yariv et al. *SIGGRAPH 2023.* https://arxiv.org/abs/2302.14859
- **2DGS** (替代谱系) — Huang et al. *SIGGRAPH 2024.* https://arxiv.org/abs/2403.17888
- **NeRF** (radiance 父) — 见 `nerf_original_dissection.md`
- **Instant-NGP** (速度兄) — 见 `instant_ngp_dissection.md`

## Boundary

仅解构 NeuS 原作 (NeurIPS 2021). **不**覆盖：表面 GS 变体 (2DGS / SuGaR — 属 3DGS family)、动态 SDF (D-NeuS 变体)、generative SDF (DreamFusion 谱系). 速度后继 (Neuralangelo) 与质量后继 (MonoSDF / BakedSDF) 在 References. 3DGS 时代的几何替代方案见 `foundations/3dgs-family/`.

---

[← Back to NeRF Family README](./overview.md)
