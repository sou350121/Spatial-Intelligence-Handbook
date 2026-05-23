# VLM Spatial Reasoning

**Status:** v1.1 — seed zone → 完整 zone（2026-05-21 扩充：+ SpatialBot + 3DSRBench）。Capability claims marked `UNVERIFIED` where not personally measured.
**TL;DR:** 通用 VLM（GPT-4V、Claude、Gemini、Qwen-VL）*默认是扁平的*——能命名物体，但无法可靠说出谁更近、距离多远、夹爪该往哪去。让 VLM 推理 3D 是一个训练问题，不是 prompt 问题。三种方法竞争：synthetic 空间 QA 的隐式预训练（SpatialVLM）、显式 caption / depth token（SpatialBot 血统）、3D-aware benchmark 训练。每种押在不同瓶颈上。

---

## VLM 是扁的——不训不会推 3D

2025 年现成 VLM 的默认行为，是把图当 2D 语义场景。它会高准确率告诉你"there is a mug and a keyboard"，被问"mug 比 keyboard 更近吗？"或"mug 把手离桌面多少厘米？"时则失败——或自信地胡说。原因是结构性的：训练数据是来自网络的 image-caption 对，而网络 caption 是命名 caption，不是空间关系 caption。模型有特征能*回答*空间问题；只是从来没被*教过*把它们浮上来。

这对机器人很重要，因为 VLM 是把语言目标接到感知系统上的最便宜接口。如果 VLM 能可靠回答"夹爪该往哪去？"，半个 semantic-3D 管线（见 [`foundations/semantic-3d/`](../semantic-3d/overview.md)）就可以省掉。本 lane 的论文都回答一个问题：**鉴于单靠架构小技巧不够，如何让 VLM 给出 3D-grounded 答案？**

## The 3 approaches

- **隐式预训练（SpatialVLM, Google DeepMind 2024）**。在网络图像上跑深度估计与开集分割，自动合成海量 spatial QA 对再微调。*押注：*空间监督规模是杠杆；模型已看见几何，只需被教会说。*代价：*精确 metric 答案不稳，遮挡推理弱。
- **显式 caption / depth token（SpatialBot 血统, 2024）**。把 depth image 或文本场景摘要（`object A at 0.4 m, B at 0.7 m`）作为输入注入。*押注：*VLM 不擅长从 RGB *抽*几何，擅长在被喂时*消费*几何。*代价：*推理期与传感器绑定。
- **3D-aware benchmark 训练**。端到端在目标 benchmark（SpatialBench、EmbodiedQA、VSR）上训，通常配 3D-aware backbone。*押注：*benchmark 抓住了对的能力，且会迁移。*代价：*benchmark 经常抓不到机器人需要的东西。

横着读：SpatialVLM 押*数据*，SpatialBot 押*输入*，benchmark 训练押*任务*。2026+ 最强的系统会把隐式预训练与显式 depth token 结合。

---

## Contents

| File | Topic | Tier |
|---|---|---|
| `spatialvlm_dissection.md` | Chen et al. CVPR 2024 — 2B 自动合成的空间 QA，"数据规模"论点 | ⚡ |
| `spatialbot_dissection.md` | Cai et al. 2024 — depth map 当第二模态喂 VLM，3B `UNVERIFIED` 追平 GPT-4o depth tasks | ⚡ |
| `3dsrbench_dissection.md` | Ma et al. ICCV 2025 — 2,772 题 4×12 子类 benchmark，旗舰 VLM 仅 49% real-split | 🔧 |

Zone 从 seed（仅 SpatialVLM）扩为完整 zone：两路 model（implicit pretraining vs explicit depth tokens）+ 独立 benchmark 裁判。`UNVERIFIED` SpatialRGPT、ManipLLM、具身 VLA 联合训练 queued for v2。

## Cross-references

- 把语言 grounded 到几何的*另一种*方式（semantic 3D lifting）→ [`foundations/semantic-3d/`](../semantic-3d/overview.md)
- 空间推理 benchmark → [`benchmarks/reasoning/`](../../benchmarks/reasoning/)（TBD）
- VLM 空间输出 → 策略动作 → [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md)（SpatialVLM caption 集成是逆向案例）
- 跨具身体对比（"VLM as perception" vs "VLM + 显式 3D"）→ [`crossing/representation-migration/`](../../crossing/representation-migration/) — 已 2 篇（`3dgs_as_simulator_comparison.md` + `dense_vs_graph_registration.md`）

## Boundary

本目录是关于 VLM 如何对空间推理的 per-method 解构。它**不**覆盖：显式 3D 语义抬升（→ `foundations/semantic-3d/`）；无空间视角的通用 VLM 架构（out of scope）；3D-aware VLA action head（→ [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)，`bridge-to-vla/`）；具身侧部署（→ `embodiments/<emb>/`）。
