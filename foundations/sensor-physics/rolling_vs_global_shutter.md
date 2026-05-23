# Rolling vs Global Shutter 物理 (Rolling vs Global Shutter Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — CMOS 行扫描 vs CCD/CMOS 全局快门，artifacts 与几何后果
> **核心定位**：drone racing 必须 global shutter，iPhone 用 rolling shutter — 不是"廉价的妥协"，是工作空间 × 运动速度共同决定的物理结果

**Status:** v1 — opinionated draft，14-item dissection 范式。数字 `UNVERIFIED`。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) Rolling shutter (RS) CMOS 一次只曝光一行像素，整帧从顶到底扫描；global shutter (GS) 一次性整帧曝光。RS 在静态场景下视觉无差异，但在**相机或场景高速运动**下，每一行的"快照时刻"不同 → 直立物体倾斜（skew）、滚转 LED 灯泡条纹、风车叶片像香蕉。(b) drone racing / SLAM / VIO / event-based 视觉**强制 GS**；iPhone / 大多数监控摄像头用 RS 因为 RS 的像素简单、噪声低、感光面积大。(c) 对 sensor 工程师：选 RS 还是 GS 是**曝光时间 vs 运动速度 vs 几何容忍度**的三角决策，不是"哪个更好"。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1969 ── CCD 发明（贝尔实验室）— 天然 global shutter
2000 ── CMOS 进入消费市场，rolling shutter 成本主导
2007 ── iPhone — RS 进入 mass-market，"jello effect" 进入大众词汇
2013 ── Sony IMX174 (2 MP global shutter CMOS) — GS 重回 CMOS
2015 ── ORB-SLAM 时代，RS-aware SLAM 研究开始
2017 ── Sony IMX250 family — 5 MP GS，工业视觉标配
2020 ── Sony IMX490 (8 MP HDR rolling + GS hybrid) — 车载普及
2023 ── Sony IMX900 1.5 MP GS NIR-enhanced，机器人专门款
        ── 你在这里 (2026) ──
2025 ── BSI GS 普及，~$50/SKU 进入消费 drone；IMX900-class
?    ── stacked GS + per-pixel ADC <$30？开
```

---

## 1 · 工作原理对比 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
RS skew_pixels = (motion_velocity × readout_time) / pixel_pitch
GS artifacts   = 0 (geometric)，但每像素 +1 transistor → noise +1–3 dB
```

行扫描时间（readout_time）从 ms 级（10–30 ms 全帧）压到 µs 级才能避免 RS artifacts；GS 每个像素加一个 storage capacitor，多一个晶体管 → fill factor / SNR 让步。

### 1.1 Rolling shutter — CMOS 默认架构

每一行像素**顺序**完成 (reset → expose → readout)。当行 N 在曝光时，行 N-1 已读出、行 N+1 还在 reset。整帧从顶到底扫描，**没有任何两行同时曝光**。优势：simple pixel（3T / 4T）、高 fill factor (~50–60%)、低读出噪声、便宜。劣势：场景中任何快速运动都会出现 skew / wobble / partial exposure 现象。

### 1.2 Global shutter — 每像素带存储

每个像素加一个 storage node (capacitor 或 floating diffusion)。所有像素**同时**reset、同时曝光、然后**逐行读出存储值**。曝光时刻全帧一致 → 几何完美。代价：每像素 5T–8T，fill factor 降到 30–40%，读出噪声 +1–3 dB，cost 1.5–3× RS。

⚡ **Eureka Moment.** RS 与 GS 不是"廉价 vs 高端"，是**曝光时刻是否在帧内一致**的二元选择。SLAM / VIO / event camera / drone racing 几何上**根本不允许**"每行时刻不同"，所以强制 GS — 不是性能偏好，是数学要求。

### 1.3 时序图

```
Rolling shutter (一帧):
Row 0   ▓▓▓░░░░░░░░░░░░░░░░░ ────readout
Row 1   ░▓▓▓░░░░░░░░░░░░░░░░ ────readout
Row 2   ░░▓▓▓░░░░░░░░░░░░░░░ ────readout
...      (每行错开 ~30 µs)
Row N   ░░░░░░░░░░░░░░░░▓▓▓▓ ────readout
        ←─── 整帧 33 ms (30 fps) ───→

Global shutter (一帧):
All rows ▓▓▓▓▓▓░░░░░░░░░░░░░ ────readout (sequential)
         ←曝光→     ←readout 不影响曝光时刻→
```

---

## 2 · 数学核心 — RS 几何畸变 (Math Core)

**目标**：估计 RS 在已知运动下的几何畸变。

**Napkin**：

```
δ_pixel = v_image × t_readout
       = (f × V_world / Z) × t_readout
```

**变量说明**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `v_image` | 物体在 image plane 速度 (pixels/s) | 取决于运动与深度 |
| `t_readout` | 整帧扫描时间 | RS: 10–30 ms，fast GS-CMOS: <100 µs |
| `f` | focal length (pixels) | 500–2000 |
| `V_world` | 物体在世界坐标速度 (m/s) | drone 10 m/s, 行人 1.5 m/s |
| `Z` | 物体深度 (m) | 1–100 |

**直觉**：v_image 越大、t_readout 越长 → δ 越大。一旦 δ 超过 ~1 pixel，feature matching / disparity / VIO 就开始崩。

---

## 3 · Worked Example — 10 m/s drone 5 ms readout = 几像素 skew？

```
Drone:        10 m/s 水平飞行
Camera:       f = 800 pixels (6 mm lens @ 1/2" sensor)
Scene:        Z = 5 m（前方树）
t_readout:    5 ms（中速 RS）
```

- `v_image = f × V / Z = 800 × 10 / 5 = 1600 pixels/s`
- `δ = v_image × t_readout = 1600 × 0.005 = 8 pixels`

**8 pixel skew** — 远超 sub-pixel feature matching 容忍（~0.1 pixel）。直立的树会倾斜 8 pixel，VIO 算法会把"树倾斜"误解读成"我在 roll"。

继续：

- 若 `t_readout = 30 ms`（典型 RS @ 30 fps full frame）→ **δ = 48 pixels**。完全无法用。
- 若 `t_readout = 100 µs`（fast GS-mode 或 GS sensor）→ **δ = 0.16 pixel**。OK。
- 若 drone 在 100 km/h (~28 m/s) racing → δ × 2.8 → 即使 5 ms readout 也 ~22 pixels，必须 GS。

⚡ **结论**：drone racing 不是"GS 更好"，是 RS 在 racing 速度下数学上不可用 — δ ≫ 1 pixel 让 VIO / SLAM 几何不闭。

---

## 4 · 实战 hardware archetypes

**典型 RS sensor.** Sony `IMX477` (Raspberry Pi HQ Camera) / OmniVision `OV2640` / Sony 手机 sensor 全家族。fill factor 高、SNR 好、低光性能优、便宜。t_readout 一般 10–30 ms。

**典型 GS CMOS.** Sony `IMX174` (2 MP) / `IMX250` 系列 (5 MP) / `IMX264MZR` (polarized GS) / `IMX900` (1.5 MP NIR-enhanced GS) / OnSemi `AR0144` (1 MP economic GS)。t_readout 仍是 ms 级 readout，但**曝光时刻全帧一致** — 这是关键。

**Hybrid HDR RS+GS.** Sony `IMX490` (8 MP automotive)、`IMX390` — 在 RS 架构上加 dual-conversion-gain，HDR 性能极佳，但**仍是 RS**（车载 ADAS 接受 RS artifacts 是常见误解 — 其实大多数车载场景速度低 + 长焦让 δ 落在 sub-pixel）。

**Fast-readout RS as GS approximation.** 一些 sensor 提供"line-by-line"高速 readout (~100–500 µs/frame)，名义上仍 RS 但 δ <1 pixel 在多数场景。Skydio 早期款用过类似策略。

---

## 5 · 应用场景决策表

| 应用 | RS / GS | 关键约束 |
|---|---|---|
| **iPhone / 消费手机** | RS | 静态拍照 + ML 后处理 deskew；BOM 主导 |
| **Drone racing (>30 m/s)** | **GS 强制** | δ > 10 pixel @ RS，VIO 不闭 |
| **Skydio / cinewhoop drone** | GS preferred | 10–15 m/s + VIO 几何要求 |
| **iRobot / AGV** | RS OK | <1 m/s 速度，δ <0.1 pixel |
| **Manipulation arm** | **GS 强制** | 手抓快速运动 + 标定要求 |
| **Tesla / Waymo 车载** | RS 可接受 | f × V/Z 在远距下小，且 ML 后处理 |
| **Event camera 对比基准** | **GS 强制** | event-based 是 sub-µs，RS 完全失语 |
| **VIO / SLAM 学术** | **GS 强制** | RS-aware SLAM 是论文话题，工程不可用 |
| **监控摄像头** | RS OK | 静态视场 + 慢速目标 |

⚡ **规则**：工作空间内运动让 δ 超过 1 pixel → 必须 GS。否则 RS 更便宜、SNR 更好、低光更强。

---

## 6 · Failure modes — 只有踩过才知道

**LED 灯泡条纹.** RS 在 60 Hz / 100 Hz / 1 kHz PWM LED 下产生横向条纹（曝光时间内 LED 亮灭 1–2 次，每行落在不同相位）。GS 仍受 flicker 影响但是**整帧统一**，更易后处理。Tesla AP 早期摄像头大量出现交通灯条纹问题。

**汽车前轮"扭曲".** drone 拍快车，前轮在曝光顶部已转过 ~10°，底部还在原位 → 椭圆变香蕉。无法 sub-pixel 测速。

**Skew + roll 混淆.** drone 横向飞行时 RS skew 与 drone roll 在 image space 数学上等价。VIO 算法把 skew 误判为 roll → 控制系统过补偿 → 振荡。这是 RS 在 drone 上**不能用** VIO 的根因。

**机械振动共振.** drone propeller 频率 (~150 Hz) 与 RS readout 频率 (~30 fps × N rows) 共振 → 出现"wobble"波纹。GS 不受此影响。

### Hidden Assumptions — RS 在哪些场景"足够"

RS 可接受当且仅当：

- **曝光时间 ≪ 帧周期。** t_exposure < 1 ms 时 RS 内部曝光重叠最小。
- **场景速度 < 1 px/ms in image space。** 取决于 f, V, Z 组合。
- **后处理可补偿。** 已知 IMU 数据可做 RS-aware bundle adjustment（学术工作很多）。
- **机械振动频率 << 行频。** 不与 readout 共振。
- **没有 sub-pixel feature 需求。** SLAM / VIO / photogrammetry 都不允许。
- **LED 光源不主导。** 车载 RS 必须额外处理 flicker。

打破任意一条 → 必须 GS。

---

## 7 · 与 event camera / SPAD 对比 + Interview Tip

| Sensor | 曝光时刻一致？ | 时间分辨率 | 应用 |
|---|---|---|---|
| **RS CMOS** | ❌ 行扫描 | 10–30 ms / frame | 消费 / 慢速 |
| **GS CMOS** | ✅ 全帧 | 1–30 ms / frame | 工业 / drone / 机器人 |
| **Event camera (DVS)** | N/A (per-pixel async) | <1 µs | 极速运动、ultra-low-latency |
| **SPAD array (ToF)** | ✅ photon-level GS | <1 ns gating | depth、low-light |

**🎙️ Interview Tip.** 被问"为什么 Skydio 用 GS、iPhone 用 RS"？— 一句话：**Skydio 在 10–20 m/s 飞 + 跑 VIO，RS skew δ > 1 pixel 让 VIO 数学不闭；iPhone 静态拍照 + ML 后处理 deskew，RS 的 SNR 优势压过 skew 代价**。决策不是"哪个更好"，是 `f × V / Z × t_readout` 这个 napkin 公式的输出。

---

## 8 · For the reader (per-persona)

- **Aerial engineer** — 任何带 VIO 的 drone 强制 GS（IMX900 / IMX264 class）。例外只在 <2 m/s hover-only inspection drone。
- **Manipulation engineer** — 手抓 + 标定都要 GS，IMX174 / IMX250 是工业默认。RS 在标定棋盘上会引入系统误差 ~1 mm @ 1 m。
- **AD engineer** — RS 在远距长焦下可用，但 LED flicker + 隧道动态范围一起逼你考虑 IMX490 hybrid，**不是单选 RS / GS**。
- **Headset / AR-VR** — eye-tracking GS 强制（眼球扫视 ~600°/s），passthrough RS 凑合（用 IMU + ML 后处理）。

---

## References

- Sony `IMX174` / `IMX250` / `IMX264MZR` / `IMX490` / `IMX900` datasheets — 全部 `UNVERIFIED, no DOI`
- OnSemi `AR0144` datasheet — `UNVERIFIED`
- Forssén & Ringaby, "Rectifying rolling shutter video from hand-held devices" (CVPR 2010)
- Kerl et al., "Dense continuous-time tracking and mapping for rolling shutter RGB-D cameras" (ICCV 2015)
- 维护者在 Autel 的 GS / RS 测试经验

## Boundary

- `foundations/sensor-physics/event_camera_dvs_physics.md` — sub-µs per-pixel async 的对比极端
- `foundations/sensor-physics/imu_physics_and_noise_model.md` — RS-aware bundle adjustment 输入 IMU 数据
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — GS premium 在 BOM 内的位置
- `embodiments/aerial/sensor-stack/` — drone 强制 GS 的整合层
- `embodiments/manipulation/sensor-stack/` — 手抓 GS 在标定中的实际数字
- `deployment/hardware-selection/` — IMX900 / IMX250 选型决策

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./overview.md)
