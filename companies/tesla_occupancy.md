# Tesla Occupancy Network — 纯视觉押注，从公司视角读

**Status:** v1 — opinionated draft。Tesla 内部规格 `UNVERIFIED — 无 datasheet 披露`。架构细节来自公开 AI Day（2021、2022）+ FSD release notes；其余皆为逆向或路线图猜测，已标记。
**TL;DR:** Tesla 在 2022 AI Day 揭示的 occupancy network —— BEV feature volume → 占据体素流水线 —— 是「纯视觉空间 AI」命题在量产规模最公开的工作例。架构有意思；战略主张（永不上 LiDAR）才是争议所在。本手册把架构读作可验证的，把无 LiDAR 哲学读作*成本 / 垂直整合*押注，而非感知物理押注。

---

## 1 · 战略命题（一段话版）

Tesla 从 FSD 项目起就押：**8 路相机 + 雷达（后期纯相机）足以做全自动驾驶**，LiDAR 是拐杖，等同行视觉栈成熟后会被弃用。这个押注靠两条：(a) 感知问题可以靠足够的数据 + 足够的模型 + 足够的算力解决，三样 Tesla 都有规模优势；(b) 纯相机的成本 / 形态 / 垂直整合优势是消费级自动驾驶的唯一路径。

Occupancy network 就是让这个押注在 2022 AI Day 站得住的*技术工件* —— Tesla 用它展示了仅靠相机就能还原 3D 结构、推理时无需 LiDAR ground truth。

---

## 2 · Occupancy network 到底是什么（按 2022 AI Day）

2022 AI Day 揭示的流水线：

```
   8× camera frames (1280×960, 36 Hz `UNVERIFIED`)
            │
            ▼
   ┌──────────────────────────┐
   │  RegNet + BiFPN per-camera │
   │  → 多尺度特征             │
   └──────────────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  Cross-attention 进入     │
   │  3D feature volume        │  ← BEV feature volume,
   │  (occupancy grid)         │     ~150m × 150m × 10m, ~10 cm cell `UNVERIFIED`
   └──────────────────────────┘
            │
            ▼
   ┌──────────────────────────┐
   │  Occupancy head + flow   │  → (占据, 语义, 运动)
   │  + semantic head         │     每体素，每帧
   └──────────────────────────┘
            │
            ▼
   Planner / control 消费体素（无单独的物体列表）
```

关键的架构动作：

**(a) BEV feature volume，不是 object detection。** 输出是 3D 占据栅格 + 每体素语义 + 流。结构上类似 BEVFormer（Li et al. 2022, ECCV）和 DETR3D —— Tesla 把这条血脉在车队规模产品化。

**(b) 每体素 flow。** 每个占据体素带速度向量。这让 planner 能对*任何会动的东西*推理，包括感知系统从未见过标注类别的物体（"general obstacle"）。这是对物体类别长尾问题的优雅逃逸。

**(c) 推理时纯相机。** 训练时用 LiDAR（给占据 ground truth `UNVERIFIED — Tesla 对此一直含糊`），推理时不用。量产车不带 LiDAR 传感器。

| 属性 | 值 `UNVERIFIED` |
|---|---|
| Cameras | 8× |
| 相机分辨率 | 1280×960 |
| 相机速率 | 36 Hz |
| BEV volume 范围 | ~150m × 150m × 10m |
| 体素大小 | ~10 cm |
| 推理速率 | ~36 Hz |
| 推理算力 | HW3 / HW4 车载 SoC |

表里都是 `UNVERIFIED` —— Tesla 没发过 model card 或同行评审论文。AI Day 视频是最接近一手资料的东西。

---

## 3 · 无 LiDAR 哲学 —— 押注 vs 主张

本手册把**工程主张**（仅靠相机的 occupancy network 足以安全驾驶）和**战略押注**（消费车永不上 LiDAR）分开。两者不一样，混着读是最常见的误读。

| 主张 | 证据强度 |
|---|---|
| 「相机能还原密集 3D 结构」 | 强 —— occupancy network 在 Tesla 数据上跑得动；BEVFormer / SurroundOcc 学术血脉佐证 |
| 「相机能还原 3D *和 LiDAR 一样好*」 | 混合 —— 重雨、强光、无路灯夜间会退化；看训练数据覆盖 |
| 「相机足够做安全 FSD」 | 有争议 —— Waymo、Cruise（停摆前）、Mobileye 都选了 LiDAR。Tesla vs LiDAR 阵营的安全数据是*另一个经验问题*，不是架构问题 |
| 「LiDAR 在某年前会过时」 | 路线图猜测 —— `UNVERIFIED`；Tesla 从 2016 年起说过各种版本 |
| 「Tesla occupancy 在某 benchmark 上击败 LiDAR 增强栈」 | 截至 2026-05 无同行评审证据 |

诚实读法：**架构令人印象深刻且有影响力**。战略押注*未决*；由部署统计而非架构来裁决。

---

## 4 · 无 LiDAR 选择的后果

| 后果 | 取舍 |
|---|---|
| BOM 成本更低 | LiDAR 加 ~$500-2000 / 车 `UNVERIFIED`；Tesla 省下 |
| 无主动照明 | 雾天不像 LiDAR 那样退化（LiDAR 雾天也退化）；但重雨下不如 radar / LiDAR 融合 |
| 训练数据是护城河 | 车队按规模产相机 + 标注数据；LiDAR 同行没这个规模 |
| 失效模式*跨所有传感器相关* | 8 路相机共享天气 / 光照失效模式。LiDAR + 相机栈有*不相关*失效模式（一个被强光坑，另一个被雾坑）|
| 推理时无深度 ground truth | 网络得从场景先验学度量深度；分布外场景脆 |

「相关失效」是对纯视觉最强的技术反驳。传感器多样性存在的理由就是「不相关失效是安全关键系统获得可靠性预算的方式」。纯相机是个押注：数据飞轮覆盖最终能糊上相关失效 —— 本手册读这个押注为合理但未证。

---

## 5 · Occupancy network 对领域的影响

尽管 Tesla 不发表，occupancy network 设计的涟漪很大：

- **BEVFormer**（Li et al. 2022, ECCV） —— 同想法的学术版，带代码
- **SurroundOcc**（Wei et al. 2023, ICCV） —— 显式占据体预测
- **OccNet / OccupancyM3D** 血脉 —— 直接占据栅格头
- **NVIDIA Cosmos** —— 用 BEV feature volume 作为 world model 条件之一；见 [`companies/nvidia_cosmos.md`](nvidia_cosmos.md)

架构模式（相机 → 多视编码器 → BEV feature volume → 3D heads）现在是 AD 感知研究主流。Tesla 该拿「先在规模上产品化」的功劳；学术领域该拿「可复现工件」的功劳。

---

## 6 · 两年展望 + 可证伪预测

两件事盯：

**(a) Tesla 是否会发表 model card。** 若是，架构从 "AI Day 幻灯片" 升到可验证。若 2028 前没有，把架构描述当传说。

**(b) 纯相机 FSD 是否能在无 LiDAR 下做到 L4 等效安全。** 这是押注。独立安全统计（不是 Tesla 自报数据）来裁决。

**可证伪预测：** 2027-12 之前，至少有一家中国 AD 厂商（小鹏 / 蔚来 / 华为 ADS）会量产*纯相机* L2++ 栈，并在公开独立 benchmark 上匹敌或超越 Tesla FSD。若没发生，无 LiDAR 命题就是 Tesla 专属；若发生，架构押注成立，LiDAR 阵营面临战略难题。

---

## 7 · 给不同读者的判读

- **机械臂工程师** —— BEV feature volume + 占据栅格是 3D-VLA 体素 tokenization 的概念祖先。见 [`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)。
- **航拍工程师** —— 可直接迁移：Skydio 的障碍图就是占据栅格形状。Tesla 在规模上的设计证明这套模式可产品化。
- **AD 工程师** —— 这是你的文件。配 `companies/wayve_world_model.md` 一起读，看 AD 两套对立押注（相机决定性感知 vs world model 生成式）。
- **传感器选型者** —— §4 相关失效论证是「要不要加 LiDAR」决策最强的输入。仔细读。

---

## References

- Tesla AI Day 2022 — https://www.youtube.com/watch?v=ODSJsviD_SU
- BEVFormer — Li et al. *ECCV 2022*. https://arxiv.org/abs/2203.17270
- SurroundOcc — Wei et al. *ICCV 2023*. https://arxiv.org/abs/2303.09551
- DETR3D — Wang et al. *CoRL 2021*. https://arxiv.org/abs/2110.06922
- 配套：[`companies/wayve_world_model.md`](wayve_world_model.md)
- 配套：[`companies/nvidia_cosmos.md`](nvidia_cosmos.md)

## Boundary

本文是 Tesla 空间 AI 栈的**公司层读法**。BEV feature volume 的逐方法解剖属于 `foundations/feed-forward-3d/` 或新的 `foundations/bev/`。航拍 / 机械臂对占据栅格的复用属于对应的 `embodiments/`。AD 特定部署失效模式属于 `embodiments/driving/`。

---

## 🤖 Moltbot Updates

<!-- Moltbot appends release / news entries below this line. Format: YYYY-MM-DD — one-line event — source URL. -->
