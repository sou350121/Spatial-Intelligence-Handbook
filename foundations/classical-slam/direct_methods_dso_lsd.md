# Direct Methods: DSO & LSD-SLAM (直接法 SLAM 解构)

> **Published:** LSD-SLAM (Engel *ECCV 2014*); DSO (Engel *T-PAMI 2018*, arXiv 1607.02565); SVO 2.0 (Forster *T-RO 2017*) — TUM CV group / UZH RPG
> **Core positioning:** The road **not** taken by mainstream visual SLAM. Direct methods skip features and minimize photometric error on raw intensities — winning on gradient-rich scenes, losing on loop closure and long-term consistency.

**Status:** v1. Numbers `UNVERIFIED`.
**TL;DR:** Direct methods proved you can do visual SLAM **without a descriptor** — track and map directly on pixel intensities at high-gradient regions. Sub-pixel accuracy, semi-dense maps free. Cost: photometric calibration non-negotiable, exposure changes silently destroy everything, loop closure unsolved. DSO survives as ancestor of DROID-SLAM and feed-forward dense methods.

**X-Ray.** Feature SLAM keeps corners (~99% discarded). Direct SLAM keeps every gradient pixel (~2000–10k/frame). Lighter front-end, sub-pixel, semi-dense maps. But photometric calibration mandatory, exposure changes fatal, loop closure unsolved. The field bet on features for a reason; DSO is the demo that explains the bet.

## 📍 Research timeline

```
2011   2014       2014   2016         2021+
DTAM ► LSD-SLAM ► SVO ── DSO (peak) ► DROID-SLAM / learned-BA
└── direct: photometric error on intensities ──┘
└── features lineage ─► ORB-SLAM3
```

DSO is the **peak of classical direct SLAM**: ~2000 sparse residuals, photometrically calibrated, full sliding-window opt. After DSO, action moved to learned dense (DROID-SLAM).

---

## 1 · Architecture

### 1.1 The fundamental split

| | Feature (ORB-SLAM) | Direct (DSO/LSD) |
|---|---|---|
| Optimized | reprojection (3D→2D) | photometric (intensity) |
| Residuals/frame | ~100 features | ~2000 (DSO) – >10k (LSD) |
| Front-end | descriptor + match | gradient only |
| Sub-pixel? | no | yes |
| Loop closure | DBoW2 | hard — §6 |
| Photometric cal. | tolerant | mandatory |
| Map density | sparse | semi-dense+ |

### 1.2 ⚡ Eureka Moment

> **"You don't need to identify what a pixel is — only that it stays the same brightness when you reproject it correctly."**

Commit to it and descriptor extract, matching, and feature-based BA all go away. You get sub-pixel precision and semi-dense maps; you give up loop closure, illumination robustness, scale recovery.

### 1.3 DSO architecture (sparse direct)

```
   Frame → select ~2000 gradient pts (inverse-depth param)
        → Sliding-window photometric BA (7 KFs: poses + depths + affine (a,b); marginalize on slide-out)
        → sparse 3D point cloud
```

LSD-SLAM tracks every gradient pixel + per-pixel probabilistic depth filter → semi-dense map. DSO is **deliberately sparse** for speed.

---

## 2 · Math core

### 📌 Napkin Formula

```
E_photo = Σᵢ Σ_p  wₚ · ρ( I_j(π(K·(R_ij·π⁻¹(p, d_p) + t_ij))) − b_j − e^{a_j−a_i}·(Iᵢ(p) − bᵢ) )
```

For frame `i`, point `p`, project to `j` via pose `(R_ij, t_ij)` + inverse depth `d_p`; minimize affine-brightness-corrected intensity difference. `(a, b)` = per-frame exposure params.

| Symbol | Meaning |
|---|---|
| `Iᵢ(p)` | pixel intensity in frame `i` |
| `d_p` | inverse depth (bounded, handles infinity) |
| `(aᵢ, bᵢ)` | affine brightness: `I' = e^a · I + b` |
| `ρ` | Huber kernel |

**Intuition:** `(a, b)` is what stands between you and exposure-driven crash. DSO's invariant is *photometric*, ORB-SLAM3's is *geometric* — each fails its own way. Sliding window ~7 KFs; direct aims *locally perfect*, not globally consistent.

---

## 3 · Worked-pattern example

Same corridor, two illumination regimes:

| Scenario | ORB-SLAM3 | DSO |
|---|---|---|
| **A** textured walls, smooth light | works | **better** — sub-pixel, ~2× accuracy `UNVERIFIED` |
| **B** flicker + sunlit-zone transition | tolerates ~30% intensity shift | **broken** — affine `(a,b)` saturates, tracking lost |

DSO wins on *clean*, loses on *real-world illumination* — why features dominate production. Only camera-level photometric pre-calibration (response + vignette) keeps DSO running outdoors.

---

## 4 · Engineering: when to pick direct

| Have... | Direct (DSO) | Features (ORB-SLAM3) |
|---|---|---|
| Photometric cal | ✅ free accuracy | — |
| Auto-exposure, uncalibrated | ❌ silent fail | ✅ tolerant |
| Need dense map | ✅ free | ❌ separate step |
| Loop closure | ❌ hard | ✅ DBoW2 mature |
| Motion blur | ❌ gradients smear | ⚠️ also degrades |
| IMU | ⚠️ DSO-VI less mature | ✅ mature |

**Pattern:** direct → research / dense-mapping; features → production. Exception: photogrammetry (BundleFusion-style post-process dense alignment).

**SVO middle ground:** Semi-direct VO (Forster): detect features for selection, track photometrically (sub-pixel direct alignment). Ships at 100+ Hz on drones `UNVERIFIED`; UZH RPG lineage. If forced to pick "one direct method that deploys", it's SVO — not DSO.

---

## 5 · Data & evaluation

DSO — TUM mono + EuRoC: direct beats features 2–3× translational on benign sequences `UNVERIFIED`. LSD-SLAM — TUM RGB-D semi-dense reconstructions. ⚠️ Both **indoor + photometrically calibrated**. Outdoor / aerial / uncalibrated phone = different story.

---

## 6 · Capabilities & failure modes

**Strengths:** sub-pixel tracking; semi-dense maps free; lower CPU on embedded; explicit photometric calibration.

**Weaknesses:** exposure / illumination changes (#1 killer); loop closure unsolved (no descriptors → DBoW2 N/A); large displacements break linearization; gradient-poor regions fail.

### 6.1 Hidden Assumptions

- **Brightness constancy** — foundational. Auto-exposure / HDR / flicker / sun-shadow violate it. Affine `(a,b)` fixes global shifts only.
- **Small inter-frame motion** — aggressive motion → linearization gap → tracking lost.
- **Lambertian surfaces** — specularities (glass, polished floors) break brightness constancy on motion.
- **Photometric calibration available** — most users skip measured response + vignette → silent degradation.
- **No loop closure needed** — non-looping trajectory → unbounded drift.

---

## 7 · Comparison & Interview Tip

| Stack | Front-end | Loop | Map | Ships in |
|---|---|---|---|---|
| ORB-SLAM3 | features (ORB) | DBoW2+Atlas | sparse | indoor RGB-D / AR / manipulation |
| **DSO** | direct (sparse) | weak/none | semi-dense | research / dense reconstruction |
| LSD-SLAM | direct (semi-dense) | FabMap | semi-dense | large-scale mono mapping |
| SVO 2.0 | semi-direct | optional | sparse+depth | UZH aerial PoCs |
| DROID-SLAM | learned dense | learned | dense | offline / GPU |
| VGGT | feed-forward | n/a | dense pointmaps | foundation successor |

> **🎤 Interview Tip.** "Why didn't direct methods win, given DSO's accuracy edge?" — right answer: *"Loop closure and exposure invariance. Direct optimizes the right local objective but inherited no global place-recognition primitive; brightness constancy is hard to enforce outside controlled photometric calibration. ORB-SLAM3 makes a worse local objective work globally; DSO makes a better local objective fail globally."* Wrong: "DSO was worse" — it was structurally different.

---

## Boundary

- ORB-SLAM3 mechanics → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md).
- Aerial real-time VIO (VINS / OpenVINS / DROID) → [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/README.md). Not duplicated.
- VGGT / feed-forward 3D successor → [`foundations/feed-forward-3d/`](../feed-forward-3d/).
- Photometric / sensor calibration workflow → [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md).

---

## References

- DSO — Engel, Koltun, Cremers · *T-PAMI 2018* · https://arxiv.org/abs/1607.02565
- LSD-SLAM — Engel, Schöps, Cremers · *ECCV 2014*
- SVO 2.0 — Forster et al. · *T-RO 2017* · https://rpg.ifi.uzh.ch/svo2.html
- DTAM — Newcombe et al. · *ICCV 2011*
- TUM mono — https://vision.in.tum.de/data/datasets/mono-dataset

---

[← Back to Classical SLAM](./README.md)
