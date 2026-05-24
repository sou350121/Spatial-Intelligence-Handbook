<!-- ontology-5axis
problem: VO / VSLAM
representation: Dense flow + pose graph
sensor: Mono + IMU optional
paradigm: Hybrid-LearnedFE + Diff-BA layer
time: Online (GPU 需)
ref: ../../../cheat-sheet/ontology.md §7
-->

# DROID-SLAM 解构 (DROID-SLAM Dissection)

> **发布时间**：2021（NeurIPS）
> **论文 / 模型**：DROID-SLAM — Teed & Deng（Princeton）
> **核心定位**：第一个在多种 trajectory 上真正全面跑赢经典 SLAM（ORB-SLAM3 / VINS-Fusion）的学习派 SLAM——靠"把 dense BA 做成可微 + 用 RAFT 风格 GRU 迭代预测 flow"。

**Status:** v1.1 — opinionated draft. Backfilled to AGENTS.md 14-item dissection template 2026-05-21. Latency / mem numbers marked `UNVERIFIED` unless re-measured.
**Paper:** Teed & Deng — *DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras*, NeurIPS 2021. arXiv [2108.10869](https://arxiv.org/abs/2108.10869). Princeton.
**Code:** [princeton-vl/DROID-SLAM](https://github.com/princeton-vl/DROID-SLAM). MIT.
**TL;DR:** DROID-SLAM is the first learned SLAM that genuinely beats classical (ORB-SLAM3, VINS-Fusion) on accuracy across diverse trajectories — by reformulating dense bundle adjustment as a recurrent network update over optical-flow predictions. The catch is operational: ~5 Hz on Jetson Orin `UNVERIFIED`, no first-class IMU coupling, 6+ GB GPU memory. **It wins where classical loses (low texture, motion blur, low light) and loses where aerial demands (200 Hz state, sub-10 ms latency).** The bridge to the VGGT question is direct: DROID's recurrent-update-on-flow is the lineage VGGT collapses into a feed-forward pass.

### X-Ray 开场（非专家友好）

(a) 2021 年前学界共识："学习派 SLAM 跑不赢经典 SLAM"——DeepVO / VINet 一票方法都在 EuRoC 上输给 ORB-SLAM3。 (b) DROID-SLAM 反共识：**不替换 BA，把 BA 的 update step 学出来**——RAFT 风格 GRU 反复预测 flow + flow uncertainty，喂给可微 dense BA 层。 (c) 对 spatial 工程师：它定义了"学习派 SLAM 的精度上限"，并直接连到 VGGT 谱系（DROID 有 BA 循环 / VGGT 无），是理解 feed-forward 3D 的必经一站。

### 📍 研究全景时间线

```
ORB-SLAM3 2020 ─► ★ DROID-SLAM NeurIPS 2021 ─► DPVO 2022 (sparse 变体) ─► DUSt3R 2024 ─► VGGT CVPR 2025 ─► π³ streaming 2025+
       │                  │                                                    │
       └ 经典 BA 巅峰        └─ 学习派首次全面赢经典                                └─ 进一步抽掉迭代 → 单 forward 多视
```

DROID-SLAM 是"经典 BA → 可微 BA → feed-forward 3D"演进链中关键的中间节点。后续 DUSt3R / VGGT 不断抽掉迭代结构。

---

## 1 · Setup — what Teed & Deng were solving

Classical SLAM stacks (ORB-SLAM3, VINS-Fusion) are good at well-textured scenes with smooth motion and fail catastrophically outside that envelope. Learned VIO attempts before 2021 (DeepVO, VINet, DeepTAM) underperformed classical on standard benchmarks — the lesson seemed to be that hand-crafted geometric optimization was hard to beat.

DROID-SLAM's insight: **don't replace bundle adjustment, learn the update step inside it.** Use a RAFT-style recurrent network (Teed & Deng's prior work) to predict per-pixel optical flow + flow uncertainty, then feed those into a differentiable dense bundle-adjustment layer that solves for camera poses and per-pixel depth. The whole thing is end-to-end differentiable, trained on TartanAir, generalizes to EuRoC / TUM / ETH3D without fine-tuning. It is the cleanest "learned geometry" SLAM result the field has produced.

## 2 · Architecture

> 📌 **Napkin Formula**：`(poses, depth) = argmin Σ‖π(pose, depth) − flow_pred‖² · w_pred`，其中 `(flow_pred, w_pred)` 由 GRU 反复迭代输出，整个 BA 层对 `flow` 可微 → loss 能从 pose / depth 误差反传到 GRU 权重。**经典 BA 假设 flow 是 ground truth，DROID 让 GRU 学如何"修正"flow 使 BA 输出更好。**

```
  Frame t-1 ──┐
              ├──► RAFT-style recurrent flow update ─► flow + flow uncertainty
  Frame t   ──┘            (GRU iterations)              │
                                                         ▼
                          ┌──────────────────────────────────────────┐
                          │  Dense Bundle Adjustment (DBA) layer     │
                          │  - per-pixel inverse depth (~1/8 res)    │
                          │  - per-frame camera pose                 │
                          │  - solved as block-sparse Gauss-Newton   │
                          │  - DIFFERENTIABLE w.r.t. flow            │
                          └──────────────────────────────────────────┘
                                                         │
                                                         ▼
                            Refined depth + poses ──► next iteration / output
                                                         │
                                                         └─► (optional) global BA over keyframes
```

| Component | What it does | Why this design |
|---|---|---|
| RAFT-style flow update | Predicts dense flow between frames as recurrent GRU iterations | Differentiable, captures large displacement |
| Dense BA layer | Solves block-sparse GN system over poses + dense depth | Bridges learned flow to geometric output |
| Per-pixel inverse depth | Depth at ~1/8 resolution per frame | Dense enough for mapping, tractable for BA |
| End-to-end training | Loss on pose + depth, backprop through DBA | Teaches the network what flow BA actually needs |
| Multi-modal (mono / stereo / RGB-D) | Same network, different input mode | Generality, no retraining per sensor |

> ⚡ **Eureka Moment**：**把 dense BA 做成可微层是把"几何归纳偏置"喂给网络的最干净方式**。RAFT 早就学得动 flow，但 flow 单独训没学到"flow 是用来做 BA 的"；把 BA 接上、loss 算在 pose / depth、梯度穿过 BA 回传——GRU 自动学会预测"BA 能用的 flow + 该信任多少"。**让网络学 update 而不是学输出**，是后来 DUSt3R / VGGT 的雏形。

## 2.5 · 玩具例子（Worked Example）— 8 帧序列一次 DBA 迭代

8 帧 384×512 RGB（飞机绕室内一圈），单目模式：

- **特征**：8 帧 × 1/8 res ≈ 24,576 pixel tracks。
- **GRU I/O**：4D correlation volume → 每 pixel `Δf` + 置信权重 `w ∈ [0,1]`。
- **DBA**：稀疏 Gauss-Newton；48 pose DoF + 24,576 depth DoF ≈ 24,624 维系统。
- **迭代**：12 步 GRU + DBA，每步 ~80 ms `UNVERIFIED` on A100，全序列 ~1 s。

直觉检查：把 `w` 全设 1 重跑——动态物体 / 反光面把 BA 拉偏，pose drift 立刻显现。`w` 是 DROID 区别于经典稠密 BA 的关键。

## 3 · Where it wins

| Condition | Classical (VINS / ORB) | DROID-SLAM |
|---|---|---|
| Smooth textured scene (EuRoC MH01) | ✅ reference accuracy | ✅ comparable or slightly better `UNVERIFIED` |
| Low-texture indoor (white wall) | ❌ feature track collapses | ✅ dense flow still anchors |
| Motion blur from fast rotation | ❌ KLT tracks fail | ✅ recurrent update is blur-tolerant |
| Low light (night flight) | ❌ feature detector starves | ✅ degrades gracefully if visible |
| HDR scene (sun-glare windows) | ❌ exposure changes break photometric | ✅ learned features more invariant |
| TartanAir hard trajectories | ❌ many fail outright | ✅ first method to complete all `UNVERIFIED` |

The TartanAir result is the one that mattered at NeurIPS — classical stacks fail on a fraction of TartanAir's hard sequences, DROID-SLAM completes them. Paradigm signal, not a benchmark delta.

## 4 · Where it loses (and why aerial cares)

| Constraint | DROID-SLAM number `UNVERIFIED` | Aerial bar |
|---|---|---|
| State rate | ~5 Hz on Jetson Orin | ≥100 Hz required |
| End-to-end latency | 200–400 ms | ≤10 ms required |
| GPU memory | 6–8 GB FP32, ~3–4 GB FP16 `UNVERIFIED` | budget 2–4 GB on Orin |
| IMU coupling | not first-class (post-hoc fusion only) | tight coupling required |
| Vibration robustness | untested at prop-induced IMU aliasing | required |
| Metric scale | learned scale, no IMU lock | required, no GNSS fallback |

**This is the gap that makes DROID-SLAM the wrong choice for a primary aerial estimator** — not accuracy, rate. A 200 Hz controller can't wait 200 ms for a pose. VINS-Fusion / OpenVINS aren't more accurate; they are *fast enough to be inside the control loop*.

## 5 · The bridge to VGGT

DROID-SLAM is the immediate ancestor of feed-forward 3D models like VGGT. The lineage:

- **DROID-SLAM (2021)** — recurrent updates inside a differentiable BA loop. Multi-pass, but learned.
- **DUSt3R (2024)** — collapse the loop to a feed-forward pair-wise pointmap regression.
- **VGGT (2025)** — collapse further to single-pass N-view, no BA loop at all.

The progression is: *more learned, fewer iterations, less geometric inductive bias.* DROID still has explicit BA; VGGT has none. That trade-off is exactly the cross-embodiment question dissected in [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) — and the same conclusion applies recursively to DROID. **DROID-SLAM ships on a desktop, not on a Skydio.**

The realistic aerial deployment pattern for DROID-class methods in 2026: not as primary state estimator, but as **a back-end / loop-closure / map-building thread** running at 1–5 Hz on a co-processor (Jetson AGX class, never Nano), feeding corrections into a classical VIO front-end. Same architectural pattern as VGGT-VIO hybrids.

## 6 · Why it earned the dissection slot anyway

Two reasons it's in `embodiments/aerial/vio/` despite not shipping on aerial: **(1)** it defines the upper bound of accuracy any aerial stack can aim for in benign conditions, **(2)** it is the bridge to the feed-forward 3D future — a reader who understands DROID-SLAM will understand VGGT in 10 minutes.

### 6.x · 隐含假设（Hidden Assumptions）

- **训练分布覆盖目标场景**：TartanAir 主导；强 OOD（水下 / 烟雾 / 雪地）flow 崩。
- **静态场景占主导**：`w` 通道压低动态像素，但动态不能占大头。
- **GPU 内存够放 4D correlation volume**：8 帧已 6+ GB，长序列必须滑窗。
- **训练有 GT pose / depth**：TartanAir 仿真；真实场景需蒸馏 / self-sup。
- **无强 rolling shutter / 大畸变**：BA 仍是 pinhole + 全局快门。
- **不要求 metric scale**：单目 DROID up-to-scale，需外部 anchor。
- **5 Hz 够用**：控制环要 ≥100 Hz——DROID 必须搭配经典前端。

任一项违背时输出仍"看起来"合理，但 pose drift 几秒内显现——这是 DROID 至今未上无人机主估计的根因。

**Interview Tip**：被问 "DROID-SLAM 跟 VGGT 啥关系" 答 **"DROID 是可微 BA 的迭代版，VGGT 是把迭代抽掉的 feed-forward 版；两者都把 update 学出来，区别是迭代步数"**。能讲出"DROID 仍有几何归纳偏置（BA 层），VGGT 完全靠 transformer 学几何"加分。

### 6.y · GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：DROID-SLAM repo `princeton-vl/DROID-SLAM`（2.6k★ · 100 open · last push 2025-05）失败模式**第一大宗是 GPU 环境装不上**而非算法本身：5070TI + CUDA + PyTorch 13.0（[#166](https://github.com/princeton-vl/DROID-SLAM/issues/166)）、lietorch 装不上（[#163](https://github.com/princeton-vl/DROID-SLAM/issues/163)）、Colab 跑挂（[#164](https://github.com/princeton-vl/DROID-SLAM/issues/164)）；训练 / fine-tune pipeline 卡（[#160](https://github.com/princeton-vl/DROID-SLAM/issues/160) 自数据 fine-tune 无 SLAM 输出·[#10](https://github.com/princeton-vl/DROID-SLAM/issues/10) mono training 18 comments·[#52](https://github.com/princeton-vl/DROID-SLAM/issues/52) `droid.pth` pretrained 15 comments）；学习派单目无 IMU lock → scale drift 结构性（[#102](https://github.com/princeton-vl/DROID-SLAM/issues/102) 6 reactions）；PyTorch/CUDA 升级后 inference unpack 塌（[#115](https://github.com/princeton-vl/DROID-SLAM/issues/115) 12 comments·[#159](https://github.com/princeton-vl/DROID-SLAM/issues/159)）；重建质量 vs paper demo（[#135](https://github.com/princeton-vl/DROID-SLAM/issues/135) "Sparse and Layered"）；详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：本 dissection §4 "5 Hz on Orin / 200-400 ms latency / 6+ GB GPU" 表中"为什么 aerial 不能用"在 atlas 中被升级为 **学习派 SLAM "装环境就要一周"的隐藏成本** + Maintainer 不活跃但 repo 没死 ⚠️；研究重心已转 DUSt3R / VGGT；atlas 推荐 DROID 作为离线建图 back-end + 经典 front-end hybrid 合理但需自接，不上无人机主估计。

## 8 · GitHub-validated pitfalls (2026-05-24 deep dive)

> 系统性扫描 96 个 open issue / 4 个 PR，覆盖 GPU 内存、RTX 30/40/50 兼容、PyTorch/CUDA 升级、IMU 缺位、aerial 部署六大类。引用为原文。

| # | Pitfall | Evidence | Severity | Workaround |
|---|---|---|---|---|
| 1 | **GPU 内存爆 (8 GB 起步)** — TartanAir training 即便 `--gpus=1` 也吃满 8 GB GPU，前向 GRU 中段 OOM | [#143](https://github.com/princeton-vl/DROID-SLAM/issues/143): "torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 126.00 MiB. GPU 0 has a total capacity of 7.79 GiB" (训练用)；[#83](https://github.com/princeton-vl/DROID-SLAM/issues/83) demo 即崩 "cuda error: out of memory" | 🔴 | inference ≥12 GB GPU，training ≥24 GB；长 seq 必须滑窗 + KF cull；Jetson Nano / Xavier NX 直接放弃 |
| 2 | **PyTorch/CUDA 升级即崩** — Windows / PyTorch 2.1.1+CUDA 11.8 跑挂；`add_proximity_factors()` 出空边 → unpack 错误 → 输出全 0 / OS exit -1073741819 | [#115](https://github.com/princeton-vl/DROID-SLAM/issues/115): "not enough values to unpack (expected 2, got 0)" at "ii, jj = torch.as_tensor(es, device=self.device).unbind(dim=-1)"; RTX 3080 Ti 12 GB | 🔴 | 严格 pin 论文环境（PyTorch 1.10 + CUDA 11.3 + Ubuntu 20.04 + Python 3.9）；Windows 不要碰；用作者 Dockerfile（PR #98 未合，社区拼） |
| 3 | **新一代 GPU (RTX 40/50) lietorch/scatter 编译失败** — SM_60 默认架构与新卡不匹配；setup.py 要手 patch | [#163](https://github.com/princeton-vl/DROID-SLAM/issues/163) "Use pip install thirdparty/lietorch problem"; [#166](https://github.com/princeton-vl/DROID-SLAM/issues/166): "For install on 5070TI with CUDA and PyTorch 13.0 you need edit that rows on setup.py under thirdparty dir (both on lietorch and pytorch_scatter)" — 用户须自加 SM_75 / 移除 SM_60 | 🟠 | 改 `thirdparty/lietorch/setup.py` + `pytorch_scatter/setup.py` 的 `nvcc_args` `-gencode` 列表；3090 是最后无痛卡 |
| 4 | **IMU 集成不存在 → 单目尺度漂移结构性** — 单目模式 up-to-scale；stereo 模式用户也报 scale issue | [#102](https://github.com/princeton-vl/DROID-SLAM/issues/102): "most of them have a scaling issue if the estimated trajectory is not scaled with the ground truth" — 用户问 stereo 应有绝对尺度却仍漂；找不到 baseline 参数入口 | 🔴 | 单目 DROID 永远需 GT scale anchor；stereo baseline 通过 `--stereo` + 数据 `intrinsics.txt` 双进，但用户体感 fuzzy；要 metric 必须自接 IMU 后处理（repo 无原生支持） |
| 5 | **Real-time 主张 vs 实测** — 离线 demo @ A100，Jetson 上 1-5 Hz；用户在 [#46](https://github.com/princeton-vl/DROID-SLAM/issues/46) 想上 Jetson Xavier NX 至今无成功案例 | [#46](https://github.com/princeton-vl/DROID-SLAM/issues/46) "Implementing on Jetson Xavier NX" 长尾无答；Colab 跑挂 [#164](https://github.com/princeton-vl/DROID-SLAM/issues/164) "Colab Usage" | 🟠 | 视 DROID 为 *offline batch reconstructor* 或 *back-end @ 1-5 Hz*；不要把它做控制环主估计；aerial 主估计仍走 VINS / OpenVINS |
| 6 | **重建质量 vs 论文 demo gap** — 用户自跑出"sparse and layered"点云，与论文展示差距明显 | [#135](https://github.com/princeton-vl/DROID-SLAM/issues/135): "the point cloud result from the visualization is sparse and layered" | 🟡 | 论文 demo 通常有特殊后处理 + 调参；自跑需精调 `--upsample`、`--filter_thresh`、帧间距；不要按 demo screencap 设期望 |
| 7 | **Fine-tune / 自数据训练 pipeline 残缺** — 用户在自数据 fine-tune 后无 SLAM 输出；`droid.pth` 与当前 model config 维度不符 | [#160](https://github.com/princeton-vl/DROID-SLAM/issues/160) "Custom Dataset Training and Fine-Tuning Fails" 无 SLAM 输出；[#52](https://github.com/princeton-vl/DROID-SLAM/issues/52): "size mismatch for module.update.weight.2.weight: copying a param with shape torch.Size([3, 128, 3, 3]) from checkpoint, the shape in current model is torch.Size([2, 128, 3, 3])" — 训练 `edges=3` vs 当前 `edges=2` 不匹配 | 🟡 | fine-tune 必须用 `edges=3` 对齐 pretrained 权重；自数据需先在 TartanAir-like 仿真预训，文档无；training pipeline 在仓内不是 first-class 支持 |
| 8 | **TensorRT / 生产部署路径缺失** — 4 个 open PR 里只有一个 Dockerfile (#98 自 2023-03 未合)；无 TensorRT export、无 ONNX 路径、无 batched inference | [PR #98](https://github.com/princeton-vl/DROID-SLAM/pull/98) "Docker Support" 自 2023 open；[PR #148](https://github.com/princeton-vl/DROID-SLAM/pull/148) 仅修 Windows/Linux 整数类型 | 🟠 | 生产部署要自己写 TensorRT export；GRU + 4D correlation volume 不直接 ONNX-friendly；考虑 DPVO 稀疏变体或换 VGGT 路线 |
| 9 | **Aerial high-speed 失败模式从未压测** — repo 测过 EuRoC（缓 handheld）、TartanAir（仿真飞行）；高振动 / 桨频 IMU aliasing / >5 rad/s 无 GitHub 报告，因为没人真上无人机 | atlas 推断: 0 issues mention 'drone' or 'UAV' or 'vibration'；GitHub 用户实际场景以 indoor reconstruct + Colab 玩具为主 | 🟠 | aerial 失败模式靠 §4 表估算而非真实数据；要上无人机先做地面振动台 + 高速旋转 ground-truth 重测；DROID 不是 aerial 一线候选 |

**Repo health signal**: 2.6k ★ / 96 open / forks 407 / 4 PR open (其中 3 个 2023 前开) / last commit 2025-05 (Apr 2026 仍有新 issue [#167](https://github.com/princeton-vl/DROID-SLAM/issues/167) 但 maintainer 无响应)

**讀者實務含義**:
1. DROID-SLAM 是 *NeurIPS 2021 论文 reproducer + 离线建图工具*，不是 *online aerial 估计*——把它视为 dataset processor 而非 robot software。
2. 环境装一周是常态：pin PyTorch 1.10/CUDA 11.3 或接受为新 GPU 改 setup.py 的工程税；Windows / Colab / Jetson Nano 全部劝退。
3. IMU 缺位 + 5 Hz 状态率 + 6+ GB 显存 = aerial 主估计死刑；研究价值（学习派 SLAM 上限 + VGGT 谱系祖宗）远高于部署价值；要上设备走 VINS-Fusion / OpenVINS。

---

## References

- DROID-SLAM — Teed & Deng. *NeurIPS 2021*. [arXiv 2108.10869](https://arxiv.org/abs/2108.10869)
- RAFT (predecessor) — Teed & Deng. *ECCV 2020*. [arXiv 2003.12039](https://arxiv.org/abs/2003.12039)
- TartanAir — Wang et al. *IROS 2020*. [arXiv 2003.14338](https://arxiv.org/abs/2003.14338)
- VGGT comparison — see [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../../crossing/slam-vio-migration/vggt_vs_drone_vio.md)

## Boundary

This file dissects DROID-SLAM mechanics. The cross-embodiment "can learned SLAM replace classical VIO" debate lives in [`crossing/slam-vio-migration/`](../../../crossing/slam-vio-migration/). VGGT's own dissection lives in [`foundations/feed-forward-3d/`](../../../foundations/feed-forward-3d/). On-device deployment trade-offs (Jetson sizing, GPU power budget) live in `deployment/`.
