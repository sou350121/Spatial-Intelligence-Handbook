# Apple Vision Pro — 这套空间栈，恰好不是机器人栈

**Status:** v1 — opinionated draft。Apple 内部规格 `UNVERIFIED`（无 datasheet 披露，数字来自拆解 + WWDC 反推）。
**TL;DR:** Apple Vision Pro 是目前已上市最激进的消费级空间感知栈 —— 端到端 inside-out 追踪、密集手部追踪、持久空间锚点，全部在设备本地。**它*不是*机器人栈**，因为用户是人类，优化目标完全不同（运动顺滑 vs 控制环带宽、舒适度 vs 度量尺度还原）。但 SLAM / 手部追踪 / 锚点的血脉可复用，**940 nm 传感器选型**是 850 nm 机器人惯例最干净的反例 —— 两者都对，理由不同。

---

## 1 · 为什么手册要写它

幼稚读法是把 Vision Pro 当「消费 AR，不是机器人」打发。这错了两遍：(a) 工程原语 —— inside-out 6-DoF 追踪、亚厘米手部姿态、世界锚定持久化 —— 正是人形或腕载相机机械臂需要的原语；(b) Apple 的**传感器选型**（940 nm 结构光 + 940 nm ToF + 全局快门立体）是「在 eye-safety / QE / range 权衡的另一端做优化」最干净的工作例。

只看机器人源资料，你永远看不到 940 nm 被论证。本文就是它被论证的地方 —— 也是「到机器人这条边界」被明确画出的地方。

---

## 2 · 已上市的空间栈（从拆解 + WWDC 反推）

| 子系统 | 干啥 | 传感器 / 来源 `UNVERIFIED` |
|---|---|---|
| Inside-out 6-DoF 追踪 | 头戴端世界位姿，无外部基站 | 6× 追踪相机（单色，全局快门）+ IMU |
| Stereo depth | 给遮挡 + 重建提供密集深度 | 2× 下视立体相机 + ToF（继承 iPad Pro LiDAR scanner）|
| 手部追踪 | 每手 26-DoF 亚厘米姿态 | 追踪相机 + 设备端 NN |
| 眼动追踪 | 视线方向亚度精度 | 2× IR 眼部相机 + 940 nm 照明（每眼）|
| 空间锚点 | 跨会话持久放置 | ARKit 锚图，设备端 |
| 算力 | M2 + R1 双芯片；R1 专用传感器融合 | Apple SoC |

**R1 芯片**值得多停一下。它是协处理器，全职任务就是把 photon-to-pixel-to-display 延迟压在「人类感知到运动病」阈值（~12 ms `UNVERIFIED`）以下。这比 200 Hz 无人机控制器需要的（~5 ms 端到端是*飞行稳定*预算，不是「骗过生物学」预算）紧一个数量级。Apple 的延迟预算是心理物理学；无人机的是动力学。**同一个数字，相反的理由。** 见 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`。

---

## 3 · 为什么 940 nm —— 而它是*对的*，即便机器人选 850 nm

这是传感器物理一篇最干净的教学案例。Apple 全套主动 NIR —— 眼动、LiDAR scanner 提供的手部区域深度、结构光近亲 —— 都收敛到 **940 nm**。物理层论证在：

→ [`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`](../foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md)

一段话版：850 nm 在机器人侧胜出，因为照明器是*脉冲式*（duty <10 ms），你可以拉高功率、找回硅 QE（~40-50%），用均值约束通过 IEC 60825-1 Class 1。Apple 是把设备戴在人脸上，眼动照明器只要戴着就*持续*亮。连续照明叠加累积剂量预算；唯一逃逸路径是搬到 **940 nm 水吸收谷** —— 环境光更低（更低输出就有更好 SNR），眼安全 MPE 也松约 2×。Apple 付了大概 2× 的 QE 税（`UNVERIFIED` 准确比值看传感器）来买这个安全预算。

**这不是机器人设计**。一个持续主动感知 8 小时、对着同事眼睛的机器人会撞上同样的权衡 —— 这就是为什么常驻仓库的机器人，做持续主动感知的也倾向 940 nm。边界不是「消费 vs 机器人」，而是「脉冲 vs 连续」。Vision Pro 是最干净的工作例。

---

## 4 · 哪些原语 *可* 复用到机器人

| Apple 原语 | 机器人侧复用 | 哪里要变 |
|---|---|---|
| Inside-out 6-DoF 追踪 | 腕相机 VIO、人形头部 SLAM | 更高速率（200 Hz vs 60-90 Hz 舒适目标）；需要度量尺度 |
| 密集手部追踪 | 机械臂手指追踪、teleop 接口 | 拓扑不同（夹爪而非五指）；回归 NN 架构可迁移 |
| 空间锚点 | 机器人持久地图记忆 | 需要把锚图作为 API 暴露；ARKit 不会 |
| 眼动追踪 | 司机注意监控、teleop 注意力 | 干净迁移 —— 部署不同，原语相同 |
| Stereo + ToF 融合 | 室内移动机器人深度 | 调高运动 / 视野后可用 |

Apple 所在的深度基础 / SLAM 血脉**就是 Skydio + 机械臂的同一血脉**。不可复用的是*系统级优化*：舒适度优先于延迟、优先于度量尺度精度、优先于机器人级可靠性。

---

## 5 · 为什么它*不是*机器人栈（边界）

三个不可化简的失配：

**(a) 用户是人类。** 每个选择都从这里级联。显示延迟预算由人类感知阈值决定；传感器位置由人类工效学决定；电池和重量由人能在脸上耐受的程度决定。机器人这些约束都没有，反而有 Apple 完全忽略的约束（振动、桨流、粉尘进入、IK 感知的传感器布置）。

**(b) 任意场景的度量尺度无保证。** ARKit 锚点是*自洽的* —— 同一会话内相对几何对 —— 但系统并不为跨重定位的真实绝对尺度调过。机器人要做接触力感知操作，绝对尺度误差要 <2%；AR 级一致性松了两个数量级。

**(c) 闭合 API 表面。** 完整传感流、原生速率 IMU、原始点云 —— Apple 开发者 API 都没暴露。机器人工程师没办法把 Vision Pro 接到机器人上当传感器栈。这不是疏漏，是战略边界。

---

## 6 · 可证伪预测

到 2027-12，**不会有任何量产机器人系统**把 Vision Pro（或 Apple 授权的 Vision-Pro 衍生模组）作为主感知栈。会有 teleop / 动捕*应用*（操作员戴头戴，机器人映射） —— 那不算。如果 Apple 开了「AVP for Robotics」SDK 暴露原生速率 IMU + 相机流，此预测翻盘。

---

## 7 · 给不同读者的判读

- **机械臂工程师** —— 手部追踪血脉迁到你的腕相机；传感器选型*不*迁（你要 850 nm 脉冲）。读 §3 + §4。
- **航拍工程师** —— 飞行栈无关；§2 的延迟论证是和你 5 ms 预算的有用对照。
- **人形工程师** —— 最相关：inside-out 追踪 + 手部追踪正是你要的头 + 机械臂原语。R1 延迟预算工程是这堂课。
- **VLA 研究者** —— 空间锚点 / 持久记忆原语是 `bridge-to-vla/` 中「神经地图记忆」最近的商业类比。
- **传感器选型者** —— 读 §3 与链接的传感器物理文档。850-vs-940 是*那道*典型工作例。

---

## References

- Apple Vision Pro hardware overview — https://www.apple.com/apple-vision-pro/specs/
- Apple WWDC 2023/2024 ARKit sessions — https://developer.apple.com/visionos/
- iFixit Vision Pro 拆解 — https://www.ifixit.com/News/95869/apples-vision-pro-teardown `UNVERIFIED — 第三方逆向`
- IEC 60825-1 激光产品安全 — https://webstore.iec.ch/publication/3587
- 配套：[`foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md`](../foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md)
- 配套对照：[`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../crossing/slam-vio-migration/vggt_vs_drone_vio.md)

## Boundary

本文是 Apple 空间栈的**公司 / 产品层读法**。传感波段物理（为何 940 nm）在 `foundations/sensor-physics/`。SLAM / VIO 方法在 `foundations/feed-forward-3d/` 或 `crossing/slam-vio-migration/`。同原语在机器人侧的应用属于 `embodiments/humanoid-legged/` 或 `embodiments/manipulation/`，不在此。

---

## 🤖 Moltbot Updates

<!-- Moltbot appends release / news entries below this line. Format: YYYY-MM-DD — one-line event — source URL. -->
