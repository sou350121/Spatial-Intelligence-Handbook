<!-- ontology-5axis
problem: Object 6-DoF pose (foundation)
representation: Mesh template + RGBD features
sensor: RGBD + Object mesh
paradigm: Learned + DiffRender refine
time: Online
ref: ../../cheat-sheet/ontology.md §7
-->

# FoundationPose (新物体 6D 位姿，无需逐物体训练)

> **发布时间**: 2024-03 (CVPR 2024 *best paper* — Wen, Yang et al., NVIDIA)
> **论文 / 模型**: FoundationPose (arXiv 2312.08344)
> **核心定位**: 一个模型给*任意*物体估计 6D pose — 用 CAD mesh 或 ~16 参考图 — 无需 per-object fine-tune.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · 2024–2026 manipulation 栈的 pose-foundation 默认.
**TL;DR:** 第一个配得上 "foundation" 的 6D pose 模型. 丢任何新物体（mug、螺丝刀、打包胶带）进去就能得到 pose 而无需重训. Render-and-compare + 扩散风迭代精化，由训在 ~1M+ 合成物体上的模型打分. 这是 2026 团队不应再训 per-object pose head 的原因.

**X-Ray.** 2024 前的 pose 模型（PoseCNN、DenseFusion、GDR-Net）要求 *per-object 训练*. FoundationPose 打破这堵墙：一次在巨量合成数据上训，泛化到任意未见物体 — 用 mesh 或 ~16 参考图. 2024 年 Object pose 加入 foundation-model 俱乐部，与深度（Depth Anything）和 3D（VGGT 前驱）同列.

> ⚠️ **"Foundation" 是 disputed (ontology §13.5)** — FoundationPose 需 first-frame mask 手動標記 / >200ms latency 不 real-time / 單任務 (僅 6-DoF pose) / 依賴外部 2D detector (single point of failure)。本文用「foundation」是社群命名 follow-along，**不是嚴格 foundation model 定義**。Production status: 🚀 pilot only。

---

## 📍 研究全景时间线

```
2017       2019         2021       2022          2024 (HERE)         2025+
PoseCNN ─► DenseFusion ► GDR-Net ► MegaPose ───► FoundationPose ──► video / temporal
└─ per-object supervised ──┘  └── novel obj, mesh required ──┘  └─ mesh-free ─┘
```

第一篇在生产精度下处理未见物体*无 mesh* 的论文. 时序 / 视频继任者在 2026 仍处早期.

---

## 1 · 架构总览

### 1.1 系统组件对比

| Module | Input | Output |
|---|---|---|
| Hypothesizer | RGB-D crop + obj rep | N 个 pose hypotheses |
| Refinement (diffusion-style) | hypothesis + render | refined (multi-step) |
| Scorer | rendered vs observed | scalar score |
| Object rep (mesh-free) | ~16 ref images | implicit neural object |

**Render-and-compare 包在学到的 scorer 里**，配扩散风迭代精化. *Scorer 才是 foundation model* — 跨物体泛化，因为它训练时见过百万个.

### 1.2 ⚡ Eureka Moment

> **把 pose 视为"给 rendered hypothesis 与观测的匹配度打分" — 让 scorer 成为 foundation model，不是 regressor.**

之前工作从特征 regress 6D pose → per-object 脆弱. FoundationPose 反转：render N 个候选（免费、确定性）并*学打分*（从合成先验泛化）.

### 1.3 信息流

```
   RGB-D crop ──┐
                ▼
   (mesh) ─► hypothesizer ─► N candidates ─► render each ─► scorer ─► top-k
   or                                                                    │
   (16 refs) ─► implicit obj ──────────────────────────────────────────► ▼
                                                  refine (K iters) → final pose + confidence
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  pose*  =  argmax_{T in candidates}  scorer( render(obj, T),  observed_crop )
```

Pose 是从候选集*选出*，不是 regress. Scorer 是学到的泛化机器.

| Symbol | Meaning |
|---|---|
| `T = (R, t)` | 6D pose |
| `render(obj, T)` | 在 `T` 处 rasterize 的 RGB-D |
| `scorer(·, ·)` | 学到的对比 scorer |
| `K` | refinement 迭代数 (~5 `UNVERIFIED`) |

**Intuition.** 渲染是几何 oracle；scorer 是感知 oracle. 合起来 → pose 变成 pose 空间中的*搜索*，scorer 作为导航梯度.

---

## 3 · Worked example: 螺丝刀的位姿

RealSense D435，screwdriver 检测到 → crop. 有 CAD mesh.

1. **Hypothesize** ~252 旋转假设（icosphere × in-plane）；translation 从 depth 重心.
2. **Render** 每个候选到 crop.
3. **Score** (rendered, observed) → 252 个标量；top-5 在 GT ~10° 内.
4. **Refine** top-5 × K=5 步；top-1 → ~2° 旋转、~3 mm translation `UNVERIFIED`.
5. **Final score** ~0.92 → 发给 grasp planner.

端到端桌面 ~80–150 ms `UNVERIFIED`，Orin ~300–550 ms `UNVERIFIED`. Mesh-free 模式用 implicit neural object 替换 renderer.

---

## 4 · Engineering view

| Stage | Desktop `UNVERIFIED` | Orin `UNVERIFIED` |
|---|---|---|
| Render (×252) | 20–40 ms | 80–150 ms |
| Scoring | 30–50 ms | 100–200 ms |
| Refinement (×5) | 30–60 ms | 100–200 ms |
| **End-to-end** | **~80–150 ms** | **~300–550 ms** |

Multi-object 不批处理则线性 scale. 蒸馏后 Orin 上单物体 30 Hz tracking 可行；2026 年桌面所有物体 30 Hz 在边缘不就绪.

**Deployment.** 新 SKU：16 张照片 + 30 秒 mesh-free 拟合 → 就绪. Tracking 模式：每 N 帧重检，从先验 refine → ~30 ms/frame `UNVERIFIED`.

---

## 5 · Data & eval

训在 Objaverse / ShapeNet 的 ~1M+ 合成物体（论文声称；准确 `UNVERIFIED`），用域随机光照 / 材料 / 背景. 在 LM-O、YCB-V、T-LESS 上评估 — 比 MegaPose 高 6–18 AR `UNVERIFIED`. Mesh-free 变体比 model-based 落后几个 AR 但是更重要的真实世界能力.

---

## 6 · Capabilities & failure modes

**赢：** 几分钟内 onboard 新 SKU；中度遮挡鲁棒；无 CAD 物体的 mesh-free 路径.

**败于：** 无纹理的严重对称（旋转歧义固有）；透明 / 镜面物体（depth sensor 先失败）；物体 <~10 mm `UNVERIFIED`；无干净 2D 检测的重杂乱.

### 6.x GitHub 实地失败（atlas 联动）

- **GitHub-validated**：NaN scores 部署灾难 — 对应 [#53 (27 comments, closed-without-explicit-fix)](https://github.com/NVlabs/FoundationPose/issues/53)，多用户在不同 GPU / CUDA 复现但根因（fp16 / 老 GPU 路径）无官方诊断；"closed 不等于已修"是 maintainer wontfix 信号，与 depth 阵营 FoundationStereo #121 同模式，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：输入资产门槛吃掉 ~30% 部署 — mesh / CAD 要求（[#83](https://github.com/NVlabs/FoundationPose/issues/83)·[#60](https://github.com/NVlabs/FoundationPose/issues/60)·[#32](https://github.com/NVlabs/FoundationPose/issues/32)）+ depth 预处理（[#44](https://github.com/NVlabs/FoundationPose/issues/44)）+ 首帧 mask 选不准导致 drift 传染（[#186](https://github.com/NVlabs/FoundationPose/issues/186)·[#279](https://github.com/NVlabs/FoundationPose/issues/279)）；论文 model-free 卖点在 issue 区落地为 "要么扫 mesh 要么没法用"，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

### 6.1 Hidden Assumptions

- **Depth 通道可用且可靠.** 仅 RGB 退化 5–15 AR `UNVERIFIED`. 反射金属 → 实际上仅 RGB.
- **物体刚性.** 线 / 布料不在范围；articulated 物体仅给主导 link 的 pose.
- **参考图覆盖旋转半球（mesh-free）.** 单半球不泛化到背面.
- **物体在图像中 ≥~10 mm.** 微小 SMD / 细螺丝低于有效分辨率.
- **光照大致 photo-realistic.** 域随机化覆盖广变化，不覆盖单色 IR.

这些是*输入域*假设，不是参数问题 — fine-tune 也修不了.

---

## 7 · Comparison & interview tip

| Model | Novel obj? | Mesh req? | Synth-only? | Real-time? | Year |
|---|---|---|---|---|---|
| PoseCNN | ❌ | yes | no | ~30 Hz | 2017 |
| DenseFusion | ❌ | yes | no | ~16 Hz | 2019 |
| GDR-Net | ❌ | yes | partial | ~25 Hz | 2021 |
| MegaPose | ✅ | **yes** | ✅ | ~3 Hz | 2022 |
| **FoundationPose** | ✅ | **optional** | ✅ | ❌ (80-150ms desktop / 300-550ms Orin; distilled ~5-10 Hz `UNVERIFIED` 但 ≪ 30 FPS per ontology §10.2) | 2024 |

> **🎤 Interview Tip.** "为从未见过的物体做 pose estimator？" — *"FoundationPose 在 mesh-free 模式下 — 用 ~16 张参考图 onboard，然后跑 pose tracker. 有 CAD mesh 用它来多拿几个精度分."* "我会在 YCB 风格数据上训 PoseCNN" 已三年过时.

---

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 数据来源：[NVlabs/FoundationPose](https://github.com/NVlabs/FoundationPose) — **3.2k★ · 140 open issues**（2026-05-24）。按 comment 降序扫前 25 + topic-grep。结论：repo 仍是 W1 anchor，但 **maintainer 半休眠**（last code commit 2025-03，社区 PR #369 RTX 50 + #364 TRT 至今未 merge），实地坑集中在「输入资产」「硬件 / 部署」「symmetric & tracking 失稳」三轴。

### 8.1 First-frame mask：仍是 deployment 最大单点失败

- **GitHub-validated**：[#51 (closed, 11c)](https://github.com/NVlabs/FoundationPose/issues/51) 显式要求"无 mask 工作流"，[#186 (closed, 11c)](https://github.com/NVlabs/FoundationPose/issues/186) 追问"第一帧怎么选"，[#383 (open, 4c)](https://github.com/NVlabs/FoundationPose/issues/383) "Correct Frame 0 but Poor Tracking" — 都指向同一根因：repo 自身**不提供** mask 工具，必须外接 XMem / SAM / Grounded-SAM，[#257 (open)](https://github.com/NVlabs/FoundationPose/issues/257) 提议 ROS + Grounded-SAM 拼装至今无官方支持。**实地后果**：first-frame mask 偏一点 → tracking 几十帧内 drift；与 dissection §6 "无干净 2D 检测的重杂乱" 失败模式同因，但严重程度高一档（90% 部署痛点）。
- **缓解**：自接 SAM2 / XMem 做 mask propagation；不要相信 single-frame mask 稳定性。

### 8.2 TensorRT / ONNX export：社区 PR 4 月未 merge

- **GitHub-validated**：[#56 (closed-without-solution, 5c)](https://github.com/NVlabs/FoundationPose/issues/56) "How to export to TensorRT"、[#124 (closed, 1c)](https://github.com/NVlabs/FoundationPose/issues/124) "accessing the onnx file for inference on jetson"、[#298 (open, 11c)](https://github.com/NVlabs/FoundationPose/issues/298) "INT8 Quantization 显著精度退化 (FP16 OK)"。社区 PR [#364 "Adds TRT support"（2025-04-30 提交，至今 open）](https://github.com/NVlabs/FoundationPose/pull/364) **未 merge**。
- **实地后果**：想上 TensorRT 必须 fork 自己改 + 调 quantization；INT8 报道精度崩，FP16 稳。NVIDIA 官方路径是 [isaac_ros_foundationpose](https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_pose_estimation)，但 [#274 (closed, 5c)](https://github.com/NVlabs/FoundationPose/issues/274) 报告 isaac_ros 版 demo_data 上 pose 严重偏离 NV 版 — 跨 ROS 包精度漂移待官方对齐。

### 8.3 RTX 50 / 4090 / Jetson：硬件覆盖滞后于市场

- **GitHub-validated**：
  - **RTX 50 (Blackwell, sm_120)**：[PR #369 (2025-07-31, open 至今)](https://github.com/NVlabs/FoundationPose/pull/369) 由社区提交修 PyTorch 2.7 + CUDA 12.8 + C++17 + sm_120，**未 merge**；[#398 (open, 3c)](https://github.com/NVlabs/FoundationPose/issues/398) 5070 Blackwell 上 pytorch3D 装不上。
  - **RTX 40**：[#27 (closed, 20c)](https://github.com/NVlabs/FoundationPose/issues/27)、[#9 (closed, 15c)](https://github.com/NVlabs/FoundationPose/issues/9) Ada 6000 sm_89 编译错。
  - **GTX 16xx (Turing)**：[#53 (open, 27c)](https://github.com/NVlabs/FoundationPose/issues/53) 长期 NaN scores — 2026-01 用户 Qiyue-Chen-robo **找到根因**：PoseRefine stage 的 CUDA AMP autocast 在 GTX 16xx 上崩，关掉 AMP 即可；issue 仍 open，官方未吸收 fix。
  - **Jetson Orin**：[#292 (closed)](https://github.com/NVlabs/FoundationPose/issues/292) 社区 fork [Jetpose](https://github.com/Kaivalya192/Jetpose) 做 Orin NX 适配；[#391 (open)](https://github.com/NVlabs/FoundationPose/issues/391) "Orin Nano 8G 够吗" 至今无 maintainer 回答；[#226 "register on Orin NX 极慢"](https://github.com/NVlabs/FoundationPose/issues/226)。
- **实地后果**：新一代硬件（5090 / Blackwell Jetson Thor）一律 fork + 等社区；不要假设 README 装得起来。

### 8.4 Latency 真值：tracking 不是 Hz，是 ms/frame，且首帧贵 10×

- **GitHub-validated**：[#402 "Low inference speed on RTX 4050"](https://github.com/NVlabs/FoundationPose/issues/402)、[#256 "How can I speed up the long inference time in first frame?"](https://github.com/NVlabs/FoundationPose/issues/256)、[#334 "Is Inference speed margin reasonable?"](https://github.com/NVlabs/FoundationPose/issues/334)。社区一致报告：register（首帧 N=252 hypothesis）远慢于 tracking（K=5 refine 单 prior）；桌面 80–150 ms 是 **tracking 稳态**，首帧 300–1000 ms 正常。dissection §4 表格的 desktop / Orin 数字与社区报告同量级 → 维持 `UNVERIFIED` 但**可信**。
- **实地后果**：30 Hz 目标只在 distilled + tracking 稳态下可期；register 阶段闭环必须容忍秒级延迟，否则换 detection-only fallback。

### 8.5 Symmetric 对象：固有失败，需上游消歧

- **GitHub-validated**：[#395 (open) "Orientation flips for Symmetry objects"](https://github.com/NVlabs/FoundationPose/issues/395) — 旋转对称物体跨帧在等价 pose 间跳变；[#107 (closed, 6c)](https://github.com/NVlabs/FoundationPose/issues/107) 无纹理圆柱 tracking 时绕轴旋；[#269 (open, 7c)](https://github.com/NVlabs/FoundationPose/issues/269) YCBV ADD-S 评测 BOP leaderboard 数字对不上。
- **实地后果**：与 dissection §6 已列「严重对称（旋转歧义固有）」一致；scorer 无方向先验，**只能上游消歧**（语义标记 canonical orientation，或加 AprilTag / 纹理标签）。不要期待算法侧修。

### 8.6 Mesh / 输入资产门槛：单位 / 对齐 / mask 三大坑

- **GitHub-validated**：[#44 (closed, 35c — top thread)](https://github.com/NVlabs/FoundationPose/issues/44) 是 repo 最常被引用的"先看这条"，用户 savidini 总结三大坑 — (1) **mesh 必须米单位**（不是 mm，违反默认）、(2) RGB & depth 必须对齐、(3) intrinsics K 矩阵格式；[#83 (closed, 16c)](https://github.com/NVlabs/FoundationPose/issues/83)、[#60 (closed, 10c)](https://github.com/NVlabs/FoundationPose/issues/60)、[#32 (closed, 10c)](https://github.com/NVlabs/FoundationPose/issues/32) "model-free 怎么转 ycb-video 格式" 反复出现 — 卖点是 mesh-free 但 issue 区落地为 "要么扫 mesh 要么没法用"。
- **实地后果**：onboarding 一个新物体 80% 时间花在资产对齐而非 pose 本身。低-poly CAD 通常 OK；过粗（< 100 face）或 normals 反向会让 scorer 退化但不会立刻报错，**silent failure 模式**。

### 8.7 光照 / 杂乱 / Tracking 失稳：score 涨不等于对

- **GitHub-validated**：[#233 (closed) "Score value goes up during occlusion"](https://github.com/NVlabs/FoundationPose/issues/233) — confidence 与正确性脱钩的危险模式；[#136 (open, 6c) "Detect when tracking is lost"](https://github.com/NVlabs/FoundationPose/issues/136) 至今无官方答案；[#279 (closed, 15c) "Large centroid error"](https://github.com/NVlabs/FoundationPose/issues/279)、[#131 (closed, 5c)](https://github.com/NVlabs/FoundationPose/issues/131) "tracking 失稳"。
- **实地后果**：闭环不能仅靠 scorer confidence 触发 grasp；必须叠 IoU mask 一致性 / depth residual 等独立 gate。

### 8.8 Maintainer 响应度：拐点信号

- **观察**：last code commit **2025-03-03**（一年多前），仅 2026-04-29 一次第三方 conda 修复 PR 合入；issue 区主要靠社区互助（savidini / Qiyue-Chen-robo 等贡献了实质 fix），核心作者 wenbowen123 2024-Q3 后基本停止回复。**未 merge 的关键 PR：#369 RTX 50、#364 TensorRT、#337 Dockerfile**。
- **判断**：repo 进入 *community-maintained foundation* 阶段（与 ontology §13.5 的 "foundation disputed" 互证 H7 maintainer responsiveness）。production 团队应假设：(a) 新硬件支持要自己 fork；(b) 关键修复要从 issue 评论区考古而非 README；(c) 2026+ 真正的接力可能来自 isaac_ros 分支或 BundleSDF 续作，而非 main repo。

### 8.9 与 ontology §13.5 / §10.2 的回灌

- §13.5 H5 real-time ❌ → **8.4 实证**（首帧 register 秒级，tracking 稳态 80–150 ms 与 30 FPS 阈值仍差 2-3×）。
- §13.5 M2 foundation disputed → **8.1 + 8.6 实证**（first-frame mask + 输入资产门槛吃掉真正"零样本"卖点）。
- §13.5 H7 maintainer responsiveness（如有此项）→ **8.8 实证**。
- 与 [`github_failure_atlas.md`](./github_failure_atlas.md) 已记录的 §6.x 同源；本节是按主题轴的二次切片。

---

## References

- FoundationPose — Wen et al. *CVPR 2024*（best paper）. https://arxiv.org/abs/2312.08344
- MegaPose — Labbé et al. *CoRL 2022*. https://arxiv.org/abs/2212.06870
- GDR-Net — Wang et al. *CVPR 2021*. https://arxiv.org/abs/2102.12145
- DenseFusion — Wang et al. *CVPR 2019*. https://arxiv.org/abs/1901.04780
- PoseCNN — Xiang et al. *RSS 2018*. https://arxiv.org/abs/1711.00199
- BOP. https://bop.felk.cvut.cz/

## Boundary

把 FoundationPose 解构为 **novel-object 6D pose foundation model**. 需 mesh 的前驱 → [`megapose_dissection.md`](./megapose_dissection.md). Per-embodiment 用法 → [`embodiments/manipulation/`](../../embodiments/manipulation/). Action 消费 → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./overview.md)
