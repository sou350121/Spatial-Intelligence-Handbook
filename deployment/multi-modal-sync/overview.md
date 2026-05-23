# 多模态同步 — 时间戳与触发 / Multi-Modal Sync

**Status:** v1 — opinionated landing。具体抖动 / 漂移 / 延迟数字标 `UNVERIFIED`，需以平台实测为准。
**TL;DR:** RGB + Depth + IMU + IR 必须在同一时间轴上才有意义——「论文跑得通、整机跑不动」常常是同步没做对。同步是看不见的 SWaP-C 杀手：算法不动、sensor 不动、BoM 不变，光是把时间戳拉对，VIO 性能差一档。本目录把硬件触发 / PTP / 软件时间戳三档同步方案与它们的「什么时候够用」写成 ops 级文档。

---

## 1 · 为什么同步要单独写

学界论文报告的 VIO / SLAM 性能数字几乎都假设了**严格时间同步**。真实部署里，时间戳错位 1 ms 在 100 Hz 控制回路就是 10% 的相位误差；错位 10 ms 在 drone 250°/s 角速度下就是 2.5° 旋转——已经够把 VIO 推到发散。

同步出错的症状常常被误诊为别的：

- 「VIO 漂得快」 → 实际是 IMU-相机时间偏置在温度漂移下变化，被当成算法问题。
- 「BEV occupancy 边缘模糊」 → 实际是 6 颗相机不是同一瞬间曝光的，被当成模型问题。
- 「LiDAR 点云有运动鬼影」 → 实际是 LiDAR scan 时间与车辆位姿不同步，被当成标定问题。

工程上修一次同步比加一颗 sensor 便宜得多，但写在 README 里的几乎没有。这是手册非要写的工程账。

---

## 2 · 三档同步方案速览

| 等级 | 实现 | 时钟偏置（`UNVERIFIED`） | 抖动 | 部署难度 | 适用 |
|---|---|---|---|---|---|
| **A. 硬件触发同步** | 一颗 MCU / FPGA 同时触发相机曝光与 IMU 采样 | &lt;0.1 ms | μs 级 | 中—需自制板或选支持外触发的相机 | 高动态平台（drone / 人形 / AD） |
| **B. PTP / gPTP（IEEE 1588）** | 网络时间协议 + 硬件辅助 NIC | 1–10 µs | µs–ms 级（取决于网络抖动） | 高—需 PTP grandmaster 与硬件 PHY 支持 | 多节点 AD 栈、机器人 fleet |
| **C. 软件时间戳 + 在线估计** | 各设备本地时钟，由 VIO / fusion 算法估计偏置 | 1–10 ms 初始，温度后漂 | 10–100 ms | 低—USB / 串口即可 | 慢速 AGV、室内 demo、研究 |

详细对比与 worked example：`hardware_trigger_vs_ptp_vs_software.md`。

---

## 3 · 同步与 embodiment 的匹配

| Embodiment | 推荐档位 | 原因 |
|---|---|---|
| Manipulation（桌面） | C 常常够 | 速度低；外参短；IMU 不是 critical |
| Humanoid | B 或 A | 多 IMU + 多相机；关节链路 + 头部 stereo |
| Ground AGV | C 或 B | 中等速度；室内地图 prior 兜底 |
| Driving (AD) | **B 强制** | 6+ 相机 + LiDAR + radar 全部 PTP；软件时间戳直接报废 |
| Aerial（高动态） | **A 强制** | 250°/s + 高加速；几毫秒偏置毁 VIO |
| Marine | A 或 B | sonar ping 同步 + INS 严格对齐 |

Skydio / DJI / 主流 AD 量产栈：A 或 B。研究 demo / 消费 ROV：C 常常凑合。

---

## 4 · 同步崩了会怎样（三个典型症状）

```
症状 1：VIO 残差有周期性偏置（与角速度相位锁定）
  ├─ 病灶：相机-IMU 时间偏置 td 没估对
  └─ 修：在因子图把 td 作为待估状态；或上硬件触发

症状 2：BEV 在快速转弯时边缘 ghosting
  ├─ 病灶：6 颗相机不是同帧曝光，车体已转 几度
  └─ 修：PTP + global shutter + 触发到 ±1 ms 内

症状 3：LiDAR 点云沿车头方向"拖尾"
  ├─ 病灶：LiDAR scan 期间车辆已移动几米，但 ego-motion 没补偿
  └─ 修：scan 时间戳与 IMU/odom 对齐，做 motion compensation
```

详见 `hardware_trigger_vs_ptp_vs_software.md` §4 worked example。

---

## 5 · 本目录内容

| 文档 | 内容 |
|---|---|
| `hardware_trigger_vs_ptp_vs_software.md` | 三档方案完整对比 + drone 200Hz 控制下的 worked example |
| `(待补) ros2_sync_pitfalls.md` | ROS 2 / DDS 时间戳常见坑（`use_sim_time`、QoS、message_filters）；TODO |
| `(待补) lidar_motion_compensation.md` | 旋转 LiDAR 与车体位姿的去畸变流程；TODO |

---

## 6 · Cross-references

- 标定（同步与标定共轭）：`deployment/calibration/README.md` §4「IMU-相机时间同步」
- 失败模式（同步崩了的下游症状）：`deployment/failure-modes/README.md`
- 单 sensor 物理（rolling vs global shutter）：`foundations/sensor-physics/`
- IMU 噪声与时间偏置：`foundations/sensor-physics/imu_physics_and_noise_model.md`

## Boundary

本目录写多 sensor **时间轴对齐**的工程账。**不写**单 sensor 内参（去 `foundations/sensor-physics/`）、空间外参标定（去 `deployment/calibration/`，但 §4「IMU-相机时间同步」与本目录交叠——time = 4th dim of calibration）、算力 / 模型（去 `deployment/compute-budget/`）。本目录 starter 配置不替代 production 同步验证——production 必须以示波器实测触发延迟 + 长时间漂移测试为准。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
