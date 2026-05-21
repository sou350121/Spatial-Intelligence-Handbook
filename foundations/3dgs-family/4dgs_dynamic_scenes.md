# 4D Gaussian Splatting — Dynamic Scenes

**Status:** v1 — opinionated draft. Hyperparams marked UNVERIFIED.
**TL;DR:** 4D-GS adds a time axis to 3DGS, but the right mental model is not "3DGS over time" — it's "one canonical gaussian set plus a learned deformation field." That distinction is what decides whether the representation survives fast manipulation motion or only slow scene changes.

Reference paper: Wu et al. "4D Gaussian Splatting for Real-Time Dynamic Scene Rendering." *CVPR 2024.* arXiv: https://arxiv.org/abs/2310.08528

---

## 1 · Why time is the bottleneck nobody admits

Vanilla 3DGS reconstructs a static scene. For robotics that is half a representation. Grasping is dynamic. Bimanual handover is dynamic. Anything involving a deformable object (cloth, cable, food) is dynamic. The honest question is not "can we extend 3DGS to video" but "what temporal embedding strategy actually survives the motion velocities a robot encounters?"

Two strategies emerged through 2023–2024 and they are not interchangeable:

| Strategy | Mechanism | What it's good at | What it breaks on |
|---|---|---|---|
| **Per-timestep gaussians** (Dynamic 3DGS lineage) | Train one gaussian set per frame; constrain neighbors via local rigidity loss | Fast motion, topology changes (cloth tearing, object splitting) | Storage explodes linearly with T; no temporal interpolation |
| **Canonical + deformation field** (4D-GS, Wu et al.) | One canonical gaussian set; an MLP / HexPlane predicts per-gaussian Δ(position, rotation, scale) at time t | Smooth motion, slow deformation, novel-view + novel-time queries | Fast motion / topology change degrades the deformation MLP |

4D-GS is the second school. The canonical-plus-deformation factorization is what makes the representation fit in memory and what makes it interpolate cleanly to in-between timestamps. It is also what makes it fail on fast or discontinuous motion.

## 2 · Mechanism

```
   Canonical gaussian set G(0)
   (anisotropic, same as 3DGS)
              │
              │     time t
              ▼
   ┌─────────────────────────┐
   │ Deformation field Φ:    │
   │   HexPlane / MLP        │     queried at every gaussian position
   │   (x, y, z, t) → Δ      │
   │   Δ = (Δxyz, Δrot, ΔS)  │
   └─────────────────────────┘
              │
              ▼
   Deformed gaussians G(t) = G(0) + Φ(G(0), t)
              │
              ▼
   Standard 3DGS rasterizer → image at time t
              │
              ▼
   Loss: photometric vs GT frame at time t
```

The interesting design choices:

- **HexPlane decomposition** (4D-GS) factorizes the 4D field into six 2D planes (xy, xz, yz, xt, yt, zt). This is what keeps the deformation MLP tractable; a naive 4D MLP would not scale.
- **Canonical frame selection** matters more than papers admit. Pick t=0 and the deformation field tries to encode everything that happens after; pick the median frame and the field stays small in both directions.
- **Densification under deformation** — the splitter has to decide whether under-covered regions are missing canonical gaussians or missing deformation capacity. Most implementations punt and only densify the canonical set.

## 3 · Where the regime split lives (slow vs fast motion)

This is the part you have to internalize before deploying:

| Motion regime | Example | 4D-GS behavior |
|---|---|---|
| Slow, smooth | breathing person, cloth draping, slow conveyor | ✅ Works. Deformation field stays smooth, novel-time interpolation is clean. |
| Medium, articulated | walking person, opening cabinet | ⚠️ Mostly works. Hinges and joints are where the field gets noisy; expect floaters. |
| Fast, rigid | thrown object, fast grasping | ❌ The deformation MLP struggles to encode high-frequency temporal change. Per-timestep gaussian variants win here. |
| Topology change | tearing paper, pouring liquid | ❌ Canonical-plus-deformation cannot represent gaussians appearing or disappearing. Hard wall. |

The rule of thumb: if the motion can be described as a smooth velocity field over the canonical scene, 4D-GS is the right tool. Once the scene topology changes, you need a different representation.

## 4 · Why this matters for robot manipulation (the lane that pays this handbook's bills)

Manipulation lives almost entirely in the medium-articulated regime. Object dynamics during grasping (an object rotating in the gripper, a cable swinging during transport) are exactly what 4D-GS was built for. The concrete use cases that benefit:

- **Demonstration replay with novel viewpoints** — record a teleop demo with 2–3 cameras, reconstruct as 4D-GS, generate synthetic views from arbitrary angles for policy data augmentation.
- **Predictive scene rollout** — use the deformation field as a learned world-model prior; condition a policy on "what does the scene look like at t+1s if I take action a?"
- **Sim-to-real visual gap closing** — 4D-GS reconstructions of real demonstrations close the visual gap that bare physics simulators leave open.

The failure mode to flag: fast pick-and-place motions (>1 m/s end-effector velocity) sit at the edge of the deformation field's competence. Reported reconstruction PSNR on standard dynamic benchmarks `UNVERIFIED — Wu et al. report ~30+ dB on D-NeRF synthetic, lower on real captures` does not directly translate to "the policy will train on this without distribution shift."

## 5 · 2-year outlook

By 2027 expect the per-timestep vs canonical-plus-deformation split to collapse into hybrid systems: a slow canonical set for the static background, a fast per-timestep set for moving foreground objects, and explicit foreground/background masks driving the routing. The pure 4D-GS formulation will be remembered as the right factorization for slow scenes; production robotics will use the hybrid.

**Falsifiable prediction:** by 2027-06, at least one published manipulation policy paper will train on 4D-GS-reconstructed demonstrations as the primary visual training data (not bare camera RGB, not simulator). Bet against any claim that 4D-GS is "too slow / too expensive" by then — it will be the standard demo replay tool.

## References

- **4D-GS** — Wu et al. *CVPR 2024.* https://arxiv.org/abs/2310.08528
- **Dynamic 3D Gaussians** (per-timestep lineage) — Luiten et al. *3DV 2024.* https://arxiv.org/abs/2308.09713
- **HexPlane** (the decomposition 4D-GS uses) — Cao & Johnson. *CVPR 2023.* https://arxiv.org/abs/2301.09632
- **D-NeRF** (the dynamic radiance field predecessor) — Pumarola et al. *CVPR 2021.* https://arxiv.org/abs/2011.13961

## Boundary

This doc covers the temporal extension of 3DGS. It does **not** cover:

- The static 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- SLAM-coupled gaussians → `foundations/3dgs-family/gs_slam_dissection.md`
- How dynamic reconstructions feed into VLA training data → `bridge-to-vla/feature-cloud-to-action.md`
- Cross-representation comparison (4D-GS vs feed-forward 3D over time) → `crossing/representation-migration/`
- Feed-forward 3D models that handle multi-frame natively → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
