# 空中主动跟踪 / Aerial Active Tracking — Skydio 与 DJI 反向工程

**Status:** v1 — 主观立场草稿，**由博客、产品行为、第三方实测反向工程而来**。Skydio 和 DJI 跟踪栈均无第一方论文；除明确引用外，所有内部架构断言均标 `UNVERIFIED`。
**Depth tier:** 🌬️ 维护者锚点（比其他实体轴深 1.5–2×）。
**TL;DR:** 主动跟踪是空中自主面向消费者的可见面。Skydio ActiveTrack 与 DJI ActiveTrack 都是**单目 RGB + IMU +（仅 Skydio）下视 stereo / TOF** 的栈，在板载以约 30 Hz 运行重识别 + 短时轨迹预测。难点**不**在检测——而在**遮挡恢复、拥挤场景目标消歧、目标运动向量超出无人机可行域时的优雅失败**。反向工程的共识：Skydio 用 6 颗环视相机 + planner 深度集成；DJI 用更少相机 + 更宽松的失败模式（"丢目标，悬停"）。两家都没发论文；都能从实测推断。

---

## 1 · 产品框架

一架无人机"主动跟踪"目标，意味着：(a) 识别感兴趣主体，(b) 在遮挡 / 场景变化中保持视觉锁定，(c) 规划轨迹同时把主体保持在画面里 *且* 自身安全，(d) 在消费级电影摄影速度（2–8 m/s）下无需操作员干预完成上述。前三点是感知 + 状态估计问题；第四点让主动跟踪不同于通用目标跟踪——**跟踪器驱动的是平台，不只是相机**。

这是 AD 以外"空间智能"最干净的商业应用。已大规模出货（Skydio 2+ / X10、DJI Mini 4 Pro / Mavic 3 / Avata），且营销与实地表现之间的差距小到可以坦诚讨论。

---

## 2 · 反向工程的感知栈

可从产品行为与公开工程记录推断：

| Layer | Skydio (反向工程) | DJI (反向工程) |
|---|---|---|
| Cameras | 6× navigation cameras（全环视）+ 4K cinema cam | 前视 + 下视 + 侧视；型号不同（2–6 cams） |
| Active depth | 下视 stereo + 可能的 TOF 地面参考 `UNVERIFIED` | 下视 stereo + 高端 SKU 前视 stereo（APAS） |
| IMU | 1 kHz 工业级 IMU（机械隔振） `UNVERIFIED` | 同档 `UNVERIFIED` |
| GNSS | 有（户外锁定 + 返航），**不用于跟踪** | 同——仅 RTH，不用于主体定位 |
| Subject detector | 板载 CNN，person + vehicle 类别，~30 Hz `UNVERIFIED` | 同家族；DJI "Spotlight / ActiveTrack 360°" 暗示专用跟踪网 |
| 遮挡 Re-ID | 可能是外观 + 运动模型融合（Kalman + ReID embedding） `UNVERIFIED` | 类似；实测在长遮挡上更弱 |
| 轨迹预测 | 短时（1–2 s）目标速度模型 | 时长更短；重获取不那么激进 |
| Planner 集成 | 紧——Skydio planner 把目标预测位置作为软成本 | 松——DJI 倾向"丢则悬停"，预判更少 |

两种设计哲学在失败模式上可见（下节）。

---

## 3 · 真正的难题（以及两栈差异）

### 3.1 遮挡恢复

当树、建筑拐角、人群成员瞬间遮挡主体时：

- **Skydio 行为**：用目标最后已知速度预测再出现点，把画面保持在该点，外观 embedding 匹配后恢复锁定 `UNVERIFIED`。实测在 1–3 s 遮挡下常常恢复成功。
- **DJI 行为**：倾向停止跟踪、悬停，Mavic 级硬件需手动重点选。新 SKU 的 ActiveTrack 360° 改善了这一点但仍不如 Skydio 预测性恢复激进。

### 3.2 拥挤场景目标消歧

如果两个穿着相似的主体交叉：

- 两个栈都依赖外观 embedding（可能是 metric-learned ReID head）。两者失败方式与当前 ReID SOTA 文献一致：5+ m 距离、同衣同姿态的目标用单目 RGB 不可分。
- 实地共识：Skydio 在交叉通过时保持正确主体约 60–80% `UNVERIFIED, 实测来源`；DJI 更低。
- 两栈都不用人脸识别（可能因隐私 + 算力）；基于人脸的 ReID 能补一部分缺口，但两家都不出。

### 3.3 不可行运动

主体冲到无人机看不到 / 穿不过的墙后：

- Skydio 会尝试侧翼机动（planner 有来自环视栈的场景几何）——**这是 Skydio 最有辨识度的行为**。
- DJI 通常保持并等待视觉重获取。

这是最干净的单轴差异化：Skydio planner *用场景几何*维持跟踪；DJI planner 更被动反应。

### 3.4 快速方向变化

主体突然 90° 转向：

- 两栈都会丢框 0.5–1.5 s，云台 slew + 无人机调头。Skydio 云台 slew + 偏航速率更高 `UNVERIFIED`；DJI 保守。

---

## 4 · 传感问题——为什么单目在这里活下来

机械臂研究者看到"跟踪目标"就想上深度。空中主动跟踪故意不上——主体通常在 3–15 m 外，超出消费级 stereo 的高质量区间，而 metric 主体位姿**并非**必需。必需的是：

- 30 Hz 的 2D 包围框（驱动云台瞄准 + 无人机航向）。
- 粗糙的主体相对深度（"保持 N 米"）——Skydio 从导航栈的摄影测量尺度获得，**不**靠电影相机上的主动深度。
- 用于遮挡预测的短时运动向量。

三者均可由单目 + IMU 达成。**电影轴上加主动深度不会改善跟踪**——只会改善避障回路（已由环视栈覆盖），不是跟踪回路。这就是为什么两家都不在主相机上装 TOF。

---

## 5 · 失败模式目录（实测能揭示的部分）

| 失败 | 可见行为 | 可能原因 |
|---|---|---|
| **杂乱背景**（森林、市场） | 飘到错的主体 | ReID embedding 模糊，无上下文消歧 |
| **相似目标交叉** | 跟踪跳到错的人 | 仅外观 ReID；无时间运动图推理 |
| **快速方向变化** | 1–2 s 画面丢失，slew 滞后 | 云台 + 偏航速率上限 |
| **长遮挡（>3 s）** | Skydio：搜索预测区域；DJI：悬停 | 运动模型衰减，ReID 先验淡化 |
| **低光电影** | 跟踪继续，画面退化 | 主体检测器对曝光敏感；无 IR 补光 |
| **主体外观改变**（穿外套） | 重获取失败 | embedding 受外观绑定 |
| **无人机达运动学极限**（如 16 m/s 主体，机最大 12 m/s） | 主体逃脱 | 无 planner 级"优雅放弃"——两栈都退化为悬停 |

最常见的消费者投诉是 *杂乱背景 → 错的主体*。两家都没解；文献也没解。

---

## 6 · 基础模型进主动跟踪？

诱惑是把 VLM 放进回路（"跟踪穿红夹克的人"）。VLM 实际能帮的：

- **一次性主体指定**——"跟踪扛冲浪板的人"——替代屏幕点选。起飞前 1–2 Hz VLM 足够。
- **语义重获取**——ReID 失败时用外观描述查询 VLM 确认。慢但能纠错。
- **多目标场景推理**——比赛中"跟踪领跑者"。需要当前跟踪器做不到的场景级推理。

VLM **不能**帮的：30 Hz 内循环。延迟禁止。

可证伪预测：**2027-06 之前，至少一台消费机会出货"描述你的主体" VLM-起飞前特性**；30 Hz VLM-in-the-loop 跟踪不会出。

---

## 7 · 给读者的指引

- **机械臂工程师** — 你的跟踪问题是 *近场 + metric*。不要把空中"远距单目"假设搬过来；你的范围需要深度。
- **AD 工程师** — 你的跟踪问题是 *多目标 + 场景图*。空中单主体框架更接近 AR/VR follow-camera，不是 AD 感知。
- **空中工程师** — 杠杆在遮挡恢复与消歧，不在检测。要做跟踪器就抄 Skydio 的预测侧翼模式，不要抄 DJI 的丢即悬停。
- **研究者** — 开放问题是 follow-camera 的多主体场景图推理："跟踪 *领先的* 跑者"，不是"跟踪这个特定跑者"。无公开基线。

---

## References

- **Skydio engineering blog** — https://www.skydio.com/blog (无单一规范论文)
- **DJI ActiveTrack feature page** — 厂商产品页，按型号不同。`UNVERIFIED, no DOI`
- **DeepSORT (可能的 ReID 谱系)** — Wojke et al. *ICIP 2017*. [arXiv 1703.07402](https://arxiv.org/abs/1703.07402)
- **ByteTrack (现代 tracker)** — Zhang et al. *ECCV 2022*. [arXiv 2110.06864](https://arxiv.org/abs/2110.06864)
- **跨实体延迟语境** — [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)

## Boundary

本文是 *反向工程的行业观察*，非第一方工程拆解。Per-method tracker 剖析（DeepSORT、ByteTrack、ReID 架构）如要写入，归 `foundations/`。同硬件的避障侧在 [`../obstacle-avoidance/`](../obstacle-avoidance/)——同环视相机，不同成本函数。电影摄影专用的构图 / 云台控制超出本 handbook 范围。
