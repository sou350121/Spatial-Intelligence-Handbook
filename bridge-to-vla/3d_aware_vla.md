# 3D-Aware VLA — How 3D-VLA, PointVLA, and SpatialVLM Differ (3D 感知 VLA — 三种整合模式对比)

> **发布时间**：2024（三个代表作均为 ICML / CVPR 2024）
> **论文 / 模型**：3D-VLA (UMass+MIT+SAIL) · PointVLA (NUS+Bytedance) · SpatialVLM (Google DeepMind)
> **核心定位**：把"VLA 看到 3D"拆成三种正交策略——explicit world model / point-cloud bolt-on / language-internalized——决定整合形态的是 data scale 与 latency budget，不是单点架构。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Internal Google / DeepMind training-data scale numbers marked `UNVERIFIED`.
**Wedge tier:** W1 · **Handbook flagship bridge doc**
**TL;DR:** Three different answers to "how should a VLA see 3D." 3D-VLA fuses an explicit 3D world model into the policy. PointVLA bolts a point-cloud branch onto an existing VLA cheaply. SpatialVLM teaches a VLM to *reason* about 3D from 2D images plus massive synthetic Q&A — a different bet entirely. None dominates; each wins a different niche, and the data cost ranges from "modest" to "Google-scale."

### X-Ray (non-expert friendly)

(a) "How does a VLA see 3D?" looks singular but is three questions: input format (cloud? world model?), where 3D enters the policy stack, and where it comes from (sensor / imagined / language-implicit). (b) 2024 yielded three orthogonal answers — explicit world model (3D-VLA), point-cloud bolt-on (PointVLA), language-internalized priors (SpatialVLM) — each winning a different niche, none dominating. (c) For spatial / VLA engineers: the *Spatial→VLA contract* differs by an order of magnitude across patterns; picking the pattern dictates the entire Spatial stack downstream.

### Research Landscape Timeline

```
2D-VLA (RT-2 2023) ─► OpenVLA 2024 ─┬─► PointVLA 2024 (cloud bolt-on)
                                    ├─► 3D-VLA ICML 2024 (world-model fusion)
                                    └─► SpatialVLM CVPR 2024 (data-scale 2D)
```

Three lineages forked off OpenVLA-class base in 2024; by 2026 none has eaten the others. The bifurcation is the story.

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

> 📌 **Napkin Formula**：`action = π(language, perception_3D)` — the three patterns differ in what `perception_3D` is. 3D-VLA: `perception_3D = WorldModel(obs)` (generated future scene). PointVLA: `perception_3D = PointEncoder(depth)` (sensed cloud). SpatialVLM: `perception_3D = ∅`, but `π` has internalized 3D priors from 2B Q&A pretraining. **The architectural choice is really a choice of data pipeline**.

> ⚡ **Eureka Moment**: "3D-aware" is not one design axis — it is *where in the policy stack 3D enters*. 3D-VLA inserts it at the **state** layer (world model conditioning), PointVLA at the **observation** layer (cloud token concat), SpatialVLM at the **prior** layer (pretraining bakes 3D in). These are not three implementations of one idea; they are three different commitments about *where data scale is most useful*. Once you see this, picking is just asking "where is my data scale?"

## 2.5 · Worked Example — same task, three pipelines

Task: "place the red mug behind the blue book". Tabletop, RGB + depth available.

- **3D-VLA**: depth → cloud → diffusion-decoded *future* cloud (mug behind book) → SE(3) waypoints. Latency 200–500 ms `UNVERIFIED`. Wins on geometric goals ("behind" = 3D).
- **PointVLA**: RGB + language → OpenVLA tokens; depth → PointNet++ → ~256 cloud tokens; concat → action. +~10 ms over OpenVLA `UNVERIFIED`. Cloud branch *sees* depth ordering directly.
- **SpatialVLM**: RGB only → VLM with 2B-Q&A 3D priors → action. No depth sensor. Breaks on OOD monocular-depth cues (transparent vase).

Same scene, three pipelines: depth sensor matters in two, world model in one, data scale in one. **No architecture replaces another — they pick different bottlenecks to invest in.**

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

### 8.x · Hidden Assumptions (per pattern)

- **3D-VLA**: world-model generative error < policy planning error; else WM becomes hallucination source. Diffusion latency tolerable — breaks fast closed-loop.
- **PointVLA**: depth sensor reliable enough that cloud branch adds info, not noise. Cheap depth can degrade fusion below RGB-only.
- **SpatialVLM**: 2B-image distribution covers test scenes; OOD lighting / sensor silently breaks monocular-depth priors with no 3D fallback.
- **All three**: VLA backbone robust to Spatial↔policy coordinate-frame mismatch — in practice the camera-frame vs world-frame bug is the #1 integration failure.

Lab works, new robot fails → check the violated assumption first, not "the model is bad."

### 8.y · Interview Tip

Asked "which 3D-VLA pattern?" — refuse the abstract answer. **Reply with: what's your data scale and latency budget?** Lab-scale + fast loop → PointVLA. Long-horizon + latency-tolerant → 3D-VLA. Google-scale + no 3D sensor → SpatialVLM. Trap: picking by benchmark accuracy instead of integration cost. **These are infrastructure decisions, not benchmark choices.**

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
