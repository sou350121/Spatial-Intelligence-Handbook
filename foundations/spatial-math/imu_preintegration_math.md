# IMU Preintegration (IMU 预积分)

> **发布时间**: 2026-05-21
> **核心定位**: Forster *T-RO 2017* 的那个 trick —— 让 VINS-Mono / OpenVINS 在 30 Hz 优化循环里用 1000 Hz IMU 测量，*而不必*在每次线性化时从头重新积分每个样本。

**Status:** v1 —— primer。
**TL;DR:** 朴素 IMU 积分在每次位姿扰动后都要从头跑 —— 每次线性化 `O(K)`，代价过高。预积分在上一帧 body frame 里计算一个与位姿无关的 summary；重新线性化 = 闭式的 bias 修正。每个 ≥200 Hz IMU 的紧耦合 VIO 都靠这个。

**X-Ray.** Drone IMU 跑 ~1000 Hz，相机 ~30 Hz —— 帧间约 33 个样本。优化器把帧当状态，IMU 当帧间约束。朴素：每次扰动都重新积 33 个样本。Forster 把积分因式化成 `(ΔR, Δv, Δp)`，只依赖于读数 + bias，不依赖初始位姿 —— 位姿在最后再复合。一个让 VINS-Mono / OpenVINS 跑得起来的代数 trick。（中文：IMU 段=相机帧间位姿增量，只依赖测量与偏置。）

## 📍 研究全景时间线

```
2011     2015            2017            2018-2020          2026
Lupton ► Forster RSS  ► Forster T-RO  ► VINS-Mono+OpenVINS ► YOU ARE HERE
preint   on-manifold    "the IMU paper" ship it             preint default
SLAM                                                         tightly-coupled VIO
```

Forster 2017 是规范引用。工程上的回报：「VIO 跑得起来」。

---

## 1 · 架构：为什么朴素积分太慢

### 1.1 问题

帧 `k-1` 到 `k` 之间，IMU 给出 `{a_i, ω_i}_{i=0}^{K-1}`。朴素：

```
R_k = R_{k-1} · Π_i exp((ω_i - b_g) Δt)
v_k = v_{k-1} + g KΔt + R_{k-1} · Σ_i [...]
p_k = p_{k-1} + v_{k-1} KΔt + ...
```

`R_{k-1}, v_{k-1}` 出现在每一行。每次扰动都要重新积 K 个样本。10 kf × 30 样本 × 10 LM × 30 Hz → ~100k IMU 积分/秒 —— 痛苦。

### 1.2 ⚡ Eureka Moment

> **把 IMU 序列因式化成上一帧 body frame 里与位姿无关的 delta `(ΔR, Δv, Δp)` —— 位姿在最后复合。重新线性化 = 一阶 bias 修正，不重新积分。**

Trick：在*上一帧 body frame* 内积分（无绝对位姿依赖）。Bias → 一阶 Taylor。

### 1.3 数据流

```
IMU 1 kHz ─► preintegration accumulator (incremental)
                 ▼
             (ΔR̃, Δṽ, Δp̃, J_bias, Σ) — pose-independent, bias-linearised
                 ▼
cam 30 Hz ─► optimizer consumes as one relative-pose factor between i and j
             re-linearisation = closed-form bias correction (no re-int)
```

---

## 2 · 数学核心：三个预积分的 delta

### 📌 Napkin Formula

```
ΔR̃_ij = Π_{k} exp((ω_k - b̄_g) Δt)                       ← rotation
Δṽ_ij = Σ_{k} ΔR̃_ik · (a_k - b̄_a) · Δt                  ← velocity
Δp̃_ij = Σ_{k} [Δṽ_ik Δt + ½ ΔR̃_ik (a_k - b̄_a) Δt²]      ← position
```

三者都在时间 `i` 的 body frame 里 —— 不依赖 i 处的绝对位姿。Bias `b̄` 固定在线性化点。

### 复合（residual）

```
e_R = log(ΔR̃_ij⁻¹ R_iᵀ R_j)
e_v = R_iᵀ(v_j - v_i - g Δt_ij) - Δṽ_ij
e_p = R_iᵀ(p_j - p_i - v_i Δt_ij - ½g Δt_ij²) - Δp̃_ij
```

delta 是优化器拿来跟当前位姿 / 速度对照的常量。无需重新积分。

### Bias 更新修正

`b̄ → b̄ + δb` 让 delta 做一阶平移：

```
ΔR̃(b̄ + δb_g) ≈ ΔR̃(b̄) · exp(J_{ΔR,b_g} δb_g)
Δṽ(b̄ + δb)   ≈ Δṽ(b̄) + J_{Δv,·} δb
Δp̃(b̄ + δb)   ≈ Δp̃(b̄) + J_{Δp,·} δb
```

Jacobian 存一次。Bias 更新 = 一次 mat-vec。**Forster 2017 的头条。**

变量：`ω_k, a_k`（读数）；`b̄_g, b̄_a`（bias）；`ΔR̃, Δṽ, Δp̃`（delta）；`Σ_ij`（factor 信息矩阵）；`g`（重力）；`Δt`（IMU 周期）。

---

## 3 · 玩具例子：相机两帧之间 3 个 IMU 样本

drone 悬停，3 ms 间隔，1 kHz 取 3 个样本。Bias `b̄_g = (0.001, 0, 0)`、`b̄_a = (0, 0, 0.05)`。

每步去 bias：`ω - b̄_g = (0.01, 0, 0)`、`a - b̄_a = (0, 0, 9.81)`。

- **旋转:** `δR_k = exp((1e-5, 0, 0))`、`ΔR̃ ≈ exp((3e-5, 0, 0))`（~0.0017° x）。
- **速度:** `Δṽ ≈ 3 · (0, 0, 0.00981) = (0, 0, 0.0294)`。
- **位置:** `Δp̃ ≈ (0, 0, 4.4e-5)`。

`e_v` 里：悬停时对照 `-g Δt = (0, 0, -0.0294)` 抵消 Δṽ → `e_v ≈ 0`。IMU 与运动一致。

**优化器:** 给定 i / j 处的位姿 / 速度 / 位置 + delta → residual + Jacobian。无需重新积分。Bias 修 0.001 rad/s → `ΔR̃` 按 `J_{ΔR,b_g}·0.001` 平移。

---

## 4 · 工程视角：预积分在 VIO 里的位置

```
IMU 1 kHz ──► accumulator (incremental ΔR̃, Δṽ, Δp̃, Σ, J)
cam 30 Hz ──► freeze, emit factor → optimizer (Ceres / GTSAM)
              sliding window, IMU factor = one residual block per pair
```

| 每次 LM iter 的代价 | |
|---|---|
| 朴素重新积分 | 300 次 exp + matmul / iter |
| Forster | 0 次 IMU op；bias = O(window) mat-vec |

Orin 上加速约 10–50× `UNVERIFIED`。更大的胜利是 **优化时间与 IMU 速率无关** —— 200 Hz vs 1 kHz，代价相同。

**bias 变化过大时怎么办:** δb 小时有效；gyro > ~0.05 rad/s 或 accel > ~0.1 m/s² 就要重新预积分。VINS-Mono 每隔几秒触发一次。

**协方差:** 向前传播的 9×9（带 bias 是 15×15）= factor 的信息矩阵。Forster 2017 §V。

---

## 5 · 能力与失败模式

### 5.1 Hidden Assumptions

- **区间内 bias 近似常数** —— bias 漂得慢。
- **一阶 bias 修正准确** —— 大 δb 时失败。
- **世界系下 gravity 已知** —— 需初始化。
- **IMU 与相机时间同步** —— 同步偏移 > 2 ms 会在 Δṽ 里引入 bias `UNVERIFIED`。
- **IMU 噪声白色 Gaussian** —— 100–400 Hz 的桨叶违反此条；要 isolator + 低通。

### 失败特征

| 现象 | 原因 |
|---|---|
| 直飞位置漂 | Accel bias 初始化错 |
| Yaw 漂 | Gyro bias 不可观；需激发运动 |
| 台架 OK、飞起来发散 | 桨振破坏白噪声；需 IMU 隔振 |
| bias 更新后预积分跳变 | 一阶修正不够；重新积分 |

---

## 6 · 比较 & 面试 Tip

| 方法 | 用在哪 | 代价 |
|---|---|---|
| 每 iter 重新积分 | 朴素 baseline | 每 iter `O(K)` |
| Forster 预积分 | 滑窗 / factor-graph VIO | 一次 `O(K)`；重新线性化 `O(1)` |
| MSCKF predict | filter VIO | 每次 propagate 一次 `O(K)` |

> **🎤 Interview Tip.** "VINS-Mono 怎么把 1 kHz IMU 塞进 30 Hz 优化器？" —— 强答："Forster 预积分。IMU 序列被因式化成上一帧 body frame 里与位姿无关的 delta `(ΔR̃, Δṽ, Δp̃)`，并存了对 bias 的 Jacobian。重新线性化时 delta 不重积 —— 通过一次一阶 bias-修正 mat-vec 平移。IMU 序列只被吃一次；优化代价与 IMU 速率无关。" 加分："MSCKF 这种 filter 在 predict step 里把状态推过样本 —— 同一个观测（重新积分是瓶颈），不同的修法。"

---

## Boundary

这篇 primer 只覆盖预积分算法。如需：

- **旋转累积背后的 SO(3) exp/log** → `./se3_so3_lie_groups_primer.md`
- **EKF predict（MSCKF 替代方案）** → `./bayesian_filtering_ekf_msckf.md`
- **消费 IMU factor 的 factor graph** → `./pose_graph_optimization.md` + `./bundle_adjustment.md`
- **VINS-Mono 量产** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`
- **IMU 噪声物理** → `foundations/sensor-physics/`

---

## References

- Forster, Carlone, Dellaert, Scaramuzza. *On-Manifold Preintegration for Real-Time VIO*, IEEE T-RO 2017, arXiv [1512.02363](https://arxiv.org/abs/1512.02363). **The IMU preintegration paper.**
- Forster et al. *IMU Preintegration on Manifold*, RSS 2015 (conference version).
- Lupton & Sukkarieh, IEEE T-RO 2012 (pre-Forster concept).
- Qin et al. *VINS-Mono*, IEEE T-RO 2018, https://arxiv.org/abs/1708.03852
- Sola, *Quaternion kinematics for error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- VINS-Mono: https://github.com/HKUST-Aerial-Robotics/VINS-Mono · OpenVINS: https://github.com/rpng/open_vins

[← Back to Spatial Math](./README.md)
