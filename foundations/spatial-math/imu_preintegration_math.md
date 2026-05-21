# IMU Preintegration (IMU 预积分)

> **发布时间**: 2026-05-21
> **核心定位**: Forster *T-RO 2017* 的那个 trick —— 让 VINS-Mono / OpenVINS 在 30 Hz 优化循环里用 1000 Hz IMU 测量，*而不必*在每次线性化时从头重新积分每个样本。

**Status:** v1.1 —— primer + production 优化深度讨论 (2026-05-22 加 §6, 10 项工程实战主题)。
**TL;DR:** 朴素 IMU 积分在每次位姿扰动后都要从头跑 —— 每次线性化 `O(K)`，代价过高。预积分在上一帧 body frame 里计算一个与位姿无关的 summary；重新线性化 = 闭式的 bias 修正。每个 ≥200 Hz IMU 的紧耦合 VIO 都靠这个。**Forster 是起点，§6 的 10 项 production 优化是从 lab demo 到飞稳的真功夫。**

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

## 6 · 深入 IMU 优化讨论

> Forster 预积分只是起点。production VIO 在 Forster 之上叠了 10 层优化才能在真机上稳定 200 Hz —— 这一节讲那些层。

### 6.1 Bias 当滑窗优化的 state（不是 calibration 常量）

朴素思路：bias 在 lab 标定一次，然后当常量。**production 反过来：bias 是优化变量。**

```
   state vector per keyframe i:
     x_i = [ R_i ∈ SO(3) ,  p_i ∈ R³ ,  v_i ∈ R³ ,  b_g,i ∈ R³ ,  b_a,i ∈ R³ ]
                                                    └─────── 在线 estimate ───────┘
   
   bias 在 keyframe 间走 random walk:
     b_*,j = b_*,i + n_walk,Δt        with covariance σ²_walk · Δt
```

**含义**:
- IMU preintegration 用的 `b̄` 是 *当前线性化点*；优化器在线更新它
- 因子图里 bias 之间有 walk factor（先验：bias 漂得慢）
- **Marginalize 旧 keyframe** 时要把 bias 的 schur complement 推回剩下的滑窗 —— 这是 OpenVINS / VINS-Mono 滑窗优化的核心代价

**Bias prior** 是工程关键 —— 没 prior bias 在静止时会从噪声里学错值，飞起来直接漂掉。

### 6.2 Time Synchronization（Hardware vs Online TD）

```
   Camera (30 Hz) ─┐                                           ┌─► RGB exposure
                   │  hardware sync                            │
                   │  - Trigger line:  ✦✦✦  μs 级 (理想)        │
                   │  - PTP:           ✦✦   ms 级 (现实)         │
                   │  - Software TS:   ✦    10-100 ms 漂动 (悲剧) │
                   ▼                                           │
                Master clock ─────────────────────────────────►│
                                                               │
   IMU (1 kHz)  ─►                                              ▼
                                                                                     
                                                  optimization 里:
                                                  td = camera_ts - imu_ts   (state!)
                                                  
                                                  Forster delta 偏移:
                                                    Δp̃ → Δp̃ - v · td
                                                    Δv 略受影响
```

**production 实践**：
- 硬件触发同步 td < 1 ms → td 在 lab 一次性标定
- PTP 同步 td ~10 ms 抖动 → **td 当 state 在线 estimate**（VINS-Mono `temporal_calib: 1`）
- 软件时间戳 td 几十 ms → 上不了高动态 VIO，**根本性故障**

> **2 ms 是分界**：sync error > 2 ms 在 1 m/s 运动下产生 2 mm 位置误差（per Forster 2017 §VII）。无人机 5 m/s 飞行下放大 5×。

### 6.3 IMU Intrinsics 在线 refinement（scale / misalignment / g-sensitivity）

实际 IMU 不是完美的 `a_meas = a_true + b_a + n`：

```
   完整模型:
                                                              
     a_meas = M_a · S_a · (a_true + g) + b_a + ε_g · ω_true + n
              ↑     ↑                          ↑
            misalign scale factor      g-sensitivity (gyro 影响 accel)
              3×3   diag (3 scalars)        3×3 cross-axis
   
   typical magnitudes (consumer MEMS, BMI270):
     scale factor:    ~0.5% drift over temperature
     misalignment:    ~0.5° between IMU & body
     g-sensitivity:   ~0.05 (deg/s) / g                          
```

**生产 trick**：
- Kalibr 在 lab 离线标 → 给优化器当 *prior* 而不是常数
- Production VIO 在线 refine 这些（VINS-Fusion `estimate_imu_intrinsic`）—— 但**可观测性弱**，需要足够 motion 激发
- 漂温度敏感 → 温度补偿表（Skydio / DJI 都有内部 LUT，`UNVERIFIED`）

### 6.4 IMU-Camera Extrinsics 在线 estimate

```
   T_BC ∈ SE(3) = IMU body frame → camera frame transform
   
   离线: Kalibr (Furgale ETHZ) target-based 标定, 误差 ~1 mm / 0.1°
   在线: T_BC 当 state, 优化器在线 refine
   
   可观测性条件 (Yang et al., RAL 2019):
     - 至少 3 axes of angular motion (rich rotation)
     - 至少 1 axis of acceleration (excite translation)
   
   悬停 drone 静止 → T_BC 完全不可观测；要先飞个 figure-8 再激活。
```

**production**：VINS-Mono 默认 `estimate_extrinsic: 0`（信任 Kalibr）；OpenVINS 提供 `estimate_extrinsic: 1` 选项；UZH RPG 赛车队飞前先做 motion excitation maneuver。

### 6.5 Continuous-Time Preintegration（GP / B-spline）

```
   离散 (Forster, 通用):
     ΔR̃ = Π_k exp((ω_k - b_g) · Δt)        ← 假设 Δt 内常速度
   
   连续时间 (Furgale et al., Anderson 2013):
     ω(t) = B-spline basis · control points
     ΔR̃ = closed-form integral over spline
   
   优势:
     - 异步 sensor (cam @ 30 Hz, IMU @ 1 kHz, LiDAR @ 10 Hz) 自然处理
     - 高频 IMU (>1 kHz) 无需 sub-step
     - 平滑 trajectory (运动模糊修复)
   
   代价:
     - control point 是新的 state → 优化规模涨
     - 实时性差 (offline / batch 更合适)
```

**主要使用者**: Cartographer (Google), Kalibr (ETHZ); production VIO 仍以离散为主。

### 6.6 Invariant EKF (IEKF) —— EKF 的几何升级

Barrau & Bonnabel 2017 发现：经典 EKF 把 SE(3) 当 R⁶ 线性化 → 线性化误差累积。**Invariant EKF** 在群的右扰动 / 左扰动框架里线性化 → 线性化误差不随状态值漂移。

```
   classical EKF (problematic):
     state error: δx ∈ R^15 (additive)
     linearization point: 当前 estimate (随漂移变)
     covariance growth: 与状态绝对值耦合
   
   Invariant EKF:
     state error: η ∈ Lie algebra (group multiplicative)
     linearization point: identity (与状态值无关)
     covariance growth: 与状态值解耦, 长 session 更稳
```

**实证**: IEKF 在长 session（>30 min）比 EKF / MSCKF 稳得多。OpenVINS 默认仍是 MSCKF；近年 production 渐渐迁 IEKF（Skydio 内部 `UNVERIFIED`）。

### 6.7 高频振动处理（aerial 关键）

```
   IMU 噪声谱:
     |
     |   ●●●●●●●●●●●●●  ← 白噪声 baseline (Allan ARW)
     |          ████████  ← propeller 100-400 Hz (drone)
     |          ░░░░░     ← motor magnetic interference
     |   ─────────────────────────► frequency
     0       100   400   1000 Hz
   
   消除手段 (production):
     ① 机械: 减震硅胶 / 双层金属外壳   (~6 dB)
     ② 电学: bandpass 30-200 Hz       (cut both DC drift & prop band)
     ③ 软件: 频域 notch filter @ prop fundamental + harmonics
     ④ Forster delta 处理: 不用，预积分假设白噪声
```

**经典坑**：台架测试 IMU 干净 → 飞起来 prop 一开 IMU 噪声爆炸 → preintegration covariance underestimate → 优化器过度信任 IMU → 漂飞。
**修法**: 飞行中 *measure* prop band noise → 把 σ_ω² 调大到匹配 → preintegration covariance 反映现实。

### 6.8 Multi-IMU Fusion（humanoid / 大型机器人）

```
   Humanoid 多 IMU 网络 (典型):
                   📐 head IMU (~5 g, low noise)
                       │
                       ├── pelvis IMU (~10 g, baseline)
                       │
                   📐  ├── L-foot IMU         📐  R-foot IMU
                       │   (high g impact)        (similar)
                       │
                   📐  ├── L-arm IMU         📐  R-arm IMU
                       │
   
   Fusion strategy 1: 选 master IMU (pelvis) preintegrate, 其他当观测
   Fusion strategy 2: 多 IMU 同时 preintegrate, 因子图加 IMU-IMU 约束
   Fusion strategy 3: 跨刚体 (foot impact) 重新初始化邻居
```

**Unitree / Figure / 1X** 各有 proprietary 方案 `UNVERIFIED`。开源没现成多 IMU VINS。

### 6.9 计算优化（SIMD / lazy / GPU）

| 优化 | 收益 | 复杂度 |
|---|---|---|
| **SIMD exp/log on SO(3)** (NEON / AVX) | 2-4× | 中（用 Sophus / Eigen 接口）|
| **Lazy 重新积分**（仅 \|δb\| > threshold 时）| 5-10× LM iter 加速 | 低 |
| **Sliding-window marginalization** | 把 O(window²) 压成 O(window) | 高（Schur complement 推导）|
| **GPU preintegration** | 单机 < 2× (overhead 太高)；多 robot fleet 偶尔有用 | 高 |
| **Mixed precision (FP16 for delta, FP32 for state)** | 略加速 + 严重精度损失 | 不推荐 |

> **生产实践**: Skydio / DJI 内部用 SIMD + lazy 是默认；GPU preintegration 不值得（IMU 序列本身太短，PCIe 来回 overhead > 加速）。

### 6.10 数值稳定性 trade-offs

```
   旋转参数化 trade-off:
   ─────────────────────────────────────────────
   选项             存储    复合代价   奇异性    适用
   ─────────────────────────────────────────────
   Quaternion       4d      ~20 op    ❌        IMU prop (production)
   Rotation matrix  9d      ~36 op    ❌        优化器 (Forster delta)
   Lie algebra      3d      exp/log   gimbal    线性化局部
   Euler angles     3d      cheap     gimbal    人类可读 (debug only)
   
   production VIO 实践:
     • IMU 高速 propagation       → Quaternion (storage + composition 平衡)
     • 优化器内部                  → Rotation matrix (Forster delta 公式)
     • 显示 / log                  → Euler (debug)
     • 跨边界传输                  → 永远 Quaternion + careful Hamilton/JPL!
```

⚠️ **Hamilton vs JPL convention**：IMU 输出（drivers）默认 JPL；Eigen / Sophus 默认 Hamilton；混用会让 IMU preintegration 静默错。每次跨边界（driver → app, app → optimizer）都 explicit 标 convention。**production VIO #1 静默 bug**。

---

## 7 · 比较 & 面试 Tip

| 方法 | 用在哪 | 代价 |
|---|---|---|
| 每 iter 重新积分 | 朴素 baseline | 每 iter `O(K)` |
| Forster 预积分 | 滑窗 / factor-graph VIO | 一次 `O(K)`；重新线性化 `O(1)` |
| MSCKF predict | filter VIO | 每次 propagate 一次 `O(K)` |

> **🎤 Interview Tip.** "VINS-Mono 怎么把 1 kHz IMU 塞进 30 Hz 优化器？" —— 强答："Forster 预积分。IMU 序列被因式化成上一帧 body frame 里与位姿无关的 delta `(ΔR̃, Δṽ, Δp̃)`，并存了对 bias 的 Jacobian。重新线性化时 delta 不重积 —— 通过一次一阶 bias-修正 mat-vec 平移。IMU 序列只被吃一次；优化代价与 IMU 速率无关。" 加分："MSCKF 这种 filter 在 predict step 里把状态推过样本 —— 同一个观测（重新积分是瓶颈），不同的修法。"

---

## Boundary

这篇 primer 覆盖预积分算法 + §6 production 优化。如需：

- **旋转累积背后的 SO(3) exp/log** → `./se3_so3_lie_groups_primer.md`
- **四元数 Hamilton vs JPL 详** → `./quaternions_and_rotations.md`
- **EKF predict（MSCKF 替代方案）** → `./bayesian_filtering_ekf_msckf.md`
- **消费 IMU factor 的 factor graph** → `./pose_graph_optimization.md` + `./bundle_adjustment.md`
- **VINS-Mono 量产代码 / 调参** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`
- **OpenVINS MSCKF 工程** → `embodiments/aerial/vio/openvins_dissection.md`
- **IMU 噪声物理 + Allan variance** → `foundations/sensor-physics/imu_physics_and_noise_model.md`
- **Sensor 同步 hardware/PTP** → `deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md`

---

## References

- Forster, Carlone, Dellaert, Scaramuzza. *On-Manifold Preintegration for Real-Time VIO*, IEEE T-RO 2017, arXiv [1512.02363](https://arxiv.org/abs/1512.02363). **The IMU preintegration paper.**
- Forster et al. *IMU Preintegration on Manifold*, RSS 2015 (conference version).
- Lupton & Sukkarieh, IEEE T-RO 2012 (pre-Forster concept).
- Qin et al. *VINS-Mono*, IEEE T-RO 2018, https://arxiv.org/abs/1708.03852
- Sola, *Quaternion kinematics for error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- VINS-Mono: https://github.com/HKUST-Aerial-Robotics/VINS-Mono · OpenVINS: https://github.com/rpng/open_vins

[← Back to Spatial Math](./README.md)
