[//]: # "<!-- ontology-5axis
problem: tracking
representation: n/a
sensor: multi-modal
paradigm: geometric
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# 轮廓误差：面向 3D 多目标跟踪评估的自我中心匹配 (Contour Errors: Ego-Centric Matching for 3D Multi-Object Tracking Performance Evaluation)

> **发布时间**：arXiv 2506.04122，v4 2026-07-22（初版 2025-06）
> **论文 / 模型名**：Contour Errors (CE)
> **核心定位**：一句话——3D MOT 评估里的 TP 匹配准则，用"自我中心最近 k 个角到对方盒面的 Hausdorff 型距离"取代 IoU（过度惩罚微小 yaw）和 CPD（完全无视朝向），获得分级的朝向敏感度。

导语：开放环 3D MOT 评估中，matching criterion 直接决定哪些 GT–Pred 对被算作 TP，从而决定 DetA。IoU 在 3D 体积交叠下对微小 yaw 极其敏感（功能上正确的匹配被判 FN），CPD 则对朝向完全免疫（90° 反向也能过）。本文提出 CE，在 ego-centric 参考系里只比较靠近自车的 k 个包围盒角点，落在 IoU 与 CPD 两个极端之间，并给出可调的朝向敏感度。

## X-Ray 开场

IoU 把 2D 交并比扩到 3D 体积后，车体几度的 yaw 偏移就让体积交叠跌破 0.7；CPD 只看中心点，预测框转了 90° 依然 TP——两者都无法从"自车视角"度量误差。CE 的做法是：在每帧取 GT 和 Pred 各自离 ego 最近的 k 个角点（2D k=3，3D k=6），算这些角点到对方盒面的最近距离，双向取 max，低于阈值即匹配。对 spatial AI 研究者意味着：**matching criterion 本身是可设计的几何量**，评估阶段的 ego-centric 重加权不需要改 tracker，就能改变帧级 DetA 的量测结果。

## 📍 研究全景时间线

```
2012 ────── 2020 ────────── 2023 ────────── 2024 ────────── 2025 ──────────── 未来
KITTI      nuScenes        GIoU/DIoU       Ego-centric      CE (本文)          threshold-
IoU≥0.7    CPD≤2.0m        CIoU/HD         加权指标          ego-centric        integrated
           + HOTA协议      作为评估对照     EC-IoU 等         k-nearest          mHOTA /
                           (多为训练损失)  (reweight)        corner 匹配        differentiable
                                                                              CE loss
   └─ 判别器：物体局部几何 ─┘        └─ 判别器：引入 ego 视角 ─┘
```

**本文位置**：它不发明新的 tracker，也不改检测器，而是在 *评估协议层* 重新定义 matching gate。承上（IoU/CPD 的互补失效）启下（distance-dependent 阈值、threshold-integrated mHOTA、CE 作可微损失）。

**本文局限**：单数据集（nuScenes val）、单 tracker（AB3DMOT）、固定阈值、无 closed-loop / planner 验证；作者自己在 §V 承认"更高 mHOTA 不等于更好准则"。

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| k-nearest corner selection | box corners、ego center | $G'_i, P'_j$（各 k 个角） | 仅评估期；按 ego 距离排序取前 k |
| point-to-surface distance | 角点 + 对方盒面 | 最近欧氏距离（closed-form $\mathcal{O}(1)$/角） | 仅评估期 |
| bidirectional max（Eq.1） | $d_{P\to G}$、$d_{G\to P}$ | $E(G_i,P_j)$ | 仅评估期 |
| Hungarian assignment | 距离矩阵 $D=[d_{ij}]_{n\times m}$ | 一对一 GT–Pred 匹配 | 仅评估期 |
| HOTA 协议 | TP/FP/FN + track IDs | mHOTA / DetA / AssA | 仅评估期 |

关键：**tracker 全程固定，只改评估期匹配准则**（论文明确"the tracker is held fixed throughout all experiments"），因此所有差异都归因于 matching criterion。

### 1.2 关键机制

**⚡ Eureka Moment**：把 Hausdorff 距离从"稠密轮廓/点云"搬到"稀疏包围盒角点"，并只取**离 ego 最近的 k 个角**——因为遮挡的远侧面本来就该被忽略，而近侧面恰好是安全相关的碰撞检查面；k 的选择对应典型双面可见几何（2D 两面=3 角，3D 两面=6 顶点）。

两个设计锁死：
- **双向 max**：只用 GT→Pred 会给"Pred 是 GT 的极小子集"打 0 误差（漏掉 gross over-detection）；只用 Pred→GT 会漏掉尺寸高估。双向 max 同时惩罚 under/over-estimation。
- **k 的取值**：2D k=3 是最少能同时捕获平移+yaw 的角数（同一边上 2 个角无法测 yaw）；3D k=6 对应"车尾+一侧"双面可见的 6 个顶点。k=8 时 CE 退化为 object-centric 对称 Hausdorff（论文 Figure 6(b) 的对照点）。

### 1.3 信息流 ASCII 图

```
每帧 t:
  GT boxes {G_i}  ──┐
  Pred boxes {P_j} ──┤
  ego center ────────┤
                     ▼
        [按 ego 距离排序，各取 k 近角]
         2D: k=3    3D: k=6
                     ▼
   for each (G_i, P_j):
     d_P→G = max_{p∈P'_j} min_{x∈Surface(G_i)} ||p−x||
     d_G→P = max_{g∈G'_i} min_{y∈Surface(P_j)} ||g−y||
     E = max(d_P→G, d_G→P)
                     ▼
        距离矩阵 D[n×m] → Hungarian 一对一
                     ▼
     E ≤ τ_E ? → TP : (未匹配 Pred=FP, 未匹配 GT=FN)
                     ▼
           HOTA 协议 → DetA, AssA, mHOTA
```

## 2 · 数学核心

📌 **Napkin Formula**：双向、最近 k 角、角→盒面、取 max。

$$\boxed{\;E(G_i,P_j)=\max\!\Big(\underbrace{\max_{p\in P'_j}\min_{x\in X_i}\|p-x\|}_{d_{P\to G}},\ \underbrace{\max_{g\in G'_i}\min_{y\in Y_j}\|g-y\|}_{d_{G\to P}}\Big)\le \tau_E\;}$$

**目标**：给每个 GT–Pred 对一个标量"轮廓失配度"，低于 $\tau_E$ 判 TP。
**变量**：
- $G_i, P_j$：GT / Pred 包围盒；$G'_i\subseteq G_i,\ P'_j\subseteq P_j$ 是离 ego center 最近的 k 个角（2D k=3，3D k=6）；
- $X_i, Y_j$：GT / Pred 盒的**表面**（不是角点集——这是与经典 HD 的关键差别）；
- $\|\cdot\|$：欧氏距离；每个角到对方表面的最近距离闭式 $\mathcal{O}(1)$ 计算。

**直觉**：把每个选中角想成以它为球心、与对方盒面相切的球，半径就是该角到对方表面的距离；双向取最大 = "最坏的那个近侧角偏了多远"。k=8 时 $G'_i=G_i, P'_j=P_j$，CE **精确退化为对称 Hausdorff**；k 越小，远侧面噪声影响越小。

**与 HOTA 的连接**：$\text{mHOTA}=\frac{1}{40}\sum_{r}\sqrt{\text{DetA}(r)\cdot\text{AssA}(r)}$，40 个等距 recall 级。匹配准则只改 TP 集合 → 主要改 DetA。

## 3 · 带数字走一遍（玩具设定，非论文实验）

**设定（2D 玩具，明确自造）**：ego 在原点；GT car 4.6×1.9 m，中心 (10, 0) m，朝向 +x。四角：(7.7, ±0.95), (12.3, ±0.95)。Pred 同中心，绕 z 轴 yaw = 30°。k=3 选离 ego 最近的三个角（rear 面两角 + 一个 front 角）。

**角点位移估算**：角到中心半径 $r=\sqrt{2.3^2+0.95^2}\approx 2.49$ m；30° 旋转 → 弧长 $\approx 2.49\times 0.524\approx 1.30$ m。论文实测"30° yaw 使最近 ego-facing corner 位移 ≈1 m"（4.6×1.9 m 车体），量级一致。

**CE 一侧**：近侧角到 Pred 盒面的最近距离约为位移的一部分（角可能正好落在 Pred 盒面上，距离更小），整体落在 $\tau_E=2.5$ m 内 → **TP**。
**IoU 一侧**：30° 旋转在 3D 体积交叠上急剧下降，通常跌破 0.7 → **FN**。
**CPD 一侧**：中心重合，CPD = 0 → **TP（且对 90° 反向也无感）**。

结论：同一对几何，CE 判 TP、IoU 判 FN、CPD 判 TP 但"瞎"。这正是论文 Table III 高 yaw 段 CE 11 次失败 vs IoU 50–63 次 vs CPD 8 次的微观来源。**以上数值为玩具演示，不是论文实测。**

## 4 · 工程视角

| 指标 | 论文报告值 |
|---|---|
| 单对 GT–Pred 匹配耗时（CE k=3, 2D） | 380 µs |
| 单对（CE k=6, 3D） | 592 µs |
| 单对（HD k=8, 3D） | 544 µs |
| 单对（3D IoU） | 377 µs |
| 单对（CPD） | 6 µs |
| 单对（GIoU/DIoU/CIoU） | 549–644 µs |
| 单对（连续 Hausdorff, s=100） | 2887 µs（约 5× 慢） |
| vs HD 的相对开销 | ≈9%（来自按 ego 距离排序选 k 角） |
| 测量样本 | 2000 nuScenes GT–Pred pairs |

- **复杂度**：CE 为 $\mathcal{O}(k\cdot n_e)$，3D IoU/GIoU 为 $\mathcal{O}(n_v^2)$，连续 Hausdorff 为 $\mathcal{O}(s^2)$。CE 与 3D IoU 同数量级。
- **端到端 FPS / VRAM / 硬件型号**：**论文未报告**。所有 µs 数字是 per-pair wall-clock，不是整条评估管线吞吐。
- **部署约束推演**：CE 成本可忽略于一个 perception cycle；但 Hungarian 是 $\mathcal{O}(n^3)$，GT/Pred 数量大时匹配阶段才是瓶颈（论文未测）。$\tau_E$ 的选取比算力更关键（见 §6）。

## 5 · 数据与评测

- **数据集**：nuScenes **validation set**；**150** 个 validation scenes。
- **预测源**：**LiDAR-based** predictions，来自 **AB3DMOT** tracker 的输出（不是 raw detections——HOTA 需要 track IDs 算 AssA）。
- **评估协议**：HOTA protocol，主指标 **mHOTA**（40 个等距 recall 级平均）。
- **操作点**：Recall@0.5，car 的 confidence threshold = **0.635**（用 CE 匹配校准后，同一阈值施加到全部 7 个准则）。
- **七种准则**：CE、IoU、GIoU、DIoU、CIoU、CPD、HD。
- **基线阈值（社区既定，非对 CE 调参）**：IoU ≥ 0.7（KITTI/Waymo 车辆标准）、IoU 家族聚合用 ≥ 0.5；CPD ≤ 2.0 m（nuScenes 检测任务）。
- **CE 阈值**（敏感性分析 + BEV 对角线 50% 上界）：pedestrian **0.5 m**、car **2.5 m**、truck **4.0 m**。

**关键实测数字（逐字）**：
- Table I（CE 匈牙利匹配后 vs 基线）：IoU≥0.7 下，**75.2%** ped、**46.7%** car、**42.6%** truck 的 CE 匹配是 CE-only；IoU-valid 但 CE-fail 仅 **&lt;0.1%**（car/ped）。
- Table II（Recall@0.5，car，按 ego 距离）：CE(k=6) TP = 4962 / 8655 / 7029（0–10/10–20/20–30 m），FN = 579 / 3721 / 8014；3D IoU TP = 4960 / 8544 / 6783；CPD TP = 4970 / 8695 / 7069。
- Table III（≤30 m，按 yaw 严重度）：CE(k=6) TP = 2529 / 400 / 1463，FN = 10 / 1 / 11；3D IoU FN = 26 / 13 / 50；CPD FN = 1 / 0 / 7。
- Table IV（car 聚合）：CE(k=6) **mHOTA 0.654**, AMOTA 0.499, AssA 0.982, DetA 0.457, TP 27307, FP 1406, FN 31010；3D IoU mHOTA **0.633**；CPD mHOTA **0.664**（最高但最 permissive）；HD mHOTA 0.654（与 CE 相同，CE TP 多 18）。
- 门控效应分解：DetA $\Delta = 0.047$，AssA $\Delta < 0.01$。
- 阈值饱和：CE 在 $\tau=2.5$ m 达到峰值 mHOTA 的 **98.9%**，$\tau\ge 3.5$ m 完全饱和。
- 角数消融：$k\in\{1..8\}$ 下 DetA/AssA 变化 **&lt; 1.3%**。
- 失败率（yaw 分箱）：CE 低/中/高 = **10/2539 = 0.39%**、**1/401 = 0.25%**、**11/1474 = 0.75%**。
- 时序案例：(a) 25 m 车 IoU 0.56–0.67 全 5 帧 fail，CE 1.60–2.03 m 全 pass；(b) 31.8 m 雨中车 GIoU≥0.5 下 0.06–0.38 全帧 fail，CE 1.73–2.47 m 全 pass。

## 6 · 能力与失败模式

**能做**：
- 保留几乎全部 IoU-valid 匹配（&lt;0.1% 被拒），同时额外接纳大量近轮廓匹配（car 46.7%、ped 75.2% CE-only）。
- 给出 IoU 与 CPD 之间的**分级朝向敏感度**：yaw 高段失败 11 次，IoU 50–63 次，CPD 8 次。
- 对遮挡远侧面鲁棒：只比 k 近角，k=8 时才退化为全局 Hausdorff。
- 对 k 不敏感（DetA/AssA 变化 &lt;1.3%），对 $\tau$ 在 2.5–3.5 m 区间不敏感。

**不能做 / 失败模式**：
- **单面可见时 k=6 会多选 far-side 角**：作者自承"当只有一面可见（如完全并行的车），4 个角可见，k=6 保守地多含 2 个近侧/远侧角"——远侧角带最高估计不确定性，是精度泄漏点。
- **固定 2.5 m 阈值不区分离 ego 距离**：5 m 处和 50 m 处同一容忍度，近距安全关键目标可能被过松放过。
- **mHOTA 可被 permissive 准则欺骗**：CPD 拿最高 mHOTA（0.664），但 90° 反向 CPD=0；论文明确"更高 mHOTA 不总是更好准则"。
- **无 closed-loop / planner 验证**：与下游安全的关系未建立。

### 隐含假设 (Hidden Assumptions)

1. **ego 位姿精确已知、稳定**：k 近角选择依赖 ego center 距离排序；ego 位姿噪声会抖乱选角集合。
2. **目标是长方体（3D cuboid / 2D rectangle）**：CE 定义在"角点—盒面"几何上，点云 / mask / 非矩形目标不直接适用。
3. **朝向对目标有意义**：CE 的朝向敏感度对行人这类 yaw 语义弱的类别意义有限（论文仍用 0.5 m 阈值评了 ped）。
4. **per-frame 独立评估**：CE 每帧独立计算，不改 tracker 状态；AssA 的漂移只来自 TP 集合变化，不是身份持续性变化（论文 §IV-E 明确）。
5. **Hungarian 一对一**：TP 定义为最优分配后的匹配，非贪心/多对一。

## 7 · 与相关工作对比

| 准则 | 几何量 | 朝向敏感 | 过/欠惩罚 | 评估期用法 |
|---|---|---|---|---|
| 3D IoU | 体积交叠 | 极敏感（微小 yaw 崩） | 过度惩罚 | 广泛 |
| GIoU | IoU + 最小包围盒惩罚 | 敏感 | 更严 | 主为训练损失 |
| DIoU / CIoU | IoU + 中心距 / 长宽比 | 敏感 | 更严 | 主为训练损失 |
| CPD | 中心距 | **完全无感**（90° 反向=0） | 欠惩罚 | nuScenes/Argoverse 2 |
| HD | 全角对称 Hausdorff | 敏感 | 远侧噪声放大 | 分割/配准 |
| **CE（本文）** | **k 近角→盒面双向 max** | **分级可调** | 中间 | 评估期匹配 |

论文明确 CE 与 EC-IoU 等 ego-centric 加权指标的区别：后者按"ego 相关性"给检测**加权/重加权**，CE 是**几何地重定义 matching gate**（用 ego-facing contour），不是给分数乘权重。

**面试 Tip**：被问"为什么评估 3D MOT 的 matching criterion 是个研究问题？"——答三段：(1) 它决定 TP 集合，实测主要动 DetA（$\Delta=0.047$）而 AssA 几乎不动（$\Delta<0.01$），所以是帧级检测质量的度量选择；(2) IoU 与 CPD 在 3D 下互补失效（IoU 对 yaw 过严、CPD 对 yaw 全盲）；(3) CE 用 ego-centric k 近角给出中间解，但别只看 mHOTA——CPD 的 mHOTA 最高恰恰因为它最宽松。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-03)

**论文全文未出现任何 `github.com` 链接**（亦无 repo URL / issue 编号可核）。按铁律，以下 3 条 pitfall 由 §6 失败模式 + 方法约束推导，**未经 issue 验证**，不附任何 repo/commit 引用：

1. **【ego 位姿噪声 → 选角抖动】** 由隐含假设 1（ego 位姿精确已知）+ 方法约束（Algorithm 1 第 2 步"按 ego 距离排序取 k 近角"）推导：ego 位姿带噪时，最近 k 角的集合可能在帧间跳变（如 30° 级 yaw 下 5 个角距离接近），导致 CE 值不连续、TP/FP 翻转。工程落地需对选角做滞后/平滑，或改用固定面而非动态 top-k。
2. **【固定 $\tau_E$ 近距过松 → 近距安全目标漏判】** 由 §6 失败模式"固定阈值不区分离 ego 距离"+ 论文 §V "distance-dependent thresholds" 讨论推导：$0\text{–}10$ m 内仍用 2.5 m，等于允许近距目标 2.5 m 轮廓误差，与"更近目标需更可靠"相悖；论文建议 $\tau=1.0$ m（≤10 m）、$4.0$ m（>30 m），但未在实验中验证该分段方案。
3. **【2D k=3 隐含"矩形 box"假设】** 由方法约束"sparse bounding-box corner geometry"+ 隐含假设 2 推导：CE 的角点—表面距离定义依赖轴对齐/朝向矩形；若上游检测器输出非矩形表示（mask、点云簇、BEV occupancy），需重新定义"表面"，直接套用 Algorithm 1 会失真。论文 Table V 的 CE(k=3, 2D)=380 µs 也只在矩形 box 假设下成立。

---
[← Back to tracking README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（本笔记所有表格数字均逐字取自论文 Table I–V / §IV–V；§3 玩具例子为自造演示，已标注）

[//]: # "<!-- source: https://arxiv.org/abs/2506.04122 -->"
