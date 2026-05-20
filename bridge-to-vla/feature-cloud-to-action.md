# 3D Feature Cloud → Action Head

**Status:** DRAFT v0.1 — scaffold only, content pending
**Wedge tier:** W2 (one of 5 launch docs)
**Why this doc exists:** The seam between this handbook and VLA-Handbook. Spatial computes the representation; VLA consumes it as a policy input. The wiring between them is where 3D-VLA / PointVLA / SpatialVLM all diverge — and where most teams' integrations fail.

---

## Thesis

A 3D feature cloud is not a *better RGB image* — it is a fundamentally different action-head input that requires architectural choices RGB-only VLAs sidestep: positional encoding for 3D coords, pooling vs. attention over variable-N points, scale normalization in metric units, and a story for what happens when the cloud is sparse. Teams that bolt 3D onto an RGB VLA without addressing these die at the deployment edge.

---

## Outline

1. **Where the boundary sits**
   - Spatial-Handbook owns: how to compute the 3D feature cloud (3DGS, VGGT, point-decoder heads, semantic 3D)
   - VLA-Handbook owns: how the action head consumes it (diffusion / flow matching / regression policy)
   - This doc lives on the seam
2. **Three integration patterns observed in 2025–2026**
   - 3D-VLA: voxelized scene tokens
   - PointVLA: PointNet++ embedding into policy
   - SpatialVLM: VLM consumes spatial captions, not raw 3D
   - Trade-off table — accuracy / latency / training data appetite
3. **What breaks in deployment**
   - Sparse cloud → policy stuck on training-distribution density
   - Coordinate frame mismatch (camera vs base vs world)
   - Metric scale drift when VGGT-class encoder used without IMU
4. **Eng patterns that work**
   - Pre-policy normalization to a canonical bbox-relative frame
   - Augmentation with synthetic 3DGS render perturbations
   - Late fusion (RGB tokens + 3D feature tokens both go into same transformer)

---

## Cross-references

- VLA-Handbook: action policy design, diffusion / flow matching trade-offs
- This handbook `foundations/feed-forward-3d/` — what the 3D encoder looks like
- This handbook `foundations/semantic-3d/` — how labels lift to 3D for the policy

---

## Starter references

- 3D-VLA / PointVLA / SpatialVLM papers
- Diffusion Policy 3D ablations
- Open X-Embodiment 3D-aware variants
- Physical Intelligence π0 technical report (insofar as it discusses observation encoders)
