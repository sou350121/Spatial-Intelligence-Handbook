# Pulsar Spatial Pipeline — Phase 1 (standalone)

> Auto-collect → LLM-rate → push to TG + write to `reports/spatial-daily/YYYY-MM-DD.md`
>
> Pure stdlib + `urllib` (no `requests` / `feedparser` deps). Python 3.9+.

---

## 4 files

| Script | Function | I/O |
|---|---|---|
| `_config.py` | Central config (RSS feeds / TG / model / keywords) | (imported) |
| `_llm.py` | Shared LLM transport: DeepSeek primary → qwen fallback + JSON salvage | (imported) |
| `collect.py` | Fetch arxiv RSS → keyword filter A → dedup → JSON | stdout JSON |
| `rate.py` | LLM rate ⚡/🔧/📖/❌ (deepseek-flash) | stdin → stdout JSON |
| `post.py` | Write daily markdown + Telegram push | stdin JSON → file + TG |
| `run_daily.py` | Single-cron orchestrator (chains 1→2→3) | env vars only |

---

## Env vars

```bash
# Required — at least one. DeepSeek is primary, qwen is the fallback.
export DEEPSEEK_API_KEY=sk-xxx             # DeepSeek deepseek-flash
export DASHSCOPE_API_KEY=sk-xxx            # Aliyun qwen (fallback)

# Optional — only if your DashScope key is a CodingPlan key, which serves a
# different catalog from a different host (qwen-plus does not exist there):
export SPATIAL_DASHSCOPE_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
export SPATIAL_LLM_MODEL=qwen3.5-plus

# Optional — TG push (default: skipped, integration via git)
export TELEGRAM_BOT_TOKEN=123:abc          # opt-in TG push
export TELEGRAM_CHAT_ID=-1001234567890

# Optional — dev/test
export SPATIAL_DRY_RUN=1                   # skip writes (no markdown, no TG)
export SPATIAL_DATE=2026-05-24             # backfill mode
```

**Default workflow**: handbook integration via git — `reports/spatial-daily/YYYY-MM-DD.md`
auto-committed to repo, Mintlify rebuild picks it up. No TG bot needed.

---

## Try it locally

```bash
cd /home/claudeuser/Spatial-Intelligence-Handbook
export DEEPSEEK_API_KEY=sk-xxx
python3.11 scripts/pulsar/run_daily.py
```

Output: `reports/spatial-daily/YYYY-MM-DD.md` created. No TG push (no token set).

For true dry-run (skip even markdown write), add `SPATIAL_DRY_RUN=1`.

---

## Deployment — 2 options

### Option A — GitHub Actions（推薦，無 server）

文件：[`.github/workflows/pulsar-spatial-daily.yml`](../../.github/workflows/pulsar-spatial-daily.yml)

**Schedule**: weekday 00:30 UTC (≈ 08:30 CN time，arxiv RSS 已 refresh)

**Setup**：
1. GitHub repo → Settings → Secrets and variables → Actions → New repository secret
2. Add `DEEPSEEK_API_KEY` = `sk-xxx` (and `DASHSCOPE_API_KEY` for the fallback)
3. 完成。第一次手動觸發測試：Actions tab → "Pulsar Spatial Daily" → Run workflow

**Workflow 做什麼**：
- Checkout main
- Setup Python 3.11
- Run `scripts/pulsar/run_daily.py`（用 secret API key）
- Sync README + audit
- `git add reports/spatial-daily/` + commit + push (skip if no diff)
- 用 `GITHUB_TOKEN` 自動 push 到 main，無需 PAT

**優勢**：免費、可見 log、易停易啟、不佔本地資源、不會跟其他 agent 撞 git state。

### Option B — Self-hosted cron

文件：[`scripts/pulsar/cron_runner.sh`](./cron_runner.sh)

**Setup**：
```bash
# 在 server 上 (assume Spatial-Intelligence-Handbook checked out at /opt/handbook)
export DEEPSEEK_API_KEY=sk-xxx   # 加到 ~/.profile or wrapper script

# 加 crontab
crontab -e
# 加一行:
30 8 * * 1-5 /opt/handbook/scripts/pulsar/cron_runner.sh
```

**cron_runner.sh 做什麼**：
- `flock` 防併發
- 跑 pipeline
- Sync README + audit (audit FAIL 不 push)
- `git add reports/spatial-daily/` only（不動其他 WIP）
- `pull --rebase` 後 commit + push
- Log to `/tmp/pulsar-spatial-YYYY-MM-DD.log`，30 天自動 rotate

**環境變數**：
- `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` (至少一個；DeepSeek 優先，qwen 兜底)
- `PULSAR_NO_PUSH=1` (test mode — commit local only, no push)
- `PULSAR_NO_COMMIT=1` (test — pipeline only, no git ops)
- `PULSAR_LOG_DIR=/var/log/pulsar` (override default `/tmp`)

**避撞** (跟 VLA / AI cron 共 server)：

| 既有 cron | 時間 | Spatial 建議 |
|---|---|---|
| upstream-monitor | 00:50 | — |
| ai-app-rss | 06:45 | — |
| vla-rss | 09:05 | — |
| **Spatial daily** | — | **08:30** |

Server 假設 UTC+8。arxiv RSS 凌晨 UTC 更新，CN 08:00 後可用。

---

## Workflow detail

### Stage 1 — collect.py

1. Fetch 4 arxiv RSS feeds (`cs.RO` / `cs.CV` / `cs.AI` / `cs.LG`)
2. Skip weekends (arxiv 沒新文)
3. Parse XML → `[{id, title, abstract, link, category}]`
4. **Layer A filter**: title OR abstract 含 spatial AI 關鍵詞（~30 個，見 `_config.py KEYWORDS_A`）
5. **Layer C reject**: title 含 medical / speech / molecule 等明顯離題詞 → drop
6. **Layer B boost**: title 含 drone / production / benchmark → 標 `boost=True`
7. **Dedup**: 跟 `state/seen_arxiv_ids.json` (90 天 window) 比對，新 paper only
8. Output: JSON list to stdout

### Stage 2 — rate.py

1. 讀 stdin JSON
2. 按 boost + category 排序（boost 先，cs.RO 先）
3. Cap 80 paper (LLM cost guard)
4. 每篇調 deepseek-flash 評 ⚡/🔧/📖/❌（失敗才降到 qwen）：
   - Prompt 教 model 用 ontology v3 標準
   - 要求 JSON output: `{rating, reason, tags}`
   - Retry 3×, backoff 5s/10s/15s
   - HTTP 200 但 body 解不出 JSON **算 provider 失敗**（觸發 qwen 兜底），
     不是 parse error——後者會讓整批默默變成 📖 placeholder
   - 全部 80 篇都失敗 → exit 1，不寫 placeholder report
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
| `state/seen_arxiv_ids.json` | dedup cache (90-day window) | `{id: date_seen}` |
| `state/curated_seen.json` | 非 arxiv 策展 dedup cache (120 天) | `{link: date_seen}` |

**這兩個檔是 tracked 的，其餘 state 仍 gitignored。** 原本整個 `state/` 都不進 git —
Phase 1 跑在有持久磁碟的 `cron_runner.sh` 上，那是對的。改跑 GitHub Actions 之後每次
`actions/checkout` 都是全新工作區，**被 ignore 的 cache 就等於不存在的 cache**：
`load_seen()` 每天回 `{}`，60 天 dedup 一次都沒生效過。2026-09-16 實測
`reports/spatial-daily/`：478 次同一 arXiv id 跨日重複刊出，其中 477 次（99.8%）落在
本該擋掉的窗口內。這個部署唯一的持久儲存就是 repo 本身，所以 cache 必須跟著 commit
（workflow 的 `git add` 排在「沒新內容就不 commit」判斷**之後**，以免每天多出空 commit）。

**不變式**：`DEDUP_WINDOW_DAYS >= REPORT_RETENTION_DAYS`，`CURATED_RETENTION_DAYS >=
CURATED_LOOKBACK_DAYS`。記憶比檔案活得短，同一篇就會在兩份還看得到的報告裡各出現一次。
由 `_config.py` 在 import 時直接 raise，並由 `test_gates.py` 守住。

---

## Failure modes & monitoring

| Failure | Symptom | Fix |
|---|---|---|
| DeepSeek / DashScope 429 | "WARN rate/deepseek: HTTP 429, retry" | `_llm.py` 自動 retry；配額耗盡會降到另一家 |
| Key 失效 | "all providers failed — deepseek(...): HTTP 401 \| qwen(...): HTTP 401" | rate.py exit 1 → workflow 紅 + sentinel issue（不會寫 placeholder） |
| DeepSeek 回 200 但 JSON 壞 | "deepseek failed (unparseable_json_body) — falling back to qwen" | 預期行為，salvage 先試兩層修復 |
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
