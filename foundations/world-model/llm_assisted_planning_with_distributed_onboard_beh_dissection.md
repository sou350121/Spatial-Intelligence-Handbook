[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# LLM 辅助规划与分布式星载行为树执行的多 AUV 任务框架 (LLM-Assisted Planning with Distributed Onboard Behaviour Tree Execution for Multi-AUV Missions)

> **发布时间**：2026-11-03（arXiv v1，已被 IFAC 接收）
> **论文 / 模型名**：LLM-Assisted Planning + Distributed Onboard BT（无单独模型名）
> **核心定位**：把自然语言 (NL) 任务指令用 LLM 解析成 MILP 约束、再由每艇行为树确定性执行的多 AUV 分层框架——它要解决的是「通信受限水下场景里，如何既让操作员用大白话下任务、又保证每艘艇的机上执行绝对可验证」这一痛点。

水声通信带宽低、间歇断连，多 AUV 协同往往卡在「任务怎么下发 + 断了怎么自愈」上。本文不给 LLM 任何控制权：LLM 只把操作员意图翻译成 MILP 的等式约束，一切安全关键决策交给 Gurobi 和每艇的 Behaviour Tree (BT)；仿真里小/中两档任务在软/硬/混合故障下 TCR 均达 100%。

---

## X-Ray 开场

多 AUV 任务通常要用结构化任务文件（航点、任务矩阵）下发，操作员门槛高、通信一断就没法改；而直接把 LLM 塞进机上控制又会因为幻觉、延迟、不可验证而在安全关键的水下作业里不可接受。本文的做法是把职责硬切两半：**topside（母船侧）只做"语义推理 + 全局分配"，seaside（艇上）只做"确定性 BT 执行"**——LLM 的输出永远是 MILP 约束，而不是直接动作。对 spatial AI 研究者而言，这提供了一条「用形式化验证器兜住 LLM」的分层范式：LLM 只在可验证的中间表示（MILP / 任务队列）上工作，机上永远跑确定性、可解释的行为树。

---

## 📍 研究全景时间线

```
2018  Colledanchise & Ögren: BT 形式语义 / Sprague et al.: BT 用于 AUV
  │
2022  Code-as-Policies (Liang): LLM → 可执行代码
  │
2024  BTGenBot (Izzo): 轻量 LLM 生成单机器人 BT；Groot 可视化 BT
  │
2025  SPINE / AI Captain / LLM-as-BT-Planner
      Merino-Fidalgo: LLM + BT + Failure Interpreter（单机器人）
      Li et al.: 水下多机 failure-aware 协同（无 NL 接口）
  │
2026  ★ 本文：LLM 只产 MILP 约束 + 分布式 BT 执行 + 选择性重规划（多 AUV）
  │
局限  ▸ 全仿真，无真机；通信延迟抽象为 Redis 直连
      ▸ 任务集静态、单传感器失效模型、无海流/定位漂移
      ▸ LLM 只抽取「分配 + 排序」两类约束，表达力受限
```

本文的坐标：它是把 2022–2025「LLM×BT」这条单机器人线，首次推到多 AUV + 通信受限 + 分布式故障自愈的场景，并用 MILP 把 LLM 隔离在安全的中间层。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| **Supervisor**（LangGraph agent） | 操作员 NL 指令 | 转发给 Planner，最终向操作员请求审批 | 纯推理，无训练 |
| **Planner**（LLM agent） | NL 指令 + 任务/机器人/传感器标识 | 结构化 MILP 约束（assignment / routing JSON） | 纯推理；用 Qwen-3-8B / Llama-3.1-8B，Ollama 本地部署 |
| **MILP Optimizer**（Gurobi） | 约束 + 任务参数（能力、时间） | 能力感知、时间一致的任务分配 | 精确求解，无学习 |
| **RA**（每艇一个，RAs Layer） | 已批准计划、Redis 故障消息 | BT 执行上下文、REQUEST_ASSISTANCE | 纯规则推理，无训练 |
| **BT–LLM Bridge** | RA 发来的任务序列 | 入队 BT Mission Manager、回传完成/故障/遥测 | 轻量翻译层，无学习 |
| **BT Mission Manager**（每艇，Groot 建树） | 任务队列 | 导航/测绘子树执行、SUCCESS/FAILURE/RUNNING 状态 | 确定性 tick 传播，无学习 |

关键点：**没有任何模块在"训练"**——LLM 模型是现成 open-weight 模型，整套框架是推理期编排。

### 1.2 关键机制

**⚡ Eureka Moment**：LLM 永远不碰行为树本身——它只写 MILP 约束，所以任何 LLM 幻觉都会在"可行性检查"这一关被打回，绝不会变成机上一个不安全动作。

这个设计把 LLM 的不可靠性**隔离**在一个有形式化语义的中间表示（MILP）里：
- LLM 输出错了 → MILP 约束写错 → 要么被标识校验挡住（task/robot/sensor 不存在），要么解出一个"合法但不符合意图"的分配（CSR 下降反映这一点）。
- 反例路线（BTGenBot / LLM-as-BT-Planner）是让 LLM 直接生成 BT 结构，语义难以验证。
- 本文路线：LLM 只做高层语义 → MILP 校验 → BT 执行，把「LLM 可靠性」问题降级为「约束抽取准确率」问题（可量化、可评测，见 §5）。

### 1.3 信息流架构图

```
 操作员 NL 指令
      │
      ▼
┌─────────────────────────────────────────────┐
│  SUPERVISION LAYER (topside)                 │
│                                              │
│  Supervisor ──► Planner (LLM)                │
│      ▲            │ 提取 assignment/routing  │
│      │            ▼                          │
│      │      ┌──────────────┐                 │
│      └──────│ MILP Optimizer│ (Gurobi)       │
│  审批/重规划  └──────────────┘                 │
└───────────────────┬─────────────────────────┘
                    │ 分配方案 + 任务上下文
                    ▼
        ┌───────────────────────┐
        │   BT–LLM Bridge        │  (topside↔seaside 翻译)
        └───────────┬───────────┘
                    │ 任务队列（有序）
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
  ┌──────┐      ┌──────┐       ┌──────┐
  │ RA1  │      │ RA2  │  ...  │ RAn  │  (RAs Layer)
  └──┬───┘      └──┬───┘       └──┬───┘
     │ 故障消息 ▲   │               │
     ▼          │   ▼               ▼
  ┌──────┐   ┌──────┐           ┌──────┐
  │ BT MM│   │ BT MM│           │ BT MM│  (Execution Layer, 每艇)
  └──────┘   └──────┘           └──────┘
   导航子树 / 测绘子树，确定性 tick

  ● Redis 消息层贯穿全栈
  ● RAs 之间不直接通信；所有多机决策集中在 Supervision Layer
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$
\min\; C_{\max} + \lambda \sum_{r\in R}\sum_{i,j\in V} d_{i,j}\, y_{r,i,j}
\quad\text{s.t. 能力约束 + 流守恒 + 时间一致性}
$$

一句话直觉：**"让最慢那艘艇尽量早收工（makespan），同时别让总航程太离谱（加权惩罚项）"**。

### 2.1 目标函数

$$\min\; C_{\max} + \lambda \sum_{r\in R}\sum_{i,j\in V} d_{i,j}\, y_{r,i,j}$$

- **第一项 $C_{\max}$**：makespan，整支编队完成所有任务的时间，直接决定任务效率。
- **第二项 $\lambda\sum d_{i,j} y_{r,i,j}$**：总航程的加权惩罚，$\lambda$ 是平衡权重。光最小化 makespan 可能让某艇绕远路去"拉平"总时长，加这一项抑制无意义的航程。

### 2.2 决策变量

| 变量 | 域 | 含义 |
|---|---|---|
| $x_{r,t}$ | $\{0,1\}$ | 机器人 $r$ 是否被分配任务 $t$（robot–task assignment） |
| $y_{r,i,j}$ | $\{0,1\}$ | 机器人 $r$ 是否从节点 $i$ 路由到节点 $j$ |
| $A_{r,i}$ | $\geq 0$ | 机器人 $r$ 到达节点 $i$ 的时间 |
| $D_{r,i}$ | $\geq 0$ | 机器人 $r$ 离开节点 $i$ 的时间 |

### 2.3 约束

- **能力约束**：$x_{r,t}$ 只在 $r$ 具备 $t$ 所需传感器时为 1（异构 sonar/optical/sidescan）。
- **流守恒**：在节点集 $V$ 上每艇形成合法路径。
- **时间一致性**：$A_{r,i}, D_{r,i}$ 由航程与执行时间串联，构成时序可行解。

### 2.4 NL 约束如何注入

LLM 抽出的每条约束变成对 $x_{r,t}$ 或 $y_{r,i,j}$ 的**等式约束**：

- `"allocate TASK_2 to AUVs3"` → $x_{\text{AUVs3},\text{TASK\_2}} = 1$
- `"execute TASK_13 then TASK_4 with AUVs1"` → $y_{\text{AUVs1},\text{TASK\_13},\text{TASK\_4}} = 1$

这就是本文把「自然语言」桥接到「形式化优化」的全部接口——**只有分配和排序两类约束**（这一表达力限制在 §6 隐含假设里展开）。

---

## 3 · 带数字走一遍（玩具例子，非论文数据）

设 2 艇（R1、R2）、3 个航点任务（T1、T2、T3），单位化距离 $d$：

```
       T1 ----10---- T2 ----10---- T3
        \                          /
         \-------- 20 ------------/
  R1 起点在 T1 附近；R2 起点在 T3 附近
```

**不加 NL 约束时的近似最优分配**（makespan 主导，$\lambda$ 小）：

| 艇 | 分配 | 路径 | 航程 |
|---|---|---|---|
| R1 | T1 | T1（10 单位航程从起点）| 10 |
| R2 | T2, T3 | 起点→T3→T2（10+10）| 20 |

$C_{\max} = 20$，总航程 $= 30$。

**现在操作员说**：`"Allocate TASK_2 to AUVs1; execute TASK_1 then TASK_2 with AUVs1"`

这变成两条约束：$x_{R1,T2}=1$，$y_{R1,T1,T2}=1$。强约束下解变为：

| 艇 | 分配 | 路径 | 航程 |
|---|---|---|---|
| R1 | T1, T2 | 起点→T1→T2（10+10）| 20 |
| R2 | T3 | 起点→T3（10）| 10 |

$C_{\max} = 20$，总航程 $= 30$。**makespan 没变，但约束被满足**——这说明两个要点：

1. **不是所有 NL 约束都会拉长 makespan**；若操作员约束导致 makespan 上升，涨多少由 $C_{\max}$ 项如实反映。
2. **CSR（约束满足率）**：这里 $y_{R1,T1,T2}=1$ 在解里被满足 → CSR=100%。若操作员写了 `"T1 必须在 T3 之后由 R1 完成"` 而 T1 早于 T3 在同一路径上不可行，MILP 会因该等式与时间一致性冲突而**不可行**——这就是论文里 CSR&lt;100% 的来源（"CSR&lt;100% occurs when user specified infeasible constraints"）。

> 以上数字为演示设定，非论文数据。

---

## 4 · 工程视角

| 维度 | 数值 / 结论 | 来源 |
|---|---|---|
| **恢复时间（小任务，均值）** | 8.2 s；分场景 Soft 11.3 s / Hard 1.8 s / Mixed 11.5 s | 论文原文 |
| **恢复时间（中任务，均值）** | 13.4 s；分场景 Soft 12.5 s / Hard 12.4 s / Mixed 15.1 s | 论文原文 |
| **每故障协调消息数** | 典型 3 条（1 故障通知 + 1 重规划请求 + 1 新分配） | 论文原文 |
| **AUV 巡航速度** | 1–2 m/s | 论文原文 |
| **仿真时间倍率** | 固定 30× | 论文原文 |
| **LLM 推理延迟** | **论文未报告** | — |
| **硬件型号 / GPU / VRAM** | **论文未报告**（仅称 "commodity hardware"） | — |
| **FPS / 吞吐** | **论文未报告** | — |
| **MILP 求解时间** | **论文未报告**（仅以含 MILP 的恢复时间间接体现） | — |

**关键 trade-off 解读**：

- 恢复时间「随任务规模而非故障类型变化」（8.2 s → 13.4 s 随小→中任务上升），说明**瓶颈是重规划+重分发，而非故障检测**。这符合直觉：MILP 规模随机器人/任务数增长，Gurobi 求解代价主导。
- 3 条消息的通信开销是这套架构的核心卖点——RAs 之间不互通，故障处理本地化，水声带宽友好。
- **但**：论文明确说「真实部署中 RA→Supervisor 的 REQUEST_ASSISTANCE 需要艇体上浮建立通信链路，仿真里抽象为直接 Redis 消息」。所以 8.2 s / 13.4 s 的恢复时间**不含上浮与声学建链时间**——真机上这项可能远大于 8 秒，这会成为端到端恢复时间的真正主导项（见 §8）。

---

## 5 · 数据与评测

**仿真环境与实现栈**：

- ROS-based AUV simulator，Zeno AUV 动力学（Gelli et al., 2018）；速度 1–2 m/s；异构传感（sonar / optical / sidescan）。
- 软件栈：LangGraph（agent 编排）、Redis（消息层）、Gurobi（MILP）、Ollama（LLM 本地部署）、Groot（BT 建树）。
- 任务类型：waypoint navigation、lawn-mower survey、spiral survey。
- 故障注入：向对应 RA 发 `FAILURE_EVENT`，固定仿真时间倍率 30，保证故障发生时艇在执行/待执行。
- **明确省略**：海流、声学噪声、定位漂移（"environmental disturbances such as currents, acoustic noise, and localization drift were omitted"）。

**任务规模**：small（2 机器人，8 任务）、medium（3 机器人，12 任务）、large（5 机器人，20 任务）。

> ⚠️ 注意：large 档在 §5 中被定义，但 §4.2 的恢复时间与 Fig. 4 只报告了 small 和 medium 两档。写报告时不要假设 large 有恢复时间数据。

**H1 — NL 约束抽取**：27 个测试用例（12 simple，15 complex），覆盖单约束、否定、多约束组合。

| Model | Complexity | Precision | Recall | F1 | CSR |
|---|---|---|---|---|---|
| Llama-3.1-8B | Simple | 83.3 | 83.3 | 83.3 | 41.7 |
| Llama-3.1-8B | Complex | 67.2 | 70.0 | 67.4 | 81.7 |
| Llama-3.1-8B | Overall | 74.4 | 75.9 | 74.5 | 63.9 |
| Qwen-3-8B | Simple | 94.4 | 100.0 | 95.8 | 49.4 |
| Qwen-3-8B | Complex | 96.6 | 96.6 | 96.6 | 92.8 |
| Qwen-3-8B | Overall | 95.6 | 98.1 | 96.2 | 73.5 |

- Qwen-3-8B 在 simple/complex/overall 三档的 Precision/Recall/F1 全面高于 Llama-3.1-8B。
- **CSR 反直觉现象**：simple 档 CSR 只有 41.7%（Llama）/ 49.4%（Qwen），反而低于 complex 档。论文解释：**CSR&lt;100% 出现在用户写了不可行约束时**——简单场景更容易被设计成"指令与任务表不兼容"，从而 MILP 不可行。仅统计可行场景时，两模型 CSR 都达 100%。

**H2 — 故障处理**：四种 profile（Nominal / Soft / Hard / Mixed），全部故障 profile × 全部任务规模下 **TCR = 100%**。

- 论文未给 makespan / 总航程的绝对数值，只在 Fig. 4 以图展示 soft/hard/mixed 下的增量（均值为趋势图），文中未列具体数字 → 绝对数值 **论文未报告**。
- 通信开销：每故障典型 3 条消息（"typically three"），论文未与集中式 baseline 做定量对比，只做绝对计数刻画。

---

## 6 · 能力与失败模式

**能做（论文验证过的）**：

- 从 free-form NL 指令抽取 assignment / routing 两类约束，Qwen-3-8B overall F1 = 96.2。
- 异构能力 + 时间约束下的 MILP 任务分配（Gurobi 求解）。
- 软故障（传感器缺失）下**选择性重规划**：只把受影响任务标 pending，其余任务继续执行。
- 硬故障（艇不可用）下返航 + 集中式重分配，TCR 保持 100%。
- 通信受限下机上 BT 持续执行（不依赖持续连母船）。

**不能做 / 失败模式（具体）**：

1. **NL 约束不可行 → MILP 直接无解**：CSR&lt;100% 的唯一定义就是用户给了不可行约束。此时框架不会自动"软化"约束，而是返回不可行——依赖操作员看到 CSR 后改指令。
2. **LLM 误抽取 → 合法但错误的分配**：Qwen 在 simple 档 Recall 100% 但 Precision 94.4%，说明存在误报约束；Llama complex 档 Precision 67.2 说明复杂指令下会抽出多余/错误约束。这类错误**不会让 MILP 不可行**（约束本身合法），而是导致"按错的约束求解"，属于语义级静默失败，比 infeasible 更危险。
3. **软故障当前任务判定边界**：RA 规则是「当前任务若不需要 $s_{\text{lost}}$，则继续」，然后「$\mathcal{T}_{\text{aff}}$ 中的任务标 pending」。如果**当前正在执行的任务恰好需要缺失传感器**，论文未明说该任务是否立即中止——它落入 $\mathcal{T}_{\text{aff}}$ 被报给 Supervisor 重分配，但从触发到重分配之间有窗口期。
4. **硬故障中途返航 → 航程与 makespan 上升**：论文只说 Fig. 4 显示上升趋势，未量化。
5. **表达力天花板**：只支持 assignment / routing 两类约束，无法表达条件逻辑（"若能见度差则改做 B"）、时序窗口、资源互斥等更丰富语义。

### 隐含假设 (Hidden Assumptions)

- **任务语义可约化为「分配 + 排序」图**：所有 NL 意图都能落成 $x_{r,t}$ / $y_{r,i,j}$ 等式。这是架构能工作的前提，也是表达力上限的根源。
- **通信抽象为 Redis 直连**：仿真里 RA→Supervisor 是直接消息，**不含声学建链、上浮时间、丢包、延迟**（论文明确承认此抽象）。真实水下这条路径可能主导端到端恢复时间。
- **静态任务集**：任务在执行前已确定，无中途任务发现/生成。
- **单传感器失效模型**：软故障被建模为「丢失单个传感器 $s_{\text{lost}}$」，且每任务有确定的传感器需求 $S(t)$；多重同时失效、间歇性失效未覆盖。
- **无环境扰动**：海流、声学噪声、定位漂移显式省略 → 假设定位与状态估计完美。
- **RAs 无分布式共识**：所有多机决策集中在 Supervision Layer，RAs 之间零直接通信。这意味着**母船侧是单点**——若 topside 宕机，故障期间无法重规划（机组只能按原计划跑到完）。
- **LLM 输出 JSON 可解析**：Ollama 部署的 open-weight 模型能稳定产出结构化 JSON；解析失败路径未在评估中讨论。
- **降解模式安全**：把受影响任务标 pending、在可行任务上"运行 degraded mode"被默认是安全的——没有对"传感器缺失下继续执行"的独立安全论证。

---

## 7 · 与相关工作对比

| 工作 | LLM 角色 | 执行层 | 多机器人 | 通信受限 | 故障自愈 |
|---|---|---|---|---|---|
| Code-as-Policies (2022) | LLM → 可执行代码 | 代码执行 | ✗ | ✗ | ✗ |
| BTGenBot (2024) | LLM **直接生成 BT** | BT（单机） | ✗ | 假设可靠 | ✗ |
| LLM-as-BT-Planner (2025) | LLM 生成 BT（prompt 工程） | BT（单机） | ✗ | 假设可靠 | ✗ |
| Merino-Fidalgo (2025) | LLM + Failure Interpreter | BT（单机） | ✗ | 假设可靠 | 部分 |
| Li et al. (2025) | 无 | 集中/分散策略切换 | ✓ | ✓ | failure-aware |
| AI Captain (2025) | LLM chain-of-thought | 船舶导航 | ✗ | — | ✗ |
| **本文 (2026)** | LLM 只产 **MILP 约束** | **分布式 BT** | ✓ | ✓（抽象） | ✓ 选择性重规划 |

**核心差异化**：本文是唯一同时满足「NL 接口 + 多 AUV + 通信受限 + 分布式故障自愈」，且用 MILP 做 LLM 输出形式化验证的框架。对比 BTGenBot 路线，本文把 LLM 从「生成难验证的 BT 结构」退到「生成可验证的 MILP 约束」，牺牲了表达力换取了可验证性 + 可行性保证。

**🎤 面试 Tip**：若被问「为什么不让 LLM 直接生成行为树/动作」，标准答案三段式：
（1）LLM 生成的低层 BT 难以形式化验证，安全关键水下作业不可接受；
（2）本文把 LLM 限制在高层语义，输出 MILP 等式约束，由 Gurobi 做可行性/能力/时间三重校验，**任何"幻觉"在进执行层之前被 MILP 挡住**；
（3）机上 BT 保持完全确定性——LLM 永远不进入实时控制回路，这同时解决了幻觉和推理延迟两个问题。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-04)

**Repo 状态**：全文**未出现任何 github.com 链接**，无官方 repo / 无社区 issue 流可引用。以下 3 条 pitfall 由 §6 失败模式 + 方法约束**推导**，**未经 issue 验证**。

1. **LLM JSON 抽取失败会断掉整条 Planner→MILP 流水线**
   - 机制：§6 失败模式 #2（语义级静默错误）+ 约束「LLM 输出 JSON 由 Ollama 本地模型生成」（§3.1.1）。
   - 后果：Qwen simple 档 Precision 94.4（存在误报约束）+ Llama complex 档 Precision 67.2，说明误抽取在真实指令分布下必然发生。误抽取的约束**合法但错误**，MILP 照解，产出"对约束可行、对意图错误"的分配——这是最难排查的静默失败。建议在 MILP 前加一层「回显约束让操作员确认」的 UI（本文其实有 approval 步骤，但那仍是人审，需要把约束原文渲染给人看）。
   - 触发条件：复杂多约束组合指令、否定语义（如 "不要用 AUVs2"）。

2. **恢复时间"8.2 s / 13.4 s"是仿真数字，不含上浮与声学建链**
   - 机制：§6 隐含假设「通信抽象为 Redis 直连」+ §3.1.2 原文「真实部署中需上浮建立通信链路」。
   - 后果：真机端到端恢复时间 = Redis 消息时间 + MILP 求解 + **上浮时间 + 声学握手时间**。后两项在仿真中为零。如果照搬 8.2 s 去做任务预算或安全论证，会在真实水下严重低估恢复窗口。建议在真机上把「上浮+建链」作为独立预算项，并从 REQUEST_ASSISTANCE 时刻开始计时验证。

3. **硬故障时机若落在「最后任务执行中」，返航可能使已完成进度白白丢弃**
   - 机制：§6 失败模式 #4 + §3.1.2 硬故障规则「abort ongoing task → return-to-home」。
   - 后果：RA 收到 hard failure 后无条件 abort 当前任务、RTH。如果该任务已接近完成（如 lawn-mower 覆盖到 95%），abort 会把大部分完成的工作量丢给重分配，导致总航程与 makespan 显著上升（Fig. 4 已示趋势但未量化）。目前没有「进度接近完成则先完成再 RTH」的规则，属于可被故障时机触发的效率坑。建议 RA 增加「当前任务剩余工作量 vs 返航代价」的判定门限。

---
[← Back to navigation README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2611.04518 -->"
