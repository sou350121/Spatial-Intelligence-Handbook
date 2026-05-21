# 3D Feature Cloud → Action Head

**Status:** v1 — opinionated draft. Specific integration numbers marked `UNVERIFIED`.
**Wedge tier:** W2 · **Bridge** between this handbook and [VLA-Handbook](https://github.com/sou350121/VLA-Handbook).
**TL;DR:** A 3D feature cloud is not a *better RGB image*. It is a different input class that forces architectural choices RGB-only VLAs sidestep — three of which (frame, scale, density) are where deployments silently fail.

---

## 1 · Where the boundary sits

Spatial owns the **encoder side**: how a 3D feature cloud is computed (3DGS, VGGT-class feed-forward, point-decoder heads, semantic lifting). VLA owns the **action side**: how a policy head — diffusion, flow matching, autoregressive — consumes that representation.

This is the bug-on-the-edge doc. It exists because neither handbook alone answers "why does my 3D-aware policy work in sim and collapse on hardware?" The answer is almost always in the interface.

---

## 2 · Three integration patterns observed in 2025–2026

**3D-VLA (UMass + MIT, ICML 2024).** Voxelize the scene into a coarse grid (`UNVERIFIED` typical 32³ at ~5 cm). Emit per-voxel feature tokens. Concatenate into LLM context alongside RGB tokens. *Get:* clean integration — voxel tokens look like vision tokens. *Pay:* voxelization discards geometry below grid resolution; token count scales with grid³, killing context budget fast.

**PointVLA (`UNVERIFIED` paper name; architectural pattern is verified).** Encode the raw cloud with PointNet++ or similar permutation-invariant backbone. Pool to a fixed-size embedding. Inject into the policy head as a side-channel feature, not tokens. *Get:* O(N) in points; handles variable density. *Pay:* embedding is opaque to LLM attention — you lose the ability to *point* at geometry.

**SpatialVLM (Google DeepMind 2024).** The contrarian move: don't feed 3D to the policy at all. Train a VLM that emits **spatial captions** ("red block 12 cm left of gripper, 4 cm above table") and feed those as text. *Get:* zero changes to your action head. *Pay:* captioning latency and a hard ceiling on fidelity — text cannot express a dense feature cloud.

### Trade-off table

| Pattern | Fidelity | Latency | Data appetite | Efficiency |
|---|---|---|---|---|
| 3D-VLA (voxel tokens) | High | High `UNVERIFIED` ~2× RGB-VLA | Large (paired RGB+3D) | Medium |
| PointVLA (PointNet++) | Medium | Low | Medium | High — augments cleanly |
| SpatialVLM (captions) | Low | Medium | Large (VLM pretrain) | Low — captions lossy |

Voxel when geometry is the bottleneck and GPU plentiful. PointNet++ when data-poor. Captions when team's strength is VLM prompting and the task is coarse.

---

## 3 · What breaks in deployment

Three failure modes, ordered by how often they kill an integration. All silent — the policy doesn't crash, it degrades, and the regression is hard to attribute.

**3.1 · Sparse cloud → density-conditioned collapse.** Sparse pointcloud is fine in sim, where every demo sees the same dense reconstruction. In real, your depth sensor or VGGT-class encoder drops to ~30% of training density the moment lighting changes, the object is glossy, or the angle is bad. The policy falls over silently — wrong object, missed grasp by 2 cm, mean-trajectory hallucination. The fix is **not more data**. It is density-conditioned augmentation: randomly subsample to 20–80% density during training and inject the density ratio as a feature. The policy learns to be *aware* of how much information it has.

**3.2 · Coordinate frame mismatch — the silent killer.** Encoder emits in camera frame; demos were recorded with TCP in base frame; sim logs in world frame. Somewhere a 4×4 transform is wrong by a 90° rotation or a gripper-offset translation, and the policy learns the offset as a *bias*. Works on the training rig. Fails on a second rig where the camera mount is 3 cm different. The fix is an **explicit frame normalization layer** at the seam: every cloud is transformed into a canonical frame (object-bbox-relative — see §4.1), with transform parameters logged so you can detect drift.

**3.3 · Metric scale drift — the VGGT-class trap.** Monocular feed-forward 3D (VGGT, DUSt3R lineage) is **un-metric**. The encoder emits geometrically correct clouds at an arbitrary scale. Plug it in front of a policy trained on stereo or RGB-D and you get the most common bug in this stack — the policy reaches with the right *direction* and the wrong *distance*. The fix is a **scale-conditional decoder**: fuse a known reference (gripper width, IMU-derived stereo baseline, calibration object), or train with a scale token the encoder emits explicitly. Do not let "the network will figure it out" be your plan. It will not.

---

## 4 · Engineering patterns that work

**4.1 · Pre-policy normalization to canonical bbox-relative frame.** Best general default. Detect a task-relevant bounding box (object, workspace, robot base) and transform every cloud into that frame before the policy sees it. The policy learns relative geometry, not camera-extrinsics-conditional geometry. Cross-rig generalization improves substantially `UNVERIFIED` — typical reports cite 2–3× sample efficiency.

**4.2 · Augmentation with synthetic 3DGS render perturbations.** Most effective when sim2real is the bottleneck. Train a 3DGS reconstruction, render perturbations (viewpoint, lighting, density) during policy training. Policy sees a continuous distribution of plausible inputs instead of a discrete set of demos. Makes a small dataset go further than collecting 10× more demos `UNVERIFIED`.

**4.3 · Late fusion: RGB + 3D tokens in same transformer.** Best when data is plentiful. Concatenate both as token streams; let cross-attention figure out which modality matters per-frame. 3D-VLA is the canonical instance. Highest ceiling, most expensive.

---

## 5 · The cross-handbook contract

| Side | Provides | At the boundary |
|---|---|---|
| **Spatial** | Cloud (points + features), camera-to-world transform, density estimate, metric-scale flag | Documented schema; canonical frame is camera-frame unless tagged |
| **VLA** | Action head consuming the schema; frame normalization layer; density/scale conditioning | Logs transform applied; refuses input if metric-scale flag mismatches training |
| **Both** | Round-trip integration tests on a shared embodiment (manipulation tabletop default) | Cited from both handbooks' boundary sections |

If either side breaks the contract silently, the integration fails silently. That is why this doc exists.

---

## 6 · For the reader

- **Manipulation engineer** — start with PointNet++ embedding and bbox-relative normalization. Cheapest path to a working 3D-aware policy. Upgrade to late fusion only after the data ceiling.
- **VLA researcher** — §3 failure modes are interface bugs, not encoder bugs. Your action head must declare what it expects (frame, scale, density) and refuse mismatched input.
- **Spatial researcher** — emit the §5 metadata. Costs nothing; saves the integrator a week.

---

## Cross-references

- **VLA-Handbook** — action policy design: https://github.com/sou350121/VLA-Handbook
- `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` — why VGGT is un-metric
- `foundations/semantic-3d/` — label-lift to 3D
- `crossing/representation-migration/` — when 3D matters per embodiment

## References (starter set)

- 3D-VLA — Zhen et al. *ICML 2024*
- SpatialVLM — Chen et al. *CVPR 2024*. https://spatial-vlm.github.io
- PointVLA — `UNVERIFIED` exact paper; pattern is verified
- Diffusion Policy 3D — Ze et al. *RSS 2024*
- π0 technical report — Physical Intelligence 2024

## Boundary

This doc lives on the seam. Does **not** dissect any single encoder (see `foundations/feed-forward-3d/`) or action head (see VLA-Handbook).

*Last opinion update: 2026-05-21.*
