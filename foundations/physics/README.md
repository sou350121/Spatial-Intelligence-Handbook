# ⚛️ Physics — Explorer's Map (物理 primitives in spatial AI)

> **"渲染告诉你世界看起来怎么样；物理告诉你戳一下世界会怎么响应。"**
>
> Spatial AI 的两条腿：**外观重建**（3DGS / NeRF / VGGT）与**物理动力学**（这一区）。前者填满了 sim2real 视觉端、后者支撑了 policy training 的因果信号 —— VLA / manipulation / locomotion 所有 RL 训练都是在某个 physics engine 里跑出来的。
>
> 目前收录 **4 篇深度解析 + 1 篇 primer + 1 篇 comparison**（2026-05-22 从 seed 扩到 first-class zone）。

&nbsp;

---

## 📍 这个 zone 在 spatial AI handbook 中的位置

physics zone 与相邻 zone 的关系是**因果链上的不同环节**：

```
   感知 / 重建        ───►   决策 / 策略       ───►   仿真训练
   ─────────────              ─────────────             ─────────────
   3dgs-family                world-model (推理)         physics (本区)
   feed-forward-3d            vlm-spatial               generative-3d-sim
   depth-foundation                                     (视觉增广)
   classical-slam                                       
                                                        ↓
                                                        VLA / RL policy
                                                        (训练好的 policy
                                                         回到机器人)
   
   物理感知 *渲染* (PhysGaussian) ──┐         ┌── 物理感知 *动力学* (MJX/Warp/Brax/Genesis)
                                    │         │
                                    └─── physics zone (本区) ───┘
                                    ↑           ↑
                                视觉端物理      控制端物理
                                (sim2real 视觉)  (sim2real 控制 / policy)
```

**这一区的双 lane 设计**：
- **Lane A · 物理感知渲染** — PhysGaussian (MPM + 3DGS) 让 3DGS 重建可变形、可交互；服务 sim2real *视觉端*
- **Lane B · 物理动力学引擎** — MuJoCo MJX / NVIDIA Warp / Brax / Genesis 等 GPU 仿真器；服务 sim2real *控制 / 策略训练*

两条 lane 在物理上互不重叠（一个解渲染、一个解动力学），但**在 VLA 训练 pipeline 中常并用** —— Splat-Sim 给视觉、MJX 给动力学，最后融合产出训练样本。

&nbsp;

---

## 🌐 边界 — 这区 vs 相邻 zone

| 这区写什么 | 别在这区，去哪 |
|---|---|
| **物理感知渲染**（MPM + 3DGS 让 splat 可变形） | per-method 3DGS 内部 → `../3dgs-family/` |
| **物理动力学引擎拆解**（MJX / Warp / Brax / Genesis） | 视觉端 sim2real 增广 → `../generative-3d-sim/` |
| **底层数学** (SE(3) twist/wrench、Featherstone、contact LCP) | 通用 SE(3)/SO(3) 数学 → `../spatial-math/se3_so3_lie_groups_primer.md` |
| **可微物理**（gradient through contact, sysID） | inference-time world model → `../world-model/`（那一区写 Cosmos / Genie / Marble） |
| **多 framework 横向对比** | training-time data factory → `../generative-3d-sim/`（视觉端） |
| | 跨 embodiment "哪家 sim 赢" → `../../crossing/`（待开 wedge） |

**与 `../generative-3d-sim/` 最容易混淆 —— 一句话区分**：
- generative-3d-sim 是**视觉端**：3DGS 给训练 policy 见到的"图像怎么变"
- physics 是**因果端**：仿真器给训练 policy 见到的"动作执行后世界怎么变"

VLA 训练管线两者都要 — 它们不是替代关系。

&nbsp;

---

## 🔍 一眼看清 zone 内 6 篇文档

### 表 1 · 文档类型与定位

| 文档 | 类型 | 何时读 |
|---|---|---|
| **本 README** | zone 入口 | 第一次进 zone | 
| [`rigid_body_dynamics_primer.md`](./rigid_body_dynamics_primer.md) | **primer**（部分 14 项） | 读 MJX/Warp dissection 前的前置课；SE(3) twist/wrench、Featherstone、contact LCP 入门 |
| [`physgaussian_dissection.md`](./physgaussian_dissection.md) | dissection (v1.1) | MPM + 3DGS：物理感知*渲染*（不是动力学）；soft-body 视觉端增广 |
| [`mujoco_mjx_dissection.md`](./mujoco_mjx_dissection.md) | dissection (v1) | MuJoCo on JAX/XLA；humanoid / dexterous RL 当前 default backend |
| [`nvidia_warp_dissection.md`](./nvidia_warp_dissection.md) | dissection (v1) | Python-first GPU kernel + 编译时 autodiff；Isaac Lab 集成 |
| [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md) | **comparison**（表格驱动） | Brax / MJX / Warp / Genesis 选型决策 — 不走 14 项 dissection |

&nbsp;

### 表 2 · 选型分诊（你想做什么 → 读哪篇）

| 你想做什么 | 第一篇读 | 第二篇 |
|---|---|---|
| 入门：理解仿真器内部数学 | `rigid_body_dynamics_primer.md` | `mujoco_mjx_dissection.md` |
| 训 humanoid / quadruped RL | `mujoco_mjx_dissection.md` | `differentiable_physics_comparison.md` |
| 写端到端可微 sim (sysID, material learning) | `nvidia_warp_dissection.md` | `differentiable_physics_comparison.md` |
| 选 simulator (Brax vs MJX vs Warp vs Genesis) | `differentiable_physics_comparison.md` | per-engine dissection |
| Soft body / cloth / 视觉端可变形 | `physgaussian_dissection.md` | `../generative-3d-sim/` |
| 调 contact stiffness 遇坑 | `rigid_body_dynamics_primer.md` §4 + `mujoco_mjx_dissection.md` §4 | MuJoCo 文档（外部） |

&nbsp;

### 表 3 · 涵盖与未涵盖

| 涵盖 ✅ | 当前未涵盖 ⚠️ |
|---|---|
| MuJoCo MJX (Google DeepMind) | Brax 专题 dissection (在 comparison 中介绍) |
| NVIDIA Warp (Python GPU DSL + autodiff) | Genesis 专题 dissection (在 comparison 中介绍, 2024-12 新发布) |
| PhysGaussian (MPM + 3DGS) | Drake / TAMSI contact-implicit dissection |
| 4 框架横向对比 (Brax / MJX / Warp / Genesis) | DiffTaichi / Taichi Lang 学术先驱 |
| 底层数学 (SE(3) twist, Featherstone, contact LCP) | per-task benchmark 数字（Pulsar pipeline 未来填） |

&nbsp;

---

## 📖 推荐学习路径

### 🏃 "我就想看 GPU 物理仿真 2024-2026 怎么变了"（3 篇 · 60 min）

```
rigid_body_dynamics_primer → mujoco_mjx_dissection → differentiable_physics_comparison
```

数学骨架 → 当前 default backend → 4 家选型矩阵。读完知道：MuJoCo MJX 是 GPU sim era 的 MuJoCo 阵营答案、Warp 是 NVIDIA 自家 differentiable 路线、Brax 是端到端可微的最快入门、Genesis 是多 solver 联合新秀。

&nbsp;

### 🤖 "我做 manipulation policy，要选 sim"（4 篇 · 90 min）

```
rigid_body_dynamics_primer → mujoco_mjx_dissection → differentiable_physics_comparison → physgaussian_dissection (视觉端)
```

底层数学 → MJX 在 manipulation 的限制（mesh collision、contact 软）→ 选型矩阵 → 视觉端怎么补。完整 manipulation sim2real 决策栈。

&nbsp;

### 🧠 "我做 differentiable physics 研究"（3 篇 · 75 min）

```
rigid_body_dynamics_primer → nvidia_warp_dissection → differentiable_physics_comparison
```

数学基础 → Warp 怎么做编译时 autodiff → 4 家 differentiability 路线对比。读完知道：Brax/MJX 的可微 ≠ Warp 的可微，contact 数学决定梯度可用性。

&nbsp;

### 🎬 "我做 sim2real，视觉 + 动力学一起搞"（4 篇 + 跨 zone · 120 min）

```
本 zone:  physgaussian_dissection (视觉)
          + mujoco_mjx_dissection (动力学)
跨 zone:  ../generative-3d-sim/splat_sim_for_manipulation.md (视觉端 sim2real)
          + ../generative-3d-sim/aerial_gym_3dgs_sim2real.md (aerial 端)
```

视觉端物理（PhysGaussian / Splat-Sim）+ 动力学端物理（MJX）的完整 sim2real 链。

&nbsp;

---

## ⚠️ Zone-wide 注意事项

### 1 · 这区 4 家 (Brax/MJX/Warp/Genesis) 的"可微"含义不同

- **Brax** & **MJX**: 通过 *softened contact* 让梯度自然存在 — 物理近似性影响梯度的物理意义
- **NVIDIA Warp**: *编译时* 生成 forward + reverse kernel —— 最严谨，但要用户写 step 函数
- **Genesis**: differentiability 范围 `UNVERIFIED`，2024-12 新发布

读 dissection 时**注意区分**：作者说"可微"，是说哪种？

### 2 · sim2real gap 的两个根

- **视觉 gap**: domain randomization / Splat-Sim / Cosmos 在补 → 见 `../generative-3d-sim/`
- **动力学 gap**: contact stiffness / friction / actuator dynamics —— 4 家仿真器都有 — 见各 dissection §6 Hidden Assumptions

**两者独立**：把视觉补好不解决动力学；反之亦然。manipulation sim2real 失败常源于动力学 gap 而非视觉，因为视觉端文献被反复刷榜，动力学端容易被忽视。

### 3 · UNVERIFIED 政策

本 zone 所有 dissection 严格遵守 AGENTS.md UNVERIFIED 规则 — throughput / benchmark / memory 等数字若 agent 未亲自 reproduce，一律标 `UNVERIFIED`。**宁可不写也不写错** —— 物理仿真的 benchmark 数字与硬件 / batch size / task / 编译器版本紧耦合，照搬别处的数字到自己 stack 上常常翻车。

### 4 · 与 PhysGaussian 的位置

PhysGaussian 在本 zone 但**与其他 4 家不在同一 lane**：
- PhysGaussian = 物理感知 *渲染*（视觉端 soft-body augmentation）
- MJX / Warp / Brax / Genesis = 物理 *动力学*（控制端 policy training）

读到 PhysGaussian 别期望它训 manipulation policy；它的客户是 *视觉端* 增广 pipeline。

&nbsp;

---

## 🗺️ Zone 内文件总览

```
foundations/physics/
├── README.md                              ← 本文件 (zone 入口)
├── rigid_body_dynamics_primer.md          ← primer：底层数学 (SE(3) twist/wrench, Featherstone, contact LCP)
├── physgaussian_dissection.md             ← dissection (v1.1)：MPM + 3DGS, 物理感知渲染
├── mujoco_mjx_dissection.md               ← dissection (v1)：MuJoCo on JAX/XLA, GPU
├── nvidia_warp_dissection.md              ← dissection (v1)：Python GPU DSL + autodiff
└── differentiable_physics_comparison.md   ← comparison：4 框架横向选型
```

&nbsp;

---

## 🌍 与其他 zone 的跨链

| 跨链方向 | 目标 | 为什么 |
|---|---|---|
| **数学上游** | [`../spatial-math/se3_so3_lie_groups_primer.md`](../spatial-math/se3_so3_lie_groups_primer.md) | 本 zone primer §2 默认你读过 SE(3) 基础 |
| **数学上游** | [`../spatial-math/rotation_intuition_primer.md`](../spatial-math/rotation_intuition_primer.md) | 旋转表达的直觉入门 |
| **视觉端互补** | [`../generative-3d-sim/`](../generative-3d-sim/) | sim2real 视觉端（与本 zone 动力学端并用） |
| **决策端区分** | [`../world-model/`](../world-model/) | 推理期 world model（Cosmos / Genie / Marble）≠ 训练期 physics |
| **VLA 接口（待补）** | `../../bridge-to-vla/` | physics-grounded VLA 训练数据 schema |
| **跨 embodiment 比较（待补）** | `../../crossing/` | "manipulation vs locomotion 各家 sim 谁赢" 候选 wedge |

&nbsp;

---

## 🔮 Zone roadmap (next 2-4 weeks)

| 优先级 | 文档 | 类型 |
|---|---|---|
| P1 | Brax dedicated dissection（当前在 comparison 中简介） | dissection |
| P2 | Genesis dedicated dissection（2024-12 新，跟踪到 v0.5+ 时写） | dissection |
| P2 | Drake + TAMSI contact-implicit dissection | dissection |
| P3 | Contact-implicit trajectory optimization primer | primer |
| P3 | Sim2real dynamics gap survey（与视觉 gap 互补） | roadmap / inspirations |
| P3 | DiffTaichi（学术先驱） + Taichi Lang | dissection |

由 [Pulsar](https://github.com/sou350121/Pulsar-KenVersion) 自动追踪 cs.RO / cs.GR 上的新工作；旗舰新论文（如 Genesis 重大版本）由维护者人工开 dissection。

&nbsp;

---

<details>
<summary>📊 Stats</summary>

&nbsp;

**3 dissections + 1 primer + 1 comparison** · 2026-05-22 从 seed 扩展（之前仅 1 篇 PhysGaussian）

**类型分布**：
- 2 篇 dissection (MJX, Warp) — 14 项严格门槛
- 1 篇 dissection (PhysGaussian v1.1) — 已有，AGENTS.md 14 项回填
- 1 篇 primer (rigid body dynamics) — 部分 14 项
- 1 篇 comparison (Brax / MJX / Warp / Genesis) — 表格主导

**坐标系**：
- 视觉端（lane A）: 1 篇 (PhysGaussian)
- 动力学端（lane B）: 3 篇 (MJX, Warp, comparison) + 1 篇 primer

**Pulsar pipeline**：本 zone 跟踪 cs.RO + cs.GR arxiv keyword（"differentiable physics", "MuJoCo", "rigid body simulation"），命中时加入候选；旗舰版本变更（MJX major release, Genesis 1.0）由维护者人工触发 dissection 更新。

</details>

&nbsp;

---

[← Back to Foundations](../overview.md) · [→ Generative 3D Sim (视觉端互补)](../generative-3d-sim/overview.md) · [→ Spatial Math (上游数学)](../spatial-math/overview.md) · [→ World Model (决策端)](../world-model/overview.md)

*Zone landing page · 2026-05-22 expanded from seed.*
