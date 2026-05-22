# Feed-Forward 3D — GitHub Failure Atlas (生态失败图谱)

> **核心定位**：从 issues / PRs 看 feed-forward 3D 五件套（VGGT、VGGT-Ω、MapAnything、DUSt3R、MASt3R）在真实部署里**哪里破**、社区把维护精力**投在哪条轴**。
>
> 不是 dissection — 这是 *ecosystem 层* 文档（按 AGENTS.md §文档类型分层 = ecosystem，不必满 14 项门槛）。

**Status:** v1 — 数据快照 2026-05-21；GitHub 数字（stars / forks / issue 编号）截止该日，所有未亲自跑 git 历史的 commit 频度均标 `UNVERIFIED`。

> 📅 数据首抓 2026-05-21 · 最後校對 2026-05-22 · 📊 跨 zone 全景: [`cheat-sheet/cross_zone_failure_atlas.md`](../../cheat-sheet/cross_zone_failure_atlas.md)

**X-Ray.** 把三件套+前驱 DUSt3R/MASt3R 谱系放一起看，会浮出三条规律：(1) Meta 三件套（VGGT, VGGT-Ω, MapAnything）momentum 在涨，issue 集中在 *OOM / scale ambiguity / 长视频*，是"能用但要解扩展"的烦恼；(2) 谱系祖先 DUSt3R / MASt3R 的 issue 集中在 *数据预处理 / 训练复现 / 文档 gap*，典型的"被取代之前最后一波用户"；(3) license 是真实部署决策点 — MapAnything Apache 2.0 vs DUSt3R/MASt3R CC-BY-NC-SA，决定能不能商用。

---

## 概览矩阵 (Snapshot 2026-05-21)

| Repo | Stars | Forks | Open issues | License | Momentum |
|---|---|---|---|---|---|
| facebookresearch/vggt | 13.2k | 1.5k | 246 | 自定义（含 commercial checkpoint）| 活跃 |
| facebookresearch/map-anything | 3.4k | 254 | 28 | Apache 2.0 | 活跃 |
| naver/dust3r | 7.1k | 752 | 133 | CC-BY-NC-SA 4.0 | 慢 |
| naver/mast3r | 2.9k | 263 | 94 | CC-BY-NC-SA 4.0 | 慢 |
| VGGT-Ω | — | — | — | — | 论文 2026-05 刚出，开源状态 `UNVERIFIED`（arXiv 2605.15195 未确认 code release） |

> 数字 last-commit-date 仍 `UNVERIFIED` — WebFetch 未能稳定抓到精确日期，issue 编号是更可靠的活跃度代理（VGGT 一年内累积到 #476，DUSt3R 一年多才到 #243）。

---

## VGGT v1

- **Repo**: https://github.com/facebookresearch/vggt
- **Stats**: 13.2k stars / 1.5k forks / open issues 246 / 24 open PRs / last-commit `UNVERIFIED`
- **Top 5 failure cases**（issue 编号是真实抓到的，描述基于 issue title）:
  1. **OOM in demo_colmap** (#470) — "OOM (Out of Memory) issue in demo_colmap is due to the resize dimension problem" — 用户跑 demo 触发显存爆炸，与 resize 维度耦合；典型的 N-view 全局 attention 二次方代价问题。
  2. **Depth map scale ambiguity** (#471) — 不清楚输出是 metric 还是 relative depth；这是 VGGT v1 的**已知架构限制**（un-metric），但社区还在反复问，文档需补。
  3. **Scene segmentation failure** (#472) — N-view 输入混了不同场景时，模型把序列错切成多个 scene；说明 VGGT 没有显式的 scene-boundary 信号。
  4. **Long video support: factor graph stitching** (#474) — 用户要扩展超出 batch 上限的长视频，请求开源 factor-graph stitching pipeline；说明 VGGT v1 batch 模式天花板被普遍撞到。
  5. **Training VGGT from scratch** (#476) — 反复有人问完整训练 recipe；说明只放 inference checkpoint 不够。
- **PR 方向** (近 6 月):
  - 依赖升级密集（torch 2.3→2.8 #462、gradio #463）
  - 多 GPU / 性能（multi-GPU demo_colmap #445、loading 加速 1.24× #251）
  - 工程修复（depth unprojection #433、CUDA tensor serialization #242）
  - 输入鲁棒性（RGBA alpha #434、EXIF transpose #350、grayscale 兼容 #133）
- **Project momentum**: ✅ 活跃 — issue # 在两个月里从 #467 涨到 #476，PR 一直有 dependency bump（说明维护者 hands-on）。
- **是否该选**: **可生产**（research / non-aerial-realtime），但务必绕开 #470 的 demo_colmap path；自己写 inference loop + 控制 N。商用走 VGGT-1B-Commercial checkpoint。

## VGGT-Ω

- **Repo**: arXiv 2605.15195；**GitHub repo `UNVERIFIED`** — 论文 2026-05 刚出，code release 状态未确认（搜 facebookresearch 下没有独立的 `vggt-omega` 公开 repo；可能在 main `vggt` repo 里 branch / 待发布）。
- **Stats**: 全部 `UNVERIFIED`。
- **Top failure cases**: N/A — 没 GitHub 就没 issue history。论文宣称的 register attn / 自监督 / 30% memory 三个轴一旦开源会立刻被社区压测。
- **PR 方向**: N/A。
- **Project momentum**: ⚠️ **未知** — 论文已 Meta 自家，VGGT v1 的活跃度暗示 Ω 会接住，但 *没有 code* 之前不能算社区项目。
- **是否该选**: **等开源** — 现在只能读 paper，部署还是用 VGGT v1。建议维护者 2026-Q3 重查此 repo 状态。

## MapAnything

- **Repo**: https://github.com/facebookresearch/map-anything
- **Stats**: 3.4k stars / 254 forks / 28 open issues / latest release v1.1.1 (2026-03-23) / Apache 2.0
- **Top 5 failure cases**:
  1. **ASE dataset metadata mismatch** (#155) — 发布的 metadata split 和公开 ASE 数据集 scene 数对不上；典型的数据集打包 bug。
  2. **WAI conversion for ASE** (#153) — 用户不清楚怎么把 ASE 转成 MapAnything 所需格式；文档 gap。
  3. **Large GLB file** (#152) — 输出 GLB 太大；下游 viewer / web 部署疼。
  4. **Deceiving point map reprojection consistency** (#147) — 点云投影回 2D 看着对，但跨视图一致性差；这是 factored repr (D/R/T/s) 解 metric 之外**留下的另一条暗坑**。
  5. **External predictions with mapanything model not working** (#141) — 自定义输入 pipeline 跑不通；feed-forward 模型外部输入接口不稳。
- **PR 方向** (近 6 月): 数据脚本完善、release tagging 规整（v1.0 → v1.1.1 半年三个 patch）；没看到大架构 PR — 说明项目处于 *stabilization* 而非 *exploration* 阶段。
- **Project momentum**: ✅ 活跃 — 半年 0 → 3.4k stars，release 节奏稳定，issue 量少（28）说明文档与 example 跟得上。
- **是否该选**: **首选 metric feed-forward 3D**（Apache 2.0 可商用，区别于 DUSt3R/MASt3R 的 CC-BY-NC）。注意 #147 的 reprojection consistency 在 manipulation grasp / drone control 这种亚厘米要求场景需自测。

## DUSt3R

- **Repo**: https://github.com/naver/dust3r
- **Stats**: 7.1k stars / 752 forks / 133 open issues / 10 open PRs / CC-BY-NC-SA 4.0
- **Top 5 failure cases**:
  1. **AMD MI GPUs supported?** (#243) — 硬件兼容性求问；DUSt3R 强绑 CUDA，AMD 用户被挡门外。
  2. **Cannot preprocess scannet++ v2** (#237) — 主流学术数据集预处理脚本对不上新版 schema。
  3. **selection_pairs.npz for ARKitScene** (#239) — 训练数据 pair 选择脚本缺失。
  4. **Origin of coordinate system of constructed scene?** (#232) — 输出坐标系语义不清；DUSt3R 是 2-view 相对坐标，绝对参考帧没文档。
  5. **Waymo Open Dataset preprocessing** (#229) — 户外 / driving 数据接入难。
- **PR 方向**: 节奏明显放缓 — Naver 系明显把精力转移到 MASt3R 和后续 Pow3R / MUSt3R。
- **Project momentum**: ⚠️ **慢** — issue 编号从 #227 (2025-06) 到 #243 (2026-02) 八个月才涨 16 个，发表后第二年活跃度断崖。Stars 数仍涨，但维护者 hands-on 不如 VGGT。
- **是否该选**: **作为范式入门**仍值得读 / 用 dissection；新项目建议用 VGGT v1 / MapAnything 替代。**绝不商用**（CC-BY-NC-SA）。

## MASt3R

- **Repo**: https://github.com/naver/mast3r
- **Stats**: 2.9k stars / 263 forks / 94 open issues / 7 open PRs / CC-BY-NC-SA 4.0
- **Top 5 failure cases**:
  1. **KeyError: 'desc'** (#147) — 关键字典 key 失踪；checkpoint / config 不齐。
  2. **MASt3R-SfM Codebook Computation** (#145) — centroid 计算 doc 不清；SfM 扩展只 paper 写、code 没。
  3. **Fine-tuning Problems** (#144) — 训练 lr 敏感、divergence；下游微调难。
  4. **Model loading error: `dunemast3r_cvpr25_vitbase`** (#142) — 命名 / weight loading 接口断。
  5. **Demo reproducibility** (#138) — 本地 demo.py 输出和在线 demo 不一致；典型的"放代码没放完整 inference recipe"。
- **PR 方向**: 类似 DUSt3R，明显放缓。
- **Project momentum**: ⚠️ **慢** — 与 DUSt3R 同步，Naver 系 attention 已挪到后续工作（Pow3R / MUSt3R）。
- **是否该选**: **matching / localization 任务**仍可作 baseline；新 feed-forward 工程接 MapAnything 或 VGGT 系。商用不行。

---

## 谱系总结 (Zone-level momentum)

**FF-3D 谱系 momentum 集中在 Meta 三件套（VGGT / VGGT-Ω / MapAnything），Naver DUSt3R 系明显放缓**。

四条 actionable 线索：
1. **License 二极分化** — Meta 系（Apache 2.0 / 自定义含 commercial checkpoint）vs Naver 系（CC-BY-NC-SA 4.0 全锁死商用）；商用决策一目了然。
2. **VGGT v1 的 OOM / batch / scale 三大限制**全部在 issue 显现（#470 OOM、#474 long-video、#471 scale ambiguity）— 与 README §三件套对照表里"VGGT v1 仍未解"列完全对得上，**社区已经在压测同一条边界**。
3. **MapAnything 的暗坑是 reprojection consistency**（#147）而非 metric scale — 提示下游 grasp / control 场景实测时别只信 metric loss。
4. **VGGT-Ω 的 GitHub repo 状态 `UNVERIFIED`** — 这是本 atlas 最大的开放问题；维护者建议每月重查 facebookresearch 组织页。

**Surprise 发现**: DUSt3R / MASt3R 在 2025 年还是热论文，但 2025-Q3 起 issue 增速断崖式下降，远比预期更"被自己后继工作吞并"；从 maintainer 视角看，**这是个早期 lifecycle 信号 — 一篇 paper 的代码 ≠ 一个长期项目**。

---

[← Back to Feed-Forward 3D](./README.md)
