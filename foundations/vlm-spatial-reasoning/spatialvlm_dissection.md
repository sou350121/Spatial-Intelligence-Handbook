# SpatialVLM: Endowing Vision-Language Models with Spatial Reasoning

**Status:** v1 — opinionated draft. QA-pair counts and capability numbers are paper-claimed unless noted; deployment latency marked `UNVERIFIED`.
**Wedge tier:** W2 · `foundations/vlm-spatial-reasoning/` anchor #1
**TL;DR:** SpatialVLM's thesis: a general-purpose VLM already *sees* enough geometry — what it lacks is supervision on how to *talk about* it. The fix is brute force: auto-generate ~2 billion spatial QA pairs from depth + open-set segmentation on web images, fine-tune, let scale work. Largely correct on qualitative relations; decisively not on precise metric distances or occluded scenes — exactly the cases robotics deployment cares about.

---

## 1 · The claim that matters

SpatialVLM (Chen, Xu, Sajjadi, Adam, Whitney, Hsu, Liu, Driess, Tsang — Google DeepMind, CVPR 2024, [arXiv:2401.12168](https://arxiv.org/abs/2401.12168)) is a *data* paper disguised as a model paper. Architecture is a standard VLM (PaLI-X / PaLM-E style backbone). The contribution is the data pipeline.

The argument:

1. VLMs fail at spatial reasoning because their pretraining corpus has almost no spatial-relation supervision. Web captions describe *what* is in an image, not *where in 3D*.
2. We can *synthesize* spatial supervision at scale by running monocular depth + open-set segmentation on web images and computing spatial relations algorithmically.
3. Do this at 2B-pair scale, fine-tune, and qualitative spatial reasoning emerges; some quantitative; the result can serve as a perception layer for robotics.

The paper backs #3 with experiments. The community has been arguing about how much to believe #3 ever since.

---

## 2 · The data pipeline (the actual contribution)

```
web image ──► depth model (ZoeDepth/Metric3D) ──► dense metric depth
           └► open-set seg (SAM + tagger)     ──► masks + labels
                             │
                             ▼
              centroid + bbox + depth per object
                             │
                             ▼
        algorithmic QA template fills:
          "Is {A} closer than {B}?"  "How far is {A} from {B}?"
          "Is {A} above {B}?"        "What is the size of {A}?"
                             │
                             ▼
              ~2B (image, question, answer) triples
                             │
                             ▼
              fine-tune VLM (next-token loss)
```

A few details that matter:

- **Depth source uncertainty is real.** ZoeDepth-class models give metric depth with `UNVERIFIED` ±10–20% scale error in the wild. Synthetic distance answers inherit that error. Metric-distance performance is bounded above by the depth model.
- **Open-set segmentation is the second leak.** Misnamed/mis-segmented objects propagate into wrong QA pairs. The paper accepts this as noise that scale washes out.
- **Templates are finite.** A few dozen templates × combinatorial filling → 2B pairs. The model learns the templates very well — generalizes to template-shaped robotics questions, stumbles on out-of-template phrasings.

---

## 3 · Why scale-of-data is the lever (not architecture)

The strongest result is the comparison against architecturally fancier baselines with less spatial data: SpatialVLM *with the same backbone* significantly outperforms VLMs *with bigger backbones but only web-caption pretraining*. The uncomfortable implication: **most of the spatial-reasoning gap in current VLMs is a supervision gap, not a capacity gap.** The VLM had the features; nobody told it to surface them.

| Lever | Cost | Effect |
|---|---|---|
| Bigger backbone, same data | High | Small `UNVERIFIED` |
| Same backbone, 2B spatial QA | Medium | Large (paper's main result) |
| Explicit depth tokens at inference | Low | Large, but couples to sensor (SpatialBot) |
| 3D-aware backbone (point/voxel) | High | Smaller than data scale-up `UNVERIFIED` |

Given a budget choice between "scale up the VLM" and "scale up the spatial supervision," scale up supervision.

---

## 4 · Where SpatialVLM falls down

Failure modes that decide whether you can put SpatialVLM in front of a robot:

**Precise distance.** "How far in cm?" produces plausible *form* and unreliable *numbers*. The depth-model floor (§2) caps this. For sub-centimeter gripper accuracy, no substitute for a calibrated depth sensor.

**Occluded queries.** Partial occlusion → segmenter mis-fires → wrong depth → wrong QA → fine-tune learns wrong associations. The model still answers confidently. **Confident wrongness is worse than ignorance** — and the model does not admit ignorance.

**Out-of-template phrasing.** Robotics teams ask things templates never covered. Degradation is not flagged.

**No temporal reasoning.** Image-conditioned. Motion questions need a different lane.

**View dependence.** Answers shift when the camera moves — still 2D-conditioned. No view-consistency the way a feature field has (compare [`../semantic-3d/lerf_dissection.md`](../semantic-3d/lerf_dissection.md)).

---

## 5 · Bridge to VLA — the integration question

The temptation: wire SpatialVLM in front of a VLA. SpatialVLM emits a spatial caption ("red cube at front-left, 8 cm from gripper"), the VLA consumes it as prompt, the action head executes. This is the "spatial caption" pattern in [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

The trade-off:

- *Get:* zero architectural change to the action head. Any text-accepting VLA accepts SpatialVLM output.
- *Pay:* the caption is a lossy projection — geometry not in the templates is gone. A dense 3D feature cloud carries far more.

Reading: SpatialVLM is *competitive perception for coarse, qualitative tasks*; a *non-starter for tasks needing dense or precise geometry*. The latter belongs to semantic-3D and feed-forward-3D lanes. See the bridge doc §2 for the head-to-head table.

---

## 6 · Falsifiable prediction

By 2026-12, the dominant pattern in published VLM-for-robotics work will be **SpatialVLM-style implicit pretraining + explicit depth tokens at inference** — not either alone. Pure-VLM plateaus at coarse-relation tasks; pure-depth-token is brittle to sensor failure. Bet against any 2026 manipulation system claiming to solve it with a VLM alone and no metric depth.

---

## References

- SpatialVLM — Chen et al. *CVPR 2024*. [arXiv:2401.12168](https://arxiv.org/abs/2401.12168) · [spatial-vlm.github.io](https://spatial-vlm.github.io/)
- ZoeDepth — Bhat et al. 2023. [arXiv:2302.12288](https://arxiv.org/abs/2302.12288) · Metric3D — Yin et al. *ICCV 2023*. [arXiv:2307.10984](https://arxiv.org/abs/2307.10984)
- SAM — Kirillov et al. *ICCV 2023*. [arXiv:2304.02643](https://arxiv.org/abs/2304.02643)
- SpatialBot — Cai et al. 2024. [arXiv:2406.13642](https://arxiv.org/abs/2406.13642)
- PaLM-E — Driess et al. *ICML 2023*. [arXiv:2303.03378](https://arxiv.org/abs/2303.03378)

## Cross-references

- Alternative lane (explicit 3D semantic lifting) → [`foundations/semantic-3d/`](../semantic-3d/README.md), esp. [`openscene_dissection.md`](../semantic-3d/openscene_dissection.md)
- VLM-lane overview → [`README.md`](./README.md)
- VLA integration → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) (SpatialVLM = "captions" row)
- 3D-aware VLA models consuming spatial captions → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)

## Boundary

This document dissects SpatialVLM specifically. It does **not** cover: paradigm comparison (→ [`README.md`](./README.md)); SpatialBot / SpatialRGPT depth-token lineage (queued v2); benchmark-driven training (→ `benchmarks/reasoning/`); 3D-encoder side of VLA architectures (→ `bridge-to-vla/`, VLA-Handbook); cross-embodiment evaluation (→ `crossing/representation-migration/`, TBD).
