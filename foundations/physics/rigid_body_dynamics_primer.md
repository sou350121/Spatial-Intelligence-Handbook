# Rigid Body Dynamics Primer (刚体动力学入门 — 给空间 AI 工程师)

> **发布时间**: 2026-05-22
> **核心定位**: 在读 MuJoCo / Warp / Brax 的 dissection 之前，先把"刚体动力学到底求解什么"这一层补齐。从 SE(3) 上的 twist / wrench 到 Featherstone 算法，再到 contact-implicit 方法的入门概念。

**Status:** v1 — primer 类型，遵循 AGENTS.md §「文档类型分层」: 重直觉、可省 Eureka / Napkin / Worked Example 的部分形式要求；不替代教科书（Featherstone 2008、Lynch & Park 2017）。
**TL;DR:** 机器人仿真器（MuJoCo / Isaac / Genesis / Brax）的内部循环全是同一个问题：给定关节状态 `(q, q̇)` 与外力，**前向动力学** 算 `q̈`，然后积分。本文解释这一步用到的三个概念栈：**(1)** 刚体在 SE(3) 上的运动学（twist、wrench、伴随）、**(2)** Featherstone 的递归算法把 O(n³) 降到 O(n)、**(3)** 接触约束的 LCP vs contact-implicit 两种处理路线。读完它再去看 MJX / Warp / Brax 的"差异对比表"才有锚点。

**X-Ray.** 任何 spatial AI / VLA 仿真训练背后，都有一个 "physics step" 在每帧调一次。你看见的输出（一段抓取动作、四旋翼飞行）是策略层，但 **policy 的 reward / loss 是通过 physics step 反向传播的**。如果你不知道 physics step 内部做了什么、哪里非线性、哪里 contact 让梯度变 noisy，你就不知道为什么 Brax 在某些任务上训得动而 MuJoCo 训不动、为什么 Warp 的 differentiable contact 对 manipulation 是必需的。本文是这层的导览图。

---

## 1 · 为什么 spatial AI 圈应该懂这一层

`foundations/3dgs-family/` 给你**外观**（怎么把场景渲染回来）。`foundations/physics/` 给你**因果**（如果机器人推一下、抓一下，世界会怎么响应）。前者是 sim2real 视觉端的填充物，后者是 sim2real 动力学端的填充物 —— 而 **VLA / manipulation 的策略学习几乎全在后者里跑**。

| 你在用什么 | 背后是哪种 physics |
|---|---|
| Isaac Sim / Isaac Lab | PhysX 5（NVIDIA, GPU rigid + 简化 deformable） |
| MuJoCo / MJX | Featherstone + soft contact，GPU 化的 JAX 路线 |
| Brax | JAX 上的 generalized-coord rigid body，方便端到端微分 |
| Genesis (2024-12) | 多 solver 联合（rigid + MPM + FEM + SPH），GPU |
| Drake | Anitescu / TAMSI contact，端到端可微，CPU 为主 |
| PyBullet / Bullet | 解析约束（LCP），CPU |

这些选择**不互换** —— 它们在 (a) 仿真速度、(b) contact-rich 任务上的稳定性、(c) 是否给可微梯度 上的 trade-off 不同。理解 trade-off 的前提是理解底下的数学。

> **与 `physics/physgaussian_dissection.md` 的边界**: 那一篇是"物理感知*渲染*"（MPM + 3DGS，**可变形** 视觉端）；这一篇是"物理 *动力学*"（rigid body + 接触，**控制 / 策略训练**）。两者交集少，是 physics zone 内的两条独立 lane。

---

## 2 · SE(3) 上的刚体运动 —— twist 与 wrench

刚体的 *位姿* 是 SE(3) 的元素 `T = (R, p)`（旋转矩阵 + 位置）。这一层 `foundations/spatial-math/se3_so3_lie_groups_primer.md` 已经讲透。**本文进一步**：刚体 *运动* 与 *受力* 也住在 SE(3) 的切空间（se(3) 李代数）里。

### 2.1 Twist (运动)

刚体瞬时运动用 **6 维 twist** `V = (ω, v)` 描述 — 上 3 维角速度、下 3 维线速度。在物体坐标系下表达叫 *body twist*；在世界坐标系下表达叫 *spatial twist*。两者通过 *伴随变换* `Ad_T` 切换。

```
   body twist  V_b ─── Ad_T ───►  spatial twist  V_s
                                      
   V_s = Ad_T · V_b                    
   
   Ad_T = [ R          0  ]   (6×6 块矩阵)
          [ [p]_× · R  R  ]
   
   [p]_× = p 的反对称矩阵
```

**这件事为什么重要**：当 MJX / Brax / Drake 在做"把 joint 的局部速度组合成整链的世界速度"时，本质就是一连串 `Ad_T` 乘起来。Featherstone 算法的本质就是 **以高效方式做这一连串乘法**（详后）。

### 2.2 Wrench (受力)

刚体所受合力 + 力矩用 **6 维 wrench** `F = (m, f)` 描述 — 上 3 维力矩、下 3 维力。Wrench 与 twist 是 *对偶* —— 二者通过同一伴随变换的转置切换坐标系。

`P = V^T · F` 是瞬时功率（标量），独立于坐标系选择 —— 这是 SE(3) 上 power-pairing 的标准事实。

### 2.3 牛顿-欧拉方程的 SE(3) 形式

单个刚体的运动方程在 body 坐标下：

```
   F_body = G · V̇_body + ad_V^T · G · V_body
   
   G = [ I_inertia    0     ]   (6×6 spatial inertia)
       [    0       m·I_3   ]
   
   ad_V = [ [ω]_×    0    ]
          [ [v]_×    [ω]_× ]
```

直觉：`F = ma` 在 6 维 SE(3) 上写法 = `G · V̇` 是"加速产生的惯性力"，`ad_V^T · G · V` 是"曲线运动产生的科氏 / 离心项"。三维平面跑起来时，物体不仅有 `ma`，还会有"我在转所以我感到额外的力" —— 这一项被 `ad_V^T` 抓住。

---

## 3 · Featherstone — 把 O(n³) 降到 O(n)

机器人是 *链状* 多关节系统。**朴素**计算前向动力学：

1. 写出 `n` 个广义坐标 `q ∈ R^n` 的拉格朗日 `L = T - U`
2. 求 mass matrix `M(q) ∈ R^{n×n}`、Coriolis `C(q, q̇) ∈ R^n`、gravity `g(q)`
3. 解 `M(q) · q̈ = τ - C - g`，要 `O(n³)` 解线性系统

对 7 自由度手臂还行；对 100+ 关节的人形 + 多指手就崩。

**Featherstone 1987 的 Articulated Body Algorithm (ABA)** 用递归把 forward dynamics 降到 `O(n)`：

```
   关节序号:    base ── 1 ── 2 ── 3 ── ... ── n  (tip)
   
   Pass 1 (outward):   from base to tip, propagate velocities V_i
   Pass 2 (inward):    from tip to base, propagate articulated inertias I^A
   Pass 3 (outward):   from base to tip, solve for accelerations a_i
```

每次 pass 是线性扫一遍关节链 —— 3 次 pass × n 关节 = `O(n)`。

**这件事在仿真器里出现在哪**：
- **MuJoCo / MJX**: composite rigid body algorithm (CRBA) for mass matrix + RNE for bias，然后解 `Mq̈ = τ_bias`；不直接用 ABA 但内部数学等价
- **Drake**: 显式用 RNEA / ABA
- **Brax**: generalized-coord 系统也走 ABA-类递归
- **PhysX (Isaac)**: 用 maximal-coord（每个 body 6 DoF + 约束）而非 ABA；trade-off 是更易并行、但约束求解更重

---

## 4 · 接触 —— 仿真器最难的部分

理想刚体接触是 **non-smooth**：法向力满足 *complementarity* —— 要么 gap > 0 且 force = 0（不接触），要么 gap = 0 且 force > 0（接触）。这是个 LCP（Linear Complementarity Problem），求解器需要解一个非光滑问题。

### 4.1 三大路线

| 路线 | 谁用 | 优点 | 缺点 |
|---|---|---|---|
| **解析 LCP** | Bullet / Drake (Anitescu) | 物理"正确"、刚性接触清晰 | 慢、不可微（或要 implicit-diff trick） |
| **Soft contact** (spring-damper) | **MuJoCo / MJX** | **快、可微、稳定**；GPU 友好 | 物理"软"了，强接触场景看起来 "弹"; 参数 (solref, solimp) 要调 |
| **Contact-implicit** | Posa et al. 2014; Drake TAMSI; differentiable physics 文献 | 接触约束写进 trajectory optimization，端到端可微 | 实现复杂、求解器要专门设计 |

### 4.2 MuJoCo 的 soft contact (重点)

MuJoCo 把所有约束（接触、关节限位、摩擦）统一写成 *convex optimization*：

```
   minimize over impulse j:
       (1/2) jᵀ A j + bᵀ j
   subject to:
       contact friction cones    (Coulomb 锥的椭圆近似)
       elasticity / damping (Baumgarte-like, 通过 solref/solimp 控制)
```

`A` 是约束雅可比与逆惯量的乘积（contact space inertia）。**这一公式在 MJX 里 GPU 并行批 N 个 env 的关键**：每个 env 一个独立的 convex QP，可以 N 个一起在 GPU 上跑。

参数说明：
- `solref` = (timeconst, dampratio) → 决定 contact "stiffness"
- `solimp` = (dmin, dmax, width, midpoint, power) → 决定 constraint impedance 曲线

调这两个参数是 MJX 仿真 contact-rich 任务 (peg-in-hole / grasping) 的核心工程任务。**默认参数对 manipulation 经常过软** `UNVERIFIED` —— 调参经验是 [MuJoCo Modeling 文档](https://mujoco.readthedocs.io/en/stable/modeling.html) `UNVERIFIED` 的核心一节。

### 4.3 Contact-implicit 入门概念

经典 trajectory optimization 假设接触模式 *预先指定*（"先抬腿、再落地、再蹬"）。**contact-implicit** 让 optimizer 自己决定何时接触：

```
   variables:  q_0, q_1, ..., q_T  (states)
               u_0, u_1, ..., u_T  (controls)
               λ_0, λ_1, ..., λ_T  (contact impulses) ★
   
   constraints:  dynamics:  q_{t+1} = f(q_t, u_t, λ_t)
                 complementarity:  0 ≤ λ_t ⊥ φ(q_t) ≥ 0  ★
```

`⊥` = complementarity = 接触力与穿透距离的乘积 = 0。这一行让接触模式"涌现"出来，不预先决定。

**为什么这对 spatial AI 重要**：未来 manipulation policy 训练越来越靠 differentiable simulation（梯度通过 contact 传回去），contact-implicit 是这条路的数学基础。Warp 与 Brax 的 contact-implicit 变体是当前热点。

---

## 5 · 整合 — 一个 sim step 内发生什么

```
  ┌──────────────────────────────────────────────────────┐
  │  Input: (q, q̇), control u, external wrench F_ext     │
  └──────────────────────────────────────────────────────┘
            │
            ▼
   1. Forward kinematics: q → 所有 body 的 SE(3) pose
            │
            ▼
   2. Collision detection: broad-phase + narrow-phase → contact pairs
            │
            ▼
   3. Constraint Jacobian J 计算 (contact + joint limit + tendon ...)
            │
            ▼
   4. Mass matrix M(q) 与 bias C(q,q̇)+g(q) 计算 (Featherstone-类递归)
            │
            ▼
   5. Solve convex QP / LCP for impulses λ
            │
            ▼
   6. q̈ = M⁻¹(τ + Jᵀλ - bias)
            │
            ▼
   7. Integrate: q ← q + h·q̇, q̇ ← q̇ + h·q̈ (semi-implicit Euler 或 RK4)
            │
            ▼
  ┌──────────────────────────────────────────────────────┐
  │  Output: new (q, q̇), contact info, …                  │
  └──────────────────────────────────────────────────────┘
```

**性能瓶颈分布** `UNVERIFIED` (经验值)：
- Collision detection: 30-50% (manipulation 多接触场景更高)
- Constraint solver: 20-40%
- Forward dynamics: 10-20%
- 其他 (integration / kinematics): 余下

GPU 化（MJX / Warp / Brax / Genesis 都在做）首先攻 collision + solver 这两块 —— 二者也是 contact-rich 任务的精度瓶颈。

---

## 6 · 何时该看什么

| 你在做什么 | 该深入读哪些 |
|---|---|
| 训 manipulation 策略 (PPO / SAC) | `mujoco_mjx_dissection.md` + `differentiable_physics_comparison.md` |
| 训 humanoid locomotion | `mujoco_mjx_dissection.md`（MJX 已是当前 hot path） |
| 做 sim2real 视觉 + 物理 | `physgaussian_dissection.md` + 本 zone + `../generative-3d-sim/` |
| 端到端可微（梯度通过 contact） | `nvidia_warp_dissection.md` + 看 contact-implicit 引文 |
| 调 contact 参数遇坑 | MuJoCo `solref / solimp` 文档 `UNVERIFIED` + Drake TAMSI 论文 |
| 数学补课 | Lynch & Park, *Modern Robotics* 第 8 章；Featherstone 2008, *Rigid Body Dynamics Algorithms* |

---

## 7 · 与其他 zone 的引用关系

- 数学骨架: [`spatial-math/se3_so3_lie_groups_primer.md`](../spatial-math/se3_so3_lie_groups_primer.md) — SE(3) / 李群基础，本文 §2 默认你读过
- 旋转直觉: [`spatial-math/rotation_intuition_primer.md`](../spatial-math/rotation_intuition_primer.md) — 旋转表达方式的前置教学
- 渲染端: [`physics/physgaussian_dissection.md`](./physgaussian_dissection.md) — MPM + 3DGS 视觉端，本 zone 的另一条 lane
- 仿真增广: [`generative-3d-sim/splat_sim_for_manipulation.md`](../generative-3d-sim/splat_sim_for_manipulation.md) — 视觉端的训练数据增广（与本 zone 互补）
- VLA 训练接口: `../../bridge-to-vla/` 待补 — physics-grounded VLA 训练数据

---

## 8 · 留给读者的练习

1. **手算 SE(3) twist**：刚体绕 z 轴 1 rad/s 转、同时沿 x 轴 0.5 m/s 平动 —— spatial twist 与 body twist 各是多少？（提示：`Ad_T`）
2. **MuJoCo 的 contact 不是真刚体** —— 试解释为什么扔一个钢珠到桌上，MJX 默认参数下它会 "陷进去" 0.1 mm 然后弹回来。这件事对 manipulation policy 训练是好事还是坏事？
3. **Featherstone 的 3 个 pass** 每个 pass 物理含义是什么？为什么 inward pass 是关键？

回答这 3 题后再去读 `mujoco_mjx_dissection.md`、`nvidia_warp_dissection.md` 会顺很多。

---

[← Back to Physics zone](./README.md) · [→ MuJoCo MJX Dissection](./mujoco_mjx_dissection.md) · [→ NVIDIA Warp Dissection](./nvidia_warp_dissection.md) · [→ Differentiable Physics Comparison](./differentiable_physics_comparison.md) · [→ Spatial Math primer (上游)](../spatial-math/se3_so3_lie_groups_primer.md)

*Primer type · partial 14-item template per AGENTS.md §「文档类型分层」.*
