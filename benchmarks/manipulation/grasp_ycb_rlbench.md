# GraspNet-1Billion, YCB, RLBench — What Each Actually Measures (三大操作基准各自衡量什么)

**Status:** v1 — opinionated draft. Saturation rates and per-task success numbers marked `UNVERIFIED`.
**TL;DR:** 这三者并不可互换。GraspNet-1B 评的是*点云上的抓取规划*，YCB 评的是*你抓取所用的物体集*，RLBench 评的是*在 photorealistic sim 中的闭环任务执行*。声称 "we beat SOTA" 而不说清测的是哪个维度，正是操作类论文虚高数字的最大来源。

---

## 1 · 为什么会混淆

操作基准各自独立演化，却被粘到同一张表里。一篇 2024 年论文说 "98% success on YCB"，几乎必然意味着：测的是 YCB 的*子集*物体，用了*特定*夹爪，常常是*某一个*实验室的桌面装置，抓取规划用 GraspNet-1B，运动执行要么在实机要么在 RLBench。这些数字之间**不可线性组合**。

修正方式：看每个基准实际在评什么 — 以及它刻意忽略什么。

---

## 2 · 三个维度 — 对照

| Benchmark | What it evaluates | What it ignores | Modality | Year / Lineage |
|---|---|---|---|---|
| **GraspNet-1Billion** | Per-scene grasp pose quality (6-DoF) on cluttered point clouds | Whole-task execution, language conditioning, multi-step planning | RGB-D point cloud, simulation-validated grasps | 2020, SJTU (Fang et al.) |
| **YCB Object Set** | Object *coverage* — does your stack handle the canonical 77-object set? | Scene / clutter / task; it's an object library not a task suite | Physical 3D objects + meshes + textures | 2015 onward, IROS object/model set (Calli et al.) |
| **RLBench** | End-to-end task success across 100+ scripted manipulation tasks | Sim2real, true visual realism, novel object generalization | CoppeliaSim + photorealistic shaders | 2019, Imperial (James et al.) |

关键洞察：**YCB 不是 benchmark**，它是一个*物体集*。GraspNet-1B 用 YCB 风格物体但评抓取姿态；RLBench 用自己的物体但评任务。论文说 "evaluated on YCB"，往往真正的意思是 "evaluated grasping on objects from the YCB set" — 这更接近 GraspNet-1B 的维度，而不是任务级别的 benchmark。

---

## 3 · GraspNet-1Billion — 实际做的事

GraspNet-1B 提供约 1B 标注的 6-DoF 抓取姿态，覆盖约 100 个 cluttered scenes，由 RealSense + Kinect 拍摄。基准协议：

1. 输入：cluttered tabletop 的 RGB-D 或 point cloud。
2. 输出：排好序的 6-DoF grasp poses 列表（gripper pose + width）。
3. 评分：基于 force-closure simulation 的 top-K grasp success rate。

它测量的是 **grasp candidate generation**。它**不测**：
- 机械臂能否无碰撞到达该位姿
- 控制器执行抓取时是否打滑
- 是否抓到了正确的目标物体（没有语言 / 目标条件）

这就是为什么 GraspNet-1B 分数能维持高位（top methods cluster around 60–70% AP `UNVERIFIED`），而同一抓取规划器部署到真实工作站时，任务成功率往往只有 20–30%。该基准刻意把规划与执行解耦。

**Use it for:** 比较抓取姿态生成器（GraspNet baseline, AnyGrasp, EconomicGrasp 等）。
**Do not use it for:** 声称 "our system can manipulate."

---

## 4 · YCB — 大家都用的那套物体集

Yale-CMU-Berkeley Object and Model Set（Calli et al. 2015）= 77 个物理物体 + meshes + textures + sizes，涵盖厨房用品、工具、食物、形状原语。它存在的原因是 *YCB 出现之前，每篇操作论文用的物体集都不同，结果根本无法比较*。

YCB 是操作领域最接近 ImageNet 的东西 — 不是规模上像，而是角色上：一个 "你的方法是否能在现实日常物体上泛化？" 的共享坐标。任何不在至少 YCB 子集上做测试的论文，都会被打上 cherry-picked 标签。

YCB **不**指定的东西：
- 一个任务
- 场景布局
- 成功度量
- 传感器装置

两篇论文都可以声称 "98% on YCB"，但测的可能完全是两回事。永远要问：哪个子集、哪个任务、哪个夹爪、什么样的杂乱程度。

衍生任务套件 — **YCB-Video**（物体姿态跟踪）、**YCB-Sim2Real** challenges、**YCBInEOAT**（手内操作）— 在物体集之上增加了结构。

---

## 5 · RLBench — 三年前就有的 LIBERO 问题

RLBench（James et al. 2019）将 100+ 操作任务打包进 CoppeliaSim，配上 photorealistic shaders、语言描述和示范生成。它看起来就是 vision-language-action policy 的理想 benchmark — 而且确实是，*在 sim 里*。

但 sim2real 的鸿沟极其严重：

| Aspect | RLBench (sim) | Real lab |
|---|---|---|
| Visual realism | Photorealistic shaders | True multi-bounce lighting + sensor noise |
| Physics | CoppeliaSim Newton/Bullet | Real contact + friction + compliance |
| Object set | Procedural / hand-modelled | YCB / custom + manufacturing tolerance |
| Failure modes | None outside the sim's tolerance | Slip, partial occlusion, sensor dropout |

这就是 **LIBERO 问题换个名字**：在 RLBench 上拿 95% 的 policy，到同一任务的真机上常掉到 20–40% `UNVERIFIED`。LIBERO（Liu et al. 2023）做了同样的架构选择 — *看起来真实但物理薄弱*的 sim — 整个领域因此把同一悬崖踩了两次。

判别法：如果论文报 RLBench 数字但没有真机消融，把头条数字当作 *policy 表征能力的上界*，而不是部署就绪信号。

**RLBench 之所以仍有价值**，是因为它是 policy 大规模消融最便宜的方式（每个任务每天 1000+ episodes）。它就不是个部署代理。

---

## 6 · 怎样读操作类论文

看到 "98% success on benchmark X" 时，按这样拆解声明：

1. **哪个维度？** Grasp planning (GraspNet-1B)、object coverage (YCB-derived)、task execution (RLBench / LIBERO / CALVIN)，还是真机？
2. **报的是哪个子集？** YCB 有 77 个物体，RLBench 有 100+ 任务，GraspNet-1B 有 100 个场景。论文常 cherry-pick。
3. **Sim 还是 real？** Sim 数字不迁移；real 数字跨实验室迁移也很糟糕。
4. **是否交叉验证？** 同一方法是否在这些维度的 ≥2 上都报了？没有就要怀疑过拟合。

2024–2026 高质量操作论文的常态是：*至少一个 sim benchmark + 一个可复现的真机评测*（RT-2 lineage、Octo、OpenVLA）。把这当作新基线。

---

## 7 · 关于饱和度

`UNVERIFIED` 但大致是：GraspNet-1B AP 从 ~30% (2020) 爬到 ~70% (2024 SOTA)，大概率即将 plateau；RLBench top methods 已贴近单任务上限 — 难关变成了多任务泛化；YCB 作为物体集天生无法饱和，它是坐标不是度量。迁移方向是真机评测（RoboArena、RoboCasa real splits）和跨 embodiment policy benchmarks（Open X-Embodiment）。

---

## Boundary

本文比较三个基准的评分维度。Per-policy 拆解（Diffusion Policy、ACT、OpenVLA、π₀）住在 `bridge-to-vla/` 和 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 的 policy benchmarks。物体集工程（夹爪选型、夹具设计）归 `deployment/`。

## References

- GraspNet-1Billion — Fang et al. *CVPR 2020*. https://arxiv.org/abs/2006.05400
- YCB Object and Model Set — Calli et al. *Adv. Robotics 2017*. https://www.ycbbenchmarks.com/
- YCB-Video — Xiang et al. *RSS 2018*. https://arxiv.org/abs/1711.00199
- RLBench — James et al. *RA-L 2020*. https://arxiv.org/abs/1909.12271
- LIBERO — Liu et al. *NeurIPS 2023*. https://arxiv.org/abs/2306.03310
- Open X-Embodiment — Padalkar et al. 2023. https://arxiv.org/abs/2310.08864
