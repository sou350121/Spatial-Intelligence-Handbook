# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 427 papers · 2026-07-08 → 2026-07-22 · ⚡ 63 · 🔧 281 · 📖 83

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ██████·················· 29
learned                    ███████████████████····· 93
hybrid                     ██████████████████······ 86
generative                 █████··················· 25
3R-SLAM-hybrid             █······················· 5
VLA                        ████████████████████████ 117
world-model-as-policy      ████████················ 39
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 |
|---|---:|---:|---:|
| geometric | 10 | 13 | 6 |
| learned | 37 | 39 | 17 |
| hybrid | 17 | 37 | 32 |
| generative | 9 | 14 | 2 |
| 3R-SLAM-hybrid | · | 3 | 2 |
| VLA | 38 | 52 | 27 |
| world-model-as-policy | 11 | 19 | 9 |
| **total** | **122** | **177** | **95** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 73
incremental                █████████··············· 69
per-scene                  ████████████████████████ 186
feed-forward               █████··················· 38
temporal-transformer-rolling ████···················· 34
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 102
VLA                        █████████████████████··· 90
spatial-reasoning          ████████················ 36
reconstruction             ██████·················· 27
pose                       █████··················· 21
VSLAM                      ████···················· 16
tracking                   ███····················· 11
depth                      ██······················ 10
VIO                        ██······················ 9
SfM                        █······················· 5
mapping                    █······················· 4
occupancy                  ························ 1
VO                         ························ 1
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 101
scene-graph                ██████████████·········· 60
sparse                     ██████████·············· 40
3DGS                       ████████················ 33
pointmap                   █████··················· 19
NeRF                       ███····················· 11
BEV                        ██······················ 10
voxel                      ██······················ 8
implicit-sdf               █······················· 5
mesh                       █······················· 4
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 183
multi-modal                ████████················ 62
RGBD                       ████████················ 59
LiDAR                      █······················· 11
event                      █······················· 9
stereo                     █······················· 9
IMU                        ························ 3
4D-radar                   ························ 3
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[Foresight Residual RL for Long-Horizon Robot Manipulation with Vision-Language-Action Models](https://arxiv.org/abs/2607.16506)** — `VLA` · 2026-07-22
  - _首次將 foresight value（基於終態對未來子任務成功概率的離線估計）引入 residual RL 的 reward 設計，開闢了 'temporal credit shaping via learned handoff quality' 這一新方法軸，解決了 VLA 策略在長視界接觸密集操作中因終態品質不可控導致的子任務耦合崩潰問題——這是 spatial reasoning × VLA × long-horizon control 交叉領域長期存在的 ontology §13 爭議（‘how to bridge skill compositionality and geometric continuity’）的首個可量化、可訓練、非啟發式的解。_
- **[DROID-ANCHOR: Odometry-Anchored Recurrent Metric Depth Estimation](https://arxiv.org/abs/2607.17058)** — `3R-SLAM-hybrid` · 2026-07-22
  - _首次將 proprioceptive odometry 作為可學習、時變協方差的幾何錨點（geometric anchor）嵌入 recurrent SLAM 的 BA 框架，從 paradigm 軸上實現 'geometric + learned' 到 '3R-SLAM-hybrid' 的範式躍遷——解決了單目 recurrent SLAM 長期無法閉合尺度漂移的根本缺陷，且不依賴外部標定或運動先驗。_
- **[Asynchronous Multimodal Diffusion Policy Composition via Latency-Aware Guidance Fusion](https://arxiv.org/abs/2607.17257)** — `generative` · 2026-07-22
  - _首次提出 diffusion policy 的異步多模態融合範式，透過 reference-frame rebasing 解決延遲不一致下的 denoising guidance 對齊問題，實現原生頻率下各模態的即時、可插拔式貢獻——此前所有 diffusion policy 均強制同步（per-scene 或 temporal-transformer-rolling），此工作開闢了 'asynchronous generative control' 這一新方法軸。_
- **[Test-Time Scaling for World Action Models via Zero-Shot Geometric Evaluation](https://arxiv.org/abs/2607.17454)** — `world-model-as-policy` · 2026-07-22
  - _首次提出無需訓練、基於零樣本幾何評估（cross-view depth reprojection consistency）的 test-time scaling 決策機制，將世界模型的 rollout 選擇從純黑箱行為評分（如 reward 或 logprob）轉向可解釋、task-label-free 的幾何一致性軸，解決了 WAMs 中「何時值得額外計算」這一長期未形式化的元控制問題。_
- **[Predictive Training with Latent Imagination for Visual Quadruped Navigation](https://arxiv.org/abs/2607.17574)** — `world-model-as-policy` · 2026-07-22
  - _首次將 latent imagination（JEPA-style predictive coding）引入 legged robot 實時導航訓練範式，實現 inference-time zero-cost、zero-parameter 的動態障礙物預測能力——此前所有 VLA/navigation 方法要麼依賴顯式運動模型（geometric），要麼需推理時額外模塊（learned/VLA），本工作在 paradigm 軸開闢 'predictive-training-without-inference-overhead' 新子類。_
- **[RT-SHCUA: Real-Time Self-Hosted Computer-Use Agent for UAV Control](https://arxiv.org/abs/2607.17951)** — `VLA` · 2026-07-22
  - _首次將 self-hosted computer-use agents（SHCUA）與 UAV 實時物理控制解耦，引入 contract-bound skill invocation 軸——為 spatial AI 中長期懸而未決的 'language-to-action trustworthiness gap'（§13.2）提供可驗證、可時序約束、可權限審計、可回溯證據的 formal interface ontology，使 LLM-based reasoning 可安全嵌入 closed-loop flight control。_
- **[Closing the Loop in Humanoid VLA: Persistent 3D Object Tokens for Verifiable Loco-Manipulation](https://arxiv.org/abs/2607.18016)** — `VLA` · 2026-07-22
  - _首次實現VLA中可驗證的閉環執行範式：通過持久化、角色索引的3D物體記錄，統一用於動作生成與幾何謂詞驗證，解決了長期存在的‘動作條件狀態’與‘結果驗證狀態’不一致這一根本性對齊問題（ontology §13 中的 state-coherence 爭議）。_
- **[Human-Inspired Neuro-Symbolic World Modeling and Logic Reasoning for Interpretable Safe UAV Landing Site Assessment](https://arxiv.org/abs/2510.22204)** — `world-model-as-policy` · 2026-07-21
  - _首次將 neuro-symbolic 架構耦合於 UAV landing site assessment 問題，實現「感知建模」與「符號安全推理」的嚴格分離軸（paradigm: hybrid → world-model-as-policy），並在 real-time edge deployment 中達成可驗證、可解釋、可形式化驗證的安全決策——此前所有 VLA 或 learned occupancy 方法均無法提供白箱邏輯追溯與人類可審計的約束違反溯源。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._