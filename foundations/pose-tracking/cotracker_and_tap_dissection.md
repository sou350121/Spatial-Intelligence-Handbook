# CoTracker & TAP-Vid (任意点的时序追踪)

> **发布时间**: CoTracker — ECCV 2024 (Karaev et al., Meta + Oxford) · TAP-Vid / TAP-Net — NeurIPS 2022 (Doersch et al., DeepMind)
> **论文**: CoTracker (arXiv 2307.07635) · TAP-Vid (arXiv 2211.03726)
> **核心定位**: Track an arbitrary set of points across an arbitrarily long video — *jointly over time and across points* — handling occlusion and persistence.

**Status:** v1 — opinionated draft. Numbers `UNVERIFIED` unless rig-tested.
**Wedge tier:** W1 · canonical *sparse long-horizon* tracking primitive (complement to RAFT's dense short-horizon).
**TL;DR:** TAP-Vid defined the task — "track any point, predict visibility, handle occlusion". CoTracker solved it by *jointly tracking a batch of query points with cross-track attention*. Replaces KLT / SIFT wherever points must persist through occlusion — contact points, action recognition, watch-and-imitate.

**X-Ray.** Classical sparse trackers track points independently and fail at occlusion. CoTracker treats the batch as a *joint* problem with cross-attention over time and points. The missing primitive for "track the contact point through this episode".

---

## 📍 研究全景时间线

```
1991     1999         ~2010s      2022           2023      2024
KLT ───► SIFT match ► local-corr ► TAP-Net+bench ► CoTrk ► CoTrk3 online
└── per-point sparse tracking ──┘  └── joint cross-point + cross-time ──┘
```

The inflection from "track each point independently" to "track all jointly". VGGT borrows this for its tracking head.

---

## 1 · Architecture overview

### 1.1 System component comparison (CoTracker)

| Module | Role |
|---|---|
| Frame encoder | ViT → features at 1/8 |
| Query-pt encoder | Embedding of `(x, y, t_query)` |
| Iterative refiner | Transformer w/ **time × point** attention |
| Visibility head | Per-(point, frame) classifier |
| Output | Trajectory + visibility |

Standout: **joint attention across time and point axis** — what previous methods didn't do.

### 1.2 ⚡ Eureka Moment

> **Track points *jointly* — let each trajectory inform the others via cross-attention — and tracking through occlusion stops being an open problem.**

KLT / SIFT trackers are per-point: each fate decided in isolation. CoTracker's insight: points on the same surface are statistically dependent — joint inference keeps tracking even when one is occluded, because the *other* points carry the signal.

### 1.3 Information flow

```
   Frames ─► frame enc ─► F_1..F_T
   Query pts (x_i, y_i, t_i) ─► q_1..q_N
                  ▼
   [joint transformer ×K: attn(time × points) → refined traj + vis]
                  ▼
   Trajectories (x_i(t), y_i(t), vis_i(t))
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  traj_{i,t}^{(k+1)}  =  refiner( {traj_{j,s}^{(k)}},  F_t,  query_i )
```

Trajectory of point `i` at `t` depends on **all other tracks `j` at other times `s`** through attention. Each iteration tightens the joint solution.

| Symbol | Meaning |
|---|---|
| `traj_{i,t}` | 2D position of point `i` at `t` |
| `vis_{i,t}` | visibility at `t` |
| `F_t` | feature map at `t` |
| `K` | refinement iterations |

**Intuition.** Single-point trackers see one piece of evidence; CoTracker sees `N × T` with attention computing the joint solution. Occlusion no longer fatal — co-moving points carry the signal.

---

## 3 · Worked example: 64 contact points, 5-s clip

5 s @ 30 fps (150 frames), robot picking up a mug. 64 query points on mug + hand contact.

1. **Encode 150 frames.** ~5–10 ms / frame `UNVERIFIED` → ~1–2 s.
2. **Initialize.** Each query point at annotated frame; trajectories constant.
3. **Iterate** `k = 1..6`: joint transformer over (64 × 150 × features) → refined positions + visibility.
4. **Output.** Each point: (150, 2) trajectory + visibility. Points behind the mug show `vis=False`; re-appearing points re-acquired.

Total ~3–5 s offline. CoTracker3 online streams live at slightly higher per-frame latency. KLT on 64 independent points drops ~half under hand occlusion, re-acquires none.

---

## 4 · Engineering view

| Task | RAFT | CoTracker |
|---|---|---|
| Dense per-pixel, 2 frames | ✅ | ❌ |
| Sparse pts through 30-frame clip | ❌ | ✅ |
| Through occlusion | ❌ | ✅ |
| Joint same-object constraint | ❌ | ✅ |
| RT 30 Hz Orin | ✅ | ⚠️ online + small N |

CoTracker3 *online* streams predictions frame-by-frame with bounded memory.

**Deployment.** Contact persistence: query at gripper-object contacts at episode start → track → contact state for policy. Watch-and-imitate: track hand + tool keypoints from demo → replay.

---

## 5 · Data & eval

**TAP-Vid** is canonical: Kinetics, DAVIS, RGB-Stacking subsets with hand-annotated GT tracks + visibility. Metrics: Average Jaccard, position accuracy (δ_avg < 5 px), occlusion accuracy. CoTracker trained on **Kubric** (procedurally-generated synthetic), evaluated on TAP-Vid + DAVIS — beats TAP-Net by significant margins `UNVERIFIED`.

---

## 6 · Capabilities & failure modes

**Capabilities.** Robust to medium occlusion. Cross-track consistency. Visibility-aware. Online streaming deployable.

**Failure modes.** Long occlusions (>30% episode) overwhelm joint constraints. Fast textureless motion. Featureless surfaces — query ill-posed; hallucinates smooth trajectory. Large point sets (>256) stress memory.

### 6.1 Hidden Assumptions

- **Query point on a coherent surface.** Depth-discontinuity boundaries → noisy.
- **Frame rate sufficient.** Slow fps + fast motion → displacement exceeds receptive field.
- **Camera stationary OR ego-motion compensable.** Massive shake degrades without ego-motion estimation.
- **Online tolerates streaming-buffer latency.** >30 Hz control tight `UNVERIFIED`.
- **Visibility calibrated to similar-distribution data.** Robotics scenes differ from Kubric; `vis` thresholds need tuning.

When these break, tracks come out smooth-looking but wrong — silent failure.

---

## 7 · Comparison & interview tip

| Tracker | Year | Joint? | Occ? | Long? | RT Orin? `UNVERIFIED` |
|---|---|---|---|---|---|
| KLT | 1991 | ❌ | ❌ | partial | ✅ very |
| SIFT | 1999 | ❌ | partial | per-pair | ⚠️ |
| TAP-Net | 2022 | ❌ | ✅ | ✅ | ❌ offline |
| **CoTracker** | 2023 | ✅ | ✅ | ✅ | ⚠️ |
| **CoTracker3 online** | 2024 | ✅ | ✅ | streaming | ✅ small N |
| VGGT head | 2025 | ✅ views | partial | bundled | ⚠️ |

> **🎤 Interview Tip.** "Track 50 contact points across 5-s episode through hand occlusion?" — *"CoTracker3 online, query points at initial contact configuration. KLT drops ~half under occlusion. RAFT is dense short-horizon, wrong primitive."* "Track them with optical flow" confuses sparse long-horizon with dense short-horizon.

---

## Bridge to action policies

Output `(N, T, 2)` trajectories + `(N, T)` visibility = the *contact-point representation* flow-conditioned VLAs consume. Full story at [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

## References

- CoTracker — *ECCV 2024*. https://arxiv.org/abs/2307.07635
- CoTracker3 — https://github.com/facebookresearch/co-tracker
- TAP-Vid / TAP-Net — *NeurIPS 2022*. https://arxiv.org/abs/2211.03726
- TAPIR — *ICCV 2023*. https://arxiv.org/abs/2306.08637
- Kubric — *CVPR 2022*. https://arxiv.org/abs/2203.03570

## Boundary

**Sparse long-horizon any-point tracking**. Dense flow → [`raft_optical_flow.md`](./raft_optical_flow.md). Rigid object pose → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md). FF-3D-bundled tracking → [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md). VLA consumption → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./README.md)
