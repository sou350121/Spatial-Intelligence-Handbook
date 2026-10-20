[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# 自结晶行为树：把基础模型推理摊销为确定性控制用于自主无人机 (Self-Crystallizing Behavior Trees: Amortizing Foundation-Model Reasoning into Deterministic Control for Autonomous Drones)

> **发布时间**：arXiv 2610.25455v1 [cs.RO]，18 Oct 2026
> **论文 / 模型名**：SCBT（Self-Crystallizing Behavior Trees）
> **核心定位**：把 foundation model 从"运行时控制环"降级为"编译期结构生成器"——只在行为树节点失败时提议一次最小子树补丁，验证后入库并固化成**无模型运行的确定性 BT**，从而在保住可检查性/确定性的同时拿到长尾适应能力。

经典 FSM/BT 确定性、可检查、快，但结构在设计期焊死，遇到设计者没想到的长尾就整体失败；LLM 驱动的方案能在运行时合成控制逻辑，却把延迟、成本、非确定性永远留在环里，且用完即弃。SCBT 的答案不是二选一，而是**排时序**：让 LLM 付一次学费。

---

## X-Ray 开场

SCBT 解决的是"设计期刚性"（design-time rigidity）：BT 无法执行一条从没被写过的分支。它的做法是把 foundation model 当**编译器而非运行时**——BT 的 `MissionCritical` 子树失败时，暂停仿真、构造 failure event、让 LLM 在受约束文法里生成**一个**最小局部补丁（patch），CMA-ES 调其连续参数，三阶段准入（静态检查 / 随机化 replay 上的不变量监视 / 相对现状的经验 margin）把关，入库；contextual bandit 学会"何时不必再问模型"；调用率衰减后**结晶（crystallize）**成一棵没人手写过的普通确定性 BT。

对 spatial AI 研究者意味着什么：这是一条**把"智能"从 tick 路径里搬出去**的工程范式——部署侧只剩 20 Hz 的 py_trees tick，控制逻辑是观测序列的纯函数（60/60 条离线 re-tick 与在线 trace 哈希完全一致）。同时它也诚实地给出一个负结果：admission 是**旋钮不是过滤器**，收紧安全会杀死泛化。

---

## 📍 研究全景时间线

```
1960s ──────── 2000s ────── 2014 ────────── 2022 ──────────── 2023 ────────── 2025 ─────────── 2026 ──────►
 FSM           BT 形式化    py_trees /      LLM 写机器人程序    Voyager        LLM 直接生成 BT      SCBT（本文）
 转移数随状态   (Chase /     BehaviorTree    Code as Policies   技能库 +        XML：BTGenBot /     ▲
 数平方增长     Colvin)      .CPP            SayCan / VoxPoser  embedding      LLM-BT              编译器范式
              模块化/反应性  确定性/可检查    VLA               检索复用        每次故障重新生成      + 摊销 + 结晶
              提升          但结构设计期固定  → 模型永远在环    → 不验证       → 不保留、不摊销      → 产物无模型
                                                                                                   │
                                                                        本文自陈局限：仅 2 类失败(F1/F7)、
                                                                        单机、单 seed 消融、headless 无感知、
                                                                        stage-2 绝对不变量规则过严（负结果）
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 学习期（System 2） | 冻结后（System 1） | 关键参数 |
|---|---|---|---|---|---|
| **确定性 BT**（py_trees） | 每 tick 遥测快照 | `Success/Failure/Running` | 被 tick，与仿真 lockstep | **唯一部署的部分**，20 Hz | 17 种 leaf 类型 |
| **`MissionCritical` decorator**（失败拦截） | 子树返回值 | 该 tick 返回 `Running` 并置 flag；暂停仿真构造 `e` | 启用 | 纯 pass-through | `P_max=3`, `F_max=2` |
| **Patch Manager** | failure event `e` | 候选臂集合 | 启用 | **不存在** | `ρ=0.80` |
| **Bandit**（线性 Thompson sampling） | `[φ(c), 1]` | 选 stored patch 或 `CallLLM` | 启用 | 换成 posterior-mean argmax | `κ=0.30` |
| **ADK proposer**：ContextAnalyst → PatchProposer | 渲染后的 `e` + 目标结构 + manifest + 文法 + ≤3 条最近库项 | 诊断 + **恰好一个** patch | 启用（episode 暂停） | 不存在 | Gemini 3.1 Pro, temp 0.2, `R=2` 修复轮 |
| **静态检查** | patch XML | admit / reject + 消息 | 启用 | 不存在 | 深度限制、占位符、锚点可解析 |
| **CMA-ES 调参** | `Θ_σ`（有界端口） | 调优后 `θ` | 启用 | `θ^{(m)}` 固定 | `B=4`（预算） |
| **Replay farm + 监视器**（stage 2/3） | patch + 当前树 | 准入判定 | 启用，4 实例并行 | 不存在 | `K=3`, `ρ_min=0.75`, `δ=0.25`, `p=0.20` |
| **Fleet library** | 准入 patch | 检索池 + 后验 | 启用 | 编译进树 | `φ` = MiniLM + one-hot + 归一化遥测 |
| **Crystallization** | 库中已准入 patch | `T*_m` | 触发一次 | 产物 | 调用率 `< ε` 且成功率 `≥ γ` |

### 1.2 关键机制

**⚡ Eureka Moment：把 foundation model 从"每个 tick 都可能被问"改成"只在结构失败时被编译一次、验证后保留、并用 bandit 学会不再问"——于是适应性是一次性资本开支，部署侧回到普通确定性 BT。**

四个机制各司其职，且**刻意不重叠**：

- **LLM 只做离散结构**（稀有、符号化、不可微）；
- **CMA-ES 只做连续参数**（有界端口，仿真里可反复重放）；
- **bandit 只做"值不值得问"**（把 `κ=0.30` 的调用成本写进 reward）；
- **准入只做"能不能留"**（静态 → 不变量 → 经验 margin）。

一句反直觉的设计约束：patch 必须**mission-agnostic**。属性值 `{@p}` 在应用时解析为锚点 leaf 的端口 `p`，`GoToRequiredGoal` 从黑板上读下一个未完成的必需目标——因为开发期出现过"含字面坐标的 patch 被复用到另一个 mission 上，飞到了错误地点"。

### 1.3 信息流

```
                      ┌──────────── System 1（唯一部署）────────────┐
 telemetry ──► py_trees BT (20 Hz, lockstep 50 ms/tick) ──► 飞行命令
                      │  MissionCritical decorator
                      │   child == Failure & patching on
                      ▼        → 返回 Running, 置 flag, 暂停仿真
        ┌──────────────── System 2（学习期，调用期间 episode 暂停）────────────────┐
        │  e = (v_f, c)   c = (s, b, m, τ, X)   ← s 由遥测生成（headless）        │
        │        │                                                              │
        │        ▼                                                              │
        │  Patch Manager: φ(c) → 余弦检索(仅 text + node-type 块, 排除 class)     │
        │        │                                                              │
        │        ▼                                                              │
        │  Bandit { retrieved patches } ∪ { CallLLM }                            │
        │        │                         │                                    │
        │        │ 选 stored              │ 选 CallLLM                          │
        │        │                         ▼                                    │
        │        │              ADK: ContextAnalyst → PatchProposer ──► π        │
        │        │                         │  (schema 不合法先被 Pydantic 拒)     │
        │        ▼                         ▼                                    │
        │  ┌──────────── Admission ────────────┐                                 │
        │  │ 1 静态: 文法/锚点/manifest/占位符   │                                 │
        │  │ 2 CMA-ES 调 θ → K=3 replays + 不变量│  ← 拒 → 记 rejection reason     │
        │  │ 3 经验: succ ≥ ρ_min 且 ≥ 现状+δ   │                                 │
        │  └───────────────┬───────────────────┘                                 │
        │                  ▼ admit                                               │
        │           Fleet library ℒ {XML, θ per class, posteriors, provenance}   │
        └──────────────────┬─────────────────────────────────────────────────────┘
                           ▼ 调用率 < ε 且成功率 ≥ γ
                    Crystallize ⇒ T*_m（无 LLM / 优化器 / bandit）
```

---

## 2 · 数学核心

📌 **Napkin Formula**：

```
max  Σ_t [ y_t − κ·u_t − λ·Δt_t/100 − μ·ΔE_t/10 ]      κ=0.30, λ=μ=0.10
s.t. 准入:  succ(T⊕π) ≥ ρ_min  且  succ(T⊕π) ≥ succ(T) + δ
```

一句话直觉：**"问一次模型"标价 0.30 个 mission success**，于是"什么时候不该问"变成了一个可学的经济问题，而不是一个调度策略。

### 2.1 学习期目标（式 1）

$$\sum_t\big(y_t-\kappa\,u_t-\lambda\,\Delta t_t/100-\mu\,\Delta E_t/10\big)$$

| 变量 | 含义 |
|---|---|
| `y_t` | 事件 `t` 之后的 mission success（必需目标权重 1、可选目标 0.5；必需目标未达成前的 abort 记 0） |
| `u_t` | 是否发起 LLM 调用（0/1） |
| `Δt_t` | 事件到 episode 结束的时间（秒），除 100 归一 |
| `ΔE_t` | 同段电量消耗（%），除 10 归一 |
| `κ, λ, μ` | 成本 / 时间 / 能量权重，取 `0.30 / 0.10 / 0.10` |

直觉：把"时间"和"电量"也放进 reward，是因为手写 abort 分支（return-to-launch）永远"安全"但常常零分——**奖励必须惩罚磨蹭**。

### 2.2 CMA-ES 的调参目标（式 2）

$$J(\theta)=\hat p_{\mathrm{succ}}-\lambda\,\bar t/100-\mu\,\bar E/10-\nu\,\mathbf 1[\text{unsafe}],\qquad \nu=1$$

- `θ`：patch 声明的有界数值端口（tunable），在单位盒内搜索，预算 `B=4`；
- `unsafe`：任一不变量违反，**或 landing reserve &lt; 10%**。

这条安全项是**被事故逼出来的**：没有它，CMA-ES 会拿 reserve 换成功率，产出一个"降落时只剩 9.8% 电量"的 patch；加上后变成 13.9% 起飞 / 12.5% 降落。

### 2.3 准入三阶段的形式条件

```
Stage 1  static :  o ∈ 𝒪, anchor 存在, leaves ∈ C_m 或可替换,
                   ports 存在/可解析/在界内, 占位符已声明且被使用,
                   锚点引用可解析, 深度限制,
                   ReplaceSubtree 必须有 rationale 且不得删除 MissionCritical
Stage 2  constraint : K=3 次 replay 上逐 tick 监视 geofence / altitude /
                      speed(class cap + margin) / inter-vehicle separation;
                      任一 tick 违反 或 landing reserve < 10% → reject
Stage 3  empirical  : p̂_succ ≥ ρ_min(=0.75)
                      且 p̂_succ ≥ p̂(current tree, 同扰动种子) + δ(=0.25) → admit
```

`𝒩(e)` 的定义是**事件邻域**：注入参数 ±`p=0.20`、触发时刻 ±2 s，并**裁剪到该失败类型的标定区间**——不裁剪的话，被扰动的电量会飘到 guard 之上，replay 根本不会失败。

### 2.4 摊销上界（作者只用来解释曲线，不作为定理使用）

在"上下文成簇 + 每次调用有正准入概率 `p`"的理想假设下，期望 LLM 调用数被 `Q|ℳ|/p` 加上 bandit 探索项界住。作者明确说明：写出它只是为了**说清经验摊销曲线在测什么**——真实上下文离"有限个簇"有多远。

---

## 3 · 带数字走一遍

> 以下为**玩具设定**，用于演示量纲与决策逻辑；其中的 `Δt`、`ΔE` 是我自造的数字，其余权重/参数取自原文。

### 3.1 一次库命中 vs 一次模型调用（bandit 的算术）

M1 任务在 20 s 处触发 F7（电量 17–24%，低于 `IsBatteryOk min_pct=25` guard），基线树走 abort 分支，必需目标未达成 → `y=0`。

假设某次 episode：库中已存 patch 被选中（`u=0`），之后 25 s 完成投送并降落，耗电 9%：

```
reward = 1 − 0.30×0 − 0.10×(25/100) − 0.10×(9/10)
       = 1 − 0      − 0.025         − 0.09
       = 0.885
```

同一情形若走 `CallLLM`（`u=1`）：

```
reward = 0.885 − 0.30 = 0.585
```

**读法**：库中 patch 只要能维持同等成功率，bandit 必然收敛到"不问"——因为问的净收益必须先补上 `κ=0.30` 的洞。为避免 `CallLLM` 臂被永久负债、再也长不出新结构，原文规定：当 `CallLLM` 产出的 patch 被准入时，**该 patch 额外记上 reward + κ**（把省下的 0.30 还给新臂）。这就是"调用率衰减是学出来的，不是排出来的"。

### 3.2 Stage 3 的 margin 量化（为什么"最常被拒"是 no margin）

`K=3` 次 replay ⇒ `p̂ ∈ {0, 1/3, 2/3, 1}`，量化步长 `1/3 ≈ 0.333 > δ = 0.25`。

```
候选 p̂ = 2/3, 现状 p̂ = 2/3  →  2/3 ≥ 2/3 + 0.25 ?  ✗ reject
候选 p̂ = 1,   现状 p̂ = 2/3  →  1   ≥ 0.667 + 0.25 = 0.917 ? ✓ admit
```

所以一个"针对树已经能处理的失败"提的补丁，几乎必然被 stage 3 以 "no margin over the current tree" 拒掉——原文确认这是他实验里**最高频的 stage-3 拒绝**。`K=3` 的分辨率决定了 `δ=0.25` 实际上是"必须整整高出一档"。

### 3.3 `ReplaceSubtree` 的 nominal regression 是怎么被抓到的

按原文的 mission value 权重（必需 1、可选 0.5；Tab. II 的值域 ≤1 提示做过归一化，此处归一化为按值域反推的解读，原文未显式写）：

```
M2 survey（lane1 必需，lane2/3 可选）
  满值 = 1 + 0.5 + 0.5 = 2  →  归一化 1.0
  某 ReplaceSubtree 删掉两条可选车道
       = 1 + 0     + 0   = 1  →  归一化 0.5
```

这个 patch **安全、且 7 次使用 7 次成功**（它从不尝试可选目标，所以从不让必需目标失败），在没有 nominal-replay 检查时被准入并结晶。检查加上后，任何 nominal mission value 的下降都被拒。

---

## 4 · 工程视角

| 项 | 论文报告值（逐字） |
|---|---|
| 单次结构化 proposal 延迟 | **31–105 s**（两次 schema 约束调用；Gemini 3.1 Pro，temperature 0.2） |
| 仿真推进 | lockstep，tick period **50 ms**，**10×** real time；一个 50 ms 请求恒定推进 **17** 个物理步 |
| BT 频率 | **20 Hz**（Fig. 1 标注 "py_trees, 20 Hz lockstep"） |
| 单次 replay 墙钟 | **5–15 s** @10× |
| replay 并行度 | **4** 个 runtime instance |
| 每 seed 准入开销 | **103–203** 个 replay episode |
| 学习期 LLM 调用总数 | **11 ± 1.4**（20 episodes） |
| 部署侧 tick 路径内的神经计算 | **无**（"No neural component is in the tick path"） |
| GPU / VRAM / 真机算力 / 端侧内存 | **论文未报告** |
| 真机验证 | **未做**（未来工作：PX4 部署） |

**关键 trade-off：把所有成本前置到学习期。**

1. **延迟被"暂停"吸收，不是被"加速"吸收。** 31–105 s 的模型调用在仿真里之所以可接受，是因为 episode 被整个暂停；真机上没有这个特权。所以 SCBT 的部署形态必须是：失败瞬间走手写 abort 分支（该分支本来就在），补丁生成发生在**离线/停场**，而不是飞行中。论文的 "learning phase" 语义天然接受这一点。
2. **确定性要分两层看。** 论文明确区分：**控制逻辑**是观测序列的纯函数（11 个冻结 cell、60/60 条日志离线 re-tick 哈希与在线一致）；**世界**不是（仿真器命令执行线程按墙钟调度，五次相同 lockstep 跑出三条在 `10⁻⁴ m` 级不同的轨迹）。端到端 10 次重复里 7 个 cell 单哈希，其余 4 个 cell 出现 2–4 个不同哈希、tick 抖动 1–33（0.05–1.65 s），最终结果相同。**这已经不是软件 bug，是阈值穿越的物理。**
3. **两处竞态是必须显式消灭的。** (a) tick 内发出的命令要先 flush 再发同步 barrier，才 step；(b) action leaf 的完成判定必须读**本 tick 遥测快照**，而不是读服务器回复（回复到达时刻依赖墙钟）。不做这两件事，trace 就不是观测的函数。
4. **资源回收的硬边界。** `P_max=3`、`F_max=2` 不是调参，是**防死循环**：没有它们，manager 会在同一锚点上反复应用同一 patch 直到超过解释器递归上限。同理，黑板的命名空间必须带 `(simulator instance, vehicle)` 前缀——replay farm 里跑的是同名无人机，不带实例前缀，活体的树会给 farm 里的机器发指令。
5. **检索的算力基本免费。** `φ(c)` = MiniLM 句向量 + failed node type / class 的 one-hot + 归一化遥测；检索只在 text 与 node-type 两个块上算余弦（**故意排除 class**，好让跨类候选浮出来）。这部分是可 CPU 完成的小模型工作，不是瓶颈。

---

## 5 · 数据与评测

**仿真栈（逐字）**：Microsoft Project AirSim（AirSim 的后继），headless runtime，**Fast Physics** + **Simple Flight** 控制器，IMU/GPS/barometer/battery 传感器，**无渲染、无网格碰撞**。场景与机器人配置按 class 程序化生成（frame mass、battery capacity/drain）。**未用 PX4**。

**任务（逐字）**：`M1` transport（向北投送 **40 m**，必需；返航；降落）、`M2` survey（三条 **30 m** 车道，lane 1 必需，lanes 2–3 可选；返航；降落）。标称能耗：**M1 用 12.7% 电量，M2 用 20.7%**。

**失败课程**：注入时刻随机取 `[6, 14] s`。headless 可用：**F1** wind gust、**F2** GPS 噪声后丢失、**F5** 降落垫移位、**F6** no-fly zone、**F7** 电池容量降低、**F8** 链路中断、**F12** 间隔冲突（双机）。需要渲染主机的 **F3、F4、F9–F11**（障碍、垫占用、相机掉线、目标搜索）留作未来工作。**实际课程只跑 F1 与 F7。**

**两处标定（这是本文最扎实的工程细节）**：

- **F1**：Fast Physics 四旋翼对均匀风在 **20 m/s** 以内几乎完全拒止（8 s 内漂移 **&lt; 1 m**），**~25 m/s** 以上饱和（30 m/s 时 8 s 漂移 **47 m**；25 m/s 下一条 40 m 腿结束于距目标 **226 m**）。因此 F1 采样 **22–28 m/s、持续 15–30 s**——按实测，这是"超出跟踪能力"。
- **F7**：电量设为 **17–24%**（低于 `25%` guard），drain **×1.3–2.2**，使"在降低的 reserve 下完成必需腿"在多数但非全部实例中可行。held-out 变体用**不相交的参数子区间**。

**评测协议**：

| 阶段 | 设置 |
|---|---|
| 学习期 | 20 episodes，mission `~U{M1, M2}`，failure `~U{F1, F7}`，方法间共享种子；SCBT 跑 seeds 0–2，消融跑 seed 0 |
| 冻结期 | 结晶后，在 20 curriculum + 20 held-out episodes 上评测，**所有学习组件禁用**（Patch Manager / farm / LLM / bandit 对象都不实例化） |
| 确定性 | 第一场景 10 次端到端重复（distinct trace hash、tick spread）；每次重复再用该次遥测日志做 3 次离线 re-tick（no-op 命令），比对哈希 |
| 基线 | B0 手写专家树（含所有失败的 recovery 分支）、B1 每次失败整树重生成、B2 有文法与准入但无库、B3 无 CMA-ES、B4 无 bandit（最近邻否则问 LLM）、B5 仅静态准入、B6 无跨类迁移；B2–B6 都是同一代码路径的配置开关 |

**学习期结果（Tab. I，逐字）**：SCBT **11 ± 1.4** 次调用 / 20 episodes，后半程 **0.33** calls/episode；B1 整树重生成 **26**（后半程 **1.20**）、B2 无库 **22**（后半程 **1.00**），两者结束时仍高于 1 call/episode。SCBT 各 seed 有 **12–14 / 23–24** 个失败事件由库服务。准入很有选择性：每 seed **2–3** 个准入、**7–9** 个拒绝，拒绝来自 stage 2（landing reserve **0.6–8.0%**，或风中 **238–1009** 个 geofence 违反 tick）与 stage 3（无 margin / nominal 回归 / 成功率低于 `ρ_min`）。**四次拒绝是准入错误**（模型输出的畸形 XML 到了编译器）。B5 跳过 replay，**10 个提案全部准入**。库的摊销作用由 B2 反证：B2 与 SCBT 唯一的差别就是不存 patch。

**冻结期结果（Tab. II，逐字）**：SCBT 结晶树 **M1 28 节点 / M2 33 节点，各 2 个 patch**，curriculum 上成功率 **.97 ± .02**、mission value **.78 ± .04**；未打补丁的 base 树 **.12 ± .09 / .12 ± .09**；手写专家 B0 **.98 ± .02 / .83 ± .06**。分失败类型：SCBT 恢复 **22/24** 次 F1、**36/36** 次 F7（B0：**23/24**、**36/36**）。

**held-out 的教训**：每个方法都退化。F1 held-out（**28–30 m/s 持续 30–36 s**）把无人机推出 geofence，**20 个 episode 中有 14 个**无论用什么树都发生；B0 只恢复 **4/36**，SCBT 同样 **4/36 F1**、**22/24 F7**，与 B0 在统计上不可区分。**唯一的例外是 B5**：仅静态准入、保留了 8 个 `WrapFallback` + 2 个 `WrapRetry`（**84/89 节点**），恢复 **14/14** 个 held-out F1 场景——没有任何其他方法（包括专家树）做到。B5 的树在该课程上并非不安全（20 个 curriculum episodes 无不变量违反；3 次降落低于 10% reserve，SCBT 为 2 次）。

**确定性（逐字）**：11 个冻结 cell 全部在 3 次离线 re-tick 中产出**单一** trace hash，且该 hash 等于产生该日志的在线运行哈希（**60/60** 条日志）。端到端 10 次重复中 **7** 个 cell 单哈希，**4** 个（B3、B6、两个 SCBT seed）出现 2–4 个不同哈希，tick 抖动 1–33（0.05–1.65 s），最终结果一致。

---

## 6 · 能力与失败模式

### 能做（具体到条件）

- **在训练分布上匹配人类专家**：两 patch、28/33 节点的机器产物，`.97 ± .02` vs B0 `.98 ± .02`，且**模型不在环**。
- **摊销**：20 episodes 内把调用从"每 episode 一次以上"压到后半程 0.33，机制是库 + bandit，不是人为调度。
- **可审计性**：每个子树都有 provenance（来源事件、模型 rationale、准入记录），结晶树是"基树 + 两处可读编辑"，节点名按 patch id 重命名以避免锚点冲突。
- **准入抓到的三类真问题**：(a) 安全但无用（`ReturnToLaunch` 单独一个 patch，静态可过、6 次 0 成功，因为它放弃了必需目标）；(b) 优化器钻目标空子（13.2% reserve 降落于 9.8%）；(c) nominal 回归（`ReplaceSubtree` 删掉可选车道）。
- **跨类迁移**在代码里存在（静态检查器原地做 leaf 替换、`θ` 从源类最优重新调、重新准入），检索 class-agnostic 使候选可见。

### 不能做（具体到条件）

- **不外推**：held-out 上 `.43 ± .10`（curriculum `.97 ± .02`）。而且 held-out F1 带**基本对所有方法都不可行**，所以这个数字测的是"对不可恢复条件的鲁棒性"，不是泛化。
- **不覆盖设计外失败类型**：只跑 F1/F7；F2/F5/F6/F8/F12 实现了但未进课程；F3/F4/F9–F11 需要渲染主机。
- **不做形式化验证**：作者明确 "We make no formal-verification claim"。安全 = 不变量监视器 + 10% landing reserve，且随机 replay 覆盖不了部署分布。
- **不做多机 / 不做跨类实验**：F12 与 fleet 已实现但未运行，所以 **B6 与 SCBT 只差一个配置**——这条消融实际上没有被真正激活。
- **stage 2 会冤枉 patch**：见 §8。

### 隐含假设 (Hidden Assumptions)

1. **失败是"局部可补"的。** 文法只有 6 个算子（`WrapFallback / GuardWith / WrapRetry / InsertBefore / InsertAfter / ReplaceSubtree`），全部是**锚点邻域的编辑**。需要全局重规划、或需要新增 leaf 类型（manifest 之外）的失败，表达能力直接为零。
2. **失败可被复现。** replay 从 mission start 重跑同一 mission、同一失败类型、扰动后的注入参数，等价于假设"该失败在参数邻域内稳定重现"。而作者自己说仿真器不是 bit-reproducible（`10⁻⁴ m` 漂移、阈值穿越翻转一 tick），所以 replay 的"同一个失败"和线上的那次并不是严格同一个。
3. **上下文成簇。** 摊销上界 `Q|ℳ|/p` 要求上下文落在有限个簇里、`ρ=0.80` 恰好切在簇边界上。held-out 的结果就是这条假设破裂时的样子。
4. **遥测足以描述失败。** headless 下 `s` 由遥测字段（failed node type、leaf feedback、高度、速度、风、电量、GPS、链路）拼出——**没有感知**。凡是需要"看见"才能诊断的失败，这条假设失效。
5. **一次 episode 一种失败、一台车。** 组合故障、级联故障、多机耦合都不在评测里。
6. **仿真不变量 ≈ 物理安全。** "geofence / altitude / speed cap / separation / reserve ≥ 10%" 被当作安全的可操作定义；这是工程约定，不是安全证明。

---

## 7 · 与相关工作对比

| 方法 | 结构从哪来 | 模型是否在环 | 是否保留产物 | 是否经验验证 | 是否摊销 | 最终产物 |
|---|---|---|---|---|---|---|
| FSM / 手写 BT | 人 | 否 | — | 人工 | — | 确定性控制器 |
| 遗传编程 / 学习 leaf 策略 [5–7] | 奖励 | 否 | 是 | 训练 | — | 策略/树（样本饥渴） |
| Code as Policies [9] / SayCan [10] / VoxPoser [12] | LLM 现场写 | **是** | 否 | 否 | 否 | 用完即弃的程序/值图 |
| VLA [13, 14] | 像素→动作 | 是 | 权重 | 训练 | — | 神经策略（不可检查） |
| BTGenBot [15] / LLM-BT [16] | LLM 生成 BT XML | **是（按需重生成）** | 否 | 语法 + 仿真执行 | 否 | 每次重生成 |
| Voyager [21] | LLM 写技能 | 是 | **是（embedding 检索）** | 执行反馈 | 部分 | 技能库 |
| Eureka [19] / RL-GPT [20] | LLM 写 reward / 分工 | 是（设计期） | 是 | RL 训练 | 部分 | 训练好的策略 |
| **SCBT（本文）** | LLM 提议**最小子树补丁** | **否（编译期一次）** | 是（context-indexed 库 + provenance） | **三阶段：静态 + 不变量 replay + 相对经验 margin** | **是（bandit + 结晶）** | **无人手写的确定性 BT** |

与最近的 BTGenBot/LLM-BT 的差别是三件事同时成立：**(i)** 产物被保留并组合；**(ii)** 保留的门槛是"相对当前树的经验 margin"，不只是语法/仿真能跑；**(iii)** 有显式的 `CallLLM` 臂去学"何时停止提问"，并有明确的终止态（结晶）。

> **面试 Tip**：被问"这跟 BTGenBot / LLM-BT 有什么区别，不就是 LLM 生成行为树吗"——一句话答："他们是 **runtime code generator**，模型永远在环、产物用完即弃；SCBT 是 **compile-time compiler**，只在结构失败时编译一次、用经验 margin 验收、用 bandit 学停止、最后固化成没人在环的确定性 BT。" 然后主动补 B5 负结果："admission 是旋钮不是过滤器——我们那条绝对不变量规则把风导致的 geofence 越界算在 patch 头上，反而杀掉了泛化最好的配置（held-out F1 14/14）。"这一句能立刻把你从"读过摘要"区分出来。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-20)

**repo 状态核实**：全文（含 HTML 版）**未出现任何 `github.com` 链接**；页面中的 "Report GitHub Issue" 是 arXiv 的 UI 按钮，不是项目仓库。因此 **官方 repo 未在论文中给出**，不存在可引用的 issue 编号 / commit / 维护者回复。以下 3 条 pitfall **由 §6 失败模式 + §4/§1 的方法约束机械推导**，标注为**未经 issue 验证**。

### P1 · 按原文 spec 部署 admission，你的风扰恢复 patch 永远进不了库

- **来源失败模式**（§6）：stage 2 "reject on any violation tick" 是**绝对**规则，不与未打补丁的树做对比。
- **方法约束**（§1.1 / §2.3）：监视器只看候选树的 replay，`K=3`，无 baseline 分支。
- **机械后果**：F1 的风本身就把机体吹出 geofence → replay 记录 **238–1009** 个违反 tick → 无论 patch 多好都被拒 → 结晶树几乎没有风恢复分支。作者自己的对照是 B5（跳过 replay）拿到 **14/14** held-out F1，而 SCBT 只有 **4/36**。
- **落地动作**：把 stage 2 改成**相对**规则——只拒 patch 相对未打补丁树**新增**的违反 tick，与 stage 3 已经在做的"相对 margin"对齐。论文明确把这条列为"future work 的第一项"，且说明**报告的数字仍是旧规则下的**，所以复现时你会看到与论文不同的 F1 覆盖率，这是预期行为，不是你的 bug。

### P2 · `K=3` + `δ=0.25` 让 stage 3 退化成"必须整整高一档"，且大量候选被判 no margin

- **来源失败模式**（§6）："候选若针对树已能处理的失败，会因缺乏 margin 被拒"是最高频 stage-3 拒绝。
- **方法约束**（§2.3）：`p̂` 由 `K=3` 次 replay 估计 ⇒ 取值只能落在 `{0, 1/3, 2/3, 1}`，量化步长 `1/3 ≈ 0.333` 已经大于 `δ=0.25`。
- **机械后果**：`δ` 实际上不起"细调松紧"的作用，只起"必须跨一整档"的作用；把小 `δ` 调到 0.1 不会让准入变宽松，只会浪费调参时间。要提高分辨率必须**加 K**（代价：每 seed 已经烧掉 **103–203** 个 replay episode）。
- **落地动作**：先定分辨率 `1/K`，再定 `δ`，让 `δ` 是 `1/K` 的整数倍附近；或改 Beta 后验 + 置信下界，避免 fixed-K 的阶梯效应。

### P3 · 直接把 Patch Manager 接到真机/长期运行，会在同一锚点上自激直到解释器递归上限

- **来源失败模式**（§6）：论文复现过"同一个 patch 在同一 anchor 上被反复应用，直到树超过解释器递归限制"。
- **方法约束**（§1.1 / §4）：防线是 `P_max=3`、`F_max=2`、以及"已应用的 patch 从 fallback 选择中排除"这三条**运行期计数器**；这些计数器属于 Patch Manager（学习期组件），而结晶后的树里**没有**它们。
- **机械后果**：结晶前的树靠计数器活着，结晶后的树靠"结构已经够用"活着。如果你在结晶**之前**就把 Patch Manager 挂到长跑系统上（比如在线持续学习），必须自己搬运这三个计数器；否则一旦出现文法能表达但闭环无法收敛的失败模式（例如 guard 反复翻转），就会出现 patch 叠加 → 节点数膨胀 → 递归上限。B5 的 84/89 节点已经展示了"宽准入"下树规模的增长方向。
- **落地动作**：把 `P_max / F_max / applied-set` 提升为 BT 运行时的**一等公民**（而不是 learning-only 的局部状态），并在结晶时把已应用的 patch 锚点写进树的静态不变量。

**另注（非 pitfall，但会坑复现）**：`MissionCritical`、`SetSpeed`、`GoToRequiredGoal`、`IsBatteryOk min_pct=25`、`GoToNED` 的 `goal_id` 语义、以及黑板按 `(simulator instance, vehicle)` 命名空间——这些是**未被行为树标准覆盖的本文私有约定**。`GoToRequiredGoal` 必须从黑板读"下一个未完成的必需目标"，否则 `{@p}` 占位符机制失效、patch 会退化成"飞向录制时的字面坐标"（作者在开发期正是踩了这个坑：patch 被复用到另一个 mission 上，飞到了错误地点）。

---

[← Back to Navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（本文全部实验均为 Project AirSim headless 仿真，作者自陈未上 PX4 硬件）

[//]: # "<!-- source: https://arxiv.org/abs/2610.25455 -->"
