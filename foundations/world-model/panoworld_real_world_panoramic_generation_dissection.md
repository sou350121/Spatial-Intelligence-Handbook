<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: multi-modal
paradigm: 3R-SLAM-hybrid
time: temporal-transformer-rolling
ref: ../../cheat-sheet/ontology.md §5
-->

# PanoWorld: Real-World Panoramic Generation  
> **发布时间**：2026/07/10  
> **论文 / 模型名**：PanoWorld  
> **核心定位**：首个专为真实世界全景视频生成设计的 diffusion-based world model，通过旋转等变性解耦运动建模与长程记忆，解决全景视频中因球面畸变、多海拔轨迹和光照变化导致的结构漂移与辐射不一致问题；在 World360 上显著超越 Matrix-3D / OmniRoam 等 SOTA。

PanoWorld 不是“又一个视频扩散模型”，而是首次将 equirectangular 投影的**旋转等变性（rotation-equivariance）** 作为第一性原理，重构全景世界建模范式——它把相机旋转降维为几何变换，只让 diffusion 模型学平移引起的视差，从而绕过传统方法在球面坐标下强行套用透视先验所引发的系统性失真。结果：在真实无人机航拍+AirSim360 多海拔轨迹上，FID ↓54%、PSNR ↑显著、极区失真↓、重访一致性↑。

---

## X-Ray 开场  
PanoWorld 解决的是全景视频生成中“**物理一致性崩塌**”这一根本瓶颈：当相机在真实三维空间中做非平面运动（如爬升、俯冲、绕飞）时，现有方法因无视 ERP 的球面拓扑，导致极区撕裂、光照跳变、重访场景闪烁。它提出两大原生模块：**DPRC（稠密全景光线条件化）** 建模平移驱动的光线强度演化；**GMA（几何感知记忆增强）** 在共享射线坐标系中检索历史特征，而非图像像素或 3D 点云。对 spatial AI 研究者而言，这是首个将**球面几何先验深度嵌入 diffusion transformer 架构**的可扩展框架，为 3R-SLAM-hybrid 范式提供可微分、可控制、可记忆的全景世界表征基座。

---

## 📍 研究全景时间线  
```
[2024] 360DVD (Wang et al.) → text-to-pano video, WEB360 benchmark  
       │  
       ↓ planar motion only, no altitude variation  
[2025] Matrix-3D (Yang et al.) → explicit 3D reconstruction + mask inpainting  
       │                         ↑ expensive, not real-time, fails on height change  
       ↓  
[2025] OmniRoam (Liu et al.) → ReCamMaster-style frame stitching  
       │                      ↑ ghosting under vertical motion, fixed-altitude bias  
       ↓  
[2026] PanoWorld (Li et al.) → DPRC + GMA + 3-stage training on World360  
                              ✅ rotation-decoupled, multi-altitude, memory-anchored  
                              ❌ no explicit 3D mesh, no pose optimization loop, no real-time inference runtime reported
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **Motion Decoupling Preprocessor** | Raw ERP video + pose sequence | De-rotated ERP clips + uniform Δd-sampled translation vectors `c_t` | **训练时强制移除 yaw；推理时输入 de-rotated trajectory**（论文未提供在线 yaw suppression 实现） |
| **DPRC (Action Stream)** | Latent `z_t`, ray directions `r_cam`, translation `c_t` | Ray-local motion-conditioned latent `z_t^dprc` | **Stage 2 冻结 backbone LoRA，仅训 DPRC 参数；推理时需实时计算 `T_ray`（式4）** |
| **GMA (Memory Stream)** | Query latent `z_t`, memory bank `{x_m}` with ray coords `r̂_m` | Confidence-gated fused latent `F_final = F_base + (g·c)·F_mem` | **Stage 3 启用；memory bank 为 sliding window of past frames；`c` 来自 softmax affinity（式6），不可微但可导** |
| **Wan2.2-5B Diffusion Backbone** | Fused latent `F_final`, timestep `t`, text prompt | Denoised ERP frame `x_{t-1}` | **Stage 1：LoRA fine-tune on panoramic data；Stage 2/3：冻结 LoRA，训 DPRC/GMA** |

### 1.2 关键机制  
⚡ **Eureka Moment：旋转在 ERP 中是纯几何变换（不改变场景内容），因此可被完全剥离；所有物理一致性建模只需聚焦于 translation-induced parallax on spherical rays —— 这使 memory retrieval 可在 ray-space 而非 pixel-space 或 3D-space 中完成，规避球面投影畸变。**

### 1.3 信息流 ASCII 图  

```
[Input ERP x₀] → [Motion Decoupling] → [De-rotated x₀' + {c₁...c_T}]  
                                     ↓  
[Latent Encoder] → z₀ → ┌───────────────┐  
                       ↓               ↓  
                 [DPRC Stream]   [GMA Stream]  
                    ↓                   ↓  
             z₀^dprc (ray-cond)   Memory Bank {x₁...xₜ₋₁} w/ r̂ₘ  
                                 ↓  
                     Unified PRoPE Space ← r̂ₜ (same as DPRC)  
                                 ↓  
              Confidence-Guided Attention: Q(z₀^dprc)·K(xₘ) → c  
                                 ↓  
            F_final = F_base + (g·c)·F_mem  
                                 ↓  
                [Wan2.2-5B DiT Decoder] → x₁ → ... → x_T  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**：  
**`F_final = F_base + clamp(max_j Softmax(Q_i K_j^⊤/√d), 0, 1) · F_mem`**  
→ *用射线对应关系替代像素 warp，在球面流形上做 memory attention，confidence 直接来自几何重叠度*

- **目标**：在全景视频生成中实现 long-horizon radiometric & geometric consistency  
- **公式**：式(7) 是 GMA 的最终融合，其中 `c`（式6）是 attention affinity 的最大值，量化 query ray 与 memory ray 的 3D 空间重合置信度  
- **变量说明**：  
  - `Q_i`: query latent at position i, projected to PRoPE space using `r̂_i`  
  - `K_j`: memory key from frame j, also PRoPE-encoded with `r̂_j`  
  - `d`: attention dimension (not depth!)  
  - `g`: learnable gating scalar (paper says "adaptive", but no formula given — likely a per-layer scalar)  
- **直觉**：传统 memory attention 在扭曲的 ERP 像素网格上计算相似度 → 错配；PanoWorld 强制所有 Q/K 都映射到同一射线流形 → `r̂_i ≈ r̂_j` ⇔ same 3D direction ⇔ same scene point ⇔ high `c` ⇔ safe fusion

---

## 3 · 带数字走一遍  

**玩具设定（简化至 2×2 ERP latent grid）**：  
- H=2, W=2 → pixel (i,j) ∈ {(0,0),(0,1),(1,0),(1,1)}  
- 用式(1)算 θ,ϕ：  
  - (0,0): θ = π/2 − (0.5/2)π = π/2 − π/4 = π/4; ϕ = (0.5/2)2π − π = π/2 − π = −π/2  
- 代入式(2)：  
  - `r_cam = [−cos(π/4)cos(−π/2), −cos(π/4)sin(−π/2), −sin(π/4)] = [0, √2/2, −√2/2]`  
- 设 `c_t = [0, 0, 0.1]`（小幅度上升）  
- 式(3)：`z_loc = r_cam`, `u_world = [0,0,−1]` → `a_y = normalize(z × u) = normalize([−√2/2,0,0]) = [−1,0,0]`, `a_x = a_y × z = [0,−√2/2,−√2/2]`  
- 式(4)：`T_ray` 的平移项 `−R_loc^⊤ c_t` 就是 `c_t` 在 local basis 下的坐标 → 影响 latent 更新方向  
- 最终 `c` in 式(6)：若 memory bank 有帧 j 其 `r̂_j` 与当前 `r̂_i` 夹角 < 5°，则 `Softmax(...)` 在该 j 上接近 1 → `c≈1` → full memory injection  

→ **关键洞察**：哪怕 ERP 图像上 (0,0) 和 (1,1) 像素相距很远，只要它们指向同一 3D 方向（如都看天顶），`r̂_i ≈ r̂_j` → `c≈1` → memory 被激活 → 保证天顶区域重访一致性。

---

## 4 · 工程视角  

| 维度 | 数值 | 来源 / 备注 |
|------|------|-------------|
| **延迟（per frame）** | `论文未报告` | 未给出 FPS / latency；Table 5 显示 720p 分辨率下 FID 更优，但未提推理速度 |
| **步数（denoising）** | `论文未报告` | 未说明采样步数（如 20/50）；Fig.5 qualitative results 未标帧率 |
| **显存（VRAM）** | `论文未报告` | Wan2.2-5B 是大模型，但未报告 batch size / GPU 型号 / VRAM usage |
| **吞吐（throughput）** | `论文未报告` | Sec.5.1 仅说 “fine-tuning on panoramic datasets”，无 inference throughput |
| **部署约束** | `UNVERIFIED` | 提到 “real-time via Causal Forcing”（Sec.5.4/C.1），但无 latency 数字；Causal Forcing 未定义公式，仅说 “enables streaming generation” |

✅ **Trade-off 总结**：  
- **精度换效率**：DPRC/GMA 均依赖实时 ray re-projection（式1–4），计算开销高于普通 pixel attention；  
- **内存换一致性**：GMA memory bank 为 sliding window，长度未指定（likely O(10) frames），显存随 window size 线性增长；  
- **可控性换复杂度**：de-rotated trajectory 预处理需外部 pose estimation + yaw removal pipeline，非端到端。

---

## 5 · 数据与评测  

| 项目 | 值 | 来源确认 |
|------|----|----------|
| **数据集名** | `World360` | ✅ Abstract, Sec.3, Table 1 |
| **组成** | `70K real-world (Anti-Gravity UAV) + 50K synthetic (AirSim360)` | ✅ Abstract, Sec.3, Table 1 |
| **分辨率** | `480p (480×960), 720p (720×1440)` | ✅ Sec.5.1, Table 2 |
| **评测指标** | `FID / FID_pole / FID_equ / FAED / NIQE / QA_qual. / QA_aes. / PSNR` | ✅ Sec.5.1, Table 2–3 |
| **PSNR 计算方式** | `average PSNR over multiple temporal windows vs GT trajectory` | ✅ Sec.5.1 |
| **Trajectory control protocol** | `all methods conditioned on same GT trajectories (no SfM noise)` | ✅ Sec.5.1 |
| **Baseline 名** | `Imagine360 / Matrix-3D / OmniRoam` | ✅ Sec.5.1 |

⚠️ 注意：所有指标数值均**逐字复制自 Table 2–3**（如 FID=27.64, PSNR 未给具体值但说 “significantly higher”）。  
❌ **未报告**：`Q-Align` 具体数值、`ViPE` pose error 数字、ablation study 中各 stage 的单独指标。

---

## 6 · 能力与失败模式  

| 能力 | 描述 | 证据 |
|------|------|------|
| ✅ **多海拔轨迹控制** | 在 World360 的 aerial trajectories（含爬升/俯冲）上保持结构完整 | Fig.5, Sec.5.2: “Matrix-3D suffers from voids during height variations” |
| ✅ **极区稳定性** | FID_pole=47.21（SOTA 最低），显著优于 Matrix-3D (67.88) | Table 2 |
| ✅ **重访一致性** | GMA confidence gating ensures landmarks identical upon revisit | Sec.4.1.3, Fig.4 caption |
| ⚠️ **仅支持 de-rotated 输入** | 要求外部 pipeline提供 yaw-free trajectory；不支持 raw pose | Sec.4.1.1, Sec.5.1: “de-rotated camera trajectories” |

### 隐含假设 (Hidden Assumptions)  
- **静态 scene assumption**: DPRC 式(4) 中 `R_t = I`（de-routed），即假设场景刚体静止；动态物体（如车辆、行人）会破坏 ray intensity evolution 模型。  
- **Global up-vector known**: 式(3) 依赖 `u_world = [0,0,−1]`，要求 world coordinate system 对齐重力方向；无人机翻滚 >30° 时 `a_y` 计算失效。  
- **Memory bank is clean**: GMA 假设 memory bank 中帧无 motion blur / exposure jump；但 World360 Illumination Filtering（Sec.3）仅排除 “improper illumination”，未定义阈值。

---

## 7 · 与相关工作对比  

| 方法 | 表示 | 运动建模 | 记忆机制 | 真实世界适配 | World360 SOTA? |
|------|------|-----------|------------|----------------|----------------|
| **Imagine360** | ERP | Text-conditioned, no explicit pose | Clip-bound context | Indoor/street only | ❌ FID=81.18 |
| **Matrix-3D** | ERP + 3D mesh | Explicit 3D reconstruction + rendering | 3D feature cache | Fails on height change | ❌ FID=34.63 |
| **OmniRoam** | ERP | ReCamMaster frame stitching | Real+gen frame concat | Fixed-altitude bias | ❌ PSNR low on elevation |
| **PanoWorld (Ours)** | ERP + ray manifold | DPRC: ray-local translation | GMA: ray-space attention | Multi-altitude UAV + sim | ✅ FID=27.64, PSNR↑ |

**面试 Tip**：  
> *被问 “PanoWorld 和 Matrix-3D 本质区别？”*  
> **答**：Matrix-3D 是 “重建-渲染” 范式：先从单帧重建 3D 场景（易错），再按 pose 渲染（计算重）；PanoWorld 是 “射线演化” 范式：把每帧视为球面光场快照，直接学习光线强度如何随相机平移变化（式2–4），跳过显式重建，因此轻量、鲁棒、天然适配 ERP 拓扑。这不是工程优化，而是表示层面的范式迁移。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-23)  

**官方 repo 未在论文中给出**, 以下 pitfall 由 §6 失败模式推导（未经 issue 验证）：  
1. **`yaw suppression failure → structural tearing`**：若输入 trajectory 含未校正 yaw（如无人机自动稳定系统抖动），DPRC 的 `R_t = I` 假设崩塌 → ray unprojection 错位 → ERP 边界出现撕裂（Sec.4.1.1: “removes artifacts that violate 360° projection rules” 反向即 failure mode）。  
2. **`u_world misalignment → local basis collapse`**：当无人机倒飞或侧倾 >45°，`u_world = [0,0,−1]` 与实际重力方向偏差大 → 式(3) 中 `a_y` 计算失准 → `T_ray` 平移项错误 → 生成画面出现非物理性拉伸（Sec.4.1.2: “world-up vector” 是硬编码）。  
3. **`memory bank contamination → confidence hallucination`**：若 Illumination Filtering 不够严（Sec.3），memory bank 存入过曝帧 → `c` 在式(6) 中仍高（因 ray correspondence 仍成立）→ 过曝特征被注入正常帧 → 局部白化（Sec.4.1.3: “prevent content hallucination in unobserved regions” 但未防 observed-but-bad regions）。

---

[← Back to 3R-SLAM-hybrid README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.09661 -->
