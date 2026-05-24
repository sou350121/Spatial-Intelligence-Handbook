# 算力预算 — 平台等级与模型选型 / Compute Budget per Platform

**Status:** v1 — opinionated draft. TOPS / 功耗 / 显存数字标 `UNVERIFIED`，需以 NVIDIA spec sheet 为准。
**TL;DR:** 学术论文一般默认你有桌面级 GPU；现实里大多数 embodied 平台跑在 8–60 W 的边缘模块上。这页给的是一个**决策树**：给定平台等级，哪些空间模型能实时跑、哪些只能离线、哪些必须挪到云端。结论看起来无聊但很重要 —— Orin Nano 上跑 VGGT-large 不现实，跑 VGGT-distilled + 量化才有戏。

---

## 1 · 为什么要单独写这一页

学界论文谈延迟时经常用「在 A100 上 30 ms」之类的数字。这不是欺骗，但是一个工程师从来不会复用的数字。embodied 平台的真实约束是：

- 总功耗预算（无人机 8–25 W，机器人 25–60 W，车 100–500 W）
- 散热（被动 / 主动 / 液冷的边界）
- 显存（Orin 系列 4–32 GB 共享显存 vs 桌面独显 8–48 GB 独立显存）
- 整机其余进程的占用（IMU 驱动、控制器、规划器、通讯栈都要钱）

桌面 spec → 平台部署的换算常常出错，且没有任何综述会替你做。这是手册非要写的工程账。

---

## 2 · 平台等级表（NVIDIA 边缘谱系为锚 — 数字 `UNVERIFIED`）

| 等级 | 代表平台 | 功耗（max） | AI TOPS（INT8） | 共享显存 | 现实场景 |
|---|---|---|---|---|---|
| **入门** | Jetson Orin Nano (8 GB) | 7–15 W | ~40 TOPS | 8 GB LPDDR5 | 小型无人机、低成本 AGV、消费机器人 |
| **主流** | Jetson Orin NX (16 GB) | 10–25 W | ~100 TOPS | 16 GB LPDDR5 | 中型无人机、商用 AGV、协作机器人 |
| **高端边缘** | Jetson AGX Orin (64 GB) | 15–60 W | ~275 TOPS | 64 GB LPDDR5 | 人形机器人主控、L2+ 车载、研究平台 |
| **车规高端** | NVIDIA DRIVE Thor / Orin X | 80–500 W | 1000+ TOPS（Thor） | 64+ GB | L3/L4 量产车 |
| **桌面 / 工作站** | RTX 4090 / 5090 / L40 | 250–600 W | 1300+ TOPS | 24–48 GB GDDR | 训练、回放、离线建图 |
| **云端** | H100 / B200 / GB200 | 700–1200 W | 4000+ TOPS | 80–192 GB HBM | 训练、批量生成、不参与机载推理 |

数字均**未经独立核对**；任何工程决策必须以 NVIDIA datasheet 为准。

---

## 3 · 主流空间模型的足迹（粗估 — 全部 `UNVERIFIED`）

| 模型 / 任务 | 输入 | 显存（FP16） | 桌面延迟 | Orin AGX 延迟 | Orin NX 延迟 | Orin Nano 延迟 |
|---|---|---|---|---|---|---|
| **3DGS 渲染**（10 万 splats） | 相机位姿 | ~2 GB | &lt;5 ms | ~10 ms | ~20 ms | ~50 ms |
| **3DGS 渲染**（1 M splats） | 相机位姿 | ~8 GB | ~15 ms | ~40 ms | OOM 风险 | OOM |
| **VGGT-large**（N=8 views） | RGB | ~6 GB | ~50 ms | ~200 ms | ~400 ms | 不可行 |
| **VGGT-distilled** `UNVERIFIED` | RGB | ~3 GB | ~25 ms | ~100 ms | ~200 ms | ~400 ms（边缘可行） |
| **Depth Foundation**（Depth Anything V2 small） | RGB 单图 | ~1 GB | ~10 ms | ~30 ms | ~50 ms | ~100 ms |
| **Depth Foundation**（V2 large） | RGB 单图 | ~3 GB | ~30 ms | ~80 ms | ~150 ms | 边界可行 |
| **VLM 空间推理**（7B Q4） | RGB + prompt | ~5 GB | ~200 ms / 100 tok | ~600 ms | ~1.5 s | 不可行 |
| **VLM 空间推理**（72B） | RGB + prompt | ~40 GB | ~1 s / 100 tok | 不可行（显存） | 不可行 | 不可行 |
| **VINS-Mono / OpenVINS** | RGB + IMU | &lt;500 MB | &lt;10 ms | &lt;10 ms | &lt;15 ms | &lt;20 ms |
| **BEVFormer-base** | 6 cam | ~6 GB | ~50 ms | ~200 ms | ~400 ms | 不可行 |
| **Occupancy network**（AD 量产） | 6–8 cam | ~8 GB | ~70 ms | ~250 ms | OOM 风险 | 不可行 |

所有数字都**未独立验证**。请把这张表当**量级参考**，不是承诺。

---

## 4 · 决策树 — 给定平台，选哪个模型

```
预算 ≤ 15 W（Orin Nano 级别）
  ├─ 实时需要 ≥ 30 Hz 状态估计 → 上经典 VINS / OpenVINS
  ├─ 需要稠密深度（≥10 Hz） → Depth Anything V2 small + 量化
  ├─ 需要 3DGS 渲染 → 控制场景规模在 10 万 splats 以内
  └─ 想跑 VGGT / 大 VLM → 不要

预算 15–30 W（Orin NX 级别）
  ├─ 同上 + 可加 VGGT-distilled 作低频几何 anchor（5 Hz）
  ├─ 7B 量化 VLM 可以离线 / 异步用，不要进主控制回路
  └─ 中等 occupancy network 边界可行

预算 30–60 W（AGX Orin 级别）
  ├─ 这是「大多数 embodied 研究项目」的真实平台
  ├─ VGGT-distilled 实时可行；VGGT-large 5 Hz 可行
  ├─ 7B VLM 在 1 Hz 可作高层规划
  ├─ AD-scale occupancy network 边界可行
  └─ 仍要给操作系统、控制器、规划器留至少 30% headroom

预算 ≥ 100 W（车规 / 桌面）
  ├─ 几乎所有方法都可以同时跑
  ├─ 真正限制变成功耗 / 散热 / 显存峰值，不是算力
  └─ 显存峰值通常先爆，不是 TOPS
```

---

## 5 · 量化、蒸馏、token reduction —— 把模型挤进预算的真实手段

学界谈推理延迟是 FP16 默认；工程上要把 8 W 平台跑起来，需要叠加：

| 手段 | 大致收益（量级 `UNVERIFIED`） | 主要副作用 |
|---|---|---|
| FP16 → INT8 量化 | 1.5–2× 加速；显存对半 | 精度下降，关键层（attention output）通常要保留 |
| FP16 → INT4 / NF4 | 3–4× 加速；显存 1/4 | 精度明显下降，主要用于 LLM/VLM 权重 |
| 蒸馏到小模型 | 2–10× 取决于规模差 | 精度下降；需要重新训练 |
| Token reduction（ViT 谱系） | 1.5–3× | 对密集预测任务（深度、occupancy）副作用大 |
| 多帧流式化（Streaming） | 实时延迟降低但单帧延迟不变 | 需要重新设计输入 |
| 模型分片到 NVDLA | 释放 GPU；NVDLA 算力较小 | NVDLA 算子覆盖有限 |

经验上，工业部署的「VGGT 实时」全部依赖蒸馏 + 量化 + token reduction 三件套组合，**单一手段不够**。

---

## 6 · 常见踩坑

- **「我有 60 W 预算」 ≠ 「我可以一次跑 60 W」**。散热被动 / 主动是硬约束，AGX Orin 默认 MAXN 模式下散热不解决就降频。
- **共享显存不是独显**。Orin 系列 CPU 和 GPU 共用 LPDDR5；同一块 16 GB 既要装系统 + 控制器 + 规划器，又要装模型，留给模型的常常只有 6–8 GB。
- **峰值显存 ≠ 平均显存**。VGGT 多视图时显存峰值远超平均，OOM 几乎都发生在峰值瞬间。
- **延迟方差** > 平均延迟。控制器关心 P99 不是平均。
- **整机其它进程的隐藏开销** 通常吃掉 20–40% TOPS（IMU 驱动、ROS / DDS 通讯、规划器、日志、SLAM 后端）。

---

## 7 · 2-year outlook + 可证伪预测

边缘算力两条线在动：(a) NVIDIA Thor 量产把车规平台抬到 1000+ TOPS / 80–500 W；(b) Orin Nano Super / 后继款 把入门级抬到 ~70 TOPS / 15 W。两条线在 2026–2027 间会让现在「不可行」的组合变成「边界可行」。

**可证伪预测：** 2027-12 之前会出现一篇 published 工作，演示 VGGT-class 模型 + 7B VLM 同时在 25 W 平台上 ≥ 10 Hz 运行，且在 EuRoC 之类真机基线上不输给 VINS-Fusion。如果到那个时点没有，这一波边缘空间 AI 仍受限于算力，不是受限于算法。

---

## For the reader

- **机器人 / 无人机工程师** —— §4 决策树是日常工具；记住「TOPS 不是显存」。
- **算法研究者** —— 论文报告延迟时多带一组 Orin AGX 数字，没人逼你也没人感谢你，但工程界会记住。
- **采购 / 产品** —— 别把桌面 spec 当目标平台；这张表里几乎所有「不可行」单元格都是产品计划坑里捞出来的。

---

## References (starter set)

- NVIDIA Jetson Orin spec sheets — https://developer.nvidia.com/embedded/jetson-modules `UNVERIFIED, no DOI`
- NVIDIA DRIVE Thor announcement — GTC 2024 keynote `UNVERIFIED`
- Depth Anything V2 — Yang et al., 2024. https://arxiv.org/abs/2406.09414
- VGGT — Wang et al., *CVPR 2025*. [arXiv link TBD]
- OpenVINS — Geneva et al., *ICRA 2020*. https://arxiv.org/abs/1910.00298

## Boundary

本文是平台 → 模型可行性的工程账，不是硬件选型指南。硬件选型谱系（具体 SKU、价格、供应链）归 [deployment/hardware-selection/](../hardware-selection/)。模型本身的 dissection 归 [foundations/](../../foundations/)。所有数字必须以官方 datasheet 为准。

⚙️ 初稿由 Moltbot 自动生成 | 2026-05-21
