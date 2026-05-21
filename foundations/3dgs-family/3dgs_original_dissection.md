# 3D Gaussian Splatting (3DGS 原始论文解构 — SIGGRAPH 2023)

> **Published**: 2023-07 (SIGGRAPH 2023)
> **Paper**: Kerbl, Kopanas, Leimkühler, Drettakis — *3D Gaussian Splatting for Real-Time Radiance Field Rendering*
> **Team**: INRIA + Université Côte d'Azur + MPI Informatik
> **Core position**: First explicit, GPU-rasterizable radiance-field representation — replaces NeRF's MLP with ~1–5M anisotropic gaussians so 3D becomes inspectable, editable, and 100× faster.

**Status:** v1.1 — backfilled to AGENTS.md 14-item template 2026-05-21. Hyperparams marked UNVERIFIED.
**TL;DR:** 3DGS is not a rendering trick — it's the moment radiance fields became an *explicit* geometric representation that a robotics stack could actually own. The 100× speedup over NeRF is real and reproducible; the 1–2 GB-per-scene storage cost is the deployment landmine nobody warned you about.

### X-Ray (non-expert friendly)

(a) NeRF gave you a differentiable 3D scene but required hours of training and rendered at <1 FPS — useless inside a 30 Hz perception loop. (b) 3DGS keeps the differentiable contract (gradients flow back from pixels) but throws away the MLP, replacing it with millions of explicit anisotropic ellipsoids that a CUDA rasterizer can splat in real time. (c) For spatial AI engineers: 3D scenes become *inspectable assets* — you can prune, edit, transplant gaussians like a point cloud, which is exactly what a robotics map editor or sim-to-real pipeline needs.

### 📍 Research Landscape Timeline

```
NeRF 2020 ─► Instant-NGP 2022 ─► Mip-NeRF360 2022 ─► ★ 3DGS SIGGRAPH 2023 ─► 4D-GS / Mip-Splat 2024 ─► GS-SLAM / VGGT 2024-25 ─► feed-forward GS init 2026+
```

3DGS is the inflection point that moved radiance fields from "research artifact" to "robotics-deployable map primitive." Open downstream: compression, semantic grounding, feed-forward initialization.

Paper: Kerbl, Kopanas, Leimkühler, Drettakis. *SIGGRAPH 2023.* arXiv: https://arxiv.org/abs/2308.04079
Code: https://github.com/graphdeco-inria/gaussian-splatting

---

## 1 · Why this paper mattered (the part the abstract undersells)

NeRF gave you a differentiable scene representation but charged you hours of training and seconds per rendered frame. For graphics that's a known tradeoff. For robotics it's a non-starter — you can't put a representation that renders at 1 FPS behind a 30 Hz perception pipeline. 3DGS kept the differentiable rendering contract (gradients flow from pixels back to scene parameters) but discarded the MLP. The scene becomes an explicit set of ~1–5 million anisotropic gaussians; rendering becomes tile-based rasterization on the GPU. **The conceptual unlock is that the representation is now inspectable** — you can prune, edit, transplant, and downsample gaussians the same way you'd manipulate a point cloud, which is exactly what a robotics map editor needs.

## 2 · Mechanism

> 📌 **Napkin Formula**: `Rendered pixel = α-blend{ Project(Gᵢ; intrinsics, pose) | i sorted front→back per tile }` — every pixel is a depth-sorted weighted sum of projected anisotropic gaussians. No MLP, no ray-marching, just rasterize-and-blend.

> ⚡ **Eureka Moment**: The win isn't the gaussians — it's the *combination* of anisotropic ellipsoids (a few million can cover a room, isotropic spheres need 10–100×) with a tile-based CUDA rasterizer (sorted α-blend, not generic point splat) and adaptive densification (the optimizer adds/removes primitives during training). All three together is what unlocked the 100× speedup; any two of three would have stayed academic.

```
   SfM points (COLMAP)
          │
          ▼
   ┌─────────────────────┐
   │ Initialize ~100k    │
   │ anisotropic         │
   │ gaussians:          │
   │   position (xyz)    │
   │   covariance (R,S)  │
   │   opacity α         │
   │   SH coeffs (color) │
   └─────────────────────┘
          │
          ▼  (differentiable rasterizer)
   ┌─────────────────────┐
   │ Tile-based splat →  │
   │ α-blend front→back  │ ──► rendered RGB
   │ in screen space     │
   └─────────────────────┘
          │
          ▼
   Loss: L1 + D-SSIM vs GT image
          │
          ▼
   Adaptive density control:
     · clone gaussians in under-covered regions
     · split gaussians with large gradients
     · prune low-opacity / oversized gaussians
```

Three pieces matter for embodied use:

- **Anisotropic covariance** — each gaussian is a 3D ellipsoid, not a sphere. This is what lets a few million primitives cover a room; isotropic spheres would need 10–100×.
- **Tile-based rasterizer** — the CUDA rasterizer sorts gaussians per tile and α-blends them. This is where the speed comes from; it is not a generic point cloud renderer.
- **Adaptive densification** — the optimizer adds and removes gaussians during training. Final count is data-driven, not a hyperparameter.

## 3 · Training loop (the practical numbers)

| Knob | Default | What it controls |
|---|---|---|
| Iterations | 30k | Training length; ~7k gives "good enough" preview |
| Densification interval | every 100 iters until 15k | When the splitter/cloner runs |
| Position LR | ~1.6e-4 → 1.6e-6 (decayed) `UNVERIFIED` | Gaussian position update |
| Opacity LR | ~0.05 `UNVERIFIED` | α update |
| SH degree | 0 → 3 (warmup) | Color expressiveness |

Reported training time on a single A6000: ~30 min for SIGGRAPH-grade quality on Mip-NeRF360 scenes `UNVERIFIED — varies with scene complexity`. Render rate at inference: 100+ FPS at 1080p on the same hardware. Compare against NeRF (hours of training, sub-1 FPS rendering) and the 100× claim resolves into "100× faster training and 100× faster rendering, simultaneously."

## 3.5 · Worked example — single mug on a desk

Capture a coffee mug with a phone, 30 photos in a 1 m arc.

- **COLMAP init**: ~5K SfM points (sparse but well-localized on the mug + desk).
- **Iter 0**: ~5K gaussians, mostly spherical, opacity ~0.1.
- **Iter 7K**: ~120K gaussians after densification — clones spawn on the rim, splits cover the handle curvature. PSNR ~28 dB UNVERIFIED.
- **Iter 30K**: ~800K gaussians, opacity bimodal (~0 prune candidates and ~0.9 keepers). PSNR ~32 dB. Disk size ~180 MB UNVERIFIED.
- **Render**: at 1080p, ~3 ms per frame on RTX 4090 → 300+ FPS headroom. Same scene as NeRF would take ~200 ms (5 FPS).

The 4–5 orders-of-magnitude render gap is what makes 3DGS usable inside a robot perception loop and NeRF not.

---

## 4 · Where it breaks (the part the paper doesn't dwell on)

- **Storage** — a finished scene is 1–2 GB on disk (millions of gaussians × ~60 floats each `UNVERIFIED`). For a humanoid that needs to carry maps of a building, this is the binding constraint, not training time. Compression variants (Self-Organizing Gaussians, Compact3D) arrived through 2024 and cut this 5–20× `UNVERIFIED`; vanilla 3DGS does not compress.
- **Initialization dependence** — 3DGS leans on COLMAP-derived SfM points for initialization. If COLMAP fails (textureless walls, motion blur, sparse views) the gaussians never converge cleanly. This is the silent failure mode in industrial scenes.
- **No semantic handle** — vanilla 3DGS encodes appearance, not category. "Where is the cup" needs an aux head (LangSplat, Feature-3DGS) bolted on.
- **Aliasing at scale** — viewing the same gaussians from a drone altitude vs a head-mounted camera produces visible aliasing artifacts. Fixed in Mip-Splatting (see `mip_splatting.md`).
- **Static scenes only** — no temporal axis. Fixed in 4D-GS lineage (see `4dgs_dynamic_scenes.md`).

### 4.x · Hidden Assumptions

Upstream assumptions whose violation produces the failure modes above:

- **Good COLMAP init** — SfM points seed the gaussian set; in textureless / motion-blur scenes COLMAP fails and gaussians never converge.
- **Static scene during capture** — any moving object during the 30-photo collection produces floaters or smeared gaussians.
- **Sufficient training views** — sparse coverage (~<20 images for a room) leaves under-constrained gaussians that look fine from training viewpoints and shatter on novel views.
- **Single camera scale (no zoom)** — vanilla 3DGS aliases under scale change; Mip-Splatting is the fix.
- **Disk and VRAM headroom** — a 1–2 GB scene must fit in GPU memory for rendering; mobile / Jetson deployment requires compression.

If violated, the model often still *renders* something — silent failure (floaters, shimmer, ghosting) is the dangerous mode.

---

## 5 · Why robotics teams cared (the lane that matters for this handbook)

Three reasons, in order of operational impact:

1. **Inspectable representation** — gaussians are points-with-extent. Existing point-cloud tooling (downsampling, region cropping, collision queries) ports over with light adaptation. Try doing that on a NeRF MLP.
2. **Edit-friendly** — you can delete a region of gaussians, transplant gaussians from another scene, or perturb their positions for data augmentation. This is what made 3DGS the substrate for sim-to-real visual training (e.g. RoboGS-style pipelines).
3. **Reasonable inference budget** — 100 FPS at 1080p on a desktop GPU means ~30 FPS on a Jetson-class device with careful tile management `UNVERIFIED — needs rig validation`. That's inside a perception loop's budget. NeRF never was.

The teams that quietly migrated through late 2023 and 2024 were not chasing photoreal renders; they were chasing a scene representation that survives contact with a robot. 3DGS is the first one that did.

## 6 · 2-year outlook

The vanilla 3DGS paper is now a baseline, not a destination. By 2027 expect:

- **Compressed-by-default variants** to be the de facto starting point — nobody ships 1 GB scenes in production.
- **Feed-forward initializations** (VGGT-class models seeding the gaussian set instead of COLMAP) to subsume the "needs SfM" failure mode.
- **Semantic-grounded gaussians** (LangSplat lineage) to be the assumed interface for VLA consumption, not a research curiosity.

**Falsifiable prediction:** by 2027-06, the dominant 3DGS pipeline in published robotics work will *not* use COLMAP for initialization — it will use a feed-forward 3D model. Bet against any paper that still relies on COLMAP as the primary init by then.

**Interview Tip**: When asked "why 3DGS over NeRF for robotics," the trap answer is "100× faster." The right answer is *"because it's explicit"* — gaussians are inspectable, prunable, and editable like point clouds; NeRF's MLP isn't. Speed is the consequence, not the contribution.

## References

- **3DGS original** — Kerbl, Kopanas, Leimkühler, Drettakis. *SIGGRAPH 2023.* https://arxiv.org/abs/2308.04079
- **Mip-NeRF360 benchmark** — Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **NeRF original** (the thing 3DGS displaced) — Mildenhall et al. *ECCV 2020.* https://arxiv.org/abs/2003.08934
- **Self-Organizing Gaussians (compression)** — Morgenstern et al. *ECCV 2024.* [arXiv link TBD]

## Boundary

This doc dissects the original 3DGS paper. It does **not** cover:

- Dynamic-scene extensions → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- SLAM integration → `foundations/3dgs-family/gs_slam_dissection.md`
- Aliasing fix → `foundations/3dgs-family/mip_splatting.md`
- 3DGS vs other scene representations (mesh, voxel, feed-forward pointmap) → `crossing/representation-migration/`
- How VLA policies consume gaussian scenes → `bridge-to-vla/feature-cloud-to-action.md`
- Comparison with feed-forward 3D models like VGGT → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
