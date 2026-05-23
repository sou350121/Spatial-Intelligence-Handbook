# 水下 SLAM —— DVL、Sonar，以及相机能帮到哪里

**Status:** v1 — opinionated draft. 商用 AUV / DVL / sonar 规格标 `UNVERIFIED`。
**TL;DR:** 把 GNSS 换成 DVL、LiDAR 换成 multibeam sonar，再把相机从主传感器降为偶尔辅助，水下状态估计的架构其实就是 aerial VIO。视觉 SLAM 只在 &lt;5 m 距离 + 清水 + 可控照明下能用，而且此时它是 photogrammetry，不是在线 VIO。本文对全手册的可迁移结论是："先选传感器、再选模型" 胜过 "先选模型、再补传感器"。

---

## 1 · Marine 传感器栈

| 传感器 | 作用 | 对应 marine 类比 | 典型规格 `UNVERIFIED` |
|---|---|---|---|
| **DVL（Doppler Velocity Log）** | 用 4 束斜向声波 Doppler 回波测对地速度 | GNSS（做 dead-reckoning） | 0.2% 行程漂移；400 kHz / 600 kHz / 1200 kHz 消费到研究级；~30–200 m 离底高度上限 |
| **Multibeam sonar (MBES)** | 前视 / 下视扇区测深 | LiDAR（做 3D 建图） | 200–400 kHz 典型；1° 波束宽；50–200 m 距离 |
| **Side-scan sonar** | 拖曳 / 船壳后向散射成像 | aerial side-looking radar | 100–900 kHz；高分辨率 2D 图像，不是 3D |
| **Mechanical scanning sonar** | 单波束机械扫描，低成本 | "旋转 LiDAR" 类比 | 50–500 kHz；便宜，慢 |
| **IMU + magnetometer (AHRS)** | 姿态与短时积分 | 同 aerial IMU | 低成本 AUV 用 MEMS；测量级用 FOG `UNVERIFIED` |
| **压力传感器** | 绝对深度（水柱压） | 气压高度计 | &lt;1 cm 分辨率；船上最可靠的传感器 |
| **USBL / LBL** | 用水面或海底应答器做声学定位 | GNSS-RTK 的声学版 | 米级精度；需要水面船或预布信标 |
| **RGB 相机 + LED 照明** | 近距离视觉检视 | 可见光相机，同 aerial | 清水 &lt;5 m 有用；>10 m 或浑水无用 |

定义性的差异在 **DVL**。一旦有了一个能在已知坐标系里测对地速度、且漂移 0.2% 的传感器，就能在不需要外部辅助的情况下连续数小时做测绘级 dead-reckoning。这就是 marine 载体能跑数小时无 GNSS 任务、aerial 载体不能的原因。

---

## 2 · 经典 AUV 状态估计架构

```
                ┌──────────────────────────┐
   压力 ──────► │                          │
   AHRS ──────► │   EKF / Factor graph     │ ──► 位置 / 速度 / 姿态
   DVL ───────► │   (tightly coupled)      │     10–50 Hz
   USBL ──────► │                          │
   IMU ───────► │                          │
                └──────────────────────────┘
                          ▲
                          │ （可选辅助）
                          │
                ┌──────────────────────────┐
   MBES ──────► │  Bathymetric SLAM        │ ──► 通过地形匹配
   近距相机 ──► │  / loop closure          │     纠正漂移
                └──────────────────────────┘
```

结构上和 aerial VIO 是同构的，只是上文那些替换。主要架构差异：

- **运行频率更低**：10–50 Hz 是常态，aerial 通常 200 Hz。AUV 不需要快速控制——它走 &lt;2 m/s，动力学慢。
- **Loop closure 走的是 bathymetry，不是视觉 descriptor。** Terrain-aided navigation 把测得的一条海底深度 swath 匹配到先验地图。
- **USBL / LBL 辅助间歇且声学慢。** 一次 USBL 更新可能每 1–5 秒来一次、米级不确定度——能限漂，不能用来做控制。

公开 / 开源 / 可参考栈：BlueROV2 + WaterLinked DVL-A50 社区栈、OceanGate 类载体 `UNVERIFIED`、Bluefin / Hydroid Remus 测绘 AUV（商用）、来自 MBARI / WHOI / NTNU / Heriot-Watt 的研究栈。

---

## 3 · 为什么经典视觉 SLAM 在水下失败

视觉 SLAM（ORB-SLAM3、DSO、VINS-Fusion、DROID-SLAM、甚至 VGGT）四个假设全部不成立：

| 假设 | 水下现实 |
|---|---|
| RGB descriptor 在光照变化下大致稳定 | 与波长相关的吸收 ~5 m 外就毁掉色彩恒常性 |
| 介质在工作距离内光学清澈 | 散射在沿岸水域 ~2 m 外就是主导噪声 |
| 单目尺度可通过视差恢复 | 视差本身没问题，但特征轨迹太短，还没三角化就丢了 |
| 场景近似静态 | 水流、生物场景（鱼、海带）、气泡极其严重违反此假设 |

结果：在 TUM-RGBD 或 EuRoC 上完美跑通的视觉 SLAM 栈，在 AQUALOC `UNVERIFIED` 及类似水下基准上 trajectory completion 掉到 &lt;30%。不是方法烂，是介质烂。

### VGGT 这类前馈 3D 怎么办？

VGGT 继承同一组失败。它是单目 RGB 前馈模型，无法在介质已经摧毁特征的地方制造特征。截至 2026-05，还没有公开评测 VGGT 在 AUV 影像上的工作；先验是它会因为和 ORB-SLAM3 同样的原因失败。**Cross-reference：** [crossing/slam-vio-migration/vggt_vs_drone_vio.md](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) §6 已经下了这个判断。

真正有意思的开放问题是：在 *sonar* 影像上训练的前馈 3D 模型能否成为 marine 版 VGGT。Sonar 图像在纹理上完全不同（speckle、距离相关强度、窄波束），但 *N 视角 → 稠密 3D* 的架构模式原则上是同一套。这种模型目前不存在。

---

## 4 · 视觉 photogrammetry *能*用的场景

诚实版本：水下视觉 photogrammetry——包括 3DGS——在近距离 + 可控条件下是能用的：

- 距离 &lt;5 m（通常 &lt;3 m）
- 多角度人工照明以最小化 backscatter
- 色彩校正或学习 albedo 以恢复 descriptor
- 多数情况是离线（任务后），不是在线

今天已经上岗的用例：考古测绘、珊瑚礁监测、船体检视、基础设施检视（管道、油气平台）。立体 + 结构光的变体也在此范围内能用。

相关基准文献：

- **AQUALOC**（Ferrera et al. 2019）—— IROS / IJRR；考古 + 港口场景的视觉惯性 SLAM 基准。https://arxiv.org/abs/1908.06846
- **SubPipe** —— 较新（2023+）的管道检视 AUV 数据集。`UNVERIFIED` 主引用
- **MIMIR-UW** —— 仿真 + 实测水下数据集。`UNVERIFIED`
- **UWVE** —— 不同团队的水下视觉惯性数据集；统一基准 `TBD`

这个 regime 下的性能数字不可外推到一般 AUV 任务——它们描述的是*视觉友好*的工作包络，不是中位部署。

---

## 5 · 对全手册的可迁移结论

Marine 给出的最大教训是 **sensor-first design**：

- Marine 社区花了 30 年工程化 DVL + 声学定位，"AI" 还没进场。结果是稳健、能连续数小时的任务。
- Aerial 社区花了 ~10 年工程化高频率 IMU + 视觉栈才有可靠 VIO。同一个模式。
- Manipulation 社区现在正在用 tactile + 近距 depth 走同一遍。

**方法是传感器选择的下游产物。** 任何假设 RGB-first 的跨 embodiment 空间模型在 marine 上会失败；任何以 sensor modality 为条件的模型有机会。

这是本手册支持把 `foundations/sensor-physics/` 当作一等公民轴的最强论据。Cross-reference：[foundations/sensor-physics/](../../foundations/sensor-physics/)。

---

## 6 · 2-year outlook + 可证伪预测

**可证伪预测：** 到 2027-12 前，不会出现一篇 published 工作，能在原始 sonar 图像（multibeam 或 side-scan）上以 AUV 量级运行前馈 3D 模型、并在公开基准上明显胜过 DVL + EKF。若出现，将是重大事件，并重写跨模态叙事。

次要预测：近距离（&lt;5 m + 可控照明）水下 3DGS 重建到 2027 会在考古 / 检视流程里达到生产级。AUV 任务尺度的实时在线水下 3DGS 不会。

---

## For the reader

- **AUV / marine 工程师** —— 这里几乎没新东西。本文留下来是给 aerial / manipulation 读者的*教学参考*。
- **Aerial / VIO 工程师** —— 读 §1 与 §3。"用 DVL 替代 GNSS" 是"如果 RF 不传播，我的栈长什么样"的最清晰心智模型。
- **研究者** —— §5 指出的 wedge：从 sonar 出发的前馈 3D。谁先发，谁就掌握未来十年 marine 空间 AI 的话语权。

---

## References (starter set)

- AQUALOC — Ferrera et al., *IJRR 2019*. https://arxiv.org/abs/1908.06846
- ORB-SLAM3 — Campos et al., *T-RO 2021*. https://arxiv.org/abs/2007.11898
- WaterLinked DVL-A50 datasheet — 厂商页面. `UNVERIFIED, no DOI`
- BlueROV2 社区导航栈 — https://www.bluerobotics.com/
- Terrain-aided navigation survey — Donovan, *J. Field Robotics* 2012. `UNVERIFIED` 引用
- Underwater visual SLAM survey — Joshi et al. 或类似 IROS / OCEANS 篇目. `UNVERIFIED`

## Boundary

本文把水下 SLAM 作为视觉空间 AI 的*反面案例*。AUV 任务规划、控制、海洋生物应用、sonar 信号处理内部、海军作战均不在范围内。Sonar 物理在 [foundations/sensor-physics/](../../foundations/sensor-physics/) 写成时归那里。水下 photogrammetry / 3DGS 值得一篇独立 wedge 文档，当前 `TBD`。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
