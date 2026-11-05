[//]: # "<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: n/a
paradigm: geometric
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->"

# 可变形四旋翼 MorphQuad：超越人类手腕的机动、操作与抗扰 (MorphQuad: Morphable Quadrotor for Superhuman Maneuverability, Manipulation, and Resiliency)

> **发布时间**：2026-07-29（arXiv:2607.02764v4 [cs.RO]）
> **论文 / 模型名**：MorphQuad（前置概念工作 MorphEUS, 2025）
> **核心定位**：把"会飞的手"所需的三个条件（任意方向最大推力矢量、几乎处处稳定、可小型化的平面四旋翼结构）在**同一台 4.56 kg 样机**上同时满足——关键不在加转子或加连杆，而在**过驱动推力分配的零空间**里同时消掉万向节锁死（gimbal lock）和旋翼间下洗（downwash）两个致命执行器缺陷。

现有全向多旋翼各有残缺：固定倾角机型靠堆 6–8 个反向桨换来全向性但失去平面结构；单轴变倾角机型有控制奇异或下洗干扰未处理；"机载机"（vehicle-of-vehicles）结构则难以小型化。MorphQuad 用"四臂各一个两轴 gimbal + 共轴反转电机对"把输入维度从 4 抬到 12，使输入矩阵 `M ∈ ℝ^{6×12}` 恒定满行秩，再用零空间修正保住稳定裕度——并且**全部计算、定位、轨迹执行都在机上完成，无动捕、无 GPS、无离线算力**。

## X-Ray 开场

它解决的问题是：让一台**保留平面四旋翼外形**的飞行器，能在任意姿态下把最大推力指向任意方向，并且在跨过 90° 奇异面时不失稳。做法是把每个旋翼做成独立两轴可articulate的推力矢量单元（共 12 个控制输入），再用"几何控制 + 最小范数分配 + 零空间修正"的三层控制把 gimbal lock 与下洗当成**分配层的可解约束**而非硬件缺陷。对 spatial AI 研究者意味着：这是一个"把不可微的物理安全约束塞进实时控制零空间"的干净范式，且它刻意把感知栈整体外置（现成 VIO），说明这类平台的瓶颈从来不在感知算法，而在 **allocation**。

---

## 📍 研究全景时间线

```
2014  Ryll [56,57]        单轴变倾角，平面结构 ✓，但控制奇异 + 下洗未处理
2018  Kamel [24] / Yang [47,48,76]   固定倾角：或全向但非平面，或平面但非全向
2019  Ji [23]             概念性双轴 articulate 四旋翼，未处理单桨陀螺进动/气动反扭
2020  Bodie [11,9,10]     差分推力分配缓解控制奇异；下洗仍无解
2021  Su [63]             链式"机载机"，全向 ✓ 但不可小型化
2023  Zhao [79,80] / SkyGauge [61]   商用/链式方案，操作能力有但结构受限
2025  MorphEUS [8]        ← 同组前置概念：两轴 articulate + 最小范数分配 + 几乎处处稳定证明
                          但【无硬件实现、未处理 gimbal lock / 下洗】
2025  Aerix [36,35]       专利：声称"propulsion offset"绕开 90° 极点，算法细节未公开
2026  MorphQuad（本文）    ← 硬件落地 + 零空间修正（锁死 & 下洗）+ 全机载 MMR 实验
      │
      └ 本文局限：无外部真值（误差由机载 EKF 自评）；无定量 baseline；
        gimbal 机械行程 ±1080°（非无限，需滑环）；接触力全程开环、无 F/T 传感；
        样机 4.56 kg，"可小型化"是设计属性而非实测。
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 仿真 / 实机差异（本文无学习环节） |
|---|---|---|---|
| 轨迹规划器（Jetson Orin Nano） | 时间戳 setpoint $(p_d, R_d)$ | **100 Hz** 参考状态 $(R_d, \omega_d, p_d, v_d)$ | 五次多项式；因可任意姿态产生平移力，**平移与旋转解耦**（常规四旋翼做不到） |
| 广义几何控制器（Pixhawk FMUv6x） | 参考状态 + EKF 状态 | $f_{\text{Geo}}\in\mathbb{R}^3$, $\tau_{\text{Geo}}\in\mathbb{R}^3$ | 与常规几何控制器的差别：推力**独立覆盖三个平移轴**，而非只沿机体 $k_\mathcal{B}$ |
| $\mathcal{L}_1$ 自适应增广 | 跟踪误差 | 扰动补偿项 | 在线估计抵消风/地面效应等未知扰动 |
| 推力分配（嵌在 PX4 mixer 框架内） | $w=[f^\top\ \tau^\top]^\top\in\mathbb{R}^6$ | 4×$(\alpha_i,\beta_i,\Omega_i)$ 共 **12** 维 | 最小范数 + 零空间修正；$c^N$ 由解析 if-else 给定（非优化、非学习） |
| 状态估计（EKF） | RealSense 立体深度相机 + IMU | **800 Hz** $(R,\omega,p,v)$ | 现成 VIO；无动捕、无 GPS |
| 执行硬件：两轴 gimbal + 共轴反转电机对 | $(\alpha_i,\beta_i,\Omega_i)$ | 机体矢量推力 $t_i$ | 每轴 **±1080°**（中性位起三整圈）；共轴反转消除陀螺进动与气动反扭 |

### 1.2 关键机制

**⚡ Eureka Moment：把 gimbal lock 与下洗干扰都看成"同一件事"——最小范数解在某个方向上的病态取值；于是用输入矩阵的零空间去扰动推力分布，既不改动 wrench，又能把舵机推离 $\beta_i=\pm\pi/2$、把旋翼推离互为下洗的共线状态。**

三点支撑这一洞见：

1. **硬件侧先消灭"不可控的力矩"**：每个 rotor system 用**两个等速反向旋转的电机 + 对应桨**，因此气动阻力矩与陀螺进动互相抵消，机体净力矩退化为纯几何项 $\tau=\sum_i l_i\times t_i$（Eq. 5）。这一步让"舵机只需克服惯量、不需对抗反扭"成立，也让分配层的线性模型 `w = M t` 站得住。
2. **过驱动带来 6 维零空间**：$M$ 是 $6\times12$ 的宽矩阵且**恒定满行秩**，故 $t=M^\dagger w+N_M c^N$（Eq. 15）中任何 $c^N$ 都精确保留 wrench（Proposition 3）。这是"免费"的安全裕度。
3. **零空间系数的物理选择**：$c^N_1=c^N_3=c^N_5=\langle f/\|f\|,\ j_\mathcal{B}\rangle$（正比于"当前推力方向离死锁轴多近"）；$c^N_2,c^N_4,c^N_6$ 按 $\langle f/\|f\|,\ i_\mathcal{B}\rangle$ 的符号**条件**分配给上/下旋翼对，用于打断共线（Eq. 16）。修正强度随危险程度自动缩放。

论文对必要性的验证是**仿真**（Fig. 2 标题为 "a simulated trajectory tracking task"；正文 "We validate the necessity of the null-space correction via simulation"）：一段 360° pitch 接 360° roll、穿过 $\beta=\pm\pi/2$ 的轨迹，无修正时指令 $\alpha$ 相对物理舵机 wind-up 超过两整圈、跳变超过 1 rad 并失稳（Fig. 2B）；有修正则无跳变（Fig. 2A）。**所有实机实验都在开启该修正的前提下运行**，因此不存在硬件 A/B。

### 1.3 信息流

```
  用户 setpoint (p_d, R_d)
        │
        ▼
 ┌──────────────────┐  100 Hz 参考状态
 │ 轨迹规划器        │──────────────┐   [Jetson Orin Nano]
 │ (五次多项式,解耦) │              │
 └──────────────────┘              ▼
                          ┌────────────────────────┐
 RealSense 立体 ──┐        │ 广义几何控制器 (SE(3)) │   [Pixhawk FMUv6x]
                  ├─EKF──▶│ + L1 自适应增广        │
 IMU ─────────────┘ 800 Hz └───────────┬────────────┘
                                       │ w = [f; τ] ∈ R^6
                                       ▼
                          ┌────────────────────────────┐
                          │ 推力分配                    │
                          │ t = M†w + N_M c^N           │
                          │  ├ c^N 抑制 β→±π/2 (锁死)  │
                          │  └ c^N 打断共线   (下洗)   │
                          │ + Eq.14 解 (Ω,α,β)         │
                          │ + ±2kπ 分支选择最小舵机位移 │
                          └───────────┬────────────────┘
                                      │ 4×(α_i, β_i, Ω_i)  ← 12 维输入
                                      ▼
                    ┌─────────────────────────────────────┐
                    │ 4× [两轴 gimbal(±1080°) + 共轴反转桨]│
                    │  → 矢量推力 t_i ∈ R^3, 任意方向      │
                    └─────────────────────────────────────┘
                                      │
                            m v̇ = m g + R f ,  J ω̇ = -ω×Jω + τ
```

---

## 2 · 数学核心

### 📌 Napkin Formula

> **$w = M\,t$，其中 $M\in\mathbb{R}^{6\times12}$ 恒定满行秩 ⟹ 一切扰动都 matched；$t = M^{\dagger}w + N_M c^{N}$，其中 $c^N$ 免费解决锁死与下洗。**

### 目标 → 公式 → 变量 → 直觉

**目标 1：把 4 个转速扩成 12 个真·独立输入。**

单旋翼在机体系产生的推力方向由两轴 gimbal 角决定（先绕 $j_\mathcal{B}$ 转 $\alpha_i$，再绕旋转后的 $i_\mathcal{B}$ 转 $\beta_i$）：

$$
\boldsymbol{G}_i(\alpha_i,\beta_i)=\begin{bmatrix}\sin\alpha_i\cos\beta_i\\ -\sin\beta_i\\ \cos\alpha_i\cos\beta_i\end{bmatrix},\qquad
\boldsymbol{f}=c_t\sum_{i=1}^{4}\boldsymbol{G}_i(\alpha_i,\beta_i)\,\Omega_i^2
$$

力矩由力臂几何给出 $\boldsymbol{H}_i(\alpha_i,\beta_i)$，合并成 wrench：

$$
\boldsymbol{w}=c_t\sum_{i=1}^{4}\begin{bmatrix}\boldsymbol{G}_i\\ \boldsymbol{H}_i\end{bmatrix}\Omega_i^2
\quad\Longrightarrow\quad
\boldsymbol{w}=\boldsymbol{M}\boldsymbol{t},\quad \boldsymbol{M}\in\mathbb{R}^{6\times12},\ \boldsymbol{t}\in\mathbb{R}^{12}
$$

- $\alpha_i,\beta_i$：内/外舵机角（内轴 XL330-M288-T，外轴 XC330-M288-T）
- $\Omega_i$：桨转速；$c_t$：推力系数
- $M$：由固定安装位置 $l_i$ 决定的**常值**矩阵
- **直觉**：把"每臂一个三维推力矢量"当抽象输入后，wrench 对输入的映射是线性的、且**比输出更宽**——过驱动量就是安全裕度的来源。

**目标 2：能量最优地反解（Proposition 2）。**

$$
\boldsymbol{t}_i=\frac{\boldsymbol{f}}{4}+\frac{\tau_x}{4b}\boldsymbol{k}_\mathcal{B}\pm\frac{\tau_y}{4l}\boldsymbol{k}_\mathcal{B}+\frac{\tau_z}{4r}\hat{\boldsymbol{e}}_{\psi_i}
\;=\;\text{Moore–Penrose 解 }\boldsymbol{t}=\boldsymbol{M}^{\dagger}\boldsymbol{w}
$$

最优性：$\min\ E(\boldsymbol{t})=\tfrac12\sum_i\|\boldsymbol{t}_i\|_2^2$。物理意义——与常规四旋翼的最小范数分配同构，**能耗最优性被保留**。

**目标 3：零空间修正（本文真正的贡献）。**

$$
\boldsymbol{t}=\boldsymbol{M}^{\dagger}\boldsymbol{w}+\boldsymbol{N}_M\boldsymbol{c}^{N},\qquad
\boldsymbol{M}\boldsymbol{N}_M=\boldsymbol{0}\ \Rightarrow\ \boldsymbol{M}\boldsymbol{t}=\boldsymbol{w}\ \ \forall \boldsymbol{c}^N
$$

- **(a) 下洗**：若 $\tau=\boldsymbol{0}$ 且 $f\parallel i_\mathcal{B}$，则全部 $\alpha_i=\pm\pi/2,\beta_i=0$，四臂下洗互指对家，Eq. 2 的推力模型失效 → 用 $c^N_2,c^N_4,c^N_6$ 把"上面那一对"掰离共线。
- **(b) 锁死**：若 $f\parallel j_\mathcal{B}$ 且 $\tau=\boldsymbol{0}$，则 $\beta_i=\pm\pi/2$，$\cos\beta_i=0$，外舵机 $\alpha_i$ 对推力方向**完全失去权限** → 用 $c^N_1=c^N_3=c^N_5=\langle f/\|f\|, j_\mathcal{B}\rangle$ 把 $\beta_i$ 顶开。
- **直觉**：修正量与"离危险轴的分量"成正比。沿死锁轴时系数为 1（最大顶开），垂直时系数为 0（不修正）。

**目标 4：稳定性（Theorem 1）。** 几何控制（Eq. 11）＋零空间修正分配（Eq. 15）下，若初值满足

$$
\Psi(\boldsymbol{R}(0),\boldsymbol{R}_d(0))<2,\qquad
\|\boldsymbol{e}_\omega(0)\|^2<\frac{2k_\boldsymbol{R}}{\lambda_{\max}(\boldsymbol{J})}\bigl(2-\Psi(\boldsymbol{R}(0),\boldsymbol{R}_d(0))\bigr),
\quad \Psi\triangleq\tfrac12\operatorname{tr}(I-\boldsymbol{R}_d^\top\boldsymbol{R})
$$

则闭环误差零点**指数稳定**，包括穿越 gimbal lock 与下洗区间的飞行。$\Psi<2$ 就是"几乎处处"里的那个零测集例外（$\Psi=2$ 对应旋转误差 180°）。

---

## 3 · 带数字走一遍（玩具演算，数字取自论文）

### (a) 悬停分配自洽性检查

$m=4.56\ \text{kg}$，$g=9.81\ \text{m/s}^2$ ⟹ 需总推力 $mg=44.73\ \text{N}$。

最小范数解给每臂 $f/4=11.18\ \text{N}$，方向全同（$\alpha_i=0,\beta_i=0$）。

论文标称**单个 rotor pair 推力 2.8 kg ≈ 27.47 N**，则所需推力占比

$$
\frac{11.18}{27.47}\approx 0.407 \;\approx\; 40\%
$$

——与论文"Sized for a rotor-pair thrust of 2.8 kg that lets MorphQuad hover at 40% throttle"**逐字吻合**。这也说明分配层留了约 60% 推力余量给接触力与抗扰。

### (b) 锁死是怎么发生的：$\epsilon$ 摄动的一次数值推演

设机体横滚 $\pi/2$ 悬停，理想 $f=[0,\ mg,\ 0]$，方向 $\hat{f}=j_\mathcal{B}=[0,1,0]$。由 $\boldsymbol{G}_i=\hat{f}$：

$$
-\sin\beta_i=1\Rightarrow \beta_i=-\pi/2,\quad \cos\beta_i=0\Rightarrow \alpha_i\ \text{由}\ \tfrac{\sin\alpha_i\cos\beta_i}{\cos\alpha_i\cos\beta_i}\ \text{决定} \Rightarrow \textbf{不可定}
$$

即 $\alpha_i$ 失去权限（这正是 $\mathbb{S}^2\to\mathbb{T}^2$ 映射的固有问题）。

现在给一个 $\epsilon=0.1$ 的小扰动：$\hat{f}=[0.0995,\ 0.995,\ 0]$。

$$
\sin\beta_i=-0.995\Rightarrow\beta_i\approx-1.471\ \text{rad}\ (=-84.3^\circ),\quad
\sin\alpha_i=\frac{0.0995}{0.0995}=1\Rightarrow \alpha_i=+\pi/2
$$

反向扰动 $\hat{f}=[-0.0995,\ 0.995,\ 0]$ 给出 $\alpha_i=-\pi/2$。

**结论**：符号一翻，$\alpha_i$ 在 $\pm\pi/2$ 之间整段跳变。高频抖动下舵机必然饱和——这正是 Fig. 2(B) 里"vertical jumps"的机制，也是论文所说的"指令 $\alpha$ 相对物理舵机 wind-up 超过两整圈、跳变超过 1 rad"。

**零空间修正如何救**：此时 $\langle \hat{f}, j_\mathcal{B}\rangle=0.995$，故 $c^N_1=c^N_3=c^N_5\approx 1$（接近满强度），把 $\beta_i$ 从 $-84.3^\circ$ 顶回到远离 $\pm90^\circ$ 的位置，$\cos\beta_i$ 恢复非零，$\alpha_i$ 重新获得连续权限。**wrench 完全不变**（Proposition 3），只是四臂推力不再严格共线，代价是短暂的内部推力抵消。

---

## 4 · 工程视角

| 项目 | 数值 | 出处/备注 |
|---|---|---|
| 起飞质量（含电池） | **4.56 kg** | 原文 Mechatronic design |
| 单 rotor pair 推力 | **2.8 kg** | 悬停落 40% 油门 |
| 电机 | T-Motor VELOX **3008 1500KV** ×2/臂，6 寸三叶桨 | 共轴反转 |
| 峰值电流 | **> 43.6 A** | 由此选 **51 A** 连续 ESC |
| 舵机 | DYNAMIXEL **XL330-M288-T**（内轴）/ **XC330-M288-T**（外轴） | 8 个**菊花链共用一条 UART** |
| gimbal 行程 | **±1080°**（两垂直轴，中性位起三整圈） | 论文脚注：滑环可做到无限 |
| 飞控 / 机载算力 / 相机 | Pixhawk FMUv6x / Jetson Orin Nano / RealSense 立体深度相机 | 全部商用现货 |
| 参考状态频率 | **100 Hz** | setpoint → 飞控 |
| 状态估计频率 | **800 Hz** | EKF 融合 VIO + IMU |
| 控制环频率（几何控制/分配） | **论文未报告** | — |
| 端到端延迟 / 舵机带宽 / 内存占用 / FPS | **论文未报告** | Fig. 4(D) 仅给 90° 阶跃的响应曲线，无量化数值 |
| 舵机负载测试 | 零推力负载下 90° 阶跃 | 用于论证共轴反转"消除动态负载" |

**Trade-off 解读**

- **12 维输入 vs 4 维**：换来过驱动零空间，但也把分配变成了"必须处理分支与病态"的模块。Eq. 14 有两支解（$\sin^{-1}$ 与 $\pi-\sin^{-1}$），还要在 $\pm2k\pi$ 里搜步长最小的那支，靠 $n_r$ 限定"超过一个三角周期的圈数"——这是个**离散搜索 + 连续优化混合**的实时环节。
- **共轴反转的代价与收益**：多一个电机、多一付桨的质量与电流，换来"舵机不需对抗陀螺进动与气动反扭"（Fig. 4(D) 论证舵机响应与推力负载解耦），以及分配层能用**纯几何线性模型**（Eq. 5 无额外力矩项）。没有这一步，Eq. 8 的 $M$ 就不成立。
- **机械行程预算**：$\pm1080°$ 靠外舵机偏置（belt-pulley）+ 轴心走线 + 线缆余量换取，因此**不是无限旋转**。上层规划必须把每轴累计转角控制在 3 圈内，否则需要滑环（论文明确列为替代方案）。
- **算力分层**：规划在 Jetson、控制在 Pixhawk，两者之间只有 100 Hz 的参考状态流——感知/规划侧的任何抖动被这个低频接口吸收，但也意味着**高层不能做高频反应式闭环**。

---

## 5 · 数据与评测

**无公开数据集、无公开 benchmark**。全部为自建硬件任务，无动捕、无 GPS、无离板计算。

**三组任务的工况（逐字数字）**

| 组 | 任务 | 场景设定 |
|---|---|---|
| 机动 | 管道巡检 | 两根水平平行管，竖直间隙 = **1.3 倍** MorphQuad 边长；沿直径 **1 m** 的竖直圆周平移，同时连续俯仰 **720°**，机头始终指向管道 |
| 机动 | 手部指向跟踪 | 操作者站于机前 **1.5 m**，伸手向机载相机；机体悬停跟踪手的指向与 roll 倾角 |
| 操作 | 阀门旋转 | 阀门装于墙上 **3 m** 高，**30 cm** 长轴以 **45°** 从墙面外伸；机头刚性 "Y" 形被动末端执行器插入轮辐 |
| 操作 | 停靠 + 打钉 | 墙上 **2 m** 高处泡沫块；钉子经钕磁连接器垂直挂于机体底部，插入后脱开 |
| 操作 | 推动 | 地面无约束轮式白板，**30 kg**，需先停靠再推约 **1 m** |
| 抗扰 | 风扰 | 吹叶机喷嘴距机前脸 **30 cm**，机身处实测风速 **30 m/s**；四类场景各持续 **30 s** |
| 抗扰 | 脉冲推/挑 | 人持锤直接敲击机体，产生侧推与偏心"挑" |
| 抗扰 | 持续拉 | 系绳 + 串联测力计 |

**指标定义**：world-frame 位置 RMSE（cm）与姿态 RMSE（deg），**全部由机载状态估计器给出**（"we report all tracking errors in the world frame as estimated by the onboard state estimator"）。论文明确声明：**不评测接触力/力矩精度**，因为规划器不指令接触力、机体也没有相应传感器。

**主要结果（逐字）**

- 机动：全轨迹位置误差 **below 6 cm** RMSE（三轴），俯仰 **5.5°** RMSE；手跟踪位置 RMSE **5.5 cm**、姿态 RMSE **6.99°**，误差分布集中于 **3°–8°**，超过 **15°** 的离群点对应手部快速加速导致视觉伺服瞬时饱和。
- 操作：机身最大力矩 **4.92 Nm**（pitch，roll 对称），侧向力 **4.55 kg**。阀门任务位置 RMSE **4 cm**（z）、**below 3 cm**（x/y），姿态 RMSE **3.9°** roll / **7.7°** pitch / **2.4°** yaw。打钉任务三轴位置 RMSE **约 5 cm**，姿态 **2.4°** / **2.9°** / **2.3°**。推动任务 x 轴 **约 3 cm**、z 轴 **约 15 cm**，y 轴因白板位移 **约 0.8 m** 直接累计为误差；姿态 **2.8°** / **5.0°** / **2.1°**。
- 抗扰：风扰下沿主风向（y）位置 RMSE **约 8 cm**，x/z **接近 4 cm**；姿态 **2.8°** / **4.6°** / **2.9°**。推扰使 y 向位移**达 50 cm**，但 x **2 cm**、z **4 cm**，pitch 双向超 **20°** 时 roll **4.3°**、yaw **2.5°**。拉扰：力传感峰值 **4.55 kg**，由位置误差与控制器状态反推的扰动力 **3.56 kg**，差 **0.99 kg** 归因于在线抗扰提前抵消；y 位移**超过 80 cm**，x **4.4 cm**、z **2 cm**，roll **2.4°**、yaw **1.0°**、pitch **5.8°**（系绳略上仰）。
- 汇总：沿未受扰轴，位置 RMSE **2–5 cm**，姿态 RMSE **3–6°**。

**对比设置的关键性质**：Table 1 是**定性 ✓/✗/△**，不是实测数字对比；本文**没有跑任何 baseline 硬件**。风扰对比也是论证性的——论文主张吹叶机（小面积、空间非均匀、时变、同时加载平移与旋转）"a regime distinct from, not easier than, a uniform freestream"，而非同一协议下的公平 benchmark。

---

## 6 · 能力与失败模式

**能做（有实机数据支撑）**

- 平移 + 连续 **720°** 俯仰旋转同时进行（管道巡检）；论文声称可达**最多六整圈**，而现有变倾角机型"at most one full revolution"，再多就需要线缆"unwinding"。
- 悬停中做 onboard 视觉手部指向跟踪，roll/pitch/yaw 独立指令。
- 45° 倾斜阀门上施加与人类手腕可比的力矩；墙面停靠压制钉子；推动 **30 kg** 白板。
- 单旋翼正面承受 **30 m/s** 气流（**67 mph / 108 km/h**）仍维持悬停；脉冲推/挑与持续拉下保持未受扰轴精度。
- **平移-旋转解耦的抗扰**：拉扰散点图显示 MorphQuad 的旋转误差几乎不随位置位移增长，而仿真中的常规四旋翼必须靠俯仰/横滚产生侧向力，旋转误差随位移快速上升。

**不能做 / 论文自陈的失败模式**

- **接触力全程开环**：无 F/T 传感、无视觉伺服；阀门/打钉/推板全部"把接触反作用当扰动"。
- **推动任务的 y 轴"误差"不是跟踪误差**：因把期望推力转成常值机体加速度而不更新位置 setpoint，白板 **约 0.8 m** 位移直接计入 y 轴误差；z 轴 **约 15 cm** 的升高归因于持续贴壁的壁面效应与接触摩擦。
- **打钉接触瞬间振荡**：着陆腿柔顺性导致撞墙振动 + 桨盘贴近壁面引发湍流扰动推力。
- **阀门任务 pitch 误差偏高（7.7°）**：前挂末端执行器附加质量产生低头力矩，而控制器用的是**不含末端执行器的标称模型**。
- **手跟踪离群点 >15°**：手部快速加速使视觉伺服反应瞬时饱和。
- **旋转不是无限的**：$\pm1080°$ 是线缆余量换来的机械预算；超出需滑环。
- **无外部真值校核**：所有 RMSE 都是"机载 EKF 眼中的世界系"，VIO 漂移会被计入而非暴露。
- **无定量 baseline、无跨平台复现实验**：Table 1 的 ✓ 是能力勾选，不是性能排名。

### 隐含假设 (Hidden Assumptions)

1. **误差自评闭环成立**：位置/姿态精度用机载 EKF 估计当基准。若 VIO 在贴壁、强风、湍流下漂移，报告数字会**系统性偏乐观**，而论文没有外部动捕做交叉验证（这是它刻意放弃动捕的代价）。
2. **推力可线性叠加且不饱和**：$w=M t$ 假设四臂推力独立可加。论文自己承认下洗 "invalidates the thrust model in (2)"，只是靠零空间把共线状态**短暂**避开——即模型在瞬态是被**故意违反**的。
3. **零空间系数是手写 if-else，不是优化出来的**：Eq. 16 的条件分支按 $\langle \hat{f}, i_\mathcal{B}\rangle$ 的符号二选一。换桨径、换臂距、换 gimbal 限位都需要重推，不存在"训练/自适应"环节。
4. **标称模型不含任务负载**：末端执行器、钉子、磁连接器都不进模型（阀门任务的 pitch 误差即此假设的代价）。
5. **接触被当作纯扰动**：不建模摩擦、弹性、壁面效应的**方向性**；因此"贴着移动表面维持接触"只能靠前馈常值加速度硬撑。
6. **"可小型化"是结构属性而非实测**：本文保留平面四旋翼布局、无笼架无连杆，因而**具备**缩到掌上级（如 Crazyflie 量级）的条件；但本文样机起飞质量为 **4.56 kg**，未做缩尺样机、未测缩尺后的推力/舵机/线缆余量。
7. **风扰的等价性主张**：吹叶机（30 cm 距离、小入射面、非均匀时变）被论证为"distinct from, not easier than"风洞/风扇阵的均匀来流（后者 10–20 m/s）。这是**论证**，不是同协议对照实验。
8. **单机、室内、任务时长内**：无长时 GPS 拒止导航验证、无多机、无动态障碍。

---

## 7 · 与相关工作对比

| 方案 | Enabler I<br />任意方向最大推力 | Enabler II<br />几乎处处稳定（含执行器缺陷） | Enabler III<br />可小型化结构 | 机载定位+轨迹 | 全向飞行之上的操作 | 抗扰 | 关键短板 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Yang 2018 [47,48,76]（固定倾角） | ✗ | ✓ | ✗ | ✗ | ✓ | ✓ | 内部推力抵消，无法任意向出满推力 |
| Lee 2024 [26]（固定倾角） | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | 同上 |
| Veenstra 2026 [68]（固定倾角） | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | 非平面多旋翼 |
| Ryll 2014 [56,57]（单轴变倾角） | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | 控制奇异 + 下洗 |
| Kamel 2018 [24] | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ | 控制奇异 |
| Ji 2019 [23] | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | 单桨陀螺进动/气动反扭耗掉推力预算 |
| Bodie 2020 [11,9,10] | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | 差分分配缓解奇异，下洗仍无解 |
| Su 2021 [63]（链式机载机） | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | 不可小型化 |
| Zhao 2023 [79,80] | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | 同上 |
| SkyGauge 2023 [61]\* | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | 有限 articulation，非全向满推力 |
| Li 2025 [30] / Lee 2025 [25] | ✗ | ✗ | ✓ | ✗ / ✗ | ✗ / ✓ | ✗ / ✓ | 控制奇异、下洗 |
| Aerix 2025 [36,35]\* △ | △ | △ | △ | ✓ | ✗ | ✓ | 专利称"propulsion offset"绕 90° 极点，**无算法细节、无量化** |
| MorphEUS 2025 [8]（同组前置） | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | 概念：仅证 minimum-norm 分配 + 几乎处处稳定，无硬件、无锁死/下洗处理 |
| **MorphQuad（本文）** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | 无外部真值、无定量 baseline、接触开环、±1080° 非无限 |

\* 无同行评审，据公开专利信息评估。△：Aerix 硬件 [36] 与控制 [35] 专利申请声称四旋翼结构与全向飞行，但硬件与算法细节不可得；本文以输入矩阵**零空间**（Eq. 15）同时处理锁死与下洗并保稳定性，与之不同。

**面试 Tip**：被问"MorphQuad 和现成的 tilt-rotor / 6–8 桨全向机差在哪"，别背结构，答三句——
① **不是加转子，是加维度**：4 臂 × 2 轴 gimbal → 12 个真独立输入，`M` 是 **6×12 恒定满行秩**，所以任意 wrench 可达、任意扰动都 *matched*（Corollary 1）；
② **真正的贡献在 allocation，不在机械**：两轴 gimbal 谁都能做（Ji 2019、Aerix 专利都提过），难的是"最小范数解在 $f\parallel j_\mathcal{B}$ 时让外舵机彻底失去权限、在 $f\parallel i_\mathcal{B}$ 时四臂下洗互指"——本文用零空间扰动解掉，且**证明 wrench 不变 + 闭环指数稳定**（Prop. 3 / Thm. 1）；
③ **验证条件是"全机载"**：无动捕、无 GPS、无离板算力，这才是它相对实验室 demo 的差异点——但要主动补一句"它的精度是机载 EKF 自评的，没有外部真值交叉验证"。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-11-05)

**论文全文未给出任何 `github.com` 仓库链接**（出现的 "Report GitHub Issue" 为 arXiv HTML 页面的公共反馈横幅，不构成 repo 信号）。因此：**官方 repo 未在论文中给出**，以下 pitfall 由 §6 失败模式 + 本文方法约束**推导（未经 issue 验证）**，不引用任何 commit / issue 编号。

### Pitfall 1 — 零空间修正的"必要性"只有仿真证据，硬件上不存在 A/B

- **来源失败模式**（§6）：跨 90° 姿态时舵机饱和 → 失稳。
- **方法约束**：论文原文 "We validate the necessity of the null-space correction **via simulation**"；Fig. 2 caption 明确为 "**in a simulated trajectory tracking task**"；并声明 "all flight experiments in this work operate with the correction active"。
- **落地后果**：你无法从论文推断真机上"不修正"会怎样——仿真的结论是指令 $\alpha$ 相对物理舵机 wind-up 超过两整圈、跳变超过 1 rad 并失稳，而真实舵机的饱和边界、齿隙、温漂完全未刻画。移植到不同舵机型号时，这条曲线必须自己重跑（建议先在 Gazebo SITL 复现 Fig. 2，再上实机）。
- **误读风险**：把 Fig. 2 当成飞行日志。它是仿真对比。

### Pitfall 2 — 零空间系数是手写条件分支，不是可迁移的增益

- **来源失败模式**（§6）：下洗 "invalidates the thrust model in (2)"，推力有效值下降 → 分配出的 wrench 送不到。
- **方法约束**：Eq. 16 用 `if ⟨f/‖f‖, i_ℬ⟩ > 0` 二选一，在 $c^N_2=-c^N_4$ 与 $c^N_6$ 之间切换。这套系数**没有量纲分析、没有优化目标、没有自适应律**，只保证"打断共线"这一条定性性质。
- **落地后果**：换桨径 / 换臂距 $l,b$ / 换 gimbal 限位后，$N_M$ 的基与 $\hat{e}_{\psi_i}$ 全部改变，必须重推 Eq. 13/16；论文没有给"多强才算够"的判据。社区实践时应把它当成**结构化启发式**，用你自己的下洗模型或实测推力衰减表重新标定。
- **误读风险**：以为 `c^N` 是控制器增益、可以随手调大。

### Pitfall 3 — 报告的 RMSE 在某些任务里不是"跟踪精度"，且全部无外部真值

- **来源失败模式**（§6）：推动任务把期望推力转成常值机体系加速度而**不更新位置 setpoint**，白板约 **0.8 m** 位移直接累计为 y 轴误差；z 轴约 **15 cm** 归因壁面效应与摩擦。
- **方法约束**：全文"we report all tracking errors in the world frame **as estimated by the onboard state estimator**"，无动捕、无 GPS、无离板基准。
- **落地后果**：任何把本文数字当 benchmark 基线（"MorphQuad 位置 RMSE 5 cm"）的下游工作都会踩两个坑——(i) 推动类任务的 y 轴数值是**任务语义误差**而非控制误差，不可与悬停 RMSE 混用；(ii) 该数值是 VIO+EKF 的**自评**，贴壁/强风/湍流下 VIO 若漂移，误差被低估而非暴露。要复现，必须自带外部真值（动捕或独立激光跟踪），否则你测的是"你的 VIO 与你的控制器的合谋"。
- **误读风险**：把 §5 汇总的"2–5 cm / 3–6°"当成全任务统一精度指标——原文限定为 "along **undisturbed** axes"。

### Pitfall 4（附）— $\pm1080°$ 是机械预算，规划器必须自己记账

- **来源失败模式**（§6）：连续多圈旋转靠线缆余量实现，超出即需 "unwinding"。
- **方法约束**：gimbal 行程 $\pm1080°$；Eq. 14 里用 $n_r$ 限定"$\pm2k\pi$ 分支搜索"的最大圈数；论文脚注明确 "Slip rings could be used instead to enable unlimited rotation"。
- **落地后果**：上层轨迹规划**没有**在数学上受 $\pm1080°$ 约束——它只做五次多项式插值。所以"最多六整圈"是硬件的余量统计，不是规划器的保证。做长时螺旋巡检时，必须自己维护每轴累计转角状态，否则会在某次任务中把线缆拧断。

---

[← Back to 导航与几何控制模块 README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（2607.02764v4）· 未在真机复现的数字标 `UNVERIFIED`（本文档中所有数字均逐字取自论文正文；标 `UNVERIFIED` 者仅 §3 的玩具推演中由论文数值二次算出的派生量，如 40.7% 油门占比）

[//]: # "<!-- source: https://arxiv.org/abs/2607.02764 -->"
