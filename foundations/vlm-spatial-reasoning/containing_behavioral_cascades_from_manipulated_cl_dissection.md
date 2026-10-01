<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# 遏制 LLM 多机器人系统中被操纵声明引发的行为级联 (Containing Behavioral Cascades from Manipulated Claims in LLM-Powered Multi-Robot Systems)

> **发布时间**：2026-09-24（arXiv:2609.30523v1 [cs.RO]）
> **论文 / 模型名**：Verify–Adapt–Hold (VAH) framework
> **核心定位**：当 LLM 高层规划器被"伪造障碍物"的权威式提示欺骗并接受假世界状态后，把"事后打假"建模成一个**团队级规划问题**而非二元信任决策，从而阻断假声明在共享时空规划器中的车队级传播。

本文不研究"如何防住操纵"，而是**在操纵已然成功的前提下**研究其下游物理后果如何被遏制。结论先行：把验证动作与任务执行耦合、按"影响相关性"选择性派发验证机器人，可在多数条件下让 SOC / makespan 贴近无攻击基线，同时维持高验证覆盖率——但在小队形（N=3）高影响场景下反而比"直接绕行"更差。

---

## X-Ray 开场

LLM 作为多机器人系统的高层规划器时，一条被接受的假障碍声明会引发**行为级联（behavioral cascade）**：一台机器人改道会占用共享预订表（reservation table），进而挤占后续被规划机器人的可行路径，连轨迹根本不与假区域相交的机器人也被迫重新规划。本文提出 Verify–Adapt–Hold：把假声明视为**暂定障碍**，选派机器人去核实、只让"验证完成前就会撞上该声明"的机器人临时改道、其余机器人保持可信轨迹不变。对 spatial AI 研究者而言，意义在于：**post-compromise 的鲁棒性是一个调度/规划问题，而不是一个"信 / 不信"的门限问题**。

---

## 📍 研究全景时间线

```
2022-2023  LLM 进入机器人高层规划 (SayCan / Code-as-Policies / 多机器人分配)
              │  LLM 把自然语言 → 结构化任务/协调决策
              ▼
2023-2024  语义操纵攻击面成型
              │  直接/间接 prompt injection、恶意触发、对抗扰动、通信劫持
              ▼
2024-2025  防御研究：jailbreak 表征 + 输入扰动 / 注入对抗
              │  "降低但无法消除"成功操纵的概率  ← 本文明确定位为互补而非替代
              ▼
2026  ────● 本文：post-compromise containment（操纵成功之后）
              │  把"验证 + 任务执行"联合成一个团队级规划问题
              │  Verify–Adapt–Hold + 事件驱动角色更新 + 共享 A* 时空规划
              ▼
未来工作   多操纵通道 / 去中心化 onboard LLM / 大车队+真机 /
           异构团队 / 受限通信 / 部分有效声明(partially valid claims)
```

**本文在演进中的位置**：它是"语义安全"链条里**被前人跳过的一环**——前人做的是"别被攻破"，本文做的是"已被攻破后如何止损"。**本文局限**：（1）仅仿真、无真机；（2）仅固定中心化 operator 且分配固定不变；（3）评测中 $`\mathcal{X}\subseteq\mathcal{F}`$，即假声明**全部是假**，未触及部分真/部分假的声明；（4）小舰队高影响下反而劣于 naive baseline。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 角色 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|---|
| Operator $`\mathcal{O}`$ | LLM 高层规划器（gpt-oss-120b） | 自然语言指令、世界状态、外部消息 | $`t=0`$ 时任务分配（resource $`\tau`$、pickup $`s_i`$、drop-off $`g_i`$）；$`t_H`$ 时接受被操纵的障碍声明 $`\mathcal{X}`$ | 推理；分配在全部方法与迭代中**固定复用**，不作为研究对象 |
| Verification $`\mathcal{V}`$ | LLM 验证/角色分配模块（gpt-oss-120b） | $`\mathcal{X},\ \mathcal{X}_t^{\mathrm{obs}},\ \{(q,I(q))\}_{q\in\mathcal{Q}_t},\ \{(\gamma_i,a_i)\}_{R_i\in\mathcal{R}},\ \mathcal{L}_t,\ \mathcal{C}_t,\ \mathcal{R}_t^{\mathrm{upd}}`$ | $`\{a_i^{\mathrm{new}}\}_{R_i\in\mathcal{R}_t^{\mathrm{upd}}}`$（Verify / Adapt / Hold，close 时另有 Rest） | **无 chat history 的全新 prompt**；每次调用只更新 $`\mathcal{R}_t^{\mathrm{upd}}`$（触发事件的机器人） |
| STP（Shared Space-Time Planner） | $`A^{*}`$ 执行层 | $`(p_i(t_0),t_0),\ a_i,\ \mathcal{F}_i^{\mathrm{plan}},\ \mathcal{Z}_{<i}`$ | 时空轨迹 $`\gamma_i`$ | 只决定几何与时序，**从不修改 $`a_i`$**；不可行则上报，由 $`\mathcal{V}`$ 在有界次数内重派 |
| Roles | 运行时语义 | 可信轨迹 $`\gamma_i`$、未决声明 $`\mathcal{X}_t`$ | Verify / Adapt / Hold（+ Stop 仅基线；Rest 仅 close） | $`\mathcal{V}`$ 生成 + 硬约束校验后执行 |

### 1.2 关键机制

**⚡ Eureka Moment：不要把假声明当"可信 / 不可信"二选一——把它当暂定障碍，用"验证何时完成（$`T`$）"与"每台机器人何时撞上它（$`K_i`$）"赛跑，只让跑输的那批机器人改道。**

三个由此派生的设计：
1. **暂定性**：$`\mathcal{X}`$ **永不写入** $`G_{\mathrm{true}}`$；物理扫描返回真实占用 $`G_{\mathrm{true}}(c)`$，观测到即解锁。
2. **决策相关性优先**：簇 $`q`$ 的二值影响 $`I(q)=1`$ 当且仅当它相交某条剩余轨迹；只对 $`I(q)=1`$ 的簇派专责 verifier，$`I(q)=0`$ 的簇推迟到 close。
3. **事件驱动增量更新**：只有 E1（verifier 监视集清空）和 E3（close）才重新调用 $`\mathcal{V}`$；E0（顺路扫描）与 E2（drop-off 完成）不调用模型。

### 1.3 信息流 / 架构图

```
恶意权威式消息 ──(仅 O 收到，不直传 V)
        │
        ▼
   ┌─────────┐  接受假障碍 X (X ⊆ F, 永不写 G_true)
   │  O / LLM│──────────────────────────────┐
   └─────────┘                              │
                                            ▼
                              ┌──────────────────────────┐
                              │  V / LLM (fresh prompt)  │
                              │  影响 I(q) + 候选站位 C_t │
                              └──────────────────────────┘
                                            │ {Verify/Adapt/Hold/Rest}
                                            ▼
   ┌──────────────────────────────────────────────────────┐
   │  STP = A* + 共享预订表 Z = (Z^V, Z^E)                  │
   │  Hold 轨迹先预订 → 再规划 Verify/Adapt(把 X_t 当墙)     │
   └──────────────────────────────────────────────────────┘
                                            │ 轨迹 γ_i
                                            ▼
                                     执行 / 感知 (ρ=2, LOS)
                                            │ 扫描 → S_t, 更新 X_t
                                            ▼
       事件循环  E0 顺路扫描(不调 V) │ E1 verifier 清空(调 V)
                 E2 drop-off(不调 V) │ E3 close(调 V, X_t≠∅ 且 (J_t=∅ 或 J_t^blocked≠∅))
                                            │
                                            └──► 回到 V（仅触发者）
```

---

## 2 · 数学核心

📌 **Napkin Formula**：

```math
\text{Hold}: K_i > T \qquad \text{Adapt}: K_i \le T
```

一句话直觉：**"我到达未决假障碍的步数" 比 "验证者到达观察站位的最长耗时" 更长，我就什么都不用改。**

**目标**：在操纵已成功（operator 接受 $`\mathcal{X}`$）后，最小化车队级额外代价，同时不耽误任务、不遗漏关键验证。

**核心公式链**

1. 未决声明集合递推（证据即时提交）：
```math
\mathcal{X}_t=
\begin{cases}
\mathcal{X}\setminus\mathcal{S}_t, & t=t_H,\\
\mathcal{X}_{t-1}\setminus\mathcal{S}_t, & t>t_H,
\end{cases}
\qquad
\mathcal{Q}_t=\{q\in\mathcal{Q}: q\cap\mathcal{X}_t\neq\varnothing\}
```

2. 角色判定（$`K_i`$ 为撞上未决声明的剩余步数，$`T`$ 为最慢 inspector 到站位的最长行程）：
```math
K_i=\min\{k\ge 0: p_i(t+k)\in\mathcal{X}_t\},\quad K_i=\infty \text{ if empty}
```
```math
\text{Hold}: K_i>T, \qquad \text{Adapt}: K_i\le T
```

3. 验证站位与监视集约束：不同 verifier 站位互异；$`\mathcal{W}_i`$ 中每格须在站位 $`u_i`$ 的 sensing range 内且视线无遮挡；初始调用时每个 $`I(q)=1`$ 的簇配一名专责 verifier 满足 $`q\cap\mathcal{X}_t\subseteq\mathcal{W}_i\subseteq\mathcal{X}_t`$。

4. 级联遏制比（评价指标）：
```math
\mathrm{CCR}=1-\frac{\sum_{m=1}^{M}D_m(\pi)}{\sum_{m=1}^{M}D_m(\pi^{\mathrm{naive}})},
\quad
D_m(\pi)=\sum_{i=0}^{N-1}\max\!\left(0,\,c(\pi_i)-c(\pi_i^{\mathrm{nom}})\right)
```

**变量说明**

| 符号 | 含义 |
|---|---|
| $`\mathcal{G}=\{0,\dots,W-1\}\times\{0,\dots,H-1\}`$ | 仓库网格 |
| $`G_{\mathrm{true}}(c)\in\{0,1\}`$ | 真实占用（假声明**永不**写入此图） |
| $`\mathcal{F}`$ | 空闲格集合 |
| $`\mathcal{Z}=(\mathcal{Z}^V,\mathcal{Z}^E)`$ | 共享预订表：占用格-时刻对 / 转移 |
| $`\gamma_i`$ | 机器人 $`R_i`$ 的时空轨迹 |
| $`a_i=(s_i,g_i,\text{role},u_i,\mathcal{W}_i)`$ | 机器人分配 |
| $`\mathcal{X}, \mathcal{X}_t, \mathcal{S}_t, \mathcal{Q}_t`$ | 原始声明 / 未决 / 已观测 / 未决簇 |
| $`I(q)\in\{0,1\}`$ | 簇影响（$`1`$=相交剩余轨迹） |
| $`K_i,\ T`$ | 撞上未决声明的步数 / 验证最长耗时 |
| $`D_m(\pi),\ \mathrm{CCR}`$ | 单次相对 Nominal 的额外里程 / 级联遏制比 |

**直觉**：角色判定本质是一个"验证赛跑门限"——$`T`$ 把机器人分成两拨，$`K_i\le T`$ 的必须先自保改道，$`K_i>T`$ 的赌验证先完成，保持可信轨迹不动。**改道的代价只由真正冲突者承担，而不是全队。**

---

## 3 · 带数字走一遍（玩具设定）

> ⚠️ 以下为演示用**玩具设定**，非论文实验数据。

**场景**：$`10\times 5`$ 网格，3 台机器人 A / B / C。$`t_H=4`$ 时 operator 接受一条假声明 $`\mathcal{X}=\{(4,2),(5,2)\}`$（一根长 2 的障碍"棍"），真实地图上这两格是空地，$`\mathcal{X}\subseteq\mathcal{F}`$。

**角色判定**（$`V`$ 选定 1 名 verifier，站位 $`u`$ 的 A* 距离 = 3 步，故 $`T=3`$）：

| 机器人 | 是否撞上 $`\mathcal{X}`$ | $`K_i`$ | 判定 | 理由 |
|---|---|---|---|---|
| A | 是，第 2 步到达 (4,2) | 2 | **Adapt**（$`2\le 3`$） | 验证来不及，先临时绕行 |
| B | 是，第 5 步到达 (4,2) | 5 | **Hold**（$`5>3`$） | 验证会在它到达前完成 |
| C | 否（轨迹不交） | $`\infty`$ | **Hold** | 完全不受影响，保持可信轨迹 |

**执行序列**（增量式）：
1. $`t=4`$：下发 A=Adapt / B=Hold / C=Hold。STP 先预订 B、C 的可信轨迹，再给 A 规划——A 把 $`\mathcal{X}`$ 当墙，绕行 +2 步。
2. $`t=6`$：verifier 到达站位 $`u`$，扫描 (4,2)(5,2)，得 $`G_{\mathrm{true}}=0`$ → $`\mathcal{S}_6=\{(4,2),(5,2)\}`$，$`\mathcal{X}_6=\varnothing`$，其监视集清空 → 触发 **E1**。
3. E1 只对 verifier 调 $`\mathcal{V}`$（$`\mathcal{R}_t^{\mathrm{upd}}=\{R_i\}`$），返回 Adapt 以续完剩余任务。
4. 由于 $`\mathcal{X}_6=\varnothing`$，所有剩余轨迹按更新后占用重规划——A 的绕行被**即时缩短**回最短路径。

**代价对照（玩具）**：A 的绕行 +2 步；若走 Naive Replan（全队接受 $`\mathcal{X}`$ 为墙），B 与 C 也会被挤占预订表而改道，额外里程可能扩散到 +6 甚至触发次级绕行。CCR 直觉上：$`1-2/6\approx 0.67`$。

**关键观察**：$`T`$ 越短（verifier 越近），Adapt 的机器人越少；当 $`T\ge\max_i K_i`$ 时，全队 Adapt，退化为 Naive Replan。这正是 N=3 High 场景 CCR 变负的机理。

---

## 4 · 工程视角

| 维度 | 论文报告情况 |
|---|---|
| 硬件平台 | **论文未报告**（纯仿真；真机验证列为 future work） |
| 延迟 / FPS | **论文未报告** |
| VRAM / 显存 | **论文未报告** |
| 吞吐 / 模型调用次数 | **论文未报告**具体数值；仅说明调用被事件门控：**只有 E1 与 E3 调用 $`\mathcal{V}`$**，E0、E2 不调用 |
| 规划器 | 时空 $`A^{*}`$（$`4`$-连通，允许等待，无对角移动） |
| 网格规模 | $`48\text{ by }28`$（全部实验固定） |
| 车队规模 | $`N\in\{3,6,9,12\}`$ |
| 感知参数 | Chebyshev 半径 $`\rho=2`$，视线无遮挡 |
| 模型 | Operator 与 Verification 均为 `gpt-oss-120b` |

**可推导的部署 trade-off（非论文报告数字，属机制推论）**：
- **模型调用被刻意稀疏化**：$`\mathcal{V}`$ 用 fresh prompt（无 chat history），只在 E1/E3 触发，且只更新 $`\mathcal{R}_t^{\mathrm{upd}}`$。这是一个以"降低 LLM 推理频率"换"角色可能次优"的设计——文中提到不可行分配会被退回模块，**在有界次数内**重派（bounded number of attempts）。
- **中心化共享预订表**是同步瓶颈：$`\mathcal{Z}`$ 要求全队一致的实时状态，隐含**通信可靠、无延迟**假设；去中心化与受限通信被列为未来工作。
- **规划顺序敏感**：Hold 轨迹先预订，再规划 Verify/Adapt；若重复预订导致无解，planner 用**不同规划顺序重试**同一分配，再失败才退回 $`\mathcal{V}`$。
- **代价口径的工程含义**：SOC **不计等待**（只算走过格数），makespan **计等待**；$`\mathrm{SOC}(T_M)`$ 与 $`\mathrm{SOC}(T_V)`$ 分开报告——即任务完成后的验证行程**不计入 SOC / CCR**，但计入 coverage（在 $`\max(T_M,T_V)`$ 处评估）。

---

## 5 · 数据与评测

**环境与设定**（Table I，全部取自原文）：

| 参数 | 配置 |
|---|---|
| Team size | $`N\in\{3,6,9,12\}`$ |
| Warehouse layout | Fixed across all experiments |
| Grid Size | $`48\text{ by }28`$ |
| Pickup locations | $`|\mathcal{P}|=3`$ |
| Drop-off locations | $`|\mathcal{D}|=N`$，每机器人一个唯一 drop-off |
| Resources per pickup | $`N/3`$ |
| Sensing | $`\rho=2`$ |
| Operator model | gpt-oss-120b |
| Verification model | gpt-oss-120b |

- 每个 $`(N,\text{category})`$ 组合有 $`M=15`$ 次**成功操纵**的重复。
- 注入时刻 $`t_H`$ 从 $`\{1,\dots,\lfloor T_{\mathrm{nom}}/5\rfloor\}`$ 均匀采样（标称任务前 1/5），$`T_{\mathrm{nom}}`$ 为无声明时的标称 makespan。
- **同一重复内所有方法共享同一状态与 $`\mathcal{X}`$**。

**四类声明（claim categories）**：
1. **Low**：1 个孤立障碍格，放在 $`k\sim\mathrm{Unif}\{1,\dots,N\}`$ 台（无放回抽取）机器人的轨迹上。
2. **High**：一条长 $`\ell\sim\mathrm{Unif}\{2,\dots,5\}`$ 的直线障碍"棍"，放在**每台**机器人轨迹上。
3. **Mixed**：混合 on-trajectory 孤立障碍与棍 + off-trajectory 障碍；$`(k_s,k_m)`$ 从满足 $`0\le k_s,k_m\le\lceil N/2\rceil`$ 且 $`1\le k_s+k_m\le N`$ 的整数对均匀采样；另含 $`m_n\sim\mathrm{Unif}\{1,\dots,\lceil N/2\rceil\}`$ 个 near-path 障碍与 $`m_f\sim\mathrm{Unif}\{0,\dots,\lceil N/2\rceil\}`$ 个 wall-adjacent 远障碍。
4. **Kill**：抽 $`k\sim\mathrm{Unif}\{1,\dots,N\}`$ 台有未交付任务的机器人，用假障碍格**封死**其 drop-off。

**Baselines**：
- **Nominal**：无声明参考。
- **Naive Replan**：全队把 $`\mathcal{X}`$ 当墙（$`\mathcal{F}_i^{\mathrm{plan}}=\mathcal{F}\setminus\mathcal{X}`$）。
- **Verify-First**：贪心集合覆盖（式 7-8）选站位，含两变体 **Verify-Min**（仅 $`n_V`$ 台去验证，其余**停机等待**）与 **Verify-All**（全部 $`N`$ 台去验证）。
- **Rule-based VAH**：与 Verify-Min 相同 inspector 集 + 固定规则（式 10）：$`\mathcal{B}_i=\varnothing\Rightarrow`$ Hold；$`\mathcal{B}_i\neq\varnothing, f_i=1\Rightarrow`$ Adapt；$`\mathcal{B}_i\neq\varnothing, f_i=0\Rightarrow`$ Stop；**角色一次决定不再更改**。

**指标**：SOC（总行走格数，不计等待）、Makespan（$`t_H`$ 到最后一台完成的最长步数，计等待）、Coverage（至少被观测一次的声明格比例）、CCR（式 11；$`1`$=无正额外里程，$`0`$=与 Naive 相同，可为负；分母为零或无 Naive 成本时未定义）。

**Coverage 结果（N=12，Table II）**：

| Scenario | Naive | Verify-Min | Verify-All | Rule Based VAH | Ours |
|---|---|---|---|---|---|
| Low | 87% | 100% | 100% | 100% | 100% |
| High | 72% | 100% | 100% | 100% | 100% |
| Mixed | 62% | 100% | 100% | 100% | **98%** |
| Kill | — | 100% | 100% | 100% | 100% |

（Naive 无 Kill 条目：把声明当墙时被封的 drop-off 不可行。）

**CCR 结果（Table III，Ours 列）**：

| Scenario | N=3 | N=6 | N=9 | N=12 |
|---|---|---|---|---|
| Low | 1.00 | 1.00 | 0.98 | 0.96 |
| High | **−0.65** | 0.81 | 0.89 | 0.83 |
| Mixed | 0.60 | 0.83 | 0.86 | 0.95 |

对照：**所有验证基线（Verify-Min / Verify-All / Rule-Based VAH）CCR 全为负**（如 High@N=3：−5.49 / −8.90 / −5.47；Mixed@N=3：−16.60 / −22.10 / −16.63），即验证基线引入的额外里程**超过 Naive Replan**。

---

## 6 · 能力与失败模式

**能做**：
- 在 Low / High / Mixed 影响下 SOC 贴近 Nominal；除 Mission Kill 外取得最低或接近最低的 makespan。
- N=12 时，除 Mixed 外全部场景 coverage = 100%；Mixed 下 98%。
- 在除 High@N=3 外的**每个报告条件**中，CCR 介于 0.60 与 1.00；论文称 **每个任务相关簇（mission-relevant cluster）在整个研究中都被检查**，off-path 簇也"几乎每次"被扫到。
- 让验证与任务执行**重叠**：多数条件下 $`\mathrm{SOC}(T_M)<\mathrm{SOC}(T_V)`$，即任务先于验证完成。

**不能做 / 失败模式**：
1. **小队形 + 高影响**：High 影响 N=3 时 CCR = −0.65（唯一为负的本文结果）。原因（原文）：车队太小无法吸收验证成本——每条轨迹都相交声明，必须派一台去站位观察整条"棍"，另两台等待或绕行，验证行程超过 Naive Replan 绕行成本。
2. **非穷尽覆盖**：Mixed@N=12 coverage 98%。原文解释：off-path 簇被推迟到 close 事件，而 close 时所有剩余未知格都属于"已不可能影响任务"的簇，模块判定不值得派发，把空闲机器人指派为 **Rest**。这是**优先级取舍**，不是 bug——但意味着"保证全覆盖"的场景不满足。
3. **Mission Kill 需额外检验行程**：封死的 drop-off 必须先验证才能交付；N=6、N=9 时 Verify-Min 反而更快，因为"被封目标足够多以致交付被推迟，但又没有足够多空闲机器人并发检验"。
4. **Rule-based VAH 的对照失效**：固定角色导致 worker 与 inspector 争抢走廊、运动串行化，**makespan 在几乎所有条件下最慢**，尽管其 SOC 与 Verify-Min 相近——说明"固定角色"这一设计本身是失败的。

### 隐含假设 (Hidden Assumptions)

- **所有声明都是假的**：评测设 $`\mathcal{X}\subseteq\mathcal{F}`$，因此观测到声明格即"确认为空"、直接解除封锁。**部分有效声明（partially valid claims，即声明里混有真障碍）被明确列入 future work** —— 这是全文最大的未验证前提。
- **operator 已被欺骗，且分配固定**：conditioning on a successful manipulation；$`t=0`$ 的任务分配在所有方法与迭代中复用一个固定匹配，**分配本身不作研究对象**。
- **中心化 + 完整通信**：单一共享预订表 $`\mathcal{Z}`$ 要求全队状态一致；受限通信列为未来工作。
- **同质机器人**：fleet 为 $`N`$ 台 homogeneous robots；异构团队列为未来工作。
- **感知理想化**：Chebyshev 半径 $`\rho=2`$ 且视线无遮挡即视为可观测；无噪声、无遮挡动态变化。
- **声明永不污染真值图**：$`\mathcal{X}`$ 从不写入 $`G_{\mathrm{true}}`$，物理扫描总返回真值——现实中"唯一真值通道"未必存在。
- **LLM 角色分配可被硬约束校验**：框架依赖对 $`\mathcal{V}`$ 输出的校验 + 有界重试；LLM 的非确定性被"验证后执行"这一工程手段吸收。

---

## 7 · 与相关工作对比

| 维度 | 传统防御（输入扰动 / 注入对抗） | Runtime Assurance / Active Perception | Naive Replan | Verify-First (Min/All) | Rule-based VAH | **本文 VAH** |
|---|---|---|---|---|---|---|
| 介入时机 | **操纵前**（降低成功率） | 运行时安全监控 | 操纵后 | 操纵后 | 操纵后 | **操纵后** |
| 对假声明的态度 | 阻止进入 | — | 全盘接受 | 先验证后执行 | 一次判定角色 | **暂定，物理证据解锁** |
| 角色是否可修订 | — | 切换安全模式 | 全局重规划 | 否 | 否（一次决定） | **是（事件驱动）** |
| 是否考虑任务影响 | — | — | 否 | 几何覆盖 | 轨迹相交 + 可达性 | **影响相关性 $`I(q)`$ + 轨迹 + 时序 $`K_i`$ vs $`T`$** |
| 验证与任务 | — | 分离 | — | **串行**（非 inspector 停机） | 固定并发但争抢 | **重叠 + 选择性改道** |
| coverage (N=12) | — | — | 62–87% | 100% | 100% | 100%（Mixed 98%） |
| CCR | — | — | 0（参照） | 全负 | 全负 | **0.60–1.00（除 High@N=3 的 −0.65）** |

**结尾面试 Tip**：被问"LLM 规划器被骗了怎么办"，不要答"加过滤器/提示词加固"（那是防御态）。标准答法：**"一旦操纵成功，问题就从安全变成规划——把假声明当暂定障碍，用'验证完成时间 T'与'每台机器人撞上它的步数 $`K_i`$'做门限，只改道 $`K_i\le T`$ 的机器人，其余保持可信轨迹；再用事件驱动（E1/E3 才调模型）把 LLM 调用稀疏化。核心洞见是：遏制代价应该只由真正冲突的机器人承担，而不是全队。"** 再补一句边界："但小队形 + 高影响时验证行程可能超过直接绕行，CCR 会变负。"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-01)

**Repo 状态**：论文正文中**未出现任何 `github.com` 链接**（唯一外部链接是项目主页 `https://sites.google.com/view/vahframework`，且为纯文本、非 PDF 内嵌可点击超链接）。因此**无官方 repo 信号**，也无 issue 流可供验证。以下 3 条 pitfall **由 §6 失败模式 + 方法硬约束推导，未经 issue 验证**。

**Pitfall 1 — 小队形高影响下验证成本反超绕行成本（可机械推导）**
- 失败模式（§6-1）：High 影响 N=3，CCR = −0.65。
- 方法约束：Verify 角色要求"站位 $`u_i`$ 可达、不同 verifier 站位互异、$`\mathcal{W}_i`$ 全在 sensing range 内且视线无遮挡"，且初始调用要求**每个 $`I(q)=1`$ 的簇配一名专责 verifier**。当 $`N=3`$ 且每条轨迹都相交声明时，$`I(q)=1`$ 的簇数与可用机器人比逼近 1，产生不可压缩的检验行程。
- 推论：任何 $`T`$ 无法被机器人冗余吸收的部署（小队形 / 窄通道 / 高影响声明密集）都会触发此退化。**修法方向**：允许 $`I(q)=1`$ 簇共享 verifier，或对 $`T`$ 设上限超过阈值即回退 Naive Replan。

**Pitfall 2 — close 事件不触发 ⇒ 非关键簇永不覆盖（可机械推导）**
- 失败模式（§6-2）：Mixed@N=12 coverage 98%，因 close 时剩余未知簇被判"不影响任务"而指派 Rest。
- 方法约束：E3（close）的触发条件是 $`\mathcal{X}_t\neq\varnothing`$ **且** $`(\mathcal{J}_t=\varnothing\ \text{or}\ \mathcal{J}_t^{\mathrm{blocked}}\neq\varnothing)`$；$`I(q)=0`$ 的簇被明确"deferred to the close event"。若任务在 close 前自然结束且无被封锁任务，这些簇可能只被顺路扫描（E0）覆盖。
- 推论：在对"声明全覆盖"有硬要求的合规场景（如审计、安全认证），VAH 的优先级策略**不是**满足条件。**修法方向**：把 close 触发条件与"存在 $`I(q)=0`$ 未决簇"解耦。

**Pitfall 3 — 依赖"声明全假"前提，部分有效声明下行为未定义（可机械推导）**
- 失败模式（§6 隐含假设）：评测设 $`\mathcal{X}\subseteq\mathcal{F}`$，故观测到的声明格被"确认为空"并解除封锁。
- 方法约束：$`\mathcal{X}_t`$ 的收缩规则仅在"扫描返回 $`G_{\mathrm{true}}=0`$"时逻辑自洽（正文明确："In the evaluated setting, $`\mathcal{X}\subseteq\mathcal{F}`$, so observed claimed cells are confirmed free"）；$`\mathcal{X}`$ 本身永不写入 $`G_{\mathrm{true}}`$。
- 推论：一旦某声明格**真的是障碍**（部分有效声明），仅"观测到"并不意味着可以解除封锁——框架的解锁逻辑需要被重新定义。论文将 partially valid claims 明确列为 future work，等于承认当前版本在此场景下未验证。**修法方向**：把"已观测"与"确认为空"分离，观测仅提供 $`G_{\mathrm{true}}`$ 证据，真正的解锁需要 $`G_{\mathrm{true}}(c)=0`$ 显式判定并经校验后才从 $`\mathcal{X}_t`$ 移除。

---

[← Back to README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（arXiv:2609.30523v1）· 未在真机复现的数字标 `UNVERIFIED`；本文所有 SOC / Makespan / Coverage / CCR 数值均逐字取自 Table II、Table III 与正文描述。论文为纯仿真研究，未报告任何延迟 / 显存 / FPS / 硬件型号。

<!-- source: https://arxiv.org/abs/2609.30523 -->
