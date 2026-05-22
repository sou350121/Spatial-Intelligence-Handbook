# Depth Foundation Models

**Status:** v1 — 带立场的入口页. 跨链接假设兄弟 wedge 已存在.

Monocular depth 曾是个客厅戏法 — 在 KITTI 上训、在 KITTI 上 demo、在厨房手机照上失败. MiDaS 系列（Ranftl et al. 2020）打破这点，靠的是在多域混合汤里训练并预测*相对* inverse depth，正因它拒绝承诺米制而到处泛化. 五年后该领域分裂：一条**相对深度 foundation 轨**追 photometric 真实感与泛化（Depth Anything v1/v2、MoGe），一条**度量深度 foundation 轨**烧入相机内参，让输出实际是米（Metric3D v1/v2、ZoeDepth、UniDepth）. 这个分裂重要，因为机器人对尺度不能耸肩 — 一个抓在"大约 0.4 metric unit"附近的 manipulator 是会摔杯子的 manipulator.

立体 foundation 模型（FoundationStereo）位于 monocular 轨旁，是负担得起两相机 + baseline 时的廉价度量深度答案. 它们继承"在巨量合成上训、零样本泛化"的同一配方，但完全绕开 monocular 尺度歧义. 对机器人，实际问题很少是"NYUv2 上哪个模型最好" — 而是"我的 embodiment 能容忍相对深度吗，还是必须要米；如果要米，我愿不愿为立体付廉价代价？"

---

## Table of contents

| File | Topic | Tier |
|---|---|---|
| [depth_anything_v2_dissection.md](./depth_anything_v2_dissection.md) | Depth Anything v2 — unlabeled-data 的胜利（+ DA3 2025-11 unified any-view）| ⚡ relative |
| [metric3d_dissection.md](./metric3d_dissection.md) | Metric3D v1/v2 — 用 canonical-camera 技巧得到度量深度（⚠️ in-the-wild 419% off）| 🔧 metric |
| [moge_dissection.md](./moge_dissection.md) | MoGe v1 + MoGe-2 — affine-invariant 几何 loss + multi-head（v2 加 metric）| 📖 relative |
| [foundationstereo_dissection.md](./foundationstereo_dissection.md) | FoundationStereo — NVIDIA 的零样本立体（⚠️ 无 confidence map）| 🔧 metric (stereo) |
| [**depth_models_comparison.md**](./depth_models_comparison.md) **★ NEW** | 4 模型横向对比：解释度 / Working Range / Sensitivity / In-the-Wild Reality | — |
| [**classical_stereo_primer.md**](./classical_stereo_primer.md) **★ NEW** | Epipolar geometry + Rectification + SGM + Triangulation —— deep stereo 之前必懂的经典几何（取材 HKUST ELEC5660 L7, BSD 3-Clause）| primer |

---

## 如何读这条车道

- 在搭 **manipulator**？先看 `metric3d_dissection.md`. 你要米，有固定 wrist camera，canonical-camera 技巧正是你的朋友.
- 在搭 **drone**？四个都读，然后跳到 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). Monocular 相对深度超 30 m 无用；立体在长 baseline 上重量受限；答案是"与 VIO 融合".
- 在搭 **VLA policy**？先读 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) 看 action head 实际消费什么 — 通常是带 `scale_flag` 的 point cloud，这把你逼回 metric vs relative 争论.

Cross-reference: [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) 覆盖多视角 feed-forward 3D，将深度作为多种输出之一吸收 — 不同范式，重叠用例.
