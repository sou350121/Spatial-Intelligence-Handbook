# Pose & Tracking Primitives (位姿与追踪原语)

> **Region tier:** Foundations · 每个机器人感知栈最终都会糟糕地重建的上游工具箱.
> **Scope:** 三类原语 — **object 6D pose**（这个东西此刻在 3D 中的位置？）+ **motion tracking**（像素 / 点 / object）+ **classical visual tracking**（KCF/CSRT/SiamFC/SAM2 等 SOT 谱系）+ 一篇 [tracking 全景导览 primer](./tracking_taxonomy_primer.md) 拆 "tracking" 这词背后的 7 个不同问题.
> **Status:** v1.2 — 带立场的入口页（2026-05-22 新增 tracking 全景 primer + SORT/ByteTrack MOT + classical visual + Siamese-Transformer SOT，共 4 篇）.

**TL;DR.** 多数机器人 / drone / AD 论文预设三类原语却不点名："我们估计 mug 的 6D pose"、"我们追踪 manipulation episode 内的接触点"、"drone ActiveTrack 锁住目标". 都不免费. 都有 2014–2024 年悄悄变成 table-stakes 的获胜论文. 本区域解构 **8 篇** — FoundationPose、MegaPose、RAFT、CoTracker (+ TAP-Vid)、SORT/ByteTrack MOT、KCF/CSRT classical、Siamese-to-Transformer SOT — 并给你一张 7 家族分类地图.

---

## Tracking 全景：7 种不同问题共用一个名字

| 家族 | 问什么 | 代表 | 本区域文档 |
|---|---|---|---|
| **a** Point / pixel | "这个像素后续 N 帧到哪？" | RAFT, CoTracker | [`raft`](./raft_optical_flow.md), [`cotracker`](./cotracker_and_tap_dissection.md) |
| **b** Feature / classical SOT | "单目标在下一帧位置 (correlation filter)？" | KLT, KCF, CSRT, MOSSE | [`classical_visual`](./classical_visual_tracking_kcf_csrt.md) |
| **b'** Deep SOT (single object) | "单目标 deep template matching" | SiamFC → MixFormer → SAM2 | [`siamese_to_transformer`](./siamese_to_transformer_sot_dissection.md) |
| **c** 2D MOT | "图像所有人 / 车，给每个稳定 ID" | SORT, ByteTrack, OC-SORT | [`sort_bytetrack`](./sort_bytetrack_mot_dissection.md) |
| **d** 3D MOT | "BEV / 点云所有动态对象 + ID" | CenterPoint-track | `embodiments/driving/` |
| **e** 6D pose | "物体当前 (R, t)，跨帧稳定" | FoundationPose, MegaPose | [`foundation_pose`](./foundation_pose_dissection.md), [`megapose`](./megapose_dissection.md) |
| **f** Active | "云台 / 机器人跟随目标（控制回路）" | Skydio ActiveTrack | `embodiments/aerial/active-tracking/` |
| **g** Visual servoing | "图像误差直驱执行器" | IBVS, PBVS | `embodiments/manipulation/` |

详细分类地图 + 决策树 + 公共数学组件 → [`tracking_taxonomy_primer.md`](./tracking_taxonomy_primer.md).

---

## 为什么本区域存在

Manipulation、humanoid、VLA 论文常以两个隐藏假设开篇："给定目标物体的 6D pose…" 和 "我们跨 demonstration 追踪 keypoint…". 两个子句都藏着一个 foundation model. **Object pose** 是几乎每个 grasp planner、peg-in-hole policy、装配 demo 的无名输入. **Point / pixel tracking** 是 optical-flow-conditioned policy、接触推理、ego-motion 估计，以及任何 "看 demo、做 demo" pipeline 的无名输入. 在本区域之前，它们是本手册架子上*缺*的 foundation.

与 feed-forward 3D (`foundations/feed-forward-3d/`) 的关系重要：**VGGT 内部产 2D track** 作为四个输出头之一 — 但它不替代专门 tracker. CoTracker 仍在长时序联合追踪上赢；RAFT 仍在密集低位移流上赢；FoundationPose 仍在 category-free instance pose 上赢. **Feed-forward 3D 把 tracking 作为副产品打包. 本区域解构专家.**

---

## 两个原语家族

### Family A — Object 6D pose（novel-object，无 per-object 训练）

| Tool | Year | Inputs | Output | When to use |
|---|---|---|---|---|
| **[FoundationPose](./foundation_pose_dissection.md)** ⚡ | 2024 CVPR best | RGB-D + (mesh OR ~16 ref imgs) | 6D pose + score | 现代默认. 无 mesh 路径几分钟内 onboard 新 SKU. |
| **[MegaPose](./megapose_dissection.md)** 🔧 | 2022 CoRL | RGB(+D) + mesh | 6D pose | 前驱；render-and-compare baseline. 有 CAD mesh 且想要显式 rejection score 时有用. |

两者皆 *category-free* — 不需要 "这是 mug" 的训练. 这是工业 / 家用 manipulation 的解锁，那里物体长尾击败 per-class 监督.

### Family B — Motion tracking（flow + point tracking）

| Tool | Year | Inputs | Output | When to use |
|---|---|---|---|---|
| **[RAFT](./raft_optical_flow.md)** ⚡ | 2020 ECCV best | 2 consecutive frames | Dense optical flow (HxWx2) | 密集像素级运动场. 2020-2024 主宰 flow leaderboard. |
| **[CoTracker + TAP-Vid](./cotracker_and_tap_dissection.md)** ⚡ | 2024 / 2022 | Video + query points | Per-point trajectory + visibility | 长时序稀疏点追踪. 接触点持续、watch-and-imitate、episode mining. |

**为什么不直接 KLT + SIFT？** 经典稀疏 tracker 独立追踪点*且*逐帧. CoTracker 是*跨时间和跨点联合* — 它跨 query set 同时传播信息，能从会杀死 KLT 的遮挡中恢复. 与 RAFT vs FlowNet 同教训：用迭代精化和跨上下文相关替代 single-shot 估计.

### Family C — 2D Multi-object tracking (MOT)

| Tool | Year | Inputs | Output | When to use |
|---|---|---|---|---|
| **[SORT](./sort_bytetrack_mot_dissection.md)** 📖 | 2016 ICIP | Detector boxes | Per-object ID | 极简鼻祖；Kalman + IoU + 匈牙利，700 行 Python. |
| **[ByteTrack](./sort_bytetrack_mot_dissection.md)** ⚡ | 2022 ECCV | Detector boxes (含 low-conf) | Per-object ID + traj | **2026 工业默认**. MOT17 80.3 MOTA, 30 FPS. 行人 / 车流第一选择. |

**为什么 2D MOT 在本仓?** Tracking 的"对象 + ID"家族在 manipulation 不常用（多用 6D pose），但 drone follow-me / AGV / 安防 / 体育分析全靠它. SORT/ByteTrack 也是理解 "tracking-by-detection" 范式的最佳入口（detector 解耦 → 关联 → ID）.

---

## 推荐阅读顺序

0. **任何 tracking 新人** → 先 **[tracking_taxonomy_primer](./tracking_taxonomy_primer.md)**（7 家族分类地图 + 决策树）.
1. Manipulation / VLA 背景 → **FoundationPose**（对 grasp / peg policy 直接有用）→ **CoTracker**（episode mining 和接触推理）.
2. SLAM / VIO 背景 → **RAFT**（驱动 DROID-SLAM 相关 volume 的原语）→ `foundations/feed-forward-3d/` 中的 **VGGT** 看打包-tracking 变体.
3. 经典 CV 背景 → **MegaPose** 看 render-and-compare 谱系，然后 **FoundationPose** 看 foundation-model 升级.
4. **Drone / AGV / 监控背景** → **[sort_bytetrack_mot_dissection](./sort_bytetrack_mot_dissection.md)**（2D MOT 工业默认）+ `embodiments/aerial/active-tracking/`（控制回路侧）.

---

## Boundary

- **Per-method 解构住这里.** 每个 `*_dissection.md` 遵循 14 项 AGENTS.md 模板.
- **Per-embodiment 用法**（humanoid 实际如何把 FoundationPose 接进其 grasp 栈）→ `embodiments/manipulation/`.
- **Bundled-tracking-inside-3D**（VGGT 的 tracking head、DROID-SLAM 相关 volume）→ `foundations/feed-forward-3d/` 和 `foundations/classical-slam/`.
- **Action 消费**（VLA 如何 condition 在 flow 或 point track 上）→ [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
- **Tracking benchmark**（TAP-Vid、Sintel、KITTI flow）→ `benchmarks/geometry/`.
- **GitHub 失败模式账本**（5 个 pose / tracking 仓库 issue 拼图：mesh / 第一帧 prompt 输入门槛 + memory 限制）→ [`github_failure_atlas.md`](./github_failure_atlas.md)（ecosystem 文档，不走 14 项门槛）.

---

## Cross-region pointers

- VGGT 把 tracking 打包进 3D feed-forward pass: [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)
- 3D feature cloud（per-point descriptor 喂 manipulation policy）: [`../../embodiments/manipulation/3d_feature_cloud_representations.md`](../../embodiments/manipulation/3d_feature_cloud_representations.md)
- VLA action 侧消费: [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

---

*Last opinion update: 2026-05-21. 六篇里维护者首选：**FoundationPose**（manipulation） + **ByteTrack**（2D MOT 工业默认）. 缺前者是 manipulation 栈不更新的信号；缺后者是行人 / 车流团队跟丢了 8 年 baseline.*
