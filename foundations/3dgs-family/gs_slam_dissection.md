# GS-SLAM — Gaussian Splatting Inside the SLAM Loop (GS-SLAM 在线 SLAM 解构 — CVPR 2024)

> **Published**: 2023-11 (arXiv) / CVPR 2024
> **Paper**: Yan et al. — *GS-SLAM: Dense Visual SLAM with 3D Gaussian Splatting*
> **Team**: Tsinghua + Zhejiang Lab
> **Core position**: First system to run 3DGS *online* from a moving RGB-D camera — tracking by render-and-compare against the current gaussian map, mapping by depth-driven gaussian spawning. Loop closure remains unsolved.

**Status:** v1.1 — backfilled to AGENTS.md 14-item template 2026-05-21. Hyperparams marked UNVERIFIED.
**TL;DR:** GS-SLAM finally got 3DGS to run *online* from a moving camera, which is what closes the gap from "post-hoc reconstruction" to "live spatial map." The unsolved problem is loop closure — gaussians don't refactor cleanly when you discover the camera was wrong about its pose 30 seconds ago, and that's why classical SLAM still wins for long-horizon mapping.

### X-Ray (non-expert friendly)

(a) Vanilla 3DGS is offline: capture images, run COLMAP, optimize ~30 minutes. SLAM needs the opposite — every new frame should refine the map incrementally. (b) GS-SLAM separates *tracking* (pose only, fast, render-and-compare) from *mapping* (gaussian update, slow, keyframe-bounded), the classical ORB-SLAM split with gaussians as the map back-end. (c) For spatial AI engineers: GS-SLAM is the first time you get a *renderable, dense, online* map — good for short indoor demos, but not yet a replacement for ORB-SLAM3 on long-horizon trajectories with loops.

### 📍 Research Landscape Timeline

```
ORB-SLAM3 2020 ─► NICE-SLAM (NeRF) 2022 ─► Co-SLAM 2023 ─► ★ GS-SLAM CVPR 2024 ─► SplaTAM 2024 ─► MonoGS 2024 ─► loop-closed GS-SLAM 2026+ (open)
```

GS-SLAM is the first 3DGS-native SLAM system; SplaTAM/MonoGS extend the lineage but loop closure on gaussian maps is still open.

Reference paper: Yan et al. "GS-SLAM: Dense Visual SLAM with 3D Gaussian Splatting." *CVPR 2024.* arXiv: https://arxiv.org/abs/2311.11700

---

## 1 · Why this fusion is the right next step

3DGS as published is an offline tool: collect images, run COLMAP, then optimize gaussians for ~30 minutes. SLAM demands incremental updates — every new frame should refine the map without retraining. The naive fusion ("just run 3DGS frame-by-frame") doesn't work; gaussian optimization is too slow and the representation has no notion of incremental insertion. **GS-SLAM is the first system to make the online loop tractable**, by separating tracking and mapping the way ORB-SLAM did but with gaussians as the map primitive.

Overclaim to resist: "3DGS replaces classical SLAM." It does not. GS-SLAM is best read as "ORB-SLAM with a photoreal map back-end" — front-end tracking stays recognizably classical, gaussians are the back-end deliverable.

> ⚡ **Eureka Moment**: The differentiable rasterizer is the *tracker* — render an expected RGB-D from the current gaussian map at predicted pose, photometric loss vs observed frame, backprop into pose. The same rasterizer that does mapping does tracking. **No separate feature pipeline, no PnP, no descriptor matching** — pose estimation collapses into a 10-iter gradient descent on the rendering loss.

## 2 · Architecture

> 📌 **Napkin Formula**: `pose ← argmin_T ‖Render(GaussianMap, T) − observed_RGBD‖²` (front-end). Then `GaussianMap ← argmin_G ‖Render(G, T_keyframes) − observed_keyframes‖²` (back-end). Both use the same differentiable rasterizer — the only difference is which variable is optimized.


```
   RGB-D frame at time t
              │
              ▼
   ┌─────────────────────────┐
   │ Front-end tracking      │
   │  · render expected RGB-D │
   │    from current gaussian │
   │    map at predicted pose │
   │  · compute photometric + │
   │    geometric residual    │
   │  · optimize pose only    │
   │    (~10 iters, fast)     │
   └─────────────────────────┘
              │
              ▼  pose T(t)
   ┌─────────────────────────┐
   │ Keyframe decision       │
   │   yes → insert keyframe │
   │   no  → continue        │
   └─────────────────────────┘
              │  (if keyframe)
              ▼
   ┌─────────────────────────┐
   │ Map expansion           │
   │  · spawn new gaussians  │
   │    in unobserved regions │
   │    (driven by depth)    │
   │  · gaussian opt over    │
   │    recent keyframes      │
   │    (~50–100 iters)      │
   └─────────────────────────┘
              │
              ▼
   Updated gaussian map
```

Key engineering tricks: **render-and-compare tracking** (pose estimation reuses the differentiable rasterizer — render expected image from the current map at predicted pose, photometric loss vs actual frame, backprop into pose); **depth-driven spawning** (new gaussians seeded from RGB-D or learned monocular depth in unobserved regions, removing COLMAP-style global SfM init); **keyframe-bounded optimization** (gaussian updates over a sliding window of recent keyframes, not the entire map — bounds per-frame compute).

## 2.5 · Worked example — 30-second indoor walk

Walk a handheld RealSense D435i through a 4 m × 4 m office, 30 s @ 30 Hz → 900 frames.

- **Frame 1**: spawn ~3K gaussians, pose = identity.
- **Frame 300** (10 s): ~200K gaussians; tracking ~80 ms; render ~30 ms.
- **Frame 900** (30 s): ~500K gaussians, ~600 MB GPU; rate drops to 3 Hz on RTX 3090 UNVERIFIED.
- **Loop closure**: return to start, ATE ~5 cm; rigid SE(3) correction on 500K covariances → ~1 dB PSNR hit, no clean re-converge.

Aggressive pruning is essential past ~30 s of capture.

---

## 3 · The loop closure problem (unsolved)

Classical SLAM treats loop closure as graph optimization: detect revisit, run global pose-graph optimization, every landmark gets the same SE(3) correction.

**Gaussians do not refactor cleanly under this.** Applying rigid pose correction to a point landmark is trivial; applying it to a gaussian rotates the covariance + SH coefficients into the wrong frame `UNVERIFIED severity`. Worse, gaussians from before and after the closure may overlap in the corrected map with no clean merge/prune algorithm, and re-optimization (densification + opacity) has no convergence guarantee.

GS-SLAM and successors (SplaTAM, MonoGS) mostly *avoid* loop closure rather than solving it — they target short-trajectory indoor scenes where drift is bounded. Honest claim: "good map quality on short loops, no real answer for long-trajectory closures."

## 4 · Real-time on Jetson Orin (the deployment question)

Reported runtime on a desktop RTX 3090 `UNVERIFIED`: ~5–8 Hz tracking, mapping in the background at lower rate. On a Jetson Orin (32 GB) the same code path drops to ~1–3 Hz `UNVERIFIED — needs rig validation`. The drop comes from LPDDR5 memory bandwidth (rasterization is memory-bound, not compute-bound, so FLOPS ratios mislead), no tensor-core shortcut (the rasterizer is hand-written CUDA), and map growth (~500k gaussians per 30s indoor capture `UNVERIFIED`, with rendering cost scaling in active gaussians per tile).

Practical implication: GS-SLAM on Jetson is fine for a short demo (one room) but not for a multi-room long-horizon task without aggressive gaussian pruning.

### 4.x · Hidden Assumptions

Upstream assumptions whose violation produces the deployment failures above:

- **RGB-D input (depth available)** — depth-driven spawning needs real depth; monocular variants (MonoGS) replace this with learned depth but inherit its scale errors.
- **Bounded trajectory length / no loops** — loop closure on gaussians is unsolved; long trajectories drift silently.
- **Static scene** — moving people / objects produce floating gaussians the optimizer cannot prune cleanly.
- **Photometric stability** — exposure / lighting changes break the rendering loss; tracking diverges.
- **Sufficient texture** — textureless corridors degrade photometric tracking; classical+IMU recovers better.
- **GPU on platform** — render-and-compare needs CUDA; CPU-only not viable.

If violated, tracking either *diverges loudly* (good, recoverable) or *drifts silently* (bad, accumulates). No drift-aware confidence flag in vanilla GS-SLAM.

---

## 5 · Where this beats classical SLAM (and where it doesn't)

| Scenario | GS-SLAM | Classical (ORB-SLAM3, RTAB-Map) |
|---|---|---|
| Indoor RGB-D, short trajectory, photoreal map needed | ✅ Wins clearly — output is renderable, classical produces sparse point cloud | — |
| Indoor RGB-D, long trajectory with loops | ⚠️ Loop closure unsolved | ✅ Wins — pose-graph optimization is mature |
| Outdoor, daylight, large scale | ❌ Memory blows up | ✅ Sparse maps handle this |
| Texture-poor scenes (warehouse aisles) | ⚠️ Photometric tracking degrades | ⚠️ ORB features also degrade — call it a tie |
| Low-light / high dynamic range | ❌ Rendering loss is brittle | ⚠️ Feature matching also struggles |
| Map quality for downstream VLA policy input | ✅ Wins — gaussians are a richer prior than sparse points | ❌ Sparse points need separate dense reconstruction |

The honest summary: GS-SLAM wins when you need a *renderable, dense* map and you can bound the trajectory length. Classical SLAM wins on long horizons, large scales, and adverse conditions.

## 6 · 2-year outlook

Unsolved problems, ordered by impact:

1. **Loop closure on gaussian maps** — needs a principled merge/prune that respects the rendering loss. Biggest opening in the lineage.
2. **Feed-forward initialization** — replace RGB-D spawning with a VGGT-class model emitting gaussian-ready point clouds from monocular input.
3. **In-loop map compression** — online pruning that doesn't damage renderability is open.

**Falsifiable prediction:** by 2027-12 there will be at least one published GS-SLAM variant that handles loops of >100m with closure accuracy comparable to ORB-SLAM3. If no such system appears, the lineage will have plateaued as "indoor demo tool only."

**Interview Tip**: When asked "does GS-SLAM replace ORB-SLAM3," the trap answer is yes. The right answer: *"not yet — loop closure on gaussian maps is open."* Pitch it as "ORB-SLAM with a photoreal back-end" for short indoor demos; keep classical for long-horizon mapping until merge/prune under SE(3) correction has a principled algorithm.

## References

- **GS-SLAM** — Yan et al. *CVPR 2024.* https://arxiv.org/abs/2311.11700
- **SplaTAM** (concurrent work, similar fusion) — Keetha et al. *CVPR 2024.* https://arxiv.org/abs/2312.02126
- **ORB-SLAM3** (the classical baseline) — Campos et al. *T-RO 2021.* https://arxiv.org/abs/2007.11898
- **MonoGS** (monocular variant, removes RGB-D requirement) — Matsuki et al. *CVPR 2024.* [arXiv link TBD]

## Boundary

This doc covers gaussian splatting fused with online SLAM. It does **not** cover:

- Static 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- Dynamic 4D extensions → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- Aliasing across scales → `foundations/3dgs-family/mip_splatting.md`
- Classical VIO/SLAM for aerial → `crossing/slam-vio-migration/vggt_vs_drone_vio.md`
- Cross-representation comparison → `crossing/representation-migration/`
- VLA policy consumption of gaussian maps → `bridge-to-vla/feature-cloud-to-action.md`
- Feed-forward 3D as alternative front-end → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
