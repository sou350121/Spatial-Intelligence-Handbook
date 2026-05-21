# Differentiable Physics 综合对照 (Differentiable Physics Frameworks Comparison)

> **发布时间**: 2026-05-22
> **核心定位**: 把 4 个主流"GPU 可微物理"框架（**Brax / MuJoCo MJX / NVIDIA Warp / Genesis**）在**架构定位 / contact 数学 / differentiability 路线 / 生态成熟度 / 何时选**五个轴上横向对比 —— 选型决策一站式参考。

**Status:** v1 — comparison 类型，遵循 AGENTS.md §「文档类型分层」：核心是横向对比表 + 决策树，不走 dissection 14 项严格门槛。所有 throughput / memory / benchmark 数字标 `UNVERIFIED`，需读者按自己 task 实测。
**TL;DR:** 没有"最好"的可微物理框架 —— 选型由 (a) 你已有的 model 生态（MuJoCo XML / URDF / 自定义）、(b) contact 数学要求（convex QP / soft / 用户自定义）、(c) 跨硬件需求（NVIDIA only / multi-device）、(d) 是否需要 multi-physics（rigid + soft + fluid）共同决定。**最大教训**：4 家的"可微"含义不同 —— Warp 是编译时可微（最严谨）、MJX/Brax 是通过 soft contact 可微（梯度物理意义打折）、Genesis 当前 differentiability 范围仍在演化 `UNVERIFIED`。

**X-Ray.** 4 个框架卡在不同位置：
- **Brax** 是 *端到端可微优先*，contact 简化 → 训快、物理粗
- **MuJoCo MJX** 是 *MuJoCo 数学 + GPU*，contact 严谨但有 soft 假设 → manipulation 现实
- **NVIDIA Warp** 是 *用户写 GPU 物理*，autodiff 编译时给 → 灵活但要拼装
- **Genesis** 是 *multi-physics 统一引擎*，对多模态仿真承诺最大 → 新、长期可信度待验证

下游 "我该选谁" 问题不是技术对比能直接答 —— 取决于你的 task 与 stack。本文给的是**怎么判断**而不是"哪家赢"。

---

## 📍 时间线（2020 → 2026）

```
   2020         2021              2022           2023            2024-初            2024-12
   ─────        ─────             ─────          ─────           ─────              ─────
   DiffTaichi   Brax              Warp open      Drake           MuJoCo MJX (JAX)   Genesis
   (DSL)        (Google)          (NVIDIA)       active dev      (DeepMind)         (multi-univ)
   学术先驱     JAX rigid          kernel DSL     contact-        ★ 本对照表 ★      multi-solver
                端到端可微        + autodiff     implicit                            GPU
   
   2021-10      
   ─────
   MuJoCo 
   open source 
   + DeepMind 
   acquires    
```

**关键节点**:
- 2021: Brax 把 "rigid body sim on JAX" 跑通 → 端到端可微 RL 成为可能
- 2022: Warp 把 "Python 写 GPU kernel + autodiff" 开放
- 2024-初: MJX 让 MuJoCo 10 年生态搬上 GPU
- 2024-12: Genesis 试图把 rigid + soft + fluid + cloth 统一到一个 GPU stack

---

## 表 1 · 架构定位（What kind of thing is it?）

| 框架 | **类型** | **底层** | **主开发者** | **License** | **GitHub repo** |
|---|---|---|---|---|---|
| **Brax** | Simulator (Python lib) | JAX / XLA | Google Research | Apache 2.0 | `google/brax` |
| **MuJoCo MJX** | Simulator (JAX backend of MuJoCo) | JAX / XLA | Google DeepMind | Apache 2.0 | `google-deepmind/mujoco` (MJX 子目录) |
| **NVIDIA Warp** | **DSL + primitives** (非 turnkey sim) | CUDA (NVIDIA only `UNVERIFIED`) | NVIDIA (Macklin's lab) | Apache 2.0 | `NVIDIA/warp` |
| **Genesis** | Simulator (multi-physics) | CUDA + custom `UNVERIFIED` | Genesis-Embodied-AI 多机构联盟 | Apache 2.0 `UNVERIFIED` | `Genesis-Embodied-AI/Genesis` |

**重大区分**：**Warp 与其他 3 个不同** —— Warp 是"写物理的工具"而不是"现成物理"。如果你只想 `pip install + 跑 RL`，Warp 不是直接对手；如果你要自定义 contact 数学或想要可微 cloth/soft，Warp 是唯一好选项。

---

## 表 2 · Contact 数学（最重要的选型轴）

| 框架 | **Contact model** | **Friction** | **Stiff contact** (e.g. 钢球) | **Soft contact** (cloth) | **真刚体可能?** |
|---|---|---|---|---|---|
| **Brax** | Spring-damper (linear) | Coulomb 近似 | ❌ 弹性 artifacts | ⚠️ 简化 | ❌ |
| **MuJoCo MJX** | Convex QP + elastic | **椭圆锥近似 ★** | ⚠️ soft (穿模 0.1mm `UNVERIFIED`) | ⚠️ 通过 tendon / soft body | ❌ (设计上 soft) |
| **NVIDIA Warp** | **用户决定** | 用户决定 | 用户实现 | **✅ FEM/PBD/SPH primitive** | **✅** (如果用户写) |
| **Genesis** | 多 solver 联合：rigid (LCP?) + MPM + FEM + SPH `UNVERIFIED` | 视 solver | ✅ rigid solver | ✅ FEM/SPH solver | **✅** `UNVERIFIED` |

&nbsp;

**重大教训**：
- **"Differentiable contact" ≠ "physical contact"** —— Brax / MJX 给的梯度是*通过 softened contact 的梯度*。对端到端 RL 训练可能 OK（梯度本来就是 noisy signal）；对 system identification / 精确 sim2real 可能误导
- **真刚体（无穿模、无弹性 artifacts）需要 LCP 或 contact-implicit**，4 家里只有 Warp（自定义）和 Genesis（声称）直接给

&nbsp;

---

## 表 3 · Differentiability 路线（"可微" 在每家是什么意思）

| 框架 | **AD 路线** | **梯度通过 contact 怎么走** | **memory cost** | **典型用途** |
|---|---|---|---|---|
| **Brax** | JAX trace-based (`jax.grad`) | spring-damper 自然平滑 → 标准梯度 | `O(T × state)` checkpointing | end-to-end policy gradient, system ID |
| **MuJoCo MJX** | JAX trace-based | convex QP 通过 implicit-function theorem `UNVERIFIED` | `O(T × state)` | RL fine-tuning, gradient-based MPC |
| **NVIDIA Warp** | **Tape-based, 编译时 forward+backward kernel 配对生成 ★** | subgradient / smoothed surrogate | `O(T × state)` (tape) | 自定义可微 sim, FEM/cloth optim |
| **Genesis** | `UNVERIFIED` (声称可微，具体范围待查) | `UNVERIFIED` | `UNVERIFIED` | multi-physics gradient research |

&nbsp;

**实操经验法则**:
- 写 RL policy + 标准 task → Brax / MJX 的 differentiability 都够
- 写 trajectory optimization 或 sim2real material learning → Warp 的可控性更强
- 长 trajectory (> 1000 steps) 的 backward → 任何一家都要 checkpointing

&nbsp;

---

## 表 4 · 生态成熟度 & 模型生态

| 框架 | **生态成熟度** | **模型格式** | **现成 task / benchmark** | **跨硬件** | **大规模训练** |
|---|---|---|---|---|---|
| **Brax** | 中-高 (Google papers, 多年) | 自定义 Python class | DM Control 类、Brax envs | JAX → GPU/TPU/CPU/Mac | ✅ 单机 4k+ env `UNVERIFIED` |
| **MuJoCo MJX** | **高 (MuJoCo 10+ 年生态) ★** | **MuJoCo XML (巨大资产) ★** | MyoSuite, Robosuite, DM Control, mujoco_playground | JAX → GPU/TPU/CPU/Mac | ✅ 单机 1-8k env `UNVERIFIED` |
| **NVIDIA Warp** | 中 (NVIDIA 内部 + Isaac Lab) | 无 (用户自拼) | examples/ 演示，但非 turnkey | **NVIDIA only `UNVERIFIED`** | ⚠️ 自己写 batch 逻辑 |
| **Genesis** | **新 (2024-12 发布)** `UNVERIFIED` | URDF + 自定义 | 演示 task; 长期 task pool 待建 | NVIDIA `UNVERIFIED` | 声称很高 throughput `UNVERIFIED` |

&nbsp;

**关键现象**：**MuJoCo XML 生态是 MJX 的护城河** —— 过去 10 年 academia + DeepMind 积累了大量精调过的 humanoid / quadruped / dexterous hand XML 模型。直接复用这些 = MJX 启动成本最低。Brax / Warp / Genesis 都要重新建模型。

&nbsp;

---

## 表 5 · 何时选谁（决策矩阵）

| 你的需求 | **第一选** | **第二选** | **避开** |
|---|---|---|---|
| 标准 humanoid / quadruped RL 训练 | **MJX** | Brax | Warp (要自拼) |
| 已有 MuJoCo XML 模型 | **MJX** (零迁移) | — | 其他都要重新建模 |
| 端到端可微 + 简单 task prototyping | **Brax** | MJX | Warp / Genesis |
| Dexterous manipulation (mesh, complex contact) | MJX (mesh 受限) `UNVERIFIED` | Genesis (声称强) `UNVERIFIED` | Brax (contact 太简化) |
| 自定义 contact 数学 / contact-implicit | **Warp** | (Drake, 但 CPU) | Brax / MJX (固定 contact) |
| Soft body / cloth / fluid + 可微 | **Warp** (`wp.sim`) | Genesis (声称) `UNVERIFIED` | Brax / MJX |
| Multi-physics (rigid + soft + fluid 一锅) | **Genesis** `UNVERIFIED` | Warp (自己拼) | Brax / MJX |
| Material parameter learning (sysID) | **Warp** | Brax | MJX (softened contact 给 noisy 梯度) |
| 跨 GPU (AMD / Metal / TPU) | **Brax** / **MJX** (JAX) | — | Warp / Genesis (NVIDIA only `UNVERIFIED`) |
| Isaac Lab / Omniverse 生态 | **Warp** (作辅助) + PhysX (主) | — | Brax / MJX (不集成) |

&nbsp;

---

## 🎯 决策树（5 秒选）

```
你要做什么？
│
├─ 训 standard RL policy (humanoid / locomotion / 简单 manip)
│   ├─ 已有 MuJoCo XML 模型              → 🌟 MuJoCo MJX
│   ├─ 想最快端到端可微 prototype         → 💫 Brax
│   └─ 在 NVIDIA Isaac Lab 生态           → Isaac Lab + PhysX (主) + Warp (辅)
│
├─ 训 manipulation (contact-rich, mesh)
│   ├─ Mesh 简单 / convex hull OK         → MJX
│   ├─ 复杂 mesh + 软体 + 流体             → Genesis `UNVERIFIED` 或 Warp (自拼)
│   └─ 需要端到端可微 contact-implicit    → 🔧 Warp
│
├─ 做 sim2real material / friction learning
│   └─ 需要严格可微梯度                    → 🔧 Warp (或 Drake CPU 版)
│
├─ 写 multi-physics demo (rigid + soft + fluid 一锅)
│   └─ 直接尝试                            → 🆕 Genesis (注意新)
│
└─ 跨硬件 (AMD / Mac / TPU) 需求
    └─ 必须 JAX 路线                        → Brax / MJX
```

&nbsp;

---

## 🚧 4 家共同未解的问题（仍 open）

| 问题 | Brax | MJX | Warp | Genesis | 状态 |
|---|:---:|:---:|:---:|:---:|---|
| **真刚体严格 LCP + GPU 高 throughput + 端到端可微** 一锅 | ❌ | ❌ | 用户拼 | ❌ `UNVERIFIED` | 学术活跃话题 |
| **大规模 mesh collision + GPU + autodiff** | ❌ | ⚠️ | ✅ (自拼) | ⚠️ `UNVERIFIED` | Warp 最近 |
| **Streaming long-horizon (10k+ steps) backward** | ❌ | ❌ | ❌ | ❌ | 通用 ML 难题 (gradient checkpointing 限制) |
| **跨硬件 + GPU + autodiff** (AMD / Mac / TPU) | ✅ (JAX) | ✅ (JAX) | ❌ | ❌ `UNVERIFIED` | JAX 路线赢 |
| **真实 dexterous manipulation 训出可上机器人 policy** | ❌ | ⚠️ (mesh 限制) | ⚠️ (要自拼) | `UNVERIFIED` | sim2real gap 是 root cause，不仅 sim |

&nbsp;

---

## 🌐 boundary — 与其他 zone 的关系

- **底层数学**: [`rigid_body_dynamics_primer.md`](./rigid_body_dynamics_primer.md) — SE(3) twist/wrench、Featherstone、contact LCP vs convex QP
- **per-engine 深度**: [`mujoco_mjx_dissection.md`](./mujoco_mjx_dissection.md)、[`nvidia_warp_dissection.md`](./nvidia_warp_dissection.md)
- **PhysGaussian (视觉端物理)**: [`physgaussian_dissection.md`](./physgaussian_dissection.md) — MPM + 3DGS 渲染；与本对照的 4 家不重叠（那是物理感知 *渲染*，本表是物理感知 *动力学*）
- **生成 sim 数据**: [`../generative-3d-sim/`](../generative-3d-sim/) — Splat-Sim / Aerial Gym / Mitsuba 是视觉端，与 physics 端互补
- **VLA 训练接口**: `../../bridge-to-vla/` 待补 — 这 4 家如何输出供 VLA 训练的数据
- **Crossing**: 跨 embodiment 比较（"manipulation vs locomotion vs aerial 各家 sim 谁赢"）— 见 `../../crossing/` 候选 wedge

&nbsp;

---

## 🔮 2-year prediction（可证伪 · 2028-05）

1. **MJX 仍是 humanoid / locomotion RL 的 default backend** (因 MuJoCo XML 生态护城河)；Genesis 不太可能在 manipulation 把 MJX 推下来 `UNVERIFIED 预测`
2. **Warp 成为 NVIDIA Isaac Lab 生态的事实 differentiable layer** —— Isaac Lab 训练用 PhysX (主) + Warp (可微辅助 kernel) `UNVERIFIED 预测`
3. **Brax 仍是端到端可微 prototyping 的最快入门，但 production 训练逐步迁移到 MJX**（XML 模型迁移摩擦小）`UNVERIFIED 预测`
4. **Genesis 的"统一 multi-physics"承诺会被实测打折** —— 多 solver 联合的数值稳定性 + sim2real gap 会暴露 `UNVERIFIED 预测`

证伪事件：
- 若 2028-05 SOTA humanoid locomotion paper 多数用 Genesis 训练 → 预测 (1)(4) 错
- 若 Isaac Lab 抛弃 Warp 转用其他可微层 → 预测 (2) 错
- 若 Brax 成为 production training 主流（公开 release 数 > MJX） → 预测 (3) 错

&nbsp;

---

## 📚 进一步阅读

- **MuJoCo MJX**: 见 [`mujoco_mjx_dissection.md`](./mujoco_mjx_dissection.md)
- **NVIDIA Warp**: 见 [`nvidia_warp_dissection.md`](./nvidia_warp_dissection.md)
- **Brax**: 论文 Freeman et al. 2021 `UNVERIFIED arXiv ID`，GitHub `google/brax`
- **Genesis**: 项目页 [genesis-embodied-ai.github.io](https://genesis-embodied-ai.github.io/) `UNVERIFIED 链接`
- **底层数学**: [`rigid_body_dynamics_primer.md`](./rigid_body_dynamics_primer.md)
- **学术总览**: Hu et al. *DiffTaichi* (2020, [arXiv:2009.14808](https://arxiv.org/abs/2009.14808)) 是这一线的学术先驱

&nbsp;

---

[← Back to Physics zone](./README.md) · [→ Primer (上游数学)](./rigid_body_dynamics_primer.md) · [→ MJX Dissection](./mujoco_mjx_dissection.md) · [→ Warp Dissection](./nvidia_warp_dissection.md) · [→ PhysGaussian (渲染端)](./physgaussian_dissection.md)

*Comparison type · 表格主导 · 不走 dissection 14 项门槛 per AGENTS.md.*
