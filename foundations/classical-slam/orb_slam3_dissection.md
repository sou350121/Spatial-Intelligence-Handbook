# ORB-SLAM3 Dissection (ORB-SLAM3 解构)

> **Published:** arXiv 2020, *IEEE T-RO* 2021 · Campos, Elvira, Gómez Rodríguez, Montiel, Tardós (Univ. of Zaragoza)
> **arXiv:** https://arxiv.org/abs/2007.11898 · **Code:** https://github.com/UZ-SLAMLab/ORB_SLAM3
> **Core positioning:** The "one-stack-fits-all" feature-based visual / visual-inertial SLAM still the default fork for indoor / manipulation / AR robotics — nothing else does mono + stereo + RGB-D + IMU + multi-map atlas in one engineered codebase.

**Status:** v1. Latency / memory `UNVERIFIED`.
**TL;DR:** ORB-SLAM3 wins not on accuracy but on running on a Jetson Nano, phone, or RGB-D arm cell with the same three-thread architecture, recovering from kidnap via Atlas multi-map. Swap to a feed-forward 3D model and you lose IMU coupling, loop closure, and long-term mapping at once.

**X-Ray.** Visual SLAM has three jobs at three time scales: track every frame, build a local map, detect loops. ORB-SLAM (2015) was first to do all three in separate threads. ORB-SLAM3 (2021) accepts mono / stereo / RGB-D + IMU interchangeably and — the one big new idea — keeps **multiple disconnected maps in an Atlas**, so losing tracking doesn't kill the session. Think "Linux of visual SLAM": not fastest, but the one tooling assumes.

## 📍 Research timeline

```
2007    2011    2014     2015         2017            2021            2024+
PTAM ─► DTAM ─► SVO ───► ORB-SLAM ──► ORB-SLAM2 ────► ORB-SLAM3 ────► VGGT / DUSt3R
                          (mono)      (+stereo/RGBD)  YOU ARE HERE    (feed-forward)
└─ keyframe + features ────────────────────────────┘  └─ learned ─┘
```

Apex of the keyframe-and-features lineage. *Why has nothing displaced it for indoor RGB-D / manipulation in 5 years?*

---

## 1 · Architecture

### 1.1 Three-thread skeleton + Atlas

| Thread | Job |
|---|---|
| **Tracking** (cam rate) | ORB extract, match local map, motion-only BA, KF decision |
| **Local mapping** (~5–10 Hz) | Insert KFs, triangulate, local BA, cull |
| **Loop & merging** (on loop) | DBoW2, essential graph, full BA, Atlas merge |
| **Atlas** (data) | Active + non-active maps; spawns new map on tracking loss |

### 1.2 ⚡ Eureka Moment

> **Tracking loss is not a failure to be avoided — it is a normal event to plan for. Spawn a fresh map, keep running, merge back when place recognition finds an overlap.**

Pre-ORB-SLAM3 systems treated tracking loss as session-ending. Atlas reframes it: *N* disconnected maps coexist; loop closure becomes a *map-merge*. This makes ORB-SLAM3 deployable for warehouse rounds / multi-room AR.

### 1.3 Data flow

```
   Cam + IMU → Tracking →(KFs)→ Local mapping →(KFs+DBoW2)→ Loop & merging → Atlas
```

ORB descriptors cross all three threads — tracking matches, map-point representation, DBoW2 vectors. That's why "swap ORB for SuperPoint" is hard: one primitive, three independent uses.

---

## 2 · Math core

### 📌 Napkin Formula

```
T*  =  argmin_T   Σᵢ  ρ( ‖ π(T · Xᵢ) − uᵢ ‖_Σ )
```

`T ∈ SE(3)` pose; `Xᵢ` 3D point; `uᵢ` 2D observation; `π` projection; `Σ` covariance; `ρ` Huber. **Visual SLAM is this reprojection-error minimization repeated at three scales** — motion-only BA (per frame), local BA (sliding window), full BA (loop).

With IMU: `J = J_visual + J_imu_preintegration + J_bias_walk`. IMU pre-integration on the manifold (Forster 2015) treats IMU as a "delta-pose factor" — why VINS / OpenVINS / ORB-SLAM3 share the same factor-graph backend.

**Intuition:** mono is scale-ambiguous → need stereo / RGB-D / IMU for meters. IMU gives short-term metric + roll/pitch; camera corrects drift; only loop closure fixes long-term yaw / position.

---

## 3 · Worked example: tracking a single frame

Mono 30 Hz, indoor, ~100 ORB features matched. Jetson Orin times `UNVERIFIED`:

| Step | Time |
|---|---|
| ORB extract (8 pyramids, 1000 target) | ~8 ms |
| Constant-velocity predict + radius match | ~3 ms |
| Motion-only BA (LM, 4 iters) | ~5 ms |
| KF decision | <1 ms |
| **Total tracking** | **~17 ms** |

In parallel: local mapping ~100 ms/KF; DBoW2 ~20 ms/KF; full BA only on loop. This budget is why ORB-SLAM3 is 30 Hz indoor, not 200 Hz aerial.

---

## 4 · Engineering: why ORB still ships

ORB (Rublee 2011): FAST + steered BRIEF, 256-bit binary, rotation-invariant, <1 ms/frame. **Hamming distance on packed bits fits in L1 cache; no GPU needed.** ORB ~1 µs/keypoint vs SIFT ~50 µs (L2 float) vs SuperPoint ~10 µs (needs GPU).

Why hasn't ORB been replaced inside ORB-SLAM3? Not accuracy — **DBoW2 loop closure is built on ORB**, and DBoW2 retraining + integration is months of work. SuperSLAM forks exist; none has displaced the canonical fork.

---

## 5 · Data & evaluation

Reported on EuRoC MAV (stereo+IMU, ATE 2–10 cm `UNVERIFIED`), TUM-VI (handheld long indoor/outdoor for Atlas), TUM-RGBD. ⚠️ Per `AGENTS.md` 仿真饱和: EuRoC numbers do **not** transfer to outdoor / fast-flight / vibration.

---

## 6 · Capabilities & failure modes

**Ships for:** indoor manipulation (RGB-D + IMU); AR/VR (stereo + IMU + Atlas multi-session); indoor AGV with warehouse loops.

**Fails on:** textureless scenes (white walls → tracking lost); fast motion / motion blur (>2 rad/s starves FAST); dynamic scenes (silent map corruption; DynaSLAM forks address); aerial 200 Hz / sub-10 ms loops (see `crossing/slam-vio-migration/`); outdoor GNSS-aware AD.

### 6.1 Hidden Assumptions

- **Static rigid world** — every map point assumed non-moving. People, doors, vehicles → silent map corruption, no crash.
- **Consistent illumination** — BRIEF compares pixel-pair intensities; HDR transitions flip descriptor bits.
- **Stable intrinsics** — temperature-induced focal-length drift on plastic-mount RealSense is invisible.
- **Slowly varying IMU bias** — prop vibration breaks the random-walk model; #1 reason aerial users pick VINS / OpenVINS.
- **At least one loop per session** — without a loop, drift accumulates and Atlas can't merge.

---

## 7 · Comparison & Interview Tip

| Stack | Modes | Front-end | IMU | Loop | Aerial? |
|---|---|---|---|---|---|
| **ORB-SLAM3** | mono/stereo/RGBD/+IMU | ORB | tight (preint) | DBoW2+Atlas | ❌ indoor |
| VINS-Fusion | mono/stereo+IMU | KLT | tight | DBoW2 | ✅ |
| OpenVINS | mono/stereo+IMU | KLT | tight (MSCKF) | weaker | ✅ |
| DSO ([dissection](./direct_methods_dso_lsd.md)) | mono | direct | weak | weak | ❌ |
| DROID-SLAM | mono/stereo/RGBD | learned | weak | learned | ❌ |
| VGGT | N-view RGB | feed-forward | — | n/a | ❌ wrong rate |

> **🎤 Interview Tip.** "ORB-SLAM3 or VINS-Fusion for our robot?" — right answer: *"Depends on embodiment and control rate. ORB-SLAM3 for indoor RGB-D / manipulation / AR where multi-session matters; VINS-Fusion for aerial / fast motion where tracking latency tilts that way."* Wrong: "ORB-SLAM3 is more general so use it" — generality is a *codebase* feature, not an *envelope* feature.

---

## Boundary

- Aerial real-time VIO (VINS / OpenVINS / DROID at 200 Hz) → [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/README.md). Not re-written here.
- "VGGT vs VIO" cross-embodiment → [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md).
- Direct methods (DSO / LSD) → [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md).
- Kalibr / calibration → [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md).
- 3DGS SLAM backends → [`foundations/3dgs-family/gs_slam_dissection.md`](../3dgs-family/gs_slam_dissection.md).

---

## References

- ORB-SLAM3 — Campos et al. *T-RO 2021* · https://arxiv.org/abs/2007.11898
- ORB-SLAM — Mur-Artal et al. *T-RO 2015* · https://arxiv.org/abs/1502.00956
- ORB-SLAM2 — Mur-Artal, Tardós *T-RO 2017* · https://arxiv.org/abs/1610.06475
- ORB — Rublee et al. *ICCV 2011*; DBoW2 — Gálvez-López, Tardós *T-RO 2012*
- IMU pre-integration — Forster et al. *RSS 2015* · https://arxiv.org/abs/1512.02363
- Code — https://github.com/UZ-SLAMLab/ORB_SLAM3

---

[← Back to Classical SLAM](./README.md)
