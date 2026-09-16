# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 2223 papers · 2026-07-08 → 2026-09-16 · ⚡ 231 · 🔧 1104 · 📖 888

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 125
learned                    █████████████████████··· 394
hybrid                     ███████████████········· 280
generative                 ██████·················· 117
3R-SLAM-hybrid             █······················· 10
VLA                        ████████████████████████ 444
world-model-as-policy      ██████████·············· 182
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W30 | W31 | W32 | W33 | W35 | W36 | W37 | W38 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 15 | 11 | 13 | 1 | 14 | 16 | 12 | 21 |
| learned | 35 | 53 | 40 | 11 | 41 | 55 | 45 | 39 |
| hybrid | 43 | 25 | 23 | 8 | 35 | 51 | 22 | 19 |
| generative | 10 | 7 | 12 | 3 | 12 | 24 | 18 | 11 |
| 3R-SLAM-hybrid | 3 | · | 1 | 1 | 1 | 1 | · | · |
| VLA | 48 | 41 | 56 | 16 | 57 | 55 | 37 | 48 |
| world-model-as-policy | 17 | 26 | 29 | 7 | 26 | 19 | 12 | 19 |
| **total** | **171** | **163** | **174** | **47** | **186** | **221** | **146** | **157** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████·············· 245
fixed-lag                  ························ 7
incremental                █████████··············· 213
per-scene                  ████████████████████████ 563
feed-forward               ███████████············· 268
temporal-transformer-rolling █████████··············· 207
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 473
navigation                 ███████████████········· 287
spatial-reasoning          █████████··············· 169
reconstruction             ████████················ 160
pose                       ████···················· 81
tracking                   ██······················ 49
depth                      ██······················ 36
VSLAM                      ██······················ 30
mapping                    █······················· 29
VIO                        █······················· 26
SfM                        █······················· 10
occupancy                  █······················· 10
VO                         ························ 6
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 410
scene-graph                ███████████············· 189
pointmap                   ████████················ 130
3DGS                       ███████················· 124
sparse                     ██████·················· 104
BEV                        ███····················· 46
voxel                      ██······················ 39
mesh                       ██······················ 39
NeRF                       ██······················ 27
implicit-sdf               █······················· 22
HD-map                     ························ 6
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 642
multi-modal                █████████████··········· 349
RGBD                       ████████················ 213
LiDAR                      ██······················ 49
event                      █······················· 30
stereo                     █······················· 20
IMU                        █······················· 16
4D-radar                   ························ 12
sonar                      ························ 5
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[4DStreamCtrl: Interactive Video Generation with Online 4D Control](https://arxiv.org/abs/2608.25479)** — `generative` · 2026-09-16
  - _把相機運動、物體軌跡與深度統一成單一 3D point-track 控制介面，並蒸餾出因果 streaming student，首次在同一模型內同時做到 3D 一致的相機+物體聯合控制與即時（20FPS）、長度無關記憶體的串流生成——新軸在「線上串流 4D 控制」這一此前只能離線/單模態的維度。_
- **[SAVLA: Symmetry-Aware Vision-Language-Action Models for Robotic Manipulation](https://arxiv.org/abs/2609.16641)** — `VLA` · 2026-09-16
  - _在 VLA 上開啟「對稱/等變性」這條新方法軸：將 action head 的 state/action/conditioning 分解為 invariant/equivariant 通道並在 flow-matching 各層保持型別，配 learned canonicalizer 正規化斜視影像，把 VLA 原本只能靠 demo 覆蓋姿態、旋轉下 41.5% 的泛化硬傷提升到 90.4%，是既有 VLA 做不到的幾何泛化能力。_
- **[Bridging Learned Visual Perception and Symbolic Belief-Space Planning](https://arxiv.org/abs/2609.16884)** — `VLA` · 2026-09-16
  - _提出 VLM-as-probabilistic-grounder 第三範式，把 VLM 謂詞 grounding 的不確定性表為符號狀態上的機率分布，讓規劃能在 belief space 進行，在既有 VLM-as-planner / VLM-as-grounder 兩條軸之外開出新軸並解了其忽略不確定性的問題。_
- **[PhysStream: Streaming Physics-Grounded Video Generation with Structured Scene Memory and Fine-Grained Motion Control](https://arxiv.org/abs/2609.17521)** — `generative` · 2026-09-16
  - _在可控視頻生成這條軸上引入此前不存在的能力：以稀疏速度增量（物理量）而非像素位置作為條件信號，配合由已生成幀在線導出的結構化場景記憶（位置圖+物體追蹤圖），實現生成中途的交互式物理動力學控制，而非既有方法必須在生成前給定完整控制序列。_
- **[Modality-Autoregressive World-Action Models](https://arxiv.org/abs/2609.17524)** — `world-model-as-policy` · 2026-09-16
  - _首個在動作解碼前對多種未來模態（point track / DINO 特徵 / depth）逐一自回歸去噪的 world-action model，開出『WAM 該預測哪些模態、以何種次序生成』這條新方法軸，並以系統量化實驗回答該領域既有開放問題（預測 RGB 並無一致增益，幾何/語義/運動模態才有效）。_
- **[Ego-Dynamics-Augmented World Model for Autonomous Driving with Zero-Shot Cross-Embodiment Adaptation](https://arxiv.org/abs/2607.13410)** — `world-model-as-policy` · 2026-09-14
  - _點名一條新軸：以物理先驗 ego-dynamics context（橫向動力學+神經輪胎力）條件化 BEV world model 的隱分佈，於資訊論上移除 transition entropy/先驗中的 ego-motion 項，從而實現 zero-shot 跨底盤/跨具身泛化——這是既有 BEV-WM 做不到的能力。_
- **[CLAP: Cross-Embodiment Video World Models are Zero-Shot Physical Simulators](https://arxiv.org/abs/2608.27406)** — `world-model-as-policy` · 2026-09-14
  - _把 action-conditioned 影片世界模型從「單一本體」推進到「跨本體」這條新方法軸：用末端執行器位姿＋語言＋latent action 統一異質動作空間，再以課程式（先 latent action 學物理先驗、後接地到 EEF 動作空間）預訓練，使世界模型能在未見過的本體上零樣本當物理模擬器——這是先前單一本體影片模型做不到的能力。_
- **[IMPLY: Physically Anchored Consistency for World-Model Rollouts](https://arxiv.org/abs/2609.12441)** — `world-model-as-policy` · 2026-09-14
  - _首度把 world-model rollout 的驗證軸從『自我一致性』換成『物理錨定一致性』：反演模擬器讀出每次 rollout 隱含的質量/摩擦並以校準推動作錨，量化揭露了自我一致性無法區分「自洽但錯認物件」與「真正追蹤物件」這一既有盲點（AUROC 0.70 vs 1.00，52%→73%），是新的評測方法軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._