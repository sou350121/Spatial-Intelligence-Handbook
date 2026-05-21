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
