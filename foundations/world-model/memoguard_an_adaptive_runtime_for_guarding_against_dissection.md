[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# MemoGuard：通信受限机器人导航中"记忆陷阱"的自适应运行时防护 (MemoGuard: An Adaptive Runtime for Guarding Against Memory Traps in Communication-Limited Robot Navigation)

> **发布时间**：2026-07-17（arXiv:2607.15589v1 [cs.RO]；ESWEEK CODES 2026 Late Breaking Results track，正式版将发表于 IEEE Embedded Systems Letters）
> **论文 / 模型名**：MemoGuard
> **核心定位**：一句话——它指出"检索相似 ≠ 执行有效"，在情节记忆复用（episodic reuse）与动作执行之间插入一层**契约校验运行时**（拓扑 / 资源 / 结果可靠性三道硬门），使通信受限机器人既能避开相似度复用带来的不安全记忆，又不必每步都调用昂贵的 LLM 兜底。

导语：通信受限的巡检 / 搜救机器人在断联期间最便宜的决策方式是"翻旧账"——检索一段过去的执行情节并复用其动作。但检索分数高只说明**语义像**，不说明**还能执行**：边被堵了、电量余量不够了、备选观测点没了，记忆就变成了"高相似度但执行无效"的**记忆陷阱（memory trap）**。MemoGuard 的结论是：把复用从"检索问题"改成"校验问题"，可以在仿真里把电池安全违规率从 67.4% 压到 15.8%（相对降 76.6%），同时比"每步都推理"少 21.4% 的 fallback 调用。

## X-Ray 开场

问题：在无法连远端操作员 / 云规划器的区间里，机器人只能在"复用旧记忆（便宜但不安全）"和"本地 LLM 推理兜底（安全但贵）"之间二选一，而现有 episodic memory 方法几乎都只按**检索相似度**决定复用，把执行前提当成了隐式假设。做法：MemoGuard 给每条记忆附一份**执行契约**（拓扑前置条件、视角可用性、期望动作代价、路径风险、安全约束），运行时用三道硬可行性门（拓扑 / 资源 / 结果可靠性）与位运算合取 `Φ = Φ_topo ∧ Φ_res ∧ Φ_out` 判定是否复用，全不通过才调用 planner / 本地 `llama3.2:3b` 兜底。对空间智能研究者意味着：**记忆系统的瓶颈不在表征与检索，而在"契约"这一层显式可验证的执行假设**——这是一个把 VLA/LLM 规划器的安全回路拆成"便宜校验 + 昂贵兜底"的通用范式。

## 📍 研究全景时间线

```
1990s───────2010s──────────2020──────────2024──────────2026─────────────────►
  │            │               │              │              │
Case-Based     Episodic         LLM as         VLM/LLM          MemoGuard
Reasoning      Memory for       high-level     onboard          (本文)
(CBR) 复用     Robot Nav        planner        fallback         │
  │            │               │              │                 │
  │  检索相似度主导复用决策     │   推理变强但能耗/延迟不可忽略   │
  │            │               │              │        ┌────────┴────────┐
  │            │               │              │        │ 契约化复用：三道 │
  │            │               │              │        │ 硬门 + 兜底触发  │
  └────────────┴───────────────┴──────────────┴────────┴─────────────────┘
                                                        本文局限
                                        ┌──────────────────────────────────┐
                                        │ · 仅图级（graph-level）仿真，     │
                                        │   无真实感知 / SLAM / 定位闭环    │
                                        │ · 原型只做 top-1（k=1），top-k 未评│
                                        │ · 资源门依赖动作代价估计精度      │
                                        │ · 结果门对冷启动记忆不设最小样本数│
                                        │ · 跨层契约（定位不确定度、通信质 │
                                        │   量、能量轨迹）留作 future work  │
                                        └──────────────────────────────────┘
```

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 | 备注 |
|---|---|---|---|---|
| Episodic Action Memory 记忆体 | 一次先前执行事件 | `m_i = (ι_i, x_i, a_i, κ_i, ρ_i)`：意图上下文、检索键、记忆动作、**执行契约 κ**、结果统计 ρ | 记忆库**离线**从 rollout 数据构建；推理时只读 | 共 **11,558** 条记忆 |
| Candidate Retrieval 检索 | 当前状态 `s_t` + 记忆库 `M` | top-k 候选 `C_t^k` | 无学习参数，纯打分排序 | 分数 `S_ret = λ_env·S_env + λ_agent·S_agent`，`λ_env=0.8, λ_agent=0.2` |
| Topology Gate 拓扑门 | `s_t`, `m_i.κ` | `Φ_topo ∈ {0,1}` | 规则判定 | 拒绝"所需边已堵 / 备选视角不存在"的记忆 |
| Resource Gate 资源门 | `b_t`, `C_act(s_t,m_i)`, `B_safe` | `Φ_res ∈ {0,1}` | 规则判定 | `b_t − C_act ≥ B_safe`；不可达时把代价视为 infeasible |
| Outcome Gate 结果门 | `ρ_i = (n^s, n^f)` | `Φ_out ∈ {0,1}` | 经验统计，非学习 | `R(m_i)=n^s/(n^s+n^f) > τ_out` |
| Fallback 兜底 | `s_t` | 从 `A` 中选一个动作 | **本地 llama3.2:3b 推理** | 动作集仅 6 个：`follow_planner / inspect_target / return_to_safe_waypoint / inspect_alternate_viewpoint / wait_for_recovery / abort_mission` |
| Graph Planner 执行层 | 被选中的移动动作 | 最小代价路径 | Dijkstra | 推理本身不是动作，只**选**动作 |

### 1.2 关键机制

**⚡ Eureka Moment：检索相似度与执行有效性是两个正交属性——相似度只能用来"排序候选"，不能用来"授权执行"；授权必须由一份可机械检验的执行契约给出。**

围绕这句洞见，方法只有三个动作：

1. **把隐式前提显式化**：过去的方法把"这段记忆能复用"当成默认，MemoGuard 要求每条记忆自带 `κ_i`（拓扑前置、视角可用性、期望代价、路径风险、安全约束）——即"这段记忆是在什么条件下成立的"。
2. **把授权判定做成合取门**：`Φ = Φ_topo ∧ Φ_res ∧ Φ_out`，任一为 0 即拒绝并顺延检查下一个候选（第 10 式）；只有全部候选被拒才付 fallback 的代价。
3. **把成本不对称当成设计杠杆**：校验是 O(1) 级的规则查询，兜底是 0.922 s / 9.288 J 的 LLM 推理（Jetson AGX Xavier, MODE_30W_ALL），所以"多加一层便宜校验"在总账上永远是赚的。

### 1.3 信息流 ASCII 图

```
                    ┌──────────── 离线：rollout 数据 ─────────────┐
                    │ 成功转移 → 存 memory, n^s+1                 │
                    │ 失败 rollout → 匹配签名则 n^f+1             │
                    └───────────────────┬─────────────────────────┘
                                        ▼
                              ┌───────────────────┐
                              │  Memory Bank      │  11,558 条
                              │  m=(ι,x,a,κ,ρ)    │
                              └─────────┬─────────┘
   当前状态 s_t                          │
 (node,target,battery,                   │
  loc-conf,comm,observ.)                │
        │                               │
        ▼                               ▼
 ┌────────────────────────────────────────────────┐
 │ ① Eligibility 掩码：intent / node / target /   │
 │    mission phase 过滤 → M_t                    │
 │ ② 打分 S_ret = λ_env·S_env + λ_agent·S_agent   │
 │    → TopK → C_t^k   （原型 k=1）               │
 └────────────────────────┬───────────────────────┘
                          ▼
        ┌─────────────────────────────────────┐
        │ ③ Contract Validation（硬门，合取）  │
        │   Φ_topo : 边未堵？视角仍存在？      │
        │   Φ_res  : b_t − C_act ≥ B_safe ?   │
        │   Φ_out  : n^s/(n^s+n^f) > τ_out ?  │
        └────────┬─────────────────┬──────────┘
             Φ = 1 │                 │ Φ = 0（检查下一候选）
                  ▼                 ▼  全候选被拒
           reuse a_i          ④ Fallback f(s_t)
        （零推理开销）        └→ llama3.2:3b 从 A 中选 1 个
                                    0.922 s / 9.288 J
                                        ▼
                               Graph Planner (Dijkstra)
                                    执行移动动作
```

## 2 · 数学核心

📌 **Napkin Formula**：
**复用当且仅当 `Φ(s_t, m_i) = Φ_topo ∧ Φ_res ∧ Φ_out = 1`；否则付钱推理。** 一句话：*相似度决定"看谁"，契约决定"信不信"。*

**目标**：在通信受限执行中选择监督动作 `a_t`，在"复用旧动作"与"调用兜底"之间做安全—效率权衡。

**决策规则（第 6 式）**：

```
a_t = a_i,   若 ∃ m_i ∈ C_t^k 使 Φ(s_t, m_i) = 1
a_t = f(s_t), 否则
```

**校验函数（第 5 / 10 式）**：

```
Φ(s_t, m_i) = Φ_intent ∧ Φ_topo ∧ Φ_res ∧ Φ_out
```

其中 `Φ_intent` 在 eligibility 过滤阶段已强制（所以运行时校验只剩三项）。

**三道门的变量说明**：

| 门 | 公式 | 变量含义 |
|---|---|---|
| 资源门（第 8 式） | `b_t − C_act(s_t, m_i) ≥ B_safe` | `b_t` 当前电量；`C_act` 执行该记忆动作的估计代价；`B_safe` 电量安全下限（实验取 `B_safe = 25`）。动作目标不可达 ⇒ 代价视为 infeasible ⇒ 直接拒绝 |
| 结果门（第 9 式） | `R(m_i) = n_i^s / (n_i^s + n_i^f) > τ_out` | `n^s`、`n^f` 为**等价 state-action 记忆**上累积的成功 / 失败计数 |
| 检索分（第 7 式） | `S_ret = λ_env S_env + λ_agent S_agent`，两者归一到 `[0,1]`，`λ_env + λ_agent = 1` | `S_env`：局部可见性、障碍状态、边代价；`S_agent`：电量余量、定位置信度等级。实验用 `λ_env=0.8`, `λ_agent=0.2` 以强调局部可通行性 |

**记忆体（第 2 式）**：`m_i = (ι_i, x_i, a_i, κ_i, ρ_i)`，`a_i ∈ A` 为 6 元有界监督动作集中的一个（第 1 式）。

**直觉**：这不是一个优化问题，而是一个**单调过滤**问题——每道门只会把候选集变小，不会变大，所以 `Φ` 的合取结构保证了"复用"是兜底的**严格子集**，安全性上界等于兜底策略本身（实验中 MemoGuard 的 Safety Viol. 15.8% 甚至略低于 Always Reasoning 的 16.5%，因为兜底 LLM 在某些场景也会选错）。代价是：`C_t^k` 里若**全部**是陷阱，MemoGuard 会退化成 Always Reasoning，一分钱省不下。

## 3 · 带数字走一遍

> **玩具设定**（数字为演示用，非论文实验值；论文的桶值见 §5）：单步决策，`B_safe = 25`，`τ_out = 0.5`，`λ_env=0.8, λ_agent=0.2`。

假设当前状态 `s_t`：节点 `n7`、目标 `T`、电量 `b_t = 30`、定位置信度 0.9、意图 `inspect T`。记忆库里有三条候选（原型 `k=1`，此处展开看各门作用）：

| 记忆 | `a_i` | `S_ret` | `Φ_topo` | `Φ_res` | `Φ_out` | `Φ` |
|---|---|---|---|---|---|---|
| `m_1` | `inspect_alternate_viewpoint` | 0.93 | **0**（该视角已被移除） | — | — | 0 |
| `m_2` | `follow_planner`（走侧路） | 0.91 | 1（边通畅） | **0**（见下） | — | 0 |
| `m_3` | `follow_planner`（绕行主干） | 0.88 | 1 | 1 | 1（`R=3/4=0.75 > 0.5`） | **1** |

逐步算：

1. **`m_1`（拓扑门）**：`κ_1` 要求备选视角 `v_alt` 存在。当前 `v_alt` 已被降级为普通节点（trap 类型 "Removed Alternate Viewpoint"）⇒ `Φ_topo = 0` ⇒ **拒绝**。注意 `S_ret = 0.93` 是全库最高分——这正是"记忆陷阱"的定义：`m_1 ∈ T_t^k` 但 `m_1 ∉ 无效集和` 之外。
2. **`m_2`（资源门）**：`C_act = 8`（走侧路，含绕行），`b_t − C_act = 30 − 8 = 22 < B_safe = 25` ⇒ `Φ_res = 0` ⇒ **拒绝**。若换个参数 `C_act = 4`，则 `30 − 4 = 26 ≥ 25` 通过——**资源门的判定对 `C_act` 估计误差极其敏感**，这一点在 §6 会变成"Reduced Battery 是最难的一类陷阱"。
3. **`m_3`（结果门）**：`n^s = 3, n^f = 1` ⇒ `R = 3/(3+1) = 0.75 > τ_out = 0.5` ⇒ 通过。三道门全 1 ⇒ 复用 `a_3`，**fallback 调用 0 次**。
4. **反事实**：如果 `m_3` 也不存在，则 `∀ m ∈ C_t^1, Φ = 0` ⇒ 调用 `f(s_t)`，付 `0.922 s / 9.288 J`。也就是说，本步的"省钱"完全来自第 1、2 步那两次近乎免费的规则查询。

**这一算例的核心结论**：MemoGuard 的收益不是"更聪明的检索"，而是"把 0.93 分的陷阱挡在门外，让 0.88 分的合法记忆胜出"——**排序与授权必须解耦**。

## 4 · 工程视角

| 项目 | 论文报告值 |
|---|---|
| 硬件平台 | NVIDIA Jetson AGX Xavier，`MODE_30W_ALL` |
| fallback 模型 | 本地 `llama3.2:3b`（constrained to a single supervisory action） |
| 单次 fallback 延迟 | `0.922 s` per call |
| 单次 fallback 能耗 | `9.288 J` per call |
| fallback 调用降幅 | `3.98` calls（`18.58 → 14.60`）/ trial |
| 每 trial 避免的兜底开销 | `3.67 s` 与 `36.97 J` |
| 记忆库规模 | `11,558` 条；评测时固定 seed 采样至多 `2,000` 条 |
| episode 长度上限 | `50` steps |
| 校验三道门自身延迟 | **论文未报告** |
| 内存 / VRAM 占用 | **论文未报告** |
| 控制频率 / FPS / 端到端吞吐 | **论文未报告** |
| 动作集规模 | `6`（`follow_planner, inspect_target, return_to_safe_waypoint, inspect_alternate_viewpoint, wait_for_recovery, abort_mission`） |

**Trade-off 分析**：

- **成本结构不对称是全部收益的来源**。一次 fallback ≈ `0.922 s / 9.288 J`；而三道门是三条标量比较（`b_t − C_act ≥ B_safe`、`R > τ_out`、图上一次邻接查询），量级上可忽略。因此"多加校验"的最坏情况只是多几次比较，最好情况是省掉一次 3B 模型前向。**只要 $\text{cost}(校验) \ll \text{cost}(推理)$ 这个不等式成立，这个架构就是免费的午餐。**
- **但兜底是"昂贵上界"，不是"便宜上界"**。`MODE_30W_ALL` 下 0.922 s/call 意味着：若某场景候选全被拒，50 步 episode 最多可累积 50 次调用（≈46 s 纯推理）——**这正是文中 Reduced Battery 场景压力最大的原因**。部署时必须先算清"最坏情况下 fallback 占比"。
- **`k=1` 是原型选择，不是方法约束**。论文脚注明确"evaluated prototype uses the lightweight `k=1` instantiation"；框架本身是 top-k + 顺序检查下一个候选。`k` 增大 ⇒ 陷阱命中率上升（更容易找到一条合法记忆）但校验次数线性增长——这是一个未被实验扫描的超参。
- **`τ_out`、`B_safe`、`λ_env/λ_agent` 三个阈值**：`B_safe=25` 与 `λ_env=0.8` 有明确取值，但 `τ_out` 的具体数值**论文未报告**。这在复现时是硬阻塞项（见 §8）。
- **记忆库 11,558 条 + 每步采样 2,000 条排序**：说明检索是 O(候选数) 的暴力打分，而非 ANN 索引。真机上若要扩到 10^5 量级需换索引结构——**论文未报告检索耗时**，无法判断这个瓶颈的现实代价。

## 5 · 数据与评测

**数据来源**：无公开数据集。自建 **graph-based corridor-inspection simulator**（地面机器人，初始可用的拓扑地图）。图 `G_t = (V_t, E_t)`，节点编码局部可见性（base / corridor / target / safe waypoint / alternate viewpoint），边编码 traversal cost 与 obstacle state。三种地图族：

- **Linear Corridor**
- **Alternate Path**
- **Long Return Cost**

情景随机化：边代价、障碍状态、可见性等级、目标位置、备选视角可用性、初始电量、定位置信度。`B_safe = 25`，max episode length `50 steps`。移动用 **Dijkstra** 求最小代价路径。

**记忆库构建**：离线从 rollout 数据；成功转移存为 episodic action memory 并累加 `n^s`，失败 rollout 在匹配已有签名时贡献 `n^f`，共 **11,558** 条。评测时 retriever 用固定 seed 采样至多 **2,000** 条并按 §2 第 7 式排序。

**Trap 生成**（每条 trap 场景相对一个非 trap 场景施加**唯一一种**受控修改，且修改后仍可解，以保证失败归因于无效复用而非不可能任务）：

| Trap 类型 | 修改 | 关键参数 |
|---|---|---|
| Blocked Edges | 一条或多条原本可通行的边改为 blocked | — |
| Reduced Battery | 初始电量下调 | **15%**（受最小可行电量约束） |
| Removed Alternate Viewpoint | 移除备选视角，降级为无 alternate-inspection 能力的普通节点 | — |

**四个 baseline**：`Top-1 Reuse`（直接执行最高分记忆）、`Threshold Reuse`（加相似度阈值，低于则兜底）、`Always Reasoning`（每步都调本地推理兜底）、`MemoGuard`。

**六个指标**：`Mission Success`（检视目标 ∧ 守住电量安全下限 ∧ 在 recovery 节点终止）、`Target Inspected`（不论最终是否 recovery）、`Battery Depletion`（电量归零）、`Battery Safety Violation`（终止时低于安全下限）、`Fallback Calls`（每 trial 平均兜底调用次数）、`Execution Cost`（移动 / 检视 / 等待 / 兜底开销累积的 battery-equivalent cost）。

**Table I 全文数值（trap 场景平均，逐字照录）**：

| Policy | Mission ↑ | Inspect ↑ | Deplete ↓ | Safety Viol. ↓ | Fallback ↓ | Cost ↓ |
|---|---|---|---|---|---|---|
| Top-1 Reuse | 32.6 | 80.4 | 18.9 | 67.4 | 0.00 | 36.73 |
| Threshold Reuse | 32.7 | 76.6 | 18.9 | 67.1 | 0.53 | 37.09 |
| Always Reasoning | 83.5 | 98.6 | 2.2 | 16.5 | 18.58 | 63.03 |
| **MemoGuard** | **84.2** | **98.2** | **2.0** | **15.8** | **14.60** | **60.21** |

**按 trap 类型分解（Fig. 3 正文数值）**：

| Trap 类型 | Top-1 Reuse Safety Viol. | MemoGuard Safety Viol. | Always Reasoning Safety Viol. | MemoGuard Fallback | Always Reasoning Fallback |
|---|---|---|---|---|---|
| Blocked Edges | 44.3% | 13.0% | 15.0% | 13.51 | 17.47 |
| Removed Alternate Viewpoint | 71.2% | 14.4% | 16.5% | 15.37 | 18.28 |
| Reduced Battery | 86.8% | 20.1% | 17.9% | 14.94 | 19.99 |

**关键结论（论文原话方向）**：相对 Top-1 Reuse，Mission Success `32.6% → 84.2%`；Safety Violation `67.4% → 15.8%`，即 **76.6% 相对降幅**。相对 Always Reasoning，fallback 调用 `18.58 → 14.60`，即 **21.4% 相对降幅**，而 mission success 保持可比（`84.2%` vs `83.5%`）。**Threshold Reuse 与 Top-1 Reuse 几乎同分（67.1% vs 67.4%）是全文最有说服力的一格**：它证明这些 trap 不是"低置信度检索失败"，而是高分但前提失效。

## 6 · 能力与失败模式

**能做（有实验支撑）**：

- 在**离散拓扑变化**（blocked edges / removed alternate viewpoint）下几乎追平甚至略优于 Always Reasoning 的安全性，同时省 20%+ 的兜底调用（Blocked Edges: 13.0% vs 15.0%，fallback 13.51 vs 17.47）。
- 把"安全性"从检索器的黑箱置信度，变成**可逐项审计的布尔门**——任何一次拒绝都能归因到"拓扑/资源/结果"其中一门。
- 在 50 步 episode、11,558 条记忆库的规模上稳定运行。

**不能做 / 弱项**：

- **资源余量类陷阱最弱**：Reduced Battery 下 MemoGuard `20.1%` **高于** Always Reasoning 的 `17.9%`。论文自陈"resource-margin traps remain more sensitive to cost estimation"——即 `C_act` 估计不准时，资源门会放行实际会击穿安全下限的动作。
- **只能从 6 个监督动作里选**，没有连续控制 / 低层轨迹；"推理不是本身可执行的动作"是硬约束。
- **不处理感知**：节点、边、可见性、障碍状态都由仿真器直接给定（ontology 里 `sensor: n/a`）。真实机器人上的"边被堵了"需要一整条感知 + 地图更新管线才能喂进 `Φ_topo`。
- **定位不确定度未进入校验**：虽然检索键 `x_i` 里有 localization confidence，未来工作才把"localization uncertainty、communication quality、energy trajectories"升级为 cross-layer contract。
- **`k=1` 时无法降级到次优候选**；若唯一候选是陷阱，直接付兜底。

### 隐含假设 (Hidden Assumptions)

| # | 假设 | 若不成立的后果 |
|---|---|---|
| H1 | **环境拓扑 `G_t=(V_t,E_t)` 的当前状态（边是否 blocked、视角是否存在）是已知且即时的** | `Φ_topo` 会对着过时地图返回 1，拓扑门形同虚设——仿真里这是"外部施加的 ground truth"，真机上是最大漏洞 |
| H2 | **`C_act(s_t, m_i)` 是可准确估计的动作代价** | Reduced Battery 已显示弱点（20.1% vs 17.9%）；真机的电量模型含坡度、负载、温度，误差会放大 |
| H3 | **`R(m_i)=n^s/(n^s+n^f)` 在少量样本下仍可信** | `n^s=1, n^f=0` ⇒ `R=1.0`，任何 `τ_out<1` 都放行。论文未给 `τ_out`、未设最小样本数门槛 ⇒ 冷启动记忆可零成本通过结果门 |
| H4 | **"等价 state-action 记忆"的签名（signature）聚类是正确的** | 计数被摊薄或串味：不同情境共享同一签名 ⇒ `R` 失真 |
| H5 | **兜底 LLM 在被约束为"从 `A` 选 1 个"时是安全策略** | 实验里 Always Reasoning 自身 Safety Viol. 就有 16.5%，说明兜底不是零风险上界；MemoGuard 的"安全天花板"因此只有 ~16.5% |
| H6 | **记忆库离线构建的分布覆盖在线场景** | 若 trap 类型超出 Blocked/Battery/Viewpoint 三类，`κ_i` 里可能根本没有对应前置条件可校验 |

## 7 · 与相关工作对比

| 维度 | Top-1 Reuse (相似度复用) | Threshold Reuse | Always Reasoning (本地 LLM 兜底) | **MemoGuard** |
|---|---|---|---|---|
| 授权依据 | 检索分数最高 | 分数 > 阈值 | 每步推理 | **执行契约三道硬门（合取）** |
| 是否可解释拒绝原因 | 否 | 部分（"分低"） | 否 | **是（拓扑/资源/结果可逐项归因）** |
| Fallback Calls / trial | 0.00 | 0.53 | 18.58 | **14.60** |
| Safety Violation | 67.4% | 67.1% | 16.5% | **15.8%** |
| Mission Success | 32.6% | 32.7% | 83.5% | **84.2%** |
| Execution Cost | 36.73 | 37.09 | 63.03 | **60.21** |
| 主要失效 | 高相似度陷阱直接执行 | 陷阱分数并不低，阈值拦不住 | 开销/能耗不可承受 | 资源余量类陷阱、`C_act` 误差、拓扑状态过时 |

**与方法谱系的关系**：论文把自身定位在 case-based / episodic memory 复用（引用 [5,6]）与 LLM 高层规划（引用 [9–12]）的交叉点上——前者提供"便宜的记忆",后者提供"安全但贵的推理",MemoGuard 是**两者之间的调度器**。与"检索增强"路线的本质区别：RAG 类方法优化的是"取回什么"，MemoGuard 优化的是"取回后敢不敢用"。

**面试 Tip**：被问到"这和普通 RAG / 记忆复用有什么区别"时，标准答法是——**"RAG 的失败模式是取错；记忆复用的失败模式是取对了但不能用。"** 紧接着补一句量化：*Threshold Reuse 的 Safety Violation 是 67.1%，和 Top-1 的 67.4% 几乎一样，这直接证明这些陷阱不是低置信度检索失败，加阈值没用，必须校验执行前提*——这一格数据是整个论证的支点，比任何定性描述都硬。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-25)

**Repo 状态说明**：论文摘要文本中出现字符串 `https://github.com/hetheiin/memoguard`（"We open-source MemoGuard at ..."）。但按本知识库的判定口径，**纯文本 URL 不构成 repo signal**——本次解析无法确认它在 arXiv PDF 中是活跃可点击超链接，也**无法访问或核实任何 issue / commit 流**。因此本节**不写任何 issue 编号、标题、日期或引文**（不做无源引用）。以下 pitfall 全部由 §6 失败模式 + §3 方法约束**推导**，标注为 *(未经 issue 验证)*。

| # | Pitfall | 由哪条失败模式推导 | 由哪条方法约束触发 | 现场症状 |
|---|---|---|---|---|
| P1 | **冷启动记忆零成本通过结果门** | H3 / §6「结果门对少量样本不可信」 | 第 9 式 `R = n^s/(n^s+n^f)`，且论文**未报告 `τ_out` 数值、未设最小样本数** | 新记忆 `n^s=1, n^f=0` ⇒ `R=1.0` ⇒ 只要 `τ_out<1` 必过。上线初期大量"成功过一次"的记忆被无条件放行，Safety Violation 反弹。**必须自己补一个 `n^s+n^f ≥ N_min` 门。** *(未经 issue 验证)* |
| P2 | **改 `B_safe` 后复现不出 15.8%** | §6「Reduced Battery 是弱点，`C_act` 误差敏感」+ Table I 只在 `B_safe=25` 下测得 | 第 8 式 `b_t − C_act ≥ B_safe` 是硬不等式；`B_safe` 与电量归一化尺度强耦合 | 若把电量尺度换成百分比（0–100）而 `B_safe` 仍填 25，或反之，资源门会变成恒真或恒假。复现脚本必须先对齐电量单位与 `C_act` 的代价口径（battery-equivalent cost）。*(未经 issue 验证)* |
| P3 | **`Φ_topo` 在真机/自定义地图上恒为 1** | §6「不处理感知，拓扑由仿真器直接给定」+ H1 | 第 10 式只查"`κ` 要求的结构是否仍成立"，结构状态来自 `G_t`，而 MemoGuard 本身**没有地图更新接口** | 需要外部每步刷新 `E_t.blocked` 与 `v_alt.available`；若沿用离线记忆库构建时的静态图，则拓扑门永不触发，"Blocked Edges 下 13.0% vs 15.0%" 的收益完全消失。*(未经 issue 验证)* |
| P4 | **`k=1` 是写死的原型，top-k 路径未评测** | §6「`k=1` 时无法降级到次优候选」 | 论文脚注 1 明确 "Our evaluated prototype uses the lightweight `k=1` instantiation"，第 3 式是 TopK 但实验未扫 `k` | 期望"多取几个候选就能多省 fallback"的工程假设没有实验背书；改 `k>1` 需自己承担校验次数与 `S_ret` 阈值标定的连锁变化。*(未经 issue 验证)* |
| P5 | **`llama3.2:3b` 兜底在非 AGX Xavier 板上不可部署** | §6 H5「兜底本身有 16.5% 违规率」+ §4 全部能耗数字绑死在单一 SKU | fallback `f(s_t)` 被实例化为本地 3B 推理 | 论文只给 `MODE_30W_ALL` 下 `0.922 s / 9.288 J`，**未报告 VRAM**；换到显存更小的板子需重标定，`3.67 s / 36.97 J` 的收益换算随之失效。*(未经 issue 验证)* |

---

[← Back to navigation README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文（v1，截断版）· 未在真机复现的数字标 `UNVERIFIED`；§4 中标注「论文未报告」的条目为全文确实缺失项，未做估算填充

[//]: # "<!-- source: https://arxiv.org/abs/2607.15589 -->"
