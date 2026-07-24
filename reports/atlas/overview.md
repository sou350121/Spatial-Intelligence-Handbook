# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 522 papers · 2026-07-08 → 2026-07-24 · ⚡ 77 · 🔧 344 · 📖 101

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 37
learned                    ███████████████████····· 114
hybrid                     █████████████████······· 101
generative                 █████··················· 32
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 141
world-model-as-policy      ████████················ 48
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 |
|---|---:|---:|---:|
| geometric | 9 | 13 | 15 |
| learned | 37 | 39 | 38 |
| hybrid | 17 | 37 | 47 |
| generative | 8 | 13 | 11 |
| 3R-SLAM-hybrid | · | 3 | 3 |
| VLA | 37 | 51 | 53 |
| world-model-as-policy | 11 | 19 | 18 |
| **total** | **119** | **175** | **185** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 87
incremental                ████████················ 79
per-scene                  ████████████████████████ 231
feed-forward               █████··················· 46
temporal-transformer-rolling ████···················· 42
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 117
VLA                        ███████████████████████· 112
spatial-reasoning          █████████··············· 44
reconstruction             ████████················ 41
pose                       █████··················· 25
VSLAM                      ███····················· 16
tracking                   ███····················· 13
depth                      ██······················ 10
VIO                        ██······················ 9
mapping                    █······················· 7
SfM                        █······················· 6
occupancy                  █······················· 3
VO                         █······················· 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 118
scene-graph                ███████████████········· 72
3DGS                       █████████··············· 45
sparse                     █████████··············· 44
pointmap                   ██████·················· 28
NeRF                       ██······················ 12
BEV                        ██······················ 12
voxel                      ██······················ 11
implicit-sdf               █······················· 6
mesh                       █······················· 5
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 219
RGBD                       ████████················ 75
multi-modal                ████████················ 74
LiDAR                      ██······················ 15
stereo                     █······················· 10
event                      █······················· 9
IMU                        █······················· 6
4D-radar                   ························ 4
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[WorldPack: Dynamic Frame Compression for Long-context Video World Modeling](https://arxiv.org/abs/2512.02473)** — `world-model-as-policy` · 2026-07-24
  - _首次將3D viewpoint geometry（camera pose + FoV overlap）顯式建模為動態壓縮率分配的控制信號，開闢‘geometrically-gated memory compression’新範式軸，使video world model首度具備空間感知的長時序記憶調控能力（此前所有VWM均用uniform/time-based/attention-based壓縮，無法保證3D一致性）。_
- **[Don't Fool Me Twice: Adapting to Adversity in the Wild with Experience-Driven Reasoning](https://arxiv.org/abs/2605.31119)** — `world-model-as-policy` · 2026-07-24
  - _首次將空間不確定性（epistemic uncertainty）與語義體素建模耦合，用於在線歸因 embodiment-dependent 干擾的物理因果機制，實現了 'interaction-as-learnable-spatial-behavior' 這一新範式——此前所有 VLA/world model 工作均將干擾視為黑箱異常或需預編碼規則處理。_
- **[Agentic Real2Sim: Physics-based World Modeling with Vision-Language Agents](https://arxiv.org/abs/2607.19190)** — `VLA` · 2026-07-24
  - _首次將 vision-language agent 作為統一控制樞紐，實現跨物性（rigid/deformable/humanoid）的端到端 real2sim 物理世界建模，突破既有 pipeline 的範式割裂——此前所有 Real2Sim 方法均依賴手工分段流水線（geometry → physics → simulation assembly），而本工作以 VLA 驅動的 agentic planning 軸心，動態協調感知、參數推斷與仿真構建，在 paradigm 軸上確立 'VLA-as-orchestrator-for-physical-world-modeling' 新範式。_
- **[Cognitive Dual-Process Planning for Autonomous Driving with Structured Scene Knowledge and Verifiable Reasoning-Action Consistency](https://arxiv.org/abs/2607.19194)** — `VLA` · 2026-07-24
  - _首次將認知雙系統理論（fast/slow thinking）形式化為可驗證的 planning 范式，引入 S-CoT 結構化鏈式推理 schema 與 deterministic rule-based validator，實現 reasoning-action 一致性可證性——此前所有 VLA/world-model 規劃器均無法提供邏輯一致性可驗證性（ontology §13 中長期未解的 'trustworthy grounding' 爭議）。_
- **[Koopman Dreamer: Spectrally Constrained Latent Dynamics for Stable World-Model Imagination](https://arxiv.org/abs/2607.19719)** — `world-model-as-policy` · 2026-07-24
  - _首次將Koopman算子理論的譜約束（旋轉-縮放塊+半徑界）嵌入Dreamer架構，實現對潛在動力學模態衰減/週期性的顯式、可解析控制，解決了長期rollout中誤差累積不可控這一world-model-as-policy範式的根本性穩定性問題。_
- **[Extending a Large View Synthesis Model for Multi-view Panoptic Segmentation](https://arxiv.org/abs/2607.19765)** — `generative` · 2026-07-24
  - _首次證明大型視圖合成模型（無顯式3D表示）所學的cross-view correspondence具備**語義不變性**，可將view-independent panoptic label經二進制編碼後直接通過凍結模型傳播至novel view——開闢了‘隱式空間對應即語義映射’新範式，解決ontology §13中長期爭議‘能否繞過3D重建實現跨視角語義一致性推斷’，且提供可量化的跨數據集zero-shot泛化證據。_
- **[Scaling Cross-Embodiment World Models for Dexterous Manipulation](https://arxiv.org/abs/2511.01177)** — `world-model-as-policy` · 2026-07-23
  - _首次將世界模型建模軸從「scene dynamics」拓展至「embodiment-agnostic interaction geometry」，以粒子位移場統一表徵人手與多種機械手的物理交互，實現跨形態（kinematically heterogeneous）的zero-shot控制遷移——此前所有VLA/world model均綁定特定動作空間或運動學模型。_
- **[STeP: Signal Temporal Logic for Precise Specifications for Action Generation with Vision Language Models](https://arxiv.org/abs/2607.18580)** — `VLA` · 2026-07-23
  - _首次將 Signal Temporal Logic（STL）作為統一形式化接口嵌入VLA全棧——從語言解析、子任務約束生成、低層策略選擇、執行監控到運行時重規劃，實現了自然語言指令中空間+時間+邏輯約束的可驗證、可分解、可修正的端到端閉環，解決了VLA長期存在的「語義漂移」與「執行不可驗證」這一ontology §13核心爭議。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._