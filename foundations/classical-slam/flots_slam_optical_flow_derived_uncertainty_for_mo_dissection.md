[//]: # "<!-- ontology-5axis
problem: VSLAM
representation: n/a
sensor: mono
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->"

# 光流不确定性驱动的单目动态 SLAM：两阶段优化 (FLoTS-SLAM: Optical Flow-Derived Uncertainty for Monocular Dynamic SLAM with Two-Stage Optimization)

> **发布时间**：2026-10-16（arXiv:2610.23496v1 [cs.RO]）
> **论文 / 模型名**：FLoTS-SLAM（**F**low-derived uncertainty + **T**wo-**S**tage optimization）
> **核心定位**：把"动态像素判定"从**外观/渲染残差**换成**光流—相机诱导流残差**（直接运动证据），并用**两阶段优化 + 动态像素重锚定**取代"只在 BA 里降权"，在 Bonn/TUM 上把 DROID-SLAM 骨干的 ATE 降 59%/19%。

动态场景下，语义分割/检测只能看见"会动的类"，渲染残差与多视图特征一致性只是"间接运动证据"；更关键的是——**估错了不确定性，加权降权也救不回来**。本文的答案是：用光流残差直接量化运动，并且**不让高不确定像素去同时更新位姿和深度**。

## X-Ray 开场

单目 SLAM 在动态场景失效的根因是：BA 假设"每个像素残差都来自位姿/深度误差"，而运动物体违反这一假设，解算器会把物体运动吸收进位姿和深度。已有做法（WildGS-SLAM、DROID-W）都只输出逐像素不确定性并在 BA 里**降权**，但降权后残差仍在，只是变弱；运动残差是**系统性偏移**而非零均值噪声，最小二乘压不住。本文提出两点：(1) 用 **光流与相机诱导流之差** 作为直接运动证据构造不确定性，并让残差变换随**帧对齐质量**自适应，避免"位姿还没收敛就把静态像素判成动态"；(2) **两阶段优化**：先用最低不确定像素**只用位姿（深度冻结）**解一个参考位姿 $G^*$，再用 $G^*$ 把高不确定像素的**对应目标本身替换掉**（re-anchoring）。对 spatial AI 研究者而言，它的意义是给出了"**不确定性不是权重，而是数据关联的否决票**"这一可复用范式。

## 📍 研究全景时间线

```
MOS / 视频分割网络 (需多帧窗口, 实时性差)
        │
        ▼
动态 SLAM: 语义先验 (DynaSLAM: Mask R-CNN + 多视图重投影验证)
   └─ 缺陷: 按"类别"判运动, 未见类别漏检 / 静态椅误判
        │
        ▼
DROID-SLAM (稠密可微 BA, 本文骨干)
        │
        ├──► 语义/几何混合: DynaMoN(MS&SS), DynoSAM, BA-Track
        │
        ├──► 动态 NeRF/3DGS SLAM: PG-SLAM, NID-SLAM, SDD-SLAM, DG-SLAM,
        │     UP-SLAM, ADD-SLAM, Flow4DGS-SLAM  ← 掩码仍多来自分割网络
        │
        └──► 逐像素不确定性路线
              ├─ WildGS-SLAM: DINOv2 特征 → MLP, 由渲染残差在线监督
              │     └─ 缺陷: 建图不准 → 不确定性不准
              ├─ DROID-W: 多视图特征不一致性 (无需渲染)
              │     └─ 缺陷: 仍是"外观"间接证据, 弱纹理/语义复杂处失效
              └─ ★ FLoTS-SLAM (2026-10)
                    光流残差(直接运动证据) + 对齐自适应 ψ(·)
                    + 两阶段优化 + 动态像素重锚定
                    局限: 无回环/全局一致性仅靠末次全局调整;
                          中位数假设依赖"静态背景占多数"
```

> 注：时间轴按论文引用谱系排序；除本文 2026-10 外，论文正文**未给出**各方法的发表年份。

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 | 论文是否明说 |
|---|---|---|---|---|
| DROID-SLAM recurrent update operator | 关键帧对 $(i,j)$ 特征 | 稠密对应目标 $\mathbf{p}^*_{ij}$ + 置信度 $\mathbf{W}_{ij}$ | **预训练、权重冻结**；推理时每步前向 | ✅ "pre-trained ... remain frozen" |
| DINOv2 | RGB 关键帧 | 特征 $\mathbf{f}_i$ | **冻结**；仅作不确定性头输入 + $\mathcal{L}_{sim}$ | ✅ |
| Metric3D | RGB | 深度先验 $\hat{\mathbf{d}}_i$ | **冻结**；对齐到当前尺度后作正则项 | ✅ |
| 不确定性头 $h_{\bm\theta}$（affine + offset softplus） | $\mathbf{f}_i(\mathbf{u})$ | $\sigma_i(\mathbf{u})$ | **在线逐序列优化**（无离线训练集） | ✅ |
| 稠密 BA（Gauss–Newton） | $\mathbf{p}^*,\mathbf{W},\bm\sigma,\hat{\mathbf{d}}$ | $\mathbf{G},\mathbf{d}$ 增量 | 推理时求解；每步与不确定性头**交替**更新 | ✅ |
| Stage I 位姿求解 | 低不确定像素集 $\mathcal{S}_i$ | 参考位姿 $\mathbf{G}^*$（深度冻结） | 仅推理；$\Delta\mathbf{d}\equiv0$ | ✅ |
| Stage II 联合精化 + re-anchor | $\mathcal{D}_i$ 的目标被 $\hat{\mathbf{p}}_{ij}$ 替换 | 最终 $\mathbf{G},\mathbf{d}$ | 仅推理；$\hat{\mathbf{p}}_{ij}$ **只算一次后固定** | ✅ |

### 1.2 关键机制

- **运动不确定性**：$\mathbf{r}_{ij}=\mathbf{p}^*_{ij}-\mathbf{p}_{ij}$（光流 − 相机诱导流），两项共用源坐标故相减即得"相机+深度解释不了的那部分位移"。静态背景随优化收敛 $\mathbf{r}\to0$，运动物体上持续存在。
- **对齐自适应变换**：$\psi(r)=\beta r^2+(1-\beta)\log(1+r^2)$，$\beta=\mathrm{sigmoid}(\tau_r-\bar r)$。对齐差（$\bar r$ 大）时 $\beta\to0$，对数为压缩 → 不把"没对齐的静态像素"判成动态；对齐好后 $\beta\to1$ 退化为 $r^2$。
- **两阶段**：Stage I 只用最低分位像素、**冻结深度**估位姿（正常方程退化为 $\mathbf{B}\Delta\bm\xi=\mathbf v$）；Stage II 用 $\mathbf{G}^*$ 预测"若场景静止该像素应出现在哪"，替换 $\mathcal{D}_i$ 的**目标本身**。
- **重锚定的数学效果**：$\hat{\mathbf{p}}_{ij}-\mathbf{p}_{ij}$ 在 $\mathbf{G}=\mathbf{G}^*,\mathbf{d}=\mathbf{d}^*$ 处**为零**，因此线性化时对梯度 $\mathbf{v},\mathbf{w}$ **无贡献**（运动不再推开位姿/深度），但**仍进入 Hessian** $\mathbf{B},\mathbf{E},\mathbf{C}$，保留参考状态附近的二次约束。

> ⚡ **Eureka Moment**：动态像素的问题不是"权重太大"，而是"它被匹配到了它实际被观测到的位置"——**把它的匹配目标换成"静止假设下应在的位置"，残差在参考状态处就自动归零**，运动对位姿/深度的梯度贡献从源头被切除，而不是靠调小权重去压制。

### 1.3 信息流 / 架构图

```
RGB 序列 {I_i}
   │
   ├─► DINOv2 (frozen) ──► 特征 f_i ──┬─► 不确定性头 h_θ ──► σ_i (逐像素)
   │                                 └─► L_sim (特征一致性, 软权重)
   ├─► DROID update op (frozen) ──► p*_ij , W_ij ──► 光流 p*_ij − u
   └─► Metric3D (frozen) ──► d̂_i (尺cał对齐) ──► 深度正则
                              │
           p_ij = Π(G_ij, Π⁻¹(p_i, d_i))   (相机诱导流)
                              │
                     r_ij = p*_ij − p_ij
                              │
                  L_flow(σ) = Σ [ ψ(r)/(2σ²) + log σ ]
                              │
        ┌─────────────────────┴─────────────────────┐
        │  每步交替: (a) 固定 σ 走 GN 更新 G,d        │
        │           (b) 固定 G,d 走梯度更新 θ         │
        └─────────────────────┬─────────────────────┘
                              │
        Stage I : argmin_G Σ_{u∈𝒮_i} ‖p*−p‖²_W      (Δd ≡ 0)
                              │  → G*
                              ▼
        Stage II: p̃*_ij(u) = p̂_ij(u) 若 u∈𝒟_i     (用 G*,d* 算一次后固定)
                  argmin_{G,d} Σ ‖p̃*−p‖²_Ω + λ_d Σ‖d−d̂‖²
```

## 2 · 数学核心

📌 **Napkin Formula**：

$$\sigma^2(\mathbf{u}) \approx \psi\big(\|\mathbf{p}^*_{ij}(\mathbf{u})-\mathbf{p}_{ij}(\mathbf{u})\|\big),\qquad \psi=\beta r^2+(1-\beta)\log(1+r^2),\ \ \beta=\mathrm{sigmoid}(\tau_r-\bar r)$$

一句话：**不确定性的方差 ≈ 光流残差，但残差要先按"这次对齐靠不靠谱"（中位数残差 $\bar r$）打折。**

### 2.1 目标 → 公式 → 变量 → 直觉

**（a）基础稠密 BA**（式 2）

$$\mathcal{L}_{\mathrm{ba}}(\mathbf{G},\mathbf{d})=\sum_{(i,j)\in\mathcal{E}}\|\mathbf{p}^{*}_{ij}-\mathbf{p}_{ij}\|^{2}_{\mathbf{W}_{ij}}+\lambda_d\sum_{i\in\mathcal{V}}\|\mathbf{d}_i-\hat{\mathbf{d}}_i\|^{2}$$

- $\mathbf{G}_i\in SE(3)$ 位姿、$\mathbf{d}_i\in\mathbb{R}^{(H/8)\times(W/8)}$ 逆深度（$1/8$ 分辨率）、$\mathbf{W}_{ij}$ 更新算子预测的对角置信度、$\hat{\mathbf{d}}_i$ Metric3D 先验。
- 第二项存在的理由：**单目视差只可观测到尺度**，必须有度量先验锚定；先验先对齐到当前尺度。
- 线化得 $\begin{bmatrix}\mathbf{B}&\mathbf{E}\\ \mathbf{E}^{\mathsf T}&\mathbf{C}\end{bmatrix}\begin{bmatrix}\Delta\bm\xi\\ \Delta\mathbf{d}\end{bmatrix}=\begin{bmatrix}\mathbf{v}\\ \mathbf{w}\end{bmatrix}$，$\mathbf{E}$ 是位姿-深度耦合块（后面 §6 的失败模式就来自它）。

**（b）不确定性加权**（式 4）

$$\bm{\Omega}_{ij}(\mathbf{u})=g\big(\sigma_i(\mathbf{u})\big)\,\mathbf{W}_{ij}(\mathbf{u})$$

$g(\cdot)$ 单调递减（论文**未给具体形式**）；高不确定像素"贡献变小但仍在 frame graph 里"。

**（c）不确定性损失**（式 6）

$$\mathcal{L}_{\mathrm{flow}}(\bm{\sigma})=\sum_{(i,j)\in\mathcal{E}}\sum_{\mathbf{u}}\left[\frac{\psi\big(r_{ij}(\mathbf{u})\big)}{2\,\sigma_i(\mathbf{u})^{2}}+\log\sigma_i(\mathbf{u})\right]$$

这是高斯负对数似然的形状：$-\log \frac{1}{\sigma}\exp(-\frac{\psi}{2\sigma^2})$。**逐像素对 $\sigma$ 求极小 ⇒ $\sigma^2=\psi(r)$**（这正是 §3 玩具例子的依据）；$\log\sigma$ 项防止 $\sigma\to\infty$ 的平凡解。

**（d）$\psi$ 与 $\beta$**（式 7、8）：$\bar r$ 是**当前优化窗口内所有像素 $r$ 的中位数**，$\tau_r$ 是转换的"对齐水平"。$\beta\to0$ ⇒ 对数压缩（重尾残差被压平，不判动态）；$\beta\to1$ ⇒ 退回平方（正常判动态）。

**（e）总不确定性代价**（式 9）：$\mathcal{L}_{\mathrm{unc}}=\lambda_{\mathrm{sim}}\mathcal{L}_{\mathrm{sim}}+\lambda_{\mathrm{flow}}\mathcal{L}_{\mathrm{flow}}$。$\mathcal{L}_{\mathrm{sim}}$ 是 DROID-W 的 DINOv2 特征一致性代价，本文把它的**相似度阈值换成连续加权**（不确定性随相似度连续变化），用来补 $\mathcal{L}_{\mathrm{flow}}$ 缺失的**物体级连贯性**（逐像素独立 ⇒ 掩码可能碎）。

**（f）参数化与交替**：$\sigma_i(\mathbf{u})=h_{\bm\theta}(\mathbf{f}_i(\mathbf{u}))$（affine + **offset softplus**，保证 $\sigma>0$ 且远离 0），$\bm\theta$ **跨序列共享** ⇒ 相似 DINOv2 特征的像素获一致不确定性；不直接优化逐像素 $\sigma$ 是为了防过拟合噪声、防空间不一致。

**（g）Stage I**（式 10）：$\mathcal{S}_i$ = $\bm\sigma_i$ 最低分位像素；$\mathbf{W}$ 用**原始置信度，不再乘 $g(\sigma)$**——不确定性在这里只当**选择器**，不当权重。

**（h）Stage II + 重锚定**（式 11–13）：

$$\hat{\mathbf{p}}_{ij}=\Pi_c\!\left(\mathbf{G}^{*}_{ij},\,\Pi_c^{-1}(\mathbf{p}_i,\mathbf{d}^{*}_i)\right),\quad \tilde{\mathbf{p}}^{*}_{ij}(\mathbf{u})=\begin{cases}\hat{\mathbf{p}}_{ij}(\mathbf{u}),&\mathbf{u}\in\mathcal{D}_i\\ \mathbf{p}^{*}_{ij}(\mathbf{u}),&\text{otherwise}\end{cases}$$

$$\mathcal{L}_{\mathrm{st2}}=\sum_{(i,j)\in\mathcal{E}}\|\tilde{\mathbf{p}}^{*}_{ij}-\mathbf{p}_{ij}\|^{2}_{\bm{\Omega}_{ij}}+\lambda_d\sum_{i}\|\mathbf{d}_i-\hat{\mathbf{d}}_i\|^{2}$$

## 3 · 带数字走一遍（玩具设定，1 维像素）

> 以下数字是**教学用玩具设定**，不是论文实验值。

设某像素光流有两种情形，相机诱导流 $p_{ij}-u=2.0$ px：

- **静态像素**：$\mathbf{p}^*_{ij}-u=2.05$ ⇒ $r=|2.05-2.0|=0.05$
- **运动像素**：$\mathbf{p}^*_{ij}-u=10.0$ ⇒ $r=8.0$

取窗口内中位数 $\bar r=0.6$，$\tau_r=1.0$ ⇒ $\beta=\mathrm{sigmoid}(1.0-0.6)=\mathrm{sigmoid}(0.4)\approx0.599$。

$$\psi(0.05)=0.599(0.0025)+0.401\log(1.0025)\approx0.0015+0.0010=0.0025$$
$$\psi(8)=0.599(64)+0.401\log(65)\approx38.34+0.401(4.174)=38.34+1.67=40.01$$

由 $\sigma^2=\psi(r)$：$\sigma_{\text{static}}\approx\sqrt{0.0025}=0.05$，$\sigma_{\text{moving}}\approx\sqrt{40.01}=6.32$。

若取 $g(\sigma)=1/(1+\sigma^2)$（**论文未给 $g$，此处为演示**）：静态权重 $\approx0.998$，运动权重 $\approx1/41\approx0.024$ ⇒ 运动像素被压到 2.4%。

**再看 $\beta$ 的作用**：若这帧对齐很差，$\bar r=3.0$ ⇒ $\beta=\mathrm{sigmoid}(-2)\approx0.119$，
$\psi(8)=0.119(64)+0.881\log(65)\approx7.62+3.68=11.30$ ⇒ $\sigma\approx3.36$ ⇒ 权重 $\approx1/12.3\approx0.081$。
**同一个 $r=8$ 的像素，在"帧还没对齐"时被压制的程度从 41× 降到 12×** —— 这就是"避免早期把静态像素误判为动态、进而切断收敛所需对应"的机制。

**重锚定的数值直觉**：Stage I 用 $\mathcal{S}_i$ 解出 $G^*$；对 $\mathcal{D}_i$ 中那个运动像素，原残差 $\mathbf{p}^*-p=8$ px（会把共享位姿往错误方向推）；替换后 $\hat{\mathbf{p}}=p$（在 $G^*,d^*$ 处）⇒ **残差 0，梯度贡献 0**，但 Hessian 里仍有这一项的曲率 ⇒ Stage II 不会把位姿从 $G^*$ 拉走，也不会给该像素的逆深度塞进一个"相机运动解释不了"的值。

## 4 · 工程视角

| 项 | 论文报告值 | 备注 |
|---|---|---|
| 硬件 | 单张 **NVIDIA RTX 4090** GPU + **96 核** CPU | §IV-E 原文 |
| FPS · Bonn | DynaMoN 2.4 / WildGS-SLAM 0.3 / DROID-W 12.2 / **Ours 11.5** | Table IV |
| FPS · TUM | DynaMoN 2.3 / WildGS-SLAM 0.3 / DROID-W 14.4 / **Ours 13.0** | Table IV |
| 单帧延迟 | 由 FPS 反算：Bonn $\approx$ 87 ms、TUM $\approx$ 77 ms（**本文推导值，非论文原值**） | 论文只给 FPS |
| 计时口径 | "The reported tracking time includes monocular depth estimation and DINOv2 feature extraction" | ⇒ Metric3D + DINOv2 前向**在预算内** |
| 额外开销 | "modest additional cost" 来自 Stage I 的 pose-only solve + 两次 re-anchoring 检验 | 定性，**未给增量毫秒数** |
| 显存 / VRAM | **论文未报告** | — |
| 嵌入端（Jetson 级）实测 | **论文未报告** | — |
| 网络参数量 | **论文未报告** | — |

**Trade-off 读数**：
1. **相对 DROID-W 的代价**：Bonn 12.2→11.5（$-0.7$ FPS，约 $-5.7\%$），TUM 14.4→13.0（$-1.4$ FPS，约 $-9.7\%$）。换来的是 Bonn ATE 2.23→2.06、TUM 1.37→1.32。这属于"用不到 10% 吞吐换精度"的经典取舍。
2. **相对 WildGS-SLAM**：0.3 FPS vs 11.5/13.0 FPS ≈ **38–43 倍**——这是"要不要跑渲染"的结构性差异，不是调参能补的。
3. **Stage I 为什么便宜**：$\Delta\mathbf d\equiv0$ 把正常方程从 $(\mathbf{B},\mathbf C,\mathbf E)$ 的联合块降成 $\mathbf B\Delta\bm\xi=\mathbf v$，只解 $6|\mathcal V|$ 维；贵的不是它，是三个冻结网络的前向。
4. **Stage II 的 $\hat{\mathbf{p}}_{ij}$ 只算一次并固定**（式 11 后："computed once and then remains fixed"）⇒ 迭代数增加不增加重投影计算，但见 §8 Pitfall C 的代价。

## 5 · 数据与评测

**数据集（逐字来自 §IV）**：
- **Bonn RGB-D Dynamic dataset** — 评估动态前景干扰下的定位鲁棒性（9 个序列：Bal. / Bal.2 / Cro. / Cro.2 / Cro.3 / Per. / Per.2 / Mov. / Mov.2）。
- **TUM RGB-D** 的**动态序列** — 定位鲁棒性（f2/dp, f3/ss, f3/sx, f3/sr, f3/shs, f3/ws, f3/wx, f3/wr, f3/whs）。
- **DAVIS** — 提供运动物体的**像素级标注**，用于评动态掩码（按 Animals / Pedestrians / Human Motion / Wheeled and Board Devices / Vehicles 五类划分）。

**指标**：
- **ATE RMSE [cm]**，在 $\mathrm{Sim}(3)$ 对齐之后（轨迹指标口径，必须说明）。
- **FPS**。
- **DM-IoU**（本文提出）：$\mathrm{DM\text{-}IoU}=\dfrac{|\widehat{\mathcal M}_{\mathrm{dyn}}\cap\mathcal M^{\mathrm{gt}}_{\mathrm{dyn}}|}{|\widehat{\mathcal M}_{\mathrm{dyn}}\cup\mathcal M^{\mathrm{gt}}_{\mathrm{dyn}}|}$，强调"既要覆盖完整也要背景污染低"。

**DM-IoU on DAVIS（Table I，逐字）**

| 类别 | MonST3R | WildGS SLAM | DROID W | **Ours** |
|---|---|---|---|---|
| Animals (mean) | 0.13 | 0.21 | 0.73 | 0.72 |
| Pedestrians (mean) | 0.57 | 0.27 | 0.51 | **0.71** |
| Human Motion (mean) | 0.54 | 0.46 | 0.49 | **0.72** |
| Wheeled/Board (mean) | 0.58 | 0.60 | 0.57 | **0.71** |
| Vehicles (mean) | 0.48 | 0.25 | 0.40 | **0.78** |
| **Overall Mean** | 0.46 | 0.36 | 0.54 | **0.73** |

> 摘要/结论的"35% 提升"对应 0.73 vs 0.54（DROID-W，state-of-the-art baseline）；注意 **Animals 类（0.72 vs 0.73）并非最好**，优势集中在 Pedestrians / Human Motion / Vehicles。

**相机跟踪 ATE RMSE [cm]（Table II，摘录平均值）**

| 方法 | Bonn Avg. | TUM Avg. | 输入 |
|---|---|---|---|
| DynaSLAM(N+G) | 6.04 | 1.69 | RGB-D |
| Flow4DGS | 4.33 | – | — |
| MonST3R | 7.50 | 19.44 | RGB-only |
| DROID-SLAM | 5.08 | 1.62 | RGB-only |
| DynaMoN | 3.96 | 1.63 | RGB-only |
| WildGS | 2.44 | 1.52 | RGB-only |
| DROID-W | 2.23 | 1.37 | RGB-only |
| **Ours** | **2.06** | **1.32** | RGB-only |

- "reduces the average ATE by 59% on Bonn and 19% on TUM relative to the SLAM backbone"：$5.08\to2.06$、$1.62\to1.32$（相对 DROID-SLAM）。
- Fig.1 caption 另给出：在 Bonn 序列上相比 NGD-SLAM 与 DROID-W 分别降低 ATE **63.9%** 与 **38.3%**（单序列口径，与表格平均值不可混用）。
- 论文说明：部分 baseline 单序列数值取自 DROID-W，其余为自行运行（"The remaining reported baseline results are obtained from our own runs"）——**复现口径不完全统一**，读表需注意。

**Ablation（Table III，Bonn 九序列，ATE RMSE [cm]，逐字）**

| 配置 | ATE |
|---|---|
| a. w/o uncertainty in BA | 3.62 |
| b. w/o re-anchoring conditions | 2.37 |
| c. w/o two-stage optimization | 2.29 |
| d. w/o dynamic-pixel re-anchoring | 2.23 |
| e. w/ DROID-W uncertainty estimator | 2.16 |
| **Full (Ours)** | **2.06** |

读法：**"不确定性进不进 BA"是最大头**（3.62）；把不确定性估计器换成 DROID-W 的（e，保留两阶段+条件重锚定）只掉到 2.16 ⇒ **两阶段优化本身贡献了相当一部分，且与估计器解耦**——这是本文方法论的强证据。

**下游任务影响（§IV-B，定性 + 统一下游管线）**：跟踪用 Mask R-CNN + Hungarian 匹配；重建用单目深度反投影分层。结论为定性描述（Fig. 4/5）：DROID-W 会在静止桌椅/显示器上产生虚假轨迹、并在人身上断轨；本文掩码保持运动人的稳定 ID、减少背景污染。**该节未给量化指标数字。**

## 6 · 能力与失败模式

**能做**：
- **类别无关**的动态识别：DAVIS 上覆盖 Animals / Vehicles / 非刚性人体运动（语义先验方法的结构性盲区）。
- **纯单目 RGB** 下优于 RGB-D 的 DynaSLAM(N+G)（Bonn 2.06 vs 6.04）。
- 输出**空间连贯、边界更锐利**的像素级掩码（Fig. 3 定性）。
- 在 GPU 上维持 **>10 FPS**（11.5 / 13.0）。
- **条件不满足时优雅退化**：两个 re-anchoring 检验未通过则 Stage II 保留原始目标，不引入比两阶段更差的结果（论文明确表述：re-anchoring is disabled 时 "the tracker preserves the two-stage accuracy without degradation"）。

**不能做 / 会失效**：
1. **动态物体占据画面主体**：$\mathcal{S}_i$ 取的是**相对分位数**，最低分位里仍可能混入运动像素 ⇒ $G^*$ 有偏；而"Re-anchoring inherits all errors in $\mathbf{G}^{*}$" ⇒ 偏差被原样继承。
2. **$\bar r$ 中位数假设被破坏**："When static pixels account for a substantial proportion of the residual samples, the median can indicate background alignment." —— 反过来说，静态像素不占多数时，中位数反映的是**运动物体的对齐程度**，$\beta$ 判据失真。
3. **深度方向的运动残差**："these residuals decompose into an epipolar component, absorbed by the inverse depth of the pixel"。**沿极线方向的运动分量会被该像素自己的逆深度吃掉**（深度被写坏），且通过 $\mathbf{E}$ 耦合污染其它基线的位姿 ⇒ 深度图在这些区域不可信（论文只承诺"减少影响"，不承诺"消除"）。
4. **长时序漂移**：无回环检测；re-anchoring 的"corrections with consistent directions accumulate along the trajectory"，因此在线阶段**关闭**重锚定，只在"final global adjustment"启用 ⇒ 在线轨迹仍带系统性方向偏差。
5. **依赖 DINOv2 语义可分性**：$\mathcal{L}_{sim}$ 与 $h_{\bm\theta}$ 的输入都是 DINOv2 特征；弱纹理/语义混杂区域的特征一致性本身不可靠（这是它批评 DROID-W 的点，但自己也用了同一特征源作补充项）。
6. **依赖 Metric3D 先验的有效域**：深度正则 $\lambda_d\|\mathbf d-\hat{\mathbf d}\|^2$ 把先验当锚；先验失效（尺度/域外场景）时，尺度锚定与重锚定的 $\mathbf{d}^*$ 一并不可靠。论文未报告域外泛化实验。

### 隐含假设 (Hidden Assumptions)

| # | 隐含假设 | 在哪暴露 | 破坏后果 |
|---|---|---|---|
| H1 | **静态背景在像素数上占多数**（窗口内 $\bar r$ 中位数 ≈ 背景对齐水平） | 式 8 及正文对 median 的解释 | $\beta$ 判据反转 → 掩码漏检或误检 |
| H2 | **帧间位移小到"光流 ≈ 对应目标"** | $\mathbf r_{ij}=\mathbf p^*_{ij}-\mathbf p_{ij}$ 直接相减（式 5） | 大位移/快速运动时残差含匹配误差，误判为运动 |
| H3 | **场景主要刚体 + 相机运动可解释背景**（除运动物体外） | 式 2 的残差假设 | 非刚体背景（水面/窗帘）、卷帘快门 ⇒ 假动态 |
| H4 | **最低分位像素里基本没有运动像素** | Stage I 的 $\mathcal{S}_i$ 定义 | 见失败模式 1，$G^*$ 有偏且被继承 |
| H5 | **单目尺度可由 Metric3D 先验锚定** | 式 2 第二项、$\mathrm{Sim}(3)$ 对齐评 ATE | 跨域场景尺度漂移 |
| H6 | **DINOv2 特征在该场景有判别力** | $h_{\bm\theta}$ 输入、$\mathcal{L}_{sim}$ | 弱纹理走廊/强反光失效 |
| H7 | **在线轨迹的 re-anchoring 修正方向一致才启用**（warm-up 判定） | §III-D "Conditions for Re-Anchoring" | 方向不一致时永不启用 ⇒ 退化为 DROID-W 式降权 |

## 7 · 与相关工作对比

| 方法 | 动态线索 | 线索性质 | 优化中怎么用 | 输入 | Bonn ATE | TUM ATE | DAVIS DM-IoU |
|---|---|---|---|---|---|---|---|
| DynaSLAM(N+G) | Mask R-CNN 语义 + 多视图重投影一致性 | 类别先验 | 直接剔除动态区 | RGB-D | 6.04 | 1.69 | – |
| DynaMoN(MS&SS) | 分割 + 自监督 | 类别先验 | 剔除 | RGB-only | 3.96 | 1.63 | – |
| MonST3R | 前馈 4D 重建 | 几何先验 | 非 SLAM 式优化 | RGB-only | 7.50 | 19.44 | 0.46 |
| DROID-SLAM | 无 | — | 无 | RGB-only | 5.08 | 1.62 | – |
| WildGS-SLAM | DINOv2 特征 → MLP，渲染残差在线监督 | **外观/重建**（间接） | BA 逐像素降权 | RGB-only(NeRF/GS) | 2.44 | 1.52 | 0.36 |
| DROID-W | 多视图特征不一致性 | **外观**（间接） | BA 逐像素降权 | RGB-only | 2.23 | 1.37 | 0.54 |
| **FLoTS-SLAM** | **光流 − 相机诱导流残差**（+ DINOv2 一致性作补充） | **运动**（直接） | **分位选择 + 目标替换（re-anchor）** | RGB-only | **2.06** | **1.32** | **0.73** |

**差异一句话总结**：WildGS-SLAM / DROID-W 的差别只在"不确定性从哪来"；FLoTS 同时改了**从哪来**（流残差）和**怎么用**（选择 + 重锚定，而非加权）。Ablation 的 e 行（换成 DROID-W 估计器仍得 2.16）正是"改怎么用"独立有效的证据。

> **面试 Tip（被问到"这跟 DROID-W 到底差在哪"怎么答）**：
> "两点，缺一不可。**第一，证据类型**：DROID-W 用多视图特征不一致性，本质是外观线索，弱纹理或语义复杂的静态结构会假阳性；FLoTS 用的是光流减相机诱导流，这是**相机+深度解释不了的位移**，是运动的直接度量，而且光流直接复用 tracker 已有的对应预测，不额外跑光流网络。**第二，用法**：DROID-W 只是在 BA 里降权，但运动残差是系统性偏移、不是零均值噪声，最小二乘压不住，而且它仍在同时更新共享位姿和该像素深度；FLoTS 先用低不确定像素冻结深度解一个参考位姿，再用这个位姿把高不确定像素的**匹配目标本身**换成'场景静止时它该在的位置'——残差在参考状态处恒等于零，梯度贡献被切除，只剩 Hessian 曲率。消融也印证了：把估计器换成 DROID-W 的，仍能拿到 2.16，说明两阶段本身就有独立收益；反过来去掉重锚定就从 2.06 掉到 2.23。"

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-19)

**repo 状态核实**：全文（含首页、摘要、结论）**未出现任何 `github.com` 链接**，仅在 Abstract 与 Contributions 中写 "The source code will be made publicly available." 与 "We will make the source code publicly available to facilitate future research."。按判定规则，**这是"无 repo 信号"**——不存在可 clickable 校验的仓库，因此也没有 issue 流可引。

> ⚠️ 声明：以下 pitfall **全部由 §6 失败模式 + 本文方法的具体约束推导**，**未经任何 issue 验证**，不含 repo URL / commit / issue 编号。

**Pitfall A —— "最低分位"是相对量：全动态视野下 Stage I 位姿被污染，且误差被重锚定原样继承**
- 来源失败模式：§6-1。
- 方法约束：$\mathcal{S}_i$ 定义为 "the set of pixels whose uncertainty falls in the **lowest quantile** of $\bm\sigma_i$"；Stage I 用 $\mathbf G^*$ 输出的 $\hat{\mathbf p}_{ij}$ 是**唯一**的重锚定目标（式 11，算一次后固定）。
- 推导：分位数是**帧内相对排序**，不是绝对阈值 ⇒ 当画面主体在动（相机被载具携行、大卡车近距占屏），"最低分位"里仍有大量运动像素 ⇒ Stage I 的 $\mathbf{G}^*$ 带系统性偏差 ⇒ 论文自述 "Re-anchoring inherits all errors in $\mathbf{G}^{*}$" ⇒ 偏差被写进**所有** $\mathcal{D}_i$ 像素的目标。
- 落地建议：监控 re-anchoring 条件一的"$\mathcal{D}_i$ 与 $\mathcal{S}_i$ 的 discrepancy 对比度"，把它当**动态占比告警**；对比度弱时按论文行为会关闭重锚定——此时应视为退化到 Stage I 精度，而非仍期待 2.06 cm。

**Pitfall B —— $\bar r$ 用中位数：静态像素不占多数时 $\beta$ 判据反转**
- 来源失败模式：§6-2。
- 方法约束：$\bar r$ = "the **median** of $r_{ij}(\mathbf{u})$ over **all pixels** in the current optimization window"，$\beta=\mathrm{sigmoid}(\tau_r-\bar r)$；论文自述 median 仅在 "static pixels account for a substantial proportion of the residual samples" 时才代表背景对齐。
- 推导：若运动像素占多数，$\bar r$ 被拉高 ⇒ $\beta\to0$ ⇒ $\psi$ 走对数分支（§3 演示：$r=8$ 的权重从 0.024 抬到 0.081）⇒ **运动像素被保留**，动态残差进入 BA，同时静态像素也可能因压缩而失去判别力。反之在极干净的静态窗口里 $\bar r$ 很小 ⇒ $\beta\to1$ ⇒ $r^2$ 生效 ⇒ 微小的匹配噪声也被判为运动。
- 落地建议：不要把 $\tau_r$ 当通用常数。需要按场景标定，或把 $\bar r$ 换成**均值 + 截断**、或按 uncertainty 分位加权的中位数；至少要在部署序列上打印 $\bar r$ / $\beta$ 的时间曲线作为 sanity check。

**Pitfall C —— 重锚定目标是"一次性固定"的：Stage II 的迭代预算直接决定精度，Hessian 会把解锚在 $\mathbf G^*$ 上**
- 来源失败模式：§6-1 / §6-4 的耦合。
- 方法约束：$\hat{\mathbf p}_{ij}$ "is computed once and then remains fixed throughout Stage II"（式 11 后）；同时 "the re-anchored residual term still contributes to the approximate Hessian blocks $\mathbf{B}$, $\mathbf{E}$, and $\mathbf{C}$, retaining a local quadratic constraint around the reference state"。
- 推导：残差在 $(\mathbf G^*,\mathbf d^*)$ 处为 0 ⇒ 线性化点梯度为 0；但二次项仍在 ⇒ Stage II 的解被**二次约束钉在 $\mathbf G^*$ 邻域**。GN 迭代越少、越接近"只解一次线性系统"，最终解就越接近 $\mathbf G^*$。⇒ 同一份代码在**限制迭代数/降频**（嵌入式、或多帧并行抢 GPU）时精度会显著下滑，且下滑不是平滑的。另：$\mathbf d^*$ 是 Stage I **冻结**的深度，若它在 Stage I 之后本应被修正，重锚定会沿用旧深度生成目标。
- 落地建议：把 Stage II 的 GN 迭代数作为**一等超参**做敏感性扫；若为实时性减迭代，必须重测 ATE，不能沿用论文 2.06 cm 的预期。同时输出"Stage I 位姿 vs Stage II 收敛位姿"的偏移量作为健康指标——偏移被压制到近零即说明解已被 $\mathbf G^*$ 主导。

**Pitfall D（论文层，非代码层）—— 表格编号与消融描述不一致，复现时先对表**
- §IV-D 正文写 "We ablate each component on nine Bonn sequences and report the results in **Table IV**"，但 Table IV 的 caption 是 "**Runtime comparison** in frames per second"，消融数值实际在 **Table III**。
- 这属于排版错误而非机制缺陷，但会直接导致"照正文找表"的复现者拿错数据。落地时以 **Table III = Ablation / Table IV = Runtime** 为准。

---

[← Back to VSLAM README](./README.md)

> **Status**：v0.1 · 基于 arXiv:2610.23496v1 全文（已截断版本）· 未在真机复现的数字标 `UNVERIFIED`（§4 中由 FPS 反算的单帧延迟为本文推导值，非论文原值；$g(\sigma)$ 的具体形式与 $\tau_r,\lambda_d,\lambda_{sim},\lambda_{flow}$ 的取值论文未报告）

[//]: # "<!-- source: https://arxiv.org/abs/2610.23496 -->"
