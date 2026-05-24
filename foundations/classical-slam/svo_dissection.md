<!-- ontology-5axis
problem: Semi-direct VO / VIO / VI-SLAM (SVO-Pro adds loop closure via iSAM2)
representation: Sparse features (tracking) + depth filter dense map + sliding-window keyframes
sensor: Mono / Stereo / Fisheye / catadioptric + IMU (Pro 起)
paradigm: Hybrid: sparse-feature alignment (Direct-style) + reprojection BA (Indirect-style) + depth filter
time: Filter-streaming (depth filter) + Fixed-lag smoother (Pro) + Incremental smoother (Pro VI-SLAM via iSAM2)
ref: ../../cheat-sheet/ontology.md §2 (Semi-direct VO) · §7 (UZH RPG lineage)
-->

# SVO Dissection (Semi-Direct Visual Odometry 解构)

> **Published:** SVO 1.0 — Forster, Pizzoli, Scaramuzza. *ICRA 2014* · SVO 2.0 — Forster et al. *IEEE T-RO 2017* · SVO-Pro — Scaramuzza et al. *RAL/ICRA 2021* (UZH Robotics & Perception Group)
> **Code:**
> - 原 SVO: https://github.com/uzh-rpg/rpg_svo（~3k ★，semi-frozen）
> - **SVO-Pro**: https://github.com/uzh-rpg/rpg_svo_pro_open（1.6k ★，57 open issues，GPL-3.0，**+ 商业 license available**）
> **核心定位:** SVO 是 *Direct vs Indirect 战争之外的第三条路*。**用 sparse 特征做 pose 对齐（像 Direct）+ 用 reprojection 做 map 优化（像 Indirect）**。结果：在 embedded CPU 上能跑 200 fps，**aerial drone 的首选 mono VO baseline**。SVO-Pro (2021) 补齐 IMU + loop closure + iSAM2 backend，等效于 *aerial-tuned 的 ORB-SLAM3*。

**Status:** v1。`UNVERIFIED` 数字 inline 标注；GitHub-validated pitfalls 锚 atlas。
**TL;DR:** Forster 选了 *worst of both worlds 还是 best of both worlds* 的赌注 —— **跟踪阶段不算描述子，直接 image alignment 找特征对应；建图阶段用 depth filter + reprojection BA**。这让 SVO 跑得**比 ORB-SLAM 快 5×**（200 fps vs 30 fps mono），**比 DSO 收敛半径大**（特征 align 比纯 photometric 鲁棒），但代价是 **mapping 质量靠 depth filter 收敛**（深度不稳定 = 漂得快）。**aerial drone 社区把它做成事实标准**；地面机器人 / AR 则继续用 ORB-SLAM3。

---

## 1 · X-Ray — 与 ORB-SLAM3 / DSO 的三方对照

### 1.1 一句话定位 — 真正的 hybrid

> **DSO       = photometric residual on raw pixels（Direct, slow & precise, no loop）**
> **ORB-SLAM3 = reprojection residual on ORB keypoints（Indirect, full stack, 30 fps）**
> **SVO       = sparse feature align (no descriptor!) → reprojection BA on depth-filter points（Hybrid, 200 fps embedded）**

```
   ┌───────────────────────────────────────────────────────────────────────┐
   │  Direct (DSO)                vs  Semi-direct (SVO)        vs Indirect (ORB)│
   ├───────────────────────────────────────────────────────────────────────┤
   │  ✗ keypoints                 │  ✓ FAST corners              │  ✓ ORB         │
   │  ✗ descriptors               │  ✗ NO descriptors!           │  ✓ BRIEF 256-bit│
   │  ✓ photometric residual      │  ✓ photometric align (track) │  ✗ reproj only │
   │  ✗ reprojection              │  ✓ reproj BA (mapping)       │  ✓ reproj BA   │
   │  Depth: per-point inv depth  │  Depth: depth filter (recursive Bayes) │ Depth: triangulate │
   │  Loop: ❌                    │  Loop: ✅ DBoW2 (Pro)         │  Loop: ✅ DBoW2 │
   │  IMU: ❌（DM-VIO fork）      │  IMU: ✅ (2.0 起, Pro)         │  IMU: ✅ tight │
   │  Multi-map: ❌                │  Multi-map: ❌                │  Atlas ✅      │
   │  Rate: ~30 Hz                │  Rate: **~200 fps embedded** │  ~30 Hz        │
   │                                                                          │
   │  ⇒ 高梯度精度战              │  ⇒ aerial drone 速度战         │  ⇒ 室内通用栈   │
   └───────────────────────────────────────────────────────────────────────┘
```

### 1.2 ⚡ Eureka Moment

> **检测要特征，匹配不要描述子 —— 用 image alignment 直接 warp 特征 patch 找对应。**
> **跟踪阶段像 Direct（光度），建图阶段像 Indirect（reprojection）。**
> **结果：embedded CPU 上跑出 200 fps，又同时保留 BA 的 metric consistency。**

ORB-SLAM 之所以慢，~50% 时间在 ORB descriptor 提取 + Hamming 匹配 + RANSAC outlier。SVO 的洞见：**FAST corner 抽出来已经够定位了；匹配可以直接用图像 patch 做 warp + 光度 align**，不用算 BRIEF。这等于把 ORB-SLAM 前端 30 ms 压到 5 ms。

但 SVO 也付出代价：**没有描述子 = 没有 DBoW2 内置闭环**。SVO 1.0 / 2.0 没有 loop closure，**SVO-Pro (2021) 才补上**（用 BRISK + DBoW2 + iSAM2 backend）。

**Aerial drone 社区的赌注**：在 100 g 级 drone 上，**100 ms loop 延迟 ≫ 200 fps 跟踪的损失**。SVO 是赢家。**ORB-SLAM3 室内的赌注**：tracking 30 fps 够了，但闭环 + Atlas multi-session 不可缺。两个 embodiment 选不同 winner。

### 1.3 SVO-Pro 架构（2021）

```
   SVO-Pro 架构 — 三阶段 pipeline + 可选 backend
   
   ┌────────────────────────────────────────────────────────────────┐
   │   📷 Camera (mono/stereo/fisheye, active exposure ctrl)         │
   │   📐 IMU (≥200 Hz, optional)                                    │
   │            │                                                    │
   │            ▼                                                    │
   │   ┌─────────────────────────────────────────┐                   │
   │   │  ① SPARSE IMAGE ALIGNMENT (pose only)  │                   │
   │   │  对每一新帧，warp 上一 KF 的 patches      │                   │
   │   │  最小化 photometric residual on patches  │                   │
   │   │  Coarse-to-fine pyramid (4 level)        │                   │
   │   │  ⇒ 5 ms · 200 fps embedded               │                   │
   │   └────────────────┬────────────────────────┘                   │
   │                    │ pose prior                                  │
   │                    ▼                                             │
   │   ┌─────────────────────────────────────────┐                   │
   │   │  ② FEATURE ALIGNMENT (subpixel refine) │                   │
   │   │  对每个 visible map point，做 patch     │                   │
   │   │  align 找 2D 子像素位置                  │                   │
   │   │  (像 Direct，但只在 sparse FAST 处)      │                   │
   │   └────────────────┬────────────────────────┘                   │
   │                    │ 2D-3D correspondences                       │
   │                    ▼                                             │
   │   ┌─────────────────────────────────────────┐                   │
   │   │  ③ POSE + STRUCTURE REFINE (BA-style)  │                   │
   │   │  Motion-only BA (reprojection)          │                   │
   │   │  Local structure BA on co-visible KFs   │                   │
   │   └────────────────┬────────────────────────┘                   │
   │                    │ refined pose + map                          │
   │                    ▼                                             │
   │   ┌─────────────────────────────────────────┐                   │
   │   │  ④ DEPTH FILTER (mapping)              │                   │
   │   │  每个新 candidate point 维护             │                   │
   │   │  Gaussian + Uniform mixture inverse-depth │                 │
   │   │  recursive Bayes update on each obs     │                   │
   │   │  收敛后转 map point                       │                   │
   │   └─────────────────────────────────────────┘                   │
   │                                                                  │
   │   ─────────── Optional backends ────────────                     │
   │   ⑤a  Visual-Inertial sliding-window optim (OKVIS-style)        │
   │   ⑤b  VI-SLAM with iSAM2 (incremental smoother, real-time)      │
   │   ⑤c  Loop closure: BRISK + DBoW2 + PGO                         │
   │                                                                  │
   └────────────────────────────────────────────────────────────────┘
   
   💡 关键洞见：SVO 把"特征 + 描述子 + 匹配"三件套**砍掉中间一件**。
      FAST corner 留着（要精确角点位置），描述子去掉（patch warp 代替匹配），
      reprojection BA 留着（保 metric consistency）。
```

---

## 2 · 数学核心

### 📌 Napkin Formula — Semi-direct Residual 双层

```
   ① Stage 1 — Sparse image alignment（跟踪阶段，photometric）
      
      T*  =  argmin_T   Σ_p ‖ I_new(π(T · X_p)) − I_ref(p) ‖²
      
      仅对 sparse FAST corner 的 4×4 patch 做 warp，**不优化结构**。
      跟 DSO 一样 photometric，但**只在 sparse 点上**而非 dense 高梯度像素。
      ⇒ 收敛半径在两者之间：比 dense direct 大、比 ORB feature matching 小
   
   ② Stage 2 — Feature alignment（子像素精炼）
      
      u_p*  =  argmin_u  ‖ I_new(u) − I_ref(p) ‖²    (small affine warp)
      
      固定 pose，每个点找子像素位置 → 给 BA 一个精确 2D 观测。
   
   ③ Stage 3 — Motion + structure BA（建图阶段，reprojection）
      
      {T*, X*}  =  argmin   Σ ρ( ‖ u_p − π(T · X_p) ‖_Σ )    (Huber)
      
      跟 ORB-SLAM 完全一样的 reprojection BA。
   
   ④ Depth filter（recursive Bayes，per-point）
      
      p(ρ_p | obs_1..N)  =  η · p(obs_N | ρ_p) · p(ρ_p | obs_1..N-1)
                          
      Mixture: Gaussian (inlier) + Uniform (outlier)
      ⇒ 论文 Vogiatzis-Hernández 2011 模型
```

**直觉**：SVO 不是"半 direct"在 *残差类型* 上模糊 —— 它在 *管线阶段* 上分割：
- **跟踪**（每帧）用 direct-style alignment（快、不要描述子）
- **建图**（每 KF）用 indirect-style reprojection BA（精、metric）
- **深度初始化**用 depth filter（recursive，不需 stereo baseline）

这是 ORB-SLAM3 和 DSO 之间真正的 *第三条路*，不是简单混合。

### 2.1 Depth Filter — SVO 的秘方

```
   传统 mono SLAM 初始化新点：
      ─── 需要 ≥2 KF 的 baseline → triangulate (closed-form)
      ─── 三角化精度差时 outlier 多 → RANSAC tax
   
   SVO depth filter：
      ─── 每个 candidate 一上来就开始 recursive Bayes
      ─── Gaussian + Uniform mixture: inlier vs outlier 自动加权
      ─── 收敛后转 mature map point；不收敛的自然过滤
      ─── ⇒ 不需要等 stereo baseline；连续观测就开始收敛
   
   → 这是 SVO 能跑 mono + 200 fps 的关键之一
   → 灵感来自 Vogiatzis & Hernández 2011（probabilistic depth fusion for 3D recon）
```

---

## 3 · 📍 研究全景时间线 — UZH RPG 与 aerial 路线

```
2007       2011       2014                 2017                 2021                 2024+
PTAM ────► DTAM ────► SVO (ICRA) ────────► SVO 2.0 (T-RO) ───► SVO-Pro (RAL/ICRA) ►   ──┐
(features) (dense     │                    + IMU + omni cam     + iSAM2 backend         │
           direct)    │                                         + DBoW2 loop closure    │
                      │                                         + GitHub release         │
                      │                                                                  │
                      ├──► ROVIO (2015, MSCKF filter)                                    │
                      ├──► OKVIS (Leutenegger 2015) ─► VINS-Mono (Qin & Shen 2018) ─────┤
                      ├──► OpenVINS (2019, Geneva et al., MSCKF)                         │
                      └──► DSO (2018, TUM Cremers) — *parallel direct lineage*           │
                                                                                          ▼
   Aerial timeline                                                              [2026 hybrid]
   ────────────────────────────────────────────────────────────────────►   Flash-Mono /
   SVO ─► SVO 2.0 ─► SVO-Pro ─► VINS-Fusion ─► OpenVINS                     SLAM3R /
                                                                            EC3R-SLAM /
   UZH RPG 实验室：Scaramuzza 组 = drone VIO 的事实标准源；                    learned + classical
   一脉相承：Forster (SVO) → Loianno (UPenn drone) → Cadena (ETH) → 
            Geneva (OpenVINS) → Zhang (HKUST aerial benchmark)
   
   2026 现状：SVO-Pro 在 aerial drone 仍活；地面机器人转 ORB-SLAM3；
              研究前沿转 hybrid / feed-forward；UZH 自己也转向 event camera + learned
```

**为什么 SVO 出现在 ICRA 2014（同年 LSD-SLAM ECCV 2014）？** 因为 2013 后 micro-aerial vehicle 革命（Pixhawk + AscTec + DJI），需要 100 g 级 onboard mono VO；ORB-SLAM 30 fps 不够、DSO 太慢、KLT-based VO 不够准。Forster 找到 sparse photometric align 这条夹缝。

---

## 4 · 玩具例子：带数字走一遍

EuRoC MAV `MH_01_easy`（752×480 mono、20 Hz）。**Intel NUC i7 测**（论文报告，`UNVERIFIED`）：

| 步骤 | SVO 2.0 时间 | ORB-SLAM3 mono 时间 | DSO mono 时间 |
|---|---|---|---|
| Feature 提取 | ~1 ms (FAST only) | ~8 ms (ORB pyramid) | ~5 ms (point selection) |
| Description / Matching | ❌ skip | ~3 ms (BRIEF match) | ❌ skip |
| Image alignment / Tracking | ~3 ms | ~5 ms (motion BA) | ~12 ms (multi-level direct) |
| Mapping (KF only, async) | ~30 ms/KF | ~100 ms/KF | ~80 ms/KF |
| **总 tracking** | **~5 ms** | **~17 ms** | **~17 ms** |
| **可达 frame rate** | **~200 fps** | ~60 fps | ~60 fps |

实测 ATE（EuRoC MAV，UZH benchmark）：
- SVO 2.0 mono+IMU：~0.3 m drift on `MH_01` `UNVERIFIED`
- ORB-SLAM3 mono+IMU：~0.04 m drift（更精）
- VINS-Mono：~0.06 m

⇒ **SVO 不是最准，是最快**。对 aerial 高速控制（200 Hz IMU loop），延迟 → jitter → 控不稳；用 SVO 换 30% 精度损失保 200 fps，aerial 接受这个交易。

---

## 5 · 工程：UZH RPG 文化与代码栈

**SVO 历史栈** (`uzh-rpg/rpg_svo`, ~3k ★)：
- 2014 release，配合 ICRA paper；C++11；ROS Indigo 时代
- 2016-2017 学界广泛 fork；很多 thesis 基础
- **后期 semi-frozen**：主 release 走 SVO-Pro

**SVO-Pro** (`uzh-rpg/rpg_svo_pro_open`, 1.6k ★)：
- 2021 release（GPL-3.0 + 商业 license）
- 包含完整三模式：VO / VIO / VI-SLAM（iSAM2 backend）
- ROS 1 支持；ROS 2 社区 fork（[#70](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/70) 请求 arrch64 未合）
- 商业版可联系 UZH technology transfer office

**周边工具**（UZH RPG ecosystem 必备）：
- **Kalibr**（Furgale 2013, ETH/UZH）—— camera-IMU 时间 + 外参 + 内参标定金标准；任何 VIO 部署的入场费
- **rpg_trajectory_evaluation**（Zhang & Scaramuzza 2018）—— ATE/RPE 评测标准
- **rpg_information_field**（信息论 active perception 工具）

**与 OpenVINS / VINS-Fusion 的分工**：
- VINS-Fusion：港科技 Shen Shaojie 组，feature-based + IMU + GPS fusion，aerial / autonomous driving 通用
- OpenVINS：UDel Geneva et al., MSCKF filter，纯 VIO baseline
- SVO-Pro：UZH，semi-direct + 优秀 mono 性能 + 完整 backend，研究 + drone 部署

---

## 6 · 能力与失败模式

**出货场景:**
- **Micro-aerial vehicle**（100-500 g drone）—— UZH 内部 + ETH Vasarhelyi lab + Stanford Kress-Gazit lab 等学术 drone 平台 baseline
- **Embedded mono VO**（树莓派 / Jetson Nano 单 mono camera）—— 200 fps 跑得动
- **研究 mono 基线** —— "我们 propose XX 模块，base SVO 做 baseline"
- **Aerial benchmark replication** —— UZH 自家 benchmark 主要测它

**失败场景:**
- **大 baseline 立即匹配** —— 没描述子 → 跑 wide-baseline relocalization 不行，需重启
- **低纹理 / 白墙** —— FAST corner 找不出来 → tracking lost（DSO 的高梯度像素这时反而能用，但 DSO 收敛半径小没救）
- **强动态场景** —— depth filter 收敛会被动态物体污染
- **多 session** —— 没有 Atlas，无法接续
- **室内 RGB-D 任务** —— ORB-SLAM3 RGB-D mode 是事实默认；SVO 没有同等的 RGB-D 路径
- **HDR / 强光切换** —— sparse image alignment 不带 a/b affine 模型，比 DSO 还差

### 6.1 Hidden Assumptions（隐含假设）

- **足够 FAST corner** —— 没有 ORB 那样的多 detector fallback；FAST 失效就停
- **Depth filter 能收敛** —— 需连续观测 + 视差累积；hover 不动 / 纯旋转时 depth 不收敛
- **Patch warp 假设小旋转 + 小尺度变化** —— 快速 yaw（>2 rad/s）让 patch warp 模型崩
- **IMU 高频 + 同步** —— SVO-Pro VI 模式假设 200 Hz IMU + 硬件 sync；与 ORB-SLAM3 / VINS 同样依赖 Kalibr
- **Loop closure 仅 BRISK + DBoW2 (Pro)** —— 比 ORB-SLAM3 的 DBoW2-on-ORB 弱，跨光照 reloc 不稳

### 6.2 GitHub 实地失败（atlas 联动）

- **GitHub-validated**：**57 open issues + maintainer 半静默** —— Issue #76 "Drifting issue"（2025-11 open）+ #69 "Relocalization success will cause bias jump"（2024-05）显示 VI-SLAM 模式 reloc bias 跳变是已知未修问题；产品部署要 fork + 自维 patch；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**ROS 2 / arrch64 / 现代 build 全部社区 fork 拼图** —— Issue [#70](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/70)（arrch64 支持，未实现）+ [#72](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/72) `load_ui128` build error 反映与 ORB-SLAM3 同病：研究 codebase 时代固化，靠社区 fork 跟进 platform，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**Monocular init 失败常见** —— Issue [#75](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/75) "Unsuccessfully run SVO in monocular mode" + [#66](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/66) "Wrong estimation when running on webcam" 反映 mono-only depth filter 对相机参数 / 同步 / 场景纹理敏感；要先用 EuRoC / stereo+IMU 跑通才能换 mono。

---

## 7 · 7.5 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 扫描 57 个 open issue，分布于 init failure / build / drift / ROS 平台支持四大类。引用 issue 链接 + 原文。

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | **Mono 模式初始化失败** — 单目跑不通，依赖场景纹理 + 摄像机运动初值 | [#75](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/75) "Unsuccessfully run SVO in monocular mode" (Mar 2025 open); [#66](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/66) "Wrong estimation when running on webcam" | 🔴 | 先在 EuRoC stereo+IMU 上跑通再换 mono；初始化需 lateral motion；webcam 通常缺标定 |
| 2 | **VI-SLAM 重定位 bias 跳变** — reloc 成功后 IMU bias 突变 | [#69](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/69) "Relocalization success will cause bias jump" (May 2024) | 🔴 | 长 session aerial 用要锁 IMU bias 更新 + 后处理对齐；产品部署有风险 |
| 3 | **长 session drifting** — 持续累积漂移，闭环未必兜底 | [#76](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/76) "Drifting issue" (Nov 2025 open) | 🔴 | 必须开 SVO-Pro loop closure（DBoW2）；短 trajectory 才能避免 |
| 4 | **Build hell on modern compiler** — `load_ui128` 等 SIMD intrinsics 不识别 | [#72](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/72) "error: 'load_ui128' was not declared in this scope" (Dec 2024) | 🟠 | GCC 9 + Ubuntu 20.04 是参考栈；GCC 11+/aarch64 要 patch SIMD wrapper |
| 5 | **arrch64 / Jetson 移植无主仓支持** — drone 主力平台缺官方支持 | [#70](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/70) "Make it available on arrch64" (Oct 2024 unanswered) | 🟠 | 用社区 fork 或自移植；Jetson Orin Nano + Ubuntu 20.04 用 GCC 9 跨编 |
| 6 | **Estimator marginalization fail** — sliding-window backend 数值不稳 | [#67](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/67) "test estimator failed with marginalization" (May 2024) | 🟠 | VI-SLAM 模式要用 iSAM2 backend 而非 sliding-window；论文配置 + EuRoC 才稳 |
| 7 | **API 文档稀疏 — pose covariance 怎么拿** | [#68](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/68) "How to get the pose covariance" | 🟡 | 要读 estimator 源码自己 expose；不要假设 ROS topic 自带 cov |
| 8 | **ROS launch 启动崩** — `process has died` 启动失败 | [#61](https://github.com/uzh-rpg/rpg_svo_pro_open/issues/61) "Process has died after roslaunch" (Jan 2024) | 🟡 | 检查 yaml config 路径；多数 case 是 camera_info topic 命名不匹配 |

**Repo health signal**：原 SVO ~3k ★ frozen / SVO-Pro 1.6k ★ + 57 open issues / GPL-3.0 + 商业 license / last commit 不公开（master 历史 commit 数低）/ 商业版分流维护

**读者实务含义**：
1. SVO-Pro 是 *aerial drone 研究 codebase*，**不是 turnkey 产品**。Production drone（如 Skydio）走自研 + 闭源；学界用 SVO-Pro 做 baseline + 论文 prototype。
2. 工作包络：**aerial drone (100-500 g)** + **stereo+IMU 优先 / mono 谨慎** + **ROS 1 / Ubuntu 20.04** + **场景有纹理** + **<10 min session（长 session 走 loop closure）**。
3. 选 SVO-Pro 的判断标准 = **是否真的需要 200 fps + onboard CPU**。如果不是 aerial，ORB-SLAM3 / VINS-Fusion / OpenVINS 任一项都更稳。

---

## 8 · 比较 & 面试 Tip

| 栈 | Paradigm | 跟踪速度 | 闭环 | IMU | 多 session | aerial? | 室内默认? |
|---|---|---|---|---|---|---|---|
| **SVO / SVO-Pro** | Semi-direct | ⭐ ~200 fps mono | ✅（Pro 起） | ✅（2.0 起） | ❌ | ⭐ aerial 标配 | ❌ |
| **ORB-SLAM3** | Indirect | ~30 fps | ✅ DBoW2 | ✅ tight | ✅ Atlas | ❌ 太慢 | ⭐ 默认 |
| **DSO** | Direct | ~30 fps | ❌ | ❌（DM-VIO fork） | ❌ | ❌ | ❌ |
| **VINS-Fusion** | Indirect | ~30-50 fps | ✅ DBoW2 | ✅ tight | △ | ⭐ aerial | ⭐ AD |
| **OpenVINS** | Filter (MSCKF) | ~30-100 fps | 弱 | ✅ tight | ❌ | ⭐ aerial baseline | ❌ |
| **DROID-SLAM** | Learned | GPU only | ✅（学的） | △ | ❌ | ❌（GPU 重） | ❌ |
| **VGGT** | Feed-forward | offline batch | n/a | ❌ | n/a | ❌ | ❌ |

> **🎤 Interview Tip：「我们这台 250 g drone 上选 SVO-Pro 还是 VINS-Fusion？」**
>
> **正确答**：「先看控制 loop 频率。如果 IMU control loop ≥200 Hz 而且 onboard 只有 ARM CPU、需 mono 模式，**SVO-Pro 是首选** —— 200 fps tracking + sparse image alignment 让它在 jitter-sensitive 控制场景压 ORB-SLAM3 / VINS 一头。如果有 stereo + Jetson Xavier 以上 + 需要 loop closure 全功能 + 想要更成熟的 ROS 接口和社区支持，**VINS-Fusion 更稳**（GPS fusion / multi-sensor / 港科技维护更活跃）。**ORB-SLAM3 太慢**，30 fps 在 aerial 控制环里加 jitter 不接受。」
>
> **错答**：「都差不多，选 ORB-SLAM3 因为它最有名」—— 这是把*室内 manipulation 的事实默认*错误外推到 *aerial 200 fps 控制*。Embodiment 决定选型，不是知名度。

> **追问**：「为什么 SVO 不用描述子？」
> **答**：「Forster 的核心判断：描述子（BRIEF/ORB）50% 时间为了**跨光照 / 大基线 reloc** 设计；但 frame-to-frame 跟踪根本不需要这个鲁棒性 —— patch warp + 光度 align 就够了。描述子留到必要的 reloc 时再算（SVO-Pro 用 BRISK + DBoW2 做 loop closure 是这时才提描述子）。换言之 —— **每一帧都算描述子是过度工程**。这个判断只在 aerial 场景（小基线、frame-to-frame 多）成立；室内 RGB-D / AR（大跳变 reloc 多）则相反。」

---

## 9 · Falsifiable Predictions（可证伪预测）

| # | 预测（2026-2027） | Falsifier |
|---|---|---|
| 1 | SVO-Pro 仍是 **2027 aerial mono VIO 论文 baseline 第一名**（出现频次 > ORB-SLAM3 mono in aerial papers） | 2027 CVPR/ICRA/RAL aerial-VIO papers 大多基线换成 ORB-SLAM3 mono 或别的 |
| 2 | 主仓 `rpg_svo_pro_open` 2026-2027 **不会** merge ROS 2 主线支持；社区 fork 继续分散维护 | ROS 2 主仓 release 出现 |
| 3 | UZH RPG 实验室未来 12 个月**会**发**至少一篇** event camera + SVO-style 论文（继 EVO/Ultimate-SLAM 路线） | UZH RPG 没发 event-VIO 系新工作 |
| 4 | Aerial drone 产品（>1k units shipped, e.g. Skydio）不会**直接** ship SVO-Pro 内核；而是**借用思想**走闭源自研 | Skydio / DJI / Parrot 公布 BOM 含 SVO-Pro |
| 5 | 3R-SLAM Hybrid (Flash-Mono / SLAM3R) **不会**在 2027 前击败 SVO-Pro 在 100 g 级 onboard CPU drone 的 frame rate（200 fps）—— 因为 feed-forward backbone GPU 重 | Flash-Mono 在 ARM CPU 100 g drone 上跑出 ≥150 fps |

---

## 10 · For the Reader（读者实务）

**如果你正在 ...**
- ... **做 aerial drone mono VIO 项目** → SVO-Pro 是首选 baseline；先在 EuRoC 跑通 stereo+IMU，再切 mono；硬件用 global-shutter + 同步 IMU（Kalibr 标）
- ... **做 ground robot / manipulation** → 别选 SVO，选 ORB-SLAM3（Atlas + RGB-D + 多模态）
- ... **要 SVO 加 ROS 2** → 用社区 fork（搜 `svo_pro_ros2`）；不要等主仓
- ... **要 SVO 上 Jetson Orin Nano / arrch64** → 看 issue #70 + 自己交叉编；GCC 9 + Ubuntu 20.04 docker
- ... **理解 semi-direct method 设计哲学** → 读 Forster 2017 T-RO §3-4 + 这篇 dissection §1-2
- ... **想看 UZH RPG 后续路线** → event camera VIO (Ultimate-SLAM, EVO)、learned drone control、neural radiance for drone NeRF
- ... **找 VIO 学术 benchmark** → UZH benchmark suite (`rpg_trajectory_evaluation`) + Kalibr 是入场费

---

## 11 · References

- **SVO 1.0** — Forster, Pizzoli, Scaramuzza. *ICRA 2014*（原始 semi-direct paper）
- **SVO 2.0** — Forster, Zhang, Gassner, Werlberger, Scaramuzza. *IEEE T-RO 2017* —— + IMU, fisheye, multi-camera
- **SVO-Pro** — Scaramuzza et al. *RAL/ICRA 2021* —— full VIO / VI-SLAM, iSAM2 backend, DBoW2 loop
- **Depth filter** — Vogiatzis & Hernández. *Image and Vision Computing* 2011（recursive Bayesian depth fusion）
- **IMU preintegration**（SVO-Pro VI 用）— Forster, Carlone, Dellaert, Scaramuzza. *RSS 2015 / T-RO 2017* · https://arxiv.org/abs/1512.02363
- **Cadena SLAM survey** — Cadena et al. *IEEE T-RO 2016* · https://arxiv.org/abs/1606.05830（Semi-direct 分类经典 ref）
- **Kalibr** — Furgale, Rehder, Siegwart. *IROS 2013*（VIO 标定金标准）
- **rpg_trajectory_evaluation** — Zhang & Scaramuzza. *IROS 2018*（ATE/RPE 评测标准）
- **Code (original)** — https://github.com/uzh-rpg/rpg_svo（~3k ★, semi-frozen）
- **Code (Pro)** — https://github.com/uzh-rpg/rpg_svo_pro_open（1.6k ★, GPL-3.0 + 商业 license）

---

## 12 · Boundary（与相邻文件的分工）

这一篇**只管 SVO / SVO-Pro**（semi-direct VO 的代表）。

- **ORB-SLAM3**（indirect VO 对照） → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md)
- **DSO**（direct VO 对照） → [`./dso_dissection.md`](./dso_dissection.md)
- **Direct method 合并对比**（LSD + DSO） → [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md)
- **GitHub-validated 失败 atlas** → [`./github_failure_atlas.md`](./github_failure_atlas.md)
- **PnP / DLT 几何基础** → [`./pnp_dlt_primer.md`](./pnp_dlt_primer.md)
- **Aerial 实时 VIO 全家桶**（VINS / OpenVINS / DROID 与 SVO 在 aerial 场景的对比） → [`../../embodiments/aerial/vio/overview.md`](../../embodiments/aerial/vio/overview.md)
- **VINS-Fusion vs ORB-SLAM3 代码层对比** → [`../../crossing/slam-vio-migration/orb_slam3_vs_vins_fusion_code_comparison.md`](../../crossing/slam-vio-migration/orb_slam3_vs_vins_fusion_code_comparison.md)
- **IMU 预积分理论**（SVO-Pro VI 用） → [`../spatial-math/`](../spatial-math/)
- **3DGS-SLAM 后端**（与 SVO 同 era 但走不同路） → [`../3dgs-family/gs_slam_dissection.md`](../3dgs-family/gs_slam_dissection.md)
- **Ontology v3 Semi-direct VO subdivision** → [`../../cheat-sheet/ontology.md`](../../cheat-sheet/ontology.md) §2

---

[← Back to Classical SLAM](./overview.md) · [→ ORB-SLAM3 dissection](./orb_slam3_dissection.md) · [→ DSO dissection](./dso_dissection.md)
