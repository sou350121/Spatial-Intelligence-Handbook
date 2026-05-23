# Mintlify 部署指南

> Handbook 對應的 Mintlify docs site 設定文檔。當前狀態：`docs.json` 已就位（186 頁全納入 nav），等待 GitHub App 安裝 / Mintlify dashboard 連接。

## 為什麼用 Mintlify

GitHub raw markdown 雖然能讀，但對 186 個 md 來說：

| 維度 | GitHub raw | Mintlify |
|---|---|---|
| 全文搜索 | ❌（只能 file name）| ✅ Algolia 級 |
| 側邊欄導航 | ❌ | ✅ 11 tab × 多層 group |
| 跨頁鏈接 | ✅ 但要手動 | ✅ 自動 anchor |
| Mobile 體驗 | 差 | ✅ |
| 部署成本 | $0 | $0（OSS / personal tier）|

---

## 部署流程（一次性，~15 分鐘）

### 1. 安裝 Mintlify GitHub App

1. 去 https://dashboard.mintlify.com → Sign in with GitHub
2. 創建新 project，選擇 repo `sou350121/Spatial-Intelligence-Handbook`
3. Mintlify 會自動偵測 `docs.json`（在 repo root）
4. 推送任何 commit 後會自動 rebuild（通常 30s-2 min）

### 2. 預覽 URL

預設會給 `spatial-intelligence-handbook.mintlify.app`（或類似 subdomain）。Mintlify dashboard 可以改 subdomain。

### 3. 自訂域名（可選）

域名（如 `spatial.molt.bot`）需要在 Mintlify dashboard 加 custom domain 並配 Cloudflare CNAME。**當前先不做**，先用 mintlify.app subdomain 上線驗證。

---

## docs.json 結構

由 `scripts/gen_mintlify_nav.py` 自動產生，**不要手改**。要改結構編輯 generator 然後重跑：

```bash
python3.11 scripts/gen_mintlify_nav.py > docs.json
```

### 當前 tab 結構（11 個）

| Tab | 來源目錄 | 頁數 |
|---|---|---|
| Get Started | repo root | ONBOARDING / README / CONTRIBUTING / AGENTS |
| Foundations | `foundations/` | 13 zone × ~6 篇 |
| Embodiments | `embodiments/` | 6 embodiment（aerial 含 9 子目錄）|
| Crossing | `crossing/` | 5 sub-lane |
| Cheat Sheet | `cheat-sheet/` | 5 篇全景 |
| Deployment | `deployment/` | 5 sub-lane |
| Benchmarks | `benchmarks/` | 6 embodiment 對應 |
| Bridge to VLA | `bridge-to-vla/` | 3-4 篇 |
| Companies | `companies/` | 8 公司 |
| Reports | `reports/` | weekly/biweekly |
| Docs | `docs/` | meta（本文檔在這）|

---

## 已知 Mintlify Caveats

### 1. 內部鏈接格式

Mintlify 期望內部鏈接是**根相對路徑、無 `.md` 擴展名**，例如：

```
Mintlify 風格 (✅):   [X](/foundations/3dgs-family/3dgs_original_dissection)
GitHub 風格 (❌):     [X](./foundations/3dgs-family/3dgs_original_dissection.md)
```

**現狀**：handbook 內部鏈接全是 GitHub 風格（含 `.md`、相對路徑）。Mintlify 對這種鏈接**會自動降級為純鏈接顯示**（不會 404，但失去 next/prev 流動）。

**修復策略（v2 再說）**：寫個 `scripts/normalize_links_for_mintlify.py`，在 CI 階段把 `.md` 鏈接轉換成根相對。當前保持 GitHub-friendly。

### 2. Curly braces `{x}` 在純文字中

Mintlify 處理 `.md` 文件時相對寬容，但 inline `{x}`（非 code span）可能被誤解為 JSX 表達式。

**現狀**：所有 `{x}` 模式都在 code span（` ``` 或行內反引號）內部，無風險。

### 3. CJK 字符 / 中文標題

Mintlify 支援 CJK，但**自動產生的 URL slug** 來自文件名（英文），所以中文標題不會出 anchor 問題。

### 4. Math / LaTeX

Mintlify 需要在 `docs.json` 加 `"math": "katex"`（或 `mathjax`）才會渲染 `$...$`。當前**未啟用**，若日後需要再加。

---

## CI 集成

`scripts/handbook_audit.py` 的 **Check 8 (Mintlify Nav)** 驗證：

- 每個 repo 內 .md 必出現在 `docs.json` nav（無 orphan）
- `docs.json` 引用的 page id 必須存在（無 dangling）

CI workflow `.github/workflows/audit.yml` 會在 push / PR 自動跑。新增 md 必須同時：

```bash
python3.11 scripts/gen_mintlify_nav.py > docs.json
git add docs.json
```

否則 CI 紅。

---

## 後續優化（v2 候選）

1. **Math 渲染**：加 `"math": "katex"` 到 `docs.json`
2. **OpenGraph 預覽**：加 `"metadata"` block
3. **Search**：開啟 Mintlify 內建 Algolia
4. **Analytics**：接 PostHog / GA4
5. **Custom domain**：`spatial.molt.bot`
6. **Link normalization script**：把 GitHub 風格 `.md` 鏈接轉成 Mintlify 風格
7. **i18n**：handbook 多為中文，未來考慮 EN 版本鏡像

---

🔗 Mintlify 官方文檔 · https://mintlify.com/docs
🔗 docs.json schema · https://mintlify.com/docs.json
🔗 GitHub App · https://github.com/apps/mintlify
