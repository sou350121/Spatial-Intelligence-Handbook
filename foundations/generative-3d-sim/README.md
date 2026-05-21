# Generative 3D as Data Factory · Not as Planner

**Status:** v1 — opinionated lane intro. UNVERIFIED policy applies to all throughput / sim2real-gap numbers downstream.
**Scope tier:** W2 lane. Sibling to `foundations/world-model/`；不重复。

---

2025-2026 的 spatial AI 里，生成式 3D 与可微渲染面向两位明显不同的客户。**一位客户是推理时的机器人策略**，向 world model 询问"如果我这么做会怎样？"——这位客户由 `foundations/world-model/`（Cosmos / Genie / Marble）服务。**另一位客户是训练管线**，要"给我这个 manipulation 任务再来一千段、光照与杂物多样化"——这位客户在此处服务。同样的底层技术（3DGS、diffusion video、可微渲染器），完全不同的 SLA、失败模式与决策准则。

本片严格限定范围：**用于制造训练数据或桥 sim2real 的生成式 3D 系统，而非充当策略运行时的 world model**。Splat-Sim 从 100 个手机拍摄视角渲出一万条扰动后的抓取演示；Aerial Gym 把 3DGS 场景接入 Isaac 动力学，让四旋翼 RL 策略在首次真实飞行前就见过照相级森林。Mitsuba 3 与 nvdiffrast 是让梯度从像素 loss 一路回流到纹理贴图、网格顶点或 Gaussian 参数的可微渲染水管——没有这套水管，Splat-Sim 与 Aerial Gym 都不能端到端训。

## Boundary vs `foundations/world-model/`

| Question | `world-model/` answer | `generative-3d-sim/` (here) |
|---|---|---|
| 何时被调用？ | **推理期** —— 策略部署时查询 | **训练期** —— 管线每个 episode batch 调用一次 |
| 谁消费输出？ | 部署中的策略 / planner | 监督学习的 loss 或 RL rollout buffer |
| 对漂移容忍度 | 关键 —— 漂移把策略直接打死 | 容忍 —— 坏样本被过滤，永不上机器人 |
| 延迟预算 | 每步 10–100 ms | 每数据集小时到天；离线 |
| 失败模式 | 错 rollout → 错动作 | 错 rollout → 噪声梯度，由数据过滤把关 |
| Example | Genie 2 当 MPC planner；Cosmos-Predict 推理期 | Splat-Sim demo 增广；Cosmos-Transfer 作数据步 |

**Cosmos 在两片都出现是故意的**：Cosmos-Transfer（sim → photoreal RGB 用于训练）在精神上归属此处；Cosmos-Predict-as-planner 归属 `world-model/`。共享解构（`world-model/nvidia_cosmos_dissection.md`）双向覆盖——我们交叉引用而非复制。

## Recommended entry points

| File | Tier | Use case |
|---|---|---|
| `splat_sim_for_manipulation.md` | W2 🔧 [3DGS] | 给扩散策略 manipulation 做 3DGS 渲染的 demo 增广 |
| `aerial_gym_3dgs_sim2real.md` | W2 🔧 🌬️ [3DGS] | 3DGS 场景 + Isaac/Gazebo 动力学，用于无人机避障 / VIO sim2real |
| `differentiable_rendering_mitsuba_nvdiffrast.md` | W2 📖 | 一切之下的梯度水管；按任务在 Mitsuba 与 nvdiffrast 中挑一 |

## What is explicitly out of scope here

- **Genie 风格 action-conditional 视频模型当 planner** → `foundations/world-model/genie_dissection.md`
- **消费级 3D 场景生成**（Marble 主产品）→ 出本仓范围
- **per-method 3DGS 内部** → `foundations/3dgs-family/3dgs_original_dissection.md`
- **跨具身体"哪种 3DGS-sim 赢"** → `crossing/representation-migration/3dgs_as_simulator_comparison.md`
- **per-embodiment 部署落地** → `embodiments/manipulation/` 与 `embodiments/aerial/`

## The one-sentence test

如果你能回答**"这系统离线产出供 SGD 更新消费的训练样本"**，归此处。如果你能回答**"这系统在部署期跑在策略闭环内"**，归 `world-model/`。如果都答不出 —— 它是生成式媒体 demo，拿 ❌ 标签。

---

[← Back to Foundations](../README.md) · [→ World Model (sibling)](../world-model/README.md) · [→ 3DGS Family](../3dgs-family/README.md) · [→ Crossing: 3DGS-as-sim comparison](../../crossing/representation-migration/3dgs_as_simulator_comparison.md)

*Last lane review: 2026-05-21.*
