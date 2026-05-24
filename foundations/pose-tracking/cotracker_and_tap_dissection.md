<!-- ontology-5axis
problem: PointTracking (任意點長時跟蹤)
representation: Per-point trajectory
sensor: Video (RGB)
paradigm: Learned-Transformer (iterative refinement)
time: Online
ref: ../../cheat-sheet/ontology.md §7
-->

# CoTracker & TAP-Vid (任意点的时序追踪)

> **发布时间**: CoTracker — ECCV 2024 (Karaev et al., Meta + Oxford) · TAP-Vid / TAP-Net — NeurIPS 2022 (Doersch et al., DeepMind)
> **论文**: CoTracker (arXiv 2307.07635) · TAP-Vid (arXiv 2211.03726)
> **核心定位**: 在任意长视频中追踪任意点集 — *跨时间和跨点联合* — 处理遮挡与持续.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · 经典 *稀疏长时序* tracking 原语（RAFT 密集短时序的互补）.
**TL;DR:** TAP-Vid 定义任务 — "追踪任意点、预测可见性、处理遮挡". CoTracker 通过 *用 cross-track attention 联合追踪一批 query points* 解决. 在点必须穿越遮挡持续时替代 KLT / SIFT — 接触点、动作识别、watch-and-imitate.

**X-Ray.** 经典稀疏 tracker 独立追点，遮挡处失败. CoTracker 把这批作为*联合*问题，用跨时间和跨点的 cross-attention. "在这个 episode 中追踪接触点" 的缺失原语.

---

## 📍 研究全景时间线

```
1991     1999         ~2010s      2022           2023      2024
KLT ───► SIFT match ► local-corr ► TAP-Net+bench ► CoTrk ► CoTrk3 online
└── per-point sparse tracking ──┘  └── joint cross-point + cross-time ──┘
```

从 "独立追每个点" 到 "联合追所有" 的转折. VGGT 为其 tracking head 借了这个.

---

## 1 · 架构总览

### 1.1 系统组件对比（CoTracker）

| Module | Role |
|---|---|
| Frame encoder | ViT → 1/8 处特征 |
| Query-pt encoder | `(x, y, t_query)` 的 embedding |
| Iterative refiner | Transformer 带 **time × point** attention |
| Visibility head | Per-(point, frame) 分类器 |
| Output | Trajectory + visibility |

亮点：**跨时间和点轴的联合 attention** — 之前方法没做.

### 1.2 ⚡ Eureka Moment

> **联合追踪点 — 让每条轨迹通过 cross-attention 互相告知 — 遮挡穿越就不再是开放问题.**

KLT / SIFT tracker 是 per-point：各自命运孤立决定. CoTracker 的洞见：同表面上的点统计相关 — 联合推断能在某一被遮时继续追踪，因为*其他*点携带信号.

### 1.3 信息流

```
   Frames ─► frame enc ─► F_1..F_T
   Query pts (x_i, y_i, t_i) ─► q_1..q_N
                  ▼
   [joint transformer ×K: attn(time × points) → refined traj + vis]
                  ▼
   Trajectories (x_i(t), y_i(t), vis_i(t))
```

---

## 2 · Math core

### 📌 Napkin Formula

```
  traj_{i,t}^{(k+1)}  =  refiner( {traj_{j,s}^{(k)}},  F_t,  query_i )
```

点 `i` 在 `t` 的轨迹依赖**所有其他 track `j` 在其他时刻 `s`** 通过 attention. 每次迭代收紧联合解.

| Symbol | Meaning |
|---|---|
| `traj_{i,t}` | 点 `i` 在 `t` 的 2D 位置 |
| `vis_{i,t}` | `t` 的可见性 |
| `F_t` | `t` 的特征图 |
| `K` | refinement 迭代 |

**Intuition.** 单点 tracker 见到一份证据；CoTracker 用 attention 在 `N × T` 上计算联合解. 遮挡不再致命 — 同动点携带信号.

---

## 3 · Worked example: 64 个接触点，5-秒 clip

5 s @ 30 fps（150 帧），机器人抓 mug. mug + 手接触上 64 个 query 点.

1. **Encode 150 帧.** ~5–10 ms / frame `UNVERIFIED` → ~1–2 s.
2. **Initialize.** 每个 query 点在标注帧；trajectory 常数.
3. **Iterate** `k = 1..6`: 在 (64 × 150 × features) 上的联合 transformer → refined 位置 + 可见性.
4. **Output.** 每个点: (150, 2) trajectory + visibility. Mug 后的点显示 `vis=False`；重现点重获.

离线共 ~3–5 s. CoTracker3 online 用稍高的 per-frame 延迟流式实时. KLT 在 64 个独立点上手遮时丢一半，无再获.

---

## 4 · Engineering view

| Task | RAFT | CoTracker |
|---|---|---|
| 密集 per-pixel, 2 帧 | ✅ | ❌ |
| 30 帧 clip 的稀疏点 | ❌ | ✅ |
| 穿越遮挡 | ❌ | ✅ |
| 同物体联合约束 | ❌ | ✅ |
| Orin RT 30 Hz | ✅ | ⚠️ online + 小 N |

CoTracker3 *online* 用有界内存逐帧流出预测.

**Deployment.** 接触持续：episode 起始在 gripper-object 接触处 query → 追踪 → policy 的接触状态. Watch-and-imitate：从 demo 追踪 hand + tool keypoint → replay.

---

## 5 · Data & eval

**TAP-Vid** 是经典：Kinetics、DAVIS、RGB-Stacking 子集 + 手标 GT track + visibility. 指标：Average Jaccard、位置精度（δ_avg &lt; 5 px）、遮挡精度. CoTracker 训在 **Kubric**（程序生成合成）上，TAP-Vid + DAVIS 评估 — 大幅击败 TAP-Net `UNVERIFIED`.

---

## 6 · Capabilities & failure modes

**Capabilities.** 中度遮挡鲁棒. Cross-track 一致. Visibility-aware. Online streaming 可部署.

**Failure modes.** 长遮挡（>30% episode）压垮联合约束. 快速无纹理运动. 无特征表面 — query 病态；幻觉平滑轨迹. 大点集（>256）压力内存.

### 6.1 Hidden Assumptions

- **Query 点在一致表面上.** 深度不连续边界 → 嘈杂.
- **帧率足够.** 慢 fps + 快运动 → 位移超过感受野.
- **相机静态或 ego-motion 可补偿.** 大震无 ego-motion 估计退化.
- **Online 容忍 streaming-buffer 延迟.** >30 Hz 控制紧 `UNVERIFIED`.
- **Visibility 校准到相似分布数据.** 机器人场景与 Kubric 不同；`vis` 阈值需调.

这些破时，track 出来看着平滑但错 — 静默失败.

### 6.2 GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：长视频 memory 爆是 CoTracker 头号痛点 — 3 分钟视频在 Colab GPU OOM（[#51](https://github.com/facebookresearch/co-tracker/issues/51), 14 comments），用户提议分段 + 末帧延续但官方无回应；live video / streaming 应用支持弱（[#37](https://github.com/facebookresearch/co-tracker/issues/37) 21 comments·[#54](https://github.com/facebookresearch/co-tracker/issues/54)·[#123](https://github.com/facebookresearch/co-tracker/issues/123)），offline v2/v3 切换不清晰；稀疏单点 webcam 跟踪不稳（[#71](https://github.com/facebookresearch/co-tracker/issues/71)·[#24](https://github.com/facebookresearch/co-tracker/issues/24)），动物腿等高频运动易丢；ONNX 导出路径 [#10](https://github.com/facebookresearch/co-tracker/issues/10) 现状不明；Kubric 训练数据复现 [#8](https://github.com/facebookresearch/co-tracker/issues/8) 29 comments 起跳；商用 license 需求 [#31](https://github.com/facebookresearch/co-tracker/issues/31)。streaming memory API 是社区等待官方接管的下一波 PR 焦点，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)
- **GitHub-validated**：CoTracker v3（2025）改善短时密集追踪，但 **长视频 + 稀疏点 + 实时 三交叉点仍缺**；本 dissection §6 "Online 容忍 streaming-buffer 延迟" / "大点集压力内存" 两条假设在 issue 区被直接量化暴露 — 30 Hz 控制紧 + Colab OOM 是部署侧最高 ROI 缺口。

---

## 7 · Comparison & interview tip

| Tracker | Year | Joint? | Occ? | Long? | RT Orin? `UNVERIFIED` |
|---|---|---|---|---|---|
| KLT | 1991 | ❌ | ❌ | partial | ✅ very |
| SIFT | 1999 | ❌ | partial | per-pair | ⚠️ |
| TAP-Net | 2022 | ❌ | ✅ | ✅ | ❌ offline |
| **CoTracker** | 2023 | ✅ | ✅ | ✅ | ⚠️ |
| **CoTracker3 online** | 2024 | ✅ | ✅ | streaming | ✅ small N |
| VGGT head | 2025 | ✅ views | partial | bundled | ⚠️ |

> **🎤 Interview Tip.** "追踪 5-秒 episode 中 50 个接触点穿越手遮？" — *"CoTracker3 online，query 点在初始接触配置. KLT 遮挡下丢一半. RAFT 是密集短时序，原语错."* "用 optical flow 追" 把稀疏长时序与密集短时序混淆.

---

## 8 · GitHub Deep Dive (2026-05, co-tracker + tapnet 仓 issue 区交叉考古)

> **来源**：[facebookresearch/co-tracker/issues](https://github.com/facebookresearch/co-tracker/issues)（4.9k★，按 comment 数排序前 25）+ [google-deepmind/tapnet/issues](https://github.com/google-deepmind/tapnet/issues)（TAP-Net / TAPIR / BootsTAPIR / TAPNext 全家桶，按 comment 数前 25）。本节用 atlas 同一套规则做 GitHub-validated 失败模式与读者实务含义。

### 8.1 Pitfall 总表（按真实痛点 × 仓库交叉打分）

| Pitfall 类别 | 高 ROI 实务含义（读者层面） | CoTracker 验证 issue | TAPNet 全家桶验证 issue |
|---|---|---|---|
| **长视频 OOM / 滑窗内存爆炸** | 3 min Colab 视频直接 OOM；任何 episode >1024 frames 必须自己切窗 + stitch | [#51](https://github.com/facebookresearch/co-tracker/issues/51) 14c open（"used co-tracker for videos of up to 3min ... Colab GPU ran out of memory"）· [#65](https://github.com/facebookresearch/co-tracker/issues/65) 10c · [#179](https://github.com/facebookresearch/co-tracker/issues/179) 6c "Evaluating offline model in robotap raise oom" | [#48](https://github.com/google-deepmind/tapnet/issues/48) 8c "OOM error" closed · [#71](https://github.com/google-deepmind/tapnet/issues/71) 10c live_demo 想加点 → GPU 不够 |
| **实时 / 在线 / 流式语义不清** | "online" 论文叙事 ≠ 工程 streaming；window_len 锁 16 不能调小 | [#37](https://github.com/facebookresearch/co-tracker/issues/37) 21c open 4 年（"is there any possibility to port ... to live videos"）· [#54](https://github.com/facebookresearch/co-tracker/issues/54) 8c · [#123](https://github.com/facebookresearch/co-tracker/issues/123) 8c "Does offline mode support v2?"（双模式 checkpoint 不通）· **[#144](https://github.com/facebookresearch/co-tracker/issues/144) 7c open "Not really an online point tracking method"**（"the online point tracker does not permit window_len < 16 due to error with time_emb dims that are loaded from ckpt"）· [#175](https://github.com/facebookresearch/co-tracker/issues/175) | **[#143](https://github.com/google-deepmind/tapnet/issues/143) 20c closed "TAPNext online tracking problems"**（"after running several frames, the tracking points are out of target"） |
| **稀疏点 / webcam / 单点跟踪** | 单点 query 不稳，需要 ≥ N 点共建 attention | [#71](https://github.com/facebookresearch/co-tracker/issues/71) 8c open webcam 单点（"track the point without putting all the frames as a batch"）· [#24](https://github.com/facebookresearch/co-tracker/issues/24) 8c open 动物腿 "The tracking points of two legs often changes to those of one leg" | [#71](https://github.com/google-deepmind/tapnet/issues/71) 10c "Potential to track more points in live_demo.py" |
| **遮挡 / 反射 / boundary** | 静默失败：轨迹平滑但错；反射面上轨追到镜像 | [#44](https://github.com/facebookresearch/co-tracker/issues/44) 5c open specular（"tracked the reflected content and the occlusion logic seems to be off"）· [#173](https://github.com/facebookresearch/co-tracker/issues/173) "Barely moving queries on the boundary of the frame" · [#24](https://github.com/facebookresearch/co-tracker/issues/24) 动物腿混淆 | [#119](https://github.com/google-deepmind/tapnet/issues/119) tracking effectiveness · [#54](https://github.com/google-deepmind/tapnet/issues/54) 高分辨率 visibility 失效 |
| **导出 ONNX / 部署边缘** | 5D GridSample ONNX 不支持；TorchScript 同样卡 | [#10](https://github.com/facebookresearch/co-tracker/issues/10) 10c closed 但社区方案碎片化 | **[#79](https://github.com/google-deepmind/tapnet/issues/79) 10c open** "OnnxExporterError: Unsupported: ONNX export of operator GridSample with 5D volumetric input" · [#83](https://github.com/google-deepmind/tapnet/issues/83) Torchscript |
| **TAPNext 1024 点硬限制** | 源码 `tapnext_torch.py#L286` 写死，dense 跟踪退化 | — | **[#147](https://github.com/google-deepmind/tapnet/issues/147) 7c closed "TapNext 1024 points limit"** |
| **TAPNext 训练 / 微调路径缺失** | 想 fine-tune 到机器人数据无门 | — | **[#141](https://github.com/google-deepmind/tapnet/issues/141) 18c open** "Any plan to release TAPNext training code?"（"I want to fine-tune TAPNext. But it seems that training code is not yet released"） |
| **TAP-Vid 3D 数据 / 标注闭源** | 跨视图 / 3D 任意点基准复现卡住 | — | [#115](https://github.com/google-deepmind/tapnet/issues/115) 25c open · [#142](https://github.com/google-deepmind/tapnet/issues/142) Aria 标注 release 请求 |
| **Windows / JAX / CUDA 平台矩阵** | 实验室落地常踩 | — | [#156](https://github.com/google-deepmind/tapnet/issues/156) "Running TapNext on windows with cuda jax support" · [#49](https://github.com/google-deepmind/tapnet/issues/49) 13c · [#127](https://github.com/google-deepmind/tapnet/issues/127) "GPU PyTorch slower than cpu" |
| **训练复现 / Kubric 配置漂移** | CoTracker3 要 seq_len=64，旧 Kubric 不能用；自训不易 | [#8](https://github.com/facebookresearch/co-tracker/issues/8) 29c · [#130](https://github.com/facebookresearch/co-tracker/issues/130) "CoTracker3 requires a seq_len of 64, while CoTracker2 only needs ... 24" · [#149](https://github.com/facebookresearch/co-tracker/issues/149) 6c | [#90](https://github.com/google-deepmind/tapnet/issues/90) 13c "Training TAPIR PyTorch version script?" |
| **商用 license / 重发布** | CoTracker 默认非商用，DINOv2 式 relicense 未排上 | [#31](https://github.com/facebookresearch/co-tracker/issues/31) 11c open "Is a relicensing planned like Dinov2?" | — |
| **TAP vs CoTracker 比较 / 迁移** | 评测口径不齐 — TAP-Vid 论文里 PIPs 没正式对比，社区自己测；CoTracker offline/online checkpoint 切换无统一接口 | [#123](https://github.com/facebookresearch/co-tracker/issues/123) 双模式 checkpoint 不通 | [#3](https://github.com/google-deepmind/tapnet/issues/3) 7c closed "Comparison between TAP-Net and PIPs"（官方未给数据） |

### 8.2 仓库健康度

| 维度 | CoTracker | TAPNet 全家桶 |
|---|---|---|
| Star | 4.9k | ~1.9k（TAP-Net+TAPIR+TAPNext 单仓） |
| Open issue 当前 | ~80+（138/181 区间多数 open） | ~60+ |
| 维护者响应 | **稀疏** — #37 (2023) / #51 / #144 多年无官方回复 | TAPNext 上线后部分回复（#143 closed），但训练码 #141 18c 仍 open |
| 新版本节奏 | CoTracker3 (2024) → 2025/26 静默；v2/v3 接口断层 #123 | TAPNext 2025 发布、Track-On 2025；旧 TAPIR 渐冷 |
| 文档质量 | 论文+notebook 强，但 "online" 边界、license、ONNX 三块持续缺 | 训练复现、3D 数据释放、平台矩阵长期欠账 |
| **致命缺口** | 长视频 streaming memory API 没有官方接管 | **TAPNext 1024 点 + 训练码缺 + ONNX 5D GridSample** 三件套 |

### 8.3 讀者實務含義（高 ROI 行动清单）

1. **>1024 frames 必须自己滑窗**：CoTracker 没有原生超长视频 API（#51 4 年 open），实务做法 = 切 32–64 帧窗 + 末帧 query 延续 + 自己 stitch trajectory；预算长 episode 时直接把 OOM 写进风险表。
2. **"Online" 别只看论文叙事**：[#144](https://github.com/facebookresearch/co-tracker/issues/144) 标题就是定论 — *"Not really an online point tracking method"*；CoTracker3 online 仍要 `window_len=16` 缓冲（30 Hz 控制紧时不达 budget）。要真流式 → TAPNext streaming 路径或自研。
3. **稀疏点 / 单点不要孤注一掷**：webcam 单点 + 动物腿场景（#71、#24）社区一致反馈不稳；接触点至少 16+ 同表面 query 让 cross-track attention 才有信号。
4. **边缘部署先决问题就是 5D GridSample**：[tapnet #79](https://github.com/google-deepmind/tapnet/issues/79) 直接说 ONNX 不支持；Mobile / Orin 路线现阶段要么改算子要么留服务端做。
5. **要 fine-tune TAPNext 现在不行**：[#141](https://github.com/google-deepmind/tapnet/issues/141) 仍 open；机器人接触点上 domain shift 无微调能力 = 视觉策略层只能当冻结特征用。
6. **TAPNext 1024 点是硬天花板**：[#147](https://github.com/google-deepmind/tapnet/issues/147) 源码写死，dense 跟踪场景退化；超过得分批跑 + 手动 stitch（与 §1024 frames 同病）。
7. **TAP vs CoTracker 选型按"是否要 online"**：要 streaming + 单/双卡 → CoTracker3 online；要纯 offline 高精度 + 跨视频迁移性 → BootsTAPIR / TAPNext；要 3D 任意点 → TAP-Vid 3D 路线但当前数据/标注释放卡（#115）。
8. **商用项目避开 CoTracker 默认 license**：[#31](https://github.com/facebookresearch/co-tracker/issues/31) relicense 未排，避免事后撤项目。
9. **TAPNext online 也有"漂出 target"问题**：[#143](https://github.com/google-deepmind/tapnet/issues/143) 官方回复仍未根治 — 不要假设迁移到 TAPNext 就把 CoTracker online 缺口完全填平。

---

## Bridge to action policies

输出 `(N, T, 2)` 轨迹 + `(N, T)` 可见性 = flow-conditioned VLA 消费的*接触点表示*. 完整故事见 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

## References

- CoTracker — *ECCV 2024*. https://arxiv.org/abs/2307.07635
- CoTracker3 — https://github.com/facebookresearch/co-tracker
- TAP-Vid / TAP-Net — *NeurIPS 2022*. https://arxiv.org/abs/2211.03726
- TAPIR — *ICCV 2023*. https://arxiv.org/abs/2306.08637
- Kubric — *CVPR 2022*. https://arxiv.org/abs/2203.03570

## Boundary

**稀疏长时序任意点追踪**. 密集 flow → [`raft_optical_flow.md`](./raft_optical_flow.md). 刚体 pose → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md). FF-3D-bundled tracking → [`../feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md). VLA 消费 → [`../../bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).

---

[← Back to README](./overview.md)
