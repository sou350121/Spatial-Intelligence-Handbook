[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# FARO：可行性感知的机器人运动优化 (FARO: Feasibility-Aware Robot Motion Optimization)

> **发布时间**：2026-07-20（arXiv:2607.18362v1 [cs.RO]）
> **论文 / 模型名**：FARO（Feasibility-Aware Robot Motion Optimization）
> **作者/机构**：Michal Ciebielski、Shafeef Omar、Aaron Johnson、Majid Khadiv（TUM MIRMI；CMU ME；TUM-IAS）
> **核心定位**：一句话——把“接触序列是否可行”做成**三级递进、可缓存的必要条件过滤器**，让 humanoid loco-manipulation 的接触搜索从“每个节点一次几十秒的 TO”变成“每个节点一次亚秒级 KSO”。
> **Ontology（本库 5 轴）**：problem=navigation（实为 loco-manipulation 运动规划）· representation=n/a · sensor=n/a · paradigm=hybrid（离散接触模式 × 连续轨迹）· time=per-scene

导语：humanoid 多接触 loco-manipulation 的瓶颈不在于“能不能优化出一条轨迹”，而在于“接触序列的组合空间大到搜不动”——论文 Table I 里单次全动力学轨迹优化（TO）平均要 **64.70 s**，搜索树里每展开一个节点都做一次 TO，在 2 小时预算内只能展开十几个节点（hard 任务 TO-only 平均 **12.8** 节点、**0** 个解）。FARO 的结论是：用 KSO（运动学序列优化）这种“丢掉动力学、只保留几何/接触/限位”的廉价代理当过滤器，平均 **0.60 s**、决策变量少 **74.8×**、保留 **70.0%** 的约束类型，假阴性几乎为零，于是同一个搜索在 hard 任务上能展开 **814.6** 节点、找到 **26.4** 个解。

---

## 🔎 X-Ray 开场

**解决什么问题**：给定场景（机器人 + 可动对象 + 环境几何 + 一组接触界面），要找出“手脚在什么时刻抓/踩哪个面”的离散接触序列，并为它生成动力学一致的全身体轨迹。难在离散 × 连续 × 欠驱动 × 长时程的乘积。

**提出了什么**：一个嵌套的 kino-dynamic 框架。三级可行性检查按代价从低到高排列——① mode/edge 的 IK 优化（式 14），② KSO 运动学序列优化（式 15），③ 全动力学 TO（式 17）；左侧的可行性是右侧的**必要条件**，因此提前否决不会丢掉可行解（只会产生假阴性）。这套过滤器接三种候选生成器：cost-based UCT 树搜索、LLM（GPT-5.5）采样、人工给定序列。

**对 spatial AI 研究者意味着什么**：这是“**把可行性当成一个可分级、可缓存的谓词**”的干净范例——不是学一个 heuristic，而是用同一套约束的**子集投影**构造一个解析的、确定性可复现的 lower bound；任何“search + expensive verifier”的管线（接触规划、抓取规划、任务分配、甚至 3D 重建里的 hypothesis verification）都能直接搬这个结构。

---

## 📍 研究全景时间线

```
 混合整数接触优化 [11,12,13]
        │  接触 = 二进制变量，组合爆炸
        ▼
 离散接触序列搜索 + TO [7,8,9,10]   ←── 本文的 baseline 家族（"similar to the
        │                               exploration strategies used in [8,9,10]"）
        │  放松换 tractability：简化模型 / 任务启发式 / 手工高层动作
        │  每节点一次 TO（单次 9.73–117.62 s，Avg 64.70 s）→ 搜索深度与广度都被卡死
        │
 ┌──────┴─────────────────────────────────────────────┐
 │ RL 运动控制 [4]（靠 reward shaping，适合周期步态）    │
 │ 示范跟踪 [16] / 人→人形重定向 [17,18,19]             │
 │   → 绕开"在新场景里探索出新行为"这个问题本身          │
 └──────┬─────────────────────────────────────────────┘
        │
 LLM 直接采样接触计划（本文 §IV-C 的采样器 = GPT-5.5 [29]）
        │  计划数量管够，但可行性完全未知 → 需要便宜的验证器
        ▼
 ★ FARO (2026-07)：mode/edge IK → KSO → TO 的三级必要条件滤波
        + feasible/infeasible 缓存 + cost-based UCT + progressive widening
        真机验证：RL 轨迹跟踪控制器 [19]（6/8 条人工序列上机）
        │
        ▼
 本文自陈局限：① 只支持平面矩形 patch 接触（作者指向可微 SDF [30]）
              ② 三级可行集"应当嵌套"但未给形式化证明（原文 left to future work）
              ③ 更长时程需要接 TAMP / program search [31]
```

---

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 | 论文报告耗时 |
|---|---|---|---|---|
| 场景与接触界面定义 | robot、movable objects、environment geometry、contact interfaces ℐ | 接触模式空间（Table IV 的允许接触表 → 分支因子 **108**） | 无学习，纯建模 | 论文未报告 |
| 候选序列生成器 | 场景 + 目标 | 候选接触模式序列 𝒞⁺ | LLM 分支用 **GPT-5.5 [29]**，**零微调**，仅 prompt（每 prompt 100 条计划） | 论文未报告（LLM 调用时间未给） |
| **M**：mode 可行性（式 14） | 单个接触模式 c | feasible / infeasible（进缓存） | 求解器 Ipopt [28]，无学习 | 论文未报告（Table I/II 未单列） |
| **E**：edge 可行性（式 14，c→c₁∪c₂） | 父子模式对 | feasible / infeasible（进缓存） | 同上 | 论文未报告 |
| **KSO**（式 15） | 完整序列 𝒞，K 个模式 | K+1 个位形 q₀:ₖ + 标量代价 J | acados SQP [26]，无学习 | **0.14–1.93 s，Avg 0.60 s** |
| **TO**（式 17） | 完整序列 𝒞 | x₀:ₙ、u₀:ₙ₋₁、T̄₀:ₖ₋₁ | Hippo SQP [27]，无学习 | **9.73–117.62 s，Avg 64.70 s** |
| 缓存 𝒦_feas / 𝒦_infeas | mode / edge / KSO / TO 的判定 | 复用结论，跳过重解 | — | — |
| 树搜索（Alg. 1） | c₀、预算 B、滤波器集 ℱ | 𝒮_goal（可行目标序列集合） | cost-based UCT + progressive widening（k=1.0, α=0.5, C=3） | 每次 run **2 h** |
| RL 轨迹跟踪器 | TO 输出的参考轨迹 | 关节指令 | **预训练、冻结**（引用 [19]），不在本文训练 | 论文未报告（控制频率未给） |

> 关键：**FARO 本身零学习**。唯一的“模型”是被 prompt 的 LLM 和冻结的 RL tracker，全部可复现的骨架是确定性 NLP。

### 1.2 关键机制

**⚡ Eureka Moment：既然“动力学可行”必然蕴含“几何/接触可行”，那就把后者当成前者的必要条件过滤器——同一个约束集，只改优化变量和离散化粒度，就得到一族代价差两个数量级、假阴性近乎为零的廉价验证器。**

拆开说这步“聪明”在哪：

1. **不是近似模型，是子集投影**。KSO（式 15）用的 contact（7a)(7b)(8)、collision（9）、limits（13a）与 TO **逐条相同**，只是把“N 个 knot 的轨迹 + 动力学”换成“K+1 个位形”。所以它保下来的约束类型覆盖率是 **70.0%**，而丢掉的恰好只是动力学那一类。这解释了为什么 FNR 能低到 0.0–1.3%——不是运气好，是构造上就该低。
2. **代价顺序 = 检查顺序**。M/E（单点 IK）→ KSO（K+1 点）→ TO（N 点 × 动力学），一旦某个 filter 失败就立刻终止（“verification terminates at the first failed filter”）。
3. **缓存把重复探索变成查表**。搜索里同一個 mode/edge 会被反复提出，`𝒦_infeas` 让第二次直接拒绝——论文明确把这归因为 KSO 与 M,E,KSO 之间的巨大差距（hard：218.2 → **814.6** 节点）。
4. **TO 被推迟到“已经到达离散目标”之后**（Alg. 1 第 15–19 行）。搜索期间 KSO 只当代价 J 的提供者，不负责最终动力学认证。

### 1.3 信息流

```
 场景 (robot + objects + env geometry + interfaces ℐ)
   │
   ▼
 ┌──────────────────────────────┐
 │ 候选接触序列生成器             │◄───────────────────┐
 │  search │ LLM(GPT-5.5) │ human│                    │
 └──────────────┬───────────────┘                    │
                │ 𝒞⁺ = 𝒞(v) ⊕ c⁺   (式20)             │
                ▼                                     │
      ┌─ [M]  mode IK (14) ──fail──► 𝒦_infeas ────────┤
      │         │ pass                                │
      ├─ [E]  edge IK (14) ──fail──► 𝒦_infeas ────────┤ 不可行反馈
      │         │ pass                                │
      ├─ [KSO] (15) ─────────fail──► 𝒦_infeas ────────┤
      │         │ pass  → J                          │
      │         ▼                                     │
      │   AddChild(𝒯, v, c⁺, J)  ── 树生长 ───────────┘
      │         │
      │    Goal(𝒞⁺)? ──no──► 回到 Select (式18/19)
      │         │ yes
      └─ [TO] (17) ──fail──► 丢弃
                │ pass
                ▼
            𝒮_goal ──► RL tracking controller [19] ──► 真机
```

滤波器集（式 21）：ℱ₁=(KSO)、ℱ₂=(M,E,KSO)、ℱ₃=(M,E,KSO,TO)、ℱ₄=(TO)——ℱ₄ 就是 baseline。

---

## 2 · 数学核心

📌 **Napkin Formula**

```
feasible_TO(𝒞)  ⟹  feasible_KSO(𝒞)  ⟹  feasible_M(c_s) ∧ feasible_E(c_s, c_{s+1})
    64.70 s            0.60 s              单点 IK（未单列）
    74.8× 决策变量  ────────────────────────►  代价单调下降，可行性单调放松
```

一句话：**用“更弱的必要条件”提前否决，只买假阴性风险（实测 ≈0），换两个数量级的吞吐。**

### 2.1 第一级：mode / edge 可行性（式 14）

**目标**：这个接触模式（或这一对模式的瞬时切换）在**几何上**站得住吗？

```
min_q   (q − q_nom)ᵀ W (q − q_nom)
s.t.    contact(q, c) ≤ 0        (7a)(7b)      ← 面贴合 + 不越界
        collision(q) ≤ 0         (9)           ← 有符号距离
        limits(q) ≤ 0            (13a)         ← 关节位置限位
```

- `q = (q^r, q^{o_1}, …, q^{o_{n_o}})`：机器人 + 全部对象的位形
- `c`：接触模式；测 edge 时替换为 `c₁ ∪ c₂`（瞬时同时满足两模式的接触）
- `q_nom`、`W`：正则化名义位形与权重
- **判据是求解器语义**：原文 “A contact mode c is said to be infeasible if the resulting nonlinear program does not converge within a number of maximum iterations.”（这句在 §8 会变成一个 pitfall）

**直觉**：先用一次单点 IK 问“这个抓/踩的组合在几何上摆得出来吗”，摆不出来就别浪费后面几秒。

### 2.2 第二级：KSO（式 15）

**目标**：整条 K 段接触序列，能否用 K+1 个位形串起来？

```
min_{q_{0:K}}  Σ_{s=0}^{K} (q_s − q_nom)ᵀ W (q_s − q_nom)
s.t.  q_0 = q_init,  q_K ∈ Q_goal
      ∀ s ∈ {1..K}:  contact(q_s, c_{s-1} ∪ c_s) ≤ 0   (7a)(7b)
                     collision(q_s) ≤ 0               (9)
                     limits(q_s) ≤ 0                  (13a)
      ∀ s ∈ {0..K−1}: 对满足 (16a) 持续接触 或 (16b) 释放接触 的 interface a:
                     contact(q_s, q_{s+1}, c_s) = 0    (8)  ← 无滑移
```

- `q_s`（1 ≤ s ≤ K−1）表示 **c_&#123;s−1&#125; → c_s 的切换瞬间**的位形；约定 `c_K := c_{K−1}` 以便末位形同构处理
- (16a) 持续接触：相邻位形间接触点位置固定；(16b) 释放接触：q_&#123;s+1&#125; 是分离瞬间的边界位形，sticking 约束保持到分离那一刻
- **没有时间变量、没有动力学**——这就是它能快 100× 的全部原因，也是它 70% 而非 100% 约束覆盖的全部原因

**直觉**：把“轨迹”降级成“一串姿态快照”，只问“这条接触序列在运动学上走得通吗”。

### 2.3 第三级：TO（式 17）

```
min_{x_{0:N}, u_{0:N−1}, T̄_{0:K−1}}  Σ_{i=0}^{N−1} φ(x_i,u_i) + φ_N(x_N) + w_T Σ_{s=0}^{K−1}(T̄_s − 1)
s.t.  x_0 = x_init,  x_N ∈ X_goal,   T̄_min ≤ T̄_s ≤ T̄_max
      ∀ i:  dyn(x_i, x_{i+1}, u_i, T̄_{s(i)}, c_{s(i)}) = 0   (10)(11)
            contact(x_i, u_i, c_{s(i)}) ≤ 0                 (7)(8)
            collision(x_i) ≤ 0                              (9)
            limits(x_i, u_i) ≤ 0                            (13)
```

- 状态 `x = (x^r, x^{o_1}, …)`，`x^r = (q^r, v^r, h^r)`：位形、广义速度、**质心动量**（h^r ∈ ℝ⁶）
- 控制 `u^r = (v̇^r, λ_1^r, …, λ_{n_ee}^r)`：广义加速度 + 各末端执行器 6D wrench
- `T̄_s`：**每个接触阶段一个**无量纲时间缩放因子，knot i 用 `T̄_{s(i)}·Δt`；`w_T` 惩罚偏离 T̄_s=1
- 动力学用**后向欧拉**离散（10a/11a）；机器人侧通过质心动量矩阵 `h^r = A(q^r) v^r` 与全身动力学一致；对象侧用 `𝒲_ext = 𝒢𝒱̇ − [ad_𝒱]ᵀ𝒢𝒱`
- 力矩限位是**线性 torque-speed 包络**：`|τ_j| + (τ_max/v_{τ,max})|v_j| ≤ τ_max`（13c）—— 高速时可用力矩线性衰减到 0

### 2.4 搜索层（式 18 / 19）

```
v* = argmin_{u ∈ children(v)} [ J(u) − C·√( log(N(v)+1) / (N(u)+1) ) ]      (18)
M(v) = max{1, k·N(v)^α}      k=1.0, α=0.5, C=3                            (19)
```

**直觉**：注意是 **argmin** 且第二项带负号——这是“代价越低越 exploitation，访问越少越 bonus”的 cost-based UCT 变体（不是 reward 版 UCB1）。progressive widening 让子节点上限随访问数增长，避免一开始就把 108 个分支全展开。

---

## 3 · 带数字走一遍

> 以下两段是**玩具设定**上的推算，用来验证量级；所有论文数值均逐字取自 Table I / II / IV。

### Toy A：74.8× 的决策变量缩减是怎么来的

玩具机器人：`n = 6` 个驱动关节（q^r = 6 base + 6 joints = 12 维），`n_ee = 2`，`n_o = 1` 个可动对象。取 `K = 4` 个接触模式，每个模式 `20` 个 TO knot（与论文 §IV-A “Each mode in the TO is discretized using 20 optimization knots” 一致）。

TO 单个 knot 的变量数：

| 分量 | 维度 |
|---|---|
| x^r = (q^r, v^r, h^r) | 12 + 12 + 6 = **30** |
| u^r = (v̇^r, λ₁, λ₂) | 12 + 6 + 6 = **24** |
| x^o = (q^o, 𝒱^o) | 6 + 6 = **12** |
| u^o = (𝒱̇^o, 𝒲_env^o) | 6 + 6 = **12** |
| 合计 / knot | **78** |

- TO 总量 ≈ `4 × 20 × 78 = 6240`（再加 4 个 T̄_s）
- KSO：`K+1 = 5` 个位形 × (robot q^r 12 + object q^o 6) = `5 × 18 = 90`
- 比值 `6240 / 90 ≈ 69.3×`

论文实测的 Avg 决策变量缩减是 **74.8×**（range 74.4–74.9）——玩具模型复现到同一量级 ✓。

时间侧的对数检查：Avg TO **64.70 s** ÷ Avg KSO **0.60 s** ≈ **108×**，正对原文 “approximately two orders of magnitude faster”。

### Toy B：为什么必须剪枝，而不能枚举

Table IV 给出允许接触，最大分支因子 **108**；§IV-B 的树最大深度 **5 switches**。

- 完整深度-5 序列数：`108⁵ = 14,693,280,768 ≈ 1.47×10¹⁰`
- 若每条都跑一次 TO（Avg 64.70 s）：`1.47×10¹⁰ × 64.70 ≈ 9.5×10¹¹ s ≈ 3.0×10⁴ 年`
- 即便每条只跑 KSO（Avg 0.60 s）：`≈ 8.8×10⁹ s ≈ 280 年`

所以 2 小时（7200 s）预算内拿到 **26.4 ± 9.7** 个解（hard, M,E,KSO），靠的是 UCT + progressive widening + 缓存，**不是**枚举。

再看“每节点一次 TO”有多致命：`7200 / 64.70 ≈ 111`，即理论上限约 111 次 TO。实测 Easy 的 TO-only 变体跑了 **208.4 ± 8.3** 次 TO 尝试（>111），说明失败/短前缀序列的 TO 会提前退出，平均每次仅 ≈ `7200/208.4 ≈ 34.5 s`。而 hard 的 TO-only：**216.2 ± 5.5** 次 TO 尝试 → 只换来 **12.8 ± 2.2** 个树节点、**0.0 ± 0.0** 个解。

**这三个数字放一起就是全文的论点**：TO 的代价 × 接触空间的规模 ⇒ 不做分级剪枝，搜索根本到不了有解的区域。

---

## 4 · 工程视角

> 硬约束：以下每个数字都标注出处；论文没给的格子写「论文未报告」，绝不留白填猜。

| 项目 | 数值 | 出处 |
|---|---|---|
| **KSO 单次求解** | **0.14–1.93 s**（最小 `Toss to Table` **0.14**；最大 `Climb 2` **1.93**），Avg **0.60 s** | Table I |
| **TO 单次求解** | **9.73–117.62 s**（最小 `Toss to Table` **9.73**；最大 `Triple Catch` **117.62**），Avg **64.70 s** | Table I |
| 决策变量缩减（TO→KSO） | **74.4–74.9×**，Avg **74.8×** | Table I |
| 约束**类型**覆盖（KSO vs TO） | **69.1–71.3 %**，Avg **70.0 %** | Table I |
| 时间/空间加速比（作为分类器） | **2.4–15.5×**（4 个 LLM 场景） | Table III |
| 搜索单次预算 | **2 h / run**，**5** 个 seed | §IV-B |
| 树深上限 | **5 switches** | §IV-B |
| 分支因子 | **108** | §IV-B, Table IV |
| TO knot 密度 | 每 mode **20** 个优化 knot | §IV-A |
| LLM 采样规模 | 每 prompt **100** 条计划 × **5** 次重复 | §IV-C |
| **求解硬件（CPU/GPU 型号、核数）** | **论文未报告** | — |
| **内存 / VRAM 峰值** | **论文未报告** | — |
| **RL tracker 控制频率** | **论文未报告** | — |
| **端到端 wall-clock（含 LLM 调用）** | **论文未报告** | — |
| **单次 mode/edge IK 耗时** | **论文未报告**（Table I/II 只给 KSO、TO） | — |

**表下注（易错点）**：KSO 时间的下界是 `Toss to Table` 的 **0.14 s**，不是 `Climb 1` 的 `0.34 s`；`0.34 s` 只是 8 条序列里第 1 条的值，`1.93 s` 才是上界（`Climb 2`）。8 个值逐字为：`0.34 / 1.93 / 0.37 / 0.90 / 0.14 / 0.31 / 0.42 / 0.43`。

### 换算（作者未给的派生量，标 `DERIVED`）

| 派生量 | 计算 | 结果 |
|---|---|---|
| hard / M,E,KSO 每节点均摊时间 | 7200 s ÷ 814.6 nodes | ≈ **8.8 s / node** `DERIVED` |
| hard / M,E,KSO 平均出解间隔 | 7200 s ÷ 26.4 sols | ≈ **273 s / sol** `DERIVED` |
| TO-only 的 TO 吞吐 | 7200 s ÷ 216.2 TO attempts | ≈ **33.3 s / TO attempt** `DERIVED`（低于 Avg 64.70 s，因早期失败提前退出） |
| Easy / KSO 首次出解 | 表中直接给出 | **192 ± 96 s** |

### 部署约束的 trade-off

1. **这不是机载实时算法**。TO 的 Avg 64.70 s 已经和“在线”无关；真实部署形态是 **离线/准离线规划 + 冻结的 RL tracker 执行**（论文即如此：`Pick Place 1/2`、`Toss to Table`、`Double Catch`、`Triple Catch`、`Juggle` 六条上机，见 Fig. 1 的 Double Catch）。
2. **算力被 NLP 求解器吃满**。整条栈是 CasADi [25] 建模 + acados SQP [26]（KSO）/ Hippo SQP [27]（TO）/ Ipopt [28]（mode-edge）+ Pinocchio [24]（刚体动力学）+ coal [22]（GJK 距离）。工程上要部署，等于要在一个目标机上把这三套求解器都编出来（论文未报告目标机型号）。
3. **KSO 是“亚秒级”，但 8.8 s/node 的实测均摊远大于 0.60 s**。差额来自 TO（在 goal 处）和 1415 次 KSO 尝试的叠加——**优化单次 KSO 延迟的边际收益，低于降低 KSO 调用次数（即缓存命中率）的收益**。
4. **分支因子 108 决定了 horizon 的成本斜率**。深度从 5 加 1，搜索空间 ×108；论文把长时程问题外推给 TAMP/program search [31]，等于承认这套东西在 depth 维上不可扩展。
5. **精度换速度是有明确边界的**：KSO 丢掉的是**动力学**这类约束，所以它能保证“几何/接触/限位可行”，不能保证“力矩够、摩擦锥内、不翻倒”——后者必须由 TO 兜底（FPR 数据见 §6）。

---

## 5 · 数据与评测

> 本文**无公开数据集、无标准 benchmark**；全部是自建场景与自建任务。以下名称与数字逐字来自原文表格。

### 5.1 三组实验的设置

**Setting 1（§IV-A）定性 + 上机：人工指定接触序列**

- 8 条人工设计的接触序列，长度与复杂度递增：`Climb 1`、`Climb 2`、`Pick Place 1*`、`Pick Place 2*`、`Toss to Table*`、`Double Catch*`、`Triple Catch`、`Juggle*`（`*` = 额外上真机）
- 每条 mode 在 TO 里用 **20** 个优化 knot 离散
- 度量：TO 时间、KSO 时间、**decision-variable reduction（TO→KSO）**、**constraint coverage**（= KSO 中出现的 TO **约束类型**占比）
- 上机执行用 RL-based trajectory-tracking controller [19]

**Setting 2（§IV-B）可行性引导树搜索**

- 场景：**两个 box-placement 变体**（Fig. 4），任务是把白盒子放到平台上；两变体**共享同一接触模式搜索空间**，但运动学/动力学难度不同（easy / hard）
- 5 个 seed × **2 h** 预算 × 最大深度 **5** switches
- baseline：**TO 作为唯一可行性检查的树搜索**，作者明确称其 “similar to the exploration strategies used in [8,9,10]”
- 分支因子 **108**（由 Table IV 的允许接触表推出）

**Setting 3（§IV-C）LLM 接触计划采样**

- 生成器：**GPT-5.5 [29]**；每场景每 prompt 生成 **100** 条多样化接触计划，同 prompt 重复 **5** 次
- 4 个场景：`1-a`、`1-b`、`2-a`、`2-b`（`-b` 比 `-a` 更难）
- 每条计划**同时**解 KSO 与 TO，把 KSO 当作“TO 可行性分类器”，报 FNR / FPR / 加速比

### 5.2 结果（逐字）

**Table I（8 条人工序列）**

| Task | K | TO [s] | KSO [s] | Dec-var ↓ | Constraint cov. [%] |
|---|---|---|---|---|---|
| Climb 1 | 6 | 50.59 | 0.34 | 74.9 | 70.2 |
| Climb 2 | 11 | 106.01 | 1.93 | 74.4 | 70.6 |
| Pick Place 1* | 6 | 21.36 | 0.37 | 74.9 | 70.2 |
| Pick Place 2* | 11 | 83.40 | 0.90 | 74.9 | 71.3 |
| Toss to Table* | 4 | 9.73 | 0.14 | 74.9 | 70.2 |
| Double Catch* | 8 | 91.53 | 0.31 | 74.9 | 69.1 |
| Triple Catch* | 11 | 117.62 | 0.42 | 74.9 | 69.1 |
| Juggle* | 10 | 37.33 | 0.43 | 74.9 | 69.1 |
| **Avg.** | **8.4** | **64.70** | **0.60** | **74.8** | **70.0** |

**Table II（树搜索，2 h/run，5 seeds）**

| Metric | Easy: KSO | Easy: M,E,KSO | Easy: M,E,KSO,TO | Easy: TO | Hard: KSO | Hard: M,E,KSO | Hard: M,E,KSO,TO | Hard: TO |
|---|---|---|---|---|---|---|---|---|
| No. sol. | 73.6 ± 19.7 | **83.8 ± 6.5** | 8.0 ± 3.7 | 20.0 ± 5.0 | 0.4 ± 0.9 | **26.4 ± 9.7** | 1.2 ± 0.8 | 0.0 ± 0.0 |
| Time to first sol. [s] | 192 ± 96 | 194 ± 74 | 1455 ± 989 | 951 ± 583 | 2671 ± n/a | 2763 ± 1549 | 5399 ± 868 | n/a |
| KSO attempts | 410.6 ± 27.1 | 410.0 ± 18.7 | 230.8 ± 16.4 | 0.0 ± 0.0 | 1660.8 ± 55.4 | 1415.0 ± 77.4 | 437.4 ± 13.0 | 0.0 ± 0.0 |
| TO attempts | 182.0 ± 4.2 | 176.2 ± 7.4 | 223.0 ± 13.6 | 208.4 ± 8.3 | 5.4 ± 2.4 | 79.6 ± 7.3 | 164.0 ± 13.8 | 216.2 ± 5.5 |
| Total tree nodes | 393.8 ± 24.3 | 380.8 ± 22.3 | 90.6 ± 5.5 | 87.8 ± 12.2 | 218.2 ± 24.0 | **814.6 ± 78.9** | 52.8 ± 7.7 | 12.8 ± 2.2 |

**Table III（LLM 计划，KSO 当分类器）**

| Metric | 1-a | 1-b | 2-a | 2-b |
|---|---|---|---|---|
| KSO-feas. | 30.8 ± 11.1 | 4.6 ± 6.4 | 47.0 ± 9.9 | 20.6 ± 28.0 |
| TO-feas. | 8.8 ± 5.0 | 0.4 ± 0.9 | 10.2 ± 8.0 | 2.8 ± 5.7 |
| FNR [%] ↓ | 0.0 ± 0.0 | 0.0 ± 0.0 | 1.3 ± 2.6 | 0.0 ± 0.0 |
| FPR [%] ↓ | 24.2 ± 10.4 | 4.2 ± 5.8 | 41.4 ± 8.3 | 19.5 ± 26.1 |
| Speedup [×] ↑ | 3.8 ± 1.4 | 15.5 ± 10.2 | 2.4 ± 0.5 | 7.4 ± 4.3 |

**Table IV（允许接触，相对初始场景状态；分支因子 108 的来源）**

| Interface | Allowed contacts |
|---|---|
| Left hand | box left, box front, free |
| Right hand | box right, box rear, free |
| Left foot | floor, free |
| Right foot | floor, free |
| Box | bottom, floor, tabletop, free |

### 5.3 读这些数字时必须讲清的条件

- **“Constraint coverage 70.0%” 是约束**类型**级别的覆盖，不是约束实例数**——原文定义是 “the fraction of TO constraint types represented in the KSO”。丢掉的正好是动力学那一类（作者原文点名）。
- **Table I 的 TO 时间跨了 12×**（9.73 → 117.62），且与模式数 K **不单调**（K=11 的 Climb 2 是 106.01，K=4 的 Toss to Table 只有 9.73），说明任务本身的难度/初值质量主导了求解时间。
- **两种任务变体只差难度，不差搜索空间**（“same contact-mode search space but different levels of kinematic and dynamic difficulty”）——所以 easy/hard 的对比是**难度的对照实验**，不是场景泛化实验。
- **FPR 与 FNR 不可兼得地看**：FNR 几乎为 0，但 FPR 高达 **41.4%**（2-a）。也就是说 KSO 的“通过”有接近一半是假的——它的价值在**不杀真解**，不在**替 TO 做最终裁决**。
- **论文未报告**：场景的 CAD/质量/摩擦系数取值、真机型号与关节数、tracker 的跟踪误差指标、以及任何与其他接触规划器的**外部**横向对比数字（唯一对比对象是自建的 TO-only baseline）。

---

## 6 · 能力与失败模式

### 6.1 能做（具体）

- **给定接触序列 → 动力学一致的全身体多接触轨迹**，且**同时包含可动对象**（状态里显式带 q^o、𝒱^o，动力学含 `𝒢𝒱̇ − [ad_𝒱]ᵀ𝒢𝒱`）。
- **动态、非周期的 loco-manipulation**：`Toss to Table`、`Double Catch`、`Triple Catch`、`Juggle` 这类带抛接/多次接续的任务，都是 4–11 个模式的序列，TO 可解且能上机（`*` 标记的 6 条）。
- **三种候选生成器都能接**：UCT 树搜索、LLM（GPT-5.5）采样、人工指定——同一个过滤器接口 ℱ 换着插。
- **在 hard 场景下把“搜不到”变成“搜得到”**：TO-only 在 hard 上 `0.0 ± 0.0` 个解，M,E,KSO 拿到 `26.4 ± 9.7`。
- **假阴性控制得当**：LLM 场景 FNR `0.0/0.0/1.3/0.0` %，代价是 FPR 偏高。

### 6.2 不能做 / 会失败（具体）

- **非平面矩形 patch 接触**。作者自陈：“The current formulation assumes planar contact interfaces”。点接触、线接触、曲面/软体接触都需要重写 (7a)–(7d)，作者指向可微 SDF [30]。
- **滑动接触 / 双向接触**。原文：“though other contact modalities, such as sliding or bilateral contact, could be incorporated”——即当前**未**纳入。
- **长时程任务**。深度 5 switches、分支 108 已是 2 h 预算下的实际上限；作者把更长 horizon 外推给 TAMP / program search [31]。
- **动力学不可行的“假通过”**。KSO 无动力学项，FPR 最高 `41.4 ± 8.3` %（2-a）——若把 KSO 当最终裁决，会产出力矩不足/摩擦锥外的序列。
- **对求解器初始化敏感**。原文把少数假阴性归因于 “poor initialization or insufficient solver iterations in the KSO”——可行性判定带求解器语义，不是纯数学判定。
- **不能保证搜索最优/完备**。2 h 预算 + UCT + progressive widening 是 anytime 的；Table II 里 `Time to first sol.` 在 hard 上到 `5399 ± 868` s，接近预算的 75%。
- **未评测闭环**：推挤/扰动后的重规划、tracker 跟踪误差、失败恢复——**论文未报告**。

### 6.3 隐含假设 (Hidden Assumptions)

1. **接触界面集 ℐ 已知且静态**。§II-A 直接把 ℐ 当作场景给定的索引集，Table IV 甚至把“允许接触”写成一张离线表。场景一变（门被推开、箱子被换个位置），ℐ 与允许表就得重建——论文未报告任何在线感知/更新机制。
2. **每个 interface 同时只能有一个接触伙伴**。模式定义里 `∀a ∈ ℐ ∃! b ∈ ℐ ∪ {∅}`：一只手不能同时贴两个面，盒子底边不能同时压地板和桌沿。这条硬约束会**结构性排除**某些真实可行的接触构型。
3. **一个接触模式内只有一个时间缩放因子 T̄_s**。所以 mode 内部不能变速（不能“先慢后快”地推），所有 knot 共享同一 Δt 缩放。
4. **几何用凸体 + 有符号距离近似**（式 9，Schulman 近似 + GJK/coal）。凹形物体必须预先凸分解；近似误差直接进约束。
5. **质量、惯量 𝒢、摩擦系数 μ 与 μ_r 已知且恒定**，且对象按刚体处理。论文未报告这些参数的取值或标定流程。
6. **“不可行”= 求解器在最大迭代内未收敛**。这是判据层面的假设，也是 FNR 非零的根源；换 solver / 换 tolerance / 换初值都会改变判定结果。
7. **可行性可缓存，即只依赖 (mode) 或 (edge)**。但式 (14) 的目标含 `‖q − q_nom‖²_W`，`q_nom` 是全局名义位形，**与到达该 mode 的前缀状态无关**。真实系统里“同一个抓取模式在前缀 A 下可行、前缀 B 下不可行”是常态。
8. **三级可行集是嵌套的**。作者原文：期望可行性集合嵌套，但 “a formal proof of this property is left to future work”。整个剪枝正确性建立在这个未证明的前提上。
9. **生成的轨迹可被冻结的 RL tracker 跟踪**（[19]）。论文以“上机成功 + 视频”作为证据，但**未报告跟踪误差/成功率指标**。

---

## 7 · 与相关工作对比

| 方法族 | 代表（本文引用） | 接触表示 | 如何处理组合爆炸 | 需要参考动作 | 本文与其关系 |
|---|---|---|---|---|---|
| 混合整数接触优化 | [11,12,13] | 二进制接触变量 | 求解器处理 MI 结构 | 否 | 本文把自己定位为“对混合整数放松”路线的进一步加速 |
| 离散接触序列搜索 + TO | [7,8,9,10] | 显式模式序列 | 限制搜索（简化模型/启发式/高层动作） | 否 | **本文的 baseline**（“similar to the exploration strategies used in [8,9,10]”）；hard 上 `0.0 ± 0.0` 解 vs 本文 `26.4 ± 9.7` |
| RL 运动 | [4] | 隐式（策略里） | 不搜索，靠 reward shaping | 否（但需大量 shaping） | 本文不用 RL 做规划，只用冻结的 RL tracker [19] 执行 |
| 示范跟踪 | [16] | 隐式 | 绕过探索 | **是** | 本文目标是“不依赖参考动作”地发现新行为 |
| 人→人形重定向 | [17,18,19] | 隐式 | 绕过探索 | **是** | 同上；[19] 被本文用作执行控制器 |
| LLM 接触计划生成 | [29] (GPT-5.5) | 文本/符号计划 | 不处理（只负责多样性） | 否 | 本文把 LLM 当**采样器**，用 KSO 补上它缺的可行性判定（Speedup 2.4–15.5×，FNR ≈ 0） |
| **FARO（本文）** | — | 显式模式序列 + patch 接触 | **三级必要条件滤波 + 缓存 + cost-based UCT** | 否 | 在 hard 树上把展开节点数从 `12.8 ± 2.2` 提到 `814.6 ± 78.9` |

**唱反调的一处细节**（读表要抓的）：论文说“searches using the proposed feasibility filters outperform the TO-only baseline in solution discovery and tree expansion”，但在 **Easy** 任务上，含 TO 的完整版 ℱ₃=(M,E,KSO,TO) 只找到 `8.0 ± 3.7` 个解，**低于** TO-only 的 `20.0 ± 5.0`。“优于 baseline”这句话实际由 ℱ₂=(M,E,KSO) 的 `83.8 ± 6.5` 撑起来——即**把 TO 从节点扩展里彻底移除**才是收益来源，而不是“加了过滤器”。

### 🎯 面试 Tip

被问“这篇的核心贡献是什么”，**别说“用了 LLM”或“用了树搜索”**——那都是外挂。一句话答：

> “它把‘轨迹优化可行’拆成一串**必要条件**：mode/edge IK ⊂ KSO ⊂ TO。三级用的是**同一套接触/碰撞/限位约束**，只改优化变量和离散粒度，所以 KSO 保留了 70% 的约束类型却少 74.8× 的决策变量、快两个数量级（0.60 s vs 64.70 s）。配上 feasible/infeasible 缓存，搜索从‘每个节点一次 TO’变成‘每个节点一次 KSO，只在 goal 处补一次 TO’，hard 任务上节点数 12.8→814.6、解数 0→26.4，代价是 KSO 的假阳性高达 41.4%（假阴性≈0）。”

接着如果被追问“有什么坑”，直接给：**FPR 41.4% 意味着 KSO 不能当最终裁决；而假阴性主要来自求解器初始化，说明‘可行性’这个词在这里是求解器语义而非数学语义。**

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-31)

**Repo 状态（诚实声明）**：全文只出现视频链接 `https://youtu.be/R6qCHoCormQ`，**未出现任何 `github.com` 链接**，因此**官方代码 repo 未在论文中给出**；无 issue 流可查。以下 3 条 pitfall 全部由 **§6 的失败模式 + §II 的具体方法约束** 推导，**未经任何 issue 验证**。

### P1 · 把 KSO 的 “pass” 当成 “可行” → 直接掉进 41.4% 的假阳性

- **来源失败模式（§6.2）**：KSO 省略动力学约束，FPR 最高 `41.4 ± 8.3` %（Table III, 场景 2-a）。
- **方法约束（§II-E, 式 15）**：KSO 的约束表里**没有** `dyn(...)=0`，也没有 λ、τ，只有 contact/collision/limits + 一个正则项 `‖q_s − q_nom‖²_W`。
- **机械后果**：任何“只用 ℱ₁=(KSO) 或 ℱ₂=(M,E,KSO) 就宣布成功”的复现，会把大量力矩不足/摩擦锥外的序列交给下游。论文自己靠 Algorithm 1 第 15–19 行（`Goal(𝒞⁺)` 为真时补一次 `TrajectoryOpt.`）兜住，**这一步不能省**。另外注意 Table II 里 ℱ₂ 的 `TO attempts` 在 hard 上是 `79.6 ± 7.3`——这些正是 goal 处的补验证调用。

### P2 · 缓存的 “infeasible” 是求解器状态，不是数学事实 → 换配置即失效

- **来源失败模式（§6.2 / §6.3-6）**：原文把少数假阴性归因于 “poor initialization or insufficient solver iterations in the KSO”。
- **方法约束（§II-D + Alg. 1）**：“A contact mode c is said to be infeasible if the resulting nonlinear program does not converge within a number of maximum iterations”；且结论写入 `𝒦_infeas` 后被永久复用。
- **机械后果**：调 Ipopt [28] 的 `max_iter`/`tol`、换初值、换机器/换编译选项，都会改变 `𝒦_infeas` 的内容。**跨配置复用缓存 = 静默引入假阴性**；在同一进程内则会出现“先跑一遍得到 26.4 个解，重启后同样的 seed 得到不同解数”的不可复现现象。

### P3 · mode/edge 缓存忽略前缀状态，而 (14) 只按 `q_nom` 正则化 → 窄通道场景下会误杀

- **来源失败模式（§6.3-7）**：可行性被假设为只依赖 `(c)` 或 `(c₁∪c₂)`。
- **方法约束（§II-D, 式 14）**：目标函数是 `(q − q_nom)ᵀW(q − q_nom)`，`q_nom` 是**全局名义位形**，式中**没有任何**来自父节点 `𝒞(v)` 或当前 robot/object 状态的项；而 Alg. 1 的 `Verify` 直接把 `M(c⁺)`/`E(c(v), c⁺)` 的结果塞进共享缓存。
- **机械后果**：在窄通道/高遮挡场景，同一接触模式在前缀 A 下可行、前缀 B 下不可行（因为要绕过的障碍不同），但缓存给出同一个结论。表现为搜索在某个分支上反复被“已知不可行”挡住，而该分支在 TO 层面其实存在解。复现时的验证方法：关掉 `𝒦_infeas` 只留 `𝒦_feas` 跑一遍 hard 任务，看解数是否变化（论文未报告此消融）。

### P4 · 分支因子 108 × depth 5 是硬编码的预算契约，改任一常量都会让 2 h 预算失效

- **来源失败模式（§6.2）**：长时程任务不可行，作者外推给 TAMP [31]。
- **方法约束（§IV-B + Table IV）**：`max depth of 5 switches`、分支因子 `108`、`C=3`、`k=1.0`、`α=0.5`（式 19 的 progressive widening）。Table IV 每多一个 allowed contact 选项，分支因子就乘性增长（108 = 3×3×2×2×3）。
- **机械后果**：给机器人加一个末端执行器、或允许“手同时贴两个面”，分支因子立刻翻数倍；此时 2 h 预算下 UCT 会退化为只探浅层（对比 hard/ℱ₃ 的 `52.8 ± 7.7` 节点——连 108 都没探完一层）。**任何“我们照着跑但加了几个接触选项”的复现都会看到解数断崖，而这不是 bug，是预算契约被破坏。**

---

[← Back to Motion Planning & Loco-Manipulation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（截断版）· 未在真机复现的数字标 `UNVERIFIED`；标 `DERIVED` 的为本文对论文报告值的换算，非原文直接给出。§4 中「论文未报告」项（求解硬件、内存、控制频率、mode/edge IK 单次耗时）在原文中确实缺失，切勿在二次引用时补数。§8 无官方 repo 可校验。

[//]: # "<!-- source: https://arxiv.org/abs/2607.18362 -->"
