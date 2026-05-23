# Humanoid + Legged · 全身空间推理

**范围：** 双足人形（Unitree H1/G1、Figure 02、1X NEO、Tesla Optimus、Boston Dynamics Atlas）+ 四足（Spot、Unitree Go2、ANYmal）——严格从**空间感知**侧来看。身体在场景里移动，而不是螺丝固定在桌上。

**状态：** v1 入口页。所有商用机器人规格标 `UNVERIFIED`，除非来自厂商数据手册。

---

## 为什么 "humanoid + legged" 是一个子树

人形和四足共享一个把它们和本手册所有其他 embodiment 分开的定义性属性：**感知传感器装在一个既平移*又*非平凡旋转的躯体上**。轮式机器人平移但相机几乎不转；aerial 转得很多但传感器相对机身姿态固定；manipulation 移臂但头是静止的。人形和腿足机器人让相机沿着一个复杂的 6-DOF 轨迹运动，其中包括**1–3 Hz 的脚部冲击**和与步态绑定的俯仰振荡。

这强加了两个 manipulation 和 ground-mobile 都不必处理的空间感知问题：

1. **远眺视距。** 人正常走路自然看前方 ~3 m，因为身体需要 ~1 秒的预览来规划落脚点和避障。装在人形头上的相机必须同时服务*远感知*（凝视）和*近感知*（落脚）。两者在分辨率、延迟、更新率上的需求都不一样。
2. **体相对空间帧。** World frame 对导航有用但对落脚没用。Body frame 对落脚有用但对导航没用。一个人形空间栈*同时*在两个 frame 里跑，由 IMU + 腿运动学维护显式变换——某处算错是最常见的失效模式。

这两个问题就是这个子树和 `ground-mobile/` 分开的原因。一台 Unitree H1 做运动控制，和 Spot 四足共享的感知架构，远多于和 iRobot Roomba 共享的，尽管 Roomba 和 H1 都是 "室内移动机器人"。

---

## 与桌面 manipulation 的空间差异

| 维度 | 桌面 manipulation | Humanoid / legged |
|---|---|---|
| 场景相对传感器 | 静态；传感器轻微移动 | 传感器不断穿过场景 |
| 工作体积 | <1 m³ 工作区 | 整个房间 → 室外 |
| 参考帧 | 物体或底座 | World + body +（每只脚） |
| 关键特征更新率 | 10–30 Hz（臂动） | 30–100 Hz 落脚；5–10 Hz 导航 |
| 失效模式 | 掉物 / 抓偏 | **摔倒**——灾难性，可能无法恢复 |
| 常用传感器 | 腕部 + 工作区 RGB-D | 头立体 + 体 IMU +（Spot：体 LiDAR）+ 足触发 |

一个有用的框架：桌面 manipulation 是**静态场景的 3D 感知**（手在里面动）。Humanoid 是**4D 感知**——身体加了一根时间轴，相机外参变化和场景本身一样快。这就是为什么 humanoid SLAM 离 drone SLAM 更近，而不是离 manipulation 更近，尽管工作速度和 ground mobile 更接近。

IMU 耦合的平行关系见 `crossing/sensor-physics/`。

---

## 厂商图景（传感器栈快照，全部 `UNVERIFIED`）

| 机器人 | 类型 | 头/眼传感器 | 体传感器 | 算力 | 来源 |
|---|---|---|---|---|---|
| **Unitree H1** | 人形 | RGB-D 头（Intel RealSense 一类） | IMU、关节编码器 | Jetson Orin 一类 | 厂商产品页 |
| **Unitree G1** | 小型人形 | 同 H1 家族 | IMU + 足力 | Jetson 一类 | 厂商产品页 |
| **Figure 02** | 人形 | 多相机头，深度未披露 | IMU + 力 | 自研 + 云 | 公关材料 |
| **1X NEO** | 人形 | 多相机头，深度未披露 | IMU + 力 | 板载 + 云辅助 | 公关材料 |
| **Tesla Optimus** | 人形 | 纯相机（无 LiDAR，依 Tesla 路线） | IMU + 力 | FSD 衍生 | 公关演示 |
| **Boston Dynamics Atlas（新）** | 人形 | 多相机头、ToF | IMU + 力 | 自研 | 公关材料 |
| **Boston Dynamics Spot** | 四足 | 体装立体相机阵列 + ToF | IMU + 腿运动学 | BD 板载 | 公开规格表 |
| **Unitree Go2** | 四足 | 头装深度，可选 LiDAR | IMU | Jetson | 厂商产品页 |
| **ANYmal** | 四足 | 体 LiDAR + 相机 | IMU + 力 | 自研 | 公开论文 |

**两个值得标记的架构分叉：**

1. **纯相机（Tesla）vs 富深度（Unitree、Figure、Atlas）vs 富 LiDAR（Spot、ANYmal）。** Tesla 押注 monocular + 从自运动估尺度够用；其他所有人靠主动深度对冲。盯这个分叉——它几乎和 AD 路线分叉（Tesla 纯视觉 vs Waymo 富 LiDAR）一一对应，这个比较是个候选的 `crossing/` 主题。
2. **头装 vs 体装传感器。** 人形压倒性头装（拟人，头跟随凝视）。四足分叉——Spot 体装（无脖子），Unitree Go2 头装。深度文 `whole_body_spatial_perception.md` 把后果摊开讲。

---

## 本目录文件

| 文件 | 用途 | 状态 |
|---|---|---|
| `whole_body_spatial_perception.md` | 头相机 + IMU + 足触发融合深度文；远眺问题；人形 vs 四足的传感器布置 | v1 |
| *（待写）* `humanoid_vio_under_footfall_shock.md` | 为何为无人机调好的 VIO 不能直接迁——振动谱不同 | TBD |
| *（待写）* `terrain_classification_for_footfall.md` | 远/近感知拆分；踏脚石选择 | TBD |
| *（待写）* `whole_body_policy_perception_seam.md` | 与全身 MPC + RL 策略的接口——策略侧指向 VLA-Handbook | TBD |

---

## 交叉引用

- **Aerial 平行：** `embodiments/aerial/vio/`——振动下的 VIO 是最接近的工程类比
- **传感器物理：** `foundations/sensor-physics/`——IMU-相机同步、ToF 人眼安全
- **跨子树：** `crossing/slam-vio-migration/`——humanoid 在迁移叙事里夹在 aerial 和 ground-mobile 之间
- **VLA 接缝：** [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)——全身策略 / RL / 运动控制器在那边。这里只管空间感知。

## 边界

本子树覆盖人形 + 四足的**空间感知、建图与体帧推理**。不覆盖：

- 全身运动控制、MPC、RL 策略训练 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)
- 硬件设计 / 执行器 / SEA / 液压 → 超出本手册范围
- 人形上半身做的 manipulation → `embodiments/manipulation/`（encoder 问题一样）
- AGV / 轮式室内 → `embodiments/ground-mobile/`

*维护者深度档：Major。2026 行业关注度高；预期该子树会在 2026–2027 快速生长。*
