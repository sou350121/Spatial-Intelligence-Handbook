# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 857 papers · 2026-07-08 → 2026-08-06 · ⚡ 142 · 🔧 540 · 📖 175

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 60
learned                    █████████████████████··· 200
hybrid                     ███████████████········· 139
generative                 █████··················· 47
3R-SLAM-hybrid             █······················· 7
VLA                        ████████████████████████ 228
world-model-as-policy      ██████████·············· 98
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 |
|---|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 11 |
| learned | 37 | 39 | 38 | 55 | 31 |
| hybrid | 17 | 37 | 44 | 26 | 15 |
| generative | 8 | 13 | 11 | 7 | 8 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 |
| VLA | 37 | 50 | 50 | 46 | 45 |
| world-model-as-policy | 11 | 19 | 18 | 26 | 24 |
| **total** | **119** | **174** | **179** | **172** | **135** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 138
fixed-lag                  ························ 1
incremental                ████████················ 121
per-scene                  ████████████████████████ 374
feed-forward               █████··················· 74
temporal-transformer-rolling █████··················· 85
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 210
navigation                 ███████████████████····· 164
spatial-reasoning          █████████··············· 77
reconstruction             ████████················ 74
pose                       ███····················· 30
tracking                   ██······················ 21
VSLAM                      ██······················ 19
depth                      ██······················ 19
VIO                        █······················· 12
mapping                    █······················· 10
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 208
scene-graph                █████████████··········· 109
3DGS                       ████████················ 70
sparse                     ███████················· 57
pointmap                   ██████·················· 52
BEV                        ██······················ 21
NeRF                       ██······················ 17
voxel                      ██······················ 17
implicit-sdf               ██······················ 16
mesh                       █······················· 8
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 330
multi-modal                ██████████·············· 143
RGBD                       ██████████·············· 139
LiDAR                      ██······················ 24
event                      █······················· 15
stereo                     █······················· 13
IMU                        █······················· 9
4D-radar                   ························ 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[GEM-4D: Geometry-Enhanced Video World Models for Robot Manipulation](https://arxiv.org/abs/2605.22882)** — `world-model-as-policy` · 2026-08-06
  - _首次將4D correspondence supervision（時空稠密幾何對應）作為可蒸餾的幾何先驗注入視頻世界模型，使單流生成模型具備內生物理一致性建模能力，解決了video world model長期無法保障跨幀物理點軌跡連續性的核心缺陷（ontology §13「geometry-grounded generation」爭議）。_
- **[DriftWorld: Fast World Modeling through Drifting](https://arxiv.org/abs/2607.15065)** — `world-model-as-policy` · 2026-08-06
  - _首次將「drifting generative model」引入 world modeling，以單次前向傳播替代多步去噪，實現 action-conditioned feed-forward world rollouts —— 新增 paradigm 軸上的 'world-model-as-policy' 實現路徑，並解開 diffusion-based world models 在 real-time planning 中的 multistep sampling 瓶頸（ontology §13 中長期存在的 'inference latency vs. rollout fidelity' 權衡爭議）。_
- **[WCM: World-Cognition Model for Generalizable Human-Robot Interaction](https://arxiv.org/abs/2607.22999)** — `world-model-as-policy` · 2026-08-06
  - _首次將 human-in-the-loop teaching 與 chain-of-thought supervision 以異步、模塊化（SLAK）架構內建於 embodied agent runtime，實現可解釋、可干預、可持續教學的 world-model-as-policy 範式，解決長期存在的 robot opacity 與 teachability 缺失問題（ontology §13.2：'agent transparency vs. autonomy trade-off'）。_
- **[ChainVLA: Chaining Vision-Language-Action Queries through a Unified Execution State for Long-Horizon Manipulation](https://arxiv.org/abs/2608.02326)** — `VLA` · 2026-08-06
  - _首次提出可更新、跨查詢傳遞且分離建模的雙態執行狀態（Progress Context + Motion Tail），在 paradigm 軸上實現 'VLA' → 'VLA-with-state-chaining' 的範式躍遷，使 VLA 從無狀態重規劃轉為具時序一致性的長程動作鏈結，解決了長期存在的「跨步驟執行狀態斷裂」根本問題。_
- **[Quo Vadis, World Modeling?](https://arxiv.org/abs/2608.02713)** — `world-model-as-policy` · 2026-08-06
  - _首次提出‘Agent-Centric Interactive World Proxies’範式，將world modeling從物理狀態遷移（dynamics-only）升級為六類agent-usable信息遷移軸（execution/memory/skill等），解開了ontology §13中‘world model如何支持持續學習代理的非物理性決策閉環’這一長期爭議，並給出可量化的六維功能分類框架。_
- **[PACE: Adaptive Budget Allocation for Time-Efficient Embodied Planning](https://arxiv.org/abs/2608.03034)** — `VLA` · 2026-08-06
  - _首次提出並實現「推理-執行時序交織」範式（paradigm 軸），使 LLM-based planning 從串行（think-then-act）轉向並行化、時間感知的 interleaved think-act，解決了 embodied planning 中長期存在的推理延遲與執行窗口不匹配這一根本性瓶頸。_
- **[GraspMeanFlow: SE(3)-Equivariant MeanFlow for Few-Step 6-DoF Grasp Generation](https://arxiv.org/abs/2608.03295)** — `generative` · 2026-08-06
  - _首次實現 SE(3)-equivariant generative sampling in ≤2 steps while preserving exact equivariance — introduces 'MeanFlow' as a new generative paradigm that replaces iterative ODE integration with time-ordered exponential-based average-velocity transport, enabling real-time 6-DoF grasp synthesis without sacrificing geometric consistency._
- **[Continue or Replan? Bernoulli-Continuation Policy Learning for Adaptive Horizon Execution](https://arxiv.org/abs/2608.03483)** — `VLA` · 2026-08-06
  - _首次將執行視界建模為可學習的序列化 Bernoulli 停止過程（而非固定 chunk 或離散 horizon 分類），在 paradigm 軸上開創 'VLA-as-adaptive-horizon-policy' 新範式，使 VLA 從被動週期重規劃轉為主動、狀態依賴的即時續航決策，解決了長期存在的 'stale action execution at critical stages' 根本性瓶頸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._