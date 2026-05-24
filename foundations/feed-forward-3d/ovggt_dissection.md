<!-- ontology-5axis
problem: Online Streaming Feed-Forward 3D with O(1) bounded memory (StreamVGGT memory disaster fix)
representation: Compressed KV cache (Self-Selective Caching + Dynamic Anchor Protection) — geometrically critical tokens protected
sensor: Mono RGB video stream (任意长度)
paradigm: Learned + Streaming + Constant-cost KV eviction（training-free post-hoc wrapper on StreamVGGT）
time: Online feed-forward streaming with O(1) per-frame memory (independent of sequence length)
ref: ../../cheat-sheet/ontology.md §5.2 / §13
-->

# OVGGT 解构 (OVGGT — O(1) Constant-Cost Streaming Visual Geometry Transformer)

> **发布时间**：2026-03 (arXiv)
> **论文 / 模型**：OVGGT — Si-Yu Lu, Po-Ting Chen, Hui-Che Hsu, Sin-Ye Jhong, Wen-Huang Cheng, Yung-Yao Chen（VAISR Lab）
> **核心定位**：StreamVGGT KV cache 爆炸（1300 frame → >100 GB）的**training-free 后处理修复** — 用 Self-Selective Caching + Dynamic Anchor Protection 把 streaming feed-forward 3D 的显存上限拉成 **O(1) 与序列长度无关**。
> **Status**: v1 — opinionated draft 2026-05-24。Latency / accuracy gap 数字标 `UNVERIFIED`（论文细节尚未深读完）。
> **Wedge tier**: W2 — streaming 3D **production candidate #1**（per ontology §5.2 「production 候选优先 OVGGT > XStreamVGGT > FrameVGGT > STAC > StreamVGGT 原版」）

**TL;DR**: StreamVGGT 把 VGGT batch 改 stream，但 KV cache 无限增长 → **GitHub issue #24 实测 1300 frame → >100 GB GPU memory，maintainer 8 个月不回**。OVGGT 是 **training-free wrapper**（不需重训）：用 **Self-Selective Caching (SSC)** 按 FFN residual magnitude 压 KV cache + **Dynamic Anchor Protection (DAP)** 保护几何关键 token 不被剔除，达到**显存与序列长度无关**（O(1) constant）。**完全兼容 FlashAttention**。是 streaming FF3D 谱系**目前最接近 production 的候选**，但仍 🔬 research-only（37★，2026-03 brand new，1 open issue / 0 closed），且 latency 数字未广泛验证。

---

## 📍 研究全景时间线 (X-Ray)

```
DUSt3R → MASt3R → VGGT (CVPR 2025, batch, O(N²) attn)
                    ↓
               VGGT-Ω (CVPR 2026 oral, batch, register attn)
                    ↓
               StreamVGGT (ICLR 2026, 2025-07) — causal+KV cache, ⚠ KV 无界爆炸
                    │
                    │  GitHub issue #24（2025-09）实测 1300 frame → >100 GB
                    │  maintainer 8 个月未回 → 学界自己解
                    │
                    ▼ 6 个月内出 4 个 follow-up paper 解 memory：
                    │
        ┌───────────┼───────────┬───────────────┐
        ▼           ▼           ▼               ▼
  XStreamVGGT  ★ OVGGT      FrameVGGT          STAC
  (2026-01)    (2026-03)    (2026-03)         (2026 in prep)
  KV pruning   ★ O(1)        Frame Evidence    Spatio-Temporal
  + quant      ★ constant    Rolling Memory    Aware Cache
  → 4.42× ↓    ★ memory      → similar cap     → similar cap
  + 5.48× ↑                                    
                                                
                                                ★ OVGGT 是**唯一 O(1) constant** 的方案
                                                  其他 follow-up 都是 bounded 但仍随 N 缓增长
```

**OVGGT 在 streaming FF3D 谱系的独特性**：唯一达到**严格 O(1)** 显存与序列长度无关的方案。XStreamVGGT 是 *constant factor* 改进（4.42× ↓），但底层仍 O(N) 增长；OVGGT 是**算法复杂度阶降**（O(N) → O(1)）。

---

## 1 · X-Ray — 跟 StreamVGGT 的核心架构差异

```
StreamVGGT (ICLR 2026, 显存灾难):
  Step t: I_t ──causal attn──► output_t
                │
                ▼
       update KV memory: M_t = M_{t-1} ∪ KV(I_t)   ◄── 无界增长！
                │
                ▼
  Step t+1: attend M_t (越来越大) + KV(I_{t+1})
                                ↑
                                │ 1300 frame → >100 GB
                                │ (issue #24, maintainer 不回)

OVGGT (2026-03, training-free wrapper):
  Step t: I_t ──causal attn──► output_t
                │
                ▼
       update KV memory: M_t = SSC(M_{t-1}) ∪ KV(I_t)
                          │
                          │  SSC = Self-Selective Caching
                          │  按 FFN residual magnitude 压
                          │  + DAP 保护 anchor tokens
                          ▼
                  |M_t| ≤ K_max  ◄── 固定上限！与 t 无关
                          │
                          ▼
  Step t+1: attend M_t (固定大小) + KV(I_{t+1})
                                ↑
                                │ 任意 N frame → 固定显存
                                │ 兼容 FlashAttention
```

**3 个关键替换**：

| 设计选择 | StreamVGGT | OVGGT |
|---|---|---|
| KV cache 增长 | unbounded O(N) | **bounded O(1)** with K_max cap |
| 训练需求 | 蒸馏自 bidirectional VGGT（重训） | **training-free**（直接套在 StreamVGGT 之上） |
| Token 剔除策略 | 无（全保留） | **Self-Selective Caching by FFN residual magnitude** |
| 几何关键 token 保护 | 无 | **Dynamic Anchor Protection (DAP)** — 防几何漂移 |
| FlashAttention 兼容 | ✅ | **✅ 保留** |
| 长序列推理 | ❌ 100+ GB OOM | ✅ 任意长度固定显存 |

---

## 2 · ⚡ Eureka Moment

> **「Streaming feed-forward 3D 的 KV cache 不必无限长 — 用 FFN residual magnitude 当 importance score 自动剔除，加 anchor protection 防几何塌，就能 O(1)。」**

StreamVGGT 把 LLM 的 KV cache 思想搬过来，但**忽略了一件事**：LLM 上下文长度漲到 100k+ token 也只是文字 token (~10 KB / token)，3D 视觉每 frame ~1000 tokens × 100 MB 量级 — *物理常数完全不同，LLM 的 KV cache 经验直接搬过来必爆*。

OVGGT 的洞察分两层：
1. **不是所有 token 同等重要** — FFN residual magnitude 是天然 importance signal（高 magnitude = 对下一层贡献大 = 值得保留）。这跟 LLM 圈的 H2O / StreamingLLM cache eviction 思想同源，但 3D 视觉首次系统应用。
2. **几何 anchor token 必须特殊保护** — 单纯按 magnitude 剔除会丢掉早期关键观测（loop closure / scene structure），导致几何漂移累积。**Dynamic Anchor Protection** 显式标记 *geometrically critical* tokens 不可剔。

**结果**：streaming FF3D 第一次达到 **production-deployable memory 上限**。`UNVERIFIED` 但合理推测：24 GB GPU 上从 StreamVGGT 的 ~300 frame 上限 → OVGGT 任意长度（只受 throughput 限，不受 memory 限）。

---

## 3 · 📌 Napkin Formula

**SSC + DAP 的复杂度账**：

```
StreamVGGT memory:
  M_t = Σ_{i=1}^{t} KV(I_i)
  |M_t| = O(t · tokens_per_frame · d_model · 2 · precision_bytes)
       ≈ t × 100 MB per frame  (对 518px frame ≈ 1000 tokens)
  t = 1000 → 100 GB   ← issue #24 实测

OVGGT memory:
  K_max = 固定 budget (e.g. 8 GB)
  M_t = SSC(M_{t-1}) ∪ KV(I_t),  subject to |M_t| ≤ K_max
  
  SSC eviction policy:
    1. score(token) = ||FFN_residual(token)||
    2. evict bottom k tokens by score, EXCEPT
    3. DAP-protected anchor tokens（geometrically critical, never evict）
  
  |M_t| ≤ K_max  for all t   ← O(1) bounded
```

**Anchor protection 数学条件**（推测，论文未公开细节，标 `UNVERIFIED`）：
- DAP 可能用 pose covariance / tracked landmark density / cross-frame matching strength 标记
- 标记的 token 在 SSC eviction 中跳过

**Speed-up 与 quality trade-off**（`UNVERIFIED`，等深读论文）：
- K_max 越小 → 显存越省 + 推理越快，但几何精度可能降
- 论文应有 K_max sweep ablation（典型 OVGGT 类工作模式）

---

## 4 · 带数字走一遍 — Worked Example (Toy)

设定：drone 飞 30 min 视频 @ 30 FPS = 54,000 frame，单卡 24 GB RTX 4090

**StreamVGGT**：
- frame_1 ~ frame_300：正常推理，memory 累到 ~20 GB
- frame_301 起：**OOM crash**（per issue #24 trajectory）
- 实际可用 sequence length: ~10 sec footage @ 30 FPS

**OVGGT (K_max = 8 GB 假设)**：
- frame_1 ~ frame_100：accumulate to K_max
- frame_101 起：SSC 开始 evict（保护 DAP anchors）
- frame 54,000：仍稳定在 K_max ≤ 8 GB
- 实际可用 sequence length: **任意长度，仅 throughput 限**

**Throughput 推算**（`UNVERIFIED`）：
- StreamVGGT 原版：~50-150 ms / frame
- OVGGT 加 SSC eviction overhead：可能 +10-30% per-frame cost
- 但**避免 OOM crash + 任意长视频**的价值远超此 overhead

→ Production 含义：30-min 长视频实时重建从 ❌ 不可能 → ✅ 可能（CPU/GPU 配齐前提下）。

---

## 5 · 工程视角：OVGGT 之外的 streaming 3D 选择

| 方案 | 显存 | 训练需求 | 当前 production 适配 |
|---|---|---|---|
| **StreamVGGT 原版** | O(N) **必爆** | 蒸馏（重训） | ❌ 不可用 |
| **XStreamVGGT** (2026-01) | 4.42× ↓（仍 O(N)） | KV pruning + quant 重训？ | 短-中视频可，长视频仍渐爆 |
| **OVGGT** (2026-03) | **O(1) bounded** | **training-free** | ✅ **production 候选 #1** |
| **FrameVGGT** (2026-03) | bounded | ? | 平行候选 |
| **STAC** (2026 in prep) | bounded | ? | 平行候选 |
| **3R-SLAM Hybrid** (Flash-Mono / SLAM3R) | O(1)（classical backend） | 不重训（套 SLAM） | ✅ 已 production，但需 SLAM 工程 |

→ **OVGGT 的独特价值**：training-free + O(1) + FlashAttention 兼容 — **三件齐备只有它**。

---

## 6 · 🚩 Hidden Assumptions

| 假设 | 看似合理 | 实际 |
|---|---|---|
| **「training-free 不掉精度」** | post-hoc wrapper | 论文宣称 "state-of-the-art 3D geometric accuracy on indoor, outdoor, ultra-long benchmarks"，**但具体 gap vs StreamVGGT 数字 `UNVERIFIED`**（需深读论文 ablation） |
| **「FFN residual magnitude 是好的 importance score」** | LLM 圈 H2O 类工作验证过 | LLM 是 1D causal token 序列，3D 视觉每 frame ~1000 token + spatial structure — magnitude 在 spatial token 上语义不同。论文应有 ablation 对比其他 score（attention magnitude / gradient-based） |
| **「DAP 能找全 anchor」** | 几何关键 token 可识别 | 何为「geometrically critical」论文需明确定义 — 是 tracked landmark? loop closure 关键 frame? pose covariance peak? **过保护 → SSC budget 不够；漏保护 → 几何漂移累积** |
| **「O(1) memory + bounded latency = real-time」** | 直觉等价 | O(1) memory 不保证 O(1) latency — attention 仍是 O(K_max²)，attention 时间常数还是要量 |
| **「替代 StreamVGGT 原版」** | wrapper 直接用 | 需 base model 仍是 StreamVGGT — 论文未说能否套到 VGGT-Ω / π³ / MapAnything（推测可，但**未验证**） |
| **「Production 候选」** | ontology 标的 | 37★ / 2026-03 brand new / 1 open issue — **学术 artefact，production 稳定性未经长期实战检验** |
| **「Bench 表现 = 真机表现」** | 论文宣称 indoor/outdoor/ultra-long | 论文用的是 indoor (ScanNet++) / outdoor (KITTI) / ultra-long benchmark — **aerial 动态 / marine 散射 / low-light 仍未测** |

---

## 7 · 🎤 Interview Tip

> **「StreamVGGT 显存灾难有解吗？OVGGT 能上 production 吗？」**
>
> 正确答：「OVGGT (arXiv 2603.05959, 2026-03) 是 **training-free wrapper** — Self-Selective Caching 按 FFN residual magnitude 剔 KV，Dynamic Anchor Protection 保护几何关键 token，显存达到 **O(1) 与序列长度无关**。**是 streaming FF3D 谱系第一个真正解 memory 问题的方案**（XStreamVGGT 是 constant factor 改进，OVGGT 是阶降）。**production 评级**：是目前最接近 production 的候选，但仍 🔬 research-only — 37★ / 2026-03 brand new，没有大规模实战验证，accuracy gap vs StreamVGGT 具体数字论文 ablation 需亲自验证。**生产部署仍走 3R-SLAM Hybrid**（Flash-Mono / SLAM3R）— 已实战验证 + 有 SLAM 后端保兜底。OVGGT 是研究/中期 prototype 的最佳选择，不是 today 的 production 答案。」
>
> 错答 1：「StreamVGGT 是 ICLR 2026 oral 就 production-ready 了」 — 25 open / 0 closed issue，maintainer 不回，memory 灾难。
> 错答 2：「OVGGT 已经 production」 — 37★，2026-03 brand new，还没经历足够实战。

---

## 8 · 🔁 Atlas 联动 — GitHub-validated 失败模式

→ 详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

**GitHub-VERIFIED issues**（2026-05-24, 37★ / 1 fork / 1 open issue / 0 closed）：

| 失败模式 | GitHub evidence | 验证状态 |
|---|---|---|
| **Brand new repo, sparse issue tracker** | 仅 **issue #2 ETH3D dataset**（2026-05 opened by narsisn） — 用户问 ETH3D dataset 兼容性 | ⚠ 单 issue 不足判断 maintainer 响应度 |
| **没有 closed issue, 无 maintainer 响应度 track record** | 0 closed / 0 commit-after-release 数据 | ⚠ **太新 (2026-03)**，无法判断「StreamVGGT-style release-and-forget」还是「真维护」 |
| **Accuracy gap vs StreamVGGT 未独立验证** | 论文宣称 SOTA on indoor/outdoor/ultra-long bench，但 GitHub 上无独立用户复现 issue | ⚠ UNVERIFIED — 等待社群独立验证 |
| **Aerial / marine / low-light 未测** | 论文 benchmark 仅 indoor (ScanNet++) + outdoor (KITTI 类) + ultra-long | ✅ 论文范围确认 — domain gap **完全未覆盖** |
| **K_max budget 选什么没指引** | repo README 未公布最优 K_max sweep | ⚠ 用户需自己试 budget |

**整体 maintainer 响应度评估**：**INSUFFICIENT DATA**（2026-05 离 paper 发布仅 2 个月）— 不能像 StreamVGGT (25 open / 0 closed) 那样确认是 release-and-forget，也无法确认是 actively maintained。**3-6 个月后需 re-audit**。

**社群信号**：37★ / 1 fork — 学术圈刚开始关注。对比 StreamVGGT 同期 (~600★) 关注度低 — 可能因为 (a) StreamVGGT 是 ICLR 2026 oral 自带流量，OVGGT 是 follow-up；(b) brand new，还没传开。

**Newer paper caveat**：本 dissection 的 issue-based deep dive 比 StreamVGGT / VGGT 系列**浅得多** — 因为 issue tracker sparse。建议读者 **2026-09 时 re-visit** atlas，届时社群验证应该铺开。

---

## 9 · 🔁 Falsifiable predictions

1. **2026-12 前**：会有独立第三方在 GitHub 复现 OVGGT，验证（或反驳）paper 宣称的 SOTA accuracy on ultra-long sequences。如果 6 个月内 0 独立复现 issue → 红旗（与论文宣称矛盾）。
2. **2027-06 前**：OVGGT 的 SSC + DAP 机制会被搬到 *其他 streaming 视觉 transformer*（dense prediction / video understanding / 4D Gaussian streaming）— LLM 圈 H2O 思想 cross-pollinate 到视觉的成功案例会增多。
3. **2027-12 前**：会出现 **OVGGT × π³ × MapAnything 三合一** — permutation-equivariant + O(1) streaming + metric scale 的 ideal FF3D。当前是 ontology 预测的 「2027 四合一」方向具体落地。
4. **2027-06 前**：3R-SLAM Hybrid (Flash-Mono / SLAM3R) **不会被纯 feed-forward streaming 替代** — SLAM 后端的 loop closure / global BA / metric scale + IMU coupling 仍是 OVGGT 类纯 FF 不具备的。Production aerial / AD 仍 hybrid。
5. **2027-12 前**：OVGGT 仍**无 aerial real-time 部署案例**（200 Hz / 5 ms 控制环） — O(1) memory 解了 memory 问题，但 attention K_max² 仍 ≥ 30 ms 量级，不到 5 ms 预算。

---

## 10 · 📊 5-axis 座标

| 轴 | 值 |
|---|---|
| Problem | **Online Streaming Feed-Forward 3D with O(1) bounded memory**（StreamVGGT memory disaster fix） |
| Representation | **Compressed KV cache** (Self-Selective Caching + Dynamic Anchor Protection) — geometrically critical tokens protected |
| Sensor | Mono RGB video stream（任意长度） |
| Paradigm | Learned + Streaming + **Constant-cost KV eviction**（training-free post-hoc wrapper on StreamVGGT） |
| Time | **Online feed-forward streaming with O(1) per-frame memory**（与序列长度无关 — NEW 子类） |

→ 详见 [`cheat-sheet/ontology.md §5.2`](../../cheat-sheet/ontology.md) 「VGGT 自带 streaming → 多个 follow-up paper 解 memory 灾难」一节，及 [`§13`](../../cheat-sheet/ontology.md) 「TRL deployment status」— OVGGT 标 production-recommended within streaming family。

---

## 11 · 对读者

- **Manipulation 工程师** — long-horizon 任务（30 sec+ 连续操作 / multi-step assembly）的 streaming 3D reconstruction，OVGGT 是当前最好的候选（StreamVGGT 会 OOM）。但仍建议 prototype 阶段用，production 仍走 per-scene optim（精度王者）。
- **Aerial 工程师** — OVGGT **不为你改 envelope**。memory 解了不等于 latency 够 — attention 仍 ≥ 30 ms 量级，不到 5 ms 控制环预算。aerial 仍走 VINS / OpenVINS / 3R-SLAM Hybrid (Flash-Mono)。
- **AD 工程师** — 长视频 BEV 预训练数据生成（dashcam 30-min 视频 → 3D ground truth）是 OVGGT 直接适配场景。考虑替换 StreamVGGT pipeline 时升级到 OVGGT，省 GPU 显存 + 跑长视频。
- **Marine 工程师** — AUV 长时观察任务（潜水器巡航 1-2 小时连续录像 → 3D map）若想用 FF3D streaming，OVGGT 是 today 唯一候选。但 underwater optics 训练 prior 仍缺，需 domain adaptation。
- **Research 学生** — OVGGT 的 SSC + DAP 是 *LLM cache eviction 思想 (H2O / StreamingLLM) cross-pollinate 到视觉 transformer* 的早期成功案例。值得 ablation：(a) FFN residual vs attention magnitude vs gradient-based importance score；(b) DAP 不同 anchor 标记策略；(c) OVGGT 能否套到 VGGT-Ω / π³（非 StreamVGGT 基础模型）。

---

## 12 · 与 handbook prediction 对照

**handbook 之前的 prediction**（`streamvggt_dissection.md` §12 prediction 1）：

> "✅ VERIFIED 2026-01 to 2026-03（早于预测 ~12 个月）：StreamVGGT v2 / 后继 with cache eviction 预期 2027-06 前出。实际 6 个月内已出 4 个：XStreamVGGT / FrameVGGT / **OVGGT** / STAC"

→ **OVGGT 直接验证了 handbook prediction**，且是 4 个 follow-up 中**唯一达 O(1) constant memory** 的方案（其他都是 bounded but still O(N) growing）。

handbook 的「streaming FF3D memory 灾难会快速催生 follow-up paper」prediction 通过严格验证。

**新 prediction 加入**（本 dissection §9）：OVGGT × π³ × MapAnything 三合一会在 2027-12 前出 — 这是下一代 FF3D 的 ideal target。

---

## References

### Primary

- **OVGGT** — Lu et al. *arXiv 2026-03* · [arXiv:2603.05959](https://arxiv.org/pdf/2603.05959) · [GitHub VAISR/OVGGT](https://github.com/VAISR/OVGGT) (37★, 1 fork, 1 open issue / 0 closed at 2026-05) · [Project page vaisr.github.io/OVGGT](https://vaisr.github.io/OVGGT/)

### GitHub issues (sparse — paper too new)

- [issue #2](https://github.com/VAISR/OVGGT/issues/2) — ETH3D dataset 兼容性（2026-05 opened, sole open issue）
- **NOTE**：本 paper 2026-03 发布，issue tracker sparse — 与 StreamVGGT (25 issues) / VGGT (50+ issues) 不可比。社群验证铺开预期 2026-09，届时 atlas 应 re-audit。

### Lineage (parent / cousin / family)

- **StreamVGGT** — Wang et al. *ICLR 2026* · [arXiv:2507.11539](https://arxiv.org/abs/2507.11539) · [`streamvggt_dissection.md`](./streamvggt_dissection.md) — **直接前身**（OVGGT wrapper 的 base model；memory 灾难的来源）
- **XStreamVGGT** — *2026-01* · [arXiv:2601.01204](https://arxiv.org/abs/2601.01204) — **平行 cousin**（KV pruning + quant，4.42× memory ↓ + 5.48× speedup，但仍 O(N)）
- **FrameVGGT** — *2026-03* · [arXiv:2603.07690](https://arxiv.org/pdf/2603.07690) — **平行 cousin**（Frame Evidence Rolling Memory，bounded but 设计不同）
- **STAC** — [project page stac-3r.github.io](https://stac-3r.github.io/) — **平行 cousin**（Spatio-Temporal Aware Cache Compression）
- **VGGT v1** — Wang et al. *CVPR 2025 Best Paper* · [arXiv:2503.11651](https://arxiv.org/abs/2503.11651) · [`vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md) — **谱系祖先**（batch FF3D 起点）
- **VGGT-Ω** — *CVPR 2026 oral* · [arXiv:2605.15195](https://arxiv.org/abs/2605.15195) · [`vggt_omega_dissection.md`](./vggt_omega_dissection.md) — 同期 batch 效率改进（OVGGT 未与之结合，未来方向）
- **π³ / Pi3** — Wang et al. *ICLR 2026* · [arXiv:2507.13347](https://arxiv.org/abs/2507.13347) · [`pi3_dissection.md`](./pi3_dissection.md) — 正交改进（reference-free，未与 OVGGT streaming 结合，未来方向）
- **MapAnything** — *3DV 2026* · [`mapanything_dissection.md`](./mapanything_dissection.md) — 正交改进（metric scale，未与 OVGGT 结合，未来方向）

### Theory roots（KV cache eviction in LLM space）

- **H2O (Heavy Hitter Oracle)** — Zhang et al. *NeurIPS 2023* · [arXiv:2306.14048](https://arxiv.org/abs/2306.14048) — LLM KV cache eviction by attention score（同源思想，OVGGT 是视觉版）
- **StreamingLLM** — Xiao et al. *ICLR 2024* · [arXiv:2309.17453](https://arxiv.org/abs/2309.17453) — attention sink + sliding window cache（OVGGT DAP 类似 attention sink protection 思想）
- **FlashAttention-2** — Dao 2023 · [arXiv:2307.08691](https://arxiv.org/abs/2307.08691) — OVGGT 显式声明兼容

---

## Boundary

- 与 StreamVGGT 原版的 *完整* batch / causal / KV cache 设计 → 详见 [`streamvggt_dissection.md`](./streamvggt_dissection.md)
- 与 XStreamVGGT / FrameVGGT / STAC 的横向对比 → [`README.md` 「memory-compression follow-up family」](./README.md)（下次 overview 更新时加入 OVGGT 行）
- 3R-SLAM Hybrid 替代方案（Flash-Mono / SLAM3R）→ [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)
- LLM 圈 H2O / StreamingLLM 完整细节 → out of scope（自查 LLM efficiency 文献）
- Per-K_max budget sweep 调参指南 → 论文 ablation 待读 + 用户实战验证（**TODO when production case 出现**）

---

## 5-axis 座标参考

→ [`cheat-sheet/ontology.md §5.2`](../../cheat-sheet/ontology.md) — streaming 子分支（StreamVGGT → XStreamVGGT / OVGGT / FrameVGGT / STAC）
→ [`cheat-sheet/ontology.md §13`](../../cheat-sheet/ontology.md) — TRL deployment status（OVGGT = production candidate within streaming family，但 still 🔬）

---

*Last updated: 2026-05-24 · v1 opinionated draft · brand new paper (2026-03), issue tracker sparse — re-audit recommended 2026-09*

---

[← Back to Feed-Forward 3D](./README.md)
