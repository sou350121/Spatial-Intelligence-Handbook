# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 1538 papers · 2026-07-08 → 2026-08-25 · ⚡ 171 · 🔧 622 · 📖 745

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 68
learned                    █████████████████████··· 228
hybrid                     ███████████████········· 165
generative                 █████··················· 56
3R-SLAM-hybrid             █······················· 8
VLA                        ████████████████████████ 266
world-model-as-policy      ██████████·············· 112
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 | W32 | W33 | W35 |
|---|---:|---:|---:|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 12 | 13 | 1 | 5 |
| learned | 36 | 39 | 37 | 54 | 40 | 11 | 11 |
| hybrid | 17 | 37 | 44 | 25 | 23 | 8 | 11 |
| generative | 7 | 13 | 10 | 7 | 12 | 3 | 4 |
| 3R-SLAM-hybrid | · | 3 | 3 | · | 1 | 1 | · |
| VLA | 37 | 49 | 50 | 43 | 58 | 17 | 12 |
| world-model-as-policy | 11 | 18 | 17 | 26 | 30 | 7 | 3 |
| **total** | **117** | **172** | **176** | **167** | **177** | **48** | **46** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ████████················ 149
fixed-lag                  ························ 1
incremental                ███████················· 135
per-scene                  ████████████████████████ 446
feed-forward               █████··················· 86
temporal-transformer-rolling ██████·················· 103
```

## Problem axis — what is being solved

```
axis value                 count
VLA                        ████████████████████████ 251
navigation                 █████████████████······· 181
spatial-reasoning          █████████··············· 99
reconstruction             ████████················ 88
pose                       ████···················· 37
depth                      ██······················ 23
tracking                   ██······················ 22
VSLAM                      ██······················ 19
VIO                        █······················· 14
mapping                    █······················· 11
SfM                        █······················· 7
VO                         █······················· 6
occupancy                  ························ 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 235
scene-graph                █████████████··········· 131
3DGS                       █████████··············· 84
pointmap                   ███████················· 64
sparse                     ██████·················· 62
BEV                        ███····················· 26
voxel                      ██······················ 20
NeRF                       ██······················ 20
implicit-sdf               ██······················ 17
mesh                       █······················· 10
HD-map                     ························ 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 384
multi-modal                ███████████············· 169
RGBD                       ██████████·············· 157
LiDAR                      ██······················ 27
event                      █······················· 17
stereo                     █······················· 15
IMU                        █······················· 9
4D-radar                   ························ 8
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[DECOWAM: Decoupled Whole-Body World-Action Model for Legged Mobile Manipulation](https://arxiv.org/abs/2608.20114)** — `world-model-as-policy` · 2026-08-25
  - _首次提出 embodiment-aware factorization 軸：將世界-動作建模中混疊的 camera ego-motion、base locomotion 和 arm manipulation 三者在潛空間中通過 adversarial separation + action-equivalent future bottleneck 進行可解耦、可條件化干預的顯式分離，實現 moving-viewpoint 下 joint visual prediction 與 whole-body control 的統一建模——此前所有 VLA/world-model 工作（含 FastWAM）均未對 legged mobile manipulation 的全體態運動學耦合做此類結構性解耦。_
- **[EndoLIFT: Language-Disambiguated Latent-Conditioned Rectified Flow for Bidirectional Endoscopic Control](https://arxiv.org/abs/2608.20478)** — `VLA` · 2026-08-25
  - _首次提出並形式化‘intent aliasing’這一空間控制中的根本性歧義問題，並通過語言條件化+隨機軌跡潛變量的雙路徑解耦機制，在 paradigm 軸上開創了‘VLA-as-ambiguity-resolver’新範式，使同一視覺觀測下可穩健切換相反運動意圖（此前所有基於視覺或時序建模的 VLA/SLAM/VIO 方法均無法區分）。_
- **[Logic-VLA: A Temporal Logic Conditioned Vision-Language-Action Model](https://arxiv.org/abs/2608.20556)** — `VLA` · 2026-08-25
  - _首次將 Signal Temporal Logic（STL）作為可插拔、推理時注入的條件信號接入VLA架構，實現單一策略模型在不重訓練前提下動態適應任意未見STL規範——此前VLA僅支持靜態NL指令，無法形式化表達時序約束、安全邊界與空間-時間混合不等式（如'避開A區直到t>5s後進入B區'），此為ontology §13中'spatial-reasoning'與'VLA'交叉軸上長期缺失的可量化形式化控制能力。_
- **[ForeTime-VLA: Causal Future-Token Distillation from a World Action Model for Conveyor-Belt Manipulation](https://arxiv.org/abs/2608.20735)** — `world-model-as-policy` · 2026-08-25
  - _首次實現因果推斷約束下的未來token蒸餾範式（paradigm軸），使VLA策略在無需生成/模擬未來幀的前提下，具備可證實的、動作等價的未來狀態感知能力，解決了WAM與VLA實時部署間長期存在的表徵耦合與因果違規矛盾。_
- **[CertVLA: Certified Defense against Physical Visual Attacks for Vision-Language-Action Models](https://arxiv.org/abs/2608.20791)** — `VLA` · 2026-08-25
  - _首次為閉環VLA控制建立與物理攻擊無關的行為一致性認證框架，開闢了'certified spatial action'新方法軸——此前所有VLA防禦僅針對離散分類或單幀動作輸出，無法處理時序耦合、連續動作空間與物理世界干擾的聯合約束。_
- **[PhysCaP: Grounding Code-as-Policy Agent with Physics-Informed Exploration](https://arxiv.org/abs/2608.21031)** — `VLA` · 2026-08-25
  - _首次將 physics-informed active exploration（含無感測器質量/剛度估計）內建於 code-as-policy 架構，實現 policy-level物理屬性驅動的交互決策，解決了VLA範式長期無法自主推斷隱藏物理量而依賴被動觀察的根本缺陷。_
- **[Robotic Manipulation is Vision-to-Geometry Mapping: Vision-Geometry Backbones over Language and Video Models](https://arxiv.org/abs/2604.12908)** — `world-model-as-policy` · 2026-08-14
  - _首次明確提出並實作「vision-to-geometry mapping」作為機械臂控制的本體論軸心，以預訓練3D世界模型（非語言/視頻）為backbone，取代VLA範式中語義中介的必要性，解決了長期存在的‘語義鴻溝導致幾何不忠實’這一ontology §13核心爭議。_
- **[MuseVLA: An Adaptive Multimodal Sensing Vision-Language-Action Model for Robotic Manipulation](https://arxiv.org/abs/2606.17598)** — `VLA` · 2026-08-14
  - _首次提出「可擴展的傳感器即工具（sensor-as-tool）」架構，將異質物理傳感器（溫度、音頻、雷達等）動態綁定至VLA模型的推理鏈中，實現跨模態感知-語言-動作的統一token化調度與 grounded sensor image 中間表示，解決了長期存在的「VLA模型被RGB綁定、無法原生支持物理屬性感知」這一ontology §13核心爭議。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._