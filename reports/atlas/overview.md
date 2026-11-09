# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4417 papers · 2026-07-08 → 2026-11-09 · ⚡ 341 · 🔧 2848 · 📖 1228

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 288
learned                    ███████████████████····· 940
hybrid                     ████████████············ 612
generative                 ██████·················· 271
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1178
world-model-as-policy      █████████··············· 430
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W39 | W40 | W41 | W42 | W43 | W44 | W45 | W46 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 28 | 13 | 13 | 8 | 18 | 24 | 23 | 8 |
| learned | 50 | 51 | 50 | 26 | 84 | 76 | 67 | 16 |
| hybrid | 44 | 38 | 34 | 17 | 60 | 30 | 39 | 9 |
| generative | 18 | 13 | 11 | 13 | 24 | 8 | 14 | 8 |
| 3R-SLAM-hybrid | · | 1 | · | 1 | · | · | · | · |
| VLA | 95 | 96 | 87 | 65 | 111 | 82 | 75 | 21 |
| world-model-as-policy | 38 | 28 | 28 | 23 | 34 | 23 | 29 | 2 |
| **total** | **273** | **240** | **223** | **153** | **331** | **243** | **247** | **64** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 548
fixed-lag                  █······················· 33
incremental                ███████████············· 493
per-scene                  ██████████████████······ 783
feed-forward               ████████████████████████ 1073
temporal-transformer-rolling ████████████············ 535
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1481
navigation                 ███████████············· 673
spatial-reasoning          █████··················· 339
reconstruction             ████···················· 276
pose                       ███····················· 211
tracking                   ██······················ 134
mapping                    █······················· 84
VSLAM                      █······················· 74
depth                      █······················· 56
VIO                        █······················· 56
occupancy                  ························ 20
SfM                        ························ 14
VO                         ························ 11
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 979
scene-graph                ████████················ 341
pointmap                   ██████·················· 253
sparse                     █████··················· 223
3DGS                       █████··················· 208
mesh                       ███····················· 127
BEV                        ███····················· 103
voxel                      ██······················ 75
implicit-sdf               █······················· 44
NeRF                       █······················· 30
HD-map                     ························ 19
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1426
multi-modal                ██████████████████······ 1073
RGBD                       ███████················· 394
LiDAR                      █······················· 87
event                      █······················· 43
IMU                        █······················· 42
stereo                     █······················· 39
4D-radar                   ························ 22
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[ODEAction: From Predicting Chunks to Evolving Actions](https://arxiv.org/abs/2611.09672)** — `VLA` · 2026-11-09
  - _沿「動作生成」軸開新範式：以動作空間上的學習式轉移場 + ODE 積分取代 action-chunk 預測，從機制上消除 chunk 邊界不連續，且可作為 backbone-agnostic action head 插拔——這不是把既有 VLA 套新場景，而是換掉動作解碼這一環。_
- **[On Agentic Manipulation Policies](https://arxiv.org/abs/2611.09892)** — `VLA` · 2026-11-09
  - _把 policy 軸從 learned specialist（VLA / world-action model）翻轉為「通用基礎模型即控制器」的 agent-as-policy：同一 harness 不經任務訓練、不需 demo 即可跨單臂/雙臂/移動平台零樣本操作，並以 RoboLab-120 85.6% vs 49.2%/42.9% 與真機 104/108 的量化差距，給「是否還需要 specialist robot policy」這個長期爭議一個可檢驗的答案；再加 persistent memory 把跨 episode 經驗學習變成 4.6x 失效率的可量化槓桿。_
- **[Concertina: Embodying Manipulation and Cognition in One Diffusion Vision-Language Model](https://arxiv.org/abs/2611.07513)** — `VLA` · 2026-11-06
  - _把連續軌跡表示、blockwise 生成與物理座標監督直接放進共享 diffusion VLM backbone（僅 0.21% action 參數、無獨立 action expert），開闢 decoupled VLA → eVLM 的新架構軸，使動作與認知在參數與計算路徑上真正耦合。_
- **[Baba in Wonderland: Online Self-Supervised Dynamics Discovery for Executable World Models](https://arxiv.org/abs/2605.16725)** — `world-model-as-policy` · 2026-11-05
  - _開新方法軸：把候選更新失敗造成的「守恆衝突」本身當作結構信號，在無可信詞彙先驗、無獎勵、無規則描述下誘導可執行動力學，並用衝突切出的假設類反過來引導前沿探索——這是此前需靠語義先驗或獎勵才做得到的動力學發現能力。_
- **[Touch\'{e}World tech report : Towards Online Unified Camera--Hand Exploration in Generative Worlds](https://arxiv.org/abs/2611.06061)** — `world-model-as-policy` · 2026-11-05
  - _把生成式視頻世界模型的行動介面從「純相機導航」擴展到相機＋連續手部動作的聯合時序控制，並用因果化＋少步蒸餾做到 chunk 級在線互動生成——開啟了 world model 動作空間這條新軸（此前無法在生成世界中用手操作物體／人物），非單純換場景的應用。_
- **[Say the Same, Act Differently: Diagnosing and Steering Text-Action Divergence in Reasoning VLAs](https://arxiv.org/abs/2611.04166)** — `VLA` · 2026-11-04
  - _在 VLA 共享的 text/action 介面上找出與 text-loss 梯度近乎正交的 text-neutral action 子空間（重疊僅 1.87%/5.28%），首次可量化地把「rationale 逐字不變」與「動作被改寫」解耦，直接推翻「可讀 rationale 可作為具身安全監控」的既有假設，開出 rationale 忠實性診斷/操控這條新軸（非既有攻擊把 rationale 弄髒的做法）。_
- **[Future Representation Distillation for Imagination-Free World Action Models](https://arxiv.org/abs/2611.04527)** — `world-model-as-policy` · 2026-11-04
  - _把「世界模型必須生成未來影片」這條軸翻轉為「只從當前觀測單步蒸餾凍結影片擴散模型之未來表徵」，讓 WAM 免去迭代去噪與視覺預測誤差傳播，14B 骨幹仍達 11Hz 實時閉環、並可用無動作標註的跨具身影片學新任務——這是 WAM 推論機制（pixel-generation → representation-level prediction）的範式級改道，而非應用套殼。_
- **[PrimeSim: A Generalist World Model Simulator from Large-Scale Cross-Embodiment Demonstrations](https://arxiv.org/abs/2611.04870)** — `generative` · 2026-11-04
  - _首個跨 22 平台、3 萬小時示範的通用多視角 action-conditioned 世界模型模擬器：以統一跨本體 action 表徵＋顯式相機身份的 view-aware interleaved attention 解掉「指令跟隨／多視角一致」，再以 fast-video/slow-memory 後訓練（因果自回歸＋self-rollout＋階層時序記憶）把雙向視頻生成器轉成可長時穩定滾動的模擬器，並能在 100–200 步內轉移到未見平台——這是既有 video world model 做不到的新能力軸（通用跨本體長時一致模擬）。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._