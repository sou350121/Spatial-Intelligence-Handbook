# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 4355 papers · 2026-07-08 → 2026-11-06 · ⚡ 339 · 🔧 2797 · 📖 1219

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 280
learned                    ███████████████████····· 924
hybrid                     █████████████··········· 603
generative                 █████··················· 264
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 1157
world-model-as-policy      █████████··············· 428
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W38 | W39 | W40 | W41 | W42 | W43 | W44 | W45 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 31 | 28 | 13 | 13 | 8 | 18 | 24 | 23 |
| learned | 56 | 50 | 51 | 50 | 26 | 84 | 76 | 67 |
| hybrid | 41 | 44 | 38 | 34 | 17 | 60 | 30 | 39 |
| generative | 20 | 18 | 13 | 11 | 13 | 24 | 8 | 14 |
| 3R-SLAM-hybrid | · | · | 1 | · | 1 | · | · | · |
| VLA | 82 | 95 | 96 | 87 | 65 | 111 | 82 | 75 |
| world-model-as-policy | 31 | 38 | 28 | 28 | 23 | 34 | 23 | 29 |
| **total** | **261** | **273** | **240** | **223** | **153** | **331** | **243** | **247** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████████············ 534
fixed-lag                  █······················· 33
incremental                ███████████············· 490
per-scene                  ██████████████████······ 775
feed-forward               ████████████████████████ 1048
temporal-transformer-rolling ████████████············ 529
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1454
navigation                 ███████████············· 666
spatial-reasoning          ██████·················· 335
reconstruction             ████···················· 272
pose                       ███····················· 202
tracking                   ██······················ 130
mapping                    █······················· 83
VSLAM                      █······················· 74
VIO                        █······················· 56
depth                      █······················· 53
occupancy                  ························ 20
SfM                        ························ 14
VO                         ························ 11
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 959
scene-graph                ████████················ 338
pointmap                   ██████·················· 250
sparse                     ██████·················· 221
3DGS                       █████··················· 206
mesh                       ███····················· 123
BEV                        ███····················· 102
voxel                      ██······················ 74
implicit-sdf               █······················· 42
NeRF                       █······················· 30
HD-map                     ························ 19
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1403
multi-modal                ██████████████████······ 1052
RGBD                       ███████················· 388
LiDAR                      █······················· 87
event                      █······················· 42
IMU                        █······················· 41
stereo                     █······················· 39
4D-radar                   ························ 21
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

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
- **[Do Agentic Policies Need to Look at Every Step? Geometric Abstraction for Reasoning and Action](https://arxiv.org/abs/2611.05058)** — `VLA` · 2026-11-04
  - _新軸：以 RGB-D grounding 的 typed evidence-aware 3D symbolic abstraction 作為語言模型可讀的幾何狀態，把 routine spatial reasoning 從每步重讀影像改成可重用符號結構＋metric residual 局部重綁、僅按需視覺推理，對「agentic policy 是否每步都要看原始觀測」給出可量化解法。_
- **[CausalWAM: Learning the Causes of Actions in World Action Models](https://arxiv.org/abs/2610.42096)** — `world-model-as-policy` · 2026-11-02
  - _在 world action model 上引入稀疏路由的可識別性理論，證明 action head 僅依賴 action-relevant latent causes（可識別到 permutation），无需时序依赖假设，开辟了 WAM 中 causal-identifiability 的新方法轴。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._