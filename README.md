# Spatial Intelligence Handbook

> **从厘米到公里，从地下到空中——一本跨 embodiment 的空间智能 handbook。**
>
> 桌面机械臂、自动驾驶、无人机、水下机器人都需要把物理空间变成可推理、可生成的表示。但 manipulation 圈写的 SLAM 综述里没有 outdoor，自动驾驶圈写的 BEV 综述里没有 manipulation，drone 圈和水下圈基本不读对方的论文。**这本 handbook 做一件事：把这些圈各自闭门发明的同一类问题摊在桌上横向对比，再加一份 3DGS / VGGT / depth foundation 的统一底层教科书。**

姊妹仓库：[VLA-Handbook](https://github.com/sou350121/VLA-Handbook) · VLA 管 action policy，Spatial 管 world representation，两者交集是 3D-aware VLA。

---

## 三句话说清楚这个 Handbook 的价值

1. **不只是综述**：每篇给出表示选型理由、关键超参、shape sanity-check、部署陷阱——"看懂论文"和"跑通代码"之间的坑，都标出来。
2. **跨 embodiment 横向比较**：市场上所有 spatial intelligence 综述都是单 embodiment 闭门写。这本是第一本把 manipulation / driving / aerial / marine 的同一类问题摊在桌上对比的。
3. **活的知识库**：自动 pipeline 每天抓最新论文（⚡/🔧/📖 评级），精选后生成深度解析写入仓库，不是六个月没人维护的静态文档。

---

## 谁应该读这本

| 读者 | 为什么读 |
|---|---|
| **跨 embodiment 转岗的算法工程师** | manipulation → drone、AD → robot、机器人 → 水下——同一套 SLAM/3D vision 在不同 embodiment 上的解法差异，过往没人系统梳理 |
| **多 embodiment 公司的系统架构师** | NVIDIA、Apple、Tesla、华为这种同时做车 + 机器人 + AR 的公司，需要横向决策"哪个 representation 跨 embodiment 复用" |
| **找下一个 research direction 的研究者** | crossing 章节直接指向"哪些跨 embodiment 问题还没人解决"——这是 paper idea 的来源 |
| **传感器 / 硬件团队** | sensor-physics 那一章是 industry 真正缺的——学界综述写不出 SWaP-C 工程账，厂商内部资料又封闭 |

---

## 三层架构

```
┌─────────────────────────────────────────────────────────┐
│  Embodiments · 各 embodiment 应用层                       │
│  操作 │ 移动 │ 驾驶 │ 空中 │ 水下                            │
│  π0/GR00T  Spot/AGV  FSD/Wayve  Skydio/DJI  AUV/USV     │
├─────────────────────────────────────────────────────────┤
│  Crossing · 跨 embodiment 合流（★ 本书 USP）              │
│  scale × sensor × SLAM/VIO × representation × failures  │
│  把各 embodiment 圈闭门的同类问题摊在桌上横向对比               │
├─────────────────────────────────────────────────────────┤
│  Foundations · 跨 embodiment 共享底层                     │
│  3DGS family · VGGT family · Depth (FF) · Semantic 3D   │
│  World model · VLM reasoning · Physics · Sensors (★)    │
└─────────────────────────────────────────────────────────┘
```

**为什么是三层而不是二层**：spatial intelligence 是一个统一领域，但它的具体表达取决于 embodiment。所有 embodiment 都要 perceive → represent → reason → act 空间，但 scale、sensor、dynamics、failure modes 截然不同。中间的 crossing 层是这本书唯一不可替代的内容——把统一底层和各应用 lane 之间的对比关系系统写出来。

---

## 和这些方式相比

| 维度 | 单 embodiment 综述 | 厂商内部资料 | 学术大杂烩 | **Spatial-Intelligence-Handbook** |
|---|---|---|---|---|
| **覆盖广度** | 单 embodiment 深度 | 单 embodiment 极深 | 偏 manipulation | 5 embodiment + crossing 对比 |
| **横向对比** | ❌ | ❌（闭门）| ❌（堆论文）| ✅ crossing 章节专门做这件事 |
| **工程细节** | ⚠️ 学术为主 | ✅ 但不外传 | ❌ | ✅ shape / 超参 / 部署陷阱 |
| **传感器物理** | ❌ | ✅ 但封闭 | ❌ | ✅ sensor-physics 独家轴 |
| **更新频率** | 静态 | 内部更新 | 不定期 | 每日自动 + 社区每周 |
| **可追溯性** | 论文链接 | 无公开 | 链接列表 | Git 永久记录 + 自动评分 |

---

## 五大 embodiment 名单与取舍理由

| Embodiment | 收 / 不收 | 理由 |
|---|---|---|
| **操作 (manipulation)** | ✅ 主力 | VLA-Handbook 已有 manipulation policy，Spatial 这边写它的 representation 侧（3D feature cloud、affordance、SAM 3D）|
| **人形 / 足式** | ✅ 主力（可合并入操作） | 全身运动的 spatial 推理（看地面 + 看远处目标）和桌面 manipulation 不同 |
| **地面移动** | ✅ 主力 | AGV / 室内移动 / VLN 独立性强，benchmark 也独立（HM3D / ObjectNav）|
| **自动驾驶** | ✅ 主力 | 必须收。BEV / 占用网络 / Cosmos / Wayve GAIA 是 spatial intelligence 资源最密集的一翼，**不收等于自废武功**。但严守"不变成 AD 综述"的边界——重点写它和其他 embodiment 的可迁移 / 不可迁移技术 |
| **无人机** | ✅ 自研深度 | 维护者工作锚点，作为 first among equals。`embodiments/aerial/` 深度可以是其他 embodiment 的 1.5–2x |
| **水下机器人** | ✅ Minor track | 必须收。水下是 spatial intelligence 最 stress test 的 embodiment——视觉退化（吸收 / 散射）、GPS 不能用、声呐主导、压力下 sensor 受限。任何在水下能 work 的方法都是真正鲁棒的方法。作为 contrasting case 比深度覆盖更重要，写 1/3 主力的篇幅就够 |
| **AR / VR (Apple Vision Pro / Quest)** | ⚠️ Edge case | 用户是人不是机器人，但 inside-out tracking / hand tracking / spatial anchor 这套技术和机器人 SLAM 完全同源，作为 `crossing/` 对比案例提及，不独立成 embodiment 章节 |
| **太空机器人** | ❌ 不收 | 太窄，公开资料少，handbook 价值低 |

---

## 项目结构

```
Spatial-Intelligence-Handbook/
├── foundations/                    # 跨 embodiment 共享底层
│   ├── 3dgs-family/               # 3DGS / 2DGS / 4DGS / Mip-Splatting / GS-SLAM
│   ├── feed-forward-3d/           # DUSt3R / MASt3R / VGGT / π³ / streaming variants
│   ├── depth-foundation/          # Depth Anything v2 / MoGe / Metric3D / FoundationStereo
│   ├── semantic-3d/               # DINOv2 / SigLIP 上抬到 3D / LERF / OpenScene / 3D scene graph
│   ├── world-model/               # Cosmos / Genie / Marble (只收对决策有用的)
│   ├── vlm-spatial-reasoning/     # SpatialVLM / SpatialBot / 3DSRBench / BLINK
│   ├── physics/                   # PhysGaussian / PhysGen / diff-physics + neural rendering
│   └── sensor-physics/            # ★ 独家：ToF / LiDAR / active-IR / stereo + 多模态融合
│
├── embodiments/                    # 各 embodiment 的 SOTA stack + 特殊问题
│   ├── manipulation/              # 桌面、抓取、装配、双臂、humanoid 上肢
│   ├── humanoid-legged/           # 全身、行走、平衡
│   ├── ground-mobile/             # AGV / 室内移动 / VLN
│   ├── driving/                   # 自动驾驶 / BEV / 占用网络
│   ├── aerial/                    # ★ 无人机自研深度
│   │   ├── vio/                  # VINS/OpenVINS + DROID-SLAM + feed-forward 替代
│   │   ├── obstacle-avoidance/   # UZH RPG champion-level / Skydio autonomy
│   │   ├── active-tracking/      # Skydio ActiveTrack / DJI ActiveTrack 反工程
│   │   ├── on-board-mapping/     # 实时 3DGS on Jetson Orin / 3DGS for inspection
│   │   ├── long-range-slam/      # 公里级 mapping / GNSS-denied / LiDAR-cam fusion
│   │   ├── event-camera/         # UZH RPG 系 / 高速 / 低光 / HDR
│   │   ├── swarm/                # 多机 SLAM / 共享地图 (展望)
│   │   └── sensor-stack/         # SWaP-C 约束下的传感器选型实战
│   └── marine/                    # AUV / USV / 声呐 / 视觉退化
│
├── crossing/                       # ★★ 本书 USP——市场上没有的内容
│   ├── scale-comparison/          # 1cm → 1000km，同一问题在不同尺度怎么变形
│   ├── sensor-stack-matrix/       # 各 embodiment 用什么 sensor / 为什么 / SWaP-C 对比
│   ├── slam-vio-migration/        # 桌面 → 室内 → 户外 → 空中 → 水下 同源问题不同解
│   ├── representation-migration/  # 3DGS / VGGT 在各 embodiment 的部署对比
│   └── failure-modes-atlas/       # 不同 embodiment 的 spatial 失败方式总图
│
├── deployment/                     # 工程实战
│   ├── hardware-selection/        # IMX900 / 850nm BPF / ToF vs SL / event camera
│   ├── multi-modal-sync/          # RGB + Depth + IMU + IR 硬同步
│   ├── calibration/               # 多相机外参 / stereo rect / IMU-cam / 飞行中在线标定
│   ├── compute-budget/            # Jetson Orin / RK3588 / 3DGS 端侧 / VGGT 蒸馏
│   ├── failure-modes/             # camera-shift / 振动 / 逆光 / 反射 / 透明 / 雨雪 / 粉尘 / 水下
│   └── community_field_notes_*.md
│
├── benchmarks/
│   ├── geometry/                  # ScanNet++ / TUM-RGBD / ETH3D / DTU
│   ├── manipulation/              # GraspNet / YCB / RLBench
│   ├── driving/                   # nuScenes / Waymo Open / Argoverse 2
│   ├── aerial/                    # ★ EuRoC / TUM-VI / UZH-FPV / Hilti SLAM Challenge
│   ├── marine/                    # AQUALOC / Mining-Sub / SubPipe
│   └── reasoning/                 # 3DSRBench / BLINK / CV-Bench / What's Up
│
├── bridge-to-vla/                  # 与 VLA-Handbook 接口
│   ├── 3d-aware-vla.md           # 3D-VLA / PointVLA / SpatialVLM
│   ├── feature-cloud-to-action.md # 3D feature cloud → action head 工程范式
│   └── neural-map-as-memory.md   # neural map 作为 long-horizon memory
│
├── companies/                      # 产业地图
│   ├── world-labs.md             # World Labs / Marble
│   ├── niantic-spatial.md
│   ├── nvidia-cosmos.md          # NVIDIA Cosmos World Foundation Models
│   ├── skydio.md                  # Skydio autonomy stack
│   ├── dji.md
│   ├── autel.md
│   ├── physical-intelligence.md
│   ├── apple-vision.md
│   ├── wayve.md
│   └── tesla-occupancy.md
│
├── reports/
│   ├── biweekly/                  # 双周推理 + 预测追踪
│   └── weekly/                    # 周报 + 风向洞察
│
└── cheat-sheet/                    # 速查表
    ├── timeline.md                # 2020-2026 关键论文时间线
    ├── representation-comparison.md  # NeRF / 3DGS / SDF / voxel / point 速查
    └── sensor-budget-matrix.md    # embodiment × sensor 一张大表
```

---

## 为什么 `crossing/` 才是真正的 USP

5 个 crossing 章节，每一篇都是市场上没人系统写过的内容。具体例子：

### `crossing/scale-comparison/depth-foundation-across-scales.md`
Depth Anything 在桌面 manipulation（0.3m）work 很好，到 drone outdoor（10m 起步）scale ambiguity 爆炸，到水下（折射 + 散射）完全失效。**同一个 foundation model 在不同 embodiment 上表现差这么多的机制层面解释**，没人写过。

### `crossing/slam-vio-migration/why-vio-doesnt-cross-embodiments.md`
VINS-Mono 在 EuRoC（drone）跑得很好，换到水下 AQUALOC 就崩，换到 manipulation TUM-RGBD 又 overkill。**同类问题在不同 embodiment 解空间为什么差这么大**——从 IMU 噪声特性、运动 mode、scene constraint 三个维度拆。

### `crossing/representation-migration/3dgs-as-simulator-comparison.md`
3DGS 现在被用作 manipulation policy 训练数据（Splat-Sim）、drone sim2real（Aerial Gym 后续）、AD simulation（NVIDIA Cosmos）。**三家用 3DGS 做 sim 的工程实践共同和不共同**，第一次系统整理。

### `crossing/sensor-stack-matrix/sensor-budget-by-embodiment.md`
一张大矩阵：rows 是 embodiment，cols 是 RGB / depth / IMU / LiDAR / NIR / event / acoustic，每个 cell 写"为什么用 / 为什么不用 / SWaP-C 约束 / failure mode"。这是 industry 真正缺的内容——学界综述写不出 SWaP-C 工程账。

### `crossing/failure-modes-atlas/transparent-reflective-deformable.md`
透明物体让 manipulation 抓取失败、让 drone 撞玻璃幕墙、让 AD 撞反光路面、让 AUV 撞水母。**同类 failure mode 在不同 embodiment 的表现和缓解策略对比**。

每篇 1-2 万字深度内容，每篇出来都直接定位"市场上没有"的 niche。

---

## 先看这几篇（30 分钟内建立正确框架）

按依赖顺序排列——每一篇回答上一篇读完后自然产生的问题。

**第一层：foundations 是什么、为什么 2024-2026 是分水岭（~15 min）**

1. **[3DGS family overview](./foundations/3dgs-family/README.md)** `5 min` — 先建立全局图：3DGS 为什么取代 NeRF 成为 spatial representation 的 hegemon、4DGS / GS-SLAM / GS-as-simulator 三条衍生线。
2. **[VGGT family — feed-forward 3D 的范式转移](./foundations/feed-forward-3d/README.md)** `10 min` — 1 告诉你 3DGS 怎么用，这篇回答 *VGGT 这条 feed-forward 路线为什么可能让 3DGS 也变成中间产物*。CVPR 2025 best paper 不是孤立事件。

**第二层：crossing 怎么把单 embodiment 看法打开（~15 min）**

3. **[VGGT 能不能替代 drone VIO？](./crossing/slam-vio-migration/vggt-vs-vio.md)** `10 min` — feed-forward 推理在 Jetson Orin 上 100ms 够不够，scale ambiguity 怎么和 IMU/GNSS 融合，比 VINS-Mono 优势在哪、bug 在哪。**这一篇是这本 handbook 的代表作**——同一个问题在 manipulation/aerial/marine 上的答案完全不同。
4. **[sensor budget matrix](./crossing/sensor-stack-matrix/README.md)** `5 min` — 一张大矩阵看完，理解为什么 manipulation 不用 LiDAR、drone 不用 RGBD、水下不用 RGB。

**第三层：对接 VLA-Handbook（按需深入）**

5. **[3D feature cloud → action head](./bridge-to-vla/feature-cloud-to-action.md)** — Spatial 这边算出来的 3D 表示怎么接到 VLA-Handbook 那边的 action policy。

---

## Wedge 文档：2 周立项

| Week | 文档 | 为什么这篇 |
|---|---|---|
| W1 | `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md` | VGGT 是 2025 年最 hot 的 representation，必须有第一版 |
| W1 | `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` | 独家轴的 wedge，用 Autel 工作产出 |
| W1 | `crossing/slam-vio-migration/vggt_vs_drone_vio.md` | 跨 embodiment 横向比较的代表作，证明 USP 存在 |
| W2 | `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` | 一张大矩阵，立即视觉化"跨 embodiment"定位 |
| W2 | `bridge-to-vla/3d_feature_cloud_to_action_head.md` | 和姊妹仓库的接口章 |

5 篇就够立项。其余让自动 pipeline ramp。

---

## 自动更新（参考 VLA-Handbook 的 Pulsar 系统）

复用 VLA-Handbook 的 Pulsar pipeline，只需要改动：

- **Hypothesis registry**：为每个 embodiment 单独建一组假设 + 置信度（某个 embodiment 沉寂时其他仍在自校准），加一组 cross-embodiment 假设
- **种子假设举例**：
  - "feed-forward 3D（VGGT 系）会在 2 年内取代 per-scene optimization（3DGS）成为机器人空间感知主流"
  - "纯 RGB + foundation depth 在 manipulation 范围内会持续压制 active sensing，但在 outdoor drone 上不会"
  - "3DGS-as-simulator 比 traditional sim 更早 product-ready 在 drone 上、更晚在 manipulation 上"
  - "World model 作为 VLA 训练数据生成器，比作为 inference-time planner 更早 product-ready"
- **更新时刻表**：
  - 每日 09:15 论文评分 ⚡/🔧/📖/❌
  - 每周一/三/五理论深度解析
  - 每周日周报 + 风向洞察
  - 每两周双周推理报告（带预测打分回溯）

---

## 与 VLA-Handbook 的边界规则

| 内容类型 | 主入口 | 另一侧 |
|---|---|---|
| Manipulation / humanoid 的空间表示创新（3D-VLA, PointVLA） | VLA-Handbook | Spatial 留 cross-ref |
| Drone / aerial 的空间表示与感知（Champion-level racing, Skydio autonomy） | Spatial-Handbook | VLA cross-ref |
| 通用 3D representation backbone（3DGS, VGGT, Depth Anything） | Spatial-Handbook（主理论位置）| VLA 引用结论 |
| Action policy 训练（diffusion / flow matching） | VLA-Handbook | 不收 |
| Sensor 物理 / 硬件选型 | Spatial-Handbook | 不收 |
| Sim2Real（动力学侧） | VLA-Handbook | Spatial 引 representation 侧 |
| World model（作为 data generator） | 两边都收，视角不同 | 互引 |

---

## 风险与对冲

| 风险 | 对冲 |
|---|---|
| **范围爆炸**——多 embodiment 看起来是百科全书 | 阀门是 `crossing/` 的 5 个维度封闭，新 embodiment 只补 `embodiments/` 子树，不让书变厚到失控 |
| **品牌稀释**——VLA-Handbook 流量被分流 | 第一版作为 VLA-Handbook 姊妹仓发布，README 互链，内容超过 50 篇深度文档再独立宣传 |
| **图形学 lane 的诱惑**——容易变成生成式 3D 综述 | 严格"是否对具身决策有用"门槛：Genie Sim 收（给 VLA 当数据），Marble 大部分功能不收（用户是人不是机器人）|
| **sensor-physics 不可持续**——你能写 NIR 但不能覆盖全谱 | 第一版只把 active-NIR 写到深度第一，作为 wedge；其他模态慢慢补，不强求一开始就齐全 |
| **某 embodiment 沉寂**——水下论文一年没几篇 | Pulsar pipeline 让其他 embodiment 接力自校准；crossing 章节本身不依赖任一 embodiment 的论文流量 |

---

## 许可证与贡献

CC BY 4.0 · 欢迎 Issue 和 PR：补论文解读 · 真机经验 · sensor 选型实测 · 跨 embodiment 对比案例

---

## 维护者注

**v0 提案版**——本文件是 handbook 设计提案，尚未建立实际仓库。建立顺序建议：

1. 起 `foundations/` 骨架（README + 8 个子目录占位）
2. 写完 5 篇 wedge 文档
3. 复用 Pulsar pipeline，调整 hypothesis registry
4. 发布 v0.1，挂到 VLA-Handbook README
5. 内容超过 30 篇时独立宣传

这本 handbook 真正的 moat 不在论文数量，在三处：
- **crossing/** 5 个章节的对比深度
- **sensor-physics** 这条 industry 没人写的独家轴
- **drone 视角的工程细节**（VIO 振动鲁棒性、SWaP-C 预算、on-board 3DGS）这些 manipulation/AD 圈不会写

守住这三处，handbook 就立得住。
