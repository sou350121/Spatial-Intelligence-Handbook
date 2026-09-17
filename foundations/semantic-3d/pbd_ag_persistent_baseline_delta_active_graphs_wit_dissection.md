<!-- ontology-5axis
problem: n/a
representation: scene-graph
sensor: RGBD
paradigm: 3R-SLAM-hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# PBD-AG：面向长时程服务机器人的持久基线-增量主动图与不确定性感知巡检 (PBD-AG: Persistent Baseline-Delta Active Graphs with Uncertainty-Aware Inspection for Long-Horizon Service Robots)

> **发布时间**：arXiv:2608.10449v2，2026-08-12
> **论文 / 模型名**：PBD-AG
> **核心定位**：把"场景里变化慢的结构"和"变化快的物体"按**变更速率 + 推翻所需证据强度**拆成 baseline 与 delta 两层，并用**几何可见性门（visibility gate）**决定"一次未观测到"到底算不算"物体消失了"——从而在无预载语义图的未知环境里自主 bootstrap 可审计的持久世界模型。

长时程服务机器人面对的真正痛点不是"重建一次场景"，而是**反复修订**：物体被挪走、被遮挡、检测器漏检，这三者产生的观测信号几乎一样。PBD-AG 的结论是：把"存不存在"当成一个**带几何可见性门控的 log-odds 累积器**，而不是逐帧独立判定的 VLM 预测。

---

## X-Ray 开场

PBD-AG 解决的是"**漏检 ≠ 消失**"这个崩溃点：现有在线建图（DynaMem）累积定位/观测误差且不维护对象身份与支撑关系，静态场景图（ConceptGraphs / HOV-SG）根本无法表达持久变化，整体式 VLM 预测又拿不出可验证的 3D 几何证据。

它提出的方案是**双层解耦 + 事件溯源**：用 frontier exploration 自主 bootstrap 出稳定 fixture（baseline），随后一切细粒度物体的变化记成**typed event delta**（move / reparent / remove…）；关键机制是 Eq.(3)——只有当物体 3D 包围盒投影落在视锥内、有足够像素支撑、且未被更近几何遮挡时，未匹配才计为负证据。

对 spatial AI 研究者的意义：它把"存在性"从一个**感知问题**重构成一个**可观测性问题**，并给出了一套固定权重、可复现、可审计的工程配方（frozen increments），这是目前 scene-graph 记忆系统里少见的"先证明再删除"范式。

---

## 📍 研究全景时间线

```
1997 ─── Yamauchi: frontier exploration（未知空间覆盖的经典范式）
  │
2020 ─── Chaplot et al.: learned exploration policies（利用几何规律）
  │
2022 ─── Hydra: 增量构建+优化 metric-semantic scene graph
  │
2023 ─── VLMaps / ConceptFusion: 语言对齐特征融进 metric map
  │      SigLIP (Zhai et al. 2023) / Grounding DINO (Liu et al. 2023)
  │
2024 ─── ConceptGraphs: 多视图物体 proposal 关联成开放词表图
  │      HOV-SG: floor/room/object 层级组织
  │      Clio: 在线选任务相关图粒度
  │      DynaMem: posed RGB-D → 可变 spatio-semantic voxel memory ★最近邻对手
  │      VLFM: 语言 value 赋给 frontier，做 zero-shot 物体导航
  │      SAM 2 (Ravi et al. 2024)
  │
2025 ─── DovSG: 初始 RGB-D 扫描建图 + 长期操作中更新子图（从"已初始化全局图"开始）
  │
2026 ─── SCOUT: 语义不确定性耦合场景覆盖
  ╰──► PBD-AG（本文）: frontier(未知空间) ⊕ graph-uncertainty(已发现 fixture 的近距离巡检)
                      + visibility-gated existence + typed event audit trail
      本文局限：定量评估仅在 OmniGibson/BEHAVIOR 仿真；真机只做定性演示；
                所有超参 frozen、无在线自适应；fine 层不做跨视图融合。
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 |
|---|---|---|---|
| Frontier exploration | occupancy map $A_t$（初始全 unknown）、range | 未知空间边界目标点 | 无训练；传统 frontier，**不给未探索区域赋语义** |
| Fixture 假设生成 | 累积 posed RGB-D + SigLIP 特征体素图、fixture taxonomy | fixture proposals（DBSCAN 聚类后） | 无训练；阈值 + margin 过滤，几何不合理簇直接丢弃 |
| 候选 track 关联 | 跨 semantic update 的 clusters | 持久候选 track $\mathcal{H}_t$ | 无训练；class 一致性 + center 距离 + footprint 重叠 |
| Cross-frame sensor-consensus gate | 多批次时序证据 | 直接晋升 $\mathcal{C}_t$（或触发 VLM 复核） | 无训练；**必须来自多个时间上不同的观测批次** |
| Coarse VLM 验证 | near-threshold / 类冲突 track | 类别确认（权重 3） | 冻结 VLM，单次有界、带缓存 |
| 持久状态融合 | 匹配对 $(i,j)$ | $p^{\rm cls}_i, p^{\rm parent}_i, \mu_i, \Sigma_i, a_i, \tau_i$ | 几何用 EMA $\alpha=0.35$；$\Sigma_i$ 只存最近 ≤32 个 accepted center |
| **Visibility-gated existence** | 3D bbox 投影 + depth | 是否施加负证据 $V_i(t)\in\{0,1\}$ | 无训练；固定 0.15 m 容差、5×5 窗口、≥2 样本 |
| Lifecycle / audit events | 每 batch 更新 | add / confirm / update / move / reparent / demote / remove | 无训练；阈值 0.72 / 0.30 / 0.12，move ≥0.35 m |
| Graph-uncertainty 巡检调度 | $\mathcal{Q}_t \subseteq \mathcal{C}_t$、$\phi_i^t$ | 目标 fixture $i^*_t$ | 固定权重 $\mathbf{w}=(.20,.30,.10,.15,.10,.15)$ |
| 视点选择 | 候选 known-free cell | 执行视点 $v^*$ | 固定代价式 Eq.(6)，$d_{\rm pref}=0.90$ m |
| Fine 接地 | 单一 contract-valid primary RGB-D view | 子节点 + support 边（挂到 canonical fixture） | 冻结 VLM 盘点 → Grounding DINO 定位 → SAM 2 精修 mask → 反投影 |

> **注意**：全流程**没有任何训练环节**，全部是冻结模型推理 + 固定阈值/权重。论文明确称为 "frozen increments" / "fixed before evaluation"。这既是可复现性的优点，也是泛化风险（见 §6）。

### 1.2 关键机制

**⚡ Eureka Moment：把"对象是否存在"从"感知置信度"改写成"几何可观测性门控的证据累积"——漏检只有在该物体 3D 包围盒确实落在视锥内、未被更近几何遮挡、且有足够像素支撑时，才允许扣减存在性 log-odds。**

第二条同等重要的洞见是**变更速率分层**：结构 fixture 慢变（可冻结成 immutable baseline $B^{(0)}$），任务物体快变（记成 typed event delta），二者用不同的关联前端与不同的证据强度去修订。

第三条：**frontier 与 inspection 职责分离**。未知空间永远交给传统 frontier（不对未见区域做语义预测）；已有 fixture 的"关系未定"状态才触发近距离巡检——这避免了"把语义内容归因给未探索区域"这一常见错误。

### 1.3 信息流 / 架构图

```
        ┌─────────────────────── 自主 Bootstrap 阶段 ───────────────────────┐
        │                                                                    │
 range ─┴─► occupancy A_t (初始 all unknown)                                 │
                │                                                             │
                │ frontier exploration                                        │
                ▼                                                             │
           new viewpoints ──► posed RGB-D z_t=(I,D,K,T)                       │
                                    │                                         │
                    SigLIP 特征 + 几何 累积进共享 world frame 体素图          │
                                    │                                         │
                        按 fixture taxonomy 查询（class sim + margin）         │
                                    │                                         │
                              DBSCAN 聚类（metric space）                      │
                                    │  几何不合理簇丢弃                       │
                                    ▼                                         │
                        跨 semantic update 关联 → 持久候选 track H_t           │
                                    │                                         │
                    ┌───────────────┴────────────────┐                        │
             跨帧 sensor-consensus 通过        近阈值 / 类冲突               │
                    │                                │                        │
                    │                      有界+缓存的 coarse VLM 验证         │
                    └───────────────┬────────────────┘                        │
                                    ▼                                         │
                    晋升为权威 fixture C_t（同一持久 ID h_i）                 │
                                    │                                         │
              ┌─────────────────────┴──────────────────────┐                  │
        属于 T_insp 且近距离细观测未解决              其他 fixture             │
              │                                        （无需巡检）            │
              ▼                                                               │
   ┌── 巡检阶段（与 frontier 交替）──┐                                        │
   │  u_i = w^T φ_i  （Eq.4）        │                                        │
   │  i* = argmax[0.8u + 0.2Prox]    │  无可行视点 → defer，检查下一个       │
   │  min J(v,i)  （Eq.6）           │  全不可达 → 恢复 frontier exploration   │
   │  固定基座 RGB-D sweep           │                                        │
   └────────────┬───────────────────┘                                        │
                │  primary view（唯一用于 fine grounding）                    │
                ▼                                                            │
   VLM 父级验证 → VLM 多模态盘点 → Grounding DINO → SAM 2 mask → 反投影 μ_j    │
                │  （alternate 角度只做父级验证/retry，不跨视图融合）          │
                ▼                                                            │
        子节点 + support edge ──► capture ledger ──► 挂到 canonical fixture  │
                                                                             │
◄────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
   Freeze(B~_{t_b}) = B^(0)   ← immutable baseline package
        │
        ▼
   运行期 M_t（mutable track state） + ℰ_{1:k_t}（有序 audit event 流）
        │
        └─► G_t = Publish(B~_t, M_t)
```

---

## 2 · 数学核心

📌 **Napkin Formula**

$$\ell_i^{t}=\ell_i^{t-1}+\eta_o O_i^{t}+\eta_c K_i^{t}-\underbrace{\eta_m U_i^{t}V_i(t)}_{\text{负证据被可见性门控}}-\eta_r R_i^{t}$$

> 一句话直觉：**存在性是 log-odds 存款账户；只有"看得见却没看到"才允许取钱。**

### 目标 → 公式 → 变量 → 直觉

**目标**：给定逐 batch 的语义观测（含"该目标未被匹配"这一信号），在线维护每个 track 的存在性信念 $p_i^{\rm exist}$，使得 (a) 真消失能被及时判定（高 event recall），(b) 遮挡/坏视角/检测器失效**不**被误判为消失（低 false absence）。

**公式（Eq.3）**：

- **变量说明**
  - $\ell_i^{t}=\log[p_i^{\rm exist,t}/(1-p_i^{\rm exist,t})]$：存在性 log-odds，$t$ 索引 semantic update batch。
  - $O_i^{t}$：ordinary positive observation（普通匹配上的观测）。
  - $K_i^{t}$：cached confirmation（缓存 VLM 确认）。
  - $U_i^{t}$：unmatched track（未匹配）。
  - $R_i^{t}$：cached rejection（缓存否决）。
  - $V_i(t)\in\{0,1\}$：**几何可见性门**——只有 $V_i(t)=1$ 时 $U_i^t$ 才真正扣分。
  - 冻结增量：$(\eta_o,\eta_c,\eta_m,\eta_r)=(1.0,\,1.8,\,0.70,\,2.20)$。
  - 记忆性更新：$\ell \leftarrow \ell + \eta_o O - \eta_m U V$（when $V=0$，$\ell$ 与"可见漏检计数"**都不变**）。

- **直觉**：$\eta_r=2.20 > \eta_m=0.70$ 说明"缓存明确否决"比"普通漏检"可信三倍；$\eta_c=1.8 > \eta_o=1.0$ 说明 VLM 确认比单次观测更值钱。最重要的不对称是：负证据只有在 $V_i(t)=1$ 时才入场——**遮挡不是证据。**

**可见性门判定（$V_i(t)=1$ 的条件，全部满足）**：
1. 从存储的 world-frame 3D bbox 采样；
2. 样本落在 valid camera range 内；
3. 样本落在 image boundary 内；
4. 在 $5\times5$ 窗口内有 valid depth；
5. **未遮挡**：$d_{\rm meas}+0.15\,\mathrm{m}\ge d_{\rm expected}$；
6. 至少 **2 个样本**通过全部条件。

**生命周期阈值（由同一个 $\ell$ 驱动）**：
- confirm（发布）：$p_i^{\rm exist}\ge 0.72$，且需跨 batch 确认；
- demote：$p_i^{\rm exist}<0.30$；
- remove：$p_i^{\rm exist}\le 0.12$，且需**至少 3 次 visibility-admissible miss**；
- move 事件：位移 $\ge 0.35\,\mathrm{m}$；
- Pinned fixture **豁免**动态删除。

**巡检调度（Eq.4–6）**：
- $u_i^{t}=\mathbf{w}^{\top}\boldsymbol{\phi}_i^{t}$，$\mathbf{w}=(.20,.30,.10,.15,.10,.15)$，$\phi$ 含 existence / class / parent / position / age / confirmation 六项归一化不确定性（existence ambiguity $=4p(1-p)$，class 用归一化熵 + score-margin 模糊度）。
- $i_t^{*}=\arg\max_{i\in\mathcal{Q}_t^{\rm feas}}\left[0.8u_i^{t}+0.2\operatorname{Prox}(i)\right]$，$\operatorname{Prox}$ 在 8 m 内衰减到 0；目标**锁定到 capture / failure / rejection / completion**。
- 视点代价：$J(v,i)=|d_{\rm foot}(v,i)-d_{\rm pref}|+0.08D_t(v)-0.20C(v)+4[1-\operatorname{Cov}(v,i)]+P_{\rm margin}(v,i)$，其中 $d_{\rm pref}=0.90\,\mathrm{m}$、$C(v)=\min(\operatorname{Clr}(v),1\,\mathrm{m})$、$D_t$ 为机器到视点距离、$\operatorname{Cov}$ 为预测支撑面覆盖率、$P_{\rm margin}$ 惩罚贴边。

---

## 3 · 带数字走一遍（玩具例子）

> ⚠️ 下面是**玩具设定**：场景为一个桌上杯子，用论文冻结增量 $(\eta_o,\eta_c,\eta_m,\eta_r)=(1.0,1.8,0.70,2.20)$ 和 σ 函数手动推演。真实系统里 $O/K/U/R$ 由匹配结果给出。

设初始 $\ell^0=0 \Rightarrow p^{\rm exist}=0.50$。

| 步 | 事件 | $\ell$ 更新 | $\ell$ | $p^{\rm exist}=\sigma(\ell)$ | 触发的生命周期动作 |
|---|---|---|---|---|---|
| t1 | 普通匹配观测 $O=1$ | $0+1.0$ | 1.00 | 0.731 | 单 batch 不够，**不发布**（需跨 batch 确认） |
| t2 | 又一个普通观测 $O=1$ | $1.0+1.0$ | 2.00 | **0.881** | 跨 batch 确认 + $p\ge0.72$ → **confirm**，发布进 baseline |
| t3 | 机器人转身，杯子被箱子遮挡 → $U=1$ 但**门控 $V=0$** | $2.00+0$ | 2.00 | 0.881 | **无任何变化**（$\ell$ 与 miss 计数都不动）✅ 核心价值 |
| t4 | 回到可见位置，仍未匹配（真被拿走了）$U=1,V=1$ | $2.00-0.70$ | 1.30 | 0.786 | update miss#1，不 demote |
| t5 | 同上 | $1.30-0.70$ | 0.60 | 0.646 | miss#2，不 demote |
| t6 | 同上 | $0.60-0.70$ | −0.10 | 0.475 | miss#3，仍 >0.30，不 demote |
| t7 | 同上 | $-0.10-0.70$ | −0.80 | 0.310 | 逼近阈值，仍未 demote |
| t8 | 同上 | $-0.80-0.70$ | −1.50 | 0.182 | $p<0.30$ → **demote**（miss#5） |
| t9 | 同上 | $-1.50-0.70$ | −2.20 | **0.100 ≤ 0.12** | 且已 ≥3 次可见 miss → **remove** |

**关键对照实验**：若 t4–t9 全部是**遮挡**（$V=0$），则 $\ell$ 永远停在 2.00，$p^{\rm exist}=0.881$，物体被永久保留。这正是论文 ablation "w/o visibility gate" 的机制——false absence 从 `0.014` 飙到 `0.262`，event recall 从 `11/12` 掉到 `6/12`。

**阈值反解（供工程调参用）**：demote 边界 $p=0.30\Rightarrow \ell=\ln(0.3/0.7)\approx-0.847$；remove 边界 $p=0.12\Rightarrow \ell\approx-1.993$。从 $\ell=2.0$ 出发需 5 次可见漏检才 remove，与"at least three visibility-admissible misses"的硬约束方向一致（可见漏检是必要非充分条件）。

**移除后恢复**：removed track 仍留在 memory 中；若它又被成功 reassociate，**恢复原 identity** $h_i$（不新建节点）——这正是 IDF1 `0.833` 与 IDS `0.0` 的来源。

---

## 4 · 工程视角

> **零容忍声明**：论文**没有报告任何** latency / VRAM / FPS / 吞吐 / 硬件型号（仅写 "physical mobile robots" / "onboard RGB-D and LiDAR" / "multiple robot platforms"）。下表凡缺失项一律标「论文未报告」，**不做任何估算填充**。

| 维度 | 论文报告值 | 说明 / 约束 |
|---|---|---|
| 推理延迟 / FPS | **论文未报告** | 全文无 latency 或 frame-rate 数字 |
| 显存 / 内存占用 | **论文未报告** | 无 VRAM/RAM 数字 |
| GPU / 机器人型号 | **论文未报告** | 只说 "physical mobile robots"、"multiple robot platforms" |
| Coarse 发现预算 | 600 semantic keyframes | 预算耗尽后**不再接纳新 coarse 候选**，但已排队的 fine inspection 可继续完成 |
| 协方差存储上限 | 至多 **32** 个最近 accepted center（$\Sigma_i$） | 明确的内存 bounded 设计；$\Sigma_i$ **不用于关联** |
| 动态关联几何门 | 3D center 距离 < **0.8 m** | 贪心一对一匹配；跨类不允许 |
| 动态关联外观门 | SigLIP cosine > **0.78** | **无 embedding 时该门被省略**（重要降级路径） |
| 中心平滑 | EMA $\alpha=0.35$ | coarse fixture center |
| 外观 embedding | 按观测次数平均后 $\ell_2$ 归一化 | — |
| VLM 调用预算 | 每 track **一次有界、带缓存**的 coarse VLM 验证（权重 3） | 调度代价式显式含 "model-call limits" |
| 巡检重试 | bounded retry + retry-cooldown 排除 | 失败目标保留，但受冷却限制 |
| 视点采光/行程 | 偏好站位 $d_{\rm pref}=0.90$ m；travel 权重 0.08；clearance 权重 0.20（$C=\min(\text{Clr},1\,\text{m})$）；coverage 权重 4 | 视点须为 connected known-free cell 且满足 standoff / inflated-map reachability / line-of-sight / projected-coverage / image-margin |
| 目标锁定 | 锁定到 capture / failure / rejection / completion | 防止调度抖动 |
| Fine 层计算 | VLM 盘点 + Grounding DINO + SAM 2，**仅在一个 primary view 上**执行 | alternate 角度**不融合**，只做父级验证/retry → 计算量可控但召回受限 |
| 部署副作用 | 真机演示仅定性（Figure 5 + supplementary video） | **不参与任何定量对比** |

**工程 trade-off 总结（凡论文未给数字处均以机制描述代替）**：
1. **延迟 vs 身份连续性**：PBD-AG 用"跨 batch 确认"换取 IDS=0，代价是 immediate-update 类方法能在 presence F1 上更高（`.938` / `.899` vs `.845`）。论文自己承认这是**刻意 trade**。
2. **内存 bounded vs 长期记忆**：$\Sigma_i$ 截断到 32 个中心，事件流 $\mathcal{E}_{1:k_t}$ 却无限追加——内存压力从几何转移到 audit log。
3. **模型调用 bounded**：coarse 阶段 VLM 只调用一次且有缓存，fine 阶段只在可巡检 fixture 上触发，且 $\mathcal{Q}_t$ 显式排除 completed / rejected / abandoned / 正在处理 / 冷却中的 track。
4. **未知空间的算力保护**：frontier 负责覆盖，不查询语义；**不给未探索区域做语义预测**——这是省 VLM 调用的关键设计，也是它区别于 VLFM / SCOUT 的地方。

---

## 5 · 数据与评测

### 5.1 数据 / 平台组成（逐字取自原文）

- **仿真平台**：`OmniGibson/BEHAVIOR`（Li et al. 2024）。
- **三个场景**：`Gates bedroom`、`Hotel suite`、`Benevolence`。
- **随机种子**：`7`、`17`、`27`。
- **rollout 数**：`nine integrated rollouts`（3 场景 × 3 种子）。
- **起始条件**：每次 rollout 从**空 working structural memory + 全 unknown 的 occupancy map** 开始；**无预载 scene-specific semantic graph**。
- **Coarse 发现预算**：`600 semantic keyframes`。
- **GT 可见性**：`Ground-truth identities, semantic annotations, and correspondences are never available to the system.` 仿真相机位姿**仅**用于 RGB-D 配准；frontier 与 fixture-inspection 调度均**不使用** GT 场景标注。
- **参数策略**：单一场景级 taxonomy 与参数化在三个 seed 上固定，`no seed-specific setting`。
- **动态评测子集**：`three Hotel sequences of 300 frames`。
- **每个 seed 的动态事件**：one appearance、within-support motion、disappearance、cross-support transfer → `12 scheduled events`（3 seed × 4 类）。

### 5.2 匹配协议与指标（讲条件）

| 项 | 设置 |
|---|---|
| Coarse 匹配 | 贪心一对一，same-class，中心距离 < `1.0 m` |
| Fine 匹配 | 额外要求**父 fixture 匹配正确** + 中心距离 < `0.5 m` → **该 F1 同时评估物体恢复与层级接地** |
| 报出的指标 | instance precision / recall / F1 / matched-center error（`Err.`）/ Count MAE |
| `MAE` 定义 | class-wise instance-count error 平均 |
| 波动 | 除注明 pooled，均为 seed 上的 sample standard deviation |
| 控制变量法 | `Adapted` = 共同接口实现，**只隔离图关联与记忆更新**，不是任一原系统的端到端复现；评测限制在该接口支持的类别交集上，且与自主全图评估**分开报告** |
| 动态协议指标 | `IDF1`（Ristani et al. 2016）、`ID-Pres.`（全局身份分配后的 presence F1）、`IDS`、pooled event recall、post-acquisition false absence（在 GT-present 的 eligible checkpoint 上） |
| 三个受控协议 | ① shared fixed-trajectory replay ② shared-observation dynamic benchmark ③ paired independent active rollouts —— 分别隔离 **representation / temporal-memory / active-acquisition** 三种效应 |

### 5.3 定量结果（逐字）

**Table 1 — 共享证据下的受控 coarse-fixture 对比（9 个 scene–seed run）**

| Method | P ↑ | R ↑ | F1 ↑ | Err. [m] ↓ | MAE ↓ |
|---|---|---|---|---|---|
| PBD-AG | `.951 ± .091` | `.802 ± .122` | `.868 ± .102` | `.320 ± .119` | `.356 ± .233` |
| DynaMem-adapted | `.890 ± .156` | `.667 ± .175` | `.757 ± .163` | `.318 ± .127` | `.716 ± .389` |
| ConceptGraphs-adapted | `.598 ± .081` | `.838 ± .136` | `.696 ± .095` | `.323 ± .121` | `1.176 ± .501` |

正文相应表述：PBD-AG 取得最高 nine-run fixture F1 `0.868 ± 0.102`，**比 DynaMem-adapted 和 ConceptGraphs-adapted 分别高 11.1 和 17.2 个点**；count MAE **从 `0.716` 降到 `0.356`**。matched-center error 相近，因为方法拿到**相同几何证据**——差异主要来自实例关联、合并与保留。

**Table 2 — 共享 grounded 3D 流上的受控动态记忆评测（3 seeds）**

| Method | IDF1 ↑ | ID-Pres. ↑ | IDS ↓ | Event R. ↑ | False abs. ↓ |
|---|---|---|---|---|---|
| **PBD-AG** | `.833 ± .029` | `.845 ± .034` | `.0 ± .0` | `11/12` | `.014` |
| DynaMem-inspired | `.688 ± .025` | `.938 ± .057` | `1.0 ± .0` | `8/12` | `.034` |
| ConceptGraphs-inspired | `.615 ± .024` | `.899 ± .000` | `1.0 ± .0` | `6/12` | `.017` |
| Last observation | `.702 ± .026` | `.938 ± .057` | `1.0 ± .0` | `8/12` | `.017` |
| Append-only | `.627 ± .025` | `.899 ± .000` | `1.0 ± .0` | `6/12` | `.000` † |
| Static-only | `.146 ± .000` | `.179 ± .000` | `.0 ± .0` | `0/12` | `.000` † |
| Online remap | `.083 ± .003` | `.125 ± .000` | `17.67 ± .58` | `6/12` | `.626` |
| w/o visibility gate | `.708 ± .029` | `.741 ± .008` | `.0 ± .0` | `6/12` | `.262` |
| w/o persistent ID | `.070 ± .003` | `.125 ± .000` | `43.33 ± 1.15` | `6/12` | `.014` |

† `zero false absence because disappearance is never resolved.`

正文：PBD-AG IDF1 最高 `0.833 ± 0.029`，恢复 `11 of 12` 事件，**零身份切换**；相比最强 immediate-update 控制，IDF1 **高 13.1 个点**，event recall **从 8/12 提到 11/12**。去 visibility gate 后 false absence 从 `0.014` 升到 `0.262`、event recall 从 `11/12` 掉到 `6/12`；去 persistent ID 后 IDF1 从 `0.833` 掉到 `0.070`、IDS 升到 `43.33 ± 1.15`。

**Table 3 — 自主 PBD-AG 场景构建（每场景 3 seeds；最后一行汇总 9 次 rollout）**

| Scene (coarse/fine GT) | Coarse P ↑ | Coarse R ↑ | Coarse F1 ↑ | Coarse Err.[m] ↓ | Fine P ↑ | Fine R ↑ | Fine F1 ↑ | Fine Err.[m] ↓ |
|---|---|---|---|---|---|---|---|---|
| Gates bedroom (9/15) | `1.000 ± .000` | `.926 ± .064` | `.961 ± .034` | `.215 ± .035` | `.874 ± .050` | `.889 ± .077` | `.878 ± .023` | `.036 ± .009` |
| Hotel suite (13/14) | `.944 ± .048` | `.795 ± .089` | `.859 ± .036` | `.320 ± .029` | `.963 ± .064` | `.571 ± .143` | `.710 ± .117` | `.071 ± .012` |
| Benevolence (14/12) | `.854 ± .109` | `.714 ± .124` | `.777 ± .119` | `.464 ± .043` | `.617 ± .114` | `.500 ± .144` | `.550 ± .128` | `.029 ± .002` |
| **All rollouts** | `.933 ± .088` | `.812 ± .124` | `.866 ± .102` | `.333 ± .113` | `.818 ± .170` | `.653 ± .210` | `.713 ± .167` | `.045 ± .021` |

正文：9 次自主 rollout coarse F1 `0.866 ± 0.102`、fine F1 `0.713 ± 0.167`；Gates 联合恢复最强（`0.961` coarse / `0.878` fine）；Hotel fine 精度高（`0.963`）但召回低，**说明其 fine 误差以漏检为主而非虚报**；Benevolence 因重复 fixture 几何 + 受限视点导致跨实例歧义上升而下降，"delineate the current operating regime of the system"。

---

## 6 · 能力与失败模式

### 6.1 能做（有数字支撑）

| 能力 | 证据 |
|---|---|
| 从**空图 + 全 unknown 地图**自主 bootstrap 层级场景图 | 9 次 rollout，coarse F1 `0.866 ± 0.102`，fine F1 `0.713 ± 0.167` |
| Coarse fixture **关联/巩固/保留**优于能力匹配控制 | F1 `0.868` vs `.757` / `.696`；MAE `0.356` vs `0.716` / `1.176` |
| **身份连续性**：跨 support 变更、跨消失-重现保持持久 ID | IDF1 `0.833 ± 0.029`，IDS `.0 ± .0` |
| **事件恢复**：appearance / within-support motion / disappearance / cross-support transfer | `11/12` scheduled events |
| **抗遮挡假删除** | false absence `.014`（去门控后 `.262`） |
| 移除后**身份复原** | removed track 保留在 memory，reassociation 成功即恢复原 $h_i$ |
| 可审计性 | 每个 audit event 存 total-order sequence / frame / persistent identity / lifecycle state / transition details |
| 真机整链路跑通 | Figure 5(A–E)：自主探索 / 物体级 RGB-D 巡检 / 持久 3D 建图+轨迹+巡检目标 / LiDAR occupancy / 物化层级图 |

### 6.2 不能做（讲具体）

1. **Fine 层召回受限，且误差性质是"漏"不是"错"**：Hotel suite fine recall 仅 `.571`（precision `.963`）、All rollouts fine recall `.653 ± .210`。
2. **重复几何 + 受限视点场景退化**：Benevolence coarse F1 `.777 ± .119`、fine F1 `.550 ± .128`，论文自认是"current operating regime"的边界。
3. **定量评估**几乎全在 OmniGibson/BEHAVIOR 仿真内；真机（含多平台、unseen indoor environments）**只有定性演示**，明确"not included in the quantitative comparisons"。
4. **不做跨视图融合**：alternate 基座角度只用于父级验证或 bounded retry，**不**融合成跨视图 mask / 点云 / 3D proposal——fine proposal 全部来自单一 primary view。
5. **fine 节点不回流动态前端**："Fine nodes from active inspection ... do not re-enter the frame-level dynamic association front end." → **已接地的细粒度物体无法被跟踪移动**（只能靠后续重新巡检刷新）。
6. **无在线学习/自适应**：所有阈值与权重"fixed before evaluation"、"frozen increments"，无 domain adaptation。
7. **不做未见空间的语义预测**：frontier 只覆盖几何，不对未知区域赋予语义内容——这既是设计优点，也意味着**无法 zero-shot 去找一个还没探索过的语义目标**（与 VLFM 的能力边界相反）。

### 6.3 隐含假设 (Hidden Assumptions)

| # | 隐含假设 | 论文证据 / 触发条件 | 被违反时后果 |
|---|---|---|---|
| A1 | **结构 fixture 慢变、任务物体快变** | "structural layout changes slowly, while task-relevant objects may appear, disappear..."；pinned fixture 豁免动态删除 | 若房间本身重排（家具整体挪位），baseline 被冻结成 $B^{(0)}$，只能靠 add/confirm 新 track 兜底，旧 fixture 因 pinned 不被 demote |
| A2 | **深度测量在 0.15 m 内可信** | 未遮挡判据 $d_{\rm meas}+0.15\ge d_{\rm expected}$；valid depth 需落在 $5\times5$ 窗口 | 深度系统性偏差 >0.15 m、透明/反光/无纹理表面 → $V_i(t)$ 误触发，false absence 上升，退化为"无门控"（`.262`）那档 |
| A3 | **已知且固定的 fixture taxonomy + 任务巡检 taxonomy $\mathcal{T}_{\rm insp}$** | "queried against the fixture taxonomy"；$\mathcal{Q}_t$ 只含类别属于 $\mathcal{T}_{\rm insp}$ 的 canonical fixture | 词表外类别的 fixture **永远不会进巡检队列**，其子物体永久不可见 |
| A4 | **单视图足以完成 fine grounding** | "one contract-valid primary view for fine-object grounding"；不融合跨视图 | 背面/顶面被遮挡的物体在任意单一视点都漏，fine recall 上限被判死 |
| A5 | **位姿 $T_t$ 已给定且准确** | $z_t=(I_t,D_t,K_t,T_t)$；仿真位姿只用于配准 | 真实 SLAM 漂移会同时污染 world-frame bbox（→可见性门）与 association 距离门（0.8 m），误差在 baseline 与 delta 间全局传播 |
| A6 | **SigLIP embedding 在 0.78 阈值下可判别** | 动态关联要求 cosine > `0.78`；无 embedding 时门被省略 | 同款多只的杯子/瓶子、无纹理白墙上的物体 → 门失效或误合并，退化成 w/o persistent ID（IDS `43.33`）那档 |
| A7 | **贪心一对一匹配足够** | "Eligible pairs are greedily matched one-to-one" | 密集场景中次优贪心分配会锁错配对，需靠 unique-class fallback 与大运动恢复兜底 |
| A8 | **支撑关系可由几何指派得到** | `p_i^parent` 由 accumulated evidence 归一化 + reparent（有效支撑变化） | 物理支撑≠几何最近（叠放、悬挂、透明桌面）时 parent belief 系统性错误 |
| A9 | **VLM 盘点能给出正确的细类与计数** | VLM-based multimodal inventory 提议 task-relevant fine categories and counts | VLM 幻觉直接变成**持久**图节点（因为一旦确认就附到 canonical fixture 并从动态前端脱离） |

---

## 7 · 与相关工作对比

| 方法 | 表示 | 是否增量 | 是否显式处理"存在性/消失" | 是否主动巡检 | 与 PBD-AG 的关键差异 |
|---|---|---|---|---|---|
| **VLMaps** (2023) | 语言对齐 metric map | 部分 | ✗ | ✗ | 特征在栅格/体素里，无对象身份、无支撑关系 |
| **ConceptFusion** (2023) | 语言对齐 metric map | 部分 | ✗ | ✗ | 同上，偏重建/查询 |
| **ConceptGraphs** (2024) | open-vocab object graph | ✗ | ✗ | ✗ | **静态重建**；PBD-AG 的 adapted 控制即取它的关联+更新规则 |
| **HOV-SG** (2024) | floor/room/object 层级图 | ✗ | ✗ | ✗ | 强于层级组织，但无时序修订机制 |
| **Hydra** (2022) | metric-semantic scene graph | ✓（增量优化） | ✗ | ✗ | 增量但面向重建/SLAM，无存在性证据门控 |
| **Clio** (2024) | 任务相关粒度图 | ✓（在线选粒度） | ✗ | ✗ | 选"粒度"，不选"是否要近距离看" |
| **DynaMem** (2024) | mutable spatio-semantic **voxel** memory | ✓ | 部分（在线更新） | ✓（可探索未见环境） | **point-centric**：不维护持久对象身份、无层级支撑关系、不把变化记成 typed event。PBD-AG 的强对手（F1 `.757`, IDF1 `.688`） |
| **DovSG** (2025) | 开放词表 3D 场景图 | ✓（长期操作中更新子图） | 部分 | ✗ | 动态更新阶段**从已初始化的全局场景图开始**；PBD-AG 从空图 bootstrap |
| **VLFM** (2024) | frontier + 语言 value | ✓ | ✗ | ✓ | 把语义赋给**未探索** frontier；PBD-AG 刻意只在**已发现** fixture 上巡检 |
| **SCOUT** (2026) | 语义不确定性 ↔ 场景覆盖 | ✓ | ✗ | ✓ | 不确定性耦合"覆盖"；PBD-AG 耦合"关系未决的持久状态" |
| **PBD-AG** (本文) | **baseline($B^{(0)}$) + delta($M_t$) + audit stream($\mathcal{E}$)** | ✓ | **✓ 显式（visibility-gated log-odds）** | ✓（graph-uncertainty 驱动） | 唯一把"负证据需几何可观测"作为硬门 + 把变化记成 typed event 的 |

**面试 Tip**：被问到"PBD-AG 和 DynaMem / ConceptGraphs 有什么本质区别"时，不要答"F1 更高"——要答**三层**：
1. **表示层**：DynaMem 是 point-centric voxel memory，没有持久对象身份和层级支撑关系；ConceptGraphs 是静态重建。PBD-AG 是 baseline（冻结结构）+ delta（可修 track）+ 有序 audit event 三件套。
2. **证据层**：别人把"没检测到"直接当负证据；PBD-AG 要求 **3D bbox 投影可见 + 未遮挡（0.15 m 容差）+ ≥2 样本通过**，才允许扣 log-odds（$\eta_m=0.70$，而缓存否决 $\eta_r=2.20$）。
3. **启动层**：DovSG 的动态更新从已初始化全局图开始；PBD-AG 从 $B^{(0)}=\varnothing$、occupancy 全 unknown 开始，靠 frontier + fixture 关联 + 跨 batch 确认自主 bootstrap。

再补一句诚实的边界：**这些差异在共享证据的受控实验里被单独隔离（Table 1/2），而自主全图评估是分开报告的**——论文自己强调 adapted 控制不是端到端复现。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-17)

**Repo 状态核查**：论文全文（含 v2 HTML 版）**未给出任何 repo URL**。文首出现的 "Report GitHub Issue ×" / "Submit in GitHub" 是 **arXiv 自身的 HTML 页面模板控件**，不是作者仓库；正文与参考文献中亦无 `github.com` 超链接。因此：

> **官方 repo 未在论文中给出，以下 pitfall 由 §6 失败模式 + 方法约束推导（未经 issue 验证）。**

---

**Pitfall 1 — 深度偏差会静默击穿可见性门，且降级后不可察觉**

- **机制来源**：§6 假设 A2（0.15 m 深度容差）+ §2 式(3) 的 $V_i(t)$ 判据 + 原文 "It is considered unoccluded when $d_{\rm meas}+0.15\,\mathrm{m}\ge d_{\rm expected}$"。
- **推导**：真实 RGB-D（结构光/ToF）对深色、透明、远距离表面存在系统性偏差；一旦偏差超过 0.15 m，$V_i(t)$ 在本该为 0 时被置 1，负证据开始累积。**该失效不会报错、不会有日志告警**——它表现为 false absence 缓慢上升，与 ablation "w/o visibility gate"（`.014 → .262`）同一条滑坡。
- **工程动作**：在部署前用**静止场景 + 已知 GT 物体**做一次 $V_i(t)$ 误触发率标定；若误触发率不可忽略，应按传感器/量程**重标定 0.15 m 这一常数**（注意：论文把增量与几何常数都标为 frozen，即**没有为这个场景预留自适应接口**）。

---

**Pitfall 2 — 0.8 m 中心距 + 0.78 cosine 的贪心匹配在密集/同款物体场景会锁错配对**

- **机制来源**：§6 失败模式 2（Benevolence 因 "repeated fixture geometry and restricted viewpoints" 退化，coarse F1 掉到 `.777`、fine F1 掉到 `.550`）+ §1.1 关联约束 "3D center distance below 0.8 m, and SigLIP cosine similarity above 0.78" + "Eligible pairs are greedily matched one-to-one"。
- **推导**：当场景中有多只同类、相距 < 0.8 m 的物体（酒店/卧室常见），贪心一对一可能先锁错对；唯一的兜底是 "unique-class fallback"——但它只在**类唯一**时生效，同类多实例场景不适用。外观门在无 embedding 时**被直接省略**（原文），此时只剩几何门，风险进一步放大。
- **工程动作**：把 $\Sigma_i$（最近 32 个 center 的协方差）纳入关联代价做最小信息量门控——注意论文明确 "$\Sigma_i$ is not used for association"，所以这是**超出论文范围的改动**，需要自行验证。

---

**Pitfall 3 — Fine 节点脱钩动态前端 ⇒ 已接地的细粒度物体"移动后无人负责"**

- **机制来源**：§6 失败模式 5 + 原文 "Fine nodes from active inspection are attached through the capture ledger and do not re-enter the frame-level dynamic association front end."
- **推导**：巡检确认的子节点一旦挂到 canonical fixture，就**脱离了 Eq.(3) 的 existence log-odds 更新回路**。因此一个被巡检确认过的杯子随后被挪到另一个桌子，**不会触发 `move` 事件**（`move` 仅由 frame-level 动态关联在位移 ≥0.35 m 时发出）。它只会停在旧位置，直到该 fixture 因其他原因（例如被 demote/remove）再次进入 $\mathcal{Q}_t$ 重巡。
- **工程动作**：下游 planner 不能把 fine 节点的位置当作"当前世界状态"来用；若需要细物体级的持久追踪，必须**自行把 fine 节点重新挂回动态前端**（论文的架构明确不做这件事）。

---

**Pitfall 4 — 巡检目标只能位于 "connected known-free cell"，未探索区域里的 fixture 会被无限 defer**

- **机制来源**：§6 强制约束 "Candidate views are connected known-free cells satisfying standoff, inflated-map reachability, line-of-sight, projected-coverage, and image-margin constraints" + "If a fixture has no feasible view, it is deferred while the controller checks the next queued target; frontier exploration resumes when none is reachable." + 600 keyframe coarse 预算 "Once exhausted, no new coarse candidate is admitted"。
- **推导**：两层预算叠加会产生**饥饿**：若某 fixture 恰好在一处被障碍膨胀图"包住"的狭窄角落（unreachable within inflated map），它会**永久停在 defer 状态**，$u_i$ 虽然很高但永远不被服务；同时 600 keyframe 预算耗尽后新 fixture 不再入场，导致 baseline 长期不完整——而且这一切**没有任何超时/告警机制**（只有 retry-cooldown 排除）。
- **工程动作**：部署侧需自行加入"defer 计数 / 最大等待时间"监控，否则会在长时程运行中默默积累一批高不确定度、永不被解决的 fixture。

---

[← Back to Scene-Graph Memory & Long-Horizon Robotics README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文（v2, 2026-08-12）· 未在真机复现的数字标 `UNVERIFIED`
> **Zero-fabrication 声明**：§4 latency/VRAM/FPS/硬件型号全文缺失，已标「论文未报告」；§5 所有数据集名、阈值、指标数字均逐字取自全文；§8 无 repo URL，pitfall 为 §6 失败模式 + 方法约束推导，未经 issue 验证。

<!-- source: https://arxiv.org/abs/2608.10449 -->
