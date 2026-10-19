# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3607 papers · 2026-07-08 → 2026-10-19 · ⚡ 291 · 🔧 2211 · 📖 1105

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 221
learned                    ███████████████████····· 715
hybrid                     █████████████··········· 485
generative                 ██████·················· 220
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 920
world-model-as-policy      █████████··············· 350
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W36 | W37 | W38 | W39 | W40 | W41 | W42 | W43 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 16 | 12 | 31 | 28 | 13 | 13 | 8 | 6 |
| learned | 55 | 45 | 57 | 50 | 51 | 50 | 26 | 16 |
| hybrid | 51 | 22 | 41 | 44 | 38 | 34 | 17 | 11 |
| generative | 24 | 18 | 20 | 18 | 13 | 11 | 13 | 2 |
| 3R-SLAM-hybrid | 1 | · | · | · | 1 | · | 1 | · |
| VLA | 55 | 37 | 83 | 95 | 96 | 87 | 65 | 26 |
| world-model-as-policy | 19 | 12 | 31 | 38 | 28 | 28 | 23 | 6 |
| **total** | **221** | **146** | **263** | **273** | **240** | **223** | **153** | **67** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 429
fixed-lag                  █······················· 21
incremental                ████████████············ 375
per-scene                  █████████████████████··· 691
feed-forward               ████████████████████████ 775
temporal-transformer-rolling █████████████··········· 432
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1107
navigation                 ████████████············ 543
spatial-reasoning          ██████·················· 278
reconstruction             █████··················· 239
pose                       ███····················· 156
tracking                   ██······················ 92
mapping                    █······················· 62
VSLAM                      █······················· 60
depth                      █······················· 46
VIO                        █······················· 46
occupancy                  ························ 16
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 758
scene-graph                █████████··············· 293
pointmap                   ███████················· 213
3DGS                       ██████·················· 174
sparse                     █████··················· 172
mesh                       ███····················· 95
BEV                        ███····················· 84
voxel                      ██······················ 56
implicit-sdf               █······················· 37
NeRF                       █······················· 30
HD-map                     ························ 12
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1144
multi-modal                █████████████████······· 792
RGBD                       ███████················· 333
LiDAR                      ██······················ 73
event                      █······················· 36
IMU                        █······················· 30
stereo                     █······················· 30
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

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
- **[Robota-Embed: Unified VLA Embeddings for Robot In-Context Learning and Evolution](https://arxiv.org/abs/2610.19495)** — `VLA` · 2026-10-15
  - _首個把視覺—語言—動作三模態同時編碼進『當前查詢』與『未來延續』的 VLA 檢索嵌入，開出「以原生動作嵌入檢索歷史經驗做 in-context 策略調控」這條新軸——既有 action-free 檢索嵌入做不到（去動作掉點遠多於去視覺），且在凍結策略上用執行回饋增量演化記憶。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._