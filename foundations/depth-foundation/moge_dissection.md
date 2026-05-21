# MoGe — Monocular Geometry Estimation

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · relative-depth foundation (geometry-rich)
**TL;DR:** MoGe (Microsoft Research 2024, `[arXiv link TBD]` UNVERIFIED) is the relative-track answer that says "if we're going to be affine-invariant anyway, let's predict the *whole geometry* — point map, depth, normals — under a single affine-invariant loss." It's a useful fork from the Depth Anything line because the multi-task head makes the model more useful as a 3D-scene-understanding backbone, even though the output is still up to scale. **For VLA pretraining and scene reconstruction it's interesting. For robotics-with-meters, it's the wrong track — go to Metric3D.**

---

## 1 · The pitch

The Depth Anything line predicts a single scalar per pixel (disparity, up to affine). The Metric3D line predicts metric depth but requires intrinsics. **MoGe sits between**: predict *geometry* (3D point map + depth + normal) directly from monocular RGB, with a unified loss that is invariant to the global affine of the scene but tight on the *internal* geometry.

The bet is that this lets the model learn richer 3D structure than a depth-only head — surface continuity, normal consistency, occlusion-edge crispness — without committing to meters. **If you need a 3D-aware visual encoder and you're willing to multiply by an externally-estimated scale at deployment, MoGe gives you more than Depth Anything for similar inference cost.**

---

## 2 · Architecture

| Component | Choice |
|---|---|
| Encoder | DINOv2 ViT (S/B/L) `UNVERIFIED breakdown` |
| Heads | Point map + depth + (optionally) normal |
| Loss | Affine-invariant per-scene + geometric consistency between heads |
| Output | Up-to-affine 3D point cloud per image |

```
RGB ──► ViT encoder ──► shared 3D feature
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
        point map       depth        normal
        (X, Y, Z)       (Z)         (nx, ny, nz)
            │             │             │
            └─────── joint affine-invariant loss ───────┘
```

The "affine-invariant point" loss is the contribution worth thinking about — it's a generalization of the MiDaS affine-invariant disparity loss to full 3D. It means MoGe predicts a 3D scene that is correct up to a global scale + offset, but with internally consistent geometry across the three output heads.

---

## 3 · Where it sits in the landscape

| Axis | Depth Anything v2 | MoGe | Metric3D | FoundationStereo |
|---|---|---|---|---|
| Output | relative depth | point + depth + normal (relative) | metric depth | metric depth (stereo) |
| Needs intrinsics? | no | no | yes | calibrated rig |
| Multi-task | no | yes | depth + normal (v2) | no |
| Cost (single-view, ViT-L) | low | medium | medium | n/a (stereo) |
| Best for | viz / pretrain | 3D-aware encoder | robot metric | robot metric (stereo) |

**The clean way to pick:** if you need meters → Metric3D or stereo. If you need a relative depth source → Depth Anything v2 (simpler, more deployed). If you need a 3D-aware visual encoder for downstream learning → MoGe earns its weight.

---

## 4 · Where it breaks

- **Same monocular-RGB failure modes** — transparent / specular / unbounded outdoor.
- **The multi-task head doesn't fix scale** — predicting normals doesn't recover meters. The model is fundamentally affine-invariant; if you forget that, you get the same wrong-meters trap as Depth Anything v2.
- **Deployment overhead** — three heads consume more memory than depth-only; on tight-edge devices it's not obviously worth it over Depth Anything.
- **Documentation maturity** — as of writing the MoGe paper is recent enough that downstream eval coverage is thinner than Depth Anything v2 `UNVERIFIED, check post-2025 surveys`.

---

## 5 · Where to use it

- **VLA pretraining** — feed the point/depth/normal outputs as auxiliary supervision for a policy encoder. The multi-task signal is richer than a single depth head.
- **Offline scene reconstruction** — when you can fit a scale per scene against a known reference.
- **Comparative ablations** — if you're writing a paper that argues "geometry-rich pretrain > depth-only pretrain," MoGe is the strong baseline.

---

## 6 · 2-year outlook + falsifiable prediction

The relative track and the metric track are converging — VGGT (see [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)) already absorbs depth + pose + pointmap into a single multi-view feed-forward model. MoGe's multi-head pattern is a one-view precursor; in 2 years it gets either subsumed by VGGT-lineage models or by a metric-aware MoGe-v2.

**Falsifiable prediction:** by 2027-06 either (a) MoGe v2 ships with metric output (canonical-camera trick) or (b) it's been quietly retired in favor of VGGT-class models for the same use cases. If MoGe remains the active "monocular geometry-rich relative" line untouched, the prediction misses.

---

## For the reader

- **Manipulation engineer** — skip unless you're using it as a pretrain.
- **Aerial engineer** — skip; need meters.
- **VLA researcher** — worth a look as a pretrain target; richer than depth-only.
- **Researcher** — the affine-invariant 3D point loss is the generalizable idea.

---

## References

- MoGe — Microsoft Research 2024. `[arXiv link TBD]` UNVERIFIED
- Depth Anything v2 — see [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- Metric3D — see [`metric3d_dissection.md`](./metric3d_dissection.md)
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193
- MiDaS (affine-invariant loss origin) — Ranftl et al. 2020. https://arxiv.org/abs/1907.01341

## Boundary

This file dissects MoGe as a relative-track multi-task monocular geometry model. For metric monocular, see [`metric3d_dissection.md`](./metric3d_dissection.md). For multi-view feed-forward 3D, see [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md). Cross-embodiment scale debate is [`crossing/scale-comparison/`](../../crossing/scale-comparison/). Bridge to action policies is [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
