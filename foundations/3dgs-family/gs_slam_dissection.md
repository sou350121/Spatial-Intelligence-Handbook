<!-- ontology-5axis
problem: VSLAM + Reconstruction (Gaussian-based)
representation: 3DGS + camera tracking
sensor: RGB-D / Mono
paradigm: Hybrid-DiffRender + tracking
time: Online (per-scene incremental)
ref: ../../cheat-sheet/ontology.md §7
-->

# GS-SLAM — Gaussian Splatting Inside the SLAM Loop (GS-SLAM 在线 SLAM 解构 — CVPR 2024)

> **Published**: 2023-11 (arXiv) / CVPR 2024
> **Paper**: Yan et al. — *GS-SLAM: Dense Visual SLAM with 3D Gaussian Splatting*
> **Team**: Tsinghua + Zhejiang Lab
> **Core position**: 第一个把 3DGS *在线*跑在移动 RGB-D 相机下的系统 — tracking 靠在当前 gaussian map 上 render-and-compare，mapping 靠 depth 驱动 gaussian spawn。Loop closure 仍未解决。

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**TL;DR:** GS-SLAM 终于让 3DGS *在线*跑在移动相机下，填补了 "post-hoc reconstruction" 到 "live spatial map" 的 gap。未解的问题是 loop closure — 当你 30 秒后发现相机当时位姿错了，gaussian 不能干净重构，这是经典 SLAM 在长时序 mapping 上仍占优的原因。

### X-Ray (non-expert friendly)

(a) Vanilla 3DGS 是离线的：拍图、跑 COLMAP、优化 ~30 分钟。SLAM 要求反过来 — 每个新帧都应增量精化地图。(b) GS-SLAM 把 *tracking*（只更新位姿，快，render-and-compare）和 *mapping*（gaussian 更新，慢，受 keyframe 限定）分开，是经典 ORB-SLAM 拆分但以 gaussian 作为地图后端。(c) 对空间 AI 工程师：GS-SLAM 是你第一次拿到 *可渲染、稠密、在线*的地图 — 适合短室内 demo，但还不能在带回环的长时序轨迹上替代 ORB-SLAM3。

### 📍 Research Landscape Timeline

```
ORB-SLAM3 2020 ─► NICE-SLAM (NeRF) 2022 ─► Co-SLAM 2023 ─► ★ GS-SLAM CVPR 2024 ─► SplaTAM 2024 ─► MonoGS 2024 ─► loop-closed GS-SLAM 2026+ (open)
```

GS-SLAM 是首个 3DGS 原生的 SLAM 系统；SplaTAM/MonoGS 延展该谱系，但 gaussian map 上的 loop closure 仍开放。

Reference paper: Yan et al. "GS-SLAM: Dense Visual SLAM with 3D Gaussian Splatting." *CVPR 2024.* arXiv: https://arxiv.org/abs/2311.11700

---

## 1 · 为什么这个融合是对的下一步

3DGS 发表态是离线工具：收图、跑 COLMAP，再优化 gaussian 约 30 分钟。SLAM 要求增量更新 — 每个新帧应精化地图而不重训练。朴素融合（"逐帧跑 3DGS"）不可行；gaussian 优化太慢，且表示没有增量插入的概念。**GS-SLAM 是第一个让在线环路可处理的系统**，借鉴 ORB-SLAM 拆分 tracking 与 mapping 的方式，把 gaussian 作为 map primitive。

要抵制的过度宣称："3DGS 替代经典 SLAM"。并没有。GS-SLAM 最好读作 "ORB-SLAM 配 photoreal 地图后端" — 前端 tracking 仍可辨认为经典做法，gaussian 是后端交付物。

> ⚡ **Eureka Moment**: 可微分 rasterizer 就是 *tracker* — 在预测位姿处用当前 gaussian map 渲染期望 RGB-D，与观测帧做 photometric loss，反传回位姿。同一个 rasterizer 既做 mapping 又做 tracking。**没有独立 feature pipeline，没有 PnP，没有 descriptor matching** — 位姿估计塌缩为对渲染 loss 做 10 步梯度下降。

## 2 · 架构

> 📌 **Napkin Formula**: `pose ← argmin_T ‖Render(GaussianMap, T) − observed_RGBD‖²`（前端）。然后 `GaussianMap ← argmin_G ‖Render(G, T_keyframes) − observed_keyframes‖²`（后端）。两者都用同一个可微分 rasterizer — 区别只在优化哪个变量。


```
   RGB-D frame at time t
              │
              ▼
   ┌─────────────────────────┐
   │ Front-end tracking      │
   │  · render expected RGB-D │
   │    from current gaussian │
   │    map at predicted pose │
   │  · compute photometric + │
   │    geometric residual    │
   │  · optimize pose only    │
   │    (~10 iters, fast)     │
   └─────────────────────────┘
              │
              ▼  pose T(t)
   ┌─────────────────────────┐
   │ Keyframe decision       │
   │   yes → insert keyframe │
   │   no  → continue        │
   └─────────────────────────┘
              │  (if keyframe)
              ▼
   ┌─────────────────────────┐
   │ Map expansion           │
   │  · spawn new gaussians  │
   │    in unobserved regions │
   │    (driven by depth)    │
   │  · gaussian opt over    │
   │    recent keyframes      │
   │    (~50–100 iters)      │
   └─────────────────────────┘
              │
              ▼
   Updated gaussian map
```

关键工程技巧：**render-and-compare tracking**（位姿估计复用可微分 rasterizer — 在预测位姿渲染期望图像，与实际帧做 photometric loss，反传回位姿）；**depth-driven spawning**（新 gaussian 由 RGB-D 或学到的单目深度在未观测区播种，移除 COLMAP 风格全局 SfM init）；**keyframe-bounded optimization**（gaussian 更新只跑近期 keyframe 滑窗，不跑整个地图 — 限定单帧算力）。

## 2.5 · Worked example — 30 秒室内行走

手持 RealSense D435i 走 4 m × 4 m 办公室，30 s @ 30 Hz → 900 帧。

- **Frame 1**: spawn ~3K gaussian，pose = identity。
- **Frame 300** (10 s): ~200K gaussian；tracking ~80 ms；render ~30 ms。
- **Frame 900** (30 s): ~500K gaussian、~600 MB GPU；RTX 3090 上速率降到 3 Hz UNVERIFIED。
- **Loop closure**: 回到起点，ATE ~5 cm；对 500K covariance 做 rigid SE(3) 校正 → PSNR ~1 dB 损失，不能干净重收敛。

>30 s 捕获后必须做激进 pruning。

---

## 3 · loop closure 问题（未解）

经典 SLAM 把 loop closure 当作图优化：检测重访，跑全局 pose-graph 优化，每个 landmark 接同样 SE(3) 校正。

**Gaussian 在这套下不能干净 refactor。** 给点 landmark 加 rigid pose 校正是平凡的；给 gaussian 加，会把 covariance + SH 系数转到错误坐标系 `UNVERIFIED severity`。更糟，校正前后的 gaussian 在校正后地图里会重叠，没有干净的 merge/prune 算法，重优化（densification + opacity）没有收敛保证。

GS-SLAM 与后继（SplaTAM, MonoGS）大多是*回避* loop closure 而非解决 — 它们瞄准短轨迹室内场景，漂移有界。诚实的说法："短回环上地图质量好，对长轨迹闭合没有真正答案"。

## 4 · Jetson Orin 上的实时性（部署问题）

桌面 RTX 3090 上报告运行时 `UNVERIFIED`: tracking ~5–8 Hz，后台 mapping 速率更低。Jetson Orin (32 GB) 上同代码路径降到 ~1–3 Hz `UNVERIFIED — 需实机验证`。下降原因：LPDDR5 内存带宽（rasterization 是 memory-bound，不是 compute-bound，FLOPS 比值会误导）、没有 tensor-core 捷径（rasterizer 是手写 CUDA）、地图增长（室内 30 s 捕获 ~500k gaussian `UNVERIFIED`，渲染开销随每 tile 活跃 gaussian 数量 scale）。

实际含义：GS-SLAM 在 Jetson 上做短 demo（一个房间）可以，但多房间长时序任务在没有激进 gaussian pruning 时不行。

### 4.x · Hidden Assumptions

上游假设，违反就触发上面的部署失败：

- **RGB-D input (depth available)** — depth-driven spawn 需要真实深度；单目变体（MonoGS）用学到的深度替代，但继承其 scale error。
- **Bounded trajectory length / no loops** — gaussian 上的 loop closure 未解；长轨迹静默漂移。
- **Static scene** — 移动的人 / 物产生 optimizer 不能干净 prune 的浮动 gaussian。
- **Photometric stability** — 曝光 / 光照变化打破渲染 loss；tracking 发散。
- **Sufficient texture** — 无纹理走廊使 photometric tracking 退化；经典 + IMU 能更好恢复。
- **平台带 GPU** — render-and-compare 需 CUDA；纯 CPU 不可行。

违反时 tracking 要么*响亮发散*（好，可恢复），要么*静默漂移*（坏，会累积）。Vanilla GS-SLAM 没有 drift-aware 置信旗标。

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

GS-SLAM 谱系在 GitHub 上的 ecosystem 状态比纸面弱得多：

- **GitHub-validated（关键发现）**：**主 SLAM pipeline 仓库 `UNVERIFIED`** —— 截至 2026-05-21 已确认公开的只有 rasterization 子模块 `yanchi-3dv/diff-gaussian-rasterization-for-gsslam`（249 stars / 22 forks / 3 open issues），主 pipeline 仓库未公开 / 未找到；**生产部署建议走 SplaTAM / Gaussian-SLAM / Photo-SLAM 等更新后继**，本仓 dissection 仅作 paper 算法对照阅读；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#gs-slam--yan-et-al-cvpr-2024)。
- **GitHub-validated**：子模块自身处于 stale 状态 —— Missing requirement file（[#7](https://github.com/yanchi-3dv/diff-gaussian-rasterization-for-gsslam/issues/7)，2025-04 依赖文档不全）+ "Can I ask for a demo?"（[#6](https://github.com/yanchi-3dv/diff-gaussian-rasterization-for-gsslam/issues/6)，2024-12 无 runnable example）+ "Running Live with RGB-D Camera"（[#5](https://github.com/yanchi-3dv/diff-gaussian-rasterization-for-gsslam/issues/5)，2024-12 实时部署无工作示例）—— 印证 §6 "loop closure 未解 + 长时序未解"的开放空缺**没有等到主仓库的工程化补丁**。
- **GitHub-validated（衍生分支寿命规律）**：与 4D-GS 一道符合"paper 发布后 12–18 个月活跃，之后断崖"的衍生分支寿命模式 —— **研究者复现 paper OK，部署务必找继任者**。

---

## 5 · 它在哪里赢过经典 SLAM（在哪里没赢）

| Scenario | GS-SLAM | Classical (ORB-SLAM3, RTAB-Map) |
|---|---|---|
| 室内 RGB-D，短轨迹，需要 photoreal 地图 | ✅ 明显赢 — 输出可渲染，经典只产稀疏 point cloud | — |
| 室内 RGB-D，长轨迹带回环 | ⚠️ Loop closure 未解 | ✅ 赢 — pose-graph 优化成熟 |
| 户外、白昼、大尺度 | ❌ 内存爆 | ✅ 稀疏地图能处理 |
| 弱纹理场景（仓库走廊）| ⚠️ Photometric tracking 退化 | ⚠️ ORB 特征也退化 — 平局 |
| 低光 / 高动态范围 | ❌ 渲染 loss 脆 | ⚠️ 特征匹配也吃力 |
| 给下游 VLA policy 的地图质量 | ✅ 赢 — gaussian 比稀疏点更丰富的先验 | ❌ 稀疏点需独立 dense 重建 |

诚实总结：当你需要*可渲染、稠密*地图且能限制轨迹长度时，GS-SLAM 赢。长时序、大尺度、恶劣条件下，经典 SLAM 赢。

## 6 · 2-year outlook

按影响排序的未解问题：

1. **Gaussian map 上的 loop closure** — 需要尊重渲染 loss 的有原则 merge/prune。本谱系最大空缺。
2. **Feed-forward initialization** — 用 VGGT 类模型从单目输入产 gaussian-ready point cloud 替代 RGB-D spawn。
3. **环路内地图压缩** — 在线 pruning 而不损伤可渲染性，开放。

**Falsifiable prediction:** 到 2027-12，至少出现一个发表的 GS-SLAM 变体，能处理 >100m 回环，闭合精度与 ORB-SLAM3 相当。若不出现，该谱系会停在 "室内 demo 工具" 平台。

**Interview Tip**: 被问 "GS-SLAM 是否替代 ORB-SLAM3"，陷阱是 yes。正确答案：*"还不行 — gaussian map 上 loop closure 开放"*。把它定位为 "ORB-SLAM 加 photoreal 后端" 用于短室内 demo；长时序 mapping 保留经典直到 SE(3) 校正下的 merge/prune 有原则算法。

---

## 8 · GitHub-validated atlas（deep dive 增量 — SplaTAM 作为代理证据）

GS-SLAM 主 pipeline repo 未公开（详见 §4.y），所以本节深挖 **SplaTAM** (`spla-tam/SplaTAM`) — 同时期 CVPR 2024 平行工作、3DGS-SLAM 谱系最常被复用的开源实现，最能反映本谱系工程化现状。

### §8.1 · GitHub-validated pitfalls (2026-05-24 deep dive, SplaTAM 代理)

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | **Repo 已实质 stale** — 最近一次 commit 2024-06-19（"Update Torch Version Requirements"），距今 ~23 个月没有 main 分支活动 | [commits/main](https://github.com/spla-tam/SplaTAM/commits/main): last commit 2024-06-19；第二近 2024-03-26；**0 open PR / 12 closed PR**（contribution channel 实质关闭） | 🔴 | 把 SplaTAM 当 paper 复现工具，不当生产框架；生产走 MonoGS / Gaussian-SLAM / Photo-SLAM 后继 |
| 2 | Loop closure 谱系级未解（与 dissection §3 一致，社区独立印证） | [issue #151](https://github.com/spla-tam/SplaTAM/issues/151) "Loop Closure Issues": "I have read other tickets that you mention about the difficults at loop closure" — 用户在 Behavior 1k 数据集上踩坑，**maintainer 无回复**；issue 自 2025-10 起 open 未解 | 🔴 | 限制轨迹长度（短室内 demo）；长轨迹 / 多房间用 ORB-SLAM3 + dense 后端，别指望 SplaTAM loop close 干净 |
| 3 | 非确定性结果 — 即使 `seed_everything` 也跑不出一致 metric | [issue #144](https://github.com/spla-tam/SplaTAM/issues/144) "Non-deterministic results despite using seed_everything": "I was wondering why this happens and if there's a way to achieve deterministic results?" — 用户在 Replica 上多次跑得不同 ATE / PSNR；无 maintainer fix | 🟠 | benchmark 报告必须跑 ≥3 seeds 取 mean ± std；不要单 run 数字写论文；CUDA non-determinism + gaussian 随机 spawn 是已知根因 |
| 4 | **Mesh export 未实现** — 只能出 .ply 点云（破坏下游 simulation / collision 用例） | [issue #145](https://github.com/spla-tam/SplaTAM/issues/145) "Export to Mesh": user noted `scripts/export_ply.py` only exports point clouds, asks if mesh export is supported — **maintainer 无回复、无 label、无 milestone** | 🟠 | 走 Poisson reconstruction (Open3D) 或 SuGaR / 2DGS 后处理把 gaussian 转 mesh；不要假设 SplaTAM 直接出 simulation-ready geometry |
| 5 | ScanNet++ 基准复现卡在 dataset 本身缺 depth | [issue #153](https://github.com/spla-tam/SplaTAM/issues/153) "Question Regarding Depth Data in the ScanNet++ Dataset": "the dslr folder contains only uncalibrated RGB images, without corresponding depth maps" — paper 用的 depth 来源未文档化 | 🟠 | ScanNet++ 实验若是 portfolio / 论文必需：联系作者要 depth pipeline；否则改用 Replica（合成 depth 干净）或 TUM-RGBD（depth 自带） |
| 6 | 自定义数据 / iPhone NeRFCapture pipeline 静默错位 | [issue #142](https://github.com/spla-tam/SplaTAM/issues/142) "images not properly mapped": 用 `bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py` 输出 image alignment 失败；无 maintainer 回复 | 🟡 | 先在 Replica / TUM 公开数据集 sanity check；自定义数据走 COLMAP 预处理再喂入而不是用 nerfcapture 一键脚本 |
| 7 | 真实 RGB-D 相机（RealSense D435i）live 模式无 working example | [issue #125](https://github.com/spla-tam/SplaTAM/issues/125) "D435i real-time or offline slam?" (open since 2024-07) + [issue #44](https://github.com/spla-tam/SplaTAM/issues/44) "Support for Stereo Images & Depth" (open since 2023-12) + [issue #39](https://github.com/spla-tam/SplaTAM/issues/39) "Debugging Failure on Custom 3DScanner App Data" — **三个 real-sensor 集成 issue 全部 open 1.5+ 年** | 🔴 | SplaTAM 在 paper benchmark 之外的 sensor 部署没人 maintain；走 MonoGS（单目，更新更活）或 Photo-SLAM（C++ 重实现，对 RealSense 有官方示例）|
| 8 | OOM 在长 trajectory + 高分辨率 keyframe 上仍是常态 | [issue #124](https://github.com/spla-tam/SplaTAM/issues/124) "CUDA OUT OF MEMORY" (open since 2024-07，labeled "Question"，无 fix) — 与 §2.5 worked example "30 s 500K gaussian ~600 MB" 一致 | 🟠 | 30 s+ 捕获必须激进 prune；keyframe 间隔放大；分辨率降到 640×480 sanity 再升 |

**Repo health signal**: 2.1k ★ / 236 forks / 53 open issues / 0 open PR / 12 closed PR / **last commit 2024-06-19**（~23 个月静默）/ BSD-3-Clause（商业可用，这是相对 INRIA 3DGS 的关键优势） — *"paper-shipped, walk-away"* 模式：CVPR 2024 论文 + V1 release 后 maintainer 实质转向 nerfstudio / 后继课题，issue tracker 变只读墓地。

**讀者實務含義**: (1) **2026 年生产部署不要选 SplaTAM** — repo stale 2 年，real-sensor 集成 issue 全 open，maintainer 无回复；走更新的 MonoGS / Gaussian-SLAM / Photo-SLAM；(2) **SplaTAM 仍是好的 paper 学习实现** — BSD-3 友好、Replica/TUM 跑得通，适合理解 §2 架构，不适合放进机器人；(3) **本谱系 issue 模式印证 §6 outlook** — loop closure / 长轨迹 / real-sensor 三大开放问题在 GitHub issue tracker 上有独立证据，不是 dissection 在唱衰。

## References

- **GS-SLAM** — Yan et al. *CVPR 2024.* https://arxiv.org/abs/2311.11700
- **SplaTAM**（并行工作，类似融合）— Keetha et al. *CVPR 2024.* https://arxiv.org/abs/2312.02126
- **ORB-SLAM3**（经典 baseline）— Campos et al. *T-RO 2021.* https://arxiv.org/abs/2007.11898
- **MonoGS**（单目变体，移除 RGB-D 需求）— Matsuki et al. *CVPR 2024.* [arXiv link TBD]

## Boundary

本文覆盖 gaussian splatting 与在线 SLAM 的融合。**不**覆盖：

- 静态 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- 动态 4D 扩展 → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- 跨尺度 aliasing → `foundations/3dgs-family/mip_splatting.md`
- 空中场景的经典 VIO/SLAM → `crossing/slam-vio-migration/vggt_vs_drone_vio.md`
- Cross-representation 对比 → `crossing/representation-migration/`
- VLA policy 对 gaussian map 的消费 → `bridge-to-vla/feature-cloud-to-action.md`
- Feed-forward 3D 作为替代前端 → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
