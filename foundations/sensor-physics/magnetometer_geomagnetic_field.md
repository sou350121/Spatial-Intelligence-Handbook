# Magnetometer & Geomagnetic Field (磁力计与地磁场 — 硬铁 / 软铁 / drone yaw 估计)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 地磁场 / WMM 模型 / 硬铁软铁畸变 / drone yaw 校准
> **核心定位**：drone yaw 估计的**唯一**绝对参考 — gravity 给 pitch+roll，magnetometer 给 yaw；但被机身电流 / 钢筋建筑 / 高压线 反复污染，校准失败是 drone 起飞 toilet bowl 的头号嫌疑

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字需 datasheet 交叉核对。
**Wedge tier:** sensor-physics expansion（E 桶 drone stack 第 2 篇）

### X-Ray opening

IMU + accelerometer 可以推出 pitch + roll（重力是绝对参考），但 yaw 在 IMU 上**永远漂**（gravity 对 yaw 不敏感）。所以每个室外 drone（DJI / Skydio / Anduril）都装 magnetometer 当 yaw 绝对参考。但它的输入是地磁场——一个 25–65 µT 的微弱信号——而 drone 自己的电流 / 永磁马达 / 锂电池都产生类似量级的局部磁场。**校准不充分的 drone 起飞 = "toilet bowl" 圆周漂移**。学界 VIO 综述几乎不写这条，但 drone 制造商售后率排第一的失败模式。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1600 ── Gilbert "De Magnete" ── 地球是磁铁，物理基础
1831 ── Faraday induction ── 电磁原理
1980s ── Fluxgate magnetometer ── 高精度但大体积，军用
2000s ── Honeywell HMC 系列 AMR magnetometer ── 小型化
2010 ── AKM AK8963 (MPU-9250 内嵌) ── 9-DoF IMU 时代开启
2014 ── Bosch BMM150 ── drone 主力，cheap + 准
2018 ── PNI RM3100 ── 高端，~$30，10× 噪声低于 BMM150 `UNVERIFIED`
2020 ── ST LIS3MDL ── 手机 / wearable 主流
202? ── ?  下一波：on-die hard/soft iron 自校准（待实证）
```

---

## 1 · 地磁场物理

📌 **Napkin Formula**：`B_local = B_earth + B_hard_iron + R_soft_iron · B_total`，其中 B_earth ~50 µT 量级，B_hard_iron 是机身永磁体造成的固定偏置（vector），R_soft_iron 是软铁畸变矩阵（3x3，affine 拉伸 / 旋转）。

**(a) 地磁场分布.** 总强度 25–65 µT (microtesla)，赤道弱（~25 µT），磁极强（~65 µT）。倾角 (inclination)：磁场矢量与水平面夹角，赤道 ~0°，磁极 ±90°。偏角 (declination)：magnetic north 与 geographic north 偏差，全球 -20° 到 +20°，每年漂 0.1° 量级。**WMM (World Magnetic Model)** — NOAA + UK British Geological Survey 联合维护的 5 年期模型，drone 固件每次更新随固件同步。

**(b) Sensor 物理.** 三种主流：
- **AMR (Anisotropic MagnetoResistance)**：NiFe 薄膜在磁场下电阻各向异性变化。Honeywell HMC 系列 / Bosch BMM150。低成本，±100 µT 量程。
- **TMR (Tunneling MagnetoResistance)**：MgO 隧道结，sensitivity 比 AMR 高 5–10×。PNI RM3100 (基于 inductive sensing) 是工业 drone 高端选择。
- **Hall effect**：Lorentz 力 → 横向电压。便宜但 noise 大，仅在罗盘玩具。
- **Fluxgate**：高磁导率芯柱被驱动到饱和 → 二次谐波 ∝ 外场。航空 IMU 用，但成本 / 体积大。

⚡ **Eureka Moment.** Magnetometer 读的不是 yaw — 是**3D 磁场矢量**。把它转换为 yaw 需要 4 个独立的几何假设全部成立：(1) sensor 已被硬铁校准；(2) 已被软铁矩阵线性变换校准；(3) 知道当前位置的 declination；(4) 知道机身姿态（pitch+roll）来 tilt-compensate。**任一破 → yaw 误差几度到几十度。**

---

## 2 · 典型 sensor 对比

| Sensor | Vendor | Resolution `UNVERIFIED` | Noise (typical) | 量程 | 价格 | 应用 |
|---|---|---|---|---|---|---|
| **AK8963** | AKM | 0.15 µT | 0.6 µT rms | ±4900 µT | $1 (MPU-9250 套件) | 消费手机 / 旧 drone |
| **BMM150** | Bosch | 0.3 µT | ~0.5 µT rms | ±1300 µT (xy), ±2500 µT (z) | $2 | drone 标配 |
| **LIS3MDL** | ST | 0.15 µT | ~3 mG ≈ 0.3 µT | ±16 G | $2 | 手机 / wearable |
| **HMC5983** | Honeywell | 0.5 µT | ~2 mG | ±8 G | $5 | drone 中端 |
| **RM3100** | PNI | 13 nT | ~15 nT rms | ±800 µT | $25 | 高端工业 / mapping drone |
| **HMR2300** | Honeywell | 70 nT | ~7 nT rms | ±2 G | $700 | 测量级，超出 drone |

drone 实战：BMM150 是 PX4 / ArduPilot 默认；RM3100 在 mapping drone（DJI M300 RTK / Wingtra）上常见。

---

## 3 · 硬铁 + 软铁畸变 — drone 真正的工程挑战

**(a) 硬铁 (Hard Iron)** — 机身上的永磁源造成的**固定 offset**。来源：永磁马达定子、扬声器、磁铁锁扣。在 sensor frame 测出 `B_meas = B_earth + B_hard`，B_hard 是常向量，~5–50 µT 量级 — **常常比地磁场本身还大**。

**(b) 软铁 (Soft Iron)** — 高磁导率材料（铁 / 镍 / 某些不锈钢）在外场下**重新组织**磁力线 → sensor 测到的磁场方向 / 强度都被扭曲。数学上 = 3x3 affine matrix R_soft，把球面读数映射到椭球面。来源：碳钢螺丝、含镍合金、PCB 上的电感铁芯。

**(c) 电流诱导磁场.** drone ESC 输出 30–100 A 峰值电流 → Biot-Savart `B = µ₀I/(2πr)` → 5 cm 距离处 0.4–1.3 mT，**远超**地磁场量级。**对策**：sensor 装尾部 / 顶部，离 ESC + 电池总线 >15 cm；电流增大时（hover→上升）yaw reading 跳变是常见 failure mode。

⚡ **关键**：硬铁 / 软铁误差与机身**捆绑**，每装一次 / 每加一个 payload 都需要重校准。这就是为什么 DJI app 每次重大变更后要求 "compass calibration figure-8"。

---

## 4 · Worked example — drone 起飞前 figure-8 校准

```
Setup:  DJI / PX4 类 drone，BMM150 magnetometer，校准目标 hard iron offset + soft iron matrix
方法:   手持 drone 在所有 3 轴空间绕一遍（典型 figure-8 + 翻转）30 秒
原理:   收集 N>1000 个 3D magnetometer samples
        理想情况下，samples 应均匀分布在一个球面上（半径 = 地磁场强度）
        实际：samples 分布在一个**偏移 + 拉伸**的椭球上
拟合:   ellipsoid fitting → 椭球中心 = hard iron offset
                          椭球轴矩阵 = soft iron correction matrix
```

**数学**（简化）：椭球方程 `(B - C)ᵀ A (B - C) = r²`。
- C ∈ R³ = hard iron offset vector → store
- A ∈ R³ˣ³ symmetric positive definite → eigen-decompose → soft iron correction R = A^(1/2) → store
- 校准后 `B_corrected = R · (B_meas - C)` → 落在半径 r 的球面

**实战结果**：好的校准 → residual &lt;1 µT rms → yaw error &lt;2°。差校准（旋转不充分 / 旁边有钢椅）→ residual >5 µT → yaw error >10° → drone 起飞 toilet bowl。

**Pi PX4 工具**：QGroundControl "Compass Calibration" 实现这个流程，30 秒采样 + ellipsoid fit on-board。

---

## 5 · electrical interference — drone 上的电流威胁

drone hover 状态 ESC 电流 ~10–20 A；急加速 / 翻转 60–100 A。Biot-Savart 在 10 cm 距离：

```
B = µ₀ · I / (2πr)
  = (4π × 10⁻⁷) · 50 / (2π · 0.10)
  = 100 µT
```

即 50 A 电流在 10 cm 处产生 100 µT 磁场 — **是地磁场 (50 µT) 的 2 倍**。这就是为什么：
- magnetometer 应**远离**电池正负总线、ESC、马达
- 用**屏蔽双绞** power 线减少回路面积（双绞抵消磁场）
- 在 IMU 模块 GPS+compass 一体（top mast）上装 — 离电流核心 15+ cm

**实战 failure**：用户加装 LED 灯带 / 摄像头云台引入新电流回路 → yaw 突然有 ~5° offset，飞机航向漂。需要重新校准。

---

## 6 · 局部磁场异常

地图上 WMM 模型给的是**几十公里尺度**的平滑场。局部异常无法预测，常见来源：

- **钢筋混凝土建筑** — 大量铁筋。室内距墙 1 m 内场强可漂 5–15 µT，方向也变。drone 室内起飞经常磁罗盘失准。
- **高压输电线** — AC 50/60 Hz 磁场。直接下方 1 m 处 ~10 µT @ 60 Hz。drone 沿线巡检需特殊校准 + IMU 主导 yaw。
- **地铁 / 火车** — DC 1.5 kV 牵引电流产生缓慢漂移 + 列车经过时尖峰。
- **磁矿区** — 极端情况，地磁场方向可反转。瑞典 / 西伯利亚某些区域 drone 自动转 IMU-only yaw。
- **铁桥 / 钢架塔** — 大尺度钢结构会扭曲场到 50 m 距离。

**对策**：drone 内部信号 = 一致性检查（compare 多个 mag / accel + GNSS course over ground），异常时降级到 IMU-only yaw + GNSS heading（速度足够时）。

---

## 7 · Hidden Assumptions — magnetometer 默默押注的前提

下游 EKF / heading 估计假设这些条件成立：

- **机身电流稳定.** Hover 与 high-throttle 之间硬铁偏置相同。Throttle 跳变 → yaw 跳变。
- **机身没有动态磁源.** 没有可活动的钢/磁性部件（pan-tilt 云台 stabilizer 上的电磁体除外）。
- **当地 declination 已知.** GPS lock 后即可查 WMM；GPS-denied 时假设上次飞行同位置。
- **没有大型钢结构在 50 m 内.** 室内 / 桥下 / 仓库 严重破。
- **Pitch + roll 已知（来自 accel）.** Tilt-compensate 需要它。Aggressive maneuver 中 accel 受 specific force 污染 → tilt-compensate 错。
- **校准在 deployment 温度范围有效.** 大温度变化（地面 -10°C 到飞行 -30°C）→ 磁性材料 magneto-thermal 漂移。
- **没有强电磁干扰源.** 高压线 / 雷达 / 强 RF 发射机。

破其一即 yaw 错几度到几十度。

---

## 8 · 跨 embodiment 比较 + interview tip

| Embodiment | Magnetometer 角色 | one driver | 主要 failure mode |
|---|---|---|---|
| **Drone (outdoor)** | yaw 绝对参考（必备） | 没它 = IMU yaw 漂 + GNSS course 只在高速可用 | 校准失败 / 钢结构 / 电流 |
| **Drone (indoor)** | 不可靠，降级到 IMU + VIO yaw | 钢筋建筑磁场紊乱 | 不再信任 |
| **Humanoid** | head heading 估计（可选） | 同 drone 但更慢 | 室内电梯 / 大型 motor 干扰 |
| **Manipulation** | 不用 | 工作空间几何已锚定到 base | 不适用 |
| **AD car** | 罕用（GNSS + IMU + map matching 足够） | yaw 高频信号已有 | 大量铁制车身 self-distortion |
| **Marine (surface)** | yaw 主力（远离铁矿 / 电厂时） | 没 GNSS yaw alternative | 船体钢板 → 重校准复杂 |
| **AUV** | 几乎不用 | 海水盐度变化 + 船体 self-distortion | 通常用 FOG yaw |

经验：room-scale embodiment（manipulation / humanoid）室内 magnetometer 不可靠；**field-scale embodiment**（drone / car / marine 表面）才用。

**🎙️ Interview Tip.** 被问 "drone yaw 为什么有时会漂 5°"？— 三层答：(1) 校准椭球拟合 residual >3 µT（未做充分 figure-8）；(2) 加装 payload 后 hard iron offset 改变未重校准；(3) 飞过铁制 / 高压线区域局部场扰动。一次性命中 calibration / config-change / env 三层。

---

## 9 · For the reader

- **Drone engineer** — BMM150 起步，每次硬件变更 figure-8 校准；EKF 内做 in-flight innovation gating。
- **Indoor robot** — 别信 magnetometer，用 VIO + lidar 锚定 yaw。
- **Mapping drone** — RM3100 + 严格电磁屏蔽 + WMM 当年版本同步。
- **Marine surface vessel** — fluxgate 或多 mag 冗余，远离铁制甲板。
- **AUV / submarine** — 跳过 mag，用 FOG yaw（见 `imu_physics_and_noise_model.md`）。

---

## References

- Bosch BMM150 datasheet `UNVERIFIED, no DOI`
- PNI RM3100 datasheet `UNVERIFIED, no DOI`
- NOAA World Magnetic Model (WMM) 2025
- "MagNav" — magnetometer-based navigation primer (MIT Lincoln Lab)
- PX4 / ArduPilot compass calibration source
- Sabatini, "Variable-State-Dimension Kalman-Based Filter for Orientation Determination Using IMU and Magnetometer" (Sensors 2012)

## Boundary

- `imu_physics_and_noise_model.md` — IMU yaw 漂移性质（与 mag 互补）
- `gnss_multi_constellation_rtk.md` — GNSS course over ground 作为 yaw 备份
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — magnetometer 在 6 embodiment 上取舍
- `embodiments/aerial/sensor-stack/` — drone compass 集成实战
- `embodiments/aerial/vio/` — VIO yaw 与 mag 融合

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
