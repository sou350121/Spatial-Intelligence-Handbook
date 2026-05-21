# VLM Spatial Reasoning

**Status:** v1 — opinionated draft. Capability claims marked `UNVERIFIED` where not personally measured.
**TL;DR:** A general-purpose VLM (GPT-4V, Claude, Gemini, Qwen-VL) is *flat by default* — it can name objects but cannot reliably say which is closer, how far, or where the gripper should move. Making a VLM reason about 3D is a training problem, not a prompting problem. Three approaches compete: implicit pretraining on synthetic spatial QA (SpatialVLM), explicit caption / depth tokens (SpatialBot lineage), and 3D-aware benchmark training. Each bets on a different bottleneck.

---

## VLMs are flat — they don't reason about 3D unless trained to

The default behavior of every off-the-shelf VLM in 2025 is to treat an image as a 2D semantic scene. They will tell you "there is a mug and a keyboard" with high accuracy and fail — or confidently hallucinate — when asked "is the mug closer than the keyboard?" or "how many centimeters above the table is the mug handle?" The reason is structural: training data is image-caption pairs from the web, and web captions are object-naming captions, not spatial-relation captions. The model has the features to *answer* spatial questions; it has never been *taught* to surface them.

This matters for robotics because a VLM is the cheapest possible interface between a language goal and a perception system. If a VLM could answer "where should the gripper go?" reliably, you could skip half of the semantic-3D pipeline (see [`foundations/semantic-3d/`](../semantic-3d/README.md)). The papers in this lane all answer one question: **how do we make a VLM produce 3D-grounded answers, given that no architectural trick alone is enough?**

## The 3 approaches

- **Implicit pretraining (SpatialVLM, Google DeepMind 2024).** Auto-generate a massive synthetic dataset of spatial QA pairs by running depth estimation and open-set segmentation on web images, then fine-tune. *Bet:* scale of spatial supervision is the lever; the model already sees geometry, it just needs to be taught to talk about it. *Pay:* precise metric answers shaky, occlusion reasoning weak.
- **Explicit caption / depth tokens (SpatialBot lineage, 2024).** Augment the input with depth images or textual scene summaries (`object A at 0.4 m, B at 0.7 m`). *Bet:* the VLM is bad at *extracting* geometry from RGB but good at *consuming* it when handed in. *Pay:* couples the model to a sensor at inference.
- **3D-aware benchmark training.** Train end-to-end on a target benchmark (SpatialBench, EmbodiedQA, VSR), often with a 3D-aware backbone. *Bet:* the benchmark captures the right capability and transfer follows. *Pay:* the benchmark frequently does not capture what robotics needs.

Read horizontally: SpatialVLM is the *data* bet, SpatialBot the *input* bet, benchmark training the *task* bet. The strongest 2026+ systems combine implicit pretraining with explicit depth tokens.

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `spatialvlm_dissection.md` | Chen et al. CVPR 2024 — 2B-pair auto-generated spatial QA, the scale-of-data argument | ⚡ |

`UNVERIFIED` SpatialBot, SpatialRGPT, and benchmark-driven (SpatialBench / VSR) dissections queued for v2.

## Cross-references

- The *other* way to ground language in geometry (semantic 3D lifting) → [`foundations/semantic-3d/`](../semantic-3d/README.md)
- Spatial-reasoning benchmarks → [`benchmarks/reasoning/`](../../benchmarks/reasoning/) (TBD)
- VLM spatial outputs → policy action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) (the SpatialVLM caption integration is the contrarian row)
- Cross-embodiment comparison ("VLM as perception" vs "VLM + explicit 3D") → `crossing/representation-migration/` (TBD)

## Boundary

This directory is per-method dissection of VLMs that reason about space. It does **not** cover: explicit 3D semantic lifting (→ `foundations/semantic-3d/`); general VLM architectures without a spatial angle (out of scope); 3D-aware VLA action heads (→ [VLA-Handbook](https://github.com/sou350121/VLA-Handbook), `bridge-to-vla/`); per-embodiment deployment (→ `embodiments/<emb>/`).
