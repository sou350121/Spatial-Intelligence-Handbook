<!-- ontology-5axis
problem: Multi-object 2D tracking (MOT)
representation: BBox + ID + Kalman state
sensor: Detection input (RGB)
paradigm: Data association (Hungarian / IoU) + Kalman
time: Streaming
ref: ../../cheat-sheet/ontology.md §7
-->

# SORT & ByteTrack — 2D 多目标追踪两座里程碑 (SORT & ByteTrack Dissection)

> **发布时间**: 2016 (SORT) / 2022 (ByteTrack); dissection 写于 2026-05-21
> **论文 / 模型**: SORT (arXiv 1602.00763, Bewley et al., ICIP 2016) · ByteTrack (arXiv 2110.06864, Zhang et al., ECCV 2022)
> **核心定位**: 把 "tracking-by-detection" 做到极简（SORT）→ 再用 low-confidence detection 推到 MOT17 80.3 MOTA（ByteTrack）。**2026 仍是 2D MOT 默认 baseline**。

**Status:** v1 — 带立场的初稿。数字除非在 rig 上测过否则标 `UNVERIFIED`。
**Wedge tier:** W1 · 2D MOT 工业部署默认；几乎所有 production 行人 / 车流 tracker 都从这两个起步。
**TL;DR:** SORT (2016) = Kalman + 匈牙利 + IoU，700+ 行 Python，零深度特征 → 居然胜过当时复杂 baseline，开启 "tracking-by-detection" 范式。ByteTrack (2022) 只改一件事：**low-confidence detection 也参与第二轮匹配** → MOT17 80.3 MOTA, 30 FPS, 完爆当时所有 SOTA。**2026 工业级行人 tracker 还在用 ByteTrack 是个常态**。

**X-Ray.** 2014 年之前 MOT 圈用复杂的 multi-hypothesis tracking (MHT) / joint probabilistic data association (JPDAF) —— SORT 一篇 4 页 ICIP paper 说："给我好 detector，剩下用 1960 年的 Kalman + 1955 年的匈牙利就够。" 整个领域被这个极简主义教训打了 8 年。ByteTrack 进一步证明：**问题不在算法复杂度，问题在我们扔掉了 low-confidence detection**。这是 2010s 工程主义的高光时刻。

---

## 📍 研究全景时间线

```
1955  1960     2014    2016 (SORT)  2017     2022 (ByteTrack)  2023      2024+
匈牙利 Kalman ─► MHT ─► SORT ─────► DeepSORT ► ByteTrack ────► OC-SORT ► SAMBA-MOTR
└── 数学基础 ──┘  └复杂─┘   └ 极简  └+appearance └+low-conf    └+OOS │
                                                              非线性运动 attention/transformer
                                                                    
本文聚焦 ──────────────► SORT ────────────────► ByteTrack ────►
```

SORT 是范式转折点（手工 → 学到 detector 驱动）；ByteTrack 是工程极限点（在不加 NN 模块的前提下推到 80+ MOTA）。**之后的工作（OC-SORT、SAMBA-MOTR、MOTRv3）本质都在解 ByteTrack 没解的问题（非线性运动 / 长时遮挡 / 关联 transformer）**。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统组件对比

| Module | SORT (2016) | ByteTrack (2022) |
|---|---|---|
| Detector | 任意 (论文用 Faster R-CNN) | YOLOX-X (论文配套) |
| Motion model | Kalman (constant velocity, 7-d state) | 同 SORT |
| Appearance | ❌ 无 | ❌ 无（关键！）|
| Association cost | 1 − IoU (Hungarian) | 同，但**两轮** |
| 第一轮关联 | high-conf detections vs all tracks | high-conf detections vs all tracks |
| **第二轮关联** | ❌ 不存在 | **low-conf detections vs unmatched tracks** |
| Track 生命周期 | hit≥3 birth, miss≥1 死 | hit≥3 birth, miss≥30 死 (lost buffer) |
| 公开代码 | 700 行 Python | ~1k 行 PyTorch |

### 1.2 ⚡ Eureka Moment

> **SORT**: "好的 detector + Kalman + Hungarian = 比 fancy tracker 好。不要再叠模块。"
>
> **ByteTrack**: "**low-confidence detection 也是有信号的** —— 把它们和*已有 track* 关联（而不是建新 track），就能在遮挡 / motion blur 下保住轨迹。"

ByteTrack 反直觉之处：之前所有 tracker 扔掉 score &lt; 0.5 的检测（怕假阳）。ByteTrack 说"先用 high-conf 起轨，再用 low-conf 续轨" —— **同样的 detector，没改一行 NN 代码，MOTA +10**。

### 1.3 信息流

```
   SORT (单轮 association):
   ──────────────────────────────────────────
   Frame ─► Detector ─► boxes (score > 0.5)
                            │
                            ▼
   tracks ─► Kalman predict ─► predicted boxes
                            │
                            ▼
                  Hungarian (cost = 1 - IoU)
                            │
                ┌───────────┴────────────┐
                ▼                        ▼
            matched              unmatched
              │                    │
              ▼                    ▼
       Kalman update         birth new tracks
                              (after 3 hits)

   ByteTrack (双轮 association):
   ──────────────────────────────────────────
   boxes ─split─► D_high (score > 0.6)  ──► 第一轮: vs all tracks
                                                │
                                                ▼
                                          unmatched tracks
                                                │
          D_low (0.1 < score ≤ 0.6)  ──► 第二轮: vs unmatched tracks
                                                │
                                                ▼
                                          仍未匹配 → lost buffer (30 frames)
```

---

## 2 · 数学核心

### 📌 Napkin Formula

```
  ByteTrack: matches = match(D_high, T)  ⊕  match(D_low, T \ matched₁)
                       └─第一轮─┘            └────第二轮────┘
```

**一行真理**: 在 SORT 上只加*第二轮匈牙利匹配* —— 就这。没有新 loss，没有 attention，没有 ReID network。

### 2.1 SORT Kalman 状态

```
   状态 x = [u, v, s, r, u̇, v̇, ṡ]ᵀ ∈ R⁷
   
   u, v : box 中心
   s    : box 面积
   r    : box 长宽比 (常量)
   u̇,v̇,ṡ : 速度
   
   Transition: F = 7×7 (constant-velocity, dt=1)
   Observation: H = 4×7 (观测 u, v, s, r)
```

关键设计：**aspect ratio r 不参与运动**（人 / 车的形状不会快速变） —— 这个简化让 Kalman 维度可控。

### 2.2 Hungarian 关联

```
   cost(track_i, detect_j) = 1 − IoU(predicted_box_i, detect_j)
   
   if cost > threshold (默认 0.7):
       视为不可匹配
   
   Hungarian solve: O(n³), n ≈ 50 → < 1ms
```

| Symbol | Meaning |
|---|---|
| `D_high` | score > τ_high (ByteTrack 默认 0.6) |
| `D_low` | τ_low < score ≤ τ_high (默认 0.1 ~ 0.6) |
| `T` | active + lost tracks |
| `IoU` | bbox 交并比 |

### 2.3 为什么 low-conf detection 有信号？

- **遮挡**: 行人被路灯杆挡 30%，detector score 从 0.9 跌到 0.4 → SORT 扔掉 → 轨断
- **Motion blur**: 快速移动 → score 下降 → 同上
- **Truncation**: 出画一半 → score 下降

**关键洞见**: 这些 box **位置仍然准确**（IoU 高），只是 detector 的"我有多确信这是个人"分数低。ByteTrack 说：位置准 + 在已有 track 附近 = 信它。

---

## 3 · Worked example: 行人被电线杆挡 3 帧

5 帧场景，1 个行人，detector 每帧输出：

| Frame | Detection score | SORT 行为 | ByteTrack 行为 |
|---|---|---|---|
| 1 | 0.92 | 第一轮匹配 ✅ → track 续 | 同 |
| 2 | 0.85 | 第一轮 ✅ | 同 |
| 3 | **0.35** (挡住) | 扔掉 → track miss | **第二轮**匹配 ✅ → 续 |
| 4 | **0.40** | 扔掉 → miss=2 | **第二轮** ✅ → 续 |
| 5 | 0.88 | 第一轮匹配，但**新 ID**（旧轨已断）→ IDsw +1 | 第一轮匹配旧 ID ✅ |

**结果**:
- SORT: 1 个 ID switch
- ByteTrack: 0 个 ID switch, 同 detector

整段视频 5000 帧 → SORT 累计 ~100 IDsw, ByteTrack ~10 IDsw `UNVERIFIED` 量级估计。

---

## 4 · 工程视角

### 4.1 速度 / 部署

| Tracker | FPS (V100, 不含 detector) | 内存 | 实现复杂度 |
|---|---|---|---|
| SORT | ~700+ Hz | &lt;50 MB | ~700 行 Python |
| DeepSORT | ~40 Hz (ReID CNN 瓶颈) | ~500 MB | ~2k 行 |
| **ByteTrack** | ~30 Hz (含 YOLOX-X detector) | ~2 GB | ~1k 行 |
| OC-SORT | ~700+ FPS (CPU) | &lt;50 MB | ~1.5k 行 |

**部署观察**: tracker 自己几乎不占资源，**detector 才是瓶颈**。Jetson Orin 上 YOLOX-S + ByteTrack ~30 FPS `UNVERIFIED` 可达。

### 4.2 关键超参（实战要点）

| 超参 | SORT 默认 | ByteTrack 默认 | 调它的场景 |
|---|---|---|---|
| `iou_threshold` (匹配) | 0.3 | 0.3 (第一轮) / 0.5 (第二轮) | 高速场景调低 |
| `track_buffer` | 1 (hit=3 出生) | 30 帧 (lost 后保留) | 长遮挡场景调高 |
| `track_thresh` (high) | - | 0.6 | detector 不同需调 |
| `det_thresh` (low) | - | 0.1 | 过低引入误关联 |

**陷阱**: ByteTrack 论文用 YOLOX detector，换成其他 detector（YOLOv8 / DETR）**所有阈值要重调** —— 不同 detector 的 score 分布不同。

### 4.3 Production deployment（学界 baseline vs 工业用）

- **学界 baseline**: 论文配 YOLOX → 复现 MOT17 80.3 MOTA
- **工业典型 stack**: YOLOv8 / RT-DETR / Co-DETR + ByteTrack → 实际部署做行人 / 车流计数
- **边缘部署**: YOLOX-S/Nano + ByteTrack on Jetson Orin Nano 8GB ~15-30 FPS `UNVERIFIED`
- **Open source**: ultralytics / supervision / mmtracking 内置 ByteTrack

---

## 5 · 数据与评测

| Dataset | MOT17 (test) | MOT20 (拥挤) | DanceTrack (非线性) | BDD100K |
|---|---|---|---|---|
| **SORT** (orig 2016) | ~33.4 MOTA | 慢 / 失败 | ~47 MOTA | - |
| **DeepSORT** | ~61.4 MOTA | - | - | - |
| **ByteTrack** (orig 2022) | **80.3 MOTA, 77.3 IDF1** | 77.8 MOTA | 47.7 MOTA | - |
| **OC-SORT** (2023) | 78.0 MOTA | 75.9 MOTA | **55.1 MOTA** | - |
| 2025 SOTA two-stage (`UNVERIFIED`) | ~80.5 MOTA, 64.2 HOTA | - | - | - |

来源: ByteTrack arXiv 2110.06864 (Zhang et al. ECCV 2022); OC-SORT arXiv 2203.14360 (Cao et al. CVPR 2023); 最新 2025 来自 Nature SR (`UNVERIFIED`).

**关键观察**:
1. ByteTrack 在 MOT17 / 20 强 → 但 DanceTrack 弱（非线性运动）→ OC-SORT 主修这件事
2. 2026 在 MOT17 上 SOTA 数字只比 ByteTrack 高 ~0.2 MOTA → **benchmark 饱和**，新论文意义有限
3. 真正未解决: 跨域泛化、长时遮挡 ID 重链接

---

## 6 · 能力与失败模式

**赢**: 密集行人场景、车流、监控、体育（足球篮球场上跑动）、零 ReID 训练成本。

**败于**:
- **非线性运动** (舞蹈、急停车、动物) → Kalman CV 假设破裂 → OC-SORT 接班
- **长时遮挡 >30 帧** → lost buffer 过期 → ID 断；需 appearance-aware (DeepSORT, BoT-SORT)
- **外观高度相似** (同制服球员、同型号车) → 当两人交叉时 IoU 模糊 → ID switch
- **极拥挤** (人群 >100) → Hungarian cost matrix 退化，box overlap 高 → 关联歧义
- **跨域** (city → factory) → detector 先崩 → tracker 救不了

### 6.1 Hidden Assumptions

- **Detector 的 box 是准确的**（位置准），只是 score 不可靠 → ByteTrack 全部 leverage 这个。若 detector box 也歪（如 motion blur 导致 box 飘 30px），假设破裂。
- **Constant velocity 在 1 帧内成立** → 高速 / 急转 / 跳跃运动破坏（Kalman 预测 → IoU &lt; 0.3 → 关联失败）
- **物体之间 IoU 不大重叠** → 极拥挤场景 IoU > 0.7 大量出现，关联歧义
- **Aspect ratio 稳定** → 行人侧身 / 趴下变形大，r 不再常量
- **Frame rate 高 (>=25 Hz)** → 低帧率 (5 Hz security cam) 单帧位移大，IoU 不再可靠
- **同一相机 / 单视图** → 多相机 / 跨视图 reid 是另一个问题（不在 SORT/ByteTrack 范围）

这些是 **MOT17 benchmark 上 ByteTrack 上 80 而真实部署常常掉到 60** 的根因。

### 6.2 GitHub-validated 失败模式（atlas 联动，2026-05）

- **GitHub-validated**：SORT / ByteTrack 这类 detector-based MOT **不在 atlas 5 仓直接覆盖范围**（atlas 选了 FoundationPose / MegaPose / RAFT / CoTracker / SAM 2 五条 foundation 模型阵营，MOT 上游靠 YOLO/DETR detector，下游靠 association 启发式，结构上不与 foundation lane 同质）；本 dissection 在 [`github_failure_atlas.md`](./github_failure_atlas.md) 中作为 zone 整体 "Cross-cutting" 部分被讨论 — atlas 总结的 **遮挡 / 反射 / OOD = production blocker，5 仓共有**、**没有任何一仓输出 per-pixel / per-track confidence** 两条与 ByteTrack 的 ID switch / detector 域外失效完全同构，未有专属失败块；详见 atlas 整体节奏部分。
- **GitHub-validated（间接）**：与 atlas 提到的 SAM 2 多 object mask 丢 / 中途新 ID 加入难（[SAM2 #249/#185](https://github.com/facebookresearch/sam2/issues/249)）正面冲突 SORT/ByteTrack 的设计假设 — **VFM-based video tracking 正在挤压 detector-based MOT 的护城河**，但 SAM 2 issue 区也证明 VFM 路线尚未解决多对象 ID hot-swap，这是 ByteTrack 至今仍稳坐 MOT17 leaderboard 的工程理由。

---

## 7 · 与相关工作对比

| Tracker | Year | Appearance? | 关联策略 | MOT17 MOTA | DanceTrack | 一行总结 |
|---|---|---|---|---|---|---|
| SORT | 2016 | ❌ | 单轮 IoU + Hungarian | ~33 | ~47 | 极简鼻祖 |
| **DeepSORT** | 2017 | ✅ (CNN ReID) | IoU + appearance cascade | ~61 | - | SORT + ReID embedding |
| FairMOT | 2020 | ✅ (jointly) | joint detect + reid | 73.7 | - | 检测追踪联合训练 |
| **ByteTrack** | 2022 | ❌ | **双轮 IoU**（high + low conf） | **80.3** | 47.7 | low-conf 也用 |
| **OC-SORT** | 2023 | ❌ | observation-centric, virtual traj | 78 | **55.1** | 非线性运动 + 长时遮挡 |
| BoT-SORT | 2022 | ✅ | ByteTrack + camera motion + ReID | ~80.5 | - | ByteTrack 加料 |
| MOTRv3 | 2023 | ✅ (implicit) | Transformer query | ~75 (offline 高) | - | end-to-end query |
| SAMBA-MOTR | 2024 | learned | sequence model attention | -  | - | attention 不靠 IoU |

> **🎤 Interview Tip.** "你会用什么 tracker？" — *"行人 / 车流 → ByteTrack（80+ MOTA, 没 ReID 也够）；舞蹈 / 动物 / 急停车 → OC-SORT；长时遮挡 + appearance 关键 → BoT-SORT。我永远不从头训 tracker —— 把预算花在 detector 上回报更高。"* 这条回答能直接秒杀"我会训 FairMOT"的候选人。

---

## 8 · 跨 Embodiment 用法

| Embodiment | 用法 | 关键调整 |
|---|---|---|
| **AGV / 室内机器人** | YOLOv8 + ByteTrack 跟踪行人，避撞 | 帧率 10-15 Hz → 调高 IoU threshold |
| **Drone follow-me** | YOLO + ByteTrack on gimbal feed → target lock | 相机自身运动 → 用 BoT-SORT (camera motion compensation) |
| **AD (Autonomous Driving)** | **不直接用**：AD 用 3D MOT (CenterPoint-track) | ByteTrack 是 2D；AD 需 BEV |
| **零售 / 监控** | RT-DETR + ByteTrack → 客流计数 | 大量 false re-id（同店员多次进出）— 需业务 logic 补 |
| **体育分析** | YOLOX + ByteTrack + 球员号码 OCR | 球员高速交叉 → OC-SORT 或 ByteTrack + appearance 更好 |

详细 → [`../../embodiments/aerial/active-tracking/`](../../embodiments/aerial/active-tracking/), [`../../embodiments/driving/`](../../embodiments/driving/).

---

## 9 · Falsifiable 2-year Prediction

**Claim**: 2027 年 6 月前，**ByteTrack 仍是工业部署占比最高的 2D MOT 算法**（>50% 行人 / 车流 production stack），尽管学术 SOTA 已被 Transformer-based tracker 超越。

**Why**: ByteTrack 1k 行 Python、零额外 NN 模块、CPU 700 FPS、可解释 —— Transformer tracker 训练成本 + 部署复杂度太高，学术 SOTA 在工业不一定胜出。

**反驳条件**: 若 2027 年某次 SAMBA-MOTR / MOTRv3 后继达成 ① open weights, ② &lt;500 MB inference, ③ Jetson Orin >25 FPS，则可能取代 ByteTrack 在产线。

---

## 10 · GitHub Deep Dive (2026-05, abewley/sort + ifzhang/ByteTrack 仓 issue 区交叉考古)

> **来源**：[abewley/sort/issues](https://github.com/abewley/sort/issues)（3.8k★，按 comment 数排序前 25）+ [ifzhang/ByteTrack/issues](https://github.com/ifzhang/ByteTrack/issues)（5.0k★，按 comment 数前 25）。本节聚焦 detector 依赖 / ID switch / CPU 实时 / OC-SORT 替代讨论 / 3D 扩展请求 5 大读者真痛点。

### 10.1 Pitfall 总表（按真实痛点 × 仓库交叉打分）

| Pitfall 类别 | 高 ROI 实务含义（读者层面） | SORT 验证 issue | ByteTrack 验证 issue |
|---|---|---|---|
| **Detector 换型 / 参数全要重调** | 论文阈值是 YOLOX 上调过的；换 YOLOv5/v8/v11/RT-DETR 全套阈值重做 | [#73](https://github.com/abewley/sort/issues/73) 6c open detector→tracker 接口（"map the bounding boxes which this method output to the earlier ones"）· [#9](https://github.com/abewley/sort/issues/9) 11c closed SSD+SORT | **[#99](https://github.com/ifzhang/ByteTrack/issues/99) 41c closed** "run ByteTrack with yolov5 instead of yolox" · **[#5](https://github.com/ifzhang/ByteTrack/issues/5) 21c closed** "Use my own detection model" · [#445](https://github.com/ifzhang/ByteTrack/issues/445) YOLOv11 集成 · [#448](https://github.com/ifzhang/ByteTrack/issues/448) "False positives from YOLOX hurting tracking" · [#461](https://github.com/ifzhang/ByteTrack/issues/461) YOLOX CrowdHuman 准确率 |
| **ID 计数器单调递增 / 不可重置** | tracker 重新实例化仍然延续旧 ID（全局静态）→ 多视频 batch / 多 session 部署直接错 | **[#106](https://github.com/abewley/sort/issues/106) 14c open** "Why the tracker ID keeps increase even I recreate the tracker object"（"recreate the tracker object ... However, the tracker IDs are different each time. For example, the tracker IDs start from 1&2 for the first iteration, then they start from 11&12 for the second"）· [#109](https://github.com/abewley/sort/issues/109) 4c "ID keeps increesing for the same objects" · [#134](https://github.com/abewley/sort/issues/134) 10c closed "Tracker skips a few identities" | **[#210](https://github.com/ifzhang/ByteTrack/issues/210) 18c open** "AttributeError: 'STrack' object has no attribute '_count'"（同根因：全局 `_count` 类属性被生命周期破坏） |
| **遮挡下 ID switch / ID 互换** | 两人/两车相互遮挡分离后 ID 交换 — Kalman 单独是救不了的 | [#137](https://github.com/abewley/sort/issues/137) 8c open "Tracking id change with a gap" · [#157](https://github.com/abewley/sort/issues/157) 6c open（已知 N 个动物，MaskRCNN 错检 + SORT 只跟 4-5 → 需 reid 恢复） | **[#226](https://github.com/ifzhang/ByteTrack/issues/226) 10c open** "id exchange when two objects coincide"（"id 2 moves to cover id 1, when they separate the moving became id 1 and the static became id 2"） |
| **长间隔 / 低 FPS 场景** | 低帧率 (5 Hz security cam, 远监控) IoU 失效；ByteTrack 也救不了 | [#22](https://github.com/abewley/sort/issues/22) 7c closed "Tracking with frame skips" | **[#424](https://github.com/ifzhang/ByteTrack/issues/424) 6c open "帧间隔时间很长的跟踪"**（"如果帧之间的间隔很长 ... 比如1s 2s的，我这边测试的结果是不行"，Kalman + 阈值全调过仍无效） |
| **CPU 实时 / 边缘部署** | 论文配 YOLOX 走 GPU；CPU-only 报错 / 速度断崖 | [#178](https://github.com/abewley/sort/issues/178) "Converting into Grayscale increasing inference time" | **[#55](https://github.com/ifzhang/ByteTrack/issues/55) 8c open** "Error when running demo_track.py - does not work on CPU"（VM Ubuntu 无 GPU → 直接报错） |
| **Deepstream / Jetson 内存泄漏** | 8 摄像头 35 min 内 OOM；NVIDIA 默认 tracker 不漏 | — | **[#276](https://github.com/ifzhang/ByteTrack/issues/276) 11c closed** "ByteTrack Deployment on Deepstream 6.0+ Major Memory Leak"（"uses the entire device memory within 35 minutes ... if i switch back to nvidia's default trackers no leak occurs"）— 引用 #253/#252/#249 多个未完整解决的 PR |
| **小目标 / appearance 相似 / ReID 集成** | 行人都穿同制服、远景小目标 → 双轮 IoU 也救不了，需 BoT-SORT 的 ReID | [#157](https://github.com/abewley/sort/issues/157) 同制服动物 · [#128](https://github.com/abewley/sort/issues/128) "False positives and misses" | **[#460](https://github.com/ifzhang/ByteTrack/issues/460)** "Tracking loss for small targets with YOLOv8 + ByteTrack" · [#45](https://github.com/ifzhang/ByteTrack/issues/45) 10c "Objects on my dataset are quite small" · [#103](https://github.com/ifzhang/ByteTrack/issues/103) 7c "How can we integrate the re-id module for deep features" |
| **依赖 / 版本腐化** | numpy / lap / PIL / torch / numpy.float 都炸过 | [#187](https://github.com/abewley/sort/issues/187) `pip install -r requirements.txt` · [#181](https://github.com/abewley/sort/issues/181) PIL ImageTk · [#173](https://github.com/abewley/sort/issues/173) lap→lapx · [#177](https://github.com/abewley/sort/issues/177) Python 版本 | [#379](https://github.com/ifzhang/ByteTrack/issues/379) "module 'numpy' has no attribute 'float'" · [#386](https://github.com/ifzhang/ByteTrack/issues/386) np.float · [#454](https://github.com/ifzhang/ByteTrack/issues/454) Missing torch module |
| **关联结果 ↔ 输入 detection 的映射缺失** | tracker 输出 ID 顺序乱 → 应用层做 label/score join 困难 | [#73](https://github.com/abewley/sort/issues/73) 6c open（核心 API 缺陷）· [#145](https://github.com/abewley/sort/issues/145) 4c closed "Fix so results are returned in same order as input" | [#447](https://github.com/ifzhang/ByteTrack/issues/447) "Models usage question" |
| **3D 扩展 / BEV / 多视图** | SORT/ByteTrack 都是 2D；自动驾驶必须切 CenterPoint-track 等 3D MOT | — | — （**两仓 issue 区都几乎没有 3D 扩展讨论 — 印证 §8 "AD 不直接用" 的判断；社区已默认 2D 边界**） |
| **OC-SORT / BoT-SORT / DeepSORT 替代讨论** | "我该不该换" 是社区主流问题 — 但官方两仓基本不正面回 | [#9](https://github.com/abewley/sort/issues/9) 11c closed "new improvement about sort" — 作者引导用户自己实验 | [#103](https://github.com/ifzhang/ByteTrack/issues/103) ReID 集成 · [#284](https://github.com/ifzhang/ByteTrack/issues/284) "Is only the detector to be trained in ByteTrack"（暴露用户对范式的误解）· [#75](https://github.com/ifzhang/ByteTrack/issues/75) Backbone Change |
| **训练复现（YOLOX 不复现）** | 论文 80.3 MOTA 重训不出 | — | [#89](https://github.com/ifzhang/ByteTrack/issues/89) 7c closed "result of completing the 80 epoch is very poor and cannot be duplicated" · [#134](https://github.com/ifzhang/ByteTrack/issues/134) 17c open "Stuck at init prefetcher" |

### 10.2 仓库健康度

| 维度 | abewley/sort | ifzhang/ByteTrack |
|---|---|---|
| Star | 3.8k | 5.0k |
| Open issue / Total | 大量 open (#187 起到 #100 几乎全 open) | 400+ open（涨到 #461+） |
| 维护者响应 | **基本停滞** — 2016 论文级原始仓，作者主要在 closed PR 留 commit 但 issue 几乎不回 | **稀疏** — 中文 issue 比例高；多个内存泄漏 / `_count` 类 bug 跨多个 PR 未完整修 |
| 新版本节奏 | 几乎冻结（仍是 700 行 Python 原始） | 2022 论文后无大版本；社区 fork (ultralytics / supervision / mmtracking) 接管维护 |
| 文档质量 | 论文 4 页 + README 简单 — `lap` / `lapx` / Kalman 维度需要读源码 | YOLOX 配套强，换 detector / CPU / Deepstream 三条线全靠 issue 自治 |
| **致命缺口** | `id` 计数器全局单调，无 reset API（4 年多 open #106 14c 没 patch）；输入输出顺序错乱（#73）；ReID 完全无（设计上故意） | Deepstream 内存泄漏（#276 11c 跨 4 个 PR 仍未根治）；`STrack._count` 类属性破生命周期（#210 18c）；CPU 报错（#55 4 年 open）；详细 YOLOv8/v11/RT-DETR 阈值重调指南缺 |

### 10.3 讀者實務含義（高 ROI 行动清单）

1. **ID 计数器要自己包一层**：SORT [#106](https://github.com/abewley/sort/issues/106) 14c / ByteTrack [#210](https://github.com/ifzhang/ByteTrack/issues/210) 18c 同根因 — 类级 `_count` 不随对象重建复位；多 session / 多视频 batch 部署务必在 import 后手动 reset 类属性，或自己 fork 把 `_count` 改实例属性。
2. **CPU 部署直接选 fork，不要原仓**：[#55](https://github.com/ifzhang/ByteTrack/issues/55) 4 年 open；要 CPU → 用 `supervision` / `mmtracking` 的实现，原 demo 跑不起来。
3. **Jetson + Deepstream = 自己做内存监控**：[#276](https://github.com/ifzhang/ByteTrack/issues/276) 35 min OOM；上线前必做 1 小时×8 路压测，比对 NVIDIA NvDsTracker 基线（或直接用 NvDs 的 ByteTrack 插件 + 自己加 metric）。
4. **换 detector 一定要重新扫阈值**：[#99](https://github.com/ifzhang/ByteTrack/issues/99) 41c / [#5](https://github.com/ifzhang/ByteTrack/issues/5) 21c 都印证 — track_thresh (0.6) 和 det_thresh (0.1) 是按 YOLOX score 分布调的；切 YOLOv8/YOLOv11/RT-DETR 各跑一遍 grid search（5×5 IoU×conf）。
5. **小目标 / 同制服场景升级到 BoT-SORT**：ByteTrack [#460](https://github.com/ifzhang/ByteTrack/issues/460) / [#45](https://github.com/ifzhang/ByteTrack/issues/45) 10c / SORT [#157](https://github.com/abewley/sort/issues/157) 都打到同一痛点；ReID 不是可选 — 当外观可区分时直接加 ReID 收益最高。
6. **低帧率场景（<10 Hz）双轮 IoU 失效**：ByteTrack [#424](https://github.com/ifzhang/ByteTrack/issues/424) 已实测 1-2 s 间隔不行；security cam / 远程监控直接选 OC-SORT（observation-centric 对 motion drift 友好）或外加 reid 重链接。
7. **3D MOT 不要在这两仓找答案**：issue 区几乎没人问 — 社区已默认 SORT/ByteTrack = 2D 边界；3D 走 CenterPoint-track / SimpleTrack / Poly-MOT 另开 dissection。
8. **API 缺陷预案**：SORT [#73](https://github.com/abewley/sort/issues/73) 输出顺序不保证 = 自己用空间索引做 detection→track 反查；不要靠"行号对齐"。
9. **遮挡 ID 互换是设计极限**：[#226](https://github.com/ifzhang/ByteTrack/issues/226) — 静态 + 动态物体重叠分离后 ID 交换是 IoU+Kalman 范式硬伤；要 BoT-SORT/DeepSORT 的 appearance embedding 才能区分（这正是 OC-SORT 主修方向之一）。
10. **依赖锁版本**：numpy < 1.20 / lap → lapx / Python 3.10+ — 两仓 issue 区一致提醒，建议在 Docker 里钉死。

---

## References

- SORT — Bewley et al. *ICIP 2016*. https://arxiv.org/abs/1602.00763 · code https://github.com/abewley/sort
- DeepSORT — Wojke et al. *ICIP 2017*. https://arxiv.org/abs/1703.07402
- ByteTrack — Zhang et al. *ECCV 2022*. https://arxiv.org/abs/2110.06864 · code https://github.com/ifzhang/ByteTrack
- OC-SORT — Cao et al. *CVPR 2023*. https://arxiv.org/abs/2203.14360 · code https://github.com/noahcao/OC_SORT
- BoT-SORT — Aharon et al. (2022). https://arxiv.org/abs/2206.14651
- FairMOT — Zhang et al. *IJCV 2021*. https://arxiv.org/abs/2004.01888
- MOTRv3 — Yu et al. (2023). https://arxiv.org/abs/2305.14298
- MOTChallenge — https://motchallenge.net/
- DanceTrack — Sun et al. *CVPR 2022*. https://arxiv.org/abs/2111.14690
- HOTA — Luiten et al. *IJCV 2020*. https://arxiv.org/abs/2009.07736

## Boundary

- **Tracking 全景与其他家族** → [`tracking_taxonomy_primer.md`](./tracking_taxonomy_primer.md)
- **像素级流 / 长时点追踪** → [`raft_optical_flow.md`](./raft_optical_flow.md), [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md)
- **6D 物体姿态** → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md)
- **Kalman 完整推导** → [`../spatial-math/bayesian_filtering_ekf_msckf.md`](../spatial-math/bayesian_filtering_ekf_msckf.md)
- **3D MOT (AD 端)** → [`../../embodiments/driving/`](../../embodiments/driving/)
- **Active tracking (drone follow-me)** → [`../../embodiments/aerial/active-tracking/`](../../embodiments/aerial/active-tracking/)

---

[← Back to Pose & Tracking](./overview.md)
