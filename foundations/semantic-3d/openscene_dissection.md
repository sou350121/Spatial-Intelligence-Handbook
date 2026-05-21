# OpenScene 解构 (OpenScene: 3D Scene Understanding with Open Vocabularies — Dissection)

> **发布时间**: CVPR 2023 (Peng, Genova, Jiang, Tagliasacchi, Tombari, Guibas — Google + ETH + Stanford)
> **论文 / 模型**: OpenScene, [arXiv:2211.15654](https://arxiv.org/abs/2211.15654)
> **核心定位**: **不需要 per-scene 训练**的开放词汇 3D 分割——把 2D CLIP 投到 3D 点上，跨视角聚合。机器人可部署；在标 label benchmark 上输给闭集模型。

OpenScene 是 LERF 的可部署对照：不再每场景训一个新 field，而是**一次训好可复用的 3D backbone**，在任意新场景上一次投影就出特征。"笨而对"的做法，结果正是机器人团队需要的。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item template 2026-05-21. Latency / memory numbers marked `UNVERIFIED`.
**Wedge tier:** W2 · `foundations/semantic-3d/` anchor #2
**TL;DR:** OpenScene 让开放词汇 3D 分割在*不需要 per-scene 训练*的前提下 work —— 把 2D CLIP 投到 3D 点/体素上、跨视角平均。笨而对 = 机器人需要的。在 labeled benchmark 上输给闭集；其它场景都赢。

### X-Ray (non-expert friendly)

(a) OpenScene 之前，需要 3D 语言 grounding 的机器人有两种坏选项：闭集分割（固定类别）或 per-scene field 训练（LERF，每房间几分钟）。(b) OpenScene 从 posed RGB(-D) 提取 dense per-pixel CLIP，投到 3D 点/体素上，跨视角平均——每个点都带 CLIP 特征；查询变点积。(c) 对工程师：**这才是可部署的 semantic-3D 模式**——流式、几何解耦、无场景训练。出活时引用它；引用 LERF 只为讲范式。

### 📍 Research Landscape Timeline

```
CLIP 2021 ─► OpenSeg / LSeg 2022 ─► ★ OpenScene CVPR 2023 ─► ConceptGraphs ICRA 2024 ─► SAM-CLIP / DINOv2-CLIP 2025+
                                            │
                                            └── peer: LERF ICCV 2023 (feature field — elegant, undeployable)
```

OpenScene 血统 = 部署方法；LERF 血统 = 优雅方法。"published" 与 "deployed" 的差距是本 lane 的核心故事。

---

## 1 · What OpenScene actually does

OpenScene (Peng, Genova, Jiang, Tagliasacchi, Tombari, Guibas — Google + ETH + Stanford, CVPR 2023, [arXiv:2211.15654](https://arxiv.org/abs/2211.15654)) 取一段 posed RGB-D 序列（或 mesh + posed images），产出一个 3D 点云，其中**每个点带 CLIP 兼容的特征向量**。文本查询化为点云上的向量相似度。

pipeline 直白得不能再直白：

1. 每张图，提取 *dense* per-pixel CLIP 特征图。论文用 OpenSeg / LSeg —— CLIP 对齐的 dense 抽取器（不是原始 CLIP-ViT，那只出一个 global vector）。
2. 每个 3D 点/体素，投到每张可见图，采样特征，跨视角聚合（average + visibility 加权）。
3. **蒸馏步骤** —— 训一个小型 3D backbone（sparse-conv MinkowskiNet）从 3D 坐标 + 颜色预测聚合特征。查询时把投影特征与预测特征 ensemble。

```
posed RGB ──► CLIP-aligned 2D dense backbone (OpenSeg/LSeg) ──► per-pixel CLIP feat.
                                                                       │
            project + multi-view aggregate ◄────────────────────────────┘
                          │
                          ├──► per-point CLIP feature (2D side)
                          │
                          └──► train MinkowskiNet to predict feature ──► per-point CLIP feature (3D side)

inference:
  text query ──► CLIP text encoder ──► dot product against per-point feature ──► open-vocab labels
```

结果是一个 3D 场景，能回答任意 text query —— `chair`、`something to sit on`、`the red object`、`kitchen utensil` —— 而从来没用这些类名训练过。

---

> 📌 **Napkin Formula**: `feat(p ∈ ℝ³) = avg_views{ CLIP_dense(image_v)[π_v(p)] · visibility(p, v) }` —— 每个 3D 点的特征是**视角加权平均的投影 dense 2D CLIP 特征**。推理 query：`relevancy(text, p) = ⟨CLIP_text(text), feat(p)⟩`。无 field 训练、无 NeRF；就只是投影并平均。

> ⚡ **Eureka Moment**: **CLIP 对齐的 2D 特征本身就 3D 一致到足够*仅靠投影*就关掉大部分到专用闭集 3D 分割器的差距**。3D backbone（MinkowskiNet）是细化，不是核心贡献——核心是投影这一洞察解锁了部署。

## 2 · Why this works without per-scene training

OpenScene 的贡献*不是*架构上的新意，而是观察到：CLIP 对齐的 2D 特征已经 3D 一致到能*靠投影聚合*，且聚合本身就关掉了大部分到专用闭集 3D 分割器的差距。一旦 per-point 特征到位，开放词汇分割就化约为文本特征点积——无 per-scene 优化、无 NeRF 训练、无第二个模型。

对照 LERF（见 [`lerf_dissection.md`](./lerf_dissection.md)）：LERF 在*每个场景*蒸馏一个新 field。OpenScene 一次性训好*可复用的 3D backbone*，在任意新场景一次前向就投影完。

| Property | OpenScene | LERF |
|---|---|---|
| Per-scene 训练 | 无 | 必需，`UNVERIFIED` 5–30 min |
| 推理 query | per-point 特征点积 | NeRF 前向 + ray 渲染 |
| 几何来源 | 提供（RGB-D / mesh） | 学（NeRF） |
| Multi-scale 文本 query | 继承 CLIP backbone | 显式 multi-scale 监督 |
| 视角一致 | 跨视角平均 | 构造上一致（field） |
| 内存开销 | O(points) —— 适中 | O(NeRF params) —— 每场景固定 |
| 机器人可部署性 `UNVERIFIED` | 流式 RGB-D 下合理在线 | 离线为主，3DGS 移植前无解 |

---

## 3 · The closed-set baseline gap

论文里诚实的部分：在 closed-set 3D 语义分割 benchmark（ScanNet、Matterport3D、S3DIS）上，OpenScene 与有监督 baseline 有明显差距。不奇怪——在 ScanNet 那 20 类上用 ScanNet 训过的模型一定胜过 zero-shot 系统。要点在于：一旦走出闭集（第 21 类、自由 query、不同 label 空间），有监督 baseline 掉到零，OpenScene 继续 work。

**对机器人，这是对的 trade。** 入户机器人遇到的物体没人 benchmark 标过。工厂机器人需要自由 form 指令。zero-shot 下限比 closed-set 上限重要。

### 3.5 · Worked example — streaming semantic map for a mobile manipulator

带 RGB-D + ORB-SLAM3 的移动机器人走过一个厨房，5 cm 体素图（~30k 体素）。

- **每帧（10–30 Hz）**：OpenSeg dense 前向 → per-pixel CLIP 特征（512-D）。
- **每个新可见体素**：投到当前帧、采特征、用 visibility 加权运行均值。
- **内存**：~30k × 512 × 4 B ≈ 60 MB `UNVERIFIED` —— Orin 装得下。
- **Query `the kitchen utensils`**：text-encode → 体素上点积 → top-K。延迟：O(N)，毫秒级。
- **失败案例**：不锈钢刀只从一个 specular 角度看到 → 单视角体素，噪声特征，错聚类。

streaming vs LERF 的胜利：同房间、同 query、**无 per-scene 训练**、适配 30 Hz 闭环。

---

## 4 · Why robotics teams cite OpenScene more than LERF

2024–2026 需要 3D 语言 grounding 的 manipulation 与 mobile-robotics 论文里，**OpenScene（或 OpenScene 血统的 projection pipeline）被作为可部署方法引用；LERF 作为优雅方法。** 三个原因：

1. **无 per-scene 训练** —— semantic 3D 在重建几何同等时间内就出。LERF 的训练循环不兼容。
2. **流式友好** —— 投影天然是 per-frame；在线 RGB-D + SLAM 系统增量地建 semantic map。LERF 需整套图先到。
3. **几何来自你已经有的部件**（depth camera、RGB-D SLAM、VGGT 类）。LERF 把几何选择与语义选择耦合——机器人团队反对这种耦合。

后续重要论文（ConceptGraphs、OVIR-3D、CLIP-Fields with online updates）都继承 OpenScene 的投影优先哲学。

---

## 5 · Where it breaks

- **dense 2D backbone 是天花板。** OpenSeg / LSeg 跨物体边界涂特征；3D fusion 继承这种涂抹。要更锐，需要 SAM-CLIP、DINOv2+CLIP 对齐等。
- **visibility 聚合是手调的。** 多视角的点可靠；少视角点噪。论文用简单加权；部署都要重新工程化这块。
- **构造上不 multi-scale。** Per-point 特征默认是 object scale。场景级 query 需要下游聚类或一个 scene-graph layer。
- **无原地更新。** 移动物体与重新摆放需要重投影。一次性 fusion，无时序。

### 5.x · Hidden Assumptions

- **几何来自他处** —— RGB-D / mesh / SLAM 体素；OpenScene 不产几何。
- **2D dense CLIP backbone 锁定质量上限** —— OpenSeg / LSeg 涂抹；SAM-CLIP / DINOv2-CLIP 抬下限。
- **每点足够 view count** —— 单视角点噪。
- **建图期间场景静态** —— 无实体跟踪；运动物体平均不一致特征。
- **CLIP 词表覆盖你的 query** —— 工业 / 领域 jargon 弱。
- **SLAM 级位姿** —— 投影误差传播为特征错聚合。

违反时表现为**对略错的格子也给出静默的高 label 置信**。

---

## 6 · Falsifiable prediction

到 2027，已出货机器人栈中的主导 semantic-3D 模式将是 OpenScene 血统投影（SAM-CLIP / DINOv2-CLIP dense backbone）配合 ConceptGraphs 风格 object layer —— *不是* feature field。LERF 血统会继续作为研究论文默认，因为图里好看；但"published vs deployed"差距会扩大、不会缩小。

**Interview Tip**：被问 OpenScene vs LERF 时，答 "OpenScene 投影 + 平均 —— 无 per-scene 训练、几何解耦、流式友好。LERF 是范式；OpenScene 是出货。" Bonus credit：把 ConceptGraphs 引为天然的 object-layer 后继。

---

## References

- OpenScene — Peng et al. *CVPR 2023*. [arXiv:2211.15654](https://arxiv.org/abs/2211.15654)
- OpenSeg — Ghiasi et al. *ECCV 2022*. [arXiv:2112.12143](https://arxiv.org/abs/2112.12143) · LSeg — Li et al. *ICLR 2022*. [arXiv:2201.03546](https://arxiv.org/abs/2201.03546)
- CLIP — Radford et al. *ICML 2021*. [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- MinkowskiNet — Choy et al. *CVPR 2019*. [arXiv:1904.08755](https://arxiv.org/abs/1904.08755)
- ConceptGraphs (successor) — Gu et al. *ICRA 2024*. [arXiv:2309.16650](https://arxiv.org/abs/2309.16650)

## Cross-references

- Feature-field 替代方案 → [`lerf_dissection.md`](./lerf_dissection.md)
- Lane 总览 → [`README.md`](./README.md)
- 仅 VLM 的空间推理（无显式 3D fusion）→ [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/README.md)
- 语义点云 → action → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

## Boundary

本文专门解构 OpenScene。它**不**覆盖：LERF 与 feature-field 范式（→ [`lerf_dissection.md`](./lerf_dissection.md)）；scene-graph 范式（ConceptGraphs、OVIR-3D —— v2 queue）；OpenScene 上游假设的 3D 几何管线（→ `foundations/feed-forward-3d/`、`3dgs-family/`）；具身侧部署（→ `embodiments/<emb>/`）；跨表示对比（→ `crossing/representation-migration/`，TBD）。
