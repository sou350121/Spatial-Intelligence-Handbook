# Pose & Tracking Primitives (位姿与追踪原语)

> **Region tier:** Foundations · the upstream toolbox every robotics perception stack ends up rebuilding badly.
> **Scope:** Two primitive families — **object 6D pose** (where is *this thing* in 3D right now?) and **motion tracking** (where did *this pixel / point* move between frames?).
> **Status:** v1 — opinionated landing page.

**TL;DR.** Most robotics papers presuppose two primitives without naming them: "we estimate the 6D pose of the mug" and "we track contact points across the manipulation episode." Neither is free. Both have a winning 2022–2024 paper that quietly became table-stakes. This region dissects four of them — FoundationPose, MegaPose, RAFT, CoTracker (+ TAP-Vid) — and tells you when to use which.

---

## Why this region exists

Manipulation, humanoid and VLA papers routinely open with two hidden assumptions: "given the 6D pose of the target object…" and "we track keypoints across the demonstration…". Both clauses hide a foundation model. **Object pose** is the unsung input to almost every grasp planner, peg-in-hole policy, and assembly demo. **Point / pixel tracking** is the unsung input to optical-flow-conditioned policies, contact reasoning, ego-motion estimation, and any "watch the demo, do the demo" pipeline. They were the *missing* foundations on this handbook's shelf until this region.

The relationship to feed-forward 3D (`foundations/feed-forward-3d/`) matters: **VGGT internally produces 2D tracks** as one of its four heads — but it doesn't replace dedicated trackers. CoTracker still wins on long-horizon joint tracking; RAFT still wins on dense low-displacement flow; FoundationPose still wins on category-free instance pose. **Feed-forward 3D bundles tracking as a byproduct. This region dissects the specialists.**

---

## Two primitive families

### Family A — Object 6D pose (novel-object, no per-object training)

| Tool | Year | Inputs | Output | When to use |
|---|---|---|---|---|
| **[FoundationPose](./foundation_pose_dissection.md)** ⚡ | 2024 CVPR best | RGB-D + (mesh OR ~16 ref imgs) | 6D pose + score | Modern default. Mesh-free path onboards a new SKU in minutes. |
| **[MegaPose](./megapose_dissection.md)** 🔧 | 2022 CoRL | RGB(+D) + mesh | 6D pose | Predecessor; render-and-compare baseline. Useful when CAD mesh is available and you want explicit rejection scores. |

Both are *category-free* — they don't need "this is a mug" training. That is the unlock for industrial / household manipulation where the long tail of objects defeats per-class supervision.

### Family B — Motion tracking (flow + point tracking)

| Tool | Year | Inputs | Output | When to use |
|---|---|---|---|---|
| **[RAFT](./raft_optical_flow.md)** ⚡ | 2020 ECCV best | 2 consecutive frames | Dense optical flow (HxWx2) | Dense pixel-wise motion field. Ruled the flow leaderboard 2020-2024. |
| **[CoTracker + TAP-Vid](./cotracker_and_tap_dissection.md)** ⚡ | 2024 / 2022 | Video + query points | Per-point trajectory + visibility | Long-horizon sparse-point tracking. Contact-point persistence, watch-and-imitate, episode mining. |

**Why not just KLT + SIFT?** Classical sparse trackers track points independently *and* frame-by-frame. CoTracker is *joint over time and across points* — it propagates information across the query set simultaneously, recovering from occlusion that would kill KLT. Same lesson as RAFT vs FlowNet: replace single-shot estimation with iterative refinement and correlation across context.

---

## Recommended reading order

1. Manipulation / VLA background → **FoundationPose** first (directly useful for grasp / peg policies) → **CoTracker** (episode mining and contact reasoning).
2. SLAM / VIO background → **RAFT** first (the primitive that powers DROID-SLAM's correlation volume) → **VGGT** in `foundations/feed-forward-3d/` for the bundled-tracking variant.
3. Classical CV background → **MegaPose** for the render-and-compare lineage, then **FoundationPose** as the foundation-model upgrade.

---

## Boundary

- **Per-method dissection lives here.** Each `*_dissection.md` follows the 14-item AGENTS.md template.
- **Per-embodiment usage** (how a humanoid actually wires FoundationPose into its grasp stack) → `embodiments/manipulation/`.
- **Bundled-tracking-inside-3D** (VGGT's tracking head, DROID-SLAM correlation volume) → `foundations/feed-forward-3d/` and `foundations/classical-slam/`.
- **Action consumption** (how a VLA conditions on flow or point tracks) → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
- **Tracking benchmarks** (TAP-Vid, Sintel, KITTI flow) → `benchmarks/geometry/`.

---

## Cross-region pointers

- VGGT bundles tracking into a 3D feed-forward pass: [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)
- 3D feature clouds (per-point descriptors feeding manipulation policies): [`../../embodiments/manipulation/3d_feature_cloud_representations.md`](../../embodiments/manipulation/3d_feature_cloud_representations.md)
- VLA action-side consumption: [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

---

*Last opinion update: 2026-05-21. Maintainer pick of the four: **FoundationPose** — its absence from a 2026 manipulation stack is the loudest tell of how green the team is.*
