# Camera Projection & View Geometry (相机投影与多视几何)

> **发布时间**: 2026-05-22
> **核心定位**: 把 3D 世界投影到相机像素的核心数学 —— **每个 SLAM / SfM / FoundationPose / VGGT 都必须假设你会的前置数学**。

**Status:** v1 — primer。
**TL;DR:** 相机投影 = 把 3D 点 X 经过 `[R|t]` 外参和 `K` 内参变成像素 `(u, v)`。**反过来 + depth 就能 back-project 拿回 3D**。**多视图几何** = 用 2 张以上图像在不知 depth 的情况下恢复几何（epipolar geometry / essential matrix / triangulation）。**所有 spatial AI 论文默认你会这套** —— 学不通这里，BA 看不懂，VGGT 也看不懂。

**X-Ray.** 你有一个 3D 点 `X = (X, Y, Z)`，你的手机相机指向某处。这个 3D 点会出现在屏幕上哪个像素？答案是 **3D → 2D 投影矩阵 P = K · [R|t]**。反过来：给定屏幕上一个像素 + 深度，能不能算回 3D 位置？能 —— **back-projection**。再难一层：给两张照片（不知道是哪里拍的），能不能恢复相机相对位姿和 3D 结构？能 —— **多视图几何**。本文从最简单的针孔模型一直到 8-point / 5-point 算法，是所有 spatial AI 的"看图与几何"必备数学。

## 📍 研究全景时间线

```
   1480s         1839        1913        1995-2003           2010+              2024+
   ──────────    ──────────  ──────────  ──────────────      ──────────         ──────────
   达·芬奇       Niépce      Hartley     Zhang's method      ORB-SLAM3          VGGT 谱系
   提出 pinhole  摄影术发明  fundamental Hartley-Zisserman   PnP / RANSAC       学习式
                            matrix      "MVG" 教科书         产业级 calibration projection
                            (相对几何)                                          (无 explicit K)
   
   └─ 透视几何 ────► classical SfM ────► production SLAM ────► learned 取代 ────►
```

Hartley & Zisserman *Multiple View Geometry* 2003 是规范教科书。**今天 VGGT 一类用 transformer 取代显式 K + epipolar geometry，但底层数学一致**。

---

## 1 · 针孔相机模型

### 1.1 3D → 2D 投影

```
   世界坐标系 ────────────────► 相机坐标系 ───────────────► 像素坐标系
        (R|t 外参)                (K 内参)                 
                                                          
   X = (X, Y, Z)            X_c = R·X + t              p = (u, v)
   3D 世界点                3D 相机坐标系点              2D 像素
   
   完整公式 (齐次):
   
              [ u ]          [ X ]
        λ ·   [ v ]  =  K ·  [ Y ]                       (Z 是 depth)
              [ 1 ]      [R|t]·[ Z ]
                              [ 1 ]
   
        where K = [ fx   0   cx ]                        fx, fy: 焦距 (像素)
                  [  0   fy  cy ]                        cx, cy: principal point
                  [  0    0   1 ]                        
                  
   2D 像素 (u, v) =  ( fx · X_c/Z_c + cx ,  fy · Y_c/Z_c + cy )
                       ↑                    ↑
                  除 Z_c 是"透视效应"（远小近大）
```

**直观理解**: 3D 世界点 → 用相机姿态 (R, t) 旋转到 *相机坐标系* → 经过焦距 fx/fy 投影到像平面 → 加上 principal point offset → 得到像素坐标。

### 1.2 内参 K (Intrinsics)

| 参数 | 单位 | 含义 | 典型值（手机相机）|
|---|---|---|---|
| `fx`, `fy` | 像素 | 焦距 (in pixels) | 1000-2000 |
| `cx`, `cy` | 像素 | principal point (光轴中心) | 接近 image center |
| `skew` | 像素 | sensor 行列倾斜 | 0（现代 CMOS 几乎都是 0）|

**fx vs 物理焦距**: `fx = f_物理(mm) / sensor pixel size(mm/px)`。手机 26mm 等效焦距 + 1.4 μm 像素 → `fx ≈ 1858` 像素。

### 1.3 外参 [R|t] (Extrinsics)

```
   相机姿态：R ∈ SO(3) (3×3 旋转) + t ∈ R³ (3 平移)
   
   X_camera_frame = R · X_world + t
   
   反过来 (camera→world):
   X_world = R^T · (X_camera - t) = R^T · X_camera - R^T · t
```

⚠️ **convention 战争**: 有些库定义 `[R|t]` 是 world→camera，有些是 camera→world。**永远在 API 边界确认 convention**。这是 SLAM 集成 #2 silent bug（#1 是 Hamilton vs JPL，见 [quaternions_and_rotations.md](./quaternions_and_rotations.md)）。

---

## 2 · 失真模型（真实镜头不是 pinhole）

### 2.1 Brown-Conrady 失真模型（最常用）

```
   径向失真 (radial, 主导):
     x_d = x · (1 + k1·r² + k2·r⁴ + k3·r⁶)
     y_d = y · (1 + k1·r² + k2·r⁴ + k3·r⁶)
     where r² = x² + y²
   
   切向失真 (tangential, 次要):
     x_d += 2·p1·x·y + p2·(r² + 2x²)
     y_d += p1·(r² + 2y²) + 2·p2·x·y
   
   5 参数: (k1, k2, k3, p1, p2)
   适用: 一般 fov < 90° 的镜头 (手机 / drone / AGV)
```

### 2.2 Kannala-Brandt（鱼眼 / 广角）

```
   FOV > 100° 的 fisheye / 广角镜头, Brown-Conrady 不够:
   
   θ_d = θ · (1 + k1·θ² + k2·θ⁴ + k3·θ⁶ + k4·θ⁸)
   where θ = atan(r)
   
   4 参数: (k1, k2, k3, k4)
   适用: drone 鱼眼 / 360 相机 / RealSense T265 (170° FOV)
```

### 2.3 物理来源（看一眼）

| 失真类型 | 物理原因 |
|---|---|
| 径向 | 透镜不均匀厚度 → 边缘光线弯折更多 |
| 切向 | 镜头安装不与 sensor 平行（assembly tolerance）|
| chromatic aberration | 不同波长折射不同（这一般 sensor 处理掉，不在 K 里）|

⚠️ **drone vibration 让 calibration drift**：~0.024 m/m flown，>30°C 漂移 +12%（per [foundationstereo dissection](../depth-foundation/foundationstereo_dissection.md)）。**Production calibration 在 lab 做一次后还要在线 refine** — 见 [imu_preintegration_math.md §6.4](./imu_preintegration_math.md#64-imu-camera-extrinsics-在线-estimate)。

---

## 3 · Back-Projection（2D + depth → 3D）

### 📌 Napkin Formula

```
   给定: 像素 (u, v), 深度 Z, 内参 K
   求: 相机坐标系下的 3D 点
   
   X_c = (u - cx) · Z / fx
   Y_c = (v - cy) · Z / fy
   Z_c = Z
   
   = K⁻¹ · (u, v, 1)ᵀ · Z
```

**为什么这很重要**:
- Depth Anything / Metric3D / FoundationStereo 给的是 per-pixel **Z**
- Back-projection 是 depth → 3D point cloud 的桥
- 整个 manipulation grasp pipeline 第一步：相机看到 → depth model → back-project → 3D 点 → 抓

⚠️ **米制 vs 相对**:
- Depth Anything v2 给 *相对* Z (un-metric) → back-project 拿到的 3D 是 *相对* 尺度
- Metric3D / Stereo / RGBD 给 *米制* Z → back-project 拿到 *真米制* 3D
- 这是 `crossing/slam-vio-migration/vggt_vs_drone_vio.md` 强调"VGGT un-metric 是 aerial 杀手"的根本原因

---

## 4 · 多视图几何（Multi-View Geometry）

**核心问题**：两张照片 + 未知 depth → 能否恢复相对姿态？答案：能（除了 scale）。

### 4.1 Epipolar Geometry（对极几何）

```
              ●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●
             /                                          \
           📷 camera 1                               📷 camera 2
            \                                           /
             \                                         /
              \─── 3D 点 X 同时被两台相机看到 ───────/
                       \                          /
                        ●  X_world
                       (未知)
   
   两相机间的 "essential matrix" E 编码:
     • 相对旋转 R
     • 相对平移方向 t̂ (单位向量, 尺度未知!)
   
   对应像素关系: p_2 = E · K⁻¹ · p_1   (epipolar constraint)
```

### 4.2 Essential Matrix E

```
   E = [t]× · R                ← [t]× 是 t 的反对称矩阵
   
   E ∈ R^(3×3), rank 2
   5 个自由度: 3 (R) + 2 (t 方向, 不含 scale)
   
   → 至少 5 个对应点对就能解出 E (5-point algorithm, Nistér 2004)
```

### 4.3 Fundamental Matrix F (适用无 K 的情况)

```
   F = K_2⁻ᵀ · E · K_1⁻¹
   
   F ∈ R^(3×3), rank 2, 7 自由度
   → 至少 8 个对应点对解 F (8-point algorithm, Hartley 1997)
```

**用 E 还是 F 取决于**：有没有内参 K。production SLAM (ORB-SLAM3 / VINS) 永远 calibrated → 用 E。无 calibrated 的 SfM 用 F。

### 4.4 5-point algorithm vs 8-point

| 算法 | 最少对应点 | 优势 | 劣势 |
|---|---|---|---|
| **5-point** (Nistér 2004) | 5 | minimum solution, 最少 RANSAC inlier | 解多项式 10 阶, 数值精度差 |
| **7-point** | 7 | F 的 minimum | 解 3 阶 polynomial |
| **8-point** (Hartley 1997) | 8 | 线性最小二乘 fast | 需归一化 (Hartley pre-normalize) |
| Direct from BA | N+ | 全局最优 | 慢, 需 init |

**ORB-SLAM3 init**: 5-point + RANSAC → 选 inlier 多的 hypothesis → 三角化点 → init 局部 map。

---

## 5 · 三角化（Triangulation）—— 从 2 个像素 + 2 个相机位姿求 3D

### 📌 DLT (Direct Linear Transform)

```
   给定: 像素 p_1 (in cam 1) + p_2 (in cam 2), 相机位姿 [R_1|t_1] + [R_2|t_2]
   求: 3D 点 X (世界系)
   
   每个 view 给 2 个约束:
     p_1 × (P_1 · X) = 0  ← cross product 化齐次方程
     p_2 × (P_2 · X) = 0
   
   堆出 4×4 线性系统 A · X = 0 → SVD 求最小特征向量
```

### 5.1 Worked Example: 玩具 2-view 三角化

两相机相距 10cm，看着同一个 1m 远的物体：

```
   cam_1 at (0, 0, 0), looking +Z
   cam_2 at (0.1, 0, 0), looking +Z
   3D 点 X = (0.05, 0, 1.0)   (1m 远, 横向居中)
   
   cam_1 看到 (像素): u_1 = fx · 0.05/1.0 + cx = 50 + 320 = 370
   cam_2 看到 (像素): u_2 = fx · (-0.05)/1.0 + cx = -50 + 320 = 270
   
   disparity = u_1 - u_2 = 100 像素 ← 给定 baseline + focal + disparity → 算 Z = baseline·fx/disparity = 0.1 · 1000 / 100 = 1.0 m ✓
```

**stereo depth 就是这套数学的实时版本** — 见 [foundationstereo dissection](../depth-foundation/foundationstereo_dissection.md) 的 `Z = f·B/d` 公式。

### 5.2 失败模式

| 现象 | 原因 |
|---|---|
| triangulation 无效 (在相机后面) | RANSAC 没找好 inlier, baseline 短 |
| depth 数字大 / negative | 极近距离 baseline 不够大 |
| 三角化 unstable (噪声敏感) | 几何 degenerate (baseline 太短 / 物体太远) |

---

## 6 · PnP (Perspective-n-Point)

**核心问题**：N 个 3D-2D 对应（3D 点已知 in world frame + 2D 像素），求相机姿态 [R|t]。

### 6.1 P3P (3 点)

```
   3 个 3D-2D 对应 → 多项式 → 4 个 hypothesis
   再用第 4 点验证选最优
   
   → ORB-SLAM3 / FoundationPose 都用 P3P 做初始姿态
```

### 6.2 EPnP (Efficient PnP) — N >= 4

```
   把 3D 点表示成 4 个 control point 的 barycentric coord
   → 线性求解 → O(N) 而不是 O(N^4)
   
   → COLMAP / OpenCV 默认实现
```

### 6.3 Production 应用

| 系统 | 用 PnP 哪里 |
|---|---|
| ORB-SLAM3 | tracking thread, 每帧用 motion-only BA (= PnP refine) |
| FoundationPose | 求物体 pose (而非相机 pose) — 同样数学 |
| AR (Apple Vision Pro) | inside-out tracking 用 PnP refine |
| visual relocalization | "我现在在哪" - PnP 从 known map + 当前 view |

---

## 7 · 相机标定 (Camera Calibration)

### 7.1 Zhang's method (2000)

```
   过程:
   1. 拍 chessboard (棋盘格) 在多个不同姿态下
   2. 检测棋盘 corner → 2D 像素 + 已知 3D 物理坐标
   3. 解 Homography for each view → 解 K (内参) + 每个 view 的 [R|t]
   4. Bundle adjustment 联合优化所有参数
   
   工具:
     • OpenCV calibrateCamera() — 简单单目
     • Kalibr (ETHZ) — 多相机 + IMU + extrinsic (production standard)
     • Camera Calibration Toolbox (Bouguet) — historical reference
```

### 7.2 在线标定

**问题**: drone 飞行震动 / 温度漂 → calibration drift（前面已提）

**解法**: 把 K + [R|t] 当 state variable 在 SLAM 优化里在线 refine
- VINS-Fusion `estimate_imu_intrinsic: 1`
- OpenVINS `estimate_extrinsic: 1`
- 需要 motion excitation 保证可观测性（见 imu_preintegration §6.4）

---

## 8 · 现代 viewpoint: VGGT 谱系如何 "替代" classical projection

```
   Classical:
     RGB → corner detection → matching → 5-point + RANSAC → E → triangulate → 3D
     (5-7 阶段, 各种 prior knowledge)
   
   VGGT-class:
     N RGB → transformer → {pose_i, depth_i, point_i, tracks}  (单次前向!)
     (隐式学会 projection, 没有显式 K!)
```

**VGGT 隐含的 projection**: 训练数据是 (RGB, K, [R|t], 3D) 四元组，模型学到了 "K 和 [R|t] 的统计先验"。**优势**: 不要标定数据；**劣势**: 不输出 K（无法 transfer 到新相机），un-metric（K 缺 baseline）。

→ **MapAnything (3DV 2026)** 把 K 当可选输入，部分回归 classical 范式。

→ 见 [feed-forward-3d/README.md](../feed-forward-3d/README.md) 三件套对照。

---

## 9 · Hidden Assumptions

- **Pinhole 模型**: 假设镜头无失真，实际所有镜头都有 → 必须用 Brown-Conrady / Kannala-Brandt
- **内参 K 恒定**: 假设温度 / 振动不影响 → 实际 drone 飞行 calibration drift
- **rigid body 假设**: 假设 camera + IMU 刚性连接 → 实际 IMU mount silicone 会让两者有微小 dynamic offset
- **大气透明**: 投影忽略大气散射 / 折射 → 远距离 outdoor 不成立
- **静态场景**: 多视图几何假设 3D 点不动 → 动态物体破坏 epipolar constraint
- **充分 baseline**: triangulation 需 baseline → 单目纯旋转无法恢复 depth

---

## 10 · 比较 & 面试 Tip

| 方法 | 输入 | 输出 | 何时用 |
|---|---|---|---|
| Pinhole projection | X (3D) + (K, R, t) | (u, v) 像素 | 任意 forward rendering |
| Back-projection | (u, v) + Z + K | X_c (3D) | depth → point cloud |
| Triangulation | (u₁, u₂) + 2 相机位姿 | X_world | stereo / 2-view SfM |
| Essential E | ≥5 对应点对 | (R, t̂) 相对姿态 | 2-view SLAM init |
| PnP | N 个 3D-2D 对应 | (R, t) camera pose | tracking / relocalization |
| Zhang's method | 多 view 棋盘 | K + distortion | offline calibration |

> **🎤 Interview Tip.** "为什么单目 SLAM 有 scale 模糊?" —— 强答："Essential matrix 编码 R + t̂（t 的方向），但 t 的*大小*完全无法从图像恢复 —— 因为图像只给你 epipolar constraint（角度），不给绝对距离。Triangulation 出来的 3D 是 *相对* scale。任何想 metric 的单目 SLAM 必须外部 anchor（stereo / IMU / known object size / GNSS）—— 这就是 Metric3D 用 canonical-camera transformation 和 MapAnything 用 metric scale factor 各自给的解。"

加分：解释 "为什么 fisheye 不能用 Brown-Conrady 模型" —— 答："Brown-Conrady 假设 θ_d ≈ θ（小角度近似），但 fisheye FOV >100° 时 sin(θ) 大变化，必须用 Kannala-Brandt 的多项式 θ_d = θ·(1 + k1θ² + ...)。"

---

## Boundary

- **3D 旋转 / SE(3) 数学** → [`./se3_so3_lie_groups_primer.md`](./se3_so3_lie_groups_primer.md)
- **0 数学基础前置** → [`./rotation_intuition_primer.md`](./rotation_intuition_primer.md)
- **BA 怎么用相机投影** → [`./bundle_adjustment.md`](./bundle_adjustment.md)
- **IMU + 相机时间对齐 + extrinsic 在线** → [`./imu_preintegration_math.md`](./imu_preintegration_math.md) §6.2, §6.4
- **Depth 输出对接 back-projection** → [`../depth-foundation/`](../depth-foundation/)
- **RGB sensor 物理（CMOS / Bayer / lens）** → [`../sensor-physics/rgb_camera_imaging_pipeline.md`](../sensor-physics/rgb_camera_imaging_pipeline.md)
- **stereo geometry physics** → [`../sensor-physics/stereo_camera_geometry_physics.md`](../sensor-physics/stereo_camera_geometry_physics.md)
- **Rolling vs global shutter** → [`../sensor-physics/rolling_vs_global_shutter.md`](../sensor-physics/rolling_vs_global_shutter.md)
- **VGGT / MapAnything 现代替代品** → [`../feed-forward-3d/README.md`](../feed-forward-3d/README.md)

---

## References

- Hartley & Zisserman (2003) *Multiple View Geometry in Computer Vision*, 2nd ed. **The bible.** Ch. 5-13.
- Zhang (2000) *A Flexible New Technique for Camera Calibration*. IEEE T-PAMI.
- Nistér (2004) *An efficient solution to the five-point relative pose problem*. IEEE T-PAMI.
- Hartley (1997) *In Defense of the Eight-Point Algorithm*. IEEE T-PAMI.
- Lepetit, Moreno-Noguer, Fua (2009) *EPnP: An Accurate O(n) Solution to the PnP Problem*. IJCV.
- Kannala, Brandt (2006) *A Generic Camera Model and Calibration Method for Conventional, Wide-Angle, and Fish-Eye Lenses*. IEEE T-PAMI.
- Kalibr toolbox — https://github.com/ethz-asl/kalibr
- OpenCV camera calibration docs — https://docs.opencv.org/

---

[← Back to Spatial Math](./README.md)
