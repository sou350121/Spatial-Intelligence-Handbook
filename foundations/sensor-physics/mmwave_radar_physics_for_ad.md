# 毫米波雷达物理 (mmWave Radar Physics for Autonomous Driving)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 76–81 GHz FMCW radar，Tesla/Waymo/Bosch/Continental/NXP
> **核心定位**：LiDAR 浪潮里所有人都打算"丢掉 radar"，但每一家 L4 平台和每一辆量产 AD 车又都把它留下 — 不是因为分辨率，是因为它在雨雪雾下**还在工作**

**Status:** v1 — opinionated draft, 14-item dissection 范式。spec 数字标 `UNVERIFIED` 需 datasheet 核对。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) 76–81 GHz FMCW radar 用 chirp 波形**同时**测距、测速、测角，从一次发射拿到三个独立量纲 — LiDAR 拿不到 native velocity，camera 拿不到 native range。(b) Tesla / Waymo / Mobileye 都用 radar 即使分辨率只有 LiDAR 的 1/100，因为它在大雨 / 浓雾 / 扬尘下衰减比 LiDAR 低 30–100× `UNVERIFIED` — 这是物理决定的，不是工程优化能补的。(c) 对 sensor 工程师：radar 不是"低成本 LiDAR 替代品"，它在传感器栈里**占据天气韧性这个独立轴**，去掉就再也没有冗余。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1995 ── Bosch ACC 24 GHz CW radar，第一代量产巡航 radar
2003 ── 77 GHz long-range radar (LRR) 进入 BMW / Mercedes 旗舰
2013 ── Continental ARS 4xx 系列 77 GHz FMCW，主流 L2
2017 ── Tesla AP2 — Bosch MRR1plus，"radar-primary forward sensing"
2019 ── NXP TEF810x / Texas Instruments AWR1843 单芯片 4D radar 出现
2021 ── Tesla 移除 radar（Pure Vision 政策） ← 业界震动
2022 ── Waymo / Cruise 反向 — 4D imaging radar (Arbe Phoenix) 进入 L4 栈
2024 ── Tesla AP HW4 重新加回 4D radar (Phoenix-class)，承认 vision-only 在恶劣天气盲区
2025 ── Imaging radar 角分辨率 ~0.5°，开始接近低端 LiDAR
        ── 你在这里 (2026) ──
?    ── 6D radar（加入 polarimetric 通道）？低成本 IRR 普及到 $50/SKU？开
```

这个 wedge 卡在"vision-only vs LiDAR-or-radar-primary"分岔点的 radar 一侧 — 真正承重的不是分辨率，是恶劣天气可用性。

---

## 1 · FMCW chirp 工作原理 (FMCW Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
range = c × f_beat / (2 × slope)
velocity = c × f_doppler / (2 × f_carrier)
AOA = arcsin(λ × Δφ / (2π × d_antenna))
```

一个 chirp 同时给出 range 与 velocity（chirp 内 beat frequency vs chirp 间相位差），AOA 由 antenna array 阵列差分给出。这是 radar 相对 LiDAR 的根本架构优势 — LiDAR 必须靠帧间 Δt 反推 velocity。

### 1.1 关键机制

- **FMCW chirp.** 发射机线性扫频（典型 76 GHz 起、200 MHz–4 GHz 带宽、扫频时间 ~10–40 µs），目标反射回来与本振信号混频得到 beat frequency `f_beat` — 与 range 线性相关。
- **Doppler.** 连续多个 chirp 之间，目标运动引入相位演化；FFT 跨 chirp 维度 → velocity。
- **AOA / DOA.** 多 antenna（MIMO TX×RX）阵列接收同一目标 → 相位差给出方向。`Bosch MRR1plus` 用 ~4 TX × 4 RX = 16 虚拟通道；`Arbe Phoenix` 4D imaging 用 48 TX × 48 RX = 2304 虚拟通道 `UNVERIFIED`，角分辨率压到 ~0.5°。

⚡ **Eureka Moment.** Radar 在传感器栈里的位置**不是**"廉价 LiDAR"，而是"native velocity sensor with 30–100× better weather penetration than 905 nm LiDAR `UNVERIFIED`"。一旦把它放在天气韧性这个独立轴上看，"为什么 Tesla 还在用 radar"的答案就显而易见。

### 1.2 信息流

```
TX VCO ─── chirp generator ──→ TX antenna ──→ 目标 ──→ RX antenna
                                                            │
                                            mixer ←── LO from same VCO
                                              │
                                          beat signal
                                              │
                                         ADC + 2D-FFT (range × Doppler)
                                              │
                                         3D-FFT (+ angle from MIMO)
                                              │
                                       point cloud / RD-map / RDA-cube
```

---

## 2 · 数学核心 (Math Core)

**目标**：从一次 chirp 同时取出 range R 与 velocity v。

**公式**：

```
f_beat = (2 × R × slope) / c + (2 × v × f_carrier) / c
       └─ range component ─┘   └─ doppler component ─┘
```

其中 `slope = bandwidth / chirp_time`。

**变量说明**：

| 符号 | 物理意义 | 典型值 (76 GHz LRR) |
|---|---|---|
| `c` | 光速 | 3 × 10⁸ m/s |
| `f_carrier` | 载频 | 76 GHz |
| `bandwidth B` | 扫频范围 | 200 MHz → range res 0.75 m；4 GHz → 0.0375 m |
| `chirp_time T_c` | 单 chirp 持续 | 10–40 µs |
| `N_chirp` | 一帧 chirp 数 | 128–256 |
| `slope` | B / T_c | ~20 MHz/µs |

**直觉**：range res ∝ 1/B，velocity res ∝ 1/(N_chirp × T_c)，angular res ∝ N_virtual_antennas。要 imaging radar，三者全要堆 — 这就是 Phoenix-class 把 1k+ 虚拟通道塞进单 module 的原因。

---

## 3 · Worked Example — 76 GHz FMCW 200 m 处 SNR 估算

```
TX power:        12 dBm (16 mW) — typical AD long-range radar
Antenna gain:    25 dBi (TX + RX)
Target RCS:      10 m² (passenger car broadside)
Range:           200 m
Bandwidth (det): 1 kHz post-FFT bin
NF (LNA):        12 dB
```

雷达方程 `P_rx = P_tx × G_tx × G_rx × λ² × σ / ((4π)³ × R⁴)`，λ = c/f = 3.9 mm。

- 路径损耗 ∝ 1/R⁴：200 m vs 1 m 差 1.6 × 10⁹ = 92 dB
- λ² σ / (4π)³ ≈ 3.9e-3² × 10 / 1984 ≈ -73 dB
- 综合：P_rx ≈ 12 + 25 × 2 - 92 - 73 ≈ **-103 dBm**
- Noise floor = -174 + 10log(1k) + 12 ≈ -132 dBm
- **SNR ≈ 29 dB** — 充分；这就是为什么 76 GHz LRR 能可靠探测 200 m。

对比：行人 RCS ~0.5 m² → SNR 下降 13 dB → 16 dB，仍可探，但分类困难（见 §6）；自行车 / 推婴儿车 ~0.1 m² → SNR ~9 dB，开始进入误警边缘。

---

## 4 · 实战 hardware archetypes

**LRR (long-range radar).** 76–77 GHz，FOV ~±10°，距离 0–250 m。Bosch `MRR1plus` / Continental `ARS 540` / Veoneer `LRR4` / Aptiv `RACam`。Tesla AP1–AP3 的"front radar"就是这一类。

**SRR (short-range radar).** 77–81 GHz，FOV ~±60°，距离 0–80 m。盲区监测 / 变道 / 泊车。Continental `ARS 408` / NXP `TEF810x` 单芯片设计。

**4D imaging radar.** 76–81 GHz，FOV ±60°，>1k 虚拟通道，角分辨率 ~0.5°，每帧 ~10⁴–10⁵ point。Arbe `Phoenix` / Mobileye `Imaging Radar` / Continental `ARS 620` / Uhnder `Digital Radar`。Tesla HW4 重新加回的就是这一档。

**单芯片 RFCMOS.** TI `AWR1843` / NXP `S32R45` / Infineon `RXS8160PL`。把 RF + ADC + DSP + MCU 全集成进单 SoC，BOM 压到 ~$10–30/SKU。

---

## 5 · 三巨头分工 (Bosch / Continental / NXP)

| Vendor | 角色 | 主力产品 | Tier-1 客户 |
|---|---|---|---|
| **Bosch** | 系统集成 + RF module | `MRR1plus` LRR / `MRR rear` SRR | Tesla AP1–AP3, BMW, Mercedes |
| **Continental** | 系统集成 + algorithm | `ARS 4xx`/`ARS 540`/`ARS 620` 4D imaging | Volkswagen, GM, Toyota |
| **NXP** | RF chipset 供应 | `TEF810x`/`S32R45` | 所有 Tier-1 都买 NXP RF 芯片 |
| Aptiv / Veoneer / ZF | Tier-1 系统厂 | LRR + SRR module | Stellantis, Ford |
| **Arbe / Uhnder / Mobileye** | imaging radar 新势力 | digital radar / Phoenix-class | NIO, Stellantis, Magna |

Bosch / Continental 是模块整合 + algorithm，NXP / Infineon / TI 是 RF chipset 上游 — 这条产业链 25 年没变过，理解这点比理解任何一篇 radar 论文都重要。

---

## 6 · 与 LiDAR 在恶劣天气下的真实差距

这是 radar 留下的根本原因 — 学界综述很少量化，工程经验很清楚：

| 天气 | 905 nm LiDAR 性能 | 76 GHz Radar 性能 | radar 优势 |
|---|---|---|---|
| **晴天** | 200 m @ 10% reflectivity | 200 m @ 10 m² RCS | 持平 |
| **雨 10 mm/hr** | 距离衰减 50–80% `UNVERIFIED` (Mie scattering) | 衰减 &lt;3 dB → 距离 ~80% | ~10× |
| **雾 50 m 能见度** | 距离 &lt; 30 m | 几乎无衰减 | ~5× |
| **雪（湿）** | 距离衰减 60–90%，且 false return 多 | 衰减 &lt;5 dB | ~10–30× |
| **灰尘（工地）** | 严重 false return | 几乎不可见 | dominant |
| **白车 backlit by sun** | OK | OK | 持平 |
| **黑色衣服 / 低 albedo 行人** | OK (NIR active) | RCS 极小，分类困难 | LiDAR 优 |

**根因**：905 nm 波长（3.3 × 10⁻⁷ m）与雨滴 / 雾滴尺度（0.01–3 mm）相比进入 Mie scattering 区，强散射；76 GHz 波长 3.9 mm 大于绝大多数 hydrometeor，进入 Rayleigh 区，散射截面 ∝ (d/λ)⁴ 急降 → 几乎透雨透雾。这是物理，不是 algorithm 能补的。

⚡ 这就是 Tesla AP HW4 在 2024 年把 radar 加回来的真正理由 — Pure Vision 在 California 永远晴天的工程师宿舍证明不了，到雪天 / 雾天就证伪。

### Hidden Assumptions — radar 默默押注的前提

- **金属反射主导。** 行人 / 自行车 RCS 比汽车小 100×；对穿黑色衣服的行人，radar 分类几乎不可能 → 必须由 camera 补。
- **多目标分辨依赖 chirp 设计。** range res = c/(2B) — 200 MHz BW → 0.75 m，两个并排行人融成一个 cluster。Imaging radar 4 GHz BW → 0.0375 m 才解。
- **76–81 GHz band 法规稳定。** 美国 / 欧洲 / 中国 / 日本都已开放 77 GHz，但 24 GHz 已被 phase-out — 押 24 GHz 的产品 EoL。
- **多 radar 干扰 (mutual interference).** 高速路上对向车都用 76 GHz FMCW，chirp 重叠产生 ghost detection。FMCW + slow ramp 容忍度低；FMCW + fast chirp + random hopping 容忍度高。
- **Multipath.** 隧道 / 桥下 / 防撞墙旁，反射路径长于直射，产生 ghost target。点云 + tracking 才能滤掉。
- **极化敏感性。** 圆极化 radar 对人形几何不敏感，线极化对车辆几何敏感 — 厂商 spec 经常不写。

---

## 7 · 与其他 sensor 对比 + Interview Tip

| Sensor | Range | 天气韧性 | Velocity | 分类能力 | Cost |
|---|---|---|---|---|---|
| **76 GHz LRR** | 200 m | 极强 | **native** | 弱 | $50–500 |
| **905 nm LiDAR** | 150–200 m | 弱 | 帧差反推 | 中 | $1k–10k |
| **1550 nm LiDAR** | 250–400 m | 中 | 帧差反推 | 中 | $5k–50k |
| **Stereo camera** | 50–100 m | 中（白天） | 帧差 | 强 | $200–1k |
| **Mono camera + ML** | 视情况 | 弱（夜雾） | 完全估计 | 强 | $30–200 |
| **Imaging radar** | 200 m | 极强 | native | 中 | $500–3k |

**🎙️ Interview Tip.** 被问"为什么 Tesla / Waymo 都重新用 radar"？— 一句话：**76 GHz 波长比 hydrometeor 大 → Rayleigh 区 → 雨雾透射；905 nm 落进 Mie 区 → 严重散射**。这是物理，不是 vision-only 能 ML 出来的。

---

## 8 · For the reader (per-persona)

- **AD engineer** — radar 不是"分辨率差的 LiDAR"，是天气韧性 + native velocity 的独立轴。砍掉它就是砍掉冗余 — Tesla 2021 砍 → 2024 加回，已经证伪一次。
- **Drone engineer** — 76 GHz radar 现在 ~10–30 g/$50 单 chip `UNVERIFIED`，对 BVLOS / 浓雾穿越有用，但点云稀疏不替代 LiDAR/stereo。
- **Manipulation engineer** — radar 在 1 m³ 工作空间几乎无用（angular res 太粗，金属反射主导）。跳过。
- **Marine engineer** — 76 GHz 在水面 reflection 严重，传统船用 X-band (9 GHz) radar 是另一物种，不在本文范围。

---

## References

- IEC / ETSI EN 302 264 — 77 GHz radar 频段规范
- Bosch `MRR1plus` / Continental `ARS 540` / NXP `TEF810x` / TI `AWR1843` datasheets — 全部 `UNVERIFIED, no DOI`
- Arbe `Phoenix` whitepapers / Mobileye Imaging Radar reveal
- Tesla AI Day 2022 / 2024 — radar policy 反转 narrative
- 维护者在 Autel 的 radar+stereo 融合经验

## Boundary

- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — LiDAR 波段物理（对比基准）
- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — NIR 主动感测（另一独立轴）
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — radar 在 BOM 内的占比与跨 embodiment 取舍
- `embodiments/driving/sensor-stack/` — radar 在 AD 模块集成 / 标定 / 时序融合
- `deployment/hardware-selection/` — radar 选型 + Tier-1 供应链

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./overview.md)
