# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 761 papers · 2026-07-08 → 2026-08-03 · ⚡ 120 · 🔧 486 · 📖 155

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 54
learned                    ██████████████████████·· 181
hybrid                     ████████████████········ 132
generative                 █████··················· 42
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 194
world-model-as-policy      ██████████·············· 84
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 |
|---|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 5 |
| learned | 37 | 39 | 38 | 55 | 12 |
| hybrid | 17 | 37 | 45 | 26 | 7 |
| generative | 8 | 13 | 11 | 7 | 3 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | · |
| VLA | 37 | 50 | 51 | 47 | 9 |
| world-model-as-policy | 11 | 19 | 18 | 27 | 9 |
| **total** | **119** | **174** | **181** | **174** | **45** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 122
incremental                ████████················ 109
per-scene                  ████████████████████████ 338
feed-forward               ████···················· 61
temporal-transformer-rolling █████··················· 77
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 177
navigation                 █████████████████████··· 153
reconstruction             ██████████·············· 71
spatial-reasoning          █████████··············· 65
pose                       ████···················· 27
tracking                   ███····················· 19
VSLAM                      ██······················ 18
depth                      ██······················ 18
VIO                        █······················· 11
mapping                    █······················· 9
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 174
scene-graph                ██████████████·········· 103
3DGS                       █████████··············· 62
sparse                     ███████················· 54
pointmap                   ██████·················· 44
BEV                        ██······················ 17
NeRF                       ██······················ 16
implicit-sdf               ██······················ 15
voxel                      ██······················ 15
mesh                       █······················· 7
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 297
multi-modal                ██████████·············· 127
RGBD                       ██████████·············· 120
LiDAR                      ██······················ 22
event                      █······················· 13
stereo                     █······················· 13
IMU                        █······················· 9
4D-radar                   ························ 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Temporally Centered SIGReg Improves Multi-Task LeWorldModel Learning: From Analysis to Method](https://arxiv.org/abs/2607.26924)** — `world-model-as-policy` · 2026-08-03
  - _首次提出將正則化目標從靜態潛在邊際分佈轉向**時序中心化殘差**（temporally centered residuals），在保持抗坍塌效果的同時解耦任務間表徵分離與簇內變異，從根本上解決多任務LeWorldModel中因邊際高斯化導致的表徵混疊問題——這是paradigm軸上對world-model-as-policy範式的關鍵修正。_
- **[What Can Latent World Models Know? Physical Parameter Identifiability in Multimodal Predictive Representations](https://arxiv.org/abs/2607.27017)** — `world-model-as-policy` · 2026-08-03
  - _首次建立可證偽的物理參數可識別性理論框架，定義並實證驗證「輸入約束」與「預測目標選擇」兩條軸如何 jointly決定 latent world model 能否收斂到物理參數（如 stiffness/drag），破解長期爭議『世界模型是否真學到物理』——提供 ontology §13 中 'identifiability under predictive objectives' 的可量化解。_
- **[ST-WAM: Semantic-Temporal World Action Model for Robust Manipulation under Visual Distribution Shifts](https://arxiv.org/abs/2607.28993)** — `world-model-as-policy` · 2026-08-03
  - _首度將世界模型範式（world-model-as-policy）從像素生成轉向語義-時序雙空間解耦建模，以DINOv3語義特徵為錨定的‘不生成未來影像’的隱式動作策略，解決了長期存在的訓練分佈幻覺（Training-Distribution Hallucination）這一 ontology §13 中關於 world model 可靠性與分布外魯棒性的核心爭議。_
- **[Auto-JEPA: A Latent World Model of Continuous Intent for End-to-End Autonomous Driving](https://arxiv.org/abs/2607.29031)** — `world-model-as-policy` · 2026-08-03
  - _首次將 JEPA（Joint Embedding Predictive Architecture）範式引入 autonomous driving 的 world model，以連續 latent intent 為核心表徵取代傳統世界重建（video/occupancy/BEV 預測），實現「不重建世界、只建模行動因果」的範式轉移——解了 ontology §13 中長期爭議『world model 是否必須具備感知保真度？』，並給出可量化的因果敏感性證據（語義遮蔽實驗）。_
- **[ActFovea: Runtime Safeguarding for VLA Policies via Spatiotemporal Visual-Action Consistency](https://arxiv.org/abs/2607.29169)** — `world-model-as-policy` · 2026-08-03
  - _首次提出 runtime safeguarding 范式，將 VLA 政策的魯棒性保障從 offline training-time robustness（learned）轉向 online spatiotemporal visual-action consistency verification（world-model-as-policy 的 runtime monitoring 軸），實現了對「視覺-動作時序對齊崩潰」這一長期隱性失效模式的可量化檢測與分級恢復——此前所有 VLA 工作均假設 observation-action pipeline 完全可信，無 runtime consistency ontology。_
- **[BWM: A Low-Cost High-Fidelity World Simulator for Robot Learning](https://arxiv.org/abs/2607.29302)** — `world-model-as-policy` · 2026-08-03
  - _首次提出將世界模型明確架構為雙重功能實體（data engine + policy evaluator），並實現可閉環風險預測與策略排序的stateful autoregressive action-conditioned視覺預測，解決了既有world model在robot learning中缺乏可驗證、可介入、可評估的行動因果推理能力這一長期爭議（ontology §13.2）。_
- **[HAM-VLN: Harnessing Hierarchical Agentic Memory for Zero-Shot Vision-and-Language Navigation](https://arxiv.org/abs/2607.29600)** — `world-model-as-policy` · 2026-08-03
  - _首次提出‘decision-coupled, agent-authored memory’範式，將世界建模從被動表徵（如BEV/scene-graph）升級為主動構建、深度接地、可檢索重構的動態世界圖（world graph），解決了VLN中長期存在的記憶膨脹與推理不可擴展性這一范疇級瓶頸（ontology §13 爭議：‘how to ground language in persistent spatial memory without training or dense mapping’）。_
- **[WCM: A World Critic Model for Vision-Language-Action Reinforcement Learning](https://arxiv.org/abs/2607.29613)** — `world-model-as-policy` · 2026-08-03
  - _首次將 critic 設計從 scalar-return regression 范式升級為 world-model-as-policy 范式：WCM 強制 critic 學習可預測的 latent world state（而非僅擬合 Q 值），從根本上解決 VLA 中 partially observable control 下 temporal credit assignment 的表示崩潰問題，實現 critic 表示與世界動態建模的耦合。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._