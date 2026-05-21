# RAFT (光流的迭代细化)

> **发布时间**: 2020-08 (ECCV 2020 *best paper* — Teed & Deng, Princeton)
> **论文 / 模型**: RAFT — Recurrent All-Pairs Field Transforms (arXiv 2003.12039)
> **核心定位**: The architecture that displaced FlowNet / PWC-Net and ruled the optical-flow leaderboard for ~5 years. Iterative refinement on a 4D correlation volume.

**Status:** v1 — opinionated draft. Numbers `UNVERIFIED` unless rig-tested.
**Wedge tier:** W1 · canonical *dense* pixel-motion primitive.
**TL;DR:** RAFT replaced single-shot CNN flow with "build a correlation volume once, refine iteratively with a GRU". ~10× fewer params than FlowNet2, large gains on Sintel / KITTI, the template every successful flow model since (GMA, FlowFormer, SEA-RAFT) builds on.

**X-Ray.** Pre-RAFT, optical flow was a tower of encoder-decoder nets regressing flow in one pass. RAFT *separated visual matching (corr volume) from flow estimation (small GRU)* and iterated. 5 years of leaderboard dominance and the template for DROID-SLAM, VGGT's tracking head, and most matching pipelines. For robotics: the primitive quietly powering DROID-SLAM and many flow-conditioned policies.

---

## 📍 研究全景时间线

```
2015        2017       2018       2020 (HERE)        2022          2024
FlowNet ──► FlowNet2 ─► PWC-Net ─► RAFT ───────────► GMA / FF ───► SEA-RAFT
└── single-shot CNN regression ───┘  └── iterative refinement + correlation volume ───┘
```

The inflection from encoder-decoder regression to iterative-refinement-on-correlation-volume. Every modern flow model is a RAFT descendant.

---

## 1 · Architecture overview

### 1.1 System component comparison

| Module | Input | Output | Freq |
|---|---|---|---|
| Feature encoder | 2 frames | `g_1`, `g_2` (H/8 × W/8 × D) | Per pair |
| Context encoder | frame 1 | GRU context | Once |
| 4D corr volume | `g_1, g_2` | `C(x,y,u,v)` | Per pair |
| Lookup | `C` + flow | local patch | Per iter |
| GRU updater | lookup + ctx + flow | residual `Δf` | `K=12/32` |

### 1.2 ⚡ Eureka Moment

> **Build the correlation volume once; iterate the flow refinement on cheap local lookups. Geometric matching = expensive setup; refinement = cheap loop.**

Single-shot CNN regression makes the network learn everything — matching, smoothing, occlusion — at once. RAFT does matching as a closed-form correlation volume and learns *only* refinement. The move that delivered the 2020 accuracy jump.

### 1.3 Information flow

```
   F1,F2 ─► feat enc ─► g_1, g_2 ─► 4D corr ─► C(x,y,u,v)
   F1 ─► ctx enc ──► h_ctx                 │
                                           ▼
   f_0=0 ─► [GRU loop ×K: lookup→GRU→f+=Δf] ─► f_K ─► upsample
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  f_{t+1}  =  f_t  +  GRU( lookup(C, f_t),  context )
```

Flow at `t+1` = flow at `t` + learned correction from correlation values *around the current flow guess*. `C` built once; GRU iterates cheaply on local lookups.

| Symbol | Meaning |
|---|---|
| `f_t` | flow field at iter `t` |
| `C(x,y,u,v)` | similarity of features at `(x,y)` vs `(x+u, y+v)` |
| `lookup` | bilinear sample of `C` around current flow |
| `K` | iters (12 train, 32 eval) |

**Intuition.** `C` is a similarity map. The GRU zooms in around the current flow guess and decides which way to nudge. Iteration count grows *mildly* with displacement — unlike exponentially in classical pyramids.

---

## 3 · Worked example: KITTI 2-frame clip

1242×375 frames, car at 60 km/h.

1. **Encode features.** 2 maps at 1/8 res. ~5 ms `UNVERIFIED`.
2. **Build corr volume.** ~150×47 × 150×47 ≈ 5e7 entries via one matmul. ~10 ms `UNVERIFIED`.
3. **Initialize.** `f_0 = 0`.
4. **Iterate** `t = 0..11`: lookup 7×7 corr patch around current flow, GRU produces `Δf` (<1 px after a few iters). ~1.5 ms × 12 ≈ 18 ms `UNVERIFIED`.
5. **Upsample.** Convex 1/8 → full res. ~3 ms.

Total ~40 ms / pair desktop `UNVERIFIED`. KITTI EPE ~1.5 px `UNVERIFIED`. FlowNet2 single-shot costs more and loses accuracy.

---

## 4 · Engineering view: the corr-volume RAM wall

| Input res | Corr volume `UNVERIFIED` | GPU mem `UNVERIFIED` | RT Orin? |
|---|---|---|---|
| 320×240 | ~1.4e6 | ~50 MB | ✅ ~30 Hz |
| 1024×768 | ~1.5e8 | ~600 MB | marginal |
| 4K | ~1e10 | doesn't fit | ❌ |

The 4D volume is the **single biggest engineering constraint** — `O(H²W²)`. Fine for VGA, blows up at 4K. SEA-RAFT and others address with multi-scale / sparse correlation.

**Deployment.** Photometric loss in self-supervised depth / VIO. Gripper-relative flow as policy state. DROID-SLAM's per-pixel correspondence reuses RAFT's correlation volume (Teed's own follow-up).

---

## 5 · Data & eval

FlyingChairs → FlyingThings3D → Sintel / KITTI fine-tune. Sintel-clean test EPE ~1.6, KITTI-2015 Fl-all ~5% `UNVERIFIED`. Top-or-near on these for years until 2023-era attention variants (FlowFormer, GMA-RAFT) marginally surpassed it.

---

## 6 · Capabilities & failure modes

**Capabilities.** Dense per-pixel flow with strong generalization. Large-displacement-capable via iteration. Small (~5M vs FlowNet2 ~160M) — easy to embed.

**Failure modes.** Sun-flare / saturation breaks brightness constancy. Thin structures (wires, railings) get background flow. Featureless regions → no corr peak; GRU hallucinates smooth field. Night / weather domain shift without fine-tune.

### 6.1 Hidden Assumptions

- **Small displacement.** Displacements >~20% of image width struggle to converge. Aerial / fast motion violates.
- **Brightness constancy.** Auto-exposure / shadow-crossing shifts the corr peak.
- **Static-camera-OR-static-scene.** Doesn't separate ego from scene motion — downstream must.
- **No occlusion.** Occluded regions get a flow value but it's extrapolation; need an occlusion mask (unofficial output `UNVERIFIED`).
- **Photometric consistency.** Specular / transparent surfaces violate dot-product matching.

When these break, *the flow still looks fine* but is wrong — silent failure.

---

## 7 · Comparison & interview tip

| Model | Year | Params `UNVERIFIED` | Style | Sintel EPE `UNVERIFIED` |
|---|---|---|---|---|
| FlowNet2 | 2017 | ~160M | single-shot | ~3.0 |
| PWC-Net | 2018 | ~9M | pyramid | ~2.6 |
| **RAFT** | 2020 | **~5M** | **iter on 4D corr** | **~1.6** |
| GMA | 2021 | ~6M | iter + attention | ~1.4 |
| FlowFormer | 2022 | ~16M | transformer iter | ~1.2 |
| SEA-RAFT | 2024 | ~10M | iter + efficient | ≈ RAFT |

> **🎤 Interview Tip.** "Why is RAFT still canonical 5 years later?" — *"Two ideas: 4D corr volume gives the geometric oracle once; iterative GRU on local lookups is parameter-efficient and large-displacement-capable. Every successful follow-up is a RAFT variant — tunes the refiner or compresses the volume, but the architecture is RAFT's."* "FlowNet-style" misses the iterative-refinement revolution.

---

## References

- RAFT — *ECCV 2020* (best paper). https://arxiv.org/abs/2003.12039
- DROID-SLAM — *NeurIPS 2021*. https://arxiv.org/abs/2108.10869
- PWC-Net — *CVPR 2018*. https://arxiv.org/abs/1709.02371
- FlowNet2 — *CVPR 2017*. https://arxiv.org/abs/1612.01925
- GMA — *ICCV 2021*. https://arxiv.org/abs/2104.02409
- FlowFormer — *ECCV 2022*. https://arxiv.org/abs/2203.16194

## Boundary

The **dense optical-flow foundation primitive**. Sparse / long-horizon point tracking → [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md). Corr volumes in SLAM → [`../classical-slam/`](../classical-slam/). Flow as policy input → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./README.md)
