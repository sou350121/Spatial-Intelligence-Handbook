<!-- ontology-5axis
problem: pose
representation: n/a
sensor: event
paradigm: hybrid
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# 概率事件：面向 Quanta（光子计数）传感的实时感知原语 (Quanta Perception as Probabilistic Events)

> **发布时间**：2026-08-27（arXiv:2608.27584v1 [cs.CV]）
> **论文 / 模型名**：Probabilistic Events（probabilistic event camera）
> **核心定位**：把"光子计数传感器 → 离线重建 → 感知"这条链路，换成"直接在每个像素上对光子流做递归贝叶斯推断（run-length 后验）"的实时中间表征——不需要显式运动补偿、不需要重建、不需要重训下游模型，吞吐比 SOTA quanta 重建基线快最多四个数量级。

导语：Quanta（SPAD/QIS）传感器能捕获单个光子，但 1 MPixel 阵列的原始二进制流超过 100 Gbits/s，现有重建法处理数秒采集要花几分钟，实时机器人根本用不了。本文的结论是：不必重建图像——把"上次强度变化以来经过多久"（run-length）当作每像素的后验信念状态在线推断，就能同时拿到运动自适应 flux、时间稳定性图与熵不确定性，并在 4090 上保持 51 kqFPS 输入、1650 FPS 输出（256×512），在 <0.05 lux 下跑通跑步人体姿态估计。

---

**X-Ray 开场**：论文要解决的是"光子级信息太多反而无法实时使用"这个悖论——quanta 传感器数据带宽与算力需求远超机器人预算，而传统做法是离线重建强度帧。它提出的做法是：把每个像素建模成一个贝叶斯在线变点检测（BOCPD）问题，维护"距上次强度跳变的时间"的后验，用该后验的期望直接决定该像素指数平滑的系数 ω，于是"曝光时间"变成每像素自适应、常数时间更新、固定内存的递归量。对 spatial AI 研究者的意义在于：这是一种**不重建、因果、可插拔**的光子层表征，把 change-based sensing 从"二值极性事件"推广为"连续稳定性 + 不确定性 + 绝对强度聚合"，并且产出的是图像化字段而非异步稀疏流，因此能直接喂给现成 CV 模型。

## 📍 研究全景时间线

```
光子计数传感                                   change-based / 事件感知
──────────────────────────────────────────────────────────────────────────────
2005  Fossum QIS 概念提出
2007                        BOCPD (Adams & MacKay)  ← 本文借用的数学工具
2003–2014                   DVS / DAVIS：固定阈值模拟触发极性事件
2017  SPAD 百万像素 (Morimoto)
2019  High-flux SPAD imaging
2020  Ma et al. Quanta Burst Photography (QBP)
                            ← 代表"离线 align-and-merge 重建"范式
2020                        1280×720 堆叠事件传感器 (Prophesee)
2021  4MP / 16.7MP QIS 堆叠 BSI
2024  Streaming quanta sensors (online imaging)
2024  Quanta Neural Networks  ← 重建无关，但需重训
2024  Bit2Bit（1-bit 视频重建，自监督，推理期训练，极慢）
2025  Quanta Video Restoration (ECCV)
2026  ★ 本文：Probabilistic Events
      把 BOCPD 后验当作传感原语，输出 flux / 稳定性 / 熵 → 免训练对接下游
──────────────────────────────────────────────────────────────────────────────
本文局限：信息受限区（<0.05 PPP 且快速运动）无法区分真实变化与散粒噪声；
          极低/极高通量两端退化（仅在光子检出概率中间 97% 区间可靠）；
          因果估计 ⇒ 放弃非因果对齐与迭代优化 ⇒ 聚合结果是"不完美重建"。
```

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| 二值 BOCPD 时间稳定性估计（Bernoulli + Beta 共轭） | 每像素二进制 quanta 帧流 $B_{1:t}(\mathbf p)$ | run-length 后验 $P(r_t\mid B_{1:t})$、稳定性图 | 无训练；纯递归消息传递，每像素常数时间 |
| 自适应 EMA flux 聚合 | run-length 后验 + $B_t$ | 运动自适应 flux $\mathcal I_{\text{adapt},t}$ | 无训练；用后验期望 $\omega_t$ 驱动指数平滑（式 5 / 10 / 11） |
| 熵不确定性信号 | run-length 后验 | $\Delta H_t$（熵变图，绿升紫降） | 无训练；熵的**时间差分**作为边缘运动检测器 |
| Binomial 泛化 | $N_{\text{sum}}$ 帧二进制求和得到的多比特虚拟曝光 $S_t$ | 同上，但吞吐更高 | 无训练；似然换成 Beta-binomial（式 13–14），输入吞吐 ≈10k→≈150k qFPS |
| 空间特征扩展（fast: 梯度 / robust: Log-Gabor；另评估 DoG） | 虚拟曝光 $S_t$，arcsine 方差稳定化 | 去相关的特征似然，与强度似然相加（式 15–17） | 无训练；$\Sigma_s$ 用**离线**特征分解 $V\Lambda V^\top$ 对角化 |
| 空间变化 Wiener 去噪（仅可视化用） | $\mathcal I_{\text{adapt},t}$ + 稳定性图 $\omega_t$ | 去噪图 | 无训练；由 $\tilde r_t = 2/\omega_t - 1$ 反推噪声方差（式 18–20） |
| 硬件视频编码 | flux / 去噪帧 | 压缩码流 | 无训练；NVENC H.264，与"事件 delta 编码"对比 |
| 彩色路径 | Bayer 马赛克原始 quanta 帧 | 彩色图 | 无训练；逐像素 binomial 直接跑在 mosaic 上，空间特征靠 Malvar-He-Cutler 估亮度，再标准 debayer |
| 下游感知 | flux 聚合（图） | 边缘/流/深度/检测/分割/位姿 | 全部**免训练、免微调**，直接用预训练模型 |

### 1.2 关键机制

**⚡ Eureka Moment**：把"事件触发"从**固定模拟阈值**换成**每个像素对 run-length 的递归后验**——一旦用后验期望 $\omega_t(\mathbf p)=\mathbb E[2/(r_t+2)]$ 去调制指数移动平均，**每像素的曝光时间就自动由局部运动决定**，于是"噪声–模糊折中"在像素级被隐式解掉，而且免去了显式运动补偿/配准的算力开销；顺带免费得到两个副产品：稳定性时长与不确定性（熵）。

三个派生信号（全部来自同一个后验）：
1. **时间稳定性图**：$\mathbb E[r]$ 的连续量，覆盖几百微秒到几秒的多尺度"结构持续多久"。
2. **熵变图** $\Delta H_t$：升熵=歧义上升，降熵=置信收敛；形成"上升前沿 + 稳定尾迹"的运动边缘签名。
3. **运动自适应 flux**：按推断稳定性积分光子，静态区抑噪、动态区抑模糊——一种**隐式重建**。

### 1.3 信息流 / 架构图

```
 原始二进制 quanta 帧 (~100 kHz, >100 Gbits/s @1MP)
        │
        ├─(可选) 时间 binning: N_sum 帧求和 → 多比特虚拟曝光 S_t
        │        Bernoulli(~10k qFPS) → Binomial 4-bit/15帧(≈150k qFPS)
        ▼
 ┌───────────────────── 逐像素递归（常数时间、固定内存） ─────────────────────┐
 │  BOCPD:  P(r_t=r+1) ∝ (1-γ)·L(B_t|r)·P(r_{t-1}=r)      ← 增长          │
 │          P(r_t=0)   ∝ γ·Σ_r L(B_t|r)·P(r_{t-1}=r)       ← 变化点(重置)  │
 │  似然 L:  Beta-Bernoulli / Beta-Binomial (+ 空间特征高斯似然)          │
 │  剪枝:    分层剪枝，仅保留 top-K (K≈5–8) run-length 概率并重归一化      │
 └───────────────────────────────────────────────────────────────────────┘
        │                        │                       │
        ▼                        ▼                       ▼
  稳定性图 / ω_t            熵变 ΔH_t           运动自适应 flux I_adapt,t
        │                        │                       │
        │                        │            ┌──────────┴─────────┐
        │                        │            ▼                    ▼
        │                        │   空间变化 Wiener 去噪    直接喂下游（免训练）
        │                        │    (~4,000 FPS)      Canny / MOSSE / RAFT /
        │                        │                       DepthAnything-v2 / YOLOv8 /
        │                        │                       RT-DETR / SAM / SAM 2
        │                        ▼
        └──────────────► NVENC H.264 (~6,000 FPS @256×512) → 传输
```

## 2 · 数学核心

📌 **Napkin Formula**

$$\omega_t(\mathbf p)=\sum_{r=0}^{t}\frac{2}{r+2}\,P\!\left(r_t=r\mid B_{1:t}(\mathbf p)\right),\qquad \mathcal I_{\text{adapt},t}=(1-\omega_t)\,\mathcal I_{\text{adapt},t-1}+\omega_t B_t$$

一句话：**"上次变化距今多久"的后验期望，就是这一像素这一帧的指数平滑系数**——后验越长则 ω 越小（积分越久、越抑噪），后验刚重置则 ω→1（立刻冻结运动）。

**目标 → 公式 → 变量 → 直觉**

- **观测模型（图像形成）**：$\phi_t(\mathbf p)$ 为像素 $\mathbf p$ 在帧 $t$ 的平均入射光子数，二进制响应
  $P(B_t(\mathbf p)=1)=1-e^{-\phi_t(\mathbf p)}$；固定窗求和 $S_t=\sum_{\tau=t-N_{\text{sum}}}^{t}B_\tau$ 在静止时服从二项分布——但 $N_{\text{sum}}$ 必须由场景动态决定，这就是噪声–模糊折中的根源。
- **递归平滑**：$\mathcal I_{\text{EMA},t}=(1-\omega)\mathcal I_{\text{EMA},t-1}+\omega B_t$，其中 $\omega=\frac{2}{N+1}$ 使稳态噪声方差等价于长度 $N$ 的 box filter。
- **BOCPD 更新（trellis 结构，"增长 or 归零"）**：
  $P(r_t=r+1\mid B_{1:t})\propto(1-\gamma)L_t(r)P(r_{t-1}=r)$；
  $P(r_t=0\mid B_{1:t})\propto\sum_{r=0}^{t-1}\gamma L_t(r)P(r_{t-1}=r)$；**危险率 $\gamma=10^{-5}$**。
- **Bernoulli 共轭**：预测概率 $\dfrac{\alpha_s}{\alpha_s+\beta_s}$，新段用 Jeffrey 先验 $\alpha_t=\beta_t=0.5$，观测后 $\alpha_s\!\leftarrow\!\alpha_s+B_t,\ \beta_s\!\leftarrow\!\beta_s+1-B_t$。
- **Binomial 版**：$P(S_t=n\mid r)=\binom{N_{\text{sum}}}{n}\frac{B(\alpha_s+n,\ \beta_s+N_{\text{sum}}-n)}{B(\alpha_s,\beta_s)}$，$\alpha_s\!\leftarrow\!\alpha_s+S_t,\ \beta_s\!\leftarrow\!\beta_s+N_{\text{sum}}-S_t$。
- **期望化聚合**：不维护每个 run-length 各自的聚合假设 $\mathcal J_t$，而是取期望 $\mathcal I_{\text{adapt},t}\equiv\mathbb E[\mathcal J_t]$；因 $\Omega_t$ 与历史聚合条件独立，递推形式不变，$\omega_t\equiv\mathbb E[\Omega_t]=\sum_r \frac{2}{r+2}P(r_t=r)$。**这一步是把"离散状态转移"变成"连续稳定性度量"的关键**，因此能表达软梯度与渐变光照，而不是阶跃式变化。
- **不确定性**：$H_t=-\sum_r P(r_t=r)\log P(r_t=r)$；实用信号是时间差分 $\Delta H_t$。
- **空间特征**：$F_t(\mathbf p,\cdot)\sim\mathcal N(\mu_s,\sigma_s^2\Sigma_s)$，离线 $V\Lambda V^\top$ 对角化后按通道独立更新，$\sigma_s^2=1+1/(r+1)$，$\mu_s\!\leftarrow\!\mu_s+(\tilde F_t-\mu_s)/(r+1)$，联合对数预测 = 特征项 + 强度项。
- **理论 SNR 上界**：全局快门 $\tau_{\text{global}}\propto(\max_{\mathbf p}v(\mathbf p))^{-1}$ 被场景最快运动卡死，而本文 $\tau_{\text{ours}}(\mathbf p)\propto v(\mathbf p)^{-1}$；SNR $=20\log_{10}\!\big(\widehat\phi/\sqrt{\mathrm{Var}(\widehat\phi)}\big)$，$\widehat\phi=-\ln(1-\hat p)$，方差用 12 阶 Taylor 展开近似。

## 3 · 带数字走一遍（玩具设定，非论文数值）

设单像素、二值 quanta 流、稳态检出概率 $p=0.3$（即 $\phi=-\ln 0.7\approx0.357$ 光子/帧）。

**Phase A：静止 100 帧后**，某段 $\alpha_s=0.5+30=30.5$，$\beta_s=0.5+70=70.5$，预测概率 $30.5/101\approx0.302$，后验质量集中在 $r\approx99$。

| 量 | 取值 | 含义 |
|---|---|---|
| $\omega_t=2/(r+2)$ | $2/101\approx0.0198$ | 等效 box filter 长度 $N=2/\omega-1\approx100$ |
| 单帧输出噪声 std | $\sqrt{0.3\cdot0.7}\approx0.458$ | 原始 |
| 聚合后噪声 std | $\sqrt{0.3\cdot0.7/100}\approx0.046$ | 约 10× 抑噪 |
| 熵 $H$（后验单峰） | ≈0 bit | 高置信：这是稳定的静态背景 |

**Phase B：乒乓球横扫该像素（对应论文 Fig. 2B 的 t=17→27 ms）**。真实通量跳变后连续 10 帧几乎都是 1：

- 旧段预测：$k$ 个 1 后变成 $(30.5+k)/(101+k)$，从 0.302 缓慢爬到 0.373；
- 新段预测：$k$ 个 1 后变成 $(0.5+k)/(1+k)$，从 0.50 爬到 0.95；
- 逐帧似然比（新/旧）≈ 1.66, 2.43, 2.62, 2.68, 2.69, 2.67, 2.65, 2.62, 2.59, 2.55 → 累积约 $9\times10^3$。

但变化点先验只有 $\gamma=10^{-5}$：$P(r_t=0)\propto\gamma\cdot L_{\text{new}}$，与 $(1-\gamma)L_{\text{old}}P(r_{t-1}=r)$ 相比，比值约 $10^{-5}\times9\times10^3\approx0.09$，即此时变化点概率仅 ~8%。**这解释了论文"保守但鲁棒"的工程性格：需要连续多帧强证据才翻后验**；一旦翻过去，后验移到 $r=0$，$\omega_t\to2/2=1$，输出立刻跳到当前帧（动态区冻结运动）。中途（后验质量摊在 $r\in\{0,1,2,3\}$ 上近似均匀）$H\approx\log_2 4=2$ bit，出现明显熵增前沿——这正是论文所说"上升的不确定性前锋 + 稳定尾迹"的运动签名。

**Phase C：物体通过后** 稳定性重新累积、后验重回尖峰、熵回落，循环重启。

## 4 · 工程视角

**硬件与实现**：所有结果用 `torch.compile` 在 **NVIDIA 4090 GPU** 上获得；嵌入式平台为 **NVIDIA Jetson Orin Nano**。作者明确指出进一步收益需自定义 CUDA kernel（融合算子、状态驻留寄存器，减少全局内存搬运）——**即当前实现尚未做 kernel 级优化**。

| 配置 | 输入吞吐 | 输出吞吐 | 分辨率 | 硬件/出处 |
|---|---|---|---|---|
| Bernoulli 实例 | ≈10,000 qFPS | 论文未报告（该行仅给输入） | 论文未报告 | 4090 |
| Binomial（4-bit，由 15 帧二值求和） | ≈150,000 qFPS | 论文未报告 | 论文未报告 | 4090 |
| 代表配置（Fig. 2D） | 51 kqFPS | 1650 FPS | 256×512 | 4090 |
| 全变体区间（5-bit 虚拟曝光，$N_{\text{sum}}=31$） | 51,000–280,000 qFPS | 1,600–9,000 FPS | 论文未报告 | 4090 |
| fast 变体（binomial + 梯度） | ≈41,000 qFPS | 1,280 FPS | 1 MPixel | 4090 |
| DoG（robust） | ≈260,000 qFPS @256×256 → ≈16,000 qFPS @1MP | 论文未报告（分分辨率） | 256×256 / 1 MP | 4090 |
| Log-Gabor（robust） | ≈115,000 qFPS @256×256 → >6,000 qFPS @1MP | 论文未报告（分分辨率） | 256×256 / 1 MP | 4090 |
| 梯度变体（嵌入式） | >10,000 qFPS（≤512×512）；≈3,200 qFPS @1MP | 论文未报告 | ≤512×512 / 1 MP | Jetson Orin Nano |
| 空间变化 Wiener 去噪 | – | ∼4,000 FPS | 论文未报告 | 论文未报告 |
| NVENC H.264 编码 | – | ∼6,000 FPS | 256×512 | GPU |

**延迟 / 对比基线**：Bit2Bit 吞吐 ≈ $3\times10^{-3}$ FPS（每帧约 300 s 优化，序列级延迟数小时），本文对应场景 **0.62 ms**，约五个数量级加速；相对 QBP 约 **10,000×** 加速；整体比 SOTA quanta 重建快 **最多四个数量级**，输出落在 kHz 量级。

**Trade-off 一览**
- **时间分辨率 vs 算力余量**：$N_{\text{sum}}$ binning（4-bit/15 帧、5-bit/31 帧）把 100 kHz 二进制传感器当 ≈3 kHz 多比特相机，吞吐上去了，但最小曝光升到约 **0.1–0.3 ms**，会引入轻微运动模糊。
- **空间结构保真 vs 速度**：梯度（最省）< DoG < Log-Gabor（最贵，且边缘附近易 ringing/blooming）；作者选择"偏 responsivity"——宁可动态物附近留噪声，也不要运动模糊（残噪可由下游去噪器兜底）。
- **内存**：设计上常数内存（每像素 top-K=5–8、常数时间递归）；**显存占用/内存带宽实测数字论文未报告**。
- **分辨率行为**：256×256 与 512×512 之间出现吞吐平台（overhead-bound），到 1024×1024 才转为亚线性增长（开始受内存带宽限制，megapixel 处饱和）。
- **压缩拓扑**：视频编解码比事件 delta 编码压缩率高 1–2 个数量级（同质量下），但事件编码在"严格 on-sensor 压缩"场景更省算力——论文明说这不是绝对排序，而是设计空间。
- **边缘部署**：与 4090 相比，Jetson 上 1 MP 只有 ≈3,200 qFPS（轻量梯度变体），**约差一个数量级**；若按 51 kqFPS 预期直接部署到边缘会严重错配。

## 5 · 数据与评测

**数据 / 采集条件（逐字取自全文）**
- **真实采集**：1-megapixel color quanta sensor（图 1 / 图 9 的彩色结果）。
- **极低光真实采集**：**SwissSPAD2 sensor**，平均 **<0.05 photons per pixel (PPP)**（对应 **<0.05 lux** 照明）。
- **受控真值评测**：**VisionSim dataset**（原文亦写作 VisionSIM [25]），提供精确 depth 与 flow 参考（定量表在 Extended Data Tab. 2，**主文未给数字**）。
- **图像质量量化**：**i2k high-speed dataset** [11]（对 QUIVER / gQIR / NAFNet / FastDVDNet / streaming EMA 做对比，见 Extended Data Figs. 1–2）。
- **时间稳定性真值**：从 i2k 取 40 ms 序列，用 **RIFE** 插值到 **96 kHz**；把本文模型作用于"干净高速序列"（强度视为方差可忽略的高斯 r.v.）得到目标窗口。
- **压缩评测**：由高速视频仿真的 photon cube，经 probabilistic events + 空间变化 Wiener 去噪后比较两条传输路径；事件 delta 阈值 0.02→1.0，视频 CRF 24→51。

**对比对象**
- 重建优先范式：**QBP**（align-and-merge）、**QUIVER**、**gQIR**、**NAFNet**、**FastDVDNet**、**streaming EMA**、**Bit2Bit**（作为性能天花板，推理期自监督去噪）。
- 专用硬件：**Canon EOS 77D**（30 FPS DSLR）、**Photron Infinicam**（200 FPS 高速）、**Bosch DINION IP starlight 8000 MP**（低光安防）、**Prophesee EVK4**（事件相机，配 **E2VID** 重建）。
- 下游模型（全部免训练）：**Canny**、**MOSSE**、**RAFT**、**DepthAnything-v2-s**、**YOLOv8 nano**、**RT-DETR**、**SAM**、**SAM 2**。

**关键量化结果（逐字）**
| 项目 | 数值 |
|---|---|
| 稳定性估计误差（ego-motion 场景，oracle global shutter） | motion blur RMSE **1.01** stops；noise RMSE **1.48** stops |
| 卡片洗牌（多速度场）global baseline | blur penalty **1.68** stops |
| 本文（局部自适应）该场景 blur RMSE | **0.26** stops |
| Log-Gabor 变体 | blur RMSE **0.72** stops（oracle 为 **1.39**）；noise RMSE **1.50** stops（oracle 为 **2.24**） |
| 整体 stability RMSE | **1.28** stops vs 全局基线 **2.0** |
| 0.72 stop 的物理含义 | 动态区过曝不超过最优时长的 **1.64×**（全局快门误差可达 **3×**） |
| 端到端任务吞吐 | 边缘检测 **4,000 FPS**；跟踪 **550 FPS**；光流 **~140 FPS**；QR 解码 **165 FPS**；夜间车辆检测 **400 FPS**（图 5A 另写 car detection **100 Hz**）；人体姿态 **1,000 FPS**；快速变体最高 **9,000 FPS** |
| 低光 QR 解码时延 | **6 ms** |
| 工作区间 | 在每帧光子检出概率的**中间 97%** 区间最可靠 |

> ⚠️ 主文未给出的数字（如各个下游任务的 mAP/EPE/depth 指标具体值、显存占用）一律记为「论文未报告」，不做推断。
> ⚠️ 提示：该 arXiv HTML 的引用编号疑似错位（正文把 BOCPD 引作 (16)，而参考文献列表 (21) 才是 Adams & MacKay；正文 (16) 位置对应 Canny）。检索时请以作者名而非编号为准。

## 6 · 能力与失败模式

**能做**
- 用一台 quanta 传感器 + 一层计算，覆盖通常需要多台专用相机分别负责的工况（夜间城市、低光高速 QR、低光自运动深度、需要绝对强度的分割）。
- 免训练、免微调地驱动从经典算子（Canny/MOSSE）到现代深度网络（RAFT/DepthAnything-v2/YOLO/RT-DETR/SAM/SAM 2）的完整任务层级。
- 输出图像化字段 → 可直接走硬件视频编码；内部更新率（约 100 kHz）与输出帧率**解耦**，按需读出。
- 因果、常数时间、固定内存的流式处理；静态区可累积 $10^4$–$10^5$ 帧证据而不糊。

**不能做 / 失败模式（含机制原因）**
1. **信息受限区（极低光 + 快速运动）**：0.02 PPP 的 Mandrill 旋转风扇场景中，"无法可靠区分真实场景动态与光子到达的随机性"——run-length 后验会**过度自信地停留在陈旧假设**上，导致漏检变点、过度积分、产生运动模糊。作者明言此时 SAM 2 仍能跟踪，但聚合体是"imperfect reconstruction"。
2. **高通量/饱和端反向失效**：光子检出近乎确定性时，微小模型失配导致**过于频繁的变化声明**与欠积分。
3. **中间 97% 之外不可靠**：这是统计变点检测器的原理性限制，不是调参能解决的。
4. **异方差噪声**：运动自适应积分天然使动态区噪声高于静态区；论文声称经典算子与深度网络对其鲁棒，并提供了可选的 Wiener 后处理兜底。
5. **因果性代价**：为 0.62 ms 级延迟放弃迭代优化与非因果对齐，因此在信号最稀缺处打不过 Bit2Bit 那类推理期训练方法（代价是 ~300 s/帧）。
6. **事件相机的镜像缺陷正是本文卖点**：DVS/E2VID 在静态区没有强度、纹理缺失，SAM 直接失败——但反过来，本文方式必须持续积分与传输图像化字段，带宽策略上不如稀疏异步流"天生省"。

### 隐含假设 (Hidden Assumptions)

- **观测模型只含散粒噪声**：$P(B_t=1)=1-e^{-\phi_t}$ 假设无读出噪声、无死时间、无串扰、无固定模式噪声；所有"可靠性边界"都建立在这个理想化似然上。
- **积分窗内场景静止**：SNR 上界推导显式假设 $\phi_t(\mathbf p)\equiv\phi(\mathbf p)$；论文虽标注失效像素并剔除，但该假设也是稳定性估计成立的前提。
- **变化只来自运动/光照跃迁**：Bernoulli/Binomial 似然只对"检出概率改变"敏感，无法在原理上区分"物体进入像素"与"该点自身变亮"。
- **危险率 $\gamma=10^{-5}$ 全局常数**：不随场景动态自适应的先验变化率——在变化频繁的序列里会反应慢，在长期静止序列里会过于保守（§3 的玩具演算正是这个效应）。
- **后验可由 top-K 近似**：$K$ 通常 5–8，隐含"run-length 概率自然集中在少数值附近"；长尾被截断，极端多模态场景（多物体以不同时标叠加）无保证。
- **下游模型对异方差噪声鲁棒且无需重训**：这是工程取舍（缺乏高速 quanta 标注数据）被写成的方法论前提，而非被证明的结论。
- **空间特征服从高斯 + 通道独立**：依赖 arcsine 方差稳定化 + 离线特征分解，等于假设协方差在场景间稳定可迁移。
- **仿真真值可代表真实动态**：时间稳定性真值来自 RIFE 插值到 96 kHz 的合成流，插值伪影会直接进入"真值"。
- **彩色路径的近似可接受**：用 Malvar-He-Cutler 从马赛克估计的"provisional luminance"足够驱动 run-length 空间特征。

## 7 · 与相关工作对比

| 方法 | 范式 | 是否重建图像 | 输出类型 | 是否需训练/重训 | 延迟定位 |
|---|---|---|---|---|---|
| 固定窗虚拟曝光（求和） | 传统积分 | 是（粗糙） | 强度图 | 否 | 低延迟但受全局噪声–模糊折中 |
| QBP | 离线 align-and-merge | 是（高质量） | 强度图 | 否（优化式） | 极慢（约 10,000× 慢于本文） |
| QUIVER / gQIR / NAFNet / FastDVDNet / streaming EMA | 学习式 quanta 复原 | 是 | 强度图 | 是 | 面向保真度，非 kHz 延迟 |
| Bit2Bit | 自监督（推理期训练） | 是（锐利） | 强度图 | 测试时优化 | ≈$3\times10^{-3}$ FPS，数小时级 |
| Quanta Neural Networks | 重建无关神经网络 | 否 | 特征/任务输出 | **需重训或微调** | 高效但受标注稀缺拖累 |
| Eulerian single-photon vision | 速度调谐滤波器组 | 否 | 手算相位类信号 | 否 | 局限于边缘/运动估计等少数任务 |
| DVS / DAVIS + E2VID | 模拟阈值异步事件 | 需重建才有强度 | 二值极性事件 | 异步算法或重建网络 | µs 级、高动态范围，但丢绝对强度 |
| **Probabilistic Events（本文）** | **递归贝叶斯信念状态** | **否（隐式自适应聚合）** | **稳定性图 + 熵变 + 运动自适应 flux（图像化）** | **否，零重训** | **因果、常数时间、kHz 输出** |

**面试 Tip**：被问"probabilistic events 跟 event camera 有什么本质区别？"三句话答完——(1) **触发机制**：DVS 是固定模拟阈值的确定性极性触发，本文是每像素对"距上次变化的时间"维护**概率后验**；(2) **输出内容**：DVS 只有稀疏二值极性、丢绝对强度，本文额外输出**连续时间稳定性（含时标）+ 熵不确定性 + 带绝对强度的 motion-aware flux**，所以能直接喂 SAM 这类依赖纹理/强度的模型；(3) **系统含义**：DVS 用异步稀疏传输省带宽，本文**解耦内部 100 kHz 状态与按需输出帧率**，输出是图像化字段因此能直接走 H.264 等成熟硬件编解码。如果面试官追问"那它的代价是什么"，答：因果估计 ⇒ 放弃非因果对齐，在光子极稀 + 运动极快时无法把真实变化与散粒噪声分开（只在光子检出概率中间 97% 区间可靠）。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-15)

**Repo 状态核查**：全文（含参考文献）**没有给出本文的官方代码库**。正文/参考文献中出现的 `github.com` 链接均为第三方依赖（`ultralytics/ultralytics`、`WISION-Lab/visionsim`），不属于本文实现的官方仓库；因此**无 issue 流可供引用**。以下 pitfall **由 §6 失败模式 + §1/§2 的方法约束推导**，未经 issue 验证，标注为 `DERIVED (unverified)`。

1. **`DERIVED`｜危险率 $\gamma=10^{-5}$ 是硬编码常量，低光场景会"反应迟钝"**。§6 失败模式 1（后验对陈旧假设过度自信、漏检变点）直接来自 §2 的 hazard 机制：$\gamma$ 越小，变化点先验越低（§3 玩具演算显示 ~10 帧强证据才推动 ~8% 概率质量）。论文报告的工作区间是"光子检出概率中间 97%"，**没有给出任何按光照/运动自适应调 $\gamma$ 的规则**。工程后果：把 <0.05 lux 场景直接套用默认 $\gamma$ 会看到明显运动模糊，而重调 $\gamma$ 又缺乏论文提供的标定流程。`UNVERIFIED`

2. **`DERIVED`｜top-K 分层剪枝 + 每像素变长状态，与静态图导出/边缘部署结构性冲突**。方法约束：每帧需要对 run-length 概率**排序并保留 top-K（K≈5–8）再重归一化**，且每像素携带 $\alpha_s,\beta_s,\mu_s$ 等**随 run 数增长的历史量**。这是"每帧一次 per-pixel sort + 变长/有状态控制流"，与 ONNX/TensorRT 的静态 shape、无数据依赖分支的假设相冲突；同时论文承认当前实现是 `torch.compile`，**自定义 CUDA kernel（状态驻留寄存器、融合算子）尚未做**。工程后果：直接照搬论文吞吐预期做边缘部署会大幅落空——Jetson Orin Nano 上 1 MPixel 只有 ≈3,200 qFPS，而 4090 上是 ≈41,000 qFPS（fast 变体），差约一个数量级。`UNVERIFIED`

3. **`DERIVED`｜极小概率的对数熵计算数值不稳，论文未报告保护措施**。方法约束：$H_t=-\sum_r P\log P$ 作用在**已剪枝并重归一化**的后验上；低光场景下 top-K 之外的尾部质量被丢弃，剩余概率可能极小。§6 失败模式 1 正是低光场景。工程后果：需要自行加 `eps` 截断与 log-domain 累加，否则会出现 `-0*log0` / 下溢导致熵变图 $\Delta H_t$ 出现伪尖峰（而该信号被论文当作"运动边缘检测器"直接使用）。`UNVERIFIED`

4. **`DERIVED`｜颜色路径依赖一个"近似亮度"估计来驱动空间特征，且未开源**。方法约束：逐像素 binomial 直接跑在马赛克 raw frame 上，空间特征所需的亮度来自 **Malvar-He-Cutler** 的 provisional luminance（论文自称"approximate"），随后用**标准 off-the-shelf debayer** 输出彩色。工程后果：换 CFA 排布或换 debayer 实现时，run-length 空间特征的质量会随之漂移；论文未给出量化敏感度分析（主文未报告相关 ablation 数字）。`UNVERIFIED`

---

[← Back to Event & Quanta Sensing README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2608.27584 -->
