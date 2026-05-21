# SE(3) / SO(3) Lie Groups Primer (李群入门：旋转与刚体变换)

> **发布时间**: 2026-05-21
> **核心定位**: The prerequisite math behind every SLAM optimizer, IMU integrator, and pose-graph back-end since 2010.

**Status:** v1 — primer. `UNVERIFIED` numbers marked inline.
**TL;DR:** Rotations and rigid-body poses do **not** live in a vector space — you cannot average them, subtract them, or take Jacobians of them naively. The Lie-group / Lie-algebra trick maps them locally onto R³ / R⁶ via `exp` / `log`, where calculus works again. Every BA solver, EKF, and IMU preintegrator silently relies on this.

**X-Ray.** A rotation matrix has 9 entries but only 3 DoF — six constraints trap it on a curved manifold. Optimizers want flat R³. The Lie algebra `so(3)` is exactly that: a 3-vector tangent at identity. Move on the tangent, `exp` back to manifold. SE(3) extends to 6-DoF poses. Every "perturb the pose by δ" line in a SLAM paper is a tangent-space update — not naïve addition. (中文直觉：旋转不是向量，但它的"小扰动"是向量。)

## 📍 研究全景时间线

```
1850       2003              2013             2018          2024           2026
Lie groups► HZ unit-quat ► Strasdat Sim(3) ► Sola tutorial► VGGT bypasses► YOU ARE HERE
math        SLAM canonical  loop scale drift  arXiv 1812.01537 for SfM     classical still
                                                                            runs aerial VIO
```

Sola's *Lie Groups for 2D and 3D Transformations* (2018) is the cheat-sheet every SLAM lab uses.

---

## 1 · Architecture: rotation as a manifold, not a vector

### 1.1 Why naïve parametrisation breaks

Any 3-parameter rotation parametrisation (Euler, axis-angle) hits **gimbal lock** or singularities. Rotation matrices (9 numbers) drift off SO(3) after one Gauss-Newton step. Quaternions (4 numbers, 1 constraint) avoid lock but need re-normalisation. Lie-group approach: keep `R ∈ SO(3)` as-is; express *updates* in tangent space `so(3) ≅ R³`.

| Object | Group (manifold) | Algebra (tangent) | Dim |
|---|---|---|---|
| Rotation | SO(3) | so(3) | 3 |
| Rigid pose | SE(3) | se(3) | 6 |
| Scaled pose (loop closure) | Sim(3) | sim(3) | 7 |

### 1.2 ⚡ Eureka Moment

> **Rotation lives on a curved 3-manifold but its tangent at identity is flat R³ — store on the manifold, optimize on the tangent.**

This trick lets BA converge, lets the EKF linearise around SO(3) state, and lets IMU preintegration accumulate δθ as a vector. Everything else is bookkeeping.

### 1.3 Information flow

```
   manifold (curved)              tangent (flat)
   R ∈ SO(3)  ── log() ───►  φ ∈ so(3) ≅ R³
   T ∈ SE(3)  ◄── exp() ──   ξ ∈ se(3) ≅ R⁶
        ▲                            │
        └──────── R ← R · exp(δφ) ───┘
                  (right perturbation)
```

`exp` / `log` = matrix exponential / log — closed-form for SO(3) (Rodrigues).

---

## 2 · Math core: exp / log and the BCH formula

### 📌 Napkin Formula

```
R = exp(φ̂)       φ ∈ R³,  φ̂ = skew(φ)         (Rodrigues)
T = exp(ξ̂)       ξ = (ρ, φ) ∈ R⁶               (SE(3))
exp(â)·exp(b̂) ≈ exp(â + b̂ + ½[â,b̂] + ...)     (BCH)
```

Skew lifts a 3-vec to a 3×3 skew matrix. Rodrigues (closed-form SO(3) exp):

```
θ = |φ|, û = φ/θ
R = I + sin(θ) û + (1-cos θ) û²
```

**Right vs left perturbation:**

```
right: R_new = R · exp(δφ̂)        (body frame)
left:  R_new = exp(δφ̂) · R        (world frame)
```

ORB-SLAM3 / most C++ optimizers use **right**; some EKFs use left. Mixing them silently inverts Jacobians — top-3 cause of "my SLAM diverges" reports `UNVERIFIED`.

| Symbol | Lives in |
|---|---|
| `R` | SO(3) (3×3 orthonormal) |
| `φ` | so(3) ≅ R³ (rotation vector) |
| `T = [R, t]` | SE(3) (4×4 homogeneous) |
| `ξ = (ρ, φ)` | se(3) ≅ R⁶ (twist; `ρ` ≠ translation directly — Sola 2018) |

---

## 3 · Worked example: small-angle cycle

Take `φ = (0.01, 0, 0)` rad — 0.57° about x. Walk exp → R → log:

```
θ = 0.01,  û = (1, 0, 0),  sin θ ≈ 0.00999983,  1-cos θ ≈ 5e-5

       [ 1   0          0         ]
R  ≈  [ 0   0.99995   -0.00999983 ]
       [ 0   0.00999983  0.99995  ]

log(R) = θ·û = (0.01, 0, 0)   ✅ round-trip
```

Compose `R_a = exp(0.01 x̂)`, `R_b = exp(0.01 ŷ)`:

```
R_a · R_b = exp( (0.01, 0.01, 0) + ½·[x̂, ŷ] + higher )
```

The `½ [â, b̂]` cross-term is the **BCH correction**. At 0.01 rad it is ~5e-5; at 0.5 rad it dominates.

**Engineering impact.** IMU preintegration accumulates ~1000 micro-rotations per camera frame. Treating them as commutative builds O(N·θ²) error. Forster *T-RO 2017* is the bookkeeping that keeps BCH errors small.

---

## 4 · Engineering view: what code actually does

| Operation | Sophus idiom | Cost |
|---|---|---|
| Store pose | `Sophus::SE3d T` (quat + 3-vec) | 7 doubles |
| Apply perturbation | `T = T * SE3d::exp(xi)` | ~50 flops |
| Linearise around `T` | right-Jacobian `J_r(φ)` | closed form |
| Re-orthonormalise | `q.normalize()` | one sqrt |

Ceres / GTSAM / g2o all build manifold-aware solvers around these ops. `J_r(φ)` is the most error-prone term to derive by hand — every SLAM paper has its appendix because everyone copies it wrong once. `Sim(3)` adds uniform scale `s` (7-DoF) — used in ORB-SLAM3 loop closure for monocular scale drift.

---

## 5 · Where this primer is graded

Quality test: can you read ORB-SLAM3 source without re-googling exp/log every page?

- Plug `φ = (0.01, 0, 0)` into `Sophus::SO3d::exp(...)` and confirm Rodrigues output matches §3.
- Open ORB-SLAM3 `Optimizer.cc` → find `Sophus::SE3f::exp(xi)` and confirm right-perturbation.

---

## 6 · Capabilities & failure modes

| Can | Can't |
|---|---|
| Optimize rotations / poses without manifold drift | Globally optimize — only local convergence |
| Compose IMU micro-rotations correctly | Magic away gimbal lock if Euler appears downstream |
| Express uncertainty as 3×3 / 6×6 Gaussian on tangent | Capture multi-modal distributions |

### 6.1 Hidden Assumptions

- **Tangent approximation is local** — δφ ≲ 0.5 rad; larger jumps need re-linearisation.
- **Right vs left convention must be consistent** across the codebase — mixing inverts Jacobian sign.
- **Quaternion sign ambiguity** — `q` and `-q` represent same R; matters for slerp / averaging.
- **Floating-point drift** — repeated `R = R · exp(δ)` drifts off SO(3); re-orthonormalise periodically.

Broken assumptions produce *silent* wrong covariances — EKF / BA diverges quietly rather than loud.

---

## 7 · Comparison & Interview Tip

| Approach | Pros | Cons | Used by |
|---|---|---|---|
| Euler | 3 num, intuitive | gimbal lock | hobby IMU, animation |
| Rotation matrix | direct compose | 9 num, drifts | textbook math |
| Axis-angle | 3 num, no gimbal θ<π | singular at π | so(3) tangent |
| Unit quat | smooth, 4 num | sign / Hamilton vs JPL | SLAM / VIO / aerospace |
| Lie group | manifold-correct opt | learning curve | every modern SLAM solver |

> **🎤 Interview Tip.** "Why not store rotations as Euler?" — strong answer: "Gimbal lock, yes — but deeper, rotations form a curved manifold and optimization needs a flat tangent space; that's why we store on SO(3) and update via so(3) exp-log." Weak answer stops at "gimbal lock"; strong names the manifold.

---

## Boundary

This primer covers the math primitive. For:

- **System SE(3) in ORB-SLAM3** → `foundations/classical-slam/orb_slam3_dissection.md`
- **SE(3) in MSCKF state** → `./bayesian_filtering_ekf_msckf.md`
- **SE(3) in IMU preintegration** → `./imu_preintegration_math.md`
- **Sim(3) for loop closure** → `./pose_graph_optimization.md`

---

## References

- Sola, J. *A micro Lie theory for state estimation in robotics*, arXiv [1812.01537](https://arxiv.org/abs/1812.01537), 2018.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003. Ch. on 3D rotation parametrisation.
- Strasdat, H. *Scale Drift-Aware Large Scale Monocular SLAM*, RSS 2010. Sim(3) original.
- ORB-SLAM3 (Sophus usage): https://github.com/UZ-SLAMLab/ORB_SLAM3

[← Back to Spatial Math](./README.md)
