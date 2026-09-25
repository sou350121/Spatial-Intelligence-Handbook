<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: geometric
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# 动态环境中在线无碰撞轨迹生成 (Online Generation of Collision-Free Trajectories in Dynamic Environments)

> **发布时间**：2026-07-11（arXiv v3；投稿 2026-02-28，接收 2026-06-28）
> **论文 / 模型名**：CFS45 (Collision-Free 4th/5th order Splines)
> **核心定位**：把「任意上游 planner 给出的几何路径」在线转成 jerk-limited、满足 P/V/A/J 约束、且在动态环境中带条件性停止安全保证的轨迹——单次求解 ~10⁻⁶ s，比 Ruckig 快约 3 倍，可直接挂在下游控制器的 500 Hz 环上。

TOPP 类方法（Bobrow / TOPP / TOPP-RA）能给出全局最优时间参数化，但要求**离线、路径与环境全知**；而现代协作机械臂需要在移动障碍与人机共存场景中**每毫秒重规划**。本文的结论是：用「五阶样条 + 单标量 jerk 二分 + 自由 C-space 气泡链 (GBur) + DEB 膨胀」这套组合，可以把在线时间参数化的代价压到微秒级，同时保留 jerk 约束与（有条件的）停止安全保证。

---

**X-Ray 开场**：这篇论文解决的是「planner 只给你一条几何路径点序列，机器人却要在线、带 jerk 限制、在移动障碍中安全地把它跑出来」这一工程断层。它提出的 CFS45 把 5 阶样条的自由度压缩到**一个标量**（三次项系数 φ⁽³⁾ = jerk(0)/6），于是四阶约束（jerk）下的时间参数化退化成「在一维区间上二分 + 每次解一个三次方程」，再用 bubble/bur/GBur 链做碰撞检查、用 DEB 膨胀提供动态环境下的停止安全。对 spatial AI 研究者意味着：**几何路径 → 可执行轨迹** 这一步可以被当成一个确定性、微秒级、无学习的服务模块，插在任意采样/搜索 planner 与底层控制器之间，而不是每次重跑优化器。

---

## 📍 研究全景时间线

```
1985        2014        2018        2020        2021        2023        2025        2026
 │           │           │           │           │           │           │           │
Bobrow       TrajOpt    TOPP-RA     ARMTD       Ruckig      CuRobo     Skuric     CFS45(本文)
TOPP         │           │           │           │           │           │           │
 │           │           │           │           │           │           │           │
offline     offline     offline     hybrid      online      online      online      online
torque      P,V,A,J     P,V,A       P,V,A       P,V,A,J     P,V,A,J     P,V,A,J     P,V,A,J
全局最优     局部最优     全局最优     成本最优      时间最优      min-J/A     near-TO     时间最优
无碰撞       有碰撞       无碰撞       有碰撞       无碰撞       有碰撞       无碰撞       ★有碰撞(DEB)
数值积分      凸优化       凸优化       可达集       闭式        GPU并行      前向缩放     微秒级+安全保证
                                                                                    ↑
                                                          本文站位：在线 + 安全 + 微秒级 + 动态环境
```

**本文的局限（写在时间轴上）**：安全性是**条件性**的——依赖「障碍速度上界 v_obs 已知」这一前提；若真实障碍速度超过 v_obs，DEB 的形式化保证立即失效（论文明确承认）。此外它只是**局部**时间参数化（parabolic-jerk 族内时间最优），不做全局重规划，需要上游 planner 持续供给 `q_target`。

---

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **Alg.1 Jerk Computation** | 系数区间 `I_i⁽⁰⁾=[-q⃛_m/6, q⃛_m/6]`、精度 `Δc_i` | `c_i* = φ_i⁽³⁾`、`t* = t_fi` | 无训练；纯在线数值（边界检查 + 二分） |
| **Eq.(4)–(6) 系数闭式求解** | 初始边界条件 `φ⁽⁰⁾,φ⁽¹⁾,φ⁽²⁾`、终态 `π_f, π̇_f, π̈_f` | `t_fi`（解三次）、`φ⁽⁴⁾`、`φ⁽⁵⁾` | 无训练；闭式 + Cardano |
| **Alg.2 Path-to-Trajectory** | 几何路径 `Q={q₁..q_N}`、`D_max` | 样条序列 `Π={π_k,k+2}` | 无训练；含 simplify&Densify 与插值二分 |
| **Alg.3 computeBur** | `π_reg(t)`、`Δt`、距离向量 `d(t₀)` | `Bur`（从根节点出射的 spine 集合） | 无训练 |
| **Alg.4 computeGBur** | `π_reg(t)`、`Δt`、`d(t₀)` | `GBur`（bur 的链式拼接） | 无训练 |
| **DEB 安全认证 (Sec.V-C)** | `GBur`、障碍速度上界 `v_obs` | 是否落在 DEB 内（是/否） | 无训练；用 `v_obs(t-t₀)` 收缩 `d_c` |
| **紧急停止样条（quartic）** | `q_new`（最后气泡边界）、当前状态 | `π_emg(t)=π[q_new, q_stop]` | 无训练；m=4，终位置自由 |

> **要点**：整个 pipeline **没有任何学习组件**——它是确定性几何 + 数值求根。这也是它能在表 I 里报出 ~10⁻⁶ s 的计算时间的原因。

### 1.2 关键机制

> **⚡ Eureka Moment**：五阶样条的前三个系数 `φ⁽⁰⁾,φ⁽¹⁾,φ⁽²⁾` 被**初始位置/速度/加速度**直接钉死，剩下 `φ⁽³⁾`（=jerk(0)/6，受约束 9 限制在一个**已知闭区间**内）成为唯一自由标量；于是「四阶 jerk 约束下的时间参数化」这个非凸问题，被降维成**一维二分 + 每次解一个关于 t_f 的三次方程**——并且约束只需在 4 个极值时刻（π̇=0, π̈=0, π⃛=0, π⁗=0 的根）上验证，而不必扫全时域。

第二个关键洞见在安全侧：**允许机器人「先撞后停」是不可能的**，所以他们把轨迹分成两类——
- **Regular trajectory（常规轨迹）**：尚未安全认证的五阶样条序列，碰撞可能发生在运动过程中（type I collision）；
- **Safe trajectory（安全轨迹）**：在 DEB 链内受限运行的轨迹 + 尾部拼接一段四次紧急停止样条，**任何碰撞只能发生在机器人已经停稳之后**（type II collision）。

### 1.3 信息流 / 架构图

```
 q_curr ─┐
 q_goal ─┼──► [上游动态 planner: ORRT / DRGBT]  ──► q_target
 WO(t) ──┘          （只取最近一个 target；DRGBT 允许
                    在距离 < n·R·‖q̇_curr‖/‖q̇_m‖ 时换 target）

          │
          ▼
 ┌────────────────────────────────────────────────────────┐
 │ Alg.2  Path-to-Trajectory                              │
 │   ① simplify&Densify(Q)  s.t. ‖q_{k+1}-q_k‖ ≤ D_max   │
 │   ② 试算 π_k,k+2（跳过角点 q_{k+1}）                     │
 │   ③ 若碰撞 → 算 π_k,k+1，再对 t_k(·) 二分找 interp. 样条  │
 │   ④ 找不到 → q_{k+1} 记为 unresolved corner node        │
 └────────────────────────────────────────────────────────┘
          │  Π = {π₁,π₂,...}
          ▼
 ┌────────────────────────────────────────────────────────┐
 │ Alg.3 computeBur  →  Alg.4 computeGBur                 │
 │   d_c 由最近点 (R_{i,j}, O_{i,j}) 与分离平面 P_{i,j}     │
 │   决定；气泡 B(q₀,d_c) 的轴向半径 r_i 上界机器人位移       │
 └────────────────────────────────────────────────────────┘
          │  GBur
          ▼
 ┌────────────────────────────────────────────────────────┐
 │ DEB 膨胀：每个平面 P_{i,j} 以 v_obs 向 link 推进          │
 │           ⟹ 检查时把 d_c 减去 v_obs·(t-t₀)               │
 └────────────────────────────────────────────────────────┘
          │
     ┌────┴───────────────────────────────┐
     │  GBur ⊆ DEB ?                      │
     ├─ 是 ─► π_safe = π[q_curr,q_new] ∪ π_emg(quartic)  ──► 下发
     └─ 否 ─► 执行上一轮已算出的 π_emg（从 q_curr 紧急停）    ──► 下发
```

（灰色框由上游动态 planner 执行，其余为 CFS45——对应论文 Fig.3 的 flowchart。）

---

## 2 · 数学核心

📌 **Napkin Formula**

```
对第 i 个关节：
  φ⁽⁰⁾,φ⁽¹⁾,φ⁽²⁾  ← 由初始 P/V/A 直接读出（已知）
  φ⁽³⁾ ∈ [-q⃛_m/6, q⃛_m/6]        ← 唯一的自由标量（=jerk(0)/6）
  在区间内二分 φ⁽³⁾ → 解三次方程得 t_f → φ⁽⁴⁾, φ⁽⁵⁾ 闭式
  只需在 t∈{π̇=0, π̈=0, π⃛=0, π⁗=0 的根} 上验约束
```

**目标**：求时间参数化轨迹 `π: [t₀,t_f] ↦ C`，在逼近原路径 `Q` 的同时满足逐关节约束

```
|π_i^{(o)}(t)| ≤ q_{m_i}^{(o)},  o ∈ {0,1,2,3},  ∀ t ∈ [t₀,t_f]      (1)
```

即位置 ℙ、速度 𝕍、加速度 𝔸、加加速度 𝕁（jerk）四阶全约束。

**公式链**：

五阶样条（m=5）：

```
π_i(t) = φ_i⁽⁵⁾t⁵ + φ_i⁽⁴⁾t⁴ + φ_i⁽³⁾t³ + φ_i⁽²⁾t² + φ_i⁽¹⁾t + φ_i⁽⁰⁾    (2)
```

初始边界（t₀=0）给出前三个系数：

```
π_i(0)=φ_i⁽⁰⁾,  π̇_i(0)=φ_i⁽¹⁾,  π̈_i(0)=2φ_i⁽²⁾                        (3)
```

终态边界（π_fi, π̇_fi, π̈_fi 已知，t_fi 未知）消元后得到一个关于 `t_fi` 的**三次方程**：

```
φ_i⁽³⁾t_fi³ + (3φ_i⁽²⁾ - π̈_fi/2)t_fi² + (6φ_i⁽¹⁾ + 4π̇_fi)t_fi
              + 10(φ_i⁽⁰⁾ - π_fi) = 0                                    (4)
```

随后 `φ⁽⁴⁾, φ⁽⁵⁾` 由 `t_fi` 与 `φ⁽³⁾` 闭式给出：

```
φ_i⁽⁴⁾ = (1/t_fi³) [ -3/2 φ_i⁽³⁾ t_fi² + (-3/2 φ_i⁽²⁾ - π̈_fi/4) t_fi - φ_i⁽¹⁾ + π̇_fi ]   (5)
φ_i⁽⁵⁾ = (1/(20 t_fi³)) [ -12 φ_i⁽⁴⁾ t_fi² - 6 φ_i⁽³⁾ t_fi - 2 φ_i⁽²⁾ + π̈_fi ]            (6)
```

Jerk 剖面：

```
π⃛_i(t) = 60 φ_i⁽⁵⁾ t² + 24 φ_i⁽⁴⁾ t + 6 φ_i⁽³⁾                        (8)
```

**变量说明 / 直觉**：

| 符号 | 含义 | 关键性质 |
|---|---|---|
| `φ_i⁽⁰⁾..φ_i⁽⁵⁾` | 第 i 关节样条系数 | 前三者由 (3) 直接定，后两者由 (5)(6) 定 |
| `φ_i⁽³⁾` | 自由标量 | `π⃛_i(0) = 6φ_i⁽³⁾`，故 `φ_i⁽³⁾ ∈ [-q⃛_mi/6, q⃛_mi/6]`（式 9） |
| `t_fi` | 关节 i 的终止时间 | 由 (4) 的**正实根**给出；多个正根取满足约束且最短的 |
| `π_fi, π̇_fi, π̈_fi` | 终态 P/V/A | 可非零（支持非零终速/终加速） |
| `t_f = max{t_f1,...,t_fn}` | 多关节同步 | baseline 策略，非最优耦合 |

**为什么这样能覆盖约束**：位置/速度/加速度的边界条件在 (3)–(7) 下**天然满足**；剩下的 jerk 端点 `π⃛(0), π⃛(t_fi)` 以及内点极值，只需检查 `π̇=0, π̈=0, π⃛=0, π⁗=0` 四组方程的根（分别对应 ℙ/𝕍/𝔸/𝕁 的极值时刻），**有限个候选点**即可，无需时域扫描。

**Theorem 1（Jerk Computation）**：先检查区间两端 `c_{i,left}⁽⁰⁾ = -q⃛_mi/6` 与 `c_{i,right}⁽⁰⁾ = q⃛_mi/6`。若有一端产生满足 `K` 的实 `t_fi` 候选，直接返回最短者；否则在保持「仍可能可行」的半区间上二分，宽度按 `(c_right⁽⁰⁾-c_left⁽⁰⁾)/2^k` 收缩，收敛到精度 `Δc_i`（实现取 `0.001 · 6|I_i⁽⁰⁾|`）。**Remark**：若无解返回，planner **复用上一轮已算出的轨迹**。

---

## 3 · 带数字走一遍（玩具例子，n=1，自造设定）

设单关节，`q₀ = 0 → q_f = 1`，静止起步静止停止：`π̇(0)=π̈(0)=π̇(t_f)=π̈(t_f)=0`，jerk 上限 `q⃛_m = 6 [rad/s³]`，故 `φ⁽³⁾ ∈ [-1, 1]`。

由 (3)：`φ⁽⁰⁾=0, φ⁽¹⁾=0, φ⁽²⁾=0`。

**代入 (4)**（`π_f=1, π̇_f=π̈_f=0`）：

```
φ⁽³⁾·t_f³ + (0)·t_f² + (0)·t_f + 10(0 - 1) = 0
⟹ t_f = (10 / φ⁽³⁾)^{1/3}
```

**关键观察**：
- 取 `φ⁽³⁾ = -1`（区间左端）→ `t_f = (-10)^{1/3}` **不是正实根 → 丢弃**。这一步正是「边界检查」的意义。
- 合法解只存在于 `φ⁽³⁾ > 0`，于是二分向右侧收敛。

**取 `φ⁽³⁾ = +1`（区间右端，jerk 在 t=0 恰好饱和）**：

```
t_f = 10^{1/3} ≈ 2.154 [s]
φ⁽⁴⁾ = -1.5·φ⁽³⁾/t_f = -1.5/2.154 ≈ -0.6965
φ⁽⁵⁾ = (1/200)·[-12·(-0.6965)·4.6416 - 6·1·2.154] ≈ (1/200)·[38.79 - 12.92] ≈ 0.1293
```

**验约束**（用 (8)）：`π⃛(t) = 7.758 t² - 16.716 t + 6`

| 候选时刻 | 来源 | 值 | 是否 ≤ 6 |
|---|---|---|---|
| t=0 | 端点 | 6.000 | ✓（恰好饱和）|
| t=t_f=2.154 | 端点 | ≈ 6.000 | ✓（恰好饱和）|
| t=1.077 | π⁗=0（jerk 内极值） | ≈ **-3.004** | ✓ |

位置回代校验：`π(2.154) = 0.1293·46.416 - 0.6965·21.545 + 1·10 ≈ 0.996 ≈ 1` ✓

**如果换 `φ⁽³⁾ = 0.1`**（更保守的 jerk）：`t_f = 100^{1/3} ≈ 4.642 [s]`，jerk 极值仅约 ∓0.3，**约束全部满足但慢了 2 倍**。所以 Alg.1 的「取最短 t_f 的可行解」在端点可行时就直接返回 `φ⁽³⁾=1`——这解释了论文所谓 **"time-optimal within the parabolic-jerk family"**：最优只在「jerk 剖面为抛物线」这一族内成立，不是全局时间最优。

（以上为纯玩具演示，用于说明机制，非论文实测数据。）

---

## 4 · 工程视角

| 指标 | 数值 | 来源 |
|---|---|---|
| 单次轨迹生成计算时间 | `~10⁻⁶ [s]` | Tab. I（CFS45 行） |
| 占 DRGBT 平均运行时间（regular） | `at most 0.1 [%]` | §VI-B |
| 占 DRGBT 平均运行时间（safe） | `2.8 [%]` | §VI-B |
| 生成耗时 vs Ruckig | `almost 3 times faster` | §VI-B |
| 仿真硬件 | `Intel® Core™ i7-9750H CPU @ 2.60 GHz × 12 with 16 GB of RAM`，**单核、无 GPU** | §VI |
| 底层控制频率 | `f_con = 500 [Hz]` | §VII |
| 规划频率 | `f_alg = 20 [Hz]`（与 `f_perc` 同步） | §VII |
| 感知频率 | `f_perc = 20 [Hz]`（2× Intel RealSense D435i） | §VII |
| 目标状态更新频率（设计目标） | `up to 1 [kHz]` | Abstract |
| 内存占用 / VRAM / 吞吐 | **论文未报告** | — |

**Trade-off 解读**：

1. **Regular vs Safe 的代价差 ~28 倍**（0.1% vs 2.8%）：safe 模式额外付出 GBur 构建 + DEB 认证 + 紧急停止样条三次开销。若实际部署中感知频率低（20 Hz）而控制率高（500 Hz），这个 2.8% 是相对 **DRGBT 总时长** 而言的，绝对量仍远低于 1 ms 预算——这也正是它能宣称支持 1 kHz target 更新的依据。
2. **单核无 GPU** 是关键卖点：CuRobo 走 GPU 并行路线（`~10⁻² [s]`），本文用闭式 + 一维二分把复杂度压到 `~10⁻⁶ s` 量级，代价是**放弃全局最优**，把最优性限定在 parabolic-jerk 族内。
3. **同步策略是 baseline**：`t_f = max{t_f1,...,t_fn}`，论文自陈 "we adopt a simple baseline synchronization strategy... rather than aiming for an optimal coupling mechanism"。多 DoF 增多时 `max` 会带来保守性放大——这也是论文把「高 DoF 扩展性」列为 future work 的原因。
4. **紧急停止是"最后防线"**：未插值成功的路径角点会让机器人**完全停下**（零速），这在时间效率上是硬损失，但换来「有解一定存在」的完备性。

---

## 5 · 数据与评测

**注意：本文没有数据集**，评测由**仿真研究 + 真机实验**两部分构成。

### 5.1 仿真设置（§VI-A）

| 项 | 内容 |
|---|---|
| 机器人模型 | `UFactory xArm6`（仿真） / 平面 2-DoF（Fig.5 示例） |
| 场景类型数 | `19 scenario types` |
| 每种场景的 planner 迭代时间 T | `{1,2,3,...,10,20,30,...,100} [ms]` |
| 随机运行次数 | `1000 different simulation runs`（1000 组随机但无碰撞的起止构型） |
| Scenario 1 障碍 | `ten random obstacles`，速度幅值上限 `1.6 [m/s]` |
| Scenario 2 障碍 | `four large predefined obstacles`，速度上限 `0.3 [m/s]` |
| 关节约束（取自 xArm6 datasheet） | `ω_max = π_{n×1} [rad/s]`，`α_max = 20_{n×1} [rad/s²]`，`j_max = 500_{n×1} [rad/s³]` |
| 对比基线 | **Ruckig**（主基线，因其效率 + 开源 + 被 MoveIt/CoppeliaSim/Frankx 采用）；另试过 TrajOpt，但因不适配实时频繁换目标而被判不合适 |
| 上游 planner | ORRT（RRT 的在线简化版）、DRGBT（专为动态环境设计） |

### 5.2 仿真结果（逐字）

| 指标 | 结果 |
|---|---|
| 平滑度（jerk L1-norm） | 平均 **`3.3 times improvement`** |
| Fréchet 距离（每轮 `q_curr q_target` 连线 vs 实际轨迹） | 平均 **`2.33 times lower`** |
| 生成耗时 | 比 Ruckig **`almost 3 times faster`** |
| 每张直方图样本量 | `more than 24 million different "random" trajectories` |
| CFS45 占 DRGBT 运行时间 | regular `at most 0.1 [%]`，safe `2.8 [%]` |
| 相对性能优势窗口 | 在 planner 频率 `above 100 [Hz]`（即 `T ≤ 10 [ms]`）时**改善显著** |

**评测指标定义**（需注意其非标准性）：论文用 **adjusted success rate** 而非二元成功率——

```
adjusted success = 1 - ‖q_end - q_goal‖ / ‖q_start - q_goal‖ ∈ [0,1]
```

`q_end` 为终止构型（发生碰撞时即碰撞时刻的构型，否则 `q_end = q_goal`）。图 Fig.7 报告中，**当成功率 < 10% 或算法时间/路径长度超出绘图范围时，相应曲线不绘制**。

### 5.3 真机实验（§VII）

| 项 | 内容 |
|---|---|
| 实验数 | `six experiments`（静态 + 动态，含人以障碍） |
| 机器人 | 真实 `UFACTORY xArm6` |
| 感知 | 两台 `Intel RealSense D435i`，`f_perc = 20 [Hz]`，左右点云融合后提取为 **axis-aligned bounding boxes** |
| 碰撞/距离查询 | 机器人 link 用 **bounding capsules** 近似 |
| 底层控制 | `f_con = 500 [Hz]`，处理各关节期望/实测 ℙ 与 𝕍 |
| 中间件 | ROS2 环境 |
| 规划频率 | `f_alg = 20 [Hz]`，与感知对齐；轨迹按 `f_con` 重采样后下发 |
| 演示的 jerk 上限 | `50 [rad/s³]` 与 `200 [rad/s³]` |
| 实测速度 | 所有关节 `remain within the set limit of 1.5 [rad/s]` |
| 未能测量项 | **关节加速度**——`the used robot does not provide joint acceleration measurements` |

---

## 6 · 能力与失败模式

### ✅ 能做

- 把**任意**几何路径（RRT / PRM / ARA* / RRT-Connect / RGBMT* / RRTX / DRGBT 输出）转成 jerk-limited 轨迹，并可按**用户指定控制率**离散化、流式下发。
- 支持**任意可行初始条件** + **非零终速/终加速**（式 7 允许 `π̇_f, π̈_f ≠ 0`）。
- 支持**一个或多个变化的目标 waypoint**；可在任意时刻被重新调用，从当前状态生成新轨迹。
- 在**有界障碍速度假设**下，对**有限时间区间**提供条件性停止安全保证；允许对原路径的**有界几何偏离**。
- 静态/动态环境通吃；真机验证包含**把人当作外部障碍**的保守处理。

### ❌ 不能做 / 失败模式（每条都可机械推导）

| # | 失败模式 | 直接原因（方法约束） |
|---|---|---|
| F1 | 障碍真实速度超过 `v_obs` → **形式化 DEB 保证失效** | 论文原话："If the true obstacle speed exceeds `v_obs`, the formal DEB-based guarantee becomes no longer valid." DEB 只做**保守平面推进**，不做运动预测 |
| F2 | Alg.1 返回 **"No solution can be found!"** → 复用上一轮轨迹 | 无解时 planner 不产生新样条，只能跑旧轨迹——在目标快速变化场景下会造成**响应滞后** |
| F3 | 插值失败的 **unresolved corner node** → 机器人必须**停在那里**再换向 | Alg.2 line 12–13 的 fallback：只能取 `π_k,k+1`，零速强制 |
| F4 | 多关节同步策略保守 | `t_f = max{t_f1,...,t_fn}` 是 baseline，非最优耦合 |
| F5 | 非凸障碍无法直接处理 | 需要**凸分解**（论文引 [22]），假设工作空间障碍为有限个「possibly overlapping convex」集合 |
| F6 | 无碰撞/距离查询时完全失效 | Alg.3/4 与 DEB 全程依赖 `d(t₀)`、最近点 `R_{i,j}, O_{i,j}` 与分离平面 `P_{i,j}` |
| F7 | **无全局最优性** | 最优性仅限 "time-optimal within the parabolic-jerk family"；且是**局部**参数化，不做全局重规划 |
| F8 | 上游无 `q_target` 时无法启动 | DE 中通常只追踪**单个** target（"sometimes necessary to account only for a single `q_target`"） |

### ⚠️ 隐含假设 (Hidden Assumptions)

1. **障碍速度上界 `v_obs` 已知且可信**。论文明确"obstacle motion directions are not assumed to be known or predictable, and obstacle accelerations need not be bounded"——但**速度必须被界住**。这是整个安全保证的阿喀琉斯之踵：现实中快速挥动的手臂、掉落物、被推动的物体都会 violate 它。
2. **碰撞/距离查询实时可得**。假设"robot-obstacle collision/distance query is available"，且其延迟被忽略。真机上这一步依赖感知链路（20 Hz、AABB 拟合、capsule 近似），**感知误差与延迟未进入 DEB 的形式化模型**。
3. **运动学模型完美、控制器能精确跟踪**。低层控制器 500 Hz 处理期望/实测 ℙ/𝕍，但论文**未建模跟踪误差、伺服延迟或关节柔性**。DEB 的保证是「指令轨迹」层面的，不是「实际轨迹」层面的。
4. **上游路径「preferably collision-free」**。Alg.2 的描述里写的是 "arbitrary, **preferably** collision-free, geometric path"——若上游给的路径本身穿过障碍，本方法只能在样条层做局部插值绕行，无力修复全局拓扑错误。
5. **感知—规划频率同步于 20 Hz**。`f_alg = f_perc = 20 Hz` 是实验里的**手工对齐**；论文也承认 "`f_alg` generally differs from `f_con`"，靠重采样弥合。在 >100 Hz 的换目标诉求（1 kHz）下，这个 20 Hz 感知环会成为实际瓶颈，而非 CFS45 本身。
6. **障碍运动被保守膨胀，而非预测**。DEB 用 `v_obs(t-t₀)` 向 link 推进分离平面——这**不利用任何运动预测**，因此对「朝机器人来」和「远离机器人」的障碍一视同仁，代价是保守性。
7. **静态障碍的几何表示为凸体或可凸分解**。非凸需分解；分解本身的开销与质量未在评测中报告。

---

## 7 · 与相关工作对比

| 方法 | 年份/出处 | 约束 | 在线/离线 | 环境 | 安全/碰撞感知 | 最优性 | 验证平台 | 计算时间 |
|---|---|---|---|---|---|---|---|---|
| Bobrow [1] / TOPP [2] | 1985 IJRR / 1985 T-AC | dynamic (torque) | offline | static | no | path-constrained, time-optimal | 数值例子 | n/a |
| TrajOpt [18] | 2014 IJRR | P,V,A,J | offline | static | yes | 局部最优（SCP） | Atlas (S), PR2 (S&E) | `~10⁻¹ s` |
| TOPP-RA [3] | 2018 T-RO | V,A + torque | offline | static | no | path-constrained, time-optimal | 6-DoF (S), 50-DoF (S) | `~10⁻² s` |
| ARMTD [15] | 2020 RSS | P,V,A | hybrid | dynamic | yes | 任意用户成本 | Fetch (S&E) | `~10⁻¹ s` |
| Pupa's [16] | 2021 RA-L | P,V,A | online | dynamic | yes | 路径上最大允许速度 | Pilz PRBT (S&E) | `~10⁻³ s` |
| **Ruckig [19]**（主基线） | 2021 RSS | P,V,A,J | online | dynamic | **no** | time-optimal | Franka Panda (S&E) | `~10⁻⁵ s` |
| Zhao's [5] | 2022 IROS | V,A,J | online | dynamic | no | 正弦-jerk 族内时间最优 | UR3 (S) | n/a |
| CuRobo [20] | 2023 ICRA | P,V,A,J | online | dynamic | yes | min-J & min-A（局部） | UR5e/UR10/Kinova (S), Jetson AGX (E) | `~10⁻² s` |
| McGovern's [14] | 2024 T-RO | torque + state | hybrid | dynamic | yes | safe feasible profiles | UR10 (E) | `~10⁻⁴ s` |
| Skuric's [8] | 2025 T-RO | P,V,A,J | online | dynamic | no | near time-optimal | Franka Panda (S&E) | `~10⁻³ s` |
| Patra's [21] | 2025 JMR | kinodynamic (P,V,A) | hybrid | dynamic | yes | receding-horizon 控制代价 | mobile manipulator (S&E) | `~10⁻¹ s` |
| **CFS45（本文）** | **–** | **P,V,A,J** | **online** | **dynamic** | **yes** | **parabolic-jerk 族内时间最优** | **planar 2-DoF (S), xArm6 (S&E)** | **`~10⁻⁶ s`** |

**定位总结**：表中唯一同时满足「在线 + 动态环境 + 碰撞感知 + P/V/A/J 全约束 + 10⁻⁶ s 量级」的行。Ruckig 更快更通用但**无碰撞感知**；CuRobo 有碰撞感知但要 GPU 且慢 4 个数量级；TOPP-RA 全局最优但离线。

> **面试 Tip**：被问到「这方法比 Ruckig 好在哪、差在哪」时，标准答法是——**好在**它把 jerk 约束的求解降维成一维二分，并且额外提供了 Ruckig 没有的碰撞认证（GBur + DEB），所以在动态场景里 success rate / jerk / Fréchet / 耗时全面更优（3.3× / 2.33× / 3×）；**差在**它的安全性是**条件性**的（依赖 `v_obs` 上界，超出即失效），而且最优性被限制在 parabolic-jerk 族内、同步策略是 max-baseline。Ruckig 是通用离线可验证的时间最优库，CFS45 是**为动态环境定制的、带安全层的时间参数化器**——两者其实是互补关系，论文也把 Ruckig 当主基线而非对手。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-25)

> **诚实声明**：论文在 §VI 与 §VII 两处分别以超链接形式写明 "The implementation of CFS45 method in C++ is available online **here**" 与 "The planning algorithm runs in a ROS2 environment (see the implementation **here**)"，但**本文抽取的 arXiv 全文文本中不含任何 `github.com` URL 字符串**（仅剩锚文本 "here"）。因此按反捏造原则，**本笔记不给出任何 repo URL、commit hash 或 issue 编号**。以下 3 条 pitfall **完全由 §6 失败模式 + 方法约束推导**，**未经社区 issue 验证**。

### P1 · 「无解即复用旧轨迹」在 1 kHz 目标流下会静默累积滞后

- **机制**：Alg.1 在二分区间 `[-q⃛_m/6, q⃛_m/6]` 内找不到满足 `K` 的实 `t_fi` 时返回 "No solution can be found!"，论文 Remark 明确写："the planner reuses the already-computed trajectory from previous iterations."
- **为什么在工程上危险**：这是一条**静默失败路径**——调用方拿到的不是错误码而是「上一次成功的轨迹」。当上游 DRGBT/ORRT 以 1 kHz 频率刷新 `q_target`、而机械臂恰好处在 jerk 上限约束最紧的构型附近（例如关节接近奇异或速度已接近 `ω_max`）时，CFS45 可能连续多轮返回旧轨迹，而调用方**无从感知**。
- **推导自**：§6 F2 + Alg.1 line 8 + Theorem 1 Remark。
- **落地建议**：在集成层显式计数「连续复用同一轨迹」的轮数，超阈值即降级（减速/停机），不要依赖返回值区分。

### P2 · DEB 保证与实际感知链之间有一道未建模的缝

- **机制**：DEB 用 `v_obs(t - t₀)` 向第 i 个 link 推进分离平面 `P_{i,j}`，检查时把 (10) 中的 `d_c` 减去 `v_obs(t-t₀)`。但 `d_c` 与 `P_{i,j}` 是从**点云拟合的 AABB + capsule 距离查询**得来的（§VII：`f_perc = 20 [Hz]`，两台 D435i）。感知的量化误差、时延、以及人在点云中的**边缘缺失**都不在形式化模型里。
- **为什么在工程上危险**：论文自己承认超过 `v_obs` 时保证失效（§6 F1），而**感知误差可以直接等效地"制造"一次超速**——一个被低估距离的平面 + 一个偏低的 `v_obs` 估计，就足以让「形式化保证」变成「经验上大概安全」。人作为障碍时，论文明确说 "treated conservatively as an external obstacle"，即**放弃预测、只靠膨胀兜底**。
- **推导自**：§6 F1 + §6 Hidden Assumption #1/#2/#6 + §VII 感知设置。
- **落地建议**：`v_obs` 必须按「感知误差 + 时延」反向放大，而非按障碍真实速度设定；同时把感知时间戳纳入 `t₀`。

### P3 · safe 模式的 28× 开销在低算力平台上会打破 1 kHz 叙事

- **机制**：§VI-B 报告 CFS45 占 DRGBT 平均运行时间 regular `at most 0.1 [%]`、safe `2.8 [%]`。两者之比约 **28 倍**，差额来自 `GBur` 构建（Alg.4 的 multi-bur 链式迭代）+ DEB 认证（每个平面 `P_{i,j}` 的膨胀检查）+ 紧急停止 quartic 样条计算。而 §VI 的基准硬件是 `Intel® Core™ i7-9750H @ 2.60 GHz × 12, 16 GB RAM`、**单核、无 GPU**——桌面级 CPU。
- **为什么在工程上危险**：Abstract 宣传的 "up to 1 [kHz]" 是在**桌面 CPU + 仿真**语境下达到的。搬到常见机器人控制器（ARM Cortex-A 级、或无 GPU 的嵌入式 x86）时，2.8% 的占比会随 DRGBT 总时长一起被压低或拉高——关键在于 GBur 的 bur 链长度随 **C-space 维度和障碍数**增长（19 场景 / 10 障碍是评测上限），高 DoF 扩展性被论文自己列为未验证的 future work。
- **推导自**：§6 F4 + §VI-B 数值 + §VIII "robots with many DoFs will be used to inspect how the proposed approach scales with the increased dimensionality"。
- **落地建议**：先在目标硬件上用本项目自己的 planner 复测 `safe` 分支的绝对耗时，**不要直接套用 10⁻⁶ s**（那是 Tab. I 里 regular 量级的代表值）；同时给 `GBur` 的链长设硬上限，超限即降级为「停—走」。

---

[← Back to Motion Planning README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2603.00759 -->
