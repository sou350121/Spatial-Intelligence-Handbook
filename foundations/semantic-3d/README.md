# Semantic 3D

**Status:** v1 — opinionated draft. Hyperparam / timing claims marked `UNVERIFIED`.
**TL;DR:** A robot doesn't need a prettier point cloud — it needs one that *knows what each point is*. Lifting 2D vision-language features (CLIP, DINO, SAM) into 3D is what turns geometry into something a policy can query with words. Three paradigms; which one ships depends on whether you can afford per-scene training, per-frame compute, or neither.

---

## Why 2D semantic features need to be lifted to 3D

CLIP, SAM and DINO live in pixel space. A robot lives in metric space. Every time a policy needs to answer "is the mug on the left side of the table?" or "go to the kitchen utensil," the stack has to bridge image-plane features to 3D coordinates the controller consumes. The naive answer — run a 2D segmenter every frame and back-project — works on a tabletop with one calibrated camera and breaks the moment the embodiment moves (occlusion, view inconsistency, no cross-frame aggregation). The deeper answer is that semantics are a property of the *scene*, not of *each frame*, so the lift needs to live in 3D where it can accumulate. That accumulation step — fusing 2D features into a 3D structure that survives view changes — is what this lane covers.

Downstream consumers are concrete: language-conditioned manipulation (`pick up the green one`), open-vocab navigation, object-centric world models, and the feature side of any 3D-aware VLA. None work without a semantic 3D representation queryable by text.

## The 3 paradigms

- **Per-pixel projection (closed-loop fusion).** Run a 2D backbone per frame, project features into voxels or points, aggregate across views. OpenScene (CVPR 2023) is the reference. *Get:* no per-scene training, zero-shot open-vocab. *Pay:* memory grows with the scene; fusion logic must handle inconsistent 2D outputs across views.
- **Feature field (NeRF-style distillation).** Distill CLIP (or DINO, SAM) into a neural field jointly with radiance. LERF (ICCV 2023) is canonical. *Get:* multi-scale text queries, view-consistent by construction. *Pay:* 5–30 min training per scene `UNVERIFIED`, hard to update online, geometry inherits NeRF's limits.
- **Scene graph (object-centric symbolic).** Detect objects, assign labels and relations, store as a graph (ConceptGraphs lineage). *Get:* tiny footprint, plays well with classical planners, language queries reduce to graph traversal. *Pay:* hard ceiling at the "object" abstraction.

Read horizontally: projection is what robotics teams *deploy*, feature fields are what research papers *publish*, scene graphs are what task planners *consume*. The interesting integrations combine two.

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `lerf_dissection.md` | Kerr et al. ICCV 2023 — CLIP distilled into a NeRF feature field, multi-scale queries | ⚡ |
| `openscene_dissection.md` | Peng et al. CVPR 2023 — direct CLIP/SAM fusion into 3D voxels, zero-shot open-vocab | ⚡ |

`UNVERIFIED` scene-graph dissection (ConceptGraphs / OVIR-3D) queued for v2.

## Cross-references

- VLM-side reasoning (the *other* way to ground language in geometry) → [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/README.md)
- Underlying geometry the features ride on → [`foundations/feed-forward-3d/`](../feed-forward-3d/), [`foundations/3dgs-family/`](../3dgs-family/)
- Semantic cloud → action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- Cross-representation comparison across embodiments → `crossing/representation-migration/` (TBD)

## Boundary

This directory is per-method dissection of how 2D vision-language features get lifted into 3D. It does **not** cover: VLM models without explicit 3D structure (→ `foundations/vlm-spatial-reasoning/`); the 3D representations themselves (→ `foundations/3dgs-family/`, `feed-forward-3d/`); action-head consumption (→ `bridge-to-vla/`); per-embodiment deployment (→ `embodiments/<emb>/`).
