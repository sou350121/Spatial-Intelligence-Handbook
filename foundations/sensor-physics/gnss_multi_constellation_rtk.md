# GNSS Multi-Constellation & RTK (GNSS 多星座与 RTK — trilateration / 多频 / cm 级定位)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — GPS/GLONASS/Galileo/BeiDou 多频 / RTK / PPP / spoofing
> **核心定位**：drone / AD / robotics 户外定位的"地基" — 但 vertical 精度 ~3× horizontal、城市峡谷 dropout、cm-级 RTK 需要 base station 协议这些工程账学界综述很少写

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字需 datasheet / vendor primer 交叉核对。
**Wedge tier:** sensor-physics expansion（E 桶 drone stack 第 3 篇）

### X-Ray opening

GNSS 是户外定位的物理基础——卫星发射的精确时间戳，receiver 测量 4+ 颗到达时间差，trilateration 求位置。但教科书的"4 颗卫星 trilateration"距离实际 cm 级 RTK 之间有 5 个工程层：多频抗电离层、载波相位 vs 伪距、RTK base station 协议、城市峡谷多径、spoofing/jamming 威胁。**消费 GPS σ ~3 m horizontal / 5 m vertical；RTK σ ~1 cm**——3 个数量级差距，几乎全是工程而非物理。学界 SLAM 综述把它当"位置 oracle"，但 drone 工程师 50% 时间在调它。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1973 ── US DoD 启动 NAVSTAR GPS 项目
1995 ── GPS Full Operational Capability ── 24 颗卫星，民用 SA dithering
2000 ── SA 关闭 ── 民用精度从 100 m 跳到 ~10 m
2010s ── GLONASS / Galileo / BeiDou 部署 ── 多星座时代
2014 ── u-blox NEO-M8N ── 第一代消费级多星座
2016 ── GPS L5 + Galileo E5 ── 多频可用（民用）
2019 ── u-blox F9P ── 消费级 RTK，cm 精度 ~$300
2020 ── Skydio 2 / DJI M300 RTK ── drone RTK 大众化
2022 ── BeiDou 全球覆盖完成 ── 4 大星座并行
202? ── ?  下一波：LEO PNT (Iridium / Starlink) 抗 jamming 备份
```

---

## 1 · Trilateration 物理基础

📌 **Napkin Formula**：`(x-xᵢ)² + (y-yᵢ)² + (z-zᵢ)² = (c·(t_rx - t_tx_i - δt))²`，4 颗卫星给 4 个方程，4 个未知数 (x, y, z, δt)。δt 是 receiver clock bias — 这就是为什么需要**4 颗**不是 3 颗（消去 δt）。

**(a) 时钟物理.** 卫星携带 Cs / Rb 原子钟，~10⁻¹³ 稳定度 → 1 ns 误差 = 30 cm 距离误差。Receiver 是廉价 TCXO（~ppm），位置解过程顺便估出 receiver clock bias。

**(b) 信号物理.** GPS L1 = 1575.42 MHz，L2 = 1227.6 MHz，L5 = 1176.45 MHz。每颗卫星发 BPSK 调制的 PRN (Pseudorandom Noise) 码 + navigation message。Receiver 用本地复制 PRN 做 correlation → 找到 ToF (time-of-flight)。

**(c) 测距类型**：
- **Pseudorange** — code correlation，1 chip = 300 m，noise σ ~3 m
- **Carrier phase** — 载波相位，λ_L1 = 19 cm，相位 noise &lt;1 cm，但有 integer ambiguity (`N`)
- RTK = carrier phase + ambiguity resolution

⚡ **Eureka Moment.** GPS 不是测**位置**，是测**到 4 颗卫星的距离**。位置是约束推断 — 卫星几何（DOP）决定误差放大率。同样测距 noise，PDOP=2 时位置 σ=6 m，PDOP=6 时位置 σ=18 m。城市峡谷只有头顶 4 颗 → PDOP=10+ → 几乎无定位能力。

---

## 2 · 4 大全球星座对比

| Constellation | 国家 | 卫星数 `UNVERIFIED` | 主要频率 | 民用精度 |
|---|---|---|---|---|
| **GPS** (US) | 美 | 31 | L1 1575.42 / L2 1227.6 / L5 1176.45 MHz | ~3 m (single freq) |
| **GLONASS** (RU) | 俄 | 24 | L1OF 1602+k×0.5625 MHz (FDMA) | ~4 m |
| **Galileo** (EU) | 欧 | 28 | E1 1575.42 / E5a 1176.45 / E5b 1207.14 MHz | ~3 m |
| **BeiDou-3** (CN) | 中 | 30+ | B1I 1561.098 / B1C 1575.42 / B2a 1176.45 MHz | ~3 m |

**多星座好处**：可见卫星 1 个星座 ~8 颗 → 4 星座 ~32 颗 → 几何强度高 + 抗 dropout。**消费 RTK chip 普遍 multi-constellation**：u-blox F9P 支持四星座 + 多频。

**频率选择**：L1/E1/B1 在 1575 MHz **共享频段** — 同一台 receiver 同一根天线接收。L5/E5a/B2a 在 1176 MHz **共享频段**。多频接收便宜得多。

---

## 3 · 多频 (L1+L2+L5) — 抗电离层延迟

电离层是色散介质 → 不同频率信号穿过电离层时延不同 (`delay ∝ 1/f²`)。单频 receiver 用经验模型 (Klobuchar) 估计，剩余误差 5–15 m at zenith，到 50 m at low elevation `UNVERIFIED`。

**双频测距**：`PR_iono_free = (f1²·PR1 - f2²·PR2) / (f1² - f2²)` → 完全消去电离层一阶项。但 noise 放大 ~3× → 实战需 carrier smoothing。

**多径**：信号反射后到达 → 测距引入偏差。L1 比 L2 / L5 受多径影响更小（chip rate）→ 实战 receiver 用 multi-frequency cross-check 减权多径。

⚡ **多频是消费级 RTK 的关键**：单频 RTK 收敛需 30 min，双频 (L1+L2) 收敛 &lt;1 min，三频 (L1+L2+L5) &lt;30 s。u-blox F9P 选三频是 cm-级实时定位的关键。

---

## 4 · RTK (Real-Time Kinematic) — cm-level positioning

**原理**：在已知位置安装 base station，base 与 rover 同时观测同样卫星的 carrier phase → **双差 (double difference)** 消去卫星钟差 / receiver 钟差 / 大气延迟 → 留下基线向量 (rover - base position)。

```
∇Δφ = ∇Δρ + λ · ∇ΔN + 残余误差
       ↑ 几何      ↑ 整数模糊度
```

**ambiguity resolution** — 把 `N` 从 float 解（连续浮点）固定到 integer 是 RTK 的核心难度。LAMBDA 算法 (Teunissen) 是标准方法。

**Real-time 链路**：base station 通过 RTCM3 protocol 把观测值发给 rover (NTRIP over 4G / radio / Wi-Fi)。延迟 &lt;2 s 才有意义。

**精度**：固定后 H σ ~1 cm + 1 ppm × baseline，V σ ~2 cm + 1 ppm × baseline。50 km baseline 退化到 ~5 cm。

**chip 选型**：
| Receiver | 频段 | 价格 `UNVERIFIED` | 用途 |
|---|---|---|---|
| **u-blox NEO-M9N** | L1+E1+B1+GLN | $40 | mid-range drone / 手持 |
| **u-blox F9P** | L1+L2+E1+E5b+B1+B2a | $200 | 消费级 RTK |
| **Trimble BD982** | 全频 + heading | $5000 | 测量 / mapping drone |
| **Septentrio AsteRx** | 全频 + jamming detect | $5000+ | 商用 / 防御 |
| **NovAtel OEM7** | 全频 + INS-tight | $10000+ | 高端 mobile mapping |

---

## 5 · PPP (Precise Point Positioning) — 全球 cm 级，无 base

替代 RTK：用全球网络的卫星 orbit + clock corrections（IGS / JAXA / ESA 推送）→ 单 receiver 也能达到 cm 级。**代价**：收敛慢 (典型 30 min)，需 internet 链路实时获取 corrections。

**应用**：远海 (无 RTK base) 测绘、global drone fleet 不想架 base。

**PPP-AR (PPP with Ambiguity Resolution)** — 近年突破，收敛压到 ~5 min。

---

## 6 · Worked example — 4 颗卫星 trilateration 几何

```
Setup:  rover at (0, 0, 0) (unknown to solver)
        4 sats at known positions (truth):
          Sat1: ( 20000, 0,     20000) km  → r₁ = √(20000² + 20000²) ≈ 28284 km
          Sat2: (-20000, 0,     20000) km  → r₂ ≈ 28284
          Sat3: (     0, 20000, 20000) km  → r₃ ≈ 28284
          Sat4: (     0, 0,     20200) km  (头顶)
        Receiver clock bias δt → 全部测距 +c·δt
```

每颗卫星给一个方程：`(x-xᵢ)² + (y-yᵢ)² + (z-zᵢ)² = (PRᵢ - c·δt)²`。4 方程 4 未知 (x, y, z, δt)，非线性 → 线性化 Newton iteration → 收敛。

**DOP (Dilution of Precision)** — 衡量几何强度。4 颗紧密排在头顶 → vertical 解极强但 horizontal 弱（HDOP 高）。4 颗分散到地平线 → horizontal 强 vertical 弱。**实战 drone**：HDOP 通常 0.8–1.5；VDOP 1.5–3 (vertical 总比 horizontal 差 ~2× 因为没卫星在地平线**下方**)。

**Why vertical worse**：所有 GNSS 卫星都在地平线**之上** → 几何信息在 vertical 方向单边 → 不可避免 ~3× 放大。这就是为什么 drone 必须用 barometer 补 vertical（见 `barometer_pressure_altimetry.md`）。

---

## 7 · Dropouts — 真实环境

| 环境 | dropout 程度 | 原因 |
|---|---|---|
| **Open sky** | 无 | 卫星全可见 |
| **Urban canyon** | 频繁 NLOS / 多径 | 楼挡 + 反射 |
| **Tunnel / 室内** | 完全无信号 | 信号被建筑屏蔽 |
| **树冠下** | 信号衰减 6–15 dB `UNVERIFIED` | leaf attenuation |
| **山谷 / 峡谷** | NLOS 边卫星丢失 | 地形遮挡 |
| **靠近高大金属物（船 / 桥）** | 多径主导 | 反射 |

**drone 实战**：起飞前等 GNSS 锁定 ≥8 颗卫星、HDOP&lt;2，否则不解锁。飞行中 GNSS quality monitor 触发 RTL (return-to-launch) 或 position hold loss。

---

## 8 · Spoofing / Jamming — 实际威胁

**Jamming**：发射同频段噪声，receiver 信号-噪声比崩溃 → no fix。市售 12V 车载 jammer 100–500 m 范围。**对策**：detect 信号强度异常 → 切换 IMU + visual + 备份 channel。

**Spoofing**：发射假卫星信号让 receiver 解出错误位置。2011 年 Iran 据称用此方式诱降美 RQ-170。**对策**：cryptographic authentication (Galileo OS-NMA 在 2024 部署)、receiver 多天线 angle-of-arrival 检测、与 INS 一致性 check。

**民用 drone**：DJI 等大厂部分启用 Galileo OS-NMA。Skydio 用 IMU + visual + 多 GNSS 一致性 cross-check。

---

## 9 · Hidden Assumptions — GNSS 默默押注的前提

下游 EKF / 控制器假设这些条件：

- **≥4 颗卫星可见.** Dropout 时 fix 完全消失（不只是降级）。
- **几何 DOP 合理.** 城市峡谷 PDOP>10 时 fix 仍然 valid bit = 1，但精度可能 50 m。
- **电离层 / 对流层在 single freq 时可建模.** 太阳活动峰 / 磁暴破之。
- **RTK base 位置已知 + 链路 &lt;2 s 延迟.** 链路丢 → 退化到 PPP / standalone。
- **No spoofing / jamming.** 民用环境通常成立，受关注地区不一定。
- **Receiver thermal stable.** 温度跳变期间 oscillator 漂移导致瞬态精度下降。
- **EKF 信任 GNSS innovation.** 多径产生 outlier 不被 reject 时 fix 漂数十米。
- **Time tag accurate.** GNSS 与其他 sensor 时间同步精度 &lt; 10 ms (高速 drone 严格 &lt; 1 ms)。

---

## 10 · 跨 embodiment 比较 + interview tip

| Embodiment | GNSS 角色 | 主要 failure mode | one driver |
|---|---|---|---|
| **Drone (outdoor)** | absolute position 主力 + RTK 高精度任务 | 树冠 / 城市峡谷 / GPS-denied | 不可缺；EKF state |
| **Drone (indoor / GPS-denied)** | 关闭，靠 VIO + lidar | spoofing 不是问题 | 不适用 |
| **AD car (highway)** | 主位置参考 + IMU + map matching 融合 | 高架桥下 / 隧道 dropout | RTK + dead reckon |
| **AD car (urban)** | 不可信主力，融合 lidar + HD map | 多径 / 多卫星阻挡 | 仅做 coarse anchor |
| **AGV (indoor)** | 不用 | — | 不适用 |
| **AGV (outdoor)** | RTK 主力 | 仓库金属墙边多径 | 工业级 receiver |
| **Marine (surface)** | RTK + INS | 浪 / 船体反射 | 全频 receiver |
| **AUV (underwater)** | 完全不可用 | 水大幅吸收 GHz 信号 | DVL + INS 替代 |

**🎙️ Interview Tip.** 被问"为什么 drone 室内不用 GPS"？— 一句答：GHz 信号穿混凝土衰减 >30 dB，加上室内多径，碰运气也只是 noise + bias，不如直接 disable 用 VIO。

---

## 11 · For the reader

- **Drone outdoor 30 m 距离** — F9P + RTK base，cm 精度。
- **Drone urban / 树冠** — 多星座 + 多频 + 备份 IMU/visual，预期降级。
- **AGV / outdoor robot** — 工业 RTK receiver + INS tight-coupling。
- **AD highway** — multi-constellation + map matching；不指望 RTK 在桥下。
- **AUV / 室内** — 跳过 GNSS。
- **远海 / 全球部署** — PPP-AR 替代 RTK。

---

## References

- u-blox F9P / NEO-M9N integration manuals `UNVERIFIED, no DOI`
- IS-GPS-200 (GPS interface spec)
- Galileo OS-NMA spec (EU 2024)
- Teunissen, "The LAMBDA Method for the GNSS Compass" (Artificial Satellites 2006)
- Misra & Enge, "Global Positioning System: Signals, Measurements, and Performance" (Ganga-Jamuna Press)
- Humphreys et al., "Assessing the Spoofing Threat" (GPS World 2008)

## Boundary

- `barometer_pressure_altimetry.md` — vertical 补 GNSS
- `magnetometer_geomagnetic_field.md` — yaw 补 GNSS (低速时)
- `imu_physics_and_noise_model.md` — GNSS-denied 时 INS dead reckon
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment GNSS 取舍
- `embodiments/aerial/sensor-stack/` — drone GNSS 集成实战
- `embodiments/aerial/long-range-slam/` — GPS-denied 长航时 SLAM

*2026-05-21. v1 初版。`UNVERIFIED` → v1.1 vendor primary 引用。*

---
[← Back to sensor-physics README](./overview.md)
