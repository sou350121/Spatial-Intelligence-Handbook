# Cross-Zone Failure Atlas (跨 zone 失败模式全景图)

> **类型**: cheat-sheet 元总结（非 dissection；不走 14 项门槛）
> **聚焦**: 把 10 个 zone 的 `github_failure_atlas.md`（共扫 42 个工具的 issue + PR）压成一张可用的全景图
> **核心定位**: 各 zone atlas 是垂直的"这个工具哪儿坏"；本图谱是水平的"跨 zone 反复出现的同一种坏法"

**Snapshot: 2026-05-22** — 数据来源：10 个 zone atlas × 42 个工具 GitHub 扫描（issue/PR/momentum 截止 2026-05-21）。

---

## TL;DR (5 行)

1. **NVIDIA Cosmos 原 monolithic repo 已 deprecate**（issue #167），生态拆 14 个子库；旧 `NVIDIA/Cosmos` clone 即走错路。
2. **multinerf 在 2025-02-11 被 Google 主动 archived**，NeRF 谱系最后的高质量参考实现进入只读。
3. **DUSt3R / MASt3R 在 2025-Q3 起 issue 增速断崖** — 论文还热，repo 已被 Naver 自己的后继工作（Pow3R / MUSt3R）吞并。
4. **SAM 3D Objects 6 个月 6665★ 但 103 open issues** — demo ≠ deploy：白纸上 pose 飞、与 depth/mask 不对齐。
5. **VINS-Fusion #3 "global optimization thread doesn't work" 自 2019 仍 open** — 论文卖点 loop closure built-in 六年没人修。

---

## Pattern 1-5: 跨 zone 反复出现的失败模式

| # | Pattern | 表征 | 跨 zone 例证 |
|---|---|---|---|
| **1** | **输出契约误解** (Output Contract) | 用户把 relative depth / affine-invariant point map 当 metric 读 | depth-foundation ~40%：DA v2 #93 #178（disparity 当米）/ DA3 #244 metric 错 / Metric3D #38 ~330% 偏差 / MoGe #75 #43 真实 metric 错；FF-3D VGGT #471（scale ambiguity）；semantic-3D SAM-3D #57（canonical vs metric） |
| **2** | **输入资产门槛** (Input Asset) | 模型假设用户提供完美初始输入（mesh / mask / 内参 / 标定） | pose ~30%：FoundationPose #83 #60 #32（要 CAD mesh）/ MegaPose #58（PNG mesh）/ CoTracker grid 起点 / SAM2 first-frame mask；classical-slam Kalibr #756 #768（IMU-cam 外参跑飞，6-DoF 激发不足）；aerial-vio Kalibr 流程缺失 → init 不收敛 |
| **3** | **closed-without-fix** (issue 标 closed 根因未解) | 评论几十条但 maintainer 没诊断就关掉 | depth FoundationStereo #121（静止物体头部对齐身体散开，closed）；pose FoundationPose #53（NaN scores 27 评论，closed 但无 GPU 兼容矩阵）；classical-slam ORB-SLAM3 #1001 用户直呼 "worst repository"；3DGS multinerf #156（JAX 升级 closed 无修） |
| **4** | **用户多 ≠ 维护强** (popular but unmaintained) | star/issue 量大但 maintainer 几年不出现 | classical-slam ORB-SLAM3 568 open issues ≈ DSO+LSD+maplab 之和，maintainer 回复率最低，最近 push 2024-07；aerial-vio VINS-Fusion 211 open + PR 几乎全 open，#5 自 2019；nerf-family bmild/nerf 117 open + spam #217 无人 triage；3DGS 4DGS 130 open + 多数空标题 |
| **5** | **demo ≠ deploy** (产品 momentum vs 真机崩溃) | 6 个月狂涨 star，但 issue 集中暴露架构级问题 | semantic-3D SAM-3D Objects 6665★/103 open（白纸 pose 飞 #149、不对齐 depth #162）；depth DA3 ★5326 但 #244 metric 错、#117 #136 3DGS export 训不动；world-model Cosmos 8096★ deprecate；vlm SpatialBot #21 left/right 反向 |

**额外发现 (Pattern 6, 浮现中)**: **谱系迁移信号** — 同一团队的后继工作吞并前作。Naver DUSt3R→MASt3R→Pow3R/MUSt3R；Google bmild/nerf→multinerf→archive；Princeton DROID-SLAM 重心已转 DUSt3R/VGGT；princeton-vl/RAFT 已被 SEA-RAFT 超越。**对读者**: 论文热度 ≠ repo 寿命，看作者是否还在原 repo 提交。

---

## Momentum 排行表 (跨 zone, 42 工具)

| 档位 | 含义 | 工具 |
|---|---|---|
| **🔥 Hot (爆发期, ★ 短期暴涨)** | 6 个月内 momentum 极强，issue 雪崩 | facebookresearch/sam2 (19204★/474 open)；facebookresearch/vggt (13.2k★/246)；ByteDance-Seed/Depth-Anything-3 (★5326, 2025-11 发布)；facebookresearch/sam-3d-objects (6665★/103) |
| **⚡ Active (官方持续维护)** | 近 6 月有 commit + issue 回复 | DepthAnything/Depth-Anything-V2 (★8149)；NVlabs/FoundationStereo (2706★)；NVlabs/FoundationPose (3213★)；microsoft/MoGe (2476★, v2)；facebookresearch/co-tracker (4955★)；facebookresearch/map-anything (3.4k★, Apache 2.0)；rpng/open_vins (2.9k★, 2025-11 push)；graphdeco-inria/gaussian-splatting (22k★/45 open PR)；nerfstudio-project/nerfstudio (11.6k★)；nvidia-cosmos/cosmos-predict2.5 (1212★, 2026-05)；nvidia-cosmos/cosmos-transfer2.5 (657★)；nvidia-cosmos/cosmos-rl (426★, 2026-05-20)；3DSRBench (benchmark 影响力大) |
| **🔧 Slow but alive (维护放缓, 算法成熟)** | 6-18 月仍有 commit 但节奏明显放慢 | minghanqin/LangSplat (1045★, 2025-10)；BAAI-DCAI/SpatialBot (344★, 2025-09)；autonomousvision/mip-splatting (1.4k★)；YvanYin/Metric3D (2195★, >1 年无 push)；NVlabs/instant-ngp (17.4k★, v2.0 2025-07)；ethz-asl/kalibr (5.4k★, 社区围 ROS 2)；princeton-vl/DROID-SLAM (2.6k★, 2025-05)；princeton-vl/RAFT (4035★, 2025-08)；naver/dust3r (7.1k★)；naver/mast3r (2.9k★)；nvidia-cosmos/cosmos-curate (184★)；nvidia-cosmos/cosmos-reason2 |
| **❌ Stale / Archived / 无 repo** | 已 archived / 1+ 年无 push / 完全闭源 | google-research/multinerf (3.8k★, archived 2025-02-11)；bmild/nerf (10.9k★, stale)；yenchenlin/nerf-pytorch (6.0k★, stale)；JakobEngel/dso (2.4k★, 2018 后冻结)；tum-vision/lsd_slam (2.7k★, 2014 后冻结)；ethz-asl/maplab (2.8k★, 2024-05)；UZ-SLAMLab/ORB_SLAM3 (8.6k★, frozen + 用户活跃)；HKUST-Aerial-Robotics/VINS-Mono (5.9k★)；HKUST-Aerial-Robotics/VINS-Fusion (4.5k★)；megapose6d (348★)；kerrj/lerf (727★, 2024-07)；pengsongyou/openscene (820★, 2023-10，OpenSeg ckpt 链接死)；hustvl/4DGaussians (3.6k★, 半弃养)；GS-SLAM 主仓 `UNVERIFIED`；NVIDIA/Cosmos (deprecate)；Google Genie (闭源)；World Labs Marble (产品)；SpatialVLM (无官方 repo) |
| **🦴 Release-and-forget (NEW v3.2)** | 開源但 maintainer 不回 issue / 0 closed | facebookresearch/vggt-omega (CVPR 2026 Oral, 15 open / **0 closed**, Multi-view fusion #17 / install #18 / HF access #26 全 unresolved)；wzzheng/StreamVGGT (913★, 25 open / **0 closed**, 1300 frame → >100GB GPU memory #24 不回應 8 月+) |

**惊讶**:
- **🔥 全部来自 Meta + ByteDance + NVlabs**；学术 lab 几乎没有 🔥 级工具。
- **❌ 占 42 个里近半数**（~20 个）—— spatial AI 生态的"基础设施层"半数已停摆。
- **🔧 + ❌ 合并占 ~70%** —— 这是个**工具半衰期 12-18 个月**的领域。

---

## Production Action Items

1. **Cosmos 用户立刻 migrate**: 从 `NVIDIA/Cosmos` 迁到 `nvidia-cosmos/{cosmos-predict2.5, cosmos-transfer2.5, cosmos-rl, cosmos-curate}` 四个活子库；旧 repo 已 deprecate via #167。
2. **OpenScene 用户立刻停用 / 找 mirror**: 上游 OpenSeg checkpoint 链接已 broken（OpenScene #97 #96 #95），整条管线不可复现；要么找 HF mirror，要么换 ODISE/SAM2 替换 OpenSeg feature。
3. **DUSt3R / MASt3R 商用决策点**: 这两个仍是 CC-BY-NC-SA 4.0；商用项目用 MapAnything (Apache 2.0) 或 VGGT-1B-Commercial checkpoint，不要赌 Naver 改 license。
4. **VINS-Fusion 不要指望官方修 loop closure**: PR #5 + issue #3 自 2019 仍 open；上 production aerial 选 OpenVINS（2025-11 仍 push, 维护活跃）。
5. **SAM 3D Objects 别用于 scene reconstruction**: 出的是**单物体** mesh + 6-DoF + canonical scale；下游要 metric depth 必须额外 scale alignment（#57）；白纸 / 弱纹理上 pose 飞（#149）。
6. **DA v2 / MoGe depth 不要直接做 grasp**: 输出是 affine-invariant 不是米；manipulation 切 Metric3D + in-house scale 校准 layer，或等 DA3 metric head 修复（#244）。
7. **FoundationStereo NaN 排查**: TensorRT fp16 NaN 是 flash_attn export 路径 bug（#49/#175/#58 同根）；deploy 前自跑 fp32 sanity check。
8. **ORB-SLAM3 production 用户**: 锁版本 fork + 自接 ROS 2 + 自接硬件 trigger（IMU-cam 时间同步）；不要等官方维护回归。
9. **NeRF 谱系收尾**: 新项目用 3DGS / VGGT / MapAnything；NeRF 留作教学 + 数学起点；不要再为 multinerf 补管线工具（archived 后没回报）。
10. **Windows / RTX 50 系列**: 3DGS / Instant-NGP / FoundationPose 都在新硬件 + 新 CUDA 路径上踩坑（3DGS #1313 RTX 50、Instant-NGP #1603 gcc 14、FoundationPose #27 RTX 4090）；预算"踩编译坑"时间或用 WSL2 / Docker。
11. **Release-and-forget 警告 (NEW v3.2)**: VGGT-Ω + StreamVGGT 都是 ICLR/CVPR 2026 重要 paper 但 maintainer 0 closed issue / 8 個月不回應。**用 streaming feed-forward 3D 直接看 follow-up**：OVGGT (O(1) constant memory) > XStreamVGGT (4.42× memory ↓ + 5.48× speedup) > FrameVGGT > STAC > StreamVGGT 原版（memory 災難 issue #24）。Production 候選看 closed issue 比例，不看 stars。

---

## Zone → Atlas → Key Finding lookup table

| Zone | Atlas 路径 | 最关键发现（一句话） |
|---|---|---|
| Feed-Forward 3D | [`feed-forward-3d/github_failure_atlas.md`](../foundations/feed-forward-3d/github_failure_atlas.md) | DUSt3R/MASt3R 2025-Q3 后被 Naver 自己后继吞并；momentum 在 Meta 三件套（VGGT / VGGT-Ω / MapAnything）+ NEW: StreamVGGT 系（StreamVGGT / XStreamVGGT / OVGGT / FrameVGGT / STAC）；**VGGT-Ω + StreamVGGT 兩個都 release-and-forget**（15/25 open issue 0 closed）；2026-05 update |
| 3DGS Family | [`3dgs-family/github_failure_atlas.md`](../foundations/3dgs-family/github_failure_atlas.md) | 原版 22k★ + 45 open PR + HIP/AMD 移植在动；衍生 4DGS / GS-SLAM 寿命 ~18 个月即半弃养 |
| NeRF Family | [`nerf-family/github_failure_atlas.md`](../foundations/nerf-family/github_failure_atlas.md) | multinerf 2025-02-11 被 Google archived；NeRF 时代标志日；Block-NeRF 公开实现 gap 仍空缺 |
| Classical SLAM | [`classical-slam/github_failure_atlas.md`](../foundations/classical-slam/github_failure_atlas.md) | 5/5 repo 官方 commit 1-2 年前；Kalibr 是事实标准但官方不接 ROS 2；ORB-SLAM3 用户多 ≠ 维护强典型 |
| Aerial VIO | [`aerial/vio/github_failure_atlas.md`](../embodiments/aerial/vio/github_failure_atlas.md) | OpenVINS 是 zone 唯一官方仍维护活跃；VINS-Fusion #3 loop closure bug 自 2019 open；DROID 5 Hz 不能做 aerial 实时 |
| Depth Foundation | [`depth-foundation/github_failure_atlas.md`](../foundations/depth-foundation/github_failure_atlas.md) | 5 仓 ~40% issue 是"输出契约没读懂"；全部缺 confidence map；FoundationStereo #121 closed-without-fix 典型 |
| Pose & Tracking | [`pose-tracking/github_failure_atlas.md`](../foundations/pose-tracking/github_failure_atlas.md) | 输入资产门槛是 #1 痛点（mesh/mask/grid 都得用户先提供）；SAM2 / CoTracker 缺 streaming memory API |
| VLM Spatial Reasoning | [`vlm-spatial-reasoning/github_failure_atlas.md`](../foundations/vlm-spatial-reasoning/github_failure_atlas.md) | 三条线只有 SpatialBot 给了能 clone 的 baseline；SpatialVLM 无官方 repo；3DSRBench 仅 benchmark 无训练 |
| Semantic 3D | [`semantic-3d/github_failure_atlas.md`](../foundations/semantic-3d/github_failure_atlas.md) | OpenScene 因外部 OpenSeg ckpt 链接死实质已死；SAM 3D Objects demo ≠ deploy；LangSplat "199× over LERF" 是 query 阶段口径错配 |
| World Model | [`world-model/github_failure_atlas.md`](../foundations/world-model/github_failure_atlas.md) | Cosmos 拆 14 子库（4 个活 / 10 个历史 + infra）；Genie 完全闭源；Marble 对机器人栈贡献近零；decision-useful 验证全社区都欠 |

---

## Boundary & For the reader

- 本文是 **2026-05-22 快照**；上述所有 momentum 标签会过期。`🔥` 工具半年后多半进 `⚡`，`⚡` 一年后多半进 `🔧`，spatial AI 工具半衰期 12-18 个月（NeRF / DUSt3R / RAFT 三个案例都已验证）。**建议 2026-Q4 重扫一次**。
- 本文**不替代**各 zone atlas — 它只浮现跨 zone 反复出现的规律。具体 issue # / PR / 维护者反应请回到对应 atlas（上表 lookup）。
- 本文**不涵盖** dissection 层细节（per-paper 14 项门槛）—— 那是各 zone 的 `*_dissection.md`。
- **关键限制**：所有 star / fork / push date 数字标 `UNVERIFIED`（未亲自跑 git 历史）；issue # 和 URL 是一手抓取，可信。
- **机器人 / VLA 工程师**: 把 Production Action Items 当 checklist 跑一遍，再决定栈。
- **学生 / 选题**: SpatialBot #21 viewpoint 翻转 study、Cosmos-trained VLA 独立验证、OpenScene + ODISE 替换、LangSplat root cause、FoundationStereo confidence head —— 每个都论文性强。
- **Reviewer**: 拒绝 "我们超过 X" 没有指出 X 的 repo 状态（archived / 闭源 / closed-without-fix）的论文。

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-22

[← Back to cheat-sheet](./)
