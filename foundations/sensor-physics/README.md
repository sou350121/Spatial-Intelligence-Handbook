# Sensor Physics (传感器物理)

**Status:** v1.1 — 带立场的初稿。Datasheet 数字标 `UNVERIFIED` 需 spec-sheet 核对。
**TL;DR:** Sensor 物理是本仓的**独家轴** — 学术综述写不出 BPF FWHM × VCSEL 热漂、Allan plot 谷底位置、76 GHz vs 905 nm 波长落进 Rayleigh / Mie 区的天气结果。这 11 篇覆盖具身 AI 真正承重的 sensor 决策物理 — 选错就是设计错了一整个 embodiment，而不是 algorithm 能补的。

---

## 为什么 sensor-physics 是独家轴

学界综述（survey papers）止步于"we used a RealSense D435"；厂商白皮书止步于"我们的 LiDAR 能打 200 m"。两者中间的**真正承重物理** — Si QE × solar dip × IEC 60825-1 安全预算共同决定波段、Allan plot 谷底决定 EKF 更新周期、76 GHz vs 905 nm 波长决定雨雾韧性、像素级 polarizer 决定玻璃可见 — 都没人系统写。这个模块就是补这条缝。

写作原则：

1. **从 datasheet 一手资料出发，不复述论文摘要的 sensor 参数。** 论文经常把 spec 写错或写成 marketing 数字。
2. **每篇必含 worked example 把公式落到具体数字** — sensor 工程是 SWaP-C 工程，不是哲学讨论。
3. **每篇必含 Hidden Assumptions 子节** — sensor 收敛到当前选择全靠一组隐性约束成立，知道这些约束才知道何时它们会破裂。
4. **跨 embodiment 对比放在文末 §7/§8** — 同一 sensor 在 manipulation / drone / AD / marine 上往往是完全不同的判决。

---

## 11 篇地图

按"主动感测 → 几何感测 → 时间序列 sensor → 噪声框架"分组。

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
| `event_camera_dvs_physics.md` | DVS / IMX636 — per-pixel async <1 µs 时间分辨率 | ⚡ |

### D. 经典 + 通用噪声框架（2 篇）

| File | Topic | Tier |
|---|---|---|
| `ultrasonic_acoustic_physics_for_robotics.md` | 40 kHz airborne ultrasonic — drone altimeter / 泊车 USS / multipath | 🔧 |
| `sensor_noise_modeling_allan_variance.md` | Allan variance 通用框架 — IMU / camera / LiDAR / radar 都适用 | ⚡ |

---

## 与 `crossing/sensor-stack-matrix/` 的边界

- 本目录 (`foundations/sensor-physics/`) 是**单 sensor 物理**：波段 / 噪声 / 几何 / 失效模式。每篇专注一个 sensor 类
- `crossing/sensor-stack-matrix/` 是**跨 embodiment 的 BOM 决策**：6 embodiment × 8 sensor class 取舍矩阵
- 引用方向：crossing 文档**应**链到本目录做 per-sensor deep dive；本目录文档在文末 §7-§8 给跨 embodiment 总结但不展开矩阵

具体：

- 旗舰 wedge `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` 是本模块 11 篇的**应用层综合**；任何"这个 sensor 在 X embodiment 上为什么这样选"的细节都拆到本目录对应文件。
- 反向：任何"D435 / VLP-16 / BMI270 / IMX900 等具体 SKU 在 production 系统中如何接入"细节去 `deployment/hardware-selection/` 或 `embodiments/<x>/sensor-stack/`，不在本目录。

---

## Boundary

本目录是 per-sensor 物理 / 失效模式 / 噪声模型。**不**覆盖：

- 跨 sensor SWaP-C BOM 矩阵 → `crossing/sensor-stack-matrix/`
- 具体 embodiment 的 sensor 集成（标定 / 同步 / 安装位置）→ `embodiments/<emb>/sensor-stack/`
- Production 选型决策 / 供应链 → `deployment/hardware-selection/`
- Sensor + ML 融合（如 RAFT-Stereo / Polarization-NeRF 算法）→ `foundations/feed-forward-3d/` 或 `foundations/3dgs-family/`
- VLA policy 如何消费 sensor 输出 → `bridge-to-vla/`

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

*2026-05-21. v1.1 — 从 5 篇旗舰扩到 11 篇，加 radar / shutter / stereo geometry / ultrasonic / polarization / Allan variance 六个独立轴。*
