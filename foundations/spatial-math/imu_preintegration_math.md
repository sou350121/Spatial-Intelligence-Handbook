# IMU Preintegration (IMU 预积分)

> **发布时间**: 2026-05-21
> **核心定位**: The Forster *T-RO 2017* trick that lets VINS-Mono and OpenVINS use 1000 Hz IMU measurements inside a 30 Hz optimization loop *without* re-integrating every sample on every linearisation step.

**Status:** v1 — primer.
**TL;DR:** Naïve IMU integration must be re-run from scratch on every pose perturbation — `O(K)` per linearisation, prohibitive. Preintegration computes a pose-independent summary in the previous body frame; re-linearisation = closed-form bias correction. Math behind every tightly-coupled VIO with ≥200 Hz IMU.

**X-Ray.** Drone IMU runs ~1000 Hz, camera ~30 Hz — ~33 samples between frames. Optimizer treats frames as state, IMU as constraint between them. Naïvely: every perturbation re-integrates 33 samples. Forster factored integration into `(ΔR, Δv, Δp)` depending only on readings + biases, not initial pose — pose composes at the end. Algebraic trick that makes VINS-Mono / OpenVINS feasible. (中文：IMU 段=相机帧间位姿增量，只依赖测量与偏置。)

## 📍 研究全景时间线

```
2011     2015            2017            2018-2020          2026
Lupton ► Forster RSS  ► Forster T-RO  ► VINS-Mono+OpenVINS ► YOU ARE HERE
preint   on-manifold    "the IMU paper" ship it             preint default
SLAM                                                         tightly-coupled VIO
```

Forster 2017 is the citation. Engineering payoff: "VIO runs at all".

---

## 1 · Architecture: why naïve integration is too slow

### 1.1 The problem

Between frames `k-1` and `k`, IMU gives `{a_i, ω_i}_{i=0}^{K-1}`. Naïve:

```
R_k = R_{k-1} · Π_i exp((ω_i - b_g) Δt)
v_k = v_{k-1} + g KΔt + R_{k-1} · Σ_i [...]
p_k = p_{k-1} + v_{k-1} KΔt + ...
```

`R_{k-1}, v_{k-1}` appear in every line. Every perturbation re-integrates K samples. 10 kf × 30 samples × 10 LM × 30 Hz → ~100k IMU integrations/sec — painful.

### 1.2 ⚡ Eureka Moment

> **Factor the IMU sequence into a pose-independent delta `(ΔR, Δv, Δp)` in the previous body frame — pose composes at end. Re-linearisation = first-order bias correction, no re-integration.**

Trick: integrate in *previous body frame* (no absolute-pose dependence). Bias → first-order Taylor.

### 1.3 Data flow

```
IMU 1 kHz ─► preintegration accumulator (incremental)
                 ▼
             (ΔR̃, Δṽ, Δp̃, J_bias, Σ) — pose-independent, bias-linearised
                 ▼
cam 30 Hz ─► optimizer consumes as one relative-pose factor between i and j
             re-linearisation = closed-form bias correction (no re-int)
```

---

## 2 · Math core: the three preintegrated deltas

### 📌 Napkin Formula

```
ΔR̃_ij = Π_{k} exp((ω_k - b̄_g) Δt)                       ← rotation
Δṽ_ij = Σ_{k} ΔR̃_ik · (a_k - b̄_a) · Δt                  ← velocity
Δp̃_ij = Σ_{k} [Δṽ_ik Δt + ½ ΔR̃_ik (a_k - b̄_a) Δt²]      ← position
```

All three are in the body frame at time `i` — no dependence on absolute pose at i. Bias `b̄` fixed at linearisation point.

### Composition (residuals)

```
e_R = log(ΔR̃_ij⁻¹ R_iᵀ R_j)
e_v = R_iᵀ(v_j - v_i - g Δt_ij) - Δṽ_ij
e_p = R_iᵀ(p_j - p_i - v_i Δt_ij - ½g Δt_ij²) - Δp̃_ij
```

Deltas are constants the optimizer compares against current pose / velocity. No re-integration.

### Bias update correction

`b̄ → b̄ + δb` shifts deltas first-order:

```
ΔR̃(b̄ + δb_g) ≈ ΔR̃(b̄) · exp(J_{ΔR,b_g} δb_g)
Δṽ(b̄ + δb)   ≈ Δṽ(b̄) + J_{Δv,·} δb
Δp̃(b̄ + δb)   ≈ Δp̃(b̄) + J_{Δp,·} δb
```

Jacobians stored once. Bias update = mat-vec multiply. **Headline of Forster 2017.**

Vars: `ω_k, a_k` (readings); `b̄_g, b̄_a` (biases); `ΔR̃, Δṽ, Δp̃` (deltas); `Σ_ij` (factor info); `g` (gravity); `Δt` (IMU period).

---

## 3 · Worked example: 3 IMU samples between two camera frames

Drone hovering, 3 ms gap, 3 samples @ 1 kHz. Biases `b̄_g = (0.001, 0, 0)`, `b̄_a = (0, 0, 0.05)`.

Bias-subtracted each step: `ω - b̄_g = (0.01, 0, 0)`, `a - b̄_a = (0, 0, 9.81)`.

- **Rotation:** `δR_k = exp((1e-5, 0, 0))`, `ΔR̃ ≈ exp((3e-5, 0, 0))` (~0.0017° x).
- **Velocity:** `Δṽ ≈ 3 · (0, 0, 0.00981) = (0, 0, 0.0294)`.
- **Position:** `Δp̃ ≈ (0, 0, 4.4e-5)`.

In `e_v`: hover comparison = `-g Δt = (0, 0, -0.0294)` cancels Δṽ → `e_v ≈ 0`. IMU and motion agree.

**Optimizer:** given pose / vel / pos at i, j + deltas → residuals + Jacobians. No re-int. Bias revise 0.001 rad/s → `ΔR̃` shifts by `J_{ΔR,b_g}·0.001`.

---

## 4 · Engineering view: where preintegration sits in a VIO

```
IMU 1 kHz ──► accumulator (incremental ΔR̃, Δṽ, Δp̃, Σ, J)
cam 30 Hz ──► freeze, emit factor → optimizer (Ceres / GTSAM)
              sliding window, IMU factor = one residual block per pair
```

| Per-LM-iter cost | |
|---|---|
| Naïve re-integration | 300 exp + matmul / iter |
| Forster | 0 IMU ops; bias = O(window) mat-vec |

Speedup ~10–50× on Orin `UNVERIFIED`. Bigger win: **opt time independent of IMU rate** — 200 Hz vs 1 kHz, same cost.

**When bias changes too much:** valid for small δb; gyro > ~0.05 rad/s or accel > ~0.1 m/s² → re-preintegrate. VINS-Mono re-triggers every few seconds.

**Covariance:** 9×9 (or 15×15 with biases) propagated forward = factor's info matrix. Forster 2017 §V.

---

## 5 · Capabilities & failure modes

### 5.1 Hidden Assumptions

- **Bias ≈ constant within interval** — biases drift slowly.
- **First-order bias correction accurate** — fails for large δb.
- **Gravity known in world frame** — needs initialisation.
- **IMU-cam time-synced** — sync >2 ms produces bias in Δṽ `UNVERIFIED`.
- **IMU noise white Gaussian** — props at 100–400 Hz violate this; need isolators + low-pass.

### Failure signatures

| Symptom | Cause |
|---|---|
| Position drift straight flight | Accel bias mis-init |
| Yaw drifts | Gyro bias not observable; need motion excitation |
| Bench OK, flight diverges | Prop vibration breaks white-noise; need IMU isolation |
| Preintegration jumps post bias update | First-order correction inadequate; re-integrate |

---

## 6 · Comparison & Interview Tip

| Approach | Where | Cost |
|---|---|---|
| Re-integrate every iter | naïve baseline | O(K) per iter |
| Forster preintegration | sliding-window / factor-graph VIO | O(K) once; O(1) per re-linearisation |
| MSCKF predict | filter VIO | O(K) once per propagation |

> **🎤 Interview Tip.** "How does VINS-Mono use a 1 kHz IMU in a 30 Hz optimizer?" — strong answer: "Forster preintegration. The IMU sequence factors into a pose-independent delta `(ΔR̃, Δṽ, Δp̃)` in the previous body frame, with stored Jacobians w.r.t. biases. On re-linearisation the deltas don't re-integrate — they shift by a first-order bias-correction mat-vec. IMU sequence consumed exactly once; optimization cost independent of IMU rate." Bonus: "Filter-based stacks like MSCKF propagate state through samples in the predict step — same observation (re-integration is the bottleneck), different fix."

---

## Boundary

This primer covers the preintegration algorithm. For:

- **SO(3) exp/log behind rotation accumulation** → `./se3_so3_lie_groups_primer.md`
- **EKF predict (MSCKF alternative)** → `./bayesian_filtering_ekf_msckf.md`
- **Factor graph consuming the IMU factor** → `./pose_graph_optimization.md` + `./bundle_adjustment.md`
- **VINS-Mono production** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`
- **IMU noise physics** → `foundations/sensor-physics/`

---

## References

- Forster, Carlone, Dellaert, Scaramuzza. *On-Manifold Preintegration for Real-Time VIO*, IEEE T-RO 2017, arXiv [1512.02363](https://arxiv.org/abs/1512.02363). **The IMU preintegration paper.**
- Forster et al. *IMU Preintegration on Manifold*, RSS 2015 (conference version).
- Lupton & Sukkarieh, IEEE T-RO 2012 (pre-Forster concept).
- Qin et al. *VINS-Mono*, IEEE T-RO 2018, https://arxiv.org/abs/1708.03852
- Sola, *Quaternion kinematics for error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- VINS-Mono: https://github.com/HKUST-Aerial-Robotics/VINS-Mono · OpenVINS: https://github.com/rpng/open_vins

[← Back to Spatial Math](./README.md)
