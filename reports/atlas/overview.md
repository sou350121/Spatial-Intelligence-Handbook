# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3990 papers · 2026-07-08 → 2026-10-27 · ⚡ 318 · 🔧 2505 · 📖 1167

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 245
learned                    ███████████████████····· 817
hybrid                     █████████████··········· 550
generative                 ██████·················· 249
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1046
world-model-as-policy      █████████··············· 386
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W37 | W38 | W39 | W40 | W41 | W42 | W43 | W44 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 12 | 31 | 28 | 13 | 13 | 8 | 18 | 12 |
| learned | 45 | 56 | 50 | 51 | 50 | 26 | 84 | 36 |
| hybrid | 22 | 41 | 44 | 38 | 34 | 17 | 60 | 16 |
| generative | 18 | 20 | 18 | 13 | 11 | 13 | 24 | 7 |
| 3R-SLAM-hybrid | · | · | · | 1 | · | 1 | · | · |
| VLA | 37 | 82 | 95 | 96 | 87 | 65 | 111 | 44 |
| world-model-as-policy | 12 | 31 | 38 | 28 | 28 | 23 | 34 | 9 |
| **total** | **146** | **261** | **273** | **240** | **223** | **153** | **331** | **124** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 485
fixed-lag                  █······················· 25
incremental                ████████████············ 435
per-scene                  ████████████████████···· 737
feed-forward               ████████████████████████ 898
temporal-transformer-rolling █████████████··········· 490
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1288
navigation                 ███████████············· 603
spatial-reasoning          ██████·················· 311
reconstruction             █████··················· 255
pose                       ███····················· 177
tracking                   ██······················ 114
mapping                    █······················· 76
VSLAM                      █······················· 68
depth                      █······················· 51
VIO                        █······················· 48
occupancy                  ························ 19
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 855
scene-graph                █████████··············· 317
pointmap                   ███████················· 234
sparse                     ██████·················· 197
3DGS                       █████··················· 193
mesh                       ███····················· 113
BEV                        ███····················· 95
voxel                      ██······················ 61
implicit-sdf               █······················· 39
NeRF                       █······················· 30
HD-map                     ························ 14
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1281
multi-modal                █████████████████······· 925
RGBD                       ███████················· 364
LiDAR                      █······················· 80
event                      █······················· 38
IMU                        █······················· 37
stereo                     █······················· 33
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[One Scan is Enough: Demonstration-Free Adaptation for Language-Guided Navigation](https://arxiv.org/abs/2610.33794)** — `VLA` · 2026-10-27
  - _將「新場景需人體遠端示範」的擴展瓶頸換成單支 iPhone 掃描→合成 grounded 導航 episode＋封閉式 Pareto 自適應（無 learned critic、無標籤），並以 82% vs 41% 量化證明掃描式自適應可泛化到未掃描區域，開了一條 demonstration-free 真實場景適配的新方法軸。_
- **[WAM-TTT: Steering World-Action Models by Watching Human Play at Test Time](https://arxiv.org/abs/2607.06988)** — `world-model-as-policy` · 2026-10-26
  - _開了一條測試時記憶轉向（test-time training）的新軸：把原始人類影片以自監督視頻預測吸收進凍結世界-動作模型內的輕量 KV 記憶，並用配對人-機數據元訓練對齊，首次做到無機器人動作、無標註、無微調即可將 RFM 轉向新任務變體，解了以往必須額外示範或 fine-tune 才能適應的行為轉向問題。_
- **[Do VLAs Know They Will Fail? Interpretable Success and Failure Patterns in Physical AI Systems](https://arxiv.org/abs/2610.32208)** — `VLA` · 2026-10-26
  - _首次證明 VLA（OpenVLA）動作模型的 SAE 稀疏激活本身攜帶「結果可預測」訊號，能在機器人進入不可逆狀態前於內部特徵層做失敗預測，並把特徵激活變化定位到具體行為階段、用 VLM 產生可驗證的行為描述——開的是「VLA 內省/可監控表徵」這條新軸，而非再刷一個策略指標。_
- **[ViT-H: Generative Video-To-Humanoid Control with Motion Tracking Feedback](https://arxiv.org/abs/2610.32966)** — `generative` · 2026-10-26
  - _以 diffusion 直接從影片生成人形參考動作，並用下游追蹤結果做 DPO 後訓練，繞過 reconstruction-retargeting 管線，讓 reference motion 的可執行性首次成為可直接優化的目標，開出 generation-and-tracking 新軸。_
- **[UniFlowWAM: A Unified World-Action Model with Visual Semantics and 4D Geometry](https://arxiv.org/abs/2610.30991)** — `world-model-as-policy` · 2026-10-23
  - _把 3D scene flow 從「旁路模組／額外預測頭」升格為與視覺、動作對等的第三模態，用模態對稱 diffusion transformer（每模態一 expert + joint attention）配合十種 target/condition/absent 角色網格，讓同一模型同時當 policy、前向／逆向動力學與未來特徵／4D 流預測器——開了一條「幾何流作為 policy 內生模態」的世界-動作模型軸，而非又在既有 VLA 上加一個輔助 head。_
- **[Inside-JEPA: From Prediction to Relational Grounding in Latent World Models](https://arxiv.org/abs/2610.31194)** — `world-model-as-policy` · 2026-10-23
  - _在 JEPA 潛在狀態內嵌入「有序實體對關係通道」，並證明 inverse-dynamics 損失可在無關係標註下把這些通道接地——開了一條「讓世界模型潛在狀態可關係化/可解釋」的新軸，給長期存在的 JEPA 狀態不透明問題一個可量化解（AUROC +0.05~0.10、top-5 動作排序 43% vs 24%），非單純應用或刷 SOTA。_
- **[Feedback World Model Enables Precise Guidance of Diffusion Policy](https://arxiv.org/abs/2605.15705)** — `world-model-as-policy` · 2026-10-22
  - _把世界模型從開環 rollout 預測器改造成推理期帶在線回饋狀態的閉環預測器（latent-space observer，具收斂保證、無需重訓），開了一條「test-time 自適應 world model 校正」的新方法軸，直接解掉 OOD 漂移下開環預測不可用的既有問題。_
- **[Let It Be Simple: One-Step Action Generation for Vision-Language-Action Models](https://arxiv.org/abs/2606.05737)** — `VLA` · 2026-10-22
  - _首度以 condition-target 資訊不對稱（Flow-Matching irreducible velocity loss R_v(t,c) 的端點塌縮 + 生成映射對初始噪聲的 Jacobian 最大奇異值遠小）量化說明「一步生成不可行」這條既有邊界只屬 text-to-image、不屬 VLA，並據此免蒸餾取得單步策略——開的是「生成式解碼步數由條件-目標結構決定」這條新分析軸，而非又一個 VLA 應用。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._