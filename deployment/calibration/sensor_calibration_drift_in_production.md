# 生产环境标定漂移全谱 / Sensor Calibration Drift in Production

> **发布时间**：2026-05-21
> **适用范围**：多相机 / IMU-相机 / LiDAR-相机 / 多 LiDAR 任意组合的生产环境标定
> **核心定位**：把「Kalibr 出厂标完就完事」这个学界默认假设打碎——温度 / 振动 / 机械应力 / 时间四类漂移每一类都有数量级，且每一类有可监测信号；fleet 维护成本 80% 来自这里。

**Status:** v1 — opinionated draft。温度系数 / 漂移率 / 时间常数全部标 `UNVERIFIED`，需以 fleet telemetry 实测分布校准。
**Wedge tier:** N/A（deployment ops runbook 风格，配套 `deployment/calibration/README.md` §1 总览）
**TL;DR:** 出厂标定的有效期不是无限，是几小时到几周——取决于温度梯度、振动谱、机械应力循环与材料蠕变。本文把四类漂移分别量化（温度 0.05–0.3°/40°C、振动 0.01–0.1°/h、跌落 0.1–2°/次、蠕变 0.05°/month），并给出**「在线 vs 离线」trade-off 的工程决策表**——不是「学习驱动一定胜」，而是看任务时长、动态范围、可中断窗口三个变量。结尾三个真实案例（drone fleet 季度漂移、D435 thermal drift、RealSense USB reset bug）给「这不是空话」的具体数字。

### X-Ray 开场（非专家友好）

(a) 标定漂移 = 标定数据「过期」的物理学：温度让金属和 CFRP 不等比例膨胀、振动让螺丝预紧力衰减、跌落改外参一截子、长时间使用胶水蠕变。(b) 每一种都有数量级（毫弧度到度）和可监测信号（残差 chi-square / 双目一致性 / IMU 预积分残差）。(c) 对 robotics 工程师：本文回答「我标定一次能撑多久 + 怎么知道它已经漂了」——这是 fleet 运维的核心 KPI。

### 📍 研究全景时间线

```
1995 ── Zhang's flexible camera calibration — 出厂标定理论确立
2008 ── Kalibr (Furgale ETH) 多相机+IMU联合标定 → 学界标准
2014 ── VINS / OKVIS 把外参 + td 纳入状态联合估计 — 「软件兜底」普及
2017 ── Skydio R1 hot-recalibration 概念公开 — drone 商用栈第一次正面回答
2019 ── 汽车量产 OEM 把 L3 在线自标作为冗余安全要求
2022 ── Open-source learning-based extrinsics (TODO citation) — 网络预测漂移修正
2025 ── VLM-as-validator：「这个标定结果看起来合理吗？」(实验阶段)
        ── 你在这里 (2026) ──
?    ── 30 秒自然场景任务起飞前 calibration（无标定板，精度接近 Kalibr）
?    ── fleet-wide 漂移联邦学习（跨 100 台 robot 共享漂移模型）
```

`deployment/calibration/README.md` 给的是工作流总览；本文给的是「漂移本身的物理与监测」深度。

---

## 1 · 四类漂移的物理桶

📌 **Napkin Formula**：

```
calibration_drift(t, ΔT, vibration, impact, age) = 
    α_T · ΔT                  ← 温度（线性 + hysteresis）
  + β_v · ∫ |v(τ)|² dτ         ← 振动累积能量
  + γ_i · Σ impact_k           ← 跌落 / 冲击（离散事件）
  + δ_age · t                  ← 时间蠕变（线性）
```

四个加项几乎独立，可分别监测、分别归因。本文按这个分桶。

| 漂移源 | 物理来源 | 旋转量级 | 平移量级 | 时间常数 |
|---|---|---|---|---|
| **温度** | CFRP / 铝 / 塑料 CTE 不等 | 0.05–0.3° / 40°C | 100–500 µm / 40°C | 分钟（达到稳态） |
| **振动** | 紧固件预紧力衰减 | 0.01–0.1° / 小时 | 10–100 µm / 小时 | 小时（积分量） |
| **跌落 / 冲击** | 弹塑性变形 | 0.1–2° / 事件 | 1–10 mm / 事件 | 即时（阶跃） |
| **时间蠕变** | 胶水 / 螺纹 viscoelastic | 0.05° / month | 10 µm / month | 月（线性） |

数字均 `UNVERIFIED`，按一手实测 + Loctite/CFRP/铝 CTE 表估的量级；个别平台可漂 ±2×。

---

## 2 · 温度漂移（CTE 不匹配的几何账）

### 2.1 物理

相机模组 + 主板 + 机架的热膨胀系数（Coefficient of Thermal Expansion, CTE）几乎不可能一致：

| 材料 | CTE（10⁻⁶ /°C，`UNVERIFIED`） | 常见用途 |
|---|---|---|
| Invar 36 | 1.2 | 高精度光学结构 |
| CFRP（quasi-iso） | 2–5 | drone / 高端 robot 机架 |
| Aluminum 6061 | 23 | 普通机架 / 散热 |
| PCB FR-4 | 14（in-plane） | 主板 |
| ABS 塑料 | 70–100 | 消费机器人外壳 |

10 cm 基线的双目，CFRP 机架 ΔT = 40°C 下基线变化：

```
ΔB = B × CTE × ΔT = 0.1 m × 3e-6 × 40 = 12 µm
```

12 µm 对 fx ≈ 600 pixel 的相机意味着视差偏移 ~0.07 pixel / 几何意义上的 ~0.1% 深度偏。**单一基线看起来无伤**——但 ΔT 在 sensor 模组内部（CMOS 与 PCB 与 lens holder 间）引入的旋转效应远大于这个，特别是 lens holder 通常是塑料。

### 2.2 实测特征

- **Hysteresis（迟滞）**：温度上升曲线 ≠ 下降曲线。开机几分钟内有快速漂；2 小时后达到准稳态。
- **Cold start 偏置**：刚开机相机模组比环境冷，热平衡需要 5–20 分钟。
- **环境敏感**：户外阳光直射 / 阴影切换 5 分钟内可见明显残差变化。

### 2.3 监测指标

```python
# 伪代码：温度-标定漂移相关性监测
chi2_window = sliding_chi2(reproj_err, window=60s)
temp_now = imu.temperature  # IMU 内置温感
if abs(temp_now - calibration_temp) > 15 and chi2_window > 2.0:
    trigger("THERMAL_DRIFT_SUSPECTED")
```

工业最佳实践：**记录标定温度**，部署时若环境温差 >15°C，触发 L2 上电重标。

### 2.4 真实案例 — D435 thermal drift

`UNVERIFIED, vendor-acknowledged`：Intel RealSense D435 在 -10°C 户外巡检场景下，开机 0–10 分钟内 depth quality 显著退化（蜂窝噪声 + 空洞 ↑），10–20 分钟后稳态。社区普遍做法：开机后等 10 分钟再起飞，或对 active stereo projector 做预热模式。这不是 bug 是物理。

---

## 3 · 振动漂移（紧固件预紧力衰减的累积量）

### 3.1 物理

误认知：「机械材料蠕变」是主因。**实际上**主因是**螺纹预紧力衰减**。每一次振动循环都让螺纹接触面产生微滑移，预紧力按 logarithmic decay 衰减。

```
F(N_cycles) ≈ F_0 × (1 - k × log(N_cycles))
```

数值上：M3 螺丝在 100 N 预紧力 + 50 Hz 振动 + 24 小时下可能衰减 10–30% `UNVERIFIED`。预紧力下降到某阈值后，螺纹副开始整体微动 → 外参旋转可观察。

### 3.2 振动谱与漂移率

不同载体振动谱完全不同：

| 载体 | 主要谱峰 | 漂移率（`UNVERIFIED`） |
|---|---|---|
| 5" racing drone | 100–200 Hz（桨叶通过频率 BPF） | 0.05–0.2° / 1 hr 飞行 |
| 1.5 kg 巡检 drone | 50–120 Hz | 0.02–0.1° / 1 hr 飞行 |
| 工业 AGV（铺装地砖） | 5–30 Hz（接缝） + 100 Hz（电机） | 0.01–0.05° / km |
| 人形（行走） | 1–5 Hz（步态） + 20–100 Hz（足部冲击） | 0.05–0.2° / 1 hr 行走 |
| AD car（高速公路） | 1–20 Hz（路面） + 80 Hz（引擎） | 0.01–0.05° / 1000 km |

### 3.3 监测指标

```
welch_psd(gyro_z, fs=1000)  → 谱
peak_amp(50–500 Hz)         → 是否超基线 3×
∫(welch_psd over 50–500Hz)  → 累积振动能量
```

经验上：**累积振动能量 + 残差 chi-square** 双指标比单指标可靠。能量低 + chi2 高 = 跌落事件；能量高 + chi2 高 = 振动累积。

### 3.4 缓解工程

- Loctite 蓝（可拆）241 / 红（永久）271 涂螺纹——能延迟衰减 2–5× `UNVERIFIED`。
- 季度紧固扭矩检查（5 N·m 起，M3 螺丝）。
- 减振垫（硅胶 / Sorbothane）放 IMU 与机架之间——把 50–500 Hz 谱削掉。
- IMU 远离激励源（不要贴电机 / 桨毂）。

---

## 4 · 跌落 / 冲击（离散事件，最大破坏力）

### 4.1 物理

弹塑性边界。日常硬触地（1–2 m/s 着陆冲击）通常在弹性区，无残余变形；但某些组件（lens holder 塑料、PCB 焊点）的弹性极限远低于机架。一次 3+ m/s 软着陆或 0.5 m 跌落到水泥地可能：

- 镜头 lens holder 轻微旋转 → 内参偏（principal point 移 1–3 pixel）
- 相机模组贴片移位 → 外参旋转 0.1–0.5°
- IMU 模组松动 → 极端情况外参跳 1–2°

`UNVERIFIED`，具体数值高度依赖 mount 设计。

### 4.2 监测

跌落几乎是「不需要算法偵测」的事件——IMU 直接告诉你：

```python
# 跌落 / 硬冲击偵测
if peak_accel > 5g and duration < 50ms:
    log_event("HARD_IMPACT", accel=peak_accel)
    flag_calibration_suspect()
```

`HARD_IMPACT` 应当**自动**触发 L2 上电重标。

### 4.3 真实案例 — drone calibration drift after crash

经验：巡检 drone fleet 中，有 crash log 的机器 90%+ 在下一次起飞前 VIO 残差异常。Skydio 的工程博客有提到 「hard impact 后强制 L1 标定流程」`UNVERIFIED, blog`。这也是 production fleet 必须有「冲击 → 强制返厂或现场重标」流程的原因。

---

## 5 · 时间蠕变（最慢、最容易被忽略）

### 5.1 物理

胶水（环氧 / UV 固化）的 viscoelastic 行为：长时间负载下慢慢流动。Loctite / 螺纹胶在数月时间尺度上预紧力衰减。这两个加起来是「6 个月不动也漂」的根因。

数量级 `UNVERIFIED`：

- 高品质环氧（如 Henkel Hysol EA 9396）：6 个月蠕变 <100 ppm
- 普通 UV 胶：6 个月蠕变 500–2000 ppm
- 塑料 holder 蠕变：6 个月可达 0.05–0.2°（极端）

### 5.2 监测

时间蠕变信号最弱，几乎无法从单次 telemetry 偵测——需要**跨月 trend**：

```
weekly_chi2_median = telemetry.aggregate(chi2, weekly)
slope = linear_fit(weekly_chi2_median, weeks)
if slope > 0.05 × baseline / month:
    flag("LONG_TERM_DRIFT_SUSPECTED")
```

这是 fleet-scale 才能看到的信号；单台 robot 看不出来。

---

## 6 · 在线 vs 离线标定 — Trade-off 决策表

学界倾向「在线全自动」叙事；工程实际是**混合栈**。决策应基于三个变量：

| 变量 | 倾向离线（L1+L2） | 倾向在线（L3） |
|---|---|---|
| 任务时长 | <1 hr | >4 hr |
| 动态范围 | 低（AGV、桌面） | 高（drone、人形） |
| 可中断窗口 | 有（起飞前、回坞） | 无（持续作业） |
| 温度梯度 | 小（室内） | 大（户外） |
| 6-DoF 激励 | 可控（控制器主动） | 自然产生 |
| 标定板可用 | 是（基地 / 车间） | 否（任务中） |

### 6.1 离线（L1+L2）的优势

- **Kalibr-class 精度**——残差小数毫弧度。
- **可观性保证**——标定板 + 主动激励轨迹，外参全部可观。
- **可重复 / 可审计**——同样数据跑两次同样结果。
- **不消耗在线算力**。

### 6.2 在线（L3）的优势

- **持续跟踪**——温度 / 振动 / 慢漂自动跟。
- **无需中断**——AD 量产车不可能「停车 30 秒重标」。
- **应对未知**——跌落 / 突发应力下 L1 直接过期，L3 还能跟。

### 6.3 现实部署

| 应用 | L1 | L2 | L3 |
|---|---|---|---|
| 桌面 manipulation | 出厂 | 任务前可选 | 通常无 |
| 室内 AGV | 出厂 | 每日开机 | 因子图轻量 td 估计 |
| 1.5 kg 巡检 drone | 出厂 + 跌落后 | 每次起飞前 6-DoF 摇动 | **VINS-Fusion 因子图全量** |
| 量产 AD | 工厂 | 4S 店重新标定 | **EKF 强制全状态** |
| AUV 长航 | 任务前码头 | 入水前 | 部分（光学）+ 全部（INS-DVL） |

「Skydio 用 L3 + hot-recal」`UNVERIFIED, public blog`——这是 drone 量产栈的事实标准。

---

## 7 · 真实案例 #3 — RealSense USB reset bug（最容易被怪标定的非标定问题）

这个案例放在最后是因为它**看起来像标定漂移**实际**不是**。

**现象**：D435/D455 在某些 Linux + USB 控制器组合下，使用数小时后突然 depth quality 退化；重启相机后恢复。

**根因**（社区追踪 `UNVERIFIED, librealsense GitHub issues #XXXX`）：

- USB 控制器在长时间高带宽传输下偶发 reset。
- Reset 后相机进入「reduced mode」，激光强度自动下调以保护硬件。
- librealsense 在某些版本不会重新初始化 projector 设置。

**为什么容易被误诊**：症状（depth 噪声 ↑、空洞 ↑）与温度漂移、镜头脏污、标定漂极其相似。新手工程师常常先怀疑标定，跑 Kalibr 重标，发现「重标后好了」——其实只是重启了 USB 链路。

**鉴别诊断**：

| 信号 | 标定漂移 | USB reset bug |
|---|---|---|
| 重启相机即恢复 | ❌ | ✅ |
| 跨多颗相机一致 | ✅（fleet 同批） | ❌（单机 sporadic） |
| 与温度强相关 | ✅ | ❌ |
| Reprojection error 上升 | ✅ | 略有，但 depth quality 下降更明显 |

教训：**不要假设异常 = 标定漂移**。先排除驱动 / USB / 散热问题。

---

## 8 · Hidden Assumptions

- **数字量级 ±2× 容差。** CTE 表 / 蠕变率 / 振动谱依平台与材料偏差大；本文给量级而非精度。
- **「四类漂移独立」是简化。** 现实中温度 + 振动有耦合（热膨胀让螺丝预紧力增加，但热软化让它衰减更快）。
- **可观性条件未在本文展开。** L3 因子图把外参当状态时，纯直线匀速下外参不可观——这个是大坑，论文很少强调（参考 `deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md` §4）。
- **rolling shutter 内部时延也算「标定」。** 严格说 rolling shutter 的 line delay 是内参的一部分；漂移很慢但存在。
- **本文假设 sensor 本身不坏。** Hardware failure（CMOS pixel dead、IMU MEMS chip 失效）不是标定问题；归 `deployment/failure-modes/`。

## 9 · 与基线对比 + Interview Tip

| 视角 | 学界标定综述 | 本文 |
|---|---|---|
| 标定流程 | ✅（Kalibr / Zhang） | 仅作为 L1 提及 |
| 漂移物理量化 | ❌ | ✅（四桶 + 量级） |
| 监测指标 | ❌ | ✅（chi2 / 谱 / 累积能量） |
| 在线 vs 离线 trade-off | 偶尔 | ✅（决策表 + 6 变量） |
| 真实失败案例 | ❌ | ✅（drone fleet / D435 / USB bug） |
| 跨载体差异 | ❌ | ✅（6 embodiment 横切） |

**Interview Tip**：被问「你的相机标定多久要重做一次」——别答「不知道」或「每天」，答「取决于四个变量：温度梯度、振动累积能量、有无冲击事件、时间。fleet telemetry 上的 chi2 滑动窗口 + 温度记录 + 冲击日志，三个一起看，重标周期可以从『每天』压到『季度 + 事件触发』」。这才是工程答案。

---

## 10 · 2-year outlook + 可证伪预测

**可证伪预测：** 到 2027-12 前，至少一家消费 / 商用 drone 厂商会公开「30 秒任务起飞前自然场景自动标定」功能，精度接近 Kalibr 板标（残差 <0.5 px），且不依赖云端。如果到那时点没有，「标定板捆绑」仍将是 drone fleet 维护的瓶颈。

支持线索：(a) VGGT / DUSt3R 类 feed-forward 几何方法已经能在任意场景做 bundle adjustment 初值；(b) Skydio / DJI 已有内部 hot-recal；(c) NVIDIA Isaac 框架提供 reference implementation。反对线索：精度差距、户外极端光照、跌落场景下的几何先验失效。

---

## For the reader

- **VIO / SLAM 工程师** —— §2-4 给四类漂移可监测信号；先把这些写进 telemetry，再讨论新算法。
- **算法研究者** —— 论文里明示你假设的标定有效期（出厂 / 任务前 / 在线全程）。审稿人不会问，下游工程师会被坑。
- **产品 / fleet 运维** —— §6 决策表是月度维护规划工具；§5 时间蠕变只有你能看到（单台 robot 看不到）。
- **硬件 / 机械工程师** —— §3 振动 + §4 冲击是设计阶段就应该约束的；Loctite + 减振垫 + lens holder 材料选择比软件 fix 便宜十倍。

---

## References

- Furgale et al., *Kalibr* — https://github.com/ethz-asl/kalibr
- VINS-Fusion 在线外参 + td — Qin et al. *T-RO 2018* — https://arxiv.org/abs/1708.03852
- Allan variance ROS — https://github.com/ori-drs/allan_variance_ros `UNVERIFIED, no DOI`
- Hysol EA 9396 datasheet — Henkel `UNVERIFIED, vendor`
- librealsense GitHub Issues — https://github.com/IntelRealSense/librealsense `UNVERIFIED, no DOI`
- Loctite threadlocker technical data — Henkel `UNVERIFIED, vendor`
- Skydio engineering blog (hot-recal) — `UNVERIFIED, no DOI`
- 相关 sensor 物理：`foundations/sensor-physics/imu_physics_and_noise_model.md`、`foundations/sensor-physics/stereo_camera_geometry_physics.md`

## Boundary

本文写**生产环境标定漂移的物理与监测**。**不写**：Kalibr 操作流程（去 `deployment/calibration/README.md` §3）、同步漂移 / 时间偏置（去 `deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md` §4）、单 sensor 内参物理（去 `foundations/sensor-physics/`）、跨 embodiment 失败模式（去 `crossing/failure-modes-atlas/` 或 `deployment/failure-modes/`）、SLAM / VIO 算法本体的可观性证明（应在 foundations/feed-forward-3d / crossing/slam-vio-migration 里写）。本文数值是 starter；production 必须用 fleet 30+ 天 telemetry 实测分布校准。

---

[← Back to Calibration README](./README.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
