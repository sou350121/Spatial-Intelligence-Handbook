# OpenVINS Dissection

**Status:** v1 — opinionated draft. CPU / RMSE figures marked `UNVERIFIED` unless re-measured.
**Paper:** Geneva, Eckenhoff, Lee, Yang, Huang — *OpenVINS: A Research Platform for Visual-Inertial Estimation*, IEEE ICRA 2020. arXiv [1910.00298](https://arxiv.org/abs/1910.00298). University of Delaware (RPNG lab).
**Code:** [rpng/open_vins](https://github.com/rpng/open_vins). BSD-3.
**TL;DR:** OpenVINS is the modern open-source MSCKF — a filter-based VIO that beats sliding-window optimization (VINS-Fusion) on CPU budget at comparable accuracy. The two design choices that matter: **(1)** MSCKF marginalizes features out of the state (no per-feature state bloat), **(2)** First-Estimates Jacobian (FEJ) freezes linearization points to recover the observability properties a naive EKF destroys. Skydio-adjacent lineage — RPNG alumni populate Skydio's autonomy team, and the design biases (single-core viable, multi-camera clean) match what shipped commercially.

---

## 1 · Setup — why MSCKF matters in 2026

By 2020 the field had split. The academic mainstream (VINS-Mono, OKVIS, ORB-SLAM3) had gone optimization. The commercial mainstream (Google ARCore, Apple ARKit, Skydio, much of DJI's flight stack `UNVERIFIED`) had stayed filter-based. The reason is unglamorous: **a tuned MSCKF runs on a single 1.5 GHz CPU core and stays under 5 ms per frame** `UNVERIFIED`, while VINS-Fusion needs 2+ cores at the same accuracy. On a drone where the same SoC is also running attitude control, ESC telemetry, video encoding, and a radio stack, that delta is the difference between "ships" and "doesn't."

OpenVINS open-sourced the MSCKF design that had been folklore in the commercial space since Mourikis & Roumeliotis 2007. It is the cleanest reference implementation of a filter-based VIO that the academic community has produced.

## 2 · Architecture

```
  IMU (200 Hz) ─► state propagation (EKF predict step)
                       │
                       ▼
   ┌────────────────────────────────────────┐
   │  Filter state = [IMU state | clone window of past poses]│
   │  Features are NOT in the state         │
   └────────────────────────────────────────┘
                       │
  Camera (30 Hz) ─► track features, accumulate observations
                       │
                       ▼
  When a feature is "ready" (lost / window full):
     1. Triangulate feature from the clone window observations
     2. Null-space project observations to eliminate feature
     3. EKF update with the null-space residual
     4. (Optional) marginalize oldest clone, slide window forward
                       │
                       ▼
              200 Hz state @ IMU propagation
```

| Component | What it does | Why MSCKF wins |
|---|---|---|
| Stochastic clone window | Past N camera poses live in state | Enables triangulation without persistent feature states |
| Null-space projection | Project feature observations to space orthogonal to feature position | Eliminates feature state algebraically; preserves info |
| EKF update (not full BA) | Single linearization point per step | O(state³) but state stays small (~20 clones × 6 DoF) |
| First-Estimates Jacobian (FEJ) | Linearize about first-time estimate, not current | Recovers the 4 unobservable directions (global yaw + 3D position) |
| Multi-camera + IMU bay | Per-camera intrinsics / extrinsics in state | Online calibration; matches multi-cam aerial rigs |

## 3 · MSCKF vs sliding-window optimization

|  | MSCKF (OpenVINS) | Sliding-window opt (VINS-Fusion) |
|---|---|---|
| CPU budget | 1 core @ 1.5 GHz viable `UNVERIFIED` | 2+ cores `UNVERIFIED` |
| Memory | ~MB-scale state vector | ~MB Ceres problem + Hessian |
| Accuracy on EuRoC | within 10–20% of VINS-Fusion `UNVERIFIED` | reference |
| Latency per frame | 2–5 ms `UNVERIFIED` | 8–15 ms `UNVERIFIED` |
| Re-linearization | Once per measurement (FEJ frozen) | Many iterations per window |
| Loop closure | external (pose graph thread) | built-in (DBoW2) |
| Multi-camera | first-class | bolted on |
| Code complexity | high (filter algebra) | moderate (Ceres handles it) |

The honest read: MSCKF wins when CPU is the constraint, optimization wins when accuracy on hard trajectories is the constraint. **For aerial production, CPU is almost always the constraint** — which is why the commercial stacks went filter.

## 4 · The FEJ trick — why naive EKF VIO does not work

Standard EKF VIO has a known bug: the linearization point of the state estimate changes every step, which couples observability with estimator-state-history. In practice the filter develops a phantom observability of global yaw and global 3D position — directions that are physically unobservable from camera + IMU alone. This causes optimistic covariance, inconsistent uncertainty estimates, and eventual divergence on long trajectories.

**FEJ (First-Estimates Jacobian)** fixes this by freezing the linearization point of each state variable to its first-ever estimate. Jacobians get computed at frozen points; mean updates still use the current estimate. The math is unglamorous (Huang, Mourikis, Roumeliotis 2008) but the result is the difference between "ships" and "drifts in 30 seconds." OpenVINS implements FEJ cleanly enough that it became the reference for how to do it.

## 5 · When to pick OpenVINS vs VINS-Fusion

| Pick **OpenVINS** when | Pick **VINS-Fusion** when |
|---|---|
| Single-core CPU budget (BeagleBone, Raspberry Pi, Jetson Nano shared with other workloads) | 2+ cores available |
| Multi-camera rig (front + down + side) | Single camera or stereo |
| You need online intrinsic / extrinsic calibration | You can offline-calibrate |
| Long-horizon consistency matters more than peak accuracy | Peak accuracy on EuRoC-style trajectories matters more |
| You want clean code structure for research extension | You want the most-forked baseline |

The Skydio-adjacent comment is not idle — multiple RPNG alumni (Geneva, Eckenhoff, others) ended up at Skydio or comparable autonomy outfits, and the design biases visible in OpenVINS (clean multi-camera support, online calibration, single-core target) are the design biases a commercial drone autonomy stack would actually want. The paper reads like a sanitized academic version of what shipped in 2017–2019 era commercial drones.

## 6 · Failure modes specific to MSCKF

- **Outlier features are catastrophic** — without an optimization loop to re-linearize, one bad triangulation pollutes the update. OpenVINS leans hard on chi-squared gating; tune carefully.
- **Init still hard** — MSCKF init has the same monocular-scale problem as VINS-Mono. The fix is identical (motion variance + linear alignment).
- **Loop closure has to be external** — the filter has no native loop-closure concept. You bolt on a pose-graph back-end (often borrowed from VINS-Fusion or ORB-SLAM3).
- **Filter divergence under fast yaw** — same KLT track failure as VINS-Mono, but the filter has less recovery margin than an optimizer with multiple Gauss-Newton iterations.

## References

- OpenVINS — Geneva et al. *ICRA 2020*. [arXiv 1910.00298](https://arxiv.org/abs/1910.00298)
- Original MSCKF — Mourikis & Roumeliotis. *ICRA 2007*. (DOI 10.1109/ROBOT.2007.364024)
- FEJ EKF consistency — Huang, Mourikis, Roumeliotis. *IJRR* 2008.

## Boundary

This file dissects OpenVINS / MSCKF mechanics. Cross-stack comparison (filter vs optimization) at the cross-embodiment level lives in [`crossing/slam-vio-migration/`](../../../crossing/slam-vio-migration/). VINS-Fusion specifics live in [`vins_mono_fusion_dissection.md`](./vins_mono_fusion_dissection.md). Commercial-stack engineering ([`companies/skydio.md`](../../../companies/) when written) lives elsewhere.
