# FoundationStereo (FoundationStereo 立体匹配基础模型解构 — NVIDIA 2024)

> **Published**: 2024 (arXiv ID TBD UNVERIFIED)
> **Paper**: NVIDIA — *FoundationStereo* `arXiv link TBD UNVERIFIED`
> **Team**: NVIDIA
> **Core position**: 立体匹配基础模型 — RAFT-Stereo 谱系架构 + foundation-feature 骨干 + 大型合成语料库 → 跨 Middlebury / KITTI / ETH3D 零样本泛化，无 per-domain fine-tune. 若能在机器人上放两台相机，是最便宜的被动度量深度源.

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · metric-depth foundation (stereo)
**TL;DR:** FoundationStereo (NVIDIA 2024, `[arXiv link TBD]` UNVERIFIED) 是把对 Depth Anything 和 VGGT 都有效的"在巨量合成上训、到处零样本"配方应用到立体的答案. 它在跨域零样本泛化上击败 RAFT-Stereo (Lipson et al. 2021) 谱系 — Middlebury、KITTI、ETH3D、野外 — **无需 per-domain fine-tune**. 对机器人这是无 LiDAR 得到 *metric* 深度最便宜的方式：若能在机器人上放两台已知 baseline 的相机，FoundationStereo 开箱给你米. 重要的是 Jetson 可部署性.

### X-Ray (non-expert friendly)

(a) 立体单凭几何给 metric 深度（`Z = f·B/d`）；历史问题是*匹配*（无纹理、重复、遮挡）. RAFT-Stereo / SGBM 需 per-domain 调. (b) FoundationStereo 把 Depth Anything 配方带到立体：foundation-feature 骨干 + 大合成语料库 → 零样本泛化. (c) 对空间 AI 工程师：最便宜的被动 metric 深度 — global-shutter 立体 + FoundationStereo + VIO 是可信的 2026 drone 栈.

### 📍 Research Landscape Timeline

```
SGBM 2005 ─► PSMNet 2018 ─► RAFT 2020 ─► RAFT-Stereo 3DV 2021 ─► ★ FoundationStereo NVIDIA 2024 ─► distilled/edge variants 2026+ ─► fused with monocular metric 2027+
```

FoundationStereo 把 foundation-model 配方应用到立体匹配. 下游开放：边缘蒸馏 + 在同一 feed-forward 骨干下与 monocular Metric3D 融合.

---

## 1 · 为什么立体 foundation 模型对机器人重要

立体是唯一无需 monocular 技巧就 metric 的被动光学深度法. Baseline + 已知校准 → 三角化 → 米，结束. **历史问题不是几何，是匹配** — 跨无纹理墙、重复花纹（砖、瓷砖、围栏）和遮挡边界找对应. 经典 block-matching（OpenCV SGBM）处理良性场景；RAFT-Stereo 谱系推精度但仍需 per-dataset fine-tune 才能泛化.

FoundationStereo 把 foundation-model 配方 — **海量合成训练语料 + 尺度不变特征骨干 → 零样本泛化** — 带到立体匹配. 赌注与 Depth Anything 同：合成数据现已够好，强预训练骨干（视觉 transformer 或卷积）足够鲁棒，使 per-domain fine-tune 不再必要. 对机器人这是巨大的 — 放上立体 rig，得米，无 scene-specific 校准环.

> ⚡ **Eureka Moment**: 立体精度的瓶颈是*特征质量*，不是 cost-volume 架构. RAFT-Stereo 的 GRU-迭代精化已强 — 但需 per-domain fine-tune 因为特征编码器训在小立体数据集上. **换上 foundation-feature 骨干（DINOv2 / EDM-style 在互联网图像上预训练），per-domain 调消失.** 架构留在 RAFT-Stereo 谱系；变的是前端.

---

## 2 · 配方

> 📌 **Napkin Formula**: `Z = f · B / d`，`d = StereoMatcher(left, right; foundation_features)`. 一旦有正确 disparity，metric depth 是几何（校准 baseline + focal length）；贡献是让 disparity 零样本准确.


| Component | Choice |
|---|---|
| Architecture | RAFT-style 迭代精化 + foundation feature 骨干 `UNVERIFIED specifics` |
| Pretrained backbone | DINOv2 / EDM-style image features `UNVERIFIED which` |
| Training data | 大型合成立体语料库 (SceneFlow-scale + 域混合) `UNVERIFIED size` |
| Cost volume | 多尺度、稀疏相关 |
| Inference | 迭代 GRU 更新，~12–32 iterations |

```
left  ──► foundation encoder ──┐
                                ├──► cost volume ──► GRU-iter refinement ──► disparity
right ──► foundation encoder ──┘                                              │
                                                                              ▼
                                                                      Z = f · B / d  (metric)
```

贡献双管齐下：**(1) 编码器在互联网规模图像上预训练**让特征扛域偏移，**(2) 合成训练语料库够大够多样**让匹配网络学到泛化的 disparity 先验. 架构上这是 RAFT-Stereo 谱系配更聪明的前端.

---

## 3 · 为什么击败 RAFT-Stereo

| Axis | RAFT-Stereo (2021) | FoundationStereo (2024) |
|---|---|---|
| Zero-shot 泛化 | 无 fine-tune 弱 | 无 fine-tune 强 |
| 无纹理表面 | 吃力 | 处理 `UNVERIFIED magnitude` |
| 部署复杂度 | per-rig fine-tune | 已知 baseline 即可放入 |

胜利不是新架构 — 是把 foundation-model 配方应用到立体. 对离线 mapping 答案是 "换". 对 >50 Hz 闭环控制，换前验证 Jetson 延迟 — RAFT-Stereo 有多年边缘硬件优化.

---

## 3.5 · Worked example — drone 立体在 5 m

1 kg drone，10 cm baseline global-shutter 对，`f ≈ 600 px` UNVERIFIED，Orin Nano.

- **在 5 m**: `d = f·B/Z = 12 px`；亚像素 ~0.1 px → 精度 ~0.04 m UNVERIFIED.
- **在 30 m**: `d = 2 px` → 精度 ~1.5 m. 范围按几何塌缩.
- **延迟**: 12 iter 时 ~50 ms / pair UNVERIFIED → ~20 Hz，适合控制环.
- **失败**: 无纹理天花板 / 重复围栏降匹配器置信；回落到 IR 投射.

立体短距精确，二次退化；与 monocular metric 配长距.

---

## 4 · 它在哪里 break

- **无纹理表面** — 比 RAFT-Stereo 好，仍非完美. 主动立体（投射图案）在此无视匹配器质量取胜.
- **重复花纹**（砖、瓷砖、围栏）— 匹配器锁错周期. Foundation 模型帮忙，不消除.
- **镜面反射** — 左右见不同高光 → 无对应.
- **长距下短 baseline** — 几何 SNR 塌缩（5 cm baseline → 10 m 处 ~1% disparity 精度，30 m 处猜测）. 无匹配器能修.
- **快速运动下 rolling-shutter** → 假 disparity. drone / 竞速用 global-shutter.
- **边缘算力成本** — Jetson Nano 上 32 GRU 迭代非实时 `UNVERIFIED actual numbers`.

### 4.x · Hidden Assumptions

上游假设，违反就破 metric 输出：

- **准确校准**（baseline + 内参 + rectification）— 误差线性传播；主导噪声源.
- **同步 global-shutter** — 运动下 rolling shutter → 假 disparity.
- **足够纹理** — 无纹理 / 重复甚至降级 foundation features；IR 投射帮忙.
- **Baseline-to-range 比** — 几何；长距下短 baseline 无视匹配器塌缩.
- **Lambertian 表面** — 镜面高光左右不同 → 无对应.
- **In-distribution 域** — 水下 / 仅 IR 需 fine-tune.

违反时得到看着合理的 metric 深度但有静默几何误差 — 在长距尤其差，因为 disparity SNR 本来就弱.

---

## 5 · 部署模式

- **Drone 上 Global-shutter 立体 + FoundationStereo** — 户外障碍距离，metric，无 LiDAR. <1 kg 检测 drone 甜蜜点.
- **立体 + 主动 IR 投射 + FoundationStereo** — 室内 manipulation；投射填无纹理表面.
- **离线 mapping** — 全迭代次数，最佳精度，任务后批处理.
- **混合：60 Hz RAFT-Stereo 控制 + 5 Hz FoundationStereo 建图** — 与 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 中 VGGT + VIO 同模式.

Jetson 粗略数字（始终对实际 rig 做基准）：Orin Nano 在 640×480 减少迭代 ~10–20 Hz `UNVERIFIED`；Orin AGX 在 1280×720 ~30 Hz `UNVERIFIED`；Xavier NX 勉强，可能需蒸馏 `UNVERIFIED`.

---

## 6 · 2-year outlook + falsifiable prediction

立体 foundation 模型与 monocular depth foundation 模型乘同一波浪 — 合成 + foundation 骨干 → 零样本泛化. 接下来两年会有：

1. 蒸馏到 Orin Nano 上 <10 ms（与 VGGT-distilled 轨迹类似）
2. 与 monocular metric 模型融合 — "baseline 好处用 FoundationStereo，一相机遮挡时回落 Metric3D"
3. 集成进多视角 feed-forward 3D — VGGT 谱系已把立体作为多视角特例吸收

**Falsifiable prediction:** 2027-06 前，至少一个公开 drone autonomy 栈（Skydio 级或开源）将发 FoundationStereo 谱系模型作为主要立体匹配器. 若到 2027 都留在经典 SGBM 或 RAFT-Stereo 则预测失败.

**Interview Tip**: 被问 "立体 vs monocular metric 深度"，正确答案：*"不同失败模式 — 立体在无纹理 / 镜面 / 长距短 baseline 失败；monocular 在错内参 / 域偏移失败."* FoundationStereo 是零样本立体答案；在立体几何塌缩处（长距、遮挡相机）与 Metric3D 配. 别二选 — 融合.

---

## For the reader

- **Manipulation engineer** — 室内无纹理配主动 IR；否则 RealSense pipeline 够.
- **Aerial engineer** — 最便宜的 metric 深度源. Global-shutter 立体 + FoundationStereo + VIO 是可信的 2026 栈.
- **AD engineer** — 仅作为立体匹配器的候选替换，不是整个栈.
- **Researcher** — 合成语料库配方是教训，同 Depth Anything v2.

---

## References

- FoundationStereo — NVIDIA 2024. `[arXiv link TBD]` UNVERIFIED
- RAFT-Stereo — Lipson et al. *3DV 2021*. https://arxiv.org/abs/2109.07547
- RAFT (optical flow 起源) — Teed & Deng *ECCV 2020*. https://arxiv.org/abs/2003.12039
- SGBM — Hirschmüller *CVPR 2005*（经典 baseline）. no arXiv
- Depth Anything v2（配方对照）— 见 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- VGGT（多视角 feed-forward，吸收立体）— 见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)

## Boundary

本文把 FoundationStereo 作为立体匹配基础模型解构. Monocular metric depth 在 [`metric3d_dissection.md`](./metric3d_dissection.md). Monocular relative depth 在 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md). 跨 embodiment scale 对比在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). "立体作为经典 VIO 下的低速 metric 锚" 模式是 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 中混合的特例. 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
