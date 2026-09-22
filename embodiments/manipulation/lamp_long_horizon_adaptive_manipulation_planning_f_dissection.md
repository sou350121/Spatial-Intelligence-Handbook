<!-- ontology-5axis
problem: n/a
representation: n/a
sensor: n/a
paradigm: hybrid
time: incremental
ref: ../../cheat-sheet/ontology.md §5
-->

# LAMP：杂乱空间中多机器人长时域自适应操作规划 (LAMP: Long-Horizon Adaptive Manipulation Planning for Multi-Robot Collaboration in Cluttered Space)

> **发布时间**：2026-07-08（arXiv:2606.29358v2 [cs.RO]）
> **论文 / 模型名**：LAMP（LAMP-A* / LAMP-Lazy）；作者 Shuai Zhou, Yorai Shaoul, Jiaoyang Li，Carnegie Mellon University Robotics Institute
> **核心定位**：把「机器人级可操作性验证」直接塞进物体级路径搜索的每一次边求值里，并用 lazy evaluation + D* Lite 增量缓存把它压到可闭环重规划——解决的正是 GCo 这类「先规划物体轨迹、再事后验证可操作性」的混合方法在最杂乱环境里必然失效的痛点。

导语：多机器人协同推物问题的搜索空间随机器人数、时域、杂乱度组合爆炸。GCo 走的是「物体级 surrogate 规划 + 学习到的短程操作原语」路线，隐含假设「选出的物体运动一定能被机器人实现」；在狭窄通道里这条假设直接崩掉。LAMP 的答案是：不要事后过滤，把可行性验证变成搜索的一部分，再用 lazy 策略把验证的代价延后并缓存。

---

## X-Ray 开场

- **解决什么问题**：多机器人非抓取式（non-prehensile，即推）协同搬运，在极密障碍中做长时域规划。已有方法要么端到端 RL（杂乱环境与长时域下复合误差爆炸），要么在简化的「物体轨迹 surrogate 空间」里规划、把学习到的操作原语当作事后执行器（狭窄空间里物体路径可行但机器人根本摆不进去）。
- **提出了什么**：LAMP-A*（在耦合 object-robot 配置空间里 eager 验证的 A*）与 LAMP-Lazy（先用 D* Lite 出物体级路径，再 lazy 验证，并用一棵以目标为根的 `Tree_eval` 缓存已验证 transition + 机器人轨迹）。
- **对 spatial AI 研究者意味着什么**：这是一份「学习模块如何以正确接口嵌入经典搜索」的清晰范例——学习的输出不是动作，而是**搜索边的可行性谓词与代价**；而 lazy + incremental 是把这种昂贵谓词变成可实时重规划的关键工程杠杆（ontology: paradigm=hybrid, time=incremental 正好落在这里）。

---

## 📍 研究全景时间线

```
早期 planning-centric 多机操作
  · 手工设计 manipulation primitive [4] / 大规模 rearrangement [5]（不建模接触物理）
        │
        ▼
纯端到端学习
  · MAPush [1] 等分层 RL：低层运动控制 + 高层交互策略
  · 优势：不需动力学；劣势：杂乱 + 长时域 → OOD 复合误差
        │
        ▼
TAMP + 学习（经典混合范式成型）
  · 用学习建模 action [9,10] / motion shortcut [11] / operator [12,13] / predicate [14,15]
  · 多机侧：学习 heuristic [16] / 局部协调策略 [17]
        │
        ▼
GCo [3]（本文最直接的基线）
  · 物体级规划 + 学习短程操作原语 + AMRMP 路由（Gspi）
  · 假设：所选的物体运动总能被机器人实现 → 狭窄空间失效（Fig.1 的红路径）
        │
        ▼
lazy / 增量搜索工具成熟
  · Lazy PRM [18]、LazySP [19]：推迟昂贵边求值
  · D* Lite [20]：环境变化时修复而非重规划
        │
        ▼
★ 本文 LAMP（arXiv:2606.29358v2, 2026-07-08）
  · 把 manipulability 验证注入搜索边；lazy 延后 + Tree_eval 增量缓存 → 闭环重规划
  · 本文局限：仅 2D planar、非抓取推、3 机器人、静态障碍；
    LAMP-Lazy 在 Maze/Warehouse 仍有失败（贴边路径把物体推出地图），
    路径代价略高于基线（拿成功率和规划时间换最优性）
```

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比表

| 模块 | 输入 | 输出 | 训练 / 推理差异 | 本文贡献？ |
|---|---|---|---|---|
| `GCo_DC`（学习到的短程操作生成器） | 物体观测（二值图 `ℐ`）、物体运动原语 `m_O`、机器人预算 `B`、候选数 `K` | 接触点集 `C_manip = {c_i ∈ R²}`、操作轨迹 `T_manip = {τ_i^manip}` | **训练**：用 GCo 原版 20,000 样本 MuJoCo 数据集训练；**推理**：批量生成 K 个候选（按 budget） | ❌ 复用 GCo [3] |
| `Gspi`（anonymous multi-robot motion planner, AMRMP） | 当前机器人配置 `q_R`、目标接触点 `C_manip` | 机器人-接触点分配 + 无碰轨迹 `T_move` | 无训练，纯规划器 | ❌ 复用 GCo [3] |
| `Verify`（本文核心子程序，Alg.1 L18–26） | `q_O^curr`, `m_O`, `q_R^curr` | `T_move, T_manip, C_R` 或 `∅` | 无训练；推理时调用上面两者 | ✅ |
| `Reassign` | `C_R, T_manip, q_R^curr` | 按最短距离配对的分配；未配对机器人去「等待点」 | 等待点用 BFS 就近找无碰配置 | ✅ |
| `LAMP-A*` | 初始 object+robot 配置、primitives | 全时域已验证计划 | **推理型**：搜索中 eager 调用 `Verify` | ✅ |
| `D* Lite` | 物体级图、`q_O^now` | 物体级路径 `P_O` | 无训练；增量修复 | ❌ 复用 [20] |
| `Tree_eval`（增量求值树） | 已验证的 `q_O^curr → q_O^next` transition | `(q_O^next, C_R, T_manip, D_T)`，`D_T` 是「机器人配置 → 全轨迹」缓存 | 只存**通向 goal 的路径上**的 transition，树根在 `q_O^goal` | ✅ |
| `LAMP-Lazy` | 同上 | 全时域计划 + 可复用求值树 | **推理型**：lazy 验证 + 缓存复用 + 漂移触发重规划 | ✅ |

### 1.2 关键机制

**⚡ Eureka Moment：不要把「机器人能不能推得动」当作规划结束后的过滤器——把它变成搜索里那条边的求值谓词，然后用 lazy 把这次求值推迟到「一条完整候选路径已经拿到」之后，再用一棵以目标为根、以物体构型为 key 的求值树把重规划变成缓存查找。**

论文原话两条支撑：
1. *"instead of solving a surrogate object-planning problem and applying learned manipulation models only after the fact, we should incorporate robot-level manipulation feasibility directly into the search."*
2. *"LAMP-Lazy that dramatically reduces planning time through lazy evaluation and penalization, allowing us to rapidly replan when execution deviates…"*

配套的三个具体机制：
- **Budget 降序扫描**：机器人预算大 → 操作精度高但需要更大工作空间余量；所以在 `Verify` 里从 `B = N` 逐级降到 1，先试高精度，狭窄时才优雅降级。
- **失败 ≠ 不可行 → 惩罚而非删边**：`GCo_DC` 是随机的，一次 `Verify` 失败不代表这条物体 transition 真的不可行，所以把父状态以 **+10⁴ 惩罚代价**重新压回 Open list，等更有希望的路走完再回头重试。
- **增量重规划**：漂移超过预设阈值 → 直接在当前位置调 `Plan()`，`D* Lite` 增量修复物体级路径，`Tree_eval` 里已缓存的 transition 直接命中（`if q_O^curr ∈ Tree_eval then break`）。

### 1.3 信息流 / 架构图

```
                 ┌──────────────────────── LAMP-Lazy 主循环 (Alg.2) ────────────────────────┐
                 │                                                                          │
  q_O^now,q_R^now│   ┌──────────┐   P_O (物体级路径)   ┌──────────────┐                     │
  ──────────────►│──►│ D* Lite  │────────────────────►│  Lazy Verify │                     │
                 │   └────▲─────┘                     │  (沿 P_O 逐边)│                     │
                 │        │                           └──────┬───────┘                     │
                 │        │ UpdateChange(cost += 10⁴)        │ 失败: 惩罚该边 + 清空 Tree_new │
                 │        └──────────────────────────────────┤                              │
                 │                                           │ 成功                          │
                 │                                           ▼                              │
                 │                                   ┌───────────────┐                      │
                 │                                   │  Tree_new /   │ 命中缓存则直接回溯      │
                 │                                   │  Tree_eval    │─────────────────┐    │
                 │                                   └───────────────┘                 │    │
                 │                                                                   ▼    │
                 │   Execute(T_R) ──► Drift(q_O^now, q_O^next)? ──是──► 回到 Plan(q_O^now) │
                 └────────────────────────────────────────────────────────────────────────┘

        ┌───────────────────────── Verify(q_O^curr, m_O, q_R^curr) ─────────────────────────┐
        │ ℐ = Observe(q_O^curr)                       # 二值图                             │
        │ for B = N … 1:                              # budget 降序：精度优先              │
        │   for (C_R, T_manip) in GCo_DC(ℐ, m_O, B, K):                                    │
        │       if Collide(C_R, T_manip): continue    # ← 只查机器人-障碍 / 机器人-机器人   │
        │       Reassign(C_R, T_manip, q_R^curr)      # 最短距离配对；落单者去等待点        │
        │       T_move = Gspi(q_R^curr, C_R)          # 匿名多机路由                         │
        │       if T_move ≠ ∅: return T_move, T_manip, C_R                                 │
        │ return ∅, ∅, ∅                                                                    │
        └──────────────────────────────────────────────────────────────────────────────────┘
```

注意 Fig.2 的注释：图里的离散化比实验粗，实际物体级图更密。

---

## 2 · 数学核心

📌 **Napkin Formula**

```
在物体构型图上求最短路径：
    边代价   c(e) = 𝒯_R^e.cost              （机器人实现该 transition 的轨迹代价）
    边可行   feas(e) = ∃B≤N, ∃k≤K : ¬Collide(C_R^k, T_manip^k) ∧ Gspi(q_R, C_R^k) ≠ ∅
    不可行 → 不删边，而是  c(e) += 10⁴
即：learned manipulation 是边谓词，不是后置执行器。
```

**目标**：求一串机器人轨迹 `𝒯 = {τ¹,…,τ^N}`，使物体从 `q_O^init` 到 `q_O^goal`，全程无机器人-机器人、机器人-障碍、物体-障碍碰撞，并且能在线重规划。

**形式化（论文 II-A / III-A）**

- 机器人 `ℛ = {R¹,…,R^N}`，`R^i` 是半径 `r` 的圆盘，构型 `q_R^i ∈ Q_R ⊆ ℝ²`；物体 `q_O ∈ Q_O ⊆ SE(2)`；工作空间 `W ⊆ ℝ²`。
- 搜索状态：`s = (q_O, q_R, s_parent)`，`q_R = (q_R^1,…,q_R^N)`。
- 边 `(s, s')` 关联轨迹 `𝒯_R^(s,s') = 𝒯_move ⊕ 𝒯_manip`（`⊕` 为拼接：先走到接触点，再执行推动）。
- 变量说明：`m_O` 是预定义的物体运动原语；`K` 是每个 budget 下**批量生成**的候选数；`B` 是机器人预算（参与操作的机器人数上限）；`N` 是机器人数；`𝒟_𝒯` 是「机器人当前配置 → 全轨迹」缓存。

**`Verify` 的判定式**

```
Verify(q_O^curr, m_O, q_R^curr) =
  ∃ B ∈ {N, N-1, …, 1}, ∃ k ∈ {1,…,K}  s.t.
      (C_R^k, T_manip^k) ~ GCo_DC(Observe(q_O^curr), m_O, B, K)
      ∧ ¬Collide(C_R^k, T_manip^k)
      ∧ Gspi(q_R^curr, C_R^k) ≠ ∅
```

**`LAMP-A*`**：标准 A*，`f = g + h`，`g` 沿 `𝒯_R.cost` 累积；命中新状态时先查 `Explored(q_O^next, q_R^next)`，若存在则走 `UpdateCost`（按代价升序做 best-first 传播，重设 parent，直到无更新），否则 `AddChild` 入队。父状态以 `+10⁴` 惩罚重新入队，允许将来用不同采样再展开。

**`LAMP-Lazy`**：底层用 `D* Lite`（标准形式，论文未展开公式，引用 [20]）维护物体级一致性：

```
rhs(s) = min_{s' ∈ Succ(s)} ( c(s,s') + g(s') )        （标准 D* Lite）
key(s) = [ min(g(s), rhs(s)) + h(q_O^now, s) + k_m ;  min(g(s), rhs(s)) ]
```

论文使用的是其三个概念分量：`Initialize`、`PlanShortestPath`、`UpdateChange`。边验证失败时调 `UpdateChange` 抬高该边代价。

---

## 3 · 带数字走一遍（玩具设定，非论文数值）

> 以下数字全部自造，仅用于演示 eager vs lazy 的代价结构。

**设定**：`N = 3` 机器人，`B_max = 3`，每 budget 候选数 `K = 4`，物体级栅格 10×10（格距 0.1 m），起 `q_O^init = (1,1)`，终 `q_O^goal = (9,9)`，惩罚 `10⁴`。

1. `D* Lite` 先出一条 9 步的 L 形物体路径 `P_O`（不经窄缝，贴墙拐角）。
2. 沿 `P_O` 第 3 条边（物体从 `(3,1)` 到 `(4,1)`），`m_O = +x`：
   - `B = 3`：`GCo_DC` 出 4 个候选，其中 1 个接触点撞障碍 → `continue`；剩 3 个 `Reassign` 后 `Gspi` 返回 `∅`（通道净宽 0.35 m，3 台半径 `r` 的机器人挤不进去）。
   - `B = 2`：同样 `Gspi = ∅`。
   - `B = 1`：`Gspi` 成功，但单机推的 `T_manip` 精度低 → 预计漂移大于阈值。
   - 结论：这条边要么不可行，要么可信度差。
3. 该边代价 `c += 10⁴` → `D* Lite.UpdateChange` → 新 `P_O` 绕开窄缝多走 4 步（路径代价升高，但可行）→ 缓存进 `Tree_eval`。
4. **代价账**：一次 `Verify` 最坏 ≈ `B_max × K = 3 × 4 = 12` 次 `GCo_DC` 前向 + 至多 12 次 `Gspi`。
   - eager A*：展开阶段大约会调 `Verify` ~30 次 ⇒ ~360 次模型/规划调用。
   - lazy：只在候选路径上验证 3 条边就发现要改路 ⇒ ~36 次调用。
   - 玩具估算差 ~10×（`UNVERIFIED`，仅示意 lazy 的收益结构）。

**对照论文真值**：Fig.4 显示 LAMP-Lazy 的每段规划时间中位数约 2–3 秒；长时域 9 物体「IROS」任务里平均 **2.07 秒/段**；而 LAMP-A* 被迫设 500 s 累计规划上限，在 Maze/Tilt/Warehouse 直接超时。

---

## 4 · 工程视角

| 维度 | LAMP-A*（eager） | LAMP-Lazy（lazy + 增量） | 来源 |
|---|---|---|---|
| 搜索空间 | 耦合 `(q_O, q_R, parent)` | 物体级图 + `Tree_eval` 缓存 | 论文 |
| 每段规划时间 | Fig.4 显示显著高于 LAMP-Lazy（**具体中位数论文未报告**） | 中位数约 **2–3 秒/段**（Fig.4）；长时域案例 **2.07 秒/段** | 论文 |
| 单场景规划时间上限 | 累计 **500 s** | 论文未报告（无累计上限） | 论文 |
| 执行迭代预算 | **100** 次操作迭代（与 GCo 相同） | **100** 次 | 论文 |
| 机器人数量 | **3** | **3** | 论文 |
| 硬件 / GPU / 显存 | 论文未报告 | 论文未报告 | — |
| 真机 FPS / 控制频率 | 论文未报告 | 论文未报告 | — |
| 环境 | MuJoCo 仿真 | MuJoCo 仿真 | 论文 |

**Trade-off 解读**

1. **成功率 vs 路径代价**：Fig.5 明确写 LAMP-Lazy「generally produces solutions with comparable or slightly higher path costs」；`GCo_var` 与 `LAMP-A*_replan` 在各自成功的场景里代价更低。LAMP-Lazy 主动放弃了最优性，换成功率与规划时间。
2. **eager vs lazy**：`LAMP-A*_replan` 找到了不少全时域路径（Table II：Random 100%、Maze 8%、Tilt 32%、Warehouse 40%），但因为反复重搜，「requires excessive planning time, failing to reach goals within our 500s limit」。lazy 的收益不是「算得更准」，而是「算得更少」。
3. **budget 降序**：从 `N` 往下降是精度优先策略；其反向代价是，在极窄处必须接受单机推动，而单机推动精度低 → 漂移 → 触发重规划 → 更多规划调用。这是一个自反馈的成本环。
4. **缓存的正确性依赖静态障碍**：`Tree_eval` 以 `q_O^curr` 为 key 存验证结果，论文未描述任何「障碍布局变化 → 缓存失效」机制（见 §6 隐含假设与 §8 pitfall 3）。长时域 IROS 任务中 clutter 会随摆放单调增加，这是部署时最先要补的地方。
5. **部署约束**：整套框架要求 `Verify` 能被高频调用（每段 2–3 s 意味着单次 `Verify` 必须比这更快），而真实机器人上 `GCo_DC` 与 `Gspi` 的调用成本论文未报告，无法判断真机实时性。

---

## 5 · 数据与评测

**场景构成（IV-A）**

- 4 张地图：**Random、Maze、Tilt、Warehouse**（Fig.3）；Random 相对稀疏，其余三张更杂乱。
- 每张图 **25** 个不同场景：物体起/终点、物体类型（**circle 和 rectangle**）、物体尺寸各异 → 合计 **100** 个测试场景。
- 每个场景 **3** 台机器人协同推一个物体到目标，需穿过障碍间的狭窄通道。

**成功判据（逐字）**

- MAPush：物体进入目标位置 **0.5 m** 内即成功，**忽略朝向**（沿用 [3]）。
- 其他所有方法：最终物体位姿与目标 **平移 0.1 m、朝向 0.1 rad** 以内。
- 且执行/时间预算内完成，且**物体全程完全在地图内**。

**预算设置**：GCo 与 LAMP 允许最多 **100** 次操作执行迭代；MAPush 最多 **2 simulated minutes**；LAMP-A* 额外加 **500 s** 累计规划时间上限。

**基线与其训练条件**

| 方法 | 来源 / 训练条件 |
|---|---|
| MAPush [1] | 开源实现 `github.com/collaborative-mapush/MAPush`，3 机器人，用原版 MQE 框架与 reward 结构**从零训练 100M 步** |
| `GCo_ori` | GCo 原版，障碍周围保守 safety buffer 膨胀 |
| `GCo_var` | 把 buffer 设为 0 的修改版本，以进入更紧空间 |
| `GCo_DC`（被 LAMP 复用） | 开源实现 `github.com/yoraish/gco`，用原版 **20,000 样本 MuJoCo [21] 数据集**训练；LAMP-A* 与 LAMP-Lazy 都用同一个模型 |
| LAMP-A*_ori | 开环执行 |
| LAMP-A*_replan | 漂移触发重规划的闭环执行 |
| LAMP-Lazy | D* Lite + 闭环重规划 |

**主结果（Table I，整体成功率）**

| Method | Random | Maze | Tilt | Warehouse |
|---|---|---|---|---|
| MAPush | 8% | 0% | 0% | 0% |
| `GCo_ori` | 0% | 0% | 0% | 0% |
| `GCo_var` | 68% | 12% | 28% | 20% |
| `LAMP-A*_ori` (ours) | 24% | 0% | 0% | 12% |
| `LAMP-A*_replan` (ours) | 88% | 0% | 8% | 0% |
| **LAMP-Lazy (ours)** | **100%** | **96%** | **100%** | **88%** |

**全时域规划成功率（Table II，执行前是否找到完整路径）**

| Method | Random | Maze | Tilt | Warehouse |
|---|---|---|---|---|
| LAMP-A* | 100% | 8% | 32% | 40% |
| LAMP-Lazy | 100% | 100% | 100% | 100% |

**长时域案例（IV-B）**：机器人逐个搬运 **9 个物体**拼出「IROS」logo，环境随物体摆放越来越杂乱。MAPush 与 `GCo_var` 在多个阶段因机器人被卡在角落失败；`LAMP-A*_replan` 与 `LAMP-A*_ori` 因 clutter 增加超过 500 s 规划时限失败；**LAMP-Lazy 把 9 个物体全部搬到目标，平均规划时间仅 2.07 秒/段**。

> 阅读提示（复现者注意）：正文 §IV-A1 写的是 "Table II shows the percentage of scenarios where the object reached the goal"，但 Table II 的 caption 是 *Full-horizon planning success rate*；按 caption 与数据内容，成功率表实为 Table I。这是论文内部的表格编号不一致，别照错表取数。

---

## 6 · 能力与失败模式

### 能做

- **极密杂乱 + 长时域**：LAMP-Lazy 在 Maze/Tilt 上 96%/100%，在 Warehouse 88%，全时域规划成功率四张图全部 100%。
- **闭环抗漂移**：`LAMP-A*_replan` 的 Random 成功率（88%）远高于开环 `LAMP-A*_ori`（24%），说明「漂移触发重规划」这一层本身有效；LAMP-Lazy 把它的代价压到了可承受范围。
- **换障碍布局 / 换时域不需重训**：论文明确声称 "generalizes to new obstacle layouts and task horizons without retraining"。
- **9 物体序列装配**这类 clutter 单调增加的场景。

### 不能做 / 具体失败模式

1. **贴边路径把物体推出地图**（LAMP-Lazy 的 Maze 96%、Warehouse 88% 的全部失败来源）：论文原话——"the planned object paths are close to workspace boundaries, and the push trajectories proposed by `GCo_DC` cause the object to intersect the workspace boundary during execution, which is less likely in the more open Random map."
2. **`GCo_var` 类失败：机器人被卡在角落**——"robots become trapped in corners due to lack of robot-level feasibility verification"。这正是 LAMP 要修的病。
3. **`LAMP-A*_replan` 类失败：找得到路但算不完**——Table II 显示它确实找到路径（Maze 8%、Tilt 32%、Warehouse 40%），但规划时间超过 500 s。
4. **MAPush / `GCo_ori`：几乎全灭**——原因分别是 obstacle-agnostic navigation 与 overly conservative safety buffers。
5. **范围外**：只处理 planar（`W ⊆ ℝ²`）、SE(2) 的**非抓取推**（non-prehensile），没有抓取、没有 3D、没有可变形体、没有未知障碍。

### 隐含假设 (Hidden Assumptions)

- **A1｜静态障碍、且物体级图有界**：`Verify` 的碰撞检查只覆盖 `Collide(C_R, T_manip)`（机器人-障碍、机器人-机器人）与 `Gspi` 的机器人路由；**物体扫掠体与工作空间边界的关系不在 `Verify` 里**。成功判据却要求 "keeping the object entirely inside the map throughout execution"。这两者之间的缝隙直接产生了 §6 失败模式 1。
- **A2｜`GCo_DC` 的泛化能力**：换障碍布局不重训的前提是，在 20,000 样本 MuJoCo 数据集上训出的模型对新 clutter 仍然给出可用候选。长时域里 clutter 单调上升，属于明确的分布外迁移。
- **A3｜"Verify 失败 ≠ 不可行" 需要被正确记账**：因为 `GCo_DC` 是随机的，一次失败只是这一次采样失败；论文用「+10⁴ 惩罚 + 重新入队」来保留将来重试的可能。这隐含假设**惩罚值足够大到能促使换路、又不会让可行边被永久埋掉**，且「more promising paths are exhausted」这个时机可判定。
- **A4｜drift 只以物体位移定义**：`Drift(q_O^now, q_O^next)` 比较的是物体当前位姿与计划位姿；机器人自身漂移若没引起物体偏移，不触发重规划（只在缓存回溯时若 `q_R^curr ∉ D_T` 才重新 `Reassign` + `Gspi`）。
- **A5｜接触点数量与机器人数匹配时才调 `Gspi`**："When the number of contact points matches the number of robots, we invoke Gspi"；不足者靠 `Reassign` 送去等待点。
- **A6｜`Tree_eval` 的语义是「目标根树 + 静态环境」**：条目 `Tree_eval[q_O^curr] = (q_O^next, C_R, T_manip, D_T)` 只按物体构型索引，只有 `Verify` 失败才触发 `D* Lite.UpdateChange`。论文未描述任何因障碍变化而失效缓存的机制（对应 §8 pitfall 3）。
- **A7｜模块可替换性是有边界的**：论文声称 "do not rely on their internal structure and can use any sub-component implementation"，但 `Verify` 事实上要求子模块提供 **批量** `(C_R, T_manip)` 生成接口（`GCo_DC` 的 `B, K` 参数）与一个接受接触点集合的匿名路由接口（`Gspi`）。换实现必须满足这个接口契约，否则 budget 降序扫描与 10⁴ 惩罚重试都无处落地。

---

## 7 · 与相关工作对比

| 方法 | 规划层 | 学习层 | 可行性验证时机 | 重规划 | 关键局限 |
|---|---|---|---|---|---|
| MAPush [1] | 无显式规划（分层 RL） | 端到端策略 | — | 策略内隐式 | obstacle-agnostic，本实验中 Random 仅 8% |
| `GCo_ori` [3] | 物体级 surrogate 规划 | `GCo_DC` 短程操作原语 + `Gspi` | **事后**（规划完再生成操作） | 逐段推进，不做搜索级修复 | safety buffer 过度保守 → 0% |
| `GCo_var` | 同上但 buffer = 0 | 同上 | 事后 | 同上 | 机器人卡角落（缺 robot-level 可行性验证）；Random 68%，杂乱图 12–28% |
| `LAMP-A*_ori` | A* over `(q_O, q_R)` | 复用 `GCo_DC`/`Gspi` | **搜索中 eager** | 无（开环） | 规划超时 + 执行漂移 |
| `LAMP-A*_replan` | 同上 | 同上 | eager | 漂移触发，但每次从搜索重来 | 能找到路但算不完（500 s 上限） |
| **LAMP-Lazy** | D* Lite 物体级 + 缓存 | 同上 | **lazy（完整候选路径后逐边）** | 增量（`D* Lite` + `Tree_eval`），重规划变缓存查找 | 路径代价略高；贴边场景仍失败 |

**一句话差异定位**：GCo 把 learned manipulation 当作「规划之后的执行器」；LAMP 把它当作「搜索边的可行性谓词」，并用 lazy + incremental 让这个昂贵谓词变得负担得起。

### 🎤 面试 Tip

被问「LAMP 与 GCo 差在哪、为什么值得一篇论文」，答这三点：
1. **接口变了**：学习模型的输出从"动作/轨迹"升级成"边的可行性谓词"——这一步让搜索可以推理「物体路径虽然短，但机器人摆不进去」，这是 GCo 结构上做不到的（Fig.1 的红/绿路径就是这个论点的可视化）。
2. **工程杠杆是 lazy + incremental，不是更准的模型**：同一个 `GCo_DC` 权重（20,000 样本 MuJoCo 数据集）同时喂给 LAMP-A* 和 LAMP-Lazy；LAMP-Lazy 的收益全部来自「推迟验证 + 以目标为根的求值树缓存」，代价是路径次优。
3. **把失败诚实说清楚**：LAMP-Lazy 的残余失败全部发生在贴边路径（Maze 96%、Warehouse 88%），根因是 `Verify` 不检查物体与工作空间边界的干涉。面试里主动指出这条，比背成功率数字更能证明你真读懂了。

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-09-22)

**仓库状态核查**：论文给出的是 project page `https://multi-robot-lamp.github.io/`（正文中为纯文本，非嵌入 PDF 的可点击超链接），**未给出 LAMP 自身的代码仓库 URL、commit hash 或 issue 编号**。全文出现的两个 `github.com` 链接均为**基线**仓库：`github.com/collaborative-mapush/MAPush`（MAPush 开源实现）与 `github.com/yoraish/gco`（GCo 开源实现）。因此本节**无社区 issue 流可依据**；以下 3 条 pitfall 由 §6 的具体失败模式 + §1.3/§4 的方法约束**机械推导**得出，未经 issue 验证。

### Pitfall 1｜`Verify` 不检查「物体 vs 工作空间边界」→ 贴边场景必然失败（对照 §6 失败模式 1）

- **失败模式**：LAMP-Lazy 在 Maze 96%、Warehouse 88%，全部失败都是 `GCo_DC` 的推动轨迹让物体在执行中越出工作空间边界。
- **方法约束**：`Verify`（Alg.1 L22）唯一的几何过滤是 `if Collide(C_R, T_manip) then continue`，即机器人-障碍/机器人-机器人；物体自身的扫掠体与地图边界从不进入判定，`Gspi` 也只负责把机器人送到接触点。
- **后果**：一条 transition 可以被 `Verify` 判为可行、被写进 `Tree_eval`、被执行，然后物体出界 → 场景判失败。而且因为该边已被缓存为"已验证"，闭环重规划不会去质疑它。
- **工程动作**：部署前在 `Verify` 里补一条「物体沿 `m_O` 的扫掠体 ∩ 工作空间边界 = ∅」的硬约束（或在 `Tree_eval` 写入前做一次边界测试）。

### Pitfall 2｜固定 10⁴ 惩罚 + 随机生成器 → 可行边可能被永久压制、结果不可复现（对照 §6 隐含假设 A3）

- **失败模式**：论文自己声明 "this does not necessarily mean that the object transition itself is infeasible"，即 `Verify` 失败是采样失败而非真不可行。
- **方法约束**：补偿手段是把父状态以 **10⁴（论文写作 10⁴，"in our implementation"）**的惩罚代价重新压回 `Open`，仅在 "more promising paths are exhausted" 时才可能重试。同时 `Verify` 每个 budget 只取 `K` 个候选，而 **`K` 的取值论文未报告**，`GCo_DC` 又是随机的。
- **后果**：同一个场景、同一障碍布局，两次运行可能因为采样不同而给出不同成功率；一个真正的可行解若连续 `K` 次采样失败，就会被 10⁴ 的固定代价长期压住。
- **工程动作**：把随机种子、`K`、budget 降序策略、10⁴ 惩罚值全部显式配置并记录；对「被惩罚过的边」做有限次数的强制重试预算，而不是依赖「更有希望的路走完」这一模糊条件。

### Pitfall 3｜`Tree_eval` 无缓存失效机制 → 障碍变化后复用陈旧已验证 transition（对照 §6 隐含假设 A6 + §4 trade-off 4）

- **失败模式**：IV-B 的长时域 IROS 装配任务里，9 个物体逐个落到目标位，clutter「compounding the difficulty for later objects」——即障碍集合在任务过程中单调增长。
- **方法约束**：缓存条目为 `Tree_eval[q_O^curr] = (q_O^next, C_R, T_manip, D_T)`，**只以物体构型为 key**，不含任何环境指纹；唯一的更新入口是 `D* Lite.UpdateChange(q_O^curr, q_O^next)`，而它只在 `Verify` 失败（Alg.2 L19、L32）时被调用。论文未报告任何由障碍变化触发的缓存失效流程。
- **后果**：一个在稀疏时验证通过的 transition，在 clutter 增加后可能已经不成立，但会被直接回溯复用（Alg.2 L38–39 `T_R ← D_T[q_R^curr]`），错误因此静默传播到执行阶段。
- **工程动作**：给缓存 key 加环境版本号 / 障碍集合 hash；或在新物体落位后清空 `Tree_eval`（牺牲重规划速度换正确性）。

### 补充：一个「复现陷阱」（非 pitfall，但会让人取错数）

正文 §IV-A1 写 "Table II shows the percentage of scenarios where the object reached the goal…"，但 Table II 的 caption 是 *Full-horizon planning success rate*。按 caption 与数值内容，**成功率表是 Table I**（LAMP-Lazy 100/96/100/88），**全时域规划成功率表是 Table II**（LAMP-Lazy 四图皆 100%）。第三方复现时若照正文文字去 Table II 取成功率会得到完全不同的结论。

---

[← Back to Multi-Robot Manipulation & Planning README](./README.md)
> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（§3 玩具算例的全部数字均为自造示范；§4 中未报告的硬件/显存/真机延迟一律标注「论文未报告」）

<!-- source: https://arxiv.org/abs/2606.29358 -->
