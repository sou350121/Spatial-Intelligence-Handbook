# SpatialBot 解构 (SpatialBot: Precise Spatial Understanding with Vision Language Models — Dissection)

> **发布时间**: arXiv 2024-06-19（v1）/ 2025-03-19（v7 修订）
> **论文 / 模型**: SpatialBot, [arXiv:2406.13642](https://arxiv.org/abs/2406.13642)（Cai, Ponomarenko, Yuan, Li, Yang, Dong, Zhao — BAAI / Southeast University / Peking University / Oxford）
> **核心定位**: SpatialVLM 的*互补*路线 —— 不靠预训练把几何"塞进"权重，而是在推理期把 **depth map 当作第二种模态**直接喂给 VLM；3B 参数追平 GPT-4o 的 depth-aware 任务。

SpatialBot 把 SpatialVLM 关于"VLM 缺监督"的论点反过来用：与其用 2B 合成 QA 教模型从 RGB *推断*几何，不如承认 VLM 不擅长这件事，干脆把 depth image 当**第二张图**与 RGB 并行送进视觉编码器。

**Status:** v1 — first draft. UNVERIFIED 标记所有未亲自重跑的数字（论文声称的 99% depth-task acc / GPT-4o 对比皆引自原文）。
**Zone tier:** `foundations/vlm-spatial-reasoning/` anchor #2 — 与 SpatialVLM 形成两路对照（implicit pretraining vs explicit depth tokens）。
**TL;DR:** SpatialBot 不再让 VLM 从 RGB 推几何。它把 depth map 编码成三通道 uint8（mm 级量化），作为第二张图直接接到视觉编码器；再用一个 "Depth API" 让模型可以*查询*某像素 / 某区域的 depth 值。同样大小的 backbone（Phi-2 / Qwen-1.5 / Llama-3-8B）在 SpatialBench 上反超 GPT-4o `UNVERIFIED`。代价：失去传感器（或深度估计模型出错）就崩；任何只有 RGB 的部署场景退化到 SpatialVLM 水平。

### X-Ray (non-expert friendly)

(a) SpatialVLM 教 VLM 从 RGB 隐式"看出"3D —— 但 metric 距离与遮挡仍然不可靠。(b) SpatialBot 反方向押：VLM 不擅长**抽取**几何，但很擅长**消费**喂给它的几何。所以把 depth map 编成三通道图像直接送进视觉编码器，再开一个 "Depth API"（特殊 token）让模型在推理时主动问"像素 (u,v) 的 depth 是多少？"。(c) 对工程师：如果手上有 depth 传感器（RealSense / iPhone LiDAR / stereo / DA3），SpatialBot 风格是当下最便宜的 VLM 空间能力升级——但你被绑死在传感器上，没 depth 就废。

### 📍 Research Landscape Timeline

```
CLIP 2021 ─► PaLI-X 2023 ─► SpatialVLM CVPR 2024 (implicit, 2B synth QA)
                                     │
                                     ├──► ★ SpatialBot 2024-06 (explicit depth modality)
                                     │         │
                                     │         └─► SpatialRGPT 2024-11 (depth + region tokens)
                                     │
                                     └──► 3DSRBench 2024-12 (benchmark, 评测两路)
                                                  │
                                                  └─► VLM + depth-token hybrid 2026+
```

SpatialBot 是 SpatialVLM 的**镜像论点**：同一个问题（VLM 缺空间能力），相反假设（监督 vs 输入）。两者实际上是不同延迟 / 精度 / SWaP 区段的最优解，2026+ 系统会混用。

---

## 1 · 核心架构 (Architecture)

### 1.1 系统组件对比

| 模块 | 输入 | 输出 | 频率 / 训练-推理差异 |
|---|---|---|---|
| Vision encoder (SigLIP) | RGB image + Depth image（**分开 forward 两次**）| 两组 visual tokens | 训练/推理一致；depth 走同一个 SigLIP，不重训 |
| LLM backbone | Phi-2 (2.7B) / Phi-3 / Qwen-1.5 0.5B-4B / Llama-3-8B | text | 标准 next-token loss |
| Depth API | 文本 query `<depth>(u,v)</depth>` | 数值（mm）| **推理期工具调用**；模型学会主动请求 depth |
| 训练框架 | 基于 Bunny（multi-image VLM） | — | 两阶段：pretrain + LoRA SFT |

注意：架构本身**没新东西**。所有的杠杆都在"如何让 SigLIP 吃 depth 图"和"如何让模型学会调用 Depth API"。

### 1.2 关键机制：depth 三通道量化 (Key Mechanism)

VLM 的视觉编码器原本只见过 RGB。直接喂 single-channel float depth 会丢分辨率（uint8 量化）或破坏 patch embedding（float dynamic range）。SpatialBot 用一个工程小聪明：

```
depth_mm ∈ [1, 131071]  (1mm 到 ~131m, uint24 等价)
                │
                ├─ ch_R = (depth_mm >> 0)  & 0xFF   # 0.001 m 精度位
                ├─ ch_G = (depth_mm >> 5)  & 0xFF   # ~3 cm 量级
                └─ ch_B = (depth_mm >> 10) & 0xFF   # ~1 m 量级
                                │
                                ▼
                  当成 RGB 图送进 SigLIP
```

> 三通道分别承载 2⁰、2⁵、2¹⁰ mm 量级（论文 §3.1）。这让 1 mm 量化精度同时跨越 131 m 范围，且每个通道动态范围都在 uint8 内，与 SigLIP 的 RGB 输入分布兼容。

⚡ **Eureka Moment**：**让 VLM 看见几何最便宜的方法，不是改架构、不是 fine-tune CLIP，而是把 depth 编成 RGB-like 三通道图，复用现成视觉编码器。** 这是 SpatialVLM "靠规模"的反命题 —— 输入工程做对了，监督需要量级降低。

### 1.3 信息流图

```
RGB image ────► SigLIP ──► [v_rgb tokens]
                                       \
Depth map ──► 3-ch quantize ──► SigLIP ──► [v_depth tokens]  ──►  LLM  ──►  text
                                       /              │                    │
                                                      │                    │
                                              Depth API token ◄────────────┘
                                              (model can ask: depth at (u,v)?)
```

Depth API 是这里的二次工程巧思：当模型不确定某像素的精确数值时，可以输出 `<depth>(u,v)</depth>`，由系统注入实际值再续生成。等价于给 LLM 装了一个**几何只读寄存器**。

---

## 2 · 数学核心：depth 三通道量化无损吗？(Math Core)

> 📌 **Napkin Formula**：`SpatialBot = VLM ⊕ encode_depth_as_RGB ⊕ DepthAPI`
> 全部贡献在 ⊕；架构、loss、backbone 都不变。

**目标**：把 `depth_mm ∈ [1, 131071]` 编成 `(R,G,B) ∈ [0,255]³`，可逆。

**公式**：
```
R = depth_mm        & 0xFF       # 取 bit 0-7
G = (depth_mm >> 5) & 0xFF       # 取 bit 5-12
B = (depth_mm >>10) & 0xFF       # 取 bit 10-17
                                 # 总覆盖 bit 0-17 = 18 位 = 262144 个 mm 级
```

**变量说明**：

| 符号 | 含义 | 注 |
|---|---|---|
| depth_mm | 整数 mm 深度 | range 1 mm – 131.07 m |
| 0xFF | 0b11111111 = 255 | uint8 上限 |
| >> N | 右移 N 位 | 取高位 |

**直觉**：三通道有"重叠位"（R 与 G 共享 bit 5-7，G 与 B 共享 bit 10-12）。这给 SigLIP 一定的冗余 —— 即使某通道被 patch embedding 微扰，其他通道可以覆盖。代价：编码不是严格双射（不同 depth_mm 可对应同一 (R,G,B) 二元组的子集），但实际机器人 0.1mm 级不在 VLM 任务范围。

⚠️ 量化误差 `UNVERIFIED`：论文不报告解码精度，假设亚厘米误差可被 SigLIP patch 抹平。

---

## 3 · 玩具例子 (Worked Example)

**场景**：桌面一只 mug，depth 传感器读 mug 中心像素 = 843 mm（0.843 m）。

1. **编码**：
   - R = 843 & 0xFF = 843 mod 256 = 75
   - G = (843 >> 5) & 0xFF = 26 & 0xFF = 26
   - B = (843 >>10) & 0xFF = 0
   - 写入像素颜色 (75, 26, 0)
2. **SigLIP** 处理整张三通道 depth 图 → depth tokens。
3. **Prompt**："Is the mug closer than the fork?"
4. **LLM** 看到 RGB tokens（看见"mug"标签）+ depth tokens（颜色编码距离）+ 可调用 Depth API。
5. 模型生成：`The mug is at <depth>(312, 245)</depth> = 0.843 m, the fork is at <depth>(420, 250)</depth> = 0.790 m. Yes, the fork is closer.`

注意第 5 步：模型**不靠 SigLIP 自己解码颜色**，它发起 API 调用拿到精确 mm 数。SigLIP 提供的是 spatial layout 直觉，Depth API 提供 metric 精度。**两者职责清楚分离**——这是为什么 SpatialBot 在 metric 任务上能赢 SpatialVLM。

---

## 4 · 工程视角 (Engineering View)

| 维度 | SpatialBot | SpatialVLM | 评注 |
|---|---|---|---|
| **推理输入** | RGB + depth map | RGB only | SpatialBot 强绑感测器 |
| **训练数据量** | ~745k samples (SpatialQA) | ~2B synth QA pairs | 监督差 ~3 个量级 |
| **模型规模** | 3B / 4B / 8B | PaLI-X 5B / 55B | 同量级更轻 |
| **延迟** | `UNVERIFIED` — depth pass 双 SigLIP forward | `UNVERIFIED` 单 SigLIP forward | SpatialBot ~2× 视觉成本 |
| **失效模式** | depth 噪声 → 自信错答 | 模板外问法 → 自信错答 | 两边都不承认无知 |
| **部署门槛** | RealSense / LiDAR / DA3 必备 | 纯 RGB camera | SpatialBot SWaP-C ↑ |

**SpatialQA 数据组成**（论文 §4.1, ~745k samples total）：

```
Bunny_695k      695,000   通用 VLM SFT 数据，奠基对话能力
VG / COCO        20,000   depth-focused QA（核心 spatial supervision）
KITTI             1,750   驾驶场景 metric depth
NYU Depth v2      1,500   indoor metric
RT-X (robot)      7,500   manipulation 上下文
SA-1B            15,000   大规模 segment-anything subset
2D-3D-S           2,900   indoor 室内 3D
```

注意：**真正 spatial-specific 的数据其实不到 5 万条**。剩下 695k 是通用 VLM 数据。也就是说 SpatialBot 用了不到 SpatialVLM 1/40000 的 spatial QA 监督，靠**输入侧把几何送进来**追平。

---

## 5 · 数据与评测 (Data & Eval)

**SpatialBench**（论文自带 eval set）：
- 80 张人工标注图（含 ~3 个 bbox/张）覆盖 positional / size / reaching 类 spatial 问题
- 20 张专注 counting
- 加上 MME 公开 spatial subset

**论文声称结果**（`UNVERIFIED`, 引自 arXiv v7）：

| Model | SpatialBench Depth Tasks | 评注 |
|---|---|---|
| GPT-4o（看 RGB+depth） | "-"（无法回答） | 论文标记：拒绝输出 metric depth |
| SpatialBot-Phi-2 (3B) | ~99% depth est. | 论文主结果 |
| SpatialBot-Qwen1.5-4B | comparable | 同量级 |
| SpatialBot-Llama3-8B | comparable | 大模型未带来 outsized 增益 |

**机器人 pick-and-place 任务**：RGB-D 变体 > RGB-only 变体（`UNVERIFIED` 具体 % 论文未给清楚 success rate baseline）。

⚠️ **Benchmark 警告**：SpatialBench 由论文作者自带，与 3DSRBench / BLINK / VSR 的独立评测尚未充分对照。看 [`3dsrbench_dissection.md`](./3dsrbench_dissection.md)（同 zone）了解外部基准对所有 VLM 的真实水平。

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做**（论文支持）：
- 精确 metric depth query —— 一旦你信任传感器，1mm 级答案可读
- 区域级 depth 推理 —— Depth API 可问任意像素
- pick-and-place 类 robot embodied 任务（条件：场景有 depth）

**不能做** / 退化场景：
- **Depth 传感器失效** —— SpatialBot 退化到 RGB-only baseline，远低于 SpatialVLM
- **Depth 估计模型代替真传感器** —— Metric3D / ZoeDepth `UNVERIFIED ±10-20%` scale 误差直接进入答案
- **Reflective / transparent / dark** 物体（玻璃、镜面） —— depth 传感器本身物理上失败，SpatialBot 不会知道
- **遮挡查询** —— Depth map 只给可见表面；问"杯子*背后*物体多远"无解
- **多视角一致性** —— 同 SpatialVLM，单图条件，移动相机答案变

### 6.x · Hidden Assumptions

- **Depth map 是 ground truth 或近似** —— 这是最关键假设；机器人现场未必成立
- **3-channel mm 量化对 SigLIP 是 transparent 的** —— 没有重训 SigLIP，假设 patch embedding 不会把 depth 颜色误解为某种 RGB 物体
- **场景完全可见** —— 与 SpatialVLM 共享此假设
- **Depth API 调用机制可学** —— 仅 ~5 万 spatial QA 数据，模型需在该数据中学会发起 `<depth>` token
- **传感器 / 估计深度的 noise 分布稳定** —— 训练用 KITTI/NYU 干净，部署遇 RealSense outdoor 飘移会失效

**自信地错**：与 SpatialVLM 同病。Depth 传感器返回错值时，SpatialBot 把错值视为权威数据，输出比 SpatialVLM 更**自信**的错答 —— 因为 metric 数字看起来很专业。这在机器人现场是危险模式。

**Interview Tip**："SpatialVLM 押数据规模，SpatialBot 押输入工程。3B SpatialBot 用 1/40000 的 spatial QA 数据追平更大 VLM，因为它不让 VLM 从 RGB 抽几何 —— 直接喂 depth 图。代价：传感器一坏整个 zone 失效，且会自信地把 depth 错值复述成 metric 答案。生产系统需要把它和深度可信度检查一起部署。"

---

## 7 · 与相关工作对比

| Lever | SpatialBot | SpatialVLM | SpatialRGPT (2024-11) | 3D-aware backbone |
|---|---|---|---|---|
| Spatial 信号来源 | 输入 depth map | 微调 2B 合成 QA | depth + region (mask) tokens | 3D encoder (点 / 体素) |
| 训练成本 | LoRA SFT ~745k | 全量 finetune 2B | SFT + region prompt | 重训 backbone |
| 推理传感器 | RGB+D 必须 | RGB only | RGB+D+region | RGB or RGB+D |
| Metric 精度 | 高（API 直接读 mm） | 低（隐式回归） | 高 | 中-高 |
| 模板外鲁棒性 | 中（depth 直读绕开模板） | 低 | 中 | 低 |
| SWaP 增量 | depth 传感器 + 双 SigLIP forward | 0（纯 RGB） | + region prompt UI | 重 GPU |

**面试问：选哪个？** 看部署：
- 桌面 manipulation、有 RealSense → **SpatialBot**
- 户外、纯 RGB camera → **SpatialVLM**
- 都要 → **2026+ 趋势：双训练（implicit pretraining + 推理期 depth token）**

---

## 8 · 与 SpatialVLM 的关键差异（zone 内对照）

```
SpatialVLM 路线：                     SpatialBot 路线：
─────────────────                    ─────────────────
RGB ──► VLM（已在 2B 合成 QA          RGB  ──► SigLIP ──┐
           上 SFT 过）──► answer      Depth─► SigLIP ──┤──► LLM ──► answer
                                                       │       │
                                                       └◄──────┘
                                                       Depth API call
押注：监督规模 → 几何"长"进权重         押注：输入工程 → 推理期持有几何
                                       
代价：metric 精度不可靠                代价：失去 depth 整套退化
失败：遮挡 / 模板外措辞                失败：传感器物理失败 / depth 估计误差
```

**两路在 zone 内非对立而是 lane** —— v2026 系统倾向把两者混合（SpatialBot 风格输入 + SpatialVLM 风格 SFT 同时用）。

---

## 9 · Falsifiable prediction

到 2026-12，任何在 manipulation benchmark 上 SOTA 的 VLM-for-robotics 论文，会同时使用 (a) 类 SpatialVLM 风格合成 QA 预训练 与 (b) 类 SpatialBot 风格推理期 depth token。**只**用其一的论文将拿不到顶级 manipulation benchmark 第一名。如果到 2026-12 SOTA 仍属于纯 RGB（无 depth 输入）的 VLM-VLA，这个预测被证伪。

---

## References

- SpatialBot — Cai et al. arXiv 2024-06. [arXiv:2406.13642](https://arxiv.org/abs/2406.13642)
- GitHub — [BAAI-DCAI/SpatialBot](https://github.com/BAAI-DCAI/SpatialBot)
- Model weights — [RussRobin/SpatialBot-3B on HuggingFace](https://huggingface.co/RussRobin/SpatialBot-3B)
- SpatialBench dataset — [RussRobin/SpatialBench on HuggingFace](https://huggingface.co/datasets/RussRobin/SpatialBench)
- Bunny (架构基线) — He et al. 2024
- 兄弟论文 SpatialRGPT — Cheng et al. 2024-11 (depth + region tokens 进一步细化)

## Cross-references

- Zone 同侪 implicit 路线 → [`spatialvlm_dissection.md`](./spatialvlm_dissection.md)
- Zone 外部评测 → [`3dsrbench_dissection.md`](./3dsrbench_dissection.md)
- 替代 lane（显式 3D 语义抬升）→ [`../semantic-3d/`](../semantic-3d/README.md)
- 深度模型本身 → [`../depth-foundation/`](../depth-foundation/README.md)（SpatialBot 部署时 depth 源选择）
- VLA 集成 → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)（SpatialBot = "explicit depth token" 行）
- VLA-Handbook spatial reasoning → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)

## Boundary

本文专门解构 SpatialBot 的 depth-as-modality 路线。它**不**覆盖：SpatialVLM 监督规模论点（→ [`spatialvlm_dissection.md`](./spatialvlm_dissection.md)）；外部 3D 推理 benchmark（→ [`3dsrbench_dissection.md`](./3dsrbench_dissection.md)）；具体 depth 传感器选型（→ `foundations/sensor-physics/`）；depth 基础模型对比（→ [`../depth-foundation/`](../depth-foundation/README.md)）；VLA 端 3D-aware action head（→ `bridge-to-vla/`，VLA-Handbook）。

---

[← Back to vlm-spatial-reasoning README](./README.md)
