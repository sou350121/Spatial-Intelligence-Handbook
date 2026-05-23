# SE(3) Equivariance in Networks Primer (神经网络中的 SE(3) 等变性入门)

> 💡 **没读过李群基础？先读** [`se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md) — manifold / 切空间 / exp-log，这里假设你会。

> **发布时间**: 2026-05-22
> **核心定位**: 2024-2026 manipulation policy（Equivariant Diffusion Policy）/ molecular structure（AlphaFold 系列）/ 3D point cloud（VN / TFN / SE(3)-Transformer / E3NN / Equiformer）背后那条**所有人都默认你会**的现代主线 — 网络结构如何"内建"3D 对称性，而不是从数据里硬学。

**Status:** v1 — primer。非论文 Table 直接来源的数字均标 `UNVERIFIED`。
**TL;DR:** 普通 MLP / Transformer 不知道"把场景整体旋转 90° 任务本质没变"，需要靠 data augmentation 暴力告诉它。**SE(3) equivariant 网络把这条对称性焊进权重里** —— 输入旋转一个 R，输出自动旋转同一个 R。后果是 3D 任务（点云、分子、机器人动作）的 sample efficiency 可以涨数倍，而且 OOD pose 也不崩。这是当前 robot policy + 3D foundation model + protein structure 共享的核心 inductive bias。

**X-Ray.** 3D 物理世界对 SE(3) 是封闭的：把场景旋转 30° 再让机器人执行，物理后果完全一样。普通网络不知道，必须遍历朝向才学。**Equivariant 架构在每一层维持对称性**：用 type-0 标量 + type-ℓ 向量 / 张量作隐藏特征，用 Clebsch-Gordan tensor product 做等变 mixing。代价慢，收益是数据小、泛化强。中文直觉：**不是教网络"任何角度都对"，而是让它根本无法"对"和"不对"地分别回答**。

## 📍 研究全景时间线

```
2017       2018         2020              2021            2023         2024            2026
TFN ──►   E(n)-MLP ──► SE(3)-Transformer► E3NN / VN ──►  Equiformer► EquivDiffPolicy► YOU ARE HERE
Thomas     Cohen        Fuchs NeurIPS     Weiler/Deng    Liao ICLR    Wang CoRL         Equiformer-v2
球谐函数    群等变 DL     attention 框架    库 + 向量 neuron atomistic    机器人 落地       + 3D foundation
```

Cohen 2018 是等变网络起点；2024-2026 在机器人 / 分子 / 3D foundation 同时落地。

---

## §1 · 形式定义：invariance vs equivariance

### 1.1 两种对称性，差一条公式

G = 对称群（这里 SE(3)）, `g ∈ G` 一个群元素, `x` 输入, `f` 网络:

```
   Invariance:    f(g · x) = f(x)        ← 输入转了, 输出不变
   Equivariance:  f(g · x) = g · f(x)    ← 输入转了, 输出同步转
```

**这区别要命**：

| 任务 | 想要 |
|---|---|
| 点云分类 / 分割（输出 label） | Invariance |
| 3D 物体检测、抓取 pose、蛋白结构（输出几何对象） | **Equivariance** |

输出"几何对象"（pose、vector field、displacement）的任务**都要 equivariance**。

### 1.2 为什么是 SE(3)

- SO(3) 只旋转 — 不够（桌子可挪动）
- **SE(3) = SO(3) ⋉ R³** rigid motion — manipulation / SfM / 分子默认
- E(3) = SE(3) + reflection — 分子（手性除外）
- SIM(3) = SE(3) + scale — 单目 SLAM 闭环

**直觉**：把桌子整体挪 + 转，任务本质不变 — 这就是 SE(3) 等变性。

---

## §2 · 不做 equivariance 的代价

**普通 MLP / Transformer 怎么"学"等变性**：靠 data augmentation 暴力刷 — 训练时把每个样本随机转一个 R。问题：

- **Sample efficiency 烂**：R₁(x) 和 R₂(x) 被当两个独立样本；连续 3D 旋转群需要的样本随精度指数爆炸
- **OOD pose 崩**：训练只见过桌子朝南，部署朝东可能直接错
- **学到的是 *近似* equivariance**：本质是 brittle regularizer

**经验性数字**：
- 3D 点云分类，无 augmentation 时 SE(3)-equiv 比 vanilla PointNet 高 5-10 个百分点 `UNVERIFIED, VN paper Sec 4`
- Equivariant Diffusion Policy 在 demos=10-50 时 success rate 比 vanilla 高 2-5× `UNVERIFIED, Wang CoRL 2024 Table 1-2`
- AlphaFold2/3 把 SE(3) equivariance 当核心 inductive bias `UNVERIFIED, 业界口口相传`

**直觉**：等变性把对称性从 task signal 抽出来，免费送给网络。

---

## §3 · 三条实现路线（核心对比表）

### 3.1 三条路线

| 路线 | 代表方法 | 隐藏特征是什么 | 表达力 | 速度 | 实现难度 |
|---|---|---|---|---|---|
| **A. Type-0 only（只用标量）** | PointNet、DGCNN | 不变的标量（距离、角度、内积） | 低（无法输出向量） | 快 ⚡⚡⚡ | 容易 |
| **B. Vector neurons (VN)** | Deng ICCV 2021 | 标量 + 3D 向量（type-0 + type-1） | 中 | 中 ⚡⚡ | 中 |
| **C. Spherical harmonics (TFN / SE(3)-Trans / E3NN / Equiformer)** | Thomas 2018, Fuchs 2020, Weiler 2021, Liao 2023 | type-ℓ 张量（ℓ=0,1,2,...）按 SO(3) 不可约表示 | 高（理论上最 expressive） | 慢 ⚡ | 高（需要 CG product） |

### 3.2 路线 A：Type-0 only

只处理 SE(3)-invariant 量（点对距离、键角）。**PointNet (Qi 2017)** 用 T-Net 学对齐，是 *approximately* invariant。**DGCNN (Wang 2019)** EdgeConv 用 (x_j - x_i)，平移等变但旋转不变。**局限**：无法重建方向 — 3D detection 出 bbox orientation 要额外塞 yaw。

### 3.3 路线 B：Vector Neurons (VN)

**Deng ICCV 2021**：把 scalar neuron 升级成 **3D 向量 neuron**。

```
   传统 MLP:        v_out = σ(W · v_in + b)      v_in ∈ R^C
   Vector Neuron:   V_out = σ(W ⊙ V_in)          V_in ∈ R^{C×3}
                    W 只在 channel 维混合, 3D 那一维原样跟着输入转
                    → 输入旋转 R, 输出也乘 R → SO(3) equivariance by construction
```

**非线性**：不能用 ReLU（破坏 equivariance），用 **VN-ReLU**（learnable hyperplane 投影）。**优点**：实现简单；比球谐路线快 2-5× `UNVERIFIED`。**局限**：只到 type-1，type-2+ 表达不了，分子能量不够用。

### 3.4 路线 C：Spherical Harmonics + Clebsch-Gordan

- **TFN (Thomas 2018)** — 第一个把球谐搬进点云
- **SE(3)-Transformer (Fuchs 2020)** — TFN + attention，邻居聚合也等变
- **E3NN (Weiler & Cesa 2021)** — PyTorch library，写等变模型像写 nn.Linear
- **Equiformer / v2 (Liao ICLR 2023/2024)** — E3NN + Transformer，atomistic SOTA

**核心 building block**：

```
   隐藏特征  h^{(ℓ)} ∈ R^{C_ℓ × (2ℓ+1)}        ℓ=0 标量, ℓ=1 向量, ℓ=2 五维球谐...
   等变线性  W^{ℓ→ℓ'}                          只允许同型混合
   等变 msg  m_{ij} = Y^{(ℓ)}(r̂_ij) ⊗_CG h_j  球谐 × Clebsch-Gordan tensor product
```

**直觉**：CG product 把两个协同变换的张量乘起来仍然协同变换 — 所有 mixing 都保留 equivariance。**优点**：理论最 expressive（universal approximator）；分子 / 力场 benchmark 反复 SOTA。**缺点**：慢（O(L_max³) 常数）、内存大、实现门槛高。

---

## §4 · 在机器人 / VLA 的应用

### 4.1 Equivariant Diffusion Policy (Wang CoRL 2024)

传统 Diffusion Policy (Chi 2023) 学 noise → action 的 denoiser，但 vanilla 对 SE(3) 不等变 — 桌面转 90° 就是新场景。**Equivariant DP 把 score network 每层做成 SE(3)-equivariant**（用 VN 或 E3NN），demo 一次 = 学到该 demo 的全部 SE(3) 轨道。论文 Table 1-2 报告 (`UNVERIFIED`，未逐行验证)：

- demos=10：success rate ~30% → ~70%
- demos=50：~70% → ~90%
- OOD object pose：vanilla 崩，equivariant 稳
- 代价：训练 / 推理慢 ~2-3× `UNVERIFIED`

### 4.2 同代际（社区在搬）

- **RVT (Goyal 2023) / 3D Diffuser Actor (Ke 2024)** — multi-view rendering 当 invariance proxy，**不是真 equivariant**
- **EDF (Ryu ICLR 2023)** — pick-and-place 的 SE(3) field
- **EquAct (Lin CoRL 2024)** — SE(3)-equivariant transformer

### 4.3 蛋白质 / 分子（机器人圈在抄）

- **AlphaFold2 (Jumper 2021)** — IPA (Invariant Point Attention) 是 SE(3) equivariance 核心
- **AlphaFold3 (Abramson 2024)** — IPA → diffusion-based pose denoiser，仍 equivariant
- **DiffDock (Corso 2023)** — molecular docking 用 SE(3) diffusion

**为什么机器人圈在抄分子圈**：数学结构惊人一致 — "少量样本 + 强 3D 对称性 + 输出几何对象"。AlphaFold 用 ~18 万样本解了 50 年蛋白质问题 `UNVERIFIED`，SE(3) equivariance 占一半功劳；机器人想用 100-1000 demos 学 task，方向相同。

---

## §5 · 计算代价：TFN 为什么慢

**球谐 Y^{(ℓ)}(θ,φ)** 把方向编码成 2ℓ+1 维（L_max=4 时每方向要算 25 个分量）。**Clebsch-Gordan** 两个 type-ℓ₁,ℓ₂ 乘起来住在 |ℓ₁-ℓ₂| ≤ ℓ ≤ ℓ₁+ℓ₂ 所有阶；每条 edge 上做很多次。

**结论**：TFN / E3NN 每条 edge 开销是 vanilla GNN 的 10-50× `UNVERIFIED`（取决于 L_max + channel）。

**工程妥协**：
- **L_max=1 or 2** — Equiformer-v2 实测 L_max=2 已够好
- **稀疏 CG implementation** — E3NN 预编译跳过 zero 项
- **VN 替代** — 只需 type-1 就用 VN，快得多
- **Hybrid** — 中间用 invariant features，末端 lift 回 equivariant

---

## §6 · 何时值得加 SE(3) equivariance？

| 场景 | 建议 |
|---|---|
| <1k samples + 3D + 输出几何对象（50 demos manipulation） | 必须加 |
| ~10k samples + 3D（分子 / 蛋白质） | 多半值得 |
| >1M samples + 3D（自动驾驶 nuScenes） | augmentation 替代，ROI 边际 |
| Real-time control >100Hz（PX4 / VIO 内圈） | 不要加，用经典李群 EKF |
| 2D 任务 / 输出标量 | 不必，invariance 足够 |
| 输出 pose / vector field / SE(3) 变量 | 强烈建议 |

**反面经验**：2024 不少论文当 buzzword 加上，large-scale 数据上**反而比 augmentation 慢且不一定更准**。**Equivariance 是 small-data prior**，不是万灵药。

---

## §7 · 与经典 SLAM 的关系

**经典 SLAM 早就在做等变性**，只是用 manifold 语言：

| 经典 SLAM | DL equivariance 对应 |
|---|---|
| Pose graph 在 SE(3) 上优化 | network state 住在 SE(3) representation |
| EKF 误差状态在 so(3) 切空间传 covariance | type-1 vector features 跟着旋转 |
| BA right perturbation `R·exp(δφ)` | 等变 layer 用 CG product 替代朴素 add |
| IMU preintegration 切空间累积 δθ | 等变 message passing 每条 edge SO(3)-aware |

**核心区别**：经典 SLAM 只在状态 / 优化层用 manifold（ORB/SIFT 不是 equivariant，靠 hand-crafted descriptor 凑合）；DL equivariance **从输入到输出每一层都维持**。

**面试 Tip**: "**李群 / 流形管的是状态空间**，equivariance 管 **feature 在状态变换下的协同变换** — 前者是 1990s 控制论传统，后者是 2018 后 representation theory 进 DL，两者在 BA / EKF Jacobian 推导那一刻碰头。"

---

## §8 · Boundary

- SE(3)/SO(3) manifold 数学 → [`./se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md)
- 6D continuous rotation rep (Zhou CVPR 2019) → `./rotation_reps_in_deep_learning_primer.md`（TBD）
- VGGT 类是否 equivariant → [`../feed-forward-3d/README.md`](../feed-forward-3d/overview.md)（VGGT 非严格 equivariant）
- 等变 feature cloud 接到 VLA action head → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- 经典 SLAM manifold 优化 → [`./bundle_adjustment.md`](./bundle_adjustment.md), [`./bayesian_filtering_ekf_msckf.md`](./bayesian_filtering_ekf_msckf.md)

## References

**必引核心论文**：
- Zhou et al. (2019) *On the Continuity of Rotation Representations in Neural Networks*. CVPR 2019. [arXiv 1812.07035](https://arxiv.org/abs/1812.07035) — 6D rotation rep。
- Thomas et al. (2018) *Tensor Field Networks*. [arXiv 1802.08219](https://arxiv.org/abs/1802.08219)
- Fuchs et al. (2020) *SE(3)-Transformers*. NeurIPS 2020. [arXiv 2006.10503](https://arxiv.org/abs/2006.10503)
- Deng et al. (2021) *Vector Neurons*. ICCV 2021. [arXiv 2104.12229](https://arxiv.org/abs/2104.12229)
- Weiler & Cesa (2021) *E3NN*. [arXiv 2110.06557](https://arxiv.org/abs/2110.06557). [Library](https://e3nn.org/)
- Liao et al. (2023/2024) *Equiformer / v2*. ICLR. [arXiv 2206.11990](https://arxiv.org/abs/2206.11990) / [arXiv 2306.12059](https://arxiv.org/abs/2306.12059)
- Wang et al. (2024) *Equivariant Diffusion Policy*. CoRL 2024. [arXiv 2407.01812](https://arxiv.org/abs/2407.01812)

**应用 / 基础**：
- Chi et al. (2023) *Diffusion Policy*. RSS. [arXiv 2303.04137](https://arxiv.org/abs/2303.04137)
- Ryu et al. (2023) *EDF*. ICLR. [arXiv 2206.08321](https://arxiv.org/abs/2206.08321)
- Jumper et al. (2021) *AlphaFold*. Nature. [DOI](https://doi.org/10.1038/s41586-021-03819-2) — IPA。
- Abramson et al. (2024) *AlphaFold 3*. Nature.
- Corso et al. (2023) *DiffDock*. ICLR. [arXiv 2210.01776](https://arxiv.org/abs/2210.01776)
- Cohen & Welling (2016) *Group Equivariant CNNs*. ICML. [arXiv 1602.07576](https://arxiv.org/abs/1602.07576) — 等变 DL 起点。
- Sola et al. (2018) *Micro Lie theory*. [arXiv 1812.01537](https://arxiv.org/abs/1812.01537)

[← Back to Spatial Math](./overview.md)
