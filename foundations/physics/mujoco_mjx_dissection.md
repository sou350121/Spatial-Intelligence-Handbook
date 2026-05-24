<!-- ontology-5axis
problem: Differentiable physics simulation (rigid body)
representation: Rigid body state + contact constraints
sensor: NoSensor (simulator)
paradigm: Hybrid-DiffSim (XLA-JIT)
time: Offline-Batch / Diff-Optim
ref: ../../cheat-sheet/ontology.md §7
-->

# MuJoCo MJX Dissection (MuJoCo MJX 解构 — JAX/XLA 上的 GPU 化 MuJoCo)

> **发布时间**: 2024-初 (与 MuJoCo 3.0 同步引入)；MJX 仍为 active 开发，跟随 MuJoCo 主版本号
> **论文 / 模型**: 无独立论文 —— 源于 MuJoCo 项目 (E. Todorov, 2012, [DOI 10.1109/IROS.2012.6386109](https://ieeexplore.ieee.org/document/6386109))；MJX 是 Google DeepMind 维护的 JAX 端口
> **团队**: Google DeepMind (MuJoCo 主仓 `google-deepmind/mujoco`)
> **核心定位**: MuJoCo 物理引擎在 **JAX + XLA** 上的并行重写 —— 让 N 千个 env 在 1 张 GPU 上批量跑 RL，**不放弃** MuJoCo 的 convex contact solver 数学精度。

**Status:** v1 — 初稿，遵循 AGENTS.md 14 项 dissection 门槛。所有未亲自 verify 的具体数字（throughput / latency / memory）标 `UNVERIFIED`。
**Wedge tier:** 🔧 [Sim] (operable — 有公开 repo + PyPI + 教程)
**TL;DR:** MJX 不是新 physics —— 它是把 MuJoCo C 引擎逐函数翻成 JAX，靠 `vmap` + XLA 编译让单 GPU 一次跑 ~1000-8000 个 env `UNVERIFIED`。**核心 trade-off**：相比 MuJoCo C 版本，MJX 牺牲了一些 sequential 灵活性 (mesh collision 受限、callback 减少) 换批并行；相比 Brax，MJX 保留了 MuJoCo 的 convex contact solver（数学更严谨、参数生态多年）。**它是 2024 年起 Google DeepMind humanoid / manipulation RL 论文的默认 backend**。

### X-Ray (non-expert friendly)

(a) MuJoCo 是 2012 起为 model-based RL 设计的 C 物理引擎，contact 用 *convex optimization* 而非 LCP —— 比 Bullet 软、比 PhysX 更准。但 MuJoCo C 版本天生单线程，跑 4096 个 env 要开 4096 个进程，浪费 CPU。(b) MJX (MuJoCo on XLA) 把同一套数学翻到 JAX，用 `vmap` 一次 GPU 把所有 env 推进一步 —— **同样的物理、4 个数量级 throughput 提升** `UNVERIFIED`。(c) 对空间 AI 工程师：这是当前 humanoid locomotion / dexterous manipulation RL 训练的 default backend；如果你训 policy 而不是做 sim2real 视觉，MJX 是第一个该评估的。

### 📍 Research Landscape Timeline

```
   MuJoCo C  ─► MuJoCo open-source ─► DeepMind acquires ─► MJX (JAX) ─► MJX in DeepMind papers
   (2012)      (2021-10, Apache 2)    (2021-10)            (2024-初)    (2024-)
   Todorov      free for all          运营接手             ★ 本文        humanoid SOTA
                                                                         RL papers
                                                          
                                        ↓ peers
                                        
   Brax (Google, 2021)  ── Isaac Gym (NVIDIA, 2021) ── Genesis (2024-12)
   pure JAX rigid       GPU PhysX, 60k+ env           multi-solver, GPU
   端到端可微           但 PhysX 不可微                claims very high speed
```

MJX 不是孤立工程：它是 **GPU sim era** (2021-2026) 的 MuJoCo 阵营答案，对应 Brax (Google 自家 JAX rigid)、Isaac Gym (NVIDIA PhysX)、Genesis (Genesis-Embodied-AI 多 solver)。每家有不同 contact 数学与 differentiability 立场 —— 见 [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md)。

---

## 1 · 核心架构 / 方法总览

> 📌 **Napkin Formula**: `MJX = MuJoCo's convex contact QP solver, re-expressed in pure JAX, batched over env axis with vmap, JIT-compiled by XLA to one GPU kernel per step.`

### 1.1 组件对照表 — MuJoCo C vs MJX

| 模块 | MuJoCo C | MJX |
|---|---|---|
| 实现语言 | C (高度调优) | Python + JAX (XLA-lowered) |
| 并行单位 | per-process; OpenMP 内部 | **vmap over batch axis (env dim)**；XLA 一次出一个 GPU kernel |
| Contact solver | Newton / PGS on convex QP | **相同**数学，JAX 重写 |
| Collision detection | 多种 (mesh / convex hull / SDF / primitive) | **受限**: mesh collision 当前不支持或有限支持 `UNVERIFIED`；primitive + convex 优先 |
| MJB / XML 模型加载 | 原生 | **共用**: 同一 XML，MJX 只是不同 backend |
| Callbacks (用户 C code) | 任意 | **不支持** —— XLA 编译要纯 JAX |
| 典型 throughput (单 step, 1 env) | 高 (单线程) | 低（GPU 单 env 没意义） |
| 典型 throughput (N env 并行) | N × 单线程 (有 OpenMP 加成) | **N × 单 GPU**，N 可达数千 `UNVERIFIED` |
| 推荐场景 | sim2real 单 env validation、teleoperation | **RL 大规模训练** (PPO / SAC / DAgger) |

### 1.2 关键机制 — 把 contact QP 翻成 JAX

> ⚡ **Eureka Moment**: **MuJoCo 的 contact solver 早就是 convex optimization**（不是非凸 LCP）—— 因此它*本来就*可以被表达成静态计算图。MJX 没有改 physics，只是改 backing —— 这是为什么 "MJX 在 GPU 上跑出来的轨迹与 MuJoCo C 在数值精度内一致" `UNVERIFIED`。

MuJoCo 把所有约束（接触、关节限位、tendon、equality）统一压成一个 convex QP（见 `rigid_body_dynamics_primer.md` §4.2）。这个 QP 用 Newton (内点) 或 PGS (projected Gauss-Seidel) 求解，*步数有界*（10-100 次内迭代），且每次迭代是**确定性矩阵运算** —— 这正好是 XLA 喜欢的 workload。

MJX 的实现技巧：
1. **Padded shapes**: 不同 env 接触数量不一样，但 XLA 要 static shape → 把所有 env 都 padding 到 `max_contacts` 上限 `UNVERIFIED`，损失内存换 vectorize
2. **`jax.vmap` over env axis**: 编程上写"单 env 的 step"，自动 batch
3. **`jax.jit` with `donate_argnums`**: 状态 buffer 复用，避免 GPU memory churn
4. **`jax.scan` for inner solver loop**: convex QP 迭代 unroll 到固定步数（典型 50-100 步 `UNVERIFIED`），保证 XLA 编译

### 1.3 信息流

```
   XML model (mujoco)
         │
         ▼
   mjx.put_model() ──► mjx.Model (JAX pytree, static shapes)
         │
         ▼
   mjx.make_data() ──► mjx.Data (q, qdot, contact, etc., JAX arrays)
         │
         ▼  ┌────────────────────────────────────┐
         │  │  mjx.step(model, data) (jit + vmap) │
         │  │                                     │
         │  │  ├── forward kinematics            │
         │  │  ├── collision (primitive/convex)   │
         │  │  ├── constraint Jacobian J         │
         │  │  ├── compute M, bias               │
         │  │  ├── solve convex QP (Newton/PGS)  │
         │  │  ├── integrate (Euler/RK4)         │
         │  │  └── return new Data               │
         │  └────────────────────────────────────┘
         ▼
   new mjx.Data (q', qdot', ...)
```

整个 `mjx.step` 在 JIT 后是 *一个 XLA program*。`vmap` 之后是 N env 并行的*同一个 program*。

---

## 2 · 数学核心 — convex QP 的 vectorized 求解

> 📌 **Napkin Formula**: `find impulse j ∈ feasible_cone such that (1/2) jᵀA j + bᵀj is minimized; A = J M⁻¹ Jᵀ (contact-space inverse inertia).`

### 2.1 求解的方程

每一仿真步，MuJoCo / MJX 求解：

```
   minimize over j:
       L(j) = (1/2) jᵀ A j + bᵀ j + ψ(j)
   
   where:
       A = J · M⁻¹ · Jᵀ         (n_contact × n_contact contact-space inertia)
       b = J · q̇_unconstrained   (unconstrained velocity projected onto contact space)
       ψ(j) = barrier / penalty enforcing friction cone & impulse positivity
```

变量说明：
- `j` ∈ R^{n_contact·3}: 每个 contact 的 impulse (法向 + 2 切向 = 3 维)
- `A`: 由 Jacobian 与质量矩阵推出来的 contact-space "stiffness" 矩阵；正定 → QP 是 convex
- `b`: 不考虑约束时各 contact 点的速度
- `ψ`: friction cone 的内点 barrier（MuJoCo 用 *椭圆* 锥近似 Coulomb 锥）

> 符号与 MuJoCo 文档保持一致：[MuJoCo Computation](https://mujoco.readthedocs.io/en/stable/computation.html) `UNVERIFIED, no DOI`。

### 2.2 直觉

- `A · j = b - J · q̇_after` 是 "如果不施加 impulse j，contact 点会以速度 `J · q̇` 穿模 / 滑移"
- QP 在 friction cone 内找 *最小冲量* 把这穿模消除
- friction cone 把"摩擦力 ≤ μ × 法向力"写成可微锥约束

为什么 MJX 能 GPU 化：这个 QP 的求解是 **确定步数的矩阵迭代**，不同 env 的 `A, b, ψ` 都是固定 shape (post-padding) 矩阵 → `vmap` 直接 batch。

---

## 3 · 带数字走一遍 — 1024 env humanoid 训练

假设：

- Humanoid: 27 DoF (q ∈ R^28, qdot ∈ R^27)
- 每 env 平均 contact: ~6 (脚 + 偶尔手) `UNVERIFIED`
- max_contacts padding: ~16 `UNVERIFIED`
- Batch: 1024 env
- Solver inner: 50 Newton 迭代 `UNVERIFIED`

每步 GPU 算量（粗估，UNVERIFIED）：

- Forward kinematics + dynamics: 1024 × O(28²) ≈ 800k flops
- Mass matrix M: 1024 × O(28³) ≈ 22M flops
- Contact Jacobian: 1024 × (16 × 3 × 28) ≈ 1.4M flops
- QP inner (50 × 矩阵乘): 1024 × 50 × O(48²) ≈ 120M flops
- Integration: 1024 × O(28) ≈ 30k flops

总计 ~150M flops / step / batch → 在 A100 (~300 TFLOPS sustained) 上理论 ~0.5 μs / step / batch（**单 batch 一步**）—— 这与公开 demo 报 "1 step / ~ms range" `UNVERIFIED` 一致（剩余开销在 kernel launch + memory bandwidth）。

实际 humanoid task 公开报数 throughput `UNVERIFIED`：单 A100 上 1024-4096 env 同时 step，~30-100k env-steps/sec `UNVERIFIED`。比 MuJoCo C 单机多线程 (~10-100 env-steps/sec/core) 高约 100-1000× `UNVERIFIED`。

---

## 4 · 工程视角 — 部署约束 / 何时该用 / 何时该避开

### 4.1 何时 MJX 是赢家

| 场景 | 为什么 MJX 赢 |
|---|---|
| 大规模 RL (PPO / SAC) 训练 humanoid / quadruped locomotion | 单 GPU 4k+ env，时间 / 成本秒杀 CPU |
| Dexterous manipulation 训练 (不要求 mesh collision) | convex contact solver 数值稳；GPU batch 多样 |
| sim2real validation (Mac M-series + jax-metal) | 跨 device，无 PhysX 依赖 |
| 端到端 JAX 训练管线 (policy net 也 JAX) | XLA 一锅烩，无 Python ↔ C bridge |

### 4.2 何时 MJX 输

| 场景 | 为什么 |
|---|---|
| 复杂 mesh collision (软体 / 复杂 asset) | MJX 当前 mesh 支持受限 `UNVERIFIED` |
| 用户 callback / 自定义 C code | XLA 编译排斥 |
| 单 env 高保真 sim2real 验证 | MuJoCo C 单线程更适配 |
| Soft body / cloth / fluid | MuJoCo 本身不擅长；Genesis / Warp 更对路 |

### 4.3 部署 checklist

```
   ┌────────────────────────────────────────────────────────┐
   │ 1. XML model 用 primitive / convex hull collision      │
   │ 2. 检查 mjx 支持的 element 子集 (mjx.supported list)    │
   │ 3. batch_size 调到 GPU memory 上限 (humanoid ~ 4k-8k)   │
   │ 4. solver iterations 调小 (50 → 20) 换 throughput       │
   │ 5. 训练完成后用 MuJoCo C 单 env validate trajectory     │
   │ 6. sim2real 时 solref / solimp 重调（默认偏软）         │
   └────────────────────────────────────────────────────────┘
```

第 5 步是 production discipline：**MJX 的 trajectory 与 MuJoCo C 之间偶有数值小差异** `UNVERIFIED`（padding / float32 量化）；最终决策（"上不上机器人"）以 MuJoCo C 为准。

---

## 5 · 数据与评测

MJX 没有"训练数据" —— 它是 deterministic physics engine。但它常被作为 **RL 训练环境的物理 backend**，对应的 evaluation 是：

- **DM Control Suite** (DeepMind) — humanoid / cheetah / quadruped 标准任务
- **MyoSuite** — 肌骨建模
- **Robosuite** (UT Austin) — manipulation tasks
- **公开 DeepMind RL papers** (2024-2026) — humanoid SOTA `UNVERIFIED` 多用 MJX

公开 reproducibility: `google-deepmind/mujoco_playground` `UNVERIFIED` 是 DeepMind 维护的 MJX RL task collection；可以直接 `pip install playground` 起跑。

---

## 6 · 能力与失败模式

### 6.1 能做

- humanoid locomotion RL (rough terrain / agile movements)
- quadruped (ANYmal, Spot 模型) RL
- 简单 manipulation (box stacking, peg insertion，平面接触)
- inverse dynamics、trajectory optimization
- sim2real (DeepMind iLQR 与 MJX 集成 `UNVERIFIED`)

### 6.2 不能做（或勉强）

- 复杂 mesh collision（碗、餐具、衣物）— mesh 支持有限
- 软体 / 布料 / 流体 — 用 PhysGaussian 或 Genesis
- 真正的可微 contact（MJX 的 step 函数*可微*，但 contact-implicit 数学正确性是另一话题 — 见 §6.3）
- 极小 dt 高频接触（如打鼓、敲击）— soft contact 会"穿一点"

### 6.3 Hidden Assumptions (本节必须有 · 14 项门槛)

1. **Convex contact**: friction cone 用椭圆近似 Coulomb 锥 → 在极端 stiction 场景下与真实 Coulomb 有偏差
2. **Soft contact**: 默认 `solref = (timeconst=0.02, dampratio=1)` 让接触有 ~20ms 弹性时间常数 → 钢球落桌会 "穿 0.1mm" `UNVERIFIED` 再弹回，**这对 manipulation policy 是噪声源**
3. **静态计算图**: max_contacts padding 决定上限；动态场景接触爆发会被截断 → silent failure
4. **Float32 by default**: 长 trajectory (>10s, dt=1ms) 会累积数值误差 `UNVERIFIED`，影响 ablation 复现
5. **JAX 编译时间**: 第一次 `jax.jit` 编译可能 30s-数分钟 `UNVERIFIED` → CI 缓存策略要规划
6. **可微 ≠ 物理梯度**: MJX 给的梯度是 *通过 softened contact 的梯度* —— 对 contact-implicit 任务，这梯度可能 noisy 或局部 wrong
7. **`UNVERIFIED` benchmark numbers**: 本文 throughput 数字均出自公开报道与社区基准，未本地 reproduce

### 6.4 sim2real gap 的固定来源 (manipulation 视角)

| 来源 | 严重度 |
|---|---|
| Contact stiffness 默认偏软 | 高 (peg insertion 会"插进去过头") |
| Friction cone 椭圆近似 | 中 (滑移方向偏) |
| 无 mesh collision | 高 (碗 / 不规则形状失真) |
| 关节 actuator 默认 PD | 中 (真实电机有 backlash / delay) |
| 视觉端 (MJX 不管) | 高 — 见 `../generative-3d-sim/` |

---

## 7 · 与相关工作对比

| | **MuJoCo MJX** | **Brax** | **Isaac Gym/Lab** | **Genesis** |
|---|---|---|---|---|
| Backend | JAX/XLA | JAX/XLA | PyTorch + PhysX | C++ + CUDA (custom) |
| Contact | Convex QP, soft | Spring-damper, simplified | PhysX LCP/TGS | Multiple (MPM/FEM/SPH/rigid) |
| Differentiable | 是 (通过 soft contact) | 是 (端到端) | 否 (PhysX 不可微) | 部分 `UNVERIFIED` |
| 主要 throughput strength | Humanoid / dexterous | 简单 rigid 多 env | 视觉 + GPU rigid 大规模 | 多 solver、统一 GPU |
| Mesh collision | 受限 | 受限 | 强 | 强 |
| 上游 model 生态 | **MuJoCo XML 巨大** (10+ 年) | 自定义 | URDF + Isaac asset | URDF + 自定义 |
| 何时选 | 已有 MuJoCo 模型 / 需 convex contact 精度 | 端到端可微、简单 task | 多 GPU + 视觉训练 | Multi-physics |

详见 [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md)。

**面试 Tip**：被问 "MJX 与 Brax 区别"，答两句 —— "**同样 JAX/XLA，contact 数学不同**：MJX 复用 MuJoCo 的 convex contact QP（数值精度高、有 10 年 MuJoCo XML 模型生态），Brax 用 spring-damper 简化 contact（编译更快、更易端到端微分，但 contact 物理近似度差）。manipulation 选 MJX，端到端可微 prototyping 选 Brax。"

---

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 数据源：`google-deepmind/mujoco` issues 搜索关键词 `mjx` / `compile` / `memory` / `gradient` / `contact` / `mac`，取 2025-08 ~ 2026-05 区间 ~12 个高信号 issue。

### 8.1 实测痛点表

| Pitfall | Issue # | Status | 直接读者后果 |
|---|---|---|---|
| **macOS M-series jax>=0.7 性能崩盘 (>100×~2200× 慢)** | [#2957](https://github.com/google-deepmind/mujoco/issues/2957) | Open (2025-11) | 在 Mac 上写 prototype 必须 pin `jax<0.7`，否则单步从 0.18ms 飙到 408ms；CI 缓存策略必须锁版本 |
| MJX 在 macOS 上启用 `impl="warp"` (Warp backend) | [#2947](https://github.com/google-deepmind/mujoco/issues/2947) | Closed | M-series 上 Warp 路径已能跑，但 §8.1 表明 JAX 默认路径回退仍痛 |
| 多设备 sharded 执行 `GraphMode.WARP_STAGED` 崩溃 | [#3191](https://github.com/google-deepmind/mujoco/issues/3191) | Closed (2026-04) | 单 GPU 没事，多 GPU sharding 是新代码路径，遇崩升级到 patch 后版本 |
| Warp FFI + `donate_argnums` 在 `pmap` 下死锁 | [#2980](https://github.com/google-deepmind/mujoco/issues/2980) | Open | 多卡训练用 `pmap` + buffer donation 时偶发挂起；workaround 关掉 `donate_argnums` 换内存浪费 |
| `model.bind()` slice-of-length-1 误 squeeze batch 维 | [#3128](https://github.com/google-deepmind/mujoco/issues/3128) | Open | 写 batch=1 单 env 调试代码时形状无声崩，难追；显式 `reshape` 保维度 |
| 嵌套 `vmap` 下 `dot_general` 批维转置低效 | [#3209](https://github.com/google-deepmind/mujoco/issues/3209) | Open | 多层 vmap (e.g. env × seed) 时 XLA 出 suboptimal kernel，throughput 与单层差距大 |
| `mjx.get_data_into` 在 Warp 后端 `flexedge_J` shape mismatch | [#3109](https://github.com/google-deepmind/mujoco/issues/3109) | Closed | flexcomp / 软体 + Warp 后端组合曾全崩，已修；老版本固化 task 注意 |
| MJX 缺 differentiable distance 计算 | [#3131](https://github.com/google-deepmind/mujoco/issues/3131) | Open (feature request) | 要对距离 (避障 reward / SDF loss) 求梯度，得自己绕 —— 印证 §6.3 的"可微 ≠ 物理梯度"假设 |
| Site (quat, pos) 在不同 init 下行为不一致 | [#3029](https://github.com/google-deepmind/mujoco/issues/3029) | Open | sim2real validation 时 site 读数与 C 版本对不上，先排查 init 顺序 |
| `FRAMELINACC` / `FRAMEANGACC` 忽略 refid | [#3140](https://github.com/google-deepmind/mujoco/issues/3140) | Open | 用加速度传感器做 contact 检测或 IMU 仿真时 frame 错位，silent failure |
| Planar mesh geom Qhull 编译失败 | [#3260](https://github.com/google-deepmind/mujoco/issues/3260) | Closed (2026-05) | 印证 §6.2 "mesh 支持受限" —— 哪怕是平面 mesh 也曾炸 |
| sharded GPU 仿真 (mjwarp) 支持 | [#2837](https://github.com/google-deepmind/mujoco/issues/2837) | Open (enhancement) | 多卡分布在 2026-05 仍是 enhancement，单 GPU memory 是真上限 |

### 8.2 Repo 健康度

- **commit 频率**: 高（Issue 编号 8 个月内从 #2837 → #3260，约 400+ tickets，活跃 maintainer）
- **MJX-Warp 分支**: 2025-2026 主线工作是 **mjwarp / Warp 后端集成**（用 NVIDIA Warp 写 MJX kernel），多个 issue 围绕这条线 —— 印证 §1.1 MJX 不只是 JAX，正在向 multi-backend 演化
- **跨平台**: macOS M-series 是已知 second-class（#2957 + #2947 + #1035 [Warp 侧]），Linux+NVIDIA 是 first-class
- **多 GPU**: sharded execution 仍在打磨，单 GPU 4k-8k env 是稳定区

### 8.3 读者实务含义 (Action items)

1. **Pin JAX 版本**: macOS 开发者锁 `jax<0.7` 直到 #2957 修复；Linux 也建议在 `requirements.txt` 钉精确版本，避免 XLA 行为漂移
2. **首跑 JIT 编译预算**: humanoid + 1024 env 第一次编译可能 1-5 分钟；CI 必须缓存 `~/.cache/jax` 或预热 warmup container
3. **不要假设 `pmap` 干净**: 多卡用 `pmap` + `donate_argnums` 时加 timeout 监控（#2980）
4. **batch=1 调试用 `reshape` 而非 slice**: 避免 #3128 的 silent squeeze
5. **嵌套 vmap 慎用**: 想要 (env × seed × sample) 多层并行时，先 benchmark 是否值得 —— #3209 说明 XLA 路径未必最优
6. **mesh collision 任务三思**: #3260 等 issue 印证 §6.2 "mesh 支持受限"不是文档话术 —— 复杂 asset 真出问题
7. **想要 differentiable distance / SDF**: 别等 MJX 内置 (#3131 尚 open)，自己写或换 Warp

> **与 §6.3 Hidden Assumptions 的交叉校验**：本次 issue 扫描*确认*了原文 7 项假设里至少 4 项 (#1 convex contact 由 #3131 印证缺梯度、#3 padding 由 #3128 印证、#5 JIT 编译 30s-数分钟由 #2957 极端化、#7 benchmark 数字未本地复现) 是真实工程痛点，非纸上谈兵。

---

## 9 · 引用与资源

- MuJoCo 原始论文 (Todorov 2012)：[IROS 2012, DOI 10.1109/IROS.2012.6386109](https://ieeexplore.ieee.org/document/6386109)
- MuJoCo GitHub: `google-deepmind/mujoco` (Apache 2.0)
- MJX 文档：[mujoco.readthedocs.io/en/stable/mjx.html](https://mujoco.readthedocs.io/en/stable/mjx.html) `UNVERIFIED 链接`
- MuJoCo Playground (DeepMind RL task collection)：`google-deepmind/mujoco_playground` `UNVERIFIED`
- 上游 primer: [`rigid_body_dynamics_primer.md`](./rigid_body_dynamics_primer.md) §4.2 contact 数学
- 同 zone 对比: [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md)

---

[← Back to Physics zone](./overview.md) · [→ Primer (上游)](./rigid_body_dynamics_primer.md) · [→ NVIDIA Warp Dissection](./nvidia_warp_dissection.md) · [→ Differentiable Physics Comparison](./differentiable_physics_comparison.md)

*Dissection type · 14-item template per AGENTS.md.*
