# 3DSRBench 解构 (3DSRBench: A Comprehensive 3D Spatial Reasoning Benchmark — Dissection)

> **发布时间**: arXiv 2024-12-10 / ICCV 2025
> **论文 / 项目**: 3DSRBench, [arXiv:2412.07825](https://arxiv.org/abs/2412.07825)（Ma, Chen, Zhang, Chou, Chen, de Melo, Yuille — Johns Hopkins University & DEVCOM Army Research Lab）
> **项目页**: [3dsrbench.github.io](https://3dsrbench.github.io/) · [HuggingFace dataset](https://huggingface.co/datasets/ccvl/3DSRBench)
> **核心定位**: 一个**用来证伪"VLM 已经会 3D 推理了"的 benchmark** —— 2,772 条人工标注 QA，逼最强 VLM（GPT-4o / Claude-Sonnet / Gemini-Pro / LLaVA-NeXT）暴露在 50% 上下徘徊的事实。

3DSRBench 是 vlm-spatial-reasoning zone 的"裁判席" —— 它本身不是模型，而是把 SpatialVLM / SpatialBot / 大厂闭源模型放在同一张表上互相打脸的工具。

**Status:** v1 — first draft. 数值引自论文 Table 1 / 项目页公开 leaderboard，`UNVERIFIED` 标记未亲自重跑的具体百分点。
**Zone tier:** `foundations/vlm-spatial-reasoning/` anchor #3 — benchmark 文档，与两篇 model dissection 互补。
**TL;DR:** 3DSRBench 标注 2,772 条 3D 空间推理 QA（2,100 real-image 来自 MS-COCO + 672 synthetic 来自 HSSD 渲染），分 4 大类 12 子类（height / location / orientation / multi-object），引入 CircularEval / FlipEval 两种位置偏置鲁棒指标，并切出 common / uncommon viewpoint 两个 synthetic split 显式测视角泛化。结果残酷：最强模型仅 49.6%（LLaVA-NeXT-8B），uncommon viewpoint 下普跌 13-19 个百分点 `UNVERIFIED`。**Random++ baseline 45.8% —— 多个旗舰模型仅勉强超过随机。**

### X-Ray (non-expert friendly)

(a) SpatialVLM 与 SpatialBot 都自称"会 3D 空间推理"，但用各自 benchmark 报告 —— 数字不可比。(b) 3DSRBench 是第一个把"3D 空间推理"切成 4 类 12 子类、要求 multi-view 视角鲁棒、还用 CircularEval 防答案位置偏置的 benchmark。它在 MS-COCO 真实图像上人工标了 2,100 题，又在 HSSD 多视角合成图上加了 672 题（含 common / uncommon viewpoint 对照）。(c) 对 zone 读者：跑这个 benchmark 是验证你的 VLM 是真的"理解 3D"还是只是"在熟悉视角下记答案"。它把 GPT-4o 打到 45% —— 比随机基线高不了多少。

### 📍 Research Landscape Timeline

```
VQA 2015 ─► CLEVR 2017 (synthetic 3D Q&A) ─► VSR 2022 (relations) ─► 
                                                    │
SpatialVLM 2024 ─► SpatialBench (model-paired)     │
SpatialBot 2024 ─► SpatialBench (model-paired)     │
                                                    ▼
BLINK 2024 (multi-task, depth subset) ──► ★ 3DSRBench ICCV 2025 (4×12, view robustness)
                                                    │
                                                    └─► Spatial-DISE / ViewSpatial-Bench 2026+
```

3DSRBench 占据"3D-aware, real-image, view-robust"的位置：之前的 spatial 评测要么 toy synthetic（CLEVR）、要么只测 2D 关系（VSR）、要么 model-paired 难以横向对比（SpatialBench）。

---

## 1 · Benchmark 总览 (Overview)

### 1.1 组成对比

| 切分 | 图源 | 题数 | 用途 |
|---|---|---|---|
| **3DSRBench-real** | MS-COCO 真实自然图像 | 2,100 | 主榜，衡量 VLM 在野外图像上的 3D 推理 |
| **3DSRBench-synthetic-common** | HSSD 室内场景渲染（常见视角）| 336 | 视角泛化对照基线 |
| **3DSRBench-synthetic-uncommon** | HSSD 渲染（**6D uncommon viewpoint**，如低角度俯视）| 336 | 验证 "common → uncommon" 的退化幅度 |
| **合计** | — | **2,772** | 全部人工标注 |

注意：2,772 是论文标题数；项目页早期版本写 2,762，皆可能在小幅修订之间。

### 1.2 关键设计：12 question types over 4 axes

```
HEIGHT       LOCATION         ORIENTATION         MULTI-OBJECT
─────        ─────────        ────────────        ────────────
- 物体高度    - 物体位置        - 物体朝向          - A vs B 高 / 左 / 近
- 离地高度    - 相对地面位置    - 相对相机朝向       - A 是否能看见 B
- vs 相机     - 相对相机距离    - 头朝向人 / 物      - A 是否在 B 后面
```

每个 cell 是一个 question type，覆盖物体绝对几何（高度 / 朝向）、相对几何（多物体）、相对相机几何（视角）。这 4 × 3 = 12 切口是论文最有用的部分 —— 让你看出 VLM 在 *哪个* 几何维度上失败。

⚡ **Eureka Moment**：**"VLM 会不会 3D 推理"是个错问题。问对的问题是"在哪种 3D 推理上失败、相差多远"。** 3DSRBench 12 子类是回答这问题的工具 —— 没这个分层，所有评测都退化为"50% 上下"的无信息平均。

### 1.3 鲁棒指标：CircularEval & FlipEval

两个工程巧思，防 VLM 用位置偏置作弊：

- **CircularEval**：把同一题的多选选项**循环重排**多次（A→B→C→D, B→C→D→A...），全部答对才算 "1"。防"VLM 偏爱选 A"作弊。
- **FlipEval**：把题目左右镜像翻转 + 答案翻转一致重测。防"VLM 偏爱选 left"作弊。

这两个不引入新数据，仅评测时 4-8× 跑同题。它们是 3DSRBench 相对前序 benchmark 的关键差异——前序 spatial 评测让 GPT-4o 看似"会"，CircularEval 暴露其实是位置偏置。

---

## 2 · Napkin Formula：为何 VLM 输

> 📌 **Napkin Formula**: `VLM 3DSR-real score ≈ Random++ + ~3 percentage points`
> 即：旗舰模型在严格指标下仅比随机基线高几个百分点（论文 Table 1）。

**论文声称结果**（3DSRBench-real，`UNVERIFIED` 具体数字以原表为准）：

| Model | Real Overall | 评注 |
|---|---|---|
| Random++ baseline | 45.8% | 加权随机，已考虑选项分布 |
| **LLaVA-NeXT-8B** | **49.6%** | 开源 SOTA，仅高 random ~4 点 |
| Gemini-Pro | 49.1% | 闭源旗舰，几乎与开源持平 |
| Claude-Sonnet | 46.9% | |
| GPT-4o | 45.3% | **低于** Random++ |

**关键观察**：闭源不胜开源；GPT-4o 在严格指标下**低于**随机基线。这是 zone 内最反直觉的事实 —— 也是该 benchmark 最大贡献。

### 2.x 视角泛化退化

`synthetic-common → synthetic-uncommon` 性能掉幅（论文 Table）：

| Model | common → uncommon 跌幅 |
|---|---|
| LLaVA-NeXT-8B | **−19.1%** |
| Cambrian-1-8B | −17.0% |
| Gemini-Pro | −17.4% |
| GPT-4o | −13.5% |

**直觉**：所有 VLM 都在"训练分布"视角下勉强可用；切换到 6D uncommon viewpoint（低角度俯视、靠墙仰拍等），表现集体下崩。这对**移动机器人 / aerial / AR-VR** 是致命问题 —— 这些 embodiment 的"常态"视角恰好是 VLM 训练分布的"长尾"。

---

## 3 · 走一遍：一个 multi-object 题如何被打分 (Worked Example)

**示例题**（论文风格）：
- 图：客厅，沙发一只猫一只狗
- 问："Which animal is closer to the camera, the cat or the dog?"
- 选项：A) cat  B) dog  C) cannot tell  D) both same distance

**CircularEval** 跑 4 轮：
1. 原序 ABCD → 模型答 A (cat) → 正确
2. 循环 BCDA → 模型答 D (= 原 A = cat) → 正确
3. 循环 CDAB → 模型答 C (= 原 A = cat) → 正确
4. 循环 DABC → 模型答 B (= 原 A = cat) → 正确
- → 全 4 轮答对 → 计 1 分

如果模型在第 2 轮答了 A（= 原 B，dog） → CircularEval 计 0 分 —— **暴露位置偏置**。

**FlipEval**：把图水平镜像 + 选项 cat/dog 顺序保持。如果模型在原图答 cat、镜像图答 dog → 计 0 —— **暴露左右偏置**。

通常 VLM 在松散 acc 下报 65-70%；CircularEval+FlipEval 下掉到 45-50%。**差距即偏置**。

---

## 4 · 工程视角：为什么这个 benchmark 难刷 (Engineering View)

| 攻击向量 | 旧 spatial benchmark | 3DSRBench |
|---|---|---|
| 位置偏置 | acc 直接报 → 偏置不可见 | CircularEval 4× 多算 → 偏置变 0 分 |
| 左右偏置 | 单图 acc | FlipEval 镜像 → 偏置暴露 |
| 视角偏置 | 全用常见角度 | uncommon viewpoint split 显式打分 |
| 答案分布偏 | "最常见答案" 投机 | 平衡分布 + Random++ baseline |
| 标注噪声 | crowdsource 噪声 | 人工标注 + reviewer |

**机器人含义**：CircularEval + uncommon viewpoint 模拟了 **embodied agent 的真实视角分布**（机械臂相机不会一直水平正面）。Benchmark 上 VLM 仅 49% —— 直接读成"现成 VLM 不能作为机器人空间 backbone"。

**部署 cost**：跑全 benchmark `UNVERIFIED` 估 ~11k API call（2,772 题 × 4× CircularEval），单次完整 GPT-4o eval $50-100 量级 `UNVERIFIED`。这是为什么 leaderboard 更新不频繁。

---

## 5 · 数据与评测细节 (Data & Eval Details)

**Real split (2,100 q)**：
- 图：MS-COCO 子集（自然室内 / 户外混合）
- 标注流程：human annotator 选物体 + 标注 3D 属性 + 设计 question + 三人交叉验证
- 实体范围：rigid objects、人、动物、logo / arrow 等抽象 visual concept

**Synthetic splits (336 + 336)**：
- 图源：HSSD（Habitat Synthetic Scenes Dataset）
- 渲染：同一 3D 场景从多个相机姿态渲染
- "Common" 视角：眼平、~1.6m 高、水平角
- "Uncommon" 视角：6D 任意 pose（含俯视、仰视、tilted roll）

**为何要 synthetic？** 因为只有 synthetic 才能保证"同一 3D 场景，仅相机变" —— 这是测视角鲁棒性的唯一干净方式。Real-image 部分不能做这个切片。

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

### 6.1 Benchmark 测出来的 VLM 失败模式

| 失败 | 表现 | 含义 |
|---|---|---|
| 多选项位置偏置 | acc 在 CircularEval 下崩 ~15-20% | VLM 不是"答案推理"，是"位置回归" |
| 左右镜像偏置 | FlipEval 下额外掉 5-8% | 数据集 left/right 分布偏 |
| Uncommon viewpoint | 跌 13-19% | 训练数据视角分布窄 |
| Multi-object 类 | 各模型普遍最差子类 `UNVERIFIED` | "两物体相对几何"=组合泛化 |

### 6.1.x GitHub 实地失败（atlas 联动）

- **GitHub-validated**："GPT-4o 45.3% < Random++ 45.8%"在 sub-axis 粒度被独立用户在 issue 区验证 — 某些 orientation / height 4-choice 子项确实低于 25% baseline，因为模型有**系统性偏好**（永远答最常见类别），比真随机更差；benchmark 仅给 HF dataset + project page、**无训练 repo**，"我 fine-tune 后 65%"类声称无法 fair-verify，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 6.2 Hidden Assumptions

- **MS-COCO 图像是"自然分布"** —— 但 COCO 偏向 photo-quality 室内/户外，与机器人相机的 cluttered 室内 / 户外有 gap
- **人工标注 = ground truth** —— 3D 朝向 / 距离对人类也难，annotator 错误未量化报告
- **CircularEval + FlipEval 抓住所有偏置** —— 仍可能漏 viewpoint-specific 偏置（如"摄像头总在右上角"）
- **HSSD 室内 = "synthetic representative"** —— 不覆盖户外 / aerial / marine viewpoint 分布
- **MCQ 格式 = spatial reasoning 测试** —— 但 MCQ 不需要*生成* metric 答案。VLM 可能选对答案而内部 representation 仍错。**这是 benchmark 本身的天花板**。

### 6.3 与其他 benchmark 对比

| Benchmark | 题数 | 核心 | 视角对照 | 局限 |
|---|---|---|---|---|
| **3DSRBench** | 2,772 | 4×12 类，view robust | ✅ common/uncommon | MCQ 而非 metric |
| BLINK (depth subset) | &lt;500 | 多任务，含 depth point | ❌ | 题量小 |
| VSR (Visual Spatial Reasoning) | ~10k | 2D 关系，二选一 | ❌ | 偏 2D，非 3D |
| CV-Bench | ~2.6k | counting / depth / distance | ❌ | 视角不对照 |
| SpatialBench (SpatialBot 自带) | ~100 图 | depth API 友好 | ❌ | model-paired, 小 |
| CLEVR | ~700k | synthetic toy | ❌ | 完全 toy，无真实 transfer |

**3DSRBench 独占地位**：唯一同时具备 (i) 真实图像题量 ≥2k (ii) 视角鲁棒性切片 (iii) 鲁棒评测指标的 spatial benchmark。这是为什么 ICCV 2025 接收。

**Interview Tip**："3DSRBench 不是新模型，是新裁判。它的关键创新是 CircularEval+FlipEval+uncommon viewpoint split —— 把以前 'GPT-4o 70%' 这种虚高数字打回 45%（低于 Random++）。要论证你的 VLM 真的会 3D 推理，跑这个；要说服别人 VLM-VLA 还远，引这个 benchmark 的 LLaVA-NeXT 49.6% 数字。"

---

## 7 · 该 benchmark 对 zone 内 model 论文的"裁判效应"

**对 SpatialVLM**：SpatialVLM 论文的 spatial benchmark 是自带 + 部分 public（VSR 等）。在 3DSRBench 上 SpatialVLM `UNVERIFIED 尚未被官方榜列入`，但其 PaLI-X backbone 同量级闭源模型表现已知 ~45-50%。SpatialVLM 的"涌现 spatial reasoning"叙事在 CircularEval 下能保留多少，仍待第三方测。

**对 SpatialBot**：SpatialBot 强项是 metric depth API；3DSRBench 是 MCQ，**不直接奖励 metric 精度**。预期 SpatialBot 在 height / location / multi-object 子类有边际优势（depth API 缓解），但在 orientation 子类无优势（depth 不解 orientation 问题）。

**对闭源旗舰**：GPT-4o / Claude-Sonnet / Gemini-Pro 在 Random++ 上下徘徊 —— 这是 zone 内"现成 VLM 不能做机器人 spatial backbone" 论点的**最强独立证据**。

---

## 8 · 视角泛化的 robotics 含义 (Robotics Implication)

uncommon viewpoint 跌 13-19% 对各 embodiment 含义不同：

| Embodiment | 典型视角分布 | 3DSRBench uncommon 相关度 |
|---|---|---|
| Manipulation（桌面臂）| 头顶 + 腕载 | 中 —— 腕载视角偏 uncommon |
| Humanoid / Ground mobile | 眼平 ~1.6m | **低** —— 训练分布友好 |
| Driving | 前向 ~1.2m | **低** —— common viewpoint |
| **Aerial / drone** ★ | 高空 + 大 pitch | **高** —— 几乎全 uncommon |
| Marine / underwater | 任意 6D | **极高** |

对 aerial 维护者锚定方向（🌬️）：3DSRBench uncommon split 是 zone 内**唯一相关**的 VLM 评测。机器人 deployment 越离开"人类视角"，VLM 越退化 —— 这是 SpatialVLM / SpatialBot 都未解决的硬限制。

---

## 9 · Falsifiable prediction

到 2026-12，将出现至少一个开源 VLM 在 3DSRBench-real 上突破 60%（CircularEval+FlipEval 严格指标），同时在 uncommon viewpoint split 上的退化幅度 ≤8 个百分点。**如果到 2026-12 顶榜仍在 50% 以下，且 uncommon 退化仍 >15%，本预测被证伪 —— 意味着 VLM spatial reasoning 范式可能需要根本性架构革新（非数据 / 输入 / SFT 可解）。**

---

## References

- 3DSRBench — Ma et al. ICCV 2025. [arXiv:2412.07825](https://arxiv.org/abs/2412.07825)
- Project page — [3dsrbench.github.io](https://3dsrbench.github.io/)
- Dataset — [ccvl/3DSRBench on HuggingFace](https://huggingface.co/datasets/ccvl/3DSRBench)
- ICCV 2025 paper — [openaccess.thecvf.com/content/ICCV2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Ma_3DSRBench_A_Comprehensive_3D_Spatial_Reasoning_Benchmark_ICCV_2025_paper.pdf)
- HSSD 数据源 — Khanna et al. 2023
- 相关 benchmark：BLINK (Fu et al. 2024), VSR (Liu et al. 2022), CV-Bench (Tong et al. 2024)
- 同期 spatial 评测：Spatial-DISE [arXiv:2510.13394](https://arxiv.org/html/2510.13394) · ViewSpatial-Bench [arXiv:2505.21500](https://arxiv.org/pdf/2505.21500)

## Cross-references

- Zone 同侪 model dissection → [`spatialvlm_dissection.md`](./spatialvlm_dissection.md) · [`spatialbot_dissection.md`](./spatialbot_dissection.md)
- 一般 VLM benchmark 体系 → [`../../benchmarks/reasoning/`](../../benchmarks/reasoning/)（TBD）
- 视角鲁棒性也是 3D-aware backbone 的卖点 → [`../feed-forward-3d/`](../feed-forward-3d/overview.md)
- VLA 端的 view 泛化 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)（cross-embodiment view transfer）
- Aerial 视角分布问题 → [`../../embodiments/aerial/`](../../embodiments/aerial/overview.md)

## Boundary

本文专门解构 3DSRBench 作为评测工具。它**不**覆盖：被评测的具体 model 内部架构（→ 同 zone model dissection）；通用 VLM benchmark 综述（→ `benchmarks/reasoning/`）；3D reconstruction benchmark（→ `benchmarks/geometry/`）；具身 VLA benchmark（→ `benchmarks/manipulation/` 或 VLA-Handbook）；视角鲁棒性的 backbone 解（→ `foundations/feed-forward-3d/`）。

---

[← Back to vlm-spatial-reasoning README](./overview.md)
