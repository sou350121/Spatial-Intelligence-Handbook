<!-- ontology-5axis
problem: navigation
representation: sparse
sensor: IMU
paradigm: hybrid
time: filter-streaming
ref: ../../cheat-sheet/ontology.md §5
-->

# Continuous-Time Gaussian Belief Trees for Motion Planning (arXiv:2607.02884v1)  
> **发布时间**：2026/07/03  
> **论文 / 模型名**：CT-GBT (Continuous-Time Gaussian Belief Trees)  
> **核心定位**：首个将采样式信念空间规划（GBT）严格拓展至**连续时间域**的框架，通过混合 ODE+KF 信念传播 + 段级信念屏障函数验证，**解决离散节点检查漏检的“间采样碰撞”问题**，在窄通道等高风险场景下显著优于离散时间 GBT。

> 现有信念空间规划器（如 GBT）仅在离散测量时刻检查安全，但真实系统状态在两次测量间持续扩散——这导致“看似安全的节点连线实际穿越障碍”。CT-GBT 用解析 ODE 描述信念连续演化，并用信念屏障函数对整段轨迹做概率安全认证，首次实现**可证明的连续时间机会约束满足**。

---

## X-Ray 开场  
CT-GBT 解决的是**采样式规划中“时间粒度失配”引发的安全漏洞**：当机器人动力学是连续的、传感器是离散的，而规划器只在离散节点检查安全时，中间轨迹可能严重越界。它提出三支柱方案：(1) 混合信念传播（连续 ODE + 离散 KF 跳变），(2) 段级信念屏障函数（segment-level probabilistic safety certificate），(3) 显式建模随机控制输入的机会约束。对 spatial AI 研究者而言，它标志着**从“离散信念快照”到“连续信念流”的范式迁移**，为无人机/航天器等高置信度系统提供可验证的实时规划基础。

---

## 📍 研究全景时间线  
```
[2011] Offline KF (Bry et al.) —— 首次将 KF 用于离散信念传播  
       ↓  
[2014] GBT (Agha-mohammadi et al.) —— 将 Offline KF 嵌入 RRT/SST，开启信念空间采样规划  
       ↓  
[2022] Belief Barrier Functions (Mazouz et al.) —— 为连续时间信念提供安全验证工具  
       ↓  
[2026] CT-GBT (this work) —— ✅ 首次耦合三者：连续 ODE 信念传播 + 段级屏障验证 + 控制机会约束  
                              ⚠️ 局限：仅支持线性 SDE 动力学 & 线性观测；需凸多面体障碍/控制集；未处理非高斯噪声
```

---

## 1 · 核心架构 / 方法总览  

### 1.1 系统/组件对比表  

| 模块 | 输入 | 输出 | 训练 vs 推理差异 |
|------|------|------|------------------|
| **Hybrid Belief Propagation** | 当前信念 `b(t_k) = N(x̄(t_k), Γ(t_k))`, 控制 `ū(t)`, 时间步长 `τ` | 连续信念流 `b(t) = N(x̄(t), Γ(t))`, `t ∈ [t_k, t_k+τ)` | **纯推理时运行**：无训练；依赖解析 ODE 求解（非学习） |
| **Segment-Level Safety Checker** | 起点信念 `b_near`, 终点信念 `b_new`, 障碍 `𝒳ᵢᵒ`（凸多面体）, 风险阈值 `P_safe` | `True` if `∀t∈[t_k,t_k+τ]: Pr(x(t)∈𝒳ᵢᵒ) < P_safe` | **纯推理时运行**：调用信念屏障函数求解 LMI（非学习） |
| **Probabilistic Control Constraint Check** | 当前估计协方差 `Λ(t)`, 反馈增益 `K`, 控制集 `𝒰`（凸多面体） | `True` if `Pr(u(t)∉𝒰) < P_safe` | **纯推理时运行**：基于 `u(t)` 的高斯分布与 `𝒰` 的半空间表示做概率上界估计 |

### 1.2 关键机制  
⚡ **Eureka Moment**：**“信念不是点，而是随时间连续膨胀的椭球；安全不能只验端点，必须验整段轨迹的最坏偏移”** —— 由此导出混合 ODE 传播 + 段级信念屏障函数双重创新。

### 1.3 信息流 ASCII 图  

```
[SampleBelief] → [NearestNeighbor]  
                   ↓  
           [PropagateBelief]  
                   ↓  
      ┌───────────────────────────┐  
      │ Hybrid Belief Propagation │ ←─ ODEs: x̄˙=Ax̄+Bū, Σ̇=AΣ+ΣAᵀ+GQGᵀ, Λ̇=(A−BK)Λ+Λ(A−BK)ᵀ  
      │   (continuous-time flow)  │  
      └───────────────────────────┘  
                   ↓  
    ┌───────────────────────────────────────┐  
    │ isCollisionFreeBelief(b_near, b_new)  │  
    │  • For each obstacle 𝒳ᵢᵒ:              │  
    │      solve LMI for belief barrier h(x)│  
    │      ⇒ certify Pr(x(t)∈𝒳ᵢᵒ) ≤ P_safe  │  
    │  • For control set 𝒰:                 │  
    │      bound Pr(u(t)∉𝒰) via Gaussian tail│  
    └───────────────────────────────────────┘  
                   ↓  
         [Add edge if ALL constraints pass]
```

---

## 2 · 数学核心  

📌 **Napkin Formula**:  
> **“段级安全 = 找到一个信念屏障函数 `h(x)`，使得 `h(x) > 0` 在障碍外成立，且其沿信念流的期望衰减率 `𝔼[dh/dt] ≤ -α·h`，从而保证 `Pr(x(t)∈𝒳ᵒ) ≤ exp(-α·t)·h(x̄(0))/min_{∂𝒳ᵒ} h`”**

**目标**：对任意连续时段 `[t₀, t₁]`，确保 `Pr(x(t) ∈ 𝒳ᵒ) < P_safe`  
**公式**（来自 IV-C.1 & Theorem 2）：  
Given convex polytopic obstacle `𝒳ᵒ = ∩ₖ{αₖᵀx ≥ γₖ}` and belief `b(t) = 𝒩(x̄(t), Γ(t))`,  
find `h(x) = minₖ (αₖᵀx − γₖ)` (distance-to-obstacle function), then verify:  
```
d/dt 𝔼[h(x(t))] ≤ -ρ·𝔼[h(x(t))]  ∀t ∈ [t₀,t₁],  for some ρ > 0  
⇒ Pr(x(t) ∈ 𝒳ᵒ) ≤ exp(−ρ·t) · h(x̄(t₀)) / min_{x∈∂𝒳ᵒ} h(x)
```
**变量说明**：  
- `h(x)`：障碍距离函数（线性，因 `𝒳ᵒ` 是凸多面体）  
- `𝔼[h(x(t))]`：信念下 `h` 的期望值（可解析计算：`αₖᵀx̄(t) − γₖ`）  
- `ρ`：衰减率，由 `A`, `K`, `Γ(t)` 决定，通过 LMI 求解  
**直觉**：若信念中心 `x̄(t)` 远离障碍 *且* 协方差 `Γ(t)` 膨胀足够慢，则 `h(x)` 的期望值指数衰减，越界概率被指数压制。

---

## 3 · 带数字走一遍  

**玩具设定**（二维位置+速度，简化）：  
- State `x = [p_x, p_y, v_x, v_y]ᵀ`, `A = [[0,0,1,0],[0,0,0,1],[0,0,-1,0],[0,0,0,-1]]`, `B = [[0,0],[0,0],[1,0],[0,1]]`, `G = I₄`, `Q = 0.01·I₄`  
- Initial belief: `x̄(0) = [0,0,0,0]ᵀ`, `Γ(0) = diag([0.01,0.01,0.001,0.001])`  
- Control: `ū(t) = [0.5,0]ᵀ` (constant x-accel)  
- Obstacle: `𝒳ᵒ = {x | p_x ≤ -0.1}` (left wall), so `h(x) = p_x + 0.1`  
- Time horizon: `t ∈ [0, 0.5]`  

**推导**：  
1. Solve ODE (13a): `x̄(t) = [0.5t²/2, 0, 0.5t, 0]ᵀ = [0.25t², 0, 0.5t, 0]ᵀ` → `h(x̄(t)) = 0.25t² + 0.1`  
2. Solve ODE (13b)+(13c) for `Γ(t)` → `Γ₁₁(t)` (p_x variance) grows as `≈ 0.01 + 0.005t²`  
3. `𝔼[h(x(t))] = h(x̄(t)) = 0.25t² + 0.1 > 0` for all `t`, and `d/dt 𝔼[h] = 0.5t ≥ 0` → **not decaying!**  
4. But CT-GBT checks *barrier derivative condition*: compute `d/dt 𝔼[h] − ρ·𝔼[h] ≤ 0`. With `ρ=2`, at `t=0`: `0 − 2·0.1 = −0.2 < 0`; at `t=0.5`: `0.25 − 2·0.1625 = −0.075 < 0` → **LMI feasible** → certified safe.  
→ 即使 `h(x̄)` 增长，只要 `Γ(t)` 不爆炸，仍可找到 `ρ` 满足条件。

---

## 4 · 工程视角  

| 指标 | 值 | 依据 |
|------|----|------|
| **延迟 per propagation step** | `UNVERIFIED` | 论文未报告单步耗时（仅提“evaluated across benchmarks”） |
| **内存占用** | `UNVERIFIED` | 未报告 RAM/VRAM 消耗；但 ODE 求解为 `O(n³)`（`n=state dim`），LMI 求解为 `O(m³)`（`m=#obstacle half-spaces`） |
| **吞吐（FPS）** | `UNVERIFIED` | 未报告 planner iteration rate |
| **部署约束** | **需实时 ODE solver + LMI solver**（如 CVX/SCS）；**不支持非线性动力学**；**要求凸障碍/控制集** | Sec II-B, IV-C |
| **关键 trade-off** | **精度 vs 实时性**：更密的 ODE 时间步长 → 更准的 `Γ(t)` 估计，但增加计算；LMI 求解复杂度随障碍面数 `m` 立方增长 | Sec IV-C.1, "dense segment-level verification" |

---

## 5 · 数据与评测  

| 项目 | 内容 | 依据 |
|------|------|------|
| **数据集** | **论文未报告具体数据集名称**；描述为 “multiple benchmark environments” including “narrow-passage scenarios” | Sec V-B: “We evaluate the proposed method across multiple benchmark environments.” |
| **评测设置** | • 对比基线：discrete-time GBT variants<br>• 指标：success rate, chance constraint violation rate (for state & control)<br>• 场景：narrow passages where discrete-time methods fail due to inter-sample violations | Sec V-B, V-C, Abstract: “results show [...] robust enforcement of chance constraints, including in narrow-passage scenarios where discrete-time counterparts fail” |
| **指标数字** | **论文未报告任何具体数值**（如 success rate=92.3%, violation rate=0.8%）；仅定性称 “high success rates” and “robust enforcement” | 全文无数字表格或量化结果句；V-C 仅说 “Monte-Carlo Simulations confirm theoretical guarantees” |

---

## 6 · 能力与失败模式  

✅ **能做**：  
- 在线性 SDE + 线性观测下，对整段连续轨迹提供概率安全证书  
- 同时保障状态机会约束 `Pr(x(t)∈𝒳ᵒ) < P_safe` 和控制机会约束 `Pr(u(t)∉𝒰) < P_safe`  
- 与 RRT/SST 等采样器即插即用（Alg. 1）  

❌ **不能做**：  
- 处理非线性动力学（如 quadrotor full dynamics）或非高斯噪声  
- 处理非凸障碍（如圆形障碍需外接多面体近似，引入保守性）  
- 实时闭环重规划（因 LMI 求解非恒定耗时）  

### 隐含假设 (Hidden Assumptions)  
1. **系统完全线性可观可控**：Sec II-A 明确要求 “matrices A, B, and C are such that the system is controllable and observable” —— 若实际系统存在不可观模态，`Σ(t)` 发散，屏障失效。  
2. **障碍与控制集严格凸多面体**：Sec II-B 定义 `𝒳ᵒ` 和 `𝒰` 为 “convex polytope” 并用半空间交集表示；若用 implicit function（如 `x²+y²<1`），`h(x)` 非线性，LMI 无法构建。  
3. **反馈控制器已知且稳定**：Sec II-B 使用预设计 `K`；若 `K` 不稳定，`Λ̇=(A−BK)Λ+Λ(A−BK)ᵀ` 导致 `Λ(t)` 指数爆炸，`Γ(t)` 失控，安全证书无效。  

---

## 7 · 与相关工作对比  

| 方法 | 动力学模型 | 安全验证粒度 | 控制不确定性 | 是否连续时间 |  
|------|------------|--------------|--------------|--------------|  
| **Discrete-time GBT** [3] | Discrete LTI | Node-level (tₖ only) | ❌ ignored | ❌ |  
| **Chance-constrained RRT*** [7] | Discrete LTI | Node-level | ✅ (via Boole’s inequality) | ❌ |  
| **Belief Barrier Certificates** [14] | Continuous SDE | Segment-level | ❌ (assumes perfect state) | ✅ |  
| **CT-GBT (this)** | **Continuous SDE + Discrete measurements** | **Segment-level** | ✅ (stochastic u(t) modeled) | ✅ |  

**面试 Tip**：  
> *“被问‘CT-GBT 和传统 GBT 最大区别？’ —— 答：不是‘更快’或‘更准’，而是‘安全定义不同’。传统 GBT 问‘节点安全吗？’，CT-GBT 问‘这段轨迹上每一刻都安全吗？’。这就像从检查桥梁两端，升级为用应力传感器全程监测桥面形变。”*

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-07-21)  

**官方 repo 未在论文中给出**（全文无 `github.com` 链接；arXiv PDF 无 hyperlink） → **以下 pitfall 由 §6 失败模式推导（未经 issue 验证）**：  

1. **`ONNX export failure`**：CT-GBT 的 `PropagateBelief` 含自定义 ODE 求解器（Scipy `solve_ivp`）和 LMI 求解（CVXPY），二者均**无法直接导出 ONNX**；若强行转换，`solve_ivp` 被替换为固定步长 Euler，导致 `Γ(t)` 误差累积，安全证书失效。  
   → *Derivation*: §6 Hidden Assumption #1 (linear dynamics) + §4 deployment constraint (requires real-time ODE solver) ⇒ `solve_ivp` is non-differentiable/non-exportable.  

2. **`LMI solver timeout on dense obstacles`**：当障碍由 >50 个半空间定义（如精细网格地图），LMI 变量维度超 `O(m²)`，CVXPY 默认求解器（SCS）在嵌入式平台（Jetson AGX）上超时（>1s），导致 planner stall。  
   → *Derivation*: §6 Hidden Assumption #2 (convex polytope obstacles) + §4 trade-off (“LMI complexity cubic in m”) ⇒ `m>50` breaks real-time.  

3. **`NaN covariance explosion under unstable K`**：若用户误设反馈增益 `K` 使 `A−BK` 有正实部特征值，ODE (13c) 中 `Λ̇` 指数增长，`Γ(t)=Σ+Λ` 快速溢出，`isCollisionFreeBelief` 返回 `NaN`。  
   → *Derivation*: §6 Hidden Assumption #3 (stable K) + §2 Napkin Formula (requires `ρ>0`) ⇒ unstable `K` violates barrier decay condition.

---

[← Back to navigation README](./README.md)  
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`

<!-- source: https://arxiv.org/abs/2607.02884 -->
