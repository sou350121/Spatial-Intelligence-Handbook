<!-- ontology-5axis
problem: VIO
representation: sparse
sensor: multi-modal
paradigm: hybrid
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# 异步事件相机实时机载视觉惯性 SLAM (AERO-VIS: Asynchronous Event-based Real-time Onboard Visual-Inertial SLAM)

> **发布时间**：arXiv:2605.07885v2 [cs.RO]，2026-09-15；Accepted for publication in IEEE Robotics and Automation Letters (RA-L), August 2026
> **论文 / 模型名**：AERO-VIS（含 SuperEvent+ / SuperLitE）
> **机构**：ETH Zürich Mobile Robotics Lab + Technical University of Munich (MCML / MIRMI)
> **核心定位**：把 event-based keypoint 检测网络压到 2.5 ms、并把它塞进 OKVIS2 的**异步多线程**框架里，做出第一个**纯事件惯性、仅靠机载算力**完成 UAV 闭环控制与 2 km 大尺度建图的 SLAM 系统。
> **Ontology 5-axis**：problem=VIO · representation=sparse · sensor=multi-modal · paradigm=hybrid · time=filter-streaming

导语：事件相机天生有 HDR 与抗运动模糊能力、且时间分辨率是微秒级，但绝大多数 event-based 里程计**仍然跑固定帧率**——这既浪费了异步传感器的能力，也把延迟和吞吐钉死在预设频率上。AERO-VIS 的答案是"预处理与状态估计线程解耦 + 处理最新可处理的事件状态"，于是在 NVIDIA Jetson Orin NX 这类受限算力上，系统速率由**当前算力上限**而非固定频率决定，且精度在多数序列上超过无算力约束的 ESVO2 / SDEVO。

## X-Ray 开场

传统 frame-based VIO 在高速/低光下会崩；event camera 能扛，但现有 event-based 系统要么精度不够、要么必须挂在桌面级大 GPU 上；少数上机载 UAV 的系统（如 ESVIO）需要融合 frame 才稳。本文做了三件事：(1) 把 SuperEvent 的 MCTS 时间表面从**固定时间窗 Δt** 改成**固定事件数 N_e**（`MCTS_Ne`），让不同运动速度下的时间表面长得更像；(2) 把网络瘦身成 4 层 backbone + 64 维描述子、8 通道输入的 **SuperLitE**，推理 2.5 ms、比 baseline 快 90.5%；(3) 在 OKVIS2 上做**异步解耦架构**（预处理线程按事件流速率跑、前端在准备好时才冻结共享 MCTS buffer 做推理）。对 spatial AI 研究者的意义：这是一条"learned frontend + 经典 factor-graph backend"在嵌入式极限算力下的可行性证据，也说明**关键假设是"事件流近时间连续可任意时刻取状态"**——这正是异步系统能压低延迟的物理根据。

## 📍 研究全景时间线

（注：截断全文中未给出各参考文献的年份，故时间轴按**方法演进顺序**排列，不标往年年份，以反捏造；本文标 2026-09。）


```
frame-based VIO 基线
  OKVIS2 (frame keypoint + factor graph, 本文直接改造的底座)
        │
        ├─► feature-based 事件法
        │     EVIO (event-frame + 光流补偿 + EKF)
        │     时间表面 patch 互相关 + Arc* corner (event-by-event，开销大)
        │     line-feature + EMVS + ESKF
        │     ESVIO (stereo event-inertial，可带 frame；纯事件配置缺硬件验证)
        │
        ├─► direct 事件法
        │     首个 6D event pose tracking (GPU / 低分辨率)
        │     EVO (binary event frame 几何对齐)
        │     ES-PTAM (需 GT 位姿初始化)
        │     ESVO ─► ESVO2 (SOTA 效率，桌面 PC 上 VGA 实时)
        │
        ├─► data-driven 事件法
        │     DEVO (monocular，尺度模糊) ─► DEIO (加 IMU，metric scale 不稳)
        │     SDEVO (static stereo association，15 Hz @VGA 桌面 PC)
        │     [5] FireNet 重建帧 + OpenVINS (onboard 20 Hz，但重建有 artifact)
        │     SNN 直接映射控制 (依赖静态地面假设)
        │
        └─► SuperEvent (MCTS 多通道时间表面 + 改 OKVIS2 前端)
                  │  ✗ 非实时、需固定预设处理率
                  ▼
        ★ 本文 AERO-VIS (2026-09, v2 15 Sep 2026)
           SuperEvent+ / SuperLitE + 异步 OKVIS2
           → 首个纯事件惯性 SLAM 的 UAV 闭环控制 + 2 km 大尺度 + onboard Jetson Orin NX

本文局限（论文自述+架构约束）：
  · 标准飞行条件下精度仍不如 frame-based OKVIS2（振动 → 特征外观畸变）
  · 描述子仍不如 frame-based 运动不变
  · 长航时下 loop closure detection 成为显著瓶颈（处理率可掉到 5 Hz 以下）
  · 只在 OKVIS2 已有框架内优化，未动回环/后端算法本身
```

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| 事件预处理线程（MCTS_Ne 生成） | 同步后的 stereo events（仅处理有对应 IMU 的事件）+ 双通道 GPU tensor（每像素/极性存最近事件时间戳） | 共享内存中的 `MCTS_Ne` 张量（8 通道：`N̄_{e,k}∈{0.03,0.1,0.3,1.0}` events/pixel × 2 极性） | 无训练；按事件传感器固定高频更新率运行，受前端门控（gating） |
| 前端 SuperLitE 推理 | 冻结的 MCTS_Ne 张量 | keypoints + 64 维描述子（归一化后量化为 8-bit 整数） | 训练：沿用 SuperEvent 的训练策略；推理：TensorRT 编译为 16-bit 浮点 + CUDA graph capture |
| 前端 keypoint matching | 描述子（cosine distance，非 SuperEvent 的 Euclidean） | 匹配 → landmark 三角化 / 残差 | 无训练 |
| 回环检测 | 描述子 vs DBoW2 数据库（先前 keyframe） | 候选回环 + 启发式漂移界检查 | 无训练；通过检查后才启动全局 pose graph 重优化 |
| 后端（factor graph） | 最近传感器观测 | 相机位姿 + landmark | 无训练；实时模式下限制最大迭代数与时间预算 |
| 回环重优化线程 | 检测到的回环 | 全局 posegraph 更新（detached 后台线程） | 无训练 |
| 平台（UAV） | 2× Prophesee EVK4 event camera（7.4 cm baseline、110° FOV、带 IR filter）+ Bosch BMI160 IMU | — | 板载 NVIDIA Jetson Orin NX |

**模式配置**（论文明确给出两档）：
- **精度优先（离线后处理）**：完整 SuperEvent+ 接入 OKVIS2，关闭所有 runtime 优化（含异步），同步频率 50 Hz（rpg-stereo / TUM-VIE）、20 Hz（VECtor）。
- **性能优先（实时）**：量化到 16-bit 浮点的 SuperLitE + TensorRT + CUDA graph capture，异步 + 限制后端迭代/时间预算 + 空间降采样。

### 1.2 关键机制

**⚡ Eureka Moment：把时间表面的"固定时间窗"换成"固定事件数"，并把事件预处理从状态估计里彻底解耦——前者让特征外观对运动速度不变，后者让系统速率由算力上限自适应决定，而不是由预设频率决定。**

拆成两个机制：

1. **`MCTS_Ne`（常量事件计数多通道时间表面）**：传统时间表面的理想 Δt 随关键点局部运动而变，是它的固有缺陷。SuperEvent 用 K 个固定 Δt 叠多通道。本文改为对每个通道 k 取**常量事件数** `N_{e,k}`，由事件序号回推 Δt（式 3）。再按传感器总像素数归一化成 `N̄_{e,k}`，实现 sensor-agnostic。最小计数的通道因第一层权重幅值最低，去掉后（得到 8 通道输入）重训练仍保精度。
2. **异步解耦 + "处理最新可处理状态"**：事件流近时间连续 ⇒ 任意时刻都能生成对应 MCTS_Ne ⇒ 前端一就绪就处理**最新的**那个时刻，而不是等待下一个固定 tick。这直接降低延迟。代价是共享 MCTS buffer 需要门控：前端完成上一轮匹配与回环检测后**冻结** buffer 跑推理，跑完再解冻。

### 1.3 信息流 / 架构图

```
 stereo events ──► time sync（只保留有对应 IMU 的事件，新事件留 buffer）
        │
        ▼
 [预处理线程] 双通道 GPU tensor(每像素/极性最近时间戳)
        │  ← 按 event sensor 固定高频更新率运行
        ▼
 共享 MCTS_Ne buffer  ◄──── freeze / unfreeze 门控 ─────┐
        │                                                │
        ▼                                                │
 [前端线程] 冻结 buffer → SuperLitE 推理(2.5 ms)          │
        │        → NMS → 描述子插值 → 量化(8-bit int)     │
        │        → keypoint matching (cosine dist)        │
        ▼                                                │
   三角化 / 残差 ──► [后端] factor graph 优化 ──► 位姿+landmark
        │
        ├─► DBoW2 回环候选 + 漂移界启发式检查
        │        └─► [detached 线程] 全局 pose graph 重优化
        │
   （迭代结束，解冻 buffer，取"最新可处理"时刻重新开始）────┘
```

## 2 · 数学核心

📌 **Napkin Formula**：

$$\Delta t_k = \tau - t_{I-N_{e,k}} \quad\Longrightarrow\quad \text{时间窗不再固定，而是"往回数够 } N_{e,k} \text{ 个事件"所花的时间}$$

再叠加时间表面的指数式衰减（越近的事件权重越高）：

$$\text{TS}_{p,\Delta t_k}(x_i,y_i)=\max_{\mathbf{e}_i\in\mathcal{E}_{p,\Delta t_k}}\left(1-\frac{\tau-t_i}{\Delta t_k}\right)$$

**目标** → 让同一块 3D 纹理在不同运动速度下产生**外观更相似**的事件时间表面，从而让学习式关键点检测/描述更稳。
**公式** →
- 事件定义：$\mathbf{e}_i=(t_i,x_i,y_i,p_i)$，$p_i\in\{-1,+1\}$
- 通道事件集：$\mathcal{E}_{p,\Delta t_k}=\{\mathbf{e}_i \mid p_i=p,\; t_i\in[\tau-\Delta t_k,\tau]\}$
- MCTS 张量：$\text{MCTS}=(\text{TS}_{-1,\Delta t_1},\ldots,\text{TS}_{-1,\Delta t_K},\text{TS}_{+1,\Delta t_1},\ldots,\text{TS}_{+1,\Delta t_K})$（共 $2K$ 通道；喂给网络时用去掉最小计数通道的 8 通道版本）
- 常量事件数版本：$\Delta t_k = \tau - t_{I-N_{e,k}}$，$I$ 为最新事件索引
- 归一化：$\overline{N}_{e,k} = N_{e,k}/(H\cdot W)$，取值 $\{0.03,0.1,0.3,1.0\}\ \text{events/pixel}$（本文用对数阶梯，对应 SuperEvent 的 $\Delta t$ 窗口阶梯）
**直觉**：$\Delta t$ 是"变量"，$N_e$ 是"不变量"。运动快 ⇒ 同样事件数在更短时间里凑够 ⇒ $\Delta t$ 自动变短；运动慢 ⇒ $\Delta t$ 自动变长。**时间表面看到的"纹理密度"因此趋于一致**，网络不必再为速度变化买单。论文同时诚实指出：这只显式归一化了运动**幅值**，并未做到完整运动不变性（所以对运动**方向**的鲁棒性提升只是"顺带"）。

## 3 · 带数字走一遍（玩具设定）

**玩具设定**：分辨率取论文 UAV 实际的降采样后尺寸 240×424 = 101,760 像素（此分辨率与 35 MEv/s 事件率上限均来自全文 UAV 配置，但下面的事件率数值是**我自造的玩具值**，非论文报告）。

取中间通道 $\overline{N}_{e,k}=0.3\ \text{events/pixel}$ ⇒ 该通道需要事件数 $N_e = 0.3 \times 101{,}760 \approx 30{,}528$ 个事件。

| 场景 | 瞬时事件率（玩具值） | 由式(3)反推的 $\Delta t$ | 时间表面会发生什么 |
|---|---|---|---|
| 剧烈甩动（接近硬件上限） | 35 MEv/s | $\Delta t \approx 30{,}528/35{\times}10^6 \approx 0.87\ \mathrm{ms}$ | 窗口极短，几乎只收当前瞬间事件，运动模糊最小 |
| 温和平移 | 5 MEv/s | $\Delta t \approx 30{,}528/5{\times}10^6 \approx 6.1\ \mathrm{ms}$ | 窗口自然拉长，仍凑够 0.3 ev/px 的覆盖 |

对照 SuperEvent 的 `MCTS_Δt`：若固定 $\Delta t = 10\ \mathrm{ms}$，则在 5 MEv/s 场景下得到稀疏、几乎为空的时间表面，在 35 MEv/s 场景下时间表面被"灌满"、纹理饱和——**同一块 3D 纹理呈现完全不同的图像**（论文 Fig. 中 10 ms 通道的两张时间表面对比正是这一点，而 0.3 events/pixel 的 `MCTS_Ne` 通道"visually more similar"）。

小通道换算（同一玩具分辨率）：

| $\overline{N}_{e,k}$ | $N_e$（事件数） | 35 MEv/s 下的 $\Delta t$ | 5 MEv/s 下的 $\Delta t$ |
|---|---|---|---|
| 0.03 | ≈ 3,053 | ≈ 0.087 ms | ≈ 0.61 ms |
| 0.1 | ≈ 10,176 | ≈ 0.29 ms | ≈ 2.0 ms |
| 0.3 | ≈ 30,528 | ≈ 0.87 ms | ≈ 6.1 ms |
| 1.0 | ≈ 101,760 | ≈ 2.9 ms | ≈ 20.4 ms |

这样 4 个通道自动覆盖了从亚毫秒到几十毫秒的多尺度时间结构，且**尺度比例不随速度漂移**——这就是"恒定事件数"带来的全部红利。

## 4 · 工程视角

**论文报告的数字（逐字）**：
- SuperLitE 推理 **2.5 ms**，比 baseline **快 90.5%**（论文语境为 embedded device 上的 inference time；Table I 的实时列在 **NVIDIA Jetson Orin NX** 上评测）。
- SuperEvent+ 相对 SuperEvent 平均相对提升 **18.7%**（AUC @ 10°）；SuperLitE 的 AUC@10° 提升 **15.0%**。
- 离线同步处理率：**50 Hz**（rpg-stereo、TUM-VIE）、**20 Hz**（VECtor）。
- 机载空间降采样：TUM-VIE → **240×424**，VECtor → **240×320**；UAV 上亦降采样至 **240×424**，并额外把最大事件率限制到 **35 MEv/s**。
- 桌面评测机：**Intel Core i5-13600 + NVIDIA GeForce RTX 4070 + 32 GB RAM**；机载：**NVIDIA Jetson Orin NX**。
- 对照系统的速度约束：SDEVO 推理速度 **1–3 Hz**（Jetson 实时评测下的精度受限原因）；SDEVO 原文在桌面 PC 上 VGA 分辨率可达 **15 Hz**；[5] 的 hybrid monocular VIO 机载位姿估计 **20 Hz**（均引自 related work 描述）。
- 2 km / 20 min 城市步行实验中：**处理率可掉到 5 Hz 以下**，AERO-VIS 仍能可靠估计轨迹。

**未报告项（不编造）**：
- AERO-VIS 在 Jetson Orin NX 上的实际平均处理频率 / FPS：**「论文未报告」**（论文只给 ATE 与"异步自适应速率"的定性描述）。
- 显存 / VRAM 占用、功耗、CPU 占用：**「论文未报告」**。
- 论文提到 "Table lists the evolving timings of several system components" 给出各组件随时间的耗时演化，但**该表的具体数值未包含在本次截断全文中** → **UNVERIFIED**（不给数字）。

**Trade-off 结构（从设计约束推导）**：

| 维度 | 取向 | 代价 / 约束 |
|---|---|---|
| 延迟 | "前端一就绪就处理最新可处理事件状态" ⇒ 相比同步（frame-based）处理降低延迟 | 需要共享 MCTS buffer 的 freeze/unfreeze 门控；预处理线程会被推理阻塞 |
| 吞吐 | 异步 ⇒ 以算力上限的最快瞬时速率运行，最大化吞吐 | 后端可能被高频观测"灌爆"，实时模式下必须限制最大迭代数与时间预算 |
| 精度 vs 速度 | 两档模式：SuperEvent+（精度）vs SuperLitE（速度，2.5 ms） | SuperLitE 的 AUC@10° 增益（15.0%）低于 SuperEvent+（18.7%），是显式取舍 |
| 网络规模 | 4 层 encoder（每层 1 conv + max-pooling + batch-norm）、描述子 256 → **64** 维、输入 10 → **8** 通道 | 论文明确：进一步削减通道数/描述子维度/backbone 深度会**显著掉精度** |
| 传输/匹配 | 描述子归一化后做 8-bit 对称 min-max 量化（scale 来自训练数据），cosine 距离计算时该 scale 被抵消 | 量化 scale 依赖训练分布，是域外泛化的隐患（见 §8） |
| 分辨率 | 机载必须空间降采样 | 直接限制精度：论文自述 UAV 上 AERO-VIS 精度受"reduced spatial resolution"限制 |
| 事件率 | UAV 上限制 35 MEv/s | 无人机振动 + 激进机动会触发高事件率，超出实时预算是核心矛盾 |
| 长航时 | 回环靠 DBoW2 + 启发式漂移界检查 | 论文自述 **loop closure detection 随轨迹增长成为显著瓶颈**；回环与后端的优化被明确划为 out of scope |

## 5 · 数据与评测

**训练/评测所用数据集（逐字）**：
- **Event Camera Dataset**：iniVation DAVIS240C，**180×240** 分辨率（用于 SuperEvent+/SuperLitE 的 keypoint 检测与描述评测）。
- **Event-aided Direct Sparse Odometry dataset (EDS)**：Prophesee Gen 3.1，**480×640** 分辨率。
- **rpg-stereo**：两台 iniVation DAVIS240C，小尺度轨迹。论文发现其传感器数据与位姿 GT 之间存在**时间错位**，因此离线在 **±100 ms** 内估计一个时间偏移，使所有估计器的误差最小。
- **TUM-VIE**：Prophesee Gen4 HD，**720×1280**；只有小尺度 mocap 序列有一致的 GT 位姿；其中 mocap-shake 序列存在激进抖动 + 部分无纹理视野。
- **VECtor**（大尺度序列）：Prophesee Gen3 CD，**480×640**；室内序列特征少而相似；IR filter 造成 vignetting artifacts，且事件相机外参标定不精确；论文因为拿不到在**所有序列上都可靠**的标定参数，启用了 OKVIS2 继承来的**在线外参标定**。

**评测设置**：
- 主指标：**RMS absolute trajectory error (ATE) [cm]，5 次运行的中位数（median of 5 runs）**；至少 3 次运行中崩溃或发散的序列标记为 **"failed"**（此标记针对 baseline 记录）。
- 括号内数字对应 [2,3] 中评估的**裁剪序列**。
- 三个基准：rpg-stereo bin 3.73 (1.63) / boxes2 8.65 (3.57) / desk2 44.42 (3.27) / monitor2 1.87 (1.80) / reader 123.82 (1.80)（ESVO2 离线值）——**ESVO2、SDEVO、OKVIS2-SE+ 在桌面 PC 上评测，其余在 Jetson Orin NX 上**。
- 相对位姿评测：**AUC scores for different rotation error thresholds**，rotation 变化强制在 **1°–45°**。

**关键结果（逐字复制）**：

| 数据 | 序列 | ESVO2 离线 | SDEVO 离线 | OKVIS2-SE+（ours） | ESVO2 实时(Jetson) | SDEVO 实时(Jetson) | AERO-VIS（ours） |
|---|---|---|---|---|---|---|---|
| rpg-stereo | bin | 3.73 (1.63) | 3.78 (4.64) | 0.56 (0.41) | 216.71 | 4.27 | 1.43 |
| rpg-stereo | desk2 | 44.42 (3.27) | 5.56 (0.59) | 0.81 (0.35) | 61.98 | 27.46 | 1.26 |
| TUM-VIE | 1d-trans | 2.19 | 1.10 | 0.34 | failed | 1.82 | 1.48 |
| TUM-VIE | 6dof | 3.48 | 2.22 | 0.38 | failed | 4.38 | 1.05 |
| TUM-VIE | shake | failed | 76.55 | 3.79 | failed | 91.61 | 8.13 |
| VECtor | school-scooter | failed | 824.45 | 174.44 | failed | 612.34 | 256.20 |
| VECtor | units-scooter | failed | 1530.22 | 138.48 | failed | 2828.34 | 326.76 |

（OKVIS2-SL 消融列另有数值：bin 1.44 (1.30)、desk2 1.49 (1.67)、1d-trans 0.94、shake 8.61 等，此处不逐一列出。）

**论文给出的结论性判断（注意条件）**：
- OKVIS2-SuperEvent+ **在所有序列上取得最好结果**；归因于 SuperEvent+ 可靠的 keypoint 检测/描述 + OKVIS2 的传感器融合与后端。
- 实时评测中，ESVO2 显著不稳定（多数序列 failed 或严重漂移），论文解读为"其计算需求超出机载硬件能力"。
- AERO-VIS "在多数序列上甚至超过 ESVO2 和 SDEVO 的无约束（桌面）结果"，且是唯一能做可靠机载状态估计的系统。
- 与同步系统 OKVIS2-SuperLitE 的消融对比：AERO-VIS 精度相当或更好；论文的解释是自适应速率"足够快但不会用观测灌爆后端"，而固定同步频率难以选——**即使平均处理时间在实时预算内，在 20 Hz 下仍有许多样本超界；反过来低于边界的样本会限制吞吐（系统必须等它们到达）；低处理率还会导致更多序列发散。**
- **UAV 闭环实验（Table 数值未含在截断全文中 → UNVERIFIED）**：正常光照下 **OKVIS2 优于 AERO-VIS**；HDR 实验中 AERO-VIS 漂移约 **1 m**（识别出旋转为主轨迹对 OKVIS2 回环检测构成约束，缺少显著平移使回环无法触发），而 frame-based OKVIS2 误差更大，**5 圈后撞墙**；模拟激进飞行实验中 AERO-VIS 相比 frame-based OKVIS2 把估计误差降低 **90%**。
- **大尺度实世界实验**：2 km、20 min 城市步行，无 GT，仅做定性对比（轨迹与街道布局吻合）；回环检测触发后纠正的漂移为**相对于估计行进距离的 1.8%**。

## 6 · 能力与失败模式

### 能做（论文有明确证据）
- **纯事件惯性、仅机载算力**完成 UAV 闭环控制（论文称为首个此类演示），控制器为 linear MPC，平台为 Jetson Orin NX + 2× Prophesee EVK4 + Bosch BMI160。
- **HDR**：关灯、光源在窗后，UAV 原地旋转 10 次仍能维持（漂移约 1 m），而 frame-based OKVIS2 撞墙。
- **抗运动模糊 / 激进机动**：手持水平抖动 + 绕竖轴快速旋转，误差比 frame-based OKVIS2 低 90%。
- **大尺度 + 回环**：2 km 城市步行，光照变化（sun/shade/artificial）与动态实体（cars/pedestrians/bicycles）下轨迹贴合街景，回环纠正 1.8% 相对漂移。
- **抗退化的鲁棒性**：VECtor 上 ESVO2 全线 failed、SDEVO 出现极大误差（如 school-scooter 824.45，units-scooter 1530.22），OKVIS2-SE+ / AERO-VIS 未失败。
- **低处理率下仍可工作**：即使速率掉到 5 Hz 以下仍可靠估计。

### 不能做 / 会失败
- **常规平稳飞行条件下精度不如 frame-based OKVIS2**（论文自述，UAV 实验）。根因被论文定位为三点：(a) 机载空间分辨率被降低；(b) 时间表面对**振动引起的特征外观变化**敏感；(c) 训练策略依赖同一序列的连续样本，网络对**突变运动**暴露不足。`MCTS_Ne` 只缓解、不消除。
- **运动不变性不完整**：论文明确"只显式归一化了运动幅度，并未实现完整运动不变性"，因此对运动**方向**的鲁棒性只是间接改善。
- **旋转为主（平移极小）的轨迹会压制回环**：OKVIS2 的回环机制对最大相对**线性**漂移设了界，纯旋转因此难以触发回环 ⇒ HDR 旋转实验出现约 1 m 漂移。
- **长航时下回环检测成为显著瓶颈**：2 km 实验中，随轨迹增长，loop closure detection 成为主要瓶颈，keypoint matching 与后端优化的开销也在上升；论文把这类问题归为 OKVIS2 框架固有（frame-based 时同样存在）并明确划出 scope。
- **无纹理 / 特征稀少场景**：TUM-VIE mocap-shake 序列"部分无纹理视野"，被论文称为"highly challenging"，OKVIS2-SE+ 在该序列 ATE 3.79、AERO-VIS 8.13，均显著高于其他序列。
- **baseline 的崩塌也划出了场景边界**：ESVO2 在**高光流**场景失效（TUM-VIE mocap-shake/-shake2、全部 VECtor 序列），论文认为其计算需求超出机载硬件；SDEVO 大部分序列尚可，但在 rpg-stereo desk2、TUM-VIE shake 系列、VECtor school-scooter / units-scooter 上误差很大，论文推测源于**训练数据的 domain shift** 与**未融合 IMU**。

### 隐含假设 (Hidden Assumptions)

| 假设 | 在哪被依赖 | 违反了会怎样 |
|---|---|---|
| 场景刚性、动态实体只占少数 | 整个 factor-graph 后端（无动态物体显式建模） | 2 km 实验里 cars/pedestrians/bicycles 存在但仍成功——说明这是"经验性成立"而非被证明的鲁棒 |
| 事件流**近时间连续**，任意时间戳都能取到一个有意义的状态 | 异步设计的前提（"process the latest possible event state"） | 事件流被硬件截断（UAV 上强制 35 MEv/s 上限）或场景静止时，"最新可处理状态"失去信息量 |
| 只有带对应 IMU 的事件才被处理，其余留在 buffer | 多模态时间对齐 | 事件率远高于 IMU 率或 IMU 丢包时，buffer 会积压，异步的"低延迟"前提受损 |
| **事件率与空间分辨率成正比**（故除以总像素数归一化） | `N̄_{e,k}` 的 sensor-agnostic 设计 | 换传感器时若极性约定/带宽/阈值策略不同，归一化不保证等价；跨传感器泛化未被验证 |
| 描述子的 8-bit 量化 scale 可由**训练数据**确定 | 量化 + cosine 距离计算 | 部署域的事件率/纹理分布偏离训练分布时，min-max scale 失配会直接损伤匹配质量 |
| 回环的 DBoW2 候选 + 启发式漂移界检查足以排除假阳 | 回环触发 | 纯旋转轨迹直接不触发（论文已实测到）；漂移界依赖对"合理漂移"的先验 |
| 时间同步可由离线优化得到（±100 ms 内搜索一个偏移） | rpg-stereo 评测 | 若真实场景存在**时变**偏移或硬件级不同步，单一常数偏移无效 |
| 外参标定可被在线估计替代 | VECtor 评测（论文启用 OKVIS2 的在线外参标定） | 论文自述"无法获得在所有序列上可靠工作的标定参数"——这是真实约束，不是巧合 |
| 机载算力瓶颈只出现在"事件预处理 + keypoint 检测"两个环节 | SuperLitE 的加速设计（占论文贡献一半） | 论文自述长航时下瓶颈转移到 loop closure 与后端，此时网络加速的边际收益趋近于零 |

## 7 · 与相关工作对比

| 系统 | 类型 | 传感器 | 优化/推理方式 | 实时性证据 | 主要限制 |
|---|---|---|---|---|---|
| EVIO | feature-based | 单目事件 | EKF，光流补偿 | — | 运行时间随特征数线性增长，高密度跟踪时低效 |
| ESVIO | feature-based | stereo event-inertial（可选 frame） | Arc* + LK + 融合 frame 匹配 | 完整流水线（含 frame）做过闭环 UAV 控制 | **纯事件配置缺乏硬件验证**；标准数据集上劣于 [2,3]，稳定性依赖 frame 输入 |
| ESVO2 [2] | direct | stereo event-inertial | 时间表面时空一致性优化 + 边缘像素采样表示 | 桌面 PC 上 VGA 实时（SOTA 效率） | 本文实测：高光流场景失效；机载算力不足导致 failed/严重漂移 |
| SDEVO [3] | data-driven（端到端） | stereo event | static stereo association 恢复尺度，mixed-precision | 桌面 PC VGA **15 Hz** | 本文实测机载 **1–3 Hz**；部分序列大误差（推测 domain shift + 无 IMU） |
| Hybrid monocular VIO [5] | hybrid | 单目事件 + 重建帧 | FireNet 重建帧 + OpenVINS | 机载 **20 Hz** | 重建有 artifact、增加开销、**抹掉事件相机的高时间分辨率**；源码未公开、未在公开数据集评测 |
| SNN 直接控制 [30] | data-driven | 单目事件 | 原始事件 → 控制指令 | — | 依赖静态地面假设，仅能定点跟随平面 |
| SuperEvent [1] | hybrid | 单目事件 + OKVIS2 | MCTS（固定 Δt）+ SuperPoint 适配 | **非实时**，需固定预设处理率 | 时间表面对运动速度敏感；算力开销大 |
| **AERO-VIS（本文）** | hybrid + 异步 | stereo event + IMU | SuperEvent+/SuperLitE + 异步 OKVIS2 factor graph | Jetson Orin NX 上 onboard 实时；首个纯事件惯性 UAV 闭环控制 | 常规飞行精度低于 frame-based OKVIS2；长航时回环成瓶颈 |

**面试 Tip**：被问"event-based SLAM 现在到哪一步了"，不要背 SOTA 表格。这样答——
"落点分三层：① **表示层**，事件数据怎么变成网络/优化器能吃的张量，MCTS 从固定时间窗演进到固定事件数（本文 `MCTS_Ne`），本质是让特征外观对运动速度解耦；② **系统层**，事件相机是异步传感器，但绝大多数方法还是固定帧率跑，本文把预处理与状态估计线程解耦、跑'最新可处理状态'，这是它能在 Jetson Orin NX 上既低延迟又高吞吐的原因；③ **证据层**，AERO-VIS 是第一个纯事件惯性 SLAM 完成 UAV 闭环控制和 2 km 大尺度建图的系统，但论文自己承认常规飞行下精度不如 frame-based OKVIS2，短板在振动导致的描述子退化。所以下一步不是把 event 做到取代 frame，而是 event + frame/LiDAR 的 hybrid——这也是作者在 conclusion 里点名的方向。"

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-17)

**Repo 信号核验**：论文全文**未出现任何 `github.com` 链接**；仅在摘要末尾以纯文本形式给出项目页 `ethz-mrl.github.io/AERO-VIS`（"Videos of the experiments, source code, and additional results are available at …"）。按本 handbook 的判定规则，纯文本域名**不构成可用作 issue 流验证的 repo 信号**，因此本节**没有经 issue 验证的失败案例**，以下 pitfall 全部由 §6 失败模式 + 方法约束**机械推导**得到（未经 issue 验证，亦不含任何 issue 编号 / commit hash）。

**P1 — 振动环境下描述子退化（由 §6 失败模式 "vibration-induced appearance changes" + §1 的 SuperLitE/训练策略约束推导）**
- 论文自述：训练策略"relies on consecutive samples from the same sequence, limiting network exposure to sudden motion variations"；UAV 振动持续改变运动方向、扭曲事件流中的特征外观，导致 event-based 描述子匹配劣化。
- 机械后果：只要平台是带电机/桨叶的 UAV，且未做显著机械减振或未融合 frame，"常规飞行下 AERO-VIS 不如 frame-based OKVIS2"就是**架构层面的必然**，不是调参问题。缓解只能走论文 conclusion 明说的 hybrid（融入 frame/LiDAR）路线。

**P2 — `MCTS_Ne` 的双侧失效：极慢运动窗口过长 / 极快运动窗口塌缩（由 §2 式(3) `Δt_k = τ − t_{I−N_{e,k}}` + §4 的 35 MEv/s 硬件上限推导）**
- 式(3) 让 Δt 完全由事件率决定。事件率过低（静态场景、悬停、慢速平移）⇒ Δt 拉长到数十毫秒 ⇒ 时间表面混入过期事件与动态物体痕迹，`1−(τ−t_i)/Δt` 的衰减权重也把陈旧事件抬得很高。
- 事件率过高（振动/激进机动）⇒ Δt 塌到亚毫秒 ⇒ 通道内事件几乎全落在同一像素，时间表面接近二值/饱和；同时论文在 UAV 上**强制限制 35 MEv/s**，说明这一侧已被真实硬件预算卡住。
- 机械后果：`MCTS_Ne` 把"运动幅度敏感性"从一个固定参数问题换成了一个**双向边界问题**，两端的失效模式由式(3) 的形式直接决定。

**P3 — 8-bit 量化 scale 的域外失配（由 §1 "symmetric min-max quantization using a scaling factor derived from the training data" + §4 量化约束推导）**
- 描述子在归一化后被对称 min-max 量化到 8-bit，scale 来自训练数据（Event Camera Dataset / EDS）；论文指出该 factor 在 cosine 距离计算时被抵消。
- 机械后果：scale 抵消只对**余弦距离**成立，**不**对描述子插值（论文把 descriptor interpolation 明确列为 keypoint detection timing 的组成部分）与跨域数据分布成立。部署到事件率分布、传感器极性/带宽特性与训练集不同的新传感器时，min-max 饱和会静默降低匹配质量——而且表现为"精度轻微下降"，不报错，极难定位。

**P4 — 时间同步与标定不可靠是复现的第一道坎（由 §5 的实验设置推导，非猜测）**
- rpg-stereo：论文自述发现"a temporal misalignment between the sensor data and pose ground truth"，需离线在 **±100 ms** 内搜索一个常数偏移。
- VECtor：论文自述"we were unable to obtain a set of calibration parameters that reliably work on all sequences"，只能启用 OKVIS2 的**在线外参标定**，并额外面对 IR filter 的 vignetting artifacts 与不精确的事件相机外参。
- 机械后果：AERO-VIS 自身不含任何时延标定/外参自标定模块（异步解耦这一改动只做线程与 buffer 的调度）；复现者在自己的硬件上必须先独立解决**事件–IMU–GT 同步**与**立体事件外参**，否则会把标定误差误判为算法失效。P1 中"精度不如 OKVIS2"的结论也是在**已做这两件事之后**才成立的。

---
[← Back to VIO README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文（截断版）· 未在真机复现的数字标 `UNVERIFIED`。§4 中 AERO-VIS 的机载处理频率/VRAM/功耗、§5 中 UAV 闭环实验与组件耗时表的**具体数值未包含在本次截断全文中**，均标注为未报告 / `UNVERIFIED`，未做任何推算填充。

<!-- source: https://arxiv.org/abs/2605.07885 -->
