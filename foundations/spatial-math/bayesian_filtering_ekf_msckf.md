# Bayesian Filtering: EKF, UKF, MSCKF (贝叶斯滤波)

> **发布时间**: 2026-05-21
> **核心定位**: The filter family that runs aerial VIO under the 10 ms / 200 Hz wall — where BA-class optimization cannot fit. OpenVINS / Skydio-class systems use MSCKF for a reason.

**Status:** v1 — primer.
**TL;DR:** Filters propagate a Gaussian over state via predict-update. EKF linearises; UKF samples sigma points; MSCKF stores a window of past *poses* but no landmarks — bounded state, BA-quality, real-time. Payoff: fits Orin Nano where VINS-Mono's optimizer struggles `UNVERIFIED`.

**X-Ray.** A Kalman filter keeps a Gaussian over state, updates with each measurement. Linear → exact. Non-linear → EKF (linearise) or UKF (sample). VIO state with N landmarks is O(N), too big for 200 Hz. MSCKF (Mourikis 2007) keeps N past *poses* and marginalises landmarks at observation time — state bounded, every observation contributes jointly to in-window poses. This is the trick that lets phone-class CPUs run drone-grade VIO. (中文直觉：MSCKF 只存过去 N 个位姿，观测时把 landmark 边际化 — 状态不长。)

## 📍 研究全景时间线

```
1960     1995        2007             2014       2020          2026
Kalman ► UKF      ► MSCKF (Mourikis)► VINS-Mono ► OpenVINS    ► YOU ARE HERE
linear   sigma pts  Multi-State        opt-based  Geneva MSCKF   filter still beats
                    Constraint KF      counterpart                opt on sub-10ms VIO
```

Mourikis 2007 is the unsung hero of aerial VIO — without it, drones cannot run tightly-coupled VI at aerospace-controller rates. OpenVINS (Geneva 2020) is the canonical impl.

---

## 1 · Architecture: predict-update cycle

### 1.1 The Kalman family

| Filter | When |
|---|---|
| **KF** linear | rare in robotics |
| **EKF** non-linear + Jacobians | most VIO |
| **UKF** sigma points | strong non-linearity |
| **MSCKF** EKF + window of past poses, landmarks marginalised | high-rate VIO |

### 1.2 ⚡ Eureka Moment

> **MSCKF stores past *poses* in state but never landmarks — landmarks are triangulated then algebraically projected out (null-space marginalisation) before update. State bounded, every landmark contributes jointly to in-window poses.**

State is `O(N_poses)` not `O(N_poses + N_landmarks)`. Constant time per IMU sample regardless of feature count.

### 1.3 Information flow

```
IMU 200 Hz ──► predict step → [x: IMU | T_1...T_N]
cam 30 Hz ──► track f → triangulate X_f
            → stack r = [u_i - π(T_i, X_f)]
            → project onto null(H_Xf) → r̃ (no X_f)
            → EKF update with r̃
```

Null-space projection removes the landmark's residual contribution while preserving geometric info about the poses.

---

## 2 · Math core: EKF predict-update, MSCKF marginalisation

### 📌 Napkin Formula

```
predict:  x̂ = f(x̂),   P = F P Fᵀ + Q
update:   K = P Hᵀ (H P Hᵀ + R)⁻¹    (Kalman gain)
          x̂ ← x̂ + K(z - h(x̂))
          P ← (I - KH) P
```

`x`: state (IMU + N past poses for MSCKF); `P`: covariance; `F, H`: Jacobians; `Q, R`: process / measurement noise; `K`: trust ratio between meas and prediction.

### MSCKF state vector

```
x = [p_IB, v, q_IG, b_a, b_g | T_1...T_N]
    └── IMU state (15) ──┘ └─ N past poses (6N) ─┘
```

Window N ≈ 10–25 → state ~165–225 elements `UNVERIFIED OpenVINS config`.

### Null-space marginalisation

Feature `f` seen at `T_{i_1}...T_{i_k}`:

```
r_j ≈ H_T_j δT_j + H_Xf_j δX_f + n_j

Stack:  r = H_T δT + H_Xf δX_f + n
V = null(H_Xfᵀ)
Project: r̃ = Vᵀ r,  H̃ = Vᵀ H_T,  R̃ = Vᵀ R V

⇒ r̃ ≈ H̃ δT + ñ      (X_f gone, geometry preserved)

EKF update with r̃, H̃, R̃.
```

That is the algebraic core. Just linear algebra on residual blocks.

---

## 3 · Worked example: 2D EKF with one position observation

State `x = [px, py, vx, vy]ᵀ`. Init `x̂₀ = [0, 0, 1, 0]`, `P₀ = diag(0.1, 0.1, 0.01, 0.01)`. Constant-velocity dynamics, Δt = 1 s; `Q = diag(0, 0, 0.01, 0.01)`.

Predict: `x̂₁ = [1, 0, 1, 0]`, `P = F P Fᵀ + Q`.

GPS `z = [1.1, 0.05]`, `R = diag(0.05, 0.05)`, `H = [I₂ | 0₂]`:

```
S = H P Hᵀ + R         K = P Hᵀ S⁻¹
x̂ ← x̂ + K(z - Hx̂)     P ← (I - KH) P
```

Result ≈ `[1.05, 0.025, 1.05, 0.025]` — meas + prediction averaged by info weights. Velocity cov shrinks via correlation in P even though velocity wasn't observed.

**MSCKF analogue:** state 15 + 6N, predict integrates IMU, update stacks reprojection residuals across window with null-space projection.

---

## 4 · Engineering view: why MSCKF wins on aerial

| Approach | State | Cost | Orin Nano? |
|---|---|---|---|
| EKF-SLAM | 15 + 3M | `O(M³)` | no, M > 100 chokes |
| MSCKF | 15 + 6N (N≈20) | `O(N³)` bounded | ✅ 200 Hz `UNVERIFIED` |
| Sliding-window BA | 6N + 3M | LM ~10 ms/iter `UNVERIFIED` | ✅ 30 Hz |
| Full BA | grows | offline only | no |

**Bounded cost** makes MSCKF canonical for sub-10 ms VIO. Skydio / OpenVINS / ASL use it. Optimization wins on offline accuracy, loses on jitter.

**Why filter at high rate:** deterministic cost, absorbs IMU at full rate, no tail latency. Hard accuracy ceiling (one linearisation / update), but IMU dominates between camera frames anyway.

**Gotchas:** linearisation drift → iterated EKF; bias unobservable stationary → ZUPT; quaternion in state → error-state form; P non-PSD → Joseph form or sqrt-EKF.

---

## 5 · Capabilities & failure modes

### 5.1 Hidden Assumptions

- **Noise Gaussian** — rarely strictly true; need chi-square innovation rejection.
- **Linearisation accurate at current mean** — fails on large δ; iterated EKF or smaller Δt.
- **Jacobians correct** — IMU Jacobians vs quat + biases are the most error-prone code; copy from OpenVINS.
- **P stays PSD** — Joseph form or square-root EKF prevents drift.
- **Sufficient feature overlap** — each MSCKF feature needs ≥2 in-window observations.

### Failure signatures

| Symptom | Cause |
|---|---|
| Cov shrinks to zero | numerical underflow; missing Q |
| Linear drift in straight flight | bias not observable; need ZUPT or motion excitation |
| Estimate jumps on update | R over-confident; chi-sq miscalibrated |
| Diverges under high spin | linearisation error; iterated EKF or smaller window |

---

## 6 · Comparison & Interview Tip

| Estimator | Best for |
|---|---|
| EKF | low-dim, smooth state |
| UKF | strong non-linearity, no Jacobian |
| MSCKF | high-rate VIO (aerial, AR) |
| EKF-SLAM | small-scale 2D / indoor |
| Sliding-window opt | offline-quality online VIO (VINS-Mono) |
| iSAM2 | factor-graph smoothing |

> **🎤 Interview Tip.** "Why MSCKF instead of BA on Skydio / OpenVINS?" — strong answer: "Bounded state and deterministic update time. MSCKF keeps a sliding window of past poses in state but marginalises landmarks at observation via null-space projection — every feature contributes jointly to in-window poses without inflating state. Per-update is `O(N³)` for N≈20, fits under 10 ms on Orin. Sliding-window optimizers re-linearise per iter (more accurate) but have non-deterministic tail latency unsuitable for 200 Hz control." Bonus: "Jacobians are the production-bug surface — every MSCKF impl copies them from OpenVINS source for a reason."

---

## Boundary

This primer covers the filter math. For:

- **SO(3) error-state in filters** → `./se3_so3_lie_groups_primer.md`
- **JPL quaternion convention** → `./quaternions_and_rotations.md`
- **IMU integration feeding predict** → `./imu_preintegration_math.md`
- **OpenVINS code architecture** → `embodiments/aerial/vio/openvins_dissection.md`
- **VINS-Mono opt counterpart** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`

---

## References

- Kalman, *Trans. ASME* 1960.
- Julier & Uhlmann, *SPIE AeroSense* 1997 (UKF).
- Mourikis & Roumeliotis, *MSCKF for Vision-aided Inertial Nav*, ICRA 2007.
- Geneva et al. *OpenVINS*, ICRA 2020. https://arxiv.org/abs/1910.00298
- Sola, *Quaternion kinematics for error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- OpenVINS: https://github.com/rpng/open_vins · https://docs.openvins.com/

[← Back to Spatial Math](./README.md)
