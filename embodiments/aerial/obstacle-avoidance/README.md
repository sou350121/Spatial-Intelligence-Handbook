# 空中避障 / Aerial Obstacle Avoidance — 两条不收敛的工程路线

**Status:** v1 — opinionated draft. Latency / compute claims marked `UNVERIFIED` unless cited.
**Depth tier:** 🌬️ maintainer anchor（写得比其他 embodiment 轴深 1.5–2×）。
**Champion reference:** Kaufmann, Bauersfeld, Loquercio, Müller, Koltun, Scaramuzza — *Champion-level drone racing using deep reinforcement learning*, *Nature* 2023. [DOI 10.1038/s41586-023-06419-4](https://www.nature.com/articles/s41586-023-06419-4)。

**TL;DR：** 空中避障已分裂为两条**不收敛**的工程路线：**(A)** RL 训练的反应式端到端策略（UZH Swift、Loquercio *Science Robotics 2021* "agile flight in the wild"）——把感知→动作压进单一网络；**(B)** 经典规划+局部几何地图（Skydio 级电影摄影、ETH-Zurich Faster / EGO-Planner 谱系）——显式维护障碍表示并在其上重规划。分裂不是教派之争，而是追踪两个不同的代价函数：**赛速下的 time-to-collision** vs. **电影摄影速度下的平滑度+构图**。Foundation models 暂时进不来这个 loop——它们慢 1–2 个数量级。

---

## 1 · 为什么避障是空中与地面机器人分道扬镳的点 / Why aerial diverges here

Roomba 可以停、AGV 可以停、汽车也可以停（刹车距离长但动作存在）。**多旋翼在 15 m/s 时无法在动力学意义上停下**——把动能耗光需要 ~1–2 s 的抬头减速行程，期间"不撞障碍"已经不是当前生效目标。你拥有的控制权是**改向**，不是**刹车**。

这一个事实重塑了整个问题：

- 真正要回答的不是"前方有没有障碍？"，而是"在感知 horizon 之内、动力学+作动器极限可行、且能绕开障碍包络的轨迹是否存在？"
- "感知 horizon" 本身就是速度的函数。2 m/s + 5 m 立体测距 = 2.5 s headway；20 m/s 同样测距只剩 0.25 s——已经短于级联控制器的响应窗口。
- 障碍的代价不对称。15 m/s 撞电线机毁；蹭到树叶没事。**目前公开的避障栈都没有把这种不对称建模好。**

这就是为什么空中避障需要单独成章，而非合并进通用的 "planning"。

---

## 2 · 两条路线对比 / The two schools

| Axis / 维度 | School A：RL 反应式（UZH Swift / Loquercio agile flight） | School B：经典规划（Skydio / ETH-Z Faster / EGO-Planner） |
|---|---|---|
| 表示 / Representation | 隐式（在策略权重里） | 显式局部 3D map（ESDF / occupancy / TSDF） |
| 主要传感 | Event camera + RGB + IMU（UZH）；RGB-D + IMU（Loquercio） | Stereo + IMU +（有时）下视 TOF |
| 规划 horizon | ~0.1 s（网络内反应） | 1–3 s（MPC / B-spline） |
| Replan rate | 隐式（策略前馈） | 5–30 Hz `UNVERIFIED` |
| 计算占用 | Jetson Orin Nano 上推理 &lt;50 ms `UNVERIFIED` | AGX 上 map update 10–30 ms + plan 5–15 ms `UNVERIFIED` |
| 运行包络 | 5–25 m/s，赛道式（已知 gate / 场景类） | 0.5–8 m/s，**未知**环境 |
| 失败模式 | OOD 场景；无 introspection | Plan infeasibility；地图陈旧；ESDF 空洞 |
| 用于电影摄影？ | 否（抖动、不擅长 target-following） | 是（Skydio 实际产品） |
| 用于穿越机竞速？ | 是（UZH 赢过 FPV 赛事） | 否（太慢） |

从表底往上读：**两条路线优化的是不同的代价函数**，所以"哪条更强"的说法基本是 benchmark-shaped——各自赢各自的 benchmark。

---

## 3 · 延迟预算 / Latency budget（公开论文几乎都不全写）

赛速 15 m/s 在 100 ms 内走 1.5 m；电影摄影 5 m/s 在 100 ms 内走 0.5 m。端到端感知→动作的预算必须满足：

```
   t_perceive + t_plan + t_actuate + t_aero_response  ≤  d_safe / v
```

数量级拆分 `UNVERIFIED`：

| Stage / 环节 | 竞速 (15 m/s, d_safe = 2 m) | 电影摄影 (5 m/s, d_safe = 1.5 m) |
|---|---|---|
| 可用总预算 | ~130 ms | ~300 ms |
| Perception（depth / events → features） | 10–20 ms | 30–80 ms |
| Planning / policy inference | 5–30 ms | 20–80 ms |
| Controller actuation（cmd → thrust） | 20–40 ms | 20–40 ms |
| Airframe aero response（commanded tilt → realized accel） | 50–80 ms | 50–80 ms |
| **Headroom / 余量** | ~10–25 ms（几乎贴线） | ~100 ms（舒服） |

两个含义：

- **Foundation models 在赛速档完全出局。** VGGT 级模型 100–400 ms 延迟（见 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`）直接吃光整个赛速预算。在 inner loop 里"GPT-for-obstacles"——除非再来 10× 压缩——否则没有路径。
- **电影摄影档 foundation model *可能*能上**——但只能当慢速副通道（场景理解、遮挡后 target re-identification），永远不会是 obstacle 的主源。

---

## 4 · 什么算"障碍"取决于速度 / What counts as an obstacle is speed-dependent

隐式的对象本体随代价函数迁移：

| 速度区间 | 主要障碍类 | 最低传感 | 通常被忽略的 |
|---|---|---|---|
| 悬停 / &lt;2 m/s（巡检） | 墙、脚手架、电线、人 | Stereo 或 LiDAR | 树叶摆动、扬尘 |
| 电影摄影 2–8 m/s | 树、枝、建筑、人、地形 | Stereo + 下视 TOF + IMU | 电线（常漏）、细叶 |
| 竞速 10–25 m/s（已知赛道） | Gate、赛道障碍、地面 | Event + RGB + IMU | 一切不在赛线上的东西 |
| 户外巡航 8–15 m/s | 高压线、树、地形 | Stereo + IMU + (理想: thermal) | 鸟、碎屑 |

两个要点：

- **高压线和细电线在 stereo-only 栈上仍是未解。** Skydio 承认这是已知限制 `UNVERIFIED, blog source`。2 MP stereo 在 10 m 处看 5 mm 电线，几何 SNR 已经低于大多数 disparity estimator 的噪声底。
- **赛速档的障碍集合是*被策展过的*（已知赛道）。** 把 UZH 风格 RL 推广到未知障碍分布，是当前开放研究问题——Loquercio et al. *Science Robotics 2021* "Learning high-speed flight in the wild" 是最干净的一步。[DOI 10.1126/scirobotics.abg5810](https://www.science.org/doi/10.1126/scirobotics.abg5810)。

---

## 5 · 两条路线各自怎么坏 / Where each school breaks

**School A（RL 反应式）失败模式：**

- OOD 场景——障碍类换了（电线 vs. 树枝），策略静默失败，无 introspection 信号。
- Sim-to-real 在光度上的鸿沟——UZH 用事件相机缓解（光度域漂移小）；RGB-only RL 迁移很差。
- 加新约束（如"避开人"）没有干净的接口；唯一旋钮是重训。

**School B（经典规划）失败模式：**

- 飞得比地图更新快时 map 陈旧（大多数 ESDF 栈在 8–10 m/s 以上就跟不上）。
- 激进飞行下 plan infeasibility——kinodynamic 约束通常偏保守，导致"plan 存在但控制器跟不上"。
- 无纹理表面（白墙）上 ESDF 出洞——stereo 深度失效，地图把墙看成"自由空间"。

诚实的读法：**两条都不是通用解**，各自只在自己的包络内出货。

---

## 6 · 2027 前 foundation models 会进 loop 吗 / Will FMs enter this loop by 2027?

可证伪预测：**2027-12 之前，没有任何出货的空中自主栈会用 VGGT 级或 VLM 级 foundation model 作为主要 obstacle 源**。最多以这些方式出现：

- 慢速（≤2 Hz）全局重定位通道，纠正局部地图。
- Open-vocabulary 语义层叠在几何障碍之上（"避开那个特定的人"、"距任何车辆 2 m"）。
- 离线 scene-class 检测器，在多个反应式策略之间 gating（Loquercio 风格的 domain selector）。

Inner-loop 的 obstacle 主源仍是 stereo + IMU（或 event + IMU）。2026 任何号称"VLM-in-the-loop 真机竞速"的论文——下注它做不到。

---

## 7 · 给读者的指引 / For the reader

- **机械臂工程师** — 你的障碍问题是*静态 + 慢*。空中反应式策略不是你的参考；5 Hz 经典重规划更接近你的世界。
- **AD 工程师** — 最接近的类比是高速换道（运动学改向、无刹车）。但你的传感预算是 10× 富，不要把空中的"只用 stereo + IMU"那种节俭照搬过来。
- **空中工程师** — 用代价函数选路线，不要用论文数量选。电影摄影 ≠ 竞速。别让一场竞速 demo 把你诱进 RL，结果客户要的是丝滑 gimbal 镜头。
- **研究者** — 细电线问题开放、OOD-introspection 开放、"VLM 作为经典规划器的语义层"架构还没有规范出货栈。三个都是 2026–2028 级研究楔子。

---

## References

- **Swift (champion-level racing)** — Kaufmann et al. *Nature 2023*. [DOI 10.1038/s41586-023-06419-4](https://www.nature.com/articles/s41586-023-06419-4)
- **Agile flight in the wild** — Loquercio et al. *Science Robotics 2021*. [DOI 10.1126/scirobotics.abg5810](https://www.science.org/doi/10.1126/scirobotics.abg5810)
- **EGO-Planner** — Zhou et al. *IEEE RA-L 2020*. [arXiv 2008.08835](https://arxiv.org/abs/2008.08835)
- **Faster** — Tordesillas & How *IROS 2019*. [arXiv 1903.03558](https://arxiv.org/abs/1903.03558)
- **Skydio autonomy engineering blog** — https://www.skydio.com/blog（无单一规范论文）
- **跨实体延迟 / VGGT 上下文** — [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)

## Boundary

本文在*空中实体层*剖析避障方法学——两条工程路线、各自的延迟预算、各自在哪儿坏。单篇论文级剖析（Swift、EGO-Planner、Faster）写出来时归各自文件。跨实体的"避障在 manipulation / ground / aerial 之间如何不同"归 `crossing/`（尚未撰写）。传感侧细节（stereo baseline 计算、event-cam contrast threshold）放在 [`foundations/sensor-physics/`](../../../foundations/sensor-physics/)。Active tracking 共用同一套 stereo rig 但目标函数不同，归 [`../active-tracking/`](../active-tracking/)。
