# AGENTS.md

本文件面向在 Spatial-Intelligence-Handbook 仓库中工作的自动化 / AI agent，说明写作与维护规范。姊妹仓库 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 的协议为基准，本文档列出**保留 / 收紧 / 新增**三类规则。

## 目标
- 维护结构化、可检索、**跨 embodiment 可对比**的空间智能知识库
- 严守 `crossing/` 是本仓 USP — 任何会被独立 embodiment 综述写出的内容，都不该独占在某一 `embodiments/<x>/` 下
- 工程细节与 sensor 物理优先于综述堆砌（学界综述写不出 SWaP-C 工程账）

---

## 仓库快速导航

```
foundations/      # 跨 embodiment 共享底层（3DGS / VGGT / depth / semantic 3D / sensor-physics ★）
embodiments/      # 各 embodiment 应用层（manipulation / humanoid / ground / driving / aerial ★ / marine）
crossing/         # 跨 embodiment 合流 ★★ USP（scale / sensor / SLAM-VIO / representation / failures）
deployment/       # 工程实战（hardware-selection / sync / calibration / compute / failure-modes）
benchmarks/       # geometry / manipulation / driving / aerial / marine / reasoning
bridge-to-vla/    # 与 VLA-Handbook 接口（3D-aware VLA、feature-cloud→action、neural-map-memory）
companies/        # 产业地图
reports/          # weekly + biweekly（Pulsar pipeline 输出）
cheat-sheet/      # timeline + representation-comparison + sensor-budget-matrix
docs/             # 仓库元文档（含 pulsar-integration.md）
```

★ = 维护者深度锚点（写得比其他 embodiment / 主题深 1.5–2×）

---

## Pulsar 写入协议（继承自 VLA-Handbook，路径与权限矩阵已重定向）

> **核心原则不变**：自动 agent 默认只做"追加行 / 创建新文件"。仅在权限矩阵明确允许时才可对自动生成文件做同日 upsert（重跑修复）；**永远不修改、不删除人工内容**。

### 写入权限矩阵

| 文件 / 目录 | 允许操作 | 禁止操作 |
|---|---|---|
| `foundations/*/README.md` · `embodiments/*/README.md` · `crossing/*/README.md` | 追加表格行（条件触发，见下） | 修改既有行、改表头、改子目录结构 |
| `foundations/<lane>/{paper_or_topic}_dissection.md` | 创建新文件 | 修改已存在的文件 |
| `embodiments/<emb>/<axis>/{topic}_dissection.md` | 创建新文件 | 修改已存在的文件 |
| `crossing/<lane>/{topic}.md` | 创建新文件 ★ 高门槛见 §「Crossing 写入门槛」 | 修改已存在的文件 |
| `reports/weekly/{YYYY-MM-DD}.md` | 创建新文件；同日重跑允许覆盖（仅限自动生成） | 修改人工撰写报告、改报告结构 |
| `reports/biweekly/{YYYY-MM-DD}.md` | 同上 | 同上 |
| `reports/{weekly,biweekly}/README.md` | 追加索引行；同日 upsert | 修改其他日期行、改文件结构 |
| `CHANGELOG.md` | 顶部追加条目 | 修改既有条目 |
| `companies/{vendor}.md` | 仅在文末 `## 🤖 Moltbot Updates` 区追加 | 修改既有正文、改结构 |
| `cheat-sheet/timeline.md` | 追加行（按时间倒序最新一行） | 修改既有行 |
| `cheat-sheet/sensor-budget-matrix.md` | **禁止自动追加** — 该文件需要人工 SWaP-C 核算 | — |
| `docs/*.md` · `AGENTS.md` · `CONTRIBUTING.md` · `LICENSE` · `README.md` | **❌ 不可触碰** | — |
| **其他所有文件** | **❌ 默认不可触碰** | — |

### Crossing 写入门槛（高严格度）

`crossing/` 是本仓的核心 USP。自动写入 `crossing/<lane>/<topic>.md` 必须同时满足：

1. **跨 ≥3 embodiment** — 内容明确比较 ≥3 个 embodiment 上的同一问题（不只 manipulation vs driving）
2. **每 embodiment 都附论文 / 一手来源** — 不允许"manipulation 部分跑通了"这种无来源叙述
3. **工程数字门槛** — 至少 1 个 cell 含具体 SWaP-C / 延迟 / 范围数字（哪怕标 `UNVERIFIED`）
4. **boundary 清晰** — 文末必须有「Boundary」段，指明 per-method 拆解去 `foundations/`、per-embodiment 实战去 `embodiments/`

不满足以上任意一条，**跳过自动写入，推送告警**让维护者补足。

### 条件触发：sensor 物理 / 硬件文档同步

`foundations/sensor-physics/*.md` 和 `deployment/hardware-selection/*.md` 不接受自动追加。这些文档需要人工核对数据手册数字，Moltbot 仅允许在文末 `## 🤖 Moltbot Updates` 段以"日期 + 一句话事件 + 一手来源 URL"格式追加发布动态。

### Commit Message 规范

emoji 前缀，便于 `git log` 区分人工与自动：

| 来源任务 | 格式 | 示例 |
|---|---|---|
| 每日论文 | `📄 daily papers: {日期} (+N papers)` | `📄 daily papers: 2026-05-21 (+4 papers)` |
| SOTA 追踪 | `📈 benchmark: {model} on {benchmark}` | `📈 benchmark: VGGT on ScanNet++` |
| Release 追踪 | `🔧 release: {source} — {event}` | `🔧 release: NVIDIA Cosmos — Cosmos-1.1 released` |
| 周报 | `📊 weekly: {起} → {止}` | `📊 weekly: 2026-05-15 → 2026-05-21` |
| 双周报 | `📊 biweekly: {起} → {止}` | `📊 biweekly: 2026-05-08 → 2026-05-21` |
| 代码分析 | `📝 code analysis: {项目}` | `📝 code analysis: VGGT-distilled` |
| 索引更新 | `📋 update index: {文件}` | `📋 update index: reports/weekly/README.md` |
| Cross-embodiment 综合 | `🔭 crossing: {topic}` | `🔭 crossing: depth-foundation-across-scales` |

人工提交不使用以上前缀。

### 失败处理

- GitHub API 非 2xx：不重试、记录、不影响主任务
- 409 conflict：放弃本次写入、推送告警
- 401/403：推送告警「GitHub Token 可能已过期」
- 格式异常（表格列数不匹配）：跳过、推送告警

---

## 标注系统

继承 VLA-Handbook 三级 + 方向标记。**新增 sensor / wedge 标记**：

### 重要性标注

| 标记 | 含义 | 入选条件 |
|---|---|---|
| ⚡ | 战略级 | 知名团队 + 明显方法论创新 / benchmark SOTA / 跨 embodiment 范式转移 |
| 🔧 | 可操作 | 有代码 / 数据 / 协议可复现 |
| 📖 | 值得了解 | 有参考价值但不需立即行动 |
| ❌ | 不收录 | 学术堆砌 / 与本仓边界无关 / 无 spatial 角度 |

### Spatial 专用方向标记

| 标记 | 含义 |
|---|---|
| 🛰️ | 跨 embodiment 论文（在 ≥2 embodiment 上做实验或显式讨论跨 embodiment 迁移）— `crossing/` 候选 |
| 🌬️ | 维护者锚定方向（drone / aerial），同 VLA 的 🎯 |
| `[3DGS]` `[VGGT]` `[VIO]` `[Sensor]` `[BEV]` `[WorldModel]` | team 方向标签 |
| `📡 sensor-physics` | sensor 物理 / 硬件类内容（hardware-selection 候选）|

🛰️ 与 ⚡/🔧/📖 组合使用，例如 `🛰️🔧 [VGGT] vggt_vs_drone_vio dissection`。

### 内容来源标注

| 标记 | 含义 |
|---|---|
| ⚙️ 本文由 Moltbot 自动生成 \| {日期} | 纯自动生成 |
| ⚙️ 初稿由 Moltbot 自动生成 \| {日期} \| 经人工编辑 | 自动 + 人工修订 |
| ✍️ | 人工撰写（Moltbot 不触碰） |

---

## 内容与格式规范

- **语言**：中英混排。foundations / crossing 优先英文（学术圈通用）；embodiments / deployment 偏中文（实战导向）；wedge / 旗舰文档 v1+ 中英都可，**保持单文档语言一致**。中文 = **简体中文**，不接受繁体（代码 / 模型名 / 公司名 / arXiv ID / 一手 URL 保留英文原样）
- **文件名**：`snake_case.md`
- **公式**：theory 类文档**禁用 LaTeX**（GitHub 渲染不稳定）— 用代码块或 Unicode 纯文本
- **引用**：必须给出来源链接（论文优先 arXiv ID / DOI；代码优先 GitHub / HuggingFace；数据手册可标 `UNVERIFIED, no DOI`）
- **`UNVERIFIED` 标记纪律**：任何 agent 未亲自验证的具体数字（延迟、QE、cost、weight），必须显式标 `` `UNVERIFIED` ``。宁可不写也不写错 — 编造数字是禁止行为

---

## Dissection 写作模板（foundations / embodiments / crossing / bridge-to-vla 深度文档通用）

> 对齐 VLA-Handbook `theory/pi0_5_dissection.md` 范式。目标：把一篇文章写成 **"可面试复述、可工程落地、可快速定位"** 的结构化笔记，不是流水摘要。Spatial 这边的旗舰参考是 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`。

### 1) 开头固定结构（必须）

```
# 中文标题 (English Title)

> **发布时间**：YYYY-MM-DD（或论文年份 / 版本）
> **论文 / 模型 / 项目名**：原始拼写保留英文
> **核心定位**：一句话回答"它解决什么痛点 / 比谁强什么"

1-2 句导语：先写痛点与结论（避免铺垫太长）。
```

紧接导语，**X-Ray 开场**（必须，2-3 句，非专家友好）— 回答：
1. 这篇 / 这个工具解决什么问题？
2. 发现了什么 / 提出了什么？
3. 对 spatial / 具身 AI 研究者意味着什么？
标准：任何聪明的非专家读完能复述核心。

### 2) 推荐章节骨架（按需删减，保持顺序与命名风格）

**📍 研究全景时间线**（X-Ray，放在 §1 之前）：用 ASCII 时间轴标出本文在研究演进中的位置，标注关键节点与本文局限。

```
## 1 · 核心架构 / 方法总览 (Overview / Architecture)
### 1.1 系统对比概览 (System Component Comparison) — 表格：模块 / 输入输出 / 频率 / 训练-推理差异
### 1.2 关键机制 (Key Mechanism) — 要点解释"为什么这样设计"；明确标 ⚡ Eureka Moment：THE 关键洞见一句话
### 1.3 信息流 / 架构图 (Flow / Diagram) — ASCII 图 / 流程图代码块

## 2 · 数学核心：X 如何实现 Y (Math Core)
- 📌 **Napkin Formula** (X-Ray)：展开前先用一行公式 / 直觉句子捕捉本质
- 目标 → 公式 → 变量说明（列表 / 小表格） → 直觉
- 符号多时加 `> 符号与 X 论文 / 相关文档保持一致：...`

## 3 · 带数字走一遍：玩具例子 (Worked Example)
- 用 2D / 低维例子把损失、推理 / 采样或更新过程走一遍

## 4 · 工程视角：快慢路径 / 训练-推理折中 (Engineering View)
- 吞吐 / 延迟 / 步数 / 抖动 / 量化误差 / 内存 trade-off
- 把公式落到控制频率、模块边界、部署约束

## 5 · 数据与评测 (Data & Eval)
- 数据组成 / 配比 / 标注类型 / 评测任务设置；避免只给结论不讲条件

## 6 · 能力与失败模式 (Capabilities & Failure Modes)
- "能做什么 / 不能做什么"讲具体（场景 + 原因）
- **必须有子节**：隐含假设 (Hidden Assumptions) — 哪些假设不成立时方法就破

## 7 · 与相关工作对比 (Comparison)
- 表格对比同系列 / 基线：关注点 / 架构 / 训练方式 / 适用场景
- 结尾放 **1 条面试 Tip**：一句话告诉读者被问到时怎么答
```

**文章末尾统一**：
```
---
[← Back to <module> README](./README.md)
```

### 3) 表达与排版习惯（建议遵守）

- **表格优先**：遇到"对比 / 模块职责 / 优缺点 / 超参"先用表格
- **分层标题**：用 `##/###` 组织，避免大段无小标题正文
- **术语一致**：同一概念中英文 / 缩写文内保持一致，首次出现给全称
- **避免重复**：导语 / X-Ray 写过的结论，正文不要同句式复述；正文要新增信息（机制 / 变量 / 边界 / 数字 / 失败模式）
- **引用就近但不过载**：关键结论附近放来源链接；同节反复引用同一来源可在节末用 `来源：...` 集中列出
- **不确定就标注**：`TODO / 待证 / UNVERIFIED / 待补 citation` 明示，不编造指标

### 4) 最小质量门槛（dissection 输出检查清单）

- [ ] 开头有元信息块（发布时间 / 定位 / 一句话 takeaway）
- [ ] **X-Ray 开场**（2-3 句，非专家读完能复述核心）
- [ ] **研究全景时间线**（ASCII，标出本文在演进中的位置）
- [ ] 至少 1 张架构 / 信息流图（ASCII 也算）
- [ ] 至少 1 个"系统对比 / 组件对比"表格
- [ ] **§1.2 明确标注 ⚡ Eureka Moment**（一句话）
- [ ] **§2 有 Napkin Formula**（一行抓住本质）
- [ ] "数学核心"包含：目标 → 公式 → 变量解释 → 直觉
- [ ] 至少 1 个玩具例子 / 具体数值推导（可很小）
- [ ] 工程视角（延迟 / 步数 / 抖动 / 部署约束）
- [ ] **§6 有隐含假设子节** (Hidden Assumptions)
- [ ] 与基线 / 同系列对比 + **1 条面试 Tip**
- [ ] 文末有返回索引链接 + 关键引用链接
- [ ] Status 行声明版本 + UNVERIFIED 政策

### 5) Wedge / Crossing 文档额外要求

`crossing/` 与旗舰 wedge（W1 / W2 标记）在上面 14 项之上**额外要求**：

- [ ] **跨 ≥3 embodiment** 对比 — 不只 manipulation vs driving
- [ ] **至少 1 个 SWaP-C / 延迟 / 范围数字**（UNVERIFIED 也算）
- [ ] **falsifiable 2-year prediction** — 哪个日期、哪个具体事件可证伪本文判断
- [ ] **`## Boundary` 段** — 指明 per-method 拆解去 `foundations/`、per-embodiment 实战去 `embodiments/`
- [ ] **`## For the reader` per-persona 收尾** — manipulation / aerial / AD / marine engineer 分别一句

### 6) code-notes 轻量模板（半自动代码级分析速记）

未来 `embodiments/<x>/code-notes/` 或 `foundations/*/code-notes/` 收纳代码级速记，深度低于主目录 dissection：

```
# {项目名} — 代码级分析

元信息：repo URL · 对应论文 · 团队 · 环境需求 · 复现难度 🟢🟡🔴

## 架构概览
一段话 + 可选 ASCII 图

## 论文未提及的工程细节
逐条列出（这是最核心的部分）

## 与已知方法的对比
可选，如有已分析的相关项目

## 启发与可借鉴之处
1-3 句

[← Back to Code Notes Index](./README.md) · [← Back to <module>](../README.md)
```

**与主目录 dissection 的区别**：

- **不要求**：数学推导、玩具例子、面试 Tip、X-Ray、Napkin Formula、Eureka Moment
- **必须有**：repo 链接、工程细节、复现难度判断
- 如某 code-note 值得升级为完整 dissection，移入主目录并补齐 14 项质量门槛

### 7) 旧 wedge 版本回填政策

2026-05-21 之前落地的 v1 wedge / dissection 可能未完全满足上述 14 项门槛（特别是 X-Ray、研究全景时间线、Eureka Moment、Napkin Formula、Hidden Assumptions、面试 Tip）。

- v1 → v1.1 回填：人工编辑时**应当**补齐缺失项目
- Moltbot 不允许自动改写既有 v1 内容（按权限矩阵）— 只能在 commit message 提示"v1 不全门槛 X，建议补"
- 新 dissection（v1 首版）**必须**满足全部 14 项

### 8) 旗舰参考

写新 dissection 前**必读**：

- `crossing/slam-vio-migration/vggt_vs_drone_vio.md` — Spatial 这边的旗舰范式（跨 embodiment + falsifiable prediction）
- `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` — 单一工具 dissection 模板
- VLA-Handbook 上游 `theory/pi0_5_dissection.md` — 教科书级模板（本仓 dissection 模板的来源）

对照参考能直接复用结构而不每次造轮子。

---

## 跨 embodiment 写作规范（`crossing/` 专用）

`crossing/<lane>/` 的每篇文档**必须**：

1. 标题以问题或对比形式表达（"Can VGGT Replace Drone VIO?" 优于 "VGGT 与 VIO 对比"）
2. 至少 1 张 ≥3 列的 embodiment 对比矩阵
3. 明确说出"哪个 embodiment 答案不同 + 为什么"，不允许"X 在所有 embodiment 上有用"这种空洞结论
4. 每个 embodiment 都附引用（不能凭印象写）
5. 至少 1 段 contrasting case（marine / AR-VR 等极端 case 拿来反衬）

---

## Bridge-to-VLA 写作规范

`bridge-to-vla/*.md` 是与姊妹仓 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 的接口。每篇必须：

1. 明确两端分工（Spatial 提供什么 / VLA 消费什么）
2. 列出 ≥1 个"两端契约"项目（数据 schema、坐标系、scale flag 等）
3. 跨链接到 VLA-Handbook 对应章节（即使姊妹仓还没写到，留 `TBD` 锚点）

---

## reports/weekly + reports/biweekly 写作规范

- **weekly**：前瞻偵察（意外 / 可证伪命题 / 观察清单）— 仿 VLA-Handbook 周报体例
- **biweekly**：回顾分析（趋势 / 洞察 / 预测）+ 上期预测打分回溯
- 双周报必须带「预测得分卡」段：列出上期预测、命中 / 未命中、原因
- 报告是索引层不是分析层：深度内容用 `→ deep dive: [link]` 指向 `foundations/` `crossing/` 中的文档

---

## 索引维护（每次新增内容必须同步）

- `foundations/` 新增：更新对应子目录 `README.md` 的 "First wedge" 列
- `embodiments/` 新增：更新 `embodiments/README.md` 的 depth tier 表
- `crossing/` 新增：更新 `crossing/README.md` 的 "First wedge" 列
- `companies/` 新增：更新 `companies/README.md` 的厂商列表
- `bridge-to-vla/` 新增：更新 `bridge-to-vla/README.md` 表格
- `cheat-sheet/` 新增：更新 `cheat-sheet/README.md` 索引
- 根目录新主题入口：更新 `README.md` 「项目结构」 + 「先看这几篇」段

---

## Sensor-physics 特别注意

`foundations/sensor-physics/` 是本仓的独家轴，与学术综述差异最大的地方：

- 任何 spec 数字（QE / power / cost / dimension）必须附数据手册引用（vendor + 型号 + datasheet URL 或 `UNVERIFIED, no DOI`）
- 任何眼睛安全 / 法规相关声明必须引 IEC 60825-1 等标准编号
- 不允许从论文摘要复述 sensor 参数 — 必须从厂商一手资料
- 维护者 Autel 经验内容用 `✍️` 标记，Moltbot 不触碰

---

## 仿真饱和警告（继承 VLA-Handbook，retarget 到 spatial benchmark）

ScanNet++ / TUM-RGBD / EuRoC 等仿真 / 受控 benchmark 数字已被反复刷榜：

- **仅 benchmark 论文**：deep dive 必须标注「⚠️ 仅 benchmark 验证」+ 讨论真机 / 户外 gap
- **评分上限**：仅 benchmark + 无真机 / 户外测试的论文最高 🔧，除非范式级架构创新
- **对比要求**：EuRoC 100% recovery 的 VIO 论文必须关注 outdoor / aerial 真机数字

---

## 避免事项

- 不要编造论文、benchmark 数字、SWaP-C 数据；不确定一律 `UNVERIFIED` 或 TODO
- 不要批量重写既有文档；优先小范围增量
- 不要创建新的顶层目录（`foundations/` `embodiments/` `crossing/` 等 9 个是封闭集）
- 不要在 `embodiments/<x>/` 写本应放在 `crossing/` 的内容（同问题写一次，不要复制到每个 embodiment 下）
- Moltbot 不触碰任何 `✍️` 标记的人工内容

---

## 变更自检

- [ ] 索引可找到新增 / 修改文档
- [ ] 内部链接有效
- [ ] 术语与命名一致（VGGT 永远大写、3DGS 永远小写 d 大写 G S）
- [ ] 关键数字附来源或 `UNVERIFIED` 标记
- [ ] Moltbot 提交：commit message 使用正确 emoji 前缀
- [ ] Moltbot 提交：未修改权限矩阵以外的文件
- [ ] 如涉及 `crossing/`：满足跨 ≥3 embodiment + 工程数字 + boundary 要求
