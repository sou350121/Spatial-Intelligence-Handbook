<!-- ontology-5axis
problem: Differentiable physics (continuum + rigid)
representation: Particle field + rigid body
sensor: NoSensor
paradigm: Hybrid-DiffSim (CUDA kernels)
time: Offline-Batch
ref: ../../cheat-sheet/ontology.md §7
-->

# NVIDIA Warp Dissection (NVIDIA Warp 解构 — kernel-based differentiable physics framework)

> **发布时间**: 2022 (初次开源) → active development through 2026
> **论文 / 模型**: 无单一会议论文 (引用 SIGGRAPH 类教程与 GTC talks)；项目主页 [github.com/NVIDIA/warp](https://github.com/NVIDIA/warp)
> **团队**: NVIDIA (M. Macklin et al.; Position-Based Dynamics 与 FleX 系列作者)
> **核心定位**: Python-first 的 **GPU kernel 编写框架** + 内置 **可微物理 primitives** —— 让"写一段类 CUDA kernel 跑物理仿真 + 反向传播得到梯度"在 Python 一行级别可达。

**Status:** v1 — 初稿，遵循 AGENTS.md 14 项 dissection 门槛。throughput / benchmark / model size 类数字标 `UNVERIFIED`。
**Wedge tier:** 🔧 [Sim] [Differentiable] (operable — repo 公开 + Isaac Lab 已集成)
**TL;DR:** Warp 不是物理仿真器（不是 MuJoCo / Brax 的直接对手）—— 它是个**用 Python 写 GPU kernel 的 DSL，附带可微物理 primitives 库**。你可以拿 Warp 写自己的 FEM / SPH / cloth 求解器，或拿现成 primitives 做 differentiable rigid / soft body。**它是 Isaac Lab 的底层 GPU 工具链组件**（与 PhysX 并存），也是 NVIDIA 自家研究组（Macklin's lab）的 differentiable physics 实验平台。

### X-Ray (non-expert friendly)

(a) 写 GPU 物理求解器传统上要 CUDA C++，门槛极高；同时主流 ML framework (PyTorch / JAX) 对 contact-rich 物理的 differentiability 支持差。(b) Warp 让用 Python 写 `@wp.kernel` 函数，它自动 transpile 到 CUDA、自动给你 forward + backward (autodiff) —— 同时附带 rigid body / cloth / particles / FEM / SDF 的 primitive solver 模板。(c) 对空间 AI 工程师：当你需要 "GPU + Python + autodiff + 自定义 physics" 四要素同时具备时，Warp 是目前唯一好的选项 —— 但它**不是 turnkey simulator**，要自己拼装。

### 📍 Research Landscape Timeline

```
   PBD (Macklin 2007+) ─► FleX (NVIDIA, 2014) ─► Warp open ─► Warp 1.0 ─► Warp 1.x (2025-26)
                          C++ unified solver    (2022)        (2023?)      Isaac Lab 集成
                                                                            differentiable
                                                                            sim research
                                       
                                          ↓ peers
                                          
   Drake (TRI/MIT, 2014+) ── Brax (Google, 2021) ── Genesis (2024-12) ── DiffTaichi (2020)
   contact-implicit         JAX rigid               multi-solver         Python DSL → GPU
   可微 RBD                 端到端可微              统一 GPU             先驱
```

Warp 的根 = **NVIDIA Macklin's lab 把 FleX (2014) 的 unified solver 思路开放到 Python 用户**。同时与 DiffTaichi (Hu et al. 2020) 思路相通 —— Python DSL 编译到 GPU。区别：Taichi 学术导向、跨硬件；Warp 紧 NVIDIA stack、产品定位。

---

## 1 · 核心架构 / 方法总览

> 📌 **Napkin Formula**: `Warp = @wp.kernel decorator (Python → CUDA transpile) + autodiff (forward + reverse) + builtin physics primitives (rigid / cloth / SPH / FEM / collision detection / SDF).`

### 1.1 三层架构

| 层 | 职责 | 用户接触面 |
|---|---|---|
| **Core**: kernel compiler | `@wp.kernel` Python AST → CUDA C++ → PTX；JIT cache | 写 kernel |
| **AD**: autodiff engine | forward + reverse mode; tape-based | `wp.Tape()`, `loss.backward()` |
| **Sim**: physics primitives | rigid body, particles, SDF, FEM, cloth, fluid | `wp.sim.Model`, `wp.sim.State`, `wp.sim.Integrator` |

最底层是 **kernel compiler** —— 这才是 Warp 的核心创新；上面的 `wp.sim` 库相当于一组 reference implementation，可读、可改、可替换。

### 1.2 与"完整 simulator"(MuJoCo / Isaac) 的关键区别

> ⚡ **Eureka Moment**: Warp 的 differentiability **不是包在 simulator 外面的 autograd 包装**（PyTorch 那种）—— 而是**编译时 transpiler 同时生成 forward + reverse kernel**。每一个 `@wp.kernel` 写完，*backward 路径已经在 GPU 上等着了*。这是为什么 Warp 能对 contact-rich physics 给"端到端梯度"而不被 Python overhead 卡死。

对照：
- **MuJoCo / MJX**: 给你一个 simulator (XML 描述 model + step())，contact / friction 是固定的 convex QP
- **Brax**: 给你一个 simulator (Python 类描述 model + step())，contact 是 spring-damper 近似
- **Warp**: 给你一个**编程框架** —— 你写 `step(state) -> next_state` kernel，contact 数学由你决定（可以是 LCP、convex QP、contact-implicit、PBD ...）；Warp 保证你写的这个 step 自动可微

trade-off：
- 你**得到**：自定义物理 + GPU 速度 + autodiff
- 你**付出**：要自己写 / 拼物理 (虽然 `wp.sim` 给 starter kit)，没有 MuJoCo 那种"开箱即用 100 个 task"的成熟度

### 1.3 信息流 — 一个端到端可微 sim 的 minimal example

```
   Python script
        │
        ├─► @wp.kernel def step_kernel(state, params):
        │       # 用户写一段 kernel: 物理逻辑
        │       ...
        │
        ├─► model = wp.sim.Model(...)           # 用户构 model
        ├─► state = model.state()               # 初始 state
        │
        ├─► with wp.Tape() as tape:             # 开 tape 记录 graph
        │       for t in range(T):
        │           step_kernel(state, params)  # forward
        │       loss = compute_loss(state)
        │
        └─► tape.backward(loss)                 # reverse pass
            → params.grad = ∂loss/∂params       # 拿到梯度
```

注意 `tape.backward` 是 **tape-based autodiff**（PyTorch style），不是 JAX 的 trace-based。这件事影响：长 trajectory 时 memory 占用 = trajectory_length × state_size`（要存中间）；可以用 checkpointing 缓解。

---

## 2 · 数学核心 — 编译时 reverse-mode autodiff for SIMD kernel

> 📌 **Napkin Formula**: 对一个 kernel `y = f(x)`，Warp transpiler 在生成 `f` 的 CUDA code 同时生成 `f_bwd(x, y_grad) → x_grad`，逐操作应用链式法则。Contact / cone projection 这类 non-smooth op 用 subgradient 或 smoothed surrogate。

### 2.1 reverse-mode 的"双 kernel"生成

对每个 user kernel：

```
   user writes:                    Warp 生成 (背后):
   
   @wp.kernel                      __global__ void step_fwd(...) {
   def step(state, p):                ... CUDA forward ...
       v = state.v                 }
       v += p.gravity * dt
       state.v = v                  __global__ void step_bwd(...) {
       ...                            ... CUDA reverse ...
                                    }
```

两个 kernel 都 JIT 编译到 PTX。运行时：

- forward pass: 调 `step_fwd`，记录 input 状态到 tape
- backward pass: 调 `step_bwd`，从 tape 读 input、把 output gradient 沿链式法则传回

### 2.2 Non-smooth ops 的处理

接触 / 摩擦 / cone projection 本质是 non-smooth，标准 autodiff 给的梯度可能 zero (sub-gradient) 或 NaN。Warp 的处理 `UNVERIFIED`：
- 摩擦锥 projection: subgradient 路线
- 接触 LCP 解算: 通过 implicit-function theorem 得到隐式梯度，或用 smoothed-LCP surrogate
- soft contact (penalty-based): 梯度自然存在，但物理近似松

> 符号与 Warp 文档保持一致：[NVIDIA/warp - Differentiability](https://nvidia.github.io/warp/modules/differentiability.html) `UNVERIFIED 链接`。

---

## 3 · 带数字走一遍 — 软体球落地训练 stiffness

任务：用 Warp 写一个粒子-弹簧系统模拟软球落地，目标是反向传播找一组 spring stiffness 让球弹起最高。

伪代码：

```python
@wp.kernel
def spring_force(positions, velocities, stiffness, dt):
    tid = wp.tid()
    # compute spring force, apply to velocity
    ...

model = build_softball()        # N_particles ~ 1000
params = wp.array([stiffness_init], requires_grad=True)

with wp.Tape() as tape:
    state = model.state()
    for t in range(T=500):       # 5 seconds @ 100Hz
        spring_force(state.pos, state.vel, params, dt=0.01)
        integrate(state)
    loss = -max_height(state.trajectory)

tape.backward(loss)
print(params.grad)               # ∂loss/∂stiffness
```

关键事实 `UNVERIFIED`：
- forward 500 steps × 1000 particles → 单 A100 大约 10-50 ms
- backward 大约 2-3× forward time
- memory 占用：500 step × 1000 particles × ~50 bytes/state ≈ 25 MB（需要 checkpointing 才能跑长 trajectory）

这个能力 **MuJoCo / Brax 不直接给** —— MuJoCo 没 differentiable particle 系统；Brax 有 differentiable rigid 但软体支持弱。

---

## 4 · 工程视角 — Warp 在生产 stack 里的位置

### 4.1 Isaac Lab 集成

NVIDIA Isaac Lab (Isaac Gym 的后继 `UNVERIFIED`) 用 **PhysX 作 rigid body simulator** + **Warp 作辅助** (collision detection / SDF / 自定义 task code) `UNVERIFIED`。这意味着 Warp 在 NVIDIA 自家 robotics stack 里是**支撑组件**而非 primary simulator。

### 4.2 何时该选 Warp

| 场景 | 为什么 |
|---|---|
| 需要可微 contact-rich physics (manipulation 端到端) | autodiff + 自定义 contact 数学 |
| 自定义 solver (FEM / SPH / PBD) + GPU | `wp.sim` 提供 starter kit |
| Isaac Lab 训练管线里的辅助 kernel | 自然集成 |
| Sim2real research (做 system identification, learn material params) | 可微梯度返回参数 |

### 4.3 何时该避开

| 场景 | 为什么 |
|---|---|
| 已有 MuJoCo XML 模型 + 标准 RL | 直接 MJX 即可，Warp overkill |
| 简单 PPO humanoid 训练 | Brax / MJX throughput 更高、生态成熟 |
| 不想自己写 step kernel | Warp 工作量 > MuJoCo / Brax |
| 跨硬件 (AMD GPU / Metal) | Warp NVIDIA-only `UNVERIFIED` |

### 4.4 部署约束

- **GPU**: NVIDIA CUDA-capable only `UNVERIFIED`
- **Python**: ≥3.8 `UNVERIFIED`
- **License**: Apache 2.0 (open source) — 商用可
- **依赖**: 自带 CUDA toolkit 部分，无需独立装 nvcc `UNVERIFIED`
- **CI**: kernel JIT 编译需 GPU，CI 跑 unit test 要 GPU runner

---

## 5 · 数据与评测

Warp 自身无"数据集"。可信验证方式：

- 跑官方 examples（`examples/` 目录有 ~30 个 demo）`UNVERIFIED 数量`
- 与 MuJoCo 等参考 simulator 对比单步 trajectory（确认数学等价度）
- Isaac Lab 集成测试

Differentiable physics 研究文献中，**Warp 与 DiffTaichi / Brax / Drake 是 baseline pool**。具体引用论文 `UNVERIFIED`，按需到 Google Scholar 查 "differentiable physics Warp"。

---

## 6 · 能力与失败模式

### 6.1 能做

- 写自定义 GPU kernel（不限物理，graphics / 数值算法也行）
- 端到端可微的物理仿真（cloth / soft body / particles / rigid）
- Mesh / SDF 几何处理 (`wp.Mesh`, `wp.HashGrid`)
- Isaac Lab / Omniverse 集成
- System identification: 从真实轨迹反推材料参数

### 6.2 不能做（或要付代价）

- 开箱即用 RL benchmark task —— 不是 turnkey
- 跨 NVIDIA 以外 GPU `UNVERIFIED`
- 完全替代 MuJoCo 的 XML model 生态 (Warp 没 XML loader)
- 对极长 trajectory 的高效 reverse pass (tape memory 占用)

### 6.3 Hidden Assumptions (本节必须有 · 14 项门槛)

1. **CUDA / NVIDIA 锁定**: Warp 跑在 CUDA 上 —— 不跨硬件 `UNVERIFIED`，与 JAX 跨 TPU/GPU/Mac 路线相反
2. **Tape-based autodiff memory**: 长 trajectory + 大 batch → memory 爆 (checkpointing 是必备工程，不是 nice-to-have)
3. **Non-smooth gradient 假设**: 接触 / 摩擦的 subgradient 选择是"工程决定"，对某些 task 给的梯度可能 wrong direction → 需用户分析
4. **`wp.sim` 是 reference impl**：不是产品级 simulator —— 它示范"用 Warp 怎么写 physics"，物理保真度比专门 simulator (MuJoCo / Drake) 弱
5. **编译时间**: kernel 第一次跑要 JIT 编译，CI 缓存策略影响开发体感
6. **Python overhead**: 虽然 kernel 在 GPU 跑，但 Python orchestration 在 step 间仍占时间 → small batch + 高频 step 时不如纯 C++ simulator
7. **生态成熟度**: 比 PyBullet / MuJoCo / Brax 年轻；社区 example 与 task 数量较少 `UNVERIFIED`

---

## 7 · 与相关工作对比

| | **NVIDIA Warp** | **MuJoCo MJX** | **Brax** | **DiffTaichi** | **Drake** |
|---|---|---|---|---|---|
| Type | DSL + primitives | Simulator | Simulator | DSL | Simulator |
| Backend | CUDA (NVIDIA-only) | JAX/XLA (multi-device) | JAX/XLA | LLVM (multi-target) | C++ |
| Differentiable | **是 ★** (编译时) | 是 (通过 soft contact) | 是 | 是 (trace) | 是 (implicit) |
| Open physics? | **是 — 用户写** | 否 (固定 convex QP) | 否 (固定 spring-damper) | 是 | 否 (Anitescu/TAMSI) |
| Built-in primitives | rigid / cloth / SPH / FEM | rigid + soft contact | rigid | 用户写 | rigid |
| Model loading | 自己拼 (无 XML/URDF) | MuJoCo XML | 自定义 Python | 自己写 | URDF / SDF |
| Production maturity | 中 (NV 内部 + Isaac Lab) | 高 (DeepMind 用) | 中-高 (Google papers) | 中 (学术) | 高 (TRI / MIT 用) |
| 何时选 | 要可微 + 自定义 physics | 已有 MuJoCo model + RL | 端到端可微 prototyping | 学术研究 | 高保真 + contact-implicit |

详细见 [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md)。

**面试 Tip**: 被问 "Warp 是不是 MuJoCo 的替代品"，答 —— "**Warp 是 DSL，MuJoCo 是 simulator**：Warp 让你*写*物理求解器（带 GPU + autodiff），MuJoCo 给你一个固定 (convex contact) 求解器。它们是上下游关系而非竞品；Isaac Lab 同时用 PhysX 做主 rigid + Warp 做辅助 kernel 就是证明。"

---

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 数据源：`NVIDIA/warp` issues 搜索 `mac` / `apple` / `install` / `wheel` / `gradient` / `autodiff`，取 2025-07 ~ 2026-05 区间 ~14 个高信号 issue。

### 8.1 实测痛点表

| Pitfall | Issue # | Status | 直接读者后果 |
|---|---|---|---|
| **Apple Silicon 数值精度问题** | [#1035](https://github.com/NVIDIA/warp/issues/1035) | Open (backlog) | M-series 上同一 kernel 跑出与 NVIDIA 不同结果；做 cross-platform repro 要意识 |
| **Mac ARM JIT/compiler bug**: 加 print 才正常 | [#928](https://github.com/NVIDIA/warp/issues/928) | Open (2025-08) | M-series 上力计算 kernel 偶发输出全 0，加调试 print 才"修好" —— Heisenbug 警告 |
| Intel Mac 支持弃用 | [#867](https://github.com/NVIDIA/warp/issues/867) | Closed (2025-08, v1.9.0) | Intel Mac 用户切走或锁老版本；与 §6.3 "CUDA / NVIDIA 锁定"互文 |
| Warp Sim 示例在 Mac ARM 上 illegal hardware instruction | [#769](https://github.com/NVIDIA/warp/issues/769) | Closed (2025-09, v1.9.0) | 1.9.0 前 M-series 跑官方 example 直接 crash；升级 ≥1.9 |
| nightly Mac wheels 发布到 NV PyPI | [#876](https://github.com/NVIDIA/warp/issues/876) | Closed (2025-09, v1.9.1) | Mac wheel 现在可装，但要走 NVIDIA PyPI index 而非 pypi.org 默认 |
| OpenGL renderer 在 macOS 上工作 | [#834](https://github.com/NVIDIA/warp/issues/834) | Closed (2025-07, v1.9.0) | Mac 上视化 demo 长期不能跑，现已修 |
| **Parallel kernel JIT compilation race condition** | [#1474](https://github.com/NVIDIA/warp/issues/1474) | Open (2026-05) | 多线程或多进程同时触发 kernel 编译时 codegen race，编译失败 → CI 偶崩 |
| `capture_while()` 多 stream CUDA graph capture 失败 | [#1469](https://github.com/NVIDIA/warp/issues/1469) | Open | CUDA graph capture + multi-stream 组合不可用；高级用户绕开 |
| Composite augmented assignment 缺梯度 | [#1451](https://github.com/NVIDIA/warp/issues/1451) | Open (milestone 1.15) | 写 `arr[i] += val` 这种"显然该可微"的代码 backward 失效 —— Tape-based 不够通用 |
| **Source-to-source AD: cross-component advection kernel 梯度反号 (~1.6% fd_check err)** | [#1472](https://github.com/NVIDIA/warp/issues/1472) | Closed (2026-05-20) | 流体类 advection 梯度反号 → 论文复现历史可能含 silent bug；要 fd-check |
| `jax_kernel(enable_backward=True)` 梯度错 | [#1380](https://github.com/NVIDIA/warp/issues/1380) | Closed (2026-04-30, v1.14) | JAX 互操作早期梯度路径有 bug，强制升 ≥1.14 |
| Newton solver 与 CUDA graph capture 整合 | [#1431](https://github.com/NVIDIA/warp/issues/1431) | Open | 自定义 Newton 求解器（contact LCP）想用 CUDA graph 提速暂不可 |
| Kernel return type annotation 被忽略 | [#1471](https://github.com/NVIDIA/warp/issues/1471) | Open | 类型注解写了不报错也不生效 → silent 类型 bug |
| Drop Python 3.9 支持 | [#1263](https://github.com/NVIDIA/warp/issues/1263) | Closed (v1.13) | 2026 起 Warp ≥1.13 要 Py 3.10+；老 Conda env 要升 |

### 8.2 Repo 健康度

- **commit 频率**: 极活跃（v1.9 → v1.14 在 2025-07 ~ 2026-05 间 5 个 minor release），milestone 1.15 排到 2026 中
- **autodiff 是 hot zone**: #1472 / #1466 / #1437 / #1380 / #1451 都是近 6 个月修的 autodiff bug —— 印证 §6.3 假设 #3 "non-smooth gradient 假设是工程决定"
- **Apple Silicon**: 1.9.0 起官方有 wheel（#876），但精度 (#1035) + Heisenbug (#928) 尚 open —— 跨硬件可用，但不可信
- **CUDA-first** 立场未变：所有性能 path 仍按 NVIDIA 优化

### 8.3 读者实务含义 (Action items)

1. **生产用 Warp ≥1.14**: autodiff 在 1.13/1.14 大修，老版本论文复现可能拿到反号梯度（#1472）
2. **永远 fd-check 你的梯度**: Warp 的 source-to-source AD 历史上多次出 silent 反号 bug；用 `wp.fd_check` 或手写有限差对照
3. **Mac 仅作 dev**: M-series 可装（#876），但 #1035 / #928 说明数值不可信 —— production 训练仍上 NVIDIA Linux
4. **CI 不要并行编译同一 kernel**: #1474 race condition 未修；CI matrix 用串行 warmup
5. **CUDA graph + multi-stream / Newton 暂避**: #1469 + #1431 都 open，复杂场景手动管理 stream
6. **`+=` 与 row writes 求梯度有坑**: #1451 milestone 1.15；现在写 element-wise + 显式 `wp.copy` 更稳
7. **Python 版本**: Warp ≥1.13 要 Py 3.10+（#1263），与 MJX (Py 3.10+) / JAX (Py 3.10+) 链路同步

> **与 §6.3 Hidden Assumptions 的交叉校验**：本次扫描*强化*了原文 7 项假设里 #1 (CUDA 锁定 — Apple 路径开始铺但仍二等)、#3 (non-smooth gradient — #1472 实锤反号)、#5 (编译时间 — #1474 race)、#7 (生态成熟度 — 跨平台 wheel 才在 2025-09 落地)。"differentiable physics 可信"在 Warp 上仍需 fd-check 验证。

---

## 9 · 引用与资源

- GitHub: [NVIDIA/warp](https://github.com/NVIDIA/warp) (Apache 2.0)
- 文档主页: [nvidia.github.io/warp](https://nvidia.github.io/warp/) `UNVERIFIED 链接`
- 相关上游研究: Macklin et al. *Position-Based Dynamics* SIGGRAPH 类教程（具体 paper 链 `UNVERIFIED`）
- 同 zone primer: [`rigid_body_dynamics_primer.md`](./rigid_body_dynamics_primer.md)
- 同 zone 对比: [`differentiable_physics_comparison.md`](./differentiable_physics_comparison.md)
- 同类 DSL: DiffTaichi (Hu et al. 2020, [arXiv:2009.14808](https://arxiv.org/abs/2009.14808))

---

[← Back to Physics zone](./overview.md) · [→ Primer (上游)](./rigid_body_dynamics_primer.md) · [→ MuJoCo MJX Dissection](./mujoco_mjx_dissection.md) · [→ Differentiable Physics Comparison](./differentiable_physics_comparison.md)

*Dissection type · 14-item template per AGENTS.md.*
