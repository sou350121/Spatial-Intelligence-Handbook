# Splat-Sim 与基于 3DGS 的操作数据工厂 (Splat-Sim and 3DGS-Powered Manipulation Data Factories)

> **发布时间**：Splat-Sim (Qureshi et al. 2024, arXiv:2405.02316); RoboGS family 2024; GaussianGrasper (arXiv:2403.09637)
> **核心定位**：用 3DGS 把"phone 拍 3 分钟 → 一万条 manipulation 训练 demo"的 sim2real 桥梁打通；它不是新仿真器，而是"以视觉真实度换接触保真度"的 data factory。

扩散策略每个任务需要数千段照相级演示。Teleop 每位操作员每天约 50 个 episode。Isaac Sim 给你无限 episode，但看起来像塑料。**Splat-Sim 拼到了中间：几分钟把真实场景重建为 3DGS，然后从一千个新视角渲同一任务——喂给一个部署时要消费真实 RGB 的扩散策略。**

### X-Ray (non-expert friendly)

1. **问题。** 模仿策略对 teleop 演示的精确相机位姿与光照过拟合；厨房稍变就崩。
2. **技巧。** 用 3DGS 拍一次场景。把同一段演示从一千个 jitter 后的相机位姿重渲，机器人 URDF 合成式叠上——把 100 段真实演示变成 10000 段照相级样本，无须重录。
3. **为什么空间 AI 读者应当关心。** 这是 3DGS 首次部署中，机器人客户*把照相级当 sim2real 杠杆*买——而非作为图形属性。它改变了"够好的 3DGS"意味着什么。

### Research Landscape Timeline (X-Ray)

```
  2017 ─── Domain randomization (OpenAI, To et al.)
  2020 ─── NeRF — but too slow per-scene for sim2real
  2023.07 ─ 3DGS (Kerbl et al. SIGGRAPH) — 100× faster, explicit
                              │
  ┌───────────────────────────┼───────────────────────────┐
  2024.05 Splat-Sim       2024.06 RoboGS         2024.09 GaussianGrasper
  Today: rigid-body only; contact dynamics still borrowed from teleop,
         deformables and contact-rich tasks remain open.
```

---

## 1 · System Overview

### 1.1 Component Comparison

| Module | Input | Output | Cost (per task, `UNVERIFIED`) |
|---|---|---|---|
| 场景拍摄 | 2–5 min 手机视频 | COLMAP poses + 3DGS 场景（~1 GB） | 5–30 min |
| 机器人叠加 | URDF + joint trajectory | 机器人渲入 3DGS 场景 | ~30 ms / frame on RTX 4090 |
| 视角增广 | k 演示 + 相机位姿分布 | k × N 渲出演示 | ~5 min for 1000 views |
| 策略训练 | 增广演示集 | 扩散 / ACT 策略 | A100 上数小时 |
| 真机评测 | 训好的策略 + 机械臂 | vs 仅 teleop 的成功率 Δ | 唯一重要的数字 |

### 1.2 Key Mechanism

Splat-Sim 的技巧：跨所有增广保持*任务*与*机器人轨迹*不变，仅变更渲染时的相机位姿、光照（重 tint SH 系数）与可选 distractor splat。

⚡ **Eureka Moment**：*机器人不必学新动作——它要学的是忽略无关像素。3DGS 渲染是规模化制造"同动作、不同像素"对的最便宜方式。*

### 1.3 Pipeline Flow

```
  phone capture → COLMAP + 3DGS fit (~10 min)
       ↓
  3DGS scene primitives
       ↓ ← URDF + teleop trajectory
  Splat-Sim renderer (jitter cam, jitter SH lighting, splice distractors)
       ↓
  N rendered demo videos → diffusion policy training (real + splat mix)
```

---

## 2 · Math Core

📌 **Napkin Formula**：
```
  Loss_policy = E_{view, light}[ L(π(I_render(scene, view, light)), a_teleop) ]
```
*策略的动作目标仍绑定原 teleop 动作；只有渲染输入在变。*

Splat-Sim 不在 per-augmentation 上改 Gaussian —— 它改的是*渲染函数*的参数：

- **相机位姿 `T_cw`**：从围绕 teleop 相机的 Gaussian 采样（典型 std `UNVERIFIED`：±5 cm 位置、±3° 朝向）。
- **SH 光照**：SH 系数衰减并重 tint per Gaussian（廉价的 relighting 代理；非路径追踪）。
- **Distractor splat 注入**：从物体库的 Gaussian cluster 插入到非任务位置。

> 变量：`I_render` 是原 3DGS 论文里的可微 rasterizer；`a_teleop` 是 teleop 动作标签；`π` 是策略网络。

这不是*物理感知*增广。它不靠路径追踪 relighting，也不改变策略推杯子时杯子的接触力矩。**增广只是光度上的；接触动力学从原 teleop 轨迹原样借来。**

---

## 3 · Worked Example: 100 Demos → 10000 Demos

任务："拿红杯子放抽屉"。从 100 段 teleop 演示开始。

1. **拍一次场景。** 手机绕料理台走 3 分钟（~150 帧）。COLMAP + 3DGS 出 ~600k Gaussian。
2. **对 100 段演示中每一段**采 100 个相机位姿扰动 N(μ=teleop_cam, σ=±5cm/±3°)。即 10000 次渲染。
3. **每张渲在 3 种光照下重渲**（warm / cool / overcast SH）。30000 段。
4. **在 50% 渲染中拼入随机 distractor**于非接触位置。
5. **训扩散策略**于 (real_100 + splat_30000)。用 ~50/50 采样——*不是* 100% splat（会塌）。
6. **真臂验证。** 已发布 delta（`UNVERIFIED`）：vs real-100 仅训 +15–30 pp 成功率，归因于光度鲁棒。

总加时间：拍 3 min + 拟合 10 min + 渲 30 min ≈ 45 min，相当于不到一小时 A100。

---

## 4 · Engineering View: When Splat-Sim Beats Isaac

| Concern | Splat-Sim | Isaac Sim |
|---|---|---|
| 场景搭建成本 | 5 min 手机拍 | 每资产数小时美术工 |
| 照相级 | ★★★★（真实拍摄） | ★★（取决于 USD 资产） |
| 接触动力学 | 借自真 teleop（✅ 正确） | 物理引擎（✅ 可控） |
| 新动作（无 teleop 参考） | ❌ —— 必须有真演示 | ✅ —— 可从零 RL |
| 可变形、流体 | ❌ —— Gaussian 是刚的 | ✅ —— FEM / SPH 插件 |
| 每 1k demo GPU 成本 `UNVERIFIED` | ~0.5 GPU-hour | ~2 GPU-hour |

**决策规则**：如果 manipulation 任务在*外观变异*上失败，Splat-Sim 是最便宜修复。如果在*新接触*（插装、滑面）上失败，Splat-Sim 帮不上——你需要 Isaac 或真数据。

---

## 5 · Data & Eval Conventions

Splat-Sim 类论文通常报告：per-task 真机器人成功率（仅 real-teleop vs real+splat 混合）、评测期相机位姿扰动下的鲁棒曲线、真实杂乱场景中 distractor 注入鲁棒性。

**很少**报告干净：接触密集任务（插装、拧螺丝）；增广能在多少真实数据下生存（不能零真演示）。

---

## 6 · Capabilities & Failure Modes

**Works well**：拣放、推、纹理表面滑动；真实家居 mobile manipulation；消费 RGB 的 VLM 上外观绑定任务。

**Fails or marginal**：插装 / peg-in-hole / 螺丝（缝错）；可变形物体；超出拍摄状态的铰接物；需要触觉或力监督的任务。

### 6.1 Hidden Assumptions

1. **场景拍摄质量足够。** COLMAP 位姿噪 → 3DGS 浮点 → 含 artifact 渲染 → 策略对 artifact 过拟。拍摄纪律是方法的一部分。
2. **接触动力学不是瓶颈。** Splat-Sim 渲机器人在杯子附近的像素；它不仿真杯子被碰倒。增广改变策略所见，不改变物理上发生了什么。
3. **Teleop 动作标签在视角抖动下仍有效。** 末端坐标系动作策略下成立；相机坐标系动作策略下脆。
4. **SH 衰减光照"够近"。** 不重算全局光照。Specular 材质与硬阴影不正确响应。
5. **仅训练期。** 部署的策略永不查询 Splat-Sim —— 这是隔离推理期 world model 失败模式的防火墙。

---

## 7 · Comparison & Interview Tip

| | Splat-Sim | Isaac + DR | Cosmos-Transfer | Genie-style WM |
|---|---|---|---|---|
| Stage | training | training | training | inference |
| Photorealism source | 真实拍摄 | USD 资产 | 学到的视频先验 | 学到的视频先验 |
| Contact dynamics | 来自真 teleop | 来自 PhysX | 无（仅像素） | 无 |
| Cost per new scene | 5 min phone | 数小时美术工 | 需先有 sim 资产 | n/a |
| Best for | 外观 gap | 接触密集 + 新动作 | Isaac 资产的 sim2real | 在线 MPC |

🎯 **Interview Tip**：被问 *"Splat-Sim 还是 Isaac Sim？"* 时，别答"看情况"。答：**"Splat-Sim：若失败模式是我能拍的场景上的外观变异；Isaac：若失败模式是接触动力学，或需要从零 RL 学新动作。两者互补 —— 生产管线 Isaac 做新动作播种 + Splat-Sim 做光度鲁棒。"**

---

## Boundary

per-method 3DGS 内部 → `foundations/3dgs-family/3dgs_original_dissection.md`。per-embodiment "我的机器人上 ship 了吗？" → `embodiments/manipulation/`。跨具身体 "manip vs drone vs AD 3DGS-sim" → `crossing/representation-migration/3dgs_as_simulator_comparison.md`。推理时 world model → `foundations/world-model/`。

## References

- Qureshi et al., *Splat-Sim: Zero-Shot Sim2Real Transfer of Manipulation Policies Using Gaussian Splatting*, arXiv:2405.02316 (2024).
- Kerbl et al., *3D Gaussian Splatting for Real-Time Radiance Field Rendering*, SIGGRAPH 2023, arXiv:2308.04079.
- Zheng et al., *GaussianGrasper: 3D Language Gaussian Splatting for Open-Vocabulary Robotic Grasping*, arXiv:2403.09637 (2024).
- To et al., *Sim-to-Real Transfer via Domain Randomization*, OpenAI 2017 (lineage).

---

**Status:** v1 (2026-05-21). UNVERIFIED policy applies to all latency / success-rate / GPU-hour numbers.

[← Back to Generative 3D Sim](./overview.md)
