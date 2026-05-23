# RGB Camera Imaging Pipeline (RGB 相机成像管线 — CMOS / Bayer / 噪声 / 畸变模型)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — CMOS QE / Bayer demosaic / 噪声分解 / 镜头光学 / 三种相机畸变模型
> **核心定位**：所有视觉算法都默认"RGB 图像是 ground truth"，但 photon→pixel 这条管线里每一段都在注入误差 — shot noise / read noise / FPN / demosaic 假色 / radial 畸变 / rolling shutter skew 一个都不能丢。学界综述把这段当"已解决"，但 SLAM 系统失败 60% 落在这里。

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的 spec 数字需 datasheet 交叉核对。
**Wedge tier:** sensor-physics expansion（D 桶 RGB camera 奠基文）

### X-Ray opening

RGB 相机是具身 AI 里最便宜也最被低估的 sensor — 一颗 $5 的 OV5640 模组卷起一条 photon → photodiode → ADC → Bayer → ISP → JPEG 的物理管线，每一段都向 SLAM / VLA pipeline 注入有色噪声。"我们用了 RealSense"或"我们用了 GoPro"在 sensor 工程上不是描述 — 真正的描述是 QE 60%? 65 dB dynamic range? rolling shutter 33 ms readout? Brown-Conrady k1=-0.28? 把 RGB 当成"已解决的输入"是 SLAM 系统 60% failure 的根源 — 实际上 photon 数被泊松统计 / 镜头 MTF 衰减 / Bayer demosaic 假色 / ISP gamma 压缩反复揉过，而 VIO / 3DGS / VGGT 都假设输入是线性辐射场。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1969 ── Bell Labs CCD (Boyle / Smith, Nobel 2009)
1993 ── CMOS APS (Eric Fossum, JPL) ── 移动相机时代
2008 ── BSI CMOS (OV5650 / IMX081) ── QE 跨过 50%
2014 ── Sony IMX stacked CMOS ── pixel + logic 垂直集成
2016 ── HDR pixel (IMX390) ── 单帧 120 dB
2020 ── Quad-Bayer (IMX700 / GN1) ── binning + full-res 双模
2022 ── Sony IMX900 全局快门 + HDR ── 工业 / 机器人普及
202? ── ?  event + RGB 双模 / 单光子 SPAD imager
```

---

## 1 · CMOS photodiode → 电压：量子效率与饱和

📌 **Napkin Formula**：`SNR = signal / √(shot² + read² + DSNU² + PRNU²)`，其中 shot = √(QE × photon_count)。低光下 shot noise 主导（信号本身的泊松统计），高光下 PRNU（Photo-Response Non-Uniformity，像素响应不均）主导。

**(a) Quantum Efficiency (QE).** Silicon 光电二极管对 550 nm 绿光峰值 QE 约 60%（BSI，front-side illuminated 约 40%），950 nm 衰退到 ~15%，>1100 nm 接近 0（光子能量低于 Si 带隙）。Datasheet `UNVERIFIED`：Sony IMX477 (RPi HQ Cam) 峰值 ~67%；OV5640 ~50%。

**(b) Full-well capacity.** 单像素电荷井容量。1 µm 像素约 2000–5000 e⁻，2.4 µm 像素 10k–30k e⁻，4.6 µm 工业像素 40k–80k e⁻ `UNVERIFIED`。**直接决定 dynamic range 上限** — Sony IMX296 全局快门 (3.45 µm pixel) `UNVERIFIED` 约 13000 e⁻ → 65 dB linear DR。

**(c) Read noise.** 像素读出链路（source follower + ADC）的电子噪声。Floor 1–2 e⁻ rms（CMS / 多采样 ADC）到 5–10 e⁻ rms（工业 sensor）。**决定 low-light floor** — read noise 5 e⁻ + shot noise 5 e⁻ → SNR=1 在约 25 photons / pixel / frame。

**(d) FPN = DSNU + PRNU.** DSNU (暗电流像素间偏差) — 温度敏感，每 7°C 翻倍 `UNVERIFIED`，室温长曝光 (>100 ms) 可见。PRNU (像素增益偏差) ~1% rms，flat-field 校准可消除但移动 SLAM 几乎不做。

⚡ **Eureka Moment.** RGB 相机不是"图像 sensor"而是**电荷积累器** — full-well capacity / read noise / DSNU 共同框定一个 SNR 漏斗，所有下游算法都在这个漏斗的有效宽度内工作。Dynamic range 不是 ISP 决定的而是物理决定的；low-light SLAM 失败几乎总能追到 read noise floor。

---

## 2 · Bayer 颜色滤波阵列与 demosaic

| Pattern | Layout | Vendor | 特性 |
|---|---|---|---|
| **RGGB** | 经典 2x2, 50% green | Sony / OV / Samsung 主流 | 标准 demosaic 工具链 |
| **BGGR** | 同尺寸不同相位 | 部分 Aptina | demosaic 算法等价 |
| **GRBG / GBRG** | 同尺寸不同相位 | 少数厂商 | 等价 |
| **X-Trans** | 6x6 非周期 | Fujifilm | 减少 moiré，但 demosaic 算法专有 |
| **Quad-Bayer** | 4x4 单色微块 | Sony IMX700 / Samsung GN1 | binning → 高信号；full-res → demosaic 复杂 |
| **RYYB** | red + yellow + blue | Huawei P30 | 高 QE 但白平衡难 |

📌 **关键事实**：CMOS 本身**不是彩色**的 — 它对所有可见光都响应。颜色完全来自镜头与像素之间的微透镜 + 染料滤光阵列。Demosaic 算法（bilinear / Malvar / Hamilton-Adams）从单通道 Bayer raw 推断 RGB 三通道 — **2/3 的颜色信息是算法生成的**，不是测量来的。

**Demosaic 假色 (color fringing).** 锐利边缘周围彩色光晕 — SLAM feature detector 在 demosaic 边缘上**误报特征点**。专业 SLAM 通常**只用 green 通道**或转灰度。

**OLPF (Anti-aliasing filter).** birefringence 滤光片散射 2x2 像素以避 moiré。手机 / 工业相机为成本省掉 → 条纹布料 / 砖墙 moiré 显著 → SLAM 误匹配。

---

## 3 · Lens optics — MTF / FOV / aperture

| Property | 公式 / 单位 | Drone 典型 | Manipulation 典型 |
|---|---|---|---|
| FOV (horizontal) | `2·atan(sensor_w / 2f)` | 90–150° (fisheye) | 60–90° |
| Focal length | f (mm) | 2.8 mm | 6–8 mm |
| Aperture | f/N = f / D | f/2.0–f/2.8 | f/1.8–f/4 |
| MTF50 | line pairs / mm | 50–80 lp/mm | 80–150 lp/mm |
| Vignetting | falloff at corner | -1 to -3 EV | -0.5 to -2 EV |

**MTF (Modulation Transfer Function).** 镜头对空间频率的传递曲线 — DC 处恒为 1，高频处衰减。**MTF50** = 对比度衰减到 50% 的空间频率，工程界常用单一数字描述清晰度。便宜镜头 MTF50 在边缘骤降（角分辨率 → 一半）；fisheye 镜头中心可能 100 lp/mm 而边缘 30 lp/mm。

**Aperture / f-number.** 光圈面积 ∝ 1/N²。f/1.4 → f/2.8 = 4× 光通量减少；曝光时间补 4×。Aperture **小**时 diffraction limit 开始主导 — f/16 在可见光下衍射圆 ~10 µm，已经超过 1 µm 像素的 Nyquist，**等效采样率丢失**。

**Vignetting.** cos⁴(θ) 自然 falloff + 物理遮挡 + sensor 微透镜接收角不匹配。Fisheye 镜头边缘可达 -3 EV — SLAM 边缘特征**信噪比**比中心低 8×。

---

## 4 · 三种相机畸变模型

具身 AI / SLAM / 3D 几何**必须**正确选模型，否则 reprojection error 在边缘累积。

| 模型 | 适用 FOV | 参数 | 公式（径向） |
|---|---|---|---|
| **Pinhole + Brown-Conrady** | <90° | k1, k2, k3, p1, p2 | `r' = r·(1 + k1·r² + k2·r⁴ + k3·r⁶) + tangential` |
| **Fisheye Kannala-Brandt** | 90–200° | k1, k2, k3, k4 | `θ' = θ·(1 + k1·θ² + k2·θ⁴ + k3·θ⁶ + k4·θ⁸)` |
| **Omnidirectional MEI / Scaramuzza** | 360° (catadioptric) | poly + mirror geom | 多项式 + 反射面 |

**Brown-Conrady.** OpenCV / ROS 默认，<90° FOV 精度高。radial k1 (barrel/pincushion)，tangential p1/p2 (lens-sensor tilt)。手机相机 k1 ≈ -0.2~-0.3；工业镜头 ≈ -0.05。

**Kannala-Brandt fisheye.** 用 θ (入射角) 建模 — >90° FOV 必须用，r 在 90° 发散。Drone 向下 / FPV 几乎全 fisheye；**Brown-Conrady 拟合 fisheye 边缘累积 5–10 px reprojection error** → VIO 失稳。

**Omnidirectional.** Scaramuzza 多项式 / cube-map。ORB-SLAM3, VINS-Fusion 支持。

⚡ **关键**：选错模型 = 边缘几何**系统 bias**，outlier rejection 滤不掉，是 fisheye SLAM 失败最常见根因。

---

## 5 · Auto exposure / AWB / 控制环

**AE.** 测光 → 18% gray PID → exposure + gain + aperture。30–60 Hz 环。**问题**：SLAM 要 photometric consistency；AE 跳变 → DSO / LSD-SLAM 失稳。**对策**：fix exposure / log AE 元数据。

**AWB.** gray-world / white-patch 假设 → 三通道增益。大面积单色 (蓝天 / 红墙) 色温估错 → color-based SLAM/VLA 降级。

**Low-light.** AE 撞曝光上限 (1/30s drone 防 blur) → gain 拉 16× → SNR 降 16× → shot noise 主导 → SLAM feature 失稳。**drone 夜飞失败的根因**。

---

## 6 · Worked example — 1 lux 低光 1/30s 曝光下的 SNR

```
Setup:    OV5640 class sensor, 2.0 µm pixel, QE=50%, read noise=3 e⁻
Lens:     f/2.0, FOV 90°
Scene:    1 lux 整体照明（昏暗室内 / 暮光）
Exposure: 1/30 s, gain 8×
```

光通量推导（数字 `UNVERIFIED`，量级估计）：

```
1 lux = 1 lm/m² ≈ 1.46 mW/m² at 555 nm (peak luminous efficacy)
镜头 f/2.0 → image plane irradiance ≈ scene_irradiance / (4·N²) = 1.46/16 ≈ 0.09 mW/m²
单像素面积 = (2.0e-6)² = 4e-12 m²
单像素功率 ≈ 4e-12 × 0.09e-3 ≈ 3.6e-16 W
单 photon 能量 ≈ 3.6e-19 J @ 555 nm
photon rate ≈ 1000 / s
1/30 s 曝光 → ~33 photons / pixel
QE 50% → ~17 e⁻ signal
```

**SNR 计算**：

```
shot noise = √17 ≈ 4.1 e⁻
read noise = 3 e⁻
gain 8× 后 read noise 等效不变（pre-gain），但 ADC 量化加进来
SNR ≈ 17 / √(17 + 9 + 1) ≈ 3.3
```

SNR ~3 已经是 SLAM feature detector 的临界线（ORB 要求 ~5–10）。**这就是为什么 drone 夜飞需要 IR illuminator 或更大像素 (4.6 µm) sensor**。同样场景换 4.6 µm pixel → 单像素面积 5.3×（pitch² 比 4×，加 fill factor），SNR 约升 √5.3 ≈ 2.3× → SNR ~7.5，恢复可用。

---

## 7 · Hidden Assumptions — RGB 相机管线的隐性前提

下游算法（SLAM / VLA / 3DGS）几乎都默认这些条件，破了就破：

- **Linear radiance assumption.** 多数算法假设 pixel value 与 photon count 线性。但 JPEG / ISP 通常 gamma 压缩 (sRGB γ≈2.2) — direct photometric SLAM 必须用 raw 或反 gamma。
- **Frame-to-frame photometric consistency.** AE / AWB 锁定。Drone 飞过窗户 → 自动调亮 → 帧间增益跳变 → DSO 失稳。
- **Negligible rolling shutter skew.** 静态 / 慢速场景 OK；fast yaw + RS sensor → 几何畸变 ~0.5 px / ms rolling time × yaw rate。详见 `rolling_vs_global_shutter.md`。
- **Bayer demosaic 不引入假特征.** 高 spatial frequency 区（栅格 / 砖墙）实际上 demosaic 会引入 → SLAM 用 green-only 或灰度。
- **Distortion model 完整覆盖.** 用 pinhole 模型拟合 fisheye → 边缘累积偏差。
- **Read noise / DSNU 在 SLAM 工作温度范围稳定.** -20°C 户外冬季 vs +50°C 引擎舱 — DSNU 可能跳 4×，影响 low-light 行为。
- **Lens vignetting / MTF 假设 isotropic.** 实际边缘比中心暗 2 EV + MTF 半 → SLAM 边缘 outlier 率高。
- **Color calibration 与 deployment 一致.** 工厂校准白平衡 vs 户外日光 vs 钨丝灯室内，color-based VLA 在域迁移时降级。

破其中一条都会让"我们的 SLAM 在 EuRoC 上 100%"变成"户外阳光下飘了 2 m"。

---

## 8 · 跨 embodiment 比较 + interview tip

| Embodiment | RGB 相机选择 | one driver | 为什么不选别的 |
|---|---|---|---|
| **Manipulation (tabletop)** | RealSense D435 RGB (OV9282) + RGGB Bayer | 室内固定光照，AE 锁定可行 | 高端 global shutter 浪费成本 |
| **Humanoid head** | Stereo IMX296 global shutter | 头部 yaw 快，RS 不可接受 | rolling shutter geometric error 累积 |
| **Drone FPV / Avoidance** | Mono fisheye (OV9281 GS, KB model) | 宽 FOV / 高速 / 室外阳光 | RS 在 fast yaw 下不可用；pinhole 模型 FOV 不够 |
| **Drone cinematic** | RS + OLPF (Sony IMX477) | 画质优先，机身云台稳像 | GS 工业 sensor 像质差 |
| **AD front cam** | HDR pixel (IMX390) 8 MP RS | 隧道出口 120 dB DR 强制 | 普通 60 dB sensor 高光 / 阴影同帧爆 |
| **AR/VR headset** | Stereo IMX681 GS + LRC | 头部 6DoF 快，RS skew 不可接受 | RS 在快速 head motion 下 VIO 失稳 |

经验：embodiment **运动学**决定 GS vs RS；**光照动态范围**决定 sensor tier；**FOV** 决定 distortion 模型。

**🎙️ Interview Tip.** 被问"为什么 SLAM 在阳光下飘"？— 三层答：(1) AE 不锁 → photometric inconsistency；(2) HDR 不足 → 阴影区 SNR 崩；(3) demosaic 在饱和区生成假色 / 假边缘 → feature outlier。一次性命中 sensor / ISP / 算法接口三层。

---

## 9 · For the reader

- **Manipulation** — D435 OV9282 RGGB 够用，AE/AWB 锁室内即可。
- **Humanoid / Drone fast-yaw** — global shutter 强制（IMX296 / OV9281 类），fisheye 用 Kannala-Brandt。
- **AD** — HDR pixel 强制（IMX390 类），120 dB+ 是入场票。
- **AR/VR** — 头部 6DoF VIO，GS + sync 强制。
- **任意 embodiment 夜飞 / 暮光** — sensor pixel pitch ≥4 µm 或加 NIR illuminator（见 `active_nir_850nm_for_embodied_ai.md`）。

---

## References

- Eric Fossum, "CMOS Image Sensors: Electronic Camera-On-A-Chip" (IEEE T-ED 1997) — CMOS APS 奠基论文
- Sony IMX296 / IMX477 / IMX390 datasheets `UNVERIFIED`
- OmniVision OV5640 / OV9281 datasheets `UNVERIFIED`
- Kannala & Brandt, "A Generic Camera Model and Calibration Method" (TPAMI 2006)
- Brown D.C., "Decentering Distortion of Lenses" (Photogrammetric Eng. 1966)
- OpenCV `cv::calibrateCamera` / `cv::fisheye` 文档

## Boundary

- `rolling_vs_global_shutter.md` — RS skew geometric 推导
- `stereo_camera_geometry_physics.md` — RGB 用于 stereo 的 baseline / disparity
- `polarization_sensing_for_3d.md` — RGB 之上加偏振滤光
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — RGB 在 6 embodiment 上的取舍
- `embodiments/aerial/sensor-stack/` — drone RGB 选型实战
- `deployment/hardware-selection/` — production BOM 决策

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
