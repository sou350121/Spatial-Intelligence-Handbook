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
