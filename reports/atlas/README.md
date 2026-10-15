# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3170 papers · 2026-07-08 → 2026-10-15 · ⚡ 264 · 🔧 1857 · 📖 1049

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 192
learned                    █████████████████······· 580
hybrid                     █████████████··········· 428
generative                 █████··················· 180
3R-SLAM-hybrid             ························ 12
VLA                        ████████████████████████ 796
world-model-as-policy      █████████··············· 303
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W35 | W36 | W37 | W38 | W39 | W40 | W41 | W42 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 14 | 16 | 12 | 31 | 28 | 13 | 13 | 3 |
| learned | 41 | 55 | 45 | 57 | 50 | 51 | 50 | 17 |
| hybrid | 35 | 51 | 22 | 41 | 44 | 38 | 34 | 10 |
| generative | 12 | 24 | 18 | 20 | 18 | 13 | 11 | 12 |
| 3R-SLAM-hybrid | 1 | 1 | · | · | · | 1 | · | 1 |
| VLA | 57 | 55 | 37 | 83 | 95 | 96 | 87 | 39 |
| world-model-as-policy | 26 | 19 | 12 | 31 | 38 | 28 | 28 | 15 |
| **total** | **186** | **221** | **146** | **263** | **273** | **240** | **223** | **97** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████████·········· 387
fixed-lag                  █······················· 16
incremental                ████████████············ 311
per-scene                  ████████████████████████ 647
feed-forward               ██████████████████████·· 597
temporal-transformer-rolling ██████████████·········· 366
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 934
navigation                 ████████████············ 461
spatial-reasoning          ██████·················· 250
reconstruction             █████··················· 203
pose                       ███····················· 130
tracking                   ██······················ 74
mapping                    █······················· 55
VSLAM                      █······················· 48
depth                      █······················· 39
VIO                        █······················· 39
occupancy                  ························ 14
SfM                        ························ 11
VO                         ························ 9
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 651
scene-graph                ██████████·············· 271
pointmap                   ███████················· 185
3DGS                       ██████·················· 153
sparse                     ██████·················· 153
mesh                       ███····················· 72
BEV                        ███····················· 70
voxel                      ██······················ 47
implicit-sdf               █······················· 31
NeRF                       █······················· 30
HD-map                     ························ 10
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 967
multi-modal                █████████████████······· 666
RGBD                       ███████················· 298
LiDAR                      ██······················ 68
event                      █······················· 36
stereo                     █······················· 27
IMU                        █······················· 24
4D-radar                   ························ 18
sonar                      ························ 7
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[World-T3: Test-Time Training as Persistent Memory for Real-Time Video World Models](https://arxiv.org/abs/2610.17434)** — `generative` · 2026-10-15
  - _在世界模型記憶這條軸上開新範式：用 test-time training 的 fast-weight 參數（pose-keyed 遞迴最小二乘在線更新）取代依賴 context 的隱式記憶，做到 rollout 長度無關的常數儲存與常數每步計算，解決了既有自回歸世界模型長時程空間記憶衰減的既有做不到之事。_
- **[Into the LidarVerse: A Real-Time Unified LiDAR World Model Across Tasks and Sensors](https://arxiv.org/abs/2610.19201)** — `generative` · 2026-10-15
  - _首個把 reconstruction-based 與 generative 兩條原本互斥的 LiDAR 模擬範式融進單一 conditional generative framework：以 universal tokenizer 共用 latent，靠「可用的場景證據」在多任務（new-world generator / point-cloud forecaster / resimulator）間切換，並泛化到未見掃描模式、支援 32/64/128-beam，開了一條「統一條件生成式 LiDAR 世界模型」的新方法軸。_
- **[Robota-Embed: Unified VLA Embeddings for Robot In-Context Learning and Evolution](https://arxiv.org/abs/2610.19495)** — `VLA` · 2026-10-15
  - _首個把視覺—語言—動作三模態同時編碼進『當前查詢』與『未來延續』的 VLA 檢索嵌入，開出「以原生動作嵌入檢索歷史經驗做 in-context 策略調控」這條新軸——既有 action-free 檢索嵌入做不到（去動作掉點遠多於去視覺），且在凍結策略上用執行回饋增量演化記憶。_
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

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._