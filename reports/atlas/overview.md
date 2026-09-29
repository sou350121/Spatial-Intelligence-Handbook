# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2666 papers · 2026-07-08 → 2026-09-29 · ⚡ 242 · 🔧 1475 · 📖 949

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 166
learned                    ███████████████████····· 477
hybrid                     ███████████████········· 361
generative                 ██████·················· 147
3R-SLAM-hybrid             ························ 10
VLA                        ████████████████████████ 595
world-model-as-policy      ██████████·············· 237
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W32 | W33 | W35 | W36 | W37 | W38 | W39 | W40 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 13 | 1 | 14 | 16 | 12 | 31 | 28 | 3 |
| learned | 40 | 11 | 41 | 55 | 45 | 57 | 50 | 15 |
| hybrid | 23 | 8 | 35 | 51 | 22 | 41 | 44 | 15 |
| generative | 12 | 3 | 12 | 24 | 18 | 20 | 18 | 3 |
| 3R-SLAM-hybrid | 1 | 1 | 1 | 1 | · | · | · | · |
| VLA | 56 | 16 | 57 | 55 | 37 | 83 | 95 | 21 |
| world-model-as-policy | 29 | 7 | 26 | 19 | 12 | 31 | 38 | 5 |
| **total** | **174** | **47** | **186** | **221** | **146** | **263** | **273** | **62** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 318
fixed-lag                  █······················· 14
incremental                ███████████············· 264
per-scene                  ████████████████████████ 602
feed-forward               ████████████████········ 413
temporal-transformer-rolling ███████████············· 279
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 683
navigation                 █████████████··········· 372
spatial-reasoning          ███████················· 203
reconstruction             ██████·················· 182
pose                       ████···················· 109
tracking                   ██······················ 59
mapping                    █······················· 40
VSLAM                      █······················· 39
depth                      █······················· 38
VIO                        █······················· 35
occupancy                  ························ 12
SfM                        ························ 10
VO                         ························ 7
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 523
scene-graph                ██████████·············· 226
pointmap                   ███████················· 158
3DGS                       ███████················· 142
sparse                     ██████·················· 129
BEV                        ███····················· 61
mesh                       ██······················ 54
voxel                      ██······················ 41
NeRF                       █······················· 29
implicit-sdf               █······················· 26
HD-map                     ························ 7
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 781
multi-modal                ████████████████········ 510
RGBD                       ████████················ 258
LiDAR                      ██······················ 62
event                      █······················· 34
stereo                     █······················· 22
IMU                        █······················· 18
4D-radar                   █······················· 17
sonar                      ························ 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

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
- **[4DStreamCtrl: Interactive Video Generation with Online 4D Control](https://arxiv.org/abs/2608.25479)** — `generative` · 2026-09-16
  - _把相機運動、物體軌跡與深度統一成單一 3D point-track 控制介面，並蒸餾出因果 streaming student，首次在同一模型內同時做到 3D 一致的相機+物體聯合控制與即時（20FPS）、長度無關記憶體的串流生成——新軸在「線上串流 4D 控制」這一此前只能離線/單模態的維度。_
- **[SAVLA: Symmetry-Aware Vision-Language-Action Models for Robotic Manipulation](https://arxiv.org/abs/2609.16641)** — `VLA` · 2026-09-16
  - _在 VLA 上開啟「對稱/等變性」這條新方法軸：將 action head 的 state/action/conditioning 分解為 invariant/equivariant 通道並在 flow-matching 各層保持型別，配 learned canonicalizer 正規化斜視影像，把 VLA 原本只能靠 demo 覆蓋姿態、旋轉下 41.5% 的泛化硬傷提升到 90.4%，是既有 VLA 做不到的幾何泛化能力。_
- **[Bridging Learned Visual Perception and Symbolic Belief-Space Planning](https://arxiv.org/abs/2609.16884)** — `VLA` · 2026-09-16
  - _提出 VLM-as-probabilistic-grounder 第三範式，把 VLM 謂詞 grounding 的不確定性表為符號狀態上的機率分布，讓規劃能在 belief space 進行，在既有 VLM-as-planner / VLM-as-grounder 兩條軸之外開出新軸並解了其忽略不確定性的問題。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._