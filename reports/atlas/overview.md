# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 1491 papers · 2026-07-08 → 2026-08-21 · ⚡ 163 · 🔧 590 · 📖 738

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 63
learned                    █████████████████████··· 219
hybrid                     ███████████████········· 154
generative                 █████··················· 52
3R-SLAM-hybrid             █······················· 8
VLA                        ████████████████████████ 254
world-model-as-policy      ██████████·············· 109
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 | W33 |
|---|---:|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 13 | 1 |
| learned | 37 | 39 | 37 | 54 | 40 | 12 |
| hybrid | 17 | 37 | 44 | 25 | 23 | 8 |
| generative | 7 | 13 | 10 | 7 | 12 | 3 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 | 1 |
| VLA | 37 | 49 | 50 | 43 | 58 | 17 |
| world-model-as-policy | 11 | 18 | 17 | 26 | 30 | 7 |
| **total** | **118** | **172** | **176** | **167** | **177** | **49** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 143
fixed-lag                  ························ 1
incremental                ███████················· 128
per-scene                  ████████████████████████ 426
feed-forward               █████··················· 82
temporal-transformer-rolling █████··················· 94
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 239
navigation                 █████████████████······· 173
spatial-reasoning          █████████··············· 92
reconstruction             ████████················ 82
pose                       ███····················· 34
depth                      ██······················ 22
tracking                   ██······················ 21
VSLAM                      ██······················ 19
VIO                        █······················· 13
mapping                    █······················· 10
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 223
scene-graph                █████████████··········· 123
3DGS                       █████████··············· 80
sparse                     ██████·················· 60
pointmap                   ██████·················· 58
BEV                        ██······················ 23
voxel                      ██······················ 19
NeRF                       ██······················ 18
implicit-sdf               ██······················ 17
mesh                       █······················· 10
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 361
multi-modal                ███████████············· 162
RGBD                       ██████████·············· 150
LiDAR                      ██······················ 26
event                      █······················· 17
stereo                     █······················· 14
IMU                        █······················· 9
4D-radar                   █······················· 8
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Robotic Manipulation is Vision-to-Geometry Mapping: Vision-Geometry Backbones over Language and Video Models](https://arxiv.org/abs/2604.12908)** — `world-model-as-policy` · 2026-08-14
  - _首次明確提出並實作「vision-to-geometry mapping」作為機械臂控制的本體論軸心，以預訓練3D世界模型（非語言/視頻）為backbone，取代VLA範式中語義中介的必要性，解決了長期存在的‘語義鴻溝導致幾何不忠實’這一ontology §13核心爭議。_
- **[MuseVLA: An Adaptive Multimodal Sensing Vision-Language-Action Model for Robotic Manipulation](https://arxiv.org/abs/2606.17598)** — `VLA` · 2026-08-14
  - _首次提出「可擴展的傳感器即工具（sensor-as-tool）」架構，將異質物理傳感器（溫度、音頻、雷達等）動態綁定至VLA模型的推理鏈中，實現跨模態感知-語言-動作的統一token化調度與 grounded sensor image 中間表示，解決了長期存在的「VLA模型被RGB綁定、無法原生支持物理屬性感知」這一ontology §13核心爭議。_
- **[4D-WAM: Infusing Spatiotemporal Awareness into World Action Models through Trajectory Fields](https://arxiv.org/abs/2608.08023)** — `world-model-as-policy` · 2026-08-14
  - _首次將4D trajectory fields作為可學習的spatiotemporal ontology注入WAMs，使world-model-as-policy範式具備顯式、可微分的3D運動軌跡建模能力——此前WAMs僅在2D像素空間操作，無法推導或約束3D動作軌跡，此工作閉合了'world model → actionable 3D trajectory'的語義鴻溝。_
- **[World Tokens: Enhancing Embodied Policies with Training-Time World Modeling](https://arxiv.org/abs/2608.09730)** — `world-model-as-policy` · 2026-08-14
  - _首次實現訓練時耦合世界模型（未來視頻去噪）與動作策略的梯度共享架構，且嚴格解耦部署：世界建模僅存於訓練階段、不參與推理，解決了WAMs長期面臨的‘表現力-延遲’根本權衡（ontology §13 爭議），開闢 world-model-as-training-signal 新範式軸。_
- **[PBD-AG: Persistent Baseline-Delta Active Graphs with Uncertainty-Aware Inspection for Long-Horizon Service Robots](https://arxiv.org/abs/2608.10449)** — `3R-SLAM-hybrid` · 2026-08-14
  - _首次提出「baseline-delta active graph」範式，將世界模型解耦為幾何可驗證的穩定基線（fixtures）與可主動檢驗的動態增量（object events），並以不確定性感知的幾何可見性閘門（geometric visibility gate）解決長期SLAM中因遮擋導致的錯誤刪除這一 ontology §13 中關於「persistent spatial identity under partial observability」的長期爭議，實現可量化的存在性/身份連續性保障。_
- **[VIScore: Diagnosing Planning-Relevant Quality in Latent World Models](https://arxiv.org/abs/2608.11174)** — `world-model-as-policy` · 2026-08-14
  - _首次提出可量化的 latent world model 規劃品質診斷指標 VIScore，解開了長期懸而未決的『潛在空間性質與規劃成功率脫鉤』問題（ontology §13 爭議：『how to evaluate whether a world model’s latent space is *planning-ready*?』），並透過 encoder-predictor-planner 三階耦合測量軸，確立規劃相關品質的可微分、可排序、跨域泛化評估範式。_
- **[Towards the Harness of Embodied Agents](https://arxiv.org/abs/2608.11246)** — `VLA` · 2026-08-14
  - _首次將 coding-agent 的 harness 范式嚴格遷移至物理具身智能，並通過 Scene Graph as Context（新 symbolic-spatial grounding 軸）與 Evaluation as Exit Codes（新 action-termination-and-diagnosis 軸）解決了物理世界中「不可觀測狀態」與「不可判定執行結果」這兩個 ontology §13 中長期懸而未決的範式級鴻溝。_
- **[How Can Driving World Models Do Counterfactual Prediction?](https://arxiv.org/abs/2608.11601)** — `world-model-as-policy` · 2026-08-14
  - _首次形式化並量化駕駛世界模型中 counterfactual prediction 的因果失配問題，提出基於 abduction-action-prediction 因果三元組的理論框架，並構建首個具 factual/counterfactual 配對標註的可控模擬基準——解決 ontology §13 中 'world model 是否真正支持反事實推理' 這一長期未解爭議，且提供可量化的評估軸心。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._