# Mip-Splatting — Anti-Aliasing for 3DGS

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED.
**TL;DR:** Vanilla 3DGS looks great at the training camera distance and falls apart everywhere else — zoom in, zoom out, change focal length, and you get visible aliasing. Mip-Splatting's 3D smoothing + 2D dilation fix is small, principled, and the reason 3DGS is usable on drones and VR headsets, not just desktop demos.

Reference paper: Yu et al. "Mip-Splatting: Alias-Free 3D Gaussian Splatting." *CVPR 2024.* arXiv: https://arxiv.org/abs/2311.16493

---

## 1 · The silent failure mode in vanilla 3DGS

3DGS is trained at a specific set of camera intrinsics — pixel size, focal length, image resolution. The gaussians end up sized to match the training-time pixel footprint. As long as you render from a camera that looks similar at inference time, things are fine.

Change the scale and the representation breaks:

- **Zoom in (closer than training)** — gaussians that were sub-pixel during training become multi-pixel at inference. Edges blur, surface detail melts.
- **Zoom out (farther than training)** — gaussians that were multi-pixel at training become sub-pixel at inference. They alias into shimmering, flickering high-frequency noise.
- **Different focal length** — same problem in a different parameterization.

For graphics demos this is a footnote. For embodied AI it is the difference between a representation that ships and one that doesn't:

- A **drone** flying through a 3DGS scene traverses a 20× distance range from a single training capture. Vanilla 3DGS produces visible aliasing at the close and far ends.
- A **VR / AR headset** rendering 3DGS for a user who steps closer and farther changes the apparent scale every second.
- A **manipulator** that trained on demonstrations from a wrist-camera viewpoint cannot re-render those scenes from an external observer camera without scale shift.

Mip-Splatting is the small, principled fix that makes 3DGS scale-robust.

## 2 · Mechanism — the two parts

```
   Training-time gaussians
              │
              ▼
   ┌─────────────────────────────┐
   │ 3D smoothing filter         │
   │   Track the maximum sample  │
   │   frequency (across all     │
   │   training views) at which  │
   │   each gaussian was         │
   │   observed.                 │
   │   Enforce minimum 3D size:  │
   │   gaussian cannot be        │
   │   smaller than the          │
   │   Nyquist limit of its      │
   │   training observations.    │
   └─────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────┐
   │ 2D Mip filter (replaces     │
   │ the standard 2D dilation)   │
   │   At render time, given the │
   │   target pixel footprint,   │
   │   convolve the projected    │
   │   gaussian with a 2D box    │
   │   matching the pixel scale. │
   │   Replaces vanilla 3DGS's   │
   │   fixed dilation kernel.    │
   └─────────────────────────────┘
              │
              ▼
   Rendered image — alias-free across scales
```

Both pieces are tiny code changes — Mip-Splatting is not an architectural redesign. It is a correctness fix.

- The **3D smoothing filter** is the training-time piece. It records, per gaussian, the highest spatial frequency at which the gaussian was ever observed during training. Then at *every* training iteration, it enforces a lower bound on the gaussian's 3D extent so it cannot shrink below what Nyquist allows. This prevents the gaussian set from over-fitting to high-frequency detail that the training cameras did not actually resolve.
- The **2D Mip filter** is the render-time piece. The vanilla 3DGS rasterizer applies a fixed pixel-space dilation to every projected gaussian. Mip-Splatting replaces that with a scale-aware 2D filter that grows with the target rendering pixel footprint. When you render at a smaller pixel footprint (zooming in), the filter shrinks; at a larger footprint (zooming out), it grows. The result is that the projected gaussian always integrates correctly into the target pixel grid.

The two filters are *coupled* — the 3D filter caps the achievable detail during training; the 2D filter resamples that detail correctly at inference. Either alone is not enough.

## 3 · Why this matters for drones and VR

- **Drone altitude change** — capturing at 50 m and inspecting at 5 m moves through 10× scale. Vanilla 3DGS aliases at one end or the other; Mip-Splatting holds up. Any serious drone-side pipeline uses the Mip-Splatting variant.
- **VR / AR head motion** — room-scale head translation covers ~3× distance range to nearby objects. Vanilla shimmers; Mip-Splatting doesn't.
- **Wrist-cam → external-cam re-rendering** — wrist-camera training data at 5 cm rendered as a 50 cm external observer. Same problem, same fix.

Reported PSNR gain on multi-scale benchmarks `UNVERIFIED — Yu et al. report ~1–2 dB on multi-scale Mip-NeRF360` is the easy number. The harder-to-quantify result is "no shimmer" — and shimmer is a distribution shift downstream policies actually pick up on.

## 4 · Deployment guidance (when to bother)

- **Single camera, single distance** (e.g. tabletop manipulation with a fixed external camera) — vanilla 3DGS is fine. Mip-Splatting adds ~5–10% training overhead `UNVERIFIED` for no visible benefit.
- **Multiple cameras, varying distance** (drone, multi-view manipulation, VR) — Mip-Splatting is the correct default. The training-time overhead is small, the inference overhead is negligible, and the artifact reduction is the difference between a representation that survives deployment and one that doesn't.
- **Long trajectory through a scene** (mobile robot navigating a building) — Mip-Splatting is mandatory. The robot's camera traverses every scale.

## 5 · 2-year outlook

Mip-Splatting will quietly become the default. By 2027 expect the vanilla 3DGS code path to be the legacy one; production gaussian-splatting pipelines will start from Mip-Splatting and add their own extensions (dynamic, SLAM, semantic) on top.

**Falsifiable prediction:** by 2027-06, every major open-source 3DGS implementation (gsplat, nerfstudio's gsplat backend, INRIA's reference) will have Mip-Splatting on by default, not as an opt-in flag. The remaining holdouts will be benchmark-replication code, not production stacks.

## References

- **Mip-Splatting** — Yu et al. *CVPR 2024.* https://arxiv.org/abs/2311.16493
- **Mip-NeRF** (the anti-aliasing predecessor in NeRF lineage) — Barron et al. *ICCV 2021.* https://arxiv.org/abs/2103.13415
- **Mip-NeRF 360** (multi-scale benchmark) — Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **3DGS original** (the thing being fixed) — Kerbl et al. *SIGGRAPH 2023.* https://arxiv.org/abs/2308.04079

## Boundary

This doc covers the multi-scale anti-aliasing fix for 3DGS. It does **not** cover:

- Static 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- Dynamic 4D extensions → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- SLAM-coupled gaussians → `foundations/3dgs-family/gs_slam_dissection.md`
- Drone-side deployment → `embodiments/aerial/` (when written)
- VLA consumption of gaussian maps → `bridge-to-vla/feature-cloud-to-action.md`
- Cross-representation comparison across scales → `crossing/representation-migration/`, `crossing/scale-comparison/`
- Feed-forward 3D alternatives → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
