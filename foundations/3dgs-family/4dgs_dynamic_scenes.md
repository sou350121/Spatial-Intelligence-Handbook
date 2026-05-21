# 4D Gaussian Splatting — Dynamic Scenes (4D-GS 动态场景解构 — CVPR 2024)

> **Published**: 2023-10 (arXiv) / CVPR 2024
> **Paper**: Wu et al. — *4D Gaussian Splatting for Real-Time Dynamic Scene Rendering*
> **Team**: HUST + Huawei + HKUST
> **Core position**: 通过 "canonical gaussian set + learned deformation field"（HexPlane MLP）给 3DGS 加时间轴，让 4D 场景保持在接近单个 static 3DGS 的内存预算内。

**Status:** v1.1 — 已按 AGENTS.md 14 项门槛模板回填于 2026-05-21. Hyperparams 标 UNVERIFIED.
**TL;DR:** 4D-GS 给 3DGS 加时间轴，但正确的心智模型不是 "3DGS over time" — 而是 "一组 canonical gaussian set + 一个学到的 deformation field"。这个区分决定该表示能否扛住快速 manipulation 运动，还是只能处理缓慢场景变化。

### X-Ray (non-expert friendly)

(a) Static 3DGS 重建快照，但每个具身用例（抓取、双手交接、布料、线缆）都涉及运动 — 朴素 per-frame 3DGS 会让存储线性爆炸。(b) 4D-GS 把问题分解：保留*一组* canonical gaussian set，学一个小的 deformation MLP `(x,y,z,t) → Δposition,Δrotation,Δscale`，渲染时先 deform 再 splat。(c) 对空间 AI 工程师：动态场景重建现在塞进与 static 3DGS 同等的内存预算 — 可用于 demo replay 和新视角数据增强，但对快速 / 拓扑变化运动有硬上限。

### 📍 Research Landscape Timeline

```
D-NeRF 2021 ─► HyperNeRF 2021 ─► HexPlane 2023 ─► ★ 4D-GS CVPR 2024 ─► Dynamic 3DGS (per-timestep) 2024 ─► hybrid canonical+per-step 2025+
```

4D-GS 选 "canonical + deformation" 分支；Dynamic 3DGS (Luiten et al.) 选 per-timestep 分支。两种 regime 至今没统一。

Reference paper: Wu et al. "4D Gaussian Splatting for Real-Time Dynamic Scene Rendering." *CVPR 2024.* arXiv: https://arxiv.org/abs/2310.08528

---

## 1 · 为什么时间是没人承认的瓶颈

Vanilla 3DGS 重建静态场景。对机器人这只是半个表示。抓取是动态的。双手交接是动态的。任何涉及可变形物体（布料、线缆、食物）都是动态的。诚实的问题不是 "能不能把 3DGS 扩到 video"，而是 "什么 temporal embedding 策略能扛住机器人遇到的运动速度？"

2023–2024 期间出现了两条策略，它们不可互换：

| Strategy | Mechanism | What it's good at | What it breaks on |
|---|---|---|---|
| **Per-timestep gaussians** (Dynamic 3DGS lineage) | 每帧训练一组 gaussian set；用 local rigidity loss 约束相邻 | 快速运动、拓扑变化（布料撕裂、物体分裂）| 存储随 T 线性爆炸；无 temporal interpolation |
| **Canonical + deformation field** (4D-GS, Wu et al.) | 一组 canonical gaussian set；MLP / HexPlane 在时刻 t 预测每个 gaussian 的 Δ(position, rotation, scale) | 平滑运动、缓慢形变、novel-view + novel-time 查询 | 快速运动 / 拓扑变化时 deformation MLP 退化 |

4D-GS 属于第二派。canonical-plus-deformation 分解让该表示能塞进内存，也让它对中间时刻做出干净的插值。这同样是它在快速或不连续运动上失败的原因。

## 2 · 机制

> 📌 **Napkin Formula**: `G(t) = G(0) + Φ_HexPlane(x,y,z,t)`，Φ 对每个 gaussian 输出 `(Δxyz, Δrot, Δscale)`。渲染 = 在 `G(t)` 上做标准 3DGS rasterize. **每时刻只查询 Φ；canonical set 复用。**

> ⚡ **Eureka Moment**: 把 4D 分解为 "static canonical + smooth deformation"，时间轴几乎不付代价 — 但这*只*在 deformation field 保持低频时成立。一旦运动高频（被抛出物）或拓扑变化（撕纸），MLP 跟不上，抽象就崩。分解本身 IS the assumption。

```
   Canonical gaussian set G(0)
   (anisotropic, same as 3DGS)
              │
              │     time t
              ▼
   ┌─────────────────────────┐
   │ Deformation field Φ:    │
   │   HexPlane / MLP        │     queried at every gaussian position
   │   (x, y, z, t) → Δ      │
   │   Δ = (Δxyz, Δrot, ΔS)  │
   └─────────────────────────┘
              │
              ▼
   Deformed gaussians G(t) = G(0) + Φ(G(0), t)
              │
              ▼
   Standard 3DGS rasterizer → image at time t
              │
              ▼
   Loss: photometric vs GT frame at time t
```

几个有意思的设计选择：

- **HexPlane decomposition**（4D-GS）把 4D 场分解为六个 2D 平面（xy, xz, yz, xt, yt, zt）。这让 deformation MLP 可处理；朴素 4D MLP 不会 scale。
- **Canonical frame selection** 比论文承认的更重要。选 t=0，deformation field 要编码之后发生的一切；选中位帧，field 在两侧都保持小。
- **形变下的 densification** — splitter 要决定欠覆盖区是缺 canonical gaussian 还是缺 deformation 容量。多数实现回避，只对 canonical set 做 densify。

## 2.5 · Worked example — 60 帧 teleop demo

2 秒 teleop demo（60 帧 @ 30 Hz）— 操纵臂从杯中倒水到碗里。

- **Canonical set**: ~400K gaussians（从第 30 帧 — 中位帧 — 构建）。
- **HexPlane**: 6 × `(64×64)` 平面，共享 64-channel features `UNVERIFIED defaults`；微型 MLP head（~50K params）。
- **朴素 per-timestep 存储**: 60 × 400K = 24M gaussian ≈ 6 GB。
- **4D-GS 存储**: 400K canonical + ~10 MB HexPlane = ~0.4 GB → **~15× 压缩**。
- **失败点**: 水柱（拓扑变化）— 杯内 gaussian 无法平滑形变成下落水柱。MLP 平均化，本该锐利的水柱变成软糊。

经验：4D-GS 把 manipulator 和 cup 运动编码得不错，*液体*则差。这就是 canonical-plus-deformation 契约。

---

## 3 · regime split 在哪里（慢 vs 快运动）

部署前必须内化的部分：

| Motion regime | Example | 4D-GS behavior |
|---|---|---|
| 慢，平滑 | 呼吸的人、布料垂落、慢传送带 | ✅ Works. Deformation field 保持平滑，novel-time 插值干净. |
| 中，articulated | 走路、开柜门 | ⚠️ 基本 works。Hinge / joint 处 field 噪声，预期有 floater. |
| 快，刚性 | 抛物、快速抓取 | ❌ Deformation MLP 难以编码高频时间变化。Per-timestep 变体在这里赢. |
| 拓扑变化 | 撕纸、倒水 | ❌ canonical-plus-deformation 表示不了 gaussian 出现/消失。硬墙. |

经验法则：如果运动能用 canonical 场景上的平滑速度场描述，4D-GS 是对的工具。一旦场景拓扑变化，你需要另一种表示。

## 4 · 为什么这对 robot manipulation 重要（本手册付账的车道）

Manipulation 几乎完全活在中-articulated regime。抓取时物体动力学（夹爪里旋转的物体、搬运时摆动的线缆）正是 4D-GS 设计的对象。具体获益用例：

- **新视角 demo replay** — 用 2–3 个相机录 teleop demo，重建成 4D-GS，从任意角度生成合成视角给 policy 做数据增强。
- **预测式场景 rollout** — 把 deformation field 作为学到的 world-model 先验；让 policy 条件化于 "若采取动作 a，t+1s 场景长什么样？"
- **Sim-to-real 视觉 gap 闭合** — 真实 demo 的 4D-GS 重建闭合裸物理仿真留下的视觉 gap。

要标的失败模式：快速 pick-and-place（末端速度 >1 m/s）位于 deformation field 能力边缘。标准动态 benchmark 上报告的 PSNR `UNVERIFIED — Wu et al. report ~30+ dB on D-NeRF synthetic, lower on real captures` 不直接等于 "policy 训练上不会有 distribution shift"。

### 4.x · Hidden Assumptions

上游假设，违反就触发上面的 regime-split 失败：

- **Smooth velocity field** — 运动被近似为连续 deformation；冲击 / 不连续运动（碰撞、跌落）打破 MLP。
- **Topology preservation** — clip 中无 gaussian 创建/销毁；撕裂、倾倒、烟雾失败。
- **Sufficient training views per timestep** — 稀疏时间覆盖让 deformation field 欠约束，产生 floater。
- **Static background** — 只期望前景动；相机自身运动会混淆背景 + 前景形变，双方都退化。
- **Short clip duration (~2–5 s) UNVERIFIED** — 更长 clip 推 HexPlane 容量；要么 canonical set 漂移，要么 deformation MLP 饱和。

违反时，重建通常仍在训练时刻渲染干净，在 novel time 静默退化 — 对 policy 训练而言是危险失败模式。

### 4.y · GitHub-validated 失败模式（atlas 联动，2026-05）

hustvl/4DGaussians 3.6k stars / 130 open issues / **4 open PRs 长期不动**，符合"paper 发完代码就半弃养"模式：

- **GitHub-validated（项目状态）**：**2024-06 后看不到大动作**，最后一次大规模 cleanup 显示在 "2024.6.25"；130 open issues 中近期标题多为空（社区 "Q & A 风格" 而非 "bug report 风格"），暗示项目处于 *半弃养* 状态 —— **paper 复现仍 OK，生产部署应找更新的 fork 或 Deformable-3DGS 系列**；详见 [`github_failure_atlas.md`](./github_failure_atlas.md#4dgs--wu-et-al-cvpr-2024-hustvl4dgaussians)。
- **GitHub-validated**：高频痛点集中在数据准备（[#273](https://github.com/hustvl/4DGaussians/issues/273)）+ visualization / viewer 路径（[#271](https://github.com/hustvl/4DGaussians/issues/271) / [#270](https://github.com/hustvl/4DGaussians/issues/270) / Web-based Viewer 请求 [#266](https://github.com/hustvl/4DGaussians/issues/266)）+ 训练后 quality 调参（[#269](https://github.com/hustvl/4DGaussians/issues/269)）—— 印证 §2.5 worked example 末尾 "液体 / 拓扑变化场景输出差" 的 canonical-plus-deformation 契约边界，社区在 viewer 生态上等不到答复。
- **GitHub-validated**：CUDA / 脚本失败长尾（#258–#263）—— 环境兼容性问题与 vanilla 3DGS 谱系（Windows / RTX 50）共享根因；**复现 paper 数据集仍能跑，manipulation 生产 demo 数据集**建议迁更新的 Deformable-3DGS 后继。

---

## 5 · 2-year outlook

到 2027 年，per-timestep vs canonical-plus-deformation 的分歧会塌缩为 hybrid 系统：慢的 canonical set 负责静态背景，快的 per-timestep set 负责动态前景物体，显式 foreground/background mask 驱动路由。纯 4D-GS 公式将被记作 "慢场景的正确分解"；生产机器人会用 hybrid。

**Falsifiable prediction:** 到 2027-06，至少有一篇发表的 manipulation policy 论文会用 4D-GS 重建的 demo 作为主要视觉训练数据（不是裸 camera RGB、不是 simulator）。届时对 "4D-GS 太慢 / 太贵" 的说法下负注 — 它会是标准 demo replay 工具。

**Interview Tip**: 被问 "4D-GS vs Dynamic 3DGS"，陷阱是二选一。正确答案：*"它们覆盖不相交的 regime"* — 4D-GS 处理平滑中-articulated 运动（manipulation、走路），Dynamic 3DGS 处理快速 / 拓扑变化运动（布料撕裂、快速抓取）。生产系统会 hybrid，不二选。

## References

- **4D-GS** — Wu et al. *CVPR 2024.* https://arxiv.org/abs/2310.08528
- **Dynamic 3D Gaussians** (per-timestep lineage) — Luiten et al. *3DV 2024.* https://arxiv.org/abs/2308.09713
- **HexPlane**（4D-GS 使用的分解）— Cao & Johnson. *CVPR 2023.* https://arxiv.org/abs/2301.09632
- **D-NeRF**（dynamic radiance field 前身）— Pumarola et al. *CVPR 2021.* https://arxiv.org/abs/2011.13961

## Boundary

本文覆盖 3DGS 的时间扩展。**不**覆盖：

- 静态 3DGS baseline → `foundations/3dgs-family/3dgs_original_dissection.md`
- SLAM 耦合 gaussian → `foundations/3dgs-family/gs_slam_dissection.md`
- 动态重建如何喂入 VLA 训练数据 → `bridge-to-vla/feature-cloud-to-action.md`
- 时间维度上的 cross-representation 对比（4D-GS vs feed-forward 3D over time）→ `crossing/representation-migration/`
- 原生处理多帧的 feed-forward 3D 模型 → `foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`

---

*Last opinion update: 2026-05-21.*
