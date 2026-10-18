[//]: # "<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 智能体式机器人创造：生成、验证与修订 (Agentic Robot Creation through Generation, Verification, and Revision)

> **发布时间**：2026-10-13（arXiv:2610.17881v1 [cs.RO]）
> **论文 / 模型名**：RoboForge（行为创造框架）；形态侧为 GPT-6 Astra 等 MLLM 生成的 Gorilla / Ostrich
> **核心定位**：一句话——它把"策略执行失败"当成对生成内容的**物理验证信号**，并让 agent 判断错在"要它做什么"（参考运动）还是"怎么学"（reward），只改被归因的那一侧；相比 Eureka（只改 reward）与 MimicAgent 式 one-shot（运动定死），首次把 motion 放进执行闭环。
> **Ontology**：`paradigm = learned`（PPO 策略 + LLM agent 决策）；`time = feed-forward`（actor 为 `d_o → 512 → 256 → 128 → d_a` 的三层 MLP，观测无历史窗口）；`problem / representation / sensor` 三轴按 atlas 记为 n/a。

导语：今天"文生机器人"已经能产出看起来像模像样的 CAD，但**好看的机器人不一定造得出来，好看的动作不一定执行得了**。本文一半篇幅用 23 项可计算检查把"造不出来"提前暴露，另一半用 RoboForge 把"执行不了"变成可迭代的修订信号，并真的 3D 打印了一台 agent 生成的大猩猩、把仿真训练的策略直接跑在硬件上。

## X-Ray 开场

论文要解决的是**机器人创造链条的断点**：形态生成、动作生成、reward 生成各自都有工作，但"生成出来"与"物理可行"之间没人验证。作者的做法是给这条链加两道闸门——制造前用 23 项几何/装配/结构/运动检查筛形态；行为侧让 agent 生成参考运动 `M` + tracking reward `r`，训练策略后看 rollout，**诊断失败来自 `M` 还是 `r`**，改完重训（每任务最多 3 次 trial）。对 spatial/embodied AI 研究者意味着：LLM agent 的价值不在"一步生成正确解"，而在于**把物理执行变成可归因的反馈通道**——这是"生成"与"工程"之间的接口协议。

## 📍 研究全景时间线

```
2018 DeepMimic ── 参考运动 + tracking reward 的 RL 范式奠基
  │
2021-22 AMP / ASE ── 用对抗先验替代手工 reward
  │
2023-24 Text2Reward / Eureka ── LLM 写 reward，Eureka 用执行反馈迭代 reward（★只改 how）
  │
2024-25 RoboMorph / Text2Robot / Laser / Lang2Morph ── LLM 做形态搜索与生成
2025    Kinematify / RobotDesignGPT ── 文本/图像 → articulated 模型（★只保证"像"）
  │
2026.09 MimicAgent ── LLM 生成参考轨迹给下游 RL（★运动定死后不再改）
2026.10 ★ 本文 RoboForge ── 形态侧：制造前 23 项可行性检查；行为侧：motion ∈ 执行闭环
  │
  └── 本文局限：形态与行为解耦（D 固定）· 任务全是 locomotion/姿态，无 manipulation
      · 真机仅定性演示 · 归因靠 agent 自行推理，无成功率统计 · 每任务 ≤3 次 trial
```

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **形态生成**（GPT-6） | 参考图（粗形态）+ 任务描述（功能线索）+ 候选执行器 CAD/规格 + **官方装配示例** | `D` = STEP（可编辑零件）+ STL（打印）+ URDF（仿真/控制） | 纯推理，无训练；装配示例被作者明确指出"很重要" |
| **制造前可行性检查** | STEP / STL / URDF + 两条任务参考运动 | 23 项 Pass/Fail（10 设计装配 + 6 机械与执行器 + 7 运动与任务） | 推理期程序化检查，非学习 |
| **参考运动生成** | `D`, `T` | 程序化规格 `B(t)`（根位姿）、`E(t)`（末端目标）、`q_K(t)`（选定任务关节）→ IK 解出其余关节 → `Q, Q̇` → `M` | 推理（agent 写规格 + 求解器） |
| **Reward 配置** | `T`, `M` | DeepMimic 风格可组合 tracking 项（joint-pose / joint-velocity / body-motion）→ `r` | 推理 |
| **策略学习** | `M`, `r` | `π` | 训练：RSL-RL PPO，4,096 并行环境 |
| **执行诊断与修订** | rollout（`q_cmd(t)`, `q_actual(t)`, 接触状态） | `(M_{k+1}, r_{k+1})` | 推理（agent），`D` 与 `T` 固定 |

### 1.2 关键机制

**⚡ Eureka Moment：把"策略跑不出来"拆成可归因的四个层级（任务意图 / 参考运动 `M_k` / 指令 `q_cmd` / 实际 `q_actual` + 接触），先判断是"要它做什么"错了还是"怎么学"错了，再只改那一侧——motion 因此成为闭环里的一等公民，而不是训练开始后就冻结的先验。**

配套的第二个洞见是**"参考运动合法 ≠ 可学"**：两拍对角小跑（two-beat trot）完全满足"高姿态高抬腿走"的语义，但 rollout 暴露后腿支撑崩溃与hind-foot 离地不足，agent 归因为"两腿支撑下质心转移不足"，把步态改成四拍交错摆腿——**语义不变，实现变**。这正是 one-shot 结构在原理上做不到的（§5.3 报告：19 个任务中 11 个被改运动，共 15 次修订）。

### 1.3 信息流

```
用户意图（图 + 任务文字）
        │
        ▼
┌───────────────────┐   23 checks (10+6+7)   ┌──────────────┐
│ 形态生成 (GPT-6)  │ ─────────────────────► │ Pass? ──No──►│ 改设计 / 人工修正
└─────────┬─────────┘                        └──────┬───────┘
          │ D (STEP/STL/URDF)                       │ Yes → 3D 打印 + 装配
          ▼                                         ▼
┌──────────────────────────────┐            ┌──────────────┐
│ 运动规格 B(t),E(t),q_K(t)     │            │ 物理 Gorilla │
│   → IK 解 q_I (式1)           │            └──────▲───────┘
│   → 关节限位/自碰撞/语义检查  │                   │ 部署（走/挥手）
└──────────────┬───────────────┘                   │
               │ M                                 │
               ▼                                   │
┌──────────────────────────────┐                   │
│ reward r ← DeepMimic 风格库  │                   │
└──────────────┬───────────────┘                   │
               ▼                                   │
        ┌─────────────┐   rollout q_cmd/q_actual   │
        │ PPO 训练 π_k │ ──────────────┐           │
        └─────────────┘               ▼           │
               ▲              ┌──────────────────┐ │
               │              │ 4 级失败定位      │ │
               └──────────────┤ 归因: M? r? 都要? │ │
                  (M_{k+1},r_{k+1})  k ≤ 2 (3 trial)
```

## 2 · 数学核心

📌 **Napkin Formula**

```
M_k = IK( B(t), E(t), q_K(t) )  s.t. 关节限位/自碰撞/语义
(M_{k+1}, r_{k+1}) = Agent( rollout( PPO(M_k, r_k) ) )      k = 0,1,2
```

一句话：**运动是 IK 解出来的可执行几何，reward 是可组合的 tracking 项，二者都由"策略跑成什么样"来修订，而机器人本体与任务语义不动。**

**(a) 运动求解（式 1）**

```
q*_I(t) = argmin_{q_I} ‖ e( q_I ; B(t), E(t), q_K(t) ) ‖²
          s.t.  q_min,I ≤ q_I ≤ q_max,I
```

- `I`：未显式规定的肢体关节（被 IK 优化的自由变量）；`K`：任务相关、被显式给定的关节（求解时冻结）。
- `B(t)`：根位姿轨迹；`E(t)`：末端执行器目标状态；`e(·)`：实际末端与目标的残差。
- 直觉：**agent 只写"根怎么走、手/脚到哪、关键关节怎么摆"，剩下的交给 IK** —— 这是把"动作创意"与"关节可行性"分层的关键设计，避免了直接回归关节轨迹必然踩限位。

拼接所有帧得 `Q ∈ ℝ^{N×J}`，时间差分得 `Q̇`，前向运动学得世界系 body 状态（位置/朝向/线速度/角速度）→ 候选 `M̃`；通过检查后记为 `M`。

**(b) 修订递推（§4.2 的算法化表述）**

```
π_k = PPO(M_k, r_k)                    # 每次从零训练，不复用 checkpoint
if success(rollout(π_k)) or k == K_max:  return π_k
else:                                  # 4 级定位后归因
    M_{k+1} = M_k ⊕ Δmotion            # 姿态/轨迹/时序/支撑协调/相位结构
    r_{k+1} = r_k ⊕ Δreward            # 增/删/reweight tracking 项
```

- `K_max = 2`（最多 3 次 trial，§5.1）。论文未给出 `success(·)` 的阈值数值，只说明在 rollout 上评"任务语义符合度 + 执行质量（运动质量、支撑、平衡）"。
- 每次修订必须写明**疑似原因、拟改动、要保留的行为、下次 rollout 期望看到的证据**（§4.3），这是把"反思"结构化的工程手段。

**(c) 与参考无关的度量（式 11–14，用于跨方法比较）**

| 指标 | 公式（要点） | 单位 | 含义 |
|---|---|---|---|
| Yaw Err. | `E_yaw = (1/N) Σ_t |atan2(sin(ψ_t−ψ*), cos(ψ_t−ψ*))|`，`ψ*=0`，世界 +X | rad | 直线行走的航向偏差 |
| Action Var. | `E_action = 1/((N−2)J) Σ_t ‖a_t − 2a_{t−1} + a_{t−2}‖²` | rad² | 指令的二阶差分（抖动） |
| Joint Acc. | `q̈̂_t = (q_t − 2q_{t−1} + q_{t−2})/Δt²`，再取 RMS | rad/s² | 实际关节加速度 |
| Foot-slip | `E_slip = sqrt( Σ_{t,f} c_{t,f}‖v^{xy}_{t,f}‖² / Σ_{t,f} c_{t,f} )` | m/s | 接触期支撑点水平滑移 |

这三个"平滑度/接触"指标的意义在于：**reward 与 tracking error 跨方法不可比（每家的 `M` 和 `r` 都不同），必须用与参考无关的量**。

## 3 · 带数字走一遍（玩具设定）

**设定（明确为玩具）**：单腿 2 自由度，髋 pitch + 膝 pitch，大腿 `l1 = 0.12 m`，小腿 `l2 = 0.12 m`，膝限位 0–55°。任务："高姿态抬腿走"。

**Step 0 · agent 写出的初始规格**：`B(t)` 让髋关节在离地 0.18 m 处，`E(t)` 要求足端在髋前 0.10 m。IK 解：

```
d = √(0.10² + 0.18²) = 0.20591
cos(内角) = (l1² + l2² − d²)/(2 l1 l2) = (0.0144+0.0144−0.0424)/0.0288 = −0.4722
→ 内角 118.2° → 膝屈 61.8°  ❌ 超 55° 限位
髋角 θ1 = atan2(0.18, 0.10) − acos((d²+l1²−l2²)/(2 d l1)) = 60.95° − 30.93° = 30.02°
```

这一步**根本不需要训练**：§4.1 的关节限位检查直接触发，agent 改程序化规格（这一步与论文 §4.1 的"Violations trigger revision of the procedural specification and re-solving"一一对应）。

**Step 1 · 改规格后重解**：把足端目标改成髋前 0.16 m、离地 0.165 m（更伸展，`d` 变大 → 膝更直）：

```
d = √(0.16² + 0.165²) = 0.22984
cos(内角) = (0.0288 − 0.052825)/0.0288 = −0.8342 → 内角 146.5° → 膝屈 33.5° ✅
θ1 = atan2(0.165, 0.16) − acos((0.052825+0.0144−0.0144)/(2·0.22984·0.12)) = 45.89° − 16.74° = 29.15°
FK 复核: 0.12·(cos29.15°, sin29.15°) + 0.12·(cos62.65°, sin62.65°) = (0.1599, 0.1651) ✅
```

**Step 2 · 训练后的 tracking 项直觉**（此处用 DeepMimic 通用指数核 `exp(−2‖Δq‖²)` 演示量级，**非论文原文公式**，论文只说"DeepMimic-style 可组合 tracking 项"）：

| 关节跟踪误差 | pose 项取值 | 说明 |
|---|---|---|
| 0.20 rad | `exp(−2×0.04) = 0.923` | 初始 M 下策略容易到的偏差 |
| 0.10 rad | `exp(−2×0.01) = 0.980` | 改运动后同一策略可达的偏差 |
| 0.05 rad | `exp(−2×0.0025) = 0.995` | 理想跟踪 |

差值 0.057 看似小，但在 PPO 里它改变的是**优势函数的排序**：同样的探索噪声下，靠近 `M_ref` 的样本获得的相对优势被放大，因此"改 `M`"确实能改变学到的策略分布——这就是 §4.2 说"M 提供具体实现、r 提供优化指引"的量化直觉。

**Step 3 · 执行后归因（离散化，对应 §5.3）**：rollout 显示后腿支撑崩溃 + 抬脚离地不足 → agent 判定"两腿支撑下 CoM 转移不足"是 `M` 的问题（不是 reward 权重问题）→ 把两拍对角小跑改成四拍交错摆腿（15 次修订中的一类：**timing and phase structure + support transfer**）。语义检查通过：仍是"高姿态高抬腿走"。

## 4 · 工程视角

| 维度 | 数值（逐字来自论文） | 工程含义 |
|---|---|---|
| 控制频率 | 全机器人 **50 Hz**（每 0.02 s 一次策略更新） | 与常见四足部署一致 |
| 物理步长 / decimation | Go2、MicroDuck、Ostrich：**0.005 s，d=4**；Gorilla：**0.002 s，d=10** | Gorilla 用更小步长（8 DoF 轻量机、接触更硬） |
| 并行环境 | **4,096** | 资源门槛的主要来源 |
| 每轮迭代 | 24 policy steps/env → **98,304 transitions/iter**；5 epochs × 4 minibatch = **20** 次优化 | — |
| PPO 关键超参 | lr `10⁻³`（KL 自适应）、`γ=0.99`、`λ=0.95`、clip `0.2`、entropy `0.005` | — |
| 每任务预算 | GPT / RoboForge：`3 × 3,000 = 9,000` iterations；Eureka-style：`2 × 2 × 2,250 = 9,000`；One-shot：`3,000` | 三法预算严格对齐，这是 Q1 可比性的核心 |
| 每任务环境转移上限 | **884,736,000**（One-shot：**294,912,000**） | ≈ 每任务 8.8 亿步 |
| 修订次数 | 每任务 **at most three training trials**；每次**从零重训，不复用 checkpoint** | 成本随修订线性增长，且不摊薄 |
| 推理开销 | 论文未报告 policy 推理延迟 / 参数量 / FPS | actor 仅 3×MLP（512/256/128），但**论文未报告**任何延迟数字 |
| 显存 / 硬件型号 / 训练 wall-clock | **论文未报告** | 4096 并行环境的实际资源占用无法从文中反推 |
| 真机硬件 | 8× DYNAMIXEL XL330-M288-T + U2D2 + U2D2 Power Hub Board + 外接电源 + 主机 PC（Protocol 2.0）；PLA、Bambu Lab X1E、层高 0.2 mm、填充 15% | 桌面级打印 + 舵机级成本，可复现门槛低 |

**Trade-off 读数**：
1. **预算换取可比性**：把三法都钉在 9,000 iterations，代价是 Eureka-style 被压缩到"2 轮 × 2 候选"（原文 Eureka 是更宽的搜索 + 多 seed 重训），所以 Table 3 里 Eureka-style 的低分**不能读成"Eureka 方法差"**，只能读成"在本预算下 reward-only 不如 motion+reward"。
2. **from-scratch 换取归因干净**：不 warm-start 是为了避免"改进来自累计优化"这一混淆（论文明确说明）；代价是 3 次 trial 的成本 ≈ 3 倍单次训练，且 19 任务 × 4 方法 = 76 条训练流水线。
3. **每个任务都重造 `M`**：没有跨任务/跨机器人的运动先验复用，换一个机器人等于运动生成、IK、reward 配置全部重来。

## 5 · 数据与评测

**没有数据集**——评测完全是自建任务集 + 自建仿真场景 + 人评。

**机器人（4 台）**

| 机器人 | 来源 | DoF | 备注 |
|---|---|---|---|
| Unitree Go2 | 现有平台 | 记录 J=12 | — |
| MicroDuck | 现有平台 | 记录 J=14 | — |
| Ostrich | **GPT-6 Astra 生成** | 15（颈头 6 + 每腿 4 + 尾 1），18 links / 17 joints | 未制造 |
| Gorilla | **GPT-6 Astra 生成** | 8（每肢 2 个 pitch），9 links / 8 revolute | **已 3D 打印并装配**，记录 J=8 |

**任务（19 个 = 7 walking + 12 whole-body skills）**——逐字来自 Table 7：

| 机器人 | Walking | Whole-body skills | 合计 |
|---|---|---|---|
| Go2 | High-step walk; low walk | Bow; look around; kick | 5 |
| MicroDuck | Fast walk; waddling walk | Bow; look around; kick | 5 |
| Ostrich | Happy walk; sad walk | Nod; stretch; squat and rise | 5 |
| Gorilla | Alternating walk | Handstand; stretch; wave | 4 |

**Baselines（三选，均同一 GPT-6 Astra agent、同一 PPO 架构、同一仿真配置）**
- **Eureka-style**：只做 reward 搜索/反思（2 轮 × 2 候选 × 2,250 iters），**不使用参考运动、不用逐帧 tracking 目标**。
- **One-shot Motion**：MimicAgent 式 generate–validate–train，与 RoboForge **共享同一个初始 `M` 和 `r`**，训练开始后冻结；**它等价于 RoboForge 的第一次 trial**。
- **Unguided GPT（Q3）**：只给 actor 模板 + 任务 + 通用 RL 工具，不告诉它要生成/修订运动。

**评测设置（条件先讲清）**
- **人评**：`n = 57` 名被试，`76` 条策略视频（4 方法 × 19 任务），1280×720 / 30 fps，任务内摄像与播放速率固定、方法匿名（A–D），1–5 分整体评分（语义达成 + 执行质量合并）；同一任务内**同一批评委评全部四法**（paired）；3 秒最短完成时间过滤；聚合为"任务内按有效评分数加权 → 机器人内等权 → 四机器人等权"的两级规则。
- **物理指标**：50 Hz 采样，禁用自动 reset、保留原生终止事件（**失败后仍继续录到任务窗结束**，避免只统计"活下来"的偏置）；接触检测阈值 Go2 `10 N`、MicroDuck `0.5 N`、Ostrich/Gorilla `0.3 N`；Yaw/slip 只在 7 个 walking 任务上算，Action Var/Joint Acc 在 19 个任务上算。

**主结果（逐字）**

| 方法 | Go2 | MicroDuck | Ostrich | Gorilla | Overall |
|---|---|---|---|---|---|
| Eureka-style | 2.79 | 2.01 | 2.00 | 1.59 | 2.10 |
| One-shot Motion | 3.93 | 3.30 | 4.04 | 3.14 | 3.60 |
| RoboForge | **4.10** | **4.03** | 3.99 | **3.77** | **3.97** |

| 方法 | Yaw Err. (rad) | Foot-slip (m/s) | Action Var. (rad²) | Joint Acc. (rad/s²) |
|---|---|---|---|---|
| Eureka-style | 0.0345 | 0.121 | 0.0830 | 114 |
| One-shot Motion | 0.0584 | 0.0716 | 0.00665 | 31.7 |
| RoboForge | **0.00836** | **0.0131** | **0.00290** | **22.0** |

**Q2（motion 进闭环改变了什么）**：11/19 任务被改运动，共 15 次修订；四类修订=姿态与肢体轨迹 / 时序与相位 / 支撑转移 / 全身协调。**Q3（无引导 GPT）**：自发引入参考运动 16/19、修订 7/19；用户评分 3.61 vs RoboForge 3.97，Foot-slip 0.0419 vs 0.0131，Action Var. 0.0179 vs 0.00290。

**形态侧（Table 1，`x/y` = 通过/总数）**

| 检查类 | GPT6-Astra | GPT5.6-Sol | GPT5.6-Terra | GPT5.5 |
|---|---|---|---|---|
| Design and Assembly | **6/10** | 4/10 | 4/10 | 3/10 |
| Mechanical and Actuation | **4/6** | 0/6 | 1/6 | 0/6 |
| Motion and Task Execution | **5/7** | 1/7 | 1/7 | 1/7 |

（由 Table 13 逐项核对可复算：Astra 合计 15/23，Sol 5/23，Terra 6/23，GPT5.5 4/23——此合计为本文算术推导，非原文直接给出。）

## 6 · 能力与失败模式

**能做（有证据）**
- 从图 + 文字生成**可打印、可装配、可驱动**的 8-DoF 机器人：Gorilla 被实际 3D 打印、装配、上电。
- **直接部署 sim 训练的策略**到硬件：alternating walk（需反复手–脚支撑转移）与 wave（其余三肢保持支撑）。
- 在"合法但难学"的参考运动上做**语义保持的实现替换**：两拍 trot → 四拍交错步态；Gorilla handstand 上把"小腿外旋"改成"先内收小腿再翻起"从而完成倒立。
- 用与参考无关的指标证明"用户觉得更好"不是错觉（四指标全优）。

**不能做 / 未验证（要具体）**
- **无 manipulation**：19 个任务全是 locomotion + 姿态/全身技能，没有抓取、推动、接触力调制类任务（这与 `M` 的表达力直接相关，见下）。
- **无外部感知**：观测只有 `[c_t, g_t^b, q_t−q_0, q̇_t, a_{t−1}]`（式 3，`d_o = 6 + 2J + d_a`），无视觉/地形/接触传感；"上台阶""过障碍"这类需要感知的任务未被触及。
- **形态与行为不联合优化**：`D` 在整个运动–RL 循环中固定（joint 定义与结构冻结），所以"这个动作对这具身体不可学"只能通过改动作解决，不能通过改身体解决。
- **真机只有定性**：Gorilla 上只展示 walking 与 waving 的动作序列，**论文未报告任何真机定量指标**（无真机成功率、无 sim-to-real 误差、无滑移测量）。
- **改进非单调**：Ostrich 上 One-shot 的 Overall（4.04）略高于 RoboForge（3.99）；Gorilla 上 One-shot 的 Action Var.（0.00023）与 Joint Acc.（4.88）优于 RoboForge（0.000482 / 10.8）；Go2 的 Yaw 最优是 Eureka-style（0.00807）；与 GPT 相比更好时，MicroDuck 的 Action Var./Joint Acc. 和 Gorilla 的 Action Var./Joint Acc. 反而输给 GPT。作者自己承认"refinement 在首轮策略较弱时收益最大"。

### 隐含假设 (Hidden Assumptions)

1. **程序化运动规格足够表达**：`M` 只能由根位姿 `B(t)` + 末端目标 `E(t)` + 选定关节 `q_K(t)`（其余靠 IK）刻画。这隐含"任务的关键在于运动学轨迹"；一旦成败取决于力矩曲线或接触力分布（推、拧、抓），该参数化就装不下。
2. **IK 总有解且解唯一可用**：式 1 是带箱约束的最小二乘，未讨论奇异位形、多解选择、以及"IK 解出的 `q_I` 在动力学上不合理"的情形。
3. **失败可被正确归因**：整篇方法建立在"agent 能从 4 级信号判断问题在 `M` 还是 `r`"之上，但论文未报告归因准确率，也没有人工标注的归因真值做对照——只用"最终评分提升"间接背书。
4. **人评即任务达成真值**：任务语义被刻意留欠定（amplitude/timing/coordination 不指定），因此必须靠 5 分制人评裁决；`n = 57`、每任务评委数不等（如 Gorilla walking 只有 14 条有效评分），跨任务绝对分不可比。
5. **检查阈值即物理真值**：许用应力 8 MPa、应力集中系数 2、附加储备 3（局部裕度 `8/(6σ_eq) ≥ 1`）、打印公差 ±0.2 mm、M2 螺纹最坏径向间隙公式……论文自己注明"Structural outcomes are conditional calculations, **not measured strength**"。检查通过 ≠ 一定不坏。
6. **仿真保真度足够**：Isaac Lab 2.1 / Isaac Sim 4.5，地面摩擦 1.0、restitution 0，默认**不加观测噪声、不做 reset 扰动、不加外力推**——策略在"干净"条件下学成，真机鲁棒性未被压测。
7. **装配知识可被示例注入**：形态生成依赖候选执行器 CAD + 官方装配示例；没有示例时模型退化为"视觉上合理地摆放部件"（§3 明确说这些示例"important"）。

## 7 · 与相关工作对比

| 方法 | 生成形态 | 生成参考运动 | 生成/修订 reward | 执行反馈闭环 | 真机 |
|---|---|---|---|---|---|
| RoboMorph / Text2Robot / Laser / Lang2Morph | ✅（搜索/生成） | ❌ | ❌ | ❌（形态侧） | 论文未提及 |
| RobotDesignGPT / Kinematify | ✅（图/文 → articulated） | ❌ | ❌ | ❌ | 论文未提及 |
| Eureka（2024） | ❌ | ❌ | ✅（执行反馈迭代 reward） | **只改 how** | 论文未提及 |
| MimicAgent（2026） | ❌ | ✅（prompt → trajectory，含生成期校验） | 部分 | **只改 what，且定死后冻结** | 论文未提及 |
| DeepMimic / AMP / BeyondMimic 系 | ❌ | 人工/数据驱动 | 人工设计 | ❌（参考与 reward 均给定） | — |
| **RoboForge（本文）** | ✅ + **23 项制造前检查** | ✅ | ✅ | **✅ 双侧归因后择一/同改；motion 在环** | ✅ Gorilla 定性演示 |

**面试 Tip（被问"这不就是 Eureka + MimicAgent 拼起来吗？"）**：
"拼不起来。Eureka 只改 how、MimicAgent 只给 what 且训练一开始就冻结——两个都是**开环的生成器**。本文的贡献是**中间的归因算子**：用 `q_intended / M_k / q_cmd / q_actual`+接触这四层信号判断失败属于哪一侧，然后只改被归因的那一项，并把'疑似原因 + 拟改动 + 要保留的行为 + 下次 rollout 的期望证据'写成结构化的修订记录。证据是 19 个任务里 11 个被改运动、共 15 次修订——这个频率说明'生成出来的合法运动经常不可学'，而这正是任何 one-shot 结构在原理上看不到的信号。另外注意它把评测设计得很克制：三法预算严格对齐 9,000 iterations，且所有指标都与各自方法的参考运动无关，否则 tracking error 根本不可跨方法比。"

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-18)

**诚实说明：论文全文未出现任何 `github.com` 仓库链接**，只给出项目页 `https://roboforge-project.github.io/`（且为纯文本，非可点击超链接）。因此**没有 issue 流可供验证**，以下 4 条 pitfall 全部由 §6 的失败模式 + 方法内部约束推导，**未经 issue 验证**。

1. **3 次 trial 的硬上限会让"最后一版"顶替"最好一版"**
   - §6 失败模式：初始运动可能严重不可学（Ostrich 两拍 trot 的支撑崩溃）。
   - 方法约束：§4.2 "If the trial budget is exhausted, `π_k` is returned **without further review**" + §5.1 "at most three training trials per task"。
   - 后果：没有 best-of-k 选择，也没有回退到更保守运动的机制；若第 2、3 次修订方向错了（归因错误），交付的是**最差的那次**而非第 1 次。落地时必须自己加跨 trial 选优或"修订无效则回滚"。

2. **from-scratch 重训把修订成本乘成线性，且没有 checkpoint 复用**
   - 方法约束：Appendix D.2 "Each refinement trial retrains the policy **from scratch without reusing checkpoints**"；预算 `3 × 3,000` iterations，`884,736,000` transitions/task 上限，4,096 并行环境。
   - 后果：19 任务 × 4 方法、且 RoboForge 侧最多 3 倍重训；论文**未报告** wall-clock / GPU 型号 / 显存，无法从文中估算单卡可行性。想省钱改 warm-start 会直接破坏 Q1 的归因（作者自己说改进就不能再归因于 guidance 修订）。

3. **23 项检查里有 8 项是"全员 Fail"、4 项是"全员 Pass"，区分度极低；阈值又是手工常数**
   - 数据事实（Table 13 逐项）：四个模型**全部 Fail** 的是 Fit tolerance (A05)、Assembly and tool access (A06)、Fastener interfaces (A07)、Static assembly clearance (A09)、Simulation tracking (DB05)、Continuous clearance (B05)、Load-path strength (C02)、Cable routing (C05)；**全部 Pass** 的是 Export volume fidelity (DA03)、BOM completeness (DA04)、Print envelope (DA06)、Mechanical model (DB01)。
   - 方法约束：Appendix I.4 的阈值是硬编码的工程常数（如 `peak torque ≤ 0.100001 N·m`、`saturation fraction ≤ 0.001`、许用应力 8 MPa、打印 ±0.2 mm、M2 最坏径向间隙公式）。
   - 后果：换执行器（XL330 → 其他型号）或换打印机，必须**整套重标定**；Table 1 的 `15/23 vs 5/23` 只能读作"在这套阈值下的相对排序"，不能当作设计质量的绝对分。连续间隙预算里 `5°` 的 tracking 允许量更是直接与策略质量耦合，意味着"检查通过"依赖你后面训出来的策略。

4. **`M` 的表示决定任务上限：根轨迹 + 末端目标 + 选定关节 + IK ⟹ 只覆盖运动学型任务**
   - 方法约束：§4.1 的规格只有 `B(t), E(t), q_K(t)`，其余关节由式 1 的 IK 逐帧求解（无动力学、无力矩可行性、无接触力规划）。
   - 失败模式对应：§6 的"无 manipulation"——19 个任务全是 locomotion / 姿态（Table 7），没有需要力调制的任务。
   - 后果：把 RoboForge 直接搬到"推箱子/开门/抓取"上，agent 会反复改 `E(t)` 却永远解不出"该用多大力"，归因层会把动力学失败误判成运动失败，3 次 trial 迅速耗尽。

---

[← Back to agentic-robot-creation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（HTML 版，含 Appendix A–I）· 未在真机复现的数字标 `UNVERIFIED`；§4 中 latency / 显存 / 训练时长论文未报告；§5 所有指标与数据集规模均逐字取自正文表格；§8 无官方 GitHub 仓库，pitfall 为推导而非 issue 验证。

[//]: # "<!-- source: https://arxiv.org/abs/2610.17881 -->"
