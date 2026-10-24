[//]: # "<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: geometric
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# VAMP-MR：多机械臂运动规划与执行的向量加速 (VAMP-MR: Vector-Accelerated Motion Planning and Execution for Multi-Robot-Arms)

> **发布时间**：2026-07-15（arXiv:2607.13478v1 [cs.RO]）
> **论文 / 模型名**：VAMP-MR（Vector-Accelerated Motion Planning for Multi-Robot-Arms）
> **核心定位**：把 VAMP 的单臂 SIMD 碰撞检测原语推广成"多机械臂、可运行时配置、按碰撞类型分离"的向量化内核，作为 FCL 的 drop-in 替代，在多臂规划 / 捷径后处理 / 安全执行全链路上拿到 10–100x 加速——**不改任何上层算法**。

导语：多机械臂运动规划（M-RAMP）里几乎每个阶段——建 roadmap、采样验证、机器人间碰撞检测、shortcutting、构造 temporal plan graph——都被同一个原语支配：碰撞检测（CC）。VAMP-MR 的结论很干脆：只把这一个原语向量化（球体几何 + CPU SIMD 批通道 + 按机器人分离的早停检查），RRT-Connect、CBS-MP、DTS、APEX-MR 这些算法一行不改就能快一到两个数量级。

---

## X-Ray 开场

多机械臂系统真正卡住的地方不是搜索算法，而是**碰撞检测**：FCL/Bullet 这类基于 BVH 的检查器是单查询、分支密集、内存访问不规则的，天然难并行。VAMP-MR 提出的做法是：把若干台臂的几何统一球体化，把**一个 batch 的复合配置塞进 SIMD 通道**（AVX2，8 lane），FK 与 CC 融合成单个 C++ header 内核，并显式区分 self / robot-environment / robot-robot 三类检查，支持附件、障碍物、allowed contacts、基座变换在**运行时增删改而无需重编译**。对 spatial AI 研究者的意义：这是一篇"原语级加速"论文——它不动学习、不动搜索，只把几何内核做到极致，然后证明现代 CPU 的 SIMD 仍然是被低估的机器人算力，GPU/FPGA 的设备通信开销反而抵消了收益。

---

## 📍 研究全景时间线

```
单臂采样规划 ──► 多臂 MAPF 化 ──► 多臂操作执行 ──► 向量化原语 ──► 本 文
 RRT-Connect        CBS-MP [10]      APEX-MR [18]      VAMP [1]        VAMP-MR
 (1999-2000)       (2019-2023)       (2024-2025)      (2022-2024)     (2026)
     │                  │                 │                │              │
 验证采样即CC      两级搜索,            TPG 异步执行,    单臂固定内核,   多臂可配内核
 BVH/FCL 单查询    冲突检测=CC           TPG 构造=O(n²)CC  SoA+SIMD      +分组早停
     │                  │                 │                │              │
     └────────── 碰撞检测始终是共同瓶颈 ──┴────────────────┴──────────────┘
                                                        ▼
                                              本文局限：
                                              · 球体近似损失几何精度
                                              · 早停 ⇒ 只能答"是否碰",
                                                不能答"碰多少/哪对"
                                              · 只测 x86 AVX2(8 lane)
                                              · Panda 系列 + LEGO 场景
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统/组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| **FK_CC_Multi**（核心贡献，Alg.1） | batch 的 `v` 个复合配置 `{(C¹…C^N)_j}`、各臂基座变换 `^wT_i`、附件 `A^i`、静态障碍 `^wO`、allowed contacts `W_allow` | `Valid / Invalid`（仅当 batch 内全部 v 个复合配置均无碰撞才 Valid） | **纯推理**，无学习参数；内核编译期确定机器人结构，运行期可改基座/附件/允许接触 |
| **Composite RRT-Connect** [4] | 所有臂 DoF 拼成一个复合 C-space | 轨迹 | 纯推理；RRT 扩展中的采样验证与边验证全部走 FK_CC_Multi |
| **CBS-MP** [10]（改为非对称约束） | 每臂独立 PRM（每臂 5000 节点）、起止配置 | 分辨率最优轨迹 | PRM 构建离线一次性，规划在线；roadmap 构建 / 冲突检测 / 低层约束评估三处都被加速 |
| **DTS 捷径化** [5] | 初始轨迹 + 时间预算 | 更优轨迹 | 纯推理；复合/优先/路径三种 shortcut 策略由 Thompson sampling 选择 |
| **多模态 TPG**（APEX-MR [18]）+ 分组策略 | 顺序或同步的任务-运动计划 | 异步 TPG（DAG） | 离线后处理，无学习；分组把 k 个 pose node 合并成 transit node 使早停可用 |
| **TOPPRA** [33] | 复合空间轨迹 | 满足加速度限的时间参数化轨迹 | 纯推理；真机部署时使用 |

### 1.2 关键机制

**⚡ Eureka Moment：碰撞检测是 M-RAMP 全流水线（roadmap → 搜索 → shortcut → TPG）唯一贯穿的瓶颈；只要把"球体几何 + 每机器人分离查询 + struct-of-arrays 布局 + CPU SIMD 批通道"这一个原语做到极致，上层算法一字不改就能整体加速 10–100x。**

支撑这个洞见的三处工程设计：

1. **不做单一复合内核**。朴素做法是把所有臂 DoF 拼成一个单体内核，但这样既无法分离三类碰撞（roadmap 只需要 self+env），也无法做机器人对之间的碰撞计数（CBS/TPG 需要），更无法在不重编译的前提下修改 `^wT_i`、`A^i`、`W_allow`。VAMP-MR 反过来做：**按机器人遍历**，每个机器人内部走单臂 VAMP 风格 FK+自碰撞，再做缓存的 env 检查，最后转世界系做两两 inter-robot 检查。
2. **早停与批处理的矛盾**。`FK_CC_Multi` 只要 batch 内任一配置碰撞就整批拒绝——这对"验证"是安全的，但对"找出所有碰撞对"（TPG 原式要求）是致命的。TPG 里用**分组策略**破解：把 k 个连续 pose node 合成一个 transit node（代表一段短路径），只问"两段路径是否有任何碰撞"，早停立刻可用；代价是优先级约束变粗（要等对方一整段），论文实测 makespan 差异可忽略。
3. **单线程反而赢多线程**。FCL 基线用 16 线程并行 TPG 构造，VAMP-MR 单线程仍快 6.9–21x——因为向量化把通信/同步开销降到零。作者明确说"多核并行在向量化面前基本不必要"。

### 1.3 信息流 ASCII 图

```
             batch: v 个复合配置 (C¹,...,C^N)_1:v  +  ^wT_i, A^i, ^wO, W_allow
                                      │
        ┌─────────────────────────────┴──────────────────────────────┐
        │                    for each robot i                       │
        │   C^i_{1:v} ──► FK(...) ──► ^iS_{1:v} (球体, 机器人系)      │
        │                     │                                      │
        │               SelfCC(^iS) ──碰──► Invalid（整批拒绝，早停） │
        │                     │ 否                                   │
        │   ^iO = (^wT_i)^-1 ∘ ^wO  （缓存：基座/障碍常固定）          │
        │   EnvCC(^iS, ^iO, W_allow) ──碰──► Invalid                 │
        │                     │ 否                                   │
        │   ^wS^i_{1:v} = ^wT_i ∘ ^iS_{1:v}   （转世界系）           │
        └─────────────────────────────┬──────────────────────────────┘
                                      │
              for each robot pair (i,k), i<k:
                  InterCC(^wS^i, ^wS^k) ──碰──► Invalid
                                      │ 全通过
                                      ▼
                                    Valid
```

下游复用：RRT 的采样/边验证、CBS 的三处碰撞、DTS 的 shortcut 验证、TPG 的 transit node 两两检查——**同一个 `FK_CC_Multi` 的不同查询模式**。

---

## 2 · 数学核心

📌 **Napkin Formula**：一个 batch 的复合配置有效 ⇔ 对 batch 内每个配置、每对球体，球心距 ≥ 半径和（allowed contact 除外）：

```
Valid(B) ⇔ ⋀_{j=1..v}  ⋀_{a<b}  [ ‖p_a^j − p_b^j‖ ≥ r_a + r_b ]
```

逐个符号说清楚：

- **目标**：把"复合配置是否无碰撞"这一布尔判定，从"调用一次碰撞库"变成"一次 SIMD 指令流处理 v 个配置"。
- **FK**：`^iS_{1:v} ← FK(C^i_{1:v}, A^i)`，由自定义 tracing 编译器展开，直接算球心坐标，最小化分支与数据依赖；自碰撞检查与 FK 交织以便早停。
- **三类检查**：
  - Self：`SelfCC(^iS_{1:v})`
  - Env：先 `^iO ← (^wT_i)^{-1} ∘ ^wO`，再 `EnvCC(^iS_{1:v}, ^iO, W_allow)`
  - Inter：先 `^wS^i_{1:v} ← ^wT_i ∘ ^iS_{1:v}`，再对所有 `(i,k), i<k` 做 `InterCC(^wS^i, ^wS^k)`
- **批语义**：返回 `Invalid` 当且仅当 ∃ j 使第 j 个复合配置碰撞；否则 `Valid`。这是"**全称量化**"而非"存在量化"——直接决定了它不能回答"哪一对/多少次碰撞"。
- **运动验证（rake）**：沿一条边按 L1 分辨率（实验中 0.1 rad）均匀取 v 个配置填满 SIMD lane，一次判定整段边是否无碰撞。分辨率决定漏检上界：不是连续扫掠，而是离散采样。

**直觉**：BVH/GJK（FCL）是"**一次深搜一棵树**"，条件分支多、访存不规则，一个 SIMD 通道都用不上；VAMP-MR 是"**一次浅扫一排球**"，把朴素的 O(球对数) 检查摊到 8 条 lane 上，算术强度低但极其规则——这正是 SIMD 的主场，也是它必须靠球体近似才能成立的原因（球-球距离是极简的算术，不需要 GJK 迭代）。

---

## 3 · 带数字走一遍（玩具设定，非论文实验）

**玩具设定**：一台 1-DoF 臂，只关心一个关节角 θ ∈ ℝ，臂上 2 个球体（r=0.05, 球心距关节分别为 0.1 与 0.2），环境里 1 个静止球体障碍（r=0.05，距关节 0.25）。AVX2，v=8。

**单配置检查**：某配置下臂球 1 与障碍球心距 0.18，半径和 0.10 → `0.18 ≥ 0.10` 通过；臂球 2 与障碍球心距 0.05 &lt; 0.10 → 该配置 Invalid。

**运动验证（rake）**：规划从 θ=0 到 θ=0.7 rad，分辨率 0.1 rad ⇒ 需要 `⌈0.7/0.1⌉+1 = 8` 个插值样本 ⇒ **恰好一个 SIMD batch**。若第 5 个样本臂球 2 与障碍相交，则整批返回 `Invalid`——这正是"早停"：第 5 lane 命中后不必算第 6–8 lane。

**批处理语义的代价（分组策略的数字直觉）**：TPG 里若逐个 pose node 做两两检查，需要 `O(N² · L²)` 次单查询；把每 k=8 个连续节点压成 1 个 transit node 后，查询次数变成 `O((N·L/k)²)`，且每次查询内部正好填满 8 lane 并支持早停。代价：某机器人必须等对方走完 8 个 pose node 而不是 1 个——论文实测"makespan 差异可忽略"（Table III 中 Ours 的 makespan 反而全面更低，但那主要来自 TPG shortcutting 更充分，不能单独归因于分组）。

> 以上为玩具设定下的算术演示，非论文实验数字；论文真实数字见 §4 / §5。

---

## 4 · 工程视角

**硬件与编译（论文明确给出）**：AMD 7840HS **笔记本 CPU**；C++ / GCC 9；`-march=native -mavx2 -O3`；256-bit AVX2 ⇒ **单精度 SIMD batch size = 8**。作者明确选择 AVX2 而非 AVX-512，理由引用 VAMP [1] 的观察：512-bit 指令因功耗/散热会拉低 CPU 频率，AVX2 是更好的平衡点。

**碰撞检测原语（Table I，10,000 随机样本）**：

| 查询 | 环境 | FCL (µs) | Ours (µs) | Speedup |
|---|---|---|---|---|
| Single | Panda Two Rod | 100.99 | 8.60 | 11.7x |
| Single | Panda Four | 206.53 | 15.01 | 13.7x |
| Single | Panda Four Bins | 382.63 | 13.70 | 27.9x |
| Motion | Panda Two Rod | 3936.13 | 36.03 | 109.2x |
| Motion | Panda Four | 4836.50 | 32.61 | 148.3x |
| Motion | Panda Four Bins | 930.03 | 14.23 | 65.4x |

**吞吐/延迟解读**：motion 验证的加速比常常超过 lane 数（8x），作者归因于向量化 + 良好 cache 利用 + rake 扫描三者叠加；同时也观察到跨环境方差比 FCL 小（FCL 在障碍密集的 Panda Four Bins 里要慢很多才否掉碰撞样本）。

**缓存行为（Table II）**：除 Panda Two Rod 的 RRT 外，VAMP-MR 的 cache miss rate 均显著低于 FCL（如 Panda Four Bins RRT：13.81% → 1.72%；MPKI 2.62 → 0.51）。Panda Two Rod RRT 是唯一反例（4.11% → 7.49%），论文未给出解释，只陈述现象。

**规划层（Fig. 4）**：中位规划时间加速"at least an order of magnitude"，**最高至 150x**。RT 与 CBS 都受益，CBS-MP 受益更大。CBS-MP 在 1 分钟时限内可扩展的 constraint tree 节点数从 FCL 下**最多 53 个**提升到**5303 个**（Panda Four）。但加速后 CC 仍是最大开销：**Panda Four 上 RRT-Connect 占 90.2%，CBS-MP 占 64.6%**。

**后处理（Fig. 5）**：DTS shortcutting 的收敛时间**最高 50x** 加速，0.1 s 内已有可观提升，1 s 内完全收敛。

**多线程 vs 单线程（Table III 关键 trade-off）**：FCL 基线用 **16 CPU 线程**并行 TPG 构造，VAMP-MR **单线程**，TPG 构造仍快 **6.9–21x**（如 Chair：817.2 s → 43.22 s）。作者结论：向量化后多核并行的通信开销基本不划算。

**真机（3 台 Kinova）**：11 次规划调用，**中位规划时间 0.16 s，样本标准差 0.70 s**（两个困难实例分别 2.36 s / 1.06 s）；整段演示约 **85 s**，规划合计 **4.7 s（~6%）**，每条执行动作平均约 **7 s**。

**内存/显存/功耗**：论文**未报告**峰值内存、DRAM 带宽、功耗数字；仅报告了 cache miss rate / MPKI（Table II）。GPU/FPGA 的通信开销是定性讨论，无量化对比。

**部署约束**：
- 依赖 x86 AVX2 与特定编译 flag；非 x86 平台（ARM/Jetson）论文**未报告**，也无标量回退路径的性能数据。
- 内核按机器人结构编译，但 `^wT_i`、`A^i`、`W_allow`、collision pair 的增删与基座重标定**运行时完成，无需重编译**——这是相对原版 VAMP 的关键工程改进。
- env 障碍在机器人系里**缓存**（假设基座与障碍规划期间不变）；基座移动即缓存失效。

---

## 5 · 数据与评测

**碰撞检测基准（Sec. III-B）**：三个多机械臂环境 **Panda Two Rod / Panda Four / Panda Four Bins**，**引自 [5]**（论文原文："introduced in [5]"），见 Fig. 3。每台 Panda **7 DoF**，用 [27] 的工具生成 **59-sphere** 近似（Fig. 2(b)）。Panda Two Rod 每臂加一根 rod 附件；Panda Four Bins 加料箱作为必须伸入的障碍。**10,000 个随机样本**；单配置检查 `v=1`，运动验证 `v=8`，分辨率 **0.1 radian**（连续插值配置间的 L1 距离）。基线 **FCL [2]**（MoveIt [28] 与既有系统 [18,10] 的默认检查器），并且**用同一套球体化几何**喂给 FCL 以保证建模一致。Bullet [3] 未实测，论文只做定性预期（"expect similar trends"）。

**规划基准（Sec. IV-A）**：**110 / 132 / 132** 组唯一起止位姿对，分别对应 Panda Two Rod / Panda Four / Panda Four Bins，**as in [5]**。CBS-MP 每臂 PRM 采样 **5,000 节点**，两种规划器均 **1 分钟超时**。roadmap 构建每环境一次、**不计入**报告时间，其加速**未评测**。

**捷径化基准（Sec. IV-B）**：初值轨迹来自 RRT-Connect 与 CBS-MP 两者；报告随时间的 makespan 改进曲线（Fig. 5）。

**长程装配基准（Sec. IV-C，Table III）**：四个双臂 LEGO 装配任务 **Cliff / Vessel / Fish / Chair**，**取自 APEX-MR [18]**，最多 **258** 块积木；砖块数分别为 **11 / 36 / 29 / 258**。流程遵循 [18]：ILP 做 task assignment → 单臂 RRT-Connect 逐段规划 + 0.1 s 向量化单臂 shortcutter 平滑 → 转成异步 TPG 并做 TPG shortcutting。**与 APEX-MR 原实现的重要差异**：论文自己直接实现 RRT-Connect（基线也用同一实现），FCL 基线用**原始 mesh**（作者发现比球体化更快），故其结果不能与 [18] 原文数字直接横比。结果对 **4 个随机种子**平均。TPG shortcut 时间预算：Cliff/Vessel/Fish 各 **1.0 s**，Chair **5.0 s**。

**真机（Sec. V）**：**3 台 Kinova 臂**，连续规划执行 **11 个复杂高度缠绕的构型**；复合 RRT-Connect 出初值 → anytime shortcutter 跑 **1 s** → TOPPRA 在复合空间做时间参数化以满足加速度限制。因无接触、无操作策略，控制器延迟极小，故**同步执行、不需 TPG**。

**指标定义**：solution quality 用 **makespan**（最后一台到达目标的总执行时间）。**未报告**成功率数字（除 Panda Four Bins "reaching a 100% success rate"、Panda Four 部分实例未解这两处定性+单点陈述）、未报告路径长度、平滑度、能耗等指标。

---

## 6 · 能力与失败模式

**能做**：
- 作为 FCL 的 drop-in 替代，在**不改任何上层算法**的前提下把 CC 加速 11–148x（单查询到运动验证）。
- 支持任意数量机械臂的**复合批查询**，并按 self / robot-env / robot-robot **分离**检查类型（roadmap 只需前两类，CBS/TPG 需要第三类）。
- 支持附件（grasped object/tool）、静态障碍、**allowed contacts**（如夹爪抓取物体时的有意接触被忽略）。
- 运行时增删 collision pair、重标定基座、换附件**无需重编译内核**。
- 加速下游全部三个阶段：规划（RRT / CBS）、shortcutting（DTS）、安全执行（TPG 构造）。
- 在复杂长程装配任务上把 TPG 构造从分钟级压到秒级（Chair：817.2 s → 43.22 s，单线程 vs 16 线程）。

**不能做 / 失败模式**：
- **只能答"是否碰"，不能答"碰多少 / 哪一对 / 哪些配置"**：batch 内任一配置碰撞即整批 `Invalid`。任何需要碰撞计数或定位的算法（CBS 的冲突选择、原始 TPG 的逐对依赖）都必须改查询粒度，否则信号被抹平。
- **球体近似是有损的**：几何被 59 球近似后面目全非；论文自己承认在 LEGO 任务里 FCL 用原始 mesh 反而更快——说明球体化不是无条件的赢。
- **不是连续碰撞检测**：运动验证是 0.1 rad 分辨率的离散采样（rake），分辨率以下的薄障碍/擦碰可能漏检。
- **仍然解不完**：Panda Four 上部分实例 1 分钟内无解（需要数千次高层 CBS 扩展的精确时序协调）；Panda Four Bins 则达到 100% 成功率。
- **加速后 CC 仍是最大开销**：Panda Four 上 RRT-Connect 90.2%、CBS-MP 64.6% 的规划时间仍在碰撞检测上——本方法缓解而非消除瓶颈。
- **不是所有阶段都受益**：task assignment 只小幅提升（0.60→0.55、4.90→4.68、5.81→5.45、13.0→10.2），因为 ILP 本身是独立瓶颈；Chair 的 makespan 改进"minimal"，因为评估随机 shortcut 时修改障碍位置的 overhead 很大。
- **AVX2 专属**：选择 AVX2 而非 AVX-512 是刻意的降频权衡；论文未给出 ARM/NEON、标量回退、或跨平台性能数据。

### 隐含假设 (Hidden Assumptions)

1. **静态环境 + 固定基座**：`^wO` 与 `^wT_i` 规划期间不变，才有"缓存机器人系障碍"的合法性；任务中物体被搬动即失效（LEGO 装配正是靠"每种 mode 重建一次"绕开）。
2. **球体近似对外切保守**：加速成立的前提是球体包住真实几何、不漏检；若为提速用内切球，会静默漏掉真实碰撞。
3. **离散分辨率足够**：0.1 rad 的 L1 分辨率被认为能覆盖扫掠碰撞；薄壁/高速关节运动下这是未证明的。
4. **早停语义安全**：返回 `Invalid` 是保守的（宁可误报不误放），因此对"验证"安全；但任何把 `Invalid` 解读为"恰好一处碰撞"的下游都会出错。
5. **TPG 分组引入的额外等待可忽略**：这是**经验观察**（"empirically, however, we find this makespan difference to be negligible"），不是有界保证；任务规模/机器人数量变化时可能失效。
6. **PRM 完备性即 CBS 完备性**：CBS-MP 的保证是"相对于 roadmap"的分辨率完备/最优，roadmap 未覆盖的构型永远找不到。
7. **单线程足够**：结论建立在"向量化收益 ≫ 多线程通信开销"之上；若换到核数更多、单核 SIMD 更窄的硬件，这个 trade-off 需要重测。
8. **同步执行可行**：真机演示不含接触与闭环策略，控制器延迟极小，因此不需要 TPG；一旦有接触/学习策略，必须回到 TPG 路径。

---

## 7 · 与相关工作对比

| 工作 | 加速对象 | 并行载体 | 多臂支持 | 运行时灵活性 | 相对 VAMP-MR 的位置 |
|---|---|---|---|---|---|
| **FCL [2] / Bullet [3]** | 通用碰撞库 | 单线程、BVH 递归遍历 | 需外部拼装 | 高（通用） | 被替代的基线；同级球体化下慢 11–148x |
| **VAMP [1]** | 单臂 FK+CC 融合内核 | CPU SIMD（SoA） | ❌ 每内核固定单机器人 | 需重编译 | 本文的直接前身；本文补上多臂、三类检查分离、运行时配置 |
| **GPU / FPGA 碰撞检测 [16, 20]** | CC 本体 | GPU / FPGA | 视实现 | 低 | 设备通信开销可抵消加速；本文坚持单核 SIMD 零传输 |
| **CBS-MP [10]** | 两级搜索算法 | — | ✅ | — | 算法被保留，本文只换其 CC 后端（并修了原约束的不完备性） |
| **DTS [5]** | 捷径化策略选择（多臂 bandit） | — | ✅ | — | 算法被保留，本文只换其 CC 后端 → 50x 收敛加速 |
| **APEX-MR [18]** | 多模态 TPG 安全执行 | CPU 多线程（16 线程） | ✅ | — | 框架被保留，本文单线程快 6.9–21x，并用分组策略适配早停 |
| **RoboBallet [15]** | 学习式集中控制 | 神经网络 | ✅ | — | 互补：本文的向量化也能加速其 feature/reward 评估 |
| **LazyPRM [21] / 经验复用 [11,12] / 学习式检测器 [22,23] / MPNet [24]** | 减少 CC 调用次数 | 算法/学习 | 视情况 | — | **正交**：本文减少每次 CC 的成本，这些减少 CC 的次数，可叠加 |

**面试 Tip**：被问到"为什么不用 GPU 而用 CPU SIMD？"——标准答法分三层：(1) 碰撞检测是低算术强度、分支密集、访存不规则的工作负载（BVH 递归），GPU 的宽 SIMT 很难吃满；(2) 规划器本身跑在 CPU 上，offload 到 GPU 意味着每次可行性查询都要一次 host-device 往返，累积延迟会吃掉加速；(3) 单核 SIMD 把 FK+CC 融合成一个 header 内核，batch 内 8 个配置天然对齐 AVX2 lane，零通信开销——所以"更笨的并行"在这里反而更快。再补一句 trade-off：选 AVX2 不选 AVX-512，是因为 512-bit 会因功耗散热降频。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-24)

**repo 信号核验**：论文正文逐字给出 "Code is available at **https://vamp-mr.github.io/vamp-mr**"。这是 `github.io` 项目页，**不是 `github.com` 仓库直链**，且全文未出现任何 `github.com` URL、commit hash 或 issue 编号。因此本节按规则**不做 issue 级实证**，以下 3 条 pitfall 全部由 §6 失败模式 + §1/§2 的方法约束**机械推导**，未经 issue 验证。

1. **早停语义 vs 碰撞计数需求**（源自 §6 "只能答是否碰" + §1.2 "整批拒绝"）
   - 失效场景：把 `FK_CC_Multi` 直接接到 CBS 的冲突选择或原始 TPG 的逐对依赖构造上。
   - 机制链条：`FK_CC_Multi` 的返回是**全称量化**的 `Valid/Invalid`（Alg.1 第 18 行注释："all v composite configurations in the batch are collision-free"）→ 它在第一个碰撞 lane 就 return Invalid → 下游拿到的是"存在碰撞"而非"碰撞集合"。
   - 工程后果：CBS 无法在多个冲突中挑选，TPG 无法确定该加哪条边。
   - 规避：像论文那样改用 **transit node 分组**（只问"两段路径是否相交"），或对需要计数的查询绕开早停、逐 lane 取结果。

2. **球体化近似的双向陷阱**（源自 §6 "球体近似是有损的" + §5 "FCL 基线用原始 mesh 反而更快"）
   - 失效场景 A：拿 mesh 直接喂 VAMP-MR——内核只接受球体表示，必须先跑 [27] 的工具做球体分解。
   - 失效场景 B：为了让球体"更贴合"而缩小半径 → 不再外切 → **静默漏检**，安全检查失效。
   - 机制链条：碰撞判据是 `‖p_a − p_b‖ ≥ r_a + r_b`（§2 Napkin Formula），保守性完全由"球是否包住几何"决定，代码层面无法检测你是否违反了这个前提。
   - 工程后果：漏检不报错、不崩溃，只是偶尔撞上。
   - 规避：球体化后做一次 mesh-vs-sphere 的包含性抽查；论文自己给的参照是每台 Panda **59 球**。

3. **AVX2 编译契约 + 障碍缓存失效**（源自 §4 "`-march=native -mavx2 -O3`、batch=8" + §1.2 "缓存机器人系障碍"）
   - 失效场景 A：在未开 `-mavx2` 的构建、或非 x86 平台上编译/部署；论文未报告任何标量回退路径的性能。
   - 失效场景 B：规划过程中基座被重标定或障碍被移动，但代码沿用了缓存的 `^iO = (^wT_i)^{-1} ∘ ^wO`。
   - 机制链条：batch size 8 是**编译期**由 256-bit / 32-bit 决定的（论文明确 "giving a SIMD batch size of 8"），lane 数与 rake 分辨率耦合；障碍缓存的前提是"base transforms and obstacles often remain fixed during planning"——这是**often**，不是 always。
   - 工程后果：A 退化为慢速路径或编译失败；B 产生基于过期几何的"无碰撞"判定。
   - 规避：把 `^wT_i` / `^wO` 的每次变更显式 invalidate 缓存；在 CI 里固定编译 flag 并断言 `sizeof(batch)==8`。

> 说明：截至 2026-10-24，未从论文全文获取到 `github.com` 仓库地址与社区 issue 流，故本节不含任何 issue 编号、标题或引文。

---

[← Back to 多机器人 / 运动规划 README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2607.13478v1 全文（HTML 截断版）· 未在真机复现的数字标 `UNVERIFIED`。本文所有性能数字均逐字取自论文 Table I / II / III、Fig. 1 / 4 / 5 与 Sec. V 正文；论文未报告的项目已显式标注「论文未报告」。

[//]: # "<!-- source: https://arxiv.org/abs/2607.13478 -->"
