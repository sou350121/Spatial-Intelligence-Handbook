# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 3802 papers · 2026-07-08 → 2026-10-22 · ⚡ 308 · 🔧 2358 · 📖 1136

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 230
learned                    ███████████████████····· 765
hybrid                     █████████████··········· 516
generative                 ██████·················· 236
3R-SLAM-hybrid             ························ 15
VLA                        ████████████████████████ 986
world-model-as-policy      █████████··············· 372
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

> Historical recovery: 317 late-imported records count toward total coverage and axis distributions, but are excluded from weekly drift and recent frontier picks. `date` is the handbook ingestion date; original submission dates are in `published_at`.

| paradigm \ week | W36 | W37 | W38 | W39 | W40 | W41 | W42 | W43 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| geometric | 16 | 12 | 31 | 28 | 13 | 13 | 8 | 15 |
| learned | 55 | 45 | 56 | 50 | 51 | 50 | 26 | 68 |
| hybrid | 51 | 22 | 41 | 44 | 38 | 34 | 17 | 42 |
| generative | 24 | 18 | 20 | 18 | 13 | 11 | 13 | 18 |
| 3R-SLAM-hybrid | 1 | · | · | · | 1 | · | 1 | · |
| VLA | 55 | 37 | 83 | 95 | 96 | 87 | 65 | 93 |
| world-model-as-policy | 19 | 12 | 31 | 38 | 28 | 28 | 23 | 28 |
| **total** | **221** | **146** | **262** | **273** | **240** | **223** | **153** | **264** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████████··········· 459
fixed-lag                  █······················· 23
incremental                ████████████············ 406
per-scene                  ████████████████████···· 709
feed-forward               ████████████████████████ 846
temporal-transformer-rolling █████████████··········· 461
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 1204
navigation                 ███████████············· 569
spatial-reasoning          ██████·················· 293
reconstruction             █████··················· 243
pose                       ███····················· 168
tracking                   ██······················ 104
mapping                    █······················· 72
VSLAM                      █······················· 62
depth                      █······················· 49
VIO                        █······················· 47
occupancy                  ························ 18
SfM                        ························ 14
VO                         ························ 10
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 811
scene-graph                █████████··············· 302
pointmap                   ███████················· 223
3DGS                       █████··················· 184
sparse                     █████··················· 183
mesh                       ███····················· 106
BEV                        ███····················· 89
voxel                      ██······················ 59
implicit-sdf               █······················· 39
NeRF                       █······················· 30
HD-map                     ························ 12
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 1217
multi-modal                █████████████████······· 864
RGBD                       ███████················· 348
LiDAR                      ██······················ 77
event                      █······················· 36
IMU                        █······················· 33
stereo                     █······················· 31
4D-radar                   ························ 20
sonar                      ························ 10
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Feedback World Model Enables Precise Guidance of Diffusion Policy](https://arxiv.org/abs/2605.15705)** — `world-model-as-policy` · 2026-10-22
  - _把世界模型從開環 rollout 預測器改造成推理期帶在線回饋狀態的閉環預測器（latent-space observer，具收斂保證、無需重訓），開了一條「test-time 自適應 world model 校正」的新方法軸，直接解掉 OOD 漂移下開環預測不可用的既有問題。_
- **[Let It Be Simple: One-Step Action Generation for Vision-Language-Action Models](https://arxiv.org/abs/2606.05737)** — `VLA` · 2026-10-22
  - _首度以 condition-target 資訊不對稱（Flow-Matching irreducible velocity loss R_v(t,c) 的端點塌縮 + 生成映射對初始噪聲的 Jacobian 最大奇異值遠小）量化說明「一步生成不可行」這條既有邊界只屬 text-to-image、不屬 VLA，並據此免蒸餾取得單步策略——開的是「生成式解碼步數由條件-目標結構決定」這條新分析軸，而非又一個 VLA 應用。_
- **[$\mu_0$: A Scalable 3D Interaction-Trace World Model](https://arxiv.org/abs/2606.13769)** — `world-model-as-policy` · 2026-10-22
  - _以「3D 互動軌跡(trace)」作 embodiment-agnostic 的 world-model 預測介面，開出一條繞開稠密像素重建與 embodiment-specific action 標籤的新方法軸，並用 TraceExtract 從無標註影片自動抽取 3D 監督實現可擴展預訓練。_
- **[WorldStream: Streaming Interactive 3D Worlds with Hierarchical Planning and Persistent State](https://arxiv.org/abs/2610.28827)** — `generative` · 2026-10-22
  - _在 streaming world model 這條軸上首次把「無界地形擴展」與「可回訪、可編輯的持久世界狀態」統一：以 typed decision model 的階層式 planner 產生跨 tile 的 boundary commitments（巨觀結構→微觀 tile 語意），再由確定性 local code 編譯成幾何，並用單一 world record（plans/seeds/object identity/mutable state/edits）同時支撐前向生成與語言互動，解決了既有 generative world model 無法越過預設地圖、且離開後無法還原編輯的既有做不到之事，屬範式級新能力軸（非單純把世界模型套到新場景）。_
- **[LiveAct: Towards Real-Time Multi-Agent World Models with Heterogeneous Action Interfaces](https://arxiv.org/abs/2610.29408)** — `generative` · 2026-10-22
  - _⚡ 將交互式視頻世界模型從單智能體、單一任務動作接口推進到多智能體聯合視覺預測與異構動作語義綁定，開了一條 action-interface 泛化的新軸，並以 blockwise causal 生成支援流式推理。_
- **[PhysiCalWorld: In-Context Physics Calibration for World Models](https://arxiv.org/abs/2610.30125)** — `world-model-as-policy` · 2026-10-22
  - _首創「免標籤、免微調」的 in-context 物理校準：從測試場景的一段探索交互 clip 抽出單一 physics descriptor token 並以此條件化 action-conditioned world model，把系統辨識（質量分布、阻尼、摩擦）內化進世界模型潛空間，解決了以往世界模型在新物理參數場景必然回歸經驗先驗、rollout 嚴重漂移且只能靠 fine-tune 或解析建模補救的具體缺口——新軸在於「測試時 in-context 物理條件化」，而非架構或 benchmark 刷新。_
- **[Agentic World Action Models](https://arxiv.org/abs/2610.30136)** — `world-model-as-policy` · 2026-10-22
  - _將可執行程式碼作為第三條生成流，與未來 video、robot action 在同一個 mixture-of-transformers 中聯合建模，使 world model 的多步預測由可重用技能程式結構化，同時讓 agentic 規劃獲得物理動態的預測依據；因此解開了 WAM 缺乏 compositional skill reuse、agentic 缺乏 predictive grounding 的雙向缺口。_
- **[DEFLECT: Temporal Counterfactual Preference Learning for Delay-Robust Asynchronous VLAs](https://arxiv.org/abs/2605.19294)** — `VLA` · 2026-10-21
  - _用離線軌跡中才可見的 execution-time 觀測與 prediction-time 觀測構成 temporal counterfactual 對比，轉為 preference 監督，開了一條「以對比未來狀態監督動作再對齊」的新監督軸，解了既有 training-time 改輸入/目標與 runtime repair 都做不到的預測-執行狀態錯配問題。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._