# Sensor 静默失败模式 / Sensor Silent Failure Patterns

> **发布时间**：2026-05-21
> **适用范围**：所有装多 sensor 的 embodiment——drone / AGV / AD / manipulation / humanoid / marine
> **核心定位**：和 `field_failures_taxonomy.md` 互补——那篇写「robot 明显崩了」的 8 类；本文写「robot 看起来还在工作但数据已经偷偷错了」的静默失败。这类失败最难偵测、损害最大、事后最难定位。

**Status:** v1 — opinionated draft。OOD 阈值 / 漂移率 / 检测延迟均 `UNVERIFIED`，需以 fleet telemetry 实测分布校准。
**Wedge tier:** N/A（deployment ops runbook 风格，配套 `field_failures_taxonomy.md`）
**TL;DR:** 「明崩」八类失败（camera shift、振动、逆光、反射、透明、雨雪、粉尘、水下）总有显式信号；本文写的「**暗崩**」六类（GPS spoofing/multipath、IMU bias creep、Camera AE 偷换、Depth model OOD silent、时钟漂移、Sensor 半死）则在 telemetry 上看起来全绿，但 SLAM / 控制 / planner 实际已被毒化。本文给「五层 watchdog 架构」+ 六类暗崩各自的偵测 / 缓解 runbook，并强调**冗余 sensor + 跨 sensor consistency check** 是唯一可靠的兜底。

### X-Ray 开场（非专家友好）

(a) 静默失败 = sensor 读数还在「合法范围」但实际已错了——比如 GPS 在城市峡谷里读 ±5 m 不报告。(b) 这类失败比硬故障更危险：robot 自信地走错路、controller 收到错的位置反馈做错的控制、planner 在错的地图上规划。(c) 对系统 / 安全工程师：本文是「不能信任单一 sensor」的具体工程实现——多 sensor 冗余 + cross-check 是唯一通用解。

### 📍 研究全景时间线

```
2009 ── Schlumberger 工业仪表 silent failure detection — Industrial PHM 起源
2015 ── 民航 ADIRU 事件 (Qantas 72) — IMU 静默故障导致民航大事故，工业认识到 silent failure 致命性
2017 ── Tesla AP 第一波白色卡车撞击 — 视觉 confidence 高但语义错的典型案例
2020 ── Waymo 公开「冗余 sensor + cross-check」架构 — AD 量产标准
2022 ── OOD detection 大潮（CLIP-based, energy-based）— 视觉 silent OOD 量产化偵测
2024 ── Foundation VLM 作为 sanity check — 「这看起来对吗」语义验证
        ── 你在这里 (2026) ──
?    ── Federated drift detection across fleet — 单机看不到的慢漂在 fleet 上跑统计
?    ── 神经符号一致性 check — 神经预测 + 符号推断双轨
```

`field_failures_taxonomy.md` 写「明崩」8 类（每类有显式物理触发）；本文写「暗崩」6 类（信号弱、容易被信任）。两篇构成完整的 fleet ops runbook。

---

## 1 · 「明崩 vs 暗崩」的分类

📌 **Napkin Formula**：

```
明崩 = sensor 读数在合法范围之外 OR 缺失
       (NaN / 突变 / 超阈值)
暗崩 = sensor 读数在合法范围之内 但与「物理真值」差距大
       (慢漂、bias creep、合法但错的语义)
```

| 维度 | 明崩 | 暗崩 |
|---|---|---|
| 单 sensor 自检 | ✅ 有效 | ❌ 无效 |
| 偵测难度 | 🟢 易 | 🔴 难 |
| 后果显式 | ✅（SLAM 失锁 / 急停） | ❌（默默走偏） |
| 偵测手段 | 范围检查 / NaN | 跨 sensor consistency / OOD score / Watchdog |
| 真实事故占比 `UNVERIFIED` | 部署 1 年内多 | 长期运维多 |

---

## 2 · 六类暗崩速览

| # | 暗崩类型 | 物理本质 | 受害组件 | 重灾 embodiment |
|---|---|---|---|---|
| 1 | GPS spoofing / multipath / urban canyon | 卫星信号被遮挡或干扰 | 全局位置、time | drone outdoor, AD city, marine |
| 2 | IMU bias creep | gyro / accel 慢漂 | VIO 位姿、控制 | drone long-flight, AUV |
| 3 | Camera AE swap | 自动曝光改 ISO/gain 改 sensor 响应 | 视觉特征、photometric prior | 所有视觉系统 |
| 4 | Depth model OOD silent | 模型在域外仍输出 confident depth | 避障、规划 | 所有用 learning depth 的 |
| 5 | Time / clock drift（非时间同步问题） | 主时钟自身漂或跳 | 多 sensor 融合、log 时间 | drone, AD |
| 6 | Sensor 半死（partial failure） | 一颗像素阵列部分坏 / 一颗激光头哑 | LiDAR、stereo、IMU | 老化 fleet |

---

## 3 · Failure #1 — GPS spoofing / multipath / urban canyon

### 3.1 物理

GNSS 接收机解 4 颗以上卫星的 pseudo-range 得到 3D 位置。三类问题：

- **Multipath（多径）**：信号经建筑反射后到达，pseudo-range 变长 → 位置偏。城市峡谷常见。
- **Urban canyon obstruction**：可见卫星数掉到 4 颗以下，几何 DOP（GDOP）变差 → 精度从 m 级掉到 10+ m。
- **Spoofing**：恶意发射假 GPS 信号；近年商业可购买 spoofing 设备。Iran 拦截 RQ-170 一例 `UNVERIFIED`。

**关键问题**：GNSS 接收机自己**不知道** multipath / spoofing；输出依然给「fix」状态。

### 3.2 症状

- 看起来稳态：经度 / 纬度数字稳定，HDOP 「合理」。
- 与 VIO / 里程计差异系统性偏移（不是高斯噪声）。
- 走到建筑遮挡 / 桥下后 5–30 m 系统偏。

### 3.3 偵测

**单 GNSS 不可能偵测**。必须跨 sensor：

```python
# GPS-VIO 一致性 watchdog
delta = gps_pos - vio_pos
slope = linear_regression(delta, last_60s)
if abs(slope) > 0.5 m/s sustained:
    flag("GPS_VIO_INCONSISTENT")
if gps.num_satellites < 5 or gps.hdop > 5:
    flag("GPS_GEOMETRY_DEGRADED")
```

最强信号：**多构型 RTK + IMU 紧耦合**——RTK 失锁是 multipath 的强 prior。

### 3.4 缓解

- AD：默认 GPS 仅作 prior，主导航靠 lane / HD map / SLAM；GPS 与地图不一致时 lane 主导。
- Drone：urban canyon 主动切「视觉 + IMU」模式；脱离峡谷后才信 GPS。
- 商业 anti-spoofing：multi-constellation（GPS + Galileo + BeiDou）+ multi-frequency（L1+L2+L5）+ RTK 校验。
- 极端：CRPA（受控辐射方向天线）+ IMU 紧耦合，军用级。

### 3.5 真实案例

`UNVERIFIED`，新闻广泛报道：黑海多艘船 GPS 同时偏到「机场」位置——大规模 spoofing。Ukraine 战场 drone 普遍上 inertial-only 模式因 GPS 干扰。Tesla / Waymo / Cruise 都使用 HD map 作为 GPS 不可信时的兜底。

---

## 4 · Failure #2 — IMU bias creep（最隐蔽的 VIO 杀手）

### 4.1 物理

MEMS IMU 的 bias instability `~0.05–0.5°/s` (gyro) 和 `~10–50 µg` (accel)，根据 Allan 方差曲线（`foundations/sensor-physics/imu_physics_and_noise_model.md`）。即使温补 + 工厂标定，**bias 在使用中会慢漂**：

- 温度变化（30 °C ΔT 内 bias 漂 0.1–1°/s `UNVERIFIED`）
- 长时使用（电池电压 / 温度共振漂）
- 老化（年级别）

VIO / VINS 把 bias 作为状态联合估计——理论上能跟。但**纯直线匀速**或**单轴旋转**下 bias 与位姿耦合不可观，估错。

### 4.2 症状

- 位姿在长期飞行下漂米级（drone 30 分钟飞行常见 1–5 m 漂）。
- VIO 残差看起来「合理」（chi2 在范围内）但「位置 ground truth」对不上。
- 闭环触发频率上升。

### 4.3 偵测

```python
# 静态时 gyro bias 应该为零
if is_static(window=5s):
    gyro_mean = mean(gyro, window=5s)
    if abs(gyro_mean) > 0.1 deg/s:
        log("GYRO_BIAS_DRIFT_DETECTED", value=gyro_mean)
        update_calibration(gyro_bias=gyro_mean)
```

「**起飞前 / 起步前 5 秒静止偵测**」是 drone / AGV 的标准做法。Skydio / DJI 都有这个流程`UNVERIFIED`。

### 4.4 缓解

- **静态校准**：每次起飞前 5 秒静止重估 bias。
- **温度补偿表**：fleet 阶段 IMU 进恒温箱测每个温度的 bias，存表。
- **冗余 IMU**：2–3 颗 IMU 加权投票（参考 `foundations/sensor-physics/imu_physics_and_noise_model.md`）。
- **FOG IMU**：成本 1000× 但 bias instability 也 1000× 小；AUV / 长航必备。
- **VIO 强观测**：保证有持续 6-DoF 激励让 bias 可观。

### 4.5 真实案例

`UNVERIFIED, 民航事故公开调查`：Qantas 72 (2008) — ADIRU IMU 在飞行中静默故障注入错误加速度数据，autopilot 紧急下俯，多人受伤。航空界把「IMU 冗余 + cross-check」做成强制要求。Robotics 圈通常没这么严，但经验上的「VIO 30 分钟后漂米级」常常是 bias creep。

---

## 5 · Failure #3 — Camera AE 偷换（photometric prior 被毁）

### 5.1 物理

自动曝光（AE）/ 自动增益（AGC）在场景亮度变化时动态调整 ISO / shutter / gain。多数 SLAM / VIO 假设：

- **gray-level constancy**：连续帧的 photometric error 是 noise，不是 ISO 跳变。
- **稳定特征**：ORB / FAST features 在曝光变化下数量 / 分布稳定。

但 AE 在「云遮太阳」「进出隧道」「卷帘门开关」等场景下可以**单帧之间 ISO 跳 4×**：

- Photometric error 从 0.5 lux 跳到 10 lux → DSO / direct SLAM 直接发散。
- ORB 提取数量从 500 掉到 50 → 跟踪失败。
- HDR sensor 切 LDR-mode → 内参隐含变化。

### 5.2 症状

- 进出隧道瞬间 VIO 残差跳 10×。
- 阳光直射切阴影时 feature lock-loss。
- 「我场景看起来一样啊」但相机 metadata 显示 ISO 从 100 跳到 800。

### 5.3 偵测

```python
exposure_log = camera.metadata.exposure_us
gain_log = camera.metadata.iso
if abs(exposure_log[t] - exposure_log[t-1]) / exposure_log[t-1] > 0.5:
    log("EXPOSURE_JUMP", ratio=ratio)
    # 通知 VIO「下一帧 photometric error 不要信」
    vio.skip_photometric_residual(t)
```

更严格：**固定曝光 / 手动 AE**——drone / 一些 AD 栈直接关 AE 用固定参数，损失动态范围但 SLAM 稳。

### 5.4 缓解

- VIO / SLAM 启用 photometric calibration（DSO 那一支） + AE 实时读取作为权重。
- ORB / 几何 feature 一支：AE 跳变后重新初始化 tracker。
- HDR sensor 主动用（Sony IMX 汽车款 130+ dB），减小 AE 跳幅度。
- AE 锁定（manual exposure）：drone 起飞前测光后锁定，飞行中不动。

### 5.5 真实案例

`UNVERIFIED, blog / paper anecdote`：早期 RealSense VIO 在仓库卷帘门开启的瞬间普遍漂 1–3 m，根因 AE 在 0.5 秒内 ISO 跳 8×，VIO photometric assumption 破裂。后续 librealsense 默认推荐手动曝光给 VIO 用。

---

## 6 · Failure #4 — Depth model OOD silent（最像「正常」的失败）

### 6.1 物理

学习深度模型（Depth Anything / MiDaS / VGGT）在域外（OOD）输入下**仍输出 confident 结果**——这是 deep learning 的通病。具体到深度估计：

- 透明物体：模型预测背景深度，confidence 高。
- 镜面反射：预测镜子后面的虚像深度。
- 极端光照：饱和区域填「合理」深度。
- 训练域外的 sensor（domain shift）：整体偏 10–30%。

### 6.2 症状

- 输出 depth map 看起来「合理」（无 NaN / 无大空洞）。
- 但具体表面距离 ground truth 偏 10–50%。
- 抓取 / 避障决策错。

### 6.3 偵测

```python
# 主要 + 备用 + 一致性 check
depth_learning = depth_model(rgb)
depth_stereo = stereo_match(left, right)  # 经典方法
disagree_ratio = (abs(depth_learning - depth_stereo) > 0.2 * depth_stereo).mean()
if disagree_ratio > 0.3:
    log("DEPTH_MODEL_OOD_SUSPECTED")
    fallback_to(depth_stereo)
```

**冗余 + 一致性 check** 是几乎唯一可靠的偵测；模型自己的 confidence 不可信。

「VLM as validator」`UNVERIFIED, 2025+ 研究`：把 RGB + depth map 交给 VLM 问「这看起来对吗」——慢但语义层面有效。

### 6.4 缓解

- **永远不要单独信学习深度**。配 stereo / LiDAR / 几何 prior 做冗余。
- **训练数据加 OOD**：把 transparent / 反射 / 极端光照场景加入训练集。
- **温度 scaling + ensembling**：多模型投票。
- **保守模式 fallback**：disagree 高时切几何方法 + 降速。

### 6.5 真实案例

`UNVERIFIED, 维护经验`：仓储 AGV 在透明玻璃门前 Depth Anything V2 small 自信地输出 5 m 深度（实际是玻璃门后的走廊），AGV 撞门。Fix：stereo + RGBD 主导，learning depth 仅作 prior 增强。

更经典：Tesla AP 第一波白色卡车撞击——视觉 confidence 高但语义错。这虽然是 detection 不是 depth，但本质同——学习模型在 OOD 下静默错。

---

## 7 · Failure #5 — 时钟漂 / 跳变

### 7.1 物理

非同步意义上的时间问题——本机时钟自身漂或跳。这跟 `deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md` 的同步问题不同；那篇讲「sensor 间对齐」，本节讲「主时钟本身错」：

- **NTP / chrony 跳变**：上电后 NTP 同步可能让系统时钟跳几秒。
- **CLOCK_REALTIME vs CLOCK_MONOTONIC**：用错 clock；夏令时 / 时区切换跳。
- **晶振漂移**：消费 SoC 晶振 ±50 ppm，1 小时漂 180 ms。
- **PTP grandmaster 失锁**：网络 PTP 主时钟离线，下游开始自由漂。

### 7.2 症状

- 多 sensor 融合突然出现「未来时间戳」（违反因果）。
- Log 文件时间戳乱跳。
- 重启后系统行为不一致。

### 7.3 偵测

```python
# 时钟一致性检查
if abs(CLOCK_REALTIME - last_known) > 1.0 sec  and not boot_phase:
    flag("CLOCK_JUMP_DETECTED")
# 避免依赖 CLOCK_REALTIME 做相对时间
ts = clock_gettime(CLOCK_MONOTONIC)  # 推荐
```

### 7.4 缓解

- **永远用 CLOCK_MONOTONIC** 做相对时间；CLOCK_REALTIME 只用于人类可读 log。
- **禁用 NTP 自动跳变**：用 chrony slewing 模式（连续调而非阶跃）。
- **PTP grandmaster 冗余**：双主时钟 + 自动 failover。
- **时间一致性 watchdog**：跨进程比对时间戳。

---

## 8 · Failure #6 — Sensor 半死（partial failure）

### 8.1 物理

不是「sensor 完全坏」，而是「部分功能退化」：

- LiDAR 一个 channel（line）哑——24 线 LiDAR 变 23 线，点云密度局部下降。
- Stereo 一颗相机的 lens holder 松动，部分像素失焦。
- IMU 三轴中一轴 bias 极端值（>5σ），另两轴正常。
- RGB 相机的 column 噪声（CMOS 缺陷）——某些列像素值固定 / 噪声大。

### 8.2 症状

- 整体看 sensor「在工作」（有数据流出）。
- 局部统计指标异常：某 line 缺、某 column 噪、某轴 bias。
- 下游模型 / SLAM 可能继续跑，但某些场景下错。

### 8.3 偵测

```python
# LiDAR per-channel 健康
for ch in range(num_channels):
    points_per_ch = count_points(ch, last_10s)
    if points_per_ch < 0.5 * baseline[ch]:
        log("LIDAR_CHANNEL_DEGRADED", channel=ch)

# Camera column / row 噪声
col_std = column_wise_std(image)
if col_std.max() > 3 * col_std.median():
    log("CAMERA_BAD_COLUMN_SUSPECTED")

# IMU per-axis bias
for axis in ['x', 'y', 'z']:
    if abs(static_mean[axis]) > 5 * historical_std[axis]:
        log("IMU_AXIS_BIAS_OUTLIER", axis=axis)
```

### 8.4 缓解

- 偵测到半死立即报警 + 计划维护。
- LiDAR：哑 channel 在感知模型里 mask 掉。
- Stereo：检查是否退化到 mono 模式。
- IMU：跨冗余 IMU 投票，剔除异常轴。

---

## 9 · 五层 Watchdog 架构

把六类暗崩偵测组织成五层 watchdog——单一指标永远会被骗，多层投票才稳：

```
Layer 1 — Range / NaN check
    各 sensor 数据是否在 spec 范围内、是否非 NaN
    成本：低；偵测：明崩；漏：暗崩

Layer 2 — Per-sensor statistical sanity
    单 sensor 的统计指标（mean / std / histogram）是否在历史分布内
    成本：低；偵测：bias creep / column 噪声 / 部分半死

Layer 3 — Cross-sensor consistency
    GPS vs VIO、stereo vs learning depth、IMU vs wheel encoder
    成本：中；偵测：spoofing / OOD / 慢漂

Layer 4 — Temporal trend
    跨小时 / 跨天的指标趋势（chi2 滑动窗口、漂移率）
    成本：低 + 需要 telemetry 基建；偵测：温度蠕变 / 长时漂移

Layer 5 — Semantic / VLM validation
    「VLM 这看起来合理吗？」「场景 prior 是否与感知一致？」
    成本：高；偵测：剩余 OOD / 训练域外语义
```

每一层独立；高层不依赖低层正确。**层次冗余 + 跨层投票** = production-grade safety net。

| Layer | 频率 | 算力开销 | 偵测延迟 |
|---|---|---|---|
| L1 | 每帧 | 微 | <1 ms |
| L2 | 1 Hz | 微 | 1–10 s |
| L3 | 10 Hz | 中 | 0.1–1 s |
| L4 | 1/min | 微 + 数据库 | 分钟 |
| L5 | 0.1 Hz | 高（VLM） | 10 s+ |

---

## 10 · 冗余 sensor 的工程账

「单 sensor 不可信，冗余兜底」是结论；但**怎么冗余**是另一个问题。

### 10.1 冗余度选择

| 类型 | 例 | 偵测能力 | 成本 |
|---|---|---|---|
| 同构冗余 | 2× IMU | 偵测单 sensor 半死 | 1× sensor |
| 异构冗余 | IMU + wheel encoder + GPS | 偵测物理建模错 / spoofing | 多种 sensor |
| 算法冗余 | learning depth + stereo + LiDAR | 偵测算法 OOD | 算力 / 重量 |
| 语义冗余 | VLM validator | 偵测语义错 | 慢 + 贵 |

经验：**异构冗余 > 同构冗余 > 算法冗余 > 语义冗余**（按可靠性 / 成本比）。AD 量产用前三种全部；drone 因 SWaP 限制常只用前两种。

### 10.2 投票 vs 主备

| 模式 | 适用 | 优点 | 缺点 |
|---|---|---|---|
| 三模冗余多数投票（TMR） | 飞控 / 关键 sensor | 容错 1 个 | 3× 成本 |
| 主备切换 | 多数场景 | 2× 成本 | 切换瞬态 |
| 加权融合 | VIO / 状态估计 | 平滑 | 不偵测单 sensor 错 |

### 10.3 冗余设计的常见坑

- **共因失败**：两颗 IMU 同型号、同批次 → 同样的固件 bug 同时触发。Fix：跨厂商 / 跨型号。
- **冗余太对称**：两个传感器都是 850 nm RGBD → 太阳下都崩。Fix：异构（如 stereo + active）。
- **投票算法本身**：投票阈值错会把冗余变成单点故障。
- **「沉默冗余」**：备用 sensor 上电几年没用过，真要切到时已经坏。Fix：周期性自检。

---

## 11 · Hidden Assumptions

- **「六类暗崩」不闭包**。还有：网络丢包、缓冲区溢出、固件 bug、电源噪声、电磁干扰——本文不展开。
- **「五层 watchdog」是参考架构，不是金标**。具体投票阈值、报警策略必须 fleet telemetry 校准。
- **冗余 sensor 不解决系统性偏差**。所有 sensor 用同一 calibration framework 出错时，冗余全错。
- **VLM validator 自身可能错**。VLM 是「另一种 sensor」，也会 OOD。
- **数字 `UNVERIFIED`**：所有阈值、漂移率、检测延迟均需要平台实测；本文给的是量级与方法论。

## 12 · 与基线对比 + Interview Tip

| 视角 | 学界论文 | `field_failures_taxonomy.md` | 本文 |
|---|---|---|---|
| 失败定义 | 「metric 下降」 | 「fleet alarm」 | 「悄悄走偏」 |
| 偵测策略 | 单 sensor confidence | 多偵测器投票 | 五层 watchdog + 跨 sensor cross-check |
| 冗余设计 | 不涉及 | 偶尔提 | 必谈（§10） |
| 真实失败例 | 不涉及 | 8 类 | 6 类（含 Qantas 72、Tesla AP） |
| 主要受众 | 学界 | 部署运维 | 安全 + 系统 + fleet |

**Interview Tip**：被问「你怎么知道你的 robot 没在偷偷错」——别答「我们有 SOTA OOD detector」，答「我有五层 watchdog：L1 range / NaN、L2 per-sensor stat、L3 跨 sensor consistency、L4 temporal trend、L5 VLM validator。每层独立 + 跨层投票。冗余是异构 + 跨厂商，不是简单复用同型号」。这是 production safety mindset。

---

## 13 · 2-year outlook + 可证伪预测

**可证伪预测：** 到 2027-12 前，至少一篇 published 工作或开源框架会提供 **「fleet-wide federated silent failure detection」**——单台 robot 看不到的慢漂在 100+ 台 fleet 上跑统计偵测，开源标准 OOD score 框架。如果到那时点没有，silent failure 偵测仍将依赖每家 OEM 自研内部工具。

支持线索：(a) Waymo / Cruise / Tesla 已内部跑 fleet-wide 异常偵测；(b) federated learning 框架成熟；(c) foundation model 提供共通「sanity check」基线。反对线索：商业 fleet 数据私有性、各 OEM 不愿开源核心 safety 栈。

---

## For the reader

- **安全 / 系统工程师** —— §9 五层 watchdog + §10 冗余设计是核心；先把跨 sensor consistency check 跑起来再谈复杂 OOD detector。
- **VIO / SLAM 工程师** —— §3-4 GPS/IMU 暗崩最容易被误诊为「算法不行」；先排除。
- **算法研究者** —— 论文里多说一句「输入分布漂移时输出会如何」。
- **fleet 运维 / 产品** —— §10.3 冗余设计坑几乎所有 fleet 都踩过；周期性自检比新 sensor 重要。
- **manipulation engineer** —— Depth model OOD silent（§6）是 grasping 失败最常见的隐藏根因。

---

## References

- Allan Variance ROS — https://github.com/ori-drs/allan_variance_ros `UNVERIFIED`
- VINS-Fusion online bias — Qin et al. *T-RO 2018* https://arxiv.org/abs/1708.03852
- DSO photometric calibration — Engel et al. *PAMI 2017* https://arxiv.org/abs/1607.02565
- Depth Anything V2 — Yang et al. 2024 https://arxiv.org/abs/2406.09414
- Qantas 72 ADIRU incident — ATSB Investigation Report `UNVERIFIED`
- OOD detection survey — Yang et al. 2024 https://arxiv.org/abs/2110.11334
- 相关本仓：`foundations/sensor-physics/{imu,stereo,gnss}_*`、`deployment/calibration/sensor_calibration_drift_in_production.md`、`deployment/failure-modes/field_failures_taxonomy.md`、`crossing/failure-modes-atlas/`

## Boundary

本文写**sensor 静默失败**——「看起来对但偷偷错」的偵测、缓解、冗余设计。**不写**：明显的物理失败（去 `field_failures_taxonomy.md`，8 类 ops runbook），跨 embodiment 失败模式的物理对比（去 `crossing/failure-modes-atlas/`），单 sensor 物理建模（去 `foundations/sensor-physics/`），SLAM / VIO 算法的 corner case（去算法 dissection），功能安全 / ISO 26262 / DO-178C（另一份专门文档）。本文阈值 `UNVERIFIED`；production 必须用 fleet 30+ 天 telemetry 实测分布 + 真实事故复盘校准。

---

[← Back to Failure Modes README](./overview.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
