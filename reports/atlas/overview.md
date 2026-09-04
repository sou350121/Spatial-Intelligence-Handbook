# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2026 papers · 2026-07-08 → 2026-09-04 · ⚡ 211 · 🔧 706 · 📖 1109

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 76
learned                    ████████████████████···· 257
hybrid                     ███████████████········· 190
generative                 █████··················· 65
3R-SLAM-hybrid             █······················· 9
VLA                        ████████████████████████ 309
world-model-as-policy      ██████████·············· 134
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 | W33 | W35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 11 | 13 | 1 | 14 |
| learned | 36 | 39 | 35 | 54 | 40 | 11 | 42 |
| hybrid | 17 | 37 | 44 | 25 | 23 | 8 | 36 |
| generative | 7 | 13 | 10 | 7 | 12 | 3 | 13 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 | 1 | 1 |
| VLA | 37 | 49 | 49 | 42 | 57 | 17 | 58 |
| world-model-as-policy | 11 | 17 | 17 | 26 | 29 | 7 | 27 |
| **total** | **117** | **171** | **173** | **165** | **175** | **48** | **191** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 180
fixed-lag                  ························ 1
incremental                ███████················· 152
per-scene                  ████████████████████████ 496
feed-forward               █████··················· 98
temporal-transformer-rolling ██████·················· 131
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 295
navigation                 ██████████████████······ 216
spatial-reasoning          █████████··············· 110
reconstruction             ████████················ 96
pose                       ████···················· 44
tracking                   ██······················ 26
depth                      ██······················ 23
VSLAM                      ██······················ 22
VIO                        █······················· 18
mapping                    █······················· 11
SfM                        █······················· 8
VO                         ························ 6
occupancy                  ························ 4
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 273
scene-graph                ██████████████·········· 157
3DGS                       ████████················ 92
sparse                     ██████·················· 73
pointmap                   ██████·················· 72
BEV                        ███····················· 29
NeRF                       ██······················ 24
voxel                      ██······················ 22
implicit-sdf               ██······················ 20
mesh                       █······················· 15
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 445
multi-modal                ███████████············· 195
RGBD                       █████████··············· 171
LiDAR                      ██······················ 34
event                      █······················· 24
stereo                     █······················· 15
IMU                        █······················· 11
4D-radar                   ························ 9
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Tactile-WAM: Touch-Aware World Action Model with Tactile Asymmetric Attention](https://arxiv.org/abs/2606.26663)** — `world-model-as-policy` · 2026-08-28
  - _首度提出 tactile-asymmetric attention 機制，解決 tactile pollution 問題——即在世界模型中協同建模視覺與觸覺時，防止稀疏/高噪觸覺信號破壞視覺動力學學習，此為 ontology §13 中 'multi-modal world modeling under signal asymmetry' 的長期未解爭議提供可量化解。_
- **[BehaviorWorldGen: Closing the Loop between Action Models and World Simulators via Controllable Behavior-Aware Structured World Generation](https://arxiv.org/abs/2608.22187)** — `world-model-as-policy` · 2026-08-28
  - _首次實現 action model 與 world simulator 的閉環協同演化，通過 BehaviorFlow 引入可控、可解釋的 meta-action-conditioned 多智能體交通流建模軸，解決了長期存在的「生成交互不真實 + 分布偏斜」這一 ontology §13 中 spatial-reasoning × VLA × world-model-as-policy 的核心耦合失效問題。_
- **[Beyond Instance Slots: Semantically Rich World Models for Physical Interaction Planning](https://arxiv.org/abs/2608.22294)** — `world-model-as-policy` · 2026-08-28
  - _首次將世界模型的內部狀態顯式結構化為五個可解釋、任務通用的語義角色（gripper/target/goal/relation/phase），並使動力學預測與關係保持、謂詞建立、階段遷移等物理交互本質約束耦合，實現了從‘觀測預測’到‘約束導向的規劃可行性驗證’的範式轉移。_
- **[DreamLedger: Where to Refuse World-Model Imagination Using Execution-Settled Credit](https://arxiv.org/abs/2608.23863)** — `world-model-as-policy` · 2026-08-28
  - _首次將世界模型的可靠性建模為可持久化、執行驅動的信用 ledger（非瞬時置信度），在 paradigm 軸上開創 'world-model-as-policy' 的信用門控新範式，解決 ontology §13 中長期懸而未決的『如何讓世界模型對自身幻覺具備可審計、可累積、條件索引的拒絕能力』問題。_
- **[NVIDIA Cosmos-H-Dreams: Real-Time Generative Physics Simulation for Surgical Robotics](https://arxiv.org/abs/2608.24199)** — `world-model-as-policy` · 2026-08-28
  - _首次實現控制器無關（controller-agnostic）、實時流式（>150 FPS）、動作條件化、具物理一致性的生成式外科手術世界模型，將 world-model-as-policy 範式從離散決策場景擴展至連續高頻閉環機器人控制軸，解決了生成模擬長期無法支持 real-time embodied interaction 的核心瓶頸。_
- **[4DStreamCtrl: Interactive Video Generation with Online 4D Control](https://arxiv.org/abs/2608.25479)** — `generative` · 2026-08-28
  - _首次實現在線（streaming）、因果（causal）、4D-consistent（3D geometry + time）視頻生成中，對相機與物體運動的聯合、幾何一致、單次前向傳播控制——此前所有方法均割裂處理（camera-only / 2D-trajectory / offline-3D），此工作將 motion control 軸從離線幾何約束或2D像素軌跡，推進至可實時流式生成的4D世界狀態操作。_
- **[LM-X: Explainable Action Modeling with Progress, Event, and Uncertainty Prediction for Generalist Robot Manipulation](https://arxiv.org/abs/2608.25757)** — `VLA` · 2026-08-28
  - _首度在VLA範式中將task progress（RTG）、semantic event boundary（ETG）與heteroscedastic action reliability（variance-propagated flow）三者作為** jointly supervised、online-conditioning、解耦的控制狀態信號**，使解釋性內建於動作生成流，突破VLA長期「action-as-black-box-output」的範式限制，實現可干預、可診斷、可重規劃的空間操作控制。_
- **[WALL-SS: Scaling Long-horizon World Models via Next-Scale Autoregression](https://arxiv.org/abs/2608.26239)** — `world-model-as-policy` · 2026-08-28
  - _首次提出 scale-wise autoregressive scaling（尺度階層式自迴歸）範式，實現長時程世界模型中因果狀態的可重用流式擴展與粗到精生成耦合，解決了既有 world-model-as-policy 范式在 >10s horizon 下因果崩潰與記憶不可擴展的根本限制。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._