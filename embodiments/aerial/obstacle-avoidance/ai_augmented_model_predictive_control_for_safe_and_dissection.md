[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->"

# AI 增强的模型预测控制：面向安全自适应交会与近距操作 (AI-Augmented Model Predictive Control for Safe and Adaptive Rendezvous and Proximity Operations)

> **发布时间**：2026-07-18（arXiv:2607.16630v1 [cs.RO]）
> **论文 / 模型名**：AI-Augmented MPC（KSPDG Capture-the-Satellite 场景；Embry-Riddle XDLab 队伍方案）
> **核心定位**：在对抗性三体在轨 RPO 中，用一个"只在参数层做自适应、绝不改动约束优化结构"的外环，把固定参数 MPC 的成功率从 28%/60% 拉到 72%，并在 1000 局蒙特卡洛中取得 94.0% 成功率。

端到端学习控制（RL 直接出推力）在安全关键的在轨场景里不可解释、无法保证硬约束；纯 MPC 则参数写死、遇到动态对抗几何就僵化。本文的答案是把"学习"降格到只调 MPC 的可解释权重与安全参数，把"约束"始终留在 QP 里——用牺牲表达力换取可解释性与约束感知。

## X-Ray 开场

在 Kerbal Space Program Differential Game（KSPDG）的 Capture-the-Satellite 三航天器对抗场景里（追捕者 Bandit、目标 Lady、对抗者 Guard），作者用 Clohessy–Wiltshire（CW）线性相对动力学 + 带松弛变量的约束 QP 构成内环 MPC，再叠一个外环"监督层"：离线用 Cross-Entropy Method（CEM）在黑盒闭环回报上搜一组基础参数 $P^{\ast}$，在线用三条**手工几何规则**（近距最小间距膨胀、按 Bandit–Lady 距离分级放大跟踪权重、按 QP 可行性逐级衰减 KOZ 权重）实时改 MPC 的权重。关键点：外环永不输出推力，只改 QP 的 $(H,f,A,b)$。对 spatial AI 研究者的意义在于：它给出了"学习/自适应应该停在哪一层"的一个明确工程答案——**调参层可以学，约束层不能学**；同时也暴露了这种做法的天花板——本文所谓"AI"其实没有神经网络、没有在线学习，只有离线无导数搜索加手写规则。

## 📍 研究全景时间线

```
1960s  CW/Hill 线性相对动力学方程
  │
2000s  MPC 进入在轨近距操作：Richards 编队约束轨迹优化；Breger & How 燃料最优+被动避碰
  │
2015-2020  RL 进入制导：端到端策略、多智能体对抗决策；但可解释性/硬约束缺失
  │
2020-2024  Safe RL / CBF 安全滤波 / RL-enhanced MPC（学习嵌进优化结构内部）
  │
2026  AIAA Differential Game Capture the Satellite（KSPDG / SpaceGym 官方环境）
  │
  ├── 基线 A：Naive MPC（固定标称参数、最小安全处理）      → 25 局 28%
  ├── 基线 B：Fixed-Agent MPC（KOZ+slack、人工调参固定）    → 25 局 60%
  └── ★ 本文：Adaptive Agent（CEM 基础参数 + 几何规则在线调参）→ 25 局 72%；1000 局 94.0%
        │
        └── 本文局限：CW 线性化;外环无形式化可行性/稳定性保证;手写阈值绑定仿真尺度;
                      "AI"仅为离线无导数搜索;无真机/无计时数据
```

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练期 vs 推理期差异 |
|---|---|---|---|
| CW 相对动力学（Eq.3–7） | LVLH 相对状态 $\mathbf{x}\in\mathbb{R}^6$、加速度 $\mathbf{u}\in\mathbb{R}^3$ | 离散 $A_d,B_d$（矩阵指数+零阶保持） | 两期完全一致；模型不随外环改变（论文明确：dynamics model 对外环决策不变） |
| 堆叠预测（Eq.10–12） | $\mathbf{x}_k$、决策 $\mathbf{U}_k\in\mathbb{R}^{3H_u}$ | $\mathbf{X}_k=\Phi\mathbf{x}_k+\Gamma T\mathbf{U}_k$ | 一致；$H_p,H_u$ 允许被外环改（Table 1） |
| 参数化 QP（Eq.15–17） | $\mathbf{x}_k$、$P_k$ | $\mathbf{z}^{\ast}=[\mathbf{U}_k;\mathbf{s}]$ | 一致；$P_k$ 只进 $(H,f,A,b)$ |
| 预测 KOZ 约束 + 松弛（Eq.19–20） | 预测 Guard 轨迹、$d_{\mathrm{KOZ}}$、法向 $\hat{\mathbf{n}}_i$ | 线性不等式 $A\mathbf{z}\le b$ + $s_i$ | 一致；仅在预测 Guard 进入安全缓冲区时激活，且只在 $i=1..K_{\mathrm{KOZ}}$ 子区间加约束 |
| CBF 安全滤波（Eq.21–23，可选） | $\mathbf{u}_{\mathrm{cmd}}$、$h=d_{BG}-d_{\mathrm{KOZ}}$、$\dot h$、$\mathbf{a}_G^{\mathrm{now}}$ | $\mathbf{u}_{\mathrm{safe}}$（投影 QP，3 维） | 一致；满足条件时是恒等映射 |
| PD 兜底（Eq.15 不可行时） | 距离、状态误差 | 饱和 PD 加速度 | 一致；论文称"报告实验中未在标称阶段触发" |
| 外环-离线（Eq.24） | episode 回报 $J(\pi_{\mathrm{MPC}}(\cdot;P),\xi)$ | $P^{\ast}$（CEM；CMA-ES 为已实现备选） | **仅离线**；推理期不再训练 |
| 外环-在线（Eq.25–26 等） | $d_{BG}$、$d_{BL}$、QP 可行性、capture lane 状态 | 有效 $d_{\min,\mathrm{eff}}$、有效 $Q$、有效 $w_{\mathrm{KOZ}}$ | **仅推理期**；纯确定性规则 |

### 1.2 关键机制

**⚡ Eureka Moment：不要让学习去生成推力，让学习只去改 MPC 的系数——把"策略搜索"换成"对一组物理可解释参数的黑盒搜索 + 几何阈值查表"，约束结构因此在任何时刻都还在线。**

三层保险，从外到内：
1. **外环（策略层）**：$P_k$ 只能落在有界的 $\mathcal{P}$ 内（论文：bounded by construction），因此内环 QP 的数据始终是紧集上的连续函数；
2. **内环（战术层）**：QP 的动力学、执行器上下界、预测安全约束对外环"免疫"；
3. **最内层（兜底）**：可选 CBF 投影 + 不可行时饱和 PD。

值得点明的**紧张之处**：论文在 4.4 节自己说，"主要安全保证来自约束 MPC 与预测安全评估 + 松弛处理；CBF 只是额外防线"，但同时 4.5.2 的第三条规则允许在 QP 反复不可行时把 $w_{\mathrm{KOZ}}$ 依次降到 $0.5w_{\mathrm{KOZ}}$、$0.3w_{\mathrm{KOZ}}$、最后置 0（"last-resort guidance mode"）。也就是说，**最需要安全的时刻，安全项恰恰被规则性关闭**。这不是 bug，是作者为了保 QP 可行性做的显式取舍——但它直接把"安全"从保证降级为统计倾向。

### 1.3 信息流

```
                ┌──────────────── 外环（监督层，只改参数，不出推力）────────────────┐
                │  离线: CEM over P∈𝒫,  min E_ξ[J(π_MPC(·;P), ξ)]   → P*          │
                │  在线: ① d_BG<1.25 d_min → d_min,eff = d_min(1+0.08·prox)        │
                │        ② d_BL<500/200/80 m → (w_pos,w_vel)×(4,25)/(8,50)/(12,80) │
                │        ③ QP 不可行 → w_KOZ ×0.5 → ×0.3 → ×0                   │
                └───────────────┬─────────────────────────────────────────────────┘
                                │ P_k
   x_k ──► [CW 离散预测 Φ,Γ,T] ──► [参数化 QP  Eq.15] ──► z*=[U;s] ──► u_k=z*_{1:3}
   (相对状态)        ▲                    ▲                                │
                     │                    │ A z ≤ b (线性化 KOZ + slack)     ▼
                     │              Guard 预测轨迹                  [可选 CBF 投影 QP]
                     │                    ▲                                │
                     └──── CW 传播 ◄──────┘                          u_safe → 执行器
                            │
                    QP infeasible ──► 饱和 PD 兜底（论文称未在标称阶段触发）
```

## 2 · 数学核心

📌 **Napkin Formula**：
$$\mathbf{u}_k=\Big[\arg\min_{\mathbf{z}}\ \tfrac12\mathbf{z}^{\top}H(P_k)\mathbf{z}+f(\mathbf{x}_k,P_k)^{\top}\mathbf{z}\ \ \text{s.t. }A\mathbf{z}\le b\Big]_{1:3},\qquad \mathbf{z}=[\mathbf{U}_k;\mathbf{s}]$$
**每一拍解一个小凸 QP；"AI"只改 QP 的系数 $P_k$，从不改 QP 本身。**

**(a) 目标**：有限时域二次代价，最小化 Bandit–Lady 相对跟踪误差、惩罚控制能量、惩罚松弛。

**(b) 公式**（Eq.9）：
$$J=\sum_{i=1}^{H_p-1}\|\mathbf{x}_B(k+i)-\mathbf{x}_L(k+i)\|_Q^2+\sigma_{H_p}\|\mathbf{x}_B(k+H_p)-\mathbf{x}_L(k+H_p)\|_Q^2+\sum_{i=0}^{H_u-1}\|\mathbf{u}(k+i)\|_R^2+\sum_{i=1}^{K_{\mathrm{KOZ}}}\lambda_s s_i^2$$
其中（Eq.13）$Q=\mathrm{blkdiag}(w_{L,\mathrm{pos}}I_3,\ w_{L,\mathrm{vel}}I_3)$，$R=w_UI_3$；$\sigma_{H_p}\ge1$ 为终端乘子，Bandit 进入 final-approach 距离时取 $\mathrm{term}_{\mathrm{final}}$，否则 $\mathrm{term}_{\mathrm{base}}$。

**(c) 变量说明**：$H_p$ 预测步数、$H_u\le H_p$ 控制步数、$T$ 为 lifting 矩阵（$i\ge H_u$ 后输入保持最后一个决策值）、$K_{\mathrm{KOZ}}$ 为激活的 KOZ 预测子区间长度、$\lambda_s$ 松弛惩罚、$s_i\ge0$、$0\le s_i\le s_{\max}$。

**(d) 直觉**：因为 CW 是线性、代价是二次、约束是线性化后的线性不等式，整个问题就是一个**参数化凸 QP**（Eq.16）：
$$H=\begin{bmatrix}T^{\top}\Gamma^{\top}\bar Q\,\Gamma T+\bar R&0\\0&\lambda_s I_{K_{\mathrm{KOZ}}}\end{bmatrix},\quad f=\begin{bmatrix}-T^{\top}\Gamma^{\top}\bar Q\,(\mathbf{X}_L^{\mathrm{ref}}-\Phi\mathbf{x}_k)\\\mathbf{0}\end{bmatrix}$$
$H$ 只依赖 $P_k$（不含状态），$f$ 线性依赖状态误差——这正是"外环调参"可行的数学根因：**改 $P_k$ 只改一个固定的二次型，不改求解器**。

**(e) 线性化 KOZ 约束**（Eq.19–20）——全篇最脆的一步：
$$\hat{\mathbf{n}}_i=\frac{\mathbf{r}_{BG}^{\mathrm{nom}}(k+i)}{\|\mathbf{r}_{BG}^{\mathrm{nom}}(k+i)\|},\qquad h_0^i=\|\mathbf{r}_{BG}^{\mathrm{nom}}(k+i)\|-d_{\mathrm{KOZ}}$$
$$-\hat{\mathbf{n}}_i^{\top}M_i\mathbf{U}_k-s_i\le-\hat{\mathbf{n}}_i^{\top}\mathbf{r}_{BG}^{\mathrm{nom}}(k+i)-\gamma_K h_0^i$$
即：把球约束 $\|\mathbf{r}_{BG}\|\ge d_{\mathrm{KOZ}}$ 沿**当前标称开环轨迹的视线方向**做一阶展开，$M_i$ 把决策控制映射到第 $i$ 步位置偏移，$\gamma_K>0$ 控制约束向边界逼近的速率，$s_i$ 软化。一阶展开只在偏移量相对 $d_{BG}$ 很小时可信——这是后面 §6、§8 全部失败模式的根源。

**(f) 在线自适应三条映射**（Eq.25–26 + §4.5.2）：
$$\mathrm{prox}=\mathrm{clip}\!\left(\frac{1.25d_{\min}-d_{BG}}{1.25d_{\min}},0,1\right),\qquad d_{\min,\mathrm{eff}}=d_{\min}(1+0.08\,\mathrm{prox})$$
即**只在 $d_{BG}<1.25d_{\min}$ 时才膨胀安全间距，最多膨胀 8%**；跟踪权重按 $d_{BL}$ 跨 500/200/80 m 三档跳变。

## 3 · 带数字走一遍（玩具设定，非论文数据）

为避免 CW 六维耦合，取**单轴双积分器**（$\Delta t=1\,\mathrm{s}$，$A_d=\begin{bmatrix}1&1\\0&1\end{bmatrix}$，$B_d=\begin{bmatrix}0.5\\1\end{bmatrix}$），$H_p=3$、$H_u=2$、Lady 恒定位于 10 m、$Q=\mathrm{diag}(1,0)$（只罚位置）、$w_U=1$、无 KOZ 激活、无松弛。$\mathbf{x}_k=\mathbf{0}$。

**堆叠预测**（按 $i\ge H_u$ 保持末值）：
$$p_1=0.5u_0,\qquad p_2=1.5u_0+0.5u_1,\qquad p_3=2.5u_0+2u_1$$
**代价**：$J=(p_1-10)^2+(p_2-10)^2+(p_3-10)^2+u_0^2+u_1^2$

**组装 QP**：$M=\begin{bmatrix}0.5&0\\1.5&0.5\\2.5&2\end{bmatrix}$，$\mathbf{r}=[10,10,10]^{\top}$
$$M^{\top}M=\begin{bmatrix}8.75&5.75\\5.75&4.25\end{bmatrix}\Rightarrow H=2(M^{\top}M+I)=\begin{bmatrix}19.5&11.5\\11.5&10.5\end{bmatrix},\quad f=-2M^{\top}\mathbf{r}=\begin{bmatrix}-90\\-50\end{bmatrix}$$

**求解**（$\det=72.5$）：
$$u_0=\frac{90\times10.5-11.5\times50}{72.5}=\frac{370}{72.5}\approx5.10,\qquad u_1=\frac{19.5\times50-11.5\times90}{72.5}=\frac{-60}{72.5}\approx-0.83$$

**读法**：开环计划是"先猛推、后刹车"（$u_0>0,u_1<0$）——这正是 $H_u<H_p$ 带来的终端代价诱导的长视距机动。但**滚动时域只执行第一拍**：$\mathbf{u}_k=u_0\approx5.10$，$p_1=2.55$ m，然后重解。

**外环调参的效果**：令 $w_U=10$（即 $R=10I$），$H=2(M^{\top}M+10I)=\begin{bmatrix}37.5&11.5\\11.5&28.5\end{bmatrix}$，$\det=936.5$，得 $u_0\approx2.13$。**仅仅把控制权重从 1 加到 10，首拍推力从 5.10 降到 2.13**——这就是"外环改 $P_k$ 只改系数"的物理含义：不需要换控制器，行为已经变了。

**松弛变量的作用**：若此刻预测 Guard 出现在前进方向、线性化约束要求 $u_0\le 0.5$，硬约束下 $u_0$ 被截到 0.5；带松弛时约束变为 $0.5-u_0-s\le0$，$s\ge0$，代价里多一项 $\lambda_s s^2$。$\lambda_s$ 大 → $s\approx0$、行为等同硬约束（安全但可能不可行）；$\lambda_s$ 小 → 允许越界换可行性。**论文的"降级阶梯"（$w_{\mathrm{KOZ}}\to0$）等价于在反复不可行时把 $\lambda_s$ 的有效权压到 0**，此时 $s$ 无成本，KOZ 约束名存实亡。

## 4 · 工程视角

| 维度 | 论文给出的事实 | 说明 |
|---|---|---|
| 硬件型号 / 算力平台 | **论文未报告** | 全部实验在 KSPDG 仿真内完成，未提任何机载计算机 |
| 单步求解时延 / 控制频率 | **论文未报告** | 仅定性表述 "compatible with real-time execution"、"real-time computational feasibility"；$\Delta t$ 的具体取值亦**未在正文给出** |
| QP 维度 | $3H_u+K_{\mathrm{KOZ}}$（由 Eq.14 直接读出） | $H_p,H_u,K_{\mathrm{KOZ}}$ 的具体数值**论文未报告**（Table 1 只列为可调参数） |
| 每拍计算链 | 1 次主 QP + 1 次 3 维 CBF 投影 QP（可选）+ 常数时间规则查表 | 结构上很轻：变量数 $\sim\!\mathcal{O}(H_u)$，约束数 $\sim\!\mathcal{O}(H_p+K_{\mathrm{KOZ}})$ |
| 内存 | **论文未报告** | — |
| 吞吐 / 1000 局总机时 | **论文未报告** | 只说执行了 1000 局 closed-loop runs |
| 离线调参成本 | **论文未报告**（仅定性：CEM 在 $n_{ep}$ 个 episode 的样本均值上做无导数搜索） | 这是部署前一次性成本，但量级未披露 |
| 部署约束 | 无形式化递归可行性/稳定性保证（作者明示 out of scope）；不可行时切 PD；QD 数据依赖 $P_k$ 有界 | 若 $H_p,H_u$ 被在线改动（Table 1 允许），QP 维度会运行期变化——对固定尺寸求解器/代码生成不友好 |
| 代码可得性 | Data Availability：代码"may require institutional approval" | 不可公开复现 |

**摘要式结论**：这是一个**计算结构上刻意做轻**的方案（线性动力学 + 凸 QP + 常数时间规则），但论文没有提供任何计时证据，"real-time" 属于定性主张，不能当作已测量结论引用。

## 5 · 数据与评测

**环境**：KSPDG（Kerbal Space Program Differential Game），官方 2026 AIAA Capture the Satellite challenge 环境，配套 SpaceGym。三航天器：Bandit（受控，本文方法）、Lady（目标，仿真框架驱动、有周期性规避行为）、Guard（对抗者，控制策略未公开，undisclosed control policy）。

**场景设定**（论文给出）：LVLH 相对坐标系；成功阈值 5 m（"below the 5 m target threshold"）；被 Guard 捕获阈值 10 m（"below the 10 m capture threshold"）。

**三种控制器配置**（Table 2）：

| 配置 | 自适应调参 | 安全处理 | 参数来源 |
|---|---|---|---|
| Naive MPC | 否 | 最小基线安全处理 | 固定标称参数 |
| Fixed Agent | 否 | 预测 KOZ + slack | 人工调参、全程固定 |
| Adaptive Agent | 是 | 预测 KOZ + slack | CEM 基础参数 + 几何规则在线调制 |

**评测协议**：
- 大规模鲁棒性：**1000 局** closed-loop 仿真，变化初始条件与对抗遭遇几何 → 只跑 Adaptive Agent；
- 配置对比：**每配置 25 局**；
- 评测期不再做离线训练（deployment mode）。
- 指标（Table 3）：成功率、目标相对距离演化、最小 Guard 间距、KOZ 越界、失败率、参数演化、闭环可行性、数值稳定性。

**结果数字（逐字来自正文）**：
- 1000 局：成功 **940** 局 → **94.0%**；超时 **44** 局 → **4.4%**；被 Guard 捕获 **16** 局 → **1.6%**。
- 成功局最近接近距离 **低于 5 m**；成功与超时局的最近 Guard 间距**约 10 到 50 m**；Guard 捕获局间距**低于 10 m**。
- 25 局/配置对比：Adaptive **72%**、Fixed **60%**、Naive **28%**。
- 代表成功案例：Guard 在 $t\approx80\,\mathrm{s}$ 前持续逼近，同时 $w_{\mathrm{KOZ}}$ 与 $d_{\min}$ 上升。

**必须说明的条件**：① 25 局样本量很小，论文自身未给置信区间，因此"72% vs 60% vs 28%"只能作为趋势证据，不能作为显著差异结论；② 1000 局只覆盖 Adaptive Agent，因此 94.0% 与 72% **不构成同一实验下的对比**；③ 全程为仿真，未上真机、未用真实轨道摄动模型；④ 作者明确：评测"not intended to provide formal proof of recursive feasibility or closed-loop stability"。

## 6 · 能力与失败模式

**能做（有证据）**：
- 在对抗 Guard + 规避 Lady 的三体场景中，以凸 QP 的代价实现 94.0%（1000 局）的成功率，且不出现失控发散或持续振荡（"No catastrophic controller divergence or persistent unstable oscillatory behavior was observed"）。
- 自适应行为**可追溯**：$w_{\mathrm{KOZ}}$、$d_{\min}$ 的轨迹可直接对应到轨道几何（Fig.6/Fig.7），这是端到端策略给不出的东西。
- 参数只在有界集内改动，内环约束结构全程在线——任何时刻的推力仍受 $u_{\max}$ 与预测 KOZ 约束约束。

**不能做 / 失败模式（有证据）**：
- **16/1000 被 Guard 捕获**：Fig.6 分析指出，这些案例的 $w_{\mathrm{KOZ}}$ 上升"only after substantial reduction of Bandit–Guard separation had already developed"——即**自适应触发得太晚**，是时序问题而非参数取值问题。
- **44/1000 超时**：部分超时局在距离双轴上"离两者都远"，说明控制器在不利几何下过度保守（"sacrificed short-term rendezvous efficiency in order to preserve longer-term safety feasibility"）。
- **捕获失败常伴随较大的最终 Bandit–Lady 距离**：说明对抗几何会**同时**破坏交会进度与安全性，不是单一维度的失败。
- **无形式化保证**：递归可行性与闭环稳定性在任意参数更新下均未证明（作者明示）。
- **CBF 只是可选层**：不提供主保证，且 $\mathbf{a}_G^{\mathrm{now}}$ 用的是 "current PD-pursuit estimate of the adversary acceleration"。

### 隐含假设 (Hidden Assumptions)

1. **CW 线性化在全程有效**：相对运动足够近、参考轨道足够圆。一旦相对距离/偏心率变大，$\Phi,\Gamma$ 的预测就只是"够用的近似"（作者自述 "sufficiently accurate for the local relative motion conditions"）。
2. **未来 Guard 轨迹可用同一 CW 结构开环预测**："The Guard relative trajectory was propagated over the MPC prediction horizon using the same CW-based prediction structure"。这等于假设**对抗者不会因为你的机动而改变策略**——但对手恰恰是"attempting to intercept or obstruct"的。
3. **Guard 加速度可由 PD 追踪估计**（CBF 里的 $\mathbf{a}_G^{\mathrm{now}}$）：假设对抗者有可被 PD 模型刻画的追击倾向。
4. **KOZ 是球、Guard 是点**：无姿态、无太阳翼、无羽流、无接近走廊概念。
5. **安全缓冲区阈值与降级阶梯的数值绑定仿真尺度**：$1.25d_{\min}$、$+8\%$、500/200/80 m、$0.5/0.3$ 倍率全部是设计常数，论文未做跨尺度敏感性分析。
6. **参数集 $\mathcal{P}$ 有界 ⟹ 内环良态**：作者以此替代可行性证明（"bounded by construction"），但这只是必要条件，不保证"软约束下的可行解一定安全"。
7. **离线 CEM 的期望回报能代表部署分布**：Eq.24 的 $\xi$ 采自 KSPDG 的初始条件分布，一旦真实遭遇几何超出该分布，$P^{\ast}$ 的最优性无依据。
8. **"AI"这个词的隐含承诺**：正文的在线层是三条确定性规则，离线层是无导数黑盒搜索，**没有神经网络、没有在线学习**。若要声称"AI-augmented"，其含义须被限定为"数据驱动的参数搜索"。

## 7 · 与相关工作对比

| 方案类别 | 代表工作/配置 | 控制输出方式 | 硬约束 | 可解释性 | 适应性 | 本文差异 |
|---|---|---|---|---|---|---|
| 经典约束 MPC for RPO | Breger & How（燃料最优+被动避碰）、Richards 等（编队约束优化） | QP 直接出推力 | 有（在模型内） | 高 | 无（固定参数） | 本文在其上加外环调参 |
| Naive MPC（本文基线） | 本文 Table 2 | QP | 弱（最小安全处理） | 高 | 无 | 25 局 28% |
| Fixed-Agent MPC（本文基线） | 本文 Table 2 | QP | 有（KOZ+slack） | 高 | 无（人工调参） | 25 局 60% |
| 端到端 RL / RL+对手建模 | He 等（RL+opponent modeling）；综述性 RL-GNC 工作 | 策略网络直接出动作 | 难（需 safe RL 补） | 低（隐表征） | 强 | 本文不学策略，只学参数 |
| RL-enhanced MPC / 学习增强优化 | 学习改预测模型/在线参数/策略决策；safe learning control | 混合 | 取决于结构 | 中 | 强 | 本文把"学习"严格限制在**有界、有物理语义**的参数向量上 |
| **本文 Adaptive Agent** | — | QP（外环不出推力） | 有（结构不变，但可被降级规则软化） | **高**（$w_{\mathrm{KOZ}},d_{\min}$ 可画曲线） | 中（3 条几何规则 + 离线 CEM） | 25 局 72%；1000 局 94.0% |

**面试 Tip**：如果被问"这和 RL 端到端比好在哪"，标准答法是三层递进——①**约束不动**：动力学、执行器界、预测安全约束在任何 $P_k$ 下都还在 QP 里，端到端策略给不出这个；②**可审计**：所有自适应量都是物理量（安全权重、最小间距、跟踪权重），能画成随几何演化的曲线做事故复盘，隐表征做不到；③**但要诚实补一句代价**：表达力被限制在"标量权重 + 阈值规则"这个极小的假设空间里，本文的在线层其实是手写启发式，真正的"学习"只在离线 CEM 那一步；而且作者自己承认没有递归可行性/稳定性证明。若继续被追问"那 72% vs 60% 显著吗"——答：每配置只有 25 局，论文没给置信区间，只能当趋势。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-28)

**repo 状态核查**：全文（含 Data Availability Statement）**未出现任何 github.com 链接或仓库标识符**；作者明确"datasets, simulation framework, and code ... may require institutional approval"，即代码不公开。因此本节**无社区 issue 证据**，以下三条 pitfall 全部由 §6 失败模式 + §4 方法约束**推导**，未经 issue 验证。

**Pitfall 1 — 一阶线性化 KOZ 在"最需要它"的时刻最不可信。**
推导链：(§6 隐含假设 2/3) 约束用**标称开环轨迹**上的视线方向 $\hat{\mathbf{n}}_i$ 做一阶展开 → (方法约束 Eq.20) 约束里只剩 $\hat{\mathbf{n}}_i^{\top}M_i\mathbf{U}_k$ 这一项线性响应，而 $h_0^i=\|\mathbf{r}_{BG}^{\mathrm{nom}}\|-d_{\mathrm{KOZ}}$ 在近距离时趋于 0 → (机械后果) 决定避碰的那一拍恰恰是 $\|\mathbf{U}_k\|$ 最大（贴 $u_{\max}$）、$h_0^i$ 最小的一拍，此时一阶展开的二阶残差相对约束右端项占比最大 → QP 判"可行"而真实 CW 传播下球约束已被穿透。可观测征兆：$s_i$ 长期钉在 0（QP 认为不需要软化）却仍出现 $d_{BG}<d_{\mathrm{KOZ}}$。修法：在 $\|\mathbf{r}_{BG}\|<2d_{\mathrm{KOZ}}$ 时改用二阶/信赖域约束，或直接用 CBF 那条对 $\|\mathbf{u}\|$ 线性的条件兜底。

**Pitfall 2 — 安全项会被"可行性降级阶梯"静默关掉。**
推导链：(§6 失败模式：16/1000 Guard 捕获) + (§1.2 紧张之处：$w_{\mathrm{KOZ}}\to0.5\to0.3\to0$) + (方法约束 Eq.14/16：$w_{\mathrm{KOZ}}$ 只在 QP 构造时作为系数进入，关闭后 QP 仍"feasible"返回) → (机械后果) 控制器在强对抗几何下会进入一种**日志显示全部正常、但目标函数里已经没有安全项**的状态；而 CBF 在 §4.4 被明确定位为"optional"、"additional defense layer"，若配置里没打开，此时全系统无任何安全项。复现方式：把 $d_{\min}$ 主动调小/把对手调激进，让 QP 连续两拍不可行，观察 $w_{\mathrm{KOZ}}$ 是否落到 0 且不再恢复。修法：给降级阶梯加**恢复条件与时序约束**（例如仅在 $d_{BG}>2d_{\min}$ 时恢复权重，且限制单次任务内的累计降级拍数），并把"KOZ 权重=0"记为硬告警而非普通日志。

**Pitfall 3 — 在线改 $H_p,H_u$ 会让 QP 维度在运行期跳变。**
推导链：(Table 1 明确把 $H_p,H_u$ 列为可自适应参数) + (方法约束 Eq.14：决策维 $=3H_u+K_{\mathrm{KOZ}}$；Eq.16：$H$ 的块结构随 $H_p$ 变；$K_{\mathrm{KOZ}}$ 亦随几何变) → (机械后果) 任何**把 QP 尺寸静态化**的部署路径都会炸：固定尺寸的稠密求解器缓冲区越界、代码生成型求解器（需编译期确定维度）直接不适用、预分配的热启动 warm-start 矩阵尺寸不匹配导致首拍退化。同理，$H_p$ 变化会改变 $\Phi,\Gamma,T$ 的形状，若这些矩阵被缓存复用则会静默用错维度。修法：把 $\{H_p,H_u,K_{\mathrm{KOZ}}\}$ 的取值枚举成有限集合，为每个组合预生成/预编译一套求解器与预分配内存；或干脆固定 $H_p,H_u$，只让权重类参数自适应（这也更符合论文"只改系数"的原始主张）。

---

[← Back to navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2607.16630v1 全文 · §4 未在真机/未在任何计时实验中复现，所有性能与实时性数字均标 `UNVERIFIED`（论文正文亦未提供）；§3 为明确标注的玩具数值推导，非论文数据；§8 无官方 repo 信号（全文无 github.com 链接），pitfall 均为由 §6 与方法约束推导，未经 issue 验证。

[//]: # "<!-- source: https://arxiv.org/abs/2607.16630 -->"
