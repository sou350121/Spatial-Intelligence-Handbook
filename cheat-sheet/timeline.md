# Spatial AI Timeline 2020-2026

**Status:** v1 — opinionated draft。给出 arXiv ID 的已核对；venue / date 凡标 `UNVERIFIED` 者皆未确认。
**TL;DR:** 六年从 NeRF 到 VGGT 拿 CVPR best paper。主弧：per-scene 优化（NeRF 2020）→ 实时可微分渲染（3DGS 2023）→ 一次过前馈 3D（DUSt3R 2023 → VGGT 2025）。其他线（depth foundation models、world models、消费 AR）都横切这条主轴。

把本文当回到手册的索引地图。条目刻意保持单行 —— 深度在 `foundations/` / `crossing/` / `companies/`。

---

## ASCII 主轴

```
2020   2021   2022   2023   2024   2025   2026
  │      │      │      │      │      │      │
NeRF   DROID   DA-β   3DGS   DA-v2  VGGT   (consolidation)
  │      │      │      │      │      │
  │   COLMAP  Mip-    DUSt3R 4DGS   AVP
  │   +NeRF   NeRF    LERF   Genie  ships
  │           era            Cosmos π³
  │                          GS-SLAM       
  │
  前馈 3D 弧
  从这里起
```

主轴是 **per-scene → 实时 → 前馈**。横切线是 **depth foundation models**（DA 系）、**world models**（Genie、Cosmos、GAIA、Marble）、**消费 AR 试验场**（Vision Pro）。

---

## 2020 — 起点

| 发布 | 一行话：为什么重要 |
|---|---|
| **NeRF**（Mildenhall et al., ECCV 2020）— https://arxiv.org/abs/2003.08934 | 体渲染神经网络证明：单个 MLP 能从带位姿图像里编码 3D 场景。开启 per-scene 优化时代。 |
| **D-NeRF**（Pumarola et al.）— https://arxiv.org/abs/2011.13961 | 把 NeRF 延伸到动态场景；走向 4D 的第一条裂缝。 |

整个领域的现代弧都从 NeRF 下来。下游血脉见 `foundations/3dgs-family/`。

---

## 2021 — 管道成熟

| 发布 | 一行话 |
|---|---|
| **DROID-SLAM**（Teed & Deng, NeurIPS 2021）— https://arxiv.org/abs/2108.10869 | 学习式密集 bundle adjustment 在精度上匹敌经典 SLAM。这个架构模式四年后进入 VGGT。 |
| **COLMAP + NeRF workflow** 成熟 `UNVERIFIED — 无规范论文` | 事实上的「数据预处理」配方：COLMAP 出位姿、NeRF 渲染。两年内每篇 NeRF 论文都假设它。 |
| **Plenoxels**（Yu et al., CVPR 2022 但 2021 末 arXiv）— https://arxiv.org/abs/2112.05131 | 无 MLP 的体素网格神经场；比 NeRF 快 100×。3DGS「显式原语」哲学的先声。 |
| **Instant-NGP**（Müller et al., 2021 arXiv → SIGGRAPH 2022）— https://arxiv.org/abs/2201.05989 | Hash 编码 + 小 MLP；几秒训出一个 NeRF。把 NeRF 从「研究专属」推到「工程可部署」。 |

---

## 2022 — Depth foundation models 起头

| 发布 | 一行话 |
|---|---|
| **Mip-NeRF 360**（Barron et al., CVPR 2022）— https://arxiv.org/abs/2111.12077 | 无界场景 + 抗锯齿。设下 3DGS 必须翻越的质量线。 |
| **Depth Anything（β 血脉 / MiDaS v3）** `UNVERIFIED — DA-v1 前精确时间` | 相对深度基础模型在分布外场景达到可用质量。「从单图取深度」时代开启。 |
| **BEVFormer**（Li et al., ECCV 2022）— https://arxiv.org/abs/2203.17270 | 多相机 → BEV feature volume。Tesla 在产品里做的事的学术版。见 [`companies/tesla_occupancy.md`](../companies/tesla_occupancy.md)。 |
| **Tesla AI Day 2022 —— Occupancy Network 揭示** | 首次公开看到车队规模量产化 BEV 占据。 |

---

## 2023 — 3DGS 年 + 前馈弧起跑

| 发布 | 一行话 |
|---|---|
| **3D Gaussian Splatting (3DGS)**（Kerbl et al., SIGGRAPH 2023）— https://arxiv.org/abs/2308.04079 | NeRF 质量下的实时可微分渲染。几乎一夜替代 NeRF 成为默认表征。见 `foundations/3dgs-family/`。 |
| **DUSt3R**（Wang et al., 2023 arXiv → CVPR 2024）— https://arxiv.org/abs/2312.14132 | 前馈图像对 → 3D pointmap，无 SfM。VGGT 架构的祖先。 |
| **LERF**（Kerr et al., ICCV 2023）— https://arxiv.org/abs/2303.09553 | 语言嵌入辐射场。语义 3D 道开启；见 `foundations/semantic-3d/`。 |
| **SpatialVLM**（Chen et al., 2023 末 → 2024）— https://arxiv.org/abs/2401.12168 | 输出空间 caption 的 VLM；开启「VLM 隐式 3D」押注，PI 后来落地。 |
| **GAIA-1**（Wayve, 2023）— 见 [`companies/wayve_world_model.md`](../companies/wayve_world_model.md) | 驾驶用的生成式视频 world model。AD world-model 第一个正经部署故事。 |

---

## 2024 — 整合 + world model 浪潮

| 发布 | 一行话 |
|---|---|
| **Depth Anything v2**（Yang et al., NeurIPS 2024）— https://arxiv.org/abs/2406.09414 | 上量产的深度基础模型。「单目深度差不多解决了」的拐点。 |
| **4D Gaussian Splatting**（多组，2024）`UNVERIFIED — 规范引用有争议` | 时延伸的 3DGS。动态场景终于能实时渲染。 |
| **GS-SLAM** 血脉（多组）`UNVERIFIED — 规范引用` | 把 3DGS 作为 SLAM 地图表征。把前馈 3D 桥到实时建图。 |
| **Genie**（Bruce et al., 2024）— https://arxiv.org/abs/2402.15391 | 从无标签视频生成可交互环境。「world model as gym」血脉。 |
| **NVIDIA Cosmos** 宣布 — 见 [`companies/nvidia_cosmos.md`](../companies/nvidia_cosmos.md) | Tokenizer + world model 平台；NVIDIA 在栈的 world model 层上押注。 |
| **MASt3R**（Leroy et al., 2024）— https://arxiv.org/abs/2406.09756 | DUSt3R + 匹配。前馈 3D + correspondences；为 VGGT 铺路。 |
| **Marble (World Labs)** 上线 — 见 [`companies/world_labs.md`](../companies/world_labs.md) | 消费级 3D 场景生成成产品。 |
| **π0**（Physical Intelligence, 2024）— 见 [`companies/physical_intelligence.md`](../companies/physical_intelligence.md) | VLA 作产品首秀；「RGB-only VLM 隐式 3D」押注在规模上跑起来。 |
| **3D-VLA**（Zhen et al., ICML 2024）— https://arxiv.org/abs/2403.09631 | 对立押注：显式体素 tokens 进策略。见 [`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)。 |
| **GAIA-2**（Wayve, 2024）— 见 [`companies/wayve_world_model.md`](../companies/wayve_world_model.md) | 更大 context + 多相机；AD world model 命题成熟。 |

---

## 2025 — VGGT、AVP、π³

| 发布 | 一行话 |
|---|---|
| **VGGT**（Wang et al., CVPR 2025 best paper）— 见 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../crossing/slam-vio-migration/vggt_vs_drone_vio.md) | 前馈 transformer 一次过出位姿 + 深度 + pointmap + tracks。CVPR best paper 印证血脉。 |
| **Apple Vision Pro** 量产 — 见 [`companies/apple_vision.md`](../companies/apple_vision.md) | 消费级空间计算量产；inside-out 追踪 + 手部追踪 + 持久锚点都能上线的证明。 |
| **π³ streaming 变体**（Physical Intelligence, 2025 `UNVERIFIED — 名称/日期`）| 流式前馈变体；要盯的是度量感知的前馈 3D 血脉。 |
| **π0.5**（Physical Intelligence, 2025 `UNVERIFIED`）| π0 + 规模 + 数据迭代。RGB-only VLA 继续奏效。 |
| **Skydio X10 上线** — 见 [`companies/skydio.md`](../companies/skydio.md) | 主动立体 + IMU + 设备端 NN 在消费 + 防务规模上。市面上最干净的量产空间 AI 栈。 |

---

## 2026 — 整合年（至 2026-05）

| 发布 | 一行话 |
|---|---|
| Cosmos-1.1（NVIDIA）`UNVERIFIED` | World model + tokenizer 平台迭代；等独立 benchmark。 |
| 继续的 VGGT distillation 工作 `UNVERIFIED — 多组` | 比赛把 VGGT 类延迟压到 &lt;20 ms；这就是无人机翻盘的解锁。见 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../crossing/slam-vio-migration/vggt_vs_drone_vio.md) §7。 |
| ARKit + 空间锚点 SDK 成熟（Apple）| 更多应用上线；尚无机器人级 SDK 发布。 |
| （Open watchlist）Tesla model card 发布 | 截至 2026-05 未发生。若发生，"occupancy network" 从传说升至可验证。 |

2026 的读法是「整合，不是革命」。2023-2025 大架构动作在产品化；下一拐点很可能是 (a) 度量感知前馈 3D 或 (b) 显式 3D VLA 在头对头中击败 PI 的 RGB-only 押注。

---

## 怎么读这条 timeline（带走什么）

| 啥都不记，至少记住 | 为什么 |
|---|---|
| 2020 NeRF → 2023 3DGS → 2025 VGGT | 组织整个领域的那条单弧。Per-scene 优化 → 实时渲染 → 前馈推理。 |
| 深度基础模型是独立弧 | 单图单目深度现在是量产级。影响每种形态。 |
| World models 是*第三*条弧 | Genie / Cosmos / GAIA / Marble 各挑不同下游应用。不要混。 |
| 公司把血脉产品化滞后论文 18-24 个月 | Skydio、Apple、Tesla、PI 上线的架构，学术起源都比它们早 1-2 周期。 |
| 航拍是每种方法最严苛的测试 | 一个方法若在竞速无人机延迟 + 规模下能上线，到哪都能上线。见 [`crossing/slam-vio-migration/`](../crossing/slam-vio-migration/)。 |

---

## Boundary

这是 **timeline 索引**，不是 deep dive。每条都链入对应的 `foundations/` / `crossing/` / `companies/`。忍住在内联加评论的冲动 —— 那是链入文件的工作。也忍住每篇论文都加的冲动 —— 本文是脊柱，不是 bibliography。

---

*按日期顺序追加（年内最新在上）。Moltbot 可追加新行；不要编辑已有行。*
