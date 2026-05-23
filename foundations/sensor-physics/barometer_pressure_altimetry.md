# Barometer Pressure Altimetry (气压计高度测量物理 — barometric formula / QNH / 温漂 / 室内电梯)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — barometric formula / MEMS pressure sensor / drone altitude EKF input
> **核心定位**：drone 高度估计的"沉默主力" — GNSS 在 vertical 上误差 ~3× horizontal，barometer 是&lt;10s 时间尺度上**唯一**可信的 vertical 信号；但被温度 / 风 / HVAC 三种噪声严重污染，工程账学界几乎从不写

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字需 datasheet 交叉核对。
**Wedge tier:** sensor-physics expansion（E 桶 drone stack 第 1 篇）

### X-Ray opening

每个 drone（消费 / 工业 / 军用）都有 barometer，但学界 SLAM / VIO 综述几乎从不提它 — 因为它的物理太"古老"（17 世纪 Torricelli）。然而在 drone EKF 里它扛 vertical channel 的主重：GNSS vertical 精度 ~3× horizontal（3D RTK 也是），visual VO 的 z-axis 在 monocular 下是 scale-ambiguous，IMU accel 双积分秒级就爆。**Barometer 是 1–60s 时间尺度上 vertical 唯一可信信号**。代价是它被温度 / 风扰 / HVAC / 电梯井气压脉冲多重污染 — 这些 failure mode 不在 datasheet 上，飞过才知道。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1643 ── Torricelli 水银气压计 ── 大气压物理基础
1851 ── Bourdon tube 机械式高度计 ── 早期航空仪表
1990s ── MEMS piezoresistive pressure die (Honeywell, Sensirion)
2010 ── Bosch BMP085 ── 第一颗消费级 MEMS 气压计 (~$2)
2014 ── Bosch BMP280 ── 智能手机普及（iPhone 6 内嵌）
2018 ── Bosch BMP388 ── drone 优化，~10 cm 分辨率 `UNVERIFIED`
2020 ── TE MS5611 ── 高精度工业级
2022 ── Infineon DPS310 / DPS422 ── 24-bit ADC，drone L4 标配
202? ── ?  下一波：sensor fusion on-die（baro + 温 + 湿，单 SiP）
```

---

## 1 · barometric formula — 大气压随高度的物理

📌 **Napkin Formula**：`P(h) = P₀ · exp(-M·g·h / (R·T))`，其中 M=空气摩尔质量 0.02897 kg/mol，g=9.81 m/s²，R=8.314，T=温度(K)。**近地 1 hPa ≈ 8.4 m altitude**（at sea level, 15°C），这是工程界用的快速换算。

**(a) 等温大气近似.** 上述公式假定 T 不随高度变。低空（&lt;2 km）误差 &lt;2%。高空必须用 ICAO 标准大气模型（lapse rate 6.5 K/km in troposphere）。

**(b) 实际 sensor 量测物理.** MEMS piezoresistive die — 一片硅膜片在压力下应变，膜下方掺杂电阻形成 Wheatstone 桥；压差 → 应变 → 电阻变化 → 电压。Sensitivity ~25 µV/V/Pa typical。24-bit ΔΣ ADC 把噪声压到 1–2 Pa rms → ~10–20 cm altitude resolution `UNVERIFIED`。

**(c) 温度补偿.** Si piezoresistor 温度系数 ~0.1%/°C。Sensor 内嵌温度传感器 + 工厂校准多项式（typically 2 阶 in T × 2 阶 in P）。残余温漂 ~5 Pa over -40 to +85°C → ~40 cm altitude error。

⚡ **Eureka Moment.** Barometer 测的不是 altitude — 是**大气压**。altitude 是个**推断**，依赖一组关于大气状态的假设：温度、QNH 校准基准、风扰、HVAC 室内气流。这些假设都不稳定，所以 barometer 是 **vertical EKF 的高频信号**，不是 ground truth。

---

## 2 · 典型 sensor 对比

| Sensor | Vendor | Resolution `UNVERIFIED` | Noise (1 Hz) | 功耗 | 价格 | 典型应用 |
|---|---|---|---|---|---|---|
| **BMP180** | Bosch | ~25 cm | ~6 Pa | 5 µA | $1 | 老款 / 极低端 |
| **BMP280** | Bosch | ~12 cm | ~3 Pa | 2.7 µA | $1.5 | 手机 / IoT |
| **BMP388** | Bosch | ~8 cm | ~2 Pa | 3.4 µA | $3 | drone 标配 (PX4 推荐) |
| **MS5611** | TE Connectivity | ~10 cm | ~1.2 Pa | 1 µA | $7 | 工业 / 高精度 drone |
| **MS5837-30BA** | TE Connectivity | 同上 + 防水 | ~3 Pa | 1 µA | $25 | 水下 / 海洋 |
| **DPS310** | Infineon | ~5 cm | ~0.6 Pa | 1.7 µA | $4 | drone L4 / 工业 |
| **DPS422** | Infineon | ~3 cm | ~0.4 Pa | 1.7 µA | $6 | 最高精度消费级 |
| **LPS22HH** | ST | ~7 cm | ~1.5 Pa | 3 µA | $2.5 | 手机 / wearable |

drone 工程经验：BMP388 是 PX4 / ArduPilot 默认 — 性价比最高。DPS310 在工业 mapping drone 上更常见。MS5611 是 academic VIO 论文老朋友（VINS-Fusion 上的实验通常配它）。

---

## 3 · QNH / QFE / QNE — 三种 altimetry 基准

航空通用三种基准，drone 工程必须区分否则会撞高度限制：

| 基准 | 定义 | 显示 | 用途 |
|---|---|---|---|
| **QNH** | 站点海平面校正气压 | altitude above MSL（海平面） | 飞行规划 / 限高 |
| **QFE** | 站点局部气压 | height AGL（地面以上） | 起降 / 室内 |
| **QNE** | ISA 标准 1013.25 hPa | flight level (FL) | >FL180 巡航高度 |

**drone 实战**：起飞前**清零**（QFE） — 自动把当前位置定义为 0 m AGL。室外飞 30 m 限高 = 30 m above takeoff point，与海拔无关。**问题**：起飞点海拔 1000 m vs 0 m，温度 / 气压基线差 → 同样 30 m AGL 的 sensor reading 不一样，必须用动态校准。

⚡ **关键**：QNH 在天气变化时会漂 — 一个低气压锋面经过 → 海平面气压降 10 hPa → 同样 altitude 的 sensor reading 错 84 m。**所以 drone EKF 必须把 barometer bias 作为 state 持续估计**，不能信"开机时的零点"。

---

## 4 · Worked example — 1 hPa ≈ 8.4 m 推导

```
Setup:  sea level, T = 288.15 K (15°C ISA)
        P₀ = 101325 Pa
        M = 0.02897 kg/mol, g = 9.81, R = 8.314
```

`dP/dh = -M·g·P/(R·T)` → at sea level，`dP/dh ≈ -101325 × 0.02897 × 9.81 / (8.314 × 288.15) ≈ -11.9 Pa/m`

即 **1 m ≈ 11.9 Pa**，或 **1 hPa = 100 Pa ≈ 8.4 m** — 这是航空 / drone 工程界的快速换算。

**实战推论**：BMP388 noise 2 Pa rms → **altitude noise 约 17 cm rms** at 1 Hz output。drone EKF 通常按 1–5 Pa 测量 σ 喂进 update step。

**温度修正**：高原 4000 m (T~265 K)，同样 1 hPa → ~7.7 m（不是 8.4 m）— 5% 差异。MAVLink protocol 让 sensor 报 raw P + T，airdata 库做转换。

---

## 5 · drone 上的具体 failure modes

**(a) Prop wash / 风扰.** drone 螺旋桨产生向下气流 → 机身下方相对低压 → barometer 报"在下降"。Hover 时 ~5–10 Pa pulse `UNVERIFIED`，对应 50–80 cm 假阶跃。**对策**：sensor 装顶部 / 内部 + 多孔 PCB 屏蔽；EKF 低通滤波 (~1 Hz cutoff)。

**(b) 翻转 / 急转.** 机身姿态变化让 sensor 入口相对气流方向变 → 静压 vs 总压混淆 → 0.5–2 hPa 跳变。**对策**：用姿态 + IMU 数据做 covariance gating，瞬态减权。

**(c) HVAC / 电梯井.** 室内空调启动 → 局部 5–20 Pa 气压脉冲。电梯井：电梯运动产生气压波，sensor 显示几米的假高度变化。**对策**：室内自动切换到 visual odometry / range finder 主导，barometer 仅做长时间 drift 校准。

**(d) 太阳暴晒.** sensor 暴晒 5 分钟 → die 温度上升 20°C → 残余温漂残量 → 高度 reading 漂 50–200 cm。**对策**：sensor 装机身阴影面 + 加白色辐射屏。

**(e) 高速前飞.** Bernoulli 效应 — 高速气流在 sensor 入口附近产生负压 → 假高度上升。10 m/s 飞行 → ~60 Pa 误差 → 5 m altitude bias。**对策**：用 airspeed 校正 (static port + pitot 整套 airdata)。

---

## 6 · 与 GNSS / IMU / range finder 融合

PX4 / ArduPilot EKF2/EKF3 vertical channel 标准融合：

```
short-term (< 1 s):   IMU accel (高频, drift fast)
mid-term  (1–60 s):   Barometer (高频, 受扰)
long-term (>10 s):    GNSS vertical (低频, 受 PDOP 影响)
近地 (<8 m):          Range finder (LiDAR / ultrasonic, 见 range_finder_for_drone_altitude.md)
```

**为什么 barometer 是 mid-term 主力**：GNSS vertical σ ≈ 3 m typical (3× horizontal due to satellite geometry — 所有卫星都在地平线以上 → vertical 几何稀释)；IMU 双积分 1 s 后已漂 ~10 cm。Barometer ~30 cm rms noise + 长时间 bias 缓变 → 完美填补这个时间尺度的 gap。

**EKF state**：通常 `baro_bias` 作为可观测状态被 GNSS update 修正 — 几分钟收敛到稳态。

---

## 7 · Hidden Assumptions — barometer 默默押注的前提

下游 EKF / 控制器假设这些条件成立，破了高度环就要爆：

- **大气压在 1–10 s 时间尺度内仅随高度变.** HVAC / 电梯 / 阵风破之。
- **Sensor temperature 与机身热平衡.** 太阳暴晒 / 引擎热源破之。
- **Drone vertical velocity << airspeed sensitivity.** 高速前飞时 Bernoulli 引入 bias，需 airdata 校正。
- **Sensor 入口与外部静压平衡.** 密闭机身内部需要静压通气孔 — 工业 drone 标配，DIY 经常忘。
- **QFE 校零基准在起降点是稳定的.** 长任务（>1 hr）期间天气变化破之。
- **EKF 信任 baro 在 1 Hz–1 Hz cutoff 内.** Cutoff 设太高 → prop wash 进入；太低 → 实际 climb rate 跟不上。
- **室内外切换有明确 trigger.** 否则在门口 HVAC 区会持续误判。

---

## 8 · 跨 embodiment 比较 + interview tip

| Embodiment | Barometer 角色 | 主要 failure mode |
|---|---|---|
| **Drone (outdoor)** | mid-term vertical 主力 | prop wash / 风扰 / 高速 Bernoulli |
| **Drone (indoor)** | 主要靠 range finder + VIO，baro 仅做 sanity check | HVAC / 电梯 / 门口气压脉冲 |
| **Humanoid** | 罕用 (脚底接地，可信 z=0) | 不适用 |
| **Manipulation** | 不用 | 不适用 |
| **AD** | 罕用 (GNSS + HD map) | 不适用 |
| **Marine (surface)** | 浪高 / 风暴预警 | 不直接用于 navigation |
| **Marine (underwater)** | depth sensor（同物理，高量程）= AUV 主力 | 防水封装 + 海水校准 |

**🎙️ Interview Tip.** 被问"drone 高度估计为什么不只靠 GNSS"？— 三层答：(1) GNSS vertical σ ~3× horizontal (几何稀释)；(2) GNSS 输出 1–10 Hz 而控制器要 100+ Hz；(3) 室内 / 树冠 / 城市峡谷 GNSS dropout。Barometer 填 mid-term 时间尺度 + 高频 + 室内可用 — 三个 gap 同时盖。

---

## 9 · For the reader

- **Drone engineer** — BMP388 / DPS310 起步，PX4/ArduPilot EKF 默认 fusion 即可。注意机身布置避 prop wash。
- **Indoor robot** — 不要信 barometer，HVAC 噪声远大于信号。
- **AUV** — MS5837-30BA 类防水版本是主深度信号，cm 精度。
- **High-altitude / mapping drone** — DPS422 + 严格热稳定 + airdata 校正。

---

## References

- Bosch BMP388 datasheet `UNVERIFIED, no DOI` — vendor primary
- Infineon DPS310 datasheet `UNVERIFIED, no DOI`
- TE Connectivity MS5611 datasheet `UNVERIFIED, no DOI`
- ICAO Standard Atmosphere (ISA) 1976
- PX4 EKF2 / EKF3 vertical channel 文档
- ArduPilot Baro driver source

## Boundary

- `gnss_multi_constellation_rtk.md` — GNSS vertical 误差性质
- `range_finder_for_drone_altitude.md` — 近地 altitude (&lt;8 m) 替代
- `imu_physics_and_noise_model.md` — IMU accel 双积分边界
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment baro 取舍
- `embodiments/aerial/sensor-stack/` — drone baro 集成实战
- `embodiments/aerial/vio/` — VIO 与 baro 融合

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
