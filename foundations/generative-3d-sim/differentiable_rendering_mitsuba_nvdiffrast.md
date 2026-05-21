# 可微渲染基础设施：Mitsuba 3 与 nvdiffrast (Differentiable Rendering Infrastructure: Mitsuba 3 and nvdiffrast)

> **发布时间**：Mitsuba 3 (Jakob et al. 2022, JCGT); nvdiffrast (Laine et al. *SIGGRAPH 2020*, arXiv:2011.03277)
> **核心定位**：差异化渲染是生成式 3D 训练管线的 *enabler* — 它让 gradient 能从像素 loss 流回到几何 / 材质 / 光照参数。**几乎没有人应当自己写一个可微渲染器**；Mitsuba 3 与 nvdiffrast 划分了两条互补的主流路线。

3DGS、NeRF、Splat-Sim、neural texture optimization —— 每个通过渲染出的图像"学"东西的系统都依赖同一套水管：可微的渲染函数 `I = R(scene_params)`，使 `∂L/∂scene_params` 存在。没有这个导数，从像素学场景就塌为暴力搜索。**本文讲的就是这个导数——谁来算、各家偷了什么角、为什么自己写几乎总错。**

### X-Ray (non-expert friendly)

1. **问题。** 传统 rasterizer / 路径追踪把场景描述变成像素—— 但这步*不易*可微。Rasterization 每像素做离散可见性决定；路径追踪采离散光路。梯度在不连续处消失。
2. **技巧。** 两个阵营。Mitsuba 3（物理正确：通过 radiative-backprop / reparameterization 给出光滑的 path 导数估计）。nvdiffrast（图形务实：在轮廓处把离散 rasterization 换成光滑的解析近似）。
3. **为什么空间 AI 读者应当关心。** 调试"我的纹理贴图训不动"或"3DGS-on-mesh 混合不收敛"时，答案几乎都藏在渲染器的梯度里——知道每个库的妥协能省下几周。

### Research Landscape Timeline (X-Ray)

```
  2014─2018 ─ OpenDR, Loubet et al.: first diff rasterizers, brittle
  2019 ───── Mitsuba 2: path-traced auto-diff, physics-correct, slow
  2020.07 ── nvdiffrast (Laine et al. SIGGRAPH): modular rast w/ analytical AA
  2022 ───── Mitsuba 3 (Dr.Jit backend): JIT-compiled gradients, now fast on GPU
  2023.07 ── 3DGS: writes its own custom rasterizer + gradient kernel
                    — does NOT use either library above
  Today ──── mesh inverse rendering: nvdiffrast
              physics-correct light transport: Mitsuba 3
              3DGS-native: that codebase's CUDA kernels
              NeRF: framework volume renderer (instant-ngp, nerfstudio)
```

3DGS 绕开两个库本身就是信息：当表示有自定义渲染公式时，自己写一次梯度，永不再 per-paper 写一次。

---

## 1 · System Overview

### 1.1 The Two Library Families Side by Side

| | Mitsuba 3 | nvdiffrast |
|---|---|---|
| 出处 | TU Wien / EPFL (Jakob), JCGT 2022 | NVIDIA (Laine et al.), SIGGRAPH 2020 |
| 渲染模型 | 路径追踪 Monte Carlo（物理正确光传输） | 模块化 rasterization（rast → interp → texture → AA） |
| 梯度机制 | Dr.Jit JIT 编译 AD；reparameterized 积分；radiative backprop | 解析反走样轮廓；每阶段自定 CUDA |
| 真实度 | 完整 BSDF + 全局光照 + 参与介质 | 直接 shading；GI 自己组合 |
| 典型每步成本 | 秒到分 | 毫秒 |
| 最适用于 | 材质 / 灯光 / SSS / 标定的 inverse rendering | mesh inverse rendering、纹理优化、NeRF-mesh 混合、大批训练 |
| API | Python；声明式场景 | PyTorch；函数式 op |
| GPU 支持 | CUDA + 通过 Dr.Jit 的 LLVM CPU | 仅 CUDA |

### 1.2 Key Mechanism

⚡ **Eureka Moment**：*离散可见性杀梯度；把不连续 reparameterize 成光滑积分（Mitsuba 路径）或解析计算边缘梯度（nvdiffrast 路径）才是技巧。在"物理正确"与"毫秒吞吐"之间的选择就是两库的选择。*

不连续问题一行：场景参数微动 `dθ` 可把三角形边移过一个像素边界，使该像素颜色一步翻转——这是非光滑函数，朴素梯度几乎处处为零或无穷。

### 1.3 Pipeline Flow

```
  scene params θ (mesh verts, textures, light, ...)
       ↓
  DIFFERENTIABLE RENDERER
    Mitsuba 3: path-trace + reparam edges → ∂I/∂θ via Dr.Jit AD
    nvdiffrast: rasterize → interp → texture → analytical-AA → ∂I/∂θ via custom kernels
       ↓
  pixels I = R(θ) → L = ||I - I_target||
       ↓
  ∂L/∂I → ∂L/∂θ (chain rule) → SGD / Adam update
```

---

## 2 · Math Core: Why Naive Gradients Fail

📌 **Napkin Formula**：
```
  ∂I(p) / ∂θ = (smooth interior term)   ← easy by autodiff
              + (boundary term over silhouettes) ← hard
```
光滑内部项就是 shading 导数。**边界项才是不连续藏身之处，也是两库不同解法之所在。**

- **Mitsuba 3（reparameterization）**：把渲染积分重写到积分域*光滑*依赖于 `θ`；边界项的梯度变成 Monte Carlo 能估计的常规积分。物理正确。慢。
- **nvdiffrast（解析边缘 AA）**：在每个被三角形 silhouette 触及的像素处，通过边方程算一个解析反走样覆盖梯度。把边界项近似为 per-edge 函数。快。在遮挡透明 / 全局光照下不物理正确。

> 变量：`I(p)` 像素 `p` 处的强度；`θ` 场景参数；silhouette = 投影边，某三角形在该像素覆盖 / 取消覆盖处。

抽象上没有"更正确"——它们答不同的问题。Mitsuba："光子传输精确的梯度是什么？"nvdiffrast："让 mesh + 纹理优化收敛的最便宜梯度是什么？"

---

## 3 · Worked Example: Train a Texture Map from One Image (nvdiffrast)

玩具问题：给一只茶壶的已知 3D mesh 与一张目标照片，恢复纹理贴图。

1. **初始化 1024×1024 纹理贴图**为灰（`θ = 0.5`）。
2. **前向**（nvdiffrast）：
   - `rasterize(verts, tris, res=(512,512))` → 每像素三角形 ID + 重心
   - `interpolate(uvs, rast, tris)` → 每像素 UV
   - `texture(tex_map, uv)` → 每像素 RGB
   - `antialias(rgb, rast, verts, tris)` → 最终平滑图像
3. **Loss**：`L = mean((I_render - I_target)^2)`。
4. **后向**：PyTorch autograd 沿每个 nvdiffrast op 把梯度回传到 `tex_map`。
5. **更新**：`tex_map -= lr * tex_map.grad`。迭代约 1000 步。单 GPU 几分钟收敛。

整个脚本约 50 行 PyTorch。**之所以可行**，是 nvdiffrast 的解析边缘 AA 在 silhouette 移动的像素处也给非零梯度，所以优化器能学*边缘附近*的纹理内容（朴素 rasterizer 会把它藏起来）。同一问题在 Mitsuba 3 上每步更慢，但产生*物理意义上有意义*的梯度——后者能撑过例如茶壶到桌面的互反射，nvdiffrast 给不到干净。

---

## 4 · Engineering View

| Concern | Mitsuba 3 | nvdiffrast |
|---|---|---|
| 每场景内存 | 高 —— path tracer + BVH + light tree | 低 —— 仅 mesh + 纹理 |
| 适合批训练 | 痛苦 —— 每步慢 | 自然 —— 训练循环速 |
| 标定用例 | 极好（BRDF 拟、灯光估计） | 中（无 GI） |
| Mesh deformation / Marching Tets | 可 | 可（标准用法） |
| NeRF / 体积积分 | 支持体积路径追踪 | 非其职责 |
| 3DGS / 点云渲染 | 非原生 | 非原生 —— 3DGS 自带 CUDA |
| 调试 —— 梯度正确性 | 参考级 | 薄 silhouette 需小心 |

务实规则：**若 loss 是"把这张渲染图匹配到这张照片，仅 mesh + 纹理"→ nvdiffrast。若 loss 涉及光传输、折射介质、BSDF 估计 → Mitsuba 3。若表示是 gaussian 或学到的体积场 → 用该框架原生 renderer。**

---

## 5 · Data & Eval Conventions

这些库是基础设施而非模型 —— 没有它们自己的 benchmark。**质量证据来自下游论文**：mesh + 纹理学习（Nvdiffrec, Munkberg et al. CVPR 2022）用 nvdiffrast 并报告 PSNR / 几何误差；BSDF 恢复 / relighting 用 Mitsuba 3。

警惕那些*ad hoc 重实现*可微渲染的论文 —— 它们几乎总有 silhouette 梯度 bug，作者没注意到是因为他们测试场景的 loss landscape 恰好光滑。

---

## 6 · Capabilities & Failure Modes

**Mitsuba 3 works for**：从照片恢复 BSDF / 材质；可微相机内参标定；逆向光传输；含参与介质的体积路径追踪。

**Mitsuba 3 struggles with**：高吞吐训练（每步数秒）；超大 mesh；实时 inverse 问题。

**nvdiffrast works for**：从图像求 mesh shape（Nvdiffrec）；纹理 / SH 光照优化；可微 mesh-NeRF 混合；任何只需直接 shading 的事。

**nvdiffrast struggles with**：全局光照；折射 / 透明多界面物体；体积散射；含糊的 silhouette 遮挡顺序。

### 6.1 Hidden Assumptions

1. **底层表示在相关变量上必须可微。** 纯三角网格在顶点*数*上没有光滑导数；你优化固定拓扑下顶点位置。改拓扑需要 remesher（DMTet、FlexiCubes）叠上去。
2. **Rasterization 本身不天然可微。** 两个库都在 silhouette 处*替换* rasterization 规则为光滑近似。期望意义上正确，但引入用户必须留意的方差。
3. **反走样很关键。** nvdiffrast 的 silhouette 正确性取决于内置 `antialias()`；跳过它得到的渲染器"能编译能跑"，但边缘梯度为零、静默学不到形状。
4. **UV 参数化已给定。** 两库都假设 mesh 输入已有 UV map；联合优化拓扑*与* UV 是另一个开放问题。
5. **GPU 内存看场景。** Mitsuba 路径追踪在复杂 BSDF 上方差受限——"loss 不降"可能意味着"每像素采样从 32 抬到 256"。
6. **你不该自己写。** 每篇从零重实现可微渲染的论文都以静默 silhouette bug 结束。这些库存在*正是因为*这事难。

---

## 7 · Comparison & Interview Tip

| Library | Pick when |
|---|---|
| Mitsuba 3 | 物理正确光传输、BSDF / 材质恢复、离线标定 |
| nvdiffrast | mesh / 纹理 / 直接 shading 优化，训练循环吞吐 |
| 3DGS 自带 kernel | 表示是 gaussian；别多叠一层 |
| nerfstudio / instant-ngp | 表示是体积神经场 |
| **自己写** | 几乎永远不；除非显式在发表可微渲染本身 |

🎯 **Interview Tip**：被问 *"你会自己写可微渲染器吗？"*，别答"会，为了控制"。答：**"几乎永远不。Mitsuba 3 占物理正确路径追踪梯度；nvdiffrast 占高吞吐 rasterization 梯度；表示特定框架（3DGS、nerfstudio）占自己那块。从零写只在显式发表可微渲染本身时合理 —— 其它情况都是静默 silhouette 梯度 bug 在等你。"**

---

## Boundary

per-method 3DGS rasterizer 内部 → `foundations/3dgs-family/3dgs_original_dissection.md`。per-method NeRF 数学 → `foundations/nerf-family/`。用例（manipulation Splat-Sim、drone Aerial Gym）→ `foundations/generative-3d-sim/` 的姊妹文。推理时 world model → `foundations/world-model/`。

## References

- Jakob et al., *Mitsuba 3: Inverse-Rendering Engine*, Journal of Computer Graphics Techniques (2022). https://mitsuba.readthedocs.io/
- Laine et al., *Modular Primitives for High-Performance Differentiable Rendering*, SIGGRAPH 2020. arXiv:2011.03277. https://nvlabs.github.io/nvdiffrast/
- Munkberg et al., *Extracting Triangular 3D Models, Materials, and Lighting From Images (Nvdiffrec)*, CVPR 2022. arXiv:2111.12503.
- Loubet et al., *Reparameterizing Discontinuous Integrands for Differentiable Rendering*, ACM TOG 2019.

---

**Status:** v1 (2026-05-21). UNVERIFIED policy applies to all timing / convergence numbers.

[← Back to Generative 3D Sim](./README.md)
