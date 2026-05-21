# 3DGS Family (3DGS 家族)

**Status:** v1 — 带立场的初稿. Hyperparams 标 UNVERIFIED.
**TL;DR:** 3D Gaussian Splatting 是终于让 photoreal radiance field 跑进机器人感知预算的表示。对空间智能真正重要的并非 2023 SIGGRAPH 原文一篇 — 而是四个衍生分支（动态、SLAM 耦合、抗锯齿、蒸馏），它们把一个渲染器变成了能用的场景表示。

---

## 为什么 3DGS 在空间智能场景下替代了 NeRF

NeRF 是对的*想法*（continuous radiance field），但包在错的*实现*里（MLP-per-ray，每个场景训练数小时，且对几何工具不透明）。3DGS 保留了 differentiable rendering 契约，但把 MLP 换成显式的一组 anisotropic gaussians，在 screen space 做 rasterize。就是这一个改动让该表示对具身 AI 可用：训练从数小时降到几分钟（消费级 GPU），渲染在桌面级显卡上达 100+ FPS，并且 — 这是关键 — gaussians 是*显式 primitive*，你可以检查、编辑、剪枝，并传给下游 policy。2024 年悄悄迁移的机器人团队，追的并不是 photoreal video；他们追的是一种能在控制环路内活下来的场景表示。

## 对具身 AI 重要的 4 个衍生分支

- **Dynamic (4D-GS lineage)** — 加上时间。让该表示能覆盖 demo 过程中物体会动的 manipulation 场景，而不仅是静态房间。
- **SLAM-coupled (GS-SLAM lineage)** — 从移动相机在线构建 gaussian set。这是从 "post-hoc reconstruction" 到 "live spatial map" 的桥梁。
- **Anti-aliased (Mip-Splatting)** — 修复一个静默失败模式：vanilla 3DGS 在 drone 和 AR headset 实际穿越的尺度范围下看起来很糟。
- **Original 3DGS** — 仍是值得先读的 baseline；其他几篇都是在补它的某个已知漏洞。

下面逐一解构。Cross-embodiment 对比（3DGS vs feed-forward pointmap vs neural mesh）放在 `crossing/representation-migration/`，不在这里。

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `3dgs_original_dissection.md` | Kerbl et al. SIGGRAPH 2023 — rasterizer、training loop、deployment envelope | ⚡ |
| `4dgs_dynamic_scenes.md` | Wu et al. CVPR 2024 — 针对运动物体的 temporal 扩展 | 🔧 |
| `gs_slam_dissection.md` | Yan et al. CVPR 2024 — SLAM 环路内的 gaussian map 构建 | 🔧 |
| `mip_splatting.md` | Yu et al. CVPR 2024 — 多尺度观看的 anti-aliasing 修复 | 🔧 |

## Boundary

本目录是 3DGS 谱系的 per-method 解构。**不**覆盖：

- Cross-representation 对比（3DGS vs feed-forward 3D vs voxel grids）→ `crossing/representation-migration/`
- Feed-forward 3D (VGGT, DUSt3R, π³) → `foundations/feed-forward-3d/`
- VLA policy 如何把 gaussian 场景作为 action feature 消费 → `bridge-to-vla/feature-cloud-to-action.md`
- Per-embodiment 部署笔记（drone-side 3DGS, manipulation-side 3DGS）→ `embodiments/<emb>/`

如需在其他场景下引用此处的 per-method 细节，请从那些地方链回这里。
