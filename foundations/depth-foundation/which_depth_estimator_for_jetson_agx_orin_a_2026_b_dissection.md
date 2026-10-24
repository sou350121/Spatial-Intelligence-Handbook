[//]: # "<!-- ontology-5axis
problem: depth
representation: n/a
sensor: stereo
paradigm: learned
time: feed-forward
ref: ../../cheat-sheet/ontology.md §5
-->"

# 哪个深度估计器适合 Jetson AGX Orin？2026 单目与双目方法基准评测 (Which Depth Estimator for Jetson AGX Orin? A 2026 Benchmark of Monocular and Stereo Methods)

> **发布时间**：2026-10-19（arXiv:2610.27199v1, cs.RO）
> **论文 / 模型名**：Orin-depth-benchmark（作者 Leaf Jiang, NODAR Inc.；非新模型，而是九个模型族的实测基准）
> **核心定位**：一句话——在**同一块 Jetson AGX Orin 64GB** 上，把 2026 年 10 月的 6 个单目 + 3 个双目深度族跑到 TensorRT FP16/native CUDA，用**同一份 Middlebury 2014 全分辨率真值**统一评 metric 精度 / GPU 时间 / 能耗 / licence，结论是**任何算力预算下双目都压倒单目**。
> **Ontology 轴**：problem=depth / representation=n/a（纯 depth/disparity 输出）/ sensor=stereo（含 mono 对照）/ paradigm=learned（含经典 SGM）/ time=feed-forward

导语：嵌入式深度估计的选型长期靠"论文报桌面 GPU、训练分辨率、还做了 GT 对齐"的数字互相比较，工程上无法落地。本文的结论很尖锐：**立体把新增像素换成精度，单目换不来**——双目误差随分辨率单调下降，单目不仅不降，metric scale 还随分辨率漂移。

---

## X-Ray 开场

如果你要在机器人/车上选一个深度估计器，本文给出的答案是：**先问有没有第二台相机**。有，就用 NVIDIA ESS（30 fps 下 0.70% AbsRel / 8.6 ms）或经典 libSGM（半分辨率 0.73% / 25 ms，Apache-2.0 可改）；没有，最好的 metric 单目也只有 **12%**（Depth Anything 3 Metric-L 33 ms、Depth Pro 803 ms），而且**只有在额外提供一个 oracle 尺度后**才降到 3.8–4.0%——仍然比最差的立体配置差一个数量级。

对 spatial AI 研究者最值得带走的一句话：**分辨率对双目是信息，对单目只是细节**。双目 triangu-lation 的像素误差可换成米；单目的 metric scale 来自训练分布里"物体多大、相机多高"的先验，更多像素不增加该先验的信息量，跑出训练分辨率后先验本身还会偏移（Depth Anything V2 在 native 把场景放近 1.45×，全分辨率放近 2.44×）。

---

## 📍 研究全景时间线

```
单目 relative/mono-metric ────────────────────────────────────────────────
 ≈2019 MiDaS ─► ≈2022 DPT ─► 2024 Depth Anything V1/V2(+Hypersim/VK 尺度微调)
                              └► 2024 Depth Pro(1536², 自带 focal 估计)
                              └► 2025 MoGe-2 / Metric3D v2 / UniDepth V2(带相机模型)
                              └► 2025–26 Depth Anything 3(任意视角、DINOv2 直出)
                                                                        │
双目 classical/learned ──────────────────────────────────────────────────┤
 ≈2008 SGM ─► libSGM(CUDA, 4-path, Apache-2.0)                           │
 ≈2021 RAFT-Stereo ─► 2025 FoundationStereo ─► Fast-FoundationStereo(蒸馏)│
 ≈2024–26 NVIDIA ESS / Light ESS(Isaac ROS, Jetson 专用)                  │
                                                                        ▼
                                        ★ 2026-10 本文：统一 Orin + 统一 GT 的横评
                                          局限：室内近距(1.3–7.6 m)、10 个场景、
                                                无 LiDAR 远距、未测 Orin OFA/VPI SGM
```

本文的位置：它不是方法创新，而是把"上游模型族"和"嵌入式部署"两条线**第一次放在同一硬件 + 同一真值 + 同一遮挡掩膜**下对齐，并额外给出**分辨率 scaling 曲线**和**边缘 flying-point 分析**这两个论文里通常不报的维度。

---

## 1 · 核心架构 / 方法总览

### 1.1 系统 / 组件对比表

评测框架层面：所有方法接收**同分辨率（≈5.7 MP）左右图**，输出上采样到全分辨率后与**同一份非遮挡真值**比较；装不下的方法跑其最大可支持输入。

| 模块（族） | 处理分辨率（实测） | 输出 | 训练/推理差异 | 限制因素（原文） | Licence（作者声明） |
|---|---|---|---|---|---|
| **libSGM** (Fixstars 3.1.0) | full ≈1990×2880；half ≈995×1440；quarter ≈497×720 | 稀疏 disparity（LR-check 留洞） | 经典算法，无训练；P1/P2 每分辨率单独调 | 256 disparity levels @处理分辨率 | Apache-2.0 |
| **ESS / Light ESS** (Isaac ROS, NGC 4.1.0) | 固定 576×960 / 288×480 | dense disparity | 只有 TensorRT engine 一种发布形式 | 固定网络输入 | NVIDIA TAO model EULA（允许商用） |
| **Fast-FoundationStereo** (23-36-37 8-iter；20-30-48 4-iter) | 768×1152；512×768；384×576 | dense disparity | ONNX 单脚本导出；0.27×width 视差上限 | 960×1440 无 TRT cost-volume pooling 实现；1280×1920 ONNX 导出耗尽 host 内存 | NVIDIA Source Code License（非商用） |
| **C-Fast-FoundationStereo** | 同上三档 | dense | 架构同 23-36-37，独立训练权重 | 同上 | NVIDIA Open Model Agreement |
| **Depth Pro** | 固定 1536×1536 | metric depth + focal | 需 focal；文中给真 focal 与自估 focal 两版 | 固定网络输入 | Apple licence |
| **Depth Anything V2 (metric, Hypersim)** S/B/L | full 1988×2884；native 518×770；S/L 另加 1008×1512 | metric depth（metric head 限 20 m） | 全分辨率导出需 memory-efficient attention；engine 构建 27–79 min | 训练于 518 px；**S 的 FP16 engine 全分辨率数值不可靠** | S: Apache-2.0；B/L: CC BY-NC 4.0 |
| **Depth Anything 3 Metric-L** (0.35 B, ViT-L) | native 350×504；700×1008；full 1988×2884 | depth 相对 focal（×f/300 转 metric） | 需真 focal | 训练于 504 px | Apache-2.0 |
| **MoGe-2** S/B/L | native ≈700×1008（3600 tokens）；1400×2030；full（≈29,000 tokens） | affine-invariant point map + class-token metric scale | 需 focal；文中给真 focal / 自估两版；未用 validity mask | token 数是输入参数 | MIT |
| **Metric3D v2** ViT-S/L | native 616×1064；1232×2128；full | canonical-camera depth，用真 focal 重标定 | 全分辨率 attention 按 query block 分块 | 输入尺寸是预处理参数 | BSD-2-Clause |
| **UniDepth V2** S/B/L | native 644×938；1302×1890；full | depth + camera ray | 给真 intrinsics；ONNX 以 rays 作相机输入 | pixel budget 是参数 | CC BY-NC 4.0 |
| **评测流水线** | — | AbsRel / δ&lt;1.05 / bad-t / 密度 / 边缘指标 | — | — | 代码与 engine 构建脚本随论文发布 |

### 1.2 关键机制

**⚡ Eureka Moment：双目把"更多像素"变成"更小的米级误差"（σ_Z ≈ Z²/(fB)·σ_d，f 随分辨率涨），而单目的 metric scale 来自与像素数无关的尺寸/相机先验——所以分辨率越高，两者差距越大，而不是越小。**

这条洞见把三个原本分散的现象统一了：

1. **scaling 方向相反**：立体 1.18% → 0.73% → 0.63%（libSGM quarter→half→full），单目 12.3% → 14.2% → 54.9%（DA3 native→2×→full）；
2. **oracle scale 也救不回 shape**：去掉全局尺度后 DA3 仍从 6.0% 升到 6.2%，说明剩余误差是**倾斜/翘曲/全局结构**，不是缺细节——"更高分辨率只是让单目深度图更锐，没让它更准"；
3. **AbsRel 看不见边界**：flying points 只占 1.7% 的像素，MoGe-2-L 边缘 46.1% flying 却只把总 AbsRel 抬高 &lt;0.1 pp。

### 1.3 信息流 / 评测架构

```
Middlebury 2014, 完美校正, ≈2.9k×2.0k（10 个 disparity ≤256 px 的场景）
        │
        ├─ 左右灰度 ─► libSGM (9×7 census → 4-path SGM → uniqueness → 抛物线亚像素 → 3×3 中值 → LR check) ─┐
        ├─ 左右 RGB  ─► TensorRT FP16: ESS / Light ESS / FFS(±C) ───────────────────────────────────────┤
        └─ 左 RGB    ─► TensorRT FP16(精度来自 FP32): mono nets ─► Z ─► d = fB/Z − d_offs ──────────────┤
                                                                                                     ▼
                                                  disparity d（各法各自分辨率）
                                                                                                     │
                    dense 双线性 / libSGM 最近邻上采样 + 按宽度比缩放视差 ◄─────────────────────────────┘
                                                                                                     │
        非遮挡真值 mask（保留 91%：右视图内 + 右视图 GT 视差 1 px 内一致）◄───────────────────────────┘
                                                                                                     │
                        ┌──────────────────────────────┬──────────────────────────────┐
                        ▼                              ▼                              ▼
              bad-t（缺失计为错）            AbsRel / δ<1.05            边缘子集：17×17 邻域深度比 ≥1.2
              （缺失中立，利于稀疏立体）      （对 flying point 几乎不敏感）           （flying / density / 边缘 AbsRel）
```

注意两个"故意偏向网络"的设定，读数字时必须扣掉：网络计时**不含** resize/归一化/后处理（MoGe-2 的 focal+shift+metric-scale head 也不含），而 libSGM 计时**含**图像上传与视差下载。

---

## 2 · 数学核心

📌 **Napkin Formula**：

$$\text{AbsRel} \approx \underbrace{\frac{|Z_\text{pred}-Z|}{Z}}_{\text{尺度项：单目主要误差}} + \underbrace{\frac{Z}{fB}\,\sigma_d}_{\text{三角化项：双目主要误差}},\qquad Z=\frac{fB}{d+d_\text{offs}}$$

一句话：**左项靠先验，不随 f 变；右项的分母带 f，随分辨率变。**

**目标**：在固定算力预算下比较两类方法的 metric 误差。**推导（视差误差 → 深度误差）**：对 $Z=fB/(d+d_\text{offs})$ 微分得

$$\left|\frac{\partial Z}{\partial d}\right|=\frac{fB}{(d+d_\text{offs})^2}=\frac{Z^2}{fB}\;\Rightarrow\;\frac{\sigma_Z}{Z}=\frac{Z}{fB}\sigma_d$$

**变量说明**：$f$ 为处理分辨率下的 focal（px），$B$ 基线（m），$d$ 视差（px），$d_\text{offs}$ 零视差偏置，$\sigma_d$ 为像素级匹配误差。**直觉**：图像边长翻倍使 $f$ 翻倍、$\sigma_Z/Z$ 减半——这就是论文说的"ideal of the triangulation argument, which halves the error with every doubling of the image side at a constant matching error in pixels"。实测收益更小，因为**固定尺寸匹配窗口在高分辨率下覆盖更少的场景，$\sigma_d$ 本身会涨**（libSGM 最后一个 step 只拿到 14%）。

单目侧则没有这样的项：网络输出 $Z_\text{pred}=s\cdot Z$，$s$ 由训练分布的后验决定，$f$ 不在公式里；论文因此把误差拆成

$$\underbrace{\text{AbsRel}_\text{raw}}_{\text{尺度偏差主导}}\;\xrightarrow{\;\times\,\text{median}(Z/Z_\text{pred})\;}\;\underbrace{\text{AbsRel}_\text{oracle}}_{\text{结构误差：倾斜/翘曲/错位}}$$

oracle scaling 是**每图一个全局标量的上界**，任何"从已知物体尺寸 / 测距 / 里程计恢复尺度"的方案都不可能超过它。

---

## 3 · 带数字走一遍（玩具设定，数字为示范，非论文实测）

设定：$B=0.2$ m，$f=4000$ px ⇒ $fB=800$ px·m；目标点 $Z=4$ m ⇒ $d=200$ px（符合论文"disparity ≤256 px"的选场景约束）。

**(a) 双目的分辨率红利**
- $\sigma_d=1$ px ⇒ $\sigma_Z=Z^2/(fB)\cdot\sigma_d=16/800=0.02$ m ⇒ $\text{AbsRel}=0.5\%$。
- 分辨率×2（$f\to8000$）：同 $\sigma_d=1$ px ⇒ $\sigma_Z=0.01$ m ⇒ **0.25%**。
- 也就是"边长翻倍→误差减半"。论文实测 libSGM 是 1.18%（0.36 MP）→0.73%（half）→0.63%（full），**收益打折**，因为 $\sigma_d$ 随分辨率上升。

**(b) 单目的尺度偏差如何直接变成 AbsRel**
- Depth Anything V2-S 在 native 的 `Scale GT/pred = 1.45`，即预测把场景放近了 1.45 倍：$\text{AbsRel}=1-1/1.45=31\%$，与表 3 实测 **29.9%** 同量级 ⇒ **它的原始误差几乎全部是全局尺度**。
- 全分辨率 `Scale = 2.44` ⇒ $1-1/2.44=59\%$，实测 **56.0%** ⇒ 尺度漂移放大了误差，而不是像素不够。
- 乘上 median 比例做 oracle：V2-S 从 29.9% → **8.9%**，剩下的是结构误差。

**(c) 零视差距离如何吃掉密度**
- 若 $d_\text{offs}$ 使零视差距离为 $fB/d_\text{offs}$，则预测深度超过该距离的像素**直接计为 missing**。
- Metric3D v2 在 full 分辨率把 86–95% 的像素放到零视差之外 ⇒ 表 3 的 `Density` 只剩 **5–8%**，AbsRel 冲到 **136.8–162.5%**。这就是"跑出训练分辨率会把 metric scale 甩出去"的具体形态。

---

## 4 · 工程视角

所有数字均来自原文（Jetson AGX Orin 64GB，JetPack 6.2 / L4T R36.4.3，CUDA 12.6，TensorRT 10.3，MAXN，FP16 engine）。

| 配置 | GPU 时间 / 帧 | 动态能耗 / 帧 | 占单 Orin @30 fps | AbsRel |
|---|---|---|---|---|
| Light ESS 288×480 | **2.8 ms** | 0.08 J | 0.08 | 1.16% |
| libSGM quarter ≈497×720 | **6.1 ms** | 0.18 J | 0.18 | 1.18%（88% 密度） |
| ESS 576×960 | **8.6 ms** | 0.31 J | 0.26 | 0.70% |
| libSGM half ≈995×1440 | **25 ms** | 0.73 J | 0.75 | 0.73%（85% 密度） |
| FFS 20-30-48 @384×576 | **68 ms** | 1.9–22.4 J（全 FFS 区间） | 2.03 | 0.64% |
| FFS 23-36-37 @384×576 | **116 ms** | 同上 | 3.47 | 0.52%（C-FFS 同） |
| libSGM full ≈1990×2880 | **101 ms** | 3.0 J | 3.02 | 0.63%（76% 密度） |
| FFS 23-36-37 @768×1152 | **758 ms**（4-iter 445 ms） | 同上 | 22.74 | 0.33% |
| Depth Anything 3 Metric-L 350×504 | **33 ms** | 0.5–12 J（mono native 区间） | 1.00 | 12.34% |
| Depth Anything V2-S native 518×770 | **11.5 ms**（表 2 记 12 ms） | 同上 | 0.35 | 29.88% |
| MoGe-2-L 700×1008 | **212 ms** | 同上 | 6.35 | 19.2%（oracle 3.78%） |
| Depth Pro 1536×1536 | **803 ms** | 32–235 J（mono full/fixed 区间） | 24.08 | 11.98% |
| 单目全/固定分辨率区间 | **0.76–5.3 s** | 32–235 J | 22.8–158.93 | — |

关键 trade-off：

- **端到端时间跨度 >3 个数量级**（2.8 ms – 5.3 s）。若 30 fps 是硬约束，可用集合就是 Light ESS / libSGM(quarter,half) / ESS 三家——**全是立体**。libSGM quarter 只占 18% GPU，剩下的算力可以留给别的任务。
- **单目没有一个比 Light ESS 快**：最快的 Depth Anything V2-S 也要 4.1× Light ESS 的 GPU 时间，DA3 要 12×，全/固定分辨率的单目要 272–1,890×。
- **FP16 不是免费的**：Depth Anything V2-S 全分辨率 FP16 与 FP32 差 **17.5%**，Depth Pro 差 1.9%（FOV 估计偏 1.6°）；Depth Anything 3 与 MoGe-2 的 TRT 10.3 fused kernel 有两个坑（见 §8）。论文对这些模型**精度报 FP32、速度报 FP16**——这是对它们有利的报法。
- **engine 构建成本**：Depth Anything V2 全分辨率 TensorRT engine 构建需 **27–79 min** 且吃掉 Orin 64 GB 的大部分；FFS 在 960×1440 **无 cost-volume pooling 的 TRT 实现**，1280×1920 ONNX 导出**耗尽 host 内存**。
- **per-frame 显存占用**：**论文未报告**（只给了上述"engine 用掉 64 GB 大部分"和"装不下"的定性边界）。
- **成本模型**（原文 eq. 1）：跑 $F$ fps 占用 $u=t_\text{GPU}F/1000$ 个 Orin，按模块价 $P_\text{SoC}=\$2&#123;,&#125;999$（1k 量）折算，第二台相机划算当且仅当
 $$P^*_\text{cam}=(t_m-t_s)\frac{F}{1000}P_\text{SoC}.$$
 结论：30 fps 下 Light ESS 相对各单目的 break-even 相机价从 **\$786（DA V2-S native）到 \$23,618（Metric3D v2-L native）**，全分辨率高达 **\$68,266–\$476,366**；对照 \$20–\$500 的相机价格区间，**加第二台相机永远更便宜**。唯一例外是 10 fps 下 DA V2-S native 的 **\$262** 阈值落进了价格区间内。

---

## 5 · 数据与评测

**数据集**：Middlebury 2014，perfect rectification，全分辨率 ≈2.9k×2.0k。公开真值共 **23 个场景**，本文只用其中 **10 个**——条件是"非遮挡真值 disparity 全程 &lt; 256 px（最大 243 px）"，以保证 256-level 的 SGM 在**所有测试分辨率下都不被搜索范围卡住**。其余 13 个场景近物视差达 265–712 px。

**非遮挡真值**：Middlebury 真值来自结构光而非立体匹配，因此覆盖右相机看不见的像素——平均 **5.8%** 的真值像素在右视图被遮挡、**2.7%** 落在右视图 FOV 外。按 MiddEval3 约定，只在**非遮挡真值（91%）**上评分：匹配点落在右图内且右视图 GT 视差在 1 px 内一致。单目方法用**同一批像素**评分。

**场景属性**（影响结论外推）：室内、近距离 **1.3–7.6 m**，基线 **17–24 cm**，focal **2,800–7,200 px** ⇒ 视差大、三角化极准。

**指标**：
- 视差：bad-t = 误差 >t px 的非遮挡像素占比，**缺失计为错**；
- 深度：AbsRel、δ&lt;1.05（5% 以内像素比例），在**已预测像素**上算 ⇒ 缺失是中立的（对稀疏立体有利）；
- libSGM 因 LR-check 留洞，raw（密度 + 已预测像素误差）与 MiddEval3 背景填洞后**两版都报**；
- 单目额外报 **oracle-scaled**（每图乘 median(GT/pred)），作为任何尺度恢复方案的上界；
- 明确**只测 accuracy 不测 precision**，理由是"网络可以输出一张完美平滑、但倾斜偏几度的地板"——precision 指标会给这种幻觉打高分。

**协议**：降采样输出上采样回全分辨率（dense 用双线性，libSGM 用最近邻以保住洞），视差按宽度比缩放；$Z=fB/(d+d_\text{offs})$，单目深度同式转视差，超过零视差距离的像素计为 missing。

**计时/能耗**：网络用 `trtexec` 的 median GPU compute time（spin-wait，3 s 预热，≥20 s 运行）；libSGM 用 Nsight Systems trace 的 per-frame GPU busy 时间（kernel+copy 区间并集，含双图上传与视差下载）；功耗用 `tegrastats`（VDD_GPU_SOC + VDD_CPU_CV），动态能耗 $=(P_\text{load}-P_\text{idle})/\text{throughput}$；负载下 GPU+SoC 与 CPU 轨合计 **34–57 W**。

**未评测**（原文自述 coverage）：Orin 的 OFA/VPI 上的 SGM 风格视差、FoundationStereo 本体、RAFT-Stereo 等其他学习立体、PatchFusion/PatchRefiner 之类 tile-based 高分辨率单目。**未在 Middlebury 上 fine-tune 任何模型**，也无法排除 Middlebury 出现在某模型训练集里。

**关键数字（逐字）**：ESS 0.70%@8.6 ms；libSGM 0.73%@25 ms（half）/1.18%@6.1 ms（quarter）/0.63%@101 ms（full, 76% 密度）；FFS 0.33%@758 ms（8-iter, 768×1152）；C-FFS 0.33%@760 ms；DA3 12.34%@33 ms；Depth Pro 11.98%@803 ms（自估 focal 19.0%）；MoGe-2-L oracle 3.78%；UniDepth V2-B oracle 3.90%；Metric3D v2-L oracle 4.0%；bad-2：ESS 20%、Light ESS 37%、FFS 7–17%。

---

## 6 · 能力与失败模式

**能做（按任务选型）**

| 需求 | 结论 |
|---|---|
| 30 fps + 双相机 | ESS（0.70%, 8.6 ms, dense）；算力最紧时 Light ESS（1.16%, 2.8 ms）或 libSGM quarter（1.18%, 6.1 ms, 88% 密度, Apache-2.0 可改） |
| 10 fps | FFS 4-iter @384×576（0.64%, 68 ms, 非商用）；商用选 C-FFS（384×576: 0.52%, 116 ms） |
| 精度优先（>100 ms 预算） | C-FFS @768×1152：0.33%, 760 ms，商用许可 |
| 只有单相机 + 已知 focal | DA3 Metric-L（12.34%, 33 ms, Apache-2.0）或 Depth Pro（11.98%, 803 ms） |
| 只有单相机 + 尺度可从别处拿 | MoGe-2-L（3.78% oracle, 212 ms, MIT）、UniDepth V2-B（3.90%, 85 ms, 非商用）、Metric3D v2-L（4.0%, 265 ms, BSD-2-Clause） |
| 物体边界要干净 | **libSGM full**：flying points 1.1%（全方法最低），代价是只返回 45% 的边缘像素 |

**不能做 / 会崩**

- **单目不要指望靠提高分辨率提升精度**：DA3 12.3%→14.2%→54.9%；Metric3D v2 从 57–60% 崩到 128–162%（86–95% 像素掉到零视差之外）；MoGe-2-L 19.2%→23.4%→24.4%；UniDepth V2 唯一略有好转的是 Small（24.7%→22.6%），Large 反而 20.5%→28.1%。
- **单目在边界会"抹平"**：17–46% 的边缘点是 flying points（MoGe-2-L 46.1% 最差），而 AbsRel 几乎不罚——因为边缘只占 1.7% 像素。
- **稀疏立体 + 缺失中立指标 = 系统性偏袒**：libSGM full 的 0.63% 是在 76% 像素上算的；填洞后升到 1.92%（half 1.79%，quarter 2.13%）。即便如此，**填洞后最差的立体（2.13%）仍优于最好的 oracle 单目（3.78%）**。
- **ESS/Light ESS 的像素级精度低**：bad-2 分别 20% / 37%（FFS 7–17%），因为它们输入分辨率下 1 px 误差等于全分辨率 3 或 6 px。
- **"精度优先"要付二次方代价**：FFS 从 384×576 到 768×1152 每档 GPU 时间 ×2–3，AbsRel 只降约 0.1 pp。

### 隐含假设 (Hidden Assumptions)

1. **标定完美**：rectification 是 "perfect"，$f$ 与 $B$ 直接当已知量。真实产品里的在线标定漂移、同步误差、卷帘快门全部未建模——而 $Z=fB/d$ 对 $f,B$ 是一阶敏感。
2. **静止单帧场景**：所有方法 per-frame 独立推理，无时域滤波、无运动模糊/动态物体建模。
3. **视差落窗内**：10 个场景被特意挑成 disparity ≤256 px，作者自己承认"这也剔掉了立体最准的最近距离场景"，13 个近距场景（265–712 px）被排除以免把"搜索范围配置问题"算成精度罚分。
4. **短距有益于立体**：立体误差随距离平方增长，本文 1.3–7.6 m 是立体最优区间；换成长距 + 短基线，差距会缩小（作者把"远距户外 + LiDAR 真值"列为最重要的后续工作）。
5. **FP16 ≈ FP32**：除了明确列出偏差的（DA V2-S 17.5%、Depth Pro 1.9%、Metric3D v2 1.3–3.3%），其余默认等价；而 DA V2-S 的计时"may not represent a correct engine"。
6. **AbsRel 的排序能代表下游**：指标对 flying point 不敏感、对缺失中立，两者都不改变本文的立体 vs 单目结论，但会改变**方法内部**的排序（边界任务下 libSGM full 反超）。
7. **licence 只按作者声明转述**，非法律意见；C-FFS 的 model card 同时写着"面向研究与评估"。
8. **作者利益相关**：作者受雇于 NODAR（做 stereo 产品），因此**刻意不评测自家 Hammerhead** 以保公平——但方向性结论（立体赢）与作者商业利益一致，读者应自行加权。

---

## 7 · 与相关工作对比

| 对比对象 | 它们报的是什么 | 本文的差异 / 结论 |
|---|---|---|
| 各模型原论文（DA V2/V3、Depth Pro、MoGe-2、Metric3D v2、UniDepth V2） | 桌面 GPU、**训练分辨率**、常常**对齐到 GT 后**再算误差 | 统一 Orin + 统一全分辨率真值 + **不做 GT 对齐**（只额外给 oracle 作为上界）；一换到训练分辨率之外，多数单目的 metric scale 就漂 |
| 经典嵌入式立体（SGM / libSGM） | 通常是 KITTI 类驾驶场景的中远距 | 本文是室内近距高视差，SGM 在**边缘**反而最干净（1.1% flying），但密度只有 45% |
| Pseudo-LiDAR 一系（"representation matters"） | 证明立体表示优于单目用于 3D 检测 | 本文把这条结论推进到**foundation-model 时代**并量化到 metric AbsRel：最差立体 &lt; 最好 oracle 单目 |
| NVIDIA Isaac ROS / TAO 生态（ESS、Light ESS） | 模型卡上的优化目标 | 首次给出 ESS 在 Middlebury 的 **0.70% / 8.6 ms** 与 Light ESS **1.16% / 2.8 ms**，即"每单位算力精度最高"的实测 |
| tile-based 高分辨率单目（PatchFusion / PatchRefiner） | 用重叠 crop + 全局估计融合来提升高分辨率细节 | 本文**未评测**，但预判：它们从低分辨率全局估计**继承 metric scale**，因此只会"锐化边缘"，不会消除尺度误差 |
| Orin 自带 OFA/VPI SGM | 专用硬件立体 | **未评测**（明确列为 coverage 限制） |

**面试 Tip（被问到"单目 foundation model 能不能替代立体"时怎么答）**：不要说"单目更通用"或"立体更准"这种立场话，直接给机制 + 数字——**"单目的 metric scale 是训练分布的先验，像素数不进这个先验；所以论文里 DA3 在 native 12.3%，跑到全分辨率变 54.9%，而 libSGM 从 1.18% 降到 0.63%。在 Orin 上 30 fps 的预算里，ESS 8.6 ms 拿 0.70%、libSGM quarter 6.1 ms 拿 1.18%，最快的单目 Depth Anything V2-S 11.5 ms 却只有 29.9%。唯一给单目翻案的场景是：只有一台相机，且你能从已知物体尺寸/测距/里程计拿到尺度——那时 MoGe-2-L 的 oracle 3.78% 是全单目最好的 shape，但仍然比填洞后最差的立体差。"** 补一句边界：**"不过如果任务关心物体边界而不是平均误差，libSGM 全分辨率的 1.1% flying points 是全方法最低，这时候 AbsRel 排行榜会骗你。"**

---

## 8 · GitHub-validated pitfalls (atlas 联动, 2026-10-24)

**Repo 信号核验**：论文 Contributions 段落以纯文本给出 `https://github.com/nodarhub/orin-depth-benchmark`（声明发布 code、per-scene results、engine build scripts 与论文源码）。但在本次可核验的 arXiv HTML 渲染中该地址为**纯文本、非可点击超链接**，且无任何 issue 编号 / commit / 日期可核验。按 atlas 规则，**视为无有效 repo 信号**：以下 4 条 pitfall **由 §6 失败模式 + 方法约束推导，未经 issue 流验证**，不引用任何 issue #、commit hash 或维护者回复。

| # | Pitfall | 从哪条失败模式 + 哪个方法约束推导 |
|---|---|---|
| 1 | **FFS 在 1440p 以上原生分辨率装不进 Orin**：960×1440 时 TensorRT **找不到 cost-volume pooling 的实现**，1280×1920 时 **ONNX 导出耗尽 host 内存**，最大可跑 768×1152 | §6「精度优先要付二次方代价」+ 表 1 的 `Limiting factor` 列；若要保原生分辨率，必须自己写 TRT plugin 或降采样（降采样同时改变有效 focal，需同步重标 `0.27×width` 的视差上限） |
| 2 | **FP16 engine 静默错误**：DA V2-S 全分辨率 FP16 与 FP32 差 **17.5%**；MoGe-2-S/B 的 3 层 metric-scale head **即使 FP32 也错**（TRT 10.3 fused kernel） | §6「FP16 ≈ FP32」这一隐含假设不成立；论文给的修法是把 `scaled_dot_product_attention` 导出改写成 `softmax(q·s·kᵀ)·v`，并把 MoGe-2 的 scale head 移出 engine。工程上必须做 **FP16 vs FP32 逐模型回归**，不能假设等价 |
| 3 | **libSGM 的 256 disparity levels 与分辨率强耦合**：全分辨率只覆盖 255 px，半分辨率 ≈510 px，quarter ≈1020 px；本文正是为此剔掉了 13 个近距场景（265–712 px） | §5「视差落窗内」假设 + 表 1 的 libSGM 约束。若在全分辨率跑近距场景，近处会大面积失效；正确做法是降分辨率跑或调大 `num_disparities`（cost volume 随路径数×视差层数增长，会撞内存） |
| 4 | **用 AbsRel 单指标选型会选错边界**：MoGe-2-L oracle 3.78% 排名最好，但边缘 **46.1%** 是 flying points；libSGM full 边缘只有 1.1% 却排在中游 | §6「单目在边界会抹平」+ §5「AbsRel 对 flying point 不敏感、对缺失中立」。避障/抓取/自由空间类下游必须**同时看边缘子集指标（flying points + 边缘密度）**，否则会选到边界糊成一团的模型 |

---

[← Back to module README](./README.md)

> **Status**：v0.1 · 基于 arXiv 全文 · 未在真机复现的数字标 `UNVERIFIED`（本文所有精度/时间/能耗数字均为论文原文转述，未做独立复现；§3 玩具例子的数值为示范设定，已明确标注）

[//]: # "<!-- source: https://arxiv.org/abs/2610.27199 -->"
