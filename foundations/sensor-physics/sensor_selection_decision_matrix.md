# 跨 Sensor 选型决策矩阵 (Cross-Sensor Selection Decision Matrix)

> **类型**: comparison (24 个 single-sensor dissection 后的元视图) — 不走 14 项 dissection 门槛
> **聚焦**: 跨 sensor 选型决策矩阵 + 决策树 + 失败模式跨 sensor 对照
> **Status**: v1 — 2026-05-22。所有具体 SWaP-C 数字 (g / W / $) 标 `UNVERIFIED` 除非引自原 dissection

**TL;DR.** 24 个 single-sensor dissection 把波段 / 噪声 / 失败模式拆到 datasheet 一层，但**缺一个「看完之后第一步选哪个」的横向决策表**。本页补这个元视图：**§2 把 13 个 sensor class 摆在一张表上**、**§3 给 6 种典型 embodiment 的最小 viable stack**、**§4-§7 处理 single-sensor dissection 不回答的 4 个问题**（互补 / 同类怎么选 / 跨 sensor 失败模式 / 隐藏拥有成本）。最重要的判断：**没有 universal best — 只有"working range + SWaP-C + 失败模式可接受"局部最优**；250 g drone 选 16-line LiDAR、或 humanoid 选 RTK GNSS，都是 SWaP-C 决策错了一个数量级。

---

## 1 · SWaP-C 轴的回顾 — 同 sensor 在不同 embodiment 权重完全不同

| 轴 | nano drone ≤250 g | 巡检 drone 1-5 kg | manipulator | AD car | humanoid | marine AUV |
|---|---|---|---|---|---|---|
| **Weight** | **<5 g 关键** | <100 g | 不敏感 | 不敏感 | <500 g | 浮力中性 |
| **Power** | <1 W (200 mAh) | <5 W | wall power | 12 V ECU | 24 V battery | ~50 Wh/km |
| **Cost** | <$50 BOM | <$500 | <$2k (D435) | <$5k OK | <$2k | <$50k OK |
| **Compute** | MCU STM32 | Jetson Orin Nano | x86 ws | Orin AGX×多 | Orin AGX×多 | low-power MCU |
| **Size** | <30 mm | <80 mm | wrist-cam | hood/roof | head/waist 10 cm | watertight bottle |

**关键观察**：(1) nano drone 几乎只看 weight × power — 加 10 g 等于减 10% flight time；(2) AD 几乎只看 range + 失败模式，weight/cost 可吸收；(3) manipulator 几乎只看 0-1 m 米制精度；(4) marine AUV 只看声学频段，光学 / 电磁全瞎。每个 sensor 的 SWaP-C 数字回 [`README.md`](./README.md) 24 篇 dissection。

---

## 2 · 主决策表 — 13 个 sensor class 横向

> 单位约定：range 是 typical operating range（不是 datasheet max）；Hz 是 typical update rate；Weight 是 module-level（不含 mount）；Cost 是 BOM tier（量产价位）。**所有具体数字 `UNVERIFIED` 除非链回上游 dissection。**

所有数字 `UNVERIFIED` 除非链回上游 dissection。Range = typical operating；Weight = module-level；Cost = BOM tier。

| Sensor | 原理一句话 | Range | Hz | Power | Weight | Cost | 主要失败模式 | 何时用 / 不用 |
|---|---|---|---|---|---|---|---|---|
| **Active-NIR 850 nm** ([↗](./active_nir_850nm_for_embodied_ai.md)) | VCSEL flood + NIR cam + BPF | 0.1-5 m | 30-90 | 1-5 W | 5-30 g | $20-100 | 强日光 + 镜面饱和 | 室内/暮光 ✓ ; 正午 ✗ |
| **ToF Phase-CW** ([↗](./tof_physics_for_embodied_ai.md)) | 调制相位测距 (Kinect/L515) | 0.3-5 m | 30 | 2-5 W | 20-50 g | $50-300 | wrap-around / 多径 / 阳光 | 室内 wrist depth ✓ ; >5 m ✗ |
| **ToF dToF (SPAD)** | ns 脉冲 + SPAD 计时 (iPhone) | 0.3-10 m | 30 | 0.5-3 W | <5 g | $5-30 | pile-up / 弱反射 | mobile ✓ ; 工业级 grasp ✗ |
| **LiDAR 905 nm 机械** ([↗](./lidar_physics_905_vs_1550.md)) | Si APD + 旋转扫描 | 30-150 m | 10-20 | 8-20 W | 600-1000 g | $1-10k | 轴承寿命 / 雨雪 Mie | 测绘 ✓ ; 量产 AD ✗ |
| **LiDAR 905 nm 半固态** | MEMS/OPA + Si APD (AT128) | 100-200 m | 10 | 8-15 W | 300-700 g | $1-4k | FOV 窄 / 反射率敏感 | 乘用车 AD ✓ ; nano drone ✗ |
| **LiDAR 1550 nm FMCW** | InGaAs SPAD + chirp 多普勒 | 200-500 m | 10 | 15-30 W | 800-2000 g | $5-20k | 单像素 50-100× Si cost | 卡车/远距 ✓ ; cost-bound ✗ |
| **RGB Camera GS** ([↗](./rgb_camera_imaging_pipeline.md)) | CMOS + Bayer + global shutter | passive | 30-120 | 0.5-2 W | 5-30 g | $5-100 | dazzle / textureless / blur | 几乎所有 embodiment ✓ ; 无光/烟雾/水下 ✗ |
| **RGB RS** ([↗](./rolling_vs_global_shutter.md)) | rolling shutter readout | passive | 30-60 | 同上 | 同上 | 更便宜 | jello / fast yaw 几何崩 | static ✓ ; drone racing ✗ |
| **Stereo (passive)** ([↗](./stereo_camera_geometry_physics.md)) | `Z=fB/d` 三角 | baseline×(10-100) | 30-60 | 2-5 W | 50-150 g | $200-2k | textureless / 标定漂 / 曝光不对称 | manipulation/drone 避障 ✓ ; >100 m/白墙 ✗ |
| **Event Camera (DVS)** ([↗](./event_camera_dvs_physics.md)) | 异步 per-pixel log-intensity | passive, ~1 µs | 异步 | 0.1-1 W | 30-100 g | $1-3k (Prophesee) | 静态没事件 / 生态嫩 | HDR/高速/低光 ✓ ; 量产认证 ✗ |
| **IMU MEMS** ([↗](./imu_physics_and_noise_model.md)) | Coriolis MEMS + 加速度计 | proprio | 100-1000 | <0.1 W | <5 g | $1-10 (BMI270) | bias drift / 振动 / 温漂；60 s ≈ 18 m | 全 embodiment baseline ✓ ; 长时单用 ✗ |
| **IMU tactical** | Honeywell HG4930 级 | proprio | 200-2000 | 1-3 W | 100-200 g | $3-10k | 振动 / 寿命 | 巡航 / AGV ✓ ; 消费品 ✗ |
| **IMU FOG** | Sagnac 光纤干涉, BI 0.05°/hr | proprio | 100-200 | 3-10 W | 500-1500 g | $10k-100k | 体积大 / 需温稳 | 真值 / 潜艇 ✓ ; weight-bound ✗ |
| **GNSS L1 single** ([↗](./gnss_multi_constellation_rtk.md)) | 单频 code phase | global, 5-10 m | 1-10 | 0.1-0.3 W | <10 g | $10-30 | 峡谷/多径/电离层 | 户外 baseline ✓ ; 室内 ✗ |
| **GNSS multi-band RTK** | 双频 + base + carrier (F9P) | 1-5 cm | 5-20 | 0.5-2 W | 30-100 g | $200-1k | base 失联即回退 | 测绘/commercial drone ✓ ; 室内 ✗ |
| **GNSS PPP** | 多频 + precise products | ~10 cm, 收敛 30 min | 1 | 0.5-2 W | ~RTK | $1k-5k | 收敛慢 | marine/静态 ✓ ; 实时机动 ✗ |
| **Magnetometer** ([↗](./magnetometer_geomagnetic_field.md)) | Hall/fluxgate 测地磁 | yaw global | 10-100 | <0.05 W | <1 g | $1-30 | 硬/软铁；50 A ESC vs 50 µT | drone yaw ✓ ; 钢梁/电流附近 ✗ |
| **mmWave 77 GHz AD** ([↗](./mmwave_radar_physics_for_ad.md)) | FMCW + MIMO 阵列 | 5-300 m | 10-30 | 5-15 W | 200-500 g | $500-3k 模组 | 角分辨率 ~0.5° / 金属混叠 | AD/浓雾穿透 ✓ ; 室内 dense ✗ |
| **mmWave 24 GHz** ([↗](./24ghz_doppler_radar_motion.md)) | K-band CW/FMCW | 0.5-20 m | 10-50 | 0.3-2 W | 5-30 g | $5-50 | 角分辨率粗 / 频段限带宽 | smart home / 廉价防撞 ✓ ; AD ✗ |
| **UWB** ([↗](./uwb_ultra_wideband_positioning.md)) | 500 MHz 脉冲 + DS-TWR | 0.1-50 m, σ ≈ 3 cm | 10-100 | RX 150 mW peak | <5 g | $3-8 chip / $30-50 anchor | 多径 / NLOS bias / 需 anchor | 室内 cm/swarm ✓ ; 户外大场景 ✗ |
| **Thermal IR LWIR** ([↗](./thermal_ir_lwir_8_14um.md)) | microbolometer 被动黑体 | 0-100 m | 9-60 (export) | 0.5-2 W | 5-100 g | $100-3k (Boson+) | 不透玻璃 / 热饱和 / FFC 1 s 盲 | 夜视/烟雾/救援 ✓ ; 透玻璃 ✗ |
| **Barometer** ([↗](./barometer_pressure_altimetry.md)) | MEMS 压力 + 温补 | -500 to 9000 m | 10-100 | <0.01 W | <0.5 g | $2-5 (BMP388) | 温漂 / 阵风 / HVAC | drone vertical mid-term ✓ ; 高动态<1 s ✗ |
| **Ultrasonic** ([↗](./ultrasonic_acoustic_physics_for_robotics.md)) | 40 kHz airborne ToF | 0.05-4 m | 10-40 | 0.3-1 W | 5-20 g | $1-30 | 多径 / 软材吸收 / 风漂 | drone 起降/USS ✓ ; >5 m/风大 ✗ |

23 行覆盖 12 个**主** sensor class（active-NIR / ToF / LiDAR 3 架构 / RGB GS+RS / stereo / event / IMU 3 等级 / GNSS 3 等级 / magnetometer / mmWave 2 频段 / UWB / thermal）+ drone 专用 barometer + ultrasonic。完整 SWaP-C 数字回各 dissection 与 [README.md](./README.md)。

---

## 3 · 决策树 (by use case) — 6 个典型 embodiment

> 每个 use case 给"最小 viable stack"（去掉 1 项就有 spec 跑不到）+ 可选增强 + **明确点名不要选的 sensor**。

### 3.1 · 250 g 微型 drone 室内 SLAM (Crazyflie / Skydio nano)
**约束**: weight <5 g/sensor, power <1 W, cost <$50。**Stack**: IMU MEMS (BMI270) + monochrome GS camera + 单点 NIR ToF / optical flow PMW3901 + barometer (BMP388)。**不要**: ✗ LiDAR (≥300 g 超 weight budget 60×) / ✗ RTK GNSS (室内无信号 + 30 g) / ✗ thermal IR (cost + FFC 不划算)。
参考: [imu](./imu_physics_and_noise_model.md) + [optical_flow](./optical_flow_sensor_pmw3901.md) + [rolling_vs_global_shutter](./rolling_vs_global_shutter.md) + [`embodiments/aerial/sensor-stack/`](../../embodiments/aerial/sensor-stack/)

### 3.2 · 1.5 kg 巡检 drone 户外 (DJI M300 / Skydio X10)
**约束**: weight <100 g/sensor, power <5 W, cost <$500。**Stack**: IMU (ICM-42688) + GS stereo (D435) + RTK GNSS (F9P) + magnetometer (RM3100, 远 ESC) + barometer。**可选**: 16-line LiDAR (~600 g) for terrain following / 77 GHz mmWave (~50 g) for BVLOS 浓雾备份。
参考: [stereo](./stereo_camera_geometry_physics.md) + [gnss](./gnss_multi_constellation_rtk.md) + [magnetometer](./magnetometer_geomagnetic_field.md) + [`embodiments/aerial/long-range-slam/`](../../embodiments/aerial/long-range-slam/) + [`embodiments/aerial/obstacle-avoidance/`](../../embodiments/aerial/obstacle-avoidance/)

### 3.3 · 室内 manipulation wrist (Franka / UR / xArm)
**约束**: 0-1 m 米制精度 <few mm。**Stack**: active stereo RGBD (D435) + RGB GS + force-torque (非本目录)。**可选**: ToF (L515, 已 EOL) for dense / event camera for 高速 dynamic grasp / Azure Kinect for 离线 calibration。**不要**: ✗ LiDAR (overkill + sparse) / ✗ GNSS / mmwave / UWB (室内有 frame)。
参考: [tof](./tof_physics_for_embodied_ai.md) + [stereo](./stereo_camera_geometry_physics.md) + [active_nir](./active_nir_850nm_for_embodied_ai.md) + [`embodiments/manipulation/3d_feature_cloud_representations.md`](../../embodiments/manipulation/3d_feature_cloud_representations.md)

### 3.4 · AD-class 高速车 (Waymo / Mobileye)
**约束**: range 200+ m + 失败模式覆盖 + 冗余。**Stack**: 8-12 颗 GS camera + 4D mmWave (Arbe Phoenix) + 1-3 颗 905 nm 半固态 LiDAR + GNSS multi-band + tactical IMU loose coupling。**可选**: 1550 nm FMCW (卡车 / 远距) / thermal IR (夜视行人，但 Tesla 至今不加)。**Tesla doctrinal 例外**: ✗ LiDAR — vision + radar 路线，详见 [`embodiments/driving/waymo_vs_tesla_doctrinal_split.md`](../../embodiments/driving/waymo_vs_tesla_doctrinal_split.md)。
参考: [lidar](./lidar_physics_905_vs_1550.md) + [mmwave](./mmwave_radar_physics_for_ad.md) + [thermal_ir](./thermal_ir_lwir_8_14um.md) + [`embodiments/driving/`](../../embodiments/driving/)

### 3.5 · Marine surface / underwater AUV
**物理约束**: 水下光 + 电磁 (>500 MHz) 全衰减。**Surface USV**: GNSS RTK + tactical IMU + RGB。**Underwater AUV**: DVL + tactical/FOG IMU + multibeam/side-scan sonar + USBL/LBL acoustic positioning。**不要 (物理)**: ✗ LiDAR (水中 <10 m 衰减完) / ✗ mmWave / UWB (水导体) / ✗ thermal IR (表面下完全无用)。
参考: [underwater_sonar](./underwater_sonar_physics.md) + [`embodiments/marine/sensor_stack_underwater.md`](../../embodiments/marine/sensor_stack_underwater.md) + [`embodiments/marine/underwater_slam_dvl_sonar.md`](../../embodiments/marine/underwater_slam_dvl_sonar.md)

### 3.6 · Humanoid (Unitree H1 / Figure 02 / 1X NEO)
**约束**: 多 viewpoint (head + waist + wrist), 24 V battery。**Stack**: head stereo RGBD (D455) + waist downward stereo (脚下地形) + wrist RGBD/ToF (D405/L515) + torso IMU + foot pressure。**可选**: Livox Mid-360 16-line LiDAR (~265 g) for 大场景 SLAM (Unitree 路线) / 24 GHz mmWave for presence。
参考: [`embodiments/humanoid-legged/whole_body_spatial_perception.md`](../../embodiments/humanoid-legged/whole_body_spatial_perception.md) + [`embodiments/humanoid-legged/unitree_h1_vs_figure_vs_1x.md`](../../embodiments/humanoid-legged/unitree_h1_vs_figure_vs_1x.md)

---

## 4 · 互补组合 — 为什么"加一颗"是物理必然

任何 single-sensor 在某个轴上都瞎；下面 4 个组合**不可裁剪**：

- **IMU + Camera = minimum viable VIO**。IMU 单独 60 s 漂 ~18 m + 3° 转角 (`UNVERIFIED`，[imu](./imu_physics_and_noise_model.md) §3)；camera 单独 scale ambiguous / baseline 限远端。**IMU 给 metric scale + 高频 propagation；camera 给 absolute drift correction** — EKF/MSCKF/VINS 都是这个数学。"VIO 是 spatial intelligence minimum unit" 的物理根据，不是"算法选择"。
- **GNSS + IMU + Visual/LiDAR = 户外完整 stack**。GNSS 单独城市峡谷 / 桥下 / 室内全瞎；GNSS+IMU loose-coupling dropout 1 s OK 但 60 s 漂 18 m；加 visual/LiDAR 后 dropout 期间 VIO 接管，camera/LiDAR 提供 absolute features。Commercial drone / robotaxi / agriculture 事实标准。
- **mmWave + Camera = 天气韧性**。Camera 雨/雾/扬尘衰减 50-80%（[lidar](./lidar_physics_905_vs_1550.md) §6）；77 GHz mmWave 穿透 30-100× + native velocity 但角分辨率粗（[mmwave](./mmwave_radar_physics_for_ad.md) ⚡ Eureka）。Tesla 重新加 radar 的根因不是 cost；Mobileye / Waymo / Bosch ARS540 都用这套。
- **Magnetometer + Optical Flow + Barometer = nano drone 室内三件套**。没 GNSS 时，mag 给 yaw（远 ESC）、flow 给 velocity（地面有 texture）、baro 给 altitude mid-term（避 HVAC 阵风）— 三者独立全弱，合一加 IMU 撑 Crazyflie 室内 hover。

---

## 5 · 同类内部选型 — 关键分歧

### 5.1 LiDAR: 905 nm vs 1550 nm vs 架构

| 维度 | 905 nm Si APD | 1550 nm InGaAs SPAD |
|---|---|---|
| QE @ λ | ~30% `UNVERIFIED` | ~20-30% `UNVERIFIED` |
| Eye-safe peak power | ~5 mW | ~5 W (~1000×) |
| 像素 cost | baseline | 50-100× |
| 雨雪环境 | Mie scatter 主导（差异小） | peak power headroom 给"看穿"裕量 |
| 量产路线 | Hesai AT128 / Innoviz / Ouster | Luminar Iris / Aeva |
| 决策准则 | **量产乘用车 / 成本敏感** | **远距 / 卡车 / 高速速度场** |

机械 vs 固态 vs FMCW 的分歧：**机械**寿命有限（轴承）但 360° FOV，**MEMS 半固态**寿命好但视场角窄需 stitch，**FMCW**直接拿 velocity 但单像素贵 — 见 [lidar](./lidar_physics_905_vs_1550.md) §7。

### 5.2 IMU: MEMS / tactical / FOG — Allan plot 的"等级"

| Grade | Bias instability | Weight | Cost | 60 s drift (位置) `UNVERIFIED` |
|---|---|---|---|---|
| Consumer MEMS (BMI270) | 0.5°/s `UNVERIFIED` | <5 g | $1-10 | ~18 m |
| Tactical (HG4930) | 0.05°/hr `UNVERIFIED` | 100-200 g | $3-10k | ~几 m |
| FOG (KVH 1750) | 0.05°/hr `UNVERIFIED` | 500-1500 g | $10k-100k | <1 m |

数字回 [imu](./imu_physics_and_noise_model.md) §3。**关键 trade-off**：consumer MEMS 已经能跑 manipulation / 消费 drone；tactical 在 GNSS-denied 巡航中是 must-have；FOG 在自动驾驶量产车上完全不现实（weight × cost 都炸）— 只用在 robotaxi 数据采集车做 ground truth。

### 5.3 GNSS: single / RTK / PPP

| 等级 | 精度 | 收敛时间 | base station? | 适用 |
|---|---|---|---|---|
| L1 single | 5-10 m | <1 s | no | 消费 drone / 农业 baseline |
| Multi-band RTK | 1-5 cm | 5-30 s + carrier lock | **yes** | 测绘 / 建筑 / commercial drone |
| PPP | ~10 cm | 30 min | no (用 precise products) | marine / 静态 / 农业 |

详见 [gnss](./gnss_multi_constellation_rtk.md) §5。**RTK 需要 base 在 10-30 km 内**，跨海 / 跨州时退化到 PPP。

---

## 6 · 失败模式跨 sensor 对照 — 同一扰动崩多少个

> ⚠️ = 中等退化, ❌ = 完全失效, ✅ = 鲁棒

| 扰动 | RGB | Stereo | Active-NIR | ToF | 905 nm LiDAR | mmWave | UWB | IMU | GNSS | Mag | Thermal IR | Sonar |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **正午阳光 dazzle** | ❌ | ❌ | ⚠️ (BPF 救) | ⚠️ | ⚠️ (ambient) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| **雨 10 mm/hr** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ Mie scatter | ✅ 衰减 <3 dB | ⚠️ | ✅ | ⚠️ multipath | ✅ | ⚠️ | n/a |
| **浓雾 (能见 <50 m)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (77 GHz 穿透 30-100×) | ⚠️ | ✅ | ⚠️ | ✅ | ⚠️ (湿) | n/a |
| **textureless 白墙 / 雪地** | ⚠️ | ❌ disparity 没了 | ✅ (project pattern) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ (温度均匀) | n/a |
| **镜面反射 / 玻璃** | ⚠️ | ❌ | ❌ (specular 不返回) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (不透玻璃) | n/a |
| **GNSS spoofing / 城市峡谷** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | n/a |
| **大铁结构 / 高电流 (50 A ESC)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ 硬铁 + 软铁 | ✅ | n/a |
| **UWB 多径 / NLOS** | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ bias | ✅ | ✅ | ✅ | ✅ | n/a |
| **桨叶振动 (200-2000 Hz)** | ⚠️ (motion blur) | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ❌ aliasing + bias | ✅ | ⚠️ | ⚠️ | n/a |
| **>30°C 热漂 / 太阳曝晒** | ✅ | ⚠️ baseline drift | ⚠️ VCSEL 漂 0.06 nm/°C | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ bias temp | ✅ | ⚠️ | ⚠️ FFC pause | ✅ |
| **水下 / 透过水面** | ❌ <10 m | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ | ❌ | ✅ 唯一 |
| **强 fluorescent 闪烁 (400 Hz)** | ⚠️ (banding) | ⚠️ | ⚠️ (Phase-CW 拍频 ghost) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**5 个跨 sensor 的"协同崩"模式**（设计时务必加冗余）：
1. **光学 + 镜面反射**：RGB / stereo / NIR / ToF / LiDAR 全瘫 — 唯一答案是 polarization 或 mmWave；
2. **光学 + 浓雾**：所有光学全瘫 — 唯一答案是 77 GHz mmWave；
3. **声学 + 强混响 / 软材料**：sonar / ultrasonic 同时崩 — 水下 UAV 设计要避开石壁直角；
4. **电磁 + 室内 + 干扰**：GNSS / WiFi RTT / mag 都不靠谱 — 室内必须 UWB or VIO；
5. **慣性 + 桨叶振动**：MEMS IMU 在 200-2000 Hz aliasing — drone 必须橡胶减振 + 200+ Hz IMU。

---

## 7 · 真实拥有成本 — BOM 单价是冰山一角

24 个 dissection 给的是 BOM 单价；生产环境真实成本至少 **3-10×**。隐藏成本: (1) **Calibration toolchain** (Kalibr / IMU-cam / multi-cam) — 1 工程师月 + 标定室；(2) **ROS driver maintenance** — 每代固件 1-2 周回归；(3) **Factory line test fixture** — $5k-50k 检具 + 工时；(4) **Per-unit calibration** 5-30 min/unit；(5) **Field re-cal** (drone stereo ~0.024 m/m drift `UNVERIFIED`)；(6) **认证 / 监管** (FCC / IEC 60825 / FAA / CE) — $30k-300k + 6-12 月；(7) **出口管制** (中国 LiDAR / FOG ITAR)。

**经验法则**: D435 BOM $300 → 量产线 ~$1000；车规 LiDAR $1k → 含认证维保 ~$5k；FOG IMU $20k → 含 ITAR licensing ~$50k+。详细见 [`deployment/hardware-selection/`](../../deployment/hardware-selection/)。

---

## 8 · 这张矩阵不能告诉你的事

(1) **Form factor / mechanical mounting** — connector 5 g 可能就让 sensor 嵌不进 250 g drone；(2) **Vendor lock-in** — RealSense / Livox SDK 迁移成本不在 BOM；(3) **国贸 / 出口管制** — 中国 LiDAR 受限 / FOG ITAR，物理能买 ≠ 合规能用；(4) **Regulatory** — 事件相机 / 1550 nm LiDAR 乘用车 functional safety 认证仍在演化；(5) **供应链 lead time** — Sony 高端 IMX / FLIR Boson 在 2024-25 出现 12-24 月 lead time；(6) **二级市场** — 工业 LiDAR 二手不存在，故障即报废；(7) **算法生态** — DVS 算法库 vs 传统 RGB pipeline 差 5-10 年成熟度；(8) **新 paradigm** — 2025-11 DA 3 / VGGT-Ω / MapAnything 把单目/stereo/multi-view 边界打散（见 [`../depth-foundation/depth_models_comparison.md`](../depth-foundation/depth_models_comparison.md)），可能让 camera-only 在某些场景重新可用。

**正确读法**：作为**第一遍 filter** 淘汰明显不合的；剩 2-3 候选回 single-sensor dissection 查 worked example；最后 vendor EVK 实测再下单。**没有 matrix 替代真机测试**。

---

## Cross-references — 24 个 single-sensor dissection 的常用组合

**Aerial 主推 5 件套**：
- [imu_physics_and_noise_model](./imu_physics_and_noise_model.md) — 必备 baseline
- [gnss_multi_constellation_rtk](./gnss_multi_constellation_rtk.md) — 户外 absolute
- [stereo_camera_geometry_physics](./stereo_camera_geometry_physics.md) — 视觉避障
- [magnetometer_geomagnetic_field](./magnetometer_geomagnetic_field.md) — yaw 唯一绝对参考
- [barometer_pressure_altimetry](./barometer_pressure_altimetry.md) — vertical mid-term
- → 集成实战见 [`embodiments/aerial/sensor-stack/`](../../embodiments/aerial/sensor-stack/) + [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/) + [`embodiments/aerial/long-range-slam/`](../../embodiments/aerial/long-range-slam/)

**AD 主推 7 件套**：
- [rgb_camera_imaging_pipeline](./rgb_camera_imaging_pipeline.md) — BEV 主输入
- [rolling_vs_global_shutter](./rolling_vs_global_shutter.md) — 高速场景必 GS
- [lidar_physics_905_vs_1550](./lidar_physics_905_vs_1550.md) — geometric truth
- [mmwave_radar_physics_for_ad](./mmwave_radar_physics_for_ad.md) — 天气韧性
- [gnss_multi_constellation_rtk](./gnss_multi_constellation_rtk.md) — loose-coupling localization
- [imu_physics_and_noise_model](./imu_physics_and_noise_model.md) — tactical-grade
- [thermal_ir_lwir_8_14um](./thermal_ir_lwir_8_14um.md) — 夜视 / 行人（可选，Tesla 例外）
- → 集成实战见 [`embodiments/driving/`](../../embodiments/driving/) + [`embodiments/driving/waymo_vs_tesla_doctrinal_split.md`](../../embodiments/driving/waymo_vs_tesla_doctrinal_split.md)

**Manipulation 主推 4 件套**：
- [stereo_camera_geometry_physics](./stereo_camera_geometry_physics.md) — D435 wrist
- [tof_physics_for_embodied_ai](./tof_physics_for_embodied_ai.md) — L515 dense depth
- [active_nir_850nm_for_embodied_ai](./active_nir_850nm_for_embodied_ai.md) — 暗光 / textureless
- [rgb_camera_imaging_pipeline](./rgb_camera_imaging_pipeline.md) — color + features
- → 集成实战见 [`embodiments/manipulation/`](../../embodiments/manipulation/)

**Marine 主推 3 件套**：
- [underwater_sonar_physics](./underwater_sonar_physics.md) — 水下唯一可信
- [gnss_multi_constellation_rtk](./gnss_multi_constellation_rtk.md) — 水面 RTK
- [imu_physics_and_noise_model](./imu_physics_and_noise_model.md) — tactical / FOG
- → 集成实战见 [`embodiments/marine/sensor_stack_underwater.md`](../../embodiments/marine/sensor_stack_underwater.md) + [`embodiments/marine/underwater_slam_dvl_sonar.md`](../../embodiments/marine/underwater_slam_dvl_sonar.md)

**通用噪声框架**（跨所有 embodiment）：
- [sensor_noise_modeling_allan_variance](./sensor_noise_modeling_allan_variance.md) — IMU / camera / LiDAR / radar 统一到一个 Allan plot
- [event_camera_dvs_physics](./event_camera_dvs_physics.md) — 跨 embodiment 的新 sensor 范式
- [polarization_sensing_for_3d](./polarization_sensing_for_3d.md) — 玻璃 / 透明物体物理解

**跨 embodiment BOM 矩阵** (本文 + 6 embodiment 的应用层综合) → [`../../crossing/sensor-stack-matrix/`](../../crossing/sensor-stack-matrix/)

---

## Boundary

- **本文档位置**：comparison（24 个 single-sensor dissection 后的元视图），不走 14 项 dissection 门槛 — 核心是横向对比表 + 决策树
- **per-sensor 物理深拆**（QE / Allan plot / 失败模式细节）→ 回各 single-sensor dissection
- **per-embodiment 集成实战**（calibration / 安装位置 / 同步）→ [`embodiments/<emb>/sensor-stack/`](../../embodiments/)
- **跨 embodiment BOM SWaP-C 矩阵**（6 embodiment × 8 sensor class）→ [`crossing/sensor-stack-matrix/`](../../crossing/sensor-stack-matrix/)
- **vendor / SKU 选型 / 供应链**（D435 vs V100 vs Boson）→ [`deployment/hardware-selection/`](../../deployment/hardware-selection/)
- **Sensor + ML 融合算法**（RAFT-Stereo / Polarization-NeRF）→ [`foundations/feed-forward-3d/`](../feed-forward-3d/) + [`foundations/depth-foundation/`](../depth-foundation/)

---

[← Back to Sensor Physics](./README.md)
