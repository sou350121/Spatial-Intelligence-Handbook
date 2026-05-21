# Logic Audit Report — 2026-05-22

> 全面梳理 logic + 文档类型分层 + 邏輯漏洞修正记录。

**Status:** v1 — 多轮深化后的系统性 audit + 修复 + 待决策。

---

## 1. 仓库统计（验证后真实数）

| 项 | 数量 |
|---|---|
| **总 md 文件** | **147** |
| **总 dissection（不含 README）** | **109** |
| foundations dissection | 65 |
| foundations zones | 13 |
| embodiments dissection | 14 |
| crossing wedges | 5 |
| bridge-to-vla | 3 |
| benchmarks | 6 |
| companies | 7 |
| deployment dissection | 3 |
| cheat-sheet | 3 |

---

## 2. 文档类型分层（v1.3 明确）

仓库内**5 种文档类型**，质量门槛不同：

| 类型 | 数量 | 14 项门槛? | 用途 |
|---|---|---|---|
| **dissection (*_dissection.md)** | 22 个 (foundations) | **必须** | 单 paper / 单 model / 单 sensor 的深度拆解 |
| **primer (*_primer.md)** | 2 个 | 部分（不必有 Eureka）| 前置教学（高门槛话题前的"地图" / 直觉建立）|
| **comparison (*_comparison.md)** | 1 个 (depth_models_comparison) | 不必 | 多 model 横向对比（核心是表格 + 决策树）|
| **ecosystem (*_ecosystem.md)** | 1 个 (slam_toolchain_ecosystem) | 不必 | 工具链生态拼图（Kalibr / maplab / ROS 等）|
| **roadmap (*_inspirations.md)** | 1 个 (cross_domain_math_inspirations) | 不必 | 跨学科 / 未来方向 roadmap，不是单点拆解 |

**为什么这分层重要**：之前 audit 误以为 `cross_domain_math_inspirations`、`rotation_intuition_primer`、`depth_models_comparison` 等"缺 Eureka / Napkin"。**这些不是 dissection，门槛不同。**

→ AGENTS.md 应该加入这分层（TODO）。

---

## 3. 各 zone 健康度

### 3.1 foundations 13 zones

| Zone | 篇数 | Status | 备注 |
|---|---|---|---|
| 🧮 spatial-math | 9 | ✅ 完整 | + 前置 + camera projection + IMU §6 + cross-domain |
| 🗺️ classical-slam | 3 | ✅ | ORB-SLAM3 + DSO + ecosystem |
| 🔮 feed-forward-3d | 3 | ✅ ★ | VGGT v1 + Ω + MapAnything (谱系三件套) |
| 💎 3dgs-family | 4 | ✅ | 4DGS / GS-SLAM / Mip-Splat / 3DGS original |
| 🔬 nerf-family | 4 | ✅ | NeRF / Instant-NGP / Mip-360 / Block-NeRF |
| 📏 depth-foundation | 5 | ✅ | 4 dissection + 1 comparison |
| 🎯 pose-tracking | 4 | ✅ | FoundationPose / MegaPose / RAFT / CoTracker |
| 🌐 semantic-3d | 2 | ⚠️ **薄** | LERF / OpenScene（未来加 SAM3D / LangSplat）|
| 🧠 vlm-spatial-reasoning | **1** | ⚠️ **种子区** | SpatialVLM only — 待加 SpatialBot / ManipLLM |
| 🌍 world-model | 3 | ✅ | Cosmos / Genie / Marble |
| 🎬 generative-3d-sim | 3 | ✅ | Splat-Sim / Aerial Gym / diff-rendering |
| ⚛️ physics | **1** | ⚠️ **种子区** | PhysGaussian only — 待补 differentiable physics / contact dynamics |
| 📡 sensor-physics ★ | 23 (7 桶) | ✅ ★ 独家轴 | 5 → 23 大扩充 |

### 3.2 ⚠️ 种子区分析（physics + vlm-spatial）

两个区都只 1 篇，但**保留独立而非合并**:

- **physics**: PhysGaussian 是 *物理感知渲染*；未来 differentiable physics / contact-rich simulation / port-Hamiltonian 等会扩展。**与 generative-3d-sim 区别**：前者解物理 grounded 渲染，后者解 sim2real 视觉端 augmentation。
- **vlm-spatial-reasoning**: SpatialVLM 是 *VLM 高层空间问答*；与 semantic-3d 不同（后者是 lift 2D 特征到 3D field）。未来 SpatialBot / ManipLLM / 3DSRBench 系列模型会进来。

**决策**：种子区**保留**。每个标 `Status: seed zone, 待扩展` 警示读者。

### 3.3 embodiments 6 个

| Embodiment | 篇数 | 锚定深度 |
|---|---|---|
| ✋ manipulation | 2 | 基线（policy 在 VLA-Handbook）|
| 🦿 humanoid-legged | 2 | 基线 |
| 🛒 ground-mobile | 2 | 基线 |
| 🚗 driving | 2 | 基线（不写 AD 综述）|
| 🚁 **aerial** ★ | 9 | **维护者锚定 1.5-2× 深度** |
| 🌊 marine | 2 | contrasting case |

### 3.4 其他 zone

- crossing: 5 wedges ✅
- bridge-to-vla: 3 ✅
- benchmarks: 6 ✅
- companies: 7 ✅
- **deployment: 3 dissection（薄）⚠️** — calibration / compute-budget 只 README

---

## 4. Logic 修复（本次 audit 完成）

| # | 问题 | 修复 |
|---|---|---|
| 1 | spatial-math README 自报 7 篇，实际 9 篇 | "上面 7 篇" → "上面 8 篇" |
| 2 | camera_projection_view_geometry 缺 ⚡ Eureka Moment | 加 §1.4 ⚡ Eureka（透视除法 = 丢失 Z = SLAM 原罪）|
| 3 | 文档类型不明确（dissection / primer / comparison / ecosystem / roadmap 混算）| 本 LOGIC_AUDIT 明确 5 种类型 + 门槛差异 |
| 4 | 计数审计 grep 误判 NeRF 缺 Hidden Assumptions | 实际全 4 篇都有（grep 大小写敏感假警报）|
| 5 | physics + vlm-spatial 种子区无明示 | 本文档明确"保留 + 待扩展" |

---

## 5. 待决策 / 后续工作

### 高优先（Tier 1）
- [ ] AGENTS.md 加入文档类型分层（5 种类型 + 各自门槛）
- [ ] deployment 区扩充 dissection（目前 3 个，至少加 sensor-failure-mode-atlas / 标定漂移等）
- [ ] vlm-spatial-reasoning 扩充：SpatialBot / 3DSRBench dissection
- [ ] semantic-3d 扩充：SAM3D / LangSplat dissection

### 中优先（Tier 2）
- [ ] physics 区扩充：differentiable physics / contact-rich sim
- [ ] reports/ 目录目前几乎空，与 Pulsar pipeline 对接？
- [ ] cheat-sheet 加 "近 6 个月谱系演化时间表"（VGGT v1 → Ω → MapAnything → DA3 等）

### Tier 3（speculative）
- [ ] 把命名统一到 `*_dissection.md` / `*_primer.md` / `*_comparison.md` / `*_ecosystem.md` / `*_roadmap.md` —— 但**改名会破坏所有 cross-ref**，需要批量 sed。等需要时再做。

---

## 6. Cross-Ref 健康

✅ **200 个内部 .md 链接全部解析正确**（0 broken）。

下次 audit 时可加 anchor (`#section`) 校验。

---

## 7. AGENTS.md 加入建议

加一段 "文档类型分层" 说明：

```markdown
## 文档类型分层 (5 种)

| 类型 | 后缀 | 14 项门槛 | 何时用 |
|---|---|---|---|
| dissection | `*_dissection.md` | 必须 | 单 paper / model / sensor 深度拆解 |
| primer | `*_primer.md` | 部分（不必 Eureka）| 前置教学 / 直觉建立 |
| comparison | `*_comparison.md` | 不必 | 多 model 横向对比 |
| ecosystem | `*_ecosystem.md` | 不必 | 工具链生态拼图 |
| roadmap | `*_inspirations.md`/`*_outlook.md` | 不必 | 未来方向 / 跨学科 |
```

---

## 8. 总结

仓库**结构性已经成熟**：
- 13 zones 覆盖 spatial AI 工具箱完整轴
- sensor-physics ★ 独家轴（23 篇 7 桶）
- spatial-math 9 篇 与 VLA-Handbook math_for_vla 对等
- 200+ cross-refs 全部正确

**剩下的扩展是 incremental** —— 不必再大重构。维护节奏可以从 "新建" 转向 "深化各篇 v1.2 → v1.3"。

---

[← Back to Handbook Root](./README.md)
