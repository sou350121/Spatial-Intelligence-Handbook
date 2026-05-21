# 水下声呐物理 (Underwater Sonar Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — multibeam / side-scan / DVL，水声学 100 kHz – 1 MHz
> **核心定位**：水下唯一可信感知物理 — 视觉退化、GNSS 不可用、LiDAR 几米衰减 — AUV / ROV 的 SLAM 全靠声呐撑

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 Teledyne / Sonardyne / Norbit datasheet 核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) 水下声呐用 100 kHz – 1 MHz 声波（不是无线电）— 因为水对电磁波 attenuation 是 ~1000 dB/km @ 1 GHz，但对声波只 ~1 dB/km @ 10 kHz；声速 ~1500 m/s（4× 空气）。三大形态：**multibeam sonar** 做前视 mapping、**side-scan sonar** 做海底 sweep 成像、**DVL (Doppler Velocity Log)** 做 4-beam 速度测量。(b) Teledyne RDI / Sonardyne / Norbit 是 AUV 工业三巨头；marine VIO / SLAM 几乎全靠 DVL + IMU + multibeam 三件套。(c) 对 robotics 工程师：把水下当成"另一个 embodiment"是错的 — 水下是**不同物理常数下的整套 sensor 重选**，视觉 / LiDAR 全部失效，声呐取而代之。空气超声 (`ultrasonic_acoustic_physics_for_robotics.md`) 和水下声呐都是声学，但**频率 / 介质 / 衰减全不同**，几乎是不同物种。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1906 ── 第一颗 hydrophone（Reginald Fessenden）
1915 ── Langevin 主动声呐（潜艇探测，WW1）
1957 ── side-scan sonar 商用（Edgerton / Klein）
1976 ── multibeam sonar（SeaBeam，海底测绘起飞）
1990s ── DVL 商业化（RD Instruments 创立 1982）
2000s ── AUV 量产（Bluefin / Hydroid / Kongsberg HUGIN）
2014 ── 马航 MH370 搜索 — multibeam + side-scan 大规模动员
2020-25 ─ Saildrone / Ocean Infinity 自主 AUV 商业化
2022 ── Pentagon 水下声呐 ML（NOAA datasets）
        ── 你在这里 (2026) ──
?    ── 水下视觉-声呐融合 SLAM / acoustic NeRF / 商用 ROV 价格降到 $10k
```

水下 SLAM 在 2026 是**学界 + 国防 + 商业**三轨独立发展 — 远没有车载 / 室内那么收敛。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
c_water ≈ 1449 + 4.6·T - 0.055·T² + 1.34·(S-35) + 0.016·z
                  温度        压力 (盐度修正)         深度
(单位：m/s，T °C，S ppt，z m)

距离测量:   d = c × t / 2
横向分辨率: ≈ c × t_pulse / 2  (脉宽决定径向精度)
角分辨率:  θ ≈ λ / D = c / (f × D)   (D = 阵列孔径)

声呐方程:   EL = SL - 2·TL + TS - NL
   EL = echo level (dB)
   SL = source level (dB re 1µPa @ 1m)
   TL = transmission loss = 20·log(r) + α·r   (geometric + absorption)
   TS = target strength (dB, 散射截面)
   NL = noise level
```

声速比空气快 4×，意味着同样 1 m 距离飞行时间从空气的 ~6 ms 缩到水下 ~0.7 ms — 更快但 c 受温/盐/深影响 5-10%，必须实时补偿。

### 1.1 三类声呐对比

| 类型 | 频率 | 应用 | 数据形态 |
|---|---|---|---|
| **multibeam** | 100-400 kHz | 前视 / 下视 mapping | 3D point cloud (~256 beams) |
| **side-scan** | 100-1000 kHz | 海底 sweep 成像 | 2D 强度图（声学"照片"）|
| **DVL** | 600-1200 kHz | 速度测量（4-beam Doppler）| (vx, vy, vz) 矢量 |
| **single-beam echo sounder** | 12-200 kHz | 简单测深 | 单 (距离) |
| **synthetic aperture sonar (SAS)** | 100 kHz | 高分辨率 mapping | 类 SAR，cm 级 |

### 1.2 关键机制：DVL — 水下 VIO 等价物

DVL 发射 4 个 Doppler 束（"Janus" 配置，向下倾 30° 形成十字），每束测海底 / 水层反射的频率偏移：

```
f_Doppler = 2 × f_carrier × v_relative / c
```

四束矢量分解出 (vx, vy, vz)，对水下 ROV / AUV 等价于**视觉 VIO 的 velocity tap**。这是水下 SLAM 之所以能工作的核心。

⚡ **Eureka Moment.** 水下 SLAM 不是"调一调视觉 SLAM 就能跑"— 是**整套 sensor 物种替换**：视觉 → multibeam；odometry → DVL；GNSS → USBL (Ultra-Short Baseline acoustic beacon)；IMU 仍在但**唯一保留的陆地 sensor**。EKF 状态向量和 KITTI / EuRoC 完全不可比 — 学界把 EuRoC 100% recovery 当王者，水下来真机就裸奔。

### 1.3 声呐方程实战

```
SL = 220 dB (典型 100 kHz multibeam, re 1µPa @ 1m)  [UNVERIFIED]
TL = 20·log(200) + 0.04·200 = 46 + 8 = 54 dB         (r=200m, α @ 100kHz)
TS = -30 dB (中等鱼群)
NL = 50 dB (海况 2-3)
EL = 220 - 108 - 30 - 50 = 32 dB                     (够检测)
```

α (吸收系数) **频率敏感**：1 dB/km @ 10 kHz，10 dB/km @ 100 kHz，100 dB/km @ 1 MHz — 这是为什么远距声呐用低频（10-50 kHz），近距高分辨率用高频（>500 kHz）。

---

## 2 · 数学核心：从波长到分辨率 (Math Core)

📌 **Napkin Formula** (X-Ray)：低频远距大目标 / 高频近距细节。水下 LiDAR 不工作的原因正是 — 蓝绿激光 532 nm 水中衰减 ~0.04 dB/m vs 声波 100 kHz ~10 dB/km — **声波传 1 km，激光传 100 m**。

### 2.1 角分辨率与阵列孔径

```
θ_angular ≈ λ / D
λ = c / f
```

100 kHz, D=0.5 m (典型 multibeam 头) → λ = 1.5 cm → θ ≈ 1.7°。200 m 距离 → 横向 ~6 m 分辨率。  
要 cm 级 → SAS (synthetic aperture) 把"运动的 array"拼成 100× 长度的虚拟孔径。

### 2.2 SVP (Sound Velocity Profile) 折射

水下声速随深度变化 → 声线**折射**（不是直线）：

```
Snell: sin(θ₁)/c₁ = sin(θ₂)/c₂
```

温跃层（thermocline）下声速 dip 形成"声学波导" — 声线被 trap 在某层 → 远距离 mapping 必须实时测 SVP（CTD 探头）做 ray tracing 修正。**没有 SVP 修正 → 100 m 距离横向偏 5-10 m**。

### 2.3 USBL 定位（水下 GPS 等价）

ship 上挂多元件接收阵列，AUV 上挂 transponder。ship 发 ping，AUV 应答 → ship 测**到达时间 + 角度**反算 AUV 位置：

```
range = c × T_round / 2
bearing = arcsin(λ × Δφ / (2π × d_baseline))
```

精度 0.1-1% × range — 1000 m 距离误差 1-10 m。这就是 AUV 水下 absolute position 的**唯一来源**。GPS 在水下 1 m 以下就死。

---

## 3 · Worked example — AUV @ 50 m 深, multibeam 100 kHz + DVL 600 kHz

设置（数字 `UNVERIFIED`）：
- AUV: HUGIN-class
- multibeam: 100 kHz, 256 beams, 1.5° angular res
- DVL: 600 kHz, range 200 m (open water)

**Multibeam 测海底（直下 50 m）:**
- T_round = 2 × 50 / 1500 = 67 ms
- 横向 footprint @ 50 m: tan(1.5°) × 50 = 1.3 m
- 256 beams × 60° swath → 60 m sweep width
- 200 ping/s → 12 km²/h coverage @ 4 kts speed

**DVL 测速:**
- 4 beam @ 30° down, 50 m altitude → 60 m slant range OK (200 m max)
- Doppler precision: ~1 mm/s `UNVERIFIED`
- 集成 5 m/s × 1 h → ~3 m drift (没 USBL update)

**EKF 融合 DVL + IMU + USBL:**
- 单独 DVL: 0.1% of distance traveled drift
- + IMU (ADIS16448): 短期 attitude OK
- + USBL update 每分钟一次 → 守住 ~1 m 绝对精度

匹配 Kongsberg HUGIN datasheet `UNVERIFIED` 报告的 marine SLAM 表现。

---

## 4 · 工程视角 (Engineering View)

**Cost.** Teledyne RDI Workhorse 600 kHz DVL ~$50k；Norbit multibeam ~$80-200k；商用 USBL ~$30-100k。**完整 AUV navigation suite 半百万级别** — 这是为什么 marine robotics 远没消费化。

**功耗.** Multibeam 50-200 W；DVL 10-50 W；USBL 10-30 W。AUV 总功率预算 ~500 W → 主动 sensor 占大头。

**延迟.** 声速 1500 m/s → 200 m 范围 RTT ~270 ms — **inherent 物理延迟**，无法 algorithmic 优化。这就是水下控制 loop 物理上不能 >5-10 Hz 的根因。

**Form factor.** Multibeam 头 30-50 cm 直径，因为 cm 级波长 + 阵列孔径要求；vs 76 GHz radar mmWave 直径几 cm。**SWaP 完全不同**。

---

## 5 · 数据与评测 (Data & Eval)

- **AQUALOC / SubPipe / FLSea** — 学界水下视觉 + 声呐 SLAM datasets
- **NOAA Public Bathymetry Database** — multibeam ground truth
- **MH370 搜索数据** (Ocean Infinity, 2018) — 公开 SAS imagery
- 学界 benchmark **严重不足** vs KITTI / EuRoC — 是 marine VIO 尚未"卷"起来的原因

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 50-1000 m 距离的可靠测距 / mapping；不受光照影响；穿浑浊水（视觉死的地方声呐还在工作）；DVL 给水下 odometry 唯一可信 velocity。

**不能做什么.** cm 级 absolute position（需 USBL + DVL fusion）；空气中工作；快速控制 loop（声速延迟）；近距离 (<2 m) — 多径主导。

### Hidden Assumptions

- **温/盐/深 SVP 已知或可测.** 没 CTD 探头的便宜 AUV 在 thermocline 下精度爆炸
- **海底反射 strong enough.** 极软泥 / 中水层（midwater）DVL 测不到底 → 退化到 "water track" 模式精度 10×
- **声学环境干净.** 港口背景噪声 / 船只 / 海洋哺乳动物声 → SNR 暴跌
- **multipath 不极端.** 浅水 (<10 m) 声呐回波叠加水面反射 → ghost target
- **温度补偿实时.** AUV 下潜 100 m 跨 10°C 温差，c 变化 ~3% → 距离测量直接错 3%

**失败模式：**
- **layer-trapping.** 温跃层下声波被 trap，远距感知失效
- **multipath in shallow.** 港口 / 沿岸 surface bounce
- **biofouling.** transducer 表面附着海洋生物 → SL 下降 10 dB+
- **cavitation.** 高速 AUV propeller 产生气泡噪声 → DVL beam 失效
- **outage 不在地图.** AUV 几小时无 USBL update → 漂出地图，dead reckon 失败

---

## 7 · 与相关工作对比 (Comparison)

### vs 空气超声 (`ultrasonic_acoustic_physics_for_robotics.md`)

| 维度 | 空气超声 (40 kHz) | 水下声呐 (100-1000 kHz) |
|---|---|---|
| 介质 | 空气 (c=343 m/s) | 水 (c=1500 m/s) |
| 频段 | 40 kHz 主 | 100-1000 kHz |
| 距离 | <5 m | 10-1000 m |
| 衰减 | ~1 dB/m @ 40 kHz | 1-100 dB/km |
| 阵列规模 | 单 transducer | 16-512 element array |
| Cost | $5 module | $50k-$200k |
| 应用 | 泊车 / drone altimeter | AUV mapping / DVL |
| 物理共性 | 都是声波 ToF | 都是声波 ToF |
| 差异根因 | 介质决定 SWaP-C 完全不同 | — |

**两者根本不是同一物种** — 介质差异主导一切。

### vs 其他水下 sensor

| Sensor | 范围 | 精度 | 水下可行 |
|---|---|---|---|
| **Multibeam sonar** | 100-1000 m | cm-m | ★★★ |
| **DVL** | 50-200 m | mm/s | ★★★ |
| **USBL acoustic** | 100-7000 m | 0.1-1% | ★★★ |
| **Camera + light** | 1-10 m | depends | ★ (浑浊死) |
| **Blue-green LiDAR (532 nm)** | 50-100 m | dm | ★ (高 cost) |
| **GNSS** | 0 (水下) | — | 完全失效 |
| **mmWave radar** | 0 (水下) | — | 完全失效 |

**🎙️ Interview Tip.** 被问"为什么水下不能用 LiDAR"？— 蓝绿激光 532 nm 在清水中 attenuation ~0.04 dB/m，传 100 m 衰减 4 dB OK，但 NIR/SWIR (>800 nm) 水中衰减 >10 dB/m，传 1 m 都不到。**水中是蓝绿激光唯一窗口**，配 ToF 给 Subsea LiDAR — 但 cost ~$200k+，远高于声呐。

---

## 8 · For the reader

- **Manipulation** — 无关
- **Mobile robot / Ground** — 无关，除非桥下 / 矿井积水
- **Drone / Aerial** — 无关，除非 amphibious drone（少数）
- **Marine (AUV / ROV)** — 这是你的核心 sensor stack；DVL + multibeam + USBL + IMU 是 marine SLAM 全部
- **Defense** — 反潜战声呐物理共性，但 frequency / array 配置不同

---

## References

- Robert Urick — *Principles of Underwater Sound* (3rd ed., 1983) — 教科书
- Teledyne RDI Workhorse DVL datasheet `UNVERIFIED, no DOI`
- Norbit Subsea iWBMSe multibeam `UNVERIFIED, no DOI`
- Sonardyne USBL Wideband product family `UNVERIFIED`
- NOAA *Hydrographic Surveys Specifications and Deliverables* (2024)

## Boundary

- 水下声呐单 sensor 物理 → 本文
- `crossing/sensor-stack-matrix/` — marine vs 其他 embodiment BOM
- `embodiments/marine/sensor-stack/` — AUV / ROV 工程集成
- `deployment/hardware-selection/` — Teledyne vs Norbit vs Sonardyne 选型
- 水下 SLAM 算法 (FLS-SLAM / acoustic graph SLAM) → `foundations/state-estimation/` 或 `embodiments/marine/slam/`
- 空气超声 → `ultrasonic_acoustic_physics_for_robotics.md`

*2026-05-21. v1. UNVERIFIED → v1.1 待 datasheet + Urick 教科书核对。*

---
[← Back to sensor-physics README](./README.md)
