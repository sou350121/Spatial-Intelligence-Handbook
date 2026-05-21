# Direct Methods: DSO & LSD-SLAM (直接法 SLAM 解构)

> **Published:** LSD-SLAM (Engel *ECCV 2014*); DSO (Engel *T-PAMI 2018*, arXiv 1607.02565); SVO 2.0 (Forster *T-RO 2017*) —— TUM CV group / UZH RPG
> **核心定位:** 主流视觉 SLAM**没有**走的那条路。直接法跳过特征、直接在原始亮度上最小化光度误差 —— 在富梯度场景下赢，在闭环与长期一致性上输。

**Status:** v1。数字 `UNVERIFIED`。
**TL;DR:** 直接法证明了可以**不用描述子**做视觉 SLAM —— 在高梯度区域直接对像素亮度做 tracking 与建图。子像素精度、半稠密地图免费送。代价：光度标定非搞不可、曝光变化静默毁掉一切、闭环没解决。DSO 作为 DROID-SLAM 和 feed-forward 稠密方法的祖先而幸存。

**X-Ray.** 特征 SLAM 留角点（~99% 丢掉）。直接 SLAM 留所有梯度像素（~2000–10k/帧）。前端更轻、子像素、半稠密地图。但光度标定强制、曝光变化致命、闭环未解。这个领域押注 features 有原因；DSO 是解释这个押注为什么对的 demo。

## 📍 研究全景时间线

```
2011   2014       2014   2016         2021+
DTAM ► LSD-SLAM ► SVO ── DSO (peak) ► DROID-SLAM / learned-BA
└── direct: photometric error on intensities ──┘
└── features lineage ─► ORB-SLAM3
```

DSO 是**经典直接 SLAM 的顶点**：~2000 个稀疏 residual、光度标定、完整滑窗优化。DSO 之后，注意力转向 learned dense（DROID-SLAM）。

---

## 1 · 架构

### 1.1 根本分歧

| | Feature (ORB-SLAM) | Direct (DSO/LSD) |
|---|---|---|
| 优化目标 | reprojection（3D→2D） | photometric（亮度） |
| 每帧 residual | ~100 个特征 | ~2000 (DSO) – >10k (LSD) |
| 前端 | descriptor + match | 只看梯度 |
| 子像素？ | 否 | 是 |
| 闭环 | DBoW2 | 难 —— §6 |
| 光度标定 | 容忍 | 强制 |
| 地图密度 | 稀疏 | 半稠密+ |

### 1.2 ⚡ Eureka Moment

> **"你不需要识别一个像素是什么 —— 只需要它在被正确重投影时亮度保持不变。"**

押下这个赌注，descriptor 提取、匹配、feature-based BA 都消失。你拿到子像素精度和半稠密地图；你交出闭环、光照鲁棒性、scale 恢复。

### 1.3 DSO 架构（稀疏直接）

```
   Frame → select ~2000 gradient pts (inverse-depth param)
        → Sliding-window photometric BA (7 KFs: poses + depths + affine (a,b); marginalize on slide-out)
        → sparse 3D point cloud
```

LSD-SLAM 跟踪每个梯度像素 + per-pixel 概率深度滤波器 → 半稠密地图。DSO 为了速度**故意稀疏**。

---

## 2 · 数学核心

### 📌 Napkin Formula

```
E_photo = Σᵢ Σ_p  wₚ · ρ( I_j(π(K·(R_ij·π⁻¹(p, d_p) + t_ij))) − b_j − e^{a_j−a_i}·(Iᵢ(p) − bᵢ) )
```

对于帧 `i`、点 `p`，经位姿 `(R_ij, t_ij)` + 逆深度 `d_p` 投到 `j`；最小化经 affine-brightness 校正后的亮度差。`(a, b)` = 每帧曝光参数。

| 符号 | 含义 |
|---|---|
| `Iᵢ(p)` | 帧 `i` 中像素的亮度 |
| `d_p` | 逆深度（有界、能处理无穷远） |
| `(aᵢ, bᵢ)` | 仿射亮度：`I' = e^a · I + b` |
| `ρ` | Huber kernel |

**直觉:** `(a, b)` 是挡在你和"曝光导致 crash"之间的那一层。DSO 的不变量是*光度*，ORB-SLAM3 是*几何* —— 各自有各自的崩溃方式。滑窗约 7 个 KF；直接法追求*局部完美*，不是全局一致。

---

## 3 · 模式例子

同一条走廊，两种光照场景：

| 场景 | ORB-SLAM3 | DSO |
|---|---|---|
| **A** 有纹理墙、平滑光 | 能跑 | **更好** —— 子像素，约 2× 精度 `UNVERIFIED` |
| **B** 闪烁 + 阳光区切换 | 容忍 ~30% 亮度偏移 | **崩** —— 仿射 `(a,b)` 饱和、tracking 丢 |

DSO 在*干净*场景赢，在*真实世界光照*下输 —— features 在 production 占主导的原因。只有相机级光度预标定（response + vignette）才能让 DSO 在户外跑下去。

---

## 4 · 工程：何时选直接法

| 你有... | Direct (DSO) | Features (ORB-SLAM3) |
|---|---|---|
| 光度标定 | ✅ 免费精度 | —— |
| 自动曝光、没标定 | ❌ 静默失败 | ✅ 容忍 |
| 需要稠密地图 | ✅ 免费 | ❌ 要另起一步 |
| 闭环 | ❌ 难 | ✅ DBoW2 成熟 |
| 运动模糊 | ❌ 梯度糊 | ⚠️ 也退化 |
| IMU | ⚠️ DSO-VI 不成熟 | ✅ 成熟 |

**模式:** 直接法 → 研究 / 稠密建图；特征法 → 量产。例外：摄影测量（BundleFusion 风格的后处理稠密对齐）。

**SVO 的中间路线:** 半直接 VO（Forster）：选点用 feature，tracking 用光度（子像素直接对齐）。drone 上 100+ Hz 出货 `UNVERIFIED`；UZH RPG 谱系。如果非选一个"能部署的直接法"，是 SVO，不是 DSO。

---

## 5 · 数据与评测

DSO —— TUM mono + EuRoC：在友好序列上直接法 translational 比 features 好 2–3× `UNVERIFIED`。LSD-SLAM —— TUM RGB-D 半稠密重建。⚠️ 两者都**室内 + 光度已标定**。户外 / aerial / 没标过的手机就是另一个故事。

---

## 6 · 能力与失败模式

**优势:** 子像素 tracking；免费的半稠密地图；嵌入式 CPU 占用更低；显式光度标定。

**劣势:** 曝光 / 光照变化（#1 杀手）；闭环未解（没 descriptor → DBoW2 不适用）；大位移破坏线性化；梯度稀少区失败。

### 6.1 Hidden Assumptions

- **亮度恒定** —— 立项前提。自动曝光 / HDR / 闪烁 / 阴阳交界违反它。仿射 `(a,b)` 只修全局偏移。
- **帧间小运动** —— 激烈运动 → 线性化间隙 → tracking 丢。
- **Lambertian 表面** —— 镜面（玻璃、抛光地板）在运动中破坏亮度恒定。
- **光度标定可用** —— 大部分用户跳过实测 response + vignette → 静默退化。
- **不需要闭环** —— 非回路轨迹 → 漂移无界。

---

## 7 · 比较 & 面试 Tip

| 栈 | 前端 | 闭环 | 地图 | 出货于 |
|---|---|---|---|---|
| ORB-SLAM3 | features (ORB) | DBoW2+Atlas | 稀疏 | 室内 RGB-D / AR / manipulation |
| **DSO** | 直接（稀疏） | 弱 / 无 | 半稠密 | 研究 / 稠密重建 |
| LSD-SLAM | 直接（半稠密） | FabMap | 半稠密 | 大尺度 mono 建图 |
| SVO 2.0 | 半直接 | 可选 | 稀疏+深度 | UZH aerial PoC |
| DROID-SLAM | learned dense | learned | 稠密 | 离线 / GPU |
| VGGT | feed-forward | n/a | 稠密 pointmap | foundation 后继 |

> **🎤 Interview Tip.** "DSO 精度更好，直接法为什么没赢？" —— 正确答："闭环与曝光不变性。直接法优化的是正确的局部目标，但没继承全局 place-recognition 基元；亮度恒定在没有受控光度标定的场景下很难强制。ORB-SLAM3 让一个较差的局部目标在全局上能用；DSO 让一个较好的局部目标在全局上崩。" 错答："DSO 更差" —— 它是结构性不同。

---

## Boundary

- ORB-SLAM3 机制 → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md)。
- Aerial 实时 VIO（VINS / OpenVINS / DROID） → [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/README.md)。不重复。
- VGGT / feed-forward 3D 后继 → [`foundations/feed-forward-3d/`](../feed-forward-3d/)。
- 光度 / 传感器标定流程 → [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md)。

---

## References

- DSO —— Engel, Koltun, Cremers · *T-PAMI 2018* · https://arxiv.org/abs/1607.02565
- LSD-SLAM —— Engel, Schöps, Cremers · *ECCV 2014*
- SVO 2.0 —— Forster et al. · *T-RO 2017* · https://rpg.ifi.uzh.ch/svo2.html
- DTAM —— Newcombe et al. · *ICCV 2011*
- TUM mono —— https://vision.in.tum.de/data/datasets/mono-dataset

---

[← Back to Classical SLAM](./README.md)
