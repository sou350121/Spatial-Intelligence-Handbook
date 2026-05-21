# Can VGGT (v1 + Ω) Replace Drone VIO? (VGGT 和 VGGT-Ω 能否取代无人机 VIO?)

> **发布时间**: 2026-05-20（v1.1 backfill 2026-05-21；翻译为简体中文 2026-05-21；**v1.2 加入 VGGT-Ω 对比 2026-05-22**）
> **论文 / 模型**: VGGT（Wang et al., *CVPR 2025*, [arXiv 2503.11651](https://arxiv.org/abs/2503.11651)）+ **VGGT-Ω**（Wang et al., 2026-05, [arXiv 2605.15195](https://arxiv.org/abs/2605.15195)）vs VINS-Fusion / OpenVINS / DROID-SLAM
> **核心定位**: feed-forward 3D foundation model 能否在 aerial 平台取代紧耦合 VIO —— 以及为什么答案因 embodiment 而异。**Ω 出来之后答案变了吗？没变。**

**Status:** v1.2 — VGGT-Ω 加入对比 2026-05-22。`UNVERIFIED` 数字需 rig-side 验证。
**Wedge tier:** W1 · **Handbook flagship**
**TL;DR:** **仍然不行**，2026 年内不行。VGGT-Ω 改了 training efficiency × data scale × dynamic scene 三件事 —— 但**没改 streaming / 没解 metric scale / 没改 inference latency budget**。差距仍是 *延迟、米制、IMU 耦合*。出货架构仍是混合（VGGT-Ω 当低速率几何锚 + 经典 VIO 跑高速率状态），不是替换。

**X-Ray.** 无人机要在桨叶振动 IMU 的同时，给出 200 Hz、米制、sub-10 ms 的状态估计 —— 经典 VIO 就是为此手工调出来的。VGGT v1 (2025) 单次前向就能从 N 帧 RGB 吐出位姿 + 稠密 3D；VGGT-Ω (2026-05) 把它做得更高效（30% GPU 内存 + 15× 训练数据）并**首次支持动态场景**（Sintel 提升 77%）—— 但 *推理 envelope* 与 v1 同构：仍 batch、仍 un-metric、仍 100ms+ latency。教训：feed-forward 3D 谱系正在 efficiency × scale 两条轴上演进，但 *streaming + metric + IMU 耦合* 这三件**架构性事**它们没碰 —— 也就是 aerial 真正的墙。

## 📍 研究全景时间线

```
2018       2020       2021         2024        2025          2026-05      2026-05-22    2027?
VINS-Mono ► OpenVINS ► DROID-SLAM ► DUSt3R ──► VGGT v1 ────► VGGT-Ω ────► YOU ARE HERE ► metric-aware FF
(opt-VIO)  (MSCKF-VIO) (learned BA) (2-view FF) (CVPR best,  (1 head +     hybrid           + streaming
                                                4-head batch) register    VGGT(-Ω) + VIO   + <20ms latency
                                                + static)    attn, 30%                     + IMU coupling
                                                             memory,
                                                             动态原生 ★)
└─ classical tightly-coupled ─┘    └─ learned ─┘  └─── feed-forward foundation 谱系 ──┘  └─ replacement?
```

本 wedge 仍卡在 *learned-BA*（DROID-SLAM）与 *feed-forward foundation*（DUSt3R → VGGT v1 → **VGGT-Ω**）的迁移线上。**Ω 把谱系往右推一段（efficiency + dynamic），但没跨过最后一条沟 —— streaming + metric + IMU 耦合。** Operational gap 仍很宽，时间轴仍短。

---

## 1 · 为什么这是最干净的跨 embodiment 测试

manipulation 研究员被问 "VGGT 能替代经典 SfM 吗？" → 耸肩，能。drone 工程师在 15 m/s 风切被问 → 一口回绝。**两个答案都对；它们的分歧告诉你 "spatial intelligence" 在每个 embodiment 上到底要什么。** 这条迁移故事（manipulation → ground → aerial → marine）正是单 embodiment 综述永远不写的维度 —— 也是这篇文章为什么住在 `crossing/`。

### 1.2 ⚡ Eureka Moment

> **VGGT 给出正确的*几何*，但永远给不到 aerial 控制器要的米制尺度和延迟 —— 差距是 operational，不是 accuracy。**

任何从"更好的 depth！更好的 tracking！更多视图！"角度切入这个问题的视角都是干扰。墙是 rate × latency × metric，benchmark accuracy 不是失败点。

---

## 2 · 数学核心：rate-latency-cost 乘积

### 📌 Napkin Formula

```
controller_rate × latency_budget  ≥  visual_rate × inference_cost
       (Hz)              (s)              (Hz)         (s·J·$)
```

视觉前端能为控制器服务 当且仅当 *控制器需求*（rate × 等待）大过 *视觉供给*（rate × 成本）。manipulation 上：不等式天然成立。aerial racing 上：翻转，单帧精度修不好这个翻转。

| Symbol | Manipulation | Aerial racing |
|---|---|---|
| controller_rate | 30 Hz | 200 Hz |
| latency_budget | 100 ms | 5 ms |
| visual_rate (v1) | VGGT v1 ~5 Hz ✅ | VGGT v1 ~5 Hz ❌ |
| visual_rate (Ω) `UNVERIFIED` | VGGT-Ω ~8-10 Hz? ✅ | VGGT-Ω ~8-10 Hz? ❌ |
| inference_cost | desktop GPU | Orin-class |

左边是*预算*；右边是*账单*。Ω 把账单做小一些（register attention linear-in-N + 移除 high-res conv），但**没改变量级** —— 仍是桌面 GPU 账单 vs autopilot 预算。两者 2026 不会相遇。

> **VGGT-Ω 的影响：** 30% 训练 GPU 内存提示**推理可能也轻一点**（`UNVERIFIED` ——论文未直接给 inference benchmark）。乐观估计 distilled Ω 在 Orin Nano 上跑到 ~10 Hz（vs v1 的 ~5 Hz）。**但 5 ms latency 的 aerial 控制环要求 200 Hz 视觉前端 —— 一个数量级的差距，Ω 没动。**

---

## 3 · 玩具例子：30 Hz 控制器、两个前端

慢速巡检无人机，30 Hz 控制器，每帧 50 ms latency 预算。

| 前端 | visual_rate | latency | Effective | 判决 |
|---|---|---|---|---|
| **VINS-Fusion** | 30 Hz cam + 200 Hz IMU | ~5 ms / <1 ms | **200 Hz**, ≤10 ms | ✅ 出货 |
| **VGGT v1 distilled** `UNVERIFIED` | ~10 Hz | 100 ms | **10 Hz**, 100 ms | ❌ 超预算 2× |
| **VGGT-Ω distilled** `UNVERIFIED` | ~10-15 Hz? | 50-100 ms? | **10-15 Hz**, ~70 ms | ⚠️ 边缘临界 |

算账：
- VINS：`30 × 0.050 = 1.5 vs 30 × 0.005 = 0.15` → 10× 余量 → 出货。
- VGGT v1：`30 × 0.050 = 1.5 vs 10 × 0.100 = 1.0` → 临界；桨叶抖动让它跌穿预算。
- **VGGT-Ω**：register attention linear-in-N + 训练 memory 30% 提示推理也可能~30-50% 提升。**乐观估计：** `1.5 vs 12 × 0.080 ≈ 0.96` → 仍在临界以内但更稳。**悲观估计：** Ω 的 inference latency 论文没披露，预期 v1 几乎不变 → 仍不行。

⚠️ **关键：Ω 改的层不解 §2 不等式的右侧 quadratic 项**。Register attention 把*跨帧 attention*的 quadratic 砍掉，但单帧的 encoder 仍要算；总 inference latency 主要 bottleneck 不在 cross-frame attention 而在 encoder + dense head。

位姿精度无关。**v1 也好、Ω 也好，答案都是不**（除非 distill 到 <20 ms latency —— 这是论文 §9 的预测）。

---

## 4 · Aerial VIO 基线（VGGT 要对照的标杆）

四条不可妥协的约束：

| 需求 | 为什么 | 典型数字 |
|---|---|---|
| **Rate ≥ 100 Hz** | 级联姿态控制器带宽 | 200 Hz |
| **Latency ≤ 10 ms** | Cam → 估计 → 控制器 → 电机 | 5–15 ms 调好的 VINS |
| **米制 (Metric scale)** | 位置以米计；油门用 m/s² | init 后 <2% 误差 |
| **抗桨叶 IMU 干扰** | 桨叶 100–400 Hz 激发 IMU | 减震 + 1 kHz IMU + 带通 |

参考栈：**VINS-Mono / Fusion**（Qin 2018, HKUST）紧耦合 opt-VIO；**OpenVINS**（Geneva 2020, UDel）MSCKF，Skydio 系；**DROID-SLAM**（Teed 2021）学习式稠密 BA，Orin 上 ~5 Hz `UNVERIFIED`，没 first-class IMU。这是 VGGT 要清的栏。

---

## 5 · VGGT 谱系实际给什么（v1 + Ω 对比）

| Metric | VGGT v1 (CVPR 2025) | **VGGT-Ω (arXiv 2605, 2026-05)** | 改进? |
|---|---|---|---|
| 架构 | 4 separate heads | **1 dense head + multi-task** | ✅ 效率 |
| Cross-frame attention | Global N×N | **Register attention (N × 16)** | ✅ memory/速度 |
| GPU memory (training) | 100% baseline | **30%** | ✅ 训练 |
| Supervised data 规模 | baseline | **15×** | ✅ 数据 |
| Self-supervised on video | ❌ | ✅ | ✅ scale |
| 动态场景 | ❌ 静态假设 | **✅ 原生支持** | ✅ 应用 |
| Sintel camera estimation | baseline | **+77%** vs 之前 SOTA | ✅ benchmark |
| **推理 latency (Orin Nano, distilled)** `UNVERIFIED` | 100-200 ms | **50-100 ms?** (`UNVERIFIED` —— Ω 论文未直接披露 inference latency) | ⚠️ 可能改但量级不变 |
| **Streaming** | ❌ batch-only | ❌ **仍 batch-only** | ❌ **不改** |
| **Metric scale** | ❌ un-metric | ❌ **仍 un-metric** | ❌ **不改** |
| **IMU 耦合** | ❌ | ❌ | ❌ **不改** |
| 抗振动训练先验 | ❌ | ❌ | ❌ **不改** |

**关键观察**：

1. ✅ Ω 在 *效率 × 训练数据 × 动态场景* 上是真升级 —— Sintel 77% 提升 + dynamic scene 是质变
2. ❌ Ω **完全没碰** aerial 真正卡住的 4 条：streaming / metric / IMU coupling / 振动抗扰
3. ⚠️ inference latency 期待 Ω 比 v1 略快（register attn linear-in-N），但量级不变（仍是 50-200 ms 而非 < 20 ms）

良性轨迹上：v1 和 Ω 都跟经典 VIO 对得上几何精度。**它们栽都栽在同一个 operational envelope，不是 metric。Ω 出来的事实改变不了这点。**

---

## 6 · Gap matrix + 隐含假设

|  | Manip desktop | Ground AGV | Aerial slow | Aerial racing | Marine AUV |
|---|---|---|---|---|---|
| Rate | 30 Hz | 30 Hz | 30 Hz | **200 Hz** | 5 Hz |
| Latency | 100 ms | 50 ms | 50 ms | **5 ms** | 200 ms |
| Metric scale | 可选 | 需要（GNSS）| 需要 | **需要（无 fallback）** | 需要（DVL）|
| IMU coupling | 不需要 | 弱 | 中 | **强** | 强 |
| VGGT 当主前端? | ✅ 出货 | ⚠️ + GNSS | ⚠️ + IMU | ❌ rate+latency | ❌ 视觉失效 |
| Hybrid 模式 | 无 | 前端 | 前端 | 后端 loop closure | 后端 loop closure |

纵看：VGGT 强在 *良性条件下的几何正确*；弱在 *aerial 把基线都拉到极端的任何东西*。横看："VGGT 能替代 VIO 吗？" 有五个不同答案 —— **这就是 `crossing/` 存在的全部意义。**

### 6.1 Hidden Assumptions（VGGT 在哪里悄悄崩）

VGGT 在 manipulation / ground 的成功，建立在 drone 一出实验室就违反的几个假设上：

- **静态场景** —— 训练分布偏拟静态；旋翼下洗扬尘、巡检工地工人、编队飞行 都破坏 rigid-world prior。
- **足够视图重叠** —— N-view 假设帧间内容共享；快速偏航或无特征墙面会让几何坍塌。
- **单目非米制** —— 前向 pass 里没尺度；米制控制器要外部 scale（stereo / RTK / 已知物体）。
- **板载 GPU** —— VGGT-large ~6 GB `UNVERIFIED`；小型无人机带的是 Orin Nano（8 GB 共享）或更少；持续推理功耗没有预算。
- **没有 native IMU 耦合** —— 没地方接 200 Hz IMU pre-integration；hybrid pose-graph 融合是外挂，会吃几十 ms。

任何一条都能悄悄拖垮 aerial；合在一起，就是 §2 那个不等式翻转的结构性原因。

---

## 7 · Hybrid 甜蜜点在哪

2026 真正能出货的是 "VGGT *和* VIO，各司其职"：

```
   ~5 Hz   ┌─VGGT (feed-forward)─┐
   ──────► │ 全局 pointmap +     │──► 闭环 / 地图合并
           │ 漂移修正             │
           └─────────┬───────────┘
                     │ pose-graph 融合
                     ▼
  200 Hz   ┌─紧耦合 VIO─────────┐
  IMU ───► │ MSCKF / 滑动窗口   │──► 控制器 @ 200 Hz
  30 Hz    │ (米制 + 快)        │
  cam ───► └────────────────────┘
```

VGGT = 低速率、无漂移的几何锚；经典 VIO = 高速率米制状态。VGGT 每完成一次全局解，pose graph 就重优化一遍。

变体：**VGGT 只做 relocalization**（最简单 —— VIO 照旧跑，VGGT 处理绑架恢复）；**VGGT pointmap 当 MSCKF 测量**（深度当延迟视觉观测）；**端到端 neural VIO + VGGT 类编码器**（研究阶段；DROID 谱系，"learned MSCKF"）。

### 7.1 Comparison & Interview Tip

| 栈 | Rate | Latency | Metric? | IMU? | 动态场景? | Aerial 2026? |
|---|---|---|---|---|---|---|
| VINS-Fusion / OpenVINS | 200 Hz | 5–15 ms | ✅ | 紧耦合 | OK | ✅ |
| DROID-SLAM | ~5 Hz | ~200 ms | 部分 | 弱 | 弱 | ❌ |
| VGGT v1 (large) | ~5 Hz | 200–400 ms | ❌ | ❌ | ❌ | ❌ |
| **VGGT-Ω** `UNVERIFIED` | ~5-10 Hz? | 100-200 ms? | ❌ | ❌ | ✅ ★ | ❌ |
| VGGT v1 distilled + VIO hybrid | 200 Hz VIO / 5 Hz v1 | 5–15 ms 经 VIO | ✅ 经 VIO | 经 VIO | ⚠️ 静态 | ⚠️ 低速可 |
| **VGGT-Ω distilled + VIO hybrid** | 200 Hz VIO / ~10 Hz Ω | 5–15 ms 经 VIO | ✅ 经 VIO | 经 VIO | **✅** | ⚠️ 低速可（+巡检动态 OK） |

**Ω 对 hybrid 架构的真正贡献**：因为 Ω 原生支持动态场景，hybrid VGGT-Ω + VIO 现在能在 **行人 / 工地 / 仓库** 这种动态环境工作（v1 hybrid 在动态环境下静默漂移）。这是 **巡检 drone** 的真实改进。

> **🎤 Interview Tip.** "VGGT-Ω 出来了，无人机要不要换？" —— 正确答："**Ω 改的是训练效率 + 数据规模 + 动态场景支持**，aerial inference envelope 一点没动 —— 仍是混合架构题，不是替换题。但如果你的无人机巡检场景动态环境多（工地、仓库、行人），**hybrid Ω + VIO 比 hybrid v1 + VIO 更稳**，因为 v1 在动态环境下静默退化。" 错答："Ω 更高效所以替换 VIO" —— Ω 改的层和 VIO 不在一个轴。

---

## 8 · 为什么 marine 根本不参加这场辩论

水下：视觉描述子失效（吸收 + 散射毁纹理），单目尺度没主动测距完全没救，GPS 没了。**VGGT 通过单目 RGB 把这些全部继承下来。** marine SLAM 用 sonar + DVL + IMU；相机是辅助。"VGGT vs VIO" 无论怎么打都输给声学 —— 这个 contrasting case 定义了视觉-only feed-forward 3D 的上限。

---

## 9 · 2 年展望（什么会翻转 aerial 答案？）

四件事都落地才会翻转：

1. **VGGT-Ω 后代蒸馏到 Orin <20 ms latency** —— 现在 Ω 训练 memory 是 v1 的 30%，提示推理也可能更轻；但实际 distilled 数字论文未披露，预期 50-100 ms 量级。还需 ~5× 进一步压缩到 < 20 ms。**2027 内可能。**
2. **Metric-aware feed-forward 变体** —— 把 stereo / IMU / known scale anchor 融进前向 pass。**Ω 没做这件事 —— 这是下一篇论文的押注**。盯 π³ streaming / 任何"VGGT-Σ / VGGT-Metric"风格的后续。
3. **Streaming feed-forward 3D** —— Ω 仍 batch-only。Register attention 天然适配 streaming（register 当 state cache），所以这是 Ω 架构留给后续的 hint。**[Streaming Visual Geometry Transformer](https://arxiv.org/abs/2507.11539) 这条路在走，但未到生产级。**
4. **抗振动前端** —— ViT 类（含 v1 / Ω）还没在高频运动模糊下专项调过；Ω 的 self-supervised on unlabeled video **可能间接帮**（视频里有自然抖动）。UZH RPG event camera 仍是最强对冲。
5. **能容忍 20–40 ms 级联 latency 的控制器** —— RL policy (UZH 赛车) 已经能；PID 不行。

五条（v1.2 加 streaming 是第三条）都可解。Ω 解了"训练效率 + 动态场景"两件 *相关* 事但不在关键链上 —— **2026 没有任何一条核心条到位。**

**Falsifiable predictions（v1.2 更新）**：

1. **2027-06 前**：会出现 VGGT-Ω 衍生 streaming variant（可能叫 VGGT-Σ 或类似），把 batch 改成 increment-per-frame。Register attention 是 streaming 的天然 cache。
2. **2027-12 前**：会有一篇公开的无人机自主 stack 论文，用 VGGT 谱系模型当 *主*视觉前端 —— 但飞 <5 m/s 室内 / 巡检，不是 racing。
3. **2027-12 前不会发生**：VGGT 谱系（含 Ω 后代）成为 Skydio-class 户外 racing aerial 主前端 —— operational envelope 限制不在 Ω 改的层。

任何"VGGT-Ω 在 Skydio 级户外任务上替代 VIO" 的主张都该被对赌反对。

---

## 10 · For the reader

- **Manipulation 工程师** —— 这些原语在你身上 port 得很干净；VGGT *就是*你的新 SfM。别把这边的时序假设带进 aerial。
- **Aerial 工程师** —— 别因此就 dismiss VGGT。它不适合控制环，但是你这辈子能见过的最便宜的 relocalizer / loop-closer。
- **AD 工程师** —— driving = ground-mobile + GNSS。VGGT 类模型在你这里最闪光是 *离线 4D 场景重建*（看 Cosmos），不是在线估计器。
- **Marine 工程师** —— VGGT 不适用；老老实实 sonar + DVL + IMU。视觉-only FF 是思考实验，不是 stack。
- **研究者** —— §9 四条都是开放问题。Metric-aware feed-forward 是最大的解锁，谁先发出来谁赢两个 CVPR。

---

## References

- VGGT v1 — Wang et al. *CVPR 2025 best paper* [arXiv:2503.11651](https://arxiv.org/abs/2503.11651)
- **VGGT-Ω** — Wang et al. 2026-05 [arXiv:2605.15195](https://arxiv.org/abs/2605.15195) · 中文导读 [Alan Hou](https://alanhou.org/blog/arxiv-vggt-/)
- VINS-Mono — Qin et al. *T-RO 2018* https://arxiv.org/abs/1708.03852
- OpenVINS — Geneva et al. *ICRA 2020* https://arxiv.org/abs/1910.00298
- DROID-SLAM — Teed & Deng *NeurIPS 2021* https://arxiv.org/abs/2108.10869
- UZH RPG champion racing — Kaufmann et al. *Nature 2023* https://www.nature.com/articles/s41586-023-06419-4
- Streaming Visual Geometry Transformer — [arXiv:2507.11539](https://arxiv.org/abs/2507.11539)（streaming 路线）
- Skydio autonomy blog — https://www.skydio.com/blog
- VGGT v1 完整解构 → [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../../foundations/feed-forward-3d/vggt_cvpr2025_dissection.md)
- VGGT-Ω 完整解构 → [`foundations/feed-forward-3d/vggt_omega_dissection.md`](../../foundations/feed-forward-3d/vggt_omega_dissection.md)（v0.5 verified）

## Boundary

本文比较的是跨 embodiment 的*方法类*。Per-method dissection 在 `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`（VGGT）和 `embodiments/aerial/vio/`（VINS-Mono）。从那两边引用本文，是因为只有这边有跨 embodiment 视角。

---

*Last opinion update: 2026-05-20. §9 预测 2027-12 打分。*
