<!-- ontology-5axis
problem: Object 6-DoF pose (foundation)
representation: Mesh template + RGBD features
sensor: RGBD + Object mesh
paradigm: Learned + DiffRender refine
time: Online
ref: ../../cheat-sheet/ontology.md §7
-->

# FoundationPose (新物体 6D 位姿，无需逐物体训练)

> **发布时间**: 2024-03 (CVPR 2024 *best paper* — Wen, Yang et al., NVIDIA)
> **论文 / 模型**: FoundationPose (arXiv 2312.08344)
> **核心定位**: 一个模型给*任意*物体估计 6D pose — 用 CAD mesh 或 ~16 参考图 — 无需 per-object fine-tune.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · 2024–2026 manipulation 栈的 pose-foundation 默认.
**TL;DR:** 第一个配得上 "foundation" 的 6D pose 模型. 丢任何新物体（mug、螺丝刀、打包胶带）进去就能得到 pose 而无需重训. Render-and-compare + 扩散风迭代精化，由训在 ~1M+ 合成物体上的模型打分. 这是 2026 团队不应再训 per-object pose head 的原因.

**X-Ray.** 2024 前的 pose 模型（PoseCNN、DenseFusion、GDR-Net）要求 *per-object 训练*. FoundationPose 打破这堵墙：一次在巨量合成数据上训，泛化到任意未见物体 — 用 mesh 或 ~16 参考图. 2024 年 Object pose 加入 foundation-model 俱乐部，与深度（Depth Anything）和 3D（VGGT 前驱）同列.

---

## 📍 研究全景时间线

```
2017       2019         2021       2022          2024 (HERE)         2025+
PoseCNN ─► DenseFusion ► GDR-Net ► MegaPose ───► FoundationPose ──► video / temporal
└─ per-object supervised ──┘  └── novel obj, mesh required ──┘  └─ mesh-free ─┘
```

第一篇在生产精度下处理未见物体*无 mesh* 的论文. 时序 / 视频继任者在 2026 仍处早期.

---

## 1 · 架构总览

### 1.1 系统组件对比

| Module | Input | Output |
|---|---|---|
| Hypothesizer | RGB-D crop + obj rep | N 个 pose hypotheses |
| Refinement (diffusion-style) | hypothesis + render | refined (multi-step) |
| Scorer | rendered vs observed | scalar score |
| Object rep (mesh-free) | ~16 ref images | implicit neural object |

**Render-and-compare 包在学到的 scorer 里**，配扩散风迭代精化. *Scorer 才是 foundation model* — 跨物体泛化，因为它训练时见过百万个.

### 1.2 ⚡ Eureka Moment

> **把 pose 视为"给 rendered hypothesis 与观测的匹配度打分" — 让 scorer 成为 foundation model，不是 regressor.**

之前工作从特征 regress 6D pose → per-object 脆弱. FoundationPose 反转：render N 个候选（免费、确定性）并*学打分*（从合成先验泛化）.

### 1.3 信息流

```
   RGB-D crop ──┐
                ▼
   (mesh) ─► hypothesizer ─► N candidates ─► render each ─► scorer ─► top-k
   or                                                                    │
   (16 refs) ─► implicit obj ──────────────────────────────────────────► ▼
                                                  refine (K iters) → final pose + confidence
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  pose*  =  argmax_{T in candidates}  scorer( render(obj, T),  observed_crop )
```

Pose 是从候选集*选出*，不是 regress. Scorer 是学到的泛化机器.

| Symbol | Meaning |
|---|---|
| `T = (R, t)` | 6D pose |
| `render(obj, T)` | 在 `T` 处 rasterize 的 RGB-D |
| `scorer(·, ·)` | 学到的对比 scorer |
| `K` | refinement 迭代数 (~5 `UNVERIFIED`) |

**Intuition.** 渲染是几何 oracle；scorer 是感知 oracle. 合起来 → pose 变成 pose 空间中的*搜索*，scorer 作为导航梯度.

---

## 3 · Worked example: 螺丝刀的位姿

RealSense D435，screwdriver 检测到 → crop. 有 CAD mesh.

1. **Hypothesize** ~252 旋转假设（icosphere × in-plane）；translation 从 depth 重心.
2. **Render** 每个候选到 crop.
3. **Score** (rendered, observed) → 252 个标量；top-5 在 GT ~10° 内.
4. **Refine** top-5 × K=5 步；top-1 → ~2° 旋转、~3 mm translation `UNVERIFIED`.
5. **Final score** ~0.92 → 发给 grasp planner.

端到端桌面 ~80–150 ms `UNVERIFIED`，Orin ~300–550 ms `UNVERIFIED`. Mesh-free 模式用 implicit neural object 替换 renderer.

---

## 4 · Engineering view

| Stage | Desktop `UNVERIFIED` | Orin `UNVERIFIED` |
|---|---|---|
| Render (×252) | 20–40 ms | 80–150 ms |
| Scoring | 30–50 ms | 100–200 ms |
| Refinement (×5) | 30–60 ms | 100–200 ms |
| **End-to-end** | **~80–150 ms** | **~300–550 ms** |

Multi-object 不批处理则线性 scale. 蒸馏后 Orin 上单物体 30 Hz tracking 可行；2026 年桌面所有物体 30 Hz 在边缘不就绪.

**Deployment.** 新 SKU：16 张照片 + 30 秒 mesh-free 拟合 → 就绪. Tracking 模式：每 N 帧重检，从先验 refine → ~30 ms/frame `UNVERIFIED`.

---

## 5 · Data & eval

训在 Objaverse / ShapeNet 的 ~1M+ 合成物体（论文声称；准确 `UNVERIFIED`），用域随机光照 / 材料 / 背景. 在 LM-O、YCB-V、T-LESS 上评估 — 比 MegaPose 高 6–18 AR `UNVERIFIED`. Mesh-free 变体比 model-based 落后几个 AR 但是更重要的真实世界能力.

---

## 6 · Capabilities & failure modes

**赢：** 几分钟内 onboard 新 SKU；中度遮挡鲁棒；无 CAD 物体的 mesh-free 路径.

**败于：** 无纹理的严重对称（旋转歧义固有）；透明 / 镜面物体（depth sensor 先失败）；物体 <~10 mm `UNVERIFIED`；无干净 2D 检测的重杂乱.

### 6.x GitHub 实地失败（atlas 联动）

- **GitHub-validated**：NaN scores 部署灾难 — 对应 [#53 (27 comments, closed-without-explicit-fix)](https://github.com/NVlabs/FoundationPose/issues/53)，多用户在不同 GPU / CUDA 复现但根因（fp16 / 老 GPU 路径）无官方诊断；"closed 不等于已修"是 maintainer wontfix 信号，与 depth 阵营 FoundationStereo #121 同模式，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：输入资产门槛吃掉 ~30% 部署 — mesh / CAD 要求（[#83](https://github.com/NVlabs/FoundationPose/issues/83)·[#60](https://github.com/NVlabs/FoundationPose/issues/60)·[#32](https://github.com/NVlabs/FoundationPose/issues/32)）+ depth 预处理（[#44](https://github.com/NVlabs/FoundationPose/issues/44)）+ 首帧 mask 选不准导致 drift 传染（[#186](https://github.com/NVlabs/FoundationPose/issues/186)·[#279](https://github.com/NVlabs/FoundationPose/issues/279)）；论文 model-free 卖点在 issue 区落地为 "要么扫 mesh 要么没法用"，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 6.1 Hidden Assumptions

- **Depth 通道可用且可靠.** 仅 RGB 退化 5–15 AR `UNVERIFIED`. 反射金属 → 实际上仅 RGB.
- **物体刚性.** 线 / 布料不在范围；articulated 物体仅给主导 link 的 pose.
- **参考图覆盖旋转半球（mesh-free）.** 单半球不泛化到背面.
- **物体在图像中 ≥~10 mm.** 微小 SMD / 细螺丝低于有效分辨率.
- **光照大致 photo-realistic.** 域随机化覆盖广变化，不覆盖单色 IR.

这些是*输入域*假设，不是参数问题 — fine-tune 也修不了.

---

## 7 · Comparison & interview tip

| Model | Novel obj? | Mesh req? | Synth-only? | Real-time? | Year |
|---|---|---|---|---|---|
| PoseCNN | ❌ | yes | no | ~30 Hz | 2017 |
| DenseFusion | ❌ | yes | no | ~16 Hz | 2019 |
| GDR-Net | ❌ | yes | partial | ~25 Hz | 2021 |
| MegaPose | ✅ | **yes** | ✅ | ~3 Hz | 2022 |
| **FoundationPose** | ✅ | **optional** | ✅ | ~5–10 Hz (Orin, distilled `UNVERIFIED`) | 2024 |

> **🎤 Interview Tip.** "为从未见过的物体做 pose estimator？" — *"FoundationPose 在 mesh-free 模式下 — 用 ~16 张参考图 onboard，然后跑 pose tracker. 有 CAD mesh 用它来多拿几个精度分."* "我会在 YCB 风格数据上训 PoseCNN" 已三年过时.

---

## References

- FoundationPose — Wen et al. *CVPR 2024*（best paper）. https://arxiv.org/abs/2312.08344
- MegaPose — Labbé et al. *CoRL 2022*. https://arxiv.org/abs/2212.06870
- GDR-Net — Wang et al. *CVPR 2021*. https://arxiv.org/abs/2102.12145
- DenseFusion — Wang et al. *CVPR 2019*. https://arxiv.org/abs/1901.04780
- PoseCNN — Xiang et al. *RSS 2018*. https://arxiv.org/abs/1711.00199
- BOP. https://bop.felk.cvut.cz/

## Boundary

把 FoundationPose 解构为 **novel-object 6D pose foundation model**. 需 mesh 的前驱 → [`megapose_dissection.md`](./megapose_dissection.md). Per-embodiment 用法 → [`embodiments/manipulation/`](../../embodiments/manipulation/). Action 消费 → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./overview.md)
