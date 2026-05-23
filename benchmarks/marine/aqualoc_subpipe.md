# AQUALOC, SubPipe, and the Marine SLAM Data Desert (水下 SLAM 数据荒漠)

**Status:** v1 — opinionated draft. Sequence counts and license details marked `UNVERIFIED`.
**TL;DR:** 水下 SLAM 在海洋实验室之外能用的公开数据集大致只有三个，它们存在的原因 *正是因为没有别的*。能见度层级（清水 vs 浊水 vs ROV-管道）比算法本身更决定结果。"饱和" 在这里不适用 — 在足够多的数据集上竞争的方法数量根本不够。

---

## 1 · 数据荒漠为什么会存在

水下数据采集有四个结构性问题：

1. **成本.** 实地部署需要船只 + 船员 + ROV / AUV 飞手。一个 season 的单次数据采集就要六位数。
2. **定位 ground truth 困难.** GPS 不工作；ground truth 需要 USBL / LBL 声学定位，那本身就是一个集成工程。
3. **共享受限.** 大量海洋调查数据归油气运营商或国防承包商所有，从来不发布。
4. **泛化可疑.** 在地中海清水里跑的 SLAM benchmark，对一条单宁染色的河口几乎说明不了任何事。

结果：少数公开数据集由学界共享，每个都绑定到某个机构和 rig。

---

## 2 · 三个公开数据集 — 对照

| Dataset | Origin | Environment | Sensors | Ground truth | Size `UNVERIFIED` |
|---|---|---|---|---|---|
| **AQUALOC** | Toulon / IFREMER (France) | Harbor + archaeological site + deep sea | Mono camera + low-cost MEMS IMU + depth + (sometimes) sonar | Loop-closure based; no global ref | ~17 sequences |
| **SubPipe** | INESC TEC (Portugal) | ROV inspecting subsea pipeline | Stereo + IMU + DVL + USBL | USBL acoustic positioning | ~10 sequences |
| **Marine Robotics Dataset family** (e.g., FLSea, Tahoe, EuRoC-underwater attempts) | Various | Mixed | Mixed | Patchy | scattered |

这是 canonical 的三个；2023–2026 的多数水下 SLAM 论文都在 AQUALOC + SubPipe + 几段私有片段上评测，并把它当作 bar。

---

## 3 · 能见度层级 — 没人公开的那个轴

水下基准与陆上基准 *根本不同* 的地方在于：所谓 "the dataset" 其实是 "the dataset at this visibility tier"。一个在 AQUALOC 清水港湾段上工作的方法，在同一数据集的浊水序列上可能彻底失效。

实用的三层模型：

| Tier | Visibility | Typical attenuation | What works | What fails |
|---|---|---|---|---|
| **Clear** | >10 m visibility (Mediterranean, tropical) | Mild blue-green absorption | Standard monocular / stereo VO with color correction | Long-range texture (still attenuated) |
| **Turbid** | 1–5 m (coastal, post-storm, estuary) | Strong scattering | Short-baseline stereo + DVL fusion | Monocular VO; long-baseline stereo |
| **ROV-pipeline / dark** | &lt;1 m or active light dominated | Total ambient loss; sensor sees only what its light reaches | Active acoustic (sonar / DVL); proprioception; structured light short-range | Any passive RGB |

AQUALOC 跨 tier 1 与 2。SubPipe 是 tier 3 数据集（ROV 检查照明 + 近距贴管）。报 "AQUALOC trajectory ATE" 而不说哪条序列毫无意义 — 港湾片段和深海考古片段是不同的问题。

---

## 4 · 为什么 "饱和" 不是正确的问题

陆上 SLAM 基准（EuRoC、TUM-RGBD、KITTI）会饱和，是因为十年间几十种方法在同一数据上竞争。水下 SLAM 没有这种密度：

- 任一年内在 AQUALOC 上报结果的方法数：大概 &lt;10 `UNVERIFIED`。
- 在 SubPipe 上报结果的更少。
- 数据集 *和* 该数据集上的 SOTA 方法常出自同一实验室。

这与 "ScanNet++ 饱和了" 的陆上问题在结构上不同。水下 SLAM 处于 *exploration phase*，而非 *saturation phase*。正确的问题是 "方法跨能见度层级是否泛化？" 而不是 "是否击败 leaderboard？"

一个有用的反向测试：论文引 AQUALOC 数字但不展示至少一条浊水序列结果，等于在暗示浊水是它的塌陷点。多数论文都是如此。

---

## 5 · 对 VGGT 一类方法在水下意味着什么

衔接 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)：前馈 3D 继承的是 monocular RGB 前端能看到什么。水下的情况是：

- Tier 1 (clear): VGGT *可能* 能跑 — 但目前没有水下 VGGT 论文 `UNVERIFIED`。
- Tier 2 (turbid): 无特征的散射会击杀任何未在水下场景上训练过的 ViT 编码器。
- Tier 3 (ROV / dark): 不是问题，是不成立。

这就是为什么水下成为 VGGT-vs-VIO 一文里的反例锚点：在这个 embodiment 上，纯视觉范式根本不参赛。水下 SLAM 栈是 *acoustic first, visual auxiliary*，这一顺序在 5 年视野内不太可能翻转。

---

## 6 · 数据集创建空白即是研究机会

水下 SLAM 最大的解锁不是新架构，而是 *更多数据集*。具体来说：

- 多层能见度基准（同场景、三种水体条件）。
- AUV 集群数据集（multi-agent SLAM 水下几乎无基准）。
- 声学—相机紧耦合同步数据集，带 ground truth（多数公开集同步质量差）。
- 长时部署数据（10+ 小时 AUV 任务能暴露短片段隐藏的 drift 行为）。

对实践者：如果你有海洋 / 港湾时段的访问权，*现在发布一个好的水下数据集，比在已有三个基准上发新方法是更高杠杆的贡献*。

---

## 7 · 水下 SLAM 评测的实用默认

如果必须评一个方法，2026 的实用协议是：

1. **AQUALOC**，所有港湾 + 考古序列 — 主要 monocular / stereo 测试。
2. **SubPipe**，全集 — DVL-fusion + acoustic 测试。
3. **一段私有片段** — 注明机构、水况、ground-truth 来源。声称 "real-world" 时这是必需的。
4. **跨层级消融** — 至少分别报清水和浊水序列的表现。聚合数字会隐藏失败模式。

没有这套协议，水下 SLAM 论文会退回 "EuRoC 100%" 陷阱：光学友好的序列拉高头条，整个领域看起来比实际更接近被解决。

---

## Boundary

本文比较公开的水下 SLAM 数据集。Per-method 拆解（Aqua-SLAM、DVL 紧耦合 VIO 变体、声—相机融合方法）归 `embodiments/marine/`。Sensor physics（sonar 成像、DVL 工作原理、水下光学衰减曲线）住在 `foundations/sensor-physics/`。跨 embodiment 的 "visual-only ceiling" 框架归 `crossing/`。

Cross-link: see `embodiments/marine/` for AUV / ROV stack architecture and the "why visual is auxiliary" discussion.

## References

- AQUALOC — Ferrera et al. *IJRR 2019*. https://arxiv.org/abs/1809.07076
- SubPipe — Álvarez-Tuñón et al. *IROS 2024*. https://arxiv.org/abs/2401.17907
- FLSea — Randall et al. https://sites.google.com/view/aquaslam (UNVERIFIED, no DOI yet for full collection)
- Underwater attenuation model (Akkaynak–Treibitz) — *CVPR 2018*. https://openaccess.thecvf.com/content_cvpr_2018/papers/Akkaynak_A_Revised_Underwater_CVPR_2018_paper.pdf
- BlueROV2 reference platform (most academic ROV data uses this rig) — https://bluerobotics.com/ (no DOI)
