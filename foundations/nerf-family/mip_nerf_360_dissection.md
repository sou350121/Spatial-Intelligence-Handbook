# Mip-NeRF 360 解构 (Mip-NeRF 360: Unbounded Anti-Aliased Neural Radiance Fields)

> **Publication:** CVPR 2022 (oral)
> **Paper:** Barron, Mildenhall, Verbin, Srinivasan, Hedman. Google Research. arXiv: https://arxiv.org/abs/2111.12077
> **Core position:** 正确处理无界 360° 场景的 NeRF 变体，且仍是 3DGS 在四年后依然追赶的*质量* benchmark.

**Status:** v1 — 带立场。除非标 `UNVERIFIED`，数字来自论文。
**TL;DR:** Vanilla NeRF 和 Mip-NeRF 都假设场景在有界 box 内. 真实拍摄不是 — 把相机指向后院就有天空、远处建筑、地面到地平线. Mip-NeRF 360 贡献三件：(1) 基于 disparity 的*场景收缩*，把无界空间映到有界球；(2) *cone-tracing with gaussian sampling*（来自 Mip-NeRF）做多尺度抗锯齿；(3) *online distillation + proposal sampling* 学表面在哪. 3DGS 上报告的 LPIPS / SSIM 是与 Mip-NeRF 360 对比的 — 在最难的场景上 3DGS 仍输. **3DGS 赢速度与可编辑；Mip-NeRF 360 仍赢质量.**

**X-Ray.** 按 "能塞进机器人栈" 衡量，3DGS 取代一切. 按 "Mip-NeRF 360 benchmark 最佳 PSNR" 衡量，2026 答案仍是 NeRF（Zip-NeRF，直系继任）. 对空间智能工程师，教训是*别把部署主导混同技术优越* — 3DGS 赢是因显式 primitive 对机器人友好，不是因 gaussian splat 更精确.

## 📍 Research panorama timeline

```
2020       2021              2022 (Jan)         2022 (Nov)         2023            2024-26
NeRF     ► Mip-NeRF        ► Mip-NeRF 360     ► Instant-NGP-     ► 3DGS displaces ► Zip-NeRF
(ECCV)     (anti-aliasing,   YOU ARE HERE       like speedups     for robotics     (still SOTA
            cone tracing)    unbounded +                                            on Mip360)
                             multi-scale
                             └─ "make NeRF correct" wing ─┘   └─ "make NeRF deployable" wing ─┘
```

Mip-NeRF 360 = *最大化质量*分支. Instant-NGP 和 3DGS = *最大化速度*分支. 几乎不重叠，直到 Zip-NeRF (2023) 尝试合并.

---

## 1 · Core architecture

### 1.1 System overview

| Component | Function | From |
|---|---|---|
| Scene contraction `f(x)` | 把无界 ℝ³ → 半径 2 的有界球 | **New** |
| Conical frustum sampling | 像素 = 锥；沿锥采样 gaussian | Mip-NeRF (2021) |
| IPE (integrated PE) | 编码 gaussian *分布*，不是点 | Mip-NeRF (2021) |
| Proposal MLP + NeRF MLP | Proposal 预测哪里采样 | **New** |
| Online distillation | Proposal 由 NeRF density 监督 | **New** |
| Distortion regularizer | 惩罚扩散权重直方图；anti-floater | **New** |

### 1.2 ⚡ Eureka moment

> **无界场景在 disparity（逆深度）空间里收缩距离后即变有界 — 渲染唯一在意的指标是每屏像素的角分辨率，disparity 保留它.**

`f(x) = (2 − 1/‖x‖)·(x/‖x‖)` 对 `‖x‖ > 1` 把无穷射线平滑映到半径 2 的球. 像素在 100 m 处覆盖比 1 m 处更多*世界空间* — disparity 匹配那种 linear-in-screen-pixels 增长.

### 1.3 Flow diagram

```
   Camera ray (cone, not line)
        │
        ▼
   Sample N gaussian frustums along cone
        │
        ▼
   Contract each f(μ), f(Σ)    ── unbounded → bounded
        │
        ▼
   Proposal MLP (density only) → resample N' around peaks
        │
        ▼
   NeRF MLP (σ + RGB)
        │
        ▼
   Volume render → pixel
        │
        ├──► MSE loss
        ├──► Online distillation (proposal ← NeRF σ-histogram)
        └──► Distortion regularizer (anti-floater)
```

---

## 2 · Math core: contraction + cone tracing

### 📌 Napkin Formula

```
contract(x) = x                              if ‖x‖ ≤ 1
contract(x) = (2 − 1/‖x‖) · x/‖x‖           if ‖x‖ > 1

per-pixel cone radius r(t) = base_radius · t
IPE(μ, Σ) = encode gaussian distribution    (vs encode point in NeRF)
```

三件正交；去掉任一 → 退化.

### 2.1 为什么 cone tracing 在尺度上重要

NeRF 采样点；同点被近、远相机查询给同样 MLP 输出. 但远相机上一个*像素*覆盖更大世界区域 — 正确答案是积分而非点. 没有 cone tracing，收缩的无界场景因每个远像素覆盖巨大收缩体而严重 aliasing.

### 2.2 Proposal network + distortion

Proposal MLP（仅 density）替换 NeRF 的 coarse pass → 每像素 ~96 评估而非 192. 通过 weight 直方图上的 online KL distillation 训练以匹配 NeRF 的 density.

Distortion regularizer: `L_dist = ∫∫ w(s)w(t)|s−t| ds dt`. 沿射线惩罚扩散权重直方图，把密度集中到明确深度. 单一正则杀掉多数 floater.

---

## 3 · Worked example: contraction 实战

后院 200 m 外建筑的相机射线.

| Sample | t (raw) | ‖x‖ | contracted | Meaning |
|---|---|---|---|---|
| Near grass | 1 m | 1.0 | 1.0 | 前景，无收缩 |
| Tree | 5 m | 5.0 | 1.8 | 压缩但定位 |
| Building | 200 m | 200 | 1.995 | 接近外壳 |
| Sky | ∞ | ∞ | → 2.0 | 边界 |

MLP 只见过 `‖·‖ ≤ 2`. **天空是半径 2 处的薄壳** — 与建筑 (1.995) 可区分但勉强. 无收缩时，MLP 需四个数量级的 density；有收缩时，同容量覆盖一切.

---

## 4 · Engineering view: 与 vanilla NeRF 的代价对比

| Metric | NeRF | Mip-NeRF 360 |
|---|---|---|
| Training | ~1 day | ~7h `UNVERIFIED` (TPU v3) |
| Render | <1 FPS | <1 FPS |
| PSNR (Mip360 bench) | ~22 dB | **~28 dB** |
| LPIPS | ~0.45 | **~0.25** |
| Reproducible? | Yes (PyTorch) | Painful; ref is JAX |

7 场景 Mip-NeRF 360 benchmark 上 2026 排行榜快照 `UNVERIFIED`:

- 3DGS vanilla (2023): ~27.4 PSNR
- Mip-NeRF 360: ~27.7
- Zip-NeRF (2023): **~28.5**
- Mip-Splatting (2024): ~27.6

**NeRF 谱系仍以 0.5–1 dB 取胜**，wall-clock 输 ~20×.

---

## 5 · Data and evaluation

- **Mip-NeRF 360 benchmark**（此处引入）：7 个无界 360° 场景 — bicycle, garden, stump, room, counter, kitchen, bonsai. 每个 100–300 张，COLMAP 位姿.
- 定义了 "unbounded NeRF" 的含义 — 2022–2026 radiance-field 论文中引用最多的单个 eval.
- 不测动态、低光、透明. 是质量测试，不是鲁棒性测试.

---

## 6 · Capabilities and failure modes

**做得好：** 有界物体配无界背景的 360° 拍摄（"后院带主体"）；通过 cone tracing 做多尺度观看；比 vanilla NeRF 更好的镜面高光.

### 6.1 Hidden assumptions

- **单一有界主体** — contraction 假设有意义的"内部"（单位球）. 无明确中心（长街）→ 浪费容量.
- **静态、良好标定** — 继承 NeRF 的 "静态 + COLMAP 位姿" 要求.
- **可接受慢训练** — 每场景 ~7h；规模化不实际.
- **无编辑** — 隐式 MLP；不能删盆栽保留厨房.
- **天空几何退化** — 塌缩到薄壳.
- **接近 pinhole 相机** — 鱼眼 / 极广角违反线性锥半径.

### 6.1.x GitHub 实地失败（atlas 联动）

> ⚠️ **2026-05 状态**：`google-research/multinerf`（含 Mip-NeRF 360 / Ref-NeRF / RawNeRF 参考实现）已于 **2025-02-11 被 Google 官方 archive**（只读）。这是 NeRF 谱系**最后一个高质量参考实现**进入只读状态；**不要指望维护**。

- **GitHub-validated**：archive 前留存的失败模式直接对应隐藏假设破裂 — 新 COLMAP 输出 `transforms.json` 不匹配 (#162)、JAX 版本兼容断 (`jax.core` has no attribute 'Shape' #156)、JAX 路径处理 quirk 强制 absolute path (#160)，详见 [`github_failure_atlas.md`](./github_failure_atlas.md)。
- **GitHub-validated**：离线重建仍是质量 SOTA 之一，但**部署要预算 JAX 老版本 + 数据集 / COLMAP 对接的工程债**；archive 意味着这些坑只能 fork 自修。新项目优先 Zip-NeRF (Barron 团队后续) + nerfstudio。

### 6.2 为什么这对 3DGS 重要

3DGS *已知弱点*是无界：远 gaussian 长巨大，存储爆. Mip-NeRF 360 contraction *按构造解决*.

- 质量：Mip-NeRF 360 以 ~1 dB / ~10% LPIPS 取胜.
- 速度：3DGS 20–100×.
- 可编辑：3DGS.
- 存储：可比（~500 MB）.

电影 VFX 离线后院重建 → Mip-NeRF 360. 机器人需 <10 ms 渲染 → 3DGS + Mip-Splatting.

---

## 7 · Comparison and interview tip

| Property | NeRF | Mip-NeRF | **Mip-NeRF 360** | Zip-NeRF | 3DGS |
|---|---|---|---|---|---|
| Anti-aliased | No | Yes | Yes | Yes | Partial |
| Unbounded | No | No | **Yes** | Yes | Limited |
| Training | 1d | 1d | 7h | 5h `UNVERIFIED` | 30m |
| Render | <1 | <1 | <1 | ~1 | 100 FPS |
| PSNR Mip360 | 22 | 24 | 27.7 | **28.5** | 27.4 |

> **🎤 Interview tip.** "若 Mip-NeRF 360 在质量上仍 SOTA，为什么 3DGS 赢了部署？" — 正确答案：*"质量不是单一数字 — 对机器人，'渲染速率 × 可编辑性 × 存储' 压倒 'PSNR 最后 1 dB'. Mip-NeRF 360 仍赢离线重建 benchmark；3DGS 赢是因其 primitive 匹配机器人操作约束（可检查、快、可编辑）. 二者共存."* 错答："3DGS 就是更好". 在机器人在意的轴上更好，不是在这篇论文引入的 benchmark 上.

---

## References

- **Mip-NeRF 360** — Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **Mip-NeRF** — Barron et al. *ICCV 2021.* https://arxiv.org/abs/2103.13415
- **Zip-NeRF** — Barron et al. *ICCV 2023.* https://arxiv.org/abs/2304.06706
- **Mip-Splatting** — Yu et al. *CVPR 2024.* https://arxiv.org/abs/2311.16493
- **3DGS** — `foundations/3dgs-family/3dgs_original_dissection.md`

## Boundary

仅解构 Mip-NeRF 360. **不**覆盖表面重建 NeRF（NeuS, VolSDF）、稀疏视角（PixelNeRF）、动态、城市级（→ `block_nerf_large_scenes.md`）或 3DGS 替代（→ `foundations/3dgs-family/`）.

---

[← Back to NeRF Family README](./overview.md)
