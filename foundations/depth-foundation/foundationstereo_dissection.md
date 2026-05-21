# FoundationStereo (FoundationStereo 立体匹配基础模型解构 — NVIDIA 2024)

> **Published**: 2024 (arXiv ID TBD UNVERIFIED)
> **Paper**: NVIDIA — *FoundationStereo* `arXiv link TBD UNVERIFIED`
> **Team**: NVIDIA
> **Core position**: Stereo matching foundation model — RAFT-Stereo lineage architecture + foundation-feature backbone + large synthetic corpus → zero-shot generalization across Middlebury / KITTI / ETH3D without per-domain fine-tune. Cheapest passive metric depth source if you can put two cameras on the robot.

**Status:** v1.1 — backfilled to AGENTS.md 14-item template 2026-05-21. Hyperparams marked UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · metric-depth foundation (stereo)
**TL;DR:** FoundationStereo (NVIDIA 2024, `[arXiv link TBD]` UNVERIFIED) is the stereo answer to the "train on huge synthetic, zero-shot everywhere" recipe that worked for Depth Anything and VGGT. It beats the RAFT-Stereo (Lipson et al. 2021) lineage on zero-shot generalization across domains — Middlebury, KITTI, ETH3D, in-the-wild — **without per-domain fine-tuning**. For robotics it's the cheapest way to get *metric* depth without LiDAR: if you can put two cameras on your robot with a known baseline, FoundationStereo gives you meters out of the box. The Jetson deployability is the part that matters.

### X-Ray (non-expert friendly)

(a) Stereo gives metric depth from geometry alone (`Z = f·B/d`); the historical problem is *matching* (textureless, repetitive, occlusion). RAFT-Stereo / SGBM needed per-domain tuning. (b) FoundationStereo brings the Depth Anything recipe to stereo: foundation-feature backbone + large synthetic corpus → zero-shot generalization. (c) For spatial AI engineers: cheapest passive metric depth — global-shutter stereo + FoundationStereo + VIO is a credible 2026 drone stack.

### 📍 Research Landscape Timeline

```
SGBM 2005 ─► PSMNet 2018 ─► RAFT 2020 ─► RAFT-Stereo 3DV 2021 ─► ★ FoundationStereo NVIDIA 2024 ─► distilled/edge variants 2026+ ─► fused with monocular metric 2027+
```

FoundationStereo applies the foundation-model recipe to stereo matching. Open downstream: edge distillation and fusion with monocular Metric3D under one feed-forward backbone.

---

## 1 · Why stereo foundation models matter for robotics

Stereo is the only passive optical depth method that's metric without monocular tricks. Baseline + known calibration → triangulation → meters, full stop. **The historical problem isn't the geometry, it's the matching** — finding correspondences across textureless walls, repetitive patterns (brick, tile, fence), and occlusion boundaries. Classical block-matching (OpenCV SGBM) handles benign scenes; the RAFT-Stereo lineage pushed accuracy but still needed per-dataset fine-tuning to generalize.

FoundationStereo brings the foundation-model recipe — **massive synthetic training corpus + scale-invariant feature backbone → zero-shot generalization** — to stereo matching. The bet is the same as Depth Anything's: synthetic data is now good enough, and a strong pretrained backbone (vision transformer or convolutional) is robust enough that fine-tuning per domain is no longer necessary. For robotics this is huge — drop in a stereo rig, get metric depth, no scene-specific calibration loop.

> ⚡ **Eureka Moment**: Stereo accuracy is bottlenecked by *feature quality*, not by the cost-volume architecture. RAFT-Stereo's GRU-iterative refinement was already strong — but per-domain fine-tune was needed because the feature encoder was trained on small stereo datasets. **Swap in a foundation-feature backbone (DINOv2 / EDM-style pretrained on internet imagery) and the per-domain tune disappears.** Architecture stays RAFT-Stereo's lineage; the front-end is what changes.

---

## 2 · The recipe

> 📌 **Napkin Formula**: `Z = f · B / d`, where `d = StereoMatcher(left, right; foundation_features)`. Metric depth is geometry (calibrated baseline + focal length) once you have correct disparity; the contribution is making disparity zero-shot accurate.


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

## 3.5 · Worked example — drone stereo at 5 m

1 kg drone, 10 cm baseline global-shutter pair, `f ≈ 600 px` UNVERIFIED, Orin Nano.

- **At 5 m**: `d = f·B/Z = 12 px`; sub-pixel ~0.1 px → precision ~0.04 m UNVERIFIED.
- **At 30 m**: `d = 2 px` → precision ~1.5 m. Range collapses geometrically.
- **Latency**: ~50 ms / pair at 12 iters UNVERIFIED → ~20 Hz, fits control loop.
- **Failure**: textureless ceiling / repetitive fence drops matcher confidence; fall back to IR projector.

Stereo is precise short-range, degrades quadratically; pair with monocular metric for long-range.

---

## 4 · Where it breaks

- **Textureless surfaces** — better than RAFT-Stereo, still not perfect. Active stereo (projected pattern) wins here regardless of matcher quality.
- **Repetitive patterns** (brick, tile, fence) — matcher latches onto wrong period. Foundation models help, don't eliminate.
- **Specular reflection** — left and right see different highlights → no correspondence.
- **Short baseline at long range** — geometric SNR collapses (5 cm baseline → ~1% disparity precision at 10 m, guessing at 30 m). No matcher fixes this.
- **Rolling-shutter under fast motion** → fake disparity. Use global-shutter for drone / racing.
- **Edge compute cost** — 32 GRU iterations on Jetson Nano is not real-time `UNVERIFIED actual numbers`.

### 4.x · Hidden Assumptions

Upstream assumptions whose violation breaks the metric output:

- **Accurate calibration** (baseline + intrinsics + rectification) — error propagates linearly; dominant noise source.
- **Synced global-shutter** — rolling shutter under motion → fake disparity.
- **Sufficient texture** — textureless / repetitive degrade even foundation features; IR projector helps.
- **Baseline-to-range ratio** — geometric; short baseline at long range collapses regardless of matcher.
- **Lambertian surfaces** — specular highlights differ left/right → no correspondence.
- **In-distribution domain** — underwater / IR-only need fine-tune.

If violated, you get plausible-looking metric depth with silent geometric errors — particularly bad at long range where the disparity SNR is already weak.

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

**Interview Tip**: When asked "stereo vs monocular metric depth," the right answer is *"different failure modes — stereo fails on textureless / specular / short baseline at long range; monocular fails on wrong intrinsics / out-of-distribution domain."* FoundationStereo is the zero-shot stereo answer; pair with Metric3D where stereo geometry collapses (long range, occluded camera). Don't pick one — fuse.

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
