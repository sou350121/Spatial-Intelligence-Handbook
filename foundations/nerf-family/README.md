# NeRF Family — The Predecessor Paradigm (and Where It Still Beats 3DGS)

**Status:** v1 — opinionated draft.
**TL;DR:** NeRF was the dominant radiance-field paradigm from ECCV 2020 to mid-2024 and got displaced — *as a deployment substrate* — by 3D Gaussian Splatting roughly the moment SIGGRAPH 2023 hit arXiv. But "displaced" is not "dead": for unbounded outdoor scenes, city-scale reconstruction, and the last 0.5 dB of LPIPS on small bounded scenes, the NeRF lineage is still the right tool in 2026. This region exists so that readers who only know 3DGS understand what they inherited — and what they're missing when they default to gaussians for problems NeRF still handles better.

---

## Why a NeRF region exists when 3DGS won the spotlight

Most spatial-intelligence handbooks written after 2024 treat NeRF as a historical footnote — "the slow MLP that gaussians replaced." That framing is half right and dangerous. The right framing:

- **NeRF (2020–2022) was the paradigm change.** Volumetric rendering + positional encoding + per-scene MLP was the first time photorealistic novel-view synthesis from RGB-only inputs became a credible research direction. Everything that followed — Instant-NGP, Mip-NeRF 360, Block-NeRF, and yes 3DGS itself — is a patch on a specific weakness of vanilla NeRF.
- **3DGS won deployment, not accuracy.** On Mip-NeRF 360 unbounded scenes, the best NeRF variants (Zip-NeRF, Mip-NeRF 360 itself) still beat vanilla 3DGS on LPIPS / SSIM. 3DGS wins on training time, render rate, and editability — which is exactly what robotics needed. For an offline scene reconstruction job where quality is the only metric, NeRF lineage is still competitive.
- **City-scale stayed NeRF.** Block-NeRF / Mega-NeRF / Switch-NeRF were never seriously challenged by 3DGS for kilometer-scale outdoor reconstruction. Storage cost of 3DGS (~1–2 GB / room scene) makes city-scale gaussian splats operationally awkward; NeRF's MLP parametrization scales by data, not by primitive count.

The lane that matters: **NeRF is what you read when you want to understand *why* differentiable scene rendering works at all**, and what you reach for when 3DGS' weaknesses (storage, unbounded scenes, surface reconstruction precision) bite.

## When to use NeRF vs 3DGS in 2026

| Scenario | Pick | Why |
|---|---|---|
| Robot perception map, ≤room scale | **3DGS** | 100 Hz inference, inspectable primitives, edit-friendly |
| Offline photoreal reconstruction, small bounded scene | **Mip-NeRF 360 / Zip-NeRF** | Last 1 dB on LPIPS; quality > speed |
| Unbounded outdoor (360°) hero shot | **Mip-NeRF 360 lineage** | Disparity-based contraction handles sky/far-field |
| City / multi-block reconstruction | **Block-NeRF / Mega-NeRF** | Spatial decomposition; 3DGS storage breaks |
| Live SLAM-coupled mapping | **3DGS** (GS-SLAM) | NeRF is too slow to integrate online |
| High-precision *surface* reconstruction | **NeuS / VolSDF (NeRF lineage)** | SDF-parametrized NeRF still wins meshing |
| Drone-altitude multi-scale viewing | **Mip-Splatting (3DGS)** *or* **Mip-NeRF 360** | Mip-aware; aliasing fixed |
| Compressed mobile deployment | **3DGS variants** (SOGS, Compact3D) | NeRF MLPs aren't easily streamable |

Rule of thumb: **if the consumer is a robot, default to 3DGS; if the consumer is a renderer or a meshing pipeline, NeRF lineage is still on the table.**

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `nerf_original_dissection.md` | Mildenhall et al. ECCV 2020 — the paper that rewrote the rules; volumetric rendering + positional encoding; why training takes hours | ⚡ |
| `instant_ngp_dissection.md` | Müller et al. SIGGRAPH 2022 (NVIDIA) — multi-resolution hash encoding; NeRF training from hours to minutes | ⚡ |
| `mip_nerf_360_dissection.md` | Barron et al. CVPR 2022 (Google) — unbounded scenes + cone-tracing anti-aliasing; the quality benchmark 3DGS still chases | 🔧 |
| `block_nerf_large_scenes.md` | Tancik et al. CVPR 2022 (Google/Waymo) — city-scale reconstruction by spatial block decomposition; deployed in Waymo's AV stack | 🔧 |

## Reading order (recommended)

1. **`nerf_original_dissection.md`** — establishes the mental model (volume rendering, positional encoding, per-scene optimization). Without this the rest is just engineering patches.
2. **`instant_ngp_dissection.md`** — the engineering breakthrough that made NeRF practically trainable. Reads like a systems paper.
3. **`mip_nerf_360_dissection.md`** — the quality ceiling. If you want to know what NeRF can still do better than 3DGS, this is the answer.
4. **`block_nerf_large_scenes.md`** — the deployment story. Waymo's reason to keep the NeRF lineage alive.

## Cross-references

- The successor paradigm → `foundations/3dgs-family/3dgs_original_dissection.md` (SIGGRAPH 2023; what displaced NeRF for robotics)
- The next paradigm shift → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` (CVPR 2025; what may displace per-scene optimization entirely)
- Industry adoption (Waymo Block-NeRF lineage) → `companies/wayve_world_model.md`
- Cross-representation comparison (NeRF vs 3DGS vs feed-forward pointmap) → `crossing/representation-migration/`

## Boundary

This directory dissects four NeRF-lineage papers picked for *narrative value*: the original (2020), the systems unlock (Instant-NGP), the quality benchmark (Mip-NeRF 360), and the large-scale deployment (Block-NeRF). It does **not** cover:

- Surface-reconstruction NeRFs (NeuS, VolSDF, Neuralangelo) — separate research line; covered indirectly when meshing is discussed in `crossing/representation-migration/`
- Dynamic-scene NeRFs (D-NeRF, HyperNeRF, K-Planes) — the 3DGS lineage took over this niche; see `foundations/3dgs-family/4dgs_dynamic_scenes.md` for the inheriting work
- Generative NeRF (DreamFusion, Zero-1-to-3) — out of scope; this region is reconstructive, not generative
- 3DGS itself or its derivatives → `foundations/3dgs-family/`

The goal here is **3DGS prehistory + still-relevant niches**, not exhaustive NeRF zoo coverage.

---

*Last opinion update: 2026-05-21.*
