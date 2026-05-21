# Stereo Camera 几何物理 (Stereo Camera Geometry Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — baseline × focal length / disparity = depth，亚像素极限
> **核心定位**：所有人都背得出 `Z = f × B / d`，但**为什么 Skydio baseline 比 D435 大 6×、为什么 5 m 处深度不确定性远超 Camera 标定误差** — 才是设计 stereo 工程系统时真正承重的物理

**Status:** v1 — opinionated draft，14-item dissection 范式。数字 `UNVERIFIED`。
**Wedge tier:** W1（独家轴扩充 6 篇之一）

### X-Ray opening (非专家友好)

(a) Stereo depth = `f × B / d` (f = focal length 像素，B = baseline，d = disparity 像素)；这意味着 depth 误差 ∝ `Z² / (f × B)` — 深度不确定性**随距离平方放大**。(b) Intel D435 用 5 cm baseline 是为了 manipulation 桌面 0.3–3 m，Skydio X10 用 ~30 cm baseline 是为了 drone 5–30 m，这两个不是"工程偏好"是几何强制。(c) 对 sensor 工程师：选 stereo 系统的 baseline 不是看"小一点更便携"，是看**目标工作距离的 Z² 误差曲线在哪里跨过应用容忍线**。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1838 ── Wheatstone 立体镜（第一个 stereoscope）
1959 ── Julesz random dot stereogram → 计算立体视觉之父
1981 ── Marr-Poggio 计算立体视觉理论
1991 ── SRI Small Vision System — 第一个量产 stereo computer
2010 ── Bumblebee / PointGrey 工业 stereo 相机
2015 ── Intel RealSense R200 (5 cm baseline, 850 nm projector)
2017 ── Intel RealSense D400 系列普及 → robotics 默认
2019 ── Skydio R1 (~25 cm baseline VIO stereo, drone)
2020 ── ZED 2 / ZED 2i (12 cm baseline，4K stereo)
2023 ── Stereo + transformer (RAFT-Stereo / CREStereo) sub-pixel 突破
2025 ── Skydio X10 / DJI Avata 2 stereo + neural depth 普及
        ── 你在这里 (2026) ──
?    ── single-photon stereo (SPAD + stereo geometry)？开
```

---

## 1 · 极线几何 (Epipolar Geometry / Overview)

📌 **Napkin Formula** (X-Ray)：

```
Z = (f × B) / d
ΔZ / Z = Z / (f × B) × Δd    # 深度误差与 Z 平方关系
σ_Z ≈ Z² × σ_d / (f × B)
```

第二式是工程上**唯一真正承重的公式** — 选 baseline 的根据。

### 1.1 系统组件

| 组件 | 输入 | 输出 | 关键约束 |
|---|---|---|---|
| **左 / 右 sensor** | photon | 同步 frame | hardware sync ≤ 几 µs |
| **rectification** | raw L/R + 内外参 | 行对齐 L/R | 标定矩阵 |
| **disparity matcher** | rectified L/R | disparity map | block matching / SGBM / neural |
| **depth converter** | disparity + (f, B) | Z map | trivial |

### 1.2 关键机制 — 极线约束

L 相机中点 (x_L, y_L) 在 R 相机的对应必落在一条**极线**上 (epipolar line)。rectification 把两个 image 旋转到使所有极线水平 → 对应搜索从 2D 退化为 1D（横向 disparity 搜索）。

⚡ **Eureka Moment.** Stereo 的全部魔法在 "对应搜索从 2D 降为 1D" — 这是 rectification 的唯一目的；只要 L/R 标定准确，剩下的 disparity 估计就是一维问题。1D 让 sub-pixel 估计 + 实时变得可行。

### 1.3 信息流

```
L photon ─→ L sensor ─→ rectify ─→ ┐
                                    ├── disparity matcher ─→ disparity ─→ Z
R photon ─→ R sensor ─→ rectify ─→ ┘
                                          ↑
                                       (f, B) 标定参数
```

---

## 2 · 数学核心 — 深度不确定性 (Math Core)

**目标**：估计在已知 (f, B, σ_d) 下，距离 Z 处的深度不确定性。

**推导**：

```
Z = f × B / d
dZ/dd = -f × B / d² = -Z² / (f × B)
σ_Z = |dZ/dd| × σ_d = Z² × σ_d / (f × B)
```

**变量说明**：

| 符号 | 含义 | 典型值 |
|---|---|---|
| `f` | focal length (像素) | D435: ~860 px; Skydio: ~800 px |
| `B` | baseline (米) | D435: 0.05; ZED 2: 0.12; Skydio X10: ~0.3 `UNVERIFIED` |
| `d` | disparity (像素) | 0–256 typical |
| `σ_d` | disparity 估计噪声 | block matching ~0.5–1.0 px; SGBM ~0.3 px; neural ~0.1 px |
| `Z` | 距离 (米) | 应用相关 |

**直觉**：

- `σ_Z ∝ Z²` — 深度误差随距离**平方放大**
- `σ_Z ∝ 1/B` — 加大 baseline 线性改善
- `σ_Z ∝ 1/f` — 长焦改善，但代价是 FOV 缩小
- `σ_Z ∝ σ_d` — 用 neural matcher（如 CREStereo）压低 σ_d 改善

工程意义：要么**长焦**、要么**大 baseline**、要么**亚像素好**，否则远距 stereo 完全不可用。

---

## 3 · Worked Example — D435 vs Skydio-class 在 5 m 处

D435 setup：

```
f ≈ 860 pixels (1280×720 @ 65° HFOV)
B = 0.05 m
σ_d ≈ 0.5 pixels (SGBM)
Z = 5 m
```

`σ_Z = Z² × σ_d / (f × B) = 25 × 0.5 / (860 × 0.05) = 25 × 0.5 / 43 ≈ 0.29 m`

**D435 在 5 m 处的深度不确定性 ~29 cm** — 已经大到无法做避障决策（drone 在 10 m/s 飞，0.3 s 内已经撞上去）。

Skydio-class setup：

```
f ≈ 800 pixels
B = 0.30 m  (6× D435)
σ_d ≈ 0.1 pixels (neural matcher)
Z = 5 m
```

`σ_Z = 25 × 0.1 / (800 × 0.30) = 2.5 / 240 ≈ 0.010 m = 1 cm`

**Skydio 在 5 m 处的深度不确定性 ~1 cm** — 29× 提升，因为 baseline 6× + σ_d 5× 改善。

延伸到 30 m（drone 真实工作距离）：

- D435: σ_Z = 900 × 0.5 / 43 = **10.5 m**（完全无用）
- Skydio: σ_Z = 900 × 0.1 / 240 = **0.375 m**（仍然可用）

⚡ **结论**：Intel D435 不是"低端 stereo"，它是 **manipulation 桌面专用**；Skydio baseline 大 6× 不是"工程贪心"，是为了 30 m 远距 drone 避障的几何要求。这两个是不同应用的几何最优解，不可互换。

---

## 4 · 实战 hardware archetypes

**Tabletop manipulation stereo.** Intel `RealSense D435` (5 cm) / `D455` (~9.5 cm) / `D435i` (内嵌 IMU)。850 nm projector 添加 texture，做"active stereo"（见 NIR 850 nm dissection）。0.3–3 m 工作。

**Mobile robot / AGV stereo.** ZED `ZED 2` / `ZED 2i` (12 cm baseline) / ZED `Mini`。无 projector，依赖自然 texture。室内 1–10 m，室外 5–25 m。

**Drone stereo.** Skydio `X10` (~30 cm baseline `UNVERIFIED`) / DJI `Avata 2` 下视 stereo / Autel `Evo II`。大 baseline + neural matcher。

**Specialty.** Lucid `Helios2+` (短 baseline + ToF 混合) / Stereolabs `ZED X` (auto-grade GS stereo)。

**Custom stereo rig.** 学术 / 高端 drone 经常用两个 GS 单目 + 标定，baseline 任意定制。Skydio R1 早期就是这样。

---

## 5 · Rectification 数学

把两个 camera 的 image 数学上旋转到使光轴平行 + 像素行水平对齐：

```
P_rect = R_rect × K × R⁻¹ × K⁻¹ × P_raw
```

需要的标定参数（出厂前需测）：

| 参数 | 维度 | 含义 |
|---|---|---|
| `K_L, K_R` | 3×3 | 左右内参（focal, principal point, skew） |
| `D_L, D_R` | 5 维 | 畸变系数（k1, k2, p1, p2, k3） |
| `R_LR` | 3×3 | L 到 R 的旋转 |
| `T_LR` | 3 维 | L 到 R 的平移（含 baseline）|

工厂标定 vs 现场标定差异巨大：D435 出厂 σ_d ~0.5 px；现场 ChArUco 标定后 ~0.3 px；drone 飞行中机械形变 ~0.1° → 在 5 m 处 ~9 cm 额外误差。drone 强制飞行前自检 + 飞行中 online refinement。

---

## 6 · Failure modes 与隐含假设

**Texture 不足.** 白墙、玻璃、纯色地板 → disparity matcher 找不到对应。Active stereo (D435) 用 projector 补；passive stereo (ZED, Skydio) 在白墙前彻底失效。

**重复纹理.** 砖墙、栅栏、棋盘 → 多个 disparity 候选都匹配。Multi-scale matcher + smoothness prior 缓解；neural matcher（CREStereo）擅长此。

**反光 / 透明物体.** 玻璃杯、塑料瓶 — disparity 跳跃。passive stereo 完全失语；polarization-aware stereo 是研究方向（见 polarization dissection）。

**Occlusion.** L 看到的物体右边 R 看不到（half-occluded region）。SGBM 会产生 disparity discontinuity；neural matcher 容忍度高。

**机械漂移.** drone 飞行温度变化 / 落地震动让两个 camera 的相对几何漂 0.05°–0.1° → 5 m 处误差 5–10 cm。online recalibration 是 production drone 必备。

### Hidden Assumptions — 极线几何成立的前提

- **极线几何成立。** L/R 内外参标定准确；机械形变 < 标定容忍。
- **Texture 充足。** disparity matcher 至少需要 ~5–10% scene 有可识别 texture。
- **亚像素精度受 SNR 限。** σ_d 不能 < 0.05 px（光子 shot noise 下限）。
- **同步精度。** L/R 帧时间差 < 100 µs（否则运动场景中物体在两帧已经位移）。
- **静态场景假设。** L/R 同时拍摄，否则动态物体 disparity 错误。
- **rectification 假设畸变可建模。** 鱼眼镜头边缘 disparity 完全失语。
- **f, B 数值已知。** 出厂标定的 baseline 在跌落 / 温度循环后会漂。

---

## 7 · 与其他 depth 传感器对比 + Interview Tip

| Depth sensor | 工作机制 | 远距能力 | 近距 (cm) | Texture 需求 |
|---|---|---|---|---|
| **Passive stereo** | 几何 + 自然 texture | 限 baseline | <0.5 m 死区 | 强 |
| **Active stereo (D435)** | 几何 + projector texture | <4 m 室外 | 0.2 m | 弱（projector 补） |
| **Structured light** | 几何 + dot pattern | <2 m | 0.05 m | 不需要 |
| **ToF (Kinect v2)** | 相位调制 | <8 m | 0.3 m | 不需要 |
| **LiDAR** | TOF 单束扫描 | 50–200 m | 0.5 m | 不需要 |
| **Monocular ML depth** | 神经网络先验 | 任意（scale 模糊） | 任意 | 弱 |

**🎙️ Interview Tip.** 被问"为什么 drone 用大 baseline、机械臂用小 baseline"？— 一句话：**`σ_Z = Z² × σ_d / (f × B)` — drone 工作距离 5–30 m 让 Z² 主导，必须加大 B；manipulation 工作距离 0.3–1 m 让 Z² 很小，B = 5 cm 就够，且小 baseline 让近距 disparity 不饱和 ≤256 px**。这是几何强制的最优，不是工程偏好。

---

## 8 · For the reader (per-persona)

- **Manipulation engineer** — D435 / D455 是几何对的选择，不需要羡慕 drone 的大 baseline。专注 active stereo projector + IR BPF。
- **Aerial engineer** — passive stereo + neural matcher 比 active stereo + small baseline 远距更优；Skydio class 是几何对的解。
- **AGV engineer** — ZED 2 (12 cm) 是 sweet spot，室内 1–10 m 平衡良好；外加 2D LiDAR 做近距 safety。
- **AR / VR** — passthrough stereo 用 ~6 cm（接近人眼瞳距），用户视差自然。

---

## References

- Hartley & Zisserman, "Multiple View Geometry in Computer Vision" — 标准教科书
- Intel RealSense D400 series whitepapers — `UNVERIFIED, no DOI`
- Stereolabs ZED 2 / ZED X datasheets — `UNVERIFIED`
- RAFT-Stereo (arXiv 2109.07547) / CREStereo (arXiv 2203.11483) — neural disparity SOTA
- Skydio X10 / DJI Avata 2 marketing materials — `UNVERIFIED`
- 维护者在 Autel 的 stereo + neural depth 经验

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — active stereo 的 projector 物理
- `foundations/sensor-physics/rolling_vs_global_shutter.md` — stereo 同步对 GS 的强制要求
- `foundations/sensor-physics/imu_physics_and_noise_model.md` — VIO 中 stereo + IMU 融合
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — stereo 在跨 embodiment BOM 位置
- `embodiments/manipulation/sensor-stack/` — D435 在桌面工作流的标定细节
- `embodiments/aerial/sensor-stack/` — drone 大 baseline 与 mechanical 设计
- `deployment/hardware-selection/` — stereo + rectification 标定 pipeline

*2026-05-21. v1 first draft. UNVERIFIED → v1.2 datasheet 验证。*

---
[← Back to sensor-physics README](./README.md)
