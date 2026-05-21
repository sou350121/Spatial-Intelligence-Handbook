# Vision-Language Navigation 与 Object Navigation

**状态：** v1——观点稿。Benchmark 数字标 `UNVERIFIED`，除非有论文引用。
**Wedge 档：** W2 · 地面移动子树锚文。
**TL;DR：** 很多 "VLN 研究" 其实根本不在测空间智能——它在测 VLM 在渲染室内帧上的语言 grounding。诚实拆分：近期 VLN 大约一半的提升来自更好的语言模型，而不是更好的空间表征。另一半是真的，住在模块化 / 建图谱系里。带着这个过滤器去读这个领域。

---

## 1 · 背景——三个 benchmark 生态，一个社区

VLN / ObjectNav 领域围绕三大仿真生态聚集，它们共享场景但协议不同：

| 生态 | 场景来源 | 主要任务 | Embodiment |
|---|---|---|---|
| **Habitat / HM3D**（FAIR，2021–） | Habitat-Matterport 3D（1000+ 家庭） | ObjectNav、ImageNav、PointNav | 点 agent / 轮式 |
| **Matterport3D / R2R**（Stanford，2017–） | MP3D（90 栋建筑） | R2R（房间到房间指令）、RxR | 离散全景图或连续 |
| **AI2-THOR / RoboTHOR**（AI2，2017–） | 设计（非扫描）室内 | 交互式 ObjectNav、ALFRED | 带臂轮式 |

iGibson / OmniGibson（Stanford）和 ProcTHOR（AI2-THOR 程序生成）有重叠但在发表量上是第二梯队。

**共享任务族：**

- **PointNav**——"走到坐标 (x, y)"。纯几何。基本视为已解决（HM3D 上 >95%）`UNVERIFIED`。
- **ObjectNav**——"找到一台电视"。需要开放词表语义 + 空间记忆。
- **ImageNav**——"找到这个视角"。纯对应——更接近重定位而非导航。
- **VLN（R2R、RxR）**——"经过沙发，在厨房左转，停在第二扇门"。完整指令跟随。

如果只能盯一个，盯 **HM3D 上的 ObjectNav**——它是 "空间记忆有没有起作用" 的最干净测试，因为纯 VLM 取巧没法绕过 "跨多个房间 *找到* 物体" 这件事。

---

## 2 · 三大范式（以及谁在哪里赢）

```
   ┌──────────────────────────────────────────────────────────┐
   │                  Instruction + RGB stream                 │
   └──────────────────────────────────────────────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
   │  Modular    │       │ End-to-end  │       │  Language-  │
   │ (map + plan)│       │ (RL / IL    │       │ conditioned │
   │             │       │  encoder-   │       │  VLM-as-    │
   │             │       │  decoder)   │       │  navigator  │
   └─────────────┘       └─────────────┘       └─────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
       SLAM map +              Black-box              Frontier +
       seg + frontier          policy net             VLM chain-of-
       + LLM planner                                  thought + tool
```

**Modular**（如 CoW、ESC、L3MVN、VLFM）：在线建公制/语义地图，识别 frontier，用外部打分器（规则、CLIP 或 LLM）打分，选一个，经典 planner 导航过去。"空间智能" 占比在这里最高——地图*就是*表征。

**End-to-end**（Habitat-Web、OVRL、学习策略谱系）：RGB 进、动作出，靠 behavior cloning 或 RL 大规模训。PointNav 原始成功率最高，ObjectNav 也不错。最不透明——你根本看不出它内部有没有建图，还是只是把场景布局背了下来。

**Language-conditioned VLM-as-navigator**（NavGPT、VLMaps 式、PIVOT、prompt-based agents）：一个冻结的 VLM 当 "大脑"；空间记忆就是 prompt 里编码的东西（有时是俯视地图图像，有时是文本日志）。原型最便宜，目前 ObjectNav 上限低于 modular `UNVERIFIED`。

**各自的赢场（截至 2026）：**

| 任务 | 最佳范式 | 诚实原因 |
|---|---|---|
| PointNav HM3D | End-to-end | 纯几何，RL 吃得下 |
| ObjectNav HM3D | Modular + LLM frontier 打分 | 需要显式的 "我来过这没？" 记忆 |
| R2R / RxR | Modular 与 VLM 平手 | 两者 SR >70% `UNVERIFIED`，边际提升小 |
| 真实世界迁移 | Modular | 黑盒策略对 Habitat 光度过拟合 |

如果一篇论文声称 "更好的空间 encoder" 带来 ObjectNav SR +5 分，但没消融 LLM frontier 打分器，对该 claim 保持怀疑。这个家族近期一半的提升来自 GPT-3.5 → GPT-4o → Claude 升级了打分器，而不是空间侧改进。

---

## 3 · 哪里是 "空间智能"，哪里是 "VLM 伪装"

读任何 2025–2026 VLN 论文时最该问的拆分：

| 组件 | 空间？ | VLM？ |
|---|---|---|
| 在线公制地图（占据 / 3D） | ✓ | — |
| 语义 3D / 点特征 lifting | ✓ | ✓（用 VLM backbone） |
| Frontier 提议 | ✓ | — |
| Frontier 打分（"哪个 frontier 帮我找到电视？"） | 部分 | 大多是 |
| 指令解析 / grounding | — | ✓ |
| 综合以上后的动作选择 | 部分 | 看情况 |

纯 "VLM 伪装" 的 VLN 论文：把俯视自我地图图像 + RGB 观测历史塞给多模态 LLM，问要什么动作。空间侧贡献是*地图图像的 prompt 工程*，没有新表征。这些论文有用——但它们在测**VLM 评估**，不是空间表征研究。

"真空间" 的 VLN 论文：在线构建 3D 语义特征场或体素地图，证明*地图结构本身*（独立于 LLM frontier 打分器）驱动了提升。VLMaps（Huang 等，ICRA 2023）是经典；L3MVN 的消融在 LLM 辅助方法里最接近这个标准。

**读论文时的诊断问题：** *把 GPT-4o 换成 GPT-3.5，SR 降 ≤2 分还是 ≥5 分？* 如果 ≥5，本质是 VLM 撬动的工作，属于 VLM 文献，不属于空间表征文献。

---

## 4 · Sim-to-real 鸿沟比领域承认的更大

HM3D 光度漂亮但分布狭窄。HM3D 训出来的策略部署到真家里反复暴露：

- **光度脆弱**——真实家里有 50/60 Hz 闪烁的荧光灯、窗外的烈日，渲染场景里没有。
- **反光地板 / 反射失败**——深度传感器和立体在大理石、漆木上的表现，和完美渲染深度差得远。
- **动态障碍**——仿真里没有猫、没有走动的人、没有中途出现的儿童玩具。
- **楼梯 / 门槛检测**——HM3D 场景大多平坦；真实家不是。

这要紧的原因是：整个 ObjectNav SR 榜单赛跑都在 HM3D val 上。HM3D val 上 5 分的提升如果一次真实家庭试验都过不了，这对 ground mobile *部署* 来说不是进展。它可能是 *作为榜单运动的 VLN* 的进展。两件事不一样，但领域倾向把这个区分模糊掉。

这和 `AGENTS.md` §"仿真饱和警告" 是同一种告诫——而且在这里加倍适用，因为目前没有被广泛接受的真实世界 VLN 榜单。

---

## 5 · 2 年展望 + 可证伪预测

**展望：** Modular 谱系会继续在真实硬件上保持优势，end-to-end 会继续在仿真榜单上保持优势。有意思的桥是 "训出来的 world model + 在线地图"——把 3DGS 或 NeRF 风格的 world model 当成 *缓存地图* 让 agent rollout。driving 里的 UniAD 类方法和 Habitat 侧的 world-model agent 正在收敛到这个方向。

**可证伪预测：**

1. **到 2026 年底**，HM3D ObjectNav 的开源 SOTA 会是用 3DGS-蒸馏语义场作为地图表征的 modular agent，而不是平面 2D 语义占据网格。
2. **到 2027 年底**，第一个被广泛引用的 "真实世界 VLN benchmark"（非仿真）会发表——而它的 top-3 方法 *不会* 是 HM3D val 的 top-3。

两条都在 `reports/biweekly/` 的 rollback 里到 2027-12 时计分。

---

## 6 · 给读者

- **VLN 研究者**——明确声明你的贡献是 *空间表征* 还是 *VLM 撬动*。§3 的诊断是你能做的最便宜的消融。
- **家用机器人产品团队**——modular pipeline 能迁移到真实硬件。End-to-end Habitat 策略不能，依我们的判断。把预算放在 SLAM + 开放词表分割上，不是 "我们再 fine-tune 一下 end-to-end 模型"。
- **VLA 研究者**——VLN 策略头属于 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)。地图 / encoder 属于这里。桥文档将来再写。
- **怀疑论旁观者**——是的，ObjectNav SR 饱和了。盯真实世界复现，别盯 val split。

---

## References（入门集）

- Habitat 1.0 — Savva et al. *ICCV 2019*. https://arxiv.org/abs/1904.01201
- Habitat 2.0 — Szot et al. *NeurIPS 2021*. https://arxiv.org/abs/2106.14405
- HM3D dataset — Ramakrishnan et al. *NeurIPS 2021*. https://arxiv.org/abs/2109.08238
- Matterport3D — Chang et al. *3DV 2017*. https://arxiv.org/abs/1709.06158
- R2R — Anderson et al. *CVPR 2018*. https://arxiv.org/abs/1711.07280
- RxR — Ku et al. *EMNLP 2020*. https://arxiv.org/abs/2010.07954
- VLMaps — Huang et al. *ICRA 2023*. https://arxiv.org/abs/2210.05714
- CoW (Clip-on-Wheels) — Gadre et al. *CVPR 2023*. https://arxiv.org/abs/2203.10421
- L3MVN — Yu et al. *IROS 2023*. https://arxiv.org/abs/2304.05501
- ESC — Zhou et al. *ICML 2023*. https://arxiv.org/abs/2301.13166
- VLFM — Yokoyama et al. *ICRA 2024*. https://arxiv.org/abs/2312.03275
- NavGPT — Zhou et al. *AAAI 2024*. https://arxiv.org/abs/2305.16986

## 边界

本文覆盖**作为空间表征问题、在仿真重度生态里**的 VLN / ObjectNav。不覆盖：

- 驱动地面机器人的 VLA 策略 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)
- 真实世界 AGV 交通 / 车队规划 → `embodiments/ground-mobile/warehouse_agv_traffic.md`（待写）
- LLM / VLM 内部 → 超出范围
- 3D 特征场 encoder 本身 → `foundations/semantic-3d/`、`embodiments/manipulation/3d_feature_cloud_representations.md`

*最近一次观点更新：2026-05-21。*
