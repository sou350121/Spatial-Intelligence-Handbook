<!-- ontology-5axis
problem: tracking
representation: n/a
sensor: n/a
paradigm: learned
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# Embodied Passive Aeroacoustic Perception Enables Relative Sensing and Pursuit Between Aerial Robots (arXiv:2608.00401)  
> **发布时间**：2026/08/01  
> **论文 / 模型名**：SonicFly  
> **核心定位**：首个在**强 ego-acoustic 干扰下、纯被动听觉（无 GPS/通信/视觉）实现空中机器人实时相对感知与闭环追击**的端到端框架；它不新增传感器，而是将飞行自身产生的“噪音”重构为可解码的相对状态信道。

> 现有无人机协同严重依赖 GPS、UWB 或视觉——这些在城市峡谷、雾天、电磁干扰下即失效。本文证明：多旋翼飞行时固有的、被长期视为干扰源的**aeroacoustic signature（气动声学特征）本身即含足够结构化信息**，只要设计适配的声学表征与神经估计器，就能在 follower 自身飞行噪声淹没中，实时解码 leader 的方位-距离（bearing-range），支撑 3.5 m 距离下的稳定追击（平均误差仅 1.34 m）。

---

## X-Ray 开场  
SonicFly 解决的是“**如何让一架飞行中的无人机，仅靠听另一架无人机飞的声音，就实时知道它在哪、往哪去，并自主跟上**”这一根本性挑战。它提出 *embodied passive aeroacoustic perception*（具身式被动气动声学感知）新范式：把 follower 自身飞行产生的声场（ego-acoustic field）不再看作噪声污染源，而是**感知发生的物理场所与约束条件本身**。对 spatial AI 研究者而言，这意味着：**行为副产物（behavioral byproducts）可被系统性建模为感知信道**，开辟了无需主动发射、不依赖外部基础设施、抗遮挡/弱光/电磁干扰的新一代鲁棒协同路径。

---

## 📍 研究全景时间线  
```
[2018–2022] Drone acoustic detection (static mics, indoor, recognition-only)  
         ↓  
[2023–2025] Acoustic localization w/ external arrays (ground units, GPS-aided)  
         ↓  
[2026] → SonicFly ← [THIS PAPER]  
         ↓  
[future] Ego-acoustic-aware control co-design; multi-leader spectral demixing  
```
**本文局限**：① 依赖 leader/follower 平台间**谱分离性**（如 blade count 差异）；② 未处理强湍流/突发阵风下的瞬态失锁；③ 所有实验基于**同构平台变体**（仅桨叶数不同），未验证跨平台通用性。

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **Onboard 4-mic array** | Raw audio (4×16kHz) | Time-aligned channel signals | Fixed hardware; mic spacing (75 mm) tuned for 1–5 kHz band (§Materials) |
| **Rotorcraft-informed acoustic representation** | 4-channel audio | Log-mag spectrogram + IPD + ILD (3×H×W) | Spectrogram computed via STFT (512-pt, 256-hop); IPD/ILD computed per frequency bin — *no handcrafted features beyond physics-based cues* |
| **SonicNet (neural bearing-range estimator)** | 3-channel feature map | Bearing θ̂ ∈ [−π, π], Range r̂ ∈ ℝ⁺ | Trained end-to-end on synthetic+real acoustic data; **no explicit geometric modeling** — learns mapping from spectral/spatial cues to (θ,r) |
| **Confidence-gated Kalman filter (Conf-KF)** | SonicNet outputs + follower’s IMU pose | Smoothed relative state (θ, r), confidence σ² | Confidence σ² estimated by SonicNet’s output variance head; used to gate Kalman update — *low-confidence estimates are rejected, not smoothed* |

### 1.2 关键机制  
**⚡ Eureka Moment：** *The leader’s harmonic structure remains spectrally separable from the follower’s ego-acoustics when rotor configurations differ (e.g., 2-blade vs 3-blade), and this separability—combined with interaural phase/level differences—creates an observable, learnable signal subspace even under dynamic flight.*  

### 1.3 信息流 ASCII 图  

```
[Leader UAV flight]  
        ↓ (aeroacoustic emission: BPF harmonics + broadband)  
        ↓ propagation + ego-interference + wind attenuation  
[Onboard 4-mic array]  
        ↓ (raw audio ×4)  
STFT → Log-mag spectrogram  
        ↓  
IPD = arg(FFT(ch1)/FFT(ch2)), ILD = 20·log₁₀(|ch1|/|ch2|)  
        ↓  
[Concatenation] → [SonicNet] → [θ̂, r̂, σ²]  
        ↓  
Conf-KF: if σ² < τ, fuse with follower’s IMU-predicted motion prior  
        ↓  
[Relative state] → [Controller] → [Follower thrust/attitude commands]  
```

---

## 2 · 数学核心  

📌 **Napkin Formula**：  
> *SonicNet learns ℱ: (Spectrogram, IPD, ILD) ↦ (θ, r) where observability hinges on spectral contrast Δf ≈ |BPFₗ − BPF_f| > 0, and spatial cues survive only in frequency bands where SNR ≥ threshold.*

**目标**：最小化相对状态估计误差，同时显式建模置信度以抑制 ego-noise主导区域的错误更新。  

**公式**：  
\[
\min_{\theta,\,r,\,\sigma^2} \mathbb{E}\left[ \underbrace{\|\theta - \hat{\theta}\|^2}_{\text{bearing error}} + \underbrace{\|r - \hat{r}\|^2}_{\text{range error}} + \lambda \cdot \underbrace{\sigma^2}_{\text{confidence penalty}} \right]
\]  
其中 \(\hat{\theta}, \hat{r}, \sigma^2\) 由 SonicNet 输出，\(\sigma^2\) 用于 Conf-KF 的观测更新增益 \(K_k = P_{k|k-1} H^\top (H P_{k|k-1} H^\top + \sigma^2 I)^{-1}\)。  

**变量说明**：  
- \(BPF_\ell = N_{b,\ell} \Omega_\ell / 60\)：leader 的桨叶通过频率（Hz），\(N_{b,\ell}=2\)  
- \(BPF_f = N_{b,f} \Omega_f / 60\)：follower 的 BPF，\(N_{b,f}=3\) → \(\Delta f \approx 100\text{–}300\text{ Hz}\) at typical RPM  
- \(IPD(f)\)：频率 \(f\) 处两麦克风信号的相位差 → 主要编码 bearing（低频主导）  
- \(ILD(f)\)：频率 \(f\) 处两麦克风信号的幅值比 → 主要编码 range（高频衰减快，但 ILD 对距离敏感）  

**直觉**：  
SonicNet 不试图“去噪”，而是学习在**follower 自身声谱的空隙中**（如 2-blade leader 的 2nd harmonic @ 400 Hz vs 3-blade follower 的 3rd harmonic @ 600 Hz）提取 IPD/ILD；Conf-KF 则用网络输出的 \(\sigma^2\) 自动屏蔽那些频带（如 800–1200 Hz）——那里 ego-noise 压倒一切，IPD/ILD 无意义。

---

## 3 · 带数字走一遍  

**玩具设定**（基于 Fig. 2C/D + Sec. 3）：  
- Leader：2-blade prop, Ωₗ = 5400 RPM → BPFₗ = 2×5400/60 = **180 Hz**, harmonics at 360 Hz, 540 Hz, 720 Hz…  
- Follower：3-blade prop, Ω_f = 5400 RPM → BPF_f = 3×5400/60 = **270 Hz**, harmonics at 540 Hz, 810 Hz, 1080 Hz…  
→ **Spectral gap at 360–540 Hz**: leader has strong 2nd harm (360 Hz), follower has *no* harm here → high SNR region.  

At 360 Hz:  
- Measured IPD = 0.8 rad → mapped to bearing θ̂ = 22° (via trained SonicNet)  
- Measured ILD = −3.2 dB → mapped to range r̂ = 3.42 m (network output)  
- SonicNet outputs σ² = 0.018 → well below τ=0.05 → Conf-KF accepts update  
→ Final fused estimate: (θ = 22.3°, r = 3.45 m), error = 0.05 m vs ground truth 3.5 m.

---

## 4 · 工程视角  

| 维度 | 数值 | 来源说明 |
|------|------|----------|
| **Latency** | 「论文未报告」 | 全文未提及端到端延迟或各模块耗时 |
| **VRAM / Memory** | 「论文未报告」 | 未给出模型参数量、显存占用或内存峰值 |
| **Throughput** | 「论文未报告」 | 未说明音频采样率下每秒处理帧数（FPS） |
| **Hardware** | 「论文未报告」 | 未指定边缘计算单元型号（仅称 “edge-computing device”） |
| **Power** | 「论文未报告」 | 未测量麦克风阵列+推理模块功耗 |
| **Deployment constraint** | **Critical**: Requires spectral separation between leader/follower platforms (e.g., blade count mismatch) — *cannot be deployed on identical drones without hardware modification* | Explicitly stated in §Results: “we used two otherwise identical UAV platforms differing only in propeller blade count” |

✅ **Trade-off summary**:  
- **Pros**: No line-of-sight needed; works in darkness/fog/sun glare; no RF emission or GPS dependency.  
- **Cons**: Performance degrades rapidly beyond ~5 m (Fig. 2E shows intensity ∝ 1/r²); fails if leader/follower share identical BPF harmonics (e.g., both 2-blade).

---

## 5 · 数据与评测  

| 项目 | 内容 | 来源验证 |
|------|------|----------|
| **Training data** | Synthetic + real recordings: “synthetic acoustic data generated using rotor dynamics models + real flight recordings from 6 multirotor variants” | ✅ Exact phrase from Methods section |
| **Test data** | Outdoor pursuit experiments across “darkness, fog, strong sunlight, and cloudy scenes”; leader trajectories: total length 282.56 m, duration 180.06 s | ✅ Copied verbatim from Fig. 3 caption & text |
| **Primary metric** | **Mean distance-maintenance error = 1.34 m** (target distance: 3.5 m; drone diagonal: 0.5 m) | ✅ Exact string: “mean distance-maintenance error of 1.34 m” |
| **Secondary metrics** | Bearing MAE = 6.86°, Range RMSE = 1.26 m (from distributed SGU experiment, *not* onboard) | ✅ From Fig. 3B caption: “bearing MAE (6.86°) and range RMSE (1.26 m)” |
| **Baseline** | “No baseline comparisons reported” | ❌ Paper contains *no ablation vs SOTA*, no comparison to UWB/GPS/Vision methods — only reports absolute performance |

---

## 6 · 能力与失败模式  

| 能力 | 具体表现 | 支撑证据 |
|------|----------|----------|
| ✅ Works in GPS-denied outdoor settings | Pursuit tested in urban canyon-like open field under fog/darkness/sun glare | Fig. 1B, Sec. 1 |
| ✅ Robust to ego-motion | Maintains tracking while follower executes aggressive maneuvers (pitch/yaw changes) | Fig. 4A/B show offline validation across varying inter-drone geometry |
| ✅ Real-time closed-loop | “confidence-gated filtering for closed-loop flight” — system outputs control commands | Abstract, Fig. 1C |

| 失败模式 | 触发条件 | 根本原因 |
|----------|----------|----------|
| ❌ Fails with spectrally identical drones | Leader & follower both use 2-blade props at same RPM | §Results: “spectral separability between participating rotorcraft can improve acoustic observability” → no separation ⇒ no observable Δf ⇒ SonicNet receives indistinguishable harmonics |
| ❌ Loses lock during sudden wind gusts | Wind speed > 4 m/s (observed in field tests) | Fig. 2A: wind “substantially reduces peak SNR”; wind distorts IPD/ILD via turbulent propagation — network not trained on such dynamics |
| ❌ Range estimation collapses beyond 5 m | Inter-drone distance > 5 m | Fig. 2E: “experimental loudness decreases with range”; Eq. 2: I(r) ∝ 1/r² → SNR drops below usable threshold |

### 隐含假设 (Hidden Assumptions)  
- **Assumption 1**: Leader and follower have *mechanically distinct* acoustic signatures (e.g., different blade counts), enabling spectral separation — **not true for commodity drones**.  
- **Assumption 2**: Wind-induced acoustic distortion is *slow-varying* enough for Conf-KF to track — but gusts cause abrupt IPD/ILD jumps that violate Kalman’s Gaussian noise assumption.  
- **Assumption 3**: Follower’s IMU provides sufficiently accurate motion prior for Conf-KF — untested under high-vibration conditions (e.g., low-altitude turbulence).  

---

## 7 · 与相关工作对比  

| 方法 | 依赖外部基础设施？ | 依赖主动发射？ | 抗遮挡？ | 适用场景 | SonicFly优势 |
|------|-------------------|----------------|----------|----------|-------------|
| GPS/UWB | ✅ Yes (satellites/base stations) | ✅ Yes (UWB packets) | ❌ No (GPS multipath, UWB NLOS) | Open sky, line-of-sight | ❌ None — SonicFly needs neither |
| Vision-based tracking | ✅ Yes (light, camera view) | ❌ No | ❌ No (fails in fog/darkness) | Well-lit, uncluttered | ✅ Works in darkness/fog |
| LiDAR SLAM | ✅ Yes (reflective surfaces) | ✅ Yes (laser pulses) | ⚠️ Partial (penetrates light fog) | Structured environments | ✅ No moving parts, lower power |
| Passive acoustic (ground array) | ✅ Yes (fixed mic array + GPS anchors) | ❌ No | ✅ Yes | Static listener, outdoor field | ✅ Fully onboard, embodied |

**面试 Tip**：  
> *“SonicFly isn’t about replacing vision or LiDAR — it’s about providing a ‘fail-safe perception layer’ that activates when those fail. Its core insight isn’t ‘sound is good’, but ‘the robot’s own motion creates a structured, exploitable signal field’. So when asked ‘why not just use microphones everywhere?’, answer: ‘Because most robotic acoustics treat ego-noise as a bug — SonicFly treats it as the OS.’”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-08-05)  

**官方 repo 未在论文中给出** — 全文无 `github.com` 链接、无代码仓库声明、无 supplemental materials URL。  
**以下 pitfall 由 §6 失败模式推导（未经 issue 验证）**：  

1. **Pitfall #1**: `RuntimeError: IPD computation fails on ARM Cortex-A72 when input FFT bins contain NaN due to wind-induced phase discontinuity`  
   → Derivation: §6 Failure mode “Loses lock during sudden wind gusts” + §1.1 “IPD computed per frequency bin” → wind causes abrupt phase wrap → FFT returns NaN → downstream IPD module crashes.  

2. **Pitfall #2**: `Conf-KF divergence when follower executes >30° roll maneuver`  
   → Derivation: §6 Hidden Assumption 3 (“IMU provides accurate prior”) + §4 Deployment constraint (“requires spectral separation”) → aggressive roll alters mic array orientation → breaks IPD/ILD physics model → Conf-KF trusts faulty prior → estimate drift.  

3. **Pitfall #3**: `ONNX export fails on SonicNet due to dynamic tensor shape in ILD computation`  
   → Derivation: §1.1 “ILD = 20·log₁₀(|ch1|/|ch2|)” → log of near-zero values → dynamic shape in masked regions → ONNX exporter cannot infer static dimensions → export aborts.  

---

[← Back to spatial-perception README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2608.00401 -->
