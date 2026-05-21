# SLAM 工具链生态 (SLAM Toolchain Ecosystem)

> **类型:** Deployment-side toolchain notes（非 paper dissection）
> **范围:** Kalibr · maplab · ROS / ROS 2 · rosbag2 · RPG datasets workflow
> **核心定位:** 没人写论文但每个 SLAM deployment 都得过的工具链账本 —— 哪些已经是事实标准，哪些只是 academic prototype，PoC 阶段该选哪个、量产前该躲哪个。

**Status:** v1 — 部署调性 (deployment register)。版本号、可用性、复现成本基于公开 repo 与社区报告，部分数字 `UNVERIFIED`。

**TL;DR:** 你跑 ORB-SLAM3 / VINS / DSO 的成败 70% 不在算法本身，而在**外参标定准不准、时间戳对不对、数据集回放是不是按真实顺序**。这一区不重写算法，重写**生态**：Kalibr 是 camera-IMU 标定的事实标准；maplab 在工业界用得不多但是 ETHZ-ASL 多机器人 mapping 的研究底座；ROS 2 集成现实远没有 ROS 1 时代那么平稳；rosbag2 + RPG datasets 是任何 PoC 必须建立的回放工作流。

## 1 · Kalibr — camera + IMU + multi-cam 外参标定

**Repo:** https://github.com/ethz-asl/kalibr · **团队:** Furgale et al., ETH Zürich (Autonomous Systems Lab)

### 它解决什么

任何 visual / visual-inertial SLAM 跑起来之前，都需要：

| 参数 | 含义 | 不准的后果 |
|---|---|---|
| Camera intrinsics (K, distortion) | 投影模型 | 重建尺度 + 位姿系统性偏差 |
| Camera-IMU extrinsics (T_cam_imu) | 相机 → IMU 6-DoF 外参 | VIO 在加速 / 转弯时位姿抖动 |
| Time offset (t_cam vs t_imu) | 时间戳偏移 | 高速运动下 VIO 发散 |
| Multi-camera extrinsics (T_cam0_cam1) | 立体 / 多目相机间外参 | 立体三角化错 / 多目融合错 |
| IMU noise model (σ_g, σ_a, σ_bg, σ_ba) | gyro / accel 噪声 + bias walk | 滤波器权重错 → 估计不一致 |

Kalibr 把这五项**同时**估出来。它是事实标准的原因：**没有第二个开源工具同时支持 cam-IMU 外参 + 时间偏移 + 多目几何 + IMU 噪声标定**。VINS、OpenVINS、ORB-SLAM3 的官方文档都建议先跑 Kalibr。

### 实战 caveat

- **AprilTag 标定板**是默认 — 自己打印 PDF 大概率精度不够，应订商业铝板（成本 ~$200–500 `UNVERIFIED`）
- **录数据要慢动作充分激发 6 DoF**（roll / pitch / yaw 各方向都要绕到位）— 这一步偷工，外参标了等于没标
- **IMU noise 标定（allan variance）需要 IMU 静置数小时录数据** — 工业部署经常跳过这一步直接用 datasheet 数字，效果差几十倍
- **温度漂移不在 Kalibr 模型里** — 户外 / 大温差场景需要额外 warm-up procedure

### 适用 / 不适用

✅ Robotics PoC 必备、SLAM 学术论文必报、aerial / ground / arm 都通用
⚠️ 量产线 calibration（每台都要跑、还要自动化）建议二次封装 Kalibr 而不是 GUI 操作
❌ 全局 / 仓库尺度的 multi-camera + LiDAR + GNSS 联合外参 — Kalibr 单机视角，跨车队 / 多机协同标定要另外架构

---

## 2 · maplab — 多机器人 visual-inertial mapping 框架

**Repo:** https://github.com/ethz-asl/maplab · **团队:** ETHZ-ASL (Schneider, Burri et al.) · **发表:** *IEEE RAL 2018*

### 它解决什么

maplab 是**多 session、多机器人**的 visual-inertial map merging 框架。单次 SLAM 出来的轨迹是孤立的；maplab 提供：

- 多 session 地图合并 (anchor + place recognition)
- 大规模 map 优化 (sliding-window + global BA)
- Loop closure detection 跨 session
- Map summarization (减少 keyframe / landmark 冗余)
- 与 ROVIO / OKVIS 等 VIO 后端配套使用（不是 SLAM 本体）

### 现实评估

- **研究界引用很多**（ETHZ-ASL 是 Skydio 主要源流之一，圈内权威）
- **工业用得不多**（部署门槛高、文档零碎、ROS 2 迁移滞后）
- **2021 后维护频率降低** —— 学术项目的常态：博士毕业，repo 进入低维护模式
- **替代方案** — 工业界倾向自研 mapping backend（如 Skydio、Autel 内部 stack）

### 何时该用 / 不该用

✅ 学术 PoC（多机器人 / 多 session VIO 实验）、研究跨 embodiment map sharing
⚠️ 商用部署前要评估二次开发负担
❌ 单机器人单 session SLAM — 用 ORB-SLAM3 或 VINS 就够，maplab 的复杂度成本不值

---

## 3 · ROS / ROS 2 集成现实

### ROS 1 时代 (2014–2020)

ORB-SLAM / VINS-Fusion / OpenVINS / Kalibr **全都有官方或社区维护的 ROS 1 wrapper**。`roslaunch` + `rosbag` + `rviz` 是不假思索的标配。

### ROS 2 现实 (2022–2026)

迁移到 ROS 2 后，事情没那么平稳：

| 框架 | ROS 2 状态 (2026) | 注 |
|---|---|---|
| ORB-SLAM3 | **社区 wrapper 多个，官方未发布** | 主流 fork: `zang09/ORB_SLAM3_ROS2`、`linzs-online/ros2-orbslam3` `UNVERIFIED` |
| VINS-Fusion | 社区 ROS 2 port 存在，未官方化 | HKUST 团队官方仍 ROS 1 |
| OpenVINS | **官方支持 ROS 2** | UDel 团队主动维护 |
| Kalibr | **仍 ROS 1 only**（截至 2026）`UNVERIFIED` | 大量 deployment 把 Kalibr 隔离在 ROS 1 容器跑 |
| maplab | ROS 1 only `UNVERIFIED` | 维护节奏与 ROS 2 迁移不同步 |

### 实战建议

- **新项目起跑用 ROS 2 + OpenVINS 是最少坑路径**（官方支持齐全）
- **必须用 ORB-SLAM3 时，选社区 fork + 把 wrapper 当依赖锁版本** — 不要追最新 main
- **Kalibr 跑在 ROS 1 容器**（docker / apt 隔离），标定结果以 YAML 输出后给 ROS 2 stack 消费 — 不要强行 port
- **rosbag2 与 rosbag1 不兼容** — 历史数据集要么 conversion 工具回放、要么用 `rosbag2 play_ros1_bag` 桥

### ROS 2 wrapper 选型 checklist

- [ ] 最近一次 commit 在 6 个月内
- [ ] 至少有 1 个真实 issue 被回复（不是 ghost repo）
- [ ] CMakeLists 锁定 ROS distribution（Humble / Iron / Jazzy）
- [ ] 附 docker 镜像或明确 dependency 列表
- [ ] 验证过的 launch file（不只 README 抄一行 launch 命令）

---

## 4 · rosbag2 + RPG datasets 回放工作流

### 为什么这一步是 PoC 必备

任何 SLAM 算法的**复现都依赖确定性回放**：同一段数据、同样的时间戳、同样的传感器顺序，跑出同样的轨迹。Live 跑机器人不可重复；rosbag 回放才可重复。

### 推荐数据集 + 回放流程

| 数据集 | 用途 | 链接 |
|---|---|---|
| **EuRoC MAV** | VIO 学界标尺；MAV 室内 | https://projects.asl.ethz.ch/datasets/doku.php?id=kmavvisualinertialdatasets |
| **TUM-VI** | 长 trajectory + 室内外混合 | https://vision.in.tum.de/data/datasets/visual-inertial-dataset |
| **TUM-RGBD** | RGB-D SLAM 学界标尺 | https://vision.in.tum.de/data/datasets/rgbd-dataset |
| **UZH-FPV Drone Racing** | aerial 高速；ORB-SLAM3 / VINS 在这上面会输 | https://fpv.ifi.uzh.ch/ |
| **KITTI / KITTI-360** | 自动驾驶（不在本区核心范围，但很多 SLAM 论文报） | https://www.cvlibs.net/datasets/kitti/ |

### 回放工作流模板

```
1. 下载 rosbag (ROS 1 .bag) 或 rosbag2 (.db3)
2. 用对应版本的 ros bag info 确认 topic 列表 + 时间戳范围
3. roslaunch / ros2 launch 起 SLAM stack（参数文件指向数据集对应的标定）
4. rosbag play --clock --rate 1.0  ←必须用 --clock，否则系统时间错乱
5. record 一份 trajectory.txt → 用 EVO / rpg_trajectory_evaluation 跑指标
6. 多次重复 (≥3 次)，因为 ORB-SLAM 系列有随机性 —— 单次结果不算
```

### 容易踩的坑

- **不加 `--clock` → wall clock 与 bag 时间错位** → IMU pre-integration 直接乱套
- **`--rate` 不是 1.0 时算法行为变了** → 0.5 倍速复现的指标不能拿去报论文
- **bag 录的时候 frame_id 不规范** → 回放时 TF 解不出来，sensor 配准失败
- **录 bag 时 USB 带宽溢出** → 帧丢失但 bag 本身正常 → 静默偏差

---

## 5 · 整体生态地图 (Where things actually live in 2026)

```
                  ┌─────────────────────────────┐
                  │  SLAM 算法本体               │
                  │  ORB-SLAM3 / VINS / DSO / ...│
                  └────────────┬────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌───────────┐   ┌──────────────┐  ┌──────────────┐
       │ 标定/输入  │   │  运行环境     │  │  数据/评测   │
       │ Kalibr ★  │   │ ROS 1 / 2 ⚠️ │  │ rosbag2 / EVO │
       │ + photo cal│  │ Docker 隔离  │  │ RPG datasets │
       └───────────┘   └──────────────┘  └──────────────┘
              │                ▲                ▲
              ▼                │                │
        ┌──────────┐           │           ┌──────────┐
        │ multi-   │           │           │ maplab    │
        │ session  │───────────┴───────────│ (research │
        │ mapping  │                       │  only)    │
        └──────────┘                       └──────────┘

★ = 事实标准  ⚠️ = ROS 2 迁移仍有坑
```

部署优先级建议：**先把 Kalibr + rosbag 回放工作流建好，再讨论选 ORB-SLAM3 还是 VINS**。算法选型是次要的，标定 + 回放是地基。

---

## Boundary

- **ORB-SLAM3 / DSO / 算法本体机制** → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md) · [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md)
- **aerial 严格 latency / IMU 工程实战** → [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/README.md) — Kalibr / 时间同步实战在 aerial 那边有更深的栈
- **传感器 / IMU noise 物理底层** → [`foundations/sensor-physics/`](../sensor-physics/)
- **跨 embodiment 时间同步 / 硬件 trigger** → [`deployment/`](../../deployment/)（如已存在对应文档）
- **VGGT / feed-forward 不依赖 Kalibr** → [`foundations/feed-forward-3d/`](../feed-forward-3d/) — 但 hybrid stack 仍要

---

## References

- Kalibr — Furgale et al. · *IROS 2013* · https://github.com/ethz-asl/kalibr
- maplab — Schneider et al. · *IEEE RAL 2018* · https://github.com/ethz-asl/maplab
- EuRoC MAV dataset — Burri et al. · *IJRR 2016*
- TUM-VI dataset — Schubert et al. · *IROS 2018*
- TUM-RGBD dataset — Sturm et al. · *IROS 2012*
- UZH-FPV Drone Racing — Delmerico et al. · *ICRA 2019*
- rpg_trajectory_evaluation — https://github.com/uzh-rpg/rpg_trajectory_evaluation
- EVO trajectory evaluation — https://github.com/MichaelGrupp/evo

---

[← Back to Classical SLAM](./README.md)
