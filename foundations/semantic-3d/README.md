# Semantic 3D

**Status:** v1.2 — opinionated draft (2026-05-21 扩充至 4 篇). Hyperparam / timing claims marked `UNVERIFIED`.
**TL;DR:** 机器人不需要更漂亮的点云——而是一个*每个点都知道自己是什么*、且*能被点到*的点云。把 2D 视觉-语言特征（CLIP、DINO、SAM）抬到 3D，是把几何变成"策略能查询 / 抓取"对象的关键。当前 lane 已经分裂成**两大正交轴**：retrieval（文本 → 3D 相关度）与 promptable（点/mask → 3D 边界 / 重建）。哪种能落地，看你能否负担 per-scene 训练、per-frame 计算、或两者都没。

---

## 为什么 2D 语义特征需要抬到 3D

CLIP、SAM、DINO 都活在像素空间。机器人活在 metric 空间。每次策略要回答"杯子是否在桌子左边？"或"去厨房用具那边"，整条栈就必须把图像平面特征桥到 controller 消费的 3D 坐标。直白的答案——每帧跑 2D 分割再反投影——在桌面单标定相机上能用，但具身体一动就崩（遮挡、视角不一致、跨帧无聚合）。更深的答案是：语义是*场景*的属性，不是*每帧*的属性，所以这次抬升应当落在 3D 里，能跨视角累积。这步累积——把 2D 特征融到能撑视角变化的 3D 结构里——就是本 lane 覆盖的。

下游消费者很具体：语言条件 manipulation（`pick up the green one`）、开放词汇导航、object-centric world model，以及任何 3D-aware VLA 的特征端。没有一个能离开可文本查询的 semantic 3D 表示。

## 两条轴 × 四条路线全景

```
                    ┌────────────────────────┬───────────────────────────┐
                    │   Retrieval (text →    │   Promptable (point/mask  │
                    │   3D 相关度)            │   /image → 3D 边界 / 重建) │
┌───────────────────┼────────────────────────┼───────────────────────────┤
│ Per-pixel project │  OpenScene CVPR 2023   │   —                       │
│   (no per-scene)  │  ✅ 部署 / 流式         │                           │
├───────────────────┼────────────────────────┼───────────────────────────┤
│ NeRF feature      │  LERF ICCV 2023        │   SA3D NeurIPS 2023       │
│  field            │  ✅ 范式证明 / 慢       │   ⚠️ ~2 min/物体，退役方向 │
├───────────────────┼────────────────────────┼───────────────────────────┤
│ 3DGS feature      │  LangSplat CVPR 2024   │   SAGA AAAI 2025          │
│  field            │  ✅ 199× over LERF     │   ✅ ~4 ms/mask            │
├───────────────────┼────────────────────────┼───────────────────────────┤
│ Image → 3D 生成   │  —                     │   SAM 3D Objects 2025-11  │
│  (no scene)       │                        │   ✅ 单图 → mesh / splats  │
└───────────────────┴────────────────────────┴───────────────────────────┘
```

- **Per-pixel projection (closed-loop fusion).** OpenScene 参考。*Get:* 无 per-scene 训练、zero-shot 开放词汇。*Pay:* 内存随场景增长；跨视角融合要工程。
- **Feature field — NeRF (LERF).** *Get:* multi-scale 文本查询、构造上视角一致。*Pay:* 每场景 5–30 min `UNVERIFIED`、几何糊。
- **Feature field — 3DGS (LangSplat).** *Get:* per-query 毫秒（199× over LERF）。*Pay:* 仍 per-scene 训练 + 24 GB VRAM。
- **Promptable on field (SA3D / SAGA).** *Get:* 点 / mask 提示 → 3D 边界，SAGA ~4 ms。*Pay:* SA3D 慢 / 退役；SAGA 仍 per-scene 蒸馏。
- **Image-to-3D (SAM 3D Objects, 2025-11).** *Get:* 单图直接出 textured mesh + 6-DoF，5:1 human-pref。*Pay:* 32 GB+ VRAM、不重建场景。
- **Scene graph (ConceptGraphs blood, v2 queue).** 检测物体存图；planner 友好但 object-level 天花板。

横着读：projection 是机器人*部署*的、feature field 是论文*发表*的、image-to-3D 是 Meta foundation 推的、scene graph 是任务 planner *消费*的。

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `lerf_dissection.md` | Kerr et al. ICCV 2023 — CLIP distilled into NeRF feature field, multi-scale queries | ⚡ |
| `openscene_dissection.md` | Peng et al. CVPR 2023 — direct CLIP fusion into 3D voxels, zero-shot open-vocab | ⚡ |
| `langsplat_dissection.md` | Qin et al. CVPR 2024 Highlight — 3DGS feature field + scene autoencoder + SAM 三层级, 199× over LERF | ⚡ |
| `sam3d_dissection.md` | SA3D / SAGA / SAM 3D Objects — promptable 路线三条（NeRF / 3DGS / image-to-3D, Meta 2025-11） | ⚡ |

> 4D LangSplat (CVPR 2025) queued for v2；ConceptGraphs / OVIR-3D / SG-Reg 详见下方 watch list。

---

## Watch list — 已盯但未拆解 (v2 候選)

> 半年內回看是否升級 dissection；目前因社群熱度 / 維護 / 通用性不足暫不拆。

| Paper / Repo | 為什麼盯 | 為什麼還不拆 |
|---|---|---|
| **SG-Reg** ([arxiv 2504.14440](https://arxiv.org/abs/2504.14440), T-RO 2025, HKUST) | semantic scene graph **registration**（不是 retrieval / promptable）— 是 semantic-3d 第三條腿；3 個新意：FM-Fusion 自監督 GT / Triplet GNN 4-DoF invariance / **52 KB 帶寬論點**（multi-agent SLAM 主賣點） | [GitHub repo](https://github.com/HKUST-Aerial-Robotics/SG-Reg) 137★ / 3 open issues / 0 closed / 無 HF weights / GPLv3 / 數據鏈接失效（3RScan 已 deleted, #5）；社群影響力 < 學術影響力。跨表徵對比角度先寫在 [`crossing/representation-migration/dense_vs_graph_registration.md`](../../crossing/representation-migration/dense_vs_graph_registration.md) |
| **ConceptGraphs** (ICRA 2024) | 跨 scene graph baseline | 雖在多篇 cite 但 deployable bar 未驗 |
| **OVIR-3D** (CoRL 2023) | open-vocab 3D segmentation | 較老，新 SAM3D 部分取代 |

## Cross-references

- VLM 侧推理（把语言 grounded 到几何的*另一种*方式）→ [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/README.md)
- 特征所骑的底层几何 → [`foundations/feed-forward-3d/`](../feed-forward-3d/), [`foundations/3dgs-family/`](../3dgs-family/)
- Semantic cloud → action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- 跨表示的跨具身体对比 → [`crossing/representation-migration/dense_vs_graph_registration.md`](../../crossing/representation-migration/dense_vs_graph_registration.md)（**★ NEW** — 5 法配準對照）
- Multi-agent SLAM 後端（loop closure 下一代）→ [`foundations/classical-slam/orb_slam3_dissection.md`](../classical-slam/orb_slam3_dissection.md)（傳統 Atlas multi-map 對照）

## Boundary

本目录是关于"2D 视觉-语言特征如何抬到 3D"的 per-method 解构。它**不**覆盖：无显式 3D 结构的 VLM 模型（→ `foundations/vlm-spatial-reasoning/`）；3D 表示本身（→ `foundations/3dgs-family/`、`feed-forward-3d/`）；action head 消费（→ `bridge-to-vla/`）；具身侧部署（→ `embodiments/<emb>/`）。
