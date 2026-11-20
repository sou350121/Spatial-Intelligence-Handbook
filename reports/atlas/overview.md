# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4761 papers · 2026-07-08 → 2026-11-20 · ⚡ 357 · 🔧 3123 · 📖 1281

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 313
learned                    ███████████████████····· 1021
hybrid                     ████████████············ 656
generative                 ██████·················· 307
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1293
world-model-as-policy      █████████··············· 474
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W40 | W41 | W42 | W43 | W44 | W45 | W46 | W47 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 13 | 8 | 18 | 24 | 23 | 14 | 19 |
| learned | 51 | 50 | 26 | 84 | 76 | 67 | 43 | 54 |
| hybrid | 38 | 34 | 17 | 60 | 30 | 39 | 32 | 21 |
| generative | 13 | 11 | 13 | 24 | 8 | 14 | 20 | 24 |
| 3R-SLAM-hybrid | 1 | · | 1 | · | · | · | · | · |
| VLA | 96 | 87 | 65 | 111 | 82 | 75 | 54 | 84 |
| world-model-as-policy | 28 | 28 | 23 | 34 | 23 | 29 | 13 | 34 |
| **total** | **240** | **223** | **153** | **331** | **243** | **247** | **176** | **236** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 592
fixed-lag                  █······················· 36
incremental                ██████████·············· 526
per-scene                  ████████████████········ 828
feed-forward               ████████████████████████ 1216
temporal-transformer-rolling ███████████············· 582
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1632
navigation                 ███████████············· 736
spatial-reasoning          ██████·················· 377
reconstruction             ████···················· 295
pose                       ███····················· 226
tracking                   ██······················ 148
mapping                    █······················· 91
VSLAM                      █······················· 79
depth                      █······················· 62
VIO                        █······················· 62
occupancy                  ························ 22
SfM                        ························ 15
VO                         ························ 13
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 1068
scene-graph                ████████················ 360
pointmap                   ██████·················· 277
sparse                     █████··················· 236
3DGS                       █████··················· 217
mesh                       ███····················· 143
BEV                        ███····················· 117
voxel                      ██······················ 92
implicit-sdf               █······················· 48
NeRF                       █······················· 30
HD-map                     █······················· 23
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1570
multi-modal                ██████████████████······ 1167
RGBD                       ██████·················· 423
LiDAR                      █······················· 94
IMU                        █······················· 48
event                      █······················· 45
stereo                     █······················· 43
4D-radar                   ························ 24
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[TacInno: Teaching Vision-Language-Action Models the Contact Dynamics Beyond Vision and Action](https://arxiv.org/abs/2611.26405)** — `VLA` · 2026-11-20
  - _以「視覺+動作無法解釋的殘差」重新定義觸覺監督：把觸覺訊號減去可由 vision/action 預測的部分（tactile innovation），僅作為離散 code 的輔助預測目標、部署時零額外模組——這是新的監督軸，直接解掉「視觸 VLA 實務上忽略觸覺輸入、增益不穩」這個既有痛點，而非又一次把觸覺塞進 VLA 的應用堆疊。_
- **[How Uncertain Is My Action? Self-Correcting Visual Planning with Frozen World Models](https://arxiv.org/abs/2611.23620)** — `world-model-as-policy` · 2026-11-19
  - _首創「反向執行凍結世界模型」的位移分數（只保留位移可產生的殘差，並以局部最優檢定＋Cramér-Rao 誤差棒估計），讓凍結 world-model planner 在部署時自行偵測/命名/補償執行器位移——開了一條「世界模型自我監測與自我修正」的新軸，且真機把 36mm 誤差降到 3-5mm。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._