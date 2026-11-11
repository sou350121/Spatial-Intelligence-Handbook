[//]: # "<!-- ontology-5axis
problem: tracking
representation: n/a
sensor: IMU
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# RedirectMimic：人形全身控制的局部动作内容重删 (RedirectMimic: Local Motion Content Redaction for Humanoid Whole-Body Control)

> **发布时间**：2026-11-10（arXiv:2611.14049v1 [cs.RO]）
> **论文 / 模型名**：**RedirectMimic**（Zepeng Wang, Xiaochuan Shi†，Wuhan University）
> **核心定位**：让一个已训好的人形全身跟踪器在**继续接收原始参考 m** 的前提下，把参考里被规则禁止的局部动作替换掉——靠"actor 看 m、tracking reward 看 m̃"的**观测/目标分离微调**实现，部署接口零改动。
> **Ontology 5-axis**：problem = `tracking` · representation = `n/a` · sensor = `IMU`（本体状态）· paradigm = `learned` · time = `feed-forward`

痛点：现有 motion tracker 是"忠实复现机器"——但你真正要的是"除了这个动作以外都照做"。直接对目标肢体做 reward zeroing 或 anti-tracking 只能**取消跟踪激励**，并没有**指定替代动作**；本文的结论是：把替代轨迹显式写进奖励（而不是写进观测），才能从"压掉"走到"改对"。

## X-Ray

跟踪类策略的输入和它的监督信号一直被绑死在一起（observation = m，reward 也算 m）。RedirectMimic 把这两者**拆开**：部署时 actor 仍然只看原始参考 m（不变的前馈接口、无未来帧、无 edit mask），但 PPO 微调时的追踪奖励改成对照一条**离线规则生成的编辑后参考 m̃**。于是策略学会"看到某段动作 → 执行另一段动作"，而不用在推理时知道"现在该编辑了"。对人形/空间智能研究者的意义：**behavior redaction 可以从"抑制"变成"重定向"，而且不需要改部署栈**——代价是它只在仿真、已知 clip 上被验证过。

## 📍 研究全景时间线

```
2018  DeepMimic ────────── 物理仿真模仿学习的范式起点
      │
      ├─ AMP（style reward）
      │
2023~ PHC / ExBody / ExBody2 ── 大规模动作库 + 全身跟踪，运动先验规模化
      │
2024~ GMT（自适应采样 + 专家）/ SONIC（scaling）/ HOVER（多模态蒸馏）
      │        / TWIST（RL+BC）/ BeyondMimic（tracking 形式化，本文的 mjlab 底座）
      │
      ├── 分支 A：动作生成侧的可编辑性
      │     MoMask / CondMDI / DartControl / MaskedMimic（motion inpainting）/ CLoSD
      │     Human Motion Unlearning / SafeMo（生成侧"遗忘"某类动作）
      │
      └── 分支 B：策略侧的行为干预
            ForgetMimic（整段 clip 抑制指定行为）
            Behavior Uncloning（把 redirection 编进权重，推理时不加引导）
                    │
                    ▼
        ★ RedirectMimic (2026.11)：局部 + 显式替代目标 + 保留原始输入
                    │
        局限：仅 Unitree G1 仿真、仅"已知 clip"、非流式、
              过渡时机（transition timing）不受控、未上真机
```

本文站在**分支 B 的末端**：它把分支 A 的"局部编辑"思想搬进了策略微调，但刻意拒绝分支 A 的代价（推理时需要 mask / 未来帧 / 编辑后参考）。

## 1 · 核心架构 / 方法总览

### 1.1 组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| 离线编辑器 `E`（规则） | 完整原始 clip `m`、内容规则（pose 阈值或速度阈值）、替代目标 `q*` | 成对参考 `m̃ = E(m)`（含位置/姿态/速度目标） | **只在离线跑**，需要整段 clip 定位 core 区间 `C` 与扩展区间 `I`；部署时不跑 |
| 成对参考库 `M̃` | `m ∈ M`（7,509 clips） | `{m ↦ E(m)}` 字典 | 训练时查表；S2 过滤后 6,650 clips |
| Actor `π_θ` | `o_t = Obs(s_t, m_t)`：机器人状态 + **原始**参考当前帧 + 上一动作 | 全身动作 `a_t` | 训练/推理**完全同构**（无未来帧、无 clip id、无 edit mask） |
| Critic `V_φ` | rollout 数据 | 价值 | 与 actor 一起被 PPO 更新 |
| `R_track` | `s_t` vs **`m̃_t`** | 追踪奖励（anchor pose + 相对 body pose + 线/角速度） | **只在训练时**指向 m̃；推理时不计算 |
| `R_reg` | `(s_t, a_t)` | 正则（沿用预训练权重与项） | 不变 |
| `Q_base`（失败驱动采样） | 历史 episode 失败率 | 起始帧分布 | 反馈**只用 base-sampled episode**，保持难度估计干净 |
| `Q`（混合采样） | `Q_base`、编辑池 `𝒫` | 起始帧分布 | 见 Eq.(4)，`ρ = min(ρ_max, κ p_pool)` |

### 1.2 关键机制

**⚡ Eureka Moment：把"该做什么"从观测搬到奖励里——actor 永远看 `m`，奖励永远看 `m̃`，于是"局部重删"变成一个不需要改部署接口的微调问题。**

三个支撑点缺一不可：

1. **成对参考的构造**（III-B）：逐关节权重混合 `q̃ = (1-w)q + w q*`，`w` 在进入段平滑升到 1、core 区间保持 1、退出段回到 0；对其它关节与区间外恒为 0 → **root 轨迹与未编辑关节逐字保留**。改关节角会带动子体，所以必须**前向运动学重算 body pose，并对编辑后的动作重新差分出速度**（这是工程复现最容易漏的一步）。
2. **同时间轴对齐**（III-C）：两份参考共享时间轴与同一 anchor 对齐，奖励在"actor 原始输入所代表的相位"上评估替代动作；episode 从 `m` 初始化，保证"从原始运动状态出发去够到替代姿态"这一段被训练到。
3. **编辑窗稀疏采样**（III-D）：替代目标只占时间轴的一小片（占比 `p_pool`），靠 `ρ` 放大曝光但用 `ρ_max` 封顶，避免挤掉动作库其余部分的覆盖。

### 1.3 信息流

```
                 ┌──────────── 离线（一次性）────────────┐
   m (7,509 clips)│  content rule → C, I                 │
        │        │  blend q̃=(1-w)q+wq*  → FK 重算 body  │
        │        │  → 差分得速度目标 → 校验规则         │
        │        └──────────────┬───────────────────────┘
        │                       ▼
        │                  m̃  (成对参考库 M̃)
        │                       │
        ▼                       │  (只在算奖励时用)
  ┌───────────┐   o_t          │
  │  Actor    │◄────────┐       │
  │  π_θ      │         │       │
  └─────┬─────┘         │       │
        │ a_t           │       ▼
        ▼               │   ┌──────────────┐
   仿真器 mjlab ── s_{t+1}│   │ R_track(s,m̃) │──┐
   (Unitree G1, 29 DoF)  │   └──────────────┘  │
        │               │                     ▼
        └── Obs(s_t, m_t)┘             r_t = Δt[R_track + R_reg]
                                              │
                                        PPO 更新 π_θ, V_φ
                                              │
                        部署：π_θ(·|Obs(s, m))  ← 接口与预训练 tracker 完全相同
```

## 2 · 数学核心

📌 **Napkin Formula**：`π 看 m，奖励看 m̃`——`a_t ~ π_θ(·|Obs(s_t, m_t))`，`r_t = Δt[R_track(s_t, m̃_t) + R_reg]`。一行话：**用原始观测去监督一个被改过的目标**。

### 2.1 观测-目标分离（问题定义）

**目标**：在"输入仍然是原始参考"的约束下，执行替代动作。

```
o_t = Obs(s_t, m_t),     a_t ~ π_θ(·|o_t)                    (1)
```

| 变量 | 含义 |
|---|---|
| `m_t` | 原始参考在 t 帧的姿态（actor 唯一能看到的参考） |
| `m̃_t` | 编辑后参考（**仅**进入奖励） |
| `s_t` | 机器人本体状态 |
| `π_θ` | 前馈 actor；输入含当前帧参考与上一动作，**无未来帧、无 clip id、无 edit mask、无 m̃ 误差** |

**直觉**：信息约束是这个方法的核心难点——策略没有任何显式信号告诉它"这一段被编辑了"，它只能从 `m_t` 的局部形态**隐式识别场景**，然后输出被训练过的替代动作。

### 2.2 编辑算子

```
q̃_{t,j} = (1 - w_{t,j}) · q_{t,j} + w_{t,j} · q*_{t,j}        (2)
```

| 变量 | 含义 |
|---|---|
| `q_{t,j}` | 关节 j 在 t 帧的原始角 |
| `q*_{t,j}` | 应用指定的替代目标角 |
| `w_{t,j}` | 混合权重：进入段平滑 0→1，core `C` 内恒 1，`I` 结束前回到 0；**其它关节与 `I` 外恒 0** |
| `C` / `I` | core 区间（替换主体）/ 扩展区间（含进出的过渡） |
| `B` | edit support：计算速度所需的过渡与邻帧 |

**目标→公式→直觉**：先把改写限制在"受影响关节 × 时间窗"的笛卡尔积上（保 root、保其它关节），再用 FK 把关节角变化传导到子体，最后对编辑后的动作重新求速度目标——**否则位置目标和速度目标会互相打架**。构造完还要"用内容规则回检"编辑后参考确实不再含该动作。

### 2.3 训练目标与采样

```
r_t = Δt [ R_track(s_t, m̃_t) + R_reg(s_t, a_t) ]              (3)

Q = (1-ρ) Q_base + ρ U(𝒫),      ρ = min(ρ_max, κ p_pool)       (4)
```

`R_track` 沿用 BeyondMimic 的形式（anchor pose + 相对 body pose + body 线/角速度），只是目标换成 `m̃`；`R_reg` 保留预训练 tracker 的全部正则项与权重。`𝒫` 是编辑起始池（选中关节在两份参考间有差异的帧 + 同一 clip 内的 lead-in）。

### 2.4 度量

```
J_C = 1[¬D_C] · 1[¬F_H] · 1[e_C^keep ≤ 0.10 m]                 (5)

α = Σ_{t,b} ⟨x_{t,b} - m_{t,b}, m̃_{t,b} - m_{t,b}⟩ / Σ_{t,b} ‖m̃_{t,b} - m_{t,b}‖²   (8)
```

`D_C`：选中手臂在 core 区间内**累计 ≥ 0.06 s** 越过任务阈值；`F_H`：pelvis 高度在视野内任何时刻 &lt; 0.35 m；`e_C^keep`：非编辑 body 相对 `m` 的误差（torso yaw 坐标系）。`α = 1` 表示沿编辑方向完成了预期位移；表 IV 所有值都 &lt; 1。

两个 reward-level 消融（用来隔离"抑制"与"指定替代"）：

```
ZeroTrack: r_t^zero = exp[ -Σ_{b∉A_t} e_{t,b} / (N σ²) ]        (6)  ← 分母仍是 N=14
AntiTrack: r_t^anti = r_t^zero - exp[ -Σ_{b∈A_t} e_{t,b} / (|A_t| σ²) ]   (7)
```

`A_t` = 被编辑手臂关节的 tracked 子体集合，`N = 14` = 全部 tracked body 数。**保留原分母 N 是 ZeroTrack 失败的关键**（见 §3）。

## 3 · 带数字走一遍

> ⚠️ 本节是**玩具设定**：单臂、50 Hz、4 帧进入 ramp、8 帧 core。`N=14` 来自论文，`σ=0.1 m`、身体误差 0.20 m、`κ=10`、`ρ_max=0.3` 是演示取值（论文未给这些超参数值）。

**(a) 编辑算子。** 某帧肩关节 `q = 1.2 rad`（手举过头），替代目标 `q* = 0.25 rad`（上臂贴身、屈肘）。进入段 `w = 0.5` 时：

```
q̃ = (1-0.5)(1.2) + 0.5(0.25) = 0.725 rad
```

core 起点 `w = 1` → `q̃ = 0.25 rad`。FK 传导后，腕部高出肩部的高度从 `0.30 m` 降到 `0.02 m`。回到内容规则（S2：腕部高出肩 `> 0.2 m` 判为 overhead reach）：`0.30 m` 触发、`0.02 m` 不触发 → **编辑后参考通过规则回检**。同时 root 轨迹与另一条手臂的关节坐标逐字未变。

**(b) 为什么 ZeroTrack 压不下去（解释表 II 的 58.9%）。** 设手臂子体 `|A_t| = 2`，每个 body 偏离 `m` 的误差 `e = 0.20 m`，`N σ² = 14 × 0.01 = 0.14`：

| 手臂位置 | 原 reward | ZeroTrack (6) | AntiTrack (7) |
|---|---|---|---|
| 停在 `m`（手臂原姿态，`e_A = 0`） | 1.00 | **1.00（最大值）** | 1.00 − 1.00 = **0.00** |
| 移到 `m̃`（`e_A = 0.40` 合计） | ≈ 0.057 | 0.057 | 0.057 − e^&#123;-20&#125; ≈ 0.057 |
| 奖励差（`m̃` − `m` 位置） | −0.94 | **−0.94（反向鼓励回原位）** | **+0.057（弱正向，但无方向）** |

ZeroTrack 保留分母 `N`，删掉手臂误差项后奖励的**最大点恰好仍在原姿态**——手臂被其它 13 个 body 的项"拉回去"，这正是 Table II 里 Content 0.589 的机制来源。AntiTrack 把"停在原位"的奖励压到 0，于是任何偏离都更好，但它只奖励"偏离"、不指定"去哪"——所以 `α` 能到 0.71（S2）而 target distance 仍 0.273 m。RedirectMimic 在 `m̃` 处 reward ≈ 1.0，**唯一的最优点就是替代姿态**：Content 0.027、Error 0.079。

**(c) 采样混合。** 设编辑池只占时间轴 `p_pool = 0.04`，`κ = 10` → `κ p_pool = 0.4`，被 `ρ_max = 0.3` 截断 → `ρ = 0.3`：30% 的 episode 从"编辑前 lead-in + core"起手，70% 仍从 `Q_base` 起手。若 `p_pool = 0.01`，则 `ρ = 0.1`；若编辑池为空，`ρ = 0`，退回纯 `Q_base`。

**(d) 判分门（Eq.5）。** 一次 rollout：没越阈值（`¬D_C`）、pelvis 未低于 0.35 m（`¬F_H`）、保留 body 误差 0.067 m ≤ 0.10 m → `J_C = 1`。若手臂只"减速"但仍越阈值 → `J_C = 0`，即便姿态看起来接近。

## 4 · 工程视角

| 维度 | 数值 / 结论 | 来源 |
|---|---|---|
| 部署接口 | 与预训练 tracker **完全相同**：`π_θ(·|Obs(s, m))`，前馈、当前帧参考 + 上一动作 | 论文明确（Eq.1、III-A） |
| 每步内存 | `O(1)`：仅当前帧参考 + 上一动作，无未来帧缓冲、无历史的参考缓存 | 由信息约束推得（非报告数字） |
| 推理延迟 / FPS / 控制频率 | **论文未报告**（`UNVERIFIED`） | — |
| 硬件 / GPU 型号 / 显存 | **论文未报告**（`UNVERIFIED`） | — |
| 微调预算 | 15,000 PPO iterations（所有 fine-tuned 方法共享同一预算）；`K`（update 长度）、`H`（rollout 长度）以符号给出，**数值未报告** | IV-B / Alg.1 |
| 训练墙钟时间 | **论文未报告** | — |
| 训练数据侧成本 | 需为 7,509 clips 各存一份 `m̃`（S2 为 6,650 份）→ 参考库存储 ×2 | IV-A |
| 超参 `κ`, `ρ_max`, `σ`, `λ` | **论文未报告具体数值**（`λ` 被设为"总 tracking 权重"以抵消奖励） | III-D / IV-B |
| 平台 | `mjlab`（仿真，MuJoCo 系），Unitree G1 29 关节 | IV-A |
| 真机 | **未做**（future work） | V / VI |

**Trade-off 读法**：

- **最大工程卖点**：推理零成本增量。不需要在线跑编辑规则、不需要把 `m̃` 送进网络、不需要改 ONNX/TensorRT 图——所有复杂度都在训练侧。这让它可以直接叠在任意已有 tracker 上。
- **最大工程债**：编辑规则**离线跑整段 clip**。要把 `C`/`I` 的过渡放对，编辑器需要"看到"编辑前后的上下文；而 actor 只有当前帧。论文自己在 Discussion 里把这点列为对**流式控制**的时序风险（可能提前或延后进入替换区间）。
- **内容规则必须冻结**：训练与部署使用同一条规则；换了阈值就得重训，不能在线调参。
- **稀疏编辑的训练成本非线性**：`p_pool` 越小 → 需要越大的 `κ` 才能学到替换，而 `ρ_max` 封顶又限制曝光；去掉 targeted sampling 时，ablation 中 scratch 训练与 fine-tune **都保留了原内容**（即完全学不到替换）。

## 5 · 数据与评测

**仿真环境**：`mjlab`，29 关节 `Unitree G1`。所有评测在仿真内，**无真机、无真实传感器数据**。

**动作数据**：`Retargeted AMASS for Robotics`，共 **7,509 clips**；S1 用全量，S2 过滤后保留 **6,650 clips**（剔除边界腕高与"编辑后仍含 overhead reach"的参考）。消融里另用**一条 `LAFAN1` arm-mirroring motion** 做采样对照。

**两个编辑场景**：

| 场景 | 内容规则（触发条件） | 替代目标 |
|---|---|---|
| **S1**（speed-defined） | 腕部沿 shoulder→wrist 轴速度 **> 1.5 m/s** | 选中手臂收到中性姿态（上臂近躯干、屈肘） |
| **S2**（pose-defined） | 腕部高出肩部 **> 0.2 m** | 同上 |

**评测窗口**：S1 **173** 个合格窗口；S2 **149** 个窗口（跨动作源采样并筛查参考可行性）；每个窗口每个控制器 **16** 条随机 rollout，起始状态匹配。正常动作保留用**每个任务 200 条未编辑 clip**。

**指标定义**：`D_C`（core 内累计 ≥ **0.06 s** 越阈值）、`F_H`（pelvis &lt; **0.35 m**）、`e_C^keep ≤ 0.10 m`、`J_C = 1[¬D_C]·1[¬F_H]·1[e_C^keep ≤ 0.10 m]`；`α`（Eq.8，沿编辑方向完成比例）。

**主要结果（逐字照抄）**——Table II，S2 overhead-arm：

| Method | `J_C` ↑ | Content ↓ | Error ↓ | Fall ↓ |
|---|---|---|---|---|
| Pretrained | 0.245 | 0.737 | 0.238 | 0.014 |
| Vanilla-FT | 0.218 | 0.774 | 0.237 | 0.011 |
| ForgetMimic‡ | &lt; 0.001 | &lt; 0.001 | 0.258 | 0.412 [¹] |
| AntiTrack | 0.650 | 0.328 | 0.171 | 0.009 |
| ZeroTrack | 0.408 | 0.589 | 0.224 | 0.011 |
| **RedirectMimic** | **0.942** | **0.027** | **0.079** | 0.022 |
| RefEdit† (oracle) | 0.972 | 0.003 | 0.046 | 0.013 |

S1 speed-defined：

| Method | `J_C` ↑ | Content ↓ | Error ↓ | Fall ↓ |
|---|---|---|---|---|
| Pretrained | 0.725 | 0.105 | 0.177 | 0.089 |
| Vanilla-FT | 0.745 | 0.120 | 0.177 | 0.079 |
| ForgetMimic‡ | 0.000 | 0.031 | 0.416 | 1.000 |
| AntiTrack | 0.857 | 0.023 | 0.174 | 0.061 |
| ZeroTrack | **0.897** | **0.020** | 0.158 | 0.049 |
| **RedirectMimic** | 0.874 | 0.023 | **0.143** | 0.064 |
| RefEdit† (oracle) | 0.803 | 0.000 | 0.079 | 0.103 |

Table III（正常动作保留，误差为保留 body 到 `m` 的距离，单位 m）：

| Method | S1 Fall ↓ / Error ↓ | S2 Fall ↓ / Error ↓ |
|---|---|---|
| Pretrained | 0.098 / 0.070 | 0.095 / 0.070 |
| Vanilla-FT | 0.090 / 0.067 | 0.098 / 0.070 |
| ForgetMimic‡ | 0.131 / 0.078 | 0.366 / 0.151 |
| AntiTrack | 0.090 / 0.067 | 0.103 / 0.073 |
| ZeroTrack | 0.093 / 0.068 | 0.093 / 0.067 |
| RedirectMimic | 0.093 / 0.067 | 0.098 / 0.070 |

Table IV（core redirection，非跌倒 rollout；误差为 elbow–wrist 到 `m̃`）：

| Method | S1 `α` ↑ / Error ↓ | S2 `α` ↑ / Error ↓ |
|---|---|---|
| Pretrained | 0.12 / 0.283 | 0.05 / 0.389 |
| AntiTrack | 0.64 / 0.280 | 0.71 / 0.273 |
| ZeroTrack | 0.20 / 0.255 | 0.12 / 0.370 |
| **RedirectMimic** | 0.35 / **0.218** | **0.84** / **0.110** |
| RefEdit† | 0.92 / 0.080 | 0.97 / 0.056 |

> [¹] 该行在 PDF 抽取中出现 **5 个数值**（`< 0.001 / < 0.001 / 0.258 / 0.412 / 1.000`），疑为列粘连。正文只定性说明其"falls dominating both tasks"、"rarely stayed upright"；`J_C` 为 &lt; 0.001，另注 `α`/Error 列为 "–"（S1 无、S2 仅 1 条非跌倒 rollout）。该行 Fall 具体归属标 `UNVERIFIED`。

## 6 · 能力与失败模式

**能做（有数字支撑）**：

- **pose 型局部重删**：S2 content 0.027 vs ZeroTrack 0.589 / AntiTrack 0.328 / Pretrained 0.737；`J_C` 0.942，逼近 oracle RefEdit† 的 0.972，而后者在部署时直接看 `m̃`。
- **正常动作不退化**：未编辑 clip 上 Error 0.067（S1）/ 0.070（S2），Fall 0.093 / 0.098，与 Pretrained（0.070、0.098 / 0.095）同量级。
- **替代保真度**：两个任务上"匹配的局部方法中最低 replacement error"（S2 0.079、S1 0.143）；S2 上 `α = 0.84`（oracle 0.97）。
- **能识别"抑制 ≠ 替换"**：S1 上三个局部方法 suppression 都在 0.020–0.023，但 `α` 差 3 倍以上（0.20 / 0.64 / 0.35），Error 0.158–0.174 → 二元阈值验收无法区分能力。

**不能做 / 明显弱项**：

- **S1 上不占优**：`J_C` 0.874 &lt; ZeroTrack 0.897，Content 0.023 = AntiTrack 0.023。原因是"沿原路径减速"就能满足速度规则，规则本身不要求换轨迹——显式目标只改善 fidelity（Error 0.143 最低），不改善 suppression。
- **跌倒率略高**：S2 Fall 0.022 vs AntiTrack 0.009、Pretrained 0.014；oracle RefEdit† 在 S1 的 Fall 反而 0.103（比 Pretrained 0.089 还高）——高保真 ≠ 高稳定。
- **只有仿真**：无 sim-to-real、无 ASAP/AMO 式残差适配，arm-torso-legs 的动力学耦合只在 `mjlab` 里被闭环吸收。
- **只有"已知 clip"**：论文明确"results on known clips in simulation"，**未做完整流式 rollout**，未测"替换是否发生在预期窗口内"的时序正确性。
- **单一形态**：单臂、29 关节 G1、两个手工规则（速度 / 高度）；无双手协同、无手指、无移动操作。
- **场景切换无显式信号**：actor 无 clip id / mask，必须从 `m_t` 隐式判别——一旦部署参考的形态分布偏移（不同 retargeting 管线、不同风格），判别就可能失效。

### 隐含假设 (Hidden Assumptions)

1. **替代目标 `m̃` 本身物理可行**：论文用 RefEdit†（直接喂 `m̃` 的 oracle）间接证明——它在两任务上 content 0.003 / 0.000，说明目标可达；但**目标不可行时没有任何保护机制**（编辑器只回检"内容规则"，不检查动力学可行性）。
2. **部署时的 `m` 与训练同分布**：obs 里只有 `m_t`，retargeting 误差、骨骼尺度差异直接进观测，不会被奖励纠正。
3. **内容规则可由离线编辑器在完整 clip 上判定**：`C`/`I` 的边界依赖未来帧；流式时该假设破裂（Discussion 自陈）。
4. **编辑是"局部"的，靠 PPO 闭环吸收耦合**：参考的 locality 只规定"想做什么"，躯干/腿的补偿由优化自己找——若替代动作严重破坏质心，正则项未必救得回来。
5. **手臂替换不改变支撑/接触需求**：所有实验都是站立/行走中的上肢编辑，没有涉及接触切换。
6. **`Q_base` 的失败率估计只用 base episode**：这是维持"难度自适应"与"编辑曝光"解耦的前提，工程实现里很容易被写成"所有 episode 都喂给 failure sampler"从而污染难度估计。

## 7 · 与相关工作对比

| 方法族 | 代表 | 编辑粒度 | 是否有显式替代目标 | 部署输入 | 是否策略权重内化 |
|---|---|---|---|---|---|
| 大规模 tracking | PHC / ExBody2 / GMT / SONIC / HOVER / TWIST / BeyondMimic | 无编辑 | ✗ | 参考 `m` | — |
| 生成侧局部编辑 | MoMask / CondMDI / DartControl / MaskedMimic / CLoSD | 帧/片段级 inpainting | ✓（生成侧） | 文本/mask/关键帧 | ✗（生成新动作） |
| 行为抑制 | **ForgetMimic** | **clip 级** | ✗ | `m` | ✓ |
| 行为重定向 | Behavior Uncloning | 全局 | ✓（隐式） | 无推理期引导 | ✓ |
| 生成侧遗忘 | Human Motion Unlearning / SafeMo | 潜码/片段 | 部分 | — | ✗ |
| 奖励层消融 | ZeroTrack / AntiTrack（本文基线） | body × 时间窗 | ✗ | `m` | ✓ |
| **本文** | **RedirectMimic** | **关节 × 时间窗（core 区间内保其余）** | **✓（`m̃` 进奖励）** | **`m`（不变）** | **✓** |
| Oracle | RefEdit† | 同上 | ✓ | **`m̃`（变）** | 不需训练 |

一句话定位差异：**ForgetMimic 回答"别再做这个"，本文回答"改成做那个"，而且不许改部署输入。**

### 面试 Tip

被问"和 ForgetMimic / reward shaping 的区别是什么，为什么不直接 zero reward"：

> "因为 zero reward 只是**取消激励**，最优策略仍然是回到原轨迹——我用 `N=14` 的分母算给你看：删掉手臂那两项之后，奖励的最大点还在原姿态，所以它的 content 还有 0.589。AntiTrack 把原位奖励压到 0，手臂会乱走，`α` 能到 0.71 但 target error 0.273 m。RedirectMimic 把奖励换成对 `m̃` 的追踪，最优点就是替代姿态，content 0.027、error 0.079。代价是：换成 `m̃` 只能在训练时做，部署时 actor 还是只看 `m`——所以这不是'推理时编辑'，是'把编辑学进权重'。"

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-11)

**Repo 状态**：全文只给出 project page `https://xiaopeng-whu.github.io/RedirectMimic/`，**未出现任何 github.com 代码仓库链接**（无 repo URL、无 commit、无 issue 流）。因此本节**没有经过 issue 验证**；以下 3 条由 §6 失败模式 + 方法约束**推导**，标注为待验证。

**P1 · 用二元阈值当 KPI 会选错控制器（机制派生）**
- 派生自 §6 失败模式："S1 上沿原路径减速即可满足速度规则"。
- 派生自方法约束：S1 的 content rule 是 `v > 1.5 m/s` 的**标量阈值**，且 `m̃` 只规定"上臂近躯干、屈肘"的末端姿态，不约束路径。
- 后果：ZeroTrack 在 S1 拿到最低 Content（0.020）与最高 `J_C`（0.897），但 `α` 只有 0.20、Error 0.158——如果验收只看 suppression，你会部署一个"其实什么都没改、只是变慢"的策略。
- 工程动作：验收必须 **suppression + `α` + target distance + fall** 四项同时看（这也是论文 Eq.5/Fig.4 双栏设计的原因）。

**P2 · 复现时漏掉"对 `m̃` 重算 FK 与速度"会导致位置/速度奖励互斥（机制派生）**
- 派生自 §6 失败模式："arm 编辑与 torso/legs 动力学耦合"，策略必须闭环补偿。
- 派生自方法约束：III-B 明确要求"recompute body poses by forward kinematics and **derive joint and body velocities from the edited motion**"，并用 edit support `B`（过渡 + 邻帧）做差分。
- 常见错误写法：位置目标用 `m̃`、速度目标仍用原始 `m` 的速度（因为"速度没编辑"）。这会让同一 body 的位置项和速度项指向不同方向，训练表现为抖动/收敛慢/跌倒率上升，且**不会报错**。
- 工程动作：把 `m̃` 的构造做成一个带自检的函数——(i) 用内容规则回检编辑后参考已不含该动作；(ii) 校验 `m̃` 的速度与位置差分自洽。

**P3 · 流式部署时"该改了却没改"或"提前改"（机制派生）**
- 派生自 §6 失败模式："只有已知 clip、未做完整流式 rollout"，讨论区明确点名 transition timing。
- 派生自方法约束：观察式 Eq.(1) 只有当前帧参考 + 上一动作，**无未来帧、无 clip id、无 edit mask**；而离线编辑器用整段 clip 来放置 `C`/`I` 的进入/退出过渡。
- 后果：编辑发生在哪一帧由 `m_t` 的局部形态隐式决定，可能与规则意图错位一个过渡窗口；对"必须在动作发生前完成重定向"的应用（例如受限区域禁入）是不可接受的。
- 工程动作：在外层加因果状态机（检测 → 预触发缓冲 → 强制窗口），或在训练时加入延迟/抖动增强；验收指标改为"整段流式 rollout 中 `D_C` 是否发生 + 替换相对窗口的时序误差"，而不是 core 区间的统计量。

**P4（附带）· 移除 edit-pool 采样 = 学不到任何替换**
- 派生自 §6 失败模式："稀疏编辑训练失败"。
- 派生自方法约束：`ρ = min(ρ_max, κ p_pool)`，`p_pool` 是编辑池占时间轴比例；消融显示无 targeted sampling 时 scratch 与 fine-tune **都保留原内容**。
- 工程动作：先统计 `p_pool`，再设 `κ` 让 `ρ` 显著大于 0；同时确保 failure-driven sampler 的反馈**只用 base-sampled episode**（III-D），否则难度估计被编辑窗污染，动作库其余部分覆盖下降。

---

[← Back to Humanoid Whole-Body Control README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（arXiv:2611.14049v1，已截断版）· 未在真机复现的数字标 `UNVERIFIED`；§4 中延迟/显存/FPS/硬件全部为「论文未报告」；§5 数据集名与指标数值逐字取自正文（`Retargeted AMASS for Robotics`、`LAFAN1`、Table II/III/IV），Table II 中 ForgetMimic‡ 的 S2 行抽取列粘连已在脚注标注。

[//]: # "<!-- source: https://arxiv.org/abs/2611.14049 -->"
