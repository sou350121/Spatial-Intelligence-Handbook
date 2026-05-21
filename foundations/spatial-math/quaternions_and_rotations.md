# Quaternions and Rotation Representations (四元数与旋转表示)

> **发布时间**: 2026-05-21
> **核心定位**: Which rotation representation to use, when, and how the Hamilton vs JPL convention war has cost real teams real weeks.

**Status:** v1 — primer. Convention-conflict numbers from public SLAM forum reports `UNVERIFIED`.
**TL;DR:** Unit quaternions for storage, rotation matrices for transformation, axis-angle for tangent updates. Never Euler in real-time stacks. **Pin one quaternion convention (Hamilton or JPL) per repo** — silent mismatches sink integrations.

**X-Ray.** A 3D rotation has 3 DoF but every parametrisation pays a cost — Euler hits gimbal lock, matrices over-parametrise, axis-angle is singular at π, quaternions have a sign ambiguity. Unit quaternions win in practice: compose cheaply, slerp smoothly, stay manifold-correct without re-orthonormalisation. Catch: graphics (Hamilton) vs aerospace (JPL) write the math with opposite multiplication order. (中文直觉：旋转有四种穿法，四元数最优 — 但要确认是 Hamilton 还是 JPL。)

## 📍 研究全景时间线

```
1843        2003           2005                  2018         2026
Hamilton ► HZ textbook ► Trawny-Roumeliotis ► JPL tech    ► YOU ARE HERE
quaternions Hamilton SLAM "Indirect KF / 3D Attitude" (JPL) convention war
                                                            still bites stacks
```

Trawny-Roumeliotis 2005 is why OpenVINS / MSCKF uses JPL while ROS / ORB-SLAM3 uses Hamilton. **Both correct; both incompatible.**

---

## 1 · The four representations (and one anti-pattern)

| Repr | Storage | Composition | Singularity | Interpolation | Real-time SLAM use |
|---|---|---|---|---|---|
| **Euler (roll/pitch/yaw)** | 3 floats | 3 trig ops, order-dependent | gimbal lock | ugly | ❌ anti-pattern in SLAM |
| **Rotation matrix R** | 9 floats | 1 matmul (27 mul + 18 add) | none | nlerp on each row, then re-orthonormalise | rarely stored, used for transforming points |
| **Axis-angle / rotvec** | 3 floats | needs exp-log round-trip | at θ = π | linear on axis, ok for small θ | tangent-space updates only |
| **Unit quaternion** | 4 floats (1 constraint) | 16 mul + 12 add | sign ambiguity | slerp (clean) | ★ canonical storage |

### 1.1 Why Euler is forbidden in SLAM stacks

1. **Order ambiguity** — ZYX vs ZXY vs ... 12 conventions, rarely documented.
2. **Gimbal lock** at pitch = ±90° — drone flying inverted hits this; conversion Jacobian singular; EKF blows up.
3. **No clean composition** — combining Euler triples requires rotation matrix anyway.

Euler is for *display*. Never the canonical state.

### 1.2 ⚡ Eureka Moment

> **Unit quaternions are the only repr that is (a) singularity-free, (b) double-cover smooth at identity, (c) cheap to compose, (d) interpolatable — all four at once. Every other drops at least one.**

This is why shipping aerial / AR / AD attitude estimators since 2015 store quaternions, even though papers write rotation-matrix equations for readability.

---

## 2 · Math core: quaternion algebra

### 📌 Napkin Formula

```
q = (w, x, y, z) = w + xi + yj + zk,  |q| = 1
ij = k, jk = i, ki = j        (Hamilton)
ji = k, kj = i, ik = j        (JPL — flipped sign)
```

The sign flip is not "different math" — it is which side a vector rotates from. Identical-looking equations produce transposed rotations.

| Aspect | Hamilton | JPL |
|---|---|---|
| `ij =` | `+k` | `-k` |
| `R(q) v` | active rotation | passive (frame change) |
| `q1 ⊗ q2` | composes left-to-right | right-to-left |
| Used by | Eigen, ROS tf, GTSAM, ORB-SLAM3, HZ | OpenVINS, MSCKF, aerospace |
| First bug | rotations backwards | covariance Jacobians transposed |

A Hamilton lib fed JPL data compiles fine — output drifts slowly in straight flight, explodes in turns. Teams have lost weeks here `UNVERIFIED`.

---

## 3 · Worked example: a Hamilton-vs-JPL collision in real code

Team integrates OpenVINS IMU front-end (JPL) with ORB-SLAM3 back-end (Hamilton). Quaternions flow front → back.

Both stacks define `Quaternion(w, x, y, z)` same layout. Both expose `toRotationMatrix()`. Identity unit tests pass. **The bug appears at runtime under yaw.**

```
front (JPL):     q_FE = (0.7071, 0, 0, 0.7071)   // 90° about z
                  → "rotates body-z to world-x"

back (Hamilton): same q bits → R = ...
                  → "rotates world-z to body-x"
```

Same quaternion, opposite interpretation. Every pose *transposed*. Position fine in straight flight (identity dominates), wrong by ~2θ in turns.

**Fix:** at integration boundary, `q_out = q_in.conjugate()` if active-vs-passive is the conflict. Document convention next to the boundary.

---

## 4 · Engineering view: slerp, normalisation, double cover

```
slerp(q0, q1, t) = sin((1-t)θ)/sin(θ)·q0 + sin(tθ)/sin(θ)·q1
where cos θ = q0 · q1   (4D dot)
```

If `q0·q1 < 0`, flip (`q1 = -q1`) before slerping — else interpolation goes the long way around. **Double-cover ambiguity** in practice.

**Renorm cadence.** Double-precision drifts ~1e-15 per op; 10 min at 200 Hz ≈ 1e-9 drift, negligible. Float32 drifts ~1e-7 per op, renorm every ~1000 ops. Idiom: renorm in predict step, not every multiply.

| Repr | Bytes (dbl) | Compose | Rotate vec |
|---|---|---|---|
| Quaternion | 32 | 16 mul + 12 add | ~30 flops `q v q*` |
| Rotation matrix | 72 | 27 mul + 18 add | 9 mul + 6 add |

10k keyframes: quaternions save ~400 KB and stay manifold-correct. Convert to R per-query for point transforms.

---

## 5 · When each repr is right

| Need | Use |
|---|---|
| Store keyframe pose | quaternion + translation (7 doubles) |
| Transform point cloud | rotation matrix (matmul) |
| Tangent-space update | axis-angle (so(3)) |
| Human log display | Euler (deg) — only place Euler belongs |
| Average N rotations | eigendecomp of `Σ q_i q_iᵀ` (Markley 2007) |
| Interpolate poses | slerp |

---

## 6 · Failure modes & Hidden Assumptions

| Failure | Cause |
|---|---|
| Drone flips at pitch 89° | Euler in stack, gimbal lock |
| Rotations transposed | Hamilton-vs-JPL mismatch |
| Slerp long-way-around | forgot `q0·q1 < 0` flip |
| Drift off SO(3) after 1M ops | missed renorm, float32 |
| Avg quat garbage | naïve component avg, need eigendecomp |

### 6.1 Hidden Assumptions

- **Convention pinned** — Hamilton or JPL, documented; never silently mixed across boundaries.
- **Storage is unit-norm** — renorm after accumulations.
- **Sign canonical** — flip `q ← -q` when `w < 0` before slerp / compare.
- **Coords documented** — body vs world, FRD (aerospace) vs FLU (ROS).
- **Active vs passive matches** the rotation-matrix convention downstream (Eigen / Sophus).

Any mismatch produces *silent* garbage that passes identity unit tests.

---

## 7 · Interview Tip

> **🎤 Interview Tip.** "Why quaternions over rotation matrices?" — strong answer hits three: (1) singularity-free 4-vec vs 9-entry redundant matrix, (2) manifold-correct under composition without re-orthonormalisation, (3) clean slerp interpolation. Add: "and we pin Hamilton vs JPL at the repo boundary because they are silently incompatible." That last sentence signals production experience.

---

## Boundary

This primer covers the *parametrisation choice*. For:

- **so(3) exp/log tangent updates** → `./se3_so3_lie_groups_primer.md`
- **Quaternion EKF state propagation** → `./bayesian_filtering_ekf_msckf.md`
- **IMU preintegration quaternion accumulation** → `./imu_preintegration_math.md`
- **OpenVINS JPL impl** → `embodiments/aerial/vio/openvins_dissection.md`

---

## References

- Hamilton, *Elements of Quaternions*, 1866.
- Trawny & Roumeliotis, *Indirect KF for 3D Attitude Estimation*, UMN Tech Report 2005-002.
- Sola, *Quaternion kinematics for the error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- Markley et al., *Averaging Quaternions*, JGCD 30(4), 2007.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003 (Hamilton convention).
- OpenVINS docs (JPL): https://docs.openvins.com/

[← Back to Spatial Math](./README.md)
