# Classical SLAM GitHub Failure Atlas (经典 SLAM GitHub 失败模式图谱)

> **类型：** Ecosystem 文档（非 paper dissection）。源：5 个 repo 的 open issues + PR 历史，采样截至 2026-05-21。
> **范围：** ORB-SLAM3 · DSO · LSD-SLAM · Kalibr · maplab
> **核心定位：** Paper 不会写、issue tracker 才会留下的"该工具到底卡在哪"账本。

**Status:** v1 — 数字 / commit 时间均 `UNVERIFIED`，issue # + URL 为一手来源。属于 `*_ecosystem.md`，不走 14 项 dissection 门槛。

**X-Ray.** Paper 给的是受控数据集最佳数字；issue tracker 给的是真实用户踩了什么坑。五个工具 issue 反复浮现 tracking lost / 编译失败 / IMU init failure / 标定不收敛 —— 是 maintainer 几年没空回复的角落。选栈不看 EuRoC RMSE，看"这 repo 的 maintainer 现在还回 issue 吗"。

## Zone Summary

整体气候：**算法稳定但工具链 stale**。5 个 repo 全部代码冻结 + 社区自治（官方 commit 1–2 年前）；issue 90% 是 Ubuntu / ROS 2 / Eigen / Pangolin / Ceres 版本冲突。DSO / LSD-SLAM / maplab 是学界毕业 → 只读状态；直接法谱系（DSO / LSD）实质停滞。学习派走前面、商用栈走自研、开源经典 SLAM 现在是"教科书 + baseline"位置，不是 production 默认。

---

## 1 · ORB-SLAM3

- **Repo:** https://github.com/UZ-SLAMLab/ORB_SLAM3 · **Stats `UNVERIFIED`:** ~8.6k stars / ~3.1k forks / **568 open issues** / 最近 push 2024-07 · **Dissection:** [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md)

### Top 失败模式

1. **IMU 初始化失败** —— [#730](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/730) "Empty IMU measurements"、[#933](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/933) EuRoC init、[#980](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/980) Mono-Inertial、[#264](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/264) infinity init。共因：D435i / 自录 / Gazebo 的 IMU-cam 时间戳不同步 → preintegration 空 buffer → 死循环。
2. **Segfaults / G2oTypes 崩** —— [#967](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/967) `G2oTypes.cc`、[#828](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/828) 23 评论、[#451](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/451) "SO3::exp failed" (7 reactions)、[#156](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/156) 自 2022 open。根因：Pangolin / Eigen / g2o 版本不匹配。
3. **Stereo tracking lost / right cam 不识别** —— [#943](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/943)、[#991](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/991) 左图 few features crash、[#961](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/961) stereo-inertial。
4. **Atlas merge 行为不可预期** —— [#950](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/950) IMU loop closure、[#737](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/737) map viewer 空。论文卖点在用户数据上不一致。
5. **构建 / OS 兼容** —— [#996](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/996) Orin Nano build、[#374](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/374) Pangolin build。

**PR 方向（近 6 月）**：不接 PR。历史 merge 多在 2020；近 1 年 PR 仅为用户挂未审稿件（如 [#999](https://github.com/UZ-SLAMLab/ORB_SLAM3/pull/999)）。社区贡献流向外部 fork（`thien94/orb_slam3_ros_wrapper`、`zang09/ORB_SLAM3_ROS2`、`SuperSLAM`），主仓视同冻结。

**Project momentum: ⚠️** — frozen 代码 + 用户活跃 + maintainer 沉默；[#1001](https://github.com/UZ-SLAMLab/ORB_SLAM3/issues/1001) 2026-04 用户吐槽 "the worst repository I have ever tried to work with"（3 reactions）即写照。

**是否该选**：✅ 学术 baseline / 室内 RGB-D / manipulation PoC；⚠️ 产品部署 — 锁版本 fork + 自接 ROS 2；❌ Aerial / 高速 / 户外 → 见 [`embodiments/aerial/vio/`](../../embodiments/aerial/vio/README.md)

---

## 2 · DSO

- **Repo:** https://github.com/JakobEngel/dso · **Stats `UNVERIFIED`:** ~2.4k stars / ~921 forks / **138 open issues** / 最近 push 2024-02 · **Dissection:** [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md)

### Top 失败模式

1. **数值断言 fail / NaN / Inf** —— [#123](https://github.com/JakobEngel/dso/issues/123) `Assertion 'std::isfinite' failed`（9 reactions）。自录手机数据上反复；与 §6 "光度标定可用 / Lambertian / 亮度恒定" 破裂对应。
2. **time-stamp / 输出格式** —— [#237](https://github.com/JakobEngel/dso/issues/237) "No timestamps in result"（6 reactions）、[#186](https://github.com/JakobEngel/dso/issues/186)。EVO 评测直接卡。
3. **Textureless / brightness silent fail** —— [#251](https://github.com/JakobEngel/dso/issues/251)、[#269](https://github.com/JakobEngel/dso/issues/269) use-after-free。自动曝光手机数据直接破。
4. **数学内核问号** —— [#93](https://github.com/JakobEngel/dso/issues/93) `orthogonalize()`、[#243](https://github.com/JakobEngel/dso/issues/243) `res_toZeroF`、[#126](https://github.com/JakobEngel/dso/issues/126) energy functional。教学读源码对象。
5. **Pangolin 装不上** —— [#242](https://github.com/JakobEngel/dso/issues/242)。

**PR 方向**：PR 流冻结。最近 merged 在 2017–2018。Engel 在 Meta / RealityLabs。

**Project momentum: ❌** — 学术冻结。LDSO（加闭环）和 DM-VIO（DSO+IMU）是继任者，本仓已成历史标本。

**是否该选**：✅ 算法研究 / 直接法教学；⚠️ 自录数据 — 不做光度标定就是浪费时间；❌ Production — 用 DM-VIO 或 SVO

---

## 3 · LSD-SLAM

- **Repo:** https://github.com/tum-vision/lsd_slam · **Stats `UNVERIFIED`:** ~2.7k stars / ~1.2k forks / **240 open issues** / 最近 push 2023-03

### Top 失败模式

1. **ROS 老版 build / Ubuntu 升级断** —— [#330](https://github.com/tum-vision/lsd_slam/issues/330) gendeps、[#302](https://github.com/tum-vision/lsd_slam/issues/302) rosdep2、[#290](https://github.com/tum-vision/lsd_slam/issues/290)。被 ROS 1 + Ubuntu 14.04 锁死。
2. **运行时崩 / Debug window 不出** —— [#321](https://github.com/tum-vision/lsd_slam/issues/321) runtime_error Duration、[#351](https://github.com/tum-vision/lsd_slam/issues/351) double free、[#348](https://github.com/tum-vision/lsd_slam/issues/348)。
3. **Gtk 兼容** —— [#355](https://github.com/tum-vision/lsd_slam/issues/355)、[#356](https://github.com/tum-vision/lsd_slam/issues/356)。
4. **数据集 link 死 / 社区 Docker 解救** —— [#353](https://github.com/tum-vision/lsd_slam/issues/353)（4 reactions）、[#342](https://github.com/tum-vision/lsd_slam/issues/342)（3 reactions）。
5. **教学提问无人回** —— [#350](https://github.com/tum-vision/lsd_slam/issues/350) Gauss Newton 自 2020 open。

**PR 方向**：最近 merged 在 2014–2015；archived in practice。

**Project momentum: ❌** — 完全 frozen。学术历史。

**是否该选**：✅ 博士论文 chapter / 经典直接法教学；❌ 其它一切

---

## 4 · Kalibr

- **Repo:** https://github.com/ethz-asl/kalibr · **Stats `UNVERIFIED`:** ~5.4k stars / ~1.6k forks / **133 open issues** / 最近 push 2024-03 · **生态:** [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md) §1

### Top 失败模式

1. **收敛失败 / 外参跑出离谱数字** —— [#756](https://github.com/ethz-asl/kalibr/issues/756) 大 translation error、[#768](https://github.com/ethz-asl/kalibr/issues/768) cam-imu cal、[#765](https://github.com/ethz-asl/kalibr/issues/765) dt + IMU 结果疑问。根因：6-DoF 激发不足 + IMU noise 用 datasheet → cost 最小但物理错。
2. **AprilTag 识别** —— [#760](https://github.com/ethz-asl/kalibr/issues/760) separator squares、[#759](https://github.com/ethz-asl/kalibr/issues/759) "texture considered harmful"。自打印分辨率 / 边界污染。
3. **多 board / fisheye 多相机** —— [#773](https://github.com/ethz-asl/kalibr/issues/773)、[#770](https://github.com/ethz-asl/kalibr/issues/770) quad-fisheye + IMU。
4. **ROS 2 / Docker** —— [#725](https://github.com/ethz-asl/kalibr/issues/725) "upgrade to ROS 2"（6 reactions, 7 comments）、[#745](https://github.com/ethz-asl/kalibr/issues/745) docker build、[#771](https://github.com/ethz-asl/kalibr/issues/771) ROS 2 衔接。与 ecosystem §3 一致。
5. **Headless display** —— [#726](https://github.com/ethz-asl/kalibr/issues/726) "Cannot open display"。

**PR 方向**：近期 PR 节奏比另四仓略好；社区维护痕迹存在。

**Project momentum: ⚠️** — 仍是事实标准（无替代品），官方维护停滞，社区围绕 ROS 2 port。周边脱节（[#763](https://github.com/ethz-asl/kalibr/issues/763) 原 calib 板供应商域名被标 unsafe）。

**是否该选**：✅ 任何 VI-SLAM PoC 必装；⚠️ 量产线 — 二次封装 + headless + 锁版本；❌ 不要指望官方接 ROS 2

---

## 5 · maplab

- **Repo:** https://github.com/ethz-asl/maplab · **Stats `UNVERIFIED`:** ~2.8k stars / ~747 forks / **123 open issues** / 最近 push 2024-05 · **生态:** [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md) §2

### Top 失败模式

1. **Ubuntu 22.04 build** —— [#422](https://github.com/ethz-asl/maplab/issues/422) D455 laggy、[#413](https://github.com/ethz-asl/maplab/issues/413) opencv3_catkin、[#411](https://github.com/ethz-asl/maplab/issues/411) init-git-hooks。
2. **maplab 2.0 rovioli 跑不通 / front-end 配套** —— [#414](https://github.com/ethz-asl/maplab/issues/414)、[#389](https://github.com/ethz-asl/maplab/issues/389) okvis + super point + brisk（12 comments）。Backend 框架，front-end wire-up 卡。
3. **demo / 数据集死链** —— [#424](https://github.com/ethz-asl/maplab/issues/424)、[#418](https://github.com/ethz-asl/maplab/issues/418)。
4. **link 错误** —— [#408](https://github.com/ethz-asl/maplab/issues/408) `addLabelToPointCloud` undefined。
5. **LiDAR / topomap / 复现请求** —— [#412](https://github.com/ethz-asl/maplab/issues/412)、[#417](https://github.com/ethz-asl/maplab/issues/417)、[#365](https://github.com/ethz-asl/maplab/issues/365)。

**PR 方向**：稀疏；ETHZ-ASL 团队大量转 Skydio / 工业。

**Project momentum: ❌** — 学术毕业 / 维护稀疏。ecosystem §2 已判 "工业用得不多，2021 后维护频率降低"。

**是否该选**：✅ 学术 PoC（多 session / 多机器人 VIO 实验）；⚠️ 长期跑 — fork + 锁版本；❌ 单机器人单 session — 用 ORB-SLAM3 / VINS-Fusion 就够

---

## Cross-Cutting Patterns & Surprises

**重复 patterns**：Pangolin / Eigen / OpenCV / Ceres 版本冲突（ORB-SLAM3 · DSO · LSD · maplab）→ 锁 Ubuntu + Docker；ROS 1→2 迁移空窗（全 5）→ 官方不来；IMU-cam 时间不同步 → 硬件 trigger 是入场费；学术 maintainer 毕业 → 只读（DSO · LSD · maplab）；自录数据 / 自打印 cal board 静默偏差（DSO · Kalibr）。

**反直觉**：(1) ORB-SLAM3 issue 数 ≈ DSO+LSD+maplab 三者之和，但 maintainer 回复率最低 — 用户多 ≠ 维护强。(2) Kalibr 最近 issue 流最活跃，但官方 push 仍冻结 — "必须用但没人修"，工具锁定 risk 最高。(3) maplab LiDAR mapping 是用户多年请求，学术 repo 永不跨这步 — 工业方向需自己重做。

---

## Boundary & References

- ORB-SLAM3 算法 → [`./orb_slam3_dissection.md`](./orb_slam3_dissection.md) · DSO / LSD-SLAM → [`./direct_methods_dso_lsd.md`](./direct_methods_dso_lsd.md) · Kalibr / maplab / ROS 2 → [`./slam_toolchain_ecosystem.md`](./slam_toolchain_ecosystem.md)
- Aerial VIO 同维度图谱 → [`embodiments/aerial/vio/github_failure_atlas.md`](../../embodiments/aerial/vio/github_failure_atlas.md) · 跨 embodiment → [`crossing/slam-vio-migration/`](../../crossing/slam-vio-migration/)
- 全部 issue 编号附 https://github.com/{repo}/issues/{N} 链接，采样截至 2026-05-21；stat 来自 GitHub REST API — `UNVERIFIED`。

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to Classical SLAM](./README.md)
