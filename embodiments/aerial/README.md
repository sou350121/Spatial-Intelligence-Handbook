# 空中 / Aerial — 维护者深度锚点

**Status:** v1 — 主观立场的导航页。子目录级断言以各子目录 `README.md` 为准。
**Depth tier:** 🌬️ **同辈领先（1.5–2× 深度）** — 这是本仓库刻意压深的实体轴；其他实体写到对比可读即可，空中要写到工程可决策。
**TL;DR:** 空中实体之所以是本仓的深度锚点，不是因为论文最多——是因为它**同时把所有空间智能的硬约束顶到极限**：状态率 200 Hz、端到端延迟 &lt;10 ms、metric scale 无 GNSS fallback、IMU 受桨叶噪声污染、SWaP-C 把传感栈按起飞重量切成离散档。任何在空中能跑的栈，迁回 manipulation / ground 都富余；反过来不成立。**这就是为什么本仓库把空中写得比其他实体深 1.5–2×——其他实体的工程读者读了空中章就知道自己的约束有多松。**

---

## 1 · 为什么把空中作为锚点

四个理由——前三个是技术，最后一个是定位：

1. **约束最紧。** 见 [`vio/`](./vio/) 头部的四条非协商约束——状态率、延迟、metric scale、IMU 抗桨噪。没有其他实体同时面对这四条。
2. **传感栈差异化最大。** 250 g 竞速机和 1.5 kg 巡检机之间的栈差距，比 manipulation 桌面机器和工业臂的栈差距还大——见 [`sensor-stack/`](./sensor-stack/) 的 payload class 矩阵。
3. **失败成本最高。** 桌面 SfM 出错重启；空中 VIO 出错炸机。这一条让"benchmark 漂亮"和"出货能飞"之间的距离比任何其他实体都大。
4. **维护者锚定方向。** 标 🌬️ = 维护者押注 + 长期跟踪的方向（与姊妹仓 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 中的 🎯 同义）。把这条写深，是这本 handbook 区分于综述类内容的核心 USP。

---

## 2 · 空中空间智能的 8 个轴

本目录按这 8 个轴组织。每个轴对应一个子目录（部分尚未撰写）：

| # | 轴 | 目录 | v1 status | 关键问题 |
|---|---|---|---|---|
| 1 | **VIO 状态估计** | [`vio/`](./vio/) | 🌬️ depth | 200 Hz / 10 ms / metric / IMU 抗噪——四条非协商约束 |
| 2 | **避障** | [`obstacle-avoidance/`](./obstacle-avoidance/) | 🌬️ depth | RL 反应式 vs 经典规划——两条不收敛路线 |
| 3 | **主动跟踪** | [`active-tracking/`](./active-tracking/) | 🌬️ depth | Skydio vs DJI 反向工程；遮挡恢复 + 拥挤场景目标消歧 |
| 4 | **板载建图** | [`on-board-mapping/`](./on-board-mapping/) | 🌬️ depth | 3DGS vs LiDAR SLAM；GNSS-denied 长距 |
| 5 | **传感栈** | [`sensor-stack/`](./sensor-stack/) | 🌬️ depth | Payload class 决定一切的纵剖 |
| 6 | **事件相机** | [`event-camera/`](./event-camera/) | 🌬️ depth | UZH RPG 谱系；高速 / 低光 / HDR 包络 |
| 7 | **集群 / Swarm** | [`swarm/`](./swarm/) | **future (v1 不写)** | 通信 + 分布式 SLAM + 协同任务——2026 尚不属于本仓 USP |
| 8 | **Long-range SLAM** | (并入 [`on-board-mapping/`](./on-board-mapping/)) | merged | 与板载建图的 compute / GNSS 约束不可分割 |

**v1 取舍：**

- **First-tier（v1 已写或在写）**：VIO、避障、主动跟踪、板载建图、传感栈、事件相机——这 6 个是任何一架严肃自主无人机都要回答的工程问题。
- **Deferred**：集群——通信协议、博弈、群智涌现等问题超出"空间智能"边界，且 2026 没有出货级的群智无人机供本仓做工程化拆解；推到 v2 或并入 `crossing/`。
- **Merged**：Long-range SLAM 的核心约束（compute、GNSS-denied、map decimation）与板载建图重叠 80%+，拆成独立目录会产生薄文档；合并到 [`on-board-mapping/`](./on-board-mapping/) 一次写透。

---

## 3 · 跨实体对照

空中的硬约束相对其他实体的**松紧关系**——读懂这个矩阵，再去看其他实体的章节会快很多：

| 维度 | Manipulation | Ground-mobile | Aerial | Marine |
|---|---|---|---|---|
| 状态率要求 | 30 Hz | 30 Hz | **200 Hz** | 5 Hz |
| 延迟预算 | 100 ms | 50 ms | **5–10 ms** | 200 ms |
| Metric scale 必需？ | 可选 | 是 (GNSS fallback) | **是 (无 fallback)** | 是 (DVL 提供) |
| IMU 耦合强度 | 弱 | 弱–中 | **强** | 强 |
| 失败成本 | 重启 | 停机 | **炸机** | 失联 / 沉舰 |
| SWaP-C 离散性 | 连续 | 较连续 | **强离散 (payload class)** | 离散 (耐压舱) |

**横着读：** 空中是 5 个维度里最严的实体（manipulation 最松，marine 在某些维度上反而更严）。
**竖着读：** 跨实体把方法搬过来时，松→紧方向要做大量补丁，紧→松方向几乎免费——这就是 `crossing/` 章节的工作原料。

详见 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 的完整 gap matrix。

---

## 4 · 怎么读这本"空中"章

按角色推荐路径：

- **机械臂 / 桌面研究者** — 从 [`vio/`](./vio/) 开始，再到 [`sensor-stack/`](./sensor-stack/)。重点是 "metric scale + 10 ms 延迟" 那一段——它会告诉你为什么 manipulation 谱系的 VGGT 不能简单搬过来。
- **AD 工程师** — 跳过 [`vio/`](./vio/)（你的 BEV 谱系比这里成熟），直接看 [`obstacle-avoidance/`](./obstacle-avoidance/)。两条工程路线的对照在 AD 里也有镜像（端到端 vs HD 地图）。
- **空中工程师** — 按你的客户路径读：消费 → 看 [`active-tracking/`](./active-tracking/)；巡检 / 测绘 → 看 [`on-board-mapping/`](./on-board-mapping/)；竞速 → 看 [`event-camera/`](./event-camera/) 和 [`obstacle-avoidance/`](./obstacle-avoidance/) §2 School A。
- **跨实体研究者 / 综述写作者** — 直接去 [`crossing/`](../../crossing/) 章；本目录是各 lane 的工程支撑。

---

## 5 · 教学基础 (Tutorial layer · HKUST ELEC5660 取材)

aerial zone 既有 dissection 偏「现代开源库拆解」，**缺基础教材层**。以下 3 篇取材自 HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲, BSD 3-Clause), 补齐基础到端到端 stack 的完整教学路径：

| 文件 | 类型 | 涵盖 |
|---|---|---|
| [`dynamics_and_control_primer.md`](./dynamics_and_control_primer.md) **★ NEW** | primer | quadrotor 6-DoF EOM + ZXY Euler + quaternion-EOM normalization 技巧 + cascade PID + 各 frame 配置（hexa/octo/tilt-rotor）|
| [`planning/min_snap_dissection.md`](./planning/min_snap_dissection.md) **★ NEW** | dissection (14 项) | differential flatness + 8 阶 polynomial + KKT closed-form QP + time allocation 策略 + min-snap vs MINCO/MPC/iLQR 对比 |
| [`vio/ekf_from_scratch_dissection.md`](./vio/ekf_from_scratch_dissection.md) **★ NEW** | dissection (14 项) | 15-state EKF + 21-state augmented EKF 从零手写（与 OpenVINS / VINS-Fusion dissection 互补：他们拆库，本文教写）|
| [`real_flight_production_gotchas.md`](./real_flight_production_gotchas.md) **★ NEW (16.6 KB)** | roadmap / runbook | 真机第一次飞起来踩什么坑：组装 / PX4 ESC / OptiTrack 三层 frame 转换 / IMU 抗桨噪 / time-sync / failsafe / sim2real gap — 取材 HKUST lab1/2/3 PDF + uav_ws/px4ctrl |

**推荐阅读路径**：dynamics primer → min-snap dissection → vio/ekf from-scratch → vio/ 三栈 dissection（VINS-Fusion / OpenVINS / DROID-SLAM）→ 应用栈（active-tracking / obstacle-avoidance / on-board-mapping）。

---

## 6 · 与 `crossing/` 的边界

铁律：**任何会被独立 embodiment 综述写出的内容，归本目录；只要话题在 ≥2 个实体上有可比答案，归 `crossing/`。**

具体来说，本目录写：

- 空中独占的传感栈选型逻辑（payload class × sensor stack）
- 空中独占的状态估计约束（200 Hz / 10 ms / metric / IMU 桨噪）
- 空中独占的失败模式（细线漏检、桨噪 IMU 饱和、map 陈旧 @ 高速）

本目录**不**写：

- "VGGT 在空中 vs manipulation 怎么不同"——归 [`crossing/slam-vio-migration/`](../../crossing/slam-vio-migration/)
- "stereo + IMU 在空中 vs ground 各自怎么选"——归 [`crossing/sensor-stack-matrix/`](../../crossing/sensor-stack-matrix/)
- "失败模式跨实体如何迁移"——归 [`crossing/failures-cross-embodiment/`](../../crossing/) (若已开)

---

## 6 · 维护承诺

- 每个 first-tier 子目录至少 1 篇 dissection 级文档（v1 已落地）
- 重大事件（DJI / Skydio / Autel 出货关键 SKU，UZH / RPG 新论文）追加到 [`reports/`](../../reports/) 而不是本目录
- 任何被引用的厂商数字必须有 `UNVERIFIED` 标记或数据手册一手来源（见 AGENTS.md sensor-physics 规则）
- ✍️ 维护者亲笔内容（Autel 经验等）Moltbot 不触碰

---

## References

- 跨实体延迟与 feed-forward 3D 对照：[`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)
- 跨实体 sensor 矩阵：[`crossing/sensor-stack-matrix/`](../../crossing/sensor-stack-matrix/)
- 主动 NIR / 眼安全：[`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`](../../foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md)
- 顶层实体地图：[`embodiments/README.md`](../overview.md)

## Boundary

本文是空中实体的**入口与导航页**——不写方法、不写论文、不写数字。具体方法学剖析进各子目录的 `README.md` 与 `*_dissection.md`。跨实体对比一律去 [`crossing/`](../../crossing/)。Sensor 物理 / 数据手册级细节去 [`foundations/sensor-physics/`](../../foundations/sensor-physics/)。维护者亲笔（Autel 经验等）标 ✍️，Moltbot 不触碰。
