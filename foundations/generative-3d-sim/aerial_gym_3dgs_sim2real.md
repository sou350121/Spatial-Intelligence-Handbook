# Aerial Gym 与无人机 3DGS Sim2Real (Aerial Gym and Drone 3DGS Sim2Real)

> **发布时间**：Aerial Gym (Kulkarni et al. 2023, arXiv:2305.16510); Splat-Nav (Chen et al. 2024, arXiv:2403.02751); GS-Splatter sim variants 2024–2025
> **核心定位**：用 3DGS 渲染真实世界森林 / 城市 / 室内走廊作为 *视觉前端*，把 *动力学* 留给 Isaac Gym / Aerial Gym / Gazebo 自带的刚体模拟器 — 是无人机 obstacle avoidance / VIO sim2real 在 2024-2025 的主流配方。

无人机 RL 策略需要百万级 episode；manipulation 策略需要千级。**这一结构性事实使无人机 3DGS sim2real 与 manipulation Splat-Sim 在本质上不同**：速度胜过保真，场景很少被编辑，风 / 气动也永远不会从 Gaussian 渲染器里出来。

### X-Ray (non-expert friendly)

1. **问题。** 在塑料感 Gazebo 世界里训出的无人机避障与 VIO 策略在户外失败 —— 真实树 / 砖 / 天空的视觉统计与渲染几何相距甚远。
2. **技巧。** 用 photogrammetry 拍下真实飞行环境，拟一个 3DGS 场景，把它当*相机渲染器*接入 Aerial Gym 高度并行的四旋翼仿真器。动力学仍是刚体 PhysX；只是渲出来的像素变成真实分布。
3. **为什么空间 AI 读者应当关心。** 这是 3DGS-as-simulator 命中最高吞吐客户的地方（多并行环境 1000+ Hz），也是几何 / 外观与动力学最干净分离的地方 —— 风与桨流来自独立模型。

### Research Landscape Timeline (X-Ray)

```
  2017─2020 ─ Flightmare / Gazebo / RotorS (plastic worlds; visual gap unsolved)
  2023.05 ── Aerial Gym (Kulkarni et al.): Isaac-based parallel quadrotor sim
  2023.07 ── 3DGS published
  2024.03─10 Splat-Nav, GS-Splatter, Aerial Gym + 3DGS: fit real scene → render
  2025 ───── Default config: 3DGS renderer + Isaac/Aerial Gym dynamics + ext. wind
  Open ───── Wind, prop wake, IMU noise still need external models;
              no gaussian renderer captures aerodynamics
```

---

## 1 · System Overview

### 1.1 Component Comparison vs Splat-Sim (manipulation sibling)

| | Aerial Gym + 3DGS (drone) | Splat-Sim (manipulation) |
|---|---|---|
| 场景尺度 | 户外 100–10000 m² / 大型室内 | 桌面 1–3 m³ |
| 采集 | 测绘无人机 5–15 min | 手机 2–5 min |
| 目标渲染速率 | **多并行环境 1000+ Hz** | 单环境 30 Hz |
| 并行度 | 单 GPU 256–4096 环境 | 通常 1 环境 / GPU |
| 动力学源 | Isaac Gym / PhysX | 借自 teleop |
| 风 / 气动模型 | **外置插件**（CFD-lite 或经验） | n/a |
| IMU 噪声模型 | 外置 —— 基于 Allan-variance | n/a |
| 真飞行闭环 | yes, zero-shot transfer | yes, grasp validation |
| 可编辑性 | 低 —— 训练中场景少改 | 低到中 |
| 计算预算 `UNVERIFIED` | 每策略 8 GPU × days | 每策略 1 GPU × hours |

### 1.2 Key Mechanism

架构承诺：**3DGS 场景被当作静态、只读的相机渲染器**。它不参与动力学、碰撞、风。碰撞 query 打到从 gaussians 单独导出的 mesh（TSDF / Poisson 重建），不是 gaussians。

⚡ **Eureka Moment**：*3DGS 解决了无人机的**视觉** sim2real gap。它不假装解决**动态** sim2real gap（风、桨流、地面效应）——这些仍作独立外置模型，这种洁癖正是组合可出货的原因。*

### 1.3 Pipeline Flow

```
  survey drone / photogrammetry → 3DGS fit (30 min – 4 hr)
       ↓
  3DGS scene file (~5 GB) → export coarse mesh (collision proxy)
       ↓
  Aerial Gym env:
    - quadrotor PhysX dynamics  ← wind field model (external)
    - mesh collision            ← IMU noise model (external)
    - 3DGS render at cam pose
       ↓
  N parallel envs at 1000+ Hz aggregate → RL policy (PPO / SAC)
       ↓
  Real drone (zero-shot)
```

---

## 2 · Why a Drone Cannot Reuse the Manipulation Recipe

📌 **Napkin Formula**：
```
  Manipulation:  L = E_{view}[ policy(I_render(scene, view)) → action ]
                       (teleop labels survive; contact baked into demos)
  Drone:         L = E_{state}[ R(quadrotor(state, action, wind, IMU))
                               + π(I_render(scene, cam(state))) → action ]
                       (RL — actions invented online; dynamics must be live)
```

两点结构差异：

1. **没有 teleop 标签可借。** Splat-Sim 信任 teleop 轨迹的接触结果，只重渲像素。无人机 RL 在线发明动作，所以仿真器必须产出正确*下一状态* —— 那是动力学模型的事，不是 3DGS 的。
2. **气动不可避免。** 桨流、地面效应、阵风 —— 都不是视觉特征；都不能从 3DGS 场景推断。必须外置：学到的风场、经验 Dryden 湍流，或 Gazebo 气动插件。

> 变量：`cam(state)` 是从四旋翼状态抽出的相机位姿；`R(·)` 是动力学步。

---

## 3 · Worked Example: Urban Obstacle Avoidance

任务：训一只四旋翼 RL 策略，在带砖墙、灯柱、悬挂招牌的真实城市内庭飞行。

1. **采集。** 测绘无人机录 10 min RGB + GPS（~3000 帧）。
2. **重建。** 3DGS 拟 → ~2M gaussians、~5 GB 场景。导出 200k 三角形 mesh 作碰撞代理。
3. **包入 Aerial Gym。** mesh 进 PhysX；3DGS 接渲染管线；在共享场景上开 1024 个并行四旋翼环境。
4. **加外置模型。** Dryden 湍流峰值阵风 3 m/s。Allan-variance IMU 噪声（匹配 MPU-9250 或 BMI088）。20 ms 一阶电机延迟。
5. **训练。** PPO 在 1000+ env-Hz 聚合速率，~8 小时于 8× A100（`UNVERIFIED`）。
6. **部署。** 在真实内庭飞真机。已发布结果报告 60–85% zero-shot 成功（`UNVERIFIED`），未建模阵风为主导剩余失败。

视觉分布精确匹配，因为训练场景*就是*测试场景。这是"特定环境下的专用策略 + 光度场景重放"——比"完全 generalist 策略"更诚实的框架。

---

## 4 · Engineering View

| Component | Why it lives where it does |
|---|---|
| 3DGS 场景 | 只渲 RGB。无法服务碰撞 query（太密、无干净表面） |
| 粗 mesh | 廉价碰撞；牺牲几何保真（~10 cm）换微秒级 query |
| Aerial Gym / Isaac 动力学 | PhysX 刚体，按 1000+ 并行环境 / GPU 优化 |
| 风模型 | 经验（Dryden）或学到。数据饥渴组件 |
| IMU 噪声模型 | Allan variance + 偏置漂移；必须匹配部署硬件 |
| RL 更新 | 标准 PPO / SAC。3DGS 渲染占每步墙时 60–80% |

瓶颈是渲染——开放研究方向是**跨环境共享 tile 级 rasterization**，避免同场景被 N 次重栅格化。

---

## 5 · Data & Eval Conventions

无人机 3DGS sim2real 论文通常报告：

- **同场景 zero-shot** 成功（最高，~70–90%）
- **跨场景迁移**（~30–50%；光度优势消退）
- 机上感知延迟（~30–60 ms 目标）
- 每千米碰撞率

诚实报告必须给跨场景数字。多篇论文只报同场景并夸大泛化。

---

## 6 · Capabilities & Failure Modes

**Works**：有纹理环境下的静态避障；VIO 前端训练；monocular depth / segmentation 的 sim2real；已知环境的专用策略（工业巡检、定期配送）。

**Does not work**：未见场景的 generalist 户外飞行；高速飞行（>10 m/s）下运动模糊 / 卷帘主导（3DGS 渲完美帧）；含动态行为体的室内（gaussian 是静态）；风主导的 regime。

### 6.1 Hidden Assumptions

1. **部署环境 = 采集环境。** 多数已发表赢的是同场景迁移。这里的 "sim2real" 指动力学真实，不是场景真实——光度优势是场景特定。
2. **风 / 湍流 / 桨流可外置建模。** 阵风主导时，再高 3DGS 视觉保真也救不了策略。风场随机化训练成必需。
3. **碰撞由粗 mesh 近似。** 细障碍（线、树叶细枝）在 TSDF / Poisson 代理中消失；策略在真实里会撞上。
4. **训练期忽略卷帘、运动模糊、镜头畸变。** 3DGS 渲理想 pinhole、无快门帧。真相机在 10 m/s 给出非常不同的统计。多数生产管线未补这块。
5. **非视觉传感器靠外置噪声模型。** 正确，但集成负担落在仿真器作者；IMU 建模 bug 静默杀死 VIO sim2real。

---

## 7 · Comparison & Interview Tip

| | 3DGS in Aerial Gym | Pure Aerial Gym (no 3DGS) | Gazebo + textured terrain | NeRF in drone sim |
|---|---|---|---|---|
| 视觉真实度 | ★★★★ | ★ | ★★ | ★★★★（慢） |
| 渲染速率 `UNVERIFIED` | 100–500 Hz/env | 1000+ Hz/env | 100 Hz/env | 1–10 Hz/env |
| 最适用于 | 场景已知、视觉 gap 主导 | 动力学调参，不要求视觉迁移 | 老栈、SITL | 研究 |

🎯 **Interview Tip**：被问 *"为什么用 3DGS 而非 Gazebo 更好的纹理？"*，别答"它看上去更好"。答：**"3DGS 给我*具体*部署环境的*真实拍摄*视觉分布。对已知环境的专用策略（巡检、定期路线），3DGS 值它的算力；对 generalist 户外飞行，谁都救不了 —— 风模型与跨场景泛化才是未解问题。"**

---

## Boundary

per-method 3DGS rasterization 细节 → `foundations/3dgs-family/3dgs_original_dissection.md`。per-embodiment aerial 部署、VIO、传感器 → `embodiments/aerial/`。跨具身体 "manip vs drone vs AD 3DGS-sim" → `crossing/representation-migration/3dgs_as_simulator_comparison.md`。推理时 world model → `foundations/world-model/`。

## References

- Kulkarni et al., *Aerial Gym — Isaac Gym Simulator for Aerial Robots*, arXiv:2305.16510 (2023).
- Chen et al., *Splat-Nav: Safe Real-Time Robot Navigation in Gaussian Splatting Maps*, arXiv:2403.02751 (2024).
- Kerbl et al., *3D Gaussian Splatting*, SIGGRAPH 2023, arXiv:2308.04079.
- See also `crossing/representation-migration/3dgs_as_simulator_comparison.md`.

---

**Status:** v1 (2026-05-21). UNVERIFIED policy applies to all latency / success-rate / GPU-hour numbers.

[← Back to Generative 3D Sim](./overview.md)
