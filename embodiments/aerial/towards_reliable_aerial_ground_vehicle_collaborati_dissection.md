<!-- ontology-5axis
problem: navigation
representation: n/a
sensor: multi-modal
paradigm: learned
time: per-scene
ref: ../../cheat-sheet/ontology.md §5
-->

# 面向可靠空地协同的集成规划与自主框架 (Towards Reliable Aerial–Ground Vehicle Collaboration: An Integrated Planning and Autonomy Framework for Field Deployment)

> **发布时间**：2026-07-07（arXiv:2607.07350v1 [cs.RO]）
> **论文 / 模型名**：Integrated Planning and Autonomy Framework（DRL mission planner + RARP）
> **核心定位**：把"续航受限 UAV + 移动充电 UGV"的耦合路径规划问题，从纯算法做成一套能上真机的端到端 pipeline——DRL 规划器优于启发式基线，YAML 任务 API 打通异构平台，在线重规划器把能量越界率从 83.33% 压到 20.00%。

导语：空中平台看得快但飞不久，地面平台跑得久但受路网约束，把两者绑成"移动充电桩"是常识，难点在于**同时**决定 UAV 访问顺序、UGV 路网走位、会合点(rendezvous)的时空同步，还要在真机风扰/传感噪声/通信延迟下不炸机。本文的结论是：好的全局规划 + 标准化接口 + 在线重规划三者缺一不可，缺了在线重规划，83.33% 的临界 sortie 会越界。

---

## X-Ray 开场

这篇论文解决的是"UAV 续航太短、UGV 可以当移动充电宝"场景下的**协同路径 + 会合调度**问题，并把它一路做到户外真机跑通。它提出了三样东西：一个 encoder–decoder Transformer 的 DRL 规划器（联合决定 UAV 访问序列和会合 RNP）、一个两层 YAML 任务 API（把规划输出变成可执行动作）、以及一个轻量在线 Rendezvous-Aware Replanner（RARP，应对执行期时序漂移）。对 Spatial AI 研究者来说，它的意义不在网络结构（Transformer 路由是老套路），而在于**"学习式规划 + 标准化接口 + 在线安全层 + 真机验证"这套配方**，以及它明确指出的短板：依赖高精度 GNSS、最终降落还是手动的、重规划是纯反应式的。

---

## 📍 研究全景时间线

```
空地协同路线演进
────────────────────────────────────────────────────────────────────►
2016            2019-2021              2022-2023           2024      2026(本文)
  │                │                      │                  │          │
[Michael 等]   [Tokekar 等]        [Maini 等 18,19]      [Cladera 等]  [本文]
地震废墟        信息论共生传感      燃料受限+            LLM 语义      DRL规划+
空-地联合        无人机回收充电      多级启发式          任务解析      YAML API+
建图            (symbiotic)        "UGV first,                    RARP在线重规划+
                                    UAV second"                    PX4/Nav2真机验证
                                                                   50m×50m户外
  │                │                      │                  │          │
 [Leahy 等]      [Fankhauser 等]     [Daly 等]           [Lee 等]
 时序逻辑规划    UAV建高程图         移动地面平台上        机载检测动态
 但仅室内动捕    助腿足机器人        精确降落(通信延迟)    生成UGV可通行路径
                                    │
                        【缺口】理论严谨的"脆"，能落地的"依赖静态行为/人工监督"
                                    ↓
                        【本文】端到端：优化规划 → 平台化执行 → 在线重规划 → 真机验证
```

**本文位置**：它是"算法 → 部署"这条缝里的一次缝合尝试，贡献重心明确放在**集成与真机部署**（论文自己说 DRL 策略设计的细节见其前作 [30,31]）。

**本文局限（论文自陈 + 推断）**：
- 只处理 **1 UAV–1 UGV** 单对，未做多机去中心化协同。
- RARP 是**反应式**树搜索 + 路径裁剪，不做扰动预测（无主动重规划）。
- **依赖高精度 GNSS** 做定位与会合，GPS-denied / 对抗环境未覆盖。
- 野外最终精确降落是**手动**的，视觉自主降落仅在 Gazebo SITL 中验证。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| **Encoder**（3 层 MHSA, 8 heads, 128-d） | 任务点特征 $o_i=(x_i,y_i,b_i)$（AOI 与 RNP） | 上下文化嵌入 $h_i^L$ | 训练/推理同结构；权重随策略更新 |
| **Decoder**（自回归，glimpse attention） | UAV 当前位置嵌入 + 全点均值嵌入 + 归一化油量 $f_t$ | 下一步动作分布 $\pi_\theta(a_t\|s_t)$ | 训练：**采样**动作（探索）+ 可行性 mask；推理：greedy 或 N 次采样取最优 |
| **训练目标**（REINFORCE + greedy baseline） | 采样轨迹 cost $c$ 与 baseline cost $c'$ | 策略梯度 $(c-c')\nabla_\theta\log\pi_\theta$ | baseline 用 paired t-test 保守更新（$\phi\leftarrow\theta$ 仅在显著优于时） |
| **YAML Mission API** | state-level YAML（agent 位置、AOI/RNP、连通性） | action-plan YAML（action_type / location / ins_id / end_time） | 无训练；纯接口层 |
| **UGV Stack**（ROS 2 + Nav2） | action-plan 指令 + GNSS/IMU/LiDAR | Smac Hybrid-A\* 全局路径 + MPPI 局部速度指令 | 无训练；双 EKF（local odom / global map） |
| **UAV Stack**（PX4 + MAVSDK） | action-plan 指令 + GPS 目标点 | offboard 速度设定点（20–50 Hz） | 无训练；比例速度控制 |
| **RARP**（Algorithm 1） | UAV/UGV 状态、当前计划、路网 $\mathcal{G}$、已耗时、续航、安全裕度 $\alpha$ | 更新后的双机计划，或紧急降落 | 无训练；在线反应式搜索 |

### 1.2 关键机制

⚡ **Eureka Moment**：**把"任务完成时间最小化"整体建模成一个"空间路由 × 时间充电"耦合的 MDP，用一个共享贪心 baseline 的 REINFORCE 策略同时吐出访问序列与会合 RNP；再用一个几乎零成本的反应式重规划层（RARP，靠"裁剪动作前缀 + 在路网里重挑可行会合点"）把执行期时序漂移挡在安全裕度之外。**

三处真正的工程洞见：
1. **Encoder 把 AOI 和 RNP 放进同一个点集**，用 $b_i\in\{0,1\}$ 区分节点类型——一个注意力机制同时推理"去哪访问"和"去哪充电"两种语义。
2. **两级 YAML API + `ins_id` 同步标识**：把规划器输出压成最小可执行动作原语，`takeoff_from_UGV` ↔ `allow_takeoff_from_UGV`、`land_on_UGV` ↔ `allow_land_on_UGV` 通过匹配的 `ins_id` 对齐，是异构平台协同的关键抽象。
3. **RARP 的四阶段降级**：检查 → 回滚裁剪 → 放松裕度(0.90→0.95) → 紧急降落，形成一条明确的"兜底链"。

### 1.3 信息流 / 架构图

```
        ┌────────────────────────────────────────────────────────────┐
        │             中央任务管理器（笔记本, Ubuntu 22.04）              │
        │   Mission Planner (DRL)  +  RARP (在线重规划)                 │
        └───────┬───────────────────────────────────────┬────────────┘
                │ action-plan YAML (UDP 广播)              │ 遥测 30–50 Hz
                ▼                                        ▼
   ┌──────────────────────┐                   ┌──────────────────────┐
   │   UAV (X500 quad)     │                   │   UGV (Clearpath     │
   │  Pixhawk 6C / PX4     │◄── takeoff/land ─►│   Husky)             │
   │  Jetson Nano + MAVSDK │   握手(ins_id)     │  Jetson Nano + ROS 2 │
   │  GNSS/IMU/RGB cam     │                   │  GNSS/IMU/SICK LiDAR │
   └──────────────────────┘                   └──────────────────────┘
        │ 20–50 Hz offboard 速度                    │ Nav2: Smac Hybrid-A*
        ▼                                          │ 20–30 Hz MPPI
   NED 比例速度控制                                 ▼
                                              运动学可行轨迹(公差 0.3m)
```

**Planner 内部数据流（Fig. 2）**：
```
任务点 o_i=(x_i,y_i,b_i) ─► Linear embed(128-d) ─► 3×MHSA ─► h_i^L
                                                              │
UAV 当前位置 emb ┐                                            │ (encoder 输出)
全点均值 emb     ├─► context(query) ─► glimpse attention ─────┘
归一化油量 f_t   ┘         │
                           ▼
                    clip(±10) ⊙ 可行性 mask ─► softmax ─► a_t
                                                            │
                       循环至所有 AOI 访问完 + 返航充电 ◄────┘
```

---

## 2 · 数学核心

📌 **Napkin Formula**：**“在油量约束下，谁先访问、去哪充电，让总任务时间最短。”**

$$\min_{\pi_a,\pi_g} T_{\text{mission}}\quad \text{s.t.}\quad t_{\text{sortie}}\le F_a,\ \ \pi_g\subseteq G,\ \ U_a,U_g\ \text{same RNP & time},\ \ M\ \text{fully serviced}$$

**目标 → 公式 → 变量 → 直觉：**

**① 主优化问题（Eq. 1）**
- $T_{\text{mission}}$：从 UAV 起飞到最终充电的总时长。
- $F_a$：UAV 飞行续航上限；$t_{\text{sortie}}$：单次 sortie 飞行时间。
- $G$：路网图（顶点=RNP，边=可行地面轨迹），$\pi_g$ 必须落在 $G$ 上。
- 直觉：这不是两台车各跑各的，而是"UAV 的路线被 UGV 的路网到达能力**反向约束**"——UAV 能飞多远，取决于 UGV 能不能按时到会合点。

**② Encoder 注意力（Eq. 2）**
$$\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\!\Big(\tfrac{QK^T}{\sqrt{d_k}}\Big)V$$
让每个任务点 attend 所有其他点，学到 AOI 簇、到充电节点的距离、可行会合点分布等空间依赖。

**③ 带 mask 的策略分布（Eq. 3）**
$$\pi_\theta(a_t\mid s_t)=\operatorname{softmax}\big(\operatorname{clip}(h_t)\odot m_t\big),\quad \operatorname{clip}\in[-C_p,C_p],\ C_p=10$$
- $m_t$：可行性 mask（已访问 AOI、当前不需要的充电点被置零）。
- 直觉：**用掩码把非法动作直接掐死在 logit 层**，避免策略学到"先访问已去过的点"这种蠢行为。

**④ REINFORCE 策略梯度（Eq. 4）**
$$\nabla_\theta J(\theta)=\mathbb{E}_{\tau\sim\pi_\theta}\big[(c-c')\nabla_\theta\log\pi_\theta(\tau)\big]$$
- $c$：采样策略的轨迹 cost；$c'$：共享结构贪心 baseline 的 cost。
- 直觉：**用贪心解当"及格线"，只奖励比它强的那部分动作**；baseline 只在 paired t-test 显示显著提升时才更新，是个带统计门的方差缩减。

**⑤ RARP 剩余续航（Algorithm 1, line 1）**
$$T_{\text{rem}}=\alpha\,T^{\text{full}}-T^{\text{ela}}$$
- $\alpha$ 默认 0.90（Phase 3 放宽到 0.95），$T^{\text{full}}$=满电续航，$T^{\text{ela}}$=已耗时。
- 直觉：**安全裕度是硬顶**——先扣掉 10% 不敢用完，再用剩余量去问"我还够不够飞到会合点"。

---

## 3 · 带数字走一遍（玩具设定，非论文数据）

**设定**：$T^{\text{full}}=100$ s，$\alpha=0.90$ → 初始有效预算 $T_{\text{rem}}=90$ s。planned sortie 原计划 88 s，逼近 90 s 红线。规划序列：$v_1\!\to\!v_2\!\to\!\dots\!\to\!v_5\!\to\!\text{RNP6}$ 充电。

**Step 0 — 正常执行（Phase 1 检查通过）**
- 若 $T_{\text{ela}}=0$，$T_{\text{rem}}=90$。UAV 完成计划需 88 s，UGV 到 RNP6 需 60 s。
- $\max(88,60)=88\le 90$ → 返回原计划，**不重规划**。

**Step 1 — $v_1$ 后延误（触发重规划）**
- 假设 $v_1$ 因风延迟，执行到此刻 $T_{\text{ela}}=40$ s（原计划此处只该花 30 s，漂移 +10 s）。
- $T_{\text{rem}}=90-40=50$ s。
- Phase 1：UAV 走完剩余 $v_2\!\to\!v_5$ + 到 RNP6 还需 55 s > 50 s → **原会合点 RNP6 不可行**。
- Phase 2 回滚：从 $i=|\mathcal{A}^{\text{uav}}|$ 向下裁。
  - 裁到 $v_5$ 后（即只走到 $v_4$），$T_{\text{pref}}=30$ s，$T_{\text{rem}}'=50-30=20$ s。
  - 查可行会合集 $\mathcal{V}_{\text{feas}}$：哪些 RNP 双方都能在 $T_{\text{rem}}$ 内到达。RNP8 距 $v_4$ 终点 UAV 需 18 s ≤ 20 s ✓，UGV 需 45 s。
  - 选 $v^*=\arg\min_{v} T_{\text{ugv}}(p^{\text{ugv}}\!\to\!v)$ → 在候选中取 UGV 最快能到的那个（此处 RNP8）。
- 输出 $\tilde{\mathcal{A}}^{\text{uav}}=\{v_1,\dots,v_4\}\oplus\text{Path}(v_4\!\to\!\text{RNP8})$，$\tilde{\mathcal{A}}^{\text{ugv}}=\text{ShortestPath}_G(p^{\text{ugv}}\!\to\!\text{RNP8})$。

**Step 2 — 第二次延误（$v_2$ 后）**
- 再次漂移，裁掉 $v_4$ 即可恢复可行，会合点仍留在 RNP8。
- 对应论文 Fig. 5：第一次裁 $v_5$ 改到 RNP8，第二次裁 $v_4$ 维持 RNP8。

**Step 3 — 若全部失败**
- Phase 3：$\alpha\leftarrow0.95$，$T_{\text{rem}}=95-40=55$ s，重算再试一次。
- Phase 4：仍失败 → UAV 就地 `Land`，UGV 走最短路径去 UAV 落点。

**结论直觉**：RARP 不做全局重优化，只做**"前缀裁剪 + 会合点重选"**这种 O(计划长度) 的贪心修补——便宜到可以在线跑，但只在"漂移不致命"时有解。这正是它把越界率从 83.33% 降到 20.00%（论文 Table IV）却**降不到 0** 的原因。

---

## 4 · 工程视角

| 维度 | 论文给出的值 | 备注 |
|---|---|---|
| 规划器训练硬件 | NVIDIA RTX 4090 Ti GPU | 论文明确给出 |
| 训练量 | 5,120,000 instances，batch 256，100 epochs | 三个规模 U15G5 / U30G10 / U45G15 |
| 优化器 | Adam，lr $10^{-4}$，每 epoch 指数衰减 0.995 | — |
| **规划器推理延迟** | DRL(greedy) **0.23 / 0.28 / 0.33 s**（U15G5/U30G10/U45G15） | Table I |
| | DRL(1024) **0.24 / 0.46 / 0.56 s** | 采样 1024 条取最优 |
| | DRL(10240) **2.44 / 4.60 / 6.38 s** | 采样 10240 条 |
| | DRL(greedy) **0.378 / 0.41 s**（U60G20/U75G25） | Table II |
| | DRL(1024) **0.83 / 1.04 s**；DRL(10240) **8.12 / 10.10 s** | Table II |
| 启发式基线延迟 | **0.01 s**（U15G5/U30G10）、**0.08 s**（U45G15）；**0.18 / 0.30 s**（大场景） | Table I & II |
| UAV offboard 速度指令频率 | 20–50 Hz | §V-B2 |
| UGV MPPI 局部控制频率 | 20–30 Hz | §V-B1 |
| UGV 到点公差 | 0.3 m | §V-B1 |
| 遥测更新率 | 30–50 Hz（5 GHz Wi-Fi） | 硬件网络 |
| 充电服务时长 $T_R$ | 30 sec（模拟充电） | §VI-C |
| 单机算力 | UAV / UGV 各一块 **NVIDIA Jetson Nano** | §VI-A |
| **真机端到端延迟** | **论文未报告** | 只给了控制频率，没给规划→执行闭环延迟 |
| **规划器在 Jetson 上的运行时间** | **论文未报告** | 规划器实际跑在中央笔记本，非机载 |
| **内存占用 / 吞吐** | **论文未报告** | — |

**部署约束与 trade-off：**
- **延迟 vs 质量**的三角非常清晰：greedy 最快但 gap 6–14%；1024 采样 gap ≤2.3%，延迟一个数量级内；10240 拿到 gap≈0 但延迟 $\times 10$。工程上 **1024 是甜点**（论文也这么说）。
- **规划器不在机载**：Mission Planner 与 RARP 都跑在**中央笔记本**上，UAV/UGV 只跑执行栈。这意味着**系统存在单点依赖**——笔记本挂了或 Wi-Fi 断了，整队失去协调能力。
- **重规划是事件驱动 + receding-horizon**：只在每次 rendezvous 事件或执行偏离计划 `end_time` 时触发，不是每帧重规划，这压低了在线算力需求。

---

## 5 · 数据与评测

### 5.1 规划器训练 / 评测（Table I & II）
- **问题规模（逐字）**：训练用 **U15G5、U30G10、U45G15**（对应 15/30/45 AOIs 与 5/10/15 RNPs）；泛化测试用 **U60G20、U75G25**。
- **数据生成**：**5,120,000 instances** on-the-fly，batch 256，100 epochs（无固定数据集，在线采样合成实例）。
- **基线**：Maini 等 [19] 的分层启发式（"UGV first, UAV second"多级 pipeline）。
- **解码策略**：greedy、DRL(1024)、DRL(10240) 三种。
- **指标**：Obj(min)（任务时间）、Gap(%)（相对最优的次优间隙）、Runtime(sec)。

**关键数字（逐字）：**
| 规模 | DRL(1024) Obj / Gap / Runtime | Heuristic Obj / Gap / Runtime |
|---|---|---|
| U15G5 | 39.0 / 0.8% / 0.24 s | 43.9 / 13.5% / 0.01 s |
| U30G10 | 61.9 / 2.3% / 0.46 s | 70.4 / 16.3% / 0.01 s |
| U45G15 | 74.6 / 1.7% / 0.56 s | 83.5 / 13.9% / 0.08 s |
| U60G20 | 91.5 / 1.9% / 0.83 s | 101.8 / 13.4% / 0.18 s |
| U75G25 | 100.8 / 2.1% / 1.04 s | 109.2 / 10.5% / 0.30 s |

论文陈述：DRL 把启发式 13–16% 的 optimality gap 降到 2.3% 以下；泛化到大场景时比启发式"outperforming ... by 10–13% in mission time"；DRL(10240) 达到 gap=0.0。

### 5.2 RARP 评测（Table IV，Gazebo 仿真）
- **平台**：Clearpath Husky UGV + PX4 SITL UAV，Gazebo。
- **场景**：3 个 mission scenario，每个 **10 AOIs + 8 RNPs**。
- **约束**：UAV 最大续航 **100 sec**，$\alpha=0.9$ → 有效 **90 sec/sortie**。
- **扰动注入**：风阵、GPS 噪声、UAV 标称巡航速度被**故意降低 15%**。
- **指标定义**：risky sortie = 计划时长 > 80 s；energy margin violation rate = risky sortie 执行时长超过 90 s 的比例；deviation rate = 计划 vs 执行的时长偏差百分比。
- **结果（逐字）**：
  - Avg. energy margin violation rate：**83.33%（无重规划）→ 20.00%（有重规划）**
  - Avg. deviation rate：**14.3% → 1.43%**

### 5.3 野外部署设定（§VI）
- **场地**：**50 m × 50 m** 户外区域，**6 个 AOI、5 个 RNP**。
- **续航**：标称 **100 sec**，$\alpha=0.9$ → 有效 **90 sec/sortie**。
- **环境**：平坦草地，中等风（**12–24 km/h**），UAV 巡航高度 **7 m**。
- **充电**：模拟充电，固定服务期 **30 sec**。
- **SAR 场景**：无预设 AOI，按 UAV 相机地面覆盖足迹离散化区域，cell 质心当 AOI；VLM 基于 **OpenAI-4o API** 做危害检测（烟雾、人偶、危险锥）。

⚠️ **诚实标注**：论文**未报告**野外实验的定量成功率 / 定位误差 / 任务时间数值 —— §VI-C 只有轨迹图与能量曲线（Fig. 8）的定性描述。

---

## 6 · 能力与失败模式

### 能做
- **联合规划**：同时决定 UAV 访问序列与 UGV 会合 RNP，最小化总任务时间；在 15–75 个 AOI 场景下 gap ≤2.3%（1024 采样）。
- **泛化到大场景**：训练尺寸从未见过的 U75G25 上仍比启发式好 10–13%。
- **真机端到端执行**：PX4/MAVSDK offboard 飞控 + ROS 2/Nav2 地面导航 + 双 EKF + 25 m 级 LiDAR costmap，在 50m×50m 户外自主完成两 sortie 覆盖 6 个 AOI。
- **动态任务插入**：mid-mission 新增 AOI 时，在 rendezvous 事件触发 receding-horizon 重规划，自动加一个 sortie。
- **在线安全兜底**：RARP 在风扰/GPS 噪声/15% 速度降下把越界率压到 20%。
- **SAR + VLM 危害检测**：无预设 AOI 的覆盖规划 + GPT-4o 图像判读，识别烟雾/人偶/危险锥。

### 不能做 / 失败模式（每条都对应 §4 的具体约束，§8 据此推导 pitfall）
1. **无 GNSS 即失效**：系统"relies on high-precision GNSS for localization and rendezvous"（§VII-B），UAV 用 M10 GNSS、UGV 用 SwiftNav，RNP 坐标也是经纬度→UTM。GPS-denied / 对抗环境直接不成立。
2. **野外最终降落不是自主的**："the final precision landing on the small landing pad is performed manually"，视觉自主降落"validated in Gazebo SITL simulation"而已。所以**野外闭环的最后一厘米仍是人**。
3. **单对单机**：只做 1 UAV–1 UGV；无去中心化协同、无碰撞感知的多机机制。
4. **重规划是反应式的**：RARP 靠"reactive tree search and route trimming"，不预测风/通信延迟，无主动早停；未来工作才提 proactive replanning。
5. **单点中心依赖**：Planner + RARP 跑在**中央笔记本**上，UDP/TCP + 5 GHz Wi-Fi；笔记本或链路失守则协调丢失。
6. **重规划有害性未量化**：Table IV 显示 RARP 后仍有 **20.00%** 越界，本质上"救援失败率仍有 1/5"。
7. **控制层安全裕度是固定常数**：$T_R$=30 s 固定、$\alpha$ 固定 0.90/0.95，不适应动态负载或电池老化。

### 隐含假设 (Hidden Assumptions)
- **路网图 $G$ 先验已知且静态**：$\pi_g\subseteq G$ 是一等约束，但 $G$ 从哪来、是否随场景变化，论文未讨论。
- **GNSS 全程可用且精度达标**：RNP 以经纬度定义，重规划直接拿 GPS 坐标做距离计算。
- **"续航"被简化成"剩余飞行时间"**：能量约束建模为固定时间预算 $T^{\text{full}}$，忽略负载、风况、爬升等对功耗的影响（Fig. 8 能量曲线也是"approximated as remaining flight time"）。
- **充电是模拟的**：固定 30 s 服务期，没有真实充电动力学、没有充电成功率。
- **平坦草地 + 中等风**：地形平坦、12–24 km/h 风，未验证崎岖地形或强风。
- **降落的相对定位可降级**："may rely on vision-based fiducials or manual landing cues"——即自主性是可选项。
- **中央笔记本 = 真值协调器**：遥测 30–50 Hz 假设链路稳定、延迟可控。
- **任务点集有限且任务可完成**：假设所有 AOI 在 UAV 可飞范围内、至少存在一条可行会合链，否则只能紧急降落。

---

## 7 · 与相关工作对比

| 工作 | 规划层 | 自主层级 | 在线重规划 | 真机验证 | 平台 |
|---|---|---|---|---|---|
| Tokekar 等 [10] | 信息论共生传感规划 | 部分（回收充电） | 无 | 有 | UAV-UGV |
| Maini 等 [18,19] | 燃料受限路由 + 会合（**多级启发式**） | 规划为主 | 无 | 有限 | UAV-UGV |
| Leahy 等 [24] | 时序逻辑 + 电池约束 | 形式化规划 | 无 | **仅室内动捕** | 多 UAV |
| Fankhauser 等 [26] | UAV 建高程图助腿足机器人 | 感知辅助 | 无 | 有 | UAV-腿足 |
| Daly 等 [27] | 移动平台上精确降落（含通信延迟） | 子系统 | 无 | 有 | UAV-UGV |
| Cladera 等 [29] | LLM 解析语义任务 | 高层推理 | 无 | 有 | UAV-UGV |
| **本文** | **DRL 联合路由 + 会合（优于启发式）** | **完整执行栈（PX4/Nav2）** | **有（RARP，越界 83.33%→20%）** | **有（50×50 m 户外 + SAR）** | **1 UAV–1 UGV** |

**差异一句话**：前人要么"理论严谨但脆"（Leahy 室内），要么"能跑但依赖静态行为/人工监督"，本文是**第一个把优化规划 → 标准接口 → 在线重规划 → 真机闭环集成到一条 pipeline 上的空地协同框架**（论文自述）。

**面试 Tip（被问到"这篇相比前人强在哪"怎么答）**：
> "它的算法内核（Transformer 路由 + REINFORCE）并不新，真正值钱的是**集成**：三级拆分——全局用 DRL 规划（Table I 显示 gap 从启发式的 13–16% 压到 2.3% 以下），中间用 YAML API + `ins_id` 把异构平台动作对齐，执行期用 RARP 做反应式兜底（Table IV，越界率 83.33%→20%）。所以它的贡献是'让学习式规划第一次在真机户外跑完整闭环'，而不是某个单点 SOTA。**注意它的三个诚实短板：依赖高精度 GNSS、最终降落手动、重规划纯反应式——这三条正好是后续工作的入口。**"

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-22)

**Repo 状态**：论文全文**未出现任何 `github.com` 链接**（仅有视频 `http://tiny.cc/4mrw001`）。因此按反捏造铁律，**不存在官方 repo 可供 issue 联动**。以下 pitfall 全部由 **§6 失败模式** × **论文显式方法约束** 机械推导，**未经 issue 验证**。

---

**Pitfall 1 — GNSS 依赖使系统在遮蔽/对抗场景直接退化**
- 根因（§6-1）：系统"relies on high-precision GNSS for localization and rendezvous"；RNP 以经纬度定义并经 UTM 转换。
- 方法约束（§V-B）：重规划的可行会合集 $\mathcal{V}_{\text{feas}}=\{v\in\mathcal{G}: T_{\text{uav}}(p^{\text{uav}}\to v)\le T_{\text{rem}},\ T_{\text{ugv}}(p^{\text{ugv}}\to v)\le T_{\text{rem}}\}$ 直接以位置可达性计算，无位置即空集。
- **后果**：一旦 GNSS 降级/丢失，$\mathcal{V}_{\text{feas}}=\emptyset$，RARP 会一路降到 Phase 4 **紧急降落**。这不是"性能下降"，是"任务终止"。
- **工程对策**：塞 UWB / 视觉 fiducial 相对定位做 GNSS 备份，正是论文 §VII-B 自己列的 future work。

**Pitfall 2 — 野外自主降落实为手动，宣称的"全自主"名不副实**
- 根因（§6-2）："the final precision landing on the small landing pad is performed manually"；视觉自主降落"validated in Gazebo SITL simulation"。
- 方法约束（§V-B2）：`land_on_UGV` 的相对定位"may rely on vision-based fiducials **or manual landing cues**"——手动 cue 是被写进设计里的合法分支。
- **后果**：端到端野外闭环的**最后一环有人**；如果你按"全自主"复现并期待无人介入，会在 30 inch × 30 inch 小平台上翻车（小落点 + 手动作业 = 高方差）。
- **复现建议**：把"视觉降落"当必须自己补的工程缺口，别当成已交付能力。

**Pitfall 3 — RARP 反应式裁剪在高延迟场景下可能追不上漂移**
- 根因（§6-4）：RARP"restores feasibility through reactive tree search and route trimming"，不预测扰动，无主动早停。
- 方法约束（Algorithm 1）：Phase 2 回滚搜索从 $i=|\mathcal{A}^{\text{uav}}|$ **逐级向下裁前缀**，每级都要重算 $T_{\text{pref}}$、$T_{\text{rem}}'$、$\mathcal{V}_{\text{cand}}$；且只在 Phase 3 放一次裕度（$\alpha$ 0.90→0.95），失败即 Phase 4 降落。
- **后果**：当单次漂移大于"一个动作"的粒度（例如 Wi-Fi 卡顿导致遥测 30–50 Hz 断流叠加风速突增），裁剪粒度不够细 → 直接跳 Phase 3/4。论文实测**仍有 20.00% 越界率**就是这个机制的下限证据。
- **工程对策**：把 $\alpha$ 和 $T_R$ 从固定常数改成在线估计（当前是固定 0.90 / 30 s），并在重规划触发器上做"漂移速率预测"而非"超时即触发"。

**Pitfall 4 — 中央笔记本 + 5 GHz Wi-Fi 是隐藏单点**
- 根因（§6-5）：Mission Planner 与 RARP 都跑在中央笔记本，通过 UDP 广播 action-plan、TCP/UDP 收 30–50 Hz 遥测。
- 方法约束（§V-B3）：replanning 是"event-driven"，由 UAV 或 UGV 发起请求后**由中央 manager 统一重规划再分发**——设计与实现上都假设链路在场。
- **后果**：Wi-Fi 抖动 / 笔记本崩溃时，两机仍在各自执行旧计划，**`ins_id` 握手失配**会累积成会合失败。
- **复现建议**：先在仿真或测试中主动注入链路中断，验证两机的降级行为，而不是默认网络永远在线。

---

[← Back to aerial README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（arXiv:2607.07350v1）· 未在真机复现的数字标 `UNVERIFIED`。§4 中「真机端到端延迟 / Jetson 上规划器运行时 / 内存吞吐」论文未报告，保持空白；§5 数字均逐字取自 Table I / II / IV。§8 因论文无 `github.com` 链接，全部 pitfall 由失败模式 × 方法约束推导，未经 issue 验证。

<!-- source: https://arxiv.org/abs/2607.07350 -->
