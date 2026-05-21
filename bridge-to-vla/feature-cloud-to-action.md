# 3D Feature Cloud → Action Head (3D 特征云 → 动作头：跨 handbook 接口)

> **发布时间**：2026-05-21 · **范围**：Spatial-Handbook 与 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 的接口
> **核心定位**：a 3D feature cloud is not a better RGB image — it forces interface choices RGB-only VLAs sidestep, and 3 of those choices kill silent deployments

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Integration numbers `UNVERIFIED`. **Wedge tier:** W2 · Bridge to VLA-Handbook.

**X-Ray.** (a) Spatial computes the 3D encoder; VLA consumes it for action — most failures live in the seam. (b) Three interface patterns dominate 2025–2026: voxel tokens (3D-VLA), pooled embedding (PointVLA), captions (SpatialVLM). (c) For integration engineers, the 3 silent failure modes are **density-drop, frame-mismatch, metric-scale drift** — fix them at the seam, not in encoder or policy.

### 📍 研究全景时间线 (3D-aware policy evolution)

```
2022 ─── 2023 ─── 2024 ────────── 2025 ──────── 2026 ── ?
 RT-1   CLIPort  3D-VLA (voxel)   VGGT-enc      ←── here
 (2D)   (2D sem) SpatialVLM (cap) + diffusion
                 PointVLA* (pool)  policy        * pattern; exact paper UNVERIFIED
```

Each step adds geometric awareness; **each step also exposed a new interface bug** (token budget → frame drift → metric-scale drift).

---

## 1 · Where the boundary sits (Architecture)

Spatial owns the **encoder side** (3DGS, VGGT-class feed-forward, point-decoder heads, semantic lifting). VLA owns the **action side** (diffusion / flow-matching / autoregressive heads consuming that representation). This is the bug-on-the-edge doc: neither handbook alone answers "why does my 3D-aware policy work in sim and collapse on hardware?" The answer is almost always in the interface.

### ⚡ Eureka Moment

**The encoder and action head must trade a *contract*** — frame normalization, density conditioning, and metric-scale flag are NOT optional. They are the interface; either side silently breaks them and the system silently fails.

---

## 2 · The contract, as one line (Math Core)

### 📌 Napkin Formula

```
policy(obs) = ActionHead( normalize_frame( scale_aware( density_conditional( cloud_encoder(views) ) ) ) )
```

The nested calls **are** the contract — skip a layer and the next layer breaks. Inside-out: Spatial supplies `cloud_encoder` (cloud tensor), `density_conditional` (`density_ratio ∈ [0,1]`), `scale_aware` (`metric_scale_flag`). VLA supplies `normalize_frame` (bbox-relative `T_canonical`) and `ActionHead`, which **must refuse** if flags mismatch training, not silently coerce.

---

## 3 · Three integration patterns observed in 2025–2026

**3D-VLA (UMass + MIT, ICML 2024).** Voxelize the scene (`UNVERIFIED` typical 32³ at ~5 cm), emit per-voxel feature tokens, concatenate into LLM context alongside RGB tokens. *Get:* clean — voxel tokens look like vision tokens. *Pay:* sub-grid geometry discarded; token count scales with grid³.

**PointVLA (`UNVERIFIED` paper name; pattern verified).** Encode the raw cloud with PointNet++ or similar permutation-invariant backbone. Pool to a fixed-size embedding, inject into the policy head as a side-channel feature. *Get:* O(N) in points; handles variable density. *Pay:* embedding is opaque to LLM attention — lose the ability to *point* at geometry.

**SpatialVLM (Google DeepMind 2024).** Contrarian: don't feed 3D to the policy. Train a VLM that emits **spatial captions** ("red block 12 cm left of gripper, 4 cm above table") and feed as text. *Get:* zero changes to action head. *Pay:* captioning latency, hard fidelity ceiling.

### Trade-off table

| Pattern | Fidelity | Latency | Data | Efficiency |
|---|---|---|---|---|
| 3D-VLA (voxel tokens) | High | High `UNVERIFIED` ~2× RGB-VLA | Large (paired RGB+3D) | Medium |
| PointVLA (PointNet++) | Medium | Low | Medium | High |
| SpatialVLM (captions) | Low | Medium | Large (VLM pretrain) | Low |

Voxel: geometry bottleneck, GPU plentiful. PointNet++: data-poor. Captions: VLM-strong team, coarse task.

### Hidden Assumptions (where each pattern silently breaks)

- **3D-VLA** assumes voxel grid resolution is task-relevant. Sub-voxel geometry (fingertips, threads, folds) is invisible regardless of token spend.
- **PointVLA-style pooled embedding** assumes runtime density ≈ training density. Pooling washes out the difference; policy has **no way** to know it's seeing 30 % density unless density is a side-channel feature (§5.1).
- **SpatialVLM** assumes captioning resolution suffices. Once the task needs finer-than-vocabulary orientation ("rotate 7° about wrist"), the ceiling is hit and no data fixes it.

---

## 4 · Worked example — density-drop in the wild

Diffusion policy trained on tabletop pick-place; depth sensor consistently gives ~30 % voxel occupancy.

```
Train:   density_ratio = 0.30  (all demos)
Deploy:  glossy red mug + side-lit → 0.08  (73 % drop)

Naive PointVLA-style (no density side-channel):
  Pool over 8 % of expected points → embedding magnitude collapses
  → policy outputs mean trajectory ("safe" prior)
  → reach 4 cm short of mug; gripper closes on air

Correct: refuse (density ∉ [0.20, 0.40]) OR density-conditioned
  policy trained on 0.05–0.95 → corrected reach.
3-rig eval lift: ~38 % vs ~91 % success  `UNVERIFIED`
```

Silent because nothing crashes. Catch with a regression test that **logs density at inference and asserts it lies in the training distribution.**

---

## 5 · What breaks in deployment — the 3 silent failure modes

Ordered by how often they kill an integration.

**5.1 · Sparse cloud → density-conditioned collapse.** Sparse pointcloud is fine in sim. In real, depth or VGGT-class encoders drop to ~30 % of training density once lighting changes, object is glossy, or angle is bad. Policy fails silently — wrong object, 2 cm grasp miss, mean-trajectory hallucination. Fix: density-conditioned augmentation (subsample 20–80 % in training, inject density ratio as a feature). **Not more data.**

**5.2 · Coordinate frame mismatch — the silent killer.** Encoder emits in camera frame; demos in TCP/base frame; sim in world frame. A 4×4 off by 90° or a gripper-offset translation, and the policy learns the offset as a *bias*. Works on training rig; fails on a second rig with camera 3 cm different. Fix: **explicit frame normalization** at the seam — every cloud into canonical (bbox-relative, §6.1) frame, params logged.

**5.3 · Metric scale drift — the VGGT-class trap.** Monocular feed-forward 3D (VGGT, DUSt3R) is **un-metric** — geometry correct at arbitrary scale. Plug in front of a policy trained on stereo/RGB-D and you get the most common bug in this stack: right *direction*, wrong *distance*. Fix: **scale-conditional decoder** — fuse a known reference (gripper width, IMU stereo baseline, calibration object), or emit a scale token. "Network will figure it out" is not a plan.

---

## 6 · Engineering patterns that work

**6.1 · Pre-policy normalization to canonical bbox-relative frame.** Best general default. Detect a task-relevant bounding box (object, workspace, base); transform every cloud into it before the policy. Policy learns relative geometry. `UNVERIFIED` ~2–3× sample efficiency.

**6.2 · Augmentation with 3DGS render perturbations.** Most effective when sim2real is the bottleneck. Train a 3DGS reconstruction; render viewpoint/lighting/density perturbations during policy training. Beats 10× more demos `UNVERIFIED`.

**6.3 · Late fusion: RGB + 3D tokens in same transformer.** Best when data is plentiful. Cross-attention picks which modality matters per-frame. 3D-VLA is canonical. Highest ceiling, most expensive.

---

## 7 · The cross-handbook contract

| Side | Provides | At the boundary |
|---|---|---|
| **Spatial** | Cloud (points + features), camera-to-world transform, density estimate, metric-scale flag | Schema documented; canonical = camera-frame unless tagged |
| **VLA** | Action head consuming schema; frame normalization; density/scale conditioning | Logs transform; **refuses** on metric-scale flag mismatch |
| **Both** | Round-trip integration tests on a shared embodiment (manipulation tabletop default) | Cited from both handbooks' boundary sections |

Break the contract silently → integration fails silently. That is why this doc exists.

### Interview Tip

Asked *"how do I plug a 3D encoder into my diffusion policy"*? — answer: **normalize to bbox-relative frame, condition on density, flag metric-scale.** The 3 things academic papers never tell you.

---

## 8 · For the reader

- **Manipulation engineer** — start with PointNet++ + bbox-relative normalization. Upgrade to late fusion only after the data ceiling.
- **VLA researcher** — §5 failures are interface bugs, not encoder bugs. Your action head must declare (frame, scale, density) and **refuse** mismatched input.
- **Spatial researcher** — emit the §7 metadata. Costs nothing; saves the integrator a week.

---

## Cross-references & References

- [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) (action policy design) · `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` (why VGGT is un-metric) · `foundations/semantic-3d/` · `crossing/representation-migration/`
- 3D-VLA — Zhen et al. *ICML 2024* · SpatialVLM — Chen et al. *CVPR 2024* (https://spatial-vlm.github.io) · PointVLA — `UNVERIFIED` exact paper, pattern verified · Diffusion Policy 3D — Ze et al. *RSS 2024* · π0 — Physical Intelligence 2024

## Boundary

This doc lives on the seam. Does **not** dissect any single encoder (see `foundations/feed-forward-3d/`) or action head (see VLA-Handbook). *Last opinion update: 2026-05-21.*

---
[← Back to bridge-to-vla README](./README.md)
