# Time-of-Flight Physics for Embodied AI (具身 AI 飞行时间传感器物理拆解)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — phase vs pulsed ToF / modulation wrap-around / SPAD vs APD / multipath
> **核心定位**：厂商 datasheet 埋在小字里的 wrap-around 与多径故事 — 调制频率才是承重旋钮，"depth accuracy" 不是

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字仍需 spec-sheet 交叉核对。
**Wedge tier:** sensor-physics expansion（5 篇姊妹文中的第 2 篇）

### X-Ray opening

每个 ToF 厂商都在两种物理体制之间二选一 — **phase-detection CW**（Kinect v2、iPhone 前置、Microsoft Azure）和 **pulsed dToF**（iPhone 后置 LiDAR、车载 flash LiDAR）。盯着 datasheet 的"range up to X m"，会错过真正的 trade：CW 给你 sub-cm 精度但在 `c / (2·f_mod)` 处 wrap-around；pulsed 给你无歧义距离但 timing jitter 把精度卡在几 cm。厂商的调制频率选择默默决定了你要继承哪种 failure mode。对 sensor 工程师：不点明体制，"ToF accuracy" 是无意义的。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2010 ── PMD Technologies CamCube — CW-ToF 接近消费级
2013 ── Kinect v2 (Microsoft, 850nm CW-ToF, ~30 MHz) ── 客厅尺度的 CW
2017 ── Sony IMX556 ToF sensor ── 手机上的 BSI CW-ToF
2020 ── iPhone 12 Pro 后置 LiDAR (Sony dToF SPAD, 940nm pulsed) ── 消费级 dToF
2022 ── ams/AMS-OSRAM TMF8828 multi-zone dToF ── proximity 级 SPAD 模组
2023-25 ── 车载 flash LiDAR (Ouster DF, Innoviz, 1550nm InGaAs SPAD)
2024 ── iPhone 前置 Face ID 补充 (940nm CW-ToF 测人脸距离)
202? ── ?  下一波：gated SPAD imager、per-pixel coherent FMCW ToF
```

本文件卡在 CW-vs-pulsed 分岔点 — 这个选择决定了 wrap-around 行为、多径敏感度与 BoM tier。

---

## 1 · ToF 两种体制 — 同一个标签下的两条物理原理

📌 **Napkin Formula**：CW 用 `range_unambig = c / (2 · f_mod)`；pulsed 用 `range_floor = c · σ_jitter / 2`。§2 的所有内容都对照这两个公式来读 — CW 用 `f_mod` 拿距离换精度，pulsed 用 detector jitter 拿精度换距离。

**(a) Phase-detection CW (Continuous Wave).** 把照明器幅度在 `f_mod` (10–100 MHz) 调制。每像素 demodulator（通常 4-tap quadrature）测量回光相位延迟 `φ` → depth `d = c·φ / (4π·f_mod)`。室内距离下 sub-cm 精度。**Wrap-around**：相位在 `2π` 处回卷，距离每 `c/(2·f_mod)` 重复一次 — 30 MHz = 5 m，100 MHz 只有 1.5 m。多频解 unwrap（Kinect v2 用 3 频 `UNVERIFIED`）能扩展但把积分时间翻倍。

**(b) Pulsed dToF (direct ToF).** 发射 ~ns 激光脉冲，用 SPAD + TDC (Time-to-Digital Converter) 逐像素计时光子返回。深度 `d = c·Δt/2`。无 wrap-around（每个脉冲独立计时）。精度被 SPAD+TDC 链的 jitter 决定 — 通常 100–500 ps `UNVERIFIED` → 单脉冲 SNR 下 1.5–7.5 cm。N 个脉冲做 histogramming 回收 `1/√N`。iPhone LiDAR 每帧打 ~thousands 个脉冲。

**(c) 探测器 — SPAD vs APD.**
- **SPAD** (Single-Photon Avalanche Diode)：反向偏压**超过击穿**，单光子触发宏观雪崩。二值输出，~50 ps 计时分辨率 `UNVERIFIED`。Dead time 10–100 ns 限制高 flux 下的 pile-up。CMOS 可量产（Sony IMX591 家族 `UNVERIFIED`）。
- **APD** (Avalanche Photodiode)：击穿以下线性增益（×10–100）。模拟输出，CW 解调友好。单光子灵敏度差，但无 dead-time pile-up。

CW-ToF 系统历史上用类 APD 的 demodulating pixel（按相位 tap 做电荷分离）。Pulsed 系统用 SPAD。**Detector 选择决定体制，反过来不行。**

⚡ **Eureka Moment.** CW-vs-pulsed 之争**不是**距离之争 — 而是你的调制频率是否在工作空间内回卷。Kinect v2 客厅尺度（3 m）@ 30 MHz 装得下一个 wrap。车载 200 m @ 100 MHz 回卷 26 次 — 不可恢复；只能上 pulsed。

---

## 2 · CW vs pulsed 对比（厂商不会并排公布）

| Property | CW phase ToF | Pulsed dToF |
|---|---|---|
| Typical illuminator | LED / VCSEL, 10–300 mW avg | VCSEL / EEL, kW peak / mW avg |
| Modulation | sinusoidal 10–100 MHz | <5 ns pulse, 10–100 kHz rep rate |
| Detector | demodulating CMOS pixel (4-tap) | SPAD + TDC per pixel |
| Wrap-around | 有，`c/(2·f_mod)` | 无（per-pulse） |
| 精度（典型） | sub-cm | 1–10 cm |
| 距离（典型） | 0.3–8 m | 0.5–200+ m |
| 多径敏感度 | 高（相位混叠） | 中（first-return / histogram） |
| Ambient rejection | 需照明在 `f_mod` 上远大于 ambient | gating + BPF；SPAD dark count 限制 |
| 成本（sensor） | $5–50 | $20–500+ (SPAD array) |
| 功率 | 连续 1–10 W | 突发，平均 <1 W |
| 典型用途 | **Kinect v2, Face ID, Azure Kinect** | **iPhone LiDAR, 车载 flash LiDAR** |

预测厂商选择的规则：工作空间在可行 `f_mod` (≤30 MHz for 5 m) 下装得下一个 wrap → CW（cheap pixel，dense depth）；range > 10 m 或解 unwrap 预算付不起 → pulsed (SPAD)。

---

## 3 · Worked example — 100 MHz CW-ToF 多远才 wrap-around？

Back-of-envelope（数字 `UNVERIFIED`，仅用于工程直觉）：

```
Source:      850 nm VCSEL, 200 mW avg, sinusoidal 100 MHz amplitude modulation
Detector:    Sony-class 4-tap demod pixel, 320×240
Integration: 30 ms/frame, 30 Hz
```

- **Wrap range：** `c / (2 · f_mod) = 3e8 / 2e8 = 1.5 m`。2.0 m 处的场景点 phase-alias 到 0.5 m。整间房间被打坏。
- **降到 30 MHz：** wrap = 5 m，但相位精度退化 ~3.3×（相位噪声 σ_φ 固定；深度 = `σ_φ·c/(4π·f_mod)`）。100 MHz 精度 ~3 mm `UNVERIFIED` → 30 MHz 精度 ~10 mm。
- **多频 unwrap：** 100 MHz + 30 MHz 交错运行；类 CRT unwrap 恢复 LCM 限内的真距离同时保留 100 MHz 精度。代价：积分时间 2× → 帧率减半，或照明 duty 翻倍。
- **Pulsed 替代方案：** 500 ps jitter SPAD → 单脉冲精度 7.5 cm；1000 脉冲做 histogram → `1/√1000 ≈ 30×` 降低 → 30 Hz 下 2.5 mm，无 wrap 直到 (rep period · c / 2)。100 kHz rep → 1.5 km 无歧义。

印证 §1 → §2：CW 是对的选择**当且仅当**工作空间 ≤ wrap range，且对应频率能命中精度规格。超过 ~10 m 或多径主导时，即便 BoM 更高 pulsed 也胜出。

---

## 4 · ToF vs structured light vs active stereo（姊妹方案）

| Method | 深度信号 | 优势 | Failure mode |
|---|---|---|---|
| **Structured light** | 点阵位移三角化 | 短距 dense、便宜 | 太阳饱和、户外失效、单点失效 |
| **CW-ToF** | 调制光相位延迟 | dense、无纹理 OK、sub-cm | 多径、wrap-around、功率 |
| **Pulsed dToF** | 直接计时光子往返 | 长距、无歧义、快 | SPAD 成本、低端阵列稀疏 |
| **Active stereo**（姊妹 850nm 文） | stereo 对应 + 非信息性纹理 projector | 优雅退化、户外 OK | baseline-vs-range 取舍 |

ToF 的**无纹理表面**优势是它在 face auth 与白对白 bin-picking 中胜出的原因。Structured light 需要点之间有**对比**；ToF 不需要。而 ToF 的诅咒 — 多径 — 正是 active stereo "世界自己提供信号"路线巧妙绕开的。

---

## 5 · 多径 — ToF 标志性的 failure mode

一面墙 + 一个 corner reflector 同时把光反射到同一个像素。Phase-ToF 测的是**两个 phasor 的矢量和** → 报出一个虚假的中间深度。在墙角、亮地板、retroreflective tape 前 — ToF 系统性地说谎。缓解：

- **多频** — 不同 `f_mod` 产生不同混叠模式；联合求解。Kinect v2 路线。
- **Frequency-modulated CW**（chirp）— coherent ToF 按 Doppler/range 分离 return。Aeva FMCW LiDAR。昂贵。
- **Pulsed first-return** — 只数每个脉冲的第一颗光子；忽略二次反射。车载标准做法。
- **几何先验** — 把镜面反射体附近的像素标记为低 confidence。

Pulsed 系统受影响较少，因为 first-return gate 在时间上隔离了直接路径。CW 系统受影响最大，因为光子落到 pixel 后相位就没时间 handle 了。

---

## 6 · Hidden Assumptions — ToF 默默押注的前提

"ToF 给你深度"这个假设只在下列条件成立时稳定。当出问题时回来对一遍：

- **调制频率 >> 环境光闪烁频率。** 太阳是 DC；100 MHz 调制把它当作 common-mode 排除。但 **fluorescent / PWM-LED 环境光**在 100–1000 Hz 会和 `f_mod` 拍频，注入 ghost depth `UNVERIFIED`。
- **场景以单次反射为主。** 多径分量 <10% — 墙角、亮地板、retroreflective tape 会打破。
- **没有竞争的 ToF 源。** 同一房间里两台手机做 dToF 几乎不可能 sync；SPAD dark count 升高，histogram 变糊。假设多 sensor 间没有协调协议。
- **SPAD pile-up < detector rate.** 高 flux 场景（铬上的太阳）让 SPAD dead-time 饱和，把 histogram 朝早偏移。Pulsed 假定光子率 << 1/dead-time。
- **照明功率在使用距离上满足 IEC 60825-1 Class 1。** Pulsed kW peak 之所以可行，是因为 pulse <5 ns 且 duty <0.1% — 参见姊妹文 `active_nir_850nm_for_embodied_ai.md` §3。
- **像素电荷阱不被 ambient 灌满。** 户外 ambient 可在 `f_mod` 解出之前就把积分阱填满；需要更短积分时间或更窄 BPF。

---

## 7 · ToF vs active stereo — 选哪个

| 问题 | 选择 |
|---|---|
| 无纹理表面（白墙、薄板金属）？ | **ToF** |
| 户外 / 直射阳光？ | **active stereo**（优雅退化） |
| 消费级 BOM 下 range >5 m？ | **pulsed ToF** |
| Range <2 m，dense，便宜？ | CW-ToF |
| 容忍单点失效？ | ToF（任一） |
| 要 soft floor（projector 挂了还能 passive stereo）？ | active stereo |
| 多机器人共存？ | active stereo（多 sensor 干扰小） |

⚡ 规则：ToF 在 active stereo 做不到的位置（无纹理）给你深度，代价是多径与需要 modulation-aware 积分。Active stereo 在户外 + 优雅退化上胜出，代价是依赖表面纹理。

**🎙️ Interview Tip.** 被问"我们机器人选 ToF 还是 active stereo"？— 反问的第一句是 *"工作距离、ambient 等级、表面纹理？"* <2 m、无纹理、室内 → ToF。户外 / 灰尘 / 表面多变 → active stereo。>10 m → pulsed dToF 或 LiDAR；CW 出局。

---

## 8 · For the reader

- **Manipulation** — 短距、无纹理零件 → CW-ToF（工作空间 ≤ 1.5 m 且 ambient 受控时）；否则 active stereo (850 nm)。
- **Drone** — pulsed dToF altimeter <5 m（TMF8828 级 proximity），深度交给 passive stereo + VIO。
- **Headset / AR** — CW-ToF 做 hand-tracking 工作空间 (0.3–1 m)；无纹理皮肤让它成为对的选择。
- **Automotive long-range** — pulsed dToF SPAD，1550 nm 让 kW peak 过 Class 1（见姊妹 LiDAR 文）。

---

## References

- IEC 60825-1 — laser product safety classification
- Sony IMX591 / IMX556 ToF datasheets, `UNVERIFIED`
- ams-OSRAM TMF8828 datasheet, `UNVERIFIED`
- Microsoft Azure Kinect DK technical specs, `UNVERIFIED`
- Apple iPhone Pro LiDAR teardowns (iFixit / TechInsights), `UNVERIFIED, no DOI`
- 实战：维护者在 Autel 平台上的 sensor-stack 工作

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — band selection / Class 1（姊妹文）
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — 长距脉冲体制（姊妹文）
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment SWaP-C 应用
- `embodiments/aerial/sensor-stack/` — drone 专用部署（CW-ToF 罕见；pulsed altimeter 常见）
- 各 embodiment 的集成 + 标定见 `embodiments/<x>/sensor-stack/`；本文只覆盖物理。

*2026-05-21. v1 首版，满足 14 项 gate。UNVERIFIED → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
