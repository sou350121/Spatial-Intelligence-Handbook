# Mip-NeRF 360 解构 (Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields)

> **Publication:** CVPR 2022 (oral)
> **Paper:** Barron, Mildenhall, Verbin, Srinivasan, Hedman. Google Research. arXiv: https://arxiv.org/abs/2111.12077
> **Core position:** The NeRF variant that handles unbounded 360° scenes properly and remains the *quality* benchmark 3DGS still chases — four years later.

**Status:** v1 — opinionated. Numbers from paper unless `UNVERIFIED`.
**TL;DR:** Vanilla NeRF and Mip-NeRF assume the scene lives in a bounded box. Real captures don't — point a camera in a backyard and there's sky, distant buildings, ground to the horizon. Mip-NeRF 360 contributes three pieces: (1) disparity-based *scene contraction* mapping unbounded space into a bounded ball, (2) *cone-tracing with gaussian sampling* (from Mip-NeRF) for multi-scale anti-aliasing, (3) *online distillation + proposal sampling* to learn where surfaces are. The LPIPS / SSIM numbers 3DGS reports are compared against Mip-NeRF 360 — and 3DGS still loses on the hardest scenes. **3DGS wins on speed and editability; Mip-NeRF 360 still wins on quality.**

**X-Ray.** Measured by "deployable in a robot stack", 3DGS displaced everything. Measured by "best PSNR on Mip-NeRF 360 benchmark", the 2026 answer is still a NeRF (Zip-NeRF, direct successor). For spatial-intelligence engineers, the lesson is *don't confuse deployment dominance with technical superiority* — 3DGS won because explicit primitives are robotics-friendly, not because gaussian splats are more accurate.

## 📍 Research panorama timeline

```
2020       2021              2022 (Jan)         2022 (Nov)         2023            2024-26
NeRF     ► Mip-NeRF        ► Mip-NeRF 360     ► Instant-NGP-     ► 3DGS displaces ► Zip-NeRF
(ECCV)     (anti-aliasing,   YOU ARE HERE       like speedups     for robotics     (still SOTA
            cone tracing)    unbounded +                                            on Mip360)
                             multi-scale
                             └─ "make NeRF correct" wing ─┘   └─ "make NeRF deployable" wing ─┘
```

Mip-NeRF 360 = the *quality-maximizing* branch. Instant-NGP and 3DGS = the *speed-maximizing* branch. They barely overlap until Zip-NeRF (2023) tried merging.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Function | From |
|---|---|---|
| Scene contraction `f(x)` | Map unbounded ℝ³ → bounded ball radius 2 | **New** |
| Conical frustum sampling | Pixel = cone; sample gaussians along cone | Mip-NeRF (2021) |
| IPE (integrated PE) | Encode gaussian *distribution*, not point | Mip-NeRF (2021) |
| Proposal MLP + NeRF MLP | Proposal predicts where to sample | **New** |
| Online distillation | Proposal supervised by NeRF density | **New** |
| Distortion regularizer | Penalize spread weight histograms; anti-floater | **New** |

### 1.2 ⚡ Eureka moment

> **An unbounded scene becomes bounded if you contract distance in disparity (inverse-depth) space — and the only metric that matters for rendering is angular resolution per screen pixel, which disparity preserves.**

`f(x) = (2 − 1/‖x‖)·(x/‖x‖)` for `‖x‖ > 1` maps the ray at infinity smoothly to a ball of radius 2. A pixel covers more *world space* at 100 m than at 1 m — disparity matches that linear-in-screen-pixels growth.

### 1.3 Flow diagram

```
   Camera ray (cone, not line)
        │
        ▼
   Sample N gaussian frustums along cone
        │
        ▼
   Contract each f(μ), f(Σ)    ── unbounded → bounded
        │
        ▼
   Proposal MLP (density only) → resample N' around peaks
        │
        ▼
   NeRF MLP (σ + RGB)
        │
        ▼
   Volume render → pixel
        │
        ├──► MSE loss
        ├──► Online distillation (proposal ← NeRF σ-histogram)
        └──► Distortion regularizer (anti-floater)
```

---

## 2 · Math core: contraction + cone tracing

### 📌 Napkin Formula

```
contract(x) = x                              if ‖x‖ ≤ 1
contract(x) = (2 − 1/‖x‖) · x/‖x‖           if ‖x‖ > 1

per-pixel cone radius r(t) = base_radius · t
IPE(μ, Σ) = encode gaussian distribution    (vs encode point in NeRF)
```

Three orthogonal pieces; remove any one → degrades.

### 2.1 Why cone tracing matters at scale

NeRF samples points; the same point queried by near- and far-cameras gives the same MLP output. But a *pixel* at the far camera covers a larger world region — the right answer is an integral, not a point. Without cone tracing, contracted unbounded scenes alias horribly because every distant pixel covers a huge contracted volume.

### 2.2 Proposal network + distortion

Proposal MLP (density only) replaces NeRF's coarse pass → ~96 evals/pixel instead of 192. Trained to match NeRF's density via online KL distillation on weight histograms.

Distortion regularizer: `L_dist = ∫∫ w(s)w(t)|s−t| ds dt`. Penalizes spread weight histograms along the ray, concentrating density at well-defined depths. Single regularizer kills most floater artifacts.

---

## 3 · Worked example: contraction in action

Ray from camera at a building 200 m away in a backyard.

| Sample | t (raw) | ‖x‖ | contracted | Meaning |
|---|---|---|---|---|
| Near grass | 1 m | 1.0 | 1.0 | Foreground, no contraction |
| Tree | 5 m | 5.0 | 1.8 | Compressed but localized |
| Building | 200 m | 200 | 1.995 | Near outer shell |
| Sky | ∞ | ∞ | → 2.0 | Boundary |

MLP only ever sees `‖·‖ ≤ 2`. **Sky is a thin shell at radius 2** — distinguishable from the building (1.995) but barely. Without contraction, MLP would need density over four orders of magnitude; with it, same capacity covers everything.

---

## 4 · Engineering view: cost vs vanilla NeRF

| Metric | NeRF | Mip-NeRF 360 |
|---|---|---|
| Training | ~1 day | ~7h `UNVERIFIED` (TPU v3) |
| Render | <1 FPS | <1 FPS |
| PSNR (Mip360 bench) | ~22 dB | **~28 dB** |
| LPIPS | ~0.45 | **~0.25** |
| Reproducible? | Yes (PyTorch) | Painful; ref is JAX |

2026 leaderboard snapshot on the 7-scene Mip-NeRF 360 benchmark `UNVERIFIED`:

- 3DGS vanilla (2023): ~27.4 PSNR
- Mip-NeRF 360: ~27.7
- Zip-NeRF (2023): **~28.5**
- Mip-Splatting (2024): ~27.6

**NeRF lineage still wins by 0.5–1 dB**, loses on wall-clock by ~20×.

---

## 5 · Data and evaluation

- **Mip-NeRF 360 benchmark** (introduced here): 7 unbounded 360° scenes — bicycle, garden, stump, room, counter, kitchen, bonsai. 100–300 images each, COLMAP poses.
- Defined what "unbounded NeRF" means — single most-cited eval in radiance-field papers 2022–2026.
- Does not test dynamic content, low-light, transparency. Quality test, not robustness.

---

## 6 · Capabilities and failure modes

**Does well:** 360° captures of bounded objects with unbounded backgrounds ("backyard with centerpiece"); multi-scale viewing via cone tracing; specular highlights better than vanilla NeRF.

### 6.1 Hidden assumptions

- **Single bounded centerpiece** — contraction assumes a meaningful "inside" (unit ball). No clear center (long street) → wastes capacity.
- **Static, well-calibrated** — inherits NeRF's "static + COLMAP poses" requirements.
- **Slow training acceptable** — ~7h / scene; impractical at scale.
- **No editing** — implicit MLP; can't delete the bonsai keep the kitchen.
- **Sky geometrically degenerate** — collapsed to a thin shell.
- **Pinhole-ish camera** — fisheye / very wide-angle violates linear-cone-radius.

### 6.2 Why this matters vs 3DGS

3DGS's *known weakness* is unbounded: distant gaussians grow huge, blowing up storage. Mip-NeRF 360 contraction *solves this by construction*.

- Quality: Mip-NeRF 360 wins by ~1 dB / ~10% LPIPS.
- Speed: 3DGS by 20–100×.
- Editability: 3DGS.
- Storage: comparable (~500 MB).

Film VFX offline backyard reconstruction → Mip-NeRF 360. Robot needing <10 ms render → 3DGS + Mip-Splatting.

---

## 7 · Comparison and interview tip

| Property | NeRF | Mip-NeRF | **Mip-NeRF 360** | Zip-NeRF | 3DGS |
|---|---|---|---|---|---|
| Anti-aliased | No | Yes | Yes | Yes | Partial |
| Unbounded | No | No | **Yes** | Yes | Limited |
| Training | 1d | 1d | 7h | 5h `UNVERIFIED` | 30m |
| Render | <1 | <1 | <1 | ~1 | 100 FPS |
| PSNR Mip360 | 22 | 24 | 27.7 | **28.5** | 27.4 |

> **🎤 Interview tip.** "If Mip-NeRF 360 is still SOTA on quality, why did 3DGS win deployment?" — Right answer: *"Quality isn't a single number — for robotics, 'render rate × editability × storage' dominates 'last 1 dB of PSNR'. Mip-NeRF 360 still wins offline reconstruction benchmarks; 3DGS wins because its primitives match robotics' operational constraints (inspectable, fast, editable). The two coexist."* Wrong: "3DGS is just better." Better along axes robotics cares about, not on the benchmark this paper introduced.

---

## References

- **Mip-NeRF 360** — Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **Mip-NeRF** — Barron et al. *ICCV 2021.* https://arxiv.org/abs/2103.13415
- **Zip-NeRF** — Barron et al. *ICCV 2023.* https://arxiv.org/abs/2304.06706
- **Mip-Splatting** — Yu et al. *CVPR 2024.* https://arxiv.org/abs/2311.16493
- **3DGS** — `foundations/3dgs-family/3dgs_original_dissection.md`

## Boundary

Dissects Mip-NeRF 360 only. Does **not** cover surface-recon NeRFs (NeuS, VolSDF), sparse-view (PixelNeRF), dynamic, city-scale (→ `block_nerf_large_scenes.md`), or 3DGS displacement (→ `foundations/3dgs-family/`).

---

[← Back to NeRF Family README](./README.md)
