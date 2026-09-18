<!-- ontology-5axis
problem: reconstruction
representation: NeRF
sensor: mono
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# 小型无人机神经 3D 物体重建 (Neural 3D Object Reconstruction with Small-Scale Unmanned Aerial Vehicles)

> **发布时间**：2025-09 (v1) / 2026-08-30 (v3，arXiv:2509.12458v3 [cs.RO])
> **论文 / 模型名**：N3DR (Neural 3D Reconstruction) 系统 · 组件 = SfM (Meshroom/AliceVision) + Nerfacto (Nerfstudio)
> **核心定位**：把「<100g 微型无人机 + 闭环主动视角选择 + near-RT SfM 反馈 + non-RT Nerfacto」拼成一套**室内静态小物体自主 3D 扫描系统**，硬件比同类小一个量级、目标从 MA/LA 缩到 PA（personal-area）尺度。

导语：现有 UAV 3D 重建要么用多公斤级平台打大场景，要么被动飞静态轨迹；微型无人机（Crazyflie）此前只被证明能做「粗糙」重建。本文的结论是——用**廉价的 near-RT SfM 点云当"覆盖率传感器"来实时改飞行轨迹**，即使这块点云人眼几乎认不出（PSNR 仅 3–6 dB），也足以做飞行控制信号，而高质量输出交给离线的 NeRF 背反向传播修位姿。

---

## X-Ray 开场（非专家 3 句版）

1. **问题**：小于 100 克的微型无人机载重/算力/续航被卡死，之前没人能用它做「高保真」3D 物体重建——只能做大平台的活。
2. **做法**：双流水线闭环——near-RT 用 SfM 出瞬时点云，把物体按角度切成若干「region」，**点数最少的那块就是下一个航点**（`argmin S_k`）；non-RT 用 Nerfacto 把 SfM 位姿与外部定位（UWB / OptiTrack）融合后做高保真体渲染。
3. **对 spatial AI 研究者意味着什么**：把「重建质量」直接变成「飞行控制信号」，是**感知-控制紧耦合**在资源极限平台上的一个干净范例；同时暴露了「微型平台上外部定位取代 onboard VO」这一实用取舍。

---

## 📍 研究全景时间线

```
1867 photogrammetry
  │
2020 NeRF ─────────────► 神经体渲染成为高保真重建主流
2022 instant-ngp (hash) ──► 近实时
2023 3DGS ───────────────► 渲染加速
2023 Nerfacto ───────────► 质量/算力折中（本文选用，理由：作者前作[8]对比 instant-ngp / Splatfacto 后 Nerfacto 更稳）
  │
UAV 重建分支：
  heavy hexacopter / DJI M600 Pro 9.5kg / Mavic Pro 2 907g  → 室外 MA 尺度（[13][18][23]）
  medium 平台 1.45–3.17kg + LiDAR/双目                   → 室内 LA 尺度（[15][5][3]）
  Crazyflie 做 LA 室内建图 → 仅"rudimentary"精度           （[15]）
  │
★ 本文（2509.12458）：<100g 微型 UAV · PA 尺度静态物体 · 闭环主动视角 + 双流水线
  │
本文局限：
  - 仅室内、静态、无避障（碰撞靠空间隔离）
  - near-RT 点云几乎不可辨识，只够做控制
  - 大/透明物体 HD 误差仍巨大（95–182）
  - 动态轨迹的"可复现"评估靠预采集池离线子采样，非完全在线闭环
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练-推理差异 / 关键点 |
|---|---|---|---|
| **多 UAV 采集** | 初始圆形航点、物体先验 | 带元数据的图像（320×320） | Crazyflie 2.1 + AI-Deck (GAP8) + ESP32 Wi-Fi，机载不做 VO |
| **定位系统** | — | UAV 坐标 | 二选一：Loco UWB（TDoA，sub-decimeter）或 OptiTrack（8 红外相机，sub-millimeter GT） |
| **图像预处理** | 原始图 | 增强图 | Unsharp Masking + high-pass 锐化；Histogram Equalization + Gamma Correction 调对比 |
| **near-RT 流水线** | 图像 + 内参元数据 | 瞬时点云 𝒫 | 特征提取/匹配 + SfM；基站在 4 个专用核上分布式处理 |
| **动态轨迹适应** | 瞬时点云 𝒫 | 新航点 + yaw | 无训练；角度切分 + 点数覆盖率评分 + `argmin` |
| **location-aware 融合** | SfM 位姿 + UAV 坐标 | 融合相机位姿 | Python 脚本做 scaling/rotation/translation 对齐（Fig.3） |
| **non-RT 重建 (N3DR)** | 融合位姿 + 图像 | Nerfacto 渲染 / mesh / 点云 | Nerfacto **默认优化**；Pose Refinement 反向传播修位姿；Meshroom 出 SfM；Poisson 重建出 mesh |

### 1.2 关键机制

**⚡ Eureka Moment**：**把"重建质量"当作飞行控制变量——用 near-RT SfM 点云在每个角度 region 的"点数"`S_k=|C_k|` 当作覆盖率，`argmin_k S_k` 直接给出下一个航点**；昂贵的高保真交给离线 NeRF，两块各司其职解耦。

次级洞见：**location-awareness** 不只是提高精度，而是**提高可用图像数**——SfM 只在图像特征足够时才给得出位姿，外部定位可在 SfM 失手时"顶替"，从而让 N3DR 吃到更多图像（Tables I/II: #images used 上升）。

### 1.3 信息流 ASCII 图

```
      ┌───────────── 初始圆形航点 / 预定义轨迹 ─────────────┐
      ▼                                                   │
[UAV 绕物飞行, yaw 锁定指向物体质心]                        │
      │ 拍图 (320x320) + 元数据(内参)                       │
      ▼                                                   │
[基站]  图像预处理(锐化/对比)                               │
      │                                                   │
      ▼                                                   │
[near-RT SfM] ──► 瞬时点云 𝒫 = {P_i}                        │
      │                                                   │
      ▼                                                   │
[距离滤波] 𝒫_filtered = { P_i : ||P_i - C_obj|| ≤ R_filter}  │
      │                                                   │
      ▼                                                   │
[按角度切 slice → 组成 region k]                            │
   S_k = |C_k| (可见簇点数)                                  │
      │                                                   │
      ├── min_k S_k ≥ τ_coverage ? ──► 是 ──► 任务结束 降落   │
      │                              └► 否                  │
      ▼                                                   │
   k_next = argmin_k S_k  ──► 下一航点(region 中心) ───────────┘
                             + ψ = atan2(y_obj-y_uav, x_obj-x_uav)

      ┌────────── 并行（non-RT, 离线）──────────┐
   [SfM 位姿] ⊕ [UWB/OptiTrack 坐标] → 对齐融合 → [Nerfacto] → 渲染/mesh/点云
```

---

## 2 · 数学核心

📌 **Napkin Formula**：
> **飞向点最少的角度切片**：`k_next = argmin_k |C_k|`；当 `min_k |C_k| ≥ τ_coverage` 时收工。

**目标**：让无人机自主决定"下一张图拍哪里"，使物体各视角覆盖均匀。

**公式链**：

1) 背景剔除（距质心的欧氏球）：
```
𝒫_filtered = { P_i ∈ 𝒫 | ‖P_i − C_obj‖₂ ≤ R_filter }        (1)
```

2) 覆盖率评分（区域 k 的可见点簇点数）：
```
S_k = |𝒞_k| ,   𝒞_k ⊆ 𝒫_filtered                            (2)
```

3) 欠覆盖判定与航点选择（Algorithm 1）：
```
under-covered:  S_k < τ_coverage
k_next = argmin_k S_k   →   航点 = region k_next 的几何中心
terminate:  min_k S_k ≥ τ_coverage
```

4) yaw 锁定（保持物体居中）：
```
ψ = atan2( y_obj − y_uav , x_obj − x_uav )
```

**变量说明**：`𝒫` 瞬时点云；`C_obj=(x_obj,y_obj,z_obj)ᵀ` 物体质心；`R_filter` 滤波半径；`𝒞_k` region k 可见簇；`S_k` 覆盖率分数；`τ_coverage` 经验阈值；`ψ` 偏航角。

**直觉**：这是一个**离散贪心覆盖**——用最便宜的可观测量（点数）当作"信息缺口"的代理，每次只补最缺的一块。注意 SfM 点云是**噪声代理**（near-RT PSNR 仅 3–6 dB），但它捕捉的是"有没有看到"，而非"看得好不好"，因此对控制够用。

---

## 3 · 带数字走一遍（玩具设定，非论文数据）

设 `R = 4` 个 region，`τ_coverage = 100`，`R_filter` 覆盖整个物体。

第 0 轮（初始两圈后）瞬时点云簇点数：

| region k | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `S_k = |C_k|` | 120 | 85 | **40** | 95 |

- 判定：min `S_k` = 40 < 100 → 未覆盖完。
- `argmin_k S_k` = region 3 → 航点 = region 3 中心；yaw 锁定指向 `C_obj`。
- UAV 飞往 region 3，期间不停机、慢速绕圈；出该扇区后把区域内约 45 张图并入点云（触发一次重建）。

第 1 轮更新后：

| region k | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `S_k` | 121 | 98 | **103** | 96 |

- min `S_k` = 96 < 100 → 仍未达标 → `argmin` = region 4 → 飞 region 4。

第 2 轮后若 min `S_k ≥ 100` → **terminate，降落**。

> 直觉：`τ_coverage` 是"宁可多飞"还是"早点收工"的旋钮；`R` 越大（切片越细）→ 覆盖分辨率越高，但 near-RT 一致性下降（论文 §VI-C：`R=4` 是平衡点）。

---

## 4 · 工程视角

| 项目 | 数值（**均逐字来自论文**） |
|---|---|
| UAV 平台 | Crazyflie 2.1，< 100 g |
| 机载算力 | AI-Deck，GAP8 处理器（图像采集+Wi-Fi 推流，已满载） |
| 相机 | 超低功耗，320×320 像素 |
| 通信 | Crazyradio dongle，2.4 GHz ISM（控制）+ ESP32 Wi-Fi（图像） |
| UWB 定位 | Loco UWB (TDoA)，STM32 上 Kalman 滤波，sub-decimeter |
| 光动捕 | OptiTrack，8 红外相机，sub-millimeter GT |
| 基站并行 | near-RT 处理分布在 **4 个专用核** |
| near-RT 单机延迟 | 23.044±9.04 s (baseline) / 23.648±9.99 s (dynamic) |
| near-RT 双机延迟 | 34.756±21.14 s (baseline) / 31.225±13.16 s (dynamic) |
| near-RT 处理延迟（正文陈述） | 约 **25–30 s**；期间 UAV 不降落、慢速绕当前扇区等待新航点 |
| non-RT 单机延迟 | 224 / 237 / 240 / 257 s（baseline / loc-aware / dynamic / integrated） |
| non-RT 双机延迟 | 222 / 217 / 232 / 226 s |
| 触发条件 | ① UAW 离开扇区（约 45 张图）；② 两图间隔超时阈值（最少可至 2 张） |

**Trade-off 解读**：
- **延迟的双峰分布**：延迟 std 很大（±9~±21 s），因为第二种触发条件让批大小从 ~45 张变到最少 2 张 → 延迟测量本身不稳定（论文自述）。
- **反直觉现象**：non-RT 双机（图更多）反而**更快**——因为给 Nerfacto 的图更多，所需迭代次数更少；而 single/dual 内部比较时保持迭代次数恒定，所以动态/集成方案因图多而略慢。
- **部署约束**：机载不跑单目 VO（内存/算力超出 GAP8 上限，GAP8 已被图像+推流占满），**必须依赖外部定位基础设施**——这是本文可用性的最大工程软肋。
- **VRAM / FPS / 推理吞吐**：论文未报告。

---

## 5 · 数据与评测

**数据来源**：无公开 benchmark；两个**自建 3D 打印物体**：
- **小参考物体**：54.7 × 20.3 × 20.9 cm³，带字母与 4 cm 深雕刻（BW 图见 Fig.6a）。
- **大物体**：人体胃肠道的 3D 打印解剖模型，透明聚合物，垂直跨度约 90 cm，光学折射 + 低对比内部特征（RGB 图见 Fig.6c）。

**评测场景设置**：
- 静态实验：UAV 绕物飞，机间约 50 cm，物体离地约 1 m，每机 2–3 圈，约 250 张图。
- 双机：初始对置，同静态轨迹，并发绕飞时 **Δz = 10 cm** 高度差。
- 定位：Loco UWB 与 OptiTrack **各自独立实验序列**，不直接横向比较（物理体积/坐标系不同）。
- 4 维消融（OptiTrack 下）：① 机队规模 (1 vs 2) ② 空间切分 `R ∈ {2,4,6,8}` ③ 流水线 (near-RT SfM vs non-RT NeRF) ④ 位姿来源 (纯 SfM vs OptiTrack 融合)。
- 图像预算敏感性：固定 50 / 100 / 150 / 200 / 250 张。
- **可复现性做法**：先在整个视角体**穷举采集**，动态策略通过对预采集池**主动子采样**评估（用于隔离视角选择的影响）。

**指标（论文定义）**：PSNR、SSIM（-1~1，1 完美）、LPIPS（0 最佳）、HD（Hausdorff，点云最大偏差）、WD（Wasserstein）、Latency、#images taken、#images used。

**代表性数字（逐字）**：
- **图像预算 50 张**：双机动态 SSIM **0.953** / LPIPS **0.141**；单机静态 SSIM **0.930** / LPIPS **0.219**。
- **图像预算 250 张**：双机动态 PSNR **9.177 dB**、SSIM **0.964**、LPIPS **0.088**、HD **0.033**。
- **单机 UWB non-RT**（Table I）：baseline PSNR **7.720** → location-aware **7.817** → dynamic **7.639** → integrated **7.723**。
- **双机 UWB non-RT**（Table II）：integrated PSNR **7.561**（比 baseline 7.651 略降，论文归因于 dual-UAV integrated 在 UWB 下的一致性）。
- **OptiTrack 消融**（Table III）：单机 2-region non-RT，PSNR 8.107（SfM）→ **8.700**（OptiTrack）；双机 4-region non-RT，HD **0.210 → 0.145**。
- **相机模态**（Table IV）：小物体 BW 优于 RGB（near-RT SSIM 0.971 vs 0.968；non-RT 0.984 vs 0.978）；大物体 RGB 反超（near-RT SSIM 0.958 vs 0.929，HD 114.37 vs 182.36；non-RT 0.986 vs 0.949，HD 95.23 vs 129.04）。

> 其余所有表中数字均可回溯至 Tables I–IV；未在正文出现的量（如 VRAM、GPU 型号、FPS）一律「论文未报告」。

---

## 6 · 能力与失败模式

**能做**：
- <100g 微型无人机上完成**闭环主动视角选择**，动态轨迹**一致优于静态**（Tables I/II）。
- location-aware 融合提高**可用图像数**与几何/感知精度。
- 跨物体尺度（小 → 大）、跨模态（BW/RGB）、跨定位（UWB/OptiTrack）自适配。

**不能做 / 具体失败**：
- **near-RT 点云几乎不可辨认**：PSNR 仅 3.295–5.624 dB，论文自述"hardly recognizable to the human eye"，只给粗略轮廓——**只够控制，不够看**。
- **大 / 透明物体几何崩坏**：大物体 HD 高达 182.360 (BW near-RT)、129.036 (BW non-RT)，量级比小物体高 3 个数量级。
- **UWB 无线电干扰**：radio-based 定位性能退化，论文明确说"caused hurdles in UAV control"。
- **dual-UAV integrated 在 UWB 下 PSNR 略降**（Table II 7.651→7.561）。
- **PSNR 对小物体不稳定**（200 张单机动态骤降，论文归因于 2D 图像指标对小尺度 3D 模型不敏感）。
- **无 onboard 定位**：机载不跑 VO，**强依赖外部定位基础设施**。

### 隐含假设 (Hidden Assumptions)

1. **物体静态**且**质心 `C_obj` 已知/可估**——整个 slice/region 划分与 `argmin` 都锚定在质心上。
2. **无人机能绕物做圆周飞行**、物体在相机中始终居中——依赖 yaw 锁定且无遮挡/障碍。
3. **SfM 有足够特征**能出初始点云（bootstrap 需"至少两张有小而非零基线的正面图"引入视差）。
4. **相机安装位置在机队内一致**——location-aware 融合的 scaling/rotation/alignment 才能成立（论文明确要求"mounting position is identical across the fleet"）。
5. **室内、低风、受控环境**——论文在 Future Efforts 中承认微型机抗风差、执行器可能失效、电池/续航严格受限。
6. **无避障**——碰撞避免仅靠"对置起飞 + Δz=10cm + 固定高度偏移"的**空间隔离**，不是感知式避障。
7. **`τ_coverage` 是目标特定的经验阈值**——换物需重调。

---

## 7 · 与相关工作对比

| 维度 | 现有 UAV 重建 | Crazyflie (小物建图)[15] | **本文** |
|---|---|---|---|
| 平台重量 | 907 g–9.5 kg（Mavic Pro 2 / M600 Pro）[13][18]；medium 1.45–3.17 kg [15][5][3] | 微型 | **< 100 g** |
| 目标尺度 | MA（都市）/ LA（大区域） | LA 室内 | **PA（personal-area）静态小物** |
| 载荷 | LiDAR / 双目 / 重载荷 | 极受限 | 单目 320×320 |
| 重建质量 | 高 | 仅 rudimentary | near-RT 粗糙 / non-RT 高保真 |
| 轨迹 | 静态 / 离线主动 | — | **闭环动态（near-RT 反馈）** |
| 定位 | 机载 GNSS/VO | — | 外部 UWB 或光动捕（无 onboard VO） |
| N3DR 选型 | — | — | Nerfacto（前作[8]对比胜过 instant-ngp / Splatfacto） |

**面试 Tip**（被问"这篇和一般 UAV+NeRF 有何不同"）：
> 标准答法是三段——**① 平台**：<100g、单目 320×320，把可行域从 MA/LA 压到 PA；**② 控制**：不是被动飞静态轨迹，而是把 near-RT SfM 点云当覆盖率传感器、`argmin` 补最缺扇区，形成感知-控制闭环；**③ 定位**：不做机载 VO，改用 UWB/OptiTrack 外部定位并融合 SfM 位姿——额外好处是提高可用图像数。**加分点**：主动指出它的可复现评估用"预采集池离线子采样"，以及大/透明物体 HD 崩坏、依赖外部基础设施这两条硬约束。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-18)

**repo 信号核查**：全文中出现的 `github.com` 仅为 arXiv 页面自带的 "Report GitHub Issue" UI 文本，**并非论文给出的官方代码仓库**（论文提及的 Meshroom/AliceVision、Nerfstudio 均为第三方开源，非本文产物）。因此判定为 **无官方 repo 信号**，以下 pitfall 由 §6 失败模式 + 方法约束推导（**未经 issue 验证**）。

1. **相机重装即破坏 location-aware 融合** ⚙
   - §6 隐藏假设 4 + 方法约束：融合靠 Python 脚本对 SfM 位姿与 UAV 坐标做 scaling/rotation/translation 对齐（Fig.3）。论文明确要求"相机安装位置在机队内一致"。
   - 推导失败：换机、补机或机上重装相机 → 两坐标系对齐失效 → N3DR 吃到错位位姿 → HD/清晰度下降（论文自述"misaligned stances 导致 sharpness 下降与 hazy artifacts"）。这是**部署时换件的头号坑**。

2. **UWB 干扰下控制环退化，无 mitigation** 📡
   - §6 失败模式"UWB 无线电干扰导致 control hurdles" + 架构约束：near-RT 航点依赖 UAV 坐标，UWB 退化 → 航点失真 → 覆盖率评估不可信。
   - 推导失败：真实室内多径/共存干扰下，闭环可能"越飞越偏"，且论文未给出干扰检测或回退策略（只列为 Future Work）。

3. **动态轨迹的"可复现"评估是离线子采样，未必反映在线反应** 🔁
   - §5 方法约束："先穷举采集，动态策略通过对预采集池主动子采样评估"。
   - 推导失败：离线子采样隔离了视角选择变量，但**消除了在线的延迟/通信/续航耦合**；真实飞行中 25–30 s near-RT 延迟 + 慢速绕圈会改变可达视点集。因此 Table 中的 dynamic 增益可能**高估**端到端在线表现。

4. **near-RT 延迟测量不可比（批大小可变）** ⏱
   - §4 方法约束：触发条件②允许"最少 2 张图"就触发重建。
   - 推导失败：不同 run 的批大小从 ~45 到 2 张不等 → 延迟 std 巨大（±9~±21 s），**跨方案延迟不可直接比较**，任何"更快/更慢"的结论都需先固定触发策略。

---

[← Back to nerf-family README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（§4/§5 中所有数值均逐字取自 Tables I–IV，未标注者即论文原文；VRAM / GPU 型号 / FPS 论文未报告）

<!-- source: https://arxiv.org/abs/2509.12458 -->
