# Generative 3D as Data Factory · Not as Planner

**Status:** v1 — opinionated lane intro. UNVERIFIED policy applies to all throughput / sim2real-gap numbers downstream.
**Scope tier:** W2 lane. Sibling to `foundations/world-model/`; do not duplicate.

---

Generative 3D and differentiable rendering have two distinct customers in 2025-2026 spatial AI. **One customer is a robot policy at inference time**, asking a world model "what happens if I do this?" — that customer is served by `foundations/world-model/` (Cosmos / Genie / Marble). **The other customer is the training pipeline**, asking "give me one thousand more episodes of this manipulation task with varied lighting and clutter" — that customer is served here. Same underlying tech (3DGS, diffusion video, differentiable renderers), entirely different SLAs, failure modes, and decision criteria.

This region keeps a tight scope: **generative 3D systems used to manufacture training data or to bridge sim2real, not to act as the policy's runtime world model**. Splat-Sim renders ten thousand perturbed grasp demonstrations from one hundred phone-captured viewpoints. Aerial Gym pipes 3DGS scenes into Isaac dynamics so a quadrotor RL policy sees photoreal forests before its first real flight. Mitsuba 3 and nvdiffrast are the differentiable-rendering plumbing that lets gradients flow from pixel loss back to texture maps, mesh vertices, or gaussian parameters — without that plumbing, neither Splat-Sim nor Aerial Gym would be trainable end-to-end.

## Boundary vs `foundations/world-model/`

| Question | `world-model/` answer | `generative-3d-sim/` (here) |
|---|---|---|
| When is it called? | **Inference time** — policy queries it during deployment | **Training time** — pipeline calls it once per episode batch |
| Who consumes the output? | The deployed policy / planner | The supervised learning loss or RL rollout buffer |
| Tolerance for drift | Critical — drift kills the policy live | Tolerable — bad samples get filtered, never reach robot |
| Latency budget | 10–100 ms per step | Hours-to-days per dataset; offline |
| Failure mode | Wrong rollout → wrong action | Wrong rollout → noisier gradient, gated by data filters |
| Example | Genie 2 as MPC planner; Cosmos-Predict at inference | Splat-Sim demo augmentation; Cosmos-Transfer as data step |

**Cosmos appears in both regions on purpose**: Cosmos-Transfer (sim → photoreal RGB for training) lives here in spirit; Cosmos-Predict-as-planner lives in `world-model/`. The shared dissection (`world-model/nvidia_cosmos_dissection.md`) covers both — we cross-link rather than duplicate.

## Recommended entry points

| File | Tier | Use case |
|---|---|---|
| `splat_sim_for_manipulation.md` | W2 🔧 [3DGS] | 3DGS-rendered demo augmentation for diffusion-policy manipulation |
| `aerial_gym_3dgs_sim2real.md` | W2 🔧 🌬️ [3DGS] | 3DGS scenes + Isaac/Gazebo dynamics for drone obstacle avoidance / VIO sim2real |
| `differentiable_rendering_mitsuba_nvdiffrast.md` | W2 📖 | The gradient-flow plumbing under everything else; pick one (Mitsuba vs nvdiffrast) per task |

## What is explicitly out of scope here

- **Genie-style action-conditional video models acting as planners** → `foundations/world-model/genie_dissection.md`
- **Consumer-facing 3D scene generation** (Marble's primary product) → out of handbook scope
- **Per-method 3DGS internals** → `foundations/3dgs-family/3dgs_original_dissection.md`
- **Cross-embodiment "which 3DGS-sim wins"** → `crossing/representation-migration/3dgs_as_simulator_comparison.md`
- **Per-embodiment deployment receipts** → `embodiments/manipulation/` and `embodiments/aerial/`

## The one-sentence test

If you can answer **"this system produces training samples that a SGD update consumes offline"**, it belongs here. If you can answer **"this system runs inside the policy loop at deployment"**, it belongs in `world-model/`. If you can answer neither — it is a generative media demo, and gets the ❌ tag.

---

[← Back to Foundations](../README.md) · [→ World Model (sibling)](../world-model/README.md) · [→ 3DGS Family](../3dgs-family/README.md) · [→ Crossing: 3DGS-as-sim comparison](../../crossing/representation-migration/3dgs_as_simulator_comparison.md)

*Last lane review: 2026-05-21.*
