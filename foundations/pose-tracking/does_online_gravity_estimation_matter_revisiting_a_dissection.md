<!-- ontology-5axis
problem: VIO
representation: n/a
sensor: multi-modal
paradigm: geometric
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# 在线重力估计真的必要吗？重审 LiDAR-Inertial Odometry 中的一个"沉默设计分歧" (Does Online Gravity Estimation Matter? Revisiting a Silent Design Split in LiDAR-Inertial Odometry)

> **发布时间**：2026-09-16（arXiv:2609.13675v2 [cs.RO]）
> **论文 / 模型名**：rethink-lio-gravity（FAST-LIO2 / LIO-SAM 状态消融研究，非新估计器）
> **核心定位**：把"LIO 初始化后是否继续在线估计重力"这个被 baseline 精度比较掩盖的设计分歧，第一次做成**同系统、编译期真状态移除**的受控消融；结论是持续 LiDAR correction 下两种设计**平均实用等价**（±2% 内），代价只在 correction 缺失/动态起步时出现，而省下的 runtime 可忽略——**默认应保留 g 与 b_a 在线**。

FAST-LIO2 把重力方向放在 $S^2$ 上在线估计，LIO-SAM 却在初始化后把它固定，Lightning-LM 更激进地把滤波器从 23D 砍到 12D。跨系统比轨迹误差永远说不清谁对——因为前端、地图、轨迹模型、参数全都在变。本文换了个问题：**只在同一份代码里把状态真删掉，看 pose 会不会变差。**

---

**X-Ray（非专家 3 句复述）**：它问的是"LIO 初始化后还要不要继续估重力"，做法是在 FAST-LIO2 与 LIO-SAM 内部编译出 4 种状态维数（23D/21D/20D/18D）并保持其余完全一致。答案是：只要 LiDAR 校正持续到来，估不估重力在 12 条序列上平均只差 ±2%（中位绝对差 0.017 m / 0.014 m），**但一旦 LiDAR 中断 3 秒，固定重力会让车载 3D 误差成倍上升**，而省掉的算力只占核心耗时的 0.06%。对 spatial AI 研究者的意义：**状态可观性结论 ≠ 状态该不该保留**，且"加个同 IMU 重力方向因子来压 z 漂移"是错的——论文里它能把残差压小却让轨迹更差。

---

## 📍 研究全景时间线

坐标轴按被引方法在 LIO 演进中的角色排列（本文正文只给引用编号 [n]；具体年份为领域常识，**非本文数据**，标注为社区常识）。

```
LOAM 时代 ────────► 状态设计分裂 ────────► 本文要打的靶子 ────────► 本文
   [8]                 [3] vs [1,2]            [4] / [19,20,21]      2609.13675
   │                    │                       │                     │
edge/plane 配准    LIO-SAM[3]:           Lightning-LM[4]:       真·编译期状态移除
奠定 scan-match    初始化重力对齐帧,    23D→12D,移除 b_a,     ×2 系统 ×4 配置
范式               无在线方向状态        g, extrinsics          + 同 IMU 方向因子
                   FAST-LIO[5]/              │                  + 匹配 dropout switch
                   FAST-LIO2[1,6]:      [19] 重力约束配准
                   S² 上在线估计重力    [20,21] radar-LiDAR/leg
                   Point-LIO[2] 沿用     软 S² 重力先验
                   VE-LIOM[7] 优化框架   （都是"加信息/加残差",
                   在线重力              与"固定状态"是两件事）
                         │                     │                     │
                   可观性分析 [13,14,15] 初始化器 [16] 联合在线标定 [17]
                   退化检测 [23,24] 不确定度感知 benchmark [25]
```

**本文在演进中的位置**：它不是新估计器，而是第一次在**同系统内做真状态移除**的对照实验，把"可观性/初始化"这条理论线接到"部署时该保留哪些状态"这条工程线上。

**本文局限（作者自陈 + 结构约束）**：
- 主结论只覆盖 **FAST-LIO2 的 12 条名义序列**；LIO-SAM 的 4 序列消融明确是 **descriptive（描述性）**，不做 pooled inference、不establish等价。
- dropout 用**删除 LiDAR 消息**模拟，不建模前端 rejection 或 update delay；几何退化用固定几何裁剪（20 m / ±60°），作者自称 "fixed geometric controls, not calibrated models of sensor failure"。
- "Two dropout and two initialization trajectories cannot establish universal thresholds."
- 方向因子只测了**同一 IMU** 的 AHRS 方向残差；独立重力传感、contact/radar 信息、全局 loop-closure PGO 先验**全在声明之外**。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练-推理差异 / 关键差异 |
|---|---|---|---|
| FAST-LIO2 前端（scan matching，ikd-tree） | deskewed 点云 + 传播的预测位姿 | point-to-plane 残差 → EKF 更新 | **无训练阶段**；全在线迭代误差状态滤波。占核心耗时 **88.2%** |
| 状态流形（编译期固定） | 初始化量 + 上一时刻状态 | 23D/21D/20D/18D 状态与协方差 | 四种配置是**四个可执行文件**，前端/地图/标定/初始化/参数完全一致；runtime 无法切换 |
| LIO-SAM 增量图（因子图） | IMU 预积分 + LiDAR 因子 (+ 方向因子) | 增量 IMU–LiDAR 图位姿 | 4 配置：FG–BA（原生：固定 g、估 b_a）、FG–B0（再去 b_a 及其随机游走）、GE–BA / GE–B0（加共享 2D 定模在线重力方向） |
| 方向因子（same-IMU direction factor） | 最新 AHRS 四元数给出的 body-frame down $\mathbf{d}_k^{AHRS}$；$\mathbf{R}_k^\top\hat{\mathbf{g}}$ | GTSAM 双分量 Unit3 方向残差 | 协方差 $\sigma_d\in\{0.5^\circ,2^\circ,5^\circ\}$ 是**受控权重**，不是声称 AHRS 误差独立 |
| 匹配开关（matched 23D→21D switch） | 在线均值处的 g + 条件化协方差 | 21D 误差子空间继续传播 | 与独立初始化 FixG 不同：切换前 clean/dropout 两跑**逐位相同**，只有不确定性变化 |

**状态维数账本**（FAST-LIO2，online extrinsics 在所有配置中关闭）：
$d = 3_{\mathbf{p}} + 3_{\mathbf{R}} + 6_{\text{ext}} + 3_{\mathbf{v}} + 3_{\mathbf{b}_g} + 3_{\mathbf{b}_a} + 2_{\mathbf{g}} = 23$

| 配置 | 维数 | 固定量 | 说明 |
|---|---|---|---|
| Online | **23D** | — | 基线，g 与 b_a 均在线 |
| FixG | **21D** | g | 移除重力状态 |
| FixBa | **20D** | b_a | 移除加计零偏 |
| FixG+Ba | **18D** | g, b_a | 最激进 |
| 23D proxy（对照） | 23D | — | **只把修正置零、不改流形**——它保留协方差块与对 Kalman 增益的影响，因此只能检验"修正置零"的有效性，**不能**检验状态移除 |

### 1.2 关键机制

**⚡ Eureka Moment：把"要不要在线估重力"从"精度问题"重新定义为"观测条件问题"——持续 LiDAR correction 会让重力状态的游走被反复吸收，此时估与不估平均等价；真正的代价藏在 correction 消失后的恢复段和动态起步段，而状态维数削减带来的算力收益可忽略（可归因节省 **0.06%**）。所以"少几个弱可观状态"这个看似合理的工程直觉，在 LIO 里不成立。**

支撑这一洞见的三条机制细节：

1. **抑制修正 ≠ 移除状态**。作者用 23D proxy（置零修正）做对照，发现它给固定 b_a 的比较带来 **+7.3 pp** 偏差。因为被压制的坐标仍留在协方差里，并通过互相关影响保留变量——**用 runtime 开关近似状态移除会得到错误结论**。
2. **同 IMU 方向因子不是独立观测**。AHRS 与预积分用同一套 IMU 测量，因子既不观测 yaw、也不观测高度与垂直速度。
3. **状态维数不是 runtime**。FixG 让 filter algebra 降低 **7.5%**，但 filter algebra 只占核心时间 **0.83%**，scan matching 占 **88.2%** → 可归因节省 **0.06%**，whole-core 变化 **-11.6% 到 +3.1%**、跨零。

### 1.3 信息流 / 架构图

```
                 ┌──────────────────────────────────────────────┐
                 │  共享部分（所有配置逐位相同）                   │
                 │  IMU 数据 · 标定 · 初始化 · 地图 · 参数         │
                 └──────────────────────────────────────────────┘
                                     │
        IMU ──────────► 传播 (propagation)  ◄──── 状态流形（编译期选择）
                          δv̇ ≃ δg − R δb_a − R[a_m−b_a]× δθ
                                     │                    ▲
                                     │                    │ 只有这四个坐标
                                     ▼                    │ 在/不在状态里
                       ┌── 有 LiDAR 校正？ ──┐            │
                       │                     │            │
                   是  │                     │ 否（dropout）│
                       ▼                     ▼            │
        scan matching（88.2% 核心耗时）   纯惯性外推       │
        point-to-plane → EKF/因子图更新   误差 ~ ½ g sinε T²
                       │                     │            │
                       └────────► 位姿输出 ◄─┘            │
                                     │                    │
                     评估：RMSE_z（垂直位置 RMSE） + ATE（3D 位置 RMSE），
                     刚性 SE(3) 对齐，无 scale fitting
                                     │
                  ┌──────────────────┴───────────────────┐
                  │ 附加分支：same-IMU direction factor   │
                  │ r_d,k = B(d_k^AHRS)^T · R_k^T ĝ/‖ĝ‖  │
                  │ → 只约束 attitude，不测高度            │
                  └──────────────────────────────────────┘
```

---

## 2 · 数学核心

📌 **Napkin Formula（本质一行）**

$$\delta\dot{\mathbf{v}} \simeq \delta\mathbf{g} - \mathbf{R}\,\delta\mathbf{b}_a - \mathbf{R}[\mathbf{a}_m-\mathbf{b}_a]_\times \delta\boldsymbol{\theta}$$

> 重力误差与加计零偏误差在**速度通道里几乎同向**（都直接进 $\delta\dot{\mathbf{v}}$），只有姿态误差通过 $[\mathbf{a}_m-\mathbf{b}_a]_\times$ 把两者分开——所以**没有旋转激励就没有辨识**，这正是"估出来的 g 未必物理正确"的根源。

以及 outage 期间的位移代价：

$$\|\delta\mathbf{p}_g\| \approx \tfrac{1}{2}\,g\sin(\varepsilon)\,T^2$$

**目标 → 公式 → 变量 → 直觉**

| 环节 | 公式 | 变量 | 直觉 |
|---|---|---|---|
| 传播耦合（式 2） | $\delta\dot{\mathbf{v}} \simeq \delta\mathbf{g} - \mathbf{R}\delta\mathbf{b}_a - \mathbf{R}[\mathbf{a}_m-\mathbf{b}_a]_\times\delta\boldsymbol{\theta}$ | $\mathbf{a}_m$ 实测比力，$\boldsymbol{\theta}$ 姿态误差 | g 与 b_a 只在旋转耦合下可分辨 |
| 中断期位移（式 4） | $\|\delta\mathbf{p}_g\|\approx \tfrac12 g\sin(\varepsilon)T^2$ | $\varepsilon$ 重力方向偏差，$T$ **两次被接受的位姿校正之间的间隔** | 校正空缺越久，方向偏差的代价按 $T^2$ 放大；这是"恢复前位移"，不是最终误差 |
| 固定模重力误差分解（式 5） | $\|\mathbf{e}_g^\top\delta\mathbf{g}\| = g(1-\cos\varepsilon)=\mathcal{O}(\varepsilon^2)$；$\|\mathbf{P}_\perp\delta\mathbf{g}\| = g\sin\varepsilon=\mathcal{O}(\varepsilon)$ | $\mathbf{e}_g$ 真实 down 单位向量，$\mathbf{P}_\perp=\mathbf{I}-\mathbf{e}_g\mathbf{e}_g^\top$ | 方向误差**横向一阶、沿真 down 只有二阶**——所以方向因子天然不擅长压高度漂移 |
| 方向残差（式 3） | $\mathbf{r}_{d,k}=\mathbf{B}(\mathbf{d}_k^{AHRS})^\top \dfrac{\mathbf{R}_k^\top\hat{\mathbf{g}}}{\|\hat{\mathbf{g}}\|}$ | $\mathbf{B}$：在 $\mathbf{d}_k^{AHRS}$ 处的正交切基；GTSAM 双分量 Unit3 残差（非精确球面 log） | 报告的方向残差范数乘 $180/\pi$，是小角度等价量 |
| 匹配切换的协方差条件化 | $\mathbf{P}_{x\mid g}=\mathbf{P}_{xx}-\mathbf{P}_{xg}\mathbf{P}_{gg}^{-1}\mathbf{P}_{gx}$ | 在触发点把 g 固定在其 Online 均值 | 切换前两跑逐位相同，避免"把中断前累积的差异算到中断头上" |

---

## 3 · 带数字走一遍（玩具设定）

### 玩具 1：方向偏差在中断期的位移代价（式 4）

取 $g = 9.8090\ \text{m/s}^2$（论文中结构审计用的固定模长），重力方向偏差 $\varepsilon = 1^\circ$：

| 校正间隔 $T$ | $\tfrac12 g\sin\varepsilon\cdot T^2$ |
|---|---|
| 1 s | 0.086 m |
| 2 s | 0.343 m |
| 3 s | 0.771 m |
| 5 s | 2.143 m |

> **这是玩具示范，不是论文数字。** 论文明确警告：式 4 只描述**恢复前**的位移，不等于最终轨迹误差——配准可能修掉大部分误差，也可能只修掉一部分。"This describes displacement before recovery, not final trajectory error."

### 玩具 2：为什么方向误差"横向一阶、垂直二阶"（式 5）

$\varepsilon = 2^\circ$ 时：

| 分量 | 表达式 | 数值 |
|---|---|---|
| 沿真 down（垂直） | $g(1-\cos 2^\circ)$ | $\approx 0.0060\ \text{m/s}^2$ |
| 横向 | $g\sin 2^\circ$ | $\approx 0.3423\ \text{m/s}^2$ |

两者差约 **57 倍**。这解释了为什么方向因子"看得到方向、看不到高度"。

> **巧合提示**：论文 §IV-E 里配对干预把 b_a 平移了 **0.342 m/s²**，同时把 $\mathbf{g}-\mathbf{R}\mathbf{b}_a$ 保持在其 **$2.0\times10^{-7}$ m/s²** 以内——即沿"g/b_a 不可分辨方向"移动状态，pose 几乎不变。这个 0.342 与上表数值同量级纯属巧合，两者不是同一个量。

### 玩具 3：paper 的"真值尺度"提醒

论文指出：在 m2dgr-hall 上，**+2.3%** 的 RMSE_z 变化只对应 **+1.0 mm**；其 ATE 变化是 **-0.45%（-5.7 mm）**。所以 paired 百分比必须与绝对米数一起读——**两个指标还可能反号**（车载 2 s 中断：RMSE_z -11.2% 而 ATE +16.8%，任一个指标单独看都会误导配置选择）。

---

## 4 · 工程视角

**论文报告的 runtime 数据（逐字来源：§V-C 的 runtime audit，MCD NTU Day10，3 组 serial pairs，100 次 warm-up 后每次运行 3144 个 matched scans）：**

| 项 | 数值 |
|---|---|
| FixG 对 filter algebra 的降低 | **7.5%** |
| filter algebra 占核心时间 | **0.83%**（scan matching 占 **88.2%**） |
| FixG 可归因的节省 | **0.06%** |
| whole-core 时间变化 | **-11.6% 到 +3.1%**，**跨零** |
| 计时口径 | core / matching / filter-algebra 计时；filter algebra = 累积 update 减去 Jacobian 构造；whole-core 计时作者自称 "descriptive because map workloads bifurcate" |
| 每次运行的 matched scan 数 | **3144**（warm-up 100 scans 后） |

**论文未报告**（不得填数）：CPU/GPU 型号、绝对延迟（ms/帧）、内存/VRAM 占用、FPS 或吞吐、功耗、Jetson 等嵌入式平台的部署实测。

**部署约束的 trade-off（全部由论文陈述直接推出，非估算）**：

1. **无法 runtime 切换**：状态维数在**编译期**固定，四种是四个可执行文件 → 想在现场按场景切 Online/FixG 不可行；而"置零修正"的近似（23D proxy）本身会把 b_a 比较**偏置 +7.3 pp**。
2. **算力不是理由**：把 21D 降到 18D 换来的可归因节省是 **0.06%**，在 scan matching 占 88.2% 的架构里属于噪声级。论文原话："Dimension reduction is not a runtime strategy."
3. **可复现性代价**：早期 FAST-LIO2 logger **对主可执行文件而非每个裁剪后可执行文件做哈希**，导致这四个状态结构的精确 hash 无法回溯。后期批次改用 launch-specific fingerprint。→ 任何做同类编译期消融的团队，**必须对每个编译产物单独打指纹**。
4. **入模门槛 = 6 道 gate**：参考弧合理、姿态帧匹配、模态帧数精确一致、宿主无休眠、launch-specific 二进制指纹、串行执行。这些是"比较是否有效"的前置成本，做受控实验时要预留。

---

## 5 · 数据与评测

**数据组成（逐字）**：

- FAST-LIO2 名义群体：**12 条公开序列，来自 MCD、TIERS、M2DGR**；覆盖 vehicle / handheld / quadruped 平台，**四种 LiDAR/IMU 组合**；**路径长度 35 m 到 3.2 km**。
- 几何退化：在**一条 MCD 车载序列**上离线修改——射程截断到 **20 m**、水平 FoV 限制为前向 **±60°** 扇区、或删除连续 LiDAR 消息形成 **1/2/3/5 s** 缺口且**每 20 s 重复一次**。
- dropout 重复次数：四种状态配置在 **2 s 与 3 s 缺口**上各跑 **3 次**；另有一条 **TUHH handheld** 轨迹做 2/3/5 s 缺口的独立测试。
- IMU 权重扫描：配对 Online/FixG，把 IMU 噪声与零偏随机游走从 **0.01 缩放到 10**，在 **2 条车载轨迹**上。
- 初始化方向误差：**12 组**配对跑，注入 **0.5°/1°/2°** 重力方向误差（共享初始化后），一条车载 + 一条 handheld。
- 动态起步：四种配置在 **60 s 后缀**上比较；每条轨迹贡献 **1 个准静态 + 3 个低速率相位**，另加 **4 个更强相位**（选相位时不看 pose 结果）。共 **12 相位 / 48 轨迹**。相位选择用 **150 ms 的 IMU/GT 描述子**。
- 分配歧义测试：**10 次** 60 s 跑，单独把 g 倾斜 **±2°**，或配上 $\mathbf{b}_{a,1}=\mathbf{b}_{a,0}+\mathbf{R}_0^\top(\mathbf{g}_1-\mathbf{g}_0)$（保持 $\mathbf{g}-\mathbf{R}_0\mathbf{b}_a$ 初值不变）。
- 方向因子：Hall05 与 TUHH Day04（handheld）各做 **2（gravity state）× 3（weight）** 全设计，每个 state–weight 组合 **3 组 serial factor-on/off 配对**，**5 s 缺口**。
- 评测序列名（逐字）：**m2dgr-hall**、**MCD NTU Day10**、**NTU Night04**、**NTU d02**、**Hall05**、**TUHH Day04（TUHH n09 / TUHH d04）**。

**评测设置（讲条件，不只给结论）**：

- 指标：垂直位置 RMSE（**RMSE_z**，表中缩写 z）+ 3D 位置 RMSE（**ATE**），**刚性 SE(3) 对齐、不做 scale fitting**。
- 对齐前缀：FAST-LIO2 拟合**同时跨 10 s 与 30 m** 的前缀；LIO-SAM **只用时间准则**。作者声明该协议在系统内固定，**不用来跨系统排名**。
- 统计：名义 FixG 比较用 **paired log ratio 上的一侧 TOST**，预设 **±5%** 边界、**90%** 置信区间；事后 **±2% TOST** 与**五条轨迹族等权**分析是敏感性检查，不替代主检验。因子交互项用 **paired Wilcoxon** 检验 $I=\Delta_{g,b_a}-\Delta_g-\Delta_{b_a}$。
- LIO-SAM 与机制扫描保持 **descriptive**，不做跨轨迹 pooled inference。
- 结构性审计门槛：被移除状态必须**逐位精确不变**、被保留状态必须移动、$\|\mathbf{g}\|=9.8090\ \text{m/s}^2$、初始方向一致性在 **0.1°** 内。
- Hall05 有一次校正时间戳错位的运行被**排除并重跑**；最后一次 reset **不替换**；TUHH 两条落在 estimator-arc 诊断带之外的完整轨迹**保留指标并标注 "A" 警告**（避免 outcome-conditioned admission）。

---

## 6 · 能力与失败模式

**能做（论文实测支持）**：

- 在**持续 LiDAR correction + 可靠初始化**下，FAST-LIO2 固定重力达到**平均实用等价**：12 条序列 signed median RMSE_z 变化 **+0.9%**、median absolute **1.1%**（range **-6.7 到 +2.6%**）；ATE signed median **-0.1%**、median absolute **0.9%**（range **-4.0 到 +5.4%**）。反变换后的均值效应与 90% 区间：RMSE_z **-0.11% [-1.54, +1.34]%**，ATE **+0.09% [-1.16, +1.35]%**（两个 TOST 均 **p < 10⁻⁴**）。
- 绝对尺度小：median absolute FixG−Online 差异 RMSE_z **0.017 m**、ATE **0.014 m**。
- LIO-SAM 跨架构描述性检查方向一致：GE–BA 相对原生 FG–BA，RMSE_z 变化 **-0.37 到 +0.46%**、ATE **-0.07 到 +0.18%**，无一致符号。
- 结构性验证成立：Online 重力**最多移动 4.0°**，所有被移除的重力轨迹**逐位精确**且模长不变。

**不能做 / 失败模式**：

| 失败模式 | 具体数字 |
|---|---|
| **LiDAR 中断**（vs 几何退化）才是分水岭 | 车载 3 s/20 s：RMSE_z/ATE **+93.1%/+119.9%**，3 次 serial repeat 全部如此；handheld 响应更晚（3 s **+8.0%/+7.3%**，5 s **+27.9%/+34.5%**）。车载 5 s（**+41.2%/+23.8%**）反而小于 3 s → **时长不是单调剂量** |
| 中断时长与平台耦合 | 车载转折在 2–3 s（2 s 时两指标反号：**-11.2%/+16.8%**），handheld 更晚 → **不存在通用阈值** |
| 几何退化**不**复现 dropout 惩罚 | 20 m 射程截断 **+0.2%/-4.0%**；±60° FoV **+6.9%/+3.5%**（保留扫描时标） |
| 匹配 switch 的稳定效应在 **3D** 而非垂直 | 车载 dropout-minus-clean ATE 交互中位 **+4.16 m**，handheld **+1.01 m**；RMSE_z 交互**跨零**（车载 [-0.23, +2.74]，handheld [-0.08, +0.22]）；clean 输入 ATE 效应很小（**-0.83%** 车载 / **-0.30%** handheld） |
| 同 IMU 方向因子**可以**把轨迹变差 | TUHH 5 s 缺口：FixG/0.5° 的 RMSE_z **-64.6%** 但 ATE **+97.6%**；Online/2° **两指标同时恶化 +450.0%/+108.4%**。Hall05 侧全部 6 个 state–weight 中位数两指标都改善（最好 FixG/2° **-43.8%/-75.0%**），但 FixG/5° 只有 **2/3** 有效精度跑（1 次 reset） |
| 方向因子无单调剂量响应 | 固定重力下最紧因子让 RMSE_z 变差 **+1.0% 到 +1.2%**；中间因子 RMSE_z/ATE 变化 **-1.7% 到 -1.2% / -0.75% 到 +0.03%**；Online 重力下 ATE 落在 **-0.07% 到 +0.04%** |
| 固定加计零偏不比固定重力更安全 | FixBa / FixG+Ba 的 median RMSE_z **+1.5% / +1.9%**，序列级 range 远大于 FixG（[-2.1, +21.9] / [-8.7, +47.2]）。交互项 **-0.8 pp (p=0.470)** RMSE_z、**-0.8 pp (p=0.151)** ATE → **无超加性证据** |
| 动态起步：固定重力可能大崩 | 一个更强的车载相位里，Online 与 FixG 的 ATE 分别为 **0.905 m 与 5.074 m**，而 RMSE_z 反号（**0.625 m vs 0.170 m**）。FixBa 在**全部 4 个更强运动相位**上 ATE 变差（**+1.64% 到 +65.82%**）；两个固定零偏配置在一个低速率 handheld 起步相位**发散** |
| IMU 权重下无一致赢家 | NTU Day10（车载）FixG RMSE_z **-10.7% 到 -5.0%**、ATE **-1.2% 到 -0.2%**；NTU Night04（车载）RMSE_z **-3.2% 到 +1.7%** 但 ATE **+2.3% 到 +9.0%** |
| 姿态几乎不受影响 | 权重扫描最大 roll/pitch 变化 **0.052°**；初始化方向注入（0.5/1/2°）最大 roll/pitch 变化 **0.013°**，RMSE_z/ATE 跨度 **-3.5% 到 +2.1% / -2.3% 到 +1.8%** |

### 隐含假设 (Hidden Assumptions)

1. **参考轨迹在弱几何下依然可信**。admission 只用 "plausible reference arc" 做诊断；作者保留 arc warning 的轨迹（标 "A"）而非剔除，但**真值本身**在射程/FoV 退化实验里的可靠性并未被独立验证。
2. **dropout 可以用"删除 LiDAR 消息"代表**。论文明确说这只隔离了 correction absence，**不建模**前端 rejection 与 update delay。关键量 $T_k = t_k - t_{k-1}$ 是**两次被接受的位姿校正之间**的间隔，不是 LiDAR packet 到达间隔——"A rejected scan cannot interrupt inertial error accumulation."
3. **biased-but-accepted 的配准未被测试**。作者点名："Biased but accepted registrations instead introduce erroneous corrections, a different failure mode not tested here."
4. **几何退化是固定几何控制，不是标定过的失效模型**——距离/侧后覆盖被切掉，但扫描时标保留。
5. **重力模长固定** $\|\mathbf{g}\|=9.8090$ m/s²，只估 2 个切向坐标；模长变化（如电梯类非惯性运动）不在测试范围。
6. **同 IMU 相关性未建模**。AHRS 与预积分共用测量，论文承认 "Unmodeled same-IMU correlation could contribute to the adverse response, but we do not isolate it from weighting and online-gravity interactions."
7. **单一刚性 SE(3) 对齐、无 scale fitting**，且对齐前缀在系统内固定 → 跨系统比较被显式排除。
8. **样本量限制结论范围**：两条 dropout、两条初始化轨迹**不能建立通用阈值**；TOST 针对 pose error，**不涉及协方差一致性**；dropout 结果不在轨迹间 pooled。
9. **每次评估只跑有限次 serial pairs**（多为 1 或 3 次），failure/reset 被保留计数而不是替换——结论是"重复性"级的，不是统计置信级。
10. **LIO-SAM 侧是 descriptive transfer check**，作者明确不 establish LIO-SAM 等价，也不给 b_a 的通用规则。

---

## 7 · 与相关工作对比

| 对手 / 相关线 | 它的做法 | 本文的差异与边界 |
|---|---|---|
| **FAST-LIO / FAST-LIO2** [5,1,6] / **Point-LIO** [2] | 迭代误差状态滤波中把重力放在 $S^2$ 在线 | 本文**不改算法**，只改**编译期状态流形**（真移除而非抑制修正），用它同时充当被检验对象与实验平台 |
| **LIO-SAM** [3] | 初始化重力对齐帧，无在线方向状态 | 作为**跨架构描述性检查**（4 序列）：native FG–BA / FG–B0 / GE–BA / GE–B0，明确不做 pooled inference |
| **VE-LIOM** [7] | 优化框架内在线估重力 | 属"保留在线"阵营，但不在本文实验内；本文关心的是"保留是否必要"，不是"哪种在线实现更好" |
| **Lightning-LM** [4] | 23D→12D，移除 b_a、g、extrinsics | 本文直接检验这个动机：**维数削减不是 runtime 策略**（可归因节省 0.06%） |
| **重力约束配准 / radar–LiDAR / radar–leg** [19,20,21] | 用 IMU 垂直方向去约束旋转自由度，或加 velocity-supported / soft $S^2$ 重力信息，报告垂直精度提升 | 这些人**加信息或加残差**；本文测的是**固定一个已初始化的状态**，两者机制不同。且本文证明：**同 IMU 的更紧方向一致性不保证更低垂直/3D 误差** |
| **电梯类非惯性运动模型** [22] | 说明非惯性运动可违反名义重力模型 | 本文明确不测模长变化场景 |
| **VIO 可观性与一致性分析** [13,14,15] | 识别不可观/弱可观方向，平面运动进一步限制激励 | 这些分析回答"何时可辨识"，本文回答"**持续 LiDAR 校正下继续放开它是否改善 pose**"——两个不同问题 |
| **初始化器 / 联合在线标定** [16,17] | 把 g、bias、时延、外参在正常运行前估出来，或显式处理耦合 | 本文用**共享的 acceleration-mean 初始化器**做动态起步压力测试，不设计 motion-aware 替代方案 |
| **退化检测与处理** [23,24] | 从 LiDAR 几何或估计器可观性检测退化，做选择性更新/切换里程计/方向相关加权 | 本文把"弱几何"与"校正缺失"**实验分离**：前者保留扫描节奏，后者完全移除校正——这是被单一轨迹分数掩盖的区别 |
| **不确定度感知 benchmark 生成** [25] | 强调基准不确定度 | 本文把该思路落到 admission gate：参考弧合理性 + 精确校正时标 |
| **全局 PGO 重力先验** | 下游位姿图里的重力先验 | **明确在声明之外**（"Gravity priors in global pose-graph optimization (PGO) are outside this intervention."） |

**面试 Tip（被问到"这论文跟 FAST-LIO2 什么关系"时怎么答）**：
> "它不是新算法，是把 FAST-LIO2 当**手术台**：四个编译期状态流形（23/21/20/18D），只让 g 和 b_a 在/不在状态里，其余完全冻结。结论有两层——名义持续校正下固定重力**平均实用等价**（12 序列，mean paired effect 90% CI 落在 ±2% 内，median absolute 差异 0.017 m/0.014 m）；但**匹配 dropout switch 与动态起步**显示恢复代价非零（车载 3 s 缺口 RMSE_z/ATE +93.1%/+119.9%，某强动态相位 FixG ATE 5.074 m vs Online 0.905 m）。加上 FixG 只省 0.06% 核心时间，所以推荐保留。**加分点**：他们用 23D proxy 证明了'把修正置零'不等于'移除状态'，会给固定 b_a 比较带来 +7.3 pp 偏差。"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-17)

**Repo 信号说明（诚实披露）**：论文摘要末尾以**纯文本**形式给出 `Code, evidence, and video: https://github.com/jiejie567/rethink-lio-gravity`。本笔记**无法确认它是可点击超链接、也无法确认存在已发布 issue 流**；因此按本系列规则，**将其视为无已验证 repo 信号**——下面 3 条 pitfall **全部由 §6 失败模式 + §1/§2 的方法约束推导，未经任何 issue 验证**，不引用任何 issue 编号、commit 或日期。

**Pitfall 1 — 拿 Online 估计出的 $\mathbf{g}$ / $\mathbf{b}_a$ 当"标定量"喂给下游模块。**
- §6 失败模式：handheld 最后 10 s 里，重力与零偏估计相差 **0.73–0.74° / 0.122–0.126 m/s²**，但**有效项**只差 **0.0077–0.0091 m/s²**、位姿只差 **4.2–8.4 mm** → 两个量**各自**都不物理正确，只是组合对了。
- 方法约束：式 2 的 $\delta\dot{\mathbf{v}} \simeq \delta\mathbf{g}-\mathbf{R}\delta\mathbf{b}_a-\mathbf{R}[\mathbf{a}_m-\mathbf{b}_a]_\times\delta\boldsymbol{\theta}$ 表明 g 与 b_a 只靠旋转激励分辨；§II 引 [15] 指出平面运动进一步限制激励。
- 机械可推导的后果：把 Online 的 $\hat{\mathbf{g}}$ 直接当重力先验送给 PGO、地面分割或重力对齐可视化（RViz 里"看起来正常"），在弱激励段会注入一个 $\mathcal{O}(\varepsilon)$ 的横向误差源；而论文的 TOST **只针对 pose error，不保证协方差一致性**。

**Pitfall 2 — 把 3 s 阈值当通用工程参数套到真实退化场景。**
- §6 失败模式：车载转折在 2–3 s、handheld 更晚，且 5 s 车载效应（+41.2%/+23.8%）**小于** 3 s（+93.1%/+119.9%）→ 时长**非单调**；论文自陈"Two dropout and two initialization trajectories cannot establish universal thresholds."
- 方法约束：dropout 由**删除 LiDAR 消息**实现（"a fixed geometric control, not a calibrated model of sensor failure"），且关键间隔 $T_k$ 是**被接受的位姿校正之间**的时间，不是消息到达时间；论文点名 biased-but-accepted 配准是"a different failure mode not tested here"。
- 机械可推导的后果：真实遮挡/隧道/玻璃导致的是**带偏但被接受**的校正，其有效 $T_k$ 与消息级缺口不一致 → 直接照搬 "3 s 就要切 Online" 会在真实数据上系统性错判；且因为 §IV-C 里 RMSE_z 与 ATE 会**反号**，只盯一个指标做开关判断必然出错。

**Pitfall 3 — 用 runtime 置零修正 / 调方向因子协方差来"近似"状态移除。**
- §6 失败模式：23D proxy（置零修正、不改流形）给固定 b_a 的比较带来 **+7.3 pp** 偏差；方向因子调 $\sigma_d$ 时**没有单调剂量响应**（最紧因子使 RMSE_z 变差 +1.0% 到 +1.2%），Online/2° 在 TUHH 上两指标同时恶化 **+450.0%/+108.4%**。
- 方法约束：被压制的坐标**仍留在协方差里**并通过互相关影响保留变量；方向残差 $\mathbf{r}_{d,k}$ 用**同一 IMU** 的 AHRS 方向，**不观测 yaw、高度、垂直速度**，且式 5 决定其沿真 down 只有 $\mathcal{O}(\varepsilon^2)$。
- 机械可推导的后果：(a) 用 runtime 开关复现本文结论会得到**相反**的比较结果；(b) 把方向因子当 $z$-drift 补救并只调权重，会在 handheld 类轨迹上把 ATE 推高一个数量级；(c) 受 $\sigma_d$ 是"受控权重而非独立误差声明"这一约束，任何声称"加了因子所以更准"的消融都必须给出**配对的 RMSE_z 与 ATE 双指标**，否则无意义。

**Pitfall 4（可复现性，直接来自方法约束）— 编译期多可执行文件的指纹管理。**
- 论文自陈：早期 FAST-LIO2 logger **对主可执行文件而非每个裁剪后的可执行文件做哈希**，导致这四个状态结构的**精确 hash 无法回溯**；后期批次才改用 launch-specific fingerprint。admission 要求 **6 道 gate**（参考弧、姿态帧、精确模态帧数、宿主休眠、launch-specific 二进制指纹、串行执行）。
- 机械可推导的后果：照搬这套消融但只记录一次构建哈希，你的 21D/20D/18D 运行**无法事后证明**用的是哪一个状态流形——"removed states must remain bit-exact、retained states must move" 这条结构审计会直接失效，整个结论链断裂。

---

[← Back to LiDAR-Inertial Odometry README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`
> **UNVERIFIED 清单**：§3 全部玩具数值（1°/2° 三角函数推导、$T$ 扫描表）为示范性计算，非论文测量；§4 中的 CPU/GPU 型号、绝对延迟、内存/VRAM、FPS/吞吐均**论文未报告**；§8 全部 pitfall 为**推导**，未经 repo issue 验证（论文仅在摘要中以纯文本给出一处 `github.com` 字符串，未确认超链接或活跃 issue 流）。§5/§6/§7 中的所有数字与数据集名均逐字取自全文。

<!-- source: https://arxiv.org/abs/2609.13675 -->
