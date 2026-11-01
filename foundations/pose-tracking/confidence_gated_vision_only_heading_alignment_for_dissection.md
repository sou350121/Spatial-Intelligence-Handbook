[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: mono
paradigm: learned
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->"

# 置信度门控的纯视觉航向对齐：UAV–UGV 协同系统 (Confidence-Gated Vision-Only Heading Alignment for UAV–UGV Cooperative Systems)

> **发布时间**：2026-07-21（arXiv:2607.18713v1 [cs.RO]）
> **论文 / 模型名**：Confidence-Gated Vision-Only Heading Alignment（无独立模型代号；决策层 = 双代理置信门 + bounded-blend fallback）
> **核心定位**：它不造更好的航向预测器，而是回答"**预测对不对**"之后的第二个问题——"**这一帧的预测该不该直接下发成控制指令**"；用两个 0 参数、可解释的可靠性代理把"预测精度"问题改写成"execute/HOLD 决策"问题。

导语：视觉航向预测的平均误差很低，并不代表每一步的输出都值得直接送进控制环——退化可见性下的抖动会变成振荡指令。本文在既有冻结预测器上加一层轻量门控，并证明**"只门控、不管 fallback"本身会失败**：稀疏执行会让指令冻结成 stale command，指令误差反而炸到 3.2°，而一个带泄漏的 bounded-blend 更新在同一套门控决策下把它压回 0.5°。

---

## X-Ray 开场

本文解决的痛点不在感知侧：给定一个**已训练好、被冻结**的视觉航向预测器 $f:\mathbb{R}^4\to\mathbb{R}$，系统仍需决定"当前 $\hat\theta_t$ 够不够可靠到可以直接当控制指令"。作者提出**双代理置信门**（bbox 面积 = 可见性、滑窗航向标准差 = 稳定性）+ **execute/HOLD 决策**，并进一步把"低置信区间指令怎么演化"提升为决策问题的一部分：对比 baseline freeze-HOLD 与 bounded-blend fallback。对 spatial AI 研究者意味着：**perception-to-control 之间的这一层"信任接口"是独立可研究的对象**，而且它的失效模式（stale command）与感知精度无关，光看 MAE 完全看不出来。

---

## 📍 研究全景时间线

```
2017  Guo et al. 神经网络置信度校准差  ─┐
2017  Gal & Ghahramani  MC-Dropout 不确定性 ─┤ 不确定性/可信度
2017  Kendall & Gal  aleatoric vs epistemic ─┤ 文献（本文的动机来源，
2017  Lakshminarayanan  Deep Ensembles ──────┤  但不是本文方法）
2018  Geifman & El-Yaniv  selective prediction（弃权）─┘
             │
2017-2020  Morales / Falanga / Wu：视觉跟随与降落（只解决"能不能估"）
             │
     ┌──── [17] 前期工作：视觉航向预测器 f(·)（本文直接冻结复用）
     ▼
★ 2026 本文：把"预测"与"执行"切开 — 双代理置信门 + fallback-aware 决策
     │        （单序列、室内 VICON、开环 replay、无闭环控制）
     ▼
 future：更多可靠性代理 / 在线自适应阈值 / 更长时程闭环实验（作者自述）
```

**本文在演进中的位置**：它不是"更好的感知"，而是无人机–无人车协同链路里被长期忽略的一段——**decision interface**。**本文局限**：单条真实序列、室内 VICON、扰动为特征空间高斯噪声、全程开环 replay（指令不回灌进观测），且 fallback 的 $\alpha,\rho,\bar h$ 与滑窗 $k$ **均未给出数值**（见 §8）。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统/组件对比表

| 模块 | 输入 | 输出 | 训练 vs 推理 | 本论文贡献 |
|---|---|---|---|---|
| 感知：航向预测器 $f(\cdot)$ | $\mathbf{x}_t=[cx_t,cy_t,area_t,aspect\_ratio_t]^\top\in\mathbb{R}^4$ | $\hat\theta_t\in\mathbb{R}$ | **已训练、全程冻结**；架构/训练/单独性能见 [17] | ❌ 不重设计、不重训练 |
| 可见性代理 | $area_t$（bbox 面积 / 全图面积，无量纲） | 与 $\tau_{area}$ 比较 | 无需训练；纯查表式比较 | ✅ |
| 稳定性代理 | 最近 $k$ 帧 $\{\hat\theta_{t-j}\}_{j=0}^{k-1}$ | $\sigma_\theta(t)$（度） | 无需训练；滚动统计 | ✅ |
| 门控策略 (7) | $area_t,\ \sigma_\theta(t)$ | $a_t\in\{\text{EXECUTE},\text{HOLD}\}$ | 两阈值在**校准子集**上 Pareto 网格搜索后固定 | ✅ |
| Fallback 指令更新 | $a_t$、$h_t$（连续 HOLD 步数）、$u_{t-1}$、$\hat\theta_t$ | $u_t$（真正下发的指令） | 无学习；一阶泄漏积分，$\alpha/\rho/\bar h$ 论文未给数值 | ✅ 核心 |
| 评测 | $\theta_t,\hat\theta_t,u_t$ | ExecFrac / $\mathrm{MAE_{exec}}$ / $\mathrm{MAE_{issued}}$ / $\bar J$ | 离线 | ✅ 决策级指标 |

> 关键结构性事实：**本文没有任何"训练"环节**。全篇唯一的"拟合"是在校准子集上对两个标量阈值做网格搜索；决策层本身是 hand-designed 规则。ontology 里 `paradigm=learned` 指的是被复用的预测器，**不是**这层决策。

### 1.2 关键机制

**⚡ Eureka Moment：置信度门控不是"多加一个 if"，而是一个 fallback-aware 决策问题——一旦执行变稀疏，指令流的质量就不再由门决定，而由"门关着的时候你在干什么"决定。**

拆开看是三件事被显式分离（论文 §III-C 原文语气）：

1. **perception problem** → 冻结的 $f(\cdot)$；
2. **decision problem** → $a_t$（该不该完整执行）；
3. **fallback command-update problem** → $u_t$ 在低置信区间怎么演化。

第 3 点是本文真正的新意：baseline freeze-HOLD（$u_t=u_{t-1}$）在 $\sigma_c=0.02$ 下把执行率压到 1.63%，executed-only MAE 只有 0.4397°（很干净！），但 issued MAE 飙到 3.2153°——**jerk 极小 0.0805 的同时指令误差极大**，这组"又平滑又错"的组合正是 stale command 的指纹。bounded-blend 更新（同一套门决策）把它拉回 0.4959°。

### 1.3 信息流

```
 图像 ──► bbox 检测 ──► x_t = [cx, cy, area, aspect] ──► f(·)  [frozen, 来自 [17]]
                              │                                  │
                              │ area_t                           │ θ̂_t
                              ▼                                  ▼
                    ┌──────────────────┐            ┌──────────────────────────┐
                    │ 可见性代理        │            │ 稳定性代理                │
                    │ area_t ≥ τ_area? │            │ σ_θ(t) ≤ τ_σ ?  (k-窗口) │
                    └────────┬─────────┘            └────────────┬─────────────┘
                             └──────────► AND ◄──────────────────┘
                                          │
                              a_t ∈ {EXECUTE, HOLD}
                                 │                    │
                    a_t=EXECUTE  ▼                    ▼  a_t=HOLD
                          u_t = θ̂_t        h_t ≤ h̄ : u_t=(1-α)u_{t-1}+α θ̂_t
                                           h_t > h̄ : u_t=(1-ρ)u_{t-1}+ρ θ̂_t
                                 └──────────┬─────────┘
                                            ▼
                              u_t ──► 控制环（本文中仅离线评测，未闭环）
                              u_t ──► 指标：ExecFrac / MAE_exec / MAE_issued / J̄
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$
a_t=\text{EXECUTE} \iff \underbrace{area_t\ge\tau_{area}}_{\text{看得够大}}\ \wedge\ \underbrace{\sigma_\theta(t)\le\tau_\sigma}_{\text{最近够稳}};\qquad
u_t=\begin{cases}\hat\theta_t & \text{EXECUTE}\\[2pt] (1-\alpha)u_{t-1}+\alpha\hat\theta_t & \text{HOLD}\end{cases}
$$

一句话直觉：**门只决定"要不要相信这一帧"，一个带泄漏的一阶低通决定"不信的时候往哪儿漂"；只用门不写 fallback = 冻死。**

### 2.1 观测与预测模型

目标、公式、变量、直觉：

- **目标**：把感知输出变成可判定可靠性的低维特征。
- 公式 (1)：$\mathbf{x}_t=[cx_t,\;cy_t,\;area_t,\;aspect\_ratio_t]^\top\in\mathbb{R}^4$，(2 后) $\hat\theta_t=f(\mathbf{x}_t)$，$f$ **固定**。
- 变量：$cx,cy$ = bbox 质心；$area$ = bbox 面积 / 全图面积（无量纲，见 §VI-A 说明）；$aspect\_ratio$ = 长宽比；$\theta_t$ = 真值航向。
- 直觉：**只保留 4 个几何量**，所以门控也只用其中 2 个派生量——这是"轻量"的来源，也是它的天花板（见 §6）。

### 2.2 两个可靠性代理

- **可见性（§IV-B）**：直接用 $area_t$。面积小 ⇒ 目标在图上占的像素少 ⇒ 证据弱。
- **稳定性（§IV-C）**：对窗口 $k\ge 2$，
  公式 (5)：$\bar\theta_t=\frac1k\sum_{j=0}^{k-1}\hat\theta_{t-j}$；
  公式 (6)：$\sigma_\theta(t)=\sqrt{\frac1k\sum_{j=0}^{k-1}\big(\hat\theta_{t-j}-\bar\theta_t\big)^2},\ t\ge k$。
  注意是**总体**标准差（除以 $k$，不是 $k-1$），且 $\sigma_\theta$ 只对 $t\ge k$ 定义。
- 直觉：$\sigma_\theta$ 是"预测器自我一致性"的代理——不需要真值，不需要模型内部方差，一个滑窗即可。

### 2.3 门控与指令更新

- 公式 (7)：$a_t=\text{EXECUTE}$ 当且仅当 $area_t\ge\tau_{area}\wedge\sigma_\theta(t)\le\tau_\sigma$，否则 HOLD。
- 公式 (3)（bounded-blend）：
$$
u_t=\begin{cases}\hat\theta_t, & a_t=\text{EXECUTE}\\[3pt]
(1-\alpha)u_{t-1}+\alpha\hat\theta_t, & a_t=\text{HOLD}\ \wedge\ h_t\le\bar h\\[3pt]
(1-\rho)u_{t-1}+\rho\hat\theta_t, & a_t=\text{HOLD}\ \wedge\ h_t>\bar h\end{cases}
$$
- 公式 (4)（baseline freeze-HOLD）：$u_t=u_{t-1}$ if $a_t=\text{HOLD}$。
- 变量：$h_t$ = 截至 $t$ 的连续 HOLD 步数；$\alpha$ = 短时保持混合因子；$\bar h$ = 最大 bounded-hold 时长；$\rho$ = 长时间低置信下的"恢复/泄放"因子。
- **直觉**：HOLD 不是"停止"，而是"以 $\alpha$ 的步长往当前预测挪一点"；超过 $\bar h$ 步后改用 $\rho$ 再挪——两段式泄漏，防止指令离真值越来越远。freeze-HOLD 相当于 $\alpha=\rho=0$。

### 2.4 决策级指标

- (10) $\mathrm{ExecFrac}=\frac1T\sum_t\mathbb{I}[a_t=\text{EXECUTE}]$
- (11) $\mathrm{MAE_{exec}}=\frac1{|\mathcal E|}\sum_{t\in\mathcal E}|\theta_t-\hat\theta_t|$，$\mathcal E=\{t:a_t=\text{EXECUTE}\}$
- (12) $\mathrm{MAE_{issued}}=\frac1T\sum_t|\theta_t-u_t|$ ← **本文真正的"系统级"指标**
- (13)(14) $J(t)=|u_t-2u_{t-1}+u_{t-2}|$，$\bar J=\frac1{T-2}\sum_{t=3}^{T}J(t)$

**为什么必须四个一起看**：(11) 只看被放行的子集，天然可被"少放行"刷高；(14) 只看平滑度，天然可被"冻住"刷高；只有 (12) 同时惩罚"信错了"和"冻太久"。

---

## 3 · 带数字走一遍（**玩具设定**）

> 下面 $\alpha=0.2,\ \rho=0.05,\ \bar h=3,\ k=3$ 是**我为演示自选的玩具值**——论文没有给出 $\alpha,\rho,\bar h,k$ 的数值。阈值用论文真值：$\tau_{area}=0.025583$，$\tau_\sigma=0.256323^\circ$。

设真值航向在缓慢增大，但目标被遮挡，bbox 面积在缩：

| $t$ | $area_t$ | $\hat\theta_t$ | 窗口 std $\sigma_\theta$ | 门 | $h_t$ | $u_t$ | 说明 |
|---|---|---|---|---|---|---|---|
| 1 | 0.030 | 10.0° | —（$t<k$） | 假定 EXECUTE | 0 | 10.00° | 窗口未满，$\sigma_\theta$ 无定义 |
| 2 | 0.020 | 12.0° | — | **HOLD**（$0.020<0.025583$） | 1 | 0.8×10.00+0.2×12.0 = **10.40°** | 面积不够 |
| 3 | 0.012 | 12.6° | mean=11.533, $\sigma$=**1.1116°** | **HOLD**（双条件都不满足） | 2 | 0.8×10.40+0.2×12.6 = **10.84°** | |
| 4 | 0.040 ✅ | 14.0° | mean=12.867, $\sigma$=**0.8380°** | **HOLD**（$\sigma>\tau_\sigma$） | 3 | 0.8×10.84+0.2×14.0 = **11.47°** | 面积恢复了，**稳定性仍拦** |
| 5 | 0.041 ✅ | 14.5° | mean=13.700, $\sigma$=**0.2217°** ✅ | **EXECUTE** | 0 | **14.50°** | 全窗一致 → 放行 |

**读法一（门的作用）**：$t=4$ 时可见性已经完全恢复，但 $t=3\!\to\!4$ 的跳变让 $\sigma_\theta$ 仍高于阈值 → 继续 HOLD。稳定性代理是**滞后指标**：它必然比可见性晚一步恢复。

**读法二（freeze vs blend，同一套门）**：假设 $t=2\ldots9$ 全 HOLD、真值一路涨到 20°，而 $\hat\theta$ 一直粘在 12° 附近：

- freeze-HOLD（式 4）：$u$ 冻在 **10.00°**，到 $t=9$ 的 $|\theta-u|\approx10°$ —— 这就是论文在 $\sigma_c=0.02$ 下看到的 3.2153° 的同款机制，只是玩具里更极端。
- bounded-blend（$\alpha=0.2$）：$u$ 每步向 12° 挪 20%，$t=2..9$ 后 $u\to12°$ 附近，误差 ~8°；若 $\bar h$ 已过、切到 $\rho=0.05$，会**慢得多**。

**读法三（阈值尺度感——这是本文最"反直觉"的工程事实）**：干净序列上预测器 $\mathrm{MAE}=0.094285^\circ$，而 $\tau_\sigma=0.256323^\circ$ 只比它大 **2.7 倍**。也就是说门对"窗口 std"极其敏感：只要出现约 0.9° 量级的抖动（对应 $\sigma_c=0.02$ 时 executed-only MAE 已到 0.4397°，整段噪声更大），门就会几乎全关——这正好解释了为什么 $\sigma_c=0.02$ 时执行率塌到 1.63%。**门不是线性变严的，是断崖式关死的。**

---

## 4 · 工程视角

**论文未报告** 任何 latency / FPS / 吞吐 / 显存 / 硬件型号 / 功耗（无 Jetson、无 PX4、无 ROS 节点时延测量）。以下仅给出**可从方法结构直接推出**的部分，其余一律标 `UNVERIFIED`。

| 维度 | 数值 / 结论 | 来源 |
|---|---|---|
| 决策层额外算力 | 每步 $O(k)$（滑窗求和/平方和）+ 2 次标量比较；可用增量式滚动方差降到 $O(1)$/步 | 由式 (5)(6) 推出 |
| 决策层额外内存 | $O(k)$ 个航向缓存 + $u_{t-1},h_t$ | 由式 (3)(6) 推出 |
| 端到端帧延迟 / FPS | **论文未报告** | — |
| 预测器 $f$ 的推理开销、参数、硬件 | **论文未报告**（论文明确说见 [17]） | — |
| 闭环控制时延、飞控接口 | **论文未报告**；全篇为离线 replay，指令未回灌观测 | §V、§VII |
| 数值稳定细节 | 式 (6) 为总体 std，$t<k$ 未定义；式 (5)(6) 对 $\hat\theta\in\mathbb{R}$ 做**算术**平均 → 跨 ±180° 环绕需先 unwrap | 由式 (5)(6) 推出 |
| 阈值部署形态 | 标量对 $(\tau_{area},\tau_\sigma)$，离线网格搜索后**固定**，无在线自适应 | §IV-F、§VI-A |
| Fallback 超参 | $\alpha,\rho,\bar h$ **论文未给出任何数值**；$\rho$ 仅描述为"recovery blending factor" | §III-C、§IV-E |
| 可部署性最大怀疑点 | 决策层本身极轻（这才是论文的卖点："computationally lightweight"），真正成本在 bbox 检测器与 $f$；论文未讨论两者失败相关性 | §IV-A |

**Trade-off 的工程语言**（数字全取自论文，见 §5）：
- 想压**指令误差**：在 area 扰动下，全门 + blend 把 issued MAE 从 always-execute 的 0.2283° 降到 0.2477°… 等等——注意这里 **0.2477 > 0.2283**，即**最激进的 blend 策略在 area 扰动下仍不如全程直发**；只有在 centroid 扰动下 blend 才有系统级收益（0.4959 vs 3.2153）。部署选型必须先判断"你的失效主要是质心抖动还是面积抖动"。
- 想压**抖动**：clean 上 area-only 的 jerk 0.016980 甚至略优于 always-execute 的 0.018487，而稳定性门反而把 jerk 拉到 0.022653——**稳定性门不是免费的平滑器**。
- 想保**可用率**：稳定性门在 centroid 噪声下会把执行率打到 1.66%，如果下游是 50 Hz 的姿态外环，这等价于"几乎不给新参考"。

---

## 5 · 数据与评测

**数据组成**

- 数据集：**"the real UAV–UGV visual-heading dataset originally collected and described in [17]"** —— 即本文**不发布新数据集**，沿用前期工作的真实 UAV–UGV 视觉航向数据集。原文**没有给出该数据集的公开名称、序列条数、帧数 $T$、采样率**。
- 采集环境：**室内实验室（indoor laboratory environment）**。
- 真值：**VICON motion-capture system**，原文称提供 **"millimeter-level position ground truth"**；航向真值 $\theta_t$ 由其生成。
- 划分：把**有序序列**切成 **calibration subset** 与 **test subset**；阈值只在校准子集上选，所有最终结果报在测试子集，且"**No threshold re-tuning is performed on the test sequence or at individual perturbation levels**"。

**评测设置（讲条件）**

- **策略网格**：4 种执行策略 × 2 种 HOLD 行为
  - 策略：Always-execute baseline / Area-only gate / Stability-only gate / Full confidence gate
  - HOLD 行为：baseline freeze-HOLD (4) / bounded-blend HOLD (3)
- **条件**：clean、centroid 扰动、area 扰动；扰动只加在**输入特征**上，**真值航向不变**，预测器**不重训**。
  - 式 (15) 质心加性：$\epsilon^{(cx)}_t,\epsilon^{(cy)}_t\sim\mathcal N(0,\sigma_c^2)$，最高档 $\sigma_c=0.02$
  - 式 (16) 面积乘性：$area_t'=area_t(1+\epsilon^{(a)}_t)$，$\epsilon^{(a)}_t\sim\mathcal N(0,\sigma_a^2)$，最高档 $\sigma_a=0.10$
  - **Monte Carlo 重复次数论文未报告**（原文仅说"repeated Monte Carlo trials are used"）
- **标定结果**（式 17，全文唯一的可复现数字）：$\tau_{area}=0.025583$，$\tau_\sigma=0.256323^\circ$。作者强调该阈值对两种 HOLD 策略**完全相同**，因此 freeze vs blend 的差异被隔离到 fallback 规则上。

**核心结果（逐字）**

Clean 序列 / freeze-HOLD（Table I）：

| Mode | Execution Rate (%) | MAE Executed (deg) | MAE Issued (deg) | Mean Jerk (deg/step²) |
|---|---|---|---|---|
| Always-execute | 100.00 | 0.094285 | 0.094285 | 0.018487 |
| Area-only | 98.78 | 0.091493 | 0.092446 | 0.017173 |
| Stability-only | 97.24 | 0.089771 | 0.102562 | 0.026114 |
| Full gate | 96.35 | 0.088549 | 0.102184 | 0.025597 |

（正文另给执行率小数：area-only **0.987844**、stability-only **0.972447**、full gate **0.963533**。）

Clean 序列 / bounded-blend（Table IV）：

| Mode | Execution Rate (%) | MAE Executed (deg) | MAE Issued (deg) | Mean Jerk (deg/step²) |
|---|---|---|---|---|
| Always-execute | 100.00 | 0.094285 | 0.094285 | 0.018487 |
| Area-only | 98.78 | 0.091493 | 0.092586 | 0.016980 |
| Stability-only | 97.24 | 0.089771 | 0.099964 | 0.022653 |
| Full gate | 96.35 | 0.088549 | 0.099837 | 0.022432 |

最高扰动档 / freeze-HOLD（Table II：$\sigma_c=0.02$）：

| Mode | Execution Rate (%) | MAE Exec. Only (deg) | MAE Issued (deg) | Mean Jerk (deg/step²) |
|---|---|---|---|---|
| Always-execute | 100.00 | 0.7477 | 0.7477 | 1.8128 |
| Area-only | 98.78 | 0.7484 | 0.7457 | 1.7921 |
| Stability-only | 1.66 | 0.4445 | 3.2177 | 0.0812 |
| Full gate | 1.63 | 0.4397 | 3.2153 | 0.0805 |

最高扰动档 / freeze-HOLD（Table III：$\sigma_a=0.10$）：

| Mode | Execution Rate (%) | MAE Exec. Only (deg) | MAE Issued (deg) | Mean Jerk (deg/step²) |
|---|---|---|---|---|
| Always-execute | 100.00 | 0.2283 | 0.2283 | 0.4818 |
| Area-only | 91.03 | 0.2271 | 0.2230 | 0.4479 |
| Stability-only | 61.77 | 0.1702 | 0.3549 | 0.2281 |
| Full gate | 54.03 | 0.1657 | 0.3504 | 0.2011 |

freeze vs blend 直对比（Table V）：

| Condition | Mode | Execution Rate (%) | MAE Exec. Only (deg) | MAE Issued Freeze (deg) | MAE Issued Blend (deg) |
|---|---|---|---|---|---|
| $\sigma_c=0.02$ | Stability-only | 1.66 | 0.4445 | 3.2177 | 0.4966 |
| $\sigma_c=0.02$ | Full gate | 1.63 | 0.4397 | 3.2153 | 0.4959 |
| $\sigma_a=0.10$ | Stability-only | 61.77 | 0.1702 | 0.3549 | 0.2531 |
| $\sigma_a=0.10$ | Full gate | 54.03 | 0.1657 | 0.3504 | 0.2477 |

图读值（原文"approximately"口径，非表格真值）：$\sigma_c=0.01$ 时 issued MAE 约 **0.75 → 0.35**（stability-only 与 full gate 均如此）；$\sigma_c=0.02$ 时 jerk 由 full gate **0.0805 → 0.1244**、stability-only **0.0812 → 0.1247**；$\sigma_a=0.10$ 时 jerk 由 **0.2281 → 0.2169**（stability-only）、**0.2011 → 0.1915**（full gate）。

> 阅读一致性小注：正文 §VI-B2 描述 Figure 5 时写的是 **3.2176 / 3.2152**，而 Table II、Table V 写 **3.2177 / 3.2153** —— 同一量在文字与表格间有 1e-4 级差异，引用时建议以表格为准。
>
> **未报告项**：RMSE 只有定义 (9)，全文**未给任何 RMSE 数值**；数据集规模、序列时长、Monte Carlo 次数、$\alpha/\rho/\bar h/k$ 数值、消融式超参敏感度，均**论文未报告**。

---

## 6 · 能力与失败模式

### 能做（有数字支撑）

- **在干净序列上做"轻度选择性"是有收益的**：area-only 同时改善 executed MAE（0.091493 vs 0.094285）、issued MAE（0.092446）与 jerk（0.017173）。
- **在质心抖动下保住"被执行子集"的干净度**：$\sigma_c=0.02$ 时 always-execute 退化到 0.7477，而门控策略执行的帧只有 0.4445 / 0.4397。
- **同一套门决策下，改 fallback 就能大幅改系统行为**：3.2177 → 0.4966、3.2153 → 0.4959（质心）；0.3549 → 0.2531、0.3504 → 0.2477（面积）。这个"控制变量"做得干净（阈值、执行率、executed MAE 全部不变）。
- **在面积扰动下 blend 还能顺带改善 jerk**（0.2281→0.2169、0.2011→0.1915），不像质心扰动下要付 jerk 代价。

### 不能做 / 明确失败

1. **门控 + freeze 在强质心噪声下系统级崩坏**：执行率 1.66% / 1.63%，issued MAE 3.2177 / 3.2153，**比"什么都不门控"差 4 倍以上**。这是本文最重要的负面结论，也是它最有价值的部分。
2. **稳定性门在面积扰动下依然劣于 always-execute 的指令精度**：0.3549 / 0.3504 vs 0.2283 —— 即便上了 blend 也只到 0.2531 / 0.2477，**仍不如全程直发**。也就是说，"加门控"并非普遍占优，只在特定失效模式下占优。
3. **无法区分"真机动"与"噪声"**：$\sigma_\theta$ 只看预测序列的短期离散度；机体真转弯时 $\hat\theta$ 当然会变，$\sigma_\theta$ 上升 → 门关 → 转弯被当成不可靠。论文全文未讨论这一点，但它是式 (6) 的直接后果。
4. **没有闭环**：所有结果都是离线 replay，$u_t$ 不回灌到下一帧图像。因此"指令平滑"与"飞行平稳"之间**没有建立任何因果链**；论文自己在 §VII 把 closed-loop 列为 future work。
5. **没有跨域泛化证据**：单条室内序列 + VICON + 固定阈值，$\tau_{area}$ 直接绑定"目标在图像里的归一化面积"，换个相机 FOV / 分辨率 / 跟飞距离就得重标。
6. **扰动模型 ≠ 真实感知失效**：真实失效是检测丢失（bbox 不存在）、框漂移到背景、运动模糊导致框膨胀——而本文用的是**在已有特征上加高斯噪声**；式 (16) 的乘性面积噪声甚至可能造出物理上不可能的框。

### 隐含假设 (Hidden Assumptions)

| # | 隐含假设 | 一旦不成立会怎样 | 依据 |
|---|---|---|---|
| A1 | **每一步都有 bbox**：$\mathbf{x}_t$ 对所有 $t$ 都存在 | 检测丢失时 $area_t$ 无定义，$f$ 无法推理；论文的扰动模型里根本没有"缺失"这个事件 | 式 (1) 定义在每一步上，§IV-I 只扰动数值不删除观测 |
| A2 | **bbox 面积 ≈ 感知可靠性**（单调） | 跟飞距离变近/变远、FOV 变化、目标转向都会改面积，与"证据质量"无关 → 门被几何而非质量驱动 | §IV-B："smaller area … potentially less reliable" |
| A3 | **预测误差的坏样本可由"短窗离散度"捕获** | 系统性偏置（bias）在窗口内是**一致**的 → $\sigma_\theta\approx0$ → 门大开，把稳定但错的预测全额放行。这是最危险的一类：**稳≠对** | 式 (6) 只测离散度，不测与真值的偏差 |
| A4 | **角度是线性可平均的实数** $\theta\in\mathbb{R}$ | bbox/航向跨 ±180° 时式 (5) 的算术均值与式 (6) 的 std 会爆炸（±180 的"平均"是 0） → 门永久 HOLD | 式 (5)(6) 明文用 $\hat\theta\in\mathbb{R}$，无 unwrap、无圆统计 |
| A5 | **校准集与测试集同分布**（同高度、同相机、同目标尺度） | $\tau_{area}=0.025583$ 与 $\tau_\sigma=0.256323^\circ$ 是这条序列的 operating point，换场景/换高度即失效；论文未做任何跨序列验证 | §V-A 只做一次划分，阈值全局固定 |
| A6 | **开环评估有效**：指令质量可用 $|\theta_t-u_t|$ 离线度量 | 闭环下指令会改变观测（飞机会动），误差不再独立；且"平均角度误差"不等于姿态稳定性 | §V 全程离线；§VII 自认 future work |
| A7 | **时间戳严格对齐**：$\theta_t$、$\hat\theta_t$、$u_t$ 同索引 | VICON 与相机不同步时，$|\theta_t-\hat\theta_t|$ 里混入时间偏移误差，指标被污染；论文未报告同步方法与残差 | 式 (8)(12) 均按 $t$ 直接配对 |
| A8 | **fallback 超参与门控解耦**：$\alpha,\rho,\bar h$ 可任意选而不影响门决策 | 论文数值上保证了这一点（$h_t$ 只依赖 $a_t$），所以成立；但**它同时意味着 $\alpha,\rho,\bar h$ 从未被调优/报告**，部署者拿不到任何先验 | §III-C 与 §VI-A："thresholds … identical across the two HOLD policies" |

---

## 7 · 与相关工作对比

| 维度 | 视觉跟随/降落（Morales, Falanga, Wu 等 [9–16]） | 不确定性/选择性预测（Kendall&Gal, Gal&Ghahramani, Guo, Lakshminarayanan, Geifman 等 [18–28]） | 前期航向预测器 [17] | **本文** |
|---|---|---|---|---|
| 解决什么 | 能不能估出相对位姿/航向并落下去 | 模型输出的不确定性/置信度是否可信、何时该弃权 | 从 bbox 几何特征回归相对航向 | **预测已有时，该不该下发、不下发时怎么演化** |
| 依赖什么信号 | 视觉几何 / fiducial / visual servoing | 模型内部（MC-dropout、ensemble、logit、校准集） | bbox 4 维特征 | **感知流外部的 2 个代理：$area$、滑窗 $\sigma_\theta$** |
| 需要重训模型吗 | 是（各自的感知/控制管线） | 是（不确定性建模通常要改训练或多次推理） | — | **否**（$f$ 冻结，零参数决策层） |
| 代价 | 完整系统 | 多次前向 / 集成 / 校准集 | 一次回归 | **每步 $O(k)$ 滑窗 + 2 次比较** |
| 处理"低置信时怎么办" | ❌ 未形式化 | 部分（弃权 = 不输出） | ❌ | ✅ **显式建模：freeze vs bounded-blend** |
| 本文相对它的增量 | — | 借其动机，但不估计贝叶斯不确定性，也不做校准学习 | 复用而非改进 | 把 stale-command 问题**量化**并给出低成本修法 |

**面试 Tip（被问到"这篇和 uncertainty-aware 工作什么关系"怎么答）**：
> "它借的是**动机**不是**方法**。Kendall&Gal / MC-dropout / ensemble 那一路要进到模型内部拿方差、要多跑几次前向；本文是**零模型侵入**的——只用 bbox 面积和预测序列的滑窗 std 这两个外部可观测量做门控，所以它可以在任何已部署的预测器上叠加，代价只是每步一个 $O(k)$ 滑动窗口。真正的贡献不在门，在**门关之后的行为**：它证明了 freeze-HOLD 在 $\sigma_c=0.02$ 下会把指令误差做到 3.2153°（比不门控还差 4 倍多），而同一套门决策 + bounded-blend 能拉回 0.4959°，说明 perception-to-control 的 fallback 策略是被长期忽略的独立设计维度。"

加分补一句（体现批判性）："但它有个致命盲点——$\sigma_\theta$ 只测**离散度**不测**偏差**，所以一个稳定但系统性偏掉的预测器会被门全额放行（A3）；而且式 (5)(6) 是线性角度统计，跨 ±180° 会直接把门焊死（A4）。"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-01)

**Repo 状态核实**：全文（含脚注、致谢、参考文献前的所有正文段落）**没有出现任何 `github.com` 链接，也没有可点击的代码/数据仓库超链接**；数据被明确指向前期工作 [17]，代码发布未提及。因此按规则——**官方 repo 未在论文中给出，以下 pitfall 由 §6 失败模式 + 本文方法约束推导，未经任何 issue 验证**。同时标注：**该论文为 2026-07-21 上传的 v1 预印本（"has been submitted to the IEEE for possible publication"），处于 early-release 阶段，社区 issue 流尚不存在。**

### P1 · 无法复现 §VI-C：$\alpha,\rho,\bar h$ 全程无数值

- **来自 §6 的失败模式**：A8 + §4 表末行——论文把 blend 的收益（3.2177→0.4966）作为核心卖点。
- **来自方法约束**：式 (3) 明文引入 $\alpha$（short-hold blending factor）、$\bar h$（maximum bounded-hold duration）、$\rho$（recovery blending factor），但**全文没有给出任何一个的具体数值**，也没有给出选法（只在 §IV-F 描述了 $\tau_{area},\tau_\sigma$ 的 Pareto 网格搜索流程）。
- **机械后果**：$\alpha$ 直接决定"停止执行后指令以多快速度追当前预测"。玩具算例里 $\alpha=0.2$ 时 8 步内就贴着 $\hat\theta$ 走；若 $\alpha=0.02$，同样步数几乎没动，退化成 freeze-HOLD，本文的收益**整体消失**。复现者无法判断 0.4966 是靠 $\alpha$ 还是靠门，**论文最强的数字因此是不可复现的单点**。
- **落地对策**：自己扫 $\alpha\in[0.05,0.5]$、$\bar h\in[3,30]$，把 $\mathrm{MAE_{issued}}$ 与 $\bar J$ 的 Pareto 前沿重画一遍，别直接抄结论。

### P2 · 角度环绕：式 (5)(6) 是线性统计，跨 ±180° 会把门焊死

- **来自 §6 的失败模式**：A4，"$\sigma_\theta$ 在 ±180° 附近爆炸 → 门永久 HOLD → 执行率塌方"，与论文实测的执行率塌到 **1.66% / 1.63%** 是同一失效机制（只是触发源不同）。
- **来自方法约束**：式 (5) 用 $\bar\theta_t=\frac1k\sum\hat\theta_{t-j}$、式 (6) 用总体 std，且 §III-A 明确 $\theta_t\in\mathbb{R}$；全文没有 unwrap、没有 $\mathrm{atan2}(\cdot)$ 圆统计、没有 360° 取模。
- **机械后果**：若真值航向在实验过程中穿过 $+\pi/180°$ 边界（室内 VICON 场景下机体转向完全可能），滑窗内会同时出现 $+179°$ 与 $-179°$，均值 ≈ 0、std ≈ 180° ≫ $\tau_\sigma=0.256323^\circ$ → 门连关 $k$ 步以上；配合 freeze-HOLD 就是一次 stale-command 尖峰，会被错误归因为"扰动导致"，污染 §VI 的曲线。
- **落地对策**：进门前先 unwrap（累积角），或改用圆统计（$R=\|\frac1k\sum e^{i\hat\theta}\|$，用 $1-R$ 当稳定性代理）。**这是把该层移植到真机前必须做的第一处改动。**

### P3 · $t<k$ 时 $\sigma_\theta$ 无定义：上电/起飞瞬间没有合法指令

- **来自 §6 的失败模式**：A1 的弱化版——"每一步都有观测"成立，但"每一步都有**可用**的稳定性代理"不成立。
- **来自方法约束**：式 (6) 显式限定 $t\ge k$，而 $k$ 的**数值论文未报告**（只说 $k\ge2$）；式 (7) 的门控要求 $\sigma_\theta(t)\le\tau_\sigma$ 才能 EXECUTE。
- **机械后果**：开环离线评测里前 $k-1$ 帧的决策**不影响任何报告的表格**（$\mathrm{ExecFrac}$、$\mathrm{MAE_{issued}}$ 都是全序列平均，$k$ 很小所以被淹掉），所以论文可以完全不交代；但真机上电那一刻，若把 $\sigma_\theta$ 当 0 处理就误放行（可能放行一帧坏预测），若判为不可用就 HOLD——而 $u_{t-1}$ 还不存在，式 (3) 的分支直接引用未初始化变量。这是**论文的离线协议合法掩盖、真机集成立刻撞上**的典型断点。
- **落地对策**：显式定义 warm-up 状态（前 $k$ 帧强制 HOLD 且 $u_t$ 取首帧 $\hat\theta_t$ 或飞控当前 yaw），并把 warm-up 帧计入日志，别混进 $\mathrm{ExecFrac}$ 统计。

### P4 · 阈值是"这条序列的 operating point"，换个跟飞距离就废

- **来自 §6 的失败模式**：A2 + A5——面积代理把"距离/FOV"误当"可靠性"。
- **来自方法约束**：§VI-A 明确 $\tau_{area}$ 无量纲，因为 $area_t$ 是"bbox 面积 / 全图面积"；$\tau_{area}=0.025583$ 是在**单条室内序列的校准子集**上网格搜出的，且 §V-A 声明"**No threshold re-tuning is performed on the test sequence or at individual perturbation levels**"（对科研正确，对部署是硬约束）。
- **机械后果**：$\tau_{area}$ 是归一化面积 ⇒ 与"目标在图像中的角尺寸"成正比 ⇒ 与 **相机 FOV、分辨率、跟飞高度/距离、目标物理尺寸** 强绑定。换一架飞机或换一个跟飞距离，同一个 $\tau_{area}=0.025583$ 可能把执行率变成 0% 或 100%——而论文在同一序列内固定阈值，**结构上无法暴露这个敏感性**（面积扰动实验是乘性加噪，均值不变，故测不出"整体尺度平移"）。
- **落地对策**：把 $\tau_{area}$ 改成**相对量**（如相对运行窗口的分位数，或与期望角尺寸的比值），或在启动阶段做一次自标定；同时监控 $\mathrm{ExecFrac}$ 作为在线健康指标——因为它对阈值漂移最敏感（clean 上 96.35%，$\sigma_c=0.02$ 上是 1.63%，横跨两个数量级）。

---

[← Back to Aerial–Ground Robotics / Perception-to-Control README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2607.18713v1 全文 · 未在真机复现的数字标 `UNVERIFIED`；§4 中 latency/VRAM/FPS/硬件均为「论文未报告」；$\alpha,\rho,\bar h,k$、数据集规模、Monte Carlo 次数、RMSE 数值均论文未报告；§8 全部 pitfall 为方法约束推导，**无 repo、无 issue 验证**。

[//]: # "<!-- source: https://arxiv.org/abs/2607.18713 -->"
