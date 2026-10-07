# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2953 papers · 2026-07-08 → 2026-10-07 · ⚡ 251 · 🔧 1700 · 📖 1002

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 182
learned                    ██████████████████······ 541
hybrid                     █████████████··········· 397
generative                 █████··················· 161
3R-SLAM-hybrid             ························ 11
VLA                        ████████████████████████ 715
world-model-as-policy      █████████··············· 270
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W33 | W35 | W36 | W37 | W38 | W39 | W40 | W41 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 1 | 14 | 16 | 12 | 31 | 28 | 13 | 6 |
| learned | 11 | 41 | 55 | 45 | 57 | 50 | 51 | 28 |
| hybrid | 8 | 35 | 51 | 22 | 41 | 44 | 38 | 13 |
| generative | 3 | 12 | 24 | 18 | 20 | 18 | 13 | 4 |
| 3R-SLAM-hybrid | 1 | 1 | 1 | · | · | · | 1 | · |
| VLA | 16 | 57 | 55 | 37 | 83 | 95 | 96 | 45 |
| world-model-as-policy | 7 | 26 | 19 | 12 | 31 | 38 | 28 | 10 |
| **total** | **47** | **186** | **221** | **146** | **263** | **273** | **240** | **106** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████████·········· 359
fixed-lag                  █······················· 14
incremental                ███████████············· 292
per-scene                  ████████████████████████ 624
feed-forward               ████████████████████···· 517
temporal-transformer-rolling █████████████··········· 331
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 830
navigation                 ████████████············ 419
spatial-reasoning          ███████················· 230
reconstruction             █████··················· 190
pose                       ███····················· 120
tracking                   ██······················ 68
mapping                    █······················· 49
VSLAM                      █······················· 45
depth                      █······················· 38
VIO                        █······················· 38
occupancy                  ························ 14
SfM                        ························ 11
VO                         ························ 8
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 600
scene-graph                ██████████·············· 251
pointmap                   ███████················· 171
3DGS                       ██████·················· 146
sparse                     ██████·················· 140
mesh                       ███····················· 65
BEV                        ███····················· 65
voxel                      ██······················ 44
implicit-sdf               █······················· 30
NeRF                       █······················· 29
HD-map                     ························ 9
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 883
multi-modal                ████████████████········ 601
RGBD                       ████████················ 280
LiDAR                      ██······················ 66
event                      █······················· 36
stereo                     █······················· 25
IMU                        █······················· 20
4D-radar                   ························ 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[SpaTime: Streaming Vision-Language Models for Spatio-temporal Reasoning](https://arxiv.org/abs/2610.08713)** — `VLA` · 2026-10-07
  - _首度把因果幾何 token 融進串流 VLM，並用可微期望回應時間損失讓模型自學「何時已回答足夠」，開出「串流 3D 空間推理 × 自適應回應時機」這條先前不存在的軸。_
- **[OpenRUA: Robot-Use Agents Are Zero-Shot Visuomotor Policies](https://arxiv.org/abs/2610.02459)** — `VLA` · 2026-10-05
  - _開了一條新的方法軸：以「workspace-as-harness / zero-abstraction」讓現成 coding agent 只憑終端直接操作機器人原生 ROS 2 介面，把感知化為檔案 I/O、操作化為寫程式，無需客製 primitive 或任務訓練即可當 zero-shot visuomotor policy（CaP-Bench 99.0%、LIBERO-PRO 87.0%），證明先前大量 harness 工程並非必要。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._