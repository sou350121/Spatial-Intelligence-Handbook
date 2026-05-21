# Event Camera (DVS) Physics for Embodied AI (事件相机物理 — 异步像素 / HDR / 10us 时间分辨率)

> **发布时间**：2026-05-21
> **范围**：`foundations/sensor-physics/` — async pixel principle / HDR / latency / motion-or-nothing
> **核心定位**：那个"无全局帧、无曝光、无快门"的 sensor — 学术宣传不愿明说**静态场景返回零数据**才是承重约束，10 µs 延迟反而是次要的

**Status:** v1 — opinionated draft，按 AGENTS.md 14 项 dissection 模板撰写，2026-05-21。标 `UNVERIFIED` 的数字仍需 spec-sheet 交叉核对。
**Wedge tier:** sensor-physics expansion（5 篇姊妹文中的第 5 篇）

### X-Ray opening

事件相机 (Dynamic Vision Sensors, DVS) 把全局快门曝光换成**逐像素异步阈值触发**：每个像素在自己 log-intensity 变化超过 ±θ 时独立发出一个 event (x, y, polarity, timestamp)。10 µs 时间戳分辨率比 30 Hz 帧快 3000×。120 dB 内禀 HDR 比 60 dB CMOS 多 60 dB。但同样的架构意味着**静态、光照良好的场景返回零比特** — 根本没有"帧"可拍。对 sensor 工程师：事件相机不是"更好的相机" — 它是一种不同的感测形态，在运动 + HDR 上胜出，其他地方都输。

### 📍 研究全景时间线 (Research Landscape Timeline)

```
2008 ── Lichtsteiner DVS128 (ETH Zurich Tobi Delbruck) ── 首个可用异步像素
2014 ── DAVIS (active + DVS hybrid, iniVation) ── 帧与事件同时输出
2017 ── Prophesee (Chronocam) 成立 ── 商业聚焦
2019 ── Prophesee Gen3 VGA ── 640×480，车载关注
2020 ── Sony IMX636 (Sony + Prophesee 合作，1280×720)
2021 ── UZH RPG drone racing (DVS-only quad 导航) ── 高速验证
2023 ── Prophesee EVK4 ── 开发者套件标准
2024 ── Sony IMX661 / hybrid event-frame sensor 出现
202? ── ?  下一波：hybrid event-frame-depth 单芯片 / spiking-NN 协处理器
```

本文件卡在"event vs frame" sensor 形态分岔点 — 整组 sensor 里唯一不产生帧的。

---

## 1 · 异步像素原理

📌 **Napkin Formula**：`event_rate ≈ N_pixels × motion_in_pixels_per_sec × (avg_contrast / θ)`。§2 的所有内容对照这个公式 — DVS 数据量受场景运动而非 pixel 数 × 帧率限制。

**(a) Pixel 电路.** 每个像素含：
1. Photoreceptor（**对数**，非线性 — HDR 的来源）。
2. Change amplifier，把当前 log-intensity 与记忆值比较。
3. 两个阈值比较器（正负方向）。
4. 一个 reset 信号，发出事件后锁存新值。

当 `|log(I_now) - log(I_last_event)| > θ`（通常 10–25% 强度变化）时，像素把 event `(x, y, t, polarity)` 发给芯片级 arbiter。Arbiter 通过 AER (Address-Event Representation) bus 串行输出 events，峰值 100M–1G events/s `UNVERIFIED`。

**(b) Logarithmic photoreceptor → 120 dB HDR.** 常规 CMOS 是线性 photoreceptor + ADC 位深 → ~60 dB。DVS 像素的对数压缩给出内禀 120 dB `UNVERIFIED` — 太阳与阴影同框不饱和，因为不同强度的像素在独立的对数刻度上工作。

**(c) 10 µs timestamping.** 像素异步 + 芯片级 timestamp counter → events 被打上 ~1–10 µs `UNVERIFIED` 时间戳。没有"帧"概念 — 时间分辨率受读出带宽而非曝光时间限制。

**(d) Polarity per event.** 只有变化方向（更亮 / 更暗），无幅度。要恢复强度，需要积分 events 或用 hybrid sensor (DAVIS, Prophesee Gen4 hybrid)。

⚡ **Eureka Moment.** 事件相机**用阈值替代快门**。没有曝光时间这个概念。静态场景 = 零 events。快速运动 = ms 级 per-pixel 响应。这不是"高速" — 是**事件驱动**。CMOS 的 framing 假设直接消失。

---

## 2 · DVS vs frame camera 对比

| Property | Global-shutter CMOS (Sony IMX900) | Event camera (Prophesee EVK4) |
|---|---|---|
| 输出 | 固定 Hz 的 dense frame | sparse events (x, y, t, ±) |
| 时间分辨率 | 1–10 ms (帧周期) | 1–10 µs (per-pixel) `UNVERIFIED` |
| 动态范围 | ~60 dB (linear) | ~120 dB (log) `UNVERIFIED` |
| 静态场景输出 | 每周期一整帧 | ~零（仅噪声 event） |
| 运动模糊 | 有，受曝光限制 | 无（无曝光） |
| 数据量 | 恒定 (W × H × Hz × bits) | 场景相关，可以少 10–1000× 或更多 |
| Sensor 成本 | $5–500 | $200–3000 |
| 分辨率（典型） | 1080p–4K | VGA–HD（今天最高 1280×720 `UNVERIFIED`） |
| 首事件延迟 | ~33 ms (一帧) | ~10 µs `UNVERIFIED` |
| 功率 | 0.1–5 W | 0.01–0.5 W（场景相关） |
| 典型厂商 | Sony, OmniVision | **Prophesee, iniVation, Samsung research** |

预测 DVS 胜出的规则：场景运动 ≫ 静态内容**且**延迟 / HDR 重要。静态监控输给帧；高速避障靠 DVS 胜。

---

## 3 · Prophesee vs iniVation — sensor 谱系

**Prophesee（原 Chronocam）.** 法国创业公司，商业聚焦。和 Sony 合作 → IMX636 (1280×720) 与 IMX669 (HD hybrid event+frame)。更高分辨率、车规雄心、EVK4 开发套件。SDK + OpenEB stack 成熟。Cost tier：sensor + 镜头 $1k–3k `UNVERIFIED`。

**iniVation（Tobi Delbruck 的 ETH spin-out）.** 研究聚焦，DAVIS sensor (240×180 DVS + APS frame)。分辨率更小，APS hybrid 更精细（同一阵列**同时**输出 events 与传统帧）。Cost tier：研究套件 $3k+ `UNVERIFIED`。

**Samsung / 学术原型.** 更大阵列 (640×480 到 1.28 MP)，研究合作之外不商业可得。

Drone 工作 → Prophesee Gen3/Gen4 sensor。要对比常规图像做 perception 研究 → DAVIS。Long-tail 边缘部署（成本敏感）— 等 IMX636 跌进 $200 车载供应 tier（2026 还没到）。

---

## 4 · Worked example — DVS 在 6 m/s 飞行下：信号率 vs 全局快门

Back-of-envelope（数字 `UNVERIFIED`，仅用于工程直觉）：

```
Drone:       6 m/s 前向，穿过门赛道
Camera:      640×480 DVS, HFOV 90°, focal_length ~ 320 px
Scene:       前方 3 m 有纹理墙
```

- **Sensor 上视运动.** 3 m 距离，6 m/s 侧向 parallax → 角速度 ~2 rad/s → 跨 sensor ~640 px/s。
- **每像素 event 率.** 跨像素 ~640 px/s 运动，典型场景对比超过阈值 → 有纹理区 ~200 events/s/px；平整区 ~0。设 ~10% 像素 active → `0.10 × 640×480 × 200 = 6.1M events/s`。每 event ~64 bits → ~50 MB/s。USB-3 吃得下。
- **同一轨迹，30 fps 全局快门帧相机.** 640 px/s × 33 ms 曝光 → 每帧 21 px 运动模糊。Feature matching 彻底退化。要 1 ms 曝光 → 1/1000 光通量 → SNR 崩塌，否则就要 HDR 照明。
- **100 fps 配亚毫秒曝光** 帧相机时间项追平，但 99% 带宽花在静态背景且功耗 10×。

DVS **不是靠分辨率取胜**（VGA vs 4K）。它赢在**首事件延迟**（避障）与**无运动模糊**（高速跟踪）。50 MB/s 全花在场景**变化**的部分 — 也就是控制真正关心的部分。

印证 §1 → §2：DVS 在 drone racing 大放异彩（每个光子都是信号），在 cinematography 上溺水（静态帧才是产品）。

---

## 5 · DVS 在哪里活、在哪里死

**活的地方.**
- **高速避障** — UZH RPG drone racing demos。
- **HDR 感知** — 出隧道、焊接火花机器人、阳光-阴影切换。
- **低功耗 always-on** — drone / 可穿戴里静态场景零 events 让功率 <100 mW。
- **只看运动的任务** — 手势、振动分析、粒子跟踪、眼跳追踪。
- **Spiking-NN 前端** — neuromorphic chip (Loihi, Akida) 天然消费 events。

**死的地方.**
- **静态场景采集** — 空停车场的安防相机什么都不返回；闯入者触发一阵 burst，但你没有"之前"。
- **色彩 / 纹理** — DVS 是单色，只给极性。Hybrid DAVIS / IMX636 用 APS 通路缓解。
- **低光无纹理** — 变化 events 低于阈值或场景没有空间对比时，DVS 失明。没有"长曝光"救援。
- **下游计算不熟悉.** 大部分 CV pipeline 假设帧。把 events 当人造帧（每 N µs binning 成 tensor）会丢掉 DVS 大部分优势。

---

## 6 · Hidden Assumptions — DVS 默默押注的前提

DVS 选择只在下列条件成立时稳定：

- **场景含运动 OR 光照变化.** 完美静态、完美均匀照明 → 零 events，DVS 对它**失明**。缓解：配 frame APS (DAVIS) 或靠 ego-motion 产生变化。
- **场景有空间对比.** 无纹理 → 无边缘 → 运动也不会跨过 log-intensity 阈值 → 仍零 events。白墙 + 完美光 = 不可见。
- **阈值 θ 与场景照明匹配.** 太紧 = 噪声淹没；太松 = 重要变化漏掉。Per-pixel 阈值随温度漂复杂化。
- **AER bus 不饱和.** 频闪、快速运动纹理场景可产生 >100M events/s 饱和读出 — events 掉、时间戳偏。难调试因为**症状是缺数据**。
- **算法天然消费 events.** 把 DVS bin 成 frame tensor → 重新引入 DVS 移除的 framing 假设 → 浪费延迟优势。只有 event-native 算法（event-based VIO、spiking NN）能榨干全部优势。
- **与其他 sensor 的同步.** AER 时间戳是 sensor 时钟；与 IMU / 帧相机对齐需要硬件 sync 或事后配准。容易做错。
- **分辨率足够任务.** VGA–HD vs 帧相机 4K — DVS 在像素数上输 8×。细粒度分类需要 APS 帧。

---

## 7 · 跨 embodiment 比较 + interview tip

| Embodiment | DVS 合适？ | 原因 |
|---|---|---|
| **Drone racing** | **是 — 主用例** | 高速 + 低延迟 + HDR (UZH RPG demos) |
| **Drone cinematography** | **否** | 静态或慢场景；观众要帧；4K 重要 |
| **Manipulation** | 研究级 | 多为静态；如有快速扰动可受益 |
| **Humanoid** | 研究 | 头部 + 眼跳追踪有趣；whole-body 还没 |
| **AD 主感知** | **否** | 分辨率 + 色彩 + 分类 — 帧相机胜 |
| **AD (HDR 切换)** | **或可作辅** | 出隧道 / 对向远光；辅助帧 |
| **Marine** | 罕用 | 静态浑浊水缺变化信号 |
| **AR / VR eye tracking** | 是 | 眼跳追踪 10 µs 延迟 + 低功耗 |

经验：DVS 凭**运动 + 延迟 + HDR** 拿到 slot。Cinematography / 分类 / 静态场景仍是 global-shutter CMOS 地盘。

**🎙️ Interview Tip.** 被问"我们 drone 该用事件相机吗"？— 分**racing / 避障**（DVS 可作主） vs **cinematography / 建图**（DVS 顶多辅）。Drone-racing 延迟基准引 UZH RPG 论文。Hollywood drone，DVS 是错的工具 — 帧才是产品。

---

## 8 · For the reader

- **Manipulation engineer** — global-shutter CMOS (RGBD) 仍是主；DVS 在快速运动目标或频闪环境有趣。
- **Aerial engineer (racing)** — **是** — Prophesee EVK4 或 IMX636 平台；延迟 + HDR + 功耗特性正好契合 drone racing。
- **Aerial engineer (cinematography)** — **否** — 观众要 4K 帧；DVS 给不了 global-shutter 给不了的东西。
- **AD engineer** — 仅作 HDR 切换辅助；主感知仍走帧。
- **Marine engineer** — 跳过；声学栈主导。

---

## References

- Lichtsteiner et al. "A 128×128 120 dB 15 µs Latency Asynchronous Temporal Contrast Vision Sensor" IEEE JSSC 2008
- Prophesee EVK4 / IMX636 datasheets `UNVERIFIED`
- iniVation DAVIS346 spec sheet `UNVERIFIED, no DOI`
- UZH Robotics & Perception Group — 事件相机 drone racing (Mueggler, Gehrig, Scaramuzza)
- Gallego et al. "Event-based Vision: A Survey" PAMI 2020
- IEC 60825-1（激光安全 — 对无源 DVS 不相关，列在此处作主动姊妹文交叉引用）

## Boundary

- `foundations/sensor-physics/active_nir_850nm_for_embodied_ai.md` — 主动 NIR（passive DVS 是光谱反端）
- `foundations/sensor-physics/tof_physics_for_embodied_ai.md` — 深度姊妹文（event-based ToF 是研究方向，非商用）
- `foundations/sensor-physics/lidar_physics_905_vs_1550.md` — 长距脉冲姊妹文
- `foundations/sensor-physics/imu_physics_and_noise_model.md` — IMU 姊妹文（DVS+IMU 是标准融合栈）
- `crossing/sensor-stack-matrix/sensor_budget_matrix_v1.md` — 跨 embodiment SWaP-C：DVS 何时拿到 slot（drone racing 主用例）
- `embodiments/aerial/event-camera/` — per-embodiment 部署，drone racing case study
- Event-based VIO / SLAM 算法：`foundations/slam-vio/` (TBD) — 算法消费物理；本文只是物理。

*2026-05-21. v1 首版，满足 14 项 gate。UNVERIFIED → v1.1 datasheet 引用。*

---
[← Back to sensor-physics README](./README.md)
