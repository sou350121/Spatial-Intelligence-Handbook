# WiFi / 5G NR 射频定位物理 (WiFi / 5G NR RF Positioning Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — WiFi RTT (802.11mc/az) + 5G NR positioning + RSSI fingerprinting
> **核心定位**：WiFi / 5G 是**复用已部署基础设施**的室内定位 — 精度永远比 UWB 差 10×，但**0 元新增 anchor**这件事决定了它在大型场所赢

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 3GPP / 802.11 标准 + 厂商白皮书核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) WiFi RTT（IEEE 802.11mc / FTM, fine timing measurement）用 2.4 / 5 / 6 GHz WiFi 信号做 ToF 测距 — 20-160 MHz 带宽给 σ_d ~1-2 m；5G NR Rel-17/18 positioning service 用 100-400 MHz BW + AoA beamforming 拼到 0.5-3 m。(b) 不需要新装 anchor — 商场 / 机场 / 仓库**已经**布满 WiFi AP 和 5G small cell，定位是"软件升级"附赠功能。(c) 对机器人工程师：WiFi 定位是仓库 AGV 替代 LiDAR SLAM 的现实路径之一 — 精度够用（货架间距 2-3 m），运维成本 1/10。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2000s ── RSSI fingerprinting (Microsoft RADAR, 2000) — 第一代 WiFi 定位，精度 3-10 m
2016 ── IEEE 802.11mc 标准化 FTM — WiFi RTT 进 spec
2018 ── Google Pixel 3 支持 WiFi RTT（首个 mass-market 端）
2020 ── 3GPP Rel-16 — 5G NR positioning service 首次纳入
2022 ── 3GPP Rel-17 — sub-meter positioning target
2023 ── Apple Indoor Maps / Google Indoor Maps — WiFi fingerprint + RTT 商用
2024 ── 3GPP Rel-18 — 0.5 m horizontal / 1 m vertical 目标
        ── 你在这里 (2026) ──
?    ── 5G-Advanced (Rel-19) cm 级 positioning ambition / 6G ISAC sensing+comm 融合
```

WiFi 定位"卡在 1-2 m"近 10 年；5G 是**真正可能突破**的下一代物理 — 带宽够宽（400 MHz）+ AoA 多天线 + 同步基础设施完善。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
WiFi RTT (FTM):
T_round = 2·T_prop + T_processing
d ≈ c × (T_round - T_processing) / 2

精度上限 σ_d ≈ c / (2·BW):
- 802.11n  20 MHz  → σ_d ~7.5 m  (理论)
- 802.11ac 80 MHz  → σ_d ~1.9 m
- 802.11ax 160 MHz → σ_d ~0.9 m
- 5G NR    400 MHz → σ_d ~0.4 m

实测约 2-3× 理论极限（multipath / SNR / clock）
```

WiFi 受限于 802.11 frame 结构 + symbol timing — 即使 160 MHz BW，实测精度 ~1-2 m；5G NR 用 PRS (positioning reference signal) 优化时间分辨率，能逼近理论极限。

### 1.1 三种定位方法

| 方法 | 物理基础 | 精度 | 部署成本 |
|---|---|---|---|
| **RSSI fingerprinting** | 信号强度衰减 | 3-10 m | 离线 mapping 高 |
| **WiFi RTT (FTM)** | ToF / 802.11mc | 1-3 m | AP 需支持 FTM |
| **5G NR positioning** | ToA / TDoA / AoA | 0.5-3 m | 5G base station |
| **5G + WiFi 融合** | EKF | 0.5-1 m | 两者都需 |

### 1.2 关键机制

⚡ **Eureka Moment.** WiFi / 5G 定位最大的杠杆**不是精度**，而是 **anchor 复用** — 商场已有 200 个 WiFi AP、3 个 5G small cell，UWB 室内定位需要重新挂 30 个 anchor + 布线 + 维护。即使 WiFi RTT 精度是 UWB 的 1/10，部署成本是 1/100 — 大型场所 ROI 完胜。

```
WiFi FTM Protocol:
STA  →  AP    FTM Request
STA  ←  AP    FTM_1 (t1, t4 timestamps)
STA  ←  AP    FTM_2 (t1, t4 of round 2)
...
After M rounds: RTT = mean[(t4-t1) - (t3-t2)]
d ≈ c × RTT / 2
```

### 1.3 5G NR Positioning 信号流

```
UE (机器人)
  │
  ├──→ gNB1 (cell A)       PRS broadcast / SRS uplink
  ├──→ gNB2 (cell B)       multi-cell 测时差
  ├──→ gNB3 (cell C)       TDoA trilateration
  │
  ↓ + 多天线 AoA + carrier phase

Location Management Function (LMF) → 计算 (x, y, z)
```

5G 的物理优势：**400 MHz BW + 64-256 element AoA antenna array + 1 ns 同步精度（PTP over fiber backbone）**。前两个 WiFi 永远拿不到。

---

## 2 · 数学核心：从 BW 到精度的极限 (Math Core)

📌 **Napkin Formula** (X-Ray)：σ_d ≈ c × √CRLB(σ_t) ≈ c / (2·BW·SNR^0.5)。BW 决定理论上限，SNR 决定实际接近度，multipath 决定实际下限。

### 2.1 Cramér-Rao Lower Bound (CRLB)

```
σ_t² ≥ 1 / (8π² × β² × SNR × N_samples)
β² = effective bandwidth (Hz², RMS spectrum)
```

变量：
- `β` — 等效带宽（rms of spectrum），≈ BW/√12 for flat spectrum
- `SNR` — linear, not dB
- `N` — symbol 数

对 80 MHz WiFi, SNR=20 dB, N=100 symbols → σ_t ~3 ns → σ_d ~1 m。这是物理下限；multipath / NLOS 把实际撑到 2-3 m。

### 2.2 RSSI Fingerprinting (老办法)

```
d ≈ 10^((P_0 - RSSI) / (10·n))
n ≈ 2-4 (path loss exponent，与建筑材料相关)
```

每个房间 RSSI 不同 → 离线 survey → kNN 查表。精度 3-10 m。**问题**：建筑改造 / 家具换位置 / AP 更换 → fingerprint 失效，需要重做 survey（数月人工 cost）。

### 2.3 AoA via Beamforming (5G 杀手锏)

```
θ_AoA ≈ arcsin(λ × Δφ / (2π × d_antenna))
```

64-element ULA (uniform linear array) @ 3.5 GHz (λ=8.6 cm), d=λ/2 → AoA 分辨率 ~1.4°。在 50 m 距离 → 1.2 m 横向定位精度。**这是 WiFi 不可能复制的物理优势**（WiFi AP 通常 2-4 天线）。

---

## 3 · Worked example — 商场 100×100 m²，6 WiFi AP + 3 5G small cell

设置：
- 6 个 802.11ax AP @ 5 GHz / 80 MHz BW，矩阵分布
- 3 个 5G NR FR1 small cell @ 3.5 GHz / 100 MHz BW
- 机器人 (50, 50) 位置

**WiFi-only:**
- 单 AP RTT σ_d ~2 m (multipath dominant)
- 6 AP trilateration + EKF → σ_xy ~1.5-2 m
- 室外 OK，靠墙 AP 旁边精度退化到 3-5 m (NLOS)

**5G-only:**
- ToA σ_d ~0.5 m + AoA 1.5° → ~1 m 单 cell
- 3 cell trilateration → σ_xy ~0.7-1 m

**WiFi + 5G fusion:**
- EKF 融合 → σ_xy ~0.5 m
- 配 IMU dead reckoning → tracking 100+ Hz

实测 Apple Indoor Maps + iPhone 在商场报告 ~1-3 m，**与上述粗算量级一致**。

---

## 4 · 工程视角 (Engineering View)

**部署成本.**
- WiFi-only: $0 增量（复用现有 AP）
- 5G-only: 需要室内 small cell ~$10-50k per cell，运营商 RAN 协议
- UWB 对比: 100×100 m² 需 ~16 anchor ~$3-5k + 布线 $10k+

**功耗.**
- WiFi RTT @ Android phone: 每次 ranging ~10 mJ；持续 1 Hz ranging ~30 mW 平均
- 5G positioning: 与正常 5G data 共用，~100-500 mW
- 机器人不痛；电池端用谨慎

**延迟.**
- WiFi FTM: 单次 ~10 ms (multiple round trips)
- 5G NR: ~5-20 ms (cell coordination)
- 远比 UWB DS-TWR (~1-5 ms) 慢

**地图维护.**
- RSSI fingerprinting: 6 月-1 年 re-survey
- WiFi RTT: AP 不动就稳定
- 5G: 运营商控制基站 — 机器人厂商无控制权

---

## 5 · 数据与评测 (Data & Eval)

- **3GPP TR 38.857** — 5G positioning study item，目标 50 cm horizontal
- **IPIN competition** — WiFi 定位每年报告，typical 2-5 m
- **Apple Indoor Maps coverage** — 已上线 5000+ 机场 / 商场 / 体育馆，user-facing 精度 ~5-10 m（fingerprinting + RTT）
- **Google Indoor Maps** — 同量级覆盖

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 大场所室内定位 1-3 m；零增量基础设施；和现有 phone / IoT 设备直接互通；动态环境（家具变化）不需重 survey（vs fingerprinting）。

**不能做什么.** cm 级（需要 UWB）；密闭金属空间（电梯井 / 集装箱）；地下（无 5G 覆盖）；高速移动（>30 km/h Doppler 误差）。

### Hidden Assumptions

- **AP 已知位置 + 启用 FTM.** 商用 AP 大半还没开 FTM；运营商 small cell 也未必开 PRS
- **multipath 不极端.** 钢筋丛林（重金属架）破坏 first-path 估计
- **不超过 phone 端能力.** Android RTT 支持参差，iOS 至今未开放 FTM API（截至 2026 年初）
- **小区切换 < 定位周期.** 移动机器人在 cell 边界切换时精度爆炸
- **运营商配合.** 5G 定位需要 LMF 部署 — 中国 / 美国 / 欧洲进度不同

**失败模式：**
- **AP 时钟漂.** 商用 AP 用便宜晶振，FTM 测得 systematic bias
- **fingerprint 失效.** 装修 / 货架重排 → 离线 survey 数据废
- **NLOS bias.** WiFi 穿墙 +1-3 m systematic 偏远
- **承载 vs 定位冲突.** 高负载 AP 优先服务数据流量，FTM 响应不准时

---

## 7 · 与相关工作对比 (Comparison)

| 方案 | 精度 | 部署成本 | 维护 | 设备兼容 |
|---|---|---|---|---|
| **WiFi RTT** | 1-3 m | $ (复用 AP) | 低 | Android / 部分 |
| **WiFi fingerprint** | 3-10 m | $$ (survey) | 高 (re-survey) | 全部 |
| **5G NR pos** | 0.5-3 m | $$$ (gNB) | 低 | 5G UE |
| **UWB** | 5-30 cm | $$ (anchor) | 低 | 专 UWB chip |
| **BLE beacon** | 1-5 m | $ (battery) | 中 | 全部 |
| **GNSS** | 1-5 m 户外 | $0 | 0 | 全部 |

**🎙️ Interview Tip.** 被问"为什么不全用 UWB"？— 大型场所新装 anchor 成本远超精度 ROI；WiFi / 5G 复用已部署基础设施零增量。**精度 vs 部署成本**是 trade-off，不是技术孰优。

---

## 8 · For the reader

- **Manipulation** — 无关，workspace 太小
- **Mobile robot / AGV (仓库)** — WiFi RTT + 视觉 SLAM 融合是 2026 主流；纯 WiFi 精度不够避货架，融合可以
- **Drone (室内 inspection)** — WiFi 太粗，UWB 主流；5G positioning 在仓库内还不成熟
- **Phone / AR** — WiFi + 5G + VIO 融合，Apple / Google Indoor Maps 已落地
- **AD** — 户外 GNSS + 5G NR-positioning 作为隧道 / 城市峡谷 backup（→ `gnss_multi_constellation_rtk.md`）

---

## References

- IEEE 802.11mc-2016 — Fine Timing Measurement standard
- 3GPP TR 38.857 — Study on NR Positioning Enhancements (Rel-17)
- 3GPP TS 38.305 — Stage 2 functional specification of UE positioning in NG-RAN
- Cisco Hyperlocation white paper `UNVERIFIED, no DOI`
- Google WiFi RTT developer guide (developers.android.com/guide/topics/connectivity/wifi-rtt)

## Boundary

- WiFi RTT / 5G NR positioning 物理 → 本文
- `crossing/sensor-stack-matrix/` — WiFi 定位 vs UWB vs SLAM 跨 embodiment 取舍
- `embodiments/ground/sensor-stack/` — AGV 仓库 WiFi 定位工程部署
- VLC / Li-Fi 可见光定位 → 待续 wedge
- 5G ISAC（integrated sensing + communication）研究方向 → 暂不在本目录

*2026-05-21. v1. UNVERIFIED → v1.1 待 3GPP / 802.11 spec 核对。*

---
[← Back to sensor-physics README](./overview.md)
