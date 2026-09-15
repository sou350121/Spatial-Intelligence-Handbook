<!-- ontology-5axis
problem: VO
representation: n/a
sensor: 4D-radar
paradigm: geometric
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# 稠密软加权雷达自速度估计 (Dense Soft Weighting for Radar Ego-Velocity Estimation)

> **发布时间**：2026-07-29（arXiv:2607.26980v1 [cs.RO]）
> **论文 / 模型名**：Dense Soft Weighting (DSW)
> **核心定位**：把雷达自速度估计从"CFAR 二值检测 → 稀疏点云拟合"改成"每个 range-Doppler 单元一个连续置信权重 → 鲁棒加权最小二乘"，免训练、跨雷达配置迁移、嵌入式实时，同一条共享 ESKF 后端下把 ColoRadar 平均平移 APE 从 2.12 m 降到 1.17 m。

导语：单芯片毫米波雷达测自速度时，传统流水线先用 CFAR 把稠密 range-Doppler 谱砍成稀疏点云，把"能量弱但几何上有用"的离轴多普勒证据提前丢掉了。DSW 保留整张稠密谱，用 beam-domain 功率 × 集中度给每个 cell 打一个软权重，再用一次 Cauchy 重加权的最小二乘闭合解出速度，并从同一次加权法方程里解析地吐出协方差给 ESKF。

## X-Ray 开场

CFAR 是一个"保留/丢弃"的硬判决，它做判决时还不知道速度几何长什么样——离轴、低 SNR 的 cell 往往正是约束横向速度 $v_y$ 的那批测量。DSW 的做法是：不删任何 cell，改成给每个 range-Doppler cell 一个 $[0,1]$ 的连续置信度（功率归一化分数 × peak-to-median 比的 sigmoid 门），于是速度估计退化成带权最小二乘的闭式解，协方差也能从加权法方程里直接读出来——不需要任何平台相关训练数据。对做 spatial AI 的人意义在于：它证明了"预处理阈值化"这一普遍的信息瓶颈，可以用一个**软**的、可解析微分的等价物替换，并且软化的代价比想象中低（嵌入式单核仍实时）。

## 📍 研究全景时间线

```
雷达自速度/里程计演进（示意，按论文引用的方法族排序）

Kellner 单帧公式 ──► Doer 等 Radar-Odometry 族 ──► EKF-RIO 后端族
(多普勒→v 线性系统)     (3点 RANSAC + LS + 残差协方差)   (ESKF + 在线外参/时延标定)
        │                        │                              │
        │                        ▼                              ▼
        │              MRIO (Cauchy+LM)                Kim 时延标定 / 紧耦合 EKF-RIO
        │              RIV-SLAM (多策略 WLS)            地面/IMU 速度先验
        │              CREVE / VGC-RIO (点云接口不变)          │
        ▼                                                      ▼
   检测器先行 = 信息瓶颈──────┬──────────────────────────────► 后端只吃前端给的 (v, Σ)
                             │
   稠密/直接路线 ──► DBE (DBF 提质但仍留点云接口)
                ──► DRO (旋转雷达稠密 SE(2) 配准，非单芯片)
                ──► milliEgo / RadarHD / Radarize / BatMobility / 4DEgo / S³E / UNRIO
                     (学习权重/运动/不确定度，依赖平台+训练分布)
                             │
                             ▼
                   ★ 2026 DSW：解析稠密软加权 ──► 免训练 / 跨配置 / 闭式协方差
                             │
                             └── 本文局限：仅单芯片、手持/推车速度；
                                 侧向运动受 sidelobe 角偏置 → v_y 有偏且无法被加权消除
```

DSW 站在"检测器先行"和"学习稠密"两条路的中间：既不设检测器，也不学任何东西。

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| FMCW 前端（ADC 解码、MIMO reshape、Range/Doppler FFT、TDM 解复用、beamforming） | 原始 ADC / IQ 帧 $[N\cdot2]$ | 稠密功率张量 $\mathcal{P}=|\mathrm{RDA}|^2\in\mathbb{R}^{D\times B\times R}$，$B=B_\alpha B_\beta$ | 无训练；beamforming 用芯片 TX/RX 布局（chip-aware），非通用变换 |
| 单元置信权重（Eq.4–6） | 单元 $i=(d_i,r_i)$ 的 beam 谱 $S_i(b)$ | $w_i=u_i v_i\in[0,1]$ | 无训练；$\tau=200,\kappa=0.5$ 全数据集固定，无 per-platform 调参 |
| 每 cell LOS 与鲁棒速度估计（Eq.7–10） | $\{\hat b_i\}$、$\{w_i\}$、$\{d_i\}$ | $\hat{\mathbf v}^R\in\mathbb{R}^3$ | 无训练；峰位三点抛物线插值做 sub-bin 角度精化；1 次 Cauchy IRLS |
| 协方差装配（Eq.11–14） | 加权法方程 + 角度方差 + 多普勒分辨率 | $\bm\Sigma_v^R\in\mathbb{R}^{3\times3}$ | 无训练；闭式，含 WLS/角度/多普勒三项 |
| 传感器→体坐标系（杠杆臂） | $\hat{\mathbf v}^R,\bm\Sigma_v^R$、陀螺 $\bm\omega$、外参 $\bm r$ | $\hat{\mathbf v}^B,\bm\Sigma^B$ | 无训练；移除 $\bm\omega\times\bm r$，前端输出即体速度 |
| ESKF 后端 | $(\hat{\mathbf v}^B,\bm\Sigma^B)$ + IMU | 轨迹 | 所有解析方法**共享同一 ESKF**（同一 $\mathbf Q$、同一 $t_d$、同一 $\chi^2_3$ 门），隔离前端效应 |

### 1.2 关键机制

传统 CFAR 检查两件事——cell 有多少功率、功率在多少个 beam 上散着——然后做二值判决。DSW 的洞见是：**这两个量本身就足以定义一个连续权重，根本不需要那个阈值。**

$$\text{CFAR 检统计量} \; \to \; \text{软门}:\quad v_i=\sigma\!\left(\frac{\log(P_i/C_i)-\log\tau}{\kappa}\right)$$

$\tau$ 是 $v_i=1/2$ 的 peak-to-median 比，$\kappa$ 控制斜率；$P_i/C_i$ 就是 cell-averaging CFAR 检统计量的 cross-beam 版本，median $C_i$ 顶替局部噪声底估计。文中明确说：peak-to-median 比**很少超过约 $100\times$**，而 $\tau=200$ —— 所以硬阈值在 $\tau$ 处会保留太少的 cell 并让稠密估计退化（Table 4 中 hard gate 直接发散）。

**⚡ Eureka Moment：把检测器阈值从"硬边界"变成"以同一工作点为中心的 sigmoid 软门"，于是低于阈值的弱离轴多普勒证据以低权重（而非零）继续参与速度几何 —— 不删 cell，只降权。**

### 1.3 信息流 ASCII 图

```
Raw ADC frame ──► ADC decode / IQ ──► MIMO reshape [D,Tx,Rx,R]
                                          │
                        Range FFT + Doppler FFT + TDM demux
                                          │  ℂ^{D×Tx×Rx×R}
                                    Chip-aware beamform (az–el grid B=Bα·Bβ)
                                          │  𝒫 = |RDA|² ∈ ℝ^{D×B×R}
                 ┌────────────────────────┴────────────────────────┐
        【灰化旁路·被跳过】                               【DSW 主干】
         CFAR 阈值 → 二值点云                        每 cell: S_i(b)=𝒫(d_i,b,r_i)
                 │                                       P_i=max S, C_i=med S
      RANSAC + LS (稀疏估计)                          w_i = √(P_i/max P) · σ(log(P_i/C_i)/κ)
                 │                                       │  ŵ_i ∈ [0,1]
                 │                                  峰位 û_i 三点抛物线精化 (sub-bin LOS)
                 │                                       │  {û_i, d_i, w_i}
                 │                                  Robust WLS 闭式 + 1×Cauchy
                 │                                       │  v̂^R ∈ ℝ³
                 │                                  协方差装配 Σ=Σ_wls+Σ_ang+Σ_dop
                 │                                       │  Σ_v^R
                 │                                  传感器→体杠杆臂 ω×r
                 └───────────────────┬───────────────────┘
                                 (v̂^B, Σ^B)   ← 前端唯一输出
                                     │
                            共享 loose-coupled ESKF (含 t_d 在线标定)
                                     │
                                  轨迹
```

## 2 · 数学核心

📌 **Napkin Formula**：

$$\hat{\mathbf v}^{R}=-\bigl(\mathbf U^{\mathsf T}\mathbf W\bm\rho\,\mathbf U\bigr)^{-1}\mathbf U^{\mathsf T}\mathbf W\bm\rho\,\mathbf d,\qquad w_i=\underbrace{\sqrt{P_i/\max_j P_j}}_{\text{功率分数}}\cdot\underbrace{\sigma\!\Big(\tfrac{\log(P_i/C_i)-\log\tau}{\kappa}\Big)}_{\text{集中度软门}}$$

——就是把每一个 Doppler cell 当成一支"带置信度的方向投票"，加权投票得到速度；没有检测器，没有采样，没有训练。

**目标**：从稠密 range-Doppler 谱直接估出三维自速度与协方差，且不依赖平台训练数据。

**测量模型（Eq.2–3）**：每个 cell 贡献一个 LOS 多普勒约束
$$d_i=-\hat{\mathbf u}_i^{\mathsf T}\mathbf v^R+\epsilon_i \quad\Longrightarrow\quad \mathbf d=-\mathbf U\mathbf v^R+\bm\epsilon,\quad \mathbf U=[\hat{\mathbf u}_1,\dots,\hat{\mathbf u}_N]^{\mathsf T}$$
单个 cell 只在 $\hat{\mathbf u}_i$ 方向上约束 $\mathbf v^R$，所以三维速度必须靠整个 az–el 网格上**多个加权 LOS 方向**共同张成。

**变量说明**：
- $d_i$：cell $i$ 的 Doppler 径向速度；$\hat{\mathbf u}_i$：雷达传感器系下的单位 LOS（由精化后角度球→笛卡尔得到）。
- $P_i=\max_b S_i(b)$、$C_i=\mathrm{med}_b S_i(b)$：beam 域峰值与 cross-beam 中位数。
- $u_i=\sqrt{P_i/\max_j P_j}$：功率分数（开根号限制单个高亮反射体的杠杆）。
- $v_i=\sigma(\cdot)$：集中度门，$\tau=200,\kappa=0.5$ 全局固定。
- $\mathbf W=\mathrm{diag}(w_1,\dots,w_N)$。
- $\rho_i=\dfrac{1}{1+(r_i/(c\,\hat\sigma_r))^2}$，残差 $r_i=d_i+\hat{\mathbf u}_i^{\mathsf T}\hat{\mathbf v}^{R(0)}$，$c=2$，$\hat\sigma_r$ 由残差 MAD 估计，只跑 1 次（作者称再迭代 per-frame RMSE 变化 $<10^{-4}\,\mathrm{m/s}$）。

**协方差（Eq.11–14）**：
$$\bm\Sigma_v^R=\underbrace{\hat\sigma_r^2(\mathbf U^{\mathsf T}\mathbf W\bm\rho\mathbf U)^{-1}}_{\text{WLS 拟合}}+\underbrace{\|\hat{\mathbf v}^R\|^2\,\mathbf J\,\mathrm{diag}(\sigma_\alpha^2,\sigma_\beta^2)\mathbf J^{\mathsf T}}_{\text{波束指向}}+ \underbrace{\sigma_{\mathrm{dop}}^2\mathbf I}_{\text{多普勒量化}}$$
第二项随速度模长 $\|\hat{\mathbf v}^R\|$ 增长（角度误差被速度放大），第三项由 Doppler bin 宽 $\Delta v_{\mathrm{bin}}$ 决定的量化底。

**直觉**：几何弱轴（如方位主导阵列下的俯仰 $v_z$）法方程对角元小 → $(\mathbf U^{\mathsf T}\mathbf W\bm\rho\mathbf U)^{-1}$ 对应分量大 → 协方差自动变大，后端知道"这一轴我不确定"。这是闭式协方差相对于"残差 sandwich 拟合"的核心优势。

## 3 · 带数字走一遍（玩具设定，2D）

**玩具设定**（非论文数据）：只估平面速度 $(v_x,v_y)$，真值 $\mathbf v^\star=(2,0)\ \mathrm{m/s}$。三个 cell：

| cell | LOS $\hat{\mathbf u}_i$ | Doppler $d_i$ | 权重 $w_i$ |
|---|---|---|---|
| A（boresight） | $(1,0)$ | $-2.00$ | $0.9$ |
| B（离轴 45°） | $(0.707,0.707)$ | $-1.414$ | $0.6$ |
| C（弱/低集中度） | $(0,1)$ | $0.00$ | $0.05$ |

权重按 DSW 逻辑想象：C 的 beam 能量散（$P_i\approx C_i$），门 $v_i\to0$。

$$\mathbf U=\begin{bmatrix}1&0\\0.707&0.707\\0&1\end{bmatrix},\ \mathbf d=\begin{bmatrix}-2.00\\-1.414\\0\end{bmatrix},\ \mathbf W=\mathrm{diag}(0.9,0.6,0.05)$$

$$\mathbf U^{\mathsf T}\mathbf W\mathbf U=\begin{bmatrix}1.20&0.30\\0.30&0.35\end{bmatrix},\qquad \mathbf U^{\mathsf T}\mathbf W\mathbf d=\begin{bmatrix}-2.40\\-0.60\end{bmatrix}$$

$$\hat{\mathbf v}=-\begin{bmatrix}1.20&0.30\\0.30&0.35\end{bmatrix}^{-1}\begin{bmatrix}-2.40\\-0.60\end{bmatrix}= -\begin{bmatrix}\phantom{-}2.000\\\phantom{-}0.000\end{bmatrix}\cdot(-1)=\;(2.00,\;0.00)\ \mathrm{m/s}\ \checkmark$$

无噪声下精确恢复真值。

**关键对比**：**去掉离轴 cell B**（只剩 A 和 C）。此时 $\mathbf U^{\mathsf T}\mathbf W\mathbf U=\mathrm{diag}(0.9,0.05)$，$v_y$ 的信息量只有 $0.05$——协方差的 $yy$ 分量直接放大 20 倍。也就是说：boresight 的 A 和弱 cell 的 C 几乎**只能约束 $v_x$**，约束 $v_y$ 的正是被 CFAR 常常砍掉的离轴 B。这精确复现了 §5.1 与 §5.7 的论断——横向运动下的增益来自 off-boresight 单元。

## 4 · 工程视角

论文报告了 Table 3 的 per-frame 延迟（median, ms），按数据集 × 平台 × core 数拆分。**以下数字全部逐字来自 Table 3，非本文估算。**

| 数据集 (RD cells) | 平台 | DSW 1×CPU | DSW 4×CPU | DSW GPU |
|---|---|---|---|---|
| ColoRadar (16 384) | Laptop | 17.8 | 8.8 | 2.0 |
| ColoRadar (16 384) | Orin NX | 71 | 35 | 12 |
| Self-collected (15 300) | Laptop | 17.7 | 8.9 | 2.1 |
| Self-collected (15 300) | Orin NX | 71 | 36 | 13 |
| Radarize (3072) | Laptop | 3.8 | 1.9 | 1.8 |
| Radarize (3072) | Orin NX | 15 | 8 | 11 |

- **单核延迟对 cell 数线性**：论文给出 $1.1\text{–}1.2\,\mathrm{\SIUnitSymbolMicro s}$/cell，从 3072 cell 的 Radarize（3.8 ms）到 16 384 cell 的 ColoRadar（17.8 ms）。
- **GPU 并行性**：per-cell 操作相互独立、无检测步骤、无数据依赖分支，加权最小二乘退化为对 cell 的累加，因此映射到数据并行硬件上，GPU 延迟 "$1.8\text{ ms}$ 至 $2.1\text{ ms}$，几乎与网格大小无关"。
- **帧预算**：论文称每个解析前端在单 CPU 核上即满足其传感器预算（ColoRadar 与自采 10 Hz，Radarize 30 Hz），笔记本与 Orin NX 皆然。
- **学习基线（PyTorch FP32 推理）**：Laptop GPU 上 Radarize 网络 3.4 ms、milliEgo 1.2 ms；Orin NX 上两者**只有用集成 GPU 才满足 30 Hz**（Radarize 220/134/21、milliEgo 81/48/7，1×/4×/GPU）。
- **ptcloud_onboard 被排除出 Table 3**：其检测跑在雷达 MCU 而非 host 上，无法在统一算力目标上测端到端延迟；只有 host 侧估计步骤（$0.5\text{ ms}$ 到 $9\text{ ms}$）。

**未报告项（诚实标注）**：算法级内存占用 / VRAM / 带宽、power 消耗均**论文未报告**。硬件平台规格（Jetson Orin NX 16GB，8-core Arm Cortex-A78AE、16 GB LPDDR5、1024-core Ampere + 32 Tensor Cores；Laptop Intel Core i9-14900HX、64 GB RAM、RTX 4090 Mobile）在 §4.2 给出，但那是平台规格而非算法资源消耗。

**部署 trade-off**：DSW 的延迟随 range-Doppler cell 数线性增长，而这一项由雷达 chirp 配置决定而不是算法能控——要换更细的 range/Doppler 分辨率就要接受更高的 per-frame 单核成本；GPU 化能把它压平。它**必须吃 DCA1000 原始 ADC cube**（见 §6 隐含假设），因此只能跑在能拿到 raw ADC 的 host 上，无法在只吐 on-chip point cloud 的封闭 DSP 上部署。

## 5 · 数据与评测

**三个数据集（Table 1 逐字）**：

| 属性 | ColoRadar | Radarize | Self-collected |
|---|---|---|---|
| 平台 | Handheld | Handheld, cart, robot | Handheld |
| 雷达芯片 | AWR1843 BOOST | AWR1843 BOOST | AWR6843 AOP-EVM |
| 采集 | DCA1000 | DCA1000 | DCA1000 |
| IMU | 3DM-GX5-25 | Bosch BMI055 | Xsens MTi-320 |
| Ground truth | LiDAR, MoCap | VIO | MoCap |
| 运动 | 2D | 2D | 3D |
| 中心频率 $f_c$ [GHz] | 77.6 | 78.7 | 61.0 |
| 带宽 $B$ [GHz] | 1.20 | 3.36 | 1.91 |
| ADC rate [MHz] | 10.67 | 2.29 | 4.68 |
| Ramp / Idle / PRT [µs] | 20.0 / 110 / 130 | 50.0 / 122 / 172 | 63.75 / 38.44 / 102.19 |
| 帧 $T_f$ [ms] | 100 | 33.3 | 100 |
| Samples/chirp $N_s$ / Chirps $N_c$ | 128 / 128 | 96 / 32 | 255 / 60 |
| 天线 $N_{tx}/N_{rx}$ | 3×4 | 3×4 | 3×4 |
| Az./El. FoV [°] | 60/15 | 60/15 | 60/60 |

**协议与使用范围（逐字）**：
- **ColoRadar** 含 $52$ 条手持序列、总计超过 $145\,\mathrm{min}$；本文用 3 条序列，覆盖 $336.8\,\mathrm{s}$ 与 $300.34\,\mathrm{m}$（缓存 GT 轨迹），全用 lidar-SLAM 参考。
- **Radarize** 含 $146$ 条室内手持/推车/机器人序列；held-out split 为 $89$ 条序列、$92.9\,\mathrm{min}$、$3.28\,\mathrm{km}$。该数据集**没有独立 GT 系统或独立 IMU**，按原协议用 T265 视觉惯性轨迹作 pseudo-ground truth、用 T265 内置 IMU 作惯性输入。
- **Self-collected** 用 AWR6843AOP-EVM，$50$ 条序列、约 $\sim30{,}000$ 帧、$10\,\mathrm{Hz}$，10 相机 Vicon Vero v2.2 动捕 GT，轨迹时钟用离线 per-trajectory 时偏（$\pmb{t_d}$）对齐。

**Baselines**：点云族 `ptcloud_onboard`（TI on-chip cloud）、`ptcloud_dsp_capon`（Capon DBF，DBE）、`ptcloud_dsp_fft`（FFT/Bartlett AoA），均走 3 点 RANSAC + LS（$\geq6$ inliers 时 ODR 精化）；学习族 `Radarize`（Doppler-flow 网络）与 `milliEgo`（雷达惯性网络），在 Radarize held-out split 上以 pose 级比较。所有解析前端喂**同一个** ESKF。

**关键指标（逐字）**：
- ColoRadar：平均 APE$_t$ 由 $2.12\,\mathrm{m}$（最强点云基线 ptcloud_dsp_capon）降到 $1.17\,\mathrm{m}$，对应 $45\%$ 缩减；平均 RPE$_t$ 降到 $0.92\,\mathrm{m}$，点云基线为 $1.38$ 和 $1.43\,\mathrm{m}$。
- Self-collected：平均 APE$_t$ 由 $0.39\,\mathrm{m}$ 降到 $0.27\,\mathrm{m}$。
- Radarize held-out：DSW $1.11\,\mathrm{m}$ 平均平移 APE，milliEgo $4.22\,\mathrm{m}$，Radarize 网络 $0.81\,\mathrm{m}$；median 序列上差距缩小到 $0.77\,\mathrm{m}$ vs $0.71\,\mathrm{m}$；DSW 在 $69\%$ 的序列上 per-frame forward-velocity RMSE 更低。
- 摘要总结：相对最强 CFAR 点云基线，平均绝对位姿误差降低 $31\text{–}45\%$。

**消融（Table 4，六个主序列均值）**：默认 DSW APE$_t=0.76\,\mathrm{m}$、$\Delta v=0.23\,\mathrm{m/s}$；power score only $2.47$/$0.32$；concentration gate only $2.97$/$0.36$；hard gate **发散**（>200 m）；scalar $\bm\Sigma_v$（vs 三分量）$0.79$/$0.23$；$\tau=100/400$ 为 $0.77/0.77$；$\kappa=0.25/1.0$ 为 $1.11/1.02$。

## 6 · 能力与失败模式

**能做**：
- 在每个评测序列上拿到最低 per-frame 自速度 RMSE（$\Delta v$ 列）。
- 跨雷达 chip / 配置迁移不重调参：同一套 $\tau=200,\kappa=0.5$ 从 AWR1843BOOST 的 60°/15° 搬到 AWR6843AOP 的 60°/60°，在自采 3D 手持数据上仍拿最低 $\Delta v$（$0.08\text{–}0.12\,\mathrm{m/s}$）。
- 训练-free 地贴近/局部超过学习基线（Radarize 上 mean APE 输给网络，但 median 逼近、$69\%$ 序列前向速度更准）。
- 闭式协方差可直接插进标准 ESKF，并在几何弱轴上自动放大不确定度。

**不能做 / 失败模式**：
- **侧向运动下的 $v_y$ 有偏（bias 而非噪声）**：sidelobe 泄漏让 per-cell angle-FFT 方向被拉向 boresight，$\hat{\mathbf u}_i$ 低估横向投影 → $\hat v_y$ 有偏。论文明确：**加权聚合消不掉这个误差，因为它进的是几何矩阵 $\mathbf U$ 而不是残差**。解法需 sidelobe-aware DoA（Capon/MUSIC/稀疏贝叶斯）。
- **RPE 不总是赢**：自采的短 $1\,\mathrm{m}$ 窗口上点云基线在 3 条里 2 条 RPE$_t$ 更好（如 sequence_01 $0.10\,\mathrm{m}$ vs $0.16\,\mathrm{m}$）。
- **协方差在重多径下可能过度自信**：模型假设残差白噪声、忽略相邻 Doppler bin 的 angle-FFT sidelobe 相关性。
- **受益范围有限**：当一帧里已有高 SNR、宽角展布检测时，二值检测已经给出良态稀疏集，两前端结果接近——DSW 的增益只在**横向/离轴运动、低反射率场景、单轴几何**下显著。
- **仅在单芯片、手持/推车速度**验证；空中与更高速度地面平台未评估。
- **旋转精度不受前端支配**：雷达以速度测量进入 loose-coupled ESKF，attitude 主要由 IMU 传播决定；Radarize 上偏大的旋转误差被归因于惯性/pseudo-GT 设置而非雷达权重。

### 隐含假设 (Hidden Assumptions)

1. **可拿到原始 ADC cube（DCA1000）**：DSW 跑在完整 range-Doppler cube 上，因此要求 raw ADC 采集。只吐 on-chip DSP point cloud 的封闭单芯片流水线**用不了**。
2. **已知芯片 TX/RX 布局**：beamforming 是 chip-aware 的，$B=B_\alpha B_\beta$ 网格由天线布局决定；换阵列需要重构 beamforming 网格。
3. **静态场景主导多普勒**：$\epsilon_i$ 里含"任何运动反射体的径向速度"，但权重（尤其集中度门）假设单个峰主导——多个运动物体共占一个 cell 时权重会误判。
4. **peak-to-median 比不过高**：作者称该比很少超过约 $100\times$，所以 $\tau=200$ 是"软门中心"；若某场景帧的集中度真的很高，门会饱和到 1，判别力下降。
5. **残差白噪声**：协方差三项推导假设 WLS 残差独立同分布，忽略角度谱 sidelobe 跨 bin 相关。
6. **单个固定截止 $c=2$、单次 Cauchy 迭代足够**：基于"低 outlier 序列"上再迭代 RMSE 变化 $<10^{-4}\,\mathrm{m/s}$ 的 pilot 结论。
7. **离线已知时空外参**：雷达-IMU 空间外参离线标定，时间偏置 $t_d$ 在线估。

## 7 · 与相关工作对比

| 方法族 | 代表 | 检测器 | 输入接口 | 平台依赖 | 协方差来源 |
|---|---|---|---|---|---|
| 稀疏点云 RANSAC+LS | Kellner, Doer 等 | CFAR 硬阈值 | 稀疏点云 | 检测器 + DSP 实现 | inlier 残差拟合 |
| 点云鲁棒化 | CREVE, VGC-RIO | CFAR | 点云（接口不变） | 中 | 残差 |
| 点云鲁棒损失 | MRIO (Cauchy+LM), RIV-SLAM | CFAR | 点云 | 中 | 残差/多策略 |
| DBF 提质 | DBE | 仍留点云接口 | 点云 | 中 | 残差 |
| 旋转雷达稠密 | DRO | 无 | 全景稠密强度 | 旋转雷达专用 | — |
| 学习稠密 | milliEgo, RadarHD, Radarize, BatMobility, 4DEgo, S³E, UNRIO | 学出来的权重/运动 | 谱/热图 | **强**（chip+chirp+场景） | 学习不确定度头 |
| **DSW (本文)** | — | **无检测器** | **稠密 range-Doppler-angle** | **弱**（解析、固定超参） | **闭式（WLS+角度+Doppler）** |

**定位**：DSW 与 UNRIO 结构最像（都是"生成 Doppler 证据 + 加权最小二乘 + 不确定度"），差别在 UNRIO 用 transformer 预测 Doppler 图像并学出不确定度头，DSW 则把权重与协方差**从雷达谱本身解析地导出**，从而不做 per-platform 训练、可跨配置迁移。

**面试 Tip**：被问到"你和学习型稠密雷达里程计（Radarize/milliEgo/UNRIO）什么区别？"——**别说"我更准"**（Radarize 在它原生训练分布上 mean APE 是 $0.81\,\mathrm{m}$，DSW $1.11\,\mathrm{m}$，DSW 输）。要说：**(a) 免训练 → 无平台/场景分布依赖；(b) 协方差是闭式测量导出，不是学的头；(c) 单核 CPU 就能实时，不依赖 GPU。** 然后补一句它的诚实边界："median 序列上已经和 Radarize 打平（$0.77$ vs $0.71\,\mathrm{m}$），前向速度在 $69\%$ 序列上更准，但侧向运动受 sidelobe 角偏置是有偏误差，加权消不掉。"

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-15)

**Repo 状态**：论文全文**未出现任何 `github.com` 链接**，也未给出官方代码仓库地址。因此以下 pitfall **不含 repo URL / commit / issue 编号**，全部由 §6 失败模式 + §3 方法约束推导，**未经 issue 流验证**。若后续论文公开 repo，这三条应优先在 issue 中核对。

**Pitfall 1 — 只有 on-chip point cloud 的部署根本跑不起来。**
- 机制来源（§6 失败模式 / §4.1）："dense soft weighting requires [raw ADC captures] because it operates on the full range-Doppler cube rather than on detected point clouds."
- 方法约束（§3.1–3.2）：DSW 的输入是 ADC 解码 → MIMO reshape → Range/Doppler FFT → beamform 得到的稠密功率张量 $\mathcal{P}\in\mathbb{R}^{D\times B\times R}$，它**没有**从点云反推谱的路径。
- 后果：任何只暴露 TI 片上 DSP 点云的封闭雷达（或只能读 `ptcloud_onboard` 的机器人平台）无法使用 DSW；必须自带 DCA1000 或等价 raw 采集通道。论文本身在自采数据上也因为"on-chip cloud is unavailable"而改用 `ptcloud_dsp_fft` 替代 `ptcloud_onboard`——这正说明 raw cube 是硬性前置。

**Pitfall 2 — 单核延迟对 cell 数线性，抬高分辨率即可击穿帧预算。**
- 机制来源（§5.6）："single-core latency is linear in the grid, at $1.1\,\mathrm{\SIUnitSymbolMicro s}$ to $1.2\,\mathrm{\SIUnitSymbolMicro s}$ per cell"，ColoRadar 16 384 cell 在 Orin NX 单核上要 $71\,\mathrm{ms}$。
- 方法约束（§3.2 / §3.4）：每个 cell 都要做 beam 选择 + 三点抛物线角度精化 + 权重计算，$N=D\times R$ 完全由 chirp 配置决定。
- 后果：$71\,\mathrm{ms}$ 相对 10 Hz 的 $100\,\mathrm{ms}$ 预算已用掉七成；把 range-Doppler 分辨率提一档（或换更密集的 chirp 配置），单核即可能超帧预算，此时**只能上 GPU**（论文 GPU 路径 $12\text{–}13\,\mathrm{ms}$，近乎与网格无关）。图省事地在 MCU 上跑 CPU 版会直接掉帧。

**Pitfall 3 — 把软门"优化"成硬门会让滤波器发散。**
- 机制来源（§6 失败模式 + §5.2）："Replacing the soft gate with a hard threshold at the same operating point makes the trajectory diverge, as too few cells remain to condition the normal matrix"，Table 4 中 hard gate 平均 APE$_t$ 达 $>>200\,\mathrm{m}$ 级别（发散）。
- 方法约束（§3.4）："the peak-to-median ratio rarely exceeds $\sim100\times$, below $\tau=200$" —— 若把 sigmoid 换成 $\tau$ 处的二值门，绝大多数 cell 被判 0，$\mathbf U^{\mathsf T}\mathbf W\bm\rho\mathbf U$ 秩亏/病态，WLS 闭式解失效。
- 后果：任何"加速"动机下的工程简化——例如把权重 threshold 到 0/1、为了省算力只保留高权重 cell——都会复现这个发散。**软化不是精度优化，是可解性前提。** 同理，$\tau$ 在 $2\times$ 范围内不敏感（$0.77/0.77$），但 $\kappa$ 变尖锐/变平滑都会回退（$1.11/1.02$ vs 默认 $0.76$），说明这两个全局常数不能随意重调。

---
[← Back to 4D-Radar / Radar Odometry README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · §4 延迟/硬件数字逐字取自 Table 3/§4.2；§5 数据集与指标逐字取自 Table 1/2 与正文；未在真机复现的数字标 `UNVERIFIED`（本文未出现此类自造数字，§3 玩具例子为明确标注的示范设定）；§8 无官方 repo 信号，pitfall 由失败模式 + 方法约束推导，未经验证。

<!-- source: https://arxiv.org/abs/2607.26980 -->
