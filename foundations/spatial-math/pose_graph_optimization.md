# Pose Graph Optimization (PGO, 位姿图优化)

> **发布时间**: 2026-05-21
> **核心定位**: local BA 之后，靠什么闭环、靠什么让 10 公里轨迹保持全局一致。g2o / GTSAM / Ceres 生态都在解同一个问题，只是符号略有不同。

**Status:** v1 —— primer。
**TL;DR:** PGO 等同于 BA 把 landmark 边际化掉：节点 = 位姿，边 = 相对位姿约束（odometry 或 loop）。比完整 BA 小得多；自 ORB-SLAM2 起每一个修漂移 SLAM 的后端都是它。信息矩阵按不确定性给每条约束赋权。

**X-Ray.** SLAM 栈跑滑窗 BA。机器人绕回来、闭环检测触发时，你不能在整个 10 公里轨迹上跑 BA。解法：建图，每个节点是一个位姿，每条边是"我测到了 i 和 j 之间的相对位姿、协方差为 Σ"（odometry 或 loop closure）。优化；漂移向后传播。PGO 比 full BA 更小、更便宜、不如它最优 —— 经典的精度 / 可扩展性 trade-off。（中文直觉：BA 太重；PGO 把 3D 点积分出来，只剩位姿间相对变换 —— 跑得快，能修闭环。）

## 📍 研究全景时间线

```
2006     2011          2012          2014       2021             2026
TORO ►   g2o       ► iSAM2 (Kaess) ► Ceres-PGO ► ORB-SLAM3 Atlas ► YOU ARE HERE
tree-PGO general    incremental                  multi-map PGO    still the back-end
         graph opt  smoothing                                      of every shipping SLAM
```

g2o (2011) 让 PGO 普及；iSAM2 (2012) 加了增量更新；ORB-SLAM3 (2021) 加了 multi-map Atlas，重新定位时合并跨地图边。

---

## 1 · 架构：图的节点与边

### 1.1 组件

- **节点** —— 关键帧位姿 `T_i ∈ SE(3)`（monocular 用 `Sim(3)`）。
- **Odometry 边** —— 顺序的 `T_{i,i+1}`，来自 BA / IMU / wheel，附信息矩阵 `Ω`。
- **Loop 边** —— 非顺序，来自 place recognition（DBoW2 / NetVLAD）。
- **信息矩阵** `Ω = Σ⁻¹` —— 每条边的信任权重。

### 1.2 ⚡ Eureka Moment

> **PGO = 把所有点代数地边际化掉的 BA —— 每个"看到过同一地方"的观测被压缩成一条携带原不确定性向前传递的单一相对位姿约束。**

10k 位姿 + 1M 点的 full BA 在线不可行；10k 位姿 + O(10k) 边的 PGO 是秒级。

### 1.3 图示

```
              loop closure (Ω_loop)
              ┌───────────────────┐
              ▼                   │
   T₀ ── T₁ ── T₂ ── T₃ ── T₄ ── T₅
     odom edges with Ω_ij
```

闭环触发 → 优化器把误差按相对信任权重向后分摊到边上。

---

## 2 · 数学核心：误差定义与最小二乘

### 📌 Napkin Formula

```
e_ij(T_i, T_j) = log(  Z_ij⁻¹ · T_i⁻¹ · T_j  ) ∈ se(3)            ← residual in tangent

min   Σ_(i,j) e_ij(T_i, T_j)ᵀ · Ω_ij · e_ij(T_i, T_j)
{T_i}
```

每条边 `(i, j)` 带一个测得的相对位姿 `Z_ij`。Residual 是"`T_i⁻¹·T_j` 实际在哪，与 `Z_ij` 说它应该在哪的差"，再用 `log` 投到 se(3)。Cost 是以 `Ω_ij` 为信息的 Mahalanobis 范数。

围绕当前估计线性化，Gauss-Newton 一步，重复。机器与 BA 同；但 Hessian 是 `6N × 6N`（无点），比 BA 小得多、稀疏更整齐。

### 稀疏性

`H = JᵀΩJ` 是带状（odometry）+ 几个非对角 entry（loop）。Sparse Cholesky 是 `O(N·b²)`，其中 `b` = 带宽 + loop 数。

### 用 Sim(3) 修 monocular 尺度漂移

Monocular SLAM 在 scale 上漂 —— 轨迹像个螺旋。Strasdat (2010) 说明 loop 约束必须在 `Sim(3)`（7 DoF：旋转 + 平移 + scale）。ORB-SLAM2/3 就这么做。

---

## 3 · 玩具例子：4 个位姿、一条闭环

正方形轨迹 4 个位姿，相邻 odom 各一条，一条 loop `T_0 ↔ T_3`。

```
   T₀ ─── T₁         odom Ω = 100·I (trusted)
   │       │
   T₃ ─── T₂         loop Ω = 50·I (less trusted)
```

真值：边长 1 m 的完美正方形。测得 odom：1 m + 0.05 m 噪声；不闭环时到 `T_3` 已漂 ~0.2 m。Loop 说 `T_3 ≈ T_0`。

PGO 重新分配：每条 odom 边被往回挪 ~0.05 m；loop 边吸收剩下的部分（Ω 50 vs 100，被信任得少）。状态维 24，H 是 24×24，微秒级解出。

**教训:** PGO 不会把误差归零。它把修正按*信息权重比例*分配。如果 loop 比 odom 更被信任，大部分修正落在 odom 边上。

---

## 4 · 工程视角：g2o / GTSAM / Ceres

| 库 | 风格 | 何时用 |
|---|---|---|
| **g2o** | sparse GN、C++、vertex-edge | ORB-SLAM 谱系 |
| **GTSAM** | factor graph、iSAM2 增量 | 研究、Python 绑定 |
| **Ceres** | 通用非线性 LSQ、auto-diff | VINS-Mono 滑窗 |

都在解同一个 `Σ eᵀΩe`；只是 API 不同（vertex+edge / factor graph / residual+param block）。

**iSAM2 (Kaess 2012)** 维护一棵 Bayes tree，只对受影响变量重新线性化。单次更新成本 `O(log N)`，而朴素重解是 `O(N²)` `UNVERIFIED`。

**旋钮:** Ω（按边类型）、闭环边上的 Huber / Cauchy loss（防假阳性 loop）、10–50 次 GN（一般 <20 收敛）、固定第一个节点（gauge）。

**栈位置:** Local BA → 产关键帧位姿 → PGO（带 DBoW2 / NetVLAD 的 loop 边）→ 修正后的位姿。ORB-SLAM3 Atlas 在跨地图 loop 时再加 multi-map 合并。

---

## 5 · 能力与失败模式

| 能 | 不能 |
|---|---|
| 在毫秒级闭公里级 loop | 从错误 loop（place rec 假阳）中恢复 |
| 按不确定性分摊修正 | 避免 loop Ω » odom Ω 的退化 |
| 用 Sim(3) 修 scale | 没有任何 loop 也能恢复 scale |

### 5.1 Hidden Assumptions

- **Loop 检测正确** —— 错 loop 会拽歪整张地图；加 loop 前要 RANSAC + 几何验证。
- **Ω 调好** —— 太不自信 → 什么都同样信任；太自信 → 后来的边静默主导。
- **Gauge 固定** —— 锚定第一个位姿；否则 H 秩亏。
- **图连通** —— 不连通的子图要靠 Atlas 风格合并。
- **噪声局部 Gaussian** —— Robust loss 能帮忙，但重尾（错 loop）要先排除。

### 失败特征

| 现象 | 原因 |
|---|---|
| 闭环后地图被撕开 | 错 loop 通过了验证 |
| Solver 立刻返回 | 在 local min；gauge 没固定 |
| 闭环后 scale 跳变 | 该用 Sim(3)、却用了 SE(3)（monocular） |
| 地图局部 noisy | Ω 没调好 |

---

## 6 · 比较 & 面试 Tip

| 后端 | 优化 | 代价 | 何时用 |
|---|---|---|---|
| Full BA | 位姿 + landmark | 高 | 离线 SfM |
| Local BA | 最近 N 个位姿 + 可见点 | 中 | 在线 tracking |
| PGO | 位姿 + 相对位姿边 | 低 | 在线 loop closure |
| iSAM2 | factor graph、增量 | 极低 | 实时平滑 |

> **🎤 Interview Tip.** "为什么 local BA + global PGO 都要？" —— 强答："Local BA 用还在窗口内的观测做度量级精调；PGO 把一切压缩成相对位姿约束，全局闭环才能在线。每次 loop 就跑 global BA 负担不起；只 PGO 又丢局部度量精度。组合是一种 memory-vs-accuracy trade-off。" 加分：monocular 的 scale drift 用 Sim(3)。

---

## Boundary

这篇 primer 只覆盖 PGO 算法。如需：

- **PGO 之前的带点局部优化** → `./bundle_adjustment.md`
- **SE(3) 切空间更新** → `./se3_so3_lie_groups_primer.md`
- **ORB-SLAM3 Sim(3) 闭环器** → `foundations/classical-slam/orb_slam3_dissection.md`
- **VINS-Mono factor graph + IMU** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`

---

## References

- Kümmerle et al. *g2o: A General Framework for Graph Optimization*, ICRA 2011.
- Kaess et al. *iSAM2: Incremental smoothing via Bayes tree*, IJRR 2012.
- Strasdat et al. *Scale Drift-Aware Large Scale Monocular SLAM*, RSS 2010.
- Grisetti et al. *Tutorial on Graph-Based SLAM*, IEEE ITSM 2010.
- g2o: https://github.com/RainerKuemmerle/g2o · GTSAM: https://gtsam.org/
- ORB-SLAM3: Campos et al. T-RO 2021, https://arxiv.org/abs/2007.11898

[← Back to Spatial Math](./overview.md)
