<!-- ontology-5axis
problem: VSLAM + Reloc + MultiSession (Atlas)
representation: Sparse landmarks + Keyframe graph + Atlas multi-map
sensor: Mono / Stereo / RGB-D + IMU optional
paradigm: Geometric-Indirect + BA + DBoW2
time: Incremental-Smoother
ref: ../../cheat-sheet/ontology.md §7
-->

# ORB-SLAM3 Dissection (ORB-SLAM3 解构)

> **Published:** arXiv 2020, *IEEE T-RO* 2021 · Campos, Elvira, Gómez Rodríguez, Montiel, Tardós (Univ. of Zaragoza)
> **arXiv:** https://arxiv.org/abs/2007.11898 · **Code:** https://github.com/UZ-SLAMLab/ORB_SLAM3
> **核心定位:** 这个"一栈通吃"的 feature-based 视觉 / 视觉惯性 SLAM 至今仍是 indoor / manipulation / AR robotics 默认要 fork 的版本 —— 没有第二个工程化 codebase 在一份代码里同时做 mono + stereo + RGB-D + IMU + multi-map atlas。

**Status:** v1。延迟 / 内存 `UNVERIFIED`。
**TL;DR:** ORB-SLAM3 胜不在精度，而在能用同一套三线程架构跑在 Jetson Nano、手机、或 RGB-D arm cell 上，并通过 Atlas multi-map 从绑架（kidnap）中恢复。换成 feed-forward 3D 模型，你会同时丢掉 IMU 耦合、闭环、长期建图。

**X-Ray.** 视觉 SLAM 在三个时间尺度上要做三件事：跟每一帧、建局部地图、检测闭环。ORB-SLAM（2015）是第一个把这三件事放到独立线程里做的。ORB-SLAM3（2021）能交替接受 mono / stereo / RGB-D + IMU —— 并且 —— 它最大的新点子 —— 把**多张不相连的地图保存在 Atlas 里**，让 tracking loss 不再终结 session。可以理解为"视觉 SLAM 界的 Linux"：不是最快的，但是工具默认的那个。

## 📍 研究全景时间线

```
2007    2011    2014     2015         2017            2021            2024+
PTAM ─► DTAM ─► SVO ───► ORB-SLAM ──► ORB-SLAM2 ────► ORB-SLAM3 ────► VGGT / DUSt3R
                          (mono)      (+stereo/RGBD)  YOU ARE HERE    (feed-forward)
└─ keyframe + features ────────────────────────────┘  └─ learned ─┘
```

keyframe-and-features 家族的顶点。*为什么室内 RGB-D / manipulation 5 年没有替代品？*

---

## 1 · 架构

### 1.1 三线程骨架 + Atlas

| 线程 | 工作 |
|---|---|
| **Tracking**（相机帧率） | ORB 提取、匹配 local map、motion-only BA、KF 决策 |
| **Local mapping**（~5–10 Hz） | 插 KF、三角化、local BA、cull |
| **Loop & merging**（闭环触发） | DBoW2、essential graph、full BA、Atlas merge |
| **Atlas**（数据） | active + 非 active 地图；tracking 丢失时新开一张 |

### 1.2 ⚡ Eureka Moment

> **Tracking 丢失不是要躲掉的失败 —— 它是要规划的常规事件。新开一张地图、继续跑，等 place recognition 找到重叠时再 merge 回来。**

ORB-SLAM3 之前的系统把 tracking 丢失当 session 结束。Atlas 重构这个语义：*N* 张不相连地图共存；闭环变成*地图合并*。这让 ORB-SLAM3 能部署到仓库巡检 / 多房间 AR。

### 1.3 数据流 —— 三线程 + Atlas 一张图

```
                   ORB-SLAM3 三线程 + Atlas (shared data)
                                                                            
  ┌──────────────────────────────────────────────────────────────────────┐
  │   📷 Camera @ 30 Hz       📐 IMU @ 200 Hz                             │
  │        │                       │                                      │
  │        └───────┬───────────────┘                                      │
  │                ▼                                                      │
  │   ┌──────────────────────────────────────┐                            │
  │   │  ① TRACKING  (实时 · ~17 ms/frame)   │                            │
  │   │  • ORB 提取 (8 层金字塔 · ~1000 pt)  │                            │
  │   │  • Match against local map           │                            │
  │   │  • Motion-only BA  (固定地图、只调 T)│                            │
  │   │  • KF 决策 (是否成为新关键帧)         │                            │
  │   └──────────────┬───────────────────────┘                            │
  │                  │ KFs (pose + features)                              │
  │                  ▼                                                    │
  │   ┌──────────────────────────────────────┐                            │
  │   │  ② LOCAL MAPPING  (~5–10 Hz · 异步)  │                            │
  │   │  • 插入新 KF                          │                            │
  │   │  • Triangulate 新 map point          │                            │
  │   │  • Local BA  (~20 covisible KFs 滑窗)│                            │
  │   │  • Cull 冗余 KF + 漂移 map point      │                            │
  │   └──────────────┬───────────────────────┘                            │
  │                  │ KFs + DBoW2 BoW 向量                                │
  │                  ▼                                                    │
  │   ┌──────────────────────────────────────┐                            │
  │   │  ③ LOOP & MERGING  (闭环触发 · 秒级) │                            │
  │   │  • DBoW2 place recognition           │                            │
  │   │  • Essential graph + Pose Graph Opt   │                            │
  │   │  • Full BA  (跨 active map 全图)     │                            │
  │   │  • Atlas merge  (跨 maps 合并)        │                            │
  │   └──────────────┬───────────────────────┘                            │
  │                  │ updates                                             │
  │                  ▼                                                    │
  │   ┌──────────────────────────────────────────────────────────────┐   │
  │   │  📚 ATLAS  (3 线程共享数据)                                    │   │
  │   │                                                                │   │
  │   │   ┌────────┐  ┌────────┐  ┌────────┐                          │   │
  │   │   │ Map A  │  │ Map B  │  │ Map C  │   ...                    │   │
  │   │   │ active │  │ frozen │  │ frozen │                          │   │
  │   │   │ KFs +  │  │ KFs +  │  │ KFs +  │                          │   │
  │   │   │ points │  │ points │  │ points │                          │   │
  │   │   │ DBoW2  │  │ DBoW2  │  │ DBoW2  │                          │   │
  │   │   └────────┘  └────────┘  └────────┘                          │   │
  │   │                                                                │   │
  │   │   tracking lost ⇒ 新开 Map D；place reco hit ⇒ merge          │   │
  │   └──────────────────────────────────────────────────────────────┘   │
  │                                                                       │
  └──────────────────────────────────────────────────────────────────────┘

   ORB 描述子 (256-bit binary) 贯穿三线程：tracking 匹配 + map point 表示 + DBoW2 词袋向量
   ⇒ "把 ORB 换成 SuperPoint" 难的原因：一种原语，三种独立用法。

### 1.3.1 Atlas 救援 —— 从单图 SLAM 到多图 session

```
   传统 SLAM (ORB-SLAM 1/2 · 单图):
   ──────────────────────────────────────────────────
        Session start
              ●─●─●─●─●─●     Map A
                       │
                       ▼  tracking 丢失 (绑架 / 黑屏 / 跑出去)
                       💥
                       └─►  SESSION END  (历史丢失)


   ORB-SLAM3 with Atlas (多图共存):
   ──────────────────────────────────────────────────
        Session start
              ●─●─●─●─●─●     Map A (active)
                       │
                       ▼  tracking 丢失
                       
                       🆕  New empty Map B (now active)
                       │
                       ●─●─●─●─●─●─●   Map B grows
                                   │
                                   ▼  DBoW2 place recognition
                                   │
                                   ✓  overlap detected with Map A!
                                   │
                                   ▼
                          ╔═══════════════════╗
                          ║   MERGE A ∪ B     ║
                          ║   + full BA on    ║
                          ║   combined essential║
                          ║   graph           ║
                          ╚═════════╤═════════╝
                                    │
                                    ▼
              ●─●─●─●─●─●─●─●─●─●─●─●   Map AB (continued)
              
        Session continues, history preserved

   💡 关键洞见：tracking 丢失 = 规划事件，不是 session 结束。
   这让 ORB-SLAM3 能跑仓库巡检 + 多房间 AR + 长期 mapping 这种长 session 场景。
```

---

## 2 · 数学核心

### 📌 Napkin Formula

```
T*  =  argmin_T   Σᵢ  ρ( ‖ π(T · Xᵢ) − uᵢ ‖_Σ )
```

`T ∈ SE(3)` 位姿；`Xᵢ` 3D 点；`uᵢ` 2D 观测；`π` 投影；`Σ` 协方差；`ρ` Huber。**视觉 SLAM 就是这个 reprojection-error 最小化，在三种尺度上重复** —— motion-only BA（每帧）、local BA（滑窗）、full BA（闭环）。

带 IMU 时：`J = J_visual + J_imu_preintegration + J_bias_walk`。manifold 上的 IMU 预积分（Forster 2015）把 IMU 当 "delta-pose factor" —— 这是 VINS / OpenVINS / ORB-SLAM3 共用同一个 factor-graph backend 的原因。

**直觉:** mono 是尺度模糊 → 要 stereo / RGB-D / IMU 才能给出米。IMU 给出短期度量 + roll/pitch；相机修漂移；只有闭环能修长期 yaw / 位置。

### 2.1 同一个公式，三个 BA 尺度

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │   ① Motion-only BA            [Tracking 线程 · 每帧]          │
   │      ╔══════════╗                                            │
   │      ║  T_new   ║  ←  只调 1 个位姿 (新帧)                    │
   │      ╚════╤═════╝                                            │
   │           │  地图固定                                         │
   │      ●─●─●─●─●─●  (map frozen)                               │
   │                                                              │
   │      ~5 ms/frame · 4 iter LM · 100s of features              │
   │                                                              │
   ├──────────────────────────────────────────────────────────────┤
   │                                                              │
   │   ② Local BA                 [Local mapping 线程 · 每 KF]    │
   │                                                              │
   │      ╔══════════════════════╗                                │
   │      ║  ~20 covisible KFs   ║  ←  滑窗内全调                  │
   │      ║    + their points     ║                                │
   │      ╚════════╤═════════════╝                                │
   │               │  Schur complement                            │
   │      ●─●─●─●─[●─●─●─●─●─●]─●─●─●                              │
   │               └─ window ──┘                                  │
   │                                                              │
   │      ~100 ms/KF · 几十 KF · 几千 features                    │
   │                                                              │
   ├──────────────────────────────────────────────────────────────┤
   │                                                              │
   │   ③ Full BA                  [Loop & merging 线程 · 闭环时]  │
   │                                                              │
   │      ╔══════════════════════════════════════════╗            │
   │      ║      Active map 全部 KFs                  ║            │
   │      ║      + 全部 map points                     ║            │
   │      ║      + IMU residuals (如 VI)              ║            │
   │      ╚════════╤═════════════════════════════════╝            │
   │               │  Schur + PGO 配合                            │
   │      ●─●─●─●─●─●─●─●─●─●─●─●─●  (全图 + 闭环约束都跑)         │
   │                                                              │
   │      几秒 · 闭环触发 · 1000s of KF, 100k+ points              │
   │                                                              │
   └──────────────────────────────────────────────────────────────┘

   📌 同一个 `min Σ ‖u − π(T,X)‖²` 公式，三个时间尺度复用：
      • 单帧 (实时)  → 滑窗 (异步) → 全图 (闭环)
   ⇒ Schur complement 数学细节 → `foundations/spatial-math/bundle_adjustment.md`
```

---

## 3 · 玩具例子：单帧 tracking

Mono 30 Hz、室内、约 100 个 ORB 特征匹配。Jetson Orin 上的时间 `UNVERIFIED`：

| 步骤 | 时间 |
|---|---|
| ORB 提取（8 层金字塔、目标 1000） | ~8 ms |
| 常速 predict + 半径 match | ~3 ms |
| Motion-only BA（LM，4 iter） | ~5 ms |
| KF 决策 | <1 ms |
| **总 tracking** | **~17 ms** |

并行：local mapping ~100 ms/KF；DBoW2 ~20 ms/KF；full BA 只在闭环。这套预算就是为什么 ORB-SLAM3 是室内 30 Hz，不是 aerial 200 Hz。

---

## 4 · 工程：ORB 为什么仍在出货

ORB（Rublee 2011）：FAST + steered BRIEF、256-bit 二进制、旋转不变、<1 ms/帧。**packed bits 上的 Hamming 距离吃进 L1 cache；不需要 GPU。** ORB 约 1 µs/keypoint，对比 SIFT 约 50 µs（L2 float）、SuperPoint 约 10 µs（要 GPU）。

为什么 ORB-SLAM3 内部不换掉 ORB？不是精度问题 —— **DBoW2 闭环建在 ORB 之上**，DBoW2 重训 + 集成是几个月的工程。SuperSLAM 之类的 fork 存在；没有一个挪到规范 fork 的位置。

---

## 5 · 数据与评测

报在 EuRoC MAV（stereo+IMU，ATE 2–10 cm `UNVERIFIED`）、TUM-VI（长 handheld 室内外，Atlas 用）、TUM-RGBD。⚠️ 按 `AGENTS.md` 仿真饱和约束：EuRoC 数字**不能**外推到户外 / 高速 / 振动。

---

## 6 · 能力与失败模式

**出货场景:** 室内 manipulation（RGB-D + IMU）；AR/VR（stereo + IMU + Atlas multi-session）；带闭环的仓库 AGV。

**失败场景:** 无纹理场景（白墙 → tracking 丢）；高速 / 运动模糊（>2 rad/s 让 FAST 缺料）；动态场景（静默地图污染、不会 crash；DynaSLAM 这类 fork 在修这点）；aerial 200 Hz / sub-10 ms（见 `crossing/slam-vio-migration/`）；户外 GNSS 感知的 AD。

### 6.1 Hidden Assumptions

- **静态刚性世界** —— 每个 map point 都被当作不动。人、门、车 → 静默地图污染、不 crash。
- **光照一致** —— BRIEF 比较像素对的亮度；HDR 切换会翻 descriptor 的 bit。
- **内参稳定** —— 塑料壳 RealSense 上的温度引起的焦距漂移看不见。
- **IMU bias 缓慢变化** —— 桨振破坏 random-walk 模型；aerial 用户选 VINS / OpenVINS 的 #1 原因。
- **每个 session 至少一次闭环** —— 没闭环时漂移累积、Atlas 也合不起来。

### 6.2 GitHub 实地失败（atlas 联动）

- **GitHub-validated**：**IMU 初始化失败**是 issue tracker 第一大类（#730 / #933 / #980 / #264），共因是 D435i / 自录 / Gazebo 的 IMU-cam 时间戳不同步 → preintegration 空 buffer → 死循环；硬件 trigger / Kalibr 时间偏移标定是入场费，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**Pangolin / Eigen / g2o 版本不匹配**导致 segfault / `G2oTypes.cc` 崩 / `SO3::exp failed`（#967 / #828 / #451 / #156 自 2022 open），印证"内参 / 依赖版本稳定"隐藏假设；产品部署必须锁版本 fork + Docker，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**maintainer 带宽 << 用户量** — 568 open issues / 最近 push 2024-07 / 主仓视同冻结，社区贡献全部流向外部 fork (`thien94/...`, `zang09/ORB_SLAM3_ROS2`, `SuperSLAM`)，用户 #1001 (2026-04) 吐槽 "the worst repository I have ever tried to work with"；选 ORB-SLAM3 意味着选 fork 文化，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。

---

## 7.5 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 系统性扫描 538 个 open issue / 30 个 PR，覆盖 build hell、ROS 2 port、Atlas merge、IMU init、stereo 失败模式六大类。引用为原文，链接为 GitHub issue ID。

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | **Atlas merge → heap corruption crash** — loop detection 触发 Atlas 合并时 malloc 元数据被改写 | [#919](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/919): "When I have a *Merge detected, the program crashes, returning a malloc(): corrupted top size, then an aborted." | 🔴 | 跑长 session 时禁用 loop closure 或 fork [`thien94/ORB_SLAM3`](https://github.com/thien94/ORB_SLAM3) 已修若干 merge race；不要在生产用主仓 Atlas |
| 2 | **G2oTypes.cc null-pointer segfault in monocular-inertial** — `EdgePriorPoseImu` 构造时 `pFp->mpcpi` 为 null 但代码只打 warning 不防御 | [#967](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/967): "It crashes because the pointer 'c' is null, so in the caller 'pFp->mpcpi' is null" | 🔴 | 多 IMU+cam dataset 切换时易触发；patch 加 null guard（社区 PR 未合）或避免动态切 dataset |
| 3 | **IMU 初始化失败 → "Empty IMU measurements vector"** — 即便 Kalibr 标定残差良好仍卡在初始化 | [#730](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/730): "IMU is not or recently initialized. Reseting active map..." 反复出现；30 fps 卷帘相机 + 49 Hz IMU | 🔴 | IMU ≥200 Hz 必备；用全局快门相机；硬件 trigger 同步；卷帘+低频 IMU 是 #1 翻车配置 |
| 4 | **Stereo 模式空特征帧 → segfault** — `Frame` 构造遇零 ORB 提前返回，`mfGridElementWidthInv` 等静态变量未初始化 | [#991](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/991): "Program crashes with segmentation fault or undefined behavior when accessing uninitialized grid variables" | 🟠 | 低光 / 白墙 / 黑帧入场即崩；前置帧质量过滤；不能依赖内部"无特征跳帧"语义 |
| 5 | **Build hell on Ubuntu 22.04 + Jetson aarch64** — Tracking.cc 编不过；g2o 先编成功后 ORB_SLAM3 自身崩 | [#996](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/996): "make[2]: *** [CMakeFiles/ORB_SLAM3.dir/build.make:93: CMakeFiles/ORB_SLAM3.dir/src/Tracking.cc.o] Error 1" on Jetson Orin Nano Ubuntu 22.04 aarch64 / kernel 5.15.148-tegra | 🟠 | Ubuntu 20.04 + GCC 9 是参考栈；22.04 / GCC 11+ / Eigen 3.4 / OpenCV 4.6+ 全部要 patch；用 Docker 锁版本 |
| 6 | **ROS 2 port = 社区 fork 拼图** — 主仓无 ROS 2 节点，用户只能挑 `zang09/ORB_SLAM3_ROS2` / `thien94/orb_slam3_ros` 等几个分叉，Humble 兼容靠 [#965](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/965) closed 但无主线合并 | [#869](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/869) "Could the version of ORBSLAM3-ROS be upgraded to ROS Noetic"; [#793](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/793) "How to publish pose topic on ROS2 with monocular-inertial node?"; [#960](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/960) oak-d ros2 bag | 🟠 | 选 fork 看活跃度 + 测试自家 sensor；不要混 ROS 1 桥；接受 fork pin-version 维护成本 |
| 7 | **Map merge → bad point cloud** — 合并后点云质量塌；timing 指标出 NaN | [#723](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/723) "Merging maps and bad point cloud"; [#489](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/489) NaN in REGISTER_TIMES | 🟡 | Atlas merge 在论文 demo 之外没经充分压测；多 session 长建图先脚本验证 metric 再上业务 |
| 8 | **Maintainer 静默 + 528 open issues** — Issue #1001 直接说"one of the worst repository I have ever tried to work with"；PR #798 22 条评论 23 年开到现在未合 | [#1001](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/1001): "Bad documentation, bad code. I think that 500+ open issues says everything"; [PR #798](https://github.com/UZ-SLAMLab/ORB_SLAM3/pull/798) "[Stable Build]: Corrects major bugs, and creates buildable repo" 未合 | 🟡 | 视主仓为"参考实现 + 论文 reproducer"；生产部署用社区 fork (`thien94/...`)，自维 patch + Docker |

**Repo health signal**: 8.6k ★ / 538 open / closed unknown but >800 累计 / forks 3.1k / 30 PR open / last commit 2024-07（视同冻结）/ PR #999 (2026-03) 最新但 spam-ish

**讀者實務含義**:
1. ORB-SLAM3 是 *2021 论文实现*，不是 *2026 活跃产品*——选它等于选 fork 文化 + Docker 版本锁 + 自维 IMU init / Atlas merge patch。
2. 工作包络以 IMU 200 Hz + 全局快门 stereo + 充足纹理 + Ubuntu 20.04 GCC 9 栈为入场费；任一项偏离都进 #730/#967/#919/#991 已知踩坑区。
3. Atlas multi-map 是论文卖点但是踩坑重灾区；长 session 生产场景先评 [thien94 fork](https://github.com/thien94/ORB_SLAM3) 或考虑 OpenVINS / VINS-Fusion + 自接 PGO。

---

## 8 · 比较 & 面试 Tip

| 栈 | 模式 | 前端 | IMU | 闭环 | aerial? |
|---|---|---|---|---|---|
| **ORB-SLAM3** | mono/stereo/RGBD/+IMU | ORB | tight (preint) | DBoW2+Atlas | ❌ 室内 |
| VINS-Fusion | mono/stereo+IMU | KLT | tight | DBoW2 | ✅ |
| OpenVINS | mono/stereo+IMU | KLT | tight (MSCKF) | 较弱 | ✅ |
| DSO ([dissection](./direct_methods_dso_lsd.md)) | mono | direct | 弱 | 弱 | ❌ |
| DROID-SLAM | mono/stereo/RGBD | learned | 弱 | learned | ❌ |
| VGGT | N-view RGB | feed-forward | — | n/a | ❌ 速率不对 |

> **🎤 Interview Tip.** "我们机器人选 ORB-SLAM3 还是 VINS-Fusion？" —— 正确答："看 embodiment 和控制速率。ORB-SLAM3 适合室内 RGB-D / manipulation / AR，多 session 重要的场景；VINS-Fusion 适合 aerial / 高速运动，tracking 延迟把权重压过去。" 错答："ORB-SLAM3 更通用，所以选它" —— 通用是*codebase* 的特征，不是*工作包络*的特征。

---

## Boundary

- Aerial 实时 VIO（VINS / OpenVINS / DROID at 200 Hz） → [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/overview.md)。这里不重写。
- "VGGT vs VIO" 跨 embodiment → [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)。
- Direct methods（DSO / LSD） → [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md)。
- Kalibr / 标定 → [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md)。
- 3DGS SLAM backend → [`foundations/3dgs-family/gs_slam_dissection.md`](../3dgs-family/gs_slam_dissection.md)。

---

## References

- ORB-SLAM3 —— Campos et al. *T-RO 2021* · https://arxiv.org/abs/2007.11898
- ORB-SLAM —— Mur-Artal et al. *T-RO 2015* · https://arxiv.org/abs/1502.00956
- ORB-SLAM2 —— Mur-Artal, Tardós *T-RO 2017* · https://arxiv.org/abs/1610.06475
- ORB —— Rublee et al. *ICCV 2011*；DBoW2 —— Gálvez-López, Tardós *T-RO 2012*
- IMU 预积分 —— Forster et al. *RSS 2015* · https://arxiv.org/abs/1512.02363
- Code —— https://github.com/UZ-SLAMLab/ORB_SLAM3

---

[← Back to Classical SLAM](./overview.md)
