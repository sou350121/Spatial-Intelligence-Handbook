# 3DGS Family — GitHub Failure Atlas (生态失败图谱)

> **核心定位**：从 issues / PRs 看 3DGS 四件套（原版 3DGS、4DGS、GS-SLAM、Mip-Splatting）在真实部署里**最常坏在哪**、社区维护精力**走向何处**。
>
> ecosystem 层文档（AGENTS.md §文档类型分层）— 不强求 14 项 dissection 门槛。

**Status:** v1 — 数据快照 2026-05-21；所有未亲自跑 git 历史的 commit 频度均标 `UNVERIFIED`。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

**X-Ray.** 三条规律: (1) 原版 3DGS 的 issue 长尾集中在 *Windows / CUDA / 安装*，是"算法成熟、工程长尾"的成熟项目特征；(2) 4DGS / GS-SLAM 这类衍生工作 issue 量看着不少（130 / 个位数），但近一年内活跃度断崖 — 典型的"paper 发完代码就半弃养"；(3) Mip-Splatting 是四件套里**最干净的**（31 open issues），但维护节奏明显放慢，issue 多为质量 / 渲染细节而非崩溃。

---

## 概览矩阵 (Snapshot 2026-05-21)

| Repo | Stars | Forks | Open issues | License | Momentum |
|---|---|---|---|---|---|
| graphdeco-inria/gaussian-splatting | 22k | 3.2k | 664 | INRIA 研究 license（非商）| 活跃（PR 节奏稳）|
| hustvl/4DGaussians | 3.6k | 359 | 130 | Apache 2.0 | 慢 |
| (GS-SLAM 主代码 repo)  | `UNVERIFIED` | — | — | — | `UNVERIFIED` |
| autonomousvision/mip-splatting | 1.4k | 114 | 31 | 有 LICENSE.md，类型 `UNVERIFIED` | 慢 |

> GS-SLAM 主仓库 `UNVERIFIED`：作者 Yan et al. 公开的 `yanchi-3dv/diff-gaussian-rasterization-for-gsslam` 只是 rasterization 子模块（249 stars / 3 open issues），主 SLAM pipeline repo 我未能在 WebFetch 上稳定定位 — 维护者后续手工补 URL。

---

## 3DGS Original (graphdeco-inria/gaussian-splatting)

- **Repo**: https://github.com/graphdeco-inria/gaussian-splatting
- **Stats**: 22k stars / 3.2k forks / 664 open issues / 45 open PRs / 250 commits on main / License: INRIA research license（非商）
- **Top 5 failure cases**:
  1. **Submodule 拉不下 simple-knn** (#1328) — `submodules-simple-knn @ 86710c2` 打不开；submodule 编译 / pinning 长尾。
  2. **Install failure on Windows 11** (#1322) — Windows CUDA 兼容性反复出现的入门坑；非 Linux 用户的统一痛点。
  3. **RTX 50-series 稳定训练** (#1313) — 新 GPU + CUDA 12.8 路径上未稳；用户在新硬件上踩坑。
  4. **Training Stuck at 0%** (#1310) — 初始化阶段 hang；与 dataset 路径 / dependency 解析有关。
  5. **Gaussian model resolution issue** (#1321) — 输出分辨率配置不直观。
  6. **SIBR viewer 看不到内网** (#1314) — viewer 网络层 bug；不是核心算法但部署常撞。
- **PR 方向** (近 6 月):
  - **平台扩展**: HIP/AMDGPU 移植、CUDA 12 兼容、conda setup 增强。
  - **bug fix**: visibility filter indexing、RGBA 训练、conversion utility exit code。
  - **perf**: SSIM 复杂度降低、GPU 几何工具、内存分配优化。
  - **feature**: UV mapping、eval dir 指定、RGBA 背景 composite。
- **Project momentum**: ✅ **活跃** — 45 open PRs + 64 closed，issue # 涨到 #1329（2026-05），跨平台移植 PR 节奏稳；典型的"祖师爷 repo + 大社区维护"模式。
- **是否该选**: **学术 baseline 首选**；商用要谈 INRIA license。Windows 用户**做好踩坑预期**（#1322 #1313 都说明这点），推荐 WSL2 / Linux 路径。

## 4DGS — Wu et al. CVPR 2024 (hustvl/4DGaussians)

- **Repo**: https://github.com/hustvl/4DGaussians
- **Stats**: 3.6k stars / 359 forks / 130 open issues / 4 open PRs / 68 commits / Apache 2.0
- **Top 5 failure cases**:
  1. **Data** (#273, 2026-05) — 空标题，但反映用户在数据准备阶段卡住的高频模式。
  2. **Visualization** (#271 / #270, 2026-01) — 渲染 / viewer 路径反复出问题。
  3. **渲染效果不理想，怎么调** (#269, 2026-01) — 训练后 quality 调参不直观。
  4. **Web-based Viewer 请求** (#266, 2025-12) — viewer 生态缺失，社区在等。
  5. CUDA / 脚本失败（#258-#263 老 issue） — 环境兼容长尾。
- **PR 方向** (近 6 月): 4 open PRs 长期不动；最后一次大规模代码 cleanup 显示在 "2024.6.25"。
- **Project momentum**: ⚠️ **慢** — 2024-06 后看不到大动作；130 open issues 但新 issue 很多空标题（社区 "Q & A 风格" 而非 "bug report 风格"），暗示项目处于 *半弃养* 状态。
- **是否该选**: **paper 复现 OK**；想做 dynamic-scene 生产部署应找更新的 fork 或 Deformable-3DGS 系列。Manipulation demo 数据集复现这里仍能跑。

## GS-SLAM — Yan et al. CVPR 2024

- **Repo**: 主 SLAM pipeline `UNVERIFIED` — 已确认的只有 rasterization 子模块 `yanchi-3dv/diff-gaussian-rasterization-for-gsslam`（249 stars / 22 forks / 3 open issues / CVPR 2024 highlight）。
- **Top failure cases**（仅子模块）:
  1. **Missing requirement file** (#7, 2025-04) — 依赖文档不全。
  2. **Can I ask for a demo?** (#6, 2024-12) — 没 demo / runnable example。
  3. **Running Live with RGB-D Camera** (#5, 2024-12) — 实时 RGB-D 真机部署问题，没工作示例。
- **PR 方向**: 几乎无活动。
- **Project momentum**: ❌ **stale**（仅子模块视角）— 主 pipeline 仓库未公开 / 未找到。
- **是否该选**: **不推荐生产** — 走更新的 GS-SLAM 后继（SplaTAM、Gaussian-SLAM、Photo-SLAM）。本 repo 仅作 paper 算法对照阅读。⚠️ 维护者后续要找官方主 SLAM repo 链接。

## Mip-Splatting (autonomousvision/mip-splatting)

- **Repo**: https://github.com/autonomousvision/mip-splatting
- **Stats**: 1.4k stars / 114 forks / 31 open issues / 16 commits / LICENSE.md 存在但类型 `UNVERIFIED`
- **Top 5 failure cases**:
  1. **NeRF Google Drive 数据失效** (#78) — 训练数据外部链接断；data infra 长尾。
  2. **Wrong result in supersplat** (#75) — 与下游 supersplat viewer 集成结果错。
  3. **Website Models seem blurry** (#74) — 官方 demo 渲染质量被质疑；视感 quality vs benchmark 数字的 gap。
  4. **Gaussian ball size & ratio to pixel** (#73) — 抗锯齿核心参数 doc 不清。
  5. **About render when training** (#72) — 训练时渲染路径疑问。
- **PR 方向**: 少量 — 集成 Gaussian Opacity Fields 的 densification metric；非高频。
- **Project momentum**: ⚠️ **慢但稳** — 31 open issues 都是细节问题而非崩溃，说明算法成熟；但 commit 节奏明显放慢。
- **是否该选**: **Drone / AR 多尺度场景的默认 3DGS 变体**（README §3DGS-family 已经这么定调）；issue 都是"调参 / 数据"层级，无致命崩溃。代码可作 reference 实现。

---

## 谱系总结 (Zone-level momentum)

**3DGS 谱系 momentum 集中在 graphdeco-inria 原版，衍生分支（4DGS / GS-SLAM）半弃养、Mip-Splatting 算法成熟节奏放慢**。

四条 actionable 线索：
1. **原版 3DGS 还在长大** — 22k stars + 45 open PRs + 跨平台移植（HIP/AMD）正在发生，这是整个 3DGS 生态的"基础设施仓库"。
2. **衍生分支寿命 ≈ 18 个月** — 4DGS / GS-SLAM 都符合"paper 发布后 12-18 个月活跃，之后断崖"的模式；研究者要复现 paper 没问题，要部署务必找继任者。
3. **Windows 是真实痛点** — #1322 #1313 等 issue 反复说明这一点；非 Linux 团队推荐先评估 WSL2 / Docker 路径。
4. **GS-SLAM 主仓库 `UNVERIFIED`** — 这是本 atlas 最大的开放问题；后续要找作者 Yan et al. 的官方主 pipeline repo（不是 rasterization 子模块）。

**Surprise 发现**: graphdeco-inria 原版的 PR 列表里有 **HIP/AMDGPU 移植**，意味着 3DGS 生态正在"破除 NVIDIA 绑定"；这对 spatial AI 部署（特别是 marine / aerial 这种功耗敏感场景）是个**未被注意的工程信号** — 远比"又一篇 4DGS 论文"重要。

---

[← Back to 3DGS Family](./overview.md)
