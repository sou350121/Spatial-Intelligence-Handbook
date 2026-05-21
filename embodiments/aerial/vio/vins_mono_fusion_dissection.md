# VINS-Mono / VINS-Fusion Dissection

**Status:** v1 — opinionated draft. Latency / RMSE figures marked `UNVERIFIED` unless re-measured on the maintainer's rig.
**Paper:** Qin, Li, Shen — *VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator*, IEEE *T-RO* 2018. arXiv [1708.03852](https://arxiv.org/abs/1708.03852). HKUST Aerial Robotics Group.
**Code:** [HKUST-Aerial-Robotics/VINS-Mono](https://github.com/HKUST-Aerial-Robotics/VINS-Mono), [VINS-Fusion](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion) (mono + stereo + GPS variant).
**TL;DR:** VINS-Mono is the open-source aerial VIO baseline that other stacks are measured against. The three design choices that aged well: **(1)** sliding-window nonlinear optimization over a tightly-coupled factor graph, **(2)** IMU pre-integration as the bridge between visual rates and inertial rates, **(3)** Schur-complement marginalization to bound CPU. The choices that did not age: monocular initialization is fragile, the loop-closure module is an afterthought, and the original code is ROS1 / OpenCV3 vintage.

---

## 1 · Setup — what HKUST was solving

In 2017, the field had two camps. Filter-based VIO (MSCKF, ROVIO) was fast but suffered from linearization-point drift. Optimization-based VIO (OKVIS) was accurate but heavy. VINS-Mono picked the optimization camp and won the CPU-vs-accuracy argument by **bounding the optimization window aggressively** (10–11 keyframes typical) and **marginalizing the rest into a prior**. Combined with a monocular-only sensor stack — no stereo rig, no LiDAR — it became the cheapest credible aerial VIO open-sourced, and HKUST became the de facto lab.

## 2 · Architecture

```
  IMU (200 Hz) ─► pre-integration ─┐
                                   ▼
  Camera (30 Hz) ─► feature track ─► sliding-window nonlinear LS (Ceres)
                                   │
                                   ├─► IMU residual    (pre-integrated Δp, Δv, Δq)
                                   ├─► reprojection    (per-feature, inverse-depth param)
                                   └─► marginalization (Schur-complement prior)
                                   ▼
                          200 Hz state @ IMU prop, 30 Hz update @ optim
                                   │
                                   └─► (optional) loop-closure thread @ ~1 Hz
                                              (DBoW2 retrieval → 4-DoF pose graph)
```

| Component | What it does | Why HKUST chose it |
|---|---|---|
| KLT optical-flow tracker | Per-frame feature association | Avoids descriptor compute on CPU; OK for monocular short baselines |
| IMU pre-integration (Forster et al. style) | Collapses IMU samples between two keyframes into one residual | Decouples optimization rate (30 Hz) from IMU rate (200 Hz) |
| Sliding window (~10 keyframes) | Bounded optimization horizon | CPU stays flat; older info enters prior |
| Inverse-depth feature parameterization | One scalar per feature in window | Linearizes well for points far from camera |
| Schur-complement marginalization | Old keyframes → linear prior on remaining | Information-preserving; key trick for accuracy |
| Loop closure (DBoW2 + 4-DoF pose graph) | Drift correction over minutes | Bolted on; not the strength of the paper |

## 3 · Why these choices held up

- **Per-feature reprojection over photometric / direct methods.** Reprojection in pixels gives a clean noise model and survives exposure changes. Direct methods (DSO lineage) need photometric calibration that aerial rigs rarely have.
- **Pre-integration as the IMU bridge.** Lets the optimizer move keyframe poses without re-integrating raw IMU samples each iteration. This is the single biggest reason VINS-Mono stays real-time on CPU.
- **Marginalization rather than fixed-lag deletion.** Throwing away old keyframes destroys information; marginalizing them into a Gaussian prior preserves the cross-correlations that matter for scale observability.
- **Monocular-first, stereo-optional.** VINS-Fusion (2019 follow-up) generalizes the same backbone to stereo and stereo+GPS; the core didn't need rewriting.

## 4 · Where it breaks

| Failure mode | Why VINS-Mono breaks | Mitigation |
|---|---|---|
| Fast yaw rate (>200°/s) | KLT tracks fail across large rotations; pre-integration uncertainty grows | Higher-FOV lens, IMU-aided feature predict, or fall back to OpenVINS (better rotational handling) |
| Low-texture indoor (white walls) | Insufficient parallax → feature window degenerates | Add wide-baseline stereo (VINS-Fusion stereo mode) or event camera |
| Aggressive throttle / IMU saturation | Pre-integration assumes accel within ±16 g; racing drones clip | Higher-range IMU (ICM-42605 / ADIS16500-class) `UNVERIFIED` |
| Long traversal without loop closure | Yaw + position drift accumulate (scale-free direction) | Pose-graph back-end (VINS-Fusion's loop-closure module, or external) |
| Init under motion at start | Monocular init needs ~1 s of acceleration variance to recover scale | Stereo init (VINS-Fusion) or warm-start from prior |

EuRoC MAV dataset numbers `UNVERIFIED` from secondary sources: VINS-Mono lands ~0.15 m RMSE on MH01–MH05 indoor trajectories. **Real outdoor / aerial racing numbers are not in the paper** — and that gap is the recurring story in aerial VIO benchmarks.

## 5 · Init from IMU pre-integration — the part most readers skim

The monocular init is the hardest part of the paper to internalize. Pure visual SfM gives a structure up to unknown scale. The IMU's gravity-aligned accelerometer gives metric magnitude, but only if you can solve for accelerometer bias, gyro bias, and the gravity direction simultaneously. VINS-Mono's init does this in three steps: **(1)** monocular SfM over the first window without IMU, **(2)** linear alignment of visual motion to IMU pre-integration to recover scale + gravity, **(3)** nonlinear refinement folding biases in. The init fails when accel variance is too low (drone sitting still) — which is why VINS-Mono needs a "wave the drone around" pre-flight ritual that bigger commercial stacks avoid via stereo or wheel odometry priors.

## 6 · When to pick VINS-Fusion vs alternatives

- Pick **VINS-Fusion** when: you want a battle-tested open-source baseline, you can afford a 2+ core CPU budget, you have a stereo rig available, and you want GPS fusion as an option.
- Pick **OpenVINS** when: your CPU budget is one core (1.5 GHz Cortex-A or Jetson Nano), or you need multi-camera with cleaner code architecture. See [openvins_dissection.md](./openvins_dissection.md).
- Pick **DROID-SLAM** when: you have a GPU, your trajectory is hard (textureless / low-light), and you can tolerate 5 Hz state. See [droid_slam_dissection.md](./droid_slam_dissection.md).

## References

- VINS-Mono — Qin, Li, Shen. *IEEE T-RO* 2018. [arXiv 1708.03852](https://arxiv.org/abs/1708.03852)
- VINS-Fusion stereo + GPS — Qin et al. *arXiv* 2019. [arXiv 1901.03642](https://arxiv.org/abs/1901.03642)
- IMU pre-integration — Forster et al. *T-RO* 2017. [arXiv 1512.02363](https://arxiv.org/abs/1512.02363)
- EuRoC MAV dataset — Burri et al. *IJRR* 2016. (DOI 10.1177/0278364915620033)

## Boundary

This file dissects VINS-Mono / VINS-Fusion mechanics. Comparative trade-offs against MSCKF and learned VIO live in [`crossing/slam-vio-migration/`](../../../crossing/slam-vio-migration/). IMU noise modeling and pre-integration math live in [`foundations/sensor-physics/`](../../../foundations/sensor-physics/) (when written). Real-rig calibration and time-sync procedures live in `deployment/`.
