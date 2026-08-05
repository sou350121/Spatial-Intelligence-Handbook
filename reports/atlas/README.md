# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 807 papers · 2026-07-08 → 2026-08-05 · ⚡ 130 · 🔧 512 · 📖 165

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 57
learned                    ██████████████████████·· 190
hybrid                     ███████████████········· 133
generative                 █████··················· 46
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 212
world-model-as-policy      ██████████·············· 91
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 |
|---|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 8 |
| learned | 37 | 39 | 38 | 55 | 21 |
| hybrid | 17 | 37 | 44 | 26 | 9 |
| generative | 8 | 13 | 11 | 7 | 7 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | · |
| VLA | 37 | 50 | 50 | 47 | 28 |
| world-model-as-policy | 11 | 19 | 18 | 27 | 16 |
| **total** | **119** | **174** | **179** | **174** | **89** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 132
fixed-lag                  ························ 1
incremental                ████████················ 115
per-scene                  ████████████████████████ 356
feed-forward               ████···················· 66
temporal-transformer-rolling █████··················· 79
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 192
navigation                 ████████████████████···· 160
reconstruction             █████████··············· 74
spatial-reasoning          █████████··············· 73
pose                       ████···················· 29
tracking                   ██······················ 19
depth                      ██······················ 19
VSLAM                      ██······················ 18
VIO                        ██······················ 12
mapping                    █······················· 10
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 191
scene-graph                █████████████··········· 104
3DGS                       ████████················ 65
sparse                     ███████················· 56
pointmap                   ██████·················· 48
BEV                        ███····················· 20
implicit-sdf               ██······················ 17
NeRF                       ██······················ 16
voxel                      ██······················ 16
mesh                       █······················· 7
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 316
multi-modal                ██████████·············· 137
RGBD                       ██████████·············· 127
LiDAR                      ██······················ 22
event                      █······················· 14
stereo                     █······················· 13
IMU                        █······················· 9
4D-radar                   ························ 6
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[The Gate, Not the Cache: Gate Provenance Bounds the Closed-Loop Reliability of Training-Free VLA Token Skipping](https://arxiv.org/abs/2608.00391)** — `VLA` · 2026-08-05
  - _首次形式化揭示並量化了VLA token skipping中gate provenance（門控信號來源）與閉環可靠性之間的因果關係，提出‘gate cleaness’為決定性變量，並通過actuation-slack refresh在不增加關鍵路徑延遲下實現可靠跳過——這定義了training-free VLA推理中‘可靠性-效率’的新權衡軸，解決了ontology §13中長期懸而未決的‘無訓練加速如何避免控制失穩’爭議。_
- **[Latency-Tolerant Cloud-Edge Collaborative Vision-Language-Action Models via Emergent Representational Specialization](https://arxiv.org/abs/2608.00569)** — `VLA` · 2026-08-05
  - _首次將時序失準（temporal misalignment）建模為表徵學習問題，並通過新穎的‘新鮮-陳舊雙路徑對比訓練目標’實現雲端表徵的任務級不變性與邊端表徵的狀態敏感性解耦——此前所有VLA部署方案均依賴顯式調度、延遲預測或異步緩衝，無法在無同步阻塞下保障動作一致性。_
- **[SelfWAM: A Self-Grounded Unified World Action Model for Fast Robot Control](https://arxiv.org/abs/2608.00725)** — `world-model-as-policy` · 2026-08-05
  - _首次提出‘action-conditioned future visual grounding via self-mask supervision’，在 paradigm 軸上開創 world-model-as-policy 與 self-grounded action-consequence modeling 的新耦合範式：將 robot self-mask 作為可微、時序緊耦合的動作因果代理，使世界模型能區分‘任務進展’與‘動作特異性後果’，解決長期存在的 WAM 中 action-observation decoupling 問題。_
- **[DynamicWAM: Dual-Path Motion Conditioning for World-Action Models in Dynamic Manipulation](https://arxiv.org/abs/2608.00793)** — `world-model-as-policy` · 2026-08-05
  - _首次將 motion as explicit kinematic descriptors（位移/時長/速度/加速度）與 optical-flow history embedding 分離建模並通過 joint world-action attention 融合，使 WAM 具備顯式時序運動參數推理能力——此前 WAMs 僅隱式從視頻 token 學習運動，無法解耦運動的幾何結構（flow）與動力學語義（kinematics），此為 paradigm 軸上從 'VLA' 到 'world-model-as-policy' 的關鍵躍遷：將世界模型輸出從動作 token 擴展為可解釋、可干預的運動參數空間。_
- **[EndoWAM: A Grounded World-Action Model for Generalizable Endoscopic Navigation](https://arxiv.org/abs/2608.01221)** — `world-model-as-policy` · 2026-08-05
  - _首次將 world-model-as-policy 範式實作於柔性、非剛體、極低-data、高安全要求的內視鏡導航場景，並透過 'future grounding' 在 denoising 特徵空間中實現任務導向的未來目標區域預測——此前 WAMs 僅適用於剛體環境（如機器人臂操作或無人機飛行），此工作在 paradigm 軸上突破了 world-model-as-policy 的適用邊界。_
- **[DreamTrajectory: Trajectory-Guided Action Generation with World Model Alignment for Mobile Manipulation](https://arxiv.org/abs/2608.01381)** — `world-model-as-policy` · 2026-08-05
  - _首次將世界模型用於**在線對齊預期端點軌跡與實際誘導軌跡**，實現行動前的可微分軌跡可行性驗證（trajectory world model as alignment oracle），突破VLA開環執行範式，解決長期存在的‘planned-vs-realized motion gap’問題。_
- **[SG-WAM: Self-Guided World Modeling in Geometry-Aware Policy Space](https://arxiv.org/abs/2608.01397)** — `world-model-as-policy` · 2026-08-05
  - _首次將 world model 的 dynamics learning 移入 policy-derived representation space，並以 EMA policy backbone 作為自監督目標、結合幾何約束結構化 token 空間，實現 action-relevant 與 geometry-aware 的統一未來建模——此前所有 WAM 均在 observation space 或脫鉤 latent space 中建模，無法同時滿足動作生成對齊與三維空間可解釋性，此為 paradigm 軸上從 'world-model-as-predictor' 到 'world-model-as-policy-space-dynamics' 的範式躍遷。_
- **[StreamSplat: Streaming Feed-Forward 3D Gaussian Splatting](https://arxiv.org/abs/2608.01659)** — `generative` · 2026-08-05
  - _首次實現因果流式 feed-forward 3DGS：在 time 軸上從 per-scene 跳躍至 incremental，並通過 VACC（voxel-bounded causal memory）與 HPDA/CGFI 兩項機制，使 3DGS 首次具備無界場景增量建模能力——此前所有 3DGS 方法（含 3DGS-VLA、Gaussian Splatting++ 等）均依賴全序列或固定上下文，無法處理長時序、內存受限的在線重建。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._