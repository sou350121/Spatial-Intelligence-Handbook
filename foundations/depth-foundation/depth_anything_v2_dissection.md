# Depth Anything v2

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED.
**Wedge tier:** W1 · relative-depth foundation
**TL;DR:** Depth Anything v2 (Yang et al. 2024, arXiv 2406.09414) is the strongest *relative* monocular depth model shipping in 2024–2026 — and the most-mistaken-for-metric model on the shelf. Its win isn't architecture, it's **62M unlabeled images distilled through a teacher-student loop on top of 595K high-quality labeled samples** `UNVERIFIED counts`. Use it for visualization, semantic depth, and as a pretrain. Do **not** use it for grasp pose. The output is up to an unknown affine — multiply by a robot-side scale estimate or you'll drop the cup.

---

## 1 · Why this paper deserves a dissection

MiDaS (Ranftl et al. 2020) defined the relative-depth-generalization template. Depth Anything v1 (Yang et al. 2024a) pushed it with a scaled-up DINOv2 backbone. **v2's contribution is almost entirely a data story**: they argue real-world labeled depth datasets are full of label noise (LiDAR shadow holes, photometric stereo artifacts, kinect IR speckle), and that **synthetic labels + massive unlabeled distillation** beats more real labels.

The lesson generalizes beyond depth — it's the same recipe that worked for SAM-2, DINOv2, and the VGGT lineage (see [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)). For robotics readers, the relevant question is whether this recipe is metric-shaped. **It isn't.** The same data trick that gives Depth Anything v2 its generalization also locks in the relative-only constraint, because unlabeled distillation provides no scale signal.

---

## 2 · Architecture & training recipe

| Component | Choice | Why it matters |
|---|---|---|
| Encoder | DINOv2 ViT-S/B/L/G | Pretrained visual features survive domain shift |
| Decoder | DPT-style (Ranftl et al. 2021) | Stable lineage from MiDaS; nothing fancy |
| Label source | 595K synthetic (Hypersim + vKITTI + 3D Ken Burns + Synscapes etc.) `UNVERIFIED list` | Clean labels, no LiDAR shadow holes |
| Unlabeled corpus | 62M images from SA-1B + Open Images + Places etc. `UNVERIFIED count` | Generalization driver |
| Loss | Affine-invariant SI loss (MiDaS) + gradient matching | Predicts disparity up to scale and shift |
| Distillation | Teacher trained on synthetic only → pseudo-labels 62M → student | The actual contribution |

```
Synthetic labeled (595K, clean)
        │
        ▼
   Teacher model  ───────────► pseudo-labels for 62M unlabeled images
                                       │
                                       ▼
                                Student model (final Depth Anything v2)
```

The architecture matrix between Depth Anything v1 and v2 is almost identical. **What changed is the training corpus and a deliberate switch away from noisy real labels.** That's the headline; everything else is engineering.

---

## 3 · Where it actually wins (and the relative-vs-metric trap)

| Use case | Verdict | Reason |
|---|---|---|
| Photo / video depth visualization | ✅ best in class | Generalizes to phone photos, art, indoor/outdoor with no fine-tune |
| Monocular depth pretrain for downstream task | ✅ strong | DINOv2 features + depth head transfer cleanly |
| AR occlusion / novel view synthesis backbone | ✅ useful | Relative depth is enough; renderer rescales anyway |
| Robot grasp pose | ❌ wrong tool | Output is affine-invariant — no meters |
| Drone obstacle distance | ❌ wrong tool | Same reason; you cannot decide "stop at 5 m" |
| BEV occupancy for AD | ⚠️ pretrain only | Production AD stacks fuse with LiDAR or stereo for scale |

**The trap to avoid:** Depth Anything v2 produces gorgeous depth maps. They look metric. They are not metric. If you take v2 output `d` and multiply by a fitted scale `s` from a single calibration scene, the scale `s` will not hold across scenes — because v2's output is affine-invariant up to **shift** as well as scale, and the shift varies with image content `UNVERIFIED whether v2 fully fixes the shift; v1 definitely had it`. For robotics, this means "fit a global scale once" doesn't work — you need a per-frame metric anchor (stereo, LiDAR, learned + camera intrinsics → see Metric3D).

---

## 4 · Where it breaks

- **Transparent / specular surfaces** — glass, water, mirrors. Inherited from every DPT-lineage model. No principled fix exists at the monocular-RGB level.
- **Unbounded outdoor depth past ~30 m** — the affine-invariant loss compresses the tail; sky and distant buildings collapse to the same disparity bin. For drone or AD this is the dominant failure mode.
- **Tiny isolated objects** — wires, thin railings, hanging cables. Depth bleed from background. Critical for drone obstacle avoidance, less so for tabletop.
- **Cross-domain artifacts when the unlabeled corpus didn't see the domain** — endoscopy, marine, underwater. The 62M unlabeled corpus is mostly internet daylight imagery `UNVERIFIED breakdown`.
- **Fine geometry around occlusion boundaries** — better than v1 but still soft. Use a stereo model if you need crisp object silhouettes.

---

## 5 · Deployment patterns

- **v2-S on Jetson Orin as feature extractor** for a 3D-aware policy encoder — use features, not the depth output.
- **v2-L offline** for scene reconstruction with per-scene scale fit.
- **Don't deploy v2 online for metric tasks** (grasp pose, obstacle distance, planning).

For metric monocular see [`metric3d_dissection.md`](./metric3d_dissection.md); for multi-view feed-forward see [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md).

---

## 6 · 2-year outlook + falsifiable prediction

The relative-depth foundation track will keep winning on generalization benchmarks because the data trick scales further (Depth Anything v3 will probably claim 200M+ unlabeled images `UNVERIFIED`). **But the metric track is where robotics money flows**, because no manipulation or aerial product can ship on relative depth. Expect the two tracks to converge by 2027 via a "metric-aware fine-tune" recipe — train relative on 62M, then fine-tune metric on a small labeled set with camera intrinsics fed in.

**Falsifiable prediction:** before 2027-06 there will be a public "Depth Anything v3 metric" or equivalent variant from the same lab, with a Metric3D-style canonical-camera input. If only relative variants ship through 2027 the prediction misses.

---

## For the reader

- **Manipulation engineer** — useful as a feature pretrain, not as a depth source. Wire your gripper to Metric3D or stereo.
- **Aerial engineer** — skip for live state estimation; might be useful offline for 4D scene reconstruction of inspection flights.
- **AD engineer** — pretrain only. Your production stack already has stereo + LiDAR.
- **Researcher** — the data recipe is the lesson, not the architecture. Apply it to whatever modality has noisy labels.

---

## References

- Depth Anything v2 — Yang et al. *NeurIPS 2024*. https://arxiv.org/abs/2406.09414
- Depth Anything v1 — Yang et al. *CVPR 2024*. https://arxiv.org/abs/2401.10891
- MiDaS — Ranftl et al. *TPAMI 2020*. https://arxiv.org/abs/1907.01341
- DPT — Ranftl et al. *ICCV 2021*. https://arxiv.org/abs/2103.13413
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193

## Boundary

This file dissects Depth Anything v2 as a *relative* monocular depth foundation model. Metric monocular depth is [`metric3d_dissection.md`](./metric3d_dissection.md). The cross-embodiment scale story is [`crossing/scale-comparison/`](../../crossing/scale-comparison/). Bridge to action policies is [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
