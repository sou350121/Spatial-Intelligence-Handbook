# 四旋翼动力学与级联 PID 控制 Primer (Quadrotor Dynamics & Cascade PID Control Primer)

> **发布时间**: 2026-05-22
> **核心定位**: 进入空中实体任何深度话题（VIO / planning / event-camera）之前，先用直觉 + 推导讲清楚"为什么四旋翼能飞 + 它的内外环怎么搭"。

**Status:** v1 — primer 类型（按 [`AGENTS.md`](../../AGENTS.md) §「文档类型分层」），重直觉 + 推导，可省 Eureka / Worked Example / 面试 Tip。

> 📚 **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲) L2-L3
> 📜 **License**: 原始 slide 与代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本 primer 为改写 + 补充教材，依 BSD 3-Clause 保留版权声明
> 📄 **公开参考**: Mellinger PhD 2012 (UPenn); Vijay Kumar Coursera "Aerial Robotics"; PX4 [`mc_pos_control`](https://github.com/PX4/PX4-Autopilot/tree/main/src/modules/mc_pos_control) source

**TL;DR.** 四旋翼能飞，是因为 4 个螺旋桨的转速差分成"1 净推力 + 3 轴力矩"——刚好等于 4 个独立控制量。但 4 控制对 6 DoF 是 **under-actuated**（位置只能通过倾斜机体得水平加速度），所以工业界统一用 **cascade**：外环看位置 → 算"多少推力 + 什么姿态"，内环追姿态 → 算 3 力矩 → motor mixing 反解电机转速。这是 PX4 / ArduPilot / DJI / Skydio 共用骨架。**不读懂它就看不懂空中实体后面任何一层**——VIO 为什么 200 Hz？内环跑 500-1000 Hz。Min-snap 为什么对 snap 连续？motor input ∝ snap。事故为什么多在大姿态机动？小角度近似在那里崩。本文是空中全栈的地基。

---

## 1 · 四旋翼为什么能飞：4 motor → 4 control authority

```
   俯视图（X 形机架）:                                            
              ω1 ↻ (CCW)                                       
                ⬤                                              
                │                                              
   ω4 ↺  ⬤────●────⬤  ω2 ↺                                     
              CoM                                              
                │                                              
                ⬤                                              
              ω3 ↻ (CCW)                                       
   x_b 朝前, y_b 朝左, z_b 朝天                                  
   单个电机: F_i = k_F·ω_i², 反扭矩 M_i = k_M·ω_i² (沿 z_b)
```

**为什么 4 motor 够？** 6-DoF 刚体要 6 独立控制；但桨叶推力**只能沿 z_b**——位置必须靠倾斜机体获得水平分量。**实际独立控制只有 4 个**：

| 控制量 | 通过什么得到 | 影响什么 |
|---|---|---|
| u₁ = F_total | ω₁²+ω₂²+ω₃²+ω₄² | z 加速度，间接驱动 xy |
| u₂ = M_x (roll) | l·(F₂−F₄) | 绕 x_b → 驱动 y |
| u₃ = M_y (pitch) | l·(F₃−F₁) | 绕 y_b → 驱动 x |
| u₄ = M_z (yaw) | M₁−M₂+M₃−M₄ | 绕 z_b → 直接 yaw |

`l` = 臂半长。对角桨同向旋转（CCW-CCW-CW-CW）—— roll/pitch 力矩来自**对角推力差**，yaw 力矩来自**对角反扭矩差**。**4 控制 / 6 DoF = under-actuated**：位置 (x,y) 不可直控，必须经姿态——这就是 cascade 的根因。

---

## 2 · 电机模型：从期望转速到实际转速

HKUST L2 的一阶模型：

```
   ω̇_i  =  k_m · (ω_i^des − ω_i)         (一阶滞后, τ_m = 1/k_m)
   F_i  =  k_F · ω_i²                      (推力 ∝ 转速²)
   M_i  =  k_M · ω_i²                      (反扭矩 ∝ 转速²)
```

**为什么是平方？** 桨叶升力 ∝ 速度² × 面积 × 升力系数——空气动力学结果，非工程约定。

HKUST sim 默认值（`proj1phase1/sim/model.py`，500 g class）：

```
   k_F   = 6.11e-8  N·s²              (UNVERIFIED, sim 默认)
   k_M   = 1.5e-9   N·m·s²            (UNVERIFIED)
   l     = 0.175 m
   ω_hover ≈ √(m·g/(4·k_F)) ≈ 4480 rad/s ≈ 42800 RPM   (UNVERIFIED, sim 内自洽)
   τ_m race quad ≈ 20-30 ms    大型穿越 ≈ 50-80 ms     (UNVERIFIED)
```

> 简化忽略了 thrust-induced velocity（地效、平移导致的推力变化）—— 出货飞控会做经验拟合，primer 阶段忽略。

---

## 3 · 6-DoF 刚体运动方程：Newton + Euler

**平动（Newton, world frame）：**

```
   m·p̈_a = [0; 0; −m·g] + R_ab · [0; 0; F_total]
```

机体倾斜 → 推力方向倾斜 → 出现水平加速度。**这就是位置控制必须通过姿态控制的根源**。

**转动（Euler, body frame）：**

```
   M_b  =  I_b · ω̇_b  +  ω_b × (I_b · ω_b)
                              └────── 陀螺耦合项 ──────┘
```

机臂近对称 → `I_b ≈ diag` → 陀螺项数量级比 `I·ω̇` 小一档，但**剧烈机动不能忽略**。

**姿态运动学：Z-X-Y Euler（HKUST 约定）：**

```
   R_ab  =  R_z(ψ) · R_x(φ) · R_y(θ)               [ZXY 序]
   φ=roll, θ=pitch, ψ=yaw                                       
   奇异点: cos φ = 0, i.e. roll = ±90°                          
   (vs 航空 ZYX 序奇异在 pitch ±90°)                            
   
   Body 角速度 ↔ Euler 角速度:
     ω_x = c_θ·φ̇ − c_φ·s_θ·ψ̇
     ω_y = θ̇ + s_φ·ψ̇
     ω_z = s_θ·φ̇ + c_φ·c_θ·ψ̇
   悬停附近 ω ≈ (φ̇, θ̇, ψ̇)
```

> **ZXY 选型动机**：x_b 朝前，悬停 φ=θ=0，奇异点 roll=±90° 正常飞行遥不可及；而航空 ZYX 在 pitch=±90° 奇异。跨库迁移要做单位测试。

**完整 13-state EOM（HKUST sim 用四元数）：**

```
   state = [x,y,z, ẋ,ẏ,ż, q_w,q_x,q_y,q_z, p,q,r]
   ṗ_world  = v_world
   v̇_world  = R(q)·[0;0;F]/m + [0;0;−g]
   q̇        = ½·Ω(ω_b)·q  +  K_quat·(1−‖q‖²)·q    ★ 见 §4
   ω̇_body   = I⁻¹·(M − ω×I·ω)
```

---

## 4 · ★ HKUST 的四元数归一化技巧：`K_quat·(1−‖q‖²)`

**大多数教科书不强调的工程细节**。HKUST `dynamics.py` 第 62-64 行：

```python
   K_quat = 2.0
   quaterror = 1.0 - (qW*qW + qX*qX + qY*qY + qZ*qZ)
   qdot = -0.5 * Ω(p,q,r) @ q  +  K_quat * quaterror * q     # ← 这一项
```

**问题**：单位四元数应 `‖q‖=1`，但 RK4/Euler 积分浮点误差 → `‖q‖` 缓慢漂离 1 → 旋转不再是合法 SO(3)。常规做法是积分后 `q←q/‖q‖`，但引入数值不连续。

**HKUST trick**：在动力学里加反馈回拉项 `K_quat·(1−‖q‖²)·q`：

- `‖q‖² > 1` → 项为负 → 拉向原点
- `‖q‖² < 1` → 项为正 → 推离原点
- `‖q‖² = 1` → 项为 0 → 无影响

等价于在 `‖q‖=1` 球面上加吸引子。`K_quat = 2.0` 是工程经验（UNVERIFIED）。**这改变了系统拓扑**——本来 `q ∈ S³`，加 K_quat 后系统活在 `R⁴` 里、`S³` 作为吸引子。对 RK45 自适应步长仿真特别友好（硬约束会让步长被砍）。PX4 用每步 renormalize 是另一条路。

---

## 5 · 级联控制结构：为什么不能一步到位？

直接 MIMO 从位置误差算 motor PWM 可行（NMPC 现在就是），但工业界 99% 是 cascade：

```
   Trajectory Planner — p_des, ṗ_des, p̈_des, ψ_des
            │
            ▼
   Outer: Position Controller (50–250 Hz)
     e_p = p_des−p,  e_v = ṗ_des−ṗ
     p̈_c = p̈_des + K_d·e_v + K_p·e_p
     u₁  = m·(g + p̈_c[z])
     φ_c, θ_c ← from p̈_c[x,y] + current ψ
            │ u₁, (φ_c, θ_c, ψ_des)
            ▼
   Inner: Attitude Controller (250–1000 Hz)
     PD on Euler error → φ̈_c, θ̈_c, ψ̈_c
     M = I·[φ̈_c, θ̈_c, ψ̈_c]ᵀ + ω×I·ω
            │ u₁, M
            ▼
   Motor Mixing (algebraic invert) → ω_i^des
```

**为什么 cascade 工程上赢？** 三理由：

1. **时间尺度分离**。姿态 τ ≈ 10-50 ms，位置 τ ≈ 100-500 ms。内环跑快、外环跑慢，gain 互不干扰（singular perturbation 保证）。
2. **失败隔离**。VIO 短暂丢数 → 外环冻结 → 内环 100% 工作 → 飞机停在原地不炸。一体化控制器丢数据全栈瘫痪。
3. **gain 可调**。每环 2-3 个 gain 单独 step response 测；一体化 12+ gain cross-coupled 几乎不可调。

> 内外环频率比通常 ≥4×。这就是 aerial IMU 1 kHz、状态估计 200 Hz、位置控制 50-100 Hz 的层级根因——和 [`vio/`](./vio/) 头部"200 Hz / 10 ms" 约束完全对偶。

---

## 6 · 位置 PID + 姿态 PD：完整公式

### 6.1 外环 Position PID（HKUST L3）

```
   误差:  e_p,i = p_des,i − p_i,    e_v,i = ṗ_des,i − ṗ_i
   PID:   p̈_c,i = p̈_des,i + K_d,i·e_v,i + K_p,i·e_p,i + K_i,i·∫e_p,i dτ
   
   z 直接给推力:  u₁ = m·(g + p̈_c,z)
   xy 给目标姿态（小角度线性化下）:
     φ_c = (1/g)·( p̈_c,x·sin ψ  −  p̈_c,y·cos ψ )
     θ_c = (1/g)·( p̈_c,x·cos ψ  +  p̈_c,y·sin ψ )
```

**关键 trick**：xy 加速度被翻译成 roll/pitch 目标—— **这就是 cascade 衔接点**。注意 `ψ` 用**当前**偏航（非 commanded），因为要在当前机体姿态下分解期望加速度。

### 6.2 内环 Attitude PD

```
   [φ̈_c; θ̈_c; ψ̈_c]  =  [K_p,φ(φ_c−φ) + K_d,φ(φ̇_c−φ̇);
                          K_p,θ(θ_c−θ) + K_d,θ(θ̇_c−θ̇);
                          K_p,ψ(ψ_c−ψ) + K_d,ψ(ψ̇_c−ψ̇)]
   
   M  =  I·[φ̈_c; θ̈_c; ψ̈_c]  +  ω × I·ω        ← 陀螺补偿
```

### 6.3 Gain tuning 直觉

| 参数 ↑ | 上升时间 | 超调 | 稳态误差 | 调节时间 |
|---|---|---|---|---|
| K_p ↑ | ↓ | ↑ | ↓ | — |
| K_d ↑ | — | ↓ | — | ↓ |
| K_i ↑ | ↓ | ↑ | 消除 | ↑ |

**实战 tune 顺序**：

1. **先内环、后外环**——倒过来内环响应一直变，外环没法收敛。
2. 内环 K_d=K_i=0，加 K_p 到 step 响应轻微 overshoot → 记录 `K_u`、振荡周期 `T_u`。
3. Ziegler-Nichols PD: `K_p = 0.8·K_u, K_d = K_p·T_u/8`。
4. 外环重复，但**只测 z**（roll/pitch 间耦合弱，z 完全解耦）。
5. xy 通道经 `1/g` scaling，gain 可复用 z 数量级。

> 生产飞控（PX4）还有 anti-windup、K_d 低通滤波、attitude rate inner-inner loop 等——从教科书 PD 到 production 的距离。

---

## 7 · Differential Flatness：为什么轨迹生成可以解耦?

`Mellinger & Kumar 2011` 证明：**四旋翼是 differentially flat system，flat output = (x, y, z, ψ)**。12-dim state + 4-dim input **全部能写成这 4 个 flat output 及导数的代数函数**。

**工程后果**：轨迹生成只需在 4-dim flat space 里搞——选 `(x(t), y(t), z(t), ψ(t))`，剩下全反算。Min-snap / min-jerk 只优化 position + yaw、不直接管 attitude，就是这原理。

为什么是 snap（`p⁽⁴⁾`）不是 jerk？**Motor input ∝ moment ∝ snap**——snap 连续 ⇔ motor input 连续 ⇔ 不出现电机突变 ⇔ 减少桨叶气动激励。

→ 完整推导与 QP 优化细节去 [`planning/min_snap_dissection.md`](./planning/min_snap_dissection.md)（TBD）

---

## 8 · 隐含假设清单（Hidden Assumptions, 不成立时公式会崩）

按破坏严重程度排序：

1. **小角度近似（外环 xy → φ/θ 反解）**。`φ_c = ...sin ψ − ...cos ψ` 是**线性化版**——超过 ±30° 时偏离精确反解 ≥5%。Race quad / agile flight 必须用 [Lee et al. 2010 SE(3) controller](https://arxiv.org/abs/1003.2005) 替代。
2. **无风 / 无地效**。Newton 方程假设外力仅重力 + 推力。低空 (&lt;1 桨径) 地效让有效推力 +5-15%（UNVERIFIED）。强阵风 (>5 m/s) 需外环加 disturbance observer。
3. **对称惯量 `I_b = diag, I_xx ≈ I_yy`**。X 机架成立。但**载荷不对称**（挂相机/抓手）让非对角项出现 → `ω×I·ω` 放大 → roll/pitch 串扰。
4. **电机响应是最快的（dominant pole）**。若 `τ_m` 接近内环周期，时间尺度分离失效。出货飞控 ESC 必须 ≥4× 内环带宽（race quad 用 BLHeli_32 就是这理由）。
5. **位置/姿态可观且 IMU 不饱和**。VIO 失锁 / IMU 桨叶噪声饱和时，两环输入崩——见 [`vio/`](./vio/) "四条非协商约束"。
6. **推力可瞬时反转**。实际有下界 `F_min ≈ 0.05·m·g`（HKUST sim）—— z 向急减速能力受限，**下落比上升慢**。
7. **`F = k_F·ω²` 不依赖前进速度**。其实平移时 thrust 微降；PX4 经验修正，HKUST sim 忽略。

---

## 9 · 四旋翼之外：hexa / octo / tilt-rotor / coaxial

| Airframe | # motors | Control authority | 关键差异 |
|---|---|---|---|
| Quadrotor (X) | 4 | 4 | no redundancy — 1 电机失效就坠 |
| Hexacopter | 6 | 4 | over-actuated — 1 电机 fail-graceful |
| Octocopter (coplanar) | 8 | 4 | 双倍冗余 + 更高载重，控制律不变 |
| Octocopter (coaxial 4×2) | 8 | 4 | 紧凑，下桨在上桨尾流中效率降 15-20% (UNVERIFIED) |
| Tilt-rotor | 4 + servo | 5-6 | 桨侧倾 → 非 under-actuated，但耦合极强 |
| Bicopter (V-tail) | 2 + 2 servo | 4 | 紧凑，yaw 很弱 |

> 控制律骨架（cascade + PD on attitude + flatness）在所有 multirotor 上不变；变的是 motor mixing 矩阵 + 失效模式 + 冗余分配。固定翼 / VTOL / 直升机带 aerodynamics，控制律完全不同，不在本 primer 范围。

---

## 10 · 该读什么

- 真机控制律细节 → **Mellinger PhD 2012** Ch.2-3 (UPenn)
- 视频版教学 → **Vijay Kumar Coursera "Aerial Robotics"**
- 生产代码 → **PX4** `mc_pos_control` + `mc_att_control`
- 大姿态机动 / 摆脱 Euler 奇异 → **Lee et al. 2010** "Geometric tracking control on SE(3)" [arXiv:1003.2005](https://arxiv.org/abs/1003.2005)
- 轨迹优化 → [`planning/min_snap_dissection.md`](./planning/min_snap_dissection.md)（TBD）
- SO(3) / 四元数底层 → [`foundations/spatial-math/rotation_intuition_primer.md`](../../foundations/spatial-math/rotation_intuition_primer.md)
- Cascade 在 state estimate 端的对偶 → [`vio/`](./vio/) "200 Hz / 10 ms" 一节

---

## 11 · 练习题（自测）

**Q1**. 500 g X-quad, `k_F = 6.11e-8`, `l = 0.175`, `k_M = 1.5e-9`。给 `ω = (4500, 4400, 4500, 4400) rad/s`。算 (a) 净推力 (b) 三轴力矩。

提示（UNVERIFIED 计算）：

```
  F = k_F·(ω₁² + ω₂² + ω₃² + ω₄²) ≈ 2.42 N
  M_x = l·k_F·(ω₂² − ω₄²) = 0        (对角对称无 roll)
  M_y = l·k_F·(ω₃² − ω₁²) = 0        (对角对称无 pitch)
  M_z = k_M·(ω₁² − ω₂² + ω₃² − ω₄²) ≈ 2.67e-3 N·m   (CCW 桨稍快 → yaw)
```

**Q2**. 给 `R_des` ∈ SO(3)，当前 `R`、`ω = 0`、`I = diag(...)`。写 SE(3) 几何控制 (Lee 2010) 的 moment 输出。

提示（超出 ZXY Euler，用李代数）：

```
  e_R = ½·vee(R_desᵀ·R − Rᵀ·R_des)        (rotation error in so(3))
  e_ω = ω − Rᵀ·R_des·ω_des
  M   = −K_R·e_R − K_ω·e_ω + ω × I·ω
```

`e_R` 用李代数（非 Euler 角差），完全避开 gimbal lock——race quad 必备。

---

## 12 · Cross-refs

- 上游数学（旋转表达 + SO(3)）：[`foundations/spatial-math/rotation_intuition_primer.md`](../../foundations/spatial-math/rotation_intuition_primer.md)
- 上游数学进阶（李群）：[`foundations/spatial-math/se3_so3_lie_groups_primer.md`](../../foundations/spatial-math/se3_so3_lie_groups_primer.md)
- 四元数 Hamilton vs JPL：[`foundations/spatial-math/quaternions_and_rotations.md`](../../foundations/spatial-math/quaternions_and_rotations.md)
- 状态估计（cascade 输入端）：[`embodiments/aerial/vio/`](./vio/)
- 轨迹规划（cascade 上游）：[`embodiments/aerial/planning/`](./planning/)
- 跨实体控制频率对比：[`embodiments/aerial/README.md`](./overview.md) §3

## Boundary

本文是 quadrotor **入门 primer**——只到"为什么飞 + cascade PID"为止。深度话题归属：

- 大姿态机动 (Lee 2010, Mellinger 2011) → 单 paper dissection 或本 zone code-notes
- NMPC / RL controller → [`embodiments/aerial/obstacle-avoidance/`](./obstacle-avoidance/)
- VIO / state estimation → [`vio/`](./vio/)
- Motor / ESC / 桨叶物理 → `foundations/sensor-physics/` (待写) + [`sensor-stack/`](./sensor-stack/)
- 跨实体（aerial 控制频率 vs ground/manip）→ `crossing/`（不在本目录）

## References

- HKUST ELEC5660 *Introduction to Aerial Robotics* (2026 Spring) [course site](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics) — L2+L3 slides + proj1 sim. License: BSD 3-Clause.
- Mellinger, D. (2012) *Trajectory Generation and Control for Quadrotors*. PhD, UPenn. [link](https://repository.upenn.edu/edissertations/547/) — 四旋翼工程化建模现代经典。
- Lee, T., Leok, M., McClamroch, N.H. (2010) *Geometric tracking control of a quadrotor UAV on SE(3)*. CDC 2010. [arXiv:1003.2005](https://arxiv.org/abs/1003.2005)
- Mellinger, D., Kumar, V. (2011) *Minimum Snap Trajectory Generation*. ICRA 2011. [IEEE](https://ieeexplore.ieee.org/document/5980409) — differential flatness 奠基。
- Murray, R.M., Li, Z., Sastry, S.S. (1994) *A Mathematical Introduction to Robotic Manipulation*. CRC. [free online](https://www.cds.caltech.edu/~murray/mlswiki/index.php/Main_Page) — HKUST L2 第 46 页引用。
- Vijay Kumar Coursera *Aerial Robotics* (Penn) [link](https://www.coursera.org/learn/robotics-flight) — 视频 + cascade 工程讲法。
- PX4 [`mc_pos_control`](https://github.com/PX4/PX4-Autopilot/tree/main/src/modules/mc_pos_control) / `mc_att_control` source — production cascade 实现，与 textbook 距离一看便知。

---

[← Back to Aerial](./overview.md)
