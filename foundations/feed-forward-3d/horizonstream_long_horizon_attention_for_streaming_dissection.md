[//]: # "<!-- ontology-5axis
problem: reconstruction
representation: feature-grid
sensor: mono
paradigm: learned
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->"

# HorizonStream：面向流式三维重建的长时程注意力 (HorizonStream: Long-Horizon Attention for Streaming 3D Reconstruction)

> **发布时间**：arXiv:2605.23889v2 [cs.CV]，24 Oct 2026
> **论文 / 模型名**：HorizonStream
> **核心定位**：把"流式几何证据该保留多久"从人工设定（滑动窗/周期 reset）变成**通道级可学习指数衰减率**，用 O(1) 递归状态替代 KV cache，做到 48 帧训练、10,000+ 帧推理不漂移。

流式三维重建的病灶不在容量，而在**证据寿命被统一处理**：局部对应是短命的，全局尺度是长命的，而滑窗一律硬截断、无门控递归一律永久累积。HorizonStream 把传播核显式分解为 `K_spatial · K_time`，让每个通道学自己的遗忘率，从而在常数内存下稳定跨越万帧。

---

## X-Ray 开场

它解决的是**因果、有界内存约束下的长序列位姿/几何退化**（drift / jitter / collapse）。做法是把重建重写成"几何证据影响核" `K(t,i)` 的分解问题：长程因子用**通道级衰减的线性注意力**（递归状态 `S_t`，O(1) 内存），短程因子用**带 head 门控 + 三轴 RoPE 的窗口注意力**，再用 **Metric Readout Token** 从状态里读回尺度。对 spatial AI 研究者的意义：它给出了"线性注意力 + 局部注意力混合"的一个**可解释的物理解释**（证据寿命谱），并示范了"训练 clip 长度 48 → 推理 10K 帧"的长度外推路线；但它的状态是固定大小的摘要，细粒度 revisit 仍要靠外挂 loop closure。

---

## 📍 研究全景时间线

```
优化式 SLAM (ORB-SLAM3) ────────────────┐ 显式地图 + 局部 BA，吞吐受限
学习式对应 + 迭代 BA (DROID-SLAM/DPVO) ─┤
离线 feed-forward (DUSt3R/MASt3R/VGGT) ─┘ 全注意力、访问未来帧 → 违反在线因果
        │
        ▼  （在线化改造：三代机制）
空间记忆 ──► 持久循环状态 ──► 因果滑窗
(Spann3R/    (CUT3R/TTT3R)     (StreamVGGT/STream3R)
 MonST3R)     └ 无门控 → heavy tail、cache 饱和、attention sink
        │
        ├── KV 剪枝 (InfiniteVGGT)
        ├── keyframe memory (Lingbot-map)
        └── 周期 refresh (LongStream) ── 块状不连续核，每个边界丢累积上下文
        ▼
★ HorizonStream  (arXiv 2605.23889v2, 2026-10)
   K(t,i) = K_spatial(t,i) · K_time(t,i)：可解释的核形状分解
   └ 本文局限：O(1) 状态丢细粒度 revisit · loop closure 独立参数化且非单调增益
                · 依赖 VGGT/DINOv2 强预训练与大规模算力 · 纹理贫乏场景不可靠
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统/组件对比表

| 模块 | 输入 → 输出 | 训练 / 推理差异 | 对应因子 |
|---|---|---|---|
| ViT-L backbone（VGGT + DINOv2 初始化） | RGB 帧 → patch tokens / pose tokens / Metric Readout Token | frame blocks 做帧内自注意力；global blocks 混合 GWA 与 GLA，按深度交错插入 | — |
| **Gated Window Attention (GWA)** + Spatiotemporal RoPE | 窗口内 patch tokens → 局部匹配特征 | 训练与推理同为因果窗口；RoPE 时间索引**周期性重置**（MRT 与 pose token 用 `π=(0,0,0)`） | `K_spatial` |
| **Geometric Linear Attention** | 跨窗口 `k_i, v_i` + 逐帧 `γ_t` → `S_t`（d×d）+ 读出 `o_t` | 训练按 21 帧计算 chunk 串行传播状态；推理逐帧递推，状态长度无关 | `K_time` |
| **Metric Readout Tokens (MRT)** + 相对位姿融合 | `z^metric` → `ŝ = exp(g(z))`；窗口内 pose tokens → 共识相对位姿 | `scale loss` **只作用于 metric-scale 样本** | 度量读出 |
| DPT depth head + scale injection | 特征 → `D̂ = ŝ · D̂_raw` | 平移与深度用同一 `ŝ` 重缩放 | 度量读出 |
| Loop closure（可选，仅推理） | DINOv2 池化全局描述子 → 检索重访帧对 → 重入网络估计局部修正 → pose graph optimization | 训练中不参与；论文声明报告的显存数字**不含**该模块 | 事后纠偏 |

### 1.2 关键机制

**⚡ Eureka Moment：几何证据的"寿命"不是超参数，而是每个特征通道一个可学习衰减率 `γ_t^(c) ∈ (0,1)` —— 于是"保留多久"变成一个与序列长度无关的局部递推规则，可无限重复施加到任意长流上。**

三个约束到三个部件的映射（论文式 (1)）：
1. 空间内容感知（选可靠短程对应）→ `K_spatial`（GWA + head 门控 + 3D RoPE）；
2. 有界多时间尺度传播（不同证据不同寿命）→ `K_time`（`diag(γ_t)` 递归状态）；
3. 尺度与刚体位姿保持 → MRT + 相对位姿融合（避免 LongStream 式顺序 keyframe chaining 的复合误差累积）。

### 1.3 信息流

```
RGB 流 t
  │
  ├─► ViT-L frame block（帧内 SA）──► patch / pose / metric tokens
  │
  ├─► global block（W=10 因果窗口，21 帧计算 chunk）
  │      ├─ Gated Window Attention ── g_h=σ(W_g x̄+b_g)，y~_h = g_h·y_h   → K_spatial
  │      └─ Geometric Linear Attention ── S_t = diag(γ_t)S_{t-1} + φ(k_t)ṽ_tᵀ → K_time
  │
  ├─► MRT ──► ŝ = exp(g(z^metric)) ──► t̂ = ŝ·t̂_raw,  D̂ = ŝ·D̂_raw
  ├─► pose tokens 相对位姿融合 ──► T̂_t ∈ SE(3)（窗口内共识，非顺序链式）
  └─► DPT head ──► D̂
                     │
        （可选）DINOv2 描述子检索重访 ──► 重入网络 ──► pose graph optimization
```

---

## 2 · 数学核心

📌 **Napkin Formula**

```
S_t = diag(γ_t) · S_{t-1} + φ(k_t) ṽ_tᵀ ,   o_t = q_tᵀ S_t ,   γ_t = σ(W_γ x_t + b_γ) ∈ (0,1)^d
每个通道的寿命：τ^(c) = −1 / log γ̄^(c)
```

一句话：**把"重建"写成对历史几何证据的折扣最小二乘，它的递推解就是通道级门控线性注意力，衰减率决定每条证据的记忆半衰期。**

**目标**（式 2，discounted geometric state-estimation objective）

```
J_t(S) = Σ_{i=1}^{t} ( Π_{j=i+1}^{t} γ_j ) · ‖ Sᵀ k_i − v_i ‖²₂ ,   K_time(t,i) = Π_{j=i+1}^{t} γ_j
```

**变量**：`S ∈ ℝ^{d×d}` 递归几何状态；`k_i, v_i` 编码时刻 i 的对应/运动/结构/尺度证据；`γ_j` 第 j 步保留率；`q_t` 查询向量；`φ(·)` 把 key 映到线性注意力特征空间；`ṽ_t` 写入状态的值更新。

**递推**（式 4 → 式 5）：`J_t(S) = γ_t J_{t−1}(S) + ‖Sᵀk_t − v_t‖²₂`，其解给出固定状态更新 `S_t = γ_t S_{t−1} + φ(k_t)ṽ_tᵀ`。

**有界性**（式 3）：`γ̄ = sup_t |γ_t| < 1` 时
`‖q_tᵀ(Π_{j=1}^{t} γ_j)S_0‖ ≤ ‖q_t‖·‖S_0‖_F·γ̄^t → 0`
即初始状态/陈旧证据的影响指数衰减；反之 `γ_t ≡ 1` 就是无门控递归 → heavy tail 累积 + 状态污染。

**通道化**（式 6、7）：把标量 `γ_t` 换成向量 `γ_t = σ(W_γ x_t + b_γ)`，`S_t = diag(γ_t)S_{t−1} + φ(k_t)ṽ_tᵀ`；每通道有自己的时变核与有效记忆视界 `τ^(c) = −1/log γ̄^(c)`。低 `γ` 通道快速适配新观测，高 `γ` 通道跨窗口保结构/尺度。

**直觉**：`γ` 是"证据的信任半衰期"。尺度与场景结构必须活很久（`γ→1`），局部对应必须快速过期（`γ` 小）。让网络按当前帧内容预测每个通道的 `γ`，等价于在"立刻全忘（滑窗）"与"永不忘（全注意力）"两个极端之间学出一条连续保留谱。附录 B 进一步把它形式化为 test-time training 的等价形式（KV binding 的 TTT ≡ linear attention），所以这既是"在线学习"又是"高效递归注意力"。

---

## 3 · 带数字走一遍（玩具设定，非论文实验）

设 `d = 2`，两个通道：通道 1 是"局部对应"型，`γ^(1) = 0.5`；通道 2 是"全局尺度"型，`γ^(2) = 0.99`。时刻 0 写入一次证据 `ṽ_0 = [1, 1]ᵀ`（`φ(k_0)=1`），此后不再写入新证据（`k=0`），只观察旧证据的残留：

| 步数 t | 通道 1：`0.5^t` | 通道 2：`0.99^t` |
|---|---|---|
| 1 | 0.500 | 0.990 |
| 10 | 0.000977 | 0.904 |
| 20 | 9.5×10⁻⁷ | 0.818 |
| 100 | ≈0 | 0.366 |

有效寿命：`τ^(1) = −1/log 0.5 ≈ 1.44` 步，`τ^(2) = −1/log 0.99 ≈ 99.5` 步。

三点可复述的结论：
1. **同一份状态里并存两种时间尺度**——这是单个标量 `γ` 做不到的：全局 `γ=0.5` 会在 20 步内把尺度信息抹平；全局 `γ=0.99` 会把已经失效的局部对应留在状态里污染后续匹配（即论文归因的 heavy-tail / attention sink）。
2. **核是长度无关的**：`K_time(t,i)` 只依赖 `i+1..t` 之间的 `γ` 连乘，与总帧数无关 → 48 帧训练出的规则可反复施加到 10K+ 帧，这是"训练短、推理长"的数学依据。
3. **单步计算量恒定**：每帧只做一次 `d×d` 的乘性衰减 + 一次秩一外积写入，与历史长度无关（O(1) 状态、线性时间）。

> 注意：上表是演示用的玩具设定；论文的真实 `γ` 分布见其 Fig. 6(a)（层 4 偏中程、层 11 出现明显长保留尾部），论文未给出逐通道数值。

---

## 4 · 工程视角

| 维度 | 论文给出的信息 |
|---|---|
| 训练算力 | Stage 1：**64 张 A800**、60k iterations；Stage 2：**64 张 H20**、40k iterations（Stage 2 增加长序列数据） |
| 优化器 | AdamW，lr `2×10⁻⁵`，cosine schedule，2000 warmup steps |
| 训练样本 | 48-frame clips；以 **21 帧计算 chunk** 顺序处理；位姿预测窗口 **W = 10**；时间 stride 1–8 |
| 推理 FPS | Table 2 中 Ours **13.20**，Ours w/ LC **10.45**（同表 Lingbot-map 11.9、LongStream 17.10、TTT3R 22.00、COLMAP 0.20） |
| FPS 测试硬件 | **论文未报告** |
| 显存占用 (GB) | **论文未报告**具体数值；论文仅声明"报告的 GPU memory usage 不含可选 loop-closure 模块" |
| 复杂度声明 | 论文称 constant memory + linear time（用于 10,000+ 帧序列）；附录 E 有 runtime/memory scaling，正文未给数值 |
| 骨干 | ViT-L，VGGT + DINOv2 初始化 |

Trade-off 读法：
- **FPS 不是它的卖点**：13.20 低于 TTT3R 的 22.00 与 LongStream 的 17.10，甚至低于 InfiniteVGGT 的 5.30 之外的多数轻量方案？——注意 InfiniteVGGT 是 5.30，反而更慢。所以它处在"中等吞吐、最强长序列稳定性"的位置；开 loop closure 后掉到 10.45（`UNVERIFIED`：这是同表数值，未说明是否同硬件同分辨率）。
- **状态固定 → 内存恒定但细节有损**：论文 Discussion 明确承认"对含重复回访的超长序列，固定大小递归状态仍会漏掉细粒度细节"（Fig. 10），即省下的内存换来的是不可回滚的信息损失，纠偏要靠外挂 loop closure。
- **训练-推理同构**：训练也用 21 帧 chunk 串行传播状态，避免 train/test 窗口语义不一致；但代价是 chunk 间串行依赖，序列维度无法并行展开。
- **部署门槛在预训练**：论文自述 "relies on strong pretraining and substantial training compute"，即复现成本主要在 VGGT/DINOv2 初始化与 24 数据集混合，而非模型结构本身。

---

## 5 · 数据与评测

**评测数据集（正文逐字列出，全部按全长无下采样）**：KITTI、vKITTI2、Oxford Spires、ScanNet++、TUM RGB-D、Waymo Open、VBR、ETH3D、7Scenes。其中 vKITTI2 / 7Scenes / Waymo / ScanNet++ **属于训练数据**（Waymo 评测用训练未见片段）。

**训练数据**：24 个数据集，含 ScanNet++、Hypersim、Replica、7Scenes、ARKitScenes、WildRGB-D、Waymo、vKITTI2、Mapillary、MegaDepth、BlendedMVS、DL3DV、CO3Dv2、TartanAir、PointOdyssey、OmniWorld、MatrixCity 及内部长序列数据等；无序图像集通过遍历相机图构造伪时序；chunk 内以 0.2 概率随机置换帧，跨 chunk 顺序保持。

**baseline 三族**：(i) 优化式 COLMAP、DPVO/DPVO++、DROID-SLAM、MASt3R-SLAM、MASt3R-SfM、VGGT-SLAM；(ii) 离线 feed-forward VGGT-Long、FastVGGT、LoGeR / LoGeR\*、Pi3-Chunk；(iii) 在线 feed-forward CUT3R、TTT3R、STream3R、StreamVGGT、InfiniteVGGT、LongStream、Lingbot-map。

**指标与关键数字（逐字取自表格）**

| 表 | 指标 | Ours | 对照（最强对手） |
|---|---|---|---|
| Table 1 KITTI | 平均 ATE ↓ | **19.75** / w LC **16.44** | Lingbot-map 25.29；LoGeR 21.91；LoGeR\* 16.35 |
| Table 2 | ATE ↓ VKITTI2 / KITTI / Oxford / ScanNet++ / TUM / Waymo | 0.94 / 19.75 / **9.38** / **0.40** / **0.04** / **0.46** | Lingbot-map 1.30 / 25.29 / 15.46 / 0.52 / 0.04 / 1.66 |
| Table 3 VBR | 平均 ATE ↓ | **25.30** / w LC **18.84** | Lingbot-map 27.53；LoGeR\* 25.24；LongStream 77.93 |
| Table 4 | CD ↓ / F1 | ETH3D 0.32 / 0.74；Oxford **4.97** / **0.89**；7Scenes **2.98** / **0.93**；TUM **0.08** / **0.95** | ETH3D 上 LoGeR 0.09 / 0.90 更优 |
| Table 5 KITTI depth | Abs Rel ↓ / δ&lt;1.25 ↑ | **0.057** / 94.8 | VGGT 0.061 / **97.0** |
| Table 6 vKITTI2 消融 | ATE ↓ @80f/200f/400f | 0.42 / 0.71 / 1.20 | w/o GLA：0.83 / 2.06 / 5.38；w/o GWA：0.78 / 2.64 / 7.46 |

**读表警示（关键，别背错）**

1. **KITTI 序列 09**：Ours **25.73**，而 **LoGeR 是 17.89**（`9.03` 是 **LoGeR\*** 的值）。也就是说该长序列上 LoGeR 系列明显优于本文，不能把 LoGeR\* 的成绩记到 LoGeR 名下。
2. **VBR 的 campus_0（12,042 fr.）**：Ours **22.46**，w/ LC **28.54**（回环后**变差**）；**campus_1（11,671 fr.）** 才是 Ours **22.49** → w/ LC **8.49**。把两列的 22.49/8.49 安到 campus_0 上，会把该序列的回环收益夸大一个量级。
3. **"超越所有离线方法"不成立于平均 ATE**：KITTI 平均 LoGeR\* 16.35 略优于 Ours 19.75、与 Ours w/ LC 16.44 基本持平；VBR 平均 LoGeR\* 25.24 也略优于 Ours 25.30。
4. **逐场景非全胜**：KITTI seq 00 VGGT-Long 8.64 优于 Ours 26.40；seq 02 Lingbot-map 82.29 优于 Ours 84.62；seq 03 Lingbot-map 2.49 优于 Ours 5.15。
5. **深度指标方向不一致**：Abs Rel 0.057 为表内最低，但 δ&lt;1.25 为 94.8，低于 VGGT 的 97.0；只引 Abs Rel 说"全面超越 VGGT"是过度解读（论文自身措辞是 "approaches the best offline methods"）。

---

## 6 · 能力与失败模式

**能做（有表格支撑）**
- 极长序列稳定位姿：VBR 上 8,815–18,846 帧的七个序列，无 refresh 机制而平均 ATE 25.30；开启 LC 后 18.84（其中 campus_1 由 22.49 → 8.49、ciampino_1 由 26.10 → 17.76）。
- 消除周期 refresh 依赖：Table 1/3 显示 CUT3R、TTT3R、LoGeR 的 w/o refresh 变体全部急剧退化（如 CUT3R 平均 91.62 → 209.78，TTT3R 72.86 → 177.73），作者据此论证退化源于状态污染而非容量。
- 尺度一致性：`ŝ` 同时重缩放平移与深度，KITTI depth Abs Rel 0.057 为表内最优。
- 消融可归因：去掉 GLA（0.83/2.06/5.38）、去掉 GWA（0.78/2.64/7.46）、去掉 channel-wise gating（0.67/1.43/3.21）都在长端显著变差。

**不能做 / 明确失败**
- **细粒度 revisit 会丢**：论文 Discussion 承认固定大小递归状态在重复回访的超长序列上"misses fine-grained details"（Fig. 10）。
- **动态前景污染**：论文原文 "Dynamic foreground objects can also corrupt local geometric evidence in the input video"。
- **纹理贫乏场景**："can be less reliable in texture-poor scenes"。
- **loop closure 不是单调增益**：VBR campus_0 上 Ours 22.46 → w/ LC 28.54（变差），说明检索-重入-位姿图这条链路在某些序列上会引入错误约束。
- **局部窗口定姿的上限**：位姿仅用 W = 10 帧窗口，论文自述"更大的 pose window 可能进一步提升内部回环能力"，即当前不具备模型内部的长程回环能力。

### 隐含假设 (Hidden Assumptions)

1. **通道 ≈ 证据语义类型**：`τ^(c)` 的可解释性依赖"某个通道专管某一类几何证据"这一假设。网络只被端到端 loss 监督，没有任何项强制通道语义解耦；论文用附录 E.1 的 channel-to-geometry linear probing 事后佐证，属于**观察性证据而非设计约束**。
2. **遗忘率可由单帧内容决定**：`γ_t = σ(W_γ x_t + b_γ)` 只看当前帧特征 `x_t`，**不看状态、也不看证据是否被后续观测验证**。即"该不该忘"由当前外观决定，而不是由"这条记忆后来被证实/证伪"决定。
3. **乘性整体缩放足以处理错误记忆**：`diag(γ_t)S_{t−1}` 只能对所有通道的旧状态做整体收缩，**没有定点擦除机制**；错误证据只能等它自然衰减，或靠外挂 loop closure 事后修正。
4. **局部 10 帧足以定姿**：快速旋转、低纹理、强遮挡下窗口内对应不足时无回退路径。
5. **场景近似静态**：几何一致性假设被动态物体破坏（论文自陈）。
6. **尺度可从固定状态线性读出**：`ŝ` 是单一标量，同时作用于平移与深度；这要求深度与平移的尺度误差同源（训练里确实用统一几何尺度因子归一化）。
7. **位置编码可在窗口边界重置**：Spatiotemporal RoPE 的时间索引被周期性重置，假设只有相对窗口内偏移有意义；跨重置边界的重访帧，时间偏置被折叠。
8. **48 帧训练可外推到 10K 帧**：依据是核的局部性+长度无关性；但状态摘要能力本身并未随长度增长，属于"规则可外推、容量不可外推"。

---

## 7 · 与相关工作对比

| 方法 | 长程机制 | 内存 | 长序列行为（论文口径 + 表内数字） |
|---|---|---|---|
| CUT3R / TTT3R | 无门控持久循环状态 | 固定状态 | 无 refresh 急剧退化（KITTI 平均 209.78 / 177.73），TTT3R w/ refresh 72.86；VBR 66.25 / 64.99 |
| StreamVGGT / STream3R | 因果掩码 + 滑窗 | 窗口受限 | box kernel 硬截断，KITTI 平均 226.15 / 227.77 |
| InfiniteVGGT | KV cache 剪枝 | 剪枝后缓存 | KITTI 183.85，VBR 91.60 |
| LongStream | 周期 cache refresh | 固定状态 + 定期重置 | 定位了 attention sink，但边界丢累积上下文；KITTI 51.90，VBR 77.93 |
| Lingbot-map | keyframe memory 扩展上下文 | 关键帧记忆 | ATE 有竞争力（KITTI 25.29、VBR 27.53），但论文 Fig. 4/5 指出其抖动随序列增长加剧、点云重叠 |
| LoGeR / LoGeR\* | 离线 chunk + 累积权重 / 优化变体 | 随 chunk | KITTI 21.91 / 16.35；VBR 28.02 / 25.24 — **最强的非流式对手** |
| **HorizonStream** | 通道级衰减线性注意力 + Gated Window Attention + MRT | **O(1) 状态，长度无关** | KITTI **19.75**（w/ LC 16.44）、VBR **25.30**（w/ LC 18.84），无 refresh |

**面试 Tip**：被问"为什么不干脆用更大的滑动窗或全注意力？"——这样答：
> "滑窗是 box kernel，硬截断会把仍然有效的长寿命证据（尺度、场景结构）提前扔掉；全注意力的 KV 随长度线性增长，且因果 softmax 会退化成 attention sink，把权重集中到无关的早期 token 上。HorizonStream 的论点是：流式几何证据的寿命是**异构**的，所以它把影响核分解成 `K_spatial · K_time`，用逐通道的 `γ`（等价于 `τ=−1/log γ̄`）学出一条连续保留谱，状态恒定、时间线性，训练只需 48 帧 clip。但要诚实补一句：在 KITTI 平均 ATE 上 LoGeR\* 的 16.35 与它的 w/ LC 16.44 基本持平，说明优化式离线流程仍是强对手，它的优势主要在**因果 + 常数内存**这个约束下。"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-27)

**repo 状态：论文正文只给出项目主页 `https://3dagentworld.github.io/horizonstream/`，未出现任何 `github.com` 仓库链接**（正文仅一句 "Our inference code and evaluation scripts have been released"）。按无 repo 信号处理：以下 pitfalls **不由 issue 流验证**，而是由 §6 失败模式 + 本文方法约束机械推导，标注为推导项。

**P1 — 错误证据只能"等它衰减"，不能"定点删除"。**
来源链：§6 假设 3（`diag(γ_t)` 只做整体乘性收缩，无定点擦除）+ §6 失败模式"动态前景污染局部几何证据"。机制后果：一旦某个高 `γ` 通道在 t₀ 被前景/误匹配写入，它会在 `γ̄^(c)` 的时间常数内持续参与读出，模型没有"这条是错的、立刻清零"的通路；纠偏必须等 loop closure 重入网络 + pose graph。工程上表现为：走廊/重复纹理/行人穿场时，误差是**缓慢衰减而非即时恢复**，`τ^(c)` 越大恢复越慢。

**P2 — loop closure 是外挂且非单调，不能当默认开关。**
来源链：§6 失败模式"loop closure 不是单调增益"（VBR campus_0：Ours 22.46 → w/ LC **28.54**）+ §6 假设 3（模型内部无回环能力，位姿窗口仅 W=10）。机制后果：检索-重入-位姿图三个环节任一给出错误约束，就会把本来正确的轨迹拉偏；且论文声明报告的显存数字**不含**该模块，说明它是一段独立参数化、独立开销的推理期流程（论文 Discussion 自陈 "currently parameterized separately, and its optimization settings could be further refined"）。落地时必须按序列 A/B 决定是否开启，而非全局默认开。

**P3 — 位置编码周期性重置 + 21 帧 chunk 串行状态，使"跨重置边界的重访"信息被折叠。**
来源链：§6 假设 7（Spatiotemporal RoPE 时间索引周期性重置，MRT/pose token 固定 `π=(0,0,0)`）+ §1.1 表（训练以 21 帧 chunk 顺序传播状态，位姿窗口 W=10 &lt; chunk 长度）。机制后果：重访帧对若落在不同重置周期内，相对时间偏置不再反映真实间隔；同时 W=10 的位姿窗口与 21 帧 chunk 边界不对齐，工程复现时容易在 chunk 接缝处出现位姿/尺度跳变——这属于**推导**，需在真机上按 chunk 边界做误差分段统计来确认（`UNVERIFIED`）。

---

[← Back to streaming-3d-reconstruction README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2605.23889v2 全文 · 未在真机复现的数字标 `UNVERIFIED`（§4 的 FPS 测试硬件、显存 GB、runtime scaling 数值论文均未报告）

[//]: # "<!-- source: https://arxiv.org/abs/2605.23889 -->"
