# 3DGS Family

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED.
**TL;DR:** 3D Gaussian Splatting is the representation that finally made photoreal radiance fields run in a robot's perception budget. The lane that matters for spatial intelligence is not the original SIGGRAPH 2023 paper alone — it's the four derivatives (dynamic, SLAM-coupled, anti-aliased, distilled) that turned a renderer into a working scene representation.

---

## Why 3DGS replaced NeRF for spatial intelligence

NeRF was the right *idea* (continuous radiance field) wrapped in the wrong *implementation* (MLP-per-ray, hours per scene, opaque to geometry tools). 3DGS keeps the differentiable rendering contract but swaps the MLP for an explicit set of anisotropic gaussians rasterized in screen space. That single change is what made the representation usable for embodied AI: training drops from hours to minutes on consumer GPUs, rendering hits 100+ FPS on a desktop card, and — crucially — the gaussians are *explicit primitives* you can inspect, edit, prune, and pass into a downstream policy. The robotics teams that quietly migrated through 2024 were not chasing photoreal video; they were chasing a scene representation that survives contact with a control loop.

## The 4 derivatives that matter for embodied AI

- **Dynamic (4D-GS lineage)** — Adds time. Lets the representation cover manipulation scenes where objects move during the demonstration, not just static rooms.
- **SLAM-coupled (GS-SLAM lineage)** — Builds the gaussian set online from a moving camera. This is the bridge from "post-hoc reconstruction" to "live spatial map."
- **Anti-aliased (Mip-Splatting)** — Fixes the silent failure mode: vanilla 3DGS looks terrible at the scale ranges drones and AR headsets actually traverse.
- **Original 3DGS** — Still the right baseline to read first; everything else patches one of its known holes.

We dissect each below. Cross-embodiment comparison (3DGS vs feed-forward pointmap vs neural mesh) lives in `crossing/representation-migration/`, not here.

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `3dgs_original_dissection.md` | Kerbl et al. SIGGRAPH 2023 — the rasterizer, training loop, deployment envelope | ⚡ |
| `4dgs_dynamic_scenes.md` | Wu et al. CVPR 2024 — temporal extensions for moving objects | 🔧 |
| `gs_slam_dissection.md` | Yan et al. CVPR 2024 — gaussian map building inside a SLAM loop | 🔧 |
| `mip_splatting.md` | Yu et al. CVPR 2024 — anti-aliasing fix for multi-scale viewing | 🔧 |

## Boundary

This directory is per-method dissection of the 3DGS lineage. It does **not** cover:

- Cross-representation comparison (3DGS vs feed-forward 3D vs voxel grids) → `crossing/representation-migration/`
- Feed-forward 3D (VGGT, DUSt3R, π³) → `foundations/feed-forward-3d/`
- How VLA policies consume gaussian scenes as action features → `bridge-to-vla/feature-cloud-to-action.md`
- Per-embodiment deployment notes (drone-side 3DGS, manipulation-side 3DGS) → `embodiments/<emb>/`

Cite from those places when the per-method detail here is needed in a different context.
