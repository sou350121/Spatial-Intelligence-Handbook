# 深度学习里旋转表达怎么选 (Rotation Representations in Deep Learning Primer)

> **发布时间**: 2026-05-22
> **核心定位**: 既有 `quaternions_and_rotations.md` 和 `rotation_intuition_primer.md` 偏经典机器人 / SLAM 视角；本文补齐 **2026 年写 pose head 的 DL 视角**——quaternion 在 backprop 哪里不稳、6D continuous 为什么一统 NN regression、axis-angle / Lie algebra 在梯度回传哪里爆。

**Status:** v1 — primer 类型（不必凑齐 dissection 14 项；重直觉 + 决策）。
**TL;DR:** 任何 NN 直接 regress 旋转的任务（pose estimation / NeRF / 3DGS camera pose / VLA action head / VGGT-style feed-forward 3D）都该读这篇。结论：**network 输出选 6D continuous（Zhou 2019）；EKF / BA 等 estimator 内部 state 仍选 quaternion + manifold update；硬件控制层（PX4 / 机械臂底层）继续 quaternion + Euler**。三类需求对应三种表达，混用是常态不是矛盾。

**X-Ray.** SO(3) 是 3 维流形但没有 4 维以下连续 + 单射欧式嵌入（Zhou 2019 拓扑论证）。经典 robotics 里不重要——manifold retraction 即可；但 DL 里 network 输出就是 R^n 向量，**"流形 vs 欧式"gap 在 backprop 时直接变成 loss 不连续**。Euler / quaternion / axis-angle 都掉坑，6D continuous 是已知最低维解。

---

## 1 · 问题本质：SO(3) 是 3 维流形，但 NN 输出住在欧式空间

经典 robotics 视角里，"旋转有 3 个自由度，挑个 3、4、9 维表达"是细节问题。DL 视角下这是**根本问题**：

```
   NN 输出  y = f_θ(x) ∈ R^n           欧式空间, 欧式 loss, 欧式梯度
   目标     R ∈ SO(3) (3 维流形)        真正距离是 geodesic
   gap     "怎么把流形塞进 R^n"          不同表达 = 不同塞法 = 不同梯度结构
```

**拓扑关键事实**：SO(3) 同胚于 **RP³**（实射影空间），不存在 SO(3) → R^n 的连续 + 单射映射当 n ≤ 4——任何 n ≤ 4 的表达必然有**不连续点**或**多对一**（double cover / antipodal）。

SLAM 圈不致命：manifold optimization 用 retraction 跨过。但 NN 是 R^n → R^n 连续函数，**学不了不连续的 target**：不连续点附近 loss landscape 出现"悬崖"，梯度爆炸或方向矛盾。

---

## 2 · 六种常用旋转表达 + DL 适合度

| 表达 | 维度 | DL 训练 | 主要坑 | 典型场景 |
|---|---|---|---|---|
| Euler (φ,θ,ψ) | 3 | ❌ 很差 | gimbal lock + 角度 wrap (179° → -179°) | debug / setpoint |
| Axis-angle (θω) | 3 | 🟡 一般 | norm 在 0 / 2π 附近不连续 | so(3) 切空间 |
| Quaternion (w,x,y,z) | 4 | 🟡 一般 | double cover：q vs −q antipodal 边界混淆 | EKF / VIO / 飞控 state |
| Rotation matrix | 9 | 🟡 中等 | 正交约束、SVD 反传不稳 | BA / Forster preint |
| **6D continuous** | 6 | ✅ **最好** | 拓扑下界，连续 + 单射 + Gram-Schmidt 重建 | NN pose head / VLA / VGGT |
| Lie algebra so(3) | 3 | 🟡 在 retraction 框架下可用 | 直接 regress 等价 axis-angle | manifold optimizer 内部 |

> **维度速记**：3 维必不连续（拓扑禁止）；4 维（quaternion）连续但非单射（double cover）；**6 维是最低维连续 + 单射**；9 维冗余但同样可用。

### 2.1 Euler 角在 NN regression 几乎从不选

```
   yaw 序列  178 → 179 → 180 → -179 → -178
                              ↑ wrap! 数值跳 358°
   NN 学不了这个跳跃 → 不收敛; 用 atan2(sin,cos) 间接学 → 不如直接 6D
```

### 2.2 Quaternion 也不够：double cover

quaternion 连续（S³ 是连续流形），但**它是 SO(3) 的 double cover**：`q` 和 `−q` 表示同一个 R。supervised regression 里如果 label 没规范化，同样的输入 → 相反的 label，loss landscape 在 antipodal 边界出现"对峙"，NN 只能学到 ≈ 0 的平均。

工程 workaround：训练前把 label enforced 到 `w ≥ 0` 半球。**但 prediction 接近边界（w ≈ 0，即旋转 ≈ 180°）时仍然炸**。

### 2.3 9D 旋转矩阵也不够好

直接让 NN 输出 9 个数没约束，无法保证 `R R^T = I`；加 SVD 投影可训练但反传数值不稳，靠近退化矩阵时梯度爆；加 soft penalty `||R R^T − I||²` 训练慢且不严格。

---

## 3 · Zhou et al. 2019 的关键洞见：6D continuous representation

**论文**: Zhou, Barnes, Lu, Yang, Li. *On the Continuity of Rotation Representations in Neural Networks*. CVPR 2019. [arXiv 1812.07035](https://arxiv.org/abs/1812.07035)

### 3.1 拓扑论证（Napkin Formula）

> **定理（Zhou 2019, 非正式版）**：任何 SO(3) → R^n 连续 + 单射表达必有 n ≥ 5；n = 5 没自然结构，实用最低维 **n = 6**。
> 证明骨架：SO(3) 同胚 RP³，不能被 R^4 以下欧式空间嵌入（algebraic topology 标准结论）。

直觉：克莱因瓶不能塞到 3D 而不自相交；同理 RP³ 不能塞到 R^4 而保持连续 + 单射。**4 维不够，5 维数学上够但没自然几何，6 维工程最优**。

### 3.2 6D 表达怎么构造（Gram-Schmidt 反构）

network 输出 6 个数 `a = (a₁, a₂)`，每个 `aᵢ ∈ R³`：

```
   b₁ = a₁ / ||a₁||                       (单位化第一列)
   b₂ = (a₂ − (b₁·a₂) b₁) / ||·||         (减去在 b₁ 方向投影后单位化)
   b₃ = b₁ × b₂                            (叉乘, 第三列由前两列定)
   R  = [ b₁ | b₂ | b₃ ]   ∈ SO(3)
```

**连续**：Gram-Schmidt 对 a 处处可微（除 `a₁ = 0` / a₁∥a₂ 薄集，gradient 自动推离）。**单射**：R 的唯一最简 a 是其前两列。**Loss**：`||R_pred − R_gt||²_F`（Frobenius）足够；geodesic loss `arccos((trace(R_pred^T R_gt) − 1)/2)` 在 ±1 数值不稳，实践中不优于 Frobenius。

---

## 4 · 训练时的实际差异：为什么 6D 收敛快

Zhou 2019 在 ShapeNet 类别预测 + 3D pose regression 上做 ablation：同样网络架构，仅改输出表达（Euler / quaternion / axis-angle / 6D / 9D-SVD）。6D 在 mean angular error 上比 quaternion 低**约 2× ~ 5×** `UNVERIFIED`（具体以原论文 Table 1-3 为准，不同任务系数不同），训练初期 loss 下降明显更快 `UNVERIFIED`。

**直觉**：quaternion loss landscape 在 antipodal 边界形成"墙"（q ↔ −q 切换的高 loss 屏障），6D landscape 是平滑凸盆。NN 优化器最怕这种 ridge / cliff。

**2020 年后社区共识**：PoseNet 后续工作、HMR / SMPL pose regression、多数 NeRF pose-aware 系统默认 6D；Pi0 / OpenVLA 类 action head rotation 部分也常 6D（delta 旋转范围小则 quaternion / axis-angle 亦可）`UNVERIFIED`。

---

## 5 · SLAM / VIO 角度：为什么经典优化仍然用 quaternion

DL pose head 偏好 6D，但 **ORB-SLAM3 / VINS-Mono / OpenVINS / Forster IMU preintegration** 内部仍是 quaternion（或等价 SO(3) manifold）。**不是矛盾**，是两类任务不同需求：

| 维度 | NN pose head | SLAM / VIO estimator |
|---|---|---|
| 输出方式 | 一次性 regress 整个 R | 增量 R_{k+1} = R_k · ΔR |
| 优化框架 | SGD / Adam 欧式 backprop | Gauss-Newton / LM manifold retraction |
| 表达需求 | 连续 + 单射就够 | minimal 3D 切空间 + 高效复合 + propagation |
| 不连续点 | 必须避开 | retraction 跨过即可 |

quaternion 在 SLAM 优势：复合廉价（16 mul + 12 add）；error state 自然（δq ≈ [1, δθ/2] → 3D δθ，covariance 是 3×3）；propagation friendly（q̇ = ½ q ⊗ [0, ω] 闭式）；数值漂移单位化一行修复。**经典 estimator 不掉 NN 的坑**，因为它从不"直接 regress R"——manifold retraction step 让 q ↔ −q 边界自动等价。

---

## 6 · 何时用哪种（决策表）

| 任务类型 | 推荐表达 | 原因 |
|---|---|---|
| NN 输出 absolute pose（VGGT / DUSt3R / PoseNet 风格） | **6D** | 连续 + 单射 + 训练稳 |
| NN 输出 delta rotation（VLA action chunk, ≤ 90°） | 6D 或 axis-angle | 小角度下 axis-angle 安全 |
| NeRF / 3DGS pose refinement | 6D | 与 photometric loss 协同好 |
| Sequence transformer (VGGT 类) | 6D（多数）/ axis-angle | 同上 |
| EKF / MSCKF / VIO state | quaternion + δθ error state | Forster / Sola 公式 |
| Bundle adjustment internal | SO(3) manifold + so(3) tangent | ceres / gtsam / theseus 默认 |
| 控制层 setpoint (PX4 / arm) | quaternion + ZYX Euler | 硬件 API + 人可读 |
| Debug / log / 给人看 | Euler (deg) | 不进入梯度回路 |

**混着用是常态**：典型 VLA / VIO 系统里同一个旋转可能在 NN 部分 6D、在 estimator 部分 quaternion、在硬件 setpoint Euler——**关键是知道每段边界用什么 + 转换在哪里发生**。

VGGT (CVPR 2025) 的 camera pose head 输出 9 维（其中 6 维表 rotation）`UNVERIFIED`——延续 Zhou 2019 路线，详见 [vggt_cvpr2025_dissection.md](../feed-forward-3d/vggt_cvpr2025_dissection.md)。real-time control 层（PX4 内部 quaternion / mavros / ROS tf2 默认 quaternion）不靠 NN 直接出旋转，详见 [aerial dynamics_and_control_primer](../../embodiments/aerial/dynamics_and_control_primer.md)。

---

## 7 · 练习题 + 常见错误

### 7.1 玩具题：antipodal 怎么坏 supervised regression

数据集：x₁ → q* = (0.01, 0.99, 0, 0)（≈ 180° around X）；x₂ → q* = (−0.01, −0.99, 0, 0)（label 工程师没规范化 sign）。**用 MSE loss 训练 quaternion regression NN，会发生什么？**

x₁ x₂ 几何上对应几乎相同的旋转，但 label 欧式距离 ≈ 2。NN 看到"几乎一样输入 → 完全相反 label"，学到 ≈ 0 的平均值，**完全学不到 180° 这个旋转**。修复：enforce `w ≥ 0`；换 geodesic loss `1 − (q_pred · q_gt)²`；或换 6D。

### 7.2 常见错误清单

1. **用 6D 但 forget 正交化**：直接当 R 用 → 不正交，loss 错位
2. **quaternion 没规范化 sign**：§7.1 那个坑
3. **axis-angle 在大旋转任务**：|θ| ≈ π 时 norm 在 0/2π 边界跳，不收敛
4. **6D 用 geodesic loss 但 ±1 数值不稳**：arccos 导数爆，建议 Frobenius 或 ε clip
5. **混 Hamilton vs JPL convention**：(w,x,y,z) vs (x,y,z,w)，IMU 静默错，详见 [quaternions_and_rotations.md](./quaternions_and_rotations.md)
6. **NN 输出的 R 灌进 BA 不做 manifold update**：丢失收敛保证

---

## 8 · 与既有文档的互补关系

| 文档 | 视角 | 侧重 |
|---|---|---|
| [`rotation_intuition_primer.md`](./rotation_intuition_primer.md) | 直觉入门 | 4 种经典表达的几何含义 |
| [`quaternions_and_rotations.md`](./quaternions_and_rotations.md) | 经典 robotics | Hamilton vs JPL convention、SLAM 工程坑 |
| [`se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md) | 流形 / manifold | exp/log、tangent space、BA |
| **本文** | **DL 训练** | **6D 为什么赢、quaternion regression 坑、Zhou 2019** |

**阅读顺序**：没基础 → `rotation_intuition_primer` → 本文 → `se3_so3_lie_groups_primer`；有 SLAM 背景刚写 NN pose head → 直接本文；写 VIO / EKF → `quaternions_and_rotations` + `se3_so3_lie_groups_primer`；写 VLA action head → 本文 §6。

---

## 9 · 一张图收尾

```
   "我要写一个旋转相关的模块, 选什么表达?"
     ├─ NN 直接 regress R?              → 6D continuous (Zhou 2019)
     ├─ estimator (EKF/VIO/BA) state?  → quaternion + δθ error state
     ├─ 硬件控制 setpoint?              → quaternion (API) + ZYX Euler (人看)
     └─ 给人看 / debug?                 → Euler (deg)
   混着用是正常的, 关键是 conversion 在边界发生.
```

---

## Boundary

- 四元数 convention 细节 / Hamilton vs JPL → [`./quaternions_and_rotations.md`](./quaternions_and_rotations.md)
- SO(3) / SE(3) manifold + Lie algebra 正式定义 → [`./se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md)
- 4 种经典表达的几何直觉 → [`./rotation_intuition_primer.md`](./rotation_intuition_primer.md)
- VGGT pose head 实测 → [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)
- aerial 飞控控制层 → [`../../embodiments/aerial/dynamics_and_control_primer.md`](../../embodiments/aerial/dynamics_and_control_primer.md)

## References

- **Zhou et al. (2019)** *On the Continuity of Rotation Representations in Neural Networks*. CVPR 2019. [arXiv 1812.07035](https://arxiv.org/abs/1812.07035) — 6D 表达拓扑论证 + ablation，本文核心
- **Sola (2017)** *Quaternion kinematics for the error-state Kalman filter*. [arXiv 1711.02508](https://arxiv.org/abs/1711.02508) — quaternion + manifold，VIO / EKF 工程师视角必读
- **Forster, Carlone, Dellaert, Scaramuzza (2017)** *On-Manifold Preintegration for Real-Time VIO*. IEEE T-RO. [arXiv 1512.02363](https://arxiv.org/abs/1512.02363)
- **Sola, Deray, Atchuthan (2018)** *A micro Lie theory for state estimation in robotics*. [arXiv 1812.01537](https://arxiv.org/abs/1812.01537) — micro-Lie theory 现代版
- Wang et al. (CVPR 2025) *VGGT* — feed-forward 3D 的 pose head 设计实例 `UNVERIFIED`
- Levinson et al. (2020) *An Analysis of SVD for Deep Rotation Estimation*. NeurIPS. [arXiv 2006.14616](https://arxiv.org/abs/2006.14616) — Zhou 2019 延伸

---

[← Back to Spatial Math](./overview.md)
