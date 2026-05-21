# Pose & Tracking Primitives (位姿与追踪原语)

> **Region tier:** Foundations · 每个机器人感知栈最终都会糟糕地重建的上游工具箱.
> **Scope:** 两个原语家族 — **object 6D pose**（这个东西此刻在 3D 中的位置？）和 **motion tracking**（这个像素 / 点在帧间移到哪？）.
> **Status:** v1 — 带立场的入口页.

**TL;DR.** 多数机器人论文预设两个原语却不点名："我们估计 mug 的 6D pose" 和 "我们追踪 manipulation episode 内的接触点". 都不免费. 都有 2022–2024 年悄悄变成 table-stakes 的获胜论文. 本区域解构其中四个 — FoundationPose、MegaPose、RAFT、CoTracker (+ TAP-Vid) — 并告诉你何时用哪个.

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

---

## 推荐阅读顺序

1. Manipulation / VLA 背景 → 先 **FoundationPose**（对 grasp / peg policy 直接有用）→ **CoTracker**（episode mining 和接触推理）.
2. SLAM / VIO 背景 → 先 **RAFT**（驱动 DROID-SLAM 相关 volume 的原语）→ `foundations/feed-forward-3d/` 中的 **VGGT** 看打包-tracking 变体.
3. 经典 CV 背景 → 先 **MegaPose** 看 render-and-compare 谱系，然后 **FoundationPose** 看 foundation-model 升级.

---

## Boundary

- **Per-method 解构住这里.** 每个 `*_dissection.md` 遵循 14 项 AGENTS.md 模板.
- **Per-embodiment 用法**（humanoid 实际如何把 FoundationPose 接进其 grasp 栈）→ `embodiments/manipulation/`.
- **Bundled-tracking-inside-3D**（VGGT 的 tracking head、DROID-SLAM 相关 volume）→ `foundations/feed-forward-3d/` 和 `foundations/classical-slam/`.
- **Action 消费**（VLA 如何 condition 在 flow 或 point track 上）→ [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
- **Tracking benchmark**（TAP-Vid、Sintel、KITTI flow）→ `benchmarks/geometry/`.

---

## Cross-region pointers

- VGGT 把 tracking 打包进 3D feed-forward pass: [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)
- 3D feature cloud（per-point descriptor 喂 manipulation policy）: [`../../embodiments/manipulation/3d_feature_cloud_representations.md`](../../embodiments/manipulation/3d_feature_cloud_representations.md)
- VLA action 侧消费: [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

---

*Last opinion update: 2026-05-21. 四个里维护者首选：**FoundationPose** — 2026 manipulation 栈缺它是团队多新最响的信号.*
