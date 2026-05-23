# 超声 / 声学传感器物理 (Ultrasonic / Acoustic Physics for Robotics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 40 kHz airborne ultrasonic（**非** marine sonar）
> **核心定位**：超声便宜、可靠、近距，但每个工程师踩过同一组坑 — multipath、温度补偿、波长 vs 物体尺度 — 这些坑物理上注定，不是 algorithm 能省掉的

**Status:** v1 — opinionated draft，14-item dissection 范式。数字 `UNVERIFIED`。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) 40 kHz 超声在空气中波长 ~8.6 mm，HC-SR04 / MaxBotix EZ 这种 $5 模块靠"发射 40 kHz pulse → 等待 echo → 飞行时间 × 声速 ÷ 2 = 距离"工作。(b) Tesla 车用超声、drone 下视 altimeter、Roomba 边缘检测都用它，因为它 **&lt;5 m 准、低成本、独立于光照**；但比 LiDAR / ToF 慢 100×（声速 343 m/s vs 光速 3 × 10⁸ m/s）。(c) 对 sensor 工程师：超声的失败模式（multipath、温度漂、物体尺度不足 ½ λ）和 LiDAR 几乎是镜像 — 把这两个对照看，会理解为什么 robotics 通常**两者都装**。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1915 ── Langevin 第一个声纳（潜艇探测，水下）
1956 ── Polaroid 600 系列相机用超声 autofocus（首个量产空气超声）
1990 ── HC-SR04 / Devantech SRF 系列 hobby 超声进入市场
1999 ── iRobot Roomba — 超声边缘检测进入 mass-market 机器人
2005 ── MaxBotix EZ 系列工业超声（温度补偿 + 滤波）
2014 ── Tesla Model S — 12 颗超声组成 360° 泊车阵列
2018 ── DJI Mavic 系列 — 下视超声 altimeter <5 m
2022 ── Tesla 移除超声（Pure Vision 政策）
2024 ── Tesla 回归超声（HW4 + 重新加 USS） ← 与 radar 一起反转
        ── 你在这里 (2026) ──
?    ── MEMS 超声 transducer（<$0.5/SKU）+ ASIC 完整 array？开
```

Tesla 砍超声 → 回归的反转和 radar 完全平行：vision-only 在低速近距停车场景**物理上**填不掉。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
Z = c_sound × t_flight / 2
c_sound (空气) ≈ 331.3 × √(T_K / 273) ≈ 343 m/s @ 20°C
λ (40 kHz) ≈ c / f = 8.6 mm
```

第一式给距离；第二、三式提示两个**主导失效轴**：温度敏感性（声速 ∝ √T） + 波长尺度（物体小于 λ/2 ~ 4.3 mm 几乎不反射）。

### 1.1 系统组件

| 组件 | 输入 | 输出 | 关键约束 |
|---|---|---|---|
| **piezo transducer (TX)** | 40 kHz drive signal | acoustic pulse | 共振频率窄 |
| **piezo transducer (RX)** | echo | electrical signal | 同 TX 同频（多数 module 同一个） |
| **timing circuit** | TX start + RX threshold | t_flight (µs) | 关键精度 |
| **温度补偿** | T sensor | c_sound | &lt;1% 误差需 ±5°C 测温 |

### 1.2 关键机制

发射机用 piezo 元件在 40 kHz 振动 ~10 cycles → 形成 ~250 µs 短脉冲；echo 回来 piezo 反向产生电信号；时序电路测 µs 级 RTT。

⚡ **Eureka Moment.** 超声不是"低端 LiDAR"，是**慢声波 + 大波长**带来的完全不同物种 — 慢让 algorithm 简单（多次回波容易区分），大波长让它**透灰尘 / 雾 / 不受光照**但**对小物体几乎隐形**（行人脚、电线、栅栏）。这两个性质对 LiDAR 几乎反转，所以两者互补而非竞争。

### 1.3 信息流

```
MCU ──→ 40 kHz drive (10 cycles)
         │
         ▼
       Piezo TX ─→ pulse 出发 (t=0)
                          │ 343 m/s
                          ▼
                       目标反射
                          │ 343 m/s
                          ▼
                     Piezo RX ──→ amplifier ──→ threshold detector
                                                       │
                                                  t_flight 测量
                                                       │
                                                       ▼
                                              Z = c × t / 2
```

---

## 2 · 数学核心 — 温度、湿度、声速 (Math Core)

**目标**：估计在已知 T、湿度下的声速，以及 echo 强度衰减。

**声速**：

```
c(T, RH) ≈ 331.3 × √(T_K / 273) × (1 + 0.0016 × RH%)   (近似)
```

| 温度 (°C) | RH% | 声速 (m/s) | 与 20°C dry 差 |
|---|---|---|---|
| 0 | 0% | 331.3 | -3.4% |
| 20 | 0% | 343.2 | baseline |
| 20 | 100% | 343.5 | +0.1% |
| 40 | 0% | 354.6 | +3.3% |
| 40 | 100% | 355.2 | +3.5% |

**衰减**：空气吸收 ~1.3 dB/m @ 40 kHz `UNVERIFIED`；散射衰减依赖 hydrometeor。5 m 往返 → 13 dB 吸收（不算扩散）。

**变量说明**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `c` | 声速 | 343 m/s @ 20°C |
| `T_K` | 绝对温度 | 273 K + °C |
| `λ` | 波长 | 8.6 mm @ 40 kHz |
| `f` | 工作频率 | 25 / 40 / 58 / 200 kHz 商用档 |
| `r_obj` | 物体特征尺寸 | <λ/2 时几乎不反射 |

**直觉**：物体特征尺寸 &lt; 4.3 mm（半波长）时反射弱 → 行人脚、电线、栅栏几乎"隐形"。这是物理。

---

## 3 · Worked Example — 5 cm 距离测量需要多精确的时序？

```
目标距离 Z = 5 cm = 0.05 m
声速 c = 343 m/s
t_flight = 2 × Z / c = 0.1 / 343 ≈ 291 µs
```

要 1 cm 分辨率 → Δt = 2 × 0.01 / 343 = 58 µs。
要 1 mm 分辨率 → Δt = 5.8 µs（µs 级 timer，廉价 MCU 即可）。

但温度漂呢？

- 20°C → 40°C 让 c 升 3.3% → 在 5 cm 处距离误差 ~1.7 mm（**单一温度变化 ≫ time 量化误差**）。

⚡ **结论**：5 cm 测量精度的瓶颈**不**是 timer 精度，是**声速温度补偿**。商用 module（MaxBotix EZ）必带 T sensor + 实时补偿 — 不补偿的 hobby HC-SR04 在 30°C 温差下系统误差 2.5%，对自动泊车场景已不可接受。

继续：

- 5 m 距离 → t_flight = 29 ms。重要后果：**最大测量频率 ~33 Hz**（必须等上一个 echo 回来才能再发）。这就是为什么超声**不能做高速避障** — 速度限于 1–30 Hz，LiDAR 用同样思路能跑 100k Hz（光速 vs 声速）。
- 飞行时间在 echo 5 cm 距离 = 290 µs；与一些 wireless 协议（BLE event ~625 µs）已经可比 — 系统时序要求严格。

---

## 4 · 实战 hardware archetypes

**Hobby tier.** `HC-SR04` / `US-100` / `JSN-SR04T` — $1–5，无温度补偿，精度 ±1 cm，距离 2 cm–4 m，5 V，硬件极简。

**工业 tier.** `MaxBotix EZ1`/`EZ4` / Murata / Devantech `SRF08` — $25–100，带温度补偿 + 数字滤波，精度 ±2 mm，距离 0.2–10 m。

**Automotive tier.** Bosch USS（超声泊车）/ Valeo PSS — embedded 在保险杠内，多 module 飞行时间编码区分（避免相互串扰），距离 0.2–5.5 m，温度补偿 + EMC 抗扰。Tesla / 大众 / 丰田 全用。

**Drone altimeter.** DJI / Autel / Skydio 下视超声 + barometer + ToF 融合 — altitude &lt;5 m 用超声主导，>5 m 切到 ToF / barometer / vision。低于 30 cm 进入"哨兵"模式准备触地。

**MEMS 新一代.** Chirp `CH101`/`CH201` (TDK 收购)、Vesper VM — 整片 MEMS + ASIC，<$3，&lt;0.5 W，正在替代 piezo discrete。

---

## 5 · 与 LiDAR / ToF / barometer 对比

| Sensor | 速度 | 近距精度 | 远距 | 透气 ✓ vs 灰尘 / 雾 | Cost |
|---|---|---|---|---|---|
| **超声 40 kHz** | &lt;5 m, 33 Hz | ±2 mm | 弱 | **透灰尘 / 雾** | $1–100 |
| **ToF (VL53L5CX)** | &lt;4 m, 60 Hz | ±5 mm | 弱 | 雾衰减 | $5–20 |
| **905 nm LiDAR** | 0.5–150 m, 10–20 Hz | ±2 cm | 强 | 雨雾散射 | $1k–10k |
| **Barometer** | 任意高度 | ±10 cm | 强 | OK | $1–10 |
| **Stereo camera** | 0.3–30 m, 30 Hz | depth-dependent | 中 | OK | $200–1k |

**drone altimeter** 通常是 4 个一起：超声 (&lt;5 m) + ToF (&lt;4 m) + barometer (>5 m) + downward stereo (整段)。任何一个单独都不可靠 — 这种冗余设计是产品级 drone 与 hobby drone 的分水岭。

---

## 6 · Failure modes — 只有踩过才知道

**Multipath.** 室内角落、车库墙角、家具腿 — 一个 pulse 从多个表面反射回，时序电路把第一个 echo 当目标，但那个 echo 可能是从天花板反射的"远"目标。LiDAR 也有 multipath 但光速太快、点云稀疏，超声 multipath 是**大问题** — 这就是 Tesla USS 用 12 个 module 协调 + 时序编码的原因。

**Cross-talk.** 多个超声同时工作，A 的 echo 被 B 接收 → 距离爆错。Tesla 用**时分发射** + 频率轻微 offset（38 kHz / 40 kHz / 42 kHz）区分。Hobby 用单 module 不存在此问题。

**Cone angle.** 40 kHz 超声 cone ~30–60° — 远比 LiDAR 单束（~0.1°）宽。意味着距离测量是 cone 内**最近**点，不是某个特定方向。drone 下视 USS 在斜坡上会给"最近的斜坡点距离"而非垂直高度。

**风噪声.** drone propeller wash 在 40 kHz 附近有能量 → 进入 RX 触发误警。商用模块用窄带 BPF 缓解，但 propeller 直接朝下吹仍会污染信号 — Mavic 下视 USS 在 80%+ 油门时几乎不可用。

**Compressor / vacuum / industrial ultrasonic.** 工厂里大量超声噪声（cleaning bath, leak detector @ 40 kHz）— AGV 在工业场景超声会**被自己周围的设备喂错距离**。

**小物体 / 细电线.** 电线、栅栏、桌椅腿（直径 &lt;4 mm）几乎不反射超声 → drone 撞电线是经典事故。这是物理（波长 8.6 mm）决定的，不是 algorithm 能补。

### Hidden Assumptions

- **物体反射面 ≥ λ/2 ~ 4.3 mm.** 细电线、栅栏失语。
- **温度补偿做对.** ±3°C 测温即给 ±0.3% 距离误差。
- **没有相邻超声干扰.** 单 module 安全；多 module 必须协调。
- **空气均匀.** 强温度梯度（暖气 / 冰箱）让 c 不均匀，距离有偏。
- **目标不动.** 高速目标在 echo 期间已位移 — 不过 33 Hz 速率下大多数 robotics 场景成立。
- **MCU 时序 µs 级稳定.** 低端 hobby MCU 中断延迟可造 ~50 µs 抖动 = 8.6 mm 误差。

---

## 7 · 与 LiDAR multipath 对比 + Interview Tip

LiDAR 也有 multipath（镜面反射，corner reflector），但点云稀疏 + 飞行时间精度 ns 级让 multipath echo 在时间上分得开；超声**慢 10⁶×**，echo 在 ms 时间窗内挤在一起 — 这就是为什么超声 multipath 是工程难点而 LiDAR multipath 是论文题目。

**🎙️ Interview Tip.** 被问"为什么 Tesla 把超声砍掉又加回来"？— 一句话：**vision-only 在低速近距停车场景（&lt;5 m、低光、灰尘、玻璃边缘）物理上填不掉超声的 ±2 cm 精度 + 光照独立性 — 砍掉省下 ~$50/车，加回是因为售后反馈 + 法规**（欧洲 EuroNCAP 要求 360° low-speed sensing）。

---

## 8 · For the reader (per-persona)

- **Drone engineer** — 下视超声 + ToF + barometer + stereo 四件套是产品级 altimeter，单 USS 不可信。注意 propeller wash 干扰 80%+ 油门下。
- **AGV / Roomba engineer** — 360° 超声 ring 是经典 cliff / wall 检测，cost <$50 全套。注意工厂超声噪声场景。
- **AD engineer** — USS 是**低速停车专用**，不参与高速决策。Tesla 反转印证了它在 BOM 里的最小价值是不可削减。
- **Manipulation engineer** — 超声在桌面几乎无用（cone 太宽、小物体不反射），跳过。
- **Marine engineer** — 空气超声与水下 sonar 是**两个完全不同物种**，本文不适用，参考 marine 专文（水声 c ≈ 1500 m/s，4× 空气）。

---

## References

- HC-SR04 / MaxBotix EZ1 / Murata MA40 datasheets — 全部 `UNVERIFIED, no DOI`
- TDK Chirp `CH101` / `CH201` MEMS ultrasonic — `UNVERIFIED`
- Bosch USS / Valeo PSS 车规 — `UNVERIFIED`
- ISO 26262 / EuroNCAP low-speed sensing 规范 — 法规文件
- 维护者在 Autel drone altimeter 融合经验

## Boundary

- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — TOF 类比，光速 vs 声速对照
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — ToF 在同一近距段的对照
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 超声在 AGV / drone / AD 的 BOM 占比
- `embodiments/aerial/sensor-stack/` — drone 下视 altimeter 融合
- `embodiments/ground/sensor-stack/` — AGV / Roomba 超声 ring
- `embodiments/driving/sensor-stack/` — USS 在 Tesla / 大众 泊车系统
- `embodiments/marine/` — 水下 sonar（**不同物种**，c = 1500 m/s）

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./overview.md)
