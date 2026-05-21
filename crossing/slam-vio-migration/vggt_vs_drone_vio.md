# Can VGGT Replace Drone VIO? (VGGT 能否取代无人机 VIO?)

> **发布时间**: 2026-05-20（v1.1 backfill 2026-05-21；2026-05-21 翻译为简体中文）
> **论文 / 模型**: VGGT（Wang et al., *CVPR 2025*）vs VINS-Fusion / OpenVINS / DROID-SLAM
> **核心定位**: feed-forward 3D foundation model 能否在 aerial 平台取代紧耦合 VIO —— 以及为什么答案因 embodiment 而异。

**Status:** v1.1 — opinionated draft。Backfilled to AGENTS.md 14-item dissection template 2026-05-21；翻译为简体中文 2026-05-21。`UNVERIFIED` 数字需 rig-side 验证。
**Wedge tier:** W1 · **Handbook flagship**
**TL;DR:** 不行，2026 年内不行。差距不在精度，而在 **延迟、度量尺度、IMU 耦合**。真正出货的是混合架构（VGGT 当低速率几何锚点 + 经典 VIO 跑高速率状态），不是替换。

**X-Ray.** 无人机要在桨叶振动 IMU 的同时，给出 200 Hz、米制、sub-10 ms 的状态估计 —— 经典 VIO 就是为此手工调出来的。VGGT (2025) 单次前向就能从 N 帧 RGB 吐出位姿 + 稠密 3D：在桌面 / 地面环境几何上极漂亮，但**频率错、非米制、IMU 没耦合**。教训：feed-forward 3D 会比改写 aerial 内控环更早改写 manipulation / AD 的前端 —— 真正卡住的是 *operational envelope*（rate × latency × metric），不是精度。

## 📍 研究全景时间线

```
2018       2020       2021         2024        2025          2026               2027?
VINS-Mono ► OpenVINS ► DROID-SLAM ► DUSt3R ──► VGGT (CVPR) ► YOU ARE HERE ────► metric-aware FF
(opt-VIO)  (MSCKF-VIO) (learned BA) (2-view FF) (N-view FF)   hybrid VGGT+VIO    + <20ms latency
└─ classical tightly-coupled ─┘    └─ learned dense ─┘  └─ feed-forward foundation ─┘  └─ replacement?
```

本 wedge 卡在 *learned-BA*（DROID-SLAM）与 *feed-forward foundation*（DUSt3R → VGGT）之间。问题：右向箭头能不能到达经典 VIO 自 2018 年以来占据的高速率 / 米制 / 紧 IMU 耦合区？时间轴短；operational gap 很宽。

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
| visual_rate | VGGT ~5 Hz ✅ | VGGT ~5 Hz ❌ |
| inference_cost | desktop GPU | Orin-class |

左边是*预算*；右边是*账单*。VGGT 的账单按桌面 GPU 算；aerial 预算按 autopilot 算。两者 2026 不会相遇。

---

## 3 · 玩具例子：30 Hz 控制器、两个前端

慢速巡检无人机，30 Hz 控制器，每帧 50 ms latency 预算。

| 前端 | visual_rate | latency | Effective | 判决 |
|---|---|---|---|---|
| **VINS-Fusion** | 30 Hz cam + 200 Hz IMU | ~5 ms / <1 ms | **200 Hz**, ≤10 ms | ✅ 出货 |
| **VGGT-distilled** `UNVERIFIED` | ~10 Hz | 100 ms | **10 Hz**, 100 ms | ❌ 超预算 2× |

- VINS：`30 × 0.050 = 1.5 vs 30 × 0.005 = 0.15` → 10× 余量 → 出货。
- VGGT：`30 × 0.050 = 1.5 vs 10 × 0.100 = 1.0` → 临界；桨叶抖动让它跌穿预算。

位姿精度无关。**这就是为什么答案是不。**

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

## 5 · VGGT 实际给什么

VGGT（Wang 2025, CVPR best paper, Meta + Oxford）—— feed-forward transformer：N 帧 RGB → poses + depth + pointmaps + 2D tracks，单次前向。架构动作：**没有 per-scene 优化、没有 BA 循环、没有 IMU**。

Orin Nano 上，FP16 + token reduction `UNVERIFIED`：

| Metric | VGGT-large | VGGT-distilled `UNVERIFIED` |
|---|---|---|
| Rate | ~5 Hz | ~10 Hz |
| Latency | 200–400 ms | 100–200 ms |
| Scale | Un-metric | Un-metric |
| GPU mem | ~6 GB | ~3 GB |
| EuRoC | ≈ VINS-Fusion | 2–4× error `UNVERIFIED` |

良性轨迹上：VGGT 跟经典对得上。**它栽是栽在 operational envelope，不是 metric。**

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

| 栈 | Rate | Latency | Metric? | IMU? | Aerial 2026? |
|---|---|---|---|---|---|
| VINS-Fusion / OpenVINS | 200 Hz | 5–15 ms | ✅ | 紧耦合 | ✅ |
| DROID-SLAM | ~5 Hz | ~200 ms | 部分 | 弱 | ❌ |
| VGGT (large) | ~5 Hz | 200–400 ms | ❌ | ❌ | ❌ |
| VGGT-distilled + VIO hybrid | 200 Hz VIO / 5 Hz VGGT | 5–15 ms 经 VIO | ✅ 经 VIO | 经 VIO | ⚠️ 低速可 |

> **🎤 Interview Tip.** "无人机上选 VGGT 还是 VINS-Fusion？" —— 正确答："**VINS-Fusion 跑控制环里，VGGT 当环外 relocalizer / 地图锚** —— 是混合架构题，不是替换题。" "直接用 VGGT" → 没算 rate × latency。"忽略 VGGT" → 把免费的漂移修正白送了。

---

## 8 · 为什么 marine 根本不参加这场辩论

水下：视觉描述子失效（吸收 + 散射毁纹理），单目尺度没主动测距完全没救，GPS 没了。**VGGT 通过单目 RGB 把这些全部继承下来。** marine SLAM 用 sonar + DVL + IMU；相机是辅助。"VGGT vs VIO" 无论怎么打都输给声学 —— 这个 contrasting case 定义了视觉-only feed-forward 3D 的上限。

---

## 9 · 2 年展望（什么会翻转 aerial 答案？）

四件事都落地才会翻转：

1. **VGGT 蒸馏到 Orin <20 ms latency** —— 现在蒸馏后 100–200 ms；还需 ~10× 压缩。2027 内有可能。
2. **Metric-aware feed-forward 变体** —— 把 stereo / IMU 融进前向 pass。盯 π³ streaming。
3. **抗振动前端** —— ViT 还没在高频运动模糊下调过。UZH RPG event camera = 对冲。
4. **能容忍 20–40 ms 级联 latency 的控制器** —— RL policy (UZH 赛车) 已经能；PID 不行。

四条都可解。2026 没有任何一条到位。

**Falsifiable prediction:** 2027-12 之前，会有一篇公开的无人机自主 stack 论文，用 VGGT 谱系模型当 *主*视觉前端 —— 但飞 <5 m/s 室内，不是 racing。任何"VGGT 这代在 Skydio 级户外任务上替代 VIO" 的主张都该被对赌反对。

---

## 10 · For the reader

- **Manipulation 工程师** —— 这些原语在你身上 port 得很干净；VGGT *就是*你的新 SfM。别把这边的时序假设带进 aerial。
- **Aerial 工程师** —— 别因此就 dismiss VGGT。它不适合控制环，但是你这辈子能见过的最便宜的 relocalizer / loop-closer。
- **AD 工程师** —— driving = ground-mobile + GNSS。VGGT 类模型在你这里最闪光是 *离线 4D 场景重建*（看 Cosmos），不是在线估计器。
- **Marine 工程师** —— VGGT 不适用；老老实实 sonar + DVL + IMU。视觉-only FF 是思考实验，不是 stack。
- **研究者** —— §9 四条都是开放问题。Metric-aware feed-forward 是最大的解锁，谁先发出来谁赢两个 CVPR。

---

## References

- VGGT — Wang et al. *CVPR 2025* [arXiv TBD]
- VINS-Mono — Qin et al. *T-RO 2018* https://arxiv.org/abs/1708.03852
- OpenVINS — Geneva et al. *ICRA 2020* https://arxiv.org/abs/1910.00298
- DROID-SLAM — Teed & Deng *NeurIPS 2021* https://arxiv.org/abs/2108.10869
- UZH RPG champion racing — Kaufmann et al. *Nature 2023* https://www.nature.com/articles/s41586-023-06419-4
- π³ streaming feed-forward variant — TBD
- Skydio autonomy blog — https://www.skydio.com/blog
- VGGT-Ω 后继 → [`foundations/feed-forward-3d/vggt_omega_dissection.md`](../../foundations/feed-forward-3d/vggt_omega_dissection.md)（v0.1 placeholder）

## Boundary

本文比较的是跨 embodiment 的*方法类*。Per-method dissection 在 `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`（VGGT）和 `embodiments/aerial/vio/`（VINS-Mono）。从那两边引用本文，是因为只有这边有跨 embodiment 视角。

---

*Last opinion update: 2026-05-20. §9 预测 2027-12 打分。*
