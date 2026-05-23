# BEV 与 Occupancy Networks — AD 之外能用到什么

**Status:** v1 — 带立场的初稿。AD 栈内部细节标 `UNVERIFIED`。
**TL;DR:** BEV lift 与稠密 occupancy network，是 AD 栈里**够格进本手册**的两块。BEV 干净地迁到地面移动，迁到低空巡检很别扭，基本迁不进操作。Occupancy network 反过来 —— 这种表征恰好是操作一直想要的，但 AD 尺度的参数在两到三个数量级上是错的。

---

## 1 · BEV 为什么打赢前视图（以及为什么这对 AD 之外也重要）

2020 年之前，AD 感知是「逐相机、前视、2D bbox 优先、后期几何融合」。2020–2022 转向 BEV —— 把各相机特征 lift 进一个共享俯视栅格，然后在栅格里做检测 / 分割 / 跟踪 —— 现在是共识。

它赢的理由**不是 AD 专属**：

1. **多相机融合在 BEV 里是免费的。** 不用跨相机做 bbox 关联，栅格几何地把它们对上了。
2. **时序融合在 BEV 里是免费的。** 自车运动只是一次刚体变换，多帧叠加不需要跟踪器。
3. **规划天然吃 BEV。** Cost map、occupancy grid、路径都是俯视的，没有投影步骤。
4. **它是自监督的干净目标。** 用未来帧的日志渲一张 BEV，从当前帧预测它 —— 下文所有驾驶 world model 的根基都在这里。

第 1–3 点是 AD 形状的；第 4 点才是真正可推广的那条。

### 谱系压缩版

| 论文 / 系统 | 年份 | 动作 | 意义 |
|---|---|---|---|
| **LSS**（Lift-Splat-Shoot，Philion & Fidler） | 2020 | 逐相机深度分布 → splat 进 BEV | 下面所有方法都建在这次几何 lift 上 |
| **BEVFormer**（Li et al.） | 2022 | 从 BEV query 到图像特征的可变形 cross-attention | BEV 从 2D conv 栅格变成 transformer 查询域 |
| **BEVDepth**（Li et al.） | 2022 | 在 LSS lift 上加显式深度监督 | 补上 LSS 的精度短板 |
| **BEVFusion**（Liu et al.） | 2022 | 用同一个 BEV 栅格做 LiDAR + 相机融合目标 | LiDAR-相机融合终于有了干净的共同空间 |
| **Tesla AI Day "occupancy network"** | 2022 | 把 3D voxel occupancy 当感知输出，不再用 3D bbox | 从 2.5D BEV 跳到真正的 3D；架构细节 `UNVERIFIED` |

Tesla 那次是讲座不是论文，学界的复现（OccNet、OccFormer、SurroundOcc、TPVFormer，都是 2023）才是领域真在读的东西。Tesla 原始架构的细节至今 `UNVERIFIED`。

---

## 2 · Occupancy networks — 操作领域真该看一眼的部分

把感知输出从「3D bbox 列表」换成「occupancy + 语义 + （可选）flow 的 voxel 网格」，意义远超 AD。原因：

- 3D bbox 没法表达悬挂的电缆、半开的门、可变形袋子、树枝；voxel 网格可以。
- 在 occupancy 上做规划对不确定性更诚实 —— 你可以带逐 voxel 概率，而不是二值「存在 / 不存在」。
- 它跟前馈 3D（VGGT 这一类）输出干净地组合 —— 那些也是逐像素 / 逐 voxel 的稠密输出。
- 它更接近人形 / 操作栈做接触推理时真正需要的东西。

### 迁移表

| 领域 | 常用 voxel 分辨率 | AD 尺度 occupancy 是否合身 | 原因 |
|---|---|---|---|
| AD 高速 | 0.4 m × 0.4 m × 0.4 m，200 m × 200 m 范围 `UNVERIFIED` | ✅ 原生 | 几何匹配 |
| 地面移动（AGV） | 0.1 m 栅格，30 m 范围 | ✅ 同思路，更小 | 直接移植，voxel 数量减少 |
| 低空巡检（慢） | 0.05–0.1 m 栅格，3D 100 m 范围 | ⚠️ 没有地面 | 需要直接 3D occupancy，跳过 BEV 步骤 |
| 桌面操作 | 2–5 mm 栅格，1 m 范围 | ⚠️ **思路**对，**参数**错 | AD 的 occupancy network 没为 5 mm voxel 设计过 |
| 海事 AUV | 0.5–2 m 栅格，声呐来 | ❌ 输入模态不同 | 声呐 occupancy 是另一条谱系 |

诚实点说：**表征可迁移，模型权重不可迁移**。目前还没有跨载体可用的「occupancy network 基础模型」。谁先做出来，谁就拿到楔子 —— 见 §6。

---

## 3 · BEV 在哪里**迁不动**

BEV 的根设定是「主导地面」。三个让它崩的载体：

- **低空巡检** —— 无人机绕风机或桥底飞时，相机 FOV 里没有有意义的地面，自然表征是直接做 3D occupancy（跳过 BEV）。
- **操作** —— 工作区里没有「地面」概念，桌面只是众多表面之一，BEV 投影根本不对。
- **室内移动（人形、地面）** —— BEV 在概念上还活着，但分辨率 / 范围跟 AD 差太多，网络无论如何要重写。Lift 代码能复用，架构和训练数据不能。

水下是特例，见 [embodiments/marine/](../marine/overview.md)：有时候有类似地面的海床，但视觉 BEV 扛不住光学衰减；声呐版「BEV」存在但走另一条管线。

---

## 4 · World model 这条线（一段话指针）

驾驶日志预训练的视频 / world model（Cosmos、Wayve 的 GAIA-1 / GAIA-2、DriveDreamer、MagicDrive、Vista），可以说是 AD 给整个载体世界产出的**最重要迁移品**。它们以 action 为条件预测未来 BEV / 未来视频 —— 这恰恰是操作和低空想要、但自己没法大规模预训出来的「world model」。驾驶有数据。它对「前向 + 铺装」的偏置是真的，但对 fine-tune 不致命。

深度内容在 [companies/nvidia_cosmos.md](../../companies/nvidia_cosmos.md) 和 [companies/wayve_world_model.md](../../companies/wayve_world_model.md)，这里不重复。

---

## 5 · 哪里会坏（值得知道的失败模式）

- **FOV 边缘的 BEV** —— 前方 ≥80 m 的特征每 voxel 只对应极少像素，不确定性校准很差，量产栈也没解决 `UNVERIFIED`。
- **低对比度下的 occupancy** —— 黄昏的黑车、贴天空的白卡。深度分布 lift 会双峰，splat 糊掉。AD 的解法是多模态融合（LiDAR / 雷达）；纯视觉载体继承了这个未解问题。
- **时序闪烁** —— 没有显式跟踪器的逐帧 occupancy 会闪，看视频没事但规划很糟糕。补一个小的时序平滑 / flow head 就行，2023 年后普及。

---

## 6 · 两年展望 + 可证伪预测

真正有意思的问题是：会不会出现一个跨载体的 occupancy network 基础模型。两件事得同时发生：

1. 一个混合了 AD 尺度 + 室内 + 操作尺度 occupancy 的训练集，分辨率各自合适
2. 一种坐标 / 尺度条件化机制，让同一个网络处理 5 mm voxel 和 0.4 m voxel

两件都可做，截至 2026-05 都还没论文。

**可证伪预测：** 到 2027-12 前，至少会有一篇论文宣称用一组共享权重处理 {AD 尺度、AGV 尺度、操作尺度} 中 ≥2 项的 occupancy 网络。它会是研究演示，不是量产栈。2026 年内任何「统一量产级 occupancy 基础模型」的宣称都该反向押注。

---

## 给不同读者

- **AD 工程师** —— 你不会从这里学到新东西。本手册留这一篇当**迁移参考**给别的载体。
- **操作工程师** —— 读 §2。Occupancy-as-output 的提法比 bbox-as-output 更对你的胃口。AD 参数错，提法对。
- **低空工程师** —— 跳过 BEV，直接上 3D occupancy。LSS 的某些部分（深度分布 lift）逐相机还是好用。
- **研究者** —— §6 是个开口的楔子。跨载体 occupancy 基础模型是下一篇明摆着的论文。

---

## 参考资料（起步集）

- LSS — Philion & Fidler, *ECCV 2020*。https://arxiv.org/abs/2008.05711
- BEVFormer — Li et al., *ECCV 2022*。https://arxiv.org/abs/2203.17270
- BEVDepth — Li et al., *AAAI 2023*。https://arxiv.org/abs/2206.10092
- BEVFusion — Liu et al., *ICRA 2023*。https://arxiv.org/abs/2205.13542
- OccFormer — Zhang et al., *ICCV 2023*。https://arxiv.org/abs/2304.05316
- TPVFormer — Huang et al., *CVPR 2023*。https://arxiv.org/abs/2302.07817
- SurroundOcc — Wei et al., *ICCV 2023*。https://arxiv.org/abs/2303.09551
- Tesla AI Day 2022 — 讲座，无论文。https://www.youtube.com/watch?v=ODSJsviD_SU
- Planning-oriented Autonomous Driving（UniAD） — Hu et al., *CVPR 2023 Best Paper*。https://arxiv.org/abs/2212.10156

## Boundary

本文只覆盖 BEV + occupancy 作为**可迁移空间原语**。完整 AD 感知栈架构、规划集成、OEM 专属实现都不在范围内 —— 去看 AD 专属综述。驾驶 world model 归 [companies/](../../companies/)（Cosmos、Wayve），这里只指针，不复制。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
