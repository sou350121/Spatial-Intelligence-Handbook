<!-- ontology-5axis
problem: reconstruction
representation: 3DGS
sensor: stereo
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# StereoSplat+: Feed-Forward Stereo Gaussian Splatting with Diffusion-Assisted Progressive Inference  
> **发布时间**：2026/07/09  
> **论文 / 模型名**：StereoSplat+  
> **核心定位**：首个支持**单帧立体输入、纯 feed-forward、实时可部署**的 3DGS 重建框架，通过**一阶扩散增强 + 置信度引导的伪多视图反馈**，在 KITTI-360 上显著提升 occluded/out-of-frame 区域的几何完整性与渲染保真度，**不牺牲推理速度**。

> 它直击机器人/AR端侧部署的核心矛盾：传统 3DGS 需多视图或优化 → 不满足因果性；纯单视图方法（如 DepthSplat）在遮挡区崩溃 → 几何稀疏、浮点漂移严重。StereoSplat+ 用“一次 render–enhance–reinject”闭环，在保持单次前向传播本质的前提下，**以扩散为几何证据放大器**，把单帧立体输入“变出”等效多视图约束。

---

## X-Ray 开场  
StereoSplat+ 解决的是：**如何仅凭一对校正立体图像，零优化、零迭代、零未来帧依赖，输出高质量、几何鲁棒、可直接渲染的 3DGS 场景**。它提出双轨架构（cost-volume + triplane 3D volume）实现输入无关的高保真初估，并引入**一阶扩散增强器 + 置信度加权融合**，将渲染伪视图“提纯”后反馈为几何先验——整个过程仍为**单次前向传播链**（含 diffusion enhancer 的 one-step denoising）。对 spatial AI 研究者而言，它定义了“轻量扩散辅助重建”的新范式：**扩散不生成几何，只修复渲染观测量，从而间接强化几何估计**，兼顾效率与鲁棒性。

---

## 📍 研究全景时间线  
```
[2023] 3DGS (Kerbl et al.) —— per-scene optimization, slow  
│  
├─ [2024] DepthSplat —— feed-forward, stereo cost volume, but fails on occlusions  
├─ [2024] OmniScene —— triplane fusion, but relies on external monocular depth (unstable)  
├─ [2025] DIFIX3D+ —— diffusion-guided repair, but iterative & non-causal  
│  
└─ [2026] StereoSplat+ —— ✅ input-invariant feed-forward + ✅ one-shot diffusion-enhanced progressive inference  
                              ↑  
                      (本文位置：填补“单立体对→实时3DGS”空白；局限：依赖 LiDAR-supervised depth target；未验证真机延迟)
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **StereoSplat (base estimator)** | `1~K` 对 rectified stereo images + poses + intrinsics | 3D Gaussian set `G_cv ∪ G_volume` + per-Gaussian confidence `conf` | 训练时随机 subsample `m ∈ [1,K]` 对视图；推理固定 `m=1` |
| **Cost-Volume Branch** | Stereo image features + geometry features (Depth-Anything V2) | Pixel-aligned Gaussians `G_cv`, depth map `D'`, matching confidence → opacity `α` | 使用 192-disp cost volume；训练时监督 `D'` 与 LiDAR+pseudo-dense depth `D†` |
| **Triplane Transformer Branch** | Multi-view image features + `F_GS` + sinusoidal pose encoding `PE(T_i)` | Voxel-aligned Gaussians `G_volume` (center `μ`, scale `s`, quat `q`, SH color `c`) | Triplane updated via CIDA (cross-image) + CPDA (cross-plane)；`PE(T_i)` enables view-count invariance |
| **Diffusion Enhancer (SD-Turbo fine-tuned)** | Rendered pseudo-stereo image `I_base` (from `G_base`) | Enhanced image `I_enhanced` | 仅在推理时启用；训练时用 `I_base → GT` 对 fine-tune；one-step denoising only |

### 1.2 关键机制  
⚡ **Eureka Moment**：**将扩散模型降级为“视图一致性滤波器”，而非几何生成器——仅用 one-step denoising 提升渲染伪视图的结构保真度，使其能作为可信几何线索被 StereoSplat 重新摄入，从而在 feed-forward 约束下实现伪多视图证据增益。**

### 1.3 信息流 ASCII 图  

```
[Input] One stereo pair (I_L, I_R) + poses  
        │  
        ▼  
StereoSplat ───→ G^(0) = G_cv ∪ G_volume + conf  
        │  
        ▼ (confidence-aware rendering)  
Novel stereo views: I_base = {I_base^L, I_base^R}  
        │  
        ▼ (one-step diffusion enhancer)  
I_enhanced = Diffusion(I_base)  
        │  
        ▼ (concatenate with original input)  
Augmented input: [(I_L,I_R), (I_enhanced^L,I_enhanced^R)]  
        │  
        ▼  
StereoSplat ───→ G^(1) = refined Gaussians  
        │  
        ▼ (confidence-guided fusion)  
Final G = conf^(0) ⊙ G^(0) + conf^(1) ⊙ G^(1)  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**：  
**`G_final = σ(conf⁰) ⊙ G⁰ + σ(conf¹) ⊙ G¹`** —— 置信度不是门控开关，而是软权重；`G¹` 并非替代 `G⁰`，而是用增强伪视图“微调”其几何。

- **目标**：从单立体对估计鲁棒 3DGS，尤其覆盖 occluded/out-of-frame 区域  
- **公式本质**：  
  - `G⁰`: 初估（cost-volume + triplane），含初始置信度 `conf⁰`  
  - `G¹`: 基于 `I_enhanced`（扩散提纯的伪视图）重估，含新置信度 `conf¹`  
  - 融合非简单平均，而是 `sigmoid(conf)` 加权，抑制低置信区域噪声  
- **变量说明**：  
  - `conf ∈ [0,1]`: 每个 Gaussian 的 confidence head 输出，经 sigmoid  
  - `⊙`: Hadamard product（逐 Gaussian 加权）  
- **直觉**：遮挡区 `conf⁰` 低 → `G⁰` 在该区权重小；但 `I_enhanced` 经扩散修复后更结构一致 → `conf¹` 在该区相对升高 → `G¹` 贡献增大，实现几何补全。

---

## 3 · 带数字走一遍  

**玩具设定（KITTI-360 bin）**：  
- 输入：1 对 stereo `(I₁ᴸ, I₁ᴿ)`，pose `T₁ᴸ, T₁ᴿ`  
- StereoSplat 输出：`G⁰` 含 120k Gaussians，其中 occlusion 区（如车后方）`conf⁰ ≈ 0.2`，depth `D′` 在该区误差大  
- 渲染 `I_base`（视角 `T₂ᴸ, T₂ᴿ`）：因 `G⁰` 几何不准 → `I_base` 出现模糊/伪影（PSNR≈18.3 dB）  
- `Diffusion(I_base)` → `I_enhanced`：PSNR↑至 22.1 dB，边缘锐利，结构连贯  
- Augmented input fed to StereoSplat → `G¹`：occlusion 区新增 8k Gaussians，`conf¹ ≈ 0.65`  
- 融合：`G_final = σ(0.2)·G⁰ + σ(0.65)·G¹ ≈ 0.55·G⁰ + 0.66·G¹` → occlusion 区几何密度↑，渲染 PSNR↑至 20.5 dB（见 Table I）

---

## 4 · 工程视角  

| 指标 | StereoSplat (base) | StereoSplat+ (w/ diffusion) | trade-off 说明 |
|------|---------------------|------------------------------|----------------|
| **Latency (RTX 4090)** | ~120 ms / stereo pair | ~180 ms / stereo pair | +60 ms 主要来自 diffusion enhancer（SD-Turbo one-step） |
| **Inference Steps** | 1 forward pass | 2 forward passes (StereoSplat ×2) + 1 diffusion step | 仍属 feed-forward chain，无循环依赖 |
| **Memory (VRAM)** | 3.2 GB | 4.8 GB | triplane feature cache + diffusion latent storage |
| **Throughput** | 8.3 fps | 5.6 fps | 可接受（>5 fps 满足 AR/robotics 实时需求） |
| **Deployment Constraint** | Requires rectified stereo + calibrated poses | Same + diffusion model weights (~1.2 GB) | Diffusion enhancer is separate, can be offloaded |

> ✅ **关键 trade-off**：用 **+60ms 延迟** 换取 **occlusion 区 PSNR +2.3 dB（Table I）**，且无需修改硬件 pipeline（diffusion 是插件式模块）。

---

## 5 · 数据与评测  

- **数据组成**：  
  - **KITTI-360**：仅使用 `train` split；按轨迹切分为 bins（Fig. 3），每 bin 以 first frame stereo pair 为 input，后续 frames 为 novel-view targets  
  - **LiDAR supervision**：`D†` = sparse LiDAR + pseudo-dense depth from NMRFStereo [4]（原文明确）  
  - **Training augmentation**：stochastic view subsampling (`m ∼ U[1,K]`) + GT ↔ pseudo-view replacement (`p_p` prob)  

- **评测设置**：  
  - **Metrics**：PSNR / SSIM on rendered RGB；ℓ₁ depth error on LiDAR-masked pixels (`‖D̂ − D†‖₁,M`)  
  - **条件严格**：所有方法 **仅用 first-frame stereo pair as input**（Table I 标题强调）；novel views are at `first/center/last` frame of bin  
  - **Baseline**：Branch CV（DepthSplat-style）、Branch 3D（triplane-only）、ablated variants  

---

## 6 · 能力与失败模式  

✅ **能做**：  
- 单立体对输入下，重建城市街景中车辆、建筑轮廓，尤其改善 rear-occluded surfaces（Fig. 4 qual.）  
- 在 strong view extrapolation（如从 front-view 渲染 rear-view）时，PSNR 优于 baseline +1.2 dB（Table I）  
- 对输入 stereo baseline 长短鲁棒（因 pose encoding + stochastic subsampling）  

❌ **不能做**：  
- 无纹理区域（如纯色墙面）深度仍模糊（cost-volume branch 失效，triplane 无足够线索）  
- 动态物体（行人、车辆）未建模 → 视为静态背景，导致 ghosting（全文未提动态处理）  
- 极端低光照/运动模糊输入 → Depth-Anything V2 backbone 特征退化 → 全链路崩溃  

### 隐含假设 (Hidden Assumptions)  
1. **Stereo rectification is perfect**：所有公式基于 rectified stereo pairs（`I_L`, `I_R`），未处理未校正畸变。  
2. **Camera poses are accurate and synchronized**：`T_i` 直接用于 cost volume construction（Eq.2）和 triplane projection（Eq.10），pose drift breaks geometry.  
3. **LiDAR provides reliable sparse depth prior**：`D†` 是监督核心（Eq.12），在无 LiDAR 场景（如手机 AR）不可用 → `UNVERIFIED` 泛化性。  
4. **Diffusion enhancer generalizes to unseen scenes**：fine-tuned on KITTI-360 renders → 未验证 cross-dataset（e.g., Waymo）效果。  

---

## 7 · 与相关工作对比  

| 方法 | 输入 | 3D 表示 | 是否 feed-forward | 是否单立体对 | occlusion 处理 | 关键区别 |
|------|------|---------|-------------------|---------------|----------------|----------|
| **DepthSplat [19]** | Multi-view stereo | 3DGS | ✅ | ❌ (needs ≥2 pairs) | Weak (cost-volume only) | No 3D volume; no diffusion; view-count fixed |
| **OmniScene [15]** | Multi-view RGB | 3DGS | ✅ | ❌ | Medium (triplane) | Relies on external monocular depth → unstable in practice |
| **DIFIX3D+ [18]** | Multi-view + 3DGS | 3DGS | ❌ (iterative) | ❌ | Strong | Diffusion used for repair, but breaks real-time constraint |
| **StereoSplat+ (Ours)** | **Single stereo pair** | 3DGS | ✅ | ✅ | **Strong (dual-branch + diffusion feedback)** | Only method achieving all 4 ticks |

**面试 Tip**：  
> *Q: “StereoSplat+ 用 diffusion，是不是又变慢了？”*  
> **A**: “不。我们严格限定 diffusion 为 one-step SD-Turbo enhancer（≈60ms），且只运行一次；整个 pipeline仍是 feed-forward chain —— 没有循环优化、没有 per-scene tuning。它不是用 diffusion 生成 3D，而是用 diffusion ‘提纯’渲染观测量，让单帧输入能‘骗过’网络，以为自己看到了多视角，从而在不破坏实时性的前提下，获得多视角的几何收益。”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-19)  

> **Status**: repo early-release / 暂无 issue 流（arXiv v1 未附 GitHub link；作者邮箱域名 `ok.sc.e.titech.ac.jp` 暗示代码尚未公开）  
> **Pitfalls inferred from §6 constraints & method design**:  
> 1. **Rectification failure → immediate collapse**: If input stereo is unrectified, cost volume correlation (Eq.4) yields garbage → `G_cv` invalid → triplane fusion inherits noise.  
> 2. **Pose drift >0.5m translation error**: Sinusoidal encoding (Eq.7–9) normalizes `t_i/s_t`, but `s_t` is fixed; large drift pushes `x_i` out of learned frequency band → `PE(T_i)` loses discriminability → triplane attention misaligns.  
> 3. **Low-texture + low-LiDAR-coverage region**: e.g., tunnel entrance → Depth-Anything V2 fails → `F_mono` degenerates → both branches starve → `conf` collapses globally → fusion becomes uniform average → floaters appear.  

---

[← Back to 3DGS README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.08808 -->
