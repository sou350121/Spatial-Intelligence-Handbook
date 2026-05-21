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

---

## 4 · Robot relevance — language-conditioned manipulation

LERF 正好坐在 manipulation 策略想抓语义的位置上。集成故事：

1. 离线把工作空间重建为一个 LERF（demo 前）。
2. 用户下令 `pick up the kitchen utensil`。
3. 在 LERF 上 object scale 查询，拿到 3D relevancy peak。
4. motion planner 把峰值 centroid + 附近 NeRF 几何当抓取目标。

桌面 demo 里 work。走进厨房、被要求 60 秒内动作的 mobile manipulator 上不 work —— per-scene 训练主导。后继（3DGS 语义场、feed-forward 语义场）直接攻这个瓶颈。**LERF 是正当化 lane 的概念证明；OpenScene 血统才是机器人团队真正融合的。** 对照见 [`openscene_dissection.md`](./openscene_dissection.md)。

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
- VLM 侧推理（绕过 field 训练）→ [`foundations/vlm-spatial-reasoning/`](../vlm-spatial-reasoning/README.md)
- 语义场如何喂 action head → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)
- 底层 NeRF / 3DGS 表示 → [`foundations/3dgs-family/`](../3dgs-family/)

## Boundary

本文专门解构 LERF。它**不**覆盖：semantic 3D 范式总览（→ [`README.md`](./README.md)）；OpenScene 风格 projection fusion（→ [`openscene_dissection.md`](./openscene_dissection.md)）；LangSplat / F-3DGS / 其它 3DGS 语言场（v2 在此 queue）；manipulation 侧策略集成（→ `embodiments/manipulation/`、`bridge-to-vla/`）；语义表示的跨具身体对比（→ `crossing/representation-migration/`，TBD）。
