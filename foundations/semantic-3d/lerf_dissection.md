<!-- ontology-5axis
problem: Open-vocabulary 3D
representation: NeRF + CLIP feature field
sensor: RGB + CLIP
paradigm: Hybrid + Distillation
time: PerScene-Optimization
ref: ../../cheat-sheet/ontology.md §7
-->

# LERF 解构 (LERF: Language Embedded Radiance Fields — Dissection)

> **发布时间**: ICCV 2023 (Kerr, Kim, Goldberg, Kanazawa, Tancik — UC Berkeley)
> **论文 / 模型**: LERF — Language Embedded Radiance Fields, [arXiv:2303.09553](https://arxiv.org/abs/2303.09553)
> **核心定位**: 把 2D CLIP 蒸馏到 3D neural field → **multi-scale、视角一致的文本查询**，无需类别标签。范式漂亮，**不是可部署系统**。

LERF 是 paradigm 证明；机器人团队真正融合的是 OpenScene 血统。读这篇是为了搞懂语言场*为什么*能 work；不要指望靠它部署。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item template 2026-05-21. Training-time and query-latency numbers marked `UNVERIFIED`.
**Wedge tier:** W2 · `foundations/semantic-3d/` anchor #1
**TL;DR:** LERF 干净地证明：CLIP 可以被蒸馏进 3D neural field，用于*multi-scale、视角一致的文本查询*。它也干净地证明了为什么机器人团队很少把它送出去：每场景训练（分钟级）、查询时 ray rendering、NeRF 级别几何。读懂*范式*；别指望部署。

### X-Ray (non-expert friendly)

(a) 听到"pick up the kitchen utensil"的机器人需要开放集合的语言 → 3D 位置。(b) LERF 把 CLIP 蒸馏到 NeRF 里，任意 text → 3D relevancy heatmap；*multi-scale* 技巧（小 / 中 / 全图 crop）让 `fork` 和 `breakfast counter` 在一个 field 里都能查。(c) 对工程师：范式对，部署错——每场景 NeRF 训练、按 ray 渲染查询、NeRF 级几何都不匹配机器人时间线。

### 📍 Research Landscape Timeline

```
NeRF 2020 ─► CLIP 2021 ─► Nerfacto 2023 ─► ★ LERF ICCV 2023 ─► LangSplat CVPR 2024 ─► F-3DGS 2024+ ─► feed-forward semantic fields ?
                                                  │
                                                  └── peer: OpenScene CVPR 2023 (projection fusion, no per-scene training)
```

LERF 是范式证明；LangSplat / F-3DGS 从 3DGS 侧攻 per-scene 训练瓶颈。竞赛：feed-forward 语义场能否把训练压到单位数秒，在那之前机器人团队就放弃 field 了。

---

## 1 · What LERF actually does

LERF (Kerr, Kim, Goldberg, Kanazawa, Tancik — UC Berkeley, ICCV 2023, [arXiv:2303.09553](https://arxiv.org/abs/2303.09553)) 取一个标准的 posed-image NeRF，再加两个并行 head：

1. **Radiance head** —— 标准 NeRF（在他们的 nerfstudio 实现里实为 Nerfacto）：每条 ray 采样点发出 RGB + density。
2. **Language head** —— 在*每个 3D 点*发出一个 CLIP 特征 embedding，训练目标是视角一致。

language head 的训练信号不是手标分割，而是把每张训练图按多种 patch 大小（小 crop、中 crop、整图）平铺，每张用 CLIP-ViT 编码，再监督 field 在对应 ray 上渲出的特征匹配该 2D crop 的特征。**"multi-scale" 技巧才是真正的贡献** —— 单尺度 CLIP 监督会逼 field 要么只抓物体、要么只抓场景级 context，二者不可兼得。

推理时，文本 query 经 CLIP text encoder 编码，沿采样 ray 与 3D field 做匹配。输出是 3D *relevancy heatmap* —— 任意文本字符串都能渲出"模型认为这个概念落在场景哪里"。

```
training:                                       inference:
  posed RGB ──► NeRF radiance head ──► RGB        text query ──► CLIP text encoder
                    │                                                   │
                    └─► language head ──► CLIP feat. per 3D point ──► dot product ──► 3D relevancy
                                ▲
  CLIP image encoder ── crops ──┘
  (multi-scale, view-consistent supervision)
```

---

> 📌 **Napkin Formula**: `relevancy(text, x ∈ ℝ³) = ⟨CLIP_text(text), Field_lang(x, scale)⟩` —— 文本 query 化为对学到的 **3D CLIP field** 沿 ray 采样点的向量点积，其中 **scale** 是额外的 conditioning，选取该位置由哪种 crop 大小监督。

> ⚡ **Eureka Moment**: **Multi-scale CLIP 监督才是贡献**，不是 NeRF 那层包装。朴素的单尺度蒸馏会塌缩——只能问 object query 或场景 query，不能两者兼有。用多种尺寸的 crop 监督，并把渲出的特征按 query-time scale 调控，得到的是一个真正意义上的 *3D CLIP* field，不是被刷在 3D 上的 2D CLIP。

## 2 · Why multi-scale is the contribution

CLIP 训练时是整图配整字幕。`pasta` 匹配宽 crop，`fork` 匹配紧 crop。朴素只选一种 crop 大小的蒸馏会塌掉一种 regime。

LERF 在多种尺度上 crop 监督，并把渲出的特征按 query-time scale 调控。结果是一个 field 同时回答"*kitchen utensil set* 在哪？"（scene scale）和"*fork* 在哪？"（object scale）。这就是 LERF 和 per-pixel CLIP projection 感觉上不同的地方——它是真正的 *3D* CLIP，不是被刷在 3D 上的 2D CLIP。

| Query | Useful scale | Per-pixel projection | LERF |
|---|---|---|---|
| `fork` | object | 若 2D 分割能分出来则可 | 直接可 |
| `kitchen utensils` | region | 需事后人工分组 | 直接可 |
| `the breakfast counter` | scene | 多数失败——单 crop 抓不到 | 直接可 |
| `the red one` | reference (object) | 跨视角脆 | 视角一致 |

视角一致是第二项贡献——同一 3D 点无论从哪条 ray 都发同一特征，所以镜头一动语言查询不闪。机器人侧若管线其它环节配合到位，这部分*会*重要。

### 2.5 · Worked example — `pick up the fork` on a tabletop

wrist-cam 拍 60 张早餐桌 RGB（fork、mug、plate）。

- **Per-scene LERF 训练**：高端 GPU 上 ~5–30 min `UNVERIFIED`（Nerfacto + hash grids + language head）。
- **Query `fork`** at object scale → fork 处 3D relevancy 峰值（~conf 0.85）。
- **Query `kitchen utensils`** at region scale → 更广的 heatmap，覆盖全部餐具。
- **Query `the tip of the fork`**（sub-object）→ relevancy 散布在整把叉子的体积里；*无法*定位到叉尖——撞上 multi-scale 天花板。
- **查询延迟**：10s–100s ms/query `UNVERIFIED`；1 Hz planner 可，30 Hz control 不行。

per-scene 训练 / 延迟 / scale 天花板三者中任一绑定时，LERF 静默失败 —— relevancy 看起来仍然*像*对的。

---

## 3 · Where LERF falls down (the robotics view)

LERF 是研究产物，不是部署产物。四种失败：

**Per-scene 训练成本。** 每场景一次完整 NeRF 训练—— `UNVERIFIED` 5–30 min 在高端 GPU 上，即便加 nerfacto + hash grid。机器人走进新房间没法等。3DGS 血统的后继（LangSplat、F-3DGS）把这砍掉了，但原版 LERF 的数字就这样。

**查询延迟。** 每个 text query 都要沿 field 射 ray —— `UNVERIFIED` 桌面 GPU 几十到上百 ms/query，嵌入式更差。30 Hz 策略闭环用不了；1 Hz 任务 planner 可。

**几何质量。** LERF 是 NeRF。几何足够*渲*，往往不够*碰*——表面糊、薄结构（线、边）不可靠，language head 继承 radiance head 的空间涂抹。要做抓取精度，几何往往是瓶颈而非语义。

**需要精细几何的开放集 query。** "the *tip* of the screwdriver" 同时撞 multi-scale 天花板（tip 是 sub-object）和几何天花板（糊表面）。relevancy 大致指对区域，很少指对体素。

### 3.x · Hidden Assumptions

- **能负担每场景训练** —— 对 60 秒内要动的 mobile manipulator 致命。
- **NeRF 几何足够支撑下游接触** —— 多半不行；language head 继承糊。
- **CLIP 覆盖你的词表** —— 工业 / 技术 jargon 失败。
- **multi-scale crop 覆盖 sub-object query** —— tip / edge / hole 漏掉。
- **query 频率低** —— 30 Hz 策略闭环不能 per-query 射 ray。
- **采集期间场景静态** —— 移动物体产生不一致监督。

置信被最弱一项限制——通常是 per-scene 训练。

### 3.y · GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：LERF repo `kerrj/lerf` 在 2024-07-09 后**几乎冻结**（727★ · 34 open issue · 最近 push 已 1+ 年）— CLI 渲染 relevancy map 无 reference 路径（[#76](https://github.com/kerrj/lerf/issues/76)），nerfstudio 升级后依赖 broken（[#75](https://github.com/kerrj/lerf/issues/75) `No module named nerfstudio.viewer.viewer_elements`），3DGS 整合愿望无回应（[#86](https://github.com/kerrj/lerf/issues/86)）；waldo_kitchen Loc. Acc 论文报 0.955、社区复现降到 0.818（见 [LangSplat #60](https://github.com/minghanqin/LangSplat/issues/60) 跨仓比较），论文数字优化是 lucky seed `UNVERIFIED`；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：本 dissection §3.x 列出的 "CLIP 词表覆盖、per-scene 训练成本" 在 atlas 中被升级为 **结构性失败**：open-vocab 在 CLIP OOD 上稳定坍塌（compositional / negation / 罕见 attribute 全错），这不是 trick 没用，而是 CLIP image-text alignment 本身弱、lift 到 3D 不会变好；LERF 在 atlas 中的 momentum 标 📖（论文级 anchor 仍稳，repo 级几乎冻结），机器人团队的优选路线已转 OpenScene 血统。

---

## 4 · Robot relevance — language-conditioned manipulation

LERF 正好坐在 manipulation 策略想抓语义的位置上。集成故事：

1. 离线把工作空间重建为一个 LERF（demo 前）。
2. 用户下令 `pick up the kitchen utensil`。
3. 在 LERF 上 object scale 查询，拿到 3D relevancy peak。
4. motion planner 把峰值 centroid + 附近 NeRF 几何当抓取目标。

桌面 demo 里 work。走进厨房、被要求 60 秒内动作的 mobile manipulator 上不 work —— per-scene 训练主导。后继（3DGS 语义场、feed-forward 语义场）直接攻这个瓶颈。**LERF 是正当化 lane 的概念证明；OpenScene 血统才是机器人团队真正融合的。** 对照见 [`openscene_dissection.md`](./openscene_dissection.md)。

---

## 4.5 · GitHub Deep Dive (2026-05, repo `kerrj/lerf` 727★ · 12 open issue · last push 2024-07)

### Pitfall 表

| Pitfall | 触发条件 | GitHub 证据 | 對 dissection 的補正 |
|---|---|---|---|
| **Repo 已实质停摆** | 任何 2024-08 之后想跑的人 | 12 open issue 含 [#88](https://github.com/kerrj/lerf/issues/88) `patch_tile_size_range: Tuple[int, int]` 被默认值 `(0.05, 0.5)` 触发 AssertionError，根因是 LERF 与 nerfstudio 版本 drift；workaround 是 pin `pip install git+...lerf.git@f1c7832d8...`；2025-05 仍开 | §3 "Per-scene 训练成本" 应加："**repo 工程债 ≥ 论文路线本身的成本**"——nerfstudio rolling 升级早就把上层 import 路径换了，LERF 没追 |
| **RTX 4090 OOM 渲染** | 用 `lerf-big` 配 + camera-path 渲染 | [#74](https://github.com/kerrj/lerf/issues/74) "i use 4090, why oom???" 零回应 — 24 GB VRAM 在大场景渲染段不够 | §3 "GPU 资源"未明示渲染段比训练段更吃 VRAM；§3.x "能负担每场景训练" 假设要加补丁 "**渲染峰值 > 训练峰值**，4090 不保证" |
| **nerfstudio 上层 API 已换** | 跟 nerfstudio main 安装 | [#75](https://github.com/kerrj/lerf/issues/75) `ModuleNotFoundError: nerfstudio.viewer.viewer_elements` — viewer 路径在 nerfstudio 1.x 重组 | §3 应加 "**下游依赖 rot**"；LERF 已不能 `pip install -e .` 在 2025+ nerfstudio 上跑通，必须锁老版本 |
| **5–30 min per-scene 训练数字未验证** | 想拿这数字做规划 | 仓库 README / issue 区都未给系统化复现时长；[#77](https://github.com/kerrj/lerf/issues/77) 用户连 Table 1 的 Localization Accuracy 怎么算都得自查论文 | §2.5 "5–30 min `UNVERIFIED`" 是 ontology 已标的；GitHub 侧未补——结论：**这个数字仍 UNVERIFIED**，不要在 talk 里说成 fact |
| **CLI 渲染 relevancy map 无 reference** | 想脚本化批量出图 | [#76](https://github.com/kerrj/lerf/issues/76) "How to render relevancy map with CLI for text query" 零回应 | §3 隐含假设"interactive viewer 够用"——对 batch eval / CI / 报告生成是阻断 |
| **3DGS 整合愿望无应** | 想接 .ply 输出 | [#86](https://github.com/kerrj/lerf/issues/86) "can lerf be used with 3D environment in .ply format?" 2024-12 开、零回应 | §5 "LangSplat 完全替代" 的预测在 atlas 侧成立：作者已经不接 3DGS PR / issue，社区自然漂去 LangSplat |
| **eval 无 dino/clip loss 可监测** | 想看 feature lifting 收敛 | [#89](https://github.com/kerrj/lerf/issues/89) "Why is there no dino loss or clip loss during evaluation?" — PR #2 显式不算，零回应 | §3 "silent failure" 应补：**训练曲线无 lang loss 监测**，可能训崩还看不出来——和 LangSplat [#74](https://github.com/minghanqin/LangSplat/issues/74) 是同类陷阱 |

### Repo 健康度

- ⭐ 727 · 🟡 12 open issues · last push **2024-07-09**（>10 个月）· last release n/a
- **Stale 程度：📖 archive-grade** — 不是 abandoned（issue 区还有人开），但是 maintenance-frozen
- Top thread comments 数都低（<5），无活跃讨论
- 作者已转向 nerfstudio 主线、不再独立维护 LERF
- 2025+ 想跑 LERF 必须 pin 老 commit（[#88](https://github.com/kerrj/lerf/issues/88) workaround）；新装环境跑不通

### 读者实务含义

1. **不要在 2026+ 项目里直接 `pip install` LERF**——锁 commit `f1c7832d8fd488423aa2e9e69a23160d31c4332c` + nerfstudio 0.3.x，否则 viewer / config 类型校验全炸。
2. **5–30 min 训练时长是 ontology 估计、不是仓库数字**——如果别人引用这个区间问你来源，老实说 UNVERIFIED；论文 / repo 都没系统报。
3. **OOM 风险在渲染段而非训练段**：24 GB 4090 训得动、`lerf-big` 渲染会炸（[#74](https://github.com/kerrj/lerf/issues/74)）；规划机器人闭环时按 **峰值 > 32 GB** 准备。
4. **没有 CLI relevancy 渲染管线**：要做批量 eval / 论文图表自动化需自己写 `ns-viewer` 替代，repo 不会帮你。
5. **范式参考价值 ≫ 工程参考价值**：LERF 文档读 paper 就够，不要花时间在 repo 调环境；要部署直接走 OpenScene 或 LangSplat / SAGA 后继。
6. **stale signal 校准**：727★ + 12 open issue + 10 个月无 push = "经典阅读型" repo，**不是** "可工作 baseline"——把它从内部 baseline 列表移到 "范式 anchor 列表"。

---

## 5 · Falsifiable prediction

在 2026-12 之前，3DGS 语言场（LangSplat 或其后继）将把 LERF 完全替代为语言条件 manipulation 论文的*默认*引用。到 2027-06，feed-forward 语义场变体会出现，把 per-scene 训练降到单位数秒 `UNVERIFIED`，那一刻部署反对就塌了。任何 2026+ 机器人论文若仍把原版 LERF 当主语义表示（而非 baseline）使用，应当下注反方。

**Interview Tip**：被问 LERF 时，答"首个可信的 *3D* CLIP —— 贡献是 multi-scale 监督，不是 NeRF 包装。当范式引用；部署用 OpenScene / LangSplat。失败在 per-scene 训练，不在 language head"。把读过方法的工程师与背了关键词的人区分开。

---

## References

- LERF — Kerr, Kim, Goldberg, Kanazawa, Tancik. *ICCV 2023*. [arXiv:2303.09553](https://arxiv.org/abs/2303.09553) · project: [lerf.io](https://www.lerf.io/)
- CLIP — Radford et al. *ICML 2021*. [arXiv:2103.00020](https://arxiv.org/abs/2103.00020)
- nerfstudio / Nerfacto — Tancik et al. *SIGGRAPH 2023*. [arXiv:2302.04264](https://arxiv.org/abs/2302.04264)
- LangSplat (3DGS-based successor) — Qin et al. *CVPR 2024*. [arXiv:2312.16084](https://arxiv.org/abs/2312.16084)

## Cross-references

- 融合替代方案 → [`openscene_dissection.md`](./openscene_dissection.md)
- VLM 侧推理（绕过 field 训练）→ [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/overview.md)
- 语义场如何喂 action head → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- 底层 NeRF / 3DGS 表示 → [`foundations/3dgs-family/`](../3dgs-family/)

## Boundary

本文专门解构 LERF。它**不**覆盖：semantic 3D 范式总览（→ [`README.md`](./overview.md)）；OpenScene 风格 projection fusion（→ [`openscene_dissection.md`](./openscene_dissection.md)）；LangSplat / F-3DGS / 其它 3DGS 语言场（v2 在此 queue）；manipulation 侧策略集成（→ `embodiments/manipulation/`、`bridge-to-vla/`）；语义表示的跨具身体对比（→ `crossing/representation-migration/`，TBD）。
