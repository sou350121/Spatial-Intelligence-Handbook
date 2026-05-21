# 3D Gaussian Splatting (Kerbl et al. SIGGRAPH 2023) — Dissection

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED.
**TL;DR:** 3DGS is not a rendering trick — it's the moment radiance fields became an *explicit* geometric representation that a robotics stack could actually own. The 100× speedup over NeRF is real and reproducible; the 1–2 GB-per-scene storage cost is the deployment landmine nobody warned you about.

Paper: Kerbl, Kopanas, Leimkühler, Drettakis. *SIGGRAPH 2023.* arXiv: https://arxiv.org/abs/2308.04079
Code: https://github.com/graphdeco-inria/gaussian-splatting

---

## 1 · Why this paper mattered (the part the abstract undersells)

NeRF gave you a differentiable scene representation but charged you hours of training and seconds per rendered frame. For graphics that's a known tradeoff. For robotics it's a non-starter — you can't put a representation that renders at 1 FPS behind a 30 Hz perception pipeline. 3DGS kept the differentiable rendering contract (gradients flow from pixels back to scene parameters) but discarded the MLP. The scene becomes an explicit set of ~1–5 million anisotropic gaussians; rendering becomes tile-based rasterization on the GPU. **The conceptual unlock is that the representation is now inspectable** — you can prune, edit, transplant, and downsample gaussians the same way you'd manipulate a point cloud, which is exactly what a robotics map editor needs.

## 2 · Mechanism

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

## 4 · Where it breaks (the part the paper doesn't dwell on)

- **Storage** — a finished scene is 1–2 GB on disk (millions of gaussians × ~60 floats each `UNVERIFIED`). For a humanoid that needs to carry maps of a building, this is the binding constraint, not training time. Compression variants (Self-Organizing Gaussians, Compact3D) arrived through 2024 and cut this 5–20× `UNVERIFIED`; vanilla 3DGS does not compress.
- **Initialization dependence** — 3DGS leans on COLMAP-derived SfM points for initialization. If COLMAP fails (textureless walls, motion blur, sparse views) the gaussians never converge cleanly. This is the silent failure mode in industrial scenes.
- **No semantic handle** — vanilla 3DGS encodes appearance, not category. "Where is the cup" needs an aux head (LangSplat, Feature-3DGS) bolted on.
- **Aliasing at scale** — viewing the same gaussians from a drone altitude vs a head-mounted camera produces visible aliasing artifacts. Fixed in Mip-Splatting (see `mip_splatting.md`).
- **Static scenes only** — no temporal axis. Fixed in 4D-GS lineage (see `4dgs_dynamic_scenes.md`).

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
