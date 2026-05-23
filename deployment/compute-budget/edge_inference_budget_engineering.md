# 边缘推理预算工程化 / Edge Inference Budget Engineering

> **发布时间**：2026-05-21
> **适用范围**：Orin Nano / Orin NX / Orin AGX / Xavier / CPU-only 各档算力 × 空间感知 stack 组合
> **核心定位**：把「我有 X TOPS / Y GB 显存」翻译成「能跑哪几个空间模型同时、各自多少 Hz、留多少 headroom 给控制器」——这是从 spec sheet 到可飞 / 可走 robot 的真实算术。

**Status:** v1 — opinionated draft。所有 TOPS / 延迟 / 显存数字均 `UNVERIFIED`，需以 NVIDIA spec sheet + 平台实测为准；ML kernel 优化半年一翻篇。
**Wedge tier:** N/A（deployment 工程文，配套 `deployment/compute-budget/README.md` §2 平台等级表）
**TL;DR:** 论文延迟数字（A100 30 ms）几乎从不直接告诉你「这能不能在我的 25 W 边缘平台跑」。本文给「平台等级 × 模型类别」的可行性矩阵 + 量化 / 蒸馏 / token reduction 的具体收益数字 + 三类典型 robot（drone / manipulation / AGV）的实战 budget allocation 案例。结论：**Orin AGX 上跑「VGGT-distilled + Depth Foundation small + 7B Q4 VLM」是 2026 年可行的 demo-级组合；产品级仍需要叠加 quantization-aware training 与 token pruning**。

### X-Ray 开场（非专家友好）

(a) 边缘算力预算 = 把 spec sheet 的 TOPS / 显存 / 功耗翻译成可运行模型的组合。(b) 关键不是「能跑哪个模型」而是「同时能跑哪几个模型 + 留多少给控制器 / 通讯 / 日志」——满负载只能跑一个模型的平台基本没用。(c) 对 robotics 工程师：本文是「桌面 GPU → 边缘 SoC」的换算手册，省去把 published latency 当部署 latency 的常见坑。

### 📍 研究全景时间线

```
2014 ── Jetson TK1（192 CUDA cores, 10 W） — robot 边缘 GPU 起点
2017 ── TensorRT 3 + INT8 校准 — 量产 INT8 实用化
2019 ── Jetson Xavier NX（21 TOPS, 15 W） — 第一波「桌面级模型可在边缘跑」
2021 ── Orin 系列发布（40–275 TOPS）— 边缘算力 ×10
2022 ── llama.cpp / GGUF INT4 — 7B LLM 在 8 GB 显存能跑
2023 ── Depth Anything / SAM 蒸馏潮 — 视觉 foundation model 边缘可用
2024 ── VGGT / DUSt3R — feed-forward 3D 几何提供新基线
2025 ── DRIVE Thor 量产化（1000+ TOPS） — 车规算力天花板抬高
        ── 你在这里 (2026) ──
?    ── chip-scale photonic accelerator（实验室）vs Orin Nano Super 量产平民化
?    ── 端侧 MoE / sparse activation 让有效算力 ×3–5
```

`deployment/compute-budget/README.md` 给的是平台等级 + 模型足迹表；本文给的是「budget 怎么分配 + 三件套量化 / 蒸馏 / pruning 怎么搭」的工程实操。

---

## 1 · 预算分配的 Napkin Formula

📌 **Napkin Formula**：

```
usable_budget = nominal_TOPS × util × (1 - os_overhead - headroom)
  util         ≈ 0.5–0.7   ← 实际 kernel 效率，FP16 比 INT8 低
  os_overhead  ≈ 0.10–0.20 ← ROS/DDS、IMU 驱动、规划器、日志
  headroom     ≈ 0.20–0.30 ← P99 峰值缓冲 + 散热降频

所以：
  Orin AGX 标称 275 TOPS → 可用 ≈ 80–130 TOPS（保守）
  Orin Nano 标称 40 TOPS → 可用 ≈ 12–20 TOPS
```

这是为什么「桌面 50 ms = 边缘 200–400 ms」的根因——不是只看 TOPS 比，要叠上 util / overhead / headroom。

| 资源 | 桌面 RTX 4090 | Orin AGX | Orin NX | Orin Nano |
|---|---|---|---|---|
| 标称 TOPS（INT8 `UNVERIFIED`） | 1300+ | 275 | 100 | 40 |
| 可用 TOPS（保守估） | 800+ | 80–130 | 30–50 | 12–20 |
| 显存（GB） | 24（独显） | 64（共享） | 16（共享） | 8（共享） |
| 模型实际可用显存 | 20+ | 30–40 | 6–10 | 3–5 |
| 功耗 max | 450 W | 60 W | 25 W | 15 W |

「模型实际可用显存」减去的部分：OS + ROS + cuDNN context + 各种 buffer，常占 8–25 GB（共享显存的代价）。

---

## 2 · 推理栈：FFmpeg / nvJPEG / TensorRT / ONNX / quantization

边缘推理不是只跑模型；从摄像头到推理结果是一条流水线，每一段都有自己的算力开销。

### 2.1 流水线

```
[CSI/USB camera]
   ↓ (raw bayer 或 MJPEG)
[ISP / debayer]                ← Orin 内置 VI/ISP，几乎零 CPU
   ↓ (YUV/RGB tensor)
[nvJPEG decode 或 GStreamer]    ← 如果 MJPEG/H.264 输入
   ↓ (CUDA tensor)
[resize / normalize]            ← npp / TensorRT plugin
   ↓
[TensorRT engine]               ← 主推理
   ↓ (logits / depth / pose)
[后处理 / output]
   ↓
[ROS topic / DDS publish]
```

**经验数字 `UNVERIFIED`**：

- 整条流水线非推理部分通常占 20–40% 端到端延迟。
- ROS 2 + DDS 跨进程 publish 在 Orin 上单帧可能 5–15 ms。
- nvJPEG decode 4K 一帧 ~3–8 ms。
- TensorRT INT8 vs FP16 的 1.5–2× 加速是在 GPU 部分，不会让流水线整体 ×2。

### 2.2 优化手段排序（按 ROI）

| 优化 | 典型加速（`UNVERIFIED`） | 副作用 | 难度 |
|---|---|---|---|
| TensorRT FP16 替代 PyTorch FP32 | 3–5× | 精度需验证 | 🟢 |
| TensorRT INT8（PTQ） | 1.5–2× over FP16 | 精度可降 0.5–2% | 🟡 |
| TensorRT INT8（QAT） | 1.5–2× over FP16 | 精度损失最小 | 🔴 |
| ONNX 转 TensorRT（避免 Python） | 2–3× | 调试难度上升 | 🟡 |
| 共用 CUDA stream + zero-copy | 1.2–1.5× | 工程复杂度 | 🔴 |
| GStreamer hardware decode | 大幅省 CPU | 灵活性 ↓ | 🟢 |
| Token pruning（ViT/VLM） | 1.5–3× | 任务相关 | 🟡 |
| 蒸馏到小模型 | 2–10× | 重新训练 | 🔴 |

### 2.3 量化谱

```
FP32 → FP16 → BF16 → INT8 → INT4 → binary
  权重        ←--- 通用 ---→     ←-- LLM 主战场 --→
  激活        FP16/INT8 常见     INT8 极限
```

经验上：

- **CNN 主流**：FP16 训练 + INT8 PTQ；精度损失常 <1%。
- **ViT / 几何模型（VGGT / DUSt3R）**：FP16 + 选择性 INT8（attention output 保 FP16），混合精度。
- **VLM**：INT4 GGUF（GGML/llama.cpp）是 7B 在 8 GB 显存的唯一路；INT8 需要 ≥10 GB。
- **Depth Foundation / SAM**：FP16 PTQ 多数足够；个别 layer（normalize）保 FP32。

---

## 3 · 主流空间模型在边缘的可行性深度账（粗估全部 `UNVERIFIED`）

`deployment/compute-budget/README.md` §3 已给延迟表；本节给「为什么这个延迟」的拆解。

### 3.1 VINS-Fusion / OpenVINS（经典 VIO）

| 平台 | 延迟 | 备注 |
|---|---|---|
| 桌面 i7 | <10 ms | CPU-only，无 GPU 使用 |
| Orin AGX | <10 ms | 同上 |
| Orin Nano | <20 ms | 单核 ARM A78AE，FOV 大时 feature 多会慢 |

VIO 是 CPU bound，加 GPU 不会更快；优化方向是 SIMD（NEON）+ 数据结构 + 因子图增量更新。Skydio / DJI 巡检 drone 的「VIO + IMU」估计回路常常完全跑在 CPU 上，把 GPU 留给深度学习。

### 3.2 ORB-SLAM3 vs VINS-Fusion 在 Orin Nano 上的 head-to-head

| 项 | ORB-SLAM3 | VINS-Fusion |
|---|---|---|
| 单帧延迟（Orin Nano） | 30–60 ms `UNVERIFIED` | <20 ms |
| CPU 占用 | 60–90%（feature 检测 + ORB）| 30–60% |
| 内存 | <500 MB | <500 MB |
| 后端 | bundle adjustment（重） | sliding window factor graph |
| 闭环 | ✅ | ✅（FAST + DBoW） |
| 适合场景 | 静态环境 + 较慢动态 | 高动态 / drone |

经验：drone 上几乎都选 VINS / OpenVINS；AGV 在静态场景下 ORB-SLAM3 闭环效果好但单帧延迟高。

### 3.3 VGGT vs VGGT-distilled vs Depth Foundation

VGGT-large 在 Orin AGX 跑 ~200 ms 是「不可用于控制回路」级别，但 5 Hz 「low-rate 几何 anchor」可行（把它当 sparse loop-closure 提供器）。蒸馏版 `UNVERIFIED` 到 ~100 ms 可作为 10 Hz 主深度。Depth Anything V2 small 是另一条路（单图 RGB → depth，~30 ms on Orin AGX）。

**典型组合（drone 巡检 1.5 kg）**：

```
30 Hz   ← VINS-Fusion (CPU)        ← 主状态
10 Hz   ← Depth Anything V2 small  ← 主深度
 5 Hz   ← VGGT-distilled            ← 几何 anchor + loop check
 1 Hz   ← 7B Q4 VLM                 ← 高层 reasoning（异步，不在控制回路）
```

总 GPU 占用 ~60% on Orin AGX；CPU 占用 ~40%；显存峰值 ~12 GB / 64 GB 共享。

### 3.4 7B / 72B VLM 实战

| VLM 配置 | Orin AGX 延迟（100 token） | 显存 |
|---|---|---|
| Qwen2-VL 7B FP16 | OOM 风险 | ~15 GB |
| Qwen2-VL 7B Q8 | ~800 ms `UNVERIFIED` | ~9 GB |
| Qwen2-VL 7B Q4_K_M | ~500–700 ms | ~5 GB |
| Qwen2-VL 72B Q4 | 不可行（显存） | ~40+ GB |
| Llama-3.2-Vision 11B Q4 | ~700 ms `UNVERIFIED` | ~8 GB |

「VLM 进控制回路」目前**没有产品案例**。所有公开 demo 都用 VLM 做 1 Hz 高层 prompt（move-to-X、open-door 类）+ 经典回路做实时控制。

---

## 4 · 三类 robot 的真实 budget allocation

### 4.1 Drone 巡检 1.5 kg（Orin Nano 8 GB）

```
总预算：~15 W power / 40 TOPS / 8 GB 共享 / 200 g 含散热
┌────────────────────────────┬──────────┬──────┬──────────┐
│ 组件                       │ TOPS     │ 显存 │ 频率     │
├────────────────────────────┼──────────┼──────┼──────────┤
│ VINS-Fusion (CPU only)     │ —        │ 200 M│ 30 Hz    │
│ Depth Anything V2 small Q8 │ 5 TOPS   │ 700 M│ 10 Hz    │
│ Obstacle avoidance (CUDA)  │ 3 TOPS   │ 200 M│ 30 Hz    │
│ Image encode + telemetry   │ 2 TOPS   │ 300 M│ 30 Hz    │
│ ROS 2 / DDS                │ —        │ 500 M│ —        │
│ OS + headroom              │ ~6 TOPS  │ ~3 G │ —        │
├────────────────────────────┼──────────┼──────┼──────────┤
│ 合计                       │ ~16 TOPS │ ~5 GB│           │
│ 余量                       │ ~24 TOPS │ ~3 GB│           │
└────────────────────────────┴──────────┴──────┴──────────┘
```

**注**：VGGT / VLM **不跑**在飞控板上。如果需要语义，云端或地面站做。

### 4.2 Manipulation Cell（Orin AGX 64 GB）

```
总预算：~60 W / 275 TOPS / 64 GB 共享
┌────────────────────────────┬──────────┬──────┬──────────┐
│ 组件                       │ TOPS     │ 显存 │ 频率     │
├────────────────────────────┼──────────┼──────┼──────────┤
│ Depth Foundation (small)   │ 8 TOPS   │ 1 G  │ 30 Hz    │
│ Polarization fusion        │ 5 TOPS   │ 500 M│ 30 Hz    │
│ Grasp net (lightweight)    │ 15 TOPS  │ 2 G  │ 10 Hz    │
│ VGGT-distilled (loop chk)  │ 20 TOPS  │ 3 G  │ 5 Hz     │
│ 7B Q4 VLM (planner)        │ 30 TOPS  │ 6 G  │ 1 Hz     │
│ F/T + tactile fusion (CPU) │ —        │ 200 M│ 1 kHz    │
│ MoveIt 规划                │ —        │ 1 G  │ 10 Hz    │
│ OS + ROS + headroom        │ ~30 TOPS │ ~15 G│ —        │
├────────────────────────────┼──────────┼──────┼──────────┤
│ 合计                       │ ~108 TOPS│ ~29 G│           │
│ 余量                       │ ~22 TOPS │ ~11 G│           │
└────────────────────────────┴──────────┴──────┴──────────┘
```

显存余量比 TOPS 余量紧——这是 manipulation 用 AGX 而不是 NX 的根因。

### 4.3 仓储 AGV（Orin NX 16 GB）

```
总预算：~25 W / 100 TOPS / 16 GB 共享
┌────────────────────────────┬──────────┬──────┬──────────┐
│ 组件                       │ TOPS     │ 显存 │ 频率     │
├────────────────────────────┼──────────┼──────┼──────────┤
│ VINS-Fusion (CPU)          │ —        │ 200 M│ 30 Hz    │
│ Depth Anything V2 small Q8 │ 8 TOPS   │ 1 G  │ 15 Hz    │
│ 2D LiDAR SLAM (CPU)        │ —        │ 300 M│ 10 Hz    │
│ 目标检测 YOLOv8s INT8      │ 12 TOPS  │ 1 G  │ 15 Hz    │
│ Local planner + 控制       │ —        │ 500 M│ 50 Hz    │
│ Fleet 通讯 / telemetry     │ 5 TOPS   │ 500 M│ —        │
│ OS + ROS + headroom        │ ~20 TOPS │ ~5 G │ —        │
├────────────────────────────┼──────────┼──────┼──────────┤
│ 合计                       │ ~45 TOPS │ ~8.5G│           │
│ 余量                       │ ~30 TOPS │ ~3.5G│           │
└────────────────────────────┴──────────┴──────┴──────────┘
```

AGV 的算力余量看起来多，但实际是「未来跑 VLM / 跑更大语义模型」预留的。

---

## 5 · 散热与降频（最容易被忽略的硬约束）

### 5.1 物理

Orin 系列默认 power mode 是 MAXN（满功率），但散热不解决 30 秒就会降频：

| Mode | Orin AGX | 散热要求 |
|---|---|---|
| MAXN (60 W) | 满 TOPS | 主动风扇 + 大热沉 |
| 30 W | ~50% | 中等热沉 + 主动 |
| 15 W | ~25% | 被动 |

**「我跑 benchmark 时 30 ms」**很可能是 MAXN 模式 + 满风扇 + 室温下；deploy 到真 drone 上 40°C 环境 + 被动散热 → 降频到 30 W → 延迟变 60 ms → 控制频率没了。

### 5.2 实测必须项

- 长时（>10 分钟）满载下记录 `tegrastats`：watt / freq / temp。
- 模拟最坏环境（高温箱 / 阳光直射）跑同样 benchmark。
- 看 `dmesg` 是否有 thermal throttle 警告。

「室温 benchmark 数字 ≠ 部署延迟」——这是 spec 与现实最大的 gap 之一。

---

## 6 · 共享显存的陷阱

Orin 系列 CPU + GPU 共享 LPDDR5。这意味着：

- **OS、driver、ROS 节点、模型权重共用一池**。
- 单一进程的 cudaMalloc 失败可能不是「显存不够」，是「碎片化」。
- Peak vs avg：VGGT 多视图时显存峰值远高于平均；OOM 几乎总在 peak 瞬间。
- DMA / camera buffer 与 GPU memory pool 互争。

经验做法：

```bash
# 启动前预留 GPU memory 给主要模型，避免后续碎片
export CUDA_DEVICE_MAX_CONNECTIONS=8
export PYTHONUNBUFFERED=1
# nvidia-smi 在 Orin 不可用；用 tegrastats
sudo tegrastats --interval 100
```

显存监控不可省略；产品级软件应自动监控并在接近阈值时降级（lower resolution、skip frames）。

---

## 7 · Hidden Assumptions

- **TOPS ≠ 实际吞吐**。kernel 效率 / memory bandwidth / batch 影响巨大；INT8 标称 TOPS 是理论峰值。
- **静态 latency 模型不准**。控制器关心 **P99**，不是平均。Linux 抢占 / GC / page fault 让 P99 比平均高 3–10×。
- **「同时跑」假设无 contention**。多个 CUDA stream 共享 SM，实际 inverse-multiplicative slowdown 存在。
- **量化精度损失是任务依赖**。深度估计 INT8 损失 <1%，但小物体检测可能损失 5%+。
- **半年后数字翻篇**。Orin Nano Super 量产、TensorRT 新版本、模型 distillation 进步——本表 2026-05 快照。
- **本表数字 `UNVERIFIED`**——必须以平台实测 + 数据手册为准。

## 8 · 与基线对比 + Interview Tip

| 视角 | 学界论文 | 本文 |
|---|---|---|
| 延迟数字 | 桌面 GPU | 边缘 SoC 5 档 |
| 同时多模型 | 单模型 | 组合 |
| 控制回路集成 | 不涉及 | 频率分层 |
| 散热 / 降频 | 不涉及 | 必谈 |
| 共享显存 / OS 开销 | 不涉及 | 必谈 |
| 量化 / 蒸馏 / pruning 实战收益 | 偶尔 | 必谈 |

**Interview Tip**：被问「这个模型能跑 30 Hz 吗」——别答「桌面 GPU 上 30 ms」，答「桌面 30 ms → 边缘 100–150 ms → 加 quant + distill 可能压到 50 ms → 同时还要给控制器和 ROS 留 30% headroom → 实际 15 Hz 安全、30 Hz 边界」。把每个步骤数字摆出来，对方就知道你做过部署。

---

## 9 · 2-year outlook + 可证伪预测

**可证伪预测：** 到 2027-12 前，至少一篇 published 工作会演示 **VGGT-class 几何模型 + 7B VLM + Depth Foundation 同时在 25 W 平台 ≥ 10 Hz 运行**，且在真机基线（EuRoC / TUM 之外）上不输 VINS-Fusion。如果到那时点没有，「边缘空间 AI = 算力受限」仍成立。

支持线索：(a) Orin Nano Super 即将量产抬高入门档；(b) MoE / sparse activation 大幅降低有效 FLOPS；(c) 多 model 联合蒸馏研究方向已起步。反对线索：散热墙、显存墙、kernel 优化的边际收益递减。

---

## For the reader

- **机器人 / 无人机工程师** —— §4 三类真实 budget allocation 是日常工具；记得给 OS + headroom 预留 30%。
- **算法研究者** —— 论文里至少给一组 Orin AGX 数字 + INT8 量化版本 + P99；这比 SOTA 数字对工程界有用得多。
- **采购 / 产品** —— 别看 spec sheet TOPS 做产品定位；要看「同时跑哪些 + 留多少 headroom」。
- **ML infra** —— TensorRT / ONNX / nvJPEG / GStreamer 整条流水线优化的边际收益常高于换 GPU。

---

## References

- NVIDIA Jetson Orin Spec Sheets — https://developer.nvidia.com/embedded/jetson-modules `UNVERIFIED`
- TensorRT documentation — https://docs.nvidia.com/deeplearning/tensorrt `UNVERIFIED`
- Depth Anything V2 — Yang et al., 2024. https://arxiv.org/abs/2406.09414
- VGGT — Wang et al., *CVPR 2025*. [arXiv TBD]
- VINS-Fusion — Qin et al. *T-RO 2018* https://arxiv.org/abs/1708.03852
- OpenVINS — Geneva et al. *ICRA 2020* https://arxiv.org/abs/1910.00298
- ORB-SLAM3 — Campos et al. *T-RO 2021* https://arxiv.org/abs/2007.11898
- llama.cpp / GGUF — https://github.com/ggerganov/llama.cpp `UNVERIFIED, no DOI`
- 相关交叉文档：`crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md`、`embodiments/aerial/vio/`、`deployment/multi-modal-sync/hardware_trigger_vs_ptp_vs_software.md`

## Boundary

本文写**边缘推理算力 budget 工程实操**。**不写**：模型本身的算法 dissection（去 `foundations/feed-forward-3d/` 等）、硬件选型 BoM（去 `deployment/hardware-selection/bom_templates_by_class.md`）、多平台同步设计（去 `deployment/multi-modal-sync/`）、TensorRT 调优具体 API（去 NVIDIA 官方文档）、训练 cost / 训练硬件（不在本仓边界）。所有数字 `UNVERIFIED`；production 必须实测。

---

[← Back to Compute Budget README](./overview.md)

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
