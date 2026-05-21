# Semantic 3D

**Status:** v1 — opinionated draft. Hyperparam / timing claims marked `UNVERIFIED`.
**TL;DR:** 机器人不需要更漂亮的点云——而是需要一个*每个点都知道自己是什么*的点云。把 2D 视觉-语言特征（CLIP、DINO、SAM）抬到 3D，是把几何变成"策略能用语言查询"对象的关键。三种范式并存；具体哪种能落地，看你能否负担 per-scene 训练、per-frame 计算、或两者都没。

---

## 为什么 2D 语义特征需要抬到 3D

CLIP、SAM、DINO 都活在像素空间。机器人活在 metric 空间。每次策略要回答"杯子是否在桌子左边？"或"去厨房用具那边"，整条栈就必须把图像平面特征桥到 controller 消费的 3D 坐标。直白的答案——每帧跑 2D 分割再反投影——在桌面单标定相机上能用，但具身体一动就崩（遮挡、视角不一致、跨帧无聚合）。更深的答案是：语义是*场景*的属性，不是*每帧*的属性，所以这次抬升应当落在 3D 里，能跨视角累积。这步累积——把 2D 特征融到能撑视角变化的 3D 结构里——就是本 lane 覆盖的。

下游消费者很具体：语言条件 manipulation（`pick up the green one`）、开放词汇导航、object-centric world model，以及任何 3D-aware VLA 的特征端。没有一个能离开可文本查询的 semantic 3D 表示。

## The 3 paradigms

- **Per-pixel projection (closed-loop fusion).** 每帧跑 2D backbone，把特征投到体素或点云，跨视角聚合。OpenScene (CVPR 2023) 是参考。*Get:* 无 per-scene 训练，zero-shot 开放词汇。*Pay:* 内存随场景增长；跨视角不一致的 2D 输出要靠融合逻辑处理。
- **Feature field (NeRF-style distillation).** 把 CLIP（或 DINO、SAM）与 radiance 联合蒸馏进一个 neural field。LERF (ICCV 2023) 是经典。*Get:* multi-scale 文本查询，构造上视角一致。*Pay:* 每场景 5–30 min 训练 `UNVERIFIED`，难在线更新，几何继承 NeRF 的局限。
- **Scene graph (object-centric symbolic).** 检测物体，赋 label 与关系，存为图（ConceptGraphs 血统）。*Get:* 占用小，与经典 planner 配合好，语言查询化约为图遍历。*Pay:* "object"这个抽象级别上有硬天花板。

横着读：projection 是机器人团队*部署*的、feature field 是论文*发表*的、scene graph 是任务 planner *消费*的。有趣的整合是两两组合。

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `lerf_dissection.md` | Kerr et al. ICCV 2023 — CLIP distilled into a NeRF feature field, multi-scale queries | ⚡ |
| `openscene_dissection.md` | Peng et al. CVPR 2023 — direct CLIP/SAM fusion into 3D voxels, zero-shot open-vocab | ⚡ |

`UNVERIFIED` scene-graph dissection (ConceptGraphs / OVIR-3D) queued for v2.

## Cross-references

- VLM 侧推理（把语言 grounded 到几何的*另一种*方式）→ [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/README.md)
- 特征所骑的底层几何 → [`foundations/feed-forward-3d/`](../feed-forward-3d/), [`foundations/3dgs-family/`](../3dgs-family/)
- Semantic cloud → action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- 跨表示的跨具身体对比 → `crossing/representation-migration/`（TBD）

## Boundary

本目录是关于"2D 视觉-语言特征如何抬到 3D"的 per-method 解构。它**不**覆盖：无显式 3D 结构的 VLM 模型（→ `foundations/vlm-spatial-reasoning/`）；3D 表示本身（→ `foundations/3dgs-family/`、`feed-forward-3d/`）；action head 消费（→ `bridge-to-vla/`）；具身侧部署（→ `embodiments/<emb>/`）。
