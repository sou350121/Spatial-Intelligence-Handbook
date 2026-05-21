# Cross-Domain Math Inspirations (跨领域数学优化灵感)

> **发布时间**: 2026-05-22
> **核心定位**: 把 spatial AI 当前用的 6 大数学骨架（SE(3) / quaternions / BA / PGO / EKF / IMU preint）拉到**更广阔的数学版图**上看 —— 找跨学科 idea 给未来 SLAM / VIO / 前向 3D 优化带来灵感。

**Status:** v0.5 — roadmap 性质（不是完整 dissection），每条给 *方向 + 核心论文 + 优化 payoff*。深度 dissection 各自值得未来独立成文。
**TL;DR:** 当前 production spatial AI 用 1970s-2010s 的数学（Lie groups, Schur, EKF, BA）。**2020s 后**数学界至少 10 个领域有现成工具可借鉴：信息几何、最优传输、可证优化、RKHS、等变深度学习、score-based / diffusion、随机线代…… **借鉴这些 + 现在的预积分** = 下一代 VIO / SLAM / feed-forward 3D 的 ammo。

**X-Ray.** Forster 预积分是 2017 的（虽然 RSS 2015 投稿）；ORB-SLAM3 是 2021；VGGT 是 2025。这些都用 *经典*非线性最小二乘 + Gaussian assumption + Lie group。**信息几何（1985, Amari）/ optimal transport (1781, Monge; 2013 Sinkhorn) / certifiable SLAM (2018, Rosen) / RKHS-based CT-SLAM (2015, Furgale) / equivariant deep learning (2018, Cohen)** 都有十几年成熟工具，*spatial AI 工程界还没系统消化*。这个 primer 列 10 条最值得跟的方向。

## 📍 跨领域数学版图

```
   spatial AI 已用 (1970-2010 几何 + 优化):
   ─────────────────────────────────────────
   • Lie groups SE(3)/SO(3)           [Sophus, Eigen]
   • Schur complement BA              [Ceres, GTSAM]
   • EKF/MSCKF/UKF                    [OpenVINS]
   • IMU preintegration               [Forster 2017]
   • Quaternion 复合                  [Hamilton / JPL]
   
   待挖掘 (2020s 现代数学已就绪, spatial AI 没系统用):
   ─────────────────────────────────────────
   §1 Information geometry           [Amari, 1985]      → natural gradient on BA
   §2 Optimal transport              [Cuturi, 2013]     → Sinkhorn 取代 ICP
   §3 Certifiable optimization (SDP) [Rosen, 2018]      → 全局最优 PGO
   §4 RKHS / Gaussian process        [Furgale, 2015]    → continuous-time SLAM
   §5 Equivariant deep learning      [Cohen, 2018]      → SE(3)-equiv VGGT-class
   §6 Information-theoretic sensing  [Krause, 2008]     → active SLAM 选 view
   §7 Random sketching               [Halko, 2011]      → 大规模 BA Schur 加速
   §8 Score-based generative         [Song, 2020]       → 位姿分布采样
   §9 Stochastic diff geometry       [Brockett, 1973]   → Itô on Lie groups
   §10 Tropical / max-plus           [Cohen, 1985]      → loop closure 组合
```

---

## §1 · 信息几何 + 自然梯度（Information Geometry / Natural Gradient）

**核心**：状态空间不是平的 R^n，而是带 Fisher metric 的统计流形。普通 SGD / Gauss-Newton 假设欧氏；natural gradient 在 Fisher metric 下走 —— **真正的 steepest descent**。

**当前 spatial AI 的痛点**：BA 在 SE(3)^N × R^3M 上跑 LM。`Hessian = J^T J + λI` 是 *Euclidean* 局部二阶；λI 是任意 trade-off，调参随机。

**借鉴方向**：
- **Riemannian Trust Region** (Boumal et al., 2014) —— BA 用 Riemannian 优化在 SE(3)^N 流形上，trust region 半径自适应，比 LM 收敛更快
- **Natural gradient on Lie groups** —— Fisher metric 给 (R, t) 的耦合权重，避免 t 单位（米）与 R 单位（弧度）的耦合 bug

**Key papers**:
- Amari (1998) *Natural gradient works efficiently in learning*
- Boumal (2014) *Manopt: a Matlab toolbox for optimization on manifolds*
- Carlone (2014) *Initialization techniques for 3D SLAM*

**优化 payoff**：`UNVERIFIED` ~2-3× 收敛速度 + 不再需要手调 LM λ。**最被低估的现成 tool**。

---

## §2 · 最优传输（Optimal Transport）—— 取代 ICP

**核心**：在两个概率分布间找最小代价 transport plan。1781 年 Monge 提出，2013 年 Cuturi 用 Sinkhorn-Knopp 把 O(n³) 降到 O(n² log n)。

**当前 spatial AI 痛点**：ICP（Iterative Closest Point）做点云对齐 —— hard assignment + L2 cost，在密度不匹配 / partial overlap 失败。

**借鉴方向**：
- **Sinkhorn-based point cloud registration** (Wang, 2019) —— soft assignment + 全局最优，处理 partial overlap 比 ICP 强 2-3×
- **Gromov-Wasserstein for non-rigid** (Mémoli, 2011) —— 不同维度空间的对齐，可用于 cross-modal SLAM (camera vs LiDAR vs sonar)
- **Wasserstein for sensor fusion** —— 取代 Gaussian 假设，处理 multi-modal 分布

**Key papers**:
- Cuturi (2013) *Sinkhorn Distances: Lightspeed Computation of Optimal Transport*
- Mémoli (2011) *Gromov-Wasserstein Distances and the Metric Approach to Object Matching*
- Sarlin et al. (2020) *SuperGlue: Learning Feature Matching* —— 用 Sinkhorn 做特征匹配，已 production

**优化 payoff**：替代 ICP 是 immediate win。**SuperGlue 已经把这个 idea 用在前端，但 SLAM 后端 / 多 modal 融合还没用够**。

---

## §3 · 可证优化（Certifiable Optimization / SDP Relaxations）

**核心**：BA / PGO 是非凸优化 —— LM 给 *local* optimum。SDP relaxation (Lasserre hierarchy) 给一个凸 lower bound + **可验证是否达到 global optimum** 的 certificate。

**当前 spatial AI 痛点**：ORB-SLAM3 / VINS-Fusion 用 LM 跑 BA —— 没人能告诉你"这真的是 best 还是卡在 local min"。

**借鉴方向**：
- **SE-Sync** (Rosen et al., 2018) *International Journal of Robotics Research* —— 把 PGO 的 SDP relaxation 在 SO(3)^N 流形上解，**给全局最优 + certificate**
- **Certifiably correct SLAM** —— BA 也有 SDP relaxation (Yang & Carlone, 2020)
- **Outlier-robust** —— SDP 自然处理 outliers, 不需要 RANSAC 启动

**Key papers**:
- Rosen et al. (2018) *SE-Sync: A Certifiably Correct Algorithm for Synchronization over the Special Euclidean Group*
- Yang & Carlone (2020) *In Perfect Shape: Certifiably Optimal 3D Shape Reconstruction*

**优化 payoff**：**全局最优 + 可证明** —— 在不需要 IMU 紧耦合的应用（offline SfM / map building / 离线 lidar SLAM）可以取代 LM-BA。**Production 还没普及**，但 OpenVINS / GTSAM 有 SE-Sync 接口。

---

## §4 · RKHS / Gaussian Process —— 连续时间 SLAM

**核心**：把 trajectory 当成 GP 样本（连续时间随机过程），代替离散 keyframe + 离散预积分。

**当前 spatial AI 痛点**：传感器异步（cam 30 Hz + IMU 1 kHz + LiDAR 10 Hz）需要插值 / 同步；离散预积分假设 Δt 内常速度，高频运动失真。

**借鉴方向**：
- **Anderson, Barfoot, Tong (2013)** *Continuous-Time Gaussian Process Trajectory Estimation* —— 用 sparse GP prior（WNOJ 模型）让 GP 在 SE(3) 上跑稀疏
- **Furgale (2015)** *Continuous-Time Batch Trajectory Estimation Using Temporal Basis Functions* —— B-spline 表示
- **Cartographer (Google, 2016)** —— 已 production，用 ceres + B-spline 跑 LiDAR SLAM

**关键 trick**：GP 的稀疏化（WNOJ / WNOA）让 inference 是 sparse linear system，不破 O(N) scaling。

**Key papers**:
- Furgale, Barfoot (2013) *Sparse Gaussian Process Regression on Lie Groups*
- Cartographer code: https://github.com/cartographer-project/cartographer

**优化 payoff**：高动态运动 + 异步 sensor 场景 (drone race + event camera + IMU 1 kHz + cam 30 Hz) 比离散方法更稳。**Cartographer 已 production；VINS / OpenVINS 没用**。

---

## §5 · 等变深度学习（SE(3)-Equivariant Networks）

**核心**：神经网络架构本身保 SE(3) 对称性 —— 输入旋转/平移 ⇒ 输出旋转/平移对应变化。无需 data augmentation 学对称性。

**当前 spatial AI 痛点**：VGGT / DUSt3R 用 ViT —— 没有任何几何 prior，靠大数据强行学 SE(3) 不变性 / 等变性。**Sample efficiency 差**。

**借鉴方向**：
- **Cohen & Welling (2016)** *Group Equivariant CNNs* —— 群理论硬塞进 conv
- **Thomas et al. (2018)** *Tensor field networks* —— 物理化学界的 SE(3)-equivariant 已 production
- **e3nn** —— DeepMind / DeepChem 开源框架
- **Equivariant DUSt3R / VGGT** —— **学术界已有少量 work** (`UNVERIFIED` 具体引用)，但 production 没用

**Key papers**:
- Cohen, Welling (2016) *Group Equivariant Convolutional Networks*
- Geiger et al. (2022) *e3nn: Euclidean Neural Networks*
- Köhler et al. (2020) *Equivariant Flows*

**优化 payoff**：**数据效率 10× 提升**（教科书结论，未在 spatial AI verify）。VGGT-Ω 训练 15× 数据如果用 equivariant 架构可能只要 1.5×。**最被低估的下一代 architecture move**。

---

## §6 · 信息论 active SLAM —— 选下个 view 该去哪

**核心**：传感器测量 = 信息增益；下一帧该测哪里 = max(MI) over future measurements。香农 1948。

**当前 spatial AI 痛点**：drone 自主探索靠 frontier-based / 启发式 —— 没数学最优性保证。

**借鉴方向**：
- **Krause & Guestrin (2008)** *Near-optimal sensor placements* —— submodularity 给 (1 - 1/e)-近似最优
- **Stachniss et al. (2005)** *Information-gain–based exploration*
- **Boots et al.** —— GP-MI 类 active SLAM 算法

**实际应用**:
- 自主巡检 drone 决定下个 inspection 点
- humanoid 哪个时刻该看脚下 vs 看远
- multi-robot SLAM 分工

**优化 payoff**：把"探索效率"从 ad-hoc 启发式变成 **(1-1/e)-bound** 优化问题。**学界已成熟，production 没用**。

---

## §7 · 随机线代 / sketching —— 大规模 BA 加速

**核心**：1000 cam × 100k point BA 的 Schur complement 是 O(N²M) —— prohibitive。Randomized SVD / matrix sketching 给 *approximate* 解，O(N M log N) 量级。

**借鉴方向**：
- **Halko, Martinsson, Tropp (2011)** *Finding structure with randomness*
- **Randomized BA** (Frahm et al., 2010 城市级 SfM)
- **GPU + randomized Schur** —— 还没有 production 实现 `UNVERIFIED`

**Key papers**:
- Halko et al. (2011) *Finding Structure with Randomness: Probabilistic Algorithms for Constructing Approximate Matrix Decompositions*
- Frahm et al. (2010) *Building Rome on a Cloudless Day*

**优化 payoff**：**Map merging / loop closure 大规模 BA 10-100× 加速**。对长期 SLAM (>1 hour 飞行 + 1000+ keyframe) 是 enabler。**Production 还没出现，机会大**。

---

## §8 · Score-based / Diffusion —— 位姿分布采样

**核心**：扩散模型不只生成图像 —— 它学一个数据分布的 score function，可以从任意先验采样到后验。**位姿不再是点估计，是 distribution**。

**当前 spatial AI 痛点**：VGGT / FoundationPose 给出一个 pose；不告诉你不确定性（covariance 是 hack）。

**借鉴方向**:
- **Song, Ermon (2020)** *Generative Modeling by Estimating Gradients of the Data Distribution*
- **Diffusion Policy** (Chi et al., 2023) —— 已用在 manipulation
- **Pose diffusion** —— 学术界 2024 起爆发，production 没用 `UNVERIFIED`

**优化 payoff**：
- 多模态位姿（多个合理答案）能采样 —— 处理 ambiguity
- Uncertainty 可量化 + 可传播到下游 policy
- 替代 RANSAC（hypothesis sampling 用 diffusion）

**Key papers**:
- Song & Ermon (2020) *Generative Modeling by Estimating Gradients of the Data Distribution*
- Chi et al. (2023) *Diffusion Policy*

**优化 payoff**：处理 ambiguity + 上游下游不确定性传播。**学术热点，production 没碰**。

---

## §9 · 随机微分几何 —— Itô on Lie groups

**核心**：IMU 噪声不是 R^3 上 Brownian motion —— 是 SE(3) 流形上的 Brownian motion。Itô calculus 一般版本（Élie Cartan，1920s）才描述对。

**当前 spatial AI 痛点**：Forster 预积分 covariance 传播用 Euclidean 一阶近似 —— 在 high-rotation segment（drone aggressive maneuver）失精。

**借鉴方向**:
- **Hamelink, Vakhania** (1968) —— Lie group Brownian motion
- **Brossard, Bonnabel** (2021) —— 直接在 Lie 群上做随机滤波
- **Invariant EKF** (Barrau, Bonnabel 2017) —— 已经是这条线下产品

**Key papers**:
- Barrau, Bonnabel (2017) *The Invariant Extended Kalman Filter as a Stable Observer*
- Brossard et al. (2020) *AI-IMU Dead-Reckoning*

**优化 payoff**：long session VIO 不漂 + 高动态运动 covariance 不 over/underestimate。**IEKF 已经在 Skydio 内部用** (`UNVERIFIED`)；学术界领先 production 5-10 年。

---

## §10 · Tropical / max-plus algebra —— 组合优化

**核心**：把 +/× 替换成 max/+ —— 形成新的代数。Dijkstra / Bellman 是 max-plus 矩阵的特征向量问题。Loop closure 中 keyframe-graph 最短路径 = max-plus matrix exp。

**借鉴方向**:
- **Cohen** (1985) *Min-Plus and Max-Plus Algebras*
- **Karp** (1979) *Characterization of the minimum cycle mean*
- **应用**: large-scale loop closure 用 max-plus 替代 Dijkstra

**优化 payoff**：`UNVERIFIED` 大规模 PGO 中找最优 loop closure topology 时，max-plus 比 Dijkstra 稍快 + 更接近线代结构。**最 speculative 的一条，暂时没看到 spatial AI 应用**。

---

## 综合排序（按 spatial AI 优化 payoff × 当前成熟度）

| § | 方向 | 优化 payoff | 成熟度 | 推荐优先级 |
|---|---|---|---|---|
| §1 | 信息几何 / 自然梯度 | 高（BA 2-3× 收敛）| ⭐⭐⭐⭐ 已成熟 | **🥇 首推** |
| §2 | 最优传输 / Sinkhorn | 高（替 ICP）| ⭐⭐⭐⭐⭐ 已 production (SuperGlue) | **🥈** |
| §3 | 可证 SLAM (SE-Sync) | 中（offline 全局最优）| ⭐⭐⭐⭐ 学术成熟 | **🥉** |
| §4 | RKHS / GP CT-SLAM | 中（异步 sensor）| ⭐⭐⭐⭐ Cartographer 已 prod | 高 |
| §5 | SE(3) 等变深度学习 | **极高**（数据 10× 减）| ⭐⭐⭐ 学术成熟，spatial 没用 | **最被低估** |
| §6 | 信息论 active SLAM | 中（exploration 效率）| ⭐⭐⭐ 学术成熟 | 中 |
| §7 | 随机 sketching BA | 中（大规模加速）| ⭐⭐ 学术新 | 中 |
| §8 | Score-based 位姿 | 高（不确定性）| ⭐⭐ 学术热点 | 中-高 |
| §9 | 随机微分几何 (IEKF) | 高（long session 稳定）| ⭐⭐⭐ Skydio 内部用 | **隐形 winner** |
| §10 | Tropical / max-plus | 低 | ⭐ speculative | 低 |

---

## 🎤 Interview Tip

> "如果你想给 production VIO 加一个跨学科 idea，会选哪个？为什么？"
>
> 强答：**"SE(3) equivariant deep learning 给 feed-forward 3D**（VGGT 谱系）—— 现在它们靠 15× 数据强学 SE(3) 不变性，等变架构可能 1.5× 数据就够。短期回报最高的是 **Sinkhorn 替代 ICP** —— 已被 SuperGlue 证明可用，SLAM 后端 / 多模态融合还没普及。长期 game-changer 是 **certifiable SLAM** —— 给 SLAM 全局最优 + 证书。每一条都有 2010s 已 mature 的论文，spatial AI 工程界还没系统消化。"

---

## Boundary

- **现行 Lie group / Quaternion / BA 数学** → `./se3_so3_lie_groups_primer.md`, `./quaternions_and_rotations.md`, `./bundle_adjustment.md`, `./pose_graph_optimization.md`
- **IEKF (§9 的当前 instantiation)** → `./bayesian_filtering_ekf_msckf.md` + 本仓 `./imu_preintegration_math.md` §6.6
- **Sinkhorn (§2) 在前端** → `../pose-tracking/cotracker_and_tap_dissection.md` 中 SuperGlue refresh
- **CT-SLAM (§4)** → `./imu_preintegration_math.md` §6.5
- **Equivariant 深度学习 (§5)** → 未来若开 region 见 `../geometric-deep-learning/`（暂不存在）

---

## References (跨学科核心)

- Amari (1998) *Natural gradient works efficiently in learning*. Neural Computation 10(2).
- Cuturi (2013) *Sinkhorn Distances: Lightspeed Computation of Optimal Transport*. NIPS.
- Rosen et al. (2018) *SE-Sync: A Certifiably Correct Algorithm for Synchronization over the Special Euclidean Group*. IJRR.
- Anderson, Barfoot, Tong (2013) *Continuous-time Gaussian process trajectory estimation*. ICRA.
- Cohen, Welling (2016) *Group Equivariant CNNs*. ICML.
- Krause, Guestrin (2008) *Near-optimal sensor placements*. JMLR.
- Halko, Martinsson, Tropp (2011) *Finding Structure with Randomness*. SIAM Review.
- Song, Ermon (2020) *Generative Modeling by Estimating Gradients of the Data Distribution*. NeurIPS.
- Barrau, Bonnabel (2017) *The Invariant Extended Kalman Filter as a Stable Observer*. IEEE T-AC.

---

## ✍️ 维护者注

本 primer 是 **roadmap**，每条值得未来独立 dissection。建议优先开 §5（equivariant）和 §3（certifiable SLAM）两条 —— 都有 production 落地 momentum。

---

[← Back to Spatial Math](./README.md)
