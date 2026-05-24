<!-- ontology-5axis
problem: Direct VO (photometric) — no loop closure, no global map
representation: Sparse photometric points (~2000 active) + inverse depth + sliding window
sensor: Monocular RGB (photometric-calibrated; rolling shutter not supported)
paradigm: Geometric-Direct + Photometric BA + joint geometry/motion/photometric calibration
time: Fixed-lag Smoother (sliding window ~7 KFs)
ref: ../../cheat-sheet/ontology.md §2 (Direct VO) · §5.1 (BA) · §7 (DSO row, TRL 🔬)
-->

# DSO Dissection (Direct Sparse Odometry 解构)

> **Published:** arXiv 1607.02565 (2016) · *IEEE TPAMI 2018* · Engel, Koltun, Cremers (TUM CV Group + Intel Labs)
> **arXiv:** https://arxiv.org/abs/1607.02565 · **Code:** https://github.com/JakobEngel/dso（2.4k ★ · 922 fork · GPL-3.0 · 66 commits · master 最近 commit 2018-ish · 视同冻结）
> **核心定位:** *主流视觉 SLAM 没有走的那条路*。直接法跳过 keypoint，直接在原始像素亮度上最小化光度误差 —— 在富梯度场景下子像素精度赢，但光度标定强制、曝光变化致命、**完全没有闭环**。DSO 是经典直接 VO 的顶点；2018 之后注意力转向 learned-BA（DROID-SLAM）+ feed-forward dense（DUSt3R / VGGT）。

**Status:** v1。`UNVERIFIED` 数字 inline 标注；GitHub-validated pitfalls 锚 atlas。
**TL;DR:** DSO 证明视觉 SLAM 可以**不用描述子**，但代价是把 ORB-SLAM3 留给闭环的最后一公里**整段砍掉**。选 DSO 的人是为了**单目稠密初始化** + **低纹理高梯度场景**（如长走廊、HDR 室内）；选 ORB-SLAM3 的人是为了**多 session + 多模态 + 闭环**。两条路 2026 都没合流 —— 学界把希望挪给了 hybrid (3R-SLAM family) 和 feed-forward (VGGT)。

---

## 1 · X-Ray — 与 ORB-SLAM3 的架构对比

### 1.1 一句话差分

> **ORB-SLAM3 = ORB 特征 → 描述子匹配 → reprojection BA → DBoW2 闭环 → Atlas 多图**
> **DSO       = ~2000 个高梯度像素 → 直接 photometric BA on 滑窗 7 KFs → 没有闭环 → 没有 Atlas**

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  ORB-SLAM3 (Indirect)               vs  DSO (Direct)             │
   ├─────────────────────────────────────────────────────────────────┤
   │  ① ORB 提取 ~1000/frame · 8 ms     │  ① 选 ~2000 高梯度像素 · 5 ms │
   │  ② BRIEF 描述子匹配 · 3 ms          │  ② 无描述子 — 直接 warp     │
   │  ③ Reprojection error min          │  ③ Photometric error min    │
   │      ‖π(T·X) − u‖²                │      ‖I_j(π(T·X)) − I_i(u)‖² │
   │  ④ Local BA (~20 KF 滑窗)          │  ④ Photometric BA (7 KF 滑窗)│
   │  ⑤ DBoW2 闭环 + Atlas merge        │  ⑤ ❌ 无闭环 · 无 multi-map   │
   │  ⑥ IMU 选配（VI 模式）              │  ⑥ ❌ 无 IMU 支持（原仓）     │
   │  ⑦ Mono / Stereo / RGB-D           │  ⑦ Mono only（原仓）        │
   │                                                                  │
   │  入场费：ORB / DBoW2 / Atlas        │  入场费：**光度标定**（vignette │
   │           DBoW2 闭环训练            │            + 曝光 + γ）+ global   │
   │                                                                  │
   │  ⇒ 室内 manipulation / AR 默认      │  ⇒ 高梯度 + 已标定相机 实验场景  │
   └─────────────────────────────────────────────────────────────────┘
```

### 1.2 ⚡ Eureka Moment

> **跳过特征提取 —— ORB-SLAM 留 1% 的像素丢 99%；DSO 直接在原始亮度上跑优化。**
> **"keypoint" 是降维近似 —— 当你信任光度标定时，原始像素本身就是更好的 residual。**

直接法的根本主张：特征 SLAM 把 image 蒸馏成 keypoint 是**信息损失**。如果你愿意付出光度标定（vignetting + 曝光时间 + 非线性响应），你能直接拿亮度做 residual，**子像素精度免费送**、半稠密地图免费送、对低纹理场景更稳健。代价是 —— 你需要**永远精确**地拿到曝光值。

ORB-SLAM 的赌注：keypoint 抽象 + Hamming 距离 + 旋转不变足以在 messy real-world 取胜。
**DSO 的赌注**：精确光度模型 + 高梯度像素 + 滑窗优化精度更高。
**2026 实证**：ORB-SLAM 赢了 deployment；DSO 赢了精度（在它的小工作包络内）；hybrid（3R-SLAM）是真正的继任。

### 1.3 三线程？不，DSO 只有一个滑窗

```
    DSO 架构 — 单一 photometric pipeline，无 atlas，无闭环
   
   ┌──────────────────────────────────────────────────────────────┐
   │   📷 Mono camera @ 30 Hz（必须光度标定 — vignette/exposure/γ） │
   │            │                                                  │
   │            ▼                                                  │
   │   ┌─────────────────────────────────────────┐                 │
   │   │  ① POINT SELECTION                      │                 │
   │   │  选 ~2000 高梯度像素                       │                 │
   │   │  region-based 均匀分布（防角点局部聚团）   │                 │
   │   └────────────────┬────────────────────────┘                 │
   │                    │                                          │
   │                    ▼                                          │
   │   ┌─────────────────────────────────────────┐                 │
   │   │  ② DIRECT IMAGE ALIGNMENT (tracking)    │                 │
   │   │  对每一新帧 warp 滑窗内的点                │                 │
   │   │  Coarse-to-fine pyramid (4-5 层)         │                 │
   │   │  最小化光度残差 Σ ‖I_j(π) − I_i‖²          │                 │
   │   └────────────────┬────────────────────────┘                 │
   │                    │                                          │
   │                    ▼                                          │
   │   ┌─────────────────────────────────────────┐                 │
   │   │  ③ KEYFRAME DECISION                    │                 │
   │   │  几何 + 光度 + 平移阈值                    │                 │
   │   └────────────────┬────────────────────────┘                 │
   │                    │                                          │
   │                    ▼                                          │
   │   ┌─────────────────────────────────────────┐                 │
   │   │  ④ SLIDING WINDOW PHOTOMETRIC BA        │                 │
   │   │  联合优化:                                │                 │
   │   │   • 7 KF poses (SE3)                    │                 │
   │   │   • 每个 KF 的 affine 光度 (a_i, b_i)     │                 │
   │   │   • 每点 inverse depth ρ                │                 │
   │   │   • （可选）相机内参 / vignetting        │                 │
   │   │  Gauss-Newton + Schur 边化 depth        │                 │
   │   │  最老 KF marginalize 出窗（FEJ）         │                 │
   │   └────────────────┬────────────────────────┘                 │
   │                    │                                          │
   │                    ▼                                          │
   │   ┌─────────────────────────────────────────┐                 │
   │   │  ⑤ POINT MANAGEMENT                     │                 │
   │   │  immature → mature (depth 收敛)          │                 │
   │   │  outlier cull / marginalize             │                 │
   │   └─────────────────────────────────────────┘                 │
   │                                                                │
   │   ❌ 无 loop closure       ❌ 无 place recognition              │
   │   ❌ 无 Atlas multi-map    ❌ 无 IMU integration（原仓）        │
   │                                                                │
   └──────────────────────────────────────────────────────────────┘
   
   💡 关键洞见：tracking + mapping 合并在一个 photometric BA 里 —— 
      ORB-SLAM3 的「motion-only BA + local BA」二分在 DSO 里不存在。
```

---

## 2 · 数学核心

### 📌 Napkin Formula — Photometric Residual

```
   ORB-SLAM3 (Reprojection):
       r_ij = u_ij − π(T_i · X_j)                  ∈ ℝ²
       E = Σ ρ( ‖r_ij‖_Σ )                         (Huber)
   
   DSO (Photometric):
       r_ij = ( I_j(π(T_ji · X_i)) − b_j )         normalized intensity
            − (t_j · e^{a_j} / t_i · e^{a_i}) · ( I_i(p_i) − b_i )
       E = Σ_p Σ_obs w_p · ρ( ‖r‖_γ )              (Huber on intensity)
   
   联合变量：{ T_i ∈ SE(3),  (a_i, b_i),  ρ_p,  c_intrinsic }
              位姿        光度仿射          逆深度    内参（可选）
```

**直觉**：
- ORB 的 residual 单位是**像素**（reprojection），DSO 的 residual 单位是**亮度差**（光度）。
- DSO 多出来的 (a_i, b_i)：**每 KF 一对 affine brightness 参数** —— 这是 DSO 不用 ORB 直接吃 HDR 切换 / 自动曝光的方式（理论上）。
- 没有 (a, b) 联合优化时，自动曝光相机 1 秒内可以让 DSO drift 翻倍。**这就是 DSO 论文 §2 的核心贡献**。

### 2.1 一个公式，一个尺度（vs ORB-SLAM3 三尺度）

```
   ORB-SLAM3：同一 reprojection 公式跑三层 BA（motion-only / local / full）
   
   DSO       ：只有一个 photometric BA on 滑窗 7 KF
              ─── 没有 motion-only（tracking 也是 photometric align）
              ─── 没有 full BA（没有闭环触发，所以也没机会）
              ─── marginalization prior 是唯一历史承载
   
   ⇒ 这是为什么 DSO 漂移会**单调累积** — 没有任何机制可以把误差「拉回去」。
     ORB-SLAM3 有闭环 → 几何修正；DSO 没有 → 只能希望滑窗够长 + FEJ 够稳。
```

---

## 3 · 📍 研究全景时间线 — Direct vs Indirect vs Semi-direct

```
2007        2011        2014                  2016         2017            2021+
PTAM ─────► DTAM ─────► LSD-SLAM ───────────► DSO ──────► ORB-SLAM2/3 ───► DROID-SLAM / VGGT
(features)  (dense      (semi-dense           (sparse      (features        (learned-BA /
            direct)     direct, ECCV 2014)    direct,      mature stack)    feed-forward)
                        │                     TPAMI 2018)
                        │
                        ├──► SVO (2014) ──────► SVO 2.0 (2017) ──► SVO-Pro (2021)
                        │    semi-direct       + IMU              + iSAM2 loop
                        │
                        └──► VINS-Mono (2018) — features + IMU (走 indirect 路)

   Direct lineage（亮度 residual）:   DTAM → LSD-SLAM → DSO  [frozen 2018]
   Indirect lineage（reprojection）:   PTAM → ORB-SLAM 1/2/3       [maintained-ish 2024-07]
   Semi-direct lineage（混合）:        SVO → SVO 2.0 → SVO-Pro    [UZH RPG, semi-active]
   
   Learned 继任：DROID-SLAM (2021) 把 BA 学出来；VGGT (CVPR 2025) 把 N-view 3D 学出来；
                3R-SLAM Hybrid (2025-2026) 把 learned 前端嫁接到 classical 后端。
   
   2026 现状：纯 Direct = research only；纯 Indirect = ORB-SLAM3 fork 文化；
              真实部署 = hybrid (FAST-LIVO2 / VINS-Fusion / 3R-SLAM family)
```

为什么 DSO 是终点不是中点？因为它要的"精确光度标定 + 全局曝光值"在真实相机栈（rolling shutter + auto-exposure + 温度漂焦距）里就是不可得的。**Engel 后来去了 Oculus，Cremers 团队转向 DROID-SLAM。** 没有继任者 = 不是没人想做，是物理学不让。

---

## 4 · 玩具例子：带数字走一遍

EuRoC MAV `MH_01_easy`（512×512 mono、20 Hz、室内、TUM mono dataset 光度标定）。x86 笔记本（Intel i7, 2018 测）`UNVERIFIED`：

| 步骤 | 时间/帧 |
|---|---|
| Point selection（~2000 候选） | ~5 ms |
| Direct image alignment（4-level pyramid，coarse-to-fine） | ~12 ms |
| KF 决策 + photometric BA（仅在 KF 上） | ~80 ms/KF（异步） |
| Marginalization + FEJ prior 更新 | ~10 ms/KF |
| **总 tracking（非 KF）** | **~17 ms** |
| **总（KF 帧）** | **~100 ms**（异步缓冲） |

对比 ORB-SLAM3 室内 30 Hz：tracking 17 ms / local mapping ~100 ms/KF（异步）。**数字几乎一样** —— DSO 不是更快，而是更**精确**（在它的小工作包络内）。

**实测 ATE（论文 EuRoC MAV 报告）**：DSO mono 室内 1-5 cm（在已光度标定 dataset 上）；ORB-SLAM3 stereo+IMU 2-10 cm（在所有 EuRoC 序列）。
**陷阱**：DSO 的 1 cm 是**光度标定可控** 下；丢掉 vignetting calibration，DSO 精度**直接掉 10×**（README 原话 "poor calibration can reduce accuracy by 10x"）。这不是 ORB-SLAM 的常规预算。

---

## 5 · 工程：为什么 DSO 是 *frozen at 2018*

GitHub 站点信号：

| 信号 | 值 | 解读 |
|---|---|---|
| ★ | 2.4k | 历史影响力 |
| Fork | 922 | 派生很多但很少 upstream |
| Commits | 66（master） | 历史性低 |
| Last commit | 2018-ish | 6+ 年无主线动作 |
| Open issues | 121 | maintainer 静默 |
| License | GPL-3.0 + 商业版（TUM） | 派生有许可成本 |
| ROS 2 port | ❌ 主仓无；社区零散 fork | 不能 plug-in modern stack |
| IMU 支持 | ❌ 原仓无 | DM-VIO 等 fork 加 IMU 但未合主 |

**Jakob Engel 去 Oculus 之后**，TUM Cremers 组的注意力**整段转向 deep learning 路线**（DROID-SLAM, DUSt3R, MASt3R, MonST3R 都源自 Cremers/Niessner 圈）。原仓视同**论文 reproducer**，不是产品。

**DM-VIO**（Engel/Cremers 2022，DSO + IMU 紧耦合）是非官方"DSO 2"，但同样维护稀疏。**TartanVO / DROID-SLAM** 才是 direct lineage 的真正延续 —— 但它们已经不是 direct 了，是 learned。

---

## 6 · 能力与失败模式

**出货场景:** 离线 mono 重建（已光度标定 dataset）；研究用 photometric baseline；TUM mono dataset 复现；少数学术机器人 demo（地面慢速 + 已标定相机）。

**失败场景:**
- **Rolling-shutter 相机** —— DSO README 明说"not recommended for rolling-shutter"。手机 / D435 / 一切 IMX477 类 sensor 排除。
- **自动曝光相机** —— 没有 a/b affine 模型外的 exposure metadata → drift 翻倍。
- **HDR / 强光切换** —— affine 模型只吃 first-order brightness 变化；窗户 / 阴影边界 fail。
- **大基线 / 快速旋转** —— direct image alignment 收敛半径远小于 ORB 描述子匹配；快速旋转直接 lose tracking。
- **闭环场景** —— 永远不会发生 →  漂移单调累积。回到起点的累积 yaw / position 误差不会被修。
- **多 session** —— 没有 Atlas。tracking lost = session 结束。
- **低帧率 (<10 fps)** —— photometric assumption 要求帧间 brightness 平滑过渡。

### 6.1 Hidden Assumptions（隐含假设）

- **光度标定永远精确** —— vignetting / exposure time / non-linear response 三件都得标定 + 在每帧时间戳上拿到正确曝光值。任何一件 drift 就是 catastrophic。
- **静态刚性世界** —— 跟 ORB-SLAM3 一样，动态物体污染光度模型。
- **Affine brightness 模型足够** —— 真实 HDR / 全局曝光变化超出 (a, b) 容量。
- **Global shutter** —— rolling shutter 让 warp 模型瞬间崩。
- **足够梯度像素** —— 全白墙 / 无纹理 → point selection 无候选 → tracking lost（feature SLAM 同样痛，但 DSO 没有 ORB fall-back）。
- **滑窗够长 + FEJ 够稳** —— 没有闭环兜底，滑窗 marginalization 必须永远健康。

### 6.2 GitHub 实地失败（atlas 联动）

- **GitHub-validated**：**121 open issues + 主仓 6+ 年无动作** —— issue tracker 全是 build / 内存安全 / 依赖更新（Pangolin v0.6 / Boost / SuiteSparse），无 maintainer 回复；社区 fork 各做各的；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：**use-after-free 内存安全 issue #269**（2024-03 open）—— C++ 历史代码的 segfault；产品部署必须自维 patch；ORB-SLAM3 #919 heap corruption 类似但至少有社区 fork (`thien94/...`)，DSO 没有这样的归一 fork。
- **GitHub-validated**：**光度标定文档缺失 issue #263 "Where photometric error is in this project"** —— 用户不知道光度模型在哪、怎么对自家相机标定；TUM mono dataset 的标定文件没法迁移到 D435 / iPhone；这印证了"光度标定永远精确"的隐含假设在生产线上**根本不成立**。

---

## 7 · 7.5 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 扫描 121 个 open issue，分布于 build hell / 光度标定不通 / memory safety / rolling-shutter 误用四大类。引用 issue 链接 + 原文。

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | **Build hell on modern Ubuntu / Boost** — Pangolin v0.6 / Boost 链接错误，Cmake 找不到符号 | [#261](https://github.com/JakobEngel/dso/issues/261) "Update readme to use Pangolin v0.6 with c++11"; [#260](https://github.com/JakobEngel/dso/issues/260) "Error while linking executable"; [#259](https://github.com/JakobEngel/dso/issues/259) Boost link errors | 🔴 | Docker 锁 Ubuntu 18.04 + GCC 7 + Pangolin v0.6；社区 fork（如 `JingeTu/DSO_for_Ubuntu`）可能跑通新版 |
| 2 | **Use-after-free / 内存安全** — C++ 历史代码 dangling pointer | [#269](https://github.com/JakobEngel/dso/issues/269) "use-after-free issues etc." (Mar 2024 open, no maintainer reply) | 🔴 | 长 session 跑 → 不可预期 crash；不能用于生产；要自打 ASAN + 修 |
| 3 | **光度标定不可迁移** — TUM mono 标定文件没法用在自家相机 | [#263](https://github.com/JakobEngel/dso/issues/263) "Where photometric error is in this project"（用户问光度模型在哪、怎么自标定，无回复） | 🔴 | 必须用 [TUM mono dataset photometric calibration 工具](https://github.com/tum-vision/mono_dataset_code)，全室内、慢速、需 chessboard pattern；自动曝光相机就放弃 |
| 4 | **Rolling-shutter 相机静默 drift** — README 警告但用户照用 | DSO README："Not recommended for rolling-shutter cameras"；用户在 RealSense D435 / iPhone 上跑后报怪 drift | 🟠 | Sony IMX296 / Basler ace 等 global-shutter 是入场费；rolling-shutter 直接拒绝 |
| 5 | **FPS 报告不一致 / 性能调测困难** — pseudo-realtime 模式时间统计混乱 | [#268](https://github.com/JakobEngel/dso/issues/268) "why the FPS and the time per frame are very different?" | 🟡 | 不能从 stdout 时间判断真实负载；必须用外部 profiler |
| 6 | **可重复性差 / RNG 未固定** — 同 dataset 多次跑结果不同 | [#270](https://github.com/JakobEngel/dso/issues/270) "Fix random seed" | 🟡 | A/B 比较实验必须自打 patch 固定 seed；论文复现要小心 |
| 7 | **Maintainer 静默 + 商业版分流** — issue tracker 死寂，TUM 维护一个 commercial fork | DSO repo last commit 2018-ish · README："professional version available for commercial purposes through TU Munich" | 🟡 | 视主仓为**论文 artifact**；产品考虑 DM-VIO（Stumberg/Engel 2022）或彻底换 ORB-SLAM3 / VINS-Fusion |
| 8 | **Pcd 输出格式问题** — point cloud 输出不易接 RViz / Open3D | [#274](https://github.com/JakobEngel/dso/issues/274) "pcd file format problem" | 🟡 | 用户需自写 exporter；DSO 出的 sparse map 不直接消费 |

**Repo health signal**：2.4k ★ / 122 PR closed / 121 open issues / 0 ROS 2 主仓支持 / last commit ~2018 / 商业版分流 / Engel 个人 GitHub 主活动转向 [Oculus 内部 stack（不公开）]

**读者实务含义**：
1. DSO 是 *2016 论文实现*，不是 *2026 活跃产品* —— 选它等于选 Docker 锁 + 自维内存安全 patch + 自做光度标定。
2. 工作包络：**global-shutter mono** + **已光度标定 dataset / 自标定鼓励** + **慢速运动 < 1 rad/s** + **室内** + **静态场景**。任一项偏离都进 #259/#260/#263/#269 已知坑。
3. 真产品 candidate 应该是 **ORB-SLAM3**（多 session + IMU）或 **DROID-SLAM**（learned BA, GPU 必备）或 **3R-SLAM Hybrid**（feed-forward + classical backend）。DSO 留作历史 + 光度法 baseline。

---

## 8 · 比较 & 面试 Tip

| 栈 | Paradigm | 前端 | 闭环 | IMU | 多 session | TRL |
|---|---|---|---|---|---|---|
| **DSO** | Direct | photometric | ❌ | ❌（DM-VIO fork 有） | ❌ | 🔬 frozen |
| **LSD-SLAM** | Semi-dense direct | photometric | ✅（弱） | ❌ | ❌ | 🔬 frozen 更早 |
| **SVO / SVO-Pro** | Semi-direct | feature align + dense map | ✅（Pro 加） | ✅（Pro 加） | ❌ | 🚀 UZH RPG drone |
| **ORB-SLAM3** | Indirect | ORB + DBoW2 | ✅ | ✅ tight | ✅ Atlas | ⭐ 室内默认 |
| **VINS-Fusion** | Indirect + IMU | KLT | ✅ | ✅ tight | △ | ⭐ aerial |
| **DROID-SLAM** | Learned BA | learned flow | ✅（学的） | △ | ❌ | 🔬 GPU 必备 |
| **VGGT** | Feed-forward | N-view transformer | n/a | ❌ | n/a | 🔬 离线 |

> **🎤 Interview Tip：「DSO vs ORB-SLAM3 我们项目选哪个？」**
>
> **正确答**：「99% 选 ORB-SLAM3。DSO 的工作包络是 *global-shutter + 已光度标定 + 慢速运动 + 室内 + 静态 + 不需要闭环 + 不需要多 session*。这个交集小到几乎只有 TUM mono dataset 复现实验。如果项目允许 RGB-D / stereo / IMU，ORB-SLAM3 直接赢；如果只能 mono 且要 deployment，看 DSO 的 fork DM-VIO 或干脆走 VINS-Mono。如果是研究 photometric baseline，DSO 仍是 gold standard，但要接受 6 年无主线维护。」
>
> **错答**：「DSO 比 ORB-SLAM 精度高所以选 DSO」—— 这是把*光度标定可控的 dataset 测试*当成*生产环境精度*。在自动曝光 / rolling-shutter / 户外 / 动态场景里，DSO 输得很难看。

> **追问**：「为什么 direct method 没赢？」
> **答**：「(1) 光度标定在真实相机栈不可得（vignetting drift + 自动曝光 + 温度漂焦距）；(2) 没有闭环 → 长 session 必然漂；(3) ORB-SLAM 的 DBoW2 + Atlas 把闭环和多 session 工程化了，direct method 一直没有等价物；(4) 2020 后 learned-BA（DROID-SLAM）+ feed-forward（VGGT）直接吃掉了 direct method 的'稠密 + 子像素'卖点。」

---

## 9 · Falsifiable Predictions（可证伪预测）

| # | 预测（2026-2027） | Falsifier |
|---|---|---|
| 1 | DSO 主仓 12 个月内**不会**有 major commit；issue #269 / #270 不会被 maintainer 回复 | 主仓 commit > 10 且 maintainer 标 closed |
| 2 | DM-VIO（DSO + IMU fork）**不会**取代 VINS-Fusion / ORB-SLAM3 在任何 robotic dataset benchmark 的 top-3 位 | EuRoC / TUM-VI / KITTI benchmark DM-VIO 进 top-3 |
| 3 | 任何 production-tier robotic shipped product（>1k units）在 mono SLAM 上选 **DSO 内核**的不会出现 | 公开 BOM / robotics paper 显示 DSO 作 mono SLAM primary |
| 4 | 3R-SLAM Hybrid（SLAM3R / Flash-Mono / EC3R-SLAM）2027 前会**完全取代**纯 direct method 在学术 mono SLAM 论文的位置 | 2027 mono SLAM 顶会论文仍以 pure direct 为基线 baseline |
| 5 | direct method 的复兴**只可能**通过和 feed-forward backbone（DUSt3R/VGGT）的 hybrid 实现 | 有纯 photometric method 在 2027 CVPR/ICCV 拿 best paper |

---

## 10 · For the Reader（读者实务）

**如果你正在 ...**
- ... **复现 DSO 论文** → 用 Docker 锁 Ubuntu 18.04 + Pangolin v0.6；只在 TUM mono dataset 测；不要换相机。
- ... **想做 mono SLAM 项目** → 先评 ORB-SLAM3 mono mode；只有当 ORB 找不到角点（白墙 / 高梯度但无纹理）且你能控制相机时再看 DSO。
- ... **要 mono + IMU** → 看 DM-VIO（Stumberg/Engel 2022）或 VINS-Mono；不是原 DSO。
- ... **想加闭环** → 别用 DSO；DSO 没有 place recognition 模块，硬加要自己整 DBoW3 + RANSAC + photometric refine，工程量等于重写。
- ... **想理解直接法 vs 特征法的根本张力** → 读 DSO 论文 §2-3 + 这篇 dissection §1-2。
- ... **想看 direct method 的未来** → 看 DROID-SLAM (2021) → MASt3R-SfM (2024) → 3R-SLAM Hybrid family (2025-2026)。

---

## 11 · References

- **DSO** — Engel, Koltun, Cremers. *IEEE TPAMI* 2018. arXiv:1607.02565 · https://arxiv.org/abs/1607.02565
- **LSD-SLAM** — Engel, Schöps, Cremers. *ECCV* 2014（DSO 前身，半稠密）
- **DTAM** — Newcombe, Lovegrove, Davison. *ICCV* 2011（稠密直接法祖宗）
- **DM-VIO** — Stumberg, Cremers. *ICRA* 2022（DSO + IMU 紧耦合 fork）
- **TUM mono dataset photometric calibration** — Engel, Usenko, Cremers. arXiv 1607.02555
- **Cadena SLAM survey** — Cadena et al. *IEEE T-RO* 2016 · https://arxiv.org/abs/1606.05830（Direct vs Indirect 经典分类）
- **DROID-SLAM** — Teed, Deng. *NeurIPS* 2021（direct method learned 继任者）
- **Code** — https://github.com/JakobEngel/dso（GPL-3.0, 2.4k ★, frozen 2018）

---

## 12 · Boundary（与相邻文件的分工）

这一篇**只管 DSO**（direct sparse VO 的顶点）。

- **ORB-SLAM3**（indirect VO 对照） → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md)
- **SVO（semi-direct VO）** → [`./svo_dissection.md`](./svo_dissection.md)
- **LSD-SLAM 与 DSO 的合并对比**（含 LSD 半稠密 vs DSO 稀疏） → [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md)
- **GitHub-validated 失败 atlas** → [`./github_failure_atlas.md`](./github_failure_atlas.md)
- **PnP / DLT 几何基础** → [`./pnp_dlt_primer.md`](./pnp_dlt_primer.md)
- **Aerial 实时 VIO**（VINS / OpenVINS / DROID） → [`../../embodiments/aerial/vio/overview.md`](../../embodiments/aerial/vio/overview.md)
- **Feed-forward 3D 继任**（DUSt3R / VGGT） → [`../feed-forward-3d/`](../feed-forward-3d/)
- **3DGS-SLAM 后端** → [`../3dgs-family/gs_slam_dissection.md`](../3dgs-family/gs_slam_dissection.md)
- **Ontology v3 Direct VO subdivision** → [`../../cheat-sheet/ontology.md`](../../cheat-sheet/ontology.md) §2

---

[← Back to Classical SLAM](./overview.md) · [→ ORB-SLAM3 dissection](./orb_slam3_dissection.md) · [→ SVO dissection](./svo_dissection.md)
