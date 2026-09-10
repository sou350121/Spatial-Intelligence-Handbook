# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2033 papers · 2026-07-08 → 2026-09-10 · ⚡ 221 · 🔧 926 · 📖 886

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 97
learned                    █████████████████████··· 332
hybrid                     ████████████████········ 251
generative                 ██████·················· 96
3R-SLAM-hybrid             █······················· 10
VLA                        ████████████████████████ 381
world-model-as-policy      ██████████·············· 156
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W29 | W30 | W31 | W32 | W33 | W35 | W36 | W37 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 15 | 11 | 13 | 1 | 14 | 16 | 5 |
| learned | 39 | 35 | 54 | 40 | 11 | 41 | 56 | 20 |
| hybrid | 37 | 44 | 25 | 23 | 8 | 36 | 52 | 9 |
| generative | 13 | 10 | 7 | 12 | 3 | 13 | 25 | 6 |
| 3R-SLAM-hybrid | 3 | 3 | · | 1 | 1 | 1 | 1 | · |
| VLA | 49 | 48 | 42 | 56 | 17 | 57 | 56 | 19 |
| world-model-as-policy | 17 | 17 | 26 | 29 | 7 | 27 | 20 | 2 |
| **total** | **171** | **172** | **165** | **174** | **48** | **189** | **226** | **61** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 208
fixed-lag                  ························ 3
incremental                ████████················ 188
per-scene                  ████████████████████████ 542
feed-forward               ████████················ 187
temporal-transformer-rolling ████████················ 173
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 383
navigation                 ████████████████········ 254
spatial-reasoning          █████████··············· 149
reconstruction             █████████··············· 137
pose                       ████···················· 65
tracking                   ██······················ 37
depth                      ██······················ 33
VSLAM                      ██······················ 25
mapping                    █······················· 20
VIO                        █······················· 20
SfM                        █······················· 10
occupancy                  █······················· 9
VO                         ························ 6
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 351
scene-graph                ████████████············ 180
3DGS                       ████████················ 111
pointmap                   ███████················· 101
sparse                     ██████·················· 92
BEV                        ███····················· 38
voxel                      ██······················ 35
mesh                       ██······················ 28
NeRF                       ██······················ 27
implicit-sdf               █······················· 20
HD-map                     ························ 5
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 561
multi-modal                ████████████············ 282
RGBD                       ████████················ 196
LiDAR                      ██······················ 39
event                      █······················· 29
stereo                     █······················· 19
IMU                        █······················· 13
4D-radar                   ························ 10
sonar                      ························ 2
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Continual Field-Adaptive Models (CFAMs) for Post-Deployment Physical AI](https://arxiv.org/abs/2609.04552)** — `VLA` · 2026-09-07
  - _提出部署後梯度無關的 on-device 持續學習軸（Capsule Field / Competence Capsules），讓物理 AI 能在不災難性遺忘下現場累積能力，此前 VLA 範式做不到。_
- **[AnyWorld: Factorized Egocentric World Models for Cross-Embodiment Generalization](https://arxiv.org/abs/2608.29242)** — `world-model-as-policy` · 2026-09-03
  - _將世界模型因子化為 action/camera/embodiment 三軸，實現跨具身、視角、場景的獨立重組，無需配對人類-機器人示範即可從單一人類影片生成多樣機器人 rollout，開闢了跨具身世界模型的新方法軸。_
- **[REFACTOR-VLA: Unsupervised Library Learning of Typed Motor Programs](https://arxiv.org/abs/2609.01215)** — `VLA` · 2026-09-03
  - _開 VLA 無監督技能庫學習軸：以世界模型 rollout 的行為等價核與 typed lambda 抽象，解決既有 VLA 長程任務缺乏可重用、可解釋組合抽象的問題。_
- **[Facet-0: A Robotic Foundation Model for Contact-Rich Precise Manipulation](https://arxiv.org/abs/2609.01596)** — `VLA` · 2026-09-03
  - _開了一條關節 action-wrench 生成式提案軸：以 flow matching 同時生成動作塊與其預期誘發的腕部力矩剖面，並用分布式 Action-Wrench Critic 對接觸後果估值——這是既有 VLA 無法做到的接觸感知新能力。_
- **[Hydra: A Navigation World Action Model with Discrete Latent Planning and Continuous Flow-Matching Execution](https://arxiv.org/abs/2608.28995)** — `world-model-as-policy` · 2026-09-01
  - _將 planner（sampler+evaluator）搬進 world model 的統一離散潛在流形，用 VQ 詞彙與 Kinematic-Perceptual Cost 直接在離散空間排序、免 decode 到像素，解了 world-model 實時控制必須回解高維像素的既有瓶頸——新軸為 Discrete Latent Planning + flow-matching 執行。_
- **[Tactile-WAM: Touch-Aware World Action Model with Tactile Asymmetric Attention](https://arxiv.org/abs/2606.26663)** — `world-model-as-policy` · 2026-08-28
  - _首度提出 tactile-asymmetric attention 機制，解決 tactile pollution 問題——即在世界模型中協同建模視覺與觸覺時，防止稀疏/高噪觸覺信號破壞視覺動力學學習，此為 ontology §13 中 'multi-modal world modeling under signal asymmetry' 的長期未解爭議提供可量化解。_
- **[BehaviorWorldGen: Closing the Loop between Action Models and World Simulators via Controllable Behavior-Aware Structured World Generation](https://arxiv.org/abs/2608.22187)** — `world-model-as-policy` · 2026-08-28
  - _首次實現 action model 與 world simulator 的閉環協同演化，通過 BehaviorFlow 引入可控、可解釋的 meta-action-conditioned 多智能體交通流建模軸，解決了長期存在的「生成交互不真實 + 分布偏斜」這一 ontology §13 中 spatial-reasoning × VLA × world-model-as-policy 的核心耦合失效問題。_
- **[Beyond Instance Slots: Semantically Rich World Models for Physical Interaction Planning](https://arxiv.org/abs/2608.22294)** — `world-model-as-policy` · 2026-08-28
  - _首次將世界模型的內部狀態顯式結構化為五個可解釋、任務通用的語義角色（gripper/target/goal/relation/phase），並使動力學預測與關係保持、謂詞建立、階段遷移等物理交互本質約束耦合，實現了從‘觀測預測’到‘約束導向的規劃可行性驗證’的範式轉移。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._