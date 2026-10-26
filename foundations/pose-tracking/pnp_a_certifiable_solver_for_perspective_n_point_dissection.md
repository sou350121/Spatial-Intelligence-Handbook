[//]: # "<!-- ontology-5axis
problem: pose
representation: n/a
sensor: mono
paradigm: geometric
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# PnP*：可认证的 Perspective-n-Point 求解器 (PnP*: A certifiable solver for Perspective-n-Point)

> **发布时间**：2026-10-22 (arXiv v1)
> **论文 / 模型名**：PnP* (Perspective-n-Point Star)
> **核心定位**：首个直接优化 PnP 真实 MLE 目标、并在中等噪声下可证明精确（certifiable）的可扩展求解器；比 BnB 快 3–8×，N=6 时 >10 Hz 返回带证书的全局最优姿态。

现有 PnP 方法要么解最小问题（P3P 等，无法平均噪声），要么把 MLE 目标替换成更易解的"替代误差"（EPnP / SQPnP / Alternative 等），要么用 branch-and-bound 直接优化 MLE 但最坏情况指数爆炸。PnP* 用 Shor 半正定松弛 + chordal 稀疏 + 商环约简，首次把"直接优化 MLE 的可认证全局求解器"做到多项式时间、N=6 下 74 ms 的平均求解速度。

---

## 🩻 X-Ray 开场

PnP* 解决的是"如何在不换目标函数的前提下，对 N 个 3D-2D 对应给出一个**可证明的全局最优相机姿态**"。它把 PnP 的 MLE 先重构成一个带辅助变量与冗余约束的二次约束二次规划（QCQP），再对提升后的变量做 Shor SDP 松弛；随后证明该松弛在中等噪声下是精确的（stability guarantee），并用 chordal 星形稀疏 + 商环约简把每个 37×37 半正定块压到 34×34，使问题在点数 N 上线性可扩展。对空间智能研究者而言，这意味着 PnP 第一次拥有了类似 rotation averaging / pose graph optimization 那样"局部求解器 + 全局证书"的闭环：你可以用 PnP* 给 EPnP+LM 的结果发证书，也可以把它当作可认证的全局回退。

---

## 📍 研究全景时间线

```
2003 ── P3P (Gao) ────────────────────────── 最小求解器，配 RANSAC 当 hypothesis generator
2006 ── BnB (Olsson) ─────────────────────── 直接优化 MLE，但最坏情况指数时间
2008/09 ─ L∞ (Enqvist-Kahl / Hartley-Kahl) ─ 改目标换速度
2009 ── EPnP (Lepetit) ───────────────────── 非最小，优化加权重投影误差（替代误差）
2011 ── Kneip 最小求解器 / Hesch-Roumeliotis 点-线误差
2013 ── Zheng et al. ─────────────────────── Gröbner 基求替代误差临界点
2017/18 ─ Tron / Briales ─────────────────── 旋转约束的 20 条二次约束形式
2020 ── SQPnP (Terzakis-Lourakis) / Alternative (Sun-Deng) ─ 替代误差的可认证/全局求解
2021 ── Cifuentes ────────────────────────── 相机标定的稳定 SDP 松弛（但不含旋转约束）
2022 ── Cifuentes et al. ─────────────────── SDP 稳定性判据（本文直接复用）
2023 ── Agostinho et al. / Ding et al. ───── 替代误差可认证求解器 / 最小求解器
2026 ── Wise et al. 手眼标定；Zhao et al. 综述
2026 ── PnP*（本文）────────────────────── 首个可扩展、直接优化 MLE 的可认证求解器
                                              │
                                              └─ 局限：无外点鲁棒性；需 N≥6 且非退化；依赖商业 SDP 求解器
```

PnP* 的位置：它填补了"直接优化 MLE"与"可扩展可认证"之间的空白。此前 Cifuentes (2021) 给出了相机标定的稳定松弛但**不含旋转约束**且明确把可扩展求解器留作 open problem；PnP* 加上旋转约束后重新验证稳定性（因为可行集变了，稳定性不再自动继承），并用 chordal + 商环把 Cifuentes 的开放问题在 PnP 这个特例上解决了。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统/组件对比表

| 模块 | 输入 | 输出 | 训练/推理差异 | 关键约束 |
|---|---|---|---|---|
| 原始 MLE (Problem 1) | 3D 点 $\{p_i\}$、2D 测量 $\{\theta_i\}$、内参 $K$ | $(R,t)\in SO(3)\times\mathbb{R}^3$ | 无训练；纯优化 | 非凸（投影是 rational，可行集非凸） |
| Naive QCQP (Problem 2) | 同上 + 辅助变量 $v\in\mathbb{R}^{2N}$ | $w=(h,z,v)\in\mathbb{R}^{13+2N}$ | 无 | Shor 松弛**非信息性**（目标恒为 0） |
| Lifted QCQP (Problem 3) | 引入 $y=v\otimes z$ | $x=(h,z,y)\in\mathbb{R}^{13+24N}$ | 无 | 提升基 + 冗余约束；每点子变量 $x^{(i)}\in\mathbb{R}^{37}$ |
| SDP (Shor) | Problem 3 的 $X=xx^\top$ 松弛 | $X\in\mathbb{S}_+^{13+24N}$ | 无 | 中等噪声下精确（Thm 3） |
| Chordal-SDP | 星形依赖图 | $N$ 个 $X^{(i)}\in\mathbb{S}^{37}$ | 无 | 用 Grone 定理保证可 PSD 完成 |
| Reduced-SDP | 商环 $\mathbb{R}[x^{(i)}]/\mathcal{I}_i$ 约简 | $N$ 个 $\check X^{(i)}\in\mathbb{S}^{34}$ | 无 | 每块去 3 维 |
| PnP* 提取 | Reduced-SDP 的 hub 块 $\check X^{(1)}_{\mathbf{hh}}$ | 认证姿态或 LM 回退 | 无 | rank-1 + 正深度检查 |

### 1.2 关键机制

**⚡ Eureka Moment：把 MLE 的 rational 投影通过辅助变量 $v$ 和提升变量 $y=v\otimes z$ 变成 QCQP，并选择一组"恰好保留星形稀疏"的冗余约束——这个选择让 Shor 松弛既可证明精确（稳定性）又可线性扩展（chordal + 商环）。**

拆开看三层洞见：

1. **为什么 naive QCQP 不行**：模型约束 $m_{\theta,i}(z,v)=0$ 是 $v$ 与 $z$ 的双线性项，目标只含 $\|v\|^2$。Shor 松弛把 $vv^\top$ 和 $vz^\top$ 当成独立变量，于是可以把它们解耦并令目标为 0——无论 $\theta$ 是什么（论文 Proposition 4 构造了 $W^*=\mathrm{diag}(1,\frac13 I_{12},0)$ 显式证明）。
2. **提升的代价与收益**：把 $y_i=v_i\otimes z$ 显式作为变量后，模型约束变成**线性**（在 $x^{(i)}$ 中），乘上基向量得到二次冗余约束；提升后的基是 $[1,z,v\otimes z]$，变量 $x\in\mathbb{R}^{13+24N}$。代价是变量维度从 $13+2N$ 涨到 $13+24N$，收益是松弛变得**信息性**。
3. **稀疏性的刻意保留**：冗余约束只取"第 $i$ 个点自己的单式"，于是每条约约束只涉及 $x^{(i)}=(h,z,y_i)$，变量依赖图是 hub=$(h,z)$、spoke=$y_i$ 的**星图**——chordal，最大团是 37 维，可以分解成 $N$ 个小 SDP。

### 1.3 信息流 ASCII 图

```
3D-2D correspondences {p_i}, {θ_i}, K
        │
        ▼
Problem 1: min Σ ||θ_i − π_i(z)||²   s.t. R∈SO(3)      ← 非凸 MLE
        │  引入 v_i = θ_i − π_i(z)
        ▼
Problem 2: min ||v||²  s.t. m_{θ,i}(z,v)=0, r_j(h,z)=0, h²=1
        │  Shor 松弛 → 非信息性（目标恒 0）
        │  提升基: [1,z,v] → [1,z,v⊗z]，令 y=v⊗z
        ▼
Problem 3: min ||y||²  s.t. g_{θ,i}(x)(x^{(i)})^T=0, r_j=0, ||z||²=1, u_i u_i^T ∈ BS¹²₃₆
        │  Shor 松弛
        ▼
(SDP):  X ∈ S_+^{13+24N}，Thm 3：中等噪声下稳定/精确
        │  星形 chordal 分解（Grone 定理）
        ▼
(Chordal-SDP): N 个 X^{(i)} ∈ S_+^{37}，共享 hub 块
        │  商环约简：Q_i ∈ R^{3×37}, x^{(i)}=Ξ_i x̌^{(i)}
        ▼
(Reduced-SDP): N 个 X̌^{(i)} ∈ S_+^{34}
        │  提取 hub 块 X̌^{(1)}_{hh}（13×13）的最大特征向量 (h,z)
        ▼
z* = z/h → (R*,t*)；若 rank-1 且所有 e₃ᵀP_i z* ≠ 0 → 认证全局最优
        │  否则：投影 R* 到 SO(3)，LM 局部精修（失去证书）
        ▼
输出 (R,t) 或 NaN
```

---

## 2 · 数学核心

📌 **Napkin Formula**：

> PnP 的 MLE 可提升为带星形 chordal 结构的 QCQP；其 Shor SDP 松弛在中等噪声下**精确**（$p^*_{\text{SDP}}=p^*_{\text{MLE}}$ 且唯一 rank-1），而商环约简把每个 37 维块压到 34 维。

**目标**：直接最小化真实 MLE 目标，而非替代误差。

**公式**：

$$
\min_{z=(\mathrm{vec}(R),t)\in\mathbb{R}^{12}} \sum_{i=1}^{N}\|\theta_i-\pi_i(z)\|^2 \quad \text{s.t. } R\in SO(3) \tag{Problem 1}
$$

其中
$$
\pi_i(z)=\frac{[I_2\ 0]KP_i z}{e_3^\top P_i z},\qquad P_i=(p_i,1)^\top\otimes I_3\in\mathbb{R}^{3\times 12}.
$$

提升后：
$$
\min_{x=(h,z,y)} \|y\|^2 \quad \text{s.t. } g_{\theta,i}(x)(x^{(i)})^\top=0,\ r_j(h,z)=0,\ \|z\|^2=1,\ u_iu_i^\top\in\mathcal{BS}^{36}_{12} \tag{Problem 3}
$$

其中 $y_i=v_i\otimes z$，$x^{(i)}=(h,z,y_i)\in\mathbb{R}^{37}$，
$$
g_{\theta,i}(x)=\theta_i(e_3^\top P_i z)-[I_2\ 0]KP_i z-(I_2\otimes(e_3^\top P_i))y_i.
$$

**变量说明**：

| 符号 | 维度 | 含义 |
|---|---|---|
| $z=(\mathrm{vec}(R),t)$ | 12 | 向量化相机姿态 |
| $v_i=\theta_i-\pi_i(z)$ | 2 | 第 $i$ 个点的重投影残差 |
| $h$ | 1 | 齐次变量（$h^2=1$，后改为 $\|z\|^2=1$） |
| $y_i=v_i\otimes z$ | 24 | 提升变量 |
| $x^{(i)}=(h,z,y_i)$ | 37 | 每个点的团变量 |
| $X^{(i)}$ | $\mathbb{S}^{37}$ | Chordal 分解后的半正定块 |
| $\check X^{(i)}$ | $\mathbb{S}^{34}$ | 商环约简后的块 |

**直觉**：MLE 的难点是"投影是 rational，旋转约束非凸"。PnP* 用 $v$ 吸收 rational，用 20 条二次约束刻画 $SO(3)$，再用 $y=v\otimes z$ 把双线性约束线性化。关键在于：提升基要选得**刚好**让冗余约束保留星形稀疏——选大了 SDP 爆炸，选小了松弛非信息性。

---

## 3 · 带数字走一遍（玩具设定）

**设定**：$N=6$（论文实验的最小配置），$K=\begin{pmatrix}800&0&320\\0&800&240\\0&0&1\end{pmatrix}$，图像 $640\times480$，深度在 $[5,35]$ 采样。以下数字是玩具演示，不来自论文实验。

**Step 1 · 维度计数**

- 全 SDP：$x\in\mathbb{R}^{13+24\cdot6}=\mathbb{R}^{157}$，对称矩阵上三角变量数 $\binom{157+1}{2}=12403$。
- Chordal-SDP：6 个 $37\times37$ 块，每块 $\binom{37+1}{2}=703$，共 $6\times703=4218$。
- Reduced-SDP：6 个 $34\times34$ 块，每块 $\binom{34+1}{2}=595$，共 $6\times595=3570$。
- 约简幅度：$(4218-3570)/4218\approx15.4\%$，与论文"12%–18% faster"方向一致。

**Step 2 · naive 松弛的零目标构造（Proposition 4）**

取 $W^*=\begin{pmatrix}1&0&0\\0&\frac13 I_{12}&0\\0&0&0\end{pmatrix}\in\mathbb{S}_+^{13+2N}$。检查：
- $W^*_{hh}=1$ ✓（齐次约束）
- $W^*_{zz}=\frac13 I_{12}$，旋转列迹和 $=3\times\frac13=1$ ✓
- $W^*_{vv}=0$，目标 $=0$ ✓
- 模型约束只涉及 $W_{hz}$ 和 $W_{vz}$，在 $W^*$ 中均为 0 ✓

结论：naive Shor 松弛对任意 $\theta$ 都能取到 0，**与测量无关**——这就是"非信息性"的具体含义。

**Step 3 · hub 块 rank-1 提取（玩具）**

假设 Reduced-SDP 解出 hub 块
$$
\check X^{(1)}_{\mathbf{hh}} = \begin{pmatrix}h\\ z\end{pmatrix}\begin{pmatrix}h\\ z\end{pmatrix}^\top,\quad h=0.1,\ z=(0.3,\,-0.2,\,0.4,\ 0.1,\,0.05,\,-0.08,\dots)^\top
$$
（这里省略 $z$ 的后 12 维）。取最大特征向量，得 $z^*=z/h=(3,-2,4,1,0.5,-0.8,\dots)$，拆出 $\mathrm{vec}(R^*)$ 和 $t^*$。若 $\check X^{(1)}_{\mathbf{hh}}$ 秩 1 且所有 $e_3^\top P_i z^*\neq0$，则 $(R^*,t^*)$ 是 Problem 1 的认证全局最小。否则将 $R^*$ 投影到 $SO(3)$，以 $(R^*,t^*)$ 为初值跑 LM。

**注意**：玩具数字只用于演示流程，不代表真实求解结果。

---

## 4 · 工程视角

| 项目 | 论文报告值 | 备注 |
|---|---|---|
| SDP 求解器 | MOSEK ApS (2025) | 商用求解器 |
| 硬件 | M4 MacBook Air, 16GB RAM | CPU only |
| Monte Carlo 次数 | 40 | 所有实验 |
| 秩判定阈值 | 特征值 $>10^{-5}$ | |
| $N=6$ 平均求解时间 | **74 ms** | (Reduced-SDP) |
| 认证解频率 | **>10 Hz** | $N=6$ |
| vs 局部非最小求解器 | **慢约 3 个数量级** | EPnP / SQPnP + LM |
| vs BnB（$N=6$ 噪声扫描） | **快 3×–13×** | |
| vs BnB（点数扫描） | **快 3×–8×** | |
| Chordal-SDP vs SDP | $N=10$ 快 **6×**，$N=50$ 快 **约 65×** | |
| Reduced-SDP vs Chordal-SDP | 快 **12%–18%** | |
| GPU / VRAM | **论文未报告** | 纯 CPU 实验 |
| 嵌入式部署（Jetson 等） | **论文未报告** | |
| 内存峰值 | **论文未报告** | |
| SDP 构建 vs 求解时间拆分 | **论文未报告** | |

**Trade-off 解读**：

- **精度换速度**：PnP* 比 EPnP/SQPnP+LM 慢约 3 个数量级，定位不是实时前端，而是"给局部解发证书"或"离线/回退全局解"。
- **多项式 vs 指数**：BnB 直接优化 MLE 但最坏情况指数；PnP* 多项式时间，实测快 3–8×。但 BnB 需要平移的先验界来保证搜索空间紧致（论文明确说明），PnP* 不需要。
- **chordal 是主要的规模化杠杆**：$N=10$ 时 6×、$N=50$ 时约 65×，说明全 SDP 在大 N 下不可用；商环约简是"锦上添花"（12%–18%）。
- **部署约束**：依赖 MOSEK（商用），没有开源/嵌入式 SDP 求解器的实验；若要上机器人/AR 设备，需换求解器或做定点化，这部分论文未涉及。

---

## 5 · 数据与评测

**数据组成**：**全部为合成数据**，论文未使用任何真实数据集（无 KITTI / N3V / Technicolor 等）。

- 随机旋转；随机平移，范数 $\le 5$。
- 内参 $K=\begin{pmatrix}800&0&320\\0&800&240\\0&0&1\end{pmatrix}$。
- 2D 测量在 $640\times480$ 图像上均匀采样，反投影深度在 $[5,35]$ 均匀采样。
- 2D 测量加高斯噪声 $\mathcal{N}(0,\sigma^2 I_2)$，$\sigma$ 以像素为单位。

**评测设置**：

| 实验 | 设置 |
|---|---|
| 稳定性（§7.1） | $N=6$；噪声扫描 $\sigma$；40 次 Monte Carlo |
| 可扩展性（§7.2） | $\sigma=10$ 像素；点数扫描 $N$；40 次 Monte Carlo |

**对比方法**：
- P3P (Gao et al., 2003)：枚举所有 3 点组合，取全对应重投影误差最小者。
- EPnP (Lepetit et al., 2009)、SQPnP (Terzakis and Lourakis, 2020)：各带/不带 LM 精修。
- Alternative (Sun and Deng, 2020)：加权重投影误差的可认证求解器（**不是 MLE**）。
- BnB (Olsson et al., 2006)：相对次优容差 $\varepsilon=10^{-4}$；需要平移先验界，上界由 $(\breve R,\breve t)=(I_3,(0,0,1+\max_i\|p_i\|))$ 构造，下界假设参考点深度至少为 1。

**报告指标**：MLE 目标值、rank-1 率、相对次优界 $(\bar p-p^*_{\text{SDP}})/p^*_{\text{SDP}}$、旋转误差（度）、平移误差（米）、求解时间。

**关键数字（逐字）**：
- 松弛在 $\sigma$ **up to 10 pixels** 时所有运行精确。
- rank-1 率：$N=4$ 时 **39 of 40**，$N=5$ 时 **37 of 40**，$N\ge6$ 时 **all 40 runs**。
- $N=3$ 时松弛**tight 但不 exact**（P3P 可有至多 4 个解）。
- $N=6$ 时 (Reduced-SDP) **74 ms** 平均。
- PnP* 比 BnB 快 **3× to 13×**（§7.1）/ **3× to 8×**（§7.2）。
- Chordal-SDP 在 $N=10$ 快 **6×**，$N=50$ 快 **约 65×**。
- Reduced-SDP 比 Chordal-SDP 快 **12%–18%**。

---

## 6 · 能力与失败模式

### 能做

- **可认证全局最优**：rank-1 + 正深度检查通过时，返回的姿态是 MLE 的全局最小，且证书可验证（Proposition 3 不依赖 $\theta$ 在 $\bar\theta$ 邻域，只依赖解本身）。
- **中等噪声下精确**：$\sigma$ 到 10 像素，$N=6$ 所有 40 次运行精确（Theorem 3 + 实验）。
- **点数线性可扩展**：chordal + 商环后，单次求解在 $N$ 上多项式；$N=6$ 时 74 ms。
- **给局部求解器发证书**：即使你本来就用 EPnP+LM，也可以用 PnP* 的 SDP 下界验证局部解是否全局最优。
- **不需要平移先验界**：与 BnB 不同，PnP* 不要求平移的先验上下界。

### 不能做

- **外点**：MLE 是 L2 损失，没有鲁棒核；论文在结论中明确把 outlier robustness 列为未来工作。真实数据必须先用 RANSAC 等外点剔除，但 RANSAC + PnP* 的组合延迟论文未报告。
- **$N<6$ 的一般情形**：Assumption 1 要求 $N\ge6$；$N=3$ 时松弛 tight 但不 exact（多解），$N=4/5$ 时部分运行失败（39/40、37/40）。
- **退化配置**：Assumption 1 排除 camera resectioning 的临界集（Hartley-Zisserman Result 22.5/22.6）。
- **负深度 / 点在相机后方**：Proposition 3 要求所有 $e_3^\top P_i z\neq0$；$z$ 在相机后方时提取失败。
- **未知内参**：$K$ 必须已知且固定，论文不处理自标定。
- **无 LM 回退时的保证**：当 rank-1 或正深度检查失败时，算法回退到 LM，此时**不再有证书**，只是一个局部解。
- **商业 SDP 求解器依赖**：实验全部用 MOSEK；嵌入式/开源替代未评估。

### 隐含假设 (Hidden Assumptions)

1. **针孔模型 + 已知内参 + 无畸变**：投影 $\pi_i$ 是理想针孔；鱼眼/畸变模型未涉及。
2. **加性高斯噪声**：MLE 的 L2 目标隐含高斯噪声；非高斯/重尾噪声下"全局最优"不再是统计意义上的最优。
3. **静态场景、单帧**：每帧独立求解，无时序先验。
4. **$N\ge6$ 且非退化**：少于 6 点或临界配置时，唯一性不成立，松弛可能不精确。
5. **点在相机前方**：正深度是提取姿态的前提。
6. **精确 SDP 求解器可得**：MOSEK 的数值精度和许可证是隐含的工程前提。
7. **rank 阈值为 $10^{-5}$**：秩判定是数值的，接近阈值的病态实例可能误判。

---

## 7 · 与相关工作对比

| 方法 | 目标 | 用全部点 | 全局最优 | 复杂度 | 需要初值 | 需要平移界 |
|---|---|---|---|---|---|---|
| P3P (Gao 2003) | MLE（最小集） | ✗ | ✗ | closed form | ✗ | ✗ |
| EPnP (Lepetit 2009) | 替代加权误差 | ✓ | ✗ | linear | ✗ | ✗ |
| SQPnP (Terzakis 2020) | 替代加权误差 | ✓ | ✗（局部） | SQP | ✓ | ✗ |
| Alternative (Sun-Deng 2020) | 替代加权误差 | ✓ | ✓（对该误差） | polynomial | ✗ | ✗ |
| BnB (Olsson 2006) | MLE | ✓ | ✓ | 最坏指数 | ✗ | ✓ |
| Cifuentes (2021) | MLE（相机标定，无旋转约束） | ✓ | ✓ | polynomial（未做可扩展求解） | ✗ | ✗ |
| **PnP*（本文）** | **MLE** | **✓** | **✓** | **polynomial** | **✗** | **✗** |

**关键差异**：
- 与 EPnP/SQPnP/Alternative 比：它们优化的是**替代误差**，PnP* 优化真实 MLE；实验显示 SQPnP 与 Alternative 结果重合（因为同一加权误差），而 PnP* 的 MLE 目标更低、姿态误差更小。
- 与 BnB 比：PnP* 多项式时间，实测快 3–8×；BnB 需要平移先验界，PnP* 不需要。
- 与 Cifuentes (2021) 比：PnP* 加了旋转约束（可行集变了，稳定性需重新证明），并首次给出可扩展求解器（chordal + 商环）。

**面试 Tip**：被问到"PnP* 和 EPnP/SQPnP 怎么选？"——答："EPnP/SQPnP 是实时前端，毫秒级但只对替代误差最优；PnP* 是慢约 3 个数量级的全局证书，$N=6$ 时 74 ms。工程上可以 EPnP+LM 出初值，PnP* 离线/低频验证是否全局最优；或者在外点剔除后、对精度敏感的场景用 PnP* 直接求全局解。"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-26)

论文在脚注 7 给出实现链接 `https://github.com/doggydoggy0101/pnp-star`。但论文发表于 2026-10-22（距本文档 4 天），属于 early-release，**无可验证的社区 issue 流**；以下 pitfall 由 §6 失败模式 + 方法约束推导，**未经 issue 验证**，不编造任何 issue 编号 / commit hash / 引文。

### Pitfall 1 · SDP 求解器依赖导致嵌入式部署失败

- **机制**：PnP* 的每一步都调用 MOSEK 求解 (Reduced-SDP)。MOSEK 是商用求解器，嵌入式/机器人平台（Jetson、ARM）上通常不可用或无许可证。
- **推导链**：§6 "不能做"第 7 条（商业 SDP 求解器依赖）→ §4 "嵌入式部署论文未报告" → 在 ARM 上直接复现会卡在 MOSEK 安装/许可证。
- **缓解**：换用 SCS / SDPA / Clarabel 等开源 SDP 求解器，但收敛速度和数值精度需重测（论文未报告）。

### Pitfall 2 · RANSAC 外点场景下证书失效

- **机制**：PnP* 最小化 L2 MLE，无鲁棒核；外点会污染 $\theta_i$，使 Shor 松弛不再精确（稳定性只在 $\bar\theta$ 邻域成立），rank-1 检查失败后回退 LM，证书丢失。
- **推导链**：§6 "不能做"第 1 条（外点）+ 结论中 "incorporating outlier robustness" 列为未来工作 → 真实数据必须先 RANSAC，但 RANSAC + PnP* 的延迟论文未报告。
- **缓解**：RANSAC 内点集 + PnP* 验证；或对残差做鲁棒加权后重解（论文未评估）。

### Pitfall 3 · $N<6$ 或临界配置下 rank-1 检查失败

- **机制**：Assumption 1 要求 $N\ge6$ 且世界点 + 相机中心不在 camera resectioning 临界集。$N=3$ 时松弛 tight 但不 exact（多解，P3P 至多 4 解），$N=4/5$ 时部分运行 rank>1，算法回退 LM。
- **推导链**：§6 "不能做"第 2/3 条（$N<6$、退化配置）+ §5 实验 "39 of 40 at N=4, 37 of 40 at N=5" → 小 N 场景（如 3-4 点的实时应用）得不到认证解。
- **缓解**：$N\ge6$ 时再用 PnP*；小 N 用 P3P+RANSAC 或 EPnP。

### Pitfall 4 · 负深度 / 点在相机后方导致提取失败

- **机制**：Proposition 3 要求 $e_3^\top P_i z\neq0$（正深度）。若部分点在世界坐标系中位于相机后方，或数值上深度接近 0，提取 $z^*=z/h$ 后检查失败，回退 LM。
- **推导链**：§6 "不能做"第 4 条（负深度）+ Proposition 3 的显式条件 → 环视/鱼眼/大视场配置下容易触发。
- **缓解**：先做视锥剔除，确保所有点在前方；或改用不假设正深度的投影模型（论文未涉及）。

---

[← Back to module README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

[//]: # "<!-- source: https://arxiv.org/abs/2610.31797 -->"
