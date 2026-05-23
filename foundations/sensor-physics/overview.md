# Sensor Physics (传感器物理)

**Status:** v1.3 — 带立场的初稿。Datasheet 数字标 `UNVERIFIED` 需 spec-sheet 核对。
**TL;DR:** Sensor 物理是本仓的**独家轴** — 学术综述写不出 BPF FWHM × VCSEL 热漂、Allan plot 谷底位置、76 GHz vs 905 nm 波长落进 Rayleigh / Mie 区的天气结果、drone 50 A ESC 电流 vs 50 µT 地磁场比、UWB 500 MHz BW 物理上比 WiFi 准 25× 的 Heisenberg-Gabor 限、LWIR 8-14 µm 透不过玻璃决定 Tesla 至今不加 thermal。这 24 篇 + 1 决策矩阵覆盖具身 AI 真正承重的 sensor 决策物理 — 选错就是设计错了一整个 embodiment，而不是 algorithm 能补的。

---

## 为什么 sensor-physics 是独家轴

学界综述（survey papers）止步于"we used a RealSense D435"；厂商白皮书止步于"我们的 LiDAR 能打 200 m"。两者中间的**真正承重物理** — Si QE × solar dip × IEC 60825-1 安全预算共同决定波段、Allan plot 谷底决定 EKF 更新周期、76 GHz vs 905 nm 波长决定雨雾韧性、像素级 polarizer 决定玻璃可见、drone hard iron offset 决定起飞 toilet bowl — 都没人系统写。这个模块就是补这条缝。

写作原则：

1. **从 datasheet 一手资料出发，不复述论文摘要的 sensor 参数。** 论文经常把 spec 写错或写成 marketing 数字。
2. **每篇必含 worked example 把公式落到具体数字** — sensor 工程是 SWaP-C 工程，不是哲学讨论。
3. **每篇必含 Hidden Assumptions 子节** — sensor 收敛到当前选择全靠一组隐性约束成立，知道这些约束才知道何时它们会破裂。
4. **跨 embodiment 对比放在文末 §7/§8** — 同一 sensor 在 manipulation / drone / AD / marine 上往往是完全不同的判决。

---

## 24 篇 + 决策矩阵地图（v1.4 扩展）

按"主动光 → 几何 → 时间序列 → RGB 成像 → drone 专用 → 通用噪声框架 → 其他物理波"7 桶组织。

### A. 主动感测 / 波段物理（4 篇）

| File | Topic | Tier |
|---|---|---|
| `active_nir_850nm_for_embodied_ai.md` | 850 vs 940 vs 1550 nm — Si QE × solar dip × Class 1 的三轴交集 | ⚡ |
| `tof_physics_for_embodied_ai.md` | CW ToF / dToF / iPhone LiDAR — 调制相位 vs SPAD 单光子 | ⚡ |
| `lidar_physics_905_vs_1550.md` | 905 nm Si APD vs 1550 nm InGaAs SPAD — kW 脉冲安全预算 | ⚡ |
| `mmwave_radar_physics_for_ad.md` | 76–81 GHz FMCW — 为什么 Tesla / Waymo 都重新加回 radar | ⚡ |

### B. 几何感测 / Camera 系统（3 篇）

| File | Topic | Tier |
|---|---|---|
| `stereo_camera_geometry_physics.md` | `Z = fB/d` + `σ_Z = Z²σ_d/(fB)` — D435 vs Skydio baseline 几何强制 | ⚡ |
| `rolling_vs_global_shutter.md` | RS skew vs GS — drone racing 强制 GS 不是偏好，是几何 | ⚡ |
| `polarization_sensing_for_3d.md` | Sony IMX250MZR + Stokes / DOLP / AOLP — 玻璃 / 透明物体物理解 | 🔧 |

### C. 时间序列 sensor（2 篇）

| File | Topic | Tier |
|---|---|---|
| `imu_physics_and_noise_model.md` | MEMS vs FOG，ARW / BI / RRW，pre-integration 输入 | ⚡ |
| `event_camera_dvs_physics.md` | DVS / IMX636 — per-pixel async &lt;1 µs 时间分辨率 | ⚡ |

### D. RGB 相机成像管线（1 篇, **NEW in v1.2**）

| File | Topic | Tier |
|---|---|---|
| `rgb_camera_imaging_pipeline.md` | CMOS QE / Bayer / 噪声分解 / Brown-Conrady vs Kannala-Brandt 三种畸变模型 | ⚡ |

RGB 是所有视觉算法的"地基输入"，但 photon→pixel 管线每段都注入有色噪声 — SLAM 失败 60% 落在这里。学界综述把这段当"已解决"，本文是 sensor-physics 区 D 桶奠基文。

### E. drone 专用 sensor stack（4 篇, **NEW in v1.2**）

| File | Topic | Tier |
|---|---|---|
| `barometer_pressure_altimetry.md` | barometric formula / QNH / 温漂 / drone vertical EKF mid-term 主力 | ⚡ |
| `magnetometer_geomagnetic_field.md` | WMM 模型 / 硬铁软铁 / drone yaw 唯一绝对参考 | ⚡ |
| `gnss_multi_constellation_rtk.md` | GPS/GLONASS/Galileo/BeiDou 多频 / RTK cm 级 / 城市峡谷 dropout | ⚡ |
| `optical_flow_sensor_pmw3901.md` | 30x30 px 低分辨率视觉 / GNSS-denied 速度 / Crazyflie 室内 hover 主力 | 🔧 |
| `range_finder_for_drone_altitude.md` | 超声 vs 单线 NIR ToF vs 60 GHz altimeter — 起降 / terrain following 物理域分工 | ⚡ |

**drone autonomy stack 现在 sensor-physics 区已完整覆盖**：IMU (C 桶) + RGB camera (D 桶) + barometer + magnetometer + GNSS + optical flow + range finder (E 桶) + 主动 NIR / mmWave (A 桶) + stereo / rolling shutter (B 桶) — 这就是从 nano Crazyflie 到 commercial M300 RTK 的全部 sensor 决策物理。

### F. 经典 + 通用噪声框架（2 篇）

| File | Topic | Tier |
|---|---|---|
| `ultrasonic_acoustic_physics_for_robotics.md` | 40 kHz airborne ultrasonic — drone altimeter / 泊车 USS / multipath | 🔧 |
| `sensor_noise_modeling_allan_variance.md` | Allan variance 通用框架 — IMU / camera / LiDAR / radar 都适用 | ⚡ |

### G. 其他物理波 / 电磁 + 声学补完（6 篇, **NEW in v1.3**）

| File | Topic | Tier |
|---|---|---|
| `uwb_ultra_wideband_positioning.md` | 500 MHz – 几 GHz 脉冲 / DS-TWR / TDoA — 室内 cm 级，Heisenberg-Gabor 限 | ⚡ |
| `wifi_rf_positioning_5g.md` | 802.11mc FTM + 3GPP 5G NR positioning — 复用基础设施 1-3 m | 🔧 |
| `underwater_sonar_physics.md` | multibeam / side-scan / DVL / USBL — 水下唯一可信感知，c=1500 m/s | ⚡ |
| `thermal_ir_lwir_8_14um.md` | LWIR microbolometer / NETD / FFC — 被动黑体辐射 / 不透玻璃 | ⚡ |
| `24ghz_doppler_radar_motion.md` | 24 GHz K-band CW / FMCW / 生命体征 — 76 GHz 的便宜表弟 | 🔧 |
| `microphone_array_beamforming.md` | GCC-PHAT / MUSIC / MVDR — 声学 stereo 几何 + 人机交互核心 | ⚡ |

**G 桶动机**：A-F 桶覆盖具身 AI **主线** sensor 物理；G 桶补完**其他频段电磁波 (UWB / WiFi / 5G / 24 GHz / LWIR)** 和**其他介质声学 (水下 sonar / mic array)** — 这 6 类在特定 embodiment 上是主感官（marine AUV 全靠声呐 / smart home 全靠 24 GHz 或 mic / 室内 GNSS-denied 全靠 UWB），写完才算"sensor-physics 区物理上闭合"。

---

## 跨 sensor 选型决策矩阵 (v1.4 元视图)

读完上面 23-24 篇 single-sensor dissection 之后，配套：

- **[`sensor_selection_decision_matrix.md`](./sensor_selection_decision_matrix.md) ⚡ NEW (24 KB)** — 12+ sensor 横向 SWaP-C 决策表 × 6 use cases 决策树（nano drone / 巡检 drone / manipulation wrist / AD car / marine surface+AUV / humanoid）+ 失败模式跨 sensor 对照 + cost-of-ownership 提醒。**先做选型再读 single-sensor dissection 性价比最高**。

---

## drone autonomy stack 一站式 reading order

新到 drone autonomy 的读者，建议按下面顺序读 sensor-physics 区：

1. **`imu_physics_and_noise_model.md`** — 所有 drone 必备 sensor，MEMS vs FOG 决策
2. **`rgb_camera_imaging_pipeline.md`** — 视觉 input 的物理基础
3. **`rolling_vs_global_shutter.md`** — drone fast yaw 为什么强制 global shutter
4. **`gnss_multi_constellation_rtk.md`** — 户外 absolute position 主力
5. **`barometer_pressure_altimetry.md`** — vertical EKF mid-term 主力
6. **`magnetometer_geomagnetic_field.md`** — yaw 唯一绝对参考 + drone toilet bowl 根因
7. **`optical_flow_sensor_pmw3901.md`** — GNSS-denied 室内 hover 的 velocity 救命稻草
8. **`range_finder_for_drone_altitude.md`** — 起降 / terrain following &lt;8 m 的唯一可信信号
9. **`stereo_camera_geometry_physics.md`** — 视觉避障 + depth 物理
10. **`active_nir_850nm_for_embodied_ai.md`** — 室内暮光主动光选择（drone 通常 passive，但 inspection drone 例外）
11. **`mmwave_radar_physics_for_ad.md`** — 全天候避障 (commercial drone 趋势)
12. **`sensor_noise_modeling_allan_variance.md`** — Allan variance 把上面所有 sensor 统一到一个噪声框架

读完这 12 篇可以独立判断 nano drone / 消费 drone / commercial mapping drone 的 sensor stack BOM 取舍。

---

## 与 `crossing/sensor-stack-matrix/` 的边界

- 本目录 (`foundations/sensor-physics/`) 是**单 sensor 物理**：波段 / 噪声 / 几何 / 失效模式。每篇专注一个 sensor 类
- `crossing/sensor-stack-matrix/` 是**跨 embodiment 的 BOM 决策**：6 embodiment × 8 sensor class 取舍矩阵
- 引用方向：crossing 文档**应**链到本目录做 per-sensor deep dive；本目录文档在文末 §7-§8 给跨 embodiment 总结但不展开矩阵

具体：

- 旗舰 wedge `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` 是本模块 17 篇的**应用层综合**；任何"这个 sensor 在 X embodiment 上为什么这样选"的细节都拆到本目录对应文件。
- 反向：任何"D435 / VLP-16 / BMI270 / IMX900 / F9P / BMP388 等具体 SKU 在 production 系统中如何接入"细节去 `deployment/hardware-selection/` 或 `embodiments/<x>/sensor-stack/`，不在本目录。

---

## Boundary

本目录是 per-sensor 物理 / 失效模式 / 噪声模型。**不**覆盖：

- 跨 sensor SWaP-C BOM 矩阵 → `crossing/sensor-stack-matrix/`
- 具体 embodiment 的 sensor 集成（标定 / 同步 / 安装位置）→ `embodiments/<emb>/sensor-stack/`
- Production 选型决策 / 供应链 → `deployment/hardware-selection/`
- Sensor + ML 融合（如 RAFT-Stereo / Polarization-NeRF 算法）→ `foundations/feed-forward-3d/` 或 `foundations/3dgs-family/`
- VLA policy 如何消费 sensor 输出 → `bridge-to-vla/`
- drone EKF state-machine / control law → `embodiments/aerial/vio/` `embodiments/aerial/sensor-stack/`

需要从其他模块引用本目录的 per-sensor 物理，请链回本目录文件，不要复述。

---

## 维护规约

按 `AGENTS.md` 第 8 段 "Sensor-physics 特别注意"：

- 任何 spec 数字（QE / power / cost / dimension）必须附数据手册引用（vendor + 型号 + datasheet URL 或 `UNVERIFIED, no DOI`）
- 任何眼睛安全 / 法规相关声明必须引 IEC 60825-1 等标准编号
- 不允许从论文摘要复述 sensor 参数 — 必须从厂商一手资料
- 维护者 Autel 经验内容用 `✍️` 标记，Moltbot 不触碰
- 本目录**不接受自动追加**；Moltbot 仅允许在文末 `## 🤖 Moltbot Updates` 段以"日期 + 一句话事件 + 一手来源 URL"格式追加发布动态

新增 dissection 必须满足 AGENTS.md 14 项门槛 — 开头元信息 / X-Ray / 时间线 / Napkin Formula / Worked Example / Eureka Moment / Hidden Assumptions / Interview Tip / Boundary 一项不漏。

---

*2026-05-21. v1.3 — 从 17 篇扩到 23 篇，加 G 桶 "其他物理波"（UWB / WiFi-5G / 水下声呐 / LWIR thermal / 24 GHz Doppler / microphone array）。sensor-physics 区现在覆盖：主线具身 AI（A-F）+ 非主线但 embodiment-critical 频段 / 介质（G）— marine AUV / smart home / GNSS-denied 室内 / 人机交互的 sensor 物理也算闭合。*

*2026-05-21. v1.2 — 从 11 篇扩到 17 篇，加 RGB 相机成像管线（D 桶奠基）+ 5 篇 drone 专用 sensor (E 桶, barometer / magnetometer / GNSS / optical flow / range finder)。drone autonomy stack 的 sensor-physics 覆盖现在完整。*
