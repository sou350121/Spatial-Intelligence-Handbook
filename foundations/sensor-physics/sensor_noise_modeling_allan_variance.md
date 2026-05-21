# Sensor 噪声建模与 Allan Variance (Sensor Noise Modeling & Allan Variance)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — Allan deviation 用于 IMU / 相机 / LiDAR / radar / 任何时间序列 sensor
> **核心定位**：每个 sensor datasheet 都写 Allan deviation 而非 RMSE — 因为 RMSE 把五类噪声混在一个数字里，**完全无法回答工程问题**（这个 sensor 在 100 ms 内可信吗？在 100 s 后呢？）

**Status:** v1 — opinionated draft，14-item dissection 范式。数字 `UNVERIFIED`。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) Sensor 输出永远不是真值 + 单一高斯噪声，它是**五类噪声叠加**：white noise / random walk / bias instability / quantization / rate ramp — 每类在不同时间尺度主导。(b) Allan variance（David Allan 1966，原本为铷原子钟设计）是**唯一**能在单张 log-log plot 上把这五类分开识别的工具，因此 sensor industry 25 年共识用 Allan deviation 而非 RMSE 标 spec。(c) 对 sensor 工程师 / SLAM 工程师 / Kalman filter 设计者：理解 Allan plot 就理解了**"sensor 在你的时间尺度上**到底**是什么样子"** — 这是 IMU pre-integration、ZUPT 触发、bias estimator 周期等决策的根。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1966 ── David Allan，"Statistics of Atomic Frequency Standards"
        — 为铷原子钟提出 Allan variance
1981 ── IEEE 519 工业 ADC 噪声分类（white / 1/f / drift）
1997 ── IEEE Std 952-1997 — Fiber Optic Gyro Allan variance 用法成标
2006 ── KVH / Honeywell FOG datasheet 全面用 Allan plot
2015 ── MEMS IMU (BMI / InvenSense) 普及 Allan plot @ datasheet 后页
2018 ── ROS imu_utils / kalibr_allan tools 让学界 / 业界容易跑
2020 ── Allan plot 用于 camera readout noise / LiDAR range noise 分析
        ── 你在这里 (2026) ──
?    ── Auto-tuned EKF noise model from on-device Allan plot？开
```

这个 wedge 卡在"sensor datasheet 与 production filter tuning 之间的桥"上 — 学界论文写 Allan，工程师真去用还得有人翻译。

---

## 1 · 五类噪声 (Noise Classes / Overview)

📌 **Napkin Formula** (X-Ray)：

```
σ_Allan²(τ) = ARW²/τ + BI² + RRW² × τ/3 + ... (其他项)
            ←─ 短时主导 ─→ ←─ 中时 ─→ ←─ 长时 ─→
```

τ 是积分时间。短 τ 由 white noise (ARW) 主导，中 τ 由 bias instability (BI) 主导，长 τ 由 random walk (RRW) 主导。Allan plot 在 log-log 坐标上**斜率**就告诉你哪类主导。

### 1.1 五类噪声详表

| 噪声类型 | Allan plot 斜率 | 物理来源 | 工程影响 |
|---|---|---|---|
| **Quantization noise** | -1 | ADC 量化、digital readout | 极短 τ < 数据率 |
| **Angle / Velocity Random Walk (ARW / VRW)** | **-1/2** | 白噪声积分 | IMU pre-integration 短时累积 |
| **Bias Instability (BI)** | **0 (谷底)** | 1/f flicker, slow drift | 中时尺度（10–1000 s）主导，决定 ZUPT 周期 |
| **Rate Random Walk (RRW)** | **+1/2** | 温度漂、应力释放 | 长时间无 reference 时不可救 |
| **Rate Ramp** | +1 | 系统性 trend | 校准 / 老化 |

⚡ **Eureka Moment.** RMSE 是把这五条曲线**积分到一个数字**，丢掉了"在哪个 τ 上工作"的信息 — 这就是为什么"我的 IMU σ_RMSE = 0.01°/s"无法回答"飞 100 s 累积漂多少"（要 ARW × √100 = 0.1°）也无法回答"长时间静止 bias 漂多少"（要 BI）。**Allan plot 是把噪声分解到时间频域**，五条斜线给了五个独立工程参数。

### 1.2 Allan plot 经典 U 形

```
log σ_Allan
   │
   │\
   │ \ -1 量化 / 1/2 ARW
   │  \
   │   \
   │    \____________ 0 bias instability (谷底)
   │                  \
   │                   \  +1/2 RRW
   │                    \
   │                     \
   └──────────────────────────→ log τ
       µs        s        ks      hr
```

谷底位置 = bias instability；它是**这个 sensor 长时间能给的最低噪声**。

---

## 2 · 数学核心 — Allan variance 定义 (Math Core)

**目标**：从一段长时静止数据估计 sensor 在任意 τ 处的噪声。

**两样本 Allan variance**：

```
σ_A²(τ) = (1 / 2(N-1)) × Σ (ȳ_i+1 - ȳ_i)²
```

其中 ȳ_i 是把数据切成长度 τ 的连续块、计算每块平均值。

**算法**：

```
1. 采集长时间静止数据 y[0..N-1] @ 采样率 f_s
2. 对每个 τ ∈ {2, 4, 8, ..., N/2 / f_s}:
   a. 切块 ȳ_i = mean(y[i·M : (i+1)·M])，其中 M = τ × f_s
   b. 计算相邻差平方和 / (2 × (n_blocks - 1))
   c. σ_A(τ) = √σ_A²(τ)
3. log-log plot σ_A vs τ
4. 从斜率读取 noise class 系数：
   - 斜率 -1/2 → ARW = σ_A × √τ
   - 谷底 → BI ≈ σ_A_min × 0.664 (修正系数)
   - 斜率 +1/2 → RRW = σ_A / √(τ/3)
```

**变量说明**：

| 符号 | 含义 | 典型值（BMI270 MEMS gyro） |
|---|---|---|
| `ARW` | Angle Random Walk | 0.007°/√s `UNVERIFIED` |
| `BI` | Bias Instability | ~10°/hr `UNVERIFIED` |
| `RRW` | Rate Random Walk | ~0.5°/hr/√hr `UNVERIFIED` |

对比 KVH 1750 FOG: ARW ~0.012°/√hr, BI ~0.05°/hr — Allan plot 谷底深 100×，这就是 FOG vs MEMS 的鸿沟。

---

## 3 · Worked Example — 100 秒 IMU 静止数据识别噪声类型

```
Setup: BMI270 IMU @ 200 Hz, 100 秒静止采集 → 20000 sample
轴: Z gyro，单位 °/s
```

**步骤**：

1. 计算 cluster size τ = {0.005, 0.01, 0.02, ..., 50} s（每 τ 取数倍数据）
2. 对每个 τ 切块 + 计算 Allan variance
3. log-log plot：

预期形态（typical MEMS gyro）：

```
τ (s)    σ_A (°/s)    斜率推断
0.005    0.05         (-1/2 ARW 主导)
0.01     0.035        ARW
0.1      0.011        ARW
1.0      0.0035       接近谷底
10       0.003        谷底 (BI)
100      0.005        开始上升 (RRW)
```

**读出**：

- 0.005 s 处 σ_A ≈ 0.05 °/s → ARW = 0.05 × √0.005 = 0.0035 °/√s = `0.21 °/√min`
- 谷底 τ ≈ 10 s, σ_A ≈ 0.003 °/s → BI ≈ 0.003 × 0.664 = `0.002 °/s ≈ 7.2 °/hr`
- τ = 100 s 上升说明 RRW 开始接管，但 100 s 数据太短不可估 RRW 准确

**应用到 SLAM/VIO**：

- VIO pre-integration 窗口典型 < 0.5 s → ARW 主导，每窗口积累 ~0.0035 × √0.5 = 0.0025° 角度漂
- 飞行 30 s 无 visual update → √30 × ARW ≈ 0.019° 累积 + BI 漂 30 × 0.002 = 0.06° → BI 主导
- 飞行 300 s（5 min） → BI × 300 = 0.6° → 严重漂
- **结论**：drone 长航程必须**< 30 s 一次 visual update**，否则 BI 接管不可救

⚡ **结论**：Allan plot 直接给"你的滤波器更新周期应该多短"的答案 — 这是 datasheet RMSE 永远给不了的信息。

---

## 4 · 应用到不同 sensor 类型

**IMU (gyro / accel).** 标准用法。datasheet 必含 Allan plot。BMI270 / ICM-42688 / KVH 1750 / Honeywell HG1700 — 比较谷底（BI）就是比较"长时间能不能信"。

**Camera readout noise.** Camera 静态场景多帧采集，每帧每像素 → Allan plot 识别 read noise (white) + 1/f noise (低频) + thermal drift (RRW)。Sony IMX490 spec 含此类分析。

**LiDAR range noise.** LiDAR 对着固定目标 100k 次测距 → Allan plot 显示 ranging precision (white) + bias instability (温度漂) + 长时 drift (oscillator 漂)。VLP-16 / Hesai AT128 spec 偶尔给。

**Radar phase noise.** Radar 单目标长时观测 → Allan plot 识别 chirp generator 相位噪声、本振漂。NXP / TI 设计 verification 必跑。

**GPS / GNSS.** L1 pseudorange Allan plot — 识别 receiver clock instability vs 多径 vs 大气漂。

**Pressure / barometer.** BMP388 / MS5611 静止采集 → Allan plot 识别 ADC noise + sensor 1/f + 长时温度漂。

**Thermometer.** 任何 ADC 数字传感器 — Allan 框架普适。

⚡ Sensor 工业**所有时间序列 sensor**都该有 Allan plot；只是 IMU community 把它做成必备 spec，其他 sensor 还在用 RMSE / σ 单数字。

---

## 5 · 与 Power Spectral Density (PSD) 对比

PSD 与 Allan variance 是**同一信息的两种表示**（傅里叶对偶）：

| 视角 | 域 | 优势 | 劣势 |
|---|---|---|---|
| **PSD** | 频域 | 频率响应直观 | 1/f noise 在低频发散，难积分 |
| **Allan variance** | 时域积分 | 五类噪声**斜率分明** | 不直接给频域 |

两者**信息等价**。但 Allan 在工程上更好用，因为：

1. log-log 斜率 -1, -1/2, 0, +1/2, +1 都是整数 → 直觉识别
2. 1/f noise 在 Allan 上**收敛**到谷底而非发散
3. 与 SLAM / Kalman filter 的"时间累积"思路同构

---

## 6 · Failure modes — Allan plot 的常见误用

**数据太短.** 100 s 数据不能估 1000 s 处的 RRW；rule of thumb：要看 τ_max，数据长 ≥ 10 × τ_max。

**非静止数据.** Allan variance 假设静止 sensor + 平稳过程。drone 飞行中振动 / 温度变化让 Allan plot 失效。**必须**实验室静止条件采集。

**温度不稳定.** Sensor 周围温度漂会被读成 RRW，混淆真实噪声特性。Allan 实验需 ±0.5°C 稳定环境。

**采样率不足.** ARW 估计需要 τ < Nyquist 限。200 Hz 采样不能估 τ < 0.005 s 的噪声。

**振动 / 共振.** 实验台振动让 Allan plot 上出现 spike → 误判为 BI 或 RRW。需做隔振。

### Hidden Assumptions

- **平稳过程.** Sensor 噪声统计性质不随时间变 — 静止+恒温下成立，飞行 / 移动场景**不成立**。
- **噪声相互独立.** 五类噪声叠加假设独立，实际可能耦合（如温度同时驱动 BI 和 RRW）。
- **采样率足够 Nyquist 之上.** 否则 alias 混进 Allan 估计。
- **数据足够长.** 至少 10× 你想估的 τ。
- **没有外部扰动.** 桌面震动、远处地铁、空调启停都污染数据。
- **传感器线性区.** 饱和 / cutoff 让 Allan 公式失效。

---

## 7 · 与 SLAM / VIO / EKF 设计的关系 + Interview Tip

**EKF Q 矩阵** 中 sensor noise variance 不该用 datasheet RMSE，而该用 **τ = filter step 处的 Allan σ²**。例如 VIO 10 ms 步长 → 用 Allan @ τ=0.01s 的 σ² 设 gyro Q。

**Bias estimation 周期** = Allan 谷底 τ。BMI270 谷底 ~10 s → EKF 应该 ~10 s 更新一次 gyro bias estimate；KVH FOG 谷底 ~1000 s → 更新频率可以更慢。

**ZUPT (Zero Velocity Update) 周期** = bias instability 到 ~5% 工作误差所需时间。短 BI → 必须更频繁 ZUPT；长 BI → 可以走更远。

**🎙️ Interview Tip.** 被问"为什么 sensor datasheet 用 Allan deviation 不用 RMSE"？— 一句话：**RMSE 把所有时间尺度的噪声叠成一个数字，无法回答"我的 filter 在 100 ms 步长时该用什么 Q"或"飞 100 s 累积漂多少"；Allan plot 把 ARW / BI / RRW 在 log-log 斜率上分开，直接给五个独立工程参数，是 IMU / FOG community 25 年的共识标准**。

---

## 8 · For the reader (per-persona)

- **IMU / SLAM engineer** — 必看 datasheet Allan plot；用 kalibr_allan / imu_utils 跑自己 sensor。EKF Q 矩阵从 Allan @ filter step 取。
- **Drone engineer** — Allan 谷底 = bias estimator 更新周期 = ZUPT 时机。MEMS ~10 s vs FOG ~1000 s 决定飞行 envelope。
- **AD engineer** — auto-grade IMU + Allan 验证是 ASPICE / ISO 26262 一部分；老化测试看 RRW 长时演化。
- **Sensor 设计者 / 新品评估** — 拿任意时间序列 sensor 跑 Allan plot；它比 datasheet 单数字更告诉你"这个 sensor 在我应用上是什么样子"。
- **AGV engineer** — bias instability 在 wheel odometry IMU 融合中是关键；Allan 决定 dead-reckoning 不退化的最大距离。

---

## References

- Allan, D.W. (1966) "Statistics of Atomic Frequency Standards", Proc. IEEE 54(2)
- IEEE Std 952-1997 "Specification Format Guide and Test Procedure for Single-Axis Interferometric FOGs"
- IEEE Std 1554-2005 — Inertial Sensor Terminology
- Woodman, O. (2007) "An introduction to inertial navigation" (Cambridge tech report) — 经典教程
- KVH 1750 FOG / Honeywell HG1700 / Bosch BMI270 / InvenSense ICM-42688 datasheets — 全部 `UNVERIFIED, no DOI`
- kalibr_allan / imu_utils GitHub — open-source Allan tools
- ROS REP 145 — IMU calibration recommendation

## Boundary

- `foundations/sensor-physics/imu_physics_and_noise_model.md` — IMU 专用噪声深度（这文是其姊妹，覆盖所有 sensor）
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — LiDAR ranging noise 应用 Allan 框架
- `foundations/sensor-physics/mmwave_radar_physics_for_ad.md` — radar 相位噪声 Allan 分析
- `foundations/sensor-physics/event_camera_dvs_physics.md` — event camera 时间分辨率与 Allan 的极端对照
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — IMU FOG vs MEMS Allan 决定的 BOM 取舍
- `deployment/hardware-selection/` — Allan-based EKF tuning workflow

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./README.md)
