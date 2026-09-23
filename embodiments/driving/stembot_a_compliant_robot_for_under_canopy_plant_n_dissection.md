<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: RGBD
paradigm: geometric
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# STEMbot：用于冠层下植物导航的柔性攀爬机器人 (STEMbot: A Compliant Robot for Under-Canopy Plant Navigation)

> **发布时间**：2026-07-08（arXiv:2607.07873v1 [cs.RO]）
> **论文 / 模型名**：STEMbot（University of Michigan, Robotics Dept.；Charlick, Choudhury, Ma, Huang, Berenson）
> **核心定位**：首个把**完整感知栈 + 几何 SLAM + 全局流形约束规划**集成到一台**可爬 7–33 mm 细茎、能做枝干切换、可倒挂**的毫米级攀爬机器人上，实现冠层下自主导航——直接对标只能做局部反应式步进的 Treebot。

导语：农业虫害早期检测的痛点是——很多害虫藏在叶背或茎干上，从远处（无人机/地面车）只能在造成可见损害后才被检出；而现有攀爬机器人要么只上工业表面、要么只能抱住无分支的树干、要么没有板载感知只能做局部反应式爬行。STEMbot 用深度几何 PIN-SLAM 绕开植物"重复纹理 + 单色调"导致的外观匹配失效，用语义 OcTree + 流形约束 A* 实现了有规划的冠层内自主导航。

---

**X-Ray 开场**：它解决的问题是——在视觉高度同质、几何却复杂的植物茎干上，如何同时做**鲁棒定位、语义建图、和枝干级别的路径规划**。它提出的方案是：硬件上做柔性高摩擦轮 + 弹簧四连杆夹持；感知上用 **PIN-SLAM（纯几何、不依赖光度一致性）** 替代特征/直接法视觉 SLAM；建图上用 SAM+CLIP 打语义标签灌进贝叶斯 OcTree；规划上把植物形态抽象成**可通行体素流形**，用**最近邻投影**把 A* 的离散动作拉回枝干表面。对 spatial AI 研究者而言，它的意义是给了一个**"几何 SLAM 在低纹理自然场景里反杀外观 SLAM"** 的实证案例，以及一个**把连续流形约束离散化成体素 + A\*** 的工程范式。

---

## 📍 研究全景时间线

```
1990s-2000s          2012             2016-2023          2023               2026
工业爬壁机器人  →   Treebot [6]   →  DSO[12]/DROID-  →  PIN-SLAM[15]   →  STEMbot
(RiSE[7] 磁/真空/   600g 连续体，      SLAM[13]/VGGT-     (弹性神经点锚   (PIN-SLAM+
 微刺，仅人造平面)   两爪针尖夹爪，     SLAM[14]           定局部 SDF，      SAM/CLIP +
                    280mm→118mm      视觉/光度 SLAM      深度几何特征)     流形约束 A*)
                    触觉反应式规划    (植物纹理上失效)                     ← 本文
      │                 │                 │                 │                │
  表面吸附          树干→枝过渡       外观匹配SLAM      深度几何SLAM    冠层下自主导航
  (非植物)          (无板载感知)      (感知混叠)        (局部 SDF)      + 枝干级全局规划
                                                                          │
                                   本文局限：① 假设刚性植物几何（靠选硬茎+绑枝实现）
                                             ② 仍需要 tether（供电+计算）
                                             ③ 语义用闭词表，无信息论探索
                                             ④ PIN-SLAM 需 10–15Hz，实测仅 5Hz
```

---

## 1 · 核心架构 / 方法总览

三大子系统：**Hardware（硬件）→ Perception（感知）→ Motion Planning（规划）**，控制层跑 PID。

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| 驱动 (Actuation) | 双对 Pololu 700:1 行星减速电机（Item No. 2359，扭矩 up to 900 g-cm） | 三个运动基元：垂直爬升 / 偏航旋转 / 俯仰调整 | 无学习；纯机械 + 开环动作 |
| 传感 (Sensing) | Intel RealSense Depth Module D401 + Adafruit VL6180X ToF | 立体深度 + 俯仰间接观测 | — |
| 底层控制 (PID) | ToF 距离反馈，目标设定点 d_ToF | 俯仰/偏航速度指令（90 Hz） | 调参得 Kp=20, Kd=5, Ki=0.1，无学习 |
| 里程计 (Odometry) | D405 逐像素深度，30 Hz；每 8 帧抽 1 帧 | PIN-SLAM 位姿 | **零训练**；纯几何 SDF 注册 |
| 语义分割 (SAM) | 最新 RGB 帧（1 Hz） | 语义 mask | **冻结零样本**，无微调 |
| 语义分类 (CLIP) | SAM mask | 标签（p > 0.90 才用） | **冻结零样本**，闭词表 7 类 |
| 概率建图 (OcTree) | 语义点云 + PIN-SLAM 位姿 | 贝叶斯 log-odds 语义体素（1 Hz） | 在线贝叶斯更新，无学习 |
| 局部几何 (PCA) | "stem" 体素质心点云（k-d tree） | 表面法向 **n**、枝干朝向 **b** | 每次迭代重估，无学习 |
| 规划 (A*) | 初始状态 s₀、目标（point / visibility） | 动作基元序列 𝒜 | 重规划式（receding horizon），无学习 |

### 1.2 关键机制

**⚡ Eureka Moment：植物茎干是"局部圆柱流形 + 空间特征密集"的结构——所以放弃在植物上必然失效的光度/外观 SLAM，改用**纯深度几何的 PIN-SLAM**；再把整个连续流形规划问题**离散化成"最近可通行体素质心"上的 A\***，用一次最近邻投影就替代了昂贵的流形数值优化。**

拆解这个洞见的三层：
1. **反直觉点**：植物视觉单色调 + 重复纹理 → 特征法/直接法/SLAM 学方法全崩；但论文指出——茎干的**几何**非均匀且空间特征密集，因此深度几何法反而稳（不同于隧道/走廊那种几何退化场景）。
2. **工程折中**：PIN-SLAM 需 10–15 Hz 才在收敛域内，实测只能跑 5 Hz → 采用"**300 ms 运动 + 1 s 静止**"的不连续策略，把位姿同步和规划塞进静止窗口。
3. **规划简化**：不做流形上的连续优化（如投影采样 [25]），而是把植物形态抽象成离散语义体素网格，A* 的动作由 `p_{t+1} = p_t ± δ·b_t`（线性）或 `p_t ± δ·(b_t×n_t)`（角度）给出，再**投影回最近可通行体素质心**。

### 1.3 信息流架构图

```
        D401/D405 RGB-D (30Hz)                    ToF (VL6180X)
              │                                       │
    ┌─────────┴─────────┐                             │
    │                   │                             ▼
每8帧抽1帧          SAM (1Hz)                  PID 俯仰控制 (90Hz)
    │                   │                             │
PIN-SLAM里程计      CLIP 闭词表                    电机指令
 (3.75/5 Hz)       {leaves,trunk,sky,          (UP/DOWN/LEFT/RIGHT
    │              light,wall,curtain,          + 俯仰 + 偏航)
    │               grate}, p>0.90                    ▲
    │                   │                             │
    └──────┬────────────┘                             │
           ▼                                          │
   语义点云 → OcTree 贝叶斯 log-odds 更新 (1Hz)         │
           │        → softmax → {traversable,          │
           │                     non-traversable,     │
           │                     free-space}          │
           ▼                                          │
   "stem"体素质心点云 → k-d tree + PCA                 │
           │           → 法向 n (r_normal=0.005m)     │
           │           → 枝干 b (r_branch=0.14m)      │
           ▼                                          │
   ┌── 目标定义 ──┐                                   │
   │ state-based  │                                   │
   │ visibility   │← 径向光线投射 + Fibonacci 球采样    │
   └──────┬───────┘                                   │
          ▼                                           │
   流形约束 A* 搜索                                     │
   (分支切换约束 |m·b_{t+1}|<ε, b_t·b_{t+1}<γ)          │
          │                                           │
          ▼ 只派发第一个动作                            │
   Receding Horizon 重规划 ───────────────────────────┘
```

---

## 2 · 数学核心

### 📌 Napkin Formula

> **机器人状态 = {位置 p，表面法向 n，枝干朝向 b}；A\* 的动作在流形切平面上"直线走/绕柱转"，每一步再投影回最近的可通行体素质心。规划 = 在离散化流形上的多目标最短路径。**

### 2.1 状态与动作（离散状态空间）

**目标**：给初始状态 s₀ 和目标条件 G，找动作序列 𝒜 = {a₁,…,a_k}，使机器人到达某状态 s ∈ G 且**始终保持与可通行流形的连续接触**。

**状态**：s = {**p**, **n**, **b**}，其中 **p** ∈ ℝ³ 为最近可通行体素质心，**n** 为表面法向，**b** 为枝干朝向（约束为沿茎轴近端或远端）。**n** 与 **b** 共同定义一个局部平面的植物流形近似（ℝ³ 中的 2D 曲面）。

**转移函数** s_{t+1} = f(s_t, u)，u ∈ {UP, DOWN, LEFT, RIGHT}：

$$
\mathbf{p}_{t+1}=\begin{cases}
\mathbf{p}_{t}+\delta_{linear}\,\mathbf{b}_{t} & u=\text{UP}\\
\mathbf{p}_{t}-\delta_{linear}\,\mathbf{b}_{t} & u=\text{DOWN}\\
\mathbf{p}_{t}+\delta_{angular}\,(\mathbf{b}_{t}\times\mathbf{n}_{t}) & u=\text{LEFT}\\
\mathbf{p}_{t}-\delta_{angular}\,(\mathbf{b}_{t}\times\mathbf{n}_{t}) & u=\text{RIGHT}
\end{cases}
$$

**变量**：δ_linear = 线性步长（试验中 0.1 或 0.2 mm）；δ_angular = 角度步长（表中记为 0.1°，但公式里作为位移量使用，见 §3 单位注记）；**b**×**n** = 横向（周向）方向。

### 2.2 流形投影与朝向一致性

**目标**：直接套用上式会让机器人脱离茎干，必须拉回流形。

**机制**：每个候选位置查 k-d tree 找**最近的可通行体素质心**，后继状态继承该点预计算的 **n** 与 **b**。朝向一致性靠两个点积强制：

$$
\mathbf{n}_{t}\cdot\mathbf{n}_{t+1}>0,\qquad \mathbf{b}_{t}\cdot\mathbf{b}_{t+1}>0
$$

**直觉**：PCA 特征分解有符号歧义（特征向量的正负号可翻转），点积约束把翻转的向量掰回来，避免"不可能的翻转动作"。

### 2.3 碰撞检查

$$
d(\mathbf{p}_{t},\mathcal{P}_{obs})=\min_{\mathbf{q}\in\mathcal{P}_{obs}}\|\mathbf{p}_{t}-\mathbf{q}\|_{2}\ \ge\ r_{robot}
$$

**变量**：𝒫_obs = 障碍物体素（叶子、杂物）质心的 k-d tree；r_robot = 机器人半径。距离小于 r_robot 的状态被剪掉。

### 2.4 分支切换约束（本文特有的"对接几何"）

**目标**：只有满足 docking 几何的枝干切换才被接受。

**机制**：当 **b**_t · **b**_{t+1} < γ 时判定为潜在分支切换（γ = 0.995 为分支检测阈值）。定义横向向量 **m** = **b**_t × **n**_t，切换仅在满足下式时被接受：

$$
|\mathbf{m}\cdot\mathbf{b}_{t+1}|<\epsilon
$$

**变量**：ε = 0.40 为分支切换阈值。

**直觉**：要求后继朝向 **b**_{t+1} 大致落在当前状态定义的平面内，剪掉需要"非物理侧向机动"的茎间过渡。若 **b**_{t+1} 落在当前 (b_t, n_t) 平面内，则违反 docking 几何 → 剪掉。

### 2.5 代价与启发式

$$
g(s_{t+1})=g(s_{t})+\|\mathbf{p}_{t+1}-\mathbf{p}_{t}\|_{2}
$$

$$
h(s)=\min_{s_g\in S_{\text{goals}}}\Big(\|\mathbf{p}-\mathbf{p}_{g}\|_{2}+W_{\theta}\arccos(\mathbf{b}\cdot\mathbf{b}_{g})\Big)
$$

**变量**：W_θ = 1.0（角度误差权重）；S_goals = 单元素（state 目标）或多元素（visibility 目标）。启发式 = 空间距离 + 朝向对齐误差，可容忍（admissible 视 W_θ 而定）。

### 2.6 目标条件

$$
\|\mathbf{p}-\mathbf{p}_{g}\|_{2}\le d_{goal},\quad \mathbf{n}\cdot\mathbf{n}_{g}>0,\quad \mathbf{b}\cdot\mathbf{b}_{g}>0
$$

**变量**：d_goal = 0.01 m。后两项保证机器人**在枝干的正确一侧**、**朝向正确方向**。

**Visibility 目标生成**：从目标点做径向光线投射 + Fibonacci 球采样；每条"先命中茎干后命中障碍"的射线贡献 **4 个候选状态**（法向/朝向方向的 4 种组合）；用固定机器-相机变换检查可见性，合法状态入 S_goals，规划变成多目标搜索。

---

## 3 · 带数字走一遍（玩具例子，低维）

**设定（玩具，非论文实测）**：茎干建模为沿 z 轴、半径 r = 8 mm 的圆柱。机器人初始 p₀ = (8, 0, 0)，法向 **n**₀ = (1, 0, 0)（径向朝外），枝干朝向 **b**₀ = (0, 0, 1)（沿茎向上）。横向向量 **m** = **b**₀ × **n**₀ = (0, 0, 1)×(1, 0, 0) = **(0, 1, 0)**。取 δ_linear = 0.1 mm。

**动作 UP**：
$$
\mathbf{p}_1 = (8,0,0) + 0.1\,(0,0,1) = (8,0,0.1)
$$
半径仍为 8 mm → 完美落在圆柱上，**无需投影**。

**动作 LEFT**（把角度步长按弧长 ℓ = 0.1 mm 处理）：
$$
\mathbf{p}_1' = (8,0,0) + 0.1\,(0,1,0) = (8,\ 0.1,\ 0)
$$
半径 = √(8² + 0.1²) = √64.01 ≈ **8.000625 mm** → **偏离圆柱 0.000625 mm**。

**流形投影**：查最近的可通行体素质心，把它拉回圆柱：
$$
\theta' = \arctan(0.1/8) = 0.0125\ \text{rad},\quad \mathbf{p}_1'' = (8\cos\theta',\,8\sin\theta',\,0) \approx (7.99938,\ 0.09999,\ 0)
$$
半径回到 8 mm，状态继承该点的 **n**、**b**。

**读数**：本例偏差极小（0.6 μm），但论文的 δ_angular = 0.1° 与 δ_linear = 0.1 mm 在**量纲上并不自洽**（表中角度步长以度为单位，式 (1) 却当作位移量使用）——若把 0.1° 理解成绕轴的角增量，那么 8 mm 半径上的弧长仅 8 × 0.1 × π/180 ≈ **0.014 mm**，比线性步长 0.1 mm 小一个量级。**这属于论文参数表的量纲歧义，UNVERIFIED**，但如果 LEFT/RIGHT 的周向步长真的比 UP/DOWN 小 7 倍，那么机器人"绕柱转一圈"需要的步数会远多于"直着爬一段"，A* 的周向搜索深度会显著膨胀——这直接影响 §4 的重规划频率预算。

**若在流形突然中断处（如被叶子遮挡导致的可通行体素缺失）**：最近邻投影会跳到"下一个存在的质心"，可能跨过一段物理上无法到达的间隙 → 状态瞬移，A* 以为可达、实机掉线。这正是 §8 推导的 pitfall 之一。

---

## 4 · 工程视角

**硬件 / 计算约束（论文报告）**：

| 项目 | 值 | 来源 |
|---|---|---|
| 无缆质量 (untethered mass) | 67 g | §III-A1 |
| 电机 | Pololu 700:1 亚微型行星减速（Item No. 2359），扭矩 up to 900 g-cm | §III-A1 |
| 轮材 | EcoFlex 00-45 硅胶（Shore 硬度 00–45），铸模 | §III-A1 |
| 主计算 | NVIDIA RTX 4080 GPU（**离线/有线**） | §III |
| 底层控制 | Arduino Nano | §III |
| 供能 / 计算 | **有线 tether** | §III |
| 传感器 | RealSense D401（硬件章节）/ D405（感知章节）+ VL6180X ToF | §III-A2 / §III-B |

**速率预算（论文报告）**：

| 环节 | 频率 | 备注 |
|---|---|---|
| PID 俯仰控制 | 90 Hz | Kp=20, Kd=5, Ki=0.1 |
| 逐像素深度 | 30 Hz | D405 |
| PIN-SLAM 里程计 | **3.75 Hz**（每 8 帧抽 1 帧；文中另处写"Operating at 5 Hz on an RTX 4080"） | 两处数值不一致，原文如此 |
| PIN-SLAM 收敛域要求 | 10–15 Hz | 实测不足 → 被迫不连续 |
| 全局地图更新 | 1 Hz | SAM → CLIP → OcTree |
| 运动占空比 | 300 ms 运动 / 1 s 静止 → ≈ 23% | 由论文数字推导 |

**核心 trade-off**：
- **速度 vs 定位**：PIN-SLAM 需要 10–15 Hz 才留在收敛域内，实机只能 5 Hz，于是用"走 300 ms、停 1 s"来换取位姿同步和规划时间——**移动速度被硬性钉死在约 23% 占空比**。想提速 → 直接触发 tracking loss（§IV-3 明说"moved too quickly relative to the PIN-SLAM update frequency"）。
- **精度 vs 泛化**：选用 PIN-SLAM 的代价是必须靠深度质量；D401 近距离更准，所以茂密冠层（Dracaena、Ficus lyrata，背景像素少）反而 tracking-loss 更少，**稀疏植物反而更难**。
- **有线束缚**：RTX 4080 + tether 意味着"自主"只是**局部自主**，外场部署不可行。

**未报告项（论文未报告，不填数字）**：
- 规划延迟（单次 A* 耗时）：论文未报告
- 峰值显存 / VRAM：论文未报告
- 端到端单次实验时长、轨迹长度：论文未报告
- 电机实测能耗：论文未报告
- 机器人尺寸（除质量与爬行茎径外）：论文未报告

---

## 5 · 数据与评测

**测试对象（论文原文明确列出）**：
- **4 个植物样本**：2 个活的（*Monstera deliciosa*、*Ficus lyrata*），2 个人造的（*Dracaena*、*Olea europaea*）。
- **机械极限基准**：3D 打印 PLA 几何 + 常见圆柱体，隔离三个变量——茎径、分叉角、曲率半径。

**机械遍历能力（论文报告）**：
| 能力 | 值 |
|---|---|
| 可爬茎径范围 | **7 mm（Bic Round Stic 笔）到 33 mm（白板框架）** |
| 分支切换角 | 16 mm PLA 茎上 **up to 90°** |
| 曲率半径 | 20 mm PLA 枝上 **as tight as 50 mm** |
| 倒挂接触 | 支持（inverted） |

**建图 Ground Truth（论文报告）**：
- 离线摄影测量（photogrammetry）流程：**4K 手持视频** → **Agisoft Metashape（Standard Edition, Version 2.3）** → 密集点云 → 用物理测量缩放 → 在 **CloudCompare（2.14.beta）** 手工标注与精修。

**评测指标（论文报告）**：
- **单向 Chamfer 距离（one-way Chamfer distance）**：重建的每个点到 GT 最近邻的**平方 L₂ 距离**（论文原文定义为平方 L₂，但报告值单位为 mm）。

**结果数字（逐字照抄）**：
| 样本类型 | 平均单向 Chamfer 距离 |
|---|---|
| 人造样本（Experiment 1 & 4） | **3.85 mm** |
| 活体样本（Experiment 2 & 3） | **13.36 mm** |
| 活体上 "Traversable" 语义类 | **37.56 mm** |
| 摘要综述口径 | **average Chamfer distance of less than 1 cm** |

**评测条件说明（关键）**：
- 误差来源被明确归因于：**活体组织的非刚性** + **ground truth 扫描与机器人测试之间的植物生长/形变**（违反静态环境假设）；以及 **Monstera 主枝被误分类**（低色彩对比导致语义分割困难）。
- **实验时关掉了顶灯**（"we turned off overhead lights for cleaner readings"）——即评测环境是**受控光照**，不是真实田间的直射阳光。
- 用 **trellising（绑枝）** 强制 Monstera 保持刚性——即"刚性假设"是被**主动制造条件**满足的，而非植物天然满足。

---

## 6 · 能力与失败模式

### 能做
- 在 **7–33 mm** 茎径上爬升；**up to 90°** 分叉；**50 mm** 曲率半径的弯曲枝；倒挂。
- 在 4 个植物样本上做**自主导航**（state-based 与 visibility-constrained 两种目标）。
- 生成**毫米级语义重建**（人造 3.85 mm）。
- **visibility 目标**：让机器人换位到能看见被遮挡目标的状态（如 Olea europaea 需先重定向满足 docking 约束再换枝）。
- 闭环 receding-horizon 重规划，每次只派发第一个动作，用新 PIN-SLAM 位姿补偿漂移。

### 不能做（论文自陈的 failure modes）
1. **深度相机误差 / 噪声**：强光、尤其直射阳光是 RGB-D 已知难题；**测试时关了顶灯**才能干净读。
2. **PIN-SLAM tracking loss**：深度误差造成 scan 不一致 → 丢跟踪；或机器人相对 PIN-SLAM 更新频率**移动过快** → 丢跟踪，之后相机位姿误差污染地图。
3. **硬件运动失败**：Olea europaea / Ficus lyrata 上的**凸起结节需要超出电机能力的扭矩**；茎干卡进底盘与硅胶轮之间 → 失去牵引力；**ToF 传感器被叶子遮挡或检测到木节** → 俯仰过度/不足修正 → 失去接触。
4. **无信息论探索**：visibility 目标只保证"到达能看见目标的状态"，**不推理哪块区域最值得探索**。
5. **刚性假设**：规划假设植物几何刚性；真实植物会弯会晃。

### 隐含假设 (Hidden Assumptions)
- **静态环境**（§III-C2 假设 1）：植物几何在规划/执行周期内固定——这被 §IV-2 的数据直接反驳（活体误差归因于植物生长与形变）。
- **局部圆柱流形**（§III-C2 假设 2）：机器人足迹内茎干建模为圆柱，局部构型空间被降为 2 自由度（纵向平移 + 周向旋转）。对**非圆柱、有锥度/椭圆截面**的真实茎干不成立。
- **PID 保证 b 与机器人朝向对齐**（§III-C2 假设 3）：把"朝向对齐"这一关键前提交给一个**只测 ToF 距离的 PID**——ToF 一旦被叶子遮挡或打到木节就失效。
- **闭词表语义**：CLIP 只对 `{leaves, trunk, sky, light, wall, curtain, grate}` 7 类分类，且只有 p > 0.90 的 trunk/leaves 才进地图。**词汇表外的任何东西（花、果实、土壤、虫体、温室网）都无法被正确建模**。
- **几何非退化**：假设茎干的"intricate and non-uniform morphology"提供足够空间特征；对**近乎直的光滑细杆**（如 7 mm 笔）几何特征变稀，PCA 的 n、b 估计会退化——但论文未在此极限下报告精度。
- **地面重建即真值**：用摄影测量点云作为 GT，假设 4K 视频 + Agisoft + 手工精修的精度高于机器人重建；对细茎（7–33 mm）本身的重建误差有多大，论文未报告。
- **静态地图 = 静态语义**：OcTree 用 log-odds 累积，隐含假设"标签一旦写入就大致正确"，**没有显式回环纠正后的语义地图清理机制**。

---

## 7 · 与相关工作对比

| 维度 | Treebot [6] | Branch Bot [10] | Amaran [8]/Climbot [9] | 工业爬壁 (RiSE [7] 等) | **STEMbot（本文）** |
|---|---|---|---|---|---|
| 质量 | 600 g | 未报告 | 未报告 | 未报告 | **67 g（无缆）** |
| 最小可爬茎径 | 枝 ≥ **118 mm** | 杆状单段 | 均匀杆 | 人造平面 | **7 mm** |
| 树干→枝过渡 | ✅（280 mm→118 mm，触觉反应式） | ❌（单段） | ❌ / 受限 | ❌ | ✅（**up to 90°**） |
| 板载感知/里程计 | ❌（无 onboard vision/odometry） | ❌（有线） | 部分 | ❌ | ✅ PIN-SLAM + SAM/CLIP + OcTree |
| 全局规划 | ❌（仅局部反应式） | ❌ | ❌ | ❌ | ✅ 流形约束 A* + receding horizon |
| 抓握原理 | 针尖爪（**有伤树皮风险**） | 被动弹性夹持 | 抱紧/包绕 | 磁/真空/微刺 | 高摩擦柔性硅胶轮（**不伤茎**） |
| SLAM 技术路线 | — | — | — | — | **纯几何 PIN-SLAM（非光度/特征）** |

| SLAM 路线 | 代表 | 在植物上的问题 |
|---|---|---|
| 特征法 | [11] | 重复纹理 + 单色调 → 感知混叠，特征匹配失败 |
| 直接法 | DSO [12] | 依赖光度一致性，植物表面无区分度 |
| 学习法 | DROID-SLAM [13]、VGGT-SLAM [14] | 在近距茎干遍历的极端视角/尺度变化下退化 |
| **几何法** | **PIN-SLAM [15]** | **用深度几何特征 + 弹性神经点锚定局部 SDF，不要求光度一致性 → 本文选用** |

| 建图路线 | 代表 | STEMbot 的用法 |
|---|---|---|
| 2D/3D 占据栅格 | [16] | 3D 体素内存开销过大 |
| 分层细分 | OctoMap [17] | 动态分配分辨率 |
| 语义贝叶斯 | [18,19] | 用 log-odds 向量 + softmax 维护类别分布 |
| 基础模型 | SAM [20]、CLIP [21]、DINOv3 [22]、Florence-2 [23] | 本文用 SAM+CLIP 冻结点，**未用 DINOv3/Florence-2** |

| 流形规划 | 代表 | 差异 |
|---|---|---|
| 投影采样 | [25] | 数值优化拉回约束面 → 昂贵 |
| 流形采样近似构型空间 | [26] | 近似合法构型空间 |
| 状态格 + 动作基元 A* | [27,28] | 本文采用 |
| **本文** | — | **不做数值优化，直接最近邻投影到可通行体素质心** |

**🎯 面试 Tip**：被问到"STEMbot 和 Treebot 的核心区别是什么"——答：**Treebot 是"能爬上树的反应式机器人"（无板载视觉、无里程计、只能局部步进、针尖爪有伤树皮风险），STEMbot 是"能在树里做规划的自主系统"（PIN-SLAM 全程定位 + 语义 OcTree 全局地图 + 流形约束 A* 全局规划 + 柔性轮不伤茎）**；再补一句"STEMbot 的边界是刚性假设 + 有线 + 闭词表，所以它验证的是'感知规划栈在冠层下可行'，不是'田间可部署'"。

---

## 8 · GitHub-validated pitfalls（atlas 联动, 2026-09-23）

**Repo 状态核查**：论文全文（arXiv:2607.07873v1）**未给出任何 github.com 链接**；页眉出现的 "Report GitHub Issue / Submit in GitHub" 是 arXiv 页面 UI 元素、**不是论文的代码仓库链接**。因此：**官方 repo 未在论文中给出，以下 pitfall 由 §6 失败模式 + §III 方法约束推导（未经 issue 验证）**。

**Pitfall 1 · 语义地图随植物形变而"陈旧"，A\* 沿过期流形规划**
- **失败模式依据**（§6/§IV-2）：活体样本误差 13.36 mm，归因于"非刚性组织 + 基线扫描与实验间植物生长"，且 §III-C2 假设 1 明文假设静态环境。
- **方法约束依据**（§III-C2 假设 1 + §III-C7 分支切换阈值）：A* 的转移/碰撞/分支约束全部建立在 OcTree 里**当时那一版**可通行体素质心上，一旦植物弯了 1 cm 量级，投影到的质心与真实茎面错位，就可能产生**违反 docking 几何却仍被接受的切换**（因为 |**m**·**b**_{t+1}|<ε 是在旧 **m**、旧 **b** 上算的）。
- **实机症状**：规划器持续输出"看起来可行"的路径，但机器人在枝干交界处打滑/掉线，且重新规划也无法恢复（地图本身没更新）。
- **规避**：给 OcTree 加时间衰减或体素新鲜度权重；在 r_branch 邻域内做在线形变检测，一旦偏差超阈值就局部重置该区域体素。

**Pitfall 2 · PIN-SLAM 被迫运行在收敛域之下，运动占空比 ≈23% 是硬天花板**
- **失败模式依据**（§IV-3）："PIN-SLAM is prone to tracking loss... if the robot moves too quickly relative to the PIN-SLAM update frequency."
- **方法约束依据**（§III-B1 + §III-B）：PIN-SLAM "requires an update rate of 10–15 Hz"，实测 "Operating at 5 Hz on an RTX 4080"，于是被迫用 "300 ms of motion is followed by a 1 s stationary interval"。
- **工程后果**：任何"让机器人爬快点"的改动 = 直接进入 tracking loss 区间；且 30 Hz 深度流被抽成 3.75 Hz（每 8 帧 1 帧）意味着**深度信息时间分辨率被主动牺牲**，快速运动时帧间重叠不足。
- **规避**：要么上更强/量化更低的硬件把 PIN-SLAM 拉到 10–15 Hz，要么改用增量式（如 iNeRF/连续时间）里程计；单纯降 δ_l 提高步数会加剧 A* 深度与重规划开销。

**Pitfall 3 · 闭词表 CLIP + 低对比度 → 主枝误分类，直接毁掉 37.56 mm 的遍历精度**
- **失败模式依据**（§IV-2）："the 'Traversable' semantic class on real plants averaged an error of 37.56 mm, due in large part to the incorrect semantic classification of a primary branch on the Monstera"；"Segmentation of this specimen is particularly challenging due to low color contrast."
- **方法约束依据**（§III-B2）：CLIP 只对 `{leaves, trunk, sky, light, wall, curtain, grate}` 7 类闭词表分类，阈值 p > 0.90，5 个非植物类只是用来"滤掉无关点"。
- **机械后果**：一旦主枝被误标成 non-traversable，碰撞检查会把整根枝条剪掉，规划器**绕远路或干脆找不到目标**；反之若叶子被误标成 trunk，`d(p,P_obs) ≥ r_robot` 会失效 → 机器人朝叶子撞。
- **规避**：把 CLIP 换成开放词表 + 多帧投票；对 trunk/leaves 用几何先验（细长/面状）交叉验证；对 p 在 [0.5, 0.9] 的模糊体素打"未定"标签而非硬二值。

**Pitfall 4 · 最近邻投影在"被遮挡导致的体素空洞"处会瞬移**
- **失败模式依据**（§IV-3）：PIN-SLAM tracking loss 后"camera-pose errors introduce map defects"；ToF 被叶子遮挡也会导致地图缺测。
- **方法约束依据**（§III-C5）：投影是"querying the k-d tree for the nearest traversable voxel centroid"，**没有最大投影距离门槛**（不像 §III-C6 的碰撞检查有 r_robot 阈值）。
- **实机症状**：当期望的下一体素因遮挡缺失时，最近邻会跳到空洞另一侧的质心，状态**跨越物理上不可达的间隙**，A* 认为路径存在，机器人却到不了。
- **规避**：给投影加一个 `max_projection_distance` 门槛（超过就判定局部地图不可信、触发重新观测该区域），并在 OcTree 里对"从未被观测"的体素与"曾观测但被移除"的体素区分对待。

---

[← Back to Robotics Navigation README](./README.md)
> **Status**：v0.1 · 基于 arXiv:2607.07873v1 全文 · 未在真机复现的数字标 `UNVERIFIED`（如 §3 的量纲解读）· 论文未报告项已显式标注「论文未报告」

<!-- source: https://arxiv.org/abs/2607.07873 -->
