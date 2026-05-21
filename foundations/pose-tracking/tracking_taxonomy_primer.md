# Tracking 全景与分类导览 (Tracking Taxonomy Primer)

> **发布时间**: 2026-05-21
> **核心定位**: "Tracking" 在机器人 / CV 领域是 7 个不同问题的统称，本文给读者一张分类地图 —— 在跳进任何 dissection 前先看一眼。
> **类型**: primer（非 dissection；不必满 14 项门槛，重直觉）

**Status:** v1 — beginner-friendly。读完它再去看 [`foundation_pose_dissection.md`](./foundation_pose_dissection.md) / [`sort_bytetrack_mot_dissection.md`](./sort_bytetrack_mot_dissection.md) / [`raft_optical_flow.md`](./raft_optical_flow.md) / [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md) 才知道每篇在地图哪里。
**TL;DR:** "我做 tracking" 这句话信息量约等于"我做矩阵乘法" —— 你必须问下一句"哪种？"。本文把 tracking 拆成 7 个家族 + 4 个公共数学组件 + 3 种 pipeline 模式 + 5 种 embodiment 用法，最后给一棵决策树。

**X-Ray.** 大部分新人把 tracking 当成"框跟着物体走"的单一问题 —— 但 RAFT (像素流) / SORT (多目标 ID) / FoundationPose (6D 姿态) / Skydio ActiveTrack (云台跟随) 在数学和工程上**几乎没有共同代码**。本 primer 让你看一眼分类，避免拿错锤子敲错钉子。

---

## 1 · 7 个 Tracking 家族（一句话定义）

```
                                                                       
   ┌─────────────────────────────────────────────────────────────────┐  
   │                    "Tracking" 在干嘛？                            │  
   ├─────────────────────────────────────────────────────────────────┤  
   │                                                                 │  
   │   per-pixel                  per-object              per-camera │  
   │   ┌──────┐  ┌──────┐         ┌──────┐  ┌──────┐      ┌──────┐  │  
   │   │ a 点 │  │ b 特征│         │ c 2D │  │ d 3D │      │ f 主动│  │  
   │   │ /像素│  │ KLT  │         │ MOT  │  │ MOT  │      │跟随  │  │  
   │   └──────┘  └──────┘         └──────┘  └──────┘      └──────┘  │  
   │                                                                 │  
   │                              ┌──────┐                ┌──────┐  │  
   │                              │ e 6D │                │ g伺服│  │  
   │                              │ pose │                │ servo│  │  
   │                              └──────┘                └──────┘  │  
   │                                                                 │  
   └─────────────────────────────────────────────────────────────────┘  
```

| # | 家族 | 一句话定义 | 代表作 | 区域文档 |
|---|---|---|---|---|
| **a** | Point / pixel tracking | "这个像素 / 物理点在后续 N 帧分别到哪里？" | RAFT, CoTracker, TAP-Net, PIPs | `raft_optical_flow.md`, `cotracker_and_tap_dissection.md` |
| **b** | Feature tracking | "这堆角点 / 描述子下一帧匹配哪个？" SLAM 前端核心 | KLT, Lucas-Kanade, SIFT-matching | `foundations/classical-slam/` |
| **c** | 2D object / MOT | "图像里所有人 / 车，给每个一个稳定 ID" | SORT, ByteTrack, DeepSORT, OC-SORT, FairMOT | `sort_bytetrack_mot_dissection.md` |
| **d** | 3D object / 3D MOT | "BEV / 点云里所有动态对象，3D 框 + ID" | AB3DMOT, CenterPoint-track, EagerMOT | `embodiments/driving/` |
| **e** | 6D object pose | "已知物体此刻的 (R, t)，且跨帧稳定" | FoundationPose, MegaPose, BundleTrack | `foundation_pose_dissection.md`, `megapose_dissection.md` |
| **f** | Active tracking | "云台 / 整机器人转向并跟随目标物（控制回路）" | Skydio ActiveTrack, DJI ActiveTrack, gaze control | `embodiments/aerial/active-tracking/` |
| **g** | Visual servoing tracking | "用图像误差直接驱动执行器（image-based control）" | IBVS, PBVS | `embodiments/manipulation/` |

**陷阱**: a / c 都叫 "tracking" 但**完全不同问题** —— a 是稠密 dense field，c 是离散 ID assignment。论文写 "we use tracking" 一定要追问哪个家族。

---

## 2 · 公共数学组件（贯穿所有家族）

虽然 7 个家族不同，**底层数学组件是共享的 4 件**。理解了这 4 件，看任何 tracker 都能拆开。

### 2.1 数据关联 (Data Association)

"上一帧的 5 个 track + 这一帧的 6 个 detection → 怎么配对？"

```
                                                                 
   上一帧 tracks:    T₁  T₂  T₃  T₄  T₅                            
                    │   │   │   │   │                            
                    ▼   ▼   ▼   ▼   ▼                            
                  ┌──────────────────┐                           
                  │   cost matrix    │  ← IoU / 距离 / appearance 
                  │   (5 × 6 矩阵)    │    相似度                  
                  └──────────────────┘                           
                    │   │   │   │   │                            
                    ▼   ▼   ▼   ▼   ▼                            
   这一帧 detects:  D₁  D₂  D₃  D₄  D₅  D₆                         
                                                                 
   匈牙利算法 (Hungarian, O(n³)) 找最小总 cost 的一一配对           
```

- **核心算法**: Hungarian / Munkres assignment (1955)；O(n³)，n 通常 <100 所以 ms 级
- **替代**: 贪心 IoU > 阈值（SORT 早期），或学到的 attention（Transformer tracker）
- **关键参数**: cost threshold（IoU < 0.3 视为不匹配 → 新建 track）

### 2.2 运动模型 (Motion Model)

"上一帧 track 当前帧应该在哪？" 用先验外推减少匹配歧义。

| 模型 | 假设 | 适用 | 代表 |
|---|---|---|---|
| 恒速 (CV) Kalman | 两帧间速度不变 | 行人 / 车流 / 高帧率 | SORT, ByteTrack |
| 恒加速 (CA) Kalman | 加速度不变 | 短时机动 | AD MOT |
| Bicycle / vehicle model | 车辆 kinematic | 3D MOT 车 | AB3DMOT |
| Random walk | 没有 prior | 极慢 / 不规则 | 室内 IoT |
| 学到的 (LSTM / Transformer) | 数据驱动 | 复杂运动 (DanceTrack) | OC-SORT, MOTRv3 |

**Insight**: Kalman = constant-velocity 假设 + 高斯不确定性。**这个假设对舞者 / 鸟群 / 急停车都不成立** → 2023+ 论文（OC-SORT, ByteTrack-V2）大半是在修这件事。

参看 `foundations/spatial-math/bayesian_filtering_ekf_msckf.md` 学完整 Kalman 推导。

### 2.3 外观模型 (Appearance Model)

"同样在那个位置的两个 detection，长得像不像？"

- **经典**: HSV 直方图、Haar 特征
- **现代**: ReID embedding (OSNet, FastReID) → 256-d 向量 → cosine 相似度
- **联合训练**: FairMOT / CenterTrack 把 detection + embedding 合在一个 head 里

**Trade-off**: appearance 强 → 处理长时遮挡好，但慢（每个 box 一次 CNN 前向）；纯 IoU 快但对穿越 / 遮挡脆弱。**ByteTrack 的反直觉发现**: 没有 appearance 也能上 80.3 MOTA（见 `sort_bytetrack_mot_dissection.md`）。

### 2.4 时序窗口 (Temporal Window)

"用最近 N 帧还是只看上一帧？"

| 窗口 | 名字 | 适用 | 代表 |
|---|---|---|---|
| 1 帧 (Markov) | online tracker | 实时部署 | SORT, ByteTrack |
| 短窗 (~10 帧) | sliding window | 弱遮挡恢复 | OC-SORT 的 virtual trajectory |
| 长窗 (~100 帧) | tracklet 重链接 | 离线视频分析 | global tracking |
| 全视频 | offline / batch | 数据集标注 | CoTracker, TAP-Net |

**注意**: online ≠ real-time。Online 指"只看过去"，real-time 指"每帧延迟 < 1/FPS"。CoTracker 是 online 但不 real-time（>100 ms/frame）。

---

## 3 · 三种典型 Pipeline 模式

| Mode | Pipeline | 优点 | 缺点 | 代表 |
|---|---|---|---|---|
| **1. Tracking-by-detection** | Frame → Detector (YOLO/DETR) → boxes → Tracker → IDs | detector / tracker 解耦，各自最优化 | detector 漏报直接丢轨 | SORT, ByteTrack |
| **2. Joint detection-tracking** | Frame → 共享 backbone → detect head + reid head → boxes + IDs | 端到端，共享特征 | 两 task 互相妥协 | FairMOT, CenterTrack |
| **3. Tracking-by-segmentation** | Frame₀ + click → mask → propagate 到全视频 | 像素级精度，自然处理形变 | 不直接给框 / ID；需手动初始化 | SAM 2, XMem |

SAM 2 (2024) 将 mode 3 推到 foundation 级 —— 单击 → 整段视频的 mask + ID（unify segment + track）。这是 2024–2026 最大 paradigm shift 之一。

---

## 4 · 跨 Embodiment 用法对照

不同身体看不同 "tracking"，理解这点能避免在 manipulation 论坛问 MOT 问题。

| Embodiment | 主要 tracking 家族 | 代表系统 / 论文 | 关键 sensor |
|---|---|---|---|
| **Manipulation / Humanoid** | e (6D pose) + a (point track) | FoundationPose, CoTracker for episode mining | RGB-D (RealSense / ZED) |
| **Autonomous Driving (AD)** | d (3D MOT) | CenterPoint-track, EagerMOT, AB3DMOT | LiDAR + 多目 camera |
| **Drone / Aerial** | f (active tracking) + c (2D MOT) | Skydio ActiveTrack, DJI ActiveTrack 5.0 | gimbal + 单目 / stereo |
| **AGV / 室内机器人** | c (2D / pedestrian MOT) | DeepSORT, ByteTrack on edge | RGB + 2D LiDAR |
| **Marine** | acoustic / sonar MOT (d 变体) | sonar-based MTT | sonar array |
| **AR / VR (headset)** | a + b (point + feature) | hand tracking, world locking | IR camera + IMU |

**一个非显然观察**: 同一篇 "tracking" 论文在不同 embodiment 含义不同 —— **AD 圈说 "tracking" 默认指 d (3D MOT)；manipulation 圈默认指 e (6D pose)**。跨圈交流先校准词汇。

---

## 5 · 决策树：你的应用 → 选哪种 tracking

```
                                                                 
   Q1: 你要追的是?                                                  
   ┌────────────────────────────────────────────────────────────┐  
   │                                                            │  
   │  ┌─像素 / 视觉特征点                                        │  
   │  │   ─► 稠密 / 短时 (2 帧)  → RAFT (a)                     │  
   │  │   ─► 稀疏 / 长时 (100+ 帧) → CoTracker, TAP-Net (a)     │  
   │  │   ─► SLAM 前端          → KLT / SIFT match (b)         │  
   │  │                                                         │  
   │  ┌─2D 边界框 (人 / 车) + ID                                 │  
   │  │   ─► online + 实时       → SORT / ByteTrack (c)         │  
   │  │   ─► 长时遮挡 + appearance → DeepSORT / BoT-SORT (c)    │  
   │  │   ─► 非线性运动 (跳舞 / 急转) → OC-SORT (c)              │  
   │  │   ─► 离线 / 高 IDF1     → MOTRv3 / SAMBA-MOTR (c)       │  
   │  │                                                         │  
   │  ┌─3D 边界框 / BEV + ID                                     │  
   │  │   ─► AD / nuScenes      → CenterPoint-track (d)         │  
   │  │                                                         │  
   │  ┌─物体 6D 姿态 (R, t)                                      │  
   │  │   ─► 新物体, 无 CAD     → FoundationPose mesh-free (e)   │  
   │  │   ─► 有 CAD             → FoundationPose / MegaPose (e)  │  
   │  │                                                         │  
   │  ┌─云台 / 整机器人跟随                                       │  
   │  │   ─► drone follow-me   → ActiveTrack (f)                │  
   │  │   ─► 机器人 head gaze  → 视觉伺服 (f / g)                 │  
   │  │                                                         │  
   │  ┌─物体 mask (像素级)                                       │  
   │  │   ─► 单击 + 视频        → SAM 2 (mode 3)                │  
   │                                                            │  
   └────────────────────────────────────────────────────────────┘  
```

---

## 6 · 常见 Trap 清单（新手必避）

1. **ID switching (ID switch)** —— 同一物体在遮挡前后被分配不同 ID。MOT 评测的 IDF1 指标专门测这件事。SORT 在长时遮挡场景 IDF1 远低于 MOTA。
2. **长时遮挡 (Long-term occlusion)** —— 物体消失 >30 帧后回来。纯 Kalman 外推已失效；需要 appearance ReID 或 virtual trajectory（OC-SORT）。
3. **高速 / 非线性运动** —— Kalman constant-velocity 假设破裂。舞者数据集 DanceTrack 专门暴露这件事；纯 SORT MOTA 大跌。
4. **外观相似 (Look-alike)** —— 同制服球员、同型号车辆。appearance embedding 失效；只能靠运动连续性 + 团队 prior。
5. **尺度变化 (Scale change)** —— 物体由远及近 box 面积变 100×。IoU 阈值需自适应；纯固定 IoU = 0.5 会切轨。
6. **检测漏报 (Missed detection)** —— detector 这一帧没看到 → 轨自动结束。**ByteTrack 的核心修复**：用 low-confidence detection 也尝试关联。
7. **跨域分布外 (Domain shift)** —— 在 MOT17 (城市步行街) 训的 tracker 在体育场 / 仓库直接掉 10+ MOTA。检测器先崩了，tracker 没救。

---

## 7 · 评测指标速查

| 指标 | 重点 | 注意 |
|---|---|---|
| **MOTA** | FP + FN + IDsw | 偏向 detection，对 ID switch 反应弱 |
| **IDF1** | 长时 ID 一致性 | 真正衡量 "track" 质量 |
| **HOTA** | 几何 + 关联平衡 | 2020 后推荐主指标 |
| **IDsw** | ID switching 次数 | 越少越好 |
| **FPS** | 速度 | 工业部署门槛 |

**规则**: 看论文先看 **HOTA + IDF1 + FPS** 三件套。只报 MOTA 的可能是 detector 强而 tracker 弱。

---

## 8 · 与本仓其他章节的关系

```
                                                                 
   本 primer (tracking 全景)                                       
        │                                                         
        ├──► foundation_pose_dissection.md  (家族 e - 6D)         
        ├──► megapose_dissection.md         (家族 e - 6D 前驱)    
        ├──► raft_optical_flow.md           (家族 a - dense flow) 
        ├──► cotracker_and_tap_dissection.md (家族 a - 长时 point)
        ├──► sort_bytetrack_mot_dissection.md (家族 c - 2D MOT)   
        │                                                         
        ├──► foundations/spatial-math/                            
        │    └─ bayesian_filtering_ekf_msckf.md  (Kalman 基础)     
        │                                                         
        ├──► foundations/classical-slam/                          
        │    └─ KLT / feature tracking (家族 b)                   
        │                                                         
        ├──► embodiments/aerial/active-tracking/   (家族 f)        
        ├──► embodiments/driving/                  (家族 d - 3D MOT)
        └──► embodiments/manipulation/             (家族 e 应用)   
```

---

## Boundary

- **MOT 单 paper 深度** → [`sort_bytetrack_mot_dissection.md`](./sort_bytetrack_mot_dissection.md)
- **6D pose 深度** → [`foundation_pose_dissection.md`](./foundation_pose_dissection.md), [`megapose_dissection.md`](./megapose_dissection.md)
- **像素流 / 长时点深度** → [`raft_optical_flow.md`](./raft_optical_flow.md), [`cotracker_and_tap_dissection.md`](./cotracker_and_tap_dissection.md)
- **Kalman / Bayesian filter 完整推导** → [`../spatial-math/bayesian_filtering_ekf_msckf.md`](../spatial-math/bayesian_filtering_ekf_msckf.md)
- **AD 端 3D MOT 实战** → [`../../embodiments/driving/`](../../embodiments/driving/)
- **Aerial active tracking 实战** → [`../../embodiments/aerial/active-tracking/`](../../embodiments/aerial/active-tracking/)

## References

- Hungarian Algorithm — Kuhn (1955) *The Hungarian method for the assignment problem*. Naval Research Logistics.
- Kalman (1960) *A New Approach to Linear Filtering and Prediction Problems*. ASME Trans.
- MOTChallenge (MOT15/16/17/20) — https://motchallenge.net/
- HOTA — Luiten et al. (2020) *HOTA: A Higher Order Metric for Evaluating Multi-Object Tracking*. IJCV. https://arxiv.org/abs/2009.07736
- SAM 2 — Ravi et al. (2024) *SAM 2: Segment Anything in Images and Videos*. https://arxiv.org/abs/2408.00714

---

[← Back to Pose & Tracking](./README.md)
