# Active NIR (850 nm) for Embodied AI (具身 AI 主动近红外 850nm 选型)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — band selection / laser safety / cost
> **核心定位**：厂商综述当成"天经地义"的上游故事 — Si QE × solar dip × Class 1 安全 × cost 才是真正承重的优化轴

**Status:** v1.1 — opinionated draft。已按 AGENTS.md 14 项 dissection 模板回填 2026-05-21。标 `UNVERIFIED` 的 spec 数字仍需核对 datasheet。
**Wedge tier:** W1（5 篇 launch docs 中的第 1 篇）

### X-Ray opening

所有出货主动感测的具身 AI 厂商都收敛到 850 nm — 这是 silicon QE、solar dip 与 IEC 60825-1 Class 1 眼睛安全三条曲线**同时**过关、BOM 又吃得下的唯一点。对 sensor 工程师来说："Apple 用 940 nm 我们也用"是范畴谬误 — Apple 优化的是**连续**眼部暴露，机器人优化的是**环境光排除**。把波段选择当成性能排名，会错过真正在交换的东西。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2010 ── Kinect v1 (PrimeSense, 850 nm structured light) ── NIR 主动感测进入消费级
2013 ── Kinect v2 (850 nm CW ToF)
2017 ── iPhone X Face ID (940 nm) ── on-skin 连续暴露 → 波段切换
2018 ── Intel RealSense D-series (850 nm active stereo) ── 机器人户外
2023-25 ─ 车载 1550 nm SPAD 浪潮 (Luminar, Innoviz, Hesai-FT) ── InGaAs kW 脉冲
2024 ── Apple Vision Pro (940 nm eye-tracking) ── 连续开启再次确认 940
202? ── ?  下一批候选：1380 nm SWIR 用于 AD 短距、905→940 SPAD 迁移
```

这个 wedge 卡在 850-vs-940 分岔点上 — 大众市场具身 AI 中唯一仍有争议的位置。

---

## 1 · 光谱物理初识 (Spectral physics primer / Overview)

有三条曲线共同决定选择；只看一条，就会得出"940 nm 因为 Apple"这种结论而打不到距离。

📌 **Napkin Formula**：`band_value = (Si_QE × ambient_rejection × safety_budget) / cost`。§2 的每一格都要对照这个公式来读 — 脉冲机器人 850 nm 胜出；on-face 连续 940 nm 胜出；1550 nm 只在 BOM 能承担 InGaAs 时才入场。

**(a) Silicon QE.** FSI CMOS 在 ~550 nm 达峰，超过 1000 nm 后急降（光子能量 < Si 间接带隙）。Datasheet `UNVERIFIED`：850 nm ~35–50%，940 nm ~15–25%，超过 1100 nm 接近 0。BSI 提升约 1.5×；NIR-enhanced（STARVIS-2）把 850 nm 推到 ~60% `UNVERIFIED`。超过 1100 nm = InGaAs = 50–100× cost。

**(b) Solar irradiance (AM1.5).** 大气在 760 nm (O₂)、940 nm (H₂O)、1380 nm (H₂O) 啃出吸收凹陷。850 nm 是**浅**凹（比 NIR baseline 低 ~30% `UNVERIFIED`）；940 nm 是**深**槽 — 长曝光的消费级产品偏好它。

**(c) Eye safety — IEC 60825-1.** MPE 在 700 nm 以后陡升；cornea+lens 透过且眨眼反射不再触发。850 nm 在 100 ms 曝光下，Class 1 的时间平均上限约 1 mW/cm² `UNVERIFIED`；940 nm 大约宽松 2×；1550 nm 宽松 ~1000×（cornea+lens 几乎全吸收）— 这就是 1550 nm LiDAR 可以打到 kilowatt 的根本原因。

⚡ **Eureka Moment.** 850-vs-940 厂商分岔是**暴露时长**之争，不是性能之争 — 脉冲 <10 ms 偶发观看者 = 850 nm，连续观看者 = 940 nm。其他所有轴都是这个选择的下游。

---

## 2 · 波段对比（厂商不会并排公布）

| Band | Si QE | Ambient rejection | Eye-safety | Cost | Typical use |
|---|---|---|---|---|---|
| **760 nm** | ~55% | good (O₂ dip) | NIR 中最紧 | cheap | 罕用 — 红光漏色 |
| **808 nm** | ~50% | poor | 紧 | cheap | 激光泵浦，不做感测 |
| **850 nm** | ~40–50% | 中等 | 可用，脉冲 | cheap | **RealSense, Kinect, Skydio** |
| **940 nm** | ~20% | strong (H₂O dip) | 宽松 ~2× | cheap | **Face ID, Vision Pro** |
| **1380 nm** | ~0% Si | 最强 dip | 很宽松 | InGaAs | 大气，非 depth |
| **1550 nm** | 0% Si | strong | 宽松 ~1000× | InGaAs 50–100× | **车载 flash LiDAR** |

预测厂商选择的规则：脉冲 <10 ms、偶发对人 → 850 nm（找回 QE）；连续对人眼 → 940 nm（用 QE 税换累积剂量）。**Apple 选 940 nm 是因为连续佩戴下安全预算会累积，不是为了性能。**

---

## 3 · Worked example — 100 mW peak, 850 nm, 10 ms pulse: 30 cm 是不是 Class 1？5 cm 呢？

Back-of-envelope（数字 `UNVERIFIED`，仅用于工程直觉）：

```
Source:  100 mW peak, 10 ms pulse, 1 Hz repetition (~1% duty)
Beam:    20° × 20° flood at 850 nm (VCSEL + diffuser)
Aperture stop: 7 mm (IEC pupil model)
```

- **30 cm：** flood 散到 ~10×10 cm² → ~1 mW/cm² peak，1% duty → 时间平均 ~10 µW/cm²。Class 1 上限量级 ~1 mW/cm² `UNVERIFIED`。**裕量 ~100×，Class 1。**
- **5 cm（用户把鼻子凑过来）：** projector 孔径填满 7 mm 瞳孔 → 瞬时 ~100 mW/cm²，时间平均 ~1 mW/cm²。**踩在 Class 1 边缘。**
- **940 nm** 买到 ~2× 宽松 MPE → 5 cm 出货还有裕量。**1550 nm** 买到 ~1000× → 100 W peak 仍是 Class 1（但 InGaAs 50–100× cost）。

印证 §1(c) → §2：30 cm 距离的机器人在 850 nm 下 Class 1 轻松；on-face 连续暴露不行，这正是厂商切到 940 nm 的位置。

---

## 4 · 实战硬件类型 (Hardware archetypes in the wild)

**Structured light.** VCSEL 投射伪随机点阵；单 camera 读取形变。Kinect v1 (PrimeSense, 850 nm), Face ID (940 nm, ~30k dots)。dense depth，无时间混叠。户外迅速失效，realistic projector power 下距离上限 <4 m。

**ToF.** Modulated illuminator + demodulating pixel 量相位延迟。Kinect v2 (850 nm CW), iPhone LiDAR (940 nm pulsed SPAD), 车载 flash LiDAR (1550 nm InGaAs SPAD, kW peak)。对无纹理表面有效。多径、调制 wraparound、耗电。

**Active stereo.** 两个 camera + 一个**非信息性** IR speckle projector — 后者为 stereo matching 制造纹理。Intel RealSense D-series (D435/D455 — 850 nm)；Skydio 的避障感测也在这一家族。优雅退化 — projector 失效，仍可走 passive stereo。Baseline-vs-range 标准取舍。

**优雅退化**正是 active stereo 在机器人领域胜出的原因。Structured light 与 ToF 都有**单点失效**风险；active stereo 有 soft floor。

---

## 5 · 嵌入式 BPF — 默默最重要的部件

每个量产主动 sensor 都在前面贴一片窄带 BPF。10 nm FWHM BPF @ 850 nm 排除约 95% 的环境太阳光功率 `UNVERIFIED` — 这是让户外主动感测可行的关键。

- **20 nm FWHM：** $1–2，~85% rejection。对 VCSEL 漂移宽容。
- **10 nm FWHM：** $3–6，~95%。户外机器人标准选择。
- **5 nm FWHM：** $10+，会和 VCSEL 热漂移较劲 — 见 §6。

BPF 必须 angle-of-incidence 稳定；进入宽 FOV 镜头的光线最大可达 30° 入射，便宜 BPF 在 off-axis 会蓝移。高端模组用 telecentric 光学或 angle-tuned stack。

---

## 6 · 只有踩过坑才知道的 failure modes

**两个 850 nm projector 互相串扰。** 两台 RealSense 面对面会把对方的 pattern 喂进自己的 correspondence search。缓解：时分复用、空间 pattern 唯一性、或关掉一个。多机器人需要协调协议 — 来自 Autel 工程经验。

**铬反射 / 湿沥青 / 保险杠的太阳反射。** 镜面反射体把太阳染色的 blob 反射回来，无视 BPF 直接饱和 — 全日光打到镜面上的 in-band 分量仍然压过 projector。只有 HDR pixel（Sony IMX490 一脉 `UNVERIFIED`）+ 动态曝光能救。

**VCSEL 中心波长热漂移。** ~0.06 nm/°C `UNVERIFIED`。60°C 跨度 → ~4 nm 漂移。配 5 nm BPF，热边光子直接掉一半。BPF 至少 ≥10 nm FWHM、给 VCSEL 做热稳定、或接受 duty-cycle 惩罚。

**Projector 点的 blooming。** 廉价 rolling-shutter sensor 会把亮 return 拖成竖直 ghost line。改用 global-shutter 或 BSI-anti-blooming pixel 解决。

### Hidden Assumptions — 850 nm 默默押注的前提

850 nm 收敛只在下列假设全部成立时稳定。当某项被打破时回来看这份清单：

- **Si-sensor 可得性。** 850 nm QE ≥35% 的 commodity CMOS 持续量产。供应冲击会把 BOM 推向 InGaAs。
- **BPF 角度稳定性。** 宽 FOV 镜头 (≤60° HFOV) 配的 BPF 在 30° AOI 下蓝移不超过几 nm。Fisheye 会打破。
- **VCSEL 热包络。** 外壳保持 emitter <60°C；户外曝晒会让 BPF / VCSEL 漂移失配。
- **多机器人非协调情况罕见。** 一间房内没有 5 台 RealSense；一旦不成立，cross-talk 主导。
- **Solar baseline。** AM1.5 户外；高原或雪地高反照率可令环境光翻倍。
- **光学元件供应。** Narrow BPF + 850 nm VCSEL 维持 commodity；供应冲击会把产品迁到 808 nm 或 940 nm。

---

## 7 · 跨 embodiment 比较 + interview tip

| Embodiment | Band pick | 选这个波段的 one driver | 为什么不选别的 |
|---|---|---|---|
| **Manipulation (tabletop)** | 850 nm active stereo | <2 m 工作空间，BOM 容得下 projector，室内环境光 | 940 nm 浪费 QE；1550 nm BOM 不可能 |
| **Drone** | 通常 passive（不开主动） | 1–3 W projector 税咬死 250 g 功率预算 | 850 nm 只在室内/暮光合理（Skydio） |
| **AR / VR headset** | 940 nm eye-tracking | 连续暴露剂量预算累积 | 850 nm Class 1 在 5 cm 裕量太紧 |
| **Phone face auth** | 940 nm structured light | on-skin 连续；<30 cm 距离 | 850 nm 需更低功率 → 点数减少 |
| **Automotive long-range** | 1550 nm SPAD | kW peak 仍 Class 1；>200 m | 905 nm 在保险杠处 Class 3R；850 nm 距离受限 |

经验：在 headset，**暴露时长**主导；在机器人，**环境光排除**主导。

**🎙️ Interview Tip.** 被问"为什么不全用 1550 nm"？— 1550 nm 需要 InGaAs（50–100× cost）；只有 kW 脉冲的车载用例付得起这个账。

---

## 8 · For the reader

- **Manipulation** — active stereo 850 nm；旋钮是 BPF FWHM vs VCSEL 热包络。
- **Drone** — passive stereo + VIO。Active 850 nm 仅用于室内/暮光；1–3 W 税。
- **Headset / on-face** — 940 nm。别和剂量预算较劲。
- **AD / long-range** — 1550 nm 如果 BOM 吃得下 InGaAs；905 nm 用于短距 cost tier。

---

## References

- IEC 60825-1 — laser product safety classification
- Hamamatsu / Sony / OmniVision CMOS QE datasheets；Lumentum / II-VI VCSEL primers
- Intel RealSense D400 whitepapers
- 实战：维护者在 Autel 的 sensor-stack 工作

## Boundary

- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — power/cost/range trades
- `embodiments/aerial/sensor-stack/` — why drones skip 850 nm
- `deployment/hardware-selection/` — BOM reasoning
- 模组集成 + 标定见 `embodiments/<x>/sensor-stack/`

*2026-05-21. v1.1 backfill. UNVERIFIED → v1.2 datasheet 引用。*

---
[← Back to sensor-physics README](./README.md)
