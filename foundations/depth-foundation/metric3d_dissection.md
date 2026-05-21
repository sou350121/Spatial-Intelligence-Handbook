# Metric3D v1 + v2 (Metric3D 度量单目深度解构 — ICCV 2023 + 2024)

> **Published**: 2023-07 (v1, ICCV 2023) / 2024-04 (v2)
> **Paper**: Yin et al. (v1) — *Metric3D: Towards Zero-shot Metric 3D Prediction*; Hu et al. (v2) — *Metric3D v2: A Versatile Monocular Geometric Foundation Model*
> **Team**: HKUST + ANT Group + JD Explore
> **Core position**: 第一个跨任意相机输出**米**的 monocular depth 模型，通过 canonical-camera 变换 — 每个输入被几何 rectify 到固定虚拟焦距，让 depth head 学"一个相机"的度量深度.

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**Wedge tier:** W1 · metric-depth foundation
**TL;DR:** Metric3D (Yin et al. *ICCV 2023*, arXiv 2307.10984 `UNVERIFIED ICCV vs preprint date`) 是首个能在**任意相机间输出米**的 monocular depth 模型，无需 per-camera fine-tune. 技巧是 **canonical-camera 变换** — 每张输入图像在预测前被几何 rectify 到固定虚拟焦距，因此 depth head 只需学"一个相机的度量深度". v2 (2024) 扩到 surface normal 并加更强骨干. **若你的机器人需要从单 RGB 相机得到米，这是首选模型.** 它是杀死 Depth Anything v2 grasp pose 的 relative-vs-metric 陷阱的承重答案.

### X-Ray (non-expert friendly)

(a) Monocular depth 根本上歧义（每像素 `s = f·w/Z` 有两未知）— MiDaS/Depth Anything 通过预测相对深度回避，对 "5 m 停" 无用. (b) Metric3D 把相机内参变*显式*：把每张输入 resize 到 canonical focal length `f_canon`，在 canonical frame 预测，然后 `D_real = D_canon · (f_real / f_canon)`. (c) 对空间 AI 工程师：若机器人有校准 wrist cam，这给你从单 RGB 输入得到米而无需 LiDAR — 但传错内参，输出按比例静默错.

### 📍 Research Landscape Timeline

```
ZoeDepth 2023 ─► ★ Metric3D v1 ICCV 2023 ─► Metric3D v2 2024 ─► UniDepth (intrinsics-free) CVPR 2024 ─► VGGT-class multi-view 2025 ─► fused with stereo 2026+
```

Metric3D 是 metric monocular 谱系的 canonical-camera 锚. UniDepth 移除内参需求；VGGT 把单视角吸收进多视角 feed-forward.

---

## 1 · 为什么 metric monocular 是难题

焦距 `f` 的相机看距离 `Z` 处的物体，其像平面尺寸 `s = f · w / Z`，`w` 是真实宽度. 两个未知（`Z`、`w`），一个观察（`s`）. **单图像的 monocular 深度根本上歧义** — 同图像可由近小物体或远大物体产生. MiDaS / Depth Anything 通过预测相对深度（up to affine）回避. 对可视化可，对 "5 m 停" 不可.

要从单 RGB 得到 metric 深度，你实际需要的是**把 `s` 链接到 `w` 的先验** — 在训练分布上对物体尺度的学到先验. 若你在一个相机上训和测，这工作（内参隐式编码），换相机就崩（35 mm 手机感光和鱼眼 drone cam 看同场景给不同 `s`）. Metric3D 的贡献是把内参对网络**显式化**，让跨相机迁移有原则.

---

> ⚡ **Eureka Moment**: 把相机先验变成**显式网络输入**，不是隐藏数据假设. 把每张图像 resample 到单一 canonical focal length，depth head 在训和推时只见过一个内参分布 — 杀死 MiDaS 谱系模型的 scale 歧义就此消失. 与 NeRF 中 positional encoding 同精神：把几何表面化，不要藏起来.

## 2 · canonical-camera 变换

> 📌 **Napkin Formula**: `Resize(image; f_real → f_canon) → DepthHead → D_canon → D_real = D_canon · (f_real / f_canon)`. Metric depth 对焦距缩放等变；canonical resize 利用此等变把所有相机塌缩到一个训练分布.


| Step | What happens |
|---|---|
| Input | RGB 图像 + 相机内参 `K` (fx, fy, cx, cy) |
| Canonical resize | 图像 resample 使有效焦距等于固定 canonical `f_canon` `UNVERIFIED value, typically ~1000 px` |
| Network forward | DPT-style depth head 在 canonical-camera frame 预测度量深度 |
| Inverse transform | 输出按 `f_real / f_canon` 重 scale 回真实相机 frame 的度量深度 |

```
RGB + K_real
    │
    ▼
 canonical resize ── (f_canon, K_canon)
    │
    ▼
 ViT encoder ─► DPT decoder ─► metric depth D_canon
    │
    ▼
 D_real = D_canon · (f_real / f_canon)
```

洞见是 **metric depth 对焦距缩放等变** — 焦距加倍，depth 减半（按像素隐含单位）. 把所有相机在训和推时塌缩到单一 canonical focal length，网络见到单一内参分布. **Scale 歧义消失，因为相机先验不再藏在数据里 — 是网络输入.**

这与 NeRF 中 positional encoding 或图形里 normalized device coordinates 同精神 — 把几何显式，而非依赖网络记忆.

---

## 3 · v1 vs v2

v1 (ICCV 2023) 落地 canonical-camera 贡献，用 ConvNeXt / ViT 骨干 `UNVERIFIED which is primary` 和 ~8M 训练图像跨 11 数据集 `UNVERIFIED`. v2 (2024) 扩到 ViT-Large + Giant，加 **surface-normal head** 联合 loss（帮助遮挡边界处深度质量 `UNVERIFIED magnitude`），并用更多合成扩训练混合. 架构上是直接放大；canonical-camera 技巧不变.

---

## 3.5 · Worked example — wrist cam grasp pose

Manipulator wrist cam，校准 `fx = fy = 750 px`，看 0.5 m 外的 mug.

- **Canonical** (`f_canon = 1000 px` UNVERIFIED): resize 1.33×，预测 `D_canon = 0.667 m`.
- **Inverse**: `D_real = 0.667 × 750/1000 = 0.500 m`. ✅

传错内参（实际 28 mm 时传 `fx = 1050` 当作 50 mm，使用 `750`）：
- Resize 0.952×，不同图像内容 → 不同 `D_canon`.
- 有效深度错约 1.4× — 夹爪冲过 mug. **静默失败.**

校准两次.

---

## 4 · 它在哪里重要

发它做：校准 wrist cam 的 manipulation grasp pose、桌面 bin picking、drone 慢飞障碍距离（超 30 m 预计退化）. 对 AR occlusion 杀鸡用牛刀（Depth Anything v2 更便宜）. 对水下（纹理破）和内窥镜（域偏移，需 fine-tune）失败.

**硬需求是校准内参.** 没 `K` 无 canonicalization. 适合固定相机机器人. 对"互联网图像深度"你需要 GT `K` 或学到的内参估计器 — UniDepth (Piccinelli et al. 2024 `UNVERIFIED`) 是 intrinsics-free 变体.

---

## 5 · 它在哪里 break

- **错内参 → 错 scale**. 28 mm 拍时传 50 mm 的 `K`，输出深度错约 1.8×. 静默失败模式 — 输出看着合理.
- **强透镜畸变**（鱼眼、ultrawide）— canonical resize 假设 pinhole. 先去畸变，或用 fisheye-aware 变体.
- **超过 ~30 m 的无界户外深度** — 与 Depth Anything 相同的根本问题；metric 与否，学到的 monocular depth 尾不可靠.
- **反射 / 透明表面** — 同 DPT-lineage 失败模式.
- **域偏移到医学 / 水下 / 合成** — 需 fine-tune.

### 5.x · Hidden Assumptions

上游假设，违反就产生静默 metric 错误：

- **准确内参** — canonical resize 依赖 `K`；错 `K` → 静默 scale 错.
- **Pinhole model** — 鱼眼破 canonical resize；先去畸变.
- **In-distribution 域** — 白昼为主；水下 / 医学需 fine-tune.
- **接近 Lambertian 表面** — 镜面 / 透明 → DPT-lineage 失败.
- **Depth ≤ ~30 m** — metric 尾超 30 m 不可靠，与 Depth Anything 相同 monocular 问题.
- **静态场景** — 运动下的 rolling shutter 引入几何不一致.

违反时输出仍是看着合理的 metric 深度图 — 校准错误是部署中主导静默失败模式.

---

## 6 · MoGe 对比（relative-track 竞争者）

[MoGe](./moge_dissection.md) (Microsoft 2024) 是 relative-track 最接近的竞争者 — affine-invariant 几何 loss + multi-task head（point + depth + normal）. 对比鲜明：

| Axis | Metric3D | MoGe |
|---|---|---|
| Output scale | metric (米) | affine-invariant |
| Needs intrinsics? | yes | no |
| Best for | 有校准 cam 的机器人 | photometric / 场景理解 |
| Multi-task head | depth + normal (v2) | point + depth + normal |
| Failure if you violate the contract | 错米 | 部署时 scale 不对齐 |

**需米：Metric3D. 不需要：MoGe 是 geometry-rich 的 relative-track 答案.**

---

## 7 · 2-year outlook + falsifiable prediction

Metric-monocular 轨是部署到机器人上的那个. 预计 intrinsics-free 变体（UniDepth 谱系）在野外图像上赢，canonical-camera 技巧成标准成分，与 stereo + IMU 融合收敛到 VGGT 谱系 feed-forward 骨干.

**Falsifiable prediction:** 2027-06 前一个主要 manipulation 产品（Figure、1X、Apptronik 或类似）将公开披露其感知栈中的 Metric3D-lineage 模型. 若都留在 RGB-D（RealSense / structured light）则预测失败.

**Interview Tip**: 被问 "怎么从单 RGB 相机得到 metric 深度"，陷阱答案是 "做不到". 正确答案：*"Metric3D 的 canonical-camera 变换 — 把内参作为网络输入显式化，利用 focal-length equivariance."* 加一句你需要校准 `K`，错 `K` 静默错.

---

## For the reader

- **Manipulation engineer** — 从这里起步，不是 Depth Anything. 校准 wrist cam 然后发.
- **Aerial engineer** — 适合慢飞检测；竞速或户外换 stereo + VIO（见 [`crossing/scale-comparison/`](../../crossing/scale-comparison/)）.
- **AD engineer** — 适合作为 metric 预训练；生产仍要 LiDAR + stereo.
- **Researcher** — canonical-camera 技巧比深度更通用. 任何 geometry-aware 都能借.

---

## References

- Metric3D v1 — Yin et al. *ICCV 2023*. https://arxiv.org/abs/2307.10984 `UNVERIFIED venue`
- Metric3D v2 — Hu et al. 2024. https://arxiv.org/abs/2404.15506 `UNVERIFIED arXiv ID`
- UniDepth — Piccinelli et al. *CVPR 2024*. https://arxiv.org/abs/2403.18913 `UNVERIFIED`
- ZoeDepth — Bhat et al. 2023. https://arxiv.org/abs/2302.12288
- MoGe — 见 [`moge_dissection.md`](./moge_dissection.md)

## Boundary

本文解构 Metric3D 的 canonical-camera 贡献. Relative-depth 对比在 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md) 和 [`moge_dissection.md`](./moge_dissection.md). 跨 embodiment scale 争论在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 VLA action head 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md) — 注意 `scale_flag` 契约.
