<!-- ontology-5axis
problem: navigation
representation: implicit-sdf
sensor: n/a
paradigm: generative
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->

# Function-Space Diffusion for Motion Planning (FSD-MP)  
> **发布时间**：2026/07/03  
> **论文 / 模型名**：FSD-MP (Function-Space Diffusion for Motion Planning)  
> **核心定位**：首个在**函数空间（而非离散点序列）执行扩散建模的运动规划器**，实现**零样本跨分辨率泛化（最高16×）**，解决传统扩散规划器因固定长度 waypoint 表征导致的 discretization-dependence 痛点。

传统扩散运动规划器（如 MPD）把轨迹硬编码为 N 个固定时间戳的关节角/位姿向量，模型一旦训练完成就锁死在该分辨率——换更密采样就得重训。FSD-MP 彻底跳出“向量空间”，将轨迹建模为连续函数 $x(\tau):[0,1]\to\mathbb{R}^d$，并在其 Hilbert 空间 $L^2([0,1],\mathbb{R}^d)$ 上定义扩散过程，使同一模型可原生输出任意分辨率轨迹，且多模态结构与碰撞可行性在超分后保持一致。

---

## X-Ray 开场  
FSD-MP 解决的是**扩散式运动规划中的分辨率刚性瓶颈**：现有方法把轨迹当向量处理，导致模型无法脱离训练分辨率工作。它提出将轨迹视为函数，在谱域（spectral domain）定义模式级（mode-wise）前向扩散，并用边界兼容的 DST-FNO 架构实现反向去噪——**不是“插值后处理”，而是从建模源头消除离散化耦合**。对 spatial AI 研究者而言，这是将 infinite-dimensional generative modeling 首次系统性引入机器人运动规划，为 trajectory representation 提供了新的数学范式锚点。

---

## 📍 研究全景时间线  
```
2022: Diffuser [10] —— 首个 diffusion-based motion planner (fixed-length waypoints)  
2023: MPD [3] —— 任务条件化 + collision guidance, 仍绑定 resolution  
2024: MPD-Spline [4] —— spline post-processing for resolution flexibility (ad-hoc fix)  
2025: Function-space diffusion in PDEs [18,24] —— theory for trace-class noise in ℋ  
2026: FSD-MP [this] —— ✅ first function-space diffusion planner with zero-shot 16× super-res  
          └── LIMITATION: assumes smooth trajectories (Matérn prior), no dynamic obstacle handling
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **Zero-End Projection** | raw trajectory $x_0(\tau)$, start/goal $(q_s,q_g)$ | residual $\tilde{x}_0(\tau) = x_0(\tau) - (1-\tau)q_s - \tau q_g$ | **训练时强制应用**；推理时仅用于重建，不参与采样 |
| **Mode-wise Forward Diffusion** | $\tilde{x}_0$, time $t$, Matérn covariance $\mathcal{C}$ | noisy residual $\tilde{x}_t$ in coefficient space $\{\tilde{X}_t^k\}$ | **训练目标**：预测谱噪声 $\xi^k$；**推理无此模块**（预计算 $\alpha_k(t),\sigma_k(t)$） |
| **DST-FNO (Reverse)** | $\tilde{x}_t$, $t$, $(q_s,q_g,\text{emb}(t))$ | noise estimate $\xi_\theta^k(\tilde{x}_t,t,q_s,q_g)$ per mode | **唯一可学习模块**；FiLM conditioning enables endpoint-aware denoising without breaking zero-boundary constraint |
| **Guided Sampling (DDIM)** | $\tilde{x}_t$, $\xi_\theta$, collision cost $C(x)$ | next-step $\tilde{x}_s$ with obstacle avoidance | **推理专属**；guidance applied in spectral domain via $\mathcal{F}^{-1}\mathcal{C}\,g$ preconditioning |

### 1.2 关键机制  
⚡ Eureka Moment：**用 Discrete Sine Transform (DST) 替代 FFT 构建 boundary-compatible neural operator，使谱基 $\phi_k(\tau)=\sin(k\pi\tau)$ 天然满足 $\phi_k(0)=\phi_k(1)=0$，从而在任意分辨率下严格保持 zero-end projection 的约束结构**。

### 1.3 信息流 ASCII 图  

```
[Start/Goal q_s,q_g]  
       ↓  
┌───────────────────────┐  
│ Zero-End Projection   │ → x̃₀(τ) ∈ {x̃ | x̃(0)=x̃(1)=0}  
└───────────────────────┘  
       ↓  
┌───────────────────────────────────────┐  
│ Mode-wise Forward Diffusion (Spectral) │  
│ X̃ₜᵏ = √αₖ(t)·X̃₀ᵏ + √(1−αₖ(t))·ξᵏ     │  
└───────────────────────────────────────┘  
       ↓  
┌───────────────────────────────────────────────────────┐  
│ DST-FNO w/ FiLM: ξ_θᵏ(x̃ₜ,t,q_s,q_g) ← learns mapping   │  
│ from function space ℋ to spectral noise coefficients    │  
└───────────────────────────────────────────────────────┘  
       ↓  
┌───────────────────────────────────────────────────────────────────────┐  
│ Guided DDIM Sampling:                                                   │  
│ 1. Estimate clean coeff: X̃̂₀ᵏ = (X̃ₜᵏ − √(1−αₖ)·ξ_θᵏ)/√αₖ              │  
│ 2. DDIM step: X̃ₛᵏ = √αₛ·X̃̂₀ᵏ + √(1−αₛ)·[√(1−η²)·ξ_θᵏ + η·zᵏ]         │  
│ 3. Guidance: g = −∇_{μ̃ₛ} C(x̂₀), then x̃ₛ ∼ 𝒩(μ̃ₛ + ℱ⁻¹𝒞·g, η²ℱ⁻¹𝒞)   │  
└───────────────────────────────────────────────────────────────────────┘  
       ↓  
x̃₀(τ) → x₀(τ) = x̃₀(τ) + (1−τ)q_s + τ q_g  // exact endpoint enforcement  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**:  
> *FSD-MP’s forward process is a spectral decomposition of trajectory functions under Matérn covariance, where each Fourier mode $k$ diffuses at rate $\lambda_k$ and noise amplitude $\mu_k$, enabling resolution-agnostic training via DST.*

**目标**：学习函数空间 $\mathcal{H}=L^2([0,1],\mathbb{R}^d)$ 上的轨迹分布 $p(x|\mathcal{O})$，其中 $\mathcal{O}$ 为障碍物约束。

**公式**（关键前向过程）：  
$$
\tilde{X}_t^k = \sqrt{\alpha_k(t)}\,\tilde{X}_0^k + \sqrt{1-\alpha_k(t)}\,\xi^k, \quad 
\xi^k \sim \mathcal{N}\left(0,\frac{\mu_k^2}{\lambda_k}\right)
$$  
其中 $\alpha_k(t) = \exp\left(-\lambda_k \int_0^t \beta(s)\,ds\right)$，$\lambda_k,\mu_k$ 来自 Matérn covariance $\mathcal{C}=\sigma^2(-\Delta+\kappa^2\mathcal{I})^{-\alpha}$ 的特征值。

**变量说明**：  
- $\tilde{X}_0^k$: zero-end projected trajectory 在第 $k$ 个 DST 模式上的系数  
- $\xi^k$: trace-class Gaussian noise coefficient (Matérn-smoothed)  
- $\lambda_k$: drift eigenvalue — controls diffusion speed per mode (higher $k$ → faster decay)  
- $\mu_k$: diffusion eigenvalue — sets noise scale per mode (Matérn ensures $\sum_k \mu_k^2/\lambda_k < \infty$)

**直觉**：  
- 高频模式（大 $k$）对应轨迹局部细节，$\lambda_k$ 增长快 → 快速被噪声淹没 → 模型聚焦低频全局结构  
- Matérn covariance ($\alpha>1/2$) guarantees trace-classness → valid infinite-dimensional Gaussian measure  
- DST basis $\sin(k\pi\tau)$ enforces zero endpoints *by construction* → no post-hoc clamping needed

---

## 3 · 带数字走一遍  

**玩具设定**（2D point robot, $d=2$）：  
- Training resolution: $N=32$ points on $[0,1]$  
- Target super-res: $N'=512$ points (16×)  
- Trajectory: straight line $x_0(\tau) = (0,0) + \tau\cdot(1,1)$ → $q_s=(0,0), q_g=(1,1)$  
- Zero-end projection: $\tilde{x}_0(\tau) = x_0(\tau) - (1-\tau)(0,0) - \tau(1,1) = \mathbf{0}$ → all coefficients $\tilde{X}_0^k=0$  
- At $t=0.5$: $\alpha_k(0.5)=e^{-\lambda_k \cdot 0.5}$, assume $\lambda_k = k^2$ → $\alpha_1=0.606$, $\alpha_{10}=e^{-50}\approx 0$  
- So $\tilde{X}_{0.5}^1 \approx \sqrt{0.606}\cdot 0 + \sqrt{0.394}\cdot \xi^1$, while $\tilde{X}_{0.5}^{10} \approx \xi^{10}$ (fully noisy)  
- DST-FNO predicts $\xi_\theta^k$; at inference, DDIM recovers $\tilde{X}_0^k$ → inverse DST gives $\tilde{x}_0(\tau)$ on 512-point grid → add affine term → $x_0(\tau)$ exactly hits $(0,0)$ and $(1,1)$.

✅ 关键：**无需重新训练，DST basis works natively at 512 points because $\sin(k\pi\tau)$ is defined for any $\tau\in[0,1]$**。

---

## 4 · 工程视角  

| 维度 | 值 | 依据 / 备注 |
|------|----|-------------|
| **Latency per sample** | 「论文未报告」 | 全文未给出 FPS / ms / hardware |
| **Memory (VRAM)** | 「论文未报告」 | 未提及 batch size / model size / GPU memory |
| **Steps to convergence** | $M=50$ (DDIM steps) | Sec IV-D: “Sampling sequence $T=t_1>\dots>t_M=0$” + Experiments use $M=50$ (implied by MPD baseline setup) |
| **Throughput** | 「论文未报告」 | 无吞吐量或并行采样指标 |
| **Deployment constraints** | Requires DST/IDST ops + spectral kernel $R\in\mathbb{R}^{K\times c\times c}$ | No FFT → avoids periodic artifacts; but DST not always hardware-accelerated (vs cuFFT); $K$ cutoff must be chosen (Sec V-A: “first $K=32$ modes retained”) |

---

## 5 · 数据与评测  

| 项目 | 内容 | 来源验证 |
|------|------|----------|
| **Environments** | Simple2D, Dense2D (2D point robot), Spheres3D, Warehouse (7-DoF Franka) | Sec V-A: “four environments covering 2D point robot and 3D manipulator planning” + Fig. 2 labels |
| **Training data source** | RRTConnect + GPMP refinement pipeline | Sec V-A: “generate an expert dataset using the same pipeline as MPD” → MPD [3] uses RRTConnect+GPMP |
| **Unseen obstacle test** | Red obstacles added *only at inference time* (Fig. 2 caption) | Sec V-A: “red obstacles are introduced only at inference time to evaluate generalization to unseen obstacles” |
| **Metrics** | Success Rate, Collision Rate, Path Length, Diversity (via MMD) | Sec V-A: “Metrics” subsection lists these four; values not reported in excerpt |
| **Resolution generalization test** | Trained at base res, evaluated at up to **16× higher resolution** | Abstract: “generalizes zero-shot across resolutions up to 16× higher” |

---

## 6 · 能力与失败模式  

✅ **能做**：  
- Zero-shot super-resolution (2×, 4×, 8×, 16×) while preserving multimodality & feasibility  
- Exact endpoint enforcement *without clamping or iterative correction*  
- Collision avoidance via classifier guidance on predicted clean trajectory $\hat{x}_0$ (not noisy $x_t$)  

❌ **不能做**：  
- Handle **dynamic obstacles** (no temporal modeling; assumes static $\mathcal{O}$)  
- Guarantee **asymptotic optimality** (like sampling-based planners) — it’s a learned prior, not completeness-guaranteed  
- Scale to **>100-DoF systems** — computational cost of DST-FNO grows with $K$ (retained modes) and $c$ (channels); no ablation on high-DoF  

### 隐含假设 (Hidden Assumptions)  
- **Trajectories are Matérn-smooth**: Prior assumes $\mathcal{C}=\sigma^2(-\Delta+\kappa^2\mathcal{I})^{-\alpha}$ with $\alpha>1/2$ → excludes discontinuous motions (e.g., impact events, abrupt stops)  
- **Obstacle geometry is differentiable**: Collision cost $C(x)$ must be differentiable for gradient-based guidance (Sec IV-D) → fails with pixel-perfect binary occupancy maps lacking gradient signal  
- **Start/goal configurations are noise-free**: Zero-end projection (Eq.14) assumes exact $q_s,q_g$; noisy observations break exact endpoint satisfaction  

---

## 7 · 与相关工作对比  

| 方法 | 表征 | 分辨率泛化 | Endpoint enforcement | Collision guidance |  
|------|------|-------------|------------------------|----------------------|  
| **MPD [3]** | Fixed-length waypoints $\in\mathbb{R}^{N\times d}$ | ❌ None (retrain required) | Inpainting (post-hoc clamp) | On $x_t$ (noisy sample) |  
| **MPD-Spline [4]** | Waypoints + B-spline interpolation | ⚠️ Post-hoc (spline fitting) | Via spline boundary conditions | Same as MPD |  
| **FSD-MP (ours)** | Continuous function $x(\tau)\in L^2$ | ✅ Zero-shot up to 16× | Exact via affine reconstruction (Eq.15) | On $\hat{x}_0$ (clean prediction) |  

**面试 Tip**：  
> *“如果被问‘FSD-MP 和 MPD-Spline 的本质区别是什么？’ —— 回答：MPD-Spline 是工程修补（post-hoc interpolation），而 FSD-MP 是范式重构（function-space modeling）。前者在向量空间里‘猜’高分辨率点，后者在函数空间里‘定义’高分辨率解——就像用矢量图 vs 位图放大，一个保真，一个模糊。”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-08-02)  

**官方 repo 未在论文中给出**（全文无 `github.com` 链接；arXiv PDF 中无 clickable hyperlink）  
→ 以下 pitfall 由 §6 失败模式推导（未经 issue 验证）：

1. **Pitfall #1**: 使用 binary occupancy map 作为 collision cost $C(x)$ 导致 guidance 失效  
   - *Derivation*: §6 隐含假设要求 $C(x)$ differentiable → binary map has zero gradient almost everywhere → $\boldsymbol{g}=\mathbf{0}$ → no obstacle avoidance  
   - *Method constraint*: Guidance relies on $\nabla_{\mu_s} C(\hat{x}_0)$ (Eq.23); non-diff. $C$ breaks Eq.24  

2. **Pitfall #2**: 在训练数据未覆盖的 sharp corner geometry 上生成轨迹出现 endpoint drift  
   - *Derivation*: §6 隐含假设 “trajectories are Matérn-smooth” → corners violate $\alpha$-Hölder continuity → DST basis poorly approximates discontinuous derivatives → residual $\tilde{x}_0$ reconstruction error accumulates near boundaries  
   - *Method constraint*: Zero-end projection + DST assumes $C^2$ regularity; sharp features force high-$k$ modes → truncation at $K=32$ (Sec V-A) loses fidelity  

3. **Pitfall #3**: ONNX export fails due to dynamic DST/IDST shape dependence  
   - *Derivation*: §4 notes “DST not always hardware-accelerated”; ONNX opset lacks native DST → exporter falls back to loop-based implementation → shape-dependent control flow violates static graph requirement  
   - *Method constraint*: DST-FNO (Eq.18) uses $\mathcal{S},\mathcal{S}^{-1}$ whose output size = input size → but ONNX requires fixed tensor dims unless using `DynamicQuantizeLinear`-style workarounds (not mentioned in paper)  

---

[← Back to navigation README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.02977 -->
