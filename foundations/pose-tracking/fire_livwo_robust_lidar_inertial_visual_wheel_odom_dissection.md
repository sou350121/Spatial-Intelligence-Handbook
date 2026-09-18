<!-- ontology-5axis
problem: VIO
representation: voxel
sensor: multi-modal
paradigm: geometric
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# FIRE-LIVWO：失效免疫的毫米波雷达增强型 LiDAR-惯性-视觉-轮速里程计 (FIRE-LIVWO: Robust LiDAR-Inertial-Visual-Wheel Odometry via Failure-Immune mmWave Radar Enhancement)

> **发布时间**：2026-09-04（arXiv:2609.05325v1 [cs.RO]）
> **论文 / 模型名**：FIRE-LIVWO（Failure-Immune mmWave Radar-Enhanced LiDAR–Inertial–Visual–Wheel Odometry）
> **核心定位**：面向地下煤矿「浓烟 + 长直自相似巷道」的双重退化场景，用一个 IESKF 紧耦合 LiDAR / 4D 毫米波雷达 / 视觉 / 轮速五种传感器，靠**在线可观测性评分动态切换融合模式**，在 baseline 全部失效或漂移数十米的隧道里把平均定位误差压到 5.677 m。

地下煤矿巷道又长、又暗、又充满烟尘，还有高度重复的墙面。视觉被烟遮死、LiDAR 点云在长直方向欠约束、单模态和多模态固定权重融合都会崩。本文的结论是：**别用固定融合策略，用在线可观测性分数当开关，缺什么补什么**——烟大就切雷达 Doppler，几何退化就切轮速 NHC。

---

## X-Ray 开场

这篇论文要解决的是：在地下煤矿这种「视觉 + 几何会**同时且异构地**退化」的场景里，LVI（LiDAR-Visual-Inertial）SLAM 会因单一 Hessian 阈值检测或固定融合权重而失效甚至发散。

它提出的方案是：把 4D 毫米波雷达（强穿透）、LiDAR、视觉、轮速里程计塞进**一个统一 VoxelMap + 一个 IESKF**，并设计**两套检测器**——用大气散射模型（暗通道先验）估计视觉可观测性分数 $\mathcal{O}_V$，用点-面残差 Hessian 的特征值比估计几何可观测性分数 $\mathcal{O}_G$——在线决定激活/抑制哪些残差项，从而在 LIV / LIVR / LIVW / LIVRW 四种融合模式间切换。

对 spatial AI 研究者而言，它的意义不在于新传感器，而在于**「可观测性可量化、融合策略可在线调度」这一范式**：把「哪路传感器现在可信」变成一个可计算的标量门控信号，而不是靠人工规则或全局固定协方差。

---

## 📍 研究全景时间线

```
2020  LIO-SAM / 2022 FAST-LIO2 ──── LiDAR-Inertial 紧耦合，IESKF 成为主流后端
   │
2021  LVI-SAM ───────────────────── LIO + VIO 因子图，多模态雏形
   │
2022  R3LIVE / FAST-LIVO ────────── IESKF 紧耦合 LiDAR-Visual-Inertial
   │
2024  FAST-LIVO2 / SR-LIVO ──────── 统一体素地图 + 稀疏直接光度残差
   │
2023  4DRadarSLAM ───────────────── 端到端 4D 毫米波雷达 SLAM
2024  GaRLIO / DR-LRIO ──────────── 点级 Doppler 速度 + 雷达-激光-惯导，抗退化
   │
   │   ★ 空缺：多模态融合的「可信度评估」本身仍是启发式/固定权重
   ▼
2026  ★ FIRE-LIVWO（本文）───────── 雷达+LIO+VIO+轮速 五模态 + 可观测性驱动的
                                     自适应融合模式切换（LIV/LIVR/LIVW/LIVRW）
```

**本文在演进中的位置**：它是「多模态紧耦合」与「退化检测」两条线的合流点——把 GaRLIO/DR-LRIO 的雷达 Doppler 思路、AC 类轮速 NHC 思路、以及 Hessian 可观测性检测，统一进一个可在线切换模式的 IESKF。

**本文局限（timeline 视角）**：
- 阈值 $\mathcal{O}_V^{th}=0.4$、$\mathcal{O}_G^{th}=40$ 是**人工设定常数**，未给自适应/在线标定机制；
- 验证只在**一条地下煤矿的三个隧道**（Tunnel1/2/3）以 20 个全站仪真值点完成，规模有限；
- 系统**强依赖轮速里程计**，本质上是地面差速/阿克曼平台方案，空中/足式不可迁移；
- 最终 5.677 m 是**米级**误差，仍是「能跑完全程」而非「高精度建图」量级。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **① Radar-Enhanced LiDAR-Visual-Inertial Constraint Module**（V-A） | LiDAR 扫描 $\mathbf{p}^L_j$、4D 雷达回波 $\mathbf{p}^R_j$ + Doppler $\hat v_{R_j}$、图像 $I_k$、IMU $\mathbf{u}_i$ | 统一 VoxelMap（0.5 m 根体素，八叉树；叶节点存平面 $\Pi=(\mathbf n,\mathbf q,\boldsymbol\Sigma)$，部分点带 $8\times8$ patch）；残差 $\mathbf r_L,\mathbf r_{R_G},\mathbf r_{R_V},\mathbf r_C$ | **无训练**，纯在线滤波；雷达/激光点统一进地图与残差框架 |
| **② Vehicle Kinematic-Constraint Module**（V-B） | 轮速 $\hat{\mathbf v}^W$、LiDAR 时间戳、轮-IMU 外参 | 轮速残差 $\mathbf r_W$（含非完整约束 NHC + 在线杆臂补偿） | 无训练；仅几何约束，不学模型 |
| **③ Degradation Detection & Adaptive Fusion Mode Switching Module**（V-C） | 当前帧图像（估透射率）、LiDAR+雷达点-面 Hessian $\mathbf H_G$ | 视觉可观测性 $\mathcal O_V$、几何可观测性 $\mathcal O_G$，退化标志 $\mathcal D_V,\mathcal D_G$，融合模式 | 无训练；阈值离线标定，在线判断 |

### 1.2 关键机制

**⚡ Eureka Moment：把「哪路传感器现在可信」压缩成两个可在线计算的标量分数（$\mathcal O_V$ = 平均透射率，$\mathcal O_G$ = Hessian 最小/最大特征值比），用它当开关去激活/加权 IESKF 里的残差项——而不是依赖单一 Hessian 阈值或固定融合权重。**

三个配套设计支撑这一点：
1. **统一 VoxelMap**：雷达点与 LiDAR 点共用同一套点-面残差形式（式 5/6），雷达点还能被投影到图像上贡献稀疏光度残差（式 9）——即雷达不只是「测距」，还当视觉地图点的来源（$\mathcal P^{map}=\mathcal P^{map}_L\cup\mathcal P^{map}_R$）。
2. **点级 Doppler 速度残差**（式 8）：在烟雾里 LiDAR/视觉失效时，用雷达的径向速度保住状态可观测性。
3. **轮速 NHC + 在线杆臂补偿**（式 10）：长直走廊几何欠约束时，用本体感知补上退化方向。

### 1.3 信息流 / 架构图

```
                 ┌───────────── IMU (IMU frame = body) ─────────────┐
                 │              前向传播 → x̂_k, P̂_k                 │
                 ▼                                                  │
 ┌──────────────────────────────┐                                   │
 │ ① Radar-Enhanced LIV 模块    │                                   │
 │  LiDAR scan ─┐               │   r_L  (式5, point-to-plane)      │
 │  4D radar  ──┼→ 统一VoxelMap ├─► r_RG (式6, point-to-plane)      │
 │  image ──────┘   (0.5m octree)│   r_RV (式8, Doppler 速度)        │
 │                              │   r_C  (式9, 稀疏直接光度)        │
 └──────────────────────────────┘                                   │
                                                                    ▼
 ┌──────────────────────────────┐                    ┌──────────────────────────┐
 │ ② 车辆运动学约束模块          │   r_W (式10, NHC)  │  IESKF 迭代更新 (式4)     │
 │  轮速 + 在线杆臂补偿          ├───────────────────►│  min Σ ‖r(·)‖²_{P^{-1}}   │
 └──────────────────────────────┘                    └──────────────────────────┘
                                                                    ▲
 ┌──────────────────────────────┐                                   │
 │ ③ 退化检测 & 融合模式切换     │   𝒟_V, 𝒟_G 决定激活哪些残差项     │
 │  图像→暗通道先验→𝒪_V (式11-13)│───────────────────────────────────┘
 │  Hessian→特征值比→𝒪_G (式14-16)│
 └──────────────────────────────┘
       模式：LIV → LIVR(烟) / LIVW(几何退化) / LIVRW(双重退化)
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$\min_{\delta\mathbf x_k}\;\underbrace{\big\|\mathbf x_k\boxminus\hat{\mathbf x}_k\big\|^2_{\hat{\mathbf P}_k}}_{\text{IMU 先验}}+\sum_{\text{5 类残差}}\big\|\mathbf r(\mathbf z,\mathbf x_k)\big\|^2_{\mathbf P^{-1}},\qquad \text{激活哪些项} \xleftarrow{\ \mathcal O_V,\ \mathcal O_G\ } \text{在线门控}$$

**一句话直觉**：这就是一个加权最小二乘/IESKF，唯一的「智能」在于——**哪些残差项被加进去、权重多大，由一个在线可观测性分数实时决定**。

### 2.1 目标与公式

**目标**：在 IMU 先验（式 3）下，对误差状态 $\delta\mathbf x_k$ 求 MAP 估计（式 4）：

$$\min_{\delta\mathbf x_k\in\mathcal M}\Bigg(\|\mathbf x_k\boxminus\hat{\mathbf x}_k\|^2_{\hat{\mathbf P}_k}+\sum_{i=1}^{N_{R_V}}\|\mathbf r_{R_V}\|^2_{\mathbf P^i_{R_V}}+\sum_{i=1}^{N_{R_G}}\|\mathbf r_{R_G}\|^2_{\mathbf P^i_{R_G}}+\sum_{i=1}^{N_L}\|\mathbf r_L\|^2_{\mathbf P^i_L}+\sum_{i=1}^{N_C}\|\mathbf r_C\|^2_{\mathbf P^i_C}+\sum_{i=1}^{N_W}\|\mathbf r_W\|^2_{\mathbf P^i_W}\Bigg)$$

- 状态 $\mathbf x\in\mathbb R^{18}$：$\mathbf x\triangleq[\ {}^G\mathbf R_I^T,\ {}^G\mathbf p_I^T,\ {}^G\mathbf v^T,\ \mathbf b_g^T,\ \mathbf b_a^T,\ {}^G\mathbf g^T\ ]^T$
- 优化非凸，用 Gauss-Newton 迭代求解，**等价于 iterated Kalman filter**。

**五类残差**：

| 残差 | 公式 | 物理含义 |
|---|---|---|
| LiDAR 点-面 $\mathbf r_L$ | $\mathbf u_j^T({}^G\mathbf T_{I_k}{}^I\mathbf T_L{}^L\mathbf p_j-\mathbf q_j)$（式 5） | LiDAR 点到地图平面距离 |
| 雷达几何 $\mathbf r_{R_G}$ | $\mathbf u_j^T({}^G\mathbf T_{I_k}{}^I\mathbf T_R{}^R\mathbf p_j-\mathbf q_j)$（式 6） | 雷达点用**同一形式**做点-面 |
| 雷达 Doppler $\mathbf r_{R_V}$ | $\mathbf u({}^R\mathbf p_j)^\top{}^I\mathbf R_R^\top({}^G\mathbf R_{I_k}^\top{}^G\mathbf v_{I_k}+\lfloor\hat\omega_I\rfloor_\times{}^I\mathbf p_R)-\hat v_{R_j}$（式 8） | 雷达径向速度 vs 由状态算出的速度投影 |
| 视觉光度 $\mathbf r_C$ | $(I_k(\mathbf u_i+\Delta\mathbf u)-\delta\mathbf n_{I_k})-(I_r(\mathbf u_i'+\mathbf A_i^r\Delta\mathbf u)-\delta\mathbf n_{I_r})$（式 9） | 参考 patch 与当前 patch 的亮度差（带仿射补偿） |
| 轮速 $\mathbf r_W$ | ${}^W\hat{\mathbf v}-{}^I\mathbf R_W^T({}^G\mathbf R_I^T{}^G\mathbf v+{}^I\omega\times{}^I\mathbf p_W)$（式 10） | NHC：轮速投影 + 杆臂补偿 |

其中 Doppler 残差的关键量是**雷达系线速度**（式 7）：
$$\mathbf v_R={}^I\mathbf R_R^\top\big({}^G\mathbf R_{I_k}^\top{}^G\mathbf v_{I_k}+\lfloor\hat\omega_I\rfloor_\times{}^I\mathbf p_R\big),\quad \mathbf u({}^R\mathbf p_j)=\frac{{}^R\mathbf p_j}{\|{}^R\mathbf p_j\|}$$

**退化检测（两套分数）**：

视觉侧（式 11–13）：大气散射模型 $I(\mathbf u)=J(\mathbf u)t(\mathbf u)+A(1-t(\mathbf u))$，$t(\mathbf u)=\exp(-\beta d(\mathbf u))\in(0,1]$。用**暗通道先验**估透射率 $\hat t(\mathbf u)$，定义
$$\mathcal O_V\triangleq\bar t_k=\frac{1}{|\mathcal U|}\sum_{\mathbf u\in\mathcal U}\hat t(\mathbf u)\in(0,1],\qquad \mathcal D_V=1 \iff \mathcal O_V\le\mathcal O_V^{th}$$

几何侧（式 14–16）：对 $\mathbf H_G\triangleq\mathbf J_G^\top\mathbf W_G\mathbf J_G$ 取姿态子块 $\mathbf H_{pose}=\begin{bmatrix}\mathbf H_{rr}&\mathbf H_{rp}\\ \mathbf H_{pr}&\mathbf H_{pp}\end{bmatrix}\in\mathbb R^{6\times6}$，分别特征分解 $\mathbf H_{pp}=\mathbf V_p\boldsymbol\Lambda_p\mathbf V_p^\top$、$\mathbf H_{rr}=\mathbf V_r\boldsymbol\Lambda_r\mathbf V_r^\top$，定义
$$s_p\triangleq\Big|\frac{\lambda_{p_1}}{\lambda_{p_3}+\epsilon}\Big|,\quad s_r\triangleq\Big|\frac{\lambda_{r_1}}{\lambda_{r_3}+\epsilon}\Big|,\qquad \mathcal O_G=\max(s_p,s_r)$$
$$\mathcal D_G=1 \iff \mathcal O_G\ge\max(s_p^{th},s_r^{th})$$

**变量说明**：$\lambda_{p_1}\ge\lambda_{p_2}\ge\lambda_{p_3}$ 为平移 Hessian 特征值；最小特征值对应方向（特征向量 $\mathbf v_{p_3}$/$\mathbf v_{r_3}$）即**退化方向**。

**直觉**：如果 Hessian 的最大/最小特征值相差悬殊（比如 40 倍以上），说明在最小特征值方向上「几乎没有任何约束」——长直巷道沿走廊方向的平移就是典型例子。

### 2.2 模式切换状态机

| 条件 | 模式 | 激活的额外约束 |
|---|---|---|
| $\mathcal D_V=0,\ \mathcal D_G=0$ | **LIV**（标称） | 无（LiDAR+IMU+Visual） |
| $\mathcal D_V=1,\ \mathcal D_G=0$ | **LIVR**（视觉退化） | 雷达 Doppler $\mathbf z_{R_V}$ |
| $\mathcal D_V=0,\ \mathcal D_G=1$ | **LIVW**（几何退化） | 轮速 $\mathbf z_W$ |
| $\mathcal D_V=1,\ \mathcal D_G=1$ | **LIVRW**（双重退化） | 雷达 Doppler + 轮速 |

---

## 3 · 带数字走一遍

> ⚠️ 本节为**玩具设定**演示切换逻辑；但其中 $\mathcal O_V$、$\mathcal O_G$ 的数值**取自论文 Fig. 6 / Fig. 7 实测报告**（论文只报了特征值比值 $\mathcal O_G$，未报原始特征值，故特征值为示意值）。

### 3.1 几何退化检测（长直走廊）

论文报告：机器人 x 位置从 0→276 m 行进时，
- x=10 m（Tunnel1 内）：$\mathcal O_G=34.7$
- x=20 m：$\mathcal O_G=36.7$
- x=135 m：$\mathcal O_G=40$（退化起点）
- x=143 m：$\mathcal O_G=114.2$（最严重）
- x=276 m（Tunnel3 末端）：$\mathcal O_G=9.2$

阈值 $\mathcal O_G^{th}=40$。玩具化推演：设某处平移 Hessian 特征值 $\lambda_{p_1}=12.0,\ \lambda_{p_3}=0.105$，
$$s_p=\Big|\frac{12.0}{0.105}\Big|\approx 114.3\ \approx\ \mathcal O_G=114.2>40\ \Rightarrow\ \mathcal D_G=1$$
此时对应 $\mathbf v_{p_3}$ 的方向就是**沿走廊 x 轴的平移**——点云沿这个方向没有平面能约束它。系统随即从 LIV 切到 **LIVW**，加入轮速残差 $\mathbf r_W$。

反之在 Tunnel1 内 $\lambda_{p_1}/\lambda_{p_3}\approx 34.7<40$，$\mathcal D_G=0$，保持 LIV/LIVR。

### 3.2 视觉退化检测（烟区）

论文报告：$\mathcal O_V^{th}=0.4$，
- x=4 m（清晰）：$\mathcal O_V=0.88$ → $\mathcal D_V=0$
- x=10 m（进烟）：$\mathcal O_V=0.66$ → $\mathcal D_V=0$
- x=25 m（最浓烟）：$\mathcal O_V=0.02$ → $\mathcal D_V=1$
- x=35 m（烟减弱）：$\mathcal O_V=0.40$ → 临界
- x=53 m（无烟）：$\mathcal O_V=0.66$ → $\mathcal D_V=0$（视觉重新激活）

玩具化推演（单像素透射率平均）：若采样 4 个像素透射率 $\hat t=[0.01,0.02,0.03,0.02]$，则
$$\mathcal O_V=\bar t=\frac{0.01+0.02+0.03+0.02}{4}=0.02\le 0.4\ \Rightarrow\ \mathcal D_V=1$$
系统抑制视觉光度残差 $\mathbf r_C$、引入雷达 Doppler $\mathbf r_{R_V}$，切到 **LIVR**。

### 3.3 双重退化下的完整切换序列

论文明确报告 FIRE-Full 完成了两次在线切换：
```
视觉退化区间：LIV --(O_V↓0.02)--> LIVR --(O_V↑0.66)--> LIV
几何退化区间：LIV --(O_G↑114.2)--> LIVW --(...)--> LIV
```
结果：FIRE-Full 达 AvgErr = **5.677 m**，而缺雷达的 FIRE-LIVW 与缺可观测性评估的 FAST-LIVO2 在 Tunnel1 **直接失败（×）**，缺轮速的 FIRE-LIVR 在 Tunnel3 漂到 **15.420 m**。

---

## 4 · 工程视角

**论文实际报告的平台信息（可逐字引用）**：

| 项 | 论文报告值 |
|---|---|
| 计算平台 | Intel i7 CPU、32 GB DDR4 RAM、NVIDIA GeForce GTX 1050Ti GPU、512 GB SSD 的工业 PC |
| 机器人 | Husky A200 |
| LiDAR | Livox AVIA（内置 IMU） |
| 相机 | Hikvision MVS-CU013-A0UC |
| 4D 毫米波雷达 | Oculii Eagle |
| 里程计 | 底盘轮速里程计 |
| 同步 | 硬件同步器对齐 LiDAR / IMU / 相机 / 雷达 |
| 运动模式 | 恒定前进速度 0.3 m/s，最大角速度 0.2 rad/s |
| 地图结构 | 八叉树自适应体素，根体素 0.5 m，叶节点存平面特征，部分点带 $8\times8$ patch |

**论文未报告的项（不填数字）**：

| 指标 | 状态 |
|---|---|
| 单帧 / 单次滤波更新 latency、FPS、实时率 | 「论文未报告」 |
| CPU / GPU 占用率、显存（VRAM）占用、峰值内存 | 「论文未报告」 |
| 状态维度之外的参数规模 / 地图体素数增长曲线 | 「论文未报告」 |
| 各模块（雷达处理 / 图像暗通道 / Hessian 特征分解）耗时拆分 | 「论文未报告」 |

**可推导的 engineering trade-off（定性，不涉数字）**：
- **GTX 1050Ti 是低端 GPU**：论文选用它说明该系统的计算负载主要压在 CPU 侧的滤波与特征分解上，而非神经网络推理；但同时论文没有给任何耗时数字，**无法判断实时性**。
- **模式切换的双刃剑**：引入雷达 Doppler 会增加 $N_{R_V}$ 个残差、引入轮速会增加 $N_W$ 个残差，Hessian 也随之变大（$\mathbf H_G\in\mathbb R^{18\times18}$，姿态子块 $6\times6$ 特征分解）；切换本身带来**额外的 Jacobian 组装与特征分解开销**，论文未量化这一开销。
- **0.5 m 根体素 + 部分点携带 $8\times8$ patch**：在「长距离、大规模」煤矿场景（论文强调 long travel distances）下，地图内存随里程线性增长，论文未给内存曲线。
- **运动速度 0.3 m/s 很低**：这意味着论文验证的是**低速巡检/救援**工况，切换到高速平台时的滤波收敛性与外参/时间同步敏感性，论文未讨论。

---

## 5 · 数据与评测

**数据集 / 场景（论文原文）**：真实地下煤矿巷道，自采数据，**无公开 benchmark**；由于地下无 GPS，用**全站仪（total station）**测真值。

- **Tunnel1**：特征相对丰富，但有**严重烟尘**（视觉退化主导）。
- **Tunnel2**：**无烟但特征稀疏**（论文列出后未在结果中详细展开）。
- **Tunnel3**：**极度特征稀疏且高度重复**（几何退化主导），代表最严重几何退化区（$\mathcal O_G$ 峰值 114.2 位于 x=143 m）。
- 世界系原点为全站仪中心 $\mathbf O_G$，机器人初始位置设为 $\mathbf P_{robot}=(-6.261,\ 1.222,\ 0.268)$。

**评测设置（讲条件）**：
- 真值点数量：**20 个全站仪测点** $\mathbf p^i_{gt}$；
- 指标定义：$\mathrm{AvgErr}=\sum_{i=0}^{N-1}\frac{\|\mathbf p^i_{es}-\mathbf p^i_{gt}\|}{N}$；
- **失败判据**：若某方法在序列中崩溃或数值发散、无法输出完整轨迹，则记为 **failure（×）**；
- 对比方法：FAST-LIVO2 (LIV)、R3LIVE (LIV)、GaRLIO (RLI)、4DRadarSLAM (Radar)；
- 消融变体：FIRE-Base (LiDAR+IMU+Visual)、FIRE-LIVR (LIVR)、FIRE-LIVW (LIVW)、FIRE-Full (LIVRW)。

**结果（逐字取自论文 Table II，单位 m）**：

| 方法 | AvgErr |
|---|---|
| **FIRE-Full** | **5.677**（best） |
| FIRE-LIVR | 15.420 |
| FIRE-LIVW | × （失败） |
| FIRE-Base | 23.962 |
| FAST-LIVO2 | × （失败） |
| R3LIVE | 31.596 |
| GaRLIO | 17.212 |
| 4DRadarSLAM | 45.453 |

**补充报告的数字（逐字）**：
- 4DRadarSLAM 沿 y、z 轴出现**高达 15 m** 的显著漂移；
- Fig. 6 关键点：x=10 m, $\mathcal O_G=34.7$；x=20 m, $\mathcal O_G=36.7$；x=135 m, $\mathcal O_G=40$；x=143 m, $\mathcal O_G=114.2$；x=276 m, $\mathcal O_G=9.2$；阈值 $\mathcal O_G^{th}=40$；
- Fig. 7 关键点：x=4 m, $\mathcal O_V=0.88$；x=10 m, $\mathcal O_V=0.66$；x=25 m, $\mathcal O_V=0.02$；x=35 m, $\mathcal O_V=0.40$；x=53 m, $\mathcal O_V=0.66$；阈值 $\mathcal O_V^{th}=0.4$。

**注意**：论文**未报告**绝对轨迹误差 ATE/RPE、未报告各隧道的分段误差、未报告 Tunnel2 的定量结果、未报告多次运行的均值/方差。

---

## 6 · 能力与失败模式

### 6.1 能做

- **浓烟穿越（Tunnel1）**：FIRE-Full 在 $\mathcal O_V$ 掉到 0.02 时抑制视觉、切雷达 Doppler，稳定穿过烟区并重新激活视觉；对比 FIRE-LIVW 与 FAST-LIVO2 在 Tunnel1 **失败（×）**。
- **长直巷道几何退化（Tunnel3）**：$\mathcal O_G$ 冲到 114.2 时切轮速 NHC，抑制 x 轴漂移；对比 FIRE-LIVR、FIRE-Base、R3LIVE、GaRLIO 在同一区域出现明显漂移。
- **双重退化**：同时进入 LIVRW，最终全程走完隧道，AvgErr = 5.677 m。
- **在线可观测性量化**：$\mathcal O_V$、$\mathcal O_G$ 的曲线与真实退化边界（进烟点、退化起点）对齐良好。

### 6.2 不能做 / 失败模式

| 失败模式 | 触发条件 | 论文证据 |
|---|---|---|
| 视觉依赖型方案崩溃 | 浓烟（$\mathcal O_V\le0.4$）且无雷达或多普勒 | FIRE-LIVW、FAST-LIVO2 在 Tunnel1 失败（×） |
| 缺轮速时几何漂移 | 长直走廊（$\mathcal O_G\ge40$） | FIRE-LIVR 在 Tunnel3 漂移，AvgErr 15.420 m |
| 纯雷达方案漂移 | 雷达点云稀疏、测距精度有限 | 4DRadarSLAM 不崩溃但 y/z 漂移高达 15 m，AvgErr 45.453 m |
| 固定融合权重方案漂移 | 混合退化 | R3LIVE 31.596 m、GaRLIO 17.212 m、FIRE-Base 23.962 m |
| 雷达+激光仍不足以抗几何退化 | 高度重复的极稀疏结构 | GaRLIO、FIRE-LIVR 在 Tunnel3 出现明显几何退化（Fig. 4-(g1,b1)） |

### 6.3 隐含假设 (Hidden Assumptions)

1. **时间同步与外参已标定**：论文显式假设「五传感器（LiDAR/IMU/相机/轮速/4D 雷达）时间偏移已知（预标定或同步）」，「所有传感器刚性安装，LiDAR/相机/IMU 硬件同步」。→ 一旦同步误差存在，$\mathbf r_{R_V}$ 的 Doppler 速度残差会直接吸收时间错位。
2. **大气散射模型适用**：$\mathcal O_V$ 通过暗通道先验估透射率，假设烟雾符合 $I=Jt+A(1-t)$ 模型。→ 若照明本身变化（矿灯闪烁、无照明区）或浓烟中 airlight $A$ 非均匀，$\mathcal O_V$ 会误判。
3. **非完整约束成立**：式 10 的轮速残差基于 NHC，隐含**车辆无侧滑、地形平坦**的差速/阿克曼假设。→ 论文自身在 Intro 里就警告「地面可能变得不平整、非结构化」，这与 NHC 假设直接冲突，是潜在的隐性失效点。
4. **Doppler 速度来自静态环境**：式 8 假设 $\hat v_{R_j}$ 反映的是平台自身运动在视线方向的投影（几何上由 $\mathbf u({}^R\mathbf p_j)$ 决定）。→ 存在动态目标/多径时，Doppler 会被污染。
5. **平面特征存在**：五类残差中三类（LiDAR/雷达几何）都是 point-to-plane，隐含场景中存在可匹配平面。→ 极稀疏/重复结构下平面退化正是本文要处理的问题，说明该假设在目标场景本来就会破。
6. **阈值可迁移**：$\mathcal O_V^{th}=0.4$、$\mathcal O_G^{th}=40$ 为常数，隐含「煤矿隧道场景的退化边界可被同一组阈值覆盖」。

---

## 7 · 与相关工作对比

| 维度 | FAST-LIVO2 | R3LIVE | GaRLIO | 4DRadarSLAM | **FIRE-LIVWO** |
|---|---|---|---|---|---|
| 传感器组合 | LIV | LIV | RLI（雷达-激光-惯导） | 纯雷达 | **LiDAR + IMU + Visual + Radar + Wheel** |
| 后端 | IESKF | IESKF | — | — | **IESKF** |
| 雷达 Doppler | ✗ | ✗ | ✓ | — | ✓（点级 $\mathbf r_{R_V}$） |
| 轮速约束 | ✗ | ✗ | ✗ | ✗ | **✓（NHC + 在线杆臂）** |
| 统一 VoxelMap（LiDAR+雷达+视觉共用） | 部分（LiDAR+视觉） | — | ✗ | ✗ | **✓（$\mathcal P^{map}=\mathcal P^L\cup\mathcal P^R$）** |
| 退化检测 | 无在线可观测性评估 | 无 | — | — | **✓（$\mathcal O_V$ 透射率 + $\mathcal O_G$ Hessian 特征值比）** |
| 融合策略 | 固定 | 固定 | 固定 | — | **在线自适应模式切换** |
| 本文报告 AvgErr | × （Tunnel1 失败） | 31.596 m | 17.212 m | 45.453 m | **5.677 m** |

**关键差异一句话**：其他方法把「传感器融合权重」当超参固定死，FIRE-LIVWO 把它变成**由可观测性分数在线调度的状态机**——这是「多模态融合」到「多模态调度」的转变。

### 🎤 面试 Tip

被问到「FIRE-LIVWO 和 FAST-LIVO2 / R3LIVE 有什么本质区别？」时，不要罗列传感器清单，直接答三层：

> **第一层（表示）**：它把雷达点和 LiDAR 点放进**同一个 VoxelMap**、用**同一套 point-to-plane 残差形式**（式 5/6），雷达还额外贡献 Doppler 速度残差（式 8），而不是把雷达当独立子系统。
> **第二层（调度）**：它的核心贡献是**可观测性驱动的自适应融合模式切换**——用 $\mathcal O_V$（暗通道先验透射率）判视觉退化、$\mathcal O_G$（Hessian 特征值比）判几何退化，在线在 LIV/LIVR/LIVW/LIVRW 间切。
> **第三层（证据）**：在真实煤矿隧道里，缺任一模态都显著掉分——FIRE-LIVR 15.420 m、FIRE-Base 23.962 m，而 FIRE-LIVW 和 FAST-LIVO2 直接失败，全系统 5.677 m。

再补一句风险意识：「它的阈值是人工设定的，且强依赖轮速，所以是典型的地面机器人方案，泛化性还没被验证。」

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-18)

**repo 信号说明**：论文 Abstract 以纯文本脚注形式给出代码地址 `https://github.com/KJ-Falloutlast/FIRE-LIVWO`（原文："We open source our code of this work on Github 3 3 3 https://github.com/KJ-Falloutlast/FIRE-LIVWO"）。该链接在 arXiv 文本中**以纯文本形式出现，未提供任何 issue 内容、commit、或讨论流**。因此本节**无法引用任何社区 issue**，以下 pitfall 由 §6 失败模式 + 本文方法约束**推导**（未经 issue 验证）。

### Pitfall 1 · 固定阈值在下穿/上穿边界处「抖动切换」

- **§6 失败模式锚点**：论文自身数据显示 $\mathcal O_V$ 在 x=35 m 处为 **0.40**，恰好等于阈值 $\mathcal O_V^{th}=0.4$（Fig. 7）；$\mathcal O_G$ 在 x=135 m 处为 **40**，恰好等于 $\mathcal O_G^{th}=40$（Fig. 6）。
- **方法约束锚点**：退化判据式 13 与式 16 是**硬阈值二值函数**（$\mathcal D_V\in\{0,1\}$、$\mathcal D_G\in\{0,1\}$），没有滞回（hysteresis）或时间平滑。
- **推导后果**：当分数在阈值附近（烟雾边缘、退化边界）抖动时，融合模式会在 LIV↔LIVR、LIV↔LIVW 之间高频切换，导致残差项集的激活状态反复跳变、Hessian 结构突变。工程上应加滞回带或对 $\mathcal O_V/\mathcal O_G$ 做滑动平均，但这在论文中未讨论。

### Pitfall 2 · NHC 假设与论文自述场景直接矛盾

- **§6 失败模式锚点**：论文 Intro 明确写「the ground may become uneven and unstructured」（地面可能不平整、非结构化），且 §6.3 隐含假设 3 指出式 10 基于非完整约束。
- **方法约束锚点**：式 10 的轮速残差 $\mathbf r_W$ 把轮速投影到 IMU 系，并假设**无侧滑、地形平坦**；论文虽提到「online lever-arm compensation」补偿杆臂，但**未提任何 slip 检测或地形坡度补偿项**。
- **推导后果**：一旦机器人驶过论文自述的「不平整地面」或出现轮子打滑，$\mathbf r_W$ 会给出错误的速度约束——而它恰恰是在**几何退化时被激活**的那个约束，等于在最需要它的时候给它注入了错误信息，可能导致沿退化方向的反向漂移。
- **验证方式**：由于无 issue 流可查，需自行在带坡度/湿滑地面复现。

### Pitfall 3 · Doppler 残差依赖静态环境与雷达视场筛选，动态/多径场景下会污染估计

- **§6 失败模式锚点**：论文报告 4DRadarSLAM「limited ranging accuracy and sparse point clouds lead to severe drift of up to 15 m along the y- and z-axes」，说明 Oculii Eagle 的**雷达点本身精度有限、稀疏**。
- **方法约束锚点**：式 8 的 Doppler 残差对每个雷达点 $j$ 都用单位方向 $\mathbf u({}^R\mathbf p_j)={}^R\mathbf p_j/\|{}^R\mathbf p_j\|$ 构造，隐含「该点的 Doppler 只由平台自运动产生」；论文虽提到用 ego-velocity estimation 做外点剔除并显式加入「radar field-of-view constraints」，但未给出对**动态目标**的处理。
- **推导后果**：在井下救援场景里若有移动的人员/设备，其 Doppler 会被当作平台自运动约束，在视觉已失效、雷达成为主力模态的 LIVR 阶段尤其危险。同时雷达点被插入统一 VoxelMap（$\mathcal P^{map}_R\subset\mathcal P^{map}$），稀疏且有噪声的雷达点可能污染地图平面拟合。

---

[← Back to VIO README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2609.05325 -->
