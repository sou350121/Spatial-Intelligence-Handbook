<!-- ontology-5axis
problem: World model (robotics foundation video)
representation: Video tokens + 3D generation
sensor: Video (multi-modal)
paradigm: Generative-VideoWorldModel (action-conditioned, post-trainable as VLA policy)
time: FeedForward
ref: ../../cheat-sheet/ontology.md §7
-->

# NVIDIA Cosmos 解构 (NVIDIA Cosmos World Foundation Models — Dissection)

> ⚠️ **PARTIALLY SUPERSEDED — 此 dissection 主述 CES 2025 Cosmos v1 family。GTC 2026 已發 Cosmos-2 family**：
> - **Cosmos-Predict-2** (2B/14B) — video foundation model 升級
> - **Cosmos-Reason-2** (7B) — reasoning VLM
> - **Cosmos-Transfer-2.5** — sim-to-real
> - **Cosmos-Policy** — post-trained for robot policy，LIBERO/RoboCasa SOTA (🚀 pilot)
>
> 技術報告：arXiv 2511.00062 (NVIDIA GTC 2026). 詳見 ontology §5.3 / §9.5.
>
> 原 `NVIDIA/Cosmos` 單一 repo 已 deprecate (issue #167)，code 移到 `nvidia-cosmos/` org 下分子庫 (cosmos-predict2.5 / cosmos-transfer2.5 / cosmos-rl / cosmos-curate)。

> ⚠️ **2026-05 状态**: 原 `NVIDIA/Cosmos` repo 已 deprecate (#167)；新代码在 [`nvidia-cosmos/` org](https://github.com/nvidia-cosmos)（14+ 子库）。本文档 url/clone 命令以新 org 为准。

> **发布时间**: CES 2025 announcement (NVIDIA)
> **论文 / 模型**: Cosmos World Foundation Model Platform — Cosmos-Predict / Cosmos-Transfer / Cosmos-Reason
> **核心定位**: 一套**为机器人 rollout 美学调过的 conditional video synthesis stack**——价值落在**数据工厂**，而非"rollout 当规划器"。

Cosmos 不是套了 transformer 外衣的物理仿真器，而是一条挂着 sim2real bridge 故事的视频生成管线。唯一重要的问题是：在某个可证伪的 benchmark 上，用 Cosmos 增广过的数据训出来的 VLA，能否真的胜过没用的版本。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. All throughput / sim2real-gap deltas marked `UNVERIFIED`.
**Wedge tier:** W2 · 🔧 [WorldModel] 🛰️
**TL;DR:** Cosmos 不是"物理仿真"意义上的 world model——它是一套 **conditional video synthesis stack，调到看起来足够物理合理，以致 VLA 用其 rollout 训出来后不会在真硬件上立刻崩**。价值在数据工厂，不在 rollout 当规划器。2027 年的关键问题是：在某个可证伪的 manipulation benchmark 上，Cosmos 增广的训练 mix 能否可测量地缩窄 sim2real gap。

### X-Ray (non-expert friendly)

(a) 机器人数据是瓶颈——真实遥操作约 $10–50 / episode `UNVERIFIED`，经典 sim 便宜但视觉错位。(b) Cosmos 把 Isaac-sim 的 depth/seg 转成 photoreal RGB video，并用 VLM critic 过滤物理违规片段，产出**VLA 训练数据工厂**，而非规划器。(c) 对空间 AI 工程师：把 Cosmos 当 ablation 表里的一种数据源——它关掉**外观 gap**，关不掉**动力学 gap**；对 contact-rich 精细任务无用。

### 📍 Research Landscape Timeline

```
Isaac Sim 2018 ─► DriveDreamer / GAIA-1 2023 ─► Sora 2024 ─► ★ Cosmos CES 2025 ─► Cosmos v2 + 3D-aware critic 2026? ─► ?
                                                                  │
                                                                  └── peer: Genie (action-conditional planner)
```

Cosmos 是首个**面向具身 AI** 的 video foundation stack，并显式拆为 Predict/Transfer/Reason 三块。下游开放问题：action-conditioning fidelity、contact dynamics、learned-material grounding。

---

## 1 · Why this question matters

机器人数据是瓶颈。真实遥操作每集 ~$10–50 `UNVERIFIED`；经典 sim（Isaac、MuJoCo）便宜但视觉上有域差。Cosmos 的卖点：付 GPU 费、拿到看起来像真实 wrist camera 的 rollout，训出 VLA，部署能扛真实 RGB 的策略。**唯一值得看的 benchmark 是：这种策略能否胜过 Isaac + 标准 domain randomization 训出来的策略**；其它皆为美学。

Cosmos 落在 `foundations/world-model/` 是因为数据管线场景在 manipulation、humanoid、ground robot 间通用。driving 的姊妹线（DriveDreamer、GAIA-1）以后挪到 `embodiments/driving/`。

---

## 2 · Model family architecture

> 📌 **Napkin Formula**: `VLA_data ≈ Cosmos-Transfer(Isaac depth/seg) → Cosmos-Predict(extend) → Cosmos-Reason(filter)`——三个视频模型串联，**不是一个物理仿真器**。

NVIDIA 在 CES 2025 把 Cosmos 发布为"World Foundation Model Platform"，分三个子家族（NVIDIA 营销外的具体 spec 数字 `UNVERIFIED`）：

| Sub-family | Architecture class | Conditioning | Primary use |
|---|---|---|---|
| **Cosmos-Predict** | Diffusion + autoregressive video generators (4B / 12B / 14B variants `UNVERIFIED`) | Text + first-frame + optionally action / trajectory | 生成合理的机器人摄像头 rollout |
| **Cosmos-Transfer** | ControlNet 风格的结构迁移 | Depth / segmentation / edge from sim → photoreal RGB | Isaac 资产的 sim2real domain bridging |
| **Cosmos-Reason** | VLM (~7B)，针对视频空间 / 物理推理 fine-tune | Multi-frame video → text | 质量门控生成的 rollout；reject 违反物理的片段 |
| **Cosmos-Predict-2** (2B/14B) | Video foundation model 升级 | GTC 2026 | 下一代 video FM；接替 Predict v1 |
| **Cosmos-Reason-2** (7B) | Reasoning VLM | GTC 2026 | 下一代物理推理 critic |
| **Cosmos-Transfer-2.5** | Sim-to-real 结构迁移升级 | GTC 2026 | 接替 Transfer v1 |
| **Cosmos-Policy** | Post-trained world model as policy | GTC 2026 | **post-trained 为 robot policy，LIBERO/RoboCasa SOTA — 是 world-model-as-policy 範式落地** |

VLA 训练数据 pipeline 视图：

```
  Isaac Sim trajectories + depth/seg
        ──► Cosmos-Transfer (depth/seg → photoreal RGB)
        ──► Cosmos-Predict (extend rollout + camera jitter)
        ──► Cosmos-Reason (physics QA, reject bad)
        ──► VLA training mix
```

架构上的承诺：**Cosmos 不模拟物理，它学合理视频的统计**，再用 Cosmos-Reason 当判别器。这就限死了 Cosmos 的能力天花板——contact-rich dynamics、deformables、OOD 物理只要不在 Cosmos-Reason 的训练分布里都会漏过去。

> ⚡ **Eureka Moment**: **Generator + Critic ≠ Simulator**，但用作 VLA 训练 mix 时可以*够用*。Cosmos-Reason 是承重件——没有学到的判别器筛掉违反物理的片段，free-generation 的 Cosmos-Predict 反而毒害 VLA 监督的速度比帮助的速度还快。

### 2.5 · Worked example — Isaac peg-in-hole augmentation

100-episode Isaac peg-in-hole 数据集（wrist cam, 256×256，含 depth + seg）：

- **Transfer**: `(depth, seg)` → photoreal RGB；A100 上约 1–3 s/frame `UNVERIFIED`。
- **Predict**: 每段延长 10–20 帧 camera jitter。
- **Reason**: 因 object permanence / hand-object intersection 拒 ~20–40% 片段 `UNVERIFIED`。
- **Mix**: 60/30/10（Isaac / real / Cosmos）训练。
- **真机 delta 预期**（contact-rich peg-in-hole）：**接近零**（像素 gap 不是瓶颈）。同 pipeline 上一个杂乱桌面抓取：合理 +3–8% `UNVERIFIED`。

外观瓶颈任务收益，接触密集任务不收益——§6 的微缩版。

---

## 3 · Where it actually helps (vs where it's just expensive generation)

| Scenario | Helps? | Why |
|---|---|---|
| Wrist-camera manipulation, 常见家用物体 | ✅ likely | 纹理 / 光照是 sim2real 主 gap；Cosmos-Transfer 直击 |
| Humanoid loco-manipulation, 场景多样 | ✅ likely | 场景多样性瓶颈在 3D 资产成本，Cosmos 绕过 |
| 精密插装、接触密集装配 | ❌ doubtful | gap 是物理而非像素；像素完美但接触错误的 rollout 没用 |
| Long-horizon mobile manipulation (>30 s) | ⚠️ partial | Cosmos-Predict 会漂；只能当短片段生成器 |
| Driving — closed-loop policy training | ⚠️ partial | GAIA-1 / DriveDreamer 教训：traffic-agent 行为 gap 才是真瓶颈，像素次要 |
| 无人机高速航拍 | ❌ | 无高速运动模糊、桨振、户外光照先验 |

读这张表的方式：**Cosmos 关掉外观 gap，不关动力学 gap**。如果你的 sim2real 失败是"纹理错、真实木纹上失败"，Cosmos 值它的 GPU 钱。如果是"接触力矩差 3 倍"，Cosmos 无关——你要的是更好的物理，不是更好的像素。

---

## 4 · Where it breaks

公开 demo + 社区报告中可观察的失败模式（严重度 `UNVERIFIED`）：

- **5 秒以上 rollout 的 object permanence** —— 小物体被换 / 消失；对依赖跟踪的策略致命。
- **手物相交** —— Cosmos-Reason 抓得到粗暴违反；细微指头穿模会漏过去，毒害 VLA 监督。
- **相机运动下的光照一致性** —— 全局光照漂移，是"没有场景表示、只有视频先验"的标志。
- **Action-conditioning fidelity** —— 渲染出来的手并未精确跟随显式的末端轨迹。这是与 Genie 的差距。

心智模型：**Cosmos-Predict 是带机器人 domain 先验的视频模型，不是带视频输出的机器人模型**。Cosmos-Reason 之所以存在，*正是因为*生成器单独不可信。

### 4.x · Hidden Assumptions

哪些上游承诺被违反时，Cosmos 反而成有害源：

- **sim2real gap 由外观主导** —— tabletop pick / pour 上成立，contact-rich 装配上不成立。
- **Cosmos-Reason 的训练分布覆盖你的物理 regime** —— 对 deformable / granular / fluid 超出其见过的 mix 不成立。
- **你有 Isaac（或类似）源管线** —— Cosmos-Transfer 需要 depth + seg 输入；纯 RGB 拍摄不解锁。
- **能负担在你的 wrist-cam 分布上做 domain finetune** —— 开箱 Cosmos 通用，遇到新摄像头会退化。
- **VLA 能容忍 ≤20% 噪声监督** —— Cosmos-Reason 抓粗违反，不抓细指穿模；脆弱策略会被放大。

任一被违反，预期**静默失败** —— Cosmos rollout 在人眼里没毛病，却暗中毒害策略训练。

### 4.y · GitHub 实地失败（atlas 联动）

- **GitHub-validated**：原 `NVIDIA/Cosmos` 8096★ monolithic repo 已被 issue #167 *"Deprecate codebase"* 合并后正式 deprecate，生态拆到 `nvidia-cosmos/` org 14+ 子库；**"git clone 一份跑通"路径已死**，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。读者必须立刻迁移到 `cosmos-predict2.5` + `cosmos-transfer2.5` + `cosmos-rl` + `cosmos-curate` 四个活子库的拼装。
- **GitHub-validated**：predict1 / reason1 / transfer1 / predict2 都已被 2.5 替代而进入 📖 历史态；任何引用旧子库的教程或论文 baseline 都要核对版本号，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**"Cosmos-trained VLA improves task X by Y" 至今无独立第三方验证** — 本 lane 最大未解问，社区欠这个数；任何论文报"Cosmos 数据 improves VLA"没有 baseline ablation 都该严审，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。

**Interview Tip**：被问 Cosmos 时，答"数据工厂，不是规划器——而且只对外观瓶颈任务有效；动力学 gap 不变"。这一区分把读懂方法的工程师和读营销的人分开。

---

## 5 · Deployment patterns that ship today

1. **增广，不是替换**。在 Isaac + 真实 teleop + Cosmos rollout 的可量化 mix（如 60/30/10）里训。别替换真实数据。
2. **Cosmos-Transfer 优先于 Cosmos-Predict**。Transfer 受 sim 条件约束；底层物理仍来自 Isaac，比自由生成的 Predict 更可信。
3. **永远过门**。用 Cosmos-Reason 或手工物理过滤器；未过滤的 Predict 毒害 VLA 训练的速度比帮助快。
4. **必须做 domain finetune**。开箱 Cosmos 通用；只有在你机器人 wrist-camera 分布上微调过才有用。

---

## 6 · 2-year outlook + falsifiable prediction

预计到 **2027-06**，Cosmos-Transfer 会成为 manipulation VLA 论文里的标准步骤（像今天的 DR），出现显式 action-conditioning 的 Cosmos v2 缩小与 Genie 的差距，Cosmos-Reason 由 3D-aware critic 加强（Cosmos × 3DGS 混合是显然的下一步）。

**Falsifiable prediction:** 在 2027-12 之前，**不会有任何公开 manipulation VLA 报告 contact-rich benchmark（peg-in-hole、deformable 操作）上仅靠 Cosmos 增广就拿到 >15% 真实世界成功率提升**。收益落在外观瓶颈任务（杂乱桌面拾取、新纹理倾倒）上 3–10%。任何标题写 >20% 的应当下注反方。

- ✅ **VERIFIED 2026 GTC**: 预测 "explicit action-conditioning Cosmos v2" — **Cosmos-Policy** 已发布，是 world model post-training 为 VLA policy。完全符合预测方向（arXiv 2511.00062）。

---

## For the reader

- **Manipulation VLA team:** 你 ablation 表上多一个数据源。不要围绕它重组整个 stack。
- **Driving team:** DriveDreamer / GAIA-1 是更近的近亲。教训能迁，模型大概率不能。
- **Aerial / outdoor robot:** 2027 之前忽略——训练分布不覆盖你的 domain。
- **Researcher:** 开放问题是 **physics-grounded conditioning** —— 让可微物理 rollout 约束扩散采样器。明显桥接到 `foundations/physics/`。

---

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

原 `NVIDIA/Cosmos` monolithic repo（8096★）已 deprecate（#167），代碼拆到 `nvidia-cosmos/` org 下五個子庫。下表按子庫整理 2026-05 實地 issue tracker，凡引用「Cosmos repo」的舊教程 / 論文 baseline 都必須先確認指的是哪個 2.5 子庫。

### 8.1 · `cosmos-predict2.5` (1.2k★, 22 open issues) — video FM

| Issue | Theme | What it reveals |
|---|---|---|
| **#135** | RTX 5090 32GB VRAM CUDA OOM across text2world / image2world / video2world | 14B video2world **需 ~32.6GB VRAM**；32GB 消費卡仍 OOM。Datacenter-only baseline；`PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` 不解 |
| **#141** | "OOM while load the whole model" — limited capacity hardware | 證實 #135 不是 5090 個案；模型 footprint 對非 H100/A100 用戶 effectively 鎖死 |
| **#136** | Paper-code mismatch on rCM distillation | **論文 method ≠ 開源 code**；distillation pipeline reproduce 不出來——和 §4 「Cosmos 數據是否真帮 VLA」未解問同源 |
| **#134** | Missing eval script for action-conditioned post-training quantization | **沒有官方 eval harness** 衡量 quantized policy 性能——讀者要自己造 benchmark |
| **#143, #148, #144, #131** | FSDP shard size 1 bug / multi-batch autoview / multiview checkpoint / single-GPU validation 不一致 | Distributed-training paper code，single-node 場景一堆隱性 bug |
| **#142** | DGX Spark 兼容性 | 連 NVIDIA 自家新硬件都還沒適配齊 |
| **#124** | Text2World training 文檔缺口 | "How do I train this?" 仍是公開問題 |

**核心結論**：14B Predict-2 在 32GB 消費卡上**跑不起來**（#135/#141），這把「個人研究者用 Cosmos 增廣自己的 VLA dataset」路徑事實上鎖死到 H100/A100 用戶。§4.y 的「Cosmos 助 VLA」claim 因此**雙重難證**——既沒有 paper-code parity（#136），也沒有官方 eval harness（#134）。

### 8.2 · `cosmos-transfer2.5` (657★, ≥232 open issues) — sim→real bridge

| Issue | Theme | What it reveals |
|---|---|---|
| **#224** | "Low quality results using CARLA inputs for cosmos-transfer2.5 auto multiview" | **直接打臉 §3「Cosmos-Transfer 對 sim 資產 sim2real bridging」**——CARLA depth/seg 進 Transfer 出 garbage。讀者不要假設任意 sim source 自動工作 |
| **#209** | "Background lost during object editing when vace_has_mask is enabled" | Mask conditioning 漏背景——VLA wrist-cam augmentation 常用 mask，這是現役 bug |
| **#207** | "Support for frame-by-frame video generation with control inputs (closed-loop simulation)" | **closed-loop sim 還是 open feature request**，Transfer 今天只能 batch generate，不能 step-wise——與「rollout 引擎」幻想不符 |
| **#225** | Request for access to Cosmos-Transfer2.5-2B/robot/multiview-agibot weights | 部分 robot-specific weights **未公開**——Apache 2.0 不等於全 checkpoint 開放 |
| **#218** | 文檔 reference 未文檔化 env var for edge/distilled model | 蒸餾版本走後門 env var 開啟，未進文檔 |
| **#216, #212, #232** | Missing `VelocityPassthroughWrapper`, camera inference module ImportError, `cosmos-oss==0.1.0` vs workspace 1.5.0 衝突 | **基本 pip install 走不通**——code/dependency 還在 churn |
| **#221** | Prompt engineering for Real→Real augmentation | 沒有官方 cookbook；社區自己摸 |

**核心結論**：Transfer2.5 對 **CARLA-class sim assets 質量不保**（#224），closed-loop sim 不支持（#207），部分 robot weights 不開（#225）。§5 「Transfer 優先於 Predict」的建議仍成立，但**前提是你用 Isaac-class assets**——把任意 sim 餵進去等失敗。

### 8.3 · `cosmos-rl` (426★, ≥681 open issues) — RL post-training

| Issue | Theme | What it reveals |
|---|---|---|
| **#681** | `torch.distributed.DistNetworkError` client socket timeout 300000ms | RL training distributed setup 卡網路握手——個人 / 小團隊基礎設施門檻高 |
| **#672** | Shape mismatch when dim0 not divisible by global_rank_size | 對 batch / GPU 數有未文檔化整除約束 |
| **#642** | Tool to convert checkpoint internal format to HuggingFace format | **checkpoint 不可直接 HF inference**——deploy 要自己寫轉換 |
| **#526** | vLLM weight + kvcache offload for colocated-separated mode | 推理 stack 還在補基礎 RL 工具鏈 |
| **#475, #495, #534, #535, #547, #551, #552** | MoE token dispatcher decouple / reward service isolation / control flow overlap / rollout balance / controller backup / RDMA-NCCL / container hybrid launch | **本質上是分布式 RL 訓練框架在 build-out 階段**——不是 turnkey "post-train 你的 VLA" 工具 |

**核心結論**：`cosmos-rl` 是 NVIDIA 內部 large-scale RL training infra 開源，**不是面向 VLA practitioner 的 fine-tune kit**。§2 表格裡「Cosmos-Policy 在 LIBERO/RoboCasa SOTA」**沒有公開 reproduce path**——issue tracker 裡找不到「How to reproduce LIBERO numbers」對話，這對「world-model-as-policy 範式落地」的 claim 是負面信號。

### 8.4 · `cosmos-curate` (184★, 1 closed issue, 0 open) — data curation

唯一 surfaceable issue 是 **#4**（2025-09 closed）關於 `internvideo2_mm_config_model.json` 格式文檔。**Tracker 異常安靜**有兩種讀法：
- (a) 工具穩定到沒人遇到問題 — unlikely given 184★ 用戶 base；
- (b) **沒有人真在用** — 更可能；data curation 工作流通常各家自己寫，NVIDIA 的 curate pipeline 黏合度低。

任何引用「我們用 cosmos-curate 處理了 X 小時數據」的論文都該核對：他們是真用整條 pipeline，還是只 import 了一個 video tokenizer？

### 8.5 · `cosmos-reason2` (8 open issues) — 7B reasoning VLM

| Issue | Theme | What it reveals |
|---|---|---|
| **#52** | **無法 reproduce 官方 Cosmos-Reason2-2B 在 Physical AI Bench 結果**（~6 點 gap） | **官方 benchmark 數字第三方驗不出來**——這是 §4 「Reason 是承重判別器」的直接風險：critic 本身的 reasoning 都 reproduce 不出，怎麼信它 filter 你的 rollout？ |
| **#54** | Recurrent CUDA OOM during SFT of Cosmos-Reason2-32B | 32B 變體 fine-tune 對普通研究組不可及 |
| **#56** | Video data SFT in post-training tutorial 不清楚 | "如何在自己 video 上 fine-tune critic" 仍是 open question — §4.x hidden assumption 「Reason 訓練分布覆蓋你的物理 regime」必須走 fine-tune 才解，而 fine-tune 路徑 undocumented |
| **#37** | Vision Processor 把 `total_pixels` 誤當 `longest_edge` overflow | Tokenizer 配置 silent bug——影響任何 high-resolution wrist-cam 輸入 |
| **#38, #41** | Cosmos-RL 集成問題 / "Put it in a virtual simulator" | 跨子庫拼裝（Reason × RL × sim）社區自己摸 |
| **#51, #53** | Bounding box prediction reliability / AV sector capability | Critic 在 detection / domain-specific 上限未知 |

**核心結論**：**Cosmos-Reason2 官方數字 reproduce 不出（#52）** 是本批 deep dive 最尖銳的發現——它直接動搖 §4 「Reason 當 critic 過濾物理違規片段」的可信度。如果第三方驗證者拿不到 paper 數字，那「Reason filter 出來的 rollout 真乾淨」這個 §5 deployment pattern #3 的承諾無從審計。

### 8.6 · 跨庫遷移（從舊 `NVIDIA/Cosmos` 到 `nvidia-cosmos/*`）

讀者要記三條：

1. **舊 8096★ repo 已死**（issue #167）— 任何 `git clone NVIDIA/Cosmos` 教程 / Colab 失效；遷移到 5 子庫拼裝。
2. **predict1 / reason1 / transfer1 / predict2 都已被 2.5 替代** — 任何 baseline ablation 引用 v1 / v2 數字必須註明，2.5 在 architecture 上不同（per **#136** 連 2.5 paper-code 都 mismatch，跨 major 版本可比性更弱）。
3. **Apache 2.0 commercial use 形式上允許**，但 **#225** 顯示部分 robot-tuned weights（multiview-agibot 等）**未公開**——商用前要逐 model card 核對 license + 權重可用性，不能假設「Apache → 全部可用」。

### 8.7 · 「Cosmos-Policy 在 LIBERO/RoboCasa SOTA」claim 的 GitHub 驗證狀態

§2 表格列出 **Cosmos-Policy** 作 "post-trained world model as policy，LIBERO/RoboCasa SOTA"。GitHub 實地查證：

- **無獨立 `nvidia-cosmos/cosmos-policy` repo 存在於 2026-05**（5 個子庫均不直接以 Policy 命名）；Policy 訓練應走 `cosmos-rl` post-training pipeline。
- `cosmos-rl` issue tracker **無 LIBERO / RoboCasa 復現討論線索**——arXiv 2511.00062 報的 SOTA 數字目前**只有 NVIDIA 內部 reproduce path**。
- §4.y "Cosmos-trained VLA improves task X by Y 至今無獨立第三方驗證" — 本 deep dive **再次確認**，且把範圍從「Predict 數據增廣助 VLA」擴到「Policy 本身作為 VLA」。

**Interview Tip 升級**：被問 Cosmos-Policy LIBERO SOTA 時，先答「arXiv 報過，獨立復現尚無；`cosmos-rl` issue tracker 沒有 reproduce 對話」——這把跟蹤論文與跟蹤工程現實的人分開。

---

## References

- NVIDIA Cosmos announcement — CES 2025 keynote. https://www.nvidia.com/en-us/ai/cosmos/
- Cosmos technical report — arXiv 2511.00062, 2025.
- **Cosmos World Models (technical report)** — NVIDIA GTC 2026 · [arXiv 2511.00062](https://arxiv.org/abs/2511.00062)
- **Cosmos org GitHub** — [nvidia-cosmos](https://github.com/nvidia-cosmos)
- Isaac Sim / Isaac Lab — https://developer.nvidia.com/isaac/sim
- DriveDreamer (sibling driving line) — Wang et al. [arXiv link TBD]
- GAIA-1 (Wayve, contrast case for driving) — Hu et al. *arXiv 2309.17080*

## Boundary

本文把 Cosmos 解构为**具身策略训练的数据工厂**。消费 / 创意视频用例按 lane PRD 划在范围外。跨家族对比归 `crossing/representation-migration/world-models-as-data-vs-planner.md`（TBD）。VLA 侧关于"Cosmos 数据是否真帮我的策略"的测量归 `bridge-to-vla/cosmos-augmented-vla-training.md`（TBD）。

---

*Last opinion update: 2026-05-21.*
