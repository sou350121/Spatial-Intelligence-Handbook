<!-- ontology-5axis
problem: Novel-view synthesis
representation: Implicit MLP radiance field
sensor: RGB + poses
paradigm: Hybrid-DiffRender (MLP + volume rendering)
time: PerScene-Optimization
ref: ../../cheat-sheet/ontology.md §7
-->

# NeRF 原作解构 (NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis)

> **Publication:** ECCV 2020 (best paper)
> **Paper:** Mildenhall et al. arXiv: https://arxiv.org/abs/2003.08934
> **Core position:** 把 novel-view synthesis 从 graphics pipeline 变成 differentiable optimization 的论文，让 "scene as neural function" 变得可行。

**Status:** v1 — 带立场。除非标 `UNVERIFIED`，数字来自论文。
**TL;DR:** NeRF 的贡献不是 MLP。它是 (1) 经典 volumetric rendering 作为可微 forward model、(2) positional encoding 打破 MLP 的低频偏置、(3) 5D 输入（xyz + view dir）支持视角相关效果 三者的组合。每一块在 2020 之前都已存在。把它们组合成 per-scene optimization 才改写规则 — 也保证了后续每一篇都在尝试修的"数小时训练"痛点。

**X-Ray.** NeRF 之前，photoreal novel-view synthesis 需要 multi-view stereo + mesh + texture（对透明 / 反射脆）或 light-field rig（不实用）。NeRF 把场景参数化为 `(x,y,z,θ,φ) → (RGB, σ)`，通过渲染已知视角并与 GT 对比来训练 MLP。约 50 张 RGB 图就能出 photoreal 3D，无需 mesh、无需 MVS。对空间智能研究者，NeRF 是首次可信的 "scene-as-neural-network" — 之后所有 learned 3D 表示（包括 3DGS）的概念祖先。

## 📍 Research panorama timeline

```
1996         2014         2019           2020          2022          2023            2025?
Light    ► PointNet  ► DeepSDF /     ► NeRF (ECCV) ► Instant-NGP ► 3DGS         ► Feed-forward
fields     (points)    OccNet          YOU ARE HERE   (mins not     (SIGGRAPH,    3D (VGGT,
(Levoy)                (implicit 3D)                  hours)        100 FPS)      no per-scene)
                                       └─ per-scene MLP, hours train, sub-1 FPS render ─┘
```

NeRF 处在 light-field / implicit-3D 思想撞上 positional-encoded MLP 的位置。2021–2024 的一切都在迭代它的弱点。

---

## 1 · Core architecture

### 1.1 System overview

| Component | Input | Output |
|---|---|---|
| Positional encoding | `(x,y,z,θ,φ)` | High-freq feature (60 + 24 dims) |
| 8-layer MLP_σ | encoded xyz | density σ + 256-d feat |
| 1-layer MLP_c | feat + encoded view dir | RGB |
| Volume renderer | (σ, RGB) along ray | Pixel color |

MLP 约 1M 参数。负担在*每像素 192 次评估*（coarse 64 + fine 128 hierarchical sampling）× 800×800 像素 × 数万次 iteration。

### 1.2 ⚡ Eureka moment

> **Volumetric rendering 端到端可微 — 当场景是连续函数时；而 positional encoding 是唯一能让小 MLP 表示高频连续函数的东西。**

任一拿走 NeRF 都失败。无 volumetric rendering → 像素级梯度无法回到场景。无 positional encoding → MLP 学到模糊低频拟合（论文 Figure 4：同网络、无 encoding，雾蒙蒙土豆）。

### 1.3 Flow diagram

```
   Camera pose                          Pixel color (GT)
        │                                       │
        ▼                                       │
   sample N points along ray                    │
        │                                       │
        ▼                                       │
   positional encoding → MLP_σ → σ              │
        │                                       │
        ▼                                       │
   MLP_c(+view dir) → RGB                       │
        │                                       │
        ▼                                       │
   Σ Tᵢ(1-exp(-σᵢδᵢ))cᵢ ──► Predicted RGB ──► MSE
                                                │
                                                ▼
                                       Backprop to MLP weights
```

---

## 2 · Math core

### 📌 Napkin Formula

```
C(ray) = ∫ T(t) · σ(r(t)) · c(r(t), d) dt        # alpha-blend density-weighted color
PE(p) = [sin(2⁰πp), cos(2⁰πp), ..., sin(2ᴸ⁻¹πp), cos(2ᴸ⁻¹πp)]
```

积分是经典 Max-1995. Encoding 把 3D 坐标提升到 60 维特征，跨频段 `2⁰...2⁹`，因此 MLP 无需变宽就能学高频变化。

### 2.1 Variables

| Symbol | Meaning |
|---|---|
| `r(t) = o + td` | 从原点 `o` 沿方向 `d` 的射线 |
| `σ(x)` | Volume density (1/length) |
| `c(x, d)` | View-dependent RGB |
| `T(t) = exp(-∫₀ᵗ σ ds)` | Transmittance |
| `L` | Encoding freq bands (10 xyz, 4 view) |

### 2.2 Quadrature + hierarchical sampling

按分层 bin 离散化：`wᵢ = Tᵢ · (1 − exp(-σᵢδᵢ))`, 像素 = `Σ wᵢ cᵢ` — 严格 alpha-compositing. Coarse pass (64) 找密度；fine pass (128) 在峰值附近重采样. **~192 MLP evals/pixel = 慢的来源.**

---

## 3 · Worked example: 一条射线，四个采样

穿过 t=2 处实心球的射线。在 t = {0.5, 1.5, 2.5, 3.5} 采样。

| t | σ | δ | α | T | w | color |
|---|---|---|---|---|---|---|
| 0.5 | 0.01 | 1 | 0.010 | 1.000 | 0.010 | sky |
| 1.5 | 0.02 | 1 | 0.020 | 0.990 | 0.020 | sky |
| 2.5 | 20.0 | 1 | ≈1.0 | 0.970 | 0.970 | red |
| 3.5 | 5.0 | 1 | 0.993 | ≈0 | ≈0 | behind |

像素 ≈ 0.97·red + 0.03·sky — "球挡住天空"。梯度流过每个采样；颜色错 → MLP 联合更新密度 + 颜色.

---

## 4 · Engineering view: 为何慢

| Cost | Default |
|---|---|
| Rays / iter | 4096 |
| Samples / ray | 192 (64 + 128) |
| MLP forward | ~1M params, 8-layer, ~5µs / eval on V100 `UNVERIFIED` |
| Iterations | 200–300k |
| Wall-clock | 1–2 days / scene on single V100 (2020) |
| Inference render | ~30s / frame |

`300k × 4096 × 192 ≈ 2.4×10¹¹ MLP forwards per scene`. 不改数据结构没法加速. 每篇 NeRF 加速论文都在攻击这个数字.

NeRF 训练是*尴尬地 per-scene*：跨场景零权重迁移. Feed-forward 3D (VGGT, 2024+) 最终爬过的概念悬崖.

---

## 5 · Data and evaluation

- **Synthetic Blender:** 8 scenes, ~100 views, white background, GT poses. PSNR ~31 dB, LPIPS ~0.05.
- **Real LLFF (forward-facing):** 8 handheld captures, COLMAP poses. PSNR ~26 dB.
- **Metrics:** PSNR / SSIM / LPIPS 在 held-out views — 之后每篇 NeRF 论文逐字照抄的协议。

仅限有界、前景中心、静态、纹理良好场景. Mip-NeRF 360 (2022) 即 "去掉这些假设"，因此成了更难的 benchmark.

---

## 6 · Capabilities and failure modes

**Does:** 从 ~50 calibrated views 做静态有界场景 photoreal novel-view synthesis；view-dependent effects；连续表示，任意位置可查询.

### 6.1 Hidden assumptions

NeRF 只在以下条件成立时 work；每条在实践中悄悄破坏：

- **Static scene** — 每个像素必须对应同一世界. 动的人、风中树叶 → 破. (D-NeRF, HyperNeRF 修复.)
- **Dense, calibrated views** — 需要 COLMAP 精确的 per-image 位姿. &lt;10 张图就崩. (PixelNeRF、feed-forward 3D 修复.)
- **Single bounded volume** — 模型在单位立方体内查询；天空 / 远建筑 → 垃圾. (Mip-NeRF 360 修复.)
- **Lambertian-ish lighting** — 强镜面、透明玻璃 → view-dir MLP 补不了. (Ref-NeRF 部分修复.)
- **Per-scene training 可接受** — 假设每个 asset 数小时是可接受的. 机器人从未接受. (Instant-NGP 修速度；feed-forward 3D 修 "per-scene 本身".)

后续每篇挑一个补 — 这正是该谱系 *碎片化*的原因：要组合 3–4 个变体才能凑出可用系统，而 3DGS 把多数折进单一表示.

### 6.3 GitHub 实地失败（atlas 联动）

- **GitHub-validated**：原 `bmild/nerf` 已事实归档 — spam issue (#217) 长期未关、TF 2.x 兼容 (#216) 无人补、数据集 GoogleDrive 链接失效 (#214/#213)，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。"经典 NeRF 论文 repo" 在 2026 只能作历史参考，复现请走 `yenchenlin/nerf-pytorch` 或 nerfstudio `vanilla-nerf`。
- **GitHub-validated**：`yenchenlin/nerf-pytorch` 同样 stale — 官方 checkpoint 损坏 (#151)、Blender 数据链接失效 (#155)、OOM kill (#147) 是教学用户最常见三连击；维护者已转向 robotics 多年，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。

---

## 7 · Comparison and interview tip

| Aspect | NeRF | Instant-NGP | Mip-NeRF 360 | 3DGS |
|---|---|---|---|---|
| Training | 1–2 days | ~5 min | ~7h `UNVERIFIED` | ~30 min |
| Render | &lt;1 FPS | ~10 FPS | &lt;1 FPS | 100+ FPS |
| Scene scale | Bounded | Bounded | Unbounded | Bounded |
| Editable? | No | No | No | Yes |
| Best for | Teaching | Fast experiments | Quality bench | Robotics |

> **🎤 Interview tip.** "NeRF 为何重要？" — 正确答案：*"它是首次让 differentiable volumetric rendering + positional encoding 组合成可信的端到端 pipeline；2020 之后的一切 — 包括 3DGS — 都在补 NeRF 的某个具体弱点（速度、规模、动态、可编辑性）。"* 错答："首个 3D MLP"。DeepSDF / OccNet 在它之前；NeRF 的贡献是*渲染*契约，不是网络.

---

## References

- **NeRF** — Mildenhall et al. *ECCV 2020.* https://arxiv.org/abs/2003.08934
- **DeepSDF** — Park et al. *CVPR 2019.* https://arxiv.org/abs/1901.05103
- **Instant-NGP** — 见 `instant_ngp_dissection.md`
- **Mip-NeRF 360** — 见 `mip_nerf_360_dissection.md`
- **3DGS** (继任) — `foundations/3dgs-family/3dgs_original_dissection.md`

## Boundary

仅解构原始 NeRF. **不**覆盖表面重建 NeRF（NeuS, VolSDF）、generative（DreamFusion）或 dynamic（D-NeRF）. 速度 / 规模 follow-up 是本目录中的兄弟；替代故事在 `foundations/3dgs-family/`.

---

[← Back to NeRF Family README](./overview.md)
