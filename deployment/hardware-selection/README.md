# 硬件选型 — 从应用反推 sensor pick / Hardware Selection

**Status:** v1 — opinionated landing。SKU 价格 / 重量 / 功耗一律标 `UNVERIFIED`，需以 vendor datasheet 为准。
**TL;DR:** 学术综述列「常用 sensor」，工程上要的是「这个应用、这个预算、这个重量包络下，**该买哪一颗，型号是什么**」。本目录把 BoM（Bill of Materials）模板与「应用 → sensor pick」决策流程作为一等公民写出来。第三颗 sensor（在 IMU + 至少一颗相机之外的那一颗）才是 embodiment 身份所在。

---

## 1 · 为什么 hardware-selection 要单独写

`foundations/sensor-physics/` 讲单颗 sensor 的物理（QE、噪声、热漂移、安全限值）。`crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` 讲跨 embodiment 的 SWaP-C 大账。但在产品立项当天，工程师要的是一份**可下单的 BoM**：

```
应用 + 预算 + 重量 / 功耗包络
   ↓
sensor 列表（mono / stereo / RGBD / LiDAR / IMU / radar / sonar / 其他）
   ↓
每一项的 vendor + 型号 + 价格 + 重量 + 功耗 + 接口
   ↓
合计 SWaP-C；与系统预算比较；迭代
```

学界不会替你做这一步；vendor sales 会替你做但会偏向自家货。本目录把这件事写成可复用的模板。

---

## 2 · 从应用反推 sensor pick 的决策流程

```
1) 确定 embodiment class（manipulation / humanoid / ground / driving / aerial / marine）
   └─ 决定哪一类 sensor 是 binding constraint（参见 sensor-stack-matrix）

2) 确定工作距离 / FOV / 帧率
   └─ 工作距离把 sensor class 进一步收窄：
      ├─ 0.1–3 m：RGBD / structured light / 近距 stereo
      ├─ 1–30 m：stereo / 中近 LiDAR / 单目 + ML
      ├─ 5–250 m：长距 LiDAR / radar / 长基线 stereo
      └─ 水下：sonar 主导，光学辅助

3) 确定环境（室内 / 室外 / 室外强光 / 雨雪 / 水下）
   └─ 决定 active NIR 是否能用、是否要 polarization、是否要 radar 冗余

4) 确定 SWaP-C 包络
   ├─ 重量预算：drone 是几十克量级；AGV 是公斤；AD 不在乎
   ├─ 功耗预算：drone <25 W；AGV ~50 W；AD 几百 W
   ├─ 成本预算：consumer <$1k；商用 AGV $5–30k；AD demo $50k+；AUV $50k–1M
   └─ 认证预算：SEMI S2 / IEC 60825-1 / 车规 / 海事 — 通常翻倍

5) 输出 BoM
   └─ vendor + 型号 + 数量 + 单价 + 重量 + 功耗 + 接口 + lead time
```

第 1 + 2 步决定**类**，第 3 + 4 步决定**SKU**，第 5 步是产物。学界综述常常只写到第 1–2 步就停了。

---

## 3 · 决策流程的常见错位

| 错位 | 后果 |
|---|---|
| 用 RealSense D435 替 LiDAR（室外 AD scale） | 强光下深度图崩；详见 `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` |
| 用 VLP-16 替 RGBD（manipulation scale） | 角分辨率在 1 m³ 内换不到 cm 级；13× 成本无收益 |
| 用 MEMS IMU 替 FOG（AUV 长航时） | 漂移指数级累积；半小时后位置不可信；详见 `foundations/sensor-physics/imu_physics_and_noise_model.md` |
| 用单目 + ML 替 stereo（aerial 5 m 内避障） | 单目 metric scale 不稳；近场避障是 stereo 主场 |
| 忽略硬件触发同步（高动态平台） | VIO 在加速 / 旋转下崩；详见 `deployment/multi-modal-sync/` |

每一个错位都对应一份过去的产品计划——它们最后都靠加预算和换型号收尾，不靠算法。

---

## 4 · 本目录内容

| 文档 | 内容 |
|---|---|
| `bom_templates_by_class.md` | 5 类典型 embodiment 的 BoM 模板（$500 / $5k / $50k / $200k 等级） |
| `(待补) sensor_vendor_landscape.md` | 主要 vendor 与 SKU 谱系；TODO |
| `(待补) certification_overhead.md` | SEMI S2 / IEC 60825-1 / 车规 / 海事认证对 BoM 的影响；TODO |

---

## 5 · Cross-references

- 单 sensor 物理（5 篇完整）：
  - `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`
  - `foundations/sensor-physics/tof_physics_for_embodied_ai.md`
  - `foundations/sensor-physics/lidar_physics_905_vs_1550.md`
  - `foundations/sensor-physics/imu_physics_and_noise_model.md`
  - `foundations/sensor-physics/event_camera_dvs_physics.md`
- 跨 embodiment SWaP-C 大账：`crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md`
- 算力预算（决定 sensor 数据怎么处理）：`deployment/compute-budget/README.md`
- 同步（决定多 sensor 时间戳怎么对齐）：`deployment/multi-modal-sync/README.md`

## Boundary

本目录写 BoM 与「应用 → SKU」决策。**不写**单 sensor 物理（去 `foundations/sensor-physics/`）、跨 embodiment SWaP-C 的对比矩阵（去 `crossing/sensor-stack-matrix/`）、每 embodiment 的完整 perception 栈（去 `embodiments/<x>/sensor-stack/`）。本目录的 BoM 是 starter 模板，不是 production-grade 采购单——production 必须以 vendor 一手 datasheet + 实测为准。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
