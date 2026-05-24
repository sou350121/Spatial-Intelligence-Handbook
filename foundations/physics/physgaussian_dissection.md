<!-- ontology-5axis
problem: Physics simulation + NVS (3DGS + MPM)
representation: 3DGS + Material Point Method
sensor: RGB (Gaussian fitted) + physics priors
paradigm: Hybrid-DiffSim + DiffRender
time: PerScene + Offline
ref: ../../cheat-sheet/ontology.md §7
-->

# PhysGaussian 解构 (PhysGaussian: MPM Physics on 3DGS — Dissection)

> **发布时间**: CVPR 2024 (Xie et al.)
> **论文 / 模型**: PhysGaussian, [arXiv:2311.12198](https://arxiv.org/abs/2311.12198)
> **核心定位**: **物理感知渲染**（通过 MPM 让 3DGS 可变形），**尚不是 physics-grounded 的策略训练** —— 材料参数仍按资产手工设。

PhysGaussian 是今天最干净的"物理 + 神经渲染"耦合：每个 3D Gaussian 当成一个 MPM 粒子。坑和经典 sim 一样——还得有人手设 E、ν、ρ、摩擦。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item template 2026-05-21. Material parameter sensitivity claims marked `UNVERIFIED`.
**Wedge tier:** W2 · 🔧 [WorldModel] [3DGS]
**TL;DR:** PhysGaussian（[arXiv 2311.12198](https://arxiv.org/abs/2311.12198)）是今天最干净的"物理 + 神经渲染"耦合：**MPM on 3DGS**。**物理感知*渲染***（场景能变形），尚不是 **physics-grounded 的策略训练** —— 材料手工设、contact-rich 场景退化、无闭环。2027 解锁：从观测学材料。

### X-Ray (non-expert friendly)

(a) 3DGS 重建是静态的——splat 不能戳、不能变形。(b) PhysGaussian 把每个 3D Gaussian 绑到一个 MPM（Material Point Method）粒子上，连续体求解器搬运 splat；radiance field 随材料按弹性 / 塑性 / 颗粒 / 粘性模型一起走。(c) 对工程师：用作**软 / 可变形 / 颗粒任务的离线数据增广**；别指望它替代 Isaac 在刚体接触密集装配上 —— MPM 对硬接触弱、材料还得手调。

### 📍 Research Landscape Timeline

```
MPM 2013 ─► NeRF 2020 ─► 3DGS 2023 ─► ★ PhysGaussian CVPR 2024 ─► PAC-NeRF + Diff-MPM (learned materials) 2025+ ─► hybrid rigid+MPM ?
                                              │
                                              └── peers: Spring-Gaus, DreamPhysics (narrower constitutive coverage)
```

PhysGaussian 是参考：本构覆盖广（elastic / plastic / granular / metallic / viscous fluid）。开放问题：**从观测学材料参数** —— PAC-NeRF 血统攻这个。

---

## 1 · Why this matters for embodied AI

3DGS 给你高质量的静态重建。机器人策略不关心静态——它戳、抓、倒、抬。"我有一个 3DGS"到"我能仿真机器人与之交互"之间的桥，正是 PhysGaussian 要补的差。如果桥成立，你就能从纯 RGB 拍摄得到**可交互数字孪生**——无资产建模、无 rigging。

门槛高。Isaac / MuJoCo / FleX 能出货是因为有人手设质量 / 摩擦 / 刚度。PhysGaussian 没消除这步；只是把结果渲得更照相级。

归属 `foundations/physics/`，因为物理 + 神经渲染对 manipulation、humanoid 与潜在的 driving 通用。具身侧评测在测过之后挪到 `embodiments/manipulation/`。

---

## 2 · Architecture

> 📌 **Napkin Formula**: `Gaussian_i.center, Gaussian_i.cov ← MPM_step(particle_i, materials, forces, dt)` —— 每个 3D Gaussian *就是*一个 MPM 粒子。几何从 RGB 学到（3DGS），**物理参数按资产手设**，动力学是经典 MPM。

```
  Captured RGB views ──COLMAP/VGGT──► 3DGS reconstruction (static scene)
                                              │
                                              ▼     ◄── hand-set material (E, ν, ρ)
                                  Per-Gaussian → MPM particle binding
                                              │
                                              ▼     ◄── external forces / applied loads
                                  MPM time-stepping (continuum mechanics)
                                              │ deformed particle positions
                                              ▼
                                  Update Gaussian centers + covariance
                                              │
                                              ▼
                                  3DGS render at new frame
```

聪明的一步：**每个 3D Gaussian 成为一个 MPM 粒子**。MPM 处理大变形、塑性，以及（加扩展后）破裂 / 流体。Gaussian 的 center 与协方差由 MPM 求解器搬运；radiance field 随材料一起走。

支持的本构：elastic、plastic、granular、metallic、viscous fluid。覆盖比 Spring-Gaus / DreamPhysics 广 —— 这是 PhysGaussian 成为参考的主因。

> ⚡ **Eureka Moment**: **每个 3D Gaussian 成为一个 MPM 粒子** —— radiance field 随材料一起走，因为 center + 协方差被物理求解器*搬运*。几何端免费（3DGS），渲染端在大变形 / 塑性 / 破裂下仍照相级。未解部分是**材料识别**，不是耦合。

### 2.5 · Worked example — deformable cloth augmentation

wrist-cam 拍 60 张桌上 T 恤；目标：合成 50 段不同拉扯增广。

1. **3DGS 重建**（~5–10 min `UNVERIFIED`）→ ~80k Gaussians。
2. **手标** shirt = elastic（E=2e5 Pa, ν=0.3, ρ=200 kg/m³）`UNVERIFIED`、桌面 = rigid。
3. **MPM 绑定**：每个 Gaussian → 一个粒子。
4. **仿真** 50 段拉扯轨迹，dt=2 ms `UNVERIFIED`，每段 2 s。
5. **渲染**：每步更新 Gaussian center + cov → 照相级 splat。
6. **输出**：50 段，~3000 帧。

work：不同拉扯下变形合理；对 cloth-folding VLA 预训练有用。
break：手设 E 偏 2× → 衬衫像橡胶或纸；夹爪与刚体接触视觉清晰但力矩错。**外观真，物理近似。**

---

## 3 · What can be *learned* vs what still needs hand-tuning

| Parameter / property | Source in PhysGaussian | Robot-deployment cost |
|---|---|---|
| 场景几何 | 学到（从 RGB 走 3DGS） | 低 —— VGGT 或 COLMAP 拍摄 |
| 外观（radiance） | 学到（3DGS） | 低 —— 同一组拍摄 |
| **材料类（elastic / fluid / granular）** | **每物体手指派** | **per-asset 人力，缩放差** |
| **Young's modulus E** | **手设** | 每种材料手调 |
| **Poisson ratio ν** | **手设** | 每种材料手调 |
| **Density ρ** | **手设** | 每种材料手调 |
| **Yield stress / hardening** | **手设**（塑性材料） | 每种材料手调 |
| 接触响应 | MPM 内部，无参数 | 软接触可，刚接触脆 |
| 摩擦系数 | **手设**于边界 | 每对接触手调 |

诚实读法：**PhysGaussian 继承经典 sim 的材料识别问题，并在其上加了一个照相级渲染器**。几何采集解决了；物理参数采集没。这就是为什么"物理感知渲染" ≠ "physics-grounded 策略训练"。

相关线 —— **PAC-NeRF**、**NeuralFluid**、**diff-MPM + observation** —— 从变形视频里*学*材料参数。这是自然下一步；与 PhysGaussian 的整合是开放研究。

---

## 4 · Where it breaks

| Failure mode | Severity | Why |
|---|---|---|
| **接触密集场景（多体、硬接触）** | High | MPM 是连续体方法；刚体接触是它最弱的 regime。堆叠、peg-in-hole 不可靠 |
| **软体精细细节** | Medium | 粒子分辨率限制能仿真的细 / 薄结构。布褶、毛发差 |
| **大力下时间步不稳** | Medium | 标准 MPM 稳定性；大机器人力矩要更小 dt，rollout 变慢 |
| **无摩擦学习** | High | 摩擦对策略关键且完全手调 |
| **与策略开环** | Hard blocker | 没有东西观测变形再喂回策略 |
| **计算成本** | Medium | 每步 MPM + Gaussian 更新在 4090 上准实时，嵌入式不行 `UNVERIFIED`。数据生成可行；部署推理可疑 |

不是反对 PhysGaussian，而是说*它落在哪*。天然归宿：**视觉丰富、软物理为主任务的离线训练数据增广**（cloth、可变形食物、颗粒倾倒）—— 而非接触密集刚装配。

### 4.x · Hidden Assumptions

- **材料参数可知** —— 今天手调；从视频学（PAC-NeRF）是开放。
- **软 / 连续体物理主导** —— 布 / 流体 yes；刚 peg-in-hole no。
- **MPM 在外力下 dt 稳** —— 大力矩逼小 dt，rollout 变慢。
- **离线数据生成可接受** —— 4090 准实时，嵌入式不行 `UNVERIFIED`。
- **你能为每个物体打材料类标签** —— 手工，缩放差。
- **摩擦近似** —— 手设；无观测识别。
- **与策略不闭环** —— 仅数据工厂；无东西观测变形并回灌。

刚接触主导或缺材料标签任一就毙了集成。

**Interview Tip**："物理感知*渲染*，不是 physics-grounded *策略训练* —— 材料手设、MPM 对硬接触弱。当 Isaac 之上的渲染器用，不替代它。PAC-NeRF + PhysGaussian 是下一篇。"

---

## 5 · Deployment patterns + 2-year outlook

今天的可行用途：(1) **cloth / 可变形 VLA 的离线数据生成** —— 拍摄、用手设材料仿真、渲染、训练（最高杠杆用法）；(2) **可视化 / 调试** —— 把经典 sim 轨迹在 PhysGaussian 里回放给人审；(3) **学材料管线中的一部件** —— PhysGaussian 渲染器 + diff-MPM + 视频观测做参数识别（研究阶段）。

策略闭环可用所需的解锁：(1) **从观测变形视频学到的材料参数** —— PAC-NeRF 风格、规模化；(2) **rigid + MPM 混合** —— 把 MPM 与刚体求解器耦合处理硬接触；(3) **从接触面识别摩擦** —— 开放问题。

**Falsifiable prediction:** 在 2027-12 之前，**不会有任何公开 manipulation VLA 报告在 contact-rich 任务（peg-in-hole、多物体堆叠）上靠 PhysGaussian 风格增广拿到真实世界成功率提升**。胜利先落在软 / 可变形 / 颗粒任务，5–15%。任何"物理感知 3DGS 解锁刚操作"标题应当下注反方。

---

## For the reader

- **Manipulation VLA team:** cloth / 可变形 / 倾倒任务的候选。不用于刚装配。
- **Sim infra team:** 当作 **Isaac / MuJoCo 之上的渲染器**集成，不替代。Isaac 管接触，PhysGaussian 管视觉。
- **Researcher:** 从视频学材料参数是开放的。PAC-NeRF + PhysGaussian 是显然组合 —— 谁先发表谁占这条 niche。
- **Driving / aerial:** 直接相关性低。刚体 + 车辆动力学（driving）与空气动力学 + IMU（aerial）都不打到 MPM 强项。

---

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 数据源：`XPandora/PhysGaussian` issues + commit history（star ~1.5k，2026-05 时 31 open issues / 仅 1 open PR）。

### 8.1 实测痛点表

| Pitfall | Issue # | Status | 直接读者后果 |
|---|---|---|---|
| **Particle filling 2 天跑不完**（grid=128, max_particles=2M, density_thresh=40） | [#47](https://github.com/XPandora/PhysGaussian/issues/47) | Open, no maintainer reply | 印证 README "particle filling 对 Gaussian 分布敏感"；高分辨率几何前处理是隐性时间黑洞 |
| Table 1 评测如何复现（GT 来源 / 数据集？） | [#40](https://github.com/XPandora/PhysGaussian/issues/40) | Open since 2024-10, no reply | **论文定量结果无可复现路径** —— 引用本文的 metric 数字要标 `UNVERIFIED` |
| Snow material 是否实现 | [#44](https://github.com/XPandora/PhysGaussian/issues/44) | Open, no reply | 论文 demo 出现的 material 不全在 release code 里 |
| Plastic Metal can 预训练 model 缺失 | [#43](https://github.com/XPandora/PhysGaussian/issues/43) | Open | 论文 hero demo 资产未释放 → 视觉对比靠自己重训 |
| `particle_impulse` / `azimuth, elevation, radius` config 含义文档缺失 | [#41](https://github.com/XPandora/PhysGaussian/issues/41) / [#42](https://github.com/XPandora/PhysGaussian/issues/42) | Open | 关键 config 参数没文档，复现要逆向源码 |
| Plasticine "softening" 参数怎么调 | [#48](https://github.com/XPandora/PhysGaussian/issues/48) | Open | 印证 §3 表格 "材料参数手设" 的现实成本 |
| Multi-view 原始图像数据集 | [#49](https://github.com/XPandora/PhysGaussian/issues/49) | Open | 想换数据集要自己拍 + COLMAP，paper 数据未公开 |
| Bread fracture 场景的 3DGS | [#52](https://github.com/XPandora/PhysGaussian/issues/52) | Open | 论文 fracture demo 资产请求未回复 |
| `ficus_whitebg` iteration_60000 训练设定 | [#51](https://github.com/XPandora/PhysGaussian/issues/51) | Open | 训练超参未公开，per-scene tuning 黑盒 |
| Config 文件本身 | [#50](https://github.com/XPandora/PhysGaussian/issues/50) | Open | 部分 config 在 release 中缺失 |
| 原始 dataset | [#46](https://github.com/XPandora/PhysGaussian/issues/46) | Open | 同 #49，数据封闭 |

### 8.2 Repo 健康度（关键警告）

- **最近 commit: 2025-04-07**（"plane example" + "tear bread example"，1 年多没动）
- **更早**: 2024-07-22 "pillow2sofa example" / 2024-04-14 "detect invalid nu" / 2024-03-28 "update readme"
- **总 commit 数 ~21**, **开放 issue 31**, **open PR 1**
- **maintainer 响应**: 抽样 issues #40/#47/#48 均 **0 maintainer 回复** —— repo 进入维护停滞期
- **PyTorch 版本**: README 钉 `pytorch=2.0.0+cu118`（CUDA 11.8）—— 与 2026 主流 cu12.x stack 不兼容，装环境要建 isolated env

### 8.3 读者实务含义 (Action items)

1. **环境隔离必须**: 建 Python 3.10 + PyTorch 2.0.0 + cu118 的 conda env，别想用现有 cu12.x 训练机直接跑
2. **paper demo 不全可复现**: 多个 hero asset (bread fracture、metal can、snow) 在 issues 里被要而未供 —— 复现 §2.5 worked example 时**预算大量手工 asset 准备时间**，不是 plug-and-play
3. **Table 1 metric 不可直接引用**: #40 自 2024-10 无答复 —— 引用本文性能数字时务必标 `UNVERIFIED` 或自评测
4. **particle filling 是隐性时间炸弹**: #47 grid=128 跑 2 天无解 —— 从 grid=64 起试，先 profile 再上分辨率
5. **`UNVERIFIED` material 参数确认是真痛点**: #48（plasticine）+ §3 表格"全部手设"+ 无 maintainer 回复 = 经验式调参，**别把它当工程化 pipeline**
6. **维护停滞 → fork 风险**: 若要在生产用，prepare 自己 fork 修 cu12.x 兼容；上游 1 年无动作意味着任何 PR 几乎不会合
7. **§4.x Hidden Assumption "材料参数可知" 升级警告**: #48 + #47 + maintainer silence 三件事叠加 → 这不是"今天手调，明天自动"，是"今天手调，且无人在做明天" —— 等 PAC-NeRF 风格的下一篇 paper，不要押宝 PhysGaussian repo 本身演化

### 8.4 对 §5 Falsifiable Prediction 的支持

原文预测："2027-12 之前不会有任何公开 manipulation VLA 报告在 contact-rich 任务上靠 PhysGaussian 风格增广拿到真实世界成功率提升。"

GitHub 证据**强支持**该预测：
- repo 1 年无 commit
- maintainer 响应停滞
- 关键 demo asset 与材料参数公式都未释放
- 没有 contact-rich 任务的官方示例

读者推论：**PhysGaussian 作为 paper 是 reference，作为 codebase 不再是 active foundation**。要做"物理感知 3DGS"研究，关注 PAC-NeRF、Spring-Gaus、DreamPhysics 与 2026 新出的 hybrid rigid+MPM + 3DGS 方向。

---

## References

- PhysGaussian — Xie et al. *CVPR 2024*. https://arxiv.org/abs/2311.12198
- 3DGS — Kerbl et al. *SIGGRAPH 2023*. https://arxiv.org/abs/2308.04079
- MPM — Stomakhin et al. *SIGGRAPH 2013*
- PAC-NeRF (learned material params) — Li et al. *ICLR 2023*. https://arxiv.org/abs/2303.05512
- Spring-Gaus / DreamPhysics — [arXiv TBD]

## Boundary

本文把 PhysGaussian 解构为**物理感知*渲染***，显式*尚未*是 physics-grounded 策略训练。per-method 替代（PAC-NeRF、NeuralFluid、diff-physics + NeRF）各自有解构。跨方法对比归 `crossing/representation-migration/physics-aware-rendering-across-tasks.md`（TBD）。VLA 训练数据 delta 归 `bridge-to-vla/physgaussian-augmented-vla-training.md`（TBD）。

---

*Last opinion update: 2026-05-21.*
