# FoundationStereo (FoundationStereo 立体匹配基础模型解构 — NVIDIA 2024)

> **Published**: 2025-01 (arXiv 2501.09898) · CVPR 2025 Best Paper Nomination
> **Paper**: NVIDIA — *FoundationStereo: Zero-Shot Stereo Matching* https://arxiv.org/abs/2501.09898
> **Team**: NVIDIA
> **Core position**: 立体匹配基础模型 — RAFT-Stereo 谱系架构 + foundation-feature 骨干 + 大型合成语料库 → 跨 Middlebury / KITTI / ETH3D 零样本泛化，无 per-domain fine-tune. 若能在机器人上放两台相机，是最便宜的被动度量深度源.

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED. arXiv ID UNVERIFIED.
**Wedge tier:** W2 · metric-depth foundation (stereo)
**TL;DR:** FoundationStereo (NVIDIA 2024, `[arXiv link TBD]` UNVERIFIED) 是把对 Depth Anything 和 VGGT 都有效的"在巨量合成上训、到处零样本"配方应用到立体的答案. 它在跨域零样本泛化上击败 RAFT-Stereo (Lipson et al. 2021) 谱系 — Middlebury、KITTI、ETH3D、野外 — **无需 per-domain fine-tune**. 对机器人这是无 LiDAR 得到 *metric* 深度最便宜的方式：若能在机器人上放两台已知 baseline 的相机，FoundationStereo 开箱给你米. 重要的是 Jetson 可部署性.

### X-Ray (non-expert friendly)

(a) 立体单凭几何给 metric 深度（`Z = f·B/d`）；历史问题是*匹配*（无纹理、重复、遮挡）. RAFT-Stereo / SGBM 需 per-domain 调. (b) FoundationStereo 把 Depth Anything 配方带到立体：foundation-feature 骨干 + 大合成语料库 → 零样本泛化. (c) 对空间 AI 工程师：最便宜的被动 metric 深度 — global-shutter 立体 + FoundationStereo + VIO 是可信的 2026 drone 栈.

### 📍 Research Landscape Timeline

```
SGBM 2005 ─► PSMNet 2018 ─► RAFT 2020 ─► RAFT-Stereo 3DV 2021 ─► ★ FoundationStereo NVIDIA 2024 ─► distilled/edge variants 2026+ ─► fused with monocular metric 2027+
```

FoundationStereo 把 foundation-model 配方应用到立体匹配. 下游开放：边缘蒸馏 + 在同一 feed-forward 骨干下与 monocular Metric3D 融合.

---

## 1 · 为什么立体 foundation 模型对机器人重要

立体是唯一无需 monocular 技巧就 metric 的被动光学深度法. Baseline + 已知校准 → 三角化 → 米，结束. **历史问题不是几何，是匹配** — 跨无纹理墙、重复花纹（砖、瓷砖、围栏）和遮挡边界找对应. 经典 block-matching（OpenCV SGBM）处理良性场景；RAFT-Stereo 谱系推精度但仍需 per-dataset fine-tune 才能泛化.

FoundationStereo 把 foundation-model 配方 — **海量合成训练语料 + 尺度不变特征骨干 → 零样本泛化** — 带到立体匹配. 赌注与 Depth Anything 同：合成数据现已够好，强预训练骨干（视觉 transformer 或卷积）足够鲁棒，使 per-domain fine-tune 不再必要. 对机器人这是巨大的 — 放上立体 rig，得米，无 scene-specific 校准环.

> ⚡ **Eureka Moment**: 立体精度的瓶颈是*特征质量*，不是 cost-volume 架构. RAFT-Stereo 的 GRU-迭代精化已强 — 但需 per-domain fine-tune 因为特征编码器训在小立体数据集上. **换上 foundation-feature 骨干（DINOv2 / EDM-style 在互联网图像上预训练），per-domain 调消失.** 架构留在 RAFT-Stereo 谱系；变的是前端.

---

## 2 · 配方

> 📌 **Napkin Formula**: `Z = f · B / d`，`d = StereoMatcher(left, right; foundation_features)`. 一旦有正确 disparity，metric depth 是几何（校准 baseline + focal length）；贡献是让 disparity 零样本准确.


| Component | Choice |
|---|---|
| Architecture | RAFT-style 迭代精化 + foundation feature 骨干 `UNVERIFIED specifics` |
| Pretrained backbone | DINOv2 / EDM-style image features `UNVERIFIED which` |
| Training data | 大型合成立体语料库 (SceneFlow-scale + 域混合) `UNVERIFIED size` |
| Cost volume | 多尺度、稀疏相关 |
| Inference | 迭代 GRU 更新，~12–32 iterations |

```
left  ──► foundation encoder ──┐
                                ├──► cost volume ──► GRU-iter refinement ──► disparity
right ──► foundation encoder ──┘                                              │
                                                                              ▼
                                                                      Z = f · B / d  (metric)
```

贡献双管齐下：**(1) 编码器在互联网规模图像上预训练**让特征扛域偏移，**(2) 合成训练语料库够大够多样**让匹配网络学到泛化的 disparity 先验. 架构上这是 RAFT-Stereo 谱系配更聪明的前端.

---

## 3 · 为什么击败 RAFT-Stereo

| Axis | RAFT-Stereo (2021) | FoundationStereo (2024) |
|---|---|---|
| Zero-shot 泛化 | 无 fine-tune 弱 | 无 fine-tune 强 |
| 无纹理表面 | 吃力 | 处理 `UNVERIFIED magnitude` |
| 部署复杂度 | per-rig fine-tune | 已知 baseline 即可放入 |

胜利不是新架构 — 是把 foundation-model 配方应用到立体. 对离线 mapping 答案是 "换". 对 >50 Hz 闭环控制，换前验证 Jetson 延迟 — RAFT-Stereo 有多年边缘硬件优化.

---

## 3.5 · Worked example — drone 立体在 5 m

1 kg drone，10 cm baseline global-shutter 对，`f ≈ 600 px` UNVERIFIED，Orin Nano.

- **在 5 m**: `d = f·B/Z = 12 px`；亚像素 ~0.1 px → 精度 ~0.04 m UNVERIFIED.
- **在 30 m**: `d = 2 px` → 精度 ~1.5 m. 范围按几何塌缩.
- **延迟**: 12 iter 时 ~50 ms / pair UNVERIFIED → ~20 Hz，适合控制环.
- **失败**: 无纹理天花板 / 重复围栏降匹配器置信；回落到 IR 投射.

立体短距精确，二次退化；与 monocular metric 配长距.

---

## 4 · 它在哪里 break

- **无纹理表面** — 比 RAFT-Stereo 好，仍非完美. 主动立体（投射图案）在此无视匹配器质量取胜.
- **重复花纹**（砖、瓷砖、围栏）— 匹配器锁错周期. Foundation 模型帮忙，不消除.
- **镜面反射** — 左右见不同高光 → 无对应.
- **长距下短 baseline** — 几何 SNR 塌缩（5 cm baseline → 10 m 处 ~1% disparity 精度，30 m 处猜测）. 无匹配器能修.
- **快速运动下 rolling-shutter** → 假 disparity. drone / 竞速用 global-shutter.
- **边缘算力成本** — Jetson Nano 上 32 GRU 迭代非实时 `UNVERIFIED actual numbers`.

### 4.x · Hidden Assumptions

上游假设，违反就破 metric 输出：

- **准确校准**（baseline + 内参 + rectification）— 误差线性传播；主导噪声源.
- **同步 global-shutter** — 运动下 rolling shutter → 假 disparity.
- **足够纹理** — 无纹理 / 重复甚至降级 foundation features；IR 投射帮忙.
- **Baseline-to-range 比** — 几何；长距下短 baseline 无视匹配器塌缩.
- **Lambertian 表面** — 镜面高光左右不同 → 无对应.
- **In-distribution 域** — 水下 / 仅 IR 需 fine-tune.

违反时得到看着合理的 metric 深度但有静默几何误差 — 在长距尤其差，因为 disparity SNR 本来就弱.

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

NVlabs/FoundationStereo 83 open issues 印证 §X.3.3 "无 confidence map" 的部署灾难是真实痛点：

- **GitHub-validated（关键发现）**：**[issue #121](https://github.com/NVlabs/FoundationStereo/issues/121) 多帧静止物体头部对齐但身体散开** —— stereo 预测有 **spatial heteroscedasticity（非均匀 spatial bias）**，但模型不输出 confidence → 下游融合无法 weighted fuse、grasp planner 用差像素作决策。**issue 已 closed 但根因未解（closed-without-fix 典型）** —— 这是 FoundationStereo 当前公开版本最大的部署债务，对 robot 是"身体能抓但头部位置不准"的灾难；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#5--foundationstereo--没-confidence-map-的-stereo-旗舰)。
- **GitHub-validated**：**TensorRT engine 输出 NaN（fp16）** —— 对应 [issue #49](https://github.com/NVlabs/FoundationStereo/issues/49) / [#175](https://github.com/NVlabs/FoundationStereo/issues/175)；ONNX export 缓慢（[#58](https://github.com/NVlabs/FoundationStereo/issues/58)）—— 同根：`flash_attn` export 路径 bug；Jetson Orin / camera K 输入格式问题（[#136](https://github.com/NVlabs/FoundationStereo/issues/136) / [#26](https://github.com/NVlabs/FoundationStereo/issues/26)）—— 印证 §3 "换前验证 Jetson 延迟" 警告。
- **GitHub-validated**：synth→real KITTI 室外差（[#102](https://github.com/NVlabs/FoundationStereo/issues/102)，训练合成室内主导）+ 大 baseline drift（[#142](https://github.com/NVlabs/FoundationStereo/issues/142)，~15 cm 对比 RGB-D ~5–7 cm）—— 印证 §X.2.6 sim-to-real gap 在 contrarian niches 上仍需 fine-tune；空 disparity / rectify 错（[#104](https://github.com/NVlabs/FoundationStereo/issues/104)）+ 视频闪烁（[#59](https://github.com/NVlabs/FoundationStereo/issues/59)）。**部署端最被低估的工程债务 = 自己加 LR consistency check + confidence head fine-tune**。

---

## 5 · 部署模式

- **Drone 上 Global-shutter 立体 + FoundationStereo** — 户外障碍距离，metric，无 LiDAR. &lt;1 kg 检测 drone 甜蜜点.
- **立体 + 主动 IR 投射 + FoundationStereo** — 室内 manipulation；投射填无纹理表面.
- **离线 mapping** — 全迭代次数，最佳精度，任务后批处理.
- **混合：60 Hz RAFT-Stereo 控制 + 5 Hz FoundationStereo 建图** — 与 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 中 VGGT + VIO 同模式.

Jetson 粗略数字（始终对实际 rig 做基准）：Orin Nano 在 640×480 减少迭代 ~10–20 Hz `UNVERIFIED`；Orin AGX 在 1280×720 ~30 Hz `UNVERIFIED`；Xavier NX 勉强，可能需蒸馏 `UNVERIFIED`.

---

## 6 · 2-year outlook + falsifiable prediction

立体 foundation 模型与 monocular depth foundation 模型乘同一波浪 — 合成 + foundation 骨干 → 零样本泛化. 接下来两年会有：

1. 蒸馏到 Orin Nano 上 &lt;10 ms（与 VGGT-distilled 轨迹类似）
2. 与 monocular metric 模型融合 — "baseline 好处用 FoundationStereo，一相机遮挡时回落 Metric3D"
3. 集成进多视角 feed-forward 3D — VGGT 谱系已把立体作为多视角特例吸收

**Falsifiable prediction:** 2027-06 前，至少一个公开 drone autonomy 栈（Skydio 级或开源）将发 FoundationStereo 谱系模型作为主要立体匹配器. 若到 2027 都留在经典 SGBM 或 RAFT-Stereo 则预测失败.

**Interview Tip**: 被问 "立体 vs monocular metric 深度"，正确答案：*"不同失败模式 — 立体在无纹理 / 镜面 / 长距短 baseline 失败；monocular 在错内参 / 域偏移失败."* FoundationStereo 是零样本立体答案；在立体几何塌缩处（长距、遮挡相机）与 Metric3D 配. 别二选 — 融合.

---

## For the reader

- **Manipulation engineer** — 室内无纹理配主动 IR；否则 RealSense pipeline 够.
- **Aerial engineer** — 最便宜的 metric 深度源. Global-shutter 立体 + FoundationStereo + VIO 是可信的 2026 栈.
- **AD engineer** — 仅作为立体匹配器的候选替换，不是整个栈.
- **Researcher** — 合成语料库配方是教训，同 Depth Anything v2.

---

---

## X.1 · Working Range 详细分析 (Working Range Deep Dive)

> 📌 **Napkin Formula 复述**：`Z = f · B / d`. 给定亚像素匹配误差 `ε_d`，**深度误差 `ε_Z ≈ Z² · ε_d / (f · B)`** — 这是立体几何最重要的一个事实：**深度误差与距离的平方成正比，与 baseline 和 focal 成反比**（来源：[Teledyne Vision Solutions / John Lambert stereo notes](https://johnwlambert.github.io/stereo/)）.

### X.1.1 物理约束：baseline × focal × disparity 三角关系

立体的精度账只看三个旋钮：

| 旋钮 | 调大的好处 | 调大的代价 |
|---|---|---|
| **Baseline `B`** | 远距离精度线性提升；`ε_Z ∝ 1/B` | rig 更大更重；近距 FOV overlap 减小；rolling shutter / 同步要求更严；calibration drift 影响放大（见 §X.2.5） |
| **Focal `f`** | 远距离精度线性提升；`ε_Z ∝ 1/f` | FOV 变窄；近距盲区扩大；像素小则 SNR 变差 |
| **亚像素匹配 `ε_d`** | foundation 模型把 `ε_d` 从经典 SGBM 的 ~0.5 px 推到 ~0.1 px 量级 `UNVERIFIED 具体数字` | 推不到 0 — disparity aliasing / textureless 是地板 |

设计 stereo rig 时这三个旋钮是死锁的：增 `B` 让远距精度变好但近距 overlap 变小；增 `f` 让远距精度变好但 FOV 变窄. 没有"一个 rig 通吃" — 必须按任务的 working range 选.

### X.1.2 近 / 中 / 远 三档 working range 与 baseline 的关系

按 `ε_Z = Z²·ε_d / (f·B)` 走三档量级（设 `f = 600 px`, `ε_d = 0.1 px` 亚像素）：

| Range tier | 典型距离 | 推荐 baseline | 估算深度精度 `UNVERIFIED 具体数字` | 典型应用 |
|---|---|---|---|---|
| **近 (Near)** | 0.2–1 m | 3–5 cm | ~0.5 mm @ 0.5 m | 桌面 manipulation, bin-picking |
| **中 (Mid)** | 1–5 m | 5–15 cm | ~3 cm @ 3 m | 室内导航, AGV, drone 室内 |
| **远 (Far)** | 5–30 m | 20–60 cm | ~50 cm @ 20 m | 户外 drone, AD perception |
| **超远 (Ultra-far)** | >30 m | >1 m 或 multi-baseline | 米级 | 测绘, satellite stereo |

### X.1.3 实际 rig 对照（验证 spec）

| Rig | Baseline | 实测 working range | 来源 |
|---|---|---|---|
| **Intel RealSense D435** | **50 mm** (5 cm) | 默认 0.2–10 m；**3 m 后精度明显漂移**；`<2%` @ 2 m | [Intel D435 specs](https://www.intel.com/content/www/us/en/products/sku/128255/intel-realsense-depth-camera-d435/specifications.html) |
| **Skydio R10** (室内 drone) | UNVERIFIED specific mm — two stereo navigation cameras 提供 180° FOV | 室内 close-quarters | [Skydio R10](https://www.skydio.com/r10) |
| **Skydio 2/2+** | 用 6 颗 4K hemispherical 相机 ring；非传统单 baseline stereo | 36 mph 速度下障碍回避 | [DroneDJ Skydio](https://dronedj.com/2019/10/01/skydios-obstacle-avoidance-self-flying-capability/) |

> **注意**：「Skydio 25cm baseline 适合 5-20m 户外」是 illustrative — Skydio 实际用的是多相机环阵列而非单 baseline pair `UNVERIFIED specific Skydio baseline`. 这正说明户外长距 drone 不靠单大 baseline，而靠多视角融合（与 VGGT 谱系合流）.

### X.1.4 disparity 量化的近-远误差不对称

`ε_Z ∝ Z²` 这个二次律的实际后果：

- **近距（high disparity, e.g. d = 100 px）**：1 px 匹配误差 → ~1% 深度误差. 近距是 stereo 的甜蜜点 — 精度甚至超过低端 ToF.
- **远距（low disparity, e.g. d = 2 px）**：1 px 匹配误差 → ~50% 深度误差. 远距 disparity 落到亚像素地板 — 再好的 foundation 模型也救不了几何 SNR.

§3.5 走 5 m / 30 m 的玩具例子（5 m → 12 px → ±0.04 m；30 m → 2 px → ±1.5 m）正是这个二次律的直观演示. **工程结论**：选 baseline 时按你最远要看的距离选，不是按最近 — 远端的几何 SNR 决定 rig 能不能用.

---

## X.2 · Sensitivity 详细分析 (Sensitivity Deep Dive)

FoundationStereo 在合成数据 + foundation 骨干加持下大幅缓解了 RAFT-Stereo 谱系的失败模式，但**几何决定的物理失败模式无法被任何匹配器消除**. 下面按敏感度从高到低排.

### X.2.1 Textureless 场景（白墙 / 雪 / 沙 / 镜面玻璃）

- **机制**：左右图像在大片区域内 patch 同质 → 匹配代价函数无 unique minimum → disparity 随机.
- **Foundation 模型帮助**：foundation features 携带 semantic prior，能从全局 context 推断"这是一面墙，深度连续" — 比 SGBM 的 local block matching 鲁棒. 但仍非完美.
- **2026 buyer's guide**：室内 manipulation 配主动 IR 投射器（D435 / D455）把"无纹理"变"有纹理"，foundation 模型在 projected pattern 上跑得很好（见 §5 部署模式）.

### X.2.2 光照不一致 / 曝光不对称

- **机制**：两相机 auto-exposure 不同步 → 同一表面在左右图亮度不同 → 标准 photometric cost 失效.
- **Foundation 模型帮助**：foundation features 多数学过对比度归一化（DINOv2 / Depth Anything 训练目标），鲁棒性比 raw photometric 高一档.
- **工程实践**：始终硬件锁定曝光（hardware-synced exposure trigger），不靠模型补.

### X.2.3 遮挡（左右目看不到同物）

- **机制**：物体在左目可见但被前景遮在右目（或反之）→ 该像素无 valid disparity.
- **Foundation 模型帮助**：训练数据含合成遮挡边界 → 模型学到"在遮挡区填合理深度". 但**填的是 hallucination 不是测量**.
- **关键**：foundation stereo **不显式输出 occlusion mask** `UNVERIFIED — 见 §X.3.3`. 下游不知道哪些像素是 measured / hallucinated → 是隐藏的 silent failure.

### X.2.4 重复纹理（铁丝网 / 牆磚 / 周期围栏）— Disparity Aliasing

- **机制**：周期 pattern → cost volume 有多个 local minima → 匹配器锁错周期 → 整片区域深度跳变.
- **Foundation 模型帮助**：长程 context 推理（FoundationStereo 论文明确点这是改进项，[arXiv 2501.09898](https://arxiv.org/abs/2501.09898)）能用全局一致性破开周期歧义. 但**重复 pattern 占整图 >50% 时仍崩**（仓库墙、整片瓷砖地）.
- **传统解法**：random-pattern IR 投射打破周期；主动立体在此完胜被动.

### X.2.5 Camera Calibration Drift — 物理震动让 baseline 变

这是 drone / AGV 上最被低估的失败源：

- **机制**：温度 / 震动 / 撞击让两相机相对外参（旋转 + 平移）漂移. 即使 ε_R 是 0.1° 量级，在远距 disparity ≈ 几 px 时也会让 epipolar rectification 失效 → 整图深度系统性偏 → 标定误差**线性传播到 metric 输出**（见 §4.x Hidden Assumptions）.
- **量级**：drone 平均漂移 ~0.024 m per m flown ([source](https://pmc.ncbi.nlm.nih.gov/articles/PMC9921183/))；IMU 在 >30°C 校准时漂移多 12% (引用同源).
- **工程对策**：(1) 鋼性 rig + 热补偿；(2) **在线自校准**（continuous stereo self-calibration，[KIT 论文](https://www.mrt.kit.edu/z/publ/download/dangStillerHoffmannTIP09.pdf)）；(3) 飞前 calibration check / 飞中残差监控. FoundationStereo 本身不做这个 — **它假设 rectified + 已知 baseline**（GitHub repo 明确要求 intrinsic file，见 [NVlabs/FoundationStereo](https://github.com/NVlabs/FoundationStereo)）.

### X.2.6 Synthetic vs Real Domain Gap

FoundationStereo 训在 **1M 合成立体对**（FSD Dataset，[paper](https://arxiv.org/abs/2501.09898)）+ 自动 self-curation pipeline 去模糊样本. 论文核心 contribution 是 side-tuning feature backbone 从 vision foundation models（Depth Anything V2 谱系）借 monocular priors 缓解 sim-to-real gap.

- **已验证泛化**：Middlebury / ETH3D 拿到 1st place leaderboard `UNVERIFIED current rank as of 2026-05`.
- **未充分验证**：水下 / 仅 IR / 夜视 / 极端动态范围（HDR）等 out-of-distribution 域 — 这些场景下 monocular prior 本身就弱，stereo 也会跟着崩.
- **教训**：合成训练 + foundation features 把"通用域"打开，但 contrarian niches（水下、镜面、IR-only）仍需 domain-specific fine-tune.

---

## X.3 · Interpretability (可解释性 / 可信度 / Graceful Degradation)

### X.3.1 输出格式：disparity vs depth

FoundationStereo 原生输出 **disparity map**，需用户提供 `baseline (meters)` 和 `intrinsic matrix` 后转 metric depth（GitHub 文档明确：`--intrinsic_file` 含 flattened 1x9 内参 + baseline meters，[repo](https://github.com/NVlabs/FoundationStereo)）.

| 量 | 误差性质 | 备注 |
|---|---|---|
| **Disparity (px)** | 网络直接输出；亚像素插值后约 0.1 px 量级 `UNVERIFIED` | 与场景 / 模型相关 |
| **Depth (m)** | `Z = f·B/d`；误差按二次律放大（§X.1.4） | 受 calibration 精度直接影响 |

**精度损失**：disparity → depth 是确定性变换（无信息损失），但**任何 baseline / focal 不确定性都进 metric depth**. 5% baseline 标定误差直接给 5% 系统性深度偏差.

### X.3.2 米制 vs 相对

- **Stereo 天然米制**：baseline 是已知物理量（标尺 / mechanical CAD），不像 monocular depth 需要 scale recovery hack（学度量 prior / 已知物体 / GPS-IMU 融合）.
- **但米制是 fragile**：baseline 标定误差 / drift 直接污染米制（§X.2.5）. **"米制 = 一次校准就能信"是误解** — 米制需要 ongoing calibration monitoring.

### X.3.3 不确定性 / Confidence Map

**关键发现**：根据 paper ([arXiv 2501.09898](https://arxiv.org/abs/2501.09898)) 和 GitHub repo（[NVlabs/FoundationStereo](https://github.com/NVlabs/FoundationStereo)）公开文档，**FoundationStereo 不显式输出 confidence map 或 occlusion mask** `UNVERIFIED — 仅基于公开文档检索；未排除 derived signal 可用`.

- **后果**：下游融合（与 mono depth、LiDAR、VIO 融合时）无法做 per-pixel 加权；只能整图 trust 或不 trust.
- **绕路**：(1) 用左右一致性检查（LR check）自己算 occlusion mask；(2) 用 GRU iteration 收敛速度作 proxy confidence `UNVERIFIED feasibility`；(3) 等社区做 confidence head fine-tune.

对照：经典 SGBM 有 cost peak ratio 当 confidence；RAFT-Stereo 出 GRU hidden state 可 probe；FoundationStereo 当前公开版本在这点上**比经典 baseline 还更不可解释**.

### X.3.4 与其他 depth 工具对比的"可解释度"

| 工具 | Metric? | 显式 confidence? | 几何可解释度 | Silent failure 风险 |
|---|---|---|---|---|
| **FoundationStereo** | Yes (geometry-grounded) | **No** | 高（disparity 物理可验证） | 中（无 confidence head） |
| **Depth Anything V2** (mono relative) | No (relative only) | No | 低（黑盒神经网络） | 高（hallucination） |
| **Metric3D** (mono metric) | Yes (learned prior) | No | 低（学到的尺度先验） | **高**（错内参 → 系统性偏） |
| **LiDAR** (e.g. Livox) | Yes (TOF) | Yes (intensity / multi-return) | **最高**（每点 ToF 测量） | 低（fail loud：无点云） |
| **Active stereo (D435)** | Yes | Partial (IR pattern strength) | 高 | 中 |

**Stereo geometry-grounded 优势**：disparity 物理量可独立用 epipolar geometry 验证 — 给定 left/right image，人能可视化是否对齐. Monocular metric 没这种 sanity check.

**Stereo 劣势**：无 confidence head → 不知道哪些 disparity 是 textureless / occluded 的 hallucination.

### X.3.5 失败的 Graceful Degradation — Clear Fail vs Silent Fail

| 失败模式 | Clear or Silent | 下游可检测吗 |
|---|---|---|
| 同步丢失 / 一相机黑屏 | **Clear** | Yes — image 全黑 / timestamp 不齐 |
| Rectification 失效（大 calibration drift） | **Silent** → eventually Clear | epipolar residual 监控可早发现；不监控就 silent |
| Textureless 大片墙面 | Semi-silent | disparity 平滑而无 confidence → 下游可能信 hallucination |
| 重复纹理 aliasing | **Silent** | 整片区域跳到错周期；图看着合理 |
| 长距 disparity SNR 塌缩（§X.1.4） | Semi-silent | 几何上可预期（按 `ε_Z ∝ Z²`），但 per-pixel 不知具体 z |
| Specular / mirror | Semi-silent | disparity 在镜面区域随机；下游需 saturation detector 标识 |
| 域外（水下 / IR-only） | **Silent** | 模型给"看着合理"的 disparity 但内部一致性低 |

**工程建议**：在 FoundationStereo 输出端**至少加 LR consistency check + 远距 mask + saturation mask**，把 silent failure 转 clear failure. 这是当前 foundation stereo 用作生产组件时**最被低估的工程债务**.

---

## References

- FoundationStereo — Wen, Trepte, Aribido, Kautz, Gallo, Birchfield (NVIDIA), *CVPR 2025 Best Paper Nomination*. https://arxiv.org/abs/2501.09898 · code: https://github.com/NVlabs/FoundationStereo
- Stereo depth-error quadratic law (`ε_Z = Z²·ε_d / (f·B)`) — John Lambert stereo notes. https://johnwlambert.github.io/stereo/
- Continuous stereo self-calibration — Dang, Stiller, Hoffmann, TIP 2009. https://www.mrt.kit.edu/z/publ/download/dangStillerHoffmannTIP09.pdf
- Variable-baseline aerial stereo (drone drift ~0.024 m/m flown) — PMC 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC9921183/
- Intel RealSense D435 specs (50 mm baseline · 0.2–10 m · &lt;2% @ 2 m). https://www.intel.com/content/www/us/en/products/sku/128255/intel-realsense-depth-camera-d435/specifications.html
- Skydio R10 (室内 stereo nav, 180° FOV). https://www.skydio.com/r10
- RAFT-Stereo — Lipson et al. *3DV 2021*. https://arxiv.org/abs/2109.07547
- RAFT (optical flow 起源) — Teed & Deng *ECCV 2020*. https://arxiv.org/abs/2003.12039
- SGBM — Hirschmüller *CVPR 2005*（经典 baseline）. no arXiv
- Depth Anything v2（配方对照）— 见 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md)
- VGGT（多视角 feed-forward，吸收立体）— 见 [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](../feed-forward-3d/vggt_cvpr2025_dissection.md)

## Boundary

本文把 FoundationStereo 作为立体匹配基础模型解构. Monocular metric depth 在 [`metric3d_dissection.md`](./metric3d_dissection.md). Monocular relative depth 在 [`depth_anything_v2_dissection.md`](./depth_anything_v2_dissection.md). 跨 embodiment scale 对比在 [`crossing/scale-comparison/`](../../crossing/scale-comparison/). "立体作为经典 VIO 下的低速 metric 锚" 模式是 [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](../../crossing/slam-vio-migration/vggt_vs_drone_vio.md) 中混合的特例. 到 action policy 的桥在 [`bridge-to-vla/feature-cloud-to-action.md`](../../bridge-to-vla/feature-cloud-to-action.md).
