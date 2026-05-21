# Quaternions and Rotation Representations (四元数与旋转表示)

> **发布时间**: 2026-05-21
> **核心定位**: 选哪种旋转表示、什么时候选、以及 Hamilton vs JPL 约定战争如何让真实团队真实地损失几个星期。

**Status:** v1 —— primer。约定冲突相关数字来自公开 SLAM 论坛报告，`UNVERIFIED`。
**TL;DR:** 存储用 unit quaternion，变换用 rotation matrix，切空间更新用轴角。实时栈里**永远别用 Euler**。**每个 repo 钉死一种 quaternion 约定（Hamilton 或 JPL）** —— 静默 mismatch 会沉掉整个集成。

**X-Ray.** 3D 旋转有 3 个自由度，但每种参数化都得付代价 —— Euler 会撞 gimbal lock，matrix 是过参数化，轴角在 π 处奇异，quaternion 有符号歧义。实战中 unit quaternion 胜出：复合便宜，slerp 平滑，不需重新正交化就保持 manifold 正确。坑：图形界（Hamilton）和航空界（JPL）写的数学乘法顺序是反的。（中文直觉：旋转有四种穿法，四元数最优 —— 但要确认是 Hamilton 还是 JPL。）

## 📍 研究全景时间线

```
1843        2003           2005                  2018         2026
Hamilton ► HZ textbook ► Trawny-Roumeliotis ► JPL tech    ► YOU ARE HERE
quaternions Hamilton SLAM "Indirect KF / 3D Attitude" (JPL) convention war
                                                            still bites stacks
```

Trawny-Roumeliotis 2005 就是 OpenVINS / MSCKF 用 JPL、而 ROS / ORB-SLAM3 用 Hamilton 的原因。**两边都对；两边互不兼容。**

---

## 1 · 四种表示（外加一种反模式）

| 表示 | 存储 | 复合 | 奇点 | 插值 | 实时 SLAM 用法 |
|---|---|---|---|---|---|
| **Euler (roll/pitch/yaw)** | 3 floats | 3 次三角运算、顺序敏感 | gimbal lock | 丑 | ❌ SLAM 里的反模式 |
| **Rotation matrix R** | 9 floats | 1 次 matmul（27 乘 + 18 加） | 无 | 逐行 nlerp 再重新正交化 | 很少存储，用于变换点 |
| **轴角 / rotvec** | 3 floats | 需 exp-log 往返 | θ = π 处 | 小 θ 时沿轴线性 OK | 仅用于切空间更新 |
| **Unit quaternion** | 4 floats（1 个约束） | 16 乘 + 12 加 | 符号歧义 | slerp（干净） | ★ 规范存储 |

### 1.1 为什么 SLAM 栈里禁用 Euler

1. **顺序歧义** —— ZYX vs ZXY vs ... 12 种约定，很少明文写。
2. **pitch = ±90° 处 gimbal lock** —— 倒飞的 drone 会撞上；转换 Jacobian 奇异；EKF 爆掉。
3. **没有干净的复合** —— Euler 三元组的复合反正还得过 rotation matrix。

Euler 只配做*显示用*。永远不是规范状态。

### 1.2 ⚡ Eureka Moment

> **Unit quaternion 是唯一一种同时满足 (a) 无奇点、(b) identity 附近的双覆盖光滑、(c) 复合便宜、(d) 可插值的表示。其他每种至少要丢掉一项。**

这就是为什么 2015 年以来所有量产的航空 / AR / AD 姿态估计器都把状态存成 quaternion，哪怕论文为了可读用 rotation matrix 写方程。

---

## 2 · 数学核心：quaternion 代数

### 📌 Napkin Formula

```
q = (w, x, y, z) = w + xi + yj + zk,  |q| = 1
ij = k, jk = i, ki = j        (Hamilton)
ji = k, kj = i, ik = j        (JPL — flipped sign)
```

这个符号翻转不是"不同的数学" —— 是"向量从哪一侧被旋转"。**长得一模一样的方程会产出转置过的 rotation。**

| 项 | Hamilton | JPL |
|---|---|---|
| `ij =` | `+k` | `-k` |
| `R(q) v` | active rotation | passive (frame change) |
| `q1 ⊗ q2` | 左到右复合 | 右到左 |
| 使用方 | Eigen、ROS tf、GTSAM、ORB-SLAM3、HZ | OpenVINS、MSCKF、航空 |
| 第一个 bug | 旋转反向 | 协方差 Jacobian 转置 |

Hamilton 库吃 JPL 数据，编译通过、直飞时缓慢漂移、一转弯就爆。团队在这里损失过几个星期 `UNVERIFIED`。

---

## 3 · 玩具例子：Hamilton-vs-JPL 在真实代码里的碰撞

团队把 OpenVINS IMU 前端（JPL）和 ORB-SLAM3 后端（Hamilton）集成。Quaternion 从前端流到后端。

两边都把 `Quaternion(w, x, y, z)` 定义成同样的 layout。两边都暴露 `toRotationMatrix()`。单元测试 identity 通过。**bug 在运行时 yaw 转动下出现。**

```
front (JPL):     q_FE = (0.7071, 0, 0, 0.7071)   // 90° about z
                  → "rotates body-z to world-x"

back (Hamilton): same q bits → R = ...
                  → "rotates world-z to body-x"
```

同一个 quaternion，相反的解释。每个位姿被*转置*。直飞时位置看起来对（identity 主导），转弯时偏 ~2θ。

**修法:** 在集成边界上，若冲突是 active vs passive，写 `q_out = q_in.conjugate()`。在边界旁明文标注约定。

---

## 4 · 工程视角：slerp、归一化、双覆盖

```
slerp(q0, q1, t) = sin((1-t)θ)/sin(θ)·q0 + sin(tθ)/sin(θ)·q1
where cos θ = q0 · q1   (4D dot)
```

如果 `q0·q1 < 0`，先 `q1 = -q1` 再 slerp —— 不然插值走的是长路。这就是实践中的**双覆盖歧义**。

**归一化节奏.** Double 精度每次操作漂 ~1e-15；200 Hz 跑 10 分钟约 1e-9，可忽略。Float32 每次操作漂 ~1e-7，每 ~1000 次操作要 renorm 一下。习惯做法：在 predict step 里 renorm，不是每次乘法都 renorm。

| 表示 | Bytes (dbl) | 复合 | 变换向量 |
|---|---|---|---|
| Quaternion | 32 | 16 乘 + 12 加 | ~30 flops `q v q*` |
| Rotation matrix | 72 | 27 乘 + 18 加 | 9 乘 + 6 加 |

10k 关键帧：quaternion 省下 ~400 KB 且 manifold 正确。需要变换点时按需转成 R。

---

## 5 · 何时用哪种表示

| 需求 | 选什么 |
|---|---|
| 存关键帧位姿 | quaternion + translation（7 doubles） |
| 变换点云 | rotation matrix (matmul) |
| 切空间更新 | 轴角 (so(3)) |
| 人类日志显示 | Euler（deg）—— Euler 唯一能上场的地方 |
| N 个旋转求平均 | `Σ q_i q_iᵀ` 的特征分解（Markley 2007） |
| 位姿插值 | slerp |

---

## 6 · 失败模式 & Hidden Assumptions

| 失败 | 原因 |
|---|---|
| 在 pitch 89° 翻 drone | 栈里有 Euler，gimbal lock |
| 旋转方向被转置 | Hamilton-vs-JPL mismatch |
| Slerp 走长路 | 忘了 `q0·q1 < 0` 时翻号 |
| 跑 1M 次操作后漂出 SO(3) | 漏 renorm，float32 |
| Quat 平均出垃圾 | 朴素分量平均，需特征分解 |

### 6.1 Hidden Assumptions

- **约定钉死** —— Hamilton 或 JPL，写在文档里；不在边界上静默混用。
- **存储是单位长** —— 累积后要 renorm。
- **符号规范化** —— 比较 / slerp 前若 `w < 0` 就 `q ← -q`。
- **坐标系写明** —— body vs world，FRD（航空）vs FLU（ROS）。
- **active vs passive** 与下游 rotation matrix 约定（Eigen / Sophus）一致。

任何 mismatch 都会产出能通过 identity 单元测试的*静默*垃圾。

---

## 7 · Interview Tip

> **🎤 Interview Tip.** "为什么用 quaternion 而不是 rotation matrix？" —— 强答抓三点：(1) 无奇点 4-vec vs 9-entry 冗余矩阵，(2) 复合下 manifold 正确、无需重新正交化，(3) 干净的 slerp 插值。加一句："我们在 repo 边界钉死 Hamilton vs JPL，因为两者会静默不兼容。" 最后这句出来面试官就知道你做过 production。

---

## Boundary

这篇 primer 只覆盖*参数化选择*。如需：

- **so(3) exp/log 切空间更新** → `./se3_so3_lie_groups_primer.md`
- **Quaternion EKF 状态传播** → `./bayesian_filtering_ekf_msckf.md`
- **IMU preintegration quaternion 累积** → `./imu_preintegration_math.md`
- **OpenVINS JPL 实现** → `embodiments/aerial/vio/openvins_dissection.md`

---

## References

- Hamilton, *Elements of Quaternions*, 1866.
- Trawny & Roumeliotis, *Indirect KF for 3D Attitude Estimation*, UMN Tech Report 2005-002.
- Sola, *Quaternion kinematics for the error-state KF*, arXiv [1711.02508](https://arxiv.org/abs/1711.02508), 2017.
- Markley et al., *Averaging Quaternions*, JGCD 30(4), 2007.
- Hartley & Zisserman, *Multiple View Geometry*, 2nd ed., 2003 (Hamilton convention).
- OpenVINS docs (JPL): https://docs.openvins.com/

[← Back to Spatial Math](./README.md)
