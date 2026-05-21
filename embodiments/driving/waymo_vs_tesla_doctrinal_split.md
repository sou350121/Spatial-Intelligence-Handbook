# Waymo vs Tesla：自动驾驶空间表征的两条道路 (The Doctrinal Split)

> **发布时间**：2026-05-21
> **核心定位**：本文**不是**自动驾驶综述，而是从**空间 representation** 角度看 Waymo 学派与 Tesla 学派为何分歧、各自的假设链是什么、以及 2026 年这场分歧的状态如何。
> **TL;DR**：Waymo 学派把空间问题拆成 `LiDAR 点云 + HD 地图 + 显式感知 stack`——结构化、可审计、可保险定价；Tesla 学派把空间问题压成 `8 摄像头 → 占用网络 → end-to-end`——可扩展、可迭代、可监督学习。这不只是传感器选择，是**世界建模的认识论**之争。

**状态：** v1 —— 有立场的草稿。涉及商用规格全部 `UNVERIFIED`。

---

**X-Ray 开场：** 同一道路、同一物理世界、同样的"L4 自动驾驶"目标，Waymo 与 Tesla 给出了**几乎完全不重叠的工程栈**。两家都在量产规模上验证了各自路线（Waymo 数百辆 Robotaxi 在 SF/PHX/LA，Tesla 数百万辆 FSD beta 车），所以这不是"一家错了"的故事，而是两套对空间问题的**不同认识论**在不同 deployment niche 上各自自洽。对 spatial researcher 意味着：**先选传感器物理 + 数据规模 → 才能决定该用什么 representation**，反过来选会失败。

---

## 📍 研究全景时间线

```
2009 ─ Google Self-Driving Car (Waymo 前身) 起步
        │ ⚡ 选择 LiDAR + HD map：因为深度学习还不存在
2013 ─ Tesla Model S Autopilot v1 (Mobileye EyeQ3) ─ pure vision
        │
2017 ─ Waymo first Robotaxi pilot (Chandler, AZ)
        │
2019 ─ Tesla Autonomy Day — 宣布 vision-only roadmap
        │ ⚡ Andrej Karpathy: "humans drive with eyes, so should cars"
2021 ─ Tesla 移除雷达，nav-only vision
        │ Occupancy Network 论文/演讲
2022 ─ Waymo 推 Driver 5th gen — 更便宜 LiDAR + camera
        │ Tesla FSD v11 — bird's eye view network → 占用网络
2023 ─ Waymo 商业化 SF/PHX；Tesla FSD v12 — end-to-end neural net
        │ ⚡ Tesla 移除 30 万行 C++ 规则代码，全部 NN
2024 ─ Waymo + Geely / Zeekr 全球扩张；Tesla Robotaxi day (8月)
        │
2025 ─ Cosmos / Wayve GAIA-2 — 世界模型路线开始威胁两家
        │
2026 ─ 本文位置：分歧没有收敛，但 vision-only 在受限场景已经够用
        └─ 局限：城市级别 + 极端天气 + 长尾事件，没有公开证据证明哪派稳赢
```

---

## 1 · 核心架构对比

### 1.1 系统对比概览

| 模块 | Waymo (Driver 5th gen) | Tesla (FSD v12+) |
|---|---|---|
| 主传感器 | 5 LiDAR + 29 摄像头 + 6 雷达 | 8 摄像头（无 LiDAR、无雷达 since 2021） |
| 深度来源 | LiDAR 直接（米级精度，200 m+ 距离） | 视觉推理（占用网络，端到端） |
| 先验地图 | HD map（厘米级，预扫描） | 无 HD map，仅 nav-level（Google Maps 级） |
| 感知栈 | 模块化：detect → track → predict | end-to-end NN（v12 起） |
| 表征 | 物体级（3D bbox + class + track） | 占用 + free space + neural feature |
| 规划 | 显式 rule-based + ML hybrid | 神经网络规划（v12+） |
| 仿真验证 | CarCraft 仿真 + 真车（>2000 万 mi `UNVERIFIED`） | 影子模式（百万辆车数据） |
| 单车 BOM | ~$100k+ `UNVERIFIED` | 仅摄像头 + Hardware 4 SoC |
| 部署 niche | 地理围栏内 L4 | 全球可用 L2+ (claim L4 future) |

### 1.2 关键机制：两种"空间真值"的来源

⚡ **Eureka Moment**：Waymo 的空间真值来自 **sensor physics**（LiDAR 飞行时间），Tesla 的空间真值来自 **data scale**（百万车队的自监督深度）。两者都是 valid 路线，但**前者的瓶颈是地图维护成本，后者的瓶颈是长尾覆盖**。

Waymo 的逻辑链：
1. LiDAR 给你**直接 3D**，深度误差物理决定（不是模型误差）
2. HD map 给你**先验**，让感知只做差异检测（"这一帧与 map 多了什么？"）
3. 因此感知/规划可以模块化、可审计、可证伪
4. 代价：地图维护、新区域开通成本高

Tesla 的逻辑链：
1. 摄像头便宜，量产车队规模 = 数据规模
2. 占用网络从 8 cam → 体素，避开了 LiDAR 但保留了 3D 表达
3. v12 全 NN，让"长尾"问题降为"数据问题"——足够数据，模型就能学到
4. 代价：可解释性、保险定价、监管对话困难

### 1.3 数据流对比

```
Waymo:
  LiDAR / Cam / Radar ──► sensor fusion ──► 3D detect ──► track ──► predict ──► plan
                                  ▲
                          HD Map (offline)

Tesla (v12+):
  8 Cam (12 Hz) ──► HydraNet backbone ──► occupancy ──► neural planner ──► action
                                        ──► lanes/objects (aux heads)
                                        ──► free space
```

---

## 2 · 数学核心：占用网络的空间表征

📌 **Napkin Formula**：`P(occupied | voxel_xyz, image_features) = σ(MLP(query_voxel, multi-view_attention(images)))`——把"3D 体素是否被占"建成可微的视觉查询。

Tesla 占用网络（Karpathy 2022 演讲披露）的关键：
- 体素分辨率：~10 cm `UNVERIFIED`，体积 200 m × 200 m × 20 m
- 输出：每个体素的占用概率 + 语义 class + flow（动 / 静）
- 训练真值：自动标注 pipeline——用未来 N 帧的运动反推过去帧的体素 ground truth

Waymo 的 LiDAR 直接给出 3D 点云，但**仍然需要类似的占用表达**做长尾物体（掉落货物、动物）——所以 Waymo 内部也有 occupancy head，只是不作为主信号。

---

## 3 · 带数字走一遍：左转盲区玩具例子

场景：左转，对向车被 truck 遮挡。

- **Waymo**：LiDAR 直接看到 truck 后**没有**对向车 → free space。`P(碰撞) = LiDAR coverage × map_prior × prediction_uncertainty` ~ 已知。**LiDAR 边界 = 决策边界**。
- **Tesla**：8 cam 看到 truck 边缘 → 占用网络在 truck 后预测**未知体素**（不是 occupied，不是 free，是 unknown）→ neural planner 学过类似场景，输出"探头慢探"行为。

哪个更好？Waymo 路线在 LiDAR 看不见的情况下**保守**（停车）；Tesla 路线**模仿人类**（慢探）。前者更安全，后者更接近通行能力。这就是为什么 Robotaxi 在受限地理区表现好（保守可接受），消费车在通行场景表现好（不能动不动急停）。

---

## 4 · 工程视角：成本与可维护性

| 维度 | Waymo | Tesla |
|---|---|---|
| 单车硬件 BOM | $100k+ `UNVERIFIED` | <$5k `UNVERIFIED` |
| 地图更新成本 | 高（专车定期扫描） | 0（无 HD map） |
| 新城市开通 | 数月 | 即时（OTA） |
| 算力（车端） | 自研 SoC + redundant | HW4 ~150 W `UNVERIFIED` |
| 数据回传 | 全量（公司车队） | 影子模式 + clip 触发回传 |
| 模型迭代周期 | 月级（保守） | 周级（FSD v12 演示） |

Tesla 的真实**unfair advantage**是**数据闭环**：百万车队 + 影子模式 + clip 触发 = 长尾事件数月内可覆盖。Waymo 的 unfair advantage 是**模块化栈**：感知 / 规划独立验证可证伪、可拿去过监管。

---

## 5 · 数据与评测

- **Waymo Open Dataset**：1150 scenes，LiDAR + cam，公开评测 motion prediction / 3D detection。
- **Tesla**：**无公开数据集**，长尾 clip 内部用，外界只能通过 disengagement rate / safety report 间接评估。
- **公开 disengagement**：CA DMV 数据（仅 SF），Waymo MPDE >17,000 mi (2023) vs Tesla 不报。

仿真饱和警告：Waymo Open Dataset / nuScenes 上 90%+ AP 不代表真路稳。

---

## 6 · 能力与失败模式

**Waymo 失败**：施工区 / 临时改道（HD map 失效）、雨雪 LiDAR 噪声、地图未覆盖区。
**Tesla 失败**：弱光长距、罕见外形车辆（如改装车）、cam 被泥/虫遮挡。

### Hidden Assumptions

1. **Waymo 假设：HD map 维护成本 < 部署收益**——在 SF/PHX 成立，在县道乡道不成立。
2. **Tesla 假设：数据规模可解决长尾**——若长尾分布是幂律尾巴（如 1/1000 万事件），数据规模也救不了。
3. **两家都假设：感知 → 决策可纯监督学**——但极端长尾 case 没有 ground truth label。
4. **Waymo 假设：LiDAR 物理永远比视觉鲁棒**——大雨 / 飞雪时 LiDAR SNR 急降，视觉反而更好 `UNVERIFIED`。
5. **Tesla 假设：占用网络可替代 LiDAR**——精度 vs 距离 trade-off 在 >100 m 急剧恶化（基线短）。

---

## 7 · 与相关工作对比

| 厂商 | 路线 | 关键差异 |
|---|---|---|
| Waymo | LiDAR + HD map + 模块化 | 最完整 stack；商业化最早 |
| Cruise (停运) | 类 Waymo | 2023 安全事件后退出 |
| Tesla FSD | vision-only + e2e | 数据规模 unfair advantage |
| Wayve (UK) | vision + 世界模型 GAIA-2 | Tesla 路线 + 学术化 |
| Mobileye | vision + REM 众包地图 | Waymo / Tesla 中间路线 |
| 小鹏 / 蔚来 / 华为 | LiDAR + vision 混合 | "保险" 路线，国内监管偏好 |
| Wayve / Cosmos | 神经世界模型 | 第三条道：视频生成 → 训练数据 |

**面试 Tip**：被问"Waymo 还是 Tesla 路线对"——别站队，答"两家在不同 deployment niche 各自自洽：Waymo 在 geofenced L4 robotaxi 已经商业化，Tesla 在 L2+ 全球部署上 ROI 更高；真正的问题是 vision-only 能否在 long-tail 上闭环——这是 2026 年还没有定论的实证问题"。

---

## Boundary

- **BEV / Occupancy 算法细节** → [`embodiments/driving/bev_and_occupancy.md`](./bev_and_occupancy.md)
- **LiDAR / camera 物理对比** → `foundations/sensor-physics/`
- **世界模型路线**（Cosmos / GAIA-2）→ `foundations/world-models/`（待补）
- **跨 embodiment sensor stack 对比** → `crossing/sensor-stack-matrix/`

## For the reader

- **AD engineer**：选传感器栈前先回答"是否有 HD map 维护预算？" 与 "是否有车队回传数据闭环？"——这两个回答决定路线。
- **Manipulation researcher**：AD 的占用网络 / BEV 表征对桌面操作过 over-engineered，但**自动标注 pipeline** 思路可借鉴。
- **Aerial researcher**：drone 没有 HD map、没有车队数据规模——AD 两派路线都不直接搬，drone 需要第三路（VIO + 在线建图）。
- **Marine engineer**：水下没有 LiDAR、没有视觉、没有 HD map——AD 两派都是奢侈品，请去 marine 子树看 sonar 路线。

## References

- Tesla Occupancy Network — Karpathy CVPR 2022 Workshop talk
- Waymo Open Dataset — Sun 等，CVPR 2020，[waymo.com/open](https://waymo.com/open/)
- Wayve GAIA-1/GAIA-2 — 2024，[wayve.ai](https://wayve.ai/)
- Cosmos — NVIDIA，2025
- CA DMV Disengagement Reports（公开）

---
[← Back to Driving README](./README.md)
