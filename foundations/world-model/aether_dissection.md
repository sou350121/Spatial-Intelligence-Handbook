<!-- ontology-5axis
problem: Unified world model (4D recon + action-conditioned video + planning)
representation: 4D point cloud + video latent + action trajectory
sensor: Multi-view RGB (training pure synthetic, zero-shot transfer claim)
paradigm: Generative-VideoWorldModel + geometry-aware (diffusion transformer with 3D state)
time: Online rollout (sample-step iterative)
ref: ../../cheat-sheet/ontology.md §5.3
-->

# Aether 解构 (Aether: Geometric-Aware Unified World Modeling — Dissection)

> **发布时间**: arXiv 2025-03-24 (v1) → ICCV 2025 Outstanding Paper（RIWM workshop track）
> **论文 / 模型**: Aether — Zhu, Wang, Zhou et al. (OpenRobotLab → InternRobotics), [arXiv 2503.18945](https://arxiv.org/abs/2503.18945)
> **核心定位**: 把"生成式视频世界模型"（Sora / Cosmos / Genie 谱系）与"前馈 3D 重建"（DUSt3R / VGGT 谱系）**合在同一个 diffusion transformer 里**——一个 net 同时吐 RGB 视频 + 深度 + 相机轨迹，三模式（4D 重建 / 动作条件预测 / 目标条件规划）由输入 mask 切换。

Aether 不是 Cosmos 那种"数据工厂"——它的赌注是**几何不是 critic，几何是主模态**：把深度、相机射线 (raymap) 与 RGB 一起当 latent，让生成器在 4D 状态下采样。代价：纯合成数据训出来的 model 是否真的 zero-shot 扛得住真实手腕相机的 OOD，目前**全靠论文 benchmark + 第三方 community 复现**——尚无任何机器人产品报"我们部署了 Aether"。

**Status:** v1.0 — initial dissection 2026-05-24. 14-item template. ICCV Outstanding 标牌仍待时间检验；所有"unified 比 specialist 更好"的承诺都标 `UNVERIFIED`。
**Wedge tier:** W2 · 🔬 [WorldModel] 🌐
**TL;DR:** 头一个**形式上**把 generative-video lineage（Sora → Cosmos）与 feed-forward-3D lineage（DUSt3R → VGGT）合流的 world model：CogVideoX-5B-I2V 初始化 + 加 depth latent + raymap action latent，靠 task-interleaved masking 一口气训 4D 重建 / video prediction / visual planning 三任务。纯合成数据（DA-V / The-Matrix），claim zero-shot 真实迁移。**关键未解问**：unified 训练是否真的产生 §7.1 "synergistic knowledge sharing"，还是只是 multi-task 让每个任务都比 specialist 略弱的妥协。

### X-Ray (non-expert friendly)

(a) 现有 world model 两派井水不犯河水——**生成派**（Sora / Cosmos / Genie）出漂亮 RGB 视频但没几何，**重建派**（DUSt3R / VGGT）出 point cloud 但不会预测未来。(b) Aether 把两派的输出都塞进同一个 diffusion transformer 的 latent：RGB tokens + depth tokens + 相机射线 tokens 并列，训练时随机 mask 不同子集 → 同一个网三种任务：mask 输入就是重建，mask 未来帧就是预测，mask 中间帧就是规划。(c) 对空间 AI 工程师：把它当 **2025 年的"几何感知 world model proof of concept"**——值得读论文了解 raymap-as-action 这个表示，但还**别拿它当产品组件**；纯合成训练的 zero-shot claim 是论文的中心赌注，需要第三方独立复现验证。

### 📍 Research Landscape Timeline

```
                          generative video lineage
                                    │
   Sora 2024 ─► Cosmos CES 2025 ─► Genie 2 2024 ─► Genie 3 2025
                                    │
                                    ▼
                          ★ Aether ICCV 2025 Outstanding ─► ?
                                    ▲
                                    │
   DUSt3R 2024 ─► VGGT CVPR 2025 ─► MapAnything 2025
                          feed-forward 3D lineage
```

Aether 是这两条独立演化谱系的**第一个正式 convergence 点**——之前的 Cosmos 用 Cosmos-Reason 当 3D-aware critic（外挂），Aether 把 3D **直接作为 latent 主模态**（内嵌）。ICCV 2025 Outstanding Paper 是 peer recognition 信号，但**工程现实如何 24-36 个月后才知道**。

---

## 1 · Why this question matters

`foundations/world-model/` 里的核心未解问是"world model 该长什么样？"。两条已有路：

- **Cosmos 路（外挂几何）**：video FM 主导，VLM critic 过滤违反物理片段。Aether 论文§4 的反驳：critic 只能事后筛，无法事前约束生成轨迹。
- **VGGT 路（无生成）**：feed-forward 几何 SOTA，但不预测未来帧，无法当 planner 用。

Aether 想走第三条：**让生成器在 4D 状态空间里采样**。这是有意义的研究问题，因为它**形式上**给了一个统一答案。**但形式正确 ≠ 工程正确**——纯合成训练的 zero-shot 边界、unified vs specialist 的 trade-off、84 GPU·week 训练成本能否被普通研究组复现，都是 open question。

Aether 落在 `foundations/world-model/` 而非 `foundations/feed-forward-3d/`，是因为它的**主要 wedge 是"world model"那个槽位**——它的 4D 重建只是副产品，论文重点是 video prediction + visual planning 两个生成任务。

---

## 2 · Model family architecture

> 📌 **Napkin Formula**: `Aether ≈ CogVideoX-5B-I2V (init) + [RGB | depth | raymap] latent triplet + task-interleaved masking`。**三个模态并列做 diffusion，不是三个模型串联**——这是与 Cosmos 的本质差别。

模型基础（参数 `UNVERIFIED` 精确数字，约 5B 量级）：

| 组件 | 选择 | 备注 |
|---|---|---|
| **Backbone** | CogVideoX-5B-I2V 预训练权重初始化 | 排除新加的 input/output projection channels |
| **Latent triplet** | (RGB 视频 `zc₀`, 深度 `zd₀`, 相机射线 `za₀`) | 三者**并列**进同一个 diffusion transformer |
| **Depth representation** | normalized disparity = reciprocal(sqrt(depth)) | scale-invariant；论文 §3.2 |
| **Action representation** | raymap：每像素 6 通道（3 ray direction + 3 ray origin）| 把相机轨迹**像素化**为图像格式输入 |
| **训练 stage 1** | latent space MSE (标准 diffusion loss) | |
| **训练 stage 2** | image space refinement = MS-SSIM + scale-invariant depth loss + pointmap loss | |
| **训练计算** | 80× A100-80GB，effective batch=320，~2 weeks | ~160 GPU·week 量级；非小团队可复现 |
| **训练数据** | DA-V + The-Matrix（**纯合成 4D**）| zero-shot real-world 是论文中心赌注 |

**三模式切换 = 输入 mask 切换**（论文 §3.3）：

| 概率 | Mask 策略 | 解锁的任务 |
|---|---|---|
| 30% | mask 观测帧 + 目标帧 | visual planning（goal-conditioned） |
| 40% | mask 观测帧（保留目标） | action-conditioned video prediction |
| 28% | mask 全部 RGB 通道 | 4D dynamic reconstruction（depth + camera only） |
| 2% | mask 全部 color condition | 退化对照 |

Action latent（raymap）**单独**以 50% 概率独立 mask，让模型同时学到 action-conditioned 与 action-free rollout。

> ⚡ **Eureka Moment**: **raymap-as-action**——把"相机往哪走"编码成一张和 RGB 同分辨率的 6 通道图，与 RGB / depth latent 并列进 diffusion transformer。这把"动作"从语言条件 / 离散 token 重新定义为**像素级几何信号**，跟生成器的 inductive bias（卷积/attention over spatial grids）天然匹配。这是 Aether 与 Cosmos 用 text+first-frame 当 conditioning 的最大表示差别。

### 2.5 · Worked example — 5 秒手腕相机预测

设你有：手腕相机 1 帧观测（480×720 RGB）+ 期望的 5 秒末端轨迹（→ 转 raymap 序列）。Aether action-conditioned prediction 流程：

1. **Encode**：RGB → `zc₀`（CogVideoX VAE），future depth slot 全 zero（要生成的），raymap 序列直接 token 化（已知）。
2. **Mask 配置**：observation RGB 保留，future RGB+depth 全 mask；raymap 全保留 → 触发 "action-conditioned video prediction" 模式。
3. **Diffusion sampling**：A100-80GB 上 ~分钟级（精确 `UNVERIFIED`，论文未给单次 inference latency）；输出 RGB 序列 + depth 序列 + 一致的 pointmap。
4. **下游用法**：
   - RGB 序列：用于 visual servoing 监督 / VLA imitation supervision；
   - depth 序列：用于 collision check / 障碍预测；
   - pointmap：可直接进 SLAM 后端做 dense mapping。

**预期质量**（基于论文 §4 + 报告 limitation）：
- 静态家居场景，已知物体 → 看起来合理（VBench-style 评分高）；
- 接触密集场景（peg-in-hole / 软体）→ 与 Cosmos 同病：像素合理但 contact dynamics 漂；
- 5 秒以上 → 长时漂移 + 相机姿态不稳定（论文 README 自己列的限制）。

**真机部署 delta vs Cosmos**：未知（`UNVERIFIED`）。**两者目前都没有第三方独立 VLA-improvement 复现**。

---

## 3 · Where it actually helps (vs where it's just expensive generation)

| Scenario | Helps? | Why |
|---|---|---|
| **学术 benchmark：depth + camera + video joint task** | ✅ likely | 论文 §4 报 multiple zero-shot benchmark（Sintel/KITTI/ScanNet/TUM-RGBD 量级）competitive with specialists |
| **静态家居 wrist-cam 5 秒以内预测** | ⚠️ partial | 论文 demo 看起来合理；但 vs Cosmos 没第三方对比 |
| **goal-conditioned visual planning（短时）** | ⚠️ partial | 这是 Aether vs Cosmos 的差异化卖点；real-robot 验证缺失 |
| **作为 VLA 训练数据增广源** | ❌ doubtful (now) | Cosmos 上同问题已被 §4.y 证未独立复现；Aether 处境更差（更新、用户基数小） |
| **生产部署组件（任意场景）** | ❌ no (now) | A100-80GB 推理；社区零部署报告；🔬 research-only |
| **接触密集 / 软体 / 流体物理预测** | ❌ no | 与 Cosmos 共享根因——纯视觉训练学不到接触动力学 |
| **长 horizon (>10s)** | ❌ no | 论文 README 自陈相机姿态会漂 |

读这张表的方式：**Aether 是"world model 形式化的研究里程碑"而非"今天能用的工具"**。如果你写 survey / 拿来证明"generative 与 reconstruction 在 2025 已 convergence"——它配。如果你想训 VLA 或部署 planner——目前**优先级低于** Isaac Sim + DR + （如果买得起）Cosmos-Transfer 数据增广。

---

## 4 · Where it breaks

论文自陈 + 可推导失败模式（严重度 `UNVERIFIED`）：

- **长时相机姿态漂移**：论文 README "struggles with camera pose instability in certain conditions"；典型 generative-video 病，未解。
- **动态场景退化**：README "struggles with dynamic scenarios"——这与 4D recon 的 motion-mask 训练数据偏向静态背景有关。
- **观测与目标差距大时 planning 退化**：论文承认 goal 在 frame 视野外或场景外时 visual planning 不可用。
- **纯合成训练的隐性 OOD 盲区**：DA-V + The-Matrix 的物理/光照/材质分布有边界，真实手腕相机的镜头畸变、运动模糊、低光场景未必覆盖。论文 zero-shot benchmark 仍在**学术 dataset**（多为接近合成域），**非机器人 wrist-cam 真实部署**。
- **5B 参数 + A100-80GB 推理门槛**：与 Cosmos-Predict-2 14B 同病（详见 `nvidia_cosmos_dissection.md` §8.1 #135）——个人研究者用消费 GPU 跑不动。Aether 5B 比 14B 小，门槛低一档，但仍非 24GB 卡可及。
- **Unified 训练的隐性 trade-off**：论文未给"Aether 单任务训练 vs 联合训练"的 ablation，因此**"task-interleaved feature learning 真的协同"是 unverified 主张**——可能 unified 模型在每个单任务上都比 specialist 略弱，作为代价换来 multi-modal 统一形式。

心智模型：**Aether 是 representation thesis，不是 deployment claim**——核心贡献是"raymap + depth + RGB 并列 latent 这套形式"，至于这套形式训出来的模型在真实任务上的端到端胜率，**论文未证明，社区未复现**。

### 4.x · Hidden Assumptions

哪些上游承诺被违反时，Aether 的形式优雅就变现为产品风险：

- **synthetic-to-real gap 由几何精度主导，不是材质/光照/动力学** —— Aether 把几何当主模态的赌注。若你的下游任务 sim2real 失败原因是接触摩擦或表面材质，几何对齐再准也救不了。
- **CogVideoX-5B 的预训练分布覆盖你的 domain** —— Aether 是 fine-tune 不是 from scratch。CogVideoX-I2V 训练数据偏 web video / 通用场景，机器人 wrist-cam 视角并非其强项。
- **DA-V + The-Matrix 的合成 4D 分布有可迁移结构** —— 这是论文 zero-shot claim 的根基。若你的真实场景物理 regime（如水下、空气湍流、软体）超出训练 distribution，zero-shot 静默退化。
- **你能负担 A100-80GB 推理** —— 不能则 Aether 在你的 stack 里**不可达**。
- **goal-conditioned planning 的 goal frame 在 observation 时空连续可达** —— 论文 README 自陈 distant goal 失效，意味着 Aether 不是 long-horizon planner，只是短程局部 trajectory 生成器。
- **"unified > specialist" 的隐性主张为真** —— 论文未做 controlled ablation 证明。若你用 Aether 替代专用 depth/VGGT/Sora，可能每一项都略弱。

任一被违反，预期**形式美但实际无用**——论文上看合理，部署后效果不及"用专用工具拼"。

### 4.y · GitHub 实地失败（atlas 联动）

- **GitHub-validated**：repo 在 2025 年从 `OpenRobotLab/Aether` 迁移到 `InternRobotics/Aether`（项目组织重命名/合并），**两个 URL 当前都 resolve 但官方 README 指向 InternRobotics**——任何引用旧 OpenRobotLab URL 的教程/论文需核对。详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：repo 显示 ~595★ / open issues = 0（2026-05 实地查证）。Issue tracker 异常安静**两种解读**：(a) 工具稳定零 bug——unlikely given 5B model 复杂度；(b) **没有人真在严肃用它**——更可能，因为 (1) A100-80GB 推理门槛劝退社区，(2) ICCV 2025 Outstanding 标牌带来"被引"而非"被用"。
- **GitHub-validated**：**至今无任何独立第三方报告"用 Aether 训出/部署了机器人 policy"**——与 Cosmos §4.y 同等空白，但 Aether 更新、用户基数更小，复现尚未发生。这与 ICCV Outstanding 标牌的 implication 形成张力：**peer review 认可的论文 ≠ 工程现实落地**。详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **未验证主张警告**：论文 zero-shot benchmark 数字（depth Abs Rel / δ<1.25 vs DUSt3R/MASt3R/MonST3R/VGGT 等）在 issue tracker 内**无第三方复现讨论线索**。与 Cosmos-Reason2 #52（官方数字第三方验不出）同等风险——peer-reviewed 不保证可复现。

**Interview Tip**：被问 Aether 时，答"ICCV 2025 Outstanding 的形式化里程碑——把 generative-video 与 feed-forward-3D 两条谱系第一次合流，靠 raymap-as-action 这个表示创新；但 (a) 纯合成训练 zero-shot 真实迁移的端到端验证缺失，(b) 第三方独立复现/部署报告为零，(c) A100-80GB 推理门槛让社区试不动。读论文学表示设计，别拿它当今天能落地的组件"。这把"读 paper 拿奖"与"用 paper 干活"两群人分开。

---

## 5 · Deployment patterns that ship today

**目前没有**。这一节对 Aether 是诚实空白，与 Cosmos 形成对比（Cosmos §5 有"数据工厂"模式可言）：

- **研究复现 / 论文 baseline 引用**：是 Aether 当前最可行的"使用"模式——下载 HuggingFace `AetherWorldModel/AetherV1` checkpoint，在 A100-80GB 上跑 inference demo，引用论文。
- **教学 / 表示设计参考**：raymap-as-action 这个 trick 值得任何在做 video-as-action 表示的研究组借鉴。
- **VLA 训练数据增广**：理论可行（与 Cosmos 同模式），实际**不建议作为主路径**——已有 Cosmos 这条更成熟的数据工厂，Aether 没有差异化优势可证。
- **机器人 planner**：**禁用**——论文自陈 distant goal 失效 + camera pose 漂移，目前**不适合任何真实闭环控制**。

如果你正在搭 manipulation VLA 数据 pipeline 且预算无限，可以把 Aether 当一个 ablation 数据源（与 Isaac、Cosmos、真实 teleop 并列），测一个 70/20/8/2 mix vs 不加 Aether 的 baseline。**但在第三方独立复现出现之前，不要把 Aether 作为依赖路径**。

---

## 6 · 2-year outlook + falsifiable prediction

预计到 **2028-05**：

- **正向**：raymap-as-action 这个表示会被其他 world model 采纳（Cosmos v3 / Genie 4 加 explicit geometry channel 的概率高）。"几何 + 生成 unified" 范式会成为主流写法，Aether 是先驱论文。
- **负向**：Aether 这个 specific 模型本身**不会**成为 production 组件——会被同组或继任组的更大模型（Aether-2 / 加 IsaacGym 物理 prior 的衍生）替代。ICCV Outstanding 的奖项更多是 "method 方向对" 的认证，不是 "这个 model 能用" 的认证。
- **关键中间态**：2026-12 之前应出现至少一篇独立第三方报告"用 Aether 训了 VLA / 复现了论文 zero-shot 数字"。如果到时仍没有，Aether 会被归入"被引但没人用"的 Outstanding Paper（与 Cosmos `nvidia-cosmos/cosmos-policy` LIBERO claim 状态一致）。

**Falsifiable prediction**：在 **2027-12 之前**：

1. **不会**有任何公开 manipulation VLA 论文报告"仅用 Aether rollout 数据（不混 Cosmos / Isaac）就在 LIBERO / RoboCasa / Calvin 任一 benchmark 超过 SOTA baseline > 5%"。任何标题写 > 10% 的应当下注反方。
2. **不会**有任何 ROS 包 / 机器人 SDK 把 Aether 作为 planner 后端集成（vs Cosmos-Predict 已被部分 sim2real pipeline 引用）。
3. **会**有 ≥ 3 篇后续论文显式 cite Aether 的 raymap-as-action 表示并采用——representation contribution 会"赢"，model artifact 会"输"。

---

## For the reader

- **World model researcher：** 读论文 §3 关于 raymap + depth + RGB latent triplet 的设计——这是 2025-2026 representation 设计的参考案例。考虑借鉴而非整体复用。
- **VLA / manipulation team：** 不要把 Aether 作为依赖；它还在 🔬 阶段。Cosmos 数据工厂路径目前更成熟（虽然两者都未独立第三方复现）。
- **Feed-forward-3D team：** Aether 把 VGGT 路线的几何 backbone 想法**反向**注入 generative video——你们的下一篇可以反过来：把 generative video 的 temporal prior 注入 VGGT，看是否能解决 VGGT 的 single-pass 时序失忆问题。明显桥接到 `feed-forward-3d/vggt_cvpr2025_dissection.md`。
- **机器人产品工程师：** **2026 不要上 Aether**——A100-80GB 推理门槛 + 零部署 case study + 5B 参数推理延迟，全部劝退。等 2027 看是否有独立复现 + 蒸馏版本出现。

---

## 7 · 跨 dissection 对比 — Aether vs Cosmos vs Genie vs VGGT

| 维度 | **Aether** | **Cosmos** | **Genie 2/3** | **VGGT** |
|---|---|---|---|---|
| 主任务 | 4D recon + action-cond video + planning | conditional video synthesis (data factory) | action-conditioned interactive world | feed-forward 3D from N images |
| 几何处理 | **主模态**（depth + raymap latent） | critic（Cosmos-Reason 外挂） | 无显式几何 | **主输出**（pointmap） |
| 时序 | online rollout（多步采样） | online rollout（多步采样） | online interactive rollout | feed-forward 单次 |
| 训练数据 | 纯合成（DA-V + The-Matrix） | 真实 video + Isaac sim | 真实 game video + simulated | 真实 + 合成 mix |
| 参数量 | ~5B | 2B / 14B / 7B (family) | closed-source | ~1.4B |
| 推理硬件 | A100-80GB | H100/A100（14B），消费卡 OOM | 闭源 | 消费 GPU 可达 |
| 开源 | ✅ MIT | ✅ Apache 2.0（部分 weights 不开） | ❌ DeepMind 闭源 | ✅ |
| TRL | 🔬 research-only | 🔧 pilot（数据工厂） / 🔬（policy） | 🔬 | 🔬 → 🔧 trending |
| 第三方独立复现 | ❌ none | ❌ none（Cosmos-Reason2 #52） | ❌ closed | ✅ partial（社区跑过） |

读这张表的方式：**Aether 是"几何派 + 生成派的形式 convergence"，Cosmos 是"生成派的工程落地尝试"，Genie 是"交互生成的闭源前沿"，VGGT 是"几何派的当下 SOTA"**。四者解决不同子问题，**短期不互相替代，长期会被一个胜出的统一框架吞并**——Aether 的赌注是它就是那个框架，但工程现实远未到。

---

## References

- **Aether paper** — Zhu et al. *Aether: Geometric-Aware Unified World Modeling*. [arXiv 2503.18945](https://arxiv.org/abs/2503.18945). ICCV 2025 (RIWM Outstanding Paper).
- **Aether ICCV PDF** — [openaccess.thecvf.com/.../Zhu_Aether_..._ICCV_2025_paper.pdf](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhu_Aether_Geometric-Aware_Unified_World_Modeling_ICCV_2025_paper.pdf)
- **Project page** — https://aether-world.github.io/
- **Code (current)** — https://github.com/InternRobotics/Aether
- **Code (legacy URL)** — https://github.com/OpenRobotLab/Aether （redirects；ICCV reference 仍引此）
- **HuggingFace checkpoints** — `AetherWorldModel/AetherV1`
- **CogVideoX (base model)** — Yang et al. 2024. arXiv 2408.06072.
- **DA-V dataset** — DepthAnyVideo (synthetic depth source).
- **The-Matrix dataset** — synthetic 4D source referenced in Aether §3.
- **Companion dissections** — [`nvidia_cosmos_dissection.md`](./nvidia_cosmos_dissection.md), [`genie_dissection.md`](./genie_dissection.md), [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)
- **Ontology entry** — [`../../cheat-sheet/ontology.md`](../../cheat-sheet/ontology.md) §5.3 (World Foundation Models subsection)

## Boundary

本文把 Aether 解构为**representation-thesis 论文**——核心贡献在 latent triplet (RGB + depth + raymap) 与 task-interleaved masking 的形式设计，不在端到端机器人部署证据。VLA 侧"Aether 数据是否真帮策略"归 `bridge-to-vla/aether-augmented-vla-training.md`（TBD，与 Cosmos 平行）。与 Cosmos / Genie / VGGT 的跨家族技术对比扩展归 `crossing/representation-migration/world-models-geometric-vs-generative.md`（TBD）。Aether 在 InternRobotics 后续工作中的演化（Aether-2 等若出现）将另开 dissection。

---

*Last opinion update: 2026-05-24.*
