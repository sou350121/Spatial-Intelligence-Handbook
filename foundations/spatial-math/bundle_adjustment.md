# Bundle Adjustment (BA, 光束法平差)

> **发布时间**: 2026-05-21
> **核心定位**: The non-linear least-squares optimization at the heart of every SfM / SLAM system since the 1950s — and the Schur-complement trick that makes it tractable.

**Status:** v1 — primer. Sparsity-pattern claims sourced to Triggs et al. 2000 and Ceres docs.
**TL;DR:** BA jointly refines camera poses and 3D points by minimising reprojection error. Jacobian is huge but block-sparse; Schur marginalises points, leaving a much smaller pose-only system. **No SfM / SLAM ships without BA, including VGGT's distillation pipeline `UNVERIFIED`.**

**X-Ray.** A SLAM session collects thousands of feature observations across hundreds of frames. Each observation is a noisy pixel matching a 3D point projected through a noisy pose. BA writes one residual per observation, stacks into a giant non-linear LSQ, solves with LM. The naïve normal equation has `(6N+3M)²` entries — billions — but its structure is two diagonal blocks linked by a sparse bridge, which Schur exploits. BA is one of the few classical algorithms where understanding the sparsity matters more than the math itself. (中文直觉：同时调相机和点 — Jacobian 两块对角加一条细桥，Schur 利用这形状。)

## 📍 研究全景时间线

```
1957       2000              2011        2014    2021         2025         2026
Brown SBA► Triggs survey ► g2o      ► Ceres ► ORB-SLAM3 ► DROID-SLAM ► VGGT skips
           "BA-Modern Synthesis"     Google  Atlas BA      learned BA    BA forward
           (the bible)                                                    YOU ARE HERE
```

Triggs 2000 is the canonical reference; Ceres (2014) made BA accessible. VGGT (2025) skips BA in the forward pass — but **distillation** still uses classical BA on supervision side.

---

## 1 · Architecture: what BA optimizes

### 1.1 The problem

Given N poses `{T_i ∈ SE(3)}`, M points `{X_j ∈ R³}`, observations `{u_ij ∈ R²}`:

```
min   Σ_(i,j) || u_ij - π(T_i, X_j, K) ||²_Σ
T,X
```

`π` = projection (intrinsics `K` fixed); `Σ` = obs covariance.

### 1.2 ⚡ Eureka Moment

> **BA's Jacobian has a "two-block + thin bridge" sparsity — Schur reduces the solve from `O((6N+3M)³)` to `O(N³ + N²M)`, dominated by `N²M` when M » N.**

This trick makes BA feasible at hundreds of cams and millions of points. Every SLAM optimizer (g2o, Ceres, GTSAM) implements it.

### 1.3 Sparsity diagram

```
JᵀJ pattern:
         [ U  |  W  ]    U: 6N×6N camera block (sparse)
   H  =  [----+-----]    W: 6N×3M bridge
         [ Wᵀ |  V  ]    V: 3M×3M strictly block-diagonal (3×3 per point)
```

`V` is strictly block-diagonal — each point's Hessian sub-block independent. This is what Schur exploits.

---

## 2 · Math core: Schur complement and LM

### 📌 Napkin Formula

```
[ U   W ] [Δc]    [g_c]                  H = JᵀJ + λI
[ Wᵀ  V ] [Δp] = -[g_p]

Schur:  (U - W V⁻¹ Wᵀ) Δc = -g_c + W V⁻¹ g_p     ← poses only
then:   Δp = V⁻¹ (-g_p - Wᵀ Δc)                  ← back-sub points
```

`V` block-diagonal, so `V⁻¹` = M independent 3×3 inversions. Reduced cam system is `6N × 6N` — for N=100 that is 600×600, trivial CPU.

### Variables (Sola / Triggs convention)

| Symbol | Meaning |
|---|---|
| `T_i ∈ SE(3)` | camera i pose, right-perturbed |
| `X_j ∈ R³` | 3D landmark |
| `u_ij ∈ R²` | observed pixel |
| `r_ij = u_ij - π(...)` | reprojection residual (px) |
| `H = JᵀJ` | GN Hessian approx |
| `λ` | LM damping |

LM step: compute (r, J), form `H = JᵀJ + λI`, Schur-solve Δc, back-sub Δp, trial, accept / shrink λ or reject / grow λ. `λ→0` GN; `λ→∞` gradient descent. Auto-tuning makes LM robust where GN diverges.

---

## 3 · Worked example: 3 poses, 5 points

Three cameras, five points, all see all (15 obs).

- State: `6·3 + 3·5 = 33`
- Residuals: `2·15 = 30`
- `J` is `30×33`; `H` is `33×33`.

```
H = [ U (18×18 cam block) | W (18×15 bridge) ]
    [ Wᵀ                  | V (15×15 strictly block-diag, 3×3 per pt) ]
```

Schur reduces to `18×18` cam-only plus 5 indep `3×3` back-subs. Speedup irrelevant here; at 1000 cams / 100k pts it is "won't fit in RAM" → "seconds". Ceres `bundle_adjustment.cc` converges 3-pose-5-point in 4–6 LM iters from 5% random init `UNVERIFIED`.

---

## 4 · Engineering view

| Knob | Range | Effect |
|---|---|---|
| N poses | 10–1000 | dominates U block |
| M points | 1k–500k | back-sub cheap (block-diag V) |
| Iters | 5–20 | one Schur solve each |
| Robust loss | Huber / Cauchy | downweights leaked outliers |
| Fix gauge | first pose | else 7-DoF freedom → H singular |

**Real-time SLAM uses local BA.** Global over 10k poses takes seconds; ORB-SLAM3 local BA = sliding window of ~20 covisible keyframes, ~30 ms CPU. VINS-Mono = local BA + IMU residuals.

**Killers:** (1) outliers — RANSAC + robust loss; (2) bad init — triangulation + PnP, not random; (3) gauge freedom — fix first pose, monocular +1 scale; (4) degenerate motion — pure rotation makes points unobservable.

---

## 5 · Where BA shows up

| System | BA? | Where |
|---|---|---|
| ORB-SLAM3 | yes | tracking (motion-only), local mapping (window), loop closure (full + PGO) |
| VINS-Mono / Fusion | yes | sliding window + IMU residuals (Ceres) |
| OpenVINS | **no** (filter) | EKF instead — see `./bayesian_filtering_ekf_msckf.md` |
| COLMAP / SfM | yes | offline global refinement |
| DROID-SLAM | learned BA | differentiable GN inside the network |
| VGGT forward | **no** | distillation uses BA on supervision `UNVERIFIED` |

---

## 6 · Failure modes & Hidden Assumptions

### 6.1 Hidden Assumptions

- **Outliers RANSAC-filtered** — one bad corr corrupts hundreds of poses.
- **Noise ≈ Gaussian** — Huber covers light tails; heavy tails need pre-filter.
- **Gauge fixed** — first pose + (mono) one baseline; else H singular.
- **Linearisation local** — init within ~30% of truth.
- **Calibration accurate** — `K` errors → multiplicative pose error.
- **Static scene** — mask dynamics.

### Failure signatures

| Symptom | Cause |
|---|---|
| Cost decreases then explodes | LM damping aggressive; outliers leaked |
| Solver returns immediately | At local min; gauge unfixed |
| Trajectory "scrunches" | Monocular scale drift; need Sim(3) / stereo / IMU |
| OOM at 500+ keyframes | Missing Schur; global where local meant |

---

## 7 · Comparison & Interview Tip

| Approach | Pros | Cons | Used by |
|---|---|---|---|
| Filter (EKF / MSCKF) | const memory, fast | linearisation error builds | OpenVINS |
| Optimization (BA) | re-lin every iter | growing problem | ORB-SLAM3, COLMAP |
| Learned BA | differentiable | needs training | DROID-SLAM |
| Feed-forward | one-shot, no opt loop | un-metric | VGGT, DUSt3R |

> **🎤 Interview Tip.** "Why is BA tractable at 1000 cameras × 100k points?" — strong answer: "The Hessian has two-block sparsity — sparse camera block, strictly block-diagonal point block, thin bridge. Schur marginalises points cheaply because each 3×3 sub-block inverts independently, leaving only the camera system. Without Schur, production-scale BA is impossible." Bonus: name gauge freedom as the reason H is singular without anchoring a pose.

---

## Boundary

This primer covers the BA algorithm. For:

- **Post-BA loop closure** → `./pose_graph_optimization.md`
- **BA replaced by EKF (MSCKF)** → `./bayesian_filtering_ekf_msckf.md`
- **ORB-SLAM3 local + global BA threading** → `foundations/classical-slam/orb_slam3_dissection.md`
- **VINS-Mono sliding-window BA + IMU** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`
- **VGGT bypass of BA** → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

## References

- Triggs et al. *Bundle Adjustment — A Modern Synthesis*, LNCS 1883, 2000. The bible.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003. Ch. 18–19.
- Agarwal et al. *Bundle Adjustment in the Large*, ECCV 2010.
- Ceres: http://ceres-solver.org/ · g2o: Kümmerle et al., ICRA 2011.
- ORB-SLAM3: https://github.com/UZ-SLAMLab/ORB_SLAM3
- DROID-SLAM: Teed & Deng, NeurIPS 2021. https://arxiv.org/abs/2108.10869

[← Back to Spatial Math](./README.md)
