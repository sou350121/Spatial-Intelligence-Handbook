# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4527 papers · 2026-07-08 → 2026-11-13 · ⚡ 346 · 🔧 2932 · 📖 1249

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 294
learned                    ███████████████████····· 967
hybrid                     █████████████··········· 635
generative                 ██████·················· 283
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1210
world-model-as-policy      █████████··············· 440
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W39 | W40 | W41 | W42 | W43 | W44 | W45 | W46 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 28 | 13 | 13 | 8 | 18 | 24 | 23 | 14 |
| learned | 50 | 51 | 50 | 26 | 84 | 76 | 67 | 43 |
| hybrid | 44 | 38 | 34 | 17 | 60 | 30 | 39 | 32 |
| generative | 18 | 13 | 11 | 13 | 24 | 8 | 14 | 20 |
| 3R-SLAM-hybrid | · | 1 | · | 1 | · | · | · | · |
| VLA | 95 | 96 | 87 | 65 | 111 | 82 | 75 | 54 |
| world-model-as-policy | 38 | 28 | 28 | 23 | 34 | 23 | 29 | 13 |
| **total** | **273** | **240** | **223** | **153** | **331** | **243** | **247** | **176** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 567
fixed-lag                  █······················· 33
incremental                ███████████············· 505
per-scene                  █████████████████······· 798
feed-forward               ████████████████████████ 1113
temporal-transformer-rolling ████████████············ 549
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1523
navigation                 ███████████············· 696
spatial-reasoning          ██████·················· 353
reconstruction             ████···················· 281
pose                       ███····················· 218
tracking                   ██······················ 138
mapping                    █······················· 87
VSLAM                      █······················· 77
VIO                        █······················· 58
depth                      █······················· 57
occupancy                  ························ 20
SfM                        ························ 14
VO                         ························ 11
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 1001
scene-graph                ████████················ 347
pointmap                   ██████·················· 257
sparse                     ██████·················· 230
3DGS                       █████··················· 211
mesh                       ███····················· 133
BEV                        ███····················· 107
voxel                      ██······················ 80
implicit-sdf               █······················· 47
NeRF                       █······················· 30
HD-map                     █······················· 21
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1467
multi-modal                ██████████████████······ 1098
RGBD                       ███████················· 404
LiDAR                      █······················· 91
IMU                        █······················· 45
event                      █······················· 43
stereo                     █······················· 40
4D-radar                   ························ 23
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[ActionCodec2: A Streaming Action Tokenizer](https://arxiv.org/abs/2611.15490)** — `VLA` · 2026-11-13
  - _首個串流式 action tokenizer：以 residual-relative 量化＋幾何覆蓋推導最小 motion primitive 集，把 action chunk 從「必須整塊解碼才能執行」改為增量釋放且重建誤差有界，令 VLA 首次能在單一 chunk 內做閉環狀態回饋——新軸在時間契約（chunk-decode → streaming/anytime decoding），非應用或刷分。_
- **[How Much of Your VLA Is kNN](https://arxiv.org/abs/2611.13160)** — `VLA` · 2026-11-11
  - _以「檢索即策略」的極簡 kNN 動作塊重用（無訓練達 91.7% LIBERO、擾動下最穩）量化回答了 VLA 泛化還是記憶這個懸而未決的爭議，並提出 LAC 這個可在離線預測成功率的表徵局部性指標，開出「把 VLM backbone 訓練成好的檢索鍵」這條有別於端到端策略學習的新方法軸。_
- **[X Marks the Spot: Diffusion for Image Geolocalization with Location Representations](https://arxiv.org/abs/2611.13180)** — `generative` · 2026-11-11
  - _將 diffusion 從語義不穩定的座標空間改到預訓練 location encoder 的潛在語義空間，並以 LAE 解碼回座標，首次讓生成式地理定位在三個 benchmark 上超越 retrieval-based，開出 location-representation diffusion 的新方法軸。_
- **[UGG: Unified Generative Geometry Model](https://arxiv.org/abs/2611.14440)** — `generative` · 2026-11-11
  - _把 feedforward 幾何預測與生成式視頻合成統一成單一擴散模型：用 per-modality / per-timestep 噪聲等級把「標註可用性」編碼進生成過程，使模型能在異質、只有部分幾何標註的數據上聯合訓練，並在無 GT 幾何下以觀測 RGB 的幾何證據做 inference-time 多假設搜索——這是既有 feedforward 幾何模型（需稠密 GT、單一確定輸出）與純生成模型（不能直接輸出度量深度/位姿）都做不到的能力軸。_
- **[Is Your Robot's Memory Just a Clock? Temporal Shortcuts in Memory-Augmented VLA Policies](https://arxiv.org/abs/2611.14488)** — `VLA` · 2026-11-11
  - _首次為 memory-augmented VLA 開出「記憶索引方式（時間戳索引 vs 事件索引）」這條新軸：用注入 null event、單獨 rescale 時間戳、移除時間編碼等因果干預，量化出「phantom progress」此一此前未被命名的失效模式（50 次中成功次數 47→16、44→10），並證明 event-indexed memory 才修得掉，屬對 §13 記憶機制爭議的可量化解答而非刷點。_
- **[ODEAction: From Predicting Chunks to Evolving Actions](https://arxiv.org/abs/2611.09672)** — `VLA` · 2026-11-09
  - _沿「動作生成」軸開新範式：以動作空間上的學習式轉移場 + ODE 積分取代 action-chunk 預測，從機制上消除 chunk 邊界不連續，且可作為 backbone-agnostic action head 插拔——這不是把既有 VLA 套新場景，而是換掉動作解碼這一環。_
- **[On Agentic Manipulation Policies](https://arxiv.org/abs/2611.09892)** — `VLA` · 2026-11-09
  - _把 policy 軸從 learned specialist（VLA / world-action model）翻轉為「通用基礎模型即控制器」的 agent-as-policy：同一 harness 不經任務訓練、不需 demo 即可跨單臂/雙臂/移動平台零樣本操作，並以 RoboLab-120 85.6% vs 49.2%/42.9% 與真機 104/108 的量化差距，給「是否還需要 specialist robot policy」這個長期爭議一個可檢驗的答案；再加 persistent memory 把跨 episode 經驗學習變成 4.6x 失效率的可量化槓桿。_
- **[Concertina: Embodying Manipulation and Cognition in One Diffusion Vision-Language Model](https://arxiv.org/abs/2611.07513)** — `VLA` · 2026-11-06
  - _把連續軌跡表示、blockwise 生成與物理座標監督直接放進共享 diffusion VLM backbone（僅 0.21% action 參數、無獨立 action expert），開闢 decoupled VLA → eVLM 的新架構軸，使動作與認知在參數與計算路徑上真正耦合。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._