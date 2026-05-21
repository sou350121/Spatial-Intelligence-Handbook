# Mip-Splatting — Anti-Aliasing for 3DGS (Mip-Splatting 抗锯齿解构 — CVPR 2024)

> **Published**: 2023-11 (arXiv) / CVPR 2024
> **Paper**: Yu, Chen, Antic, Geiger — *Mip-Splatting: Alias-Free 3D Gaussian Splatting*
> **Team**: University of Tübingen + MPI for Intelligent Systems
> **Core position**: 一个小而有原则的修复（3D Nyquist-bound 平滑滤波 + 2D scale-aware Mip filter），让 3DGS 对尺度鲁棒 — 这是 gaussian splat 能用于 drone 与 VR headset 而非仅固定相机桌面 demo 的原因。

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**TL;DR:** Vanilla 3DGS 在训练相机距离下看着不错，离开这个距离就崩 — 放大、缩小、改焦距，都会看见 aliasing。Mip-Splatting 的 3D 平滑 + 2D 膨胀修复小而有原则，是 3DGS 能上 drone 和 VR headset，而非只是桌面 demo 的原因。

### X-Ray (non-expert friendly)

(a) Vanilla 3DGS 过拟合到训练相机的像素大小 — 从更近 / 更远 / 不同焦距渲染，会看到边缘模糊或高频闪烁。(b) Mip-Splatting 加一个 Nyquist 限定的 3D 平滑滤波（gaussian 不能小于训练视角能解析的尺度）+ 一个渲染时的 scale-aware 2D filter（Mip filter 替换固定膨胀核）。(c) 对空间 AI 工程师：任何穿越*尺度范围*的系统（drone 高度变化、VR 头动、wrist-cam → external-cam 重渲）都需要 Mip-Splatting — vanilla 3DGS 会 aliasing，下游 policy 会把 shimmer 当作 distribution shift。

### 📍 Research Landscape Timeline

```
Mip-NeRF 2021 ─► Mip-NeRF360 2022 ─► 3DGS SIGGRAPH 2023 ─► ★ Mip-Splatting CVPR 2024 ─► default in gsplat / nerfstudio 2025+
```

Mip-Splatting 是 3DGS 这边对 Mip-NeRF 在 radiance MLP 上解决的同一抗锯齿问题的回答。正在悄悄成为生产 gaussian pipeline 的默认起点。

Reference paper: Yu et al. "Mip-Splatting: Alias-Free 3D Gaussian Splatting." *CVPR 2024.* arXiv: https://arxiv.org/abs/2311.16493

---

## 1 · vanilla 3DGS 的静默失败模式

3DGS 在某一组相机内参（像素大小、焦距、图像分辨率）下训练。Gaussian 的大小被调到匹配训练像素脚印。只要推理相机看起来类似，就没事。

改变尺度就崩：

- **放大（比训练更近）** — 训练时亚像素的 gaussian 在推理变多像素。边缘模糊，表面细节融化。
- **缩小（比训练更远）** — 训练时多像素的 gaussian 在推理变亚像素。混叠成闪烁的高频噪声。
- **不同焦距** — 同问题，不同参数化。

对图形 demo 这是脚注。对具身 AI 这是能否上产品的差别：

- **drone** 飞越 3DGS 场景，从单次训练捕获要穿越 20× 距离范围。Vanilla 3DGS 在近端或远端有可见 aliasing。
- **VR / AR headset** 给走近 / 走远的用户渲染 3DGS — 表观尺度每秒都变。
- **manipulator** 在 wrist-camera 视角的 demo 上训练，无法从外部观察相机重渲染那些场景而不出现尺度偏移。

Mip-Splatting 就是让 3DGS 对尺度鲁棒的小而有原则的修复。

> ⚡ **Eureka Moment**: 训练和推理都必须 Nyquist-aware。仅 3D filter（训练时给 gaussian 大小封顶）会在推理时不必要地模糊；仅 2D filter（渲染时调整膨胀大小）不能修复已经过拟合到亚 Nyquist 细节的 gaussian。**把 3D-size-cap 与渲染时 scale-aware 2D filter 耦合才是契约** — 任一单独都是半修。

## 2 · 机制 — 两个部分

> 📌 **Napkin Formula**: 3D filter: `size(Gᵢ) ≥ max_views(pixel_footprint(view, Gᵢ))` 在每 iter 强制. 2D filter: 渲染时 kernel σ ∝ target_pixel_footprint，替换 vanilla 的固定膨胀. 两者合并 = projected gaussian 总能正确积分到目标像素网格.


```
   Training-time gaussians
              │
              ▼
   ┌─────────────────────────────┐
   │ 3D smoothing filter         │
   │   Track the maximum sample  │
   │   frequency (across all     │
   │   training views) at which  │
   │   each gaussian was         │
   │   observed.                 │
   │   Enforce minimum 3D size:  │
   │   gaussian cannot be        │
   │   smaller than the          │
   │   Nyquist limit of its      │
   │   training observations.    │
   └─────────────────────────────┘
              │
              ▼
   ┌─────────────────────────────┐
   │ 2D Mip filter (replaces     │
   │ the standard 2D dilation)   │
   │   At render time, given the │
   │   target pixel footprint,   │
   │   convolve the projected    │
   │   gaussian with a 2D box    │
   │   matching the pixel scale. │
   │   Replaces vanilla 3DGS's   │
   │   fixed dilation kernel.    │
   └─────────────────────────────┘
              │
              ▼
   Rendered image — alias-free across scales
```

两部分都是微小代码改动 — Mip-Splatting 不是架构重设计，是正确性修复。

- **3D smoothing filter** 是训练时的部分。记录每个 gaussian 在训练中被观测的最高空间频率。然后在*每次*训练 iter 强制下界，使 gaussian 3D extent 不会小于 Nyquist 允许值。这阻止 gaussian set 过拟合到训练相机实际未解析的高频细节。
- **2D Mip filter** 是渲染时的部分。Vanilla 3DGS rasterizer 对每个 projected gaussian 应用固定像素空间膨胀。Mip-Splatting 替换为 scale-aware 2D filter，随目标渲染像素脚印增长。渲染更小像素脚印（放大）时 filter 收缩；更大（缩小）时 filter 增长。结果是 projected gaussian 总能正确积分到目标像素网格。

两个 filter 是*耦合*的 — 3D filter 训练时封顶可达细节；2D filter 推理时正确重采样。任一单独都不够。

## 2.5 · Worked example — drone 立面 10× 尺度变化

50 m 高度训练，5 m 重渲。

- **Vanilla 3DGS**: gaussian 拟合到 ~5 cm 脚印 UNVERIFIED；5 m 处投影 ~10 px / gaussian（vs 训练 ~1 px）。边缘糊，PSNR 降 ~4 dB UNVERIFIED.
- **Mip-Splatting**: 3D Nyquist 封顶 + 2D Mip filter 适配近景尺度 → 边缘锐利，比训练低 ~1 dB UNVERIFIED.

3 dB 是 "demo vs 真实场景" 在下游检查上的 gap。

---

## 3 · 为什么这对 drone 和 VR 重要

- **drone 高度变化** — 50 m 捕获、5 m 检查穿越 10× 尺度。Vanilla 3DGS 一端或另一端 aliasing；Mip-Splatting 撑住。任何严肃 drone 端 pipeline 都用 Mip-Splatting 变体。
- **VR / AR 头动** — 房间级头平移对附近物体覆盖 ~3× 距离范围。Vanilla shimmer，Mip-Splatting 不会。
- **wrist-cam → external-cam 重渲** — 5 cm wrist-cam 训练数据渲染成 50 cm 外部观察者。同问题，同修复。

多尺度 benchmark 上报告的 PSNR 提升 `UNVERIFIED — Yu et al. report ~1–2 dB on multi-scale Mip-NeRF360` 是容易的数字。更难量化的结果是 "无 shimmer" — 而 shimmer 是下游 policy 会真实拾取的 distribution shift。

### 3.x · Hidden Assumptions

上游假设，违反就削弱 Mip-Splatting 的好处（或它解决不了）：

- **Pinhole model** — 两个 filter 都假设线性投影；鱼眼需要预先去畸变。
- **Stable training intrinsics** — 捕获中途自动变焦打破 3D Nyquist 估计。
- **多视角不同距离覆盖** — Mip-Splatting 能在新尺度重渲，但发明不出细节；全远景训练在近景仍受分辨率限制。
- **Photometric stability** — 抗锯齿是几何的；曝光偏移仍伤。
- **有界尺度范围（~10–20×）** — 超过 50× 尺度变化，连 Mip-Splatting 也需要 pyramid / progressive 变体。

违反时 Mip-Splatting 的好处缩小但不引入新失败模式 — 严格优于 vanilla，不会回退。

---

## 4 · 部署指南（何时该用）

- **单相机、单距离**（如固定外部相机的桌面 manipulation）— vanilla 3DGS 已够。Mip-Splatting 增加 ~5–10% 训练开销 `UNVERIFIED` 而无可见收益。
- **多相机、距离变化**（drone、多视角 manipulation、VR）— Mip-Splatting 是正确默认。训练时开销小，推理开销可忽略，伪影削减是 "能上 deployment 与不能" 的差别。
- **场景内长轨迹**（移动机器人巡楼）— Mip-Splatting 必选。机器人相机穿越每一种尺度。

## 5 · 2-year outlook

Mip-Splatting 会悄悄成为默认。到 2027 年，vanilla 3DGS 代码路径会变 legacy；生产 gaussian-splatting pipeline 会从 Mip-Splatting 起步，并在上面加自己的扩展（dynamic, SLAM, semantic）。

**Falsifiable prediction:** 到 2027-06，每一个主要开源 3DGS 实现（gsplat、nerfstudio 的 gsplat 后端、INRIA 参考）都会默认开启 Mip-Splatting，而非 opt-in flag。剩余保持 vanilla 的将是 benchmark-replication 代码，不是生产栈。

**Interview Tip**: 被问 "为什么我的 3DGS 训练视角看起来好，靠近就 shimmer"，答案是 *尺度变化下的 aliasing* — vanilla 3DGS 对 gaussian size 没有 Nyquist 约束。Mip-Splatting 的 3D + 2D 耦合 filter 是标准修复；引用 Yu et al. CVPR 2024。

## References

- **Mip-Splatting** — Yu et al. *CVPR 2024.* https://arxiv.org/abs/2311.16493
- **Mip-NeRF**（NeRF 谱系下的抗锯齿前身）— Barron et al. *ICCV 2021.* https://arxiv.org/abs/2103.13415
- **Mip-NeRF 360**（多尺度 benchmark）— Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **3DGS original**（被修复的东西）— Kerbl et al. *SIGGRAPH 2023.* https://arxiv.org/abs/2308.04079

## Boundary

本文覆盖 3DGS 的多尺度抗锯齿修复。**不**覆盖：

- 静态 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- 动态 4D 扩展 → `foundations/3dgs-family/4dgs_dynamic_scenes.md`
- SLAM 耦合 gaussian → `foundations/3dgs-family/gs_slam_dissection.md`
- Drone 端部署 → `embodiments/aerial/`（待写）
- VLA 对 gaussian map 的消费 → `bridge-to-vla/feature-cloud-to-action.md`
- 跨尺度的 cross-representation 对比 → `crossing/representation-migration/`, `crossing/scale-comparison/`
- Feed-forward 3D 替代 → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
