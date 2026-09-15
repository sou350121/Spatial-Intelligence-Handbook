# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2120 papers · 2026-07-08 → 2026-09-14 · ⚡ 225 · 🔧 1034 · 📖 861

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 116
learned                    ██████████████████████·· 368
hybrid                     ███████████████········· 264
generative                 ███████················· 111
3R-SLAM-hybrid             █······················· 10
VLA                        ████████████████████████ 409
world-model-as-policy      ██████████·············· 172
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W30 | W31 | W32 | W33 | W35 | W36 | W37 | W38 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 15 | 11 | 13 | 1 | 14 | 16 | 12 | 12 |
| learned | 35 | 53 | 40 | 11 | 41 | 55 | 45 | 13 |
| hybrid | 43 | 25 | 23 | 8 | 35 | 51 | 23 | 2 |
| generative | 10 | 7 | 12 | 3 | 13 | 24 | 18 | 4 |
| 3R-SLAM-hybrid | 3 | · | 1 | 1 | 1 | 1 | · | · |
| VLA | 48 | 42 | 56 | 16 | 57 | 55 | 38 | 11 |
| world-model-as-policy | 17 | 26 | 29 | 7 | 26 | 19 | 12 | 9 |
| **total** | **171** | **164** | **174** | **47** | **187** | **221** | **148** | **51** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████·············· 226
fixed-lag                  ························ 6
incremental                █████████··············· 198
per-scene                  ████████████████████████ 559
feed-forward               ██████████·············· 229
temporal-transformer-rolling ████████················ 194
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 430
navigation                 ███████████████········· 272
spatial-reasoning          █████████··············· 163
reconstruction             █████████··············· 155
pose                       ████···················· 74
tracking                   ███····················· 45
depth                      ██······················ 35
VSLAM                      ██······················ 27
mapping                    █······················· 23
VIO                        █······················· 22
SfM                        █······················· 10
occupancy                  █······················· 9
VO                         ························ 6
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 384
scene-graph                ███████████············· 183
3DGS                       ███████················· 117
pointmap                   ███████················· 113
sparse                     ██████·················· 101
BEV                        ███····················· 41
voxel                      ██······················ 39
mesh                       ██······················ 37
NeRF                       ██······················ 26
implicit-sdf               █······················· 21
HD-map                     ························ 6
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 607
multi-modal                ████████████············ 314
RGBD                       ████████················ 202
LiDAR                      ██······················ 45
event                      █······················· 30
stereo                     █······················· 19
IMU                        █······················· 14
4D-radar                   ························ 12
sonar                      ························ 3
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Ego-Dynamics-Augmented World Model for Autonomous Driving with Zero-Shot Cross-Embodiment Adaptation](https://arxiv.org/abs/2607.13410)** — `world-model-as-policy` · 2026-09-14
  - _點名一條新軸：以物理先驗 ego-dynamics context（橫向動力學+神經輪胎力）條件化 BEV world model 的隱分佈，於資訊論上移除 transition entropy/先驗中的 ego-motion 項，從而實現 zero-shot 跨底盤/跨具身泛化——這是既有 BEV-WM 做不到的能力。_
- **[CLAP: Cross-Embodiment Video World Models are Zero-Shot Physical Simulators](https://arxiv.org/abs/2608.27406)** — `world-model-as-policy` · 2026-09-14
  - _把 action-conditioned 影片世界模型從「單一本體」推進到「跨本體」這條新方法軸：用末端執行器位姿＋語言＋latent action 統一異質動作空間，再以課程式（先 latent action 學物理先驗、後接地到 EEF 動作空間）預訓練，使世界模型能在未見過的本體上零樣本當物理模擬器——這是先前單一本體影片模型做不到的能力。_
- **[IMPLY: Physically Anchored Consistency for World-Model Rollouts](https://arxiv.org/abs/2609.12441)** — `world-model-as-policy` · 2026-09-14
  - _首度把 world-model rollout 的驗證軸從『自我一致性』換成『物理錨定一致性』：反演模擬器讀出每次 rollout 隱含的質量/摩擦並以校準推動作錨，量化揭露了自我一致性無法區分「自洽但錯認物件」與「真正追蹤物件」這一既有盲點（AUROC 0.70 vs 1.00，52%→73%），是新的評測方法軸。_
- **[Zero-shot World Models Are Developmentally Efficient Learners](https://arxiv.org/abs/2604.10333)** — `world-model-as-policy` · 2026-09-11
  - _開了一條新方法軸：用稀疏、時間因子化解耦外觀與動力學的預測器＋近似因果推斷的 zero-shot 估計，從單一兒童第一人稱數據學出可跨物理理解基準泛化的世界模型，給『數據高效且靈活』這一長期爭議一個可量化的解。_
- **[Continual Field-Adaptive Models (CFAMs) for Post-Deployment Physical AI](https://arxiv.org/abs/2609.04552)** — `VLA` · 2026-09-07
  - _提出部署後梯度無關的 on-device 持續學習軸（Capsule Field / Competence Capsules），讓物理 AI 能在不災難性遺忘下現場累積能力，此前 VLA 範式做不到。_
- **[AnyWorld: Factorized Egocentric World Models for Cross-Embodiment Generalization](https://arxiv.org/abs/2608.29242)** — `world-model-as-policy` · 2026-09-03
  - _將世界模型因子化為 action/camera/embodiment 三軸，實現跨具身、視角、場景的獨立重組，無需配對人類-機器人示範即可從單一人類影片生成多樣機器人 rollout，開闢了跨具身世界模型的新方法軸。_
- **[REFACTOR-VLA: Unsupervised Library Learning of Typed Motor Programs](https://arxiv.org/abs/2609.01215)** — `VLA` · 2026-09-03
  - _開 VLA 無監督技能庫學習軸：以世界模型 rollout 的行為等價核與 typed lambda 抽象，解決既有 VLA 長程任務缺乏可重用、可解釋組合抽象的問題。_
- **[Facet-0: A Robotic Foundation Model for Contact-Rich Precise Manipulation](https://arxiv.org/abs/2609.01596)** — `VLA` · 2026-09-03
  - _開了一條關節 action-wrench 生成式提案軸：以 flow matching 同時生成動作塊與其預期誘發的腕部力矩剖面，並用分布式 Action-Wrench Critic 對接觸後果估值——這是既有 VLA 無法做到的接觸感知新能力。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._