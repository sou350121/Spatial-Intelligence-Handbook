# SpatialVLM 解构 (SpatialVLM: Endowing VLMs with Spatial Reasoning — Dissection)

> **发布时间**: CVPR 2024 (Chen, Xu, Sajjadi, Adam, Whitney, Hsu, Liu, Driess, Tsang — Google DeepMind)
> **论文 / 模型**: SpatialVLM, [arXiv:2401.12168](https://arxiv.org/abs/2401.12168)
> **核心定位**: 一篇**披着模型论文外衣的数据论文** —— 用网络图像 depth + open-set seg 自动合成 ~2B 空间 QA、微调一个 VLM、让规模做功。定性赢；精确 metric / 遮挡输。

SpatialVLM 是最干净地指出"当前 VLM 在空间推理上的差距是**监督差距，不是容量差距**"的论文。架构平淡；数据管线才是贡献。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. QA-pair counts and capability numbers are paper-claimed unless noted; deployment latency marked `UNVERIFIED`.
**Wedge tier:** W2 · `foundations/vlm-spatial-reasoning/` anchor #1
**TL;DR:** SpatialVLM 的论点：通用 VLM 已经*看见*足够多的几何 —— 缺的是关于如何*说出来*的监督。补救方式是暴力：从网络图像跑 depth + open-set 分割，自动合成约 20 亿条空间 QA triple，微调，让规模做功。在定性关系上大体对；在精确 metric 距离与遮挡场景上明显不对——而那恰恰是机器人部署关心的情况。

### X-Ray (non-expert friendly)

(a) VLM（GPT-4V、PaLI-X）在"A 比 B 近吗？"上失败，因为它们的网络 caption 预训练几乎只描述图里*有什么*，几乎不描述*在 3D 哪里*。(b) SpatialVLM 在网络图像上跑 depth + segmentation，**算法合成约 20 亿条 (image, spatial question, answer) triple**，微调标准 VLM，定性空间推理涌现。(c) 对空间 AI 工程师：在粗粒度定性任务上用 SpatialVLM 风格感知；要做精细任何东西，推理时再注入显式 depth token —— 纯 VLM 在 metric 距离上会到顶。

### 📍 Research Landscape Timeline

```
CLIP 2021 ─► PaLI-X / PaLM-E 2023 ─► ★ SpatialVLM CVPR 2024 ─► SpatialBot 2024 ─► SpatialRGPT 2024 ─► VLM + depth-token hybrid 2026+
                                                  │
                                                  └── peer: feature-field lane (LERF / OpenScene) — explicit 3D, no VLM
```

SpatialVLM 占据 VLM 空间推理的**数据侧**；SpatialBot / SpatialRGPT 在推理期加显式 depth token。汇合点是混合——以合成 QA 预训练、以 depth token 推理。

---

## 1 · The claim that matters

SpatialVLM (Chen, Xu, Sajjadi, Adam, Whitney, Hsu, Liu, Driess, Tsang — Google DeepMind, CVPR 2024, [arXiv:2401.12168](https://arxiv.org/abs/2401.12168)) 是一篇*数据*论文披着模型论文。架构是标准 VLM（PaLI-X / PaLM-E 风格 backbone）。贡献是数据管线。

论点：

1. VLM 在空间推理上失败，因为预训练 corpus 几乎没有空间关系监督。网络 caption 描述图里*有什么*，不描述*在 3D 哪里*。
2. 我们可以*合成*大规模空间监督：在网络图像上跑 monocular depth + open-set 分割，再代数地算出空间关系。
3. 在 2B-pair 规模做完再微调，定性空间推理涌现；有些定量；结果可以当机器人的感知层。

论文用实验支持 #3。社区从那以后一直在争论该信 #3 几分。

---

> 📌 **Napkin Formula**: `spatial_VLM = VLM(backbone) + finetune(2B auto-synth QA from depth × seg × templates)` —— 同架构、**新监督分布**。20 亿这个数字就是全部贡献。

> ⚡ **Eureka Moment**: **空间推理是监督问题，不是容量问题。** 同 backbone + 2B 空间 QA 胜过*更大* backbone 而只有网络 caption 预训练—— VLM 本就有特征，只是没人教它浮上来。

## 2 · The data pipeline (the actual contribution)

```
web image ──► depth model (ZoeDepth/Metric3D) ──► dense metric depth
           └► open-set seg (SAM + tagger)     ──► masks + labels
                             │
                             ▼
              centroid + bbox + depth per object
                             │
                             ▼
        algorithmic QA template fills:
          "Is {A} closer than {B}?"  "How far is {A} from {B}?"
          "Is {A} above {B}?"        "What is the size of {A}?"
                             │
                             ▼
              ~2B (image, question, answer) triples
                             │
                             ▼
              fine-tune VLM (next-token loss)
```

要注意的几个细节：

- **Depth 源不确定性是真的。** ZoeDepth 类模型在野外给出 metric depth `UNVERIFIED` ±10–20% 的 scale 误差。合成的距离答案继承这个误差。Metric 距离表现的上限被深度模型卡住。
- **开集分割是第二处漏。** 命名错 / 分割错的物体把错 QA 传播下去。论文把这接受为"被规模洗掉的噪声"。
- **模板有限。** 几十个模板 × 组合填空 → 2B pair。模型学得很好——能泛化到模板形状的机器人问题，遇到模板外措辞会卡。

### 2.5 · Worked example — synthesizing one QA pair

网络图："厨房料理台上一只 mug、一把 fork 与一块木板。"

1. **Depth**（ZoeDepth）：mug z=0.84 m，fork z=0.79 m `UNVERIFIED scale`。
2. **Open-set seg**（SAM+tagger）：`mug`、`fork` masks；像素 centroid。
3. **抬到 3D**：mug at (0.12, 0.05, 0.84)，fork at (0.04, 0.06, 0.79)。
4. **模板填**：`"Is {A} closer than {B}?"` with A=fork, B=mug → compute `z(fork)<z(mug)` → `Yes`。
5. **加入** `(image, "Is the fork closer than the mug?", "Yes")` 到 2B 池。

不在 pipeline 内：人工核验、亚厘米标定、遮挡检查。规模能洗掉定性噪声——洗不掉精确度。

---

## 3 · Why scale-of-data is the lever (not architecture)

最强的结果是与架构更花哨但空间数据更少的 baseline 对比：SpatialVLM *相同 backbone*显著胜过*更大 backbone 但仅 web caption 预训练*的 VLM。让人不舒服的暗示：**当前 VLM 在空间推理上的差距，主要是监督差距，不是容量差距。** VLM 本就有特征；没人教它浮上来。

| Lever | Cost | Effect |
|---|---|---|
| 更大 backbone、同数据 | 高 | 小 `UNVERIFIED` |
| 同 backbone、2B 空间 QA | 中 | 大（论文主结果） |
| 推理时显式 depth token | 低 | 大，但与传感器绑定（SpatialBot） |
| 3D-aware backbone（点 / 体素） | 高 | 比数据规模化小 `UNVERIFIED` |

在"扩 VLM"和"扩空间监督"之间预算选其一，请扩监督。

---

## 4 · Where SpatialVLM falls down

决定 SpatialVLM 能否摆在机器人前面的失败模式：

**精确距离。** "几厘米？"产出合理*形式*与不可靠*数字*。深度模型下限（§2）卡死这点。亚厘米夹爪精度无替代——必须用标定深度传感器。

**遮挡 query。** 部分遮挡 → 分割误开火 → 错深度 → 错 QA → 微调学到错关联。模型仍自信回答。**自信地错比无知更糟**——而模型不承认无知。

**模板外措辞。** 机器人团队提出模板从未覆盖的问法。退化未被旗标。

**无时序推理。** 单图条件。运动问题需要另一 lane。

**视角依赖。** 镜头一动答案就变——仍是 2D 条件。没有 feature field 那种视角一致（对比 [`../semantic-3d/lerf_dissection.md`](../semantic-3d/lerf_dissection.md)）。

### 4.x · Hidden Assumptions

- **深度源误差（~10–20%）OK** —— 亚厘米任务请改用标定传感器。
- **开集分割够可靠** —— 分割误开火 → 自信错的训练对。
- **query 落在几十个 QA 模板内** —— 模板外措辞静默退化。
- **场景完全可见** —— 遮挡 → 错分割 → 错答案，依旧自信。
- **单图足够** —— 无时序、无视角一致。
- **CLIP 词表覆盖你的领域** —— 工业 / 小众物体 OOD。

自信地错才是危险模式 —— SpatialVLM 不承认无知。

**Interview Tip**："数据论文不是模型论文 —— 2B 自动合成 QA 才是贡献。在定性空间关系上用；任何 metric 任务把显式 depth token 拼上。纯 VLM 在遮挡与亚厘米精度上到顶。SpatialBot 是显式 depth-token 后继。"

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：SpatialVLM 是 Google DeepMind 论文 [arXiv:2401.12168](https://arxiv.org/abs/2401.12168)，**未发布官方训练代码或权重** `UNVERIFIED`（2026-05 GitHub 搜索仅返回学生项目与社区复刻）；继承"自动合成 spatial QA"思想的最活跃公开实现是 [`remyxai/VQASynth`](https://github.com/remyxai/VQASynth)（567★ / 2026-05-15 last push）；社区可见失败：复现版能力远低于论文（LLaVA backbone + ~10⁴ QA ≠ PaLI-X + 2B QA — 论文核心**规模论点**在小规模上根本测不到），Precise metric distance 严重偏差（网络图像 depth 是相对的；自动合成 templates 把 "0.4 m" 当 ground truth，但 ZoeDepth 在户外/反光面误差 >30% `UNVERIFIED`），遮挡场景 hallucination（监督源 seg + depth 在遮挡区本身 garbage in）；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：本 dissection §4.x "深度源误差（~10–20%）OK"、"开集分割够可靠"、"模板内措辞" 三条假设在 atlas 中被升级为 **结构性失败** — 隐式 QA 预训练 vs 推理期 depth 注入两条路线**至今无受控实验**，是 atlas 标为 "2026+ VLM 空间路线最重要的未做实验"；SpatialVLM 在 atlas 中 momentum 标 📖（论文级影响大，repo 级几乎零自有动量），社区借数据管线想法做下游 trainer。

---

## 5 · Bridge to VLA — the integration question

诱惑：把 SpatialVLM 接到 VLA 前面。SpatialVLM 输出空间 caption（"red cube at front-left, 8 cm from gripper"），VLA 当作 prompt 消费，action head 执行。这就是 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) 中的 "spatial caption" 模式。

权衡：

- *Get:* action head 零架构变动。任何接受文本的 VLA 都接受 SpatialVLM 输出。
- *Pay:* caption 是有损投影——不在模板里的几何就丢了。dense 3D 特征点云携带的信息远多得多。

读：SpatialVLM 在*粗粒度、定性任务上是有竞争力的感知*；对*需要稠密或精确几何的任务则是非起点*。后者归 semantic-3D 与 feed-forward-3D lane。请看 bridge doc §2 的对照表。

---

## 6 · Falsifiable prediction

到 2026-12，VLM-for-robotics 论文的主导模式将是 **SpatialVLM 风格隐式预训练 + 推理时显式 depth token** —— 不是任一独用。纯 VLM 在粗关系任务上到顶；纯 depth-token 对传感器故障脆。任何 2026 manipulation 系统声称仅靠 VLM 而无 metric depth 解决问题的，应当下注反方。

---

## References

- SpatialVLM — Chen et al. *CVPR 2024*. [arXiv:2401.12168](https://arxiv.org/abs/2401.12168) · [spatial-vlm.github.io](https://spatial-vlm.github.io/)
- ZoeDepth — Bhat et al. 2023. [arXiv:2302.12288](https://arxiv.org/abs/2302.12288) · Metric3D — Yin et al. *ICCV 2023*. [arXiv:2307.10984](https://arxiv.org/abs/2307.10984)
- SAM — Kirillov et al. *ICCV 2023*. [arXiv:2304.02643](https://arxiv.org/abs/2304.02643)
- SpatialBot — Cai et al. 2024. [arXiv:2406.13642](https://arxiv.org/abs/2406.13642)
- PaLM-E — Driess et al. *ICML 2023*. [arXiv:2303.03378](https://arxiv.org/abs/2303.03378)

## Cross-references

- 替代 lane（显式 3D 语义抬升）→ [`foundations/semantic-3d/`](../semantic-3d/README.md)，尤其 [`openscene_dissection.md`](../semantic-3d/openscene_dissection.md)
- VLM lane 总览 → [`README.md`](./README.md)
- VLA 集成 → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)（SpatialVLM = "captions" 行）
- 消费空间 caption 的 3D-aware VLA → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)

## Boundary

本文专门解构 SpatialVLM。它**不**覆盖：范式对比（→ [`README.md`](./README.md)）；SpatialBot / SpatialRGPT 的 depth-token 血统（v2 queue）；benchmark-driven 训练（→ `benchmarks/reasoning/`）；VLA 架构的 3D-encoder 侧（→ `bridge-to-vla/`，VLA-Handbook）；跨具身体评测（→ `crossing/representation-migration/`，TBD）。
