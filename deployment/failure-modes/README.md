# 失败模式 — 田野部署的常见崩法 / Failure Modes in the Field

**Status:** v1 — opinionated landing。具体频率 / 触发阈值数字标 `UNVERIFIED`。
**TL;DR:** 论文报告 SOTA 时跑的是 ScanNet / EuRoC / KITTI 这类受控数据；田野部署遇到的 8 类失败模式（camera shift / 振动 / 逆光 / 反射 / 透明 / 雨雪 / 粉尘 / 水下）几乎不在 benchmark 里。本目录把这 8 类按「物理触发 → 算法症状 → 偵测方法 → 缓解策略」组织成 ops runbook，与 `crossing/failure-modes-atlas/` 的跨 embodiment 物理分析分工。

---

## 1 · 为什么 failure-modes 要单独写

学界综述写「算法在 KITTI 上达到 SOTA」；产品工程师要的是「这套系统部署到 100 台车上跑 3 个月，常见崩法有哪几种、每种怎么自动偵测、出现时怎么 fallback」。两者之间隔着的就是本目录。

`crossing/failure-modes-atlas/transparent_reflective_deformable.md` 已经把 TRD（transparent / reflective / deformable）三类跨 embodiment 写过——那是**物理分析**视角。本目录是**部署运维**视角：田野上 robot 真的崩了，工程师手里要拿什么 runbook。

---

## 2 · 8 类田野失败模式（速览）

| # | 失败模式 | 物理本质 | 典型受害 sensor | embodiment 重灾区 |
|---|---|---|---|---|
| 1 | Camera shift（外参漂移） | 紧固件松动 / 跌落 / 热膨胀 | 多目 / RGBD / LiDAR-cam 标定 | drone, AD, humanoid |
| 2 | 振动 | 电机 / 桨 / 路面 | IMU 偏置抖动、相机模糊、LiDAR jitter | drone, AGV |
| 3 | 逆光 / 阳光直射 | 高动态范围超 sensor / 主动 NIR 被压 | RGB AE 崩、active depth 失效 | aerial, AD, ground |
| 4 | 反射（镜面 / 水面 / 玻璃） | 几何估计虚像 | stereo NaN、LiDAR 多径、VIO loop-close 错 | humanoid, AGV, AD |
| 5 | 透明（玻璃 / 塑料 / 水） | 光穿过 surface | depth 看到背景而非物体 | manipulation, humanoid, drone |
| 6 | 雨雪 | 介质散射 + 雨滴 | 镜头雨珠、LiDAR 雨噪、radar 干扰小 | AD, aerial |
| 7 | 粉尘 / 烟雾 | 介质散射 | 镜头蒙尘、LiDAR 多回波、热成像有用 | mining AGV, aerial, AD |
| 8 | 水下 | 折射 / 吸收 / 浑浊 | 针孔模型失效、NIR 被吸收 | marine |

更细的跨 embodiment 矩阵 + 物理来源：`crossing/failure-modes-atlas/`。

---

## 3 · 「物理 → 症状 → 偵测 → 缓解」四步法

```
1) 物理触发（field cause）
   例：螺丝松动 → 相机外参旋转漂 0.5°
2) 算法症状（algorithm symptom）
   例：双目重投影残差持续 > 阈值；VIO 漂率 ↑
3) 在线偵测（detection）
   例：reprojection error chi-square 7 天滑动；OOD score
4) 缓解（mitigation）
   例：自动触发 hot-recal；fallback 到 mono+IMU；降速；上报维护
```

每一类失败模式都该有一份这样的四步 runbook。详细分类与案例：`field_failures_taxonomy.md`。

---

## 4 · 8 类失败模式的「偵测难度」与「缓解难度」分级

| 失败模式 | 偵测难度（自动） | 缓解难度 | 备注 |
|---|---|---|---|
| Camera shift | 🟢 易（残差 + chi-square） | 🟡 中（hot-recal 或工厂返修） | 残差监测是基线 |
| 振动 | 🟡 中（IMU 谱分析） | 🟡 中（减振 + IMU 滤波） | 频率分析比时域容易 |
| 逆光 | 🟢 易（AE 报曝光过曝） | 🔴 难（物理就这样） | 多曝光融合或换 HDR sensor |
| 反射 | 🔴 难（看起来像合法表面） | 🔴 难（要语义先验） | VLM 知道「这是玻璃」最快 |
| 透明 | 🔴 难（同上） | 🔴 难（语义 + 偏振 + 触觉） | TRD 旗舰话题 |
| 雨雪 | 🟢 易（雨刮信号 / 雨滴检测） | 🟡 中（降级 + radar fallback） | 雨刮信号是好 prior |
| 粉尘 / 烟雾 | 🟡 中（点云密度异常） | 🔴 难（视觉根本不行） | 工业场景换热成像 |
| 水下 | 🟡 中（NIR 缺失 + 声呐主导） | N/A | 整套设计就不一样 |

---

## 5 · 跨 embodiment 的「哪些失败该上 alarm，哪些该 fallback」

- **应 alarm 立即停**：camera shift（标定漂超阈值）、IMU 谱异常（飞行平台）、水下漏水、热失控。
- **应 fallback 降级**：逆光下 active depth → stereo only；雨雪下 LiDAR → radar primary；振动剧烈下 VIO → odom + IMU。
- **应 alert 等维护**：长期慢漂、镜头脏污、单颗 IMU 偏置异常但还能跑。
- **应记录不响应**：罕见但暂时性的偵测（一帧 OOD），写入 telemetry，离线分析。

---

## 6 · 本目录内容

| 文档 | 内容 |
|---|---|
| `field_failures_taxonomy.md` | 8 类失败模式 ops runbook：每类 1–2 真实案例 + 偵测 + 缓解 |
| `(待补) ood_score_design.md` | OOD / 异常分数设计模式；TODO |
| `(待补) telemetry_field_log.md` | 田野 telemetry 字段与回流；TODO |

---

## 7 · Cross-references

- 跨 embodiment 物理分析（TRD）：`crossing/failure-modes-atlas/transparent_reflective_deformable.md`
- Sensor 物理限值（逆光 / 水下 / NIR）：
  - `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`
  - `foundations/sensor-physics/tof_physics_for_embodied_ai.md`
  - `foundations/sensor-physics/lidar_physics_905_vs_1550.md`
  - `foundations/sensor-physics/imu_physics_and_noise_model.md`
- 标定漂移监测（camera shift 的标定视角）：`deployment/calibration/README.md` §5.3
- 同步崩了 → 也是失败模式：`deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md` §4

## Boundary

本目录写**田野失败的部署运维 runbook**。**不写**：跨 embodiment 失败模式的物理对比（去 `crossing/failure-modes-atlas/`，那里写「TRD 在 6 个 embodiment 上各自怎么崩」）、单 sensor 物理（去 `foundations/sensor-physics/`）、SLAM / VIO 算法本身的 corner case（应在算法 dissection 里写）、安全 / 功能安全（ISO 26262 / SOTIF）—— 那是另一份文档。本目录的运行阈值是 starter；production 必须以 fleet telemetry 实测分布为准。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
