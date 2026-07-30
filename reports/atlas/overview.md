# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 669 papers · 2026-07-08 → 2026-07-30 · ⚡ 102 · 🔧 422 · 📖 145

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 45
learned                    ██████████████████████·· 156
hybrid                     ████████████████········ 118
generative                 █████··················· 39
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 173
world-model-as-policy      ██████████·············· 69
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 |
|---|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 8 |
| learned | 37 | 39 | 38 | 42 |
| hybrid | 17 | 37 | 45 | 19 |
| generative | 8 | 13 | 11 | 7 |
| 3R-SLAM-hybrid | · | 3 | 3 | · |
| VLA | 37 | 50 | 52 | 34 |
| world-model-as-policy | 11 | 19 | 18 | 21 |
| **total** | **119** | **174** | **182** | **131** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 107
incremental                ████████················ 95
per-scene                  ████████████████████████ 297
feed-forward               ████···················· 55
temporal-transformer-rolling █████··················· 64
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 152
navigation                 ██████████████████████·· 137
spatial-reasoning          █████████··············· 60
reconstruction             █████████··············· 56
pose                       ████···················· 26
VSLAM                      ███····················· 18
tracking                   ███····················· 16
depth                      ██······················ 15
VIO                        ██······················ 11
mapping                    █······················· 9
SfM                        █······················· 6
VO                         █······················· 5
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 149
scene-graph                ███████████████········· 96
3DGS                       █████████··············· 53
sparse                     ████████················ 51
pointmap                   █████··················· 33
BEV                        ██······················ 15
NeRF                       ██······················ 14
voxel                      ██······················ 14
implicit-sdf               ██······················ 11
mesh                       █······················· 6
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 263
multi-modal                ██████████·············· 111
RGBD                       █████████··············· 104
LiDAR                      ██······················ 19
stereo                     █······················· 12
event                      █······················· 10
IMU                        █······················· 8
4D-radar                   ························ 5
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[VLASH: Real-Time VLAs via Future-State-Aware Asynchronous Inference](https://arxiv.org/abs/2512.01031)** — `VLA` · 2026-07-30
  - _首次將 asynchronous inference 與 future-state-aware roll-forward 結合，使 VLA 在 temporal misalignment 下仍保持動作穩定性與精度，開創 'VLA-as-continuous-control' 新範式，解了 ontology §13 中長期懸而未決的「動態環境下 VLA 時序一致性」問題。_
- **[VisualPatchWorld: Code World Models as Latent Structured Representations for Planning](https://arxiv.org/abs/2607.25236)** — `world-model-as-policy` · 2026-07-30
  - _首次將世界模型實例化為可執行、可檢視、可編輯的**程式碼級潛在結構化表示**（而非向量或物理引擎），並透過主動探針選擇定性動力學形式——這在 ontology §13 中解決了「可解釋性 vs. 可學習性」的長期根本張力，開闢 paradigm 軸上全新的 'code-as-world-model' 方法論。_
- **[Temporal-Distance JEPA: Plan-Aware Representation Learning for Latent World Model Predictive Control](https://arxiv.org/abs/2607.25337)** — `world-model-as-policy` · 2026-07-30
  - _首次將JEPA範式從無向嵌入距離升級為可學習、目標導向的有向時間距離（temporal distance），在paradigm軸上實現world-model-as-policy與representation learning的耦合閉環： mined temporal cost既是規劃器的即時成本函數，又是反饋驅動的表徵學習信號，解決了長期存在的‘預測≠規劃’鴻溝（ontology §13.2）。_
- **[HiFi-UMI: Learning Deployable Manipulation Policies from High-Fidelity UMI Data Alone](https://arxiv.org/abs/2607.25895)** — `VLA` · 2026-07-30
  - _首次實現純 robot-free UMI 數據驅動的 zero-robot post-training 部署——解除了 Spatial AI 中長期存在的「真實機器人錨點依賴」這一 ontology §13 核心爭議，開闢了 spatially-grounded VLA 訓練的全新 data-centric 軸。_
- **[DC-WAM: Dynamic-Centric Visual Supervision and Reasoning for World-Action Models](https://arxiv.org/abs/2607.25918)** — `world-model-as-policy` · 2026-07-30
  - _首次將 WAM 的視覺監督從 appearance-centric 光度重建範式，轉向 dynamic-centric、action-grounded 的時空變化建模，並透過 DynaRoute 實現 token-level 動態相關性路由——這在 ontology §13 中解了「如何讓世界模型的視覺表徵內生對齊動作因果」這一長期未量化爭議，開闢了 paradigm 軸上 'world-model-as-policy' 與 'dynamic-aware visual reasoning' 的耦合新路徑。_
- **[Pictura: Perspective-View Self-Play at Scale for Driving](https://arxiv.org/abs/2607.26005)** — `world-model-as-policy` · 2026-07-30
  - _首次實現純視角圖像輸入（無任何privileged state）的大規模多智能體自博弈駕駛訓練範式，將self-play從vectorized-observation paradigm徹底遷移至 world-model-as-policy paradigm，解決了長期存在的‘感知-決策表徵鴻溝’這一ontology §13核心爭議。_
- **[$\pi\mathbf{R}^2$: Reactive Real-time Flow Policies](https://arxiv.org/abs/2607.26055)** — `generative` · 2026-07-30
  - _首次將 diffusion flow policy 的 denoising 調度解耦為 latency-adaptive 動態 inpainting 機制，並在 paradigm 軸上開創 'flow-policy-as-real-time-control' 新範式，使大模型驅動的多動作 chunking 政策具備毫秒級感官反饋閉環能力（此前所有 VLA/flow policies 均為 open-loop 或固定步長 replanning）。_
- **[INTACT: Isomorphic Intent-to-Action Learning for Search-Free World Models](https://arxiv.org/abs/2607.26056)** — `world-model-as-policy` · 2026-07-30
  - _首創 'intent-to-action' 范式：以等變語法（isomorphic grammar）與動作律語義（action-law semantics）取代傳統 latent matching 或全局線性動力學，實現零搜索、端到端可部署的 world model 控制接口，解開長期困擾 forward world models 的 'inverse control bottleneck'。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._