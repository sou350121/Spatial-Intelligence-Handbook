# 🧭 Classical Visual SLAM — Region Landing (经典视觉 SLAM 导读)

> **Status:** v1 — new region, opinionated draft. `UNVERIFIED` numbers marked inline.
> **Depth tier:** 📖 foundations baseline (1× depth; not a maintainer anchor — aerial VIO already is)
> **TL;DR:** This region collects the **cross-embodiment classical visual SLAM canon** — ORB-SLAM3 (feature-based), DSO / LSD-SLAM (direct), and the tooling that keeps them honest (Kalibr / maplab / ROS). It is the *feed-forward 3D dual face* of the foundations stack: VGGT-class models are what the field is becoming, ORB-SLAM3 is what it actually runs on in 2026.

---

## 为什么这一区独立存在 (Why this region exists)

`foundations/` 一直缺一块：**feed-forward 3D（VGGT 系）**的对偶面 —— 跨 embodiment 通用、被工业界反复 fork 的**经典视觉 SLAM 框架**。

之前的分工是：

- `foundations/feed-forward-3d/` — VGGT / DUSt3R 这类**前向 3D foundation 模型**（2024+）
- `embodiments/aerial/vio/` — VINS / OpenVINS / DROID 这类**aerial real-time VIO**（rate × latency × IMU 严苛）
- `crossing/slam-vio-migration/` — 跨 embodiment 对比

但有一整批论文坐落在中间：**ORB-SLAM (1/2/3)** 是 manipulation / ground / AR / 室内 robotics 的事实默认；**DSO / LSD-SLAM** 是直接法的里程碑；**Kalibr / maplab** 是不论你跑哪个 stack 都得用的工具链。这些既不"feed-forward"也不"aerial-only"，应该住在 foundations 里，作为跨 embodiment 共享的**经典基线**。

简言之 —— 你跑 VGGT 之前得先理解 ORB-SLAM3 为什么 5 年没被取代，否则讨论 "范式转移" 都没有 baseline。

---

## 推荐入口 (Recommended entries)

| File | 一句话 |
|---|---|
| [`orb_slam3_dissection.md`](./orb_slam3_dissection.md) ★ | Campos et al. *T-RO 2021* — 三线程 + Atlas multi-map，**Why ORB-features still ship in 2026** |
| [`direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md) | Engel 2014 / 2017 — pixel intensity 直接法 vs feature matching 的根本分歧，何时赢何时输 |
| [`slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md) | Kalibr / maplab / ROS2 — 没人写论文但每个 deployment 都得用的工具链账本 |

---

## 角色定位 (Pick by role)

| 角色 | 起点 |
|---|---|
| 🤖 Manipulation / 室内 robotics 工程师 | → ORB-SLAM3 dissection（你 90% 的项目从这开始 fork） |
| 🎓 SLAM 研究者 / 想理解直接法 vs 特征法 | → Direct methods (DSO / LSD) |
| 🛠️ Robotics PoC 部署 / 标定工程师 | → Toolchain ecosystem（Kalibr / maplab / ROS2 实战） |
| 🛰️ 跨 embodiment 系统架构师 | → 先回 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`，再来这里看经典基线 |

---

## 与相邻区的边界 (Boundary)

这一区 **不重写** 已经在别处的内容：

| 主题 | 住在哪 | 不要在这一区写 |
|---|---|---|
| VINS-Fusion / OpenVINS / DROID-SLAM | `embodiments/aerial/vio/` | aerial 严格 200 Hz / sub-10 ms latency 的实战拆解 |
| VGGT / DUSt3R / MASt3R / π³ | `foundations/feed-forward-3d/` | feed-forward N-view 推理范式 |
| "VGGT 能否取代 VIO" 跨 embodiment 比较 | `crossing/slam-vio-migration/vggt_vs_drone_vio.md` | rate × latency × metric 的跨 embodiment 矩阵 |
| GS-SLAM (3DGS-based SLAM backend) | `foundations/3dgs-family/gs_slam_dissection.md` | radiance field 后端 |
| IMU 噪声物理 / rolling shutter | `foundations/sensor-physics/` | 传感器底层信号 |
| 时间同步 / 多机标定部署 | `deployment/` | 工程实战 |

**这一区只管**：**纯视觉关键帧 SLAM**（ORB 系）+ **直接法**（DSO / LSD）+ **跨 embodiment 通用工具链**（Kalibr / maplab / ROS）。换句话说：**Pre-foundation-model 时代的视觉 SLAM 共享底层**。

---

## Cross-references

- [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) — 这一区的"未来对偶面"
- [`embodiments/aerial/vio/README.md`](../../embodiments/aerial/vio/README.md) — aerial 严苛实时实战
- [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) — 跨 embodiment 跨范式旗舰
- [`foundations/sensor-physics/`](../sensor-physics/) — IMU / camera 信号源头

---

[← Back to Foundations](../README.md) · [→ Crossing](../../crossing/README.md)
