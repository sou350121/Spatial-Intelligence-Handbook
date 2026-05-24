<!-- ontology-5axis
problem: Reference-Free Feed-Forward 3D (permutation-equivariant variant)
representation: Affine-invariant camera pose + scale-invariant local pointmap (no privileged anchor frame)
sensor: Multi-view RGB (unordered set)
paradigm: Learned-EndToEnd + Permutation-Equivariant attention (no reference token, no positional bias on view index)
time: Feed-forward batch (one-shot, order-independent)
ref: ../../cheat-sheet/ontology.md §5.2 / §13
-->

# π³ 解构 (Pi3 — Permutation-Equivariant Visual Geometry Learning)

> **发布时间**：2025-07 arXiv v1 / 2026-03 最新版 / ICLR 2026 accepted
> **论文 / 模型**：π³ (Pi3) — Yifan Wang, Jianjun Zhou, Haoyi Zhu, Wenzheng Chang, Yang Zhou, Zizun Li, Junyi Chen, Jiangmiao Pang, Chunhua Shen, Tong He
> **核心定位**：把 VGGT 谱系**继承自 SfM 的 reference-view 假设**砍掉 — 全 permutation-equivariant，输入顺序不影响输出，输出 affine-invariant pose + scale-invariant pointmap。
> **Status**: v1 — opinionated draft 2026-05-24。Latency / memory 數字標 `UNVERIFIED`。
> **Wedge tier**: W2 — handbook 第一篇 reference-free FF3D 解构。
> **TRL**: 🔬 research-only (ICLR 2026 brand new, ~10 個月內出)

**TL;DR**: VGGT / DUSt3R 整条谱系都默认「第一帧 = anchor」（一种 SfM 残留假设）— 任何 reference view 选错（模糊、动态、遮挡），整个重建塌。π³ 用**全 permutation-equivariant transformer**（每帧地位完全等价、view index 不进 attention bias）+ **scale-invariant 局部 pointmap**（每帧自己的尺度，不绑全局）打破这条假设。**ICLR 2026 accepted, 2k★ on GitHub**，但 72 open issue（含 #138 memory overflow / #135 GPU 间结果不一致 / #132 不同输入顺序结果不同）— 论文宣称 permutation-equivariant，issue tracker 显示**实测仍有顺序敏感性残留**，是 v1 阶段的典型 gap。⚠ Weights **CC BY-NC 4.0 非商用**。

---

## 📍 研究全景时间线 (X-Ray)

```
                        SfM 时代假设：必有一个 reference view
                                       ↓
CroCo (NeurIPS 2022) — pretext 配对 → DUSt3R (CVPR 2024, 2-view, reference=view1)
                                       ↓
                          MASt3R (ECCV 2024, +matching head)
                                       ↓
                          VGGT (CVPR 2025 best, N-view batch, reference=view1)
                                       ↓
                          VGGT-Ω (CVPR 2026 oral) — efficient + dynamic, **仍 reference=view1**
                                       ↓
                          StreamVGGT (ICLR 2026) — causal stream, **首帧 = anchor**
                                       ↓
                  ★ π³ / Pi3 (ICLR 2026) — **打破 reference 假设**
                                       ↓
                          Pi3X (2025-12) — 加 metric scale prediction 分支
                                       ↓
                          ???（2027+：reference-free + streaming + metric 三合一？）
```

**这条谱系的 reference 假设源头**：DUSt3R 把第一张图作 anchor pointmap，第二张图回归到第一张的坐标系。VGGT 沿用：N-view batch 里第一帧的 camera token 是 origin，pose head 输出的 R_i, t_i 都是 *相对* 第一帧。**StreamVGGT 加剧**：causal attention 让第一帧成为永久 anchor — 后续所有帧都 attend 它。

**π³ 是这条谱系第一篇正面攻击 reference 假设的工作**。

---

## 1 · X-Ray — 跟 VGGT batch 的核心架构差异

```
VGGT batch (有 reference):
  [I_1, I_2, ..., I_N]
    │   │       │
    ▼   ▼       ▼
  encode → tokens with view-index embedding [pos_1, pos_2, ..., pos_N]
                                       ↑
                                       │ 不同 view 不同位置编码
                                       │ → output 依赖 (view 1, view 2, ..., view N) 这个 ordering
                                       ▼
  bidirectional attention → {pose_i 相对 view1, depth_i, pointmap_i 全在 view1 坐标系}
                                       ↑
                                       │ view 1 = privileged anchor

π³ (permutation-equivariant, no reference):
  {I_1, I_2, ..., I_N}  ← set, not sequence
    │   │       │
    ▼   ▼       ▼
  encode → tokens **without** distinguishing view-index
                                       ↑
                                       │ 同一 token type，仅 spatial position 区分
                                       │ → swap any I_i ↔ I_j：output 也对应 swap
                                       ▼
  attention 等价于对 token set 操作（permutation-equivariant 设计）
                                       ▼
  {affine-invariant pose_i, scale-invariant local pointmap_i}
                                       ↑
                                       │ 没有「相对哪一帧」的概念
                                       │ pose 决定到一个 affine ambiguity
                                       │ 每帧 pointmap 各自的尺度（不绑全局）
```

**3 个架构替换**：

| 设计选择 | VGGT batch | π³ |
|---|---|---|
| View ordering | 第一帧 = origin / anchor | **set input — no ordering** |
| Attention 形式 | bidirectional + view-index embedding | **fully permutation-equivariant**（无 view-index bias） |
| Pose 输出空间 | 相对 view1 的 SE(3) | **affine-invariant**（解到 affine ambiguity，下游再 anchor） |
| Pointmap 输出空间 | 全局 view1 坐标系 dense pointmap | **每帧 local scale-invariant pointmap** |
| Robust to ref selection | ❌ 选错 ref 整个塌 | ✅ 不存在「选 ref」这个问题 |

---

## 2 · ⚡ Eureka Moment

> **「Feed-forward 3D 不需要 reference view — SfM 的 anchor 假设是历史包袱，丢掉它，输入顺序就完全无关。」**

整个 SfM / MVS 谱系（80s COLMAP → DUSt3R → VGGT）都假设需要一个「基准帧」来锚定全局坐标。这是因为 SfM 是 bundle adjustment 优化问题，必须 fix 7 个 gauge freedom DoF（global SE(3) + scale）。

**π³ 论证**：feed-forward 网络不做 BA 优化，没有 gauge freedom 问题 — 直接输出 *affine-invariant* pose（解到一个全局 affine）+ *scale-invariant* local pointmap（每帧自己的尺度），下游需要 metric 再用一个**轻量 anchor head**（Pi3X 做的事）。

**结果**：把「reference view 选什么」这个长期工程痛点（特别在动态场景 / 6-DoF aerial / multi-camera rig）从架构层消解。

---

## 3 · 📌 Napkin Formula

**Permutation equivariance 的数学条件**：

```
对任意 permutation σ：
  π³({I_σ(1), I_σ(2), ..., I_σ(N)})  ≡  σ ∘ π³({I_1, I_2, ..., I_N})

i.e.,  P_{σ(i)} = σ_pose ∘ P_i,   Map_{σ(i)} = σ_map ∘ Map_i
```

**Implementation napkin**：
- 不加 view-index positional embedding（spatial within-frame 还有）
- Attention 必须是 set-permutation-equivariant（self-attention 天然是；加 view-bias 就不是）
- Loss 函数对 view ordering 也对称

**Affine-invariant pose 的意义**：
```
True pose:    P_i ∈ SE(3) — 6 DoF
π³ output:    P_i 解到 affine transform A ∈ Aff(3) 的等价类
              i.e., 给定 ground truth, 存在 A 使 A P_i ≈ P_i^GT for all i
```
→ 下游若要 metric，需 ≥1 个 anchor（GT pose / IMU / RTK / known object）。这就是 Pi3X (2025-12) 加的 metric scale head 做的。

---

## 4 · 带数字走一遍 — Worked Example (Toy)

设定：4 张同一物体不同角度照片（典型 sparse-view object reconstruction）

**VGGT batch**：
- 选第一张做 anchor → 输出 {pose_1 = I, pose_2, pose_3, pose_4} 都相对 view1
- 若 view1 模糊 / 部分遮挡 → 后续 3 帧的 pose 全错 → pointmap 全塌
- 修复：要么手动选最好的 view 作 view1，要么跑多次 swap ordering 集成（成本 ×N）

**π³**：
- 4 张图 set 输入 → 输出 {pose_1, pose_2, pose_3, pose_4} affine-invariant + 4 个 local pointmap
- 模糊 view 自然降权（attention 学到），不会拖累其他 3 帧
- 任意顺序输入：输出对应顺序 swap，**几何结果一致**（理论上；实测见 §8 issue #132）

**Latency 推算**（与 VGGT 同级，`UNVERIFIED`）：
- 4 view @ 518px: ~200-500 ms on A100
- 4 view @ 224px: ~50-100 ms on RTX 4090
- per-frame cost 跟 VGGT 同数量级（架构没变，只去掉 ref bias）

---

## 5 · 工程视角：何时 π³ 比 VGGT 好

| 场景 | VGGT (with ref) | π³ (ref-free) |
|---|---|---|
| Sparse-view object scan（4-8 张同物） | 选 ref 是痛点 | ✅ **明显胜出** |
| Multi-camera rig（固定多相机阵列，无明显「第一帧」概念） | 强行选 ref 不自然 | ✅ **胜出** |
| Long video sequence | 自然有「第 1 帧」 | 等价 |
| Streaming / online | causal 必有第 1 帧 | π³ 是 batch，不适用 |
| Metric scale 需求 | 无（都不支持） | ✅ Pi3X 加 metric head |
| Edge deploy / real-time | 都不行 | 都不行 |

---

## 6 · 🚩 Hidden Assumptions

| 假设 | 看似合理 | 实际 |
|---|---|---|
| **「Permutation equivariance 在实测真成立」** | 论文证明数学等价 | ✅ GitHub **issue #132 反证**：「different result for different order」— 实测仍有顺序敏感性。可能源于：(a) BF16 累加非交换；(b) 实现里仍有隐藏 ordering bias；(c) attention numerical noise |
| **「Affine-invariant pose 下游容易补 metric」** | 加一个 head 就行 | Pi3X 做了，但 **metric scale prediction 准度未公开 benchmark**（issue #154 用户问技术细节） |
| **「输入 set 不依赖 N」** | 架构通用 | N 越大 attention O(N²) cost 越高；π³ 没解 streaming 问题（StreamVGGT 才解） |
| **「不同 GPU 结果一致」** | 推理 deterministic | **issue #135 反证**：「不同显卡上的推理表现存在差异」 |
| **「Scale-invariant local pointmap 够用」** | 局部 + 下游 fuse | 多 view 间需要额外 alignment 步骤 — π³ 没在 paper 里写明 alignment 协议 |
| **「替代 VGGT」** | 看起来是 upgrade | π³ 没解 streaming / metric / dynamic，**与 VGGT-Ω / StreamVGGT / MapAnything 是正交改进**，不是替代 |

---

## 7 · 🎤 Interview Tip

> **「π³ 出来了，VGGT 是不是要被换掉？」**
>
> 正确答：「π³ 是 VGGT 谱系**第一篇打破 reference-view 假设**的工作 — 全 permutation-equivariant + affine-invariant pose。**关键 use case**：sparse-view object scan、multi-camera rig 这种没有自然『第一帧』的场景。但它跟 VGGT-Ω（efficient + dynamic）/ StreamVGGT（streaming）/ MapAnything（metric）是**正交改进**，不是替代 — 一个理想下一代 FF3D 应是『permutation-equivariant + register attention + factored metric + streaming』四合一，2027 前可能出现。**生产实测 caveat**：GitHub issue #132 显示实测仍有顺序敏感性残留（可能 BF16 / numerical 原因），论文宣称的严格 equivariance 与实测有 gap。」
>
> 错答：「permutation-equivariant 是 paradigm shift，VGGT 过时了」 — 单轴改进，四件套互补。

---

## 8 · 🔁 Atlas 联动 — GitHub-validated 失败模式

→ 详见 [`github_failure_atlas.md`](./github_failure_atlas.md)

**GitHub-VERIFIED issues**（2026-05-24, 72 open / 2k★ / 153 fork）：

| 失败模式 | GitHub evidence | 验证状态 |
|---|---|---|
| **顺序敏感性残留**（与 paper claim 矛盾） | **issue #132**：「different result for different order」— 用户实测同样的 N view 不同顺序输入，结果不同 | ✅ VERIFIED — paper 宣称严格 equivariant，实测有残差。可能源于 BF16/FP16 累加非交换 + attention numerical noise |
| **GPU 间推理不一致**（reproducibility） | **issue #135**：「不同显卡上的推理表现存在差异」— A100 vs 4090 vs 3090 数值不同 | ✅ VERIFIED — feed-forward 3D 谱系通病（VGGT 也有），mixed-precision + CUDA kernel 差异 |
| **GPU memory overflow** | **issue #138**：「显存溢出问题」— 多 view 输入时 OOM | ✅ VERIFIED — O(N²) attention，N>20 在 24 GB GPU 易爆 |
| **微调收敛困难** | **issue #140**：「fine-tuning 过程中收敛问题」 | ✅ VERIFIED — 训练 recipe 未完整公开（Pi3X training branch issue #148 也是这个） |
| **相机内参输入报错** | **issue #134**：runtime error with provided weights + camera intrinsics | ⚠ partial — API 文档不全 |
| **Metric scale 技术不公开** | **issue #154**：用户问 Pi3X 如何做 metric scale prediction | ⚠ 论文未详述，issue 待回应 |
| **Domain adaptation 无指引** | **issue #147**：「How to fine-tune for different domain?」 | ⚠ 训练代码 / 配方部分未发 |

**整体 maintainer 响应度**：72 open issue / 2k★（2026-05）— 比 StreamVGGT (25 open / 0 closed) 活跃，但 **CC BY-NC 4.0 weights** 限制商用。Research artefact 性质强于 maintained product。

**社群信号**：2k★ + 153 fork — 是 VGGT 谱系**第二高关注度** repo（仅次 VGGT v1 本身）。学术圈对 reference-free 路线认可度高。

---

## 9 · 🔁 Falsifiable predictions

1. **2027-06 前**：会出现 *permutation-equivariant + streaming* 合一的 FF3D（π³ × StreamVGGT 思想结合）— 解 issue #132 顺序敏感性 + 解 batch-only 限制。可能名字 StreamPi3 或类似。
2. **2027-12 前**：π³ issue #132（顺序敏感性）会被作者承认是 BF16/FP16 numerical 限制，FP32 模式会被加进 codebase 作为「strict equivariance」选项。
3. **2027-06 前**：会出现 *π³ + factored metric repr*（π³ × MapAnything 思想结合）— Pi3X 已是这个方向的初步尝试，但社区会出更完整的 metric variant。
4. **2027-12 前不会发生**：π³ 譜系成为 aerial real-time 主前端 — 跟 VGGT 一样，batch + 高 latency + un-metric，aerial envelope 不变。
5. **2026-12 前**：CC BY-NC license 会成为商用部署的卡点 — 会出现 community re-implementation under Apache/MIT（类似 LLaMA → Alpaca 模式）。

---

## 10 · 📊 5-axis 座标

| 轴 | 值 |
|---|---|
| Problem | **Reference-Free Feed-Forward 3D** (permutation-equivariant variant) |
| Representation | **Affine-invariant pose + scale-invariant local pointmap**（无 anchor frame） |
| Sensor | Multi-view RGB（unordered set，非 sequence） |
| Paradigm | Learned-EndToEnd + **Permutation-equivariant attention**（无 view-index embedding） |
| Time | Feed-forward batch (one-shot, order-independent) |

→ 详见 [`cheat-sheet/ontology.md §5.2`](../../cheat-sheet/ontology.md) feed-forward 多 view 第 4 子类「Permutation-equivariant」（π³ 是该子类目前唯一代表）。

---

## 11 · 对读者

- **Manipulation 工程师** — sparse-view object scan（机械手前 4-8 张物体照片）是 π³ **明显胜出 VGGT** 的场景。reference frame 难选的痛点直接消失。考虑替换 VGGT pipeline 时用 π³（但注意 CC BY-NC 商用限制）。
- **Aerial 工程师** — π³ **不为你改 envelope**。仍 batch / 仍 un-metric / 仍 high-latency。aerial 仍走 VINS / OpenVINS / 3R-SLAM Hybrid。
- **AD 工程师** — multi-camera surround rig (6-8 个固定相机) 是 π³ 的天然场景 — 不需强行指定「第一帧」。可能值得与 BEVFormer 系列对比 ablation。
- **Marine 工程师** — sparse-view underwater object scan（潜水器观察沉船 / 礁石）符合 π³ scenario。但 underwater optics（散射 / 吸收）训练 prior 缺失，仍需 domain adaptation。
- **Research 学生** — π³ 的 *permutation-equivariant attention* 是 set transformer 思想在 3D 重建的首次成功，值得作为 ICLR/NeurIPS 2026-2027 hot architecture 模板研究。重点关注 issue #132 — 严格 equivariance 在实测的 gap 是好的开放问题。

---

## 12 · 与 handbook prediction 对照

**handbook 之前的 prediction**（feed-forward-3d/overview.md §「哪些问题谁都没解」）列出 4 条未解轴，**不包含 reference-view 假设这条**。π³ 揭示了**第 5 条隐藏轴**：reference frame selection robustness。

→ handbook 应在 v2 overview 加入这条作为 FF3D 评估维度：「**Reference-view dependence**：是否需要选 anchor frame？anchor 选错是否塌？」

VGGT v1 / Ω / StreamVGGT / MapAnything 在这条上都是 ❌，**π³ 是目前唯一 ✅**。

---

## References

### Primary

- **π³ / Pi3** — Wang et al. *ICLR 2026* · [arXiv:2507.13347](https://arxiv.org/abs/2507.13347) · [GitHub yyfz/Pi3](https://github.com/yyfz/Pi3) (2k★, 153 fork, 72 open issue at 2026-05) · [Project page yyfz.github.io/pi3](https://yyfz.github.io/pi3/)
- **Pi3X** (2025-12) — metric scale prediction variant, same repo

### Critical GitHub issues (load-bearing failure mode evidence)

- [issue #132](https://github.com/yyfz/Pi3/issues/132) — 顺序敏感性残留：different result for different order（与 paper claim 矛盾）
- [issue #135](https://github.com/yyfz/Pi3/issues/135) — 不同显卡推理不一致（reproducibility）
- [issue #138](https://github.com/yyfz/Pi3/issues/138) — 显存溢出（多 view OOM）
- [issue #140](https://github.com/yyfz/Pi3/issues/140) — fine-tuning 收敛困难
- [issue #154](https://github.com/yyfz/Pi3/issues/154) — Pi3X metric scale 技术细节未公开

### Lineage (parent / cousin / family)

- **VGGT v1** — Wang et al. *CVPR 2025 Best Paper* · [arXiv:2503.11651](https://arxiv.org/abs/2503.11651) · [`vggt_cvpr2025_dissection.md`](./vggt_cvpr2025_dissection.md) — π³ 的**直接前身 + 攻击对象**（reference 假设）
- **VGGT-Ω** — *CVPR 2026 oral* · [arXiv:2605.15195](https://arxiv.org/abs/2605.15195) · [`vggt_omega_dissection.md`](./vggt_omega_dissection.md) — 正交改进（efficiency + dynamic，仍 reference-dependent）
- **StreamVGGT** — *ICLR 2026* · [arXiv:2507.11539](https://arxiv.org/abs/2507.11539) · [`streamvggt_dissection.md`](./streamvggt_dissection.md) — 正交改进（streaming，仍 reference-dependent — causal anchor）
- **MapAnything** — *3DV 2026* · [`mapanything_dissection.md`](./mapanything_dissection.md) — 正交改进（metric scale，reference 同样存在）
- **DUSt3R** — Wang et al. *CVPR 2024* · [arXiv:2312.14132](https://arxiv.org/abs/2312.14132) — reference 假设的最早 FF3D 来源（view1 anchor）
- **CroCo** — Weinzaepfel et al. *NeurIPS 2022* · [arXiv:2210.10716](https://arxiv.org/abs/2210.10716)

### Theory roots

- **Set Transformer** — Lee et al. *ICML 2019* · [arXiv:1810.00825](https://arxiv.org/abs/1810.00825) — permutation-equivariant attention 的理论起源
- **DeepSets** — Zaheer et al. *NeurIPS 2017* · [arXiv:1703.06114](https://arxiv.org/abs/1703.06114) — set-input neural net 的理论基础

---

## Boundary

- 与 VGGT v1 / Ω / StreamVGGT / MapAnything 的**对比矩阵** → [`README.md` §「三件套对照」](./README.md)（应在下次 overview 更新时加入 π³ 列 — 当前 v1 dissection 不修改 README）
- Set Transformer / DeepSets 等理论细节 → out of scope（自查 ML 文献）
- π³ 在具体 embodiment 的落地（manipulation grasp / AD surround / drone scan）→ 各 embodiment dir 的 dissection
- Permutation equivariance vs SE(3)-equivariance 的区分 → out of scope（前者是 view ordering，后者是 spatial group action，是不同概念）

---

## 5-axis 座标参考

→ [`cheat-sheet/ontology.md §5.2`](../../cheat-sheet/ontology.md)
→ [`cheat-sheet/ontology.md §13`](../../cheat-sheet/ontology.md) — open controversies（reference-view 假设属于 paradigm shift 争议范畴）

---

*Last updated: 2026-05-24 · v1 opinionated draft · ICLR 2026 brand-new paper, GitHub deep dive included*

---

[← Back to Feed-Forward 3D](./README.md)
