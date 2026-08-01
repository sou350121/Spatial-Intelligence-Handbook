# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 716 papers · 2026-07-08 → 2026-07-31 · ⚡ 112 · 🔧 454 · 📖 150

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 49
learned                    ██████████████████████·· 169
hybrid                     ████████████████········ 125
generative                 █████··················· 39
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 186
world-model-as-policy      ██████████·············· 78
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 |
|---|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 |
| learned | 37 | 39 | 38 | 55 |
| hybrid | 17 | 37 | 45 | 26 |
| generative | 8 | 13 | 11 | 7 |
| 3R-SLAM-hybrid | · | 3 | 3 | · |
| VLA | 37 | 50 | 52 | 47 |
| world-model-as-policy | 11 | 19 | 18 | 30 |
| **total** | **119** | **174** | **182** | **177** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 115
incremental                ████████················ 102
per-scene                  ████████████████████████ 323
feed-forward               ████···················· 57
temporal-transformer-rolling █████··················· 68
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 164
navigation                 █████████████████████··· 144
spatial-reasoning          █████████··············· 63
reconstruction             █████████··············· 62
pose                       ████···················· 27
tracking                   ███····················· 18
VSLAM                      ███····················· 18
depth                      ██······················ 17
VIO                        ██······················ 11
mapping                    █······················· 9
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 165
scene-graph                ██████████████·········· 99
3DGS                       ████████················ 57
sparse                     ████████················ 53
pointmap                   ██████·················· 38
BEV                        ██······················ 16
NeRF                       ██······················ 14
implicit-sdf               ██······················ 14
voxel                      ██······················ 14
mesh                       █······················· 6
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 283
multi-modal                ██████████·············· 118
RGBD                       █████████··············· 112
LiDAR                      ██······················ 21
stereo                     █······················· 12
event                      █······················· 11
IMU                        █······················· 9
4D-radar                   █······················· 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Temporal-Distance JEPA: Plan-Aware Representation Learning for Latent World Model Predictive Control](https://arxiv.org/abs/2607.25337)** — `world-model-as-policy` · 2026-07-31
  - _首次將JEPA範式從被動表徵學習升級為主動時序距離挖掘，引入可從無獎勵軌跡中端到端學習有向時間成本（而非依賴嵌入空間的副產物歐氏距離），解決了latent world model中長期存在的‘規劃成本與表徵學習目標錯配’這一ontology §13核心爭議。_
- **[$\pi\mathbf{R}^2$: Reactive Real-time Flow Policies](https://arxiv.org/abs/2607.26055)** — `world-model-as-policy` · 2026-07-31
  - _首次實現「在保留大型多模態生成式策略 backbone 的前提下，達成毫秒級感官反饋驅動的動態重規劃」——新在 paradigm 軸：將 world-model-as-policy 從固定 chunking 的開環生成範式，升級為具 latency-adaptive inpainting conditioning 的閉環流式策略範式，解決了生成式操作策略長期無法實時響應 proprioceptive 突變的根本性瓶頸。_
- **[Learning Implicit Causal World Models from Multi-Agent Demonstrations](https://arxiv.org/abs/2607.26336)** — `world-model-as-policy` · 2026-07-31
  - _首次在 Spatial AI 中提出隱式因果世界模型範式（paradigm 軸），透過策略方差誘導 sequential backdoor 條件，從多智能體示範中無需先驗因果圖地解耦物理動力學與戰略意圖，解決長期存在的因果混淆導致分布外泛化失敗這一 ontology §13 核心爭議。_
- **[Explicit Kinematic Guidance from Analytic Concepts for Vision-Language-Action Models](https://arxiv.org/abs/2607.26513)** — `VLA` · 2026-07-31
  - _首次將可執行的、基於解析性3D運動學建模的'Analytic Concepts'嵌入VLA範式，使VLA具備顯式、程序化、動態更新的物體級運動學約束能力——此前VLA僅能隱式泛化空間行為，無法在推理時維持物理一致的關節參數與結構不變量。_
- **[ContactFlow: A video action conditioning that transfers across embodiments](https://arxiv.org/abs/2607.26579)** — `world-model-as-policy` · 2026-07-31
  - _首度提出 embodiment-agnostic action representation（Contact Flow）作為 world model 的 conditioning 軸，將 manipulation 建模為 3D 接觸點軌跡，從根本上解耦動作語義與具身形態，使 video-based world model 首次能跨 human/robot embodiment 泛化物理互動預測——此前所有 VLA/world model 均綁定特定執行器（gripper/arm kinematics），此為 paradigm 軸的範式轉移：從 VLA 或 world-model-as-policy 升級為 world-model-as-contact-dynamics-policy。_
- **[Genie Sim PanoWorld: An Infinite Indoor 3D World Generation Pipeline via Panoramic Scene Modeling and Simulation](https://arxiv.org/abs/2607.26646)** — `world-model-as-policy` · 2026-07-31
  - _首次實現從單張360°全景圖端到端生成具SE(3)軌跡可控性、可自由導航的高保真3D高斯場（3DGS），且無需每場景優化或多視圖輸入——解決了長期存在的「單圖→可導航世界模型」範式斷裂，開闢了panoramic-world-model-as-policy新軸。_
- **[ActSWM: Action-Sensitive World Models for Long-Horizon Planning in Open-World Games](https://arxiv.org/abs/2607.26712)** — `world-model-as-policy` · 2026-07-31
  - _首次將 latent world model 的 rollout 穩定性與行動可辨識性解耦，提出 'transition-separation principle' 並以 action-sensitive constraint 強制保持不同動作序列在潛在空間中的軌跡可分離性——解決了長期存在的 Context Collapse 問題（ontology §13 中 'world-model-as-policy 軸上的因果不可逆性與行動反事實保真度' 爭議），使 world-model-based action recovery 從 offline video 成為可量化的實用能力。_
- **[CheckVLA: Execution-Time Verification with Action-Conditioned World Model for Long-Horizon Mobile Manipulation](https://arxiv.org/abs/2607.26789)** — `world-model-as-policy` · 2026-07-31
  - _首次將 conformal risk calibration 與 action-conditioned world model 結合，實現 episode-level 可控置信度的執行時干預決策——解決了 VLA 長程操作中「開環承諾與在線偏差不可調和」這一 ontology §13 中長期懸而未決的範式衝突（即：如何在不重規劃前提下，對已發出但尚未執行完的 action chunk 做語義一致性的動態驗證）。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._