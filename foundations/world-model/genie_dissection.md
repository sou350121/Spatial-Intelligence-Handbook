<!-- ontology-5axis
problem: World model (action-conditioned video gen)
representation: Latent video tokens
sensor: Video
paradigm: Generative-VideoWorldModel (action-conditioned)
time: FeedForward (action-conditioned); Real-time 24 fps (Genie 3)
ref: ../../cheat-sheet/ontology.md §7
-->

# Genie / Genie 2 / Genie 3 解构 (Genie / Genie 2 / Genie 3 — DeepMind, Dissection)

> ⚠️ **STALE notice — Genie 3 (DeepMind Aug 2025) 已發布**，本 dissection 主述 Genie 1 (ICML 2024) 與 Genie 2 (Dec 2024)。Genie 3 規格：
> - **11B autoregressive transformer**
> - **720p @ 24 fps real-time navigable**
> - **Multi-minute scene consistency**
>
> 大幅改善 §4 failure table 的「each step >50ms」rated as `Medium`：Genie 3 達 24 fps real-time，**接近 MPC 可用**（每步 ~42 ms < 50 ms threshold）。Weights 仍 closed (Hard blocker 不變)。詳見 ontology §5.3 / §9.5 ("Genie 2/3 ★ updated")。
>
> 同期 peer：**GAIA-3 (Wayve 2026)** — closed-loop driving evaluation；**Aether (OpenRobotLab ICCV 2025 Outstanding)** — geometry-aware unified world modeling。

> **发布时间**: Genie 1 — ICML 2024 (Bruce et al.); Genie 2 — DeepMind blog, December 2024; Genie 3 — DeepMind blog, August 2025
> **论文 / 模型**: Genie — DeepMind action-conditional world model family
> **核心定位**: 一个**可玩**的图像空间 world model，带**学到的潜在动作词表**——VLA 的候选**推理时规划器**，不是训练数据工厂。

Genie 在结构上与 Cosmos 不同：它给你一个可调用的 `next_frame = model(frame, action)` 函数。这让它成为策略闭环内 MPC 风格规划的合适原语——前提是你能解决未解决的部分：把 VLA 动作映射到 Genie 学到的潜在词表上。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Latent-action dimensionality and horizon claims marked `UNVERIFIED`.
**Wedge tier:** W2 · ⚡ [WorldModel] 🛰️
**TL;DR:** Genie 的贡献不是"又一个 text-to-video"，而是**首个可信地朝 action-conditional world model 迈进、且带一个可控潜在动作空间**的工作——这使它成为 VLA 的候选**推理时规划器 / rollout 引擎**，而非训练数据工厂。代价：潜在动作空间是从视频无监督学到、无 grounded label，从 VLA 动作词表映射到 Genie 潜在动作的问题至今没人干净解决。多步 horizon 与精细几何是限制实用的两大失败模式。

### X-Ray (non-expert friendly)

(a) 现有视频模型（Cosmos、Sora）渲染出合理视频但不可*玩*——你没法问"如果我采取动作 a 会发生什么？"。(b) Genie 从无标签视频学一个离散潜在动作词表，再训一个 dynamics 模型，给定当前 frame + 选定潜在动作预测下一 frame——像函数一样调用。(c) 对空间 AI 工程师：Genie 是 VLA 首个可信的**在线 MPC rollout 引擎**，但今天用不上，因为 (i) 潜在动作不 grounded 到机器人末端命令，(ii) rollout 在 2–4 s 后漂，(iii) 权重不开。

### 📍 Research Landscape Timeline

```
World Models 2018 ─► DreamerV3 2023 ─► UniSim ICLR 2024 ─► ★ Genie ICML 2024 ─► Genie 2 Dec 2024 ─► Genie 3 Aug 2025 (11B, 720p@24fps, multi-min) ─► grounded-LAM 2026? ─► ?
                                            │
                                            └── peer: Cosmos (data factory, not planner)
```

Genie 2 是首个声称分钟级 3D 场景 rollout 的工作；权重保持封闭，所以实际机器人工作都跑在 UniSim 风格的开源 clone 上。

---

## 1 · Why Genie is structurally different from Cosmos

Cosmos 问的是：*"给定 conditioning，渲染合理视频。"* 动作进来作为弱信号，甚至不进来。

Genie 问的是：*"给定当前 frame 和一个离散潜在动作，按好像采取了那个动作的方式渲染下一 frame。"* 这是更强的架构承诺——它让模型**可玩**，规划器需要的就是这个性质。

这就是为什么 Genie 对 VLA 团队的意义和 Cosmos 不同。Cosmos rollout 是你*训练之上的*东西。Genie rollout 是你在策略闭环内*想象*的东西——你在分支上剪枝，给候选动作打分。**推理时使用，不是训练时使用**——集成故事不同，失败模式也不同。

---

## 2 · Architecture in one diagram

> 📌 **Napkin Formula**: `frame_{t+1} = Dynamics(frame_t, a_t)`，其中 `a_t ∈ {1..K}` 是从无标签视频自监督推得的**学到的潜在动作**。模型整体就是"frame + latent action → next frame"，可玩部分在于以 `a_t` 为条件。

DeepMind 的 Genie（Bruce et al. 2024）与 Genie 2（DeepMind blog, 2024 年底）共享同一骨架：

```
  (training)   frame_t, frame_{t+1} ──► ST-Transformer tokenizer ──► VQ latent action a_t ∈ {1..K}
                                                                              │
  (training)   frame_t + a_t ──► autoregressive dynamics ──► frame_{t+1}      │
                                                                              │
  (inference)  frame_t + supplied a_t ──► dynamics ──► next frame  ◄──────────┘
```

三个组件：

| Component | Role | Trained on |
|---|---|---|
| **Video tokenizer** | 把帧压成空间 token | 无标签互联网视频 |
| **Latent action model (LAM)** | 推断连续两帧间的离散潜在动作 | 同视频自监督 |
| **Dynamics model** | 给定当前 frame + 潜在动作预测下一 frame | 与以上联合训练 |

Genie 1：以 2D 平台跳跃 / 机器人视频为主；K ≈ 8 `UNVERIFIED`。Genie 2：3D 场景、更长 horizon（在 cherry-pick 的 demo 里约 1 分钟稳定 rollout）、更丰富的动作词表——确切 K 未公开。

最重要的架构事实：**潜在动作空间是学到的，不是 labeled 的**。"Genie 潜在动作 #3" → "VLA 末端 +5 cm x" 没有保证映射。这就是集成痛点。

> ⚡ **Eureka Moment**: **学到的离散潜在动作词表**（Genie 1 中 K ≈ 8）是模型可*玩*的原因。没有它的视频模型只是无条件地合理生成；Genie 在**选定动作 token 下合理生成**，这正是 MPC 闭环需要的原语。

### 2.5 · Worked example — toy MPC planning step

VLA 控制一个桌面机械臂。状态 = 当前 wrist-cam 帧。

- **采样**：VLA top-K 中取 5 个候选 (Δx, Δy, Δz, Δθ)。
- **Action → latent**（开放问题）：在学到的 embedding 里最近邻 → 5 个 `a ∈ {1..8}` token `UNVERIFIED`。
- **Genie 滚** 8 帧 / 分支，每帧 ~10–30 ms `UNVERIFIED`（远低于当前 Genie 2 实际延迟）。
- **VLM critic** 给每个分支打分；执行最优 Δ。

今天的杀手：(i) 5 个不同 VLA 动作可能塌缩到**同一个** K=8 token；(ii) rollout ~4 s 后漂；(iii) Genie 2 单步延迟 `UNVERIFIED` 远 >> 50 ms——不蒸馏跟不上 10–30 Hz 控制。

---

## 3 · Inference-time planner: the use case that justifies the model

一个能*正当化*Genie 存在的 VLA-in-the-loop 模式：

```
 VLA top-K candidate actions
        │
        ▼  (map VLA action → nearest Genie latent action ← OPEN PROBLEM)
 Genie rolls out 5–10 steps per branch
        │
        ▼
 Critic (VLM / value head) scores rollouts ──► pick best branch
```

一个学到的图像空间 dynamics 模型驱动的 MPC 闭环。**这是 Genie 类模型对具身 AI 最合理的高杠杆用法**，与 Cosmos 的数据工厂角色严格不同。

为什么难：连续 VLA 动作 → 离散 K-way 潜在词表失精；rollout 漂（有用 horizon 5–10 帧 `UNVERIFIED`）；critic 也得活在像素空间，否则需要一个快速 pixel→state encoder。与 `bridge-to-vla/feature-cloud-to-action.md` 自然相交。

---

## 4 · Where it breaks

| Failure | Severity | Why |
|---|---|---|
| **Multi-step horizon** | High | rollout 在 2–4 秒后视觉漂移。再长就是 cherry-pick，硬性限制规划 horizon |
| **Fine geometry** | High | tokenizer 是视频统计而非 3D 感知；小物体、窄缝、精接触都错 |
| **Action precision** | High | 离散 K-way 动作无法表达亚厘米级运动，精细操作不可行 |
| **Out-of-distribution scene** | Medium | 训于互联网视频；新机器人实验室几何 OOD |
| **Lack of metric scale** | Medium | 和 VGGT 同盲点——无绝对单位，与 metric world model 或物理先验难融合 |
| **Closed weights** | Hard blocker | 截至 2026-05 Genie 1 与 Genie 2 权重均未公开；机器人工作可复现性受限 |

Genie 2 声称的 1 分钟 rollout 伴随 cherry-pick 注释，从未被宣称为"策略闭环可用"。

### 4.x · Hidden Assumptions

- **潜在动作可映射到你的动作空间** —— 无保证；LAM 训于互联网视频，不是 teleop。
- **有用 horizon ≤ 5–10 帧** `UNVERIFIED`；再长就漂。
- **静态或近静态场景** —— 运动物体被 token 化为外观、不当作实体。
- **像素空间 critic 可接受** —— 否则需要快速 pixel→state encoder。
- **你拿到权重** —— Genie 1 & 2 至今封闭（2026-05）；UniSim clone 是唯一实际基底。
- **近 Lambertian、类互联网视频场景** —— 机器人实验室几何 OOD。

任一被违反，规划器变噪声——没有 calibrated uncertainty 旗。

### 4.y · GitHub 实地失败（atlas 联动）

- **GitHub-validated**：Genie 1 & 2 至今**完全闭源**（无 repo / 无权重），社区"genie-2-demos" 类项目都不是官方对照；这意味着 action-conditional 路线**社区根本没有 baseline**，任何论文"we beat Genie on metric X" 都该被严审——他们在 beat 什么 artifact？详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：实际可用的开源 sibling 是 UniSim clone / iVideoGPT / 1X World Model；要部署 action-conditional rollout 走这些，不要等 Genie 权重，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。

**Interview Tip**：答"可玩 world model，但潜在动作 grounding 未解；今天它的位置是 *离线 dream-based pretraining*（Dreamer 风格），不是 live MPC。关注 UniSim clone，而非 Genie 这个品牌。"

---

## 5 · Open-source siblings to watch

由于 Genie 权重不开，实际可用的相关血统是开源 clone：

- **Open-source Genie reproductions** ([arXiv link TBD], multiple 2024–2025 efforts) —— 较小规模，同骨架。
- **UniSim** (Yang et al. *ICLR 2024 best paper*) —— 用于机器人策略训练的 action-conditional 仿真器。
- **iVideoGPT / 1X World Model** —— 嵌入具身的 dynamics 模型，占同一槽。

真实机器人工作走 UniSim 风格的开源变体；Genie 是参考目标，不是部署系统。

---

## 6 · 2-year outlook + falsifiable prediction

解锁项：(1) **grounded 潜在动作标签** —— 用少量已知动作视频（teleop / sim GT）有监督训 LAM；(2) **3D-consistent dynamics** —— 把 Genie tokenizer 与 3DGS 或 feed-forward 3D 耦合，几何不再漂；(3) **每步 &lt;50 ms** —— MPC 必需，Genie 2 远高于此 `UNVERIFIED`，**Genie 3 (Aug 2025) 24 fps ≈ 42 ms 已達門檻** (見頂部 STALE notice)；(4) **开源权重** —— 没有它，社区会一直拿 UniSim clone 顶上。

- ✅ **VERIFIED 2025-08 Genie 3**: 预测 "每步 <50 ms" 已部分达成 — Genie 3 11B autoregressive 在 720p @ 24 fps real-time 运行 (~42 ms/step < 50 ms threshold)。权重仍封闭（Hard blocker 未解）。

**Falsifiable prediction:** 在 2027-12 之前，**不会有任何公开 manipulation 策略在真机评估中把 Genie 血统模型作 online MPC rollout 引擎、并以 >10% 优势胜过非 rollout VLA 基线**。胜利会先落在 offline dream-based pretraining（Dreamer 风格），horizon 问题在那里被绕开。任何缺乏真硬件对比的"Genie 当 live planner"标题应当下注反方。

---

## For the reader

- **Manipulation VLA team:** Genie 是*未来*的推理时规划器。今天，优先 offline dream-based pretraining（DreamerV3 血统）而非 live MPC。跟 UniSim clone。
- **Driving team:** GAIA-2 / DriveDreamer 是你那侧的版本。同 trade-off，更多 domain 数据。
- **RL researcher:** 潜在动作词表是最干净的开放问题。Grounded-LAM 训练是下一篇论文。
- **Aerial / drone:** 不是你的模型。互联网视频先验不编码高速飞行动力学。

---

## References

- Genie 1 — Bruce et al. *ICML 2024 best paper*. [arXiv link TBD]
- Genie 2 — DeepMind blog, December 2024. https://deepmind.google/discover/blog/genie-2-a-large-scale-foundation-world-model/
- Genie 3 — DeepMind blog Aug 2025 · https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/
- UniSim — Yang et al. *ICLR 2024 best paper*. https://arxiv.org/abs/2310.06114
- DreamerV3 (offline-dream baseline) — Hafner et al. *Nature 2025*. https://arxiv.org/abs/2301.04104

## Boundary

本文把 Genie 解构为**具身策略的候选推理时 rollout 引擎**。媒体 / 游戏生成视角按 lane PRD 划在范围外。跨家族对比（Cosmos / Genie / UniSim）归 `crossing/representation-migration/world-models-as-data-vs-planner.md`（TBD）。VLA 集成契约归 `bridge-to-vla/feature-cloud-to-action.md`。

---

*Last opinion update: 2026-05-21.*
