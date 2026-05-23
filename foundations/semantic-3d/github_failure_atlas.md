# Semantic 3D GitHub 失败图谱 (Semantic 3D · GitHub Failure Atlas)

> **类型**：roadmap / atlas（非 dissection；不走 14 项门槛）
> **聚焦**：在 LERF / OpenScene / LangSplat / SAM 3D Objects 四条线公开 repo 的 issue / fork / momentum 中，**真实暴露的失败模式与 PR 方向**
> **核心定位**：dissection 写"它声称能查询什么"；本图谱写"复现者实际跑出来语义会糊、per-scene 训得多慢、lift artifact 长什么样、SAM 3D Objects 的 pose 为什么经常飞"

**Status:** v1 — opinionated draft, 2026-05-21。所有 star / fork / issue 数字截取自 GitHub API 当日快照；维护节奏判断标注 `UNVERIFIED` 表示作者未亲自跑过复现。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

---

## X-Ray (non-expert friendly)

(a) Semantic 3D 的四条公开 repo 路线**全部**有可复现性危机：LERF 慢且糊、OpenScene 模型权重链接 broken、LangSplat 跑完精度低、SAM 3D Objects pose 在简单物体上飞。(b) 失败的本质不是"哪个 trick 没用"，而是**三大结构性瓶颈**：开放词汇查询在 CLIP 训练分布外坍塌、per-scene 训练让规模化不可能、2D→3D lift 在遮挡 / 反射 / 弱纹理表面产生稳定 artifact。(c) 对工程师：决定用哪条线之前先看每个 repo 的 5 个最高赞 open issue —— 比 paper Table 1 更能预测你会撞到什么。

---

## 📍 Zone Momentum Snapshot (2026-05-21)

```
路线              | repo                       | stars  | last push       | open issues | momentum
─────────────────|────────────────────────────|────────|─────────────────|─────────────|──────────
LERF (NeRF)      | kerrj/lerf                 | 727★   | 2024-07-09     | 34          | 📖 衰退
OpenScene (vox)  | pengsongyou/openscene      | 820★   | 2023-10-27     | 18          | 📖 冻结
LangSplat (3DGS) | minghanqin/LangSplat       | 1045★  | 2025-10-10     | 46          | 🔧 慢但活
SAM 3D Objects   | facebookresearch/sam-3d-objects | 6665★ | 2026-04-18 | 103 (!)     | ⚡ Meta 推
```

读法：**SAM 3D Objects 在 6 个月里 6665★ 拉爆所有传统路线**（Meta 品牌 + foundation model 范式）。但 issue 103 个集中爆出 alignment / pose flying 问题，意味着"用起来"远没看上去顺。

---

## 1 · LERF — 范式证明，repo 冻结

**Repo**：[`kerrj/lerf`](https://github.com/kerrj/lerf) · 727★ · 76 forks · MIT · last push **2024-07-09** · 34 open issues · 维护几乎停摆 `UNVERIFIED`

### Failure patterns

| Pattern | Issue | 根因 |
|---|---|---|
| **CLI 渲染 relevancy map 文档缺失** | [#76 *"how to render the relevancy map with cli, given the text query"*](https://github.com/kerrj/lerf/issues/76) | viewer 给了 query UI，但下游脚本化 / batch 化无 reference 路径 — 论文级 vs 工程级 gap |
| **依赖 broken** | [#75 *"No module named nerfstudio.viewer.viewer_elements"*](https://github.com/kerrj/lerf/issues/75) | nerfstudio 升级后 LERF 不兼容；repo 不再 catch-up |
| **CLIP / DINO loss 在 eval 路径缺位** | [#89](https://github.com/kerrj/lerf/issues/89) | 训练时算的 loss 在 eval 不重算 → 难判断 over/under fit |
| **3DGS 整合愿望** | [#86 *"Compatibility with 3D scene generated using Gaussian Splatting"*](https://github.com/kerrj/lerf/issues/86) | 社区在等 LERF→3DGS port —— 实际是 LangSplat 已部分接力 |
| **Loc. Acc 复现降到 0.82**（来自 LangSplat 跨仓 issue #60） | [LangSplat #60](https://github.com/minghanqin/LangSplat/issues/60) | LERF waldo_kitchen 报 0.955，社区复现 0.818 — 论文数字优化是 lucky seed `UNVERIFIED` |

### Open-vocab 失败的真实形态

LERF 的开放词汇查询在**训练分布外的 compositional query**坍塌：
- 训过的 "yellow mug" 可工作
- 反向（"the cup that isn't yellow"）几乎全错
- 罕见 attribute（"the dusty one"）失败

根因：CLIP image-text alignment 在 spatial / negation / 罕见形容词上本身弱，lift 到 3D 不会变好。

### PR / 实验方向

- **PR 1**：fork 升级 nerfstudio 兼容 + 加 CLI relevancy export — 让 LERF 至少**可被下游脚本调用**。低门槛、高 ROI 的接力 PR。
- **PR 2**：把 LERF 当 baseline 重新跑 waldo_kitchen，公布 N seeds 的 mean ± std — 这个数还没人正经做过。
- **实验**：LERF vs LangSplat 在同一组 CLIP-OOD 查询上的对照（compositional / negation / 罕见 attribute），分类 break-down 公布。

### Momentum: 📖（范式贡献已被引用稳；repo 级几乎冻结；接力的 PR 价值在让它**仍可跑**）

---

## 2 · OpenScene — Weights 失踪危机

**Repo**：[`pengsongyou/openscene`](https://github.com/pengsongyou/openscene) · 820★ · 68 forks · Apache-2.0 · last push **2023-10-27**（>2 年未动）· 18 open issues

### Failure patterns

| Pattern | Issue | 严重度 |
|---|---|---|
| **OpenSeg checkpoint 链接 broken** | [#97 *"OpenSeg checkpoint"* (2026 reopen 风潮)](https://github.com/pengsongyou/openscene/issues/97) + [#96 "Missing Source"](https://github.com/pengsongyou/openscene/issues/96) + [#95 "Request for model weights"](https://github.com/pengsongyou/openscene/issues/95) | **致命** — OpenScene 严重依赖外部 OpenSeg feature；外部链接死后，整条管线**不可复现** |
| **distill vs evaluate.py 结果不一致** | [#90](https://github.com/pengsongyou/openscene/issues/90) | 报告数字与脚本数字内部分歧；无人回应 |
| **3DGS 整合愿望** | [#92](https://github.com/pengsongyou/openscene/issues/92) | 同 LERF — 社区希望接 3DGS，作者无回应 |
| **nuScenes multi-view fusion 坐标系不清** | [#23 (closed, 9 comments)](https://github.com/pengsongyou/openscene/issues/23), [#87, #88](https://github.com/pengsongyou/openscene/issues/87) | camera pose convention 论文未给定式 — 复现要靠 issue thread 拼凑 |

### Lift artifact 真实形态

OpenScene 的 per-pixel projection 在以下情况稳定产生 lift artifact：
- **遮挡边界**：前后景特征混在同一 voxel，查询 "the table" 时桌面边缘"染"上椅子 feature
- **反射面**（玻璃 / 桌面）：CLIP feature 看到的是反射内容，被 lift 到反射面物理位置
- **弱纹理**（白墙）：特征 dominated by noise，查询时 random voxel 高响应

### PR / 实验方向

- **PR 1（紧急）**：在 README 顶置一条 "**OpenSeg checkpoints 已不可获得**" 警告 + 指向 HuggingFace 上社区 mirror（若存在），或直接 fork 提供 mirror。否则 820★ 的 repo 等于一座纪念碑。
- **PR 2**：替换 OpenSeg → 更新的 open-vocab segmenter（如 ODISE / SAM2）。完整 working pipeline 重发布。
- **实验**：把 OpenScene 的 lift artifact**逐类**量化（per-pixel project vs feature field vs 3DGS field 在遮挡 / 反射 / 弱纹理上的 IoU break-down）。

### Momentum: 📖（论文级 anchor 仍稳；repo 实际**已死**，PR 1 是让它复活的唯一路）

---

## 3 · LangSplat — 活但 reproducibility 危机

**Repo**：[`minghanqin/LangSplat`](https://github.com/minghanqin/LangSplat) · 1045★ · 110 forks · last push **2025-10-10** · 46 open issues (zone 最高) · 维护活跃 `UNVERIFIED`

### Failure patterns

| Pattern | Issue | 含义 |
|---|---|---|
| **最终精度低到离谱（复现者中文反馈）** | [#82 *"最终评估结果精确度很低"*](https://github.com/minghanqin/LangSplat/issues/82) | 严格跟随 README 步骤跑完，下游 query 几乎全错 — 4 条评论维护者已介入但根因未结 |
| **报告 metric 与复现 gap** | [#60 *"Inconsistency between reported metric and self-trained results"*](https://github.com/minghanqin/LangSplat/issues/60) | waldo_kitchen Loc. Acc 论文 0.955 vs 复现 0.818 — gap 14 个百分点 |
| **diff_gaussian_rasterization build 失败** | [#49, #78](https://github.com/minghanqin/LangSplat/issues/49) | CUDA build 是 3DGS 家族通病；LangSplat 特化 rasterizer 让问题更尖锐 |
| **快速启动文档缺失** | [#18 (26 comments!)](https://github.com/minghanqin/LangSplat/issues/18) | 论文 199× over LERF 的口号广为流传；实际 onboard 26 评论起跳 |
| **3D-OVS 数据集复现失败** | [#20](https://github.com/minghanqin/LangSplat/issues/20) | open-vocab 3D segmentation 数字论文 vs 自训严重 gap |

### Per-scene 训练慢的真相

LangSplat 论文卖点是 "199× over LERF"。但**真正的 per-scene 训练总时长**是：
1. 3DGS base scene 重建（30 min ~ 数小时）
2. 三层级 SAM mask 提取（per-frame，几十分钟）
3. Scene-specific autoencoder 训练
4. CLIP 特征蒸馏到 GS

复现者多次反馈，**"on a real captured scene"** 端到端跑完是数小时级，不是论文给的 query latency 几毫秒 `UNVERIFIED`。"199× over LERF" 比较的是 query 阶段，不是端到端时长。这是社区**没充分讨论的口径错配**。

### PR / 实验方向

- **PR 1**：维护一个 "end-to-end pipeline time-budget" 文档 — 公开每一步的实际墙钟时间（在 reference GPU 上）。让用户对总时长有真实预期。
- **PR 2**：对 #82 / #60 做 root cause — 是 CLIP backbone 版本？SAM 版本？autoencoder 收敛 seed？逐条隔离。
- **PR 3**：移植 LangSplat → 2025 的 3DGS variant（如 4D / SuGaR / 几何更准的 splat），让它在 dynamic / outdoor 场景能用。
- **实验**：与 LERF / OpenScene 在**同一 reference scene**做 sub-axis open-vocab benchmark（不只是 mIoU overall），公布 weak-texture / 反射 / 遮挡 break-down。

### Momentum: 🔧（zone 最活的传统路线；复现痛但维护者还回应；接力 PR 价值最高）

---

## 4 · SAM 3D Objects — Meta 推、6665★、issue 雪崩

**Repo**：[`facebookresearch/sam-3d-objects`](https://github.com/facebookresearch/sam-3d-objects) · **6665★** · 797 forks · last push **2026-04-18** · 103 open issues · 维护**还在**但 issue 雪崩

### Failure patterns

| Pattern | Issue | 严重度 |
|---|---|---|
| **预测物体与 depth/mask 不对齐** | [#162 *"Prediction is not aligned with depth or mask"*](https://github.com/facebookresearch/sam-3d-objects/issues/162) | 6 comments；用户从 web demo + 本地都复现 — 输出的 mesh / pose **不在 input depth pointmap 上** |
| **简单物体上 pose 飞** | [#149 *"Weird pose estimation on white paper"*](https://github.com/facebookresearch/sam-3d-objects/issues/149) | 白纸（弱纹理 + 平面）pose 被估到完全错位 — single-image foundation model 在低信息物体上的典型崩溃 |
| **HF Model Approval 漫长** | [#5, #182 *"HF Model Approval Duration"*](https://github.com/facebookresearch/sam-3d-objects/issues/5) | 想用必须先过 Meta HF approval，社区抱怨等待 |
| **scale 与 real-world depth 不一致** | [#57 *"How to preserve real-world scale when using SAM3D with a real depth pointmap?"*](https://github.com/facebookresearch/sam-3d-objects/issues/57) | 模型输出 scale 是 canonical 单位 — 与 real metric depth 对齐需额外 alignment step，文档不清 |
| **fine-tune 路径不清** | [#42](https://github.com/facebookresearch/sam-3d-objects/issues/42) | 用户想在自己 domain（医疗 / 工业）fine-tune，没有 reference recipe |
| **ss_encoder 未释出** | [#183](https://github.com/facebookresearch/sam-3d-objects/issues/183) | 文档中提到的 ss_encoder 仍未公开 — 部分功能黑盒 |
| **gsplat build 失败** | [#181](https://github.com/facebookresearch/sam-3d-objects/issues/181) | 与 LangSplat 同样的 3DGS 家族 build 苦难 |

### Image-to-3D 范式失败的真相

SAM 3D Objects 把"semantic 3D"问题**从 per-scene 训练改写成 image-conditional generation**——是范式跳跃，不是渐进。代价：
- **不重建场景**：只出**单物体** mesh + 6-DoF；要拼成 scene 仍需自己做 layout
- **scale 漂移**：canonical 单位 ≠ real metric，下游策略要消费 metric 必须额外对齐
- **弱纹理 / 反射上崩**：foundation model 看到信息不够时不会"承认未知"，会**编造一个似然 mesh**（hallucination 3D）
- **黑盒 fail mode**：与 per-scene 训练不同，failure mode 不可调 — 重新跑两次结果可能不同

### PR / 实验方向

- **PR 1**：在 README 加 "scale alignment recipe"（结合 known depth 把输出对齐到 metric）— #57 / #186 共需此 doc。
- **PR 2**：对 #149 / #162 类 alignment failure 做 systematic study — 哪些物体类别 / 视角 / 纹理上 pose 翻转概率高？做出来是 workshop paper。
- **PR 3**：开放一个 "SAM 3D scene assembler" — 用 SAM 3D Objects 出 N 个物体，结合 metric depth 拼回 scene。当前 zone 缺这个工具。
- **实验**：与 LangSplat / SAGA promptable 路线**做 head-to-head** — 同一 prompt 在 image-to-3D vs per-scene 3DGS field 上的 IoU / pose accuracy。

### Momentum: ⚡（Meta 品牌 + 6665★ + 仍在 push；但 103 个 open issue 说明"用起来"门槛比 demo 远高）

---

## 5 · Zone 共性失败 (Cross-tool synthesis)

读完四条 repo issue 流，semantic-3D lane 的**结构性失败**：

1. **Open-vocab 在 CLIP OOD 上稳定坍塌**。LERF / OpenScene / LangSplat 都依赖 CLIP（或同代）feature，CLIP 在 spatial relation / negation / 罕见 attribute 上的弱点**全部继承到 3D**。Lift 不能修。
2. **Per-scene 训练让"规模化"成幻觉**。Feature field 路线（LERF / LangSplat）号称的"快"是 query 阶段，不是端到端 — 每场景几十分钟到数小时。`UNVERIFIED` 但社区反馈一致。机器人多场景部署不可行。
3. **Lift artifact 在三类表面稳定出现**：遮挡边界、反射面、弱纹理。论文 demo 都选"摄影棚级"场景规避 — 真实家庭 / 户外场景几乎必有这三类。
4. **Image-to-3D 改写了游戏但引入新黑盒**。SAM 3D Objects 摆脱了 per-scene 训练，代价是**单次 inference 不可解释 / 不可调**。机器人闭环可控性丢失。
5. **维护半衰期短**。LERF 2024 冻结、OpenScene 2023 冻结、LangSplat 2025 仍活、SAM 3D Objects 2026 活但雪崩。论文 1-2 年后维护停摆是常态。

---

## 6 · 维护者优先级建议

| 行动 | 谁干 | 为什么现在做 |
|---|---|---|
| OpenScene 的 OpenSeg checkpoint mirror | 任何想保 OpenScene 活的人 | 当前 820★ 的 repo 等同于已死 |
| LangSplat 端到端时长公开 | 复现过的研究生 | 全社区在用错口径 "199× over LERF" |
| SAM 3D Objects scale-to-metric recipe | 与 metric pipeline 整合的实验室 | 是把 SAM 3D 接到机器人栈的硬门槛 |
| 四条线在同一 reference scene 上的 IoU sub-axis 公开 benchmark | 任何要发 survey 的人 | 当前社区只引 overall mIoU，藏了 weak-texture 崩溃 |
| **不**做：又一个 per-scene CLIP feature field | 任何人 | 现状 4 个 repo 已塞满，无差异化空间 |

---

## Boundary

本图谱**只覆盖 2D 视觉-语言特征抬升到 3D 的路线**。它**不**覆盖：

- VLM 直接出空间答案 → [`foundations/vlm-spatial-reasoning/github_failure_atlas.md`](../vlm-spatial-reasoning/github_failure_atlas.md)
- 世界模型生成式 → [`foundations/world-model/github_failure_atlas.md`](../world-model/github_failure_atlas.md)
- 单文档深度拆解 → 见各 `*_dissection.md`
- 3DGS / NeRF 底层几何 → [`foundations/3dgs-family/`](../3dgs-family/), [`foundations/nerf-family/`](../nerf-family/)

## For the reader

- **机器人工程师**：优先选 LangSplat（zone 最活）但预算端到端**数小时** / scene。OpenScene 在 checkpoint mirror 之前不要用。SAM 3D Objects 适合**已知物体的 6-DoF**，不适合 scene reconstruction。
- **学生 / 选题**：LangSplat #82 / #60 root cause 系统 study，或 OpenScene + ODISE/SAM2 替换 OpenSeg，都是 thesis 题。
- **Reviewer**：拒绝 "我在 LERF dataset 上 mIoU X%" 没有 sub-axis（compositional / negation / 弱纹理）break-down 的论文。

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21
[← Back to semantic-3d README](./overview.md)
