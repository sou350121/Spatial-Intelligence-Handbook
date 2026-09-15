<!-- ontology-5axis
problem: navigation
representation: scene-graph
sensor: mono
paradigm: 3R-SLAM-hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# SuperMap：面向视觉-语言导航的时空 SLAM 系统 (SuperMap: A Spatio-Temporal SLAM System for Visual-Language Navigation)

> **发布时间**：2026-08-24（arXiv:2608.22896v1 [cs.RO]）
> **论文 / 模型名**：SuperMap
> **核心定位**：把「高频几何 SLAM」与「低频开放词汇感知」解耦并联，用一个一致性驱动的在线建图引擎（3D 感知实例关联 + 存在性/标签置信度更新）首次同时做到**实时 + 开放词汇 + 实例级 + 短时&长时动态 + 4D 场景图**；对标 Khronos（闭集、非实时）、ConceptGraphs / HOV-SG（离线）。
> **Ontology 标签**：problem=navigation · representation=scene-graph · sensor=mono · paradigm=3R-SLAM-hybrid · time=incremental

现实痛点是：开放词汇检测器（GroundingDINO / SAM2）逐帧输出**间歇且视角相关**，直接塞进建图管线会得到身份漂移、语义过期的地图；而现有场景图方法（ConceptGraphs、HOV-SG）需要分钟到小时的离线重建。SuperMap 的结论是：只要把"几何一致性残差"同时用作**存在性判据**和**语义融合门控**，就能在机器人上实时维护一张可查询、可剪枝、可追溯历史的实例级 4D 地图。

## X-Ray 开场

机器人导航要的是"能回答『白板旁边那个显示器在哪』『刚才放在植物旁边的椅子去哪了』"的地图，而现有系统要么离线、要么闭集、要么只能处理移动的人而看不到"垃圾桶被搬走"这类长时变化。SuperMap 提出三层（几何/实例/拓扑）在线 SLAM：用 SuperOdometry 出位姿与稠密重建，用 3D-to-2D 运动补偿替代 2D 跟踪器的线性运动模型来扛自车剧烈运动，再用**深度残差 Δd 的符号**判定地图点是"可观测 / 被遮挡 / 已消失"，并以 log-odds 累积剪枝、以贝叶斯后验融合标签，最后把实例组织成带空间边与时序边的 4D 场景图交给 VLM 出导航路点。对 spatial AI 研究者的意义：**"几何残差 = 存在性证据 + 语义门控"** 这个复用范式，是把异步大模型感知安全接进实时 SLAM 的一个可复制的工程接口。

## 📍 研究全景时间线

```
【离线开放词汇语义建图】
 OpenScene / ConceptGraphs / HOV-SG
   │  假设完整场景扫描；分钟~小时级；无在线可用性
   ▼
【闭集语义 SLAM】
 Kimera / SuMa++ / LIOM
   │  实时、有场景图，但闭集 CNN 分割、无实例级身份
   ▼
【开放词汇在线建图】
 RayFronts / OVO-SLAM / CLIO
   │  实时/在线，但无长时变化；或非实例级；CLIO 缺时空能力
   ▼
【时空动态（短时+长时）】
 Khronos
   │  覆盖短时+长时，但闭集、无实例级跟踪、难以实时
   ▼
【本文 2026】SuperMap ── 实时 ✓ 开放词汇 ✓ 实例级 ✓ 短时 ✓ 长时 ✓ 场景图 ✓
   │
   └─ 本文局限：高速动态物体跟踪能力有限；
                 依赖预定义 object prompt 列表，无自动提示/开放世界发现
```

---

## 1 · 核心架构 / 方法总览

系统由三层 + 一个 VLM 接口组成（Fig. 2）：几何层在线 3D 重建 → 实例层时空实例关联 → 拓扑层 4D 场景图 → VLN。核心声明是"全 onboard 实时"。注意：ontology 标 `sensor=mono`，但实机传感器套件实为 **Livox Mid-360 LiDAR（360°×59° FOV）+ 360° 全景相机 + IMU**，属 LiDAR-惯性-视觉融合，不是纯单目。

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 | 频率（论文报告） |
|---|---|---|---|---|
| **几何层** SuperOdometry [35] | RGB、depth/LiDAR、IMU | 位姿 $P_t=\mathbf{T}_{WC}^{(t)}$、稠密彩色 3D 重建 | 无训练（经典 LVI 里程计），纯在线推理 | 10 Hz |
| **2D 感知** GroundingDINO [12] + SAM2 [21] | RGB 帧 | 2D 实例检测框 + 分割 mask + 开放词汇标签 | 冻结基座模型，zero-shot，无微调 | 1 Hz |
| **3D 感知实例关联** | 2D 检测 + $P_t$ + 历史地图 $\mathcal{M}_{t-1}$ | 实例 ID $\mathcal{I}_t$ | 无训练；Kalman 滤波 + 3D-to-2D 投影先验 | 论文未单独报告 |
| **几何一致性更新** | 地图点 $\mathbf{X}_k$、当前 depth $D(\mathbf{u})$ | 每点占用 log-odds、存在性状态 $s_k^{(t)}$ | 无训练；解析式递推 | 并入 3D mapping |
| **贝叶斯语义融合** | 检测器标签 $z_t$ | 每实例标签后验 $P(L_j=c)$ | 无训练；需检测器混淆矩阵 | 并入 3D mapping |
| **拓扑层** 4D 场景图 | 实例 + 3D 质心 + 类别谓词 | $\mathcal{G}=(\mathcal{V},\mathcal{E}_s,\mathcal{E}_t)$ | 无训练；按质心距离聚类后加边 | 5 Hz（3D mapping 3 Hz） |
| **VLN 接口** | 局部子图序列化文本 | VLM（Gemini 2.0 Flash）→ `<answer>` 内实例 ID → 3D 路点 | 无训练；zero-shot VLM 推理 | 论文未报告 |

### 1.2 关键机制

**⚡ Eureka Moment：一个标量深度残差 $\Delta d = d_{proj} - D(\mathbf{u})$ 的**符号**同时编码了两件事——"这个地图点还存在吗"（存在性）和"这一帧的语义标签可信吗"（观测可更新性）。** 因此不必为变化检测单独训练一个模块，变化检测和语义融合天然共享同一个几何证据源。

三条支撑这个洞见的机制：

1. **3D-to-2D 运动补偿替代线性运动模型**：标准 2D 跟踪器（如 ByteTrack [33]）在自车剧烈运动下会漂，SuperMap 用"把地图中实例的 3D 质心 $\mathbf{X}_i$ 用当前位姿投影回图像"作为 Kalman 滤波的**先验**，而不是假设匀速。这是"SLAM 位姿反馈进感知关联"的闭环。
2. **存在性用 log-odds 递推而非阈值单帧判决**：单帧 $\Delta d$ 抖动大，递推到 log-odds 上才能既快删又抗噪。
3. **标签用贝叶斯后验而非投票**：后验低到阈值以下的物体点被直接移除，抑制瞬时误分类。

### 1.3 信息流 / 架构图

```
 RGB-D / LiDAR + IMU
        │
        ▼
 ┌───────────────────────────────┐
 │ 几何层  SuperOdometry         │ ──► P_t = T_WB·T_BC  (SE(3))   @10 Hz
 │ 位姿 + 稠密彩色 3D 重建         │ ──► 稠密彩色点云
 └───────────────────────────────┘
        │
        ├──────────────► ┌──────────────────────────┐
        │                │ 2D 感知 GroundingDINO+SAM2│ ──► 2D mask/label @1 Hz
        │                └──────────────────────────┘
        ▼
 ┌─────────────────────────────── 实例层 ───────────────────────────────┐
 │  ① 混合跟踪状态 S_i(t)=[c, s, ċ] ∈ R^6                              │
 │  ② 预测质心 ĉ_i = π(K·P_t⁻¹·X_i)  ──► Kalman 更新 ──► 实例 ID I_t    │
 │  ③ 几何一致性:  Δd = d_proj − D(u)                                  │
 │        |Δd|≤τ_ε → Observable      (更新语义)                        │
 │        Δd >  τ_ε → Unobservable   (点被遮挡/在观测面之后)             │
 │        Δd < −τ_ε → Disappeared    (点在观测面之前 → 已消失)           │
 │        └─► log-odds 递推 ──► 剪枝旧内容                              │
 │  ④ 贝叶斯语义融合 P(L_j=c|z_1:t) ∝ P(z_t|L_j=c)·P(L_j=c|z_1:t−1)    │
 └──────────────────────────────────────────────────────────────────────┘
        │
        ▼
 ┌───────────────────────────────┐
 │ 拓扑层 4D 场景图 G=(V,E_s,E_t) │ @5 Hz   E_s: on/beside/under 等谓词
 └───────────────────────────────┘          E_t: 跨时间轨迹
        │
        ▼
 子图序列化为文本 ──► VLM (Gemini 2.0 Flash) ──► <answer>ID</answer>
        │
        └─► 从 M_t 取该 ID 的 3D 质心 X_j ──► 导航 waypoint
```

---

## 2 · 数学核心

📌 **Napkin Formula**

> **点的存在性 = log-odds 递推上的 $\mathrm{sign}(\Delta d)$ 累积；点的语义 = 混淆矩阵加权下的贝叶斯后验——二者共用同一个 $\Delta d$。**

### 2.1 问题分解

**目标**：给定当前观测 $Q_t=\{C_t,D_t\}$ 与已有地图 $\mathcal{M}_{t-1}$，估计位姿 $P_t$、实例 ID $\mathcal{I}_t$ 与更新后地图 $\mathcal{M}_t$。

$$P(\mathcal{I}_t,\mathcal{M}_t,P_t\mid\mathcal{M}_{t-1},Q_t)$$

**链式分解**：

$$=\underbrace{P(P_t\mid\mathcal{M}_{t-1},Q_t)}_{\text{pose estimation (geometric)}}\times\underbrace{P(\mathcal{I}_t\mid\mathcal{M}_{t-1},Q_t,P_t)}_{\text{spatio-temporal instance association}}\times\underbrace{P(\mathcal{M}_t\mid\mathcal{M}_{t-1},Q_t,P_t,\mathcal{I}_t)}_{\text{online map update}}$$

**直觉**：位姿先行（几何）、身份随后（关联）、地图最后（更新）——三层结构与概率分解一一对应，这也是"几何层→实例层→拓扑层"顺序的数学理由。

### 2.2 位姿与观测

$$P_t=\mathbf{T}_{WC}^{(t)}=\mathbf{T}_{WB}^{(t)}\cdot\mathbf{T}_{BC}$$

$\mathbf{T}_{WB}$ 为 body 在世界系的位姿，$\mathbf{T}_{BC}$ 为固定外参。

### 2.3 混合跟踪状态

$$\mathbf{S}_i(t)=[\mathbf{c}_i(t)^\top,\ \mathbf{s}_i(t)^\top,\ \dot{\mathbf{c}}_i(t)^\top]^\top \in \mathbb{R}^6\ (\text{含尺度速度则 }\mathbb{R}^8)$$

$\mathbf{c}_i=[x,y]^\top$ 为 2D 像面质心，$\mathbf{s}_i=[w,h]^\top$ 为框宽高，$\dot{\mathbf{c}}_i$ 为像面平移速度。

$$\hat{\mathbf{c}}_i(t)=\pi(\mathbf{K}\cdot P_t^{-1}\cdot\mathbf{X}_i)$$

$\mathbf{X}_i$ 是地图中该实例的 3D 质心，$\pi(\cdot)$ 为投影。这是**用几何先验替换匀速先验**的关键式。

$$\hat{\mathbf{S}}_i(t)=\mathbf{F}\mathbf{S}_i(t-1)+\mathbf{w}_t,\quad \mathbf{w}_t\sim\mathcal{N}(0,\mathbf{Q})$$

### 2.4 几何一致性 / 存在性

$$\Delta d=d_{proj}-D(\mathbf{u}),\quad d_{proj}=\|\mathbf{T}_{CW}\mathbf{X}_k\|_z,\quad \mathbf{u}=\pi(\mathbf{X}_k)$$

$$s_k^{(t)}=\begin{cases}\text{Observable}&\text{if }|\Delta d|\leq\tau_\epsilon\\ \text{Unobservable}&\text{if }\Delta d>\tau_\epsilon\quad(\text{Point behind surface})\\ \text{Disappeared}&\text{if }\Delta d<-\tau_\epsilon\quad(\text{Point in front of surface})\end{cases}$$

$$L(o_k\mid Q_{1:t})=L(o_k\mid Q_{1:t-1})+\text{logit}\,P(o_k\mid Q_t),\qquad L(n)=\log\frac{n}{1-n}$$

**直觉**：$\Delta d>0$ 表示地图点比传感器看到的表面更远 → 被遮挡（Unobservable，**不应惩罚**）；$\Delta d<0$ 表示地图点悬在观测面之前 → 它所在的东西没了（Disappeared，**应惩罚剪枝**）。这个不对称正是抗遮挡的核心。

### 2.5 贝叶斯语义融合

$$P(L_j=c\mid z_{1:t})=\eta\cdot P(z_t\mid L_j=c)\cdot P(L_j=c\mid z_{1:t-1})$$

$P(z_t\mid L_j=c)$ 取检测器混淆矩阵。仅在 $s_k=\text{Observable}$ 的点上做该更新，后验过小的物体点被移除。

### 2.6 场景图边

$$\text{On}(A,B)\iff(z_{min}^{A}\approx z_{max}^{B})\land(\text{IoU}_{xy}(\mathcal{B}_A,\mathcal{B}_B)>\gamma)$$

空间边由类别相关几何谓词（on / beside / under）建立，时序边由 $\mathcal{I}_t$ 结果连接跨时刻节点、刻画轨迹。

---

## 3 · 带数字走一遍（玩具设定，数值为演示自造）

设 $\tau_\epsilon=0.10$ m，反传感器模型取 $P(o_k|Q_t)=0.9$（Observable）/ $0.5$（Unobservable）/ $0.1$（Disappeared），则 $\text{logit}(0.9)=\ln 9\approx+2.197$，$\text{logit}(0.5)=0$，$\text{logit}(0.1)\approx-2.197$。

**场景**：地图点 $\mathbf{X}_k$ 属于一把椅子，其初始 log-odds $L_0=0$（$P=0.5$）。

| 帧 | 情形 | $d_{proj}$ | $D(\mathbf{u})$ | $\Delta d$ | 判定 | $\Delta L$ | 累计 $L$ | $P(o_k)$ |
|---|---|---|---|---|---|---|---|---|
| t=1 | 正常观测 | 2.00 | 1.95 | +0.05 | Observable | +2.197 | 2.197 | 0.900 |
| t=2 | 正常观测 | 2.00 | 1.92 | +0.08 | Observable | +2.197 | 4.394 | 0.988 |
| t=3 | **有人挡在椅前** | 2.00 | 1.20 | **+0.80** | Unobservable | 0 | 4.394 | 0.988 |
| t=4 | 椅前恢复空旷 | 2.00 | 1.98 | +0.02 | Observable | +2.197 | 6.591 | 0.9986 |
| t=5 | **椅子被搬走，看到后墙** | 2.00 | 3.50 | **−1.50** | Disappeared | −2.197 | 4.394 | 0.988 |
| t=6 | 椅子仍未回来 | 2.00 | 3.48 | −1.48 | Disappeared | −2.197 | 2.197 | 0.900 |
| t=7 | 椅子仍未回来 | 2.00 | 3.52 | −1.52 | Disappeared | −2.197 | **0.000** | **0.500** |

**读法**：第 3 帧的人体遮挡**没有**让椅子丢身份（$L$ 不动，正是 Unobservable 分支的意义）；连续 3 帧"看到后墙"才把 $L$ 打回原点、触发剪枝。这就是"抗遮挡 + 抗过期"之间的取舍旋钮——$\tau_\epsilon$ 越小删得越快、也越容易被深度噪声误删。

**实例关联玩具示例**：地图中实例 $\mathbf{X}_i=(3.0,\,1.0,\,0.8)$，当前位姿把相机推到 $\mathbf{X}_i$ 正前方，投影得 $\hat{\mathbf{c}}_i=(640,360)$；本帧 SAM2 给出一个质心在 $(646,357)$、尺寸近似相同的 mask，IoU 远超阈值 → 判定为同一实例，沿用旧 ID；若本帧检测质心在 $(200,700)$ 且与所有历史轨迹的空间距离都过远，则分配新 ID。**关键在"旧 ID 是靠 3D 投影找回来的，不是靠 2D 匀速外推"**——自车急转时 2D 外推会失效，3D 投影不会。

---

## 4 · 工程视角

**论文报告的吞吐（Sec. V-H "Runtime and Memory"）**：

| 模块 | 报告频率 |
|---|---|
| 位姿估计（SuperOdometry） | 10 Hz（"consistent 10 Hz output"） |
| 2D 实例分割（GroundingDINO+SAM2） | 1 Hz（"due to the heavy inference requirements"） |
| 3D mapping | 3 Hz |
| 4D 场景图更新 | 5 Hz |

**硬件配置（论文原文）**：定制麦克纳姆轮移动平台；Livox Mid-360 LiDAR（360°×59° FOV）；360° 全景相机；软件时间戳对齐；Intel i9-14900H CPU + NVIDIA RTX 4090 Laptop GPU（16GB VRAM）；"All computations … run onboard in real-time"。

**未报告项（严禁外推）**：
- 单模块 **latency**：论文未报告（只给 Hz，不给 ms）。
- **内存占用**：论文未报告（虽然小节标题含 "Memory"，正文只给吞吐；16GB VRAM 是硬件型号参数而非实测占用）。
- **功耗 / 网络带宽 / VLM 调用延迟**：论文未报告。
- **CPU/GPU 占用率**：论文未报告。

**Trade-off 解读（可直接落地的三条）**：

1. **1 Hz 感知 vs 10 Hz 位姿的异步是架构的必然**，不是优化不足。想提频只能换更小的分割模型，代价是开放词汇质量——这是被显式接受的设计折衷。
2. **瓶颈在感知端（1 Hz），不在几何端（10 Hz）**。所以系统鲁棒性的工程抓手是"位姿别漂"（决定 3D 投影先验质量）与"地图别乱删"（决定 $\tau_\epsilon$ 标定），而不是"分割别停"。
3. **全 onboard 是硬约束**：VLM 交互必须走子图序列化的**文本**通道（而非视频/点云），否则 16GB VRAM 与实时性都撑不住。这解释了 §2 §2.6 场景图存在的工程理由——它本质是一个**给大模型的降维压缩接口**。

---

## 5 · 数据与评测

### 5.1 评测设置

- **公开 benchmark**：**ScanNet**（class-level 语义分割 Table II；instance-level 分割 Table III）。
- **感知基座**：GroundingDINO [12]（语言引导检测）+ SAM2 [21]（实例分割），零样本。
- **VLM**：Gemini 2.0 Flash [29]。
- **实机实验**：10 分钟、30m × 20m 室内区域；人为引入 3 个消失物体（plant、trash can、chair）与 3 个新增物体（bucket、cart、safety sign）。
- **消融场景**：41 个标注物体。
- **对比方法**：class-level 对 ConceptFusion [7]、NACLIP-3D [6]、Trident-3D [26]、RayFronts [1]、ConceptGraphs [5]、HOV-SG [30]；instance-level 对 HOV-SG、ConceptGraphs；变化检测对 Khronos [25]、DualMap [8]。
- **指标**：mIoU / f-mIoU / Acc（class-level）；mAP50 / mAP25（instance-level）；Object Detection Recall 与 Change Detection Recall（实机）；Precision/Recall/F1（消融）。其中 Detection Recall 的 TP 判定要求 **3D IoU > 0.1、质心距离 < 0.3 m、且语义标签正确**。

### 5.2 关键数字（逐字照抄）

**Class-level（ScanNet, Table II）**，SuperMap（Ours）行：`27.42 43.50 55.48 | 22.61 29.10 33.00`（左为 Without Background，右为 With Background，各为 mIoU / f-mIoU / Acc）。正文表述为："achieves a competitive accuracy of **55.48%**"，"slightly lower (**1.32%**) than the point-feature fusion method RayFronts"（RayFronts 对应行 `41.29 46.42 56.76 | 32.29 39.04 49.15`）。

**Instance-level（ScanNet, Table III）**：

| 方法 | Chair mAP50/25 | Window mAP50/25 | Refrigerator mAP50/25 | Sofa mAP50/25 | Door mAP50/25 |
|---|---|---|---|---|---|
| HOV-SG | 4.58 / 4.73 | 0.00 / 0.00 | 0.00 / 0.00 | 30.00 / 31.25 | 9.70 / 10.40 |
| ConceptGraphs | 0.00 / 2.33 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| **SuperMap** | **63.76 / 74.72** | **42.20 / 67.92** | **62.50 / 62.50** | **33.35 / 83.35** | **10.00 / 25.00** |

**变化检测（Table IV，实机）**——列顺序为新增 Buc./Cart/Sign 与消失 Plant/Trash/Chair：

| 方法 | 任务 | Buc. | Cart | Sign | Plant | Trash | Chair |
|---|---|---|---|---|---|---|---|
| Khronos | Detect. | – | – | – | – | – | – |
| DualMap | Detect. | 0.000 | 0.000 | 0.000 | 0.000 | 0.310 | 0.000 |
| **SuperMap** | Detect. | 1.000 | **0.262** | 0.583 | 0.755 | **0.434** | 1.000 |
| Khronos | Change | – | – | – | – | – | – |
| DualMap | Change | 0.553 | 0.527 | 0.507 | 0.561 | 0.642 | 0.449 |
| **SuperMap** | Change | 1.000 | 0.622 | 0.790 | 0.865 | 0.679 | 1.000 |

论文对 DualMap 的评述值得记：其"消失区间 ~0.5 的 recall 是数学假象——只因一开始就没检测到该物体"。Khronos 因"latent semantic inference bottlenecks 导致显著掉帧与语义 mask 质量退化"而无法给出稳定 3D 结果（用 `–` 表示）。

**消融（Table V，41 物体）**：

| 配置 | Precision | Recall | F1 |
|---|---|---|---|
| W/o 2D Tracker | 0.7787 | 0.4595 | 0.5780 |
| W/o Semantic Fusion | 0.7929 | 0.3870 | 0.5201 |
| W/o Geometric Consistency Update | 0.8189 | 0.4448 | 0.5764 |
| **All (proposed)** | **0.8677** | **0.4955** | **0.6308** |

**注意 recall 的绝对量级**：全系统 Recall 也只有 **0.4955**。这不是笔误，而是他们自己设定的严格 TP 判据（3D IoU>0.1 ∧ 质心距<0.3 m ∧ 标签正确）下的结果——引用时务必带上判据，否则会被误读为"效果差"。

---

## 6 · 能力与失败模式

**能做**（均有论文对应证据）：

- 实时 onboard 全流程（10/1/3/5 Hz 分层吞吐，实机验证）。
- 开放词汇 + 实例级：ScanNet instance-level 上对 Chair 达 mAP50 63.76，远超 HOV-SG 的 4.58。
- 短时动态（人走进走出）+ 长时变化（物体被搬走/新增）**同时**处理，且消失物体保持 ID 不变（Fig. 3 的 "Chair 7 disappears between table 1 and chair 4" 案例）。
- 零样本 VLN：在视觉歧义场景中通过空间关系（四块相同白板中按相对顺序选对）与关系检索（白板旁的画 / 冰箱旁的画）完成导航，全部 onboard。
- 结构化场景图提升 VLM 推理：空间逻辑（灭火器 vs 锥桶 vs 植物）与时间逻辑（追溯 bag 的轨迹）均优于原始视频输入。

**不能做 / 会失效**（论文自陈 + 数字推导）：

- **高速动态物体跟踪有限**（Limitation 原文："its performance in tracking highly dynamic objects remains limited"）。
- **依赖预定义 object prompt 列表**，无开放世界自动发现（Limitation 原文），因此"真正新颖环境"不可用。
- **实机 recall 不均**：Cart 检测 recall 仅 **0.262**、Trash **0.434**（Table IV），说明细长/小目标/易遮挡类别仍是短板。
- **class-level 精度非最优**：Acc 55.48 低于 RayFronts 的 56.76（论文自述低 1.32%），其卖点是算力足迹而非绝对精度。
- 与 Khronos、DualMap 的可比性受限：Khronos 在其测试场景中无法产出稳定 3D 结果，Table IV 大面积 `–`，横向比较需谨慎。

### 隐含假设 (Hidden Assumptions)

1. **静态背景假设**：整个存在性判据（Eq. 7–9）建立在"地图点不动，动的一定是错的"之上。世界系里真正在动的物体（人、手推车）会被判成 Disappeared 并被剪枝——这正是"短时动态"能力与"高速动态跟踪有限"局限的同一个根源。
2. **深度观测有效且已被正确配准到像素**：$D(\mathbf{u})$ 假设 LiDAR/深度能给到该像素的可靠深度。对玻璃、镜面、远距离稀疏 LiDAR 回波，$\Delta d$ 是噪声驱动的随机量。
3. **位姿先验足够准**：3D-to-2D 投影（Eq. 5）与深度投影（Eq. 7）都以 $P_t$ 正确为前提；SLAM 漂移会同时污染关联与存在性判定，且两种错误会互相掩盖。
4. **检测器混淆矩阵已知/可估**：Eq. 10 中的 $P(z_t\mid L_j=c)$ 被当作给定量，但论文未说明其如何标定。
5. **单趟在线、单会话**：没有多会话/终身建图机制；地图是增量的、不可跨次重启合并（论文未涉及）。
6. **空间关系是有限谓词集**：$E_s$ 由类别相关几何谓词（on / beside / under）生成，关系表达力受限于谓词表。
7. **VLM 会按要求格式作答**：路点生成假设 VLM 稳定输出 `<answer><answer/>` 内的合法实例 ID；解析失败路径论文未讨论。

---

## 7 · 与相关工作对比

**能力清单（Table I 逐项照抄，✓ / ✗ 均按原文）**：

| 方法 | 类别 | 实时 | 开放词汇 | 实例级 | 短时动态 | 长时动态 | 场景图 |
|---|---|---|---|---|---|---|---|
| HOV-SG [30] | 语义建图 | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ |
| ConceptGraphs [5] | 语义建图 | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ |
| RayFronts [1] | 语义建图 | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| OpenScene [16] | 语义建图 | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| OpenMask3D [28] | 语义建图 | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| SeeGround [11] | 语义建图 | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Kimera [24] | 语义 SLAM | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| OVO-SLAM [15] | 语义 SLAM | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Khronos [25] | 语义 SLAM | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| **SuperMap (Ours)** | 语义 SLAM | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |

**叙述性差异**（论文原文要点）：
- **OpenScene / OpenMask3D / SeeGround**：离线假设完整扫描 → 不适在线。
- **LERF / LangSplat**：辐射场 + CLIP 特征灵活查询，但算力上不实时。
- **RayFronts**：唯一在 class-level 精度上压过 SuperMap 的在线方法（56.76 vs 55.48），但无变化检测、无实例级 3D 语义。
- **Kimera**：实时且有场景图，但闭集 CNN 分割，泛化不了新类。
- **ConceptGraphs / HOV-SG**：需先离线重建再上 SAM/CLIP，分钟到小时级。
- **CLIO**：实时开放词汇场景图，但缺时空能力。
- **Khronos**：唯一同时覆盖短时+长时的先前工作，但闭集、无实例级跟踪、且难以实时。
- 论文自述其定位：「to the best of our knowledge, SuperMap is the first real-time, spatio-temporal, open-vocabulary, and instance-level object mapping framework that effectively handles both short-term and long-term dynamic objects.」

**🎤 面试 Tip**：如果被问"SuperMap 相对 ConceptGraphs / Khronos 到底强在哪"，不要只答"更强"。标准答法是**沿能力清单的六个正交维度作答**：ConceptGraphs 强在开放词汇与场景图但**离线**（分钟~小时），Khronos 强在**短时+长时覆盖**但**闭集、无实例级、非实时**；SuperMap 的贡献是把这六格一次性填满，代价是 class-level 精度让出约 1.3 个点、以及必须预先给定 object prompt 列表。**主动说出代价，比只报优点更像读过论文的人。**

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-15)

**仓库状态核查**：论文全文**未出现任何 `github.com` 链接**。正文中出现的 "Report GitHub Issue / Submit in GitHub" 属于 arXiv HTML 页面自身的 UI 元素，不是论文给出的仓库；唯一给出的外部地址是项目主页 `superodometry.com/supermap`（纯文本、非可点击仓库链接）。**结论：无 repo 信号，官方 repo 未在论文中给出，因此以下 pitfall 由 §6 失败模式 + §2 方法约束推导，未经 issue 验证。**

- **Pitfall 1 · 新类别静默失败（源自 Limitation "relies on a pre-defined list of object prompts" + 2D 感知模块 = 文本提示驱动的 GroundingDINO）**
  机制链：2D 感知 → 文本 prompt → 无 prompt 则零检测 → 实例层无 tracklet 可建 → 4D 场景图无对应节点 → VLM 查询返回空。**失败形态是"不报错、只是答不出"**，这在长跑部署里极难察觉。工程对策：把 prompt 列表当成必须版本化的配置文件，并在部署期配一个"检测覆盖率监控"（每帧 mask 面积占比骤降即告警）。

- **Pitfall 2 · 快速逼近的物体会被系统当成"已消失"并剪掉（源自 §6 "tracking highly dynamic objects remains limited" + Eq. 9 的 Disappeared 分支 $\Delta d<-\tau_\epsilon$）**
  机制链：物体朝相机运动 → 其地图点 $d_{proj}$ 小于传感器在该像素看到的深度 → $\Delta d<-\tau_\epsilon$ → 连续帧 log-odds 递减 → 点被剪枝 → 分割只有 1 Hz，两次分割之间该物体已位移较大 → 重新检测时按新 ID 建 tracklet → **同一物理物体反复换 ID**。这不是调参能消除的，因为 Eq. 9 的三分支本身把"运动"和"消失"归到同一符号上。工程对策：对已知的 movers（人、推车）先做 2D 层动态剔除，再让其进入几何一致性判定。

- **Pitfall 3 · $\tau_\epsilon$ 与稀疏 LiDAR 的像素级深度查询耦合（源自 Eq. 7 的 $D(\mathbf{u})$ 与硬件 Livox Mid-360）**
  机制链：$\Delta d = d_{proj}-D(\mathbf{u})$ 假设逐像素有可靠深度；Livox Mid-360 是稀疏非重复扫描，$\mathbf{u}=\pi(\mathbf{X}_k)$ 处的 $D(\mathbf{u})$ 需要投影插值或邻域查找 → 在远距离/边缘/玻璃反光处取到错值 → $\Delta d$ 随机化 → 既可能误删真物体（假 Disappeared），也可能误留已搬走的物体（假 Observable）。**$\tau_\epsilon$ 的"最优值"随传感器与场景变化，论文未给出其取值。** 工程对策：把 $\tau_\epsilon$ 与深度 $D$ 的方差绑定（$\tau_\epsilon \propto \sigma_D(d)$），而非用常数。

- **Pitfall 4 · 标签后验依赖未标定的检测器混淆矩阵（源自 Eq. 10 中 $P(z_t\mid L_j=c)$ 被当作给定量）**
  机制链：贝叶斯语义融合要更新 $P(L_j=c)$，就需要 $P(z_t\mid L_j=c)$；论文未说明该矩阵如何获得。若用均匀/单位矩阵近似，Eq. 10 退化为"帧数投票"，瞬时误分类不再被抑制——而"抑制瞬时误分类"正是 §6 中 Semantic Fusion 消融（W/o Semantic Fusion 的 F1 掉到 0.5201 vs 全系统 0.6308）所依赖的能力。

---

[← Back to Spatio-Temporal SLAM / VLN README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2608.22896 -->
