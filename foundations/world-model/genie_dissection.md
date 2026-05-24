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

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive) — closed-source failure modes

Genie 1/2/3 是 DeepMind 三代閉源——**沒有官方 repo、沒有官方 issue tracker、沒有官方權重**。標準的「逐 issue 列表」deep dive 在這裡**不適用**；本節改述「閉源 = 哪些 GitHub 訊號該存在但不存在」，並把可用的開源 sibling 量化。

### 8.1 · 「No GitHub issue track」失敗模式分類

| Failure mode | 對讀者的具體後果 |
|---|---|
| **權重不開** | 你**永遠不能**在自己的 wrist-cam 分布上 fine-tune Genie；§4.x 「LAM 訓於互聯網視頻、不是 teleop」這個 hidden assumption 對外部使用者**不可解** |
| **無官方 issue tracker** | 沒有「what breaks at scale」社區語料；§4 failure table 全部基於 DeepMind blog + ICML paper 自報，**無對抗驗證** |
| **無第三方 benchmark reproduction** | "Genie 2 achieves X 在 Y benchmark" claims 都活在 cherry-pick demo 視頻裡，**無 paper 引用「we reproduced Genie 2's X 數字」** |
| **無公開 deployment post-mortem** | Cosmos 至少有人 issue 抱怨 32GB OOM（具體成本訊號）；Genie 連「跑一次要多少 GPU-hour」社區數字都沒有 |
| **無 weights → 無 API surface** | 不能 wrap、不能 distill、不能 benchmark against；任何"我的 X 勝過 Genie" 是 **prima facie 不可審計** |

**這不是工程小事**——這結構性地切斷了 §6 falsifiable prediction 的所有對照組：要驗證「Genie 血統不會在 2027-12 前以 >10% 優勢勝過 non-rollout VLA」，社區**沒有 Genie 血統 baseline 可比**。預測仍 falsifiable（waits for any group with API access），但反方無從主動下注。

### 8.2 · 可用的 GitHub 開源 sibling（量化）

§5 列了 "Open-source Genie reproductions / UniSim / iVideoGPT / 1X World Model"。GitHub 實地清點 (2026-05)：

| Repo | Owner | ★ | What it is | Caveat |
|---|---|---|---|---|
| **`open-genie`** | myscience | 284 | PyTorch impl of Genie 1 (Bruce et al. 2024) | 規模小，無 Genie 2/3 對應；reference implementation 性質 |
| **`jafar`** | FLAIROx | 107 | JAX reimplementation of Genie 1 | 框架對 robotics 社區門檻高（多數 RL/VLA 在 PyTorch） |
| **`GenieRedux`** | insait-institute | 75 | Genie + enhancements，含 exploration agents + 數據 | 最接近「研究可用」變體 |
| **`Matrix-Game`** | SkyworkAI | 2.2k | Interactive world model w/ long-horizon memory，real-time streaming env | 自家路線，**不**復現 Genie 但占同生態位 |
| **`Olaf-World`** | showlab | 101 | "Orienting Latent Actions for Video World Modeling" (ICML 2026) | **直接攻擊 §4.x「潛在動作不 grounded 到機器人末端命令」這個關鍵 hidden assumption** — 值得讀者單獨追 |
| **`Project Lyra`** | nv-tlabs | 2k | NVIDIA "Open Generative 3D World Models" | NVIDIA-side 開源回應，不是 Genie clone |
| **`Helios`** | PKU-YuanGroup | 1.8k | Real-time long video generation via diffusion | 解 §4 「multi-step horizon High severity」的同類 |

**讀數**：
- **真正的「Genie 1 reimpl」三個（open-genie / jafar / GenieRedux）合計 ★ ~466**——對比 Genie blog 帖的社交曝光，**社區實際投入小於 1%**。這證實 §4.y 「社區根本沒有 baseline」 — 結構性失血，不是時間問題。
- **無 Genie 2 / 3 reimpl** — DeepMind 不公布架構細節（11B autoregressive transformer 是唯一公開規格），導致 reproduce 路徑不明。即使有人想試，**沒有足夠 spec 起步**。
- **Olaf-World (ICML 2026 Outstanding)** 是本批 deep dive 最有價值的線索——它正面攻 latent-action grounding 問題，是 §4.x hidden assumption #1 的學術突破口。值得從 sibling list 升級為 §5 的**首選跟蹤對象**。

### 8.3 · 對比表：Cosmos vs Genie vs GAIA-3 開源姿態

| 維度 | Cosmos (NVIDIA) | Genie (DeepMind) | GAIA-3 (Wayve) |
|---|---|---|---|
| 權重 | ✅ Apache 2.0（部分 robot-tuned 變體仍閉 — 見 cosmos-transfer #225） | ❌ 全閉 | ❌ 全閉 |
| 官方 repo | ✅ 5 子庫 (nvidia-cosmos/*) | ❌ 無 | ❌ 無 |
| Issue tracker | ✅ 千級開放 issues | ❌ 不存在 | ❌ 不存在 |
| 第三方 reproduce | ⚠️ 部分（#52 顯示 Reason2 reproduce 有 ~6 點 gap；Policy 無 reproduce） | ❌ Genie 1 有 3 個小 reimpl；Genie 2/3 無 | ❌ 無 |
| 商業使用 | ✅ Apache 2.0 允許 | ❌ DeepMind 內部 | ❌ Wayve 內部 |
| Community baseline 可用性 | ✅ 至少可 git clone 跑（如果有 H100） | ❌ 用 UniSim / open-genie 代替 | ❌ 無 |

**核心結論**：在 world-model 三方陣中，**Cosmos 是唯一有 actual community surface 的選項**；Genie 與 GAIA-3 是「論文存在、產品不存在」狀態。讀者做 lane 選擇時：
- 要 **deploy / fine-tune** → Cosmos 子庫拼裝（接受 §8.1–§8.7 列出的所有 caveat）；
- 要 **academic reference** → cite Genie/GAIA-3 paper，但別 claim 已 reproduce；
- 要 **online MPC rollout 引擎** → 跟 `open-genie` / `Olaf-World` / UniSim 開源血統，**Genie 品牌本身不是路徑**。

### 8.4 · 「Closed weights」對 §6 預測的影響

§6 falsifiable prediction 寫的是「2027-12 前不會有任何公開 manipulation 策略把 Genie 血統作 online MPC rollout 引擎並以 >10% 勝過 baseline」。本節 GitHub 訊號**強化**這個預測：

- 即使 DeepMind 內部驗證了，**社區無 baseline 對比**——claim 不可獨立 audit；
- 開源血統（open-genie 等）規模太小（最大 284★），**沒有訓練到 Genie 2/3 級別的 capacity**；
- Genie 3 24 fps 解的是「per-step latency」這個失敗模式（§6 解鎖項 #3），**但解不了 grounded LAM**（解鎖項 #1）——後者才是 manipulation 的 binding constraint。

**Interview Tip 升級**：被問「為何 Genie 不像 Cosmos 一樣有人實際拿來訓 VLA」，答「閉權重 + 無 issue tracker + 第三代仍無架構 spec → 社區結構性沒有 baseline；真正在 robotics 工作的人跟 `open-genie` / `Olaf-World` / UniSim 而非 Genie 品牌本身」。

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
