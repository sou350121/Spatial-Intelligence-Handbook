# Depth Models 综合对照 (Depth Models Comprehensive Comparison)

> **发布时间**: 2026-05-22
> **核心定位**: 把 4 个 depth foundation 模型（Depth Anything v2 / Metric3D / MoGe / FoundationStereo）+ 2025-11 新出的 **Depth Anything 3** 在**解释度 / working range / sensitivity / 真实失效**四个轴上做横向对比 —— 选型决策一站式参考。

**Status:** v1 — 基于本仓 4 篇 v1.2 dissection 的实测数据 + WebSearch 验证 (2026-05-22 4-agent 深化结果)。
**TL;DR:** 没有"最好"的 depth model —— 只有**适合你 working range + 失效模式可接受**的 model。**最大教训：所有 mono 模型的 in-the-wild 性能比 benchmark 差一个数量级**；FoundationStereo 没 confidence map；DA v3 (2025-11) 已经把 mono+stereo+multi-view 统一了。

**X-Ray.** 4 个 depth foundation model 各自卡在不同物理 / 输出形式：
- DA v2 是 **affine-invariant inverse depth**（不能直接 grasp）
- Metric3D 是 **米制** 但 in-the-wild 与 benchmark 差 10×
- MoGe 是 **多 head affine-invariant**（MoGe-2 已加 metric）
- FoundationStereo 是 **几何 grounded 米制** 但 **没 confidence map**

更要命的：**Depth Anything 3 已经 (2025-11) 把它们都打到一个 generalist 模型里**，单图 / 立体 / 多视角 / 视频统一 —— 选型矩阵 2026 末可能要重写。

---

## 📍 谱系时间线（2024 → 2026）

```
   2024-04        2024-10           2025-01           2025-07          2025-11           
   ─────────      ─────────         ─────────         ─────────        ─────────         
   Metric3D       MoGe v1           FoundationStereo  MoGe-2           DA 3 ★            
   v2 (TPAMI)     (CVPR Oral)       (CVPR Best        (+metric+        ByteDance Seed,   
   16M imgs       21 datasets       Paper Nom)        normal,          ICLR 2026 Oral    
   米制 zero-shot 99M frames        1M synthetic      手 normal)       any-view          
   ViT-g          多 head           pairs                              generalist        
                                                                       (单图+stereo+      
                                                                       multi-view+视频)   
   
   2024-12        2026-01-23                                                              
   ─────────      ─────────                                                              
   DA v2          MapAnything                                                            
   (LiHe Yong)    (12+ tasks                                                             
   relative       feed-forward                                                           
   inverse        metric)                                                                
   depth                                                                                 
```

⚠️ **2025-11 起谱系正在重整**：DA 3 把 mono / stereo / multi-view 统一到一个 backbone；MapAnything 加 metric scale；MoGe-2 加 metric。**单点 dissection 现在是 *snapshot*，谱系演化太快**。

---

## 表 1 · 输出可解释度（Interpretability）

| 模型 | **输出形式** | **米制?** | **数学定义** | **能直接 grasp 吗?** | **不确定性输出?** |
|---|---|:---:|---|:---:|:---:|
| **DA v2** | affine-invariant inverse depth | ❌ | `D ∝ 1/(a·z + b)` | ❌ (需要 anchor) | ❌ no confidence |
| **Metric3D v2** | metric depth | ✅ | `D_metric = (1/ω_d)·D_canonical`, ω_d=f_c/f | ⚠️ (in-the-wild 419% off) | ❌ no confidence |
| **MoGe v1** | affine-invariant depth + normals + points | ❌ | (scale, Z-shift) 双自由度 | ❌ | ❌ |
| **MoGe-2** (2025-07) | **metric** depth + normals + points | **✅** | 加 metric head | ⚠️ (新论文未实测) | ❌ |
| **FoundationStereo** | metric depth (从 stereo disparity) | ✅ | `Z = f·B/d` 几何 grounded | ✅ (baseline 已知) | ❌ **没 confidence map ★** |
| **DA 3** (2025-11) | depth + ray (any-view) | ✅ (`UNVERIFIED`) | unified depth-ray | ⚠️ (新, 待验证) | `UNVERIFIED` |

&nbsp;

**重大缺口**：**4 个老 model 全部没有 per-pixel confidence map**。下游融合无法 per-pixel 加权，silent failure 风险高。**这是把 "foundation" 标签贴到 production depth model 上最被低估的工程债务**。

&nbsp;

---

## 表 2 · Working Range（米制可信范围）

| 模型 | **近 (0-1m)** | **中 (1-30m)** | **远 (30-100m)** | **超远 (>100m)** | **物理上限** |
|---|---|---|---|---|---|
| **DA v2** | ⚠️ (相对，无 metric) | ✅ 主战场 | ⚠️ (依训练分布) | ❌ sky clip hack | KITTI variant **80m** (训练 ceiling) |
| **Metric3D v2** | ✅ benchmark OK / ⚠️ 实测崩 | ⚠️ **4m 已开始 419% off** | ❌ | ❌ | 室内训练偏，户外 normal 标注 &lt;20K |
| **MoGe v1** | ✅ 近距离强（multi-scale loss）| ✅ 主战场 | ⚠️ sky head 工程 hack | ❌ | sphere scale α=1/64 是 ceiling |
| **MoGe-2** | ✅ + metric | ✅ + metric | `UNVERIFIED` | ❌ | TBD |
| **FoundationStereo** | ✅ (baseline 5cm @ 0.2-3m) | ✅ (baseline 20cm @ 3-30m) | ⚠️ (baseline 60cm @ 20-80m) | ❌ baseline 物理限制 | `ε_Z = Z²·ε_d/(f·B)` 二次律崩 |
| **DA 3** | ✅ unified | ✅ | ✅ vs VGGT pose +44.3% | `UNVERIFIED` | TBD |

&nbsp;

**关键观察**:
- **没有 model 在 >100m 工作**（除非加 active sensing / LiDAR）
- **FoundationStereo 受 baseline 物理硬约束** — 你的 stereo rig baseline 决定 working range，不能软件解决
- **Metric3D 的 "米制" 在 in-the-wild 是个口号**（419% off @ 4m）；只有 NYUv2/KITTI benchmark 上是真米制

&nbsp;

---

## 表 3 · Sensitivity 矩阵（哪个模型对哪种扰动敏感）

> ✅ = 鲁棒 / ⚠️ = 中等 / ❌ = 容易崩

| 扰动类型 | DA v2 | Metric3D | MoGe | FoundationStereo |
|---|:---:|:---:|:---:|:---:|
| **光照变化 / HDR** | ✅ (DINOv2 训出来) | ⚠️ | ⚠️ normal 比 depth 更敏感 | ❌ 两相机曝光不对称 |
| **运动模糊** | ⚠️ | ⚠️ | ⚠️ | ❌ disparity 直接坏 |
| **textureless (白墙/雪)** | ⚠️ | ⚠️ | ⚠️ | ❌ disparity 信号没了 |
| **透明 / 镜面** | ✅ DA-2K transparent_reflective +10% vs Marigold | ❌ | ⚠️ | ❌ |
| **遮挡 / partial visibility** | ✅ | ⚠️ | ⚠️ 三 head 内部不一致 | ❌ 左右目看不到同物 |
| **重复纹理 (栅栏/砖墙)** | ✅ | ✅ | ✅ | ❌ disparity aliasing |
| **calibration drift** | n/a (单目) | n/a | n/a | ❌ drone ~0.024m/m flown |
| **>30°C 热漂移** | n/a | n/a | n/a | ❌ +12% disparity error |
| **OOD (水下/太空/微观)** | ❌ | ❌ | ❌ | ❌ |
| **synthetic→real gap** | ✅ (62M unlabeled) | ⚠️ 16M 标注偏 indoor | ✅ 21 datasets | ❌ 1M 合成 → real gap 大 |

&nbsp;

**Sensitivity 一句话总结**:
- **DA v2 最鲁棒**：DINOv2 + 62M unlabeled distillation 给最广 invariance
- **Metric3D 最脆**：训练偏室内 + canonical assumption 严格
- **MoGe 内部不一致 risk**：3 head 各自对扰动反应不同
- **Stereo 是 fragile 几何**：6 类失败源，calibration drift 是 #1

&nbsp;

---

## 表 4 · Benchmark 数字（NYUv2 zero-shot）

| 模型 | **NYUv2 AbsRel** | **NYUv2 δ₁** | **KITTI AbsRel** | **KITTI RMS (m)** | 备注 |
|---|---|---|---|---|---|
| DA v2-L | 0.074 | 0.946 | — | — | relative, 不直接比 metric |
| Metric3D v2 (ViT-g) | **0.067** | — | **0.051** | **2.403** | benchmark 最强 metric, 但 in-the-wild 419% off |
| MoGe v1 | — | — | point error **6.43** | (vs 9.86 baseline) | 21 datasets 平均 |
| MoGe-2 | `UNVERIFIED` | — | — | — | 2025-07 新出 |
| FoundationStereo | — | — | — | &lt;2% @ 2m (D435 实测) | Middlebury+ETH3D 1st |
| DA 3 | `UNVERIFIED` | — | — | — | vs VGGT pose **+44.3%**, geo **+25.1%** |

⚠️ **Benchmark 数字 ≠ 实际**。Metric3D NYUv2 AbsRel=0.067 但 in-the-wild 4m 实距给 20.7m（419% off）—— **benchmark 与生产环境差一个数量级**。

&nbsp;

---

## 表 5 · In-the-Wild Reality Check（生产环境真实失效）

| 模型 | **Benchmark 漂亮指标** | **In-the-Wild 现实** | Source |
|---|---|---|---|
| **DA v2** | NYUv2 AbsRel 0.074 | OK in distribution; 透明/镜面 robust (+10% vs Marigold) | DA-2K bench |
| **Metric3D v2** | KITTI AbsRel 0.051 | **4m 实距 → ViT-L 给 20.7m (419% off) ★** | GitHub Issue #161 一手实测 |
| **Metric3D v2** | ViT-L > ViT-S 在 benchmark | **远端 ViT-L 反而比 ViT-S 更差 ★** | 同上 (违反直觉) |
| **MoGe v1** | 21 datasets 平均强 | sky region 是工程 clip hack | 论文 §6 承认 |
| **FoundationStereo** | Middlebury+ETH3D 1st | **没有 confidence map / occlusion mask ★** | GitHub repo |
| **FoundationStereo** | 实验室 &lt;2% @ 2m | drone ~0.024m/m flown calibration drift | 推测 |

&nbsp;

**生产环境 3 大坑**:
1. **Mono depth in-the-wild 比 benchmark 差 10× —— 永远 vicon 验证一次**
2. **更大模型不保证远端更好** （ViT-L 在 Metric3D 远端不如 ViT-S）
3. **没 confidence map 的 stereo 是 silent failure 高危**

&nbsp;

---

## 表 6 · 选型决策矩阵（一眼选）

```
   你的应用场景 → 推荐模型
   ─────────────────────────────────────────────────────────────────────────
   
   1. Manipulation grasp (≤1m, 要米制, manipulation arm)
       └─► **FoundationStereo** (几何 grounded) + RGBD (D435)
           (Metric3D in-the-wild 不可靠, MoGe-2 仍待验证)
   
   2. Drone obstacle avoidance (1-30m, drone, 要米制)
       └─► **FoundationStereo** (Skydio baseline 20cm @ 3-30m)
           + IMU fusion in EKF
   
   3. AD perception (5-200m, 要远距离米制)
       └─► **不要用 mono / FFstereo**, 用 LiDAR + Radar + 多目 stereo BEV
           (mono in-the-wild 100m 全部崩)
   
   4. 离线高质量 3D reconstruction (无米制要求)
       └─► **MoGe-2** (multi-task + 加 metric head) 或 DA 3 (unified)
   
   5. 单目 depth augmentation (训练数据生成, no metric)
       └─► **DA v2** (DINOv2 鲁棒, 透明/镜面友好)
   
   6. Multi-view 大规模 SfM
       └─► **DA 3** (2025-11 新出, vs VGGT 几何 +25.1%) 或 MapAnything
   
   7. Production VIO front-end depth
       └─► 仍是 classical stereo + ORB-SLAM3 / VINS-Fusion
           (foundation depth model latency 太重, 200 Hz aerial 上不了)
```

&nbsp;

---

## 重大教训汇总

### 🔥 教训 1: 米制是 production 第一杀手

**Metric3D 的 "米制" 在 benchmark 上真，in-the-wild 是 419% off**。任何 production deployment 必须：
1. vicon 验证一次 metric accuracy
2. 测量在你的 working range 上的 actual error vs benchmark error
3. 准备 fallback（stereo / LiDAR）

### 🔥 教训 2: 模型越大不保证 working range 越远

ViT-L > ViT-S 在 benchmark，但 **Metric3D ViT-L 在 4m 远距离反而比 ViT-S 更差**（419% vs 186%）。大模型在 OOD distribution 上未必更稳。

### 🔥 教训 3: 没 confidence map 是 silent failure

**FoundationStereo 全公开版本无 confidence**。下游融合无 per-pixel 权重，failure 模式悄悄渗透到 SLAM 后端。Production 必须自己加 sanity check（disparity gradient / occlusion mask）。

### 🔥 教训 4: 谱系演化太快

- **MoGe v1 → v2 (2024-10 → 2025-07)** = 加 metric + normal head ✅ 已落地
- **DA v2 → v3 (2024-12 → 2025-11)** = unified mono+stereo+multi-view ✅ 已落地
- **VGGT → MapAnything → VGGT-Ω** = 12-tasks unified + metric + efficient

**单点 dissection 是 snapshot**。Production 选型时务必查最新 release，2025-2026 的 depth foundation 谱系每 3-6 月有大变。

---

## Boundary

- DA v2 完整 dissection → [`./depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- Metric3D 完整 dissection → [`./metric3d_dissection.md`](./metric3d_dissection.md)
- MoGe 完整 dissection → [`./moge_dissection.md`](./moge_dissection.md)
- FoundationStereo 完整 dissection → [`./foundationstereo_dissection.md`](./foundationstereo_dissection.md)
- VGGT / VGGT-Ω / MapAnything (feed-forward 3D 视角，含 depth) → [`../feed-forward-3d/README.md`](../feed-forward-3d/overview.md)
- Stereo geometry physics → [`../sensor-physics/stereo_camera_geometry_physics.md`](../sensor-physics/stereo_camera_geometry_physics.md)
- RGB 相机物理 (latest) → [`../sensor-physics/rgb_camera_imaging_pipeline.md`](../sensor-physics/rgb_camera_imaging_pipeline.md)
- 跨 embodiment depth 选型对比 → [`../../crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md`](../../crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md)

---

## References (最新, 2025-2026)

- **Depth Anything v2** — Yang et al. 2024-06 · [arXiv 2406.09414](https://arxiv.org/abs/2406.09414) · [GitHub LiheYoung/Depth-Anything-V2](https://github.com/LiheYoung/Depth-Anything-V2)
- **Depth Anything 3** — ByteDance Seed 2025-11-14 · [arXiv 2511.10647](https://arxiv.org/abs/2511.10647) · **ICLR 2026 oral** · any-view generalist
- **Metric3D v2** — Yin et al. 2024 · [arXiv 2404.15506](https://arxiv.org/abs/2404.15506) · IEEE TPAMI 2024
- **MoGe v1** — Wang et al. 2024-10 · [arXiv 2410.19115](https://arxiv.org/abs/2410.19115) · CVPR 2025 Oral
- **MoGe-2** — Wang et al. 2025-07 · [arXiv 2507.02546](https://arxiv.org/abs/2507.02546) · 加 metric + normal
- **FoundationStereo** — NVIDIA Research 2025 · [arXiv 2501.09898](https://arxiv.org/abs/2501.09898) · CVPR 2025 Best Paper **Nomination**
- DA-2K transparent/reflective bench — DA v2 supplementary
- Metric3D GitHub Issue #161 — 一手 in-the-wild 实测对照

---

[← Back to Depth Foundation](./overview.md)
