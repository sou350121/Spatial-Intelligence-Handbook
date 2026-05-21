# FoundationPose (新物体 6D 位姿，无需逐物体训练)

> **发布时间**: 2024-03 (CVPR 2024 *best paper* — Wen, Yang et al., NVIDIA)
> **论文 / 模型**: FoundationPose (arXiv 2312.08344)
> **核心定位**: One model that estimates 6D pose for *any* object — with a CAD mesh OR ~16 reference images — without per-object fine-tuning.

**Status:** v1 — opinionated draft. Numbers marked `UNVERIFIED` unless rig-tested.
**Wedge tier:** W1 · pose-foundation default for 2024–2026 manipulation stacks.
**TL;DR:** First 6D pose model that earns "foundation". Drop in any new object — mug, screwdriver, packing-tape roll — and get pose without retraining. Render-and-compare + diffusion-style iterative refinement, scored by a model trained on ~1M+ synthetic objects. The reason 2026 teams shouldn't be training per-object pose heads.

**X-Ray.** Pre-2024 pose models (PoseCNN, DenseFusion, GDR-Net) required *per-object training*. FoundationPose breaks the wall: train once on huge synthetic data, generalize to any unseen object — mesh or ~16 reference images. Object pose joined the foundation-model club in 2024, alongside depth (Depth Anything) and 3D (VGGT precursors).

---

## 📍 研究全景时间线

```
2017       2019         2021       2022          2024 (HERE)         2025+
PoseCNN ─► DenseFusion ► GDR-Net ► MegaPose ───► FoundationPose ──► video / temporal
└─ per-object supervised ──┘  └── novel obj, mesh required ──┘  └─ mesh-free ─┘
```

First paper handling unseen objects *without* mesh at production accuracy. Temporal / video successors are early-stage in 2026.

---

## 1 · Architecture overview

### 1.1 System component comparison

| Module | Input | Output |
|---|---|---|
| Hypothesizer | RGB-D crop + obj rep | N pose hypotheses |
| Refinement (diffusion-style) | hypothesis + render | refined (multi-step) |
| Scorer | rendered vs observed | scalar score |
| Object rep (mesh-free) | ~16 ref images | implicit neural object |

**Render-and-compare wrapped in a learned scorer**, with diffusion-style iterative refinement. The *scorer is the foundation model* — generalizes across objects because it saw a million in training.

### 1.2 ⚡ Eureka Moment

> **Treat pose as "score how well a rendered hypothesis matches the observation" — and make the scorer the foundation model, not the regressor.**

Earlier work regressed 6D pose from features → fragile per-object. FoundationPose flips it: render N candidates (free, deterministic) and *learn to score* (generalizes from synthetic prior).

### 1.3 Information flow

```
   RGB-D crop ──┐
                ▼
   (mesh) ─► hypothesizer ─► N candidates ─► render each ─► scorer ─► top-k
   or                                                                    │
   (16 refs) ─► implicit obj ──────────────────────────────────────────► ▼
                                                  refine (K iters) → final pose + confidence
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  pose*  =  argmax_{T in candidates}  scorer( render(obj, T),  observed_crop )
```

Pose is *selected* from a candidate set, not regressed. The scorer is the learned generalization machine.

| Symbol | Meaning |
|---|---|
| `T = (R, t)` | 6D pose |
| `render(obj, T)` | rasterized RGB-D at `T` |
| `scorer(·, ·)` | learned contrastive scorer |
| `K` | refinement iterations (~5 `UNVERIFIED`) |

**Intuition.** Rendering is the geometric oracle; the scorer is the perceptual oracle. Combined → pose becomes *search* in pose space, scorer as navigation gradient.

---

## 3 · Worked example: pose of a screwdriver

RealSense D435, screwdriver detected → crop. CAD mesh available.

1. **Hypothesize** ~252 rotation hypotheses (icosphere × in-plane); translation from depth centroid.
2. **Render** each candidate into the crop.
3. **Score** (rendered, observed) → 252 scalars; top-5 within ~10° of GT.
4. **Refine** top-5 × K=5 steps; top-1 → ~2° rotation, ~3 mm translation `UNVERIFIED`.
5. **Final score** ~0.92 → ship to grasp planner.

End-to-end ~80–150 ms desktop `UNVERIFIED`, ~300–550 ms Orin `UNVERIFIED`. Mesh-free mode replaces the renderer with the implicit neural object.

---

## 4 · Engineering view

| Stage | Desktop `UNVERIFIED` | Orin `UNVERIFIED` |
|---|---|---|
| Render (×252) | 20–40 ms | 80–150 ms |
| Scoring | 30–50 ms | 100–200 ms |
| Refinement (×5) | 30–60 ms | 100–200 ms |
| **End-to-end** | **~80–150 ms** | **~300–550 ms** |

Multi-object scales linearly unless batched. Single-object 30 Hz tracking on Orin is feasible after distillation; pose-of-everything-on-table at 30 Hz is not 2026-ready on edge.

**Deployment.** New SKU: 16 photos + 30-s mesh-free fit → ready. Tracking mode: re-detect every Nth frame, refine from prior → ~30 ms/frame `UNVERIFIED`.

---

## 5 · Data & eval

Trained on ~1M+ synthetic objects (paper claim; exact `UNVERIFIED`) from Objaverse / ShapeNet, with domain-randomized lighting / materials / backgrounds. Evaluated on LM-O, YCB-V, T-LESS — beats MegaPose by 6–18 AR points `UNVERIFIED`. Mesh-free variant lags model-based by a few AR points but is the more important real-world capability.

---

## 6 · Capabilities & failure modes

**Wins:** novel-SKU onboarding in minutes; moderate-occlusion robustness; mesh-free path for objects without CAD.

**Fails on:** severe symmetry without texture (rotation ambiguity inherent); transparent / specular objects (depth sensor fails first); objects <~10 mm `UNVERIFIED`; heavy clutter without clean 2D detection.

### 6.1 Hidden Assumptions

- **Depth channel available and reliable.** RGB-only degrades 5–15 AR `UNVERIFIED`. Reflective metal → effectively RGB-only.
- **Object rigid.** Cables / fabric out of scope; articulated objects give dominant-link pose only.
- **Reference images cover the rotational hull (mesh-free).** Single hemisphere doesn't generalize to the back side.
- **Object ≥~10 mm in image.** Tiny SMD / fine screws below effective resolution.
- **Lighting roughly photo-realistic.** Domain randomization covers wide variation, not monochrome IR.

These are *input-domain* assumptions, not parameter issues — fine-tuning won't fix them.

---

## 7 · Comparison & interview tip

| Model | Novel obj? | Mesh req? | Synth-only? | Real-time? | Year |
|---|---|---|---|---|---|
| PoseCNN | ❌ | yes | no | ~30 Hz | 2017 |
| DenseFusion | ❌ | yes | no | ~16 Hz | 2019 |
| GDR-Net | ❌ | yes | partial | ~25 Hz | 2021 |
| MegaPose | ✅ | **yes** | ✅ | ~3 Hz | 2022 |
| **FoundationPose** | ✅ | **optional** | ✅ | ~5–10 Hz (Orin, distilled `UNVERIFIED`) | 2024 |

> **🎤 Interview Tip.** "Pose estimator for a never-before-seen object?" — *"FoundationPose in mesh-free mode — onboard with ~16 reference images, then run the pose tracker. With a CAD mesh, use it for extra accuracy points."* "I'd train a PoseCNN on YCB-style data" is three years out of date.

---

## References

- FoundationPose — Wen et al. *CVPR 2024* (best paper). https://arxiv.org/abs/2312.08344
- MegaPose — Labbé et al. *CoRL 2022*. https://arxiv.org/abs/2212.06870
- GDR-Net — Wang et al. *CVPR 2021*. https://arxiv.org/abs/2102.12145
- DenseFusion — Wang et al. *CVPR 2019*. https://arxiv.org/abs/1901.04780
- PoseCNN — Xiang et al. *RSS 2018*. https://arxiv.org/abs/1711.00199
- BOP. https://bop.felk.cvut.cz/

## Boundary

Dissects FoundationPose as a **novel-object 6D pose foundation model**. Mesh-required predecessor → [`megapose_dissection.md`](./megapose_dissection.md). Per-embodiment usage → [`embodiments/manipulation/`](../../embodiments/manipulation/). Action consumption → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./README.md)
