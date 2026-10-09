# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3071 papers · 2026-07-08 → 2026-10-09 · ⚡ 259 · 🔧 1790 · 📖 1022

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 189
learned                    ██████████████████······ 563
hybrid                     █████████████··········· 418
generative                 █████··················· 168
3R-SLAM-hybrid             ························ 11
VLA                        ████████████████████████ 757
world-model-as-policy      █████████··············· 288
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W33 | W35 | W36 | W37 | W38 | W39 | W40 | W41 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 1 | 14 | 16 | 12 | 31 | 28 | 13 | 13 |
| learned | 11 | 41 | 55 | 45 | 57 | 50 | 51 | 50 |
| hybrid | 8 | 35 | 51 | 22 | 41 | 44 | 38 | 34 |
| generative | 3 | 12 | 24 | 18 | 20 | 18 | 13 | 11 |
| 3R-SLAM-hybrid | 1 | 1 | 1 | · | · | · | 1 | · |
| VLA | 16 | 57 | 55 | 37 | 83 | 95 | 96 | 87 |
| world-model-as-policy | 7 | 26 | 19 | 12 | 31 | 38 | 28 | 28 |
| **total** | **47** | **186** | **221** | **146** | **263** | **273** | **240** | **223** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████████·········· 375
fixed-lag                  █······················· 16
incremental                ███████████············· 304
per-scene                  ████████████████████████ 636
feed-forward               █████████████████████··· 560
temporal-transformer-rolling █████████████··········· 351
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 883
navigation                 ████████████············ 443
spatial-reasoning          ███████················· 241
reconstruction             █████··················· 197
pose                       ███····················· 126
tracking                   ██······················ 71
mapping                    █······················· 54
VSLAM                      █······················· 47
depth                      █······················· 39
VIO                        █······················· 38
occupancy                  ························ 14
SfM                        ························ 11
VO                         ························ 8
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 628
scene-graph                ██████████·············· 265
pointmap                   ███████················· 179
3DGS                       ██████·················· 149
sparse                     ██████·················· 147
mesh                       ███····················· 70
BEV                        ███····················· 68
voxel                      ██······················ 46
implicit-sdf               █······················· 30
NeRF                       █······················· 30
HD-map                     ························ 9
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 927
multi-modal                █████████████████······· 640
RGBD                       ████████················ 290
LiDAR                      ██······················ 66
event                      █······················· 36
stereo                     █······················· 26
IMU                        █······················· 22
4D-radar                   ························ 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

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
- **[FoldBack: Self-Correcting Masked Generative Policy for Long-Horizon Garment Folding](https://arxiv.org/abs/2610.10462)** — `generative` · 2026-10-08
  - _首個『可編輯全軌跡生成策略』，把 refine/rollback/retry 三個推理時決策統一起來，能在不重訓基策略、不需失敗示範下偵測—回退—修復失敗抓取，開出『長程策略可回滾/可編輯』這條此前不存在的新方法軸。_
- **[SpaTime: Streaming Vision-Language Models for Spatio-temporal Reasoning](https://arxiv.org/abs/2610.08713)** — `VLA` · 2026-10-07
  - _首度把因果幾何 token 融進串流 VLM，並用可微期望回應時間損失讓模型自學「何時已回答足夠」，開出「串流 3D 空間推理 × 自適應回應時機」這條先前不存在的軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._