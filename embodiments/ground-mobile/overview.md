# Ground Mobile · AGV / 室内机器人 / VLN

**范围：** 轮式/履带式地面机器人——仓储 AGV、家用/服务机器人、以及在 Habitat / HM3D / Matterport3D 等仿真环境中跑的视觉语言导航（VLN）研究智能体。

**状态：** v1 入口页。本子树下的所有 benchmark 数字标 `UNVERIFIED`，除非经实机验证。

---

## 为什么"地面移动"单独成子树（而不是合并到 driving 或 humanoid）

三个原因：

1. **GNSS 大多可用。** 室外 AGV 有 GNSS 作为兜底信号，aerial-indoor 和 indoor-VLN 都没这个待遇。室内 AGV 则有 *已知地图*（仓库平面图、酒店平面图），别的子树都没法假设这一点。
2. **轮式里程计便宜、精确、且是公制的。** 这把整个栈推到了和 aerial（纯 IMU 约束）以及 humanoid（脚部接触估计问题）截然不同的延迟/精度预算上。
3. **控制带宽宽松。** 典型工作速度 0.5–2 m/s；30 Hz 的状态就够用；没有 200 Hz 控制器的延迟死线。这从根本上改变了哪些 encoder 能上线——VGGT 类前馈在 5 Hz 出结果，对 aerial racing 太慢，对室内 AGV 却是*太快*。

GNSS + 轮式里程计 + 慢控制——这三者组合就是这个子树的位置。Aerial 一个都拿不到；humanoid 失去轮式里程计；driving 有 GNSS 但工作速度（10–30 m/s）已经把地面移动的假设打穿。

---

## 三个细分领域（共享的东西比想象中少）

| 细分 | 主要任务 | 地图类型 | 速度 | 空间瓶颈 |
|---|---|---|---|---|
| **仓储 AGV** | 货到人、托盘搬运 | 先验公制（工程化布置） | 1–2 m/s | 多车交通 + 动态行人 |
| **家用/服务机器人** | 清洁、配送、取物 | SLAM 现建、半静态 | 0.3–1 m/s | 光照变化、反光地板、电线、楼梯（禁区） |
| **VLN 智能体** | "去到有蓝沙发的房间" | 仅仿真（HM3D / MP3D） | 仿真步 | 语言 ↔ 空间 grounding |

仓储和家用共享*地图性质*（多为静态、平面）。家用和 VLN 共享*语言条件任务*。仓储和 VLN 几乎不共享什么——把它们塞进"地面移动"一个子树更多是分类便利，而不是方法可迁移。

最干净的心智模型：**仓储是已被工程化解决的问题**，**家用是脏的现实世界**，**VLN 是 benchmark 驱动的研究、能否在真实世界存活待观察**（见 `vln_and_object_nav.md` §5）。

---

## 为什么地面移动 *不是* aerial（对照案例）

| 约束 | 地面移动 | Aerial（见 `embodiments/aerial/`） |
|---|---|---|
| GNSS 可用 | 室外常有；室内有已知地图 | 室外有时有；室内永远没有 |
| 轮式里程计 | 有（公制、漂移约 1%） | 没有 |
| 最低状态率 | 30 Hz | 200 Hz |
| 延迟预算 | 50–100 ms | 5–15 ms |
| 失败后果 | 停下等待 | 坠机 |
| 视觉退化容忍度 | 小时级（机器人可以静止） | 秒级（重力不等人） |

最大的一个工程后果：**地面机器人能跑慢 encoder**。200 ms 的 VGGT 类推理在四旋翼上完全不能用，在 AGV 上完全可部署。这就是为什么 ground-mobile 是第一个让前馈 3D 和大模型感知进入量产的 embodiment，而 aerial 落后 2–3 年（见 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`）。

---

## Benchmark 独立性（别重复计数）

地面移动用的仿真 benchmark 故意和 manipulation、driving 互不相通：

- **HM3D**（Habitat-Matterport 3D）——1000+ 扫描家庭室内。ObjectNav、ImageNav 的标准。
- **Matterport3D**（MP3D）——更老，90 个建筑级别扫描。R2R VLN benchmark 用它。
- **Habitat 3.0**——多智能体 + humanoid 扩展；地面移动仍是主要 embodiment。
- **AI Habitat / iGibson / RoboTHOR**——替代的仿真生态。

driving benchmark（nuScenes、Waymo Open）替代不了。manipulation benchmark（RLBench、LIBERO）替代不了。数据分布——亚 2 m/s 速度穿过杂乱家庭室内、带语言查询——是真正独有的。这也是为什么 "VLN" 值得一篇深度文档，而不只是 "navigation"。

---

## 本目录文件

| 文件 | 用途 | 状态 |
|---|---|---|
| `vln_and_object_nav.md` | 视觉语言导航深度文：HM3D / Habitat / MP3D 生态、三大范式、以及 "spatial intelligence vs VLM-in-disguise" 的拷问 | v1 |
| *（待写）* `warehouse_agv_traffic.md` | 多 AGV 协同、交通死锁、动态障碍 | TBD |
| *（待写）* `home_robot_floor_perception.md` | 反光地板、电线、深色家具、楼梯检测 | TBD |
| *（待写）* `slam_for_indoor_agv.md` | "已解决"的栈——Cartographer / RTAB-Map / LIO-SAM 室内调参 | TBD |

---

## 交叉引用

- **Aerial 对照：** `embodiments/aerial/vio/`（延迟预算不同，没有轮式里程计）
- **Driving 对照：** `embodiments/driving/`（GNSS 情况类似，但速度高得多）
- **Encoder 基础：** `foundations/feed-forward-3d/`（为何 VGGT 类先在这里跑通）
- **跨 embodiment：** `crossing/slam-vio-migration/`（地面移动在迁移叙事中的位置）
- **VLA 接缝：** [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)——任何驱动 AGV / 家用机器人的 VLA 智能体放那边。空间这边只管空间。

## 边界

本子树覆盖地面移动的**空间感知、建图与导航表征**。不覆盖：

- 高速自动驾驶（>5 m/s 室外）→ `embodiments/driving/`
- 腿足运动控制 → `embodiments/humanoid-legged/`
- 地面机器人的策略 / VLA 动作头 → [VLA-Handbook](https://github.com/sou350121/VLA-Handbook)
- AGV 车队管理软件细节（仓储物流 SaaS）→ 完全超出范围

*维护者深度档：Major。比 aerial 锚级别低，但比 driving 深。*
