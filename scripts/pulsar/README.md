# Pulsar Spatial Pipeline — Phase 1 (standalone)

> Auto-collect → LLM-rate → push to TG + write to `reports/spatial-daily/YYYY-MM-DD.md`
>
> Pure stdlib + `urllib` (no `requests` / `feedparser` deps). Python 3.9+.

---

## 4 files

| Script | Function | I/O |
|---|---|---|
| `_config.py` | Central config (RSS feeds / TG / model / keywords) | (imported) |
| `collect.py` | Fetch arxiv RSS → keyword filter A → dedup → JSON | stdout JSON |
| `rate.py` | LLM qwen3.5-plus rate ⚡/🔧/📖/❌ | stdin → stdout JSON |
| `post.py` | Write daily markdown + Telegram push | stdin JSON → file + TG |
| `run_daily.py` | Single-cron orchestrator (chains 1→2→3) | env vars only |

---

## Env vars

```bash
export DASHSCOPE_API_KEY=sk-xxx            # Aliyun qwen3.5-plus
export TELEGRAM_BOT_TOKEN=123:abc          # reuse ai_agent_dailybot
export TELEGRAM_CHAT_ID=-1001234567890     # new target for spatial
# optional:
export SPATIAL_DRY_RUN=1                   # skip TG push, only write reports
export SPATIAL_DATE=2026-05-24             # backfill mode
```

---

## Try it locally (dry run, no TG push)

```bash
cd /home/claudeuser/Spatial-Intelligence-Handbook
export DASHSCOPE_API_KEY=sk-xxx
export SPATIAL_DRY_RUN=1
python3 scripts/pulsar/run_daily.py
```

Output: `reports/spatial-daily/YYYY-MM-DD.md` will be created. No TG push.

---

## Cron (server deployment)

Once env vars set on server, add to crontab:

```cron
# Spatial daily — 08:30 weekdays (after arxiv RSS refresh ~08:00 UTC)
30 8 * * 1-5 cd /path/to/Spatial-Intelligence-Handbook && python3 scripts/pulsar/run_daily.py >> /tmp/spatial-daily.log 2>&1
```

Or if you're on Pulsar's existing server (avoid time collision with VLA / AI cron):

| 既有 cron | 時間 | Spatial 建議 |
|---|---|---|
| upstream-monitor | 00:50 | — |
| ai-app-rss | 06:45 | — |
| vla-rss | 09:05 | — |
| Spatial daily | — | **08:30** (between AI 08:00 picks and VLA 09:05) |

Server clock UTC+8 假設；arxiv RSS 凌晨 UTC 更新，CN time 約 08:00 後可用。

---

## Workflow detail

### Stage 1 — collect.py

1. Fetch 4 arxiv RSS feeds (`cs.RO` / `cs.CV` / `cs.AI` / `cs.LG`)
2. Skip weekends (arxiv 沒新文)
3. Parse XML → `[{id, title, abstract, link, category}]`
4. **Layer A filter**: title OR abstract 含 spatial AI 關鍵詞（~30 個，見 `_config.py KEYWORDS_A`）
5. **Layer C reject**: title 含 medical / speech / molecule 等明顯離題詞 → drop
6. **Layer B boost**: title 含 drone / production / benchmark → 標 `boost=True`
7. **Dedup**: 跟 `state/seen_arxiv_ids.json` (60 天 window) 比對，新 paper only
8. Output: JSON list to stdout

### Stage 2 — rate.py

1. 讀 stdin JSON
2. 按 boost + category 排序（boost 先，cs.RO 先）
3. Cap 80 paper (LLM cost guard)
4. 每篇調 qwen3.5-plus 評 ⚡/🔧/📖/❌：
   - Prompt 教 model 用 ontology v3 標準
   - 要求 JSON output: `{rating, reason, tags}`
   - Retry 3×, backoff 5s/10s/15s
5. Drop ❌ (除非 `--keep-rejects`)
6. Output: enriched JSON to stdout

### Stage 3 — post.py

1. 讀 stdin JSON
2. 按 rating priority 排序
3. **生成 markdown** → `reports/spatial-daily/YYYY-MM-DD.md`
   - 分 3 tier sections: ⚡ Load-bearing / 🔧 Engineering / 📖 Reference
   - 每篇含 title link, arxiv ID, category, boost flag, tags, reason
4. **TG push**: 只推 top 5 個 ⚡/🔧 (📖 太雜不推)
5. **Prune**: 自動刪 `reports/spatial-daily/` 90 天前的舊文件

---

## State files

| Path | Purpose | Format |
|---|---|---|
| `state/seen_arxiv_ids.json` | dedup cache (60-day window) | `{id: date_seen}` |

State 目錄已加 `.gitignore`，runtime data 不進 git。

---

## Failure modes & monitoring

| Failure | Symptom | Fix |
|---|---|---|
| DashScope rate limit (429) | "qwen call failed code=429" | rate.py 自動 retry；hour 配額耗盡需等 |
| arxiv RSS timeout | "fetch failed" + 0 papers | stage 1 仍 OK，今天可能空 |
| TG bot token wrong | "TG HTTP 401" | check `TELEGRAM_BOT_TOKEN` |
| TG chat_id wrong | "TG HTTP 400 chat not found" | check `TELEGRAM_CHAT_ID` |
| Weekend run | "SKIP: YYYY-MM-DD is weekend" | 預期行為 |
| 全天 0 ⚡/🔧 | "no ⚡/🔧 papers, skipping TG push" | 寫 markdown 但不推 TG |

---

## Future (Phase 2+)

- Weekly summary cron (`weekly.py` → `reports/spatial-weekly/`)
- GitHub anchor repo issue monitor (跟 VLA-Handbook GH issues sensor 同模式)
- 整合 Pulsar 主倉 `memory/domains.json` 註冊 spatial domain（取消 standalone）
- Hypothesis registry（每月校準）
- Cross-domain insight engine (spatial × VLA × AI)

---

## License & contribution

Same as parent repo (CC BY 4.0). Bug reports / PR welcome via GitHub Issues.

See [`docs/pulsar-integration.md`](../../docs/pulsar-integration.md) for the original design spec
(written for Pulsar production server integration). This standalone version is the **MVP first
cut** that runs anywhere with Python + 3 env vars.
