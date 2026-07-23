# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 476 papers · 2026-07-08 → 2026-07-23 · ⚡ 71 · 🔧 311 · 📖 94

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 34
learned                    ███████████████████····· 104
hybrid                     █████████████████······· 92
generative                 █████··················· 29
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 129
world-model-as-policy      ████████················ 43
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 |
|---|---:|---:|---:|
| geometric | 9 | 13 | 12 |
| learned | 37 | 39 | 28 |
| hybrid | 17 | 37 | 38 |
| generative | 9 | 13 | 7 |
| 3R-SLAM-hybrid | · | 3 | 3 |
| VLA | 38 | 52 | 39 |
| world-model-as-policy | 11 | 19 | 13 |
| **total** | **121** | **176** | **140** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           ██████████·············· 83
incremental                ████████················ 73
per-scene                  ████████████████████████ 209
feed-forward               █████··················· 40
temporal-transformer-rolling ████···················· 38
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 110
VLA                        ██████████████████████·· 102
spatial-reasoning          █████████··············· 39
reconstruction             ███████················· 34
pose                       █████··················· 22
VSLAM                      ███····················· 16
tracking                   ██······················ 11
depth                      ██······················ 10
VIO                        ██······················ 9
mapping                    █······················· 6
SfM                        █······················· 5
VO                         ························ 2
occupancy                  ························ 1
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 110
scene-graph                ███████████████········· 68
sparse                     █████████··············· 41
3DGS                       █████████··············· 39
pointmap                   █████··················· 24
NeRF                       ██······················ 11
BEV                        ██······················ 11
voxel                      ██······················ 8
implicit-sdf               █······················· 6
mesh                       █······················· 5
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 199
RGBD                       ████████················ 68
multi-modal                ████████················ 67
LiDAR                      ██······················ 14
event                      █······················· 9
stereo                     █······················· 9
IMU                        █······················· 5
4D-radar                   ························ 4
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Scaling Cross-Embodiment World Models for Dexterous Manipulation](https://arxiv.org/abs/2511.01177)** — `world-model-as-policy` · 2026-07-23
  - _首次將世界模型建模軸從「scene dynamics」拓展至「embodiment-agnostic interaction geometry」，以粒子位移場統一表徵人手與多種機械手的物理交互，實現跨形態（kinematically heterogeneous）的zero-shot控制遷移——此前所有VLA/world model均綁定特定動作空間或運動學模型。_
- **[STeP: Signal Temporal Logic for Precise Specifications for Action Generation with Vision Language Models](https://arxiv.org/abs/2607.18580)** — `VLA` · 2026-07-23
  - _首次將 Signal Temporal Logic（STL）作為統一形式化接口嵌入VLA全棧——從語言解析、子任務約束生成、低層策略選擇、執行監控到運行時重規劃，實現了自然語言指令中空間+時間+邏輯約束的可驗證、可分解、可修正的端到端閉環，解決了VLA長期存在的「語義漂移」與「執行不可驗證」這一ontology §13核心爭議。_
- **[Agentic Real2Sim: Physics-based World Modeling with Vision-Language Agents](https://arxiv.org/abs/2607.19190)** — `VLA` · 2026-07-23
  - _首次將 vision-language agents 作為統一 agentic controller 用於端到端 real2sim 轉換，實現跨物體物理態（rigid/deformable/humanoid）的統一建模與可執行仿真生成，突破既有 pipeline 嚴格分域、手動 glue 的範式限制，解開 ontology §13 中 'physics-aware world model composition from unstructured video' 的長期爭議。_
- **[Cognitive Dual-Process Planning for Autonomous Driving with Structured Scene Knowledge and Verifiable Reasoning-Action Consistency](https://arxiv.org/abs/2607.19194)** — `VLA` · 2026-07-23
  - _首次將認知雙系統理論（fast/slow thinking）形式化為可驗證的規劃範式，通過結構化鏈式推理（S-CoT）schema與確定性邏輯驗證器實現推理-行動一致性（reasoning-action consistency）的可證偽性，解決了VLA類規劃中長期存在的‘幻覺推理與實際動作脫鉤’這一ontology §13核心爭議。_
- **[IGGT4D: Streaming 4D Instance-Grounded Geometry Transformer](https://arxiv.org/abs/2607.19228)** — `3R-SLAM-hybrid` · 2026-07-23
  - _首度實現 streaming 4D instance-grounded geometry modeling via causal spatial-temporal Transformer — introduces 'instance-grounded geometry' as a new paradigm axis, enabling unified, temporally consistent joint estimation of camera motion, dynamic 3D geometry, and object identity *online*, which prior geometric, learned, or VLA paradigms cannot do without offline optimization or external 2D cues._
- **[Masked Visual Actions for Unified World Modeling](https://arxiv.org/abs/2607.19343)** — `world-model-as-policy` · 2026-07-23
  - _首次將動作建模統一為像素空間內的掩碼視覺軌跡（masked visual trajectory），使同一模型同時支持前向動力學預測與逆向行為合成，突破了傳統VLA/world model中action representation與visual representation割裂的範式，實現了‘視覺-動作’本體論級對齊。_
- **[Foresight Residual RL for Long-Horizon Robot Manipulation with Vision-Language-Action Models](https://arxiv.org/abs/2607.16506)** — `VLA` · 2026-07-22
  - _首次將 foresight value（基於終態對未來子任務成功概率的離線估計）引入 residual RL 的 reward 設計，開闢了 'temporal credit shaping via learned handoff quality' 這一新方法軸，解決了 VLA 策略在長視界接觸密集操作中因終態品質不可控導致的子任務耦合崩潰問題——這是 spatial reasoning × VLA × long-horizon control 交叉領域長期存在的 ontology §13 爭議（‘how to bridge skill compositionality and geometric continuity’）的首個可量化、可訓練、非啟發式的解。_
- **[DROID-ANCHOR: Odometry-Anchored Recurrent Metric Depth Estimation](https://arxiv.org/abs/2607.17058)** — `3R-SLAM-hybrid` · 2026-07-22
  - _首次將 proprioceptive odometry 作為可學習、時變協方差的幾何錨點（geometric anchor）嵌入 recurrent SLAM 的 BA 框架，從 paradigm 軸上實現 'geometric + learned' 到 '3R-SLAM-hybrid' 的範式躍遷——解決了單目 recurrent SLAM 長期無法閉合尺度漂移的根本缺陷，且不依賴外部標定或運動先驗。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._