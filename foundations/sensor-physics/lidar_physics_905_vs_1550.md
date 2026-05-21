# LiDAR Physics: 905 nm vs 1550 nm (LiDAR 物理 — 905nm 与 1550nm 路线之争)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — Si SPAD vs InGaAs SPAD / eye safety / mechanical vs solid-state / FMCW
> **核心定位**：厂商 pitch 含糊带过的眼睛安全算术 — 1550 nm 在物理上没赢 905 nm，它赢在 IEC 60825-1 MPE 天花板上的 ~1000×，这就是全部故事

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字仍需 spec-sheet 交叉核对。
**Wedge tier:** sensor-physics expansion（5 篇姊妹文中的第 3 篇）

### X-Ray opening

905-vs-1550 LiDAR 之争由一个数字决定：IEC 60825-1 Class 1 Maximum Permissible Exposure (MPE) 在激光波长上的值。905 nm 下，cornea + lens **透过**光束打到视网膜 → MPE 把 peak power 卡在几 mW。1550 nm 下，cornea + lens 在光到达视网膜之前**几乎全部吸收** → MPE 跳 ~1000× → kilowatt peak 脉冲也是 Class 1。对 sensor 工程师：这就是 Luminar / Aeva / Hesai-FT 愿意付 InGaAs 溢价的原因 — 他们买的是 eye-safety headroom，不是更好的光子。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2007 ── Velodyne HDL-64 (905nm, mechanical) ── KITTI 时代, $80k/13kg
2014 ── Quanergy / Ouster (905nm Si SPAD) ── solid-state 时代开始
2017 ── Luminar 成立 (1550nm InGaAs SPAD, kW peak) ── 眼睛安全套利
2019 ── Aeva 发布 FMCW LiDAR (1550nm 相干检测)
2020 ── Hesai Pandar128 (905nm，车规验证)
2022 ── Innoviz One (905nm MEMS-mirror solid-state，靠 duty 等效 kW)
2023 ── Hesai AT128 / AT512 (905nm, 半固态, $1-4k tier)
2024 ── Aeva Atlas (FMCW 量产) / Luminar Halo
2025 ── Livox Mid-360 (905nm, 250g) ── 进入 sub-3kg drone tier
202? ── ?  下一波：silicon-photonics OPA（无活动部件）、$500 级 1550nm
```

本文件卡在 905 nm Si / 1550 nm InGaAs 分岔点 — 大众市场 AD LiDAR 中唯一有争议的物理问题。

---

## 1 · 波长物理初识

📌 **Napkin Formula**：`max_class1_peak ≈ MPE(λ) × eye_pupil_area / pulse_duration`。§2 的所有内容对照这个公式 — 905 nm 在 ~5 mW peak 撞 MPE；1550 nm 在 ~5 W average / kW peak 撞。这就是全部路由。

**(a) 探测器物理。**
- **905 nm + Si SPAD.** Silicon 带隙 1.12 eV — 905 nm 光子（1.37 eV）可被探测。Si SPAD QE ~30% @ 905 nm `UNVERIFIED`。CMOS 量产工艺；车规价位下 100k+ 像素阵列。Hesai / Innoviz / Ouster 路线。
- **1550 nm + InGaAs SPAD.** Silicon 在 ~1100 nm 以后透明。需要 InGaAs (In₀.₅₃Ga₀.₄₇As，带隙 0.74 eV)。Hybrid CMOS+InGaAs ROIC。QE ~20–30% `UNVERIFIED`。每像素成本 50–100× Si SPAD。Luminar / Aeva / Hesai-FT 路线。

**(b) Eye safety — IEC 60825-1 MPE。** Cornea 表面的吸收决定视网膜风险：
- **905 nm：** cornea + lens **透过** ~70% 到视网膜；1.37 eV 光子对视网膜有 photochemical damage。100 ns 脉冲 MPE：~`UNVERIFIED` 1 µJ/cm²。Continuous：~1 mW/cm²。
- **1550 nm：** cornea (~3 mm 厚) 与 lens 中的水吸收 >99% 的 1550 nm 在到达视网膜前。光子能量 (0.80 eV) 即便穿透也太低，不足以造成 photochemical 损伤。MPE 跳 ~1000× — kW peak 脉冲也是 Class 1。

这就是**那个**套利。Photon-for-photon，1550 nm 更差（InGaAs 更贵，廉价模组 QE 还略低）；MPE-for-MPE，它赢 1000×。

**(c) 大气 / 天气。**
- **雾 / 雨 / 雪** — Mie scattering 在两个波长都主导；1550 nm 在浓雾中略好 `UNVERIFIED` 但远不到 MPE 的 1000× 量级。1550 nm 的 "all-weather" 营销**大部分**其实是 peak-power headroom，不是大气损耗差异。
- **太阳环境光** — 1550 nm 处于 H₂O 吸收 dip → ambient 比 905 nm 低 ~3–5× `UNVERIFIED`。小帮助，不是承重因素。

⚡ **Eureka Moment.** 905-vs-1550 选择是眼睛安全 MPE 天花板之争，**不**是更好的光子或天气。其他所有轴都是 1000× MPE 阶跃的下游。Luminar 的"see further in rain"半真半假；真正故事是"我们能打你打不到的 kilowatt"。

---

## 2 · 905 nm vs 1550 nm 对比

| Property | 905 nm Si SPAD | 1550 nm InGaAs SPAD |
|---|---|---|
| 每像素探测器成本 | ~$0.01–0.10 (CMOS) | ~$1–10 (hybrid InGaAs) |
| QE @ λ | ~30% `UNVERIFIED` | ~20–30% `UNVERIFIED` |
| Class 1 peak (10 ns pulse) | ~5 mW `UNVERIFIED` | ~5 W (~1000×) |
| Class 1 average | ~1 mW/cm² | ~100 mW/cm² + |
| Range (Class 1, automotive) | 100–200 m | 250–500+ m |
| Solar ambient @ λ | baseline | ~3–5× lower `UNVERIFIED` |
| 雾穿透 | baseline | 微弱优势 |
| BoM tier（整 sensor） | $500–4k | $5k–80k |
| 量产成熟度 | very high | growing |
| 典型厂商 | Velodyne, Ouster, Hesai, Innoviz, Livox | Luminar, Aeva, Hesai-FT |

预测厂商选择的规则：range 目标 ≤200 m 且 BoM 上限 ≤$4k → 905 nm；range 目标 >250 m 或平台容得下溢价 BoM → 1550 nm。

---

## 3 · Mechanical vs solid-state vs FMCW（架构）

**(a) Mechanical spinning.** Velodyne HDL/VLP, Hesai Pandar64。64–128 个独立 laser+detector 对装在旋转 gimbal 上，5–20 Hz。优势：成熟、原生 360°、易理解。劣势：机械磨损、~500–13000 g、集成丑陋。**905 nm 主导** — InGaAs 价格乘以 N=64 通道不可接受。

**(b) Solid-state — MEMS mirror.** Innoviz One, Hesai AT128/AT512。一个（或少数）laser，用 ~5×5 mm MEMS mirror 做光束扫描。优势：无宏观活动部件、车规可达。劣势：FOV 受限（通常 60–120°）、震动下 MEMS 可靠性。

**(c) Solid-state — flash.** Ouster DF, Continental HFL110。无扫描；一次性照亮整场，2D SPAD array 逐像素读 timing。优势：无扫描伪影（动态场景的 rolling-shutter 消失）、光学简单。劣势：光功率预算 — flash 200 m × 60° 宽角度极耗能 → 1550 nm 在这里出场。

**(d) Solid-state — OPA (optical phased array).** Quanergy 试过，今天是 silicon-photonics 研究。无活动部件、电子束转向。优势：chip 级潜力。劣势：仍受成熟度限制。

**(e) FMCW (Frequency-Modulated Continuous Wave).** Aeva, SiLC, Mobileye Chauffeur LiDAR。相干检测：发射 chirped CW，与本地振荡器混频，beat 频率逐像素编码距离**与** Doppler 速度。优势：每像素速度（对预测巨大帮助）、抗干扰（只匹配自己的 chirp）、对眼睛安全友好。劣势：光学复杂、激光昂贵（1550 nm tunable）。**1550 nm 主导** — 相干检测需要 narrow linewidth + InGaAs 探测器。

大部分 pulsed LiDAR（905 或 1550）都是 **ToF** — 只测距。FMCW 是 **coherent** — 距离 + 速度，根本不同。

---

## 4 · Worked example — 905 nm vs 1550 nm 在 200 m 处的 SNR

Back-of-envelope（数字 `UNVERIFIED`，仅用于工程直觉）：

```
Target:     10% diffuse Lambertian reflector, 200 m
Receiver:   25 mm aperture, 10 nm BPF
Ambient:    AM1.5 daylight (1 kW/m² broadband)
Pulse:      10 ns (limited by Class 1 peak)
```

- **905 nm 路径.** Class 1 cap → 5 mW peak → 0.05 nJ/pulse。200 m 处每脉冲返回光子：`0.05 nJ × (10% × π·(0.025/2)² / (4π·200²)) × QE / hν` ≈ ~5 photons `UNVERIFIED`。SPAD dark count ~10 cps `UNVERIFIED`，BPF 把 ambient 降到 ~1k cps。需 ~100 脉冲做 histogram → 3 kHz rep rate 下 30 Hz 帧率。每像素成本低，系统成本中等。
- **1550 nm 路径.** Class 1 cap → 5 W peak (1000×) → 50 nJ/pulse。返回光子 → ~5000 photons/pulse `UNVERIFIED`。200 m 单脉冲 SNR：比 905 nm 好 100×。结果：同帧率下打到 250–500 m，或 200 m 处 30 Hz 用 1 脉冲/像素无 histogramming → timing 更简、每像素摊销成本更低。

1000× MPE 阶跃不是边际收益 — 它是**根本不同的信号体制**。在 200 m，905 nm 靠 histogramming 撑住；1550 nm 根本不需要。这就是 Luminar 营销 "single-pulse confidence" 的物理基础。

印证 §1 → §2：905 nm 的 range 不是被物理限制，是被 Class 1 限制。1550 nm 用 BoM 把天花板抬高。

---

## 5 · 实战硬件类型

**Velodyne / Ouster 一脉.** 905 nm Si SPAD，机械或固态。Range 通常 100–200 m，$1k–10k tier。L4 开发车队的主力；研究界遍地都是。

**Hesai AT128 / AT512.** 905 nm MEMS 半固态。~$1–4k。半固态时代；≥10% 反射率下 range 200 m `UNVERIFIED`。2024-26 中国乘用车 AD 主导。

**Luminar Iris / Halo.** 1550 nm InGaAs SPAD，pulsed。目标 $1k+，今天 $5k+。Volvo EX90 一脉。打高速 250 m。

**Aeva Atlas.** 1550 nm FMCW。每像素速度。Mobileye Chauffeur 合作。BoM 更高，溢价 tier。

**Innoviz One / Two.** 905 nm MEMS。Audi A8 时代 → Volkswagen 量产。Range 200 m，BMW-ID 905 nm Si SPAD 路线。

**Livox Mid-360.** 905 nm，零售 ~$1k，265 g。把 LiDAR 带入 sub-3 kg drone tier（见 `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` §7）。

---

## 6 · Hidden Assumptions — 每条路线默默押注的前提

905-vs-1550 选择只在下列条件成立时稳定：

- **IEC 60825-1 保持 Class 1。** 法规收紧（例如新的儿童眼睛安全修订）可能抹掉 1000× headroom；两条路线都要重算。
- **InGaAs 供应。** 1550 nm 需要 InGaAs；供应冲击（telecom 上行、地缘政治）拉长 lead time。905 nm 绑定 CMOS 供应（深得多）。
- **Class 3R/3B 不被接受。** 工业 LiDAR（仓库、采矿）有时出 Class 3R — 905 nm 靠 duty cycling 拿到 kW 等效，不需要 1550 nm。乘用车保险杠处必须 Class 1。
- **太阳维持 AM1.5。** 雪 albedo、高原 UV、赤道午时都会把 ambient 推高 — 905 nm in-band ambient 会让廉价 SPAD 饱和。
- **雾 / 雨数字是 population-tail 不是中位数。** 浓雾两个都挂；1550 nm 的"全天候"优势是营销 tail-end。
- **没有竞争的 in-band 源。** 高速上多台 905 nm LiDAR 会互相干扰；coded pulse 序列能缓解但不能消除。FMCW (1550) 靠相干检测绕开。

---

## 7 · 跨 embodiment 比较 + interview tip

| Embodiment | LiDAR pick（如果用） | 原因 |
|---|---|---|
| **AD 乘用车 L2+** | 905 nm MEMS (Hesai AT128 / Innoviz) | $1–4k BoM 上限；高速够 200 m |
| **AD 乘用车 L3+** | 1550 nm (Luminar Iris / Aeva) | 250 m + single-pulse confidence 撑得起溢价 |
| **Robotaxi L4** | 905 nm 机械 (Velodyne) 历史主流；混入 1550 | 异质感测做冗余；stack 成熟 |
| **Drone (≥3 kg)** | 905 nm 固态 (Livox Mid-360) | 250 g / 10 W 适合 payload；100 m 够用 |
| **AGV / 采矿** | 905 nm Class 3R 短距 | 室内/围栏 → Class 1 非强制 |
| **Manipulation** | 不用 | 工作空间 1 m³；LiDAR 无分辨率优势（见 crossing/sensor-stack-matrix） |

经验：**L3+ 乘用车 AD** 上，1550 nm 靠 MPE 天花板胜出。其他位置，905 nm 的 BoM 优势是决定性的。

**🎙️ Interview Tip.** 被问"Luminar 为什么用 1550 nm"？— 答**眼睛安全 MPE 1000× headroom 让 kW peak 脉冲成为可能，从而让 250 m 在 Class 1 下达成。** 回答"更好的天气"或"更长波长 = 更远距离"的人读的是营销不是物理。

---

## 8 · For the reader

- **AD engineer** — ≤200 m / BoM 受限用 905 nm；只在 250 m+ 写进合同时才上 1550 nm。FMCW 只在预测里需要每像素速度时才考虑。
- **Aerial engineer** — Livox Mid-360 级 905 nm；1550 nm 还没进 drone tier。
- **Manipulation engineer** — 直接跳过 LiDAR；这个分岔与你的工作空间无关。
- **Marine engineer** — 两个波长都在 >1 m 水中失效；忽略 LiDAR，用 multibeam sonar。

---

## References

- IEC 60825-1 — laser product safety classification
- Velodyne HDL/VLP, Hesai AT128/AT512, Innoviz One/Two product specs `UNVERIFIED`
- Luminar Iris / Halo whitepapers `UNVERIFIED, no DOI`
- Aeva Atlas FMCW technical brief `UNVERIFIED, no DOI`
- Livox Mid-360 datasheet `UNVERIFIED`
- 实战：维护者在 trade shows 上接触车载 LiDAR 厂商 pitch

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — 短距 850 nm 姊妹文（active stereo / structured light）
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — ToF 体制（姊妹文；pulsed LiDAR 是 pulsed ToF 的长距分支）
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment SWaP-C：LiDAR 何时合理
- `embodiments/aerial/sensor-stack/` — Livox 级 drone 部署
- 各 embodiment 的集成 + 标定（extrinsics、time-sync）见 `embodiments/<x>/sensor-stack/`；本文只覆盖波长 + 眼睛安全 + 探测器物理。

*2026-05-21. v1 首版，满足 14 项 gate。UNVERIFIED → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./README.md)
