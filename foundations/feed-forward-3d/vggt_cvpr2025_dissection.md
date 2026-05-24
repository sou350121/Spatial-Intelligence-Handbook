<!-- ontology-5axis
problem: FeedForward3D (pose + depth + points + tracks)
representation: Dense pointmap + depth + pose + tracks
sensor: Multi-view RGB
paradigm: Learned-EndToEnd-MultiTask
time: FeedForward-OneShot (batch)
ref: ../../cheat-sheet/ontology.md §7
-->

# VGGT (CVPR 2025) Dissection (VGGT 解构 — CVPR 2025 best paper)

> **发布时间**: 2025-03 (arXiv) / CVPR 2025
> **论文 / 模型**: VGGT — Wang et al.
> **团队**: Meta + Oxford VGG
> **核心定位**: 一次 transformer 前向完成 N 视图 3D 重建 —— 将 MVS + pose + depth + tracking 合并为单一学得函数。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Hyperparam claims marked UNVERIFIED need rig-side validation.
**Wedge tier:** W1 (one of 5 launch docs)
**TL;DR:** VGGT 以单次前向同时输出 pose、depth、point maps 与 tracks，替代 per-scene 优化。它并非对 DUSt3R 的提速，而是一次*范式跨越*——将 3D 从离线拟合（NeRF、3DGS、COLMAP）拽进 foundation-model 范式：3D 成为推理输出。

### X-Ray (non-expert friendly)

(a) VGGT 之前，multi-view 3D 需要 pair-wise 前向（DUSt3R）再叠一个独立的全局对齐步。(b) VGGT 让 N 张视图在一个共享 transformer trunk 内一次完成 —— 同时输出 pose、depth、point map、tracks。(c) 对空间 AI 工程师：3D 从离线拟合步骤变为*可组合层*（梯度可流、特征可复用）。

### 📍 Research Landscape Timeline

```
NeRF 2020 ─► COLMAP+3DGS 2023 ─► DUSt3R 2024 ─► MASt3R 2024 ─► ★ VGGT CVPR 2025 ─► π³ streaming 2025+ ─► ?
```

VGGT 是首个在单次前向内合并 N-view 几何 + pose + depth + tracking 的工作。下游开放问题：streaming、metric scale、edge 部署。

## Thesis

VGGT 将 multi-view stereo、dense 重建与 pose 估计合并到一个 transformer —— 价值不在速度，而在*3D 从此与深度学习栈可组合*（梯度可穿过、特征可复用下游、无 per-scene state）。

---

## 1 · Setup — what VGGT is being measured against

到 2024 年底，三条血统各自占据问题的一块：

- **COLMAP + 3DGS / NeRF** (Kerbl et al. *SIGGRAPH 2023*, [arXiv:2308.04079](https://arxiv.org/abs/2308.04079)) —— per-scene 优化。拟合按小时，无迁移。
- **DUSt3R / MASt3R** (Naver Labs Europe 2024, [arXiv:2312.14132](https://arxiv.org/abs/2312.14132), [arXiv:2406.09756](https://arxiv.org/abs/2406.09756)) —— 前向，但**pair-wise**。Multi-view 需独立的全局对齐步。
- **Depth Anything v2** (Yang et al. 2024, [arXiv:2406.09414](https://arxiv.org/abs/2406.09414)) —— 前向 monocular depth。无几何、无 pose、无 multi-view 一致性。

领域里有 monocular 分支、pair 分支与 per-scene multi-view 分支。没有任何一种同时做到前向 *且* multi-view *且* geometry-aware。

VGGT (Wang et al., CVPR 2025, Meta + Oxford, [arXiv:2503.11651](https://arxiv.org/abs/2503.11651)) 在单一架构内合并了这些。**DUSt3R 只能做 pair，VGGT 做 N —— 不是定量提升，是范式跨越。** Pair + 全局对齐是两阶段系统；N-view 单次前向是单一学得函数。下游后果——与策略网络可组合、梯度可流、可批推理——只有在后一范式下才存在。

> ⚠️ **Contested claim (ontology §13.1)** — "Paradigm shift" is the dissection's framing, **not academic consensus**:
> - **Wu et al. (2025) Geo-Spatial Information Science (peer-reviewed)**: "transformer-based methods cannot fully replace traditional SfM and MVS, but offer promise as complementary approaches" (arXiv 2507.14798)
> - **arXiv 2512.21691 (2026)**: VGGT global self-attention **collapses to rank-1** as input length grows — 新失敗模式 with no classical SfM analogue
> - **FastVGGT (arXiv 2509.02560)**: quadratic memory exhausts GPU within hundreds of frames
> - **Wu 2025 also documents**: VGGT capped at 518 px input, holes around buildings, fails top-down on tall structures
>
> **Handbook's actual position** (ontology §13.1, §5.4): VGGT is an important **paradigm signal**, not "shift". Actual 2025-2026 deployment walks **3R-SLAM Hybrid** (SLAM3R / Flash-Mono / EC3R-SLAM) — learned 3D backbone + classical SLAM back-end. Pure VGGT is research-only (🔬 TRL); 0 shipped robots use it.

---

## 2 · Architecture walk — four heads, one trunk

> 📌 **Napkin Formula**: `3D ≈ Transformer(N RGB views) → {poses, depths, points, tracks}` —— 四个输出来自单次前向，而非四个级联系统。

一个 ViT 风格 transformer 把 N 个 RGB view 当成一段 token 序列吃进去。Cross-view attention **不被 factorize** —— 每个 patch 跨所有视图与所有其它 patch attend。这使 N-view 推理在单次前向中可行，并限制实用的 N（memory 随 N² 增）。甜点：N=2 到约 30 帧 UNVERIFIED。

四个 head 共享 trunk：

1. **Camera pose** —— per-view extrinsics + intrinsics。替代 COLMAP。
2. **Depth** —— per-view dense depth。替代 MVS / Depth Anything。
3. **Point map** —— per-view 3D points 在共享世界坐标系下。DUSt3R 遗产。
4. **Tracking** —— 跨视图 2D 点轨迹。替代 CoTracker。

不显眼的选择：四个 head 共享 trunk *且联合训练*。**四个 head 互相 regularize。** Depth 无 pose 时 metric 不定；pose 无 depth 时欠约束；point map 无 tracks 时无时序连贯。联合训练正是 depth head 在相同 backbone 尺寸下能胜过 Depth Anything v2 的原因 UNVERIFIED。

> ⚡ **Eureka Moment**: 四个 head（pose / depth / pointmap / tracking）的联合训练相互 regularize —— depth 无 pose 时 metric 不定，pose 无 depth 时欠约束。**约束栈本身就是架构**；trunk 只是让约束彼此耦合的基底。

形状校验：N RGB views → N depth maps + N camera params + 全局对齐的 point cloud + 2D tracks。一次前向。无优化循环。无 scene state。

---

## 2.5 · Worked example — N=4 desktop views

桌面（mug、laptop、keyboard）四张 518×518 RGB，相机间隔约 30°，手持手机。

- **输入**：`4 × 3 × 518 × 518` RGB
- **Tokens**：14×14 patches → `4 × 1369 ≈ 5476` patch tokens（+ camera / register token UNVERIFIED）
- **Attention**：跨视图 all-to-all —— N-view 融合发生在这里
- **输出**：4 个 pose（R, t, intrinsics；首视为世界系）+ 4 张 dense depth map + 共享世界系下 per-view pointmap `4 × 518 × 518 × 3` + K 条可选 2D track 轨迹

A100 上延迟 ~150–250 ms UNVERIFIED。一次 `model(images)` 调用——点云立即可被下游消费。合理性检验：测一段已知长度物体与参考边的比，比例不对 = scale ambiguity 咬到你了（monocular up-to-scale）。

---

## 3 · Training data — the unglamorous half

论文里讨论最少、但决定模型能否泛化到你的 rig 的部分。Mix UNVERIFIED：

- 合成 3D（MegaSynth 类、Hypersim、BlendedMVS）—— 干净的几何真值。
- 多视图真实 + SfM 伪标签（ScanNet、ARKitScenes、Co3D、MegaDepth）—— 照相级。
- DINOv2 风格 backbone 预训练 —— 特征质量。

合成与真实的比例决定失败模式。合成偏多在 Hypersim 类室内场景上几何紧；在户外 unbounded depth、运动模糊、非 Lambertian 表面上崩。这不是 VGGT 专属——DUSt3R 以来每个前向 3D 模型都这样失败——但此处的表现（窄基线室内胜过宽基线户外 UNVERIFIED）是任何要部署在桌面之外的人最需要记的事实。

---

## 4 · Where it breaks (deployment-ordered)

1. **Unbounded outdoor depth** —— 天空、远处建筑、超过约 30 m 的任何东西。depth head 没在这些分布上训过，会编。这是 VGGT 不能直接拿去做 drone 户外的最大原因——见 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`。
2. **纹理稀疏场景** —— 白墙、抛光地板、雾。对应无处可锁；point map head 发出貌似合理但不可靠的几何。
3. **运动模糊、卷帘** —— ViT encoder 无时序模型；高速采集 aliasing。
4. **动态物体** —— 假定场景静态，静默把动态几何平均进静态估计。
5. **Metric scale** —— monocular up-to-scale。要米制需外部 scale（stereo、IMU、已知尺寸物体）。
6. **大 N** —— 单 GPU 大约 30 帧封顶 UNVERIFIED；更长视频需流式变体（π³ 血统）。

重复模式：VGGT 在训练分布内极好，分布外*静默*失败。无置信 head 标 OOD depth —— 这让朴素部署危险。

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

社区在 facebookresearch/vggt issue 上反复压测同一组边界，与上面六条几乎一一对应：

- **GitHub-validated**：demo_colmap 触发 OOM，与 resize 维度耦合 —— 对应 [issue #470](https://github.com/facebookresearch/vggt/issues/470)，部署侧建议绕开该 path 自己写 inference loop + 控制 N；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#vggt-v1)。
- **GitHub-validated**：depth scale ambiguity 用户反复问"是 metric 还是 relative" —— 对应 [issue #471](https://github.com/facebookresearch/vggt/issues/471)，即 §4 #5 monocular up-to-scale 限制；文档仍需补。
- **GitHub-validated**：长视频超过 batch 上限请求 factor-graph stitching —— 对应 [issue #474](https://github.com/facebookresearch/vggt/issues/474)，印证 §4 #6 "大 N" 边界被普遍撞到，详见 [`github_failure_atlas.md`](./github_failure_atlas.md#vggt-v1)。

### 4.x · Hidden Assumptions

上游假设被违反时会产生上述失败：

- **静态场景** —— 移动物体被平均进静态几何；无运动模型。
- **足够视图重叠** —— 需 ≥30% 共享内容 UNVERIFIED；否则塌为 per-view monocular depth。
- **Monocular up-to-scale** —— 无 metric scale；需外锚（stereo / IMU / 已知物体）。
- **近 Lambertian 表面** —— specular / 透明 / 镜面破坏对应。
- **分布内运动模糊** —— ViT encoder 无时序去噪。
- **每次前向 ≤30 视图** UNVERIFIED —— O(N²) attention；更长需流式。
- **相机内参隐式可学** —— 手机 / 网络摄像头 FOV 可，鱼眼 / 大广角退化。

若违反，输出可能仍看上去干净——静默失败才是危险模式。

---

## 5 · Deployment notes (Jetson-class targets)

参考 checkpoint 对 edge 太大。锚定数 UNVERIFIED：

| Target | Rate | GPU mem |
|---|---|---|
| A100 / H100 | 5–15 Hz N=8 | 16–24 GB |
| RTX 4090 | 3–8 Hz N=8 | ~16 GB |
| Orin (FP16) | ~5 Hz N=4 | ~6 GB |
| Orin distilled | ~10 Hz N=4 | ~3 GB |

Jetson 数字取决于 token reduction（drop patch、缩小 N、FP16 attention）。结论：VGGT 是*工作站*模型，可蒸馏到 edge；不是原生 edge。

Batch-2 技巧：每秒在 N 帧滑窗上跑一次 VGGT，缓存全局 point map，让更快前端（CNN depth net、经典 VIO）做插值。这让 VGGT 参与实时闭环，但不主导。

---

## 6 · Cross-embodiment implications (pointers, not analysis)

跨具身体故事住在 `crossing/`：

- **Aerial** —— `crossing/slam-vio-migration/vggt_vs_drone_vio.md`。对任何有正经控制环的飞行器而言，*无替代、只能混合*。
- **3DGS displacement** —— `crossing/representation-migration/`。VGGT 的 point map 不是 Gaussian splat；前向 point map 是否能替代 per-scene 3DGS 用于仿真、sim-to-real 与编辑，是另一个未解争论。
- **特征到策略的传递** —— `bridge-to-vla/feature-cloud-to-action.md`。对 VLA 策略而言，问题是 VGGT 的中间特征是否比其显式点云更有用——多半是的，这会改写集成故事。

阅读习惯：看到"VGGT 替代 X"时，问*在哪种具身体上*。答案几乎总是"桌面 manipulation，带 caveat"，几乎从来不是"aerial 户外"。

---

## 7 · GitHub-validated pitfalls (2026-05-24 deep dive)

> **Scope:** 直接读 `facebookresearch/vggt` 2026-02 → 2026-05 的 issue / PR 流，用以校验前面 §4 / §4.x 的失败模式清单。不替换 §H1 的 Wu 2025 学术争议；这里是工程一侧的 *社区可见* 痛点。
> **Repo health (2026-05-24):** ~13.2k★, **246 open issues**, **24 open PRs / 31 closed**。issue 流稳定有新输入（最新 #476 落在 2026-05-14），属于活跃但**未走向成熟封装**的状态——大量"我撞到边界"型 issue 长期 *open without maintainer response*，对外部用户即"自己读源码，自己绕"。

### 7.1 — 已落地痛点表

| Issue | 标题 / 核心引文 | 严重度 | Workaround |
|---|---|---|---|
| [#470](https://github.com/facebookresearch/vggt/issues/470) | "images are directly resized to [518, 518], which is why demo_colmap runs out of memory" — `fee0103` | **High** (OOM blocker) | 不走 `demo_colmap` 内的方块 resize，改调 `load_and_preprocess_images`（保 aspect ratio，约 `[294, 518]`，显存 ~½）。 |
| [#474](https://github.com/facebookresearch/vggt/issues/474) | "Long video support: factor graph stitching pipeline... chunks VGGT into memory-sized batches and stitches them with a GTSAM factor graph for global consistency" — `jashshah999`，自报 **70.3% average ATE reduction** vs naive stitching | **High**（长视频根本性限制）| 社区贡献的 GTSAM + Sim(3) + DINOv2 loop closure 外挂；官方未集成。 |
| [#471](https://github.com/facebookresearch/vggt/issues/471) | "DA3 has models that produce real world metric depth maps. Are VGGT depth maps metric and linear as well, or just relative?" — `sourcesync` | **Med-High**（文档黑洞）| 答：up-to-scale。每个手册读者都需要被告知，文档至今未补。 |
| [#472](https://github.com/facebookresearch/vggt/issues/472) | "aerial images of the sequence would be split into two independent pose estimates" — `xiazhenyu555` | **Med**（航拍场景分裂）| 重叠不足时 cross-view attention 退化；切窗 / 提高重叠率 / 用外部 pose 初始化。 |
| [#476](https://github.com/facebookresearch/vggt/issues/476) | "the paper mentions that 64 A100s were used, with [2,24] frames sampled per sequence" —— 训练 batch / loss 收敛 / dataset 采样三连问无人回 — `stephanie-fu` | **Med**（复现 blocker）| 无官方 training script；复现 paper 数字目前不可行。 |
| [#424](https://github.com/facebookresearch/vggt/issues/424) | 210 张 spherical 拍摄，全跑 vs 分半跑 → 分半"下半部分明显更好" — `XXX` | **Med**（误差累积非随机）| 多视图大 N 下并非"越多越好"，分窗 + 后端拼接更稳。 |
| [#417](https://github.com/facebookresearch/vggt/issues/417) | "whether the scaling applied to the normalised space... is consistent across both the camera pose's height and the translation transformation" — `Shexiaox` | **Med**（标准化空间到米制的语义不清）| 单标量 rescale 不够；需要额外 metric anchor，参考 MapAnything factored repr。 |
| [#455](https://github.com/facebookresearch/vggt/issues/455) | "the big-part of cuda memory use is in Aggregator... Only 4 layers of output_list are processed" (indices 4/11/17/23) — `XiShuFan` | **Med**（显存优化）| 自己改 `aggregator.py:253`，丢弃 unused intermediate tensors。 |
| [#106](https://github.com/facebookresearch/vggt/issues/106) | "I am wondering if it is possible to run this on a very large dataset of hundreds to thousands of images?" — 2025-04 提出，**至今未回** | **Low-info**（长尾问询）| 与 #474 同根；无原生大数据集 path。 |

### 7.2 — PR 信号（看走向，看遗留债）

| PR | 标题 | 状态 | 含义 |
|---|---|---|---|
| [#445](https://github.com/facebookresearch/vggt/pull/445) | Parallel **multi-GPU** inference for `demo_colmap.py` | open（2025-12 起）| 真有人撞到大场景，自己做了 multi-GPU；官方未合 → 显存边界靠社区。 |
| [#462](https://github.com/facebookresearch/vggt/pull/462) | Bump **torch 2.3.1 → 2.8.0** | open | 依赖 2 个版本落后；可能拖住 H100 / Blackwell 用户。 |
| [#434](https://github.com/facebookresearch/vggt/pull/434) | Improved **RGBA / alpha channel** handling | open（2025-11 起）| 透明背景图像（合成 / matte）尚不被原生支持。 |
| [#350](https://github.com/facebookresearch/vggt/pull/350) | **EXIF transpose** on image load | open（2025-08 起）| 手机竖拍照片不被自动校正方向 → pose 估计可能整体偏 90°。**手机用户立刻撞到的隐坑。** |
| [#251](https://github.com/facebookresearch/vggt/pull/251) | Accelerate model loading on GPU by 1.24× | open（2025-07 起）| 半年没合，PR review 节奏慢。 |
| [#427](https://github.com/facebookresearch/vggt/pull/427) | Data augmentation | open | 训练 pipeline 仍未公开。 |

### 7.3 — Repo health & 读者实务含义

- **维护节奏**: 6 个月内最早的 PR（#251, #350）至今 open；issue 大量 *无 maintainer 回应*。结论：**VGGT 1.0 已发布即冻结**，演进重心已转向 VGGT-Ω / MapAnything 等后继。把 VGGT v1 当 *已封存的 reference impl*。
- **1B-Commercial checkpoint**: GitHub 上对"1B-Commercial 商用 checkpoint 使用 gotcha"几乎无 issue ([#298](https://github.com/facebookresearch/vggt/issues/298) 仅问 500M/200M 变体)；License 与商用走源码 + LICENSE 文件确认，社区并未把它压出明显坑——但**也意味着商用部署者还没大规模上线**。
- **硬件特异性**: torch 落后 + multi-GPU 走社区 PR + EXIF / RGBA / Aggregator 显存优化均依赖 fork → **生产部署强烈建议 fork lock**，不要追主分支。
- **对手册 §4 / §4.x 的反馈**:
  1. §4 #5 "Metric scale" 一条得到 [#471](https://github.com/facebookresearch/vggt/issues/471) / [#417](https://github.com/facebookresearch/vggt/issues/417) 双重外部印证 —— 不是只有学术 reviewer 在喊，连普通用户也撞到。
  2. §4 #6 "大 N" 边界获 [#474](https://github.com/facebookresearch/vggt/issues/474) / [#106](https://github.com/facebookresearch/vggt/issues/106) / [#424](https://github.com/facebookresearch/vggt/issues/424) 三处压力测试印证，且**误差不只是溢出而是非单调累积**（#424 分半反而更准）。
  3. §4.x "demo_colmap OOM" 由 [#470](https://github.com/facebookresearch/vggt/issues/470) 定位到**具体一行代码**（方块 resize）—— 这是 demo 工程债务，不是模型本身瓶颈。
  4. **新增 §4 候选条目**: EXIF 方向未校正（[PR #350](https://github.com/facebookresearch/vggt/pull/350)）—— 手机相册输入的 *silent failure mode*，建议加入 §4.x 条目下次回填。

---

## 8 · Comparison + Interview Tip

| System | Inputs | Outputs | Multi-view | Per-scene fit |
|---|---|---|---|---|
| **VGGT** | N RGB | pose + depth + points + tracks | **N-view, one pass** | no |
| **DUSt3R** | 2 RGB | aligned pointmap | pair + alignment step | no |
| **MASt3R** | 2 RGB | DUSt3R + matching | same as DUSt3R | no |
| **Depth Anything v2** | 1 RGB | relative depth | no | no |
| **COLMAP + 3DGS** | many RGB | poses + dense splats | yes | **yes (hours)** |

**Interview Tip**：恰好两视、最小模型 → DUSt3R；N>2 或想一次拿到 pose / depth / tracks 而不粘合系统 → VGGT。"为什么不用 COLMAP？"—— 梯度穿不过它，且推理离线。

---

## References

- VGGT — Wang et al. *CVPR 2025*. [arXiv:2503.11651](https://arxiv.org/abs/2503.11651)
- DUSt3R — *CVPR 2024*, Naver Labs Europe. [arXiv:2312.14132](https://arxiv.org/abs/2312.14132)
- MASt3R — Leroy et al. *ECCV 2024*. [arXiv:2406.09756](https://arxiv.org/abs/2406.09756)
- Depth Anything v2 — Yang et al. 2024. [arXiv:2406.09414](https://arxiv.org/abs/2406.09414)
- 3D Gaussian Splatting — Kerbl et al. *SIGGRAPH 2023*. [arXiv:2308.04079](https://arxiv.org/abs/2308.04079)
- COLMAP — Schönberger & Frahm *CVPR 2016*. [arXiv link TBD]
- π³ streaming variant — [arXiv link TBD]

---

## Boundary

本文*专门*把 VGGT 解构为一个模型：架构、训练、失败模式、部署。跨具身体对比（替代 VIO？取代 3DGS？桥到 VLA？）住 `crossing/`。架构层面引用此处；具身体重要时引用 `crossing/` 处。

---

*Last opinion update: 2026-05-21. UNVERIFIED markers retire as rig-side numbers land.*
