# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4576 papers · 2026-07-08 → 2026-11-16 · ⚡ 348 · 🔧 2969 · 📖 1259

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 299
learned                    ███████████████████····· 986
hybrid                     █████████████··········· 643
generative                 ██████·················· 285
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1224
world-model-as-policy      █████████··············· 441
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W40 | W41 | W42 | W43 | W44 | W45 | W46 | W47 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 13 | 8 | 18 | 24 | 23 | 14 | 5 |
| learned | 51 | 50 | 26 | 84 | 76 | 67 | 43 | 19 |
| hybrid | 38 | 34 | 17 | 60 | 30 | 39 | 32 | 8 |
| generative | 13 | 11 | 13 | 24 | 8 | 14 | 20 | 2 |
| 3R-SLAM-hybrid | 1 | · | 1 | · | · | · | · | · |
| VLA | 96 | 87 | 65 | 111 | 82 | 75 | 54 | 14 |
| world-model-as-policy | 28 | 28 | 23 | 34 | 23 | 29 | 13 | 1 |
| **total** | **240** | **223** | **153** | **331** | **243** | **247** | **176** | **49** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 571
fixed-lag                  █······················· 33
incremental                ███████████············· 508
per-scene                  █████████████████······· 811
feed-forward               ████████████████████████ 1137
temporal-transformer-rolling ████████████············ 551
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1540
navigation                 ███████████············· 705
spatial-reasoning          ██████·················· 357
reconstruction             █████··················· 289
pose                       ███····················· 219
tracking                   ██······················ 140
mapping                    █······················· 88
VSLAM                      █······················· 78
depth                      █······················· 60
VIO                        █······················· 58
occupancy                  ························ 21
SfM                        ························ 15
VO                         ························ 11
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 1009
scene-graph                ████████················ 348
pointmap                   ██████·················· 262
sparse                     ██████·················· 232
3DGS                       █████··················· 213
mesh                       ███····················· 138
BEV                        ███····················· 107
voxel                      ██······················ 82
implicit-sdf               █······················· 47
NeRF                       █······················· 30
HD-map                     █······················· 22
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1493
multi-modal                ██████████████████······ 1111
RGBD                       ███████················· 408
LiDAR                      █······················· 93
IMU                        █······················· 45
event                      █······················· 44
stereo                     █······················· 40
4D-radar                   ························ 23
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Training Reasoning Models in Simulation to Natively Use Real Robots](https://arxiv.org/abs/2611.18562)** — `VLA` · 2026-11-16
  - _首次證明「reasoning model 即 robot-use agent」這條新軸：不做示範模仿、不接 harness 或 action head，純以模擬環境 RL（RURL）訓練 27B 開放權重模型輸出路徑（end-effector pose），並 zero-shot 遷移到未見機體與真機（真機 0%→60%、LIBERO 1.6%→74.4%），把「跨具身推理式策略」由封閉前沿模型獨有能力變成可複現的訓練範式。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._