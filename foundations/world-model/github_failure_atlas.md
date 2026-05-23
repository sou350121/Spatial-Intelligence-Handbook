# World Model GitHub 失败图谱 (World Model · GitHub Failure Atlas)

> **类型**：roadmap / atlas（非 dissection；不走 14 项门槛）
> **聚焦**：在 NVIDIA Cosmos / Genie / Marble 三条线公开 repo 与产品页里**真实可见的 momentum 与失败模式**，给出"哪些值得跟、哪些不该浪费时间"
> **核心定位**：dissection 写"它如何与策略闭合"；本图谱写"原始 repo 已 deprecate、生态拆 14 个子库、Genie 与 Marble 没 repo 可看的现实如何影响读者下一步"

**Status:** v1 — opinionated draft, 2026-05-21。star / fork / issue 数字截取自 GitHub API 当日快照；产品级声称（Marble）标 `UNVERIFIED`。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)
**Scope tier 继承 README**：W2 lane，只看 decision-useful 那一片。

---

## X-Ray (non-expert friendly)

(a) "World model" 这条 lane 公开 artifact 极度不均：NVIDIA Cosmos **已 deprecate 原 monolithic repo** 拆成 [`nvidia-cosmos`](https://github.com/nvidia-cosmos) 14+ 子库；Google Genie **完全闭源**；World Labs Marble 是**消费级产品**没有任何代码或论文 `UNVERIFIED`。(b) 三条线的真实失败模式都不一样：Cosmos 因生态拆分而**碎片化部署痛**；Genie 因闭源而**复现不可能 → action-conditional 路线社区无 baseline**；Marble 是**对机器人无用**（NVS / depth-from-video 这一片虽可榨出价值，主线是给人类看的）。(c) 对工程师：Cosmos 子库挑 1-2 个跟（数据生成 → cosmos-predict / sim2real → cosmos-transfer / 数据闭环 → cosmos-curate）；Genie 当成范式 inspiration 不当成 baseline；Marble 直接绕开。

---

## 📍 Zone Momentum Snapshot (2026-05-21)

```
路线          | repo / artifact                  | stars     | last push       | momentum
─────────────|──────────────────────────────────|───────────|─────────────────|──────────
Cosmos       | NVIDIA/Cosmos (旗舰 — deprecate) | 8096★     | 2026-01-06     | 🔧 已转移
Cosmos       | nvidia-cosmos/cosmos-predict2.5  | 1212★     | 2026-05-04     | ⚡ 活
Cosmos       | nvidia-cosmos/cosmos-reason1     | 945★      | 2026-01-06     | 🔧 转 reason2
Cosmos       | nvidia-cosmos/cosmos-transfer1   | 801★      | 2026-01-06     | 🔧 转 transfer2.5
Cosmos       | nvidia-cosmos/cosmos-predict2    | 775★      | 2025-10-29     | 🔧 转 predict2.5
Cosmos       | nvidia-cosmos/cosmos-transfer2.5 | 657★      | 2026-05-13     | ⚡ 活
Cosmos       | nvidia-cosmos/cosmos-rl          | 426★      | 2026-05-20     | ⚡ 活
Cosmos       | nvidia-cosmos/cosmos-curate      | 184★      | 2026-05-01     | 🔧 数据闭环
Genie        | (无公开 repo)                    | —         | —              | ❌ 闭源
Marble       | (无公开 repo, 产品)              | —         | —              | ❌ 消费向
```

读法：NVIDIA Cosmos 不是"一个 repo"，**而是一个 14+ 子库的生态**。原 `NVIDIA/Cosmos` 已**标 deprecate**（issue #167 *"Deprecate codebase"* 已合并 + README 重定向到 `nvidia-cosmos/`）。如果你 git clone 旧 repo，**走错路了**。

---

## 1 · NVIDIA Cosmos — 已生态化、原 repo deprecate

**原 repo**：[`NVIDIA/Cosmos`](https://github.com/NVIDIA/Cosmos) · 8096★ · 512 forks · last push 2026-01-06 · **deprecate via #167**

**新生态**：[`nvidia-cosmos` org](https://github.com/nvidia-cosmos)，至少 14 个子库（截至 2026-05-21）。

### 子库定位矩阵

| 子库 | 角色 | 决策有用? | 备注 |
|---|---|---|---|
| `cosmos-predict2.5` ⚡ | 世界基础模型预测（最新） | **是** — sim2real 数据工厂主线 | 1212★，2026-05-04 push |
| `cosmos-transfer2.5` ⚡ | sim→real 多空间控制传递 | **是** — 解决 sim2real 渲染 gap | 657★，2026-05-13 |
| `cosmos-rl` ⚡ | Physical AI 强化学习 | **是** — RL 框架可与 VLA 端整合 | 426★，2026-05-20 |
| `cosmos-curate` | 视频数据系统化策展 | **是** — 数据闭环工具链 | 184★，2026-05-01 |
| `cosmos-reason2` | 物理常识 + chain-of-thought | 部分 — 仍在测 | 386★，2026-05-08 |
| `cosmos-cookbook` | post-training 脚本 | 中介 — 实战重要 | 406★，2026-04-24 |
| `cosmos-xenna` | Ray 分布式 pipeline | infra | 67★ |
| `cosmos-predict1` 📖 | v1 预测 (前代) | 历史 | 447★，已被 predict2.5 替代 |
| `cosmos-reason1` 📖 | v1 reason (前代) | 历史 | 945★ |
| `cosmos-transfer1` 📖 | v1 transfer (前代) | 历史 | 801★ |
| `cosmos-predict2` 📖 | v2 中间版 | 历史 | 775★ |
| `cosmos-evaluator` | 自动评测 | infra | 16★ |
| `cosmos-dependencies` | 依赖封装 | infra | 9★ |

读法：**真正活的是 predict2.5 + transfer2.5 + rl + curate 这四个**。其余要么是上一代要么是 infra 辅助。

### Failure patterns

| Pattern | 出处 | 含义 |
|---|---|---|
| **Repo 拆分让"clone 一份跑通"几乎不可能** | issue stream 跨 14 子库分散 | 旧 monolithic 路径已 deprecate；新生态要求**学会怎么拼**而不是 git clone |
| **Physical implausibility 在 demo 之外稳定** | 论文 / blog 自陈 + 社区反馈 | sim2real 桥被卖力宣传，但**生成视频在被推到训练数据规模时**仍含违反物理（穿模、能量不守恒、刚体抖）的轨迹 `UNVERIFIED` 待 VLA 端 ingest 实验 |
| **时序漂移** | 视频生成共病 | 几秒后 identity / geometry 漂；机器人长 horizon 任务 ingest 会**承袭漂移**作为训练分布 |
| **"Decision-useful" 论断仍未公开测量** | 无公开 paper 报告 "Cosmos-trained VLA improves task X by Y" | 厂商承诺 sim2real 数据可加速 VLA 训练，但**社区还没看到独立验证**；这是本 lane 最大的未解问 |

### PR / 实验方向

- **PR 1**：写一份 "Cosmos ecosystem reading guide" — 给后来者一张图说明 4 个活子库怎么拼成数据生成 → 训练 pipeline。当前 nvidia-cosmos 的 README 跨库导航不够清。
- **PR 2 (实验)**：跑 cosmos-predict2.5 生成 1k 轨迹 → 用 cosmos-transfer2.5 渲到真实风格 → 喂给一个 baseline VLA → 测量 task success 提升 vs not using Cosmos 数据。**这个独立验证是 2026 全社区都欠的**。
- **PR 3 (审查)**：在 cosmos-curate 流水线里加 "physical plausibility filter" — 过滤生成数据里的违反物理样本，看下游 VLA 训练是否质变。
- **实验**：cosmos-predict2.5 在不同 horizon (1s / 5s / 30s) 上的几何 / identity drift 量化曲线。决定能用多长。

### Momentum: 🔧（生态层 ⚡ NVIDIA 推得猛；单 repo 层是中等活；最大未解：decision-useful 验证）

---

## 2 · Google Genie — 完全闭源，社区无 baseline

**Repo 状态**：**无任何公开 repo / 权重**。仅 paper + DeepMind blog。社区复现存在（如 `genie-2-demos` 类项目）但**不是官方**，不应当作 Genie 对照。

### Failure patterns (推论性质，无 repo 可看 issue)

| Pattern | 来源 | 含义 |
|---|---|---|
| **Action-conditional 路线社区无 baseline** | 闭源 | Genie 是该范式（latent action + 视频生成）最有名实现；社区没法 reproduce → 任何后续工作只能**间接**比较 |
| **Decision-useful 仅 demo 级** | DeepMind 演示 | Genie 用作"推理时 action-conditional 规划器"看起来工作，但**真正的 metric**（机器人 task success、planner 成本节省）从未由独立第三方测量 |
| **时序合理性论文级断言 vs 真机静默** | 论文 + 内部测试 | DeepMind 论文给 N 步 rollout 一致性，但具身侧第三方未验 |

### PR / 实验方向

- **没有 PR 直接路径**（无 repo）。可做的二阶：
- **开源 "Genie-like" minimal reference impl** — 用 latent action transformer + 小视频生成 backbone，在 Procgen / Atari 上跑出动作可控的 rollout。证明该范式可独立复现。已有学术尝试，但需要一个**community canonical** 接力 repo。
- **比较 Cosmos (predict2.5 + reason1) 与 Genie 范式的论文** — Cosmos 是"无 action conditional 的高质量视频生成"，Genie 是"action conditional 的相对粗糙生成"。哪一条更先抵达 decision-useful？至今无文献正式比较。

### Momentum: ❌（闭源 → 社区 baseline 等于不存在；论文级影响在 → cite 价值仍有；工程级跟进**无路径**）

**本图谱建议**：Genie 当 inspiration / paradigm reference 看，**不当 baseline**。任何论文报告 "we beat Genie" 都该被严格审查 — 他们到底在 beat 什么 artifact？

---

## 3 · World Labs Marble — 消费级，机器人无用主线

**Repo 状态**：**无公开 repo**。是 World Labs 商业产品 (`worldlabs.ai/marble`)，提供"text/image → 3D scene"的消费向工具。无 paper / 无 weight / 无 API doc 公开 `UNVERIFIED`。

GitHub 搜索 "marble world model" 仅返回**第三方 ComfyUI 节点**（[`rikturnbull/comfyui-worldlabs-marble`](https://github.com/rikturnbull/comfyui-worldlabs-marble) 1★）— 即"调 Marble 商业 API 的 wrapper"，不是 reimpl。

### Failure patterns

| Pattern | 含义 |
|---|---|
| **目标用户是人类，不是策略** | Marble 卖点是"创作 3D 场景"，输出供 Blender / 游戏引擎 / VR 消费。机器人栈消费它的成本（再提 depth / 再校 metric / 再过物理 plausibility）超过自己跑 NeRF/3DGS |
| **物理 plausibility 弱** | 消费级容忍违反物理（飘空物体、不闭合 mesh），机器人栈消费会触发碰撞规划失败 |
| **Closed API → 训练管线锁定** | 用 Marble 生成数据训 VLA → 厂商改 API → 数据分布漂移 → 模型必须重训 |

### Decision-useful 可榨取的"那一片"

按 README scope tier，**仅 Marble 的 depth-from-video / NVS 这一片**理论上可作策略数据增广。但前提是：
1. World Labs 公开足够 inference path 让外部跑 batch
2. 输出含 metric scale 或可校准
3. 几何精度可量化（CD / F-score 等）

以上三条**当前一条都不满足** `UNVERIFIED`。本图谱判断：**当前不值得投入跟进**，留 v2 watchlist。

### PR / 实验方向

- **不建议任何 PR**。可做的：
- **写一篇 "Marble for robotics? No." 短分析**放 `cheat-sheet/` — 给后来者省时间，避免反复被 "Marble does world model" 营销话术拉进坑。
- **观察 World Labs 是否发学术论文** — 一旦发，按 dissection 模板审，决定是否升 W3 → W2。

### Momentum: ❌（产品级 ⚡ 资本市场关注；学术 / 工程级 ❌ 对机器人栈贡献近零）

---

## 4 · Zone 共性失败 (Cross-tool synthesis)

读完 NVIDIA 14 子库 issue 流 + Genie / Marble 的"无 repo"事实，World Model lane 的**结构性失败**：

1. **Physical implausibility 是所有生成式世界模型的共病**。Cosmos / Genie / Sora 系一致 — 模型生成的样本通过人类视觉 turing test，但喂给物理引擎 / 碰撞 / 力学约束**几乎必有违反**。"漂亮 demo 与可消费数据"之间有质的 gap。
2. **"Decision-useful only" 至今仍是承诺级，不是测量级**。本 lane README 立的高门槛 — 数据真能被 VLA / RL ingest 改善 metric — **目前无第三方独立验证**。NVIDIA / DeepMind 内部测过但没让外部 reproduce。
3. **时序漂移压住有效 horizon**。生成式 rollout 几秒后 identity / geometry 漂，意味着策略训练能用的有效 segment 短。长 horizon 任务（manipulation 序列、driving 多分钟）几乎不可能完全靠生成数据。
4. **闭源 / 商业化吞掉社区 baseline**。Genie 闭源、Marble 商业，加上 Cosmos 拆 14 库 onboard 高 — 本 lane 比 semantic-3D 更难有"git clone 就能跑的对照"。
5. **生态化 ≠ 易用**。NVIDIA 把 Cosmos 拆成 14 库本意是 modular，但实际让"我该 clone 哪个"成为新 onboarding 痛点。

---

## 5 · 维护者优先级建议

| 行动 | 谁干 | 为什么现在做 |
|---|---|---|
| 跑独立 "Cosmos-trained VLA vs baseline VLA" 闭环实验 | 任何有 VLA 训练管线的实验室 | 是 World Model lane **最大未解问** — 全社区都欠这个数 |
| 写 "Cosmos ecosystem reading guide"（4 个活子库怎么拼） | 任何跟过 Cosmos 的人 | 现状 onboard 极乱，社区议题分散 |
| 开源 "Genie-minimal" 范式 reference | 学生 / 研究组 | 让 action-conditional 视频生成有 community baseline |
| **不**做：跟 Marble 商业 API | 任何人 | 投入回报极低，且 lock-in 风险高 |
| 把"physical plausibility filter"做成 cosmos-curate 插件 | 数据 ops 团队 | 直接攻击 #1 共性失败 |

---

## Boundary

本图谱**只覆盖 decision-useful 世界模型**（生成数据 / observation / rollout 能闭合到具身策略）。它**不**覆盖：

- VLM 直接出空间答案 → [`foundations/vlm-spatial-reasoning/github_failure_atlas.md`](../vlm-spatial-reasoning/github_failure_atlas.md)
- 2D 特征抬升 → [`foundations/semantic-3d/github_failure_atlas.md`](../semantic-3d/github_failure_atlas.md)
- 通用 text-to-video / 生成式媒体 → out of scope（按 README ❌ 标签）
- 物理真实度方法 deep dive → [`foundations/physics/`](../physics/)
- 跨方法对比 (Cosmos vs Genie vs UniSim vs DriveDreamer) → [`crossing/representation-migration/`](../../crossing/)

## For the reader

- **机器人 / VLA 工程师**：跟 `cosmos-predict2.5` + `cosmos-transfer2.5` + `cosmos-rl` 三个。其他 12 个先忽略。先做独立验证再扩大投入。
- **学生 / 选题**：(a) "Cosmos-trained VLA improves task X by Y" 独立验证；(b) action-conditional vs unconditional 在 decision-useful 上的对照；(c) physical plausibility filter for cosmos-curate。任一题都论文性强。
- **Reviewer**：拒绝 "we beat Genie on metric X" 没有 Genie reference impl 的论文。拒绝 "Cosmos 生成数据 improves VLA" 没有 baseline ablation 的论文。

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21
[← Back to world-model README](./overview.md)
