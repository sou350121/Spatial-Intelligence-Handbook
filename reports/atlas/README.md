# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2845 papers · 2026-07-08 → 2026-10-02 · ⚡ 249 · 🔧 1617 · 📖 979

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 176
learned                    ██████████████████······ 513
hybrid                     ██████████████·········· 384
generative                 ██████·················· 157
3R-SLAM-hybrid             ························ 11
VLA                        ████████████████████████ 670
world-model-as-policy      █████████··············· 260
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W32 | W33 | W35 | W36 | W37 | W38 | W39 | W40 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 1 | 14 | 16 | 12 | 31 | 28 | 13 |
| learned | 40 | 11 | 41 | 55 | 45 | 57 | 50 | 51 |
| hybrid | 23 | 8 | 35 | 51 | 22 | 41 | 44 | 38 |
| generative | 12 | 3 | 12 | 24 | 18 | 20 | 18 | 13 |
| 3R-SLAM-hybrid | 1 | 1 | 1 | 1 | · | · | · | 1 |
| VLA | 56 | 16 | 57 | 55 | 37 | 83 | 95 | 96 |
| world-model-as-policy | 29 | 7 | 26 | 19 | 12 | 31 | 38 | 28 |
| **total** | **174** | **47** | **186** | **221** | **146** | **263** | **273** | **240** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 341
fixed-lag                  █······················· 14
incremental                ███████████············· 284
per-scene                  ████████████████████████ 617
feed-forward               ██████████████████······ 475
temporal-transformer-rolling ████████████············ 316
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 775
navigation                 █████████████··········· 405
spatial-reasoning          ███████················· 218
reconstruction             ██████·················· 186
pose                       ████···················· 115
tracking                   ██······················ 63
mapping                    █······················· 47
VSLAM                      █······················· 42
depth                      █······················· 38
VIO                        █······················· 37
occupancy                  ························ 14
SfM                        ························ 11
VO                         ························ 7
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 575
scene-graph                ██████████·············· 240
pointmap                   ███████················· 166
3DGS                       ██████·················· 144
sparse                     ██████·················· 135
BEV                        ███····················· 65
mesh                       ███····················· 63
voxel                      ██······················ 43
implicit-sdf               █······················· 30
NeRF                       █······················· 29
HD-map                     ························ 9
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 846
multi-modal                ████████████████········ 571
RGBD                       ████████················ 271
LiDAR                      ██······················ 66
event                      █······················· 34
stereo                     █······················· 24
IMU                        █······················· 20
4D-radar                   █······················· 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[World Motion Models: Flexible Sequence Modeling of SE(3) Trajectories](https://arxiv.org/abs/2610.01742)** — `world-model-as-policy` · 2026-10-02
  - _以稀疏 SE(3) 軌跡作統一 4D 表徵、用 per-token noise flow-matching 支援任意 mask 條件化，開了一條「軌跡序列生成即多任務」的新軸：同一網路把未來預測、motion infilling、MPC、IK、cross-embodiment retargeting、policy learning 全化約為不同遮罩，是既有生成式 4D 模型做不到的統一性。_
- **[RoboCoach: World Models as Active Coaches for Compositional Robot Skills](https://arxiv.org/abs/2609.39685)** — `world-model-as-policy` · 2026-10-01
  - _把 world model 從 policy/規劃器改用作「主動教學者」（Route-Imagine-Diagnose-Improve）：以想像失敗定位首個未完成子任務，反過來決定要採集哪個子技能的示教與更新哪個 expert adapter，解了 compositional 長程操作中無法定位該補哪段監督的 credit-assignment／資料選擇問題（ρ=0.840 想像-實機一致，150 條示教 13.3%→75.0%），開出 world-model-as-teacher 這條新方法軸。_
- **[HelixWorld: A Real-time Interactive Audio-Visual World Model](https://arxiv.org/abs/2609.38123)** — `generative` · 2026-09-30
  - _首次讓互動式世界模型長出『相機對齊的空間立體聲』——開闢音視覺共演（multisensory world model）這條此前不存在的模態軸，並用線上軌跡蒸餾把 6-DoF 音視覺聯合 rollout 壓到 24FPS 串流。_
- **[Causeway: Restoring Task Accessibility for Instruction Switching in VLA Policies](https://arxiv.org/abs/2609.30913)** — `VLA` · 2026-09-28
  - _首開『訓練-free 推理期表徵干預』這條新軸：對凍結的 VLA 解碼計算反向傳播、在 action-stream 表徵內做 state-directed write，讓策略自身解出回歸動作，解決了 VLA 在任務切換後無法從前一任務產生的狀態（task island）重新進入目標任務這一既有做不到的能力。_
- **[Latent evolving World Action Model](https://arxiv.org/abs/2609.27455)** — `world-model-as-policy` · 2026-09-24
  - _把 World Action Model 從「必須依賴大型 video diffusion backbone + VAE latent」的範式上拆下來，改用 JEPA 預測式 embedding 空間同時做動作生成與環境演化預測（新方法軸：representation-for-action 的可控比較 + 免生成式主幹的 latent world model），並以 DemoDPO 在不需環境互動/人工重啟下實現 offline 偏好式策略改進。_
- **[Feeling Terrain Before Crossing: World Models for Off-Road Navigation](https://arxiv.org/abs/2609.19863)** — `world-model-as-policy` · 2026-09-18
  - _首個以本體感知（proprioception）為條件的導航世界模型，把預測軸從「相機會看到什麼」擴展到「機器人會感覺到什麼」（未來本體態 + 失效風險），開了世界模型物理未來預測這條新方法軸。_
- **[Compliance for Free: Learning Identifiable Impedance via Bilateral Teleoperation](https://arxiv.org/abs/2609.19976)** — `VLA` · 2026-09-18
  - _首次讓 VLA 除位姿外再輸出剛度/順應性，並以四通道雙邊遙操作（leader 臂作為意圖平衡點的獨立量測）解決順應性監督訊號的可辨識性瓶頸，從而零標註成本取得 per-timestep、方向相關的剛度標籤——開了一條『接觸力/阻抗監督』的新方法軸，解了既有示教介面原則上取不到順應性這件事。_
- **[Dreaming the Sound of Contact: Leveraging Video and Audio Generation for Zero-Shot Force-Aware Manipulation and Data Generation](https://arxiv.org/abs/2609.19137)** — `generative` · 2026-09-17
  - _開了一條新軸：把生成式音訊的接觸響度當作「力/接觸先驗」，補上既有 video-generation 操作軌跡只給純運動學、無力資訊的缺口，實現 zero-shot 力感知的接觸豐富操作（純運動學 baseline 直接失敗），並兼作資料生成引擎——具體新意在『生成音訊→時變力廓線』這條此前不存在的能力軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._