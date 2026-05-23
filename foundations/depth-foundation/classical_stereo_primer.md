# 经典双目几何入门 (Classical Stereo Geometry Primer)

> 📚 **教材出处**：HKUST ELEC5660 *Introduction to Aerial Robotics* (Spring 2026, 沈劭劼主讲) L7 + Project 2 Phase 2 (stereo_vo)
> 📜 **License**: 原始 slide 与代码遵循 [BSD 3-Clause](https://github.com/HKUST-Aerial-Robotics/HKUST-ELEC5660-Introduction-to-Aerial-Robotics/blob/main/LICENSE)；本 primer 为改写 + 补充教材
> 📄 **公开参考**: Hartley & Zisserman *MVG* (2nd ed., 2004)；Hirschmuller 2008 (SGM, TPAMI)；[camodocal](https://github.com/hengli/camodocal)

**Status:** v1 — primer 类型（不强制 Eureka / Worked Example，重直觉）；depth-foundation zone 缺的经典 stereo 数学底座。

---

## TL;DR — 为什么 deep stereo 之前要先懂经典

zone 里 Depth Anything / MoGe / Metric3D / FoundationStereo 全是 **deep model 解构**，没人讲*为什么*它们的输入是 rectified pair、*为什么*输出是 disparity 不是直接 depth、*为什么*缺 confidence map 是 [FoundationStereo failure atlas](./github_failure_atlas.md) 第一根刺。这些不是 deep 决定的 — 是 1970s 起经典 pipeline 沉淀的工程约束。学完能回答：D435 为什么在 5 m 外"幻觉"(§1)；matching 为什么 1D 不 2D (§2)；为什么必须 rectify (§3, §7)；FoundationStereo 不给 confidence 为什么是大事（§6, §9 — 经典 SGM *默认*给 LR-consistency mask）；OAK-D / RealSense / ZED 为什么默认都是 SGM (§10)。本文是 **map** 不是 deep dive — 走完能看懂下游 `./foundationstereo_dissection.md` 第 1 节为什么以 `Z = f·B/d` 一行起手。

---

## §1 双目几何基础：disparity 怎么变成 depth

设两台相机光轴*完全平行*、焦距 `f`、baseline `B`。空间点 `P = (X, Y, Z)`：

```
u_L = f · X / Z
u_R = f · (X − B) / Z
d   = u_L − u_R = f · B / Z     ← disparity 定义
Z   = f · B / d                  ← 经典立体深度公式
```

三个直接推论：

**(1) Depth 与 disparity 反比放大**：`∂Z/∂d = −Z²/(f·B)`。`Z` 一倍 → `∂Z/∂d` 四倍。"近距精、远距糊"是 *结构性* 问题，不是工程问题。

**(2) Baseline 决定可用 range 上限** — 远处 disparity → 0。亚像素 refinement 推到 ~0.1 px 是物理极限。给定亚像素精度 `Δd`：`Z_max ≈ √(f·B/Δd)`。要测远 → 加 baseline 或加 focal（FoV 变窄）。`UNVERIFIED` 常引数字：RealSense D435 baseline 5 cm → 有效 < 3 m；ZED 2 baseline 12 cm → ~10 m；KITTI rig baseline 54 cm → ~80 m。

**(3) Baseline / occlusion trade-off** — baseline 越大测远越准，但 occlusion 区域多、匹配失败区扩大。drone 端 SWaP 再压一层 baseline 上限。

---

## §2 Epipolar geometry：为什么从 2D 搜索降到 1D

§1 假设光轴平行；现实双目绝不完美对齐。一般情况：空间点 `P` 与两投影中心 `O_L, O_R` 张成 **epipolar plane**，与左右像面相交得到两条 **epipolar line**。关键事实：

> 给定左图点 `p_L`，其右图对应点 `p_R` **必在某条 epipolar line 上**。

搜索从 *2D 整图* 缩到 *1D 直线* — `O(W·H) → O(W)`，且排除大量虚假匹配。

**Essential / Fundamental matrix** 编码约束：

```
p_R^T · F · p_L = 0           ← 像素坐标
x_R^T · E · x_L = 0           ← 归一化坐标
E = [t]× · R                  ← R, t 右相机相对左的位姿
F = K_R^(−T) · E · K_L^(−1)
```

`[t]×` 是 `t` 的反对称矩阵。`E` 由相对 pose 决定（5 DoF：3 rot + 2 translation 方向，scale 不可恢复）。`F` ≥7 对点（8-point）从图像直接估出，不需 calibration → **uncalibrated stereo**。`E` SVD 分解可得 `(R, t)` — stereo VO 中 "5-point" 相对位姿估计的核心 (Nistér 2004)；HKUST Project 2 Phase 2 `estimator.cpp` 走这条路径。

---

## §3 Stereo rectification：把任意双目"摆正"

epipolar 把搜索降到 1D，但 1D 是 *斜的*。Rectification 更猛：**用 image warping 把两图重投影，使所有 epipolar line 变成水平 row-aligned**。rectify 后左图第 `v` 行点对应右图第 `v` 行 → 沿 row 一维搜索；这是 §1 平行光轴假设的 *软件实现* — 物理上相机仍歪，warp 后的 *virtual* camera 满足公式。**整个 deep stereo 流水线（PSMNet / RAFT-Stereo / FoundationStereo）默认输入是 rectified pair**，不 rectify 丢入网络输出垃圾。

**Bouguet 算法** (OpenCV `stereoRectify`)：(1) 把右相机旋转 `R^(1/2)`、左 `R^(−1/2)` 光轴对称指中间；(2) 再加旋转把 `t` 转到沿 X 轴 → baseline 横平；(3) 算 rectifying homography `H_L, H_R` 应用到原图；(4) crop / 保 FoV。**前提是 calibration 准确**：`B, f`、distortion 任何一个错，rectify 出的 epipolar line 就不水平 → §1 公式不成立 → depth 系统偏，这是 §9 calibration drift 的本质。

---

## §4 Block matching / SAD / NCC：cost volume 起源

rectified 后对左图 `(u, v)` 沿右图 row `v` 在 `[d_min, d_max]` 搜索：

```
SAD(d) = Σ |I_L − I_R|                               ← Sum of Absolute Differences
SSD(d) = Σ (I_L − I_R)²                              ← Sum of Squared Differences
NCC(d) = Σ (I_L − μ_L)(I_R − μ_R) / (σ_L · σ_R)      ← Normalized Cross-Correlation
```

patch `W` 典型 5×5 ~ 15×15。每 pixel × 每候选 `d` 算一次 → 三维 `C[u, v, d]` 即 **cost volume**，`d*(u, v) = argmin_d C[u, v, d]`。**直接预示 deep stereo 为什么存在**：(a) **Textureless** 区 patch 相似度无差别 → argmin 随机 → 雪花。(b) **重复纹理**多 `d` 同低 cost → ambiguity。(c) **窗口大小 trade-off**：小 → 精度高抗噪差；大 → 抗噪但跨 depth discontinuity 平均 → 边缘"流"。(d) **光照不一致**：SAD/SSD 对 gain/exposure 敏感；**Census transform** (Zabih 1994) 把像素换成局部二值串算 Hamming distance，对单调光照变化免疫 — 至今是嵌入式默认。

---

## §5 SGM (Semi-Global Matching)：经典 stereo 的天花板

local block matching 只看一个 window，textureless / 重复区域必坏。global MRF 把整张图 disparity 当能量最小化 `E(D) = Σ_p C(p, D_p) + Σ_{p,q∈N} V(D_p, D_q)` — 但 2D MRF 全局优化 NP-hard。**Hirschmuller 2008 SGM 的洞察**：

> 沿 *单一方向* 的 1D 动态规划是多项式时间且最优。把 8 方向（→ ← ↑ ↓ + 4 对角）的 1D 解加起来近似 2D 全局解。

沿方向 `r` 的递推：

```
L_r(p, d) = C(p, d) + min{
                L_r(p−r, d),               ← disparity 不变
                L_r(p−r, d±1) + P1,        ← ±1 跳，小惩罚
                min_i L_r(p−r, i) + P2     ← 大跳，大惩罚
            } − min_k L_r(p−r, k)          ← 数值稳定
```

总 cost `S(p, d) = Σ_r L_r(p, d)`；`P1 < P2` 是核心 trick — 倾斜表面（小跳）惩罚小、物体边缘（大跳）惩罚大。HKUST L7 给的 reference 链路（MathWorks visionhdl）：CSCT (Center-Symmetric Census Transform) → Hamming distance → 5 方向累加 → minimum cost index → uniqueness check + 抛物线插值。**SGM 至今没被 deep model 在嵌入式上击败** — OAK-D / RealSense / ZED mini 内核默认就是它。

---

## §6 Sub-pixel refinement + post-processing

argmin 给整数 disparity，但 `Z = fB/d` 对 d 极敏感。cost minimum 附近用三点 **抛物线拟合**：

```
d_sub = d* + (C[d*−1] − C[d*+1]) / (2·(C[d*−1] − 2·C[d*] + C[d*+1]))
```

精度 1 px → ~0.1 px。深度模型直接输出 float disparity 跳过这步，本质等价。**post-processing 三件套**：(1) **Left-right consistency check** — 同时跑 `D_L, D_R`（互换 reference），要求 `|D_L(p) − D_R(p − D_L(p))| < threshold`，不满足标 invalid → 自动 occlusion mask。**这就是 FoundationStereo 缺的那个 confidence map 的经典版**。(2) **Speckle filtering** — 连通域分析，孤立小 disparity 块几乎必是噪声。(3) **Hole filling** — invalid 区域沿水平线插值（保守）或不填（诚实）。

---

## §7 Camera model 细节：pinhole 不够用

HKUST stereo_vo 的 `camera_models/include/camodocal/camera_models/` 提供四种 model：

| Model | 适用 FoV | 失真模型 | 何时用 |
|---|---|---|---|
| **Pinhole** | ≤ ~90° | radial `k1,k2,k3` + tangential `p1,p2` | 工业相机、KITTI rig |
| **Pinhole-full** | ≤ ~90° | 加 `k4,k5,k6` rational | 高精校准 |
| **MEI (CataCamera)** | 180°+ | unified sphere + radial + tangential | 全向 / catadioptric / 鱼眼 |
| **Kannala-Brandt (Equidistant)** | 100–200° | 角度多项式 `θ_d = θ(1 + k1θ² + ...)` | 广角 / 鱼眼业界默认 |

**关键纪律：rectify *必须* 在 distortion 模型正确的前提下做**。鱼眼用 pinhole `undistort` 的结果：中心还行（小角度 distortion 小），边缘 epipolar line 不水平甚至弯成抛物线，SGM 沿水平 row 搜索 → 外 30% 区域 disparity 是垃圾。HKUST L7 第 65 页画出 pipeline：**Raw → Undistortion (用对的 model) → Rectify → Crop**。

---

## §8 Triangulation：从 disparity 回到 3D 点

rectified parallel 下 `Z = fB/d` 直接给 depth；更一般地用 **DLT triangulation**：给点 `P` 在两 view 像素 `p_L, p_R`、投影矩阵 `P_L, P_R` (3×4)，每 view 贡献两条约束 `p × (P · X) = 0`，共 4 方程 4 未知（齐次 `X`）→ **SVD** 解最小奇异值对应右奇异向量。SVD 比直接解线性系统稳得多（病态时 LU 会爆）。

**Cheirality check** — 解出 3D 点必须在两相机*前方*（`Z > 0` in both frames），否则解了"镜像"。`E` SVD 分解给 4 候选 `(R, t)`，cheirality 是唯一筛真解的方法。Project 2 stereo_vo 恢复相对 pose 时反复用。

---

## §9 失败模式：经典 stereo 的硬边界

| 失败模式 | 机制 | 缓解 |
|---|---|---|
| **Textureless** (白墙、天空) | matching cost 平坦 | 主动光 IR pattern (RealSense / Kinect-2)；deep stereo learned prior |
| **Repetitive texture** (砖、栅栏) | 多 disparity 同低 cost | 大 baseline；multi-scale；deep model 含上下文 |
| **Reflective / specular** | 左右像看到不同反射，违反 brightness constancy | 偏振 filter；放弃这类区域 |
| **Calibration drift** | 温度 / 震动让 baseline / `R, t` 漂 → epipolar line 不水平 | 在线 self-calib；定期 re-calib（FoundationStereo atlas 明确点名） |
| **Baseline 硬上限** | `Z_max ≈ √(fB/Δd)` 几何不可超 | 加 baseline (SWaP 不许) / 加 focal (FoV 变窄) / 接受范围 |
| **Occlusion** | baseline 越大近物边只看到一边 | LR-consistency 自动 mask；hole-filling 保守填 |

下游 [`./foundationstereo_dissection.md`](./foundationstereo_dissection.md) §6 隐含假设里 calibration drift 是头号风险 — deep model 是 black box，calibration 错了它*不自己发现*，依然信心输出错 depth。

---

## §10 经典 vs 深度：什么时候用哪个？

KITTI 排行榜上 deep model 在 5+ 年前已越过 SGM。**但**：

| 维度 | SGM (经典) | Deep Stereo |
|---|---|---|
| KITTI 精度 | 中等 | SOTA |
| Textureless | 雪花 | 学习先验补 — 可能"幻觉" |
| 延迟 (Jetson Orin Nano) | < 10 ms (HW 加速) `UNVERIFIED` | ~50 ms+ |
| 内存 | < 100 MB | GPU + 模型 ~GB |
| Confidence map | 默认有 (LR-check, speckle mask) | 多数模型*不*给 — 隐含失败 |
| OOD | 慢慢糟 | 可能突然 catastrophic |
| 嵌入式默认 | ✅ OAK-D / RealSense / ZED mini | 仅高端 (Jetson Orin) |

实战 rule of thumb：(a) **OAK-D / RealSense / ZED**：默认 SGM 跑得好就别换。(b) **离线 mapping**：FoundationStereo 换上去，不在乎延迟。(c) **drone / 闭环 + Jetson 边缘**：先 SGM 跑通 → 实测有大量 textureless / 重复区域再上 deep；上 deep 必加 sanity check（LR-check 仍可外挂跑）。(d) **Safety-critical**（车、医疗）：deep 单独不可信，组合 SGM 作为 fallback / cross-check。

> **经典 SGM 仍是 ROS / 嵌入式 stereo 的默认。** 不因 deep 不够好，是因为 confidence map + 低延迟 + 5+ 年现场验证。

---

## §11 练习题（带数字直觉）

**Q1** — 题目原文：`B = 12 cm`、`f = 500 px`、`Z = 5 m`，1 px disparity error 对应多少 depth error？
`d = 500 × 0.12 / 5 = 12 px`；`∂Z/∂d = Z²/(f·B) = 25 / 60 = 0.417 m/px` → 1 px ≈ **41.7 cm** depth 误差。

**Q2** — 同 Q1 但 RealSense D435（`B = 5 cm, f = 380 px` `UNVERIFIED`）在 5 m：`d = 3.8 px`；`∂Z/∂d = 25/19 = 1.32 m/px` → 1 px ≈ **132 cm**！亚像素到 0.1 px 也只 13 cm 精度。这就是 D435 spec sheet 写 working range "up to 3 m" 的几何原因 — 5 m 不可用。

**Q3** — Rectification 对齐度检查：rectify 后同 row 对应点正确情况 `|v_L − v_R| ≤ 0.5 px`。若系统性偏 2–3 px 且随 row 变化 → calibration 错了，最可能 distortion 模型选错（鱼眼跑成 pinhole）。立即停止 SGM / deep stereo — garbage in garbage out。

---

## Cross-refs

- [`./foundationstereo_dissection.md`](./foundationstereo_dissection.md) — 看完本文能理解 §1 napkin formula `Z = f·B/d`、§6 calibration drift 是头号风险、"无 confidence map"为什么是大问题（经典 SGM 默认给）。
- [`./depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md) — monocular 不需 rectify；度量版本若与 stereo 融合，仍需 rectified pair 作 stereo 分支输入。
- [`./depth_models_comparison.md`](./depth_models_comparison.md) — monocular vs stereo 工作范围表的几何解释在本文 §1 / §9。
- [`./github_failure_atlas.md`](./github_failure_atlas.md) — "calibration drift" / "textureless" / "无 confidence" 三大类，本文 §9 给出经典视角的同名诊断。
- 上游：HKUST ELEC5660 L7；Project 2 Phase 2 `camera_models/` (pinhole / MEI / Kannala-Brandt reference)、`stereo_vo_estimator/`；Hartley & Zisserman *MVG* §9-11；Hirschmuller 2008 (TPAMI) SGM 原文。

---

[← Back to Depth Foundation README](./overview.md)
