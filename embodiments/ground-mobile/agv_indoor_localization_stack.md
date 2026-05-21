# 室内 AGV 全 Stack：2D LiDAR + 轮式里程 + IMU + 视觉辅助 (Indoor AGV Localization Stack)

> **发布时间**：2026-05-21
> **核心定位**：仓储 / 工厂 AGV 是 mobile robotics 最早大规模落地的形态——但其 spatial stack **几乎完全反学界趋势**：用 2D LiDAR + EKF，不上 3D，不上深度学习。本文回答：为什么 mass-market 解锁定在 2D LiDAR，而 Skydio-class 高端在做什么。
> **TL;DR**：消费 / 仓储 AGV (Hokuyo 2D LiDAR + AMCL) 的"够用"档把 95% 室内导航需求 cover 了，price point ~$2k；高端 (Skydio / Cobalt 安保 / 自主 forklift) 才上 3D LiDAR + 视觉 + 深度学习。**反直觉的事实是：mass-market 不需要 3D，因为地面是平的 + 高度信息不参与决策。**

**状态：** v1 —— 有立场的草稿。商用 AGV / sensor 规格 `UNVERIFIED`。

---

**X-Ray 开场：** 走进任何亚马逊 / 京东仓库，看到的 AGV / AMR 不是装 RGB-D + 神经网络 SLAM 的高端机器人，而是 **2D LiDAR + 轮式里程 + 简单 IMU + AMCL（自适应蒙特卡洛定位）** 的老派组合。这套 stack 自 2005 年 ROS Navigation Stack 起几乎没变过，但**它够用**——仓储地面平整、动态障碍稀疏、Wi-Fi 不可靠时退回轮式里程也能撑。spatial researcher 容易认为"过时"，但 mass-market AGV 的 unit economics 决定了**这套老 stack 才是赢家**。本文拆解：什么时候 2D LiDAR 够用、什么时候必须升 3D、Skydio-class 高端在做什么。

---

## 📍 研究全景时间线

```
1990s ─ AGV 用磁条 / 反射板导航（无 SLAM）
        │
2005 ─ ROS 立项 + 2D LiDAR SLAM (GMapping)
        │ ⚡ Hokuyo URG-04LX 把 LiDAR 价格打到 <$2k
2010 ─ AMCL（自适应蒙特卡洛定位）成为 ROS 默认
        │
2012 ─ Amazon 收购 Kiva → 仓储 AGV 商业化起飞
        │
2015 ─ Hokuyo / SICK / RPLIDAR 主导 2D LiDAR 市场
        │
2018 ─ Velodyne VLP-16 价格下降 → 高端 AGV 开始 3D LiDAR
        │
2020 ─ Skydio 2 (drone) 推广 vision-based avoidance → 移植到 AGV
        │ ⚡ 视觉避障从 drone 渗透到 AGV
2022 ─ 自主 forklift（Outrider / Phantom Auto）— 户外 + 3D LiDAR
        │
2024 ─ Cobalt 安保机器人 — 多 sensor 融合 + 神经语义
        │
2026 ─ 本文位置：mass-market 仍 2D LiDAR，高端开始 3D + 视觉
        └─ 局限：户外 AMR / 多楼层（电梯）仍未稳定解
```

---

## 1 · 核心架构 / 方法总览

### 1.1 Mass-market vs 高端 stack 对比

| 维度 | Mass-market AGV (仓储) | 高端 AMR (Skydio-class) |
|---|---|---|
| 主 LiDAR | 2D（Hokuyo / SICK / RPLIDAR） | 3D（Velodyne / Livox） |
| RGB / RGB-D | 可选辅助 | 多 cam + 占用网络 |
| IMU | 消费 MEMS | 工业级（多 IMU） |
| 轮式里程 | 标配（核心信号） | 仍标配 |
| 定位算法 | AMCL（粒子滤波） | Fast-LIO / LIO-SAM / 神经 SLAM |
| 地图 | 预扫 2D occupancy grid | 3D 点云 + 语义 |
| 动态障碍 | costmap inflation | 占用 + 预测 |
| 单车 BOM | $2-10k | $20-100k |
| 案例 | Amazon Robotics / Geek+ / Quicktron | Skydio drone / Cobalt 安保 / Locus 仓储 |

### 1.2 关键机制：为什么 2D LiDAR 够用

⚡ **Eureka Moment**：仓储地面**平整 + 高度信息不参与决策**，2D 切片足够描述 navigable space——3D 是过度工程。这是 spatial researcher 最容易忽略的工程现实：**够用即停**。

具体逻辑链：
1. 仓储地面公差 <5 cm，AGV 底盘可吸收
2. 障碍物（货架 / 人 / 叉车）在 0-2 m 高度有截面 → 2D 切片必检出
3. 货架顶部 / 天花板 → 与导航无关
4. 因此 2D 切片完全捕获 "navigable space" 的信息
5. **3D 加进来纯成本，无 ROI**

例外（必须 3D）：
- 户外 AMR（草地 / 阶梯 / 倾斜面）
- 多楼层 + 电梯 + 不同地面材质
- 与人协作 + 需要预测人的 3D 姿态

### 1.3 Mass-market AGV 数据流

```
                    ┌──────────────────────┐
   2D LiDAR ──────► │                      │
   (10-40 Hz)      │   AMCL                │ ──► 位姿 (5-20 Hz)
   ──► 2D scan    │   (粒子滤波)          │
                    │                      │     ▲
   轮式里程 ──────► │   EKF / dead-reck    │     │
   (50-200 Hz)     │                      │     │
                    │                      │     │ 预扫 2D map
   IMU (MEMS) ────► │                      │     │ (OG, occupancy grid)
   (100-500 Hz)    └──────────────────────┘     │
                            │                    │
                            ▼                    │
                    ┌──────────────────────┐     │
                    │  Costmap + Planner   │ ◄───┘
                    │  (A* / TEB / DWA)    │
                    └──────────────────────┘
                            ▼
                       motor cmd
```

---

## 2 · 数学核心：AMCL 粒子滤波

📌 **Napkin Formula**：`belief(x_t) = η · P(z_t | x_t, map) · Σ P(x_t | x_{t-1}, u_t) · belief(x_{t-1})`——粒子近似的递归贝叶斯，每步用 LiDAR scan 与预扫地图的匹配概率重加权。

要点：
- 粒子数：500-5000 典型，部署时 adaptive 调
- 似然函数 `P(z_t | x_t, map)`：每个 beam endpoint 落在 occupied / free 的概率累乘（log-likelihood 加）
- Resampling：粒子有效数 N_eff 低于阈值时触发
- 关键限制：**需要初始位姿** 或 全局重定位（kidnapped robot 问题）

数值直觉：1000 粒子 + 50 ms scan-match → 20 Hz 输出。仓储平面 10000 m² 全局重定位 < 5 s `UNVERIFIED`。

---

## 3 · 带数字走一遍：仓储 AGV 玩具例子

设 Hokuyo UST-10LX (10 m, 270°, 40 Hz)，AGV 速度 1 m/s，地图 100 m × 100 m。

- 每 25 ms 一帧 scan，AMCL 处理 ~20 Hz
- 轮式里程漂移：直线 ~1%（无 IMU 帮忙），10 m 行程 → 10 cm
- IMU 加进来后：方向角漂移降到 ~0.1°/min
- 全局重定位（粒子分散到全图）：~2-5 s 收敛 `UNVERIFIED`
- 货架移动后地图失效 → AMCL 性能急降，需要触发重扫地图

工程现实：**地图维护成本是 AGV 部署的隐性大头**——仓库布局每变动一次，要全场重扫。Amazon Robotics 通过**固定货架位 + 移动整个货架**（不是 AGV 在静态环境穿梭）绕开这个问题。

---

## 4 · 工程视角：成本拆解与失效模式

| 失效 | 原因 | 缓解 |
|---|---|---|
| 玻璃门 / 镜面 | LiDAR 透射 / 反射，看不到障碍 | 加超声 / 加贴纸标记 |
| 同质走廊（白墙） | scan match 退化（aperture 问题） | 加视觉 / 反射板 |
| 货架移动 → 地图过期 | AMCL 匹配失败 | 触发动态重扫 / 短期记忆 |
| 拥挤动态环境 | costmap 抖动 | TEB / DWA local planner |
| 人 / 叉车遮挡 | 单 2D 切片信息丢失 | 多 LiDAR 高度 / 加 cam |
| 电梯换层 | 高程变化 + 信号短暂丢失 | 多层地图 + RFID / Wi-Fi 提示 |

成本结构（mass-market AGV ~$5k BOM `UNVERIFIED`）：
- 底盘 / 电机：~30%
- 电池：~15%
- 2D LiDAR：~15-25%（最大单 sensor 项）
- IMU + 控制板：~10%
- 软件（开源 ROS） / 集成：剩余

3D LiDAR 加进来 → BOM 升 ~$3-15k → 部署 ROI 立刻不成立——这就是 mass-market 不上 3D 的真正原因。

---

## 5 · 数据与评测

- **公开数据**：TUM / KITTI（户外 AD 用，不太适合 AGV）；MIT Multi-Floor 数据集
- **工业评测**：MTBF（平均故障间隔）、定位精度 (cm)、动态环境通过率
- **仿真**：Gazebo + ROS 是 mass-market 标准；高端用 Isaac Sim

仿真饱和警告：Gazebo AMCL 100% 成功率不可外推到真实仓库——玻璃门 / 同质走廊 / 货架移动是 sim 没建模的。

---

## 6 · 能力与失败模式

**能做**：仓储 / 工厂室内导航、固定路径运输、有限动态环境。
**做不了**：户外、多楼层、与人深度协作（不止避障）、未扫描的临时区。

### Hidden Assumptions

1. **地面平整**——倾斜 / 阶梯 / 软地毯 → 轮式里程 + 2D LiDAR 全失效。
2. **预扫地图新鲜**——货架移动一次，AMCL 立即失能；地图维护成本被低估。
3. **障碍在 LiDAR 高度有截面**——超低（地毯卷起边）/ 超高（悬挂物）→ 2D 切片漏检。
4. **环境非镜面**——玻璃 / 镜子 / 抛光金属 → LiDAR 误读。
5. **GNSS-denied 但 Wi-Fi/UWB 可用作辅助**——纯 GNSS-denied + 同质走廊 → 全局重定位失败。

---

## 7 · 与相关工作 / 跨 embodiment 对比

| Embodiment | 主 LiDAR | 预扫地图 | 主要漂移源 |
|---|---|---|---|
| 仓储 AGV (Mass-market) | 2D（10 m） | 是 | 轮式里程 + 货架移动 |
| 户外 AMR | 3D | 是 / GNSS RTK | GNSS 多径 + 树荫 |
| 自动驾驶 (Waymo) | 多 3D LiDAR | 是（HD map） | 地图过期 + 城市新建 |
| Aerial drone | （多无 LiDAR） | 否（在线 SLAM） | VIO 漂移 |
| AUV | 无 LiDAR（替代 = DVL） | 是（bathymetry） | 声速变化 + 磁罗盘 |
| Humanoid | 头装 LiDAR (Unitree) | 否 | 头部姿态稳定 |

**面试 Tip**：被问"AGV 为什么不上 3D LiDAR + 神经 SLAM"——答"仓储地面平整 + 障碍在 2D 切片有截面，3D 加进来纯成本无 ROI；mass-market 解锁定在 $5k BOM 量级，3D LiDAR 把 BOM 翻倍而精度提升不到 deployment ROI 临界"。

---

## Boundary

- **VLN / Object Navigation（HM3D / ObjectNav benchmarks）** → [`embodiments/ground-mobile/vln_and_object_nav.md`](./vln_and_object_nav.md)
- **2D / 3D LiDAR 物理对比** → `foundations/sensor-physics/`（待补）
- **粒子滤波 / 因子图 SLAM 算法细节** → `foundations/slam-classical/`（待补）
- **跨 embodiment sensor stack** → `crossing/sensor-stack-matrix/`

## For the reader

- **AGV / 仓储 engineer**：2D LiDAR + AMCL 仍是 BOM 最优解；上 3D 之前先问"是否户外 / 多楼层 / 与人协作"，三个都否就别上。
- **Aerial engineer**：AGV 路线提醒你"够用即停"——drone 不能用预扫地图（变化太快），但 AGV 可以，这是 sensor stack 差异的根源。
- **Humanoid engineer**：人形不能用 2D LiDAR（地面不平 / 楼梯），但**预扫地图 + 局部感知**这个范式可借鉴。
- **AD engineer**：AGV 的"预扫地图 + AMCL"是 Waymo HD map 路线的低端版本，量子区别在更新频率（AGV 月级 vs Waymo 周级）。

## References

- AMCL — Fox 等 1999；ROS 集成 Pratkanis 等
- ROS Navigation Stack — [wiki.ros.org/navigation](http://wiki.ros.org/navigation)
- Hokuyo URG / UST-10LX 数据手册 `UNVERIFIED, no DOI`
- Kiva Systems — Amazon Robotics 早期论文
- Skydio autonomy — Skydio whitepapers `UNVERIFIED`

---
[← Back to Ground-Mobile README](./README.md)
