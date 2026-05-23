# 麦克风阵列波束成形物理 (Microphone Array Beamforming Physics)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — multi-mic array / DOA / GCC-PHAT / MUSIC / beamforming
> **核心定位**：声学 "stereo 几何" — 多麦时间差给 direction-of-arrival，beamforming 给 SNR 增益；机器人**听到人声方向**的物理基础

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板。数字 `UNVERIFIED` 需 Respeaker / iFlytek / Sony 数据手册核对。
**Wedge tier:** W1（G 桶"其他物理波"6 篇之一）

### X-Ray opening (非专家友好)

(a) 多个麦克风同时录同一声源 → 声波到不同 mic 有 **time-difference-of-arrival** (TDoA) → 反推声源方向 (DOA, direction-of-arrival)。空气中声速 343 m/s，10 cm 间距 mic 阵列对垂直入射声波看到 ~290 µs 时间差 — 用 GCC-PHAT 算法估计。N 个 mic 还可以做 **beamforming** 把目标方向信号相加增益 √N、噪声分散抵消。(b) Amazon Alexa / Google Home / Apple HomePod 全部用 6-7 mic 圆阵；Respeaker 系列是开源机器人界的事实标准；hearing aid / 视频会议 (Jabra / Owl Labs) 同物理。(c) 对机器人工程师：mic array 是**人机交互核心 sensor** — 听 wake word + 看 speaker direction → 机器人转向看人；同时 active noise cancellation 给 ASR 喂干净音频。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
1970s ── 声呐 beamforming / 军用水下定位
1976 ── Knapp & Carter — GCC-PHAT 经典算法
1986 ── MUSIC algorithm (Schmidt) / ESPRIT (Roy & Kailath)
2000s ── Microsoft Kinect (4-mic linear array) — beamforming 进消费
2014 ── Amazon Echo (7-mic circular) — smart speaker 大爆发
2017 ── Apple HomePod (6-mic) / Google Home Max
2019 ── ReSpeaker 4/6 mic — 机器人开源 mic array 标准
2020-22 ─ DNN beamforming (DeepBeam / NN-FaSNet) 替代经典算法
2024 ── Sony 16-mic AR headset / Meta Reality Labs 多 mic VAD
        ── 你在这里 (2026) ──
?    ── End-to-end ASR + DOA + speaker ID 单模型；neural ambisonic
```

经典 (GCC-PHAT / MUSIC) → 神经网络方法在 2020 后逐步替代，但**信号物理基础没变** — 学界仍以经典方法做 baseline。

---

## 1 · 工作原理 (Operating Principle / Overview)

📌 **Napkin Formula** (X-Ray)：

```
TDoA → DOA:
τ_ij = (d_i - d_j) / c                       (c = 343 m/s 空气)
对线阵 (mic 间距 d_mic):
sin(θ_DOA) = c × τ / d_mic                   (远场 plane wave 近似)

Spatial aliasing 限:
d_mic ≤ λ_min / 2 = c / (2 × f_max)
   f_max = 8 kHz (语音) → d_mic ≤ 2.1 cm
   f_max = 16 kHz       → d_mic ≤ 1.1 cm

Beamforming gain:
G_array = 10·log(N)  dB  (理想 N mic delay-sum)
   4 mic → 6 dB, 6 mic → 7.8 dB, 8 mic → 9 dB
```

间距决定**空间 Nyquist** — 太大 → spatial aliasing；太小 → 阵列尺寸小 → DOA 精度差。这是阵列设计第一约束。

### 1.1 阵列几何对比

| 阵列形态 | 典型 mic 数 | DOA 维度 | 应用 |
|---|---|---|---|
| **单 mic** | 1 | 无 | 一般录音 |
| **2-mic linear** | 2 | 1D（前后模糊）| hearing aid / 手机 |
| **4-mic linear** | 4 | 1D + beam | Microsoft Kinect |
| **4-mic square** | 4 | 2D（azimuth）| Respeaker 4-mic |
| **6-mic circular** | 6 | 2D + 高 SNR | Amazon Echo / HomePod |
| **8-16 mic spherical** | 8-16 | 3D（azimuth + elevation）| AR headset / 高端会议 |

### 1.2 关键机制：GCC-PHAT (Generalized Cross-Correlation Phase Transform)

```
R_ij(τ) = IFFT{ X_i(f) × X_j*(f) / |X_i(f) × X_j*(f)| }
                                  ↑
                              PHAT weighting: 仅留相位
τ_ij_est = argmax(R_ij(τ))
```

PHAT 把幅度归一化，仅留 phase 信息 → 对噪声 / 房间 reverberation **鲁棒**。这是 40 年来 DOA 算法的工业基线。

⚡ **Eureka Moment.** Beamforming 不是"放大声音"— 它是**空间滤波器**。N mic 阵列同时给：
1. 目标方向 SNR 提升 √N
2. 其他方向 attenuate
3. 一次性 echo cancellation（相位错位 echo 不在主 beam）

**这就是为什么 Alexa 在嘈杂厨房还能听清 "Hey Alexa"** — 不是麦克风更好，是 6 mic 在空间上把背景音"减掉"。

### 1.3 Signal flow

```
6-mic circular array (radius 4 cm)
   │
   ▼
[6 ADCs @ 16 kHz, 24-bit]
   │
   ▼
DOA estimation (GCC-PHAT / SRP-PHAT) → θ_speaker
   │
   ▼
Beamformer (delay-sum / MVDR / DNN) → enhanced single-channel audio
   │
   ▼
ASR (wake-word + LLM)
   │
   ▼
Robot action: "turn head toward θ"
```

ReSpeaker 系列 SDK / Respeaker SLM 把整个 pipeline 打包在 $30-100 module。

---

## 2 · 数学核心：DOA 算法谱 (Math Core)

📌 **Napkin Formula** (X-Ray)：DOA 算法分三档：(1) **GCC-PHAT** — 经典，单声源 OK；(2) **MUSIC / ESPRIT** — 高分辨率，分辨多声源；(3) **DNN-based (NN-DOA)** — end-to-end，对 reverb 鲁棒。

### 2.1 MUSIC (MUltiple SIgnal Classification)

```
R = E[x(t) × x*(t)]      (协方差矩阵 N×N)
特征分解: R = U_s Λ_s U_s' + U_n Λ_n U_n'
                         ↑signal subspace  ↑noise subspace

P_MUSIC(θ) = 1 / (a*(θ) U_n U_n' a(θ))
峰值位置 = DOA
```

变量：
- `a(θ)` — 阵列响应向量（steering vector）
- `U_n` — 噪声子空间

MUSIC 能分辨**比 mic 数少 1 的同时声源**（6 mic → 5 同时 speaker）— 远超 GCC-PHAT 的"单声源夹击"限。

### 2.2 SRP-PHAT (Steered Response Power)

对每个候选方向 θ 计算"假设声源在那"的 phase-aligned 总能量；遍历角度网格找峰。等价于 GCC-PHAT 在所有 mic pair 求和。鲁棒 + 多源。

### 2.3 MVDR Beamforming

```
w_MVDR = (R⁻¹ × a(θ)) / (a*(θ) R⁻¹ a(θ))
output = w_MVDR' × x(t)
```

"在 θ 方向单位增益，其他方向最小输出"— 等价于"看目标方向的 super-directional mic"。配 voice activity detector → 动态自适应跟随说话人。

### 2.4 DNN-based (NN-FaSNet / Deep Beamforming)

2020+ 主流：CNN / RNN 直接从多 mic 输入预测单通道 enhanced output。end-to-end，对 reverb / non-Gaussian noise 比经典强。**Cost**: 计算量大、可解释性差、训练数据依赖。**学界 2026 共识**: DNN 用于 enhancement，经典算法仍用于 DOA（更稳）。

---

## 3 · Worked example — 6-mic circular array @ Amazon Echo

设置（数字 `UNVERIFIED`）：
- 6 mic 等距分布在 r=4 cm 圆上
- Sampling 16 kHz, 24-bit
- 声源：人在 1 m 远，30° azimuth

**TDoA 极值:**
- max delay = 2 × r / c = 0.08 / 343 = 233 µs
- @ 16 kHz → 3.7 samples
- Sub-sample: 用 GCC-PHAT 上采样 8× → 0.46 sample 分辨率 = ~30 µs ≈ 1° angular

**Beamforming gain:**
- 6 mic delay-sum → +7.8 dB SNR vs 单 mic
- + MVDR adaptive → 额外 5-10 dB (kitchen 噪声场景)
- Total ~15 dB enhancement → "Alexa" 在油烟机背景下被听清

**Spatial aliasing 检查:**
- 邻 mic 间距 ≈ 2 × r × sin(30°) = 4 cm
- Aliasing 限频率: f_max = c / (2 × 4 cm) = 4.3 kHz
- ⚠️ 4 kHz 以上有空间 aliasing — 但语音信息 80% 集中在 <4 kHz，OK

**Power.** ADC 6 路 + DSP processing ~200 mW；Always-on wake word detection ~50 mW (low-power DSP)。

---

## 4 · 工程视角 (Engineering View)

**Cost (`UNVERIFIED`):**
- Single MEMS mic (Knowles / Infineon): $0.5-2
- Respeaker 4-mic linear: $25
- Respeaker 6-mic circular: $50-100
- ReSpeaker Mic Array v2.0 (with DSP): ~$70
- Amazon Echo / Google Home 内部 BOM ~$10-20 (mic array + DSP chip)

**功耗.**
- Standby (wake word always-on): ~50-100 mW
- Active streaming + beamforming: 200-500 mW
- 比 RGB camera (~500 mW-1 W) 低；比 PIR (~10 µW) 高很多

**Latency.**
- Wake word detection: 100-300 ms
- DOA estimation: 20-50 ms (16 ms frame + algorithm)
- End-to-end ASR + LLM: 500-2000 ms

**Mechanical.**
- Mic 必须**机械去耦** — 否则机器人电机 / fan 振动直接进 mic
- 圆形阵列在 PCB 边缘 → 抗内部 EMI / 振动
- 防风罩 (windshield) 户外必备

---

## 5 · 数据与评测 (Data & Eval)

- **CHiME challenge** — 多 mic 远场 ASR benchmark（CHiME-6, 2020）
- **DCASE** — 声学场景 + 事件检测 benchmark
- **LOCATA dataset** — 多 mic + 移动声源 DOA tracking benchmark
- **Sony / Audio Spatial datasets** — VR / AR ambisonic 评测

---

## 6 · 能力与失败模式 (Capabilities & Failure Modes)

**能做什么.** 听清远场（5-10 m）说话；定位声源方向 ~1-3° 精度；同时跟踪 2-4 个 speaker；抗背景噪声 (kitchen / 街道) +10-20 dB SNR；wake word 24/7 monitoring 低功耗。

**不能做什么.** 测距（mic array 不直接测距，需声源主动配合 ping-back）；穿墙听清（薄墙 OK，厚混凝土损失 30+ dB）；高频精确 DOA（spatial aliasing）；强 reverberation 房间（混响时间 >0.5 s 退化严重）。

### Hidden Assumptions

- **声源远场 (plane wave).** <0.5 m 近场需要球面波修正
- **静止声源 or 慢速.** 快速移动声源（车）TDoA 不稳定
- **mic 已 calibrated.** mic 间 gain mismatch 1 dB → DOA bias 几度
- **房间不极端混响.** 浴室 / 教堂 / 阶梯井 RT60 >1 s → GCC-PHAT 大幅退化
- **目标声谱 broadband.** 单频纯音 DOA 不稳定（spatial aliasing 严重）
- **风声 / 振动隔离.** drone 风噪 / 机器人马达 → mic 直接耦合噪声

**失败模式：**
- **Cocktail party 同方向多 speaker.** beam 都开向同一区域 → 听不清单一人；需要 BSS（盲源分离）算法
- **drone propeller noise.** -3 to 0 dB SNR；标准 mic array 在 drone 上几乎不工作 — 需要 propeller-aware noise cancellation
- **echo from speaker.** 机器人自己说话 echo 进 mic → AEC (acoustic echo cancellation) 必装
- **temperature drift.** 空气温度变化改 c → DOA 偏 1% per 10°C
- **wind noise.** 户外 >5 m/s 风直吹 mic → low-freq 饱和

---

## 7 · 与相关工作对比 (Comparison)

### Mic array vs 其他人机交互 sensor

| Sensor | 检测 | 隐私 | Range | Cost |
|---|---|---|---|---|
| **Mic array (6-mic)** | speech + DOA | ★★ (audio) | 5-10 m | $50-100 |
| **Camera (RGB)** | gaze + lip + gesture | ★ | 5-10 m | $20-100 |
| **Wake word PIR** | presence | ★★★★ | 5 m | $1 |
| **mmWave radar** | presence + breath | ★★★★ | 10 m | $10-50 |
| **Thermal camera** | body | ★★ | 50 m | $200+ |

**🎙️ Interview Tip.** 被问"为什么 Alexa 用 6 mic 不用 1"？— 不是"放大声音"问题。6 mic = **空间滤波器** → (1) DOA 给方向，(2) beam-sum +7.8 dB SNR，(3) 反方向 noise 自然 cancel，(4) 多 talker 分离。**单 mic 用最好的算法也做不到**这些 — 物理上必须多 mic。

### Counter-Drone Audio 应用

Drone propeller 在 50-2000 Hz 有特征 spectral signature。**counter-drone mic array** 在地面装 16-32 mic 球阵列，多公里外就能 detect + DOA enemy drone。比 radar / 视觉早 30 s 预警，是反 drone 系统物理层。

---

## 8 · For the reader

- **Manipulation** — 极少用（操作场景声音少 informative）
- **Mobile robot (service)** — 必装 mic array → 人机对话 + DOA "看人方向"。ReSpeaker 6-mic 是事实标准
- **Drone** — 标准 onboard 不装（风噪 too high）；外部 ground station 装阵列做 counter-drone
- **AD** — 车内 mic array 做 voice control + occupant detection；外部很少
- **AR / VR headset** — 8-16 mic 球阵列做 ambisonic + spatial audio capture
- **Search & Rescue** — 听呼救方向；典型 4-mic linear 装救援机器人 / drone

---

## References

- Knapp & Carter — *The Generalized Correlation Method for Estimation of Time Delay* (IEEE TASSP 1976)
- Schmidt — *Multiple Emitter Location and Signal Parameter Estimation* (IEEE TAP 1986, MUSIC paper)
- Brandstein & Ward — *Microphone Arrays* (Springer 2001)
- ReSpeaker documentation (Seeed Studio)
- Amazon Alexa Voice Service technical reference
- CHiME Challenge dataset / Far-field ASR benchmark

## Boundary

- Mic array 信号物理 / 算法谱 → 本文
- `crossing/sensor-stack-matrix/` — audio sensor 在 6 embodiment 取舍
- `embodiments/ground/sensor-stack/` — service robot mic array 工程集成
- `deployment/hardware-selection/` — ReSpeaker vs XMOS vs Sony 选型
- ASR 算法 / wake word DNN → 不在本目录（属语音 ML）
- 声呐 (水下) → `underwater_sonar_physics.md`
- 空气超声 (40 kHz active) → `ultrasonic_acoustic_physics_for_robotics.md`

*2026-05-21. v1. UNVERIFIED → v1.1 待 ReSpeaker / Knowles / Infineon datasheet 核对。*

---
[← Back to sensor-physics README](./overview.md)
