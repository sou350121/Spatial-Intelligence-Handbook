# Metric3D v1 + v2 (Metric3D 度量单目深度解构 — ICCV 2023 + 2024)

> **Published**: 2023-07 (v1, ICCV 2023) / 2024-04 (v2)
> **Paper**: Yin et al. (v1) — *Metric3D: Towards Zero-shot Metric 3D Prediction*; Hu et al. (v2) — *Metric3D v2: A Versatile Monocular Geometric Foundation Model*
> **Team**: HKUST + ANT Group + JD Explore
> **Core position**: First monocular depth model to output **meters** across arbitrary cameras via a canonical-camera transformation — every input is geometrically rectified to a fixed virtual focal length, so the depth head learns "one camera" metric depth.

**Status:** v1.1 — backfilled to AGENTS.md 14-item template 2026-05-21. Hyperparams marked UNVERIFIED.
**Wedge tier:** W1 · metric-depth foundation
**TL;DR:** Metric3D (Yin et al. *ICCV 2023*, arXiv 2307.10984 `UNVERIFIED ICCV vs preprint date`) is the first monocular depth model that **outputs meters across arbitrary cameras** without per-camera fine-tuning. The trick is a **canonical-camera transformation** — every input image is geometrically rectified to a fixed virtual focal length before prediction, so the depth head only has to learn "metric depth on one camera." v2 (2024) extends this to surface normals and adds a stronger backbone. **If your robot needs meters from a single RGB camera, this is the first model to look at.** It's the load-bearing answer to the relative-vs-metric trap that kills Depth Anything v2 for grasp pose.

### X-Ray (non-expert friendly)

(a) Monocular depth is fundamentally ambiguous (`s = f·w/Z` has two unknowns per pixel) — MiDaS/Depth Anything dodge by predicting relative depth, useless for "stop at 5 m." (b) Metric3D makes camera intrinsics *explicit*: resize every input to a canonical focal length `f_canon`, predict in canonical frame, then rescale `D_real = D_canon · (f_real / f_canon)`. (c) For spatial AI engineers: if your robot has a calibrated wrist cam, this gives meters from a single RGB input without LiDAR — but pass wrong intrinsics and the output is silently wrong by the ratio.

### 📍 Research Landscape Timeline

```
ZoeDepth 2023 ─► ★ Metric3D v1 ICCV 2023 ─► Metric3D v2 2024 ─► UniDepth (intrinsics-free) CVPR 2024 ─► VGGT-class multi-view 2025 ─► fused with stereo 2026+
```

Metric3D is the canonical-camera anchor of the metric monocular lineage. UniDepth removes the intrinsics requirement; VGGT subsumes single-view into multi-view feed-forward.

---

## 1 · Why metric monocular is the hard problem

A camera with focal length `f` looking at an object at distance `Z` sees it at image-plane size `s = f · w / Z`, where `w` is real-world width. Two unknowns (`Z`, `w`), one observation (`s`). **Monocular depth from a single image is fundamentally ambiguous** — the same image is produced by a near small object and a far large one. MiDaS / Depth Anything dodge the ambiguity by predicting relative depth (up to affine). That's fine for visualization, useless for "stop at 5 m."

What you actually need for metric depth from a single RGB is **a prior linking `s` to `w`** — a learned prior over object scales in the training distribution. This works fine if you train and test on one camera (intrinsics implicitly encoded), and breaks the moment you swap cameras (a 35 mm phone sensor and a fisheye drone cam see the same scene at different `s`). Metric3D's contribution is making the intrinsics **explicit** to the network so cross-camera transfer is principled.

---

> ⚡ **Eureka Moment**: Make the camera prior an **explicit network input**, not a hidden data assumption. By resampling every image to a single canonical focal length, the depth head sees one intrinsics distribution at train time and one at inference — the scale ambiguity that kills MiDaS-lineage models simply disappears. Same trick (in spirit) as positional encoding in NeRF: surface the geometry, don't hide it.

## 2 · The canonical-camera transformation

> 📌 **Napkin Formula**: `Resize(image; f_real → f_canon) → DepthHead → D_canon → D_real = D_canon · (f_real / f_canon)`. Metric depth is equivariant to focal-length scaling; the canonical resize exploits that equivariance to collapse all cameras into one training distribution.


| Step | What happens |
|---|---|
| Input | RGB image + camera intrinsics `K` (fx, fy, cx, cy) |
| Canonical resize | Image is resampled so that effective focal length equals a fixed canonical `f_canon` `UNVERIFIED value, typically ~1000 px` |
| Network forward | DPT-style depth head predicts metric depth in canonical-camera frame |
| Inverse transform | Output rescaled by `f_real / f_canon` to recover metric depth in real-camera frame |

```
RGB + K_real
    │
    ▼
 canonical resize ── (f_canon, K_canon)
    │
    ▼
 ViT encoder ─► DPT decoder ─► metric depth D_canon
    │
    ▼
 D_real = D_canon · (f_real / f_canon)
```

The insight is that **metric depth is equivariant to focal-length scaling** — if you double the focal length, depths halve (in pixel-implied units). By collapsing all cameras to a single canonical focal length at training and inference time, the network sees a single intrinsics distribution. **The scale ambiguity disappears because the camera prior is no longer hidden in the data — it's a network input.**

This is the same trick (in spirit) as positional encoding in NeRF, or normalized device coordinates in graphics — making the geometry explicit instead of relying on the network to memorize it.

---

## 3 · v1 vs v2

v1 (ICCV 2023) lands the canonical-camera contribution with a ConvNeXt / ViT backbone `UNVERIFIED which is primary` and ~8M training images across 11 datasets `UNVERIFIED`. v2 (2024) scales to ViT-Large + Giant, adds a **surface-normal head** under a joint loss (helps depth quality at occlusion boundaries `UNVERIFIED magnitude`), and widens the training mix with more synthetic. Architecture-wise it's a straightforward scale-up; the canonical-camera trick is unchanged.

---

## 3.5 · Worked example — wrist cam grasp pose

A manipulator wrist cam, calibrated `fx = fy = 750 px`, looking at a mug 0.5 m away.

- **Canonical** (`f_canon = 1000 px` UNVERIFIED): resize 1.33×, predict `D_canon = 0.667 m`.
- **Inverse**: `D_real = 0.667 × 750/1000 = 0.500 m`. ✅

Pass wrong intrinsics (`fx = 1050` for a 50 mm, actual 28 mm with `750`):
- Resize 0.952×, different image content → different `D_canon`.
- Effective depth wrong by ~1.4× — gripper plunges past the mug. **Silent failure.**

Calibrate twice.

---

## 4 · Where it matters

Ship it for: manipulation grasp pose with calibrated wrist cam, tabletop bin picking, drone slow-flight obstacle distance (expect degradation past 30 m). Overkill for AR occlusion (Depth Anything v2 cheaper). Fails for underwater (texture breaks) and endoscopy (domain shift, needs fine-tune).

**The hard requirement is calibrated intrinsics.** No `K`, no canonicalization. Fine for fixed-camera robotics. For "depth from an internet image" you need either ground-truth `K` or a learned intrinsics estimator — UniDepth (Piccinelli et al. 2024 `UNVERIFIED`) is the intrinsics-free variant.

---

## 5 · Where it breaks

- **Wrong intrinsics → wrong scale**. Pass `K` for a 50 mm lens when you shot at 28 mm and the output depth is wrong by ~1.8×. This is a silent failure mode — output looks plausible.
- **Strong lens distortion** (fisheye, ultrawide) — the canonical resize assumes pinhole. Pre-undistort first, or use a fisheye-aware variant.
- **Unbounded outdoor depth past ~30 m** — same fundamental issue as Depth Anything; metric or not, learned monocular depth tail is unreliable.
- **Reflective / transparent surfaces** — same DPT-lineage failure mode.
- **Domain shift to medical / underwater / synthetic** — needs fine-tune.

### 5.x · Hidden Assumptions

Upstream assumptions whose violation produces silent metric errors:

- **Accurate intrinsics** — canonical resize depends on `K`; wrong `K` → silent scale error.
- **Pinhole model** — fisheye breaks canonical resize; pre-undistort first.
- **In-distribution domain** — daylight dominates; underwater / medical need fine-tune.
- **Near-Lambertian surfaces** — specular / transparent → DPT-lineage failures.
- **Depth ≤ ~30 m** — metric tail unreliable past ~30 m, same monocular issue as Depth Anything.
- **Static scene** — rolling shutter under motion introduces geometric inconsistency.

If violated, the output remains a plausible-looking metric depth map — calibration errors are the dominant silent failure mode in deployment.

---

## 6 · MoGe comparison (the relative-track contender)

[MoGe](./moge_dissection.md) (Microsoft 2024) is the closest relative-track competitor — affine-invariant geometric loss with a multi-task head (point + depth + normal). The contrast is sharp:

| Axis | Metric3D | MoGe |
|---|---|---|
| Output scale | metric (meters) | affine-invariant |
| Needs intrinsics? | yes | no |
| Best for | robotics with calibrated cam | photometric / scene understanding |
| Multi-task head | depth + normal (v2) | point + depth + normal |
| Failure if you violate the contract | wrong meters | misaligned scale at deploy |

**If you need meters: Metric3D. If you don't: MoGe is the geometry-rich relative-track answer.**

---

## 7 · 2-year outlook + falsifiable prediction

The metric-monocular track is the one that gets deployed on robots. Expect intrinsics-free variants (UniDepth-lineage) to win on wild imagery, the canonical-camera trick to become a standard ingredient, and fusion with stereo + IMU to converge into VGGT-lineage feed-forward backbones.

**Falsifiable prediction:** by 2027-06 a major manipulation product (Figure, 1X, Apptronik, or similar) will publicly disclose a Metric3D-lineage model in its perception stack. If all stay on RGB-D (RealSense / structured light) the prediction misses.

**Interview Tip**: When asked "how do you get metric depth from a single RGB camera," the trap answer is "you can't." The right answer: *"Metric3D's canonical-camera transformation — surface the intrinsics as a network input, exploit focal-length equivariance."* Pair with a note that you need calibrated `K` and the result is silently wrong if `K` is wrong.

---

## For the reader

- **Manipulation engineer** — start here, not at Depth Anything. Calibrate your wrist cam and ship.
- **Aerial engineer** — useful for slow-flight inspection; replace with stereo + VIO for racing or outdoor (see [`crossing/scale-comparison/`](../../crossing/scale-comparison/)).
- **AD engineer** — useful as a metric pretrain; production still wants LiDAR + stereo.
- **Researcher** — the canonical-camera trick is more general than depth. Anything geometry-aware can borrow it.

---

## References

- Metric3D v1 — Yin et al. *ICCV 2023*. https://arxiv.org/abs/2307.10984 `UNVERIFIED venue`
- Metric3D v2 — Hu et al. 2024. https://arxiv.org/abs/2404.15506 `UNVERIFIED arXiv ID`
- UniDepth — Piccinelli et al. *CVPR 2024*. https://arxiv.org/abs/2403.18913 `UNVERIFIED`
- ZoeDepth — Bhat et al. 2023. https://arxiv.org/abs/2302.12288
- MoGe — see [`moge_dissection.md`](./moge_dissection.md)

## Boundary

This file dissects Metric3D's canonical-camera contribution. Relative-depth comparison lives in [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md) and [`moge_dissection.md`](./moge_dissection.md). Cross-embodiment scale debate is [`crossing/scale-comparison/`](../../crossing/scale-comparison/). Bridge to VLA action heads is [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) — note the `scale_flag` contract.
