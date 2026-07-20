# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 375 papers · 2026-07-08 → 2026-07-20 · ⚡ 53 · 🔧 251 · 📖 71

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 30
learned                    █████████████████████··· 90
hybrid                     ████████████████········ 66
generative                 ██████·················· 25
3R-SLAM-hybrid             █······················· 4
VLA                        ████████████████████████ 101
world-model-as-policy      ████████················ 32
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 |
|---|---:|---:|---:|
| geometric | 10 | 13 | 7 |
| learned | 37 | 39 | 14 |
| hybrid | 17 | 38 | 11 |
| generative | 9 | 14 | 2 |
| 3R-SLAM-hybrid | · | 3 | 1 |
| VLA | 38 | 52 | 11 |
| world-model-as-policy | 11 | 19 | 2 |
| **total** | **122** | **178** | **48** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 58
incremental                ████████················ 57
per-scene                  ████████████████████████ 166
feed-forward               █████··················· 37
temporal-transformer-rolling █████··················· 34
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 87
VLA                        ███████████████████████· 82
spatial-reasoning          ████████················ 28
reconstruction             ██████·················· 23
pose                       █████··················· 19
VSLAM                      ████···················· 15
tracking                   ███····················· 10
depth                      ███····················· 10
VIO                        ██······················ 7
SfM                        █······················· 5
mapping                    █······················· 2
occupancy                  ························ 1
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 94
scene-graph                █████████████··········· 50
3DGS                       ████████················ 32
sparse                     ████████················ 32
pointmap                   ████···················· 14
NeRF                       ███····················· 11
BEV                        ██······················ 9
implicit-sdf               █······················· 5
voxel                      █······················· 5
mesh                       █······················· 3
HD-map                     █······················· 2
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 164
multi-modal                ████████················ 54
RGBD                       ███████················· 50
event                      █······················· 9
LiDAR                      █······················· 8
stereo                     █······················· 7
IMU                        ························ 3
4D-radar                   ························ 3
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[MindDrive: A Vision-Language-Action Model for Autonomous Driving via Online Reinforcement Learning](https://arxiv.org/abs/2512.13636)** — `VLA` · 2026-07-20
  - _首度將 VLA 范式從 imitation-based 遷移至 online RL 軸：透過 LLM 兩路 LoRA 分離「語言決策空間」與「動作映射空間」，使 RL 在離散、語義可解釋的 driving decision 軸上進行策略優化，避開連續動作空間探索災難——此前所有 VLA 自駕模型均無法在線更新策略，此為 ontology §13 中「VLA policy adaptability」長期未解問題的可量化、可部署解。_
- **[Generation Models Know Space: Unleashing Implicit 3D Priors for Scene Understanding](https://arxiv.org/abs/2603.19235)** — `generative` · 2026-07-20
  - _首次將預訓練視頻生成模型的隱式3D先驗（非顯式幾何監督）轉化為可提取、可融合、可泛化的Latent World Simulator，開闢'generative-as-geometric-prior'新範式軸，解決MLLM長期存在的空間失明問題且無需3D數據微調。_
- **[GigaWorld-Policy-0.5: A Faster and Stronger WAM Empowered by AutoResearch](https://arxiv.org/abs/2607.13960)** — `world-model-as-policy` · 2026-07-20
  - _首次實現 world-model-as-policy 范式下「訓練時用視覺動態監督、推理時僅輸出動作」的解耦架構，使 WAM 從 video-generation-based 轉為 action-first real-time policy backbone，解決了長期存在的 world model 推理延遲與 closed-loop 控制不可兼得的根本矛盾。_
- **[Think at 5 Hz, Act at 20 Hz: Asynchronous Fast-Slow Vision-Language-Action Inference for Closed-Loop Driving](https://arxiv.org/abs/2607.15621)** — `VLA` · 2026-07-20
  - _首度實現 vision-language-action 推理與控制週期的異步解耦：通過將 LLM 的 KV cache 固化為時序穩態表徵（standing representation），並讓輕量 action expert 在每 tick 單次前向即刻綁定最新觀測與該 cache，從根本上打破 'LLM 推理頻率 < 控制頻率' 的範式枷鎖——此前所有 VLA 驅動系統均被迫降頻或插值，此工作首次使 full-rate closed-loop control 與 foundation-model-level scene reasoning 同時成立。_
- **[SkillNav: Score-Level Skill Intervention for Zero-Shot Object Goal Navigation](https://arxiv.org/abs/2607.15758)** — `VLA` · 2026-07-20
  - _首次提出 score-level skill intervention 軸：在 VLM-based navigation 中跳過 token-level prompting，直接在內部價值圖（curiosity value map）上以零 token 成本進行可組合、分層權威的行為干預，實現跨步驟行為記憶與空間信號（角度/坐標/格點）的內生編碼——此前所有 VLA/embodied navigation 方法均依賴 prompt engineering 或 policy head 微調，無法在不觸發 LLM 推理的情況下動態重權或強制行為。_
- **[Orbis 2: A Hierarchical World Model for Driving](https://arxiv.org/abs/2607.15898)** — `world-model-as-policy` · 2026-07-20
  - _首次提出分層世界模型架構（高階結構預測 + 低階細節生成）並耦合雙階段訓練範式（diffusion forcing 預訓練 + teacher forcing 微調），在 paradigm 軸上實現 'world-model-as-policy' 向 'hierarchical world-model-as-planner' 的範式躍遷，使模型具備跨時空尺度的空間推理與反事實操控能力——此前所有 driving world models 均為單一抽象層、單一時間尺度的 feed-forward 或 autoregressive 序列建模。_
- **[MotuBrain: An Advanced World Action Model for Robot Control](https://arxiv.org/abs/2604.27792)** — `world-model-as-policy` · 2026-07-17
  - _首次實現 world-model-as-policy 范式下的統一多任務架構（policy/world model/video gen/inverse dynamics/joint prediction），且透過共享跨 embodiment 行動表徵與實時閉環 chunked 推理，解決長期存在的「世界模型不可控、可控策略無世界理解」的 ontology §13 核心張力。_
- **[RoboWorld: Fast and Reliable Neural Simulators for Generalist Robot Policy Evaluation](https://arxiv.org/abs/2607.01060)** — `world-model-as-policy` · 2026-07-17
  - _首次將 world-model-as-policy 範式轉向 policy evaluation 場景，並透過 Step Forcing 在 autoregressive video world models 中實現可證實的 long-horizon rollout 可靠性（解決長期存在的 train-test mismatch 導致 rollout 指標失真問題），使 video world model 從生成工具升級為可量化的、與 real-world policy ranking 強對齊的評估儀器。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._