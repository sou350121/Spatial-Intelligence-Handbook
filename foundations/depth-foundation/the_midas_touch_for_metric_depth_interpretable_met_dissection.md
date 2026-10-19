[//]: # "<!-- ontology-5axis
problem: depth
representation: n/a
sensor: mono
paradigm: hybrid
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 把相对深度“点石成金”为度量深度：可解释度量化的泛化深度感知 (The Midas Touch for Metric Depth: Interpretable Metricization for Generalizable Depth Perception)

> **发布时间**：2026-10-12（arXiv:2610.16749v1）
> **论文 / 模型名**：**MTDv2**（Midas Touch for Depth V2；前作为 MTD, CVPR 2026）
> **核心定位**：把"显式可解释的度量化解"与"数据驱动残差修正"拼成一个混合框架——不需要任务专用训练就能从稀疏度量观测恢复稠密度量深度，且比纯学习的 depth completion 更抗稀疏、更抗跨域。

相对深度基础模型（Depth Anything V2、MiDaS）已经把 zero-shot 几何先验做得很好，但它们输出的深度没有绝对尺度，且**同一张图内不同区域的"相对→度量"关系并不共享同一组仿射参数**。MTDv2 的结论：用 segment-wise 仿射 + 图传播 + 测地线动态规划把 scale 显式解掉，再让网络只学残差——于是它可以在**伪标签**上训练，并在 16 个公开数据集上做到 zero-shot 深度补全的 SoTA。

---

## X-Ray 开场

单目相对深度模型给出的深度图，几何结构对但尺度错，且误差不是"全局一次性缩放"能修掉的：近处桌面和远处墙面各自需要不同的 affine 参数。MTDv2 提出的做法是：先把图像切成**同时纹理与相对深度一致**的 superpixel，在含稀疏观测的 segment 上独立最小二乘拟合 $(a,b)$，用**二部稀疏图**把参数传播到没有观测的 segment；再用**测地线动态规划**沿"累积二阶曲率最小"的路径把观测深度传播到每个像素；最后用一个 geometry-guided propagation head 把这条单路径传播改写成**可学习的多路径软传播**，只学残差。

对 spatial AI 研究者意味着：**metric scale 不一定要靠"学"，它可以被"解"出来**；网络该负责的是薄结构、边界、非仿射畸变这类显式模型表达不了的部分。这条"显式解 + 学残差"的配方可以直接搬到 depth completion、NVS 初始化、VO 的深度输入上。

---

## 📍 研究全景时间线

```
2019  MiDaS ────────────────► 相对深度 + affine-invariant loss 成为范式
2024  Depth Anything / V2 ──► zero-shot 相对深度泛化大幅提升
2024  Marigold ─────────────► 扩散先验进深度，细节好但贵
2025  Marigold-DC ──────────► 把稀疏观测塞进扩散深度补全（本表最强 baseline 之一）
2025  OMNI-DC / DMD3C ──────► 大规模合成稀疏观测训练，强调泛化
2026  MTD (CVPR) ───────────► 训练-free 显式度量化：segment 仿射 + 图传播 + DP 精修 ◄── 前作
2026  MTDv2 (本文, 10月) ───► 混合：显式度量化做初值/稠密几何先验 + 网络学残差多路径传播
未来  ?  ───────────────────► 论文自述：更轻量的共享 backbone、在线无靶标外参标定、
                              相对深度失效场景（弱光）的域适应
```

**本文在演进中的位置**：它是"相对深度 → 度量深度"这条支线上第一个把**显式优化与可学习精修统一在同一套测地线/传播语言下**的工作。局限（论文 §IV-I 自述）：推理成本高（两个独立 backbone + CPU-only superpixel + 传播头开销）、相对深度本身错时不纠错、依赖精确相机-雷达外参。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 |
|---|---|---|---|
| 几何感知 superpixel 分割 | RGB + 相对深度 $z_{\mathrm{rel}}$（作为额外几何线索） | $N$ 个局部 segment $\{\mathcal{S}_i\}$ | 训练/推理一致，**无参数**，CPU 执行 |
| Segment-wise 仿射拟合（Eq.1） | $\mathcal{S}_i$ 内 $z_{\mathrm{rel}}$ 与稀疏观测 $o$、掩码 $m$ | $\hat{\boldsymbol\theta}_i=(\hat a_i,\hat b_i)$，仅对"合格 segment" $\mathcal{Q}$ | 闭式最小二乘，**训练-free** |
| 稀疏二部图参数传播（Eq.2–3） | 合格 segment 参数 + segment 质心 | 不合格 segment 的 $\hat{\boldsymbol\theta}_j$ | 训练-free，$K$ 近邻 + 指数距离衰减 |
| 显式像素级精修（Eq.4–11） | 粗度量深度 + 观测锚点 | $z_{\mathrm{opt}}$（单路径 DP，最多 3 步） | 训练-free，纯几何 |
| 双流特征提取 | RGB → 纹理流；$z_{\mathrm{opt}}$ + 稀疏观测 + 有效掩码 → 几何流 | 融合特征 | **需要训练**（伪标签监督） |
| Geometry-guided propagation head | 融合特征 | 残差 $r_z$、残差 $r_\phi$、传播 logit $\gamma$、锚定置信 $c$ | 需要训练 |
| 多路径软传播 + 锚定（Eq.12–16） | 上述四类输出 | $z_{\mathrm{hybrid}}$（最终度量深度） | 迭代 $t$ 步，推理时同样执行 |

关键点：**前四个模块零训练、完全可解释；只有后三个模块有参数**。这是全文最值钱的结构性设计。

### 1.2 关键机制

**⚡ Eureka Moment**：一阶曲面近似从 $\boldsymbol{q}$ 推 $\boldsymbol{p}$ 的残差 $R(\boldsymbol{p},\boldsymbol{q})$ 是**反对称**的，其幅值被沿路径累积的二阶量 $\phi=\sqrt{z_{uu}^2+z_{vv}^2}$ 从上方界定——所以"哪条路径传播最可靠"这个工程直觉，可以严格写成一个**测地线最小代价路径**问题，进而用 dynamic programming 精确求解；而同一个代价函数可以原地替换成 softmax 亲和度 + 可学习 logit，让网络做**多路径软传播**，既保留可解释性又超越单路径。

### 1.3 信息流 ASCII 图

```
 RGB ─┬────────────────────────────────────────────► [纹理流 encoder] ──┐
      │                                                                 │
      │  z_rel (DAv2 ViT-L)                                             ├─► 融合 ─► propagation head
      ├──► [几何感知 superpixel 分割] ─┐                                 │        │  ├─ r_z  深度残差
      │                               ▼                                 │        │  ├─ r_φ  不连续密度残差
      │                    [segment-wise 仿射 LSF] ──► θ̂_i (i∈Q)        │        │  ├─ γ    传播 logit
      │                               │                                 │        │  └─ c    锚定置信
      │                    [稀疏二部图传播]    ──► θ̂_j (j∉Q)            │        │
      │                               ▼                                 │        ▼
      │                    粗度量深度 ──► [测地线 DP 精修] ──► z_opt ────┘   [多路径软传播 Eq.15]
      │                                        ▲                              │
      └─ 稀疏观测 o, 掩码 m ──────────────────┴──────────────────────────────┴─► [锚定 Eq.16] ─► z_hybrid
```

显式分支（上半 §III-B/III-C）产出 $z_{\mathrm{opt}}$，它同时扮演三个角色：**网络初值**、**稠密几何先验输入**、**伪标签监督的参照系**。

---

## 2 · 数学核心

📌 **Napkin Formula**

$$z_{\text{metric}}\big|_{\mathcal{S}_i}=a_i\,z_{\mathrm{rel}}+b_i,\qquad \text{路径选择}=\arg\min_{\Pi}\sum_k \ell_k\,\phi(\boldsymbol{p}^{(k)}),\qquad \phi=\sqrt{z_{uu}^2+z_{vv}^2}$$

一句话：**尺度按 segment 分段解，深度沿"曲率最小"路径传，网络只补残差。**

### 2.1 Segment-wise 仿射拟合（目标 → 公式 → 变量 → 直觉）

**目标**：放弃"全图一个 affine"，改为每个含足够观测的 segment 一个 affine。

$$\hat{\boldsymbol\theta}_i=\arg\min_{\boldsymbol\theta}\sum_{\boldsymbol p\in\mathcal{S}_i} m(\boldsymbol p)\big(a\cdot z_{\mathrm{rel}}(\boldsymbol p)+b-o(\boldsymbol p)\big)^2 \tag{1}$$

- $\boldsymbol\theta=(a,b)^\top$：scale / shift。
- $m(\boldsymbol p)\in\{0,1\}$：该像素是否有有效稀疏观测。
- $o(\boldsymbol p)$：稀疏观测值（LiDAR 点、RGB-D 测量、或由 correspondence match 换算的深度）。
- 直觉：**只在观测存在的像素上算残差**，segment 内共享 $(a,b)$，所以观测密度再低也能解（只要 ≥2 个有效点）。

> 工程注记：论文 §IV-G 的 ablation (a0) 明确写 **inverse depth 上拟合优于 depth 上拟合**——因为 DAv2 本来就是在 affine-invariant **inverse depth** 上训练的。所以实际实现里"$z_{\mathrm{rel}}$"应当是逆深度（或其等价变换），这是复现时最容易踩的坑。

### 2.2 稀疏二部图参数传播（Eq.2–3）

**目标**：不合格 segment（观测不足）的 $(a,b)$ 从邻近合格 segment 借。

$$w_{ij}=\exp\!\Big(-\|\boldsymbol c_i-\boldsymbol c_j\|_2^2/\tau_j\Big),\qquad \hat{\boldsymbol\theta}_j=\frac{\sum_{i\in\mathcal N_j}w_{ij}\hat{\boldsymbol\theta}_i}{\sum_{i\in\mathcal N_j}w_{ij}} \tag{2,3}$$

- $\boldsymbol c_i,\boldsymbol c_j$：segment 质心（2D 图像坐标距离）。
- $\tau_j$：由 $\mathcal S_j$ 到其选中邻居的**中位距离自适应**计算。
- $\mathcal N_j$：保留权重最高的 $K$ 条边（图稀疏化，去掉远距离不可靠传播）。
- 直觉：参数是个"局部常数场"，用距离衰减的加权平均做**软插值**；二部图保证只在"有解↔无解"之间连边，避免合格 segment 之间互相污染。

### 2.3 显式精修：反对称残差 → 测地线代价 → DP

**第一步，定义反对称残差**（与常规一阶余项不同）：

$$R(\boldsymbol p,\boldsymbol q)\triangleq z(\boldsymbol q)-z(\boldsymbol p)-\tfrac12\big(\nabla z(\boldsymbol p)+\nabla z(\boldsymbol q)\big)^\top(\boldsymbol q-\boldsymbol p) \tag{4}$$

性质：$R(\boldsymbol p,\boldsymbol q)+R(\boldsymbol q,\boldsymbol p)=0$，且对任意**仿射深度场** $R\equiv 0$。→ 它只测量"非仿射性"，也就是真正的曲面弯折，消除了方向偏置。

**第二步，用二阶量界定它**：

$$|R(\boldsymbol p,\boldsymbol q)|\le\int_L\phi\,ds,\qquad \phi(u,v)\triangleq\sqrt{z_{uu}^2+z_{vv}^2} \tag{5,6}$$

**第三步，取所有最短路径的下确界，得到测地线代价**：

$$g_\phi(\boldsymbol p,\boldsymbol q)=\min_{L\in\mathcal P_{\boldsymbol p\to\boldsymbol q}}\int_L\phi\,ds \tag{7}$$

**第四步，离散化到 8 邻域并做 DP（min-plus 松弛）**：

$$W(\boldsymbol p^{(k)}\!\to\!\boldsymbol p^{(k+1)})=\ell(\boldsymbol p^{(k)},\boldsymbol p^{(k+1)})\,\phi(\boldsymbol p^{(k+1)}) \tag{8}$$

$$\boldsymbol G_\phi^{(t+1)}(\boldsymbol p)=\min\Big\{\boldsymbol G_\phi^{(t)}(\boldsymbol p),\ \min_{\boldsymbol q\in\mathcal N_{\boldsymbol p}}\big[\boldsymbol G_\phi^{(t)}(\boldsymbol q)+W(\boldsymbol q\to\boldsymbol p)\big]\Big\} \tag{9}$$

- 种子：有观测的像素，$\boldsymbol G_\phi=0$；其余初始化为充分大的值。
- 直觉：这是一次 **Dijkstra / fast marching 的离散版**——代价是"曲面弯折的累积量"，所以传播路径会主动**绕开物体边界**（边界处 $z_{uu},z_{vv}$ 大）。

**第五步，沿选定路径做二阶 Taylor 传播 + 滑动平均融合**：

$$\hat z^{(t)}(\boldsymbol p|\boldsymbol q,\Delta\boldsymbol p)=z^{(t)}(\boldsymbol q)+\nabla z^{(t)}(\boldsymbol q)^\top\Delta\boldsymbol p+\tfrac12\Delta\boldsymbol p^\top \boldsymbol H_z^{(t)}(\boldsymbol q)\Delta\boldsymbol p \tag{10}$$

$$z^{(t+1)}(\boldsymbol p)=\Big(1-\tfrac{1}{t+1}\Big)z^{(t)}(\boldsymbol p)+\tfrac{1}{t+1}\hat z^{(t)}(\boldsymbol p|\boldsymbol q,\Delta\boldsymbol p) \tag{11}$$

$\frac{1}{t+1}$ 就是标准的**在线均值**权重——步数越多，单步预测的权重越低，天然抑制误差累积。默认最多 3 步。

### 2.4 数据驱动精修：把"选一个邻居"换成"所有邻居软加权"

四个可学习输出，全部挂在同一套显式量上：

$$\text{深度残差: } z^{(t+1)}=z^{(t)}+\rho_z r_z^{(t)},\quad \rho_z=0.1 \tag{12}$$
$$\text{不连续密度残差: } \hat\phi^{(t+1)}=\max\big(\epsilon,\ \hat\phi^{(t)}+\rho_\phi r_\phi^{(t)}\big),\quad \rho_\phi=0.02,\ \epsilon=10^{-6} \tag{13}$$
$$\text{亲和度: } a^{(t)}(\boldsymbol p,\boldsymbol q)=\frac{\exp\big(\gamma^{(t)}(\boldsymbol p,\boldsymbol q)-\lambda_\phi\hat\phi^{(t)}(\boldsymbol q)\big)}{\sum_{\boldsymbol r\in\mathcal N_{\boldsymbol p}}\exp\big(\gamma^{(t)}(\boldsymbol p,\boldsymbol r)-\lambda_\phi\hat\phi^{(t)}(\boldsymbol r)\big)},\quad \lambda_\phi=0.05 \tag{14}$$
$$\text{多路径聚合: } \hat z^{(t+1)}=(1-\eta_t)z^{(t)}+\eta_t\sum_{\boldsymbol q\in\mathcal N_{\boldsymbol p}}a^{(t)}(\boldsymbol p,\boldsymbol q)\,z^{(t)}(\boldsymbol p|\boldsymbol q,\Delta\boldsymbol p) \tag{15}$$
$$\text{观测锚定: } z^{(t+1)}=\begin{cases}(1-c(\boldsymbol p))\hat z^{(t+1)}+c(\boldsymbol p)\,o(\boldsymbol p),&m(\boldsymbol p)=1\\ \hat z^{(t+1)},&m(\boldsymbol p)=0\end{cases} \tag{16}$$

**直觉对照**：式 (9) 的 $\min$ → 式 (14) 的 softmax；式 (9) 的解析 $\phi$ → 式 (13) 的 $\hat\phi$ + 学习残差；式 (10) 的固定 Taylor → 式 (12) 的 Taylor + 学习残差。**每一处替换都保持原公式的解释**，这就是"interpretable multi-path"的字面含义。

### 2.5 伪标签训练为何成立（这是最容易被面试官追问的一点）

显式分支已经解决了**全局尺度**，因此网络不需要从训练数据学"metric scale prior"，只需要学"显式精修的残差"。设伪标签为 $\tilde z$，从 $\tilde z$ 上采样得到稀疏观测 $\tilde o$——**$\tilde o$ 天然继承 $\tilde z$ 的全部误差与分布偏移**。于是"用 $\tilde o$ 对 $\tilde z$ 做显式度量化"得到的 $z_{\mathrm{opt}}$ 与 $\tilde z$ 之间的差异，恰好就是显式精修过程的残差，与真实场景中的残差同构。**因此伪标签的绝对精度不重要，重要的是"标签-观测-显式输出"三者的一致性。**

---

## 3 · 带数字走一遍（玩具设定，低维，非论文数据）

**设定**：一段 1D 的"图像"被切成两个 segment $\mathcal S_A$（合格）、$\mathcal S_B$（不合格）。使用 inverse depth 参数化：$y=1/z=a\cdot\rho+b$，其中 $\rho$ 是相对逆深度。

**Step 1 — Segment A 上最小二乘**。三个观测点：

| $\rho$ | $y=1/o$ |
|---|---|
| 0.500 | 4.00 |
| 0.250 | 2.00 |
| 0.125 | 1.00 |

三点共线，闭式解 $\hat a_A=8.00,\ \hat b_A=0.00$（检验：$8\times0.125+0=1.00$ ✓）。则该 segment 内 $\rho=0.125$ 的像素恢复出 $z=1/1.00=1.00$ m。

**Step 2 — 图传播给 Segment B**。两个合格邻居，质心距离平方 $d^2=4$ 与 $d^2=9$，$\tau_j=4$：

- $w_1=\exp(-4/4)=0.368$，对应 $\hat{\boldsymbol\theta}_1=(8.0,\ 0.20)$
- $w_2=\exp(-9/4)=0.105$，对应 $\hat{\boldsymbol\theta}_2=(7.5,\ -0.10)$

$$\hat a_B=\frac{0.368\times8.0+0.105\times7.5}{0.473}=\frac{2.944+0.788}{0.473}=7.89,\qquad \hat b_B=\frac{0.368\times0.20+0.105\times(-0.10)}{0.473}=0.133$$

于是 Segment B 里 $\rho=0.25$ 的像素得 $y=7.89\times0.25+0.133=2.106$，即 $z=0.475$ m。**注意**：这一步用的是"邻居参数的加权平均"，而不是"邻居深度的加权平均"——这是本方法与前作 MTD 都坚持的语义。

**Step 3 — 测地线 DP 选路**。目标像素 $\boldsymbol p$ 的 8 邻域里有两个候选前驱：

- 对角邻居 $\boldsymbol q_{\text{diag}}$（$\ell=\sqrt2\approx1.414$），该处 $\phi=0.90$（正压在物体边界上）→ $W=1.414\times0.90=1.273$
- 水平邻居 $\boldsymbol q_{h}$（$\ell=1$），$\phi=0.10$；再从其左侧 $\boldsymbol q_{hh}$（$\ell=1$，$\phi=0.10$）两步到达 → $W=0.10+0.10=0.200$

$0.200\ll1.273$，DP 选"绕远两步"的 L 形路径而非对角直连——**因为对角穿越边界会引入 ~6× 的残差上界**。这就是"discontinuity-aware"的具体含义。

**Step 4 — 二阶 Taylor 传播 + 融合**。在 $\boldsymbol q_h$ 处 $z=2.000$，$\nabla z=(0.10,\,-0.05)$，$\boldsymbol H_z=\mathrm{diag}(0.010,\,0.020)$，$\Delta\boldsymbol p=(1,0)$：

$$\hat z=2.000+0.10\times1+\tfrac12\times0.010\times1^2=2.105$$

$t=1$ 时融合权重 $1/(t+1)=0.5$，若当前值 $z^{(1)}=2.000$，则 $z^{(2)}=0.5\times2.000+0.5\times2.105=2.0525$。

**Step 5 — 数据驱动残差**。传播头输出 $r_z=-0.0050$，$\rho_z=0.1$ → 修正 $-0.0005$；若该像素是观测锚点且 $c=0.9$、$o=2.060$，则 $z=\big(1-0.9\big)\times2.0520+0.9\times2.060=2.0592$。**锚定把观测误差原样搬进来**——这也是 §6 里"观测噪声无法被网络抑制"的来源。

---

## 4 · 工程视角

| 项目 | 论文给出的值 | 说明 |
|---|---|---|
| 训练硬件 | 4× NVIDIA RTX 4090 | 论文原文 |
| 训练轮数 / batch | 20 epochs, batch size 12 | 论文原文 |
| 优化器 / lr | Adam, 初始 $10^{-3}$，每 5 epoch ×0.3 | multi-step scheduler |
| 输入分辨率 | 480×640（resize + crop） | 训练时；推理分辨率未报告 |
| 显式 DP 最大传播步数 | 3（ablation 中对比 1 与 5） | 步数 ↑：KITTI 改善、VOID 退化 |
| 超参 | $\rho_z=0.1$、$\rho_\phi=0.02$、$\lambda_\phi=0.05$、$\epsilon=10^{-6}$ | $\eta_t$ 随步数递减 |
| 推理延迟（绝对值 / FPS） | **「论文未报告」** | 论文只给 Fig.7(a) 的**相对**耗时分解 |
| 显存占用 | **「论文未报告」** | — |
| 默认相对深度网络 | Depth Anything V2, ViT-L backbone | ViT-L 是推理成本主因之一 |
| 相对耗时分解 | 相对深度网络 + 数据驱动精修的 backbone 合计约 **50%** 总推理时间 | 两者**独立 backbone，不共享特征** |
| 已知瓶颈 | superpixel 分割**仅 CPU 执行**；传播头预测残差与 logit 带来显著开销 | 论文 §IV-I 自述 |

**Trade-off 叙述（可面试复述）**：

1. **显式分支 vs 数据驱动分支的成本不对称**。显式分支是训练-free 的 LSF + 图 + DP，几乎零成本；成本全压在两个 ViT 系 backbone 上。论文自己指出"共享 backbone + 合适训练策略"是最直接的优化方向（未实现）。
2. **DP 步数是精度/误差累积的旋钮**。ablation (c3) 步数=1：KITTI RMSE 2.049、(c4) 步数=5：1.913，但 VOID 从 0.358（默认 3 步）→ 0.391（5 步）变差。**手工设定的传播范围跨数据集不可迁移**，这正是引入可学习多路径的动机。
3. **部署约束**：整套 pipeline 需要 RGB + 已配准的稀疏深度 + **精确外参**，且 superpixel 在 CPU 上跑 → 无法与 GPU 前向完全流水；实际车载/机器人部署时，外参漂移是比算力更致命的风险（论文 §IV-I 第三条局限）。

---

## 5 · 数据与评测

### 5.1 训练数据组成

- **高质量合成**：TartanAir、VKITTI2、Hypersim、IRS、BlendedMVS。
- **无标注真实图像**：BDD100K、SA-1B、MegaDepth。
- **伪标签来源**：上述全部数据用论文引用的高性能 metric depth 模型（reference [17]）生成稠密伪度量深度标签，再按不同采样模式抽稀疏观测用于训练。
- **过滤策略**：丢弃有效像素过少或深度变化过小的样本（论文明确点名 SA-1B 中的平面类图像，如画作、海报、邮票）。
- **损失函数**：沿用前作 [13] 的损失设计（论文未给出具体公式）。

### 5.2 评测数据集（共 16 个公开数据集）

| 数据集 | 用途 | 划分 / 规模（论文原文） |
|---|---|---|
| nuScenes | zero-shot depth completion | test split，150 scenes，6,019 张前视相机图像；单帧 LiDAR 投影；GT 由多帧聚合，遵循 [47] |
| DDAD | zero-shot depth completion | 官方 val split 的 3,950 张前视图像；约 20% LiDAR 深度被采样为稀疏观测 |
| Make3D | zero-shot depth completion | 官方 test split，134 张 |
| DIODE | depth completion + scale recovery | 325 indoor / 446 outdoor；scale recovery 用同一划分，有效深度范围 256 m |
| ETH3D | depth completion（传感器 + 匹配两种）、scale recovery、NVS | depth completion 454 张（遵循 [8]）；correspondence 设定 27 对立体图；scale recovery 有效范围 65 m；NVS：13 train scenes / 12 test scenes，1/8 视角为测试 |
| ScanNet | depth completion + scale recovery | 800 样本；scale recovery 有效范围 10 m |
| VOID | depth completion | 官方 test 800 帧，使用 1,500 points/frame（表头记作 VOID1500） |
| SUN-RGBD | zero-shot depth completion | 排除与 NYUv2 重叠后 4,395 张 |
| HAMMER | zero-shot depth completion | 固定随机种子从官方 test scenes 抽 400 张（论文称将随代码发布） |
| iBims-1 | zero-shot depth completion | 官方 split，100 张 |
| KITTI | scale recovery | Eigen split，652 张，有效范围 80 m |
| NYUv2 | scale recovery | 标准 test split，654 张，有效范围 10 m |
| Middlebury | correspondence 匹配评测 | 15 对立体图，遵循 [54] 的 zero-shot 协议 |
| KITTI Stereo 2012 / 2015 | correspondence 匹配评测 | 194 / 200 对立体图 |
| KITTI Odometry | 下游 VO | Seqs. 00–10 中排除 01、03、04（轨迹过短） |

**稀疏观测合成规则（论文原文）**：无预定义稀疏观测或专用采样协议的数据集，depth completion 随机保留有效深度测量的 **0.01%–0.1%**；scale recovery 保留 **1.0%–1.5%**。

### 5.3 指标

- Depth completion：**RMSE**、**MAE**。
- 与 stereo matching 对比：**BP-1**、**BP-2**（绝对视差误差 >1 / >2 像素的像素百分比）、**D1**（视差误差同时 >3 像素且 >5% GT 的像素百分比），遵循 [54]。
- Scale recovery：**Abs Rel**、**δ₁**。
- NVS：**PSNR**、**SSIM**、**LPIPS**，另加渲染深度与 GT 的 **RMSE**。
- VO：**ATE**（米）。

### 5.4 关键数字（逐字取自论文表格）

**Depth completion（Table I，RMSE / MAE）**：

| 方法 | nuScenes | DDAD | Make3D | DIODE | ETH3D |
|---|---|---|---|---|---|
| Marigold-DC | 4.924 / 2.595 | 6.449 / 2.364 | 8.926 / 4.932 | 1.987 / 0.887 | 0.706 / 0.245 |
| MTD | 4.387 / 2.177 | 5.252 / 1.834 | 8.581 / 4.776 | 1.736 / 0.761 | 0.662 / 0.177 |
| **MTDv2** | **3.081 / 1.344** | **5.470 / 1.095** | **8.225 / 2.634** | **1.534 / 0.461** | **0.384 / 0.108** |

| 方法 | ScanNet | VOID1500 | SUN-RGBD | HAMMER | iBims-1 |
|---|---|---|---|---|---|
| Marigold-DC | 0.145 / 0.059 | 0.505 / 0.151 | 0.238 / 0.067 | 0.054 / 0.037 | 0.176 / 0.038 |
| MTD | 0.129 / 0.049 | 0.366 / 0.138 | 0.220 / 0.050 | 0.093 / 0.034 | 0.190 / 0.072 |
| **MTDv2** | **0.095 / 0.033** | **0.358 / 0.132** | **0.125 / 0.033** | **0.032 / 0.020** | **0.169 / 0.063** |

论文原文结论：MTDv2 相比此前最优结果 **降低 RMSE 4.0%–47.5%**。**注意 DDAD 上 RMSE 从 MTD 的 5.252 微升到 5.470**，论文自述为"可能残留较大深度误差，但 MAE 大幅下降"。

**Scale recovery（Table II，Depth Anything V2 行）**：KITTI `0.018 / 0.991`；NYUv2 `0.009 / 0.995`；ETH3D `0.015 / 0.991`；ScanNet `0.012 / 0.994`；DIODE `0.086 / 0.922`。（格式：Abs Rel / δ₁）

**Stereo 对比（Table III）**：MTDv2 在 Middlebury `BP-2 5.3 / BP-1 2.2`，ETH3D `D1 2.9`，KITTI-12 `D1 4.1`，KITTI-15 `D1 4.1`；FoundationStereo 对应为 `5.5 / 1.8`、`3.2`、`4.9`。论文原文：相比 FoundationStereo 视差误差分别降低 **3.6%、9.4%、16.3%**（Middlebury / KITTI Stereo 2012 / KITTI Stereo 2015）。**注意 BP-1 上 MTDv2 (2.2) 劣于 FoundationStereo (1.8)。**

**NVS（Table IV，ETH3D）**：3DGS `15.64 / 0.557 / 0.418 / 3.857` → 3DGS+MTDv2 `20.42 / 0.689 / 0.213 / 0.812`（PSNR↑ / SSIM↑ / LPIPS↓ / 深度 RMSE↓）。论文原文：深度重投影误差从 `3.857` 降到 `0.812`。

**VO（Table V，KITTI Odometry，ATE↓）**：MTDv2 输入下 Seq00 `24.985`、Seq02 `26.050`、Seq05 `12.513`、Seq06 `13.504`、Seq07 `6.138`、Seq08 `20.965`、Seq09 `24.832`、Seq10 `11.763`。论文原文：相比 RGB-only 与原始 LiDAR 的 RGB-D 配置，平均 ATE 分别降低 **66.2%** 与 **67.7%**。

**Ablation（Table VI，KITTI / VOID，RMSE↓）**：`(a0)` 6.782 / 0.614 → `(b0)` 2.201 / 0.452 → `(c0)` MTD 2.028 / 0.366 → `(d0)` MTDv2 **1.216 / 0.358**。关键消融：`(d2)` 去掉 surface modeling residual → 1.571；`(d5)` 去掉 geometry-aware segmentation → 1.702；`(d4)` 去掉 geometry-guided affinity → 1.284。**说明最大增益来自 segment 量化本身，其次才是残差修正与多路径亲和度。**

---

## 6 · 能力与失败模式

### 6.1 能做（有具体证据的）

- **跨 10 个数据集的 zero-shot depth completion**，且在极稀疏（0.01%–0.1% 有效深度）下优势最大；敏感性分析（Fig.6）显示观测越稀，MTDv2 相对 MTD 的优势越大。
- **观测源无关**：LiDAR 点、RGB-D 测量、correspondence matches 三种来源均可用，无需任务专用训练（显式分支）。
- **兼容三类相对/度量深度范式**：discriminative（MiDaS / LeReS / DPT / Depth Pro / DAv2）、generative（Marigold / GeoWizard / Lotus / DepthMaster）、metric（Metric3Dv2 / UniDepthV2）。Table II 显示连较老的 MiDaS 也能被提到 KITTI Abs Rel `0.053`。
- **下游可用**：3DGS 的深度 RMSE `3.857 → 0.812`；DROID-SLAM 的 ATE 显著下降（长序列漂移改善最明显）。

### 6.2 不能做

- **不能纠正相对深度本身的重大错误**。论文 Fig.7(b) 明确给出失败例：弱光下"车"的相对深度估计错误，该错误同时出现在 MTD 与 MTDv2 输出中。原因：显式精修**保结构**，只改尺度与局部曲面，不改几何拓扑。
- **不能抑制观测噪声**。Eq.16 的锚定直接把 $o(\boldsymbol p)$ 按置信度 $c(\boldsymbol p)$ 写回，$c\to1$ 时观测误差原样进入输出。
- **不能容忍外参漂移**。论文 §IV-I 第三条：方法依赖相机-距离传感器的精确外参，实际安装变化 / 机械扰动 / 长期漂移会降低度量化精度。
- **DDAD 上 RMSE 未改进**（5.470 vs MTD 5.252）：说明混合框架在长距 LiDAR + 高速场景下仍可能残留局部大误差（MAE 大幅下降说明是"少数大误差"而非整体退化）。
- **不是实时系统**：两个独立 backbone + CPU superpixel + 传播头，推理成本是自述首要局限。

### 隐含假设 (Hidden Assumptions)

1. **分段仿射假设**：相对深度与度量深度在**每个 segment 内**满足单一仿射关系，且 segment 边界与"仿射参数变化边界"对齐。几何感知 superpixel 只是让这个假设"更可能成立"，并未保证成立；ablation `(d5)` 显示退回纯纹理分割时 KITTI RMSE 从 1.216 恶化到 1.702，恰恰证明该假设被违反时代价很大。
2. **逆深度线性假设**：默认在**逆深度**上拟合（ablation a0 优于 a1），这依赖 DAv2 的 affine-invariant inverse depth 训练范式。换成原生输出 depth 或 disparity 的模型时，拟合域必须相应调整，否则 Eq.1 的线性关系不成立。
3. **观测正确性假设**：$o(\boldsymbol p)$ 被视为可信锚点，$m(\boldsymbol p)$ 的 1/0 是硬判定——观测的**空间配准误差**被完全忽略。
4. **静态场景假设**：DP 的代价 $\phi$ 从当前深度图算得，若场景中存在运动物体导致深度场非分段光滑，$z_{uu},z_{vv}$ 会异常大，路径可能被错误绕开。
5. **伪标签残差同构假设**：训练成立的前提是"伪标签→采样观测→显式度量化"这条链路产生的残差分布与真实场景同构。若训练采样密度（0.01%–0.1%）与测试时真实 LiDAR 密度不匹配，这个同构性被破坏。
6. **有效深度范围可截断假设**：各数据集的 scale recovery 评测都对深度范围做了截断（KITTI 80 m、NYUv2/ScanNet 10 m、ETH3D 65 m、DIODE 256 m），跨范围外推能力未被验证。
7. **图像分辨率不敏感假设**：训练在 480×640，superpixel 数量与 DP 步数（3 步）都按此尺度设定；高分辨率输入的等价设定未被讨论。

---

## 7 · 与相关工作对比

| 维度 | 全局 affine 对齐（MiDaS/DAv2 惯例） | 纯学习 depth completion（BP-Net / LRRU / DMD3C / Marigold-DC） | 前作 MTD (CVPR'26) | **MTDv2（本文）** |
|---|---|---|---|---|
| 尺度来源 | 全图单组 $(a,b)$ | 网络隐式学习 | 每 segment 一组 $(a,b)$ + 图传播 | 同 MTD，且分割引入几何线索 |
| 是否需任务训练 | 否 | 是（大规模稠密 GT / 合成数据） | 否 | 显式分支否；精修分支需训练（**可用伪标签**） |
| 空间变化的 relative→metric 关系 | ❌ 无法表达 | ✅ 但依赖数据分布 | ✅ | ✅ |
| 极稀疏观测鲁棒性 | 差 | 依赖预处理（插值 / 形态学 / Poisson），稀疏时退化 | 较好 | 最好（稀疏度越高优势越大） |
| 可解释性 | 高（但假设过强） | 低 | 高 | 高（每一处学习都对应一个显式量） |
| 观测源 | 任意 | 通常绑 LiDAR 投影 | LiDAR / disparity / matches | LiDAR / RGB-D / matches |
| 代表数字（nuScenes RMSE） | — | Marigold-DC 4.924 / DMD3C 5.556 | 4.387 | **3.081** |
| 主要短板 | 段内不一致 | 分布偏移敏感 | 分割瑕疵导致跨段大误差、手工算子次优 | 推理成本高、相对深度错时不纠错、依赖精确外参 |

补充对比（Table III）：在 correspondence 作为观测时，MTDv2 不训练 stereo matching 专用特征，却在 Middlebury / KITTI-12 / KITTI-15 的 D1 / BP-2 上超过多数在 Scene Flow 上训练的 stereo 网络，但仍未全面超过 FoundationStereo（BP-1 上落后）。

> **面试 Tip**：被问到"这和 Marigold-DC / DMD3C 这类 depth completion 有什么本质区别"，一句话作答：**"它们学的是 'RGB + 稀疏深度 → 稠密度量深度' 这个映射，MTDv2 学的是 '显式度量化之后还剩多少残差' 这个更小的映射。"** 然后立刻给两个可验证的推论：(1) 因为尺度是解出来的不是学出来的，所以它**可以在伪标签上训练**而不需要真值稠密度量深度；(2) 因为网络只补残差，所以**观测越稀疏，它的相对优势越大**（Fig.6 的趋势）——这两个推论都是论文实测支持的，比单纯背 RMSE 更有说服力。若被追问代价，答：**推理成本**（两个独立 backbone、CPU-only superpixel）与**外参依赖**，这是论文自述的两条硬约束。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-19)

**仓库状态核实**：论文正文仅给出纯文本形式的项目页 `https://mias.group/MTD`，原文措辞为 "Code will be publicly available at ... upon publication"，**全文未出现 `github.com` 链接**。因此本笔记按规则判定为**无 repo 信号**：官方代码库地址、commit、issue 编号均**不存在可验证依据**，以下 pitfall 全部由 §6 的失败模式与 §III 的方法约束**推导**得出，**未经任何 issue 验证**。

### Pitfall 1 — 拟合域选错（depth vs inverse depth）会让整条显式链路静默退化
- **方法约束**：Eq.1 假设 $o\approx a\,z_{\mathrm{rel}}+b$，即"相对深度到度量深度是仿射的"。
- **§6 失败模式**：隐含假设 2 —— 该线性关系只在**逆深度**上成立，因为 DAv2 是在 affine-invariant inverse depth 上训练的。
- **可观测症状**：ablation (a0) 中 `w/ LSF (inverse depth)` 得 KITTI RMSE `6.782`、VOID `0.614`，而 `w/ LSF`（在 depth 上拟合）退化到 `7.013` / `0.791`。差距在小数据集上不易察觉，但在 nuScenes 这类远距场景会被放大。
- **工程动作**：接入新的相对深度骨干时，**先确认其输出参数化**（inverse depth / disparity / depth），再决定 Eq.1 的拟合域；不要默认复用 DAv2 的配置。

### Pitfall 2 — superpixel 边界与"仿射参数边界"不对齐时，误差会跨段放大且被网络掩盖
- **方法约束**：Eq.1 是**段内独立**求解，段间没有任何平滑项（只有 Eq.3 的参数加权平均，那是给**无观测**段的）。
- **§6 失败模式**：隐含假设 1 —— 纯纹理分割会在几何连续面上碎成多块，也会把几何不连续但纹理相近的区域并成一块；前作 MTD 正是因此受限。
- **可观测症状**：ablation (d5) `w/o Geometry-aware segmentation` → KITTI RMSE 从 `1.216` 恶化到 `1.702`（+40%），是除 surface modeling residual 之外最大的单项退化。
- **为什么"被掩盖"**：这类跨段误差在训练分布内会被 propagation head 的 $r_z$ 吸收（因为它确实表现为局部残差），于是**离线指标看起来还行，换域后突然崩**。诊断时应单独可视化 $z_{\mathrm{opt}}$（网络输出前）的段间跳变，而不是只看 $z_{\mathrm{hybrid}}$。
- **工程动作**：把"段间 $|a_i-a_j|$ 与 $|b_i-b_j|$ 的分布"作为监控指标；参数跳变异常说明 superpixel 数量/紧致度超参不匹配当前分辨率（论文未报告其取值，需自行调）。

### Pitfall 3 — 观测锚定（Eq.16）绕过网络，观测量测噪声与配准误差原样进入输出
- **方法约束**：$m(\boldsymbol p)=1$ 时 $z^{(t+1)}=(1-c)\hat z^{(t+1)}+c\,o(\boldsymbol p)$，$c(\boldsymbol p)$ 由网络预测但 $o(\boldsymbol p)$ 是**硬写入**的；同时 Eq.1 与 Eq.9 的种子初始化也都直接把 $o$ 当锚点。
- **§6 失败模式**：隐含假设 3（观测正确性）与"不能抑制观测噪声"。
- **可观测症状**：RGB-D 传感器在物体边缘的 depth 飞点、LiDAR-相机投影在遮挡边界处的错误投影，会在输出中形成**孤立的细线状深度尖峰**，且不随迭代步数消失（因为每一步都被重新锚定）。论文对 nuScenes 明确说明"丢弃有明显投影伪影的样本"，即回避而非解决。
- **工程动作**：(a) 在送入 pipeline 前做观测级离群点剔除（论文对 DDAD 沿用了 KITTI Depth Completion 官方 benchmark 的 outlier filtering 策略，可参考该做法）；(b) 若允许改动，为 $c(\boldsymbol p)$ 加一个基于局部一致性（如与 $z_{\mathrm{opt}}$ 的偏差）的显式门控，而不是完全交给网络。

### Pitfall 4 — 训练采样密度与部署时真实观测密度不匹配，会破坏伪标签监督的同构性
- **方法约束**：§III-E 的监督信号成立依赖"伪标签 → 采样观测 → 显式度量化"这条链路与真实场景**残差同构**；训练时按不同 observation pattern 采样（depth completion 用 0.01%–0.1%）。
- **§6 失败模式**：隐含假设 5 —— 密度分布偏移会破坏同构性；同时 §IV-G 已证明传播步数的最优值**随数据集变化**（KITTI 5 步更好、VOID 5 步更差），说明"最优传播范围依赖观测空间分布"。
- **可观测症状**：在训练密度范围内表现稳定，但在**极高密度**（例如 RGB-D 直接给 30% 有效像素）或**极端非均匀**（雷达近距密、远距疏）输入下，$r_z$ 残差项失去意义（因为显式分支已足够准），网络可能反而引入扰动。
- **工程动作**：部署前用目标传感器的真实稀疏模式（而非随机均匀采样）重跑一次敏感性分析；把训练采样密度区间显式记录在模型卡上。

---

[← Back to 深度感知 模块 README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2610.16749v1 全文 · 未在真机复现的数字标 `UNVERIFIED`
> **核实备注**：§4 中绝对推理延迟、FPS、显存占用论文未报告；§5 全部数据集名与指标数值逐字取自正文与 Table I–VI。论文未给出 `github.com` 链接，§8 全部为推导性 pitfall（未经 issue 验证）。

[//]: # "<!-- source: https://arxiv.org/abs/2610.16749 -->"
