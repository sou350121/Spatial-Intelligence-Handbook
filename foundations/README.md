# Foundations · 跨 embodiment 共享底层

Backbone primitives every embodiment ends up depending on. Owned here — referenced by `embodiments/*` and `crossing/*`.

| Subdirectory | Scope | First wedge |
|---|---|---|
| `3dgs-family/` | 3DGS / 2DGS / 4DGS / Mip-Splatting / GS-SLAM | TBD |
| `feed-forward-3d/` | DUSt3R / MASt3R / VGGT / π³ / streaming variants | **`vggt_cvpr2025_dissection.md` (W1)** |
| `depth-foundation/` | Depth Anything v2 / MoGe / Metric3D / FoundationStereo | TBD |
| `semantic-3d/` | DINOv2 / SigLIP → 3D / LERF / OpenScene / 3D scene graph | TBD |
| `world-model/` | Cosmos / Genie / Marble (only decision-useful) | TBD |
| `vlm-spatial-reasoning/` | SpatialVLM / SpatialBot / 3DSRBench / BLINK | TBD |
| `physics/` | PhysGaussian / PhysGen / diff-physics + neural rendering | TBD |
| `sensor-physics/` ★ | ToF / LiDAR / active-IR / stereo + multimodal fusion (industry's missing axis) | **`active_nir_850nm_for_embodied_ai.md` (W1)** |
