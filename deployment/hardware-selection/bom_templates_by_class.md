# BoM 模板（按 embodiment 等级） / BoM Templates by Embodiment Class

> **发布时间**：2026-05-21
> **适用范围**：5 类典型 embodiment × $500–$200k 预算段
> **核心定位**：把「应用 → 可下单 BoM」这一步从产品立项当天的手忙脚乱，写成可复用模板。

**Status:** v1 — opinionated draft。所有 SKU 价格 / 重量 / 功耗均标 `UNVERIFIED`，需以 vendor 一手 datasheet 为准；2026-05 报价快照，半年后可能漂 ±30%。
**Wedge tier:** N/A（deployment 工程文，非 W1/W2 旗舰）
**TL;DR:** 5 份 starter BoM——$500 indoor AGV / $5k outdoor drone（250g racer + 1.5kg payload）/ $50k AD demo / $200k AUV / 桌面 manipulation。**每一份都把「第三颗 sensor」明示**——IMU 与一颗相机是普遍必选，第三颗（RGBD / LiDAR / radar / sonar / 无）才是 embodiment 身份。

### X-Ray 开场（非专家友好）

(a) BoM = 产品立项当天工程师手里要拿的那张纸：vendor + 型号 + 价格 + 重量 + 功耗 + 接口。(b) 跨 embodiment 看，IMU 与一颗相机几乎总在表里；真正分类的是第三颗 sensor。(c) 对硬件 / 系统工程师，本文是 starter——production BoM 要加供应链 / lead time / 替代品列。

### 📍 研究全景时间线

```
2010 ── HDL-64 era：BoM 上 LiDAR 一项就 $80k；AD 之外没人敢碰
2015 ── Bosch BMI / InvenSense $3 MEMS IMU：drone BoM 翻篇
2017 ── RealSense D400 量产 $300/70g：indoor RGBD 标配
2020 ── Apple iPad Pro dToF：消费 SPAD normalize
2023 ── Livox Mid-360 $1k/250g：3kg+ drone LiDAR 可行
2025 ── Hesai AT128 $15–25k：AD demo BoM 从 $80k 砍半
        ── 你在这里 (2026) ──
?    ── <100g solid-state automotive LiDAR <$2k？aerial 卡格翻篇？
```

---

## 1 · 五份 BoM Starter（汇总）

📌 **Napkin Formula**:

```
BoM_total ≈ Σ(sensor + compute + power + structure)
         × (1 + cert)        ← 0.5–2× 常见
         × (1 + integration) ← 0.2–0.5× 常见
```

学界 BoM 只算 `Σ sensor`；产品 BoM 要把后两项算进去，否则发布时差一半。

| Class | 总预算 | 重量 / 功耗 | 第三颗 sensor | 距离 |
|---|---|---|---|---|
| Indoor AGV | $500 | 5–15 kg / 20–40 W | RGBD（D435） | 0.5–5 m |
| Aerial racer | $5k | 250 g / 15 W | 无 | 5–50 m |
| Aerial payload | $5k | 1.5 kg / 25 W | Livox Mid-360 | 1–40 m |
| AD demo | $50k | — / 数百 W | Hesai AT128 | 5–200 m |
| AUV survey | $200k | 30–80 kg | DVL + multibeam | 0.5–30 m 水下 |
| Tabletop manip | $25k（不含臂） | 桌面 | Polar cam + 触觉 | 0.1–1 m |

---

## 2 · BoM #1 — $500 室内 AGV

应用：仓储 / 配送 / 巡检；室内 + WiFi + floor map。

| 项目 | Vendor / 型号 | 单价 | 重量 | 功耗 |
|---|---|---|---|---|
| RGBD 前向 | RealSense D435 | $300 | 70 g | 3.5 W |
| IMU 板载 | Bosch BMI270 | $3 | <1 g | <5 mW |
| 超声 ×4 | HC-SR04 | $5/颗 | 10 g/颗 | 0.5 W |
| 主控 | Raspberry Pi 5（8 GB） | $80 | 50 g | 6 W |
| 轮编码器 ×2 | quadrature | $20/颗 | 20 g/颗 | <1 W |
| 电池 + 结构 / 线材 | 3S 5000 mAh LiPo + 杂项 | ~$70 | 400 g + — | — |
| **合计** | | **~$520** | ~600 g | **<15 W avg** |

价格 2026-05 零售快照 `UNVERIFIED`。D435 在 0.5–5 m 室内可当稀疏 2D 虚拟激光雷达，跳 LiDAR；IMU 板载即可；超声补 D435 FOV 外侧方；不通过 SEMI S2。详见 `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`。

---

## 3 · BoM #2 — $5k drone（250 g racer）

应用：FPV racing / 短途巡检；纯室外 + mono + 极简算力。

| 项目 | Vendor / 型号 | 单价 | 重量 | 功耗 |
|---|---|---|---|---|
| Mono GS | OmniVision OV9281 / Arducam | $80 | 5 g | 0.5 W |
| IMU | BMI270 / ICM-42688 | $5 | <1 g | <5 mW |
| 气压计 | BMP388 | $5 | <1 g | <1 mW |
| GPS | u-blox NEO-M9 | $40 | 8 g | 0.2 W |
| 飞控 | Betaflight F7 | $60 | 8 g | 1 W |
| ESC + 电机 + 桨 | 2207 1750KV ×4 | $200 | ~120 g | 视油门 |
| 电池 | 6S 1300 mAh | $40 | 180 g | — |
| 图传 + 接收 | analog VTX + ELRS | $80 | 10 g | 1 W |
| 机架 | 5" 碳纤维 | $50 | 90 g | — |
| **合计** | | **~$560** | 250 g | ~15 W avionics |

`UNVERIFIED`。racer BoM 远低于 $5k；预算余量给备机 + 备电 + 地面站。RGBD / LiDAR 全跳过——250 g 包络塞不下（`crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` §3.1）。IMU + mono + baro + GPS 是全部 perception；fallback = 飞手 + ELRS。无避障。

---

## 4 · BoM #3 — $5k drone（1.5 kg payload 巡检）

应用：电力 / 农业 / 物流；可载 200–500 g 任务负载。

| 项目 | Vendor / 型号 | 单价 | 重量 | 功耗 |
|---|---|---|---|---|
| Mono GS 前向 | Arducam OV9281 | $80 | 5 g | 0.5 W |
| 下视 stereo | 双 OV9281 | $200 | 30 g | 1 W |
| LiDAR | Livox Mid-360 | $1k | 250 g | 8 W |
| IMU 高精 | BMI270 + ADIS16465 备用 | $400 | 30 g | 1 W |
| GPS-RTK | u-blox ZED-F9P + L1/L2 | $400 | 40 g | 0.5 W |
| 主控 | Jetson Orin Nano 8GB | $250 | 75 g | 10 W |
| 飞控 | Pixhawk 6X / Cube Orange | $400 | 60 g | 2 W |
| ESC + 电机 + 桨 | 2814 920KV ×4 | $400 | 600 g | 视油门 |
| 电池 | 6S 8000 mAh | $150 | 1100 g | — |
| 图传 + LTE backup | 数字图传 | $300 | 100 g | 5 W |
| 机架 + 云台 | 13" 折叠 + 2 轴 | $500 | 600 g | 1 W |
| **avionics 合计** | | **~$4,080** | ~2.9 kg | ~30 W |

`UNVERIFIED`。Mid-360 是 2025 年才让 1.5 kg 级 LiDAR 现实化的关键（VLP-16 580 g vetoed）。下视 stereo 用于 <5 m 着陆 / 避障；前向 mono 用于 5–50 m。RGBD 跳过——户外 850 nm 2 m 外被太阳压住。硬件触发同步必须（`deployment/multi-modal-sync/`）。

---

## 5 · BoM #4 — $50k AD demo

应用：研究 demo / 园区低速 / L2+ 数据采集（非量产车规）。

| 项目 | Vendor / 型号 | 单价 |
|---|---|---|
| 前向长距 LiDAR | Hesai AT128 | $15k–25k |
| 周视相机 ×6 | Sony IMX390 + Leopard | $400/颗 |
| 前向 stereo | ZED 2i / 自组 | $1k |
| 角 radar ×4 | Continental ARS548 | $500/颗 |
| 前向长距 radar | Continental ARS548 | $1.5k |
| IMU（auto-grade） | KVH 1750 FOG / Honeywell HG4930 | $5k–15k |
| GNSS-RTK | NovAtel PwrPak7 | $5k |
| 主控 | DRIVE AGX Orin 或 2× Jetson AGX Orin | $5k–10k |
| 同步 PTP grandmaster + 线束 / 机柜 / 电源 | — | ~$3.5k |
| **合计** | | **~$40k–55k** |

`UNVERIFIED`。Hesai AT128 单项常占 BoM 30–50%——「Tesla 还是 Waymo 学派」实际就是「这一项 $20k 花还是不花」。

**设计点**：全部 sensor 必须 PTP（详见 `deployment/multi-modal-sync/`）；软件时间戳在 AD scale 直接报废。量产车还要叠 ISO 26262 ASIL-D 冗余 + 车规连接器 + EMC，价格 ×3–5。详见 `foundations/sensor-physics/lidar_physics_905_vs_1550.md`。

---

## 6 · BoM #5 — $200k AUV survey

应用：海底测绘 / 管道 / 科研；100–500 m 水深。

| 项目 | Vendor / 型号 | 单价 |
|---|---|---|
| 多波束 sonar | Norbit iWBMSh / R2Sonic | $80k–150k |
| DVL | Nortek DVL1000 / RDI Workhorse | $25k |
| 侧扫 sonar | Edgetech 2205 | $40k |
| FOG IMU | KVH 1750 / iXblue Phins | $15k–80k |
| USBL acoustic positioning | Sonardyne Ranger 2 | $30k |
| CTD | Sea-Bird SBE 49 | $10k |
| 光学相机 aux | GoPro / Allied Vision in housing | $2k |
| 主控（耐压舱） | Jetson AGX Orin + custom IO | $5k |
| 推进 + 浮力 + 框架 | — | $30k+ |
| **合计** | | **~$200k–300k+** |

`UNVERIFIED`。science-grade AUV 配置常突破 $1M。

**设计点**：光学不是主感知（NIR <1 m 被吸收）。DVL 是底面速度唯一来源；丢 DVL 等于丢 INS anchor。FOG 必须；MEMS 在 4 小时任务里漂到不可用。详见 `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` §3。

---

## 7 · BoM #6 — 桌面 manipulation cell（不含臂体）

| 项目 | Vendor / 型号 | 单价 |
|---|---|---|
| 腕部 RGBD | RealSense D435i | $350 |
| 第三视角 RGB | FLIR Blackfly S | $800 |
| 偏振相机 | Lucid Phoenix Polar | $3k `UNVERIFIED` |
| F/T sensor | ATI Nano17 / Mini40 | $5k |
| 触觉皮肤 ×2 | GelSight Mini / DIGIT | $1k/颗 |
| 主控 | Workstation（RTX 4090） | $4k |
| 标定板 + fixture | AprilGrid + 6-DoF | $500 |
| **合计** | | **~$15k–25k** |

详见 `crossing/failure-modes-atlas/transparent_reflective_deformable.md` §4a。

---

## 8 · Worked Example — $5k drone 为什么不能加 RGBD

```
当前 §4 BoM：~2.9 kg 含电池，hover 余量 ~+100 g。
塞 D435：+70 g, +3.5 W
  → 吃掉 70% 重量余量
  → 户外 2 m 外深度被太阳压垮（850 nm vs 1 kW/m²）
  → 工作距离 <2 m 与典型任务 5–50 m 不符
  → 付出 70 g 换不到任务可用的深度。
```

这是「drone 不上 RGBD」的工程账，不是「技术不成熟」。

---

## 9 · Hidden Assumptions

- 2026-05 价格快照；vendor 6 个月内可漂 ±30%（Hesai/Innoviz 24 个月已下移 3×）。
- 不含人工 / 集成 / 软件；production BoM 常 ×2。
- 不含 spare / lead time buffer；LiDAR / FOG / 海事 sensor 6–12 个月 lead time 是常态。
- `UNVERIFIED` 容差 ±2×；个别 SKU 偏差不动整体结构。
- 认证开销线性叠加是简化；SEMI S2 / ISO 26262 / IEC 60825-1 / 海事常非线性。

## 10 · 与基线对比 + 面试 Tip

| 视角 | 学界综述 | 本文 BoM |
|---|---|---|
| 列 sensor class | ✅ | ✅ |
| 一致基线 SKU + 价格 | ❌ | ✅ |
| 重量 / 功耗 | 偶尔 | ✅ |
| Lead time / 认证 | ❌ | TODO |
| 「为什么不选 X」 | ❌ | ✅ |

**Interview Tip**：被问「这架 drone 为什么没上 LiDAR / RGBD」——别答「技术不成熟」，答「70 g + 3.5 W + 太阳压制 + 距离不匹配」。每项都有具体数字。

---

## References

- Intel RealSense D435 / Livox Mid-360 / Hesai AT128 / KVH 1750 / Norbit iWBMSh / Nortek DVL1000 / Sea-Bird SBE 49 / Lucid Vision Phoenix Polar — vendor datasheets, `UNVERIFIED, no DOI`

## Boundary

本文给的是 starter BoM，不是 production 采购单。Production 需要：vendor 一手 datasheet 核对、lead time 锁定、备选 SKU 列、认证清单（SEMI S2 / ISO 26262 / IEC 60825-1 / 海事）、EMC / 环境测试。**Sensor 物理参数与限值**归 `foundations/sensor-physics/`；**跨 embodiment 对比矩阵**归 `crossing/sensor-stack-matrix/`；**算力 / 模型可行性**归 `deployment/compute-budget/`；**同步设计**归 `deployment/multi-modal-sync/`。

---

[← Back to Hardware Selection README](./README.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
