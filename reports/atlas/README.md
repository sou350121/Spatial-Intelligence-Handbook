# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 329 papers · 2026-07-08 → 2026-07-17 · ⚡ 45 · 🔧 221 · 📖 63

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 23
learned                    ███████████████████····· 76
hybrid                     ██████████████·········· 55
generative                 ██████·················· 24
3R-SLAM-hybrid             █······················· 3
VLA                        ████████████████████████ 94
world-model-as-policy      ████████················ 31
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 |
|---|---:|---:|
| geometric | 10 | 13 |
| learned | 37 | 39 |
| hybrid | 17 | 38 |
| generative | 9 | 15 |
| 3R-SLAM-hybrid | · | 3 |
| VLA | 39 | 55 |
| world-model-as-policy | 11 | 20 |
| **total** | **123** | **183** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 49
incremental                ████████················ 49
per-scene                  ████████████████████████ 150
feed-forward               █████··················· 30
temporal-transformer-rolling █████··················· 30
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 79
navigation                 ███████████████████████· 77
spatial-reasoning          ████████················ 25
reconstruction             ██████·················· 20
VSLAM                      ████···················· 13
pose                       ███····················· 11
tracking                   ███····················· 9
depth                      ██······················ 8
VIO                        ██······················ 6
SfM                        █······················· 3
mapping                    █······················· 2
occupancy                  ························ 1
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 85
scene-graph                █████████████··········· 45
3DGS                       ████████················ 28
sparse                     ██████·················· 22
pointmap                   ███····················· 12
NeRF                       ███····················· 11
BEV                        ███····················· 9
voxel                      █······················· 5
implicit-sdf               █······················· 4
mesh                       █······················· 2
HD-map                     █······················· 2
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 140
multi-modal                ████████················ 48
RGBD                       ████████················ 45
LiDAR                      █······················· 8
event                      █······················· 7
stereo                     █······················· 7
IMU                        █······················· 3
4D-radar                   ························ 2
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[MotuBrain: An Advanced World Action Model for Robot Control](https://arxiv.org/abs/2604.27792)** — `world-model-as-policy` · 2026-07-17
  - _首次實現 world-model-as-policy 范式下的統一多任務架構（policy/world model/video gen/inverse dynamics/joint prediction），且透過共享跨 embodiment 行動表徵與實時閉環 chunked 推理，解決長期存在的「世界模型不可控、可控策略無世界理解」的 ontology §13 核心張力。_
- **[RoboWorld: Fast and Reliable Neural Simulators for Generalist Robot Policy Evaluation](https://arxiv.org/abs/2607.01060)** — `world-model-as-policy` · 2026-07-17
  - _首次將 world-model-as-policy 範式轉向 policy evaluation 場景，並透過 Step Forcing 在 autoregressive video world models 中實現可證實的 long-horizon rollout 可靠性（解決長期存在的 train-test mismatch 導致 rollout 指標失真問題），使 video world model 從生成工具升級為可量化的、與 real-world policy ranking 強對齊的評估儀器。_
- **[Diagnosing Semantic Handoff Failures in Agent-Orchestrated Vision-Language-Action Skill Composition](https://arxiv.org/abs/2607.06256)** — `VLA` · 2026-07-17
  - _首次形式化並可診斷「語義交接失敗」這一長期隱性瓶頸，定義了技能鏈式執行中狀態分布偏移（clean boundary → messy chained state）的可量化診斷軸，為VLA技能組合提供了新的robustness評估範式與學習目標。_
- **[Just-In-Time Scene Graph Growth: Combating Perceptual Saturation in Long-Horizon Robotics](https://arxiv.org/abs/2607.13245)** — `world-model-as-policy` · 2026-07-17
  - _首次將 scene-graph 的構建從靜態、全量、ahead-of-time 范式，轉為動態、稀疏、query-driven 的 closed-loop just-in-time 生長範式，解開了長期存在的「感知飽和」（perceptual saturation）與邊緣實時性之間的根本矛盾，屬 paradigm 軸上的範式信號：world-model-as-policy + hybrid（LLM-driven cognitive control over geometric memory）。_
- **[Ego-Dynamics-Augmented World Model for Autonomous Driving with Zero-Shot Cross-Chassis Adaptation](https://arxiv.org/abs/2607.13410)** — `world-model-as-policy` · 2026-07-17
  - _首次將可識別的物理 ego-dynamics prior 顯式注入 world-model 的 latent transition（paradigm 軸），解耦 ego-motion 與 scene dynamics，使 WM 從 'egocentric BEV imagination' 轉向 'dynamics-conditioned scene-centric imagination'，實現 zero-shot cross-chassis adaptation——這是 ontology §13 中長期懸而未決的 'embodiment generalization without retraining' 問題的可量化、可驗證解。_
- **[S-squared-VLA: Decoupling Semantic and Spatial Streams in Vision-Language-Action Models for Autonomous Driving](https://arxiv.org/abs/2607.13926)** — `VLA` · 2026-07-17
  - _首次提出語義-空間雙流解耦範式（paradigm軸），在VLA中系統性阻斷語言token化對空間幾何先驗的不可逆坍縮，實現了語言級意圖推理與毫米級邊界感知控制的正交化建模——此前所有VLA均採用單一token流聯合編碼，無法同時保障語義泛化性與空間保真度。_
- **[GigaWorld-Policy-0.5: A Faster and Stronger WAM Empowered by AutoResearch](https://arxiv.org/abs/2607.13960)** — `world-model-as-policy` · 2026-07-17
  - _首次實現 world model 與 policy 的解耦式 inference：在 paradigm 軸上提出 'world-model-as-policy' 新範式，使 WAM 從「生成未來視覺序列」轉向「僅輸出動作」的純 policy 推理模式，突破既有 WAM 必須解碼視頻的計算瓶頸，實現 real-time closed-loop 控制。_
- **[M$^\text{4}$World: A Multi-view Multimodal Driving World Model for Interactive Object Manipulation and Minute-long Streaming](https://arxiv.org/abs/2607.14005)** — `world-model-as-policy` · 2026-07-17
  - _首次實現 driving world model 的「交互式物體級操控」與「分鐘級因果流式生成」雙能力：在 paradigm 軸上開創 'world-model-as-policy' 與 generative 的緊耦合範式，使 world model 不僅預測，更支持空間語義干預（如移動/替換特定車輛）並維持跨視角、跨模態（RGB+LiDAR）、長時序（60s+）的動力學一致性——此前所有 driving world models（e.g., WorldSim, DriveDreamer, VQ-Diffusion-based simulators）均無法同時滿足 object-level intervention + minute-long causal streaming + multi-modal synchronization。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._