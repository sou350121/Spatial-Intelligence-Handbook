# Reports · Pulsar-pipeline 自動產出

| Subdirectory | Cadence | Format |
|---|---|---|
| `spatial-daily/` | 每 weekday (00:30 UTC ≈ 08:30 CN) | 當天 arxiv cs.RO / cs.CV / cs.AI / cs.LG 過濾後 LLM 評級 (⚡/🔧/📖) |
| `weekly/` | 每週五 (02:00 UTC ≈ 10:00 CN) | 前瞻偵察 — 本週主軸 / 意外信號 / 五軸熱度 / 可證偽觀察清單（彙整本週日報的 ⚡/🔧） |
| `atlas/` | 每 weekday (隨日報累積) | 🌌 **星圖** — 每篇評級論文的 ontology 五軸座標流；[`overview`](./atlas/overview.md) 看 paradigm 軸質量分佈與漂移 |
| `biweekly/` | (Phase 2) | Retrospective — trends, insights, prediction scorecard |

These mirror VLA-Handbook's `reports/` layout. 管線程式 [`scripts/pulsar/`](../scripts/pulsar/README.md)；
部署 `.github/workflows/pulsar-spatial-daily.yml`（日）+ `pulsar-spatial-weekly.yml`（週）。

**🌌 星圖（Atlas）**：日報是逐日歸檔，星圖是**分析層**——把每篇論文放進 ontology 五軸座標，累積成可測量的座標雲。重點不是清單，是**漂移**：看質量沿 paradigm 軸（geometric → … → world-model-as-policy）隨時間往前遷移。見 [`atlas/overview`](./atlas/overview.md)，機器可讀源 `reports/atlas/atlas.jsonl`。

> 日檔 / 週檔是逐日歸檔內容，不進 Mintlify 側欄逐頁列表，由本 landing page 串接。

[//]: # "<!-- BEGIN PULSAR REPORT INDEX -->"

## 自动报告目录 (Report Archive)

| 类型 | 日期 | 报告 |
|---|---|---|
| 日报 | 2026-10-30 | [阅读](./spatial-daily/2026-10-30.md) |
| 日报 | 2026-10-28 | [阅读](./spatial-daily/2026-10-28.md) |
| 日报 | 2026-10-27 | [阅读](./spatial-daily/2026-10-27.md) |
| 日报 | 2026-10-26 | [阅读](./spatial-daily/2026-10-26.md) |
| 日报 | 2026-10-23 | [阅读](./spatial-daily/2026-10-23.md) |
| 日报 | 2026-10-22 | [阅读](./spatial-daily/2026-10-22.md) |
| 日报 | 2026-10-21 | [阅读](./spatial-daily/2026-10-21.md) |
| 日报 | 2026-10-20 | [阅读](./spatial-daily/2026-10-20.md) |
| 日报 | 2026-10-19 | [阅读](./spatial-daily/2026-10-19.md) |
| 日报 | 2026-10-18 | [阅读](./spatial-daily/2026-10-18.md) |
| 日报 | 2026-10-16 | [阅读](./spatial-daily/2026-10-16.md) |
| 日报 | 2026-10-15 | [阅读](./spatial-daily/2026-10-15.md) |
| 日报 | 2026-10-12 | [阅读](./spatial-daily/2026-10-12.md) |
| 日报 | 2026-10-09 | [阅读](./spatial-daily/2026-10-09.md) |
| 周报 | 2026-W43 | [阅读](./weekly/2026-W43.md) |
| 周报 | 2026-W42 | [阅读](./weekly/2026-W42.md) |
| 周报 | 2026-W41 | [阅读](./weekly/2026-W41.md) |
| 周报 | 2026-W40 | [阅读](./weekly/2026-W40.md) |
| 周报 | 2026-W39 | [阅读](./weekly/2026-W39.md) |
| 周报 | 2026-W38 | [阅读](./weekly/2026-W38.md) |
| 周报 | 2026-W37 | [阅读](./weekly/2026-W37.md) |
| 周报 | 2026-W35 | [阅读](./weekly/2026-W35.md) |
| 周报 | 2026-W33 | [阅读](./weekly/2026-W33.md) |
| 周报 | 2026-W32 | [阅读](./weekly/2026-W32.md) |
| 周报 | 2026-W31 | [阅读](./weekly/2026-W31.md) |
| 周报 | 2026-W30 | [阅读](./weekly/2026-W30.md) |
| 周报 | 2026-W29 | [阅读](./weekly/2026-W29.md) |
| 周报 | 2026-W28 | [阅读](./weekly/2026-W28.md) |
| 产业信号 | 2026-10-30 | [阅读](./curated-signal/2026-10-30.md) |
| 产业信号 | 2026-10-29 | [阅读](./curated-signal/2026-10-29.md) |
| 产业信号 | 2026-10-28 | [阅读](./curated-signal/2026-10-28.md) |
| 产业信号 | 2026-10-27 | [阅读](./curated-signal/2026-10-27.md) |
| 产业信号 | 2026-10-26 | [阅读](./curated-signal/2026-10-26.md) |
| 产业信号 | 2026-10-23 | [阅读](./curated-signal/2026-10-23.md) |
| 产业信号 | 2026-10-22 | [阅读](./curated-signal/2026-10-22.md) |

完整归档：[GitHub reports](https://github.com/sou350121/Spatial-Intelligence-Handbook/tree/main/reports)。

[//]: # "<!-- END PULSAR REPORT INDEX -->"
