# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3665 papers · 2026-07-08 → 2026-10-20 · ⚡ 293 · 🔧 2255 · 📖 1117

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 223
learned                    ██████████████████······ 726
hybrid                     █████████████··········· 496
generative                 ██████·················· 225
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 943
world-model-as-policy      █████████··············· 355
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W36 | W37 | W38 | W39 | W40 | W41 | W42 | W43 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 16 | 12 | 31 | 28 | 13 | 13 | 8 | 8 |
| learned | 55 | 45 | 56 | 50 | 51 | 50 | 26 | 29 |
| hybrid | 51 | 22 | 41 | 44 | 38 | 34 | 17 | 22 |
| generative | 24 | 18 | 20 | 18 | 13 | 11 | 13 | 7 |
| 3R-SLAM-hybrid | 1 | · | · | · | 1 | · | 1 | · |
| VLA | 55 | 37 | 83 | 95 | 96 | 87 | 65 | 49 |
| world-model-as-policy | 19 | 12 | 31 | 38 | 28 | 28 | 23 | 11 |
| **total** | **221** | **146** | **262** | **273** | **240** | **223** | **153** | **126** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 439
fixed-lag                  █······················· 22
incremental                ████████████············ 389
per-scene                  █████████████████████··· 696
feed-forward               ████████████████████████ 796
temporal-transformer-rolling █████████████··········· 437
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1133
navigation                 ████████████············ 550
spatial-reasoning          ██████·················· 284
reconstruction             █████··················· 242
pose                       ███····················· 159
tracking                   ██······················ 94
mapping                    █······················· 67
VSLAM                      █······················· 61
depth                      █······················· 47
VIO                        █······················· 46
occupancy                  ························ 17
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 770
scene-graph                █████████··············· 294
pointmap                   ███████················· 217
3DGS                       ██████·················· 178
sparse                     █████··················· 175
mesh                       ███····················· 100
BEV                        ███····················· 87
voxel                      ██······················ 57
implicit-sdf               █······················· 37
NeRF                       █······················· 30
HD-map                     ························ 12
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1165
multi-modal                █████████████████······· 815
RGBD                       ███████················· 340
LiDAR                      ██······················ 73
event                      █······················· 36
IMU                        █······················· 31
stereo                     █······················· 30
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Online World Modeling Enables Real-World Inverse Reinforcement Learning from Observation](https://arxiv.org/abs/2602.24121)** — `world-model-as-policy` · 2026-10-20
  - _首個在真實世界僅憑任務觀測（video）從零學會視覺操作的 IRLfO 方法：以線上世界模型取代獎勵設計、模擬器建模與動作監督三項瓶頸，40 分鐘內將 pick-and-place 訓練到 82%（同等預算下 RL 為 0%、BC 為 12%），並首次展示真實世界跨任務的正向線上遷移，開出「無獎勵、無動作標籤的真實世界策略學習」這條新軸。_
- **[Scaling Online Exploration for Robot Agents](https://arxiv.org/abs/2610.22496)** — `VLA` · 2026-10-19
  - _開了一條新軸：以「通用 coding agent + 線上探索」直接合成可執行程式來取代 teleoperation 示範語料與 value function，使策略不再受 imitation distribution 束縛，並首次在多 embodiment 上給出「泛化隨探索量單調提升」的可量化 scaling 證據（既有 robot learning 做不到無示範、無 primitive、無 value guidance 的自提升）。_
- **[Sample-Efficient Reinforcement Learning for Policy Improvement via Flow-Reversed Action Anchors](https://arxiv.org/abs/2610.22852)** — `VLA` · 2026-10-19
  - _把 flow-matching 策略的 RL 探索空間由無結構噪聲空間改為「flow reversal 得到的 state-conditioned 潛在錨點 + 局部粒子」，開了一條以可粗到細精化的動作表示做 policy improvement 的新軸，解決既有噪聲空間 RL 在難任務上取不到學習信號的問題，並給出識別複雜度/support bias 的可量化權衡分析。_
- **[BeJEPA: A Goal-Conditioned Humanoid Behavior World Model via Unsupervised RL](https://arxiv.org/abs/2610.23127)** — `world-model-as-policy` · 2026-10-19
  - _以 JEPA 學一個「世界座標下的身體+位置」共享潛在表徵，並用 successor predictor 把長時程 goal-conditioned 政策的期望未來壓成單一向量，取代 world-model 控制中常見的長 imagined rollout，首次讓 humanoid 在被位移後能回到目標世界位姿（AMASS 上全域位置誤差較 BFM-Zero 降 61.7%），是把 successor representation 接到 JEPA 行為世界模型這條新軸上的具體能力突破。_
- **[Momentum: Persistent Dynamics for Video World Models](https://arxiv.org/abs/2610.23423)** — `generative` · 2026-10-19
  - _在視頻世界模型上開了一條「視野外持續動態記憶」的新軸：以同步參考相機組的視頻 latent 作共享世界狀態，並用 rig 圖在相鄰組間傳播生成，使離開視野的車輛/行人不再被遺忘或錯誤重現——這是既有 observation-history / 靜態點雲 / image-cache 表示結構上做不到的。_
- **[A Phenomenology of Neural Geometry in Vision-Language-Action Models](https://arxiv.org/abs/2610.20840)** — `VLA` · 2026-10-16
  - _在 VLA 可解釋性上開出新軸：從「概念可否線性讀出」推進到「概念實際實現的幾何形狀」，並用沿幾何方向的 steering 使其可操作化。_
- **[World-T3: Test-Time Training as Persistent Memory for Real-Time Video World Models](https://arxiv.org/abs/2610.17434)** — `generative` · 2026-10-15
  - _在世界模型記憶這條軸上開新範式：用 test-time training 的 fast-weight 參數（pose-keyed 遞迴最小二乘在線更新）取代依賴 context 的隱式記憶，做到 rollout 長度無關的常數儲存與常數每步計算，解決了既有自回歸世界模型長時程空間記憶衰減的既有做不到之事。_
- **[Into the LidarVerse: A Real-Time Unified LiDAR World Model Across Tasks and Sensors](https://arxiv.org/abs/2610.19201)** — `generative` · 2026-10-15
  - _首個把 reconstruction-based 與 generative 兩條原本互斥的 LiDAR 模擬範式融進單一 conditional generative framework：以 universal tokenizer 共用 latent，靠「可用的場景證據」在多任務（new-world generator / point-cloud forecaster / resimulator）間切換，並泛化到未見掃描模式、支援 32/64/128-beam，開了一條「統一條件生成式 LiDAR 世界模型」的新方法軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._