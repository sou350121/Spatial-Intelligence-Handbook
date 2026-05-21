# nuScenes, Waymo Open, Argoverse 2 — Why "SOTA on nuScenes" Travels Badly (三大自动驾驶基准为何不可互换)

**Status:** v1 — opinionated draft. Annotation cost and dataset-size numbers marked `UNVERIFIED`.
**TL;DR:** 这三者并不是同一基准的三个副本。它们在 **sensor rig geometry、label semantics、split policy** 三方面有本质差异 — 而正是这些差异，使一个在 nuScenes 上获胜的方法常常输给 Waymo。读 AD 论文时，先看 rig 示意图再看 leaderboard。

---

## 1 · "AD benchmark" 其实是三个 benchmark

差不多有五年，文献都把 nuScenes 当默认。然后 Waymo Open 上线了一套更难的 rig + 更大的标注预算；Argoverse 2 接着上线了多城市长尾 rig。到 2024 年，正经论文至少都报两个；到 2026 年，只报 nuScenes 已经被读作 "这方法泛化不了" 的信号。

本手册关心的问题是 **为什么** 数字会分化 — 答案大多在 sensor rig 和 label semantics，而不是算法。

---

## 2 · Rig 差异承担了大部分工作

| | **nuScenes** (Boston + Singapore) | **Waymo Open** (Phoenix + SF + Mountain View) | **Argoverse 2** (6 US cities) |
|---|---|---|---|
| Cameras | 6 × 1600×900 (1 front, 1 front-left/right, 1 back, 1 back-left/right) | 5 × 1920×1280 (front + 4 side) | 7 × 2048×1550 ring + 2 stereo |
| LiDAR | 1 × 32-beam roof Velodyne | 1 × 64-beam top + 4 × short-range side | 2 × 32-beam roof |
| LiDAR points / frame | ~35k | ~177k | ~110k |
| Camera FOV coverage | 360° sparse | 252° dense (no rear) | 360° dense |
| Sample rate (keyframes) | 2 Hz | 10 Hz | 10 Hz |
| Geographic diversity | 2 cities | 3 cities (mostly sunny) | 6 cities incl. rain / snow |
| Sequence length | ~20 s | ~20 s | ~15 s |
| Total annotated frames | ~40k keyframes `UNVERIFIED` | ~230k `UNVERIFIED` | ~150k `UNVERIFIED` |

**最关键的差异**：Waymo 每帧 LiDAR 点数是 nuScenes 的约 5×；Argoverse 2 配的是 7 路环形相机。一个针对 nuScenes "6 相机 + 稀疏 LiDAR" 布局调过的 camera-only BEV detector，*无法*直接在 Waymo (FOV 重叠不同、量程不同) 或 Argoverse 2 (image aspect ratio 不同 + 多了一路相机) 上复现自己的数字。

---

## 3 · Label 语义 — leaderboard 悄悄漂移的地方

Bounding box 语义的差异不会出现在头条 mAP 里，但其影响非常实在：

- **nuScenes** 用 10 个检测类 + 8 个属性状态（如 `pedestrian.moving`）。velocity 在 label 里。
- **Waymo Open** 用 4 个检测类（vehicle / pedestrian / cyclist / sign），但 3D box 质量更高 + LET-3D-AP 度量对纵向误差更宽容。
- **Argoverse 2** 用 30 个长尾类，包括施工设备、婴儿车、铰接公交车。长尾 mAP 主导。

这就是 "SOTA on nuScenes" 难以迁移的原因：

1. 针对 10 类 + 2 Hz 关键帧推理优化的方法，会过拟合到 **时间稀疏推理** — Waymo 的 10 Hz 会把 flicker 暴露出来。
2. Argoverse 2 的 30 类长尾奖励的是另一种归纳偏置（open-set / few-shot），nuScenes 调出来的检测头并不携带它。
3. Waymo 的 LET-3D-AP 度量对纵向误差宽容 — 靠纵向精度生死的方法在 Waymo 上看起来比 nuScenes 好。

---

## 4 · Occupancy 基准的分裂

2023–2024 把 **occupancy prediction** 推为 AD 感知首要任务后，这些数据集差异变得更尖锐。

| Occupancy benchmark | Built on | Label source | Grid resolution |
|---|---|---|---|
| **Occ3D-nuScenes** | nuScenes | LiDAR-accumulated + manual cleanup | 0.4 m voxels, 200×200×16 |
| **Occ3D-Waymo** | Waymo Open | LiDAR-accumulated, no manual fix | 0.4 m, larger range |
| **OpenOccupancy** | nuScenes | Same accumulation, denser labels `UNVERIFIED` | 0.2 m option |
| **CVPR 2023 challenge split** | nuScenes | Org-curated subset | matches Occ3D-nuScenes |

要点：**occupancy splits 是数据集特定方言，不是可移植 benchmark**。论文说 "65% mIoU on Occ3D" 必须指明是哪个数据集的 Occ3D。跨 occupancy 迁移是开放问题（Cosmos / SimGen 和 ScalableSimulator 押注 *合成数据*能弥合这个 gap；结果待定 `UNVERIFIED`）。

---

## 5 · 为什么 nuScenes 仍是合适的 *第一* 个 benchmark

尽管有上述问题，对多数团队 nuScenes 仍是正确的 *第一* benchmark：

- 40k 关键帧能塞进一台工作站；Waymo 的 230k 帧 + 更大的每帧 LiDAR 通常需要集群级存储。
- 6 相机环形布局匹配多数量产车 ship 的 *廉价* AD rig（Tesla 一类）。
- Leaderboard 文化成熟；baseline 可复现。

陷阱是 *停在* nuScenes。2026 的范式是：在 nuScenes 上原型 → 在 Waymo 上验证泛化 → 在 Argoverse 2 上压力测试长尾。

---

## 6 · "迁移失败" 实际长什么样

三种 pattern 反复出现：

1. **Range cliff.** 在 nuScenes 上调出的 BEV detector，在 ~50 m 以外开始退化 — 因为它训练所依赖的稀疏 32-beam LiDAR 在那里就停止提供监督。Waymo 的 64-beam 顶部 LiDAR + 4 路短程 LiDAR 把这个 gap 暴露出来。
2. **Class imbalance 翻转.** Argoverse 2 的铰接公交、施工设备在 nuScenes 标签里很少；nuScenes 调出的检测头默认走 "vehicle"，把这些当 false negative 吃掉。
3. **Weather-rig 依赖.** Argoverse 2 包含雨 / 雪；nuScenes 在 Singapore 段大体晴朗。camera 重的方法在恶劣天气下退化幅度高于 LiDAR 重的方法。

如果论文报跨数据集数字而 gap >15% mAP，rig 差异解释的部分可能多于算法本身。

---

## 7 · Sensor rig 是隐藏的超参数

结论简单但后果严重：**你选的 AD benchmark 决定了你选了哪一整套 rig 假设**。没有对 rig 做归一化的方法比较，就不是方法比较 — 而是伪装成方法比较的 rig 比较。

对实践者：

- 关心 *camera-only* 方法（Tesla 一类部署）：nuScenes + Argoverse 2 ring camera 是正确的成对组合。
- 关心 *LiDAR-heavy* 方法（Waymo 一类部署）：Waymo Open 是 canonical bar；nuScenes 是次要。
- 关心 *长尾安全*：Argoverse 2 的 30 类标签是唯一真正触及该问题的。

没有所谓的单一 "AD benchmark"。选与部署目标匹配的 rig，然后在其他 rig 上为跨数据集数字做辩护。

---

## Boundary

本文在 dataset / rig 层面比较三个感知基准。Per-method 拆解（BEVFormer、BEVFusion、OccFormer、SparseOcc）当 wedge 落地后归 `foundations/`。端到端驾驶模拟器（CARLA、nuPlan、Waymo-Sim）评分维度不同，住别处。LiDAR 和相机自身的传感器物理：`foundations/sensor-physics/`。

## References

- nuScenes — Caesar et al. *CVPR 2020*. https://arxiv.org/abs/1903.11027
- Waymo Open Dataset — Sun et al. *CVPR 2020*. https://arxiv.org/abs/1912.04838
- Argoverse 2 — Wilson et al. *NeurIPS 2021 (Datasets track)*. https://arxiv.org/abs/2301.00493
- Occ3D — Tian et al. *NeurIPS 2023*. https://arxiv.org/abs/2304.14365
- OpenOccupancy — Wang et al. *ICCV 2023*. https://arxiv.org/abs/2303.03991
- LET-3D-AP — Hung et al. (Waymo metric). https://waymo.com/open/challenges/
