# NeRF Family — 前驱范式（以及它仍在哪里击败 3DGS）

**Status:** v1 — 带立场的初稿。
**TL;DR:** NeRF 从 ECCV 2020 到 2024 年中是 radiance field 的主导范式，*作为部署基底*被 3D Gaussian Splatting 取代 — 大致是 SIGGRAPH 2023 上 arXiv 的那一刻。但 "displaced" 不等于 "dead"：在无界室外场景、城市级重建、以及小型有界场景上最后 0.5 dB LPIPS 的争夺中，NeRF 谱系到 2026 年仍是对的工具。本区域存在，是为了让只懂 3DGS 的读者明白他们继承了什么 — 以及当他们对 NeRF 仍处理得更好的问题默认上 gaussian 时错过了什么。

---

## 为什么有 3DGS 抢了风头，仍要保留 NeRF 区域

2024 之后写的多数 spatial-intelligence 手册把 NeRF 当历史脚注 — "被 gaussian 替换掉的慢 MLP"。这个框定一半正确，且危险。正确框定：

- **NeRF (2020–2022) 是范式转移。** Volumetric rendering + positional encoding + per-scene MLP 是首次让 photorealistic novel-view synthesis 从纯 RGB 输入成为可信的研究方向。之后的一切 — Instant-NGP、Mip-NeRF 360、Block-NeRF，没错连 3DGS 本身 — 都是在 vanilla NeRF 某一具体弱点上打补丁。
- **3DGS 赢的是部署，不是精度。** 在 Mip-NeRF 360 无界场景上，最佳 NeRF 变体（Zip-NeRF、Mip-NeRF 360 本身）在 LPIPS / SSIM 上仍打过 vanilla 3DGS。3DGS 赢在训练时间、渲染速率、可编辑性 — 正是机器人需要的。对于以质量为唯一指标的离线场景重建，NeRF 谱系仍有竞争力。
- **城市级仍属 NeRF。** Block-NeRF / Mega-NeRF / Switch-NeRF 从未在公里级户外重建上被 3DGS 真正挑战。3DGS 存储成本（房间级场景 ~1–2 GB）让城市级 gaussian splat 操作上很尴尬；NeRF 的 MLP 参数化按数据 scale，不按 primitive 数量 scale。

要紧的车道：**NeRF 是你想理解 *为什么* differentiable scene rendering 能 work 时该读的**，也是 3DGS 弱点（存储、无界、表面精度）反咬你时该拿出来的。

## 2026 年何时用 NeRF vs 3DGS

| Scenario | Pick | Why |
|---|---|---|
| Robot perception map, ≤room scale | **3DGS** | 100 Hz 推理、可检查 primitive、易编辑 |
| 离线 photoreal 重建，小型有界场景 | **Mip-NeRF 360 / Zip-NeRF** | LPIPS 最后 1 dB；质量 > 速度 |
| 无界户外 360° 镜头 | **Mip-NeRF 360 lineage** | Disparity-based contraction 处理天空 / 远场 |
| 城市 / 多街区重建 | **Block-NeRF / Mega-NeRF** | 空间分解；3DGS 存储崩 |
| Live SLAM 耦合 mapping | **3DGS** (GS-SLAM) | NeRF 在线集成太慢 |
| 高精度*表面*重建 | **NeuS / VolSDF (NeRF lineage)** | SDF 参数化 NeRF 仍在 meshing 上赢 |
| Drone 高度多尺度观看 | **Mip-Splatting (3DGS)** *或* **Mip-NeRF 360** | Mip-aware；aliasing 已修 |
| 压缩移动端部署 | **3DGS variants** (SOGS, Compact3D) | NeRF MLP 不易 streamable |

经验法则：**若消费者是机器人，默认 3DGS；若消费者是 renderer 或 meshing pipeline，NeRF 谱系仍在桌面上。**

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `nerf_original_dissection.md` | Mildenhall et al. ECCV 2020 — 改写规则的论文；volumetric rendering + positional encoding；训练为何要数小时 | ⚡ |
| `instant_ngp_dissection.md` | Müller et al. SIGGRAPH 2022 (NVIDIA) — multi-resolution hash encoding；NeRF 训练从数小时降到几分钟 | ⚡ |
| `mip_nerf_360_dissection.md` | Barron et al. CVPR 2022 (Google) — 无界场景 + cone-tracing 抗锯齿；3DGS 仍在追的质量 benchmark | 🔧 |
| `block_nerf_large_scenes.md` | Tancik et al. CVPR 2022 (Google/Waymo) — 通过空间块分解做城市级重建；已部署在 Waymo AV stack | 🔧 |

## 阅读顺序（推荐）

1. **`nerf_original_dissection.md`** — 建立心智模型（volume rendering、positional encoding、per-scene optimization）。没有这个，其余只是工程补丁。
2. **`instant_ngp_dissection.md`** — 让 NeRF 实际可训的工程突破。读起来像系统论文。
3. **`mip_nerf_360_dissection.md`** — 质量上限。想知道 NeRF 仍比 3DGS 强在哪，这就是答案。
4. **`block_nerf_large_scenes.md`** — 部署故事。Waymo 让 NeRF 谱系活下去的理由。

## Cross-references

- 继任范式 → `foundations/3dgs-family/3dgs_original_dissection.md`（SIGGRAPH 2023；在机器人侧取代 NeRF 的东西）
- 下一个范式转移 → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`（CVPR 2025；可能完全取代 per-scene optimization）
- 产业采用（Waymo Block-NeRF 谱系）→ `companies/wayve_world_model.md`
- Cross-representation 对比（NeRF vs 3DGS vs feed-forward pointmap）→ `crossing/representation-migration/`

## Boundary

本目录解构按*叙事价值*挑选的四篇 NeRF 谱系论文：原作 (2020)、系统解锁 (Instant-NGP)、质量 benchmark (Mip-NeRF 360)、大规模部署 (Block-NeRF)。**不**覆盖：

- 表面重建 NeRF（NeuS、VolSDF、Neuralangelo）— 独立研究线；在 `crossing/representation-migration/` 讨论 meshing 时间接涉及
- 动态场景 NeRF（D-NeRF、HyperNeRF、K-Planes）— 该 niche 被 3DGS 谱系接管；继承工作见 `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- Generative NeRF（DreamFusion、Zero-1-to-3）— 不在范围内；本区域是 reconstructive，不是 generative
- 3DGS 本体或其衍生 → `foundations/3dgs-family/`

这里的目标是 **3DGS 史前史 + 仍相关的 niche**，不是穷举 NeRF zoo。

---

*Last opinion update: 2026-05-21.*
