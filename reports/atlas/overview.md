# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4233 papers · 2026-07-08 → 2026-11-04 · ⚡ 331 · 🔧 2698 · 📖 1204

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 268
learned                    ███████████████████····· 885
hybrid                     █████████████··········· 587
generative                 ██████·················· 258
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1124
world-model-as-policy      █████████··············· 413
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W38 | W39 | W40 | W41 | W42 | W43 | W44 | W45 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 31 | 28 | 13 | 13 | 8 | 18 | 24 | 11 |
| learned | 56 | 50 | 51 | 50 | 26 | 84 | 76 | 28 |
| hybrid | 41 | 44 | 38 | 34 | 17 | 60 | 30 | 23 |
| generative | 20 | 18 | 13 | 11 | 13 | 24 | 8 | 8 |
| 3R-SLAM-hybrid | · | · | 1 | · | 1 | · | · | · |
| VLA | 82 | 95 | 96 | 87 | 65 | 111 | 82 | 41 |
| world-model-as-policy | 31 | 38 | 28 | 28 | 23 | 34 | 23 | 13 |
| **total** | **261** | **273** | **240** | **223** | **153** | **331** | **243** | **124** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 519
fixed-lag                  █······················· 30
incremental                ███████████············· 475
per-scene                  ██████████████████······ 763
feed-forward               ████████████████████████ 998
temporal-transformer-rolling ████████████············ 511
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1400
navigation                 ███████████············· 649
spatial-reasoning          ██████·················· 325
reconstruction             █████··················· 264
pose                       ███····················· 195
tracking                   ██······················ 124
mapping                    █······················· 81
VSLAM                      █······················· 71
depth                      █······················· 52
VIO                        █······················· 52
occupancy                  ························ 20
SfM                        ························ 14
VO                         ························ 11
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 917
scene-graph                █████████··············· 328
pointmap                   ██████·················· 245
sparse                     █████··················· 209
3DGS                       █████··················· 201
mesh                       ███····················· 120
BEV                        ███····················· 101
voxel                      ██······················ 73
implicit-sdf               █······················· 41
NeRF                       █······················· 30
HD-map                     ························ 18
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1360
multi-modal                ██████████████████······ 1008
RGBD                       ███████················· 381
LiDAR                      ██······················ 86
event                      █······················· 41
IMU                        █······················· 40
stereo                     █······················· 36
4D-radar                   ························ 21
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Say the Same, Act Differently: Diagnosing and Steering Text-Action Divergence in Reasoning VLAs](https://arxiv.org/abs/2611.04166)** — `VLA` · 2026-11-04
  - _在 VLA 共享的 text/action 介面上找出與 text-loss 梯度近乎正交的 text-neutral action 子空間（重疊僅 1.87%/5.28%），首次可量化地把「rationale 逐字不變」與「動作被改寫」解耦，直接推翻「可讀 rationale 可作為具身安全監控」的既有假設，開出 rationale 忠實性診斷/操控這條新軸（非既有攻擊把 rationale 弄髒的做法）。_
- **[Future Representation Distillation for Imagination-Free World Action Models](https://arxiv.org/abs/2611.04527)** — `world-model-as-policy` · 2026-11-04
  - _把「世界模型必須生成未來影片」這條軸翻轉為「只從當前觀測單步蒸餾凍結影片擴散模型之未來表徵」，讓 WAM 免去迭代去噪與視覺預測誤差傳播，14B 骨幹仍達 11Hz 實時閉環、並可用無動作標註的跨具身影片學新任務——這是 WAM 推論機制（pixel-generation → representation-level prediction）的範式級改道，而非應用套殼。_
- **[PrimeSim: A Generalist World Model Simulator from Large-Scale Cross-Embodiment Demonstrations](https://arxiv.org/abs/2611.04870)** — `generative` · 2026-11-04
  - _首個跨 22 平台、3 萬小時示範的通用多視角 action-conditioned 世界模型模擬器：以統一跨本體 action 表徵＋顯式相機身份的 view-aware interleaved attention 解掉「指令跟隨／多視角一致」，再以 fast-video/slow-memory 後訓練（因果自回歸＋self-rollout＋階層時序記憶）把雙向視頻生成器轉成可長時穩定滾動的模擬器，並能在 100–200 步內轉移到未見平台——這是既有 video world model 做不到的新能力軸（通用跨本體長時一致模擬）。_
- **[Do Agentic Policies Need to Look at Every Step? Geometric Abstraction for Reasoning and Action](https://arxiv.org/abs/2611.05058)** — `VLA` · 2026-11-04
  - _新軸：以 RGB-D grounding 的 typed evidence-aware 3D symbolic abstraction 作為語言模型可讀的幾何狀態，把 routine spatial reasoning 從每步重讀影像改成可重用符號結構＋metric residual 局部重綁、僅按需視覺推理，對「agentic policy 是否每步都要看原始觀測」給出可量化解法。_
- **[CausalWAM: Learning the Causes of Actions in World Action Models](https://arxiv.org/abs/2610.42096)** — `world-model-as-policy` · 2026-11-02
  - _在 world action model 上引入稀疏路由的可識別性理論，證明 action head 僅依賴 action-relevant latent causes（可識別到 permutation），无需时序依赖假设，开辟了 WAM 中 causal-identifiability 的新方法轴。_
- **[RoboArchitect: Automating the Design of Robotic Agents with Persistent Memory](https://arxiv.org/abs/2610.42141)** — `VLA` · 2026-11-02
  - _首次把「agent harness（控制代碼＋持久記憶）」本身當作可被 coding model 觀測 rollout、診斷失敗並迭代演化的搜尋對象，而非微調 policy 權重——開了『自動設計 agent 架構而非策略』這條新軸，並讓記憶隨演化累積（如抓取深度經驗）遷移到新場景。_
- **[ELEVATE: Agentic Controller Acquisition from Task Failure for Quadrupedal Manipulation](https://arxiv.org/abs/2610.38388)** — `VLA` · 2026-10-30
  - _把「任務失敗訊號→偵測能力缺口→coding agent 自動設計並精煉 RL 問題（reward/curriculum/termination）→驗證後併入能力庫再組合重試」閉環打通，使 agent 的動作空間可自我擴張而非受限於固定控制器庫，是既有 VLA/任務規劃 agent 做不到的新方法軸，且免真機訓練零樣本遷移到四足機械臂。_
- **[E0.5: From Reconstructive to Future-Predictive 3D Foundations for Robotic World-Action Modeling](https://arxiv.org/abs/2610.36011)** — `world-model-as-policy` · 2026-10-28
  - _⚡：把 3D 基礎模型由輔助特徵/重建目標提升為 world-action 模型的原生主幹，並聯合預測未來 3D 狀態與動作，開出 geometry-native 世界建模新軸。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._