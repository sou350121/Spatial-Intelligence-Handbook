<!-- ontology-5axis
problem: Promptable 3D / Image-to-3D (SA3D / SAGA / SAM 3D Objects)
representation: NeRF + 3DGS feature / Mesh
sensor: RGB / RGBD / 單 image
paradigm: Hybrid + Generative (SAM 3D Objects 2025)
time: PerScene + FeedForward (依變體)
ref: ../../cheat-sheet/ontology.md §7
-->

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

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 数据来源：[facebookresearch/sam-3d-objects](https://github.com/facebookresearch/sam-3d-objects) — **6.7k★ · 103 open issues**（发布 6 个月达到 65× issues/月，远高于 FoundationPose 5× 的速率，是 hype-cycle 信号而非健康度信号）。Last code activity 2026-01-07（Layout Post-Optimization merge），**maintainer 仍活跃**（gleize / Sasha Sax 在 issue 区有实质回复，与 FP 形成对比）。下方按主题轴切片；legacy SA3D（[Jumpat/SegmentAnythingin3D](https://github.com/Jumpat/SegmentAnythingin3D)）和 SAGA（[Jumpat/SegAnyGAussians](https://github.com/Jumpat/SegAnyGAussians)）2025 后无 commit，本节聚焦 SAM 3D Objects。

### 8.1 单物体 vs 场景：API 混淆是 top issue

- **GitHub-validated**：[#21 (open, 13c) "How to inference with multiview input?"](https://github.com/facebookresearch/sam-3d-objects/issues/21)、[#37 (open) "Support multi-view inference"](https://github.com/facebookresearch/sam-3d-objects/issues/37)、[#20 (open, 9c) "How to inference with pointcloud input?"](https://github.com/facebookresearch/sam-3d-objects/issues/20)、[#103 (closed, 7c) "From single objects to scene"](https://github.com/facebookresearch/sam-3d-objects/issues/103)、[#110 (open) "Scene Inference Speedup"](https://github.com/facebookresearch/sam-3d-objects/issues/110) — 用户反复期待"多视角 / 点云 / 场景"输入，但模型**强制单图单物体**。`make_scene` 是 for-loop 串行 per-object，几分钟级延迟。
- **实地后果**：与 dissection §6 "单物体导向，不重建场景" 一致。机器人栈想做"扫场景一次 3Dfy"必须自接 SAM 3 → per-object crop → SAM 3D 循环 → 自己拼 scene；多视角融合**模型不支持**，要么挑最佳视角要么自己做 mesh 融合。

### 8.2 Canonical scale alignment：metric-aware pipeline 必须额外补

- **GitHub-validated**：[#57 (closed, 6c) "How to preserve real-world scale when using SAM3D with a real depth pointmap?"](https://github.com/facebookresearch/sam-3d-objects/issues/57) — 用 D435 真 depth 提示，**重建出 15 cm，真值 5 cm**；[#121 (open) "Controlling output mesh scale for scene integration"](https://github.com/facebookresearch/sam-3d-objects/issues/121)、[#98 (open, 2c) "Object GLB from sam_3d_objects has large scale/translation"](https://github.com/facebookresearch/sam-3d-objects/issues/98)、[#186 (open) "Orientation and scale of objects in coords grid"](https://github.com/facebookresearch/sam-3d-objects/issues/186)、[#174 (open) "Pointmap contains Inf values causing NaN scale"](https://github.com/facebookresearch/sam-3d-objects/issues/174)。
- **根因**：模型在 canonical space 训练，scale 是相对的；与 input depth 的 metric scale 对齐**需外部 alignment 步骤**（典型做法：用 mask + depth 拟合 scale factor，issue #57 closed 的方案）。
- **实地后果**：机器人闭环消费 metric pose / 抓取规划前必须额外做 scale alignment，否则 grasp planner 输入是几何形状对但尺寸错的 mesh。

### 8.3 弱纹理 / 白纸 / 镜面：foundation 仍 hallucinate

- **GitHub-validated**：[#149 (open) "Weird pose estimation on white paper"](https://github.com/facebookresearch/sam-3d-objects/issues/149) — 白纸被渲到立方体右侧（pose drift）；[#162 (open, 6c) "Prediction is not aligned with depth or mask"](https://github.com/facebookresearch/sam-3d-objects/issues/162) 用通用 web 图测试 pose 不对齐 mask；[#71 (open, 12c) "Bug: Incorrect Rotational Pose in Scene Reconstruction"](https://github.com/facebookresearch/sam-3d-objects/issues/71) — translation/scale "plausible" 但 **rotation 普遍错**（基于 mesh.glb + parameters.json 复构场景）。
- **实地后果**：与 dissection §6 "high reflection / glass 几何 stage 拓扑错" 同类，但更广 — **任何低纹理 / 大平面物体都进入风险区**。Demo 漂亮 ≠ 任意输入鲁棒；human-pref 5:1 win rate 也不告诉你 rotation 是否对。

### 8.4 License：SAM License 不是 MIT，commercial 谨慎

- **GitHub-validated**：repo 的 LICENSE 文件首行明确 `SAM License · Last Updated: November 19, 2025`（不是 Apache/MIT/CC，GitHub API 显示 SPDX = `NOASSERTION`）。Meta SAM License 历史上对商用有约束（典型 600M+ MAU clause + 不得用 SAM output 训竞品 model）。SAM 3 / SAM 3D 沿用变体。issue 区目前没有 license-specific 高 comment thread，但 [#12 (open) "Generation of STL/OBJ files"](https://github.com/facebookresearch/sam-3d-objects/issues/12) 等下游集成讨论隐含商用诉求。
- **实地后果**：commercial 部署前**必须读完整 LICENSE**；与 vggt-omega 等 CC-BY-NC 路径不同但也不是无限制 commercial-friendly。**不要默认当 Apache 用**。

### 8.5 HuggingFace 模型访问：审批拒绝高发

- **GitHub-validated**：[#82 (open, 9c) "Why was my request to download the checkpoint file rejected?"](https://github.com/facebookresearch/sam-3d-objects/issues/82)、[#158 (open) "Why can't I get the access to the checkpoint on Huggingface"](https://github.com/facebookresearch/sam-3d-objects/issues/158)、[#5 (closed, 8c) "HF Model Approval Duration"](https://github.com/facebookresearch/sam-3d-objects/issues/5)、[#165 / #182 "HF Approval"](https://github.com/facebookresearch/sam-3d-objects/issues/165) — 多用户反复被拒，无明确拒绝理由。
- **实地后果**：与 vggt-omega 早期同模式（HF gating 是 Meta release 通病）。production 团队应预留 1-2 周审批 buffer，团队邮箱 + 公司组织名 + 明确用途文案能提高通过率。

### 8.6 TensorRT / 生产部署：尚无成熟路径

- **GitHub-validated**：repo 至今**没有** TRT / ONNX 相关 issue 或 PR（grep 无结果）。[#19 (open, 18c) "Windows System Compatibility Build"](https://github.com/facebookresearch/sam-3d-objects/issues/19) 是社区在协作做 Windows 适配；[#110 (open) "Scene Inference Speedup"](https://github.com/facebookresearch/sam-3d-objects/issues/110) 反映 per-object 串行延迟；[#119 (open) "Is the model the four-step distilled one?"](https://github.com/facebookresearch/sam-3d-objects/issues/119) 显示**释出权重的蒸馏档位仍不明确**（paper 提 25→4 step distillation，但 HF ckpt 是否已蒸馏未公开确认）。
- **实地后果**：32 GB VRAM 门槛 + 串行 scene 装配 + 无 TRT 路径 → 当前**只能离线批处理**或服务器侧推理，边缘端不可行（与 dissection §4 "32 GB+ 边缘端不可" 一致）。

### 8.7 与 Wonder3D / Zero123 的混淆：定位错位高发

- **观察**：issue 区频繁出现"为何与 X 不同"或"输入要求差异"类讨论（[#21 multi-view](https://github.com/facebookresearch/sam-3d-objects/issues/21)、[#20 pointcloud](https://github.com/facebookresearch/sam-3d-objects/issues/20)），背后是用户把 SAM 3D 当 **Wonder3D / Zero123-XL / TRELLIS** 类 image-to-3D 通用工具用。**实际**：SAM 3D 强制 image + 单物体 mask（依赖 SAM 3 上游），输出是 mesh + 6-DoF layout（含场景内 pose 信息，Wonder3D 没有），主打 in-the-wild 3D 重建（SAM 3D Artist Objects benchmark）而非 novel-view synthesis。
- **实地后果**：选型时**不要按"另一个 image-to-3D"评估**；要按 "image + mask → mesh + 物体 6-DoF" 接口评估。如果你要 multi-view → 走 TRELLIS；要 NeRF 重建 → 走 Instant-NGP；要 in-the-wild 单图带 pose → SAM 3D 是唯一。

### 8.8 Texture 质量降级：mesh 输出 vs splat 输出有显著差异

- **GitHub-validated**：[#75 (closed, 10c) "Baked Texture on Mesh (.glb) is extremely washed-out/pale compared to Gaussian Splat (.ply)"](https://github.com/facebookresearch/sam-3d-objects/issues/75) — splat 颜色对，但 baked mesh 颜色严重褪色；[#178 (open) "ply result of demo_multi_object has no color"](https://github.com/facebookresearch/sam-3d-objects/issues/178)。
- **实地后果**：如果下游需要"看着像照片"的 mesh，直接用 .glb 会失望；保留 .ply Gaussian splat 出 rendering，mesh 仅用于碰撞 / 物理。

### 8.9 Maintainer 响应度：仍活跃，与 FoundationPose 形成对比

- **观察**：gleize (Contributor)、Sasha Sax 等 Meta 工程师在 issue 区实质回复（[#15](https://github.com/facebookresearch/sam-3d-objects/issues/15) 等），2026-01-07 还在 merge PR (#134 Layout Post-Optimization)、2025-12-12 add posed SA — 6 个月内的 repo 活跃度健康。
- **判断**：与 FoundationPose（社区维护）相反，SAM 3D Objects 当前处 *vendor-maintained foundation* 阶段；中短期可期待官方修一部分上述 issues（特别是 scale alignment / TRT / scene speedup）。但 license 限制和 32 GB 硬约束**不会消失**。

### 8.10 与 dissection §6.y atlas 的回灌

- 已记录 §6.y 的三条（#162 alignment、#149 white paper、#57 scale）→ **8.2 + 8.3 扩展**至 7 条同类 issue，确认是**类别性失败**而非个例。
- 新增维度：**8.4 license**、**8.5 HF gating**、**8.6 TRT 缺失**、**8.7 定位混淆**、**8.9 maintainer 健康** — 与 [`github_failure_atlas.md`](./github_failure_atlas.md) 互补；选型时建议按 8.4–8.7 四轴做 production-readiness gate。
- 对比 [`foundation_pose_dissection.md`](../pose-tracking/foundation_pose_dissection.md) §8：FP issue 集中在「输入资产 + 硬件 + 部署」，SAM 3D 集中在「单图限制 + scale + license」 — **两类 foundation 的失败族正交**，搭栈时不要互相代偿。

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
