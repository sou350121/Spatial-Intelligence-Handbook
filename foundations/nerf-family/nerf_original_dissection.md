# NeRF 原作解构 (NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis)

> **Publication:** ECCV 2020 (best paper)
> **Paper:** Mildenhall et al. arXiv: https://arxiv.org/abs/2003.08934
> **Core position:** The paper that turned novel-view synthesis from a graphics pipeline into a differentiable optimization, and made "scene as neural function" viable.

**Status:** v1 — opinionated. Numbers from paper unless `UNVERIFIED`.
**TL;DR:** NeRF's contribution was not the MLP. It was the combination of (1) classical volumetric rendering as the differentiable forward model, (2) positional encoding to break the MLP's low-frequency bias, and (3) 5D input (xyz + view dir) for view-dependent effects. Each piece existed pre-2020. Putting them together as a per-scene optimization is what rewrote the rules — and what guaranteed the hours-of-training pain every follow-up tried to fix.

**X-Ray.** Before NeRF, photoreal novel-view synthesis needed multi-view stereo + mesh + texture (brittle on transparent / reflective) or light-field rigs (impractical). NeRF parametrized scene as `(x,y,z,θ,φ) → (RGB, σ)`, trained an MLP by rendering known views and comparing to GT. Photorealistic 3D from ~50 RGB images, no mesh, no MVS. For spatial-intelligence researchers, NeRF was the first credible "scene-as-neural-network" — the conceptual ancestor of every learned 3D representation since (3DGS included).

## 📍 Research panorama timeline

```
1996         2014         2019           2020          2022          2023            2025?
Light    ► PointNet  ► DeepSDF /     ► NeRF (ECCV) ► Instant-NGP ► 3DGS         ► Feed-forward
fields     (points)    OccNet          YOU ARE HERE   (mins not     (SIGGRAPH,    3D (VGGT,
(Levoy)                (implicit 3D)                  hours)        100 FPS)      no per-scene)
                                       └─ per-scene MLP, hours train, sub-1 FPS render ─┘
```

NeRF sits where light-field / implicit-3D ideas collided with positional-encoded MLPs. Everything 2021–2024 iterates on its weaknesses.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Input | Output |
|---|---|---|
| Positional encoding | `(x,y,z,θ,φ)` | High-freq feature (60 + 24 dims) |
| 8-layer MLP_σ | encoded xyz | density σ + 256-d feat |
| 1-layer MLP_c | feat + encoded view dir | RGB |
| Volume renderer | (σ, RGB) along ray | Pixel color |

MLP is ~1M params. Work is in *192 evals per pixel* (coarse 64 + fine 128 hierarchical sampling), × 800×800 pixels, × tens of thousands of iterations.

### 1.2 ⚡ Eureka moment

> **Volumetric rendering is differentiable end-to-end if the scene is a continuous function — and positional encoding is the only thing that lets a small MLP represent a high-frequency continuous function.**

Take either piece away and NeRF fails. No volumetric rendering → no pixel-level gradients into the scene. No positional encoding → MLP learns a blurry low-frequency fit (paper's Figure 4: same net, no encoding, foggy potato).

### 1.3 Flow diagram

```
   Camera pose                          Pixel color (GT)
        │                                       │
        ▼                                       │
   sample N points along ray                    │
        │                                       │
        ▼                                       │
   positional encoding → MLP_σ → σ              │
        │                                       │
        ▼                                       │
   MLP_c(+view dir) → RGB                       │
        │                                       │
        ▼                                       │
   Σ Tᵢ(1-exp(-σᵢδᵢ))cᵢ ──► Predicted RGB ──► MSE
                                                │
                                                ▼
                                       Backprop to MLP weights
```

---

## 2 · Math core

### 📌 Napkin Formula

```
C(ray) = ∫ T(t) · σ(r(t)) · c(r(t), d) dt        # alpha-blend density-weighted color
PE(p) = [sin(2⁰πp), cos(2⁰πp), ..., sin(2ᴸ⁻¹πp), cos(2ᴸ⁻¹πp)]
```

Integral is classical Max-1995. Encoding lifts 3D coords to 60-dim feature spanning frequencies `2⁰...2⁹`, so the MLP learns high-freq variation without going wide.

### 2.1 Variables

| Symbol | Meaning |
|---|---|
| `r(t) = o + td` | Ray from origin `o` in direction `d` |
| `σ(x)` | Volume density (1/length) |
| `c(x, d)` | View-dependent RGB |
| `T(t) = exp(-∫₀ᵗ σ ds)` | Transmittance |
| `L` | Encoding freq bands (10 xyz, 4 view) |

### 2.2 Quadrature + hierarchical sampling

Discretized by stratified bins: `wᵢ = Tᵢ · (1 − exp(-σᵢδᵢ))`, pixel = `Σ wᵢ cᵢ` — exact alpha-compositing. Coarse pass (64) finds density; fine pass (128) resamples around peaks. **~192 MLP evals/pixel = the slowness.**

---

## 3 · Worked example: one ray, four samples

Ray through a solid sphere at t=2. Samples at t = {0.5, 1.5, 2.5, 3.5}.

| t | σ | δ | α | T | w | color |
|---|---|---|---|---|---|---|
| 0.5 | 0.01 | 1 | 0.010 | 1.000 | 0.010 | sky |
| 1.5 | 0.02 | 1 | 0.020 | 0.990 | 0.020 | sky |
| 2.5 | 20.0 | 1 | ≈1.0 | 0.970 | 0.970 | red |
| 3.5 | 5.0 | 1 | 0.993 | ≈0 | ≈0 | behind |

Pixel ≈ 0.97·red + 0.03·sky — "sphere blocks sky". Gradient flows through every sample; wrong color → MLP updates density + color jointly.

---

## 4 · Engineering view: why it's slow

| Cost | Default |
|---|---|
| Rays / iter | 4096 |
| Samples / ray | 192 (64 + 128) |
| MLP forward | ~1M params, 8-layer, ~5µs / eval on V100 `UNVERIFIED` |
| Iterations | 200–300k |
| Wall-clock | 1–2 days / scene on single V100 (2020) |
| Inference render | ~30s / frame |

`300k × 4096 × 192 ≈ 2.4×10¹¹ MLP forwards per scene`. No way to make this fast without changing the data structure. Every NeRF speedup paper attacks this number.

NeRF training is *embarrassingly per-scene*: zero weight transfer across scenes. The conceptual cliff feed-forward 3D (VGGT, 2024+) finally climbed.

---

## 5 · Data and evaluation

- **Synthetic Blender:** 8 scenes, ~100 views, white background, GT poses. PSNR ~31 dB, LPIPS ~0.05.
- **Real LLFF (forward-facing):** 8 handheld captures, COLMAP poses. PSNR ~26 dB.
- **Metrics:** PSNR / SSIM / LPIPS on held-out views — the protocol every NeRF paper since copied verbatim.

Bounded, foreground-centric, static, well-textured scenes only. Mip-NeRF 360 (2022) is "remove those assumptions", which is why it became the harder benchmark.

---

## 6 · Capabilities and failure modes

**Does:** photoreal novel-view synthesis of static bounded scenes from ~50 calibrated views; view-dependent effects; continuous representation queryable anywhere.

### 6.1 Hidden assumptions

NeRF works only when these hold; each silently breaks in practice:

- **Static scene** — every pixel must correspond to the same world. Moving people, wind-blown leaves → broken. (Fixed in D-NeRF, HyperNeRF.)
- **Dense, calibrated views** — needs COLMAP-accurate per-image poses. <10 images collapses. (Fixed in PixelNeRF, feed-forward 3D.)
- **Single bounded volume** — model queried inside a unit cube; sky / far buildings → garbage. (Fixed in Mip-NeRF 360.)
- **Lambertian-ish lighting** — strong specularity, transparent glass → view-dir MLP can't compensate. (Partially fixed in Ref-NeRF.)
- **Per-scene training is OK** — assumes hours-per-asset is acceptable. Robotics never accepted this. (Instant-NGP fixed speed; feed-forward 3D fixed "per-scene at all".)

Each follow-up picks one and patches it — which is why the lineage *fragmented*: combining 3–4 variants to get a usable system, while 3DGS folded most into a single representation.

---

## 7 · Comparison and interview tip

| Aspect | NeRF | Instant-NGP | Mip-NeRF 360 | 3DGS |
|---|---|---|---|---|
| Training | 1–2 days | ~5 min | ~7h `UNVERIFIED` | ~30 min |
| Render | <1 FPS | ~10 FPS | <1 FPS | 100+ FPS |
| Scene scale | Bounded | Bounded | Unbounded | Bounded |
| Editable? | No | No | No | Yes |
| Best for | Teaching | Fast experiments | Quality bench | Robotics |

> **🎤 Interview tip.** "Why was NeRF a big deal?" — Right answer: *"It was the first time differentiable volumetric rendering + positional encoding combined into a credible end-to-end pipeline; everything since 2020 — including 3DGS — patches one of NeRF's specific weaknesses (speed, scale, dynamics, editability)."* Wrong: "First MLP for 3D." DeepSDF / OccNet predated it; NeRF's contribution is the *rendering* contract, not the network.

---

## References

- **NeRF** — Mildenhall et al. *ECCV 2020.* https://arxiv.org/abs/2003.08934
- **DeepSDF** — Park et al. *CVPR 2019.* https://arxiv.org/abs/1901.05103
- **Instant-NGP** — see `instant_ngp_dissection.md`
- **Mip-NeRF 360** — see `mip_nerf_360_dissection.md`
- **3DGS** (successor) — `foundations/3dgs-family/3dgs_original_dissection.md`

## Boundary

Dissects original NeRF only. Does **not** cover surface-recon NeRFs (NeuS, VolSDF), generative (DreamFusion), or dynamic (D-NeRF). Speed / scale follow-ups are siblings in this directory; displacement story is in `foundations/3dgs-family/`.

---

[← Back to NeRF Family README](./README.md)
