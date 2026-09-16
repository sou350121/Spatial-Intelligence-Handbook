<!-- ontology-5axis
problem: n/a
representation: sparse
sensor: RGBD
paradigm: hybrid
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# 从视频生成到机器人操作：基于刚体几何一致性 (GenVid2Robot: From Video Generation to Robot Manipulation via Rigid-Geometric Consistency)

> **发布时间**：2026-07-10（arXiv:2607.09191v1 [cs.RO]）
> **论文 / 模型名**：GenVid2Robot
> **核心定位**：把"生成视频"从**伪演示**降级为**不确定的 2D 运动假设**，只有通过首帧 RGB-D 稀疏锚点的刚体 SE(3) 重投影一致性检验的 2D 轨迹才允许转成真机轨迹——解决"视觉合理 ≠ 物理可执行"的鸿沟。

生成视频能给出物体"看起来怎么动"的先验，但它没有米制几何、没有抓取接地、没有运动学可行性、也没有执行期反馈，直接回放会失败。本文的结论是：在生成视频与真机执行之间插入一个**稀疏刚体几何一致性验证器**，可以显著提升真机操作成功率。

---

## X-Ray 开场

**解决什么问题**：RIGVid / NovaFlow 这类"生成视频→机器人操作"的方法直接抽取物体轨迹或 dense flow 重定向给机器人，但生成视频的 2D 视觉合理性并不蕴含 3D 刚体一致性、抓取可行性和运动学可达性——视觉漂移、非刚体伪影、深度演化错误都会被直接执行。

**提出了什么**：GenVid2Robot 用**首帧 RGB-D 的稀疏语义锚点**作为米制参考，追踪这些锚点在生成视频中的 2D 运动，用 PnP/RANSAC 问一个反向问题——"这段 2D 运动能不能被一个**公共的**相对 SE(3) 变换重投影解释？"能则接受，不能则拒绝或重新生成。接受的相对运动被施加到**真实抓取时刻的 TCP 位姿**上（而非复制物体中心轨迹），再用有限幅度的 RealSense 深度补偿修正执行误差。

**对 spatial AI 研究者意味着什么**：这是一条"**生成模型负责假设、几何验证负责把关**"的架构范式。它没有训练任何模型，全部用 off-the-shelf 组件（VLM + SAM + Kling 1.6 + CoTracker + solvePnPRansac + AnyGrasp），贡献在**组织方式**——把 SfM 式的重投影一致性测试插进生成式 pipeline 当作 gate。对做 3D 生成、VLA、视频世界模型的人，这是一个可复用的"几何裁判"设计模式。

---

## 📍 研究全景时间线

```
2022 ── SayCan（语言规划 + affordance 接地）
     └ Code as Policies（语言→可执行机器人程序）
2023 ── VoxPoser（LLM 生成空间 value map）
     └ RT-2 / PaLM-E（多模态表征→具身推理/动作）
     └ ACT / Diffusion Policy（模仿学习、visuomotor policy）
     └ FoundationPose / AnyGrasp（6D 位姿 / 抓取候选，但需 CAD 或参考视图）
2024 ── ReKep（大模型生成关系关键点约束）           ← 本文 baseline 之一
2025 ── RIGVid（生成视频→6D 物体轨迹→重定向）        ← 本文 baseline 之一
     └ NovaFlow（生成视频→actionable object flow）   ← 本文 baseline 之一
2026 ── ★ GenVid2Robot：在「生成视频」与「真机执行」之间插入
        稀疏刚体 SE(3) 重投影一致性 gate
        + 把相对运动挂在真实抓取 TCP 上（grasp-conditioned）
        + 有界单轴深度补偿
        │
        └ 本文局限：① 依赖生成视频质量，pass rate 仅 55–74%
                     ② 无全局可达性/可操作度规划 → 8/11 失败是 workspace-limit
                     ③ 深度补偿只沿相机 z 单轴，图像平面位移不补偿
                     ④ 总延迟 420.5 s，且 96% 花在云端（不可闭环）
```

**位置判读**：它不是"更强的生成模型"，而是"给生成模型加一个几何审计层"。相对于 ReKep（约束欠定连续旋转）、RIGVid（对视觉漂移敏感）、NovaFlow（无显式刚体一致性、轨迹漂移累积），本文的差异化在于**显式的稀疏 SE(3) 可解性判据**与**以抓取位姿为轨迹锚点**。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 阶段 | 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|---|
| Stage 1 / Phase 1 | 语义锚点采样：VLM 部件提示 + **SAM** + 深度感知 K-Means | 首帧 $\mathbf{I}_0,\mathbf{D}_0$、任务指令 $l$ | 部件掩码 $\{M_m\}$、稀疏锚点 $\mathbf{q}_i^{(0)}$、首帧 3D 锚点 $\mathcal{P}_c^0$ | 训练-free，全为现成模型推理（VLM + SAM + K-Means） |
| Stage 1 / Phase 2 | 视频运动假设：**Kling 1.6** 生成 + VLM 语义筛选 + **CoTracker** 追踪 | $\mathbf{I}_0, l$ | $N_v$ 条候选视频、2D 跟踪 $\mathbf{q}_{i,n}^{(t)}$ 与可见性 $\alpha_{i,n}^{(t)}$ | 训练-free；论文实现每任务生成 **5 个候选** |
| Stage 2 / Phase 3 | 刚体几何一致性验证：**solvePnPRansac** + 重投影残差判据 | 首帧 3D 锚点 + 跟踪 2D 点 | $\Delta\mathbf{T}_{c,n}^{raw,(t)}$、残差 $e_{n,t}$、接受集 $\mathcal{A}$ | 训练-free；RANSAC 内点阈值 ≈ **8 px** |
| Stage 3 / Phase 4 | 掩码约束抓取 + TCP 归纳：**AnyGrasp** + 掩码过滤 + PyBullet IK(RM75 URDF) + CubicSpline/Savitzky–Golay | 真实 RGB-D 点云、$\Delta\bar{\mathbf{T}}_b^{(t)}$ | 抓取位姿 $\mathbf{T}_{b,tcp}^{(0)}$、关节轨迹 | 训练-free；IK 位置/姿态阈值 **0.01 m / 0.40 rad** |
| Stage 3 / Phase 5 | 有界深度补偿（**RealSense**） | 标称 TCP 轨迹 + 实时深度流 | $\mathbf{T}_{cmd}^{(t)}$ | 训练-free；$\lambda_d\in[0.3,0.5]$，$d_{max}\in[0.005,0.01]$ m |

**一句话**：整条 pipeline **没有任何可训练参数**，所有组件都是 off-the-shelf；论文自陈"贡献不是新的 VLM、点追踪器、PnP 求解器或抓取检测器"。

### 1.2 关键机制

**⚡ Eureka Moment：生成视频不是演示（demonstration），而是假设（hypothesis）；判定它能否进入机器人执行管线的唯一门槛是——它的 2D 锚点运动必须能被首帧 RGB-D 3D 锚点的**同一个**相对 SE(3) 变换重投影解释，残差足够小。**

由此派生出两个非显然的设计决策：

1. **不用 CAD 规范物体坐标系**。锚点集 $\mathcal{P}_c^0$ 直接定义在首帧相机系里，恢复的是"首帧稀疏锚点集的相对刚体运动"，不是 canonical object 6D pose。这样绕开了 FoundationPose 那类方法对 CAD 模型/参考视图的依赖。
2. **轨迹锚在抓取上，不锚在物体中心上**。$\mathbf{T}_{b,tcp}^{nom,(t)}=\Delta\bar{\mathbf{T}}_b^{(t)}\mathbf{T}_{b,tcp}^{(0)}$。论文反复强调：物体轨迹与 TCP 轨迹**本来就不应该重合**，因为可执行的腕部运动取决于抓取位置与机器人运动学。

### 1.3 信息流 / 架构图

```
      首帧 RGB-D O_0 = {I_0, D_0, K, T_b,c}  +  指令 l
                        │
        ┌───────────────┴────────────────┐
        │ Stage 1  Phase 1               │         Stage 1  Phase 2
        │ VLM 部件提示 (handle/body/spout/lid)      Kling 1.6 ──► 5 候选视频 V̂_n
        │        │                        │              │
        │      SAM 掩码 {M_m}             │         VLM 语义筛选（任务/身份/形状/方向）
        │        │                        │              │
        │  有效性过滤: D_0>0, d(·,∂M_m)>ε_b │        CoTracker 追踪
        │        │                        │              │
        │  深度感知特征 φ=[u/W, v/H, D/d_s] │         q_{i,n}^{(t)}, α_{i,n}^{(t)}
        │        │                        │              │
        │  部件级 K-Means  K_m=5           │              │
        │        │                        │              │
        └──────► 2D 锚点 q_i^(0) ──────────┴──────────────┘
                        │
                反投影 (Eq.3)  z_i·K⁻¹[u,v,1]ᵀ
                        ▼
              首帧 3D 锚点 P_c^0 = { p̄_i^{c,0} }
                        │
        ╔═══════════════▼════════════════════════════════╗
        ║ Stage 2  Phase 3  刚体几何一致性验证            ║
        ║  可见性/退化剔除 ──► 需 ≥4 个有效锚点且不近共线   ║
        ║  solvePnPRansac (阈值≈8px) → ΔT_{c,n}^{raw,(t)} ║
        ║  重投影残差 e_{n,t} (Eq.14)                     ║
        ║  接受判据 (Eq.15): ē_n<5px, e_n^max<12px,       ║
        ║                    r_n^valid>η_v, L_n^invalid<L_max
        ║  多候选择优 (Eq.16) → n*                       ║
        ╚═══════════════╤════════════════════════════════╝
                        │ 相机系 → 基座系 (Eq.5)  ΔT_b = T_b,c ΔT_c T_c,b
                        ▼
        ┌───────────────────────────────┐   ┌──────────────────────────┐
        │ Stage 3  Phase 4               │   │ Stage 3  Phase 5         │
        │ AnyGrasp 6-DoF 候选             │   │ e_d = d_rs − d_exp       │
        │ 掩码过滤 (contact ⊂ object mask)│   │ p_cmd = p̄_tcp +          │
        │ 打分 S_j = s_j − λ_m E_m − λ_r E_r − λ_c E_c              │
        │ → T_{b,tcp}^{(0)}               │   │  clip(λ_d e_d, ±d_max)·r_b│
        │ TCP 归纳: T̃ = ΔT̄_b^(t) T_{b,tcp}^{(0)}                     │
        │ PyBullet IK(RM75) → CubicSpline → S-G 滤波 → FK 回检       │
        └───────────────────────────────┘   └──────────────────────────┘
                        │
                        ▼
                 真机执行 T_cmd^(t)   →  若失败/大幅位移 → 重新初始化 O_0
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$\mathbf{q}_{i,n}^{(t)} \;\approx\; \Pi\!\left(\mathbf{K},\; \Delta\mathbf{T}_{c,n}^{(t)}\,\bar{\mathbf{p}}_i^{c,0}\right),\quad i\in\mathcal{I}_{n,t}$$

**一句话**：生成视频里追踪到的 2D 点，必须能被**首帧 3D 点集的同一个刚体变换**投影出来——否则这条视频不能上机器人。

### 2.1 目标 → 公式 → 变量 → 直觉

**(a) 首帧反投影（构造米制参考）**

$$\mathbf{p}_i^{c,0}=z_i^{(0)}\mathbf{K}^{-1}\begin{bmatrix}u_i^{(0)}\\v_i^{(0)}\\1\end{bmatrix},\qquad z_i^{(0)}=\mathbf{D}_0\!\left(u_i^{(0)},v_i^{(0)}\right)$$

- $\mathbf{K}$：相机内参；$\mathbf{D}_0$：首帧米制深度图
- 直觉：把"文字提示定位到的部件像素"变成**有真实尺度的 3D 点**。这是整个方法的米制来源。

**(b) 锚点采样（深度感知 K-Means）**

$$\phi(u,v)=\left[\tfrac{u}{W},\;\tfrac{v}{H},\;\tfrac{\mathbf{D}_0(u,v)}{d_s}\right]^{\top},\qquad \{\mathbf{c}_{m,k}\}_{k=1}^{K_m}=\mathrm{KMeans}\!\left(\left\{\phi(u,v)\mid(u,v)\in\Omega_m\right\},K_m\right)$$

- $\Omega_m$：第 $m$ 个部件掩码内满足 $\mathbf{D}_0>0$ 且 $d((u,v),\partial M_m)>\epsilon_b$ 的有效区域（去无效深度、去边界、去过密采样）
- $d_s$：深度归一化常数；论文实现 $K_m=5$（每个有效部件 5 个锚点）
- 直觉：把 $u/W, v/H$ 与 $D/d_s$ 放在同一量纲里聚类，得到**既空间分散、又有深度区分度**的锚点。锚点选在语义部件的几何中心附近，而不是任意纹理点。

**(c) 相对运动估计（PnP/RANSAC）**

$$\Delta\mathbf{T}_{c,n}^{raw,(t)}=\arg\min_{\Delta\mathbf{T}\in SE(3)}\sum_{i\in\mathcal{I}_{n,t}}\rho\!\left(\left\|\mathbf{q}_{i,n}^{(t)}-\Pi\!\left(\mathbf{K},\Delta\mathbf{T}\bar{\mathbf{p}}_i^{c,0}\right)\right\|_2^2\right)$$

- $\rho(\cdot)$：由 RANSAC 内点选择诱导的鲁棒损失；$\mathcal{I}_{n,t}$：内点集
- **输入是 3D–2D 配对的"逆问题"**：3D 点固定（来自真机首帧），2D 观测来自生成视频。

**(d) 一致性判据（Gate）**

$$\bar{e}_n=\frac{1}{|\mathcal{T}_n^{valid}|}\sum_{t\in\mathcal{T}_n^{valid}}e_{n,t},\qquad e_n^{max}=\max_{t\in\mathcal{T}_n^{valid}}e_{n,t}$$

$$\mathcal{A}=\left\{n\;\middle|\;\bar{e}_n<\epsilon_{mean},\;e_n^{max}<\epsilon_{max},\;r_n^{valid}>\eta_v,\;L_n^{invalid}<L_{max}\right\}$$

- 论文实现：$\epsilon_{mean}=5$ px，$\epsilon_{max}=12$ px
- $r_n^{valid}=|\mathcal{T}_n^{valid}|/T$：有效帧比例；$L_n^{invalid}$：最长连续无效帧长度
- 直觉：**均值 + 最大值双阈值**——均值管整体漂移，最大值管单帧爆掉（非刚体瞬间）。再叠加"有效帧够多、连续丢帧不能太长"两条可用性约束。

**(e) 多候选择优**

$$C_n=\bar{e}_n+\lambda_{max}e_n^{max}-\lambda_v r_n^{valid}+\lambda_s E_n^{smooth},\qquad n^*=\arg\min_{n\in\mathcal{A}}C_n$$

- $E_n^{smooth}$：对时间上不稳定的恢复运动做惩罚
- 直觉：残差小、覆盖久、时间平滑的候选胜出。

**(f) 抓取条件轨迹归纳 + 有界深度补偿**

$$\tilde{\mathbf{T}}_{b,tcp}^{(t)}=\Delta\bar{\mathbf{T}}_b^{(t)}\mathbf{T}_{b,tcp}^{(0)},\qquad \mathbf{p}_{cmd}^{(t)}=\bar{\mathbf{p}}_{tcp}^{(t)}+\mathrm{clip}\!\left(\lambda_d e_d^{(t)},-d_{max},d_{max}\right)\mathbf{r}_b$$

- $\mathbf{r}_b=\mathbf{R}_{b,c}[0,0,1]^{\top}$：相机深度方向在基座系中的表示
- 直觉：**只改位置、只改一条轴（相机 z）、改动被 clip 硬限幅**。这是一个"宁可修不够，也不修坏"的保守设计。

---

## 3 · 带数字走一遍（玩具例子，非论文数据）

> 以下为**自造的示范数值**，用于建立量感，与论文实验无关。

**设定**：相机 $640\times480$，$f_x=f_y=600$，$c_x=320$，$c_y=240$。两个锚点深度均为 $z=0.5$ m：

| 锚点 | 像素 $(u,v)$ | 反投影 $(x,y,z)$ (m) |
|---|---|---|
| A | (200, 150) | $(-0.100,\;-0.075,\;0.500)$ |
| B | (440, 330) | $(+0.100,\;+0.075,\;0.500)$ |

**情形 1：一个小深度变化**。假设物体沿相机 z 靠近 5 cm，A 变为 $(-0.100,-0.075,0.450)$：

$$u'=\frac{600\times(-0.100)}{0.450}+320=186.7,\qquad v'=\frac{600\times(-0.075)}{0.450}+240=140.0$$

即 A 从 (200,150) 移到 (186.7,140.0)，**位移约 16.6 px**。

> 关键量感：**5 cm 的真实深度变化 → 16.6 px 的图像位移，直接超过 $\epsilon_{max}=12$ px**。这解释了为什么"像素级看着差不多"和"米制上差多少"完全是两回事，也解释了为什么必须先反投影再验证。

**情形 2：一个真实刚体旋转**。假设 $\Delta\mathbf{T}$ 是绕相机 Y 轴转 $1°$：

- A：$x'=-0.100\cos1°+0.500\sin1°=-0.09126$，$z'=0.100\sin1°+0.500\cos1°=0.50167$ → $u'=210.85,\;v'=150.30$，**位移约 10.9 px**
- B：$x'=+0.100\cos1°+0.500\sin1°=0.10871$，$z'=-0.100\sin1°+0.500\cos1°=0.49818$ → $u'=450.93,\;v'=330.33$，**位移约 10.9 px**

两个锚点**位移量级一致、方向一致** → PnP 能拟合出一个公共 SE(3)，内点重投影残差 ≈ 0 px，$e_{n,t}\ll 5$ px → **接受**。

**情形 3：非刚体（假设被拒）**。若 B 的追踪结果是 (465, 340)（位移 25.3 px 且方向偏离），单个 SE(3) 无法同时解释 A 的 10.9 px 和 B 的 25.3 px：
- RANSAC 会保留残差小的内点（比如 A 加其他点），B 被踢出内点；
- 若有效锚点降到 <4 个，该帧直接标记 invalid；
- 若 $L_n^{invalid}$ 超限，整条候选视频被拒。

论文实测的拒绝率与此量级相符：Table I 中 Sweeping 仅 **55%** 通过、Pouring **61%**。

---

## 4 · 工程视角

### 4.1 论文报告的运行时剖析（Table II，单条代表性 trial）

**配置**：153 帧、$640\times480$ 生成视频，从 3 个物体部件采样 18 个语义锚点。

| 模块 | 设备 | 时间 |
|---|---|---|
| 视频生成 / 预处理 | Cloud/GPU | **185.5 s** |
| 锚点生成（VLM grounding） | Cloud/API + GPU | **224.8 s** |
| CoTracker | GPU | 7.41 s |
| PnP/RANSAC | CPU | 0.204 s |
| AnyGrasp | GPU | 2.1 s |
| IK + 平滑 | CPU | 0.5 s |
| **总延迟** | Mixed | **420.5 s** |

**核心工程结论（论文自陈）**：
- 延迟被**云端视频生成（185.5 s）与 VLM grounding（224.8 s）**主导，两者合计约占总延迟的 97.6%；
- 本地几何与机器人侧模块都极轻量（PnP/RANSAC 仅 0.204 s）；
- 「future runtime improvement should mainly focus on faster video generation, local or cached VLM grounding, and parallel candidate evaluation, rather than on the rigid-geometric verification itself.」

### 4.2 关键约束与 trade-off

| 维度 | 数值 / 约束 | 来源 |
|---|---|---|
| 端到端延迟 | 420.5 s（单 trial，含云端） | Table II（论文报告） |
| PnP/RANSAC 单次 | 0.204 s（CPU） | Table II（论文报告） |
| RANSAC 内点阈值 | ≈ 8 px | §IV-B-1（论文报告） |
| 接受阈值 | $\epsilon_{mean}=5$ px，$\epsilon_{max}=12$ px | §IV-B-1（论文报告） |
| 深度补偿幅度 | $\lambda_d\in[0.3,0.5]$，$d_{max}\in[0.005,0.01]$ m | §IV-C-2（论文报告） |
| IK 回检阈值 | 位置 0.01 m，姿态 0.40 rad | §IV-C-1（论文报告） |
| 每部件锚点数 | $K_m=5$ | §IV-A-1（论文报告） |
| 生成候选数 | 每任务 5 个 | §IV-A-2（论文报告） |
| 控制频率 / FPS | **论文未报告** | — |
| 显存 / VRAM | **论文未报告** | — |
| GPU 具体型号 | **论文未报告**（表中仅标 "GPU"/"Cloud/GPU"） | — |
| 单次试验的重规划次数 | **论文未报告** | — |

### 4.3 部署含义

1. **不是闭环控制器**。整条轨迹在执行前离线生成完毕（视频生成 + 验证 + IK），Phase 5 只在执行时叠加一个被 clip 到 ±0.005–0.01 m 的单轴修正。论文明确否定了"full online visual servoing / task-level replanning"的读法。
2. **失败即安全停机**。Eq.15 的判据不满足时，"no robot trajectory is executed"——这是一个 fail-safe 而非 fail-operational 的设计。
3. **云端依赖是最大部署瓶颈**。要落地必须把 Kling 1.6 与 VLM grounding 本地化或缓存化，或者接受**秒级到分钟级的任务级重规划周期**。
4. **并行候选评估**是论文自己点出的优化方向（5 个候选目前是串行评估？论文未报告并发策略）。

---

## 5 · 数据与评测

### 5.1 数据构成

| 项目 | 内容 |
|---|---|
| 硬件 | 真实 **RM75** 机械臂 + 平行夹爪 + **Intel RealSense** RGB-D 相机（论文报告） |
| 任务 | **Pouring / Lifting / Tool Delivery / Sweeping** 四项桌面操作（论文报告） |
| 试验数 | 每任务 **20** 次真机试验（论文报告） |
| 评估是否用公开数据集 | **否**；全部为真机自采试验，论文未报告任何公开 benchmark 名 |
| 生成视频模型 | **Kling 1.6**，每任务 5 个候选（论文报告） |
| 点追踪器 | **CoTracker**（论文报告） |
| 分割 | **SAM**（论文报告） |
| 抓取 | **AnyGrasp**（论文报告） |
| 可行性检查 | **PyBullet IK + RM75 URDF**（论文报告） |

**成功的判据（论文原文语义）**：机器人完成预期操作，且不丢失物体、不违反目标交互、不产生不可恢复的执行漂移。

### 5.2 评测设置（讲条件）

**Baselines 是"风格复现"，不是原论文直接比对**：论文明确说三个 baseline 是 "reproduced baseline variants"，且共享**同一个 RM75、同一 RGB-D 相机、同一物体集合、同一 AnyGrasp 抓取源、同一 IK 检查器、同一执行接口**。因此论文声称"性能差异主要反映运动迁移机制，而非抓取检测或底层控制差异"。

- **ReKep-style**：关系关键点约束优化
- **RIGVid-style**：生成视频 6D 物体轨迹重定向
- **NovaFlow-style**：dense actionable flow 重定向

### 5.3 结果数字（逐字来自正文/表格）

**Table I — 生成轨迹过滤**

| Task | Avg. samples | Pass rate | Mean reproj. err. |
|---|---|---|---|
| Pouring | 2.1 | 61% | 3.4 px |
| Lifting | 1.6 | 74% | 2.8 px |
| Tool Delivery | 1.9 | 68% | 3.1 px |
| Sweeping | 2.4 | 55% | 4.0 px |

**Table III — 刚体几何一致性过滤消融**

| Setting | Pouring | Lifting | Delivery | Sweeping |
|---|---|---|---|---|
| w/o filter | 75% | 80% | 70% | 60% |
| GenVid2Robot | **90%** | **90%** | **85%** | **80%** |

**Table IV — 锚点选择与 PnP 诊断**

| Point selection | Survival | Valid PnP | Reproj. err. |
|---|---|---|---|
| Random points | 72.4% | 68.1% | 6.7 px |
| Uniform mask points | 81.6% | 78.9% | 5.1 px |
| Semantic anchors | **91.8%** | **90.5%** | **3.6 px** |

**失败统计（§V-E，逐字）**：80 次 GenVid2Robot 试验中，**69 次成功，11 次失败**；失败构成：**8 次 workspace-limit、2 次 excessive keypoint-loss、1 次 grasp-execution error**。

> 一致性交叉验证（我的算术核对，非论文原文）：Table III 四个任务的 90%/90%/85%/80% 对应 20 次中的 18/18/17/16，合计 **69/80**，与 §V-E 的 69 成功完全吻合。

**Figure 4 的具体柱状数值**：论文正文只给方向性描述（"achieves the highest success rate across all tasks"），**未在正文给出逐 baseline 的数值**——如需精确对比需读图，本笔记不臆测。

---

## 6 · 能力与失败模式

### 6.1 能做（有实证支撑）

| 能力 | 证据 |
|---|---|
| 从单张 RGB-D + 语言指令出发，无需 CAD / 无需物体扫描 / 无需物体专属物理演示 | §III、§I 贡献声明 |
| 拒绝"视觉合理但几何不可迁移"的生成视频 | Table I：pass rate 55–74%，说明确实在拒；且被拒原因是 keypoint drift / non-rigid artifacts / severe occlusion / unstable sparse rigid motion |
| 把相对运动正确挂到真实抓取位姿上，而非复制物体中心轨迹 | Eq.18 + §VI 明确"object and TCP trajectories are not expected to overlap" |
| 对**适度初始布局扰动**鲁棒 | §V-D + Fig.5/Fig.6(a)：因为每帧从当前 RGB-D 重建锚点、从当前抓取位姿归纳 TCP，而非回放固定物体中心路径 |
| 有界深度补偿降低执行时深度方向漂移 | §V-D + Fig.5(d) |
| 一致性过滤显著提升成功率（尤其连续旋转/接触丰富的任务） | Table III：Pouring 75→90、Sweeping 60→80 |

### 6.2 不能做（论文自陈 + 失败分析）

1. **全局可达性与可操作度无法保证**。8/11 失败是 workspace-limit failure——生成运动通过了刚体一致性检验，但归纳出的 TCP 轨迹逼近 RM75 的可达边界、近奇异姿态或易碰撞区域。论文原话：稀疏刚体几何一致性"does not by itself guarantee global reachability, manipulability, or collision-free execution along the entire robot trajectory"。
2. **严重遮挡 / 大幅外观变化 / 边界歧义 → 2D–3D 对应不足**。2 次 excessive keypoint-loss 失败。此时系统会拒绝而非发出不稳定轨迹。
3. **接触级不确定性无法消除**。1 次 grasp-execution error，来自局部深度噪声或小幅接触扰动。
4. **图像平面内的大幅位移不支持**。深度补偿只沿相机 z 单轴，"does not compensate for arbitrary lateral displacement in the camera X–Y plane"。若物体/目标在图像平面内大幅移动，当前轨迹视为无效，必须**从新的 RGB-D 观测重新初始化并重新生成/验证**。
5. **纹理less / 对称 / 分布不良的锚点区域 → 稀疏 PnP 不稳定**（§VI 自陈）。
6. **严重形变、错误任务语义、强遮挡、可见锚点不足 → 依赖生成视频质量而失败或被拒**。

### 6.3 隐含假设 (Hidden Assumptions)

| # | 假设 | 出处 | 被打破时的后果 |
|---|---|---|---|
| A1 | 短时操作时域内，任务相关物体区域可由**稀疏刚体锚点集**近似 | §III-A 第一条 | 形变物体（布、软管、液体表面）→ 非刚体运动被 filter 拒绝；或残差被"平均"掩盖 |
| A2 | 抓取后 **TCP 与被操作物体近似局部刚体关系** | §III-A 第二条 | 夹爪内打滑 → 归纳出的 TCP 轨迹系统性错误；深度补偿修不了 |
| A3 | 生成视频几何与真实执行的差异**只需沿相机 z 单轴、有界补偿** | §III-A 第三条 + §IV-C-2 | 图像平面 XY 漂移、侧向接触扰动 → 完全不补偿，需重初始化 |
| A4 | 首帧 RGB-D 深度有效且相机-基座标定 $\mathbf{T}_{b,c}$ 准确 | §III Eq.1/Eq.5 | 标定残差直接进入全部 3D 锚点 → 全局偏置；深度无效像素被 $\mathbf{D}_0>0$ 过滤但会减少锚点数 |
| A5 | 生成视频中追踪到的 2D 点与首帧锚点是**同一物体的同一语义部件** | §IV-A-2（"Only anchors initialized from the object region are used"） | 生成视频改变物体身份/形状（Kling 常见）→ VLM 筛选兜底，但筛不掉细微身份漂移 |
| A6 | 相机相对基座固定（$\mathbf{T}_{b,c}$ 在整个 trial 内不变） | Eq.5 单次标定 | 相机移动/机械臂遮挡相机 → 基座系变换失效 |
| A7 | 至少 4 个有效锚点且 3D 点**不近共线 / 分布不差** | §IV-B-1 | 细长物体（工具手柄、扫帚杆）→ 锚点近共线 → PnP 退化 → 帧无效累积 → 整条候选被拒 |
| A8 | **逐帧 IK 可行 ⇒ 整条轨迹可行** | §IV-C-1（仅做逐帧 IK + FK 回检） | 帧间关节空间不连续、动态奇异性 → 正是 8 次 workspace-limit 失败的机制 |
| A9 | 任务成功可由"不丢物 / 不违反目标交互 / 无可恢复漂移"三个二元判据刻画 | §V-A | 部分成功、任务质量（倒水量多少）这类连续指标被忽略 |

---

## 7 · 与相关工作对比

### 7.1 定位对比表

| 方法 | 运动先验来源 | 中间表示 | 是否显式证明几何一致性 | 轨迹锚点 | 执行期反馈 |
|---|---|---|---|---|---|
| **ReKep**（style） | VLM 生成关系关键点约束 | 关键点约束优化 | 否（约束层面） | 约束求解结果 | 论文未报告 |
| **RIGVid**（style） | 生成视频 | 6D 物体轨迹 | 否（靠 VLM 筛选 + 直接重定向） | 物体轨迹 → 重定向 | 论文未报告 |
| **NovaFlow**（style） | 生成视频 | dense actionable object flow | 否 | flow 重定向 | 论文未报告 |
| **FoundationPose**（对照） | — | canonical 物体 6D pose | —（但需 CAD/参考视图） | — | — |
| **GenVid2Robot** | 生成视频（Kling 1.6） | **首帧 RGB-D 稀疏锚点的相对 SE(3) 运动** | **是**：PnP/RANSAC + 重投影双阈值 gate | **真实抓取时刻 TCP 位姿** | 有界单轴深度补偿（RealSense） |

**论文给出的 baseline 失败模式（定性，逐字语义）**：
- ReKep-style：倾向于**欠定连续旋转**（"under-specify continuous rotation"）；
- RIGVid-style：对**视觉漂移与抓取对齐误差**敏感；
- NovaFlow-style：在没有显式稀疏刚体 SE(3) 一致性的情况下**累积轨迹漂移**。

**GenVid2Robot 的差异化三点**：
1. 生成视频只被当作**假设**，须过几何 gate 才能进入执行；
2. **不用 CAD 规范物体坐标系**，恢复的是相对锚点集运动先验；
3. 轨迹从**真实抓取位姿**归纳，因此物体轨迹与 TCP 轨迹**本就不应重合**。

### 7.2 面试 Tip

> **如果被问"这篇和 RIGVid / NovaFlow 的本质区别是什么？"**
>
> 别答"它更准"。答：**它改变的是生成视频在系统中的认识论地位**。RIGVid/NovaFlow 把生成视频当"可执行的伪演示"，直接从里面提轨迹或 flow 重定向；GenVid2Robot 把它当"待验证的 2D 运动假设"，要求这段 2D 运动能被首帧 RGB-D 3D 锚点的**同一个** SE(3) 变换重投影解释（$e_{mean}<5$px、$e_{max}<12$px），不通过就不发给机器人。第二个区别是**轨迹锚点从物体中心换成真实抓取 TCP 位姿**——这样可执行的腕部运动才能随抓取位置和机器人运动学变化。代价是：它仍不解决全局可达性（8/11 失败都是 workspace-limit），而且总延迟 420.5 s 里 96% 花在云端生成与 VLM grounding 上，本地几何验证只占 0.204 s。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-16)

**Repo 状态说明（诚实标注）**：本篇论文正文中**未出现任何指向作者代码仓库的 `github.com` 链接**（截断文本中出现的 "Report GitHub Issue" 是 arXiv HTML 页面自带的反馈按钮，不是论文仓库信号）。因此**无官方 repo、无社区 issue 流可供验证**。以下 3 条 pitfall **由 §6 失败模式 + §2/§4 的方法约束机械推导**，未经 issue 验证，标注为 `UNVERIFIED`。

---

**Pitfall 1 — 细长/近共线物体的锚点退化会让整条候选被静默拒绝** `UNVERIFIED`

- **失败模式来源（§6.2 第 5 条 / 隐含假设 A7）**：论文自陈"sparse PnP can also be unstable for textureless, symmetric, or poorly distributed anchor regions"。
- **方法约束来源（§IV-B-1）**：PnP 仅在"至少 4 个有效锚点**且首帧 3D 点不近共线/分布不差**"时才执行；退化的帧被标记 invalid，若 $r_n^{valid}$ 太低或 $L_n^{invalid}$ 太大，**整个候选视频被拒**。
- **机械推论**：对 Tool Delivery（工具手柄）与 Sweeping（扫帚杆/长条物）这类物体，若 VLM 只给出一个部件提示且该部件是细长形状，深度感知 K-Means 的 $K_m=5$ 个中心会沿主轴排布 → 3D 点近共线 → PnP 反复退化 → 有效帧比例崩掉 → 5 个候选可能全被拒 → 触发 Eq.15 的 "no robot trajectory is executed"。
- **可操作建议**：在锚点采样后**显式加一个可观测性检查**（如 3D 点协方差的最小特征值 / 条件数阈值），退化时主动扩到第二个部件掩码或提高 $K_m$，而不是等到 Stage 2 才发现全候被拒。

---

**Pitfall 2 — 深度补偿只覆盖相机 z 轴，图像平面漂移会直接把任务做废且系统无法自恢复** `UNVERIFIED`

- **失败模式来源（§6.2 第 4 条 / 隐含假设 A3）**：论文原文"it does not compensate for arbitrary lateral displacement in the camera X–Y plane"，且"if the object or target region moves substantially during execution, especially in the image plane, the current trajectory is regarded as invalid and the system must reinitialize"。
- **方法约束来源（§IV-C-2）**：修正项为 $\mathbf{p}_{cmd}^{(t)}=\bar{\mathbf{p}}_{tcp}^{(t)}+\mathrm{clip}(\lambda_d e_d^{(t)},-d_{max},d_{max})\mathbf{r}_b$，其中 $\mathbf{r}_b=\mathbf{R}_{b,c}[0,0,1]^\top$ **只有 z 分量**，且 $d_{max}$ 仅 0.005–0.01 m。
- **机械推论**：抓取后物体若因夹持不稳沿图像平面滑移 1–2 cm（远超 $d_{max}$ 上限 1 cm 且方向正交于补偿轴），补偿量恒为 0，轨迹完全按原样执行。而"重新初始化"意味着整条 pipeline 重跑一遍——**按 Table II 是 420.5 s**。
- **可操作建议**：把 Phase 5 从"单轴 clip"扩成"图像平面残差检测 + 阈值触发重规划"，或至少在图像平面残差超阈时**立刻停机**而非继续执行一条已知失效的轨迹。

---

**Pitfall 3 — 逐帧 IK 可行 ≠ 轨迹可行，导致 workspace-limit 成为主导失败类型** `UNVERIFIED`

- **失败模式来源（§6.2 第 1 条 / 隐含假设 A8）**：80 次试验中 **8/11** 的失败是 workspace-limit failure；论文原文自陈几何一致性"does not by itself guarantee global reachability, manipulability, or collision-free execution along the entire robot trajectory"。
- **方法约束来源（§IV-C-1）**：可行性检查是"每帧用前一帧解初始化 IK"，帧可行判据仅三条——FK 回检的位置阈值 **0.01 m**、姿态阈值 **0.40 rad**、关节限位；随后做 CubicSpline + Savitzky–Golay 平滑，**再**做一次 FK 回检。系统里**没有任何全局可达性 / 可操作度 / 碰撞代价**进入候选打分（Eq.16 的 $C_n$ 只含重投影与平滑项；Eq.17 的 $S_j$ 只含抓取置信、掩码一致性、可达/近奇异惩罚、碰撞惩罚——注意 $E_r,E_c$ 是**抓取位姿层**的，不是**轨迹层**的）。
- **机械推论**：一条轨迹可能每一帧都过 IK 阈值，但整条轨迹贴着 RM75 工作空间边界或穿过近奇异区，关节速度爆掉、跟踪误差累积；由于 gate 只看重投影残差，这条轨迹在 Stage 2 是"通过"的，失败只会在真机执行时暴露，且论文的失败分类显示这是**最大单一失败源**。
- **可操作建议**：把 $E_r$（reachability / near-singularity）从"抓取位姿打分"提升为"**整条轨迹的后置过滤**"——对 $\{\tilde{\mathbf{T}}_{b,tcp}^{(t)}\}$ 计算关节空间条件数 / 可操作度椭球体积的时间序列，超阈直接回退到次优候选 $n$。

---

**Atlas 联动小结**

| Pitfall | 根因（§6 失败模式） | 触发约束（方法级） | 论文可查证据 |
|---|---|---|---|
| 1 锚点退化静默拒绝 | 稀疏 PnP 对纹理less/对称/分布不良区域不稳定 | ≥4 非共线锚点 + 全候拒绝即停机 | §IV-B-1, §VI |
| 2 单轴补偿盲区 | 不支持图像平面大幅位移 | $\mathbf{r}_b$ 仅 z 分量，$d_{max}\le 0.01$ m | §IV-C-2, §VI |
| 3 逐帧 IK ≠ 轨迹可行 | workspace-limit 占 8/11 失败 | 无轨迹级可达性/可操作度代价项 | §IV-C-1, §V-E |

---

[← Back to Robot Manipulation README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.09191 -->
