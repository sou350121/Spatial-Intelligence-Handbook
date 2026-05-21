# RAFT (光流的迭代细化)

> **发布时间**: 2020-08 (ECCV 2020 *best paper* — Teed & Deng, Princeton)
> **论文 / 模型**: RAFT — Recurrent All-Pairs Field Transforms (arXiv 2003.12039)
> **核心定位**: 取代 FlowNet / PWC-Net 并主宰 optical-flow leaderboard 约 5 年的架构. 在 4D 相关 volume 上迭代精化.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · 经典 *密集* 像素运动原语.
**TL;DR:** RAFT 用 "一次构建相关 volume，用 GRU 迭代精化" 替换 single-shot CNN flow. 比 FlowNet2 少 ~10× 参数，在 Sintel / KITTI 上大涨，是之后每个成功 flow 模型（GMA、FlowFormer、SEA-RAFT）的模板.

**X-Ray.** RAFT 之前，optical flow 是一栈 encoder-decoder 网络一次性 regress flow. RAFT *把视觉匹配（corr volume）与 flow 估计（小 GRU）分开*并迭代. 5 年 leaderboard 主宰，是 DROID-SLAM、VGGT tracking head 和多数匹配 pipeline 的模板. 对机器人：悄悄驱动 DROID-SLAM 和多数 flow-conditioned policy 的原语.

---

## 📍 研究全景时间线

```
2015        2017       2018       2020 (HERE)        2022          2024
FlowNet ──► FlowNet2 ─► PWC-Net ─► RAFT ───────────► GMA / FF ───► SEA-RAFT
└── single-shot CNN regression ───┘  └── iterative refinement + correlation volume ───┘
```

从 encoder-decoder regression 到 iterative-refinement-on-correlation-volume 的转折. 每个现代 flow 模型都是 RAFT 后裔.

---

## 1 · 架构总览

### 1.1 系统组件对比

| Module | Input | Output | Freq |
|---|---|---|---|
| Feature encoder | 2 frames | `g_1`, `g_2` (H/8 × W/8 × D) | Per pair |
| Context encoder | frame 1 | GRU context | Once |
| 4D corr volume | `g_1, g_2` | `C(x,y,u,v)` | Per pair |
| Lookup | `C` + flow | local patch | Per iter |
| GRU updater | lookup + ctx + flow | residual `Δf` | `K=12/32` |

### 1.2 ⚡ Eureka Moment

> **一次构建 correlation volume；在便宜局部 lookup 上迭代 flow 精化. 几何匹配 = 昂贵 setup；精化 = 便宜循环.**

Single-shot CNN regression 让网络一口气学一切 — 匹配、平滑、遮挡. RAFT 把匹配做成闭式 correlation volume，只让网络学*精化*. 这一步带来 2020 精度跃升.

### 1.3 信息流

```
   F1,F2 ─► feat enc ─► g_1, g_2 ─► 4D corr ─► C(x,y,u,v)
   F1 ─► ctx enc ──► h_ctx                 │
                                           ▼
   f_0=0 ─► [GRU loop ×K: lookup→GRU→f+=Δf] ─► f_K ─► upsample
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  f_{t+1}  =  f_t  +  GRU( lookup(C, f_t),  context )
```

`t+1` 的 flow = `t` 的 flow + 从*当前 flow 猜测周围*的相关值学到的修正. `C` 一次构建；GRU 在局部 lookup 上廉价迭代.

| Symbol | Meaning |
|---|---|
| `f_t` | 第 `t` 次迭代的 flow field |
| `C(x,y,u,v)` | `(x,y)` 与 `(x+u, y+v)` 的特征相似度 |
| `lookup` | 当前 flow 周围对 `C` 的双线性采样 |
| `K` | 迭代数（训 12、测 32）|

**Intuition.** `C` 是相似度图. GRU 在当前 flow 猜测周围放大，决定往哪个方向 nudge. 迭代次数随位移*温和*增长 — 不像经典金字塔指数增长.

---

## 3 · Worked example: KITTI 2-frame clip

1242×375 帧，60 km/h 车.

1. **Encode features.** 1/8 分辨率 2 个 map. ~5 ms `UNVERIFIED`.
2. **Build corr volume.** ~150×47 × 150×47 ≈ 5e7 entries 一次 matmul. ~10 ms `UNVERIFIED`.
3. **Initialize.** `f_0 = 0`.
4. **Iterate** `t = 0..11`: 在当前 flow 周围 lookup 7×7 corr patch，GRU 产出 `Δf`（几迭代后 <1 px）. ~1.5 ms × 12 ≈ 18 ms `UNVERIFIED`.
5. **Upsample.** Convex 1/8 → 全分辨率. ~3 ms.

桌面每对总 ~40 ms `UNVERIFIED`. KITTI EPE ~1.5 px `UNVERIFIED`. FlowNet2 single-shot 花更多且输精度.

---

## 4 · Engineering view: corr-volume 内存墙

| Input res | Corr volume `UNVERIFIED` | GPU mem `UNVERIFIED` | RT Orin? |
|---|---|---|---|
| 320×240 | ~1.4e6 | ~50 MB | ✅ ~30 Hz |
| 1024×768 | ~1.5e8 | ~600 MB | marginal |
| 4K | ~1e10 | doesn't fit | ❌ |

4D volume 是**单一最大工程约束** — `O(H²W²)`. VGA OK，4K 爆炸. SEA-RAFT 等用多尺度 / 稀疏相关解决.

**Deployment.** 自监督深度 / VIO 的 photometric loss. Gripper-relative flow 作为 policy state. DROID-SLAM 的 per-pixel correspondence 复用 RAFT correlation volume（Teed 自家后续）.

---

## 5 · Data & eval

FlyingChairs → FlyingThings3D → Sintel / KITTI fine-tune. Sintel-clean test EPE ~1.6，KITTI-2015 Fl-all ~5% `UNVERIFIED`. 多年在这些上 top-or-near，直到 2023 年代 attention 变体（FlowFormer、GMA-RAFT）勉强超过.

---

## 6 · Capabilities & failure modes

**Capabilities.** 密集 per-pixel flow + 强泛化. 通过迭代具备大位移能力. 小（~5M vs FlowNet2 ~160M）— 易嵌入.

**Failure modes.** 太阳眩光 / 饱和打破亮度恒定. 细结构（线、栏杆）拿到背景 flow. 无特征区 → 无 corr 峰；GRU 幻觉平滑场. 无 fine-tune 时夜晚 / 天气域偏移.

### 6.1 Hidden Assumptions

- **小位移.** 位移 >~图像宽度 20% 难收敛. 空中 / 快速运动违反.
- **亮度恒定.** Auto-exposure / 阴影穿越移动 corr 峰.
- **静态相机或静态场景.** 不分离 ego 与场景运动 — 下游必须做.
- **无遮挡.** 遮挡区拿到一个 flow 值但是外推；需要遮挡 mask（非官方输出 `UNVERIFIED`）.
- **Photometric 一致.** 镜面 / 透明表面违反点积匹配.

这些破坏时，*flow 看着仍 OK* 但错 — 静默失败.

---

## 7 · Comparison & interview tip

| Model | Year | Params `UNVERIFIED` | Style | Sintel EPE `UNVERIFIED` |
|---|---|---|---|---|
| FlowNet2 | 2017 | ~160M | single-shot | ~3.0 |
| PWC-Net | 2018 | ~9M | pyramid | ~2.6 |
| **RAFT** | 2020 | **~5M** | **iter on 4D corr** | **~1.6** |
| GMA | 2021 | ~6M | iter + attention | ~1.4 |
| FlowFormer | 2022 | ~16M | transformer iter | ~1.2 |
| SEA-RAFT | 2024 | ~10M | iter + efficient | ≈ RAFT |

> **🎤 Interview Tip.** "为什么 5 年后 RAFT 仍经典？" — *"两个想法：4D corr volume 一次给几何 oracle；局部 lookup 上的迭代 GRU 参数高效且能大位移. 每个成功 follow-up 都是 RAFT 变体 — 调精化器或压 volume，但架构是 RAFT 的."* "FlowNet 风" 错过迭代精化革命.

---

## References

- RAFT — *ECCV 2020*（best paper）. https://arxiv.org/abs/2003.12039
- DROID-SLAM — *NeurIPS 2021*. https://arxiv.org/abs/2108.10869
- PWC-Net — *CVPR 2018*. https://arxiv.org/abs/1709.02371
- FlowNet2 — *CVPR 2017*. https://arxiv.org/abs/1612.01925
- GMA — *ICCV 2021*. https://arxiv.org/abs/2104.02409
- FlowFormer — *ECCV 2022*. https://arxiv.org/abs/2203.16194

## Boundary

**密集 optical-flow foundation 原语**. 稀疏 / 长时序 point tracking → [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md). SLAM 中 corr volume → [`../classical-slam/`](../classical-slam/). Flow 作 policy 输入 → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./README.md)
