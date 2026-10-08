# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3013 papers · 2026-07-08 → 2026-10-08 · ⚡ 254 · 🔧 1748 · 📖 1011

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 183
learned                    ██████████████████······ 552
hybrid                     █████████████··········· 410
generative                 █████··················· 165
3R-SLAM-hybrid             ························ 11
VLA                        ████████████████████████ 737
world-model-as-policy      █████████··············· 279
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W33 | W35 | W36 | W37 | W38 | W39 | W40 | W41 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 1 | 14 | 16 | 12 | 31 | 28 | 13 | 7 |
| learned | 11 | 41 | 55 | 45 | 57 | 50 | 51 | 39 |
| hybrid | 8 | 35 | 51 | 22 | 41 | 44 | 38 | 26 |
| generative | 3 | 12 | 24 | 18 | 20 | 18 | 13 | 8 |
| 3R-SLAM-hybrid | 1 | 1 | 1 | · | · | · | 1 | · |
| VLA | 16 | 57 | 55 | 37 | 83 | 95 | 96 | 67 |
| world-model-as-policy | 7 | 26 | 19 | 12 | 31 | 38 | 28 | 19 |
| **total** | **47** | **186** | **221** | **146** | **263** | **273** | **240** | **166** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████████·········· 370
fixed-lag                  █······················· 15
incremental                ███████████············· 296
per-scene                  ████████████████████████ 629
feed-forward               █████████████████████··· 542
temporal-transformer-rolling █████████████··········· 340
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 859
navigation                 ████████████············ 433
spatial-reasoning          ███████················· 235
reconstruction             █████··················· 194
pose                       ███····················· 121
tracking                   ██······················ 70
mapping                    █······················· 51
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
feature-grid               ████████████████████████ 612
scene-graph                ██████████·············· 257
pointmap                   ███████················· 174
3DGS                       ██████·················· 147
sparse                     ██████·················· 142
mesh                       ███····················· 67
BEV                        ███····················· 67
voxel                      ██······················ 44
implicit-sdf               █······················· 30
NeRF                       █······················· 30
HD-map                     ························ 9
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 906
multi-modal                ████████████████········ 621
RGBD                       ████████················ 284
LiDAR                      ██······················ 66
event                      █······················· 36
stereo                     █······················· 25
IMU                        █······················· 22
4D-radar                   ························ 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[PhysEvo: Astra Can Act, Let It](https://arxiv.org/abs/2610.08995)** — `VLA` · 2026-10-08
  - _開了一條『物理遞歸自我改進』新方法軸：以 meta-agent 對凍結 VLA 的工具/技能/診斷器做持續且可測試的修訂（無權重更新、無另訓 policy），把直連 Astra 幾乎做不到的操控（1.25%→55%）變成可行。_
- **[Co-Evolving Robot Orchestrators and Policies through Deployment](https://arxiv.org/abs/2610.09228)** — `VLA` · 2026-10-08
  - _首次讓 VLM orchestrator 與 VLA policy 在部署中共同演化（以驗證式採納把關），開啟「部署即自我改進飛輪」這條新方法軸，突破了既有 orchestrator 只能繞過、無法克服 frozen-policy 失敗的根本瓶頸。_
- **[FoldBack: Self-Correcting Masked Generative Policy for Long-Horizon Garment Folding](https://arxiv.org/abs/2610.10462)** — `generative` · 2026-10-08
  - _首個『可編輯全軌跡生成策略』，把 refine/rollback/retry 三個推理時決策統一起來，能在不重訓基策略、不需失敗示範下偵測—回退—修復失敗抓取，開出『長程策略可回滾/可編輯』這條此前不存在的新方法軸。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._