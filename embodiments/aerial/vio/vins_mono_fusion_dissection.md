<!-- ontology-5axis
problem: VI-SLAM (含 loop closure) + GPS fusion
representation: Sparse landmarks + IMU bias + Marginalization prior
sensor: Mono + IMU + GNSS optional
paradigm: Geometric-FactorGraph + Ceres
time: FixedLag-Smoother
ref: ../../../cheat-sheet/ontology.md §7
-->

# VINS-Mono / VINS-Fusion 解构 (VINS-Mono / VINS-Fusion Dissection)

> **发布时间**：2018（T-RO 论文）/ 2019（VINS-Fusion 跟进）
> **论文 / 模型**：VINS-Mono — Qin, Li, Shen（HKUST Aerial Robotics Group）
> **核心定位**：开源单目 VIO 的事实参考实现，把"紧耦合滑窗优化 + IMU 预积分 + Schur 边缘化"打包成无人机能跑的 CPU 预算。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Latency / RMSE figures marked `UNVERIFIED` unless re-measured on the maintainer's rig.
**Paper:** Qin, Li, Shen — *VINS-Mono: A Robust and Versatile Monocular Visual-Inertial State Estimator*, IEEE *T-RO* 2018. arXiv [1708.03852](https://arxiv.org/abs/1708.03852). HKUST Aerial Robotics Group.
**Code:** [HKUST-Aerial-Robotics/VINS-Mono](https://github.com/HKUST-Aerial-Robotics/VINS-Mono), [VINS-Fusion](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion) (mono + stereo + GPS variant).
**TL;DR:** VINS-Mono is the open-source aerial VIO baseline that other stacks are measured against. The three design choices that aged well: **(1)** sliding-window nonlinear optimization over a tightly-coupled factor graph, **(2)** IMU pre-integration as the bridge between visual rates and inertial rates, **(3)** Schur-complement marginalization to bound CPU. The choices that did not age: monocular initialization is fragile, the loop-closure module is an afterthought, and the original code is ROS1 / OpenCV3 vintage.

### X-Ray 开场（非专家友好）

(a) 2017 年前后无人机 VIO 分两派：滤波派（MSCKF）快但发散，优化派（OKVIS）准但吃 CPU。 (b) VINS-Mono 选优化派，靠"滑窗 + 边缘化"压到 10 帧，CPU 不爆且精度领先。 (c) 对 spatial 工程师：它是后来所有开源 VIO 的事实基线——新方法都要先跟它在 EuRoC 上比 RMSE 才进圈子。

### 📍 研究全景时间线

```
MSCKF 2007 ─► OKVIS 2014 ─► ★ VINS-Mono 2017/18 ─► VINS-Fusion 2019 ─► OpenVINS 2020 ─► ORB-SLAM3 2020 ─► DROID-SLAM 2021 ─► VGGT 2025 ─► ?
```

VINS-Mono 把紧耦合滑窗做成无人机 CPU 能跑的形态；后续 VIO 沿用骨架（VINS-Fusion / ORB-SLAM3）或走滤波回头路（OpenVINS）。学界 / 开源仍以它为基准。

---

## 1 · Setup — what HKUST was solving

In 2017, the field had two camps. Filter-based VIO (MSCKF, ROVIO) was fast but suffered from linearization-point drift. Optimization-based VIO (OKVIS) was accurate but heavy. VINS-Mono picked the optimization camp and won the CPU-vs-accuracy argument by **bounding the optimization window aggressively** (10–11 keyframes typical) and **marginalizing the rest into a prior**. Combined with a monocular-only sensor stack — no stereo rig, no LiDAR — it became the cheapest credible aerial VIO open-sourced, and HKUST became the de facto lab.

## 2 · Architecture

> 📌 **Napkin Formula**：`state ≈ argmin Σ(reprojection² + IMU_preint² + marginalization_prior)` over 10-keyframe sliding window，Ceres 解，每 30 Hz 一次，IMU 在两次优化间以 200 Hz 预积分推进。三项残差缺一不可：reprojection 锁 scale-free 方向、IMU 给 metric scale、prior 保留被 marginalize 掉的旧信息。

```
  IMU (200 Hz) ─► pre-integration ─┐
                                   ▼
  Camera (30 Hz) ─► feature track ─► sliding-window nonlinear LS (Ceres)
                                   │
                                   ├─► IMU residual    (pre-integrated Δp, Δv, Δq)
                                   ├─► reprojection    (per-feature, inverse-depth param)
                                   └─► marginalization (Schur-complement prior)
                                   ▼
                          200 Hz state @ IMU prop, 30 Hz update @ optim
                                   │
                                   └─► (optional) loop-closure thread @ ~1 Hz
                                              (DBoW2 retrieval → 4-DoF pose graph)
```

| Component | What it does | Why HKUST chose it |
|---|---|---|
| KLT optical-flow tracker | Per-frame feature association | Avoids descriptor compute on CPU; OK for monocular short baselines |
| IMU pre-integration (Forster et al. style) | Collapses IMU samples between two keyframes into one residual | Decouples optimization rate (30 Hz) from IMU rate (200 Hz) |
| Sliding window (~10 keyframes) | Bounded optimization horizon | CPU stays flat; older info enters prior |
| Inverse-depth feature parameterization | One scalar per feature in window | Linearizes well for points far from camera |
| Schur-complement marginalization | Old keyframes → linear prior on remaining | Information-preserving; key trick for accuracy |
| Loop closure (DBoW2 + 4-DoF pose graph) | Drift correction over minutes | Bolted on; not the strength of the paper |

> ⚡ **Eureka Moment**：**marginalization 不是删除旧帧，而是把它压缩成 Gaussian prior 留在系统里**。删除旧关键帧会破坏 cross-correlation，scale 与 yaw 立刻发散；Schur-complement 把"信息"留下、"变量"去掉——这是滑窗优化能在 CPU 上既稳又准的真正原因，也是 VINS 系列骨架延续 7 年仍是基准的核心理由。

## 2.5 · 玩具例子（Worked Example）— 滑窗一次 update

无人机以 1 m/s 水平直飞 1 秒，IMU 200 Hz、相机 30 Hz、~0.1 s 出一个 keyframe：

- **状态**：10 个 keyframe pose（60 DoF）+ IMU bias（6 DoF）+ ~150 个 active feature inverse-depth ≈ 216 维。
- **IMU 预积分**：相邻 keyframe 间 ~20 IMU 样本 → 压缩成 `(Δp, Δv, Δq)` 三元残差，优化时不再碰原始 IMU。
- **reprojection**：~800 像素残差。
- **Schur 边缘化**：最老 keyframe → `H_new = H_remain − H_cross · H_marg⁻¹ · H_crossᵀ`，~6 维 Gaussian prior。
- **求解**：Ceres ~3 次 Gauss-Newton，CPU ~8–15 ms `UNVERIFIED`。

直觉检查：关掉 prior 重跑，尺度会在 5–10 秒漂走——单目 SfM 没 metric anchor，IMU 信息只能靠 prior "记住"。

## 3 · Why these choices held up

- **Per-feature reprojection over photometric / direct methods.** Reprojection in pixels gives a clean noise model and survives exposure changes. Direct methods (DSO lineage) need photometric calibration that aerial rigs rarely have.
- **Pre-integration as the IMU bridge.** Lets the optimizer move keyframe poses without re-integrating raw IMU samples each iteration. This is the single biggest reason VINS-Mono stays real-time on CPU.
- **Marginalization rather than fixed-lag deletion.** Throwing away old keyframes destroys information; marginalizing them into a Gaussian prior preserves the cross-correlations that matter for scale observability.
- **Monocular-first, stereo-optional.** VINS-Fusion (2019 follow-up) generalizes the same backbone to stereo and stereo+GPS; the core didn't need rewriting.

## 4 · Where it breaks

| Failure mode | Why VINS-Mono breaks | Mitigation |
|---|---|---|
| Fast yaw rate (>200°/s) | KLT tracks fail across large rotations; pre-integration uncertainty grows | Higher-FOV lens, IMU-aided feature predict, or fall back to OpenVINS (better rotational handling) |
| Low-texture indoor (white walls) | Insufficient parallax → feature window degenerates | Add wide-baseline stereo (VINS-Fusion stereo mode) or event camera |
| Aggressive throttle / IMU saturation | Pre-integration assumes accel within ±16 g; racing drones clip | Higher-range IMU (ICM-42605 / ADIS16500-class) `UNVERIFIED` |
| Long traversal without loop closure | Yaw + position drift accumulate (scale-free direction) | Pose-graph back-end (VINS-Fusion's loop-closure module, or external) |
| Init under motion at start | Monocular init needs ~1 s of acceleration variance to recover scale | Stereo init (VINS-Fusion) or warm-start from prior |

EuRoC MAV dataset numbers `UNVERIFIED` from secondary sources: VINS-Mono lands ~0.15 m RMSE on MH01–MH05 indoor trajectories. **Real outdoor / aerial racing numbers are not in the paper** — and that gap is the recurring story in aerial VIO benchmarks.

### 4.y GitHub 实地失败（atlas 联动）

- **GitHub-validated**：VINS-Fusion 招牌 loop closure 长期不可靠 — [VINS-Fusion #3 "global optimization thread doesn't work properly"](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/3) **从 2019 至今仍 open**，官方未修；同 repo PR [#5](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/pull/5) `FeatureManager::triangulate` SVD 疑误也从 2019 挂着，是"学术毕业 + 社区自治"的范式信号
- **GitHub-validated**：VINS-Mono 已 stale（最近 push 2024-08, 293 open issues）— 静止开机即发散（[#475](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/475)·[#473](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/473)），Jetson Nano 直接 crash（[#400](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/400)），ROS 2 port 官方未做；真上无人机 **2026-05 默认推 OpenVINS**，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 4.x · 隐含假设（Hidden Assumptions）

上述失败模式背后的"未明说但必须成立"的假设：

- **充分激励的 init 段**：单目 metric scale 需要 ~1 s 的 accel 方差才能从 IMU 恢复；静止开机直接发散。
- **IMU bias 慢变**：预积分把 bias 当 keyframe 间常量；高动态飞行下 bias 漂移破坏假设。
- **scene 大体静态**：动态物体被 KLT 跟踪后混入 reprojection 残差，没有内置 outlier 模型。
- **充足 feature parallax**：低纹理或纯旋转时滑窗内 feature 三角化退化，inverse-depth 协方差爆炸。
- **rolling-shutter 可忽略**：全局快门假设；rolling shutter + 高角速度会破坏 reprojection geometry。
- **time-sync 子毫秒级**：相机 / IMU 时间戳偏差 >1 ms 直接进入 IMU 预积分误差。
- **载荷振动可由 IMU LPF 滤掉**：螺旋桨基频 / 谐波若进入信号带宽，bias 估计被污染。

任一项不成立时优化仍会收敛，但收敛到错误轨迹——**静默失败是最危险的模式**。

## 5 · Init from IMU pre-integration — the part most readers skim

The monocular init is the hardest part of the paper to internalize. Pure visual SfM gives a structure up to unknown scale. The IMU's gravity-aligned accelerometer gives metric magnitude, but only if you can solve for accelerometer bias, gyro bias, and the gravity direction simultaneously. VINS-Mono's init does this in three steps: **(1)** monocular SfM over the first window without IMU, **(2)** linear alignment of visual motion to IMU pre-integration to recover scale + gravity, **(3)** nonlinear refinement folding biases in. The init fails when accel variance is too low (drone sitting still) — which is why VINS-Mono needs a "wave the drone around" pre-flight ritual that bigger commercial stacks avoid via stereo or wheel odometry priors.

## 6 · When to pick VINS-Fusion vs alternatives

- Pick **VINS-Fusion** when: you want a battle-tested open-source baseline, you can afford a 2+ core CPU budget, you have a stereo rig available, and you want GPS fusion as an option.
- Pick **OpenVINS** when: your CPU budget is one core (1.5 GHz Cortex-A or Jetson Nano), or you need multi-camera with cleaner code architecture. See [openvins_dissection.md](./openvins_dissection.md).
- Pick **DROID-SLAM** when: you have a GPU, your trajectory is hard (textureless / low-light), and you can tolerate 5 Hz state. See [droid_slam_dissection.md](./droid_slam_dissection.md).

**Interview Tip**：被问"为什么 VINS-Mono 至今仍是 baseline 而不是 ORB-SLAM3"——答 **"它把滑窗优化压到 CPU 单核能跑、并把 IMU 预积分 + Schur 边缘化作为开源教科书"**。ORB-SLAM3 精度可能更高，但 VINS-Mono 是后来所有 aerial-VIO 教程、所有 EuRoC 论文复现、所有商业 stack 比对的零点。讲不出 "marginalization 是 information-preserving" 就丢分。

## References

- VINS-Mono — Qin, Li, Shen. *IEEE T-RO* 2018. [arXiv 1708.03852](https://arxiv.org/abs/1708.03852)
- VINS-Fusion stereo + GPS — Qin et al. *arXiv* 2019. [arXiv 1901.03642](https://arxiv.org/abs/1901.03642)
- IMU pre-integration — Forster et al. *T-RO* 2017. [arXiv 1512.02363](https://arxiv.org/abs/1512.02363)
- EuRoC MAV dataset — Burri et al. *IJRR* 2016. (DOI 10.1177/0278364915620033)

## Boundary

This file dissects VINS-Mono / VINS-Fusion mechanics. Comparative trade-offs against MSCKF and learned VIO live in [`crossing/slam-vio-migration/`](../../../crossing/slam-vio-migration/). IMU noise modeling and pre-integration math live in [`foundations/sensor-physics/`](../../../foundations/sensor-physics/) (when written). Real-rig calibration and time-sync procedures live in `deployment/`.
