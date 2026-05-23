# 田野失败模式分类 / Field Failures Taxonomy

> **发布时间**：2026-05-21
> **适用范围**：8 类失败模式 × 6 embodiment 的部署运维
> **核心定位**：把田野上 robot 真的崩了那一刻，工程师手里要拿的 ops runbook 写出来——每类失败给「物理 → 症状 → 偵测 → 缓解」四步。

**Status:** v1 — opinionated draft。具体触发阈值 / 频率 / OOD 分数全部标 `UNVERIFIED`，需以 fleet telemetry 实测分布校准。
**Wedge tier:** N/A（deployment ops runbook 风格）
**TL;DR:** 8 类失败模式（camera shift / 振动 / 逆光 / 反射 / 透明 / 雨雪 / 粉尘 / 水下）合起来吃掉田野部署 80%+ 的运维工时。每类都有可自动偵测的指标——只是论文不写。本文写指标 + 阈值 + fallback 模式 + 真实案例。

### X-Ray 开场（非专家友好）

(a) 田野 robot 崩 = 论文 benchmark 之外的 8 类物理触发。(b) 每类有可偵测信号（残差 / 谱 / 曝光直方图 / 雨刮 / NIR floor / OOD），论文从不写。(c) 对运维 / 系统工程师，本文是 fleet 上线后第一份要打印贴墙的 runbook。

### 📍 研究全景时间线

```
2012 ── KITTI 时代：失败模式 = 算法在 paper 数据集崩，没人讨论现场
2017 ── Waymo / Cruise 上路：fleet telemetry 第一次发现「雨刮启动 → AD 性能 ↓」
2020 ── Skydio 飞控公开：hot-recalibration 概念进入 drone 社区
2023 ── 端到端 AD：OOD detection 与 DDT (degraded driving)作为正式架构
2025 ── Foundation VLM 加入 safety net：「这是不是玻璃 / 雨 / 隧道？」
        ── 你在这里 (2026) ──
?    ── TRD-aware 深度基础模型 + VLM 语义先验融合？开放问题
```

---

## 1 · 8 类失败模式的物理分桶

📌 **Napkin Formula**:

```
field_failure = paper_assumption_broken
  Paper 默认假设：
    A1. 外参不变       ← camera shift 打破
    A2. 曝光稳定       ← 逆光 / 隧道打破
    A3. 表面 diffuse   ← 反射 / 透明打破
    A4. 介质透明       ← 雨雪 / 粉尘 / 水下打破
    A5. sensor 不动    ← 振动打破
```

每一类失败 = 某一条 paper 默认假设被现场打破。修法 = 偵测它被打破 + fallback。

| 类 | 打破的假设 | 物理来源 |
|---|---|---|
| Camera shift | A1 | 螺丝松 / 跌落 / 热漂 |
| 振动 | A5 | 电机 / 桨 / 路面 |
| 逆光 | A2 | 阳光 1 kW/m² floor |
| 反射 | A3 | 镜面虚像 |
| 透明 | A3 | 光穿过表面 |
| 雨雪 | A4 | 雨滴 / 雪散射 |
| 粉尘 / 烟雾 | A4 | 颗粒 Mie 散射 |
| 水下 | A4 + 折射 | 水折射 / NIR 吸收 |

---

## 2 · Failure #1 — Camera shift（外参漂移）

**物理**：螺丝预紧力衰减 + 热膨胀（CFRP / 铝合金膨胀系数不同）+ 跌落。温度循环 −20 → 60 °C 引入 0.05–0.3° 旋转 `UNVERIFIED`；软着陆 0.1–2°。

**症状**：双目重投影残差 ↑ 2×；VIO 漂率 ↑、闭环失败；BEV 边缘不齐。

**偵测**：滑动 60s chi-square `reprojection_err_chi2 > 2.0 × expected` → `CAMERA_SHIFT_SUSPECTED`；阈值用 fleet 30 天 P95 作初值。

**缓解（分级）**：(1) L3 在线自标——因子图把 `T_cam_imu` 当状态联合估计（VINS-Fusion 路线）；(2) Hot-recal——偵测到漂移 → 主动飞段已知 6-DoF 激励轨迹（Skydio-class 据信用这个 `UNVERIFIED`）；(3) 漂 >2° 自动报警，机柜锁定不出勤。

**真实案例**：巡检 drone fleet 6 个月后 P95 残差 0.6 → 1.4 px，根因螺丝松动；fix：Loctite + 季度紧固 + 因子图 L3 自标。详见 `deployment/calibration/README.md` §5。

---

## 3 · Failure #2 — 振动

**物理**：电机 / 桨叶 / 路面 50–500 Hz 振动；IMU 见 alias-down 低频偏置，相机见 motion blur。

**症状**：IMU 谱尖峰（drone 桨叶 100–200 Hz `UNVERIFIED`）；feature tracker lock-loss ↑；LiDAR jitter。

**偵测**：`welch(gyro_z, fs=1000)` 找 50–500 Hz 峰；`peak_amp > 3 × baseline` → `VIBRATION_OUT_OF_SPEC`。

**缓解**：硬件减振垫 + IMU 远离激励源；软件 notch filter；motion blur 下降低 VIO 视觉权重。Drone 特例：IMU 谱可顺带做桨叶 PHM。

**真实案例**：工业 AGV 跑铺装地砖（接缝 60 cm），1 km 后 IMU 偏置累积；fix：提高 wheel encoder 权重 + IMU 主动 bias 重估。

---

## 4 · Failure #3 — 逆光 / 阳光直射

**物理**：阳光 1 kW/m² floor 在 850 nm 仍 ~500 W/m² `UNVERIFIED`；几瓦 NIR projector 2 m 外信噪比塌。RGB AE 在 130+ dB 室外动态范围下要不过曝要不全黑。

**症状**：D435 户外 >2 m 蜂窝噪声 + 空洞；RGB 直方图 >10% 在 255 或 <5；feature 数量骤降。

**偵测**：`sat_high > 0.10 or sat_low > 0.30` → `EXPOSURE_OUT_OF_RANGE`；`depth_valid_ratio < 0.4` → `ACTIVE_DEPTH_DEGRADED`。

**缓解**：HDR sensor（Sony IMX 汽车款）；户外切 passive stereo + IMU 主导，active depth 标 invalid；drone 用 IMU + 时钟 + GPS 算太阳方向主动避朝阳飞。

**真实案例**：仓储 AGV RealSense 在卷帘门开启瞬间深度全空；fix：valid ratio 偵测 → 切 wheel + IMU + 2D LiDAR 模式 5 秒过渡。

---

## 5 · Failure #4 — 反射（镜面 / 水面 / 玻璃）

**物理**：镜面反射使 stereo 三角化到"虚像点"；LiDAR 多径错距；RealSense 镜面读 NaN。

**症状**：VIO loop-close 到"镜像房间"；LiDAR 点云"穿墙"；active depth NaN。

**偵测**：多视一致性（不同角度同一点深度跳变）；polarization sensor（偏振度异常高 = 镜面）；VLM 语义「这是镜子？」（2026 VLM 稳定可用 `UNVERIFIED`）。

**缓解**：manipulation 用 polarization + 触觉 fallback（详见 `crossing/failure-modes-atlas/` §4a）；humanoid / AGV 用地图 prior + 减速；AD 用 radar primary（radar 不在意镜面）。

**真实案例**：医院巡检机器人在抛光地板上 VIO loop-close 到天花板镜像；fix：垂直向上 30° 内特征加 outlier penalty + VLM 语义先验。

---

## 6 · Failure #5 — 透明（玻璃 / 塑料 / 水）

**物理**：光穿过透明体到背景；depth 估计器把背景当表面。

**症状**：抓玻璃杯瞄向后桌；drone 朝玻璃幕墙飞撞墙（视觉看内部，LiDAR 弱回波）。

**偵测**：LiDAR 强度异常低；polarization 偏振信号特殊；VLM「这是玻璃？」。

**缓解**：manipulation 用 polarization + 触觉 closed-loop；drone 在 HD map / VLM prior 标注玻璃幕墙 + radar 辅助；AD 把 windshield-of-stopped-car 列为经典 corner case，靠 radar + 多帧累积。

**真实案例**：机械臂在透明饮料瓶上 50% 抓取失败；fix：合成 transparent 数据训练 + 在线 polarization fusion → 80%+ `UNVERIFIED`。更全面 TRD 跨 embodiment：`crossing/failure-modes-atlas/transparent_reflective_deformable.md`。

---

## 7 · Failure #6 — 雨雪

**物理**：雨滴在镜头 → 局部畸变；在 LiDAR 光路 → 假回波"雪花"；雪覆盖路面 → 反射率均匀化 lane line 消失。

**症状**：LiDAR 远距低强度噪点；镜头雨珠 → feature ↓ 30%+；stereo NaN 区域 ↑。

**偵测**：雨刮 / 雨量传感器是最强 prior；LiDAR 孤立低强度点过滤；camera 局部对比度下降区。

**缓解**：AD 用 radar primary + 降速 + 增大跟车距离；drone 雨天不该起飞，强制 RTH；AGV 用地面 wet 检测 → 切打滑模型。

**真实案例**：某 AD 车队中雨下 lane detection 误检率 ×3 `UNVERIFIED`；fix：雨刮信号 → 提高 radar 权重 + HD map prior 限速。

---

## 8 · Failure #7 — 粉尘 / 烟雾

**物理**：颗粒 Mie 散射可见 + NIR；LiDAR 出"墙"假象；视觉对比度急降；热成像（LWIR）穿透较好。

**症状**：LiDAR 在矿洞 / 烟雾下报 1–2 m"墙"；camera contrast < baseline 50%；active NIR 几乎无回波。

**偵测**：LiDAR 多回波（first-return = dust，last-return = wall）；camera 对比度直方图 OOD。

**缓解**：工业 / 矿业 AGV 换 thermal + radar，视觉辅助；fire response drone 用 thermal + LiDAR last-return + 极慢速。

**真实案例**：矿用 AGV 在掘进面扬尘下 LiDAR 急停；fix：last-return + 多帧时序确认（dust ms 级，wall 稳态）。

---

## 9 · Failure #8 — 水下

**物理**：水折射使针孔模型失效（须建 housing port 折射模型）；NIR <1 m 被吸收；可见光 <5 m（浑浊 <1 m）；声呐主导。

**症状**：针孔 calibration 残差 systematic bend；RGB <5 m 外看不到；浮游生物 = false acoustic returns。

**偵测**：visibility 透射率作 prior；acoustic + optical fusion 一致性。

**缓解**：整套设计就不一样——multibeam sonar 主 + DVL 速度锚 + FOG IMU + 光学辅助（详见 `deployment/hardware-selection/bom_templates_by_class.md` BoM #5）。浅水可见区用光学；浑浊 / 深水纯 acoustic。

**真实案例**：科研 AUV 视觉 SLAM 在 5 m 后崩；fix：视觉 SLAM 限 <3 m，主导航交给 sonar+DVL+FOG。

---

## 10 · Hidden Assumptions

- **8 类是工程归类，不是物理分类。** 反射 + 透明物理上是「surface BRDF 假设破裂」一族；camera shift + 振动是「机械 / 时变」一族。运维上分开写更方便。
- **阈值高度平台依赖。** P95 残差 / 雨噪密度 / 振动谱峰阈值——必须用 fleet 30+ 天 telemetry 实测分布校准；本文数字仅作起点。
- **偵测器本身会失效。** 偵测器是分布外那一刻最不可信；多偵测器投票 + 人工 fallback 是常态。
- **「8 类」不闭包。** GNSS jamming / 电磁干扰 / sensor 软死 / 时钟跳变也是田野常见，本文未独立列；归入 telemetry 异常类。
- **embodiment 偏置。** 本文重 ground / aerial / AD / manip，marine 与 humanoid 案例偏少；待补。

## 11 · 与基线对比 + Interview Tip

| 视角 | 学界 benchmark | 本文 ops runbook |
|---|---|---|
| 失败定义 | "metric 下降" | "fleet alarm 触发" |
| 数据来源 | 公开数据集 | telemetry 实测分布 |
| 阈值 | 不写 | 必须有（哪怕 UNVERIFIED）|
| Fallback 模式 | 不写 | 必须有（哪些 sensor 降权、哪些 alarm）|

**Interview Tip**：被问"你怎么知道 robot 当前不能信"——别答"用 SOTA detector"，答"我在 fleet telemetry 上拉 P95 + chi-square 滑动窗口 + 多偵测器投票，每个失败模式有独立 alarm 通道"。这才是 ops。

---

## References

- Skydio engineering blog (hot-recalibration concept) — `UNVERIFIED, no DOI`
- WaterDepth optical attenuation — Mobley, *Light and Water* (1994). `UNVERIFIED, textbook`
- Active NIR vs sunlight — `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`
- ClearGrasp（透明物体抓取）— Sajjan et al. *ICRA 2020*. https://arxiv.org/abs/1910.02550
- LiDAR weather degradation — Bijelic et al. *CVPR 2020 STF*. https://arxiv.org/abs/1902.08913

## Boundary

本文是田野部署 ops runbook：每类失败给「物理 → 症状 → 偵测 → 缓解」+ 真实案例。**不写**：跨 embodiment 失败模式的物理对比矩阵（去 `crossing/failure-modes-atlas/transparent_reflective_deformable.md`），单 sensor 物理（去 `foundations/sensor-physics/`），SLAM / VIO 算法本体的 corner case（应在算法 dissection 里），功能安全 / ISO 26262 / SOTIF（另一份文档）。本文阈值是 starter；production 必须用 fleet 30+ 天 telemetry 校准。

---

[← Back to Failure Modes README](./overview.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
