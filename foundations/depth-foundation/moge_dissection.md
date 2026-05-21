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

---

## X.1 · Working Range 详细分析 (2026-05-21 补)

MoGe 作为 monocular feed-forward 模型，**没有内置 range gating**（输入 RGB 不带尺度），但内部各 head 在不同距离段表现差异显著. 下面分四段对照（数字若来自论文则有引用，否则标 `UNVERIFIED`）.

### X.1.1 affine-invariant 精度按距离分层

MoGe 输出 **up-to-global-(scale, Z-shift)** 的 3D point map（论文将 affine 简化为 Z-axis shift，前提是 principal point 居中，见 [arXiv:2410.19115](https://arxiv.org/abs/2410.19115)，§Method）. 这意味着 *绝对距离* 数字本身没意义，下表读"affine-invariant 后的相对误差"：

| Range | 典型场景 | 主要误差来源 | Affine-invariant 精度（直觉） |
|---|---|---|---|
| 近 (<1 m) | 桌面操作 / 抓取 | 相机近平面、镜头径向畸变、对焦模糊 | 三 head 都较稳；normal 边缘清晰. `UNVERIFIED, no per-range breakdown in paper` |
| 中 (1–5 m) | 室内房间、走廊 | 训练分布主力（ScanNet / Hypersim 等） | MoGe sweet spot，论文 6.43 average rel error 主要由此段贡献. ref §Experiments |
| 远 (5–30 m) | 户外街景、广场 | 远距离 disparity 极小、纹理压缩 | depth head 较稳，point map Z 维度方差扩大；normal 在远端噪声放大 |
| 超远 (>30 m / sky) | 户外天空、远山 | "infinity region" 无 finite point | MoGe **专门有 mask head**（[v1 §3.3](https://arxiv.org/abs/2410.19115)）预测 sky / infinity binary mask + SegFormer label，避免给天空赋大值污染前景几何 |

> ⚡ **设计亮点**: mask head 是 MoGe 对"超远 / 无界"的明确工程答复 — 不是预测无穷远的深度，而是把这些像素**显式排除出 finite point map 的损失**. 这是 Depth Anything 系列没有的 wedge.

### X.1.2 multi-head 在不同 range 的行为差异

MoGe-1 主要输出 **point map + depth + (FOV)**；MoGe-2 增加 **metric scale + normal head**（`-normal` 变体，见 [github.com/microsoft/MoGe](https://github.com/microsoft/MoGe/blob/main/README.md)）.

| Head | 近 | 中 | 远 | 超远 |
|---|---|---|---|---|
| Point map (X, Y, Z) | 锐 | 锐 + 一致 | Z 方差大 | mask 排除 |
| Depth (Z only) | 锐 | 锐 | 平滑过渡 | mask 排除 |
| Normal (MoGe-2-normal) | 边缘最锐 | 表面连续 | **噪声放大**（梯度对远处微小 disparity 极敏感）| 不适用 |
| FOV / intrinsics | 全局量，不分 range | 同 | 同 | 同 |

**关键洞察**: normal 通过 point map 梯度间接监督（[v1 §3.3](https://arxiv.org/abs/2410.19115/) — angular diff on cross product of image-grid neighbors），所以 normal 在远端"借放大了 point map 的 Z-噪声". 实践上：近距离信赖 normal，远距离信赖 depth.

### X.1.3 Multi-scale local loss 与 range 关系

论文用 **三个 sphere 尺度** `α ∈ {1/4, 1/16, 1/64}` 的 local-region ROE alignment（[v1 §3.2](https://arxiv.org/abs/2410.19115)）. 这本质上是 *range-aware 监督*：

- **α=1/4** 大球 → 覆盖整景，惩罚跨远近物体的 relative-distance 漂移
- **α=1/16** 中球 → 房间 / 物体级
- **α=1/64** 小球 → 物体表面 / 抓取尺度细节

> 这三尺度回避了"全局 affine 把近端硬挤压"和"局部尺度孤立漂浮"两个极端. **Ablation**: 去除 multi-scale local loss 把 ViT-Base 上的 point error 从 8.00 推到 8.10（[v1 Tab. 5](https://arxiv.org/abs/2410.19115)）— 收益不大但稳定.

---

## X.2 · Sensitivity 详细分析 (2026-05-21 补)

### X.2.1 经典 monocular RGB 敏感性

| 因素 | 影响 | 缓解 |
|---|---|---|
| 光照（HDR / 低光） | DINOv2 在低光鲁棒，但 specular highlight 会产生 normal 翻转 | 训练分布覆盖；MoGe-1 训练用 21 datasets ~99 M frames（[v1 §4.1](https://arxiv.org/abs/2410.19115)） |
| 运动模糊 | feed-forward per-frame；模糊帧 point map 边界 hazy | 无时序滤波；下游需自补 |
| 纹理缺失（白墙 / 雾） | DINOv2 patch feature 退化，point map 表面塌陷 | mask head **不解决这个** — 它只管 sky |
| OOD（鱼眼 / 全景 / 显微 / 卫星图） | 无 canonicalization；FOV 估计崩 | MoGe-2 通过 DINOv2 interpolatable positional embedding 支持任意分辨率，但 *镜头模型* 仍 pinhole 假设（[MoGe-2 §Method](https://arxiv.org/abs/2507.02546)） |
| 分辨率依赖 | `resolution_level` 0–9，默认 9（[github README](https://github.com/microsoft/MoGe/blob/main/README.md)） | 高分辨率 → token 数 1200–2500，延迟和细节同涨 |

### X.2.2 Multi-head 之间的 sensitivity 不一致性 ★★

这是 MoGe 比 Depth Anything 更复杂的地方：**三 head 不一定一致敏感**.

| 扰动 | depth head 反应 | normal head 反应 | point map 反应 |
|---|---|---|---|
| 局部光照变化（阴影边） | 弱（DINOv2 patch 不受 photometric 强干扰） | **强**（normal 通过 point gradient 算，光照引发的纹理变化会扰动 patch feature → 表面凹凸幻觉） | 中（X、Y 主要受 FOV 控制，Z 部分受光照） |
| 远距离 fine texture | 平滑，Z 漂移 | **噪声爆炸**（小 Z-error → 大 normal-angle error） | Z 维方差放大 |
| 透明 / 镜面 | depth 给反射深度（如玻璃后的物体） | normal 给镜面表面 | **不自洽** — depth ≠ ∂point/∂Z |
| Sky | mask 标 infinity，前景不污染 | 不计算 | mask 排除 |

> ⚡ **隐含失败模式**: MoGe 三 head 用 "joint affine-invariant loss" 训练**应该**保持几何一致，但论文未提供 **"三 head 一致性"的显式度量**（如 `depth from ∂Z(pointmap) - depth_head` 残差直方图）. 这是工程实践中需要自己 ablation 的内容. `UNVERIFIED — not in paper`

### X.2.3 内部一致性 — 何时违反

理论上：
```
depth_head(x,y)     ≈ Z 分量 of point_map(x,y)
normal_head(x,y)    ≈ normalize(∇_{x,y} point_map(x,y))   (cross product)
```

实践上违反情境（来自工程社区经验，标 UNVERIFIED）：

- **遮挡边界**：depth head 给前景值，normal head 给"穿过遮挡"的过渡平面（梯度计算跨越深度 jump）. `UNVERIFIED, community report`
- **薄结构**（细绳、铁丝网）：depth head 因 patch 平均把薄物体抹掉；point map 失去这些点；normal 在该位置无定义.
- **OOD FOV**：FOV head 估错 → point map 的 X/Y 整体放大或压缩，但 depth head 仅给 Z，所以下游若用 `Z` 作距离不会出错；用 `point_map` 重建场景会得到拉伸的盒子.

工程对策：**对每帧计算 `||depth_head - point_map_Z||` 的统计量作 QA 门**；论文 mask 只过滤 sky，不过滤 multi-head 不一致区. **这是 MoGe 留给下游的工程坑**.

---

## X.3 · Interpretability (2026-05-21 补)

### X.3.1 三输出之间的关系 — 怎么互推

MoGe-2 在物理几何上的关系（[v1 §3](https://arxiv.org/abs/2410.19115), [v2 §Method](https://arxiv.org/abs/2507.02546)）：

```
point_map(u, v) = (X, Y, Z)
depth(u, v)     = Z                              (定义直接给)
fov             → fx, fy (假 principal point 居中)
X = (u - cx) * Z / fx                            (pinhole back-project)
Y = (v - cy) * Z / fy
normal(u, v)    = normalize(∂P/∂u × ∂P/∂v)       (cross product, image grid neighbors)
```

所以理论上**只需 (depth, FOV)** 就能恢复 point map；point map 是"depth + 内参"的派生量. **冗余监督**带来：
1. **正则化**：三 head 互相 sanity-check
2. **失败定位**：哪个 head 错可定位是 *Z* 错（depth）还是 *内参* 错（FOV）还是 *局部梯度* 错（normal）
3. **下游适配**：使用者直接拿 `point_map` 而不必跑 back-projection，工程节省

### X.3.2 affine-invariant 究竟代表什么 — 可以恢复米制吗

MoGe-1 输出是 **(scale, Z-shift) 双自由度未定**（[v1 §3.1](https://arxiv.org/abs/2410.19115)，论文把全 3D translation 简化为 Z-shift，前提是 principal point 居中）.

| 想做的事 | 需要 | MoGe-1 支持？ |
|---|---|---|
| 看 3D 形状 / 表面 | 无 | ✅ |
| 用 normal 跑光照重渲染 | 无 | ✅ |
| 测物体长宽比 | 无（affine-inv 保比例） | ✅ |
| 测物体绝对尺寸 | scale anchor（已知物体 / IMU） | ❌ 需外部 |
| 跨帧拼接 | scale 一致性 | ❌ 不保证 |
| Grasp pose（米制） | scale + offset | ❌ 用 Metric3D / stereo |

**MoGe-2 解决这个**：直接预测 metric scale point map（[arXiv:2507.02546](https://arxiv.org/abs/2507.02546)，2025-07-03 发布）. 论文说"carefully disentangles relative geometry (shape) prediction from metric scale recovery"，即 *形状* 仍按 MoGe-1 路线训练，*scale* 由独立分支恢复. 这印证了原版 §6 的预测："2027-06 前 MoGe v2 出 metric 输出". **预测提前一年半命中**.

### X.3.3 VGGT 谱系的先声 — multi-head 范式溯源

MoGe-1 (2024-10) 早于 VGGT (CVPR 2025) 几个月，且共享几个核心范式：

| 范式 | MoGe-1 | VGGT |
|---|---|---|
| Backbone | DINOv2 ViT | DINOv2 + alternating attention |
| Multi-head | point + depth + (FOV) + (mask) | depth + pointmap + camera + tracking |
| 训练 loss | joint affine-invariant | per-task L1 + reprojection |
| 视角 | single-view | multi-view (1→N) |
| Scale | affine-invariant (v1) / metric (v2) | metric (canonical first cam) |

> **谱系关系**: MoGe 是 **single-view 的 multi-head 几何头**；VGGT 把它推广到 multi-view + 加 tracking head. 二者共用"DINOv2 backbone + 多个几何任务联训 + 同一个 transformer 输出多种几何量"的设计哲学. MoGe **不是 VGGT 的子集**（VGGT 没 normal head），但它是 VGGT "多 head 几何 = 通用 3D 视觉模型" 论点的 single-view 证据.

`UNVERIFIED on direct citation`: 在 VGGT 论文里是否明确 cite MoGe 为先声 — 时间窗紧（MoGe arXiv 2024-10-24，VGGT 投稿 2024-11 ~ 12）.

### X.3.4 与 Metric3D 对比 — 哲学差异

| 维度 | MoGe (relative track) | Metric3D (canonical metric track) |
|---|---|---|
| **scale 哲学** | "scale 是 ambiguous，把它从 loss 里减掉" | "scale 用 canonical camera 假设钉住" |
| **内参依赖** | 无（FOV 自估） | 需（用于 canonical 化） |
| **训练数据要求** | 21 datasets ~99 M frames 混合（synthetic + SfM + LiDAR + Kinect），不同质量数据用不同 loss 组合（[v1 §4.1](https://arxiv.org/abs/2410.19115)） | 需要 metric-aligned 数据 |
| **失败模式** | OOD FOV → 全局拉伸但形状对 | OOD 焦距 → 米制错 |
| **下游契约** | "我给你形状，scale 你来" | "我给你米，相信我的训练分布" |
| **代表 ⚡ insight** | ROE alignment solver（[v1 §3.2](https://arxiv.org/abs/2410.19115)，O(N² log N) parallel 1D subproblems）让 affine-invariant 训练可优可解 | canonical camera transformation |

**两种路线在 2026 都活着**：
- **相对轨**: MoGe-1 → MoGe-2（自带 metric）→ 趋同 metric
- **米制轨**: Metric3D v1/v2 → 加 normal head（趋同 multi-task）

> ⚡ **Surprise**: MoGe-2（2025-07）已经把"affine-invariant 加 metric scale" 二合一，**两条路线在 metric multi-head 上合流**. 上面 §6 的 2-year falsifiable prediction 在 8 个月内命中.

---

## References

- MoGe v1 — Wang et al., Microsoft Research. *MoGe: Unlocking Accurate Monocular Geometry Estimation for Open-Domain Images with Optimal Training Supervision*. arXiv:2410.19115, 2024-10-24（CVPR 2025 Oral）. https://arxiv.org/abs/2410.19115
- MoGe-2 — Wang et al., Microsoft Research. *MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details*. arXiv:2507.02546, 2025-07-03. https://arxiv.org/abs/2507.02546
- GitHub: https://github.com/microsoft/MoGe (MIT license; DINOv2 sub-tree Apache 2.0)
- Depth Anything v2 — 见 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- Metric3D — 见 [`metric3d_dissection.md`](./metric3d_dissection.md)
- DINOv2 — Oquab et al. 2023. https://arxiv.org/abs/2304.07193
- MiDaS (affine-invariant loss 起源) — Ranftl et al. 2020. https://arxiv.org/abs/1907.01341

## Boundary

本文把 MoGe 作为 relative-track 多任务 monocular 几何模型解构. Metric monocular 见 [`metric3d_dissection.md`](./metric3d_dissection.md). 多视角 feed-forward 3D 见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md). 跨 embodiment scale 争论在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
