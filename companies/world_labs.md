# World Labs — 李飞飞的 3D 豪赌，从公司视角读

**Status:** v0.1 — opinionated draft。所有营收 / 使用量 / 内部模型说法 `UNVERIFIED`（私人公司，除创始团队过往学术发表外无同行评审披露）。
**TL;DR:** World Labs（2024 由 Fei-Fei Li + Justin Johnson + Christoph Lassner + Ben Mildenhall 创立）是**消费级 3D 场景生成最高调的一笔押注** —— 把 NeRF / Mip-NeRF / 3DGS 这条学术血脉商业化。本手册只从一个窄角度涵盖它：*战略*（数据 + 研究，不是机器人部署），以及底层 3D 流水线 —— 仅限于它将来是否会以 API 形式让机器人工程师调用。产品本身（Marble）超出本手册范围，对应文件在 [`foundations/world-model/marble_decision_view.md`](../foundations/world-model/marble_decision_view.md)。

---

## 1 · 战略命题（一段话版）

World Labs 在 2024 年以十亿美元以上估值融资，前提是**大规模生成式 3D 是继文本与图像之后的下一个基础模型前沿**。创始团队就是这个领域的学术血脉本身 —— NeRF（Mildenhall 2020）、3DGS 系（Lassner 早期工作）、ImageNet 时代规模化打法（Fei-Fei Li）。这笔押注**不是**要造机器人，而是建一个**3D 基础模型**，让创作者、设计师 —— 最终间接地 —— 让具身 AI 团队来付费授权。

形态与 OpenAI / Anthropic 之于文本一致：拥有模型，拥有数据飞轮，卖访问权。机器人接入是下游问题，不是他们要先解的题。

---

## 2 · Marble —— 可见的产品（交叉引用，不重复）

Marble 在 2024 年末以**面向消费者的 3D 场景生成器**上线 —— 提示词 → 可漫游 3D 世界。本手册对 Marble 为什么对机器人而言基本无关、保留哪一小块、它原则上可能在哪里帮到具身策略，完整解剖在：

→ [`foundations/world-model/marble_decision_view.md`](../foundations/world-model/marble_decision_view.md)

短版本：**目标用户是人类创作者，不是机器人策略**，且开放学术血脉（DUSt3R / VGGT / 3DGS）已经用可复现 benchmark 覆盖了同样的原语。Marble 底层流水线封闭，截至 2026-05 没有研究者可基准化的 API 表面 `UNVERIFIED`。

---

## 3 · 在跑的 vs roadmap（2026-05）

| 能力 | 状态 | 对机器人有用吗？ |
|---|---|---|
| Marble — 文本 → 3D 场景生成 | 已上线（消费产品） | ❌ 封闭，没有策略闭环 API |
| 单图 → 3D 场景重建 | 已演示；集成进 Marble | ⚠️ 也许 —— 如果 API 开放 |
| 稀疏视角 → 3D 场景 | 已演示 | ⚠️ 同上 |
| 物理感知场景演化 | 未公开演示 `UNVERIFIED` | 会重要；但没发生 |
| 开放权重 / 可基准化 API | 截至 2026-05 没有 | — |
| 机器人合作 | 没有公开 `UNVERIFIED` | — |

这张表读法：**World Labs 有让自己与机器人相关的能力，但没把方向对准过去**。产品 roadmap 是创作者工具、VR、AR —— 这些表面付费能力更强、长尾风险也比具身部署低。

---

## 4 · 为什么公司战略是「数据 + 研究，不做机器人」

三个理由叠在一起：

**(a) 数据飞轮是消费者形状的。** 生成式 3D 的质量随成对（prompt, scene）数据规模化。取这类数据最便宜的地方是创作者工作流 —— 一个设计师反复在 Marble 上调一个场景就产生排序偏好数据，正是 Midjourney / DALL-E 起飞那套飞轮。机器人产生的是错的形状的数据：动作轨迹、接触事件，稀疏且专有。

**(b) 机器人部署的营收滞后 5 年以上。** 具身 AI 团队今天付不起基础模型的价；消费者创作者付得起。World Labs 选了在模型训练成本峰值期就能变现的表面。

**(c) 团队的专长是图形学 + 感知，不是控制。** 创始团队没有人来自控制 / 硬件 / 机器人背景。要做机器人产品就得新建一整套学科。这个战略避开了那条路。

本手册把这读作**理性且自洽**，而不是错失机会。World Labs 技术真用到机器人那天，会以授权 API 形式到达 —— 不是它自家部署。

---

## 5 · 从具身 AI 这一侧怎么看 World Labs

| 问题 | 诚实答案 |
|---|---|
| 我的 VLA 栈要不要押 World Labs 的技术？ | 不要。继续用开放血脉（VGGT、DUSt3R、3DGS），等 World Labs 开出可基准化 API 再说。 |
| Marble 是「机器人的 world model」吗？ | 不是 —— 它是给人类用的*场景生成器*。参见 `foundations/world-model/marble_decision_view.md` §4。 |
| 团队会发布权重吗？ | `UNVERIFIED` —— 没有公开承诺。对照 OpenAI，可能性低。 |
| 这家公司是否验证了空间 AI 的投资命题？ | 是 —— 3D 生成拿到十亿美元级融资，说明这个领域已过拐点。 |
| 它会威胁开放 3DGS / NeRF 生态吗？ | 边际威胁。学术血脉照样发论文，World Labs 并排存在，不替代。 |
| World Labs 会在 2027 出一个机器人级别的单图深度 API 吗？ | 可能，但没宣布。盯住 `UNVERIFIED` 合作信号。 |

---

## 6 · 两年展望 + 可证伪预测

两条路径在跑：

**路径 A —— API 开放。** World Labs 开出一个面向非消费者定价的 depth / pointmap API。机器人团队在 ScanNet++ / TUM-RGBD 上跑出第一组与 VGGT 的同基准对比。

**路径 B —— 垂直锁定。** World Labs 留在创作者侧。机器人领域继续走开放血脉。World Labs 成为「3D 的 Adobe」，而不是「空间 AI 的 OpenAI」。

本手册的工作假设是**路径 B 持续到 2027**，2028 年前后消费市场饱和时路径 A 才漏出来。

**可证伪预测：** 在 2027-12 之前，不会有任何 World Labs 模型在 ScanNet++ 或其他标准 3D benchmark 上出现同行评审评估。若出现，公司在向研究 API 表面重新定位，机器人相关性问题需要重开。

---

## 7 · 给不同读者的判读

- **机械臂工程师** —— 暂时无关；继续用开放前馈 3D。18 个月后再回看。
- **航拍工程师** —— 完全无关。World Labs 是室内场景形状，不是户外 / 空中。
- **AD 工程师** —— Wayve / NVIDIA Cosmos 才是 AD 相关的 world model 押注。World Labs 不在这条道上。
- **VLA 研究者** —— 真正可迁移的洞察是数据战略（消费者飞轮 > 机器人轨迹，能付得起算力）这一课，即便技术本身到不了你这。
- **投资人 / 战略向** —— World Labs 是*3D 已成为基础模型表面的信号*。它对机器人的下游影响会通过 API 价格压力，在 24-36 个月后到达。

---

## References

- NeRF — Mildenhall et al. *ECCV 2020*. https://arxiv.org/abs/2003.08934
- 3DGS — Kerbl et al. *SIGGRAPH 2023*. https://arxiv.org/abs/2308.04079
- World Labs official site — https://www.worldlabs.ai （仅博客；截至 2026-05 无同行评审 model card）
- Marble product blog — `UNVERIFIED` 本手册未承诺规范 URL
- 配套决策视图：[`foundations/world-model/marble_decision_view.md`](../foundations/world-model/marble_decision_view.md)

## Boundary

本文件是 World Labs 的**公司层读法**（战略、roadmap、为何存在）。产品 / 流水线解剖在 `foundations/world-model/marble_decision_view.md`。与开放前馈 3D 的对比属于 `foundations/feed-forward-3d/`。不要在此重复 Marble 的流水线拆解。

---

## 🤖 Moltbot Updates

<!-- Moltbot appends release / news entries below this line. Format: YYYY-MM-DD — one-line event — source URL. -->
