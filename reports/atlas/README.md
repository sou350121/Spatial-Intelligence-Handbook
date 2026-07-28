# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 566 papers · 2026-07-08 → 2026-07-28 · ⚡ 85 · 🔧 366 · 📖 115

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 39
learned                    █████████████████████··· 128
hybrid                     █████████████████······· 106
generative                 ██████·················· 36
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 148
world-model-as-policy      █████████··············· 55
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 |
|---|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 2 |
| learned | 37 | 39 | 38 | 14 |
| hybrid | 17 | 37 | 47 | 5 |
| generative | 8 | 13 | 11 | 4 |
| 3R-SLAM-hybrid | · | 3 | 3 | · |
| VLA | 37 | 50 | 52 | 9 |
| world-model-as-policy | 11 | 19 | 18 | 7 |
| **total** | **119** | **174** | **184** | **41** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 91
incremental                ████████················ 84
per-scene                  ████████████████████████ 253
feed-forward               █████··················· 49
temporal-transformer-rolling █████··················· 50
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 123
VLA                        ███████████████████████· 120
spatial-reasoning          ██████████·············· 51
reconstruction             █████████··············· 48
pose                       █████··················· 25
VSLAM                      ███····················· 16
tracking                   ███····················· 13
depth                      ██······················ 12
VIO                        ██······················ 11
mapping                    ██······················ 8
SfM                        █······················· 6
occupancy                  █······················· 3
VO                         █······················· 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 126
scene-graph                ███████████████········· 78
3DGS                       █████████··············· 48
sparse                     █████████··············· 45
pointmap                   ██████·················· 31
NeRF                       ██······················ 13
voxel                      ██······················ 13
BEV                        ██······················ 13
implicit-sdf               ██······················ 9
mesh                       █······················· 5
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 235
multi-modal                █████████··············· 84
RGBD                       ████████················ 82
LiDAR                      ██······················ 17
stereo                     █······················· 10
event                      █······················· 9
IMU                        █······················· 7
4D-radar                   █······················· 5
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[NVIDIA OmniDreams: Real-Time Generative World Model for Closed-Loop Autonomous Vehicle Simulation](https://arxiv.org/abs/2606.03159)** — `world-model-as-policy` · 2026-07-28
  - _首次實現 world-model-as-policy 范式下的 real-time autoregressive generative world model，具備 action-conditioned、state-aware、closed-loop sensor synthesis 能力，解決傳統重建式模擬器無法泛化至未見動態場景（如極端天氣、不可預測 agent 行為）的根本限制，屬 ontology §13 中 'generative world model as closed-loop environment' 的範式信號。_
- **[BiWM: Advancing Open-Source Interactive Video World Models with Bidirectional Autoregression](https://arxiv.org/abs/2606.10135)** — `world-model-as-policy` · 2026-07-28
  - _首創 bidirectional autoregressive 范式，突破傳統 causal autoregressive world model 的單向時序約束，在 time 軸上實現可逆、非破壞性歷史交互，使長時程可控生成與動態場景編輯成為可能——此前所有 VLA/world-model-as-policy 工作均受限於嚴格因果掩碼。_
- **[Agentic Real2Sim: Physics-based World Modeling with Vision-Language Agents](https://arxiv.org/abs/2607.19190)** — `world-model-as-policy` · 2026-07-28
  - _首次將 vision-language agent 作為統一控制樞紐，實現跨物性（rigid/deformable/humanoid）的端到端 real2sim 轉換，開創 'world-model-as-policy' 範式在物理世界建模中的實用化軸線：agent 不僅解析視覺輸入，還主動協調幾何重建、物理參數辨識、坐標對齊與仿真組裝等異構子系統，解決長期存在的 'perception-to-simulation semantic gap' 問題。_
- **[Addressing the Orchestration Gap in Generalist Robots via Physical Agency](https://arxiv.org/abs/2607.21725)** — `world-model-as-policy` · 2026-07-28
  - _首次提出並實作「物理代理協調範式（Physical Agency orchestration）」，在 paradigm 軸上開闢新類別 'world-model-as-policy' 的子類——將 world model 從被動預測器轉為主動、可介入、具故障恢復能力的閉環高階協調器，解決長期存在的 'orchestration gap'：既有 VLA 政策無法自主分解目標、驗證執行結果、或規劃性恢復，此能力此前不存在於任何 SOTA 架構中。_
- **[Closing the Loop: Training-Free Revisit Consistency for Autoregressive Generative Rendering](https://arxiv.org/abs/2607.21848)** — `generative` · 2026-07-28
  - _首次提出訓練無需的、基於3D引擎內建幾何先驗（pose + depth reprojection）實現autoregressive生成視頻中長期revisit外觀一致性的範式，解決了生成式渲染中KV cache eviction導致的world collapse這一範式級瓶頸，開闢了'generative SLAM'新軸。_
- **[Action-Conditioned World Model for Goal Plane Probe Guidance in Robotic Ultrasound](https://arxiv.org/abs/2607.21918)** — `world-model-as-policy` · 2026-07-28
  - _首次將 world-model-as-policy 範式引入超音波引導任務，透過凍結的 action-conditioned latent diffusion world model 提供可微分、物理感知的模擬獎勵，解決了超音波影像無法建構顯式物理模擬器的根本瓶頸，實現無真值運動標註下的目標平面導航。_
- **[ViTacWorld: Scaling Visuo-Tactile World Models for Contact-Rich Robot Manipulation](https://arxiv.org/abs/2607.22530)** — `world-model-as-policy` · 2026-07-28
  - _首度將 world model 范式（而非僅 VLA 或 policy network）擴展至 visuo-tactile-action 軸，實現可微分、動作條件化的跨模態（視覺+觸覺）時序預測，解決了 contact-rich 操控中因觸覺數據稀缺與 sim2real 障礙導致的 world model 缺位問題——此前 world-model-as-policy 軸僅涵蓋視覺或語言動作，未整合物理接地最強的觸覺信號。_
- **[Robot-Factored World Models via Robot Rendering](https://arxiv.org/abs/2607.22535)** — `world-model-as-policy` · 2026-07-28
  - _首次將 robot body 的 controller、kinematics 和 URDF 渲染顯式解耦為可復用的中間表示（nominal trajectory + rendered robot geometry），使 world model 免於學習 action realization 與 robot-specific rendering，從而實現跨 embodiment 的視覺世界模型接口——這在 paradigm 軸上開創 'world-model-as-policy' 與 robot-factored perception 的新耦合範式，解決了長期存在的 action-conditioning 混淆（realization vs. interaction）與 embodiment 泛化瓶頸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._