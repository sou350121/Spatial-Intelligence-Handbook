<!-- ontology-5axis
problem: Novel-view synthesis (alias-free across scales)
representation: 3DGS + 3D smoothing filter + 2D Mip filter
sensor: RGB + poses (from COLMAP)
paradigm: Hybrid-DiffRender (Gaussian rasterize + anti-alias)
time: Per-scene optimization
ref: ../../cheat-sheet/ontology.md §8.2
-->

# Mip-Splatting (Mip-Splatting 抗锯齿正典 — CVPR 2024 Best Student Paper)

> **Published**: 2023-11 (arXiv 2311.16493) / CVPR 2024 (Best Student Paper)
> **Paper**: Yu, Chen, Huang, Sattler, Geiger — *Mip-Splatting: Alias-Free 3D Gaussian Splatting*
> **Team**: University of Tübingen + ETH Zurich + Czech Technical University + MPI for Intelligent Systems
> **Core position**: 3DGS 谱系第一个把"训练-推理尺度不一致"系统化修复的 drop-in patch — 3D Nyquist 限定平滑 + 2D Mip filter 替换 vanilla 固定膨胀，让 3DGS 从"训练相机尺度专用"变成"任意尺度可渲染"。这是 3DGS 能用在 drone / VR / multi-cam 而非只是桌面 demo 的真正分水岭。

**Status:** v1.0 — 创建于 2026-05-24，按 AGENTS.md 14 项门槛模板填充。Hyperparams 标 UNVERIFIED。
**TL;DR:** Vanilla 3DGS 不是"训练完就万事大吉"——它把 gaussian 大小过拟合到训练相机的像素脚印；离开这个尺度就出现 zoom-in 模糊、zoom-out shimmer。Mip-Splatting 用两个互补 filter 一起修：3D filter 在训练时给每个 gaussian 一个 Nyquist 下界（不能小于训练视角能解析的尺寸），2D filter 在渲染时按目标像素脚印自适应卷积。两个 filter 必须*耦合*，单独用任一都是半修。代价：训练时间 ~+5–10% UNVERIFIED，推理时间几乎不变；收益：多尺度 PSNR ~+1–2 dB，shimmer artifact 消失。对具身 AI 这是"能否部署"的分水岭，不是"指标变好"的论文级改进。

> **与 `mip_splatting.md` 的分工**：原文件 v1.1 已存在并覆盖核心机制；本 dissection 是 2026-05-24 按 14 项门槛 + atlas v2 重写的正典版，**新增内容**：(a) Mip-NeRF/Mip-NeRF360 谱系前身的概念对比（Yu 等怎么把 Barron 在 MLP 上的 Nyquist 思想搬到显式 gaussian）；(b) 2026-05-24 重爬 issues + PRs 的 atlas 证据细化；(c) 5-axis ontology header + 8 节标准化结构。**不重复**原文件已有的 drone/VR 部署论述，跳转 `mip_splatting.md` §3。

### X-Ray (non-expert friendly)

(a) Vanilla 3DGS 训练时每个 gaussian 的大小会被 optimizer 自由调整去匹配训练相机的像素脚印 — 这本质是"训练相机分辨率下的精细过拟合"。当推理相机距离 / 焦距 / 分辨率改变，gaussian 在投影后要么变得太大（zoom-in 模糊）要么变得亚像素（zoom-out 闪烁混叠）。(b) Mip-Splatting 一边在训练时给每个 gaussian 一个"Nyquist 下界"（gaussian 3D 范围不能小于所有训练视角中*最高*采样频率的 1/(2f)），一边在渲染时按目标像素脚印做 scale-aware 2D box filter 卷积。3D + 2D 耦合 = 训练时不再过拟合到亚 Nyquist 假细节，推理时正确积分到任意目标网格。(c) 对空间 AI 工程师：任何穿越尺度范围的系统（drone 50m→5m 飞越 / VR 头动 / wrist-cam 数据被外部相机重渲）都*必须*用 Mip-Splatting，否则下游 policy 会把 vanilla 3DGS 的 shimmer 当作 distribution shift 而崩溃。

### 📍 Research Landscape Timeline

```
Mip-NeRF (Barron 2021) ─► Mip-NeRF360 (Barron 2022) ─► 3DGS (Kerbl SIGGRAPH 2023)
                                                                    │
                                                                    ▼
                            ★ Mip-Splatting (Yu CVPR 2024 Best Student Paper)
                                                                    │
                                                                    ▼
            Gaussian Opacity Fields (2024) ─► default in gsplat / nerfstudio 2025+
                                          └─► Scaffold-GS / 2DGS / Compact3D (吸收 Mip-Splatting 思路)
```

Mip-Splatting 把 Barron 在 MLP 上解决的 anti-aliasing 问题对应搬到 3DGS 显式 gaussian 表示。它**不是**抗锯齿研究的终点 — Gaussian Opacity Fields (arXiv 2404.10772) 后续又改进了 densification metric，autonomousvision 团队把这部分回流到 Mip-Splatting repo（README 公告）。但 Mip-Splatting 是把 "scale-aware rendering" 这个抽象概念在 3DGS 谱系里**第一个工程化得能 ship** 的工作。

Paper: Yu, Chen, Huang, Sattler, Geiger. *CVPR 2024 Best Student Paper.* arXiv: https://arxiv.org/abs/2311.16493
Code: https://github.com/autonomousvision/mip-splatting （1.4k stars / 31 open issues / 16 commits on main）

---

## 1 · 为什么这篇论文重要（abstract 里没强调的部分）

3DGS 原版（Kerbl SIGGRAPH 2023）发布六个月内就成为 NVS baseline，但所有早期 demo 都有一个隐藏约束：**推理相机要类似训练相机**。这在 paper figure 里看不出来 — paper figure 用 held-out test views，分布跟训练 views 几乎一致。一旦你试图：

- 从训练分布外的距离重渲（drone capture 训练在 50m，要重渲 5m 近景检查）；
- 改变 image resolution（用 4K 训练，要在 mobile 上 720p 渲染）；
- 改变 focal length（不同焦距等价于不同 pixel footprint）；

vanilla 3DGS 就开始崩 — 不是失败到无法渲染，而是出现 shimmer / 边缘模糊 / floater 闪烁，这种 *partial failure* 是机器人 pipeline 最危险的形态：下游 policy 不知道场景表示出问题了，会把 artifact 当 distribution shift 并产生错误 action。

Mip-Splatting 的核心贡献**不是引入一个新的渲染表示**，而是把 vanilla 3DGS 的一个静默假设（"训练相机 ≈ 推理相机"）暴露出来，并给出 ~100 行代码的修复。这种"小而正确"的工作通常被低估 — 但它是 3DGS 谱系能从 "research demo" 真正进入 "可上 drone / VR / robot" 的临界改进。Best Student Paper 的评委认出了这一点。

## 2 · 机制 — 两个 filter 必须耦合

> 📌 **Napkin Formula**:
> - **3D filter**（训练时）：`size(Gᵢ) ≥ 0.2 / f_max` 其中 `f_max = max over training views of (focal_length / depth_to_Gᵢ)`，单位是 sample-per-world-unit。`0.2` 是 Yu 等给出的工程常数 `UNVERIFIED — 论文具体值需查表`。
> - **2D filter**（渲染时）：`output(x) = ∫ G_projected(u) · box(u - x; σ_pixel) du` 其中 `σ_pixel = max(target_pixel_footprint, original_dilation)`，替换 vanilla 3DGS 的固定 0.3 px 膨胀。
> - 两者合并：训练时不让 gaussian "细于 Nyquist"，推理时按目标网格正确低通滤波。

> ⚡ **Eureka Moment**: 关键洞察是 *aliasing 在 3DGS 里发生在两个地方，必须两处都修*。仅 3D filter（"训练时给 gaussian 大小封顶"）在 zoom-in 推理时不必要地模糊远处细节；仅 2D filter（"渲染时调整 dilation 大小"）不能修复已经过拟合到亚 Nyquist 假细节的 gaussian set。把 3D-size-cap 与渲染时 scale-aware 2D filter *耦合*才是契约 — 任一单独都是半修。Yu 等的 ablation table（论文 Table 3 UNVERIFIED）应该量化证实这一点。

```
   Training (per iter)
          │
          ▼
   ┌──────────────────────────────┐
   │ 3D smoothing filter:         │
   │   For each gaussian Gᵢ:      │
   │     f_max(Gᵢ) = max over     │
   │       training views v of    │
   │       (focal_v / depth_v(Gᵢ))│
   │     enforce:                 │
   │       size(Gᵢ) >= c / f_max  │
   │   (c ≈ 0.2 UNVERIFIED)       │
   │                              │
   │   Effect: gaussian 不能小于  │
   │   训练相机最高采样频率允许   │
   │   解析的尺寸 → 不再过拟合到  │
   │   亚 Nyquist 假细节          │
   └──────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────┐
   │ 2D Mip filter (render time): │
   │   Given target pixel         │
   │   footprint σ_target:        │
   │     replace vanilla's        │
   │     fixed dilation (0.3 px)  │
   │     with box filter of size  │
   │     σ = max(σ_target, σ_dil) │
   │                              │
   │   Effect: projected gaussian │
   │   总是被卷积到匹配的目标     │
   │   像素 footprint → zoom-out  │
   │   时正确低通避免混叠         │
   └──────────────────────────────┘
          │
          ▼
   Rendered image — alias-free across scales (zoom 10–20× safe)
```

两个 filter 都是微小代码改动 — Mip-Splatting **不是架构重设计**，是正确性修复。这恰好是它能 drop-in 替换 vanilla 3DGS 并被快速吸收的原因：你不需要重训、不需要新数据、不需要换 rasterizer，只需要重编 `diff-gaussian-rasterization` extension。

### 与 Mip-NeRF 谱系的概念对应

| Aspect | Mip-NeRF (Barron ICCV 2021) | Mip-Splatting (Yu CVPR 2024) |
|---|---|---|
| 基础表示 | MLP radiance field | Explicit 3D gaussians |
| Aliasing source | ray 上的 point sample 在不同分辨率下 alias | gaussian 在不同 pixel footprint 下投影 alias |
| 抗锯齿手段 | conical frustum + integrated positional encoding (IPE) | 3D Nyquist-bound size cap + 2D scale-aware filter |
| Train/test scale 鲁棒性 | 是（核心贡献）| 是（核心贡献）|
| 是否改基础渲染契约 | 否（仍 ray marching, 只是改 PE） | 否（仍 rasterize+α-blend, 只是改 dilation）|

**关键观察**：Mip-Splatting 的设计哲学是把 Barron 在 NeRF 上的 Nyquist-aware 思想（"渲染时考虑采样频率"）翻译到 3DGS 的显式 gaussian 表示。Mip-NeRF 通过让每个 ray 携带一个 frustum 信息来做；Mip-Splatting 通过让每个 gaussian 携带 Nyquist 下界 + 渲染时 scale-aware 卷积来做。这种"在范式 A 上的好思想要在范式 B 上也实现一遍"是 3DGS 谱系演化的常见模式（参见 `4dgs_dynamic_scenes.md` 把 dynamic NeRF 思想搬到 3DGS）。

## 3 · 实用部署数字

| Knob | Vanilla 3DGS | Mip-Splatting | 何时差异显著 |
|---|---|---|---|
| 训练时间（A6000, Mip-NeRF360） | ~30 min UNVERIFIED | ~33 min（+10%）UNVERIFIED | 任何场景 |
| 推理 FPS（1080p, RTX 4090） | ~300 FPS UNVERIFIED | ~290 FPS（无显著差异） | 任何场景 |
| Multi-scale PSNR vs single-scale eval | -3 to -5 dB UNVERIFIED | -1 to -2 dB UNVERIFIED | drone / VR / multi-cam |
| Disk size / scene | ~1–2 GB | ~1–2 GB（无变化） | — |
| Code change vs vanilla | baseline | ~100 lines + recompile rasterizer | 是 drop-in |

**部署口径**：单场景 single-camera demo 用 vanilla 即可（Mip-Splatting 的 +10% 训练开销没收益）；任何穿越尺度的真实部署（drone / VR / 任何 multi-cam pipeline）应该把 Mip-Splatting 作默认起点而非 opt-in。这是 §5 outlook 的来源。

## 3.5 · Worked example — drone 50 m → 5 m 立面巡检

> 一个 industrial drone 飞 50 m 高度沿建筑物立面拍 30 张图，训练 3DGS 用于后续从任意距离重渲检查。

| Phase | Vanilla 3DGS | Mip-Splatting |
|---|---|---|
| Train @ 50 m | gaussian 拟合到 ~5 cm pixel footprint UNVERIFIED | 同 vanilla，但 3D filter 强制 size ≥ ~3 cm UNVERIFIED |
| Render @ 50 m (test view, same scale) | PSNR ~32 dB UNVERIFIED | PSNR ~32 dB UNVERIFIED — 同等 |
| Render @ 25 m (2× closer) | PSNR ~30 dB，边缘开始模糊 UNVERIFIED | PSNR ~31.5 dB，边缘锐利 UNVERIFIED |
| Render @ 5 m (10× closer) | PSNR ~27 dB UNVERIFIED，可见 shimmer + ghost | PSNR ~30 dB UNVERIFIED，无 shimmer |
| Render @ 100 m (2× farther) | PSNR ~29 dB UNVERIFIED，远景闪烁 | PSNR ~31 dB UNVERIFIED，稳定 |

那 3 dB 在 5 m 近景的差距是 "demo 通过 vs 巡检员看了说不行" 的差别。具体数字 UNVERIFIED — Yu 等论文 Table 2 给的是 Mip-NeRF360 multi-scale benchmark 上 ~1–2 dB 综合提升；drone 立面 10× 尺度的差距*应*更大，但需要实地测试验证。

---

## 4 · 它在哪里 break（论文没着墨的部分）

- **Pinhole camera 假设** — 3D filter 和 2D filter 都建立在线性投影上。鱼眼 / 全景 / catadioptric 相机需要先 undistort 再用 Mip-Splatting；直接喂未矫正图像，Nyquist 估计错位，效果可能比 vanilla 还差。
- **训练相机 intrinsics 必须稳定** — 训练时自动变焦（手机自动对焦改变 focal length）打破 `f_max` 估计；3D filter 假设 intrinsics 已知且固定。
- **极端尺度变化（>50×）仍需 pyramid 变体** — Mip-Splatting 论文 evaluation 在 ~10× 尺度变化内 robust；50× 以上（如卫星图 → 街景细节）需要 progressive 或 multi-resolution gaussian set。
- **依然 per-scene optimization** — Mip-Splatting 修了 aliasing，但没修 3DGS 的另两个 fundamental constraints：(a) 仍依赖 COLMAP SfM init，(b) 仍需要每场景 30 min 训练。Feed-forward gaussian models (LRM, pixelSplat) 才修这两个。
- **不能凭空 invent 细节** — 5 m 近景重渲只能锐化*存在*的 gaussian，不能补出训练时没看到的 sub-cm 细节。Mip-Splatting 是"正确低通"，不是 "super-resolution"。
- **License 继承 INRIA 3DGS 非商业限制** — Mip-Splatting README 明说 "Please follow the license of 3DGS"。这意味着 INRIA gaussian-splatting 的商业许可限制 *也* 适用于 Mip-Splatting；要商用必须走 INRIA 邮件流程（见 `3dgs_original_dissection.md` §8.1 #5），或换 `gsplat` 这类 BSD/MIT reimplementation（gsplat 已吸收 Mip-Splatting 思路）。

### 4.x · Hidden Assumptions

上游假设，违反就削弱或破坏 Mip-Splatting 的好处：

- **Pinhole projection model** — 鱼眼 / 全景需先去畸变；否则两个 filter 的 Nyquist 估计都错位。
- **Stable training intrinsics** — 拍摄中途变焦 / autofocus 飘移会让 `f_max` 估计失真；商用 SDK 需锁定 intrinsics。
- **训练 views 跨尺度覆盖** — Mip-Splatting 能在新尺度*正确低通*，但发明不出细节。全远景训练在近景仍受原始解析度限制（≠ super-resolution）。
- **Photometric stability** — 抗锯齿修的是几何，不修曝光偏移 / white balance 漂移；这些仍需独立处理（如 NeRF-W 的 latent appearance code）。
- **有界尺度范围（~10–20×）** — 超过这个范围 Mip-Splatting 不够，需要 progressive / pyramid 变体（如 Octree-GS, ZoomGS UNVERIFIED — 检查具体方案名）。
- **底层 3DGS 假设全部继承** — Good COLMAP init / static scene / 足够 training views — 这些 vanilla 3DGS 的隐含假设 Mip-Splatting 一个都没修，违反它们依然崩。详见 `3dgs_original_dissection.md` §4.x。

违反时通常是"Mip-Splatting 的好处缩小"而非"引入新失败模式" — Mip-Splatting 严格优于 vanilla，最坏退化为 vanilla 等价。

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05-24）

autonomousvision/mip-splatting 1.4k stars / 31 open issues / 16 commits — *算法成熟、节奏放慢、issue 都是工程/数据/集成层面而非崩溃*。

- **GitHub-validated（项目节奏）**：1.4k stars 但仅 16 commits 主干提交 — 典型"paper 发完代码稳定下来、社区接手"的成熟模式。近期*唯一*显著更新是吸收 Gaussian Opacity Fields (arXiv 2404.10772) 的 densification metric（README 公告，要求用户重装 `diff-gaussian-rasterization`），表明 autonomousvision 团队仍维护但优先级在向 GOF / GOF-followup 转移；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#mip-splatting-autonomousvisionmip-splatting)。
- **GitHub-validated（install / build 长尾）**：[#65 CUDA version mismatch](https://github.com/autonomousvision/mip-splatting/issues/65) 是高复现度问题（修改后的 `diff-gaussian-rasterization` 对 CUDA 版本敏感，比 vanilla 3DGS 更挑剔）；[#68 training script stuck at 0%](https://github.com/autonomousvision/mip-splatting/issues/68) 与底层 3DGS 同款故障模式（详见 `3dgs_original_dissection.md` §8.1 #4）— 印证 "Mip-Splatting 继承 3DGS 所有部署痛点 + 自带 rasterizer 重编挑剔"。
- **GitHub-validated（数据 pipeline 复用问题）**：[#70 AssertionError: colmap camera model not handled](https://github.com/autonomousvision/mip-splatting/issues/70) + [#69 convert.py issue](https://github.com/autonomousvision/mip-splatting/issues/69) — 自定义 COLMAP 数据进 Mip-Splatting 时与 3DGS 同款问题（特定 camera model 不支持）；[#66 poor results on custom data](https://github.com/autonomousvision/mip-splatting/issues/66) 提示**自有数据先在 Mip-NeRF360 公开 scene 上 sanity check 跑通再上**，避免 "不知道是数据问题还是算法不适合"。
- **GitHub-validated（surprise — viewer 集成）**：[#75 supersplat viewer 集成结果错误](https://github.com/autonomousvision/mip-splatting/issues/75) + [#74 website models seem blurry](https://github.com/autonomousvision/mip-splatting/issues/74) — Mip-Splatting 训练出的 gaussian set 在第三方 viewer（supersplat）渲染结果与官方不一致；**说明 2D Mip filter 是 render-time 逻辑，导出 `.ply` 后下游 viewer 必须 *也* 实现 Mip filter**，否则你在自己机器看着好的场景，部署给客户后看是模糊的。这是 ply-as-interchange 的隐藏陷阱。
- **GitHub-validated（核心参数 doc 不足）**：[#73 Gaussian ball size & ratio to pixel](https://github.com/autonomousvision/mip-splatting/issues/73) — 即使是认真读论文的用户也对核心参数（3D filter 的 Nyquist 常数 `c`、2D filter 的最小 σ_dil）的具体取值困惑；论文公布的工程常数没在 README 完整列出，无 maintainer 回复 — 印证 §2 "3D + 2D 耦合是工程细节，社区仍在啃"。

**Repo health signal**: 1.4k★ / 31 open issues / 16 commits / 31 open issues 都无 maintainer 回复 — "Best Student Paper + paper-as-reference-impl" 模式：算法已被 gsplat / nerfstudio 吸收，autonomousvision repo 作论文复现 reference 而非生产 backbone。**生产路径推荐 gsplat 后端**（BSD license + 同等 Mip-Splatting 支持 + 积极维护）。

---

## 5 · 为什么机器人团队在乎（本手册核心车道）

本节简要补充 `mip_splatting.md` §3 已论述的 drone/VR/wrist-cam 部署 — 这里聚焦 **VLA pipeline 的特殊关切**：

1. **Demo data → policy 数据增强** — Manipulation policy 经常用 wrist-cam 训练但需要外部观察相机重渲做数据增强（更多视角 → 更鲁棒 policy）。vanilla 3DGS 在 wrist-cam 5cm → external-cam 50cm 重渲时 shimmer，policy 训练数据里夹带 artifact。Mip-Splatting 修这个。
2. **Sim-to-real visual fidelity** — 用 3DGS 场景做 sim → real 视觉训练时，仿真渲染相机参数*必须*能跨越部署相机分布。vanilla 3DGS 强制 sim 相机要近似 capture 相机；Mip-Splatting 解锁 sim 相机可以是 capture 时没见过的 intrinsics / pose。
3. **Multi-embodiment shared scene** — 同一个 3DGS 场景 asset 要被 drone（远视角）+ humanoid（人眼高度）+ manipulator（wrist-cam 近视角）共享时，vanilla 3DGS 选哪个相机训练都对其他相机不友好。Mip-Splatting 让一个 capture 适配三个 embodiment。

对 VLA-Handbook 的 `bridge-to-vla/feature-cloud-to-action.md` 章节，Mip-Splatting 是"3DGS scene 喂给 policy"路径的*前置必要*改进 — 否则 policy 学到的不是场景，是 vanilla 3DGS 的 viewer artifact。

## 6 · 2-year outlook

Mip-Splatting 不是"一个论文"，而是"3DGS 谱系的最低正确性 bar"。到 2027 年的预测：

- **Mip-Splatting 思路成为 gsplat / nerfstudio default** — opt-out 而非 opt-in。已有信号：gsplat 0.1.x 版本已默认支持 anti-alias mode，标志业界达成共识。
- **3D filter 与 feed-forward 3DGS 融合** — VGGT / pixelSplat 这类 feed-forward 3D 模型在生成 gaussian 时需要内置 Nyquist 约束；否则 feed-forward 模型继承 vanilla 3DGS 的 aliasing 问题。已有 2025 论文（Mip-LRM UNVERIFIED — 检查具体方案名）在尝试。
- **2D filter 标准化为 ply interchange spec** — 第三方 viewer / web renderer / mobile renderer 需要*都*实现 Mip filter，才能避免 §4.y atlas 提到的 ply 跨 viewer 不一致问题。社区可能推出 "Mip-ply v1" interchange standard。

**Falsifiable prediction:** 到 2027-06，主流 3DGS 教学材料（CVPR tutorial, NeRF/3DGS handbooks）会把 Mip-Splatting 写成 "3DGS standard"，把 vanilla 3DGS 写成 "historical baseline"。如果仍把 vanilla 当 default 介绍，对 prediction 下负注。

**Interview Tip**: 被问 "我的 3DGS demo 训练视角看着完美，靠近一点就 shimmer 是 bug 还是 feature"，正确答案是 *尺度变化下的 aliasing，vanilla 3DGS 对 gaussian size 没有 Nyquist 约束*。修复方法：用 Mip-Splatting (Yu CVPR 2024) — 3D Nyquist filter + 2D scale-aware filter 耦合。陷阱答案是"训练时间不够" / "需要更多 views" — 都不对。

---

## 7 · TRL classification

- **⭐ shipped** — CVPR 2024 Best Student Paper；已被 gsplat / nerfstudio 等主流开源栈吸收为默认抗锯齿路径；autonomousvision 团队仍维护原 repo（虽节奏放慢）。
- **License caveat**：仍继承 INRIA 3DGS 非商业限制（README 明说 "Please follow the license of 3DGS"）；商用路径推荐 `gsplat` (BSD) reimplementation 而非 autonomousvision 原 repo。
- **Maturity stage**：算法稳定（核心机制 2 年无重大改动），工程长尾（rasterizer 重编对 CUDA 版本敏感，issue 多但都是 install/data 层面）；属"研究成熟、工程进入维护期"阶段。

---

## 8 · References

- **Mip-Splatting**（本文主体）— Yu, Chen, Huang, Sattler, Geiger. *CVPR 2024 Best Student Paper.* https://arxiv.org/abs/2311.16493
- **Mip-NeRF**（NeRF 谱系下抗锯齿前身，概念祖父）— Barron et al. *ICCV 2021.* https://arxiv.org/abs/2103.13415
- **Mip-NeRF 360**（多尺度 benchmark 数据集来源）— Barron et al. *CVPR 2022.* https://arxiv.org/abs/2111.12077
- **3DGS original**（被修复的基础工作）— Kerbl et al. *SIGGRAPH 2023.* https://arxiv.org/abs/2308.04079
- **Gaussian Opacity Fields**（Mip-Splatting 后续吸收的 densification 改进）— arXiv 2404.10772

## Boundary

本文是 Mip-Splatting 在抗锯齿语境下的解构。**不**覆盖：

- 3DGS 原版机制详解 → [`3dgs_original_dissection.md`](./3dgs_original_dissection.md)
- Mip-Splatting 的 drone / VR / wrist-cam 部署论述（已在）→ [`mip_splatting.md`](./mip_splatting.md)
- 3DGS 4D 动态扩展 → [`4dgs_dynamic_scenes.md`](./4dgs_dynamic_scenes.md)
- 3DGS as SLAM map → [`gs_slam_dissection.md`](./gs_slam_dissection.md)
- 3DGS 与 NeRF / mesh / voxel 的跨表示对比 → `crossing/representation-migration/`
- Feed-forward 3DGS（pixelSplat / LRM / VGGT-gaussian）替代 per-scene → `foundations/feed-forward-3d/`
- VLA policy 如何消费抗锯齿后的 gaussian 场景 → `bridge-to-vla/feature-cloud-to-action.md`
- 3DGS 谱系完整 GitHub 失败地图 → [`github_failure_atlas.md`](./github_failure_atlas.md)

---

*Created: 2026-05-24. v1.0.*
