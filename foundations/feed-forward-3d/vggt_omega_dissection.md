<!-- ontology-5axis
problem: FeedForward3D (VGGT variant)
representation: Dense pointmap + depth + pose
sensor: Multi-view RGB
paradigm: Learned-EndToEnd
time: FeedForward-OneShot
ref: ../../cheat-sheet/ontology.md §7
-->

# VGGT-Ω 解构 (VGGT-Omega Dissection)

> **发布时间**: 2026-05 · arXiv [2605.15195](https://arxiv.org/abs/2605.15195)
> **论文**: *VGGT-Ω: Scaling Feed-Forward 3D Reconstruction with Efficient Architecture and Self-Supervised Learning*
> **作者**: Wang, Chen, Zhang, Karaev, Schönberger, Labatut, Bojanowski, Novotny, Vedaldi, Rupprecht（Meta + Oxford 系，与 VGGT v1 同核心团队）
> **核心定位**: VGGT v1（CVPR 2025）的高效化 + 自监督扩展 —— 把 N-view 前向 3D 推到"单 dense head + register attention + 15× 训练数据"，同时**首次原生处理动态场景**。

**Status:** v0.5 — 解构基于论文摘要 + arXiv 元数据 + 第三方分析（[Alan Hou blog](https://alanhou.org/blog/arxiv-vggt-/)）；细节如完整 ScanNet++/ETH3D 数字、code release、参数量待维护者从论文正文补完后升 v1。
**TL;DR:** VGGT-Ω 做三件事：① 把 4 head 合成 1 个 dense multi-task head + 去掉高分辨 conv；② 用 **registers** 把 N-frame global attention（100k × 100k）压成 sparse register attention（100k × 16）—— GPU 内存降到 v1 的 30%；③ 用自监督打开 unlabeled video 大池，supervised 数据规模 15×。**结果**：Sintel camera estimation 比之前 SOTA 提升 77%，并且原生支持动态场景（v1 静态假设破除）。

**X-Ray.** VGGT v1 已经证明"N-view 单次前向能跑 3D"是范式转移，但留下三个工程坑：(a) 4 head 各自管 pose / depth / point / track ⇒ 训练 memory 爆炸；(b) global cross-frame attention 是 quadratic，N>30 就 OOM；(c) 训练只在静态 + 标注数据上做。**VGGT-Ω 一次性把这三个坑用 architecture × data 双重压力解掉**：multi-task head 共享 backbone、registers 做信息瓶颈、自监督打开 video pool。对 spatial AI 研究者意义：feed-forward 3D 不只是更好的几何，**它把"训练资源"作为可扩展轴打开了** —— 这是从单篇 paper 到 foundation 物种的关键一步。但 aerial 真实部署仍受 §6 限制 —— operational envelope 不在 Ω 改的层。

## 📍 研究全景时间线

```
   2020      2023        2024              2025                  2026-05            2027?
   NeRF ────► 3DGS ────► DUSt3R ───────► VGGT v1 ───────────► VGGT-Ω ─────────► metric+streaming
   per-scene  per-scene   feed-forward     CVPR best paper      YOU ARE HERE       on edge?
              (faster)    (2-view)         (N-view batch, 4 head) (1 head + registers
                                            static only)          + self-supervised
                                                                  + dynamic!) ★
   └─ offline fitting ──────────► forward inference ──────────► efficiency + scale ──────►
                                  paradigm shift                (Ω 的押注)
```

★ = 主要新点：efficiency-by-architecture + data-by-self-supervision + dynamic scenes。**仍 un-metric、仍 batch-mode**（没解决 streaming + metric scale —— 这两条留给下一代）。

---

## 1 · 架构（核心新点）

### 1.1 三大改动 vs VGGT v1

| 维度 | VGGT v1 | VGGT-Ω |
|---|---|---|
| **Prediction heads** | 4 个独立 head（pose / depth / pointmap / tracks）| **1 个 dense head + multi-task 监督** |
| **High-res conv layers** | 有 | **删除** — 减少 FLOPs + memory |
| **Cross-frame attention** | Global（N×N tokens 每对都做）| **Register attention** — frames 只透过 ~16 registers 交换信息 |
| **Training data** | 标注数据 | **+ self-supervised on unlabeled video，规模 15×** |
| **Scene assumption** | 静态 | **静态 + 动态原生支持** |
| **GPU memory (training)** | 100% baseline | **30%** of v1 |

### 1.2 ⚡ Eureka Moment

> **Register attention = "把 N-view global attention 当作总线，N×N 信息交换简化为 N×16 + 16×16"** —— 16 个 learnable tokens 当 scene summary slot，inter-frame 信息流被强制走它们。Memory 从 quadratic-in-N 降到 linear-in-N + constant。

这是从 ViT 的 [register tokens trick](https://arxiv.org/abs/2309.16588)（Darcet 2023）借鉴到多视图 3D —— 但放大到 scene 级别。

### 1.3 信息流（架构图）

```
            VGGT v1                                   VGGT-Ω
   ─────────────────────────────              ─────────────────────────────
                                                                            
   Frame_1 ┐                                  Frame_1 ┐                    
   Frame_2 ├─► Encoder ─┐                     Frame_2 ├─► Encoder ─┐       
   Frame_3 ┤            │                     Frame_3 ┤            │       
   ...     ┤            ▼                     ...     ┤            ▼       
   Frame_N ┘    Global cross-frame attn         Frame_N ┘    Register attn 
                (N×N token pairs)                          (N tokens ↔     
                  ↓                                          16 registers   
                                                              ↓             
            ┌──────┬──────┬──────┐                    ┌─────────────┐     
            │ Pose │Depth │ Pt   │ Tracks            │ Single      │     
            │ head │ head │ head │ head              │ Dense Head  │     
            └──────┴──────┴──────┘                    │ + multi-task│     
            ★ 4 独立 head                              │   supervis. │     
                                                       └─────────────┘     
                                                       ★ 1 head + 监督共享 backbone
                                                                            
            训练 memory ★ 100%                          训练 memory ★ 30%   
            Cross-frame: O(N²·tokens²)                Cross-frame: O(N·tokens·16)
```

---

## 2 · 数学层

### 📌 Napkin Formula

```
   Register Attention:
      
      H_t  ←  attention( Frame_t  ,  R )           ← frame ⇆ register (cheap)
      R    ←  attention( R       ,  R  )           ← register ⇆ register (constant cost)
      H_t  ←  attention( Frame_t  ,  R )           ← frame reads back from updated registers
      
      where  R ∈ ℝ^(16 × d)   is a small set of learnable tokens.
   
   Cost: O(N · M_per_frame · 16)  +  O(16²)        ← linear in N, constant in registers
         vs VGGT v1 global:  O(N² · M²)             ← quadratic in N
```

**直觉**：global attention 把每对 (frame_i, frame_j) 都建桥；register attention 让信息**走总线** —— 每帧只跟 ~16 个 summary slot 通信，slot 自己再互相通信压缩 scene 共识，然后帧从更新后的 slot 拿信息回来。**信息瓶颈 (16 个 register) = 容量 floor**，但实证证明在 3D scene 这种 sparse cross-frame correspondence 任务上够用。

### 2.1 Multi-task dense head 的损失组成

单 head 取代 4 独立 head 后，损失变成 multi-task weighted：

```
   L_total = λ_pose · L_pose + λ_depth · L_depth + λ_pointmap · L_pointmap + λ_track · L_track
                                                                    (+ L_self_supervised)
```

具体 `λ` 权重 + 监督形式 `UNVERIFIED` 待论文正文补。

### 2.2 自监督损失（new）

打开 unlabeled video 池靠新增自监督信号 `UNVERIFIED` 具体形式 — 可能候选：
- **多帧 photometric consistency**：render 一帧从相邻帧的 pose + depth 推断
- **Temporal pose smoothness**：相邻帧 pose delta 应平滑
- **Tracking consistency**：同物体被 2D tracker 追踪 vs forward pass 的 prediction

`TODO` 论文正文确认 self-supervised 损失的具体公式。

---

## 3 · 数据层

### 3.1 训练数据 scale up

| 数据类型 | VGGT v1 | VGGT-Ω | 倍数 |
|---|---|---|---|
| 标注 3D + pose（监督）| baseline | **15× baseline** | 15× |
| Unlabeled video（自监督）| 0 | "vast amounts" `UNVERIFIED` | — |

具体哪些 dataset `UNVERIFIED`，候选大概率包括：
- 监督：MegaSynth 类合成、Hypersim、ScanNet++、ARKitScenes、Co3D、MegaDepth（v1 的扩展）
- 自监督：YouTube 类未标注视频、Internet video collections

`TODO` 论文 §4 (datasets) 应该有详细 list。

### 3.2 数据 × 架构 = 训练能跑得起

**关键事实**：架构改省了 70% memory → 才能在同样 GPU 预算上**用 15× 数据训**。这是论文的核心 product/process loop：

```
   Memory budget (per GPU) ─────────────► 训练 batch × seq_length
                ↑                                    ↓
    Architecture efficiency (registers, 1 head)     Data scale (15× supervised + unlabeled)
                ↑                                    ↓
                └────── 形成正反馈 ──────────────────┘
```

VGGT v1 是 model first；Ω 是 model × data co-design。

---

## 4 · 代码层

### 4.1 上游 (v1 已开源)

VGGT v1 的官方实现：https://github.com/facebookresearch/vggt （CVPR 2025 best paper code）

预测 Ω 实现 inherits v1 的 PyTorch 框架 `UNVERIFIED`。

### 4.2 Ω 自己代码

`TODO` Ω 是否开源、何时开源、checkpoint 大小 — 论文披露后补。

历史规律：Meta + Oxford 这条线（DUSt3R / MASt3R / VGGT v1）都在 NeurIPS / CVPR 后 1-3 月开源，预期 Ω 走同样节奏。

### 4.3 部署关键（基于 v1 + Ω 设计推断）

| 关键问题 | v1 状态 | Ω 预期 `UNVERIFIED` |
|---|---|---|
| 推理 GPU 内存 | distilled ~3 GB | 因为 register attn 推理也省，预期 1-2 GB? |
| 推理延迟（Orin Nano）| 100-200 ms | 因 conv 砍 + register attn，预期 50-100 ms? |
| Streaming 模式 | ❌ batch-only | ❌ **仍 batch-only**（论文重点是 efficiency + scale，没改 streaming）|
| Metric scale | ❌ un-metric | ❌ **仍 un-metric** |
| N 上限 | ~30 | 因 register attn linear-in-N，**N 应能扩**（但论文未明说 N=100 / 500） |

⚠️ **重要**：Ω 改的是 *训练效率 + 数据规模 + 动态场景*；**没改 streaming 也没解 metric scale**。这两条仍是下一代要做的（见 §7 falsifiable prediction）。

---

## 5 · 评测层（benchmark 实证）

### 5.1 已知数字

| Benchmark | Metric | VGGT v1 / 之前 SOTA | VGGT-Ω | Δ |
|---|---|---|---|---|
| **Sintel** | camera estimation | baseline | **77% 提升** | -77% error |
| ScanNet++ | TBD | `UNVERIFIED` | `UNVERIFIED` | TBD |
| ETH3D | TBD | `UNVERIFIED` | `UNVERIFIED` | TBD |
| DTU | TBD | `UNVERIFIED` | `UNVERIFIED` | TBD |
| MegaDepth | TBD | `UNVERIFIED` | `UNVERIFIED` | TBD |

`TODO` 维护者从论文 §5 / table 补齐完整 benchmark 表。

### 5.2 Sintel 提升 77% 的解读

Sintel 是**合成动态视频** benchmark — 77% 提升主要来自两件事：
1. **首次原生支持动态场景** — v1 假设静态，在 Sintel 上结构性不对
2. **训练数据规模 + 自监督 unlabeled video** —— 增加了 motion / 动态先验

⚠️ **不是说在 EuRoC / 真机 aerial 上也提升 77%** —— Sintel 是合成数据 + 动态场景；真实户外 / 抗振动 / 实时这些 envelope 论文没碰。

---

## 6 · Issues & Limitations

### 6.1 论文自述 limitations

- **自监督 detail 比监督差**：自监督训出来的结果在细节几何上不如纯监督
- **Unlabeled data 数量需求未明**：多少 unlabeled video 才能匹配监督性能，论文没给量化曲线
- **Sintel 合成 → 真实差距未充分验证**：动态场景提升 77% 是合成 benchmark；真实世界动态视频结果"need more demonstration"

### 6.2 Hidden Assumptions（隐含假设）

- **静态 + 动态 prior 一锅训** —— 训练数据中静态与动态的比例 / 平衡未披露；分布外 OOD 动态（接触爆炸性运动、流体）可能崩
- **Register 数量 16 是 magic number** —— 16 个 register 容量够还是不够取决于 scene 复杂度；非常 cluttered 场景可能信息溢出
- **Self-supervised 不保证 metric** —— 自监督只对几何一致性 / 运动平滑性敏感，**完全不能产生 metric scale**
- **Single dense head 共享 backbone** —— 改一 task 训练损失可能干扰其他 task 性能（multi-task interference 经典问题）
- **GPU memory 30% 是训练 only** —— 推理时 register 仍需保留，预测 inference memory 不会同比例下降

### 6.2.x GitHub-validated 失败模式（atlas 联动，2026-05-24 deep dive）

VGGT-Ω repo 已開源（[facebookresearch/vggt-omega](https://github.com/facebookresearch/vggt-omega)），但跟 StreamVGGT 同樣模式：**Meta FAIR 開源不維護**。

| 失敗 / 問題 | GitHub evidence | 嚴重度 |
|---|---|---|
| **Multi-view fusion 失敗** | [issue #17](https://github.com/facebookresearch/vggt-omega/issues/17): "generated point cloud has poor geometric quality... I do not see an obvious fusion of point clouds from different views" (maintainer 無回應) | 🔴 同 v1 / StreamVGGT 遺傳問題 |
| **Sparse-view face 重建失敗** | [issue #15](https://github.com/facebookresearch/vggt-omega/issues/15) — 與 StreamVGGT #29 同主題 | 🔴 multi-view alignment 仍未解 |
| **Install 失敗** | [issue #18](https://github.com/facebookresearch/vggt-omega/issues/18): `pip install -e .` → "ERROR: File 'setup.py' not found" — 缺 setup.py | 🟠 入門門檻高 |
| **HF model access 被拒** | [issue #26](https://github.com/facebookresearch/vggt-omega/issues/26) — Edinburgh PhD student academic 用途被拒，無公開 criteria | 🟠 access 不透明 |
| **Training code 未發布** | [issue #27](https://github.com/facebookresearch/vggt-omega/issues/27) — maintainer 無回應 | 🟠 reproducibility 受限 |
| **COLMAP export 問題** | [issue #28](https://github.com/facebookresearch/vggt-omega/issues/28) | 🟡 整合下游 SfM workflow 卡 |
| **Original VGGT export script 不相容** | [issue #21](https://github.com/facebookresearch/vggt-omega/issues/21) | 🟡 migration 路徑斷 |
| **10B model variant 不可得** | [issue #29](https://github.com/facebookresearch/vggt-omega/issues/29) | 🟡 paper 提到但未發布 |

**Maintainer 響應度**：15 open issues / **0 closed** (2026-05-24)。Meta FAIR 開源節奏一貫 — 程式碼 release 但 issue 不答。

**對讀者實務含義**：
- 想 **學 architecture** → 讀 paper / 看 code 可以
- 想 **production deploy** → 不要（HF access 不確定 + install broken + training code 沒 release）
- 想 **academic research baseline** → 用，但記得 inheritance VGGT v1 的 multi-view fusion 問題尚未解

### 6.3 aerial / 实时 angle 的影响（不变）

VGGT-Ω 改的层与 aerial real-time VIO 替代题无关：

- **Streaming**：没做 → aerial 实时控制环仍不能上
- **Metric scale**：没做 → 控制器仍需要外部 scale anchor（IMU / stereo / RTK）
- **Latency**：可能略降 但 100 ms 量级仍不够 200 Hz × 5 ms 预算
- **Vibration**：训练 prior 没有桨叶振动；ViT 类 encoder 仍易受 motion blur 影响

所以 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 的结论 **完全不变**：hybrid VGGT(-Ω) + 经典 VIO，不是替换。

---

## 7 · 比较 & 面试 Tip

| 模型 | 架构 | Memory | Dynamic? | Streaming? | Metric? | Status |
|---|---|---|---|---|---|---|
| VGGT v1 | 4 heads + global attn | 100% | ❌ 静态 | ❌ batch | ❌ | shipped |
| **VGGT-Ω** | 1 dense head + register attn | **30%** | ✅ 静态+动态 | ❌ batch | ❌ | arXiv 2605 |
| DUSt3R / MASt3R | pairwise feed-forward | low | ❌ | ❌ | ❌ | shipped |
| Depth Anything v2 | per-frame depth | low | yes (frame-by-frame) | ✅ per-frame | ❌ relative | shipped |
| π³ streaming `UNVERIFIED` | streaming variant of VGGT lineage | TBD | TBD | ✅ | ? | research |
| Classical VIO | 经典 | embedded | yes | ✅ tight | ✅ | shipped |

> **🎤 Interview Tip.** "VGGT-Ω 出来了，我们要不要换 VGGT v1？" 正确答："**Ω 在 efficiency × data × dynamic 都赢，训练成本省 70%，Sintel 提 77%** — 如果你已经在用 v1 做 manipulation / 室内 offline 重建，迁就值得。**但你的 deployment envelope 一行没变**：仍是 batch / un-metric / >100ms latency。所以 aerial 实时 / 控制环里头要不要换的答案是 *No*，跟之前一样。" 错答："Ω 更强，所以替换" — Ω 改的是训练效率，不是推理 envelope。

### 7.1 Falsifiable predictions

1. ✅ **VERIFIED 2026-07 (預測時間 2027-06，早 ~1 年)**：StreamVGGT（ICLR 2026）+ INCVGGT（ICLR 2026）兩條 streaming variant 已出。StreamVGGT 用 *temporal causal attention + cached memory token* 達 incremental on-the-fly reconstruction —— 跟我們預測「register 當 state cache」方向一致，**memory token = register cache 的 streaming 化**。詳見 [`streamvggt_dissection.md`](./streamvggt_dissection.md)。
2. **2027-12 前**：第一篇 metric-aware feed-forward 3D 论文会借鉴 Ω 的 register architecture + 额外 scale anchor head（stereo 或 IMU）。
3. **2027-12 前不会发生**：VGGT 谱系（含 Ω 后代 + StreamVGGT）成為 aerial 200 Hz 主前端 — operational envelope 限制不在 N 多少 / streaming 與否能解（streaming 解 latency 一半，但 metric scale + vibration robustness 還沒解）。

---

## 8 · For the reader

- **Manipulation 工程师** —— Ω 是 v1 的 strict upgrade（除了 metric scale 那条仍未解）。如果 Splat-Sim / 桌面环境用得多，直接迁。
- **Aerial 工程师** —— Ω 的进步*不为你* 改 envelope。继续用 VINS / OpenVINS 做控制环；Ω 当 out-of-loop relocalizer / map anchor 依然成立。
- **AD 工程师** —— Ω 的 dynamic scene 支持有意思（Sintel 提 77% 不是小事）；可能比 v1 更适合 offline AD scene reconstruction（NVIDIA Cosmos 类 sim2real）。
- **Marine 工程师** —— 与 v1 一样，单目 RGB 在水下退化前提下，Ω 也救不了你。继续 sonar + DVL + IMU。
- **Research 学生** —— 注意 §7.1 三条预测；register attention + multi-task dense head 是接下来几年的 architectural baseline。

---

## References

- **VGGT-Ω** — Wang et al. 2026-05 · [arXiv:2605.15195](https://arxiv.org/abs/2605.15195)
- **VGGT v1** — Wang et al. *CVPR 2025 best paper* · [arXiv:2503.11651](https://arxiv.org/abs/2503.11651) · [code](https://github.com/facebookresearch/vggt)
- **Register tokens for ViT** — Darcet et al. *ICLR 2024* · [arXiv:2309.16588](https://arxiv.org/abs/2309.16588)（register attention 思想源头）
- DUSt3R — *CVPR 2024* · [arXiv:2312.14132](https://arxiv.org/abs/2312.14132)
- MASt3R — *ECCV 2024* · [arXiv:2406.09756](https://arxiv.org/abs/2406.09756)
- Streaming Visual Geometry Transformer（相关 streaming 路线）— [arXiv:2507.11539](https://arxiv.org/abs/2507.11539)
- 第三方 lay analysis — [Alan Hou blog](https://alanhou.org/blog/arxiv-vggt-/)

---

## Boundary

- 与 v1 的完整解构（4 head 架构、训练 stack 细节、worked example）→ [`./vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md)
- 跨 embodiment "VGGT vs VIO" → [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)（Ω 不改这个 wedge 的结论）
- 与 3DGS 关系（谁取代谁）→ [`crossing/representation-migration/3dgs_as_simulator_comparison.md`](../../crossing/representation-migration/3dgs_as_simulator_comparison.md)
- 与 VLA 接口 → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)

---

## ✍️ 维护者注（v0.5 → v1 升级清单）

本 v0.5 基于摘要 + 第三方分析。下次有时间打开论文正文时补：

1. ⏳ Authors 的具体 affiliation（Meta vs Oxford vs 别）
2. ⏳ 16 个 register 是否就是确数 / register dimension d / encoder layer 数
3. ⏳ Multi-task supervision 的 λ 权重
4. ⏳ Self-supervised 损失的具体形式（photometric / temporal / tracking）
5. ⏳ 完整训练数据 dataset list（监督 15× 具体是哪些 + 自监督来源）
6. ⏳ ScanNet++ / ETH3D / DTU / MegaDepth 完整 benchmark 数字（vs v1 + DUSt3R + MASt3R）
7. ⏳ 推理延迟 / GPU 类型 / FLOPs（不只训练 memory）
8. ⏳ Code / checkpoint release 状态
9. ⏳ Status v0.5 → v1，删本节

---

[← Back to Feed-Forward 3D](./overview.md)

Sources:
- [VGGT-Ω arXiv 2605.15195](https://arxiv.org/abs/2605.15195)
- [Alan Hou — VGGT-Ω 中文导读](https://alanhou.org/blog/arxiv-vggt-/)
- [VGGT v1 GitHub](https://github.com/facebookresearch/vggt)
- [Streaming Visual Geometry Transformer (relative)](https://arxiv.org/html/2507.11539)
