# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 377 papers · 2026-07-08 → 2026-07-21 · ⚡ 56 · 🔧 249 · 📖 72

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 29
learned                    ████████████████████···· 86
hybrid                     ████████████████········ 69
generative                 ██████·················· 24
3R-SLAM-hybrid             █······················· 3
VLA                        ████████████████████████ 104
world-model-as-policy      ████████················ 35
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 |
|---|---:|---:|---:|
| geometric | 10 | 13 | 6 |
| learned | 37 | 39 | 10 |
| hybrid | 17 | 38 | 14 |
| generative | 9 | 14 | 1 |
| 3R-SLAM-hybrid | · | 3 | · |
| VLA | 38 | 52 | 14 |
| world-model-as-policy | 11 | 19 | 5 |
| **total** | **122** | **178** | **50** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 58
incremental                ████████················ 58
per-scene                  ████████████████████████ 168
feed-forward               █████··················· 35
temporal-transformer-rolling █████··················· 34
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 88
VLA                        ███████████████████████· 84
spatial-reasoning          ███████················· 27
reconstruction             ███████················· 24
pose                       █████··················· 20
VSLAM                      ████···················· 14
tracking                   ███····················· 10
depth                      ███····················· 10
VIO                        ██······················ 7
SfM                        █······················· 5
mapping                    █······················· 2
occupancy                  ························ 1
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 94
scene-graph                █████████████··········· 50
sparse                     ████████················ 33
3DGS                       ████████················ 32
pointmap                   ████···················· 16
NeRF                       ███····················· 11
BEV                        ██······················ 9
implicit-sdf               █······················· 5
voxel                      █······················· 5
mesh                       █······················· 3
HD-map                     █······················· 2
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 165
multi-modal                ████████················ 53
RGBD                       ███████················· 51
event                      █······················· 9
LiDAR                      █······················· 8
stereo                     █······················· 7
IMU                        ························ 3
4D-radar                   ························ 3
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Human-Inspired Neuro-Symbolic World Modeling and Logic Reasoning for Interpretable Safe UAV Landing Site Assessment](https://arxiv.org/abs/2510.22204)** — `world-model-as-policy` · 2026-07-21
  - _首次將 neuro-symbolic 架構耦合於 UAV landing site assessment 問題，實現「感知建模」與「符號安全推理」的嚴格分離軸（paradigm: hybrid → world-model-as-policy），並在 real-time edge deployment 中達成可驗證、可解釋、可形式化驗證的安全決策——此前所有 VLA 或 learned occupancy 方法均無法提供白箱邏輯追溯與人類可審計的約束違反溯源。_
- **[MindDrive: A Vision-Language-Action Model for Autonomous Driving via Online Reinforcement Learning](https://arxiv.org/abs/2512.13636)** — `VLA` · 2026-07-21
  - _首度將 VLA 范式從 imitation-based 遷移至 online RL 驅動的 linguistic decision space，以離散語言決策（而非連續動作）作為 RL 的 policy output 軸，解開了 autonomous driving 中 continuous-action RL 探索效率與因果可解釋性長期不可兼得的困境（ontology §13 爭議：'how to ground RL in semantically meaningful action abstractions?'）。_
- **[Generation Models Know Space: Unleashing Implicit 3D Priors for Scene Understanding](https://arxiv.org/abs/2603.19235)** — `generative` · 2026-07-21
  - _首次證實並系統性提取視頻生成模型中隱含的、未經顯式監督的3D結構與物理先驗，將其轉化為可即插即用的Latent World Simulator，開闢『generative-as-geometric-prior』新範式軸，解決長期存在的MLLM空間失明問題（ontology §13爭議：是否需顯式3D數據才能獲得可靠幾何推理能力）。_
- **[ABot-AgentOS: A General Robotic Agent OS with Lifelong Multi-modal Memory](https://arxiv.org/abs/2607.10350)** — `world-model-as-policy` · 2026-07-21
  - _首次提出「failure-driven self-evolution loop」機制，將記憶失敗診斷轉化為閘控式 runtime evo-assets 並跨評估分割（split）動態升級記憶結構，解決 lifelong memory consistency 與 ground-truth leakage 的根本性張力——此為 ontology §13 中 'temporal grounding of memory evolution' 的可量化、可部署解。_
- **[ABot-N1: Toward a General Visual Language Navigation Foundation Model](https://arxiv.org/abs/2607.10383)** — `VLA` · 2026-07-21
  - _首次提出以像素空間錨點（pixel goal）作為視覺語言導航中認知與控制解耦的通用接口，實現了從黑箱端到端策略到可解釋、可組合、跨任務共享中間表徵的範式轉移，解決了長期存在的坐標漂移、長尾語義泛化與透明性不可兼得的根本矛盾。_
- **[GigaWorld-Policy-0.5: A Faster and Stronger WAM Empowered by AutoResearch](https://arxiv.org/abs/2607.13960)** — `world-model-as-policy` · 2026-07-21
  - _首次實現 world-model-as-policy 范式下「訓練時建模視覺動力學、推理時僅輸出動作」的解耦架構，解決了 WAMs 因視頻生成導致無法實時閉環控制的根本瓶頸，開闢 action-only inference 軸。_
- **[Think at 5 Hz, Act at 20 Hz: Asynchronous Fast-Slow Vision-Language-Action Inference for Closed-Loop Driving](https://arxiv.org/abs/2607.15621)** — `VLA` · 2026-07-21
  - _首次實現 vision-language-action 的異步解耦範式：慢速語義理解（7B VLA backbone）與快速動作生成（lightweight expert）在時間軸上分離，並透過可重用的 KV cache 作為跨時刻共享的空間-語言聯合表徵，使 action 推理脫離 LLM 自迴歸延遲束縛，解決了 closed-loop driving 中 '語義理解速率 < 控制頻率' 的根本性時序不匹配問題。_
- **[AC-VLA: Robust Out-of-Distribution Action Execution via Compositional Learning](https://arxiv.org/abs/2607.15714)** — `VLA` · 2026-07-21
  - _首次將 compositional generalization 作為可訓練的 VLA 范式軸心，通過 LLM-driven 指令分解 + proprioceptive trajectory alignment 實現 sub-task-level supervision，使 VLA 從 end-to-end holistic policy 轉向可組合、可干預、語義對齊的 action grammar，解決了長期存在的 OOD recombination 失效問題（§13.2 爭議：'VLA lacks compositional abstraction'）。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._