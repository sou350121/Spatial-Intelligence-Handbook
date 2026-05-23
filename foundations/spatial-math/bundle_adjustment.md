# Bundle Adjustment (BA, 光束法平差)

> **发布时间**: 2026-05-21
> **核心定位**: 1950 年代起，每个 SfM / SLAM 系统核心的非线性最小二乘优化 —— 以及让它变得可解的 Schur complement 技巧。

**Status:** v1 —— primer。稀疏性结构出处为 Triggs et al. 2000 + Ceres 文档。
**TL;DR:** BA 通过最小化 reprojection error 联合精调相机位姿与 3D 点。Jacobian 巨大但 block-sparse；Schur 把点边际化掉，留下小得多的纯位姿系统。**没有任何 SfM / SLAM 不靠 BA 出货，包括 VGGT 的蒸馏管线 `UNVERIFIED`。**

**X-Ray.** 一次 SLAM session 会在几百帧上收集几千个特征观测。每个观测都是一个噪声像素，对应一个 3D 点经一个噪声位姿投影出来的样子。BA 给每个观测写一条 residual，堆成一个庞大的非线性 LSQ，用 LM 求解。朴素的法方程有 `(6N+3M)²` 个 entry —— 几十亿 —— 但它的结构是两块对角块加一座稀疏的桥，Schur 正好利用这点。BA 是少数几个理解稀疏性比理解数学本身更重要的经典算法。（中文直觉：同时调相机和点 —— Jacobian 两块对角加一条细桥，Schur 利用这形状。）

## 📍 研究全景时间线

```
1957       2000              2011        2014    2021         2025         2026
Brown SBA► Triggs survey ► g2o      ► Ceres ► ORB-SLAM3 ► DROID-SLAM ► VGGT skips
           "BA-Modern Synthesis"     Google  Atlas BA      learned BA    BA forward
           (the bible)                                                    YOU ARE HERE
```

Triggs 2000 是规范引用；Ceres（2014）让 BA 变得可用。VGGT（2025）在前向 pass 跳过 BA —— 但**蒸馏**那边还是经典 BA 在做监督。

---

## 1 · 架构：BA 优化什么

### 1.1 问题

给定 N 个位姿 `{T_i ∈ SE(3)}`、M 个点 `{X_j ∈ R³}`、观测 `{u_ij ∈ R²}`：

```
min   Σ_(i,j) || u_ij - π(T_i, X_j, K) ||²_Σ
T,X
```

`π` = 投影（内参 `K` 固定）；`Σ` = 观测协方差。

### 1.1.1 一张图：BA 到底在调什么

```
                3D 世界 (待估)                          2D 屏幕 (已观测)
                                                                                
                  🔺 X_1                                ┌────── cam_1 ─────┐
                 ╱╱ ╲╲                                  │                  │
                ╱╱   ╲╲                                 │  ✦ u_11 (观测)   │
               ╱╱     ╲╲                                │   ╲                
              ╱╱       ╲╲                               │    ╲ ← residual r│
       📷 cam_1        📷 cam_2  ─── π(T_2, X_2) ──►   │     ╳ π(预测)    │
              ╲╲       ╱╱                               │                  │
               ╲╲ 🔵 X_2 ╱╱                             └──────────────────┘
                ╲╲ ╱╱╲╲ ╱╱                                                  
                 ╲╳  ╲╳                                 ┌────── cam_2 ─────┐
                ╱╲    ╲╲                                │  ✦ u_22          │
               ╱╱      ╲╲                               │    ╳ π(...)       │
              ╱╱        ╲╲                              │      ↑ minimize  │
       📷 cam_3 ────────► 📷 cam_4                      │      this gap     │
                                                        └──────────────────┘
                                                                            
       每条 "📷─🔵" 光线 = 一个 observation u_ij
       residual r_ij = u_ij(像素观测) − π(T_i, X_j)(投影预测)
                                                                            
       BA 同时调所有 T_i（位姿）+ 所有 X_j（点），让 Σ ‖r_ij‖² 最小。
       "光束法平差" = "把所有 (相机 ↔ 点) 光束拟合干净"。
```

### 1.2 ⚡ Eureka Moment

> **BA 的 Jacobian 有"两块 + 细桥"稀疏性 —— Schur 把求解从 `O((6N+3M)³)` 降到 `O(N³ + N²M)`，M » N 时由 `N²M` 主导。**

这个 trick 让 BA 在几百相机几百万点的规模下可行。每个 SLAM 优化器（g2o、Ceres、GTSAM）都实现它。

### 1.3 稀疏性图

**Step 1 — J 的形状**：每行（一个观测）只在 2 个 6-列 块（看它的相机）+ 1 个 3-列 块（它看的点）非零。

```
                         ←── 6N cam cols ──→  ←──── 3M point cols ────→
                         cam_1 cam_2 ... cam_N  X_1   X_2   ...   X_M
                       ┌──────┬──────┬─────────┬──────┬──────┬──────┬──────┐
   u_11 (cam1×X1)  →   │ ████ │      │         │ ████ │      │      │      │
   u_12 (cam1×X2)  →   │ ████ │      │         │      │ ████ │      │      │
   u_21 (cam2×X1)  →   │      │ ████ │         │ ████ │      │      │      │
   u_22 (cam2×X2)  →   │      │ ████ │         │      │ ████ │      │      │
   u_NM (camN×XM)  →   │      │      │    ████ │      │      │      │ ████ │
                       └──────┴──────┴─────────┴──────┴──────┴──────┴──────┘
                              ↑                            ↑
                       每行 2 个非零                   每行 1 个非零
                       6-col camera 块               3-col point 块
```

**Step 2 — `H = JᵀJ` 的"两块 + 细桥"**：

```
                  ←──── 6N (~hundreds) ────→  ←─── 3M (~hundred-thousands) ───→
                ┌────────────────────────────┬───────────────────────────────┐
                │                            │                               │
                │            U               │              W                │
        6N      │      6N × 6N               │         6N × 3M               │
       cams     │   sparse (cam-cam          │   bridge (non-zero only if    │
                │    covisibility only)      │    cam i actually sees pt j)  │
                │                            │                               │
                ├────────────────────────────┼───────────────────────────────┤
                │                            │ ┌─┐                            │
                │                            │ │█│                            │
                │           Wᵀ               │ │ │█│       V                  │
        3M      │      3M × 6N               │ │   │█│   3M × 3M              │
       pts      │    (W transposed)          │ │     │█│  ★ STRICTLY          │
                │                            │ │       │█│ BLOCK-DIAGONAL    │
                │                            │ │         │█│ (each 3×3       │
                │                            │ │           │█│ independent)  │
                │                            │ └─────────────┘                │
                └────────────────────────────┴───────────────────────────────┘

           ★ "block diagonal V" = 每个 3×3 子块独立 ⇒ V⁻¹ 是 M 次独立 3×3 求逆
                                  这一性质是 Schur complement 的**整个基础**。
                                  没有它，BA 算不动。
```

---

## 2 · 数学核心：Schur complement 与 LM

### 📌 Napkin Formula

```
[ U   W ] [Δc]    [g_c]                  H = JᵀJ + λI
[ Wᵀ  V ] [Δp] = -[g_p]

Schur:  (U - W V⁻¹ Wᵀ) Δc = -g_c + W V⁻¹ g_p     ← poses only
then:   Δp = V⁻¹ (-g_p - Wᵀ Δc)                  ← back-sub points
```

`V` 分块对角，所以 `V⁻¹` = M 次独立的 3×3 求逆。约化后的相机系统是 `6N × 6N` —— N=100 时是 600×600，CPU 上轻松。

### 变量（Sola / Triggs 约定）

| 符号 | 含义 |
|---|---|
| `T_i ∈ SE(3)` | 相机 i 的位姿，右扰动 |
| `X_j ∈ R³` | 3D landmark |
| `u_ij ∈ R²` | 观测像素 |
| `r_ij = u_ij - π(...)` | reprojection residual（px） |
| `H = JᵀJ` | GN Hessian 近似 |
| `λ` | LM damping |

LM 一步：计算 (r, J)，组 `H = JᵀJ + λI`，Schur-solve Δc，回代 Δp，trial，accept / 缩 λ 或 reject / 涨 λ。`λ→0` 即 GN；`λ→∞` 即梯度下降。自适应让 LM 在 GN 会发散的情形依然稳健。

### 2.x LM 一次迭代的流程图

```
              ┌──────────────────────────────┐
              │  当前 T_i, X_j (init or 上轮) │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  计算 residual r, Jacobian J │
              │  (遍历所有 u_ij 观测)         │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  H = JᵀJ + λI                │
              │  g = Jᵀr                     │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Schur 约化:                  │
              │    (U−WV⁻¹Wᵀ)Δc = -g_c+WV⁻¹g_p│  ← 6N × 6N 系统 (轻量)
              │  Solve Δc                    │
              │  Back-sub: Δp = V⁻¹(...)     │  ← M 次独立 3×3 (并行)
              └──────────────┬───────────────┘
                             │
                             ▼
            ┌──────────────────────────────────┐
            │  Trial: T ⊕ Δc, X + Δp           │
            │  新 cost = Σ ‖r_new‖²            │
            └────────┬───────────────┬─────────┘
                     │ cost ↓         │ cost ↑
                     ▼               ▼
            ┌───────────────┐  ┌──────────────────┐
            │  ✓ accept     │  │  ✗ reject        │
            │  λ /= 10      │  │  λ *= 10         │
            │  (更接近 GN)  │  │  (更接近 GD)     │
            └────────┬──────┘  └────┬─────────────┘
                     │              │
                     └──────┬───────┘
                            │
                            ▼
                  收敛 / 到 iter 上限?  ──否──┐
                            │ 是              │
                            ▼                 │
                         完成 ←───────────────┘ (回顶重算)

         λ→0   ≡ Gauss-Newton (快、需 init 好)
         λ→∞   ≡ gradient descent (稳、慢)
         自适应 λ ≡ LM —— 介于两者，GN 失败时能恢复，GN 顺利时跑得快
```

---

## 3 · 玩具例子：3 个位姿、5 个点

三个相机、五个点、互看（15 个观测）。

- 状态：`6·3 + 3·5 = 33`
- Residual：`2·15 = 30`
- `J` 是 `30×33`；`H` 是 `33×33`。

```
H = [ U (18×18 cam block) | W (18×15 bridge) ]
    [ Wᵀ                  | V (15×15 strictly block-diag, 3×3 per pt) ]
```

Schur 约化成 `18×18` 纯相机块加 5 次独立 `3×3` 回代。这里加速不显眼；到 1000 相机 / 100k 点就是"装不下 RAM" → "秒级解"。Ceres `bundle_adjustment.cc` 在 5% 随机 init 下 3-pose-5-point 收敛在 4–6 个 LM iter `UNVERIFIED`。

---

## 4 · 工程视角

| 旋钮 | 范围 | 影响 |
|---|---|---|
| N 位姿 | 10–1000 | 主导 U 块 |
| M 点 | 1k–500k | 回代便宜（块对角 V） |
| Iter | 5–20 | 每次一遍 Schur |
| Robust loss | Huber / Cauchy | 降权漏过的 outlier |
| 固定规范 | 第一个位姿 | 否则 7-DoF 自由 → H 奇异 |

**实时 SLAM 用 local BA.** 跑 10k 位姿的 global 要几秒；ORB-SLAM3 的 local BA = ~20 个 covisible 关键帧的滑窗，CPU 上 ~30 ms。VINS-Mono = local BA + IMU residual。

**杀手:** (1) outlier —— RANSAC + robust loss；(2) init 差 —— triangulation + PnP，不要随机；(3) gauge 自由 —— 固定第一个位姿，monocular 再 +1 个 scale；(4) 退化运动 —— 纯旋转让点不可观测。

---

## 5 · BA 出现在哪

| 系统 | 用 BA? | 在哪 |
|---|---|---|
| ORB-SLAM3 | 是 | tracking（motion-only），local mapping（窗口），loop closure（full + PGO） |
| VINS-Mono / Fusion | 是 | 滑窗 + IMU residual（Ceres） |
| OpenVINS | **否**（filter） | EKF 替代 —— 见 `./bayesian_filtering_ekf_msckf.md` |
| COLMAP / SfM | 是 | 离线全局精调 |
| DROID-SLAM | learned BA | 网络内部的可微 GN |
| VGGT forward | **否** | 蒸馏用 BA 做监督 `UNVERIFIED` |

---

## 6 · 失败模式 & Hidden Assumptions

### 6.1 Hidden Assumptions

- **outlier 已 RANSAC 过滤** —— 一个坏对应就能毁掉几百个位姿。
- **噪声 ≈ Gaussian** —— Huber 能处理轻尾；重尾要预滤。
- **规范固定** —— 第一个位姿 +（mono）一条 baseline；否则 H 奇异。
- **线性化是局部的** —— init 要在真值 ~30% 范围内。
- **标定准确** —— `K` 的误差会乘到位姿误差里。
- **静态场景** —— 动态要先 mask 掉。

### 失败特征

| 现象 | 原因 |
|---|---|
| Cost 降一会儿后爆 | LM damping 太激进；outlier 漏过 |
| Solver 立刻返回 | 在 local min；规范没固定 |
| 轨迹"皱缩" | Monocular scale drift；要 Sim(3) / stereo / IMU |
| 500+ 关键帧 OOM | 没用 Schur；该 local 的写了 global |

---

## 7 · 比较 & 面试 Tip

| 方法 | 优 | 缺 | 谁用 |
|---|---|---|---|
| Filter（EKF / MSCKF） | 常数内存、快 | 线性化误差累积 | OpenVINS |
| 优化（BA） | 每 iter 重线性化 | 问题规模会涨 | ORB-SLAM3、COLMAP |
| Learned BA | 可微 | 要训练 | DROID-SLAM |
| Feed-forward | 一次到位、无优化循环 | 非度量 | VGGT、DUSt3R |

> **🎤 Interview Tip.** "为什么 1000 相机 × 100k 点的 BA 能跑？" —— 强答："Hessian 有两块稀疏性 —— 稀疏的相机块、严格块对角的点块、细桥；Schur 把点便宜地边际化掉，因为每个 3×3 子块独立可逆，只剩相机系统。没有 Schur，production 级 BA 根本不可能。" 加分：点出 gauge 自由是 H 奇异的原因，要锚一个位姿。

---

## Boundary

这篇 primer 只覆盖 BA 算法。如需：

- **BA 之后的闭环** → `./pose_graph_optimization.md`
- **被 EKF (MSCKF) 替代的 BA** → `./bayesian_filtering_ekf_msckf.md`
- **ORB-SLAM3 local + global BA 的线程结构** → `foundations/classical-slam/orb_slam3_dissection.md`
- **VINS-Mono 滑窗 BA + IMU** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`
- **VGGT 绕开 BA** → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

## References

- Triggs et al. *Bundle Adjustment — A Modern Synthesis*, LNCS 1883, 2000. The bible.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003. Ch. 18–19.
- Agarwal et al. *Bundle Adjustment in the Large*, ECCV 2010.
- Ceres: http://ceres-solver.org/ · g2o: Kümmerle et al., ICRA 2011.
- ORB-SLAM3: https://github.com/UZ-SLAMLab/ORB_SLAM3
- DROID-SLAM: Teed & Deng, NeurIPS 2021. https://arxiv.org/abs/2108.10869

[← Back to Spatial Math](./overview.md)
