<!-- ontology-5axis
problem: Novel-view synthesis / Reconstruction
representation: N×Gaussian primitives (μ, Σ, SH, α)
sensor: RGB + poses (from COLMAP)
paradigm: Hybrid-DiffRender (Gaussian rasterize + GD)
time: PerScene-Optimization
ref: ../../cheat-sheet/ontology.md §7
-->

# 3D Gaussian Splatting (3DGS 原始论文解构 — SIGGRAPH 2023)

> **Published**: 2023-07 (SIGGRAPH 2023)
> **Paper**: Kerbl, Kopanas, Leimkühler, Drettakis — *3D Gaussian Splatting for Real-Time Radiance Field Rendering*
> **Team**: INRIA + Université Côte d'Azur + MPI Informatik
> **Core position**: 首个显式、GPU-rasterizable 的 radiance-field 表示 — 用 ~1–5M 个 anisotropic gaussians 替换 NeRF 的 MLP，使 3D 变得可检查、可编辑、且快 100×。

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**TL;DR:** 3DGS 不是一个渲染技巧 — 它是 radiance field 终于变成*显式*几何表示、机器人栈可以真正拥有的时刻。比 NeRF 的 100× 加速是真实可复现的；1–2 GB-per-scene 的存储成本则是没人提醒过你的部署地雷。

### X-Ray (non-expert friendly)

(a) NeRF 给了你一个可微分 3D 场景，但需要数小时训练、渲染 &lt;1 FPS — 在 30 Hz 感知环路内毫无用处。(b) 3DGS 保留可微分契约（梯度从像素回流），但把 MLP 丢掉，换成数百万个显式 anisotropic ellipsoid，由 CUDA rasterizer 实时 splat。(c) 对空间 AI 工程师：3D 场景变成*可检查 asset* — 像 point cloud 一样可以剪枝、编辑、移植，这正是机器人地图编辑器或 sim-to-real pipeline 需要的。

### 📍 Research Landscape Timeline

```
NeRF 2020 ─► Instant-NGP 2022 ─► Mip-NeRF360 2022 ─► ★ 3DGS SIGGRAPH 2023 ─► 4D-GS / Mip-Splat 2024 ─► GS-SLAM / VGGT 2024-25 ─► feed-forward GS init 2026+
```

3DGS 是把 radiance field 从 "research artifact" 推进到 "robotics-deployable map primitive" 的拐点。下游仍未收口的方向：compression、semantic grounding、feed-forward initialization。

Paper: Kerbl, Kopanas, Leimkühler, Drettakis. *SIGGRAPH 2023.* arXiv: https://arxiv.org/abs/2308.04079
Code: https://github.com/graphdeco-inria/gaussian-splatting

---

## 1 · 为什么这篇论文重要（abstract 里没强调的部分）

NeRF 给了你可微分场景表示，但要付出数小时训练 + 每帧数秒渲染的代价。对图形学这是已知的取舍，对机器人则是 non-starter — 你不可能把一个 1 FPS 的表示塞进 30 Hz 感知 pipeline。3DGS 保留 differentiable rendering 契约（梯度从像素流回场景参数），但抛弃了 MLP。场景变成显式的 ~1–5 百万 anisotropic gaussian；渲染变成 GPU 上的 tile-based rasterization。**概念上的解锁是这个表示现在可检查** — 你能像操作 point cloud 一样剪枝、编辑、移植、下采样 gaussians，这正是机器人地图编辑器需要的。

## 2 · 机制

> 📌 **Napkin Formula**: `Rendered pixel = α-blend{ Project(Gᵢ; intrinsics, pose) | i sorted front→back per tile }` — 每个像素是 projected anisotropic gaussian 按深度排序的加权和。No MLP, no ray-marching, just rasterize-and-blend.

> ⚡ **Eureka Moment**: 关键不是 gaussians 本身 — 而是*组合*：anisotropic ellipsoid（几百万个就能覆盖一个房间，isotropic sphere 需要 10–100×）+ tile-based CUDA rasterizer（排序 α-blend，而非通用 point splat）+ adaptive densification（optimizer 在训练中增删 primitive）。三者同时具备才解锁了 100× 加速；任意缺一都会停留在学术里。

```
   SfM points (COLMAP)
          │
          ▼
   ┌─────────────────────┐
   │ Initialize ~100k    │
   │ anisotropic         │
   │ gaussians:          │
   │   position (xyz)    │
   │   covariance (R,S)  │
   │   opacity α         │
   │   SH coeffs (color) │
   └─────────────────────┘
          │
          ▼  (differentiable rasterizer)
   ┌─────────────────────┐
   │ Tile-based splat →  │
   │ α-blend front→back  │ ──► rendered RGB
   │ in screen space     │
   └─────────────────────┘
          │
          ▼
   Loss: L1 + D-SSIM vs GT image
          │
          ▼
   Adaptive density control:
     · clone gaussians in under-covered regions
     · split gaussians with large gradients
     · prune low-opacity / oversized gaussians
```

对具身用例重要的三件事：

- **Anisotropic covariance** — 每个 gaussian 是 3D ellipsoid，不是球。这让几百万个 primitive 就能覆盖一个房间；isotropic sphere 需要 10–100×。
- **Tile-based rasterizer** — CUDA rasterizer 按 tile 排序 gaussian 并 α-blend。这是速度的来源；不是通用 point cloud renderer。
- **Adaptive densification** — optimizer 在训练中增删 gaussian。最终数量由数据驱动，不是超参。

## 3 · Training loop（实用数字）

| Knob | Default | What it controls |
|---|---|---|
| Iterations | 30k | 训练长度；~7k 给 "good enough" 预览 |
| Densification interval | every 100 iters until 15k | splitter/cloner 触发时机 |
| Position LR | ~1.6e-4 → 1.6e-6 (decayed) `UNVERIFIED` | Gaussian position 更新 |
| Opacity LR | ~0.05 `UNVERIFIED` | α 更新 |
| SH degree | 0 → 3 (warmup) | 颜色表达力 |

单卡 A6000 上报告训练时间：在 Mip-NeRF360 场景上达到 SIGGRAPH 质量约 ~30 分钟 `UNVERIFIED — 随场景复杂度变化`。同硬件下推理：1080p 100+ FPS。对照 NeRF（数小时训练、&lt;1 FPS 渲染），"100× 加速" 实际是 "训练 100× + 渲染 100× 同时成立"。

## 3.5 · Worked example — 桌上的一个马克杯

用手机拍一个咖啡杯，1 m 弧线上 30 张照片。

- **COLMAP init**: ~5K SfM points（稀疏但在杯子 + 桌面上定位良好）。
- **Iter 0**: ~5K gaussians，大多近似球形，opacity ~0.1。
- **Iter 7K**: densification 后 ~120K gaussians — 杯沿 clone 出新点，杯柄曲率被 split 覆盖。PSNR ~28 dB UNVERIFIED。
- **Iter 30K**: ~800K gaussians，opacity 呈双峰（~0 待 prune 和 ~0.9 保留者）。PSNR ~32 dB。Disk size ~180 MB UNVERIFIED。
- **Render**: 1080p 下 RTX 4090 上 ~3 ms/frame → 300+ FPS 余量。同场景 NeRF 约 200 ms (5 FPS)。

这 4–5 个数量级的渲染差距，正是 3DGS 能塞进机器人感知环路而 NeRF 不能的原因。

---

## 4 · 它在哪里 break（论文没着墨的部分）

- **Storage** — 完成的场景在磁盘上 1–2 GB（数百万 gaussian × ~60 floats each `UNVERIFIED`）。对需要随身携带一栋楼地图的 humanoid，这才是约束瓶颈，不是训练时间。2024 年陆续出现的压缩变体（Self-Organizing Gaussians, Compact3D）能砍 5–20× `UNVERIFIED`；vanilla 3DGS 不压缩。
- **Initialization dependence** — 3DGS 依赖 COLMAP 出的 SfM points 做初始化。若 COLMAP 失败（无纹理墙、运动模糊、稀疏视角），gaussians 永远不会干净地收敛。这是工业场景下的静默失败模式。
- **No semantic handle** — vanilla 3DGS 编码外观，不编码类别。"杯子在哪" 需要一个外挂头（LangSplat, Feature-3DGS）。
- **Aliasing at scale** — 同一组 gaussian 从无人机高度和头戴相机看会产生明显锯齿。Mip-Splatting 修复（见 `mip_splatting.md`）。
- **Static scenes only** — 没有时间轴。4D-GS 谱系修复（见 `4dgs_dynamic_scenes.md`）。
- **Specular / reflective surfaces** — ref-NeRF (Verbin CVPR 2022) and NeRF-Casting (Verbin 2024 arXiv 2405.14871) demonstrably outperform 3DGS on reflective scenes. 3DGS per-Gaussian SH order is too low for high-frequency view-dependent appearance. 多篇 2026 paper (PolarGuide-GSDR, MSGS, TraceFlow) 存在 *因為* 3DGS 反射失敗。詳見 ontology §13.2。

### 4.x · Hidden Assumptions

上游假设，违反就触发以上失败：

- **Good COLMAP init** — SfM points 播种 gaussian set；在无纹理 / 运动模糊场景下 COLMAP 失败，gaussians 永远不收敛。
- **Static scene during capture** — 拍 30 张照片期间任何动的物体都会产生 floater 或拖影。
- **Sufficient training views** — 稀疏覆盖（房间 &lt;20 张）会留下欠约束的 gaussian，训练视角看着 OK，novel view 一塌糊涂。
- **Single camera scale (no zoom)** — vanilla 3DGS 对尺度变化 aliasing；Mip-Splatting 是修复。
- **Disk and VRAM headroom** — 1–2 GB 场景必须能进 GPU 内存才能渲染；mobile / Jetson 部署需压缩。

违反时模型经常仍能*渲染*出某种东西 — 静默失败（floater、shimmer、ghosting）才是危险模式。

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

graphdeco-inria/gaussian-splatting 22k stars / 664 open issues / 45 open PRs，活跃的"祖师爷 repo"模式；issue 长尾集中在工程而非算法：

- **GitHub-validated**：**Windows / CUDA 是真实痛点而非脚注** —— Install failure on Windows 11（[issue #1322](https://github.com/graphdeco-inria/gaussian-splatting/issues/1322)）+ RTX 50-series + CUDA 12.8 稳定训练（[#1313](https://github.com/graphdeco-inria/gaussian-splatting/issues/1313)）反复出现；**非 Linux 用户应做好踩坑预期，推荐 WSL2 / Docker 路径**；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#3dgs-original-graphdeco-inriagaussian-splatting)。
- **GitHub-validated**：submodule pinning 长尾 —— `submodules-simple-knn @ 86710c2` 打不开（[issue #1328](https://github.com/graphdeco-inria/gaussian-splatting/issues/1328)）；training stuck at 0%（[#1310](https://github.com/graphdeco-inria/gaussian-splatting/issues/1310)）多与 dataset 路径 / dependency 解析有关；SIBR viewer 网络层 bug（[#1314](https://github.com/graphdeco-inria/gaussian-splatting/issues/1314)）—— 印证 §6 outlook "compressed-by-default" + "feed-forward init" 未到位前工程长尾仍主导部署体验。
- **GitHub-validated（surprise）**：近 6 月 PR 列表有 **HIP/AMDGPU 移植** —— 3DGS 生态正在"破除 NVIDIA 绑定"，对功耗敏感场景（marine / aerial）是 *未被注意的工程信号*；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#3dgs-original-graphdeco-inriagaussian-splatting)。

---

## 5 · 为什么机器人团队在乎（本手册的核心车道）

按运营影响排序三个原因：

1. **可检查表示** — gaussian 是带 extent 的点。已有的 point cloud 工具（下采样、区域裁切、碰撞查询）只需小幅适配即可移植。在 NeRF MLP 上你试试。
2. **可编辑** — 你可以删除某区域 gaussian、从另一个场景移植 gaussian、或扰动位置做数据增强。这正是 3DGS 成为 sim-to-real 视觉训练基底的原因（如 RoboGS 风格 pipeline）。
3. **合理推理预算** — 桌面 GPU 1080p 100 FPS，意味着 Jetson 级设备上配合 tile 管理可达 ~30 FPS `UNVERIFIED — 需要实机验证`。这在感知环路预算内。NeRF 永远不在。

2023 年底到 2024 年悄悄迁移的团队，并非在追 photoreal render；他们追的是一种能在机器人接触中存活下来的场景表示。3DGS 是第一个做到的。

## 6 · 2-year outlook

vanilla 3DGS 现在是 baseline，不是终点。到 2027 年预期：

- **Compressed-by-default 变体** 成为事实起点 — 没人在产品里发 1 GB 场景。
- **Feed-forward initialization**（VGGT 类模型替代 COLMAP 给 gaussian set 做种子）吸收 "需要 SfM" 的失败模式。
- **Semantic-grounded gaussians**（LangSplat 谱系）成为 VLA 消费的默认接口，而非研究 curio。

**Falsifiable prediction:** 到 2027-06，机器人发表里主流 3DGS pipeline *不再*用 COLMAP 初始化 — 会用 feed-forward 3D 模型。届时仍主要靠 COLMAP 做 init 的论文，对它下负注。

**Interview Tip**: 被问 "robotics 为什么选 3DGS 而非 NeRF"，陷阱答案是 "100× 更快"。正确答案是 *"because it's explicit"* — gaussian 可检查、可剪枝、可编辑，像 point cloud；NeRF MLP 不行。速度是结果，不是贡献。

---

## 8 · GitHub-validated atlas（deep dive 增量）

§4.y 已概述 atlas 联动；本节为 2026-05-24 重新爬 issues / PR / license 后的细化证据。

### §8.1 · GitHub-validated pitfalls (2026-05-24 deep dive)

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | Windows 11 安装直接挂在 `diff-gaussian-rasterization` CUDA extension build | [issue #1322](https://github.com/graphdeco-inria/gaussian-splatting/issues/1322): "OSError: [WinError 182] The operating system cannot run %1. Error loading..." — 失败发生在 `python setup.py egg_info` 阶段；无 maintainer 回复 | 🔴 | 走 WSL2 / Linux；issue #1313 是用户自己写的 RTX 50 + WSL2 工作配方，明确说 "Ubuntu Linux is recommended because it feels much more stable" |
| 2 | RTX 50 系列 + CUDA 12.8 需要重做整条依赖栈 | [issue #1313](https://github.com/graphdeco-inria/gaussian-splatting/issues/1313): 用户自发分享的工作配方而非 bug — 必须 Ubuntu 22.04 (WSL2)、PyTorch CUDA 12.8 wheels、重编 diff-gaussian-rasterization + simple-knn + fused-ssim；没有官方支持文档 | 🟠 | 复刻 issue 内步骤；不要相信 README 默认环境对 Blackwell 卡 work |
| 3 | submodule pinning 静默失败（祖师爷 repo 经典痛点） | [issue #1328](https://github.com/graphdeco-inria/gaussian-splatting/issues/1328) "submodules-simple-knn @ 86710c2 打不开" — issue body 仅 "如题"，无 maintainer 回复；commit SHA 失效 | 🟠 | clone 时 `--recurse-submodules`，并 fork 一份子模块到本地镜像，PR #1317-1319（Breadzzone）正在尝试系统性修 Windows submodule build flags |
| 4 | 训练静默 stuck at 0% 即使在顶配硬件上 | [issue #1310](https://github.com/graphdeco-inria/gaussian-splatting/issues/1310): RTX 5090 + 128 GB RAM + 1238 drone photos 卡死在 0%；无 maintainer 回复、无 diagnosis | 🔴 | 缩到 100-200 张子集 sanity check；检查 COLMAP 输出而不是相信 progress bar；保留 CPU monitor 看是否 disk-IO bound |
| 5 | License **明确禁止商业用途**（被许多复用方忽视） | [LICENSE.md](https://github.com/graphdeco-inria/gaussian-splatting/blob/main/LICENSE.md): "THE USER CANNOT USE, EXPLOIT OR DISTRIBUTE THE SOFTWARE FOR COMMERCIAL PURPOSES WITHOUT PRIOR AND EXPLICIT CONSENT OF LICENSORS" — 必须发邮件到 stip-sophia.transfert@inria.fr 申请商业授权 | 🔴 | 机器人产品 / SaaS / VLA pipeline 商用：要么走 INRIA 商业授权流程，要么换 BSD/MIT 的 reimplementation（如 gsplat、nerfstudio 内置实现） |
| 6 | issue close rate 低 + maintainer 几乎不在 issue tracker 回复 | 22.1k★ / **664 open issues** / 45 open PRs；上面 5 个 high-severity issue 全部无 maintainer 回复；最近合并 PR 据查询数月前（PR backlog 主要由社区贡献者推 Windows/CUDA 兼容性） | 🟠 | 把 issues 当 "stack overflow 镜像" 而不是 support channel；生产关键 bug 自己 fork + 维护补丁 |
| 7 | COLMAP 转换 pipeline 在自定义数据上脆弱 | [issue #1308](https://github.com/graphdeco-inria/gaussian-splatting/issues/1308) COLMAP command mismatch in convert.py + [#1307](https://github.com/graphdeco-inria/gaussian-splatting/issues/1307) Custom COLMAP rendering failure — 自有相机 / 非标准目录布局触发静默错位 | 🟡 | 严格按 `data/<scene>/{images,sparse/0}` 布局；先在 Mip-NeRF360 公开 scene 上跑通 sanity 再上自有数据 |
| 8 | （surprise）社区主动推 AMD/HIP 移植 PR | PR #1297 HIP/AMDGPU port + PR #1319 Windows CUDA build flags submodule update — 来自社区而非 INRIA | 🟢 | 功耗敏感场景（marine / aerial / 工业机器人）现在有非 NVIDIA 路径试验中；生产前 review PR 实测分支 |

**Repo health signal**: 22.1k★ / 664 open / ~? closed (counter 未直接可见) / 45 open PR / last meaningful PR backlog ~数月 — *"祖师爷 repo + 论文作者 INRIA mode"*: 论文级代码作为参考实现，工程化几乎全部依赖社区 PR；issue tracker 是搜索证据库，不是 support channel。

**讀者實務含義**: (1) **商用前先解决 license** — INRIA 非商业许可在产品化时是真实 blocker，要么走授权要么用 BSD 重写如 `gsplat`；(2) **Windows / RTX 50 部署预设要踩坑**，issue #1313 是当前最完整的 RTX 50 配方，按它走可以省一周；(3) **关键 bug 别等官方** — 自己 fork、把社区 PR（特别是 Breadzzone 的 Windows 系列 + HIP 移植）merge 进内部 mirror。

## References

- **3DGS original** — Kerbl, Kopanas, Leimkühler, Drettakis. *SIGGRAPH 2023.* https://arxiv.org/abs/2308.04079
- **Mip-NeRF360 benchmark** — Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **NeRF original**（主流 NVS 已被 3DGS 取代，但反光/鏡面場景例外 — 見 ontology §13.2）— Mildenhall et al. *ECCV 2020.* https://arxiv.org/abs/2003.08934
- **Self-Organizing Gaussians (compression)** — Morgenstern et al. *ECCV 2024.* [arXiv link TBD]

## Boundary

本文解构 3DGS 原论文。**不**覆盖：

- 动态场景扩展 → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- SLAM 集成 → `foundations/3dgs-family/gs_slam_dissection.md`
- Aliasing 修复 → `foundations/3dgs-family/mip_splatting.md`
- 3DGS vs 其他场景表示（mesh, voxel, feed-forward pointmap）→ `crossing/representation-migration/`
- VLA policy 如何消费 gaussian 场景 → `bridge-to-vla/feature-cloud-to-action.md`
- 与 feed-forward 3D 模型 VGGT 的对比 → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
