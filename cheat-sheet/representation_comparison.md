# 3D Representation Comparison — 什么时候选哪个

**Status:** v1 — opinionated draft。定量声明（内存、渲染速率）仅量级，未钉的均 `UNVERIFIED`。
**TL;DR:** 2026 年空间 AI 由六种表征主导 —— **NeRF、3DGS、SDF、voxel grid、point cloud、scene graph**。它们不可互换。决定因素是**任务类型**（rendering / geometry / planning / reasoning），不是「哪个最新」。多数量产栈混用 2-3 种；选错主表征，6 个月后会要你的命。

---

## 1 · 六种表征概览

| 表征 | 存储 | 几何 | 渲染 | 可编辑性 | 最擅长 |
|---|---|---|---|---|---|
| **NeRF**（体 MLP）| 隐式（网络权重）| 隐式、平滑 | 慢（ray marching）；Instant-NGP 可快 | 难（要重训）| 从带位姿 RGB 做照片级新视角合成 |
| **3DGS**（splat 原语）| 显式（数百万 Gaussian 原语）| 半隐式（密集化的原语）| **快**（光栅化，100+ FPS）| 中（移动/编辑原语）| 实时可微分渲染、SLAM 地图 |
| **SDF**（signed distance field）| 隐式（网格或网络）| 在零等值面显式 | Marching cubes → mesh 再走标准 | 难 | 水密表面重建、机器人运动规划（碰撞查询便宜）|
| **Voxel grid** | 显式 3D 数组 | 离散化 | 直接渲染或 marching cubes | 容易（cell 更新）| 占据建图、BEV-volume 策略、接触推理 |
| **Point cloud** | 显式 (x,y,z[,rgb,normal]) 集合 | 稀疏、无结构 | Splatting 或表面重建 | 容易（增删点）| 传感器输出（LiDAR、ToF、立体）；中间交换格式 |
| **Scene graph** | 符号（节点 + 边）| 物体级抽象 | 无（要下游渲染）| 容易（语义编辑）| 高层规划、VLM 推理、操作任务分解 |

3DGS 血脉见 [`foundations/3dgs-family/`](../foundations/3dgs-family/)；scene graph / 语义见 [`foundations/semantic-3d/`](../foundations/semantic-3d/)。

---

## 2 · 大对照表

列是你选表征时该问的问题。行是六种表征。格子里是**带主观的简短判定**，不是 benchmark 数（数字在 `benchmarks/`）。

| 问题 | NeRF | 3DGS | SDF | Voxel | Point cloud | Scene graph |
|---|---|---|---|---|---|---|
| **实时渲染（>30 FPS）？** | ❌ 原版，⚠️ Instant-NGP 可 | ✅ 原生 | ❌（要 mesh 抽）| ⚠️ 粗分辨率光栅化可 | ✅ 但丑 | n/a |
| **传感器流友好？**（depth/LiDAR 直接）| ❌ 要带位姿 RGB | ⚠️ 要初始化 | ✅ 从深度直接（TSDF）| ✅ 直接融合 | ✅ 原生 | ❌ 要上游感知 |
| **端到端可微分？** | ✅ 规范 | ✅ 规范 | ✅ DeepSDF 血脉 | ⚠️ 离散 cell | ⚠️ 要排列不变 | ❌ 符号 |
| **碰撞 / 接触查询便宜？** | ❌ 啥都要 ray-march | ⚠️ 每个 splat raycast | ✅ **同类最佳** | ✅ 直接 cell lookup | ❌ 要表面重建 | ❌ 物体级 |
| **编辑能传到策略？**（移动一个杯子，要重训吗？）| ❌ 重训 | ⚠️ 移原语，部分重训 | ⚠️ 部分 | ✅ 翻 cell | ✅ 增删点 | ✅ 符号更新 |
| **机器人 SoC 上的存储？** | 小（权重）| 中-大（几十-几百 MB）| 小-中 | 中-大 | 稀疏则小 | 极小 |
| **与 VLM tokens 配合？** | ❌ 隐式 | ⚠️ 经投影 | ❌ 仅表面 | ✅ voxel tokens | ⚠️ 池化 embedding | ✅ 符号 tokens |
| **动态场景？** | ⚠️ D-NeRF / 4D-NeRF 研究 | ✅ 4DGS 血脉 | ⚠️ 动态 SDF（研究）| ✅ 每体素 flow | ✅ 平凡支持 | ✅ 符号 state |
| **开放区 / 户外尺度？** | ⚠️ 无界变体（Mip-NeRF 360）| ✅ 还能 scale | ❌ 内存爆 | ❌ 内存爆 | ✅ 但稀疏 | ✅ 符号 |
| **2026 产线成熟度** | 小众（CG、资产采集）| 主流（SLAM、渲染）| 主流（规划）| 主流（AD、AR）| 通用（传感 IO）| 新兴（VLA、VLM 推理）|

读表：**没有任何单列是「最好」**。选择与任务耦合。

---

## 3 · 决策树 —— 90 秒选表征

```
Q1: 任务主要是渲染 / 视角合成？
 ├─ 是 ──► Q2: 要实时？
 │          ├─ 是 ──► 3DGS
 │          └─ 否 ──► NeRF（质量受限）或 Instant-NGP（工程速度）
 │
 └─ 否 ──► Q3: 任务主要是几何 / 规划？
            ├─ 是 ──► Q4: 要便宜碰撞 / 接触？
            │          ├─ 是 ──► SDF（出 mesh 给 ICP，体素化给占据）
            │          └─ 否 ──► Q5: 要每体素语义 / flow？
            │                     ├─ 是 ──► Voxel grid（占据 + flow + 语义）
            │                     └─ 否 ──► Point cloud（最便宜的中间格式）
            │
            └─ 否 ──► Q6: 任务关于高层推理 / VLM？
                       ├─ 是 ──► Scene graph（+ 留一份备用几何表征）
                       └─ 否 ──► 八成要混合；见 §5。
```

启发式：**先选与你传感器栈*输出*匹配的表征，然后为它不擅长的下游任务加第二种**。传感器输出 → 点云或体素 → 派生 → 按需 SDF 或 3DGS。

---

## 4 · 失效模式 —— 每种表征会被什么坑

| 表征 | 在哪崩 | 症状 |
|---|---|---|
| **NeRF** | 稀疏视角输入、动态场景、外推到新位姿 | Floater、几何模糊、遮挡错乱 |
| **3DGS** | 镜面 / 透明面、相机轨迹大跳跃 | 杂散原语、"popcorn" 噪声、空洞 |
| **SDF** | 拓扑复杂的薄结构（电线、叶子）、开放面 | 表面合并或消失；非水密让 marching cubes 崩 |
| **Voxel grid** | 超过 ~100m × 100m × 10m 且亚分米分辨率 | 内存爆炸；精细几何走样 |
| **Point cloud** | 学习模型里的排列不变性麻烦；表面歧义 | 网络分不清密疏同表面；最近邻成本 |
| **Scene graph** | 子物体几何（哪根手指压在杯把上？）| 符号抽象丢掉接触相关细节 |

最常见的量产错误：**因为 3DGS 最新就选它，然后需要碰撞查询**。3DGS 是给渲染的，不是给「夹爪有没有撞」用的。配一层 SDF 或 voxel。

---

## 5 · 量产栈都是混合 —— 五种典型组合

几乎没有量产栈只用一种表征。常见组合：

**(a) Voxel + Point cloud —— AD / AGV 模式。**
传感器栈出点云（LiDAR / 立体）。前端融合到占据 voxel grid。Planner 查 voxel。例：Tesla occupancy network（相机 → BEV volume → voxel-occupancy head）。见 [`companies/tesla_occupancy.md`](../companies/tesla_occupancy.md)。

**(b) 3DGS + SDF —— 操作 + 地图。**
3DGS 做场景视觉地图与新视角监督；SDF 给运动规划做碰撞查询。两者协同训练或后处理对齐。

**(c) Point cloud + Scene graph —— VLA 模式。**
点云（或 3DGS feature cloud）→ scene graph 抽取（物体 + 关系）→ VLM 消费 scene graph tokens + 原始 features。集成模式见 [`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)。

**(d) Voxel + NeRF —— 离线重建 + 在线占据。**
Voxel 在线（便宜、快）；高质量 NeRF / 3DGS 重建离线建，给下游仿真 / world model 训练用。AD 数据流水线常见。

**(e) Scene graph + 下面一切 —— VLM 驱动机器人。**
VLM 只看 scene graph 做规划；几何层（point cloud + SDF + 3DGS）在下面执行。这是当前通用机器人团队收敛的架构形状。

---

## 6 · 按任务速查

| 任务 | 主表征 | 次表征（典型）| 为什么 |
|---|---|---|---|
| 从带位姿图像合成新视角 | 3DGS | NeRF | 实时渲染赢 |
| 水密表面重建 | SDF | Point cloud | 表面保证 |
| 机器人运动规划（碰撞查询）| SDF 或 voxel | Point cloud | 便宜接近查询 |
| AD / AGV 占据建图 | Voxel | Point cloud | 直接融合，语义 + flow head |
| SLAM 地图（实时密集）| 3DGS | Point cloud / SDF | GS-SLAM 血脉 |
| 从稀疏图像前馈 3D | Point cloud | 3DGS（后期密集化）| DUSt3R / VGGT 输出是 pointmap |
| 操作抓取合成 | SDF | Point cloud | 要精细表面 |
| 场景级 VLM 推理 | Scene graph | Point cloud（feature cloud）| 符号 + 亚符号 |
| 驾驶 world model rollout | Voxel / BEV | (latent) | Cosmos / Wayve 模式 |
| AR 持久化（消费头戴）| Scene graph + SDF（锚 + nav mesh）| Point cloud | ARKit 形状 |
| 航拍障碍图 | Voxel（占据）| Point cloud | 快净空查询 |
| 海面 SLAM 地图 | Point cloud（稀疏，声纳衍生）| Voxel | 声学原生格式 |

---

## 7 · 两年展望

三个该盯的位移（都不意外；问题是时机）：

**(a) 3DGS 成为通用地图表征。** GS-SLAM 成熟，机械臂采用 3DGS 场景地图，AR 用 3DGS 渲染。2027 默认「地图」数据类型是 3DGS 风。

**(b) Feature clouds 在策略接口替代 point clouds。** 原始 (x,y,z) 让位给每点 (x,y,z,feat_d)，feat_d 是学到的语义嵌入。见 [`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)。

**(c) Scene graphs 成为面向 VLM 的层。** 通用机器人 VLM 在 scene graph 级别推理；几何层喂它。这是领域从 PI、OpenAI 机器人工作 `UNVERIFIED`、学术 3D-VLA / SpatialVLM 反推出的架构。

**可证伪预测：** 到 2027-12，至少一家主流机器人基础模型发布（PI、DeepMind、OpenAI 量级）会显式公开*scene graph + 3DGS map + voxel collision*混合作为规范感知栈。若大家都还在 RGB-only 隐式，混合栈命题错了，我们要转向「VLM 就够」。

---

## Boundary

这是**速查表** —— 90 秒选表征。每种表征的解剖在：

- 3DGS / NeRF 血脉：[`foundations/3dgs-family/`](../foundations/3dgs-family/)
- 前馈 3D（point cloud、pointmap）：[`foundations/feed-forward-3d/`](../foundations/feed-forward-3d/)
- 语义 3D / scene graph：[`foundations/semantic-3d/`](../foundations/semantic-3d/)
- Voxel / BEV：见 [`companies/tesla_occupancy.md`](../companies/tesla_occupancy.md) 与 `foundations/feed-forward-3d/`
- 与策略集成：[`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)

不要在本文深入任何表征。速查表的工作是 90 秒把你送到正确文件，然后让路。

---

*仅追加。Moltbot 可追加新行或新表征；不要编辑已有行。*
