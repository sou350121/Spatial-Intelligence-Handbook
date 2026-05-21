# Block-NeRF 解构 (Block-NeRF: Scalable Large Scene Neural View Synthesis)

> **Publication:** CVPR 2022
> **Paper:** Tancik, Casser, Yan, Pradhan, Mildenhall, Srinivasan, Barron, Kretzschmar. Google Research / Waymo. arXiv: https://arxiv.org/abs/2202.05263 · Project: https://waymo.com/intl/en_us/research/block-nerf/
> **Core position:** The first method that scaled neural radiance fields from room-size to *city-block-size*, and the reason the NeRF lineage stayed alive in AD stacks after 3DGS displaced everything else.

**Status:** v1 — opinionated. Numbers from paper unless `UNVERIFIED`.
**TL;DR:** Block-NeRF's contribution is not a new MLP — it's a *system design* for splitting a city-scale capture (Waymo's 2.8M images of San Francisco's Alamo Square) into ~100 overlapping NeRF "blocks", each independently trained, dynamically composed at render time. Three engineering pieces: per-block appearance embedding for cross-block lighting consistency; visibility prediction so renderer knows which blocks to query; transient-object masking from a segmentation net. The only published method in 2022 capable of doing this. **3DGS still cannot match Block-NeRF at this scale** — storage explodes.

**X-Ray.** Vanilla NeRF on a 100m×100m city block: training fails, storage explodes, COLMAP loses tracks across passes. Block-NeRF says: don't fight scale — partition it. 50m-diameter blocks with ~50% overlap, each its own NeRF, blended at query time. For spatial-intelligence engineers, this is when NeRF graduated from research toy to *production infrastructure*: Waymo published because they were already using it for AV simulation. The lineage (Mega-NeRF, Switch-NeRF, NVIDIA Cosmos sim-data) is still NeRF-based in 2026.

## 📍 Research panorama timeline

```
2020       2021         2022 (Feb)         2022 (Aug)        2024-26
NeRF     ► NeRF-W     ► Block-NeRF       ► Mega-NeRF        ► Waymo / Cosmos
(ECCV)     (in-the-     YOU ARE HERE       (drone octree      sim pipelines
            wild         city-scale +       decomposition)     still ship
            transient    visibility +                          Block-NeRF
            objects)     appearance)                           lineage
                         └─ "split scene into chunks" lineage ─┘
                                                                │
3DGS (2023) ─► tries city ─► storage explodes ─► defers to NeRF
              (~1GB/room → ~kTB/city block)
```

3DGS displaced NeRF for room-scale + robot perception. For city-scale outdoor it *never displaced* NeRF — storage scales with primitives × scene area. Block-NeRF stayed put.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Function | Novelty |
|---|---|---|
| Block decomposition | ~100 circular blocks, 50m dia, 50% overlap | Manual placement; one NeRF / block |
| Per-block NeRF | Mip-NeRF backbone + appearance embedding head | Inherits Mip-NeRF (2021) |
| Appearance embedding | Per-image learnable 32-d; modulates color MLP | NeRF-W (2021) |
| Visibility prediction | Tiny MLP: `(xyz,dir) → "block relevant?"` | **New** |
| Transient mask | Segmentation (people, cars) masked from loss | **New** |
| Block composition | Inverse-distance-weighted blend of top-K | **New** |

### 1.2 ⚡ Eureka moment

> **At city scale, the right question isn't "how big can one NeRF be" — it's "how do N independent NeRFs render as one coherent scene". Coherence comes from (a) shared appearance embeddings and (b) visibility-aware composition, not from a unified MLP.**

A systems-thinking move a deep-learning-only lab would miss. Why Waymo (with production capture + compute) wrote it, not a pure ML group.

### 1.3 Flow diagram

```
   City capture: 2.8M images over ~3 months
                 │
                 ▼
   Spatial partition: ~100 blocks, 50m dia, 50% overlap
                 │
                 ▼
   Parallel training per block:
     Mip-NeRF + appearance embed + visibility head + transient mask
                 │
                 ▼  (rendering)
   Query (x, y, z, view dir):
     1. top-K blocks via visibility heads
     2. render each → RGB_k, weight_k = 1/distance_to_block_center
     3. blend: pixel = Σ w_k · RGB_k / Σ w_k
                 │
                 ▼
              Final rendered image
```

---

## 2 · Math core: block composition + appearance embedding

### 📌 Napkin Formula

```
RGB(query) = Σ_{k ∈ visible} w_k · NeRF_k(query, app_embed_k) / Σ w_k

w_k = (1 / distance(query, center_k))^p          # inverse-distance weighting
app_embed_k = 32-d vector per image, optimized during training
```

IDW (inverse-distance weighting) — same formula geospatial interpolation has used for decades. Novelty: *what gets weighted* is independent neural radiance fields.

### 2.1 Why appearance embedding is non-optional

Captures span months. Same intersection in June (green leaves, harsh shadows) and December (no leaves, overcast). Train one NeRF on both → foggy gray average. NeRF-W solution: per-image 32-d embedding modulates color MLP. At inference, freeze to canonical lighting (or interpolate for time-of-day). Block-NeRF extends: embeddings *shared* across blocks via joint optimization, so neighbors pick compatible canonical lighting → no seams.

### 2.2 Visibility prediction = speed-saver

Rendering through all 100 blocks per pixel is impossibly slow. Visibility head — tiny MLP predicting whether a query falls in a block's well-represented region — prunes 90%+ of blocks at query time. **This makes inference tractable.**

---

## 3 · Worked example: render 30 m from a block center

Three nearby blocks: A (center 0m), B (50m), C (100m). Query at 30 m.

| Block | distance | visibility | weight (1/d) | RGB |
|---|---|---|---|---|
| A | 30 m | 0.95 (in) | 0.033 | (0.40, 0.30, 0.20) |
| B | 20 m | 0.90 (overlap) | 0.050 | (0.42, 0.31, 0.21) |
| C | 70 m | 0.05 | pruned | — |

Final = `(0.033·0.40 + 0.050·0.42) / 0.083 = 0.412`. Smooth transition between A and B, no visible seam — both trained on 50% overlapping imagery, appearance embeddings jointly optimized.

---

## 4 · Engineering view: what the paper built

| Metric | Value |
|---|---|
| Total images | ~2.8M (Alamo Square, SF) |
| Capture duration | ~3 months |
| Blocks | ~100 |
| Per-block training | ~12h `UNVERIFIED` |
| Total compute | ~12k GPU-hours `UNVERIFIED — TPU-equiv` |
| Per-block storage | ~500 MB `UNVERIFIED` |
| Total scene | ~50 GB |
| Render | <1 FPS at 1080p |

**Not a single-researcher project.** Industrial pipeline. Waymo wrote it because they had the fleet and the compute. **No academic lab has reproduced it at the same scale.**

Why this stayed NeRF: per-block neural representation is *constant size* regardless of feeding imagery. With 3DGS, more imagery → more gaussians → more storage. Block-3DGS would need ~1 GB × 100 = 100 GB minimum, plus exploding gaussian count on urban facades. **Storage economics favor NeRF at this scale.**

---

## 5 · Data and evaluation

- **Custom Alamo Square dataset:** Waymo internal, not released (publication + demo, not benchmark contribution).
- **Eval:** qualitative novel-view rendering, drive-through demos. Paper does not establish numerical benchmark — Block-NeRF *defined* the city-scale problem.
- **Reproducibility:** zero. Code not released; dataset not released. Mega-NeRF reproduced the idea on public drone captures (Mill 19) at lower scale.

The canonical paper is a closed demo; downstream re-derives ideas on open data.

---

## 6 · Capabilities and failure modes

**Does:** coherent novel-view rendering of multi-block city scenes from long-running captures; time-of-day / weather interpolation via appearance embedding; robustness to transient objects (cars, pedestrians); driveable trajectories (Waymo's actual AV-sim use case).

### 6.1 Hidden assumptions

- **Industrial-scale capture available** — ~30k images / block, multi-pass, GPS / IMU. Single-camera handheld won't work.
- **Spatially uniform capture density** — block partition assumes even distribution. Sparse blocks (rarely-driven side streets) fail; holes appear.
- **Mostly-static scene** — transient masking handles cars / pedestrians; does **not** handle construction, seasonal foliage, demolition. Long-term changes break embedding.
- **Compute budget for retraining** — adding / updating a block requires retraining from scratch. **Not online.**
- **Poses converge** — assumes GPS / SLAM gives poses good enough for COLMAP refinement. Urban canyons with poor GPS can fail.

### 6.2 Why 3DGS hasn't replaced it (2026)

1. **Storage** — 3DGS at city scale ~kTB; nobody ships that.
2. **Streaming** — NeRF MLPs stream in 100MB block chunks; gaussian splats are less streamable (entire block must load for rasterization).
3. **Production inertia** — Waymo, NVIDIA Cosmos, large sim-data shops standardized on Block-NeRF lineage in 2022–23 before 3DGS proved itself. Migration cost is enormous; nobody has motive.

2025–26 "large-scale 3DGS" (Hierarchical 3DGS, Scaffold-GS) is closing storage partially. No published method matches Block-NeRF's storage + quality + scale combo by mid-2026.

---

## 7 · Comparison and interview tip

| Property | Mega-NeRF | **Block-NeRF** | Hierarchical 3DGS (2024) | Mip-NeRF 360 |
|---|---|---|---|---|
| Scale | Drone (~km²) | City block (~km²) | City block (early) | Single 360° |
| Decomposition | Octree | Manual blocks + overlap | LOD hierarchy | None |
| Transient handling | No | Yes | No | No |
| Appearance variation | Per-image embed | Per-image embed | No | No |
| Storage at city scale | ~tens of GB | ~50 GB | ~hundreds GB–TB `UNVERIFIED` | N/A |
| Published deployment | UAV recon | **Waymo AV sim** | Research demos | Offline bench |

> **🎤 Interview tip.** "Why didn't 3DGS replace Block-NeRF the way it replaced room-scale NeRF?" — Right answer: *"Storage. 3DGS primitive count scales with scene area, pushing a city map into terabytes. Block-NeRF's neural representation is constant-size per block. Until someone publishes a compressed-by-default 3DGS that breaks the storage curve at km² scale, the NeRF lineage holds the city-scale lane — Waymo and NVIDIA Cosmos still ship it in production AV sim."* Wrong: "3DGS will catch up soon." Maybe; nobody has shipped it as of 2026.

---

## References

- **Block-NeRF** — Tancik et al. *CVPR 2022.* https://arxiv.org/abs/2202.05263
- **Mega-NeRF** — Turki et al. *CVPR 2022.* https://arxiv.org/abs/2112.10703
- **NeRF in the Wild** — Martin-Brualla et al. *CVPR 2021.* https://arxiv.org/abs/2008.02268
- **Mip-NeRF 360** (per-block backbone) — `mip_nerf_360_dissection.md`
- **Waymo project page** — https://waymo.com/intl/en_us/research/block-nerf/
- **NVIDIA Cosmos** — `foundations/world-model/nvidia_cosmos_dissection.md`
- **Wayve world model** — `companies/wayve_world_model.md`

## Boundary

Dissects Block-NeRF only. Does **not** cover drone-altitude Mega-NeRF in depth, AV-sim integration (→ `companies/wayve_world_model.md`, `foundations/world-model/nvidia_cosmos_dissection.md`), large-scale 3DGS variants (→ `foundations/3dgs-family/` future docs), or sensor questions (→ `foundations/sensor-physics/`).

---

[← Back to NeRF Family README](./README.md)
