# MoGe — Monocular Geometry Estimation (MoGe 单目几何估计解构 — Microsoft 2024)

> **Published**: 2024 (arXiv ID TBD UNVERIFIED)
> **Paper**: Microsoft Research — *MoGe: Monocular Geometry Estimation* `arXiv link TBD UNVERIFIED`
> **Team**: Microsoft Research
> **Core position**: Relative-track 多任务 monocular 几何模型 — 在统一 affine-invariant 3D loss 下预测 point map + depth + normal. 作为 3D-aware 视觉编码器比 Depth Anything 更丰富；仍无米.

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · relative-depth foundation (geometry-rich)
**TL;DR:** MoGe (Microsoft Research 2024, `[arXiv link TBD]` UNVERIFIED) 是 relative-track 的答案，说"既然要 affine-invariant，就预测*整个几何* — point map、depth、normal — 用同一 affine-invariant loss". 这是 Depth Anything 线的有用分叉，因为 multi-task head 让模型作为 3D-scene-understanding 骨干更有用，即使输出仍 up to scale. **对 VLA 预训练和场景重建有意思. 对带米的机器人，工具错 — 去 Metric3D.**

### X-Ray (non-expert friendly)

(a) Depth Anything 每像素预测一个标量（disparity, up to affine）；Metric3D 预测米但需内参. (b) MoGe 说"既然反正 affine-invariant，就在同一 affine-invariant loss 下预测*完整几何* — 3D 点、深度、法线"，模型由此变 3D-aware 编码器，不只深度网. (c) 对空间 AI 工程师：作为 VLA 预训练或场景重建骨干有用；仍非 metric，所以别用于 grasp pose.

### 📍 Research Landscape Timeline

```
MiDaS 2020 ─► Depth Anything v1/v2 2024 ─► ★ MoGe (Microsoft) 2024 ─► VGGT CVPR 2025 (subsumes single-view) ─► MoGe v2 metric?  2026+
```

MoGe 是 VGGT 多视角几何头的单视角前驱. 2 年内，要么 MoGe v2 加 metric 输出（canonical-camera 技巧），要么被静默退役、由 VGGT 类模型接手.

---

## 1 · 卖点

Depth Anything 线每像素预测一个标量（disparity, up to affine）. Metric3D 线预测 metric depth 但需内参. **MoGe 居中**：直接从 monocular RGB 预测*几何*（3D point map + depth + normal），用统一 loss，对场景全局 affine 不变但对*内部*几何紧.

赌注是这让模型比 depth-only head 学到更丰富的 3D 结构 — 表面连续性、法线一致性、遮挡边界锐度 — 不承诺米. **若你需要 3D-aware 视觉编码器且部署时愿意乘以外部估计的 scale，MoGe 给你的比 Depth Anything 多，推理成本相近.**

> ⚡ **Eureka Moment**: 把 affine-invariant *disparity* loss (MiDaS) 推广到 affine-invariant *3D point* loss. 输出现是 up to global scale + offset 的完整 point cloud，但跨 point / depth / normal head 内部一致. **三头互为正则化** — surface normal 收紧 depth 梯度，point map 收紧表面连续 — 不付 metric 监督的代价.

---

## 2 · 架构

> 📌 **Napkin Formula**: `RGB → ViT → {pointmap, depth, normal}`，loss `L = AffineInv(pointmap) + AffineInv(depth) + cos(normal, ∇pointmap)`. 每图像解一个场景级 affine `(s, t)`；跨头强制内部几何约束.


| Component | Choice |
|---|---|
| Encoder | DINOv2 ViT (S/B/L) `UNVERIFIED breakdown` |
| Heads | Point map + depth + (可选) normal |
| Loss | Per-scene affine-invariant + 跨头几何一致 |
| Output | 每图 up-to-affine 3D point cloud |

```
RGB ──► ViT encoder ──► shared 3D feature
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
        point map       depth        normal
        (X, Y, Z)       (Z)         (nx, ny, nz)
            │             │             │
            └─────── joint affine-invariant loss ───────┘
```

"affine-invariant point" loss 是值得思考的贡献 — 是 MiDaS affine-invariant disparity loss 到完整 3D 的推广. 意味着 MoGe 预测的 3D 场景 up to global scale + offset，但三个输出头之间几何内部一致.

---

## 3 · 它在版图中位置

| Axis | Depth Anything v2 | MoGe | Metric3D | FoundationStereo |
|---|---|---|---|---|
| Output | relative depth | point + depth + normal (relative) | metric depth | metric depth (stereo) |
| Needs intrinsics? | no | no | yes | calibrated rig |
| Multi-task | no | yes | depth + normal (v2) | no |
| Cost (single-view, ViT-L) | low | medium | medium | n/a (stereo) |
| Best for | viz / pretrain | 3D-aware encoder | robot metric | robot metric (stereo) |

**干净选择方法：** 需米 → Metric3D 或 stereo. 需相对深度源 → Depth Anything v2（更简单、更广部署）. 需下游学习用的 3D-aware 视觉编码器 → MoGe 配得上.

---

## 3.5 · Worked example — VLA 预训练特征信号

对比 Depth Anything v2 预训练 vs MoGe 预训练在 manipulation policy 编码器上：

- **Depth Anything v2 预训练**: 编码器每像素一个标量监督信号（disparity）. 下游 policy linear probe 在 grasp success 上: 78% UNVERIFIED.
- **MoGe 预训练**: 编码器每像素三个信号（point、depth、normal）在统一 loss 下. 同编码器骨干（DINOv2 ViT-L），同下游 probe: 82% UNVERIFIED.
- **成本差**: MoGe 推理 ~1.3× Depth Anything v2（三头）.
- **Caveat**: 数字示意；实际胜负取决于 policy 从预训练需要什么（normal 对抓圆柱重要；对捡积木不那么）.

教训：当下游任务本身不是 metric 时，预训练信号丰富度比 metric 正确性更重要.

---

## 4 · 它在哪里 break

- **同 monocular-RGB 失败模式** — 透明 / 镜面 / 无界户外.
- **Multi-task head 修不了 scale** — 预测法线找不回米. 模型根本上 affine-invariant；若忘了这点，就掉进 Depth Anything v2 同样的错米陷阱.
- **部署开销** — 三头比 depth-only 占更多内存；在紧边缘设备上相对 Depth Anything 不明显值.
- **文档成熟度** — 截至写时 MoGe 论文较新，下游 eval 覆盖比 Depth Anything v2 稀 `UNVERIFIED, check post-2025 surveys`.

### 4.x · Hidden Assumptions

上游假设，违反就产生静默失败：

- **下游可接受 affine-invariant 输出** — 同 Depth Anything v2 陷阱；若消费者需米，MoGe 工具错.
- **Multi-task head 保持一致** — 统一 loss *应该*让 point / depth / normal 一致，但偶尔不一致（法线与 point-cloud 梯度不符）会漏到下游.
- **In-distribution 域** — 与 Depth Anything 同样的互联网图像训练偏差.
- **标准 FOV + pinhole** — 鱼眼 / 广角退化，无 canonicalization 机制.
- **足够推理算力** — 三头 × ViT-L 比 Depth Anything v2 重；紧边缘设备可能不值.

违反时通常得到一个看着合理的 3D point cloud，在一个场景里正确 scale，在下一个里漂移 — 与咬 Depth Anything 用户的同一内容相关 affine.

---

## 5 · 何处用

- **VLA 预训练** — 把 point/depth/normal 输出作为 policy 编码器的辅助监督. multi-task 信号比单深度头丰富.
- **离线场景重建** — 当你能对已知参考拟合 per-scene scale.
- **对比 ablation** — 若你写论文论证 "geometry-rich 预训练 > depth-only 预训练"，MoGe 是强 baseline.

---

## 6 · 2-year outlook + falsifiable prediction

Relative 轨与 metric 轨在收敛 — VGGT（见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)）已把 depth + pose + pointmap 吸收进单一多视角 feed-forward 模型. MoGe 的 multi-head 模式是单视角前驱；2 年内要么被 VGGT 谱系吸收，要么由 metric-aware MoGe-v2 取代.

**Falsifiable prediction:** 2027-06 前要么 (a) MoGe v2 出 metric 输出（canonical-camera 技巧），要么 (b) 它在同用例上静默被 VGGT 类模型取代. 若 MoGe 仍作为活跃的 "monocular geometry-rich relative" 线未动，则预测失败.

**Interview Tip**: 被问 "MoGe vs Depth Anything"，正确答案：*"MoGe 用简单度换更丰富的 3D 预训练信号 — point + depth + normal 在同一 loss 下"* — 对 VLA 编码器更好，部署上相同的 affine-invariant 限制. Metric 陷阱仍在；需米切到 Metric3D.

---

## For the reader

- **Manipulation engineer** — 跳过，除非作为预训练.
- **Aerial engineer** — 跳过；需米.
- **VLA researcher** — 值得作为预训练目标看；比 depth-only 丰富.
- **Researcher** — affine-invariant 3D point loss 是可推广的想法.

---

## References

- MoGe — Microsoft Research 2024. `[arXiv link TBD]` UNVERIFIED
- Depth Anything v2 — 见 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- Metric3D — 见 [`metric3d_dissection.md`](./metric3d_dissection.md)
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193
- MiDaS (affine-invariant loss 起源) — Ranftl et al. 2020. https://arxiv.org/abs/1907.01341

## Boundary

本文把 MoGe 作为 relative-track 多任务 monocular 几何模型解构. Metric monocular 见 [`metric3d_dissection.md`](./metric3d_dissection.md). 多视角 feed-forward 3D 见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md). 跨 embodiment scale 争论在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
