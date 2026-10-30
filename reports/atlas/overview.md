# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4109 papers · 2026-07-08 → 2026-10-30 · ⚡ 324 · 🔧 2600 · 📖 1185

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 257
learned                    ███████████████████····· 857
hybrid                     ████████████············ 564
generative                 ██████·················· 250
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1084
world-model-as-policy      █████████··············· 400
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W37 | W38 | W39 | W40 | W41 | W42 | W43 | W44 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 12 | 31 | 28 | 13 | 13 | 8 | 18 | 24 |
| learned | 45 | 56 | 50 | 51 | 50 | 26 | 84 | 76 |
| hybrid | 22 | 41 | 44 | 38 | 34 | 17 | 60 | 30 |
| generative | 18 | 20 | 18 | 13 | 11 | 13 | 24 | 8 |
| 3R-SLAM-hybrid | · | · | · | 1 | · | 1 | · | · |
| VLA | 37 | 82 | 95 | 96 | 87 | 65 | 111 | 82 |
| world-model-as-policy | 12 | 31 | 38 | 28 | 28 | 23 | 34 | 23 |
| **total** | **146** | **261** | **273** | **240** | **223** | **153** | **331** | **243** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 500
fixed-lag                  █······················· 26
incremental                ████████████············ 456
per-scene                  ███████████████████····· 748
feed-forward               ████████████████████████ 948
temporal-transformer-rolling █████████████··········· 499
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1346
navigation                 ███████████············· 622
spatial-reasoning          ██████·················· 318
reconstruction             █████··················· 257
pose                       ███····················· 187
tracking                   ██······················ 119
mapping                    █······················· 78
VSLAM                      █······················· 70
depth                      █······················· 52
VIO                        █······················· 50
occupancy                  ························ 19
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 882
scene-graph                █████████··············· 323
pointmap                   ███████················· 241
sparse                     ██████·················· 203
3DGS                       █████··················· 197
mesh                       ███····················· 116
BEV                        ███····················· 99
voxel                      ██······················ 67
implicit-sdf               █······················· 39
NeRF                       █······················· 30
HD-map                     ························ 14
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1323
multi-modal                ██████████████████······ 969
RGBD                       ███████················· 369
LiDAR                      █······················· 82
event                      █······················· 41
IMU                        █······················· 40
stereo                     █······················· 35
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

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
- **[ViT-H: Generative Video-To-Humanoid Control with Motion Tracking Feedback](https://arxiv.org/abs/2610.32966)** — `generative` · 2026-10-26
  - _以 diffusion 直接從影片生成人形參考動作，並用下游追蹤結果做 DPO 後訓練，繞過 reconstruction-retargeting 管線，讓 reference motion 的可執行性首次成為可直接優化的目標，開出 generation-and-tracking 新軸。_
- **[UniFlowWAM: A Unified World-Action Model with Visual Semantics and 4D Geometry](https://arxiv.org/abs/2610.30991)** — `world-model-as-policy` · 2026-10-23
  - _把 3D scene flow 從「旁路模組／額外預測頭」升格為與視覺、動作對等的第三模態，用模態對稱 diffusion transformer（每模態一 expert + joint attention）配合十種 target/condition/absent 角色網格，讓同一模型同時當 policy、前向／逆向動力學與未來特徵／4D 流預測器——開了一條「幾何流作為 policy 內生模態」的世界-動作模型軸，而非又在既有 VLA 上加一個輔助 head。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._