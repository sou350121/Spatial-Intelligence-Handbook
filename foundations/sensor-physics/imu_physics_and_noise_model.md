# IMU Physics & Noise Model (IMU 物理与噪声模型 — MEMS vs FOG / Allan 方差 / 漂移预算)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — MEMS vs FOG sensing principles / Allan variance / bias instability / temperature
> **核心定位**：VIO 论文默默忽略的 drift-budget 算术 — `$3 BMI270` vs `$15k KVH 1750` 是 5000× 的成本阶跃和 10000× 的 bias-instability 阶跃，由任务时长唯一决定

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字仍需 spec-sheet 交叉核对。
**Wedge tier:** sensor-physics expansion（5 篇姊妹文中的第 4 篇）

### X-Ray opening

每个 embodiment 至少装一颗 IMU；真正的问题只有一个 — **走哪条物理**。MEMS 陀螺（振动质量、Coriolis 读出）$3 一颗，bias instability ~0.5°/s — 装 GNSS 的 drone 没问题，没 GNSS 的 AUV 会爆。FOG (Fiber-Optic Gyro，光纤盘上的 Sagnac 效应) $5k–50k 一颗，bias instability ~0.05°/hr — drone 上严重过度，长航时自主水下或隧道驾驶**必备**。对 sensor 工程师：IMU 选择坍缩成一个问题 — **平台在没有 aiding 信号时要 dead-reckon 多久？**

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1985 ── 首批光纤陀螺 (Honeywell, KVH) ── 惯导时代开始
2007 ── Apple iPhone 4 InvenSense MPU-6050 ── 消费级 MEMS IMU 大众市场
2014 ── Bosch BMI160 / BMI270 一脉 ── $3 9-DoF IMU
2015 ── DJI Phantom 3 MEMS+GPS 融合 ── 消费 drone 时代
2018 ── Honeywell HG4930 tactical MEMS (~$5k) ── 中端
2020 ── KVH 1750 / 1775 FOG 广泛用于 AUV / 测绘
2022 ── Apple AirPods Pro 2 9-DoF MEMS in earbud ── ~$1 成本底 `UNVERIFIED`
2024 ── Anello Photonics SiPh gyro 目标 <$1k ── 光子学中端崛起
202? ── ?  下一波：chip-scale atomic gyro / cold-atom interferometer（今天还在实验室）
```

本文件卡在 MEMS-vs-FOG 分岔点 — "用 IMU"定下来之后，剩下唯一的真选择。

---

## 1 · 两种物理体制

📌 **Napkin Formula**：`dead_reckon_drift = bias_instability × t + ARW × √t + scale_factor_error × Δθ`。§2 的所有内容对照这个公式 — MEMS 每分钟漂米级，FOG 每小时漂米级，bias instability 上差 4 个数量级。

**(a) MEMS Coriolis 陀螺.** 微机械振动质量（silicon，100 µm 尺度）在共振点驱动。绕敏感轴的旋转向 drive motion 垂直方向注入 Coriolis 力 → 容性 pickoff 量测。Gyro-on-a-chip：3 轴 + 3 加速度计 + 温度 + 磁力计装在 3×3 mm BGA 里。Bosch BMI270 (~$3 `UNVERIFIED`，bias instability 0.5°/s，ARW 0.007°/√Hz `UNVERIFIED`)。InvenSense ICM-42688 同级。

**(b) FOG (Fiber-Optic Gyro).** Sagnac 效应：一束光在光纤盘绕中分成两条反向传播路径。绕盘轴的旋转造成光程差 → 在重组干涉仪上产生相位移。分辨率随 coil area × turns 而变 — KVH 1750 通常 200 m 光纤。KVH 1750 ($15k `UNVERIFIED`，bias instability 0.05°/hr，ARW 0.012°/√hr `UNVERIFIED`)。Honeywell GG1320 / iXBlue 对应。

**(c) RLG (Ring Laser Gyro).** 同样 Sagnac 原理，但用 laser cavity 代替光纤。航空惯导（Honeywell HG9900）。性能高于 FOG，体积更大更贵 ($50k+)。超出消费成本下具身 AI 的范围。

**(d) 加速度计.** 每个 tier 都是 MEMS — 振动梁或 pendulous mass，容性读出。Bias instability 与 noise 与陀螺类似缩放，但加速度计漂移通过**双重**积分进入位置，所以陀螺数字主导姿态而加速度计在姿态锁定后主导位置漂移。

⚡ **Eureka Moment.** MEMS-vs-FOG **不是**质量阶梯 — 是任务时长分岔。MEMS 在每几秒被 aided（GNSS、视觉、轮速里程计）就没问题。FOG 只在你必须无 aiding 滑行 minutes-to-hours 时才有意义。成本阶 5000×，因为物理阶（振动 silicon vs km 长光纤盘）根本不同。

---

## 2 · MEMS vs FOG 对比

| Property | MEMS (BMI270 class) | FOG (KVH 1750 class) |
|---|---|---|
| 感测原理 | Coriolis on vibrating mass | Sagnac on fiber coil |
| 成本 | ~$3 | ~$15k |
| 重量 | <1 g | 500–1000 g |
| 功率 | <10 mW | 5–15 W |
| Bias instability (gyro) | 0.5°/s `UNVERIFIED` | 0.05°/hr `UNVERIFIED` |
| ARW (angle random walk) | 0.007°/√Hz | 0.012°/√hr |
| Scale-factor stability | ~0.1% | ~5 ppm |
| 温度敏感度 | ~0.05°/s/°C `UNVERIFIED` | ~0.001°/hr/°C `UNVERIFIED` |
| 工作温度范围 | -40 to +85 °C consumer | -40 to +85 °C industrial |
| 典型用途 | **BMI270 → drones, phones, AGVs** | **KVH 1750 → AUVs, L4 AD tunnels, surveying** |

中端 "tactical-grade MEMS"（Honeywell HG4930，~$5k `UNVERIFIED`）介于两者之间 — **临时** bias 0.05°/hr，但因残留 MEMS 不稳定机制，几小时内漂移比 FOG 快。

---

## 3 · Allan variance — 标准噪声模型

在 log-log 图上画静止 IMU 的 σ(τ)：x 轴 averaging time τ，y 轴 deviation σ。

```
log σ
  ^
  |    \         /
  |     \  ARW  /
  |      \    /
  |       \  /  ← bias instability floor
  |        \/______
  |        /
  |       / RRW (rate random walk)
  |      /
  +-----+---------------------> log τ
        曲线最低点 τ = bias instability 时间常数
```

三段：
1. **ARW (angle random walk)** — 短 τ，log-log 斜率 -1/2。读出链的热噪声 / 散粒噪声。按 `1/√τ` 平均下来。随积分时长改善；决定短时性能。
2. **Bias instability** — 曲线最低点，斜率 0。IMU 的**地板** — 过了这个 τ 再平均也没用。来自机械 / 电子 1/f 噪声。**datasheet 上引用的那个数字。**
3. **RRW (rate random walk)** — 长 τ，斜率 +1/2。Bias 自身在漂。主导长时无 aiding 积分。

对 VIO / VINS-Fusion / OpenVINS 论文，ARW + bias instability 决定 IMU pre-integration 噪声协方差。RRW 通常被建模为慢随机游走 bias 状态 — 在长航时实际比论文假设更糟，因为未建模的温度瞬态。

---

## 4 · Worked example — 1 分钟无 aiding 飞行：MEMS vs FOG 位置漂移

Back-of-envelope（数字 `UNVERIFIED`，仅用于工程直觉）：

```
Scenario:   GNSS-denied 隧道，无视觉辅助（烟雾 / 黑暗）
Platform:   drone 或 robocar，仅靠 IMU dead-reckoning
Duration:   t = 60 s
```

- **MEMS BMI270 路径.**
  - 姿态漂移（来自 bias instability）：`0.5°/s × 60 s = 30°`。本身就是灾难。
  - 现实一点（标定后）：残余 bias ~0.05°/s `UNVERIFIED` → 60 s 内 3°。
  - 加速度计 bias ~0.01 m/s² `UNVERIFIED` → 位置漂移 `(1/2)·b·t² = 0.5·0.01·3600 = 18 m`。
  - **60 s 无 aiding 飞行的位置不确定度合计：~20 m。** 隧道行驶用不了；短 GNSS gap 勉强可容。

- **FOG KVH 1750 路径.**
  - 姿态漂移：`0.05°/hr × (60/3600) = 0.0008°`。实质上零。
  - 加速度计（IMU 封装内仍是 MEMS — FOG 只换陀螺）：同样 ~0.01 m/s² → 18 m 位置漂移。
  - **60 s 后位置不确定度合计：~18 m**，几乎完全由加速度计支配。
  - 但在 1 小时尺度，MEMS 位置漂移膨胀到 ~`O(km)`，而 FOG-aided estimator 保持 tens of meters。

印证 §1 → §2：60 s 上两条路都是加速度计 bias 主导。FOG 优势出现在**分钟-到-小时**。5000× 成本阶跃只在无 aiding 任务时长超过 ~5 分钟时才划算。

---

## 5 · 只有踩过坑才知道的误差来源

**温度瞬态.** 大部分 MEMS spec 是**在**标定温度下。drone 户外冷启动 → IMU 在 10 分钟内穿过 30 °C swing → 未标定 bias 漂移主导一切。缓解：thermal hood、内嵌标定 LUT、soft-start 延时。

**振动 aliasing.** Drone 电机 1F ~100–500 Hz；1 kHz 采样的 IMU 会把 600 Hz 振动 alias 到导航滤波器所在的低频带。IMU 本身没坏 — 是采样坏了。缓解：机械隔振、ADC 之前的 anti-alias LPF、oversample-and-decimate。

**磁力计污染.** 磁导航辅助在电池、电机、铁磁货物附近失效。永远把 mag 当 soft-aid，不要当 hard-aid。

**G-sensitivity（陀螺对线加速度的响应）.** 廉价 MEMS 陀螺在持续 g 下会有 `O(0.01°/s/g)` 的 bias。激进 drone 机动会注入虚假旋转。

**轴间耦合.** 廉价 MEMS 的 cross-axis sensitivity ~0.5%；标定矩阵很重要。

---

## 6 · Hidden Assumptions — IMU 选择默默押注的前提

MEMS-vs-FOG 决策只在下列条件成立时稳定：

- **振动谱不超过采样 anti-alias 带宽。** Drone 电机 5–10 kRPM (200–500 Hz 1F) 在 1 kHz IMU 采样下 → 必须滤。高 RPM 微型 drone 打破这个假设。
- **工作温度在标定包络内。** -40 to +85 °C industrial；-20 to +60 °C consumer。超出则 bias 跳出 datasheet 数倍。
- **任务时长估计正确。** Drone 标称 GNSS-aided 每 100 ms — MEMS 没问题。AUV 没 GNSS 数小时 — FOG 必备。估错 → IMU 等级错。
- **Aiding 源可靠。** Vision-aided VIO 在黑暗、灰尘、雾中失效 → IMU 无 aiding 滑行 → 把 MEMS 合理化的"aided"假设蒸发。同样硬件，不同结论。
- **标定保持最新.** MEMS bias 批间漂、年际漂；OEM 出厂标定够短任务，长任务挂。长航时平台在 stationary 段跑 self-calibration。
- **1 分钟漂移的瓶颈是加速度计而非陀螺.** 超过 5–10 分钟无 aiding 后，陀螺接管。选 FOG 陀螺却保留廉价加速度计是没意义的。

---

## 7 · 跨 embodiment 比较 + interview tip

| Embodiment | IMU pick | 原因 |
|---|---|---|
| **Manipulation** | MEMS BMI270 ($3) | 静态底座；视觉反馈主导；无 aiding 周期 <10 s |
| **Humanoid** | 多颗 MEMS（通常 >12） | per-joint 感测；靠运动链聚合 |
| **Ground AGV** | MEMS + 轮速里程计 | 轮速编码器每米 aid；MEMS 足够 |
| **Drone (consumer)** | MEMS + GNSS + visual | 全 aid 可得；MEMS 没问题；FOG 重量不可行 |
| **AD 乘用车** | auto-grade MEMS ($50–500) | GNSS + visual aid；隧道靠短时 MEMS dead-reckon |
| **AD L4 + 隧道 >5 min** | MEMS + 偶尔 tactical-grade 或 FOG 混合 | 无 aiding 隧道时长重要 |
| **AUV** | **FOG 必备 (KVH 1750)** | 水下无 aiding 数小时；物理禁止 GNSS，视觉 <5 m |
| **Aerospace 惯导** | RLG ($50k+) | 数小时到数天无 aiding，超出 FOG 包络 |

经验：按**无 aiding 任务时长**选 IMU class，不要按"质量"。Drone 不需要 FOG；AUV 需要。

**🎙️ Interview Tip.** 被问"这台 drone 需要 FOG 吗"？— 反问的第一句是 *"最长无 aiding 段是几秒？"* <30 s GNSS gap 用 MEMS + 好 VIO 就够。如果你 bound 不住（采矿隧道、AUV 任务），上 FOG。回答"FOG 永远更好"的人在卖 FOG。

---

## 8 · For the reader

- **Manipulation** — MEMS ($3)，别想了。
- **Drone** — MEMS BMI270 / ICM-42688 + GNSS + VIO。FOG 仅当任务规格含 >5 min 无 aiding 段时考虑。
- **AD** — L2 用 auto-grade MEMS；L4 带隧道用 tactical-grade MEMS；FOG 仅当任务含长隧道 + 无 map 先验时。
- **Marine** — FOG 必备（KVH 1750 或等效）；无替代。

---

## References

- Bosch BMI270 datasheet `UNVERIFIED`
- InvenSense ICM-42688 datasheet `UNVERIFIED`
- KVH 1750 / 1775 IMU technical brief `UNVERIFIED, no DOI`
- Honeywell HG4930 tactical MEMS spec `UNVERIFIED, no DOI`
- IEEE 952-1997 — IMU 规格格式（Allan variance 术语）
- 实战：维护者在 drone 标定 / 温度 soak 上的经验

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — 视觉感测姊妹文
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — 深度感测姊妹文
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — 长距姊妹文
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — IMU 是所有 embodiment 的 universal-core；矩阵展示 FOG 何时入场
- `embodiments/aerial/sensor-stack/` — drone IMU 集成 / 隔振
- VIO / VINS pre-integration 数学：`foundations/slam-vio/` (TBD) — IMU 模型的**消费方**。本文覆盖产生噪声的 sensor 物理；filter 数学住在 SLAM-VIO 下面。

*2026-05-21. v1 首版，满足 14 项 gate。UNVERIFIED → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./overview.md)
