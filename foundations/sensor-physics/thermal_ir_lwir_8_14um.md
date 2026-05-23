# 长波热红外 LWIR 8-14 µm 物理 (Thermal IR / LWIR Physics for Robotics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 8-14 µm microbolometer / cooled InSb / NETD / FFC
> **核心定位**：LWIR 是**被动黑体辐射**感知 — 不靠光照 / 不靠 active emitter — 但物理上**不透玻璃**且**与可见光 SLAM 不能直接共用相机**，这两点决定它的边界

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 FLIR / Teledyne 数据手册核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) 任何物体温度 >0K 都辐射黑体光谱；300 K 物体（人 / 室温物体）的 Planck 峰值在 ~10 µm — 这是**长波红外** (LWIR, 8-14 µm) 窗口。**Microbolometer** 用一片 12-17 µm pitch 的氧化钒 / 非晶硅薄膜阵列检测温度 → 不需要光照，dark room / 雾 / 浓烟里照常工作。(b) FLIR Boson 320 / Lepton 模组把这个能力做成 ~$200-2000 的 OEM 模组；典型 NETD（噪声等效温差） 30-50 mK；汽车级 Tesla / Mobileye 持续争论加不加 LWIR（截至 2026 仍不加）。(c) 对机器人 / drone 工程师：thermal 是**完全独立物种** — 不能和 RGB 共用 SLAM pipeline（feature detector / 数据分布不同），但 thermal-VIO / thermal-stereo 学界 2022+ 有突破。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1800 ── Herschel 发现红外（用棱镜分光）
1960s ── 冷却型 HgCdTe / InSb 军用
1990s ── 非冷却微测辐射热计（microbolometer，VOx 薄膜）量产
2009 ── FLIR 收购 Boson / Lepton 系列 → 商用 thermal 进入 drone
2014 ── FLIR ONE for iPhone — 消费 thermal 入场
2018 ── DJI Zenmuse XT — drone thermal payload 标准化
2020 ── Tesla 删除 thermal 计划讨论（Pure Vision）
2022 ── thermal-VIO 学界论文涌现（IROS / ICRA 2022-24）
2024 ── FLIR Boson+ — 8.7 µm pixel pitch，NETD <30 mK
        ── 你在这里 (2026) ──
?    ── thermal NeRF / event-thermal fusion / 消费 AR thermal overlay
```

Thermal 在机器人语境里 2022 年前几乎只是"传感器附属"，2022 年后开始作为 SLAM 主感官出现 — 但远未收敛。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
Planck radiation:
B(λ, T) = (2hc²/λ⁵) × 1 / (exp(hc/λkT) - 1)

Peak wavelength (Wien displacement):
λ_peak × T = 2898 µm·K
  → 300 K (人/室温)        → λ_peak = 9.66 µm    (LWIR 中心)
  → 1000 K (火焰)          → λ_peak = 2.9 µm     (MWIR / SWIR)
  → 5800 K (太阳)          → λ_peak = 0.5 µm     (可见光)

大气透过窗口:
3-5 µm (MWIR) + 8-14 µm (LWIR)  ← 这两段被大气放过
  其他 H₂O / CO₂ 吸收禁区
```

**所有几何机制下游都来自 Wien 位移：300 K 物体峰值在 10 µm，所以监控"人体 / 自然场景温度"的 sensor 必须在 LWIR。**

### 1.1 三类 thermal sensor 对比

| 类型 | 波段 | 制冷 | NETD | Cost | 典型应用 |
|---|---|---|---|---|---|
| **Microbolometer (VOx/a-Si)** | LWIR 8-14 µm | 非冷却 | 30-50 mK | $200-2k | 民用 thermal camera |
| **Cooled InSb** | MWIR 3-5 µm | -200°C Stirling | 5-15 mK | $20-100k | 科研 / 军用 |
| **Cooled HgCdTe** | LWIR/MWIR 可调 | -200°C | <5 mK | $50-200k | 高端军用 / 天文 |
| **Pyroelectric (PIR)** | broadband | 无 | mK 级 motion only | $1 | 运动检测 (不成像) |

### 1.2 关键机制：Microbolometer

Pixel 是一片 micro-bridge 悬空 VOx 薄膜，吸收 LWIR 辐射 → 升温 → 电阻变化 → ROIC 读出。

```
ΔT_pixel ≈ α × (T_scene - T_sensor) × τ_optical / G_thermal
```

变量：
- `α` — 吸收率（VOx ~80-90%）
- `τ_optical` — Ge / 硫属玻璃透镜透过率 (~90%)
- `G_thermal` — pixel 热导（决定时间常数 ~10 ms）

NETD（noise equivalent temperature difference）是关键指标：30 mK 民用 / 5 mK 高端。

⚡ **Eureka Moment.** Thermal 不是"可见光的夜视版本"— 它是**被动黑体辐射感知**，物理本质和 RGB / NIR 完全不同。RGB 测**反射可见光强度**，thermal 测**自发热辐射**。**玻璃 RGB 透 / LWIR 阻**是因为玻璃 SiO₂ 在 8-14 µm 强吸收 — 这一个事实就让 thermal 无法做"挡风玻璃后面的车载主感官"。

### 1.3 FFC (Flat-Field Correction) — thermal sensor 的"心跳"

Microbolometer 有强 **fixed-pattern noise** 和 drift：

```
每 60-180 秒
  ↓
shutter (机械叶片) 关闭，覆盖整个 array
  ↓
sensor 看到均匀温度参考
  ↓
重新校准每个 pixel offset
  ↓
shutter 开 — 期间画面冻结 ~0.5-1 s
```

⚠️ 对 SLAM 的影响：**FFC 期间帧无效** — drone 视觉 SLAM 需要做 "FFC blackout handling" 否则 EKF 输入异常。

---

## 2 · 数学核心：NETD 与对比度 (Math Core)

📌 **Napkin Formula** (X-Ray)：能看见 ΔT = 1 K 物体需要 NETD ≪ 1 K；30 mK NETD → 信噪比 ~30 检测 1 K 温差。

### 2.1 NETD 推导

```
NETD = √(noise²_temporal + noise²_spatial) × (∂T/∂DN)

典型分解 (VOx microbolometer):
  noise_temporal ≈ 25 mK (read noise)
  noise_spatial  ≈ 15 mK (PRNU after FFC)
  total NETD     ≈ 30 mK
```

**Thermal 信号链：温度 → 辐射 → pixel 升温 → 电压 → DN.** 每段都注入有色噪声，类似 RGB camera pipeline 但物理量不同。

### 2.2 反射率污染

Thermal 测的是**辐射温度** = 自发辐射 + 反射环境辐射：

```
L_observed = ε × σT⁴ + (1-ε) × L_ambient
```

- `ε` = emissivity (人皮 ~0.98, 抛光金属 ~0.05, 玻璃 ~0.9)
- 抛光金属（车保险杠 / 工具）→ ε 低 → 主要反射环境 → thermal 失效

工业测温必须知道目标 emissivity；机器人 thermal SLAM 在金属环境下 feature unstable。

### 2.3 大气透过

```
LWIR 8-14 µm 透过率:
  距离 100 m, 50% RH, 25°C → ~95% (典型)
  距离 1 km, 雾 (1 g/m³)    → ~50% (LWIR 仍比 visible 好 10×)
  距离 1 km, 干燥           → ~80%
```

**LWIR 穿雾 / 烟比 RGB 好但不是无敌** — 大颗粒水滴（雨）/ 浓厚烟尘仍吸收。

---

## 3 · Worked example — FLIR Boson 320 (320×256, 12 µm pitch) 在 50 m 检测行人

设置（数字 `UNVERIFIED` from FLIR datasheet）:
- Resolution: 320×256
- Pixel pitch: 12 µm
- FOV: 35° HFOV
- f-number: f/1.1
- NETD: 50 mK

**几何:**
```
Angular pixel: 35° / 320 = 0.11° = 1.9 mrad
@ 50 m → 9.5 cm/pixel
行人身高 1.7 m → 18 pixels tall (Johnson criterion "detect" ≥ 1.5 pixel, "recognize" ≥ 6, "identify" ≥ 12)
```

**热对比度:**
```
人皮肤 ~308 K (35°C 表面)
室温墙 ~293 K (20°C)
ΔT ≈ 15 K
NETD 50 mK → SNR ≈ 300
完美检测，长距离尚可
```

**功耗 & FFC:**
- Boson 320 typical power ~0.5 W
- FFC 每 60 s ~0.5 s 画面冻结
- drone 视觉 SLAM 必须处理 FFC blackout

---

## 4 · 工程视角 (Engineering View)

**Lens 物理强约束.** LWIR 不能用普通玻璃透镜 — 玻璃 8-14 µm 吸收。必须用 **Ge（锗）/ ZnSe / 硫属玻璃 (chalcogenide)** — Ge 透镜 ~$50-500 / piece，是 thermal camera BOM 大头。

**Cost ladder (`UNVERIFIED`):**
- FLIR Lepton 3.5 (160×120): ~$200 OEM
- FLIR Boson 320 (320×256): ~$1500
- FLIR Boson+ 640 (640×512): ~$3500-5000
- DJI Zenmuse XT2: ~$10k
- Cooled InSb 640: $20k-100k
- 比 RGB 贵 30-300×

**功耗.**
- Lepton: ~150 mW
- Boson: ~500 mW
- Cooled MWIR: 5-20 W (Stirling cooler 主导)

**Frame rate.** Microbolometer 受 thermal time constant ~10 ms 限制 → 30-60 Hz；cooled ~200 Hz 可达。

**Mechanical FFC shutter.** 每 60-180 s 一次 0.5 s 画面冻结 — drone 系统必须 EKF 跳过该窗口。

---

## 5 · 数据与评测 (Data & Eval)

- **FLIR ADAS Dataset** — 26k thermal + RGB pairs, 标注 person/car (商用 thermal-AD)
- **KAIST Multispectral Pedestrian** — thermal + visible benchmark
- **TUM-VI thermal**, **VTOL-VIO** datasets — thermal-VIO 学界 benchmark
- 真机 drone 数据：FLIR Vue Pro / DJI XT 系列实拍 — 学界 dataset 仍稀缺

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 全黑环境工作；穿雾 / 烟 / 灰尘比 RGB 强；检测人 / 动物 / 发热物体；屋顶 / 电网 / 太阳能板巡检；消防搜救（火场 + 烟）。

**不能做什么.** 透玻璃（车窗 / 建筑窗）；区分相同温度的不同物体（"温度盲"）；高分辨率 cm 级（民用 ~mm-cm @ 1 m）；颜色信息（grayscale only）。

### Hidden Assumptions

- **场景有温差.** "全场 25°C 房间"thermal 画面接近 noise — 温差才有信号
- **emissivity 可知.** 抛光金属 / 镜面反射使 thermal 测错
- **FFC 容忍.** drone 视觉 SLAM 必须能跳过 FFC blackout
- **Ge 镜头不受冲击.** Ge 是脆性材料 — drone crash 后镜头碎裂常见
- **太阳不直射.** sensor 直对太阳 → saturation + 长时间损伤
- **环境温度稳定.** sensor housing 温度大幅变化 → drift，FFC 频率被迫提升

**失败模式：**
- **玻璃挡风.** Tesla 拒用 LWIR 的物理根因 — 挡风玻璃完全阻挡
- **太阳烧 pixel.** 热成像直对太阳 → 永久 dead pixel
- **水雾 / 大雨.** 大水滴对 LWIR 仍是 obstacle
- **NUC drift.** 长时间无 FFC → image quality 退化 30%+
- **反射金属误判.** 反射环境 → 出现"假人"（反射人体在工具上）

---

## 7 · 与相关工作对比 (Comparison)

| Sensor | 波段 | 工作条件 | 与 RGB 互补 |
|---|---|---|---|
| **RGB camera** | 0.4-0.7 µm | 需要光照 | self |
| **NIR active (850 nm)** | 0.85 µm | 主动 illumination | 强 |
| **SWIR (1.4-3 µm)** | 1.5-2.5 µm | 雾穿透中等 | 中 |
| **LWIR microbolometer** | 8-14 µm | 全条件 (不透玻璃) | 强 (热补 RGB) |
| **MWIR cooled** | 3-5 µm | 工业测温 / 军用 | 强 |
| **mmWave radar** | 4 mm | 全天候穿玻璃 | 强 (radar 测速 thermal 看人) |

⚡ **关键 insight**: thermal 和 mmWave radar 是"全天候双子" — radar 穿玻璃 + 测速 + 不被雾死，thermal 看人 / 测温 / 看到 radar 看不到的小目标。两者**绝佳互补**。

**🎙️ Interview Tip.** 被问"为什么 Tesla 不加 thermal"？— 主要物理障碍：(1) **挡风玻璃不透 8-14 µm**，sensor 必须挂车外；(2) 民用 thermal cost $200-500，但 ADAS 选定 BOM 严苛；(3) **温度盲** — 两辆温度相同的车 thermal 上几乎一样。所以 thermal 在 ADAS 是"夜间 + 雾天的 RGB backup"而非主感官 — 部分国产厂（华为 / 地平线）正在加。

---

## 8 · For the reader

- **Manipulation** — 极少用，除非 thermal-haptic（柔性机器人触觉）研究
- **Mobile robot / Ground** — 消防机器人 / 工厂巡检 / 农业（畜禽体温）核心 sensor
- **Drone** — 巡检电网 / 农业 / 搜救 / 消防核心 payload；FLIR Vue / DJI XT 是标准品
- **AD** — 夜间 / 雾天 backup，未来 5 年可能进入中高端 ADAS（截至 2026 仍未量产标配）
- **Marine** — port surveillance / 浮油检测；AUV 水下 thermal 不工作（水吸收 LWIR）

---

## References

- FLIR Boson+ Datasheet `UNVERIFIED, no DOI`
- FLIR Lepton 3.5 Engineering Datasheet `UNVERIFIED`
- DJI Zenmuse XT2 specifications
- Vollmer & Möllmann — *Infrared Thermal Imaging* (2nd ed., Wiley 2018)
- Teledyne Vue Pro / Boson product family

## Boundary

- LWIR sensor 物理 / FFC / NETD → 本文
- `crossing/sensor-stack-matrix/` — thermal vs RGB vs radar 全天候组合
- `embodiments/aerial/sensor-stack/` — thermal payload 工程集成（FFC drone EKF 处理）
- `deployment/hardware-selection/` — FLIR vs Teledyne vs Hikvision 选型
- 工业测温 / 黑体校准 → 不在本目录
- Thermal-VIO 算法 / thermal NeRF → `foundations/feed-forward-3d/` 或学界 paper dissection

*2026-05-21. v1. UNVERIFIED → v1.1 待 FLIR datasheet 核对。*

---
[← Back to sensor-physics README](./overview.md)
