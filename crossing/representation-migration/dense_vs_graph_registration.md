# Dense vs Graph Registration — 5 种表征的配准怎么选 (Dense vs Graph Registration — Choosing across 5 Representations)

> **类型**: comparison（cross-zone, representation-migration）— 不走 14 项 dissection 门槛
> **聚焦**: 不同表征下「3D registration」是不同问题；本文给 5 法对照 + 决策树
> **Status**: v1 — 2026-05-22。具体 benchmark 数字标 UNVERIFIED 除非有 paper Table 引用

**TL;DR.** 「3D registration」在 dense point / super-point / sparse keypoint / object graph 四种粒度下是**四个不同的问题**。本文用 5 个代表方法（TEASER++ / FCGF / GeoTransformer / RoITr / SG-Reg）拉开输入粒度、带宽、监督方式、benchmark、license 五轴。**最被忽视的轴是带宽**：SG-Reg 一次 graph 上传 ≈52 KB（`UNVERIFIED`），同场景 dense 描述子几十 MB —— multi-agent SLAM / 5G uplink / edge deploy 上是数量级差。

**X-Ray.** 「估 SE(3) 把两张 3D 观测对齐」一句话覆盖至少 4 个不相容子问题：dense 每点匹配（FCGF）/ super-point patch 匹配（GeoT, RoITr）/ sparse keypoint + 鲁棒求解（TEASER++）/ 物体图节点匹配（SG-Reg, 4-DoF）。benchmark、license、失败模式都不同 —— **不能用 3DMatch recall 排座次**。

---

## 问题定义

给定两个 3D 观测 A、B，估 SE(3) 变换 T 使 `T·A ≈ B`。表征不同，「≈」含义不同：

| 表征粒度 | "对齐"的含义 | 典型应用 |
|---|---|---|
| **dense point** | 每点最近邻对应，最小化 point-to-point | 室内 RGBD reconstruction |
| **super-point** | patch-level 粗匹配 + fine matching | 3DMatch / KITTI SOTA |
| **sparse keypoint** | 关键点 + 描述子 + 鲁棒求解器 | 工业 SfM / LiDAR registration |
| **object graph** | 节点 1-1 对齐 + 位姿一致 | Multi-agent SLAM / loop closure |
| **dense feature volume** | feature volume 对齐（NeRF / 3DGS） | 跨视角 reconstruction（非本文） |

**核心论点**：0.1 m point-to-point 误差对 manipulation 是失败，对 multi-agent SLAM loop closure 是成功 —— **「准确」的定义随粒度变**。

---

## §1 · 5 种表征方法

### TEASER++ (Yang & Carlone 2020, T-RO 2021)
- **输入 / 核心**: sparse FPFH keypoints (1k-5k) → truncated least squares + adaptive voting，抗 **99%** outlier
- **特色**: 无学习；certifiable optimality
- **用法**: SfM 后处理 / LiDAR registration / 工业测量
- [arXiv 2001.07715](https://arxiv.org/abs/2001.07715) · [GitHub MIT-SPARK/TEASER-plusplus](https://github.com/MIT-SPARK/TEASER-plusplus)（MIT）

### FCGF — Fully Convolutional Geometric Features (Choy et al. ICCV 2019)
- **输入 / 核心**: dense 点云（每点 32-D 描述子） → sparse 3D conv (Minkowski) + hardest contrastive
- **特色**: 第一个把 metric learning 做到 dense 点云
- **用法**: 室内 RGBD (3DMatch) / 户外 LiDAR (KITTI)
- [arXiv 1909.06289](https://arxiv.org/abs/1909.06289) · [GitHub chrischoy/FCGF](https://github.com/chrischoy/FCGF)（MIT）

### GeoTransformer (Qin et al. CVPR 2022)
- **输入 / 核心**: super-points patch embedding → geometric self-attention (pairwise distance + angle) + coarse-to-fine matching
- **特色**: 不需 RANSAC（local-to-global）；3DMatch / KITTI 当时 SOTA
- [arXiv 2202.06688](https://arxiv.org/abs/2202.06688) · [GitHub qinzheng93/GeoTransformer](https://github.com/qinzheng93/GeoTransformer)（MIT）

### RoITr — Rotation-Invariant Transformer (Yu et al. CVPR 2023 Highlight)
- **输入 / 核心**: super-points + RoI 局部坐标系 → rotation-invariant frame + cross attention
- **特色**: 任意旋转下 recall 不掉；跨 session re-localization 友好
- [arXiv 2303.08231](https://arxiv.org/abs/2303.08231) · [GitHub haoyu94/RoITr](https://github.com/haoyu94/RoITr)（license `UNVERIFIED`，README 标 MIT）

### SG-Reg — Scene Graph Registration (Liu et al. T-RO 2025)
- **输入 / 核心**: 两张 scene graph（节点 = 物体 + 语义 + centroid） → BERT caption + GNN 上下文 + Optimal Transport + 4-DoF 求解
- **特色**: 物体级配准，带宽 ≈52 KB / graph (`UNVERIFIED`)，天然适合 multi-agent
- [arXiv 2504.14440](https://arxiv.org/abs/2504.14440) · [GitHub HKUST-Aerial-Robotics/SG-Reg](https://github.com/HKUST-Aerial-Robotics/SG-Reg)（**GPLv3**）

---

## §2 · 横向对比表（5 法 × 多维度）

| 维度 | TEASER++ | FCGF | GeoT | RoITr | SG-Reg |
|---|---|---|---|---|---|
| 表征粒度 | sparse keypoint | dense point | super-point | super-point + RoI | object graph |
| 典型节点数 | 1k-5k | ~30k 点 | 256-1024 | 256-1024 | 10-100 物体 |
| 每观测带宽 | 数 MB FPFH 33-D | 数十 MB `UNVERIFIED` | ~1-10 MB | ~1-10 MB | **~52 KB `UNVERIFIED`** |
| 学习化 | ❌ 纯几何 | ✅ contrastive | ✅ Transformer | ✅ Transformer | ✅ BERT+GNN+OT |
| 监督 | n/a | GT corr. | GT overlap | GT overlap | caption + GT pose |
| 需 semantic | ❌ | ❌ | ❌ | ❌ | ✅ |
| DoF | 6 | 6 | 6 | 6 | **4** (yaw+xyz) |
| 鲁棒求解器 | truncated LS | RANSAC | local-to-global | local-to-global | OT + 4-DoF SVD |
| 抗 outlier | **99%** | 中 | 高 | 高 | 节点级 |
| benchmark | KITTI/工业 | 3DMatch/KITTI | 3DMatch/KITTI/3DLoMatch | 3DMatch/3DLoMatch | **3RScan/RIO** |
| 3DMatch FMR `UNVERIFIED` | ~85% | ~95% | ~98% | ~98% | n/a |
| License | MIT | MIT | MIT | MIT `UNVERIFIED` | **GPLv3** ⚠️ |
| 何时用 | SfM outlier 多 | dense 重建 | RGBD SOTA | 任意旋转 | multi-agent 带宽紧 |
| 何时不用 | 需 fine matching | sym / textureless | sparse 输入 | 不显著优于 GeoT | 无语义标签 |

**三条不能合并的 benchmark 轴**：3DMatch / KITTI 是 dense + super-point 赛场（TEASER 输因 FPFH 不为 indoor 优化）；3DLoMatch (low overlap) 才显出 GeoT / RoITr 真本事；3RScan / RIO 是 scene graph 赛场，SG-Reg 不在 3DMatch 数字上不是因为弱，**问题不一样**。

---

## §3 · 决策树

```
输入 / 约束                                推荐
──────────────────────────────────────────────────────────────
dense RGBD, overlap >30%             ─► GeoTransformer (3DMatch SOTA)
dense, overlap <30% (3DLoMatch)      ─► RoITr 或 GeoT + 多 hypothesis
任意旋转 (视角 >90°)                 ─► RoITr (rotation-invariant)
工业 SfM / LiDAR, outlier >50%       ─► TEASER++ (99% outlier 抗性)
多 agent SLAM, 带宽 <1 MB            ─► SG-Reg (52 KB) 或 NetVLAD only
Jetson / 手机, 不能 sparse conv      ─► TEASER++ (CPU OK) 或 SG-Reg
跨 session re-localization           ─► SG-Reg (语义稳) 或 RoITr (几何稳)
离线单机 reconstruction              ─► FCGF / GeoT + ICP refine
```

**反模式**：拿 SG-Reg 跑 3DMatch 然后说"输了"（benchmark 不匹配）；拿 TEASER++ 当 fine matching（它是 outlier rejection 不是 sub-cm refine）；GPLv3 的 SG-Reg 进闭源商业 SLAM stack（license 不兼容）；用 GeoT 给 multi-agent 带宽受限场景（patch embedding 太重）。

---

## §4 · 共同失败模式

| 失败模式 | TEASER++ | FCGF | GeoT | RoITr | SG-Reg |
|---|:---:|:---:|:---:|:---:|:---:|
| symmetric (对称走廊/圆桌) | ❌ | ❌ | ❌ | ⚠️ | ⚠️ |
| textureless (白墙) | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ 不依赖纹理 |
| large viewpoint gap (>120°) | ⚠️ | ❌ | ❌ | ✅ 设计目标 | ✅ 物体不变 |
| low overlap (<30%) | ⚠️ | ❌ | ✅ 3DLoMatch | ✅ | ✅ |
| dynamic objects (人/椅换位) | ⚠️ | ❌ | ❌ | ❌ | ⚠️ |
| 跨域 (室内训→室外用) | ✅ 无训练 | ❌ | ❌ | ⚠️ | ❌ caption 偏 |
| OOD 语义类别 | n/a | n/a | n/a | n/a | ❌ BERT OOD |

**一句话**：TEASER++ 不学就不会过拟合但精度上限低；FCGF / GeoT / RoITr in-distribution 强、跨域脆；SG-Reg 用语义作为新的不变性来源 —— 同时是它 textureless / large gap 上赢的原因和 OOD 类别下输的原因。

---

## §5 · 一个被忽视的维度：带宽 vs 精度

```
bandwidth (log)    精度
─────────────      ────────
100 MB  FCGF dense
 10 MB  GeoT / RoITr super-point
  1 MB  TEASER++ FPFH
 52 KB  SG-Reg graph     `UNVERIFIED`
 10 KB  NetVLAD only (no geometry)
```

**4 个场景下带宽从可忽略变决定性**：(1) Multi-agent SLAM — N agent 互相 query，带宽 ∝ N²，SG-Reg 52 KB vs FCGF 几十 MB ≈ 1000×；(2) 5G/4G uplink — 上传 map fragment，FCGF 级别上不去；(3) Jetson / 手机 — 大描述子 RAM 超限；(4) Cold-start 跨设备 — 先 exchange 地图指纹。**反向**：单机离线 reconstruction，带宽不重要，FCGF / GeoT 直接 win。

**学界 vs 工业失配**：3DMatch / KITTI 评 recall / RTE / RRE，**不评带宽**。这解释了 SG-Reg 类 graph 方法在学术 benchmark 看似不存在，却在 multi-agent 实战里被反复独立发明。

---

## §6 · SG-Reg 为什么 handbook 还没给 14 项 dissection

诚实交代：SG-Reg 是本文唯一一个**没进 foundations dissection**的方法。

| 检查项 | 状态 |
|---|---|
| 论文质量 | T-RO 2025 一区 ✅ |
| star 数 | 137★（`UNVERIFIED`，仍属新仓） |
| issue 健康 | 3 open / 0 closed `UNVERIFIED` —— 缺社区反馈 |
| 预训练 weights | 无 HuggingFace 镜像 —— 复现门槛 |
| license | **GPLv3** —— 商业不友好 |
| benchmark 覆盖 | 3RScan / RIO，不在 3DMatch / KITTI —— 难与主流对比 |

**当前定位**：`foundations/semantic-3d/README.md` watch list；待社区在 multi-agent SLAM 上独立复现（Kimera-Multi / LAMP team cite）或 star 越过 ~500 再升级。Handbook 政策：**先看到下游用，再深拆**。

---

## §7 · 何时学习化反而输经典

| 场景 | 经典赢家 | 学习化为什么输 |
|---|---|---|
| 工业 LiDAR（已知传感器 + 标定） | RANSAC + ICP/GICP | 跨传感器 generalize 差 |
| SfM 后处理（已有 SIFT/SuperPoint match） | TEASER++ | 重复造轮子，无 certifiable optimality |
| 超高精度（亚毫米） | ICP + plane-to-plane | sub-cm 上限被描述子量化卡住 |
| 跨域零先验（医疗 vs 室内训练） | FPFH + TEASER++ | distribution shift 直接崩 |
| CPU only / 嵌入式 | TEASER++ / Open3D ICP | sparse conv 需 GPU |
| 算法证书 / 可解释 | TEASER++ | 黑盒 Transformer 不能给 optimality 证明 |

**判断启发**：输入分布稳定 + 精度要求极高 + 部署受限，三条命中 ≥2，**先试经典**。学习化真正优势在 low-overlap / textureless / cross-session generalize —— 经典在这些 case 才真的输。

---

## Boundary

- 单方法深拆 → `foundations/semantic-3d/`（SG-Reg watch list）/ `foundations/feed-forward-3d/`（VGGT internal tracking 是另一条配准路）
- Loop closure 经典栈 → [`../../foundations/classical-slam/orb_slam3_dissection.md`](../../foundations/classical-slam/orb_slam3_dissection.md)（DBoW2 vs 学习化 place recognition）
- Per-embodiment 应用（manipulation grasp / AD HD-map alignment）→ `embodiments/<emb>/`

## Cross-references

- [`../../foundations/semantic-3d/README.md`](../../foundations/semantic-3d/README.md) — SG-Reg watch list
- [`../../foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../../foundations/feed-forward-3d/vggt_cvpr2025_dissection.md) — 不显式 SE(3) 的配准
- [`../../foundations/classical-slam/orb_slam3_dissection.md`](../../foundations/classical-slam/orb_slam3_dissection.md) — loop closure 上下文
- [`./3dgs_as_simulator_comparison.md`](./3dgs_as_simulator_comparison.md) — 同 zone comparison 范例

## For the reader

- **Manipulation** — grasp 场景大概率 GeoT + ICP refine 够；TEASER++ 留给标定异常排查
- **Aerial** — LiDAR-LiDAR 单机 GeoT / RoITr；跨 drone loop closure 看 SG-Reg / NetVLAD
- **AD** — HD-map alignment 仍 ICP + GICP 主流；学习化在 ramp / 长隧道 GNSS 失锁场景有 niche
- **Multi-agent SLAM** — 带宽最大约束，SG-Reg 类 graph 方法是 2026 必看
- **Researcher** — 学界最大盲点是跨 benchmark 不公平比较；下一篇好 paper 应建带宽-精度联合 benchmark

---

## References

主要 5 法的 paper / repo 已在 §1 内联给出。Benchmark：3DMatch (Zeng et al. CVPR 2017) · 3DLoMatch (Huang et al. CVPR 2021, PREDATOR) · 3RScan / RIO (Wald et al. ICCV 2019)。

---

*Last opinion update: 2026-05-22. 具体 recall / KB 数字若无 paper Table 直引，统一标 `UNVERIFIED`；带宽量级判断基于描述子维度 × 节点数推算，非实测。*

---

[← Back to crossing/](../README.md)
