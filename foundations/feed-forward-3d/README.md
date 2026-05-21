# 🔮 Feed-Forward 3D — Explorer's Map

> **3D 不再是离线拟合的目标，而是单次 transformer 前向就能输出的 tensor。**
>
> 2020-2024 NeRF / 3DGS 是 per-scene 拟合；2024 DUSt3R 把成对前向打通；2025-2026 是 **feed-forward foundation model 时代** — VGGT、VGGT-Ω、MapAnything 三件套互补，把 efficiency × dynamic × **metric** 三条核心轴各解一条。
>
> 目前收录 **3 篇深度解析** + 本 region 导读。

&nbsp;

## 📍 三件套时间线 (2025-03 → 2026-05)

```
       2025-03                  2025-09 (v1) / 2026-01 (v2)         2026-05
     ───────────                ───────────────────────────         ───────────
     ┌──────────┐               ┌─────────────────────┐            ┌──────────┐
     │  VGGT    │ ──────────►   │   MapAnything ★      │ ──────►   │ VGGT-Ω ★ │
     │   v1     │               │   metric solved!      │            │ efficient│
     │ CVPR best│               │                       │            │  scale   │
     │          │               │   factored repr:      │            │          │
     │ 4 heads  │               │   (D × R × T × s)     │            │ 1 dense  │
     │ N-view   │               │   12+ tasks unified   │            │  head    │
     │ batch    │               │   1B param 开源       │            │ register │
     │ un-metric│               │                       │            │ attn 16  │
     │ static   │               │                       │            │ 30% mem  │
     │          │               │                       │            │ dynamic ★│
     └──────────┘               └─────────────────────┘            └──────────┘
                                                                                
     谱系开创                    metric breakthrough                  efficiency
     un-metric / 4-head          (factored representation)            + scale
                                                                                
                                ↓                                              
                                                                                
                          ╔═════════════════════════════════════════╗
                          ║  下一代 (2027?)                          ║
                          ║  metric + register attn + streaming     ║
                          ║  + IMU coupling + edge real-time         ║
                          ╚═════════════════════════════════════════╝
```

**关键洞察**：MapAnything 与 VGGT-Ω 是 Meta **同期并行的两条路线**（部分作者重叠 — Schönberger 在两篇论文都署名）：

- **MapAnything**（2025-09 / 2026-01）解 **metric scale** — factored representation 把 (depth, ray, pose, **scale**) 分解
- **VGGT-Ω**（2026-05）解 **efficiency + dynamic** — register attention + 自监督 + 30% 训练内存

**两者互补不竞争**。下一代很可能是 *factored repr + register attn* 两个 idea 合一。

&nbsp;

---

&nbsp;

## 🔍 三件套对照（一眼看差异）

### 表 1 · 谁解了什么

| 模型 | **Metric?** | **训练效率** | **动态场景** | **任务统一** | **开源** | 主要 differentiator |
|---|:---:|---|:---:|---|:---:|---|
| **VGGT v1** | ❌ | baseline | ❌ 静态 | 4-head 单任务 | ✅ Meta | N-view feed-forward 谱系开创 |
| **VGGT-Ω** | ❌ | **30% memory ★** | **✅ ★** | 1 dense head + multi-task | likely | register attention + 自监督 |
| **MapAnything** | **✅ ★** | — | `UNVERIFIED` | **12+ tasks** ★ | ✅ HF 46k/月 | **factored repr + metric ★** |

&nbsp;

### 表 2 · 输入 → 输出（上下游）

| 模型 | **🔼 上游 (input)** | **📦 输出 (output)** |
|---|---|---|
| VGGT v1 | N RGB (batch, N ≤ 30) | poses + depth + pointmap + 2D tracks |
| VGGT-Ω | N RGB (batch, register attn 让 N 可扩) | poses + depth + pointmap + tracks (single dense head) |
| **MapAnything** | **N RGB + 可选 (K / pose / partial depth / partial recon)** | **米制 3D：(D_i, R_i, T_i, scalar s) 因子化** |

&nbsp;

### 表 3 · 推理 / 部署

| 模型 | 推理 latency `UNVERIFIED` | 模型大小 | GPU 门槛 | License |
|---|---|---|---|---|
| VGGT v1 (distilled) | 100-200 ms (Orin Nano) | ~3 GB / ~6 GB | Orin Nano OK | likely Apache 2 |
| VGGT-Ω (distilled) | ~50-100 ms? | ~30% of v1 memory | Orin Nano OK | likely Apache 2 |
| **MapAnything** | TBD | **1B params · F32 ≈ 4 GB** | RTX 4090 / A100 (consumer) | **CC-BY-NC-4.0 ★ 非商用** |

⚠️ **License 警告**：MapAnything CC-BY-NC-4.0 商用要谈许可；与 VGGT 谱系（likely Apache）的差异是 deployment 决策。

&nbsp;

### 表 4 · 哪些问题谁都没解

| 仍未解 | VGGT v1 | VGGT-Ω | MapAnything | 何时解? |
|---|:---:|:---:|:---:|---|
| **Streaming** (frame-by-frame, 非 batch) | ❌ | ❌ | ❌ | 2027? `streaming VGT` 路线 |
| **Native IMU 耦合** | ❌ | ❌ | ❌ | 2027-12 前 |
| **Edge real-time (Orin <20ms)** | ❌ | ⚠️ | ❌ | 2028+ (quant + arch 改) |
| **抗振动 (aerial) 训练先验** | ❌ | ❌ | ❌ | 与 event camera fuse |

**关键含义**：feed-forward 3D 谱系在 2025-2026 取得了 metric + efficiency + dynamic 三个轴的进展，**但 aerial 实时控制环的硬约束（streaming + IMU + sub-10ms latency）一个也没解**。所以 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 结论：hybrid VGGT(任意变体) + 经典 VIO，**不是替换** — 仍成立。

&nbsp;

---

&nbsp;

## 🎯 我该选哪个？(5 秒决策树)

```
你的应用？
│
├─ 要 metric scale (manipulation grasp / drone control)
│   ├─ 慢速 / 离线 OK / consumer GPU 有 → 🌟 MapAnything
│   ├─ 实时 + Orin Nano edge → 📏 Metric3D (单目) / FoundationStereo
│   └─ Aerial 200 Hz 控制环 → 经典 VIO (VINS / OpenVINS)
│
├─ 不需要 metric (rendering / NVS / sim 数据)
│   ├─ 训练大规模 + 数据多 + 想跑动态场景 → 🚀 VGGT-Ω
│   ├─ 简单 baseline / 范式入门 → VGGT v1
│   └─ 桌面只看几何质量不在乎效率 → DUSt3R / MASt3R
│
├─ 商用 deployment
│   ├─ ✅ Apache 2 license 路线 → VGGT v1 / Ω (likely)
│   ├─ ❌ CC-BY-NC 不能商用 → MapAnything 要谈许可
│   └─ 内部用 / 研究 / 非商业 → 都 OK
│
└─ 训练自己的 feed-forward 3D
    ├─ 想省 memory → 抄 Ω 的 register attn
    ├─ 想解 metric → 抄 MapAnything 的 factored repr
    └─ 两个都要 → 等 2027 合并版本
```

&nbsp;

---

&nbsp;

## 📖 三篇深度解析

| 篇 | 文件 | 何时读 |
|---|---|---|
| **VGGT v1** (CVPR 2025 best paper) | [vggt_cvpr2025_dissection.md](./vggt_cvpr2025_dissection.md) | 想理解 feed-forward N-view 3D 的范式开创 — 必读起点 |
| **VGGT-Ω** (2026-05) | [vggt_omega_dissection.md](./vggt_omega_dissection.md) | 想看 efficiency × scale × dynamic 怎么解（v0.5 verified）|
| **MapAnything** (3DV 2026) | [mapanything_dissection.md](./mapanything_dissection.md) | 想看 metric scale 怎么解 + universal multi-task（v0.7 verified）|

&nbsp;

---

&nbsp;

## 🌐 与其他区的边界

| 这区写什么 | 别在这区 |
|---|---|
| feed-forward 单次前向 3D 模型的解构 + 谱系演进 | per-scene 拟合（NeRF / 3DGS）→ `../nerf-family/` `../3dgs-family/` |
| metric / dynamic / efficiency 等架构性能维度 | 跨 embodiment 应用对比（"VGGT vs VIO"）→ `crossing/slam-vio-migration/` |
| pose / depth / track 输出的工具拆解 | per-pixel depth 专精 → `../depth-foundation/` |
| | 物体 6D pose 专精 → `../pose-tracking/` |
| | classical SLAM (ORB-SLAM3) → `../classical-slam/` |

&nbsp;

---

&nbsp;

<details>
<summary>📊 Stats</summary>

&nbsp;

**3 dissections** · 全部 2025-2026 新 paper · 全部 Meta 系作者

**演进逻辑**：VGGT v1 开创范式 → MapAnything 解 metric → VGGT-Ω 解 efficiency
→ 下一代 (2027?) 三者合一 + streaming + IMU

**Pulsar pipeline**：本区是 spatial AI 最热的轴，平均每 3-6 个月有重大新论文。
Pulsar `vla-rss-collect.py` 监控 cs.CV arxiv，命中 feed-forward 3D 类
keyword 时自动加进候选；旗舰新 paper（如 MapAnything）由维护者人工开 dissection。

</details>

&nbsp;

---

[← Back to Foundations](../README.md) · [→ 3DGS family](../3dgs-family/README.md) · [→ NeRF family](../nerf-family/README.md) · [→ classical SLAM](../classical-slam/README.md)
