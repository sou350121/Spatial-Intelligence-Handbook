# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3733 papers · 2026-07-08 → 2026-10-21 · ⚡ 301 · 🔧 2303 · 📖 1129

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 226
learned                    ██████████████████······ 742
hybrid                     █████████████··········· 506
generative                 ██████·················· 233
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 965
world-model-as-policy      █████████··············· 364
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W36 | W37 | W38 | W39 | W40 | W41 | W42 | W43 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 16 | 12 | 31 | 28 | 13 | 13 | 8 | 11 |
| learned | 55 | 45 | 56 | 50 | 51 | 50 | 26 | 45 |
| hybrid | 51 | 22 | 41 | 44 | 38 | 34 | 17 | 32 |
| generative | 24 | 18 | 20 | 18 | 13 | 11 | 13 | 15 |
| 3R-SLAM-hybrid | 1 | · | · | · | 1 | · | 1 | · |
| VLA | 55 | 37 | 83 | 95 | 96 | 87 | 65 | 71 |
| world-model-as-policy | 19 | 12 | 31 | 38 | 28 | 28 | 23 | 20 |
| **total** | **221** | **146** | **262** | **273** | **240** | **223** | **153** | **194** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 450
fixed-lag                  █······················· 23
incremental                ████████████············ 395
per-scene                  █████████████████████··· 706
feed-forward               ████████████████████████ 818
temporal-transformer-rolling █████████████··········· 448
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1168
navigation                 ████████████············ 560
spatial-reasoning          ██████·················· 289
reconstruction             █████··················· 243
pose                       ███····················· 164
tracking                   ██······················ 98
mapping                    █······················· 70
VSLAM                      █······················· 61
depth                      █······················· 48
VIO                        █······················· 46
occupancy                  ························ 18
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 791
scene-graph                █████████··············· 298
pointmap                   ███████················· 219
3DGS                       █████··················· 180
sparse                     █████··················· 177
mesh                       ███····················· 105
BEV                        ███····················· 88
voxel                      ██······················ 58
implicit-sdf               █······················· 38
NeRF                       █······················· 30
HD-map                     ························ 12
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1193
multi-modal                █████████████████······· 836
RGBD                       ███████················· 344
LiDAR                      ██······················ 75
event                      █······················· 36
IMU                        █······················· 33
stereo                     █······················· 31
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[DEFLECT: Temporal Counterfactual Preference Learning for Delay-Robust Asynchronous VLAs](https://arxiv.org/abs/2605.19294)** — `VLA` · 2026-10-21
  - _用離線軌跡中才可見的 execution-time 觀測與 prediction-time 觀測構成 temporal counterfactual 對比，轉為 preference 監督，開了一條「以對比未來狀態監督動作再對齊」的新監督軸，解了既有 training-time 改輸入/目標與 runtime repair 都做不到的預測-執行狀態錯配問題。_
- **[Flow Control: Steering Vision-Language-Action Models with Simple Real-Time Inputs](https://arxiv.org/abs/2606.10180)** — `VLA` · 2026-10-21
  - _首創在凍結 VLA 的 flow-matching 動作專家初始條件寫入即時人類輸入，無需重訓即可在推論期沿新控制軸兼顧意圖保真與策略一致性，解決既有 VLA 只能被動執行或需微調才能接受外部 steer 的限制。_
- **[Quantum-JEPA: Quantum Born Priors for Latent-Action JEPA World Models](https://arxiv.org/abs/2610.27921)** — `generative` · 2026-10-21
  - _首創以 conditional quantum Born prior 作為 latent-action 分佈，讓 JEPA 世界模型以多項式參數產生相關多模態未來並避開指數級 categorical head——新軸：量子先驗式世界模型。_
- **[PACT-VLA: Speculative Action-Chunk Verification with Pre-Commit Observations](https://arxiv.org/abs/2610.28019)** — `VLA` · 2026-10-21
  - _把 VLA 異步推理的延遲窗口當成「驗證時間」，用 pre-commit 較新觀測對候選 action chunk 做選擇，並以凍結策略自身的 flow 殘差（FlowRes）當評分器、無需額外 verifier 且零額外控制步延遲——開了一條 inference-time speculative chunk verification 的新方法軸，正好解掉既有候選法「用過時觀測排序」與「執行中切換造成動作不連續」的二選一困局。_
- **[Reasoning as a Distribution: Generative Plan Latents for Vision-Language-Action Models](https://arxiv.org/abs/2610.28166)** — `VLA` · 2026-10-21
  - _把 VLA 的推理狀態從單一承諾改寫為可定址的低維條件分佈（plan latent），解鎖了既有的點估計推理做不到的能力——不重訓即可採樣／請求式轉向／依部署結果重加權，且用「原生動作分佈同樣加引導無效」的對照把增益歸因於 plan 層（轉向命中 0.48→0.94），開出『可定址推理表徵』這條新方法軸。_
- **[Physical Canvas: A Vision Tactile World Model For Robot Policy Evaluation And Learning](https://arxiv.org/abs/2610.28613)** — `world-model-as-policy` · 2026-10-21
  - _把觸覺影像、marker 位移與多視角 RGB 統一進同一個 video VAE/生成骨幹，開出「視覺-觸覺一體化生成式世界模型」這條新模態軸，並用 Scene/Modality/State 三個凍結獎勵模型做一致性後訓練，解掉「視覺似真卻誤表接觸動力學」這個以往世界模型做不到的失效，並直接支撐閉環策略評估與 GRPO 更新。_
- **[Joints, Camera, Action! Co-Generating 3D Motion and Video for Arbitrary Rigs](https://arxiv.org/abs/2610.28632)** — `generative` · 2026-10-21
  - _把 3D 動作從影片的像素中解放出來：用獨立、支援任意骨架（含機器人 rig）的動作模型，經少量 cross-attention 接到預訓練影片模型，並透過學到的關節在畫面中定位反解相機，首次讓生成的影片動作回傳成可重播、已對齊場景座標的 3D 動作——開了「任意 rig 動作 + 影片共同生成 + 相機註冊」這條此前只有 human-only 或 2D 三角化能做到的新軸。_
- **[Online World Modeling Enables Real-World Inverse Reinforcement Learning from Observation](https://arxiv.org/abs/2602.24121)** — `world-model-as-policy` · 2026-10-20
  - _首個在真實世界僅憑任務觀測（video）從零學會視覺操作的 IRLfO 方法：以線上世界模型取代獎勵設計、模擬器建模與動作監督三項瓶頸，40 分鐘內將 pick-and-place 訓練到 82%（同等預算下 RL 為 0%、BC 為 12%），並首次展示真實世界跨任務的正向線上遷移，開出「無獎勵、無動作標籤的真實世界策略學習」這條新軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._