<!-- ontology-5axis
problem: FeedForward3D (pair-wise unconstrained 3D reconstruction)
representation: Pointmap pair (per-pixel 3D in shared frame) + relative pose + depth
sensor: 2-view RGB (uncalibrated)
paradigm: Learned-EndToEnd-Pairwise
time: FeedForward-OneShot (per pair) + per-scene global alignment
ref: ../../cheat-sheet/ontology.md §5.2
-->

# DUSt3R 解构 (DUSt3R Dissection — CVPR 2024)

> **发布时间**: 2023-12 (arXiv v1) / 2024-04 (CVPR 2024 camera-ready) / 2024-12 (arXiv v3)
> **论文 / 模型**: *DUSt3R: Geometric 3D Vision Made Easy* · [arXiv:2312.14132](https://arxiv.org/abs/2312.14132)
> **作者**: Shuzhe Wang, Vincent Leroy, Yohann Cabon, Boris Chidlovskii, Jerome Revaud
> **团队**: Naver Labs Europe
> **核心定位**: feed-forward 3D 谱系的**范式起点** —— 第一次把"无内参 + 无 pose"的 2-view 3D 重建当作端到端 pointmap 回归来解，催生整个 3R 家族（MASt3R / MUSt3R / Pow3R / VGGT / MapAnything）。

**Status:** v1.0 — opinionated dissection 2026-05-24。Architecture / loss / 数据 mix 基于论文 abstract + 公开 code；具体 benchmark 数字 (7Scenes / ScanNet / Habitat 等) 未亲自跑标 UNVERIFIED。**License = CC-BY-NC-SA 4.0**，商用全锁。
**Wedge tier:** lineage anchor (无 DUSt3R 就无后续 3R 谱系；必读历史起点)。
**TL;DR:** DUSt3R 把 2-view 3D 重建从 "calibration → matching → triangulation → BA" 四阶段 SfM 管线，**塌缩成"两张图进、对齐的 pointmap pair 出"的单次前向**。无需内参、无需 pose、无需 multi-view —— 用 CroCo SSL pretraining 让 cross-view completion 学到的 dense geometric prior 直接吐 per-pixel 3D。代价：(i) 仍 pair-wise（N 视图需 O(N²) 全局对齐步），(ii) 匹配不精确（正是 MASt3R 要补的洞），(iii) up-to-scale（非米制，必须等 MapAnything）。

### X-Ray (non-expert friendly)

(a) DUSt3R 之前，做 "我手机随手拍的 10 张照片重建一个场景" 需要 COLMAP 类 SfM 管线：先 SIFT 匹配、再 RANSAC 找 fundamental matrix、再 incremental SfM、再 BA —— 几小时离线，对纹理 / 视图角度敏感。(b) DUSt3R 让一个 transformer 直接吃两张 RGB 图，**不需告诉它任何相机参数**，输出两张 "pointmap"（每个像素一个 3D 点，在两张图共享的坐标系里）。从 pointmap 反推 depth / pose / focal 都是线性几何题。(c) 对 spatial AI 工程师：3D 重建从"几何 + 优化 pipeline"变成"一个 learned function"，能放进 deep learning 栈、能微调、能用作下游任务（如 metric depth、relocalization、SLAM 前端）的 backbone。

### 📍 Research Landscape Timeline / 研究全景时间线

```
SIFT 1999 ─► COLMAP 2016 ─► CroCo NeurIPS 2022 ─► ★ DUSt3R CVPR 2024 ─► MASt3R ECCV 2024 ─► MUSt3R/Pow3R 2025 ─► VGGT CVPR 2025 ─► MapAnything 3DV 2026
   |              |              |                   |                       |                       |                          |                        |
classical    photogrammetric  self-supervised   pair-wise FF 3D       + matching head         + scaling / multi-view     N-view single-pass        +metric (factored)
matching      SfM/MVS        cross-view pre.   范式起点 ★               (matching outlier 修)   (DUSt3R 限制 patch)          (全局 transformer)        (factored repr)
```

DUSt3R 是把"feed-forward 3D"从想法变成可用工具的**那一篇**。它**没解** metric scale、N-view 单次前向、matching precision —— 这三个洞分别被 MapAnything、VGGT、MASt3R 填上。位置 = 谱系**祖先**。

## Thesis

DUSt3R 的核心价值不在"快"，而在 **把 3D 几何重建变成一个 differentiable function**：从此 3D 不再是离线优化目标，而是可以放进任何 deep learning 栈的 *learned layer*。代价是 pair-wise 限制和 up-to-scale 输出 —— 这两个限制催生了整个后续 3R 家族。

---

## 1 · X-Ray — architecture diagram (架构图)

```
┌──────────────────────────────────────────────────────────────────────┐
│                          DUSt3R Architecture                          │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   Image 1 (RGB)         Image 2 (RGB)                                 │
│       │                      │                                        │
│       ▼                      ▼                                        │
│   ┌────────┐              ┌────────┐                                  │
│   │  ViT   │              │  ViT   │   ← Shared CroCo encoder        │
│   │encoder │              │encoder │     (SSL pretrained on cross-   │
│   └────────┘              └────────┘      view completion)            │
│       │                      │                                        │
│       │     ┌───── tokens ───┘                                        │
│       │     ▼                                                         │
│   ┌────────────────┐     ┌────────────────┐                          │
│   │ Cross-attn Dec │ ↔   │ Cross-attn Dec │   ← Two decoders         │
│   │ (view 1 frame) │     │ (view 2 frame) │     cross-attend mutually │
│   └────────────────┘     └────────────────┘                          │
│       │                          │                                    │
│       ▼                          ▼                                    │
│   ┌────────────┐           ┌────────────┐                            │
│   │ Pointmap   │           │ Pointmap   │                            │
│   │ Head + Conf│           │ Head + Conf│                            │
│   └────────────┘           └────────────┘                            │
│       │                          │                                    │
│       ▼                          ▼                                    │
│   X₁ ∈ ℝ^(H×W×3)          X₂ ∈ ℝ^(H×W×3)                            │
│   per-pixel 3D points     per-pixel 3D points                        │
│   都在 view-1 坐标系       都在 view-1 坐标系 ★                        │
│                                                                       │
│   下游线性求解（无学习）：                                              │
│   • Focal: 由 X₁ 反推（PnP-style）                                     │
│   • Relative pose T₂←₁: Procrustes(X₁, X₂)                            │
│   • Depth_i: ‖X_i‖_z (相机系)                                          │
│   • Dense matches: nearest neighbor in 3D                             │
└──────────────────────────────────────────────────────────────────────┘

N > 2 时：所有 pair 跑一遍 → O(N²) pointmap → 全局对齐优化（per-scene, ~minutes）
```

**关键设计**：两个 decoder 在 cross-attention 中彼此读 token —— 这让 view-2 的输出"知道" view-1 的几何，最终统一到 view-1 坐标系。

---

## 2 · ⚡ Eureka Moment

> **"放弃所有几何先验假设，让 transformer 直接回归共享坐标系下的 per-pixel 3D 点"** —— 不要内参、不要 pose、不要 epipolar geometry；只要两张图 + 一个学得的 cross-view 几何 prior（CroCo SSL），就能直接吐 pointmap。Depth / pose / focal 反而成了**线性下游计算**，而不是预设输入。

这把 200 年的 photogrammetric 假设（"必须先知道相机才能重建"）反过来：**先重建，再反推相机**。所有后续 3R 家族（MASt3R / VGGT / MapAnything）都继承这个 inversion。

---

## 3 · 📌 Napkin Formula (math core)

```
DUSt3R objective:

   L = Σ_v∈{1,2}  Σ_i∈valid_pixels  C_v,i · ‖ (1/z̄) · X_v,i  -  (1/z̄_gt) · X̂_v,i ‖  -  α · log(C_v,i)

   where:
     X_v,i   = predicted 3D point at pixel i of view v (in view-1 frame)
     X̂_v,i   = ground-truth 3D point
     z̄, z̄_gt = scale normalization (median depth) — 关键：归一化掉绝对尺度
     C_v,i   = predicted per-pixel confidence (>0)
     α       = regularizer keeping C from going to 0
```

**变量解释**：
- 损失是 **scale-normalized 3D regression**（per-pair），不学米制
- Confidence map 让模型自我标注"哪里 unreliable"（天空 / 透明 / 高频纹理稀疏）
- 没有显式 reprojection loss / no epipolar loss —— 全靠 dense 3D 监督打通

**直觉**：把 3D 重建当成 dense supervised regression，跟语义分割形状一样（H×W×3 而非 H×W×classes）。CroCo SSL pretraining 提供"两张图都看了哪里"的 prior，让 fine-tune 阶段不需要大量标注几何数据。

---

## 4 · Worked Example — 桌面 2 视图

场景：手机随手拍一个咖啡桌（mug + book + laptop），相机间隔 ~30°，分辨率 512×384。

| 步骤 | 操作 | 数字 |
|---|---|---|
| 1. 输入 | `2 × 3 × 512 × 384` RGB | |
| 2. CroCo encoder | ViT-Large patch16，每图 → tokens | `768 tokens × 1024 dim`（per view）UNVERIFIED |
| 3. Cross-attn decoders | 双向 cross-attention 12 层 | shared, frozen-aware |
| 4. Pointmap head | per-pixel MLP → 3 channel | output `2 × 512 × 384 × 3` |
| 5. Confidence head | per-pixel softplus → C | `2 × 512 × 384 × 1` |
| 6. Linear post-proc | focal from X₁ shape, pose from Procrustes(X₁, X₂) | ~ms |
| 7. Output | pointmap pair + relative pose + focal | up-to-scale |

**RTX 4090 延迟** ~150–250 ms `UNVERIFIED`（单 pair 前向，后处理 negligible）。

**Sanity check**：测一段桌面上已知长度的物体（book 长 24 cm），看 pointmap 投影出来的距离是否成比例 —— 是的话 shape 对，scale 是 unknown multiplier；要米制只能外锚（IMU / 双目 baseline / 已知物体）。

---

## 5 · Hidden Assumptions Table (隐含假设)

DUSt3R 在以下假设违反时会出现 silent failure：

| 假设 | 违反时的失败模式 | 工程绕法 |
|---|---|---|
| **场景静态** | 移动物体被平均进静态几何（无 motion segmentation） | 预处理 mask 动态像素，或换 DyNeRF 类方法 |
| **视图重叠 ≥ ~30%** | cross-attention 找不到对应 → 退化为 monocular depth | 滑窗 / 加中间视图 |
| **近 Lambertian 表面** | specular / 透明 / 镜面 → pointmap 噪声大 | 显式 mask 或后处理 confidence 阈值 |
| **训练分布内 FOV** | 鱼眼 / 大广角 → focal 反推错 | fine-tune on calibrated wide-angle set |
| **2-view 输入**（pair-wise 限制）| N>2 视图必须靠 O(N²) global alignment | 上 MASt3R / VGGT / MUSt3R |
| **Up-to-scale 接受** | 不接受 → metric 任务（grasp / drone control）无法直用 | 外部 scale anchor 或换 MapAnything |
| **训练分布内运动模糊** | ViT encoder 无时序去噪 → 边缘飘 | 预处理 deblur，或上 event-camera 路线 |
| **足够纹理** | 白墙 / 抛光地板 → confidence 低，输出靠 prior 编 | 投影结构光 / 主动光，或换 stereo + active |

**重复模式**：DUSt3R *训练分布内* 极好，分布外 *静默失败*。confidence head 是唯一外露的"我也不确定"信号 —— 部署时必须读它，不能只看 pointmap。

---

## 6 · Interview Tip (面试 Tip)

**Q**: "DUSt3R 与 COLMAP 的根本区别是什么？为什么 DUSt3R 出现后还有人用 COLMAP？"

**A**: 根本区别 = **DUSt3R 是 learned function（可微 / 可组合 / 前向），COLMAP 是 optimization pipeline（不可微 / 离线 / per-scene）**。但 COLMAP 不会被 DUSt3R 完全替代：(1) DUSt3R up-to-scale，COLMAP 加 SIFT 可标米；(2) DUSt3R pair-wise，N 大于 ~30 视图时 O(N²) 全局对齐 cost 反超 COLMAP；(3) COLMAP 在大型 outdoor scene（数百张 image）精度仍高于 DUSt3R 类前向方法。**当下生产 SfM 实务**：DUSt3R / MASt3R 做前端 dense 匹配，COLMAP / GTSAM 做后端 BA —— hybrid，不是替换。

**Q**: "为什么不直接训 metric DUSt3R？"

**A**: 数据问题 —— 大规模 web RGB 数据没标米制；要训 metric 必须靠 ScanNet/ARKit/Hypersim 等室内 metric-labeled dataset，但这些 dataset 的 scene diversity 远小于 in-the-wild RGB。MapAnything 后来用 **factored representation**（depth × ray × pose × scale）解了这个 —— 几何在大数据上学，scale 在小米制数据上学 → 二者解耦。

---

## 7 · GitHub-validated pitfalls (atlas 联动, 2026-05-24)

> **Scope:** 直接读 `naver/dust3r` 2025-06 → 2026-02 的 issue / PR 流。Naver 系 maintainer 已把重心转向 MASt3R / MUSt3R / Pow3R，DUSt3R repo 处于 *被自己后继工作吞并* 的 lifecycle 阶段（见 [`github_failure_atlas.md`](./github_failure_atlas.md#dust3r)）。

### 7.1 — Repo health snapshot (2026-05-24)

| 指标 | 值 |
|---|---|
| Stars | 7.1k (取自 atlas 2026-05-21 snapshot)，2026-05-24 复核 ~7.2k |
| Forks | 752 |
| Open issues | 133 |
| Open PRs | 10 |
| Issue # 增速 | 8 月仅 16 个新 issue（#227 → #243）—— 断崖式下降 |
| License | CC-BY-NC-SA 4.0（**商用全锁**）|
| Maintainer 响应度 | 🔴 大量 issue *open without maintainer response* |

### 7.2 — 已落地痛点表

| Issue | 标题 / 核心引文 | 严重度 | Workaround |
|---|---|---|---|
| [#243](https://github.com/naver/dust3r/issues/243) | "AMD MI GPUs supported" — 社区自己写 Docker + ROCm 6.4.3 配方在 MI300x 上跑通；**maintainer 无响应** | **Med-High**（CUDA 强耦合）| 社区贡献 Docker setup，但官方 README 未集成 → AMD 用户靠 fork |
| [#239](https://github.com/naver/dust3r/issues/239) | "Creating the selection_pairs.npz for ARKitScene" — 训练 pair 选择脚本缺失 | **Med**（复现 blocker）| 自己写 pair sampler 或查 MASt3R-SfM repo |
| [#237](https://github.com/naver/dust3r/issues/237) | "Cannot preprocess data scannet++ v2" — 主流学术数据集预处理脚本对不上新版 schema | **Med**（dataset 升级未跟进）| fork scannet++ v1 schema 或自己写 v2 adapter |
| [#232](https://github.com/naver/dust3r/issues/232) | "where the origin of the coordinate system of the constructed scene is?" — `cam_to_world` 第一矩阵非 identity，用户不确定 reference frame 在哪 | **Med**（文档黑洞）| 答：first view 是 canonical 坐标系但 pose 经过 normalization；文档未补 |
| [#229](https://github.com/naver/dust3r/issues/229) | "Waymo Open Dataset preprocessing" — 户外 / driving 数据接入难 | **Med**（domain gap）| outdoor unbounded depth 不在训练分布内；切窗 + 自己做 preprocessing |
| [#225](https://github.com/naver/dust3r/issues/225) | "MUSt3R and Pow3R are released" — 用户主动汇报后续工作；侧面证明 **DUSt3R 已被自家后继 paper 吞并** | Info | 新项目直接看 MUSt3R / Pow3R / VGGT |

### 7.3 — Repo health & 读者实务含义

- **维护节奏**: 8 个月仅 16 个新 issue；issue 大量 *无 maintainer 回应*。Naver 系明显把精力转移到 MASt3R 与 Pow3R / MUSt3R 等后续工作 → 把 DUSt3R 当 *已封存的 reference implementation*，**不要把生产 pipeline 绑在主分支演进上**。
- **License 二极分化**: CC-BY-NC-SA 4.0 **商用全锁**；商业项目（grasp / drone / AR 商用）走 MapAnything (Apache-like) 或 VGGT (Meta 自定义含 commercial checkpoint) 才安全。
- **§4 / §5 反馈印证**:
  1. §5 "Up-to-scale" 一条在 [#232](https://github.com/naver/dust3r/issues/232) 获普通用户印证 —— 不是只有学术 reviewer 在喊。
  2. §5 "训练分布内 FOV" 一条在 [#229](https://github.com/naver/dust3r/issues/229) (Waymo outdoor / 车载 wide FOV) 获 domain-gap 印证。
  3. §5 "训练分布内运动模糊" 在 ARKit / Waymo 类输入实战中反复浮现，但 [#239](https://github.com/naver/dust3r/issues/239) 显示**官方训练 recipe 不完整**，复现校验都难。

---

## 8 · Falsifiable Predictions (2-year)

1. **DUSt3R repo 在 2027-12 前不会再有重大架构 update**（仅 dependency bump + bugfix）—— 维护者已转向 MASt3R / MUSt3R / Pow3R；如果 main branch 出现 metric scale head 或 N-view 单次前向，该预测 falsified。
2. **生产 SfM 默认前端在 2027-06 前 transition 到 MASt3R / VGGT 类**，DUSt3R 仅作 *historical reference*；可证伪信号：COLMAP / hloc 类工具链如果在 2027-06 前仍把 DUSt3R 列为推荐前端而非 MASt3R，则预测错。
3. **Naver 不会主动把 DUSt3R / MASt3R license 改为商用友好** —— Naver 系商业策略明确（卖 SaaS / 自家服务）；如果 2027-12 前出现 Apache 2.0 重新发布，则预测错（可能性 < 10%）。

---

## 9 · For the Reader (per-persona)

- **Manipulation engineer**: DUSt3R 不要直接用于 grasp pose estimation —— up-to-scale 会让你 grasp 抓空气。先看 [`mapanything_dissection.md`](./mapanything_dissection.md) 或 FoundationStereo / Metric3D 类米制方法。
- **Aerial engineer**: DUSt3R 不能直接做飞行器导航 —— pair-wise + 离线 global alignment + un-metric + ViT 抗振动差。看 [`../../crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 的混合策略（feed-forward 3D 做地图 backbone + 经典 VIO 做控制环）。
- **Autonomous driving engineer**: outdoor unbounded depth / dynamic actors / high-speed motion 三件事 DUSt3R 都没解（[#229](https://github.com/naver/dust3r/issues/229) Waymo preprocessing 难度即证）—— 仍用 stereo + LiDAR + classical SfM，DUSt3R 仅作离线 dense 重建工具（如生成训练数据）。
- **Marine / underwater engineer**: scattering + 低对比 + 无 GPS pose 的极端环境，DUSt3R 训练分布完全没覆盖 —— **不可用**，应回到 active sonar / structured light。
- **Researcher**: 必读 paper —— feed-forward 3D 谱系的奠基。读完直接接 [`vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md)（N-view 一次前向）和 [`mapanything_dissection.md`](./mapanything_dissection.md)（解 metric），看演进逻辑。

---

## 10 · References

**Paper:**
- **DUSt3R** — Wang, Leroy, Cabon, Chidlovskii, Revaud. *CVPR 2024*. [arXiv:2312.14132](https://arxiv.org/abs/2312.14132)

**Code & Models:**
- GitHub: [naver/dust3r](https://github.com/naver/dust3r) — 7.1k★ / 752 forks / CC-BY-NC-SA 4.0 / atlas: [`github_failure_atlas.md`](./github_failure_atlas.md#dust3r)
- Hugging Face checkpoints: `naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt`

**Lineage (必读上下文):**
- **CroCo** (predecessor SSL backbone) — Weinzaepfel et al. *NeurIPS 2022*. [arXiv:2210.10716](https://arxiv.org/abs/2210.10716)
- **MASt3R** (immediate successor + matching head) — Leroy et al. *ECCV 2024*. [arXiv:2406.09756](https://arxiv.org/abs/2406.09756) · [`mast3r_dissection.md`](./mast3r_dissection.md)
- **MUSt3R / Pow3R** (Naver 自家 follow-up) — 2025
- **VGGT** (N-view 单次前向后继) — Wang et al. *CVPR 2025*. [arXiv:2503.11651](https://arxiv.org/abs/2503.11651) · [`vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md)
- **MapAnything** (metric breakthrough) — Keetha et al. *3DV 2026*. [arXiv:2509.13414](https://arxiv.org/abs/2509.13414) · [`mapanything_dissection.md`](./mapanything_dissection.md)

**Cross-handbook context:**
- Ontology: [`../../cheat-sheet/ontology.md`](../../cheat-sheet/ontology.md) §5.2 modern foundations
- Cross-zone failure atlas: [`../../cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)
- Zone overview: [`./overview.md`](./overview.md)

---

## 11 · TRL Classification

🔬 **Research-only / Lineage anchor** —— Naver pipeline 已转 attention 到 Pow3R / MUSt3R / MASt3R，DUSt3R repo 处于 *被自家后继工作吞并* 的 lifecycle 阶段；CC-BY-NC-SA license 阻止商业部署；**学术与 reference impl 仍重要**，新项目应直接走后继。

---

## 12 · Boundary (本文不覆盖)

本文 *专门* 把 DUSt3R 解构为一个 model：架构、训练目标、失败模式、生态位置。**以下不在本文范围**：

- **Per-method 后继**（MASt3R 加 matching 头 / VGGT N-view 全局前向 / MapAnything factored repr / MUSt3R scaling / Pow3R additional prior）→ 各自独立 dissection。
- **Cross-embodiment 应用对比**（"DUSt3R vs VIO？ vs 3DGS？vs LiDAR SLAM？"）→ `crossing/`，旗舰参考 [`../../crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)
- **Per-embodiment 实战落地**（manipulation pick-place pipeline / aerial mapping / autonomous driving offline reconstruction）→ `embodiments/<x>/`
- **Sensor physics**（rolling shutter / IR cut-off / 镜头畸变对 DUSt3R 的影响）→ `foundations/sensor-physics/`
- **CroCo SSL pretraining 细节**（mask ratio / loss design / 数据 mix）→ 独立 dissection 待写（候选 `croco_neurips2022_dissection.md`）

架构层面引用本文；具身体相关问题请引用 `crossing/` 或 `embodiments/`。

---

*Last opinion update: 2026-05-24. UNVERIFIED markers retire as rig-side numbers land.*

[← Back to Feed-Forward 3D](./overview.md)
