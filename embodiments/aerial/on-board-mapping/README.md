# 板载空中建图 / On-Board Aerial Mapping — 3DGS、LiDAR SLAM 与 GNSS-denied 长距

**Status:** v1 — 主观立场草稿。算力 / 延迟数字除引用数据手册外均标 `UNVERIFIED`。
**Depth tier:** 🌬️ 维护者锚点（比其他实体轴深 1.5–2×）。
**Scope note:** 本文吸收了原本会写在 `long-range-slam/` 的内容——两者共享 compute / sensor / GNSS-denied 约束，拆开会两边都薄。
**TL;DR:** 板载建图是唯一一个 compute 预算与 SWaP-C 像精度一样主导算法选择的实体。2026 分野：**3DGS** 在纹理丰富、需要颜色、有 AGX 级算力（~60 W）的场景胜出（高端巡检、测绘机）；**LiDAR SLAM（FAST-LIO2 谱系）**在几何为主、长距、GNSS-denied、主动测距比颜色更重要的场景胜出；**纯视觉惯性融合**只在最低 payload 档位胜出（既负担不起 GPU 也负担不起 LiDAR）。Jetson Orin Nano（~10 W）上的实时 3DGS 对室内 / 短距已可行；长距户外 + 飞行速度下的 3DGS **暂时**离不开 AGX 级 GPU。

---

## 1 · 为什么空中建图与其他场景不同

- **算力被 SWaP-C 硬约束**，不被货架上能买到什么约束。250 g 竞速机背不动 AGX Orin；1.5 kg 巡检机可以。地图表示选择是 payload class 的下游，不是算法偏好。
- **地图有两个客户**，常常需求冲突：*自主栈*（要快几何障碍查询、低延迟、不要颜色）与 *交付物*（要高保真颜色、稠密表面、给人看）。
- **闭环更难。** 一架无人机可能飞 1 km 户外不复访任何视点。GNSS 提供全局锚点；没它（室内巡检、城市峡谷）漂移会累积且无恢复面。
- **地图飞行中会老化。** 30 分钟飞行中不断增长的点云最终会撑爆 Orin Nano 的内存。地图抽取 / 滑窗保留是头等问题，不是事后补丁。

---

## 2 · 算力切分（决定架构的那个数字）

| 平台档 | 典型 SoC | 持续 GPU 功耗 | 现实可行的板载建图 |
|---|---|---|---|
| Racing FPV (<300 g) | 自制 MCU + 可选 Nano | <5 W to GPU | 无地图。只跑 VIO 状态。 |
| Cinematography (300–800 g, Skydio 级) | Jetson Orin Nano `UNVERIFIED` | ~10 W | 局部 occupancy + 稀疏 landmark；3DGS 仅限小场景 + 室内 |
| Inspection / mapping (800–1500 g, Autel EVO / DJI Matrice 3D) | Orin NX 或 AGX Orin `UNVERIFIED` | 25–60 W | LiDAR SLAM (FAST-LIO2) +（可选）落地时周期性 3DGS |
| Industrial mapping (>1.5 kg, DJI Matrice 350 RTK, Wingtra) | AGX Orin 或 x86 companion | 60 W+ | 全 LiDAR + 摄影测量；3DGS 通常在地面站后处理 |

两点这表说得明白：

1. **飞行速度下的实时 3DGS 是顶档命题。** AGX Orin 以下，要么离线做，要么接受不完整场景。
2. **2026 "严肃"无人机的默认板载实时地图是 LiDAR SLAM**，不是 3DGS、不是 NeRF。原因不是偏好——是 60 W 预算。

---

## 3 · 何时 3DGS 胜 LiDAR SLAM

3DGS 在无人机上赢得一席之地的充要条件：

- **纹理丰富。** 无特征墙 / 雪 / 开阔水面会让它崩（与单目 VIO 崩的原因相同）。
- **颜色是交付物的一部分。** 立面巡检、植被健康、考古遗址——LiDAR 不捕获反照率。
- **范围有界（典型作业距表面 <50 m）。** 长距户外 3DGS 在板载飞行速度下未被证明 `UNVERIFIED`。
- **无人机有时间停留。** 3DGS 质量受停留时间限制；快速掠过比缓慢绕飞产出差。

3DGS *输*给 LiDAR SLAM 的情况：

- 无人机处于低光或纹理退化场景（仓库、隧道、扬尘）。
- 需要远距障碍查询（>30 m）保证安全。
- 地图必须可被经典运动规划器查询——LiDAR + occupancy grid 干净接入；3DGS 查询难得多。

诚实的 2026 答案：**3DGS 是交付物地图；LiDAR 是自主地图。** 高级栈两者都跑。

---

## 4 · Jetson 上的实时 3DGS——真实数字

Jetson 级硬件（Orin Nano / NX）上公开的 3DGS 工作显示：

| 硬件 | 板载可达模式（2026） | 注意 |
|---|---|---|
| Orin Nano 8 GB (~10 W) | 小室内场景增量 3DGS 更新 ~5–10 Hz `UNVERIFIED` | 内存预算上限约 500K Gaussian；首次复访质量退化 |
| Orin NX 16 GB (~25 W) | 房间级 ~15–30 Hz 更新；全场景 Gaussian 数到 ~2M `UNVERIFIED` | 功耗明显影响续航 |
| AGX Orin 64 GB (~60 W) | 飞行速度下房间-到-楼层尺度实时 | Payload class 限制哪种机能装 |

要看的谱系是 *增量高斯泼溅 / Gaussian SLAM* 一支（MonoGS、SplaTAM、Gaussian-SLAM）。它们都不是 aerial-first；都假设运动比无人机慢。aerial-specific 的论文还没落地 `UNVERIFIED`。

```
  ┌───────────────────────────────────────────────────────────────────┐
  │ 混合板载模式（高端巡检机，2026）                                  │
  │                                                                   │
  │  Stereo + IMU                                                     │
  │      │                                                            │
  │      ▼                                                            │
  │  VIO (200 Hz state)  ──────►  Controller                          │
  │      │                                                            │
  │      ▼                                                            │
  │  LiDAR + IMU  ─►  FAST-LIO2  ─►  Occupancy grid (autonomy map)    │
  │                       │                                           │
  │                       └──►  Pose graph                            │
  │                                  │                                │
  │                                  ▼                                │
  │  RGB + pose  ─►  Incremental 3DGS (deliverable map, ~5 Hz)        │
  └───────────────────────────────────────────────────────────────────┘
```

---

## 5 · GNSS-denied 长距——没人明说的硬问题

室内巡检、城市峡谷、地下、隧道飞行都共享一个约束：**无 GNSS 锚点**。SOTA VIO 的漂移增长率约 0.5–2% / 行程距离 `UNVERIFIED`。1 km 行程累积 5–20 m 误差——超过可用 as-built 建图的临界，必须修正。

2026 出货模式：

| 模式 | 出货于 | 约束 |
|---|---|---|
| **视觉闭环** | 户外 / 有复访的城市 | 需要实际复访；并非总能 |
| **LiDAR 闭环**（Scan Context、LoGG3D-Net） | 室内 / 结构化户外 | 需要明显几何；走廊难 |
| **基准 marker** | 工业巡检（可控站点） | 需要现场布置 |
| **周期 GNSS 航点** | 室内外混合（起终点已知） | 需要端点对天可见 |
| **地图先验 + 重定位**（CAD 或先前 3DGS） | 重测工作流 | 需要先验；首测开放 |
| **UWB 锚点** | 仓库 / 工业 | 需要现场基础设施 |

诚实的读法：**>100 m 级的首测、无先验、无基础设施、室内/地下建图仍是开放问题。** 无公开栈在不靠上述任一拐杖下解决。

DJI Matrice 3D 与 Autel EVO Max 4T 默认上 RTK + LiDAR；他们的答案是"默认有 GNSS 并优雅退化"。Skydio 的自主巡检机（X10、Dock for Enterprise）依赖视觉闭环 + 偶发 GNSS 重获取。两家都不公开闭环阈值。

---

## 6 · VGGT 级 feed-forward 3D 何时进板载？

今天：不在飞行速度下。延迟故事见 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)。

到 2027，feed-forward 3D 在板载建图里**可能**贡献的：

- **初始化** — 用 feed-forward 解前 5–20 帧，更快引导经典 SLAM。
- **纹理丰富重定位** — 经典失败（kidnap、track loss）时丢一个 VGGT 解。
- **离线地面站升级** — 用 VGGT 重处理飞行日志产生更高质量交付地图。

板载实时主建图用 VGGT 级模型是 2028+ 命题，按当前轨迹。

---

## 7 · 给读者的指引

- **机械臂工程师** — 3DGS 在你桌面跑得动，是因为你有 100+ W 和场景装得进盒子。不要把这种舒适带进空中。
- **AD 工程师** — 你的板载地图是 HD-map 先验 + 在线 occupancy。空中大多没先验；最近的类比是无地图场的自主货运卡车。
- **空中工程师** — 按谁消费选地图。两张地图（自主 + 交付物）OK；一张图同时干两件事通常比分开做更差。
- **研究者** — Orin NX 飞行速度下、对纹理退化优雅降级的 aerial-native 增量 3DGS 是开放且可解的问题。谁先发出规范论文，谁拥有这块。

---

## References

- **FAST-LIO2** — Xu et al. *T-RO 2022*. [arXiv 2107.06829](https://arxiv.org/abs/2107.06829)
- **3D Gaussian Splatting** — Kerbl et al. *SIGGRAPH 2023*. [arXiv 2308.04079](https://arxiv.org/abs/2308.04079)
- **MonoGS** — Matsuki et al. *CVPR 2024*. [arXiv 2312.06741](https://arxiv.org/abs/2312.06741)
- **SplaTAM** — Keetha et al. *CVPR 2024*. [arXiv 2312.02126](https://arxiv.org/abs/2312.02126)
- **Scan Context** — Kim & Kim *IROS 2018*. [arXiv 1810.04287](https://arxiv.org/abs/1810.04287)
- **VGGT cross-ref** — [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)
- **DJI Matrice 3D / 350 RTK 产品页**, **Autel EVO Max 4T 产品页** — 厂商源。`UNVERIFIED, no DOI`

## Boundary

本文覆盖 *板载* 空中建图——飞行时跑在无人机上的部分。地面站后处理（全质量 3DGS、Pix4D / RealityCapture 摄影测量流水线）不在范围。Per-method 剖析（MonoGS、FAST-LIO2 等）在 [`foundations/`](../../../foundations/)。跨实体的"何时 3DGS 胜 NeRF 胜经典深度"在 [`foundations/3dgs/`](../../../foundations/3dgs/) 与 [`crossing/`](../../../crossing/)。Long-range SLAM 在此吸收而不拆出 `long-range-slam/`——compute 与 GNSS-denial 约束与建图选择不可分。Sensor-stack 权衡（LiDAR 档、stereo baseline）在 [`../sensor-stack/`](../sensor-stack/)。
