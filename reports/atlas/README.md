# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 1595 papers · 2026-07-08 → 2026-08-26 · ⚡ 186 · 🔧 655 · 📖 754

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 70
learned                    ████████████████████···· 235
hybrid                     ███████████████········· 177
generative                 █████··················· 58
3R-SLAM-hybrid             █······················· 9
VLA                        ████████████████████████ 286
world-model-as-policy      ██████████·············· 122
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 | W33 | W35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 13 | 1 | 7 |
| learned | 36 | 39 | 37 | 54 | 40 | 11 | 18 |
| hybrid | 17 | 37 | 44 | 25 | 23 | 8 | 23 |
| generative | 7 | 13 | 10 | 7 | 12 | 3 | 6 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 | 1 | 1 |
| VLA | 37 | 49 | 50 | 43 | 58 | 17 | 32 |
| world-model-as-policy | 11 | 18 | 17 | 26 | 30 | 7 | 13 |
| **total** | **117** | **172** | **176** | **167** | **177** | **48** | **100** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 158
fixed-lag                  ························ 1
incremental                ███████················· 143
per-scene                  ████████████████████████ 466
feed-forward               █████··················· 92
temporal-transformer-rolling ██████·················· 115
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 268
navigation                 ██████████████████······ 198
spatial-reasoning          █████████··············· 103
reconstruction             ████████················ 92
pose                       ███····················· 38
tracking                   ██······················ 24
depth                      ██······················ 23
VSLAM                      ██······················ 21
VIO                        █······················· 14
mapping                    █······················· 11
SfM                        █······················· 8
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 248
scene-graph                ██████████████·········· 146
3DGS                       ████████················ 87
pointmap                   ██████·················· 67
sparse                     ██████·················· 64
BEV                        ███····················· 27
voxel                      ██······················ 21
NeRF                       ██······················ 20
implicit-sdf               ██······················ 17
mesh                       █······················· 14
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 412
multi-modal                ██████████·············· 180
RGBD                       █████████··············· 161
LiDAR                      ██······················ 29
event                      █······················· 18
stereo                     █······················· 15
IMU                        █······················· 9
4D-radar                   ························ 8
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Towards Zero-Shot Task Transfer with Neurosymbolic World Models](https://arxiv.org/abs/2608.17959)** — `world-model-as-policy` · 2026-08-26
  - _首次將 neurosymbolic 結構強制注入 world model 的 latent 拓撲：reward 預測被約束於可解釋、可重組的 symbolic 子空間，實現 reward 函數更換下的 zero-shot task transfer——此前所有 VLA/world-model 論文均無法在不 finetune 或重規劃的前提下切換 reward semantics。_
- **[Selective Cross-View Consistency for World Action Models: Held-Out Viewpoint Robustness Without Test-Time Camera Information](https://arxiv.org/abs/2608.21402)** — `world-model-as-policy` · 2026-08-26
  - _首次提出並形式化證明 cross-view consistency 對 view-covariant 模塊的系統性 shrinkage 效應（1/(1+4λ) 定量坍縮律），並基於此導出 selective 約束範式——在不引入任何 camera 先驗或額外模組下，實現 world model 對未見 viewpoint 的泛化能力，開闢了 WAMs 的 robustness 軸（paradigm: world-model-as-policy）中「無需測試時幾何資訊的視角不變學習」這一新方法類別。_
- **[RiskWorld: Object-Centric Latent World Modeling for Autonomous Driving Risk Identification](https://arxiv.org/abs/2608.21414)** — `world-model-as-policy` · 2026-08-26
  - _首度將 world-model-as-policy 范式具體實作於 object-centric latent dynamics 上，實現「風險源定位」這一長期未被建模的 spatial reasoning 子問題：既有方法只能輸出場景級風險或間接推斷，RiskWorld 首創以 RSSM-style rollout 直接建模 ego–object 關係演化並解碼為可解釋、可定位的 object-level 飽和風險分數，填補 ontology §13 中 'risk attribution' 的因果空間推理缺口。_
- **[Inferring Action from Future Latent State for Robotic Manipulation](https://arxiv.org/abs/2608.22067)** — `world-model-as-policy` · 2026-08-26
  - _首次提出「action-from-future-latent-state」範式，將世界模型的輸出從稠密視覺序列（video generation）解耦為緊湊、動作相關的物理結果潛在狀態（future latent state），從而實現 world-model-as-policy 的新實作軸：不再以生成視覺過渡為中介，而是直接建模 action → physical-outcome 映射，解決 ontology §13 中「world model 與 policy 的語義鴻溝」這一長期爭議。_
- **[Meta-Ctrl: Guaranteed Plan Generation by Decoupling Syntactic and Semantic Constraints](https://arxiv.org/abs/2608.22149)** — `VLA` · 2026-08-26
  - _首次實現LLM生成計劃的**形式化可證正確性保障**（syntactic + semantic constraints jointly enforced via meta-token factorization），在不犧牲語言模型常識推理能力前提下，將約束解碼記憶複雜度從10⁷TB壓縮至2GB，解決了長期存在的‘LLM規劃不可靠’與‘符號規劃無常識’二元困境。_
- **[BehaviorWorldGen: Closing the Loop between Action Models and World Simulators via Controllable Behavior-Aware Structured World Generation](https://arxiv.org/abs/2608.22187)** — `world-model-as-policy` · 2026-08-26
  - _首次實現 action model 與 world simulator 的雙向閉環協同演化，通過 BehaviorFlow 將 meta-action 條件注入 traffic-flow 建模，在 structured trajectory 表示上同時保證 ego 可控性與 multi-agent 行為一致性，解決了長期存在的 'simulator realism–interaction fidelity trade-off'（ontology §13 爭議），開闢 'world-model-as-policy-coevolution' 新範式。_
- **[DreamMimic: Learning Visuomotor Whole-Body Loco-Manipulation via World Model](https://arxiv.org/abs/2608.22278)** — `world-model-as-policy` · 2026-08-26
  - _首次將 world-model-as-policy 範式（非用於規劃，而是作為可蒸餾的 predictive latent dynamics 機制）用於解決視覺驅動人形機器人全身 loco-manipulation 的長期漂移與接觸建模難題，實現了 'vision-based policy distillation via world model' 這一新方法軸：世界模型不再輸出動作或規劃軌跡，而輸出 action-conditioned multi-step privileged supervision（含 contact/object/reward latent heads），使學生策略能在無真值狀態下學習物理一致的長時序交互動力學。_
- **[Beyond Instance Slots: Semantically Rich World Models for Physical Interaction Planning](https://arxiv.org/abs/2608.22294)** — `world-model-as-policy` · 2026-08-26
  - _首次提出以功能角色（gripper/target/goal/relation/phase）為本體錨點的任務條件化世界模型範式，將世界建模從「預測觀測/潛在特徵」轉向「驗證動作是否維持語義關係與階段約束」，解決了長期存在的 planning-oriented world model 缺乏可解釋、可干預、關係保持型狀態抽象的根本缺陷（ontology §13 爭議：'how to ground action feasibility in relational invariants'）。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._