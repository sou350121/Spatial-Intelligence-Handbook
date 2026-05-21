# Instant-NGP 解构 (Instant Neural Graphics Primitives with a Multiresolution Hash Encoding)

> **Publication:** SIGGRAPH 2022
> **Paper:** Müller, Evans, Schied, Keller. NVIDIA. arXiv: https://arxiv.org/abs/2201.05989 · Code: https://github.com/NVlabs/instant-ngp
> **Core position:** 把 NeRF 训练从 "V100 上两天" 变成 "RTX 3090 上五分钟" 的工程论文 — 并证明瓶颈是输入编码，而非 MLP.

**Status:** v1 — 带立场。除非标 `UNVERIFIED`，数字来自论文。
**TL;DR:** 用一个*可学*的 multi-resolution hash grid 替换固定 Fourier positional encoding；让一个微型 2 层 MLP 做剩下的事。本来以为会毁掉质量的 hash collision 实际不会 — MLP 优雅地处理它们，在标准 benchmark 上速度提升 1000× 而无可测质量损失。这是 NeRF 不再是研究 artifact、开始出现在商业 pipeline（NVIDIA Omniverse、Luma AI、Polycam）的时刻。

**X-Ray.** Vanilla NeRF 99% 训练时间在做每像素 192 次 8 层 MLP 评估. Instant-NGP 问：如果 MLP 只学*邻近特征间的插值*，特征本身住在 hash-indexed grid 里呢？你得到一个显式数据结构（查询快、更新便宜）+ 用于局部平滑的 2 层 MLP. 对空间智能工程师，这是经典的 "对的*数据结构*胜过更深*网络*" 教训 — 后来 3DGS 把它推到极限。

## 📍 Research panorama timeline

```
2020         2021              2022 (Jan)              2022 (Aug)        2023
NeRF (ECCV) ► Plenoxels    ► Instant-NGP (SIGGRAPH) ► NerfAcc          ► 3DGS displaces
              (kill MLP,    YOU ARE HERE             (occupancy accel)  for robotics
              dense voxel)  hash grid + tiny MLP
              └─ "kill MLP" wing ─┘  └─ "keep tiny MLP, fix encoding" wing ─┘
```

2021–22 对 NeRF 速度的两条同时攻击。Instant-NGP 赢得影响力，因为 hash grid 泛化到 NeRF 之外（同 primitive 驱动 SDF、neural radiance caching、gigapixel image fitting）。

---

## 1 · Core architecture

### 1.1 System overview

| Component | Input | Output | Detail |
|---|---|---|---|
| Multi-resolution hash grid | xyz | 16 levels × 2 = 32-d feat | 细级 hashed |
| Tiny MLP | 32-d + view dir | RGB + σ | 2-layer, 64 wide `UNVERIFIED` |
| Occupancy grid | xyz | skip-empty bool | 缓存，定期刷新 |
| Volume renderer | (σ, RGB) | Pixel | 同 NeRF |

总参数 ~12M（多数在 hash entry）vs ~1M NeRF。反直觉但解释了速度：参数*索引*便宜，*前向*贵.

### 1.2 ⚡ Eureka moment

> **Hash collision 不是 bug — 是 feature. MLP 学会消歧冲突的特征，所以每级小 hash table 就够；信任网络自行清理.**

粗级，grid 能装进 table（无冲突）。细级，table < grid → 冲突不可避免。渲染 loss 自然把细级容量分配到*重要*空间位置（射线终止处），忽略空区冲突. **hash function 无需优化；基于 xor 的空间 hash 即可.**

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

Pipeline 是一个融合 CUDA kernel. ~10k 行手写 CUDA. 也是 Instant-NGP 的诅咒 — 见 §6.

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

空间 hash: `hash(x,y,z) = (x·π₁) XOR (y·π₂) XOR (z·π₃)`, 素数 `{1, 2654435761, 805459861}`. 便宜，相关性足够低.

### 2.1 Parameter budget

| Knob | Default | Rationale |
|---|---|---|
| L (levels) | 16 | Coarse → fine |
| T (table / level) | 2¹⁹ = 524k | 内存/质量旋钮 |
| F (feat dim) | 2 | MLP 组合 |
| N_min, N_max | 16, 2048 | 分辨率范围 |

Table 内存: `L × T × F × 4 ≈ 67 MB`. MLP <1 MB.

### 2.2 为什么冲突可行

最细级：2048³ ≈ 8.6B cell，table 524k → >16,000× 压缩. 但只有*表面附近*（σ ≠ 0）的 cell 需要独特特征 — 通常 ~0.01% 体积，远在 table 容量内. **空 cell 无害冲突，因其梯度为零.** 同样的统计论据让 Bloom filter work.

---

## 3 · Worked example: 优雅的冲突退化

不同表面上两点 — A = (0.1, 0.1, 0.1), B = (0.7, 0.3, 0.9) — hash 到细级同一 slot 42.

- 穿 A 的射线：target "red" → 把 `table[42]` 推向红.
- 之后穿 B 的射线：target "blue" → 把 `table[42]` 推向蓝.
- `table[42]` 振荡 → 细级**噪声**.
- 粗级对 A vs B *不*冲突（cell 足够），提供大部分信号. MLP 自动给细级降权.

结果：一点的高频细节略损，不致命. 论文 Figure 4：标准 hash size 下不可感.

---

## 4 · Engineering view: 1000× 从哪来

| Source | NeRF | Instant-NGP | Factor |
|---|---|---|---|
| MLP depth | 8 layers | 2 layers | ~4× |
| MLP width | 256 | 64 | ~4× |
| Per-sample cost | 192 × big MLP | 192 × tiny MLP + 16 lookups | ~10× |
| Empty-space skip | — | Occupancy grid | ~5× |
| CUDA fusion | PyTorch | Hand-written | ~5–10× |
| **Net** | | | **~1000×** |

- Lego: **~5s** 到 PSNR=30；**5 min** 到最终.
- NeRF: **~1 day** 到 PSNR=30.
- Render: **~10 FPS** at 1920×1080 on RTX 3090 `UNVERIFIED`.

**Catch:** 活在 NVIDIA CUDA 内. 单 GPU、仅 NVIDIA、难扩展、锁死 tinycudann. 下游重实现（Nerfstudio）优化较少，丢失 3–5× wall-clock.

---

## 5 · Data and evaluation

- **NeRF synthetic / LLFF:** 同数据集、同协议. 1/1000 训练时间下达到质量平价.
- **超越 NeRF：** 论文展示 SDF、gigapixel images、neural radiance caching. **Hash grid 非 NeRF 专用.**
- **未做 benchmark：** unbounded 场景（Mip-NeRF 360 的问题）、view-dependent specular 精度. 除速度外继承 vanilla-NeRF 限制.

---

## 6 · Capabilities and failure modes

### 6.1 Hidden assumptions

- **Hash collision tolerance** — 假设高频内容*在表面上稀疏*. Volumetric 现象（烟、雾）σ ≠ 0 处处皆是会违反；每个 cell 都在工作集时质量退化.
- **足够 GPU 内存** — 67 MB table 不大，但 occupancy grid + activation 把工作集推到 ~2 GB. **Jetson Nano 装不下.** Jetson Orin (8 GB shared) 是实际下限.
- **CUDA 单一文化** — 速度依赖 tinycudann fused kernel. Apple Silicon / AMD ROCm / 边缘：无一线支持. 移植级别属研究.
- **仍需 per-scene 训练** — *快*，不是*不需要*. 跨场景迁移悬崖到 VGGT 类 feed-forward 才填上.
- **Static scene** — 继承自 NeRF.

### 6.2 什么阻碍部署

机器人方面：1080p 10 FPS 适合*可视化*，不适合闭环感知（需要 30+ FPS）. 推理时 1–2 GB GPU 内存对嵌入式尴尬. Hash table 不透明 — 不解码整个场景无法检查"椅子在哪". 无编辑 primitive — 修改一片需重训. 这些正是 3DGS 后来通过*显式*解决的. Instant-NGP 是快版 NeRF；3DGS 是*另一种* NeRF.

---

## 7 · Comparison and interview tip

| Method | Where work goes | Lego training | Render |
|---|---|---|---|
| NeRF (2020) | Deep MLP | ~1 day | <1 FPS |
| Plenoxels (2021) | Dense voxels, no MLP | ~10 min | ~15 FPS |
| TensoRF (2022) | Low-rank tensor | ~30 min | ~5 FPS |
| **Instant-NGP** | Hash grid + tiny MLP | **~5 min** | **~10 FPS** |
| 3DGS (2023) | Explicit gaussians | ~30 min | **~100 FPS** |

> **🎤 Interview tip.** "Instant-NGP 实际贡献了什么？" — 正确答案：*"它把容量从网络挪到一个可学的空间数据结构（hash grid），证明 NeRF 瓶颈是输入编码而非 MLP 深度. 1000× 加速让 NeRF 实际可复现 — '显式数据结构胜过更深网络' 是 3DGS 后来推到逻辑结论的教训."* 错答："它把 MLP 变小了"。症状，不是原因.

---

## References

- **Instant-NGP** — Müller et al. *SIGGRAPH 2022.* https://arxiv.org/abs/2201.05989
- **Code** — https://github.com/NVlabs/instant-ngp
- **Plenoxels** — Yu et al. *CVPR 2022.* https://arxiv.org/abs/2112.05131
- **TensoRF** — Chen et al. *ECCV 2022.* https://arxiv.org/abs/2203.09517
- **tinycudann** — https://github.com/NVlabs/tiny-cuda-nn

## Boundary

仅解构 Instant-NGP. **不**覆盖 unbounded-scene 处理（→ `mip_nerf_360_dissection.md`）、城市级（→ `block_nerf_large_scenes.md`）、3DGS（→ `foundations/3dgs-family/3dgs_original_dissection.md`）、hash-grid SDF / image demo，或竞争的 "no MLP" 谱系.

---

[← Back to NeRF Family README](./README.md)
