# Aerial VIO — Landing Page

**Status:** v1 — opinionated draft. Spec / latency claims marked `UNVERIFIED`.
**Depth tier:** 🌬️ maintainer anchor (written 1.5–2× deeper than other embodiment axes).
**TL;DR:** Aerial VIO is the strictest test of any state estimator — 200 Hz state rate, sub-10 ms end-to-end latency, metric scale with no GNSS fallback, and IMU robustness against propeller-induced aliasing. Three stacks have actually shipped against this bar: **VINS-Fusion** (HKUST), **OpenVINS** (UDel / Skydio-adjacent), and the learned outlier **DROID-SLAM** (Princeton). Everything else is benchmark theater.

---

## Why aerial is harsher than ground / manipulation

A tabletop SfM pipeline can take 100 ms and nobody dies. A drone at 15 m/s in a wind gust integrates 1.5 m of position error in that same 100 ms — past the recoverable envelope of a cascaded attitude controller. The non-negotiables:

| Requirement | Why | Typical bar |
|---|---|---|
| State rate ≥ 100 Hz | Cascaded attitude controller bandwidth | 200 Hz on tuned stacks `UNVERIFIED` |
| End-to-end latency ≤ 10 ms | Camera → estimate → controller → motor | 5–15 ms VINS-Fusion / OpenVINS `UNVERIFIED` |
| Metric scale, no fallback | Position controller integrates in meters; throttle compensates gravity in m/s² | <2% scale error post-init |
| IMU saturation / aliasing | Props excite IMU at 100–400 Hz | Mechanical isolators + 1 kHz IMU + bandpass |

This is why aerial state estimation gets its own folder rather than being absorbed into a generic SLAM section. The constraints that matter here — vibration, latency budget, controller coupling — never show up in a manipulation benchmark.

## The three production stacks

1. **VINS-Fusion** ([dissection](./vins_mono_fusion_dissection.md)) — Qin et al. *T-RO 2018*, the open-source baseline. Tightly coupled, optimization-based, sliding-window factor graph. The reference everyone forks.
2. **OpenVINS** ([dissection](./openvins_dissection.md)) — Geneva et al. *ICRA 2020*, MSCKF formulation. Lower CPU than VINS-Fusion at comparable accuracy. Lineage adjacent to Skydio-class commercial autonomy.
3. **DROID-SLAM** ([dissection](./droid_slam_dissection.md)) — Teed & Deng *NeurIPS 2021*, learned dense bundle adjustment. Best accuracy on hard scenes; loses on Jetson-class real-time. The bridge to the VGGT-vs-VIO question.

Each gets its own dissection because the failure modes are non-overlapping — pick by your CPU / GPU budget, your vibration profile, and how much loop-closure / relocalization tolerance you need.

## 教学基础 (Tutorial layer · 配合上述三栈使用)

- **[`ekf_from_scratch_dissection.md`](./ekf_from_scratch_dissection.md)** ⚡ NEW — 15-state EKF + 21-state augmented EKF 从零手写教程（取材 HKUST ELEC5660 L8-L9 + proj3, BSD 3-Clause）。**与上述三栈互补 — 它们是「拆库」，本文是「从零写自己的 estimator」**。读完你能：(a) 上 Jacobian / 协方差传播自己 onboard 的 sensor 组合；(b) 看懂 OpenVINS / VINS-Fusion 内部 trade-off 来自哪。

> **2026-05 默认推 OpenVINS**（VINS-Fusion [#3](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/3) global-optimization 自 2019 long-open、VINS-Mono 已 stale 无 ROS 2 port）。OpenVINS 是 aerial VIO 区**唯一仍正常维护的官方 repo**（2025-11 仍 push，issue 回复活跃）。详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。

## Cross-references

- Cross-embodiment angle: [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) — why VGGT does not replace VIO at aerial latency budgets.
- Sensor stack pairing: [`crossing/sensor-stack-matrix/`](../../../crossing/sensor-stack-matrix/) — IMU + camera + (optional) event-camera trade-offs.
- Feed-forward 3D context: [`foundations/feed-forward-3d/`](../../../foundations/feed-forward-3d/) — what VGGT-class models can and can't contribute.
- Event-camera complement: [`../event-camera/`](../event-camera/) — when classical VIO breaks (high speed, low light), event sensors are the hedge.

## Boundary

This folder dissects **per-paper / per-stack** mechanics for aerial VIO. Cross-embodiment comparisons (manipulation ↔ ground ↔ aerial ↔ marine) live in `crossing/slam-vio-migration/`. Sensor physics (IMU noise models, rolling-shutter geometry) lives in `foundations/sensor-physics/`. Deployment-side topics (calibration, time-sync, mechanical isolation) live in `deployment/`.
