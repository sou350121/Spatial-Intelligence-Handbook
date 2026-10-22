[//]: # "<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: hybrid
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# 何处触、如何触：面向几何感知的虚实迁移操作的分层 RL–MPC 框架 (Where to Touch, How to Contact: A Hierarchical RL–MPC Framework for Geometry-Aware Sim-to-Real Manipulation)

> **发布时间**：2026-08-19（arXiv v5, cs.RO）
> **论文 / 模型名**：RL–MPC Hierarchical Framework（高层 Contact Intention + 低层 ComFree-MPC）
> **核心定位**：把「在哪接触（几何）」交给 RL、「如何通过接触动力学实现（非光滑物理）」交给 contact-implicit MPC，用一个 object-centric 的 *Contact Intention* 接口解耦两层——比端到端 RL 省约 40× RL decision steps，并能零样本 sim-to-real。

端到端策略把几何推理和非光滑接触动力学塞进同一个网络，数据饥渴且迁移差。本文的核心主张是：灵巧操作天然分层——高层决定「摸哪里、把物体推到哪个中间位姿」，低层用 MPC 在线解接触模式（滚动/粘滞/滑动/脱离）。这样 RL 只需学可迁移的几何/运动学，接触动力学由物理模型兜底。

---

## X-Ray 开场

**解决什么问题**：接触丰富的非抓取操作（推动、翻转、借环境翻面）需要同时推理全局几何与非光滑接触动力学，端到端 RL 数据效率低、sim-to-real 迁移差；纯 MPC 又短视、易陷局部最优。

**提出了什么**：一个分层框架。高层 RL 策略输出 *Contact Intention*——物体表面接触点 + 接触后的物体子目标位姿；低层 *ComFree-MPC*（complementarity-free、准动态接触模型）以该 intention 为代价条件，在线优化机器人动作序列。

**对 spatial AI 研究者意味着什么**：它把「几何表征」和「物理动力学」显式拆成两个可独立验证的模块，并用 object-canonical 三组件观测（几何 / 目标流 / 碰撞间隙）证明了 object-centric 表征对策略学习稳定性的决定性作用——Ablation 2 里仅把目标流换到世界系，学习就直接失败。

---

## 📍 研究全景时间线

```
接触隐式规划 (contact-implicit planning)
   └─ 自动发现 contact modes，但短视 / 局部最优
        │
        ▼
RL–MPC 分层（先在 locomotion 成熟）
   └─ 学习高层决策 + 模型低层控制
        │
        ▼
RL–MPC 进入 manipulation
   ├─ RL 学可变形物体 latent dynamics → 喂 MPC
   ├─ RL 学接触动力学模型 / 给采样 MPC 做 warm-start
   └─ RL 预测末端中间目标 → MPC 跟踪
        │
        ├── HACMan (2023)：flat RL 同时学 where + how
        ├── PushAnything：采样接触点 + MPC 评估
        ├── HiDex：MCTS 选接触 + 路径规划
        └── HDP：diffusion 分层做接触预测 + 轨迹生成
        │
        ▼
★ 本文 (2026-08)：RL 只做几何 → Contact Intention → ComFree-MPC 做接触动力学
        │
        └─ 局限：依赖准确物体位姿追踪；离散 keypoint 集合在多末端执行器时组合爆炸
```

本文在演进中的位置：它**不是**第一个提出「where to touch / how to contact」分解的（HACMan 已提出该口号），但它是第一个把 *how* 彻底外包给 contact-implicit MPC、并让 RL 只输出 object-level 接触意图的工作。差异点在于接口设计：HACMan 的 action 是「接触点 + 末端位移」，仍需 RL 隐式学接触动力学；本文的 action 是「接触点 + 物体子目标位姿」，接触动力学完全由 ComFree-MPC 承担。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **高层 RL 策略** π | 三组件 object-canonical 观测 `o_k = (P, ΔP_k, D_k)`：物体表面 keypoints、每点目标流、每点环境间隙 | Contact Intention `I_k = (c̄^1..c̄^n, q̄^obj)`，n=1（stick） | **训练**：仅在 abstract-robot 仿真（末端抽象为 mass–spring–damper 质点）中用 PPO 训练；**推理**：zero-shot 用于 full robot / 真机，无需微调 |
| **Contact Intention 接口** | 高层输出 | `I_k ∈ G^n × SE(3)` | 无参数；是两层之间的抽象动作空间 |
| **低层 ComFree-MPC** | `I_k` + 当前环境状态 `x_env` | 机器人动作（只执行第一个控制输入） | **无训练**：每个控制步在线解优化；~100 Hz receding-horizon |
| **子目标参数化（两种）** | — | Option 1：MPC 权重 `(w_pos, w_ori)`；Option 2：从预定义候选集 `Q` 选 `q̄^obj` | 训练时二选一，推理一致 |

关键点：高层策略的动作是**物体级意图**而非机器人动作，因此可用抽象末端训练、再配不同机器人的 MPC 部署——这是零样本迁移的结构性前提。

### 1.2 关键机制

**⚡ Eureka Moment：把「接触动力学」从 RL 的动作空间里彻底删掉——RL 只输出一个物体级的*接触意图*（摸物体表面哪一点 + 接触后物体应到达哪个中间位姿），非光滑的滚动/粘滞/滑动/脱离全部由 contact-implicit MPC 在线解。**

这个洞见的三重收益论文明确列出：(I) 数据效率——RL 只学几何/运动学，接触动力学不学；(II) 比纯 MPC 有全局规划——高层选接触点和子目标，把短视的 MPC 引导出局部最优；(III) 可迁移——几何/运动学比接触动力学在仿真里更可信。

支撑该洞见的一个**次级设计**同样关键：观测必须是**一致的 object-canonical 表征**。Ablation 2 显示，仅把目标流 `ΔP` 从物体系换到世界系（几何 `P` 仍在物体系），学习直接失败——策略被迫重新发现「依赖物体位姿的变换」。

### 1.3 信息流 / 架构图

```
                      ┌──────────────────────────────┐
                      │  高层 RL 策略 π (PPO)          │
   观测 o_k ──────────▶│  PointNet++ / MLP backbone    │
   (P, ΔP_k, D_k)      │  → action logits              │
   物体正则系            └──────────────┬───────────────┘
                                       │ Contact Intention
                                       │ I_k = (c̄, q̄^obj)
                                       ▼
                      ┌──────────────────────────────┐
                      │  低层 ComFree-MPC (~100Hz)    │
   当前状态 x_env ────▶│  min Σ L(p_ee, c̄) + V(q_H, q̄^obj) │
                      │  s.t. x_{t+1}=ComFree(x_t,u_t) │
                      └──────────────┬───────────────┘
                                       │ 只取 u_0
                                       ▼
                                  机器人动作
                      ┌──────────────────────────────┐
                      │ 执行 T 个 env steps 后，       │
                      │ 高层重新出 intention (多速率)  │
                      └──────────────────────────────┘
```

多速率耦合：低层 MPC 执行 `T` 个环境步，高层 intention 在此期间保持不变；`k` 记高层决策步，`t` 记低层控制步。

---

## 2 · 数学核心

📌 **Napkin Formula**：
```
I_k = π(o_k) = ( c̄ , q̄^obj )                    ← 高层：几何意图
u* = argmin Σ_t w_c‖p_t^ee − T_obj^w c̄‖² + V(q_H, q̄^obj)
     s.t. x_{t+1} = ComFree(x_t, u_t)            ← 低层：接触动力学
```
直觉：高层说「摸这个点、把物体带到那个中间姿态」，低层用物理模型解「怎么摸才能到」。

### 目标 → 公式 → 变量 → 直觉

**① Contact Intention 定义（Eq. 1）**

```
I = (c̄^1, c̄^2, …, c̄^n, q̄^obj) ∈ G^n × SE(3)
```

- `c̄^i ∈ G`：物体表面 `G` 上的接触锚点，对应第 i 个主动接触点（stick 末端时 n=1）。
- `q̄^obj ∈ SE(3)`：接触后的物体子目标位姿，**不必等于**最终目标 `q̄^target`，而是朝目标推进的中间位姿。
- 直觉：把「摸哪里」和「摸完物体应变成什么样」打包成一个物体级动作，机器人无关。

**② 低层 MPC 目标（Eq. 2）**

```
min_{u_0:H−1}  Σ_{t=0}^{H−1} Σ_i L(p_t^{ee,i}, c̄_k^i) + V(q_H^obj, q̄_k^obj)
s.t.  x_{t+1} = ComFree(x_t, u_t),  x_0 = x_env
```

- `H`：MPC 前瞻步数（论文正文未给具体值，见 Appendix A.6）。
- `L`：running cost，拉末端接触点 `p_t^{ee,i}` 靠近意图接触点。
- `V`：terminal cost，拉物体到子目标。
- `ComFree`：complementarity-free 准动态接触模型（引 [27]），使 receding-horizon 优化足够快。

**③ Running cost 具体形式**

```
Σ_i L(p_t^{ee,i}, c̄_k^i) = Σ_i w_c ‖ p_t^{ee,i} − T_obj^w c̄^i ‖²
```

- `T_obj^w`：把物体系接触点变换到世界系。
- `w_c`：接触贴合强度超参。

**④ 子目标 Option 1（Eq. 3）——用 MPC 权重隐式定义子目标**

```
V(q^obj, q̄^obj) = w_pos · e_pos(p^obj, p̄^target) + w_ori · e_ori(r^obj, r̄^target)
```

- `(w_pos, w_ori)` 由 RL 输出。例：`(1,0)` 表示子目标只要求位置到位。
- 直觉：不在 `SE(3)` 里回归一个位姿，而是让 RL 选「这一阶段更在乎平移还是旋转」，把连续回归降成低维选择——直接缓解 RL 在 `SE(3)` 上的搜索难度。

**⑤ 子目标 Option 2——离散候选集**

```
q̄^obj ∈ Q = { q̄_1^obj, …, q̄_M^obj }
```

- 从预设的、朝最终目标有意义的中间位姿集合里选一个，进一步把动作空间离散化。

---

## 3 · 带数字走一遍（玩具设定，非论文实验）

**设定（明确为教学玩具）**：二维平面推动。物体视为质点，起点 `(0,0)`，目标 `(1.0, 0)`；障碍在 `(0.5, 0)`、半径 0.2。末端每步可沿 `+x` 或 `+y` 推 `Δ=0.2`。MPC horizon `H=1`，terminal cost 为欧氏距离平方。

**无子目标（contact-only 变体，对应 Ablation 1）**：

| 步 | 物体位置 | 可选动作 → 下一位姿 | 到目标的 cost |
|---|---|---|---|
| 0 | (0,0) | +x → (0.2,0) | 0.64 |
| 1 | (0.2,0) | +x → (0.4,0) | 0.36 |
| 2 | (0.4,0) | +x → (0.6,0) | 0.16（撞障碍区）|
| 3 | (0.6,0) | 被障碍挡住，无法继续 +x | — |

MPC 的贪心 terminal cost 一直把物体往 `+x` 推，直到撞上障碍后无路可走；若 64 步内到不了目标即失败。这正是论文 Ablation 1 观察到的现象——去掉子目标后 pushing 成功率从 `100% ± 0.0%` 掉到 `20.62% ± 11.02%`，因为 MPC 直接冲最终位姿会陷入局部极小。

**有子目标（本文）**：RL 选 `c̄ = 物体侧面`、`q̄^obj = (0.5, 0.4)`（绕过障碍的中间位姿）。

| 步 | 动作 | 位置 | 到子目标 cost |
|---|---|---|---|
| 0 | +y | (0, 0.2) | 0.29 |
| 1 | +y | (0, 0.4) | 0.25 |
| 2 | +x | (0.2, 0.4) | 0.09 |
| 3 | +x | (0.4, 0.4) | 0.01 → 子目标达成 |

子目标达成后，RL 重新出意图（`q̄^obj = (1.0, 0)`），MPC 再 `+x` 两、三步即到目标。整个任务约 6–8 步完成——与论文 full sim 中 pushing 平均 `7.4 ± 6.9`（seen）/ `6.8 ± 4.6`（unseen）个 RL decision steps 的量级一致（玩具数字仅作机制演示）。

**为什么这个分解有效**：MPC 的局部最优问题来自「terminal cost 直接指向最终目标」；RL 的子目标把长程问题切成一系列短程、可达的物理子问题，每一步 MPC 都只在一个凸性较好的局部区域内优化。

---

## 4 · 工程视角

| 维度 | 论文报告值 | 备注 |
|---|---|---|
| 低层 MPC 控制频率 | **around 100 Hz** | ComFree-MPC receding-horizon |
| 高层决策 / 控制步比例 | 15K RL steps ≈ 300K control steps | 论文在 T-pushing 对比中明确，比例约 1:20 |
| 每 RL 决策对应的 MPC 执行步数 T | **论文正文未报告**（见 Appendix A.6） | 只知「MPC executes for multiple control steps」 |
| 仿真 full-system 平均 RL 决策步 | 约 10（approx. 10 on average） | 三任务综合 |
| Pushing (seen) 完成步数 | `7.4 ± 6.9` | Table 1，full sim |
| Pushing (unseen) 完成步数 | `6.8 ± 4.6` | Table 1 |
| 3D Reorientation 完成步数 | `14.5 ± 9.5` | Table 1 |
| Env-contact 完成步数 | `4.0 ± 2.0` | Table 1 |
| 真机 Pushing (seen) 步数 | `6.10 ± 3.40` | Table 2 |
| 真机 Pushing (unseen) 步数 | `7.35 ± 4.73` | Table 2 |
| 真机 3D Reorientation 步数 | `24.96 ± 15.5` | Table 2 |
| 真机 Env-contact 步数 | `5.92 ± 4.35` | Table 2 |
| 训练 RL steps（pushing） | ~40k 达到 100%/99.69% | 学习曲线 |
| 训练 RL steps（reorientation） | ~200k 达到 96.56% | 学习曲线 |
| 训练 RL steps（env-contact） | ~120k 达到 98.44% | 学习曲线 |
| 机器人硬件 | 7-DOF Franka + stick end-effector | §6 开头 |
| MPC 单次求解延迟 (ms) | **论文未报告** | 仅给 ~100Hz |
| GPU 型号 / 训练 wall-clock / VRAM | **论文未报告** | — |

**Trade-off 解读**：
- **多速率设计的代价**：高层 intention 在 `T` 个控制步内冻结。若 `T` 太大，物体状态漂移后意图过时；太小则高层频繁推理、且 MPC 来不及执行完一个子目标。论文未报告 `T` 的取值，但 full sim 平均 ~10 个高层步完成 pushing 说明 `T` 与任务时长匹配。
- **抽象末端训练的红利**：高层在 mass–spring–damper 质点上训练，MPC 求解更快 → 加速 RL；部署时只加机器人特定的 ComFree-MPC，不需重训。代价是真实机器人需「minimally tuned」少量物理参数（mass、stiffness 等，Appendix A.6）。
- **无训练低层**：MPC 每步在线优化，没有策略网络推理开销，但优化求解是延迟瓶颈（论文只给 ~100Hz 的总体频率，未拆解单次 solve 时间）。

---

## 5 · 数据与评测

**任务设置（三个非抓取任务，全部 7-DOF Franka + stick 末端）**：

1. **Geometry-generalized pushing**：把多样字母形状物体从随机初始位姿推到平面目标。训练字母 `(E, H, L, N, T, X)`，留出测试 `(F, I, K, V, Y, Z)`——直接检验几何泛化。
2. **Pivoting-flipping based object reorientation**：把立方体从随机初始位姿重定向到随机 3D 目标，需要 toppling / pivoting / sliding 等更丰富的接触策略。
3. **Environment-assisted object repositioning**：把楼梯上的长方体物体翻到桌面目标位姿，需要利用楼梯边缘的环境接触（先借楼梯转 90° 再完成翻转）。

**训练设置（§6.1）**：
- 高层策略用 **PPO** 训练；每 episode 随机物体与目标位姿；pushing 每 episode 采样一个训练物体。
- 域随机化：mass、friction、end-effector actuation。
- 每任务 **5 次独立训练**，每 checkpoint 用 **64 trials** 评估，每 trial 随机起止位姿。
- 成功判据：物体在 **64 RL policy steps** 内足够接近目标。

**仿真评测规模**：pushing 每字母 **5 trials**；3D reorientation 与 env-contact 各 **20 trials**。

**仿真结果（Table 1，abstract → full）**：

| Task | Success (Abstract) | Success (Full) | Steps (Full) |
|---|---|---|---|
| Pushing (seen) | `100% ± 0%` | `100% ± 0%` | `7.4 ± 6.9` |
| Pushing (unseen) | `99.69% ± 0.62%` | `100% ± 0%` | `6.8 ± 4.6` |
| 3D Reorientation | `96.56% ± 2.50%` | `95% ± 5.48%` | `14.5 ± 9.5` |
| Env-contact task | `98.44% ± 1.98%` | `95% ± 3.16%` | `4.0 ± 2.0` |

**基线对比（abstract 末端）**：
- **End-to-end RL**（T-pushing）：`~600K` RL steps 后达 `83.44% ± 13.89%`；本文 `15K` steps 达 `100% ± 0%`（≈`300K` control steps）→ 约 `40×` RL decision steps、约 `2×` control steps 的改进。
- **HACMan-style**（reorientation）：约 `300K` steps 达约 `96.25% ± 7.50%`；本文 `200K` steps 内达 `96.56% ± 2.50%`。
- **MPC-only**（T-pushing）：成功率 `0%`——contact-implicit MPC 短视，无高层几何规划几乎必败。

**Ablation**：
- Ablation 1（去掉 subgoal）：pushing `100% ± 0.0%` → `20.62% ± 11.02%`。
- Ablation 2（`ΔP` 换世界系）：学习失败。
- Ablation 3（去掉 collision 组件 `D_k`）：reorientation `96.56% ± 2.50%` → `75.00% ± 29.33%`。

**真机评测（Table 2）**：pushing 每字母 **10 trials**，reorientation 与 env-contact 各 **25 trials**。

| Task | Success rate | Num. steps |
|---|---|---|
| Pushing (seen) | `100.0%` | `6.10 ± 3.40` |
| Pushing (unseen) | `95.0%` | `7.35 ± 4.73` |
| 3D Reorientation | `100.0%` | `24.96 ± 15.5` |
| Env-contact task | `88.0%` | `5.92 ± 4.35` |

**真机基线（pushing-T）**：end-to-end `35%`，MPC-only `0%`。

**评测条件说明**：所有真机结果均为 zero-shot——高层策略直接从 abstract-robot 仿真迁移，**无任何 fine-tune / post-training**，只加一个 ComFree-MPC 并最小调少量物理参数。

---

## 6 · 能力与失败模式

### 能做（具体）

- **几何泛化**：单一策略在 6 个训练字母上 `100% ± 0%`，在 6 个**未见过**字母上仿真 `99.69% ± 0.62%`、真机 `95.0%`。
- **丰富接触策略涌现**：reorientation 中末端可纯靠顶面摩擦滑动、绕棱 pivoting、绕角 pivoting；env-contact 中可借楼梯边缘 sliding / pivoting / nudging / toppling 完成翻面。
- **零样本 sim-to-real**：三任务真机成功率 `100.0%` / `95.0%` / `100.0%` / `88.0%`，无微调。
- **数据效率**：pushing 仅 `15K` RL steps 达 `100%`，对比端到端 `600K` steps 才 `83.44% ± 13.89%`。
- **方差更小**：HACMan-style `±7.50%` vs 本文 `±2.50%`（reorientation）。注意：标准差约 3 倍差异，**不是一个数量级**——论文归因于高方差接触动力学由 MPC 承担而非 RL 学习。

### 不能做 / 失败模式（论文明确）

- **依赖物体位姿追踪**：真机 letter I 偶尔失败，原因是 tracking failure；env-contact 真机降到 `88.0%`，论文归因于 vision tracking error。§8 明确列为第一条 limitation——goal flow 与 MPC 项都依赖准确物体位姿估计。
- **离散 keypoint 集合的扩展性**：`c̄ ∈ P` 是离散选择，多末端执行器（如四指手 n=4）会导致组合动作空间爆炸（§8 第二条 limitation）。
- **接触模型是准动态的**：ComFree 采用 quasi-dynamic 模型，适用于「relatively slow non-prehensile manipulation」，高速动态接触不在验证范围。
- **仅验证 n=1（stick 末端）**：论文所有实验都是单主动接触点。

### 隐含假设 (Hidden Assumptions)

1. **物体位姿可被稳定追踪**：`ΔP_k`（目标流）与 MPC terminal cost 都建立在物体位姿之上；遮挡、快速运动、反光材质会直接破坏意图质量。这是真机 letter I 与 env-contact 掉点的根因。
2. **物体几何可用关键点集 `P` 充分近似**：接触点只能从 `P` 中选，`P` 的密度/分布决定了几何表达上限；对细长、薄壁、非凸物体可能漏掉关键接触锚点。
3. **准动态接触足够**：忽略惯性主导的冲击/弹跳，假设操作准静态——对快速抛掷、动态捕获不成立。
4. **环境几何可观测**：`D_k`（每点环境间隙）需要知道障碍/楼梯/桌面的位置；env-contact 任务依赖对楼梯几何的准确建模。
5. **高层意图与机器人本体解耦**：假设在 mass–spring–damper 抽象末端上学到的几何策略可直接迁移到真实 7-DOF 臂 + stick；这依赖「几何/运动学比接触动力学更可迁移」的经验假设，论文未给出该假设的独立验证。
6. **子目标可离散化 / 低维参数化**：Option 1（权重）或 Option 2（候选集）都假设存在一小组有意义的中间位姿；对开放世界任务，预定义候选集可能覆盖不足。
7. **MPC 在子目标引导下可局部求解**：仍然依赖优化器在 `H` 步内找到可行接触序列；若子目标本身物理不可达（例如被环境挡住），MPC 会失败而 RL 无从得知。

---

## 7 · 与相关工作对比

| 方法 | 高层角色 | 低层角色 | 动作空间 | 数据效率 / 性能 | 关键差异 |
|---|---|---|---|---|---|
| **End-to-end RL** | 无（单一策略） | 无（网络直接出动作） | 末端动作 | `600K` steps → `83.44% ± 13.89%`（T-pushing） | 需大量数据，接触动力学隐式学，迁移差 |
| **HACMan-style** | flat RL 同时学 contact + displacement | 无模型 | `P × [−0.1,0.1]^3` | ~`300K` steps → 约 `96.25% ± 7.50%`（reorientation） | 口号相同（where/how），但 how 仍由 RL 隐式学 |
| **PushAnything** | 采样接触点 | MPC 评估 | 采样 | — | 无学习高层，采样低效 |
| **HiDex** | MCTS 选接触 | 路径规划 | 离散 | — | 树搜索，非 RL |
| **HDP** | diffusion 接触预测 | 轨迹生成 | 连续 | — | 生成式分层 |
| **MPC-only** | 无 | contact-implicit MPC | 机器人动作 | `0%`（T-pushing） | 短视、局部最优 |
| **本文** | RL 出 Contact Intention（接触点 + 物体子目标） | ComFree-MPC 解接触动力学 | `G^n × SE(3)`（物体级） | `15K` steps → `100% ± 0%`；`200K` → `96.56% ± 2.50%` | how 完全外包给物理 MPC；RL 只学几何 |

**方差对比的正确读法**：论文报告本文 `96.56% ± 2.50%` vs HACMan-style 约 `96.25% ± 7.50%`，标准差约 **3 倍**差异（`7.50 / 2.50 = 3`），论文表述为「performance variance ... considerably small」，归因于接触动力学由 MPC 承担。**不要**把它说成「小一个数量级」——数据不支持。

**面试 Tip**：被问「你和 HACMan 都讲 where/how 分解，区别是什么？」——答：HACMan 的 how 仍然是 RL 学的（action 是末端位移），接触动力学被隐式编码进策略；本文把 how 换成 contact-implicit MPC 的在线优化，RL 的 action 升维到物体级（接触点 + 物体子目标），所以 RL 只需学几何，接触动力学零学习。这带来两个可量化后果：pushing 上 `15K` vs `600K` RL steps（约 40×），reorientation 上收敛更快且标准差从 `±7.50%` 降到 `±2.50%`（约 3×，不是数量级）。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-22)

**Repo 状态核查**：论文正文出现 "Project Link." 占位，但**截断全文内未见任何 `github.com` URL，也未见可点击超链接**。按铁律，视为 **no repo signal**——以下 pitfall **不是**来自 issue 流，而是由 §6 失败模式 + §5/§2 方法约束**推导**（未经 issue 验证）。

1. **物体位姿追踪抖动 → 意图质量崩塌**
   - *方法约束*：`ΔP_k`（目标流，§4）与 MPC terminal cost `V(q_H^obj, q̄^obj)`（Eq. 2/3）都以物体位姿为输入。
   - *失败模式*：§6 明确「letter I 偶尔失败 due to tracking failure」「env-contact 真机 88% likely caused by vision tracking error」。
   - *推导 pitfall*：任何基于视觉/mocap 的位姿估计在遮挡或快速运动下抖动，会同时污染高层观测与低层代价，且两层误差叠加——不是单点降级，而是意图与执行同时失配。

2. **离散 keypoint 动作空间随接触点数组合爆炸**
   - *方法约束*：`c̄^i ∈ P`，动作空间 `G^n × SE(3)`（Eq. 1）；§8 明确「discrete keypoint set ... could scales poorly with multiple end-effectors due to the combinatorial action space」。
   - *失败模式*：本文所有实验 n=1；n=4（四指手）时离散组合数随 n 指数增长。
   - *推导 pitfall*：直接把该框架扩到多指手会遭遇 action logits 维度爆炸与探索效率骤降，需要连续化接触点回归或层级采样——论文未提供方案。

3. **准动态接触模型对高速/冲击任务失效**
   - *方法约束*：§5 明确采用「quasi-dynamic complementarity-free contact model ... for our relatively slow non-prehensile manipulation task」。
   - *失败模式*：所有任务都是慢速推动/翻转；无高速抛掷、动态捕获验证。
   - *推导 pitfall*：把 ComFree-MPC 用于需要惯性/冲击主导的接触（如击打、抛出接住），模型假设破裂，MPC 预测与真实偏离，而高层 RL 从未见过这类动力学，无法补偿。

4. **真实机器人 MPC 物理参数仍需手工最小调参**
   - *方法约束*：§7 明确 zero-shot 迁移「only requires to add a ComFree-MPC controller with few physical parameters minimally tuned for the hardware (e.g., few mass and stiffness parameters)」。
   - *失败模式*：论文称 "minimally tuned"，但未量化参数敏感度。
   - *推导 pitfall*：换机器人/换末端（stick 质量、刚度不同）时，`w_c`、mass、stiffness 需重调；若参数偏差大，running cost 拉不住接触点，表现为「意图正确但执行滑脱」——这类失败在论文的真机表中不可见（只报成功率），复现时需预留调参预算。

---

[← Back to spatial-math README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（v5, 2026-08-19）· 未在真机复现的数字标 `UNVERIFIED`；论文未报告的工程指标（GPU、单次 MPC solve 延迟、训练 wall-clock、VRAM）已在 §4 明确标注「论文未报告」。

[//]: # "<!-- source: https://arxiv.org/abs/2601.10930 -->"
