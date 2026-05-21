# 3D-Aware VLA — How 3D-VLA, PointVLA, and SpatialVLM Differ

**Status:** v1 — opinionated draft. Internal Google / DeepMind training-data scale numbers marked `UNVERIFIED`.
**Wedge tier:** W1 · **Handbook flagship bridge doc**
**TL;DR:** Three different answers to "how should a VLA see 3D." 3D-VLA fuses an explicit 3D world model into the policy. PointVLA bolts a point-cloud branch onto an existing VLA cheaply. SpatialVLM teaches a VLM to *reason* about 3D from 2D images plus massive synthetic Q&A — a different bet entirely. None dominates; each wins a different niche, and the data cost ranges from "modest" to "Google-scale."

---

## 1 · Why "3D-aware VLA" is three different questions

"We made our VLA 3D-aware" could mean any of: (1) **inject 3D representation** (point cloud, feature volume, 3DGS scene) into the policy; (2) **add 3D reasoning** to the VLM backbone (the model answers "how far is the cup from the edge?"); (3) **replace the action head** with one that outputs 3D-aware trajectories (SE(3) waypoints, contact frames). Different groups solve these in different orders; resulting architectures look very different. This doc disentangles via 3D-VLA, PointVLA, and SpatialVLM as exemplars of three distinct integration patterns.

---

## 2 · The three patterns — comparison

| | **3D-VLA** | **PointVLA** | **SpatialVLM** |
|---|---|---|---|
| Answers | Inject explicit 3D state into policy | Cheaply add point-cloud awareness | Teach VLM to reason in 3D from 2D |
| 3D input | Diffusion-decoded world state | Raw point cloud branch + RGB | None — 3D internalized |
| Pretraining data | Robot + 3D scene paired | Standard VLA + clouds | Internet image + synthetic Q&A `UNVERIFIED` |
| Inference cost | High (diffusion in loop) | Modest (point encoder) | Same as base VLM |
| Best at | Long-horizon w/ spatial goals | Manipulation where geometry > language | Spatial-reasoning queries |
| Breaks | Slow; world-model errors propagate | Point-cloud quality dependent | Doesn't "know" 3D; OOD fails |
| Origin | UMass+MIT+Shanghai AI Lab 2024 | NUS+Bytedance 2024 `UNVERIFIED` | Google DeepMind 2024 |

Spectrum: explicit 3D (3D-VLA / world model / high data + compute) ← PointVLA (cloud branch / modest cost) → implicit 3D (SpatialVLM / image-only reasoning / internet-scale data).

---

## 3 · 3D-VLA — explicit world model as conditioning

3D-VLA (Zhen et al., ICML 2024) adds a *generative 3D world model* on top of a 3D-LLM-style backbone. Flow: observation → 3D scene representation (point cloud / feature volume) → language goal + scene → diffusion-decoded *future* 3D state → future-conditioned action decoder produces the trajectory. Architectural bet: **planning is easier in a 3D representation than in tokenized text**.

Data cost: paired (trajectory ↔ 3D scene ↔ language goal) data, scaled via Holodeck + Objaverse + RLBench-style synthesis `UNVERIFIED`. Modest by Google standards, prohibitive for a small lab. Wins on long-horizon tasks with geometrically describable goals. Stumbles on real-time control (diffusion world model adds latency) and OOD scenes (world model hallucinates).

---

## 4 · PointVLA — the cheap bolt-on

PointVLA's bet is the opposite: don't redesign the backbone, just **bolt a point-cloud branch onto an existing VLA and let the policy figure out fusion**. Existing VLA (OpenVLA-class) keeps its RGB + language path; a lightweight point encoder (PointNet++ or sparse 3D conv) tokenizes the depth / cloud; point tokens are concatenated into the VLA stream before the action head.

Data cost: minimal extra — train the new branch + fine-tune fusion on a single lab's manipulation dataset scale. Wins on tasks where geometry solves what RGB can't (transparent objects, low light, occluded depth-from-context). Stumbles when the depth sensor is bad — the branch becomes a regularizer, not a feature. This is the **pragmatic** approach most non-Google-scale VLA teams will reach for first.

---

## 5 · SpatialVLM — the data-scale bet

SpatialVLM (Chen et al., CVPR 2024) is the most ambitious: instead of changing the architecture, **teach a 2D VLM to reason about 3D by training it on huge volumes of synthetic spatial Q&A**. Pipeline: mine ~2B images `UNVERIFIED`, run depth + segmentation + 3D lifting per image, auto-generate Q&A ("how far is X from Y?", "is X taller than Y?"), train a VLM on the corpus.

Result: a model that answers spatial questions about 2D images with rough quantitative accuracy — no 3D input at inference. The catch: it doesn't really "see" 3D, it's learned cues that correlate with the answer. Clean indoor works; novel sensors / OOD lighting degrade. Only Google-scale labs can afford this `UNVERIFIED`. Useful as a *reasoning oracle* upstream of a policy, not as a controller.

---

## 6 · How to pick

| Constraint | Pick |
|---|---|
| Lab-scale data, manipulation, depth sensor available | **PointVLA** |
| Long-horizon planning, can afford latency, language goals | **3D-VLA** |
| Need a spatial-reasoning oracle, no 3D sensors | **SpatialVLM** |
| Drone / fast-loop | none direct; Spatial output → classical controller |
| Marine / acoustic-first | none; visual-only breaks |

---

## 7 · The two-end contract with Spatial

Spatial supplies: 3D representations from `foundations/`, sensor-physics reliability annotations, cross-embodiment scale/latency budgets. VLA-Handbook supplies: policy backbones, action heads, training recipes, real-robot success rates.

The **contract**: Spatial side guarantees coordinate frame (camera vs world), metric-scale flag, point-cloud / feature-cloud schema (see `feature-cloud-to-action.md`). VLA side guarantees action space, coordinate convention match, perception latency budget. 3D-VLA needs temporally coherent spatial output; PointVLA needs per-frame clouds; SpatialVLM needs only RGB — the VLA-side choice dictates what Spatial delivers.

---

## 8 · 2-year outlook + falsifiable prediction

The three patterns aren't converging — they're *specializing*. By 2027: PointVLA-style becomes the academic-lab default; 3D-VLA-style is where Figure / 1X / Apptronik bet for humanoid long-horizon; SpatialVLM-style becomes a *component* (spatial-QA tool) inside larger agent systems, not a deployment endpoint.

**Falsifiable prediction:** before 2027-06 a published VLA ships as primary policy on a real humanoid using explicit 3D world-model conditioning (3D-VLA lineage), from Figure / 1X / Tesla Optimus / Boston Dynamics. Bet against any claim that pure SpatialVLM-style 2D-only reasoning suffices for fine-manipulation humanoid control.

---

## Boundary

This doc surveys integration patterns at the *interface* level. The action-head and policy-training side belongs in [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) under policy architectures. The engineering of feeding spatial features into the policy lives in [`bridge-to-vla/feature-cloud-to-action.md`](./feature-cloud-to-action.md). Per-method paper dissection (3D-VLA paper deep dive, SpatialVLM paper deep dive) belongs in `foundations/semantic-3d/` once those wedges land.

## References

- 3D-VLA — Zhen et al. *ICML 2024*. https://arxiv.org/abs/2403.09631
- PointVLA — Li et al. 2024. https://arxiv.org/abs/2409.14411 `UNVERIFIED canonical link`
- SpatialVLM — Chen et al. *CVPR 2024*. https://arxiv.org/abs/2401.12168
- 3D-LLM (architecture lineage for 3D-VLA) — Hong et al. *NeurIPS 2023*. https://arxiv.org/abs/2307.12981
- OpenVLA (baseline VLA for PointVLA-style additions) — Kim et al. 2024. https://arxiv.org/abs/2406.09246
- Holodeck (scene synthesis used in 3D-VLA-style training) — Yang et al. *CVPR 2024*. https://arxiv.org/abs/2312.09067
