# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4169 papers · 2026-07-08 → 2026-11-02 · ⚡ 327 · 🔧 2650 · 📖 1192

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 262
learned                    ███████████████████····· 869
hybrid                     █████████████··········· 577
generative                 ██████·················· 253
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1104
world-model-as-policy      █████████··············· 406
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W38 | W39 | W40 | W41 | W42 | W43 | W44 | W45 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 31 | 28 | 13 | 13 | 8 | 18 | 24 | 5 |
| learned | 56 | 50 | 51 | 50 | 26 | 84 | 76 | 12 |
| hybrid | 41 | 44 | 38 | 34 | 17 | 60 | 30 | 13 |
| generative | 20 | 18 | 13 | 11 | 13 | 24 | 8 | 3 |
| 3R-SLAM-hybrid | · | · | 1 | · | 1 | · | · | · |
| VLA | 82 | 95 | 96 | 87 | 65 | 111 | 82 | 21 |
| world-model-as-policy | 31 | 38 | 28 | 28 | 23 | 34 | 23 | 6 |
| **total** | **261** | **273** | **240** | **223** | **153** | **331** | **243** | **60** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 509
fixed-lag                  █······················· 29
incremental                ███████████············· 466
per-scene                  ███████████████████····· 752
feed-forward               ████████████████████████ 975
temporal-transformer-rolling ████████████············ 505
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1370
navigation                 ███████████············· 638
spatial-reasoning          ██████·················· 323
reconstruction             █████··················· 259
pose                       ███····················· 189
tracking                   ██······················ 121
mapping                    █······················· 78
VSLAM                      █······················· 71
depth                      █······················· 52
VIO                        █······················· 52
occupancy                  ························ 20
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 897
scene-graph                █████████··············· 325
pointmap                   ███████················· 243
sparse                     ██████·················· 207
3DGS                       █████··················· 198
mesh                       ███····················· 120
BEV                        ███····················· 100
voxel                      ██······················ 69
implicit-sdf               █······················· 38
NeRF                       █······················· 30
HD-map                     ························ 15
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1337
multi-modal                ██████████████████······ 990
RGBD                       ███████················· 377
LiDAR                      █······················· 82
event                      █······················· 41
IMU                        █······················· 40
stereo                     █······················· 35
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[CausalWAM: Learning the Causes of Actions in World Action Models](https://arxiv.org/abs/2610.42096)** — `world-model-as-policy` · 2026-11-02
  - _在 world action model 上引入稀疏路由的可識別性理論，證明 action head 僅依賴 action-relevant latent causes（可識別到 permutation），无需时序依赖假设，开辟了 WAM 中 causal-identifiability 的新方法轴。_
- **[RoboArchitect: Automating the Design of Robotic Agents with Persistent Memory](https://arxiv.org/abs/2610.42141)** — `VLA` · 2026-11-02
  - _首次把「agent harness（控制代碼＋持久記憶）」本身當作可被 coding model 觀測 rollout、診斷失敗並迭代演化的搜尋對象，而非微調 policy 權重——開了『自動設計 agent 架構而非策略』這條新軸，並讓記憶隨演化累積（如抓取深度經驗）遷移到新場景。_
- **[ELEVATE: Agentic Controller Acquisition from Task Failure for Quadrupedal Manipulation](https://arxiv.org/abs/2610.38388)** — `VLA` · 2026-10-30
  - _把「任務失敗訊號→偵測能力缺口→coding agent 自動設計並精煉 RL 問題（reward/curriculum/termination）→驗證後併入能力庫再組合重試」閉環打通，使 agent 的動作空間可自我擴張而非受限於固定控制器庫，是既有 VLA/任務規劃 agent 做不到的新方法軸，且免真機訓練零樣本遷移到四足機械臂。_
- **[E0.5: From Reconstructive to Future-Predictive 3D Foundations for Robotic World-Action Modeling](https://arxiv.org/abs/2610.36011)** — `world-model-as-policy` · 2026-10-28
  - _⚡：把 3D 基礎模型由輔助特徵/重建目標提升為 world-action 模型的原生主幹，並聯合預測未來 3D 狀態與動作，開出 geometry-native 世界建模新軸。_
- **[Rollback: Experience Backtracking in World Models for Policy Improvement](https://arxiv.org/abs/2610.36068)** — `world-model-as-policy` · 2026-10-28
  - _把 world model 從只做前向模擬的替代物，改造成「可回溯的反事實引擎」：回到關鍵決策點分支替代動作、對比結果，做 action-level 信用分配，並取代另學的 value model；再加上以 LoRA 在 test-time 用真機軌跡校正動力學，形成自我增強的閉環——新軸在於 counterfactual rollback 與 test-time physics grounding，這是既有 forward-only world model / model-based RL 做不到的能力。_
- **[One Scan is Enough: Demonstration-Free Adaptation for Language-Guided Navigation](https://arxiv.org/abs/2610.33794)** — `VLA` · 2026-10-27
  - _將「新場景需人體遠端示範」的擴展瓶頸換成單支 iPhone 掃描→合成 grounded 導航 episode＋封閉式 Pareto 自適應（無 learned critic、無標籤），並以 82% vs 41% 量化證明掃描式自適應可泛化到未掃描區域，開了一條 demonstration-free 真實場景適配的新方法軸。_
- **[WAM-TTT: Steering World-Action Models by Watching Human Play at Test Time](https://arxiv.org/abs/2607.06988)** — `world-model-as-policy` · 2026-10-26
  - _開了一條測試時記憶轉向（test-time training）的新軸：把原始人類影片以自監督視頻預測吸收進凍結世界-動作模型內的輕量 KV 記憶，並用配對人-機數據元訓練對齊，首次做到無機器人動作、無標註、無微調即可將 RFM 轉向新任務變體，解了以往必須額外示範或 fine-tune 才能適應的行為轉向問題。_
- **[Do VLAs Know They Will Fail? Interpretable Success and Failure Patterns in Physical AI Systems](https://arxiv.org/abs/2610.32208)** — `VLA` · 2026-10-26
  - _首次證明 VLA（OpenVLA）動作模型的 SAE 稀疏激活本身攜帶「結果可預測」訊號，能在機器人進入不可逆狀態前於內部特徵層做失敗預測，並把特徵激活變化定位到具體行為階段、用 VLM 產生可驗證的行為描述——開的是「VLA 內省/可監控表徵」這條新軸，而非再刷一個策略指標。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._