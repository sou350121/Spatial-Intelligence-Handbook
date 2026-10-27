[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# 以行为树实现异构多机器人团队分层去中心化任务自主 (MATE-BT: A Behavior-Tree-Based Framework for Hierarchically Decentralized Mission Autonomy in Heterogeneous Multi-Robot Teams)

> **发布时间**：2026-10-26（arXiv:2610.35429v1 [cs.RO]）
> **论文 / 模型名**：MATE-BT（Mission, Allocation, and Task Execution with Behavior Trees）
> **核心定位**：把「任务推进 / 分配 / 执行」拆成三层、并把 mission 管理权做成可在机器人之间转移的行为树框架——比单体重规划（PlanSys2 式 PDDL→BT）响应快一个量级，且能扛住执行机器人甚至当前 leader 的失效。

多机器人团队执行预定义任务时，真正的痛点不是「会不会规划」，而是**运行期出现扰动（新目标、机器人失效）时该在哪一层改**。单体会话式符号规划只要一处失效就要重生成整份 plan；MATE-BT 的答案是分层 + 只更新受影响的层，并用 30 机器人 / 120 目标的约 130 ms 响应时间给出工程证据。

## X-Ray 开场

MATE-BT 解决的是「异构多机器人团队在无人干预下把一段预定义任务跑完、并在机器人掉线时不断链」这件事：它把系统切成 mission execution（Swarm BT 里的 Mission BT）、allocation（Swarm BT 的 AssignTask + Agent BT 的 MRTA plugin）、task execution（Agent BT 的 Task BT，用 PA-BT backchaining 现场展开）三层。它提出的不是新算法，而是**一套分层去中心化的组织方式**：所有 leader-capable 机器人各跑一份完全相同的 Swarm BT，但只有当前 leader tick mission 子树；leader 超时后按优先级顺位接管，mission policy 本身不丢。

对 spatial AI 研究者意味着：这是一份「**系统集成范式**」参考——BT 作为可组合的运行时骨架、MRTA 作为可插拔的分配后端、ROS 2 作为通信底座；它的实验方法论（HILS 资源测量 + 真机 4 台 LIMO + 与单体 POPF baseline 的响应时间对比）比它的算法更值得抄。

## 📍 研究全景时间线

```
2016-2020  ROSPlan / PDDL 单体符号规划
             └─ 全局一份 plan，失效 → 整份重生成                    [13][14]
2020-2023  HTN / 集中优化 / 集中拍卖
             └─ 分配完整 task 给机器人，mission 权仍在中心          [16][17][18][19]
2021-2023  分层多机器人 BT（全局/分配/执行树在每台机上复制）
             └─ 只做解析式容错论证，无仿真/真机实验                  [10]
2023-2025  分布式拍卖 / 效用委派 / 去中心化拍卖
             └─ 分配下沉了，但 mission 管理仍集中或未定义其失效续接  [23][24][25]
2026       ★ MATE-BT
             └─ 三层解耦 + leader 可转移 + MRTA 插件化
                Webots + 4 台 LIMO 真机 + HILS 资源测量
   本文局限：mission policy 与 PPA library 仍需人工编写；
             真机无异构（4 台同型 LIMO，UAV 仅在仿真）；
             任务分配（AssignTask）仍是内置贪心，未插件化
```

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| **GatherMissionInfo**（Swarm BT 叶节点） | ROS topics：世界信息、队伍信息、任务执行反馈 | 写入本地 blackboard | 无学习；纯在线刷新 |
| **AmILeader**（条件节点） | alive signal（ID / robot type / leader priority）+ 本地 membership view | Success = 自己是最高顺位候选 | 无学习；优先级由配置给定，同优先级按 robot ID 破平 |
| **Mission BT**（Sequence of phases） | 任务策略（有序 phase，每 phase 含 task 请求 + 完成条件） | blackboard 上的 task request；phase 完成则推进 | 无学习；**由应用设计者手写**（论文 Remark 2） |
| **AssignTask**（Swarm BT） | 未 scoped 的 robot 集合 `R_unsc`、任务 `k`、`w_k`、`c_{r,k}`、上限 `n_k` | 机器人专属 task request | 无学习；每 tick 贪心重解 |
| **ScopeOf**（decorator） | mission policy 里的 robot-type 指定 | 把 task 专属派给该类型；该类型耗尽则退化为 unscoped | 无学习 |
| **BroadcastTask / ReceiveTask** | 当前 task request | ROS topic 广播 / 写入各机器人 blackboard | 无学习；每 tick 广播 |
| **AssignTarget + MRTA plugin**（Agent BT） | 可用 target 集合、机器人状态、收到的消息 | 本地 blackboard 上的 target | 无学习；插件可为 CBAA / CBBA / distributed Hungarian / GRAPE |
| **Task BT + PPA library** | 当前 task + target → 期望 postcondition | 现场 backchain 出的动作子树 | 无学习；每次 assignment 变化时重装子树 |
| **Action primitives** | 动作调用 | ROS action / service / topic | 平台相关，由用户提供 |

关键点：**全篇没有任何训练环节**，所有模块都是在线规则 / 在线优化；「训练-推理差异」这一列在本文语境下恒为「无」。

### 1.2 关键机制

**⚡ Eureka Moment：把「去中心化」做成层级化的——leader 不是中心服务器，而是「一份被复制的、只有一个人 tick 的 Swarm BT」**，于是 mission 管理权可以在机器人之间像接力棒一样传下去，而 mission policy 本身不需要重建。

配套的两个次級洞见：
1. **只更新受影响的层**：新目标来了改 target assignment；机器人挂了改 task assignment；leader 挂了换 tick 的人。**没有一层需要「重生成整份 plan」**——这正是与单体 PDDL baseline 拉开差距的机制来源。
2. **分配接口标准化**：Target assignment 被抽成「本地决策 + 机器人间冲突消解」两阶段插件接口，让 CBAA / CBBA / distributed Hungarian / GRAPE 在不改 Mission BT 与 Agent BT 的前提下互换——把「用哪种 MRTA」变成配置项而不是架构决策。

### 1.3 信息流 / 架构图

```
┌──────── leader-capable robots：每台各跑一份完全相同的 Swarm BT ────────┐
│ Swarm BT (ReactiveSequence)                                            │
│   GatherMissionInfo → AmILeader → Parallel( Mission BT ,               │
│                                             AssignTask ,               │
│                                             BroadcastTask )            │
│   ※ 只有 active leader 的 Mission 子树被 tick                          │
└──────────────────────────┬─────────────────────────────────────────────┘
                           │ ROS topics（task request / 执行反馈 / alive 5 Hz）
                           ▼
每台机器人 onboard（ROS 2 Jazzy，Swarm BT 与 Agent BT 跑在异步的两个 node）
  Agent BT
    ReceiveTask ──► AssignTarget ──(MRTA plugin: 本地决策 ⇄ 冲突消解)──► target
                        │
                        ▼  (task, target) 变化 → 设定期望 postcondition
                   Task BT  ←── PA-BT backchaining over PPA library
                        │           （递归补齐 postcondition 与未满足 precondition）
                        ▼
                   action primitives ──► ROS action / service / topic
```

注意图里 **allocation 是横跨两棵树的**：task assignment 在 Swarm BT，target assignment 在 Agent BT。这是全文最容易被面试官追问的结构细节。

## 2 · 数学核心

📌 **Napkin Formula**：`u(r,k) = w_k · c_{r,k} / max_{r'∈R_unsc} c_{r',k}` —— 用「任务重要性 × 相对能力」排序，每 tick 贪心拍一次；系统其余部分不优化，只重评估。

**目标**：在每个 tick，把「未 scoped」的机器人一对一（或最多 `n_k` 对一）地贴到未 scoped 的任务上，使高重要度、高能力的匹配先被接受。

**公式**（论文式 (1)）：

```
u(r,k) = w_k · c_{r,k} / max_{r' ∈ R_unsc} c_{r',k}
```

**变量说明**：

| 符号 | 含义 |
|---|---|
| `r ∈ R_unsc` | 尚未被 scoped 任务占用的机器人 |
| `k` | 一个 unscoped 任务请求（如 rescue / suppress / return） |
| `w_k` | 任务重要度 |
| `c_{r,k}` | 机器人 `r` 对任务 `k` 的能力值 |
| `n_k` | 该任务允许的最大机器人数 |
| `u(r,k)` | 匹配效用；分母用「该任务上最强候选的能力」做归一化 |

**直觉**：分母归一化让不同任务之间的效用可比——即一个「弱任务上的最强者」不会因为绝对能力值小而永远排在后面。算法本身是**降序贪心**：按 `u(r,k) > 0` 降序处理 `(r,k)` 对，接受即写为机器人专属 task request。贪心意味着无最优性保证、无交换（swap）修复，这与 §3 里看到的「reassignment 抖动」直接相关。

**第二组公式：leader 顺位与接管延迟**

```
AmILeader(robot i) = Success  ⟺  i = argmax_{j ∈ View_i} rank(j)
rank(j) = (priority_j, ID_j)   # 字典序，priority 为主、ID 破平
handover_latency ≈ τ − Δ       # Δ = 最后一次收到 alive signal 到真实失效的间隔
```

其中 `τ` 是 alive-signal 超时阈值（本文设 2.5 s）。论文报告 handover latency 「slightly below τ = 2.5 s because the timeout started from the last received alive signal, before the failure」——这条注释是理解整个容错机制的关键：**检测粒度就是 alive 信号的周期（5 Hz）加 τ**，误差项来自失效发生在两次心跳之间的哪个位置。

## 3 · 带数字走一遍

> 下面是**玩具设定**，只用来演示式 (1) 与接管延迟怎么算；数字非论文报告值。

**设定**：Rescue phase，rescuer 原本是 1 台 Rescue UGV（priority 0）。该机失效后，剩 3 台 Fire UGV（priority 1/2/3），`c_{r,rescue}` 依次取 0.8、0.6、0.4；`w_rescue = 1.0`；任务上限 `n_k = 2`。

1. **失效前**：Rescue UGV 是 scoped 的 rescue 执行者，Fire UGV 只做 escort/suppress，`R_unsc` 里没有 rescue 候选。
2. **Rescue UGV 失效**：`τ = 2.5 s` 内没有收到它的 alive signal → 从 membership view 中剔除；同时 `ScopeOf` 发现「无该类型机器人剩余」，rescue 请求**退化为 unscoped**，进入 `AssignTask`。
3. **算效用**（3 台都在 `R_unsc`，`max c = 0.8`）：
   - Fire UGV(1)：`1.0 × 0.8 / 0.8 = 1.00`
   - Fire UGV(2)：`1.0 × 0.6 / 0.8 = 0.75`
   - Fire UGV(3)：`1.0 × 0.4 / 0.8 = 0.50`
4. **贪心接受**：降序处理，取前 `n_k = 2` 个 → Fire UGV(1)、Fire UGV(2) 承接 rescue；Fire UGV(3) 继续保持 suppress。论文的 Breakdown 1 场景记录的正是「two to rescue after Rescue UGV 1 failed」这一类 task reassignment（Table II：Task reassignments 4.0 ± 0.0）。
5. **接管延迟**：如果 leader 失效发生在最后一次心跳之后 `Δ` 秒，则接管延迟 ≈ `τ − Δ`。论文实测 Handover latency = **2.44 ± 0.08 s**（Breakdown 1）与 **2.46 ± 0.06 s**（Breakdown 2），确实「略低于 2.5 s」。
6. **代价**：任务重排后 `Task BT expansions` 从 Normal 的 **37.4 ± 0.5** 涨到 Breakdown 1 的 **51.2 ± 1.6**，完成时间从 **252.74 ± 12.28 s** 涨到 **323.61 ± 42.32 s**——「没有重规划」不等于「没有代价」，代价转移到了局部子树展开与重跑上。

## 4 · 工程视角

| 维度 | 论文报告值 | 说明 |
|---|---|---|
| BT tick 频率 | **10 Hz** | Swarm BT / Agent BT 的 tick 周期，也即响应时间的下限来源 |
| alive signal 频率 | **5 Hz** | 心跳；leader 检测的采样粒度 |
| alive 超时 `τ` | **2.5 s** | 判定「机器人失效」的唯一机制 |
| 单次响应 `t_full`（MATE-BT） | Reactivity 测试「remains near **100 ms**」；Scalability 测试「approximately **130 ms** with **30** robots and **120** targets」 | 论文明确「this response time is largely determined by the BT tick period」 |
| 单体 baseline `t_full` | 100 fires 时 approximately **370 ms**；30 机器人时 approximately **2,800 ms** | POPF 重规划；10 robots 以内「comparable」 |
| `t_replan`（baseline） | 「exceeds the tick period around **60** fires」 | 即重规划成本在 60 个火点时越过 100 ms |
| HILS CPU 增量（RPi 5） | **+19.9 ~ +22.5** 个百分点（相对 idle） | Active leader 29.3 / leader-capable 28.4 / Agent-only 26.7（idle 6.8） |
| HILS RAM 增量（RPi 5） | **+1.5 ~ +2.1** 个百分点；绝对值 1419 → 1534/1564/1586 MiB | 括号内为 %p |
| HILS CPU 增量（Jetson Orin Nano） | **+14.3 ~ +15.3** 个百分点 | Active leader 20.7 / leader-capable 20.2 / Agent-only 19.7（idle 5.4） |
| HILS RAM 增量（Jetson） | **+0.9 ~ +2.0** 个百分点；绝对值 1851 → 1916/1952/2006 MiB | 同上 |
| 真机 CPU / RAM 增量 | 「approximately **13** and **2** percentage points」 | 开启 MATE-BT 后；active leader 与非 leading 的 leader-capable 差别很小 |
| 端到端 mission 时长 | Normal **252.74 ± 12.28 s**；Breakdown 1 **323.61 ± 42.32 s**；Breakdown 2 **366.92 ± 33.63 s** | Webots，每场景 10 runs |
| 通信带宽 / 消息大小 | **论文未报告** | alive signal 只说明含 ID / robot type / leader priority |
| GPU 占用 / 功耗 | **论文未报告** | 全部为 CPU/RAM 口径 |
| 网络拓扑规模上限 | **论文未报告** | 只假设「connected, but not necessarily fully connected」 |

**Trade-off 读法**：
- **「多背一份 Swarm BT」的代价**：论文用 HILS 直接给了三个角色的对照（同一块板子分别扮演 active leader、非 leading 的 leader-capable、以及只跑 Agent BT 的普通机器人）。注意这三者的 CPU 增量区间是**重叠且接近**的（RPi 5 上 19.9 / 21.6 / 22.5 %p），也就是说在本文的测量精度下，**多跑一份 Swarm BT 并没有带来数量级的额外开销**——这正是 leader 冗余可行的前提。但请勿把这三列相减当作「Swarm BT 的单位成本」，论文并未这样报告。
- **延迟 = tick，不是 CPU**：MATE-BT 的响应时间被 10 Hz 钉死，所以在 30 机器人 / 120 目标下仍「approximately 130 ms」。想更快只能提高 tick 频率，而 tick 频率直接线性抬 CPU——这是部署时唯一真正的旋钮。
- **内存可忽略、CPU 需留余量**：RPi 5 上 RAM 只涨 1.5~2.1 %p（绝对约百 MiB 级），CPU 涨约 20 %p。在 Jetson Orin Nano 上更宽松（14.3~15.3 %p），因为基线 idle 只有 5.4%。

## 5 · 数据与评测

**没有公开数据集**。全部评测基于自建的火场搜救任务（fire-suppression-and-rescue），三个来源：

| 评测通道 | 设置 |
|---|---|
| **Webots 仿真** | 队伍配置见 Table I：Rescue UGV ×1（priority 0）、Fire UGV ×3（priority 1–3）、UAV ×2（仅仿真）。UAV 只做 search/return |
| **HILS（hardware-in-the-loop）** | 一块 Raspberry Pi 5 或一块 Jetson Orin Nano 跑某一个机器人的 BT；外部 PC 跑 Webots、底层控制器、其余机器人的 BT。每块板子按三种角色各测，每角色 **10** 次 HILS runs 取平均 |
| **真机** | **4** 台 AgileX LIMO（1 Rescue UGV + 3 Fire UGVs），全部 leader-capable；每台机载 Jetson Orin Nano 跑 Swarm BT + Agent BT + 驱动栈；中央只提供 Zenoh 通信层与 detected-target 信息；室内，Nav2 driving stack |

**指标与条件（讲条件而不只讲结论）**：

- **任务连续性**（Table II）：Normal / Breakdown 1 / Breakdown 2，每场景 **10** runs，**same random seeds**。两个 breakdown 场景都含 Fire UGV 1 在 Rescue phase 失效；active leader（Rescue UGV 1）分别在 Breakdown 1 的 Rescue phase 随机时刻失效、Breakdown 2 的 Suppress phase 停在 base 时失效。Runs completed 三者均为 **10/10**。
- **Reassignment 计数口径**：Task reassignments 统计「phase 内」的任务变更，**排除** phase transition；Breakdown 1 计 **4.0 ± 0.0**（1 次 escort 切换 + 2 次 rescue + 1 次回到 suppression），Breakdown 2 计 **1.0 ± 0.0**（只有 escort 那一次，leader 失效未改变 suppression 分配）。
- **归一化观察**：把均值除以均值完成时间后，三个场景均为「approximately **14–15** reassignments per minute」，论文据此认为总量上升「partly reflected longer execution」。
- **响应性 / 可扩展性（Fig. 5）**：**只用 Suppress phase**；两法同环境、共用 ROS 状态接口、**100 ms tick period**；**机器人全程静止**以隔离计算响应。Reactivity 测试用 10 台 Fire UGV，每 5 s 加 5 个火点，活跃火点从 10 增到 100；Scalability 测试机器人 5→30，火点为机器人数的 4 倍。
- **⚠️ 重要条件**：为匹配 baseline 的集中式设定，「MATE-BT's target assignment was run centrally with the Hungarian algorithm in this comparison only」——即 Fig. 5 里 MATE-BT 那一侧**不是**去中心化插件在跑。
- **插件对比（Table IV）**：5 台 Fire UGV，**只用 Suppress phase**，每 case **15** episodes，火点位置每 episode 随机。Case 1 = 25 个分散火点；Case 2 = 25 个聚集火点；Case 3 = 5 批 × 5 个火点顺序出现；Case 4 = 3 个大火焰（合作压制，压制速率正比于机器人数量）。指标 = mission completion time + total travel distance。

**Table IV 真值（节选，mean ± s.d., 15 episodes）**：

| Allocator | Case 1 时间 | Case 2 时间 | Case 3 时间 | Case 4 时间 |
|---|---|---|---|---|
| CBAA | 103.54 ± 11.54 | 90.36 ± 15.93 | 178.34 ± 18.45 | 86.99 ± 1.86 |
| Dist. Hungarian | 102.88 ± 7.48 | 93.62 ± 16.50 | 155.84 ± 10.14 | 85.91 ± 1.99 |
| CBBA | 101.13 ± 8.53 | **83.70 ± 7.99** | 181.49 ± 12.57 | 86.96 ± 1.67 |
| GRAPE | 103.92 ± 12.01 | 105.86 ± 13.89 | 227.24 ± 33.06 | **60.11 ± 4.89** |

| Allocator | Case 1 距离 (m) | Case 2 距离 (m) | Case 3 距离 (m) | Case 4 距离 (m) |
|---|---|---|---|---|
| CBAA | 313.97 ± 36.22 | 265.18 ± 87.00 | 453.74 ± 35.66 | 46.12 ± 5.79 |
| Dist. Hungarian | 337.74 ± 49.21 | 292.12 ± 93.39 | 478.55 ± 48.58 | 44.96 ± 5.02 |
| CBBA | **243.23 ± 19.64** | **157.05 ± 19.75** | **350.55 ± 29.42** | 46.06 ± 5.73 |
| GRAPE | 396.58 ± 68.27 | 377.38 ± 76.80 | 1040.10 ± 191.20 | 112.83 ± 26.24 |

结论是**方向性的**：「No plugin performs best across all cases and both metrics」——CBBA 在 Case 1–3 距离最短，Case 2 时间最短；distributed Hungarian 在 Case 3 时间最短（155.84）；GRAPE 只在 Case 4 靠合作压制拿到最短时间（60.11）但距离最长（112.83）。**不要**把某一行说成「总体最优」。

## 6 · 能力与失败模式

**能做（有实验支撑）**：
- 新目标（新火点 / 新受害者的 target 集合变化）下**不重生成 plan**，只更新受影响层；30 机器人 / 120 目标仍 approximately 130 ms。
- **执行机器人失效**后重派任务：Fire UGV 1 失效 → escort 任务转给 Fire UGV 3。
- **active leader 失效**后接管：Rescue UGV 1 失效 → Fire UGV 2（priority 顺位下一台）接管并「regenerated the current-phase task requests」；`AssignTask` 在没有 Rescue UGV 的情况下按效用把 rescue 派给两台 Fire UGV，「robots with unaffected assignments continued their tasks」。
- **MRTA 插件热插拔**：四个插件在不改 Mission BT / Agent BT 的前提下互换，且四个 case 各自产生不同的赢家。
- **机载闭环**：真机上 MATE-BT 全部计算 onboard，中央只给通信 + target 检测。

**不能做 / 论文明确未覆盖**：
- **不会重规划 mission policy**：「The mission policy is assumed to remain valid throughout execution」——mission 层面的语义变化（比如出现 policy 里没定义的任务类型）无解。
- **新任务需人工编码**：结论自承「Applying MATE-BT to a new mission currently requires manually specifying the Mission BT and the PPA library」。Remark 2 把 Mission BT、效用/成本模型、PPA library、action primitives 全列为「application designer 提供」。
- **任务分配不可插件化**：`AssignTask` 是内置贪心；只有 target assignment 有标准插件接口。结论把「Extending plugin-based configuration to AssignTask」列为 future work。
- **分区期间不保证一致**：Remark 1 只说重连后收敛（「After reconnection, the robots select a common leader once alive-signal exchange brings their membership views into agreement」），分区期间可能出现多个 leader、各自推进。
- **真机未验证异构性**：4 台全是同型 LIMO；UAV 只在仿真；异构性（`ScopeOf` 的 robot-type 语义）在真机上没有被压测。
- **没有感知闭环**：真机上「central infrastructure supplies only the communication layer and detected-target information」——目标检测不是本文解决的。
- **失效模型只有 crash-stop**：唯一检测机制是 alive signal 超时，没有错误行为、没有拜占庭。

### 隐含假设 (Hidden Assumptions)

1. **失效 = 心跳静默**。任何「还活着但不干活 / 发错消息」的机器人都不在模型内；`τ` 同时承担了「检测延迟」与「误判风险」两个互相拉扯的角色。
2. **mission policy 静态且正确**。三层解耦的收益建立在「顶层不变」之上；一旦 policy 需要演化，框架退回到人工改 Mission BT。
3. **phase 完成条件可观测**。Remark 1 明说「All phases in the evaluated mission define completion using such observable information」——这条是 leader 接管后能「从第一个 phase 重新评估」的前提。
4. **通信最终连通**。正常运行假设「connected, but not necessarily fully connected」，分区被视为暂时事件。
5. **leader 优先级是全局静态配置**，且所有 leader-capable 机器人拿到同一份；一致性靠「相同视图 → 相同结果」这个确定性函数保证，而非共识协议。
6. **能力值 `c_{r,k}` 与重要度 `w_k` 是已知常量**，不随机器人状态（电量、载荷、损伤）在线变化。
7. **每个机器人同时最多一个 task**（「Each robot executes at most one task at a time」），任务不可并行叠加。
8. **target 由外部提供**：真实系统中 target 列表来自中央检测，框架不判断 target 是否真实存在。
9. **BT tick 是准同步的**：10 Hz 的响应下界假设 tick 能按时到达；论文未报告 tick 抖动或时钟同步方案。

## 7 · 与相关工作对比

| 方法族 | 代表 | mission 管理 | task 分配 | target 分配 | 局部执行 | leader 失效续接 | 真机实验 |
|---|---|---|---|---|---|---|---|
| 单体符号规划 | PlanSys2 [13] / ROSPlan [14] | 中央 plan | 中央 plan | 中央 plan | 执行 dispatched action | 需 plan 级更新/重生成 | — |
| 分区执行 + 分级恢复 | [15] | 中央生成 | 按失败影响选局部重规划/重分配/全重规划 | 同左 | team-specific BT executor | 依赖中央 | — |
| HTN / 集中优化 / 集中拍卖 | [16][17][18][19] | 中央 | 中央 | 中央或按本地 bid 选 | robot-local BT | 未覆盖 | — |
| 单机 FSM + BT | [20][21] | 单机 phase/mode | 不涉及 | 不涉及 | 本地 BT | 不涉及 | — |
| 复制式分层 BT | [10] | 每台机复制全局树 | 每台机自算 | 每台机自算 | 本地树 | 未说明冲突消解 | 仅解析论证 |
| 中央 mission + 动作拍卖 | [23] | 保留中央 mission controller | 拍卖 prerequisite action | 在线扩展本地 BT | 本地 BT | 未覆盖 | — |
| 效用委派 / 去中心化拍卖 | [24][25] | 部分下放 | 子树委派 / 拍卖 | 拍卖 | 本地 | 未说明 mission 管理续接 | — |
| **MATE-BT（本文）** | — | **Swarm BT 复制 + 单 leader + 顺位接管** | **Swarm BT 内贪心 `u(r,k)`** | **Agent BT 内 MRTA 插件（4 种）** | **PA-BT backchaining 现场展开 Task BT** | **✔ 2.44/2.46 s 实测** | **✔ 4 台 LIMO，onboard** |

**面试 Tip**：被问「MATE-BT 相比 PlanSys2 这类单体规划强在哪」，**不要答「算法更强」**——它的分配就是个贪心、目标分配直接用现成 MRTA。标准答法是：「它的贡献是**把扰动的处理范围最小化**：mission / allocation / task 三层解耦，加上 leader 可转移，所以新目标只改 assignment、机器人挂了只改 task assignment，全程不重生成 plan。数字上是 30 机器人 / 120 目标 approximately 130 ms，而重生成 plan 的 baseline 在 30 机器人时 approximately 2,800 ms。但要注意这个对比里两边 tick 都是 100 ms、机器人静止、而且 MATE-BT 那一侧为了公平还把 target assignment 换成了集中式 Hungarian。」

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-27)

**仓库状态核查**：全文只出现一个外部链接——视频 `https://youtu.be/xHf-y_1Dl6M`。**论文未给出任何 github.com 仓库地址**（无 repo URL、无 commit、无 issue 编号）。因此本节**不含任何经 issue 验证的条目**，以下 3 条 pitfall 全部由 §6 的失败模式 + §1/§4 的方法约束**推导**，标注为未经社区验证。

**P1 · tick 频率是唯一延迟旋钮，但它同时是 CPU 旋钮**
- 来源约束：§1.3 中 Swarm BT 与 Agent BT 都是「每 tick 重评估」的 BT；论文明确 `t_full`「largely determined by the BT tick period」，且实现在 10 Hz（100 ms）。
- 来源失败模式：§6 的「响应下界 = tick」+ §4 的「CPU 增量 19.9~22.5 %p 是在 10 Hz 下测得」。
- 推导结论：把 tick 提到 20 Hz 以追上更快的外部扰动，等于把 §4 表里的 CPU 增量按 tick 数放大，而 RPi 5 上 idle 只有 6.8%——余量存在但不再宽裕。论文既未报告更高 tick 下的资源曲线，也未报告 tick 抖动，**在需要 &lt;100 ms 反应的应用里必须自行补测**。

**P2 · `AssignTask` 每 tick 全量贪心 + `BroadcastTask` 每 tick 广播 → 潜在分配抖动（flapping）**
- 来源约束：§1.2 中 `AssignTask`「At each tick ... greedily processes pairs ... in descending order of `u(r,k)`」，`BroadcastTask`「publishes the current task requests at every tick」；无滞后项、无切换代价、无 swap 修复。
- 来源失败模式：§5 中 Table II 显示 target reassignments 高达 63.4–85.6 次、Task BT expansions 37.4–51.2 次——说明分配确实在频繁变动；论文把这归因于「更长的执行时间」（约 14–15 次/分钟），但没有报告任何抑制抖动的机制。
- 推导结论：当两个机器人的 `u(r,k)` 接近（能力同型、`w_k` 相同，例如 3 台全新 Fire UGV），tick 间的微小状态差异就可能让同一任务在两个 tick 内来回换手，触发 Task BT 反复卸载/重装（`Task BT` 的子树「installed ... whenever either changes」）。同型机器人队伍恰恰是本文真机配置（4 台同型 LIMO），风险不低。

**P3 · `τ` 的调参是「接管快」与「误判」的硬冲突，且分区期间无一致性保证**
- 来源约束：§2 中 `handover_latency ≈ τ − Δ`，实现在 `τ = 2.5 s`、alive 5 Hz；§6 隐含假设 4「通信最终连通」，Remark 1 只承诺重连后收敛。
- 来源失败模式：§5 实测 handover latency 2.44 / 2.46 s，几乎贴住 `τ`；而论文同时假设网络「not necessarily fully connected」且「delays may cause temporary differences in robots' local information」。
- 推导结论：把 `τ` 压到 1 s 以加快接管，在多跳延迟下会把「慢」误判成「死」，触发反复换 leader 并把 Mission BT Sequence 反复 reset（Remark 1：成为 leader 或视图扩张时 **reset 到第一个 phase 重新评估**）；把 `τ` 放大则接管变慢。更关键的是，分区期间两个 group 会各自选出 leader 并各自推进 phase——重连后的「收敛」只统一 leader 身份，**不保证已经分叉的 phase 进度能被回滚**。

---

[← Back to navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`；本文所有数值均逐字取自 arXiv:2610.35429v1 正文（Table I–IV、Fig. 5 描述、Sec. III 文字），未做四舍五入或推算；标注「论文未报告」的项（带宽、消息大小、GPU、功耗、tick 抖动、网络规模上限）为全文确实未给出的量。

[//]: # "<!-- source: https://arxiv.org/abs/2610.35429 -->"
