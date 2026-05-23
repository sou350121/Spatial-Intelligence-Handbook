# Why Your Tabletop Depth Foundation Model Fails Outdoors

**Status:** v1 — opinionated draft. Range / latency / sensor numbers marked `UNVERIFIED` need rig-side validation.
**Wedge tier:** W1
**TL;DR:** Depth Anything wins on a 0.3 m tabletop and quietly collapses past 30 m unbounded — not because the model is bad, but because *relative depth from a monocular RGB image is a fundamentally different physical problem at cm scale vs km scale*. The first depth foundation model that ships across all scales will not be a bigger ViT; it will be a model that *consumes a sensor stack hint* and decides whether to output relative or metric.

---

## 1 · Why the question is interesting (and why surveys miss it)

Depth foundation models — Depth Anything v1/v2 (Yang et al. 2024), Marigold (Ke et al. 2024), Metric3D v2 (Hu et al. 2024) — are routinely benchmarked on NYUv2 (indoor, 0.5–10 m) and KITTI (driving, 5–80 m). They are **rarely** benchmarked on:

- a tabletop scene with a chrome teapot (manipulation, 0.3 m, specular)
- a humanoid stepping over a curb (1–3 m, mixed indoor-outdoor)
- a drone above tree canopy at 80 m AGL (5–500 m, no ground truth available)
- an AUV in 4 m visibility green water (0.5–30 m, particulate scatter)

The reason isn't laziness — it's that *no single embodiment owns all four regimes*. Manipulation researchers care about &lt;2 m. AD researchers care about 5–80 m. Drone and marine engineers don't trust monocular depth at all. The result is that "depth foundation model" surveys treat the failure modes as embodiment-specific quirks rather than what they actually are: **a single relative-vs-metric trap that takes a different shape at each scale band**.

That is exactly the kind of cross-cut that lives in `crossing/`.

---

## 2 · The scale axis nobody draws end-to-end

```
   0.1 m ─── 1 m ─── 10 m ─── 100 m ─── 1 km
    │        │        │         │         │
    │ manip  │humanoid│ ground  │  drone  │  AD highway
    │ 0.3 m  │ 1–3 m  │ 1–50 m  │5–500m AGL│  5–200 m
    │        │        │         │         │
    │            marine AUV (0.5–30 m vis)│
    │        │        │         │         │
    └─ Depth │Depth   │ stereo  │ stereo  │ LiDAR
       Any-  │Anything│ +LiDAR  │  brittle│ + radar
       thing │+IMU    │ + radar │  GPS    │ + camera
       wins  │OK      │ OK      │ INS-IMU │ fusion
```

Reading left-to-right: as range grows, *every property of the scene that monocular depth exploits weakens*:

- **Baseline parallax** — A stereo rig of 12 cm baseline `UNVERIFIED` gives sub-cm depth at 1 m and ±3 m at 100 m (Z² / fB scaling). Monocular has *no* baseline; it leans on learned priors that were trained on scenes where context was rich (texture, ground plane, common-object scale).
- **Atmospheric contrast** — Aerosol scattering eats long-range texture (Koschmieder's law). Drone images at 200 m through summer haze lose the high-frequency detail Depth Anything relies on.
- **Scene prior validity** — A model trained mostly on NYUv2 + driving has seen sofas and lane markings; it has not seen tree canopy from above, ocean surface from below, or a humanoid's hand reaching into a cluttered cabinet.

---

## 3 · The cross-embodiment depth matrix

| | Manipulation | Humanoid | Ground AGV | Drone (low) | Drone (high) | AD highway | Marine AUV |
|---|---|---|---|---|---|---|---|
| Working range | 0.1–0.8 m | 0.5–5 m | 1–50 m | 0.5–30 m | 5–500 m | 5–200 m | 0.3–30 m |
| Latency budget | 100 ms | 50 ms | 50 ms | 20–50 ms | 50–100 ms | 30 ms | 200 ms |
| Metric required? | usually no (relative + grasp servo) | yes (foot placement) | yes | yes | yes | **yes (no fallback)** | yes (DVL helps) |
| Best 2026 stack | Depth Anything v2 + RGB-D (RealSense D435) | Depth Anything + stereo + IMU | Stereo + LiDAR + camera | Stereo (Skydio-class) + IMU | Stereo brittle; GPS-INS + camera | LiDAR + camera + radar | Stereo + DVL + acoustic |
| Depth-foundation today? | ✅ ships | ⚠️ with metric anchor | ⚠️ as redundancy | ⚠️ as redundancy | ❌ range collapses | ❌ tail-risk fatal | ❌ visual fails |
| Failure regime | glossy / transparent | dynamic shadows | low-texture asphalt | wind-shake, motion blur | haze + range | rain + glare + edge cases | scatter + absorption |
| SWaP-C of depth sensor `UNVERIFIED` | RealSense D435 ~30 g, $300 | ZED 2i ~160 g, $500 | Velodyne / Hesai ~600 g, $4k+ | Skydio stereo pair ~50 g | radar 200 g, $800 | full AD stack >$10k | DVL ~3 kg, $30k |

Read this matrix **vertically** — each column is one embodiment's complete depth story. Read it **horizontally** — each row is one constraint that changes by 10–100× across embodiments. The mistake every depth-foundation paper makes is to optimize one row (accuracy) and not notice the others move under their feet.

---

## 4 · The relative-vs-metric trap

Depth Anything v1/v2 outputs **relative inverse depth**. To use it on a robot you must metric-anchor it — typically via a sparse depth source (LiDAR, stereo, RealSense IR projector). The anchor recovers shift and scale.

This works wonderfully at &lt;2 m where:
- The anchor is dense (a RealSense D435 fires ~300k points per frame `UNVERIFIED`).
- The relative-depth prediction is locally consistent (small scene, lots of pixels per surface).
- A 2% scale error means 4 mm at 0.2 m — invisible to a parallel-jaw gripper.

It breaks at >30 m where:
- The anchor is sparse (32-beam LiDAR puts 4–6 returns on a car at 80 m `UNVERIFIED`).
- The relative-depth prediction is *globally* over-smoothed — sky and far ground get squished into similar values.
- A 2% scale error means 1.6 m at 80 m — enough to clip a curb or rear-end at highway speed.

Metric3D v2 and ZoeDepth try to *output metric directly*, conditioned on intrinsics. They help indoors. **They do not generalize across embodiments**: a model trained on KITTI-style intrinsics + ground-plane assumption gives garbage on a tilted drone camera that sees no ground plane at all.

---

## 5 · Failure regime gallery

A few illustrative breaks worth naming:

- **Glossy mug in a manipulation cell** — Depth Anything predicts the *reflection* as the surface. Stereo fails the same way. The 2026 fix is light-field cameras or polarization (Lucid Phoenix-class). See `crossing/failure-modes-atlas/transparent_reflective_deformable.md`.
- **Drone hovering above fog at 60 m AGL** — RGB image has no high-frequency content. Both monocular depth and stereo collapse. Survivable only via radar or descending below the layer.
- **Marine particulate scatter** — Suspended sediment looks like fog but is closer to the camera (1–5 m). Forward-scatter halo around the headlight breaks all RGB descriptors. Only acoustic / structured-light underwater (DIDSON, Tritech) gives reliable depth.
- **Humanoid stepping over a curb at dusk** — Mixed indoor lighting + outdoor low sun + a 15 cm depth discontinuity right where the foot lands. The latency budget is 50 ms because the foot is already moving. Depth Anything's 100 ms inference is too slow on this exact step.

The pattern: **depth foundation models fail at the boundary between their training regime and the deployment regime, and that boundary moves per embodiment**.

---

## 6 · The deployable pattern (today, not 2027)

```
                ┌──────────────────────────┐
   RGB ────────►│ Depth foundation model   │── relative depth
                │ (Depth Anything / DAv2)  │   (dense)
                └──────────────────────────┘
                            │
                            ▼
                ┌──────────────────────────┐
   sparse  ────►│ Metric anchor / fusion   │── metric depth
   range        │ (stereo / LiDAR / radar) │   (dense + scaled)
                │ scale + shift solver     │
                └──────────────────────────┘
```

The dense relative depth from the foundation model is *cheap* — one forward pass. The metric anchor comes from whatever active range sensor the embodiment can afford to fly / drive / dive with. The fusion is a 2-parameter least-squares solve, robust by RANSAC.

This is the pattern shipping in 2026 on manipulation, humanoid, and ground AGV. Drone and AD use a *much* sparser version where the foundation model is a redundancy layer, not the primary. Marine doesn't use it at all yet.

---

## 7 · 2-year outlook + falsifiable prediction

What would close the gap?

1. **Sensor-conditioned depth foundation** — feed the model not just RGB but a sparse depth prior + intrinsics + an embodiment flag. Metric3D v2 is a half-step in this direction.
2. **Sky / ground prior decoupling** — current models fight over sky pixels. Explicit sky segmentation as a side head would help drone and AD long-range stability.
3. **Particulate / atmospheric awareness** — train on synthetic fog / haze / underwater scatter (Aerial Gym + UWSim lineages). The 2026 data does not exist at scale.
4. **&lt;10 ms inference** — distilled depth models for the drone latency budget. Plausible but not free.

**Falsifiable prediction:** before 2027-12, a single depth foundation model will ship that produces *metric* depth with &lt;5% error on (a) NYUv2-style indoor, (b) KITTI-style driving, **and** (c) drone-above-canopy at 50 m AGL. It will not be a scaled-up Depth Anything; it will explicitly consume a sparse range prior. Bet against any paper claiming "monocular metric depth across all scales" without an active-range input.

---

## For the reader

- **Manipulation engineer** — Depth Anything v2 is already your default. Don't extrapolate your success to humanoid foot placement; the latency and metric requirements are different orders of magnitude.
- **Humanoid engineer** — your hardest case is the 0.5–5 m mixed indoor/outdoor transition. Don't pick a depth model that hasn't been validated at *both* ends of your range.
- **Drone / AD engineer** — treat depth foundation models as a redundancy layer in 2026, not a primary. They have not earned safety-of-life trust at your range.
- **Marine engineer** — skip the RGB foundation conversation; your depth comes from acoustics. The cross-over case is shallow-water survey where DVL + stereo + Depth Anything can fuse; that is the one place to watch.
- **Researcher** — items 1 and 3 in §7 are the open lanes. Sensor-conditioned + atmospheric-aware depth is the missing primitive.

---

## References

- Depth Anything v2 — Yang et al. *NeurIPS 2024*. https://arxiv.org/abs/2406.09414
- Metric3D v2 — Hu et al. 2024. https://arxiv.org/abs/2404.15506
- Marigold — Ke et al. *CVPR 2024*. https://arxiv.org/abs/2312.02145
- ZoeDepth — Bhat et al. 2023. https://arxiv.org/abs/2302.12288
- NYUv2 — Silberman et al. *ECCV 2012*.
- KITTI depth — Uhrig et al. *3DV 2017*. https://arxiv.org/abs/1709.07492
- Koschmieder's law (atmospheric extinction) — standard atmospheric optics; see Narasimhan & Nayar *IJCV 2002*. `UNVERIFIED, no single DOI`

## Boundary

This doc compares depth foundation behavior *across scales / embodiments*. It does **not** dissect Depth Anything internals (that's `foundations/depth-foundation/depth_anything_v2_dissection.md` — TBD), nor manipulation-specific RGB-D tooling (`embodiments/manipulation/perception/`), nor the sensor SWaP-C math (that lives in `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md`). Cross-link here for the scale-collapse story.

---

*Last opinion update: 2026-05-21. §7 prediction will be scored at 2027-12.*
