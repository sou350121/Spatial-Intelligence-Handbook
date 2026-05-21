# Physical Intelligence (π) — 只读空间这一片

**Status:** v1 — opinionated draft。内部训练规格 `UNVERIFIED`（私人公司；π0 / π0.5 model card 有限）。策略侧细节延迟到 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)。
**TL;DR:** Physical Intelligence (PI) 是 2024-2026 年**「VLA 作为产品」最高调的押注**。本手册只窄角度覆盖它：**栈的空间感知侧** —— π0 与 π0.5 消费什么 3D / 视觉表征、它在哪里与 action head 相接。完整策略 / 数据配方故事在 VLA-Handbook。这个文件存在的理由：PI 是看「空间遇到 VLA」在公司规模上最干净的地方。

---

## 1 · 本文存在的理由 + 故意不覆盖什么

PI（2024 由 Karol Hausman、Chelsea Finn、Sergey Levine 等创立）在产品层是通用机器人基础模型公司。π0 论文（Black et al. 2024）和 π0.5（2025 `UNVERIFIED` 准确日期）是公开工件。PI 大部分有意思的东西 —— flow-matching action head、跨形态训练、数据组成 —— 是**策略侧**，归在姐妹手册：

→ **VLA-Handbook：** 策略架构、action head、训练配方、跨形态迁移（TBD 链接到具体节）

**本文只覆盖空间 / 感知片段**：PI 的模型*看*什么、如何编码 3D 结构（或不编码），以及那如何与 bridge-to-VLA 合约相接。

---

## 2 · π0 / π0.5 血脉概览（感知侧）

| 模型 | 年份 | 感知输入 | 空间表征 | 备注 |
|---|---|---|---|---|
| π0 | 2024 | 多相机 RGB（腕载 + 第三人称）| 隐式 —— 无显式 3D head | VLM backbone 直接消费 RGB tokens |
| π0.5 | 2025 `UNVERIFIED` | RGB + 部分任务（传闻）带深度 `UNVERIFIED` | 同架构 + 更大 context | 数据 + 规模迭代，不是感知架构迭代 |

关键观察：**π0 感知时只用 RGB**。没有点云、没有体素、没有显式前馈 3D 模块。空间信息通过 VLM backbone 学到的视觉表征隐式进入模型。这与 SpatialVLM 式押注（`bridge-to-vla/feature-cloud-to-action.md` §2）一致 —— 数据 + 模型够大，RGB + scale 就可以。

手册不背书也不反驳这押注；只标注它是**已上线 VLA 中「跳过显式 3D」最干净的范例**。取舍见 §3。

---

## 3 · PI 栈里什么是空间的，什么不是

| 层 | π0 / π0.5 是否有？ | Spatial-Handbook 引用 |
|---|---|---|
| 标定多相机采集 | 是（腕载 + 第三人称立体或单目）| `deployment/sync`（TBD）、`deployment/calibration`（TBD）|
| 显式深度 / 点云 head | **否** | — |
| 3D feature cloud → policy | **否** | `bridge-to-vla/feature-cloud-to-action.md`（替代路径）|
| VLM 隐式空间推理 | 是（承重假设）| `foundations/vlm-spatial-reasoning/` |
| Flow-matching action head | 是 | VLA-Handbook（不在本文范围）|
| 跨形态训练集 | 是（移动 + 机械臂）| VLA-Handbook |

有意思的格子是那个空的：**无显式 3D head**。这是设计选择，不是疏漏。含义：

- **数据流水线更便宜** —— 不要求每个采集点都有标定深度传感器。
- **VLM backbone 复用更紧** —— 感知编码器可用互联网级 RGB 通用 VLM。
- **空间推理上限由 VLM 隐式 3D 理解决定** —— 见 `foundations/vlm-spatial-reasoning/` 看现 VLM 能做什么、不能做什么。
- **风险集中在显式 3D 本会接住的失效模式** —— 遮挡接触、精细度量尺度、透明物体。PI 在量产是否会被这些坑到，是经验测试。

---

## 4 · 数据策略（一段话版，外部可见的部分）

PI 的主张是**跨形态遥操作数据的规模 + 多样性** + **强 VLM backbone** + **flow-matching action head** 是配方。数据侧是护城河：PI 在多形态多任务的规模化遥操作基础设施上重投入，π0.5 迭代据称主要是数据 + 规模升级而不是感知架构变化 `UNVERIFIED`。

从 Spatial 手册角度，数据选择重要是因为**VLM 学到的隐式 3D 推理被数据分布卡上限**。如果大部分数据是桌面操作，模型在远距离 standoff 或杂乱场景的空间先验就弱。这正是 Tesla 等纯相机 AD 厂商靠的数据飞轮论证 —— 同模式、不同形态。

---

## 5 · PI 在哪里遇到空间手册

这里就是桥的位置。PI 是 `bridge-to-vla/` 这条道上公司层最高杠杆的读法：

| 问题 | PI 落在哪 |
|---|---|
| VLA 应该消费 3D feature clouds 吗？ | **不，在 PI 的押注里。** 见 `bridge-to-vla/feature-cloud-to-action.md` §2 —— PI 落在「SpatialVLM 形状」|
| action head 从感知要什么？ | flow-matched velocity tokens；感知交付 RGB tokens 而非 3D tokens |
| 集成合约长啥样？ | 相机外参 + RGB 流；没有点云 schema。合约更简单，保真上限更低 |
| 跨形态故事？ | 重数据多样性、轻架构统一。与显式 3D-VLA 路线相反 |

手册把 PI 读作**「隐式 3D 在当前规模上足够」最强存在证明**，也是显式 3D VLA（3D-VLA、体素 VLA 血脉）最终若反超时最干净的对比案例。

---

## 6 · 两年展望 + 可证伪预测

PI 的押注胜负在一个问题：**RGB-only VLM 的隐式 3D 能否在更难空间任务（遮挡、透明物、精细度量伸够）上规模化得比显式 3D 方法追上数据 + 策略质量更快？**

两种情景：

**(a) 隐式赢。** RGB-only π 系列在杂乱、遮挡、接触富集任务上匹敌或击败显式 3D VLA。显式 3D 研究道变成特定任务的小众（透明 / 反光 / 精细装配）。PI 的数据护城河是故事。

**(b) 显式赢。** 度量尺度或精细几何承重的任务暴露了隐式天花板；领域转向 feature-cloud-conditioned policies。PI 2027 前转向混合。

**可证伪预测：** 2027-06 前，π 系列会上线一个变体，**显式消费深度或点云 tokens** 用于至少一个任务族（很可能是精细装配或透明物操作）。若没发生，PI 在加倍 RGB-only，隐式胜命题在更高赌注上被测试。

---

## 7 · 给不同读者的判读

- **机械臂工程师** —— 策略侧在 VLA-Handbook；*此处*要点是若你的数据像 PI 那样规模化，栈里可能不需要显式 3D。诚实评估你的数据规模是闸门。
- **航拍工程师** —— 不直接相关；PI 当前形态域是操作。
- **AD 工程师** —— 策略无关，但数据飞轮论证概念可迁移（PI 遥操作队 ≈ Tesla 车队）。
- **VLA 研究者** —— π0 / π0.5 是你的参考架构；此处记录的空间选择是你不需要重复的输入。
- **空间研究者** —— 要回答的问题是「在哪个最小任务上隐式 3D RGB *可演示地*崩」。能发表这个，领域会重定位。

---

## References

- π0 — Black et al. 2024. https://www.physicalintelligence.company/blog/pi0（`UNVERIFIED — 直接论文链接`）
- π0.5 — Physical Intelligence 2025 release blog `UNVERIFIED`
- SpatialVLM — Chen et al. *2024*. https://arxiv.org/abs/2401.12168
- 3D-VLA — Zhen et al. *ICML 2024*. https://arxiv.org/abs/2403.09631
- VLA-Handbook（姐妹仓库，策略侧）— https://github.com/sou350121/VLA-Handbook
- 配套：[`bridge-to-vla/feature-cloud-to-action.md`](../bridge-to-vla/feature-cloud-to-action.md)
- 配套：[`foundations/vlm-spatial-reasoning/`](../foundations/vlm-spatial-reasoning/)

## Boundary

本文是 PI *空间*片段的**公司层读法**。策略 / action head / 训练配方细节超范围 —— 在 VLA-Handbook。显式 3D 替代方案的逐方法解剖属于 `bridge-to-vla/feature-cloud-to-action.md` 与 `foundations/vlm-spatial-reasoning/`。不在此重复策略故事。

---

## 🤖 Moltbot Updates

<!-- Moltbot appends release / news entries below this line. Format: YYYY-MM-DD — one-line event — source URL. -->
