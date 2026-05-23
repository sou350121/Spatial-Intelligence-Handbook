# Marine（AUV / USV）— 着陆页

**Status:** v1 — opinionated index. 商用 AUV / DVL 规格标 `UNVERIFIED`。
**TL;DR:** Marine 是这本手册里的*压力测试* embodiment。视觉为主的空间 AI 默默依赖的每一个假设——可用纹理、单目从视差恢复尺度、GPS 作为度量锚、低动态介质——在水下都会崩。我们写 marine 不是因为有大量 marine SLAM 论文（没有），而是因为它在反面定义了：视觉前馈 3D *能*做什么、*不能*做什么。

---

## 1 · 为什么 marine 是最干净的反面案例

挑过去三年任何一项空间 AI 主张——VGGT、depth foundation model、3DGS、dense BEV——然后问一句："在 30 m 深、能见度 3 m 的浑浊水里、前向 LED 照明，这玩意能用吗？"答案几乎总是不能；而原因和模型架构无关，全在介质：

| 失败模式 | 物理原因 | 对视觉 SLAM 的后果 |
|---|---|---|
| **吸收** | 水对红色波段吸收最快；>10 m 后所有东西都偏绿蓝 | 光度损失有系统偏置；在 RGB 上训练的 descriptor 失效 |
| **散射** | 悬浮颗粒造成 backscatter；LED 越亮越糟 | 前向照明的场景出现"前灯光晕"，纹理被毁 |
| **能见度低** | 沿岸 / 浑水里 <5 m 是常态 | 特征跟踪距离骤降；loop closure 几乎不可能 |
| **GPS 失效** | RF 不在水下传播 | 没有度量锚；单目尺度真正不可恢复 |
| **动态介质** | 水流让载体和场景独立移动 | 大多数 SLAM 栈的静态世界假设崩 |
| **舱壁折射** | 平面 port 造成与波长相关的畸变 | 标准针孔内参错；标定必须包含水侧折射 |

这就是为什么 marine SLAM 栈和 aerial / AD 栈长得完全不同。主传感器是**声学的，不是光学的**：

- **DVL（Doppler Velocity Log）**——用声学 Doppler 回波测量对地速度；marine 版的 GNSS 做 dead-reckoning
- **Multibeam / side-scan sonar**——marine 版的 LiDAR，用来做环境建图
- **压力传感器**——绝对深度，比任何视觉线索都可靠
- **相机**——*辅助*，只在近距离 + 良好能见度下有用

Cross-reference：这正是 [crossing/slam-vio-migration/vggt_vs_drone_vio.md](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) §6 末尾讨论的失败模式。Marine 就是那篇文档把 VGGT 与 VIO 同时判负的原因。

---

## 2 · 为什么本手册仍要保留 marine

论文量小，但仍然值得留这一章，三个理由：

1. **边界定义。** 当读者问"空间 AI 哪里都能用吗？"，marine 是诚实的答案。它是单目视觉前馈 3D 极限被毫不含糊暴露的 embodiment。
2. **传感器多样性。** Marine 是手册里唯一以*声学*作为主导 3D 模态（不是光学也不是 RF）的 embodiment。把 sonar 流水线和 LiDAR 流水线放在一起对比，对 sensor-physics 轴是真正有教学价值的。
3. **近距离 photogrammetry 案例。** 能见度允许时（<5 m、光照可控），水下 photogrammetry——包括 3DGS 与前馈 3D——*是*能跑的；把它跑起来所需的工程套件（照明、色彩校正、折射感知标定）本身就是部署主义的可迁移课程。

---

## 3 · 子领域地图

| 子领域 | Status | Doc |
|---|---|---|
| Underwater SLAM 栈（DVL + sonar + IMU + 辅助相机） | v1 draft | [underwater_slam_dvl_sonar.md](underwater_slam_dvl_sonar.md) |
| Sonar 基础与物理 | `TBD` — 交叉到 `foundations/sensor-physics/` | — |
| Underwater photogrammetry + 3DGS | `TBD` — wedge 候选 | — |
| Marine benchmarks（AQUALOC、SubPipe、MIMIR 等） | `TBD` | — |
| ROV / AUV / USV / glider 分类 | `TBD` | — |

Marine 在本手册中**有意不做深度锚**（★）。Aerial 是维护者的锚点；marine 是反面案例。我们追求一两篇过硬的 wedge 文档，而不是覆盖面。

---

## 4 · Cross-references

- 这一节的动机来源 → [crossing/slam-vio-migration/vggt_vs_drone_vio.md](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) §6
- 水下光学作为 sensor-physics → [foundations/sensor-physics/](../../foundations/sensor-physics/)（声学 + 水下光学条目 `TBD`）
- 跨 embodiment 尺度叙事（DVL 在 GNSS 失效场景下提供度量）→ [crossing/scale-and-metric/](../../crossing/) `TBD`
- 跨 embodiment 失败模式 → [deployment/failure-modes/](../../deployment/failure-modes/)

---

## 5 · 给不同读者

- **Marine 工程师** —— 本手册不是你的主参考。我们把你的领域当作跨 embodiment 矩阵里的一列。Marine 深度文献在 IEEE OES、ICRA marine workshop、OCEANS 会议里。
- **Aerial / manipulation 工程师** —— 来这一节的目的是学*不要*假设什么。如果你的方法依赖稠密纹理、单目视差、或 RGB 光度损失，marine 告诉你这些假设崩掉是什么样。
- **研究者** —— 这里有一个小而真实的 wedge：*从 sonar 的跨模态前馈 3D*。一个吃 sonar imagery + RGB、产出 3D 的 VGGT-equivalent 会很重要。目前不存在。

---

## Boundary

本页把 marine 作为视觉空间 AI 的*反面案例*来索引。Marine 深度文献、AUV 任务规划、海洋控制、海洋学整合、海军应用均不在范围内。唯一一篇 deep 文件是 [underwater_slam_dvl_sonar.md](underwater_slam_dvl_sonar.md)；sonar 物理在 `foundations/sensor-physics/` 写成时归那里。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
