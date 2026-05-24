<!-- ontology-5axis
problem: Relative depth estimation
representation: Per-pixel depth map (relative)
sensor: Single RGB
paradigm: Learned-Foundation (monocular)
time: FeedForward-OneShot
ref: ../../cheat-sheet/ontology.md §7
-->

# Depth Anything v2 (Depth Anything v2 解构 — NeurIPS 2024)

> **Published**: 2024-06 (arXiv) / NeurIPS 2024
> **Paper**: Yang et al. — *Depth Anything V2*
> **Team**: HKU + TikTok
> **Core position**: 2024–2026 最强的 relative monocular depth foundation 模型. 靠 data recipe（62M unlabeled 蒸馏叠在 595K 高质量合成上）取胜，不是架构. **输出是 affine-invariant** — 永远别用于 grasp pose.

**Status:** v1.2 — 2026-05-21 加 §4.1/4.2/4.3/4.4（range / sensitivity / interpretability / DA3 后续）. Hyperparams 标 UNVERIFIED. **Wedge tier:** W1.
**TL;DR:** DA v2 (Yang et al. 2024, [2406.09414](https://arxiv.org/abs/2406.09414)) 是 2024–2026 出货最强 *relative* monocular depth 模型 — 也是最常被误当 metric 的现成模型. 胜利不在架构而在 **62M unlabeled 蒸馏叠 595K 高质量合成** `UNVERIFIED counts`. 用于可视化、semantic depth、预训练. **不要**用于 grasp pose — affine-invariant 输出乘机器人侧 scale 估计会摔杯子.

### X-Ray (non-expert friendly)

(a) 早期 monocular depth 模型（MiDaS、DPT、Depth Anything v1）泛化尚可但脆 — 真实标签有噪声（LiDAR 阴影、kinect 散斑），封死可达精度. (b) v2 的贡献是*数据*：在 595K *合成*干净标签上训 teacher，蒸馏到 62M unlabeled 真实图像上，发学生. 架构（DINOv2 + DPT）没变. (c) 对空间 AI 工程师：这是可得的最佳 relative-depth 预训练，但 affine-invariant 输出让它对任何需要米的任务*无用* — 那是独立轨（Metric3D）.

### 📍 Research Landscape Timeline

```
MiDaS 2020 ─► DPT 2021 ─► Depth Anything v1 2024 ─► ★ Depth Anything v2 NeurIPS 2024 ─► Metric3D / canonical-camera track 2024+ ─► VGGT subsumes 2025
```

v2 是 relative-depth foundation 谱系的顶峰. 下一步要么是 (a) metric-aware fine-tune（与 Metric3D 趋同）要么是 (b) 被多视角 feed-forward (VGGT) 吸收.

---

## 1 · 为什么这篇值得解构

MiDaS (2020) 定义 relative-depth 泛化模板，v1 用更大 DINOv2 骨干推它. **v2 的贡献几乎完全是数据故事**：真实标签数据集充满噪声（LiDAR 阴影、photometric stereo 伪影、kinect IR 散斑），**合成标签 + 大规模 unlabeled 蒸馏 > 更多真实标签**.

教训泛化到深度之外 — 同配方对 SAM-2、DINOv2、VGGT 都 work. 对机器人读者：这配方**不是 metric-shaped** — unlabeled 蒸馏不提供 scale 信号，泛化的同一技巧也锁死 relative-only 约束.

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

跑 DA v2-L 到桌上咖啡杯手机照：output 是 `H×W` disparity, 值 ~0.1–0.9（无单位，affine-invariant）. 用尺测杯子 0.5 m 拟合 `(s, b)`，**同相机再拍一张复用**：模型 0.7 m vs 尺 0.5 m → **40% 误差**. v2 的 `(s, b)` 与内容相关，不与相机相关 — 拟合不迁移. 用 per-frame metric anchor 或切到 Metric3D.

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

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

DepthAnything/Depth-Anything-V2 上 236 open issues 里 ~40% 都是同一类"输出契约没读懂"问题，与 §3 / §4 完全对得上：

- **GitHub-validated**：**relative-vs-metric 混淆是头号坑** —— 用户把 disparity 当 meter 读，对应 [issue #93](https://github.com/DepthAnything/Depth-Anything-V2/issues/93) / [#178](https://github.com/DepthAnything/Depth-Anything-V2/issues/178)；维护者最高 ROI 的修复不是改模型而是写 README Output Contract 表（§4.3）；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#1--depth-anything-v2--relative-only-的输出契约困局)。
- **GitHub-validated**：metric variant `max_depth` 写死（Hypersim 20 m / VKITTI 80 m）超过即截断 —— 对应 [#26](https://github.com/DepthAnything/Depth-Anything-V2/issues/26) / [#4](https://github.com/DepthAnything/Depth-Anything-V2/issues/4) / [#69](https://github.com/DepthAnything/Depth-Anything-V2/issues/69) / [#289](https://github.com/DepthAnything/Depth-Anything-V2/issues/289)，印证 §4.1 "天花板 80 m" 行；relative→metric 蒸馏（[#98](https://github.com/DepthAnything/Depth-Anything-V2/issues/98) / [#102](https://github.com/DepthAnything/Depth-Anything-V2/issues/102)）的 shift `b` 与内容相关，single-anchor 不可跨场景迁移。
- **GitHub-validated**：ONNX 后 metric head sigmoid + max_depth 丢精度 —— 对应 [issue #49](https://github.com/DepthAnything/Depth-Anything-V2/issues/49)；部署到 ONNX/TRT 必须单元测试 metric 输出；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#1--depth-anything-v2--relative-only-的输出契约困局)。

---

## 4.1 · Working Range（按距离桶）

DA v2 输出 affine-invariant disparity，**无"米"概念**；但相对精度按距离桶差异巨大.

| 距离桶 | 表现 | 应用 | 失效 |
|---|---|---|---|
| **0–1 m（manipulation）** | 边界软；薄物（栏杆 / 杯沿）渗透背景 | 桌面 grasp 视觉辅助、AR occlusion | 透明 / 镜面把深度拉远；细线背景渗透 |
| **1–30 m（主战场）** | 训练分布主区间；NYUv2 AbsRel ≈ 0.074 / δ₁ ≈ 0.946（v2-L）；DA-2K SOTA | 室内重建、SfM 预填、video depth | 与 metric 对齐需 per-frame anchor（§3.5） |
| **30–100 m（unbounded outdoor）** | affine-invariant loss 压尾；远端 disparity 量化误差大 | AD / drone 远场仅可视化 | 同一 disparity bin 内米差可达 10× |
| **>100 m（sky / horizon）** | 塌缩到 disparity ≈ 0；**metric 变体 VKITTI 上限 80 m，超过截断**；indoor Hypersim 变体上限 20 m | 仅做 sky mask | "天花板" 80 m（VKITTI 训练上限） |

**关键观察**：relative 模式无硬"天花板"，但 affine-invariant loss 尾部压缩让 >30 m 信息密度急剧下降. Metric variant `Depth-Anything-V2-Metric-VKITTI` 把上限 hard-code 在 80 m（issue #289 中 absrel 30 → 0.6 仅靠 ×(1/80) rescale 即佐证）.

来源：[HF Metric-VKITTI-Large](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-VKITTI-Large)、[issue #289](https://github.com/DepthAnything/Depth-Anything-V2/issues/289).

---

## 4.2 · Sensitivity（输入扰动 → 输出稳定性）

DINOv2 骨干 + 62M 互联网蒸馏让 DA v2 对*常见域*惊人稳定，脱分布即静默退化.

| 扰动 | 稳定性 | 失败例子 |
|---|---|---|
| **光照 / HDR / 曝光** | 中–高 | 强逆光高光区噪声；过曝白块塌缩 |
| **运动模糊** | 中（per-frame，无时序） | 高速帧 disparity 闪烁；视频用 Video Depth Anything 变体 |
| **玻璃 / 水 / 镜面** | v2 比 v1 显著好（DA-2K transparent_reflective 桶 >10% vs Marigold） — 但**未根治**：玻璃后被"看穿"到背景 | 玻璃桌面 grasp 抓"穿"；镜子里场景被当真深度 |
| **遮挡 / partial visibility** | 中（边界比 v1 锐） | 半遮挡物向可见部分插值 |
| **OOD 域（水下 / 内窥镜 / 显微）** | ❌ 静默崩 | 62M 语料未覆盖；输出"干净"但物理无意义 |
| **输入分辨率** | 默认 518（短边）；测试时可上采得更细，>1024 收益递减 `UNVERIFIED 曲线` | &lt;256 丢细物；>1024 显存爆无增益 |
| **训练分布外类别** | ❌ 假信号 | 医学 / 科学图给非零 disparity，需 OOD 守门 |

**对策**：(a) OOD 用 DINOv2 feature distance 守门；(b) 玻璃 / 镜面接 stereo / ToF 二次确认；(c) 视频用 temporal 变体. 来源：[Roboflow DA-2K](https://blog.roboflow.com/depth-estimation-models/)、[DA-2K README](https://github.com/DepthAnything/Depth-Anything-V2/blob/main/DA-2K.md).

---

## 4.3 · Interpretability（输出可解释度）

> **TL;DR**：DA v2 输出是 **affine-invariant inverse depth（disparity-like）**，[0, 1] **全图全局归一化**；**无 confidence / variance**；**不能直接 3D 重建**.

**精确定义**：
- `D ∈ [0, 1]^{H×W}`，**值越大越近**（sky → 0，foreground → 1）.
- 物理：`D ∝ 1 / (a · z + b)`，`(a, b)` **每图独立未知 affine**（MiDaS scale-shift-invariant loss 谱系，DA v2 沿用）.
- **不是** log(distance)、**不是**直接 inverse-depth metric、**不是** normalized metric depth.

**两像素 A=1.0 / B=0.5**：只能说"A 比 B 近"（单调可信），**不能说近 2×**（affine 不消去）；估出 `(a,b)` 也仅对同帧有效，换帧立即失效（§3.5：40% 误差）.

**不确定性**：DA v2 **不**输出 confidence / variance — 确定性 head. 工程 hack：DINOv2 feature 距离做 OOD score、left-right flip 一致性做 self-consistency proxy `UNVERIFIED 有效性`.

**Normalization 范围**：**全局**（whole-image，非 patch / per-pixel）— sky 占主导时把 `b` 推大，前景动态范围被吃掉.

**3D 重建？** ❌ 不能直接反投影. 输出契约对比：

| 模型 | 输出 | 直接 3D？ |
|---|---|---|
| **DA v2** | affine-invariant inverse depth | ❌ 需 per-frame anchor |
| **Metric3D v2** | metric depth (米) + canonical 内参 | ✅ |
| **MoGe** | affine-invariant 3D points + 相机 | ⚠️ 形状 OK，scale 未知 |
| **VGGT (multi-view)** | 多视角 feed-forward metric | ✅ 跨视角自洽 |

来源：[DA v2 arXiv 2406.09414](https://arxiv.org/abs/2406.09414)（SSI + gradient matching loss）；[HF DA v2 fine-tuning blog](https://huggingface.co/blog/Isayoften/monocular-depth-estimation-guide).

**面试 Tip**：被问"DA v2 输出 0.7 是几米" — 正确答："**[0,1] 上的 affine-invariant disparity，单调表示近远但米数未定义；要米必须 per-frame anchor 或换 Metric3D**".

---

## 4.4 · 后续工作：Depth Anything 3（2025-11，重要 surprise）

**Depth Anything 3 (DA3)** 已发布（ByteDance Seed，2025-11-14；[arXiv 2511.10647](https://arxiv.org/abs/2511.10647)，ICLR 2026 oral）— 比 §6 falsifiable prediction（"2027-06 前 metric 变体"）早 ~1.5 年、方向不同：

- **不是 v2 metric 后续，而是 any-view generalist**：单图 / 立体 / 多视角 / 视频统一；
- 架构反而更简：单一 plain DINOv2 transformer + 单一 depth-ray 预测（去掉多任务）；
- vs VGGT：相机位姿 +44.3%、几何 +25.1%（团队自报，独立复现 `UNVERIFIED`）；
- 2025-12-11 追加 **DA3-Streaming**：&lt;12 GB GPU 处理长视频；
- **吸收 VGGT 谱系** — 印证 §16 时间线判断方向，但比预测的"metric fine-tune"路径更激进.

**对 §6 prediction 的影响**：DA v2 metric 变体（VKITTI / Hypersim）已在 2024 仓内；DA3 走"多视角统一"而非"单目 metric". 判定：预测*精神*命中（轨迹收敛），*形式*偏离 — 留 2027 重评. 来源：[DA3 项目页](https://depth-anything-3.github.io/)、[GitHub](https://github.com/ByteDance-Seed/Depth-Anything-3).

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
- Depth Anything v3 — ByteDance Seed *ICLR 2026 oral*. https://arxiv.org/abs/2511.10647
- Depth Anything v1 — Yang et al. *CVPR 2024*. https://arxiv.org/abs/2401.10891
- MiDaS — Ranftl et al. *TPAMI 2020*. https://arxiv.org/abs/1907.01341
- DPT — Ranftl et al. *ICCV 2021*. https://arxiv.org/abs/2103.13413
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193

## Boundary

本文把 Depth Anything v2 作为 *relative* monocular depth foundation 模型解构. Metric monocular depth 在 [`metric3d_dissection.md`](./metric3d_dissection.md). 跨 embodiment scale 故事在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
