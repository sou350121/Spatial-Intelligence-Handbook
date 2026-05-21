# FoundationStereo

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · metric-depth foundation (stereo)
**TL;DR:** FoundationStereo (NVIDIA 2024, `[arXiv link TBD]` UNVERIFIED) is the stereo answer to the "train on huge synthetic, zero-shot everywhere" recipe that worked for Depth Anything and VGGT. It beats the RAFT-Stereo (Lipson et al. 2021) lineage on zero-shot generalization across domains — Middlebury, KITTI, ETH3D, in-the-wild — **without per-domain fine-tuning**. For robotics it's the cheapest way to get *metric* depth without LiDAR: if you can put two cameras on your robot with a known baseline, FoundationStereo gives you meters out of the box. The Jetson deployability is the part that matters.

---

## 1 · Why stereo foundation models matter for robotics

Stereo is the only passive optical depth method that's metric without monocular tricks. Baseline + known calibration → triangulation → meters, full stop. **The historical problem isn't the geometry, it's the matching** — finding correspondences across textureless walls, repetitive patterns (brick, tile, fence), and occlusion boundaries. Classical block-matching (OpenCV SGBM) handles benign scenes; the RAFT-Stereo lineage pushed accuracy but still needed per-dataset fine-tuning to generalize.

FoundationStereo brings the foundation-model recipe — **massive synthetic training corpus + scale-invariant feature backbone → zero-shot generalization** — to stereo matching. The bet is the same as Depth Anything's: synthetic data is now good enough, and a strong pretrained backbone (vision transformer or convolutional) is robust enough that fine-tuning per domain is no longer necessary. For robotics this is huge — drop in a stereo rig, get metric depth, no scene-specific calibration loop.

---

## 2 · The recipe

| Component | Choice |
|---|---|
| Architecture | RAFT-style iterative refinement with foundation feature backbone `UNVERIFIED specifics` |
| Pretrained backbone | DINOv2 / EDM-style image features `UNVERIFIED which` |
| Training data | Large synthetic stereo corpus (SceneFlow-scale + domain mix) `UNVERIFIED size` |
| Cost volume | Multi-scale, sparse correlation |
| Inference | Iterative GRU updates, ~12–32 iterations |

```
left  ──► foundation encoder ──┐
                                ├──► cost volume ──► GRU-iter refinement ──► disparity
right ──► foundation encoder ──┘                                              │
                                                                              ▼
                                                                      Z = f · B / d  (metric)
```

The contribution is two-pronged: **(1) the encoder is pretrained on internet-scale imagery** so features survive domain shift, and **(2) the synthetic training corpus is large and diverse enough** that the matching network learns disparity priors that generalize. Architecture-wise this is RAFT-Stereo's lineage with a smarter front-end.

---

## 3 · Why it beats RAFT-Stereo

| Axis | RAFT-Stereo (2021) | FoundationStereo (2024) |
|---|---|---|
| Zero-shot generalization | weak without fine-tune | strong without fine-tune |
| Textureless surfaces | struggles | handles `UNVERIFIED magnitude` |
| Deployment complexity | per-rig fine-tune | drop-in with known baseline |

The win isn't a new architecture — it's the foundation-model recipe applied to stereo. For offline mapping the answer is "swap." For closed-loop control at >50 Hz, verify Jetson latency before swapping — RAFT-Stereo has years of edge-hardware optimization.

---

## 4 · Where it breaks

- **Textureless surfaces** — better than RAFT-Stereo, still not perfect. Active stereo (projected pattern) wins here regardless of matcher quality.
- **Repetitive patterns** (brick, tile, fence) — matcher latches onto wrong period. Foundation models help, don't eliminate.
- **Specular reflection** — left and right see different highlights → no correspondence.
- **Short baseline at long range** — geometric SNR collapses (5 cm baseline → ~1% disparity precision at 10 m, guessing at 30 m). No matcher fixes this.
- **Rolling-shutter under fast motion** → fake disparity. Use global-shutter for drone / racing.
- **Edge compute cost** — 32 GRU iterations on Jetson Nano is not real-time `UNVERIFIED actual numbers`.

---

## 5 · Deployment patterns

- **Global-shutter stereo + FoundationStereo on drone** — outdoor obstacle distance, metric, no LiDAR. Sweet spot for sub-1 kg inspection drones.
- **Stereo + active IR projector + FoundationStereo** — indoor manipulation; projector fills textureless surfaces.
- **Offline mapping** — full iteration count, best accuracy, batch post-mission.
- **Hybrid: RAFT-Stereo at 60 Hz for control, FoundationStereo at 5 Hz for map** — same pattern as VGGT + VIO in [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md).

Jetson rough numbers (always benchmark your exact rig): Orin Nano ~10–20 Hz at 640×480 with reduced iterations `UNVERIFIED`; Orin AGX ~30 Hz at 1280×720 `UNVERIFIED`; Xavier NX marginal, likely needs distillation `UNVERIFIED`.

---

## 6 · 2-year outlook + falsifiable prediction

Stereo foundation models are riding the same wave as monocular depth foundation models — synthetic + foundation backbone → zero-shot generalization. The next two years will see:

1. Distillation to <10 ms on Orin Nano (similar to VGGT-distilled trajectory)
2. Fusion with monocular metric models — "use FoundationStereo where baseline is good, fall back to Metric3D when one camera is occluded"
3. Integration into multi-view feed-forward 3D — VGGT-lineage already absorbs stereo as a special case of multi-view

**Falsifiable prediction:** by 2027-06, at least one public drone autonomy stack (Skydio-tier or open-source) will ship a FoundationStereo-lineage model as the primary stereo matcher. If everyone stays on classical SGBM or RAFT-Stereo through 2027, the prediction misses.

---

## For the reader

- **Manipulation engineer** — pair with active IR for textureless indoor; otherwise RealSense pipeline is fine.
- **Aerial engineer** — cheapest metric depth source. Global-shutter stereo + FoundationStereo + VIO is a credible 2026 stack.
- **AD engineer** — candidate replacement for the stereo matcher only, not the whole stack.
- **Researcher** — the synthetic-corpus recipe is the lesson, same as Depth Anything v2.

---

## References

- FoundationStereo — NVIDIA 2024. `[arXiv link TBD]` UNVERIFIED
- RAFT-Stereo — Lipson et al. *3DV 2021*. https://arxiv.org/abs/2109.07547
- RAFT (optical flow origin) — Teed & Deng *ECCV 2020*. https://arxiv.org/abs/2003.12039
- SGBM — Hirschmüller *CVPR 2005* (classical baseline). no arXiv
- Depth Anything v2 (recipe parallel) — see [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- VGGT (multi-view feed-forward, subsumes stereo) — see [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)

## Boundary

This file dissects FoundationStereo as a stereo matching foundation model. Monocular metric depth is [`metric3d_dissection.md`](./metric3d_dissection.md). Monocular relative depth is [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md). Cross-embodiment scale comparison is [`crossing/scale-comparison/`](../../crossing/scale-comparison/). The "stereo as a low-rate metric anchor under classical VIO" pattern is a special case of the hybrid in [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md). Bridge to action policies is [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
