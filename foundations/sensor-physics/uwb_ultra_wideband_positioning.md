# UWB 超宽带定位物理 (Ultra-Wideband Positioning Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — 500 MHz – 几 GHz UWB 脉冲 / ToF / TWR / TDoA
> **核心定位**：UWB 不是"短距 WiFi" — 它是**短脉冲 ranging 物理**带来的 cm 级室内定位，靠 sub-ns 边沿时间换 WiFi 拿不到的 NLOS 抗多径

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 chip datasheet 核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) UWB（IEEE 802.15.4z / 4a）发射 **500 MHz – 几 GHz 带宽**的纳秒级脉冲，每个 pulse 的 leading edge 上升时间 &lt;1 ns；接收端测脉冲首到时间（first-path detection）就能在金属反射 / 多径环境里**钉死直达路径** — 这是 WiFi (20-160 MHz 窄带) 物理上做不到的。(b) Apple AirTag (U1 chip)、Decawave DW1000、Qorvo DWM3000 把这个能力做成 ~$10 IC，室内定位精度 ~10 cm，4 anchor + 1 tag 标准拓扑。(c) 对机器人 / drone 工程师：UWB 是 **GNSS-denied 室内**的唯一 cm 级 sensor — LiDAR SLAM 重、视觉退化、WiFi 太粗 — UWB 是"室内 GPS"的现实形态。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1960s ── 军用脉冲雷达（UWB 原理首次出现，spread spectrum）
2002 ── FCC 批准 UWB 民用频段 (3.1–10.6 GHz)
2007 ── IEEE 802.15.4a — 首个 UWB ranging 标准
2013 ── Decawave DW1000 量产 — $5 IC + ~10 cm 精度
2019 ── Apple U1 chip (iPhone 11) — UWB 进入消费电子
2020 ── Apple AirTag — UWB ranging 民用爆款
2021 ── Samsung / Xiaomi / Google 跟进 UWB
2024 ── 802.15.4z (HRP/LRP) — 安全 ranging 防中间人攻击
        ── 你在这里 (2026) ──
?    ── Phone-to-car digital key / 自动驾驶 V2X tag / AR headset 6DoF anchor
```

UWB 的"室内 GPS"野望在 2019 年 Apple 入场后转入消费量产；2024-26 是机器人开始**复用消费链 IC**降本的关键 2 年。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
ToF ranging:    d = c × Δt                  (c = 3×10⁸ m/s)
带宽 → 时间分辨率: σ_t ≈ 1/(2·BW)
σ_d ≈ c / (2·BW)                            ≈ 30 cm / GHz  → 500 MHz BW 给 ~30 cm 雷诺极限

Two-Way Ranging (TWR):
T_round = T_reply + 2·T_prop
d = c × (T_round - T_reply) / 2             无需 anchor-tag 时钟同步
```

第一组式子告诉你为什么 UWB 是 cm 级（带宽够宽，时间分辨率到 ns）；第二组告诉你为什么消费级 UWB 不需要 RTK 级时钟基础设施（双向交换抵消 clock offset）。

### 1.1 系统组件

| 组件 | 输入 | 输出 | 关键约束 |
|---|---|---|---|
| **UWB transceiver** | bit stream | 纳秒脉冲 RF | 3.1–10.6 GHz（FCC）/ 6–8.5 GHz（消费）|
| **first-path estimator** | RX 多径波形 | 首到路径 timestamp | NLOS 关键 |
| **ranging engine** | T_TX / T_RX timestamps | distance | TWR / SS-TWR / DS-TWR 协议变体 |
| **multilateration** | ≥3 anchor 距离 | (x, y, z) 位置 | 几何 dilution（GDOP）|

### 1.2 关键机制

UWB 发射 **2 ns 短脉冲**（500 MHz BW 等价）；接收端用 leaky-integration + threshold detection 找 **first-path arrival**（FPA），即使后续多径强 10× 也不会被 fool — 因为 FPA 在时间上**早于**反射路径。这是 UWB 抗多径的物理根因。

⚡ **Eureka Moment.** UWB 不是"另一个无线频段"，而是**用带宽换时间分辨率**的 sensor — Heisenberg-Gabor 限：σ_t × BW ≥ 1/2。WiFi 20 MHz BW → σ_t ~25 ns → σ_d ~7.5 m；UWB 500 MHz BW → σ_t ~1 ns → σ_d ~30 cm。**精度差 25× 是带宽差 25× 的直接结果**，不是协议优劣。

### 1.3 信息流

```
Tag           Anchor 1     Anchor 2     Anchor 3     Anchor 4
 │ poll →      │            │            │            │
 │      ← resp │            │            │            │     ← d₁ via DS-TWR
 │ poll →      │            │            │            │
 │             │     ← resp │            │            │     ← d₂
 │      ...    │            │            │            │
 │             │            │            │            │
 ▼                                                       trilateration
 (x, y, z) tag pose
```

4 anchor 是"3D fix + redundancy"的最小配置；3 anchor 给 2D fix（地面机器人 OK）；2 anchor 只能给"圆周交集"模糊解。

---

## 2 · 数学核心：TWR / TDoA 协议对比 (Math Core)

📌 **Napkin Formula** (X-Ray)：TWR 让 tag 主动握手（双向），TDoA 让 tag 只发不收（单向，anchor 协同测时差）— 前者 tag 耗电高但 anchor 不需同步，后者 anchor 必须时钟同步但 tag 可以低功耗信标。

### 2.1 SS-TWR (Single-Sided TWR)

```
T_round (at A) = T_reply (at B) + 2·T_prop
d = c × (T_round - T_reply) / 2
```

变量：
- `T_round` — A 测量的从发 poll 到收 ack 的时间
- `T_reply` — B 测量并在 ack payload 里告诉 A 的处理延迟
- `T_prop` — 单程传播时间

误差源：`σ_d ≈ c × σ_clock × T_reply / 2`。`T_reply ~200 µs`，clock 误差 20 ppm → `σ_d ≈ 0.6 m`。SS-TWR 的 ppm 时钟误差直接放大成距离误差。

### 2.2 DS-TWR (Double-Sided TWR)

二次握手 cancel 掉一阶 clock drift：

```
T_prop = [T_round1 × T_round2 - T_reply1 × T_reply2] / [T_round1 + T_round2 + T_reply1 + T_reply2]
```

DS-TWR 把 clock 误差从一阶降到二阶 — 同样 20 ppm clock，DS-TWR `σ_d` 降到 ~3 cm `UNVERIFIED`。**消费 UWB 几乎全部用 DS-TWR。**

### 2.3 TDoA (Time-Difference of Arrival)

Tag 单次发信标，多 anchor 测**到达时间差**：

```
Δd_ij = c × (t_i - t_j)
```

每个 Δd 是一条双曲线，3 个 Δd → trilateration。优势：tag 仅 TX 无 RX，电池 10× 寿命（AirTag 1 年）；劣势：anchor 必须**纳秒级时钟同步**（有线 / PTP / 光纤）— 基础设施投资。

---

## 3 · Worked example — 10×10 m² 仓库，4 anchor，DS-TWR

设置：anchor 在 (0,0), (10,0), (10,10), (0,10)，高度 3 m；tag 在地面 (5, 5, 0)。

```
真距 = √(5² + 5² + 3²) = 7.68 m to each anchor
T_prop = 7.68 / 3e8 = 25.6 ns
```

DS-TWR with DW1000 (`UNVERIFIED` from Qorvo datasheet)：
- `σ_t ~ 200 ps` per measurement
- `σ_d_single = c × 200 ps = 6 cm`
- 4 anchor trilateration + GDOP ~1.5 → `σ_xyz ≈ 9 cm`

100 Hz 采样 + EKF 融合 IMU → 长时间收敛到 ~3–5 cm。匹配 Apple AirTag / DJI Phantom RTK 室内文档 spec。

如果 anchor 数减到 3：丢 z 维 → 室内 2D 仍 ~10 cm；如果 anchor 数到 5+ 用 outlier rejection 抗 NLOS bias，进一步降到 5 cm。

---

## 4 · 工程视角 (Engineering View)

**功耗.** DW3000 RX 模式 ~150 mW peak / TX ~250 mW peak `UNVERIFIED`。SS-TWR 每秒 10 Hz ranging ~50 mW 平均 — drone 不痛，但 AirTag 改用 TDoA 单向广播才能 1 年 CR2032。

**延迟.** DS-TWR 4 anchor 串行 ~5–10 ms per cycle（4 次握手）→ 100 Hz 极限；并行多址 → 200 Hz+。EKF 配合 IMU 给最终 200–500 Hz pose。

**Cost.** Qorvo DW3000 ~$3–5 / Decawave DW1000 ~$5–8 `UNVERIFIED`；anchor 套件 ~$30–50；完整 4-anchor 仓库系统 BOM &lt;$200。比 Vicon 便宜 1000×，比 LiDAR SLAM 便宜 50×。

**Range.** 室内 LOS ~50 m / NLOS（穿一面墙）~10–20 m / NLOS（多面墙）&lt;10 m。AirTag 标称 9 m。

---

## 5 · 数据与评测 (Data & Eval)

- **室内定位 benchmark**：no single dominant — 各机构自行测，没有像 KITTI 那样的统一基准
- **典型报告精度**：LOS ~5 cm / NLOS bias 30–100 cm（pre-correction）/ ML correction 后 ~10–20 cm
- **EVAAL / Microsoft Indoor Localization Competition** — 2014–2018 年的学界 benchmark，UWB 队伍稳定胜出

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 室内 cm 级 6DoF（配 IMU）；NLOS 穿 1-2 面墙；不需要光照；不被电磁干扰显著影响；100+ tag 同时跟踪。

**不能做什么.** 户外 GPS 信号好时无优势；穿金属彻底不行（电梯井 / 集装箱）；anchor 部署成本（每个房间 ≥3 个）；DOA 单 anchor 给不出方向（除非用 AoA 多天线，U1 / DWM3000 在做）。

### Hidden Assumptions (隐含假设)

- **anchor 已知位置.** Survey 误差是系统 bias —— 1 cm anchor 测量误差直接传到 tag 位置
- **多径不极端.** 大金属反射体（汽车厂 / 钢架仓库）破坏 first-path estimator
- **clock 稳定.** DW3000 内置 30 ppm TCXO；温度漂超 0–50°C 包络会损失精度
- **频段空闲.** 6–8.5 GHz 在欧盟需要遵守 DAA（Detect-and-Avoid），与 5G C-band 有相邻共存问题
- **tag 在水平面.** 4 anchor 在同一平面时 z 方向 GDOP 爆炸 — 需要 3D 立体部署

**失败模式：**
- **金属反射 boom.** 金属架构里 first-path detector 把强反射误认为直达 — 加 ML correction 或多 anchor 投票
- **NLOS bias.** 穿墙额外延迟 1-3 ns → 30-100 cm 系统性偏远；可用 received signal strength / waveform 特征做 NLOS classifier
- **anchor 互扰.** 同 channel 多 anchor TX 重叠 → TDMA 调度
- **CR2032 battery cliff.** TWR tag 1-3 月寿命 vs TDoA 1 年 — 协议选择决定

---

## 7 · 与相关工作对比 (Comparison)

| Sensor | 精度 | 范围 | 室内 / 户外 | Cost | NLOS |
|---|---|---|---|---|---|
| **UWB** | 5-30 cm | 10-50 m | 室内 ★ | $$ | 部分 |
| **WiFi RTT** | 1-3 m | 30-100 m | 室内 | $ | 弱 |
| **5G NR positioning** | 0.5-3 m | 100 m+ | 户外+室内 | $$$ | 一般 |
| **BLE RSSI** | 1-5 m | 10 m | 室内 | $ | 弱 |
| **mmWave radar (76 GHz)** | 10-30 cm | 200 m | 户外 ★ | $$$ | OK |
| **Vicon / OptiTrack** | &lt;1 mm | room | 室内 | $$$$$ | 不能 |

UWB 的甜区是 **室内 cm 级 + 中价位** — 上挤 Vicon（精度更高但 1000× 价格），下挤 WiFi RTT（便宜但精度差 30×）。

**🎙️ Interview Tip.** 被问"为什么 UWB 比 WiFi 准这么多"？— **带宽差 25×，物理上精度差 25×**（Heisenberg-Gabor 限）。不是协议优劣，是 FCC 给 UWB 留的 500 MHz 频段让脉冲足够短。

---

## 8 · For the reader

- **Manipulation** — 一般用不上 UWB；workspace &lt;1 m 用视觉 / FT 更直接
- **Mobile robot / AGV (仓库)** — UWB anchor 部署 + tag 替代 LiDAR SLAM 是主流方案，省 maintenance（地图不需要持续更新）
- **Drone (GNSS-denied 室内)** — UWB anchor + tag = 室内 RTK；DJI / Skydio 行业版本已在用
- **Marine** — UWB 在水下完全失效（电磁衰减），改用声学 USBL（→ `underwater_sonar_physics.md`）

---

## References

- IEEE 802.15.4z-2020 — UWB HRP/LRP standard
- Qorvo DW3000 Family Datasheet `UNVERIFIED, datasheet URL TODO`
- Apple U1 Chip / Nearby Interaction framework (developer.apple.com)
- Decawave DW1000 User Manual v2.18 `UNVERIFIED`
- IPIN 2020-2024 indoor positioning conference proceedings

## Boundary

- 单 sensor 物理 / 协议 / 失效模式 → 本文
- `crossing/sensor-stack-matrix/` — UWB 在 6 embodiment BOM 取舍
- `embodiments/aerial/sensor-stack/` — drone 室内 UWB anchor 工程部署
- `deployment/hardware-selection/` — Qorvo vs Apple U1 vs NXP Trimension 选型
- 室内 RTK 算法 / EKF 融合 → `foundations/state-estimation/`（如有）

*2026-05-21. v1. UNVERIFIED → v1.1 待 datasheet 核对。*

---
[← Back to sensor-physics README](./overview.md)
