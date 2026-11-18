# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4636 papers · 2026-07-08 → 2026-11-18 · ⚡ 351 · 🔧 3020 · 📖 1265

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 307
learned                    ███████████████████····· 1000
hybrid                     █████████████··········· 646
generative                 ██████·················· 295
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1239
world-model-as-policy      █████████··············· 451
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W40 | W41 | W42 | W43 | W44 | W45 | W46 | W47 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 13 | 8 | 18 | 24 | 23 | 14 | 13 |
| learned | 51 | 50 | 26 | 84 | 76 | 67 | 43 | 33 |
| hybrid | 38 | 34 | 17 | 60 | 30 | 39 | 32 | 11 |
| generative | 13 | 11 | 13 | 24 | 8 | 14 | 20 | 12 |
| 3R-SLAM-hybrid | 1 | · | 1 | · | · | · | · | · |
| VLA | 96 | 87 | 65 | 111 | 82 | 75 | 54 | 30 |
| world-model-as-policy | 28 | 28 | 23 | 34 | 23 | 29 | 13 | 11 |
| **total** | **240** | **223** | **153** | **331** | **243** | **247** | **176** | **110** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 578
fixed-lag                  █······················· 34
incremental                ███████████············· 512
per-scene                  █████████████████······· 815
feed-forward               ████████████████████████ 1165
temporal-transformer-rolling ████████████············ 560
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1562
navigation                 ███████████············· 718
spatial-reasoning          ██████·················· 366
reconstruction             ████···················· 291
pose                       ███····················· 221
tracking                   ██······················ 144
mapping                    █······················· 88
VSLAM                      █······················· 78
depth                      █······················· 61
VIO                        █······················· 61
occupancy                  ························ 22
SfM                        ························ 15
VO                         ························ 12
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 1028
scene-graph                ████████················ 352
pointmap                   ██████·················· 265
sparse                     █████··················· 233
3DGS                       █████··················· 214
mesh                       ███····················· 140
BEV                        ███····················· 110
voxel                      ██······················ 87
implicit-sdf               █······················· 47
NeRF                       █······················· 30
HD-map                     █······················· 22
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1515
multi-modal                ██████████████████······ 1130
RGBD                       ██████·················· 410
LiDAR                      █······················· 93
IMU                        █······················· 46
event                      █······················· 45
stereo                     █······················· 40
4D-radar                   ························ 24
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[CoBoVLA: Decoupling Language from Action with Discrete Codes for Robust and Interpretable Robot Manipulation](https://arxiv.org/abs/2611.22395)** — `VLA` · 2026-11-18
  - _以共享離散 step code 作為語言與動作之間的瓶頸，將 VLA 拆成語言理解、視覺規劃與語言無關 actor，開出可逐階段歸因且抗指令改寫的新方法軸，解了既有 VLA 對 paraphrase 敏感與失敗不可定位的問題。_
- **[Body Schema Policy: Body as the Vision-Action Interface for Efficient Robot Loco-Manipulation](https://arxiv.org/abs/2611.22713)** — `generative` · 2026-11-18
  - _把「身體圖式」做成具體架構：將 joint/link token 掛在運動學樹上、以 screw motion 在連桿間傳遞特徵，並讓 body-queried vision 由各身體部位自行檢索視覺證據——用結構先驗換掉參數規模（75× 更少參數匹配 Ψ0），且無空間監督即湧現部位專屬視覺讀出，開了一條 morphology-grounded vision-action 介面新軸，而非又一個 VLA/擴散策略的應用。_
- **[CaFe: Causally Faithful Conditional Traffic Scenario Generation](https://arxiv.org/abs/2611.22855)** — `generative` · 2026-11-18
  - _提出「intent leakage / 因果忠實性」這條新軸：以配對干預測試量化「周遭車輛只應對可觀察的公開意圖反應」，並用限縮於 public beliefs 的 dual-stream diffusion-forcing 閉環模擬器，解決既有生成式交通模擬無法量測也無法避免的過早反應問題。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._