# 🌌 Spatial Atlas — Ontology Coordinate Map

> Every paper the Pulsar pipeline rates drops a 5-axis ontology coordinate here.
> The point is not the list — it is the **drift**: watch where mass accumulates on the
> paradigm axis (geometric → … → world-model-as-policy) as the field moves.

**Coverage:** 564 papers · 2026-07-08 → 2026-07-27 · ⚡ 84 · 🔧 366 · 📖 114

> Seed corpus — grows every weekday as the daily pipeline runs. Machine-readable source: [`atlas.jsonl`](./atlas.jsonl).

---

## Paradigm axis — where the field sits

_The money axis. Ordered classical → frontier; read the mass migrating rightward over time._

```
axis value                 count
geometric                  ███████················· 41
learned                    ████████████████████···· 125
hybrid                     █████████████████······· 107
generative                 ██████·················· 35
3R-SLAM-hybrid             █······················· 6
VLA                        ████████████████████████ 147
world-model-as-policy      █████████··············· 54
```

### Paradigm drift by week

_Rows ordered classical → frontier. The field moving toward world models reads as
the lower rows getting heavier week over week. (`·` = 0; **total** = weekly sample.)_

| paradigm \ week | W28 | W29 | W30 | W31 |
|---|---:|---:|---:|---:|
| geometric | 9 | 13 | 15 | 4 |
| learned | 37 | 39 | 38 | 11 |
| hybrid | 17 | 37 | 47 | 6 |
| generative | 8 | 13 | 11 | 3 |
| 3R-SLAM-hybrid | · | 3 | 3 | · |
| VLA | 37 | 50 | 52 | 8 |
| world-model-as-policy | 11 | 19 | 18 | 6 |
| **total** | **119** | **174** | **184** | **38** |

## Time axis — batch → streaming frontier

```
axis value                 count
filter-streaming           █████████··············· 92
incremental                ████████················ 85
per-scene                  ████████████████████████ 251
feed-forward               █████··················· 49
temporal-transformer-rolling █████··················· 48
```

## Problem axis — what is being solved

```
axis value                 count
navigation                 ████████████████████████ 124
VLA                        ███████████████████████· 118
spatial-reasoning          ██████████·············· 50
reconstruction             █████████··············· 47
pose                       █████··················· 25
VSLAM                      ███····················· 16
tracking                   ███····················· 13
depth                      ██······················ 12
VIO                        ██······················ 11
mapping                    ██······················ 9
SfM                        █······················· 6
occupancy                  █······················· 3
VO                         █······················· 3
```

## Representation axis

```
axis value                 count
feature-grid               ████████████████████████ 128
scene-graph                ██████████████·········· 75
3DGS                       █████████··············· 48
sparse                     █████████··············· 46
pointmap                   █████··················· 29
NeRF                       ███····················· 14
voxel                      ██······················ 13
BEV                        ██······················ 13
implicit-sdf               ██······················ 8
mesh                       █······················· 5
HD-map                     █······················· 3
```

## Sensor axis

```
axis value                 count
mono                       ████████████████████████ 233
RGBD                       █████████··············· 83
multi-modal                ████████················ 81
LiDAR                      ██······················ 17
stereo                     █······················· 10
event                      █······················· 9
IMU                        █······················· 7
4D-radar                   █······················· 5
```

---

## ⚡ Leading edge (recent frontier-paradigm breakthroughs)

- **[NVIDIA OmniDreams: Real-Time Generative World Model for Closed-Loop Autonomous Vehicle Simulation](https://arxiv.org/abs/2606.03159)** — `world-model-as-policy` · 2026-07-27
  - _首次實現 generative world model 作為 closed-loop autonomous vehicle simulator 的實時、動作條件式、自迴歸視覺生成範式，解開了傳統重建式神經模擬器無法泛化至未見動態場景（如極端天氣、不可預測代理行為）的根本限制，將 spatial AI 的 paradigm 從 reconstruction-based simulation 推進至 world-model-as-policy 的感知-動作閉環生成軸。_
- **[Agentic Real2Sim: Physics-based World Modeling with Vision-Language Agents](https://arxiv.org/abs/2607.19190)** — `VLA` · 2026-07-27
  - _首次將 vision-language agents 作為統一 agentic controller 驅動跨物理態（rigid/deformable/humanoid）的 real2sim 全流程——從觀測重建、物理參數反演、到可執行仿真組裝，實現了 'physics-aware world modeling as agentic orchestration' 新範式，解決 ontology §13 中長期割裂的 'perception → simulation' 軸上缺乏語義-物理聯合規劃能力的根本問題。_
- **[Addressing the Orchestration Gap in Generalist Robots via Physical Agency](https://arxiv.org/abs/2607.21725)** — `world-model-as-policy` · 2026-07-27
  - _引入 'physical agency' 范式——將 VLA 從端到端 learned policy 解耦為可驗證、可恢復、可規劃的 closed-loop orchestrator，首次實現具顯式 goal decomposition、outcome verification 與 failure recovery 的 real-world robotic reasoning閉環，解決 ontology §13 中 'VLA 缺乏可解釋性與可控性' 的長期爭議。_
- **[Closing the Loop: Training-Free Revisit Consistency for Autoregressive Generative Rendering](https://arxiv.org/abs/2607.21848)** — `world-model-as-policy` · 2026-07-27
  - _首次實現訓練無需的 autoregressive generative rendering 中的 revisit consistency，通過將 3D 引擎提供的 pose/depth 時空對應關係直接編碼為 KV cache loop-closure 與幾何約束 attention，使生成式世界模型具備長期空間一致性記憶——此前所有 VLA/world-model-as-policy 工作均無法在 feed-forward 或 auto-regressive 生成中維持跨 eviction 的幾何一致重訪（即 ontology §13 中 'persistent world grounding under bounded context' 長期爭議），此為範式級新能力。_
- **[Action-Conditioned World Model for Goal Plane Probe Guidance in Robotic Ultrasound](https://arxiv.org/abs/2607.21918)** — `world-model-as-policy` · 2026-07-27
  - _首次將 world-model-as-policy 範式引入超音波引導任務，以 action-conditioned latent diffusion 建模非剛性組織形變與聲學觀測的耦合動力學，解決了長期存在的「超音波影像不可微分、無解析渲染模型」導致無法構建可梯度優化的仿真環境這一根本瓶頸。_
- **[ViTacWorld: Scaling Visuo-Tactile World Models for Contact-Rich Robot Manipulation](https://arxiv.org/abs/2607.22530)** — `world-model-as-policy` · 2026-07-27
  - _首度將 world model 范式（paradigm 軸）擴展至 visuo-tactile-action 三元耦合動態建模，實現 tactile 信號在時序 rollout 中的因果可預測性——此前所有 world models（如 Gato、Decision Transformer、VoxPoser、World Models in RL）均忽略 tactile grounding，無法生成或評估接觸力學驅動的行為；ViTacWorld 使 'tactile outcome prediction under action' 成為可量化、可訓練、可評估的范式級能力。_
- **[Robot-Factored World Models via Robot Rendering](https://arxiv.org/abs/2607.22535)** — `world-model-as-policy` · 2026-07-27
  - _首次提出 robot-factored world model 范式：將 action realization（透過真實機器人控制器與運動學求解軌跡）與 robot rendering（基於 URDF 的幾何-運動學-外觀顯式渲染）從世界模型中剝離，使世界模型僅需建模 scene dynamics（接觸、物體運動），解決了長期存在的 action-conditioning 混淆「控制實現」與「物理響應」的根本性建模污染問題。_
- **[WorldPack: Dynamic Frame Compression for Long-context Video World Modeling](https://arxiv.org/abs/2512.02473)** — `world-model-as-policy` · 2026-07-24
  - _首次將3D viewpoint geometry（camera pose + FoV overlap）顯式建模為動態壓縮率分配的控制信號，開闢‘geometrically-gated memory compression’新範式軸，使video world model首度具備空間感知的長時序記憶調控能力（此前所有VWM均用uniform/time-based/attention-based壓縮，無法保證3D一致性）。_

---

_Auto-generated from `atlas.jsonl` by `scripts/pulsar/atlas.py`. Ratings here use the calibrated prompt and may differ from the archived daily reports._