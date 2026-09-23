<!-- ontology-5axis
problem: depth
representation: n/a
sensor: multi-modal
paradigm: hybrid
time: fixed-lag
ref: ../../cheat-sheet/ontology.md §5
-->

# StreamTTO：面向视频深度补全的高效在线测试时优化 (StreamTTO: Efficient Online Test-Time Optimization for Video Depth Completion)

> **发布时间**：arXiv 2603.01765v5，2026-09-22（v5 时间戳）
> **论文 / 模型名**：StreamTTO（Multi-Scene Depth，MS-Depth benchmark 同期发布）
> **机构**：Korea Advanced Institute of Science and Technology (KAIST)
> **核心定位**：把"稀疏深度引导的 test-time optimization (TTO)"从**逐帧独立优化**改成**沿视频流累积的在线优化**——冻结因果特征提取器、缓存特征、复用同一个 decoder 及其 optimizer state，每帧只做 2 次窗口回传，在 MS-Depth 上以 15.73 FPS (VGGT) / 25.90 FPS (MoGe-2) 取得最低 RMSE。
> **Ontology 标注**：`problem=depth` · `representation=n/a` · `sensor=multi-modal` · `paradigm=hybrid` · `time=fixed-lag`

单目深度基础模型泛化好，但**不保证物理尺度**；稀疏 LiDAR 提供尺度锚点，却让 TTO 变成昂贵的逐帧迭代。StreamTTO 的结论是：**省的不只是"每步的算力"，更是"每帧需要多少步"**——一旦视觉计算和适配状态都能跨帧复用，2 步就能打平原来的 20 步。

---

## X-Ray 开场

它解决的是：**在持续变化的传感器/环境条件下，如何让深度基础模型在线对齐真实物理尺度，同时把 TTO 的算力压进一个连续感知系统的预算里**。做法是把时间建模和在线适配解耦——冻结的因果注意力编码器负责"看历史"（KV cache 一次算完，特征可复用），一个共享的 2D depth decoder 负责"吸收稀疏深度的纠正"，并用 Causal Sliding-Window Optimization (CSWO) 在 3 帧因果窗口上批量更新，参数与优化器状态一路带下去。对 spatial AI 研究者意味着：**TTO 的成本结构从"每帧步数 × 每步前反向"重写为"每帧固定 2 次窗口回传 + 0 次特征重算"**，并且"warm-start 后多优化反而变差"这一现象（Table 7）说明在线适配本质上是**约束累积问题**而非**拟合精度问题**。

---

## 📍 研究全景时间线

```
2018  Sparse-to-Dense ──────────── 学习 RGB-稀疏深度融合
2020  NLSPN ────────────────────── 非局部空间传播
2023  CompletionFormer ─────────── CNN+ViT 深度补全
2024  Depth Anything V2 ────────── 单目深度基础模型（尺度靠学，环境迁移不保）
2025  VGGT / π³ ────────────────── 多视图几何重建（不保证 metric）
2025  PromptDA / PriorDA ───────── 用稀疏/先验 prompt 条件化 DA
2025  Marigold-DC ──────────────── TTO：优化 diffusion latent + scale/shift
2025  TestPromptDC ─────────────── TTO：逐帧优化 visual prompt（50 updates，0.256 FPS）
2026  CAPA-LoRA ────────────────── TTO：只更新 encoder LoRA（默认 100 steps，0.780 FPS）
2026  StreamVGGT ───────────────── 因果注意力 + 缓存的在线几何重建
2026  ★ StreamTTO (本文) ───────── 冻结特征 + 共享 decoder + CSWO；同发 MS-Depth
                                   │
                                   ├─ 局限① 每帧仍需 decoder 反传 → 高分辨率下非实时
                                   ├─ 局限② 适配状态仅服务当前流（不跨序列迁移）
                                   ├─ 局限③ 无遗忘/多域保留目标（论文明确不以此为目标）
                                   └─ 局限④ 只测 518×392 / B200；无嵌入式部署证据
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练期 | 推理期（在线适配） |
|---|---|---|---|---|
| **Frozen spatiotemporal encoder** `F`（VGGT 或 MoGe-2 + 因果时序注意力） | `I_t` + KV memory `V_{t-1}` | `Z_t`, `V_t` | **冻结**；仅离线微调注意力组件使其支持 causal + KV cache | 冻结，每帧只跑一次 → 特征可缓存 |
| **KV cache** `V_{t-1}` | 历史帧 key/value | 过去视觉上下文 | — | 流式追加，6 帧因果上下文 |
| **Decoder-input feature cache** | `Z_j` | 可重复取用的特征 | — | 存最近 `W=3` 对 `(Z_j, S_j)`，CSWO 批量复用 |
| **Shared 2D depth decoder** `D(·;θ_t)` | `Z_t` | raw depth | 冻结（离线微调时 VGGT 冻结 encoder+decoder，MoGe-2 冻结两者） | **唯一被优化的模块**（32.655M 参数） |
| **Optimizer state** `O_t` | AdamW 状态 | — | — | **跨帧保留**（warm-start 的关键） |
| **Scale–shift aligner** `Align_{S_t}` | raw depth + `S_t` | `a*_t, b*_t` | — | 每次 loss 评估前最小二乘重算，`stop-gradient` |
| **CSWO buffer** `B_t` | `W=3` 帧 `(Z_j,S_j)` | 批量 loss | — | 当前帧权重 2、历史帧权重 1 |
| **MS-Depth** | RGB + LiDAR | 120 序列 / ~40h | 107 训练序列 | 13 测试序列（1 验证 TE04） |

**训练/推理差异的核心**：离线只做一件"结构性"的事——把预训练 backbone 改造成因果流式（VGGT：10 epochs、16×B200、约 1 天）；在线不做任何特征提取的重复计算，只更新 decoder。

### 1.2 关键机制

**⚡ Eureka Moment：把"时间建模"和"在线适配"拆开——特征提取器冻结后，缓存的特征在 decoder 优化的整个过程中保持有效；于是既能跨帧复用视觉计算，又能把 decoder+optimizer 状态当作一种"已积累的纠正"继承下来，使每帧所需优化步数从 20 塌缩到 2。**

两个必须一起看的设计推论：

1. **冻结是缓存有效性的前提**：论文在 Appendix D 形式上论证了 cached representation 与按同一因果策略重算的一致性——一旦 encoder 参与优化，缓存即刻失效（Table 3(b)：encoder-only 0.9306 m、FLOPs 149.538 T vs decoder-only 0.8694 m、7.028 T）。
2. **warm-start 让"优化步数"变成非单调量**：Table 3(d) 显示，warm-start 下步数从 2 增到 20 反而把 RMSE 从 0.8694 恶化到 0.9846 m；而 reset 下从 2 增到 20 才从 1.3725 改善到 0.8753 m。**"多优化 = 更准"这个直觉在状态可复用时失效。**

### 1.3 信息流

```
 I_t ──►┌─────────────────────────────────────────────────┐
        │ Frozen encoder F (spatial + causal temporal attn)│
        │   ↑ V_{t-1} (KV cache, 6-frame context)          │
        └───────────────┬─────────────────────────────────┘
                        │ Z_t   (每帧只算一次，之后可复用)
                        ▼
        ┌───────────────────────────────────────────┐
        │ Feature cache  B_t = {(Z_{t-2},S_{t-2}),   │   W = 3
        │                       (Z_{t-1},S_{t-1}),   │
        │                       (Z_t , S_t )}        │
        └───────────────┬───────────────────────────┘
                        │  batch 拼成一组
                        ▼
             ┌──────────────────────────┐
             │ Shared 2D decoder D(·;θ_t)│  ← 全框架唯一可训练部分
             └──────────┬───────────────┘
                        │ raw depth
        ┌───────────────▼──────────────────────────┐
        │ Align_{S_t}: 最小二乘拟合 a*, b* (stop-grad)│
        └───────────────┬──────────────────────────┘
                        │ aligned prediction
                        ▼
                 ρ-loss (L2 + λ|e|)  →  2 passes / AdamW
                        │
                        ├──► θ_{t+1}, O_{t+1}  （跨帧继承）
                        └──► D̂_t 输出该帧稠密深度
```

---

## 2 · 数学核心

📌 **Napkin Formula**

```
冻结 F 一次 → 缓存 Z；每帧只对 W=3 窗口做 R=2 次「对齐残差」回传：
ℒ = (1/|Ω|)Σ ρ(a*·D_θ(p) + b* − S(p))，  ρ(e) = e² + λ|e|，  权重 当前:历史 = 2:1
```

**目标**：用稀疏测量 `S_t` 在线监督一个共享 decoder，使输出在**未观测**位置也逼近真实 metric depth。

**① 特征提取（冻结，含因果时序）**

$$(Z_t,\ \mathcal{V}_t)=\mathcal{F}(I_t,\ \mathcal{V}_{t-1})$$

**② 输出与对齐**

$$\hat{D}_t=\operatorname{Align}_{S_t}\!\left[\mathcal{D}(Z_t;\theta_t)\right]$$

**③ 尺度-平移最小二乘（stop-gradient）**

$$(a_t^{\star},b_t^{\star})=\arg\min_{a,b}\sum_{p\in\Omega_t}\left(a\,\operatorname{sg}[D_t(\theta)(p)]+b-S_t(p)\right)^{2}$$

**④ 帧级稀疏损失**

$$\mathcal{L}_t^{\mathrm{sp}}(\theta)=\frac{1}{|\Omega_t|}\sum_{p\in\Omega_t}\rho\!\left(a_t^{\star}D_t(\theta)(p)+b_t^{\star}-S_t(p)\right),\qquad \rho(e)=e^{2}+\lambda|e|$$

**⑤ CSWO 批量损失（窗口归一化加权）**

$$\mathcal{L}^{\mathrm{CSWO}}=\frac{1}{2+(W-1)}\sum_{j\in\mathcal{B}_t} w_j\,\mathcal{L}_j^{\mathrm{sp}},\qquad w_{\text{current}}=2,\ w_{\text{past}}=1$$

**变量说明**

| 符号 | 含义 | 取值 |
|---|---|---|
| `Z_t` | 含过去视觉上下文的特征 | 缓存复用 |
| `V_{t-1}` | KV memory | 6 帧因果上下文 |
| `θ_t, O_t` | decoder 参数 + optimizer 状态（= adaptation memory `Ξ_t`） | 跨帧继承 |
| `Ω_t = dom(S_t)` | 稀疏观测有效位置 | 评价时**剔除** |
| `a*, b*` | 全局尺度与平移 | 每次 loss 前重算，反传时冻结 |
| `ρ(e)` | 伪 Huber（L2 + L1） | `λ = 0.1` |
| `W` | CSWO 窗口 | 3 |
| `R` | 每帧窗口 pass 数 | 2 |
| `K_boot` | 首帧 bootstrap 更新数 | 20 |
| lr / clip | AdamW | `3×10^{-5}` / 梯度全局 L2 范数裁剪 `1.0` |

**直觉**：`sg[·]` 让对齐求解器退化成一个"每帧自动标定的尺子"，梯度**只穿过被对齐后的预测回到 decoder**，因此适配能纠正**空间上变化的深度结构**，而不只是全局 scale/shift。`ρ` 的 L1 项对稀疏点上的离群残差（反光、边缘、动态物）更鲁棒。窗口把"当前帧"权重设为历史的 2 倍，是用 1 个超参在"吸收新观测"与"不丢弃近邻约束"之间做定点。

---

## 3 · 带数字走一遍（玩具设定，非论文数字）

**设定**：单参数 decoder，输出 `D(p) = θ`（3 个像素同值）；稀疏观测 `S = [1.0, 2.0, 4.0]`，即 `|Ω_t| = 3`；`λ = 0.1`；当前 `θ = 1.0`。

**Step 1 · 解对齐**

恒等输出下 `a` 与 `b` 只由 `a+b` 可辨识，取最小范数解：

$$a^\star=b^\star=\bar{S}/2=\frac{7/3}{2}=\frac{7}{6}\approx1.1667$$

对齐后预测恒为 `a*·θ + b* = 2.3333`。

**Step 2 · 残差与 ρ**

| p | S(p) | 对齐预测 | e | ρ(e)=e²+0.1\|e\| |
|---|---|---|---|---|
| 1 | 1.0 | 2.3333 | +1.3333 | 1.7778+0.1333 = **1.9111** |
| 2 | 2.0 | 2.3333 | +0.3333 | 0.1111+0.0333 = **0.1444** |
| 3 | 4.0 | 2.3333 | −1.6667 | 2.7778+0.1667 = **2.9444** |

`ℒ = (1.9111+0.1444+2.9444)/3 ≈ 1.6667`

**Step 3 · 梯度（对齐被 stop-gradient，`∂(a*θ+b*)/∂θ = a*`）**

$$\frac{\partial\mathcal{L}}{\partial\theta}=\frac{1}{3}\sum_i \underbrace{\left(2e_i+\lambda\,\mathrm{sign}(e_i)\right)}_{\rho'(e_i)}\cdot a^\star$$

| p | ρ'(e) | ρ'(e)·a* |
|---|---|---|
| 1 | 2.7667 | 3.2278 |
| 2 | 0.7667 | 0.8944 |
| 3 | −3.4333 | −4.0056 |

和 = 0.1167 → `∂ℒ/∂θ ≈ 0.03889` → `θ ← 1.0 − 3e-5×0.03889 ≈ 0.9999988`（学习率极小，单步几乎不动）。

**Step 4 · 三个可复述的机制结论**

1. **`|Ω| ≤ 2` 时对齐可以精确拟合** → 残差为 0 → **梯度塌缩**。极端稀疏下 TTO 空转（这解释了为什么 Sparse-depth 至少取 8 个 ring / 10% 像素）。
2. **亏损项（`λ|e|`）把第 3 点的极端残差从"平方主导"拉回线性** → 单个坏点不会炸掉整帧梯度。
3. **窗口滑动后 3 帧中 2 帧已被优化过**（`W−1 = 2`）→ 继承来的 θ 在新窗口上梯度已经在**近驻点**，这正是"2 步就够、20 步反而坏"的玩具版解释。

---

## 4 · 工程视角

**论文报告的硬件与吞吐**

| 项目 | 数值（逐字） | 条件 |
|---|---|---|
| GPU | **NVIDIA B200** | 全部实验 |
| FPS · MS-Depth | **15.73**（VGGT + StreamTTO）/ **25.90**（MoGe-2 + StreamTTO） | 518×392，含首帧 20 次 bootstrap |
| FPS · 五个公开 benchmark 平均 | **7.14**（VGGT）/ **11.99**（MoGe-2） | 各数据集原生分辨率（KITTI `1216×352`、DDAD `1936×1216`） |
| 输入分辨率对 FPS 的影响 | 公开 benchmark 更高分辨率 → 平均 FPS 低于 MS-Depth | Appendix A.2 |
| 相对吞吐 | MoGe-2 变体 ≈ **54× / 47× / 15×** 于 Marigold-DC / TestPromptDC / offline CAPA-LoRA（§5.2）；Appendix A.1 写 **47.7× / 60.8× / 15.7×**（顺序为 TestPromptDC / Marigold-DC / CAPA-LoRA） | ⚠️ 正文与附录口径不一致（见 §8） |
| 训练 FLOPs/帧（默认配置） | **7.028 T** | 518×392，含特征提取 + 适配 |
| 窗口/上下文 FLOPs 对照 | W=1: 4.320 T；W=3: 7.028 T；W=6: 11.091 T；W=12: 19.217 T；KV=1: 6.496 T；KV=12: 7.668 T | 同上 |
| decoder-only 训练 FLOPs（transition 实验） | **4.063 T/帧**（W1 与 W3 匹配，不含冻结特征提取） | Table 4 |
| 参数量 | decoder **32.655 M**；encoder-only 304.372 M；full 337.026 M；encoder-LoRA 0.393 M；decoder-LoRA 0.357 M；full-LoRA 0.750 M | Table 3(b)(c) |
| 离线微调成本 | VGGT 变体 10 epochs，16×B200 约 **1 天**（L=24 层，FlashAttention-2，从 VGGT-1B checkpoint 起） | Appendix A.2 |
| 单帧延迟 | **论文未报告** | 只给 FPS 聚合 |
| VRAM / 显存占用 | **论文未报告** | — |
| CPU / 嵌入式（Jetson 类）结果 | **论文未报告** | 只在 B200 上验证 |

**Trade-off 结构（可直接用于面试表述）**

- **复用维度一：每步成本**。decoder-only 7.028 T vs encoder-only 149.538 T（**≈21×**）→ 冻结特征提取是"每步成本"那一刀。
- **复用维度二：每帧步数**。warm-start R=2 达到 reset R=20 的精度（0.8694 vs 0.8753 m），**每帧优化更新数少 10 倍**（Appendix A.1）。
- **精度-算力曲线在中段见底**。W: 1→3 改善，3→6 再改善 1.6% 但 FLOPs +57.8%，6→12 反而恶化；R 在 warm-start 下超过最优值后单调变差。
- **部署硬约束**：适配阶段**必须在推理时做反向传播与参数更新**（论文明确 "performing backpropagation and parameter updates"）。这意味着只支持前向的部署栈（典型 INT8 推理引擎、纯推理加速器）**无法直接承载该适配步骤**；论文没有给出任何量化/蒸馏/前向替代方案。
- **分辨率即预算**：518×392 才有 15.73/25.90 FPS；DDAD `1936×1216` 拉低平均 FPS——论文未报告该分辨率下的单数据集 FPS。

---

## 5 · 数据与评测

### 5.1 MS-Depth（本文同期发布的 benchmark）

| 项目 | 论文原文数值 |
|---|---|
| 全称 | MS-Depth (Multi-Scene Depth) |
| 规模 | 120 个约 20 分钟序列，共 **约 40 小时**，**约 1.45M** 同步 RGB–LiDAR 帧 |
| 划分 | 训练 **107** 序列 / 测试 **13** 序列；测试覆盖 **8** 个地点/路线 |
| 平台 | 手持刚体平台；**Ouster OS-1-128-SR** 128 线 LiDAR @ **10 Hz**；三台 **Point Grey Research Blackfly BFLY-PGE-31S4C** 相机 |
| 相机 | 中心相机 **2048×1536** RGB；另两台构成 **20 cm** 基线立体对；触发板硬件同步 |
| 标定 | 图像平面标定误差 **至多 0.9 像素** |
| 参考深度构造 | 单帧 LiDAR scan 投影（**不做多帧累积**）；用 RoMa v2 三角化立体深度做过滤：丢弃无匹配、左右一致性误差 > **1 像素**、与 LiDAR 深度差 > **10%** 的样本 |
| 稀疏输入 | 保留 **8 个 LiDAR ring**（固定 ring-index 间隔） |
| 场景 | 测试序列持续穿越室内/室外并回到起点；其中 **9** 个含 underground 段；含昼夜标签与室内/室外/地下时序标注 |
| 隐私 | 排除移动行人；人脸与车牌模糊 |
| 开发/测试隔离 | **TE04** 为验证序列（超参选择、消融）；其余 **12** 个测试序列用于报告，不参与调参 |

### 5.2 公开 benchmark 评测子集（逐字）

| 数据集 | 分辨率 | 子集规模 |
|---|---|---|
| KITTI | `1216×352` | 8 个序列的 110 帧 clip → **880** 帧 |
| Bonn RGB-D Dynamic | — | 5 个序列 → **550** 帧 |
| NYUv2 Raw | `640×480` | 8 个序列 → **880** 帧 |
| TUM RGB-D | `640×480` | 8 个序列 → **880** 帧 |
| DDAD | `1936×1216` | 官方 validation split 全部 **50** 场景的 **3,950** 前视帧 |

**稀疏深度输入构造（关键条件）**：KITTI / DDAD / MS-Depth = 投影**至少 8 个 LiDAR ring**（序列内固定选择）；Bonn / NYUv2 Raw / TUM RGB-D = 均匀采样**有效参考深度像素的 10%**（不放回）。所有需要稀疏深度的方法接收**完全相同**的观测；评测**只在剩余的有效参考像素上**进行（即剔除输入观测点）。

### 5.3 主要结果（逐字复制）

**Table 1 · 五个公开 benchmark（RMSE / MAE，米）**

| 方法 | KITTI | Bonn | NYUv2 Raw | TUM RGB-D | DDAD | Avg. FPS |
|---|---|---|---|---|---|---|
| VGGT + Causal-Attn | 3.0817 / 1.3334 | 0.1723 / 0.0792 | 0.1602 / 0.0832 | 0.2150 / 0.0988 | 12.7059 / 6.6541 | 17.52 |
| TestPromptDC | 1.1266 / 0.3441 | 0.0514 / 0.0190 | 0.0495 / 0.0229 | 0.0514 / 0.0163 | 8.2693 / 2.2167 | 0.256 |
| CAPA-LoRA (offline) | 1.0902 / 0.2684 | 0.0566 / 0.0179 | 0.0546 / 0.0219 | 0.0560 / 0.0144 | 7.6213 / 1.7592 | 0.780 |
| OMNI-DC v1.1 | 1.3557 / 0.4219 | 0.0700 / 0.0146 | 0.0526 / 0.0147 | 0.0563 / 0.0113 | 7.6406 / 1.7980 | 9.07 |
| **VGGT + StreamTTO** | 1.0223 / 0.3920 | 0.0592 / 0.0210 | 0.0403 / 0.0220 | 0.0738 / 0.0274 | 7.1448 / 2.3483 | 7.14 |
| **MoGe-2 + StreamTTO** | **0.7796** / 0.2763 | **0.0430** / 0.0155 | **0.0316** / 0.0173 | 0.0586 / 0.0195 | **5.2864** / 1.7124 | 11.99 |

论文陈述的排名条件：MoGe-2 变体在 KITTI、Bonn、NYUv2 Raw、DDAD 上取得最低 RMSE；**TUM RGB-D 的 RMSE 由 TestPromptDC 领先（0.0514）**；OMNI-DC 在三个室内 benchmark 上取得最低 MAE。

**Table 2 · MS-Depth 12 个测试序列（RMSE / MAE，米）**

| 条件 | VGGT + StreamTTO | MoGe-2 + StreamTTO | FPS（对应行） |
|---|---|---|---|
| Indoor Underground | 0.8077 / 0.2610 | **0.5899** / 0.2063 | 15.73 / 25.90 |
| Outdoor Aboveground | 1.0728 / 0.2211 | **0.8339** / 0.1647 | 同上 |
| Day | 1.3666 / 0.3668 | **0.9950** / 0.2779 | 同上 |
| Night | 1.2603 / 0.3497 | **0.8846** / 0.2558 | 同上 |

**关键评测发现（论文自己的话）**：TestPromptDC 在 5 个公开 benchmark 中的 4 个上 RMSE 优于 OMNI-DC，但在 MS-Depth 的**全部四个条件上排名反转**——**公开 benchmark 的排名不迁移到连续环境变化场景**。

**消融（Table 3，VGGT backbone，MS-Depth TE04，10 seeds 均值）**

| 配置 | RMSE (m) | FLOPs (T/frame) |
|---|---|---|
| 单帧上下文 / reset | 1.4213 | 6.496 |
| 6 帧重算 / warm-start | 0.8718 ± 0.0401 | 20.727 |
| 6 帧因果 KV / reset | 1.3725 ± 0.0189 | 7.028 |
| **6 帧因果 KV / warm-start（默认）** | **0.8694 ± 0.0532** | **7.028** |
| 适配目标 = encoder | 0.9306 ± 0.0287 | 149.538 |
| 适配目标 = decoder（默认） | 0.8694 ± 0.0532 | 7.028 |
| 适配目标 = full | 0.9271 ± 0.0492 | 150.892 |
| decoder-LoRA | 0.9205 ± 0.0536 | 5.719 |
| full-LoRA | 0.8706 ± 0.0271 | 145.885 |
| reset / 20 passes | 0.8753 ± 0.0526 | 43.595 |
| warm-start / 20 passes | 0.9846 ± 0.0232 | 43.595 |
| W=1 / W=3 / W=6 / W=12 | 0.9314 / 0.8694 / 0.8551 / 0.9544 | 4.320 / 7.028 / 11.091 / 19.217 |
| KV=1 / 3 / 6 / 12 | 1.1333 / 0.8918 / 0.8694 / 0.8697 | 6.496 / 6.709 / 7.028 / 7.668 |
| K_boot = 20 / 40 / 60 / 100 | 0.8694 / 0.8727 / 0.8749 / 0.8684 | 论文未报告 |

**其他报告结果**：Table 4（51 个 transition clip）W1 1.2146 m / 10.5 FPS vs W3 1.1340 m / 15.7 FPS（FLOPs 匹配 4.063 T）；Table 7 诊断：W=3 时 R 从 2 增至 20，**observed RMSE 0.8162→0.2623，unobserved RMSE 0.8696→0.9773**；Table 9（长时）：连续 warm-start 整体 1.09 m vs 周期 reset 1.19 m / reset+bootstrap 1.11 m；Table 12（NYUv2 降密度）：VGGT+StreamTTO 在 3% 时 0.0541 m、1% 时 0.0593 m（1% 下比次优 TestPromptDC 的 0.0679 m 低 12.7%）；Appendix A.9：warm-start 使 TestPromptDC 平均 RMSE 改善 2.50%、CAPA-LoRA 改善 5.72%；完整框架相对无 TTO 的因果 backbone 平均 RMSE 降低 **63.35%**。

---

## 6 · 能力与失败模式

### 能做

- **无训练数据的在线尺度对齐**：只用目标域稀疏深度监督，不依赖训练分布覆盖（Table 1 中在 5 个公开 benchmark 上与专用深度补全模型互有胜负，且在 KITTI/Bonn/NYUv2/DDAD 取得最低 RMSE）。
- **持续环境过渡下的长时稳定性**：40 小时量级、跨 indoor/outdoor/underground、昼夜变化的连续流上保持精度；Table 8 显示全流 warm-start 在过渡后 `[0,1)s` 就已优于局部重置（1.24 vs 1.26），并持续到 `[3,10)s`（1.07 vs 1.11）。
- **稀疏密度退化下相对优势增强**：NYUv2 从 3% 降到 1%（观测减少 66.7%），StreamTTO RMSE 仅上升 9.6%（0.0541→0.0593），而 TestPromptDC 上升 25.5%、OMNI-DC 上升 32.9%。
- **吞吐数量级提升**：相对 Marigold-DC / TestPromptDC / offline CAPA-LoRA 的数十倍级加速（数量级确凿；具体倍数见 §8 的口径不一致提示）。

### 不能做 / 已证明的失败模式

| 失败模式 | 论文证据 |
|---|---|
| **多优化步数反而恶化未观测位置** | Table 7：W=3 时 R 2→20，observed 0.8162→0.2623（拟合更好），unobserved 0.8696→0.9773（泛化更差） |
| **大窗口因"当前帧权重稀释"退化** | W=12 在 R=2 下 RMSE 0.9544，差于 W=3 的 0.8694；把当前帧权重提到 5.5 可恢复 93.2% 的差距，但**不省算力**（W3→W12 在 R=2 下 FLOPs 7.028→19.217 T，≈2.73×） |
| **在 TUM RGB-D 上不是最优** | TestPromptDC RMSE 0.0514 < MoGe-2+StreamTTO 0.0586 |
| **室内 MAE 不是最优** | OMNI-DC 在三个室内 benchmark 上取得最低 MAE |
| **公开 benchmark 排名不可外推** | 论文自陈：TestPromptDC > OMNI-DC 的排名在 MS-Depth 全部四个条件上反转 |
| **超长流上有轻微漂移** | Table 9：连续 warm-start 在 `10–15 min` 为 1.05 m，`≥15 min` 升到 1.11 m |
| **无遗忘/多域保留保证** | 论文明确："Preserving performance on earlier environments is not an explicit objective"；适配状态**不跨序列迁移** |
| **因果时序注意力不可省** | CSWO-only 变体在每个公开 benchmark 和每个 MS-Depth 条件上都差于完整框架（如 MS-Depth indoor underground：VGGT+CSWO 1.1234 vs VGGT+StreamTTO 0.8077） |
| **只能用稀疏深度监督** | 目标函数只定义在 `Ω_t` 上；论文未引入光度/几何一致性项来约束未观测区域 |

### 隐含假设 (Hidden Assumptions)

1. **每帧都有可用、已配准的稀疏 metric depth `S_t`**。`Ω_t = dom(S_t)` 为空时损失无定义（除以 `|Ω_t|`）。论文只测到 1% 均匀采样密度，**未测零观测场景**（LiDAR 掉线、纯视觉区段）。
2. **单帧误差主要由全局 affine（scale+shift）项 + decoder 可学到的空间残差构成**。`Align_{S_t}` 只解 2 个自由度；若 backbone 误差的主体不是仿射型（例如整体几何结构错、卷帘/畸变未建模），对齐会把这个误差"扣"进去而 loss 看起来不大——Table 7 中 observed RMSE 0.2623 与 unobserved 0.9773 的巨大落差就是这种风险的实证。
3. **冻结的 encoder 特征对当前传感器/环境仍足够有信息量**。适配被限制在 decoder（Table 3(b) 证明这是最优选择：0.8694 vs encoder 0.9306），但这也意味着**误差若源于表征本身，decoder 补救不了**。
4. **`|Ω_t|` 足够大（≥3）使最小二乘残差非零**。`|Ω| ≤ 2` 时 `(a,b)` 两个自由度可精确拟合两点，残差归零、梯度塌缩——这约束了可用的稀疏密度下界。
5. **场景主导静态 + 参考深度是单帧投影**。MS-Depth "Recordings exclude moving pedestrians"，参考深度由**单帧 LiDAR scan 投影**生成（不做多帧累积），并靠立体一致性剔除动态/遮挡不一致样本；因此**动态物体、快速运动、卷帘快门**下的参考真值本身不可靠。
6. **可缓存的因果表示**。Appendix D 的一致性/梯度有界性论证是**有条件的**（"当上一窗口梯度小、且相关逐帧梯度变化小"），且依赖**固定的因果执行策略**与冻结的 extractor；改变执行顺序或让 encoder 参与优化即破坏前提。
7. **离线因果化改造是前置条件**，而非可选优化：VGGT 需要先按 StreamVGGT 的方式做因果微调（10 epochs / 16×B200 / 约 1 天）；MoGe-2 需要在 encoder 与 decoder 之间**新插入** 3 层空间 + 3 层因果时序注意力（8 heads）。直接用公开预训练权重跑不出报告的行为。
8. **"精度"的定义剔除了观测点**。所有 RMSE/MAE 都在**剩余有效参考像素**上计算；在 LiDAR 命中点上的误差不被度量。
9. **单流、单传感器会话假设**。decoder 与 optimizer 状态"只服务当前流"，任何流切换/重连都要重新付 `K_boot = 20` 的 bootstrap 成本。

---

## 7 · 与相关工作对比

| 维度 | Marigold-DC | TestPromptDC | CAPA-LoRA | **StreamTTO** |
|---|---|---|---|---|
| 优化对象 | diffusion latent + scale/shift | 输入 visual prompt（3 通道，逐帧从 0 起） | image encoder 的 LoRA adapter | **共享 2D depth decoder（full）** |
| 时序性 | 逐帧独立 | 逐帧独立，50 updates | 默认 100 steps（离线 clip 级协议） | **因果在线，跨帧继承 θ 与 optimizer state** |
| 特征重算 | 每次更新都前反向穿过全网络 | 每次更新都前反向 | 重复 encoder 特征计算 + 反传 | **冻结 extractor，特征缓存复用；0 次重算** |
| 每帧优化步数 | 迭代式 | 50 | 100（默认） | **R = 2**（首帧 `K_boot = 20`） |
| 时序上下文 | 无 | 无 | 无 | **6 帧 causal KV** |
| 辅助监督模型 | 需训练好的引导（diffusion 先验） | 无 | 无 | **无**（直接用目标域稀疏深度） |
| 同 backbone 对照 | — | VGGT 基线 FPS 0.201；MoGe-2 基线 FPS 0.102 | offline 协议，FPS 0.780 / 1.652 | **VGGT 7.14 / MoGe-2 11.99（公开 benchmark 平均）** |
| 相对 backbone 的 RMSE 降幅 | — | — | — | **平均 63.35%**（完整框架 vs 因果 backbone） |
| 是否跨流保留适配 | — | 否 | 否（离线 clip 级） | **否（论文明确不迁移）** |
| 是否以抗遗忘为目标 | — | — | — | **否（论文明确不以此为目标）** |

与其他路线的定位差异：
- **vs 训练式深度补全（NLSPN / CompletionFormer / OMNI-DC / PriorDA）**：StreamTTO 推理时改参数，因而不受训练数据覆盖限制；但 OMNI-DC 在室内 MAE 上仍更优，且 OMNI-DC 参数固定却只有 9.07 FPS（公开 benchmark 平均），**被 MoGe-2 + StreamTTO 的 11.99 FPS 反超**——这是论文最反直觉的效率结论之一。
- **vs StreamVGGT**：同属"因果 + 缓存"的流式几何，但 StreamVGGT 只做重建、不保证 metric；StreamTTO 借用其因果微调配方 + 引入稀疏深度监督。
- **vs Continual depth completion（UnCLe / ProtoDepth）**：那些工作强调**跨域保留**；StreamTTO 明确把目标定为**当前流当前环境**的精度，换来极低的每帧更新预算。

**面试 Tip（被问到"StreamTTO 和 TestPromptDC / CAPA-LoRA 最本质的区别是什么"）**：
> 不要答"它更快"。答：**它改变了 TTO 的成本结构。** TestPromptDC/CAPA-LoRA 是"每帧从零重启的独立优化"，成本 = 每帧步数 × 每步全网络前反向；StreamTTO 冻结特征提取器让每步成本塌到只穿 decoder（7.028 T vs 149.538 T），再把 decoder+optimizer 当作状态跨帧继承，让每帧步数从 20 降到 2——而且论文用 Table 3(d) 证明这两者是**耦合**的：一旦状态能继承，"多优化"从帮助变成伤害（warm-start R=20 → 0.9846 m，R=2 → 0.8694 m）。所以我更愿意把它描述为**"把 TTO 从拟合问题重构成约束累积问题"**。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-23)

**诚实声明**：本论文正文与附录**未给出 StreamTTO 自身代码仓库的链接**；论文仅在 Appendix A.7 以纯文本形式引用了 baseline 的地址 `https://github.com/JinhwiPark/TestPromptDC/blob/main/main.py`（非本文方法、非可点击超链接形式），并声明 "Code and data will be released... upon acceptance"（Conclusion）与 "We will publicly release the source code and the full MS-Depth dataset upon acceptance"（Reproducibility Statement）。因此**当前无官方 repo、无 issue 流可供验证**。以下 4 条 pitfall 由 §6 的失败模式 + 本文方法的具体约束**推导**得出，**未经 issue 验证**。

### Pitfall 1 · 把 `R`（每帧 pass 数）或学习率调大，会在观测点上"看起来更好"、在未观测点上显著变差 —— 而在线部署拿不到未观测点的真值来早停

- **机制来源**（失败模式）：Table 7，W=3 时 R 从 2→20，observed RMSE 0.8162→0.2623，unobserved RMSE 0.8696→0.9773。
- **方法约束**：损失 `ℒ_t^sp` **只定义在 `Ω_t` 上**（Eq. 4），没有任何光度/几何一致性项约束未观测区域；`Align` 的 `sg[·]` 又让 scale/shift 每帧自适应吸收全局误差。
- **工程后果**：任何基于"稀疏点残差"做的在线监控/早停/学习率调度都会**朝反方向优化**。论文自己给出的部分缓解是降低常数学习率（unobserved 0.9321）或重置 decoder+optimizer（0.9603），但都**不能恢复到 R=2 的 0.8696**。

### Pitfall 2 · 调大 CSWO 窗口 `W` 不但更贵，还可能更差；根因是硬编码的 `2:1` 权重随 `W` 稀释当前帧

- **机制来源**（失败模式）：W=12, R=2 → RMSE 0.9544，差于 W=3 的 0.8694；Table 7 中把当前帧权重提到 5.5（使系数从 `1/12` 变回 `1/3`）把 unobserved RMSE 从 0.9251 拉回 0.8734，恢复约 93.2% 的差距。
- **方法约束**：Eq. ⑤ 的权重是 `w_current = 2, w_past = 1`，（§5.4/Appendix A.4）明确当前帧在全窗口中的归一化系数是 `2/(W+1)`。也就是说 **`W` 与"当前帧有效学习率"是隐式耦合的两个旋钮**——想扩窗口保住长时上下文，就必须同时改权重，而论文的 reweight 方案**不减 FLOPs**（W3→W12 仍是 7.028→19.217 T，≈2.73×）。
- **工程后果**："把 `W` 从 3 调到 6 换 1.6% 精度，代价是每帧 FLOPs +57.8%"（Table 3(e)）是最容易被误当成免费午餐的地方。

### Pitfall 3 · 适配阶段要求**推理时反传**，且默认配置未在 B200 之外的硬件上验证

- **机制来源**（方法约束）：论文明确 "Despite performing backpropagation and parameter updates..."（§5.2），每帧执行 `R=2` 次窗口回传 + AdamW 更新，梯度全局 L2 裁剪 1.0；首个序列帧还要 `K_boot = 20` 次更新。全部 runtime 在 **NVIDIA B200** 上测量，FPS 计算还**包含**首帧 20 次 bootstrap。
- **工程后果**：(a) 只支持前向推理的部署栈（典型 INT8 推理加速器、纯前向引擎）**无法承载适配步骤**；(b) 首个序列帧的 20 次 bootstrap 是冷启动延迟，任何流重启/相机切换都要重付；(c) 论文未报告 VRAM、单帧延迟、CPU 或嵌入式平台结果——**任何"能上机器人"的性能声明都超出论文证据范围**，标 `UNVERIFIED`。

### Pitfall 4 · "零观测帧"会让损失无定义，且论文的鲁棒性只下探到 1% 均匀采样

- **机制来源**（方法约束）：`ℒ_t^sp` 含 `1/|Ω_t|` 归一化（Eq. 4），`Ω_t = dom(S_t)` 为空则未定义；对齐最小二乘同样需要 `Ω_t` 非空。
- **机制来源**（失败模式 + 隐含假设）：论文的密度消融仅在 **NYUv2 Raw** 上测到 3% 与 1%（Table 12），且是**均匀采样**而非"LiDAR ring 部分缺失"；MS-Depth/KITTI/DDAD 用的都是"至少 8 个 ring"。论文未验证 ring 选择性丢失、LiDAR 短时掉线、极端远距无回波等真实失效模式。
- **工程后果**：实车/机器人上 LiDAR 掉帧或进入全反射区时，必须自己加一层 fallback（跳过适配 / 复用上一次 `θ` / 退回 backbone + 对齐），论文不给方案。

### 附加：可复现性口径不一致（在论文文本内部，非推测）

- 吞吐倍数：正文 §5.2 写 MoGe-2 变体达到 Marigold-DC / TestPromptDC / offline CAPA-LoRA 的 **约 54× / 47× / 15×**；Appendix A.1 写 TestPromptDC / Marigold-DC / CAPA-LoRA 的 **47.7× / 60.8× / 15.7×**。两组数字（同一组对比对象）互相矛盾，**复现时不要引用具体倍数，只引用绝对 FPS（15.73 / 25.90）**。

---

[← Back to depth-completion README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（2603.01765v5）· §4 中"单帧延迟 / VRAM / 嵌入式平台表现"论文未报告，未做任何估算 · §8 无官方 repo，pitfall 均由 §6 失败模式 + 方法约束推导，**未经 issue 验证** · 论文正文与附录的吞吐倍数口径不一致已在 §8 标注

<!-- source: https://arxiv.org/abs/2603.01765 -->
