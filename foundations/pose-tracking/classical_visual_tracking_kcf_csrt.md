# 经典 Visual Tracking：从 MOSSE 到 KCF 到 CSRT (Classical Visual Tracking: MOSSE → KCF → CSRT)

> **发布时间**: MOSSE — CVPR 2010 (Bolme et al., CSU) · KCF — TPAMI 2014 / arXiv 1404.7584 (Henriques et al., Coimbra) · CSR-DCF (CSRT) — CVPR 2017 / arXiv 1611.08461 (Lukežič et al., Ljubljana + CTU)
> **论文 / 模型**: MOSSE · CSK · KCF · DCF · SRDCF · CSR-DCF (`cv2.TrackerCSRT`)
> **核心定位**: 2010-2017 主宰 visual tracking 的 **correlation filter** 谱系. 不用 GPU、不用 deep features 也能在 CPU 单线程跑数百 FPS — 至今仍是嵌入式 / 实时 / 边缘场景的默认.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · *Pre-deep* 时代的 visual tracker 工程默认；仍占据 OpenCV `legacy` namespace.
**TL;DR.** 2010 年 Bolme 用 FFT 在频域学一个 correlation filter，让追踪在桌面 CPU 上跑到 ~669 FPS（论文宣称 `UNVERIFIED`）. Henriques 把它 kernel 化（KCF），用 circulant matrix 数学技巧让训练样本 "免费". Lukežič 2017 给 channel + spatial reliability 加成（CSRT），目前是 OpenCV 里 *non-deep* CPU tracker 的默认推荐. 当今仍在用 — drone 嵌入式 / 监控 / Pi 类项目里 GPU 是 luxury.

**X-Ray.** Deep tracker 之前，"我要 bounding box 跟一帧到下一帧" 的工程答案是 **correlation filter**：把 patch 当做模板，在新一帧上做 cross-correlation（FFT 加速），找峰值即新位置. KCF 加 kernel trick + HOG channel，CSRT 加遮挡可靠性 mask. 这条线即"轻量 visual tracking"族 — 2017 后被 SiamFC / SiamRPN 等 deep tracker 在精度上超越，但在 CPU-only / <50 ms / 无 model download 的部署上**至今没有真正替代品**.

---

## 📍 研究全景时间线

```
2010      2012        2014           2015      2017            2018+
MOSSE ──► CSK ──────► KCF / DCF ───► SRDCF ──► CSR-DCF(CSRT) ──► SiamFC takes over (deep)
└── frequency-domain correlation filter ─┘    └─ channel+spatial reliability ─┘   └─ siamese / transformer (GPU) ─┘
```

从 2010 *单帧 FFT filter* 到 2017 *channel-weighted reliable mask* 的 7 年演进. 2018 后 deep tracker (SiamRPN / SiamMask) 通吃 benchmark 排行榜，但 CPU 实时 / 嵌入式仍是 CSRT 的天下.

---

## 1 · 三代谱系：架构与"发明了什么"

### 1.1 系统对比

| Tracker | Year | 训练样本来源 | Feature | 关键技巧 | 报告速度 `UNVERIFIED` | OpenCV API |
|---|---|---|---|---|---|---|
| **MOSSE** | 2010 | 第一帧 + 仿射扰动 | 原始 grayscale | FFT 频域 MOSSE 解 | ~669 FPS (论文) | `cv2.legacy.TrackerMOSSE` |
| **CSK** | 2012 | circulant shift | grayscale | 隐式密集采样 | ~362 FPS `UNVERIFIED` | — |
| **KCF / DCF** | 2014 | circulant shift | **HOG** (KCF) / 灰度 (DCF) | Kernel trick + circulant FFT | ~172 FPS (KCF on HOG `UNVERIFIED`) | `cv2.legacy.TrackerKCF` |
| **SRDCF** | 2015 | 大搜索区 | HOG + CN | 空间正则化（边缘惩罚） | ~5 FPS `UNVERIFIED` | — |
| **CSR-DCF (CSRT)** | 2017 | 大搜索区 | HOG + CN | Channel 可靠性 + spatial mask | ~13 FPS `UNVERIFIED` | `cv2.TrackerCSRT` |

注意 **KCF 与 DCF 的区别**：KCF = kernelized（Gaussian kernel + HOG），DCF = dual 线性形式（只灰度）—— Henriques 一篇论文同时给出两个.

### 1.2 ⚡ Eureka Moment

> **把"在搜索窗里滑动模板找峰值"重新表述为"在频域里一次相乘"，再用 circulant matrix 把*所有平移样本*的训练等价为单一闭式解 — 一次相乘代替成千上万个 sliding window forward.**

这是 2010-2014 的核心爆破点. Bolme MOSSE 用 FFT 让搜索 cost 从 O(HW · template) 降到 O(HW log HW). Henriques 进一步意识到：**在循环移位生成的"虚拟训练集"上岭回归，有闭式 FFT 解** — 训练根本不需要遍历样本. Lukežič 2017 把"哪些 channel / 哪些像素该信任"显式建模，让 filter 不被背景拉走.

### 1.3 信息流（CSRT 简化版）

```
   first frame + bbox
        │
        ▼
   提取 HOG + CN channels  ──┐
        │                    │  per-channel reliability
        ▼                    ▼
   FFT → 频域 filter F  ◄── channel weights w_c
        │
   下一帧 search patch ──► FFT ──► 与 F 频域相乘 ──► IFFT
        │                                              │
        ▼                                              ▼
   spatial reliability mask（前景概率，色彩直方图）─► 加权响应
        │
        ▼
   响应 peak → 新位置 → 用新 patch 在线更新 F（learning rate η）
```

---

## 2 · 数学核心：Circulant + FFT = 几乎免费的训练

### 📌 Napkin Formula

```
   f̂  =  (ĝ ⊙ x̂*) / (x̂ ⊙ x̂* + λ)
```

频域 ridge regression 闭式解：filter `f̂`（hat = FFT）= 期望响应 `ĝ` 与训练 patch 共轭 `x̂*` 的逐元素乘积，除以 `|x̂|² + λ`. **一次 FFT、一次逐元素除法、一次 IFFT**. 在 64×64 patch 上单 CPU 核 < 1 ms `UNVERIFIED`.

| Symbol | Meaning |
|---|---|
| `x` | 训练 patch（cropped from first frame）|
| `g` | 期望响应（Gaussian，中心 = bbox 中心）|
| `f` | 学到的 correlation filter |
| `x̂` | `FFT(x)` |
| `⊙` | 逐元素乘法（Hadamard） |
| `x̂*` | `x̂` 的复共轭 |
| `λ` | ridge 正则化常数（典型 1e-4）|

**Intuition.** Circulant matrix 是"把所有 shift 后的 patch 堆成矩阵"——其特征向量恰是 DFT 基. 所以 *岭回归 + 所有 shift 训练样本* = *DFT 域逐元素 ridge*. 训练所需 "成千上万个 sliding 样本" 用 FFT 一步搞定. 这是 2014 的代数奇迹.

### KCF 的 kernel 化

```
   α̂  =  ĝ / (k̂_xx + λ)        # 训练
   response  =  IFFT( k̂_xz ⊙ α̂ )  # 推理
```

其中 `k_xx` = `x` 与自己的 kernel correlation（Gaussian 或 polynomial），`k_xz` = `x` 与新 patch `z` 的 kernel correlation. 整个 RKHS 表示用 FFT 一样廉价 —— 因为 circulant 结构保留.

### CSR-DCF 加成

```
   F_c   =  (ĝ ⊙ x̂_c*) / (x̂_c ⊙ x̂_c* + λ)     # per-channel
   w_c   =  PSR(F_c)                              # channel reliability
   m(p)  =  fg-posterior(p) · constraint mask     # spatial mask
```

每个 channel 独立学 filter，按 PSR (peak-to-sidelobe ratio) 加权；同时用前景 / 背景颜色直方图算 spatial reliability mask，"哪些像素是物体" 的软先验. 这两个 reliability 是 2017 论文的真正贡献.

---

## 3 · 带数字走一遍：64×64 patch 一帧追踪

设：320×240 视频，目标 bbox 64×64，HOG cell 4×4 → feature map 16×16，bin 31 维.

1. **首帧训练.** Crop patch → HOG (16×16×31) → FFT per-channel → 共轭乘 ĝ → 除 |x̂|²+λ → `f̂_c` 一组. ~2 ms `UNVERIFIED`.
2. **下一帧.** 在上一位置 ±1.5× bbox 搜索区 crop → HOG → FFT → ⊙ 共轭 `f̂_c` → IFFT → response map. ~1.5 ms `UNVERIFIED`.
3. **峰值定位.** `argmax(response)` 给 cell-level 位置；亚像素用 paraboloid fit. 位移误差 < 1 px.
4. **在线更新.** 用新 patch 算新 `f̂_c'`，按 `f̂_c ← (1−η) f̂_c + η f̂_c'`（η ≈ 0.02）. ~2 ms `UNVERIFIED`.

桌面 i7 单线程 KCF 全帧约 ~5 ms，~200 FPS `UNVERIFIED`. CSRT 因 channel reliability + 大搜索区，约 ~30 ms / ~30 FPS `UNVERIFIED`. **零 GPU、零 model download**.

---

## 4 · 工程视角：何时仍在用？

### 4.1 KLT / Lucas-Kanade — 与 KCF 完全不同的角色

容易混淆：**KLT (Lucas-Kanade 1981)** 是另一条线 — 它追踪*点*（feature points: Harris / Shi-Tomasi corners），不是 bbox. KLT 解 `(I_x I_y) Δ = -I_t` 的 2-equation system，per-point. 在 **SLAM / VIO 前端**几乎所有 visual front-end 都跑 KLT：ORB-SLAM3、OpenVINS、VINS-Mono 的 monocular 流程都靠 KLT 在帧间 propagate 角点.

| 角色 | KLT | KCF / CSRT |
|---|---|---|
| 追踪对象 | 单个 feature 点（pixel）| Bounding box（object）|
| 数学 | 2-eq Newton iter（image gradient）| FFT correlation filter |
| 典型用途 | **SLAM 前端 keypoint association** | Visual object tracking（drone follow、监控）|
| 抗大位移 | 弱（需金字塔） | 中（搜索区参数化）|
| ORB matching 区别 | KLT 在像素灰度连续性 *track*；ORB 在 descriptor 离散 *match* | — |

**关键区分**：**ORB matching 是"重新匹配"**（无时间假设、跨帧 descriptor 距离），KLT 是**"传播"**（小位移、image gradient）. ORB-SLAM3 实际混用：keyframe 间用 ORB matching，帧间用 KLT-like 光流（视实现）.

### 4.2 嵌入式 / 实时 / 无 GPU 场景

| 场景 | 为什么仍选 CSRT | 替代品 |
|---|---|---|
| Raspberry Pi / Jetson Nano drone follow `UNVERIFIED` | Deep tracker (Siam) 在 CPU < 5 FPS；CSRT 仍 ~20 FPS | SiamFC TVM 量化 `UNVERIFIED` |
| 监控 NVR 多路并发 | 每路独立线程 0.5 core 即跑 | YOLO + ByteTrack（per-frame 检测重） |
| OpenCV 教学 / 原型 | 一行 `cv2.TrackerCSRT_create()`，零模型文件 | — |
| ROS workshops / 工业 visual servo PoC | 不需要 PyTorch / CUDA 栈 | — |

**OpenCV legacy trackers 现状**（OpenCV 4.5+）：MOSSE / KCF / TLD / Boosting / MIL 已迁到 `cv2.legacy.Tracker*`，明确标记 deprecated 但**未移除**. **CSRT** 仍在 `cv2.TrackerCSRT_create()` 主 namespace，是官方推荐 CPU tracker.

### 4.3 与 deep tracker 对比

| Axis | CSRT (CSR-DCF) | SiamRPN++ | STARK / MixFormer |
|---|---|---|---|
| Params | ~10 KB filter | ~50 M | ~100 M |
| GPU 必需? | **否** | 是 | 是 |
| CPU FPS（桌面 i7）`UNVERIFIED` | ~30 | ~3 | ~1 |
| GPU FPS (3080)`UNVERIFIED` | — | ~150 | ~50 |
| LaSOT AUC `UNVERIFIED` | ~24% | ~50% | ~67% |
| 在线更新 | 是（per-frame η update）| 否（template 固定）| 是（动态 template）|
| 训练数据需求 | **零** — 第一帧 bbox 即可 | ImageNet VID + GOT-10k | + LaSOT + TrackingNet |

差 ~25-40 AUC 点但**省一台机器**. 大多数嵌入式项目这个 trade 仍合算.

---

## 5 · Data & Eval

- **MOSSE / KCF / CSRT 发表 era benchmark**：OTB-50 / OTB-100（Wu 2013/2015）+ VOT 系列（Kristan 2013-2019）.
- KCF 在 OTB-100 上 ~62.3% precision `UNVERIFIED`；CSR-DCF 在 VOT-2016 / VOT-2017 上**冠军级**（EAO ~0.34 `UNVERIFIED`，超过同年所有 non-deep tracker）.
- LaSOT（2018+）出现后这些 CF tracker 在 long-term 长视频上崩塌：LaSOT 平均 2500 帧、含频繁遮挡 + 完全脱离镜头 → 在线更新模型很快 drift.
- **学术训练数据需求 = 零**：CSRT 是 "online learning from frame 1" 范式，没有 pretrain dataset 概念. SiamFC 之后才出现"训练 tracker 是个事"的世代.

---

## 6 · Capabilities & Failure Modes

**Capabilities.** CPU 实时；零模型；single bbox init 即可；对短时遮挡（PSR 检测）有 graceful pause；HOG + CN 在颜色 / 纹理稳定目标上 robust.

**Failure modes.**
- **长时遮挡 → drift**：在线更新让 filter 慢慢"学到"遮挡物，目标重现时已经追错.
- **快速旋转 / 形变**：rigid template 假设破裂；HOG 对 in-plane rotation 稳，对 out-of-plane 旋转弱.
- **相似 distractor**：第二个同色同形物体出现 → response map 双峰，无 re-ID 能力.
- **尺度变化大**：MOSSE / 原始 KCF 无 scale，需 multi-scale pyramid（CSRT 内置）；快速 zoom-in / zoom-out 失败.
- **Long-term**：> 30 秒视频 + 目标离开镜头 → 几乎一定 fail，没有 re-detection.

### 6.1 Hidden Assumptions

- **Filter 模板是 rigid**. 假设目标外观跨帧近似常数（仅小扰动 + 平移）；非刚体（人形、布料）违反.
- **目标始终在搜索区内**. KCF 搜索区 = 1.5–2.5× bbox；大跳跃 / 快速摄像头 pan 出搜索区即丢.
- **Background appearance 与 foreground 可分离**. 同色背景 → channel reliability 全低 → filter 无信号.
- **光照 / 颜色稳定**. CN feature 对色温变化敏感；阴天/夜间 → 直方图 mask 失效.
- **Periodic 更新不会 over-fit drift**. η 太大学到 distractor；η 太小不适应 appearance change. **一个超参数无 silver bullet**.

破坏时 *bbox 看着还在动* 但已锁错目标 — 静默失败.

---

## 7 · 与现代 deep tracker 对比 + Interview Tip

| Tracker | Year | Family | LaSOT AUC `UNVERIFIED` | CPU? | Model size |
|---|---|---|---|---|---|
| KCF | 2014 | Correlation filter | ~17% | ✅ | < 10 KB filter |
| CSR-DCF (CSRT) | 2017 | CF + reliability | ~24% | ✅ | < 50 KB |
| SiamFC | 2016 | Siamese CNN | ~33% | marginal | ~5 MB |
| SiamRPN++ | 2019 | Siamese + RPN | ~50% | ❌ | ~50 MB |
| STARK | 2021 | Transformer | ~67% | ❌ | ~30 MB |
| SAM 2 | 2024 | VFM video-mask | (different task) | ❌ | ~150 MB |

> **🎤 Interview Tip.** "为什么 2026 还提 KCF / CSRT？" — *"它们是 visual tracking 唯一的 CPU-real-time、零模型、第一帧训练的 tracker. Embedded / drone / 多路监控里 GPU 是 luxury，CSRT 仍是 OpenCV `cv2.TrackerCSRT_create()` 的官方推荐. Deep tracker (SiamRPN++、STARK) 在 LaSOT 上多 30-40 个 AUC 点 — 但需要 GPU、需要数百 MB 模型、需要预训练数据集. 工程上是不同 weight class."* 不要只背 LaSOT 排行榜.

---

## References

- MOSSE — *CVPR 2010*. Bolme et al. "Visual Object Tracking using Adaptive Correlation Filters." https://www.cs.colostate.edu/~draper/papers/bolme_cvpr10.pdf
- CSK — *ECCV 2012*. Henriques et al. "Exploiting the Circulant Structure of Tracking-by-Detection with Kernels."
- KCF — *TPAMI 2014* / arXiv 1404.7584. Henriques, Caseiro, Martins, Batista. "High-Speed Tracking with Kernelized Correlation Filters." https://arxiv.org/abs/1404.7584
- SRDCF — *ICCV 2015*. Danelljan et al.
- CSR-DCF (CSRT) — *CVPR 2017* / arXiv 1611.08461. Lukežič, Vojíř, Čehovin, Matas, Kristan. "Discriminative Correlation Filter with Channel and Spatial Reliability." https://arxiv.org/abs/1611.08461
- OpenCV `cv2.TrackerCSRT` docs: https://docs.opencv.org/4.x/d2/da2/classcv_1_1TrackerCSRT.html
- LaSOT benchmark — *CVPR 2019*. Fan et al. https://arxiv.org/abs/1809.07845
- Lucas-Kanade — *IJCAI 1981*. Lucas & Kanade. "An Iterative Image Registration Technique."

## Boundary

**Pre-deep CPU-real-time visual object tracker 原语**.
- 现代单物体 deep tracker (SiamFC → STARK → SAM 2) → [`siamese_to_transformer_sot_dissection.md`](./siamese_to_transformer_sot_dissection.md)
- 密集像素 flow（不是 bbox） → [`raft_optical_flow.md`](./raft_optical_flow.md)
- 长时序点追踪 → [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md)
- 6D 物体 pose（不只 2D bbox） → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md)
- KLT 在 SLAM 前端的角色 → [`../classical-slam/`](../classical-slam/)
- Drone active-tracking 工程使用 → [`../../embodiments/aerial/active-tracking/`](../../embodiments/aerial/active-tracking/)
- Correlation 在图像空间的几何 → [`../spatial-math/camera_projection_view_geometry.md`](../spatial-math/camera_projection_view_geometry.md)

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to README](./overview.md)
