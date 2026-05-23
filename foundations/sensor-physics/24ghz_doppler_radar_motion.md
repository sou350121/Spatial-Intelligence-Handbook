# 24 GHz K-band Doppler Radar 运动检测 (24 GHz Doppler Radar Motion Sensing)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 24 GHz K-band CW / FMCW Doppler，运动检测 / 生命体征 / 短距避障
> **核心定位**：24 GHz 是 76 GHz 车载 radar 的**便宜表弟** — 同物理原理，更便宜、距离短、分辨率粗，统治智能家居 / 室内 IoT / drone 室内 safety

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 Acconeer / Infineon / TI datasheet 核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) 24 GHz K-band radar 是 76-81 GHz 自动驾驶 radar 的"民用低 cost 版本" — 同样 FMCW / Doppler 物理，波长 1.25 cm（vs 76 GHz 4 mm）→ 分辨率粗 3× 但距离够（~20 m）+ 便宜（$5-30 chip vs $80-200）。(b) 典型 chip: Acconeer A111 / A121、Infineon BGT24、Silicon Labs。应用：自动门 / 智能马桶 / 防摔倒 / 智能音箱 presence detection / 工业 limit switch。生命体征 radar 能检测 0.1 mm 胸腔运动 = 呼吸 + 心率。(c) 对机器人 / drone 工程师：24 GHz radar 是 **室内 short-range presence** 的便宜解 — 替代 PIR（被动红外）和超声，**因为它检测速度（Doppler）而不是温度变化**。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1970s ── 警用 X-band (10 GHz) 速度雷达
1990s ── 工业 24 GHz limit switch / 自动门
2000s ── ISM 24-24.25 GHz 全球免照许可频段确立
2014 ── Acconeer A1 — 首个民用 60 GHz pulsed coherent radar（后转 24 GHz 路线）
2016 ── Infineon BGT24LTR / 24 GHz SiGe BiCMOS 单片 → cost $5
2019 ── Google Soli (60 GHz, Pixel 4) — radar 进入消费电子
2020 ── COVID 后 presence-sensing 智能家居爆发（"在不在家"检测）
2022 ── TI IWR2243 24/77 GHz 双频段单 chip
2024 ── Infineon BGT24MTR / 生命体征 chip 入医疗
        ── 你在这里 (2026) ──
?    ── 24 GHz radar + thermal fusion 防摔倒 / 6G FR3 (7-15 GHz) ISAC
```

24 GHz 是 ISM 全球免照频段，**法规友好** — 而 76 GHz 各国监管不同，民用很受限。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
CW Doppler:
f_Doppler = 2 × f_c × v / c
   24 GHz, v = 1 m/s → f_Doppler = 160 Hz   (人音频范围！直接 mic 测)

FMCW range:
Δf_beat = (2 × BW / T_sweep) × R / c
   BW 250 MHz, T 1 ms, R 10 m → Δf = 16.7 kHz

波长:
λ = c / f = 3e8 / 24e9 = 1.25 cm
   vs 76 GHz λ = 4 mm  → 24 GHz 角分辨率 3× 粗
   vs 60 GHz λ = 5 mm  → Google Soli 在更细
```

Doppler 物理对 24 GHz 特别合用：1 m/s 速度 → 音频频率，**便宜 audio ADC 就能解调**，整个 chip BOM 极低。

### 1.1 三种 24 GHz radar 形态

| 形态 | 信号 | 输出 | 应用 |
|---|---|---|---|
| **CW Doppler** | 连续波 | 速度 only (无距离) | 自动门 / 防摔倒 / 运动检测 |
| **FMCW** | 线性扫频 | (range, velocity) | 短距避障 / 智能音箱 |
| **Pulsed coherent (PCR)** | 数 ns 短脉冲 | 高分辨率 (range + phase) | Acconeer A121 / 生命体征 |

### 1.2 关键机制：CW Doppler 极简电路

```
   24 GHz oscillator ───→ TX antenna ──→ scene
                    │                        │
                    │                        ↓ (moving target)
                    │              ←──── reflected with Doppler shift
                    │                        │
                    │      RX antenna  ←─────┘
                    │            │
                    ▼            ▼
                  mixer  → IF (audio range) → ADC → motion detected
```

**整个 receiver 只需要一个 mixer + audio ADC** — chip 可以 $2-5 BOM。这是为什么 24 GHz 民用爆发的根因。

⚡ **Eureka Moment.** 24 GHz Doppler 不是"低端 76 GHz radar"，是**完全不同的应用域**：
- 76 GHz: 200 m / cm 分辨率 / 高 cost / 强监管 → 自动驾驶
- 24 GHz: 20 m / 10-30 cm 分辨率 / 极便宜 / ISM 免照 → 智能家居 + 室内 IoT
两者**互不竞争**，是 radar 频段法规 + cost 决定的应用分层。

### 1.3 生命体征 radar (Vital Sign Radar)

人胸腔呼吸位移 ~5 mm，心跳引起体表位移 ~0.1 mm — 24 GHz 波长 12.5 mm 检测 0.1 mm 位移 = **测 phase shift 而非 range** —

```
Δφ = 4π × Δd / λ
   Δd = 0.1 mm, λ = 12.5 mm → Δφ = 0.1 rad   (可检测)
```

呼吸 0.2-0.4 Hz、心率 1-2 Hz — 频谱分离 → 同时测呼吸 + 心率 + 体动。已用于医院床位监测、车内婴儿遗留检测、防摔倒。

---

## 2 · 数学核心：vs 76 GHz 分辨率与距离 (Math Core)

📌 **Napkin Formula** (X-Ray)：所有 radar 物理跟 76 GHz 同（FMCW / chirp / range = BW × time delay / c），仅频率不同导致：(1) 波长长 → 角分辨率粗、(2) 大气衰减小、(3) 法规宽松。

### 2.1 Range Resolution

```
ΔR = c / (2 × BW)
   24 GHz ISM BW = 250 MHz → ΔR = 60 cm
   24 GHz wideband (UWB-radar) BW = 5 GHz → ΔR = 3 cm
   76 GHz BW = 4 GHz → ΔR = 3.75 cm
```

**ISM 频段限 24-24.25 GHz** = 250 MHz BW → range 分辨率 60 cm。要 cm 级需走 UWB-radar 路线（FCC 准许 22-29 GHz 给 short-range automotive，但功率限严）。

### 2.2 Angular Resolution

```
θ_angular ≈ λ / D
24 GHz, D = 5 cm aperture → θ ≈ 1.25/5 rad = 14°
76 GHz, D = 5 cm → θ ≈ 5°
60 GHz, D = 5 cm → θ ≈ 6°
```

24 GHz 同样大小 antenna 角分辨率粗 3× — 决定了它**只能做 "presence in zone"** 而非精细 mapping。

### 2.3 Atmospheric Absorption

```
α_24GHz ≈ 0.05 dB/km  (晴朗)
α_60GHz ≈ 15 dB/km    (氧吸收峰)
α_76GHz ≈ 0.5 dB/km
```

24 GHz 是低衰减 sweet spot — 这就是为什么它适合**远距 + 全天候 + 便宜**的组合。60 GHz Google Soli 反而因为氧吸收衰减成"近场"sensor。

---

## 3 · Worked example — 卫浴防摔倒 24 GHz CW Doppler

设置（数字 `UNVERIFIED`）：
- chip: Infineon BGT24LTR11
- TX power: 10 dBm (10 mW)
- 应用: 浴室天花板装 sensor，检测人**摔倒后不动**

**正常活动:**
- 人慢走 → Doppler 0.5-1 m/s → 80-160 Hz IF
- 洗澡微动 → 0.1 m/s → 16 Hz IF
- 呼吸 → 5 mm × 0.3 Hz → 极小 IF 信号

**摔倒检测:**
- 快速移动 → 短脉冲 0.5-2 m/s
- 然后 "Doppler 全 0"持续 30 s
- 但仍有呼吸 phase shift (Δφ ~0.1 rad @ 0.2 Hz) → "**有人但不动**"
- 触发警报

**距离 vs 灵敏度:**
- 3 m 距离 → SNR ~30 dB （足够）
- 5 m 距离 → SNR ~15 dB （边缘）
- 透薄塑料 / 木门 OK（穿一层墙），透厚混凝土不行

**典型 module BOM**: chip $5 + antenna PCB $1 + MCU $2 + housing $5 = **&lt;$15 完整产品** vs PIR sensor $0.5 但功能少很多。

---

## 4 · 工程视角 (Engineering View)

**Cost ladder (`UNVERIFIED`):**
- Infineon BGT24LTR11 (CW only): ~$3-5 chip
- Acconeer A111 (PCR): ~$10-15
- Acconeer A121 (PCR upgraded): ~$15-20
- TI IWR1843 (24/77 dual): ~$30-50
- Module form factor: $10-50

**功耗 (24 GHz CW vs PCR):**
- CW Doppler (always on): ~50-200 mW
- Pulsed coherent (PCR, sub-Hz duty): &lt;1 mW average（battery-powered IoT 可行）
- vs PIR ~10 µW, ultrasonic ~50 mW

**Antenna PCB.** 24 GHz patch antenna 在 FR4 板上可以做 — vs 76 GHz 需要专用高频材料（Rogers RO4350）。**这降低 PCB cost 10×.**

**法规.** 24-24.25 GHz ISM 全球免照许可、power 限 100 mW EIRP；22-29 GHz UWB-radar 各国不同：FCC OK（功率严限），欧盟 ETSI 限 vehicular only。

---

## 5 · 数据与评测 (Data & Eval)

- **Infineon Position2Go 评估板** — 24 GHz dev kit，开源 demo (presence / counting / 防摔倒)
- **Acconeer Exploration Tool** — A121 PCR dev framework，SDK + Python visualizer
- **学界 datasets**: vital-sign radar 学界论文多但缺乏统一 benchmark
- **Google Soli (60 GHz)** — Pixel 4 motion gestures 是手势 radar 唯一消费爆款

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 室内 presence 检测；运动 / 速度直接测；穿薄墙 / 玻璃 / 衣物；不需要光照；24/7 always-on；隐私友好（不是 camera）；生命体征监测。

**不能做什么.** 区分人和动物（都是 0.5-2 m/s warm-blooded mover）；高分辨率 mapping（ΔR ~60 cm）；穿混凝土；同 chip 多目标精细分辨。

### Hidden Assumptions

- **24-24.25 GHz ISM 频段持续可用.** 各国监管偶有调整
- **室内 multipath 可控.** 大金属墙 / 镜面 → ghost target
- **目标在 Doppler 范围.** 静止物体 CW Doppler 检测不到（只能 FMCW）
- **天线方向已知.** 24 GHz 单 antenna FOV ~60-90°，固定指向
- **干扰物不在 24 GHz.** 部分 microwave oven leakage / industrial RF 落在 24 GHz

**失败模式：**
- **静止人误判为"无人"** — CW Doppler 只测运动；需 FMCW 或 PCR phase-tracking 才能"看到"静止人
- **HVAC 气流误触发** — 窗帘 / 风扇 / 空调让 radar 误判有运动
- **多人混叠** — 单 antenna 分不开 2 个 1 m/s 同向运动的人
- **ISM 邻频干扰** — 部分国家 5G NR n258 (24.25-27.5 GHz) 与 24 GHz 邻频 → spurious
- **金属壁反射 ghost** — 摔倒报警系统在金属浴室假阳性高

---

## 7 · 与相关工作对比 (Comparison)

### 24 GHz vs PIR vs Ultrasonic vs Camera vs 76 GHz

| Sensor | 检测原理 | 隐私 | Power | Cost | 距离 | 区分人/动物 |
|---|---|---|---|---|---|---|
| **PIR** | 温度变化 | ★★ | µW | $0.5 | &lt;8 m | 弱 |
| **Ultrasonic (40 kHz)** | 距离变化 | ★★ | 50 mW | $5 | &lt;5 m | 不能 |
| **24 GHz Doppler** | 速度 | ★★★ | 50-200 mW | $5-30 | &lt;20 m | 弱 |
| **60 GHz Soli** | 高分辨率 motion | ★★★ | ~50 mW | $20-50 | &lt;2 m | 中（手势） |
| **76 GHz** | range + velocity | ★★★ | 1-3 W | $80-200 | 200 m | 中 |
| **Thermal camera** | 体温 | ★★ | 0.5 W | $200+ | 50 m | 强 |
| **RGB camera** | 视觉 | ★ | 1 W | $20+ | 100 m | 强 |

**🎙️ Interview Tip.** 被问"24 GHz 和 76 GHz radar 啥区别"？— 同物理原理 + 频段不同 → **法规 + cost + 距离**完全不同分层：24 GHz ISM 免照 / chip $5 / 20 m → 智能家居；76 GHz 各国限车载 / chip $100 / 200 m → 自动驾驶。**不是性能孰优，是应用域分层。**

---

## 8 · For the reader

- **Manipulation** — 几乎用不上
- **Mobile robot (室内 service)** — 检测人在不在房间 → 24 GHz presence sensor 是低 cost 解
- **Drone (室内 inspection / safety)** — 24 GHz 短距避撞 + 室内"人在工区"safety 检测
- **AD** — 76 GHz 主，24 GHz 备 (低速短距避撞 / 后视盲点) — 部分国产车在用
- **Smart home / IoT** — 24 GHz 完全统治（Aqara 防摔倒 / Vayyar 居家健康 / 自动门）

---

## References

- Infineon BGT24LTR11 Datasheet `UNVERIFIED, no DOI`
- Acconeer A111 / A121 PCR Series Documentation `UNVERIFIED`
- TI IWR1843 / IWR2243 Single-Chip mmWave Sensor `UNVERIFIED`
- FCC 47 CFR §15.245 / §15.246 — 24 GHz ISM emissions
- ETSI EN 300 440 — Short Range Devices in 1-40 GHz

## Boundary

- 24 GHz radar 物理 / chip 选型 / 失效模式 → 本文
- `mmwave_radar_physics_for_ad.md` — 76 GHz 车载 radar 物理（频率不同导致应用分层）
- `crossing/sensor-stack-matrix/` — radar 在 6 embodiment 频段选择
- `embodiments/aerial/sensor-stack/` — drone 室内 24 GHz safety 工程集成
- `deployment/hardware-selection/` — Acconeer vs Infineon vs TI 选型
- 生命体征算法 / radar signal processing → 学界 paper 或 vendor SDK 文档

*2026-05-21. v1. UNVERIFIED → v1.1 待 chip datasheet 核对。*

---
[← Back to sensor-physics README](./overview.md)
