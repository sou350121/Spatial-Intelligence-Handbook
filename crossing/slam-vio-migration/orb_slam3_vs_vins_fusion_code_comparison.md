# ORB-SLAM3 vs VINS-Fusion — 代碼層工程哲學對比

> **類型**：comparison（跨 zone）— 不走 14 項 dissection 門檻，核心是「打開 IDE 改代碼時手感差別」
> **覆蓋**：兩條 production stack 在 main entry / 主 pipeline / 前端 / 狀態 / 優化器 / IMU / 初始化 / 回環 8 個維度的代碼級對照
> **互補對象**：
>
> - 兩篇 paper-level dissection：[`foundations/classical-slam/orb_slam3_dissection.md`](../../foundations/classical-slam/orb_slam3_dissection.md) · [`embodiments/aerial/vio/vins_mono_fusion_dissection.md`](../../embodiments/aerial/vio/vins_mono_fusion_dissection.md)
> - 教學基礎：[`foundations/classical-slam/pnp_dlt_primer.md`](../../foundations/classical-slam/pnp_dlt_primer.md) · [`embodiments/aerial/vio/ekf_from_scratch_dissection.md`](../../embodiments/aerial/vio/ekf_from_scratch_dissection.md)

**Status:** v1 — 代碼路徑與類名引自上游 repo（GitHub URL 在文末），實測 commit / API 行為標 `UNVERIFIED`。

**TL;DR.** 兩者**不是「同一類 SLAM 實現的不同版本」**，而是工程哲學差很多：

- **ORB-SLAM3 是 map-centric SLAM library** — 核心圍繞 `Frame / KeyFrame / MapPoint / Map / Atlas`，Tracking、LocalMapping、LoopClosing 彼此耦合，目標是完整建圖、重定位、多地圖、回環與全局一致性。
- **VINS-Fusion 是 estimator-centric ROS stack** — 核心是固定滑窗 VIO/VO 狀態估計器 `Estimator`，loop / global fusion 是相對獨立的 ROS node/package。

選哪個取決於你要改什麼：**SLAM 地圖 / 多地圖 / 重定位 → ORB-SLAM3**；**VIO 狀態估計 / IMU / multi-sensor fusion / GPS → VINS-Fusion**。

---

## 1. 工程入口：庫 vs ROS estimator stack

| 層面 | ORB-SLAM3 | VINS-Fusion |
|---|---|---|
| 主入口 | `src/System.cc` | `vins_estimator/src/rosNodeTest.cpp` |
| 核心對象 | `System`, `Tracking`, `LocalMapping`, `LoopClosing`, `Atlas`, `Optimizer` | `Estimator`, `FeatureTracker`, `FeatureManager`, `MarginalizationInfo`, `PoseGraph` |
| 工程形態 | 可作為 C++ SLAM library 調用，ROS examples 是附加 | 強 ROS / catkin 風格，topic callback + queue + estimator |
| 狀態中心 | 地圖、關鍵幀、地圖點、多 map | 固定滑窗內的 pose / velocity / bias / feature depth |
| Loop | 內建 `LoopClosing` thread | 可選 `loop_fusion_node`，和 estimator 分開跑 |

ORB-SLAM3 的 `System.cc` 初始化時會直接建立 `Tracking`、`LocalMapping`、`LoopClosing`，並把後兩者放到獨立 thread；後面還會把三者互相設 pointer，形成緊密耦合 pipeline。

VINS-Fusion 主 node 是 ROS subscriber + buffer + sync thread：`main()` 讀配置、建立 `Estimator`、訂閱 IMU / image / feature / restart 等 topic，然後啟動 `sync_process` thread 並 `ros::spin()`。

---

## 2. 主 pipeline 對比

### ORB-SLAM3 主線

```cpp
System::TrackMonocular / TrackStereo / TrackRGBD
    -> Tracking::GrabImage*
        -> Tracking::Track()
            -> TrackWithMotionModel()
            -> TrackReferenceKeyFrame()
            -> Relocalization()
            -> NeedNewKeyFrame()
            -> CreateNewKeyFrame()
                -> LocalMapping::InsertKeyFrame()

LocalMapping::Run()
    -> ProcessNewKeyFrame()
    -> MapPointCulling()
    -> CreateNewMapPoints()
    -> LocalBundleAdjustment / LocalInertialBA

LoopClosing::Run()
    -> DetectCommonRegionsFromBoW()
    -> DetectAndReffineSim3FromLastKF()
    -> CorrectLoop()
    -> MergeLocal()
    -> RunGlobalBundleAdjustment()
```

`Tracking.h` 裡有清晰 tracking 狀態機：`NO_IMAGES_YET` / `NOT_INITIALIZED` / `OK` / `RECENTLY_LOST` / `LOST`；同一個類裡還有 `Track()`、`MonocularInitialization()`、`TrackReferenceKeyFrame()`、`TrackWithMotionModel()`、`PredictStateIMU()`、`Relocalization()` 等。

### VINS-Fusion 主線

```cpp
rosNodeTest.cpp
    imu_callback()
        -> estimator.inputIMU(t, acc, gyr)

    img_callback / sync_process()
        -> estimator.inputImage(t, image0, image1)

Estimator::inputImage()
    -> FeatureTracker::trackImage()
    -> feature_buf.push()

Estimator::processMeasurements()
    -> processIMU()
    -> processImage()
        -> initialization 或 non-linear optimization
        -> triangulate()
        -> optimization()
        -> outlier rejection
        -> slideWindow()
        -> publish odometry / point cloud / keyframe
```

`Estimator` 接口非常 estimator-style：`inputIMU()`、`inputFeature()`、`inputImage()`、`processIMU()`、`processImage()`、`processMeasurements()`、`changeSensorType()`。

---

## 3. 前端特徵：ORB 描述子匹配 vs KLT 光流追蹤

| 層面 | ORB-SLAM3 | VINS-Fusion |
|---|---|---|
| 前端特徵 | ORB keypoint + descriptor | KLT optical flow + Shi-Tomasi 新點 |
| 匹配方式 | descriptor matching、BoW、MapPoint projection matching | feature id tracking，光流維持同一 feature id |
| 地圖關聯 | feature 會關聯到 `MapPoint` | feature 多數是滑窗內深度參數，**不是長期 `MapPoint`** |
| 回環詞袋 | ORB vocabulary / DBoW2 | loop_fusion 用 BRIEF vocabulary / DBoW2 |

ORB-SLAM3 依賴 ORB 特徵、DBoW2 詞袋、g2o；DBoW2 和 g2o 是 modified versions 含在 `Thirdparty/` 中。

VINS-Fusion 的 `FeatureTracker::trackImage()` 走 `cv::calcOpticalFlowPyrLK` 做 temporal tracking；不足的點再用 `cv::goodFeaturesToTrack` 補新點，可做 reverse check 和 fundamental matrix RANSAC reject。

**改前端時的落點**：

```
ORB-SLAM3:  改 ORBextractor / ORBmatcher / Frame / KeyFrame / MapPoint 關係
VINS-Fusion: 改 FeatureTracker / optical flow / mask / RANSAC / feature id 管理
```

ORB-SLAM3 前端更像「特徵—描述子—地圖點」系統；VINS-Fusion 前端更像「連續幀 feature track 管理器」。

---

## 4. 狀態量：儲存地圖 vs 儲存滑窗狀態

### ORB-SLAM3 的狀態中心

`Atlas` 代碼裡有多個 `Map`、當前 map、bad maps、map points、keyframes、camera、KeyFrameDatabase、ORBVocabulary 等成員；它不是只估計最近幾幀，而是在維護一個可持久化、可切換、可 merge 的 map graph：

```cpp
Atlas
  ├── Map 0
  │    ├── KeyFrame
  │    ├── KeyFrame
  │    └── MapPoint
  ├── Map 1
  └── currentMap

Tracking
  ├── current Frame
  ├── last Frame
  ├── local map
  └── references to LocalMapping / LoopClosing / Atlas
```

### VINS-Fusion 的狀態中心

`Estimator` 是固定滑窗形式，核心成員包括：

```cpp
Ps[WINDOW_SIZE + 1]   // position
Rs[WINDOW_SIZE + 1]   // rotation
Vs[WINDOW_SIZE + 1]   // velocity
Bas[WINDOW_SIZE + 1]  // accelerometer bias
Bgs[WINDOW_SIZE + 1]  // gyroscope bias
td                    // time delay
para_Pose
para_SpeedBias
para_Feature
para_Ex_Pose
para_Td
pre_integrations
```

`parameters.h` 固定 `WINDOW_SIZE = 10`，定義 pose / speed-bias / feature 等 parameter block 尺寸。

**本質差異**：

```
ORB-SLAM3:   長期 map graph + local/global BA + relocalization + multi-map
VINS-Fusion: 固定長度 sliding window + marginalization + local VIO/VO state
```

---

## 5. 優化器：g2o map BA vs Ceres sliding-window factor graph

| 層面 | ORB-SLAM3 | VINS-Fusion |
|---|---|---|
| 優化器 | g2o | Ceres |
| 優化粒度 | pose、MapPoint、KeyFrame graph、essential graph、Sim3、inertial BA | 滑窗 pose、speed/bias、feature inverse depth、extrinsic、time delay |
| 邊/殘差風格 | ORB-SLAM 系的 graph optimizer | factor classes + parameter blocks + marginalization |
| 回環優化 | LoopClosing 內部調用 pose graph / BA / Sim3 | loop_fusion 裡 PoseGraph 做 4DoF / 6DoF pose graph |

ORB-SLAM3 的 `Optimizer.h` include 多種 g2o 類型，提供 `BundleAdjustment()`、`GlobalBundleAdjustment()`、`FullInertialBA()`、`LocalBundleAdjustment()`、`PoseOptimization()`、`PoseInertialOptimizationLastKeyFrame()`、`OptimizeEssentialGraph()`、`OptimizeSim3()`、`LocalInertialBA()`、`MergeInertialBA()`、`InertialOptimization()` 等靜態方法。

VINS-Fusion 用 Ceres Solver；`Estimator` include Ceres 和 projection / IMU / marginalization / pose local parameterization 等 factor 相關頭文件，狀態通過 `vector2double()` 填進 Ceres parameter blocks，再 `double2vector()` 寫回。

**改優化殘差時的落點**：

```
ORB-SLAM3:
    include/Optimizer.h
    src/Optimizer.cc
    g2o vertex / edge
    KeyFrame / MapPoint / IMU state

VINS-Fusion:
    vins_estimator/src/factor/*
    estimator.cpp::optimization()
    estimator.cpp::vector2double()
    estimator.cpp::double2vector()
    marginalization_factor
```

---

## 6. IMU 處理：融在 SLAM pipeline vs VIO 主體

ORB-SLAM3 的 `System::TrackMonocular()` 可接收 `vector<IMU::Point>`，把 IMU 數據 push 給 tracker 再進 `GrabImageMonocular()`；建構 `Tracking` / `LocalMapping` / `LoopClosing` 時會根據 sensor type 判斷 inertial flag。

VINS-Fusion 則典型：`imu_callback()` 調 `estimator.inputIMU()`；`processIMU()` 做 preintegration / propagation，更新 `Rs` / `Ps` / `Vs`，處理 bias 和 gravity。

```
ORB-SLAM3:
    IMU 是 SLAM tracking / local mapping / BA 的一部分
    代碼重點: Tracking + LocalMapping + Optimizer + IMU initialization

VINS-Fusion:
    IMU 是 estimator 的核心輸入
    代碼重點: inputIMU -> processIMU -> preintegration -> processImage -> optimization
```

---

## 7. 初始化：SLAM 狀態機 vs VIO alignment

```
ORB-SLAM3 initialization:
    image init -> create map -> tracking OK
    inertial mode 下再做 IMU initialization / scale / bias / gravity refinement

VINS-Fusion initialization:
    collect window -> visual SFM / PnP
    if IMU: Visual-IMU alignment -> scale / gravity / bias
    then solver_flag = NON_LINEAR
```

ORB-SLAM3 用 `Tracking` 狀態機（`NOT_INITIALIZED` / `OK` / `RECENTLY_LOST` / `LOST`），所有初始化、重定位、IMU prediction 都在 Tracking 主流程內。

VINS-Fusion 用 `SolverFlag INITIAL / NON_LINEAR` 和 `MarginalizationFlag MARGIN_OLD / MARGIN_SECOND_NEW`；初始化含 `initialStructure()`、`visualInitialAlign()`、PnP、Global SFM、Visual-IMU alignment，之後才進非線性滑窗優化。

---

## 8. 回環：內建核心線程 vs 外掛式 loop_fusion

ORB-SLAM3 的 `LoopClosing` 是 `System` 初始化時直接建立並啟動的 thread；持有 `Atlas`、`KeyFrameDatabase`、`ORBVocabulary`、`LocalMapping` 等引用，提供 `DetectCommonRegionsFromBoW()`、`DetectAndReffineSim3FromLastKF()`、`CorrectLoop()`、`MergeLocal()`、`RunGlobalBundleAdjustment()`。

VINS-Fusion 的 loop 是另一個 node：`vins_node` 之外可再啟 `loop_fusion_node`；`PoseGraph` 載入 BRIEF vocabulary、查 DBoW database、`detectLoop()`、`addKeyFrame()`，根據是否用 IMU 啟動 4DoF 或 6DoF pose graph optimization。

**實際代碼差異**：

```
ORB-SLAM3:
    loop closure 會深度影響 Atlas / Map / KeyFrame / MapPoint / BA

VINS-Fusion:
    estimator 主要輸出 local odometry
    loop_fusion 主要修 pose graph / drift / path
```

---

## 9. 改代碼時的實際手感

### 9.1 你要改前端

```
ORB-SLAM3:
    ORBextractor / ORBmatcher / Frame / KeyFrame / MapPoint / Tracking
    代價: feature/descriptor/MapPoint/local map tracking 強耦合
          改一處常牽動 tracking / mapping / loop

VINS-Fusion:
    feature_tracker.cpp / feature_tracker.h
    Estimator::inputImage() / Estimator::processImage()
    FeatureManager
    代價: 光流品質 / feature id 穩定性 / 時間同步 / IMU-image alignment
          會直接影響 estimator
```

### 9.2 你要加新 residual / factor

```
ORB-SLAM3:
    Optimizer.h / Optimizer.cc
    g2o edge / vertex
    KeyFrame / MapPoint / IMU state

VINS-Fusion:
    vins_estimator/src/factor/*
    estimator.cpp::optimization()
    vector2double() / double2vector()
    marginalization
```

VINS-Fusion 對「加 factor」**更直觀**（整個 estimator 本來就是 Ceres factor graph 風格）；ORB-SLAM3 對「加 SLAM 地圖約束」**更自然**（已有完整 map graph / keyframe graph / loop graph）。

### 9.3 你要做 multi-session / map reuse / relocalization

**偏 ORB-SLAM3**。`Atlas`、`Map`、`KeyFrameDatabase`、`LoopClosing`、BoW relocalization 都是核心架構的一部分。

VINS-Fusion 也能 loop/path correction，但主 estimator 不是為「長期可重用地圖」設計，比較像穩定提供 local VIO/VO odometry，loop/global fusion 做後端修正。

### 9.4 你要做 GPS / multi-sensor fusion

**偏 VINS-Fusion**。工程命名 + README 都是 multi-sensor state estimator，repo 有 `global_fusion`、`loop_fusion`、`vins_estimator` 等 package 分工。

ORB-SLAM3 也可擴展，但會進入 map/keyframe/BA/loop 耦合，修改成本較高。

---

## 10. 一句話總結

> **ORB-SLAM3 的代碼是「完整 SLAM 系統」** — Tracking 產生 KeyFrame，LocalMapping 維護 MapPoint，LoopClosing 修正 Atlas，**全局一致性是核心**。

> **VINS-Fusion 的代碼是「固定滑窗 VIO/VO estimator」** — FeatureTracker 給 tracks，Estimator 做 IMU preintegration + Ceres optimization + marginalization，**loop/global fusion 是相對獨立的後處理模塊**。

| 目標 | 選哪個 |
|---|---|
| 研究 SLAM 地圖、回環、重定位、多地圖、KeyFrame/MapPoint 管理 | **ORB-SLAM3** |
| 研究 VIO 狀態估計、IMU preintegration、滑窗優化、marginalization、sensor calibration、GPS/loop fusion 接入 | **VINS-Fusion** |

---

## Cross-references

- Paper-level dissection：
  - [`foundations/classical-slam/orb_slam3_dissection.md`](../../foundations/classical-slam/orb_slam3_dissection.md) — ORB-SLAM3 paper 拆解（三線程 + Atlas）
  - [`embodiments/aerial/vio/vins_mono_fusion_dissection.md`](../../embodiments/aerial/vio/vins_mono_fusion_dissection.md) — VINS-Mono/Fusion paper 拆解（滑窗 VIO）
- 教學上游：
  - [`foundations/classical-slam/pnp_dlt_primer.md`](../../foundations/classical-slam/pnp_dlt_primer.md) — PnP 是兩者前端共用基礎
  - [`embodiments/aerial/vio/ekf_from_scratch_dissection.md`](../../embodiments/aerial/vio/ekf_from_scratch_dissection.md) — VIO state estimation 從零教學
- 相關失敗信號：
  - [`foundations/classical-slam/github_failure_atlas.md`](../../foundations/classical-slam/github_failure_atlas.md) — ORB-SLAM3 的 maintainer 帶寬 vs 用戶量 gap
  - [`embodiments/aerial/vio/github_failure_atlas.md`](../../embodiments/aerial/vio/github_failure_atlas.md) — VINS-Fusion #3 從 2019 至今 open
- 跨 zone 全景：
  - [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](./vggt_vs_drone_vio.md) — feed-forward 3D 為什麼取代不了 VIO 的延遲預算

---

## Sources

代碼路徑與類名引自上游 repo 公開 master：

- ORB-SLAM3: <https://github.com/UZ-SLAMLab/ORB_SLAM3>
  - `src/System.cc` · `include/Tracking.h` · `include/Atlas.h` · `include/Optimizer.h`
- VINS-Fusion: <https://github.com/HKUST-Aerial-Robotics/VINS-Fusion>
  - `vins_estimator/src/rosNodeTest.cpp` · `vins_estimator/src/estimator/estimator.h` · `vins_estimator/src/estimator/estimator.cpp` · `vins_estimator/src/estimator/parameters.h` · `vins_estimator/src/featureTracker/feature_tracker.cpp`

---

[← Back to crossing](../overview.md) · [→ ORB-SLAM3 dissection](../../foundations/classical-slam/orb_slam3_dissection.md) · [→ VINS-Fusion dissection](../../embodiments/aerial/vio/vins_mono_fusion_dissection.md)
