[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: hybrid
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# Mosaic：组合规则式与学习式运动规划器的可扩展框架 (Mosaic: An Extensible Framework for Composing Rule-Based and Learned Motion Planners)

> **发布时间**：2026-07（arXiv:2604.13853v2 [cs.RO]，v2 修订 2026-07-14；笔记日期 2026-10-18）
> **论文 / 模型名**：Mosaic（KIT 测量与控制研究所 + FZI；基于 Arbitration Graph, AG）
> **核心定位**：把"轨迹生成"和"轨迹验证+选择"在架构上拆开——用一张仲裁图把任意黑盒 planner 包成 behavior，共享 verifier 当安全下限、逐步 cost 仲裁当性能上限，**不重训、不加数据**就把 nuPlan Val14 闭环刷到 SOTA。

导语：规则式 planner 可解释但脆弱，学习式 planner 能适应但不可验证，已有的 hybrid 大多把规则当**硬编码后处理**，决策逻辑既不统一也不可复现。Mosaic 的答案是：不动 planner 本身，只把它们塞进一个带验证、带打分、带兜底层的结构化决策图里——并**分别量化**安全与性能两个来源。结果是 Val14 CLS-NR **95.56** / CLS-R **94.18**，interPlan CLS-R **54.10**（比最强单体检出 +22.8%）。

---

## X-Ray 开场

论文要解决的是"**异构 planner 怎么组合**"这个工程与安全命题：不是造一个更强的 planner，而是造一个**组合层**。核心机制只有三点：(1) 每个 planner（FlowDrive* 学习式、PDM-Closed 规则式）被包成 AG 里的 behavior，输出统一为"一条候选轨迹"；(2) 所有 planner 内部的私有安全检查被**关掉**，换成 Composer 里一个**共享 verifier**（2.0 s 内 at-fault 碰撞即拒绝，全速域生效，兜底刹车 8.0 m/s²）；(3) 通过验证的候选由统一的连续打分函数排序，最优者胜出，全败则落到 Emergency Stop。

对 spatial AI 研究者意味着什么：这是一份"**如何把不可验证的学习式模块安全地放进产品级决策栈**"的架构模板——安全下限来自**集中的、领域特定的验证器**，性能上限来自**逐步的、可解释的仲裁**，且两者贡献可以被 ablation 干净地拆开。VLA / 端到端 planner 迟早要面对同一道题。

---

## 📍 研究全景时间线

```
1990s          2000s–2010s            2023–2024                 2025                 2026（本文）
  │               │                      │                        │                    │
Brooks 包容式   AG 源于机器人足球       PDM-Open / PDM-Hybrid    diffusion & flow      Mosaic
架构 / Behavior  → 迁移到自动驾驶       PDM-Closed 拿下          planner 崛起          = AG + 共享 verifier
Tree（反应式     分层决策，加入          nuPlan 闭环 SOTA；       FlowDrive(*) 开源      + 逐步 cost 仲裁
行为的源头）     verification（[9]）    AG 仍未上大 benchmark     SOTA；GIGAFLOW(RL)    + 优先级兜底
                                                                  (闭源) CLS-R 93.8
```

- **本文的位置**：把 AG 这条"解释性决策"支线，第一次放到 nuPlan / interPlan 这种公认 benchmark 上，与 learned + hybrid 主流做同类对比；并把 AG 从"组合多个规则行为"扩展为"组合任意黑盒 planner"。
- **本文的局限**：只演示了 **2 个** planner + 1 个 fallback；verifier 自认"deliberately simple"（仅 at-fault 碰撞 + 恒速预测）；仿真 benchmark，无真车、无真实感知输入；per-step 延迟/内存未报告。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **FlowDrive\***（behavior 封装） | 当前世界状态（nuPlan 场景特征；论文未逐一列出输入张量） | 1 条候选轨迹 + 内部打分 | 预训练（rectified flow-matching + diffusion transformer），推理时用 moderated guidance 注入小扰动增加机动多样性；**本文不重训**；跑在 **GPU** |
| **PDM-Closed**（behavior 封装） | 状态 + 车道中心线图 + 其他 agent 的**恒速**预测 | 从 **15** 条 proposal 中选出的 1 条最优轨迹 | 无训练（IDM + 图搜索 + LQR/运动学自行车仿真）；跑在 **CPU** |
| **共享 Verifier**（位于 Composer 内） | 候选轨迹 + 恒速预测的 agent | 通过 / 拒绝 + 拒绝归因（哪个 component、什么原因） | 无学习参数；检查 **2.0 s** 内 at-fault 碰撞，**无速度门限**（原 planner 内置检查仅 &lt; 5 m/s 时触发） |
| **Composer**（cost arbitrator） | 全部**通过验证**的候选轨迹 | 最优轨迹 + 逐项分数 | 无学习参数；`S_total = (S_coll·S_driv·S_dir)·G_prog·S_perf` |
| **Emergency Stop**（fallback behavior） | 当前速度 | 直线减速轨迹，**8.0 m/s²**（原为 4.05 m/s²） | 无训练；**不需通过验证**（安全浮标） |
| **Mosaic**（priority arbitrator，根节点） | Composer 的输出 / 或"无有效输出" | 最终执行轨迹 | 无学习参数；优先级规则：Composer 有效轨迹 **>** Emergency Stop |

### 1.2 关键机制

**⚡ Eureka Moment：把"验证"和"选择"从各 planner 的内部逻辑里抽出来，变成架构层的一等公民——于是安全来自共享 verifier（下限），性能来自逐步仲裁（上限），两者互不冗余、可被独立测量。**

三个让这个洞见落地的细节：

1. **关掉各 planner 的内置安全检查**（两者原本都是"预测到 at-fault 碰撞且自车 &lt; 5 m/s → 4.05 m/s² 急刹"），换成**全速域**、刹车更强的共享版本——所以共享 verifier **严格强于**原来的内部检查（ablation 里原版各 25 次碰撞 → 单 planner + 共享 verifier 分别 17 / 15 次）。
2. **把 nuPlan 的二值 pass/fail 指标改造成 [0,1] 连续分**，乘性安全门 + 软进度门 + 加权性能分，让仲裁器在同为"合法"的候选间有细粒度区分能力。
3. **verifier 与 scorer 刻意非冗余**：verifier 是 2 s 视界上的**二值** at-fault 检查；scorer 的安全门是**全视界连续**惩罚，并额外覆盖可行驶区域与逆行——verifier 不管这些。

### 1.3 信息流

```
                    ┌─────────────── Composer (cost arbitrator + verification) ───────────────┐
 state ─┬─► FlowDrive*  ──► traj_A ──► [verify 2.0s at-fault?] ──pass──► score S_A ─┐        │
        │   (GPU)                                          └─fail─► 丢弃(+归因)      ├─► argmax ─┐
        └─► PDM-Closed  ──► traj_B ──► [verify 2.0s at-fault?] ──pass──► score S_B ─┘           │
            (CPU, 15 proposals)                       └─fail─► 丢弃(+归因)                    │
                                                                                              ▼
                                                             Mosaic (priority arbitrator, root)
                                                                                              │
        ┌──────────── 若 Composer 无有效轨迹（两者皆被拒，约 0.12% 步）────────────┐          │
        │                        Emergency Stop (8.0 m/s², 免验证)                 ├──────────► 执行
        └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2 · 数学核心

📌 **Napkin Formula**：`S_total = (S_coll · S_driv · S_dir) · G_prog · S_perf`，取通过验证的候选里 `argmax S_total`；全被拒 → 8.0 m/s² 直线刹停。
一句话直觉：**安全项是乘性的闸门（有一项为 0 就直接失去竞争力），进度是软闸门（鼓励别停着），性能是加权平均（TTC 权重最高）。**

### 目标

在"每个 step 都必须给出可执行轨迹"的硬约束下，最大化闭环驾驶分数，同时保证任何被执行的轨迹都通过统一安全判定，且**每个决策都可归因**（谁提的、为什么被拒、为什么被选中）。

### 公式

**(a) 验证（二值，先于打分）**
候选 $\tau$ 在 $[0, 2.0\,\mathrm{s}]$ 内与任一 agent 发生 **at-fault 碰撞** ⟹ 拒绝。agent 位置由**恒速预测**给出。

**(b) 打分（连续）**

$$S_{\text{total}}=\underbrace{S_{\text{coll}}\cdot S_{\text{driv}}\cdot S_{\text{dir}}}_{\text{safety gate}}\cdot G_{\text{prog}}\cdot S_{\text{perf}},\qquad C_{\text{total}}=-S_{\text{total}}$$

$$S_{\text{coll}}=\min_{t,k}\left(1-\frac{|B_{\text{ego}}(t)\cap B_k(t)|}{|B_{\text{ego}}(t)|}\right)\ \ (\text{静态障碍下界 }0.5)$$

$$G_{\text{prog}}=\min\left(d_{\text{route}}/\tau,\ 1\right),\quad \tau=0.2$$

$$S_{\text{perf}}=\frac{\sum_k w_k S_k}{\sum_k w_k},\quad k\in\{\text{prog},\text{ttc},\text{comf}\},\quad w_{\text{comf}}=2,\ w_{\text{prog}}=5,\ w_{\text{ttc}}=7$$

**(c) 仲裁**

$$\tau^\*=\arg\max_{\tau\in\mathcal{V}}S_{\text{total}}(\tau),\quad \mathcal{V}=\{\text{通过验证的候选}\};\qquad \mathcal{V}=\varnothing\Rightarrow \text{Emergency Stop}$$

### 变量说明

| 符号 | 含义 | 取值 / 备注 |
|---|---|---|
| $S_{\text{coll}}$ | 碰撞分，按 ego 框与碰撞框的**归一化重叠面积**取全时域、全对象最坏值 | 擦碰≈1，完全重叠→0；静态障碍地板 **0.5** |
| $S_{\text{driv}}$ | 仿真位姿落在**可行驶区域**内的比例 | [0,1] |
| $S_{\text{dir}}$ | 逆行判定，作用在"最长连续逆行距离"上 | 离散阈值 **1.0 / 0.5 / 0.0** |
| $d_{\text{route}}$ | 沿 route 中心线的位移，按当前速度下的**期望距离**归一化 | 无单位 |
| $\tau$ | 进度软门阈值 | **0.2**（即只完成期望进度 20% 以下开始扣） |
| $S_{\text{ttc}}$ | 恒速 ego rollout 下最早碰撞时间，截断到 **3 s** 视界后归一化 | 权重最高（7），因为它是打分时刻**唯一可用**的即时安全信号 |
| $S_{\text{comf}}$ | 加速度/加加速度限值检查 | 权重 2，主要当 tiebreaker |

### 直觉

- **乘性 vs 加性**：安全项用乘法 → 任一安全项为 0，性能再好也救不回来（"unsafe trajectory is never preferred regardless of its performance score"）；进度/性能用加性 → 平滑可微的排序信号。
- **两级安全，粒度不同**：verifier 是 2 s 二值硬闸（便宜、确定），scorer 的安全门是全视界连续软闸 + 覆盖可行驶区域/逆行（贵一点、更细）。作者明确说二者**非冗余**。
- **打分必须 online**：与 nuPlan 评测指标同源但**不能用 ground truth**，只能用历史观测与预测——这是"评测指标 → 在线代价函数"的移植，也是它可被复用为 runtime 决策依据的前提。

---

## 3 · 带数字走一遍（玩具设定）

> 以下场景与分项数值为**手算示范**（非论文数据），只用来展示公式如何产生决策。

**设定**：自车 12 m/s，限速 15 m/s，前方有慢车；仿真时域抽样 8 个位姿。两个候选已通过 verifier。

**候选 A = PDM-Closed 式的跟车 proposal**
- $S_{\text{coll}}=0.92$（有轻微擦碰风险，未达拒绝阈值）、$S_{\text{driv}}=1.0$、$S_{\text{dir}}=1.0$
- 进度只到期望的 12% → $d_{\text{route}}=0.12$ → $G_{\text{prog}}=\min(0.12/0.2,1)=0.6$
- 分项：$S_{\text{prog}}=0.15$、$S_{\text{ttc}}=0.90$、$S_{\text{comf}}=0.95$
- $S_{\text{perf}}=(5\cdot0.15+7\cdot0.90+2\cdot0.95)/14=(0.75+6.30+1.90)/14=0.6393$
- $S_{\text{total}}=0.92\times0.6\times0.6393=\mathbf{0.3529}$

**候选 B = FlowDrive\* 式的绕行 proposal**
- $S_{\text{coll}}=1.0$、$S_{\text{driv}}=1.0$、$S_{\text{dir}}=1.0$
- 进度 85% → $G_{\text{prog}}=\min(0.85/0.2,1)=1.0$
- 分项：$S_{\text{prog}}=0.85$、$S_{\text{ttc}}=0.55$、$S_{\text{comf}}=0.80$
- $S_{\text{perf}}=(5\cdot0.85+7\cdot0.55+2\cdot0.80)/14=(4.25+3.85+1.60)/14=0.6929$
- $S_{\text{total}}=1.0\times1.0\times0.6929=\mathbf{0.6929}$ → **B 胜出**

**候选 C（说明乘性门的威力）**：若某候选在 $t$ 时刻与横穿车辆框完全重叠 → $S_{\text{coll}}=0$ → $S_{\text{total}}=0$，无论 $S_{\text{perf}}$ 多高都排最后。若它在 **2.0 s** 内就发生 at-fault 碰撞，则连打分都进不去——直接被 verifier 丢弃。

**再把 8.0 m/s² 兜底量化（手算）**：12 m/s 全力刹停距离 $=v^2/(2a)=144/16=9.0$ m，用时 $1.5$ s；若沿用原来的 4.05 m/s²，则距离 $144/8.1=17.8$ m、用时 $2.96$ s——**超过 2.0 s 的验证视界本身**。这就是作者把兜底刹车从 4.05 提到 8.0 的物理理由：原值恰好等于 nuPlan 的舒适减速度阈值，"对最后一招来说过于保守"。

> 工程备注（笔者推断，论文未讨论）：8.0 m/s² ≈ **0.82 g**，已经贴近干沥青的轮胎附着极限，是规划层的名义减速度，真车可跟踪性需另做约束。

---

## 4 · 工程视角

| 项目 | 数值 | 说明 |
|---|---|---|
| 每 scenario 总计算耗时（Mosaic） | **2.0 s** | 在**全部 Val14** 上平均，同一硬件 |
| 同上，FlowDrive\* 单独 | **1.7 s** | |
| 同上，PDM-Closed 单独 | **1.4 s** | |
| 硬件型号 | **论文未报告** | 只说"same hardware" |
| per-step 延迟 / 控制频率 / FPS | **论文未报告** | 2.0 s 是整段 scenario 的计算量，**不能**直接换算成每步时延 |
| 显存 / 内存 / 功耗 | **论文未报告** | |
| 并行实现的延迟 | **未测量** | 论文明确："could be executed in parallel, though we have not measured a parallel implementation" |
| 相对 FlowDrive\* 的增量 | **+0.3 s/scenario**（UNVERIFIED：本文未给此差值，为笔者用报告值相减） | 作者解释增量有界的原因：FlowDrive\* 占 **GPU**，PDM-Closed 与全部仲裁逻辑占 **CPU**，两者资源独立 |

**架构层的 trade-off 读法：**

1. **异构算力天然并行**：GPU（学习式）+ CPU（规则式 + 仲裁）不抢资源，所以"多加一个 planner"的成本主要是 wall-clock 串行叠加，而非算力叠加。这也是"可扩展到 N 个 planner"的成本论据（虽然本文只做了 2 个）。
2. **共享 verifier 几乎免费**：验证与急刹逻辑原本就存在于每个 planner 内部，本文只是**合并**成一个模块，真正新增的计算只有"轻量的轨迹打分"。
3. **改造成本在"关开关"**：要把 planner 接入，必须找到并 disable 其内置安全检查（否则双重触发、统计口径与论文表 V 不等）。这是本文没写成 API 的隐藏工序。
4. **verifier 便宜是设计选择**：只做 2.0 s at-fault 碰撞 + 恒速预测，因此可以每步对**每个**候选跑一遍；作者明说"strengthening it toward a production safety module fits the same interface without touching the arbitration logic"——即接口留好了，实现可以换重。

---

## 5 · 数据与评测

**数据集 / benchmark（逐字来自全文）**

| Benchmark | 规模 | 指标 | 说明 |
|---|---|---|---|
| **nuPlan** closed-loop, **Val14** split | **1118** scenarios，**14** 个 scenario types | **CLS-NR**（non-reactive）、**CLS-R**（reactive） | CLS-NR：周围 agent 回放记录轨迹；CLS-R：周围 agent 通过 **IDM** 策略对 ego 做出反应。两者均在 **[0,100]**，由 at-fault collision、drivable-area、driving-direction、ego progress、TTC、speed-limit、comfort 子项合成；**安全相关子项是乘性门**，违反则该 scenario 直接 0 分；总分是全部 scenario 的均值 |
| **interPlan** | **80** scenarios，**8** 个 scenario types | **CLS-R** | nuPlan 的公开扩展，聚焦**高度交互与 out-of-distribution** 场景 |

**Baseline 与结果（Table II 原值照抄）**

| 类型 | Planner | Val14 CLS-NR↑ | Val14 CLS-R↑ | interPlan CLS-R↑ |
|---|---|---|---|---|
| Expert | Log-replay | 93.53 | 80.32 | 14.76 |
| Learning-based | PDM-Open | 53.53 | 54.24 | 25.02 |
| | Diffusion Planner | 89.87 | 82.38 | 24.71 |
| | FlowDrive | 91.21 | 85.37 | 36.96 |
| | GIGAFLOW †（闭源） | — | 93.8 | — |
| Rule-based & Hybrid | IDM | 75.60 | 77.33 | 31.20 |
| | PDM-Closed | 92.84 | 92.12 | 41.23 |
| | PDM-Hybrid | 92.77 | 92.11 | 41.61 |
| | Diffusion Planner w/ refine. | 94.26 | 92.90 | — |
| | FlowDrive\* | 94.81 | 92.96 | 44.05 |
| | **Mosaic (ours)** | **95.56** | **94.18** | **54.10** |

**评测条件（只说论文给出的）**

- **不重训任何 planner、不使用额外数据**：FlowDrive\* 与 PDM-Closed 都是原样预训练权重，Mosaic 只增加推理期的验证/打分/兜底。
- 消融统一在 **CLS-R** 上做；除两行"original"基线保留各 planner 内置检查外，**所有 Mosaic 配置都关闭了内置检查**（单 planner 行与 full 行用共享 verifier，"w/o verif." 行两者皆无）。
- Ablation（Table V，Table V 原值）：`PDM-Closed (original)` CLS-R **92.18**、Coll. **25**、Zero **35**、EB **0.16%**；`FlowDrive* (original)` **92.96 / 25 / 32 / 0.29%**；`Mosaic w/o verif.` **92.82 / 40 / 38 / —**；`PDM-Closed only` **92.37 / 17 / 28 / 0.14%**；`FlowDrive* only` **93.37 / 15 / 23 / 0.31%**；`Mosaic (full)` **94.18 / 16 / 17 / 0.12%**。
- 验证触发率（per-step，共 **166 806** 步）：PDM-Closed 失败 **0.45%**、FlowDrive\* 失败 **0.37%**、至少一个失败 **0.70%**、**两者同时失败 0.12%（197 步）**。
- 仲裁选择占比：PDM-Closed 胜出 **28.8%**、FlowDrive\* 胜出 **18.6%**、**52.6%** 平局（按设计选学习式）。
- 参数敏感性：以默认权重为中心把 $w_{\text{ttc}}$、$w_{\text{prog}}$ 各自减半/加倍，CLS-R 落在 **93.85–94.18**，最大波动 **0.33**，默认权重最高。
- interPlan 分型极值：`avoid crashed cars` 两个单体都是 **0.00**，Mosaic **29.80**。

---

## 6 · 能力与失败模式

### 能做（有具体数字支撑）

1. **安全下限**：共享 verifier 把 at-fault 碰撞从每个单体的 **25** 降到 **16**；去掉 verifier（保留两 planner）回弹到 **40**，论文称此即 **60.0%** 的碰撞削减归因于验证。
2. **性能上限**：CLS-R **94.18** 高于两个单 planner 消融（**92.37** / **93.37**）；zero-score scenario 从 23 / 28 降到 **17**（对任一单体至少 **26.1%** 的削减）；14 类场景中 **8** 类严格更优、**2** 类持平（`Stopping w/ lead` 98.96、`Behind long vehicle` 100.00）。
3. **OOD 泛化（无需重训）**：interPlan CLS-R **54.10**，比 FlowDrive\* 高 **22.8%**、比 PDM-Closed 高 **26.8%**；最尖锐的 `avoid crashed cars`（两体皆 0.00）达 **29.80**。
4. **可归因**：每次拒绝可定位到具体 component 与原因；每个 step 可说明是"因 cost 选中"还是"因 validity 选中"。

### 不能做 / 会退化

1. **会输给单体，且原因明确**：14 类里 **4** 类低于更强的那个单体，最多低 **2.4** CLS-R 分——`Follow. w/ lead` 92.74（FlowDrive\* 95.10）、`Changing lane` 92.79（PDM-Cl 94.33）、`Start. right turn` 93.58（FlowDrive\* 94.49）、`High mag. speed` 96.27（FlowDrive\* 96.60）。机制：这些类型里某个 planner 持续更强，仲裁器偶发的"逐步切到更弱提案"把均值拉下来了。interPlan 上同理（`Nudge parked veh.` 81.51 vs FlowDrive\* 82.40、`Low traffic density` 65.08 vs 68.02）。
2. **验证只看"2 s 内 at-fault 碰撞 + 恒速预测"**，因此对下列情形**没有**安全保证：agent 在 2 s 后偏离恒速预测（急刹/突然变道）、被遮挡后出现的 agent、非碰撞类违规（可行驶区域与逆行**只进打分不进验证**）、舒适性崩溃、以及**需要转向才能规避**的情形（兜底是直线减速）。
3. **兜底是"能停下"而非"能躲开"**：Emergency Stop 为直线 8.0 m/s² 减速且免验证；其可行性依赖前向净空。
4. **残留碰撞不可由仲裁逻辑消除**：16 次里 **10** 次是 benchmark 伪影（**5** 次初始化即处于不可避免碰撞、**5** 次 ghost/不稳定检测被 nuPlan 当真值回放）、**4** 次是恒速预测 + 感知噪声的共同极限、**2** 次是 nuPlan 的 at-fault 归因伪影（他车致碰但几何启发式仍判 ego）。
5. **可扩展性只到 2 个 planner**：结论明写"Demonstrating extensibility beyond two planners is left to future work"；多 planner 下的打分可比性、$O(n)$ 验证开销、优先级层级设计均未验证。
6. **verifier 是"为 benchmark 服务的简化版"**，作者自认；不能当作产品级安全模块。

### 隐含假设 (Hidden Assumptions)

| # | 假设 | 一旦不成立的后果 |
|---|---|---|
| A1 | 所有 planner 都能被包成**同一 observation 接口 + 同一轨迹表示（同一时域/同一时间栅格）** | 共享 verifier 与 scorer 里的 $\min_t$ 无法跨候选比较，打分失去意义 |
| A2 | **at-fault 归因**在在线时刻可判定 | 真实车端并无 nuPlan 的归因真值；verifier 需要自建责任判定，否则"at-fault collision"退化为"any collision"（更保守，EB 率上升） |
| A3 | **恒速预测**在 2 s 视界内是 agent 行为的可接受代理 | 对急刹/横穿/让行场景系统性低估风险（残留 4 次碰撞的直接原因） |
| A4 | 验证作用在**仿真出的 ego 位姿**上，而非跟踪误差下的真实位姿 | 控制层跟踪偏差会吃掉验证余量；论文未建模 |
| A5 | **关掉各 planner 内置安全检查是安全的**，因为共享 verifier 更严格（全速域 + 8.0 m/s² > 4.05 m/s²） | 若共享 verifier 的预测模型弱于某 planner 私有模型，关掉反而变危险 |
| A6 | 用一个**手工设计的 $S_{\text{total}}$** 就能公平比较异质 planner | 学习式 planner 的置信度/多模态信息被完全丢弃，只剩 3 个标量分项；对"多样性"的偏好无法表达 |
| A7 | **平局时选学习式**是合理的先验 | 52.6% 的步是平局，该规则实质决定了半个策略的行为；换成选规则式结果会显著不同（论文未做此 ablation） |
| A8 | 场景级均分是聚合 per-step 决策的正确口径 | 单步的"赢"不一定转化为场景分（4 类场景的负增益即证据） |
| A9 | $\tau=0.2$、静态障碍 0.5 地板、$S_{\text{dir}}$ 的 1.0/0.5/0.0 阈值在不同路网/不同速度分布下仍适用 | 这些是 nuPlan 定标值，换域需重标定（论文的敏感性分析只覆盖 $w_{\text{ttc}}$/$w_{\text{prog}}$） |

---

## 7 · 与相关工作对比

| 方案 | 组合方式 | 安全机制放在哪 | 可解释性 | Val14 CLS-R↑ |
|---|---|---|---|---|
| PDM-Hybrid（PDM-Closed + PDM-Open） | 规则框架内嵌学习提议 | 规则 planner 内部 | 中（决策逻辑为该用例定制） | 92.11 |
| Diffusion Planner w/ refine. | 学习式 + 规则后处理 refine | 后处理 | 低–中（ad hoc） | 92.90 |
| FlowDrive\*（single hybrid） | 学习式 + moderated guidance 后处理 | planner 内部私有检查 | 低 | 92.96 |
| GIGAFLOW †（闭源，RL self-play） | 纯学习 | 学习策略内隐 | 低 | 93.8 |
| Behavior Trees / 包容式架构 | 层级化反应式组合 | 各叶节点 | 中（但缺少显式 verification 契约） | 本文未报告同类数字 |
| **Mosaic** | **AG：behavior 化 + 集中验证 + 逐步 cost 仲裁 + 优先级兜底** | **共享 verifier（架构层，与 planner 解耦）** | **高（每次拒绝/选择都可归因）** | **94.18** |

差异的一句话：已有 hybrid 的"决策逻辑往往是 ad hoc、非模块化、难复现"（原文判断），Mosaic 的差异不在于用了什么新 planner，而在于把**信任分配变成运行时可审计的逐步判断**，而不是写死在某个 bespoke pipeline 里。

**面试 Tip**：被问到"这东西和 PDM-Hybrid / 加个规则后处理有什么区别"时，别背分数，讲**两个独立机制**——"verifier 是安全下限（25→16），仲裁是性能上限（92.37/93.37→94.18），而且我可以说清哪一半来自哪里"；再补一句诚实的边界："它只证明了 2 个 planner 的组合，且 verifier 是简化版，可扩展性还在 future work"。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-18)

**Repo 信号核验**：全文只在 Abstract 中以**纯文本**出现 `github.com/KIT-MRT/mosaic`，未构成 arXiv PDF 内可点击 hyperlink。按 atlas 判定口径，**视为无 repo 信号**：本节不引用任何 issue 编号、commit hash 或 issue 标题，以下 3 条 pitfall 全部由 **§6 失败模式 + §1/§3 的方法约束**机械推导，**未经 issue 验证**。

---

**P1 · 忘记 disable planner 内置安全检查 → 你的碰撞/EB 统计一定对不上表 V**
- 推导链：§1.2 明确"两者原本都是'at-fault 碰撞 + 自车 &lt; 5 m/s → 4.05 m/s² 急刹'"（§III-B）→ 本文所有 Mosaic 配置都要把这段私有逻辑**关掉**，改用 §III-D 的全速域 + 8.0 m/s² 共享版本。
- 复现症状：共享 verifier 判定"应刹"，但 planner 内部的 4.05 m/s² 弱刹车先生效/覆盖输出 → 有效减速度被拉回 4.05，EB 频率与碰撞数与论文偏离（对照值：EB **0.16% / 0.29% / 0.12%**，Coll. **25 / 25 / 16**）。
- 落地做法：把"内置检查是否启用"做成显式配置开关并在日志里记录，跑完先核对 §IV-E-5 的 **0.45% / 0.37% / 0.70% / 0.12%（197/166 806）** 四个拒绝率，作为接入是否正确的冒烟测试。

**P2 · 打分函数的阈值/分母是 nuPlan 定标的 → 换域后排序会整体漂移**
- 推导链：§2 里 $\tau=0.2$、静态障碍 **0.5** 地板、$S_{\text{dir}}$ 的 **1.0/0.5/0.0** 阈值、$d_{\text{route}}$ 按"当前速度下的期望距离"归一化、$S_{\text{coll}}$ 以 **ego 框面积**为分母——这些都依赖 nuPlan 的地图/route 中心线/框定义；而 §6 假设 A9 指出敏感性分析**只覆盖两个权重**。
- 复现症状：换到自定义路网或不同车速分布后，$G_{\text{prog}}$ 在正常行驶时就长期饱和或长期不饱和，仲裁器退化为"只按 $S_{\text{perf}}$ 排序"，§6 里那 4 类负增益场景的边界被放大。
- 落地做法：把 $\tau$、静态障碍地板、$S_{\text{dir}}$ 阈值、碰撞面积分母全部提为外部配置；换域先只跑 CLS-R 的子项分布直方图（而非总分）做定标。

**P3 · 平局裁决规则与浮点比较方向，会决定半个策略**
- 推导链：§IV-E-4 给出 PDM-Closed 胜 **28.8%**、FlowDrive\* 胜 **18.6%**、**52.6%** 平局且"learned planner is chosen by design"（§IV-E-4 / §III-C）→ 也就是说超过一半的步，执行的是什么由**平局规则**而非分数决定。
- 复现症状：用 `np.argmax` / `>` 还是 `>=` 遍历候选，平局时会落到不同 planner；一旦你的实现把平局判给规则式，结果不能与 **94.18** 对齐，且差异集中在 §6 里"某 planner 持续更强"的 4 类场景上（`Follow. w/ lead`、`Changing lane`、`Start. right turn`、`High mag. speed`）。
- 落地做法：把 tie-break 写成显式、可配置、可日志化的规则（并记录每步是"cost 胜"还是"tie 胜"），先复现 **28.8% / 18.6% / 52.6%** 这三个占比，再谈总分。

**P4（附带，口径类）**：论文中 PDM-Closed / FlowDrive\* 的 CLS-R 存在三处不同数值——Table II 的 **92.12 / 92.96**、Table III 的 overall **92.37 / 93.37**、Table V 的 original **92.18 / 92.96** 与 single-planner **92.37 / 93.37**。合理读法是 **Table III 用的是"单 planner + 共享 verifier"消融，而非原版**（因为 92.37 / 93.37 与 Table V 的 `PDM-Closed only` / `FlowDrive* only` 完全一致），但**论文未明写**。复现时若混用三张表做对比，会得出错误的"组合增益"。

---

[← Back to Navigation README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（§4 中标 `UNVERIFIED` 者为笔者对报告值的算术推导；§3 全部为玩具设定手算；per-step 延迟、显存、硬件型号论文均未报告）

[//]: # "<!-- source: https://arxiv.org/abs/2604.13853 -->"
