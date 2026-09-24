<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: learned
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# ContactMimic：通过接触控制实现人形机器人物体交互 (ContactMimic: Humanoid Object Interaction via Contact Control)

> **发布时间**：arXiv 2607.08742v1，2026 年 7 月 9 日（cs.RO）
> **论文 / 模型名**：ContactMimic
> **核心定位**：把"接触"从关键点跟踪的**副产品**升级为 policy 的**运行时可控输入**——同一个关键点轨迹下，用一个二进制接触标签就能命令机器人"接触 / 不接触"，从而无需任务专属 reward 即可完成擦白板、抬箱子等以接触定义成败的任务。
> **作者 / 机构**：Xinyao Li, Xialin He, Runpei Dong, Saurabh Gupta（University of Illinois Urbana-Champaign）

导语：现有全身 tracker（BeyondMimic 等）只跟踪关键点轨迹，能摆出正确姿态却"贴着物体擦不到"——挥手 vs 擦白板、蹲下 vs 坐下在几何上几乎等价，差别只在接触。ContactMimic 的关键结论是：**仅靠关键点跟踪不足以完成任务；接触必须被显式建模为可控信号，而且训练数据必须被"改造"以打破关键点与接触之间的相关性，否则 policy 会直接无视接触指令。**

---

## X-Ray 开场

**解决什么问题**：全身 loco-manipulation 任务（擦板、坐椅、推家具、抬箱）的成功由"哪个身体部位在什么时候碰到什么物体"决定，而不是由关键点轨迹决定。纯关键点 tracker 无法区分"擦"与"挥"、"坐"与"蹲"。

**提出了什么**：在关键点 tracking 之上，把逐帧、逐身体部位的**二进制接触标签** $\bar{\mathbf{c}}_t$ 作为 policy 输入；配套两组接触感知 reward（接触标签匹配 + 接触距离），并用三种数据增强（接触标签翻转 / 物体移除 / 几何膨胀）合成"关键点相似但接触标签不同"的运动对，强行让 policy 依赖接触指令。

**对 spatial AI 研究者意味着什么**：接触/交互是一种**一等的、可被外部旋钮控制的表示**，而不是物理仿真里"出现就出现"的涌现行为。这为"任务 = 几何 + 接触语义"的表征提供了可复用的接口范式，并把"数据工程（解耦相关性）"推到与网络/奖励设计同等重要的位置。

---

## 📍 研究全景时间线

```
2022  PHC (Perpetual Humanoid Control)
      │  物理式模仿，解决自由空间运动模仿
      │
2024  OmniRetarget / GMR
      │  HOI 数据重定向到人形，显式保持接触结构
      │  （本文用它做数据前端）
      │
2025  BeyondMimic  ← keypoint-only tracker 的 SOTA（本文主要 baseline）
      │  全身运动跟踪，接触是几何匹配的副产品
      │
2025  ResMimic
      │  残差 HOI tracker + contact-tracking reward
      │  └─ 但仍只条件于 motion/object 轨迹，无细粒度接触控制
      │
2026  ★ ContactMimic（本文）
      │  contact 作为 runtime 可控输入 + 数据增强解耦 keypoint↔contact
      └─ 局限：每 motion 单独训一个 policy（非 universal tracker）；
             数据域仅 HUMOTO；真机仅 5 motion / 单一机器人
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **重定向（OmniRetarget）** | 人类 HOI clip（HUMOTO） | 机器人参考构型轨迹 $\bar{\mathbf{q}}_{1:T}$（关节位置 + root pose） | 仅离线；推理不参与 |
| **接触标签提取** | 重定向后的参考轨迹 + 物体表面 | 二进制接触标签 $\bar c_{t,b,p}\in\{0,1\}$；body 条件向量 $\bar c_{t,b}=\max_p \bar c_{t,b,p}$ | 仅离线；距离 < **1 cm** 记为接触，就近分配语义部件 $p$ |
| **数据增强** | 一条重定向 clip | 若干"同关键点结构、异接触标签"的运动对 | 仅训练时；推理不使用 |
| **Policy** $\pi_\theta(\mathbf a_t\mid \mathbf p_t,\bar{\mathbf k}_t,\bar{\mathbf c}_t)$ | 本体感受 $\mathbf p_t$ + 参考关键点 $\bar{\mathbf k}_t$ + 接触标签 $\bar{\mathbf c}_t$ | 目标关节角 → PD → 力矩 | 训练：全标签；**推理：接触标签是可拨动的旋钮（✔/✘）** |
| **Reward（接触感知）** | 参考标签 vs 实际接触 | $r^{lm}_t,\ r^{cd}_t$ | 仅训练；推理不参与 |

接触能力身体集合 $\mathcal B$ = {pelvis, torso, hips, knees, ankles, shoulders, wrists}（7 类，注意**足部接触走 ankle**）。

### 1.2 关键机制

**⚡ Eureka Moment：接触不是"跟踪对了就会发生"的结果，而必须是一个被显式条件化、且被数据工程强制解耦出来的可控输入——否则 policy 会直接从关键点几何"猜到"接触，完全无视你的指令。**

这个洞见包含两个必须同时成立的支点：
1. **Reward 支点**：接触标签匹配 reward + 接触距离 reward，给出"往物体表面靠 / 离开表面"的连续梯度。
2. **数据支点**：原始 HOI 数据里"一种关键点 ≈ 一种接触模式"，policy 可以偷懒。必须构造"关键点相似但接触标签相反"的运动对，让接触指令**成为唯一可用的判别信号**。

消融（§4.5）证实：**只加输入 + reward、不加数据增强是不够的**——多数运动上接触可控性明显变差。

### 1.3 信息流 / 架构图

```
 HUMOTO 人类 HOI clip
        │
        ▼
 [OmniRetarget] ──► 参考机器人轨迹 q̄_1:T
        │                     │
        │                     ├──► 参考关键点 k̄_t ──────────┐
        │                     │                            │
        │                     ▼                            │
        │           [接触标签提取]  d<1cm → c̄_{t,b,p}      │
        │                     │                            │
        ▼                     ▼                            │
 [数据增强]         c̄_t (条件)                            │
  ❶标签翻转                                                │
  ❷物体移除                                                │
  ❸几何膨胀 ──► 运动对（near/far × ✔/✘）                  │
        │                                                  │
        └──────────────┬───────────────────────────────────┘
                       ▼
      π_θ(a_t | p_t, k̄_t, c̄_t) ──► 目标关节角 ──► PD ──► 力矩
                       ▲
                       │ 训练信号
      r_t = r^track + w_lm·r^lm + w_cd·r^cd + r^reg
                    └── 接触标签匹配 (bal. acc / TP−λFP)
                    └── 接触距离 (靠近 + / 远离 −)
  推理时： k̄_t 固定，仅拨动 c̄_t 的 ✔/✘ → 行为改变
```

---

## 2 · 数学核心

📌 **Napkin Formula**：

$$r_t=\underbrace{r^{\text{track}}_t}_{\text{关键点跟踪}}+\underbrace{w_{\text{lm}}r^{\text{lm}}_t+w_{\text{cd}}r^{\text{cd}}_t}_{\text{接触感知（本文）}}+\underbrace{r^{\text{reg}}_t}_{\text{正则}},\qquad r^{\text{lm}}_t=\tfrac12(\mathrm{TPR}+\mathrm{TNR})$$

一句话直觉：**总 reward = 别把姿态跳错 + 按指令碰到/避开物体**，其中"按指令接触"用一对平衡的分类指标（正类要碰、负类不许碰）来度量。

### 目标 → 公式 → 变量 → 直觉

**（a）接触标签匹配 $r^{\text{lm}}_t$**

定义 $\mathcal S_+=\{(b,p):\bar c_{t,b,p}=1\}$，$\mathcal S_-=\{(b,p):\bar c_{t,b,p}=0\}$，实际接触 $c_{t,b,p}\in\{0,1\}$：

$$\mathrm{TPR}=\frac{1}{|\mathcal S_+|}\sum_{(b,p)\in\mathcal S_+}c_{t,b,p},\quad \mathrm{TNR}=\frac{1}{|\mathcal S_-|}\sum_{(b,p)\in\mathcal S_-}(1-c_{t,b,p}),\quad \mathrm{FPR}=1-\mathrm{TNR}$$

- **默认（平衡准确率）**：$r^{\text{lm}}_t=\tfrac12(\mathrm{TPR}+\mathrm{TNR})$
- **稀疏接触（TP − FP）**：$r^{\text{lm}}_t=\mathrm{TPR}-\lambda\,\mathrm{FPR}$，当几乎所有 pair 都是 $c=0$、TNR 饱和时提供更强梯度。

> 直觉：单纯的"接触比例"会被极不平衡的负类淹没（物体部件 × 身体部位组合数远大于真实接触数），所以用**平衡**的 TPR/TNR，或对误碰（FP）显式惩罚。

**（b）接触距离 $r^{\text{cd}}_t=r^{\text{cd,+}}_t+r^{\text{cd,-}}_t$**

设 $d(b,p)$ 为身体 $b$ 的原点到物体部件 $p$ 表面的距离：

$$r^{\text{cd,+}}_t=\frac{1}{|\mathcal S_+|}\sum_{(b,p)\in\mathcal S_+}\exp\!\Big(\frac{-d(b,p)^2}{2\sigma^2}\Big),\qquad r^{\text{cd,-}}_t=-\frac{1}{|\mathcal S_-|}\sum_{(b,p)\in\mathcal S_-}\mathbf 1\!\big[d(b,p)<\delta\big]$$

- **变量**：$\sigma$ 控制"吸引"的作用范围；$\delta$ 是"误碰"判定阈值；$w_{\text{lm}},w_{\text{cd}}$（权重值论文正文未给，见 supp.）。
- **直觉**：$r^{\text{cd,+}}$ 是高斯吸引势，把"应该碰"的部位往表面拉；$r^{\text{cd,-}}$ 是阶跃惩罚，把"不该碰"的部位从表面推开。二者与 $r^{\text{lm}}$ 互补——前者给**连续梯度**（解决稀疏/不可微的二元接触信号），后者给**最终判定**。

---

## 3 · 带数字走一遍（玩具设定）

**场景：坐椅子（contact pair = torso ↔ chair backrest）。**

设接触能力集合 $\mathcal B$ 取 7 个部位，物体语义部件 1 个（backrest）。于是共 $|\mathcal S|=7$ 个 (b,p) 对，其中任务相关只有 1 对：$\mathcal S_+=\{\text{torso}\}$，$|\mathcal S_+|=1$；$\mathcal S_-=\{$其余 6 个$\}$，$|\mathcal S_-|=6$。

**情形 A：torso 贴住椅背，其余不碰。**
$\mathrm{TPR}=1/1=1$，$\mathrm{TNR}=6/6=1$ → $r^{\text{lm}}=\tfrac12(1+1)=1$。

**情形 B：完全没碰到椅背（但姿态到位）。**
$\mathrm{TPR}=0$，$\mathrm{TNR}=1$ → $r^{\text{lm}}=\tfrac12(0+1)=0.5$。

**情形 C：躯干和另外 5 个部位全都贴上。**
$\mathrm{TPR}=1$，$\mathrm{TNR}=1/6\approx0.167$ → $r^{\text{lm}}=\tfrac12(1+0.167)\approx0.583$。

> 观察：平衡准确率在 A 得满分、B/C 都明显掉分，但 B 与 C 差距不大。这正是论文用 **TP − λFP** 变体的动机——在稀疏接触场景下，对"误碰"给更陡的梯度：取 λ=1，B 得 $1-0=1-0$… 注意 B 的 $\mathrm{FPR}=1-\mathrm{TNR}=0$，所以 $r=\mathrm{TPR}-\mathrm{FPR}=0-0=0$；C 得 $\mathrm{TPR}-\mathrm{FPR}=1-0.833=0.167$。此时 B（该碰没碰）反被罚得比 C（碰太多）更重——稀疏接触任务里"漏碰"比"误碰"更致命。

**玩具补充：为什么需要数据增强。** 假设训练集只有一条 clip：关键点贴近椅背（near），标签 contact=1。policy 学到的实际映射可能是 $P(\text{contact}\mid \text{near})=1$，**与标签无关**。测试时把标签翻成 0，关键点仍然 near，policy 照样贴上去——接触不可控。增强方案强行构造两条样本：

| 样本 | 关键点 | 接触标签 | 迫使 policy 学到 |
|---|---|---|---|
| ❶ 标签翻转 | near | 0 | near 但不碰 |
| ❸ 几何膨胀 | far | 1 | far 也要碰（关键点被轻微错标） |

只有同时见过这两条，policy 才必须**读标签**而不是猜几何。（以上数字为玩具演示，非论文实验值。）

---

## 4 · 工程视角

| 项目 | 论文报告值 |
|---|---|
| 机器人硬件 | Unitree G1 humanoid，**29 DoF** |
| 仿真器 | Isaac Lab + **PhysX** 刚体仿真 |
| 每环境物体 | 一个交互物体，固定（fixed）或自由（free）取决于 motion |
| 控制接口 | policy 输出目标关节角 → **PD 控制器**转力矩 |
| 策略网络结构 / 参数量 | 论文未报告 |
| 控制频率 / 推理延迟 / FPS | 论文未报告 |
| 训练算力 / 训练时长 | 论文未报告 |
| 显存 / 内存 | 论文未报告 |
| reward 权重 $w_{\text{lm}},w_{\text{cd}}$、$\sigma,\delta,\lambda$ | 正文未给（指出见 supp.，正文未列出具体值） |
| 真机部署相机 / 通讯 / 状态估计 | 论文未报告 |
| 推理时是否需要接触传感器 | **不需要**（设计上刻意不用，理由见 §6） |

**部署侧的核心 trade-off（定性，论文明确论述，非我估算）**：
- **省掉接触传感**：policy 输入只用本体感受 + 参考关键点 + 接触标签，不依赖全身触觉硬件——代价是接触状态只能由 proprioception **推断**，论文用线性探针证明其可达性（§5 表 4），但这是**离线相关性证据**而非闭环误差保证。
- **每 motion 一个 policy**：换取每段运动的接触可控性，牺牲了 universal tracker 的泛化与复用（作者列为第一局限）。
- **推理自由度只在标签上**：关键点轨迹固定，运行时可"拨动"的只有二进制标签 → 接口极简、极轻量（发送的是若干 bit），但**无法在线修改几何目标**。

---

## 5 · 数据与评测

**数据组成**
- **Motion Dataset**：训练用 **10 motion clips**，来自 **HUMOTO [21]** 数据集，覆盖多种 human-object interaction 类别。
- 每个 clip 经 **OmniRetarget [39]** 重定向到 G1，得到参考轨迹 $\bar{\mathbf q}_{1:T}$；接触标签由重定向轨迹按 **1 cm** 距离阈值提取。
- 物体类型：whiteboard、chair、table、box（box 与 chair 在"Kick chair"/"Pick up box"中为 free object，其余固定）。

**实验用 10 个 motion（Table 1）**：wipe whiteboard；sit in front of table；lean on backrest I；lean on backrest II；step foot on chair；sit on table；lean against table；sit and squat；kick chair（free）；pick up box（free）。

**指标（逐字）**：`contact bodies`（与目标物体部件接触的身体数，含参考计数 Ref）、`contact impulse (N·s)`、`mean key-joint torque (N·m)`、`MPJPE (cm)`；自由物体运动额外报 `object displacement (m)`（越大越好）。

**关键评测设置**
- **接触可控性实验（sim）**：固定同一条关键点轨迹 $\tau$，比较 4 组：
  $\mathcal T^{\text{✔}}_{\text{near}}$、$\mathcal T^{\text{✘}}_{\text{near}}$、$\mathcal T^{\text{✔}}_{\text{far}}$、$\mathcal T^{\text{✘}}_{\text{far}}$（far = 用 §3.2 的几何膨胀把关键点推离物体表面）。可观测量为接触数 / 接触冲量，红箭头（near, ✔→✘）与蓝箭头（far, ✔→✘）应指向"接触下降"。
- **真机（§4.3）**：5 个 motion（wipe whiteboard / sit in front of table / lean on backrest I & II / sit and squat），同关键点、拨动接触命令 ✔/✘。
- **真机成功率（Table 2，逐字）**：

| Motion | ✔ | ✘ |
|---|---|---|
| Wipe whiteboard | 5/5 | 5/5 |
| Sit in front of table | 4/5 | 5/5 |
| Lean on backrest I | 9/10 | 10/10 |
| Lean on backrest II | 10/10 | 9/10 |
| Sit and squat | 5/5 | 5/5 |

  成功判定为**定性/人工判据**，例如 wipe whiteboard：`Hand contact leaves visible trace ⇔ contact=✔`。
- **vs BeyondMimic（Table 3）**：论文陈述结论为"BeyondMimic 的 contact metrics（接触数与接触冲量）远低于本文方法"，且两者 MPJPE 可比；物体操作任务上关键点-only 方法**无法移动物体**。可逐字引用的行例：**Pick up box** —— contact bodies BM `0.29 ± 0.59` vs Ours `1.85 ± 0.94`；object displacement BM `0.03 ± 0.01` vs Ours `0.49 ± 0.47`。（Table 3 其余行的列对齐在正文 HTML 中因下标渲染存在歧义，此处不逐格转写。）
- **数据增强消融（§4.5）**：在 $\mathcal T^{\text{✔}}_{\text{near}}$ 与 $\mathcal T^{\text{✘}}_{\text{near}}$ 上比较；除一个 motion 外，带增强版本接触可控性更好。
- **线性探针（Table 4，逐字 F1）**——从 policy 输入与 Layer-2 表示预测 runtime contact state：

| Motion | Chance(%) | Ref label | Obs | Layer 2 |
|---|---|---|---|---|
| Wipe whiteboard | 61 | 0.843 | 0.956 | **0.964** |
| Sit in front of table | 99 | 0.762 | **0.997** | **0.997** |
| Lean on backrest I | 70 | 0.906 | 0.943 | **0.964** |
| Lean on backrest II | 75 | 0.894 | 0.944 | **0.968** |
| Step foot on chair | 67 | 0.963 | 0.987 | **0.994** |
| Sit on table | 69 | 0.922 | **0.958** | **0.958** |
| Lean against table | 13 | 0.885 | **0.926** | 0.915 |
| Sit and squat | 62 | 0.906 | 0.970 | **0.974** |
| Kick chair | 2 | 0.000 | 0.267 | **0.476** |
| Pick up box | 81 | 0.846 | 0.930 | **0.931** |

  结论：Obs 与 Layer 2 的 F1 均远高于 chance 与参考标签本身——**policy 内部已编码实际接触状态**。（注：Kick chair 行 layer-2 仅 0.476，接触极稀疏时探针质量骤降。）

---

## 6 · 能力与失败模式

**能做到**
- **接触可控性**（sim + 真机）：同一关键点轨迹下，拨动接触标签即改变接触行为——擦白板留下痕迹 vs 悬停在板前；坐上椅背 vs 保持直立；坐（承重）vs 蹲（等高度动态平衡）。
- **不靠任务专属 reward 完成操作**：仅凭 keypoint + contact tracking，pick up box 时物体位移 **0.49 ± 0.47 m**（BM 仅 0.03 ± 0.01 m）。
- **接触指标优于 keypoint-only**，且 **MPJPE 不退化**（论文称 comparable）。
- **无需接触传感器**：proprioception 已足以推断 runtime 接触状态。

**不能做 / 明确局限（作者自述）**
- **每个 motion 单独训一个 policy**，不是 universal contact-conditioned tracker；跨 motion 联合训练为未来工作。
- 依赖 **HUMOTO** 高质量 HOI 数据，**交互多样性受限**；未支持 in-the-wild 视频。
- 真机只覆盖 **5 个 motion、单一机器人**；更广硬件验证为未来工作。

### 隐含假设 (Hidden Assumptions)

1. **重定向轨迹本身物理可信**：接触标签从重定向轨迹按 1 cm 提取，隐含假设 OmniRetarget 输出无穿透、无脚滑；若重定向有 artifact（论文自己提到 naive retargeting 会造成 foot-skating / penetration / hands floating），标签即被污染，reward 会追一个错误的接触定义。
2. **物体语义部件 $p$ 与几何已知**：接触标签定义在"物体语义部件"上（chair seat / board surface），隐含假设物体实例化已知、部件分割已知、位姿已知——**未见物体 / 可变形物体 / 未知部件划分无法直接套用**。
3. **二值接触即足够**：接触被压缩为 $\{0,1\}$（1 cm 阈值），冲量只在评测中出现，reward 里没有力的大小/方向建模；"擦得动"与"轻轻贴住"在标签上等价。
4. **接触能力身体集合固定为 7 类**：{pelvis, torso, hips, knees, ankles, shoulders, wrists}——足部接触走 ankle；手部精细操作（手指）不在集合内。
5. **推理时 motion identity 已知**：单 motion 单 policy，隐含测试时知道当前是哪段运动。
6. **增强的几何膨胀能代表部署扰动**：inflated geometry 在重定向阶段改变碰撞体，隐含假设这种"绕开"能迁移为真实世界的"关键点轻微错标"情形。
7. **proprioception 推断接触状态在闭环下仍然可靠**：探针是**离线**线性 probe，隐含假设高 F1 能转化为闭环鲁棒性，而非只在训练分布内成立。
8. **成功判定定性可复现**：真机成功率为人工定性判据（"留下可见痕迹"），隐含假设不同操作者判定一致。

---

## 7 · 与相关工作对比

| 方法 | 接触如何进入系统 | 接触是否 runtime 可控 | 是否需任务专属 reward | 关键差异 |
|---|---|---|---|---|
| **BeyondMimic [19]** | 不进入（纯关键点跟踪） | ✘（接触是几何副产品） | 是（否则操作任务失败） | Table 3 中 contact bodies/impulse 远低、物体不被移动 |
| **ResMimic [44]** | 加 contact-tracking reward（残差 HOI tracker） | ✘（只条件于 motion/object 轨迹） | — | 无细粒度控制（如"坐但不靠背"做不了） |
| **PHC [22]** | 物理式模仿解决自由空间运动 | ✘（无物体接触） | — | 面向自由空间，非 HOI |
| **OmniRetarget [39]** / GMR [2] | 重定向时保接触结构 | ✘（产出单条 canonical 轨迹） | — | 是本文的数据前端，不足以教 policy 解耦 |
| **经典接触规划 [25,30,34]** | 互补约束 / 轨迹优化 | ✘（contact schedule 规划时固定） | — | 开环，非闭环 policy 的输入旋钮 |
| **PhyCS 角色动画 [28,32,9]** | 以 scene contact 为条件合成 | ✘（计划时固定） | — | 非 runtime 可控 |
| **HOI 合成（运动学 [37,27,17,18] / 物理条件策略 [29,38,26]）** | 接触作为中间表示 / affordance | ✘（保物理合理，非用户旋钮） | — | 接触"隐式"而非"暴露给用户" |
| **★ ContactMimic** | **显式二进制接触标签作为 policy 输入 + 接触感知 reward + 解耦数据增强** | **✔（推理时可 ✔/✘ 拨动）** | **否**（keypoint+contact tracking 即可抬箱） | 首次把接触做成 runtime 可控旋钮 |

**🎤 面试 Tip**：被问"ContactMimic 相比 BeyondMimic 到底强在哪？"——**别只说"接触指标更高"**。要点三层：(1) **表面层**：MPJPE 相当，但 contact bodies / impulse 显著更高，说明关键点跟踪本身无法产生有效接触；(2) **接口层**：ContactMimic 多了"接触标签"这一可控输入通道，BeyondMimic 连这个旋钮都没有，所以只能在"要求接触"的场景下比较；(3) **方法层**：真正的贡献不是 reward 而是**数据增强解耦**——如果只加输入和 reward 而不打破 keypoint↔contact 相关性，policy 会忽略指令（§4.5 消融）。第三层是最容易被追问、也最能体现你读过消融的点。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-24)

**Repo 状态说明**：论文正文中**未出现任何 `github.com` 仓库链接**（仅给出项目页 `https://lixinyao11.github.io/contactmimic-page/`，非代码仓库）。因此**以下 pitfall 由 §6 失败模式 + §3 方法约束推导，未经任何 issue 流验证**，不代表社区已报告的真实缺陷。

**Pitfall 1 · 1 cm 阈值接触标签 → sim2real 边界抖动**
- 方法约束：接触标签由重定向轨迹"距离物体表面 < 1 cm"二值化（§3.2）。
- 失败模式：§6 隐含假设 1/3——部署时没有任何真值表面距离，1 cm 是仿真几何下的定义；一旦真机手腕到物体表面距离在 1 cm 附近波动，reward 语义与真机行为错位，表现为"看起来碰到了但离得很近"与"贴住了却判定未接触"交替。论文真机判据本身退化为定性（"留下可见痕迹"），恰恰是这一不确定性的旁证。
- 工程后果：不要在真机上复用 sim 的 1 cm 判定去自动打分，必须换人工/外部传感判据。

**Pitfall 2 · 每 motion 一个 policy → 无法迁移到新 motion，且没有 universal tracker 可用**
- 方法约束：作者明确"train a separate policy per motion"（§5 Limitations）。
- 失败模式：§6"不能做"——新物体/新交互类别没有现成权重；§6 隐含假设 5（推理时 motion identity 已知）意味着部署时必须先做 motion 分类/索引。
- 工程后果：想做成产品级"通用交互 tracker"的团队，这条路需要自己补跨 motion 联合训练；直接照搬只有 10 段 clip 的权重，覆盖率极低（作者自述 HUMOTO 多样性受限）。

**Pitfall 3 · 物体语义部件需预先定义 → 未见物体 / 可变形物体直接失效**
- 方法约束：接触标签定义在"物体语义部件 $p$"上（chair seat、board surface），由"最近部件"分配（§3.2）。
- 失败模式：§6 隐含假设 2——桌子/椅子/白板/箱子的部件划分与位姿是离线给定的；换成未见物体或可变形物体，$p$ 无定义，$r^{cd}$ 的距离场与 $r^{lm}$ 的 pair 集合都无从计算。
- 工程后果：接入新物体时至少需要一套部件分割 + 位姿估计 + 距离场管线；这不是 policy 端能补的。

**Pitfall 4 · 膨胀几何增强可能把策略带偏成"绕开物体"的先验**
- 方法约束：增强 ❸ 在重定向阶段**膨胀目标物体碰撞几何**，让机器人绕行、从而产生"关键点远离"的轨迹（§3.2）。
- 失败模式：§6 隐含假设 6——膨胀量一旦过大，合成轨迹与真实可行轨迹分布偏离；结合增强 ❶（near 关键点 + 接触标签 0），policy 学到的是"在物体附近抑制接触"的保守策略，可能损害需要稳健贴合的任务。
- 工程后果：膨胀幅度是需要调的敏感超参，而论文正文未给出具体数值；复现时要自己扫。

**Pitfall 5 · 线性探针高 F1 ≠ 闭环接触状态可靠**
- 方法约束：Table 4 的 F1 是**离线线性探针**，在训练分布上评估（§4.6）。
- 失败模式：§6 隐含假设 7——Kick chair 行 Layer-2 F1 仅 0.476，说明稀疏/瞬态接触下该表示几乎不可用；若把"proprioception 能推断接触"当作部署保证，会在线下/未见场景踩坑。
- 工程后果：任何"用 proprioception 替代接触传感器"的决策，都应在目标场景重做在线评估，而不是引用本表的离线 F1。

---

[← Back to Humanoid / Loco-Manipulation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（截断版）· 未在真机复现的数字标 `UNVERIFIED`；§4 中标注"论文未报告"的项为全文确实缺失，非估算。Table 3 除 `Pick up box` 行外未逐格转写，因正文 HTML 下标渲染导致列对齐歧义。

<!-- source: https://arxiv.org/abs/2607.08742 -->
