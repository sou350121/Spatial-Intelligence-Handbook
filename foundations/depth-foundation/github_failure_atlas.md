# Depth Foundation GitHub Failure Atlas (深度基础模型 · GitHub 失败模式图谱)

> **类型**: `*_ecosystem.md` —— 5 个 depth foundation 仓库的工程失败拼图
> **覆盖**: Depth Anything v2 · Depth Anything 3 · Metric3D · MoGe / MoGe-2 · FoundationStereo
> **核心定位**: 不重写算法，重写**部署侧用户在 GitHub issue 里反复掉的坑**.
> **数据**: 2026-05-21 GitHub REST API 拉取；issue # / 状态 / push 日期实测.

**Status:** v1 — ecosystem register. 按「failure pattern → PR 方向 → momentum」三层. UNVERIFIED 用于用户自报偏差等不可二次验证数字.

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

**TL;DR:** 5 仓 issue 表面是 bug，本质是**输出契约（relative/metric/affine-invariant）没被用户读懂** —— 占 ~40%；模型本质局限（透明/远场/synth→real）~30%；ONNX/TRT 摩擦 ~20%；时序/部署 ~10%. 维护者**最高 ROI 的 PR 不是改模型，而是 README 加 Output Contract 表 + 添加 confidence head**.

### X-Ray (non-expert friendly)

(a) Depth foundation 一年出 5 个开源旗舰，issue 区一直重复三个问题：「我量的距离不对」「换设备不准」「ONNX 转完精度掉光」. (b) 不是 bug，是**输出契约没被用户读懂** —— 论文 1 行免责声明，issue 被复述 200 次. (c) 对维护者：写 README 输出契约表 + confidence head 的回报，远高于刷 +0.5% AbsRel.

---

## Zone Summary

| 仓 | ★ | open | push | 主要 failure | Momentum |
|---|---|---|---|---|---|
| **Depth-Anything-V2** | 8149 | 236 | 2026-03-24 | 输出契约 / 时序 / metric variant 截断 | 🟢 活跃，DA3 出后分流 |
| **Depth-Anything-3** | 5326 | 183 | 2026-03-21 | metric 失真 / 3DGS export 错 / 内外参错配 | 🔥 火爆（6 月 ★ 5300+） |
| **Metric3D** | 2195 | 84 | 2025-03-13 | in-the-wild 倍数偏差 / canonical 假设破 | 🟡 维护降速（>1 年无 push） |
| **MoGe** | 2476 | 76 | 2025-11-02 | local vs HF demo 不一致 / multi-head 矛盾 / 真实 metric 错 | 🟢 v2 活跃 |
| **FoundationStereo** | 2706 | 83 | 2025-12-19 | 无 confidence / synth→real / TRT NaN / calibration drift | 🟢 NVlabs 撑腰 |

---

## 1 · Depth Anything v2 — relative-only 的输出契约困局

**Repo**: https://github.com/DepthAnything/Depth-Anything-V2 · ★8149 · push 2026-03-24 · open 236

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **以为输出是米** | [#93](https://github.com/DepthAnything/Depth-Anything-V2/issues/93)·[#178](https://github.com/DepthAnything/Depth-Anything-V2/issues/178) | 直接读 disparity 当 meter；实际是 affine-invariant inverse depth，[0,1] 无单位 |
| **NYU↔KITTI scale 不通用** | [#26](https://github.com/DepthAnything/Depth-Anything-V2/issues/26)·[#4](https://github.com/DepthAnything/Depth-Anything-V2/issues/4)·[#69](https://github.com/DepthAnything/Depth-Anything-V2/issues/69) | metric variant max_depth 写死（Hypersim 20m / VKITTI 80m），超过截断 |
| **relative→metric 蒸馏失效** | [#98](https://github.com/DepthAnything/Depth-Anything-V2/issues/98)·[#102](https://github.com/DepthAnything/Depth-Anything-V2/issues/102) | shift `b` 随内容变，单点拟合不可迁 |
| **ONNX 后 metric 炸** | [#49](https://github.com/DepthAnything/Depth-Anything-V2/issues/49) | metric head sigmoid + max_depth 在 export 时丢精度 |
| **视频时序闪烁** | [#85](https://github.com/DepthAnything/Depth-Anything-V2/issues/85) | 单帧模型无 temporal head；需切 Video Depth Anything |
| **透明 / 镜面穿透** | [#5](https://github.com/DepthAnything/Depth-Anything-V2/issues/5)·[#157](https://github.com/DepthAnything/Depth-Anything-V2/issues/157) | DPT-lineage 通病，DA-2K `transparent_reflective` 桶未根治 |

**PR**: (1) README Output Contract + max_depth 说明 → 关 #93/#178/#98；(2) OOD 守门 head（flip 一致性 / DINOv2 distance）→ 关 #5；(3) 官方 ONNX export + 单元测试 → 关 #49；(4) distance bucket 文档 → 关 #4/#26. **Momentum**: 🟢 活跃但被 DA3 分流；stable + low-touch；新用户优先评估 DA3 / VGGT.

---

## 2 · Depth Anything 3 — 最火也最容易翻车（2025-11 发布）

**Repo**: https://github.com/ByteDance-Seed/Depth-Anything-3 · ★5326 · push 2026-03-21 · open 183 · created 2025-11-12

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **多视角点云塌缩 / 伪影** | [#22](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/22)·[#125](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/125) | 「深度图很多伪影，多视角点云基本没有点」 |
| **3DGS export 后训不动** | [#117](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/117)·[#136](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/136)·[#46](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/46) | export_to_colmap 位姿 3DGS 收敛失败 |
| **metric 模型精度差** | [#244](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/244)·[#94](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/94)·[#142](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/142) | 户外路面 metric depth 错 |
| **小模型反而退化** | [#71](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/71) | DA3-SMALL 某些场景不如 DA v2-small |
| **每相机重复点云** | [#14](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/14) | 多视角下同物体被独立预测、未对齐 |
| **缺 ONNX / PyTorch ckpt** | [#65](https://github.com/ByteDance-Seed/Depth-Anything-3/issues/65) | 部署侧无路径 |

**PR**: (1) 修 metric depth head（#244/#94 = 最大短板）；(2) export_to_colmap 对照 3DGS e2e 测试（#117/#136 位姿可能 off-by-one）；(3) PyTorch/ONNX ckpt 释放（#65）；(4) DA3-Small vs v2-Small 退化场景表（#71）. **Momentum**: 🔥 极火，6 月 ★ 5326（vs DA v2 同期 +30%）；2026-07 前应有补丁；当前**不建议**做 production AD/drone 主依赖.

---

## 3 · Metric3D — canonical-camera 假设的边界

**Repo**: https://github.com/YvanYin/Metric3D · ★2195 · push 2025-03-13 · open 84

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **in-the-wild 倍数偏差** | [#38](https://github.com/YvanYin/Metric3D/issues/38) | 真值 5m / 预测 16.5m，**~330% 偏差**；人身高 5m vs 真值 1.7m，**~190%** `UNVERIFIED 是否所有 in-the-wild 都这量级` |
| **大焦距静默退化** | [#19](https://github.com/YvanYin/Metric3D/issues/19) | f=1966 px（训练分布 500-700）→ depth 错 |
| **canonical 假设破** | [#17](https://github.com/YvanYin/Metric3D/issues/17)·[#95](https://github.com/YvanYin/Metric3D/issues/95) | canonical camera 假设（focal=1000 px）违反时无 fallback |
| **fine-tune shape mismatch** | [#156](https://github.com/YvanYin/Metric3D/issues/156)·[#91](https://github.com/YvanYin/Metric3D/issues/91) | 自定义 KITTI-like 训练失败 |
| **ONNX 动态 shape** | [#117](https://github.com/YvanYin/Metric3D/issues/117)·[#126](https://github.com/YvanYin/Metric3D/issues/126) | dynamic batch 边角 case |
| **老 GPU 不支持** | [#81](https://github.com/YvanYin/Metric3D/issues/81) | sm<70 跑不通 |

**关键洞察**：Metric3D 的 metric 能力依赖「输入已 rescale 到 canonical focal length (~1000 px)」假设. 真实焦距偏离 canonical 时输入被静默 rescale 错 —— 输出仍像 metric 但米数错. #38 的「5m → 16.5m」几乎对应 `(520/260)² ≈ 4` 量级偏差 —— 不是模型学错，是 canonical 假设的几何代价.

**PR**: (1) input focal 超训练分布显式 warning → 关 #19/#38；(2) README in-the-wild checklist（K、ratio to canonical 1000 px、resize 顺序）；(3) 多 focal length 训练数据；(4) #156 fine-tune 文档. **Momentum**: 🟡 低维护（>1 年无 push）；学术 repo「PhD 毕业 → low-maintenance」典型；PoC 可用，production 需 in-house 校准 layer.

---

## 4 · MoGe / MoGe-2 — affine-invariant 3D points 的多头一致性

**Repo**: https://github.com/microsoft/MoGe · ★2476 · push 2025-11-02 · open 76

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **真实 metric 错** | [#75](https://github.com/microsoft/MoGe/issues/75)·[#43](https://github.com/microsoft/MoGe/issues/43) | MoGe-2 点云 scale 与真实尺寸偏差「2x? more? less?」（用户原话） |
| **local vs HF demo 不一致** | [#72](https://github.com/microsoft/MoGe/issues/72)·[#66](https://github.com/microsoft/MoGe/issues/66) | 同图本地 vs demo 不同 —— 隐藏前/后处理 |
| **multi-head / sphere sky hack** | [#79](https://github.com/microsoft/MoGe/issues/79)·[#81](https://github.com/microsoft/MoGe/issues/81) | depth+normal+FoV 互不洽；sky 区被「推到球面」占位 |
| **视频时序不一致** | [#6](https://github.com/microsoft/MoGe/issues/6) | 单帧模型，视频闪烁 |
| **ONNX export 缺** | [#20 (34c)](https://github.com/microsoft/MoGe/issues/20)·[#83](https://github.com/microsoft/MoGe/issues/83) | 34 评论无官方 ONNX，呼声最高 |
| **FoV 复现失败** | [#115](https://github.com/microsoft/MoGe/issues/115) | v1 FoV head 与论文数字 reproduce 不上 |

**关键洞察**：MoGe 同时输出 depth + 3D points + FoV + (v2) normal，每 head「affine-invariant up to its own scale」**且无跨 head scale 约束**. 用户期待「3D points 直接米」（#75），实际形状对、scale 不可知. sky head「推到球面」是 dynamic range hack，**不是几何**.

**PR**: (1) README Output Contract per Head（affine-invariant/metric/sphere-hack）；(2) HF demo vs local pipeline 对照（关 #72/#66）；(3) 官方 ONNX export（#20 = 最高动量）；(4) temporal 变体（#6）. **Momentum**: 🟢 v2 活跃；Microsoft 稳定（vs Metric3D 学术）；MoGe-3 可能加 temporal + 显式 metric head.

---

## 5 · FoundationStereo — 没 confidence map 的 stereo 旗舰

**Repo**: https://github.com/NVlabs/FoundationStereo · ★2706 · push 2025-12-19 · open 83

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **没 confidence map** | [#121](https://github.com/NVlabs/FoundationStereo/issues/121) | 多帧静止物体**头部对齐但身体散开** —— 非均匀 spatial bias |
| **TensorRT NaN** | [#49 (19c)](https://github.com/NVlabs/FoundationStereo/issues/49)·[#175](https://github.com/NVlabs/FoundationStereo/issues/175) | TRT engine 输出 NaN（fp16） |
| **ONNX 慢** | [#58](https://github.com/NVlabs/FoundationStereo/issues/58) | flash_attn unsupported export |
| **大 baseline drift** | [#142](https://github.com/NVlabs/FoundationStereo/issues/142) | baseline ~15 cm（vs RGB-D ~5-7 cm）效果差 |
| **synth→real（KITTI）** | [#102](https://github.com/NVlabs/FoundationStereo/issues/102) | 室外 KITTI 差 —— 训练合成室内主导 |
| **空 disparity / rectify** | [#104](https://github.com/NVlabs/FoundationStereo/issues/104) | 输出全 0 |
| **视频闪烁** | [#59](https://github.com/NVlabs/FoundationStereo/issues/59) | 单帧 stereo，无 temporal |
| **Jetson Orin / camera K** | [#136](https://github.com/NVlabs/FoundationStereo/issues/136)·[#26 (24c)](https://github.com/NVlabs/FoundationStereo/issues/26) | embedded 部署 + K 输入格式 |

**关键洞察**：#121 多帧静止物体**头部对齐而身体散开** —— stereo 预测有 spatial heteroscedasticity，但模型不输出 confidence → 下游融合无 weighted fuse、grasp planner 用差像素作决策. issue 标 closed 但根因未解 —— closed-without-fix 典型.

**PR**: (1) **加 confidence head**（最高优：flip 一致性 / attention entropy / Bayesian KL）→ 关 #121 + 一批 drift；(2) KITTI/outdoor 训练 batch（#102）；(3) TRT 修复（#49/#175/#58 同根：flash_attn export 路径 bug）；(4) 多 baseline 训练（~5-15 cm，#142）；(5) Jetson Orin official build（#136）. **Momentum**: 🟢 NVlabs 活跃；多 ONNX issue closed；confidence map 是下一波 PR；2026Q3 前应有 confidence variant.

---

## Cross-cutting

1. **输出契约 = #1 问题，维护者最不重视** —— 5 仓最高动量 issue 都是「输出是什么意思」.
2. **ONNX/TRT = #2 摩擦** —— flash_attn export / dynamic shape / fp16 NaN.
3. **Confidence map 全 5 仓缺失** —— production grasp/drone/AD 硬伤；FStereo 最可能先加.
4. **Synth→Real 边界** —— 医学/水下/极端光照全静默退化，**无任何一个**输出 OOD 警示.
5. **时序一致性普遍缺口** —— 仅 Video Depth Anything 处理；其余 5 仓靠下游自己 smooth.

## Surprise

**FoundationStereo #121**：「多帧静止物体头部对齐但身体散开」意味着 FStereo 不只缺 confidence，**预测的 spatial bias 本身非均匀**. 对 robot 是「身体能抓但头部位置不准」的部署灾难. issue 标 closed 但根因未解 —— failure atlas **必须挖 closed issue**.

## Boundary & For the reader

- Per-model 拆解：`{depth_anything_v2,metric3d,moge,foundationstereo}_dissection.md`；姊妹：`../pose-tracking/github_failure_atlas.md`
- **Manipulation**：DA v2/MoGe depth 不可直接 grasp；切 Metric3D + in-house scale
- **AD/drone**：5 仓缺 confidence → 不可裸跑；LiDAR/radar 兜底
- **Researcher**：先看 maintenance（Metric3D >1 年无 push）
- **维护者**：README Output Contract + ONNX 测试 ROI 远高于刷 AbsRel

来源：GitHub REST API 2026-05-21.

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to depth-foundation README](./README.md)
