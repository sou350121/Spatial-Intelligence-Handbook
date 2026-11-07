[//]: # "<!-- ontology-5axis
problem: reconstruction
representation: n/a
sensor: stereo
paradigm: generative
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# StereoFlow：渐进式立体匹配，结合 StereoDiT 与 Transition Flow Matching (StereoFlow: Progressive Stereo Matching with StereoDiT and Transition Flow Matching)

> **发布时间**：2026-07-22（arXiv v1，cs.CV）
> **论文 / 模型名**：StereoFlow（StereoDiT / Transition Flow Matching, TFM）
> **核心定位**：把立体匹配从“确定性单点回归”改成“先验引导的生成式分布建模”——用 ConvGRU 的视差先验当生成起点，只在局部歧义上做少步 flow matching，从而在遮挡 / 反光 / 重复纹理 / 深度不连续处同时拿到几何一致性与细节。

现有深度立体匹配几乎都假设“一个像素只有一个正确视差”，用 L1 / smooth-L1 回归，于是在多峰歧义区被 regression-to-mean 拉平；直接套 diffusion 又因为极线约束和“无先验”而在整条极线上盲搜、步数多、开销大。StereoFlow 的结论是：把确定性匹配的输出 `d0` 当作生成模型的**起点分布**而不是各向同性高斯噪声，2 步采样即可在 Scene Flow / KITTI / ETH3D / Middlebury 上取得多项第一。

## X-Ray 开场

立体匹配本质是“多峰分布”问题（遮挡、反光、重复纹理处有多个同样合理的视差假设），但主流做法把它压成单点回归，于是边界被抹平、不可靠区域被过度平滑、跨域泛化差。StereoFlow 提出**先验引导的生成式框架**：一个两级渐进级联网络（低分辨率 4D GEV 负责几何一致性，高分辨率 3D ACV 负责细节）先给出视差先验，再由像素级 DiT（StereoDiT，频率解耦的 geometric encoder + stereo decoder）在先验附近建模多模态分布，配一个把源分布从“高斯噪声”换成“退化视差”的少步 flow matching 目标（Transition Flow Matching）。对 spatial AI 研究者来说，它的意义是给出了一个可复用的范式：**生成模型不必从噪声起步，可以用任务的确定性解当先验，把生成能力集中花在真正歧义的少数像素上**——这正是 diffusion 类方法在几何任务上落地时最缺的那一环。

## 📍 研究全景时间线

```
2018  GwcNet / PSMNet            —— 3D/4D cost volume + 3D CNN 回归（几何强、过度平滑）
2021  RAFT-Stereo                —— ConvGRU 迭代 + 3D All-pairs Correlation Volume（细节强、局部性差）
2023  IGEV-Stereo                —— 4D Geometry Encoding Volume + 迭代优化（本文 baseline 家族）
2024  Selective-IGEV / DLNR / Mocha-Stereo / DEFOM-Stereo
                                 —— 频率分解、单目深度先验注入（affine-invariant + metric scaling）
2025  MonSter / BridgeDepth / FoundationStereo
                                 —— 视觉基础模型 + 单目深度，追求 zero-shot 泛化
2025  扩散进立体：DiffuVolume / D3RoMa / DiffMVS
                                 —— 直接把 diffusion 套到 cost volume / 视差上，收益边际、步数多
2026  StereoFlow  ★本文           —— 确定性回归(d0) + 生成建模(2 步 TFM)，先验引导的多模态建模
未来  ← 本文自述局限：(i) 2 步采样仍有非可忽略延迟，需 one-step；(ii) 两阶段训练复杂且不稳定，需 one-stage
```

本文在演进中的位置：它既不是“再堆一个 cost volume”，也不是“再套一个大 diffusion”，而是**重新定义了生成模型在立体匹配里的起点**；局限也很清楚——延迟还没到实时、训练流程不是端到端。

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|---|---|---|---|
| Feature / Context encoder | 校正后图像对 `I^{l,r} ∈ R^{3×h×w}` | 匹配特征金字塔 `{f_s}` s=1..4、上下文特征 `{c_s^l}` s=1..3 | 一致；推理只跑一次前向 |
| Depth foundation model（DepthAnythingV2-L） | 图像对 `I^{l,r}` | 单目深度特征金字塔 `{d_s^{l,r}}` s=1..4 | 一致；被注入匹配特征与上下文特征以缓解 ill-posed 与合成域偏差 |
| 4D GEV（stage-1，1/8 尺度） | 低分辨率匹配特征 | `C^g_{s=3} ∈ R^{c×d/8×h/8×w/8}`（group-wise corr + 紧凑 concat，正则化） | 一致；金字塔 `{C^g_{s=3,l}}` l=1,2 由沿视差维 1D 平均池化得到 |
| 3D ACV（stage-2，1/4 尺度） | 高分辨率匹配特征 | 单通道全视差相关体 `C^a_{s=2} ∈ R^{w/4×h/4×w/4}` | 一致；建立精确像素对应、支持大视差 |
| ConvGRU matching regression（每级各一） | `d_{n-1}`、检索到的 cost features `C_{n-1}`、context `c`、隐状态 `h_{n-1}` | 更新视差 `d_n = d_{n-1} + Δd` → 作为**视差先验 d0** | 训练用 `L_init` + 加权 `L_iter`（γ=0.9）；推理 8+8=16 次迭代 |
| StereoDiT（geometric encoder + stereo decoder） | 噪声视差 `d_t`、`t`、cost features `C`、单目深度特征 `d*`、不确定度 `U` | 速度场 `v_t` | 训练随机 `t∼U[0,1]` 回归速度场；推理 2 步 Euler ODE |
| Transition Flow Matching（目标函数） | 耦合对 `(d1, d0)` | 损失 `L_tfm` | 训练：`d0` 取退化视差；推理：直接从 `d0` 出发积分到 `d1` |
| REPA 对齐损失 | encoder 第 i 层中间特征 `h_i` | `L_repa = 1 − cos(h_φ(h_i), d*)` | 仅训练时；权重 `γ_repa = 0.5` |

### 1.2 关键机制

**⚡ Eureka Moment：生成模型的源分布不必是各向同性高斯——把确定性匹配网络输出的视差 `d0` 当作 flow matching 的源，生成过程就从“在整条极线上盲搜”退化为“在先验附近修局部歧义”，于是 2 步就能采样。**

三个组件互相咬合：
1. **两级渐进级联**（论文强调这是核心架构贡献）：1/8 尺度用 4D GEV 拿“非局部几何一致性”，1/4 尺度用 3D ACV 拿“精确像素对应 + 细粒度 + 大视差”。消融显示“每级都放 3D ACV”只有边际收益（0.43→0.41 EPE），而“低分辨率 GEV + 高分辨率 ACV”才显著（→0.37）。
2. **StereoDiT 频率解耦**：geometric encoder 用 patch 16²、depth 4/8、hidden 256、8 heads，通过 REPA 向单目深度特征对齐 → 负责**低频结构一致性**；stereo decoder 用 patch 1²、depth 2/3、hidden 32 的轻量 MLP，吃 `d_t, t, z_t, C, U` → 负责**高频度量细节**。整个 StereoDiT base 只有 12M（1/8）与 20M（1/4）参数，比通用 DiT 系紧凑得多。
3. **TFM 把“确定性搬运”和“随机扰动”拆开**：均值 `μ_t` 走线性插值（方向性位移，搬运几何结构），标准差 `σ_t` 走线性调度 `tσ_min + (1−t)σ_max`（合成细节）；`σ_max` 保证生成性与泛化，`σ_min` 避免奇点。

### 1.3 信息流图

```
I^{l,r} ──┬─ Feature Enc ──► {f_s} s=1..4 ──┬─► 4D GEV (1/8) ──► Cost filtering(3D CNN) ──► d_init
          │                                 └─► 3D ACV (1/4)
          ├─ Context Enc ──► {c_s^l} s=1..3 ──────────────┐
          └─ DepthAnythingV2-L ──► {d_s} s=1..4 ──┐       │
                                                    │       ▼
        ┌───────────────── Stage-1 @1/8 ──────────┴──► ConvGRU ×8 ──► d0 (视差先验)
        │                                                    │
        │                                            StereoDiT(1/8) ── 2 步 ODE ──► d
        │                                                    │
        └─ 凸上采样 (Up) ──► Stage-2 @1/4 ──► ConvGRU ×8 ──► d0'
                                                     │
                                             StereoDiT(1/4) ── 2 步 ODE ──► 最终视差
        （每级 StereoDiT 内部：d_t,t ─► geometric encoder(patch16², REPA←d*) ─► z_t
                              {d_t,t,z_t,C,U} ─► stereo decoder(patch1², MLP) ─► v_t）
```

## 2 · 数学核心

📌 **Napkin Formula**：`p_t(d|d0,d1) = N(t·d1 + (1−t)·d0, (t·σ_min + (1−t)·σ_max)² I)` —— 均值从“退化视差”线性搬到“目标视差”，方差从 `σ_max` 线性收到 `σ_min`。

**目标**：不要学“从纯噪声生成视差”，而要学“从有偏的确定性视差 `d0` 搬运到干净视差 `d1`”的速度场。

**公式（式 6–8）**：
- 转移路径：`μ_t = t d1 + (1−t) d0`，`σ_t = t σ_min + (1−t) σ_max`
- 仿射流：`ψ_t(d|d0,d1) = σ_t ε + μ_t`，`ε ~ N(0, I)`
- 速度场真值（对 t 求导）：`u_t = (dσ_t/dt) ε + (dμ_t/dt) = (σ_min − σ_max) ε + (d1 − d0)`
- 损失：`L_tfm = E_{t,d0,d1} ‖ v_t(ψ_t(d|d0,d1)) − u_t(d|d0,d1) ‖²`，`t ~ U[0,1]`
- 总目标：`L_match = L_init + L_iter`，`L_iter = Σ_{i=1..N} γ^{N−i} ‖d_i − d_gt‖_1`（γ=0.9），`L_generative = 0.5·L_repa + L_tfm`，`L_total = γ_match·L_match + L_generative`

**变量说明**：`d1` 目标视差（真值侧），`d0` ConvGRU 输出的退化视差（先验侧），`σ_min` 最小平滑因子（防奇点），`σ_max` 最大扰动因子（保生成性），`C` 为按 `d` 检索到的局部 cost features，`U` 为把右图 warp 到左图后算出的不确定度。**注**：式 (11) 后原文写作 “γ_iter = 0.1 defines the weight coefficient for the matching loss”，与式 (9) 中 `γ_iter = 0.9` 冲突，按上下文应为 `γ_match = 0.1`（原文笔误）。

**直觉**：主流 diffusion 走“弯的 SDE/ODE + 各向同性高斯先验”，采样步数多，且先验与目标分布错位导致额外传输代价；纯 Rectified Flow 类最优路径虽直，但在高维稀疏耦合下会掉模式覆盖、出伪影。TFM 在两条路之间取中：**方向性搬运用线性插值（直、便宜），随机性用线性噪声调度保留（不丢多模态）**，因此能 2 步采样。

## 3 · 带数字走一遍（玩具设定，非论文数据）

取一维单像素、`σ_min = 0.01`、`σ_max = 1.0`。某反光像素有两个同样合理的假设：前景 `d=4`、背景 `d=8`；确定性回归（L1）落到中点 `d0 = 6`（这正是 regression-to-mean）。

- 若只信回归：输出 6，误差 2 px。
- TFM：`d1 = 4`（目标模态）、`d0 = 6`。
  - `μ_t = 6 − 2t`，`σ_t = 1 − 0.99t`
  - `u_t = (0.01 − 1.0)ε + (4 − 6) = −0.99ε − 2`
  - t=0 时路径为 `N(6, 1.0²)`；t=0.5 时 `N(5, 0.505²)`；t=1 时 `N(4, 0.01²)`
- 2 步 Euler（t: 0→0.5→1），取 `ε=0`：`d ← 6 + 0.5×(−2) = 5`，再 `d ← 5 + 0.5×(−2) = 4`，恰好命中模态 4，误差 0。
- 噪声项 `−0.99ε` 的作用：`ε ≠ 0` 时在同一模态周围抖动，正是它让模型保留“另一种假设也可能是 8”的概率质量，而不会被 L1 拉回 6。

对应到论文的量级：Table IX 里 PixelDiT 基线 1 步 EPE 0.527 / 2 步 0.419 / 5 步 0.356，而加上解耦架构 + REPAlign + local cost volume + uncertainty 后，**2 步就到 0.348**（5 步 0.347 几乎不再降）——这就是“先验把采样步数压到 2”的实证。

## 4 · 工程视角

| 项目 | 数值 | 来源 / 说明 |
|---|---|---|
| 全模型推理时间 | **0.39 s**（输入 960×540，NVIDIA 4090） | Table VII 原文 |
| IGEV-Stereo 推理时间 | 0.35 s | Table VII 原文（同条件） |
| MonSter 推理时间 | 0.64 s | Table VII 原文（同条件） |
| Baseline（简化 DEFOM-Stereo）推理时间 | 0.29 s | Table VII 原文 |
| 加 Cascade 后 | 0.26 s | Table VII 原文 |
| 加 Progressive 后 | 0.28 s | Table VII 原文 |
| 再加 StereoDiT 1/8 | 0.32 s | Table VII 原文 |
| 再加 StereoDiT 1/4 | 0.35 s | Table VII 原文 |
| StereoDiT 采样时间 | **0.04 s**（1/8）、**0.07 s**（1/4） | Table VI 原文，两档分别报告；论文**未报告**两者合计与总采样占比 |
| ODE 步数 | **2** | Table VI（Euler，时间步线性分布于 [0.0, 1.0]） |
| StereoDiT 参数量 | 12M（1/8）、20M（1/4） | Table VI “Base params” |
| 匹配网络 / DepthAnythingV2-L 参数量 | **论文未报告** | 全文无该数字 |
| 显存 / VRAM | **论文未报告** | 全文未给 |
| 训练硬件 | NVIDIA A100（数量**论文未报告**） | §IV-A 原文 |
| GRU 迭代 | 8（1/8）+ 8（1/4）= 16 次；对比 IGEV-Stereo / DEFOM-Stereo 需 32 次 | §IV-E4 原文 |
| 训练成本 | 预训练 200k 步（无 StereoDiT）+ 100k 步（全模型），batch 16；微调 batch 8，lr 1e-4 | §IV-A 原文 |
| 微调步数 | ETH3D 300k / Middlebury 200k / KITTI 50k | §IV-B 原文 |

**Trade-off 读法**：
- **延迟换质量**：相对 baseline 的 0.29 s，全模型 0.39 s（Table VII），换来 Scene Flow EPE 0.43→0.32、KITTI-15 Bad3.0 5.27→3.92。相对 IGEV-Stereo 的 0.35 s 仍“competitive”（原文措辞），但明显快于 MonSter 的 0.64 s。
- **生成模块是延迟的主要增量**：每级各一次 2 步采样（Table VI 分别报告 0.04 s 与 0.07 s，**论文未给二者之和**），加 Progressive 反而比单 Cascade 只慢 0.02 s（0.26→0.28），说明开销结构上是“迭代次数/分辨率”主导而非生成分支主导。
- **部署约束（推导，非论文数字）**：3D ACV 形状 `R^{w/4×h/4×w/4}`，其视差候选范围等于 `w/4`——即**可表示的最大视差由图像宽度决定**（960 宽 → 240 px 上界）。这条是从 §III-B 的 volume 定义直接读出来的架构约束，不是实测。
- **两阶段训练是工程债**：论文结论自述 “two-stage training strategy not only increases complexity but also introduces instability”，落地时必须保留 stage-1（纯 `L_match`）checkpoint 作为可加载产物。

## 5 · 数据与评测

**训练数据**：预训练用合成 **Scene Flow**；微调用的 **Basic Training Set (BTS)** 为混合集，原文列为 **Scene Flow、CREStereo、Tartan Air、Sintel Stereo、FallingThings、InStereo2k**；KITTI 微调另用 **KITTI-2012、KITTI-2015、Virtual KITTI-2** 的混合。深度基础模型为 **DepthAnythingV2-L**。Baseline 为**去掉 affine-invariant monocular depth 与 metric scaling 模块的简化 DEFOM-Stereo**。

**评测集与阈值**：Scene Flow（EPE, px）；ETH3D（Bad 1.0 / RMSE）；Middlebury（Bad 2.0 / RMSE）；KITTI-2015（D1-bg / D1-all）、KITTI-2012（Out-2 / Out-3）、KITTI-2012 反射区域（Out-2/3/4）。Zero-shot 表的阈值原文明确：“3-pixel for KITTI, 2-pixel for Middlebury, and 1-pixel for ETH3D”，并含 **Middlebury-Quarter**。

**合成预训练（Scene Flow test, EPE↓，Table I）**：RAFT-Stereo `0.56` / IGEV-Stereo `0.47` / NMRF `0.45` / Selective-IGEV `0.44` / DEFOM-Stereo `0.42` / Monster `0.38` / **StereoFlow `0.32`**。原文称 “surpassing RAFT-Stereo by 42% and DEFOM-Stereo by 23% on EPE”。

**真实基准（微调后，Table II 节选；StereoFlow 行）**：ETH3D Bad1.0 Noc `0.58` / All `0.69` / RMSE `0.19`；Middlebury Bad2.0 Noc `2.30` / All `4.82` / RMSE `5.40`；KITTI-15 D1-bg Noc `1.03` / All `1.30`、D1-all Noc `1.13` / All `1.38`；KITTI-12 Out-2 Noc `1.32` / All `1.71`、Out-3 Noc `0.83` / All `1.07`。对应 DEFOM-Stereo 为 `0.70/0.78/0.22`、`2.39/5.02/5.81`、`1.15/1.33/1.25/1.41`、`1.43/1.79/0.94/1.18`。原文给出的相对提升：ETH3D 超 DEFOM-Stereo 17%（Bad1.0 noc）、12%（all）；Middlebury 超 6%（Bad2.0 noc）、6%（all）；KITTI-15 超 10%（D1-bg noc）、10%（all）；KITTI-12 超 8%（Out-2 noc）、5%（Out-2 all）。
> 注：Table II 的 caption 在给定全文中写作 “Synthetic pre-training evaluation on Scene Flow test set”，与其实际内容（微调后的真实基准对比）不符，属原文 caption 重复笔误。

**Zero-shot 泛化（Scene Flow 预训练直接测，Table III）**：KITTI-2012 `3.5` / KITTI-2015 `3.9` / Middlebury-Quarter `4.1` / ETH3D `1.7`；对比 DEFOM-Stereo `3.7/4.9/5.6/2.3`、Monster `3.6/3.9/5.1/2.0`、BridgeDepth `3.6/4.5/4.3/1.3`。原文相对降幅：KITTI-2012 6%、KITTI-2015 20%、Middlebury-Quarter 27%、ETH3D 26%（对比 DEFOM-Stereo）。**注意**：zero-shot 的 ETH3D 上 BridgeDepth（`1.3`）优于 StereoFlow（`1.7`），论文正文未就这一项做说明。

**反射区域（KITTI-2012，Table IV）**：StereoFlow Out-2 Noc `5.62` / All `6.70`、Out-3 Noc `2.71` / All `3.29`、Out-4 Noc `1.74` / All `2.11`；原文称超 BridgeDepth 4%（Out-2 noc）、7%（Out-3 noc）、8%（Out-4 noc）。

**消融（Scene Flow test + KITTI，Table VII，时间在 4090、960×540）**：Baseline `0.43 / 4.14 / 5.27 / 0.29 s` → +Cascade `0.41 / 3.91 / 4.97 / 0.26` → +Progressive `0.37 / 3.80 / 4.55 / 0.28` → +StereoDiT 1/8 `0.35 / 3.63 / 4.26 / 0.32` → +StereoDiT 1/4 `0.34 / 3.61 / 4.19 / 0.35` → Full `0.32 / 3.55 / 3.92 / 0.39`。

**配置（Table VI）**：StereoDiT 1/8 —— encoder patch 16、depth 4、REPAlign layer 2、hidden 256、heads 8、decoder patch 1、depth 2、hidden 32、params 12M、采样 0.04 s；StereoDiT 1/4 —— depth 8、REPAlign layer 4、decoder depth 3、params 20M、采样 0.07 s。优化器 AdamW（β=0.9/0.999）、lr 1e-4、weight decay 0、EMA 0.999。

## 6 · 能力与失败模式

**能做（有数字支撑）**
- 合成域收敛：Scene Flow EPE `0.32`，为表内最低（Table I）。
- 微调后多基准领先：ETH3D Bad1.0 Noc `0.58`、Middlebury Bad2.0 Noc `2.30`、KITTI-15 D1-all All `1.38`、KITTI-12 Out-3 Noc `0.83`（Table II）。
- 零样本跨域：KITTI-2015 `3.9`、Middlebury-Quarter `4.1`（Table III）。
- 反射区域专项：KITTI-2012 Out-4 Noc `1.74`（Table IV）。
- 少步采样成立：StereoDiT 消融中 2 步即 `0.348`，5 步 `0.347`（Table IX）。
- 迭代预算减半：16 次 GRU（8+8）优于 IGEV/DEFOM 所需的 32 次（§IV-E4，Table VIII）。

**不能做 / 会坏**
- **仍然不是实时**：全模型 0.39 s @960×540（Table VII），论文自述 “diffusion models still inevitably introduce non-negligible latency”，并把 one-step 采样列为未来工作。
- **zero-shot ETH3D 不占优**：`1.7` vs BridgeDepth `1.3`（Table III）。
- **大视差受图像宽度限制**：ACV 视差候选维是 `w/4`，超出该范围的视差在该级无候选（由 §III-B 的 `C^a_{s=2} ∈ R^{w/4×h/4×w/4}` 直接推出）。
- **两阶段训练不稳定**：论文自述 “increases complexity but also introduces instability”。
- **依赖外部大模型**：DepthAnythingV2-L 既提供 `d*`（REPA 对齐目标）又是 decoder 输入条件之一，其失效会同时污染低/高频两条支路。

### 隐含假设 (Hidden Assumptions)

1. **输入是严格校正后的像对**：全篇反复出现 “rectified stereo images” 与 epipolar 约束（decoder 靠 `C` “enforces stereo epipolar constraints”）。未校正、或校正残差大的像对，视差先验与 ACV 检索都会错位。
2. **确定性先验“大体正确”**：TFM 的整个采样预算花在 `d0` 附近。若 ConvGRU 在某个病态区把先验放到错误模态之外（或被 L1 拉到两模态中点且 `σ_max` 不足以覆盖），生成分支被约束在错误邻域——这是先验引导范式的结构性代价。
3. **`d0` 与 `d1` 可以在训练时构成耦合对**：TFM 需要从数据分布联合采样 `(d1, d0)`，即训练时必须能同时拿到真值视差和“退化视差”（由匹配网络在线产生）。没有真值视差的场景无法直接训 TFM。
4. **单目深度的低频结构可信**：REPA 把 encoder 中间特征拉向 DepthAnythingV2-L 特征（`L_repa = 1 − cos(h_φ(h_i), d*)`，权重 0.5），等价于假设单目深度在低频上是对的；反光/透明面上单目深度本身失效时，这个对齐项会把错误结构注入 encoder。
5. **`σ_max` 能覆盖真实歧义幅度**：`σ_t` 从 `σ_max` 线性收到 `σ_min`，多模态覆盖范围由 `σ_max` 这个超参决定，论文未报告其取值与敏感性分析。
6. **`U` 是有效的不确定度信号**：decoder 用“右图 warp 到左图”的误差当作不确定度输入，隐含假设遮挡/无纹理处该 warp 误差能反映歧义程度。

## 7 · 与相关工作对比

| 方法 | 范式 | 核心机制 | 关键弱点（论文口径） | 代表数字 |
|---|---|---|---|---|
| GwcNet / GANet / ACVNet | cost filtering | 3D/4D cost volume + 3D CNN 正则 | 计算贵、大视差扩展差、细节过度平滑 | ETH3D Bad1.0 Noc 6.42 / 6.22 / 2.58 |
| RAFT-Stereo | 迭代优化 | ConvGRU + 3D ACV | 缺非局部上下文，ill-posed 区陷局部极小、泛化差 | Scene Flow EPE 0.56 |
| IGEV-Stereo | 迭代优化 | 4D GEV + 迭代 | 同上；需 32 次迭代 | EPE 0.47，960×540 上 0.35 s |
| Selective-IGEV / DLNR / Mocha-Stereo | 迭代 + 频率分解 | 选择性 / 频率分解视差表示 | 仍是确定性单点回归 | EPE 0.44 / – / – |
| DEFOM-Stereo | 单目深度先验 | affine-invariant 深度 + metric scaling | 单点回归 + 域偏差 | EPE 0.42；Zero-shot KITTI-15 4.9 |
| MonSter / BridgeDepth / FoundationStereo | 基础模型 | 视觉基础模型 + 单目深度 | 慢（MonSter 0.64 s）；仍单点回归 | EPE 0.38；Zero-shot ETH3D 2.0 / **1.3** |
| DiffuVolume / D3RoMa / DiffMVS | 生成式（直接套） | diffusion 滤波 / diffusion 先验 / ConvGRU 去噪骨干 | 收益边际；ConvGRU 去噪把表征跨时间步纠缠、容量不足 | 论文未给这些方法的数值表 |
| **StereoFlow（本文）** | **先验引导生成式** | 渐进级联 + StereoDiT + TFM(2 步) | 非实时、两阶段训练不稳 | EPE **0.32**；0.39 s @960×540 |

**面试 Tip（被问到“这和直接拿 diffusion 做立体匹配有什么区别？”）**：
先给一句定调——“关键差别不在网络，而在**源分布**”。然后三点收束：(1) 通用 diffusion 从各向同性高斯起步，在极线约束下要在整条极线上盲搜，轨迹弯、步数多；(2) 本文把 ConvGRU 的确定性输出 `d0` 当源分布，生成只负责 `d0` 附近的局部多模态，所以 `σ_max` 保生成性、`σ_min` 防奇点，2 步 Euler 就够（Table IX：2 步 0.348 vs 5 步 0.347）；(3) 代价是先验错了就没救，而且两阶段训练（200k 无 StereoDiT + 100k 全模型）不稳定，延迟 0.39 s 还没进实时。最后补一句“这在思想上接近 Residual/Delta 建模——生成模型学残差而不是学全图”。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-07)

**repo 状态**：给定全文中**未出现任何 `github.com` 链接**（无项目页、无代码可用性声明），因此**官方 repo 未在论文中给出**。以下 3 条 pitfall 全部由 §6 失败模式与 §III 的具体方法约束推导，**未经任何 issue 验证**，不引用任何 issue 编号 / commit / URL。

1. **【由 §6 隐含假设 2 + §III-D 源分布定义推出】先验一旦跑偏，2 步采样没有自我纠错预算。**
   TFM 的路径均值是 `μ_t = t·d1 + (1−t)·d0`，t=0 端点严格锚在 `d0` 上；只有 2 步 Euler，且 `σ_max` 决定探索半径。工程后果：如果把 stage-1 checkpoint 换成别的匹配网络（或只训 stage-2），`d0` 的分布偏移会直接变成系统性偏差，且**不会像多步 diffusion 那样靠步数摊薄**。复现时要先单独验证 stage-1 的 EPE（论文 stage-1 只用 `L_match` 训 200k 步、lr 2e-4、batch 16），再挂 StereoDiT。

2. **【由 §6 隐含假设 1 + §III-B 的 ACV 形状推出】高分辨率 / 大视差输入会撞上 `w/4` 的候选上限并炸显存。**
   `C^a_{s=2} ∈ R^{w/4 × h/4 × w/4}`：视差候选数 = `w/4`，同时体量随 `w²` 增长。960 宽时是 240×h/4×240；若直接把 1920×1080 丢进去，单级 ACV 变为 480×270×480（约 `6.2×10⁷` 元素/级，且金字塔有 2 级、级联有 2 stage）。论文所有实验的分辨率口径是 960×540（Table VII 明确），未报告更高分辨率的结果与显存占用。部署时要么按宽度限制最大视差，要么先 resize —— 而 resize 会改变度量尺度，与“高频度量细节”的目标直接冲突。

3. **【由 §6 “不能做” + §IV-A 训练流程推出】想端到端一把训完会得到不稳定结果。**
   论文的流程是硬性两段：先 200k 步纯 `L_match`（无 StereoDiT），再 100k 步 `L_total`（`γ_match = 0.1`，`γ_repa = 0.5`）；结论段自述两阶段“increases complexity but also introduces instability”。同时 `L_repa` 需要 DepthAnythingV2-L 特征在线前向（`d*` 既是 REPA 目标又是 decoder 条件），意味着训练管线里常驻一个大单目深度模型——论文**未报告**其参数量、显存与耗时，因此显存预算无法从论文反推。复现建议：按 200k/100k 两段严格分离，并把 `γ_match = 0.1`（注意原文式 (11) 处把该符号误写成 `γ_iter`）作为首要调参项。

---

[← Back to Stereo & Matching README](./README.md)
> **Status**：v0.1 · 基于 arXiv:2607.19986v1 全文（已截断版）· 论文未报告的工程数字（VRAM、匹配网络/DepthAnythingV2-L 参数量、两级采样时间合计、`σ_min`/`σ_max` 取值）一律标注「论文未报告」，未做估算；§3 为明确标注的玩具设定；§8 无 repo 信号，全部为推导型 pitfall。

[//]: # "<!-- source: https://arxiv.org/abs/2607.19986 -->"
