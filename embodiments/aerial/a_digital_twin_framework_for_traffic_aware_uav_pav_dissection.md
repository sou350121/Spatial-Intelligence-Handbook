<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: mono
paradigm: learned
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# 开放交通条件下交通感知型无人机路面巡检的数字孪生框架 (A Digital Twin Framework for Traffic-Aware UAV Pavement Monitoring in Open-Traffic Conditions)

> **发布时间**：2026-07-04（arXiv:2606.20742v2 [cs.RO]，v1 更早）
> **论文 / 模型名**：RDMO-DigitalTwin（Unity DT + 多任务 YOLOv8n）
> **核心定位**：把"车辆/行人临时遮挡路面缺陷"这件事做成一个可复现的 Unity 数字孪生 testbed，并在其中**评估**（而非假设）三种 UAV 恢复策略的 coverage–时间–能量 trade-off。

真机 UAV 路面巡检一旦进入开放交通，缺陷可见性就被动态交通破坏，而实物测试既贵又危险。本文用 Unity 造出一个"交通感知"的仿真闭环——程序化缺陷 + 动态车辆/行人 + NavMesh 自主飞行 + 多任务 YOLOv8n 感知 + 三种遮挡恢复策略——其最有工程价值的结论反而是**反直觉的**：恢复动作并不稳定优于"什么都不做"的 Baseline。

## X-Ray 开场
- **解决什么问题**：现有 UAV 路面巡检要么在受控条件下验证（真机一遇运动和遮挡就掉链子），要么只做路线规划/维护管理，缺少一个把"缺陷生成 + 动态交通遮挡 + 飞行感知 + 恢复决策"统一起来的可复现评估台。
- **提出了什么**：一个 Unity 数字孪生框架，把遮挡显式建模为可观测的**可见度分数 $o_{s,t}$**，据此在线触发 hover / micro-reposition / skip 三种恢复策略，并配一个共享 backbone 的双头 YOLOv8n（检测头 + ROIAlign 子类型头）。
- **对 spatial AI 研究者意味着什么**：它是一个"感知↔决策"耦合的仿真基准样品；核心信号是**策略评估>策略设计**——在仿真里诚实地暴露出"恢复并不总涨 coverage，还会把 mission time 和能耗推高"，这比再报一个 SOTA 检测数字更值得复述。

## 📍 研究全景时间线

```
2019 ────────────────────────────────────────────────────────────────────► 2026
  │              │                │                   │                     │
[Tsai 虚拟坑洞] [Wang 背景重建/   [Silva 多智能体,     [DT 维护应用       [本文 DT testbed]
 合成+真实混合   Unreal 虚拟巡检]  Zhao 路径规划,       路面健康/预测性    统一 traffic-aware
 训练检测器      检测数据增强      Zhong 集群路由]      维护 6-9]         + 恢复策略评估
                                                                    + 多任务 YOLOv8n
                                                                              ▲
                                                                        你在读这里
演进主线：单点数据增强 ──► 系统级巡检架构 ──► 维护数字孪生 ──► 交通感知闭环评估
本文局限：纯合成域、无真机验证、无天气效应、仅三类路面缺陷、恢复策略非自适应（固定 Π）
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| Unity 环境（Blender 建模资产） | 道路网络（街道/交叉口/红绿灯/路牌） | 可飞行域 + 程序化缺陷（single crack / crocodile crack / pothole，图 2） | 无训练；仅构建 |
| 动态交通 | 车辆/行人 agent 定义 | $\mathcal{A}_t$：位置、速度、类别 | 无训练；Unity 内实时仿真 |
| NavMesh 导航 | baked 凸多边形飞行域、目标路段 $\mathcal{S}$ | 全局路径 + 平滑轨迹 | 运行期（NavMeshAgent） |
| 数字孪生决策层 | $o_{s,t}, x_t, \mathcal{M}_t, \Pi$ | 恢复动作选择 | 运行期在线触发 |
| 多任务 YOLOv8n | RGB 顶视帧 | 5 类框 + 3 缺陷子类 | 先在 Balanced Dataset 训，再在 Synthetic Dataset 微调 |
| 子类型头 | P3 特征图上的 ROIAlign 特征 | Single / Crocodile / Pothole | 检测头 40 epoch，子类型头 10 epoch |

关键参数：UAV agent 半径 0.5 m；巡检高度 **6 m / 10 m / 15 m**（低/中/高）；`NavMeshAgent` 速度 5 m/s、角速度 45°/s、加速度 8 m/s²、停止距离 1 m。

### 1.2 关键机制

⚡ **Eureka Moment：把"遮挡"从一个检测失败事件升格为一个可观测的连续状态变量 $o_{s,t}\in[0,1]$**——一旦 $o_{s^*,t}<\tau_o$ 就把它当作决策触发信号，让恢复策略成为"可在线切换的动作"，从而把 coverage / mission time / energy 三者放进同一个可比较的坐标系里。

第二个（次级但漂亮）机制：**一次编码、两处使用**。YOLOv8n backbone 只前向一次产出 P3/P4/P5，检测头用全部金字塔做粗类（Road Defect / Person / Car），子类型头**只借 P3 的高分辨率特征**、经 ROIAlign 取固定尺寸特征来细分缺陷子类——不裁剪原图、不二次跑 backbone。选择 P3 的理由是"小或细的路面缺陷需要最高空间分辨率"。

### 1.3 信息流 ASCII 图

```
Unity 环境
 ├─ 程序化缺陷 (Single / Crocodile / Pothole)
 ├─ 动态交通 (车辆 / 行人)
 └─ 道路网络  S = {s_1..s_N}
        │
        ▼
UAV —— NavMesh 全局路由 + 局部避障 + 巡检模式
        │  RGB 顶视帧
        ▼
多任务 YOLOv8n
 ├─ 检测头  ← P3,P4,P5 ──► Road Defect / Person / Car
 └─ 子类型头 ← ROIAlign(P3) ──► Single / Crocodile / Pothole
        │  缺陷框 + 遮挡 agent 位置
        ▼
DT 决策层：可见度 o_{s,t} → 记忆 M_t
        │  若 o_{s*,t} < τ_o  →  触发恢复
        ▼
恢复策略 Π：Baseline / Hover / Micro / Skip
        │
        ▼
指标：coverage · mission time · energy · recovery ratio
```

---

## 2 · 数学核心

📌 **Napkin Formula：遮挡触发 = `if o_{s*,t} < τ_o → 从 Π 选动作`；训练 = `L_total = L_det + α·L_subtype`。**

**目标**：让 DT 能在运行中根据可见度决定是否/如何恢复，并让感知模型同时产粗类与子类。

**数字孪生形式化**：在离散时刻 $t$，
$$\mathcal{D}_t=\big(\mathcal{S},\mathcal{A}_t,x_t,\mathcal{M}_t,\Pi\big)$$

- $\mathcal{S}=\{s_1,\dots,s_N\}$：路段集合
- $\mathcal{A}_t$：动态 agent 集合，$a_i^t=(y_i^t,\nu_i^t,\kappa_i)$，$\kappa_i\in\{\text{vehicle},\text{pedestrian}\}$
- $x_t=(p_t,h_t,v_t,e_t)$：UAV 状态，$p_t\in\mathbb{R}^2$ 平面位置，$h_t\in\mathbb{R}_{>0}$ 高度，$v_t\in\mathbb{R}_{\ge0}$ 速度，$e_t\in[0,1]$ 电量
- $\mathcal{M}_t=\{m_s^t\mid s\in\mathcal{S}\}$：巡检记忆
- $\Pi$：候选恢复策略集合

**可见度与记忆判定**：
$$m_{s}^{t}=\begin{cases}\texttt{inspected}, & \text{if } o_{s,t}\ge\tau_o\\ \texttt{pending}, & \text{otherwise}\end{cases}$$
当 $o_{s^*,t}<\tau_o$ 时，DT 从 $\Pi$ 激活一个恢复策略（Baseline / Hover / Micro / Skip，见 Table I）。

**恢复动作**：
- Hover：$p_{t+1}=p_t$，静止 $\Delta t_{\text{wait}}$ 等遮挡消散
- Micro：$p_{t+1}=p_t+\delta_t$，$\|\delta_t\|\le d_{\max}$，小位移改善可见性
- Skip：跳过被遮挡段，按预定义路径稍后回访

**训练损失**：
$$L_{\mathrm{total}}=L_{\mathrm{det}}+\alpha L_{\mathrm{subtype}}$$
其中 $L_{\mathrm{det}}$ 为标准 YOLO 检测损失，$L_{\mathrm{subtype}}$ 为三子类上的交叉熵，本文 $\alpha=1.0$（检测与子类等权）。

**直觉**：整套数学的"骨"很轻——真正被形式化的不是网络，而是**决策的状态空间**：谁挡住了路（$\mathcal{A}_t$）、看得见多少（$o_{s,t}$）、记没记住（$\mathcal{M}_t$）、要不要动（$\Pi$）。感知只负责喂 $\mathcal{A}_t$ 和缺陷框。

---

## 3 · 带数字走一遍（玩具设定，非论文数值）

设单段 $s^\ast$，$\tau_o=0.5$，$\Delta t_{\text{wait}}=1$ 步，采样 4 个时刻：

| $t$ | $o_{s^*,t}$ | $o<\tau_o$? | DT 行为 | $m_{s^*}^t$ |
|---|---|---|---|---|
| 0 | 0.90 | 否 | 正常巡检 | inspected（0.90≥0.5） |
| 1 | 0.40 | 是 | 触发 Hover：$p_2=p_1$ | pending |
| 2 | 0.35 | 是 | 车仍未走，继续 Hover | pending |
| 3 | 0.72 | 否 | 遮挡消散，继续巡检 | inspected |

若把 Hover 换成 Skip：$t=1$ 直接跳到下一段，$s^\ast$ 保持 `pending` 直到按路径回来——这解释了论文观察：**Skip 产生非零 recovery ratio，但主要成本是 mission time 与 energy，而非 coverage 收益**。

若把 Hover 换成 Micro：$p_{t+1}=p_t+\delta_t$，$\|\delta_t\|\le d_{\max}$，可能一步就把 $o$ 从 0.40 拉到 0.72，省掉第 2 步的等待——这正是 Micro 在低空有时反超 Baseline 的机制（但会牺牲与目标的贴近度）。

> 损失侧玩具感受：$\alpha=1.0$ 意味着子类错的梯度与检测错的梯度同权。若把 $\alpha$ 调小，检测更稳但子类可能退化；论文只报了 $\alpha=1.0$ 一个点，未做消融。

---

## 4 · 工程视角

| 项 | 数值 | 来源 |
|---|---|---|
| 仿真主机 | AMD Ryzen 5 5600G @3.90 GHz / NVIDIA GeForce GTX 1050 Ti（4 GB VRAM）/ 16 GB RAM @2666 MT/s / 64-bit x64 | 论文 V 节 |
| FPS 测量硬件 | 单张 NVIDIA **T4** GPU（YOLO 变体统一条件） | 论文 V 节 |
| YOLOv8n 模型大小 | 6.0 MB | Table IV |
| YOLOv8n GFLOPs | 8.1 | Table IV |
| YOLOv8n FPS | 273.47（T4） | Table IV |
| YOLOv8n 单帧延迟 | ≈3.66 ms（由 273.47 FPS 换算，**UNVERIFIED**，论文未直接给延迟） | 换算 |
| 训练 epoch | 检测头 40，子类型头 10（early stopping + LR 调度） | 论文 V-B |
| 训练时间 / VRAM / 吞吐 | **论文未报告** | — |
| NavMesh 速度/角速度/加速度/停止距离/半径 | 5 m/s / 45°/s / 8 m/s² / 1 m / 0.5 m | 论文 III-B |
| 最清晰的运行成本 | Hover + 高交通 + 低空：mission time 91.40 ± 118.27 s，能耗 5.08 ± 6.57 % | 论文 V-A |

**Trade-off 读法**：
1. **精度–速度拐点**：mAP@0.5 从 YOLOv8n 0.866 到 YOLOv8m 0.878（+0.012），但 FPS 从 273.47 掉到 39.19、大小从 6.0 MB 涨到 49.6 MB。nano 是"仿真内实时推理"的必然选择——这段是全文最硬的部署论证。
2. **策略成本爆炸**：Hover 在高交通/低空下 mission time 标准差 118.27 s **大于均值 91.40 s**——说明少数拥堵 run 里车辆长时间静止，UAV 被迫原地空等。这是"实时闭环决策"在真实拥堵下的典型长尾风险。
3. **资源约束**：仿真跑在 4 GB VRAM 的 GTX 1050 Ti 上，说明整套 DT（Unity + 推理）本就按"低配可跑"设计；但论文**未报告**峰值 VRAM、Unity 渲染帧率与推理的耦合开销。
4. **实时性约束**：论文明确指出检测需在 Unity 仿真器内"实时运行"，但**未报告**端到端（渲染+推理+决策）的帧预算拆解。

---

## 5 · 数据与评测

### 数据集组成（Table II，逐字）

来自 **六个路面损伤数据集 + 两个 UAV 交通数据集**，统一为三类路面缺陷（Single Crack / Crocodile Crack / Pothole）+ Person + Car：

| Source Dataset | Single | Crocodile | Pothole | Person | Car | Total (boxes) | 图像(Annotated) | 图像(Background) | 图像(Total) |
|---|---|---|---|---|---|---|---|---|---|
| HighRPD [20] | 11,409 | 6,900 | 0 | 0 | 0 | 18,309 | 9,974 | 310 | 10,284 |
| Pothole-Recog. [3] | 108 | 0 | 453 | 0 | 0 | 561 | 111 | 11 | 122 |
| PothRGBD [21] | 0 | 0 | 972 | 0 | 0 | 972 | 871 | 0 | 871 |
| UAPD [22,23] | 3,256 | 0 | 94 | 0 | 0 | 3,350 | 2,146 | 0 | 2,146 |
| UAV-PDD2023 [24] | 10,074 | 603 | 195 | 0 | 0 | 10,872 | 2,403 | 0 | 2,403 |
| RDD2022* [13] | 2,689 | 293 | 86 | 0 | 0 | 3,068 | 1,919 | 482 | 2,401 |
| UAV car detection [25] | 0 | 0 | 0 | 0 | 16,868 | 16,868 | 299 | 0 | 299 |
| Pedestrian recognition [26] | 0 | 0 | 0 | 17,034 | 0 | 17,034 | 215 | 0 | 215 |
| **Merged** | 27,536 | 7,796 | 1,800 | 17,034 | 16,868 | 71,034 | 17,938 | 803 | 18,741 |
| **Balanced** | 24,295 | 24,295 | 24,295 | 24,000 | 23,884 | 120,769 | 42,755 | 3,420 | **46,175** |
| **Synthetic** | 4,435 | 3,134 | 4,665 | 8,376 | 5,333 | 25,943 | 2,235 | 0 | 2,235 |

\* RDD2022 仅取 **China UAV** 子集。类别重映射要点：HighRPD 的 line→Single、block→Crocodile，含 pit 标注的图**丢弃**；UAPD/UAV-PDD2023 的 alligator→Crocodile，longitudinal/transverse/oblique→Single，repair 丢弃；RDD2022 的 D00/D10→Single、D20→Crocodile、D40→Pothole，repair/block 丢弃。标注统一为 Pascal VOC/XML，再导出 YOLO 格式；图像最长边缩到 640 px。

增强（Albumentations）：水平翻转、亮度/对比度、高斯噪声、±15° 旋转；变换后可见面积不足的框删除。

**最终 Balanced Dataset：46,175 张图、120,769 个框、五类**；按**类分层 70%/20%/10%** 划分 train/val/test。

**Synthetic Dataset**：在 DT 仿真内采集的顶视 UAV 画面，含全部五类，用于合成域微调。

### 评测设置与结果

**恢复策略（Table III，coverage %，mean ± std，20 次独立重复；低/中/高交通 × 6/10/15 m）**

| 交通 | 高度 | Baseline | Hover | Micro | Skip |
|---|---|---|---|---|---|
| Low | Low(6m) | 56.00±11.48 | 52.35±11.89 | **60.30±11.81** | 47.45±11.78 |
| Low | Medium(10m) | **84.01±5.72** | 83.59±7.74 | 82.70±10.47 | 79.63±10.64 |
| Low | High(15m) | **82.82±6.79** | 82.45±10.29 | 76.41±8.83 | 77.75±8.12 |
| Medium | Low | 52.37±10.18 | **53.90±11.55** | 53.58±9.26 | 51.71±11.81 |
| Medium | Medium | **84.53±8.15** | 80.43±11.01 | 81.82±7.35 | 81.03±9.10 |
| Medium | High | 75.19±11.42 | **81.98±9.99** | 74.60±10.70 | 75.03±11.52 |
| High | Low | 50.78±10.74 | **54.79±14.08** | 51.80±11.40 | 49.45±11.22 |
| High | Medium | **81.87±11.16** | 81.51±7.98 | 79.13±9.61 | 74.91±12.30 |
| High | High | **78.28±10.47** | 75.53±9.85 | 73.01±15.55 | 76.84±11.03 |

- 高度强烈影响 coverage；**没有任何单一策略在所有条件下占优**。
- 中/高交通、低空：所有策略 coverage 下降（持续车辆遮挡）。
- 成本记录：Hover 在高交通/低空 mission time 91.40±118.27 s、能耗 5.08±6.57 %。

**感知模型（Table IV，三粗类 first-stage 对比；FPS on T4）**

| 指标 | v8n | v8s | v8m | v8l | 11n | 11s | 11m | 11l | 12n | 12s | 12m | 12l |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mAP@0.5 | 0.866 | 0.875 | 0.878 | 0.876 | 0.869 | 0.876 | 0.874 | 0.873 | 0.874 | 0.875 | 0.872 | 0.869 |
| mAP@0.50:0.95 | 0.775 | 0.785 | 0.791 | 0.789 | 0.778 | 0.785 | 0.785 | 0.783 | 0.784 | 0.786 | 0.783 | 0.780 |
| Precision | 0.888 | 0.887 | 0.905 | 0.898 | 0.890 | 0.895 | 0.893 | 0.889 | 0.901 | 0.890 | 0.896 | 0.885 |
| Recall | 0.840 | 0.856 | 0.849 | 0.855 | 0.847 | 0.853 | 0.851 | 0.854 | 0.844 | 0.854 | 0.847 | 0.847 |
| Size (MB) | 6.0 | 21.5 | 49.6 | 83.6 | 5.2 | 18.3 | 38.6 | 48.8 | 5.3 | 18.1 | 38.9 | 51.0 |
| FPS | 273.47 | 97.73 | 39.19 | 22.68 | 263.11 | 92.38 | 35.98 | 32.36 | 166.43 | 63.46 | 26.03 | 18.18 |
| GFLOPs | 8.1 | 28.4 | 78.7 | 164.8 | 6.3 | 21.3 | 67.7 | 86.6 | 6.3 | 21.2 | 67.1 | 88.5 |

→ 选 YOLOv8n（精度几乎不随规模涨，速度/体积代价大）。

**多任务五类模型（在 simulator test split 上评测）**

| 阶段 | mAP@0.5 | mAP@0.50:0.95 | macro F1 |
|---|---|---|---|
| 合成微调前 | 0.7442 | 0.6124 | 0.7666 |
| **合成微调后** | **0.9591** | **0.6450** | **0.9400** |

- 检测头 mAP@0.5：**0.8525 → 0.9738**
- 子类型分支：在匹配的预测缺陷 ROI 上 macro F1 = **0.9973**
- 结论：合成域微调显著提升定位与检测覆盖（混淆矩阵见图 5）。

---

## 6 · 能力与失败模式

**能做**
- 在仿真内检测 5 类：Single Crack / Crocodile Crack / Pothole / Person / Car，并对缺陷做子类细分。
- 用共享 backbone 一次编码（P3/P4/P5）+ P3 ROIAlign 子类型头，保住 YOLOv8n 的实时性。
- 对三种恢复策略在 3×3（交通×高度）网格上做 20 次重复的 coverage/时间/能耗**量化对比**。
- 合成域微调把五类 mAP@0.5 从 0.7442 提到 0.9591。

**不能做 / 失败模式**
- **恢复不总赢**：中/高交通、中/高空下 Baseline 常胜过所有恢复策略（如 High/Medium：Baseline 81.87 vs Hover 81.51 vs Skip 74.91）。
- **Skip 的收益错位**：产生非零 recovery ratio，但主要增加 mission time 与能耗，coverage 增益不显著。
- **Hover 的拥堵长尾**：高交通/低空下 mission time 均值 91.40 s 而 std 118.27 s，车辆停住时 UAV 原地空等。
- **低空普遍吃亏**：所有策略在 6 m 下 coverage 明显偏低（约 47–60%）。
- **只在合成域验证**：模型在 simulator 生成的 test split 上评估，未用真机 UAV 图像验证（作者列为 future work）。
- **缺陷类别只有 3 类**，且全靠程序化生成，形态分布未必覆盖真实病害。

### 隐含假设 (Hidden Assumptions)

1. **可见度 $o_{s,t}$ 是"上帝视角"已知的**：DT 直接持有该真值，而真机上必须从图像估计可见度——这是仿真→现实最大的语义鸿沟。
2. **交通 agent 行为简化**：车辆可以长时间完全静止（正是 Hover 长尾的成因）；真机交通不会这么"配合地卡住"。
3. **环境理想**：无雨、雾、夜间、强阴影；论文明确把天气列为 future work。
4. **顶视、固定相机、晴好光照**：感知分布与真机斜视/姿态抖动差异大。
5. **政策集 Π 固定且非自适应**：$\tau_o$、$\Delta t_{\text{wait}}$、$d_{\max}$ 都是预定义超参，非学出来的（论文把 adaptive policy-selection 列为未来工作）。
6. **电量模型是黑盒标量**：$e_t\in[0,1]$ 只用于统计能耗百分比，未与真实电池化学/风阻耦合。
7. **"inspected 即完成"**：$o_{s,t}\ge\tau_o$ 就把段标记为已检，未验证缺陷是否真的被检出（可见≠可识别）。
8. **子类型头只在 P3 上工作**：假设缺陷足够小/细、且 ROIAlign 后特征足够判别三类。

---

## 7 · 与相关工作对比

| 工作 | 缺陷生成 | 动态交通遮挡 | 自主 UAV 巡检 | 在线恢复策略 | 多任务感知 | 真机验证 |
|---|---|---|---|---|---|---|
| Tsai et al. [17] | 虚拟坑洞场景 | ✗ | ✗ | ✗ | ✗ | 合成+真实混合 |
| Wang et al. [18] | UAV 背景重建+渲染 | ✗ | ✗ | ✗ | ✗ | 数据增强导向 |
| Wang et al. [19] | Unreal 纹理背景 | ✗ | 虚拟巡检 | ✗ | ✗ | 数据增强导向 |
| Silva et al. [3] | ✗ | ✗ | 多智能体架构 | ✗ | ✗ | UAV 图像 |
| Zhao et al. [4] | ✗ | ✗ | 路径规划+拼接 | ✗ | ✗ | — |
| Zhong et al. [10] | ✗ | ✗ | 集群路由 | ✗ | ✗ | — |
| DT 维护类 [6–9] | ✗ | ✗ | ✗ | ✗ | ✗ | 资产级维护 |
| **本文** | **程序化 3 类** | **✓ 车辆+行人** | **✓ NavMesh** | **✓ Hover/Micro/Skip** | **✓ 检测+子类** | ✗（future work） |

**面试 Tip**：被问到"这篇和一般的 UAV 路面检测比强在哪"——答：**它不是又一个检测器，而是一个把"遮挡"变成可评估决策变量的 testbed**；最该复述的结论不是 0.9591 的 mAP，而是"恢复策略在多数条件下打不过 Baseline、且会把时间/能耗推高"这个 trade-off 证据。如果面试官追问"那它有什么用"——答：它把"该不该恢复"这个问题从直觉变成了可量化的 3×3 实验矩阵。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-19)

论文正文以纯文本形式给出项目地址 `https://github.com/EdwinTSalcedo/RDMO-DigitalTwin`。按 atlas 判定规则：**纯文本 URL 不构成可点击的超链接 repo signal**，因此本文档**不引用任何 issue 编号/commit/标题**，也**未做 issue 流验证**。以下 pitfall 由 §6 失败模式 + 方法约束**推导**（未经 issue 验证）：

1. **Hover 策略在"车辆会长时间静止"的仿真交通下必然产生 mission-time 长尾 → 复现时会看到极端离群 run。**
   - 机制：Table I 中 Hover 的动作为 $p_{t+1}=p_t$，即原地等待 $\Delta t_{\text{wait}}$ 直到遮挡消散；而仿真交通允许车辆长时间停滞。
   - 可观测后果：高交通/低空下 mission time 91.40 ± 118.27 s，标准差 > 均值；任何按"平均飞行时间"配置电量/航时的部署假设都会被少数 run 击穿。

2. **NavMesh 全局路径 + 局部避障 + agent 半径 0.5 m 的组合，在窄街与高密度 agent 下会退化为抖动/绕圈，压低低空 coverage。**
   - 机制：全局路径由 baked NavMesh 给出，动态避障交给 `NavMeshAgent` local-avoidance；两者无全局协调，agent 半径固定 0.5 m。
   - 可观测后果：6 m 高度下所有策略 coverage 仅 ~47–60%，与"低空应看得更清"的直觉相反——低空视野窄 + 避障频繁改航向共同造成。

3. **子类型头只吃 P3 + ROIAlign，且仅训 10 epoch、只在合成域评测 → 跨域/小目标子类可能整体塌掉，而仿真内数字仍接近完美。**
   - 机制：$L_{\mathrm{total}}=L_{\mathrm{det}}+\alpha L_{\mathrm{subtype}}$，$\alpha=1.0$；子类型头只用 P3、10 epoch、在 Synthetic Dataset 上评到 macro F1 0.9973。
   - 可观测后果：0.9973 几乎饱和，方法是"在目标域上评目标域"，一旦换真机域，Single vs Crocodile 这类细粒度区分最可能先崩，而 DT 仿真里看不出预警。

---

[← Back to Spatial Intelligence Handbook](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文（v2，含 Table I–IV）· 未在真机复现的数字标 `UNVERIFIED`（如由 FPS 换算的单帧延迟）；所有数据集名、指标数字均逐字取自全文。

<!-- source: https://arxiv.org/abs/2606.20742 -->
