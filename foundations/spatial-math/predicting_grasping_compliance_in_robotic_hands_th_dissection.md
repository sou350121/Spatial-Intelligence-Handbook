[//]: # "<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: hybrid
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 用力工具抓取中的顺应性预测：解析模型引导神经网络 (Predicting Grasping Compliance in Robotic Hands through Analytical-Model-Informed Neural Networks)

> **发布时间**：2026-07-20（arXiv:2607.17541v1 [cs.RO]，2026 年 7 月 20 日）
> **论文 / 模型名**：AMINN（Analytical Model-Informed Neural Network）
> **核心定位**：把"抓取"从二分类成功/失败问题，重构成"外部力旋量 → 手内工具位移"的顺应性预测问题；用嵌入解析刚度层的混合网络，在保持与黑盒 MLP 同级精度的同时把能量不守恒（passivity violation）从 0.65 压到 0.00。

抓取的稳定性标签只回答"工具会不会掉"，却回答不了"工具在受力时会滑移多少" —— 而在用工具施力的场景里，后者才是精度与安全的分水岭。本文用"预测分支级关节刚度 + 闭合雅可比同余映射"的方式，把物理结构塞进网络，得到一个可解释、能量一致的力-位移预测器；但它完全建立在仿真数据上，尚未给出实机验证。

## X-Ray 开场

现有抓取评估管线几乎都是二分类（stable/unstable、success/failure），这对 pick-and-place 够用，对"握着螺丝刀去拧"不够用：抓取名义稳定，工具仍可能在手内位移到破坏轨迹精度。作者提出 AMINN —— 不让网络直接回归笛卡尔空间的"力→位移"，而是让网络只学生成**关节空间刚度块**（SPD 约束的弹簧块 + 门控的肌腱刚度），再用闭合雅可比的同余变换 $K_x = J_x^\top(J_q K_q^{-1}J_q^\top)^{-1}J_x$ 推到笛卡尔空间，级联地先判稳定性、再算位移。对 spatial AI 研究者的意义：这是一个"结构化物理先验作为网络中间层"的可复用范式 —— 约束施加在**参数化空间**（这里是 $K_q \succ 0$），而不是靠损失函数软惩罚。

## 📍 研究全景时间线

```
1990s ── 力闭合 / 扳手空间判据（[1-6]）：抓取能不能抵抗扰动？
   │
2000s ── 刚度分析三件套：VJM 集中柔度 [18] / MSA [19] / FEA [20]
   │      Cutkosky & Kao 拆解手部柔度 [22]；Chen & Kao 关节↔笛卡尔刚度同余 [23]
   │
2017-19 ─ 学习式抓取成功率大爆发：Dex-Net 2.0 [11] / QT-Opt [12] / 触觉稳定性分类 [13]
   │      → 二分类范式成为主流，但"稳定性 ≠ 可用性"
   │
2020s ── 欠驱动手力学建模（[31-41]）+ 学习式顺应性估计（[42-44]）
   │      物理引导/混合学习抬头，但少见"解析层嵌进网络"的完整预测器
   │
2026 ── ▶ 本文 AMINN：两阶段级联 + 两趟解析层 + 关节空间 SPD 刚度学习
   │        局限：全仿真数据、准静态小变形、接触集固定、passivity 仅平移代理
   ▼
未来 ── 实机 sim-to-real、接触切换、把可解释性接到规划/控制闭环
```

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| 可观测状态 $\mathbf{z}$ | 传感 + 几何 + 接触推断 | $\mathbf{z}=(\mathbf{q},\mathbf{x}_{HT},\mathbf{w}_e,\mathcal{C},J_x,J_q)$ | 推理时同样需要全部 6 项，$J_x,J_q$ 来自解析手-工具模型 |
| Stage 1（稳定性） | $\mathbf{z}$ + 融合特征 $\mathbf{f}$ + 解析辅助量 $\Delta\hat{\mathbf{x}}_{\text{aux}},\ \mathrm{diag}(K_{x,\text{aux}})$ + 肌腱门 $g$ | $\hat{s}=\sigma(h_s[\cdot])\in[0,1]$ | 全样本训练，损失 $\mathcal{L}_{\text{stab}}=\text{BCEWithLogits}$ |
| Stage 2（位移） | 同 Stage 1 主干（独立参数） | $\Delta\hat{\mathbf{x}}_{HT}\in\mathbb{R}^6$ | **只用 GT 稳定样本训练**；推理只在 Stage 1 判为稳定的样本上跑 |
| 力学头（每阶段各一个） | 骨干特征 | 分支弹簧块 $K_{s,b}$、肌腱方向 $\mathbf{d}_b$、增益 $k_b$、门参数 $(\alpha_b,\beta_b,\rho_b)$ | $K_{s,b}\succ 0$ 结构约束；无显式数据标签，靠下游损失反传 |
| 解析层 Pass 1（弹簧-only） | $J_x, J_q, K_{\text{spring}}$ | $K_x^{(0)},\ \Delta\mathbf{x}^{(0)},\ d\mathbf{q}^{(0)}$ | 求"基线柔度"，用于推断肌腱是否拉紧 |
| 解析层 Pass 2（肌腱合并） | $K_q^{\text{eff}}=K_{\text{spring}}+K_{\text{tendon}}$ | $K_x,\ \Delta\hat{\mathbf{x}}_{HT}=K_x^{-1}\mathbf{w}_e$ | 输出最终位移；$\epsilon_M,\epsilon_{K_x},\epsilon_{J_q}$ 做数值正则 |
| 阈值 $\tau$ | 验证集调优 | 级联工作点 | 训练后选择，平衡 F1 与位移误差 |

### 1.2 关键机制

**⚡ Eureka Moment：不要在笛卡尔空间回归柔度，而要学"关节空间的正定刚度块"，让闭合雅可比的同余变换把物理结构自动长出来。**

三个支撑点：
1. **同余变换保证结构**：$K_x = J_x^\top(J_qK_q^{-1}J_q^\top)^{-1}J_x$ 是合同变换，只要 $K_q \succ 0$（弹簧块强制 SPD $K_{s,b}\succ 0$，肌腱项 $k_bg_b\mathbf{d}_b\mathbf{d}_b^\top$ 半正定），Cartesian 柔度就自动带上"力与位移同向"的定性行为 —— 这是 passivity 从 0.65 → 0.00 的机制来源，而不是靠一个软惩罚项撞出来的。
2. **两趟解析（two-pass）**：肌腱不能直接注入，要先算"纯弹簧基线"位移 $\Delta\mathbf{x}^{(0)}$，再把它反推成关节挠度 $d\mathbf{q}^{(0)}$，投影到肌腱方向得 $\eta_b=\langle d\mathbf{q}^{(0)}_b,\mathbf{d}_b\rangle$，最后过 sigmoid 门 $g_b=\sigma(\alpha_b(\eta_b-\beta_b)+\rho_b)$。即"肌腱是否咬合"是从物理上本来会发生多少变形**推断**出来的，等价于实现文中说的"two-regime compliance"（弹簧软区 / 肌腱咬合硬区）。
3. **级联而非联合回归**：先定"这抓取还有效吗"，再只对有效样本算位移 —— 与部署决策顺序一致，也把 Stage 2 的监督聚焦在物理上有意义的变形样本上。

### 1.3 信息流

```
                 q, x_HT, w_e, C, Jx, Jq
                          │
        ┌─────────────────┴─────────────────┐
        │           骨干 + 力学头            │
        │  → K_s,b (SPD), d_b, k_b, α,β,ρ    │
        └─────────────────┬─────────────────┘
                          │  K_spring = blkdiag({K_s,b})
                 ┌────────▼─────────┐
                 │   Pass 1 解析层   │
                 │ K_x^(0), Δx^(0), │
                 │      dq^(0)      │
                 └────────┬─────────┘
                          │ η_b = <dq_b^(0), d_b>
                          │ g_b = σ(α_b(η_b-β_b)+ρ_b)
                          │ K_tendon,b = (k_b g_b) d_b d_bᵀ
                 ┌────────▼─────────┐
                 │ K_q^eff = K_spring + K_tendon
                 │   Pass 2 解析层   │
                 │ K_x = Jxᵀ(Jq(Kq^eff)⁻¹Jqᵀ+ε_M I)⁻¹Jx
                 └────────┬─────────┘
            ┌─────────────┴──────────────┐
            ▼                            ▼
   Stage1 头: ŝ = σ(h_s[f, Δx̂_aux,    Δx̂_HT = K_x⁻¹ w_e
              diag(K_x,aux), g])         （仅当 ŝ > τ）
```

## 2 · 数学核心

📌 **Napkin Formula**：
$$K_x = J_x^\top\big(J_qK_q^{-1}J_q^\top\big)^{-1}J_x,\qquad \Delta\hat{\mathbf{x}}_{HT}=K_x^{-1}\mathbf{w}_e$$
—— 网络不预测位移，网络预测"关节有多硬"，位移是物理推出来的。

**目标**：在准静态、刚体、库仑摩擦假设下，给出外部力旋量 $\mathbf{w}_e$ 到手内工具位姿偏移 $\Delta\mathbf{x}_{HT}$ 的局部线性映射，并保证该映射不为系统凭空造能量。

**公式链**：
- 局部刚度定义（式 4）：$K_x=\partial\mathbf{w}/\partial\mathbf{x}$，局部有 $\Delta\mathbf{w}\approx K_x\Delta\mathbf{x}$。
- 平行机构视角：把工具当动平台、掌当基座，每根手指是一条运动支链 —— 这正是欠驱动手"多指通过同一工具机械耦合"的准确刻画。
- 线性化闭合 + 静力（式 5-6）：$J_xd\mathbf{x}+J_qd\mathbf{q}=0$，$d\mathbf{w}=J^\top d\boldsymbol{\tau}$，$d\boldsymbol{\tau}=K_qd\mathbf{q}$。
- 消去 $d\mathbf{q}$ 得式 7；网络里 $K_q$ 被替换成 $K_q^{\text{eff}}$（式 17），并加三个正则 $\epsilon_M I$、$\epsilon_{K_x}I$、$\epsilon_{J_q}I$（式 11、12、18）。

**变量说明**：

| 符号 | 含义 | 谁提供 |
|---|---|---|
| $\mathbf{q}\in\mathbb{R}^8$ | 手部关节坐标（两指各 3 + 拇指 2） | 关节传感器 |
| $\mathbf{x}_{HT}\in\mathbb{R}^6$ | 名义手-工具位姿 | 几何/运动学 |
| $\mathbf{w}_e\in\mathbb{R}^6$ | 外部力旋量 | 腕部六轴力/力矩传感器 |
| $\mathcal{C}$ | 估计的接触集 | 接触推断 |
| $J_x,J_q$ | 闭合雅可比 | 解析手-工具模型 |
| $K_{\text{spring}}=\mathrm{blkdiag}(\{K_{s,b}\})$ | 分支弹簧块，$K_{s,b}\succ 0$ | 力学头（可学习） |
| $g_b\in[0,1]$ | 第 $b$ 支链肌腱咬合度 | 由 Pass 1 挠度推断 |

**直觉**：$J_qK_q^{-1}J_q^\top$ 是"关节柔度投影到闭合约束空间"，取逆后再被 $J_x$ 两侧合同夹住 —— 这就是手掌-手指-工具闭链的柔度组装。学 $K_q$ 而不是学 $K_x$，等于把网络的可表达空间限制在"物理上可能的柔度"内部，非物理预测在参数化层面就被排除了。

**损失**：$\mathcal{L}_{\text{disp}}=\mathcal{L}_{\text{pose}}+\mathcal{L}_{\text{str}}$，其中平移用欧氏、旋转用测地角误差；结构正则有 $\mathcal{L}_{\text{gate}}=\text{mean}(\mathbf{g}\odot(1-\mathbf{g}))$（把门推向 0/1 的自信饱和）、$\mathcal{L}_{\text{ten}}=\text{mean}(K_{\text{tendon}}\odot K_{\text{tendon}})$（压制肌腱刚度幅度、改善条件数）。

## 3 · 带数字走一遍

> 以下为**玩具设定**，只用来说明公式链的量级行为，非论文数据。

取单支链标量简化：$J_x=1$，$J_q=1$，弹簧刚度 $K_{\text{spring}}=100$（N/m 量级），外载荷 $w_e=5$。

**Pass 1（弹簧-only）**：
$$K_x^{(0)}=(1\cdot100^{-1}\cdot1)^{-1}=100,\quad \Delta x^{(0)}=5/100=0.05$$
$$dq^{(0)}=-J_q^{-1}J_x\Delta x^{(0)}=-0.05$$

**肌腱门控**：设方向 $\mathbf{d}_b=-1$（符号使挠度沿肌腱拉伸方向为正），则 $\eta_b=\langle dq^{(0)},\mathbf{d}_b\rangle=0.05$。取 $\alpha=60,\beta=0.03,\rho=0$：
$$g=\sigma\big(60(0.05-0.03)\big)=\sigma(1.2)=0.769$$
取 $k_b=400$：$K_{\text{tendon}}=400\times0.769\times1=307.6$，$K_q^{\text{eff}}=100+307.6=407.6$。

**Pass 2**：
$$K_x=407.6,\qquad \Delta\hat{x}_{HT}=5/407.6=0.01227$$

对比 Pass 1 的 0.05：肌腱一旦咬合，位移掉到约 1/4 —— 这就是文中"two-regime compliance"的数值形态。四个关键工程性质在此一次性可见：
1. 位移方向恒与力同向（$K_x>0$），**结构上不可能出现负功**；
2. 门 $g$ 由 $dq^{(0)}$ 决定，梯度可以沿 Pass 1 回传到 $K_{s,b}$ 与 $k_b$；
3. $\mathcal{L}_{\text{gate}}$ 会把 $g=0.769$ 往 0 或 1 推，即"要么明显没咬合、要么明显咬合"，避免半开半闭的病态工作点；
4. 若换成黑盒 MLP 预测出 $\Delta x=-0.01$，则 signed work $=5\times(-0.01)=-0.05<0$ —— 正是文中 passivity 判据要抓的那类"预测工具朝反方向动"的非物理输出。

## 4 · 工程视角

**论文未报告**以下任何一项：推理延迟、FPS、模型参数量绝对值、显存/内存占用、CPU/GPU 型号、训练时长、单次前向的实测耗时。论文只说 AMINN 与 Cascade MLP 使用"matched parameter budgets"、相同训练计划、相同随机种子（**未报告种子个数与方差**）。故下表只给可推导的结构性特征，数字一律标 `UNVERIFIED`：

| 维度 | 情况 |
|---|---|
| 单样本计算结构 | 两次 6×6 量级矩阵求逆/组装（$J_qK_q^{-1}J_q^\top$ 是 $8\times8$ 内层）+ 若干 MLP 前向；无迭代求解、无 FEA 网格 |
| 延迟 / FPS | **论文未报告** |
| 参数量 | **论文未报告**（仅"matched parameter budgets"） |
| 内存 | **论文未报告** |
| 硬件 | **论文未报告**（实机平台只描述了机构与传感器，未给计算单元） |
| 部署前置依赖 | 推理时需要 $J_x,J_q,\mathcal{C}$ 全部可用 → 依赖解析手-工具模型 + 接触推断；这是比算力更硬的部署约束 |
| 数值稳定性 | 解析层靠 $\epsilon_M,\epsilon_{K_x},\epsilon_{J_q}$ 三项正则；$J_q$ 接近奇异时 $K_x$ 会被放大（`UNVERIFIED`：具体条件数阈值论文未给） |
| 训练成本 | 两阶段串行（Stage 1 全样本 → Stage 2 仅稳定样本），Stage 2 训练集小于 Stage 1；**具体规模未报告** |

**Trade-off 判断**：这是一个"用解析层换可信度、几乎不付算力代价"的方案 —— 解析层是闭式的矩阵运算，不是 FEA，所以相比黑盒基线**额外开销主要在 6×6/8×8 求逆与两次 pass**，而非数量级差异（`UNVERIFIED` 推断）。真正的部署风险不在延迟，而在**输入可得性**（接触集 $\mathcal{C}$、雅可比）与**数值条件数**。

## 5 · 数据与评测

**数据来源：纯仿真，无实机数据。** 论文明确写"Simulation-based experimental results on a three-finger underactuated robotic hand"。

- **仿真环境**：与腱驱动欠驱动架构一致的物理仿真；8-DoF 手，由 **2 个位置执行器 + 6 个自定义肌腱执行器**驱动，外加 **1 个 6-DoF 基座执行器**定位腕部；模型含腱走线、被动手部柔度（如扭转弹簧）、接触动力学。
- **采样降维**：跟随 [46] 使用手部协同启发子空间 $\mathbf{T}\in\mathbb{R}^3$，三轴为 size $\sigma$（开/合）、spread $\alpha$（指间展开）、curl $\epsilon$（指弯曲）；投影矩阵 $A=[\boldsymbol{\alpha}_H\ \boldsymbol{\sigma}_H\ \boldsymbol{\epsilon}_H]\in\mathbb{R}^{N\times3}$，配中性位姿 $\mathbf{o}$ 与每轴缩放 $\boldsymbol{\delta}$ 把 $\mathbf{q}$ 映到 $\boldsymbol{\psi}$。动机是避免全关节空间随机采样产生大量不可行/任务无关位姿。
- **载荷生成**：每个可行抓取位姿配多个随机扰动扳手（方向与幅值随机），每个抓取对应多个 load case。
- **样本字段**：$(\mathbf{q},\mathbf{x}_{HT},\mathbf{w}_e,\mathcal{C},J_x,J_q,\Delta\mathbf{x}_{HT},s)$，位移为监督目标，$s\in\{0,1\}$ 为稳定性标签。
- **数据集规模、训练/验证/测试划分比例**：**论文未报告**（图 9 提到 "IID test split"，§4.3 提到用 validation data 选工作点，但均未给样本数）。

**评测协议**：Cascade AMINN vs Cascade MLP（黑盒多层感知机基线）。两者输入相同、参数预算匹配、训练计划相同、随机种子相同、两阶段级联结构相同。三个指标：稳定性 **F1**、位移 **RMSE pose**、**Passivity violation rate**（对判为稳定的样本计算平移力与预测平移位移的有符号功 $w=\mathbf{w}_e^{\text{tr}}\cdot\Delta\hat{\mathbf{x}}_{HT}^{\text{tr}}$，$w<0$ 计为一次违反，越低越好）。

**Table 1（逐字照抄）**：

| 指标 | Cascade AMINN | Cascade MLP |
|---|---|---|
| F1 ↑ | 0.96 | 0.95 |
| RMSE pose ↓ | 0.05 | 0.08 |
| Passivity ↓ | 0.00 | 0.65 |

**条件说明**：这是一组**单一工作点**下的结果 —— 级联阈值 $\tau$ 是在验证集上、为平衡稳定过滤质量与位移误差而选定的；RMSE pose 的**单位与构成（平移/旋转是否分列）论文未报告**；表内数值只到小数点后两位，**未给方差或置信区间**。因此 F1 0.96 vs 0.95 的差异**不足以**支撑"精度更优"的强结论；能站住的是 passivity 0.00 vs 0.65 这个量级差。

## 6 · 能力与失败模式

**能做**：
- 在同一模型里同时输出**二值稳定性概率**与**6 维手内工具位移**，且次序符合部署决策逻辑（先判可用性、再算量）。
- 输出**机械可解释的中间量**：分支弹簧块 $K_{s,b}$、肌腱方向 $\mathbf{d}_b$、每支链咬合度 $g_b$、$K_x$ 对角项 —— 这些可以直接被人读懂，而不只是注意力热图。
- 在**准静态、刚体、库仑摩擦**的加载条件下保持能量一致：passivity violation 0.00（vs 基线 0.65）。
- 位移精度优于同预算黑盒基线（RMSE pose 0.05 vs 0.08），F1 基本持平（0.96 vs 0.95）。

**不能做 / 明确出界**：
- **高速冲击瞬态**：论文明确写 "high-speed impact transients are out of scope"。
- **大变形**：式 5-7 是速度级/线性化闭合，$\Delta\mathbf{w}\approx K_x\Delta\mathbf{x}$ 只在局部有效。
- **接触集切换**：把抓取建模为"固定支链数的平行机构"，$\mathcal{C}$ 视为给定；"richer contact transitions" 被列为未来工作。
- **实机泛化**：全部结果来自仿真，没有 sim-to-real 数字。
- **旋转方向的能量一致性**：passivity 判据只用了平移分量 $\mathbf{w}_e^{\text{tr}}\cdot\Delta\hat{\mathbf{x}}_{HT}^{\text{tr}}$，旋转功未纳入检查 —— 也就是说"预测出一个非物理的转动"不会被这个指标抓住。

### 隐含假设 (Hidden Assumptions)

1. **接触集 $\mathcal{C}$ 是可靠的**：它被当作输入而非待估状态，但图 2 的动机又强调实机传感稀疏 —— 实际部署时 $\mathcal{C}$ 只能靠接触推断近似。$\mathcal{C}$ 错 → $J_x,J_q$ 错 → 整条解析链错。
2. **准静态 + 刚体 + 库仑摩擦三者同时成立**：放松任一条（比如工具是软材料、或施力有加速度），式 4 的 $K_x$ 定义就失去意义。
3. **局部线性化在采样载荷范围内成立**：位移监督标签由仿真产生，但训练时并未约束"样本必须落在小变形区"，若仿真中某些 load case 已超出线性区，$\Delta\mathbf{x}_{HT}$ 标签本身就带模型误差。
4. **$K_q$ 可由块对角弹簧 + 秩一半正定肌腱项充分表达**：这是很强的结构假设 —— 它排除了关节间刚度耦合（off-diagonal 耦合只能经由 $J_q$ 间接出现），也排除了肌腱间的相互耦合。
5. **Stage 2 的输入分布 = 稳定样本分布**：Stage 2 只用 GT 稳定样本训练，但推理时它接收的是 **Stage 1 判为稳定**的样本。二者的差集就是"Stage 1 漏判"的区域，$K_x^{-1}\mathbf{w}_e$ 在这些点上没有任何监督保障。
6. **$\mathrm{diag}(K_{x,\text{aux}})$ 足以代表力学信息**：式 9 只把 $K_{x,\text{aux}}$ 的对角线喂给 Stage 1 头，所有耦合/非对角刚度信息在稳定性判断这条路径上被丢弃。
7. **拇指基座滚动 DoF 缺失是可容忍的**：式 30 的实现中"missing coordinates (e.g., the thumb base rolling DoF) are handled by masking in $J_q$"，等价于承认运动学模型不完备并用掩码绕过。
8. **技能子空间 $\mathbf{T}\in\mathbb{R}^3$ 覆盖了任务相关的抓取多样性**：数据分布由三轴（size/spread/curl）协同基决定，落在该子空间外的抓取（例如非协同的手指独立构型）不在训练分布内。

## 7 · 与相关工作对比

| 路线 | 代表工作 | 输出 | 物理可解释性 | 对欠驱动手工具用力的适配性 |
|---|---|---|---|---|
| 力闭合 / 扳手空间判据 | [1-6] | 能否抵抗扰动的二值/裕度 | 高（显式约束） | 只答"能否抵抗"，不答"会移动多少" |
| 二值抓取成功学习 | Dex-Net 2.0 [11]、QT-Opt [12]、触觉稳定性分类 [13] | success/failure | 低 | 迁移/筛选有效，不建模受力位移 |
| 刚度解析建模 | VJM [18]、MSA [19]、FEA [20]；Chen & Kao [23] | 笛卡尔刚度矩阵 | 最高 | 需难辨识的刚度参数；系统复杂后完整模型"often difficult or not always practically available" |
| 欠驱动手力学/顺应性分析 | Ciocarlie & Allen [36]、Malvezzi & Prattichizzo [39]、Chen et al. [40] | 滑移/不平衡力/抓取刚度 | 高 | 有机制洞察，但没有嵌入学习模型的力旋量条件预测器 |
| 纯黑盒学习 | 本文的 Cascade MLP 基线 | 稳定性 + 位移 | 低 | 精度可用，但 passivity 0.65，存在非物理输出风险 |
| **AMINN（本文）** | — | 稳定性 + 6 维位移 + 可读中间量 | 中高（结构约束而非纯软惩罚） | 精度与黑盒同级、能量一致性显著更好；代价是强结构假设 + 需 $\mathcal{C},J_x,J_q$ |

**面试 Tip**：被问到"这跟 physics-informed learning 有什么不一样"时，答**约束的位置不同**——常见做法是在损失里加物理残差项（软约束，可以被数据压过去），AMINN 是把 SPD 刚度块作为**网络输出层的参数化**、再用合同变换把结构"焊死"在计算图里，所以 passivity 是结构性推论而非训练出来的偏好；然后再补一句"但它把赌注押在准静态小变形 + 固定接触集 + 可靠 $\mathcal{C}$ 上"。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-28)

**官方 repo 未在论文中给出**：全文（含 HTML 页面文本）未出现任何 `github.com` 链接，因此**不做任何 issue / commit / PR 级验证**。以下 3 条 pitfall 由 §6 的失败模式 + §4.2/§4.3 的方法约束**机械推导**，标注为"未经 issue 验证"。

1. **把论文的 passivity 指标当作部署验收门，会漏掉旋转方向的非物理预测。**
   推导链：§6 已指出判据只用平移分量 → 图 9 定义 $w=\mathbf{w}_e^{\text{tr}}\cdot\Delta\hat{\mathbf{x}}_{HT}^{\text{tr}}$ → 式 19 输出的是完整 6 维 $\Delta\hat{\mathbf{x}}_{HT}$，其中旋转 3 维**完全不参与**该判据。工程后果：一个在平移上完美、但在旋转上"反向发力"的预测仍会得到 passivity = 0.00。修复方向：把判据扩成完整旋量功 $\mathbf{w}_e^\top\Delta\hat{\mathbf{x}}_{HT}$（含力矩·角位移项），并单独监控旋转分量。

2. **$J_q$ 近奇异时整条解析链会给出"过度刚硬"的位移，且不会被精度指标报警。**
   推导链：§6 假设 4/7 → $K_x=J_x^\top(J_q(K_q^{\text{eff}})^{-1}J_q^\top+\epsilon_MI)^{-1}J_x$（式 18）→ $J_q$ 秩亏或接近秩亏时，$J_qK_q^{-1}J_q^\top$ 的最小特征值趋近 0，被 $\epsilon_M$ 截断后其逆在正交方向被放大，$K_x$ 随之爆大，$\Delta\hat{\mathbf{x}}_{HT}=K_x^{-1}\mathbf{w}_e$ 趋近 0。而拇指基座滚动 DoF 本就用**掩码**处理（式 30 的实现说明），掩码后的 $J_q$ 列结构天然更容易秩亏。工程后果：模型在"抓得很紧/构型奇特"的样本上系统性低估位移，表现为过度自信的安全假象；F1 与 RMSE 在整体平均下都不敏感。修复方向：显式监控 $J_q$ 的条件数与 $\epsilon_M$ 的比值，把接近截断阈值的样本标为 out-of-distribution 并拒答。

3. **换一个级联阈值 $\tau$，论文报告的 RMSE pose 0.05 就不再成立。**
   推导链：§4.3 明说工作点是**训练后在验证集上**选定的（平衡稳定过滤质量与下游位移误差）→ §6 假设 5：Stage 2 只用 GT 稳定样本训练，推理却接收 Stage 1 判稳的样本。工程后果：把 $\tau$ 调低（更激进地放行）会把更多边界样本送进 Stage 2，而这些样本既不在其训练分布内、也不再是论文评测的那个工作点，位移误差会以不可预期的方式漂移；反之调高 $\tau$ 会让可用样本骤减。落地时**必须把 $\tau$ 当作一起发布的一等参数**，并在自己的数据上重新选点、重新报 RMSE，而不是引用 0.05。

（补充说明：论文表格只到两位小数、未报方差、未报种子次数，因此"AMINN 精度优于 MLP"这一条在复现前应视为**方向性结论**，`UNVERIFIED`。）

---
[← Back to Robotics Manipulation README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文（arXiv:2607.17541v1，含正文、公式、Table 1）· 未在真机复现的数字标 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2607.17541 -->"
