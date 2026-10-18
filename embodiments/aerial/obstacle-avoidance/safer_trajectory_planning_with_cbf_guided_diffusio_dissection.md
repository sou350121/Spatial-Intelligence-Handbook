[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: generative
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->"

# 基于控制屏障函数引导扩散模型的无人机安全轨迹规划 (Safer Trajectory Planning with CBF-guided Diffusion Model for Unmanned Aerial Vehicles)

> **发布时间**：2026-04-19（arXiv 2604.17527**v1** [cs.RO]）。本笔记**仅覆盖 v1**，标准入口为 https://arxiv.org/html/2604.17527v1 ；官方元数据指向 v3，但 2026-10-18 抓取时 v3 的 HTML/PDF 不可取得（HTTP 404），**v3 不能代表本笔记内容，本笔记也不推断 v3 的任何改动**。
> **论文 / 模型名**：**AeroTrajGen**（HK PolyU, Dept. of Aeronautical and Aviation Engineering；通讯作者 Weisong Wen）
> **核心定位**：把 CBF 导出的安全评分梯度注入扩散模型逆向去噪的**噪声预测**里，让生成式特技轨迹在**推理时**被推离障碍——不重训、不依赖"安全验证过的训练数据"、不做后处理滤波。
> **Ontology**：problem=`navigation` · representation=`n/a` · sensor=`n/a` · paradigm=`generative` · time=`per-scene`

导语：扩散模型能生成多样、平滑的无人机特技轨迹，但输出分布里混着撞障碍的样本，撞不撞很大程度取决于采样。已有做法要么靠"安全数据集重训"，要么靠事后滤波或额外分类器引导，都不触及生成过程本身。AeroTrajGen 的答案是：在反向扩散的每一步，用 CBF 构造的安全评分函数的**对数梯度**去修正 score，把"安全"变成去噪轨迹上的一个持续力场。论文自己报告了代价：位置 RMSE 从 0.47 m 升到 1.19 m、风格准确率从 94.0% 降到 68.0%——安全性的提升伴随保真度下降。

---

## X-Ray 开场

**问题**：生成式轨迹规划器的输出分布里混着撞障碍的样本，而"安全"是长尾约束，纯数据驱动难以覆盖；同时飞行器在线算力有限，跑不了重规划。
**提出**：一个 obstacle-aware diffusion transformer（条件 = 历史轨迹 + 目标点 + 14 类特技 one-hot + 障碍注意力编码），配一个**推理期 CBF 引导采样器**：把安全评分 $p_s(\mathcal{C}\mid \mathbf{x}_t)$ 的对数梯度加到 score 上，等价于在噪声空间里给 $\epsilon_\theta$ 加一个"远离障碍"的修正项。
**对 spatial AI 研究者意味着什么**：这是"**生成先验 + 控制论约束**"融合路线的一个清晰样本——安全约束不再在输出端做硬投影（CBF-QP 滤波器），而是被软化成生成过程内部的一个梯度场。它换来了"不改训练数据也能提安全性"，同时**没有提供**硬约束 CBF-QP 那一侧的形式化前向不变性保证（本文的构造是软引导）。这个 trade-off 值得每一个做 safety-critical generative planning 的人记住。

---

## 📍 研究全景时间线

```
采样/搜索规划            控制论安全              生成式轨迹              本文位置
──────────────────────────────────────────────────────────────────────────────
RRT* / A*  ──┐
(高维退化、    │
需后平滑)[8]  │
              ▼
         MPC + CBF ──────────┐
         (凸MPC-CBF[11],      │
          GPBF[12],           │
          固定翼CBF[13],      │
          因子图CBF[14],      │
          时变CBF着陆[15])    │
                              ▼
                        DDPM/Diffusion
                        (2020, 分数匹配)
                              │
                              ▼
                    ┌── 扩散用于轨迹生成
                    │   Diffuser/planning-as-
                    │   inference[7]
                    │   移动操作[5]
                    │   无人机特技生成[6] ◄── 本文的直接 baseline
                    │
                    ├── 安全化外挂手段
                    │   classifier guidance[10]
                    │   projection curriculum[9]
                    │   (都要额外模型 / 启发式 / 重训)
                    ▼
              ★ AeroTrajGen (2026, v1)
              CBF 梯度注入反向扩散
              = 推理期安全引导，无需安全验证数据
                    │
                    ▼
              [本文局限] 静态球障碍 / 纯自定义
              Python 仿真 / 软引导无形式保证 /
              无真机 / 序列长度与状态维度存在待核对
              的表述差异
                    │
                    ▼
              (未做) 动态障碍 / 非凸几何 /
              部分可观测 / 实机部署
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练期 vs 推理期差异 |
|---|---|---|---|
| **条件嵌入**（多模态融合） | 扩散步 $t$；目标点 $\mathbf{p}_t\in\mathbb{R}^3$；特技 one-hot $\mathbf{a}\in\mathbb{R}^{14}$；历史轨迹；障碍集 | 条件向量 $\mathbf{e}_{\text{cond}}$ | 训练与推理相同；障碍由 attention-based **obstacle encoder** 编码，该 encoder 是消融的核心对象 |
| **Transformer 主干**（Obstacle-Aware Diffusion Transformer） | 加噪轨迹 $\mathbf{x}_t$ + 位置编码 + $\mathbf{e}_{\text{cond}}$ | 预测 $\epsilon_\theta(\mathbf{x}_t,t)$（或 $\mathbf{x}_0^{\text{pred}}$） | 4 层 / 128 维 / 4 头 / dropout 0.1；**causal mask** 保证时序因果 |
| **多分量损失** | $\mathbf{x}_0^{\text{pred}}$ vs GT | 标量 | 仅训练期：$\lambda_{pos}$=1.0（末步 ×5）、$\lambda_{vel}$=1.0（**当前配置禁用**）、$\lambda_{obs}$=1.0、$\lambda_{cont}$=5.0、$\lambda_{acc}$=1.0、$\mathcal{L}_{att}$ 无权重 |
| **安全评分函数** | 单步 DCBF 值 $h^v(\mathbf{x}_k,\mathbf{c})$ | $P_s\in(0,1)$ 及其对数梯度 | 三候选：$P_1$（指数/平方差，**不光滑**、$P(R_s)=1.0$、最快）、$P_{\text{CDF}}$（光滑、$P(R_s)=0.5$、最慢）、$P_{\text{Logistic}}$（光滑、$P(R_s)\approx0.5$、快）——论文实测选 Logistic |
| **CBF 引导采样器**（Algorithm 1） | $\mathbf{x}_t$、条件、障碍、$\gamma_0$ | $\mathbf{x}_{t-1}$ | **仅推理期**；引导强度 $\gamma_t$ 随步数变化；训练时完全不存在 |
| **仿真评估环境** | 3–5 个随机球障碍 | 碰撞率 / AE / 最小距离 / 成功率 | 仅评估，自定义 Python 环境（⚠️ 非真机、非标准 benchmark） |

### 1.2 关键机制

**⚡ Eureka Moment**：**安全不是输出的过滤器，而是 score function 的一个加项。**
把"生成约束下的分布"写成 $p_t(\mathbf{x}_t\mid\mathcal{C}) \propto p_t(\mathbf{x}_t)\,p_s(\mathcal{C}\mid\mathbf{x}_t)$，两边取对数求梯度，就得到 $\nabla\log p_t(\mathbf{x}_t\mid\mathcal{C}) = \nabla\log p_t(\mathbf{x}_t) + \nabla\log p_s(\mathcal{C}\mid\mathbf{x}_t)$。于是"往哪走更安全"这件事，可以直接从**噪声预测**里减掉——生成与约束在同一个梯度场里合并，不需要两套模块在后处理阶段拼接。

第二个机制性观察（论文未强调，但复现时绕不开）：**CBF 里的 $\gamma$ 在文中承担了两个角色**。原版 DCBF 的 $\gamma\in(0,1]$ 控制"逼近安全边界的最大衰减速率"（式 12/13、式 27）；而引导强度 $\gamma(t)$（式 36/38）是一个可调超参，$\gamma_{\max}$ 取 2000 或 4000。两者量纲、语义不同，却共用同一个符号。这是复现时需要核对的命名冲突，不能直接当作同一个量使用。

### 1.3 信息流 ASCII 图

```
【训练期】
  2000 条专家轨迹(14 类特技) + 平滑拼接增强(+50%, 混合窗 5 帧)= 3000 条
        │
        ▼
  加噪 x_t = sqrt(ᾱ_t)·x_0 + sqrt(1-ᾱ_t)·ε        (DDPM 前向, 100 步)
        │
        ├── 条件: t, 目标点 p_t, 特技 a(14), 历史 20 步, 障碍(attention encoder)
        ▼
  TransformerDecoder(x_t + e_cond, causal mask)  →  ε_θ
        │
        ▼
  L = λpos·Lpos + λvel·Lvel(禁用) + λobs·Lobs + λcont·Lcont + λacc·Lacc + Latt
   (λcont=5.0 最重 ← 惩罚"历史末帧 ↔ 预测首帧"的跳变)

【推理期】  ← 本文的贡献全在这里
  x_T ~ N(0,I)
        │
        ▼   for t = T … 1:
  ┌─────────────────────────────────────────────────────┐
  │ 1. x_0^pred ← model(x_t, t, target, action, hist, obs)│
  │ 2. ε_pred  ← (x_t - sqrt(ᾱ_t)·x_0^pred)/sqrt(1-ᾱ_t) │
  │ 3. γ_t     ← γ_max·(1 - t/t_start)^α · 1{t≤t_start}  │
  │ 4. V, ∇V   ← barrier_and_grad(x_0^pred, obs)         │
  │ 5. ε_guided← ε_pred + γ_t·∇V·sqrt(1-ᾱ_t)   ★ 核心   │
  │ 6. μ       ← (1/√α_t)(x_t - coeff·ε_guided)          │
  │ 7. x_{t-1} ← μ + σ_sample·N(0,I)                     │
  └─────────────────────────────────────────────────────┘
        │
        ▼
   60 步轨迹 (6 s @ 10 Hz) —— 论文报告 Config C 碰撞率 0.0%（200 条测试）
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$\boxed{\;\epsilon_{\text{guided}} \;=\; \epsilon_{\theta}(\mathbf{x}_t,t)\;-\;\sqrt{1-\bar\alpha_t}\,\nabla_{\mathbf{x}}\log p_s(\mathcal{C}\mid\mathbf{x}_t)\;}$$

**一句话直觉**：去噪时网络说"往这个方向减噪"；CBF 说"再补一个方向，让轨迹离障碍更远"。两者在**噪声空间**相加，于是安全约束作用在生成过程内部，而不是贴在输出上的后处理。

### 2.1 目标 → 公式 → 变量 → 直觉

| 环节 | 公式 | 变量 | 直觉 |
|---|---|---|---|
| 前向扩散 (SDE) | $\mathrm{d}\mathbf{x}_t=f\mathrm{d}t+g\,\mathrm{d}w_t$，$f=-\beta(t)\mathbf{x}_t$，$g=\sqrt{2\beta(t)}$ | $\beta(t)$ 噪声调度 | 数据被逐步"糊化"成高斯 |
| 逆向 SDE | $\mathrm{d}\mathbf{x}_t=[-\beta\mathbf{x}_t-2\beta\nabla\log p_t]\mathrm{d}t+\sqrt{2\beta}\,\mathrm{d}\tilde w_t$ | score $\nabla\log p_t$ | 只要知道 score，就能倒着走回去 |
| Score ↔ 噪声 | $\epsilon_\theta=-\sqrt{1-\bar\alpha_t}\,\nabla_{\mathbf{x}_t}\log q(\mathbf{x}_t)$ | $\bar\alpha_t=\prod\alpha_s$ | 网络预测的噪声是负 score 的缩放版 |
| **条件化 score** | $\nabla\log p_t(\mathbf{x}_t\mid\mathcal{C})=\nabla\log p_t+\nabla\log p_s(\mathcal{C}\mid\mathbf{x}_t)$ | $\mathcal{C}$=安全集 | 加一个"安全似然"的梯度，等价于条件采样 |
| 转回噪声空间 | $\epsilon_{\text{guided}}=\epsilon_\theta-\sqrt{1-\bar\alpha_t}\nabla\log p_s$ | — | **本文的最终注入点** |
| 离散安全集 | $\mathcal{C}=\{\mathbf{x}:h(\mathbf{x})\ge0\}$，$h=(\mathbf{p}-\mathbf{c})^\top(\mathbf{p}-\mathbf{c})-r^2$ | $\mathbf{c}$ 障碍球心，$r$ 半径 | 球外为正、球内为负 |
| **DCBF 条件** | $h^v(\mathbf{x}_k,\mathbf{c})=h(\mathbf{x}_{k+1})-(1-\gamma)h(\mathbf{x}_k)\ge0$ | $\gamma\in(0,1]$ | 允许 $h$ 以 $(1-\gamma)^k$ 速率衰减，但不许穿零 |
| DCBF 展开 | $=\gamma(\mathbf{p}_k-\mathbf{c})^\top(\mathbf{p}_k-\mathbf{c})-\gamma r^2+2\Delta t(\mathbf{p}_k-\mathbf{c})^\top\mathbf{v}_k+(\Delta t)^2\|\mathbf{v}_k\|^2$ | $\Delta t=0.1$ s | 位置项 + **速度项**：速度也进入安全评分 |
| 安全评分 ($P_{\text{Logistic}}$) | $P_s=1/\big(1+\exp(-h^v/\sigma)\big)$ | $\sigma>0$ 不确定性尺度 | $h^v\gg0\to1$；$h^v<0\to0$，光滑可导 |
| 安全梯度 | $\nabla\log p_s=\nabla P_s/P_s$ | — | 对数形式让评分越接近 0，推力越大 |
| 多障碍屏障 | $V(\mathbf{x})=\sum_{\tau=1}^{N}\sum_{i=1}^{M}\max(0,-h(\mathbf{x}_\tau,\mathbf{c}_i))^2$ | $N$=时间步，$M$=障碍数 | hinge 平方：只在违规时罚，且越深越狠 |
| 时变引导强度 | $\gamma(t)=\gamma_{\max}(1-t/t_{\text{start}})^{\alpha}\mathbf{1}_{\{t\le t_{\text{start}}\}}$ | $\gamma_{\max}$=2000/4000，$t_{\text{start}}$=30，$\alpha$=2.0 | 只在扩散链的一段里加力，其余放开让模型自己雕细节 |

**三处需要核对的表述差异**（论文中并存，不能判断哪一个是最终实现，也不能断言是笔误）：

1. **$V$ 有两种定义**：式 (34) 的 hinge 平方 vs. Algorithm 1 第 7 行的 $V=-\log(P_{\text{safe}})$。两者梯度形状和量级不同。
2. **$\sqrt{1-\bar\alpha_t}$ 因子时有时无**：式 (22) 有，式 (35) 没有，Algorithm 1 第 8 行又有。
3. **时间调度描述不一致**：正文说"在**早期**扩散步加更强引导"；式 (36) 在 $t\le t_{\text{start}}=30$ 时非零；Algorithm 1 第 6 行写成 $\gamma_0(1-t/T)$（线性、无截断、无 $\alpha$ 幂次）。论文未明确 $t$ 的索引方向（从 $T$ 递减还是递增），因此无法单从公式判断"早期"对应哪一段。需以源码核对。

---

## 3 · 带数字走一遍（玩具设定，2D 简化，非论文数据）

**设定**：单障碍球，球心 $\mathbf{c}=(0,0)$，半径 $r=1.0$ m，安全裕度 20% → $R_s=1.2$ m。$\Delta t=0.1$ s（10 Hz）。当前预测点 $\mathbf{p}=(0.9,\,0)$，速度 $\mathbf{v}=(-2,\,0)$ m/s（**正朝球心方向**）。DCBF 参数 $\gamma=0.5$，评分尺度 $\sigma=0.5$。

**Step 1 — 原始 CBF 值**（只看位置）：
$$h=0.9^2-1.0^2=0.81-1.00=\mathbf{-0.19}$$
即该点已在球内 0.19 m 处。

**Step 2 — 加入速度项（DCBF 的关键）**：
$$h^v=\underbrace{0.5\times(-0.19)}_{\gamma(h-r^2)}=-0.095\;+\;\underbrace{2(0.1)(0.9)(-2)}_{2\Delta t(\mathbf{p}-\mathbf{c})^\top\mathbf{v}}=-0.36\;+\;\underbrace{(0.01)(4)}_{\Delta t^2\|\mathbf{v}\|^2}=+0.04$$
$$h^v=\mathbf{-0.415}$$
速度项把 $-0.19$ 进一步压到 $-0.415$：**正在靠近**这一事实被显式编码进评分。若速度反向（$+2$ m/s），则 $h^v=+0.305$——同一位置，安全评分截然不同。这是 DCBF 与静态距离项的区别所在。

**Step 3 — 安全评分**：
$$P_{\text{Logistic}}=\frac{1}{1+e^{-h^v/\sigma}}=\frac{1}{1+e^{0.83}}=\frac{1}{1+2.293}=\mathbf{0.304}$$
注意：这只是按式 (30) 构造的可微评分，论文**未验证**它是否校准为真实安全概率；下文只把它当作惩罚权重使用。

**Step 4 — 梯度**：
$$\frac{\partial h^v}{\partial \mathbf{p}}=2\gamma(\mathbf{p}-\mathbf{c})+2\Delta t\,\mathbf{v}=(0.9,\,0)+(-0.4,\,0)=(0.5,\,0)$$
$$\frac{\partial\log P}{\partial h^v}=\frac{1-P}{\sigma}=\frac{0.696}{0.5}=1.393$$
$$\nabla_{\mathbf{p}}\log P_s=1.393\times(0.5,\,0)=\mathbf{(0.696,\,0)}$$

方向 $+x$：$\mathbf{p}$ 在 $+x$ 侧，梯度指向远离球心的一侧。**速度项的影响**：无速度项时 $\partial h^v/\partial\mathbf{p}=(0.9,0)$，乘同一系数后为 1.253；有速度项时降为 0.696。说明 DCBF 的速度项会改变同一位置处的梯度大小。但**不能**由此推断控制器"必须改速度"——这只是该玩具点上的局部梯度差异，是否改变飞行行为取决于引导项注入后的实际采样。

**Step 5 — 注入噪声空间**：若按 Algorithm 1 第 8 行注入（取 $V=-\log P_s$，$\nabla V=(-0.696,0)$；取 $\sqrt{1-\bar\alpha_t}=0.5$）：

| $\gamma_t$ | 修正量 $\gamma_t\nabla V\sqrt{1-\bar\alpha_t}$ | 与 $\epsilon_\theta\sim\mathcal{O}(1)$ 的量级比 |
|---|---|---|
| 2000 | $(-696,\ 0)$ | ~700× |
| 4000 | $(-1392,\ 0)$ | ~1400× |

⚠️ 这是**玩具设定下的量级外推**（`UNVERIFIED` 分析）：论文未报告实现中是否对 $\nabla V$ 做归一化或裁剪，也未报告 $\epsilon_\theta$ 的实际幅值，$\sigma$ 只在图 2 caption 中给出 0.5。因此**不能**据此断定实际采样被引导项主导，**不能**把表 IV 的 RMSE 上升直接归因于"用力过猛"，也**不能**反推论文的 trade-off 表。它只提示一件事：$\gamma_{\max}$ 的取值必须与 $\nabla V$ 的数值尺度匹配，复现时应先核对二者比值。

---

## 4 · 工程视角

| 维度 | 数值 | 来源/说明 |
|---|---|---|
| 扩散步数（NFE） | **100** | 论文明确（Training Configuration: Diffusion steps: 100）→ 每条轨迹 **100 次网络前向**，DDPM，无加速采样器 |
| 序列长度 | 训练 **60**（6 s @10 Hz），历史 **20**（2 s） | 论文明确；§III-D-1 另写 $N=80$（8 s），两处表述不一致，需核对 |
| 状态维度 $D$ | **10** | 论文写 "speed, 3D position, 3D attitude" = 1+3+3 = **7**，与 10 对不上，论文未解释 |
| 模型规模 | 4 层 / 128 维 / 4 头 / dropout 0.1 | 论文明确；**参数量、FLOPs：论文未报告** |
| 训练配置 | batch 32，lr $1\times10^{-4}$，100 epochs，3000 条轨迹 | 论文明确 |
| 单条轨迹推理延迟 | **论文未报告** | V-A 把 "inference time" 列为评估指标，但全文**没有任何一个延迟数字** |
| FPS / 吞吐 | **论文未报告** | — |
| 显存 / 硬件型号 | **论文未报告** | 无 GPU 型号、无内存占用 |
| 引导的计算结构 | 每步一次模型前向得到 $\mathbf{x}_0^{\text{pred}}$，再在其上解析求 $\nabla V$ | Algorithm 1 的结构；该步相对开销**论文未报告** |
| 部署前提 | 障碍集（球心+半径）必须**在推理时已知且静态** | 论文明确假设；无感知前端（ontology: sensor=n/a） |

**Trade-off 的结构性判断**：

- **运行时**：论文未报告延迟、吞吐、硬件，也未与 CBF-QP、RRT 或任何规划器做运行时对比。因此**无法判断**其部署开销，也不能断言比滤波器快或慢。可确认的只有两点：采样需要 100 次网络前向（论文配置）；每步还要在 $\mathbf{x}_0^{\text{pred}}$ 上计算一次屏障梯度（Algorithm 1 结构）。实际耗时需实测（`UNVERIFIED`）。
- **调参预算**：$\gamma_{\max}$（2000/4000）、$t_{\text{start}}$（30）、$\alpha$（2.0）、$\sigma$（0.5）、$r$ vs $R_s$ 的裕度（20%）、CBF 的 $\gamma$（0.5）——多个耦合超参，且论文自述"最优配置取决于应用需求"。这对机载部署意味着额外的调参负担（本文未做机载实验）。
- **安全裕度的尺度语义**：按式 (24)(27)，$R_s=R_{\text{margin}}+r$ 是**相对障碍半径**的裕度，而 $h^v$ 里的 $\Delta t$ 固定为 0.1 s。障碍半径在 0.5–2.0 m 之间跨 4 倍、速度跨越特技包线时，同一组 $(\gamma,\sigma)$ 对应的保护强度是否变化，论文未讨论（`UNVERIFIED` 分析，非论文结论）。
- **确定性**：DDPM 采样含随机项 $\sigma_{\text{sample}}\mathbf{z}$，同一条件下多次采样结果可能不同。论文报告 200 条测试轨迹的统计量，**未报告方差/重复实验次数**；但缺少重复实验波动并不等于不能计算条件置信区间，零碰撞样本在独立同分布等假设下仍可估计条件置信区间，只是需明确其假设与适用范围。

---

## 5 · 数据与评测

> ⚠️ **仅 benchmark / 仿真验证**：本文全部量化结果来自**作者自建的 custom Python 仿真环境**，无真机飞行、无公开 benchmark；本文未核查第三方复现，不能据此断言不存在第三方复现。所有"安全"结论仅在该仿真设定及相应假设下成立，**不构成真实飞行安全保证**。

### 5.1 数据组成（逐字）

- **专家演示**：**2,000** 条轨迹，覆盖 **14** 种特技：power loop、barrel roll、split S、Immelmann、wall ride、figure eight、star、half moon、sphinx、clover、spiral inward、spiral outward、spiral vertical up、spiral vertical down。
- **数据增强**：smooth concatenation，**+50%** 额外轨迹，blend window **5** 帧 → 训练集 **3,000** 条。
- **演示轨迹的生成器/规划器**：**论文未报告**（只写 "Data Generation"，未说明用什么算法、什么飞行动力学模型产生这 2000 条）。
- **训练数据是否需要无碰撞**：论文主张**不需要**（"without collision-free demonstrations being required"），但**未做"含碰撞训练数据"的对照实验**来验证这一主张。

### 5.2 评测设置（讲条件）

- 环境：custom Python；**3–5 个随机放置的球障碍**；障碍半径 **0.5–2.0 m**；安全裕度 **障碍半径的 20%**；轨迹 **60 步（6 s）**。
- 测试规模：消融 **200** 条测试轨迹；表 III 中 unguided 组样本量为 **800**（3 障碍）和 **500**（5 障碍），CBF-guided 组均为 **200**。
- **成功判定（三条同时满足）**：
  1. 无碰撞：$\|\mathbf{p}(t)-\mathbf{c}_o\|_2\ge r_o$，对所有 $t$、所有障碍 $o$；
  2. 轨迹精度：$\max_t\|\mathbf{p}_{\text{pred}}(t)-\mathbf{p}_{\text{gt}}(t)\|_2<2.0$ m；
  3. 到点：$\|\mathbf{p}_{\text{pred}}(T)-\mathbf{p}_{\text{target}}\|_2<1.0$ m。
- 指标：collision rate、mean AE、min distance、success rate、position/velocity RMSE、smoothness（加速度方差）、style accuracy。

### 5.3 结果（逐字抄录，不做任何四舍五入或推断）

**表 II — 消融（200 条测试轨迹）**

| Configuration | Encoder | Safety Func. | $\gamma$ | Collision (%) | Mean AE (m) | Min Dist (m) | Success (%) |
|---|---|---|---|---|---|---|---|
| Unguided | ✓ | × | × | 12.0 | 1.641 | 0.537 | 29.5 |
| **A (Ours)** | ✓ | $P_1$ | 2000 | **2.0** | 1.685 | 0.550 | **31.5** |
| Unguided | × | × | × | 99.0 | 0.356 | −0.447 | 1.0 |
| **B** | × | $P_1$ | 2000 | 46.5 | 0.570 | −0.007 | 47.5 |
| **B** | × | $P_1$ | 4000 | **8.5** | 0.693 | 0.1623 | **67.0** |
| **C** | × | $P_{\text{Logistic}}$ | 4000 | **0.0** | 0.982 | 0.665 | 42.0 |

**表 III — 安全性能（Config C）**

| Configuration | Collision Rate (%) | Avg. Min Distance (m) | Safety Violations |
|---|---|---|---|
| Unguided (3 obs) | 23.4 | −0.42 | 187/800 |
| Unguided (5 obs) | 96.0 | −0.40 | 480/500 |
| CBF-guided (3 obs) | 0.0 | 0.89 | 0/200 |
| CBF-guided (5 obs) | 0.0 | 0.66 | 0/200 |

**表 IV — 轨迹质量（Config C）**

| Metric | Unguided | CBF-guided | Ground Truth |
|---|---|---|---|
| Position RMSE (m) | 0.47 | 1.19 | — |
| Velocity RMSE (m/s) | 0.31 | 0.78 | — |
| Smoothness (accel. variance) | 0.12 | 0.24 | 0.12 |
| Style accuracy (%) | 94.0 | 68.0 | 100 |

### 5.4 ⚠️ 数字之间的内部差异（原样列出，不替作者圆场）

1. **摘要/结论 vs 结果表**：摘要称 collision rates 降低 **94.7%**；结论又称 "preserving trajectory agility (**92.4%** average success rate)"。但表 II 中最高成功率仅 **67.0%**（Config B, $\gamma$=4000），**无任何一行支持 92.4%**。94.7% 也无法由 96.0%→0.0%（=100%）或 12.0%→2.0%（=83.3%）直接算出。
2. **同一成功率两个值**：§V-C-4 写 Config C 成功率 **42.0%**，§VI-A 写 **42.6%**。
3. **无出处的基础误差**：§V-C-4 写 "mean absolute error increases from **0.399 m** to 0.982 m (+146%)"，但表 II 中无编码器的 unguided 是 **0.356**，全表无 0.399。
4. **表 II 行标签重复**：两组配置都叫 "B"，仅 $\gamma$ 不同（2000 / 4000），易误读；解读时需按 $\gamma$ 区分。

---

## 6 · 能力与失败模式

### 6.1 能做（具体）

- 在**自定义仿真**中，对 **14 类特技**生成 60 步轨迹；Config C 在 3 障碍与 5 障碍两种设置下均报告 **0.0%** 碰撞（各 200 条，表 III）。
- **不需要**用安全验证过的数据重训：引导在推理期发生，训练好的权重可复用（作者主张；论文未做"含碰撞训练数据 vs 无碰撞训练数据"的对照实验来验证）。
- **障碍编码对碰撞率有可观影响**：带 encoder 的 unguided 基线碰撞率 12.0%，不带 encoder 的 unguided 为 **99.0%**（表 II）。这是两个不同配置的观测值；论文未做 encoder × guidance 的全因子对照，因此**不能据此量化** encoder 与 CBF 引导各自的贡献，也不能断言"encoder 贡献远大于引导"。
- **在不带 encoder 的配置内，引导强度与碰撞率同向变化**：$\gamma$: 0 → 2000 → 4000（均用 $P_1$）对应碰撞率 99.0% → 46.5% → 8.5%。这仍是单次统计，论文未报告方差或重复次数。

### 6.2 不能做 / 失败模式（具体）

| 失败模式 | 触发条件 | 论文证据 |
|---|---|---|
| **保真度下降** | 强引导 $\gamma_{\max}$=4000 + Logistic | 位置 RMSE 0.47→1.19 m；速度 RMSE 0.31→0.78 |
| **特技风格被削弱** | 同上 | style accuracy 94.0%→68.0% |
| **轨迹变抖** | 同上 | smoothness（加速度方差）0.12→0.24（GT 也是 0.12） |
| **复杂特技成功率低** | sphinx / eight_figure | 论文自报成功率 30–32% |
| **同 $\gamma$、不同评分函数，结果差异明显** | Config B($\gamma$=4000, $P_1$) vs Config C($\gamma$=4000, $P_{\text{Logistic}}$) | 成功率 67.0% vs 42.0%；AE 0.693 vs 0.982 m。注意两者评分函数不同，表 I 显示 $P_1$ 在 $R_s$ 处为 1.0、Logistic 为 0.5，数值尺度不同，**不能把差异直接归因于引导强度** |
| **动障碍 / 未知障碍** | 论文明确列为 limitation | 仅静态球、位置半径已知 |
| **非球几何** | 论文明确列为 limitation | "generalizing to arbitrary convex or non-convex shapes is an important direction" |
| **部分可观测** | 论文明确列为 limitation | 无感知/建图环节 |
| **新特技 few-shot / zero-shot** | 论文明确列为 limitation | 需 2,000 条专家演示 |
| **软引导不提供形式化保证** | 机制层面 | CBF 条件被嵌入 logistic/指数评分再取对数梯度，没有约束求解、投影或可行性检查；$h^v\ge0$ 未被硬性强制，论文未给出前向不变性证明。这不等于"该方法不可能证明安全"，只是本文的构造未提供该类保证 |

### 6.3 隐含假设 (Hidden Assumptions)

1. **障碍是完美已知的静态球**。$h(\mathbf{x})=(\mathbf{p}-\mathbf{c})^\top(\mathbf{p}-\mathbf{c})-r^2$ 直接把 $\mathbf{c},r$ 当常量。任何位置误差、半径低估或运动，都会让 $P_s$ 的评分偏高——而引导强度是按"评分已准确"来定的。
2. **轨迹序列上的每一点都对应一个真实的动力学可达状态**。DCBF 里的 $\mathbf{v}_k$ 从序列中取得（状态含 speed 与姿态），但训练损失只惩罚位置/速度/加速度/连续性，**没有显式的动力学可行性约束**（无推力/角速率上限）。所以"几何上不撞"≠"飞得出来"。
3. **$h^v$ 的数值尺度是良态的**。$h^v$ 以 m² 为单位（$\gamma d^2 + 2\Delta t\,d\,v + \Delta t^2 v^2$），而 $\sigma=0.5$ 在图 2 caption 中固定；障碍半径 0.5–2.0 m 跨度 4 倍、速度跨越特技包线时 $\sigma$ 是否随之缩放，论文未讨论。
4. **一步预测 $\mathbf{x}_0^{\text{pred}}$ 是引导的可靠载体**。Algorithm 1 在每步先预测干净的 $\mathbf{x}_0$，再在它上面算 $\nabla V$，然后把修正注入第 $t$ 步的噪声。这假设 $\mathbf{x}_0^{\text{pred}}$ 已足够准；在扩散早期（高噪声）该假设最弱。论文对引导生效时段有不止一种表述（见 §8），实际把最大权重放在哪一段需核对。
5. **"不需要安全训练数据"** 这个卖点，依赖演示数据产生的分布本身离障碍足够近（否则引导无事可做），又足够不安全（否则无处体现收益）——这是一个未被实验验证的中间地带假设。
6. **随机性是"多样性"而不是"风险"**。$\sigma_{\text{sample}}$ 的采样噪声在 100 步里累积，同一条件多次生成结果不同；论文报告单次统计量，未给重复实验的方差。
7. **安全评分的数值可解释为概率**。式 (28)–(30) 的 $P_s$ 只是把 $h^v$ 映射到 $(0,1)$ 的平滑函数，论文未做校准性检验；把它称作"安全概率"是构造性命名，不是统计意义上的频率保证。

---

## 7 · 与相关工作对比

| 方法 | 安全机制 | 何时介入 | 训练数据是否需安全 | 是否有形式保证 | 计算开销 |
|---|---|---|---|---|---|
| RRT* / A* [8] | 采样/搜索 + 后平滑 | 规划期 | 否 | 否（离散无碰） | 高维退化明显（论文定性描述） |
| 凸 MPC-CBF [11] / GPBF [12] / 因子图 CBF [14] / 时变 CBF [15] | CBF 硬约束（QP/优化） | 控制期 | 否 | 在模型、可行性与定理假设满足时具有前向不变性 | 每步解一个优化问题（具体耗时本文未报告） |
| classifier guidance [10] | 额外预训练分类器给梯度 | 采样期 | 需额外模型 | 否 | 中（多一次前向+反传） |
| projection curriculum [9] | 用"投影后轨迹 vs 原轨迹"当损失 | **训练期** | 需安全投影算子 | 否 | 需重训 |
| planning-as-inference [7] | 后验引导 | 采样期 | 否 | 否 | 中 |
| 特技扩散 [6]（本文 baseline） | 无 | — | 否 | 否 | 100 NFE（本文配置） |
| **AeroTrajGen（本文）** | CBF → 安全评分 → score 加项 | **采样期** | **宣称不需要**（未做对照验证） | **否**（软引导，论文未给证明） | 100 NFE + 每步一次屏障梯度 |

**定位一句话**：比 classifier guidance [10] 省一个额外网络（CBF 是解析式）；比 projection curriculum [9] 省一次重训（推理期生效）；相比 CBF-QP 滤波器，它不把安全做成输出端的硬投影——但本文的构造也**没有提供**硬约束那一侧的前向不变性保证，这一点论文未充分讨论。

### 🎯 面试 Tip

被问"**这跟直接拿 CBF 做个安全滤波器（在输出轨迹上做投影/QP）有什么区别？**"——标准答法分三层：

1. **机制层**：滤波器是 post-hoc，先有一条可能很烂的轨迹再修，修完可能不可行；本文是 in-loop，安全梯度作用在**去噪链的每一步**上，最终样本在生成过程中持续受安全梯度影响，不依赖"事后可修复性"。
2. **代价层**：本文的构造不提供**前向不变性**保证。$h^v\ge0$ 只是被嵌入 logistic/指数评分再取对数求导，是一个**软惩罚**，没有任何一步强制它成立——所以论文只能说"collision rate 0.0% on 200 trajectories"，不能说"保证不撞"。
3. **实证层**：论文自己的表 IV 显示，$\gamma$=4000 时 RMSE 从 0.47 涨到 1.19 m、风格准确率从 94.0% 降到 68.0%。这提示软引导的代价需要用精度与风格指标来度量；零碰撞的统计结果是否可外推到其他障碍分布/动力学包线，论文未验证。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-18)

**仓库信号状态（未核查）**：论文摘要末句以**纯文本**给出代码地址（`RoboticsPolyu/CBF-DMP`），该字符串出现在 arXiv v1 HTML 全文中。本次**未访问该地址、未做任何代码审查**，因此不掌握其 commit / issue / release 状态，也不对其链接可用性作判断。按本笔记的判定规则（纯文本地址不构成已验证的 repo 信号），**以下 3 条 pitfall 与 1 条形状级疑点全部由 §6 失败模式 + 论文自身公式/参数约束推导，未经任何 issue 验证**，不引用任何 issue 编号、标题或日期。

---

**Pitfall 1 — 引导项用哪个 $V$、是否乘 $\sqrt{1-\bar\alpha_t}$：论文给出三种写法，需以源码核对**

- **来自 §6 的失败模式**：安全性完全依赖这一个加项的符号与量级（§6.2 最后一行"软引导不提供形式化保证"）；若符号取反，引导会把轨迹往障碍方向推。
- **来自方法约束的具体冲突**：
  - 式 (22)：$\epsilon_{\text{guided}}=\epsilon_\theta-\sqrt{1-\bar\alpha_t}\nabla\log p_s$
  - 式 (35)：$\epsilon_{\text{guided}}=\epsilon_\theta+\gamma_t\nabla_{\mathbf{x}}V(\mathbf{x}_t)$，其中 $V$ 是式 (34) 的 **hinge 平方**，**无** $\sqrt{1-\bar\alpha_t}$ 因子
  - Algorithm 1 第 8 行：$\epsilon_{\text{guided}}\leftarrow\epsilon_{\text{pred}}+\gamma_t\nabla V\sqrt{1-\bar\alpha_t}$，但第 7 行明确 $V=-\log(P_{\text{safe}})$，**又是另一个 $V$**
- **待核对项**：三种写法在"$V$ 的定义 × 符号 × 缩放因子"上不一致。哪一种对应实际实现，论文未说明，本次也未做代码审查，无法确认。复现时应先固定一种并显式记录，否则碰撞率与 RMSE 无法与论文表格对齐。这是待复现核对项，**不断言源码有误**。

---

**Pitfall 2 — $\gamma_{\max}=4000$ 与 $\epsilon_\theta$ 的量级关系需复现核对（论文未报告 $\nabla V$ 是否归一化）**

- **来自 §6 的失败模式**：$\gamma$=4000 时 Position RMSE 0.47→1.19 m、style accuracy 94.0→68.0（表 IV）——这是"引导项可能与生成先验量级不匹配"的一个观测信号。
- **玩具量级推导**（§3，`UNVERIFIED` 分析）：在该玩具点，$\nabla\log P_s\sim\mathcal{O}(1)$（0.696），$\sqrt{1-\bar\alpha_t}=0.5$，则 $\gamma_t\nabla V\sqrt{1-\bar\alpha_t}$ 在 $\gamma_t=4000$ 时约 $10^3$ 量级，而 $\epsilon_\theta$ 通常为 $\mathcal{O}(1)$。
- **为什么不能下结论**：论文未报告实现中是否对 $\nabla V$ 做范数裁剪/均值归一化，也未报告 $\epsilon_\theta$ 的实际幅值，$\sigma$ 只在图 2 caption 中写 0.5。因此**不能**说"只有归一化才成立"，也**不能**说"原样实现就会轨迹稀烂"。可执行的排查建议：先把 $\gamma_t$ 固定为 1，记录 $|\gamma_t\nabla V|$ 与 $|\epsilon_\theta|$ 的实测比值，再对照论文报告的 RMSE/风格准确率变化，判断论文所用参数落在什么量级区间。

---

**Pitfall 3 — 引导生效时段：正文、式 (36)、Fig. 3 与 Algorithm 1 的表述不一致，需核对 $t$ 的索引方向**

- **来自 §6 的失败模式**：引导太晚会来不及纠（后期噪声小、已无自由度），太早可能压平全局结构（高噪声期 $\mathbf{x}_0^{\text{pred}}$ 最不准，见 §6.3 假设 4）。
- **来自方法约束的表述差异**：
  - 正文（§IV-C）：「we apply stronger guidance in the **early** diffusion steps … allowing more freedom in later steps」→ 早期加力；
  - 式 (36)/(38)：$\gamma(t)=\gamma_{\max}(1-t/t_{\text{start}})^{\alpha}\mathbf{1}_{\{t\le t_{\text{start}}\}}$，$t_{\text{start}}=30$ → 仅在 $t\le30$ 时非零；若 $t$ 是从 100 递减的去噪索引，则落在去噪后段，与正文"早期"方向不一致；
  - Fig. 3 caption：$t_{start}=0.3$（归一化）——与 §IV-C 的 $t_{start}=30$ 在 $T=100$ 时等价，**不构成额外矛盾**；该图未标注 $t$ 的索引方向；
  - Algorithm 1 第 6 行：$\gamma_t\leftarrow\gamma_0(1.0-t/T)$ → 线性、无 $t_{\text{start}}$ 截断、无 $\alpha$ 幂次，与式 (36) 形式不同。
- **待核对项**：论文未明确 $t$ 的索引方向，也未说明 Algorithm 1 与式 (36) 哪一个是最终实现。复现时应先把 $\gamma(t)$ 曲线按实际循环方向画出来，确认非零区间落在扩散链的哪一段，再与正文描述对齐。选错时段的影响是引导可能作用在样本已基本定型的阶段，导致"看不出效果"。此为待复现核对项，**不断言源码错误**。

---

**附加疑点（形状级，非 issue 验证）：$N$ 与 $D$ 的取值在正文中不一致，加载 checkpoint 前需核对**

- §III-D-1：$\mathbf{x}\in\mathbb{R}^{N\times D}$，$N=80$（8 s @10 Hz），$D=10$（speed + 3D position + 3D attitude）。
- §IV-A：Sequence length **60**（6 s @10 Hz），history **20**。
- §V-A：trajectory length **60 timesteps**。
- $D=10$ 但列出的分量只有 $1+3+3=7$，论文未解释剩余 3 维是什么。
- **待核对项**：$N=80$ 与 60 的差异会影响 position encoding 维度与序列形状；但轨迹长度 $N$ 不决定扩散噪声表 `alpha_bars[t]` 的索引，后者由扩散步数 $T$ 决定，$t_{\text{start}}=30$ 的语义也需结合 $T$ 与源码/checkpoint 形状核对（本次未做代码审查，仓库状态未核查），不能仅凭论文判断实现有误。

---

[← Back to navigation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 2604.17527**v1** 全文（2026-04-19，cs.RO）· 标准入口 https://arxiv.org/html/2604.17527v1 ；v3 于 2026-10-18 抓取时不可取得（HTTP 404），**不能代表最新版本，本笔记不覆盖 v3** · 全部量化结果**仅在作者自建 Python 仿真中获得**，⚠️ 仅 benchmark/仿真验证，未在真机复现 · §4 中的延迟/显存/吞吐/硬件、§5 中的演示数据生成器，论文均未报告 · §3 玩具算例、§4 与 §8 中的量级推导均为本笔记分析，标 `UNVERIFIED`；仓库状态未核查，未引用任何 commit/issue/release 信息。

[//]: # "<!-- source: https://arxiv.org/abs/2604.17527 -->"
