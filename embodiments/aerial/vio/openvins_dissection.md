# OpenVINS 解构 (OpenVINS Dissection)

> **发布时间**：2019（arXiv）/ 2020（ICRA）
> **论文 / 模型**：OpenVINS — Geneva, Eckenhoff, Lee, Yang, Huang（U. Delaware RPNG）
> **核心定位**：把商用无人机里跑了十年的 MSCKF 滤波 VIO 写成干净的开源参考，证明"单核 CPU + 多相机 + 在线标定"在 2020 年代仍能击败优化派。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. CPU / RMSE figures marked `UNVERIFIED` unless re-measured.
**Paper:** Geneva, Eckenhoff, Lee, Yang, Huang — *OpenVINS: A Research Platform for Visual-Inertial Estimation*, IEEE ICRA 2020. arXiv [1910.00298](https://arxiv.org/abs/1910.00298). University of Delaware (RPNG lab).
**Code:** [rpng/open_vins](https://github.com/rpng/open_vins). BSD-3.
**TL;DR:** OpenVINS is the modern open-source MSCKF — a filter-based VIO that beats sliding-window optimization (VINS-Fusion) on CPU budget at comparable accuracy. The two design choices that matter: **(1)** MSCKF marginalizes features out of the state (no per-feature state bloat), **(2)** First-Estimates Jacobian (FEJ) freezes linearization points to recover the observability properties a naive EKF destroys. Skydio-adjacent lineage — RPNG alumni populate Skydio's autonomy team, and the design biases (single-core viable, multi-camera clean) match what shipped commercially.

### X-Ray 开场（非专家友好）

(a) 大多数学界 VIO 论文（VINS-Mono、ORB-SLAM3）走滑窗优化，准但吃 2+ CPU 核。 (b) OpenVINS 走滤波派 MSCKF：feature 不进 state、用 null-space projection 一次性 marginalize 掉，单核就能跑、多相机原生支持。 (c) 对 spatial / 具身工程师：这是商用无人机自治栈（Skydio、早期 DJI `UNVERIFIED`）的开源近似——读懂它就懂为什么"学界用优化、工业用滤波"持续到 2026。

### 📍 研究全景时间线

```
MSCKF 2007 (Mourikis) ─► MSCKF 2.0 / FEJ 2008–2014 (Huang/RPNG) ─► ROVIO 2015 ─► ★ OpenVINS ICRA 2020 ─► (商用栈持续在用)
                              │                                                              │
                              └─► 解决 naive EKF 的 observability bug                          └─► 学界焦点转向 DROID-SLAM / VGGT 等学习派
```

OpenVINS 是 MSCKF 谱系的 reference implementation——把 14 年的 RPNG 工程积累（FEJ、stochastic cloning、null-space projection、在线标定）汇成一份能编译能跑的代码。学界注意力转向学习派，但商用栈仍按 MSCKF 配方走。

---

## 1 · Setup — why MSCKF matters in 2026

By 2020 the field had split. The academic mainstream (VINS-Mono, OKVIS, ORB-SLAM3) had gone optimization. The commercial mainstream (Google ARCore, Apple ARKit, Skydio, much of DJI's flight stack `UNVERIFIED`) had stayed filter-based. The reason is unglamorous: **a tuned MSCKF runs on a single 1.5 GHz CPU core and stays under 5 ms per frame** `UNVERIFIED`, while VINS-Fusion needs 2+ cores at the same accuracy. On a drone where the same SoC is also running attitude control, ESC telemetry, video encoding, and a radio stack, that delta is the difference between "ships" and "doesn't."

OpenVINS open-sourced the MSCKF design that had been folklore in the commercial space since Mourikis & Roumeliotis 2007. It is the cleanest reference implementation of a filter-based VIO that the academic community has produced.

## 2 · Architecture

> 📌 **Napkin Formula**：`state = [IMU 15 DoF | N pose clones × 6 DoF]`，**feature 不在 state**；feature 观测通过 `H · null(Hf) = 0` 投到 feature-orthogonal 子空间，得到 feature-free 残差喂给 EKF update。Jacobian 用每个变量的 first-estimate 计算（FEJ），保 4 维不可观方向（global yaw + 3D position）真的不可观。

```
  IMU (200 Hz) ─► state propagation (EKF predict step)
                       │
                       ▼
   ┌────────────────────────────────────────┐
   │  Filter state = [IMU state | clone window of past poses]│
   │  Features are NOT in the state         │
   └────────────────────────────────────────┘
                       │
  Camera (30 Hz) ─► track features, accumulate observations
                       │
                       ▼
  When a feature is "ready" (lost / window full):
     1. Triangulate feature from the clone window observations
     2. Null-space project observations to eliminate feature
     3. EKF update with the null-space residual
     4. (Optional) marginalize oldest clone, slide window forward
                       │
                       ▼
              200 Hz state @ IMU propagation
```

| Component | What it does | Why MSCKF wins |
|---|---|---|
| Stochastic clone window | Past N camera poses live in state | Enables triangulation without persistent feature states |
| Null-space projection | Project feature observations to space orthogonal to feature position | Eliminates feature state algebraically; preserves info |
| EKF update (not full BA) | Single linearization point per step | O(state³) but state stays small (~20 clones × 6 DoF) |
| First-Estimates Jacobian (FEJ) | Linearize about first-time estimate, not current | Recovers the 4 unobservable directions (global yaw + 3D position) |
| Multi-camera + IMU bay | Per-camera intrinsics / extrinsics in state | Online calibration; matches multi-cam aerial rigs |

> ⚡ **Eureka Moment**：**feature null-space projection 让 EKF 既得到 feature 信息又不付 feature state 代价**。把 feature observation 投到 feature-orthogonal 子空间后，feature 变量被代数消去，残差仍含 pose-side 信息——这是 MSCKF 能在单核上跑 50 帧 / 多相机的真正杠杆。FEJ 是修 bug，null-space projection 才是创新内核。

## 2.5 · 玩具例子（Worked Example）— 单 feature 的一次 update

5 个 clone（30 DoF）+ IMU 15 DoF = **45 维 state**，一个 feature 在 5 帧都被看到：

- **观测**：10 维残差 `r`；Jacobian 拆 `H_x`（45 列）+ `H_f`（3 列）。
- **三角化**：5 个 clone 反投影出 `pf`。
- **null-space projection**：`N = null(H_f)`（10×7，因 `H_f` 秩 3），左乘 `Nᵀ` → 7 维 feature-free 残差。
- **gating + update**：chi-squared 过门后 `K = P H_x'ᵀ (H_x' P H_x'ᵀ + R)⁻¹`。
- **CPU**：单 feature ~50 μs `UNVERIFIED`；50 features ≈ 2.5 ms / frame。

直觉：naive EKF 把 feature 也放进 state → 维度 45 + 3N_feat，求逆 O((45+3N)³) 立即爆。MSCKF 的 "feature 不进 state" 是直接收益。

|  | MSCKF (OpenVINS) | Sliding-window opt (VINS-Fusion) |
|---|---|---|
| CPU budget | 1 core @ 1.5 GHz viable `UNVERIFIED` | 2+ cores `UNVERIFIED` |
| Memory | ~MB-scale state vector | ~MB Ceres problem + Hessian |
| Accuracy on EuRoC | within 10–20% of VINS-Fusion `UNVERIFIED` | reference |
| Latency per frame | 2–5 ms `UNVERIFIED` | 8–15 ms `UNVERIFIED` |
| Re-linearization | Once per measurement (FEJ frozen) | Many iterations per window |
| Loop closure | external (pose graph thread) | built-in (DBoW2) |
| Multi-camera | first-class | bolted on |
| Code complexity | high (filter algebra) | moderate (Ceres handles it) |

The honest read: MSCKF wins when CPU is the constraint, optimization wins when accuracy on hard trajectories is the constraint. **For aerial production, CPU is almost always the constraint** — which is why the commercial stacks went filter.

## 4 · The FEJ trick — why naive EKF VIO does not work

Standard EKF VIO has a known bug: the linearization point of the state estimate changes every step, which couples observability with estimator-state-history. In practice the filter develops a phantom observability of global yaw and global 3D position — directions that are physically unobservable from camera + IMU alone. This causes optimistic covariance, inconsistent uncertainty estimates, and eventual divergence on long trajectories.

**FEJ (First-Estimates Jacobian)** fixes this by freezing the linearization point of each state variable to its first-ever estimate. Jacobians get computed at frozen points; mean updates still use the current estimate. The math is unglamorous (Huang, Mourikis, Roumeliotis 2008) but the result is the difference between "ships" and "drifts in 30 seconds." OpenVINS implements FEJ cleanly enough that it became the reference for how to do it.

## 5 · When to pick OpenVINS vs VINS-Fusion

| Pick **OpenVINS** when | Pick **VINS-Fusion** when |
|---|---|
| Single-core CPU budget (BeagleBone, Raspberry Pi, Jetson Nano shared with other workloads) | 2+ cores available |
| Multi-camera rig (front + down + side) | Single camera or stereo |
| You need online intrinsic / extrinsic calibration | You can offline-calibrate |
| Long-horizon consistency matters more than peak accuracy | Peak accuracy on EuRoC-style trajectories matters more |
| You want clean code structure for research extension | You want the most-forked baseline |

The Skydio-adjacent comment is not idle — multiple RPNG alumni (Geneva, Eckenhoff, others) ended up at Skydio or comparable autonomy outfits, and the design biases visible in OpenVINS (clean multi-camera support, online calibration, single-core target) are the design biases a commercial drone autonomy stack would actually want. The paper reads like a sanitized academic version of what shipped in 2017–2019 era commercial drones.

## 6 · Failure modes specific to MSCKF

- **Outlier features are catastrophic** — without an optimization loop to re-linearize, one bad triangulation pollutes the update. OpenVINS leans hard on chi-squared gating; tune carefully.
- **Init still hard** — MSCKF init has the same monocular-scale problem as VINS-Mono. The fix is identical (motion variance + linear alignment).
- **Loop closure has to be external** — the filter has no native loop-closure concept. You bolt on a pose-graph back-end (often borrowed from VINS-Fusion or ORB-SLAM3).
- **Filter divergence under fast yaw** — same KLT track failure as VINS-Mono, but the filter has less recovery margin than an optimizer with multiple Gauss-Newton iterations.

### 6.y GitHub 实地失败（atlas 联动）

- **GitHub-validated**：OpenVINS 是 **aerial VIO 区唯一仍正常维护的官方 repo**（最近 push 2025-11，68 open issue，maintainer 回复活跃）— issue 多在自录数据 / 边缘硬件而非算法本身：filter divergence after init（[#540](https://github.com/rpng/open_vins/issues/540)·[#533](https://github.com/rpng/open_vins/issues/533)），static init fail（[#477](https://github.com/rpng/open_vins/issues/477)），Orin Nano segfault（YAML 与 IMU 实际采样率不匹配，[#514](https://github.com/rpng/open_vins/issues/514)），100 m 高度大尺度 parallax 退化（[#513](https://github.com/rpng/open_vins/issues/513)），multi-cam online calib 实际门槛比文档高（[#534](https://github.com/rpng/open_vins/issues/534)·[#505](https://github.com/rpng/open_vins/issues/505)）；**2026-05 aerial VIO 默认推 OpenVINS**（VINS-Fusion #3 long-open / VINS-Mono stale），详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 6.x · 隐含假设（Hidden Assumptions）

- **outlier 已被 chi-squared 滤干净**：单线性化 EKF 无 re-linearize，outlier 直接污染 covariance。
- **feature triangulation 收敛**：clone 窗口 baseline 太小 → 反投影退化。
- **IMU bias 可线性化**：长静止 + FEJ 冻结点 → Jacobian 失效。
- **IMU 噪声白噪声 + bias random-walk**：振动 / 温漂破坏假设。
- **time-sync 已标定**：sync 偏差直接拉偏 yaw。
- **clone 窗口 N 与机动匹配**：N 太小 → 反投影差；N 太大 → state 膨胀。
- **multi-cam online-calib 收敛**：外参标定靠 motion excite；纯前飞无 yaw 不可观。

Skydio 商用栈把这些外化为 "pre-flight wiggle"；学界跑 EuRoC 隐式满足、迁真机即暴露。

**Interview Tip**：被问"为什么工业界用滤波不用优化"——答 **"单核 CPU 预算 + 多相机原生 + 在线标定 + FEJ 修好了 observability"**。再加一句"OpenVINS 不是更准，是更省"。能讲出 null-space projection 是 feature 消去而非 feature 忽略，加分。

## References

- OpenVINS — Geneva et al. *ICRA 2020*. [arXiv 1910.00298](https://arxiv.org/abs/1910.00298)
- Original MSCKF — Mourikis & Roumeliotis. *ICRA 2007*. (DOI 10.1109/ROBOT.2007.364024)
- FEJ EKF consistency — Huang, Mourikis, Roumeliotis. *IJRR* 2008.

## Boundary

This file dissects OpenVINS / MSCKF mechanics. Cross-stack comparison (filter vs optimization) at the cross-embodiment level lives in [`crossing/slam-vio-migration/`](../../../crossing/slam-vio-migration/). VINS-Fusion specifics live in [`vins_mono_fusion_dissection.md`](./vins_mono_fusion_dissection.md). Commercial-stack engineering ([`companies/skydio.md`](../../../companies/) when written) lives elsewhere.
