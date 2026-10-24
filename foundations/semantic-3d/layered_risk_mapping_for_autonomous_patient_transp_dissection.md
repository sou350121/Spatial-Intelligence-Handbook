[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: RGBD
paradigm: geometric
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# 分层风险地图：远征医疗设施中的自主患者转运 (Layered Risk Mapping for Autonomous Patient Transport in Expeditionary Medical Facilities)

> **发布时间**：2026-07-15（arXiv:2607.13497v1 [cs.RO]）
> **论文 / 模型名**：Layered Risk Mapping / **Noisy-OR Fusion**（LRM）
> **核心定位**：为"帐篷野战医院里没人陪同的病人转运"这一此前无人定义的运行域，把 4 类异质危险源（坡度 / 静态障碍 / 动态障碍 / 语义可通行性）用 Noisy-OR 概率融合成一张代价面，喂给 MPPI 局部规划器；比 `max` 融合与"无风险"基线更安全。

疫情爆发场景下，每次护送病人转运都要消耗一整套 PPE、并把一名临床医生从床旁抽走；自主轮椅本可吸收这部分负荷，但野战医院的地形（碎石道、临时木板路、泥地/草地过渡带）既不是室内服务机器人域，也不是越野 AGV 域。本文的结论是：**把危险源当作"可能独立致灾的因子"求联合概率（Noisy-OR），比"取最大值"或"加权求和"更贴合安全关键场景**。

## X-Ray 开场

它解决的问题是：野战/隔离医疗设施的转运走廊是"半结构化混合地形 + 生物危害区边界 + 移动人员"的三重叠加，现有室内轮椅导航（依赖预建图的 LiDAR/视觉里程计）与越野 AGV（单一几何危险源）都不覆盖。它提出的做法是：为每一类危险单独建一张 2D 风险栅格 $\mathcal{R}_i:\mathbb{Z}^2\to[0,100]$，归一化为 $\mu_i$ 后按 **Noisy-OR** 融合成"至少一个安全违例发生"的联合概率 $\mu_{\text{fused}}=1-\prod_i(1-\mu_i)$，再交给 MPPI 做随机 rollout 打分。对 spatial AI 研究者的意义：**这是一个"概率融合语义 vs. 启发式层叠加"的干净对照实验**——同一套感知、同一套规划器，只换融合算子，就能在仿真里把碰撞率从 73.3%–82.2% 压到 17.8%–31.1%，并指出 `max` 融合存在"低密度盲区"、log-odds 存在"高密度漂移"两种方向相反的失效模式。

## 📍 研究全景时间线

```
2019-2021  COVID-19 隔离病房消毒/无接触配送机器人
           → 证明"机器人能降低 staff 暴露"，但严格限于结构化室内
2020-2024  自主/半自主轮椅（shared control 为主；Baltazar et al. 全自主跨楼层+电梯）
           → 目标用户是"有意图但缺运动控制"，不是"无人陪护"
2020-2025  越野风险导航：RAMP(LiDAR 地面风险 → MPPI) / Cai、Endo(地形分类+打滑概率融合)
           → 单一或少数几何危险源，且不载人
           ROS 2 Nav2 layered costmap：priority-based max-value overlay
           driving-risk-field：人工加权势场求和（需手调权重、无概率解释）
2026-05    WHO 宣布 DRC/乌干达 Bundibugyo 埃博拉为 PHEIC（第 17 次 DRC 爆发）
2026-07    ★ 本文：4 层异质风险 + Noisy-OR 融合 + MPPI，仿真 Monte-Carlo + Q500M 实机
           【本文局限】μ_i 是未校准的 pseudo-probability；坡度层用 30 m DEM；
            静态/坡度层离线预计算；视觉 SLAM 在特征稀疏/突变光照下漂移；
            全部计算挤在一台 laptop 上；实机只做可行性演示、无统计量
```

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 | 在线性 |
|---|---|---|---|---|
| $\mathcal{R}_{\text{slope}}$ 坡度风险 | FABDEM（源自 Copernicus GLO-30 的 30 m bare-earth DEM） | 2D 风险栅格 $[0,100]$，四档 | 无学习；阈值按 ADA 1:12（≈4.8°）与 Q500M 厂商 8° 上限标定 | **离线预计算** |
| $\mathcal{R}_{\text{terr}}$ 语义可通行性 | 2× Orbbec Gemini 336L RGB-D 流 | 逐像素语义 → 查表得 $c\in[0,100]$ → 反投影到世界系栅格 | SegFormer-B2 **在 ADE20K（150 类）上微调**，推理时只前向 | 在线，**15 Hz** |
| $\mathcal{R}_{\text{static}}$ 静态障碍 | RGB-D + IMU（RTAB-Map 建图） | 轮椅垂直净空内的 3D 点云 → 2D 占据栅格 | 无学习 | **执行前预建** |
| $\mathcal{R}_{\text{dyn}}$ 动态障碍 | RTAB-Map 实时建图更新流 | 移动目标投影为 lethal cost | 无学习 | 在线，**15 Hz** |
| Noisy-OR 融合 | 四层 $\mu_i=\mathcal{R}_i/100$ | $\mu_{\text{fused}}\in[0,1]$ | 无参数、无训练 | 每个 MPPI 规划周期重算 |
| MPPI 局部规划 | $\mu_{\text{fused}}$ + 目标位姿 | 控制序列 | 无学习；$K=1000$ rollouts、$H=40$、$\Delta t=0.1$ s | 实时 |

栅格参数：cell size **0.30 m**，以轮椅为中心的 **10 m** 局部窗口。

### 1.2 关键机制

**⚡ Eureka Moment：危险不是"程度"，而是"致因"。** 两层各 0.5 的风险，`max` 给 0.5（等于单层），Noisy-OR 给 0.75——因为在安全关键场景里，你关心的是"至少有一层把我判死"的联合概率，而不是"最凶的那一层有多凶"。论文原文的表述是：四层来自**物理与感知上相互独立**的观测，因此应"combine each layer's independent failure probability into the joint probability that at least one violation occurs"，而不是调权重或让某层主导。作者同时点名两种被否定的做法：`max` 会"structurally dilute compounding risks"，加法会把低层传感器噪声"aggregate into artificial, impassable blockades"。

### 1.3 信息流

```
 FABDEM/GLO-30 (30m DEM) ──► slope tiers ──► R_slope  ─┐
                                                        │
 RGB-D ×2 ──► SegFormer-B2(ADE20K) ──► class→cost ──► R_terr ─┤   μ_i = R_i/100
                                                        ├─► Noisy-OR ──► μ_fused
 RGB-D+IMU ──► RTAB-Map ──► 点云 ──► 2D 占据 ──► R_static ─┤   (1-∏(1-μ_i))
                   └──► 实时更新 ──► 移动目标 ──► R_dyn  ──┘        │
                                                                    ▼
                                            MPPI: K=1000 rollouts, H=40, Δt=0.1s
                                            J_k = Σ_t μ_fused(x_t,y_t) + λ_term‖p_H−p_goal‖ + λ_hdg θ̃_H²
                                                                    │
                                                                    ▼
                                                          轮椅底盘控制
```

## 2 · 数学核心

📌 **Napkin Formula**：$\;\mu_{\text{fused}} = 1-\prod_{i\in\{\text{slope,terr,static,dyn}\}}\left(1-\mu_i\right)$，其中 $\mu_i=\mathcal{R}_i/100$ —— **风险是"或"，不是"和"，也不是"最大"。**

**目标**：把 4 张量纲不同、语义不同的风险栅格，变成一个能在 MPPI 里逐格查询、且概率可解释的标量代价面。

**公式 (1)**：
$$\mu_{\text{fused}}=1-\prod_{i}\left(1-\mu_{i}\right)$$

**变量**：
- $\mathcal{R}_i:\mathbb{Z}^2\to[0,100]$，0 = 完全安全，100 = 最大风险；
- $\mu_i=\mathcal{R}_i/100\in[0,1]$，论文明确称其为"the independent probability that layer $i$ causes a navigational safety violation at a given grid cell"；
- $\mu_{\text{fused}}$ = "the joint probability that at least one safety violation occurs"。

**公式 (2) MPPI rollout 打分**：
$$J_k=\sum_{t=0}^{H-1}\mu_{\text{fused}}\!\left(x_t^k,y_t^k\right)+\lambda_{\text{term}}\lVert \mathbf{p}_H^k-\mathbf{p}_{\text{goal}}\rVert_2+\lambda_{\text{hdg}}\left(\tilde\theta_H^k\right)^2$$
$(x_t^k,y_t^k)$ 为第 $k$ 条 rollout 在第 $t$ 步的预测位置，$\mathbf{p}_H^k$ 为终端位置，$\tilde\theta_H^k$ 为到目标方位的 wrapped heading 误差。实机取值：$\lambda_{\text{term}}=12.0$、$\lambda_{\text{hdg}}=0.5$，$\sigma_v=0.2$ m/s、$\sigma_\omega=0.1$ rad/s、温度 $\tau=0.4$。

**直觉**：因为 $1-\prod(1-\mu_i)\ge\max_i\mu_i$，Noisy-OR 是**单调放大**的：任何一层给出中等风险，融合后必被抬升；而当所有层都接近 0 时，融合值也接近 0（$\approx\sum\mu_i$，与加法在小风险区间近似等价，但不会线性堆到 1）。这解释了表 I 里 Noisy-OR 的"高进入率、低条件峰值"特征：它愿意踩边（进入率 8.9%–13.3%，高于 Max 的 6.9%/8.9%/11.1%），但把踩边的严重度压住。

**原始风险栅格的阈值设计**（可工程复用的标定逻辑）：

| 层 | 分级 | 依据 |
|---|---|---|
| slope | $<5^\circ\to0$；$5^\circ$–$8^\circ\to50$；$8^\circ$–$20^\circ\to80$；$>20^\circ\to100$ | ADA 1:12（≈4.8°）/ Sunrise Medical 对 Q500M 的 8° 安全上限 / 打滑与重心偏移 / ISO 7176-2 动态稳定性 |
| terr | 硬质高摩擦（road, path, floor）$r\le10$；可变形（grass, sand, mud, rock）$r=20$–$65$；结构不可通行（wall, fence, water, building）$r=100$ | 轮-土交互的打滑与能耗排序 |
| static | 垂直净空内点云，0 = 未观测/自由，100 = 高置信障碍 | RTAB-Map 离线建图 |
| dyn | 实时建图流中的移动目标 → lethal | RTAB-Map 在线更新 |

注意 8°–20° 给 80 而非 100 是有意为之："This preserves finite (rather than lethal) traversal cost, allowing the planner to cross such terrain when no lower-risk route exists."

## 3 · 带数字走一遍（玩具设定，数值为本文自造，仅演示公式行为）

设某格四层归一化风险为 $\mu_{\text{slope}}=0.5$（5°–8° 档）、$\mu_{\text{terr}}=0.2$、$\mu_{\text{static}}=0$、$\mu_{\text{dyn}}=0.3$：

| 融合方式 | 计算 | 结果 |
|---|---|---|
| Max | $\max(0.5,0.2,0,0.3)$ | **0.50** |
| 加法（被论文否定的做法） | $0.5+0.2+0+0.3$ | 1.00（直接变成不可通行假障碍） |
| **Noisy-OR** | $1-(1-0.5)(1-0.2)(1-0)(1-0.3)=1-0.5\times0.8\times1\times0.7$ | **0.72** |
| Log-odds | $\sigma(\sum\ell_i)$，$\ell=\mathrm{logit}$：$0+(-1.386)+0+(-0.847)=-2.233$，$\sigma=1/(1+e^{2.233})\approx0.097$ | **≈0.10** |

这张表说明了三件事：(1) `max` 把 4 层压成 1 层的信息，0.72 的复合风险被读成 0.50；(2) 加法在小风险区没问题，但只要两层同时给中等值就饱和到 1，规划器会绕无可绕；(3) **log-odds 在"没有任何一层说很危险"时会跌到 0.10**——比单层最小值还小，这正好呼应表 I 里 Log-odds 在高密度下条件峰值风险从 0.48→0.52→0.58 逐级爬升、且三种 risk-informed 方法中碰撞率最差（24.4%–25.4%）的反向失效。

再看代价：若整条 40 步 rollout 都落在该格，$\sum_{t=0}^{39}\mu_{\text{fused}}=0.72\times40=28.8$，与 $\lambda_{\text{term}}=12.0$ 乘上终端到目标距离的量级可直接比较——这就是为什么 $\lambda_{\text{term}}$ 的标定必须以 $\mu_{\text{fused}}$ 的尺度为前提（见 §8 第 3 条）。

## 4 · 工程视角

| 项 | 数值 | 来源 |
|---|---|---|
| 计算平台 | Razer x Lambda Tensorbook 笔记本；Intel Core i7-11800H CPU；NVIDIA GeForce RTX 3080 Mobile GPU，**16 GB VRAM**；64 GB RAM；Ubuntu 22.04 LTS | 论文报告 |
| 传感器 | 2× Orbbec Gemini 336L RGB-D，前向，装在座椅导轨上 | 论文报告 |
| 载体 | Quickie Q500M 中轮驱动电动轮椅 + LUCI safety payload | 论文报告 |
| 语义层 / 动态层刷新 | **15 Hz**（来自 RGB-D 流） | 论文报告 |
| 栅格分辨率 / 局部窗口 | 0.30 m / 10 m | 论文报告 |
| MPPI | $K=1000$ rollouts，$H=40$，$\Delta t=0.1$ s；$\sigma_v=0.2$ m/s，$\sigma_\omega=0.1$ rad/s，$\tau=0.4$；$\lambda_{\text{term}}=12.0$，$\lambda_{\text{hdg}}=0.5$ | 论文报告 |
| 坡度层 / 静态层 | **离线预计算** | 论文报告 |
| 端到端规划频率 / 融合耗时 / FPS | **论文未报告** | — |
| 显存占用 / 功耗 | **论文未报告**（仅给出 16 GB VRAM 的硬件上限） | — |
| 实机 mission 用时 | 室内：Intake 10.0 m / 65.94 s；Intra-facility 6.23 m / 42.62 s；Egress 8.59 m / 47.08 s。室外：Intake 6.93 m / 45.27 s；Intra-facility 11.12 m / 69.13 s；Egress 9.09 m / 54.53 s | 论文报告 |

**Trade-off 三条（论文自陈 + 从参数推出）**：
1. **算力是全系统瓶颈，不是算法**。作者明确写："all components execute onboard a laptop, which introduces strict resource competition when simultaneously running high-frequency semantic segmentation (SegFormer), local planning, and spatial mapping"，并把迁到 NVIDIA Jetson AGX Orin 列为未来工作。$K=1000\times H=40=40000$ 次代价查询/规划周期，与 15 Hz 语义分割共享一块 3080 Mobile。
2. **15 Hz 是语义层与动态层的地板，而静态/坡度层是"零在线成本"换来的"零在线更新"**——省算力的代价是部署后改不了（见 §6/§8）。
3. **10 m 局部窗口 + 0.30 m 栅格 → 约 33×33 格**；这个窗口内的风险完全由"反应式"更新重建（论文："Hazards are assessed reactively within the sliding local map window"）。窗口外无全局风险规划，长走廊只能靠局部贪心绕行。

## 5 · 数据与评测

**仿真设置**：Gazebo 搭建的"代表性爆发式野战医院"——4 个帐篷治疗模块围绕中央 staging area，帐篷位置与结构布局**所有 trial 固定**；地形 patch（gravel / mud / grass / rock）与高程特征在每次 trial 开始时按密度参数 $\rho$ 生成；人群在帐篷间沿每 trial 随机轨迹移动；仿真轮椅镜像 Q500M 的尺寸与运动学约束。

**危险密度分级（逐字）**：$\rho\in\{1.0,1.5,2.0\}$。$\rho=1.0$ 时 24 个地形 patch + 6 个坡度 patch = 30 个 hazard patch；$\rho=1.5$ 时 32 + 8 = 40；$\rho=2.0$ 时 36 + 9 = 45。**人群数量恒为 4，不随密度变化。**

**流程**：paired Monte-Carlo，每种融合方法在每个密度下 **50 runs**，同一 run 内 4 种方法共享完全相同的 hazard 配置与人群轨迹 seed（即"paired"的含义）。4 种方法：
- **Noisy-OR**：式 (1)；
- **Log-odds**：$\mu_{\text{fused}}=\sigma(\sum_i\ell_i)$，$\ell_i$ 为第 $i$ 层的 log-odds；
- **Maximum**：$\mu_{\text{fused}}=\max_i\mu_i$，对应 ROS 2 Nav2 的默认层组合策略；
- **No risk**：$\mu_{\text{fused}}=0$，绕过融合风险图、只对障碍反应。

**指标定义（逐字口径）**：SPL（条件于成功的路径效率，失败 run 记 0）；Obstacle clearance（m，全程最小机器人-障碍距离）；Collision Rate（% 至少发生一次碰撞的 run 比例）；Collisions（每 run 与静态障碍和人的接触事件总数）；High-Risk Zone Entry Rate（% 至少穿越一个 risk > **0.3** 的栅格的 run 比例）；Conditional Peak Risk（进入风险区前提下遇到的最大风险值，未进入的 run 被排除）。

**表 I 关键数字（论文原文，mean ± std，列序 = No risk / Noisy-OR / Max / Log-odds）**：

| 指标 | $\rho$ | No risk | **Noisy-OR** | Max | Log-odds |
|---|---|---|---|---|---|
| SPL | 1.0 | 0.77±0.18 | 0.66±0.29 | 0.71±0.26 | 0.67±0.30 |
| | 1.5 | 0.77±0.18 | 0.69±0.27 | 0.69±0.28 | 0.69±0.27 |
| | 2.0 | 0.77±0.18 | 0.68±0.27 | 0.65±0.31 | 0.64±0.30 |
| Obstacle clearance (m) | 1.0 | 0.16±0.23 | **0.49**±0.13 | 0.42±0.15 | 0.46±0.12 |
| | 1.5 | 0.14±0.22 | **0.50**±0.07 | 0.40±0.17 | 0.44±0.12 |
| | 2.0 | 0.17±0.23 | **0.50**±0.06 | 0.42±0.14 | 0.45±0.11 |
| Collision Rate (%) | 1.0 | 73.3 | 17.8 | 22.2 | 24.4 |
| | 1.5 | 82.2 | 24.4 | 31.1 | 25.4 |
| | 2.0 | 75.6 | 17.8 | 22.2 | 24.4 |
| Collisions | 1.0 | 3.94±1.50 | 3.88±4.94 | **2.20**±1.87 | 2.27±2.33 |
| | 1.5 | 3.95±1.88 | **2.36**±4.20 | 5.43±11.06 | 3.73±3.26 |
| | 2.0 | 4.00±1.86 | **1.50**±0.53 | 1.80±0.92 | 2.00±1.55 |
| High-Risk Zone Entry (%) | 1.0 | 44.4 | 8.9 | 6.9 | 6.7 |
| | 1.5 | 55.6 | 13.3 | 8.9 | 11.1 |
| | 2.0 | 60.0 | 13.3 | 11.1 | （所给文本片段中缺失） |
| Conditional Peak Risk | 1.0 | 0.70±0.20 | **0.47**±0.05 | 0.69±0.20 | 0.48±0.06 |
| | 1.5 | 0.73±0.19 | **0.50**±0.16 | 0.55±0.14 | 0.52±0.16 |
| | 2.0 | 0.71±0.20 | **0.55**±0.16 | 0.56±0.23 | 0.58±0.16 |

**结论口径**：风险感知方法在**所有密度、所有指标**上优于 No risk；No risk 的 SPL 最高（0.77±0.18，uniformly）但不偏离直路，碰撞率 73.3%–82.2%、间隙 0.14–0.17 m、高风险区进入率 44.4%–60.0%。三种 risk-informed 方法把碰撞率压到 32% 以下、间隙保持在 0.40 m 以上、高风险区进入率压到 13.4% 以下。Noisy-OR 的间隙方差最小（从 0.13 缩到 0.06）。Max 在 $\rho=1.5$ 出现 5.43±11.06 的碰撞数方差（"an order of magnitude higher than any other method or density"），且低密度下条件峰值风险 0.69 几乎与 no-risk 的 0.70 无差别。

**实机验证设置**：室内为受控场地中复现帐篷模块布局 + 一个人造 hazardous floor patch；室外为同样的帐篷配置放在非结构化草地上、含自然高程变化与模块间地表过渡。起终点**随机选取**。三个 mission profile 全部完成；论文给出 6 条 (距离, 用时) 对（见 §4 表），**未报告实机的成功率、碰撞次数、间隙或任何统计量**（n 也未报告）。

**数据/模型资产**：SegFormer-B2 在 ADE20K（150 类）上微调；高程来自 FABDEM（由 Copernicus GLO-30 DEM 去除建筑与植被冠层得到的 30 m bare-earth DEM）；建图/定位用 RTAB-Map。完整的 ADE20K class→cost 查表在项目页。

## 6 · 能力与失败模式

**能做（论文有证据）**：
- 在 4 层危险源同时存在的混合地形里，把"撞上"的概率量级从"多数 run 都撞"降到"少数 run 撞"（仿真，73.3%–82.2% → 17.8%–31.1%）。
- 维持**稳定**的障碍间隙：Noisy-OR 在三个密度下 0.49–0.50 m，方差随密度**下降**（0.13 → 0.06）。
- 在真机上完成 intake / intra-facility / egress 三类 mission（室内与室外草地各一遍），并展示局部风险图随行进实时更新、规划器绕开红色高风险区后重新收敛到目标（Fig. 6）。
- 相比 `max`：消除"低密度盲区"；相比 log-odds：消除"高密度漂移"；相比 no-risk：安全指标全面领先。代价是 SPL 下降（0.77 → 0.64–0.71）。

**不能做 / 论文承认的失效**：
- **视觉 SLAM 漂移**：室外"feature-sparse environments and during sudden lighting transitions"下 RTAB-Map 视觉里程计漂移，"affected the accuracy of the local planning"；作者明确"resolving tracking drift is outside the scope of this work"。
- **算力竞争**：三个高频组件同跑一台 laptop，资源争抢（未给量化）。
- **概率未经校准**："We treat the normalized cost $\mu_i=\mathcal{R}_i/100$ as an uncalibrated pseudo-probability; layer-specific probability calibration is future work."——即 Noisy-OR 的"独立概率"语义是**设计假设**，不是标定结果。
- **Noisy-OR 的进入率反而最高**：三种 risk-informed 方法中它在每个密度的 High-Risk Zone Entry Rate 都最高（8.9% vs 6.9%/6.7% @ $\rho=1.0$）。作者的解释是"当它确实穿过边缘风险区时，把暴露的峰值严重度紧紧压住"，但这是一个**未做因果验证的解释**。
- **实机无统计结论**：6 条轨迹、无重复次数、无失败率，只能算 feasibility。

### 隐含假设 (Hidden Assumptions)

1. **层间独立**（Noisy-OR 的数学前提）。但 slope 与 terr 明显相关（草坡 vs 泥坡同源），static 与 dyn 同出 RTAB-Map——相关性会使 $\prod(1-\mu_i)$ 低估联合风险。论文只说四层"arise from physically and perceptually independent observations"，未做独立性检验。
2. **$\mu_i$ 可当概率用**。风险值 0/50/80/100 是**人工档位**（ADA、厂商手册、ISO 7176-2），不是频率标定。$\mu=0.5$ 并不意味"50% 会翻车"。
3. **静态图与坡度图在 mission 期间有效**。$\mathcal{R}_{\text{static}}$ 与 $\mathcal{R}_{\text{slope}}$ 都是"precomputed offline"，而野战医院的核心特征是"assembled anew at each deployment"——两者在时间尺度上是矛盾的。
4. **30 m DEM 能刻画 10 m 局部窗口内的坡度**。GLO-30/FABDEM 的水平分辨率（30 m）> 局部窗口（10 m）> 栅格（0.30 m），即坡度层在单个窗口内基本是常数场。
5. **风险 > 0.3 即"高风险区"** 是一个全局固定阈值，用于指标定义；它不随地形类型或病人状态变化。
6. **per-scene 假设**：整篇的部署单元是"一个场地 + 一次建图 + 一批固定 seed 的 trial"，跨场景泛化（换帐篷布局 / 换地面材质分布）未被测试。

## 7 · 与相关工作对比

| 工作线 | 代表 | 危险源数量 | 融合方式 | 载人 | 混合室内外地形 |
|---|---|---|---|---|---|
| 灾难医学机器人 | 搜救/伤员后送 [3–5]、医疗配送 [6,7] | — | — | 否 | — |
| 隔离病房机器人 | COVID-19 消毒/配送 [8] | — | — | 否 | 否（严格室内结构化） |
| 半自主轮椅 | [9–12] | — | shared control / human-in-the-loop | 是 | 否 |
| 全自主轮椅 | Baltazar et al. [14]（接医院信息系统、跨层、对接电梯） | 单一（占据） | 预建图 | 是 | 否 |
| 室内轮椅导航 | LiDAR + 视觉里程计 [16,17] | 单一 | 预建图 | 是 | 否 |
| 室外轮椅导航 | GPS/IMU/LiDAR 融合 [17–19] | 单一 | 城市/结构化室外 | 是 | 否（未考虑异质地形可通行性） |
| 越野风险导航 | RAMP [20]（LiDAR 地面风险 → MPPI）；Cai [21]、Endo [22]（地形分类 + 打滑概率 → 联合可通行性分布） | 1–2 | 概率 / 单源 | **否** | 部分 |
| 多层代价地图 | Nav2 layered costmap [23] | 多 | priority-based **max-value overlay** | 否 | 否 |
| 行车风险场 | [24] | 多（车/路/行人） | 人工加权势场求和 | 是 | 否 |
| 学习式代价网络 | [25] | 多模态 | 端到端学习 | — | 需 in-domain 训练数据（野战医院不具备） |
| **本文** | LRM | **4（slope/terr/static/dyn）** | **Noisy-OR 概率融合** | **是** | **是** |

论文对"为什么不学一个代价网络"的回答很关键：野战医院每次部署都是新建的，**in-domain 训练数据根本不存在**，所以必须走"物理可解释层 + 无参数融合"的路子。这也是它和 [25] 的分界线。

**面试 Tip**：如果被问"这跟 Nav2 的 layered costmap 有什么区别？"，标准答法是三段——(1) Nav2 用 priority-based max-value overlay，**结构上会让单层主导**，四层复合风险被读成最大那一层；(2) 本文把每层视为**独立致因**，求"至少一个违例"的联合概率，数学上 $\mu_{\text{fused}}\ge\max_i\mu_i$ 恒成立；(3) 这个差别在仿真里可测：Max 在低密度下条件峰值风险 0.69（no-risk 是 0.70，几乎没起作用），在 $\rho=1.5$ 出现 5.43±11.06 的碰撞数方差。**再补一句诚实的**：本文的 $\mu_i$ 是未校准的 pseudo-probability，所以"概率融合"目前是**结构性优势**而非标定优势。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-24)

**Repo 状态核查**：全文出现的唯一链接是项目页 `https://lrm-patient-transport.github.io/`（*。github.io，非 github.com 仓库*）。**论文未给出 github.com 仓库地址**，因此不存在可引用的 issue / commit / PR 证据链。以下 3 条 pitfall **由 §6 失败模式 + §1/§2 的方法约束机械推导，未经任何 issue 验证**，请勿当作社区已验证结论引用。

| # | Pitfall | 从哪条失败模式 / 约束推出 | 工程后果 |
|---|---|---|---|
| H1 | **离线层 = 部署不可迁移** | §6 假设 3：$\mathcal{R}_{\text{static}}$ 与 $\mathcal{R}_{\text{slope}}$ 均"precomputed offline"；而论文开篇即强调野战设施每次部署"assembled anew" | 换场地必须重跑 RTAB-Map 建图 + 重新拉取 FABDEM patch；若跳过，$\mathcal{R}_{\text{static}}$ 退化为全 0，Noisy-OR 只剩 terr+dyn 两层，安全增益按式 (1) 单调下降（层数减少 → $\prod(1-\mu_i)$ 变大 → $\mu_{\text{fused}}$ 变小） |
| H2 | **30 m DEM 与 0.30 m 栅格量级失配** | §2 坡度四档全部由 FABDEM（30 m）算出；§1 局部窗口 10 m、栅格 0.30 m | 在 10 m 窗口内坡度层近乎常数场，帐篷间木板路↔泥地的**微观过渡**不可能出现在 $\mathcal{R}_{\text{slope}}$ 中；该过渡只能靠 SegFormer 的 terr 层兜底，而 terr 层 15 Hz 刷新 + 手工查表，风险档位跳到 100（wall/fence/water）时会直接封路 |
| H3 | **$\mu_i$ 未标定 → $\lambda_{\text{term}}=12.0$ 不可移植** | §6 原文"We treat ... as an uncalibrated pseudo-probability"；§2 式 (2) 中风险项是 $\sum_{t=0}^{H-1}\mu_{\text{fused}}$，上限随 $H=40$ 线性增长，而终端项 $\lambda_{\text{term}}\lVert\cdot\rVert_2$ 与 $H$ 无关 | $\lambda_{\text{term}}=12.0$ / $\lambda_{\text{hdg}}=0.5$ 是在**该场地、该层查表、该 $H$** 下调出来的（论文："tuned on outdoor trials and held fixed"）；换传感器、换 ADE20K 微调、或改 $H$，风险项与终端项的相对权重即失配，需重调——否则表现为"该绕不绕"或"原地打转" |

**另附一条来自作者自陈的部署约束（非推导）**：所有组件同跑一台 laptop 造成"strict resource competition"，作者计划迁至 NVIDIA Jetson AGX Orin。任何在本平台上复现的人，第一步应验证 SegFormer 的 15 Hz 刷新在目标硬件上是否仍成立——**但这个 15 Hz 在目标硬件上的实际值，论文未报告**。

---

[← Back to navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（提供片段，Table I 的 $\rho=2.0$ / Log-odds 高风险区进入率单元格在片段中缺失，已标注）· 未在真机复现的数字标 `UNVERIFIED`；本文未给出 latency / FPS / 显存占用，相关格已写「论文未报告」

[//]: # "<!-- source: https://arxiv.org/abs/2607.13497 -->"
