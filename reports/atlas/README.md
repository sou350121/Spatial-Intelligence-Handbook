# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 762 papers · 2026-07-08 → 2026-08-04 · ⚡ 120 · 🔧 486 · 📖 156

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 54
learned                    █████████████████████··· 178
hybrid                     ████████████████········ 131
generative                 █████··················· 44
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 199
world-model-as-policy      ██████████·············· 83
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 |
|---|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 5 |
| learned | 37 | 39 | 38 | 55 | 9 |
| hybrid | 17 | 37 | 45 | 26 | 6 |
| generative | 8 | 13 | 11 | 7 | 5 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | · |
| VLA | 37 | 50 | 51 | 47 | 14 |
| world-model-as-policy | 11 | 19 | 18 | 27 | 8 |
| **total** | **119** | **174** | **181** | **174** | **47** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 123
incremental                ████████················ 108
per-scene                  ████████████████████████ 337
feed-forward               ████···················· 63
temporal-transformer-rolling █████··················· 76
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 178
navigation                 █████████████████████··· 154
reconstruction             ██████████·············· 72
spatial-reasoning          █████████··············· 65
pose                       ████···················· 27
tracking                   ██······················ 18
VSLAM                      ██······················ 18
depth                      ██······················ 17
VIO                        █······················· 11
mapping                    █······················· 9
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 175
scene-graph                ██████████████·········· 102
3DGS                       █████████··············· 62
sparse                     ████████················ 55
pointmap                   ██████·················· 45
BEV                        ██······················ 17
NeRF                       ██······················ 16
implicit-sdf               ██······················ 16
voxel                      ██······················ 15
mesh                       █······················· 7
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 298
multi-modal                ██████████·············· 125
RGBD                       ██████████·············· 119
LiDAR                      ██······················ 22
event                      █······················· 14
stereo                     █······················· 13
IMU                        █······················· 9
4D-radar                   ························ 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[What Can Latent World Models Know? Physical Parameter Identifiability in Multimodal Predictive Representations](https://arxiv.org/abs/2607.27017)** — `world-model-as-policy` · 2026-08-04
  - _首次建立可證偽的物理參數可識別性理論框架，透過 certificate-gated protocol 將 latent world model 的物理知識內容從「黑箱關聯」提升為「可驗證的因果參數嵌入」，解了 ontology §13 中長期懸而未決的『latent 是否真知 physics？如何量化其物理語義完整性？』爭議。_
- **[ST-WAM: Semantic-Temporal World Action Model for Robust Manipulation under Visual Distribution Shifts](https://arxiv.org/abs/2607.28993)** — `world-model-as-policy` · 2026-08-04
  - _首次將世界模型範式（world-model-as-policy）解耦為語義空間（DINOv3）與細粒度動態空間（VAE），並透過 Dual-Space Future Experts 與 Current-Anchored Intent Retrieval 實現跨視覺分佈的動作泛化——此前所有 WAM 均綁定像素級生成，無法在 distribution shift 下區分 task-relevant state transition 與 task-irrelevant visual hallucination。_
- **[Auto-JEPA: A Latent World Model of Continuous Intent for End-to-End Autonomous Driving](https://arxiv.org/abs/2607.29031)** — `world-model-as-policy` · 2026-08-04
  - _首次將 JEPA（Joint-Embedding Predictive Architecture）範式引入 autonomous driving world modeling，以連續 latent intent 為核心表徵取代傳統 dense future reconstruction（如 occupancy/BEV/video），實現「規劃導向的壓縮世界建模」——解決 ontology §13 中長期爭議『world model 是否必須重建可觀測物理狀態？』，並給出可量化的因果干預證據（語義遮蔽實驗量化 intent 對關鍵 agent 的敏感性）。_
- **[GO-PRE: Goal-Oriented Next-Best-View Selection via Predictive Rendering Entropy for Active 3D Reconstruction](https://arxiv.org/abs/2607.29037)** — `generative` · 2026-08-04
  - _首次將信息增益直接定義在渲染預測空間（而非參數或幾何空間），開闢了「prediction-space information gain」這一新方法軸，使主動重建的目標函數與最終重建 fidelity 完全對齊，解決了長期存在的 surrogate-signal misalignment 問題（ontology §13.2）。_
- **[ActFovea: Runtime Safeguarding for VLA Policies via Spatiotemporal Visual-Action Consistency](https://arxiv.org/abs/2607.29169)** — `VLA` · 2026-08-04
  - _首次提出 runtime safeguarding 范式，將 VLA 政策的魯棒性保障從 offline robustness design（如數據增強、對抗訓練）轉向 online spatiotemporal visual-action consistency verification，實現了「不修改策略、不重訓練」條件下動態干擾檢測與幾何-動作一致性的可驗證恢復——這在 ontology §13 的「VLA 安全性與故障恢復」爭議中提供了首個可量化的、基於運動學約束與視覺時序新鮮度的 formal safety monitor 軸。_
- **[BWM: A Low-Cost High-Fidelity World Simulator for Robot Learning](https://arxiv.org/abs/2607.29302)** — `world-model-as-policy` · 2026-08-04
  - _首次將 world-model-as-policy 范式具體實作為可閉環評估、風險預判、策略排序的 stateful autoregressive simulator，解了 ontology §13 中 'world model 如何承擔 policy evaluation 的因果責任' 這一長期未量化爭議；其 action-aligned rollouts + initial-environment guidance + dynamic visual history 三重條件機制，構成新的 world-model 時序因果建模軸。_
- **[HAM-VLN: Harnessing Hierarchical Agentic Memory for Zero-Shot Vision-and-Language Navigation](https://arxiv.org/abs/2607.29600)** — `VLA` · 2026-08-04
  - _引入「agent-authored memory」新範式：首次將記憶建構（semantic + reflective + topological）與每步決策耦合於單一 LLM call 內，實現 depth-grounded world graph 的動態、有損但語義可控的壓縮與檢索，解決 training-free VLN 中長期累積記憶導致的推理崩潰這一範疇內長期未解的 scalability vs. grounding 權衡問題。_
- **[WCM: A World Critic Model for Vision-Language-Action Reinforcement Learning](https://arxiv.org/abs/2607.29613)** — `world-model-as-policy` · 2026-08-04
  - _首次將 critic 設計從純 scalar-return 回歸升級為 world-model-as-policy 軸上的聯合 latent dynamics 預測與價值估計，使 critic 自身具備顯式 temporal state representation 能力，解決了 VLA-RL 中長期存在的 partially observable control 下 critic 表徵退化問題。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._