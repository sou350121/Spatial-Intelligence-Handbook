# Unitree H1 vs Figure 02 vs 1X NEO：人形空间感知 stack 对比 (Three Humanoid Doctrines)

> **发布时间**：2026-05-21
> **核心定位**：三家头部人形公司的**空间感知 stack** 不一样，背后是三种不同的产品哲学。本文不评公司，只看 sensor 选型 + spatial representation 决策链。
> **TL;DR**：Unitree 走"传感器堆料"路线（LiDAR + 多 IMU + 多 cam）；Figure 走 "Vision Pro 风 inside-out" 纯视觉 + 多目；1X 走极简 cam-only + 神经网络。三家都在量产规模上推进，分歧不是技术能力差距，是**对人形 use case 的不同押注**。

**状态：** v1 —— 有立场的草稿。所有商用 spec 数字 `UNVERIFIED`，除非来自厂商发布会 / 数据手册。

---

**X-Ray 开场：** 同样是双足人形、同样的高度（170-180 cm 量级）、同样目标"通用劳动平台"，三家公司选了截然不同的传感器堆叠。Unitree H1 / H2 用 3D LiDAR（Livox / 自研）+ 多目 + 多 IMU，Figure 02 用纯多目 RGB（"Vision Pro 风" inside-out tracking），1X NEO 走 cam-only + 神经网络 (NEO Beta 上能看到的)。这不是"谁更先进"的问题——是**对 deployment scenario** 的不同押注：Unitree 押工业 / 学界（要可解释 + 安全）、Figure 押工厂 / 仓储（要泛化 + 数据规模）、1X 押家用（要外观自然 + 成本极低）。对 spatial researcher 意味着：**sensor 选型本质是产品决策**，不是技术决策。

---

## 📍 研究全景时间线

```
2022 ─ Tesla Optimus Day — 人形进入主流视野
        │ ⚡ Tesla 路线：cam-only + 共享 FSD 神经栈
2023 ─ Figure 01 demo（咖啡机演示）— 纯视觉 + RT-X 类 policy
        │
2023 ─ Unitree H1 发布 — Livox MID-360 LiDAR + 多目 + 双 IMU
        │ ⚡ 工业风传感器堆料，价格 ~$90k `UNVERIFIED`
2024 ─ 1X NEO Beta — 软体外壳 + cam-only + 神经栈
        │ ⚡ 极简感官路线，押家用场景
2024 ─ Figure 02 — Vision Pro 风 6 cam inside-out tracking
        │ ⚡ Apple-influenced 多目 + 占用网络方案
2024 ─ Boston Dynamics Atlas（电动版） — 头装 RGB-D + 多目
2025 ─ Unitree H2 — 头装 LiDAR + 全身 IMU 升级
        │
2026 ─ 本文位置：三家路线没收敛，量产规模分别 1k+ / 500+ / 100+ `UNVERIFIED`
        └─ 局限：家用场景没有任何公司真正验证
```

---

## 1 · 核心架构对比

### 1.1 系统对比概览

| 维度 | Unitree H1/H2 | Figure 02 | 1X NEO |
|---|---|---|---|
| 主深度来源 | 头装 / 体装 LiDAR（Livox） | 6 cam inside-out 三角化 | cam stereo + 推理 |
| RGB 摄像头数量 | 2-3 | 6 (Vision Pro 风分布) | 2-4 |
| IMU 数量 | 2-3（头 + 躯干 + 骨盆） | 1-2 + per-limb | 1（最小化） |
| LiDAR | ✓（Livox MID-360） | ✗ | ✗ |
| 雷达 / sonar | ✗ | ✗ | ✗ |
| 触觉 | 指尖力（H2 配灵巧手时） | 指尖（02） | 软外壳全身 |
| 头部姿态稳定 | 主动 gimbal-like 颈控 | 头部惯性补偿 | 极简 |
| 算力（车端） | NVIDIA Jetson + 自研 | Tesla / Apple-like 自研 | Embedded NVIDIA |
| 设计哲学 | 工业可审计 | Apple 风优雅 | 家用极简 |
| 量产单价 | ~$90k+ `UNVERIFIED` | ~$50-80k `UNVERIFIED` | ~$10-30k 目标 `UNVERIFIED` |

### 1.2 关键机制：三种"远凝视 + 近落脚"分工

⚡ **Eureka Moment**：[`whole_body_spatial_perception.md`](./whole_body_spatial_perception.md) 提出过"远凝视 + 近落脚"两份工作的拆分——三家用三种方式回答这个拆分。

```
Unitree:   远凝视 = 头装 cam     ┐
                                  ├── 都靠头装 LiDAR 兜底
           近落脚 = 体装 LiDAR    ┘     (Livox MID-360 360° 覆盖)

Figure:    远凝视 = 头部 6 cam    ┐
                                  ├── 占用网络在 cam 上做端到端
           近落脚 = 同 6 cam      ┘     (类 Tesla 占用网络思路)

1X:        远凝视 = 极少 cam      ┐
                                  ├── 软外壳触觉做近距 bumper
           近落脚 = 软外壳 + cam   ┘     (避免摔倒靠柔顺性)
```

### 1.3 数据流对比

```
Unitree H1/H2:
  Livox LiDAR ──► 点云 (10 Hz) ──┐
  Head cam ────► RGB (30 Hz) ────┼──► fusion ──► occupancy + 步态 plan
  Body IMU x3 ─► 200 Hz ─────────┘                ▲
                                                  └─ 步态控制器 (RL or MPC)

Figure 02:
  6 RGB cam ─► inside-out triangulation ─► 占用网络 ──► neural policy (类 RT-2)
                                                  ▲
                                                  └─ 灵巧手 + 触觉

1X NEO:
  2-4 cam ──► CNN backbone ──► neural policy (含步态)
                ▲
                └─ 软外壳触觉做安全 bumper（不是 perception 主信号）
```

---

## 2 · 数学核心：三种空间表征的本质

📌 **Napkin Formula**：三家的 spatial representation 差在 `(measurement → 3D)` 的转换链长度。

- Unitree：`LiDAR → 直接 3D 点云`（链长 = 1，物理深度）
- Figure：`6 cam → multi-view triangulation → 占用`（链长 = 2，学习 + 几何）
- 1X：`stereo → 单目深度 NN → 占用 (可能隐式)`（链长 = 3，几乎全学习）

链越长，**长尾鲁棒性**越差但**数据可扩展性**越好——这就是为什么 1X 路线必须配数据规模 + 神经网络，Figure 居中（多目几何 + 学习），Unitree 最保守（LiDAR 物理）。

---

## 3 · 带数字走一遍：上楼梯玩具例子

场景：人形上 18 cm 高、25 cm 深的楼梯。

| 公司 | 感知 | 决策 |
|---|---|---|
| Unitree | LiDAR 直接给楼梯几何，深度误差 &lt;2 cm `UNVERIFIED` | MPC 步态控制器优化落脚 |
| Figure | 6 cam 多视图三角化 → 占用网络输出 voxel grid | neural policy 端到端输出步态 |
| 1X | stereo cam + 单目深度 NN | end-to-end policy（可能不显式建楼梯模型） |

**鲁棒性 vs 数据规模**：Unitree 的 LiDAR 路线对未见楼梯样式鲁棒（物理深度不变），但只能学会"穿过已见过的具体楼梯类型"；1X 的 cam-only 路线对长尾敏感（弱光、纹理少），但用百万家庭数据后理论上能 cover 所有家用楼梯。这是 Tesla vs Waymo 之争的人形版本。

---

## 4 · 工程视角：传感器 SWaP-C 对比

| | Unitree | Figure | 1X |
|---|---|---|---|
| 传感器重量 (头+躯干) | ~1.5 kg `UNVERIFIED` | ~0.8 kg | ~0.3 kg |
| 传感器功耗 | ~30 W | ~15 W | ~8 W |
| 传感器 BOM 占比 | 20-30% of $ | 10-20% | &lt;10% |
| 视觉处理延迟 | 30-50 ms（LiDAR fusion） | 50-100 ms（多目） | 30-80 ms |
| 失效模式 | LiDAR 失灵 → 严重 | cam 失灵 → 严重 | cam 失灵 → 软外壳兜底 |
| 部署门槛 | 工业接受 | 工厂 / 仓储接受 | 家用接受（外观自然） |

**1X 的隐藏优势**：软外壳不只是安全，是**减小对感知精度的要求**——撞到墙没事，对手没事，倒了也没事。这把"人形必须高精度感知"这个隐含假设解构掉了。

---

## 5 · 数据与评测

- 三家都**不公开**详细数据集
- 公开演示：Figure 02 (折衣服 / 工厂作业)、Unitree H1 (跳跃 / 后空翻)、1X NEO (家务 demo)
- 学界主要参考：**ALOHA** + **HumanPlus** + **OmniH2O**（unified policy）

仿真饱和警告：IsaacLab / MuJoCo 上的人形仿真 sim-to-real gap 比四足大一个数量级——四足摔倒可恢复，人形摔倒可能损坏。

---

## 6 · 能力与失败模式

**Unitree 失败**：LiDAR 户外阳光下 SNR 下降、人形跌倒时 LiDAR 损坏成本高。
**Figure 失败**：多目对极弱光敏感、6 cam 标定漂移导致占用网络静默退化。
**1X 失败**：泛化范围窄、长尾事件无 LiDAR 兜底、cam 被遮挡（小孩、宠物）即失能。

### Hidden Assumptions

1. **Unitree 假设：LiDAR 在人形 form factor 上不会成为瓶颈**——但 LiDAR 旋转件 / 头部加重对动平衡有副作用。
2. **Figure 假设：多目占用网络足以替代 LiDAR**——在 outdoor / 极端光照下未公开验证。
3. **1X 假设：家用场景容差大 + 软外壳 = 不需要高精度感知**——但小孩 / 宠物 / 楼梯下行等关键 case 仍然需要可靠 perception。
4. **三家共同假设：步态控制器 + spatial perception 可分层**——但跳跃 / 后空翻这类高动态动作要求两者紧耦合，分层架构在那里失效。
5. **三家共同假设：头部 / 躯干 IMU 数 = 设计选择**——但实际多 IMU 之间标定 / 时间同步是工业级人形的核心难题，远超学术讨论。

---

## 7 · 与相关工作对比

| 厂商 | 路线 | 关键差异 |
|---|---|---|
| Tesla Optimus | cam-only + 共享 FSD 神经栈 | "汽车的副产品" 路线 |
| Boston Dynamics Atlas | 头装 RGB-D + 多目 + 强力液压（旧）/电动（新） | 工程实力 + 高动态，但产品化弱 |
| Unitree H1/H2 | LiDAR + 多目 + 多 IMU | 工业 / 学界路线，性价比 |
| Figure 02 | 6 cam inside-out + 占用 | Apple/OpenAI 风优雅 |
| 1X NEO | cam-only + 软外壳 | 家用极简 |
| Sanctuary AI Phoenix | 头装 stereo + 多目 + 灵巧手 | 加拿大学派，偏 manipulation |
| Apptronik Apollo | RGB-D + 多目 | NASA 背景，工业仓储 |

**面试 Tip**：被问"哪家人形 stack 更先进"——别站队，答"三家分歧不是技术差距，是产品押注差距：Unitree 押工业可审计，Figure 押工厂神经栈 + 数据规模，1X 押家用容差 + 软外壳；问对哪种 use case 才有'更先进'的答案"。

---

## Boundary

- **远凝视 vs 近落脚的拆分** → [`whole_body_spatial_perception.md`](./whole_body_spatial_perception.md)
- **跨 embodiment sensor stack 矩阵** → `crossing/sensor-stack-matrix/`
- **占用网络** → [`embodiments/driving/waymo_vs_tesla_doctrinal_split.md`](../driving/waymo_vs_tesla_doctrinal_split.md)
- **VLA policy 端**（HumanPlus / OmniH2O）→ VLA-Handbook `theory/`

## For the reader

- **Humanoid engineer**：选 stack 前先回答"产品 niche 是工业 / 工厂 / 家用？"——答案直接决定 LiDAR vs 多目 vs cam-only。
- **AD engineer**：Figure 路线本质是"Tesla 占用网络放到人形上"——可借鉴占用网络的自动标注 pipeline。
- **Manipulation researcher**：三家头部都有灵巧手计划，但**头装 perception → 手部 manipulation** 的 token 化接缝没人公开做对。
- **Aerial engineer**：drone 早就走过 "LiDAR vs cam-only" 之争（drone 答案：cam 在小 SWaP 下赢），人形可能也会收敛到 cam-only，但要 10-15 年。

## References

- Unitree H1 / H2 — 官方发布会、[unitree.com](https://www.unitree.com/) `UNVERIFIED`
- Figure 02 — Figure AI demo videos
- 1X NEO Beta — 1X Technologies announcement
- HumanPlus — Fu 等 2024，[arXiv 2406.10454](https://arxiv.org/abs/2406.10454)
- OmniH2O — He 等 2024，[arXiv 2406.08858](https://arxiv.org/abs/2406.08858)
- Atlas（电动版）— Boston Dynamics 2024 公告

---
[← Back to Humanoid-Legged README](./overview.md)
