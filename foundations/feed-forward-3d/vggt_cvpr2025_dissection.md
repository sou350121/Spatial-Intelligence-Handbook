# VGGT (CVPR 2025) Dissection

**Status:** DRAFT v0.1 — scaffold only, content pending
**Wedge tier:** W1 (one of 5 launch docs)
**Why this doc exists:** VGGT is 2025's hottest spatial representation. The handbook needs an opinionated dissection — not a paper summary — that future cross-embodiment compare pieces can link back to.

---

## Thesis (one sentence)

VGGT collapses multi-view stereo, dense reconstruction, and camera pose estimation into a single feed-forward transformer pass — and that single architectural move is what flips the per-scene-optimization paradigm (NeRF, 3DGS) into a *foundation-model* paradigm where 3D becomes a forward inference output, not an offline fitting target.

---

## Outline

1. **Setup** — what problems pre-VGGT methods (DUSt3R, MASt3R, COLMAP+3DGS) solved separately, where each broke down.
2. **Architecture walk** — the four heads (camera pose, depth, point map, tracking) and the multi-view attention pattern. Shape sanity-check: input N views → output N depth maps + N camera params + global point cloud.
3. **Training data** — which datasets, what label format, scale of compute. Note where the synthetic-vs-real ratio matters.
4. **Where it breaks** — out-of-distribution scale (drone outdoor → unbounded depth), texture-poor scenes (white walls), motion blur, dynamic objects.
5. **Deployment notes** — Jetson Orin inference time, memory footprint, batch-2 tricks. Distillation candidates.
6. **Cross-embodiment implications** — links to `crossing/slam-vio-migration/vggt_vs_drone_vio.md` and `crossing/representation-migration/3dgs-as-simulator-comparison.md`.

---

## Starter references

- VGGT paper (CVPR 2025) — TBD link
- DUSt3R / MASt3R lineage — Naver Labs Europe
- π³ streaming variant — TBD
- Critical commentary: where the community disagrees with the paper's claims

---

## What this doc is NOT

- Not a paper summary (read the abstract).
- Not a tutorial (read the official code).
- Not an end-of-story take (the field is moving weekly; this is calibrated to mid-2026).
