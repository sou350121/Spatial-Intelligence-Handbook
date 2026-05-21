# 🧮 Spatial Math — Region Landing (空间数学工具箱)

> **Status:** v1 — 新区，立场鲜明的草稿。按 AGENTS.md `foundations/` 政策，narrative 用简体中文。
> **Depth tier:** 📖 foundations 基线（1× 深度；跨 embodiment 工具箱，不是维护者锚点）
> **TL;DR:** 数学工具箱 —— 每一篇 SLAM / VIO / feed-forward 3D 论文都默认你已经掌握的七个基础工具。SE(3) / quaternions / BA / pose graph / EKF-MSCKF / IMU preintegration。对应 VLA-Handbook 那边的 `math_for_vla.md`。

---

## 这一区为什么独立存在 (Why this region exists)

其他每一个 `foundations/` 子区都假设读者已经会说 SE(3) 的李代数、会拆 BA 的 Schur complement。ORB-SLAM3 第二页就把 `Sim(3)` 砸在你脸上；OpenVINS 开篇就是 MSCKF state propagation；VINS-Mono 在第一组方程里就埋着 Forster-2017 IMU preintegration。

新读者撞到这些墙就会反弹。这一区是**工具箱** —— 短小、立场鲜明、数学优先的入门篇，让你重新打开任何经典 SLAM / VIO 论文时不用在脑子里翻译符号。

它是 `foundations/feed-forward-3d/` 的**对偶面**：

- Feed-forward 3D（VGGT 系，2024+）试图*让大部分这种数学消失*。
- 这一区记录的是*2026 年仍然在每一个量产的航空 / 地面 / AR 系统里运行的*那部分数学。

两边都得懂。只懂 feed-forward，真机 drone 一抖你就束手无策；只懂经典，又看不见整个领域往哪里走。

> 这是 foundations 的**工具箱第一站**，对应 VLA-Handbook 那一侧 `math_for_vla.md` 的地位。先把这七篇通读，再去拆 ORB-SLAM3 / OpenVINS / VINS-Mono 的代码会平顺很多。

---

## 推荐入口 (Recommended entries)

读 SLAM / VIO 论文遇到不懂的数学时，按下面顺序回查：

| File | 一句话 | 依赖前置 |
|---|---|---|
| [`se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md) ★ | SO(3) / SE(3) / 李代数 exp-log map —— *所有*后续内容的前提 | 无 |
| [`quaternions_and_rotations.md`](./quaternions_and_rotations.md) | quaternion vs rotation matrix vs Euler —— Hamilton vs JPL 约定战争 | SO(3) primer |
| [`bundle_adjustment.md`](./bundle_adjustment.md) ★ | 每个 SLAM 背后的数学 —— cost、Jacobian 稀疏性、Schur complement、LM | SO(3) + quaternions |
| [`pose_graph_optimization.md`](./pose_graph_optimization.md) | 后 BA 阶段的闭环 —— g2o / GTSAM / Ceres 生态 | BA + 李群 |
| [`bayesian_filtering_ekf_msckf.md`](./bayesian_filtering_ekf_msckf.md) ★ | EKF / UKF / MSCKF —— 为什么 OpenVINS 保留一窗口位姿而非 landmark | 线性代数复习 |
| [`imu_preintegration_math.md`](./imu_preintegration_math.md) | Forster *T-RO 2017* —— 为什么 VINS-Mono 能在相机帧之间扔掉 IMU 样本 | SO(3) + EKF |

★ = 只读三篇的话，读这几篇。

---

## 角色定位 (Pick by role)

| 角色 | 入口 |
|---|---|
| 🆕 SLAM 新手，想要一篇 primer | → `se3_so3_lie_groups_primer.md`（一切都堆在这上面） |
| 🤖 在读 ORB-SLAM3 / colmap 源码 | → `bundle_adjustment.md` + `pose_graph_optimization.md` |
| 🌬️ 在读 OpenVINS / VINS-Mono 源码 | → `bayesian_filtering_ekf_msckf.md` + `imu_preintegration_math.md` |
| 🎓 从 VGGT / feed-forward 3D 那边过来 | → 先看 `bundle_adjustment.md`，理解 VGGT 替换掉了什么 |
| 🛠️ 生产环境调 quaternion sign flip bug | → `quaternions_and_rotations.md` §Hamilton-vs-JPL |

---

## Boundary (与相邻区的边界)

这一区**只放数学 primer** —— 短篇、~5-7k chars、不做完整系统拆解。

| Topic | 住在哪 | 不要在这里写 |
|---|---|---|
| ORB-SLAM3 系统架构 | `foundations/classical-slam/orb_slam3_dissection.md` | 系统级线程 / Atlas / loop closer |
| OpenVINS / VINS-Mono 代码级 | `embodiments/aerial/vio/` | aerial 实时调参、prop-IMU 隔离 |
| VGGT / DUSt3R feed-forward | `foundations/feed-forward-3d/` | N-view 前向推理 |
| 跨 embodiment 迁移（VGGT vs VIO） | `crossing/slam-vio-migration/` | rate × latency × metric 矩阵 |
| 3DGS / radiance-field 数学 | `foundations/3dgs-family/` | 可微光栅化 |
| IMU 噪声物理 / Allan variance | `foundations/sensor-physics/` | 传感器信号源头 |
| Sim(3) 尺度漂移修正 | 这里 `pose_graph_optimization.md` 提及，完整版在 classical-slam | 完整 Sim(3) 闭环实现 |

**这一区只拥有**至少被 3 个下游子区引用的数学基元 —— SE(3)、quaternions、BA、PGO、EKF / MSCKF、IMU preintegration。某数学话题如果只被一个下游文档用到，那就 inline 写在那个文档里，不来这一区。

---

## Cross-references

- [`foundations/classical-slam/orb_slam3_dissection.md`](../classical-slam/orb_slam3_dissection.md) —— BA + PGO 的最大用户
- [`embodiments/aerial/vio/openvins_dissection.md`](../../embodiments/aerial/vio/openvins_dissection.md) —— MSCKF 的最大用户
- [`embodiments/aerial/vio/vins_mono_fusion_dissection.md`](../../embodiments/aerial/vio/vins_mono_fusion_dissection.md) —— IMU preintegration 的最大用户
- [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) —— 试图绕开这套数学的那一边
- [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) —— 为什么这套数学在 2026 仍然重要

---

[← Back to Foundations](../README.md)
