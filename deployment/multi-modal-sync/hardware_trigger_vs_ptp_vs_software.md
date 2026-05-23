# 硬件触发 vs PTP vs 软件时间戳 / Hardware Trigger vs PTP vs Software Timestamp

> **发布时间**：2026-05-21
> **适用范围**：RGB + Depth + IMU + LiDAR + IR 任意组合的时间轴对齐
> **核心定位**：三档同步方案的工程对照——什么时候哪一档够用，错位多少 ms 会让什么算法崩。

**Status:** v1 — opinionated draft。具体抖动 / 偏置 / 漂移数字标 `UNVERIFIED`，需以平台实测为准。
**Wedge tier:** N/A（deployment 工程文）
**TL;DR:** 同步不是「越严越好」，是「匹配平台动态」。Drone 250°/s 角速度下 1 ms 偏置 = 0.25° 旋转误差；AGV 1°/s 角速度下 1 ms 偏置 = 0.001°——同样的偏置，一个毁 VIO，一个完全无感。本文把「硬件触发 < 0.1 ms」「PTP 1–10 µs」「软件时间戳 1–100 ms」三档落到具体平台与算法的容忍度上。

### X-Ray 开场（非专家友好）

(a) 同步 = 给所有 sensor 一个共同时间轴；三档实现方式从严到宽。(b) 严不严的对错取决于平台动态：drone 与 AD 必严，桌面 manip 可松。(c) 对系统 / 嵌入式 / VIO 工程师，本文回答「哪一档够用 + 错位多少 ms 会崩」。

### 📍 研究全景时间线

```
2010 ── ROS 1 时代：bag 录制各设备本地时钟；同步靠 message_filters 拉齐
2014 ── VINS / OKVIS 把 td（time delay）作为状态联合估计——软件兜底标配
2018 ── IEEE 1588v2 PTP 量产化；汽车 OEM 把多相机栈搬到 PTP
2020 ── PX4 / Pixhawk 普及硬件触发相机；研究 drone 标配
2023 ── ROS 2 + DDS 把 PTP 化为推荐方案；但默认不开
2025 ── 端到端 AD 栈：6+ 相机 + LiDAR + radar 全部 PTP 强制
        ── 你在这里 (2026) ──
?    ── all-PTP 边缘 SoC（Orin + 自带 PTP PHY）？已在路上
```

---

## 1 · 三档方案对照（扩展）

📌 **Napkin Formula**:

```
angular_error_per_ms = ω × 1ms
  ω = 1°/s   → 0.001° / ms     ← AGV / manip：100ms 偏置 = 0.1°，几乎无感
  ω = 30°/s  → 0.03° / ms      ← 人形头部 / 中速 AD：10ms 偏置 = 0.3°
  ω = 250°/s → 0.25° / ms      ← drone 急转 / racing：1ms 偏置 = 0.25°，VIO 边缘
```

一行就能算出哪档够用。

| 维度 | A. 硬件触发 | B. PTP / gPTP | C. 软件时间戳 |
|---|---|---|---|
| 时钟偏置 `UNVERIFIED` | <0.1 ms | 1–10 µs | 1–10 ms 初始 |
| 抖动 `UNVERIFIED` | µs 级 | µs–ms 级 | 10–100 ms |
| 漂移 | 零（同源） | 网络 / 温度 | 晶振 + USB / 串口缓冲 |
| 硬件要求 | MCU/FPGA + 触发线 | PTP-aware NIC + PHY | 任意 |
| 软件要求 | 驱动支持外触发 | linuxptp + 内核时钟 | 仅时间戳记录 |
| BoM 增量 | $50–500 `UNVERIFIED` | $200–2k `UNVERIFIED` | $0 |
| 部署难度 | 中（电气 + 驱动） | 高（网络拓扑） | 低 |
| Failure mode | 触发线断 / MCU 死 | 网络风暴 / grandmaster 丢 | 时间戳估错 |

---

## 2 · A 档 — 硬件触发（hardware trigger）

### 2.1 机制

一颗 MCU（或 FPGA / PX4 飞控）输出一根 GPIO 脉冲（TTL / LVDS），同时：

- 触发相机的 external trigger 引脚（曝光开始）
- 触发 IMU 的 DRDY / external sample 引脚
- 给主控一个中断，记录这一刻的"主时钟时间戳"

```
            MCU/FPGA
              │
   ┌──────────┼──────────┐
   │          │          │
   ▼          ▼          ▼
 cam EXP    IMU SMP    host IRQ
  ↓          ↓          ↓
 frame_t   imu_t      master_t   ← 同一瞬间，零偏置
```

### 2.2 优点

- **物理上同源**：所有 sensor 在同一脉冲沿采样，偏置纯由信号传输 + sensor 内部延迟决定，常 <100 µs。
- **不需要 PTP 网络**：单板 / 单 MCU 即可。
- **可观性强**：示波器一接就能验。

### 2.3 缺点 / 坑

- **不是所有相机都有外触发**：消费 RGBD（D435 经典）没有；工业相机（FLIR Blackfly、Basler ace）有。
- **rolling shutter 不算同步**：触发只决定第一行曝光时间；rolling shutter 整帧扫完要几 ms。global shutter 才算真触发。
- **驱动配合**：相机驱动要支持外触发模式（GenICam / GigE Vision / V4L2 各家不同）。
- **LiDAR 不是「曝光」**：旋转 LiDAR 是 scan，触发只能对 scan **起点**；motion compensation 必须叠加。

### 2.4 何时选

- Drone（强制）：电机 + 桨振 + 急转下，C 档必崩。
- 人形头部 stereo：30 Hz × 6 相机要同帧。
- AUV 高速：sonar ping 与 INS 必须同步到 1 ms 内。

---

## 3 · B 档 — PTP / gPTP（IEEE 1588）

### 3.1 机制

PTP 是网络时间协议（IEEE 1588-2019，gPTP 是 IEEE 802.1AS 子集），通过周期性 sync / follow-up / delay-request 报文，让网络上所有节点对齐到 grandmaster 时钟，硬件辅助（NIC PHY 打时间戳）下精度 1–10 µs。

```
       Grandmaster (GPS-disciplined)
              │
       PTP-aware switch
       ┌──────┼──────┬──────┐
       │      │      │      │
   cam-FL   cam-FR  LiDAR  radar
   (NIC PTP hw stamp on each frame)
```

### 3.2 优点

- **支持多节点 / 长距离**：AD 整车 6+ 相机分布在 4 个 ECU 上，PTP 是事实标准。
- **不需要专用触发线**：以太网线就够。
- **可观性中**：`ptp4l` / `phc2sys` 工具看 offset；硬件 PHY stamp 才达 µs 级。

### 3.3 缺点 / 坑

- **需要 PTP-aware NIC**：Intel i210 / i225、Realtek 部分型号、汽车 PHY。普通 NIC 退化到软件 PTP，精度 ms 级。
- **需要 PTP-aware 交换机**：BC（boundary clock）或 TC（transparent clock）；普通交换机会引入 ms 抖动。
- **Linux 配置坑多**：`linuxptp` + `phc2sys` + kernel `CONFIG_PTP_1588_CLOCK`；时区 / TAI vs UTC vs CLOCK_REALTIME 混淆很常见。
- **不解决 sensor 内部延迟**：sensor 收到指令到实际采样的内部延迟，PTP 看不到——还是要靠 sensor datasheet 或实测。

### 3.4 何时选

- 量产 AD（强制）：分布式 ECU 拓扑下 A 档电气上不可行。
- 多 robot fleet：跨 robot 的事件对齐。
- 园区低速 demo 车：6 相机 + 2 LiDAR + radar 跨 ECU。

---

## 4 · C 档 — 软件时间戳 + 在线估计

### 4.1 机制

各 sensor 在 host 端收到数据的瞬间，host 用本地 `CLOCK_MONOTONIC` 打时间戳。USB / 串口 / I2C 接收缓冲、驱动调度、kernel 抢占都会引入抖动。

下游算法把 `td`（time delay，例如相机相对 IMU）作为待估状态，与位姿一起优化（Kalibr / VINS / OKVIS / OpenVINS 都这么做）。

### 4.2 优点

- **零硬件代价**：USB 相机 + 串口 IMU 直接跑。
- **研究 / demo 友好**：跑个 EuRoC bag 即可。

### 4.3 缺点 / 坑

- **`td` 可观性条件苛刻**：纯直线匀速运动下 `td` 与平移耦合不可观；需要持续 6-DoF 激励才估得稳。
- **温度漂移**：晶振温漂使 `td` 随时间慢漂；上电估的值飞 10 分钟后可能差几 ms。
- **USB 突发抖动**：USB 调度 + Linux 抢占下，单帧延迟可能突跳 50 ms。
- **算法依赖**：换算法（VINS → ORB-SLAM）等于重估 `td`，且新算法可能不估。

### 4.4 何时选

- 桌面 manipulation：速度低，td 漂个 5 ms 无感。
- 室内 AGV demo：地图 prior 兜底。
- 研究 prototype：硬件就位前。
- **不要选**：drone、AD、高速人形。

---

## 5 · Worked Example — drone 200 Hz 控制 vs 30 Hz 相机

场景：1.5 kg 巡检 drone，控制回路 200 Hz（IMU 1 kHz），单目 + IMU VIO，相机 30 Hz global shutter。最大期望角速度 250°/s（急转 / wind gust 修正）。

### 5.1 各档下的相位误差

```
A 档（硬件触发，假设 100 µs 偏置）：
  ω_max × td = 250°/s × 0.0001 s = 0.025°
  → 远低于 IMU 单步噪声（~0.05° gyro bias × dt）
  → VIO 不受影响

B 档（PTP，假设 100 µs 偏置）：
  与 A 档同量级；可行。
  → 但 drone 上拉以太网 + PTP grandmaster 是 SWaP 杀手；通常不上 B 档。

C 档（软件时间戳，假设 5 ms 偏置）：
  ω_max × td = 250°/s × 0.005 s = 1.25°
  → 急转瞬间，相机以为飞机指向 A，IMU 已经在 B
  → VIO 残差被强行解释为状态误差 → 估姿偏 → 估速偏 → 控制偏 → 飞机摇头
  → 实际表现：温和飞行 OK，急转 / wind gust 下漂或发散
```

C 档在该平台**不可行**。这是为什么消费 drone（Skydio / Autel / DJI 顶级机型）都用 A 档。

### 5.2 时间戳设计

```
1) PX4 飞控（STM32 F7/H7）作为时序主：
   - GPIO0 → 相机 EXT_TRIG（30 Hz 上升沿）
   - SPI → IMU（1 kHz, IMU DRDY 引脚反向通知）
   - 内部记录每个事件的 micros() 时间戳

2) 飞控通过 MAVLink TIMESYNC 把时间偏置广播给 Jetson Orin Nano：
   - 主控 CLOCK_MONOTONIC ↔ 飞控 micros() 偏置
   - 周期性同步，纠正晶振漂移

3) Jetson 收到 30 Hz 相机帧（USB3）时，丢弃 USB 到达时间戳，
   用飞控广播的 "trigger 发出时刻" 作为帧时间戳。

4) IMU 数据由飞控以 1 kHz 流出，时间戳用飞控 micros()。

5) VIO 输入：（帧时间戳, IMU 时间戳）都在飞控时钟轴，偏置 <100 µs。
```

这套已是 PX4 + VIO companion computer 的事实标准。

---

## 6 · LiDAR motion compensation（绕一个坑）

旋转 LiDAR（Velodyne / Livox 旋转款）一帧 100 ms。期间车辆 / drone 已经动了。直接当 "瞬间快照" 拼图会拖尾。

- 标准做法：每个 LiDAR 点的本机时间戳 + ego-motion（IMU/wheel/VIO）→ 把点变换回 scan 起点位姿。
- 这要求 LiDAR scan **起点** 与 ego clock 严格同步（A 或 B 档）。
- 软件时间戳 + 旋转 LiDAR + 高速 → 拖尾几乎必然。

固态 LiDAR（Livox Mid-360、Hesai AT128）扫描方式不同，但 motion compensation 思路一致。

---

## 7 · 隐含假设（Hidden Assumptions）

- **`UNVERIFIED` 数字 ±2× 容差。** A < 0.1 ms / C 1–10 ms 的 *级差* 是结论；个别 SKU 实测可能落在边界外。
- **同步 ≠ 标定。** 时间对齐了，外参也得对——两者共轭但不等价；详见 `deployment/calibration/`。
- **rolling shutter 仍然有内部时延曲线。** 即便硬件触发，rolling shutter 整帧扫描期间 sensor 还在动；GS 优先。
- **PTP 软件实现退化到 ms 级**——必须硬件 stamp。
- **Sensor 内部固有延迟**（曝光中点 vs 触发沿、IMU 内部低通延迟）需查 datasheet 或示波器，PTP / 触发都看不到。

## 8 · 与同步方案的对比矩阵 + Interview Tip

| 场景 | 推荐 | 不推荐 |
|---|---|---|
| 桌面 manip + ROS 1 demo | C 软件 + Kalibr 估 td | A（过度设计） |
| 室内 AGV @ 1 m/s | C 或 B | A（成本不划算） |
| 1.5 kg 巡检 drone | **A 强制** | C |
| 250 g racer | A（极简版：PX4 自带触发） | — |
| 6-cam AD demo | **B 强制（PTP）** | A（电气不可行），C（直接报废） |
| 量产车 | B + 部分 A | C |
| AUV 长航 | A + INS 严格对齐 | C |

**Interview Tip**：问"为什么你 drone VIO 在急转弯漂"——别答"算法不行"，答 `ω × td` 算一遍。1 ms × 250°/s = 0.25°，整套数字逻辑摆出来，对方就明白你做过工程。

---

## References

- IEEE Std 1588-2019 (PTP) — `UNVERIFIED, IEEE`
- IEEE Std 802.1AS-2020 (gPTP) — `UNVERIFIED, IEEE`
- `linuxptp` — http://linuxptp.sourceforge.net/ `UNVERIFIED, no DOI`
- VINS-Fusion 在线外参 + td — Qin et al. *T-RO 2018* https://arxiv.org/abs/1708.03852
- Kalibr — Furgale et al. https://github.com/ethz-asl/kalibr
- PX4 camera trigger driver — https://docs.px4.io/main/en/peripherals/camera.html `UNVERIFIED, no DOI`
- OpenVINS — Geneva et al. *ICRA 2020* https://arxiv.org/abs/1910.00298

## Boundary

本文写时间轴对齐方案。**不写**空间外参标定（去 `deployment/calibration/`，那里 §4 写了 IMU-相机时间偏置在标定流程里的位置——time = 4th dim of calibration，两边互相 cross-ref）、单 sensor 物理（去 `foundations/sensor-physics/`）、ROS 2 / DDS QoS 调优（TODO `ros2_sync_pitfalls.md`）。本文 starter 配置不替代 production 同步验证——production 必须示波器实测 + 长时漂移 + 温度循环测试。

---

[← Back to Multi-Modal Sync README](./overview.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
