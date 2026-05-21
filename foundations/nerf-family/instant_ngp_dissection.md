# Instant-NGP 解构 (Instant Neural Graphics Primitives with a Multiresolution Hash Encoding)

> **Publication:** SIGGRAPH 2022
> **Paper:** Müller, Evans, Schied, Keller. NVIDIA. arXiv: https://arxiv.org/abs/2201.05989 · Code: https://github.com/NVlabs/instant-ngp
> **Core position:** The engineering paper that turned NeRF training from "two days on a V100" into "five minutes on an RTX 3090" — and proved the bottleneck was the input encoding, not the MLP.

**Status:** v1 — opinionated. Numbers from paper unless `UNVERIFIED`.
**TL;DR:** Replace fixed Fourier positional encoding with a *learnable* multi-resolution hash grid; let a tiny 2-layer MLP do the rest. Hash collisions you'd think would ruin quality don't — the MLP handles them gracefully, and the speedup is 1000× wall-clock with no measurable quality loss on standard benchmarks. This is the moment NeRF stopped being a research artifact and started showing up in commercial pipelines (NVIDIA Omniverse, Luma AI, Polycam).

**X-Ray.** Vanilla NeRF spent 99% of training time evaluating an 8-layer MLP 192 times per pixel. Instant-NGP asks: what if the MLP only learns *interpolation between nearby features*, and the features themselves live in a hash-indexed grid? You get an explicit data structure (fast to query, cheap to update) + a 2-layer MLP for local smoothing. For spatial-intelligence engineers, this is the canonical "right *data structure* beats deeper *network*" lesson — which 3DGS later generalized.

## 📍 Research panorama timeline

```
2020         2021              2022 (Jan)              2022 (Aug)        2023
NeRF (ECCV) ► Plenoxels    ► Instant-NGP (SIGGRAPH) ► NerfAcc          ► 3DGS displaces
              (kill MLP,    YOU ARE HERE             (occupancy accel)  for robotics
              dense voxel)  hash grid + tiny MLP
              └─ "kill MLP" wing ─┘  └─ "keep tiny MLP, fix encoding" wing ─┘
```

Two simultaneous attacks on NeRF speed in 2021–22. Instant-NGP won influence because the hash grid generalizes beyond NeRF (same primitive powers SDF, neural radiance caching, gigapixel image fitting).

---

## 1 · Core architecture

### 1.1 System overview

| Component | Input | Output | Detail |
|---|---|---|---|
| Multi-resolution hash grid | xyz | 16 levels × 2 = 32-d feat | Hashed at fine levels |
| Tiny MLP | 32-d + view dir | RGB + σ | 2-layer, 64 wide `UNVERIFIED` |
| Occupancy grid | xyz | skip-empty bool | Cached, refreshed |
| Volume renderer | (σ, RGB) | Pixel | Same as NeRF |

Total params ~12M (mostly hash entries) vs ~1M NeRF. Counterintuitive but explains speed: params are cheap to *index*, expensive to *forward through*.

### 1.2 ⚡ Eureka moment

> **Hash collisions are not bugs — they're a feature. The MLP learns to disambiguate colliding features, so a tiny hash table per level works; trust the network to clean up.**

At coarse levels, the grid fits in the table (no collisions). At fine levels, table < grid → collisions inevitable. Rendering loss naturally allocates fine capacity to *important* spatial locations (where rays terminate) and ignores collisions in empty space. **The hash function does not need optimization; xor-based spatial hashing is fine.**

### 1.3 Flow diagram

```
   xyz query
       │
       ▼
   For L=16 resolutions:
     hash 8 corners → table → trilerp 2-d feature
       │
       ▼
   Concat L=16 → 32-d
       │
       ▼
   2-layer MLP (64 wide) → σ + 16-d feat
       │
       ▼
   View dir (SH-encoded) → concat → 1-layer MLP → RGB
```

Pipeline is one fused CUDA kernel. ~10k lines of hand-written CUDA. Also Instant-NGP's curse — see §6.

---

## 2 · Math core: multi-resolution hashing

### 📌 Napkin Formula

```
For each level L:
    grid_res_L = floor(N_min · b^L)               # b ≈ 1.4 growth
    if grid_res_L^3 ≤ table_size: direct lookup   # dense, no collisions
    else:                          hash mod T     # collisions OK

feature = concat_L trilerp(table[indices_L])
```

Spatial hash: `hash(x,y,z) = (x·π₁) XOR (y·π₂) XOR (z·π₃)`, primes `{1, 2654435761, 805459861}`. Cheap, decorrelated enough.

### 2.1 Parameter budget

| Knob | Default | Rationale |
|---|---|---|
| L (levels) | 16 | Coarse → fine |
| T (table / level) | 2¹⁹ = 524k | Memory/quality knob |
| F (feat dim) | 2 | MLP combines |
| N_min, N_max | 16, 2048 | Resolution range |

Table memory: `L × T × F × 4 ≈ 67 MB`. MLP <1 MB.

### 2.2 Why collisions work

Finest level: 2048³ ≈ 8.6B cells, table 524k → >16,000× compression. But only cells *along surfaces* (σ ≠ 0) need distinct features — typically ~0.01% of volume, well under table capacity. **Empty cells collide harmlessly because their gradients are zero.** Same statistical argument that makes Bloom filters work.

---

## 3 · Worked example: graceful collision degradation

Two points on different surfaces — A = (0.1, 0.1, 0.1), B = (0.7, 0.3, 0.9) — hash to the same fine-level slot 42.

- Ray through A: target "red" → updates `table[42]` toward red.
- Later ray through B: target "blue" → pushes `table[42]` toward blue.
- `table[42]` oscillates → **noise** at fine level.
- Coarse levels do *not* collide for A vs B (enough cells), supplying most of the signal. MLP downweights fine levels automatically.

Result: slight loss of high-freq detail at one point, not catastrophic. Paper's Figure 4: imperceptible at standard hash sizes.

---

## 4 · Engineering view: where 1000× comes from

| Source | NeRF | Instant-NGP | Factor |
|---|---|---|---|
| MLP depth | 8 layers | 2 layers | ~4× |
| MLP width | 256 | 64 | ~4× |
| Per-sample cost | 192 × big MLP | 192 × tiny MLP + 16 lookups | ~10× |
| Empty-space skip | — | Occupancy grid | ~5× |
| CUDA fusion | PyTorch | Hand-written | ~5–10× |
| **Net** | | | **~1000×** |

- Lego: **~5s** to PSNR=30; **5 min** to final.
- NeRF: **~1 day** to PSNR=30.
- Render: **~10 FPS** at 1920×1080 on RTX 3090 `UNVERIFIED`.

**Catch:** lives inside NVIDIA CUDA. Single-GPU, NVIDIA-only, hard to extend, locked to tinycudann. Downstream re-impls (Nerfstudio) less optimized, losing 3–5× wall-clock.

---

## 5 · Data and evaluation

- **NeRF synthetic / LLFF:** same datasets, same protocol. Quality parity at 1/1000th training time.
- **Beyond NeRF:** paper demos SDF, gigapixel images, neural radiance caching. **Hash grid is not NeRF-specific.**
- **Does NOT benchmark:** unbounded scenes (Mip-NeRF 360's problem), view-dependent specular accuracy. Inherits vanilla-NeRF limits except speed.

---

## 6 · Capabilities and failure modes

### 6.1 Hidden assumptions

- **Hash collision tolerance** — assumes high-freq content is *sparse on surfaces*. Violated by volumetric phenomena (smoke, fog) where σ ≠ 0 everywhere; quality degrades when every cell is in the working set.
- **Sufficient GPU memory** — 67 MB table is modest, but occupancy grid + activations push working set to ~2 GB. **Won't fit on Jetson Nano.** Jetson Orin (8 GB shared) is the practical floor.
- **CUDA monoculture** — speed depends on tinycudann fused kernels. Apple Silicon / AMD ROCm / edge: no first-class support. Porting is research-grade.
- **Per-scene training still required** — *fast*, not *unnecessary*. Cross-scene transfer cliff stayed until VGGT-class feed-forward.
- **Static scene** — inherits from NeRF.

### 6.2 What kills deployment

For robotics: 10 FPS at 1080p is fine for *visualization*, not closed-loop perception (need 30+ FPS). 1–2 GB GPU memory at inference awkward for embedded. Hash table opaque — cannot inspect "where is the chair" without decoding entire scene. No editing primitive — modifying a region requires retraining. These are exactly what 3DGS later solved by being *explicit*. Instant-NGP is fast NeRF; 3DGS is *different* NeRF.

---

## 7 · Comparison and interview tip

| Method | Where work goes | Lego training | Render |
|---|---|---|---|
| NeRF (2020) | Deep MLP | ~1 day | <1 FPS |
| Plenoxels (2021) | Dense voxels, no MLP | ~10 min | ~15 FPS |
| TensoRF (2022) | Low-rank tensor | ~30 min | ~5 FPS |
| **Instant-NGP** | Hash grid + tiny MLP | **~5 min** | **~10 FPS** |
| 3DGS (2023) | Explicit gaussians | ~30 min | **~100 FPS** |

> **🎤 Interview tip.** "What did Instant-NGP actually contribute?" — Right answer: *"It moved capacity from the network into a learnable spatial data structure (hash grid), proving NeRF's bottleneck was input encoding, not MLP depth. 1000× speedup made NeRF practically reproducible — and 'explicit data structure beats deeper net' is the lesson 3DGS later took to its logical conclusion."* Wrong: "It made the MLP smaller." Symptom, not cause.

---

## References

- **Instant-NGP** — Müller et al. *SIGGRAPH 2022.* https://arxiv.org/abs/2201.05989
- **Code** — https://github.com/NVlabs/instant-ngp
- **Plenoxels** — Yu et al. *CVPR 2022.* https://arxiv.org/abs/2112.05131
- **TensoRF** — Chen et al. *ECCV 2022.* https://arxiv.org/abs/2203.09517
- **tinycudann** — https://github.com/NVlabs/tiny-cuda-nn

## Boundary

Dissects Instant-NGP only. Does **not** cover unbounded-scene handling (→ `mip_nerf_360_dissection.md`), city-scale (→ `block_nerf_large_scenes.md`), 3DGS (→ `foundations/3dgs-family/3dgs_original_dissection.md`), hash-grid SDF / image demos, or competing "no MLP" lineage.

---

[← Back to NeRF Family README](./README.md)
