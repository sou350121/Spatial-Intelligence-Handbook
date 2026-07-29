# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 622 papers · 2026-07-08 → 2026-07-29 · ⚡ 95 · 🔧 395 · 📖 132

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 41
learned                    █████████████████████··· 142
hybrid                     █████████████████······· 113
generative                 █████··················· 37
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 162
world-model-as-policy      █████████··············· 64
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 |
|---|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 4 |
| learned | 37 | 39 | 38 | 28 |
| hybrid | 17 | 37 | 47 | 12 |
| generative | 8 | 13 | 11 | 5 |
| 3R-SLAM-hybrid | · | 3 | 3 | · |
| VLA | 37 | 50 | 52 | 23 |
| world-model-as-policy | 11 | 19 | 18 | 16 |
| **total** | **119** | **174** | **184** | **88** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 100
incremental                ████████················ 89
per-scene                  ████████████████████████ 280
feed-forward               ████···················· 52
temporal-transformer-rolling █████··················· 57
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 140
navigation                 █████████████████████··· 125
spatial-reasoning          ██████████·············· 57
reconstruction             █████████··············· 51
pose                       ████···················· 26
VSLAM                      ███····················· 18
tracking                   ██······················ 14
depth                      ██······················ 14
VIO                        ██······················ 11
mapping                    █······················· 8
SfM                        █······················· 6
VO                         █······················· 4
occupancy                  █······················· 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 138
scene-graph                ███████████████········· 88
3DGS                       █████████··············· 49
sparse                     █████████··············· 49
pointmap                   ██████·················· 33
NeRF                       ██······················ 14
BEV                        ██······················ 14
voxel                      ██······················ 13
implicit-sdf               ██······················ 11
mesh                       █······················· 5
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 248
multi-modal                ██████████·············· 102
RGBD                       █████████··············· 97
LiDAR                      ██······················ 18
event                      █······················· 10
stereo                     █······················· 10
IMU                        █······················· 8
4D-radar                   ························ 5
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[VLASH: Real-Time VLAs via Future-State-Aware Asynchronous Inference](https://arxiv.org/abs/2512.01031)** — `VLA` · 2026-07-29
  - _首次提出 future-state-aware asynchronous inference paradigm for VLAs, enabling real-time closed-loop control without temporal misalignment — solves the long-standing 'prediction-execution desync' problem in VLA deployment (ontology §13: temporal grounding of action policies)._
- **[WCM: World-Cognition Model for Generalizable Human-Robot Interaction](https://arxiv.org/abs/2607.22999)** — `world-model-as-policy` · 2026-07-29
  - _首次將 human-in-the-loop teaching mode 深度整合至 world-model-as-policy 范式，實現可解釋、可中斷、可修正的自主任務執行與持續 co-teaching，解決了長期存在的 'black-box policy execution vs. human agency' 根本張力。_
- **[Action from Adjacent Set in Physical Space Outperforms the Best Prediction in World Models](https://arxiv.org/abs/2607.23602)** — `world-model-as-policy` · 2026-07-29
  - _首次揭示並形式化‘proposal overgeneration’這一世界模型規劃中的根本性失效機制（paradigm軸），並提出ASAR——一種不依賴更高精度預測、而透過鄰域密度重構動作序列的新規劃範式，實現feasibility與cost optimality的解耦。_
- **[Try Once, Then Optimal: De-Redundified Procedure Memory for Cross-Episode Exploration Amortization](https://arxiv.org/abs/2607.23702)** — `world-model-as-policy` · 2026-07-29
  - _首次提出‘procedure memory’作為可泛化、可檢索、可恢復的跨episode記憶機制，將探索行為從狀態導向轉為物體導向，並在 paradigm 軸上開創 'world-model-as-policy' 與 'procedure-conditioned policy' 的耦合新範式——此前所有 SLAM/VLA/world model 工作均無法在無重訓練前提下，從單次（可能失敗）交互中蒸餾出可重用、可容錯、可注入策略的程序性知識。_
- **[$N_0$-TWAM: Scaling Tactile-Native World-Action Model for Contact-Rich Manipulation](https://arxiv.org/abs/2607.23783)** — `world-model-as-policy` · 2026-07-29
  - _首創 tactile-native world-action model（新paradigm軸），實現視覺+觸覺+動作的聯合未來預測，解決了既有world-model-as-policy範式中觸覺信號長期被忽略、無法建模接觸事件動態演化的根本缺陷。_
- **[Memory for Attention: Language-Conditioned Re-Perception with a Vision--Language--Motion Map](https://arxiv.org/abs/2607.23797)** — `world-model-as-policy` · 2026-07-29
  - _首次將 persistent spatial memory (change-history/recency) into a formal resource-allocation theory for language-conditioned re-perception, deriving and verifying a Cauchy–Schwarz bound on perception gain (Var(√λ)) — establishing memory as a *quantifiable, task-aware attention scheduler*, not just a passive store; this introduces a new paradigm axis: 'world-model-as-policy' grounded in volatility-aware memory scheduling._
- **[LeapBot-WA: World-Anchor Action Models via Predictive Latent Alignments](https://arxiv.org/abs/2607.23969)** — `world-model-as-policy` · 2026-07-29
  - _首度將 JEPA 引入 Spatial AI 的 world model 軸，以 Predictive Semantic Alignment 取代 pixel-level video generation，實現「不生成視覺表徵即可建模物理動力學」這一此前不可行的能力，直接解 ontology §13 中『world-model-as-policy 是否必須耦合感知合成』的長期爭議。_
- **[FeelWorld: Visuo-Tactile World Model for Hierarchical Contact Prediction and Planning](https://arxiv.org/abs/2607.24267)** — `world-model-as-policy` · 2026-07-29
  - _首次將 tactile state (contact/slip) as一等公民納入 world model 的 latent dynamics，開闢 'visuo-tactile latent space' 軸，使 world model 從純視覺外推躍遷至可嚴格約束接觸力學的物理-grounded 預測——此前所有 VLA/world model 均無法顯式建模並 jointly rollout contact/slip latents under physical consistency._

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._