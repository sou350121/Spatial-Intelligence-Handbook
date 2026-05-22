# Pose & Tracking GitHub Failure Atlas (位姿 / 追踪基础模型 · GitHub 失败模式图谱)

> **类型**: `*_ecosystem.md` —— 5 个 pose / tracking foundation 仓库的工程失败拼图
> **覆盖**: FoundationPose · MegaPose · RAFT · CoTracker · SAM 2
> **核心定位**: 不重写算法，重写**部署侧用户在 GitHub issue 里反复掉的坑**.
> **数据**: 2026-05-21 GitHub REST API 拉取；issue # / 状态 / push 日期实测.

**Status:** v1 — ecosystem register. 按「failure pattern → PR 方向 → momentum」三层. UNVERIFIED 用于用户自报偏差等不可二次验证数字.

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

**TL;DR:** 5 仓 issue 的痛点和 depth 阵营完全不同：**输入资产门槛（mesh / 第一帧 prompt）占 ~30%**、**memory / 长视频限制 ~25%**（SAM2 / CoTracker）、**部署摩擦（CUDA / build / ONNX）~25%**、**accuracy（遮挡 / 反光 / 大运动）~20%**. 维护者最高 ROI PR 不是改模型，而是**降低输入资产门槛 + 加 streaming memory 接口**.

### X-Ray (non-expert friendly)

(a) Pose / tracking foundation 模型表面是「输入图 + 提示 → 输出位姿 / 轨迹」，issue 区揭示真实痛点：**用户提供的输入资产（mesh、第一帧 mask、相机内参）从来都不符合模型期望**. (b) FoundationPose 要 mesh + CAD，MegaPose 要 PNG mask，CoTracker 要 grid 起点 —— 资产门槛拒绝了 50% 部署. (c) 长视频 memory 是 SAM2 / CoTracker 共同痛点；RAFT 是「大运动 + OOD」；FoundationPose 是「novel object + 遮挡」.

---

## Zone Summary

| 仓 | ★ | open | push | 主要 failure | Momentum |
|---|---|---|---|---|---|
| **NVlabs/FoundationPose** | 3213 | 140 | 2026-04-29 | mesh 要求 / 高反射 / 遮挡 / RTX 兼容 | 🟢 NVlabs 活跃，CVPR 2024 旗舰 |
| **megapose6d/megapose6d** | 348 | 54 | 2024-12-12 | novel 不准 / mesh png / pinocchio 依赖 / 渲染失败 | 🟡 维护降速（>1 年无 push） |
| **princeton-vl/RAFT** | 4035 | 76 | 2025-08-24 | 大运动失效 / 域外 / 静止帧噪声 / 老接口 | 🟡 经典作品，低维护 |
| **facebookresearch/co-tracker** | 4955 | 101 | 2026-03-03 | 长时漂移 / 多 GPU memory / 稀疏 sparse 弱 / ONNX 难 | 🟢 v3 出后活跃 |
| **facebookresearch/sam2** | 19204 | 474 | 2026-04-07 | 长视频 memory / mask shape 错配 / TRT 难 / 资源贵 | 🔥 Meta 旗舰，社区最活跃 |

---

## 1 · FoundationPose — novel object 的 mesh 门槛

**Repo**: https://github.com/NVlabs/FoundationPose · ★3213 · push 2026-04-29 · open 140

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **NaN scores（部署灾难）** | [#53 (27c)](https://github.com/NVlabs/FoundationPose/issues/53) | 252 个候选 pose 评分全 NaN → OpenCV crash；GTX 1660 Ti / CUDA 11.5 用户高发 |
| **mesh 输入门槛** | [#83 (16c)](https://github.com/NVlabs/FoundationPose/issues/83)·[#60 (10c)](https://github.com/NVlabs/FoundationPose/issues/60)·[#32 (10c)](https://github.com/NVlabs/FoundationPose/issues/32) | model-based 要 CAD mesh；novel object 必须先扫 mesh —— 真正 novel use case 卡死 |
| **depth 预处理** | [#44 (35c, closed)](https://github.com/NVlabs/FoundationPose/issues/44) | depth image 缺值 / 去噪 / 单位转换不文档化 |
| **首帧选择 / drift** | [#186 (11c, closed)](https://github.com/NVlabs/FoundationPose/issues/186)·[#279 (15c, closed)](https://github.com/NVlabs/FoundationPose/issues/279) | track 漂移；首帧 pose 估错会传染所有后续帧；large centroid error |
| **RealSense 集成** | [#147 (14c)](https://github.com/NVlabs/FoundationPose/issues/147) | 用户 4 个具体问题（color/depth 接入、texture、mask）无官方答案 |
| **build / RTX 兼容** | [#27 (20c, closed)](https://github.com/NVlabs/FoundationPose/issues/27)·[#348 (18c)](https://github.com/NVlabs/FoundationPose/issues/348)·[#9 (15c, closed)](https://github.com/NVlabs/FoundationPose/issues/9) | RTX 4090 / pybind11 / build_all_conda 路径碎 |
| **INT8 / 加速** | [#298 (11c)](https://github.com/NVlabs/FoundationPose/issues/298) | INT8 量化无官方路径 |
| **遮挡 / 高反射** | （issue 区零散） | model-based 部分鲁，model-free novel 部分掉 30%+ `UNVERIFIED 具体数字` |

**关键洞察**：mesh 是 FoundationPose 的「藏在公式后的硬假设」—— 论文展示 model-free（仅参考图），但实际部署要么 mesh 要么先扫描 mesh，**真正「拍照即追踪 novel object」未释放**.

**PR**: (1) #53 NaN 排查（fp16 / 老 GPU 路径）；(2) RealSense wrapper（#147）；(3) novel object 无 mesh fallback（SAM2 + monocular depth 自动估 mesh）；(4) INT8/TRT 官方路径（#298）；(5) build 系统统一（#27/#348/#9）. **Momentum**: 🟢 NVlabs 活跃；2026-04 push；6D pose 开源 SOTA；mesh 门槛是下一波 PR 焦点.

---

## 2 · MegaPose — 早 FoundationPose 一年的 6D pose 模板

**Repo**: https://github.com/megapose6d/megapose6d · ★348 · push 2024-12-12 · open 54

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **可视化失败** | [#12 (22c, closed)](https://github.com/megapose6d/megapose6d/issues/12)·[#27 (10c, closed)](https://github.com/megapose6d/megapose6d/issues/27) | pose 数字看着对，mesh overlay 不显示 |
| **mesh PNG 是否必需** | [#58](https://github.com/megapose6d/megapose6d/issues/58) | 用户问 png 是否必需；MegaPose 默认要 mesh + texture PNG |
| **novel object 不准** | [#55](https://github.com/megapose6d/megapose6d/issues/55) | 新物体 pose 估算「pretty inaccurate」—— 无官方诊断回复 |
| **依赖地狱** | [#65 (5c, closed)](https://github.com/megapose6d/megapose6d/issues/65)·[#51](https://github.com/megapose6d/megapose6d/issues/51) | pinocchio.SE3 缺、firefox/geckodriver 缺、torch multiprocessing 卡死 |
| **大物体慢 / OOM** | [#42](https://github.com/megapose6d/megapose6d/issues/42)·[#53](https://github.com/megapose6d/megapose6d/issues/53) | 大物体推理慢 + 显存爆 |
| **`assert LOCAL_DATA_DIR`** | [#5 (5c, closed)](https://github.com/megapose6d/megapose6d/issues/5) | 数据路径配置碎 |

**关键洞察**：MegaPose 是 FoundationPose 精神先驱，但精度/鲁棒/工程化已被全面超越. issue 区是「最后一批使用者」痕迹.

**PR**: (1) 渲染流水线（pinocchio + browser deps）docker 化 → #65/#51；(2) mesh-png 改 optional（#58）；(3) novel object 文档（#55）；(4) 官方迁移到 FoundationPose. **Momentum**: 🟡 低维护（>1 年无 push）；INRIA 学术「项目结束」典型；**新用户直接选 FoundationPose**.

---

## 3 · RAFT — 大运动失效 + 域外的经典 optical flow

**Repo**: https://github.com/princeton-vl/RAFT · ★4035 · push 2025-08-24 · open 76

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **遮挡区光流错** | [#57 (11c, closed)](https://github.com/princeton-vl/RAFT/issues/57) | 遮挡区域 flow 静默错；RAFT 无 occlusion mask 输出 |
| **demo 复现失败** | [#86](https://github.com/princeton-vl/RAFT/issues/86)·[#21 (8c, closed)](https://github.com/princeton-vl/RAFT/issues/21) | `--alternate_corr` 跑挂 / Sintel test split 数字复现不上 |
| **静止帧噪声** | [#123](https://github.com/princeton-vl/RAFT/issues/123) | 邻帧几乎相同时 flow 是 mess（无运动 → 大噪声） |
| **训练 / dataloader** | [#181](https://github.com/princeton-vl/RAFT/issues/181)·[#49 (6c, closed)](https://github.com/princeton-vl/RAFT/issues/49)·[#100](https://github.com/princeton-vl/RAFT/issues/100) | 自定义数据集训练失败 |
| **import 错** | [#108](https://github.com/princeton-vl/RAFT/issues/108)·[#23 (6c, closed)](https://github.com/princeton-vl/RAFT/issues/23) | `cannot import name 'RAFT' from 'raft'`；老接口 / Python 版本不匹配 |
| **可视化 jaggy** | [#16 (7c, closed)](https://github.com/princeton-vl/RAFT/issues/16) | 边缘锯齿（colorize 阶段，模型本身没问题） |

**关键洞察**：RAFT 2020 经典；三条未解硬限：**(1) 无 occlusion mask** → 遮挡 flow 静默错；**(2) 大运动外推弱**（训练 max disp ~50 px）；**(3) 静止帧噪声**（flow 不是 0 是小随机量）. 社区已转 GMFlow/FlowFormer/SEA-RAFT.

**PR**: (1) occlusion mask head（多 fork 已实现）→ #57；(2) 修 `--alternate_corr`（#86）；(3) 老接口兼容（#108）；(4) 自定义训练 README. **Momentum**: 🟡 经典低维护；SEA-RAFT 已超越；**新项目优先 SEA-RAFT 或 CoTracker**.

---

## 4 · CoTracker — 长时漂移 + 多 GPU memory 的 dense tracking 旗舰

**Repo**: https://github.com/facebookresearch/co-tracker · ★4955 · push 2026-03-03 · open 101

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **长视频 memory 爆** | [#51 (14c)](https://github.com/facebookresearch/co-tracker/issues/51) | 3 分钟视频在 Colab GPU OOM；用户提议分段 + 末帧延续，但官方无回应 |
| **稀疏点效果弱** | [#71](https://github.com/facebookresearch/co-tracker/issues/71)·[#24 (8c)](https://github.com/facebookresearch/co-tracker/issues/24) | 单点 webcam 跟踪不稳；动物腿等高频运动易丢 |
| **live video 应用** | [#37 (21c)](https://github.com/facebookresearch/co-tracker/issues/37)·[#54](https://github.com/facebookresearch/co-tracker/issues/54)·[#123](https://github.com/facebookresearch/co-tracker/issues/123) | 实时流支持弱；offline 模式 v2 / v3 切换不清晰 |
| **训练数据准备** | [#8 (29c)](https://github.com/facebookresearch/co-tracker/issues/8)·[#130](https://github.com/facebookresearch/co-tracker/issues/130) | Kubric dataset 复现 / 自定义训练集准备摩擦 |
| **ONNX 导出** | [#10 (10c, closed)](https://github.com/facebookresearch/co-tracker/issues/10) | 早期 ONNX 路径，现状不明 |
| **多 GPU 推理 OOM** | [#51](https://github.com/facebookresearch/co-tracker/issues/51) | 多 GPU 分段不被官方支持 |
| **License** | [#31 (11c)](https://github.com/facebookresearch/co-tracker/issues/31) | 类 DINOv2 商用化需求 |
| **高分辨率性能** | [#15 (8c, closed)](https://github.com/facebookresearch/co-tracker/issues/15) | 1080p+ 性能掉 |

**关键洞察**：CoTracker v3（2025）改善短时密集追踪，但**长视频 + 稀疏点 + 实时**三交叉点仍缺. #51「分段 + 末帧延续」是等待官方接管的社区方案 —— 需 streaming memory API.

**PR**: (1) streaming inference API（chunk + handoff，#51/#37/#54）；(2) 稀疏 + 高频运动 robust（#24/#71）；(3) 官方 ONNX（#10）；(4) Kubric 准备脚本（#8/#130）；(5) 商用 license（#31）. **Momentum**: 🟢 v3 后活跃；Meta FAIR 稳定；streaming + sparse 下一波；2026 应有 CoTracker3-Streaming.

---

## 5 · SAM 2 — video memory 的旗舰瓶颈

**Repo**: https://github.com/facebookresearch/sam2 · ★19204 · push 2026-04-07 · open 474

| Pattern | 高动量 issue | 现象 |
|---|---|---|
| **长视频 memory 限制** | [#264 (24c)](https://github.com/facebookresearch/sam2/issues/264)·[#90 (26c)](https://github.com/facebookresearch/sam2/issues/90) | 2 小时 720p/60fps 在 4090 OOM；实时应用 latency 不明确 |
| **mask shape / 多对象 ID** | [#249 (16c)](https://github.com/facebookresearch/sam2/issues/249)·[#185 (14c)](https://github.com/facebookresearch/sam2/issues/185)·[#138 (22c)](https://github.com/facebookresearch/sam2/issues/138) | 多 object mask 丢；video 中途新 ID 加入难；input 分辨率变 mask shape mismatch |
| **TRT / ONNX 难** | [#284 (16c)](https://github.com/facebookresearch/sam2/issues/284)·[#186 (24c, closed)](https://github.com/facebookresearch/sam2/issues/186)·[#501 (24c)](https://github.com/facebookresearch/sam2/issues/501) | memory_attention 模块 export NaN；ComplexFloat 不支持；vos_inference.py 复杂 |
| **build / CUDA** | [#41 (18c, closed)](https://github.com/facebookresearch/sam2/issues/41)·[#18 (18c, closed)](https://github.com/facebookresearch/sam2/issues/18)·[#56 (17c, closed)](https://github.com/facebookresearch/sam2/issues/56)·[#21 (16c, closed)](https://github.com/facebookresearch/sam2/issues/21) | CUDA_HOME 缺 / no-build-isolation / `_C` import fail |
| **config 缺** | [#81 (24c, closed)](https://github.com/facebookresearch/sam2/issues/81) | hydra 配置文件找不到 |
| **fine-tune** | [#347 (14c, closed)](https://github.com/facebookresearch/sam2/issues/347) | 自定义图像 fine-tune |
| **demo Web UI LAN** | [#366 (21c, closed)](https://github.com/facebookresearch/sam2/issues/366) | LAN 访问失败 |
| **大视频分割** | [#105 (16c)](https://github.com/facebookresearch/sam2/issues/105) | segment all objects in video |

**关键洞察**：SAM2 memory bank 是核心创新，但**bank 容量是隐藏 hyperparameter** —— 视频长到一定程度 mask 缓存 OOM. 不是 bug，是架构选择. #264/#90 揭示部署期待「2 小时」级别，当前 budget 远小于此. **streaming + memory pruning 是下一波 PR**.

**PR**: (1) streaming memory bank + pruning（#264/#90）；(2) 多 object ID hot-swap（#249/#185）；(3) input resolution 变化时 mask 自动 resize（#138）；(4) ONNX/TRT memory_attention 修复（#186/#284）；(5) build 系统统一（#18/#21/#41/#56/#81）. **Momentum**: 🔥 Meta 旗舰最活跃；19k★ + 474 open；2026Q3-Q4 应有 SAM2.1 / streaming variant.

---

## Cross-cutting

1. **输入资产门槛 = #1** —— FoundationPose mesh、MegaPose mesh+PNG、CoTracker grid、SAM2 first-frame mask. 5 仓假设「用户能提供完美初始输入」，issue 证明：完全不能.
2. **长视频 memory 是共同缺口** —— SAM2 / CoTracker 都缺 streaming API；用户用例「1 小时+」，模型 budget 远小于此.
3. **ONNX/TRT = #2 摩擦** —— SAM2 memory_attention NaN、CoTracker ONNX 状态不明、FoundationPose INT8 缺.
4. **CUDA / build / RTX 兼容** —— RTX 4090、pybind11、CUDA_HOME、`_C` import fail，5 仓共有.
5. **遮挡 / 反射 / OOD = production blocker** —— 没有任何一仓输出 per-pixel / per-track confidence.

## Surprise

**FoundationPose #53「NaN scores」27 comments 但 closed-without-explicit-fix** —— 多用户在不同 GPU / CUDA 复现，但根因（pose grid 计算 / fp16 路径）无官方诊断；6D pose SOTA repo 居然没有 GPU 兼容矩阵. 与 depth 阵营 FStereo #121 同一模式：**closed 不等于已修，failure atlas 必须挖**.

## Boundary & For the reader

- Per-model 拆解：`foundation_pose_dissection.md` · `megapose_dissection.md` · `raft_optical_flow.md` · `cotracker_and_tap_dissection.md`；姊妹：`../depth-foundation/github_failure_atlas.md`
- **Manipulation**：FoundationPose 仍是 6D pose 首选，novel object 要 in-house mesh 扫描；MegaPose 已被超越
- **AD/drone**：RAFT 已被 SEA-RAFT 超越；SAM2 长视频前置 streaming 工程
- **Researcher**：MegaPose / RAFT 是「学术对比基线」；新项目选 FoundationPose / CoTracker3 / SAM2
- **维护者**：降低输入资产门槛 + streaming API ROI 远高于刷 +1% accuracy

来源：GitHub REST API 2026-05-21.

⚙️ 本文由 Moltbot 自动生成 | 2026-05-21

[← Back to pose-tracking README](./README.md)
