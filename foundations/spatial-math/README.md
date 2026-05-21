# 🧮 Spatial Math — Region Landing (空间数学工具箱)

> **Status:** v1 — new region, opinionated draft. English-first per AGENTS.md `foundations/` policy.
> **Depth tier:** 📖 foundations baseline (1× depth; cross-embodiment toolbox, not a maintainer anchor)
> **TL;DR:** Math toolbox — the seven primitives every SLAM / VIO / feed-forward 3D paper silently assumes you know. SE(3) / quaternions / BA / pose graph / EKF-MSCKF / IMU preintegration. The Spatial-side analogue of VLA-Handbook's `math_for_vla.md`.

---

## Why this region exists (为什么这一区独立存在)

Every other `foundations/` region assumes the reader already speaks Lie-algebra-of-SE(3) and Schur-complement bundle adjustment. ORB-SLAM3 throws `Sim(3)` at you on page 2; OpenVINS opens with MSCKF state propagation; VINS-Mono buries Forster-2017 IMU preintegration in the first equation block.

A reader new to the field hits these walls and bounces. This region is the **toolbox** — short, opinionated, math-first primers that let you re-enter any classical SLAM / VIO paper without translating notation in your head.

It is deliberately the **dual face** of `foundations/feed-forward-3d/`:

- Feed-forward 3D (VGGT-class, 2024+) tries to *make most of this math go away*.
- This region documents the math that *still runs every shipping aerial / ground / AR system in 2026*.

You need both. Knowing only feed-forward leaves you helpless when a real drone shakes; knowing only classical leaves you blind to where the field is moving.

> 这是 foundations 的**工具箱第一站**，对应 VLA-Handbook 那一侧 `math_for_vla.md` 的地位。先把这七篇通读，再去拆 ORB-SLAM3 / OpenVINS / VINS-Mono 的代码会平顺很多。

---

## Recommended entries (推荐入口)

读 SLAM / VIO 论文遇到不懂的数学时，按下面顺序回查：

| File | One-liner | Depends on |
|---|---|---|
| [`se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md) ★ | SO(3) / SE(3) / Lie algebra exp-log map — *the* prerequisite for everything else | none |
| [`quaternions_and_rotations.md`](./quaternions_and_rotations.md) | quaternions vs rotation matrix vs Euler — Hamilton vs JPL convention war | SO(3) primer |
| [`bundle_adjustment.md`](./bundle_adjustment.md) ★ | the math behind every SLAM — cost, Jacobian sparsity, Schur complement, LM | SO(3) + quaternions |
| [`pose_graph_optimization.md`](./pose_graph_optimization.md) | post-BA loop closure — g2o / GTSAM / Ceres ecosystem | BA + Lie groups |
| [`bayesian_filtering_ekf_msckf.md`](./bayesian_filtering_ekf_msckf.md) ★ | EKF / UKF / MSCKF — why OpenVINS keeps a sliding window of poses, not landmarks | linear algebra refresh |
| [`imu_preintegration_math.md`](./imu_preintegration_math.md) | Forster *T-RO 2017* — why VINS-Mono can drop IMU samples between camera frames | SO(3) + EKF |

★ = if you only read three, read these.

---

## Pick by role (角色定位)

| Role | Entry point |
|---|---|
| 🆕 New to SLAM, want one primer | → `se3_so3_lie_groups_primer.md` (everything stacks on this) |
| 🤖 Reading ORB-SLAM3 / colmap source | → `bundle_adjustment.md` + `pose_graph_optimization.md` |
| 🌬️ Reading OpenVINS / VINS-Mono source | → `bayesian_filtering_ekf_msckf.md` + `imu_preintegration_math.md` |
| 🎓 Came from VGGT / feed-forward 3D side | → start with `bundle_adjustment.md` to see what VGGT replaces |
| 🛠️ Debugging quaternion sign flips in production | → `quaternions_and_rotations.md` §Hamilton-vs-JPL |

---

## Boundary (与相邻区的边界)

This region is **math primers only** — short, ~5-7k chars, no full system dissection.

| Topic | Lives in | Don't write here |
|---|---|---|
| ORB-SLAM3 system architecture | `foundations/classical-slam/orb_slam3_dissection.md` | system-level threading / Atlas / loop closer |
| OpenVINS / VINS-Mono code-level | `embodiments/aerial/vio/` | aerial real-time tuning, prop-IMU isolation |
| VGGT / DUSt3R feed-forward | `foundations/feed-forward-3d/` | N-view forward inference |
| Cross-embodiment migration (VGGT vs VIO) | `crossing/slam-vio-migration/` | rate × latency × metric matrix |
| 3DGS / radiance-field math | `foundations/3dgs-family/` | differentiable rasterization |
| IMU noise physics / allan variance | `foundations/sensor-physics/` | sensor signal source |
| Sim(3) scale-drift correction | mentioned in `pose_graph_optimization.md`, full in classical-slam | full Sim(3) loop-closing implementation |

**This region only owns** the math primitives that ≥3 other regions cite — SE(3), quaternions, BA, PGO, EKF / MSCKF, IMU preintegration. If a math topic is used in only one downstream doc, it stays inline there.

---

## Cross-references

- [`foundations/classical-slam/orb_slam3_dissection.md`](../classical-slam/orb_slam3_dissection.md) — heaviest customer of BA + PGO
- [`embodiments/aerial/vio/openvins_dissection.md`](../../embodiments/aerial/vio/openvins_dissection.md) — heaviest customer of MSCKF
- [`embodiments/aerial/vio/vins_mono_fusion_dissection.md`](../../embodiments/aerial/vio/vins_mono_fusion_dissection.md) — heaviest customer of IMU preintegration
- [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) — what attempts to bypass this math
- [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) — why the math still matters in 2026

---

[← Back to Foundations](../README.md)
