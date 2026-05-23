# 面向操作任务的 3D Feature Cloud 表征

**状态：** v1 —— 有立场的草稿。所有 accuracy / latency / memory 数字在未经已知 rig 验证前均标 `UNVERIFIED`。
**Wedge tier：** W2 · 操作子树 anchor。
**TL;DR：** "3D feature cloud" 不是单一概念。PointNet++ 脉络给你一个排列不变、便宜到可部署的 embedding；SAM-3D 给你 lift 到几何上的开放词汇分割；DINOv2-lifted-to-3D 给你每点的稠密语义特征。它们解决 encoder 问题中**不同**的部分，却常被混为一谈。按 policy 需要*查询什么*选，不要按 CVPR 海报选。

---

## 1 · 设定 —— 为何是三条脉络，而非一条

操作任务的 encoder 问题，对应同一物理点云的三类正交查询，policy 可能同时发起：

| Policy 发起的查询 | 最佳脉络 |
|---|---|
| "*这块几何*在 3D 中位于何处？"（碰撞、grasp pose） | PointNet++ 家族 |
| "哪些点属于*红色杯子*？"（开放词汇 seg） | SAM-3D / SAM2 lifted |
| "这一点的*语义特征向量*是什么？"（匹配、correspondence、affordance） | DINOv2 lifted to 3D / F3RM |

2026 年一个典型的操作 policy 同时发起以上三种查询。错误在于：把它们漏斗到一个 encoder 里，假装一种架构能把三类查询都答好。没有一种能做到。

虚线切分的 encoder / policy 边界，正是 `bridge-to-vla/feature-cloud-to-action.md` 记录的接缝。

---

## 2 · PointNet++ 脉络（几何为先）

PointNet（Qi 等，CVPR 2017）→ PointNet++（Qi 等，NeurIPS 2017）→ Point Transformer v1/v2/v3（2021–2024）。

它给你的：排列不变的逐点特征，关于点数 O(N)，捕捉局部 + 层次几何。它**不**给你：开放词汇语义，或跨场景的 correspondence。

**操作任务今日落地：**

| 系统 | Encoder | 用途 |
|---|---|---|
| Diffusion Policy 3D（Ze 等，RSS 2024） | PointNet 式逐点 encoder | 用点云 + state 条件化 diffusion policy |
| Act3D（Gervet 等，CoRL 2023） | 多尺度 3D ghost-point encoder | 在点云空间预测 3D 动作 |
| RVT / RVT-2（Goyal 等，CoRL 2023/24） | 多视图 token | 混合 —— 点云投到虚拟视图 |
| PerAct（Shridhar 等，CoRL 2022） | 体素 transformer | 体素 token，对比用 |

**工程现实** `UNVERIFIED`：

- 推理：工作站 GPU 上 2048 点云约 10–30 ms。
- 内存：&lt;1 GB。
- 样本效率：很好 —— 旋转 / jitter 增广干净；稀疏点云训练也存活。
- 失败模式：**密度条件坍缩** —— 仿真稠密点云训练，部署到稀疏真实深度，policy 静默回归。

何时用：从零起步，数据有限，需在一个季度内跑起 3D 感知 policy。何时不用：policy 需按语言推理"那只*红色*马克杯" —— PointNet++ 没语义。请与下面的 SAM-3D 配对。

---

## 3 · SAM-3D 路线（开放词汇分割 lift）

SAM（Kirillov 等，ICCV 2023）→ SAM 2（Ravi 等，2024）→ "SAM-3D" 模式：将 SAM mask 通过深度反投影或 NeRF 式融合 lift 成点云标签。

并没有单一的标准 "SAM-3D" 论文 —— 模式是：在多视图 RGB 上跑 SAM/SAM2，将 mask ID 反投影进点云，跨视图通过投票或 NeRF 式密度融合。例子：SA3D（CVPR 2024）、SAGA、SAI3D、Gaussian Grouping。

它给你的：点云中每个点带一个 **mask ID**，可选附带 CLIP 对齐的文本 embedding。policy 可以说"那只杯子"，你能把它解析到 3D 区域。它**不**给你：细粒度 correspondence（两只杯子长得一样），或基础模型未训练过的遮挡稳健处理。

**操作任务今日落地：**

- 开放词汇抓取 pipeline：SAM mask → 质心 / 主轴 → 抓取提议。
- 语言条件操作："拿红色那个"经 SAM2 视频传播跨整段示教。
- Scene-graph 操作：SAM mask 成图节点；关系由 VLM 推断。

**工程现实** `UNVERIFIED`：

- 推理：RTX 4090 上 SAM2 视频低分辨率约 30 fps；Jetson 上实时难。
- 难点**不是** SAM —— 难在 lift。多视图一致性、mask-ID 稳定性、遮挡处理 —— 都没解到位。生产团队通常硬编码冻结工作区，对每段 clip 重跑 SAM。
- 失败模式：mask ID 闪烁。同一物理对象 *t* 帧是 mask 3、*t+1* 帧变 mask 7。视频传播（SAM2 贡献）有帮助，但没解决。

何时用：开放词汇指令跟随是产品需求。何时不用：需高频闭环控制 —— SAM 进回路加 30–100 ms `UNVERIFIED`。

---

## 4 · DINOv2 lift 到 3D（稠密语义特征）

DINOv2（Oquab 等，2023）→ Feature Fields（F3RM、LERF、OpenScene）→ DINO-distilled NeRF / 3DGS。

模式：DINOv2 为每帧 RGB 给出逐像素特征向量。把该特征 lift 到 3D —— 经 NeRF 式体积蒸馏（F3RM、LERF），或附着到 3DGS 场景的 Gaussian 上。3D 中每点带一个 **DINOv2 级特征**，可按与参考 patch 或文本 embedding 的相似度查询。

**操作任务今日落地：**

- F3RM（Shen 等，CoRL 2023）—— 用 CLIP embedding 查询 lifted feature field，实现语言条件操作。
- Distilled Feature Fields —— 基于 correspondence 的抓取、为 policy 生成 novel-view rollout。
- 3DGS 变体：feature-3DGS、LangSplat —— 同配方，不同几何 backbone。

它给你的：**任意可查询 3D 位置的稠密、连续语义特征**。若下游需要 correspondence 或逐点 affordance 评分，这是最佳表征。

代价：

| 属性 | F3RM 类 | 3DGS-distilled | PointNet++ baseline |
|---|---|---|---|
| 每场景构建时间 | 分钟级 | 分钟级 | 无（inline） |
| 查询时间 | ~10 ms `UNVERIFIED` | ~5 ms `UNVERIFIED` | inline |
| 内存 | 每场景 1–4 GB | 每场景 0.5–2 GB | &lt;1 GB |
| 在线场景适配 | 不行（要重建） | 不行（要重建） | 行 |
| 开放词汇 | 行（CLIP head） | 行（CLIP head） | 不行 |

Feature field 方法的阿喀琉斯之踵是**在线适配**。极适合固定工位 —— 任务开始时重建一次 field，整个 episode 复用。不适合末端执行器以 30 Hz 接近新场景。

---

## 5 · 怎么选（真正的决策）

若只能跑一个 encoder：

- 实验室 demo 阶段的双臂 / 移动操作 → **PointNet++ baseline**。
- 面向消费者的开放词汇 demo → **SAM-3D**。50 ms 延迟值得，因为 demo *需要*语言。
- 固定工位、语言指令、新物体 → **DINOv2-lifted（F3RM 类）**。

若能跑两个：PointNet++ 做几何 + SAM-3D 做语义，融合为两路 token 流。这是 2026 年最常见的生产模式，对应 `bridge-to-vla/feature-cloud-to-action.md` §4.3 的 "late fusion"。

---

## 6 · 到 action head 的接缝（本文档止于此）

以上全是 **encoder 侧**。一旦你开始问"diffusion policy 应如何 attend 这些 token"，你就进了 VLA 领地：

→ `bridge-to-vla/feature-cloud-to-action.md` —— 集成契约（schema、坐标系、scale、密度）。
→ [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) —— action head（diffusion policy、π0、OpenVLA、ACT）。

本手册从不指定 policy 是 diffusion 模型还是 flow matching 模型。指定这一点是 category error。

---

## 7 · 2 年展望 + 可证伪预测

**展望：** Feature field 方法变*快*的速度，会快于变*更准*的速度。瓶颈是每场景构建延迟，不是特征质量。预计 2027 年前每场景 feature field 构建 &lt;30 s —— F3RM 类对 episodic 操作变得可用。

**可证伪预测：** 到 2027 年底，开源操作 policy 论文的中位数会用**两个** encoder（几何 + 语义），不是一个。

---

## 参考（起步集）

- PointNet++ —— Qi 等，*NeurIPS 2017*。https://arxiv.org/abs/1706.02413
- Point Transformer v3 —— Wu 等，*CVPR 2024*。https://arxiv.org/abs/2312.10035
- Diffusion Policy 3D —— Ze 等，*RSS 2024*。https://arxiv.org/abs/2403.03954
- Act3D —— Gervet 等，*CoRL 2023*。https://arxiv.org/abs/2306.17817
- SAM —— Kirillov 等，*ICCV 2023*。https://arxiv.org/abs/2304.02643
- SAM 2 —— Ravi 等，*2024*。https://arxiv.org/abs/2408.00714
- SA3D —— Cen 等，*CVPR 2024*。https://arxiv.org/abs/2304.12308
- DINOv2 —— Oquab 等，*2023*。https://arxiv.org/abs/2304.07193
- F3RM —— Shen 等，*CoRL 2023*。https://arxiv.org/abs/2308.07931
- LERF —— Kerr 等，*ICCV 2023*。https://arxiv.org/abs/2303.09553

## Boundary

本文档覆盖**为操作任务产出 3D feature cloud 的 encoder**。它**不**覆盖：

- Action head、policy 架构、示教采集 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)
- Encoder 到 policy 的接口契约 → `bridge-to-vla/feature-cloud-to-action.md`
- VGGT / DUSt3R 内部 → `foundations/feed-forward-3d/`
- 语义 3D lifting 基础 → `foundations/semantic-3d/`

*最近立场更新：2026-05-21。*
