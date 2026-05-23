# 偏振传感器 3D 感知 (Polarization Sensing for 3D)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 像素级 polarizer CMOS (Sony IMX250MZR / IMX264MZR)，玻璃 / 反光物体感知
> **核心定位**：偏振是 robotics 长期忽视的"第四光学维度"（强度 / 颜色 / 偏振 / 时间），玻璃 / 反光 / 透明物体是 stereo / ToF / LiDAR 共同盲区 — 偏振是物理上唯一能直接打到的解

**Status:** v1 — opinionated draft，14-item dissection 范式。数字 `UNVERIFIED`。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) 自然光是非偏振的，但被表面**反射后**会变成部分偏振 — 偏振方向 (AOLP) 与偏振度 (DOLP) 编码了表面**法向量**。Sony `IMX250MZR` (2018) 在每 2×2 像素 block 内集成 0°/45°/90°/135° polarizer → 单次曝光 + 单 sensor 就能拿到完整 Stokes parameters。(b) Apple Face ID 隐含用偏振 reject 屏幕反射光（屏幕光是高度偏振的）；polarization-aware depth 在透明杯子、镜面金属、湿地面上**正确**而 stereo / ToF **失语**。(c) 对 sensor 工程师：偏振不是"高端选项"，是 robotics 玻璃 / 反光 / 透明物体盲区的物理解 — 学术界已有 10 年研究，工业仍未普及。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1808 ── Malus 发现反射光偏振（玻璃板实验）
1852 ── Stokes parameters 提出（描述任意光偏振状态）
1956 ── Fresnel 方程详化 — 反射偏振与入射角关系
1990s ── Polarization imaging 学术研究开始（Wolff, Schechner）
2000 ── DOLP / AOLP 用于 shape-from-polarization 论文涌现
2018 ── Sony `IMX250MZR` — 5 MP CMOS + 像素级 polarizer grid 量产
2019 ── Lucid Vision Labs `Phoenix` / `Triton` polarized camera 工业级
2020 ── Sony `IMX264MZR` 2.3 MP global shutter 版本
2022 ── Apple Face ID 文献暗示用偏振信息 reject 屏幕欺骗 `UNVERIFIED`
2023 ── Polarization-aware NeRF / 3DGS 学术涌现（玻璃、反光建模）
2024 ── Tesla / Mobileye 测试偏振 sensor 用于 wet-road 检测 `UNVERIFIED`
        ── 你在这里 (2026) ──
?    ── 偏振 + ToF 融合 sensor 商用？$30 polarized sensor 进入消费？开
```

工业落地慢的原因：学术界给的"shape-from-polarization"在受控环境完美，**自然光照下偏振信号噪声大** — 工程上需要 active polarization + ML 才稳。

---

## 1 · 偏振物理初识 (Polarization Physics Primer / Overview)

📌 **Napkin Formula** (X-Ray)：

```
S = [S0, S1, S2, S3]  (Stokes parameters)
DOLP = √(S1² + S2²) / S0    # 偏振度 0–1
AOLP = 0.5 × atan2(S2, S1)  # 偏振方向 -90° to +90°
```

DOLP 接近 0 = 非偏振（自然光、漫反射）；DOLP 接近 1 = 完全偏振（镜面反射近 Brewster 角）。AOLP 给方向。两者组合编码表面法向量。

### 1.1 像素级 polarizer 网格架构

Sony `IMX250MZR` 把传统 Bayer color filter array 升级 — 2×2 block 内四个像素各覆盖 0° / 45° / 90° / 135° 方向的 wire-grid polarizer。单次曝光后从四个相邻像素直接算 Stokes：

```
S0 = (I_0° + I_45° + I_90° + I_135°) / 2       # 总强度
S1 = I_0° - I_90°                              # 水平 vs 垂直
S2 = I_45° - I_135°                            # 45° vs 135°
S3 ≈ 0 (大多数情况，圆偏振 sensor 才测)
```

代价：空间分辨率减半（2×2 block → 1 polarization sample），fill factor 略降，对准精度要 < 0.1° otherwise crosstalk。

⚡ **Eureka Moment.** 偏振相机不是"加滤镜"，是把"四帧不同 polarizer 角度照片"压进**单次曝光的单 sensor** — 这让动态场景的偏振成像变得可行。Lucid Phoenix 之前的偏振相机必须机械旋转 polarizer 拍四张，无法用于运动机器人；像素级 polarizer 让 robotics 落地。

### 1.2 反射偏振机制 — Fresnel 方程

入射自然光被表面反射时，**p 偏振分量**（平行入射面）与 **s 偏振分量**（垂直入射面）反射率不同：

```
R_s = |((n1·cosθi - n2·cosθt) / (n1·cosθi + n2·cosθt))|²
R_p = |((n1·cosθt - n2·cosθi) / (n1·cosθt + n2·cosθi))|²
```

在 **Brewster 角** θ_B = arctan(n2/n1)（玻璃 ~56°，水 ~53°）处 R_p = 0，反射光**完全 s 偏振** → DOLP = 1。这是偏振检测玻璃 / 水面的物理基础。

### 1.3 信息流

```
非偏振入射光 ─→ 表面 ──┬─→ 漫反射部分 (DOLP ~ 0)
                       │
                       └─→ 镜面反射部分 (DOLP 高，AOLP 与入射面对应)
                                              │
                                              ▼
                                  Pixel-grid polarized sensor
                                              │
                                              ▼
                                  4 frames @ 0°/45°/90°/135°
                                              │
                                              ▼
                                 Stokes → DOLP / AOLP map
                                              │
                                              ▼
                                  surface normal estimate (法向量)
                                              │
                                              ▼
                          + 主动 stereo / ToF → robust depth on glass/metal/water
```

---

## 2 · 数学核心 — Shape-from-Polarization (Math Core)

**目标**：从 DOLP / AOLP 还原表面法向量。

**简化模型（漫反射主导，光滑介质）**：

```
DOLP = ((n - 1/n)² × sin²θ) / (2 + 2n² - (n + 1/n)² × sin²θ + 4cosθ·√(n² - sin²θ))
AOLP = φ (azimuth of surface normal projected on image plane)
```

其中 θ 是 zenith 角（normal 与视线的夹角），φ 是 azimuth，n 是折射率。

**变量说明**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `n` | 表面折射率 | 玻璃 1.5；水 1.33；塑料 ~1.4–1.6 |
| `θ` | normal 与视线夹角 (zenith) | 0–90° |
| `φ` | normal 投影方位 (azimuth) | 0–360° |
| `DOLP` | 偏振度 | 0–1 |
| `AOLP` | 偏振方向 | -90° to +90° |

**π-ambiguity**：AOLP 在 -90°/+90° 等价，所以 φ 是 mod π 的；需要额外约束（多视图、active polarization、ML 先验）解决。

**直觉**：

- DOLP → 给 zenith θ
- AOLP → 给 azimuth φ
- 合起来 → 表面法向量
- 但 π-ambiguity + 漫反射 vs 镜面反射 model 选择不当 → 系统误差大

---

## 3 · Worked Example — 玻璃杯偏振 vs 木桌偏振

```
场景: 室内自然光照
- 玻璃水杯 (n = 1.5)，曲面法向量与视线夹角 ~50°
- 木桌 (n = 1.5 但表面粗糙，主导漫反射)
- 不锈钢勺子 (镜面金属，强偏振)
```

预期信号：

| 表面 | DOLP | AOLP | 解释 |
|---|---|---|---|
| **玻璃杯弯曲表面** | 0.4–0.8 高 | 沿曲面变化 | Fresnel 镜面反射主导，接近 Brewster 角处峰 |
| **木桌（漫反射）** | 0.05–0.15 低 | 噪声大 | 漫反射几乎不偏振 |
| **不锈钢勺** | 0.6–0.95 极高 | 沿勺面平滑 | 金属反射强偏振 |
| **白墙** | 0.05–0.10 极低 | 噪声 | 漫反射 |
| **手机屏幕** | 0.7–0.9 高 | 与屏幕生产方向对应 | LCD 输出偏振光 |

**对比 stereo depth：**

- 玻璃杯：stereo disparity 跳跃 / 无信号 → depth NaN；偏振 DOLP 高 + AOLP 平滑 → 表面法向量可恢复
- 木桌：stereo 几乎完美（texture 充足）；偏振信号近零无用
- 不锈钢：stereo 受镜面反射干扰；偏振反而最强

⚡ **结论**：偏振与 stereo / ToF **互补而非替代** — 它们在不同表面类型上工作。production system 应该 fuse：stereo 提供 texture-rich 区域，偏振接管 glass/metal/water。

---

## 4 · 实战 hardware archetypes

**Sony `IMX250MZR`.** 5 MP (2448 × 2048)，1/1.8" GS CMOS，像素级 polarizer grid，60 fps。工业领头。

**Sony `IMX264MZR`.** 2.3 MP 版本，GS，更低分辨率但 SNR 略好；更便宜模组。

**Lucid Vision Labs `Phoenix`/`Triton` polarized.** 用 IMX250MZR/264MZR 做的工业相机，~$2k–4k，GigE/USB3 接口，工业 / robotics 学术研究用。

**Lucid `TRT089S-PC`.** USB3 polarized 紧凑款，~$1.5k，机器人 R&D。

**FLIR `Blackfly S polarization`.** 同 IMX250MZR sensor，FLIR / Teledyne 软件生态。

**Photonic Lattice / 4D Technology.** 旧式机械旋转 polarizer 系统，专用 metrology，不适合 robotics。

**Apple custom (推测).** Face ID dot projector 周围 sensor 据信使用某种偏振信息 reject 屏幕欺骗 `UNVERIFIED, no public confirmation` — 学术圈普遍认为这是 anti-spoof 路径之一。

---

## 5 · 应用场景

**Apple Face ID anti-spoof.** 把手机举起 = 屏幕反射 = 高度偏振光；真脸 = 漫反射 = 几乎不偏振。判别 DOLP > threshold → 拒绝认证。此路径外加 NIR structured light + ML 一起构成 anti-spoof 体系。**注意：这是 community 推测，Apple 未公开确认。**

**Robotics glass/transparent manipulation.** 抓玻璃杯 / 透明瓶子 — D435 + ToF 看不见，polarized camera 直接看到。Lucid Phoenix 在 Berkeley / CMU 研究多次用过。

**Automotive wet-road detection.** 路面变湿 → DOLP 跳升（水膜镜面反射）。Mobileye / Tesla 测试 polarized sensor 用于 ADAS 路面状况评估 `UNVERIFIED`。

**Solar / industrial 表面缺陷.** Polished metal / glass 表面缺陷在 polarization 下高对比；半导体 wafer inspection 用 polarization microscopy。

**Underwater / marine.** 水下 polarized imaging 能突破散射限制做远视；学术研究多，商用罕见。

**3D reconstruction of reflective scenes.** Polarization-aware NeRF / 3DGS — 玻璃 / 镜子场景 photorealistic reconstruction。

---

## 6 · Failure modes — 只有踩过才知道

**π-ambiguity.** AOLP 是 mod π 的，单视图无法唯一确定 azimuth；多视图 / 主动光源 / 神经网络先验来解。

**光照非均匀 / 偏振.** 室内 LED 灯本身有部分偏振（驱动电路 / 灯罩塑料）；偏振 sensor 把光源偏振当成表面偏振 → 系统误差。室外阳光在天空散射偏振也是干扰源（天空 ~20% DOLP @ 90° 太阳角）。

**对准精度.** 像素级 polarizer grid 在 mass production 误差 ~1–2°；这让 Stokes 计算有 5–10% crosstalk。Sony datasheet 给的是 ideal numbers，实际场景需 calibration。

**SNR.** DOLP 是相邻 4 像素差分 → 信号弱时差分被噪声主导。低光场景偏振几乎无用。

**Specular vs diffuse model 选错.** Shape-from-polarization 公式有 specular / diffuse 两套，选错给出 90° 偏差的 normal。production 需要 ML 自动选 model。

**Wavelength 依赖.** Wire-grid polarizer 在 visible band 性能好，IR band 性能下降；偏振 + NIR 主动感测组合需要专门设计。

### Hidden Assumptions — 偏振工作的前提

- **入射光部分偏振或表面足够光滑.** 完全 Lambertian 漫反射 + 完全非偏振光 → DOLP 永远为 0，偏振 sensor 无用。
- **表面反射满足 Fresnel.** Sub-wavelength 粗糙（亚光金属）让 Fresnel 失效。
- **像素 polarizer 对准精度.** ~0.1° 误差会在 Stokes 计算造成几个百分点 crosstalk。
- **光源 polarization 可控或可建模.** 否则光源 polarization 与表面 polarization 混淆。
- **足够 SNR.** 弱光下 4-pixel 差分被读出噪声主导。
- **AOLP π-ambiguity 可通过其他约束解.** 单视图 standalone 不可解。

---

## 7 · 与其他 sensor 对比 + Interview Tip

| Sensor | 玻璃可见？ | 镜面可见？ | 透明物体可见？ | Cost |
|---|---|---|---|---|
| **RGB camera** | 难 | 难 | 难 | $30 |
| **Stereo (D435 passive)** | 失语 | 跳跃 | 失语 | $300 |
| **Active stereo + projector** | 部分（projector 在玻璃上有反射）| 失语 | 部分 | $300 |
| **ToF / LiDAR** | 部分（多次反射）| 部分 | 部分 | $5–10k |
| **Polarized camera** | **强** | **强** | **强** | $1.5–4k |
| **Polarized + stereo fusion** | **优** | **优** | **优** | $2–5k |

**🎙️ Interview Tip.** 被问"为什么 robotics 还不普及偏振"？— 一句话：**学术 shape-from-polarization 在受控环境完美，但自然光照下偏振信号 SNR 不足，需要 active polarization + ML + 多视图融合才稳；Sony IMX250MZR 提供硬件，但 production-grade fusion stack 还在 R&D。Apple Face ID 是少数量产 case，因为它有受控 NIR 主动照明帮助**。

---

## 8 · For the reader (per-persona)

- **Manipulation engineer** — 玻璃 / 透明 / 反光物体抓取是 stereo + ToF 共同盲区，偏振是物理解。Lucid Phoenix 在 R&D 桌面上启动。
- **AD engineer** — Wet-road detection + windshield reflection rejection 是潜在应用；偏振 sensor 进入 ADAS 套件还需 5+ 年。
- **Drone engineer** — 偏振 sensor 太贵（>$1k）+ 太重（工业模组），目前不可上 drone。等待 MEMS 微缩。
- **Headset / AR-VR** — Apple Face ID 的 anti-spoof 路径；眼动追踪 + 显示器偏振相互作用是已知 R&D 方向。
- **Marine engineer** — 水下偏振穿透散射，学术研究丰富，商用罕见。

---

## References

- Stokes, G.G. (1852) "On the composition and resolution of streams of polarized light" — 原始论文
- Wolff, L.B. (1989) "Surface orientation from two camera stereo with polarizers"
- Atkinson & Hancock (2006) "Recovery of surface orientation from diffuse polarization"
- Sony `IMX250MZR` / `IMX264MZR` datasheets — `UNVERIFIED, no DOI`
- Lucid Vision Labs `Phoenix` / `Triton` polarized camera datasheets — `UNVERIFIED`
- Kadambi et al., "Polarized 3D" (ICCV 2015) — DOLP-based depth
- 维护者参考 Lucid + Berkeley AUTOLAB polarization 工作

## Boundary

- `foundations/sensor-physics/stereo_camera_geometry_physics.md` — stereo 在玻璃 / 反光的失败场景
- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — Face ID 中 NIR + polarization 组合
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — ToF 在镜面反射的失败模式
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 偏振 sensor 在跨 embodiment 的 BOM 位置（多数 cell 仍 rare）
- `embodiments/manipulation/sensor-stack/` — 玻璃 / 透明物体抓取的 R&D 路径
- `deployment/hardware-selection/` — Lucid Phoenix / FLIR Blackfly S 选型

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./overview.md)
