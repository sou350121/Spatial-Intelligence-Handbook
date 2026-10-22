[//]: # "<!-- ontology-5axis
problem: VIO
representation: pointmap
sensor: multi-modal
paradigm: 3R-SLAM-hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# FoundationVIO：为前馈视觉惯性里程计施加公制尺度 (FoundationVIO: Enforcing Metric Scale in Feed-forward Visual-Inertial Odometry)

> **发布时间**：2026-10-10（arXiv:2610.14951v1 [cs.RO]）
> **论文 / 模型名**：FoundationVIO
> **核心定位**：把多视图 GFM 的 up-to-scale 点图/位姿与 IMU 预积分放进因子图，在线恢复公制尺度；轨迹与经典 VIO 竞争，稠密重建优于 GFM-enabled SLAM。

GFM 单次前馈能给出局部一致的稠密几何，但物理尺度未知，且不同 batch 之间尺度会漂。FoundationVIO 的关键不是训练新模型，而是把“每 batch 的未知尺度”显式建模成因子图变量，用 IMU 提供米制锚点、用重叠帧的相对尺度连接 batch，从而把 GFM 的 Sim(3) 输出收束成公制 SE(3) 轨迹与重建。

**X-Ray 开场**：它解决的是“GFM 预测局部很密、但不知道一米有多长”的痛点。做法是把 GFM 的位姿/点图当作测量，把 IMU 预积分当作公制锚，把 batch 间相对尺度当作约束，统一进 iSAM2/GTSAM 因子图。对 spatial AI 研究者意味着：GFM 不一定要端到端重训，也可以作为“几何前端”被经典因子图后端计量化。

## 📍 研究全景时间线

```text
2015-2020                2023-2024                 2024-2026                         2026
经典 VIO/SLAM      ->    两视图 GFM          ->    多视图 GFM + GFM-SLAM       ->    惯性 GFM / 本文
OKVIS2/VINS/ORB          DUSt3R/MASt3R             VGGT, MASt3R-SLAM, VGGT-SLAM      MASt3R-Fusion, VI3, FoundationVIO
稀疏/直接法              两视图点图                视觉一致、无公制尺度              IMU 锚定公制尺度
```

本文位置：在“多视图 GFM + 增量 SLAM”与“IMU 锚定 GFM”之间架桥，把 MASt3R-Fusion/VI3 的惯性-GFM 思路推广到多视图 GFM 与长序列增量 batch。

本文局限：
- 尺度恢复依赖 GFM 质量与重叠帧几何；DA3-L 在 Oxford CC02 的 Table I 平移 RPE 为 `×`，Table III F-score 也为 `×`；注意 Table II 没有 DA3-L 行，不能把 Table II 当作 DA3-L 发散的出处。
- 初始化依赖 IMU 激励；低激励/静止启动会延迟 bootstrap。
- loop-closure 只是最小扩展，不是主贡献；false positive 可能污染尺度节点。
- 论文未报告峰值显存、功耗、CPU 占用、端到端 FPS。

## 1 · 核心架构 / 方法总览

### 1.1 系统/组件对比表

| 模块 | 输入 | 输出 | 训练-推理差异 |
|---|---|---|---|
| Visual-inertial initialisation | 图像 + IMU | 重力方向、陀螺仪 bias、初始状态 | 无训练；改自 VINS-Mono，用 GFM 位姿替换 SfM 步 |
| GFM batch inference | 重叠 batch \(\mathcal I_k=\&#123;\mathbf I_1^k,\dots,\mathbf I_B^k\&#125;\) | up-to-scale 位姿 \(\mathcal T_k\)、pointmap \(\mathcal P_k\)、confidence \(\mathcal C_k\) | GFM 预训练冻结；本文只推理，不 fine-tune；model-agnostic |
| Filtering / masking | pointmap、depth、confidence | 过滤后的点 | 无训练；深度阈值按轨迹 baseline 的倍数过滤，并做 depth-based edge mask |
| Batch-to-batch relative scale | 重叠帧的两组 pointmap/confidence | \(s_k^&#123;rel&#125;\) | 无训练；IRLS + confidence-weighted Umeyama 估 Sim(3) |
| Factor graph construction | GFM 位姿、\(s_k^&#123;rel&#125;\)、IMU | IMU 预积分因子、GFM pose 因子、scale consistency 因子 | 无训练；自定义 GFM pose 因子带 batch scale |
| Optimisation | 因子图 | 位姿、速度、bias、每 batch \(l_k=\log s_k\) | iSAM2 / GTSAM 增量优化 |
| Loop-closure | SALAD 全局描述子、回环 batch | 回环因子 | 最小扩展；非本文主焦点；Huber 鲁棒核 |

### 1.2 关键机制

**⚡ Eureka Moment：把每个 GFM batch 的未知尺度显式建模成因子图里的 log-scale 变量 \(l_k\)，用 IMU 预积分提供公制锚点、用重叠帧相对尺度提供 batch 间约束，从而把 GFM 的 Sim(3) 自由度收束成可优化的公制 SE(3) 轨迹。**

具体地：
- GFM 位姿因子只约束旋转与“按 \(s_k\) 缩放后的平移”；
- IMU 预积分因子约束真实米制运动、速度、bias；
- scale consistency 因子用 \(\log s_&#123;k+1&#125;^&#123;rel&#125;\) 连接相邻 batch 的 \(l_k\)，把尺度乘法变成加法；
- iSAM2 在新增 batch 因子时增量重线性化，最后用每 batch 的 \(s_k\) 缩放点云并钉在该 batch 第一帧位姿上。

### 1.3 信息流 ASCII 图

```text
图像流
  │
  ├─> 重叠 batch（batch k 第一帧与 k-1 最后一帧重叠）
  │       │
  │       ├─> GFM（DA3-L / DA3-N / VGGT-Ω）
  │       │       └─> up-to-scale poses + pointmaps + confidence
  │       │
  │       ├─> 过滤：深度阈值 + edge mask
  │       │
  │       └─> 重叠帧 pointmap 对齐
  │               └─> IRLS + confidence-weighted Umeyama
  │                       └─> s_k^rel
  │
  ├─> IMU ─> 预积分 ─> IMU factor
  │
  └─> 因子图：GFM pose factor + IMU factor + scale consistency factor
          │
          └─> iSAM2/GTSAM 增量优化
                  └─> 公制位姿 + 按 s_k 缩放的点云

回环分支：SALAD descriptor -> 候选帧 -> loop batch -> GFM -> 相对尺度 -> Huber 回环因子
```

## 2 · 数学核心

📌 **Napkin Formula**：
\[
l_k=\log s_k,\qquad s_&#123;k+1&#125;=s_k\,s_&#123;k+1&#125;^&#123;rel&#125;
\]
GFM 给形状与相对运动，IMU 给“米”；因子图只额外估计每个 batch 的 log 尺度 \(l_k\)，以及每帧位姿、速度、bias。

**目标**：在 GFM 位姿 up-to-scale、IMU 有公制加速度的条件下，估计公制轨迹与每 batch 尺度，使所有因子残差加权平方和最小。

**核心公式**：

GFM pose 因子（带 batch scale）：
\[
\mathbf r_&#123;i,j&#125;^&#123;GFM&#125;(\mathbf T_i,\mathbf T_j,s_k)
=
\begin&#123;bmatrix&#125;
\mathrm&#123;Log&#125;\left(\mathbf Z_R^T\mathbf R_i^T\mathbf R_j\right)\\
\mathbf Z_t - s_k\mathbf R_i^T(\mathbf t_j-\mathbf t_i)
\end&#123;bmatrix&#125;
\]
其中 \(\mathbf Z_&#123;i,j&#125;=\mathbf T_j^&#123;-1&#125;\mathbf T_i=\&#123;\mathbf Z_t,\mathbf Z_R\&#125;\) 是 GFM 给出的 up-to-scale 相对位姿。

Scale consistency 因子：
\[
\mathbf r_k^&#123;scale&#125;(l_k,l_&#123;k+1&#125;)
=
(l_&#123;k+1&#125;-l_k)-\log s_&#123;k+1&#125;^&#123;rel&#125;
\]

IMU 预积分残差（结构）：
\[
\mathbf r_&#123;ij&#125;^&#123;IMU&#125;(\mathcal X_i,\mathcal X_j)
=
\begin&#123;bmatrix&#125;
\mathbf R_i^T(\mathbf t_j-\mathbf t_i-\mathbf v_i\Delta t-\frac12\mathbf g\Delta t^2)-\hat&#123;\mathbf t&#125;_&#123;ij&#125;\\
\mathbf R_i^T(\mathbf v_j-\mathbf v_i-\mathbf g\Delta t)-\hat&#123;\mathbf v&#125;_&#123;ij&#125;\\
\mathrm&#123;Log&#125;(\hat&#123;\mathbf R&#125;_&#123;ij&#125;^T\mathbf R_i^T\mathbf R_j)\\
\mathbf b_j^a-\mathbf b_i^a\\
\mathbf b_j^g-\mathbf b_i^g
\end&#123;bmatrix&#125;
\]

因子图目标可写成：
\[
\min_&#123;\mathcal X,\&#123;l_k\&#125;&#125;
\sum_&#123;(i,j)&#125;\|\mathbf r_&#123;ij&#125;^&#123;IMU&#125;\|^2_&#123;\Sigma_&#123;IMU&#125;&#125;
+
\sum_&#123;(i,j,k)&#125;\|\mathbf r_&#123;i,j&#125;^&#123;GFM&#125;\|^2_&#123;\Sigma_&#123;GFM&#125;&#125;
+
\sum_k\|\mathbf r_k^&#123;scale&#125;\|^2_&#123;\sigma_s^2&#125;
+
\text&#123;loop factors with Huber&#125;
\]

**变量说明**：

| 符号 | 含义 |
|---|---|
| \(\mathbf T_i=\&#123;\mathbf t_i,\mathbf R_i\&#125;\in SE(3)\) | 第 \(i\) 帧 body pose |
| \(\mathbf v_i\) | 第 \(i\) 帧 body velocity |
| \(\mathbf b_i=\&#123;\mathbf b_i^a,\mathbf b_i^g\&#125;\) | IMU 加速度计/陀螺仪 bias |
| \(s_k\) | 第 \(k\) 个 batch 的尺度（GFM 单位/米） |
| \(l_k=\log s_k\) | log 尺度，便于把相对尺度乘法变加法 |
| \(s_k^&#123;rel&#125;\) | batch \(k\) 相对 batch \(k-1\) 的相对尺度 |
| \(\mathbf Z_t,\mathbf Z_R\) | GFM 预测的 up-to-scale 相对平移/旋转 |
| \(\mathbf g\) | 重力向量 |

**直觉**：GFM 的平移残差里，\(s_k\) 把“GFM 单位”换算成“米”；IMU 残差里，重力与加速度把“米”钉死；scale consistency 残差把相邻 batch 的尺度比钉死。三者一起，使 \(s_k\) 不再自由漂移。

## 3 · 带数字走一遍

> 玩具设定（非论文实验）：一维平移，忽略旋转、bias、confidence，只演示尺度如何被 IMU 与相对尺度共同确定。

设 batch 1 中，GFM 给出相邻帧平移 \(Z_t^&#123;(1)&#125;=2.0\)（GFM 单位），IMU 预积分在同一时间间隔给出真实平移 \(0.5\) m。

GFM pose 因子平移残差置零：
\[
Z_t^&#123;(1)&#125; = s_1 \cdot 0.5
\quad\Rightarrow\quad
s_1 = \frac&#123;2.0&#125;&#123;0.5&#125;=4.0
\]
即 batch 1 的 GFM 单位是“4 单位/米”。对应 \(l_1=\log 4.0=1.386\)。

设重叠帧估计出 batch 2 相对 batch 1 的相对尺度：
\[
s_2^&#123;rel&#125;=0.5
\]
scale consistency 因子置零：
\[
l_2-l_1=\log 0.5=-0.693
\quad\Rightarrow\quad
l_2=1.386-0.693=0.693
\]
即 \(s_2=e^&#123;0.693&#125;=2.0\)，batch 2 的单位是“2 单位/米”。

若 batch 2 中 GFM 给出某段平移 \(Z_t^&#123;(2)&#125;=0.6\) 单位，则换算成米：
\[
\Delta t_&#123;\text&#123;metric&#125;&#125;=\frac&#123;Z_t^&#123;(2)&#125;&#125;&#123;s_2&#125;
=\frac&#123;0.6&#125;&#123;2.0&#125;=0.3\text&#123; m&#125;
\]
如果没有 IMU 与跨 batch 尺度约束，\(s_1,s_2\) 都可任意缩放；有了 IMU 的 \(0.5\) m 锚点和 \(s_2^&#123;rel&#125;=0.5\)，整条轨迹就被固定到米制。

## 4 · 工程视角

论文实验平台：Intel Core(TM) i7-13850HX + RTX 3500 Ada Generation Laptop GPU，12 GB VRAM。实时预算：2000 ms/batch（10 张图 @ 5 Hz）。

**Table IV：Runtime breakdown（ms/batch）**

| 模型 | Inference | Filter | Rel. scale | Loop-closure | Factor graph | Other | Total* |
|---|---:|---:|---:|---:|---:|---:|---:|
| DA3-L | 725 | 253 | 32 | 90 | 97 | 102 | 1299 |
| VGGT-Ω | 867 | 249 | 36 | 129 | 76 | 436 | 1792 |
| DA3-N | 1799 | 239 | 28 | 162 | 63 | 99 | 2390 |

\* 实时预算为 2000 ms/batch（10 images at 5 Hz）。

工程解读：
- DA3-L 总耗时 1299 ms，低于 2000 ms 预算，论文称可 real-time；VGGT-Ω 1792 ms，接近预算；DA3-N 2390 ms，超过 2000 ms，论文称 near real-time。
- 模型推理占主要开销；论文明确说 “Model inference costs around half of the time budget on unoptimised code”。
- 精度更高的 DA3-N（1.4B）带来更高延迟；DA3-L（0.3B）更快但精度较低。工程上是在“GFM 质量 vs 延迟”之间换挡。
- 论文未报告峰值 VRAM、功耗、CPU 占用、端到端 FPS；只报告 ms/batch 与 5 Hz/10 图设定。部署到 12 GB 笔记本 GPU 时，batch size 与 GFM 大小是硬约束。
- loop-closure 分支在表中为 90/129/162 ms；它还会额外触发一个 loop batch 的 GFM 推理，工程上需考虑回环检测频率。

## 5 · 数据与评测

### 5.1 数据集组成

| 数据集 | 传感器 | 图像/IMU 参数 | 真值 |
|---|---|---|---|
| Aria Office（自采） | Meta Aria glasses (Gen 1) | 前向 RGB：FoV \(110^\circ\)，15 Hz，1408×1408；实验用 pinhole rectified \(98.2^\circ\times98.2^\circ\)；IMU 1 kHz（设备另有 800 Hz IMU），用右耳附近 1 kHz IMU | MPS 后处理 SLAM 参考轨迹；Leica BLK360 TLS 高精度激光扫描 |
| Oxford Spires | Alphasense 相机 + IMU | 20 Hz，1440×1080；IMU 400 Hz；rectified \(91.6^\circ\times75.4^\circ\) | 毫米级 TLS map；移动 LiDAR 对齐得到 GT 轨迹 |
| ScaRF-SLAM | Insta360 ONE RS 1-inch | 双鱼眼 30 Hz，1472×1440；IMU 1 kHz；rectified \(81.5^\circ\times65.9^\circ\) | 毫米级 TLS map；移动 LiDAR 对齐得到 GT 轨迹 |

实验设置：FoundationVIO 图像降采样到 5 Hz、batch size 10；所有方法使用相同 FoV 的 rectified pinhole 图像；经典方法用 full image sequences，MASt3R-Fusion 用默认输入率。Aria Office 含多楼层、窄走廊、低纹理楼梯、办公室；Oxford Spires 含 indoor-outdoor transitions；ScaRF-SLAM 含多楼层办公室与“轻抬设备”初始化段。

### 5.2 指标与对齐

- Odometry：RPE RMSE，平移 `m/m`，旋转 `°/m`。
- SLAM：APE RMSE，单位 `m`。
- Reconstruction：F-score at 5 cm；按 10 m 轨迹分块，局部对齐 + ICP；recall 时参考点云过滤到距估计点 30 cm 内，排除未访问区域。
- 对齐：GFM-only SLAM（DA3-Streaming、VGGT(D)-SLAM）因 up-to-scale 用 Sim(3) 对齐；其他方法用 SE(3)。MASt3R-Fusion 的 loop-closure 是离线全局优化（BA + LC），与在线增量方法不是完全 like-for-like，表中以灰底参考。

### 5.3 关键数字（逐字核对与事实校正）

**Table I 平移 RPE 均值（m/m）**

| 方法 | Aria Office | ScaRF-SLAM | Oxford Spires |
|---|---:|---:|---:|
| FoundationVIO (DA3-N) | 0.034 | 0.037 | 0.041 |
| ORB-SLAM3 | 0.026* | 0.049 | 0.029 |
| OKVIS2 | 0.069 | 0.031 | 0.093 |
| VINS-Fusion | 1.560* | 0.137 | 0.026 |
| MASt3R-Fusion | 0.306* | 0.111 | 0.292 |

\* Mean over non-diverged sequences only。

> **事实校正 1**：不能说 “DA3-N 版 FoundationVIO 在 Aria 与 Oxford 平移 RPE 上优于所有经典方法”。Table I 中 Aria 均值 FoundationVIO (DA3-N)=0.034，高于 ORB-SLAM3 的 0.026*（非发散序列均值）；Oxford 均值 FoundationVIO=0.041，高于 ORB-SLAM3 的 0.029 与 VINS-Fusion 的 0.026。它优于 OKVIS2（Aria 0.069、Oxford 0.093），也优于 VINS-Fusion 的 Aria 均值 1.560*，但不是全面领先。ScaRF 上 FoundationVIO=0.037，也高于 OKVIS2 的 0.031。

旋转 RPE 方面，FoundationVIO (DA3-N) 的均值为 Aria 0.49、ScaRF 0.40、Oxford 0.24 `°/m`；论文表述为与经典方法 comparable、保持 sub-degree 精度。

**Table II SLAM APE 均值（m）**

| 方法 | Aria Office | ScaRF-SLAM | Oxford Spires |
|---|---:|---:|---:|
| FoundationVIO (DA3-N) | 0.155 | 0.101 | 1.043 |
| OKVIS2 | 0.331 | 0.116 | 0.842 |
| ORB-SLAM3 | 1.558* | 0.232 | 1.061* |
| VINS-Fusion | 1.705* | 0.424 | 0.607 |
| MASt3R-Fusion (BA + LC) | 0.150 | 0.337* | 0.623 |
| DA3-Streaming (DA3-N) | 0.431 | 0.193 | 1.877* |
| VGGT(D)-SLAM (DA3-N) | 0.624* | 1.773* | 2.532* |

\* Mean over non-diverged sequences only。

注意：Table II 只评了 **FoundationVIO (DA3-N)**，没有 DA3-L 行。因此不能把 Table II 当作 DA3-L 发散的出处。

**Table III Reconstruction F-score（% ↑, 5 cm）均值**

| 方法 | Aria Office | ScaRF-SLAM | Oxford Spires |
|---|---:|---:|---:|
| FoundationVIO (DA3-N) | 66.7 | 73.1 | 54.9 |
| DA3-Streaming (DA3-N) | 60.4 | 76.1 | 33.5* |
| MASt3R-Fusion | 52.5 | 58.8* | 40.1 |
| VGGT(D)-SLAM (DA3-L) | 33.9* | 47.0 | 35.8* |
| VGGT(D)-SLAM (DA3-N) | 41.6* | 46.5* | × |

\* Mean over successful sequences only；Aria 的 BigRoom (BR) 序列没有对齐的 GT 重建，未计入。

> **事实校正 2**：Table III 中 `†`（out of memory (RAM)）标在 **NT4**，VGGT(D)-SLAM 的 DA3-L 与 DA3-N 两行都在 NT4 列。AT2 对 DA3-L 与 DA3-N 都是 `×`；NT3 对 DA3-L 是 `26.6`、对 DA3-N 是 `×`，均不是 `†`。

> **事实校正 3**：DA3-L 在 Oxford CC02 的 Table I 平移 RPE 为 `×`（发散），Table III F-score 也为 `×`；但 Table II 没有 DA3-L 行，不能引用 Table II 作为其 `×` 出处。

## 6 · 能力与失败模式

**能做**：
- 用 IMU 把多视图 GFM 的 up-to-scale 位姿/点图锚定到公制尺度，输出米制轨迹与稠密重建。
- model-agnostic：论文实测 DA3-L（0.3B）、DA3-N（1.4B）、VGGT-Ω（1.0B），并观察到 GFM 质量提升会改善轨迹/重建。
- 增量 batch 融合：通过重叠帧 + 相对尺度因子连接长序列，不要求一次前馈覆盖全序列。
- 最小 loop-closure：SALAD 候选 + loop batch + Huber 因子，可把系统从 odometry 扩展成 SLAM。
- 在 Aria Office、Oxford Spires、ScaRF-SLAM 三类传感器 rig 上验证，兼容常见相机+IMU。

**不能做 / 容易失败**：
- 低 IMU 激励或静止启动时，visual-inertial initialisation 会等待加速度计范数标准差超过阈值，bootstrap 延迟。
- 重叠帧视差小、纹理弱、动态遮挡严重时，confidence-weighted Umeyama 估出的 \(s_k^&#123;rel&#125;\) 不稳定，错误尺度会通过 scale consistency 因子传播。
- 强动态场景违反“刚体点图”假设，动态点会污染点图对齐与重建。
- 相机-IMU 外参/时间同步/内参误差会直接进入 IMU 因子与 GFM pose 因子，造成系统性尺度/位姿偏差。
- GFM 本身失败时（例如 DA3-L 在 Oxford CC02 的 Table I 平移 RPE 为 `×`），后端无法凭空恢复；Table III 中 DA3-L 在 CC02 的 F-score 也为 `×`。
- loop-closure 只是最小实现，false positive 可能引入错误回环因子；Huber 只能 dampen，不能完全消除。
- 计算上受 batch size 与 GFM 大小约束；DA3-N 在 Table IV 中 2390 ms/batch，超过 2000 ms 预算。

### 隐含假设 (Hidden Assumptions)

1. **场景近似刚性**：batch 内 pointmap 与深度一致，动态物体会破坏 Umeyama 对齐。
2. **重叠帧有足够视差与纹理**：否则 Sim(3) 的尺度分量不可观，\(s_k^&#123;rel&#125;\) 噪声大。
3. **IMU 与相机已校准且时间同步**：论文用 Kalibr 标定内参与相机-IMU 外参；偏差会变成尺度/位姿偏差。
4. **初始化窗口内 IMU 有激励**：固定滑窗要等到加速度计范数标准差超过阈值，才接受窗口并送入 GFM。
5. **GFM 的 pose head 与 pointmap 局部一致**：GFM 预测误差会直接作为因子图测量误差进入后端。
6. **batch size 10 @ 5 Hz 足以覆盖运动**：更大的 batch 可能提升一致性，但会增加显存/延迟；论文未报告峰值显存。
7. **回环候选可由 SALAD + L2 召回**：loop batch 的 GFM 预测仍需可用，否则回环因子不可靠。

## 7 · 与相关工作对比

| 方法 | 类型 | 尺度来源 | 多视图 GFM | 增量/长序列 | 备注 |
|---|---|---|---|---|---|
| OKVIS2 / ORB-SLAM3 / VINS-Fusion | 经典 VIO/SLAM | IMU + 视觉 | 否 | 是 | 强 baseline；部分 Aria 序列因 visual-inertial 初始化差而发散 |
| MASt3R-SLAM | GFM-enabled SLAM | 视觉 only，up-to-scale | 两视图 MASt3R | 是 | 增量点图对齐 + 全局 Sim(3) 图优化 |
| VGGT-SLAM | GFM-enabled SLAM | 视觉 only，up-to-scale | 多视图 VGGT | 是 | local submaps + SL(4) 流形配准 |
| AIM-SLAM | GFM-enabled SLAM | 视觉 only，up-to-scale | 多视图 | 是 | 自适应选择 keyframes |
| MASt3R-Fusion | 惯性 GFM | IMU + 两视图 MASt3R | 否（pairwise） | 否/有限 | 因子图恢复公制尺度；loop-closure 用 MASt3R encoder feature tokens；其实验实现含离线 BA + LC |
| VI3 | 惯性 GFM | IMU 预积分导出 metric motion reference | 单 batch | 短序列 | 把单次前馈预测 ground 到公制；不处理长序列增量 SLAM |
| **FoundationVIO** | **惯性 GFM + SLAM** | **IMU 预积分 + batch 间相对尺度** | **是（DA3/VGGT-Ω）** | **是（重叠 batch 增量）** | **因子图显式估计每 batch \(l_k\)；最小 GFM loop-closure；model-agnostic** |

**面试 Tip**：被问到“它和 MASt3R-Fusion/VI3 有什么区别”时，答三点：
1. MASt3R-Fusion 是 pairwise 两视图 GFM + IMU；FoundationVIO 面向多视图 GFM 的 batch 输出。
2. VI3 主要是把单 batch 预测 ground 到公制；FoundationVIO 处理长序列增量 batch，并用 scale consistency 因子连接相邻 batch。
3. FoundationVIO 不训练 GFM，而是把 GFM 当测量，用因子图估计 \(l_k=\log s_k\)；因此可以随 GFM 升级而受益，但也会继承 GFM 的失败模式。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-22)

截至 2026-10-22，论文摘要只出现纯文本代码链接字符串，未提供可验证的 issue/commit 流；按本笔记规则，不引用 repo URL、commit hash 或 issue 编号。以下 pitfall 由 §6 失败模式 + 方法约束推导，**未经 issue 验证**。

1. **静止/低激励启动会卡在初始化**
   - 方法约束：III-B 用固定滑窗，直到加速度计范数标准差超过阈值才接受窗口并送入 GFM。
   - 失败链：机器人静止或缓慢平移 → IMU 激励不足 → 初始化窗口迟迟不被接受 → 因子图无法 bootstrap → 后续尺度节点没有公制锚点。
   - 工程表现：启动阶段延迟、首段轨迹缺失或尺度漂移。

2. **纯旋转/小重叠会让 \(s_k^&#123;rel&#125;\) 不可观，错误尺度被因子图固化**
   - 方法约束：III-D 在重叠帧上用 IRLS + confidence-weighted Umeyama 估 Sim(3)，取尺度分量 \(s_k^&#123;rel&#125;\)；III-E 的 Eq.(2) 把 \(s_k^&#123;rel&#125;\) 作为硬测量连接 \(l_k,l_&#123;k+1&#125;\)。
   - 失败链：重叠帧视差小/动态遮挡/弱纹理 → Umeyama 尺度分量病态 → \(s_k^&#123;rel&#125;\) 噪声大 → scale consistency 因子把错误尺度传播到相邻 batch → 轨迹与点云整体缩放错误。
   - 工程表现：纯旋转手持、窄走廊正对墙面、低纹理楼梯等场景容易触发。

3. **加大 batch 提精度会撞延迟/显存墙**
   - 方法约束：III-C 将图像分成 \(B\) 张的 batch；论文指出单次前馈受 GPU 显存限制，移动 GPU 上只能处理 tens of images；实验用 batch size 10、5 Hz。
   - 失败链：为提升 GFM 一致性而增大 batch 或换更大模型 → 推理时间/显存上升 → Table IV 中 DA3-N 已达 2390 ms/batch，超过 2000 ms 实时预算；12 GB VRAM 笔记本 GPU 上更易 OOM 或掉帧。
   - 工程表现：DA3-L 可 real-time，DA3-N 仅 near real-time；loop-closure 还会额外触发 loop batch 推理（表中 162 ms 为 DA3-N 的 loop-closure 分量）。

---
[← Back to VIO README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2610.14951 -->"
