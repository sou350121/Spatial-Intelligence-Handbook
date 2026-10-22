[//]: # "<!-- ontology-5axis
problem: pose
representation: HD-map
sensor: mono
paradigm: geometric
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 无DSM的无人机视觉定位：潜在深度变量投影与结构自适应耦合 (DSM-Free UAV Visual Localization via Latent-Depth Variable Projection and Structure-Adaptive Coupling)

> **发布时间**：2026-10-10（arXiv:2610.14945v1 [cs.CV]，10 Oct 2026）
> **论文 / 模型名**：LDVP（Latent-Depth Variable Projection）+ SAC（Structure-Adaptive Coupling）
> **核心定位**：在**没有 DSM 高程**、只有 2D 正射参考图的条件下，直接解出**米制水平位姿**；比 OPE / AH 这类 OPG 方法更强，并把与 DSM-based 定位的差距显著缩小。

低空 UAV 视觉定位通常靠“正射图 + DSM 抬升 2D–3D 对应 + PnP”来获得绝对位置，但米级分辨率的 DSM 往往拿不到或已过期（例如 AW3D30 约 30 m，文中明确对比“参考图通常是米级或更细”）。LDVP 的做法是：把每条透视射线的未知尺度当作 **latent depth 解析消掉**，让非线性优化只剩旋转；SAC 再用单目深度的**相对**结构在 LDVP 与 Planar-PnP 之间切换。

---

## X-Ray 开场

论文要解决的是“**没有 DSM 也要拿到米制水平位置**”这个约束下的几何估计问题。它的关键做法是把 orthographic–perspective geometry（OPG）从“估中间矩阵再分解”改写成“**消掉每条射线的未知深度 λ_i，直接以位姿为变量**”：消元后残差退化成米制的点到线距离，水平中心在给定旋转下是 2 维线性最小二乘，非线性只剩 SO(3)。对 spatial AI 研究者而言，这意味着 **OPG 的退化结构（近平面场景下 tilt 与水平平移一阶耦合）是所有 OPG 参数化共有的**（附录证明 LDVP / OPE / AH 的 Jacobian nullspace 相同），因此“换参数化”不能解决退化，只能“换求解器 / 换场景假设”——这正是 SAC 的立论基础。

---

## 📍 研究全景时间线

```
时间轴（年份以论文正文可查者为准，其余仅表先后顺序）
────────────────────────────────────────────────────────────────────────────
[手工特征期]  SIFT / SURF / ORB  →  中等视角变化下的匹配
      │
[学习特征期]  SuperPoint / LightGlue / DISK / ALIKED   ← 本文的匹配器候选
      │       LoFTR / DKM / RoMa（dense，本文默认 RoMa）
      │
[DSM-based]   2D–3D lifting by DSM + PnP-RANSAC  ← 本文的“上界参照” DSM-PnP
      │       + 重力约束 / 惯性姿态先验 / AeroMap3D(bare-earth DEM + OSM)
      │       ✗ 痛点：DSM 分辨率粗、更新滞后
      │
[Planar 分支] Homography / Planar-PnP（统一零高程）  ← 本文的对照 + SAC 的备选
      │       ✗ 痛点：matched points 跨高程时失效
      │
[OPG 分支]    OPE（Larsson et al.，最小解 essential matrix）
      │       AH（Li et al.，Antisymmetric-Homography）
      │       ✗ 痛点：经中间矩阵估计再分解，非直接度量位姿；未处理近平面退化
      │
[MDE 辅助]    depth-aware homography / DECO（用单目深度做几何过滤）
      │       ✗ 空白：单目深度只用于匹配/过滤，未用于“求解器选择”
      │
   ►► [本文 2026-10] LDVP + SAC ◄◄
        · 变量投影消 λ_i → 非线性只剩 rotation，c 闭式/2 维鲁棒回归
        · 局部可观测性分析：高程变化恢复 tilt 约束
        · SAC：用 MDE 的“相对结构”在 LDVP / Planar-PnP 间切换（不做度量高程）
      │
[本文局限]  · 只评测水平位置 e_pos，未报告高度 / 旋转精度
            · 中间起伏带（2–10 m）分支选择一致性下降
            · 近平面场景仍退化（几何固有，非实现问题）
            · 无开源代码、无运行时/资源报告
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| 图像匹配器（RoMa 默认；消融用 SuperPoint+LightGlue、DISK+LightGlue、ALIKED+LightGlue） | UAV 透视图 $\mathbf{I}_u$、正射参考图 $\mathbf{I}_r$ | 对应点集 $\mathcal{M}=\{(\mathbf{p}_i,\mathbf{y}_i)\}_{i=1}^{N}$ | 论文未训练任何网络，直接使用现成匹配器；本文无训练阶段 |
| 地理配准变换 $\mathcal{G}(\cdot)$ | 参考图像素 $\mathbf{y}_i$ | 米制水平坐标 $\mathbf{m}_i=[X_i,Y_i]^\top$ | 无需学习；**高程 $Z_i$ 未知**（这是全文前提） |
| 单目深度 $\mathcal{F}_{\mathrm{MDE}}$（MoGe2-Aerial 默认；消融 MoGe2、Depth Anything 3） | $\mathbf{I}_u$ | $\widehat{\mathbf{D}}$ | 仅用于**相对结构**判断，**不当度量高程**用（论文反复强调） |
| SAC 平面支持率 | 反投影点 $\widehat{\mathbf{X}}_i$（按 $\widehat{d}_{\mathrm{med}}$ 归一化） | $S_1=N_1/N_{\mathrm{valid}}$ | 无学习；three-point RANSAC，2000 次迭代，$\tau_\pi=0.003$ |
| LDVP 求解器 | $\mathcal{M}$、$\mathbf{K}$、$\mathbf{R}$ | 米制水平中心 $\mathbf{c}^*(\mathbf{R}^*)$ | 5 点最小集 + MSAC；$\tau_L=5$ m 点到线阈值 |
| Planar-PnP 分支 | $\mathbf{P}_i^\pi=[X_i,Y_i,0]^\top$ | 位姿（零高程虚拟平面） | IPPE-based RANSAC（OpenCV） |
| DSM-PnP（仅对照，非本方法） | DSM 抬升的 2D–3D 对应 | 位姿 | P3P-based RANSAC；**只有它用到 DSM** |

> 全流程为 **feed-forward、免训练、几何求解**：一次前向 = 匹配 + 一次 MDE + 一次平面拟合 + 一个 PnP/LDVP 求解。

### 1.2 关键机制

**⚡ Eureka Moment**：*每条透视射线的未知尺度 $\lambda_i$ 不是必须估计的状态，而是可以像“讨厌参数（nuisance parameter）”一样被解析消掉的——消掉之后剩下的就是米制点到线残差，水平中心在给定旋转下有闭式解，于是“DSM-free 位姿估计”从 5+N 维非线性问题塌缩成 3 维旋转搜索。*

三个配套机制：

1. **变量投影（Variable Projection）**：$\min_{\lambda_i}\|\mathbf{m}_i-\mathbf{c}-\lambda_i\mathbf{q}_i\|_2^2=e_i^2$ —— 消元是**精确恒等**（附录 B 用投影矩阵 $\mathbf{I}_2-\mathbf{q}_i\mathbf{q}_i^\top/\mathbf{q}_i^\top\mathbf{q}_i=\mathbf{n}_i\mathbf{n}_i^\top$ 证明），不是代数近似。
2. **可观测性分析**：近平面时 $\mathbf{J}_{\omega_x}=-H\mathbf{J}_{C_y}$、$\mathbf{J}_{\omega_y}=H\mathbf{J}_{C_x}$，tilt 与水平平移**一阶耦合**；高程差 $\Delta h_i$ 打破耦合。并证明 OPE/AH 的 Jacobian 只是 LDVP 的**非奇异对角缩放**，故 nullspace 相同 → 退化是几何固有。
3. **SAC**：既然退化随场景起伏变化，就用 MDE 的**相对**平面支持率 $S_1$ 做 0/1 分支（$S_1<0.5$ → LDVP，否则 Planar-PnP）。

### 1.3 信息流

```
UAV 透视图 I_u ──┬─→ [Matcher: RoMa] ──┐
                 │                     ├─→ M = {(p_i, y_i)}
正射参考图 I_r ───┴─────────────────────┘        │
                                                 │ G(·) 地理配准（只给 X,Y，无 Z）
                                                 ▼
                                        m_i = [X_i, Y_i]^T
                                                 │
   ┌─────────────────────────────────────────────┤
   │                                             │
   ▼                                             ▼
[MDE: MoGe2-Aerial]                        [LDVP 求解]
   │  D̂                                       1) 由 R 得 q_i(R) = 世界系水平射线
   │  X̂_i = d̂(p_i)K⁻¹p̃_i                      2) RANSAC 5 点最小集 → 旋转候选
   │  X̃_i = X̂_i / d̂_med                       3) 消 λ_i：e_i = n_iᵀ(m_i − c)
   │  3-pt RANSAC 拟合主平面                    4) 内层：c 的 2 维鲁棒回归（闭式/鲁棒）
   │  S_1 = N_1 / N_valid                      5) 外层：SO(3) 旋转最小化 Σρ(e_i)
   ▼                                            6) MSAC 打分（τ_L = 5 m）+ 精化
 S_1 < τ_S (=0.5) ?
   │是 ──────────────→ LDVP ────────────────→ 位姿 (R, c)
   │否 ──→ [Planar-PnP] P_i^π=[X_i,Y_i,0]ᵀ → IPPE-RANSAC → 位姿 (R, c)
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$\min_{\mathbf{R}\in SO(3)}\sum_{i=1}^{N}\rho\Big(\mathbf{n}_i(\mathbf{R})^\top\big(\mathbf{m}_i-\mathbf{c}^*(\mathbf{R})\big)\Big),\qquad \mathbf{n}_i=\frac{1}{\|\mathbf{q}_i\|}\begin{bmatrix}-q_{iy}\\ q_{ix}\end{bmatrix}$$

一句话直觉：**把“未知深度”投影掉，每条对应就只剩一条过相机的水平直线约束；N 条线交于一点就是相机水平位置，剩下的自由度只有姿态。**

### 2.1 问题形式化（目标）

已知：$\mathbf{K}$、重力对齐世界系、$\mathcal{M}=\{(\mathbf{p}_i,\mathbf{y}_i)\}$、$\mathbf{m}_i=[X_i,Y_i]^\top$（$Z_i$ 未知）。
未知：世界到相机旋转 $\mathbf{R}\in SO(3)$、相机中心 $\mathbf{C}=[C_x,C_y,C_z]^\top$。

相机坐标系单位视线：$\mathbf{r}_i=\dfrac{\mathbf{K}^{-1}\widetilde{\mathbf{p}}_i}{\|\mathbf{K}^{-1}\widetilde{\mathbf{p}}_i\|_2}$。
世界系视线：$\mathbf{R}^\top\mathbf{r}_i=[\mathbf{q}_i^\top\ \ v_{iz}]^\top$，$\mathbf{q}_i=[q_{ix}\ q_{iy}]^\top$。

场景点落在射线上：$[X_i\ Y_i\ Z_i]^\top=\mathbf{C}+\lambda_i\mathbf{R}^\top\mathbf{r}_i,\ \lambda_i>0$。
取水平分量：

$$\boxed{\ \mathbf{m}_i=\mathbf{c}+\lambda_i\,\mathbf{q}_i(\mathbf{R})\ }\tag{Eq.6}$$

| 变量 | 含义 |
|---|---|
| $\mathbf{c}=[C_x,C_y]^\top$ | 待求的**米制水平**相机中心（仅 2 维！） |
| $\mathbf{q}_i(\mathbf{R})$ | 世界系下第 $i$ 条射线的**水平方向**（依赖旋转） |
| $\lambda_i$ | 第 $i$ 条射线的 latent depth（未知尺度） |
| $C_z$ | 竖向位置——注意 Eq.6 中**完全未出现** |

### 2.2 消去 $\lambda_i$

最小化 $\|\mathbf{d}_i-\lambda_i\mathbf{q}_i\|_2^2$（$\mathbf{d}_i=\mathbf{m}_i-\mathbf{c}$），求导置零：

$$\lambda_i^\ast=\frac{\mathbf{q}_i^\top(\mathbf{m}_i-\mathbf{c})}{\mathbf{q}_i^\top\mathbf{q}_i}\tag{Eq.9}$$

代回并引入单位线法向 $\mathbf{n}_i(\mathbf{R})=\frac{1}{\|\mathbf{q}_i\|_2}[-q_{iy}\ \ q_{ix}]^\top$：

$$e_i(\mathbf{R},\mathbf{c})=\mathbf{n}_i^\top(\mathbf{m}_i-\mathbf{c}),\qquad \min_{\lambda_i\in\mathbb{R}}\|\mathbf{m}_i-\mathbf{c}-\lambda_i\mathbf{q}_i\|_2^2=e_i^2\tag{Eq.11-12}$$

**直觉**：$\lambda_i$ 描述“点沿射线走多远”，它完全不影响点到**线**的距离；所以深度信息对“点—线一致性”是冗余的。

### 2.3 双层 profile

内层（给定 $\mathbf{R}$，对 $\mathbf{c}$ **仿射** ⇒ 只是 2 维鲁棒回归）：

$$\mathbf{c}^\ast(\mathbf{R})=\arg\min_{\mathbf{c}}\sum_i\rho\big(e_i(\mathbf{R},\mathbf{c})\big)\tag{Eq.13}$$

平方损失下有闭式解（附录 B）：记 $\mathbf{N}=[\mathbf{n}_1^\top;\dots;\mathbf{n}_N^\top]$、$\mathbf{b}=[\mathbf{n}_1^\top\mathbf{m}_1;\dots;\mathbf{n}_N^\top\mathbf{m}_N]$，若 $\operatorname{rank}(\mathbf{N})=2$ 则

$$\mathbf{c}^\ast(\mathbf{R})=(\mathbf{N}^\top\mathbf{N})^{-1}\mathbf{N}^\top\mathbf{b}\tag{Eq.60}$$

外层（**只剩旋转**）：

$$\mathbf{R}^\ast=\arg\min_{\mathbf{R}\in SO(3)}\sum_i\rho\big(e_i(\mathbf{R},\mathbf{c}^\ast(\mathbf{R}))\big)\tag{Eq.14}$$

鲁棒化：5 点假设 + MSAC，$E_{\mathrm{MSAC}}=\sum_i\min(e_i^2,\tau_L^2)$，并**先验丢弃**正深度($\lambda_i^\ast>0$)支持不足的假设。
自由度计数（附录 C）：$2N\ge N+5\Rightarrow N\ge 5$。

### 2.4 与 OPE / AH 的等价（本文最锋利的一刀）

$$\mathbf{E}_{\mathrm{AH}}=-\mathbf{E}_{\mathrm{OP}}^\top,\qquad \mathbf{r}_i^\top\mathbf{E}_{\mathrm{AH}}\overline{\mathbf{m}}_i=-\overline{\mathbf{m}}_i^\top\mathbf{E}_{\mathrm{OP}}\mathbf{r}_i=-\|\mathbf{q}_i\|_2\,e_i\tag{Eq.20-21}$$

⇒ 三者是**同一无噪声约束的不同参数化**，只在“是否显式保留 $\mathbf{c}$、是否要估中间矩阵”上不同。

### 2.5 SAC 判据

$$\widehat{\mathbf{X}}_i=\widehat{d}(\mathbf{p}_i)\mathbf{K}^{-1}\widetilde{\mathbf{p}}_i,\quad \widetilde{\mathbf{X}}_i=\frac{\widehat{\mathbf{X}}_i}{\widehat{d}_{\mathrm{med}}},\quad \bar r_i^\pi=\big|\widehat{\mathbf{n}}_\pi^\top\widetilde{\mathbf{X}}_i+b_\pi\big|<\tau_\pi,\quad S_1=\frac{N_1}{N_{\mathrm{valid}}}$$

$$\mathcal{B}=\begin{cases}\mathrm{L\ (LDVP)}, & S_1<\tau_S\\ \mathrm{P\ (Planar\text{-}PnP)}, & S_1\ge\tau_S\end{cases}\qquad \tau_S=0.5$$

**Planar-PnP 分支的零高程技巧**：$\mathbf{P}_i^\pi=[X_i,Y_i,0]^\top$，令 $\mathbf{C}^\pi=\mathbf{C}-Z_\pi\mathbf{e}_z$，则 $[X_i,Y_i,Z_\pi]^\top-\mathbf{C}=\mathbf{P}_i^\pi-\mathbf{C}^\pi$ —— 把平面设为 0 高程只**平移竖直参考**，不改变旋转和水平位置。

---

## 3 · 带数字走一遍（玩具设定，作者自造数字，非论文结果）

设重力对齐世界系，$\mathbf{R}$ 已知（近似下视），于是 $\mathbf{q}_i$ 已知。

**(a) 两条正交射线 → 闭式交点**
- 对应 1：$\mathbf{q}_1=(1,0)$、$\mathbf{m}_1=(5,3)$ ⇒ $\mathbf{n}_1=(0,1)$，$e_1=3-C_y$
- 对应 2：$\mathbf{q}_2=(0,1)$、$\mathbf{m}_2=(4,7)$ ⇒ $\mathbf{n}_2=(-1,0)$，$e_2=C_x-4$

令 $e_1=e_2=0$ ⇒ $\mathbf{c}^\ast=(4,3)$。回代内层：$\lambda_1^\ast=\mathbf{q}_1^\top(\mathbf{m}_1-\mathbf{c}^\ast)=5-4=1>0$，$\lambda_2^\ast=7-3=4>0$，两条射线正深度通过。

这正是附录 B 的 $\mathbf{N}^\top\mathbf{N}=\mathrm{diag}(1,1)$ 情形：**两个方程直接读出两个未知量**，不需要任何迭代。

**(b) 沿射线移动点 → 残差完全不变（latent depth 的可消性）**

把 $\mathbf{m}_1$ 从 $(5,3)$ 挪到 $(100,3)$（同一射线方向、更远）：
$e_1=3-C_y$，与挪动前**逐字相同**。⇒ 深度不可观测，但它根本不需要被观测。

**(c) 第三条点带噪声 → 残差即垂距**

取 $\mathbf{q}_3=(0.7071,0.7071)$、$\mathbf{m}_3=(7,7)$，用 $\mathbf{c}^\ast=(4,3)$：
$\mathbf{n}_3=0.7071\cdot(-0.7071,\ 0.7071)$ 方向（即 $\mathbf{n}_3=(-0.7071,0.7071)$），$\mathbf{m}_3-\mathbf{c}^\ast=(3,4)$，
$e_3=-0.7071\times3+0.7071\times4=0.7071$ —— 即该点到“过 $\mathbf{c}^\ast$、方向 $\mathbf{q}_3$ 的直线”的**米制垂距**。MSAC 用 $\tau_L=5$ m 截断，这条 0.7071 m 显然是 inlier。

**(d) 近平面为什么退化（定性，不给自造数值）**

若所有 $h_i=Z_i-C_z\equiv H$，则 $\mathbf{J}_{\omega_x}=-H\mathbf{J}_{C_y}$、$\mathbf{J}_{\omega_y}=H\mathbf{J}_{C_x}$：**绕 x 轴 tilt 与沿 y 平移产生完全相同的一阶残差变化**。这不是“小量近似”，而是**精确共线**，因此 $\mathbf{c}$ 被 profile 掉之后，这两个旋转方向不提供任何独立约束。而 $\mathbf{c}$ 被 profile 掉这件事在 LDVP 里是**强制的**（内层必解），所以退化在 LDVP 参数化下被放大成“必须靠 $\Delta h_i$ 来救”。

---

## 4 · 工程视角

| 项目 | 论文报告值 |
|---|---|
| 硬件 | NVIDIA GeForce RTX 4090 GPU；Intel Xeon Platinum 8370C CPU |
| 软件栈 | Ubuntu 22.04 / Python 3.10 / PyTorch |
| 单帧延迟 | **论文未报告** |
| FPS / 吞吐 | **论文未报告** |
| 显存 / 内存占用 | **论文未报告** |
| 模型参数量 | **论文未报告** |
| LDVP 最小集 | 5 个对应点（MSAC 内） |
| LDVP 鲁棒阈值 $\tau_L$ | 5 m（米制点到线残差） |
| 旋转初始化 | tilt $30^\circ$、azimuth $45^\circ$、roll $45^\circ$ 的角步长，随后局部旋转细化 |
| SAC 平面拟合 | three-point RANSAC，2000 次迭代，$\tau_\pi=0.003$（无量纲） |
| SAC 阈值 $\tau_S$ | 0.5（主实验）；敏感性扫 0.30 / 0.40 / 0.50 / 0.60 |
| 内点判别额外条件 | $\lambda_i^\ast>0$（正深度） |

**结构性 trade-off（可推导，非编数）**

1. **SAC 的代价是一个 MDE 前向 + 一次 2000 次迭代的 3 点 RANSAC**。相对 LDVP 本身，这是**新增的一条深度网络推理路径**——即“用一个大网络的算力换取几何退化场景的鲁棒性”。论文未量化这笔开销。
2. **LDVP 把非线性压到 3 DoF，但把成本转移到“旋转搜索”**：$30^\circ/45^\circ/45^\circ$ 的网格 + 局部细化意味着外层是非凸搜索，收敛依赖初始化网格覆盖到真值附近的吸引域。这是“降维换来非凸性”的典型交换。
3. **$\tau_L=5$ m 是米制阈值**，与 $A@1$ 这种 1 m 级指标不在同一量级：内点带远比评价精度宽，因此**鲁棒性靠宽阈值买来，精度靠最后的 refit 补**。部署时若把 $\tau_L$ 收紧到米级以内，inlier 数量会掉、5 点假设存活率下降——这是可直接推出的调参陷阱。
4. **Planar-PnP 分支只返回水平位置 + 旋转，不返回有意义的绝对高度**（Eq.33–35 明确“只平移竖直参考”）。若下游要做高度保持/地形跟随，SAC 的另一半分支**不提供 $C_z$**。
5. **整套方法假设重力对齐世界系**，即需要外部重力/姿态先验（IMU 或已对齐的 attitude）。这不是可选项，而是 Eq.4 拆分 $\mathbf{q}_i$ 与 $v_{iz}$ 的前提。

---

## 5 · 数据与评测

### 5.1 数据集（逐字来自正文）

| 数据集 | 规模 / 构成 | 高度、视角 | DSM 分辨率 |
|---|---|---|---|
| **AnyVisLoc** | 20,077 张 UAV 图像，24 个城市与自然场景 | 飞行高度 6–500 m；down-tilt $5^\circ$–$90^\circ$（斜视 + 近下视） | 0.15–1.98 m（使用 aerial reference maps）；参考图旋转/裁剪协议沿用 [40] |
| **OrthoLoC** | 16,427 个样本，51 个地点；其中 10,923 same-domain、5,504 cross-domain | 高度 23–201 m；多数 down-tilt $60^\circ$–$90^\circ$ | 0.04–0.73 m；UAV 图与参考图 yaw 差限制在 $45^\circ$ 内 |

### 5.2 指标与设置

- 水平位置误差 $e_{\mathrm{pos}}=\|\widehat{\mathbf{c}}-\mathbf{c}_{\mathrm{gt}}\|_2$；
- 报告**中位误差**与 $A@\tau$（$\tau\in\{1,3,5\}$ m，误差不超过 $\tau$ 的图像百分比）；
- 所有方法在同一测试实例内**共用同一套 UAV–参考图对应**；DSM 只提供给 DSM-PnP；
- 默认匹配器 RoMa；默认 MDE MoGe2-Aerial；对照：DSM-PnP（P3P-RANSAC）、Planar-PnP（IPPE-RANSAC）、OPE、AH。

### 5.3 主结果（Table I，RoMa 对应；逐字抄录）

| Method | AnyVisLoc A@1 | A@3 | A@5 | Med.(m) | OrthoLoC A@1 | A@3 | A@5 | Med.(m) |
|---|---|---|---|---|---|---|---|---|
| DSM-PnP（用到 DSM，不参与排名） | 82.22 | 96.74 | 97.20 | 0.46 | 72.48 | 84.09 | 86.55 | 0.46 |
| Planar-PnP | 16.50 | 50.72 | 66.17 | 2.93 | 17.49 | 53.66 | 69.64 | 2.72 |
| AH | 28.01 | 54.87 | 64.99 | 2.44 | 19.16 | 35.37 | 41.68 | 11.36 |
| OPE | 41.37 | 70.76 | 80.91 | 1.37 | 36.73 | 59.66 | 69.28 | 1.83 |
| **LDVP (ours)** | 48.59 | 75.41 | 82.87 | 1.05 | 39.89 | 59.28 | 66.23 | 1.69 |
| **LDVP+SAC (ours)** | 51.35 | 81.51 | 88.36 | 0.97 | 39.34 | 62.05 | 70.33 | 1.66 |

阅读要点（诚实标注）：
- 论文正文明确写 “On AnyVisLoc, SAC improves $A@3$ by **6.10 percentage points**”。
- **OrthoLoC 上并非全指标领先 OPE**：LDVP 的 $A@3$ 为 59.28（OPE 59.66）、$A@5$ 为 66.23（OPE 69.28）；LDVP 的优势体现在 $A@1$（39.89 vs 36.73）与 Med.（1.69 vs 1.83）。
- **OrthoLoC 上 SAC 使 $A@1$ 略降**（39.89 → 39.34），论文自述：“$A@1$ decreases slightly … Planar-PnP branch mainly helps reduce larger localization errors”。
- 与 DSM-PnP 的差距仍显著（AnyVisLoc $A@1$ 51.35 vs 82.22；Med. 0.97 vs 0.46）。

### 5.4 合成实验设置

正弦地形 $g(x,y)=\sin(2\pi x/L)\cos(2\pi y/L)$，$L=300$ m；高程归一化为指定 relief $\Delta h$（按 $P_{90}-P_{10}$ 度量），$\Delta h\in\{0,0.25,0.5,1,2,4,8,16,32,64\}$ m；图像 $1024\times768$、焦距 800 px；6 个高度 $\{50,100,150,200,250,300\}$ m × 7 个 down-tilt $\{30^\circ,40^\circ,\dots,90^\circ\}$；每配置重复 3 次、每次 200 个对应；两图均加 $\sigma=1$ px 高斯噪声；相同相机配置/对应布局/噪声实现跨 relief 复用（配对比较）。
结论方向：Planar-PnP 在近平面好、随 relief 增大变差；OPG 族（含 LDVP）随 relief 增大变好；LDVP 在各 relief 上优于 OPE/AH。

### 5.5 消融（逐字抄录）

**SAC 阈值（Table II，$\Delta$ 相对 LDVP，SelP = 选 Planar-PnP 的比例）**

| 数据集 / $\tau_S$ | SelP (%) | $\Delta A@1$ | $\Delta A@3$ | $\Delta A@5$ |
|---|---|---|---|---|
| AnyVisLoc / 0.30 | 33.2 | +0.74 | +6.72 | +6.99 |
| AnyVisLoc / 0.40 | 23.3 | +2.61 | +7.21 | +6.85 |
| AnyVisLoc / 0.50 | 14.9 | +2.76 | +6.10 | +5.49 |
| AnyVisLoc / 0.60 | 8.3 | +1.84 | +3.84 | +3.50 |
| OrthoLoC / 0.30 | 57.02 | −4.87 | +4.72 | +8.59 |
| OrthoLoC / 0.40 | 33.47 | −1.91 | +4.52 | +6.71 |
| OrthoLoC / 0.50 | 17.06 | −0.55 | +2.77 | +4.10 |
| OrthoLoC / 0.60 | 7.10 | −0.09 | +1.25 | +1.85 |

要点：阈值越低 → 越多用 Planar-PnP → $A@3/A@5$ 收益越大，但 OrthoLoC 上 $A@1$ 变差（−4.87）。这是一个**真实的精度—鲁棒性旋钮**，不是单调改进。

**匹配器（Table III 摘要，AnyVisLoc / OrthoLoC 的 $A@1$）**

| 匹配 | DSM-PnP | Planar-PnP | AH | OPE | LDVP | LDVP+SAC |
|---|---|---|---|---|---|---|
| SuperPoint+LightGlue | 41.23 / 49.45 | 7.98 / 9.21 | 8.07 / 10.77 | 6.22 / 13.45 | 17.77 / 23.25 | 20.35 / 23.42 |
| DISK+LightGlue | 57.18 / 42.54 | 9.33 / 5.59 | 9.44 / 5.97 | 11.16 / 12.06 | 25.05 / 19.12 | 28.59 / 19.46 |
| ALIKED+LightGlue | 66.59 / 47.87 | 9.63 / 7.82 | 12.44 / 9.98 | 14.00 / 14.70 | 25.24 / 23.64 | 28.82 / 23.94 |

要点：换成稀疏匹配器后**所有 DSM-free 方法一起崩**（例如 ALIKED+LightGlue、AnyVisLoc 上 LDVP $A@1$ 25.24，而 RoMa 下 48.59；DSM-PnP 66.59）。这提示**瓶颈在对应质量，不在几何求解器**。

**MDE 模型（Table IV）**

| Method | AnyVisLoc A@1 / A@3 / A@5 / Med. | OrthoLoC A@1 / A@3 / A@5 / Med. |
|---|---|---|
| LDVP | 48.59 / 75.41 / 82.87 / 1.05 | 39.89 / 59.28 / 66.23 / 1.69 |
| +SAC (MoGe2-Aerial) | 51.35 / 81.51 / 88.36 / 0.97 | 39.34 / 62.05 / 70.33 / 1.66 |
| +SAC (MoGe2) | 51.19 / 80.92 / 87.87 / 0.97 | 39.72 / 61.62 / 69.57 / 1.64 |
| +SAC (Depth Anything 3) | 51.25 / 81.64 / 88.50 / 0.97 | 38.53 / 62.49 / 71.34 / 1.70 |

论文的结论原文为 “The differences among the three models are relatively small” —— 我不在此另算差值（避免引入原文没有的数字）；三个配置的绝对数值见上表，读者可自行核对。

### 5.6 场景级定性证据（逐字）

- AnyVisLoc Case 1（Scene 07，城市—农田混合）：城市 query $S_1=0.130$，农田 query $S_1=0.707$；图 5(a) Planar-PnP 误差 **9.26 m**；图 5(b) LDVP 误差 **11.7 m** → Planar-PnP **1.00 m**。农田区部分 query 被误路由到 LDVP，导致 “approximately **3.4 percentage-point** decrease in $A@5$ compared with Planar-PnP”。
- AnyVisLoc Case 2（Scene 03，密集城市）：query 顶点高程 **2.5 m 至 73.9 m**，$S_1=0.156$，LDVP 误差 **0.83 m**。

---

## 6 · 能力与失败模式

### 能做（有证据）

- **无 DSM 的米制水平定位**，且在**非平面/高起伏**场景显著优于 Planar-PnP（合成：relief 增大时趋势反转；真实：Case 2 中 Planar-PnP “degrades substantially”）。
- **优于同族 OPG 方法**：AnyVisLoc 上 LDVP $A@1$ 48.59 vs OPE 41.37 / AH 28.01，Med. 1.05 vs 1.37 / 2.44。
- **优势不只依赖 RoMa**：三种稀疏匹配器下 $A@1$ 仍高于 OPE/AH（Table III）。
- **直接输出位姿参数**，不像 OPE/AH 要先估 $\mathbf{E}$ 再分解（避免分解时的多解/尺度处理）。

### 不能做 / 明确短板（有证据或可直接推导）

- **近平面场景几何退化**：论文自述 “LDVP may become less reliable in approximately planar scenes”；且证明退化对 OPE/AH/LDVP **同时成立**（$\mathrm{null}(\mathbf{J}_{\mathrm{OP}})=\mathrm{null}(\mathbf{J}_{\mathrm{AH}})=\mathrm{null}(\mathbf{J}_{\mathrm{LDVP}})$）。换参数化救不了。
- **中间起伏带（2–10 m）分支选择不可靠**：Fig.3(d) 明确写 SAC 选择与“更优求解器”的一致性在 $2$–$10$ m 区间**下降**。
- **均质乡村区域 MDE 结构不可靠**：论文自承 “monocular depth may not always provide sufficiently reliable relative structure for identifying planar queries in relatively homogeneous rural regions”。
- **高度 / 旋转精度未评测**：通篇只有 $e_{\mathrm{pos}}$（水平）；没有 $C_z$ 误差、没有 yaw/roll/pitch 误差指标。
- **对应质量是硬瓶颈**：稀疏匹配器下 $A@1$ 大幅下滑（见 §5.5）。
- **与 DSM-based 仍有明显差距**（AnyVisLoc $A@1$ 51.35 vs 82.22）。

### 隐含假设 (Hidden Assumptions)

1. **重力方向已知**，世界系已与水平面（$X$–$Y$ 平面）对齐。若姿态先验有偏，$v_{iz}$ 会混入水平分量，$\mathbf{q}_i$ 失真。论文未讨论姿态误差敏感性。
2. **参考图是真正射且地理配准 $\mathcal{G}$ 精确**。地图地理配准误差会**一比一**映射为 $e_{\mathrm{pos}}$；论文未给出 $\mathcal{G}$ 的误差预算。
3. **参考图与当前场景在“平面位置”上一致**。DSM-free 只是绕过了高程，**没有绕过**建筑轮廓变化：新建/拆除建筑会改变可行对应，MSAC 只能当外点处理。
4. **$\lambda_i^\ast>0$ 的物理解释成立**：即匹配到的地面/建筑点确实在相机前方。对大幅斜视 + 远处天际线/背景匹配，这条会被违反，导致假设被丢。
5. **主平面假设的“支持率”能代表平面主导性**：$S_1$ 用 MDE 深度反投影算，若 MDE 在弱纹理屋顶/水面/植被上退化，$S_1$ 是噪声而非结构。
6. **$\operatorname{rank}(\mathbf{N})=2$**（附录 B 的闭式解前提）：需要至少两个方向不同的水平射线；若匹配点水平射线近似共向，中心不可解（见 §8）。
7. **对应分布足够“一般”**：5 点最小集只有在非退化配置下才唯一；附录 C 明确写 “it does not guarantee a unique or valid solution for every five-correspondence configuration”。

---

## 7 · 与相关工作对比

| 方法 | 是否需 DSM/高程 | 是否需平面假设 | 位姿获取方式 | 近平面退化是否被处理 | 用 MDE 做什么 |
|---|---|---|---|---|---|
| DSM-PnP（如 AnyVisLoc 基线） | **需要**（0.15–1.98 m / 0.04–0.73 m DSM） | 否 | DSM 抬升 2D–3D + PnP-RANSAC | 不适用 | 不用 |
| 全局 DSM 产品（如 AW3D30，约 30 m） | 需要但精度不足 | 否 | 同上，但高程误差大 | 不适用 | 不用 |
| Planar-PnP / Homography 类 | 不需 | **需要** | 零高程抬升 + IPPE-RANSAC | 不适用（本身就是平面解） | 不用 |
| Sekii et al.（垂直 3D 线，street-view） | 不需 | 否 | 点到线约束 | 未涉及 | 不用 |
| OPE（Larsson et al.） | 不需 | 否 | 估 $\mathbf{E}_{\mathrm{OP}}$ + 分解（最小解） | **未处理** | 不用 |
| AH（Li et al.） | 不需 | 否 | 估 $\mathbf{E}_{\mathrm{AH}}$（反对称单应）+ 分解 | **未处理** | 不用 |
| DECO（MDE 辅助） | 不需 | 否 | 用单目深度做**几何过滤**后再匹配 | 未涉及求解器选择 | 过滤无效 keypoint |
| depth-aware homography（Huang et al.） | 不需 | 部分 | 深度感知单应 | 未涉及 | 修正单应 |
| **本文 LDVP** | **不需** | **不需** | 直接以 $(\mathbf{R},\mathbf{c})$ 为变量；消 $\lambda_i$ + profile $\mathbf{c}$ + 3 DoF 搜索 + MSAC | **分析并承认**（几何固有） | 不用 |
| **本文 LDVP+SAC** | **不需** | **自适应** | 上述 + 分支选择 | **用分支绕开**（非消除） | 只推断**相对**平面支持率 $S_1$ |

定位一句话：**LDVP 在“几何层”不是新几何（与 OPE/AH 等价），而是新参数化（把度量位姿顶到最外层）；SAC 在“系统层”把退化从“不可解”降级为“换个解”。**

**面试 Tip**：如果被问“LDVP 和 OPE/AH 到底差在哪，是不是刷参数化？”，标准答法分三层——①**几何等价**：Eq.21 证明三者残差只差非零尺度与符号，Jacobian nullspace 相同，所以**可观测性完全一致**；②**估计等价性不同**：OPE/AH 先估 3×3 矩阵再分解，噪声下分解会引入投影/约束误差和多解处理，LDVP 直接在位姿空间最小化，且 $\mathbf{c}$ 在给定 $\mathbf{R}$ 下是 2 维线性问题有闭式解，**变量数从 9 降到 3**；③**系统层面**：正因为几何退化不可通过参数化修复，才必须引入 SAC 这种“按场景结构换求解器”的机制——这才是本文相对 OPE/AH 的真正增量。

---

## 8 · GitHub-validated pitfalls（atlas 联动, 2026-10-22）

**Repo 状态核查**：论文摘要仅以纯文本写明 “Code will be released at https://github.com/UAV-AVL/LDVP-SAC”（**未作为可点击超链接嵌入**，且措辞为“will be released”）。按 atlas 判定规则，这属于 **early-release / 尚无 repo 信号**：截至 2026-10-22 **无公开代码、无 issue 流可供核对**。因此下述 pitfall **全部由 §6 失败模式 + 本文方法约束推导**，**未经 issue 验证**，不含任何 issue 编号 / commit / 引文。

**P1 — 射线近共向时内层线性系统秩亏，$\mathbf{c}^\ast$ 数值爆炸**
- 来源约束：附录 B 明确 “If $\operatorname{rank}(\mathbf{N})=2$, its unique least-squares minimizer is $\mathbf{c}^\ast(\mathbf{R})=(\mathbf{N}^\top\mathbf{N})^{-1}\mathbf{N}^\top\mathbf{b}$”，$\mathbf{N}$ 的行是各对应点的水平线法向 $\mathbf{n}_i$。
- 触发条件（可机械推导）：当匹配点集中在一条直路/堤线/单侧建筑立面上，或**极端窄视场 + 近下视**使所有 $\mathbf{q}_i$ 近似同向 ⇒ $\mathbf{n}_i$ 近似同向 ⇒ $\operatorname{rank}(\mathbf{N})=1$ ⇒ $(\mathbf{N}^\top\mathbf{N})^{-1}$ 病态。
- 现象：位姿不报错但水平位置沿“无约束方向”飘出几十米，且 MSAC 打分（点到线残差）可能仍然很小 —— **残差小 ≠ 位置对**，这是最阴的一类失败。
- 迁移建议：在 MSAC 前显式计算 $\mathbf{N}$ 的条件数/最小奇异值，低于阈值直接判该 query 不可解而非输出。

**P2 — 5 m 的 $\tau_L$ 与 1 m 的评价口径错位，导致“低内点残差 + 大定位误差”并存**
- 来源约束：实现细节写死 “five-correspondence hypotheses are evaluated within MSAC using a 5 m point-to-line residual threshold”；而指标是 $A@\{1,3,5\}$。
- 触发条件：把 $\tau_L$ 沿用到更高精度需求（如 &lt;1 m 的巡检/降落），或在尺度更小的场景（OrthoLoC 高度 23–201 m）沿用同一绝对阈值。
- 现象：内点集被远距离外点“稀释”，refit 结果偏向多数但不是最近的那些点。
- 迁移建议：$\tau_L$ 应随 GSD（地面采样距离）或飞行高度归一化，而不是固定 5 m。

**P3 — 旋转网格 + 局部细化：斜视 query 可能落在吸引域外**
- 来源约束：初始化搜索用 “angular steps of $30^\circ$, $45^\circ$, and $45^\circ$ for tilt, azimuth, and roll, respectively, followed by local rotation refinement”。
- 触发条件：AnyVisLoc 的 down-tilt 覆盖 $5^\circ$–$90^\circ$，最斜的观测离近下视初始猜测很远；且 tilt 与 azimuth 的步长不对称（$30^\circ$ vs $45^\circ$），粗网格上存在“某些方向采样更稀”的空隙。
- 现象：同一场景里斜视 query 的误差分布出现**多峰 / 长尾**，而非整体偏移；SAC 的分支统计也因此被污染。
- 迁移建议：把 tilt 的初值从“网格”换成 IMU/重力先验给出的粗姿态（论文已假设重力对齐世界系，这一信息本就可免费获得）。

**P4 — 正深度 $\lambda_i^\ast>0$ 过滤会在大斜视/远景点上“杀掉”正确假设**
- 来源约束：“Hypotheses with insufficient support from correspondences satisfying the positive-depth condition $\lambda_i^\ast>0$ are discarded before consensus evaluation。”
- 触发条件：弱纹理区匹配到远处天际/背景，或相机几乎水平（大斜视）；这些点几何上可能在相机平面之后，$\lambda_i^\ast<0$。
- 现象：正确假设因“正深度支持不足”被提前淘汰，MSAC 在剩余假设里选，输出系统性偏差而非随机噪声。
- 迁移建议：把该过滤改成软惩罚（把负深度记为大残差而非直接删假设），并单独统计负深度比例作为 query 可信度指标。

**P5 — SAC 的两处已承认失效区在工程上会表现为“偶发 5 m+ 跳变”**
- 来源约束一：$S_1$ 由 MDE 相对结构给出，“monocular depth may not always provide sufficiently reliable relative structure for identifying planar queries in relatively homogeneous rural regions”。
- 来源约束二：Fig.3(d) 显示 SAC 选择与“更优求解器”的一致性在 **2–10 m** relief 区间下降。
- 触发条件：农田/草地/水面等均质区，或 matched points 起伏刚好落在 2–10 m。
- 现象：同一航线上相邻帧被分到不同分支，位置输出出现**帧间不连续**（而非缓慢漂移）——这对滤波/控制链路杀伤力远大于同等幅度的平滑误差。
- 迁移建议：对 $S_1$ 做时间域平滑或用滞回（hysteresis）阈值，避免 $\tau_S=0.5$ 附近的抖动式切换。

**P6 — Planar-PnP 分支不产出可信高度**
- 来源约束：Eq.33–35 与正文 “setting the plane elevation to zero only shifts the vertical reference and preserves the camera rotation and horizontal position”。
- 触发条件：下游需要 $C_z$（地形跟随、相对高度保持、着陆）。
- 现象：SAC 一旦切到 Planar-PnP，$C_z$ 变成“相对某个虚拟零平面的量”，跨 query 不可比。
- 迁移建议：把 SAC 的分支标志位一并输出给下游，高度通道在 P 分支时切到别的来源（气压计/单目尺度恢复）。

---

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（本笔记未引入任何自算的论文外指标差值；§3 的数值为明确标注的玩具设定）· 官方 repo 尚为 “Code will be released” 状态，§8 全部 pitfall 为推导而非 issue 验证

[← Back to Map-based Localization README](./README.md)

[//]: # "<!-- source: https://arxiv.org/abs/2610.14945 -->"
