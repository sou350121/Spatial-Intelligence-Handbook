# PnP DLT + RANSAC 失败分析 Primer (PnP via DLT + RANSAC Failure Analysis Primer)

> 📚 **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲) L6 + Project 2 Phase 1 PnP
> 📜 **License**: 原始 slide 与代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本 primer 为改写 + 补充教材，依 BSD 3-Clause 保留版权声明
> 📄 **公开参考**: Hartley & Zisserman *Multiple View Geometry in Computer Vision* (2nd ed., 2003); Lepetit, Moreno-Noguer, Fua *EPnP* (IJCV 2009, [arXiv:0807.5103 替代查 DOI 10.1007/s11263-008-0152-6]); Fischler & Bolles *RANSAC* (CACM 1981, DOI 10.1145/358669.358692)

**Status:** v1 · ⚙️ 本文由 Moltbot 自动生成 | 2026-05-22
**TL;DR:** PnP（Perspective-n-Point）= 已知 3D 点 + 内参 → 解相机 6-DoF 位姿，是 SLAM tracking / VIO 重定位 / AR 标记跟踪共用的腰部模块；DLT 给一个**线性闭式初值**，Gauss-Newton 把它推到精修解；RANSAC 处理外点，但当外点率 > 50% 时迭代次数会**指数爆炸**——这是为什么现代 pipeline 还要叠 PROSAC / MAGSAC / 几何 prior。

**X-Ray.** 跟踪线程在每一帧都要回答："相机现在在地图里哪儿？"——答案是把已知 3D 点投到当前图像，用对应关系反推 `[R|t]`。**DLT 把投影方程线性化、SVD 一发解出**初值；**Gauss-Newton 用重投影误差精修**；**RANSAC 套一层抗外点**。这是 ORB-SLAM / VINS / OpenCV `solvePnPRansac` 共同的基底。

## 📍 研究全景时间线

```
1981     1999            2003                2009        2013        2020+
Fischler ► H&Z MVG ────► Sturm planar ────► EPnP O(n) ► PROSAC ───► MAGSAC++
RANSAC   DLT 教科书化    degenerate fix     线性化       score-based  no-threshold
                                                                     YOU ARE HERE
```

EPnP / MAGSAC 是工程默认，但**面试 / debug / 课程 baseline / planar marker** 场景下 DLT + GN 仍是最短解释路径——理解它你才看懂 `cv::solvePnP(SOLVEPNP_DLT)` 在做什么、为什么 planar 要走 homography 分支。

---

## §1 · 问题定义 (Problem Statement)

**输入**：
- `n` 个 3D-2D 对应：世界坐标 `(X_i, Y_i, Z_i)` ↔ 图像像素 `(u_i, v_i)`，`i = 1..n`
- 相机内参 `K`（焦距 `fx, fy`、主点 `cx, cy`），已通过 Kalibr / Zhang's method 标定

**输出**：相机相对于世界的 6-DoF 位姿 `[R | t]`，`R ∈ SO(3)`、`t ∈ R^3`

**最小 n 与解的多重性**：

| 配置 | 最少点数 | 几何解数量 | 备注 |
|---|---|---|---|
| **P3P**（最小 case） | 3 | 4 解（最多） | 需第 4 点消歧 |
| **平面 PnP** (3D 点共面) | 4 | 2 解（双解性） | 用深度 / 法向消歧 |
| **DLT-PnP**（一般 6+） | 6 | 1 线性解 | 教科书 / 课程主选 |
| **EPnP**（一般 4+） | 4 | 1 解 + 优化 | OpenCV 默认 ≥ 4 点路径 |

> **课程惯例**：HKUST L6 + Project 2 Phase 1 用 **n ≥ 4 平面 DLT (homography 路径) 或 n ≥ 6 一般 DLT**——ARuco marker 提供 4 角点共面 → 走 homography 分支。

---

## §2 · DLT 推导：从投影方程到 `A·x = 0`

**投影方程**（齐次坐标 + 尺度因子 `s`）：

```
s · [u; v; 1] = K · [R | t] · [X; Y; Z; 1]
```

记 `P = K · [R | t]` 是 `3×4` 投影矩阵，`P` 有 12 个未知元（其实 11 个 DoF，因尺度任意）。设 `P` 行向量 `p1^T, p2^T, p3^T`：

```
u_i = (p1^T · X̃_i) / (p3^T · X̃_i)
v_i = (p2^T · X̃_i) / (p3^T · X̃_i)
  其中 X̃_i = [X_i, Y_i, Z_i, 1]^T
```

**交叉相乘消分母**（关键步骤），每个对应给两行：

```
[ X̃_i^T,   0^T, -u_i·X̃_i^T ]   [p1]
[  0^T,  X̃_i^T, -v_i·X̃_i^T ] · [p2] = 0
                                  [p3]
```

堆 `n` 个对应 → `A ∈ R^{2n × 12}`，求 `A·x = 0` 的非平凡解（因 `x = 0` 平凡）。

**SVD 取最小奇异向量**：`A = U Σ V^T`，`x* = V` 的最后一列（对应 `σ_min`）。这是 **最小二乘意义下** `||A·x||` 的非平凡极小者，受 `||x|| = 1` 约束。

**直觉**：观测越多噪声越小、`σ_min` 越接近 0；如果 `σ_min` 不显著小于次小奇异值 → 几何配置退化（见 §4）。

---

## §3 · SO(3) 投影：DLT 出来的 R 不是真正旋转

`P` 解出后拆 `K^{-1} · P = [r1 r2 r3 t]`。问题：`[r1 r2 r3]` **不严格正交**——SVD 闭式解只受 `||x|| = 1` 约束，没有显式 `R^T R = I`。

**修复步骤**（HKUST L6 slide 28 公式）：

1. 取出粗 `R_dlt = [r̃1, r̃2, r̃3]`（或平面 case 用 `[h̃1, h̃2, h̃1 × h̃2]`）
2. SVD：`U Σ V^T = SVD(R_dlt)`
3. 投影到 SO(3)：`R_ortho = U · V^T`
4. **行列式翻转检查**：若 `det(R_ortho) < 0`，反射不是旋转 → 令 `R = U · diag(1, 1, -1) · V^T`

**尺度恢复**（平面 PnP）：`t = h̃3 / ||h̃1||`，因 `r1, r2` 是单位向量，但 `h̃1, h̃2` 经 `K^{-1}` 后只是**比例**单位。

---

## §4 · Planar PnP 退化：为什么 4 点共面要走 homography

**退化诊断**：当所有 3D 点共面（`Z_i = 0`），一般 DLT 矩阵 `A` 损失秩——`P` 的第 3 列 `r3` 永远乘 0，根本进不了方程；`A` rank ≤ 8，解流形维度大于 1，SVD 得不到唯一答案。

**解决**：改解 `3×3` homography `H = K · [r1 r2 t]`（直接舍 `r3`），每对应 2 行，4 点 → `8×9` 线性系统正好满秩。

**双解性**（slide 28-29）：从 `K^{-1} H = [h̃1 h̃2 h̃3]` 恢复 `r3 = ±(h̃1 × h̃2)`——两个符号都使 `R ∈ SO(3)`。消歧靠：

- **深度判定**：`t_z > 0`（点在相机前方）
- **第 5 点投影**：用未参与解 H 的额外对应做重投影误差，取小的
- **物理 prior**：drone 不会瞬间翻转到平面背面

> 工程坑：ARuco / AprilTag 4 角共面 → marker 离相机太远 / 视角太斜时，**两解的重投影 RMSE 接近**，pose flicker（180° 抖动）。VINS-Mono 的 marker 重定位曾踩过——VIO 给的姿态先验是消歧救星。

---

## §5 · Gauss-Newton 非线性精修

DLT 是 **algebraic error**（不是像素误差）的最小二乘解。真实想最小化的是 **reprojection error**：

```
min_{θ, t}  Σ_i || [u_i; v_i] − π( K · (R(θ) · X_i + t) ) ||^2
  其中 π([x;y;z]) = [x/z; y/z] 是除深度
```

**G-N 迭代**（L6 slide 35-36）：①初值 `θ_0, t_0` ← DLT；②线性化 `γ_i ≈ γ_i(0) + J_i · [δθ; δt]`，`J_i ∈ R^{2×6}`；③正规方程 `(Σ J_i^T J_i) · δ = − Σ J_i^T γ_i`；④更新 + 回 ②，3-5 轮收敛。

**Jacobian 直觉**：`∂γ/∂t` 直接导，`∂γ/∂θ` 对 Euler / so(3) Lie-algebra / quaternion 选一种参数化导——Lie-algebra 最干净（见 [`../spatial-math/se3_so3_lie_groups_primer.md`](../spatial-math/se3_so3_lie_groups_primer.md)）。

**为什么必须 G-N 精修**：DLT 的 algebraic error 在像素空间 **非各向同性**——离主点远的角点权重莫名增大。G-N 各向同性，工业 RMSE 通常降 3-10×（`UNVERIFIED`，依配置）。

---

## §6 · RANSAC 标准 4 步与 PnP sample size

```
loop k=1..N: ①sample s 对应 ②fit hypothesis [R_k,t_k]
             ③score: 所有 n 对应 reproj < τ 计 inlier
             ④update: inlier 数最多则记录
末尾: 用全部 inliers 做 G-N 精修
```

**为什么 PnP 采样 s=4 而非 3？** P3P 解 quartic → 最多 **4 几何解**，第 4 点 disambiguate；再多增加抽中外点的概率。

**阈值 τ 经验**：marker 子像素 `2-3 px`，ORB matching `8-10 px`（`UNVERIFIED`，依 dataset）。

---

## §7 · RANSAC 失败概率公式与外点率爆炸 (HKUST L6 黄金教材)

**记号**：
- `ε` = 外点率（outlier ratio，例：0.3 表 30% 外点）
- `k` = 每轮 sample size（PnP=4、line=2、3D-3D=3）
- `N` = 总迭代轮数
- `p_fail` = 全部 N 轮**没有一轮抽到全 inlier sample** 的概率

**单轮抽到全 inlier**：`(1 − ε)^k`
**单轮失败**：`1 − (1 − ε)^k`
**N 轮全部失败**：

```
p_fail = ( 1 − (1 − ε)^k )^N
```

**给定目标置信度 `1 − p_fail = p_conf`（例 99%），反解 `N`**：

```
N = log(1 − p_conf) / log( 1 − (1 − ε)^k )
```

**HKUST L6 数据表（slide 49-51）**：ε=0.3, k=2 (2D line) → N=10 时失败 0.12%；k=3 (3D-3D) → N=10 时 1.49%；k=20 (反面教材) → N=1000 时 **45%**。

**爆炸点**——固定 `p_conf = 0.99`、所需 N（`UNVERIFIED`，自算 `N = ⌈log(0.01) / log(1 − (1 − ε)^k)⌉`）：

| ε \ k | k=3 | k=4 (PnP) | k=8 | k=20 |
|---|---|---|---|---|
| 0.10 | 6 | 8 | 17 | 110 |
| 0.30 | 16 | 26 | 142 | ~4600 |
| 0.50 | 35 | 72 | 1177 | ~4.7M |
| **0.70** | **170** | **587** | **70k** | ~3e10 |

**结论**：k=4 PnP 在 ε ≤ 50% 还可控，ε=70% 跳到 ~600 次、ε=80% 超 5000 次——**feature matching 质量决定 SLAM 能不能跑**，不是 RANSAC 给力。

### PROSAC / MAGSAC 怎么救高 ε

- **PROSAC** (Chum & Matas 2005)：按 matching score 排序优先抽好对应——ε>50% 时迭代降 2-10×
- **MAGSAC++** (Barath 2020)：取消硬阈值 τ，对所有点做 marginalized weighting——不挑 τ
- **GC-RANSAC**：加 Graph-Cut LO，相邻 inlier 一起判

**直觉**：score-based sampling 把"均匀随机"换成"先验加权"，等效降 ε。

---

## §8 · 为什么 2026 年 ORB-SLAM3 / OpenVINS 还在用 RANSAC + PnP

| 替代方案 | 现状 | 没取代理由 |
|---|---|---|
| Learn-based PnP (PoseNet/DSAC) | 室内 demo 跑得过 | 跨场景泛化差、metric scale 无保障、数据贵 |
| Feed-forward 3D (VGGT/DUSt3R) | 跨 dataset 强 | 还没 200Hz、IMU 耦合缺位 |
| Direct method (DSO/LSD) | photometric 最优 | 光照 / 自动曝光敏感、跨集脆 |

**核心理由**：PnP + RANSAC 是 **interpretable + no-training + sub-ms latency** 组合。ORB-SLAM3 tracking 每帧 `~17ms` 里 PnP + 局部 BA 占大头但**可预测**；NN 替代都得过 latency / determinism 两关。

---

## §9 · 真机 production gotchas

1. **Distortion**：DLT 假设理想针孔，real lens 有 radial + tangential 畸变 → 解前必须 `cv::undistortPoints()`，否则代数误差吃掉物理意义、G-N 难收敛
2. **Focal length 偏差**：`fx` 错 1% → `t_z` 系统性偏 ~1%（深度最敏感）。Aerial 5m 高度可漂 5cm，叠 IMU 漂移会爆 trajectory
3. **Planar 没检测到走一般 DLT**：`A` rank 不足、`σ` 多个近零、`R` 像噪声。Defense：检测 `σ_{12}/σ_{11}` 比值过大就 fallback 到 homography
4. **Numerical conditioning**：3D 点尺度差 100× → `A` 病态。Defense：Hartley normalization（centroid 平移 + 缩放使 RMS ≈ √2）
5. **Marker pose flip**：planar 双解 + 斜视角 → 帧间 A/B 解切换 → 180° flicker。Defense：用上帧 pose 投影选近解
6. **n 大反而慢**：DLT SVD `O(n)`、RANSAC 每轮 `O(k^3)` fit + `O(n)` score。L6 slide 48 的"few points better"指**单 hypothesis fit 用最少**，scoring 用全部

---

## §10 · 练习题（可在自己脑里走完）

### Q1：4 共面角点 → H → R/t 双解
给定 marker 边长 0.2 m, fx=fy=500, cx=320, cy=240；4 角投到 (280,200)/(360,200)/(360,280)/(280,280)：堆 `A∈R^{8×9}` → SVD → `H` → `K^{-1}H = [h̃1 h̃2 h̃3]` → `t = h̃3/||h̃1||`, `r1, r2` 归一化, `r3 = ±r1×r2` 双解 → SVD 投 SO(3) → 选 `t_z > 0`。预期 `t ≈ (0,0,1.0)`, `R ≈ I`（自验 `UNVERIFIED`）。

### Q2：ε=25%, k=4, 99% confidence → N？
`N = log(0.01) / log(1 − 0.75^4) = −4.605 / −0.380 ≈ 13`。实战加 margin 用 17-20。

### Q3：ε=60% 时 N？PROSAC 怎么救？
`N = log(0.01) / log(1 − 0.4^4) ≈ 178`。PROSAC score 排序使等效 ε 降到 ~0.3 → N 降到 ~26（`UNVERIFIED`，依 score 质量）。

### Q4：Planar marker 跑一般 DLT 会怎样？
`A` rank ≤ 8，SVD 最后两个奇异值都接近 0，`V[:,-1]` 在二维零空间里乱选 → `R` 不正交、`t` 失尺度、G-N 不收敛。诊断信号：`σ_{11} / σ_{12}` 比值过小。

---

## Cross-references

**上游 / 数学前置**：
- [`../spatial-math/camera_projection_view_geometry.md`](../spatial-math/camera_projection_view_geometry.md) — 投影方程 / 内参 / 畸变
- [`../spatial-math/se3_so3_lie_groups_primer.md`](../spatial-math/se3_so3_lie_groups_primer.md) — Lie-algebra Jacobian
- [`../spatial-math/bundle_adjustment.md`](../spatial-math/bundle_adjustment.md) — G-N 推广到联合多帧多点

**下游 / 应用**：
- [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md) — Tracking 线程的 motion-only BA 本质是 G-N PnP
- [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md) — 绕开"先匹配再 PnP"的对偶范式
- [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md) — `solvePnPRansac` 工程默认路径

**范式对比**：
- [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md) — feed-forward 端到端跳过 PnP
- [`../../crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) — 跨范式比较

---

## 面试 Tip 一句话

> 被问"PnP 退化在哪里"——答 **planar configuration + 一般 DLT** 让 `A` 失秩，必须 fallback 到 homography 路径，并且 planar 有 **2 解** 要 disambiguate（深度 / 第 5 点 / 前一帧 prior）。这一答能把面试官从"知道公式"拉到"踩过坑"。

---

[← Back to Classical SLAM](./README.md) · [→ ORB-SLAM3 Dissection](./orb_slam3_dissection.md)
