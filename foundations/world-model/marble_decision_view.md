# World Labs / Marble 决策视角 (World Labs / Marble — Decision-Useful Slice Only)

> **发布时间**: World Labs / Marble launch — late 2024 (product blog; no peer-reviewed technical report as of 2026-05)
> **论文 / 模型**: Marble — World Labs (Fei-Fei Li / Justin Johnson / Christoph Lassner / Ben Mildenhall)
> **核心定位**: 由 NeRF / 3DGS 创始团队带出来的**消费级 3D 场景生成器**——只有当其底层 single-image-to-3D 管线可能喂给策略时，才与机器人相关。

本文刻意是一个**decision-useful slice**，不是全解构。按项目 PRD，Marble 表面约 90%（创意工具、VR 创作、交互 UX）划在范围外。我们记录余下 10% 为什么尚不足以正当化机器人集成——以及哪些变化会改变结论。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Most product-side specs from blog / demo posts, marked `UNVERIFIED`.
**Wedge tier:** W3 · 📖 [WorldModel]
**TL;DR:** Marble（World Labs, 2024）是**消费级 3D 场景生成器**。其表面约 90%——交互式 3D 内容创作、VR 场景生成、创意工具——按本仓项目 PRD 是**显式 out of scope**。我们保留的窄片：底层 **single-image / sparse-view → 3D 场景表示**管线，与 feed-forward 3D 重叠，可能成为**策略增广**源（novel-view 监督、单 wrist-camera 帧的深度）。只解构那一片，并明确标出我们没覆盖的内容。

### X-Ray (non-expert friendly)

(a) Marble 是写 NeRF / 3DGS 的团队搞出的消费级 3D 场景生成器；从 prompt 或图像产出可漫游 3D 世界。(b) 对具身 AI 而言，只有底层的 **single/sparse-image → 3D 管线**重要——而它仍是封闭、未发表、未对 ScanNet++ / TUM-RGBD 做基准评测的。(c) 对空间 AI 工程师：**今天用 VGGT 或 DUSt3R，关注 World Labs 的研究端发表，不是产品页**。

### 📍 Research Landscape Timeline

```
NeRF 2020 ─► Mip-NeRF 2021 ─► 3DGS SIGGRAPH 2023 ─► DUSt3R 2024 ─► VGGT CVPR 2025
                                                                       │
                                                ★ World Labs / Marble (consumer 3D, closed) 2024 ─► API or paper 2026? ─► ?
```

Marble 的定位与 feed-forward 3D **邻接**——同一批人、同一血统——但产物以消费产品形态发布，而非 benchmark 过的模型。开 vs 闭是此处的决定性轴。

---

## 1 · Why this file is short on purpose

World Labs（创始人：Fei-Fei Li、Justin Johnson、Christoph Lassner、Ben Mildenhall——NeRF / Mip-NeRF / 3DGS 血统）在 2024 年底把 Marble 作为生成式 3D 产品发布。营销面很大：输入 prompt 得可漫游 3D 世界、交互编辑、VR 交付。按本仓项目 PRD 的"only decision-useful"原则，**那里的目标用户是人类创作者，不是机器人策略**。我们不覆盖那部分。

我们覆盖的——而且只很简短地覆盖，因为它处在更有据可查的系统的阴影里：

| In scope (decision-useful) | Out of scope (consumer 3D) |
|---|---|
| 底层 feed-forward image → 3D 管线 | 交互式场景编辑 UI |
| 对机器人 wrist camera 的深度 / pointmap 输出质量 | 生成式场景创作 |
| NVS 作 VLA 数据增广源 | VR / AR 内容交付 |
| 对比 VGGT / DUSt3R 血统 | 消费级 prompt-to-world 质量 |

如果维护者想读完整的创意工具故事，应当去看媒体 AI 综述，不在本仓。

---

> 📌 **Napkin Formula**: `robot-relevance(Marble) = openness × benchmark_coverage × distribution_match` —— 当前三项乘积接近零，所以用 VGGT / DUSt3R。

> ⚡ **Eureka Moment**: 当年*开源*了 NeRF 与 3DGS 的同一批创始人，选择把 Marble 作为**封闭消费产品**发布。这个**选择**——而非任何架构差异——才是它在本仓只是脚注、而 VGGT 是旗舰的原因。机器人影响跟随的是开源权重 + 标准 benchmark，不是华丽 demo。

## 2 · The decision-relevant slice in one paragraph

只要 Marble 或任何 World Labs 研究产物暴露出一条把 single / sparse RGB view 转成 3D 表示的管线，**相关比较对象是 feed-forward 3D lane**（`foundations/feed-forward-3d/`）。那 lane 已经有 VGGT、DUSt3R、MASt3R、π³——均有公开权重且文档齐全的学术系统。Marble 的底层技术——就目前披露的（多为 blog post，截至 2026-05 无开源权重、无 peer-reviewed 解构）`UNVERIFIED`——看起来处在同一概念家族（学到的场景 3D 先验 + 可微渲染），但**闭源、消费品调优**、未在机器人 benchmark 上验证。

对 manipulation 工程师而言，**实用答案是：用 VGGT 或 DUSt3R**。Marble 的管线没有暴露成策略能消费的形态、在 ScanNet++ / TUM-RGBD / 机器人相关集合上无公开评测、且未作为研究产物维护。

---

## 3 · Where Marble could (in principle) help an embodied policy

| Hypothetical use | Plausibility | What would need to change |
|---|---|---|
| Single-image → 3D，给 wrist-camera 做 NVS 监督 | Medium | 需要 API 或权重发布；当前产品封闭 |
| Sparse-view → 场景重建做导航预建图 | Low | VGGT / 3DGS 已能且开源 |
| 生成场景增广 VLA 训练 | Low | 消费级 3D 场景对机器人具身分布失配（过审美、无接触物理） |
| Teleop 时 AR-overlay 风格 NVS 渲染 | Medium | 可能，但工具侧；无已发表机器人部署故事 |

读这张表的方式：**Marble 在结构上与机器人有用能力邻接，但产品层阻止 drop-in 使用，而开放学术血统（DUSt3R / VGGT / 3DGS）已经用可复现 benchmark 覆盖了同样的原语**。

---

### 3.5 · Worked example — should I switch from VGGT to Marble?

场景：一支 manipulation 团队有一条可用的 VGGT wrist-camera NVS 管线；他们读到 Marble 上线博客，问要不要切。

今天的决策清单：

| Check | VGGT | Marble |
|---|---|---|
| 开源权重 | ✅ | ❌ |
| 在 ScanNet++ / TUM-RGBD 上有 benchmark | ✅ | ❌ 无公开数字 |
| API / 批推理 | ✅ via HuggingFace | ❌ 仅消费产品 |
| 训练分布 ≈ 机器人 wrist-cam | ⚠️ 室内场景 ok | ❌ 消费审美，错配 |
| Metric scale | ❌ (both) | ❌ (both) |
| 可蒸馏到 Orin | ⚠️ 进行中 | ❌ 无路径 |

**建议**：留 VGGT，待 World Labs 出 API 或论文再看。今天切换得不到可测量收益，反丢可复现性。

## 4 · Where it doesn't help (and why we say so explicitly)

- **无公开策略闭环评测**。Marble 没在真实机器人 pipeline 里被测过。没有那个，叫它"机器人 world model"是营销不是工程。
- **无 metric scale 保证**。和 monocular feed-forward 3D 同盲点；无 IMU / stereo 融合就没有机器人集成故事。
- **无物理**。Marble 是*视觉* 3D 模型。接触、摩擦、质量——缺席。需要物理感知渲染时，`foundations/physics/` 里的 PhysGaussian 是对照。
- **闭源权重**。截至 2026-05 没有可像我们解构 VGGT 或 3DGS 那样解构的公开 checkpoint。

### 4.x · Hidden Assumptions

任何"Marble for robots"提案隐含承诺——我们目前都不相信：

- **底层管线在机器人分布上兼容** —— 消费级 3D 场景过审美、且偏离杂乱桌面 / 工业场景。
- **API 或权重发布在路上** —— 截至 2026-05 无公开路线图。
- **消费审美场景对策略训练有信号** —— 可能，但用已有开源系统就能便宜证伪。
- **视觉真实度可迁移到策略收益** —— 同 Cosmos 案例的谬误：外观 ≠ 动力学。
- **产品团队会优先机器人用例而非消费变现** —— 激励错位。

任一不成立，机器人相关性故事便塌缩为"看研究端发表"。

**Interview Tip**：被问 Marble 时，答"消费 3D——具身 AI 范围外，直到 API 或 benchmark 过的研究产物落地。今天用 VGGT / DUSt3R / Depth Anything v2；跟 World Labs 的论文，不是产品页"。把你拽出炒作 lane。

---

## 5 · 2-year outlook

有趣的问题不是"Marble 会不会帮机器人"，而是"World Labs 的产物会不会以研究人员可用的形态发布"。两条合理路径：

1. **API exposure** —— Marble 开 API；研究者按标准 3D / depth 指标做 benchmark，终于能苹果对苹果地比较。
2. **研究端发表** —— World Labs 把底层方法作为带代码的论文发布，与消费产品分离。这正是 NeRF / 3DGS 当年的影响力来源。

**Falsifiable prediction:** 在 2027-06 之前，**Marble（这个消费产品）不会出现在任何 peer-reviewed manipulation 或 navigation 论文的 baseline 列里**。如果某 World Labs *研究产物*出现在那种论文里，会用另一个模型名、带学术 license，与 Marble 品牌分开。

---

## For the reader

- **Manipulation engineer:** 继续用 VGGT / DUSt3R / Depth Anything v2。别等 Marble。
- **追踪这家公司:** 看研究 / publications 页，不是产品页。World Labs 的机器人相关性如果有，会从论文发布来。
- **Researcher:** 开放问题：考虑到分布失配，消费级生成 3D 场景对策略训练是否有*任何*信号。这是一个值得做的 ablation，但先用已开源系统跑会更便宜。

---

## References

- World Labs / Marble announcement — https://www.worldlabs.ai/ (product blog, `UNVERIFIED` on technical claims)
- Background lineage — NeRF (Mildenhall et al. *ECCV 2020*, https://arxiv.org/abs/2003.08934), 3DGS (Kerbl et al. *SIGGRAPH 2023*, https://arxiv.org/abs/2308.04079)
- Comparison anchor — VGGT (Wang et al. *CVPR 2025*, [arXiv link TBD])

## Boundary

本文**刻意窄**。仅覆盖 Marble 的底层 3D 管线在多大程度上可能服务于具身策略。消费 3D 场景生成、创意工具、VR 交付、产品 UX 按项目 PRD 是**显式 out of scope**。Feed-forward 3D 作为一类已在 `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` 解构；跨方法对比归 `crossing/representation-migration/`。

---

*Last opinion update: 2026-05-21.*
