# Bayesian Filtering: EKF, UKF, MSCKF (贝叶斯滤波)

> **发布时间**: 2026-05-21
> **核心定位**: 在 10 ms / 200 Hz 这堵墙下跑 aerial VIO 的滤波器家族 —— BA 级优化进不来的地方。OpenVINS / Skydio 级系统选 MSCKF 有原因。

**Status:** v1 —— primer。
**TL;DR:** 滤波器把状态的 Gaussian 通过 predict-update 向前传播。EKF 线性化；UKF 采 sigma point；MSCKF 在状态里保留过去一窗口的*位姿*但不存 landmark —— 状态有界、精度接近 BA、实时可行。回报：能跑在 Orin Nano 上，而 VINS-Mono 的优化器在这里挣扎 `UNVERIFIED`。

**X-Ray.** Kalman filter 维护状态的 Gaussian，每个测量更新一次。线性 → 精确。非线性 → EKF（线性化）或 UKF（采样）。带 N 个 landmark 的 VIO 状态是 O(N)，200 Hz 太大。MSCKF（Mourikis 2007）只保留过去 N 个*位姿*，在观测时把 landmark 边际化 —— 状态有界，每个观测对窗口内所有位姿都做联合贡献。这正是手机级 CPU 能跑 drone 级 VIO 的关键 trick。（中文直觉：MSCKF 只存过去 N 个位姿，观测时把 landmark 边际化 —— 状态不长。）

## 📍 研究全景时间线

```
1960     1995        2007             2014       2020          2026
Kalman ► UKF      ► MSCKF (Mourikis)► VINS-Mono ► OpenVINS    ► YOU ARE HERE
linear   sigma pts  Multi-State        opt-based  Geneva MSCKF   filter still beats
                    Constraint KF      counterpart                opt on sub-10ms VIO
```

Mourikis 2007 是 aerial VIO 不为人知的功臣 —— 没有它，drone 无法在 aerospace 控制器频率下跑紧耦合 VI。OpenVINS（Geneva 2020）是规范实现。

---

## 1 · 架构：predict-update 循环

### 1.1 Kalman 家族

| 滤波器 | 何时 |
|---|---|
| **KF** 线性 | robotics 罕见 |
| **EKF** 非线性 + Jacobian | 大多 VIO |
| **UKF** sigma point | 强非线性 |
| **MSCKF** EKF + 过去位姿窗口、landmark 边际化 | 高速率 VIO |

### 1.2 ⚡ Eureka Moment

> **MSCKF 在状态里存过去*位姿*，但绝不存 landmark —— landmark 先 triangulate，再在 update 前代数投影掉（null-space 边际化）。状态有界，每个 landmark 对窗口内位姿做联合贡献。**

状态是 `O(N_poses)`，不是 `O(N_poses + N_landmarks)`。无论特征数是多少，每个 IMU 样本的处理是常数时间。

### 1.3 信息流

```
IMU 200 Hz ──► predict step → [x: IMU | T_1...T_N]
cam 30 Hz ──► track f → triangulate X_f
            → stack r = [u_i - π(T_i, X_f)]
            → project onto null(H_Xf) → r̃ (no X_f)
            → EKF update with r̃
```

Null-space 投影把 landmark 的 residual 贡献剥掉，同时保留对位姿的几何信息。

---

## 2 · 数学核心：EKF predict-update、MSCKF 边际化

### 📌 Napkin Formula

```
predict:  x̂ = f(x̂),   P = F P Fᵀ + Q
update:   K = P Hᵀ (H P Hᵀ + R)⁻¹    (Kalman gain)
          x̂ ← x̂ + K(z - h(x̂))
          P ← (I - KH) P
```

`x`: 状态（MSCKF 是 IMU + N 个过去位姿）；`P`: 协方差；`F, H`: Jacobian；`Q, R`: 过程 / 量测噪声；`K`: 测量与预测之间的信任比。

### MSCKF 状态向量

```
x = [p_IB, v, q_IG, b_a, b_g | T_1...T_N]
    └── IMU state (15) ──┘ └─ N past poses (6N) ─┘
```

窗口 N ≈ 10–25 → 状态约 165–225 个元素 `UNVERIFIED OpenVINS config`。

### Null-space 边际化

特征 `f` 在 `T_{i_1}...T_{i_k}` 处被观测：

```
r_j ≈ H_T_j δT_j + H_Xf_j δX_f + n_j

Stack:  r = H_T δT + H_Xf δX_f + n
V = null(H_Xfᵀ)
Project: r̃ = Vᵀ r,  H̃ = Vᵀ H_T,  R̃ = Vᵀ R V

⇒ r̃ ≈ H̃ δT + ñ      (X_f gone, geometry preserved)

EKF update with r̃, H̃, R̃.
```

这就是代数核心。residual 块上的线性代数而已。

---

## 3 · 玩具例子：2D EKF 带一次位置观测

状态 `x = [px, py, vx, vy]ᵀ`。Init `x̂₀ = [0, 0, 1, 0]`，`P₀ = diag(0.1, 0.1, 0.01, 0.01)`。常速动力学，Δt = 1 s；`Q = diag(0, 0, 0.01, 0.01)`。

Predict：`x̂₁ = [1, 0, 1, 0]`，`P = F P Fᵀ + Q`。

GPS `z = [1.1, 0.05]`，`R = diag(0.05, 0.05)`，`H = [I₂ | 0₂]`：

```
S = H P Hᵀ + R         K = P Hᵀ S⁻¹
x̂ ← x̂ + K(z - Hx̂)     P ← (I - KH) P
```

结果约为 `[1.05, 0.025, 1.05, 0.025]` —— 测量与预测按信息权重平均。速度协方差通过 P 内的相关性也缩小了，即使速度本身没被观测。

**MSCKF 类比:** 状态 15 + 6N，predict 积分 IMU，update 跨窗口堆 reprojection residual 并做 null-space 投影。

---

## 4 · 工程视角：MSCKF 在 aerial 为什么赢

| 方法 | 状态 | 代价 | Orin Nano? |
|---|---|---|---|
| EKF-SLAM | 15 + 3M | `O(M³)` | 不行，M > 100 卡住 |
| MSCKF | 15 + 6N (N≈20) | `O(N³)` 有界 | ✅ 200 Hz `UNVERIFIED` |
| 滑窗 BA | 6N + 3M | LM ~10 ms/iter `UNVERIFIED` | ✅ 30 Hz |
| Full BA | 增长 | 离线 only | 不行 |

**有界成本**让 MSCKF 成为 sub-10 ms VIO 的规范选择。Skydio / OpenVINS / ASL 都用它。优化在离线精度上赢，在抖动上输。

**为什么在高速率用滤波器:** 确定性成本、吃满 IMU 速率、没有长尾延迟。精度天花板硬（一次线性化 / 更新），但反正帧间是 IMU 主导。

**坑:** 线性化漂 → 迭代 EKF；静止时 bias 不可观 → ZUPT；状态里有 quaternion → error-state form；P 非 PSD → Joseph form 或 sqrt-EKF。

---

## 5 · 能力与失败模式

### 5.1 Hidden Assumptions

- **噪声 Gaussian** —— 很少严格成立；需 chi-square innovation 拒绝。
- **当前均值处线性化准确** —— 大 δ 时失败；要么迭代 EKF，要么减小 Δt。
- **Jacobian 正确** —— 含 quat + bias 的 IMU Jacobian 是代码里最易错的部分；从 OpenVINS 抄。
- **P 保持 PSD** —— Joseph form 或 square-root EKF 防漂。
- **特征足够 overlap** —— 每个 MSCKF 特征在窗口里要 ≥2 个观测。

### 失败特征

| 现象 | 原因 |
|---|---|
| 协方差缩到 0 | 数值下溢；Q 漏了 |
| 直飞时线性漂移 | bias 不可观；需 ZUPT 或激发运动 |
| update 时估计跳变 | R 太自信；chi-sq 校得不对 |
| 高自旋下发散 | 线性化误差；改迭代 EKF 或缩窗口 |

---

## 6 · 比较 & 面试 Tip

| 估计器 | 最适合 |
|---|---|
| EKF | 低维、平滑状态 |
| UKF | 强非线性、无 Jacobian |
| MSCKF | 高速率 VIO（aerial、AR） |
| EKF-SLAM | 小规模 2D / 室内 |
| 滑窗优化 | 在线但接近离线精度的 VIO（VINS-Mono） |
| iSAM2 | factor-graph 平滑 |

> **🎤 Interview Tip.** "Skydio / OpenVINS 为什么用 MSCKF 而不是 BA？" —— 强答："状态有界、更新时间确定。MSCKF 在状态里保留过去位姿的滑窗，观测时通过 null-space 投影把 landmark 边际化掉 —— 每个特征对窗口内位姿做联合贡献，状态不膨胀。每次更新 `O(N³)`，N≈20，Orin 上 < 10 ms。滑窗优化器每 iter 重新线性化（更准）但有不确定的长尾延迟，不适合 200 Hz 控制。" 加分："Jacobian 是 production bug 的高发面 —— 每个 MSCKF 实现都从 OpenVINS 源抄是有原因的。"

---

## Boundary

这篇 primer 只覆盖滤波器数学。如需：

- **滤波器里的 SO(3) error-state** → `./se3_so3_lie_groups_primer.md`
- **JPL quaternion 约定** → `./quaternions_and_rotations.md`
- **喂 predict 的 IMU 积分** → `./imu_preintegration_math.md`
- **OpenVINS 代码架构** → `embodiments/aerial/vio/openvins_dissection.md`
- **VINS-Mono 优化版对照** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`

---

## References

- Kalman, *Trans. ASME* 1960.
- Julier & Uhlmann, *SPIE AeroSense* 1997 (UKF).
- Mourikis & Roumeliotis, *MSCKF for Vision-aided Inertial Nav*, ICRA 2007.
- Geneva et al. *OpenVINS*, ICRA 2020. https://arxiv.org/abs/1910.00298
- Sola, *Quaternion kinematics for error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- OpenVINS: https://github.com/rpng/open_vins · https://docs.openvins.com/

[← Back to Spatial Math](./README.md)
