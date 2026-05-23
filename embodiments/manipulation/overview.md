# 操作（Manipulation）· 空间表征侧

**范围：** 桌面 / 台面 / 双臂 / 人形上半身的操作任务，**严格从空间表征侧切入**。即几何、语义、接触相关的 3D 结构如何被编码成 policy 可消费的形式。

**状态：** v1 着陆页。本子树下所有具体 benchmark 数字在未经实机校验前均标注 `UNVERIFIED`。

---

## 本 README 为何存在（以及它刻意省略了什么）

本手册拥有操作任务的 **encoder 侧**：点云、体素栅格、feature field、neural scene graph、affordance map、SAM-3D 式 segmentation lift、接触相关几何。它**不**拥有 policy 侧 —— diffusion policy、flow matching、ACT、π0、OpenVLA、action chunking、示教采集 rig、teleop pipeline。这些归姊妹仓：

→ [**VLA-Handbook**](https://github.com/sou350121/VLA-Handbook)（`policy/`、`data-collection/`、`evaluation/`）。

两者的接缝文档见 `bridge-to-vla/feature-cloud-to-action.md`。若你发现自己在这里写 action head，请停下并把它推到边界另一侧。

这种切分不是官僚式的。一个把 3D 当作"更好的 RGB 图像"的操作研究员，在真机上会静默回归 —— 因为他从未分离*几何知道什么*与 *policy 用几何做什么*。把这两者当作一栈，是我们在 2025–2026 部署里看到的最常见架构错误。

---

## 操作任务实际使用的四条表征轴

| 轴 | 典型方法 | 强项 | 弱项 | 今日落地处 |
|---|---|---|---|---|
| **点云** | PointNet++ / PointTransformer | 排列不变、O(N)、可处理变密度 | 无全局结构；对 outlier 敏感 | Diffusion-Policy-3D、RVT、Act3D |
| **体素栅格** | VoxNet / 3D-VLA token | 易 tokenize；与 transformer context 对齐 | 立方内存；丢失亚体素几何 | 3D-VLA、GR-1、voxel-occupancy head |
| **Feature field** | NeRF-distilled / DINOv2-lifted / F3RM | 连续，任意分辨率可查询 | 训练重；对符号查询不透明 | F3RM、Distilled Feature Fields |
| **Scene graph** | 开放词汇 seg + 关系抽取 | 符号化、与语言对齐、可规划 | 对 seg 失败脆弱；保真度低 | SayPlan 类、SAM-3D pipeline |

单个工位通常**同时**使用其中两条 —— 例如：voxel occupancy 做碰撞、point feature cloud 做抓取选择、scene graph 做任务规划。陷阱在于：在你没决定每条轴喂给哪个决策之前，就把三者强塞进一个 architecture。

---

## 操作任务独有、别处没有的空间问题

这些问题正是设立专门子树（而非被 `foundations/` 收编）的理由：

1. **夹爪下的遮挡。** 末端执行器一靠近物体，最关键的决策区域就被夹爪本身遮住。RGB-only policy 能容忍这一点；3D 表征**不能** —— 点云恰好在你最需要保真的位置变空。解法：先验条件下的补全、腕部相机多视图融合、NeRF 式时序累积。这是**那个**操作-3D 问题，单独成篇剖析。
2. **接触几何 vs 视觉几何。** 5 mm 的视觉误差肉眼不可见；同样误差出现在接触法向上则是灾难性的。触觉传感器 + 视觉融合（TacSL、ReSkin、GelSight）是操作任务独有的模态，更大的手册不追踪它。
3. **透明 / 高光 / 反射物体。** 深度传感器会撒谎；stereo 会失败；连 VGGT 类 feed-forward 也会退化。操作必须解决这个问题，因为人们*真正想*自动化的家务任务（厨具、玻璃、包装）几乎全在这个域内。见 `foundations/sensor-physics/depth-sensor-failure-modes.md`。
4. **铰接 / 可形变物体。** 抽屉、柜门、布料、线缆。几何不是静态的；表征必须编码"什么跟着什么动"。Scene graph 与按部件分割的 feature field 是当前最佳答案。

第一条（夹爪遮挡）是楔子 —— 若你在选先读什么，从那篇开始。

---

## 本子目录文件

| 文件 | 用途 | 状态 |
|---|---|---|
| `3d_feature_cloud_representations.md` | 深入 PointNet++ 脉络 + SAM-3D + DINOv2-lifted 特征。衔接 VLA-Handbook policy 接口 | v1 |
| *（规划中）* `gripper_occlusion_completion.md` | 夹爪下区域的多视图 + 先验条件补全 | TBD |
| *（规划中）* `transparent_object_perception.md` | NeRF 类方法 + 偏振 + 主动深度策略 | TBD |
| *（规划中）* `affordance_maps_3d.md` | 逐点抓取 affordance lifting；CLIP-Fields 脉络 | TBD |

---

## 交叉引用

- **Policy 侧：** [VLA-Handbook · policy](https://github.com/sou350121/VLA-Handbook)（diffusion policy、π0、OpenVLA、ACT、action chunking）
- **接口接缝：** `bridge-to-vla/feature-cloud-to-action.md`
- **Encoder 基础：** `foundations/feed-forward-3d/`（VGGT、DUSt3R）、`foundations/semantic-3d/`（label-lift）
- **传感器现实：** `foundations/sensor-physics/depth-sensor-failure-modes.md`
- **跨载体视角：** `crossing/representation-migration/`（3D 在各载体上何时真正重要）

## Boundary

本子目录剖析**操作任务中几何 / 语义如何被编码**。它**不**覆盖：policy 架构、示教采集、teleop、评测协议、操作系统的真实部署 —— 全部归 **[VLA-Handbook](https://github.com/sou350121/VLA-Handbook)**。若本目录下某文档开始描述 action head、action chunking 或 success-rate 评测，它已越界；请用 `bridge-to-vla/` stub 推到 VLA-Handbook。

*维护者注：本处深度为 Major 但非 anchor（anchor 是 `aerial/`）。1.0× 深度档。*
