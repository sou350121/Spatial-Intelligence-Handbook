# Siamese 到 Transformer 到 SAM 2：单物体 Tracking 八年演进 (Siamese → Transformer → SAM 2: Eight Years of Single-Object Tracking)

> **发布时间**: SiamFC — ECCV 2016 / arXiv 1606.09549 · SiamRPN — CVPR 2018 · SiamMask — CVPR 2019 / arXiv 1812.05050 · SiamRPN++ — CVPR 2019 · STARK — ICCV 2021 / arXiv 2103.17154 · MixFormer — CVPR 2022 oral / arXiv 2203.11082 · SAM 2 — Meta 2024 / arXiv 2408.00714
> **论文 / 模型**: SiamFC · SiamRPN · DaSiamRPN · SiamMask · SiamRPN++ · STARK · MixFormer · OSTrack · SAM 2
> **核心定位**: **Single Object Tracking (SOT)** — 给定第一帧 bbox，在后续视频中追踪同一个 instance. 2016 后的 deep tracker 谱系（visual tracking 真正变 "深"）—— 与 MOT (multi-object) 是不同问题；与 CSRT 类 CF tracker 是不同 weight class.

**Status:** v1 — 带立场的初稿. 数字除非在 rig 上测过否则标 `UNVERIFIED`.
**Wedge tier:** W1 · 现代 visual SOT 的主干 — drone follow / 监控 re-track / 体育转播 / Skydio ActiveTrack 类应用全部走这条线.
**TL;DR.** 2016 SiamFC 第一次用 *端到端学到的相似度* 替代手工 correlation filter，在 GPU 上 ~80 FPS. 之后五年是 *给 Siamese 加配件* 的演化：RPN（box regression）→ Mask（pixel-level）→ ResNet-50 backbone → Transformer encoder-decoder（STARK）→ joint feature-extraction-and-matching（MixFormer / OSTrack）. 2024 SAM 2 把 *video segmentation + tracking 统一* 在一个 promptable 框架里 — VOT 范式被 video VFM 重写.

**X-Ray.** Siamese 的核心想法：把"是不是同一个 object"做成 *learned similarity*. 训练时给一对 patch（template + search），让网络学到与目标看似 / 不似的判别. 测试时拿第一帧 patch 当 template，每一新帧 cross-correlate. 8 年演进可归纳为：**(a)** 怎么把 box 估准 — anchor → anchor-free → corner head；**(b)** 怎么挑 backbone 不破坏 translation invariance — AlexNet → ResNet（SiamRPN++ 解决）→ ViT；**(c)** 怎么在线适应 — template 固定 → 动态 update → memory bank（SAM 2）.

---

## 📍 研究全景时间线

```
2016        2018         2019            2020-21       2022             2024
SiamFC ──► SiamRPN ───► SiamRPN++/Mask ► STARK/Trans ► MixFormer/OST ► SAM 2 (mask + memory)
└─ learned similarity ─┘  └── deep backbone + RPN ─┘ └── transformer joint matching ─┘ └─ video VFM ─┘
└────── CNN era ────────────────────────────────────┘└─── transformer SOT era ────┘  └ VFM era ┘
```

三个 era 的转折点：2018 SiamRPN（anchor box regression）、2021 STARK（transformer 入侵 SOT）、2024 SAM 2（promptable video segmentation 吞并 tracking）.

---

## 1 · 八年谱系：架构与 "发明了什么"

### 1.1 系统对比

| Model | Year | Backbone | Matching | Head | LaSOT AUC `UNVERIFIED` | Speed (V100) `UNVERIFIED` | 训练数据 |
|---|---|---|---|---|---|---|---|
| **SiamFC** | 2016 | AlexNet-like | Cross-correlation | Score map peak | ~33% | ~86 FPS | ILSVRC-VID |
| **SiamRPN** | 2018 | AlexNet | Depth-wise XCorr | RPN anchors | ~50% | ~160 FPS | ILSVRC-VID + DET |
| **DaSiamRPN** | 2018 | AlexNet | XCorr | RPN + distractor-aware | ~52% | ~160 FPS | + Youtube-BB |
| **SiamMask** | 2019 | ResNet-50 | XCorr | RPN + mask head | ~46% (+mask) | ~55 FPS | + COCO + DAVIS |
| **SiamRPN++** | 2019 | ResNet-50 | XCorr + 多层聚合 | RPN | ~50% | ~35 FPS | + LaSOT |
| **STARK** | 2021 | ResNet / ViT | Transformer enc-dec | Corner head + score | ~67% | ~42 FPS | + GOT-10k |
| **MixFormer** | 2022 | CVT / ViT | **Joint** mixed-attention | Pyramid corner | ~70% | ~25 FPS | + TrackingNet |
| **OSTrack** | 2022 | ViT | One-stream | Center / size head | ~71% | ~58 FPS | + TrackingNet |
| **SAM 2** | 2024 | ViT (Hiera) | Promptable + memory | Mask decoder | (mask, not bbox) | ~44 FPS / 1024² | SA-V (51K videos, 36M masklets) |

### 1.2 ⚡ Eureka Moment（三处）

> **(1) SiamFC (2016): "用 deep features 学 similarity 比手工 HOG correlation 高一截." (2) STARK (2021): "把 template 与 search 一起塞进 transformer encoder — cross-attention 同时处理 matching 与 contextual reasoning，不再分两步." (3) SAM 2 (2024): "video segmentation 是 tracking 的超集 — 用 memory bank + promptable mask decoder 一个模型吞掉两个任务."**

三处转折. 在 SiamFC 之前 visual tracking 是工程匠艺（CF + HOG），在 STARK 之前 Siamese 是 "backbone + 手工 head"，在 SAM 2 之前 video segmentation 与 SOT 是两个互不通信的子社区.

### 1.3 信息流（SiamFC vs STARK vs SAM 2）

```
SiamFC (2016):
   template patch z ─► CNN_φ ─► φ(z)  ┐
   search patch  x ─► CNN_φ ─► φ(x)  ─┼─► φ(z) * φ(x) (XCorr) ─► score map ─► argmax
   ───────────────────────────────────┘    （手工 head）

STARK (2021):
   z + x ─► CNN ─► tokens ─► Transformer encoder（cross-attn）
                                  │
                                  ▼
                             decoder query ─► corner head ─► bbox
                             score head ─► trust → 动态更新 z

SAM 2 (2024):
   prompt (click/box/mask) on frame_t ─► image encoder ─► memory bank ◄── prev frames
        │                                       │
        ▼                                       ▼
   mask decoder ──── output mask + visibility ── for every t
```

---

## 2 · 数学核心：Cross-correlation → Joint attention → Memory readout

### 📌 Napkin Formula

```
   SiamFC :  s(x, z)  =  φ(z) ⋆ φ(x)         # 单一 XCorr
   STARK  :  q  =  Attention( z_tok ⊕ x_tok )；bbox = HeadCorner(q)
   SAM 2  :  mask_t  =  Decoder( image_t, memory(prev t, prompt) )
```

| Symbol | Meaning |
|---|---|
| `φ(·)` | 共享 CNN 的特征图（Siamese 的"双胞胎"）|
| `⋆` | 2D cross-correlation（depth-wise / channel-wise variants）|
| `z_tok / x_tok` | template / search 经 backbone 后的 token 序列 |
| `memory` | SAM 2 的 streaming memory（每帧 mask + features 写入）|

**Intuition.** SiamFC 把 tracking 当 *逐帧 retrieve*：在新帧上找与 template 最像的位置. STARK 改成 *逐帧 reason*：让 template 与 search 在 cross-attention 里互相 condition，不只是相似度而是 "在 spatio-temporal 上下文里这个 object 在哪". SAM 2 改成 *逐帧 segment with memory*：把上文 frame 的特征作为 prompt 隐式注入，输出 pixel mask 而非 bbox.

### 关键区分：anchor vs anchor-free vs corner

- **SiamRPN** 用 anchor boxes（5 scales / aspect ratios per location），与 Faster-RCNN 同款 — 引入超参困境.
- **SiamRPN++** 用 ResNet-50 + spatial-aware sampling 解决 deep network *破坏 translation invariance* 的问题（论文核心贡献）.
- **STARK** 用 **corner head** — 直接预测 bbox 左上 + 右下 corner 的 heatmap，anchor-free.
- **OSTrack** 用 center + size 解耦头，**one-stream**（template 与 search 共享 encoder 不分两支）.

---

## 3 · 带数字走一遍：STARK 在 LaSOT 一段视频

设：1920×1080，目标骑车人，初始 bbox 100×200，搜索区 320×320.

1. **首帧.** Crop template 128×128，过 ResNet-50 → 16×16×256. 过 transformer encoder（template + search tokens 共 16² + 20² = 656 tokens）. ~12 ms `UNVERIFIED`.
2. **后续帧.** Search 区裁 320×320 → backbone → 20×20×256. 与 template tokens cat → transformer encoder. Decoder query → corner heatmap → bbox. ~10 ms / 帧 `UNVERIFIED`.
3. **Score-driven update.** STARK 的 score head 判 "当前 box 是否高置信"；> τ 即用此帧 patch 作为 *dynamic template*，下一帧 encoder 输入变 `template_init + template_dyn + search`. 关键设计 — 让 STARK 能在 appearance change 时仍跟得住，而不 drift.
4. **遮挡帧.** Score head 输出 < τ，*不* 更新 dynamic template，但仍输出 bbox（用历史 template）. 短遮挡能恢复.

桌面 V100 全帧 ~40 FPS `UNVERIFIED`. Jetson Orin TensorRT INT8 量化后 ~15 FPS `UNVERIFIED` — Skydio ActiveTrack 类应用的工程目标线.

---

## 4 · 工程视角：production 现状

### 4.1 工业级谁在用什么

| 场景 | 实际部署 | 原因 |
|---|---|---|
| **Skydio ActiveTrack / DJI ActiveTrack 5.0** `UNVERIFIED` | Siamese 变体 + IMU + depth fusion | GPU SoC 受限；轨迹平滑由控制层做 |
| **Hawk-Eye 体育转播 / VAR** `UNVERIFIED` | 多 camera + Siamese / MOT 混合 | 实时 + 多视角约束 |
| **监控视频 re-track** | YOLO + ByteTrack（MOT）+ 人工 click → SiamRPN++ / OSTrack | 检测重，SOT 补 ID 持续 |
| **影视后期 rotoscope / 抠像** | **SAM 2** 主流 | 一键 mask + 跨帧传播，Adobe / Runway 等已接入 |
| **研究 / VOT benchmark 刷榜** | MixFormer / OSTrack / SeqTrack / ARTrack | LaSOT > 70% AUC 是 2024 入门线 |
| **嵌入式 / CPU-only drone** | CSRT（看姊妹 dissection）+ optical flow re-detect | GPU 不可用 |

### 4.2 VOT challenge 谱系演进

| Year | 冠军 | EAO `UNVERIFIED` | Family |
|---|---|---|---|
| 2013-2015 | DSST / KCF / MUSTer | 0.2-0.3 | CF |
| 2016 | C-COT | ~0.33 | DCF + deep features |
| 2017 | CSR-DCF | ~0.34 | CF + reliability |
| 2018 | MFT (LADCF) | ~0.39 | Multi-feature CF |
| 2019-2020 | DiMP / D3S | ~0.45 | Online deep learning |
| 2021 | STARK-derived | ~0.52 | Transformer |
| 2022 | MixFormer | ~0.55 | Joint attention |
| 2023+ | VOT 转向 ST/RT(real-time) protocol；deep tracker 通吃 | — | — |

**关键 inflection points**：2016 deep features 进 CF；2018 RPN 让 box regression 准；2021 transformer 占领；2024 SAM 2 让 mask 任务吃 bbox 任务.

### 4.3 SAM 2 为什么是革命

| Axis | 经典 SOT (STARK / MixFormer) | SAM 2 |
|---|---|---|
| 任务 | bbox tracking | bbox / point / mask tracking + segmentation |
| Prompt | 第一帧 bbox（必须）| 任意帧任意 prompt（click / box / mask）|
| 中途 re-prompt | 不支持 | **支持** — 任意中间帧加点修正 |
| 输出粒度 | bounding box | per-pixel mask |
| 训练数据 | LaSOT + TrackingNet + GOT-10k ~10⁵ videos | **SA-V: 51K videos, 36M masklets** |
| 失败模式 | drift / 遮挡丢 | drift 但允许 mid-stream 修复 |
| 同一模型推图像? | 否 | 是（SAM 1 的超集）|

SAM 2 之后，新 SOT 论文很难再 *只* 在 LaSOT 刷 AUC — 评估必须包含 SAM 2 baseline. 这跟 2020 RAFT 之后 flow 论文都要跟 RAFT 比是同一性质的范式转移.

---

## 5 · Data & Eval

**Training benchmarks**（决定模型质量上限）:

- **GOT-10k** (arXiv 1810.11981): 10,000 training videos，**class disjoint** train/test split — 强迫 class-agnostic. 是 Siamese 系列 generalization 的关键 corpus.
- **LaSOT** (CVPR 2019): 1,400 videos, **3.52 M frames**, 平均 2,512 帧 / 视频 — 真正的 long-term benchmark.
- **TrackingNet** (ECCV 2018): 30,000+ videos, 14 M+ bbox.
- **SA-V** (SAM 2 论文 2024): **51K videos, 36M masklets** — 比所有 SOT 训练集合大一个数量级；mask-level 标注.

**典型 evaluation 指标**：

- Success / Precision plot（OTB style）.
- AUC（area under success curve）— LaSOT 主指标.
- EAO (expected average overlap) — VOT 主指标.
- J&F mean — DAVIS / video object segmentation.

⚠️ **仅 benchmark 警告**：LaSOT / TrackingNet 已被反复刷榜，70%+ AUC 论文每月数篇 — 真机 drone follow / 监控 deployment 的 *gap* 远大于论文 delta. SAM 2 在 SA-V test 上的数字（J 84%, F 81% `UNVERIFIED`）也是受控 evaluation.

---

## 6 · Capabilities & Failure Modes

**Capabilities.** 长时（minutes-scale）单物体追踪；class-agnostic（无需 per-category 训练）；遮挡 recovery（STARK score head / SAM 2 memory）；mask-level 输出（SiamMask / SAM 2）；mid-stream re-prompt（SAM 2 独有）.

**Failure modes.**
- **Distractor confusion**：相似 instance 进入 search region（足球场上换人、行人交错）— Siamese 无 re-ID.
- **大尺度变化**：zoom-out 让目标 < template 一半；scale estimation 在 STARK 之前不稳.
- **快速旋转 / out-of-plane**：template 与 search 几何不匹配，cross-correlation 响应低.
- **超长遮挡（> few seconds）**：dynamic template 已学到 occluder appearance；目标重现也认不出 — *无 global re-detection*.
- **多 instance 切换**：SOT 是 *one object only*；切到第二个目标需要重新 prompt（SAM 2 可处理但需 user prompt）.

### 6.1 Hidden Assumptions

- **目标在 search region 内**. 搜索区是 bbox × 2-4×；大跳跃出区即丢. Skydio 用 IMU 预测 search center 部分缓解.
- **第一帧 bbox 准确且 representative**. 初始 bbox 含太多背景 → template "学错"；过紧 → margin 不足 / robustness 差.
- **目标外观 piecewise smooth**. 突变（穿/脱衣、变形、灯光剧变）→ 即便 dynamic update 也跟不上.
- **Class-agnostic 仅在 training distribution 内**. 训练在 ILSVRC-VID + GOT-10k 上，extreme novel domain（医学、水下、显微）需要 fine-tune.
- **Memory bank 长度有限**（SAM 2）. 默认 ~7 frames + 1 init; 超长 video 早期信息会被挤出.

破坏时 tracker *仍输出 bbox* 但 lock 错目标 — 静默失败 + 下游 policy 接到错 bbox 不自知.

---

## 7 · 对比 + Interview Tip

| Tracker | Year | Family | LaSOT AUC `UNVERIFIED` | Anchor | 输出 | 训练 corpus 量级 |
|---|---|---|---|---|---|---|
| CSRT | 2017 | CF | ~24% | — | bbox | 第一帧 |
| SiamFC | 2016 | Siamese CNN | ~33% | none | score map | 10⁵ |
| SiamRPN++ | 2019 | Siamese + RPN | ~50% | anchor | bbox | 10⁵ |
| SiamMask | 2019 | Siamese + Mask | ~46% | anchor | bbox + mask | 10⁵ |
| STARK | 2021 | Transformer | ~67% | corner | bbox | 10⁵-10⁶ |
| MixFormer | 2022 | Joint attn | ~70% | corner | bbox | 10⁶ |
| OSTrack | 2022 | One-stream ViT | ~71% | center | bbox | 10⁶ |
| **SAM 2** | **2024** | **Video VFM** | (mask J&F ~80% on SA-V `UNVERIFIED`) | — | mask + visibility | **10⁷ masklets** |

> **🎤 Interview Tip.** "为什么 2024 后 SOT 论文都要跟 SAM 2 比？" — *"SAM 2 把 video segmentation 与 tracking 统一在 promptable 框架里：用 51K-video / 36M-masklet 的 SA-V dataset + memory bank 让一个模型既能 image-segment、又能 cross-frame propagate. 比 STARK / MixFormer 多一个维度（mask vs bbox）且支持 mid-stream re-prompt — 这是 traditional SOT 不可能的. 在 production 上 SAM 2 已经吃掉影视 rotoscope、Runway 类视频编辑；学术上它逼着 VOT 社区重新定义 protocol."* 别只背 LaSOT 排行榜.

---

## References

- SiamFC — *ECCV 2016 W*. Bertinetto et al. https://arxiv.org/abs/1606.09549
- SiamRPN — *CVPR 2018*. Li et al.
- DaSiamRPN — *ECCV 2018*. Zhu et al.
- SiamMask — *CVPR 2019* / TPAMI 2023. Wang et al. https://arxiv.org/abs/1812.05050
- SiamRPN++ — *CVPR 2019*. Li et al. https://arxiv.org/abs/1812.11703
- STARK — *ICCV 2021*. Yan et al. https://arxiv.org/abs/2103.17154
- MixFormer — *CVPR 2022 oral / TPAMI 2024*. Cui et al. https://arxiv.org/abs/2203.11082
- OSTrack — *ECCV 2022*. Ye et al. https://arxiv.org/abs/2203.11991
- SAM 2 — *Meta 2024*. Ravi et al. https://arxiv.org/abs/2408.00714
- GOT-10k benchmark — Huang et al. https://arxiv.org/abs/1810.11981
- LaSOT benchmark — Fan et al. https://arxiv.org/abs/1809.07845
- TrackingNet benchmark — Müller et al. https://arxiv.org/abs/1803.10794
- VOT challenge series — https://www.votchallenge.net/

## Boundary

**单物体 deep visual tracking 谱系**.
- CPU-only / pre-deep CF tracker → [`classical_visual_tracking_kcf_csrt.md`](./classical_visual_tracking_kcf_csrt.md)
- 密集 optical flow（非 bbox） → [`raft_optical_flow.md`](./raft_optical_flow.md)
- 稀疏长时点追踪（非 single object） → [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md)
- 6D 物体 pose（manipulation 用，非 2D bbox） → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md) / [`megapose_dissection.md`](./megapose_dissection.md)
- Drone ActiveTrack / Skydio 工程使用 → [`../../embodiments/aerial/active-tracking/`](../../embodiments/aerial/active-tracking/)
- Driving multi-object（不在本系列） → [`../../embodiments/driving/`](../../embodiments/driving/)
- Correlation 在图像空间的几何 → [`../spatial-math/camera_projection_view_geometry.md`](../spatial-math/camera_projection_view_geometry.md)

---

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to README](./README.md)
