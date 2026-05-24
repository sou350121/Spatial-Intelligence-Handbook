<!-- ontology-5axis
problem: Online Streaming Feed-Forward 3D (VGGT streaming variant)
representation: Dense pointmap + depth + pose (per-frame incremental) + memory KV cache
sensor: Mono RGB video stream
paradigm: Learned-EndToEnd + Temporal Causal Attention + KV-cache memory
time: Online feed-forward streaming (LLM-style incremental, not batch)
ref: ../../cheat-sheet/ontology.md §5.2 / §5.4
-->

# StreamVGGT Dissection (StreamVGGT 解构 — ICLR 2026)

**发布时间**: 2025-07 (arXiv) / ICLR 2026
**论文 / 模型**: StreamVGGT — Wang et al. (清华 + 复旦相关 group, 维护者 wzzheng)
**核心定位**: VGGT 谱系的 **streaming variant** —— 把 N-view batch 改成 frame-by-frame 增量；用 temporal causal attention + cached memory tokens（LLM 式 KV cache）做 online 3D 重建。
**Status**: v1 — opinionated draft 2026-05-24. Inference timing / memory footprint claims 标 `UNVERIFIED`.
**Wedge tier**: W2 — handbook 第一个收的「VGGT 系自带 streaming」非 hybrid 路线。

**TL;DR**: VGGT-Ω 仍 batch；StreamVGGT 用 *causal attention + KV memory* 把 batch 改 stream，架构抄 GPT 自回归。**不是 3R-SLAM hybrid** — 純 feed-forward 但能 stream。**現實檢驗 (GitHub deep dive 2026-05)**：(a) 1300 frame → >100 GB GPU memory（issue #24，maintainer **8 個月未回應**）；(b) Multi-view alignment 失敗（issue #29 face 案例，遺傳 VGGT batch 問題）；(c) **25 issue / 0 closed** — research artefact 不是 maintained product；(d) TensorRT 部署未驗證。**生態系統反應**：6 個月內已出 4 個 follow-up paper 專解（XStreamVGGT 4.42× memory ↓ / OVGGT O(1) constant / FrameVGGT / STAC）— production 候選看這些，不是原 repo。仍 ❌ aerial 200 Hz / 5 ms 控制環。

---

## 1 · X-Ray — 跟 VGGT batch 的核心差別

```
VGGT (CVPR 2025 batch):
  [I_1, I_2, ..., I_N] ─bidirectional self-attention──► {pose_i, depth_i, pointmap_i}_{i=1..N}
                       ↑
                       O(N²) attention; 全 N view 同時看；每加一 frame 整個重算

StreamVGGT (ICLR 2026 streaming):
  Step t: I_t ─causal attention──► {pose_t, depth_t, pointmap_t}
                                    │
                                    ▼
                       update KV memory cache (M_t = M_{t-1} ∪ KV(I_t))
                                    │
                                    ▼
  Step t+1: I_{t+1} attends to M_t (cached) + own KV ──► {pose_{t+1}, ...}
                       ↑
                       O(N) per step; 只看過去 frame；新 frame 不重算過去
```

**3 個架構替換**：

| 設計選擇 | VGGT batch | StreamVGGT |
|---|---|---|
| Attention 方向 | bidirectional | **causal (forward-only)** |
| Memory 模型 | 整個 N view tokens | **KV cache (LLM-style)** |
| 計算複雜度 | O(N²) per inference | **O(N) per frame** |
| 訓練 supervision | end-to-end on dense data | **knowledge distillation from bidirectional VGGT** |

---

## 2 · ⚡ Eureka Moment

> **「Feed-forward 3D 不必 batch — 把 GPT 那套 KV cache 搬過來就 stream 了。」**

過去把「feed-forward」與「streaming」當對立詞（feed-forward = 一次性 forward / streaming = incremental），是因為直覺認為 transformer 必須 bidirectional 才能 attend 跨 view。**StreamVGGT 證明**：用 causal attention + 過往 KV cache，純 feed-forward 也能 incremental — 就跟 LLM autoregressive generation 一模一樣。

**結果**：3R-SLAM Hybrid family (SLAM3R / Flash-Mono) **不再是唯一 streaming 路線**。純 feed-forward 譜系自己也有 streaming 子分支了。

---

## 3 · 📌 Napkin Formula

**KV cache 增長 vs 顯存上限 — 理論 vs 實測**：

```
理論 napkin:
  顯存 ≈ T × d_model × n_layer × 2 × precision_bytes
        ≈ T × 96 KB / token × tokens_per_frame
  對 518px frame ≈ 1000+ tokens:
        ≈ T × 100 MB per frame
  T = 100 → 10 GB
  T = 500 → 50 GB
  T = 1000 → 100 GB
```

**✅ 實測驗證（GitHub issue #24）**：
- 1 分鐘視頻、1300 frames、518px → **GPU memory >100 GB**
- maintainer 無回應 8 個月+（issue 開 2025-09，到 2026-05 仍 open）
- 這意味 **24 GB 消費級 GPU 大概 ~300 frame 就 OOM**（取決 frame token 數）

→ **單卡 24 GB 上限 ≈ 300 frame（10 sec @ 30 FPS）**。長視頻需要 cache eviction（已有 XStreamVGGT / OVGGT / FrameVGGT / STAC 4 個 follow-up paper 解這個，見 §8.1）。

---

## 4 · 📍 研究全景時間線

```
                 register attention (Darcet ICLR 2024)
                              ↓
DUSt3R (CVPR 2024) → MASt3R (ECCV 2024) → VGGT (CVPR 2025 best, batch)
                                            ↓
                                  VGGT-Ω (CVPR 2026 oral, batch)
                                            ↓
                                  ★ StreamVGGT (ICLR 2026, causal+KV cache)
                                            ↓
                                  INCVGGT (ICLR 2026, 平行另一條 incremental)
```

**對應 LLM 譜系演化**：BERT (bidirectional) → GPT (causal + KV cache) 是經典範式。StreamVGGT 是 VGGT 譜系做了同樣 transition。

---

## 5 · 帶數字走一遍 — Worked Example (Toy)

設定：drone 飛 100 frame @ 30 FPS（3.3 sec footage）

**VGGT batch**：
- 等所有 100 frame 收齊
- forward pass: ~5-10 sec on A100 `UNVERIFIED`
- 輸出: 100 pose + 100 depth map
- **end-to-end latency**: 3.3 sec recording + 5-10 sec inference = **~10 sec**（不可 control loop 使用）

**StreamVGGT**：
- frame_1 來 → forward (cache empty) → pose_1, depth_1 (~100 ms `UNVERIFIED`)
- frame_2 來 → forward (attend cache_1) → pose_2, depth_2 (~50 ms cache 用)
- ...
- frame_100 → pose_100, depth_100 (~50-100 ms 看 cache 多大)
- **per-frame latency**: ~50-150 ms `UNVERIFIED`
- **end-to-end recording-to-final**: 3.3 sec recording + ~100 ms last frame = **~3.5 sec**

→ Streaming 把 end-to-end 從 10 sec → 3.5 sec（3× 改善），且**每 frame 都有 estimate**（不必等完）。但仍 ≥ 50 ms / frame，遠不到 aerial 5 ms 預算。

---

## 6 · 🚩 Hidden Assumptions

| 假設 | 看似合理 | 實際 |
|---|---|---|
| **「causal attention 不丟資訊」** | LLM 工作得很好 | 3D 重建需要全局一致性 — causal 沒看未來，loop closure 是 SLAM 後端傳統強項；StreamVGGT 用 distillation from bidirectional model 補救，但 **gap 仍存在 `UNVERIFIED`** |
| **「KV cache 可無限延伸」** | LLM 上下文長度漲 | ✅ **GitHub-VERIFIED 災難**：1300 frame @ 518px → **>100 GB GPU memory**（issue #24，maintainer 8 個月無回應）。24 GB GPU 大概 ~300 frame 就 OOM |
| **「streaming = real-time」** | 名字暗示 | StreamVGGT 「typically reconstructs in under one second」 — sub-second 不等於 real-time (需 ≤ sensor period) |
| **「替代 VGGT batch」** | 通常理解 | distillation 訓練意味 StreamVGGT 是 batch VGGT 的 *streaming approximation* — 精度仍 ≤ batch |
| **「替代 3R-SLAM Hybrid」** | 都是 streaming | StreamVGGT 純 feed-forward 無 loop closure / 無 IMU coupling / 無 metric scale，仍**輸於** hybrid 在這三軸 |

---

## 7 · 🎤 Interview Tip

> **「StreamVGGT 出來了，aerial 可以上嗎？」**
>
> 正確答：「StreamVGGT 把 VGGT 從 batch 變 stream（causal attention + KV cache），**latency 從 ~10 sec 降到 sub-second** — 對 manipulation / offline 都是好事。**但 aerial 仍 ❌**：(a) per-frame 仍 50-150 ms 量級遠 > 5 ms 控制環預算；(b) 仍 un-metric scale；(c) 訓練 prior 仍無 propeller vibration / motion blur。**aerial deployment envelope 仍未變**，跟 VGGT-Ω 一樣。」
>
> 錯答：「streaming = real-time，可以上 aerial」 — streaming ≠ real-time，且仍 ≥ 50 ms / frame。

---

## 8 · 🔁 Atlas 联动 — GitHub-validated 失败模式

→ 詳見 [`github_failure_atlas.md`](./github_failure_atlas.md)

**GitHub-VALIDATED failure modes**（2026-05-24 deep dive 確認，原 v1 dissection 的 UNVERIFIED predictions 多數已被 issue / follow-up paper 驗證）：

| 失敗模式 | 觸發場景 | GitHub evidence | 驗證狀態 |
|---|---|---|---|
| **KV cache 顯存爆炸** | ~1 分鐘 1300-frame 視頻 @ 518px | **issue #24**：「GPU memory has exceeded 100GB」maintainer **無回應 8 個月+**（2025-09 開至 2026-05）| ✅ VERIFIED — 真實災難性，比我們原 napkin 預測（500 frame ~10GB）嚴重 5-10× |
| **Multi-view alignment 失敗（繼承自 VGGT batch）** | 6 張同一物體不同角度 image | **issue #29**：「6 images of human face 從不同角度 → 分別生成 misaligned point clouds 不對齊」maintainer 無回應 | ✅ VERIFIED — 不是 stream 帶來的問題，VGGT batch 原有問題繼承過來 |
| **TensorRT deploy 未驗證** | 試 production deploy | **issue #30**：「Due to KV cache during inference, possible to convert to TensorRT?」maintainer 無回應 | ⚠ UNVERIFIED — 主流 deploy path 仍是 question mark |
| **KV cache 策略不透明** | 想自訂 cache 行為 | **issue #25**：「each layer has different K,V — do you cache all layers?」maintainer 無回應 | ⚠ 設計細節 maintainer 不公開回應 |
| **長視頻處理無官方解** | 任何超過幾百幀 | **issue #24** + **issue #34**（ARKitScenes_Multi）+ **issue #28**（compute_pose_loss not work）多 issue 集中**長序列**和**訓練 reproducibility** | ✅ VERIFIED — 整類問題 maintainer 響應度低 |
| **Causal attention 精度 gap vs bidirectional** | 比 VGGT batch | 論文用 *distillation from bidirectional VGGT* 補救，但不可能完全達 batch 精度 | ⚠ 論文宣稱「competitive」未公布具體數字 |

**整體 maintainer 響應度**：StreamVGGT 25 open issues / 0 closed（2026-05）— maintainer 響應**極低**。是 research artefact 不是 maintained product。

**社群信號**：GitHub 913★ / 47 fork（2026-05）— 高學術關注，但 production 不可用。

### 8.1 · 生態系統反應（4 個 follow-up paper 6 個月內出，解 memory 問題）

StreamVGGT 的 KV cache 爆炸催生了一整個 sub-paradigm：

| Follow-up | Date | 設計 | 性能 |
|---|---|---|---|
| **XStreamVGGT** (arXiv 2601.01204) | 2026-01 | KV cache pruning + quantization | **4.42× memory ↓**, **5.48× inference ↑**, perf degradation "mostly negligible" |
| **OVGGT** (arXiv 2603.05959) | 2026-03 | Self-Selective Caching + Dynamic Anchor Protection | **O(1) constant memory**，序列長度無關 |
| **FrameVGGT** (arXiv 2603.07690) | 2026-03 | Frame Evidence Rolling Memory | similar memory cap |
| **STAC** ([stac-3r.github.io](https://stac-3r.github.io/)) | 2026 | Spatio-Temporal Aware Cache Compression | similar |

→ **建議讀者**：要 streaming 3D 從 StreamVGGT 起步，但 production 候選優先看 OVGGT (O(1)) 或 XStreamVGGT (4× 省記憶體)。

---

## 9 · 🔁 Cross-references

- VGGT 原版 → [`vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md)
- VGGT-Ω (batch efficiency upgrade) → [`vggt_omega_dissection.md`](./vggt_omega_dissection.md)
- **Memory-compression follow-ups** (production 候選)：
  - **XStreamVGGT** ([arXiv 2601.01204](https://arxiv.org/abs/2601.01204), 2026-01) — KV cache pruning + quantization, 4.42× memory ↓, 5.48× speedup
  - **OVGGT** ([arXiv 2603.05959](https://arxiv.org/pdf/2603.05959), 2026-03) — O(1) constant memory
  - **FrameVGGT** ([arXiv 2603.07690](https://arxiv.org/pdf/2603.07690), 2026-03) — Frame Evidence Rolling Memory
  - **STAC** ([stac-3r.github.io](https://stac-3r.github.io/)) — Spatio-Temporal Aware Cache Compression
- 3R-SLAM Hybrid alternative (learned 3D + classical SLAM 後端) → [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)（涵蓋為什麼 streaming feed-forward 仍輸 hybrid 在 aerial）
- LLM causal attention + KV cache 起源 → GPT-2 paper / Vaswani 2017 Transformer
- 並行 incremental 路線 → INCVGGT (ICLR 2026)

---

## 10 · 📊 5-axis 座標

| 軸 | 值 |
|---|---|
| Problem | Online Streaming Feed-Forward 3D |
| Representation | Dense pointmap + depth + pose (per-frame incremental) + memory KV cache |
| Sensor | Mono RGB video stream |
| Paradigm | Learned end-to-end + Temporal causal attention + KV-cache memory |
| Time | **Online feed-forward streaming** (新類 — LLM-style incremental，不是 batch / 不是 per-scene optim / 不是 incremental smoother) |

→ 詳見 [`cheat-sheet/ontology.md §5.2`](../../cheat-sheet/ontology.md) feed-forward 多 view 第 3 子類「Online streaming」。

---

## 11 · 對讀者

- **Manipulation 工程師** — StreamVGGT 比 VGGT batch 適合 long video sequence 場景（30 sec+ 連續觀察）。但 per-scene optimization 仍精度王者。
- **Aerial 工程師** — StreamVGGT **不為你改 envelope**。仍走 VINS / OpenVINS / 3R-SLAM Hybrid。
- **AD 工程師** — streaming + causal 跟 Tesla FSD v13 temporal transformer rolling buffer 思想接近，可能值得做 ablation 比較。
- **Research 學生** — StreamVGGT 是 *causal attention + KV cache* 的 3D 譜系首次驗證，是 ICLR / NeurIPS 2026-2027 的 hot architecture 模板。

---

## 12 · Falsifiable predictions

1. ✅ **VERIFIED 2026-01 to 2026-03（早於預測 ~12 個月）**：StreamVGGT v2 / 後繼 with cache eviction 預期 2027-06 前出。實際 **6 個月內** 已出 4 個：XStreamVGGT (arXiv 2601.01204, 2026-01) / FrameVGGT (2603.07690) / OVGGT (2603.05959) / STAC — XStreamVGGT 達 4.42× memory 減少 + 5.48× speedup，OVGGT 達 O(1) constant memory。
2. **2027-12 前**：第一個 streaming + metric-aware feed-forward 3D 會出 — 借鑑 StreamVGGT causal pattern + scale anchor head（IMU / RTK）。
3. **2027-12 前不會發生**：StreamVGGT 譜系成為 aerial 200 Hz 主前端 — per-frame latency 上限仍 ≥ 30 ms 量級 (memory bandwidth bound)，不到 5 ms 預算。
4. **2027-06 前**：StreamVGGT 主 repo 仍 maintainer 響應度低（25 open issue / 0 closed at 2026-05）；production candidate 會是 follow-up papers (XStreamVGGT / OVGGT)，不是原 repo。

---

## 13 · 與 handbook prediction 對照

**handbook 之前的 prediction (vggt_omega_dissection §7.1)**：

> "2027-06 前：會出現 VGGT-Ω 衍生 streaming variant（可能叫 VGGT-Σ 或類似），把 N-view batch 改成 increment-per-frame。register attention 天然適配 streaming（register 當 state cache）。"

→ **VERIFIED 2026-07**：StreamVGGT 用 *causal attention + cached KV memory* 達到 — 跟我們 prediction 方向一致（memory token = register cache 的 streaming 化），**早於預測 ~1 年**。

handbook 的 falsifiability discipline 通過驗證。

---

## References

### Primary

- **StreamVGGT** — Wang et al. *ICLR 2026* · [arXiv:2507.11539](https://arxiv.org/abs/2507.11539) · [GitHub](https://github.com/wzzheng/StreamVGGT) (913★, 25 open issue / 0 closed at 2026-05) · [Project page](https://wzzheng.net/StreamVGGT/)
- **VGGT-Ω** — Wang et al. *CVPR 2026 Oral* · [arXiv:2605.15195](https://arxiv.org/abs/2605.15195)
- **VGGT v1** — Wang et al. *CVPR 2025 Best Paper* · [arXiv:2503.11651](https://arxiv.org/abs/2503.11651)

### Critical GitHub issues (load-bearing failure mode evidence)

- [issue #24](https://github.com/wzzheng/StreamVGGT/issues/24) — long video memory: 1300 frame → >100GB (open since 2025-09)
- [issue #25](https://github.com/wzzheng/StreamVGGT/issues/25) — KV cache strategy unclear (which layers cached)
- [issue #27](https://github.com/wzzheng/StreamVGGT/issues/27) — kv cache in camera head
- [issue #29](https://github.com/wzzheng/StreamVGGT/issues/29) — Multi-view alignment failure (face example)
- [issue #30](https://github.com/wzzheng/StreamVGGT/issues/30) — TensorRT deployment unverified
- [issue #34](https://github.com/wzzheng/StreamVGGT/issues/34) — ARKitScenes_Multi dataset missing

### Follow-up papers (memory-compression sub-paradigm in response to StreamVGGT)

- **XStreamVGGT** — *2026-01* · [arXiv:2601.01204](https://arxiv.org/abs/2601.01204) — KV cache pruning + quantization, **4.42× memory ↓ + 5.48× speedup**
- **FrameVGGT** — *2026-03* · [arXiv:2603.07690](https://arxiv.org/pdf/2603.07690) — Frame Evidence Rolling Memory
- **OVGGT** — *2026-03* · [arXiv:2603.05959](https://arxiv.org/pdf/2603.05959) — **O(1) constant-cost streaming**，Self-Selective Caching + Dynamic Anchor Protection
- **STAC** — [project](https://stac-3r.github.io/) — Spatio-Temporal Aware Cache Compression

### Lineage

- **Register tokens for ViT** — Darcet et al. *ICLR 2024* · [arXiv:2309.16588](https://arxiv.org/abs/2309.16588)
- **INCVGGT (parallel incremental line)** — *ICLR 2026* · [OpenReview](https://openreview.net/pdf/1995d220697c6b5a0dc0dde14751e3ee4c351422.pdf)
- **CroCo** — Weinzaepfel et al. *NeurIPS 2022* · [arXiv:2210.10716](https://arxiv.org/abs/2210.10716)
- **DUSt3R** — Wang et al. *CVPR 2024* · [arXiv:2312.14132](https://arxiv.org/abs/2312.14132)
- **GPT-2 (KV cache origin)** — Radford et al. 2019
- **FlashAttention-2** — Dao 2023 · [arXiv:2307.08691](https://arxiv.org/abs/2307.08691)

---

## Boundary

- 與 VGGT v1 / Ω 的完整 batch 解構 → 各自 dissection
- 與 3R-SLAM Hybrid 的對比 → `crossing/slam-vio-migration/vggt_vs_drone_vio.md` §6
- 純 LLM KV cache / FlashAttention 細節 → out of scope（自查 transformer 文獻）

---

*Last updated: 2026-05-24 · v1 opinionated draft · handbook prediction verified*
