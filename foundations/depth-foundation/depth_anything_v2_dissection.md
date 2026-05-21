# Depth Anything v2 (Depth Anything v2 解构 — NeurIPS 2024)

> **Published**: 2024-06 (arXiv) / NeurIPS 2024
> **Paper**: Yang et al. — *Depth Anything V2*
> **Team**: HKU + TikTok
> **Core position**: 2024–2026 最强的 relative monocular depth foundation 模型. 靠 data recipe（62M unlabeled 蒸馏叠在 595K 高质量合成上）取胜，不是架构. **输出是 affine-invariant** — 永远别用于 grasp pose.

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**Wedge tier:** W1 · relative-depth foundation
**TL;DR:** Depth Anything v2 (Yang et al. 2024, arXiv 2406.09414) 是 2024–2026 出货的最强 *relative* monocular depth 模型 — 也是最常被误当成 metric 的现成模型. 胜利不在架构，而在 **62M unlabeled 图像通过 teacher-student 环路蒸馏，叠在 595K 高质量带标签合成样本上** `UNVERIFIED counts`. 用于可视化、semantic depth、和预训练. **不要**用于 grasp pose. 输出至多差一个未知 affine — 乘以机器人侧 scale 估计否则会摔杯子.

### X-Ray (non-expert friendly)

(a) 早期 monocular depth 模型（MiDaS、DPT、Depth Anything v1）泛化尚可但脆 — 真实标签有噪声（LiDAR 阴影、kinect 散斑），封死可达精度. (b) v2 的贡献是*数据*：在 595K *合成*干净标签上训 teacher，蒸馏到 62M unlabeled 真实图像上，发学生. 架构（DINOv2 + DPT）没变. (c) 对空间 AI 工程师：这是可得的最佳 relative-depth 预训练，但 affine-invariant 输出让它对任何需要米的任务*无用* — 那是独立轨（Metric3D）.

### 📍 Research Landscape Timeline

```
MiDaS 2020 ─► DPT 2021 ─► Depth Anything v1 2024 ─► ★ Depth Anything v2 NeurIPS 2024 ─► Metric3D / canonical-camera track 2024+ ─► VGGT subsumes 2025
```

v2 是 relative-depth foundation 谱系的顶峰. 下一步要么是 (a) metric-aware fine-tune（与 Metric3D 趋同）要么是 (b) 被多视角 feed-forward (VGGT) 吸收.

---

## 1 · 为什么这篇值得解构

MiDaS (Ranftl et al. 2020) 定义了 relative-depth 泛化模板. Depth Anything v1 (Yang et al. 2024a) 用更大的 DINOv2 骨干推它. **v2 的贡献几乎完全是数据故事**：他们认为真实世界带标签深度数据集充满标签噪声（LiDAR 阴影空洞、photometric stereo 伪影、kinect IR 散斑），且 **合成标签 + 大规模 unlabeled 蒸馏 > 更多真实标签**.

教训泛化到深度之外 — 同样的配方对 SAM-2、DINOv2、VGGT 谱系都 work（见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)）. 对机器人读者，相关问题是这个配方是不是 metric-shaped. **不是.** 给 Depth Anything v2 泛化的同一数据技巧也锁死了 relative-only 约束，因为 unlabeled 蒸馏不提供 scale 信号.

---

> ⚡ **Eureka Moment**: 一旦标签预算够大，真实标签*比合成更差* — LiDAR 阴影空洞、kinect IR 散斑、photometric stereo 伪影都把噪声漏进监督. 在干净合成上训 teacher，然后*蒸馏到 62M unlabeled 真实图像*上桥接 synthetic→real 域差. **Data recipe IS the contribution**；架构与 v1 相同.

## 2 · 架构与训练配方

> 📌 **Napkin Formula**: `Teacher(synthetic 595K) → pseudo-labels for unlabeled 62M → Student(real+pseudo) = final model`. Loss 是 affine-invariant disparity（MiDaS-style）— 预测 disparity up to scale **and shift**，不是度量深度.


| Component | Choice | Why it matters |
|---|---|---|
| Encoder | DINOv2 ViT-S/B/L/G | 预训练视觉特征扛域偏移 |
| Decoder | DPT-style (Ranftl et al. 2021) | 自 MiDaS 起稳定谱系；不花哨 |
| Label source | 595K 合成 (Hypersim + vKITTI + 3D Ken Burns + Synscapes 等) `UNVERIFIED list` | 干净标签，无 LiDAR 阴影 |
| Unlabeled corpus | 62M 张来自 SA-1B + Open Images + Places 等 `UNVERIFIED count` | 泛化驱动 |
| Loss | Affine-invariant SI loss (MiDaS) + gradient matching | 预测 disparity up to scale and shift |
| Distillation | 仅在合成上训 teacher → pseudo-label 62M → student | 真正的贡献 |

```
Synthetic labeled (595K, clean)
        │
        ▼
   Teacher model  ───────────► pseudo-labels for 62M unlabeled images
                                       │
                                       ▼
                                Student model (final Depth Anything v2)
```

Depth Anything v1 与 v2 的架构矩阵几乎相同. **变的是训练语料库和刻意脱离嘈杂真实标签的转向.** 那是头条；其余是工程.

---

## 3 · 它实际赢在哪里（以及 relative-vs-metric 陷阱）

| Use case | Verdict | Reason |
|---|---|---|
| 照片 / 视频深度可视化 | ✅ 同类最佳 | 无 fine-tune 即泛化到手机照、艺术、室内外 |
| 下游任务的 monocular depth 预训练 | ✅ 强 | DINOv2 特征 + depth head 干净迁移 |
| AR occlusion / 新视角合成骨干 | ✅ 有用 | 相对深度够；renderer 反正重新 scale |
| Robot grasp pose | ❌ 工具错 | 输出 affine-invariant — 无米 |
| Drone 障碍距离 | ❌ 工具错 | 同理；你不能决定"5 m 停" |
| AD 的 BEV 占据 | ⚠️ 仅预训练 | 生产 AD 栈与 LiDAR 或 stereo 融合做 scale |

**要避的陷阱：** Depth Anything v2 产出漂亮的深度图. 看着像 metric. 不是 metric. 若你取 v2 输出 `d` 并乘以来自单次校准场景的拟合 scale `s`，scale `s` 不会跨场景成立 — 因为 v2 的输出是 affine-invariant up to **shift** as well as scale，shift 随图像内容变 `UNVERIFIED v2 是否完全修了 shift；v1 肯定有`. 对机器人，这意味着"一次拟合全局 scale"不 work — 你需要 per-frame metric anchor（stereo、LiDAR、学习的 + camera intrinsics → 见 Metric3D）.

---

## 3.5 · Worked example — 桌上手机照

拍一张桌上咖啡杯的手机照，跑 Depth Anything v2-L：

- **Output**: `H×W` disparity, 值 ~0.1–0.9（无单位，affine-invariant）.
- **"一次拟合 scale"**: 用尺测杯子在 0.5 m，拟合 `s, b` 使 `s/output + b ≈ 0.5 m`.
- **同相机再拍一张复用 `s, b`**: 模型说 0.7 m，尺说 0.5 m → **40% scale 误差**.

v2 的 affine `(s, b)` 与内容相关，不与相机相关 — 拟合不迁移. 用 per-frame metric anchor 或切到 Metric3D.

---

## 4 · 它在哪里 break

- **透明 / 镜面表面** — 玻璃、水、镜子. 从每个 DPT-lineage 模型继承. 在 monocular-RGB 层面没有有原则的修复.
- **超过 ~30 m 的无界户外深度** — affine-invariant loss 压缩尾部；天空与远建筑塌缩到同一 disparity bin. 对 drone / AD 是主导失败模式.
- **孤立小物体** — 线、细栏杆、悬挂线缆. 背景深度渗透. 对 drone 避障关键，对桌面少.
- **当 unlabeled 语料库未见过域时的跨域伪影** — 内窥镜、海洋、水下. 62M unlabeled 语料库多数是互联网白昼图像 `UNVERIFIED breakdown`.
- **遮挡边界附近的细几何** — 比 v1 好但仍软. 需要清晰物体剪影时用 stereo 模型.

### 4.x · Hidden Assumptions

上游假设，违反就触发上面的失败：

- **可接受 affine-invariant 输出** — 任何 metric 任务违反此条；无恢复路径.
- **In-distribution 测试域** — 互联网白昼为主；内窥镜 / 水下静默退化.
- **接近 Lambertian 表面** — 玻璃 / 水 / 镜子破 DPT-lineage 预测.
- **标准 FOV (~50–90°)** — 鱼眼引入未训练畸变.
- **深度范围 ~0.3–30 m** — affine-invariant loss 压尾；>30 m 不可靠.
- **Pseudo-label 足够可靠** — teacher bias 传播；OOD 图像得到自信的错误深度.

违反时模型仍产出看着干净的深度图 — 静默失败是任何部署下游系统的危险模式.

---

## 5 · 部署模式

- **Jetson Orin 上 v2-S 作为特征提取器** 给 3D-aware policy 编码器 — 用特征，不用深度输出.
- **离线 v2-L** 做场景重建，per-scene 拟合 scale.
- **别在线部署 v2 做 metric 任务**（grasp pose、障碍距离、规划）.

Metric monocular 见 [`metric3d_dissection.md`](./metric3d_dissection.md)；多视角 feed-forward 见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md).

---

## 6 · 2-year outlook + falsifiable prediction

Relative-depth foundation 轨会继续在泛化 benchmark 上赢，因为 data 技巧能继续 scale（Depth Anything v3 大概会声称 200M+ unlabeled `UNVERIFIED`）. **但机器人钱流入的是 metric 轨**，因为没有 manipulation 或空中产品能在相对深度上发. 预计两条轨在 2027 通过 "metric-aware fine-tune" 配方收敛 — 在 62M 上训相对，然后在小型带标签集 + 喂入相机内参上 fine-tune metric.

**Falsifiable prediction:** 2027-06 前会有同实验室出公开的 "Depth Anything v3 metric" 或等效变体，带 Metric3D 风格 canonical-camera 输入. 若到 2027 只出 relative 变体则预测失败.

**Interview Tip**: 被问 "Depth Anything v2 vs Metric3D 用哪个"，陷阱答案是 "哪个更准". 正确答案：*"不同输出契约"* — v2 是 affine-invariant（无米、无 metric 任务），Metric3D 输出米（需校准内参）. 把契约匹配下游消费者；永不互换.

---

## For the reader

- **Manipulation engineer** — 作为特征预训练有用，作为深度源不行. 你的夹爪接 Metric3D 或 stereo.
- **Aerial engineer** — 跳过 live state estimation；可能对检测飞行的 4D 场景离线重建有用.
- **AD engineer** — 仅预训练. 你的生产栈已有 stereo + LiDAR.
- **Researcher** — data recipe 是教训，不是架构. 应用于任何标签嘈杂的模态.

---

## References

- Depth Anything v2 — Yang et al. *NeurIPS 2024*. https://arxiv.org/abs/2406.09414
- Depth Anything v1 — Yang et al. *CVPR 2024*. https://arxiv.org/abs/2401.10891
- MiDaS — Ranftl et al. *TPAMI 2020*. https://arxiv.org/abs/1907.01341
- DPT — Ranftl et al. *ICCV 2021*. https://arxiv.org/abs/2103.13413
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193

## Boundary

本文把 Depth Anything v2 作为 *relative* monocular depth foundation 模型解构. Metric monocular depth 在 [`metric3d_dissection.md`](./metric3d_dissection.md). 跨 embodiment scale 故事在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
