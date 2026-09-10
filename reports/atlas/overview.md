# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2033 papers · 2026-07-08 → 2026-09-10 · ⚡ 222 · 🔧 953 · 📖 858

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 98
learned                    █████████████████████··· 346
hybrid                     ████████████████········ 255
generative                 ██████·················· 97
3R-SLAM-hybrid             █······················· 10
VLA                        ████████████████████████ 392
world-model-as-policy      ██████████·············· 164
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W29 | W30 | W31 | W32 | W33 | W35 | W36 | W37 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 15 | 11 | 13 | 1 | 14 | 16 | 6 |
| learned | 39 | 35 | 54 | 40 | 11 | 41 | 55 | 35 |
| hybrid | 37 | 44 | 25 | 23 | 8 | 36 | 52 | 13 |
| generative | 13 | 10 | 7 | 12 | 3 | 13 | 25 | 7 |
| 3R-SLAM-hybrid | 3 | 3 | · | 1 | 1 | 1 | 1 | · |
| VLA | 49 | 48 | 42 | 56 | 17 | 57 | 56 | 30 |
| world-model-as-policy | 17 | 17 | 26 | 29 | 7 | 27 | 20 | 10 |
| **total** | **171** | **172** | **165** | **174** | **48** | **189** | **225** | **101** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 214
fixed-lag                  ························ 4
incremental                ████████················ 191
per-scene                  ████████████████████████ 545
feed-forward               █████████··············· 200
temporal-transformer-rolling ████████················ 180
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 402
navigation                 ███████████████········· 259
spatial-reasoning          █████████··············· 153
reconstruction             ████████················ 142
pose                       ████···················· 66
tracking                   ██······················ 38
depth                      ██······················ 33
VSLAM                      █······················· 25
mapping                    █······················· 21
VIO                        █······················· 20
SfM                        █······················· 10
occupancy                  █······················· 9
VO                         ························ 6
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 364
scene-graph                ████████████············ 180
3DGS                       ███████················· 111
pointmap                   ███████················· 101
sparse                     ██████·················· 94
BEV                        ███····················· 39
voxel                      ██······················ 36
mesh                       ██······················ 32
NeRF                       ██······················ 27
implicit-sdf               █······················· 21
HD-map                     ························ 6
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 578
multi-modal                ████████████············ 294
RGBD                       ████████················ 199
LiDAR                      ██······················ 39
event                      █······················· 29
stereo                     █······················· 19
IMU                        █······················· 13
4D-radar                   ························ 10
sonar                      ························ 2
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Zero-shot World Models Are Developmentally Efficient Learners](https://arxiv.org/abs/2604.10333)** — `world-model-as-policy` · 2026-09-10
  - _提出 Zero-shot World Model 這條新範式軸：以時間因子化預測器解耦外觀/動力學、並用近似因果推論做零樣本估計，讓世界模型能從單一兒童的第一人稱資料學會多項物理理解能力，是既有世界模型做不到的新能力。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._