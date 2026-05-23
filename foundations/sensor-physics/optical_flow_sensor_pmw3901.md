# Optical Flow Sensor PMW3901 (光流传感器 — 30x30 px 低分辨率视觉 / drone 室内悬停)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 光流 sensor 物理 / PMW3901 / drone 室内悬停 + GNSS-denied 速度估计
> **核心定位**：drone GNSS-denied 速度估计的"沉默主力" — 30x30 像素就够给出 horizontal velocity，但需要 texture / 充足光线 / 几何范围匹配；学界 VIO 综述把这条当"已解决的 dataset"，实际它是 PX4 EKF 的关键 fallback

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字需 datasheet 交叉核对。
**Wedge tier:** sensor-physics expansion（E 桶 drone stack 第 4 篇）

### X-Ray opening

PMW3901 / Aurora 这类光流 sensor 是从 optical mouse 衍生的——30x30 像素 + 内建 motion-estimation DSP。Bill of materials $3，重量 &lt;1 g，drone 上塞一个就能在 GNSS-denied 室内 hover——这是 Crazyflie / Skydio / PX4 室内能力的关键。学界 VIO 综述基本不写它，因为它"算法太傻"（光流帧间相关）；但真正在 drone EKF 中它**填的是高频 velocity update gap**——VIO 慢、IMU 双积分爆、optical flow 100 Hz horizontal velocity 直接灌进 EKF，让室内 hover 从"理论"变"产品"。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1981 ── Horn & Schunck / Lucas-Kanade ── 光流算法奠基
1999 ── Agilent ADNS-2610 ── 第一颗集成 optical flow chip（光学鼠标）
2010 ── PX4FLOW open-source drone optical flow ── 基于 MT9V034 + STM32 外接
2014 ── PMW3901 (PixArt) ── drone 优化，集成 lens + DSP，~$3
2016 ── Crazyflie 2.x + PMW3901 ── 室内 hover 大众化
2020 ── Aurora 系列 ── 更高范围 / 暗光
2022 ── Bosch BHA260 PSI ── 工业级
202? ── ?  下一波：event-based optical flow on-die（SLAMcore / Prophesee 集成）
```

---

## 1 · 光流 sensor 物理

📌 **Napkin Formula**：`velocity = (Δpixel × distance_to_surface) / (focal_length × Δt)`。光流 sensor 不直接测速度——它测**帧间像素位移** × **到表面距离**。distance 通常由 range finder 或 stereo 提供（见 `range_finder_for_drone_altitude.md`）。

**(a) 内部结构.** PMW3901 = 低分辨率 CMOS imager (30x30 pix `UNVERIFIED`) + 自带 lens (FOV ~42° `UNVERIFIED`) + ASIC 做 sum-of-absolute-differences (SAD) block matching → 输出 `(dx, dy)` 整数像素位移 over SPI bus。

**(b) 几何**：sensor 看着地面，飞机相对地面横移 1 m → 像素移动量 = `1 m / d × f / pixel_pitch`，其中 d = altitude，f = focal length。例：d=1 m、f=4 mm、pixel pitch=8 µm → 1 m 横移 = 500 pixel 位移；而 sensor 只有 30 pixel → 单帧最大可测位移 ~30 pixel × 8 µm / 4 mm = 6 cm。对应 100 Hz frame rate → 最大可测速度 6 m/s @ 1 m altitude。

**(c) 角分辨率**：30 pixel × 42° FOV / 30 = 每像素 1.4° = 25 mrad。1 m altitude 处一个像素 ≈ 25 mm in world。**这就是 light flow 测速度精度的根本上限**——亚像素插值可压到 5–10 mm equivalent。

⚡ **Eureka Moment.** Optical flow sensor 解决的是 IMU 双积分 drift 的物理问题——IMU 提供 acceleration，二阶积分秒级就爆。Optical flow 提供 **velocity** (一阶量)，~100 Hz, drift 不累积。**这就是为什么 PX4 EKF 把 optical flow 当 inertial-velocity update**，不是 position update。

---

## 2 · 典型 sensor 对比

| Sensor | Vendor | Resolution `UNVERIFIED` | Max rate | 范围 | 价格 | 典型应用 |
|---|---|---|---|---|---|---|
| **ADNS-9800** | Avago | 8200 cpi | gaming mouse | &lt;1 cm | $5 | desktop mouse |
| **PMW3901** | PixArt | 30x30 px, ~120 fps | 7.4 rad/s | 0.08–10 m | $3 | drone, Crazyflie |
| **PAA5100JE** | PixArt | 35x35 px | similar | 0.15–5 m | $4 | mini drone |
| **PX4FLOW (legacy)** | PX4 | MT9V034 + STM32 | 250 Hz | 0.5–5 m | $50 | 早期 PX4 drone |
| **Aurora** (multiple) | various | 60x60 px | 200 fps | 0.1–20 m | $20+ | indoor robot |
| **Bosch BHA260** | Bosch | hi-res | — | low-light | $30 | 工业 robotics |

drone 实战：PMW3901 是 Crazyflie / Bitcraze flow deck 默认；PX4 mainline 推荐 PMW3901 / PAA5100。

---

## 3 · drone 集成 — PX4 EKF 怎么 fuse optical flow

```
optical flow sensor output:  Δpixel_x, Δpixel_y over Δt
                             quality byte (texture confidence)
              ↓
range finder (LiDAR / ultrasonic / barometer) → altitude d
              ↓
attitude (IMU) → body rotation rate ω, tilt R
              ↓
compensate: pixel flow includes rotation component
            (gyro × focal_length / pixel_pitch)
              ↓
velocity = (compensated_flow / d) × f_eff
              ↓
EKF velocity update:  innovation = v_measured - v_predicted
                      gating by quality + altitude validity
```

**关键**：rotation compensation 必须正确——sensor 看到的 flow 是 translation + rotation 的混合。drone pitch / roll 时即使悬停，optical flow 也会读出明显信号。**没有 IMU rotation compensation 就用 optical flow，会把姿态变化误认为速度，飞机直接 toilet bowl。**

PX4 EKF2 / EKF3 把光流当作 NED-frame velocity update (after tilt compensation)，~100 Hz。VIO + optical flow + range finder 三方互校。

---

## 4 · Worked example — 5 m/s 飞行下 optical flow 信号率

```
Setup:  PMW3901, altitude d = 1.5 m, FOV ~42°
         pixel resolution 30 × 30
         focal length f equivalent 4 mm
         pixel pitch ≈ 9 µm (1.5 mm sensor / 30 / ... 估算)
         frame rate 100 fps → Δt = 10 ms
         velocity v = 5 m/s horizontal
```

每帧像素位移：
```
Δpixel = (v · Δt / d) × (f / pixel_pitch)
       = (5 × 0.01 / 1.5) × (0.004 / 9e-6)
       = 0.0333 × 444
       ≈ 14.8 pixel/frame
```

14.8 pixel / 30 pixel ≈ **50% sensor 视野** — 临界。超过 30 pixel/frame (~10 m/s 在 1.5 m altitude) sensor 不能 track（搜索窗口爆）。

**这就是 PMW3901 的 7.4 rad/s 飞行速度上限**——把 altitude 当变量，max velocity ≈ d × 7.4 / s。0.5 m altitude → 3.7 m/s；3 m altitude → 22 m/s 但 spec 限 10 m 距离上限。

**降级**：fast forward flight 时 sensor 失锁 → quality byte 降低 → EKF 自动减权或拒绝。**对策**：fast cruise 时切到 visual VIO + GNSS 主导，optical flow 只在 hover / 慢移使用。

---

## 5 · Failure modes (drone 实战)

| Failure | 触发 | 表现 | 对策 |
|---|---|---|---|
| **Low light** | &lt;50 lux 室内 / 夜飞 | quality byte 降，flow=0 | LED auxiliary illumination |
| **Textureless surface** | 光滑地板 / 雪 / 单色地毯 | quality 极低 | 加纹理贴纸 / 沙地避免 |
| **Fast motion** | >7 rad/s 角速度 | 像素位移 >30 → 丢锁 | 慢飞 / 切 VIO |
| **High altitude** | >10 m (PMW3901 spec) | 信号微弱 | 改用 stereo 视觉 VO |
| **Strobe / IR flicker** | LED 强 flicker | 帧间一致性破 | dimming / DC LED |
| **反光 / 水面** | 镜面反射 | 假 flow 来自反射 | reject by quality |
| **Rotor downwash 灰尘** | 起飞瞬间地面尘 | 灰尘飞舞 → 假 flow → 飞机晃 | 起飞 throttle ramp |
| **过低 (&lt;8 cm)** | landing 最后阶段 | sensor 焦距 / mfg 限制 | 切 range finder only |

实战：Crazyflie 厂家文档明确说"光面瓷砖 / 透明玻璃地板会失败"，推荐起降区铺纹理垫。

---

## 6 · Hidden Assumptions — optical flow 默默押注的前提

- **Sensor 视野内有 textured surface.** 沙石 / 草地 / 砖 / 木纹 OK；瓷砖 / 雪 / 水面 fail。
- **Altitude 在 sensor 范围内（PMW3901: 8 cm–10 m）.** 太低焦距 / 太高信号弱。
- **IMU rotation 准确 + 同步.** 时间偏差 >10 ms → rotation compensation 错 → velocity bias。
- **Surface 静止.** 流动河面 / 大风草地 / 移动地毯 → flow 包含 surface motion → 飞机以为自己在飞。
- **充足光线 (>50 lux typical).** 夜飞需要 LED illumination。
- **没有 strobing 光源.** Dimmer LED / 荧光灯 50 Hz flicker 可能干扰。
- **Lens 干净.** 灰尘 / 雾气覆盖镜片 → 减少 sharp edges → quality 降。
- **Range sensor 与 flow sensor 看同一表面.** range finder 看到斜坡而 flow 看到地面 → distance 错。

---

## 7 · 跨 embodiment 比较 + interview tip

| Embodiment | Optical flow 角色 | 替代方案 |
|---|---|---|
| **Drone (indoor hover)** | velocity 主力 | VIO 单独 → cost / power 增加 |
| **Drone (outdoor)** | 备份，与 VIO + GNSS 互校 | GNSS 主导，flow 是 anti-spoof check |
| **Crazyflie nano drone** | 必备（VIO 计算预算不够） | 无 |
| **AGV / ground robot** | 罕用（轮速里程计已有） | 不需要 |
| **Manipulation** | 不用（base 静止） | 不适用 |
| **AD car** | 不用（GNSS + 轮速 + 视觉 VO） | 不适用 |
| **Marine surface vessel** | 不用（水面 flow 来自波浪 noise） | DVL 替代 |
| **AUV** | DVL (Doppler Velocity Log) acoustic 等价物 | DVL |

**🎙️ Interview Tip.** 被问"为什么 Crazyflie nano drone 能室内 hover 但 RealSense 不在板上"？— optical flow + range finder + IMU 三件套总功耗 &lt;0.5 W、重量 &lt;5 g、CPU 占用 0%（all on-chip DSP）；VIO 需要 ~5 W CPU + 10 g sensor + 算法栈。20 g 飞机塞不下 VIO，塞得下 flow。

---

## 8 · For the reader

- **Nano drone (&lt;100 g)** — PMW3901 + ToF range finder + IMU = 完整室内 hover stack。
- **Mid-size drone (1–3 kg)** — flow as backup，VIO 主导，但 fast yaw 时 flow 救命。
- **Industrial mapping drone** — 跳过 flow，靠 RTK + IMU + VIO。
- **Indoor ground robot** — 不用 flow，轮速里程计 + lidar 即可。
- **AUV** — DVL 替代（acoustic optical flow 类比）。

---

## References

- PixArt PMW3901 datasheet `UNVERIFIED, no DOI`
- Honegger et al., "An Open Source and Open Hardware Embedded Metric Optical Flow CMOS Camera for Indoor and Outdoor Applications" (ICRA 2013) — PX4FLOW 论文
- Bitcraze Crazyflie Flow Deck 文档
- PX4 EKF2 optical flow integration source
- Lucas & Kanade, "An Iterative Image Registration Technique with an Application to Stereo Vision" (IJCAI 1981)

## Boundary

- `imu_physics_and_noise_model.md` — IMU 提供 angular rate 给 rotation compensation
- `range_finder_for_drone_altitude.md` — altitude 输入给 flow→velocity 转换
- `stereo_camera_geometry_physics.md` — 更高端 alternative
- `rgb_camera_imaging_pipeline.md` — 全分辨率 visual VO 对比
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment 取舍
- `embodiments/aerial/sensor-stack/` — flow deck 集成实战
- `embodiments/aerial/vio/` — VIO + flow 融合

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
