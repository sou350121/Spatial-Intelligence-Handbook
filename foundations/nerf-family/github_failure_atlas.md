# NeRF Family — GitHub Failure Atlas (生态失败图谱)

> **核心定位**：从 issues / PRs 看 NeRF 谱系四件套（原版 NeRF、Instant-NGP、Mip-NeRF 360 / multinerf、Block-NeRF via Nerfstudio）在 2026 年还**值不值得碰**、维护精力**走向何处**。
>
> ecosystem 层文档（AGENTS.md §文档类型分层）— 不强求 14 项 dissection 门槛。

**Status:** v1 — 数据快照 2026-05-21；所有未亲自跑 git 历史的 commit 频度均标 `UNVERIFIED`。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

**X-Ray.** 三条规律: (1) 原版 NeRF (bmild/nerf) 和 nerf-pytorch 都已**事实归档** — issue 集中在数据集链接失效、TF 兼容、checkpoint 损坏，是历史文物维护模式；(2) multinerf (Google) 在 **2025-02-11 官方 archived**，最后的"质量 NeRF"参考实现进入只读状态；(3) Instant-NGP 仍由 NVIDIA 主动维护（2025-07 v2.0 release），但 issue 主轴变成 Windows + cmake/gcc 编译，已经是"被 3DGS 替代后的 niche 工具"；(4) Block-NeRF **没有官方公开 repo**，社区实现走 Nerfstudio，但 Nerfstudio 默认模型列表里**没有显式的 Block-NeRF**（待维护者后续确认）。

---

## 概览矩阵 (Snapshot 2026-05-21)

| Repo | Stars | Forks | Open issues | License | Momentum |
|---|---|---|---|---|---|
| bmild/nerf (TF 原版) | 10.9k | 1.4k | 117 | MIT | ❌ stale |
| yenchenlin/nerf-pytorch | 6.0k | 1.1k | 73 | MIT | ❌ stale |
| NVlabs/instant-ngp | 17.4k | 2.1k | 491 | NVIDIA SCL-NC（非商）| ⚠️ 慢但有维护（2025-07 v2.0）|
| google-research/multinerf | 3.8k | 357 | 103 | Apache 2.0 | ❌ archived 2025-02-11 |
| nerfstudio-project/nerfstudio | 11.6k | 1.6k | 850 | Apache 2.0 | ✅ 活跃（v1.1.5 2024-11，40 releases）|

---

## NeRF Original (bmild/nerf)

- **Repo**: https://github.com/bmild/nerf
- **Stats**: 10.9k stars / 1.4k forks / 117 open issues / 4 open PRs / 48 commits / MIT
- **Top 5 failure cases**:
  1. **Spam issue** (#217) — 标题是一长串 "gtgtgt..."；说明 issue triage 完全停摆。
  2. **Update Colab Script: TF 2.x compat** (#216) — 原版用 TF 1.x，TF 2.x 升级 path 没人补。
  3. **InternalError: Blas GEMM launch failed** (#215) — 老 CUDA / TF 组合下崩。
  4. **Dataset GoogleDrive expired** (#214) — 训练数据链接失效，无人补。
  5. **Connection to dataset broken** (#213) — 同样的 data infra rot。
- **PR 方向**: 几乎无活动；4 open PRs 长尾。
- **Project momentum**: ❌ **stale** — 维护者已转向后续工作（Mildenhall → Google 系列）；spam issue 没被关闭说明无人 triage。
- **是否该选**: **不要碰** — 读 paper + 用 yenchenlin/nerf-pytorch 或 nerfstudio 的 `vanilla-nerf` 实现。本 repo 只作历史参考。

## nerf-pytorch (yenchenlin)

- **Repo**: https://github.com/yenchenlin/nerf-pytorch
- **Stats**: 6.0k stars / 1.1k forks / 73 open issues / 31 commits / MIT
- **Top 5 failure cases**:
  1. **Blender dataset not found** (#155, 2025-11) — 数据链接失效。
  2. **Pretrained tar files corrupted** (#151, 2025-03) — 官方 checkpoint 损坏。
  3. **Extract mesh model** (#150, 2025-01) — meshing 工具缺失（NeRF→mesh 一直没标准 path）。
  4. **Black and white video output** (#149, 2025-01) — 训练后输出诡异色彩。
  5. **Process killed** (#147, 2024-12) — OOM / OOM-killer 触发。
- **Project momentum**: ❌ **stale** — 维护者 Lin 转向 robotics 项目多年，本 repo 进入 reference-only 状态。
- **是否该选**: **教学 NeRF 入门 OK**（代码读起来直观），新项目用 nerfstudio。

## Instant-NGP (NVlabs/instant-ngp)

- **Repo**: https://github.com/NVlabs/instant-ngp
- **Stats**: 17.4k stars / 2.1k forks / 491 open issues / last release **v2.0 2025-07-08** / NVIDIA SCL-NC（非商）
- **Top 6 failure cases**:
  1. **cmake --build Release Error** (#1613, 2026-02) — 编译失败；典型新 CUDA / 新 compiler 组合问题。
  2. **b 参数取值** (#1609, 2025-11) — multi-resolution hash encoding 参数 doc 不清。
  3. **NV Windows** (#1607, 2025-11) — Windows 平台 issue（无标题细节）。
  4. **Warning for Windows users** (#1606, 2025-10) — Windows 用户需要文档提示。
  5. **Compilation error on gcc 14** (#1603, 2025-08) — 新 gcc 编译断。
  6. **RGB-D input** (#1600, 2025-07) — 用户求 depth 输入支持；instant-ngp 原版只 RGB。
- **PR 方向**: 主要是 NVIDIA 内部 release（v2.0 2025-07），社区 PR 少；491 open issues 反映长尾长。
- **Project momentum**: ⚠️ **慢但活** — NVIDIA 一年放一次 release，没有持续 hands-on triage（491 open issues）；但 v2.0 说明项目没死。
- **是否该选**: **极致训练速度 + 单一硬件平台（NVIDIA 桌面级）→ OK**；任何跨平台 / Windows 团队都要预算"踩编译坑"时间。非商用 license 也要注意。

## Mip-NeRF 360 (google-research/multinerf)

- **Repo**: https://github.com/google-research/multinerf（含 Mip-NeRF 360、Ref-NeRF、RawNeRF 三篇）
- **Stats**: 3.8k stars / 357 forks / 103 open issues / Apache 2.0 / **2025-02-11 archived（只读）**
- **Top 5 failure cases**:
  1. **Pinecone dataset 求链接** (#164, 2024-12) — paper 用的数据集没 distribute。
  2. **transforms.json missing workaround** (#162, 2024-08) — 新 COLMAP 输出格式不匹配。
  3. **Checkpoint path 必须 absolute** (#160, 2024-07) — JAX 路径处理 quirk。
  4. **ExistsDir 失败** (#158, 2024-04) — 目录验证报错。
  5. **`jax.core` has no attribute 'Shape'** (#156, 2024-03) — JAX 版本兼容断。
- **PR 方向**: 已 archive，无新 PR。
- **Project momentum**: ❌ **archived 2025-02-11** — Google 官方关闭维护；这是 NeRF 谱系**最后一个高质量参考实现**进入只读。
- **是否该选**: **离线质量重建仍 SOTA 之一**（README §nerf-family 里"无界场景"那一行"Mip-NeRF 360 lineage"仍成立），但**部署要预算 JAX 老版本 + 数据集对接**的工程债。新项目优先 Zip-NeRF（Barron 团队后续）+ nerfstudio。

## Block-NeRF (via Nerfstudio)

- **Repo**: 无官方公开 repo（Google / Waymo 内部）；社区实现走 Nerfstudio。
- **Nerfstudio (https://github.com/nerfstudio-project/nerfstudio)**:
  - 11.6k stars / 1.6k forks / 850 open issues / Apache 2.0 / v1.1.5 2024-11-11 / 40 releases — **活跃**
  - 但默认模型列表写的是 `nerfacto` / `vanilla-nerf`，**Block-NeRF 是否被显式实现 `UNVERIFIED`**；社区有 fork 但官方文档没明说。
- **Top failure modes** (Nerfstudio 整体): 850 open issues — 城市级 / 大规模 NeRF 是 niche use case；多数 issue 围绕 nerfacto，不是 Block-NeRF。
- **Project momentum**: Nerfstudio ✅ 活跃；Block-NeRF 本身 ⚠️ **生态层失踪** — Google 留给 Waymo 内部，公开复现是社区个人项目。
- **是否该选**: **城市级 NeRF 仍然该走 Block-NeRF 思路**（README §nerf-family 决策表"城市/多街区重建"列写明），但工程上要走 Mega-NeRF / 自实现，不是单一 repo。维护者后续应跟踪 Mega-NeRF / Switch-NeRF repo。

---

## 谱系总结 (Zone-level momentum)

**NeRF 谱系全线进入 stale / archived / niche 状态，仅 Instant-NGP 和 Nerfstudio 保持活跃 — 但已不在 spatial AI 主流量轴上**。

四条 actionable 线索：
1. **2025-02-11 是 NeRF 时代的标志日** — Google 把 multinerf archive，意味着官方层面 NeRF 研究重心已移走（向 3DGS / VGGT / world model 迁移），README §nerf-family "3DGS 赢部署不赢精度" 的判断仍成立，但**精度护城河也开始萎缩**（没有人继续优化）。
2. **教学 / baseline 用 nerf-pytorch + nerfstudio**；新生产部署用 3DGS / feed-forward 3D 谱系。
3. **Instant-NGP 是 NeRF 唯一长寿 niche** — hash-encoding 在 LiDAR / 多传感 fusion 类工作里仍被引用，但要预算 Windows / 编译坑。
4. **Block-NeRF 的"公开实现 gap"是 spatial AI 城市级重建的真实空白** — README §nerf-family 城市级一栏的推荐至今没有对应的健康 OSS 仓库；维护者应专门写一篇 *city-scale neural reconstruction* roadmap。

**Surprise 发现**: multinerf 在 2025-02 被 Google 主动 archive，比同期 3DGS 谱系的快速膨胀**早了将近一年**。这给一个**强可证伪信号**：NeRF 不是慢慢消失，而是被维护者主动判决"不值得继续投入"。对 spatial AI 写作者意味着：在 2026 后写 NeRF 章节，定位应该从"另一条活跃支线"调到"历史范式 + 数学起点"。

---

[← Back to NeRF Family](./overview.md)
