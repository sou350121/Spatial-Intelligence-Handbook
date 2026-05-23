# SAM-in-3D 解构 (Promptable 3D Segmentation / Reconstruction — Dissection)

> **覆盖范围**: SA3D (NeurIPS 2023) · SAGA (AAAI 2025) · **SAM 3D / SAM 3** (Meta, 2025-11-19)
> **代表论文**: [arXiv:2304.12308 SA3D](https://arxiv.org/abs/2304.12308) · [arXiv:2312.00860 SAGA](https://arxiv.org/abs/2312.00860) · [arXiv:2511.16624 SAM 3D](https://arxiv.org/abs/2511.16624) · [Meta blog](https://ai.meta.com/blog/sam-3d/)
> **核心定位**: 把 SAM 从 2D 抬到 3D 的三条路线 —— NeRF-promptable (SA3D)、3DGS-promptable (SAGA)、image-to-3D 重建 (SAM 3D Objects)。**这条 lane 是 *promptable* 不是 *retrieval***，与 LERF / OpenScene / LangSplat 正交。

SA3D 用 NeRF 反投影 + 跨视角 self-prompt；SAGA 用 per-Gaussian affinity + scale gate 做毫秒级 segmentation；SAM 3D 跳过场景，单图直接 *3Dfy* 出 mesh / splats。**三者都是 promptable，与 retrieval 路线（LangSplat / OpenScene）正交**。

**Status:** v1 — opinionated draft. 延迟 / 训练时间 / VRAM 多数标 `UNVERIFIED`（仅 "SA3D ~2 min"、"SAGA ~4 ms"、"SAM 3D 5:1 win rate" 来自原文/官方）。
**Wedge tier:** W2 · `foundations/semantic-3d/` anchor #4
**TL;DR:** SAM 抬 3D 三条路：SA3D NeRF mask inverse + self-prompt（~2 min）；SAGA 3DGS affinity + scale gate（~4 ms）；SAM 3D (2025-11) 单图 → textured mesh / splats，5:1 human-pref 胜先前 single-view 方法。

### X-Ray (non-expert friendly)

(a) SAM 在 2D 上极强，但机器人栈活在 3D；如何把 SAM 的 promptable 能力抬到 3D 不丢效率？(b) 三条路：SA3D 让 SAM 在多视角 NeRF 上"扫"出 3D mask（慢，~2 min）；SAGA 把 SAM 蒸馏成每 Gaussian 的 affinity feature，提示来时毫秒级出 3D mask；SAM 3D（Meta 2025-11）不再做 in-scene 分割，直接吃单张图出完整 3D 物体（mesh + texture + 6-DoF pose）。(c) 对工程师：**这是 promptable 路线，不是 retrieval**。LERF/OpenScene/LangSplat 接 "what is *this* in 3D"；SAM-3D 路线接 "give me a 3D handle on *that thing I just clicked*" 或 "turn this image *into* 3D"。两条轴互补，机器人栈两边都要。

### 📍 Research Landscape Timeline

```
SAM 2023 ─┬─► SA3D NeurIPS 2023 (NeRF + inverse rendering + self-prompt) ─┐
          │                                                                │
          ├─► SAGA AAAI 2025 (3DGS + affinity feature, ~4 ms) ─────────────┤
          │                                                                │
          └─► SAM 2 (video, 2024) ──► ★ SAM 3D / SAM 3 (Meta, 2025-11-19) ─┴─► PCS + single-image 3Dfy
                                              │
                                              └── benchmark: SAM 3D Artist Objects (新评测集)
```

SA3D / SAGA 走"场景内 promptable 分割"；SAM 3D 跳一档，做"任意图 → 完整 3D 物体"。**SAM 3 (Promptable Concept Segmentation)** 与 SAM 3D 同包发布，把 SAM 推到 "text prompt + concept" 级 —— 但仍是 2D / video，本文不展开。

---

## 1 · 系统对比概览 (Three Routes Comparison)

### 1.1 三条路线对比

| 路线 | 代表 | 输入 | 输出 | 场景表示 | 速度 |
|---|---|---|---|---|---|
| NeRF-promptable | SA3D | 2D 点 + NeRF | voxel mask | NeRF | ~2 min |
| 3DGS-promptable | SAGA | 2D 点/涂鸦/mask + 3DGS | Gaussian mask | 3DGS | **~4 ms** |
| Image-to-3D | SAM 3D Objects | 单图 + mask | mesh / splats | **无** | 几秒 `UNVERIFIED` |

**SAM 3D 不预设场景表示** —— 吃单图 + mask 直出 3D，与 SA3D/SAGA 把 SAM 抬到已有 NeRF/3DGS 之上是不同的工程位置。

### 1.2 promptable vs retrieval 边界

| 路线 | 你问什么 | 你得到 |
|---|---|---|
| **Retrieval** (LangSplat/OpenScene/LERF) | "the red mug 在哪" | 3D 相关度 heatmap |
| **Promptable in-scene** (SA3D/SAGA) | "[点了它] 切出来" | 3D mask |
| **Image-to-3D** (SAM 3D) | "[这图里的它] 给我 3D" | mesh + 6-DoF |

⚡ **Eureka Moment**: **SAM 抬 3D 不解决"文本→3D 相关度"**。SAM 优势是"点/mask 提示→干净边界"，不是 CLIP 语义对齐。这是为什么 SAM-in-3D 与 LangSplat **不互相替代**——retrieval 回答 *what/where*，promptable 回答 *give me a handle*。

### 1.3 信息流（三路线一图）

```
SA3D:
  user 2D 点 ──► SAM 2D mask ──► inverse render to NeRF voxel
                                       │
                                       └─► 新视角渲 mask ──► self-prompt SAM ──► iterate ~2 min

SAGA:
  per-Gaussian affinity feature 训练（offline, SAM contrastive）
       │
  user 2D prompt ──► SAM 2D mask ──► 提取目标 affinity ──► 与所有 Gaussian 比 ──► 3D mask ~4 ms

SAM 3D Objects:
  single image + 物体 mask (from SAM 3)
       │
  ──► Geometry MoT (coarse 64³ voxel + 6-DoF layout) ──► Texture & Refinement flow transformer (600M+)
       │
       └─► dual VAE decoder ──► {mesh, Gaussian splats up to 32 splats / occupied voxel}
```

---

## 2 · 数学核心 (Math Core)

> 📌 **Napkin Formula**:
> SA3D: `mask_3D ← argmin_M Σ_v ‖SAM(render_v(NeRF, M)) − M_v‖`，cross-view self-prompt 迭代。
> SAGA: `mask_3D = { g : sim(aff_g · gate(s), aff_prompt) > τ }`，`aff_g ∈ ℝᴰ`，`gate(s)` soft scale gate。
> SAM 3D: `(mesh, splats) = Decoder(Refine(Geo_MoT(image, mask_2D)))`，纯前馈生成，无 per-scene 优化。

**SA3D**：每张视角 SAM 2D mask 经 NeRF density 反投到体素，多视角累积；渲新视角投影 → self-prompt SAM → 迭代收敛。

**SAGA**：把 SAM "同物体属同类" 蒸馏成 per-Gaussian affinity feature，soft scale gate 处理多粒度。query 时一次点积 + 阈值 → ~4 ms。**训练时一次性蒸馏，query 时不再 forward SAM**。

**SAM 3D Objects**：Stage 1 Mixture-of-Transformers 双流（shape + layout，cross-attention 互通）→ 64³ voxel + 6-DoF；Stage 2 flow-based transformer (~600M+) 精化 + texture；dual VAE decoder 分别出 mesh 或 Gaussian splats（≤32 splat / occupied voxel）。Distillation 扩散步数 25→4（[learnopencv](https://learnopencv.com/sam-3d/)）→ 亚秒-几秒。

| 量 | SA3D | SAGA | SAM 3D |
|---|---|---|---|
| 输入 | 2D prompt + NeRF | 2D prompt + 3DGS | 单图 + mask |
| 训练 | 无 | per-scene 蒸馏 | foundation 一次性 |
| 推理 | ~2 min | ~4 ms | 亚秒-几秒 `UNVERIFIED` |
| 输出 | voxel mask | Gaussian mask | mesh + splats + pose |
| VRAM | NeRF+SAM | 3DGS+SAM | **32 GB+** |

---

## 3 · 玩具例子 — 抓取桌上的 mug

**SAGA**（in-scene 操作首选）：离线 3DGS + affinity 蒸馏 → wrist-cam 点 mug → SAM 2D mask → 提取目标 affinity → 与所有 Gaussian 比 → 3D mask **~4 ms** → 抓取规划。

**SAM 3D Objects**（未见物体"看图建 3D"）：单图 → SAM 3 出 mask → SAM 3D 单图+mask → 完整 mug mesh + 6-DoF（亚秒-几秒，**32 GB GPU**）→ 注入仿真。

**SA3D**：同位置但慢 30000×，2024+ 在 3DGS 上几乎退役。

**失败 case**：SAGA 严重遮挡 → affinity 退化；SAM 3D 高反光 / 玻璃 → 几何 stage 拓扑错。

---

## 4 · 工程视角

| 维度 | SA3D | SAGA | SAM 3D |
|---|---|---|---|
| 在线延迟 | ~2 min | ~4 ms | 亚秒-几秒 |
| 离线开销 | 无 | per-scene 蒸馏 | 无 |
| VRAM | NeRF+SAM | 3DGS+SAM | 32 GB+ |
| 输入要求 | NeRF + 多视角 | 3DGS + 多视角 | **单图 + mask** |
| 适用 | 标注 / 离线 | in-scene 实时 | "看图建 3D" |

**部署判断**：操作闭环时间预算 → SAGA 唯一选项；"先扫后操作" → SAGA 离线蒸馏 + 在线 promptable；未见物体单图 3Dfy → SAM 3D Objects 唯一可用，但 32 GB VRAM 边缘端不可；SA3D 2025+ 实际退役。

---

## 5 · 数据与评测

- **SA3D**：在 NeRF 标准场景（Replica、ScanNet、LLFF 等）做 mask 一致性评测；具体 mIoU `UNVERIFIED`。
- **SAGA**：在 3DGS 场景集做 promptable segmentation；论文宣称"与 SOTA 相当 + ~1000× 加速 over SA3D"`UNVERIFIED`（摘要原话）。
- **SAM 3D Objects**：Meta 引入 **SAM 3D Artist Objects** 新评测集——首个 in-the-wild 3D 重建 benchmark；human preference test **5:1 win rate** over 先前 single-view 3D 方法（Meta blog 明确）。训练用 Objaverse-XL（合成预训练）+ Render-Paste（半合成）+ MITL-3DO / Art-3DO（real-world 标注），具体规模未公开。

---

## 6 · 能力与失败模式

**能做什么**：

- SAGA：场景内点击 → 毫秒 3D mask，配 3DGS 工作流天然；
- SAM 3D Objects：单图 → 完整 textured mesh + 6-DoF，foundation 级即用；
- SAM 3 + SAM 3D 组合：text 提示 → 2D mask → 3D 重建，第一条端到端 "text → 3D 物体" 链路（Meta 2025-11 同包发布）。

**不能做什么**：

- 三者都不做开放词汇 *retrieval* —— `the red one` query 仍归 LangSplat / OpenScene；
- SAGA 仍 per-scene 蒸馏，新场景要重训 affinity；
- SAM 3D Objects 单物体导向，**不重建场景**——多物体 layout 是其副产品，不是主输出；
- 几何精度未在接触级抓取 benchmark 上独立验证，工业精度需另测。

### 6.y GitHub 实地失败（atlas 联动）

- **GitHub-validated**：6665★ 但 103 open issue 全集中在 alignment / scale —— demo ≠ deploy 的范式信号。预测物体与输入 depth / mask **不对齐**（[#162](https://github.com/facebookresearch/sam-3d-objects/issues/162)），白纸等弱纹理平面上 pose 直接飞走（[#149](https://github.com/facebookresearch/sam-3d-objects/issues/149)），canonical scale 与 real metric depth 不一致（[#57](https://github.com/facebookresearch/sam-3d-objects/issues/57)）；single-image foundation 在低信息物体上 hallucinate mesh 是结构性失败，机器人闭环消费 metric 前必须额外做 scale alignment，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 6.x · Hidden Assumptions

- **SAGA**：3DGS 已建好 + SAM 在该场景出 mask 稳；多物体重叠 / 强遮挡时 affinity 蒸馏退化。
- **SA3D**：NeRF 几何足够支撑 mask inverse rendering；糊几何 → mask 跨视角不一致。
- **SAM 3D Objects**：图中物体 mask 干净（SAM 3 上游负责）；物体大体可见（occlusion >50% 风险高）；32 GB VRAM 可用。
- **三者共有**：CLIP 不参与 → 没有词表先验；要"语义检索"必须搭 retrieval 路线。
- **SAM 3D**：合成预训练 → real 对齐链长，长尾物体 OOD 风险存在；human-pref win rate 不等于 metric 精度。

---

## 7 · 与相关工作对比 (Comparison)

| 维度 | SA3D | SAGA | SAM 3D Objects | LangSplat (对照) |
|---|---|---|---|---|
| 范式 | NeRF promptable | 3DGS promptable | image-to-3D 生成 | 3DGS retrieval |
| 输入 prompt | 2D 点 | 2D 点 / mask | 单图 + mask | 文本 |
| 是否需场景 | 是（NeRF） | 是（3DGS） | **否** | 是（3DGS） |
| 在线延迟 | ~2 min | ~4 ms | 亚秒-几秒 | ~毫秒 |
| 训练 | 无 | per-scene | foundation 即用 | per-scene |
| 主用途 | 标注 | 操作 | "现场 3Dfy" | 语义查询 |

关键观察：**LangSplat 与 SAGA 同住 3DGS 上但解不同问题**——LangSplat 接 *text → relevancy*，SAGA 接 *point → 3D mask*。机器人栈通常**两者都要**：LangSplat / OpenScene 找"在哪"，SAGA 给"干净边界"。SAM 3D Objects 是第三轴，跳过 in-scene，做"图 → 物体 3D"。

**面试 Tip**：被问 "SAM 怎么抬到 3D" 时，答 "三条路：NeRF promptable (SA3D, ~2 min, 退役)、3DGS promptable (SAGA, ~4 ms, 操作首选)、image-to-3D (SAM 3D Objects, 2025-11, 单图出 mesh)。这是 promptable 轴，与 LangSplat/OpenScene 的 retrieval 轴正交——机器人栈通常两边都用。" 把"SAM in 3D"这条 lane 拆成三个工程位置而不是一团是关键。

---

## References

- **SA3D** — Cen et al. *NeurIPS 2023*. [arXiv:2304.12308](https://arxiv.org/abs/2304.12308) · [project](https://jumpat.github.io/SA3D/) · [code](https://github.com/Jumpat/SegmentAnythingin3D)
- **SAGA** — Cen, Fang et al. *AAAI 2025*. [arXiv:2312.00860](https://arxiv.org/abs/2312.00860) · [code](https://github.com/Jumpat/SegAnyGAussians)
- **SAM 3D: 3Dfy Anything in Images** — Meta. *2025-11-19*. [arXiv:2511.16624](https://arxiv.org/abs/2511.16624) · [blog](https://ai.meta.com/blog/sam-3d/) · [code](https://github.com/facebookresearch/sam-3d-objects)
- **SAM 3** (sibling, 2D PCS) — Meta. *2025-11-19*. [announcement](https://about.fb.com/news/2025/11/new-sam-models-detect-objects-create-3d-reconstructions/)
- **SAM** (foundation) — Kirillov et al. *ICCV 2023*. [arXiv:2304.02643](https://arxiv.org/abs/2304.02643)

## Cross-references

- Retrieval 路线对照 → [`langsplat_dissection.md`](./langsplat_dissection.md), [`openscene_dissection.md`](./openscene_dissection.md), [`lerf_dissection.md`](./lerf_dissection.md)
- 底层 3DGS → [`foundations/3dgs-family/`](../3dgs-family/)
- VLM 侧推理 → [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/overview.md)
- 3D mask → action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

## Boundary

本文覆盖把 SAM 抬到 3D 的**三条 promptable 路线**。它**不**覆盖：retrieval 路线（→ `langsplat_dissection.md`、`openscene_dissection.md`）；SAM 2 视频追踪（→ 留 v2，VLA-Handbook 工具篇覆盖）；SAM 3 PCS 自身（2D / video，本仓 2D 视觉边界外）；mesh extraction from 3DGS（→ `foundations/3dgs-family/`）；具身侧策略集成（→ `embodiments/manipulation/`、`bridge-to-vla/`）。

---
[← Back to semantic-3d README](./overview.md)
