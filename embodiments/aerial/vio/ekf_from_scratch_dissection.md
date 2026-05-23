# 从零手写 EKF — 15-state 与 21-state Augmented (EKF from Scratch — 15-state & 21-state Augmented Dissection)

> **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主講) L8-L9 + Project 3 (proj3phase1 `ekf` + proj3phase2 `aug_ekf` packages)
> **License**: 原始 slide 与代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本 dissection 为改写 + 补充教材，依 BSD 3-Clause 保留版权声明
> **公开参考**: Kalman 1960 (orig); Mourikis & Roumeliotis 2007 ICRA (MSCKF); OpenVINS 2020; Thrun, Burgard, Fox *Probabilistic Robotics* (2005)
> **核心定位**：用 HKUST 飞机课的 proj3 骨架，把一个 15-state EKF 与一个 21-state augmented EKF **从公式到 Jacobian 维度到 ROS 回调**完整走一遍——这是学完 VINS-Mono / OpenVINS 之后，第一次真正"自己写一个能上飞机的 EKF"的指南。

**Status:** v1 draft (2026-05-22). 教学型 dissection，与 `openvins_dissection.md`（库拆解）互补。Wedge tier 🔧 (operable)。数值标 `UNVERIFIED` 除非来源是 HKUST proj3 default config。
**TL;DR:** OpenVINS / MSCKF dissection 讲"一个写好的库怎么用"；本文讲"拿到一台陌生飞机 + IMU + 相机/marker，怎么自己写 200 行 Eigen 跑起来"。两个关键设计：(1) **IMU bias 当 state**（非 calibration 常量），否则飞行中 bias 漂把姿态拉爆；(2) **augmented state** 处理 stereo VO 的相对 pose（keyframe 间），避免 relative measurement 错当 global。HKUST proj3phase1 = IMU + PnP 的 15-state；phase2 = IMU + PnP + stereo VO 的 21-state（多 6 维是 keyframe pose copy）。

---

### X-Ray 开场（非专家友好）

(a) 一个真飞机的状态估计器，光靠 IMU 会漂、光靠相机 30 Hz 太慢；EKF 把两者按"高频预测 + 低频校正"融合。 (b) **从零写**意味着你得自己定 state 是哪 15 维、自己推 process Jacobian `F` 和 measurement Jacobian `H`、自己决定 noise covariance 怎么调；HKUST proj3 phase1/2 就是教你完成这件事的最干净骨架（ROS 回调 + Eigen，约 250 行）。 (c) 对 spatial / 具身工程师：库（OpenVINS、msf）能让你 demo，但当 IMU 噪声不像、bias 上电漂 0.3 rad/s、yaw 在悬停时不可观时，**只有自己写过 EKF 的人能 debug**——这是商用无人机自治组的入职门票。

### 📍 研究全景时间线

```
Kalman 1960 (linear) ─► Extended Kalman 1970s (NASA/Apollo) ─► UKF 1997 (Julier/Uhlmann) ─► MSCKF 2007 (Mourikis) ─► VINS-Mono 2018 (优化派) ─► OpenVINS 2020 (滤波派 ref)
        │                          │                                                      │                                 │
        │                          └─► 工业界（航空 / 导弹）成为默认            ★ HKUST ELEC5660 教学版（本文聚焦）           └─► 商用无人机栈延续 MSCKF
        └─► "线性高斯下 BLUE 最优"
```

HKUST proj3 的 15/21-state EKF 不是研究产物，而是把工业界 50 年的 EKF 配方剪裁成"一学期能写完、能在 DJI M100 上飞起来"的最小可教学单元——它的价值在**最短路径让学生触到所有关键工程决策**，而非任何 SOTA 数字。

---

## 1 · 核心架构：为什么 from-scratch EKF 值得学

### 1.1 与"读库"型 dissection 的对比

| 维度 | OpenVINS | VINS-Mono | **本文 (from-scratch)** |
|---|---|---|---|
| 目标 | 读懂生产级库 | 读懂优化派 | 自己写最小 EKF |
| state | 15 + N×6 clones | 滑窗 11-frame | 15 / 21 |
| features | null-space project | 在 state | 不在 state，PnP/VO 当 6-DoF 量测 |
| 代码量 | ~30K LOC | ~10K LOC | **~250 行** |

**Eureka**（§1.2 详述）：IMU bias 当 state（而非地面校准后常量）——EKF 飞机闭环的前提。

### 1.2 关键机制 (Key Mechanism) ⚡

⚡ **Eureka Moment**：**"Bias 不是常量，是会随机游走的 state"**。地面静止校准后写死 `b_a` / `b_g`，飞 30 秒姿态发散——MEMS bias 随温度 / 震动 / 上电次数漂。把 6 维 bias 塞进 state（vision update 时和 pos/ori 一起估），是飞机闭环的 enabler。HKUST 15-state 最后 6 维就是 `[b_g; b_a]`。

第二个 Eureka：**"EKF 在当前 best estimate 处线性化"**——每次 predict/update 重算 `F = ∂f/∂x|_x̂`、`H = ∂h/∂x|_x̂`，不像 KF 用固定矩阵；代价是剧烈机动时一阶展开误差大→发散 (§7)。

### 1.3 信息流 / 架构图

```
IMU 200 Hz ──► predict (modelF, jacobiFx):  x̂←f(x̂,u); P←FPFᵀ+VQVᵀ
                       │
Marker PnP 30 Hz ────► update G1 (modelG1):  K=PHᵀ(HPHᵀ+R)⁻¹
Stereo VO ~10 Hz ────► update G2 (modelG2)  ← phase2 only (relative pose)
                       │                     x←x̂+K(z-h); P←(I-KH)P
                       ▼
                  融合 odom @ 200 Hz
```

ROS 层：每个 sensor 一个 callback，往同一 `deque<AugState>` 按 stamp 插入。`processNewState()` 处理 **out-of-order**（vision 比 IMU 晚几十 ms），插回后从插入点重新 propagate。

---

## 2 · 数学核心：从 Bayes 到 EKF 五行公式

> 📌 **Napkin Formula**：`x_{k+1} = f(x_k, u_k) + n_w`；`z_k = h(x_k) + n_v`；EKF 就是把 Bayes 滤波在 `x̂` 处一阶展开后落到 5 行：predict (x̂, P̂)、innovate (y, S)、gain (K)、update (x, P)。**state 长什么样、`f/h` 长什么样、Jacobian 维度对不对**——只要这三件事对，EKF 就能跑。

### 2.1 15-state state vector (phase1)

```
x = [ p (3)         # position in world frame (NWU)
    ; θ (3)         # ZXY Euler (phi, theta, psi) — 见 §9 gotcha
    ; v (3)         # velocity in world frame
    ; b_g (3)       # gyro bias
    ; b_a (3) ]     # accel bias
```

> **符号约定**：与 HKUST proj3 `ekf_model.h` 一致 — `Vec15 x` 索引 `0:2 = p`, `3:5 = θ`, `6:8 = v`, `9:11 = b_g`, `12:14 = b_a`。Euler 用 **ZXY** 不是标准 ZYX，因为 NWU body 下 pitch-around-Y 在 hover 接近奇点时 ZXY 数值更稳。`UNVERIFIED` 是否其他选择更好——proj3 历年用 ZXY。

### 2.2 Process model (IMU motion + bias random walk)

IMU 给 `u = [ω_m; a_m]`（机体系 gyro / accel 量测），含 bias 与 white noise：

```
ω_m = ω + b_g + n_g          # measured gyro
a_m = R_wbᵀ(a_w + g_w) + b_a + n_a   # measured accel (gravity included)
```

连续时间 state derivative `ẋ = f(x, u, n)`：

```
ṗ   = v
θ̇   = G(θ)⁻¹ · (ω_m - b_g - n_g)        # Euler rate 不是 body rate
v̇   = g_w + R_wb(θ) · (a_m - b_a - n_a)  # 世界系加速度
ḃ_g = n_{bg}                              # bias 随机游走
ḃ_a = n_{ba}
```

噪声 `n = [n_g; n_a; n_{bg}; n_{ba}] ∈ ℝ^12`，所以 `Qt_` 是 `12×12`（HKUST 默认对角，gyro / accel noise + bias walk）。

### 2.3 EKF 五行（离散化后）

```
# Predict (每次 IMU)
x̂_k = x_{k-1} + Δt · f(x_{k-1}, u_k, 0)
F_k = I + Δt · ∂f/∂x |_{x_{k-1}, u_k}        # 15×15
V_k =     Δt · ∂f/∂n |_{x_{k-1}, u_k}        # 15×12
P̂_k = F_k · P_{k-1} · F_kᵀ + V_k · Q · V_kᵀ

# Update (每次 vision)
y_k = z_k - h(x̂_k)                            # innovation, 6×1
H_k = ∂h/∂x |_{x̂_k}                           # 6×15 (phase1) / 6×21 (phase2)
S_k = H_k · P̂_k · H_kᵀ + R                    # 6×6
K_k = P̂_k · H_kᵀ · S_k⁻¹                      # 15×6 or 21×6
x_k = x̂_k + K_k · y_k
P_k = (I - K_k · H_k) · P̂_k                  # Joseph form 更稳但 HKUST 用简单式
```

> **直觉**：predict 把 covariance 沿着 `F` 拉长（state 不确定性增长 + 注入 process noise）；update 把它压扁（K 是 "信不信 measurement" 的权重——measurement noise R 大就少信、predict covariance 大就多信）。

---

## 3 · 带数字走一遍：IMU 1-step + PnP 1-update

> 简化 1D 玩具例子，对齐 HKUST `modelF` / `jacobiFx` 结构；目的是看清 **Jacobian 维度怎么对、哪些块是 ∂R/∂θ**。完整 3D 推导见 L9 slide 20-30。

**Setup**：`x = [p; v; b_a] ∈ ℝ^3`、`Δt = 0.005 s`、`x_{k-1} = [0; 0; 0.1]`、`a_m = 1.0`、`P_{k-1} = diag(0.01, 0.01, 0.0001)`。

**Predict**：

```
f(x, u, 0) = [v ; a_m - b_a ; 0] = [0; 0.9; 0]
x̂_k = x_{k-1} + Δt·f = [0; 0.0045; 0.1]

∂f/∂x = [[0,1,0],[0,0,-1],[0,0,0]]       F = I + Δt·∂f/∂x
∂f/∂n = [[0,0],[-1,0],[0,1]]              V = Δt·∂f/∂n
P̂ = F P Fᵀ + V Q Vᵀ ≈ diag(0.010, 0.0100, 0.0001)   (含 v-b_a 非对角耦合)
```

**Update (PnP 量测 p)**：`z = 0.001`、`R = 0.001`、`H = [1, 0, 0]`。

```
y = 0.001 ; S = H P̂ Hᵀ + R = 0.011 ; K = P̂Hᵀ/S ≈ [0.91; 0.1; 0.01]ᵀ
x_k = x̂ + K·y → 主要修 p，但 v / b_a 经 cross-covariance 也被微调
```

**Takeaway**：position 量测**同时修了 velocity 和 bias**，因为 `P̂` 的非对角项耦合了它们——这就是 IMU bias 能被 vision update 估出来的原因。HKUST `jacobiFx` 全 15×15 Jacobian 关键非零块：

```
              p     θ     v     b_g   b_a
         p [  I    0     ΔtI   0     0   ]
         θ [  0    A     0    -ΔtG⁻¹ 0   ]   A = I + Δt·∂(G⁻¹ω̂)/∂θ
   F  =  v [  0    B     I     0    -ΔtR ]   B = Δt·∂(R(a_m-b_a))/∂θ
        b_g[  0    0     0     I     0   ]
        b_a[  0    0     0     0     I   ]
```

写出这个矩阵，并对 `A`、`B` 手推 `∂R/∂θ`（Euler 角导数链式法则），是 proj3phase1 的核心作业。`B` 块是 EKF 能从 vision update 反推 accel bias 的"通路"。

---

## 4 · 21-state Augmented EKF (phase2)

### 4.1 为什么 stereo VO 不能直接当 PnP

PnP 给 **global 6-DoF pose**（marker 在 world 已知），直接 `h(x) = [p; θ]`。Stereo VO 给 **relative pose**——当前帧到上一 keyframe 的 `T_rel`。当 global 用就会把 keyframe pose error 永久注入，每次切 kf 累一次，几分钟废。

### 4.2 21-state 设计

```
x_aug = [ x_15 (origin) ; p_kf (3) ; θ_kf (3) ]
                          # keyframe pose snapshot
```

HKUST `AugState.mean` 注释：`x15:17 ~ keyframe x,y,z; x18:20 ~ keyframe phi theta psi`。

VO 量测 `modelG2(x_21, v)`：

```
z_vo = [ R_kfᵀ (p - p_kf) ;          # 相对位置
         logSO3(R_kfᵀ · R) ]          # 相对旋转
```

`jacobiG2x ∈ ℝ^{6×21}`，右半 6 列对 keyframe pose 的 Jacobian 非零——这是 augmented state 存在的全部理由。

### 4.3 Keyframe 切换与重映射

```
M_a (21×15): copy 当前 [p; θ] 到 augmented slot   (keyframe 选定)
M_r (15×21): drop augmented slot                  (切下一个 keyframe)
```

**Eureka**：augmented state 不是"多估 6 个数"，而是**把 keyframe 当时 pose 冻进 state，让其 covariance 跟着所有后续 update 一起改善**——stochastic cloning (Roumeliotis 2002) 的最小教学版，MSCKF 的祖宗。

### 4.4 Out-of-order：deque + repropagate

ROS 接收顺序：IMU、IMU、IMU、（VO stamp 50ms 前）、IMU...。HKUST 用 `deque<AugState>` 按 `time_stamp` 排序：

```
processNewState():
  1) insertNewState  # 按 timestamp 插回
  2) repropagate     # 从插入点重 propagate 所有后续
  3) removeOldState  # 队列太长 drop head
```

OpenVINS 同款简化版——OpenVINS 用 clones、HKUST 用 augmented snapshot，解决同一 latency 问题。

---

## 5 · 工程视角：快慢路径 / 真机决策

| 决策 | 选择 | 理由 |
|---|---|---|
| **prediction** | IMU 200 Hz | 控制环要高频；vision 太慢且非等间隔 |
| **update** | PnP 30 Hz + VO ~10 Hz | 提供 absolute anchor；IMU 自己不可观 |
| **state rep** | Euler ZXY | hover 不奇异；与 DJI SDK 一致；小角下 `G⁻¹ ≈ I` |
| **R (PnP)** | ~0.1 m / 0.1 rad | 远距 marker 噪声大 |
| **R (VO)** | ~0.01 m / 0.01 rad | 短程相对量测精 |
| **Q** | 对角 ~1e-2 (acc/gyro), 1e-5 (bias walk) | datasheet σ×√BW 量级；调大→信 vision、调小→信 IMU |
| **初始化** | 第一个 PnP 拍 yaw/pos；前 1s 静止估 bias | yaw 纯 IMU 不可观 |
| **reject** | innovation `‖y‖² > χ²_{0.99}` gating | 坏 PnP 会拉爆 state |

**为什么 IMU 做 prediction**：control loop 要 200+ Hz；vision pipeline 自己 30-100 ms 延迟。EKF "先 IMU 推到现在、vision 来用滞后量测修过去"，把延迟摊到 covariance 上。

---

## 6 · 隐含假设 (Hidden Assumptions)

EKF 能跑的前提（不成立时直接发散）：

1. **IMU 噪声 white Gaussian + zero-mean** — 实际 MEMS 有 1/f、温度漂移、震动耦合；Q 调保守补偿
2. **Bias 是 random walk** — 实际 bias 含低频温度漂移，random walk 只在 ~1 min 量级对
3. **小姿态扰动下线性化 OK** — 30°/s 缓飞行 OK；> 200°/s 急机动需 UKF / iterated EKF
4. **量测模型可微** — EKF 把 PnP/VO 当各向同性高斯量测，忽略 marker 边缘视场的方向性
5. **time-sync 完美** — IMU 与 cam < 1ms；硬件 trigger 不到位时 RMSE 上升数倍 `UNVERIFIED`
6. **gravity 方向已知** — world z 对齐重力，初始化静止估
7. **state 高斯近似** — 大不确定下后验非高斯，EKF 强制塌成高斯会丢信息（粒子滤波解此，L9 后半）

---

## 7 · 失败模式

| 失败 | 触发条件 | 现象 | 缓解 |
|---|---|---|---|
| **Large maneuver divergence** | 急转/急加速 → Δt 内非线性大 | 姿态 NaN、P 爆炸 | 降低 IMU prediction Δt、用 iterated EKF |
| **P explodes** | Q/R 调错 + 长时间无 update | 监视 `trace(P)` > 阈值 → reset | innovation gating + 周期性 reset |
| **Yaw unobservability** | 长时间 hover + 无 marker | yaw drift 几度/分钟 | 加 magnetometer 或保 marker 在视场 |
| **Bias never excited** | 长时间 hover、加速度恒等于 g | accel bias 估不出来（state 不可观） | 飞 8 字让 IMU 各方向 excite |
| **Lost marker / VO** | 离开 marker 视场 | 退化为 IMU dead-reckoning，几秒就漂 | 多 marker 备份；切 keyframe 时 covariance 注入 |
| **Vision outlier** | 一个错的 PnP 解 | 一帧把 position 拉跳几米 | χ² gating + medium-window history check |
| **Out-of-order with 大 gap** | VO 比 IMU 晚 200+ ms | repropagate 太多 state 算不完 | drop 该量测或缩短 history |

### 7.y · GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：from-scratch EKF 本身不是 GitHub repo，但 atlas 4 仓（VINS-Mono / VINS-Fusion / OpenVINS / DROID-SLAM）的失败模式**几乎逐条对应 §7 失败表**：Init 卡死 / 反复 restart（[VINS-Mono #475](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/475)·[#473](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/473) 初始 quaternion (0,1,0,0)）= §1 静止开机 / accel 方差不足；stationary drift（[VINS-Mono #462](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/462)·[#469](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/469)）= §7 "Bias never excited"；OpenVINS filter divergence after init（[#540](https://github.com/rpng/open_vins/issues/540) "extremely large IMU values"）= §7 "Large maneuver divergence"；OpenVINS Orin Nano segfault（[#514](https://github.com/rpng/open_vins/issues/514) YAML 与 IMU 采样率不匹配）= §9 真机 production gotchas；VINS-Fusion Ceres 2.2.0 数值不稳（[#246](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/246)·[#275](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/275)）= §7 "P explodes"；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：本 dissection 在 atlas 中作为 zone "选栈不看 EuRoC 名次"的**教学锚**被讨论，未有专属失败块；atlas Cross-Cutting 总结：**init 失败 / IMU bias 时间同步 / 单目 scale 收敛慢 / ROS 2 半成品 / 嵌入式 SoC 不够 / 自录数据 ≠ EuRoC** 六条共性 — 与 §6 Hidden Assumptions 七条假设互为镜像；Skydio 商用栈把这些外化为 "pre-flight wiggle"，学界跑 EuRoC 隐式满足、迁真机即暴露，正是本文 from-scratch EKF 路径的价值所在。

---

## 8 · 与 MSCKF / OpenVINS 对比

| 维度 | 本文 21-state aug | MSCKF 2007 | OpenVINS 2020 | VINS-Mono |
|---|---|---|---|---|
| **state** | 15 + 6 (1 keyframe) | 15 + N×6 clones | 15 + N×6 + 标定 | 滑窗 ~99 dim |
| **feature** | 不在 state | null-space project | 同 MSCKF | 优化变量 |
| **量测** | 6-DoF PnP + 6-DoF relative VO | 单 feature 像素 | 同 MSCKF + 多相机 | 同 VINS-Mono |
| **何时用** | 教学 / 自家 sensor | 单核 CPU 商用 | 工业参考 | 学界 SOTA |
| **从零写难度** | **一学期能写** | 1-2 周 | 不可能 | 不可能 |

**Eureka link**：HKUST 的 augmented state 是 MSCKF stochastic cloning 的 "1-clone 简化版"——把 N 个 clones 简化为单个 keyframe snapshot。这个 simplification 牺牲了多观测一致性（MSCKF 一个 feature 跨 N 帧的约束），但换来代码量从 3K 行降到 250 行、能在一学期内手推完毕。

**面试 Tip**：被问到 "为什么不直接用滑窗优化" 时，答 **"single-core latency budget on 2-4W SoC"**——MSCKF 谱系单核 < 5ms / frame `UNVERIFIED`、VINS-Fusion 需要 2+ 核同等精度。无人机的 SoC 还要跑 attitude control / ESC / radio / video encoding，CPU 配额是工程上限。

---

## 9 · 真机 production gotchas

1. **IMU frame 对齐** — HKUST 用 **NWU**、PX4 用 **FRD**、ROS REP-103 是 ENU。换 IMU 第一件事是 `cout << R_imu_body` 验证
2. **Cam-IMU 外参** — proj3 默认 `R_cam = quat(0,1,0,0)`, `t = [0.05, 0.05, 0]` m；换相机要 Kalibr 重标——5mm/1° 错就产生 systematic drift
3. **Time-sync** — 软件 sync 5-50 ms 不确定；硬件 trigger 是商用方案。回调里用 `msg->header.stamp` 不是接收时间
4. **Bias 上电校准 + 飞行 estimate** — 起飞前静止 1-2s 平均 gyro 估 `b_g` 初值；飞行中 EKF 持续 update。两步缺一不可
5. **Yaw initialization** — 第一个 PnP 之前 yaw 不可观；proj3 假设第一个 marker 给 yaw
6. **Euler 奇点** — ZXY 在 `phi = ±π/2` 奇异；做特技要换四元数 / Lie group
7. **NaN watchdog** — `publishFusedOdom` 检查 `mean.head(3).norm() > 20` 直接 reject，避免下游 control 收 NaN 炸机
8. **Covariance reset** — 数值累积 P 失对称性；定期 `P = 0.5*(P+Pᵀ)` + 检查 eigenvalues > 0

---

## 10 · References & Cross-refs

**教材出处**：
- HKUST ELEC5660 L8（Bayes filter / Kalman intro）、L9（EKF + particle filter）— [HKUST-Aerial-Robotics/HKUST-ELEC5660](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics)
- Project 3 phase 1 (`ekf/`) 与 phase 2 (`aug_ekf/`) reference scaffold

**经典公开文献**：Kalman 1960 (orig); Mourikis & Roumeliotis 2007 ICRA (MSCKF); Roumeliotis & Burdick 2002 ICRA (stochastic cloning); Geneva et al. *OpenVINS* ICRA 2020 [arXiv 1910.00298](https://arxiv.org/abs/1910.00298); Thrun/Burgard/Fox *Probabilistic Robotics* 2005 (Ch.3)

**Cross-refs**：
- 上游 IMU 数学：[../../../foundations/spatial-math/imu_preintegration_math.md](../../../foundations/spatial-math/imu_preintegration_math.md)
- 库版本（MSCKF 工业放大）：[openvins_dissection.md](./openvins_dissection.md)
- 优化派对照：[vins_mono_fusion_dissection.md](./vins_mono_fusion_dissection.md)
- 失败模式实战：[github_failure_atlas.md](./github_failure_atlas.md)

**与 openvins_dissection 分工**：本文 = tutorial（从 state 设计到 Jacobian 到 ROS 回调，手把手写一个 EKF）；OpenVINS dissection = 库拆解（生产级 MSCKF 怎么用、FEJ 怎么修 observability、何时选 OpenVINS vs VINS-Fusion）。目标读者：本文给"刚学完贝叶斯滤波、要自己写 EKF 的工程师"，那篇给"已在跑 VIO、想理解工业选型的工程师"。

---

[← Back to VIO zone](./overview.md)
