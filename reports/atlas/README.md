# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3125 papers · 2026-07-08 → 2026-10-12 · ⚡ 261 · 🔧 1832 · 📖 1032

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 192
learned                    ██████████████████······ 570
hybrid                     █████████████··········· 424
generative                 █████··················· 173
3R-SLAM-hybrid             ························ 11
VLA                        ████████████████████████ 781
world-model-as-policy      █████████··············· 295
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W35 | W36 | W37 | W38 | W39 | W40 | W41 | W42 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 14 | 16 | 12 | 31 | 28 | 13 | 13 | 3 |
| learned | 41 | 55 | 45 | 57 | 50 | 51 | 50 | 7 |
| hybrid | 35 | 51 | 22 | 41 | 44 | 38 | 34 | 6 |
| generative | 12 | 24 | 18 | 20 | 18 | 13 | 11 | 5 |
| 3R-SLAM-hybrid | 1 | 1 | · | · | · | 1 | · | · |
| VLA | 57 | 55 | 37 | 83 | 95 | 96 | 87 | 24 |
| world-model-as-policy | 26 | 19 | 12 | 31 | 38 | 28 | 28 | 7 |
| **total** | **186** | **221** | **146** | **263** | **273** | **240** | **223** | **52** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████████·········· 382
fixed-lag                  █······················· 16
incremental                ████████████············ 309
per-scene                  ████████████████████████ 643
feed-forward               ██████████████████████·· 583
temporal-transformer-rolling █████████████··········· 355
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 914
navigation                 ████████████············ 457
spatial-reasoning          ██████·················· 245
reconstruction             █████··················· 197
pose                       ███····················· 128
tracking                   ██······················ 72
mapping                    █······················· 54
VSLAM                      █······················· 47
depth                      █······················· 39
VIO                        █······················· 39
occupancy                  ························ 14
SfM                        ························ 11
VO                         ························ 8
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 640
scene-graph                ██████████·············· 270
pointmap                   ███████················· 182
3DGS                       ██████·················· 152
sparse                     ██████·················· 150
mesh                       ███····················· 70
BEV                        ███····················· 70
voxel                      ██······················ 46
implicit-sdf               █······················· 31
NeRF                       █······················· 30
HD-map                     ························ 10
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 948
multi-modal                █████████████████······· 653
RGBD                       ███████················· 295
LiDAR                      ██······················ 67
event                      █······················· 36
stereo                     █······················· 27
IMU                        █······················· 22
4D-radar                   ························ 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[VLMs are Native Action Models: Unleashing the Manipulation Capabilities of VLMs with Explicit Action-Space Grounding](https://arxiv.org/abs/2610.12832)** — `VLA` · 2026-10-12
  - _EASG 把 TCP 動作框投影進腕部相機觀測、並用 VLM 原生文字生成介面表達連續動作，使未經機器人資料預訓練、亦無 action token/head 模組的預訓練 VLM 能零樣本直接輸出可執行操作動作——在「VLA 動作介面」這條軸上開出新範式，同時解掉模組化零樣本方法需外部規劃控制腳手架、無法端到端連續動作的既有痛點。_
- **[Forward Dynamics Models](https://arxiv.org/abs/2610.13117)** — `VLA` · 2026-10-12
  - _提出 action-to-future 新方法軸：以動作特徵為條件預測未來世界狀態，未來預測僅在訓練時經特徵監督策略、推論時完全跳過生成，解決了 WAM 推論成本與視覺誤差傳入動作、VLA 缺乏未來狀態監督的兩難。_
- **[NavGPT-3: Harnessing Context in a Hierarchical Navigation Runtime](https://arxiv.org/abs/2610.10787)** — `VLA` · 2026-10-09
  - _開了一條新方法軸：以 OS 式 runtime 將推理 LLM 與低延遲 VLA 策略以多執行緒（推理/行動/監控、含搶佔與執行緒切換）調度，讓機器人能中途打斷並切換控制權以回應突發事件——這是既有單一 policy 或單一 LLM-planner 都做不到的能力，並首次在 RxR-CE 把自主導航代理推到人類水準。_
- **[Cross-Embodiment Robot Foundation World Models with Latent Actions](https://arxiv.org/abs/2610.10846)** — `world-model-as-policy` · 2026-10-09
  - _新在「跨 embodiment 的統一 latent action 空間」這條軸，解了 explicit action conditioning 導致 action representation 跨 embodiment 分裂、無法隨 pretraining embodiment 數量正向擴展的既有問題。_
- **[Acting from Belief, Looking When Needed: A Bayesian Spatial World Model for Navigation under Intermittent Perception](https://arxiv.org/abs/2610.11591)** — `world-model-as-policy` · 2026-10-09
  - _開了一條新方法軸：以「信念可靠度圖」閘控何時重新觀測，讓導航在間歇感知（感測器被其他任務共用）下幾乎全程從內部空間信念行動，僅約 1% 決策步需取新觀測——此為既有主動感知/世界模型未提供的能力。_
- **[UNITAS: A 3D-Native World Action Model for Embodied Manipulation](https://arxiv.org/abs/2610.12099)** — `world-model-as-policy` · 2026-10-09
  - _首個 3D-native world action model：把 world action model 的世界演化表徵從 2D 影片/視覺 latent 換成共享 metric 空間的 3D point-trajectory flow（action flow + scene flow），並以 world-aligned 3D positional embedding 與 physical-time trajectory tokenizer 打通跨 embodiment 的動作與場景預測，開出 WAM 的 3D-native 這條新方法軸，具體解掉像素距離不編碼物理距離的既有缺陷。_
- **[PhysEvo: Astra Can Act, Let It](https://arxiv.org/abs/2610.08995)** — `VLA` · 2026-10-08
  - _開了一條『物理遞歸自我改進』新方法軸：以 meta-agent 對凍結 VLA 的工具/技能/診斷器做持續且可測試的修訂（無權重更新、無另訓 policy），把直連 Astra 幾乎做不到的操控（1.25%→55%）變成可行。_
- **[Co-Evolving Robot Orchestrators and Policies through Deployment](https://arxiv.org/abs/2610.09228)** — `VLA` · 2026-10-08
  - _首次讓 VLM orchestrator 與 VLA policy 在部署中共同演化（以驗證式採納把關），開啟「部署即自我改進飛輪」這條新方法軸，突破了既有 orchestrator 只能繞過、無法克服 frozen-policy 失敗的根本瓶頸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._