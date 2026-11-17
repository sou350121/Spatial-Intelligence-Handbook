[//]: # "<!-- ontology-5axis
problem: depth
representation: n/a
sensor: mono
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 信号脚手架：释放轻量模型在自监督单目深度估计中的潜力 (Signal Scaffolding: Unlocking the Potential of Lightweight Models for Self-Supervised Monocular Depth Estimation)

> **发布时间**：2026-11-13（arXiv:2611.17828v1 [cs.CV]）
> **论文 / 模型名**：Signal Scaffolding (SS) / ReForgeDepth
> **核心定位**：它指出轻量自监督单目深度的精度天花板部分来自“预训练→直接微调”的训练信号错配，用三阶段 Signal Scaffolding 在不加参数、不加数据的前提下，把 1.5M 模型推到 KITTI 640×192 轻量档 Abs Rel 0.102。

轻量深度模型部署友好，但精度长期挤在窄带里；作者不改架构、不加数据，改的是训练流程。结论是：固定容量下，训练信号的“到达顺序”和“对齐方式”本身就能释放可恢复容量。

**X-Ray 开场**：这篇论文解决的是“轻量自监督深度模型为什么怎么练都难突破”的问题——作者认为根因不是容量 alone，而是标准两阶段训练没有把轻量学生假设空间里可恢复的部分激活。它提出三阶段 SS：ImageNet 初始化 → 纯光度自监督适应目标域 → 用域匹配教师做中位数对齐的 log 相对深度蒸馏，并 warm-up 注入。对 spatial AI 研究者意味着：在边缘部署约束下，训练课程与信号对齐可能比继续堆参数更划算。

## 📍 研究全景时间线

```
早期       Zhou et al. / Monodepth2 奠定光度自监督 + min-reprojection + auto-mask
  │
2023       Lite-Mono / MViTDepth 把轻量编码器压到 2–3M 级
  │
2024       R-MSFM3/6-GC 继续多尺度轻量设计
  │
2025       LEDepth / ADDepth / EdgeMono / PuriLight 进入 <5M 精度窄带
  │
2026       LEA-depth / Flex-Nano / 本文 ReForgeDepth + Signal Scaffolding
          └─ 本文位置：不改架构，改训练课程；把“容量分配”问题转成“信号组织”问题
```

本文局限：光度一致性在运动物体周围会退化；没有 GT 深度，精度上限仍受监督信号限制；Phase III 仍需要一个域匹配教师（Flex-Large），训练流程比标准两阶段更复杂。

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| GMD（Gated Multi-Dilation Block） | 编码器特征 \(X\in\mathbb&#123;R&#125;^&#123;H\times W\times C&#125;\) | 自适应多膨胀局部上下文 \(\hat X\) | 训练时含 DropPath、LayerScale；推理为普通 depthwise/pointwise 卷积 |
| DCGI（Detail-Compensated Global Interaction） | 局部块输出 \(L=Z_i\)、下采样 stage 输入 \(S=X_i\) | 保留高频残差 + 通道交互的 stage 输出 \(\hat Z_i\) | XCA 通道注意力，\(O(C^2)\)；训练含 DropPath、LayerScale |
| Decoder + RGB Boundary Residual | 多尺度编码特征 + RGB 亮度 Sobel 边缘 \(G\) | 全分辨率、1/2、1/4 深度图 | 推理只用 RGB 与 DepthNet；BR 是轻量 depthwise–pointwise + sigmoid gate |
| PoseNet | 相邻两帧通道拼接 | 6-DoF 相对位姿 \(T_&#123;t\to t'&#125;\) | 仅训练参与自监督目标，推理丢弃 |
| Signal Scaffolding | 学生、教师、训练阶段 | 三阶段训练课程 | 教师只在 Phase III 训练时使用；不增加推理开销 |
| 自监督目标 | \(I_t,I_&#123;t'&#125;,D_t,T,K\) | \(\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;\) | 光度重投影 + min over sources + auto-mask + 边缘感知平滑 |
| 蒸馏目标 | 学生/教师逆深度 | \(\mathcal&#123;L&#125;_&#123;\text&#123;KD&#125;&#125;\) | median 归一化 + log 相对误差 + 多尺度几何权重 + warm-up |

### 1.2 关键机制

**⚡ Eureka Moment：轻量模型的精度天花板不全是“容量不够”，而是“训练信号没有按学生能吸收的顺序到达”；先让学生用光度自监督适应目标域，再用中位数对齐的 log 相对深度做渐进教师蒸馏，能把固定容量里可恢复的部分激活。**

三阶段拆解：

1. **Phase I — ImageNet 初始化**：给编码器一个通用视觉起点。
2. **Phase II — 光度自监督训练**：学生先在目标域上用重投影 photometric loss 适应任务。
3. **Phase III — 教师蒸馏**：冻结域匹配教师 Flex-Large，用 median 对齐的 log 相对深度做 KD；\(\lambda_e=\eta\min(1,e/5)\)，\(\eta=0.1\)，从 0 逐步 ramp 到 0.1。

论文强调 SS **不引入额外数据集、不增加参数、不增加推理开销**；教师只在训练期存在。

### 1.3 信息流

```
训练 Phase II（光度自监督）
I_t, I_{t±1} ──> PoseNet ──> T_{t→t'}
      │
      └──> DepthNet: GMD encoder → DCGI → Decoder → RGB Boundary Residual
                                   │
                                   └──> D_t
                     warp + min-reprojection + auto-mask + smoothness

训练 Phase III（教师脚手架）
Teacher (Flex-Large, frozen) ──> q_tch
Student DepthNet ──> q_stu
        │
        └──> median 归一化 → log 相对残差 → 多尺度加权 L_KD
                                   │
                     L = L_base + λ_e · L_KD

推理
I_t ──> DepthNet ──> depth map
（PoseNet 与 Teacher 均丢弃）
```

## 2 · 数学核心

📌 **Napkin Formula**：

\[
\mathcal&#123;L&#125;=\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;+\lambda_e\mathcal&#123;L&#125;_&#123;\text&#123;KD&#125;&#125;,\qquad
\lambda_e=0.1\min\!\left(1,\frac&#123;e&#125;&#123;5&#125;\right),\qquad
\mathcal&#123;L&#125;_&#123;\text&#123;KD&#125;&#125;=\frac&#123;\sum_&#123;k=0&#125;^&#123;2&#125;2^&#123;-k&#125;\ell_&#123;\mathrm&#123;KD&#125;&#125;^k&#125;&#123;\sum_&#123;k=0&#125;^&#123;2&#125;2^&#123;-k&#125;&#125;
\]

一句话直觉：先用光度一致性把学生拉到目标域，再用 median 对齐的 log 深度残差把教师信号“架”上去；warm-up 防止教师早期压死学生。

### 2.1 自监督基础目标

**目标**：用单目视频的光度重投影训练 DepthNet + PoseNet。

对目标帧 \(I_t\)，DepthNet 预测 \(D_t\)，PoseNet 预测 \(T_&#123;t\to t'&#125;\)，源帧像素按投影位置合成目标视图：

\[
I_&#123;t'\to t&#125;=I_&#123;t'&#125;\big\langle \operatorname&#123;proj&#125;(D_t,T_&#123;t\to t'&#125;,K)\big\rangle
\]

光度误差：

\[
pe(I_a,I_b)=\frac&#123;\alpha&#125;&#123;2&#125;\big(1-\operatorname&#123;SSIM&#125;(I_a,I_b)\big)+(1-\alpha)\|I_a-I_b\|_1,\quad \alpha=0.85
\]

逐像素取源帧最小值，抑制遮挡/出视野：

\[
L_p=\min_&#123;t'&#125; pe\big(I_&#123;t'&#125;\langle \operatorname&#123;proj&#125;(D_t,T_&#123;t\to t'&#125;,K)\rangle,I_t\big)
\]

auto-mask：

\[
\mu=\big[\min_&#123;I_s\in[-1,1]&#125;L_p(I_s,I_t)>\min_&#123;I_s\in[-1,1]&#125;L_p(I_&#123;t'&#125;,I_t)\big]
\]

边缘感知平滑：

\[
L_&#123;\text&#123;smooth&#125;&#125;=|\partial_x d_t^*|e^&#123;-|\partial_x I_t|&#125;+|\partial_y d_t^*|e^&#123;-|\partial_y I_t|&#125;,\quad d_t^*=d_t/\bar d_t
\]

基础损失：

\[
\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;=\sum_&#123;s=\&#123;1,\frac12,\frac14\&#125;&#125;\mu\odot L_p+\lambda L_&#123;\text&#123;smooth&#125;&#125;,\quad \lambda=10^&#123;-3&#125;
\]

### 2.2 Signal Scaffolding 的蒸馏

**目标**：在不改参数/数据的前提下，把域匹配教师的深度知识渐进注入学生。

学生与教师都预测“未知 per-image scale”的逆深度，先按图像域中位数对齐：

\[
\widetilde q=\frac&#123;q&#125;&#123;\operatorname&#123;median&#125;_&#123;p\in\Omega&#125;q(p)&#125;
\]

在 log 域比较，得到相对误差：

\[
r_k(p)=\log\max(\widetilde q_&#123;\text&#123;stu&#125;&#125;^k(p),\epsilon)-\log\max(\widetilde q_&#123;\text&#123;tch&#125;&#125;^k(p),\epsilon)
\]

\[
\ell_&#123;\mathrm&#123;KD&#125;&#125;^k=\frac&#123;1&#125;&#123;|\Omega_k|&#125;\sum_&#123;p\in\Omega_k&#125;\sqrt&#123;r_k(p)^2+\epsilon^2&#125;,\quad \epsilon=10^&#123;-6&#125;
\]

多尺度几何权重 \(w_k=2^&#123;-k&#125;\)：

\[
\mathcal&#123;L&#125;_&#123;\mathrm&#123;KD&#125;&#125;=\frac&#123;\sum_&#123;k=0&#125;^&#123;2&#125;w_k\ell_&#123;\mathrm&#123;KD&#125;&#125;^k&#125;&#123;\sum_&#123;k=0&#125;^&#123;2&#125;w_k&#125;
\]

总目标：

\[
\mathcal&#123;L&#125;=\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;+\lambda_e\mathcal&#123;L&#125;_&#123;\mathrm&#123;KD&#125;&#125;,\quad
\lambda_e=\eta\min(1,e/5),\quad \eta=0.1
\]

其中 \(e\) 是从 Phase III 开始、从 0 计数的训练轮次。

### 2.3 变量说明

| 符号 | 含义 | 本文取值 / 备注 |
|---|---|---|
| \(\alpha\) | 光度误差中 SSIM 与 L1 的平衡 | 0.85 |
| \(\lambda\) | 平滑项权重 | \(10^&#123;-3&#125;\) |
| \(\mu\) | auto-mask | \(\&#123;0,1\&#125;\) |
| \(s\) | 输出尺度 | \(1,\frac12,\frac14\) |
| \(k\) | 蒸馏尺度索引 | \(0,1,2\) 对应 full、1/2、1/4 |
| \(w_k\) | 多尺度蒸馏权重 | \(2^&#123;-k&#125;\) |
| \(\eta\) | KD 最大权重 | 0.1 |
| \(e\) | Phase III 训练轮次 | 从 0 开始 |
| \(\epsilon\) | 数值稳定项 | \(10^&#123;-6&#125;\) |

**直觉**：median 归一化只消除 per-image scale；log 域让远近深度的相对误差更均衡，大深度不会主导；多尺度权重让全分辨率边界细节优先；warm-up 让轻量学生先适应光度任务，再逐步接受教师信号。

## 3 · 带数字走一遍

> 以下为玩具设定，用来演示公式，不是论文实验数字。

设一张图取 3 个像素，忽略遮挡与 auto-mask。

学生原始逆深度：

\[
q_&#123;\text&#123;stu&#125;&#125;=[0.4,\ 1.0,\ 2.5]
\]

中位数 \(=1.0\)，归一化后：

\[
\widetilde q_&#123;\text&#123;stu&#125;&#125;=[0.40,\ 1.00,\ 2.50]
\]

教师原始逆深度：

\[
q_&#123;\text&#123;tch&#125;&#125;=[0.5,\ 1.2,\ 2.0]
\]

中位数 \(=1.2\)，归一化后：

\[
\widetilde q_&#123;\text&#123;tch&#125;&#125;=[0.4167,\ 1.00,\ 1.6667]
\]

逐像素 log 残差：

\[
r=\left[\ln\frac&#123;0.40&#125;&#123;0.4167&#125;,\ 0,\ \ln\frac&#123;2.50&#125;&#123;1.6667&#125;\right]
\approx[-0.0408,\ 0,\ 0.4055]
\]

取 \(\sqrt&#123;r^2+\epsilon^2&#125;\approx|r|\)，full 尺度项：

\[
\ell_&#123;\mathrm&#123;KD&#125;&#125;^0\approx\frac&#123;0.0408+0+0.4055&#125;&#123;3&#125;=0.1488
\]

若玩具设定下 1/2、1/4 尺度项分别为 \(0.090\)、\(0.050\)，则：

\[
\mathcal&#123;L&#125;_&#123;\mathrm&#123;KD&#125;&#125;
=\frac&#123;1\cdot0.1488+0.5\cdot0.090+0.25\cdot0.050&#125;&#123;1+0.5+0.25&#125;
=\frac&#123;0.2063&#125;&#123;1.75&#125;
\approx0.1179
\]

Phase III 的权重：

| \(e\) | \(\lambda_e=0.1\min(1,e/5)\) | 含义 |
|---:|---:|---|
| 0 | 0 | 第一轮不给教师信号 |
| 1 | 0.02 | 轻微注入 |
| 5 | 0.1 | 达到最大权重 |

若 \(\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;=0.5\)，到 \(e=5\) 时总损失约为：

\[
0.5+0.1\times0.1179=0.51179
\]

这个玩具例子说明：median 归一化让“学生整体乘 2”不改变 KD 误差；log 残差把远近深度的相对偏差拉到同一量级；warm-up 让教师项从 0 平滑进入。

## 4 · 工程视角

论文报告了 640×192 输入、Apple Core ML（Float32）、200 次运行取平均、50 次 warm-up 的端侧延迟：

| 方法 | Params (M) | FLOPs (G) | Abs Rel ↓ | MacBook Air M2 速度 (ms) ↓ | M2 FPS ↑ | iPhone 12 A14 速度 (ms) ↓ | A14 FPS ↑ |
|---|---:|---:|---:|---:|---:|---:|---:|
| Monodepth2 | 14.3 | 8.0 | 0.115 | 21.36 | 47 | 30.47 | 33 |
| R-MSFM3 | 3.5 | 16.5 | 0.114 | 21.61 | 46 | 47.53 | 21 |
| Lite-Mono | 3.1 | 5.0 | 0.107 | 18.27 | 55 | 41.65 | 24 |
| PuriLight | 2.7 | 7.1 | 0.106 | 37.26 | 27 | 60.64 | 16 |
| **ReForgeDepth** | **1.5** | **3.6** | **0.102** | **17.28** | **58** | **29.80** | **34** |

关键 trade-off：

- **参数/FLOPs**：ReForgeDepth 1.5M、3.6G FLOPs；比 Monodepth2 的 14.3M/8.0G 小很多，但 iPhone 12 延迟 29.80 ms 与 Monodepth2 的 30.47 ms 接近。论文解释：Monodepth2 是纯卷积架构，移动推理引擎优化得好；FLOPs 不能单独预测端侧延迟。
- **PuriLight 的反例**：FLOPs 7.1G 不算高，但 iPhone 12 60.64 ms，论文归因于其 frequency-domain operations 在移动端支持差。
- **实时性**：论文称 ReForgeDepth 在 iPhone 12 上 29.80 ms / 34 FPS，在 M2 上 17.28 ms / 58 FPS；这是论文报告的数字，未在真机复现。
- **训练硬件**：Intel Core Ultra 7 270K CPU、NVIDIA RTX 5080、48 GB RAM；PyTorch；AdamW（\(10^&#123;-2&#125;\) decay）；GMD/DCGI 使用 drop-path。
- **训练时长/显存/功耗/热稳定性/INT8/FP16**：论文未报告。不要把这些当成已验证的部署指标。
- **推理图**：PoseNet 只在训练期使用，推理丢弃；Teacher 也只在 Phase III 使用，因此端侧只有 DepthNet。

## 5 · 数据与评测

### 5.1 数据组成

| 数据集 | 用途 | 规模 | 分辨率 / 设置 |
|---|---|---|---|
| KITTI Eigen split | 训练 / 验证 / 测试 | 39,180 monocular triplets \(\&#123;I_&#123;t-1&#125;,I_t,I_&#123;t+1&#125;\&#125;\)；4,424 validation；697 test | 主表 640×192；正文还提到 1024×320 设置 |
| Cityscapes | 动态城市场景 benchmark | 58,335 training；1,525 test（按 [10] split） | 416×128 |
| Make3D | 跨数据集泛化 | 134 outdoor test images | KITTI 训练模型直接迁移，无 fine-tuning |

### 5.2 训练与评测条件

- **KITTI**：标准 Eigen split；训练用单目三元组；主表在 640×192 下比较；正文还声称 1024×320 下 Abs Rel 最佳，但截断全文未给出该设置的具体表值。
- **Cityscapes**：拥挤城市街道、大量运动物体；按 [10] 的 58,335/1,525 split，416×128。
- **Make3D**：KITTI-trained 模型直接测试，不做 fine-tuning。
- **训练 schedule**：从 scratch 60 epochs、\(5\times10^&#123;-4&#125;\)、cosine；或 ImageNet pretraining 30 epochs、\(1\times10^&#123;-4&#125;\)，再用 frozen Flex-Large teacher 训练 30 epochs、\(5\times10^&#123;-5&#125;\)。
- **评价指标**：Abs Rel、Sq Rel、RMSE、RMSE log、\(\delta&lt;1.25\)、\(\delta&lt;1.25^2\)、\(\delta&lt;1.25^3\)、Params；端侧另有 FLOPs、ms、FPS。

### 5.3 主要结果（原文数字）

| 设置 | 方法 | Params | Abs Rel ↓ | Sq Rel ↓ | RMSE ↓ | RMSE log ↓ | \(\delta&lt;1.25\) ↑ | \(\delta&lt;1.25^2\) ↑ | \(\delta&lt;1.25^3\) ↑ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KITTI 640×192 | Lite-Mono | 3.1M | 0.107 | 0.765 | 4.561 | 0.183 | 0.886 | 0.963 | 0.983 |
| KITTI 640×192 | PuriLight | 2.7M | 0.106 | 0.747 | 4.536 | 0.182 | 0.890 | 0.964 | 0.984 |
| KITTI 640×192 | Flex-Nano | 1.5M | 0.110 | 0.794 | 4.678 | 0.184 | 0.878 | 0.961 | 0.983 |
| KITTI 640×192 | **ReForgeDepth** | **1.5M** | **0.102** | **0.726** | **4.459** | **0.179** | **0.891** | **0.964** | **0.983** |
| Cityscapes 416×128 | Flex-Nano | 1.5M | 0.107 | 1.261 | 6.133 | 0.164 | 0.893 | 0.971 | 0.989 |
| Cityscapes 416×128 | PuriLight | 2.7M | 0.099 | 1.014 | 5.892 | 0.153 | 0.901 | 0.976 | 0.992 |
| Cityscapes 416×128 | **ReForgeDepth** | **1.5M** | **0.091** | **0.918** | **5.590** | **0.146** | **0.912** | **0.978** | **0.992** |
| Make3D zero-shot | Lite-Mono-tiny | 2.2M | 0.318 | 3.217 | 7.234 | 0.164 | — | — | — |
| Make3D zero-shot | Flex-Small | 6.1M | 0.315 | 3.127 | 6.865 | 0.159 | — | — | — |
| Make3D zero-shot | **ReForgeDepth** | **1.5M** | **0.311** | **3.094** | **6.995** | **0.160** | — | — | — |

条件说明：

- “轻量档最佳”是在 Table 1 的对比范围内；正文明确说只有 Flex-Medium/Large 仍在其前面。
- 论文称 1.5M 参数匹配 4–22× 更大的模型；这是论文的 accuracy–efficiency 结论，不是绝对 SOTA。
- KITTI 640×192 下，论文称 Abs Rel 0.102 比 LEDepth 与 PuriLight 好 0.004；这两个 baseline 的值在表中分别是 0.106、0.106。
- Make3D 的 RMSE 6.995 高于 Flex-Small 的 6.865，但 Abs Rel/Sq Rel 更低；不要简单说“全面超过”。

### 5.4 消融关键数字

**SS 的模型规模泛化（Table 4，教师 Flex-Large）**：

| 模型 | w/o SS Abs Rel ↓ | w/ SS Abs Rel ↓ | w/o SS Sq Rel ↓ | w/ SS Sq Rel ↓ | w/o SS RMSE ↓ | w/ SS RMSE ↓ |
|---|---:|---:|---:|---:|---:|---:|
| Lite-Mono-tiny | 0.110 | 0.105 | 0.837 | 0.773 | 4.710 | 4.516 |
| Flex-Nano | 0.110 | 0.106 | 0.794 | 0.757 | 4.678 | 4.547 |
| Lite-Mono-8M | 0.101 | 0.100 | 0.729 | 0.696 | 4.454 | 4.356 |
| ReForgeDepth | 0.110 | 0.102 | 0.894 | 0.726 | 4.748 | 4.459 |

论文原文称：gain 从 Lite-Mono-tiny 的 0.005 Abs Rel 降到 Lite-Mono-8M 的 0.001；最小模型受益最大。

**教师选择（Table 6b，全 SS）**：

| Teacher | Abs Rel ↓ |
|---|---:|
| Depth Anything V3-Small | 0.114 |
| Lite-Mono-3.1M | 0.107 |
| Lite-Mono-8M | 0.104 |
| Flex-Large | 0.102 |

论文据此强调：教师质量与域对齐都重要；低冗余学生会放大教师噪声，跨域教师会引入 gap。

**KD 权重 schedule（Table 5，教师 Flex-Large）**：

| 配置 | Abs Rel ↓ |
|---|---:|
| \(\eta=0.1\)，无 warm-up，epoch 0 开始 | 0.104 |
| \(\eta=0.1\)，无 warm-up，epoch 5 开始 | 0.105 |
| \(\eta=0.1\)，warm-up，epoch 0 开始 | 0.102 |

## 6 · 能力与失败模式

### 6.1 能做

- **KITTI 640×192 轻量档精度**：1.5M 参数，Abs Rel 0.102、Sq Rel 0.726、RMSE 4.459、RMSE log 0.179；\(\delta&lt;1.25=0.891\)。
- **Cityscapes 动态城市场景**：1.5M 参数，Abs Rel 0.091、Sq Rel 0.918、RMSE 5.590；在 Table 1 轻量档中最低。
- **Make3D zero-shot**：KITTI 训练直接迁移，134 张测试图，Abs Rel 0.311、Sq Rel 3.094、RMSE 6.995。
- **端侧实时**：iPhone 12 29.80 ms / 34 FPS，M2 17.28 ms / 58 FPS；1.5M 参数、3.6G FLOPs。
- **SS 可迁移到其他轻量学生**：Lite-Mono-tiny、Flex-Nano、Lite-Mono、Lite-Mono-8M 上均有 Abs Rel 改善；模型越小收益越明显。
- **不增加推理负担**：教师只在训练期；SS 不引入额外参数、数据或推理开销。

### 6.2 不能做 / 失败模式

- **运动物体周围深度会退化**：结论明确写“photometric consistency degrades depth around moving objects”；auto-mask 能处理部分与相机同速的刚性物体，但不能解决独立运动。
- **没有 GT 深度，精度上限受限**：结论写“lack of ground-truth depth caps accuracy”；SS 只是更好地利用现有自监督信号，不是引入新监督。
- **弱纹理/遮挡/出视野仍依赖启发式**：min-reprojection 与 auto-mask 是必要补丁；在低纹理区域主要靠 smoothness 正则，容易过平滑。
- **教师域不匹配会伤害学生**：Table 6b 中 Depth Anything V3-Small 作教师为 0.114，Flex-Large 为 0.102；论文归因于跨域 gap 与低冗余学生对教师噪声的放大。
- **KD 不能随便全程满权重**：Table 5 中 \(\eta=0.1\) 无 warm-up 从 epoch 0 开始为 0.104，warm-up 后为 0.102；延迟到 epoch 5 为 0.105。
- **容量仍有上限**：正文说只有 Flex-Medium/Large 仍在 ReForgeDepth 前面；SS 不能把 1.5M 变成无上限模型。
- **动态场景只是“相对更好”**：Cityscapes 上 Abs Rel 0.091 是轻量档最佳，但论文没有声称完全解决运动物体。

### 隐含假设 (Hidden Assumptions)

1. **场景静态刚性 + Lambertian + 亮度恒定**：光度重投影的基本假设；非朗伯表面、反光、曝光变化会破坏。
2. **相机在运动且帧间有足够重叠**：静止相机、纯旋转、无穷远表面需要 auto-mask 兜底。
3. **auto-mask 能排除“与相机同速”的物体**：对独立运动物体不可靠；这是结论中承认的退化来源。
4. **内参 \(K\) 已知且帧间一致**：投影 warp 依赖标定；内参错误会直接把光度误差变成深度错误。
5. **逆深度只有 per-image scale 歧义**：median 归一化只消除尺度；若教师输出存在 shift/affine 或不同深度约定，Eq. 17 的对齐不够。
6. **教师与学生域匹配**：Flex-Large 是域匹配教师；换跨域教师会引入 gap，Table 6b 的 0.114 是证据。
7. **多尺度输出恰好是 full、1/2、1/4 三个尺度**：Eq. 19 的 \(k\in\&#123;0,1,2\&#125;\) 与 \(w_k=2^&#123;-k&#125;\) 是硬编码；改输出 stride 需重设权重。
8. **Phase III 的 \(e\) 从 0 计数，且 warm-up 必要**：\(\lambda_e=0.1\min(1,e/5)\)；直接常数权重或延迟开启都不是最优。
9. **端侧运行时支持 depthwise/pointwise、XCA、Sobel 等算子**：论文用 Apple Core ML Float32 测；换推理引擎需重新验证算子支持与延迟。
10. **训练数据是连续视频三元组**：单目视频假设；若只有离散图像，光度自监督不成立。

## 7 · 与相关工作对比

### 7.1 方法范式对比

| 方向 | 代表工作 | 核心做法 | 与 SS 的差异 |
|---|---|---|---|
| 轻量架构 | Lite-Mono、MViTDepth、R-MSFM、PuriLight、Flex-Nano、LEA-depth | 压编码器/解码器、混合 CNN-Transformer、特征净化 | 不改架构，改训练信号组织 |
| 传统蒸馏 | teacher–student distillation | 学生模仿教师输出，天花板由教师定 | SS 先让学生光度适应，再用 median 对齐的 log 相对深度渐进注入 |
| 自蒸馏 | self-distillation | 精炼模型自身预测 | SS 用域匹配外部教师，但强调学生可恢复容量 |
| 本文 | ReForgeDepth + SS | GMD + DCGI + RGB Boundary Residual；三阶段训练 | 不加参数/数据/推理开销，提升轻量档精度 |

### 7.2 关键数字对比

| 方法 | Params | KITTI Abs Rel ↓ | Cityscapes Abs Rel ↓ | iPhone 12 FPS ↑ | 备注 |
|---|---:|---:|---:|---:|---|
| Monodepth2 | 14.3M | 0.115 | 未报告 | 33 | 纯卷积，移动端优化好 |
| R-MSFM3 | 3.5M | 0.114 | 未报告 | 21 | 多尺度轻量 |
| Lite-Mono | 3.1M | 0.107 | 未报告 | 24 | 轻量 CNN |
| PuriLight | 2.7M | 0.106 | 0.099 | 16 | 频域操作在移动端支持差 |
| Flex-Nano | 1.5M | 0.110 | 0.107 | 未报告 | Flex 系列最小档 |
| **ReForgeDepth + SS** | **1.5M** | **0.102** | **0.091** | **34** | GMD + DCGI + BR + 三阶段 |

**面试 Tip**：如果被问“SS 是不是就是蒸馏？”，答：不是把教师输出当替换信号，而是训练课程——先让学生用光度自监督适应目标域，再用 median 对齐的 log 相对误差做渐进蒸馏；Table 6b 说明教师不是越强越好，域匹配的 Flex-Large 是 0.102，Depth Anything V3-Small 是 0.114。

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-17)

论文全文未出现作者仓库链接（页面顶部的 “Report GitHub Issue” 是 arXiv HTML 模板，不是作者 repo）。因此以下 pitfall 由 §6 失败模式 + 方法约束推导，**未经 issue 验证**；不写任何 repo URL、commit 或 issue 编号。

### Pitfall 1：动态物体周围的光度信号会把深度拉坏

- **触发条件**：Cityscapes 这类拥挤街道，或车载场景中有独立运动的车辆/行人。
- **机制**：\(\mathcal&#123;L&#125;_&#123;\text&#123;base&#125;&#125;\) 依赖光度重投影；auto-mask \(\mu\) 只能排除“与相机同速/静止/无穷远”等特定情况，独立运动物体不满足静态刚性假设。论文结论明确写 photometric consistency 在 moving objects 周围退化。
- **表现**：运动物体边界深度粘连、拖尾或过平滑；Cityscapes 上虽为轻量档最佳，但不等于解决动态物体。
- **规避**：按论文 future work 的方向加入 motion-aware masking；或在部署前用运动物体 segment 做评估切片。

### Pitfall 2：换教师时，median 归一化只对齐尺度，不对齐深度约定

- **触发条件**：把 Phase III 教师从 Flex-Large 换成跨域模型（如 Depth Anything V3-Small），或教师输出是 metric depth / 不同 relative depth 约定。
- **机制**：Eq. 17 只做 per-image median 归一化，Eq. 18 在 log 域比较；它假设学生与教师只差一个全局 scale。若存在 shift、affine 或不同深度定义，残差 \(r_k\) 会带系统偏差。Table 6b 中 Depth Anything V3-Small 为 0.114，Flex-Large 为 0.102；论文归因于教师质量与域对齐。
- **表现**：KD 越训越偏，轻量学生放大教师噪声；换教师后 Abs Rel 不一定改善。
- **规避**：优先域匹配教师；换教师前先检查深度约定（relative vs metric、disparity vs depth），必要时加 shift/affine 对齐，而不是只做 median。

### Pitfall 3：\(\lambda_e\) 不是常数，三尺度 KD 也是硬编码

- **触发条件**：复现时把 KD 权重设成固定 0.1，或延迟到 Phase III 第 5 epoch 才开启；或修改输出尺度数量。
- **机制**：Eq. 20 的 \(\lambda_e=0.1\min(1,e/5)\) 要求从 0 ramp；Table 5 中 \(\eta=0.1\) 无 warm-up 从 epoch 0 开始为 0.104，warm-up 后为 0.102，延迟到 epoch 5 为 0.105。Eq. 19 的 \(k\in\&#123;0,1,2\&#125;\) 与 \(w_k=2^&#123;-k&#125;\) 假设恰好三个尺度；改 stride 后权重索引不再成立。
- **表现**：训练早期教师信号压过光度信号，或后期欠拟合；改分辨率/尺度后 KD 权重错位。
- **规避**：保留 warm-up；若改输出尺度，重设 \(k\) 集合与 \(w_k\)；在消融中同时报告 w/o SS 与 w/ SS，不要只报最终值。

---

[← Back to depth README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2611.17828 -->"
