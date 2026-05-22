# 真机飞起来不炸的工程坑 (Real-Flight Production Gotchas — from First Hand-Flight to Onboard Autonomy)

> 📚 **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲) lab1 / lab2 / lab3
> 📜 **License**: 原始 lab PDF + lab/uav_ws 代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本文为改写 + 补充教材，依 BSD 3-Clause 保留版权声明
> 🛡️ **内容定位**：所有 gotchas 来自 HKUST 一线 TA 真实踩过的坑（lab PDF 警告章节 + `uav_ws/src/px4ctrl` 注释 + `nxt1.14.3_5660_2026.params` 客制值），非泛论

**Status:** v1 — opinionated draft，runbook 风格，配套 `dynamics_and_control_primer.md` 与 `vio/ekf_from_scratch_dissection.md` 的"理论 → 真机"接续。具体硬件型号 / 固件版本 / 阈值数字按 lab PDF + px4ctrl config 标注；未在源材料出现的量化数字一律 `UNVERIFIED`。**Doc type:** runbook（不走 dissection 14 项）。
**TL;DR:** Handbook 多数 dissection 教 *如何拆 VIO 库*；本文教 *让你自己拼的四旋翼第一次飞起来、且不炸*。坑按时间顺序串五道门：组装 → PX4 刷参 → 手飞 → OptiTrack 接管 → onboard VO/EKF 接管。每步 HKUST TA 都写在 lab PDF 的 "!!!" 警告里，本文给物理解释 + 失败信号 + 缓解。真机 sim2real gap 不是"controller 调不准"，而是"基线 24V 不到飞起来就掉电、磁罗盘没关导致 yaw 转圈、mocap 第一帧还没到你已 takeoff、VIO 初始化飘 0.5 m 你的 setpoint 已经过来"——Isaac Sim 里全部不存在。HKUST ELEC5660 用客制 PX4 1.14.3 固件 (`NxtPX4v2`) + `px4ctrl` ROS 控制器 + `RI_Mocap` VRPN 桥，把 3 个 lab 串成"组装 → API → onboard 自主"完整闭环。

### X-Ray 开场（非专家友好）

(a) 一架自主四旋翼从零件到 onboard 自主飞要过五道门，每道门都有"看着没事起飞就翻"的失败模式。(b) HKUST 把 3 个 lab 串成完整闭环，本文逐门列 TA 在 "!!!" 段写下的真坑。(c) 对 robotics / spatial 工程师：本文回答"sim 里 controller / VIO / planner 都通了，搬上真机为什么会翻"——这是大多数线上 MOOC 不闭环的 gap。

---

## 1 · 组装阶段 gotchas (lab1)

> **来源**: lab1.pdf §"Assembled Quadrotor" → "Check Motors & Direction" → "Before Flight"。

机械装配的失败大多 *不会在静态检查暴露*，要等通电 / 起飞才知道。lab1 PDF "!!!" 段反复警告四件事：

### 1.1 桨叶旋转方向必须 CW/CCW 对角配对

PX4 默认 X 型 motor 编号与旋向（lab1 §"Please Remove All Propellers"）：M1 前右 CW、M2 后左 CW、M3 前左 CCW、M4 后右 CCW。装错 → 反扭矩不平衡 → toilet bowl 自旋 → 起飞翻。lab1 PDF: "**This step is very important, please check carefully**"，要求 TA 亲检。

**自检（无桨）**：起飞前 arm 微给油门肉眼看旋向，或用 QGC Motor Test 逐个测。

### 1.2 ESC 焊接 / BEC 短路

lab1 PDF Soldering 段三条 "!!!"：不要碰 400°C 烙铁、刚焊完不要碰焊点、热熔胶。焊接质量本身的失败模式：

- **冷焊**：焊点光亮但内部未润湿 → 起飞振动几秒后开路，单 motor 失速 → 翻。
- **桥接短路**：相邻焊盘锡桥 → 上电瞬间 ESC 烟。
- **BEC 反接**：HKUST 的 4-in-1 ESC + NxtPX4v2 通过 VBAT 给 ESC 供电、ESC 的 BEC 给 FC 供 5V，接反 → FC 烟。lab1 Wiring 图明确标 VBAT (2-6S) 与 BEC 走向。

**自我检查**：通电前用万用表 continuity 扫 VBAT-GND、5V-GND 无短路。

### 1.3 CG（重心）偏移

`px4ctrl/config/ctrl_param_fpv.yaml` 写死 `mass: 1.2 # kg`，controller 前馈推力按 1.2 kg 算。电池 / Jetson / RealSense 装偏：CG 偏前 → hover 持续 pitch 后仰补偿，integrator 饱和后失控；CG 偏侧 → roll 偏置，航迹"画 S"。lab1 Part 6 的相机支架 + Jetson 装载板 + 电池绑带有固定孔位，按 BOM 装完 CG 自然落几何中心 ±5mm `UNVERIFIED`。

### 1.4 Propeller 平衡

`UNVERIFIED`：lab1 PDF 没明示但桨叶不平衡会显著推高 100-400 Hz IMU 噪声（见 §6）。生产环境上桨叶平衡器，教学环境通常跳过。

---

## 2 · PX4 ESC calibration + bootloader (lab1 Part 1-3)

HKUST 用客制飞控板 **NxtPX4v2** + 客制 PX4 1.14.3 固件 + bootloader + params 套件 (`nxt1.14.3_5660_2026.params`)。通用 PX4 流程类似——HKUST 把 multi-sensor 抑制 / 通讯 baud 写死在 params 避免学生踩坑。

### 2.1 客制 params 关键值（一手出处）

来自 `/lab/lab1/px4/nxt1.14.3_5660_2026.params` 的硬约束：

| Param | Value | 用意 |
|---|---|---|
| `BAT_N_CELLS` / `BAT_V_EMPTY` / `BAT_V_CHARGED` | 6 / 3.30 / 4.20 V/cell | 6S 锂电（lab1: ≥23.0V 才允许起飞）|
| `BAT_LOW_THR` / `CRIT_THR` / `EMERGEN_THR` | 0.15 / 0.07 / 0.05 | 容量三级阈值 |
| `SYS_HAS_MAG` | 0 (lab1 §"Disable Magnetometer") | **完全关闭磁罗盘** — 室内 mocap + 电机磁场污染 + GNSS-denied，磁罗盘反而是负贡献；yaw 由 mocap (lab2) / VIO (lab3) 提供 |
| `SENS_FLOW_ROT` | Yaw 270 | optical flow 安装方向旋转修正 |
| `SER_GPS2_BAUD` / `SER_TEL1_BAUD` / `SER_TEL2_BAUD` | 921600 / 57600 / 115200 | GPS2 / 手柄遥测 / onboard 通讯串口 |

### 2.2 ESC calibration（通用版）

lab1 PDF 没单独列（4-in-1 ESC 出厂校准），但通用 PX4 用户初用 ESC 必做：

1. **移除所有 propellers**（lab1 PDF 反复强调）。
2. QGC → Power → Calibrate ESCs，PX4 发 max throttle 信号 → 断电再上电 → 发 min throttle 信号。

**失败信号**：单 motor 起转速低 / arm 后怠速不一致 → ESC throttle 范围未对齐 → 重做；完全无响应 → 焊接 / 信号线问题（§1.2）。

### 2.3 Bootloader 刷写

HKUST 用 BOOT 跳线 + DFU 刷 `NxtPX4v2_PX4_bootloader.elf`，再 QGC 通过 USB 刷 `NxtPX4v2_PX4_1.14.3.px4`。**踩坑**：bootloader 刷一半断电 → 砖 → 必须 ST-Link / J-Link 重刷。lab1 把这步标 "Provided by TAs" —— 学生不该单独刷。

---

## 3 · 第一次手飞 — 失败模式 (lab1 §"Calibrate Radio" → §"Before Flight")

lab1 PDF 推荐 **Position Mode** 起步（"It is much friendly to beginner"）。手飞炸机几种模式：

- **Toilet bowl 自旋** — (A) 磁罗盘没关 / 校错 → yaw 估计错 → controller 持续 yaw rate 修正；HKUST 直接 `SYS_HAS_MAG=0`。(B) motor 编号 / 旋向错配（见 §1.1）。
- **持续漂移** — (A) accelerometer 未校 / ROTATION 选错 → gravity 估计偏 → controller 把 gravity 一部分当水平加速度补偿。lab1 PDF: ROTATION 按飞控板实际安装方向选，TA 已校好但学生重做易错。(B) optical flow 旋转参数错（应 `SENS_FLOW_ROT: Yaw 270`）→ vx/vy 反 → 飞机往反方向加速。
- **Yaw drift** — 磁罗盘启用 + 室内电磁污染。HKUST 关磁罗盘后基本消失；自主时由 mocap (lab2) / VIO (lab3) 提供 yaw。
- **起飞瞬间 cutoff** — 电池电压不足。lab1 PDF: "!!! At least 23.0V before flight"；`ctrl_param_fpv.yaml` 给 `low_voltage: 13.2 # 4S battery`（FPV 默认；HKUST 实飞 6S 阈值应按 cell 数缩放）。BB Buzzer "b~b~b~b~" → 立即落地。

---

## 4 · OptiTrack motion capture 接 PX4 (lab2)

lab2 把 OptiTrack 当"外定位 ground truth"，通过 VRPN → `RI_Mocap` ROS 包 → MAVROS → PX4 EXTERNAL VISION estimator 喂位姿。看起来"装个包就跑"，实际三类坑：

### 4.1 Rigid body 配置（lab2 §2）

HKUST 强制规则：每架机至少 4 个**非对称** marker（symmetric → OptiTrack yaw 无唯一解）；每组 marker 摆位**不能与其他组相同**（同时上场会 swap 刚体身份 → lab2 原话: "**WRONG CONFIG WILL MAKE YOUR DRONE CRASH**"）；建刚体时机头朝 **North**（场地约定 +X），rigid body name `Gx`，user ID = 组号。

**失败信号**：mocap pose 突然跳到隔壁组位置 → swap → 立即 disarm；yaw 抖 ±180° → marker 对称歧义 → 重建。

### 4.2 坐标系三层转换

OptiTrack Motive (Y-up，lab2 PDF §3) → ROS REP-103 (FLU, forward-left-up) → PX4 EKF2 vision input (NED / FRD)，三层坐标约定不同。`RI_Mocap` 包从 VRPN PoseStamped 拿到 Motive 坐标 → 重排轴 + yaw offset → ROS FLU PoseStamped → MAVROS → PX4 NED。lab2 PDF §1.3 要求学生**只改 group ID 不要碰轴重排逻辑**——乱改 → 飞机往反方向冲。

**典型失败**：position 持续单向漂 → Y/Z swap 错；起飞后 yaw 跳 90° / 180° → 某一环 yaw offset 错；定点 hover 转圈 → mocap yaw 噪声大 / marker 对称性问题。

### 4.3 Odom timeout

`ctrl_param_fpv.yaml` 的 `msg_timeout` 给 5 路 (odom/rc/cmd/imu/bat) 各 0.5s 阈值——任一超时 → 状态机跳出 AUTO_HOVER 回 MANUAL → 飞行员接管。三路时钟对齐细节见 §7。

---

## 5 · OptiTrack → onboard 过渡 (lab3)

lab3 是 ELEC5660 闭环最关键一步：**关 OptiTrack，全靠 onboard RealSense + VO + EKF + planner 自主**。lab3: "**do not use OptiTrack data in your algorithm**. We will test your quadrotor without OptiTrack"。

### 5.1 不要直接切换 — hand-hold 渐进

lab3 §"Suggested Workflow" 五步（炸机概率从 ~80% 压到 ~5% `UNVERIFIED`）：(1) **手持 VO** 测 RealSense 驱动 / VO 初始化（USB 3.0 带宽不够 → frame drop → init 失败）；(2) **手持 EKF** 测协方差 / IMU bias / 时间同步收敛；(3) **手飞 + EKF 可视化**（不闭环），看 EKF vs OptiTrack 偏差（典型 <0.1 m `UNVERIFIED`）；(4) **EKF hover**；(5) **EKF + trajectory**。

### 5.2 切换瞬间的炸机模式

- **A. Position freeze 没做** — 切换 mocap → onboard EKF 瞬间，EKF 输出 pose 可能与 mocap 最后一帧偏 0.3-1.0 m `UNVERIFIED` → controller 把 "setpoint 与 state 突然偏 1 m" 当指令 → 输出最大加速度 → 翻。HKUST 缓解：px4ctrl AUTO_HOVER 子状态 hold 当前位置，切 odom 源时 setpoint 跟随 state。
- **B. VIO 初始化前 hover-in-place 没做** — VO 通常需要 1-3 秒激励运动初始化 metric scale。起飞瞬间 VO 未收敛 → 零位姿 / 漂移位姿 → 翻。lab3 "hand hold" 第一步就是地面让 VO 收敛后再装回飞机。
- **C. Sensor health / fallback** — RealSense USB 偶尔 reset（见 `deployment/calibration/sensor_calibration_drift_in_production.md` §7）→ EKF 断流。`msg_timeout` 500ms 是最基本 fallback。

---

## 6 · IMU 抗桨叶噪声

桨叶通过频率（Blade Passing Frequency, BPF）= 桨叶数 × RPM / 60。HKUST 5 寸级机 hover RPM `UNVERIFIED`，估算 5000-8000 RPM × 2 桨叶 ≈ **170-270 Hz**，加谐波 → 100-400 Hz 段 IMU 谱明显抬升。

**三层抗噪栈**：(1) 机械隔震 — lab1 Part 2 BOM 列 **8 颗 M2*6 Rubber Shock Absorber** 把 FC + ESC baseboard 浮接在 frame 上；(2) 1 kHz IMU 高速采样 Nyquist 覆盖 BPF（NxtPX4v2 内置 ICM-42688 / 类似 `UNVERIFIED`）；(3) PX4 `IMU_GYRO_NF*` notch + dynamic notch 数字滤波。

**失败信号**：hover 高频抖动（视觉可见）→ shock absorber 装反（lab1: "Be careful with the rubber direction"）；VIO 残差异常 + IMU bias 持续漂 → notch 没盯住 BPF（推力变化 BPF 也变，dynamic notch 必要）。详见 `embodiments/aerial/vio/README.md` §"四条非协商约束" 第 4 条。

---

## 7 · Time-sync 雷区

四个时间源同时跑：PX4 STM32 (usec counter，MAVLink TIMESYNC 对齐 Jetson)；Jetson ROS 主时钟；RealSense (hardware ISP timestamp，librealsense 重打 ROS time `UNVERIFIED`)；OptiTrack Motive (Windows wall clock，`RI_Mocap` 重打 ROS time)。每对 offset + jitter 直接进 EKF 残差。

**HKUST 折中**：全部用 ROS time 重打 + 5-20 ms jitter `UNVERIFIED`。生产必须走 PTP / gPTP 硬件同步、hardware trigger (FC GPIO 触发 camera shutter sub-ms)、或 VINS-Fusion 的 `td` 状态联合估计。详见 `deployment/calibration/sensor_calibration_drift_in_production.md` §6。

**失败信号**：VIO 残差长期 >2 px 中位数但 sensor 健康 → td 没补；IMU 预积分 chi-square 大 → td 未收敛；快速机动位置突然飘 → td 误差在角速度大时放大。

---

## 8 · 安全 / cutoff / failsafe

HKUST 三层 fail-safe（lab1 Safety Reminder + lab2 "If You Crash..." + `ctrl_param_fpv.yaml`）：

- **Battery 硬层** — BB Buzzer 单 cell 3.7V 报警 + PX4 `BAT_LOW_THR=0.15 / CRIT=0.07 / EMERGEN=0.05` + px4ctrl `low_voltage: 13.2`（HKUST 6S 按 cell 数缩放 `UNVERIFIED`）。
- **RC 中层** — Emergency Kill + Arm switch；emergency kill 直接停所有电机。RC signal lost：HKUST 室内应配 Land 而非默认 RTL。
- **Software 软层** — `msg_timeout` 5 路 0.5s 任一触发 → px4ctrl 回退 MANUAL。lab2: "**Anything abnormal during flight, switch back to manual control and land immediately**"。
- **GPS-denied** — HKUST 默认 GPS-denied（关磁罗盘 + 室内无 GNSS），lab2 mocap、lab3 onboard VIO 都不依赖 GPS。

---

## 9 · 真机 vs sim2real gap

Isaac Sim / Gazebo / Flightmare 学的 controller / planner 搬上 ELEC5660 真机的关键差异（出处 `ctrl_param_fpv.yaml`）：

| 维度 | Sim 默认 | ELEC5660 真机 |
|---|---|---|
| Thrust → force | 线性 `T = k·u` | `F = K1·V^K2·(K3·u² + (1-K3)·u)` — 低油门段非线性显著 |
| Battery sag | 忽略 | `K1` 是 voltage 函数，hover_percentage 任务后段抬升 5-10% `UNVERIFIED` |
| Air drag | 无 / 线性 | `rotor_drag` yaml 默认 0，高速停止过冲 |
| IMU noise | 白噪声 | 桨叶 BPF 主导（§6），sim EKF Q 矩阵真机偏低 |
| Latency | 0 | mocap 5-20 + ROS 1-5 + MAVLink 5-10 ms `UNVERIFIED`，总 ~30 ms 影响 phase margin |
| Hover throttle | 理论 50% | 1.2 kg 真机 `hover_percentage: 0.45` |

**核心**：sim 通常缺 *non-linear thrust + battery sag + BPF noise + latency*。HKUST `px4ctrl` 的 K1/K2/K3 三参 + low_voltage 阈值 + msg_timeout 就是把这四件事写进配置 schema。

---

## 10 · HKUST 做了大多数课程不做的事

| 课程 | 真机 | Onboard 自主 | 自写 VIO/EKF | 装配+焊 |
|---|---|---|---|---|
| Coursera Aerial Robotics (Penn) | sim | ❌ | sim EKF | ❌ |
| edX AMR (ETH) | partial | partial | ❌ | ❌ |
| **HKUST ELEC5660 (lab1+2+3)** | **真机** | **真机** | **lab3 学生自写 augmented EKF** | **lab1 焊+装** |

**ELEC5660 成功标准（lab3 原文）**：API 模式 position control 起飞；关 mocap 后还能飞；指定起点到终点；不撞已知障碍；demo + 视频 + 报告。这套 4 周"从焊接到 onboard 自主"的真机闭环是 ELEC5660 在公开教材中的稀缺价值。本仓 dynamics primer + min-snap + ekf-from-scratch 是"理论支柱"，**本文是"工程踩坑栈"**——两侧合起来才让读者真能从理论走到真机。

---

## 11 · Hidden Assumptions

- 本文数字大多 `UNVERIFIED` — RPM / BPF / latency / 坐标转换细节按 lab PDF 与 px4ctrl 源出处给量级；学生实测可能 ±50%。
- HKUST 关磁罗盘的前提是 mocap / VIO 提供 yaw；户外 GNSS 场景必须开磁罗盘并校准。
- `hover_percentage: 0.45` 与 `low_voltage: 13.2` 是 FPV yaml 4S 默认；HKUST 实飞 6S 需用 `px4ctrl/thrust_calibrate_scrips` 单独标定 + 按 cell 数缩放电压阈值。
- 本文不写 controller 调参（见 `dynamics_and_control_primer.md`）、VIO 算法本体（见 `vio/*_dissection.md`）。

---

## 12 · Cross-references

- `embodiments/aerial/dynamics_and_control_primer.md` — quadrotor EOM + cascade PID
- `embodiments/aerial/planning/min_snap_dissection.md` — lab3 trajectory generation 理论
- `embodiments/aerial/vio/ekf_from_scratch_dissection.md` — lab3 augmented EKF 自写理论
- `embodiments/aerial/vio/README.md` — 200 Hz / 10 ms / metric / IMU 抗桨噪四条约束
- `deployment/calibration/sensor_calibration_drift_in_production.md` — fleet 标定漂移（§4.3 §7 引用）
- `deployment/failure-modes/sensor_silent_failure_patterns.md` — sensor 静默失效（§5.2 fallback 衔接）
- `crossing/slam-vio-migration/vggt_vs_drone_vio.md` — sim2real gap 跨实体视角

---

## Boundary

本文写**五道炸机门的工程坑**，每条都有 lab PDF / px4ctrl 一手出处。**不写**：四旋翼动力学（→ `dynamics_and_control_primer.md`）、min-snap / 路径规划（→ `planning/`）、VIO / EKF 推导（→ `vio/*_dissection.md`）、fleet 标定漂移（→ `deployment/calibration/`）、跨实体对比（→ `crossing/`）、sensor 物理与厂商参数（→ `foundations/sensor-physics/`）。本文是 runbook，不走 dissection 14 项门槛——按 AGENTS.md §文档类型分层属于 deployment-style 工程文档。

---

[← Back to Aerial README](./README.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-22 | 取材 HKUST ELEC5660 lab1/lab2/lab3 (BSD 3-Clause)
