<!-- ontology-5axis
problem: Metric depth estimation
representation: Per-pixel depth map (metric)
sensor: Single RGB (+ intrinsic)
paradigm: Learned-Foundation (metric)
time: FeedForward-OneShot
ref: ../../cheat-sheet/ontology.md §7
-->

# Metric3D v1 + v2 (Metric3D 度量单目深度解构 — ICCV 2023 + 2024)

> **Published**: 2023-07 (v1, ICCV 2023) / 2024-04 (v2)
> **Paper**: Yin et al. (v1) — *Metric3D: Towards Zero-shot Metric 3D Prediction*; Hu et al. (v2) — *Metric3D v2: A Versatile Monocular Geometric Foundation Model*
> **Team**: HKUST + ANT Group + JD Explore
> **Core position**: 第一个跨任意相机输出**米**的 monocular depth 模型，通过 canonical-camera 变换 — 每个输入被几何 rectify 到固定虚拟焦距，让 depth head 学"一个相机"的度量深度.

**Status:** v1.2 — 在 v1.1 基础上追加 §8/§9/§10（working range / sensitivity / interpretability），2026-05-21. Hyperparams 标 UNVERIFIED.
**Wedge tier:** W1 · metric-depth foundation
**TL;DR:** Metric3D (Yin et al. *ICCV 2023*, arXiv 2307.10984 `UNVERIFIED ICCV vs preprint date`) 是首个能在**任意相机间输出米**的 monocular depth 模型，无需 per-camera fine-tune. 技巧是 **canonical-camera 变换** — 每张输入图像在预测前被几何 rectify 到固定虚拟焦距，因此 depth head 只需学"一个相机的度量深度". v2 (2024) 扩到 surface normal 并加更强骨干. **若你的机器人需要从单 RGB 相机得到米，这是首选模型.** 它是杀死 Depth Anything v2 grasp pose 的 relative-vs-metric 陷阱的承重答案.

### X-Ray (non-expert friendly)

(a) Monocular depth 根本上歧义（每像素 `s = f·w/Z` 有两未知）— MiDaS/Depth Anything 通过预测相对深度回避，对 "5 m 停" 无用. (b) Metric3D 把相机内参变*显式*：把每张输入 resize 到 canonical focal length `f_canon`，在 canonical frame 预测，然后 `D_real = D_canon · (f_real / f_canon)`. (c) 对空间 AI 工程师：若机器人有校准 wrist cam，这给你从单 RGB 输入得到米而无需 LiDAR — 但传错内参，输出按比例静默错.

### 📍 Research Landscape Timeline

```
ZoeDepth 2023 ─► ★ Metric3D v1 ICCV 2023 ─► Metric3D v2 2024 ─► UniDepth (intrinsics-free) CVPR 2024 ─► VGGT-class multi-view 2025 ─► fused with stereo 2026+
```

Metric3D 是 metric monocular 谱系的 canonical-camera 锚. UniDepth 移除内参需求；VGGT 把单视角吸收进多视角 feed-forward.

---

## 1 · 为什么 metric monocular 是难题

焦距 `f` 的相机看距离 `Z` 处的物体，其像平面尺寸 `s = f · w / Z`，`w` 是真实宽度. 两个未知（`Z`、`w`），一个观察（`s`）. **单图像的 monocular 深度根本上歧义** — 同图像可由近小物体或远大物体产生. MiDaS / Depth Anything 通过预测相对深度（up to affine）回避. 对可视化可，对 "5 m 停" 不可.

要从单 RGB 得到 metric 深度，你实际需要的是**把 `s` 链接到 `w` 的先验** — 在训练分布上对物体尺度的学到先验. 若你在一个相机上训和测，这工作（内参隐式编码），换相机就崩（35 mm 手机感光和鱼眼 drone cam 看同场景给不同 `s`）. Metric3D 的贡献是把内参对网络**显式化**，让跨相机迁移有原则.

---

> ⚡ **Eureka Moment**: 把相机先验变成**显式网络输入**，不是隐藏数据假设. 把每张图像 resample 到单一 canonical focal length，depth head 在训和推时只见过一个内参分布 — 杀死 MiDaS 谱系模型的 scale 歧义就此消失. 与 NeRF 中 positional encoding 同精神：把几何表面化，不要藏起来.

## 2 · canonical-camera 变换

> 📌 **Napkin Formula**: `Resize(image; f_real → f_canon) → DepthHead → D_canon → D_real = D_canon · (f_real / f_canon)`. Metric depth 对焦距缩放等变；canonical resize 利用此等变把所有相机塌缩到一个训练分布.


| Step | What happens |
|---|---|
| Input | RGB 图像 + 相机内参 `K` (fx, fy, cx, cy) |
| Canonical resize | 图像 resample 使有效焦距等于固定 canonical `f_canon` `UNVERIFIED value, typically ~1000 px` |
| Network forward | DPT-style depth head 在 canonical-camera frame 预测度量深度 |
| Inverse transform | 输出按 `f_real / f_canon` 重 scale 回真实相机 frame 的度量深度 |

```
RGB + K_real
    │
    ▼
 canonical resize ── (f_canon, K_canon)
    │
    ▼
 ViT encoder ─► DPT decoder ─► metric depth D_canon
    │
    ▼
 D_real = D_canon · (f_real / f_canon)
```

洞见是 **metric depth 对焦距缩放等变** — 焦距加倍，depth 减半（按像素隐含单位）. 把所有相机在训和推时塌缩到单一 canonical focal length，网络见到单一内参分布. **Scale 歧义消失，因为相机先验不再藏在数据里 — 是网络输入.**

这与 NeRF 中 positional encoding 或图形里 normalized device coordinates 同精神 — 把几何显式，而非依赖网络记忆.

---

## 3 · v1 vs v2

v1 (ICCV 2023) 落地 canonical-camera 贡献，用 ConvNeXt / ViT 骨干 `UNVERIFIED which is primary` 和 ~8M 训练图像跨 11 数据集 `UNVERIFIED`. v2 (2024) 扩到 ViT-Large + Giant，加 **surface-normal head** 联合 loss（帮助遮挡边界处深度质量 `UNVERIFIED magnitude`），并用更多合成扩训练混合. 架构上是直接放大；canonical-camera 技巧不变.

---

## 3.5 · Worked example — wrist cam grasp pose

Manipulator wrist cam，校准 `fx = fy = 750 px`，看 0.5 m 外的 mug.

- **Canonical** (`f_canon = 1000 px` UNVERIFIED): resize 1.33×，预测 `D_canon = 0.667 m`.
- **Inverse**: `D_real = 0.667 × 750/1000 = 0.500 m`. ✅

传错内参（实际 28 mm 时传 `fx = 1050` 当作 50 mm，使用 `750`）：
- Resize 0.952×，不同图像内容 → 不同 `D_canon`.
- 有效深度错约 1.4× — 夹爪冲过 mug. **静默失败.**

校准两次.

---

## 4 · 它在哪里重要

发它做：校准 wrist cam 的 manipulation grasp pose、桌面 bin picking、drone 慢飞障碍距离（超 30 m 预计退化）. 对 AR occlusion 杀鸡用牛刀（Depth Anything v2 更便宜）. 对水下（纹理破）和内窥镜（域偏移，需 fine-tune）失败.

**硬需求是校准内参.** 没 `K` 无 canonicalization. 适合固定相机机器人. 对"互联网图像深度"你需要 GT `K` 或学到的内参估计器 — UniDepth (Piccinelli et al. 2024 `UNVERIFIED`) 是 intrinsics-free 变体.

---

## 5 · 它在哪里 break

- **错内参 → 错 scale**. 28 mm 拍时传 50 mm 的 `K`，输出深度错约 1.8×. 静默失败模式 — 输出看着合理.
- **强透镜畸变**（鱼眼、ultrawide）— canonical resize 假设 pinhole. 先去畸变，或用 fisheye-aware 变体.
- **超过 ~30 m 的无界户外深度** — 与 Depth Anything 相同的根本问题；metric 与否，学到的 monocular depth 尾不可靠.
- **反射 / 透明表面** — 同 DPT-lineage 失败模式.
- **域偏移到医学 / 水下 / 合成** — 需 fine-tune.

### 5.x · Hidden Assumptions

上游假设，违反就产生静默 metric 错误：

- **准确内参** — canonical resize 依赖 `K`；错 `K` → 静默 scale 错.
- **Pinhole model** — 鱼眼破 canonical resize；先去畸变.
- **In-distribution 域** — 白昼为主；水下 / 医学需 fine-tune.
- **接近 Lambertian 表面** — 镜面 / 透明 → DPT-lineage 失败.
- **Depth ≤ ~30 m** — metric 尾超 30 m 不可靠，与 Depth Anything 相同 monocular 问题.
- **静态场景** — 运动下的 rolling shutter 引入几何不一致.

违反时输出仍是看着合理的 metric 深度图 — 校准错误是部署中主导静默失败模式.

### 5.y · GitHub-validated 失败模式（atlas 联动，2026-05）

YvanYin/Metric3D 仓库 push 已 >1 年（2025-03-13 最后 push），处于"PhD 毕业 → low-maintenance"典型学术 repo 状态；84 open issues 集中在 canonical-camera 假设的几何代价：

- **GitHub-validated**：**大焦距静默退化** —— `f = 1966 px`（训练分布 500–700）直接给错深度，对应 [issue #19](https://github.com/YvanYin/Metric3D/issues/19)；与 [issue #38](https://github.com/YvanYin/Metric3D/issues/38) 报告的"真值 5 m / 预测 16.5 m（~330% 偏差）"几乎对应 `(520/260)² ≈ 4` 量级，**不是模型学错，是 canonical 假设的几何代价**；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#3--metric3d--canonical-camera-假设的边界)。
- **GitHub-validated**：canonical 假设（focal ≈ 1000 px）违反时无 fallback —— 对应 [#17](https://github.com/YvanYin/Metric3D/issues/17) / [#95](https://github.com/YvanYin/Metric3D/issues/95)；维护者最高 ROI 的修复是 input focal 超训练分布时显式 warning + README in-the-wild checklist（K、ratio to canonical、resize 顺序）。
- **GitHub-validated**：自定义 KITTI-like fine-tune shape mismatch —— 对应 [#156](https://github.com/YvanYin/Metric3D/issues/156) / [#91](https://github.com/YvanYin/Metric3D/issues/91)；ONNX 动态 shape 边角 case（[#117](https://github.com/YvanYin/Metric3D/issues/117) / [#126](https://github.com/YvanYin/Metric3D/issues/126)）；老 GPU sm&lt;70 跑不通（[#81](https://github.com/YvanYin/Metric3D/issues/81)）。**部署前必做 in-house 校准 layer**。

---

## 6 · MoGe 对比（relative-track 竞争者）

[MoGe](./moge_dissection.md) (Microsoft 2024) 是 relative-track 最接近的竞争者 — affine-invariant 几何 loss + multi-task head（point + depth + normal）. 对比鲜明：

| Axis | Metric3D | MoGe |
|---|---|---|
| Output scale | metric (米) | affine-invariant |
| Needs intrinsics? | yes | no |
| Best for | 有校准 cam 的机器人 | photometric / 场景理解 |
| Multi-task head | depth + normal (v2) | point + depth + normal |
| Failure if you violate the contract | 错米 | 部署时 scale 不对齐 |

**需米：Metric3D. 不需要：MoGe 是 geometry-rich 的 relative-track 答案.**

---

## 7 · 2-year outlook + falsifiable prediction

Metric-monocular 轨是部署到机器人上的那个. 预计 intrinsics-free 变体（UniDepth 谱系）在野外图像上赢，canonical-camera 技巧成标准成分，与 stereo + IMU 融合收敛到 VGGT 谱系 feed-forward 骨干.

**Falsifiable prediction:** 2027-06 前一个主要 manipulation 产品（Figure、1X、Apptronik 或类似）将公开披露其感知栈中的 Metric3D-lineage 模型. 若都留在 RGB-D（RealSense / structured light）则预测失败.

**Interview Tip**: 被问 "怎么从单 RGB 相机得到 metric 深度"，陷阱答案是 "做不到". 正确答案：*"Metric3D 的 canonical-camera 变换 — 把内参作为网络输入显式化，利用 focal-length equivariance."* 加一句你需要校准 `K`，错 `K` 静默错.

---

## For the reader

- **Manipulation engineer** — 从这里起步，不是 Depth Anything. 校准 wrist cam 然后发.
- **Aerial engineer** — 适合慢飞检测；竞速或户外换 stereo + VIO（见 [`crossing/scale-comparison/`](../../crossing/scale-comparison/)）.
- **AD engineer** — 适合作为 metric 预训练；生产仍要 LiDAR + stereo.
- **Researcher** — canonical-camera 技巧比深度更通用. 任何 geometry-aware 都能借.

---

## 8 · Working Range 详细分析

每段距离可信度差很大. NYUv2/KITTI 数字来自 arXiv 2404.15506v2 verified.

| Range | 场景 | Verified accuracy | 状态 | 失效 |
|---|---|---|---|---|
| **近 0-1 m** | Manipulation | NYUv2 ViT-g: **AbsRel=0.067, RMS=0.260 m** | ✅ 甜区 | 镜面/透明; rolling shutter |
| **中 1-30 m** | 室内/慢户外 | KITTI ViT-g: **AbsRel=0.051, RMS=2.403 m**；**Issue #161 户外实测 2 m 实距 ViT-S 1.3 m (35% off)，ViT-L 1.5 m (25% off)** | ✅ 主战场 | In-the-wild << KITTI benchmark |
| **远 30-200 m** | AD/drone | KITTI 上界 ~80 m；**Issue #161 实测 4 m 实距 ViT-S 11.45 m (186% off)，ViT-L 20.764 m (419% off)** UNVERIFIED if representative | ⚠️ 退化 | 系统性偏差；**ViT-L 远端比 ViT-S 更差**（反直觉） |
| **超远 >200 m / sky** | 天际 | 无 verified；用户报告 sky **clipped 到固定上限** (Issue #161 paraphrase) | ❌ 失效 | Sky 是 clip hack；>100 m 必须 LiDAR/stereo |

**部署前必做**：用卷尺在你的场景测 0.5 / 2 / 10 m 偏差曲线. NYUv2/KITTI 数字**不可直接外推** — issue #161 显示 in-the-wild 与 benchmark 差一个数量级. **Manipulation**: 0-1 m 是甜区可信. **AD/drone**: >30 m 必须 LiDAR/stereo/RADAR fallback.

---

## 9 · Sensitivity 详细分析

各 sensitivity 轴失效曲线不同：

| 轴 | 退化模式 | 数字 / 来源 | 缓解 |
|---|---|---|---|
| **焦距 `f` 误差** | `D_real = D_canon·(f_real/f_canon)`，比例错则深度比例错 | 28 mm 当 50 mm → 1.8× 静默错 (§3.5) | OpenCV/Kalibr 重标定 |
| **主点 `(cx,cy)`** | 假设 pinhole；偏移引入投影误差 | UNVERIFIED — 论文未量化 | 标定时同时给 cx/cy |
| **镜头畸变（鱼眼/ultrawide）** | Canonical resize 假设 pinhole，畸变破坏 equivariance | 定性确认；定量 UNVERIFIED | 先 undistort 或用 fisheye 变体 |
| **光照（夜间/强阴影）** | ViT 共病：低 SNR 噪声大 | UNVERIFIED | 多帧融合 / HDR |
| **运动模糊** | Rolling shutter + 高速运动 → 几何不一致 | UNVERIFIED | 全局快门 / 降速 |
| **白墙/玻璃/反射** | 纹理稀疏，反射给错先验 | DPT 通病 | 主动光 / 结构光 fallback |
| **OOD（水下/医学/合成）** | 分布外，metric 崩 | 定性确认 | 域内 fine-tune |
| **输入解析度** | DPT 对 resize 敏感；canonical 已按 `f` 比例处理，但小物体仍受影响 | UNVERIFIED；issue #161 用 3024×4032 | 用 paper 推荐尺寸 |
| **训练分布偏置** | v2 训 **>16M 图**，~9488K 含深度标注（arXiv 2404.15506v2）；**outdoor normal 标注 &lt;20K，严重偏室内**（论文 limitation） | Indoor/outdoor 深度比例 UNVERIFIED | 不要用 v2 normal head 做户外 grasp |

**最大 sensitivity**：错 `f` + OOD 域（户外远距）— 吃 90% 部署失败.

---

## 10 · Interpretability

### 10.1 输出语义

- **单位**：米 — `D[u,v] = Z_metric in meters`，相机光心到像素表面点的 **z 距离**（不是 Euclidean range）
- **坐标系**：**相机-中心**（要 world frame 自己叠 `T_world_cam`）
- **每像素独立**：dense `H × W` map；无 explicit cross-pixel 3D consistency

### 10.2 Canonical 变换的精确数学（arXiv 2404.15506v2 verified）

```
CSTM_label:  D_c = ω_d · D*       where  ω_d = f_c / f
CSTM_image:  I_c = T(I, ω_r)       where  ω_r = f_c / f
De-canonical: D  = (1/ω_d) · D_c
```

`f_canon` 数值论文未明确给出（UNVERIFIED — 实现常 ~1000-1200 px）. `T(I, ω_r)` 是几何 resample（双线性/bicubic）.

**直观**：网络只见"焦距 = `f_canon` 的虚拟相机". 实测时图像 resize 让它"像虚拟相机拍的"，预测后按 `f` 比例缩回. **本质：利用 metric depth 对焦距缩放的等变性**.

### 10.3 不确定性

- **v1**: ❌ 不输出 per-pixel confidence
- **v2**: ⚠️ 论文有 "aleatoric uncertainty-aware loss" 用于 normal supervision（arXiv 2404.15506v2），但 **inference 时是否暴露 per-pixel confidence UNVERIFIED**
- **实战**：当无 confidence 模型用；自加 ensemble / TTA / 多帧一致性

### 10.4 与 DA v2 / MoGe 可解释度对比

| 维度 | Metric3D v2 | DA v2 | MoGe |
|---|---|---|---|
| 输出单位 | ✅ 米（绝对） | ❌ Affine-invariant | ❌ Affine-invariant |
| 直接驱动 grasp？ | ✅ 可（K 准、0-1 m） | ❌ 需 scale 对齐 | ❌ 除非 MoGe-2 metric |
| 内参依赖 | 必须 K | 不需 | 不需 |
| Per-pixel confidence | ❌ | ❌ | ❌ |
| 失败长相 | 看似合理的错米（静默） | 形对但无尺度 | 形对但无尺度 |

**结论**：metric 决策维度上 **Metric3D 是 monocular 谱系中可解释度最高的** — 错也只错在"scale 系数". DA v2/MoGe 的 affine 不变性导致 relative 输出无法直接接 metric controller.

### 10.5 米制精度上界（arXiv 2404.15506v2，ViT-g 骨干 verified）

- **NYUv2 (indoor)**: AbsRel=0.067, RMS=0.260 m → 室内 2 m 处典型绝对误差 ~13 cm
- **KITTI (outdoor, ≤80 m)**: AbsRel=0.051, RMS=2.403 m → 户外 20 m 处典型绝对误差 ~1 m

**底线**：indoor 0-1 m manipulation 可达 cm 级；outdoor >10 m 是米级常态. **不要从 KITTI AbsRel 0.051 推断"50 m 处误差 2.5 m"** — KITTI 上界 80 m 内的 RMS 已 2.4 m，远端 worse.

---

---

## 8.1 · GitHub Foundation Dissection (2026-05 atlas，issue 原文驗證)

> **方法**：直接讀 YvanYin/Metric3D issue 原文 + repo metadata. 數字來自仓库 about page + 個別 issue 截圖；所有引號為 issue 原文.

### 8.1.1 Repo 健康指標

| 指標 | 數值 | 解讀 |
|---|---|---|
| **Stars / Forks** | 2.2k ★ / 162 forks | 中量級學術 repo |
| **Open issues** | **80** open（之前 84，閉了少數）+ 大量 closed-without-fix | 維護斷層典型 |
| **最後活躍** | 最後 push 2025-03，最新 open issue #217（2026-02）/ #215（2025-09） | **>14 個月無新 commit** |
| **License / Python 主導** | BSD-2-Clause / 99.9% Python | 學術授權，純 Python |
| **核心開發者** | Yin（一作）PhD 畢業 | 進入 "PhD 畢業 → low-maintenance" 模式 |

**結論**：Metric3D 是**設計凍結**狀態（v2 是最後一版），不要期待 maintainer 修 issue. **任何 in-the-wild 部署都要自帶適配層**.

### 8.1.2 Pitfall Table（按出現頻率與危害排序）

| # | Pitfall | Issue 證據（原文驗證） | 危害 / 部署含義 |
|---|---|---|---|
| **P1** | **大 focal 靜默退化**（>>1000 px） | **[#19](https://github.com/YvanYin/Metric3D/issues/19)**：使用者 `K=[1966.9, 1969.5, 948.7, 498.4]` 拿到 **RMSE ~10 m**；同模型在 SHIFT 數據（`K=[640,640,640,400]`）只有 **RMSE ~7 m**. 作者**親口回覆**："在训练中，大部分数据也并不1000。比如taskonomy，大部分在500-700左右"（訓練 focal 主要落在 **500–700 px**） | **訓練分布是 500–700 px，不是論文寫的 ~1000 px canonical**. 部署 focal >1000 px 的相機（手機長焦、工業）→ 靜默深度錯 |
| **P2** | **outdoor 中遠距系統性偏差** | **[#161](https://github.com/YvanYin/Metric3D/issues/161)**：實測 outdoor，輸入 3024×4032 縮 616×1064，canonical 1000，real 3000：<br>• 真距 2 m → ViT-S **1.3 m (-35%)**, ViT-L **1.5 m (-25%)**<br>• 真距 4 m → ViT-S **11.45 m (+186%)**, ViT-L **20.76 m (+419%)**<br>• 使用者問 "is the model clipped... to account for the sky?"（未答） | **ViT-L 在遠距比 ViT-S 更差**（反直觉，可能 ViT-L overfit indoor）. KITTI AbsRel 0.051 是 benchmark cherry-pick，**in-the-wild ≥4 m 直接崩**. **AD/drone 戶外用此模型 = 高危** |
| **P3** | **canonical focal 違反無 fallback** | [#19](https://github.com/YvanYin/Metric3D/issues/19) + [#95](https://github.com/YvanYin/Metric3D/issues/95) + [#161](https://github.com/YvanYin/Metric3D/issues/161) 系列；代碼層面無顯式 warning，僅在 README 留 canonical 數字 | 部署無 in-distribution 檢查 → P1+P2 持續複現. **必須在輸入層加 `f_real / f_canon` 邊界檢查 + warning** |
| **P4** | **bfloat16 硬編碼，老 GPU 跑不通** | **[#81](https://github.com/YvanYin/Metric3D/issues/81)**：使用者引用代碼："Your model uses `torch.bfloat16` which is only supported by the newer GPUs"，建議 `dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32`. **未合併** | **sm<80 (Ampere 之前) 跑不通**. 部署到 T4/V100/老 Jetson 需自己 monkey-patch decoder |
| **P5** | **ONNX 動態 shape 邊角 case** | [#117](https://github.com/YvanYin/Metric3D/issues/117) / [#126](https://github.com/YvanYin/Metric3D/issues/126)；README 標 "ONNX support with dynamic shapes" 但實測動態尺寸有失敗模式 | TensorRT/Jetson 部署可能要固定 shape，犧牲彈性 |
| **P6** | **fine-tune KITTI-like shape mismatch** | [#156](https://github.com/YvanYin/Metric3D/issues/156) / [#91](https://github.com/YvanYin/Metric3D/issues/91)；自定義數據集 fine-tune 直接報 shape 錯 | domain fine-tune 路徑不穩；對 contrarian domain（水下 / 醫學）必須自己改數據 pipeline |
| **P7** | **v2 沒有 per-pixel confidence**（未來無 roadmap） | [#212](https://github.com/YvanYin/Metric3D/issues/212)（"Depth confidence and normals uncertainty values"，open，未答）；[#215](https://github.com/YvanYin/Metric3D/issues/215) 請求 DINOv3 backbone，未答 | 下游融合無 per-pixel 加權；只能整圖 trust/不 trust（同 §10.3 結論） |
| **P8** | **v1 vs v2 依賴衝突** | README 區分 `requirements_v1.txt` (ConvNeXt-L) vs `requirements_v2.txt` (ViT) → 兩條依賴鏈不兼容 | 混用 v1/v2 模型必須隔離環境 |

### 8.1.3 ZoeDepth / UniDepth 對比爭議現狀

倉庫內**沒有直接的 ZoeDepth / UniDepth A/B 爭議 issue**（已搜過 #1-#217）—— 對比都在論文 table 裡，社區層面僅作者宣稱 "击败 ZoeDepth"，無第三方仲裁. **空缺本身就是信號**：metric monocular 賽道沒有像 stereo 那樣的 Middlebury 公開 leaderboard，**所有 metric 數字都是論文方自報**.

### 8.1.4 v1 vs v2 遷移實務（從 issue 反推）

- **v1 (ICCV 2023)**: ConvNeXt-L 主，依賴 `requirements_v1.txt`，社區用得最久（issue 多數在此）
- **v2 (TPAMI 2024)**: ViT-Small/Large/Giant2 + normal head，依賴 `requirements_v2.txt`，**ViT-g 是論文宣稱的最強**，但 [#161](https://github.com/YvanYin/Metric3D/issues/161) 顯示 **ViT-L 在 outdoor 遠距反而比 ViT-S 更差**
- **遷移風險**: v2 不是 drop-in 替換 v1；環境、API、輸出格式都變. 已有 v1 production 的最好等 community port，不要盲遷
- **DINOv3 backbone 升級無望**（[#215](https://github.com/YvanYin/Metric3D/issues/215) 未答）—— 想要更強 backbone 自己 fork

### 8.1.5 讀者實務含義（按角色）

- **Manipulation engineer**：v2 ViT-S/L 在 **0–1 m 校準 wrist cam** 仍是最強選擇；確認你的 `f` 在 **500–700 px** 範圍（DSLR / 工業遠焦不適用）；不要相信 v2 的 confidence（沒有）.
- **Aerial / AD engineer**：**直接放棄 Metric3D 做遠距 metric**. [#161](https://github.com/YvanYin/Metric3D/issues/161) 數字 (+419% @ 4 m) 不是 outlier，是 systemic. 用 stereo + VIO，monocular 只當 fallback / 視覺檢查.
- **Researcher**：把 [#19](https://github.com/YvanYin/Metric3D/issues/19) 的 "train focal 500–700, deploy focal 1966" 當作教材 — canonical-camera 的 sim-to-real gap 不在演算法，**在訓練分布的隱性 prior**.
- **Production / SRE**：repo 凍結，不要在生產上依賴 maintainer fix；**fork + 自己加 in-distribution gate + bf16/fp32 fallback** 是基本工程.

---

## References

- Metric3D v1 — Yin et al. *ICCV 2023*. https://arxiv.org/abs/2307.10984 `UNVERIFIED venue`
- Metric3D v2 — Hu et al. 2024. https://arxiv.org/abs/2404.15506 (verified 2026-05-21；TPAMI 2024 收录，IEEE Xplore 10638254)
- Metric3D v2 项目页 — https://jugghm.github.io/Metric3Dv2/ (verified 2026-05-21)
- GitHub issue #161 (outdoor accuracy 实测报告) — https://github.com/YvanYin/Metric3D/issues/161 (verified 2026-05-21)
- Survey on Monocular Metric Depth Estimation — arXiv 2501.11841 (引 Metric3D 作 canonical-camera 代表)
- UniDepth — Piccinelli et al. *CVPR 2024*. https://arxiv.org/abs/2403.18913 `UNVERIFIED`
- ZoeDepth — Bhat et al. 2023. https://arxiv.org/abs/2302.12288
- MoGe — 见 [`moge_dissection.md`](./moge_dissection.md)

## Boundary

本文解构 Metric3D 的 canonical-camera 贡献. Relative-depth 对比在 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md) 和 [`moge_dissection.md`](./moge_dissection.md). 跨 embodiment scale 争论在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 VLA action head 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) — 注意 `scale_flag` 契约.
