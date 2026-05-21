# Pose Graph Optimization (PGO, 位姿图优化)

> **发布时间**: 2026-05-21
> **核心定位**: After local BA, what closes the loop and keeps a 10-km trajectory globally consistent. The g2o / GTSAM / Ceres ecosystem all solve the same problem in slightly different notation.

**Status:** v1 — primer.
**TL;DR:** PGO is BA with landmarks marginalised out: nodes = poses, edges = relative-pose constraints (odometry or loop). Much smaller than full BA; the back-end of every drift-correcting SLAM since ORB-SLAM2. Information matrices weight each constraint by uncertainty.

**X-Ray.** A SLAM stack runs BA over a sliding window. When the robot loops back and the detector fires, you cannot run BA over the whole 10-km trip. Solution: a graph where each node is a pose, each edge is "I measured the relative pose between i and j with covariance Σ" (odometry or loop closure). Optimize; drift propagates backward. PGO is smaller, cheaper, less optimal than full BA — the classical accuracy / scalability trade. (中文直觉：BA 太重；PGO 把 3D 点积分出来，只剩位姿间相对变换 — 跑得快，能修闭环。)

## 📍 研究全景时间线

```
2006     2011          2012          2014       2021             2026
TORO ►   g2o       ► iSAM2 (Kaess) ► Ceres-PGO ► ORB-SLAM3 Atlas ► YOU ARE HERE
tree-PGO general    incremental                  multi-map PGO    still the back-end
         graph opt  smoothing                                      of every shipping SLAM
```

g2o (2011) made PGO ubiquitous; iSAM2 (2012) added incremental updates; ORB-SLAM3 (2021) added multi-map Atlas with inter-map edges that merge on relocalisation.

---

## 1 · Architecture: graph nodes and edges

### 1.1 Components

- **Nodes** — keyframe poses `T_i ∈ SE(3)` (or `Sim(3)` for monocular).
- **Odometry edges** — sequential `T_{i,i+1}` from BA / IMU / wheels, with information `Ω`.
- **Loop edges** — non-sequential, from place-recognition (DBoW2 / NetVLAD).
- **Information matrix** `Ω = Σ⁻¹` — weights edge trust.

### 1.2 ⚡ Eureka Moment

> **PGO = BA with all points algebraically marginalised — every "saw the same place" observation compresses into a single relative-pose constraint with an info matrix carrying the original uncertainty forward.**

Full BA over 10k poses + 1M points is impossible online; PGO over 10k poses + O(10k) edges is seconds.

### 1.3 Graph diagram

```
              loop closure (Ω_loop)
              ┌───────────────────┐
              ▼                   │
   T₀ ── T₁ ── T₂ ── T₃ ── T₄ ── T₅
     odom edges with Ω_ij
```

Loop fires → optimizer redistributes the discrepancy backward across edges, weighted by relative trust.

---

## 2 · Math core: error definition and least-squares

### 📌 Napkin Formula

```
e_ij(T_i, T_j) = log(  Z_ij⁻¹ · T_i⁻¹ · T_j  ) ∈ se(3)            ← residual in tangent

min   Σ_(i,j) e_ij(T_i, T_j)ᵀ · Ω_ij · e_ij(T_i, T_j)
{T_i}
```

Each edge `(i, j)` carries a measured relative pose `Z_ij`. The residual is "where T_i⁻¹·T_j actually is vs where Z_ij said it should be", projected into se(3) via `log`. The cost is the Mahalanobis norm with information `Ω_ij`.

Linearise around current estimate, Gauss-Newton step, repeat. Same machinery as BA — but the Hessian is `6N × 6N` (no points), much smaller and more sparsely populated than BA.

### Sparsity

`H = JᵀΩJ` is banded (odometry) + a few off-diagonal entries (loops). Sparse Cholesky is `O(N·b²)` where `b` = bandwidth + loop count.

### Sim(3) for monocular scale drift

Monocular SLAM drifts in scale — trajectory looks like a corkscrew. Strasdat (2010) showed the loop constraint must be in `Sim(3)` (7 DoF: rotation + translation + scale). ORB-SLAM2/3 does this.

---

## 3 · Worked example: 4 poses, triangle with one loop closure

4 poses in a square trajectory, odom between consecutive pairs, one loop `T_0 ↔ T_3`.

```
   T₀ ─── T₁         odom Ω = 100·I (trusted)
   │       │
   T₃ ─── T₂         loop Ω = 50·I (less trusted)
```

Truth: 1 m sides, perfect square. Measured odom: 1 m + 0.05 m noise; unclosed trajectory drifts ~0.2 m by `T_3`. Loop says `T_3 ≈ T_0`.

PGO redistributes: every odom edge nudges ~0.05 m back; loop absorbs the rest (Ω 50 vs 100, less trusted). State dim 24, H is 24×24, solves in microseconds.

**Lesson:** PGO does not zero the error. It distributes correction *proportional to information weights*. If loop is more trusted than odom, most correction lands on odom edges.

---

## 4 · Engineering view: g2o / GTSAM / Ceres

| Lib | Style | When |
|---|---|---|
| **g2o** | sparse GN, C++, vertex-edge | ORB-SLAM lineage |
| **GTSAM** | factor graph, iSAM2 incremental | research, Python bindings |
| **Ceres** | general non-linear LSQ, auto-diff | VINS-Mono sliding-window |

All solve the same `Σ eᵀΩe`; only the API differs (vertices+edges / factor graph / residual+param blocks).

**iSAM2 (Kaess 2012)** maintains a Bayes tree, re-linearising only affected variables. Cost per update `O(log N)` instead of `O(N²)` for naïve re-solve `UNVERIFIED`.

**Knobs:** Ω (per edge type), Huber / Cauchy loss on loop edges (guards false positives), 10–50 GN iters (converges <20), fix first node (gauge).

**Stack location:** Local BA → emits keyframe poses → PGO (with loop edges from DBoW2 / NetVLAD) → corrected poses. ORB-SLAM3 Atlas adds multi-map merging on cross-map loops.

---

## 5 · Capabilities & failure modes

| Can | Can't |
|---|---|
| Close km-scale loops in ms | Recover from wrong loop (place-rec false positive) |
| Uncertainty-aware redistribution | Avoid degeneracy if loop Ω » odom Ω |
| Sim(3) scale correction | Recover scale without ever firing a loop |

### 5.1 Hidden Assumptions

- **Loop detection correct** — wrong loop pulls the entire map; RANSAC + geometric verification before adding edge.
- **Ω tuned** — under-confident → trusts everything equally; over-confident → late edges dominate silently.
- **Gauge fixed** — first pose anchored; else H rank-deficient.
- **Graph connected** — disconnected subgraphs need Atlas-style merging.
- **Noise locally Gaussian** — robust loss helps, but heavy tails (wrong loops) need pre-rejection.

### Failure signatures

| Symptom | Cause |
|---|---|
| Loop closes, map tears | Wrong loop passed verification |
| Solver returns immediately | At local min; gauge unfixed |
| Scale jumps after loop | Sim(3) needed, used SE(3) (monocular) |
| Map locally noisy | Ω untuned |

---

## 6 · Comparison & Interview Tip

| Back-end | Optimizes | Cost | Use when |
|---|---|---|---|
| Full BA | poses + landmarks | high | offline SfM |
| Local BA | recent N poses + visible pts | medium | online tracking |
| PGO | poses + relative-pose edges | low | online loop closure |
| iSAM2 | factor graph, incremental | very low | real-time smoothing |

> **🎤 Interview Tip.** "Why both local BA and global PGO?" — strong answer: "Local BA gives metric refinement over recent observations with points still in scope; PGO compresses everything into relative-pose constraints so global loop closure stays online. Global BA every loop is unaffordable; PGO-only loses local metric accuracy. Combination is a memory-vs-accuracy trade." Bonus: Sim(3) for monocular scale drift.

---

## Boundary

This primer covers the PGO algorithm. For:

- **Pre-PGO local opt with points** → `./bundle_adjustment.md`
- **SE(3) tangent updates** → `./se3_so3_lie_groups_primer.md`
- **ORB-SLAM3 Sim(3) loop closer** → `foundations/classical-slam/orb_slam3_dissection.md`
- **VINS-Mono factor graph + IMU** → `embodiments/aerial/vio/vins_mono_fusion_dissection.md`

---

## References

- Kümmerle et al. *g2o: A General Framework for Graph Optimization*, ICRA 2011.
- Kaess et al. *iSAM2: Incremental smoothing via Bayes tree*, IJRR 2012.
- Strasdat et al. *Scale Drift-Aware Large Scale Monocular SLAM*, RSS 2010.
- Grisetti et al. *Tutorial on Graph-Based SLAM*, IEEE ITSM 2010.
- g2o: https://github.com/RainerKuemmerle/g2o · GTSAM: https://gtsam.org/
- ORB-SLAM3: Campos et al. T-RO 2021, https://arxiv.org/abs/2007.11898

[← Back to Spatial Math](./README.md)
