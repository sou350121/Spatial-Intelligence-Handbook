# Range Finder for Drone Altitude (drone 近地测距 — 超声 vs 单线 ToF vs mmWave altimeter)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — drone 起降 / 室内悬停 / terrain following 近地测距三种物理对比
> **核心定位**：drone &lt;8 m altitude 是 barometer 失效 / GNSS vertical 不够准的盲区——range finder 是唯一可信信号；但三种物理（acoustic / NIR ToF / mmWave）在不同表面 / 距离 / 天气下成功率天差地远，工程账学界从不写

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字需 datasheet 交叉核对。
**Wedge tier:** sensor-physics expansion（E 桶 drone stack 第 5 篇）

### X-Ray opening

drone 在地面 ±8 m 范围内：barometer 受 prop wash 扰、GNSS vertical σ ~3 m（精度不够 0.5 m 起降要求）、IMU 双积分秒级就爆。**Range finder 是唯一在这个时间-空间尺度上可信的 vertical 信号**。但三种主流物理（超声 acoustic / 单线 NIR ToF / mmWave altimeter）各自有不同的盲区：超声在户外有风扰、ToF 在草地透射不返回、mmWave 在水面 specular 反射失锁。学界综述把它当"已解决"，实际是 drone 起降事故的主要根因。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1980s ── Polaroid SX-70 超声测距头 ── 第一代消费级 USS
1995 ── Devantech SRF04 ── DIY drone 主流
2005 ── 雷电 / 大疆早期产品超声 altimeter ── 消费 drone 时代
2014 ── Garmin LIDAR-Lite ── 单线 ToF 大众化
2018 ── TFmini-S (Benewake) ── drone 优化 ToF，~$50
2019 ── VL53L1X (ST) ── SPAD ToF chip，~$5
2020 ── 大疆 Mavic 系列向下视觉 + ToF hybrid
2022 ── Acconeer A111/A121 ── 60 GHz pulsed coherent radar，~$10 drone altimeter
2024 ── Texas Instruments IWR6843 ── 60 GHz altimeter 产品化
202? ── ?  下一波：multi-line ToF (Garmin LIDAR-Lite v4 / Lumotive) 在 drone
```

---

## 1 · 三种 range finder 物理对比

📌 **Napkin Formula**：`R = (c × ToF) / 2`，其中 c 是介质中的波速：声速 343 m/s @ 20°C，光速 3e8 m/s，mmWave 3e8 m/s。**声波 ToF 比光快 10⁶ 倍但精度 1 cm 也够 drone 用**——成本和功耗才是真正区别。

| Property | 超声 (HC-SR04 / MaxBotix) | 单线 NIR ToF (TFmini-S, VL53L1X) | mmWave altimeter (Acconeer A121, TI IWR6843) |
|---|---|---|---|
| 物理 | acoustic pulse 40 kHz | NIR laser pulse 905 nm | FMCW 60 GHz radar |
| 速度 | 声速 343 m/s | 光速 3e8 m/s | 光速 3e8 m/s |
| 范围 | 0.02–4 m (室内 OK, 户外退化) | 0.1–12 m (TFmini-S), 0.04–4 m (VL53L1X) | 0–50 m (60 GHz) |
| 精度 `UNVERIFIED` | ±1 cm &lt; 2 m | ±1 cm &lt; 6 m | ±5 cm typical, ±0.5 cm peak |
| 视野角 | 30° 锥 | 2–3° narrow beam | 30–80° (天线设计) |
| 功耗 | &lt;10 mW | 50–500 mW | 50–200 mW |
| 价格 | $2 (HC-SR04) – $50 (MaxBotix) | $5 (VL53L1X) – $50 (TFmini-S) | $10 (A121) – $50 (IWR6843) |
| 失败表面 | 软织物 / 棉花 / 海绵（吸声） | 草地（光散射穿透） / 黑漆 (低反射) | 平静水面（specular 单点反射） |
| 天气 | 强风噪声 / 暴雨吸收 | 浓雾 / 暴雨 / 强阳光（环境 NIR） | 全天候 ✓ |
| 倾斜表面 | 30° 锥所以容忍度高 | 表面法线偏 >30° → 漏接收 | 中等容忍 |

⚡ **Eureka Moment.** 三种 range finder 不是性能阶梯——是**物理域分工**：超声短距+宽锥适室内 / 低速；NIR ToF 准+窄束适 mapping / terrain following；mmWave 全天候+长距适商用 drone landing。**选错就是 drone 起降事故。**

---

## 2 · 超声 (HC-SR04 / MaxBotix MB1240)

**物理**：发 40 kHz 短脉冲，等 echo 返回，ToF / 2 × 343 m/s = 距离。

**优势**：成本极低，软织物 / 玻璃可见，DC-LED 干扰 immune。

**缺陷**：
- **风扰**：5 m/s 风 → ~10–20% range error (Doppler shift + medium displacement)。
- **prop wash**：drone 螺旋桨产生 air turbulence + acoustic noise → pulse 衰减 + 多径。
- **室外限**：地面起伏 / 草地吸声 → max range 1.5 m typical (室内 4 m)。
- **吸声物体**：海绵 / 织物 / 蓬松地毯无 echo。

**drone 实战**：DJI 早期 Phantom 用，~3 m altitude 起降；现在大都 hybrid (USS + ToF)。Crazyflie 不用 (重量 / 互扰)。

详见 `ultrasonic_acoustic_physics_for_robotics.md` 完整物理。

---

## 3 · 单线 NIR ToF (TFmini-S, VL53L1X)

**物理**：发 905 nm laser pulse → SPAD 阵列检测 → histogram peak → ToF。VL53L1X 是 SPAD-based; TFmini-S 是 SPAD + DSP 集成模组。

**优势**：
- 窄 beam (2–3°) → terrain following 中精确锁定地面
- 高频更新 (50–100 Hz)
- 小 (15x15 mm)
- 准 (±1 cm &lt; 6 m)

**缺陷**：
- **草地透射**：905 nm 在叶片之间散射，echo 时间分布宽 → peak 不显著 → 误读"草顶"或"草下"。
- **黑色 / 低反射表面**：黑漆 / 沥青 / 黑布 反射率 &lt;5% → range 缩到 1–2 m。
- **倾斜表面**：法线偏 >30° → 反射不返回，丢失 echo。
- **暴雨 / 浓雾**：水滴散射 → range 缩 30–50%。
- **强阳光**：阳光中 NIR 分量 ~50 W/m² (AM1.5) → SPAD 饱和，需要窄带 BPF + 短曝光保护。

**drone 实战**：TFmini-S 是商用 drone (DJI M300, Skydio 2) altimeter 主力；VL53L1X 是 nano drone (Crazyflie) 主力。

物理细节见 `tof_physics_for_embodied_ai.md` 与 `active_nir_850nm_for_embodied_ai.md`。

---

## 4 · mmWave altimeter (Acconeer A121, TI IWR6843)

**物理**：FMCW 60 GHz chirp → mixer → IF beat frequency ∝ range → FFT。

**优势**：
- **全天候**：水 / 雾 / 雪 / 烟 吸收 60 GHz &lt;1 dB/km → 暴雨 / 沙尘暴正常工作
- **长距**：60 GHz altimeter 能打 50 m
- **range + Doppler**：副产品给 vertical velocity（drone 降落判断）
- **不受 sun NIR**

**缺陷**：
- **水面 specular**：60 GHz 在静水面镜面反射 → 角度偏离即丢 echo
- **空中沙尘**：sand 颗粒尺寸 ~0.1–1 mm @ 60 GHz λ=5 mm → Mie 散射轻度衰减
- **vegetation penetration**：草叶 / 树叶部分穿透 → 测量到草下表面（**好坏看应用**：terrain following 要草顶， search-rescue 要地面）
- **小 transient (Sub-1m)** 精度比 ToF 差（chirp bandwidth 限）
- 需要 antenna design 工程

**drone 实战**：Acconeer A121 在工业 drone 上日益普及（~$10 chip + 1 cm² PCB area）。TI IWR6843 是高端 drone 用。

详见 `mmwave_radar_physics_for_ad.md` mmWave 通用物理。

---

## 5 · Worked example — 0.5 m 起飞降落精度需求 → 选哪个 sensor？

```
Mission:    DJI Mavic 类 drone，户外 grass field 起降
Target:     altitude error <10 cm in last 50 cm of approach
Constraint: low cost, low weight (<10 g sensor module)
```

**比较**：
- **超声 (HC-SR04)**：户外草地 echo 弱 + prop wash 噪声 → 10–30 cm error。**不达标。**
- **TFmini-S (NIR ToF)**：草地多 echo peak → ±5 cm at last 1 m，但草高度本身 ~5 cm → 把草顶当地面 → 飞机停在草上 vs 草中地面不一致。**近达标，但 vegetation 不稳定。**
- **VL53L1X**：4 m range, 短距精度 ±1 cm，价格 $5。草地 limitation 同上。
- **Acconeer A121 (60 GHz)**：vegetation 部分穿透 → 报地面距离 + 草顶 echo → 选 strongest peak = 地面。10 g 模组 / $20 / ±2 cm typical。**达标。**

**结论**：grass-field 起降优先 mmWave altimeter；硬地 (asphalt / 砖) 起降 NIR ToF 足够 + 更便宜；室内 (任何表面) NIR ToF + 超声 hybrid。

**这就是为什么现代商用 drone 不止一颗 range finder**——多物理冗余。DJI Mavic 3：USS + ToF + 双下视相机 + barometer = 5 vertical 信号 fusion。

---

## 6 · 与 barometer + GNSS 融合 — fallback hierarchy

drone EKF 通常的 vertical 信号融合 priority：

```
altitude  source                          band valid
< 0.1 m   none / range finder noise floor   landing impact
0.1–8 m   range finder (laser / radar)      primary
0.1–4 m   ultrasonic (室内)                 secondary
> 8 m     barometer (mid-term) +            primary
          GNSS vertical (long-term)
> 50 m    barometer + GNSS only             primary
```

**降落序列实战 (PX4)**：
1. 高度 >8 m：barometer + GNSS vertical
2. 高度 8 m → 3 m：触发 range finder fusion，innovation gating 一致性检查
3. 高度 3 m → 0.5 m：range finder 主导，barometer 仅 sanity
4. 高度 &lt;0.5 m：range finder + 视觉 ground tracking + IMU 触地检测
5. 触地：spring-load 检测 motor disarm

**为什么需要切换**：barometer prop wash 噪声越靠近地面越严重；range finder 在 >10 m 信号微弱或超量程。

---

## 7 · Hidden Assumptions — range finder 默默押注的前提

- **Surface 在 sensor 范围内 + 反射率足够.** 黑漆 / 草 / 水面 / 雪 各破不同 sensor。
- **No multi-path 主导.** 室内 reflective 墙壁角落产生多径；mmWave 在金属车库地面易多径。
- **drone 姿态合理.** Tilt >30° 时窄 beam range finder 看不到正下方。多 sensor + tilt compensation。
- **Range finder 看到的就是地面.** vegetation / 雪 / 水面下方 differ。
- **Sensor 没被 prop wash 灰尘遮蔽.** 起飞前 5 s sensor 透镜需保持清洁。
- **EKF 信任 range innovation.** 高度跳变（飞过高物 / 屋顶边缘）outlier rejection 必须正确。
- **Sensor 与 IMU 时间同步 &lt;10 ms.** 高速 vertical motion 时关键。

---

## 8 · 跨 embodiment 比较 + interview tip

| Embodiment | Range finder 选择 | one driver |
|---|---|---|
| **Drone (室内 hover)** | VL53L1X / 超声 | 短距 / 低成本 / 不受 sun |
| **Drone (户外硬地起降)** | TFmini-S NIR ToF | ±1 cm 精度 + 4 m 范围 |
| **Drone (户外 grass / 雪 / 水面)** | Acconeer A121 60 GHz | vegetation 穿透 + 全天候 |
| **Drone (商用 mapping)** | TFmini-S + 60 GHz hybrid | 冗余 + cross-check |
| **Nano drone (&lt;100 g)** | VL53L1X 唯一 | 重量限 |
| **AGV (室内)** | 2D lidar 不需要单线 range finder | 2D lidar 已覆盖 |
| **AD car (parking)** | USS + radar | low-speed close-range |
| **Manipulation (wrist)** | RGBD (RealSense) 不用单线 | RGBD 已覆盖 |
| **Marine (surface)** | radar altimeter (60 GHz) | 浪反射 |
| **AUV** | acoustic altimeter (sonar) | 水下 |

**🎙️ Interview Tip.** 被问"drone 降落用什么 sensor"？— 一句答：高度分层。3 m 以上 barometer + GNSS；3 m 到 0.5 m 用 range finder (laser 在硬地 / radar 在草地)；0.5 m 以下加视觉 ground tracking + IMU 触地。**不存在单一 sensor 解决整段**——多物理冗余是 drone 安全降落的根本。

---

## 9 · For the reader

- **Nano drone** — VL53L1X，重量 / 价格 / 性能甜点。
- **Mid drone 户外硬地** — TFmini-S 性价比最高。
- **Commercial drone 户外 mixed surface** — TFmini-S + Acconeer 60 GHz 双 sensor。
- **Mapping drone (草地 / 雪 / 水面)** — 60 GHz altimeter 主力。
- **AGV / manipulation** — 用专门的 2D lidar / RGBD，不用单线 range finder。

---

## References

- Benewake TFmini-S datasheet `UNVERIFIED, no DOI`
- ST VL53L1X datasheet `UNVERIFIED, no DOI`
- Acconeer A121 datasheet + Range Detector app note
- TI IWR6843 reference design
- MaxBotix MB1240 ultrasonic datasheet
- PX4 / ArduPilot rangefinder driver source

## Boundary

- `barometer_pressure_altimetry.md` — >8 m 高空 altitude
- `gnss_multi_constellation_rtk.md` — GNSS vertical (3× horizontal σ)
- `ultrasonic_acoustic_physics_for_robotics.md` — 超声完整物理
- `tof_physics_for_embodied_ai.md` — NIR ToF 完整物理
- `mmwave_radar_physics_for_ad.md` — mmWave 完整物理
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment 取舍
- `embodiments/aerial/sensor-stack/` — drone range finder 集成实战
- `embodiments/aerial/obstacle-avoidance/` — 横向避障 (不在本文档范围)

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
