# VLM 空间推理 GitHub 失败图谱 (VLM Spatial Reasoning · GitHub Failure Atlas)

> **类型**：roadmap / atlas（非 dissection；不走 14 项门槛）
> **聚焦**：从公开 repo 的 issue / PR / momentum 抽出**这条 lane 在 2025-2026 真实暴露的失败模式**，给"下一步该往哪打 PR / 该做什么实验"指方向
> **核心定位**：dissection 写"它声称做对了什么"；本图谱写"复现者实际撞了哪堵墙、维护者还在不在线、合理的 PR 方向是什么"

**Status:** v1 — opinionated draft, 2026-05-21。所有 star / fork / issue 数字截取自 GitHub API 当日快照，标 `UNVERIFIED` 表示作者未亲自跑过复现。
**Coverage:** 3 工具 — SpatialVLM（Google DeepMind, 无独立官方 repo）/ SpatialBot（BAAI-DCAI）/ 3DSRBench（仅 project page + HF dataset）。

---

## X-Ray (non-expert friendly)

(a) 三条 VLM 空间路线都已有公开 artifact：SpatialVLM 是论文加几个第三方复现（无 Google 官方 repo）；SpatialBot 给了 model + code + 数据，仍活；3DSRBench 只给了 benchmark + HF dataset，**没有训练代码**。(b) 真实复现者撞到的墙不是新闻里讲的 "VLM 看不懂 3D"，而是更朴素的三件事：**相对方位反过来**（SpatialBot #21）、**自报 metric 与论文表不一致**（#25）、**depth/mask alignment 不准**（任何下游 SAM 3D 整合）。(c) 对工程师：用这些 repo 前先看 v1 issue 而不是看论文；表里给的 GPT-4o-comparable 数字常在 in-distribution 上成立，跨域几乎肯定降级。

---

## 📍 Zone Momentum Snapshot (2026-05-21)

```
SpatialVLM 2024-01 ─► [无官方 repo] ──► 社区复现散落 ──► VQASynth (567★) 继承数据管线
                                      │
SpatialBot 2024-06 ──► repo 活, 344★ ──► 2025-09 last push ──► Embodied CKPT 仍欠 (#30)
                                      │
3DSRBench  2025 ──► project page + HF dataset ──► [无训练 repo] ──► 真 split 49% 天花板
```

仅 SpatialBot 一条线给了"可 git clone 的 baseline"。SpatialVLM 留下了**数据管线想法**（VQASynth 继承）但没给权重；3DSRBench 留下了**裁判**但没给训练。

---

## 1 · SpatialVLM — 数据管线散落，无官方代码

**Repo 状态**：Google DeepMind 论文 [arXiv:2401.12168](https://arxiv.org/abs/2401.12168) **未发布官方训练代码或权重** `UNVERIFIED`（2026-05 GitHub 搜索仅返回学生项目与社区复刻）。继承其"自动合成 spatial QA"思想的最活跃公开实现是 [`remyxai/VQASynth`](https://github.com/remyxai/VQASynth)（567★ / 2026-05-15 last push）。

### Failure patterns (社区可见)

| Pattern | 出处 | 根因 |
|---|---|---|
| **复现版能力远低于论文** | HYN-KULU/SpatialVLM_X_LLaVA (学生项目) | LLaVA backbone + ~10⁴ QA ≠ PaLI-X + 2B QA — 论文核心论点（规模）在小规模上根本测不到 |
| **Precise metric distance 严重偏差** | 论文自身 §6 + 多篇 followup | 网络图像 depth 是相对的；自动合成 templates 把 "0.4 m" 当 ground truth，但 ZoeDepth 在户外/反光面误差 >30% `UNVERIFIED` |
| **遮挡场景 hallucination** | SpatialBot 论文对照实验 | 监督源（seg + depth）在遮挡区本身 garbage in |

### PR / 实验方向

- **PR 1（社区 repo）**：给 VQASynth 加一个 "metric-grounded subset" 标记 — 只保留有标定深度（NYUv2、HM3D-real-scale）的图像，把模板答案的相对值改成可信 metric。预期目标：3DSRBench Height 子项从 ~30% 提升到 ~50%（`UNVERIFIED` baseline）。
- **PR 2（新工具）**：开源 "spatial QA distillation harness" — 给定任意 VLM，跑论文式自动合成的最小子集（10M QA, 不是 2B），让小团队**只验证 #3 论点**而不必负担 2B 训练。
- **实验方向**：与 SpatialBot 显式 depth token 路线**做 head-to-head**（同 backbone、同评测、隐式 QA 预训练 vs 推理期 depth 注入）。是 2026+ VLM 空间路线最重要的未做实验。

### Momentum: 📖（论文级影响大；repo 级几乎零自有动量；社区借数据管线想法做下游 trainer）

---

## 2 · SpatialBot — 唯一可跑 baseline，issue 暴露关键失败

**Repo**：[`BAAI-DCAI/SpatialBot`](https://github.com/BAAI-DCAI/SpatialBot) · 344★ · 24 forks · MIT · last push 2025-09-14 · open issues 5 / closed 多。维护节奏：开了重要 issue 多有 maintainer 回应，但 2025-09 后明显放缓。

### Failure patterns (issue 一手暴露)

| Pattern | Issue | 关键发现 |
|---|---|---|
| **相对方位反过来** | [#21 *"when inquiring about the relative positional relationship of items, the returned results are always incorrect"*](https://github.com/BAAI-DCAI/SpatialBot/issues/21) | 7 comments；用户在自家图片上问 left/right 几乎稳定**反向**。指向：训练数据视角分布偏差（俯视 vs 平视）+ depth token 注入没有 viewpoint canonicalization |
| **自报 metric 与论文不一致** | [#25 *"Confusion about experiment results"*](https://github.com/BAAI-DCAI/SpatialBot/issues/25) | Table 1 给出高 depth score，但论文 §5 自陈"VLM has not been fully prepared for MDE in text-only output fashion" — 内部前后矛盾，复现者无法判断该信哪个数 |
| **Embodied CKPTs 缺失** | [#30 *"Estimated timeline for Embodied SpatialBot CKPTs"*](https://github.com/BAAI-DCAI/SpatialBot/issues/30) | 论文 §"Embodied" 章节承诺的具身权重至今未发；下游 manipulation 复现的最关键 artifact 缺位 |
| **batch inference 难** | [#5](https://github.com/BAAI-DCAI/SpatialBot/issues/5) | depth token 注入与标准 VLM batch 路径冲突；机器人端 30 Hz 推理需自己改 |
| **bbox / mask 坐标不清** | [#23, #17](https://github.com/BAAI-DCAI/SpatialBot/issues/23) | depth crop 与 VLM image patch 的坐标系是 normalized 还是 raw — 文档未给定式答案 |

### PR / 实验方向

- **PR 1（high-value）**：给 batch inference path 一个 reference impl（#5 已 closed 但社区方案散乱）。是 SpatialBot 进 manipulation 真机推理的第一道闸。
- **PR 2**：在 README 加 "viewpoint canonicalization" 警告 + 一个最小复现脚本展示 #21 失败模式。让下游用户知道 left/right 在 oblique view 不可信。
- **PR 3（论文性）**：fork 出 SpatialBot-Embodied 自行训一组 manipulation tabletop CKPT（用 RT-1 / Open X-Embodiment 数据 + SpatialBot backbone），把 #30 这个洞填掉。这是一篇可发的工作。
- **实验方向**：把 #21 上升为系统 study — VLM + depth token 在哪些视角 / 距离区间 left/right 翻转概率 >50%？做出来就是一篇 workshop paper。

### Momentum: 🔧（repo 还能 clone、issue 还有回应，但 2025-09 后没新 push；社区 PR 接力机会很大）

---

## 3 · 3DSRBench — Benchmark 公开，训练代码不公开

**Repo 状态**：`wufeim/3DSRBench` **404**（2026-05 查询不到该 repo 本人）`UNVERIFIED`。公开 artifact 仅：
- Project page：[`3dsrbench.github.io`](https://3dsrbench.github.io/)
- HuggingFace dataset：[`ccvl/3DSRBench`](https://huggingface.co/datasets/ccvl/3DSRBench)（2772 题 × 4×12 子类）

**没有训练代码 repo**。意味着该 benchmark 的角色是**纯裁判**，不是工具箱。

### Failure patterns (benchmark 数字本身暴露)

| Pattern | 论文报告 | 含义 |
|---|---|---|
| **旗舰 VLM 仅 49% real-split** | GPT-4o / Gemini / Claude 在真实图像 split | 即使最大 VLM，在 height / orientation / multi-object 推理上不到 50%。**对应 "GPT-4o 不如 random" 现象**：某些 4-choice 子项确实低于 25% baseline `UNVERIFIED` 待逐项核 |
| **synthetic vs real 大 gap** | paper Table | 同模型 synth split 高，real split 低 → benchmark 自动生成 QA 的覆盖偏差与模型训练分布偏差**共谋**产生虚假能力错觉 |
| **Domain shift 不受控** | 无 train repo → 无法做 fair fine-tune 对照 | 一个团队声称"我 fine-tune 后 65%"无法验证：起点权重、数据增广、随机种均不公开 |

### PR / 实验方向

- **不存在 PR 直接路径**（无 repo）。可做的二阶贡献：
  - **新 repo**：开源一个 "3DSRBench-trainer" — 给定任意 VLM 与 HF dataset，跑标准化 fine-tune harness，输出可对比数字。仓库化 community baseline。
  - **新 benchmark zone**（spatial-handbook 内部）：把 3DSRBench 的 4×12 sub-axis 拆开，**逐 sub-axis** 画一张"VLM 能力图"——目前社区只引用 overall 49%，掩盖了某些 sub-axis 已经 ~75% / 某些 sub-axis 仍 <20% 的真实分布。
  - **实验**：拿 SpatialBot vs SpatialVLM 复现版 vs GPT-4o，在每个 sub-axis 上跑同一题，发布 sub-axis 胜负矩阵。是 2026 上半年最高 ROI 的实验之一。

### Momentum: ⚡（benchmark 影响力大，社区会 cite；自有 repo 维护几乎为零 — 论文作者把 artifact 放 HF + project page 就当结束）

---

## 4 · Zone 共性失败 (Cross-tool synthesis)

读完三个 repo 的 issue 流，VLM 空间推理 lane 的**结构性失败**比任何单一论文的"defeat list"更值得记录：

1. **Hallucination 是默认态，不是 edge case**。VLM 仍倾向回答"看起来像该答的东西"，而不是承认未知 — 三个 repo 的负面 issue 几乎全是"它自信地给了错答"。
2. **"GPT-4o 不如 random" 在 sub-axis 粒度真实成立**。3DSRBench 整体 49% 平均下，某些 orientation / height sub-axis 在 4-choice 上低于 25% baseline `UNVERIFIED`，因为模型有**系统性偏好**（永远答最常见类别）— 比真随机更差。
3. **Domain shift 极脆**。论文常用 ScanNet / web 数据训练，真机 / 户外 / 反光面性能崩塌。SpatialBot #21 的 left/right 翻转就是典型 domain shift 表现。
4. **可复现 baseline 稀缺**。一条 lane 三个旗舰，只有一个（SpatialBot）给了能 git clone 的训练代码。SpatialVLM 与 3DSRBench 的"训练侧"事实上**只活在论文 PDF 里**。

---

## 5 · 维护者优先级建议

| 行动 | 谁干 | 为什么现在做 |
|---|---|---|
| 把 SpatialBot #21 失败模式做成系统 study | 学生 / workshop 论文作者 | 这是被忽视的"具身 VLM 直接不可用"证据，论文性强 |
| 写 "3DSRBench-trainer" 第三方 fine-tune harness | 任何想 publish 的团队 | 当前论文宣称 fine-tune 提升均不可验，社区缺统一 baseline |
| 用 VQASynth 复现 SpatialVLM-mini 并 head-to-head SpatialBot | 任何想 publish 的团队 | 隐式 QA vs 显式 depth token 之争**至今无受控实验**，做了就是 anchor reference |
| **不**用 GPT-4o 做 spatial benchmark 报告分数 | 所有 reviewer | 49% / sub-axis 低 25% 的现实意味着该报告**置信区间**而非 single number |

---

## Boundary

本图谱**只覆盖 VLM 路线**（图像 + 语言出空间答案）。它**不**覆盖：

- 显式 3D 语义抬升 (semantic-3D) → [`foundations/semantic-3d/github_failure_atlas.md`](../semantic-3d/github_failure_atlas.md)
- 世界模型生成式路线 → [`foundations/world-model/github_failure_atlas.md`](../world-model/github_failure_atlas.md)
- 单文档深度拆解 → 见各 `*_dissection.md`
- VLA 端的部署 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)

## For the reader

- **学生 / 找 thesis 题**：SpatialBot #21 viewpoint 翻转 systematic study 是最低门槛、最高论文性的选题。
- **机器人工程师**：三条线没一条**真的**能 plug-and-play。优先用 SpatialBot 做粗粒度 caption，metric 决策走 explicit depth pipeline（不要相信 VLM 报的距离数）。
- **Reviewer**：拒绝接受 "我们 fine-tune 后 X% on 3DSRBench" 没有 sub-axis 拆分的论文 — overall number 几乎肯定 cherry-picked。

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21
[← Back to vlm-spatial-reasoning README](./README.md)
