# Aerial VIO GitHub Failure Atlas (无人机 VIO GitHub 失败模式图谱)

> **类型：** Ecosystem 文档（非 paper dissection）。源：4 个 repo 的 open issues + PR 历史，采样截至 2026-05-21。
> **范围：** VINS-Mono · VINS-Fusion · OpenVINS · DROID-SLAM
> **核心定位：** Paper §6 写得太干净；issue tracker 才记得 "prop 振动让 IMU bias 漂、init 在静止开机时发散、ROS 2 port 半成品" —— 给给 drone autonomy 选 VIO 栈的工程师一份"先看这页再开 fork"的清单。

**Status:** v1 — 数字 / commit 时间均 `UNVERIFIED`，issue # + URL 一手来源。属 `*_ecosystem.md`，不走 14 项 dissection 门槛。与 [`foundations/classical-slam/github_failure_atlas.md`](../../../foundations/classical-slam/github_failure_atlas.md) 配套。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../../cheat-sheet/cross_zone_failure_atlas.md)

**X-Ray.** Paper 报 EuRoC RMSE；issue tracker 报 "我装上自家四旋翼第一次起飞就发散"。四栈 issue 反复浮现：init 失败 / extrinsic 漂 / scale 收敛慢 / 振动污染 / GPU 跑不下 —— 与 dissection §6 Hidden Assumptions 一一对应。选栈不看 EuRoC 名次，看 "我家 IMU + 我家 prop + 我家 SoC，起飞前需要做几件事才不发散"。

## Zone Summary

整体气候：**比 classical SLAM 区显著活跃**。**OpenVINS（UDel RPNG）是唯一官方维护活跃**的 repo（近 6 月仍有 commit / issue 被官方回 / 官方 ROS 2）。VINS-Mono / VINS-Fusion（HKUST）已是学术毕业 + 社区自治（≥ 1 年未 push）；社区 fork 撑 ROS 2。DROID-SLAM 是 GPU 学习派离线工具，issue 多在训练 / pip 装环境，结构上不上无人机控制环。Production 部署仍需自录 calibration、自硬件 trigger、自定 prop 滤波 — 论文不替你做。

---

## 1 · VINS-Mono

- **Repo:** https://github.com/HKUST-Aerial-Robotics/VINS-Mono
- **Stats `UNVERIFIED`:** ~5.9k stars / ~2.2k forks / **293 open issues** / 最近 push 2024-08
- **Dissection:** [`./vins_mono_fusion_dissection.md`](./vins_mono_fusion_dissection.md)

### Top 失败模式

1. **Init 卡死 / 反复 restart** —— [#475](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/475) 自录反复 restart、[#473](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/473) 初始 quaternion (0,1,0,0)。对应 dissection §6.x：静止开机 / accel 方差不足 → 单目 metric scale 永不收敛。
2. **Stationary drift** —— [#462](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/462)、[#469](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/469)。静止时 bias 漂 + 无 parallax → 滑窗 prior 失效。
3. **EuRoC 复现 RMSE 不对** —— [#471](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/471)、[#470](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/470) ROS 2 RMSE 不同。跨 OS / ROS / Ceres 版本 RMSE 不一致。
4. **嵌入式 crash** —— [#400](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/400) Jetson Nano crashed（10 comments）。单核 + 200 Hz preint + Ceres → 资源不够。
5. **OOD 场景错配** —— [#468](https://github.com/HKUST-Aerial-Robotics/VINS-Mono/issues/468) Underwater。文档没说"是 indoor handheld + slow MAV 调优"。

**PR 方向**：2018–2021 后断；近 1 年无 merged PR。HKUST 团队继续在 VINS-Fusion / fork 上动。

**Project momentum: ⚠️** — 学术毕业 + 社区自治；社区 ROS 2 fork 取代官方。

**是否该选**：✅ 教学 baseline / EuRoC 复现；⚠️ 真上无人机 — 用 VINS-Fusion 或 OpenVINS；❌ 最新 ROS 2 — 选 OpenVINS

---

## 2 · VINS-Fusion

- **Repo:** https://github.com/HKUST-Aerial-Robotics/VINS-Fusion
- **Stats `UNVERIFIED`:** ~4.5k stars / ~1.6k forks / **211 open issues** / 最近 push 2024-05
- **Dissection:** [`./vins_mono_fusion_dissection.md`](./vins_mono_fusion_dissection.md)

### Top 失败模式

1. **Mono 漂 / Mono+IMU 不可靠** —— [#271](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/271) mono drift (Gazebo + real)、[#269](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/269)、[#198](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/198) "Weird Init of IMU + Stereo"。对应 dissection §4。
2. **Global opt / loop closure 不稳定** —— [#3](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/3) "global optimization thread doesn't work"（自 2019 仍 open）、[#239](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/239) RVIZ 与 GPS 垂直。
3. **数值稳定 / Ceres 版本** —— [#246](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/246) preint 数值不稳、[#275](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/275) Ceres 2.2.0、[#276](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/276) `FeatureManager::triangulate` SVD 疑误。
4. **ROS 2 + IMU QoS** —— [#273](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/273) RELIABLE vs BEST_EFFORT、[#247](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/247) ros2 d435i 报错。与 ecosystem §3 一致。
5. **OAK-D / D435i / 自录 stereo rig** —— [#241](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/241)、[#272](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/272)。没按 Kalibr 流程 → init 不收敛。

**PR 方向**：几乎全 open / 无人 merge。[#5](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/pull/5) "FeatureManager::triangulate() potential bug" 自 2019 仍 open。

**Project momentum: ⚠️** — 学术毕业 + 社区自治；issue / PR 堆积。

**是否该选**：✅ Stereo+IMU 部署 baseline / aerial 业界比对基线；⚠️ GPS fusion / global localization；❌ CPU 极度受限 — 选 OpenVINS

---

## 3 · OpenVINS

- **Repo:** https://github.com/rpng/open_vins
- **Stats `UNVERIFIED`:** ~2.9k stars / ~854 forks / **68 open issues** / 最近 push **2025-11**
- **Dissection:** [`./openvins_dissection.md`](./openvins_dissection.md)

### Top 失败模式

1. **Filter divergence after init** —— [#540](https://github.com/rpng/open_vins/issues/540) "divergence after init – extremely large IMU values"（2 reactions）、[#533](https://github.com/rpng/open_vins/issues/533) D435i。对应 dissection §6.x outlier / triangulation 收敛假设。
2. **Static init fail** —— [#477](https://github.com/rpng/open_vins/issues/477) save_total_state（5 comments, maintainer 在线）。Static / dynamic init 在自录数据常两种都失败。
3. **Orin Nano segfault** —— [#514](https://github.com/rpng/open_vins/issues/514)。YAML 与 IMU 实际采样率不匹配。
4. **大尺度 OOD（100 m 高度）** —— [#513](https://github.com/rpng/open_vins/issues/513)（1 reaction, 7 comments）。Parallax 退化 → clone 窗口 baseline 不足。
5. **多相机 / online calib 真实失败** —— [#534](https://github.com/rpng/open_vins/issues/534)、[#505](https://github.com/rpng/open_vins/issues/505) ZED2（6 comments）。Multi-cam 论文卖点，实际门槛比文档高。

**PR 方向**：近 6 月有官方维护活动（init 改进、bug 修、ROS 2 launch）；issue 回复率明显高于 VINS 系列。

**Project momentum: ✅** — **Aerial VIO 区唯一仍正常维护的官方 repo**。UDel RPNG（Geneva / Huang）持续在动；dissection "Skydio-adjacent lineage" 在这里现实化。

**是否该选**：✅ CPU 受限 / 多相机 / ROS 2 / production aerial 主估计器 — 当前最优默认；✅ 学 MSCKF+FEJ+null-space；⚠️ 学界绝对精度 — VINS-Fusion 在 EuRoC 仍稍准

---

## 4 · DROID-SLAM

- **Repo:** https://github.com/princeton-vl/DROID-SLAM
- **Stats `UNVERIFIED`:** ~2.6k stars / ~406 forks / **100 open issues** / 最近 push 2025-05
- **Dissection:** [`./droid_slam_dissection.md`](./droid_slam_dissection.md)

### Top 失败模式

1. **GPU 环境 / pip 装不上** —— [#166](https://github.com/princeton-vl/DROID-SLAM/issues/166) 5070TI + CUDA + PyTorch 13.0、[#163](https://github.com/princeton-vl/DROID-SLAM/issues/163) lietorch、[#164](https://github.com/princeton-vl/DROID-SLAM/issues/164) Colab。issue 第一大宗。
2. **训练 / fine-tune pipeline 卡** —— [#160](https://github.com/princeton-vl/DROID-SLAM/issues/160) 自数据 fine-tune 无 SLAM 输出、[#10](https://github.com/princeton-vl/DROID-SLAM/issues/10) mono training（18 comments）、[#52](https://github.com/princeton-vl/DROID-SLAM/issues/52) `droid.pth` pretrained（15 comments）。
3. **Scale issue / stereo / mono 不一致** —— [#102](https://github.com/princeton-vl/DROID-SLAM/issues/102)（6 reactions）。学习派单目无 IMU lock → scale drift 结构性。
4. **Inference unpack / 旧 API** —— [#115](https://github.com/princeton-vl/DROID-SLAM/issues/115) "not enough values to unpack"（12 comments）、[#159](https://github.com/princeton-vl/DROID-SLAM/issues/159)。PyTorch / CUDA 升级后塌。
5. **重建质量 vs paper demo** —— [#135](https://github.com/princeton-vl/DROID-SLAM/issues/135) "Sparse and Layered"。

**PR 方向**：稀疏；近期更新主要是 docker / wheels / 文档。无 aerial-specific 改造。

**Project momentum: ⚠️** — 学界仍引用 / 社区还在装环境；研究重心已转 DUSt3R / VGGT。Maintainer 不活跃但 repo 没死。

**是否该选**：✅ 离线高精度建图 / TartanAir 难场景 / GPU 充足；✅ 学 "可微 BA" — 通向 DUSt3R / VGGT 必经；❌ 任何 aerial 实时估计 — dissection §4 已说死 "~5 Hz on Orin / 200-400 ms latency / 6+ GB GPU"；⚠️ 离线 mapping back-end + 经典 front-end hybrid — 合理但需自接

---

## Cross-Cutting Patterns & Surprises

**重复 patterns**：init 失败（静止开机 / 不充分激发）→ VINS-Mono · VINS-Fusion · OpenVINS，pre-flight wiggle ritual 不可省；IMU bias / time-sync 误差（全 4）→ 硬件 trigger + Kalibr 是入场费；单目 scale 收敛慢（VINS-Mono · DROID mono）→ 结构性弱项，stereo / RGB-D / IMU lock 必备；ROS 2 port 半成品（VINS-Mono · VINS-Fusion · DROID）→ 选 OpenVINS 省一年；嵌入式 SoC 不够（全 4）→ Jetson Nano 是"硬件不够"信号，Orin 起步才稳；自录数据 ≠ EuRoC（全 4）→ EuRoC RMSE 不外推。

**反直觉**：(1) OpenVINS 是 aerial VIO 区唯一 maintainer 仍活跃的 repo，反而 issue 数最少（~68）— 验证 dissection "Skydio-adjacent lineage" 工程感。(2) VINS-Fusion [#3](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion/issues/3) "global optimization thread doesn't work properly" 自 2019 仍 open — 论文卖点 loop closure built-in 长期不可靠，官方未修。(3) DROID-SLAM 失败模式几乎全是 GPU 环境（lietorch / CUDA / pip） — 学习派 SLAM "装环境就要一周"的隐藏成本。(4) VINS-Mono Jetson Nano crash 最频繁 — "EuRoC 跑通 ≠ Nano 跑通"，CPU 预算 dissection §4 是必看现实。

---

## Boundary

- VINS 算法 → [`./vins_mono_fusion_dissection.md`](./vins_mono_fusion_dissection.md)
- OpenVINS / MSCKF / FEJ → [`./openvins_dissection.md`](./openvins_dissection.md)
- DROID-SLAM 可微 BA → [`./droid_slam_dissection.md`](./droid_slam_dissection.md)
- Classical SLAM 同维度图谱 → [`foundations/classical-slam/github_failure_atlas.md`](../../../foundations/classical-slam/github_failure_atlas.md)
- Kalibr / 标定 / time-sync → [`foundations/classical-slam/slam_toolchain_ecosystem.md`](../../../foundations/classical-slam/slam_toolchain_ecosystem.md)
- 跨 embodiment "学习派 vs 经典 VIO" → [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)

---

## References

- 全部 issue 编号附 https://github.com/{repo}/issues/{N} 链接，采样截至 2026-05-21
- 仓库 stat 来自 GitHub REST API 即时查询 — 数字 `UNVERIFIED`

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to Aerial VIO](./README.md)
