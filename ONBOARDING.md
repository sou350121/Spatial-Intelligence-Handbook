# Onboarding — 5 分鐘找到你該讀什麼

> **186 個 md、13 zone、36 dissection、10 atlas、5 comparison。第一次來容易迷路。本文 5 分鐘把你導到正確入口。**
> 完整概覽見 [`README.md`](./README.md) · 結構地圖見 [`cheat-sheet/functional_map.md`](./cheat-sheet/functional_map.md)

---

## 🚪 60 秒簡介

這本 handbook 做 **一件事**：把 manipulation / aerial / driving / marine 圈各自閉門發明的同一類問題（SLAM / 3D 表徵 / sensor 選型 / VLA 接口）攤在桌上橫向對比 + 給一套 3DGS / VGGT / depth foundation 的統一底層教科書。

**不寫**：產業地圖（→ `companies/`）、論文簡單介紹（→ arxiv 自己讀）、單 embodiment 從零教程（→ 各 embodiment 自己有教材，aerial 例外 — 我們有 HKUST 全套）。

---

## 🎯 第一步：你的場景是什麼？

挑最近的：

### A. 我要做 production — 真的要把東西飛起來 / 跑起來

```
1. embodiments/aerial/real_flight_production_gotchas.md       (16.6 KB · 15 min)
   — HKUST lab1-3 一手 gotchas，組裝→OptiTrack→onboard 全流程踩坑
2. embodiments/aerial/vio/README.md                            (5 min)
   — 三栈 VINS-Fusion / OpenVINS / DROID-SLAM 對比 + 推哪個
3. foundations/sensor-physics/sensor_selection_decision_matrix.md  (24 KB · 20 min)
   — 23 sensor × 14 維 SWaP-C 對比表 + 6 use case 決策樹
4. deployment/calibration/sensor_calibration_drift_in_production.md
   — calibration 半年後為什麼漂
```
**🎁 結果**：知道**哪個 stack 能飛、會撞哪些牆**。

---

### B. 我要看 2026 spatial AI 的範式變化

```
1. foundations/feed-forward-3d/vggt_cvpr2025_dissection.md     (10 min)
   — CVPR 2025 best paper，feed-forward 取代 incremental SfM 的範式
2. crossing/slam-vio-migration/vggt_vs_drone_vio.md            (10 min ★ 旗艦)
   — 同一問題在 manipulation / aerial / marine 的答案差這麼大
3. cheat-sheet/cross_zone_failure_atlas.md                     (11.7 KB · 15 min)
   — 10 zone × 42 工具的 6 大失敗模式（誰活 / 誰死 / 誰假裝活）
```
**🎁 結果**：分得清**哪個方向是 hype、哪個是真正的下一輪**。

---

### C. 我是 PhD / 想找 paper idea

```
1. cheat-sheet/cross_zone_failure_atlas.md                     (15 min)
   — 看 atlas 找跨 zone 反復出現的 unsolved 問題
2. foundations/spatial-math/cross_domain_math_inspirations.md  (15 min)
   — 10 個跨域數學切口（信息幾何 / OT / equivariant / certifiable SLAM）
3. foundations/spatial-math/se3_equivariance_in_networks_primer.md  (13 KB · 10 min)
   — 為什麼 sample efficiency 5-10× 的 architecture move 還沒爆
4. foundations/semantic-3d/README.md § Watch list             (5 min)
   — v2 候選（SG-Reg / ConceptGraphs / OVIR-3D 為什麼還沒拆）
```
**🎁 結果**：拿到 5+ 個**真的有 paper-able gap** 的方向。

---

### D. 我是學生 — 想從零學 aerial robotics

```
讀序（HKUST ELEC5660 取材 + handbook dissection 配套）：
1. foundations/spatial-math/rotation_intuition_primer.md       (基礎)
2. foundations/spatial-math/se3_so3_lie_groups_primer.md       (manifold)
3. embodiments/aerial/dynamics_and_control_primer.md           (quadrotor EOM + cascade PID)
4. foundations/classical-slam/pnp_dlt_primer.md                (DLT + RANSAC)
5. foundations/depth-foundation/classical_stereo_primer.md     (stereo geometry)
6. embodiments/aerial/planning/min_snap_dissection.md          (trajectory)
7. embodiments/aerial/vio/ekf_from_scratch_dissection.md       (15-state EKF)
8. embodiments/aerial/vio/openvins_dissection.md               (生產栈)
9. embodiments/aerial/real_flight_production_gotchas.md        (真機)
```
**🎁 結果**：從 0 到能用 HKUST 教材自己飛真機，**handbook 是你的 study guide**。

---

### E. 我是算法工程師 — 想跨 embodiment 轉崗

```
1. crossing/slam-vio-migration/vggt_vs_drone_vio.md            (★ 看完知道為什麼跨不過去)
2. crossing/sensor-stack-matrix/                               (sensor 跨 embodiment 怎麼變)
3. crossing/slam-vio-migration/orb_slam3_vs_vins_fusion_code_comparison.md
   — 兩條 production stack 的代碼層工程哲學差異
4. embodiments/<你想去的 embodiment>/README.md
```
**🎁 結果**：把舊知識**精準對到新領域**，不靠面試官 mercy。

---

### F. 我是 ML 研究員 — 要把 3D / SE(3) 加進我的 model

```
1. foundations/spatial-math/rotation_reps_in_deep_learning_primer.md  (Zhou 2019 6D)
2. foundations/spatial-math/se3_equivariance_in_networks_primer.md    (VN / TFN / E3NN)
3. foundations/feed-forward-3d/vggt_cvpr2025_dissection.md            (現代 architecture 範本)
4. bridge-to-vla/feature-cloud-to-action.md                            (3D → action head)
```
**🎁 結果**：知道**為什麼 quaternion 在 DL regression head 收斂慢、6D 為什麼贏**。

---

## ⏱️ 30 分鐘核心序列（不管你是誰都該讀）

如果不確定，按這個讀：

| 順序 | 篇 | 時間 | 為什麼讀 |
|---|---|---|---|
| 1 | [`cheat-sheet/functional_map.md`](./cheat-sheet/functional_map.md) | 5 min | 看 handbook 整體結構地圖（按功能而非位置）|
| 2 | [`foundations/feed-forward-3d/vggt_cvpr2025_dissection.md`](./foundations/feed-forward-3d/vggt_cvpr2025_dissection.md) | 10 min | 看 2026 spatial AI 範式變化（CVPR 2025 best paper）|
| 3 | [`crossing/slam-vio-migration/vggt_vs_drone_vio.md`](./crossing/slam-vio-migration/vggt_vs_drone_vio.md) | 10 min | 看 handbook 代表作 — 同問題在 manipulation/aerial 答案為什麼差 |
| 4 | [`cheat-sheet/cross_zone_failure_atlas.md`](./cheat-sheet/cross_zone_failure_atlas.md) | 5 min | 看 42 工具的生死狀態 — 別被 hype 騙 |

---

## 🗂️ 進階：按目錄結構

| 目錄 | 是什麼 | 何時來 |
|---|---|---|
| [`foundations/`](./foundations/) | 13 zone · 82 dissection — 跨 embodiment 共享底層 | 想拆某個 paper 進來 |
| [`embodiments/`](./embodiments/) | 6 embodiment — 應用層（aerial 是深度錨點，1.5-2× 其他）| 想看「在我的場景怎麼用」|
| [`crossing/`](./crossing/) | 跨 embodiment 對比 — handbook 真正的 USP | 想看「為什麼方法 X 在 A 行在 B 不行」|
| [`cheat-sheet/`](./cheat-sheet/) | 全景元視圖 — functional map + timeline + cross-zone atlas | 想看「整本 handbook 一頁紙」|
| [`deployment/`](./deployment/) | 工程實戰 — calibration / failure modes / hardware selection | 想做 production 不踩坑 |
| [`bridge-to-vla/`](./bridge-to-vla/) | 與 VLA-Handbook 的接口 | 想做 3D-aware VLA |

---

## 🛑 這本 handbook **不寫**的事

- **產業地圖 / 公司分析** → `companies/`（在這仓但側重技術）/ 行業報告
- **單 paper 簡單介紹** → arxiv 自己讀（我們只寫 dissection，重點是「拆」）
- **單 embodiment 完整教程** → 除 aerial 外，其他 embodiment 是「橫向比較粒度」非「教材」
- **AD (autonomous driving) BEV/Occupancy 深度** → AD 圈論文已多，我們不複製
- **論文 score / leaderboard 排名** → handbook 不打分，靠 atlas 看真實 deployment 狀態
- **VLA action policy** → 那是姊妹仓 [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) 的工作

---

## 🤝 怎麼貢獻

- 看 [`AGENTS.md`](./AGENTS.md) — 14 項 dissection 模板 + 5 type 文檔分層 + 自動 audit 規則
- 開 PR — `scripts/handbook_audit.py` 會自動跑 7 個 lint check
- Audit 通過後才能 merge

---

🔗 完整 README · [`README.md`](./README.md)
🔗 功能地圖 · [`cheat-sheet/functional_map.md`](./cheat-sheet/functional_map.md)
🔗 姊妹仓 · [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)

---

*Last updated: 2026-05-22 · 5 min to find your entry · 30 min to build framework · the rest is depth.*
