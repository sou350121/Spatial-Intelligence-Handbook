# 空中传感栈 / Aerial Sensor Stack — Payload Class 决定一切

**Status:** v1 — 主观立场草稿。厂商 / 重量 / 成本断言除数据手册引用外均标 `UNVERIFIED`。
**Depth tier:** 🌬️ 维护者锚点（比其他实体轴深 1.5–2×）。
**TL;DR:** 空中传感栈不按 "what's best for perception" 选，按**起飞重量级别**选。250 g 竞速最多 mono + IMU + 气压计；800 g Skydio 级 stereo + IMU + 下视；1.5 kg+ 巡检 / 测绘才负担得起 LiDAR 或主动深度。每跨一档 payload class，传感预算翻倍、自主能力台阶上升、客户也换。本文做空中纵剖——跨实体比较归 [`crossing/sensor-stack-matrix/`](../../../crossing/sensor-stack-matrix/)。

---

## 1 · 为什么 SWaP-C 在空中是头号约束

地面多带 1 kg 影响巡航 5%；空中多带 1 kg 影响续航 30%+，且常突破 FAA Part 107 / EASA 的 250 g / 25 kg 监管边界。Skydio 加 LiDAR 不只是钱，是产品线分级问题：

- **重量**直接乘到续航上
- **功率**挤压 GPU / SoC 预算（10 W vs 60 W = Orin Nano vs AGX Orin）
- **体积**受机壳气动外形约束（前向 stereo baseline 常被机臂限死 7–10 cm）
- **成本**决定 SKU 档位（消费 vs 企业差 10×）

四约束**联立**让"加一颗 sensor"在空中比地面贵 5–10×。栈不是 "more is better"，是 "cleanly clears one payload class boundary"。

---

## 2 · Payload Class × Sensor Stack 总览

| Payload class | 起飞重量 | 代表机型 | 典型传感栈 | 主导自主能力 | 客户类 |
|---|---|---|---|---|---|
| **Racing FPV** | &lt;300 g | DJI Avata 2 (`UNVERIFIED` 重量), UZH 自制 | Mono cam + IMU + 气压计 (+ 可选 event) | VIO @ 200 Hz；reactive policy | 玩家 / 研究 |
| **Cinematography** | 300–800 g | Skydio 2+, DJI Air 3, Autel EVO Lite+ | Surround stereo (4–6 cam) + IMU + 下视 stereo / TOF + GNSS | Obstacle avoidance + ActiveTrack | 消费 / 创作者 |
| **Cinematography Pro / Light Inspection** | 800–1500 g | Skydio X10, DJI Mavic 3 Enterprise, Autel EVO Max 4T | 上 + 多目 stereo + IMU + 主动 TOF + thermal (可选) + GNSS-RTK | 长续航跟踪 + 半结构化巡检 | 企业 / 公共安全 |
| **Inspection / Mapping** | 1.5–3 kg | DJI Matrice 3D / 3DT, Autel EVO Max 4T 重载, Skydio Dock for Enterprise | Stereo + IMU + LiDAR (Livox Mid-360 级) + RGB inspection cam + GNSS-RTK | LiDAR SLAM 测绘 + 离线 3DGS | 测绘 / 基础设施巡检 |
| **Heavy / Industrial** | >3 kg | DJI Matrice 350 RTK, Wingtra Gen II | 同上 + 多负载（多光谱、气体、payload bay） + 冗余 IMU + L1/L2 RTK | 任务级测绘 + 农业 / 矿业 | 工业 / 测绘公司 |

**读法：** 跨一档 payload class，传感栈不是 "加件"，是**整层重建**。

---

## 3 · 三个有代表性的纵剖

### 3.1 250 g 竞速机 — 极简栈

```
  ┌─────────────────────────────────────────────────────────┐
  │ Sensor budget (250 g class)                             │
  │                                                         │
  │   Mono RGB global-shutter cam   (~5–10 g)               │
  │   IMU 6-axis 1 kHz              (~1 g)                  │
  │   Barometer                     (<1 g)                  │
  │   GNSS (single-band)            (~3 g, optional)        │
  │   (optional) Event camera       (~10 g, DVXplorer Mini) │
  │                                                         │
  │   Total sensor weight: ~10–15 g (~5% of takeoff weight) │
  └─────────────────────────────────────────────────────────┘
```

特点：

- **没有 stereo**（baseline 被机臂限死）；**没有 LiDAR**（重量 + 功率双超）。
- 状态估计完全靠 mono + IMU VIO——VINS-Fusion 级 + 赛速 IMU 隔振。
- Event camera 是 UZH 风格的奢侈选项；上了能进高速包络，但成本翻 10×（见 [`../event-camera/`](../event-camera/)）。

自主能力上限是 **course-known 反应式 RL**，不是通用避障。

### 3.2 800 g 电影摄影 — Skydio 级

```
  ┌─────────────────────────────────────────────────────────────┐
  │ Sensor budget (Skydio 2+ / Skydio X10 inferred, 800 g cls)  │
  │                                                             │
  │   6× navigation global-shutter cameras (full surround)      │
  │     — 4× side / 1× up / 1× down (varies)                    │
  │   4K cinema cam (front, gimbal)                             │
  │   IMU 1 kHz, mechanically isolated                          │
  │   Barometer                                                 │
  │   GNSS (dual-band on X10)                                   │
  │   (X10) thermal cam — 640×512 LWIR                          │
  │                                                             │
  │   Total sensor weight: ~50–80 g (~10% of takeoff weight)    │
  │   `UNVERIFIED`                                              │
  └─────────────────────────────────────────────────────────────┘
```

特点：

- **Stereo / Surround 是分界线**——第一档"真避障"出现的位置。
- **下视 stereo 或 TOF**——离地高度 + 落点检测，降落与悬停精度关键。
- **没有 LiDAR**（成本 + 重量撑不住；Skydio X10 是这档天花板）；**没有 RTK**（户外飞行 ≠ 测绘）。

自主能力是 **未知环境避障 + ActiveTrack**。Skydio 与 DJI 在这档拼 planner 集成深度（见 [`../active-tracking/`](../active-tracking/)）。

### 3.3 1.5 kg+ 巡检 — LiDAR + RTK

```
  ┌─────────────────────────────────────────────────────────────┐
  │ Sensor budget (DJI Matrice 3D / Autel EVO Max 4T class)     │
  │                                                             │
  │   Multi-direction stereo (6 obstacle-sensing cams)          │
  │   IMU + redundant IMU on Matrice 350                        │
  │   LiDAR — Livox Mid-360 (~265 g, ~40k pts/s) `UNVERIFIED`   │
  │   RGB inspection / mapping cam (mechanical gimbal)          │
  │   Thermal LWIR / Multispectral payload bay (option)         │
  │   GNSS-RTK dual-band                                        │
  │                                                             │
  │   Total sensor weight: ~400–600 g (~30% of takeoff weight)  │
  └─────────────────────────────────────────────────────────────┘
```

特点：

- **LiDAR 是分界线**——第一档允许 GNSS-denied 长距 SLAM 的栈。
- **RTK 默认**（测绘客户最低 cm-级绝对精度）；**多 payload 接口**这档之下不存在。
- **Surround stereo 仍在**——避障仍走视觉，LiDAR 主要给测绘 / SLAM。

这档进 GNSS-denied 室内 / 隧道巡检的开放问题（见 [`../on-board-mapping/`](../on-board-mapping/)）。

---

## 4 · 哪些"显然要装"的传感其实没出货

| Sensor | 直觉上应该装 | 实际为什么没出货 |
|---|---|---|
| **前视 LiDAR @ 800 g 电影摄影机** | 提升避障 | 重量 + 成本 + 视觉避障已够用 |
| **Event camera @ Skydio 级量产** | 高速 / 低光鲁棒 | 单价 $3–5k `UNVERIFIED`，SDK 生态弱 |
| **Thermal @ 消费机** | 夜飞 / 搜救 | ITAR + 成本；只进企业 SKU |
| **mmWave radar @ 巡检机** | 雾穿透 / 测速 | 信息密度差；视觉 + LiDAR 已覆盖 |
| **主动 NIR (850 nm) flood @ 室内巡检** | 黑暗 stereo 恢复 | 散热 + 眼安全（IEC 60825-1）、续航代价；见 [`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`](../../../foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md) |
| **多光谱 @ 消费机** | 植被健康 / NDVI | 消费侧无市场 |

诚实读法：**这些不是"还没有"，是"被市场否决了"**——不是技术问题，是 SWaP-C × 客户预算乘积太小。

---

## 5 · 两个常见误读

**误读 1：消费机加更多 sensor 就会更智能。** 错。Skydio X10 已是这档天花板，再加 LiDAR 要付续航 / 价格 / 重量代价，而消费客户"智能"感知曲线已饱和。

**误读 2：LiDAR 是巡检机的"主"传感。** 错。巡检机主传感**仍是视觉**（避障 + 跟踪 + 客户交付物）；LiDAR 是**测绘负载**——服务离线 deliverable，不是 inner-loop 自主。

---

## 6 · 2027 前会变的

- **Event camera 价格下穿 $500** — 触发消费机以"高速 / 低光选配"出货 (`UNVERIFIED`)。
- **固态 LiDAR 重量 &lt;150 g** — 让 800 g 电影机第一次能负担 LiDAR；改 Skydio X10 / DJI Mavic Pro 档的栈结构。
- **VGGT 级 feed-forward 3D 在 Orin Nano 上 &lt;50 ms** — 低端机第一次有 "feed-forward 全局重定位" 选项（见 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)）。
- **主动 NIR flood 眼安全 LED 模块小型化** — 室内黑暗巡检栈第一次可工业化。

**可证伪预测：** 2027-06 之前会有一台 800 g 级机首次出货前视 LiDAR——但只在企业 SKU，不在消费 SKU。

---

## 7 · 给读者的指引

- **机械臂工程师** — 你的传感预算几乎无限。不要把"加一颗 RealSense"的轻松感带进空中。
- **AD 工程师** — 你的预算也富但分布外周；空中 sensor 都顶载。LiDAR 机械式 vs 固态逻辑对空中参考有限——空中固态几乎唯一。
- **空中工程师** — 选栈之前先选 payload class；选 payload class 之前先选客户。倒着推栈基本确定。
- **研究者** — 250 g 竞速档的"add one sensor"是当前最大开放轴：event camera 走通了，下一颗是什么？取决于谁先做出 50 g 级模块。

---

## References

- **Skydio X10 / DJI Matrice 3D / 350 RTK / Mavic 3 Enterprise / Autel EVO Max 4T 产品页** — 厂商源。`UNVERIFIED, no DOI`
- **Livox Mid-360 数据手册** — 厂商源。`UNVERIFIED, no DOI`
- **Prophesee Gen4 evaluation kit pricing** — 厂商源。`UNVERIFIED, no DOI`
- **IEC 60825-1 激光安全标准** — 见 [`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`](../../../foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md)
- **跨实体 sensor 矩阵** — [`crossing/sensor-stack-matrix/`](../../../crossing/sensor-stack-matrix/)
- **VIO / 事件相机基线** — [`../vio/`](../vio/), [`../event-camera/`](../event-camera/)

## Boundary

本文做**空中实体内的 sensor stack 纵剖**——payload class 决定栈。跨实体横向比较归 [`crossing/sensor-stack-matrix/`](../../../crossing/sensor-stack-matrix/)。单一 sensor 物理 / 数据手册 / 眼安全等级归 [`foundations/sensor-physics/`](../../../foundations/sensor-physics/)。SLAM / VIO 算法在不同 sensor 上的表现归 [`../vio/`](../vio/)、[`../on-board-mapping/`](../on-board-mapping/)。`cheat-sheet/sensor-budget-matrix.md` 是人工核算总览，自动 agent 不改。
