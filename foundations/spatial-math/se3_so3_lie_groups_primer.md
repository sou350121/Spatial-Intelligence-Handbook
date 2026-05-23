# SE(3) / SO(3) Lie Groups Primer (李群入门：旋转与刚体变换)

> 💡 **觉得本文太硬？先读** [`rotation_intuition_primer.md`](./rotation_intuition_primer.md) — 从手机翻转开始的前置教学，0 SLAM 背景即可。

> **发布时间**: 2026-05-21
> **核心定位**: 2010 年以来每一个 SLAM 优化器、IMU 积分器、pose-graph 后端背后那个所有人都默认你会的前置数学。

**Status:** v1 —— primer。`UNVERIFIED` 数字已 inline 标注。
**TL;DR:** 旋转和刚体位姿**不**住在向量空间里 —— 你不能朴素地把它们求平均、相减、对它们求 Jacobian。李群 / 李代数这个 trick 把它们通过 `exp` / `log` 在局部映射到 R³ / R⁶，让微积分重新能用。每一个 BA solver、EKF、IMU 预积分器都默默靠它。

**X-Ray.** 一个 rotation matrix 有 9 个 entry 但只有 3 个自由度 —— 六个约束把它钉在一个弯曲的流形上。优化器想要的是平直的 R³。李代数 `so(3)` 就是 identity 处的切空间：一个 3-向量。在切空间上扰动，再 `exp` 回流形。SE(3) 把它扩展成 6-DoF 位姿。每篇 SLAM 论文里那句"在位姿上扰动 δ"，本质都是切空间更新 —— 不是朴素加法。（中文直觉：旋转不是向量，但它的"小扰动"是向量。）

## 📍 研究全景时间线

```
1850       2003              2013             2018          2024           2026
Lie groups► HZ unit-quat ► Strasdat Sim(3) ► Sola tutorial► VGGT bypasses► YOU ARE HERE
math        SLAM canonical  loop scale drift  arXiv 1812.01537 for SfM     classical still
                                                                            runs aerial VIO
```

Sola 的 *Lie Groups for 2D and 3D Transformations* (2018) 是每个 SLAM 实验室都在用的速查表。

---

## 1 · 架构：把旋转当流形，不当向量

### 1.1 朴素参数化为什么会崩

任何 3-参数旋转表示（Euler、轴角）都会撞到**万向锁**或奇点。Rotation matrix（9 个数）经过一次 Gauss-Newton 之后会漂出 SO(3)。Quaternion（4 个数 + 1 个约束）避开了 lock 但需要重新归一化。李群的做法：把 `R ∈ SO(3)` 原样保留；把*更新*表达在切空间 `so(3) ≅ R³` 里。

| 对象 | 群（流形） | 代数（切空间） | 维度 |
|---|---|---|---|
| 旋转 | SO(3) | so(3) | 3 |
| 刚体位姿 | SE(3) | se(3) | 6 |
| 带尺度位姿（闭环） | Sim(3) | sim(3) | 7 |

### 1.2 ⚡ Eureka Moment

> **旋转住在一个弯曲的 3 维流形上，但 identity 处的切空间是平直的 R³ —— 把状态存在流形上，把优化跑在切空间上。**

这个 trick 让 BA 能收敛，让 EKF 能在 SO(3) 状态附近线性化，让 IMU preintegration 能把 δθ 当向量来累积。剩下都是记账问题。

### 1.3 信息流

```
   manifold (curved)              tangent (flat)
   R ∈ SO(3)  ── log() ───►  φ ∈ so(3) ≅ R³
   T ∈ SE(3)  ◄── exp() ──   ξ ∈ se(3) ≅ R⁶
        ▲                            │
        └──────── R ← R · exp(δφ) ───┘
                  (right perturbation)
```

`exp` / `log` = matrix exponential / log —— SO(3) 上有闭式（Rodrigues）。

---

## 2 · 数学核心：exp / log 与 BCH 公式

### 📌 Napkin Formula

```
R = exp(φ̂)       φ ∈ R³,  φ̂ = skew(φ)         (Rodrigues)
T = exp(ξ̂)       ξ = (ρ, φ) ∈ R⁶               (SE(3))
exp(â)·exp(b̂) ≈ exp(â + b̂ + ½[â,b̂] + ...)     (BCH)
```

Skew 把 3-向量提升为 3×3 反对称矩阵。Rodrigues（SO(3) exp 闭式）：

```
θ = |φ|, û = φ/θ
R = I + sin(θ) û + (1-cos θ) û²
```

**右扰动 vs 左扰动:**

```
right: R_new = R · exp(δφ̂)        (body frame)
left:  R_new = exp(δφ̂) · R        (world frame)
```

ORB-SLAM3 / 大多数 C++ 优化器用**右扰动**；某些 EKF 用左扰动。混用会悄悄把 Jacobian 取反 —— "我的 SLAM 发散了" 报告的前三名原因 `UNVERIFIED`。

| 符号 | 住在 |
|---|---|
| `R` | SO(3)（3×3 正交） |
| `φ` | so(3) ≅ R³（旋转向量） |
| `T = [R, t]` | SE(3)（4×4 齐次） |
| `ξ = (ρ, φ)` | se(3) ≅ R⁶（twist；`ρ` ≠ 直接的 translation —— Sola 2018） |

---

## 3 · 玩具例子：小角度往返

取 `φ = (0.01, 0, 0)` rad —— 绕 x 轴 0.57°。走一遍 exp → R → log：

```
θ = 0.01,  û = (1, 0, 0),  sin θ ≈ 0.00999983,  1-cos θ ≈ 5e-5

       [ 1   0          0         ]
R  ≈  [ 0   0.99995   -0.00999983 ]
       [ 0   0.00999983  0.99995  ]

log(R) = θ·û = (0.01, 0, 0)   ✅ round-trip
```

复合 `R_a = exp(0.01 x̂)`、`R_b = exp(0.01 ŷ)`：

```
R_a · R_b = exp( (0.01, 0.01, 0) + ½·[x̂, ŷ] + higher )
```

`½ [â, b̂]` 那一项是 **BCH 修正**。在 0.01 rad 时它约 5e-5；到 0.5 rad 它就主导了。

**工程影响.** IMU preintegration 每个相机帧累积约 1000 次微旋转。当成可交换会累积 O(N·θ²) 的误差。Forster *T-RO 2017* 就是那套把 BCH 误差压住的记账法。

---

## 4 · 工程视角：代码到底在做什么

| 操作 | Sophus 写法 | 代价 |
|---|---|---|
| 存位姿 | `Sophus::SE3d T`（quat + 3-vec） | 7 double |
| 施加扰动 | `T = T * SE3d::exp(xi)` | ~50 flops |
| 在 `T` 处线性化 | 右 Jacobian `J_r(φ)` | 闭式 |
| 重新正交化 | `q.normalize()` | 一次 sqrt |

Ceres / GTSAM / g2o 都围绕这些操作构建 manifold-aware solver。`J_r(φ)` 是手推时最容易错的一项 —— 每篇 SLAM 论文都在 appendix 重列它，因为大家都会有一次抄错。`Sim(3)` 额外加一个 uniform scale `s`（7-DoF）—— ORB-SLAM3 闭环用它来修正 monocular scale drift。

---

## 5 · 这篇 primer 怎么算合格

质量测试：你能不能在不再 google exp / log 的前提下逐页读 ORB-SLAM3 源码？

- 把 `φ = (0.01, 0, 0)` 喂进 `Sophus::SO3d::exp(...)`，验证输出与 §3 的 Rodrigues 一致。
- 打开 ORB-SLAM3 `Optimizer.cc` → 找 `Sophus::SE3f::exp(xi)`，确认是右扰动。

---

## 6 · 能力与失败模式

| 能 | 不能 |
|---|---|
| 不漂离流形地优化旋转 / 位姿 | 全局优化 —— 只保证局部收敛 |
| 正确复合 IMU 微旋转 | 让下游出现 Euler 时也躲掉 gimbal lock |
| 把不确定性表达为切空间上的 3×3 / 6×6 高斯 | 表达多峰分布 |

### 6.1 Hidden Assumptions

- **切空间近似是局部的** —— δφ ≲ 0.5 rad；更大跳跃要重新线性化。
- **右 vs 左扰动约定必须一致** —— 整个 codebase 混用会把 Jacobian 取反。
- **Quaternion 符号歧义** —— `q` 和 `-q` 是同一个 R；对 slerp / 求平均敏感。
- **浮点漂移** —— 反复 `R = R · exp(δ)` 会漂出 SO(3)；定期重新正交化。

破掉这些假设产出的是*静默*的错协方差 —— EKF / BA 会无声地发散，不会爆出 loud error。

---

## 7 · 比较与面试 Tip

| 表示 | 优 | 缺 | 谁用 |
|---|---|---|---|
| Euler | 3 个数、直觉 | gimbal lock | 业余 IMU、动画 |
| Rotation matrix | 直接复合 | 9 个数、会漂 | 教科书数学 |
| 轴角 | 3 个数、θ<π 无 gimbal | π 处奇异 | so(3) 切空间 |
| Unit quaternion | 平滑、4 个数 | 符号 / Hamilton vs JPL | SLAM / VIO / 航空 |
| Lie group | manifold 正确的优化 | 学习曲线 | 每个现代 SLAM solver |

> **🎤 Interview Tip.** "为什么不把旋转存成 Euler？" —— 强答：「gimbal lock，对；但更深一层是 —— 旋转是弯曲流形，优化需要一个平直切空间；所以我们把 R 存在 SO(3) 上，更新走 so(3) 的 exp-log。」弱答只停在"gimbal lock"；强答能点出 manifold。

---

## Boundary

这篇 primer 只覆盖数学基元。如需：

- **ORB-SLAM3 里的系统级 SE(3)** → `foundations/classical-slam/orb_slam3_dissection.md`
- **MSCKF 状态里的 SE(3)** → `./bayesian_filtering_ekf_msckf.md`
- **IMU preintegration 里的 SE(3)** → `./imu_preintegration_math.md`
- **闭环用的 Sim(3)** → `./pose_graph_optimization.md`

---

## References

- Sola, J. *A micro Lie theory for state estimation in robotics*, arXiv [1812.01537](https://arxiv.org/abs/1812.01537), 2018.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003. Ch. on 3D rotation parametrisation.
- Strasdat, H. *Scale Drift-Aware Large Scale Monocular SLAM*, RSS 2010. Sim(3) original.
- ORB-SLAM3 (Sophus usage): https://github.com/UZ-SLAMLab/ORB_SLAM3

[← Back to Spatial Math](./overview.md)
