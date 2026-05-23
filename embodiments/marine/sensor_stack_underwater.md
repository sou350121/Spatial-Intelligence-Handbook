# 水下 AUV / USV 传感器堆叠 (Underwater Sensor Stack)

> **发布时间**：2026-05-21
> **核心定位**：水下载体的传感器堆叠**不是 aerial 的水下变体**——它是另一套 sensor physics 决定的另一套架构。本文按"GNSS 替代品 + LiDAR 替代品 + 视觉退化曲线"三条线把堆叠讲透。
> **TL;DR**：水下没有 GNSS，**DVL** 顶上；水下没有 LiDAR，**multibeam sonar** 顶上；视觉只在 **<5 m + 清水 + LED 照明**下才有用，其余 99% 时间是装饰。这套堆叠决定了 AUV state estimation 在物理上**根本不能照搬** aerial VIO。

**状态：** v1 —— 有立场的草稿。所有商用 sonar / DVL 规格标 `UNVERIFIED`。

---

**X-Ray 开场：** 把"水下"当成"aerial 但是慢一点"是水下机器人新手最大的坑。水下的真正不同是**电磁波几乎不传播**——GPS、WiFi、可见光（>10 m）、雷达全部失效，但**声波传播极好**（数公里）。这把整个 sensor stack 倒过来：声学传感器从 aerial 的 niche 变成水下的主力。本文回答：水下载体的 GNSS 等价物是 DVL，LiDAR 等价物是 multibeam sonar，视觉退到辅助位——这意味着 spatial researcher 想跨到 marine，必须**重学传感器物理**，不是重学算法。

---

## 📍 研究全景时间线

```
1960s ─ 美海军 Doppler velocity 测速（DVL 前身）
        │ ⚡ 用 4 束斜向声波 Doppler 测对地速度
1980s ─ Multibeam sonar 商用化（海洋测绘）
        │
1990s ─ 早期 AUV（REMUS、Bluefin）DVL + AHRS dead-reckoning
        │
2000s ─ EKF / UKF 紧耦合状态估计成型
        │
2010s ─ ROV 视觉检视（清水近距离）— GoPro 时代
        │ ⚡ 视觉首次进入 marine pipeline，但仅辅助
2015 ─ Hovering ROV (SAAB Seaeye 等) — 双 DVL + 视觉伺服
        │
2020 ─ 学界水下 VIO 论文涌现（UWSim、AQUALOC）
        │ ⚠️ 几乎全在受控水池或清水库验证
2023 ─ 工业水下检视用 photogrammetry（SfM） + DVL 拼接
        │
2026 ─ 本文位置：消费级 AUV (BlueROV2、CHASING M2) 进入海洋
        └─ 局限：视觉 / SLAM 始终是装饰，DVL + 声学定位才是命脉
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统对比概览

| 传感器 | 物理原理 | Aerial 类比 | 典型规格 `UNVERIFIED` | 价格档 |
|---|---|---|---|---|
| **DVL (Doppler Velocity Log)** | 4 束声波 Doppler 测对地速度 | GNSS（dead-reckoning） | 0.2% 行程漂移；400/600/1200 kHz；30-200 m 离底高 | $5k-$50k |
| **Multibeam sonar (MBES)** | 多 beam 测深扇区 | LiDAR | 200-400 kHz；~1° beam；50-200 m 距离 | $20k-$200k |
| **Side-scan sonar** | 拖曳后向散射成像 | side-looking radar | 100-900 kHz；高分辨率 2D 图像 | $10k-$80k |
| **Mechanical scanning sonar** | 单 beam 机械扫描 | 旋转 LiDAR | 50-500 kHz；廉价；慢 | $3k-$15k |
| **IMU / AHRS** | 加表 + 陀螺 + 磁罗盘 | 同 aerial IMU | 消费 MEMS - FOG 工业级 | $50-$50k |
| **压力深度传感器** | 水柱压力测深 | 气压高度计 | <1 cm 分辨率；最可靠 | $100-$1k |
| **USBL / LBL** | 应答器三角测距 | GNSS-RTK 声学版 | 米级精度；需水面船 / 信标 | $20k-$500k |
| **RGB 相机 + LED 照明** | 可见光成像 | aerial cam | <5 m 清水有用，否则废 | $50-$5k |

### 1.2 关键机制：DVL 为何是 marine 的真主角

⚡ **Eureka Moment**：DVL 不只是"水下 GPS 替代"——它是 marine state estimation **唯一**给你**对地速度**而非加速度的传感器（IMU 给加速度，需要积分；DVL 直接给 v）。这把 marine state estimation 从二阶积分（误差立方增长）降到一阶积分（误差线性增长）——这是 AUV 能数小时连续作业的物理基础。

```
                  ┌──────────────────────────┐
   压力 ──────► │                          │
   AHRS ──────► │   EKF / Factor graph     │ ──► 位置 / 速度 / 姿态
   DVL  ──────► │   (tightly coupled)      │     10-50 Hz
   USBL ──────► │                          │
   IMU  ──────► │                          │
                  └──────────────────────────┘
                            ▲
                  ┌──────────────────────────┐
   MBES ──────► │  Bathymetric SLAM        │ ──► 通过地形匹配
   近距相机 ──► │  / loop closure          │     纠正漂移
                  └──────────────────────────┘
```

### 1.3 视觉退化曲线

```
能见度 (m)  │ 视觉作用                  │ 主传感器
─────────  │ ───────                  │ ───────
> 10 m     │ 仅 LED 路灯效果            │ DVL + 声学
5-10 m     │ 大致辅助                  │ DVL + 声学，cam 辅助
1-5 m      │ photogrammetry / 检视有用 │ DVL + cam（清水）
< 1 m      │ 接触级，但能见度本来就低   │ 触觉 / 力反馈
浑水/夜间  │ 全黑                      │ DVL only
```

视觉传感器在水下**95% 时间是装饰**。学术界喜欢做水下 VIO 论文（aerial 算法搬过去），工业界几乎不用——因为真实海况下视觉根本看不见。

---

## 2 · 数学核心：DVL + IMU 紧耦合

📌 **Napkin Formula**：`error_position(t) ≈ 0.002 · ∫|v| dt`——DVL 的 0.2% 行程漂移把位置误差锁在**线性增长**而非 IMU 的立方增长。

详细：
- 纯 IMU dead-reckoning：`error_pos ~ ½ a_bias · t²`，1 mg bias → 1 hour 误差 ~64 m
- DVL + IMU：`error_pos ~ 0.002 × distance_traveled`，1 km 行程 → 误差 2 m
- 加 USBL fix（每 N 秒一次）：误差被截断到 USBL 精度（米级）

DVL 失效模式（必须建模）：
- 离底太高（>200 m，400 kHz DVL）→ beam 不返回 → 退回 IMU only
- 软泥 / 海草底质 → Doppler 信号弱 → variance 上升
- DVL beam 与水流方向耦合（水中 mode 而非 bottom-lock mode）→ 测的是相对水速不是对地速度

---

## 3 · 带数字走一遍：BlueROV2 + DVL-A50 玩具例子

设 BlueROV2 装 Water Linked DVL-A50（消费级 DVL，~$8k `UNVERIFIED`），出航 30 min，平均速度 0.5 m/s，无 USBL。

- 总行程：30 × 60 × 0.5 = 900 m
- DVL 漂移：0.002 × 900 = 1.8 m
- IMU 单独 30 min 漂移（无 DVL）：>500 m（不能用）
- 压力深度误差：<10 cm（独立）

结论：纯 DVL + AHRS 已经支持 30 min 任务到 ~2 m 精度——足够检视 / 测绘任务。若需要 <0.5 m 绝对精度，加 USBL。

这就是为什么 marine 没有人讨论"水下 VIO 是否替代 DVL"——DVL 是 marine 的 GNSS，**视觉再好也是辅助**。

---

## 4 · 工程视角：声学的真实代价

| 维度 | DVL | MBES | USBL |
|---|---|---|---|
| 功耗 | 5-30 W | 30-100 W | 5-20 W |
| 重量 (水中) | 0.5-5 kg | 5-30 kg | 1-3 kg |
| 更新率 | 1-10 Hz | 0.5-5 Hz | 0.5-2 Hz |
| 数据带宽 | <1 kbps | 10-100 Mbps（实时拼接） | <1 kbps |
| 干扰 | 多 DVL 互扰（同频） | 自激 OK | 信标布设成本 |

工程痛点：
- **多声学传感器互扰**——同船 DVL + MBES + USBL 同频段时，需要时分 / 频分调度，否则互相干扰。
- **声速剖面**——水温 / 盐度变化使声速漂移 1450-1550 m/s，USBL / MBES 精度直接受影响。深海作业要随船测 CTD（温盐深）。
- **磁罗盘失准**——水下 AUV 靠磁罗盘提供 heading，但水下铁磁结构（沉船 / 管道）会扰动。Heading 是 marine 最常见的 silent failure。

---

## 5 · 数据与评测

- **公开数据集稀缺**：AQUALOC（CNRS）是少数公开水下 SLAM 数据集。
- **工业标准**：IHO S-44 测绘标准定义不同等级的 bathymetric 精度要求。
- **仿真**：UWSim、Stonefish、HoloOcean——但水下流体 / 声学仿真**远不如** aerial 仿真成熟。

仿真饱和警告：水池清水中的 VIO 100% 成功率**不可外推**到真海况，gap 巨大。

---

## 6 · 能力与失败模式

**能做**：水下检视（管道 / 船壳）、测绘（多波束）、矿产勘探（侧扫）、近距视觉检视（清水）。
**做不了**：浑水视觉、长程纯惯导（>1 hour 无 fix）、实时 sub-cm 定位。

### Hidden Assumptions

1. **DVL bottom-lock 假设**——离底 < 量程；浮潜在 1000 m 海面以上时 DVL 测的是水流（无用）。
2. **声速恒定**——深海 CTD 不测时假设 1500 m/s 会引入百分之几误差。
3. **磁罗盘有效**——靠近铁磁结构时静默失准。
4. **视觉退化已知**——能见度不是稳态量，cm 级浑度变化把可视距离从 5 m 砍到 0.5 m。
5. **声学频段无冲突**——多载体 / 船舶同区作业时严重互扰。

---

## 7 · 与相关工作 / 跨 embodiment 对比

| Embodiment | "GNSS 替代" | "LiDAR 替代" | 主感官 |
|---|---|---|---|
| Aerial drone | GNSS-RTK / VIO | 真 LiDAR | 视觉 + IMU |
| 自动驾驶 | GNSS-RTK + HD map | LiDAR / 占用 | 视觉 + LiDAR |
| AGV 室内 | UWB / Lighthouse | 2D LiDAR | LiDAR + 轮式里程 |
| AUV / USV | **DVL** | **MBES sonar** | **声学**（视觉装饰） |
| Humanoid | （室内无 GNSS） | 头装 LiDAR | 视觉 + IMU |

**面试 Tip**：被问"水下能用 VIO 吗"——答"学术上有论文，工业上没人用；因为 DVL 提供对地速度（不是加速度），把误差从二阶降到一阶，视觉根本竞争不过；视觉只在 <5 m 清水近距检视场景有补充价值"。

---

## Boundary

- **Sensor 物理原理细节**（声波传播、Doppler 数学）→ `foundations/sensor-physics/`（待补 sonar / DVL 章节）
- **跨 embodiment sensor stack 矩阵** → `crossing/sensor-stack-matrix/`
- **水下视觉退化与 photogrammetry** → 本目录未来文档（清水 SfM 场景）
- **声学定位 USBL / LBL 理论** → `foundations/sensor-physics/`（待补）

## For the reader

- **Marine engineer**：DVL 选型先于一切；预算次序是 DVL > IMU > 压力 > USBL > 视觉。
- **Aerial engineer**：marine 路线提醒你"GNSS-denied"问题远比 drone 极端；DVL 在 aerial 没等价物。
- **AD engineer**：marine 与 AD 共享"先验地图（bathymetry）+ 局部感知"范式，但 marine 的地图更新周期是**年**而非**天**。
- **Manipulation researcher**：水下机器手存在（如 ROV manipulator），但因可见度极差，几乎完全依赖力 / 触觉反馈而非视觉。

## References

- DVL 原理 — Brokloff 1994 IEEE Oceans
- AQUALOC — Ferrera 等 IJRR 2019
- HoloOcean — BYU 2022
- BlueROV2 + Water Linked DVL-A50 — 厂商数据手册 `UNVERIFIED, no DOI`
- IHO S-44 测绘标准

---
[← Back to Marine README](./overview.md)
