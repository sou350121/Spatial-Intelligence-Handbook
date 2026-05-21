# 4D Gaussian Splatting — Dynamic Scenes (4D-GS 动态场景解构 — CVPR 2024)

> **Published**: 2023-10 (arXiv) / CVPR 2024
> **Paper**: Wu et al. — *4D Gaussian Splatting for Real-Time Dynamic Scene Rendering*
> **Team**: HUST + Huawei + HKUST
> **Core position**: Adds a time axis to 3DGS via "canonical gaussian set + learned deformation field" (HexPlane MLP), keeping a 4D scene in a memory budget close to a single static 3DGS.

**Status:** v1.1 — backfilled to AGENTS.md 14-item template 2026-05-21. Hyperparams marked UNVERIFIED.
**TL;DR:** 4D-GS adds a time axis to 3DGS, but the right mental model is not "3DGS over time" — it's "one canonical gaussian set plus a learned deformation field." That distinction is what decides whether the representation survives fast manipulation motion or only slow scene changes.

### X-Ray (non-expert friendly)

(a) Static 3DGS reconstructs a snapshot, but every embodied use case (grasping, bimanual handover, cloth, cables) involves motion — naive per-frame 3DGS blows up storage linearly. (b) 4D-GS factorizes the problem: keep *one* canonical gaussian set, learn a small deformation MLP `(x,y,z,t) → Δposition,Δrotation,Δscale`, render by deforming-then-splatting. (c) For spatial AI engineers: dynamic scene reconstruction now fits the same memory budget as static 3DGS — usable for demonstration replay and novel-view data augmentation, but with a hard ceiling at fast / topology-changing motion.

### 📍 Research Landscape Timeline

```
D-NeRF 2021 ─► HyperNeRF 2021 ─► HexPlane 2023 ─► ★ 4D-GS CVPR 2024 ─► Dynamic 3DGS (per-timestep) 2024 ─► hybrid canonical+per-step 2025+
```

4D-GS picks the "canonical + deformation" branch; Dynamic 3DGS (Luiten et al.) picks the per-timestep branch. The two regimes are still not unified.

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

> 📌 **Napkin Formula**: `G(t) = G(0) + Φ_HexPlane(x,y,z,t)` where Φ outputs `(Δxyz, Δrot, Δscale)` per gaussian. Render = standard 3DGS rasterize on `G(t)`. **Only Φ is queried per-time; the canonical set is reused.**

> ⚡ **Eureka Moment**: Factorize 4D into "static canonical + smooth deformation," and the temporal axis costs almost nothing — but this *only* works if the deformation field stays low-frequency. Once motion is high-frequency (thrown object) or topology changes (tearing paper), the MLP cannot keep up and the abstraction breaks. The factorization IS the assumption.

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

## 2.5 · Worked example — 60-frame teleop demo

A 2-second teleop demo (60 frames @ 30 Hz) of a manipulator pouring water from a cup into a bowl.

- **Canonical set**: ~400K gaussians (built from frame 30, the median).
- **HexPlane**: 6 × `(64×64)` planes with shared 64-channel features `UNVERIFIED defaults`; tiny MLP head (~50K params).
- **Naive per-timestep storage**: 60 × 400K = 24M gaussians ≈ 6 GB.
- **4D-GS storage**: 400K canonical + ~10 MB HexPlane = ~0.4 GB → **~15× compression**.
- **Failure spot**: the water stream (topology change) — gaussians from the cup interior can't smoothly deform into a falling column. The MLP averages, producing a soft blur where the stream should be sharp.

Lesson: 4D-GS encodes the manipulator and cup motion well, the *liquid* poorly. That's the canonical-plus-deformation contract.

---

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

### 4.x · Hidden Assumptions

Upstream assumptions whose violation produces the regime-split failures above:

- **Smooth velocity field** — motion is approximated as a continuous deformation; impulsive / discontinuous motion (collisions, drops) breaks the MLP.
- **Topology preservation** — no gaussian creation/destruction during the clip; tearing, pouring, smoke fail.
- **Sufficient training views per timestep** — sparse temporal coverage leaves the deformation field under-constrained and produces floaters.
- **Static background** — only foreground is expected to move; camera-mounted motion conflates background + foreground deformation and degrades both.
- **Short clip duration (~2–5 s) UNVERIFIED** — longer clips push HexPlane capacity; either canonical set drifts or deformation MLP saturates.

If violated, the reconstruction usually still renders cleanly at training timestamps and degrades silently at novel times — the dangerous failure mode for policy training.

---

## 5 · 2-year outlook

By 2027 expect the per-timestep vs canonical-plus-deformation split to collapse into hybrid systems: a slow canonical set for the static background, a fast per-timestep set for moving foreground objects, and explicit foreground/background masks driving the routing. The pure 4D-GS formulation will be remembered as the right factorization for slow scenes; production robotics will use the hybrid.

**Falsifiable prediction:** by 2027-06, at least one published manipulation policy paper will train on 4D-GS-reconstructed demonstrations as the primary visual training data (not bare camera RGB, not simulator). Bet against any claim that 4D-GS is "too slow / too expensive" by then — it will be the standard demo replay tool.

**Interview Tip**: If asked "4D-GS vs Dynamic 3DGS," the trap is to pick one. The right answer: *"they cover disjoint regimes"* — 4D-GS for smooth medium-articulated motion (manipulation, walking), Dynamic 3DGS for fast / topology-changing motion (cloth tearing, fast grasping). A production system will hybridize, not pick.

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
