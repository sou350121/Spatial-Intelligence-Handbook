# Block-NeRF 解构 (Block-NeRF: Scalable Large Scene Neural View Synthesis)

> **Publication:** CVPR 2022
> **Paper:** Tancik, Casser, Yan, Pradhan, Mildenhall, Srinivasan, Barron, Kretzschmar. Google Research / Waymo. arXiv: https://arxiv.org/abs/2202.05263 · Project: https://waymo.com/intl/en_us/research/block-nerf/
> **Core position:** 把 neural radiance field 从房间级 scale 到*城市街区级*的首个方法，也是 3DGS 替代其他一切后 NeRF 谱系仍能活在 AD 栈里的原因.

**Status:** v1 — 带立场。除非标 `UNVERIFIED`，数字来自论文。
**TL;DR:** Block-NeRF 的贡献不是新 MLP — 是把城市级拍摄（Waymo 2.8M 张 Alamo Square 旧金山照片）切成 ~100 个重叠 NeRF "block" 的*系统设计*，每个独立训练，渲染时动态组合. 三个工程件：跨 block 光照一致的 per-block appearance embedding；让渲染器知道查询哪些 block 的 visibility prediction；来自分割网络的 transient-object masking. 2022 年唯一发表能做此规模的方法. **3DGS 仍无法在此规模匹配 Block-NeRF** — 存储爆炸.

**X-Ray.** Vanilla NeRF 跑 100m×100m 城市街区：训练失败、存储爆、COLMAP 跨次失去 track. Block-NeRF 说：别跟规模较劲 — 分区. 50m 直径 block，约 50% 重叠，各自一个 NeRF，查询时混合. 对空间智能工程师，这是 NeRF 从研究玩具毕业进入*生产基础设施*的时刻：Waymo 公开发表因他们已用它做 AV simulation. 该谱系（Mega-NeRF, Switch-NeRF, NVIDIA Cosmos sim-data）在 2026 年仍是 NeRF-based.

## 📍 Research panorama timeline

```
2020       2021         2022 (Feb)         2022 (Aug)        2024-26
NeRF     ► NeRF-W     ► Block-NeRF       ► Mega-NeRF        ► Waymo / Cosmos
(ECCV)     (in-the-     YOU ARE HERE       (drone octree      sim pipelines
            wild         city-scale +       decomposition)     still ship
            transient    visibility +                          Block-NeRF
            objects)     appearance)                           lineage
                         └─ "split scene into chunks" lineage ─┘
                                                                │
3DGS (2023) ─► tries city ─► storage explodes ─► defers to NeRF
              (~1GB/room → ~kTB/city block)
```

3DGS 替代了房间级 + 机器人感知的 NeRF. 在城市级户外它*从未替代* NeRF — 存储随 primitive × 场景面积 scale. Block-NeRF 留了下来.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Function | Novelty |
|---|---|---|
| Block decomposition | ~100 圆形 block，50m 直径、50% 重叠 | 手工放置；每 block 一个 NeRF |
| Per-block NeRF | Mip-NeRF 骨干 + appearance embedding head | 继承 Mip-NeRF (2021) |
| Appearance embedding | Per-image 可学 32-d；调制 color MLP | NeRF-W (2021) |
| Visibility prediction | 小 MLP：`(xyz,dir) → "block 相关？"` | **New** |
| Transient mask | 分割（行人、车）从 loss 中遮掉 | **New** |
| Block composition | 顶 K 的 inverse-distance-weighted 混合 | **New** |

### 1.2 ⚡ Eureka moment

> **在城市规模，正确的问题不是"一个 NeRF 能多大" — 而是"N 个独立 NeRF 如何渲染成一个一致场景". 一致来自 (a) 共享 appearance embedding 和 (b) visibility-aware composition，不是来自统一 MLP.**

仅深度学习的实验室会错过的系统思维. 这就是 Waymo（有生产采集 + 算力）写它而非纯 ML 组写的原因.

### 1.3 Flow diagram

```
   City capture: 2.8M images over ~3 months
                 │
                 ▼
   Spatial partition: ~100 blocks, 50m dia, 50% overlap
                 │
                 ▼
   Parallel training per block:
     Mip-NeRF + appearance embed + visibility head + transient mask
                 │
                 ▼  (rendering)
   Query (x, y, z, view dir):
     1. top-K blocks via visibility heads
     2. render each → RGB_k, weight_k = 1/distance_to_block_center
     3. blend: pixel = Σ w_k · RGB_k / Σ w_k
                 │
                 ▼
              Final rendered image
```

---

## 2 · Math core: block composition + appearance embedding

### 📌 Napkin Formula

```
RGB(query) = Σ_{k ∈ visible} w_k · NeRF_k(query, app_embed_k) / Σ w_k

w_k = (1 / distance(query, center_k))^p          # inverse-distance weighting
app_embed_k = 32-d vector per image, optimized during training
```

IDW（inverse-distance weighting）— 地理空间插值用了几十年的同样公式. 新颖处：*被加权对象*是独立的 neural radiance field.

### 2.1 为什么 appearance embedding 不可选

拍摄跨数月. 同路口 6 月（绿叶、强阴影）与 12 月（无叶、阴天）. 训练一个 NeRF 跨两者 → 雾蒙蒙灰平均. NeRF-W 解法：per-image 32-d embedding 调制 color MLP. 推理时冻到 canonical 光照（或为 time-of-day 插值）. Block-NeRF 扩展：embedding 通过联合优化在 block 间*共享*，使邻居选兼容的 canonical 光照 → 无缝.

### 2.2 Visibility prediction = 节速器

每像素穿过 100 个 block 渲染慢得不可能. Visibility head — 预测查询是否落在某 block 的良好表示区的小 MLP — 在查询时剪掉 90%+ block. **这让推理可处理.**

---

## 3 · Worked example: 距 block 中心 30 m 处渲染

附近三个 block：A（中心 0m）、B（50m）、C（100m）. 查询 30 m.

| Block | distance | visibility | weight (1/d) | RGB |
|---|---|---|---|---|
| A | 30 m | 0.95 (in) | 0.033 | (0.40, 0.30, 0.20) |
| B | 20 m | 0.90 (overlap) | 0.050 | (0.42, 0.31, 0.21) |
| C | 70 m | 0.05 | pruned | — |

Final = `(0.033·0.40 + 0.050·0.42) / 0.083 = 0.412`. A 和 B 间平滑过渡，无可见缝 — 两者都训练在 50% 重叠图像上，appearance embedding 联合优化.

---

## 4 · Engineering view: 论文构建了什么

| Metric | Value |
|---|---|
| 总图像 | ~2.8M (Alamo Square, SF) |
| 采集时长 | ~3 个月 |
| Blocks | ~100 |
| Per-block 训练 | ~12h `UNVERIFIED` |
| 总算力 | ~12k GPU-hours `UNVERIFIED — TPU-equiv` |
| Per-block 存储 | ~500 MB `UNVERIFIED` |
| 总场景 | ~50 GB |
| Render | <1 FPS at 1080p |

**不是单人项目.** 工业级 pipeline. Waymo 写它因为他们有车队和算力. **没有学术实验室在同规模复现.**

为什么仍属 NeRF：per-block neural representation 是*恒定大小*，与 feeding 图像无关. 3DGS 上，更多图像 → 更多 gaussian → 更多存储. Block-3DGS 需要 ~1 GB × 100 = 至少 100 GB，加上城市立面爆炸的 gaussian 数. **此规模下存储经济偏向 NeRF.**

---

## 5 · Data and evaluation

- **自建 Alamo Square 数据集：** Waymo 内部，未发布（发表 + demo，不是 benchmark 贡献）.
- **评测：** 定性 novel-view 渲染、穿行 demo. 论文未建立数字 benchmark — Block-NeRF *定义*了城市级问题.
- **可复现性：** 零. 代码未放；数据集未放. Mega-NeRF 在公开 drone 拍摄（Mill 19）上以更低规模复现思想.

经典论文是闭源 demo；下游在公开数据上重推思想.

---

## 6 · Capabilities and failure modes

**做：** 长时拍摄下多 block 城市场景的一致 novel-view 渲染；通过 appearance embedding 做时间 / 天气插值；对 transient 物体（车、行人）鲁棒；可驾驶轨迹（Waymo 实际 AV-sim 用例）.

### 6.1 Hidden assumptions

- **可获工业级采集** — 每 block ~30k 张、多次穿越、GPS / IMU. 单相机手持不 work.
- **空间均匀采集密度** — block 分区假设均匀分布. 稀疏 block（罕开侧街）失败；出现空洞.
- **多数静态场景** — transient masking 处理车 / 行人；*不*处理施工、季节变化、拆除. 长期变化破 embedding.
- **重训算力预算** — 加 / 更新 block 需从零重训. **非在线.**
- **位姿收敛** — 假设 GPS / SLAM 给的位姿足够好让 COLMAP refine. GPS 差的城市峡谷会失败.

### 6.1.x GitHub 实地失败（atlas 联动）

- **GitHub-validated**：Block-NeRF **没有官方公开 repo**（Waymo / Google 内部），社区复现走 Nerfstudio（11.6k★ 活跃，但默认模型列表里 `nerfacto` / `vanilla-nerf` 没有显式 Block-NeRF），详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。这就是 README §nerf-family 城市级一栏推荐至今没有对应健康 OSS 仓库的真实空白 — 工程上要走 Mega-NeRF / Switch-NeRF / 自实现。

### 6.2 为什么 3DGS (2026) 没替代它

1. **存储** — 3DGS 城市级 ~kTB；没人发那个.
2. **流式** — NeRF MLP 按 100MB block 块流式传；gaussian splat 不易流式（整 block 必须加载才能 rasterize）.
3. **生产惯性** — Waymo、NVIDIA Cosmos、大型 sim-data 商在 2022–23 标准化到 Block-NeRF 谱系，那时 3DGS 尚未证明. 迁移成本巨大；没人有动力.

2025–26 "大规模 3DGS"（Hierarchical 3DGS、Scaffold-GS）部分闭合存储. 截至 2026 年中，没有发表方法能匹配 Block-NeRF 在存储 + 质量 + 规模上的组合.

---

## 7 · Comparison and interview tip

| Property | Mega-NeRF | **Block-NeRF** | Hierarchical 3DGS (2024) | Mip-NeRF 360 |
|---|---|---|---|---|
| Scale | Drone (~km²) | City block (~km²) | City block (early) | Single 360° |
| Decomposition | Octree | Manual blocks + overlap | LOD hierarchy | None |
| Transient handling | No | Yes | No | No |
| Appearance variation | Per-image embed | Per-image embed | No | No |
| Storage at city scale | ~tens of GB | ~50 GB | ~hundreds GB–TB `UNVERIFIED` | N/A |
| Published deployment | UAV recon | **Waymo AV sim** | Research demos | Offline bench |

> **🎤 Interview tip.** "为什么 3DGS 没像替换房间级 NeRF 那样替换 Block-NeRF？" — 正确答案：*"存储. 3DGS primitive 数随场景面积 scale，把城市图推到 TB 级. Block-NeRF 的 neural representation 是 per-block 恒定大小. 直到有人发表能在 km² 规模打破存储曲线的 compressed-by-default 3DGS，NeRF 谱系仍占城市级车道 — Waymo 和 NVIDIA Cosmos 仍在生产 AV sim 中使用."* 错答："3DGS 很快会赶上". 也许；截至 2026 没人发过.

---

## References

- **Block-NeRF** — Tancik et al. *CVPR 2022.* https://arxiv.org/abs/2202.05263
- **Mega-NeRF** — Turki et al. *CVPR 2022.* https://arxiv.org/abs/2112.10703
- **NeRF in the Wild** — Martin-Brualla et al. *CVPR 2021.* https://arxiv.org/abs/2008.02268
- **Mip-NeRF 360** (per-block 骨干) — `mip_nerf_360_dissection.md`
- **Waymo project page** — https://waymo.com/intl/en_us/research/block-nerf/
- **NVIDIA Cosmos** — `foundations/world-model/nvidia_cosmos_dissection.md`
- **Wayve world model** — `companies/wayve_world_model.md`

## Boundary

仅解构 Block-NeRF. **不**深度覆盖 drone 高度的 Mega-NeRF、AV-sim 集成（→ `companies/wayve_world_model.md`, `foundations/world-model/nvidia_cosmos_dissection.md`）、大规模 3DGS 变体（→ `foundations/3dgs-family/` 未来文档），或 sensor 问题（→ `foundations/sensor-physics/`）.

---

[← Back to NeRF Family README](./overview.md)
