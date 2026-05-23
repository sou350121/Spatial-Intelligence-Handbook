# 驾驶（AD）空间智能 — 入口页

**Status:** v1 — 带立场的索引。**本页明确不是 AD 综述。**
**TL;DR:** 本手册只收录 AD 中能**迁移到其他载体**的空间原语。完整的感知栈综述、规划栈、法规分析、整车传感器经济学，都归 AD 专属资料管。我们只保留三条线 —— BEV、occupancy networks、world models —— 不再往外扩。

---

## 1 · 驾驶为什么会出现在本手册里

驾驶是目前工程化最彻底的空间 AI 载体。它在三个方向上为整个领域买了单：稠密 BEV 特征 lift、3D occupancy 作为输出表征、用驾驶日志训出来的大规模神经 world model。**这三条都是空间原语**；AD 栈其余部分（高精地图运维、交规推理、V2X）不是。

边界规则很硬：一个话题如果只在「30 m/s 的两吨车跑公开道路」上才成立，就归 AD 教科书；如果它**至少在原理上**能迁移到无人机、地面机器人、操作臂，就归本手册。

---

## 2 · 我们保留的三条线

| 线 | 为什么能迁移 | 在哪里迁不动 | 文档 |
|---|---|---|---|
| **BEV（鸟瞰图）** lift | 多相机 → 统一俯视特征栅格，是地面移动、低空巡检都在用的通用空间原语 | 无人机没有有意义的「地面」；操作臂没有 BEV 对应物 | [bev_and_occupancy.md](bev_and_occupancy.md) |
| **Occupancy networks** | 把感知输出从 bbox 列表换成稠密 3D voxel occupancy，正是操作 / 人形栈一直想要的 | AD 尺度（200 m × 200 m）的 occupancy 参数，对桌面操作是过剩两到三个数量级 | [bev_and_occupancy.md](bev_and_occupancy.md) |
| **驾驶 world models** | Cosmos / Wayve / DriveGPT 这一类驾驶视频预训练 → 4D 场景模型，确实是通用的「载体预训练」打法 | 驾驶日志分布很窄（前向、地面、铺装路面），模型继承这一偏置 | [companies/nvidia_cosmos.md](../../companies/nvidia_cosmos.md)、[companies/wayve_world_model.md](../../companies/wayve_world_model.md) |

World model 这条线主要追在 `companies/` 下，因为可部署产物来自 Cosmos / Wayve 公司，不是学术组。我们交叉链接，不重复写。

---

## 3 · 我们明确**不**覆盖的内容

- 端到端规划栈（UniAD、VAD 等）—— 每篇 AD 综述都在写
- 高精地图制作、矢量地图融合、车道级路径规划
- OEM 量产级传感器采购经济学（L4 车队的 LiDAR 成本）
- 法规 / ODD 定义 / 安全论证
- 交规推理、社会认知层面的行为预测
- 具体 OEM 栈（Tesla FSD、Mobileye、华为 ADS、小鹏等）—— 除非他们**公开**了某个空间原语

如果你冲着这些来，请去看 Tesla AI Day 2021–2022、Mobileye CES 讲稿，以及标准 AD 综述（Hu et al. 2023 *Planning-oriented Autonomous Driving*；Chen et al. 2024 *End-to-end Autonomous Driving Survey*）。本手册不重复它们。

---

## 4 · 交叉引用

- BEV / occupancy 作为**表征谱系** → [foundations/semantic-3d/](../../foundations/semantic-3d/)
- 驾驶传感器物理（纯视觉 vs LiDAR 之争） → [foundations/sensor-physics/](../../foundations/sensor-physics/)
- 驾驶作为跨载体矩阵的一列 → [crossing/slam-vio-migration/vggt_vs_drone_vio.md](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) §4
- 驾驶 world model 作为跨载体预训练 → [companies/nvidia_cosmos.md](../../companies/nvidia_cosmos.md)
- 跨载体尺度叙事（驾驶 = 室外有度量，操作 = 室内有度量） → [crossing/scale-and-metric/](../../crossing/) `TBD`

---

## 5 · 给不同读者

- **AD 工程师** —— 你关心的几乎所有东西**都不在这本手册里**。本手册对你只有一个用途：看看你已建好的空间原语，跟操作 / 无人机的需求比较起来长什么样。
- **操作 / 低空工程师** —— 把 [bev_and_occupancy.md](bev_and_occupancy.md) 读一遍。你会更清楚**为什么** occupancy-as-output 比 bbox-as-output 更对路，回去也好替自己栈里那一改争论。
- **研究者** —— BEV → occupancy → world model 这条进化线，是「工业预训练比学界先一步」最干净的案例之一。即使你这辈子不碰车，也值得理解。

---

## Boundary

本页只是**入口索引**，不是深文。深文只有一篇 [bev_and_occupancy.md](bev_and_occupancy.md)。World model 的深内容归 `companies/` 下。再往外的内容都属于 AD 专属资料，不归这里。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
