[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->"

# 学习机器人元推理：自适应实时控制计算预算 (Learning Robot Metareasoning: Adaptive Computation Budgets for Real-Time Control)

> **发布时间**：2026-10-16（arXiv:2610.23662v1 [cs.RO]）
> **论文 / 模型名**：Learning Robot Metareasoning（预算策略 Φ_θ）
> **核心定位**：把"该想多久"从部署前拍死的超参数变成一个**在线决策**——用 semi-MDP 把开环执行块长 h 与求解器计算预算绑成同一个动作，再用 PPO 从经验里学出来，在导航/缆挂四旋翼/接触操作三个域上匹配或超过所有固定预算基线。

导语：机器人"边动边规划"时，为了给求解器留出计算时间，必须闭着眼执行一段开环动作块（action chunk）；块越长，规划越好，但反馈越稀。现有控制器把这个块长在部署前写死。本文指出**最优计算时间本质上是状态的函数**（非建模动态、安全约束边界、边际优化收益都会改变它），静态调参必然在某些关键时刻"失明"。作者把预算选择写成 semi-MDP，并给出"物理价值计算（physical value of computation）"的一行定义。

---

## X-Ray 开场

传统 metareasoning 把世界当作在思考期间**冻结**，所以必须由设计者手写一个"思考的时间惩罚"来权衡收益。本文的洞见是：对具身智能体，世界不冻结——机器人在求解器思考时继续漂移，**物理本身已经替你收了费**，因此那个启发式惩罚项根本不需要。于是"该分配多少计算"就是一个标准 RL 问题：动作是块长 h ∈ &#123;1,…,h_max&#125;，回报是这 h 步的真实环境回报，折扣按**流逝的物理时间** γ^h 打。对 spatial AI 研究者，它给了一个可复用的工程配方——**用求解器自身的统计量（ESS、time-to-infeasibility、模型失配）作为策略输入，让"这个问题现在有多难"变得可观测**。

---

## 📍 研究全景时间线

```
 实时MPC(h=1)      事件/自触发MPC      metareasoning / VOC         [21] 预算化 options      ★ 本文
 [7,8]             [16,17]            [5,6,18,19,20]              (离散博弈)                (2026)
    │                 │                    │                          │                      │
    ▼                 ▼                    ▼                          ▼                      ▼
 每步都解          省算力, 但求解器      显式给"思考"定价,           semi-MDP, 但需要        连续控制 +
 反馈最快          被当作 oracle         世界冻结                  额外 reflex 策略         physical VoC
 预算最紧          (多给时间不涨质量)    (经济价值 of computation)                          + 三域真机
    │                 │                    │                          │                      │
    └─────────────────┴────────────────────┴──────────────────────────┴──────────────────────┘
                                      固定的"执行承诺长度 h"
        action chunking: RTC[12] / DEFLECT[13] / 自适应长度[14] / 多候选[15]  ← 全部与预算解耦
```

**本文位置**：第一次把"执行承诺长度"与"求解器计算预算"显式**耦合为同一个决策变量**，并在连续时间、连续状态的机器人任务上端到端学习。

**本文局限（先摆出来）**：① h_max 仍需人按 Theorem 1 保守设定，ε/δ/L_P/e_0 实测不可得；② 要求求解器是"单调改进"型且 wall-clock ∝ h；③ 在 PushT 上退化为常数 h̄ = 8.00（作者归因于 nominal 设定下无可利用的预算变化）；④ 每个域单独训一个策略，非通才。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **预算策略 Φ_θ** | z_k = (s_&#123;t_k&#125;, h_&#123;k−1&#125;, τ_k, 𝔟_k) ∈ 𝒮 × ℋ × 𝒯^&#123;H(h_&#123;k−1&#125;)&#125; × ℝ^l | h_k ~ Cat(ℋ)，ℋ = &#123;1,…,h_max&#125; | 训练：PPO 采样；推理：单次前向，2 层 tanh MLP（128 units/layer），categorical actor + scalar critic |
| **求解器 ψ_h** | s_&#123;t_k&#125;，预算 h_k（horizon 与样本数随 h 缩放） | 动作块 τ_&#123;k+1&#125; ∈ 𝒯_h | 无学习；MPPI（导航、缆挂）、CEM（PushT）；JAX 实现 + MuJoCo MJX |
| **求解器统计 𝔟_k** | rollout bundle + 最新执行反馈 | 固定维 ℝ^l：ESS、time-to-infeasibility、dynamics-model mismatch | 推理期在线计算，**不额外调用 planner** |
| **SMDP 回报 R(s_&#123;t_k&#125;, h_k)** | 块内 h_k 步的 ρ = r + g·δ_&#123;s∈G&#125; | 折扣和 Σ_&#123;j=0&#125;^&#123;h_k−1&#125; γ^j ρ | 训练期由环境累积；推理期不计算 |
| **PPO + duration-aware GAE** | (z_k, h_k, R_k, τ_k, z_&#123;k+1&#125;) 一条 transition = **一个 epoch** | 策略梯度更新 | δ_k = R_k + γ^&#123;h_k&#125; V(z_&#123;k+1&#125;) − V(z_k)；A_k = δ_k + γ^&#123;h_k&#125; λ A_&#123;k+1&#125; |

### 1.2 关键机制

**⚡ Eureka Moment：在连续时间里，"思考的代价"不需要人为定价——机器人一边算一边漂移，物理已经在收费；所以块长 h 不是超参数，而是一个 semi-MDP 动作，它的 Q 值就是 physical value of computation。**

由此派生三个直接后果：

1. **不需要 reflex 策略**。对比 [21] 需要在开环期额外跑一个反射策略，本文让同一个 ψ_h 产出的 chunk 直接开环执行——因为"执行的就是规划结果"，没有额外的行为库要发现（Remark 2：高层动作是**时长**，不是**行为**）。
2. **折扣必须按物理时间**。若沿用 per-epoch 的 γ，长 chunk 会被系统性低估代价（见 §3 玩具算例）。
3. **策略输入必须包含"求解器有多确定"**。仅凭状态 s 无法区分"这条路看起来一样但搜索已经收敛"与"搜索还在乱撞"——𝔟_k 正是把这层不可见于状态的信息暴露出来。消融显示去掉它成功率从 98% 掉到 86%。

### 1.3 信息流

```
        ┌──────────────────────── epoch k ────────────────────────┐
        │                                                          │
 s_{t_k}┤                                                          │
   │    │   z_k = ( s_{t_k}, h_{k-1}, τ_k , 𝔟_k )                 │
   ├────┼──────────────► Φ_θ (2×128 MLP) ──► h_k ~ Cat({1..h_max})│
   │    │                                          │               │
   │    │                        ┌─────────────────┘               │
   │    │                        ▼                                 │
   │    │      ╔═════════════ 并行执行 / 计算 ══════════════╗        │
   │    │      ║  开环执行 τ_k 共 h_k 步（h_k · dt 秒）      ║        │
   │    │      ║  同时 ψ_{h_k}(s_{t_k}) 用 h_k 的预算算 τ_{k+1}║     │
   │    │      ╚═══════════════════════════════════════════╝        │
   │    │                        │                                 │
   └────┼────────► t_{k+1} = t_k + h_k , 刷新 𝔟_{k+1} 与 τ_{k+1}    │
        └──────────────────────────────────────────────────────────┘
```

注意图中**没有反馈通路**穿过 "并行执行" 框：块内 h_k 步是真开环的，这正是约束 (C1) 的来源，也是 Theorem 1 要量化的对象。

---

## 2 · 数学核心

📌 **Napkin Formula**

$$h_k^\star=\arg\max_{h\in\mathcal{H}}\ \Phi^{\mathrm{VoC}}_{\mathrm{rel}}(s_{t_k},h,1),\qquad Q^\Phi(s,h)=R(s,h)+\gamma^{h}\,\mathbb{E}\big[V(s')\big]$$

一句话：**"多给 h 步预算值不值"= 这块的回报 + 按流逝时间打折后的未来 − 立刻反应（h=1）的价值。**

### 2.1 SMDP 目标

底层 MDP ℳ = (𝒮, 𝒜, 𝒫, r, γ, g)，控制周期 dt 固定。求解器 ψ_h : 𝒮 → 𝒯_h = 𝒜^h 单调改进（多给时间不会变差）。semi-MDP 𝔠 = (𝒵, ℋ, ℳ, ψ_h)，决策 epoch k = 0,1,2,…：

$$h_k\sim\Phi_\theta(\cdot\mid z_k),\quad \Phi_\theta:\mathcal{Z}\to\Delta(\mathcal{H}),\qquad t_{k+1}=t_k+h_k$$

epoch 回报与目标：

$$R(s_{t_k},h_k)=\sum_{j=0}^{h_k-1}\gamma^{j}\big[r(s_{t_k+j},a_{t_k+j})+g(s_{t_k+j})\delta_{s_{t_k+j}\in G}\big]$$

$$\mathrm{P}_{\mathfrak{C}}:\ \max_{\Phi_\theta}\ \mathbb{E}_{\mathcal{P}_{\mathcal{M}}^{\Phi_\theta,\psi_h}}\Big[\sum_{k\ge 0}\gamma^{t_k}R(s_{t_k},h_k)\Big],\qquad Q(s_{t_k},h_k)=R(s_{t_k},h_k)+\gamma^{h_k}\mathbb{E}\big[V(s_{t_{k+1}})\big]$$

**变量**：γ 折扣；h_k 既是执行长度也是预算；γ^&#123;h_k&#125; 是**按物理时间**的 bootstrap 折扣（不是按 epoch 数）。

### 2.2 等价性（Remark 1）——为什么优化"何时思考"就是在优化原问题

若 r、g 有界、γ ∈ (0,1)，则对任意 Φ_θ 与 s_0：

$$\mathbb{E}_{\mathcal{P}_{\mathcal{M}}^{\Phi_\theta,\Psi}}\Big[\sum_{k\ge0}\gamma^{t_k}R(s_{t_k},h_k)\Big|s_0\Big]=\mathbb{E}_{\mathcal{P}}\Big[\sum_{t\ge0}\gamma^{t}\rho(s_t,a_t)\Big|s_0\Big]$$

**直觉**：epoch 区间 I_k = &#123;t_k,…,t_&#123;k+1&#125;−1&#125; 是环境时间的严格不相交划分，R 是 ρ 在该区间上的精确折扣和，逐路径相加即还原无限时域回报。所以这是**精确重构**，不是 surrogate。

### 2.3 开环漂移上界（Theorem 1）——h_max 该定多少

**Assumption 1**：ρ 对状态 L_ρ-Lipschitz；真实核与求解器标称核的单步失配 W_1(P, P̂) ≤ δ；标称动态在 W_1 下 L_P-Lipschitz。

**递推**：由 Kantorovich–Rubinstein 对偶，期望状态偏差 e_j ≔ 𝔼‖s_&#123;t_k+j&#125; − ŝ_&#123;t_k+j&#125;‖ 满足 e_j ≤ L_P e_&#123;j−1&#125; + δ，展开得

$$e_j\le L_P^{\,j}e_0+\delta\sum_{i=0}^{j-1}L_P^{\,i}$$

于是块内累计回报偏差被下式界住：

$$B(h)\coloneqq L_\rho\sum_{j=0}^{h-1}\gamma^{j}\Big(L_P^{\,j}e_0+\delta\sum_{i=0}^{j-1}L_P^{\,i}\Big)\ \le\ \epsilon$$

**关键细节**：e_0 ≠ 0 且**是被继承来的**——τ_k 是在上一个预算 h_&#123;k−1&#125; 执行期间算出来的，新 chunk 从**预测状态** ŝ_&#123;t_k&#125; 出发，起点就已经偏了。所以 B(1) = L_ρ e_0，h̄(ε, e_0) 只在 ε ≥ L_ρ e_0 时才存在。B(h) 非降（非负项求和），故 &#123;h : B(h) ≤ ε&#125; 是 ℕ_&#123;≥1&#125; 的初始段，其上确界即 h̄。**工程结论：h_max ≤ h̄(ε, e_0)。**

### 2.4 优化

PPO over decision epochs，duration-aware GAE：

$$\delta_k=R_k+\gamma^{h_k}V(z_{k+1})-V(z_k),\qquad A_k=\delta_k+\gamma^{h_k}\lambda A_{k+1}$$

**Proposition 1（单调改进）**：令 P̃(z'|z,h) ≔ γ^&#123;h−1&#125;P(z'|z,h)，剩余质量 1−γ^&#123;h−1&#125; 送到吸收零回报态，则 𝔠 变成标准 γ-折扣 MDP 且值完全相同（因 γ·γ^&#123;h−1&#125; = γ^h）。PPO 是 mirror learning 的实例，其更新对这类 MDP 单调改进；再由 Remark 1 转移到 P_ℳ。

---

## 3 · 带数字走一遍（玩具设定，数值自造，仅示范机制）

**设定**：γ = 0.99，导航 dt = 0.1 s，L_ρ = 1.0，L_P = 1.02（模型略"放大"误差），δ = 0.01，e_0 = 0.05（继承了上一轮规划时的投影误差）。

**(a) Theorem 1 怎么卡出 h_max。** 逐项代入 B(h)：

| h | γ^&#123;h−1&#125;L_P^&#123;h−1&#125;e_0（本步误差项） | δ·Σ 项（失配累积） | B(h) 累计 |
|---|---|---|---|
| 1 | 0.0500 | 0 | **0.0500** |
| 2 | 0.0505 | 0.0099 | 0.1104 |
| 3 | 0.0510 | 0.0198 | 0.1812 |
| 4 | 0.0515 | 0.0297 | **0.2624** |
| 5 | 0.0520 | 0.0396 | 0.3539 |
| 7 | 0.0535 | 0.0594 | 0.5683 |
| 9 | 0.0541 | 0.0792 | 0.8244 |

若可接受退化 ε = 0.3，则 h̄ = 4（B(4) = 0.262 ≤ 0.3，B(5) = 0.354 > 0.3）。**这就是"论文里 h_max = 9 是任务特定选择、不是普适常数"的具体含义**——把 L_P 从 1.02 调到 1.00（完美模型），B(h) 的增长立刻放缓，h_max 可以放大；实测拿不到 L_P 与 δ，就只能往小拍。

**(b) 为什么折扣必须按时间。** 若错误地用 per-epoch γ：一个 h = 9 的 epoch，其后续回报只被折扣 0.99¹ = 0.99；正确值应是 γ^9 = 0.99⁹ ≈ **0.9135**。差距 7.6%，且**偏差方向单一**——所有长 chunk 都被系统性高估，策略会退化到"永远多想"。这正是 duration-aware GAE 存在的理由。

**(c) 时间尺度的直观换算**（由论文报告的 dt 与 h 直接相乘，非实测延迟）：导航 h = 9 → 0.9 s 开环；缆挂四旋翼 dt = 0.02 s，h = 8 → **160 ms** 开环，也就是求解器必须在这 160 ms 内交付下一块；PushT dt = 0.04 s，h = 8 → 320 ms。

---

## 4 · 工程视角

| 项 | 论文报告值 |
|---|---|
| 计算硬件 | **single NVIDIA A100 GPU (40GB VRAM)**（"ensuring the solver's wall-clock latency strictly dictates the physical temporal cost of computation"） |
| 控制周期 dt | 导航 **0.1 s**；缆挂飞行 **0.02 s**；PushT **0.04 s** |
| 求解器单次 wall-clock 延迟 | **论文未报告** |
| 策略推理延迟 | **论文未报告** |
| 端到端 FPS / 吞吐 | **论文未报告** |
| 实际显存占用 | **论文未报告**（仅给出 A100 40GB 规格） |
| 策略网络 | 2 层 tanh MLP，128 units/layer；categorical actor + scalar critic |
| PPO 超参 | λ = 0.95，lr 3×10⁻⁴，minibatch 256，4 epochs，clip 0.2，grad clip 0.5；2500 updates × 2048 transitions/update |
| 求解器随 h 的缩放 | MPPI：prediction horizon ∝ h；samples ∝ h（导航）/ ∝ √h（缆挂）。CEM（PushT）：horizon 与 population 均 ∝ h |
| 中间件 | ROS 2；真机平台 DJI RoboMaster；仿真 MuJoCo + MuJoCo MJX；MPPI/CEM 全部 JAX 实现 |

**核心 trade-off（可推导，非实测）**：整个框架建立在一条硬契约上——**"为了负担 h 个控制周期的计算预算，求解器必须在 h·dt 内算完"**。这条契约有两个方向的风险：

1. **大 h 侧**：dt = 0.02 s 的缆挂任务，h = 8 只买到 160 ms。MPPI 的 samples ∝ √h 已经是在压这个账，但如果单次 MPPI 在给定样本数下的实际耗时超过 h·dt，块会在新计划就绪前跑完 → 隐式退化到 h=1 的行为，但策略以为自己还有 160 ms。论文未报告实测耗时，这条无法从文本验证。
2. **小 h 侧**：h = 1 买到 dt = 0.02 s 的计算窗口，而 JAX/MJX 的 JIT 与 kernel launch 开销近似常数，"预算 ∝ h"在 h→1 时越来越不像成立。而策略恰恰在**最关键的时刻**（merging lane 中 t ≈ 3 s 穿越交叉机器人）把 h 压到 h_min = 1——这是全系统最脆的一档。

**部署约束总结**：策略本身极轻（2×128 MLP + 分类头），瓶颈完全在求解器。A100 的选择说明作者把"计算预算 → 物理时间"这条映射当作硬约束来满足，而不是靠实时内核调优；换到 Jetson 类平台时，"预算 ∝ h" 的斜率会整体抬升，h_max 必须相应缩小——但这一点论文未讨论。

---

## 5 · 数据与评测

**数据组成**：无公开数据集、无标准 benchmark。三个自建域，刻意从不同物理维度施压"计算–反应"权衡：

| 域 | 环境 | 难点来源 | 求解器 |
|---|---|---|---|
| Holonomic 2D navigation | **真机 DJI RoboMaster** + 仿真；三个场景：barrier（固定墙 + 3 个随机障碍）、merging lane（1 个交叉机器人 + 3 个随机障碍）、highway（5 个横向移动障碍） | 全局最优 vs 动态障碍避让 | MPPI |
| Quadrotor with suspended cable payload | MuJoCo / MJX；two-goal slalom | 刚性欠驱动动态，staleness 由**开环发散**而非环境变化惩罚 | MPPI |
| Contact-rich planar manipulation（3D Push-T） | MuJoCo MJX + hydrax 模型；CEM | 接触切换使计划快速失效 | CEM |

**评测设置（条件，不只是结论）**：

- 指标：**task success rate**、**mean total return**（未折扣、含失败回合平均）、导航额外 **harshness** H = (L/D)[1 + log(1 + J_norm)]（L 路径长、D 起终点直线距离、J_norm 归一化 jerk；越低越好）、**optimality regret** Φ_rel^VoC(s_&#123;t_k&#125;, h*, h) = Φ_abs^VoC(s_&#123;t_k&#125;, h*) − Q^Φ(s_&#123;t_k&#125;, h)。
- 导航奖励：ρ = −‖p_t − p_g‖₂² − 3000·**1**_collision；成功或碰撞终止。
- 回合数：Fig. 4 池化 **300 randomised episodes**；**Table I 每场景 100 episodes**；Fig. 7 消融 **每变体 300 episodes**；缆挂 **每方法 20 episodes**；PushT **16 matched validation episodes / 600 steps**；Fig. 6 regret **10 episodes**。
- 固定基线集合：h ∈ &#123;1,…,9&#125;，Table I 选 **h = 5（池化后 best Success rate）、h = 1（best total Return）、h = 9（best Harshness）**，且跨场景保持不变。

**Table I 导航结果（原文数字照抄）**

| 场景 | 策略 | Success ↑ | Total return ↑ | Harshness ↓ |
|---|---|---|---|---|
| Barrier | **Ours** | **0.97** | **−435** | 7.37 |
| | h = 5 (S) | 0.73 | −1167 | **7.28** |
| | h = 1 (R) | 0.12 | −1523 | 7.42 |
| | h = 9 (H) | 0.63 | −1400 | 7.55 |
| Merging Lane | **Ours** | **1.00** | **−385** | **7.02** |
| | h = 5 (S) | 0.63 | −1462 | 7.17 |
| | h = 1 (R) | **1.00** | −460 | 9.68 |
| | h = 9 (H) | 0.61 | −1466 | 7.46 |
| Highway | **Ours** | **0.99** | **−534** | 9.05 |
| | h = 5 (S) | 0.92 | −719 | **8.84** |
| | h = 1 (R) | 0.78 | −1265 | 11.73 |
| | h = 9 (H) | 0.08 | −2988 | 9.26 |

**关键观察（原文支持）**：池化图上，**按成功率最优的固定预算是 h = 5，按总回报最优的是 h = 1**——没有任何单一固定 h 同时拿下两者，而学习策略同时压过两者。

**消融（planner statistics，Fig. 7）**：Full 98% → Full − PS **86%**（"removing planner statistics drops success by 12 percentage points"）→ PS only **74%**。

**其他域结果**：缆挂四旋翼——"Our policy succeeds in **80%** of trials, while every fixed commitment fails"，并学到两段式模式（稳定巡航用大预算、接近目标用小预算；Fig. 8 展示 h = 8 → 2 → 8 → 3）。PushT——策略收敛到常数 **h̄ = 8.00**，终位误差 **0.65 ± 0.48** cm / **0.020 ± 0.017** rad，与最优固定基线 h = 8（**0.65 ± 0.48** / **0.020 ± 0.017**）持平；h = 10 的角误差更小（**0.016 ± 0.014**）但位置误差为 0.76 ± 0.71。

**Sim-to-real**：RoboMaster 实验"uses the same learned policy and budget-to-planner mapping as simulation, with only the physical robot, sensing, and ROS 2 execution stack changed"；作者称 sim-to-real gap 小。

---

## 6 · 能力与失败模式

### 能做（论文有具体证据的）

- **状态依赖的预算切换**：merging lane 中先大预算找安全路线，穿越交叉机器人与近距随机障碍时把承诺压到 h_min = 1（t ≈ 3 s）；缆挂中"巡航大、目标小"（h = 8 / 2 / 8 / 3）。
- **同时优化多个冲突目标**：导航三场景上 success、total return、harshness 三项里，Ours 在 9 个格子中拿下多数最优（仅 Barrier 与 Highway 的 harshness 让给 h = 5）。
- **planner statistics 是有效信号**：去掉 𝔟_k 掉 12 个点；只用 𝔟_k 也能到 74%。
- **对"固定预算必败"的任务给出可行解**：缆挂 80% vs 所有固定 h 全败。
- **真机可迁移**：同一策略 + 同一 budget-to-planner 映射直接上 RoboMaster。

### 不能做 / 失败模式

- **无可利用预算变化时退化为常数**：PushT 上 h̄ = 8.00 恒定。作者归因：planning 与 execution 共享精确动态、系统全观测、无扰动、且目标函数**不奖励计算节省或更早到达**。→ 这是**边界行为**而非 bug，但它说明本方法的价值完全取决于任务里是否存在可利用的预算变化。
- **h_max 无法自适应**：动作空间 ℋ = &#123;1,…,h_max&#125; 在训练前固定，由 Theorem 1 的 h̄(ε, e_0) 保守界定；理论量 L_ρ、L_P、δ、e_0 实测不可得。
- **只支持单调改进型求解器**：ψ_h 的定义要求"解随预算单调改进"；对会被更多迭代带偏的优化器（非凸 + 差初始化）或 anytime 但非单调的启发式，Theorem 1 与整个"预算↔质量"假设都不成立。
- **块内无反馈**：h_k 步真开环，没有任何中途重规划或反射策略（作者明确把它作为相对 [21] 的优势，但代价是 C1 的全部风险由 h 的选择承担）。
- **每域一个策略**：三个域分别训练，未见跨域泛化或单一通才策略的证据。
- **安全保证只在"事后界定"层面**：Theorem 1 给的是"若 h ≤ h̄ 则偏差 ≤ ε"，不是"运行时会检测到偏差超限并回退"。策略本身可能在 ε 之外选 h。

### 隐含假设 (Hidden Assumptions)

1. **求解器 wall-clock ∝ h，且能在 h·dt 内完成**。原文："To afford a computational budget of h control periods, the solver must therefore commit to generating a sequence of actions (a chunk) of length h"。这是**框架成立的必要条件**，但它把"预算"这个抽象量与真实时钟绑死；JAX/MJX 的常数开销在 h 小时会破坏线性关系。
2. **chunk 被精确地开环执行**，没有执行器延迟、无中途干预。e_0 的递推建立在"上一块跑完、下一块从预测状态出发"之上。
3. **模型失配 δ 有界且相对状态平稳**（Assumption 1 的 W_1 上界与状态无关）。真实系统里接触切换（PushT）会让 δ 突变。
4. **ρ 对状态 Lipschitz**。含指示函数项（g·δ_&#123;s∈G&#125;、collision 惩罚）的奖励在边界处并不 Lipschitz——3000·**1**_collision 在碰撞面两侧跳变，L_ρ 在实践中要按最坏跳变取，界会很松。
5. **𝔟_k 的三个统计量足以表征"问题有多难"**。ESS、time-to-infeasibility、dynamics-model mismatch 是为 MPPI/CEM 手工设计的；换求解器（如梯度型 DDP、学习型 planner）时需要重新设计，论文的 Future work 也承认要"richer, high-dimensional planner statistics"。
6. **真机上状态与物体位置可得**：dynamics-model mismatch 定义为"predicted and realised positions of the objects intersected by the rollout tube"的均值位移，这要求可靠的状态估计与物体跟踪；RoboMaster 的室内设定满足，无外部定位的场景不满足。
7. **回报里已隐含时间成本**。PushT 的反例说明：若任务目标不含"早到"或"省算力"，折扣不足以制造出可利用的预算变化，adaptation 就学不出来。

---

## 7 · 与相关工作对比

| 方法族 | 执行承诺 h | 预算与承诺的关系 | 世界在思考时是否冻结 | 与本文的差异 |
|---|---|---|---|---|
| 实时 MPC [7,8] | 固定 h = 1 | 每步都解，预算 = 1 个 dt | — | 反馈最快但预算最紧，无法深度优化；本文把 h=1 作为动作空间下界与"完全反应"参照 |
| Action chunking：RTC [12] / DEFLECT [13] | **固定** | 解耦 | — | RTC 用"条件化到仍在执行的动作"跨过缝隙，DEFLECT 训练策略容忍陈旧观测；两者都不让更大承诺换来更好计划 |
| 自适应 chunk 长度 [14] | 自适应 | 解耦 | — | 只调执行长度，**不调求解器预算**——这是本文最核心的区分点 |
| 多候选 chunk [15] | 固定集合 | 解耦 | — | 预计算多个候选再匹配实际状态；不改变单个计划的求解深度 |
| 事件/自触发 MPC [16,17] | 自适应触发 | 求解器被当 **oracle** | 半冻结 | 目标是在保底性能下**省算力**，假设"多给时间解不会变好"；[17] 用"最大可执行且仍有安全回退"来定时。本文反过来：多给时间**确实**会变好，所以要学"给多少" |
| metareasoning / VOC [5,6]、anytime、deliberation scheduling [18,19]、learned budget [20] | — | 显式惩罚 | **冻结** | 传统 VOC 是**经济价值**：必须由设计者写一个"思考成本"去权衡期望收益。本文的**物理价值**：机器人漂移本身就是成本，惩罚项消失 |
| [21] budgeted options over semi-MDP | 自适应 | 耦合 | 否 | 最接近的工作。但（a）限于**离散博弈**，无真实世界的不受控变化；（b）需要**额外的 reflex 策略**在开环期行动。本文在连续控制三域上做，且不需要 reflex 策略（Remark 2：高层动作是时长不是行为，没有 option library 要发现，也没有低层非平稳性） |

### 🎯 面试 Tip

被问"这篇和 event-triggered MPC / adaptive action chunking 有什么本质区别"时，标准答法三步走：

> **第一句给分野**：event-triggered MPC 把求解器当 oracle，问的是"什么时候**可以省**算力"；本文问的是"什么时候**值得花**算力"——因为求解器是单调改进的，多给时间确实换来更好的计划。
> **第二句给机制**：所以它必须把**执行承诺长度 h** 和**计算预算**绑成**同一个**决策变量，这在 adaptive chunking [14] 里是解耦的。绑在一起的代价是块内真开环，收益是 h 同时决定"想多深"和"反馈多快"。
> **第三句给理论抓手**：绑起来之后，"思考成本"不需要人为定价——物理漂移已经在收费，这就是 physical value of computation；形式化后 Q^Φ(s,h) 就是 VoC，于是可以直接用 PPO 学，且 Theorem 1 告诉你 h_max 能开到多大。

如果追问"为什么不用 MPC 里现成的自适应 horizon"，答：horizon 是**规划视野**，h 是**开环执行长度 + 计算预算**，二者在本文里通过 "MPPI horizon ∝ h" 联动，但概念不同——horizon 变长不给你更多墙钟时间，h 变长才给。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-19)

**诚实声明**：论文正文**未给出任何 `github.com` 链接**（References 前的正文仅出现 "website" 一词，无 repo URL、无 commit、无 issue 编号）。因此本节**不存在社区 issue 流可验证**，以下三条 pitfall 全部由 **§6 失败模式 + §2/§4 的方法约束**推导，标注为 `DERIVED`。

### P1 — `DERIVED`：h = 1 这一档的"预算→0"假设在真实时钟上不成立，而策略恰在关键时刻用它

- **失败模式来源（§6）**：merging lane 中策略在 t ≈ 3 s 穿越交叉机器人时"approaches the reactive limit h_min = 1"——即最危险的时刻选了最小预算档。
- **方法约束来源（§4）**：框架要求"To afford a computational budget of h control periods"，即预算与 h 成正比；但 MPPI 的实现是 JAX/MJX，JIT 后的 kernel launch 与调度开销近似**常数**，不随 h 缩放。
- **机制**：h = 1 时标称预算 = 1 个 dt（导航 0.1 s），实际有一个不为零的计算地板。若地板 > dt，则 h = 1 档在真机上无法按时交付新块，开环实际延长——而策略的 z_k 里记录的 h_&#123;k−1&#125; = 1，与实际不符，形成**训练/部署的时钟错配**。论文未报告单次求解 wall-clock，无法从文本排除。
- **排查动作**：在目标硬件上单独 profile h ∈ &#123;1,2,3&#125; 的求解耗时分布（不是均值，看 P99），确认 h·dt 是所有档位的上界。

### P2 — `DERIVED`：h_max 只能靠 Theorem 1 保守拍定，而该定理的四个常数实测不可得 → 动作空间被人为压扁

- **失败模式来源（§6）**：h_max 在训练前固定，"由 Theorem 1 的 h̄(ε, e_0) 保守界定"，且 PushT 已经出现"策略塌成常数 h̄ = 8.00"的退化。
- **方法约束来源（§2.3）**：h̄ 依赖 L_ρ、L_P、δ（真实核与标称核的 **W_1 上界**）、e_0（**继承来的**初始投影误差）。§3 玩具算例显示：L_P 从 1.00 抬到 1.02，ε = 0.3 时 h̄ 就掉到 4——**界对 L_P 极敏感**。
- **机制**：部署时这四个量都没有在线估计手段，只能取保守值 → ℋ 变小 → categorical actor 的支撑集变窄 → 学到的策略在结构上无法表达"该想 9 步"的决策，表现上退化成近似固定 h。这与 PushT 的 h̄ = 8.00 是**两种不同成因的同一现象**（一个是任务无变化，一个是动作空间被砍）。
- **排查动作**：报告 h 的**分布直方图**而非仅均值。若策略在训练早期就饱和到单一 h，先怀疑 h_max 被拍小，再怀疑任务无可利用变化。

### P3 — `DERIVED`：𝔟_k 中的 dynamics-model mismatch 会吸收感知误差，而策略对该项依赖极强

- **失败模式来源（§6）**：𝔟_k 定义为"the mean displacement between predicted and realised positions of the objects intersected by the rollout tube"——需要真实物体位置；本文真机只在 RoboMaster 室内设定验证，且明文说明"only the physical robot, sensing, and ROS 2 execution stack changed"，即定位由平台提供。
- **方法约束来源（§5 消融）**：Full 98% → Full − PS 86%，且 PS only 已达 74%——**策略严重依赖 𝔟_k**。
- **机制**：一旦定位有偏、物体跟踪有延迟，`predicted vs realised` 的位移里就混进了感知误差，策略会把"我看不准"误读成"我的模型不准"，从而**过度缩短 h**（因为模型失配 δ 大 → h̄ 小 → 保守）。这与 P2 叠加时尤其危险：既缩小了动作空间，又持续把策略推向 h = 1 一侧。而由于它依赖强，这个误读的代价不会有任何缓冲。
- **排查动作**：在部署前给 mismatch 项单独做一次**注入实验**（人为平移 1–2 cm 的物体位姿估计），看 h 的分布是否整体左移；若左移，说明该项需要与感知不确定性解耦（例如用残差的**时间一致性**而非绝对位移）。

---

[← Back to navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（2610.23662v1，正文已截断至 Conclusion + References 前）· 论文未报告延迟/吞吐/显存占用，相关格位已标「论文未报告」· §3 玩具算例数值为自造示范，非论文数据 · §8 全部为 `DERIVED`，无 repo / issue 可验证 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2610.23662 -->"
