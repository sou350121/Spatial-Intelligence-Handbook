# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 985 papers · 2026-07-08 → 2026-08-11 · ⚡ 154 · 🔧 567 · 📖 264

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 62
learned                    █████████████████████··· 209
hybrid                     ███████████████········· 147
generative                 █████··················· 50
3R-SLAM-hybrid             █······················· 7
VLA                        ████████████████████████ 242
world-model-as-policy      ██████████·············· 104
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 |
|---|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 13 |
| learned | 37 | 39 | 38 | 54 | 41 |
| hybrid | 17 | 37 | 44 | 26 | 23 |
| generative | 8 | 13 | 10 | 7 | 12 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 |
| VLA | 37 | 50 | 50 | 45 | 60 |
| world-model-as-policy | 11 | 18 | 18 | 26 | 31 |
| **total** | **119** | **173** | **178** | **170** | **181** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 142
fixed-lag                  ························ 1
incremental                ████████················ 125
per-scene                  ████████████████████████ 399
feed-forward               █████··················· 78
temporal-transformer-rolling ██████·················· 93
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 227
navigation                 ██████████████████······ 167
spatial-reasoning          █████████··············· 87
reconstruction             ████████················ 77
pose                       ███····················· 32
tracking                   ██······················ 22
depth                      ██······················ 21
VSLAM                      ██······················ 19
VIO                        █······················· 13
mapping                    █······················· 10
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 219
scene-graph                ████████████············ 114
3DGS                       ████████················ 77
sparse                     ██████·················· 58
pointmap                   ██████·················· 55
BEV                        ██······················ 22
NeRF                       ██······················ 17
voxel                      ██······················ 17
implicit-sdf               ██······················ 16
mesh                       █······················· 9
HD-map                     ························ 4
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 349
multi-modal                ██████████·············· 150
RGBD                       ██████████·············· 145
LiDAR                      ██······················ 25
event                      █······················· 17
stereo                     █······················· 13
IMU                        █······················· 9
4D-radar                   █······················· 8
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[DeepThinkVLA: Enhancing Reasoning Capability of Vision-Language-Action Models](https://arxiv.org/abs/2511.15669)** — `VLA` · 2026-08-07
  - _首次確立並驗證CoT在VLA中生效的兩個必要條件（解碼對齊與因果對齊），並基於此提出hybrid-attention decoder與SFT-then-RL雙階段訓練範式，使CoT從經驗性插件轉為可證實、可優化、可失效歸因的因果模組——這重新定義了VLA中‘推理’的本體論地位，解決ontology §13中長期爭議‘CoT is epiphenomenal in VLA’。_
- **[StreamSplat: Streaming Feed-Forward 3D Gaussian Splatting](https://arxiv.org/abs/2608.01659)** — `generative` · 2026-08-07
  - _首次實現因果流式 feed-forward 3DGS（突破 time 軸：從 per-scene 到 filter-streaming），通過 VACC（voxel-bounded memory）與 HPDA/CGFI 機制，使 3DGS 從離線批量建模轉為可擴展、記憶有界、幾何感知的在線構建範式——此前所有 3DGS 方法均無法在不崩潰或退化下處理 >100 幀因果序列。_
- **[GROVE: Growing and Reasoning over Temporally Stratified Memory from Streaming Video Experience](https://arxiv.org/abs/2608.02392)** — `world-model-as-policy` · 2026-08-07
  - _首次提出時序分層記憶（moments/episodes/patterns）與對應尺度原生檢索技能的統一架構，使單一因果增長記憶同時支撐反應式QA與情境觸發的主動協助——此前所有視頻記憶系統均無法在無額外控制模組下實現此雙模式共用記憶與接口。_
- **[Radar4D-VLM: Proposal-Grounded Temporal 4D Radar Reasoning Across Frozen Language Models](https://arxiv.org/abs/2608.04130)** — `VLA` · 2026-08-07
  - _首次實現純4D雷達（無相機/LiDAR）時序輸入到凍結大語言模型的端到端語義-運動聯合推理，開闢了‘radar-as-language-modality’新範式軸：將物理感知（徑向速度+距離+方位+仰角）直接映射為可被凍結LLM理解的幾何與運動 grounded token 層次結構，解決了長期懸而未決的「雷達語義鴻溝」——即4D雷達缺乏可解釋、可組合、可對齊語言空間的表徵接口問題。_
- **[CofactVLA: Deconfounding Vision-Language-Action Models via Counterfactual Intervention](https://arxiv.org/abs/2608.04396)** — `VLA` · 2026-08-07
  - _首次將反事實干預（counterfactual intervention）形式化為可微分、單次前向傳播的雙路因果圖（DDG），並通過OPG幾何投影與CCR協方差譜抑制，在VLA範式中實現語言因果驅動的解耦——此前所有VLA模型均無能力區分/抑制視覺混雜因子對動作策略的非因果支配。_
- **[Faster-WAM: Efficient Inference-Time Future Conditioning for Robust World Action Models](https://arxiv.org/abs/2608.04404)** — `world-model-as-policy` · 2026-08-07
  - _首次提出 inference-time future conditioning as a *necessary and separable computational primitive* for robust world action models—introducing 'future representation' as a first-class, reusable, sparse, multi-depth temporal latent (via SparseMoT + Interval KV-Fusion), enabling temporal reasoning without video-action re-fusion at every denoising step; this establishes a new paradigm axis: 'world-model-as-policy' now explicitly decouples *temporal representation persistence* from *action generation dynamics*, resolving the long-standing efficiency-robustness trade-off in WAMs (§13 ontology: 'future conditioning' was previously conflated with training-time loss or joint diffusion, not isolated as an inference-time reusable module)._
- **[PhysMind: From Video to Executable Worlds for Training-Free Physical Reasoning](https://arxiv.org/abs/2608.04575)** — `world-model-as-policy` · 2026-08-07
  - _首次實現 training-free、question-agnostic、可編輯的 executable world 構建——在 paradigm 軸上開闢 'world-model-as-policy' 新範式：不依賴預訓練物理模擬器或梯度優化，亦不需微調，僅從單段視頻即構建可因果干預（edit/continue/inspect）的解析動力學世界，解決 ontology §13 中 '如何實現免訓練、可泛化、可操作的物理世界模型' 這一長期爭議。_
- **[Mind-VLA: Instruction-Aware Spatial Representation Alignment for Vision-Language-Action Models](https://arxiv.org/abs/2608.04633)** — `VLA` · 2026-08-07
  - _首次提出並實現 instruction-aware spatial alignment 軸：將 VLA 的 latent 空間對齊目標物體（而非全場景）的三視圖幾何表徵，解決了長期存在的 'instruction-scene grounding mismatch' 問題——此前所有 VLA 方法均在 scene-level 做幾何對齊，無法區分指令所指目標的 3D 構造，導致 occlusion 下操縱失敗。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._