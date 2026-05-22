# 最小 Snap 轨迹生成 (Minimum-Snap Trajectory Generation Dissection)

> 📚 **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲)
> 📜 **License**: 原始 slide 与代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本 dissection 包含改写 + 补充材料，依 BSD 3-Clause 保留 HKUST 版权声明
> 📄 **原始论文**: Mellinger & Kumar, "Minimum Snap Trajectory Generation and Control for Quadrotors", ICRA 2011

> **发布时间**：2011 (ICRA 原始论文) / 2026-03 (HKUST L4 教材改写本)
> **方法 / 工具**：Minimum-Snap Polynomial Trajectory + KKT-based QP closed-form
> **核心定位**：把四旋翼"航迹规划"压缩到 4D flat-output 空间里的多项式 QP——8 阶多项式 + 闭式 KKT，把 collision-free 航点串成"电机吃得下"的连续轨迹。

**Status:** v1 — first draft. 14 项全覆盖；L4 改写 + Mellinger 2011 + Richter 2016；未验证数字标 `UNVERIFIED`。
**Wedge tier:** Aerial planning W1（aerial 首篇 dissection；与 [`obstacle-avoidance/`](../obstacle-avoidance/) waypoint 段对接）。
**TL;DR:** Mellinger 2011 用 differential flatness 把 quadrotor 12 维动力学映射到 (x,y,z,ψ) 4D flat-output，**只规划位置 + yaw 多项式**——四阶导 snap = 差分推力，最小化它 = 最小化电机抖动。凸 QP + KKT 闭式解；L4 走 polynomial QP → endpoint-derivative reparam → selection C 三段。它是 2011 至今工业基线，胜在 **closed-form + 数值稳 + 控制器吃得下**。

### X-Ray (non-expert friendly)

(a) 四旋翼 12D 状态 + 4 电机，直接规划太高维。(b) Differential flatness：只要定好 (x,y,z,yaw) 及其导数，**12D 状态 + 4 推力都能反算**——只需在 4D 平坦空间画光滑曲线。(c) "光滑"的最优定义就是最小 snap（位置四阶导，等于差分推力）——电机最少抖、最省电。整个问题塌成有 closed-form 解的 QP。

### 📍 Research Landscape Timeline

```
Differential Flatness (Fliess 1995) → Min-Jerk human motor (Flash & Hogan 1985)
  → ★ Mellinger & Kumar 2011 ICRA (Min-Snap QP)
  → Bry & Roy 2011/15 (RRT* + min-snap belief)
  → Richter, Bry & Roy 2016 IJRR (closed-form unconstrained reparam)
  → Burri, Oleynikova et al. 2015 IROS (mav_trajectory_generation 开源)
  → Gao & Shen 2017+ (Btraj corridor-QP)
  → Wang 2022 T-RO (MINCO 时空联合)
  → Learning-based (NeuralMP / Diffusion 2024+, UNVERIFIED)
```

L4 内容卡在 **Mellinger 2011 + Richter 2016 reparam** 一段——工业现行基线，但**不含 corridor 约束**（需 corridor-QP 扩展）也**不含时间分配优化**（segment 时间外生）。MINCO 2022 是下一代答案，L4 不讲。

---

## 1 · 核心方法总览 (Overview / Architecture)

### 1.1 系统组件对比

| 模块 | I/O | 频率 | 备注 |
|---|---|---|---|
| Path planner (A*/RRT*) | 障碍图 → waypoints | 1-10 Hz | L4 后半节讲 |
| Time allocator | waypoints → `T_j` | 1× | L4 假设已知 |
| **Min-snap solver** | waypoints + `T_j` → 多项式系数 `p_j ∈ R^(N+1)`, N=7 | 1× | **本文核心**：闭式 QP |
| Trajectory evaluator | `t` → `(p,v,a,j,s,ψ,ψ̇)` | 200 Hz | `trajectory_generator.py:evaluate()` |
| Geometric controller | 期望状态 + VIO → 推力 + ω | 200-500 Hz | Mellinger 2011 § Control |

### 1.2 关键机制 — Differential Flatness

四旋翼的 `(x, y, z, φ, θ, ψ, v, ω, u_1..u_4) ∈ R^12 × R^4` 可以**完全被 `σ = (x, y, z, ψ)` 及其有限阶导数代数地表达**：

- 给定 `σ(t)`，反算所有 12 维状态 + 4 个推力。
- 推力方向 ∝ `(ẍ, ÿ, z̈ + g)` → 二阶导决定姿态。
- 角速度由 jerk 决定；角加速度 + 差分推力由 **snap** 决定。

> ⚡ **Eureka Moment**：四旋翼是 differentially flat 的，所以**从来不需要在 12 维状态空间规划**——只需在 (x, y, z, ψ) 这 4D flat-output 里画光滑曲线，姿态/角速度/推力自动算出。Snap 在物理上**就是差分推力**——最小化 snap = 最小化电机抖动 = 最省电、最容易跟。16D 最优控制 → 4D 多项式 QP。

### 1.3 信息流

```
Path Planner → waypoints → Time Allocator (T_j) → Min-Snap QP (x/y/z 解耦) →
  min pᵀQp  s.t. A_eq p = d_eq  → KKT 闭式 OR Richter reparam d_U* = −R_UU⁻¹R_CUᵀd_C
  → poly coeffs (p_x, p_y, p_z, p_yaw)
  → Trajectory(t) ≜ (p, v, a, j, s, ψ, ψ̇) @ 200 Hz → Geometric Controller
```

x/y/z 完全解耦各跑一次 QP（yaw 独立）——flatness + 多项式表达的红利。

---

## 2 · 数学核心 (Math Core)

> 📌 **Napkin Formula**：
> ```
> min ∫₀ᵀ |f⁽⁴⁾(t)|² dt    s.t.   f⁽ᵏ⁾(T_j⁻) = f⁽ᵏ⁾(T_j⁺)   for k = 0..3
>  p                                  f⁽ᵏ⁾(T_0) = x_start⁽ᵏ⁾, f⁽ᵏ⁾(T_M) = x_goal⁽ᵏ⁾, f(T_j) = waypoint_j
> ```
> 一行：在多段多项式上，最小化 snap 的平方积分，受制于"端点导数固定 + 段间 0-3 阶连续 + 中间点位置固定"。

### 2.1 单段 cost matrix Q（L4 P16）

`f(t) = Σᵢ pᵢ tⁱ`，四阶导平方积分：

```
J(T) = ∫₀ᵀ |f⁽⁴⁾(t)|² dt
     = Σ_{i,j≥4} [i(i-1)(i-2)(i-3) · j(j-1)(j-2)(j-3) / (i+j-7)] T^(i+j-7) pᵢ pⱼ
     = pᵀ Q p
```

Q ∈ R^(N+1)×(N+1) 对称半正定、解析可写。snap 取 N=7（boundary 4 + continuity 4 = 8 自由度，最低阶 2k-1=7）。

### 2.2 约束 A_eq（L4 P17-P18）

两类约束合成块带状 `A_eq p = d_eq`：

- **Derivative**（端点 / waypoint）：`f_j⁽ᵏ⁾(T) = Σ_{i≥k}[i!/(i-k)!] T^(i-k) p_{j,i} = x_{T,j}⁽ᵏ⁾`
- **Continuity**（段间 0-3 阶连续）：`[A_j −A_{j+1}][p_j; p_{j+1}] = 0`

### 2.3 标准 QP + KKT 闭式

```
min pᵀ blkdiag(Q_1,…,Q_M) p   s.t.  A_eq p = d_eq
[ Q     A_eqᵀ ] [ p ]   [ 0    ]
[ A_eq  0     ] [ λ ] = [ d_eq ]
```

参考代码 `_solve_equality_qp` 直接 `lstsq` KKT：

```python
# BSD 3-Clause, (c) 2026 HKUST Aerial Robotics Group — concept excerpt
H = 0.5*(H + H.T);  KKT = [[H, Aeqᵀ], [Aeq, 0]]
sol = lstsq(KKT, [0; d_eq]);  p = sol[:n]
```

### 2.4 Richter 2016 重参数化（L4 P20-P22）

直接 QP 在 N=7 时 condition number 极差（`T^14` 量级与 `1` 并存）。Richter 2016 IJRR trick：

- 引入 `M_j p_j = d_j`，`d_j` = segment 端点的 0-3 阶导数。
- cost 重写：`J = dᵀ M⁻ᵀ Q M⁻¹ d = dᵀ R d`。
- selection matrix `C` 把 `d` 分成 `d_C`（waypoint 位置 + 起终全部导数，**已知**）和 `d_U`（中间点 1-3 阶导，**自由**）。
- 连续性**自动满足**（左右段共享中间端点导数）。
- 无约束 QP 闭式：`d_U* = − R_UU⁻¹ R_CUᵀ d_C`。

把 ill-conditioned 约束 QP 变成 well-conditioned 无约束 QP——**工业实现普遍走这条**（ethz-asl/mav_trajectory_generation 默认）。

> 符号与 Richter 2016 / HKUST L4 P20-P22 一致；Mellinger 2011 原论文系数用 `c`，本节用 `p`。

---

## 3 · 带数字走一遍 (Worked Example)

**Setup**：3 waypoints，2 段（M=2），1D（x 轴；y/z 对称）。

```
waypoints: x_0=0, x_1=1, x_2=3 (m)    times: T_0=0, T_1=1, T_2=2 (s)
boundary:  v/a/j_start = v/a/j_goal = 0
middle pt: x_1 固定; 1/2/3 阶导 free
```

**Step 1** — N=7 → 每段 8 系数 → `p ∈ R^16`。

**Step 2** — Q 矩阵 (T=1s 简化掉 `T^(i+j-7)`)：

```
Q[i,j] = i(i-1)(i-2)(i-3)·j(j-1)(j-2)(j-3)/(i+j-7),  i,j ∈ {4,5,6,7}
Q_44 = 576,  Q_45 = 1440,  Q_55 = 4800, …   (UNVERIFIED 手算)
```

其它行/列为 0；Q 是稠密 4×4 块嵌在 8×8 稀疏壳里。

**Step 3** — A_eq 13×16：seg1 起点 (4 行 boundary) + waypoint 1 位置固定 (1) + 1/2/3 阶连续 (3) + seg2 起点 waypoint (1) + seg2 终点 (4) = **13**。16 − 13 = **3 自由度**对应中间点 (v₁, a₁, j₁)；QP 在这 3 维里最小 snap。

**Step 4** — KKT 29×29 线性系统一次 `lstsq` 出 `p ∈ R^16`。

**Step 5** — evaluate：按 `t` 落在哪段取 8 系数 `np.polyval` 拿位置；逐次求导拿 v/a/j/s（见 `trajectory_generator.py:_poly_derivative + evaluate`）。

**直觉检查**：中间点 (t=1) 速度应为**正且合理量级**（waypoint 0→1→3 加速向前）；若负，多半是约束行/列写反。

---

## 4 · 工程视角 (Engineering View)

### 4.1 阶数选择：min-jerk vs min-snap

| 准则 | N | 物理含义 | 适用 |
|---|---|---|---|
| min-acc (2nd) | 3 | 最小加速度变化 | 仅位置跟踪 |
| **min-jerk** (3rd) | 5 | 最小角速度 | 相机 gimbal / 主动跟踪 |
| **min-snap** (4th) | 7 | 最小**差分推力** | **四旋翼默认** |
| min-crackle (5th) | 9 | 推力变化率 | 罕用、数值差 |

L4 P12-P13 对照表钉死 snap ↔ 角加速度 ↔ 差分推力；Mellinger 选 snap **不是任意取**，是物理对应。

### 4.2 Time Allocation 策略

L4 假设 `T_j` 已知；工程上怎么定？

| 策略 | 做法 | 评价 |
|---|---|---|
| **Constant velocity** | `T_j = ||w_{j+1}-w_j||/v_max` | 简单；短段慢、长段可能超动力学 |
| Arc-length | `T_j ∝ 弧长 / v_target` | 速度均匀，不考虑曲率 |
| **Gradient on T** (Richter 2016) | 外层 cost = J(T) + ρ·ΣT_j 梯度调时间 | 接近最优；非凸外层迭代 |
| **MINCO** (Wang 2022 T-RO) | 时空联合，T 是决策变量 | 真最优；HKUST L4 不讲 |

工业默认：**constant velocity + dynamic feasibility check** (thrust/ω 反推) 校验时间。

### 4.3 数值稳定性

N=7 直接 QP 时 condition number 可达 `1e10+` (`UNVERIFIED`，与 T 强相关)。两条救命路径：

1. **Time normalization** — 每段归一化到 [0,1] 再缩放。
2. **Richter reparam** + 正交基（Bernstein / cosine `cos(iπt/T)`） — ethz-asl/mav_trajectory_generation 默认这条。

### 4.4 控制器接口

控制器 200 Hz 吃 `(p, v, a, j, ψ, ψ̇)`：`a → b_3,des` 给期望姿态，`j → ω_des` 给角速度前馈。**snap 仅用于 cost，控制器不吃**——这点容易混淆。

---

## 5 · 失败模式 (Failure Modes)

### 5.1 已知失败模式（L4 + Mellinger/Richter + 工业经验）

1. **撞墙** — QP **不含 corridor / obstacle 约束**；waypoint 之间的曲线会出 collision-free 走廊。修：corridor-QP (Btraj 2017) box/polytope 走廊；或加密 waypoint。
2. **速度爆掉** — `T_j` 太短 → v/a spike 超动力学。Richter 2016 cost `J_snap + ρ·ΣT_j` 外层调 ρ。
3. **Ill-conditioning** — N=7 直接 QP condition number 爆炸；见 §4.3。
4. **Yaw 解耦但耦合超限** — yaw 加速度 + 位置 jerk 通过 dynamics 耦合，总角加速度可能超 IMU 量程。
5. **航点距离悬殊** — 10 m + 0.1 m 混段使短段 ill-conditioned；合并 / 降阶到 min-jerk。
6. **长程精度损失** — 30 s+ 时 `T^14` 吃掉 32-bit 精度；用 double + time normalization。

### 5.2 Hidden Assumptions

- **Quadrotor is differentially flat** — 准静态包络内成立；aggressive maneuver（roll > 60°、推力饱和、桨叶颤振、地效）下 flatness 失效，flat-output 轨迹**不再可跟踪**。
- **No obstacles in cost** — cost 仅惩罚 snap，环境信息**全在 waypoints / corridor 里**。QP 在 waypoint 之间补的曲线对障碍无感。
- **No motor saturation in formulation** — QP 不知道 `T_min ≤ T ≤ T_max`；事后 dynamic feasibility check。
- **Segment durations known** — L4 P15 第一句明确："segment durations must be known"。
- **No disturbance / wind** — nominal trajectory；抗风靠下游控制器。
- **Yaw is independent** — 工程近似；严格不成立。
- **Continuous polynomial basis** — 默认幂基；高 N 时换正交基（§4.3）。

---

## 6 · 与其他方法对比 (Comparison)

| 方法 | 决策变量 | 障碍 | 时间优化 | 求解 | 工业 |
|---|---|---|---|---|---|
| **Min-snap (Mellinger 2011)** | 多项式系数 | ❌ | ❌ | 凸 QP + KKT 闭式 | ⚡ PX4 / Crazyswarm / AirSim 默认 |
| **Min-snap + corridor (Btraj 2017)** | 多项式系数 | ✅ box / polytope | ❌ | 凸 QP | 🔧 HKUST 系 |
| **MINCO (Wang 2022)** | 端点导数 + segment time | ✅ corridor / ESDF | ✅ | 非凸局部光滑 | 🔧 Fast-Planner / EGO |
| **RRT\* + smoothing** | 树节点 | ✅ | n/a | sampling | 📖 学术 |
| **NMPC** | 控制输入 | ✅ via cost | ✅ | NLP / SQP / IPOPT | 🔧 Acados |
| **iLQR / DDP** | 状态-控制 | ⚠️ penalty | ✅ | LQR-like | 📖 学术 |
| **NeuralMP / Diffusion (2024+)** | 神经网络 | learned | learned | inference | 📖 早期 `UNVERIFIED` |

**关键观察**：min-snap 是**唯一闭式 + 凸 + 工业大规模部署**的方法。MINCO 更优但复杂；MPC 通用但 ms 级开销；NeuralMP 没出货。→ min-snap 至今默认基线。

**与其他 embodiment 差异**：manipulation 用 min-jerk（关节平滑），ground robot 用 trapezoidal / B-spline；**只有 quadrotor 因为 flatness + snap = 差分推力，才用到四阶导最小化**——不是品味，是动力学物理特性。

---

## 7 · 工业现况 (Industrial Landscape)

| 项目 | 用法 | 状态 |
|---|---|---|
| [ethz-asl/mav_trajectory_generation](https://github.com/ethz-asl/mav_trajectory_generation) | Richter reparam + time grad | 🔧 工业基线 |
| [HKUST/Btraj](https://github.com/HKUST-Aerial-Robotics/Btraj) | min-snap + flight corridor | 🔧 Gao & Shen 2017 |
| [HKUST/Fast-Planner](https://github.com/HKUST-Aerial-Robotics/Fast-Planner) | min-snap → 后被 EGO 替代 | 📖 |
| [HKUST/EGO-Planner-v2](https://github.com/HKUST-Aerial-Robotics/EGO-Planner-v2) | B-spline + gradient（脱 min-snap） | ⚡ 当前 SOTA |
| PX4 / Crazyswarm2 / AirSim | `polynomial-7` 接口默认 piecewise min-snap | 🔧 / 🔧 / 📖 |

**趋势** (`UNVERIFIED` 2024-2026 估计)：学术前沿 (HKUST/ZJU FAST-Lab) 已转向 MINCO / EGO；工业 (PX4 / 商用 SDK) 仍以 min-snap 默认（已认证）；教育 (ETHZ / HKUST 课程、Crazyswarm) 持续用 min-snap 作教学基线——L4 这门课就是。

---

### 💼 面试 Tip

> **Q：为什么四旋翼用 min-snap 不用 min-jerk？**
> A："因为 quadrotor 是 differentially flat 的——位置的四阶导 snap 通过 flatness **直接对应差分推力**。最小化 snap = 最小化电机推力抖动 / 电流冲击 / 能耗。Min-jerk 在 manipulation 上对应关节角速度 OK，但在 quadrotor 上少了一阶（jerk 只到角速度）。HKUST L4 P12-P13 的导数对照表正是这个论点的标准展示。"
>
> **Q（追问）：为什么不上 crackle？**
> A："边际收益小——snap 已覆盖差分推力；crackle 对应推力变化率，但电调 / 电机响应频率本身就在 100-500 Hz 量级 (`UNVERIFIED`)，再高阶平滑对硬件无意义；同时 N=9 数值条件数恶化得厉害，不划算。"

---

## Cross-refs

- **同 zone**：[`../obstacle-avoidance/`](../obstacle-avoidance/)（提供 waypoints）· [`../on-board-mapping/`](../on-board-mapping/)（提供地图）· [`../vio/`](../vio/)（吃 trajectory 输出 200 Hz 状态估计）
- **跨 embodiment**：min-snap 几乎是 quadrotor 独占（ackermann car 部分 flat 但 yaw 不是独立 flat output）；manipulation 用 min-jerk（关节空间不 flat，不可直接搬）。跨域素材建议放 [`../../../crossing/`](../../../crossing/) (TBD lane)。
- **来源**：
  - Mellinger & Kumar 2011 ICRA, "Minimum Snap Trajectory Generation and Control for Quadrotors" (DOI `UNVERIFIED`)
  - Richter, Bry & Roy 2016 IJRR, "Polynomial Trajectory Planning for Aggressive Quadrotor Flight in Confined Indoor Environments"
  - HKUST ELEC5660 L4 PDF（本文主要依据）+ `assignments/proj1phase2/sim/trajectory_generator.py` (BSD 3-Clause)

---

## Boundary

本文 = `embodiments/aerial/planning/` 下方法学拆解。**在范围**：min-snap 数学推导 + QP 公式 + L4 教材逻辑 + 对比 + 工业现况。**不在范围**：跨 embodiment 对比 → [`crossing/`](../../../crossing/)（TBD）；geometric controller SE(3) 跟踪 → Mellinger 2011 后半，另文；path planning (A*/RRT*/PRM) → L4 P28+，另文；corridor-QP / MINCO / EGO 完整数学 → 各自 dissection。

---

⚙️ Moltbot 自动生成 | 2026-05-22 | HKUST ELEC5660 L4 (沈劭劼讲), BSD 3-Clause

[← Aerial README](../README.md) · [← Embodiments](../../README.md)
