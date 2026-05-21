# nuScenes, Waymo Open, Argoverse 2 — Why "SOTA on nuScenes" Travels Badly

**Status:** v1 — opinionated draft. Annotation cost and dataset-size numbers marked `UNVERIFIED`.
**TL;DR:** These three are not three replicas of the same benchmark. They differ in **sensor rig geometry, label semantics, and split policy** — and those differences are exactly why a method that wins on nuScenes often loses on Waymo. If you're reading an AD paper, read the rig diagram before the leaderboard.

---

## 1 · The "AD benchmark" is three benchmarks

For roughly five years the literature treated nuScenes as the default. Then Waymo Open shipped a much harder rig + larger label budget, then Argoverse 2 shipped a multi-city long-tail rig. By 2024 every serious paper reported on at least two; by 2026 reporting only nuScenes is read as a tell that the method doesn't generalize.

The interesting question for this handbook is **why** the numbers diverge — and the answer is mostly the sensor rig and label semantics, not the algorithm.

---

## 2 · The rig diff that does most of the work

| | **nuScenes** (Boston + Singapore) | **Waymo Open** (Phoenix + SF + Mountain View) | **Argoverse 2** (6 US cities) |
|---|---|---|---|
| Cameras | 6 × 1600×900 (1 front, 1 front-left/right, 1 back, 1 back-left/right) | 5 × 1920×1280 (front + 4 side) | 7 × 2048×1550 ring + 2 stereo |
| LiDAR | 1 × 32-beam roof Velodyne | 1 × 64-beam top + 4 × short-range side | 2 × 32-beam roof |
| LiDAR points / frame | ~35k | ~177k | ~110k |
| Camera FOV coverage | 360° sparse | 252° dense (no rear) | 360° dense |
| Sample rate (keyframes) | 2 Hz | 10 Hz | 10 Hz |
| Geographic diversity | 2 cities | 3 cities (mostly sunny) | 6 cities incl. rain / snow |
| Sequence length | ~20 s | ~20 s | ~15 s |
| Total annotated frames | ~40k keyframes `UNVERIFIED` | ~230k `UNVERIFIED` | ~150k `UNVERIFIED` |

The **single most consequential difference**: Waymo has ~5× more LiDAR points per frame and Argoverse 2 has the 7-camera ring. A camera-only BEV detector tuned on nuScenes' 6-camera + sparse LiDAR layout *cannot* directly reproduce its numbers on Waymo (different FOV overlap, different range) or Argoverse 2 (different image aspect ratio + extra camera).

---

## 3 · Label semantics — where leaderboards quietly drift

Bounding box semantics differ in ways that don't show up in the headline mAP:

- **nuScenes** uses 10 detection classes + 8 attribute states (e.g. `pedestrian.moving`). Velocity is in the label.
- **Waymo Open** uses 4 detection classes (vehicle / pedestrian / cyclist / sign) but higher-quality 3D boxes + LET-3D-AP metric that penalizes longitudinal error less.
- **Argoverse 2** uses 30 long-tail classes including construction equipment, strollers, articulated buses. Long-tail mAP dominates.

This is why "SOTA on nuScenes" travels badly:

1. A method optimized for 10-class detection in 2 Hz keyframes overfits to **temporally sparse inference** — Waymo's 10 Hz exposes flicker.
2. The 30-class Argoverse 2 long tail rewards a different inductive bias (open-set / few-shot capacity), which nuScenes-tuned heads don't carry.
3. The LET-3D-AP metric on Waymo forgives longitudinal error — a method that lives or dies on longitudinal precision will look better on Waymo than on nuScenes.

---

## 4 · The occupancy benchmark fracture

The 2023–2024 shift to **occupancy prediction** as the primary AD perception task made these dataset differences sharper.

| Occupancy benchmark | Built on | Label source | Grid resolution |
|---|---|---|---|
| **Occ3D-nuScenes** | nuScenes | LiDAR-accumulated + manual cleanup | 0.4 m voxels, 200×200×16 |
| **Occ3D-Waymo** | Waymo Open | LiDAR-accumulated, no manual fix | 0.4 m, larger range |
| **OpenOccupancy** | nuScenes | Same accumulation, denser labels `UNVERIFIED` | 0.2 m option |
| **CVPR 2023 challenge split** | nuScenes | Org-curated subset | matches Occ3D-nuScenes |

The point: **occupancy splits are dataset-specific dialects, not a portable benchmark**. A paper that says "65% mIoU on Occ3D" needs to specify which dataset's Occ3D. Cross-occupancy transfer is an open problem (Cosmos / SimGen and ScalableSimulator are betting that *synthetic* data closes this gap; results pending `UNVERIFIED`).

---

## 5 · Why nuScenes still wins as the *first* benchmark

Despite the above, nuScenes is the right *first* benchmark for most teams because:

- 40k keyframes fits on a workstation; Waymo's 230k frames + larger LiDAR per frame routinely needs cluster-scale storage.
- 6-camera ring matches the *cheap* AD rig configuration that most production vehicles ship (Tesla-class).
- The leaderboard culture is mature; baselines are reproducible.

The trap is *stopping* at nuScenes. The 2026 norm is: prototype on nuScenes, validate generalization on Waymo, stress-test long tail on Argoverse 2.

---

## 6 · What "transfer fails" actually looks like

Three patterns recur:

1. **Range cliff.** nuScenes-tuned BEV detectors degrade beyond ~50 m where the sparse 32-beam LiDAR they were trained on stopped providing supervision. Waymo's 64-beam roof + 4 short-range LiDARs reveal the gap.
2. **Class imbalance flip.** Argoverse 2's articulated buses and construction equipment are rare in nuScenes labels; nuScenes-tuned heads default to "vehicle" and eat the false negatives.
3. **Weather rig dependence.** Argoverse 2 includes rain / snow; nuScenes Singapore is mostly clear. Camera-heavy methods regress more than LiDAR-heavy methods under bad weather.

If a paper reports cross-dataset numbers and the gap is >15% mAP, the rig diff probably explains more than the algorithm.

---

## 7 · Sensor rig as the hidden hyperparameter

The takeaway is simple but consequential: **the AD benchmark you pick selects for an entire rig assumption**. Method comparisons that don't normalize for rig are not method comparisons — they're rig comparisons in disguise.

For practitioners:

- If you care about *camera-only* methods (Tesla-class deployment), nuScenes + Argoverse 2 ring camera is the right pair.
- If you care about *LiDAR-heavy* methods (Waymo-class deployment), Waymo Open is the canonical bar; nuScenes is secondary.
- If you care about *long-tail safety*, Argoverse 2's 30-class label set is the only one that engages the question.

There is no single "AD benchmark." Pick the rig that matches the deployment target, then defend cross-dataset numbers on the others.

---

## Boundary

This doc compares the three perception benchmarks at the dataset / rig level. Per-method dissection (BEVFormer, BEVFusion, OccFormer, SparseOcc) belongs in `foundations/` once those wedges land. End-to-end driving simulators (CARLA, nuPlan, Waymo-Sim) are scored on different axes and live elsewhere. Sensor-physics for the LiDARs and cameras themselves: `foundations/sensor-physics/`.

## References

- nuScenes — Caesar et al. *CVPR 2020*. https://arxiv.org/abs/1903.11027
- Waymo Open Dataset — Sun et al. *CVPR 2020*. https://arxiv.org/abs/1912.04838
- Argoverse 2 — Wilson et al. *NeurIPS 2021 (Datasets track)*. https://arxiv.org/abs/2301.00493
- Occ3D — Tian et al. *NeurIPS 2023*. https://arxiv.org/abs/2304.14365
- OpenOccupancy — Wang et al. *ICCV 2023*. https://arxiv.org/abs/2303.03991
- LET-3D-AP — Hung et al. (Waymo metric). https://waymo.com/open/challenges/
