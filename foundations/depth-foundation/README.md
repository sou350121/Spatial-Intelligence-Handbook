# Depth Foundation Models

**Status:** v1 — opinionated landing page. Cross-links assume sibling wedges exist.

Monocular depth used to be a parlor trick — train on KITTI, demo on KITTI, fail on a phone photo of a kitchen. The MiDaS line (Ranftl et al. 2020) broke that by training on a mixed-domain soup and predicting *relative* inverse depth, which generalized everywhere precisely because it refused to commit to meters. Five years later the field has split: a **relative-depth foundation track** that pursues photometric realism and generalization (Depth Anything v1/v2, MoGe), and a **metric-depth foundation track** that bakes in camera intrinsics so the output is actually in meters (Metric3D v1/v2, ZoeDepth, UniDepth). The split matters because robots can't shrug at scale — a manipulator that grasps "somewhere around 0.4 metric units" is a manipulator that drops the cup.

Stereo foundation models (FoundationStereo) sit beside the monocular track as the cheap-metric-depth answer when you can afford two cameras and a baseline. They inherit the same "train on huge synthetic, generalize zero-shot" recipe but bypass the monocular scale ambiguity entirely. For robotics, the practical question is rarely "which model is best on NYUv2" — it's "does my embodiment tolerate relative depth, or do I need metric, and am I willing to pay for stereo to get it cheap?"

---

## Table of contents

| File | Topic | Tier |
|---|---|---|
| [depth_anything_v2_dissection.md](./depth_anything_v2_dissection.md) | Depth Anything v2 — the unlabeled-data win | ⚡ relative |
| [metric3d_dissection.md](./metric3d_dissection.md) | Metric3D v1/v2 — canonical-camera trick for metric depth | 🔧 metric |
| [moge_dissection.md](./moge_dissection.md) | MoGe — affine-invariant geometric loss + multi-head | 📖 relative |
| [foundationstereo_dissection.md](./foundationstereo_dissection.md) | FoundationStereo — zero-shot stereo from NVIDIA | 🔧 metric (stereo) |

---

## How to read this lane

- Building a **manipulator**? Start with `metric3d_dissection.md`. You need meters, you have a fixed wrist camera, the canonical-camera trick is exactly your friend.
- Building a **drone**? Read all four, then jump to [`crossing/scale-comparison/`](../../crossing/scale-comparison/). Monocular relative depth is useless past 30 m; stereo dies at long baseline weight; the answer is "fuse with VIO."
- Building a **VLA policy**? Read [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) first to see what the action head actually consumes — usually a point cloud with a `scale_flag`, which forces you back into the metric vs relative debate.

Cross-reference: [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) covers multi-view feed-forward 3D, which subsumes depth as one of several outputs — different paradigm, overlapping use cases.
