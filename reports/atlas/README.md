# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 1642 papers · 2026-07-08 → 2026-08-27 · ⚡ 201 · 🔧 681 · 📖 760

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 73
learned                    ███████████████████····· 244
hybrid                     ███████████████········· 185
generative                 █████··················· 61
3R-SLAM-hybrid             █······················· 9
VLA                        ████████████████████████ 305
world-model-as-policy      ██████████·············· 126
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 | W33 | W35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 13 | 1 | 10 |
| learned | 36 | 39 | 37 | 54 | 40 | 11 | 27 |
| hybrid | 17 | 37 | 44 | 25 | 23 | 8 | 31 |
| generative | 7 | 13 | 10 | 7 | 12 | 3 | 9 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 | 1 | 1 |
| VLA | 37 | 49 | 50 | 42 | 58 | 17 | 52 |
| world-model-as-policy | 11 | 17 | 17 | 26 | 29 | 7 | 19 |
| **total** | **117** | **171** | **176** | **166** | **176** | **48** | **149** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 170
fixed-lag                  ························ 1
incremental                ███████················· 146
per-scene                  ████████████████████████ 482
feed-forward               █████··················· 99
temporal-transformer-rolling ██████·················· 122
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 285
navigation                 ██████████████████······ 209
spatial-reasoning          █████████··············· 108
reconstruction             ████████················ 93
pose                       ███····················· 40
tracking                   ██······················ 25
depth                      ██······················ 23
VSLAM                      ██······················ 22
VIO                        █······················· 17
mapping                    █······················· 11
SfM                        █······················· 8
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 262
scene-graph                ██████████████·········· 154
3DGS                       ████████················ 89
pointmap                   ███████················· 72
sparse                     ██████·················· 68
BEV                        ███····················· 29
voxel                      ██······················ 21
NeRF                       ██······················ 21
implicit-sdf               ██······················ 19
mesh                       █······················· 14
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 433
multi-modal                ██████████·············· 186
RGBD                       █████████··············· 167
LiDAR                      ██······················ 31
event                      █······················· 21
stereo                     █······················· 15
IMU                        █······················· 11
4D-radar                   ························ 9
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Latent Chain-of-Thought World Modeling for End-to-End Driving](https://arxiv.org/abs/2512.10226)** — `world-model-as-policy` · 2026-08-27
  - _首次將 chain-of-thought 推理完全內化為 action-aligned latent tokens（非自然語言、非 symbolic），並與 world model 的未來 rollout 聯合參數化，實現了 'world-model-as-policy' 範式下推理與控制的統一表徵——此前所有 VLA 驅動模型的 CoT 均依賴外部可讀語言或離散符號，無法端到端優化語義-動作對齊。_
- **[Scene2Demo: Self-Evolving Embodied Data Generation via Object-Action Graph](https://arxiv.org/abs/2602.12065)** — `world-model-as-policy` · 2026-08-27
  - _首次實現「單圖→可執行具身任務數據集」的端到端閉環生成範式，引入 object-action graph 作為空間-動作聯合本體，在 paradigm 軸上確立 'world-model-as-policy' 的新實例：世界模型不再僅預測狀態，而是直接編碼可執行、可演化、帶反饋修正的行動流（action flow），解決 ontology §13 中長期懸而未決的『具身數據生成缺乏因果可追溯性與執行可修正性』問題。_
- **[SANTS: A State-Adaptive Scheduler for World Action Models](https://arxiv.org/abs/2605.27947)** — `generative` · 2026-08-27
  - _首次提出並實證了‘狀態自適應去噪深度調度’這一新範式軸：在視頻到動作的擴散策略中，放棄固定終端去噪（既有範式），轉而根據當前視頻狀態動態選擇最優去噪點，使行動生成從‘追求視頻保真度’轉向‘最大化下游動作質量’，解決了擴散模型在時序動作決策中長期存在的‘過去噪-欠去噪’權衡困境。_
- **[Temporally Centered SIGReg Improves LeWorldModel Representations for Robot Policy Learning](https://arxiv.org/abs/2607.26924)** — `world-model-as-policy` · 2026-08-27
  - _首次提出將正則化目標從全時序潛在表示轉向**時序中心化殘差**（temporally centered residual），解開了世界模型中持久性成分與動態殘差的方差分配耦合問題，使潛在空間同時具備穩定規劃能力與可解碼的機器人狀態/動力學表徵——這是 world-model-as-policy 範式下 latent geometry 的根本性重構。_
- **[AeroDPO: Unleashing Lightweight UAV Navigation with High-Fidelity Perception and Automated Preference Optimization](https://arxiv.org/abs/2608.07557)** — `VLA` · 2026-08-27
  - _Introduces 'automated Direct Preference Optimization' with deterministic physical simulation state rollback — a new paradigm axis (VLA → VLA-as-policy-with-automated-preference-mining) that eliminates human annotation for spatial safety constraints, solving the long-standing OOD collision robustness problem in UAV-VLN without sacrificing lightweight deployment._
- **[DELE-w0.5: Inferring Action from Future Latent State for Robotic Manipulation](https://arxiv.org/abs/2608.22067)** — `world-model-as-policy` · 2026-08-27
  - _提出首個跳過視頻生成中間表示、直接從未來物理狀態潛變量反推動作的範式（paradigm 軸：world-model-as-policy → 'world-model-as-state-action-inverter'），解了 ontology §13 中「世界模型應建模物理因果而非視覺連續性」這一長期爭議，並給出可量化的因果壓縮指標（w0.5 表示 50% latent dim 縮減下動作恢復精度不降）。_
- **[Learning to Act While Waiting: RL Finetuning of Generalist Robot Policies Under Inference Latency](https://arxiv.org/abs/2608.23831)** — `VLA` · 2026-08-27
  - _首次提出並形式化「推理延遲破壞馬可夫性」這一根本問題，並通過狀態增廣（committed actions + mid-inference observation）在 paradigm 軸上開創 'latency-aware RL for VLAs' 新範式，使 RL finetuning 在真實部署延遲下首次成為可能。_
- **[GaussVLA: Geometry-Aware Spatial Reasoning for Vision-Language-Action Model](https://arxiv.org/abs/2608.24959)** — `VLA` · 2026-08-27
  - _首次將3D Gaussian tokens作為VLA的原生空間表徵軸，實現了從2D patch token → 几何可微3D token的範式轉移，使VLA具備內建表面法向、置信度與局部曲率感知能力，此前所有VLA均無法在token層級執行非自迴歸幾何推理。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._