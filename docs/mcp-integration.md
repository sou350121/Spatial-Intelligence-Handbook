# MCP 整合 — 讓 Claude / Agent 直接查 Handbook

> **Mintlify Hobby tier 自帶 MCP server**，無需架設。Endpoint 已 live：
> `https://kensou.mintlify.app/mcp`（Streamable HTTP，無 auth，public）

---

## 為什麼要接 MCP

| 之前 | 之後 |
|---|---|
| 問 Claude「VGGT vs VIO 在 drone 為什麼不能替代」→ Claude 用訓練資料回答（不一定準）| 問 Claude → 它先查 handbook，引用具體 dissection 回答 |
| 提到 atlas → Claude 不知道我們有 atlas | Claude 自動 search 找到 `cross_zone_failure_atlas.md` |
| 想知道哪篇文章是 anchor → 自己翻 | Claude 用 filesystem 工具 grep 找 |

---

## Endpoint 規格

```
URL:        https://kensou.mintlify.app/mcp
Transport:  Streamable HTTP（MCP 標準）
Auth:       none（public OSS docs）
Discovery:  https://kensou.mintlify.app/.well-known/mcp
```

**自帶 2 個 tool**：

| Tool | 功能 |
|---|---|
| `search_spatial_intelligence_handbook` | 語義搜索；輸入自然語言 query，回最相關 5-10 段帶 URL |
| `query_docs_filesystem_spatial_intelligence_handbook` | 虛擬 shell（rg / grep / find / tree / cat / head）；可結構性探索 + exact match |

---

## 接入 Claude Desktop（macOS）

1. 找到 config 路徑：
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. 在 `mcpServers` 加入：
   ```json
   {
     "mcpServers": {
       "spatial-handbook": {
         "url": "https://kensou.mintlify.app/mcp"
       }
     }
   }
   ```

3. 完全退出 Claude Desktop（⌘Q，不只是關視窗）後重啟。

4. 驗證：開新對話，問「what's in the spatial intelligence handbook?」— Claude 會自動使用 `search_spatial_intelligence_handbook` tool 並引用具體頁面。

---

## 接入 Claude Code（CLI）

### 方法 A：用 `claude mcp add`（推薦）

```bash
claude mcp add --transport http spatial-handbook https://kensou.mintlify.app/mcp
```

### 方法 B：手動編輯 settings

`~/.claude/settings.json` 加入：
```json
{
  "mcpServers": {
    "spatial-handbook": {
      "type": "http",
      "url": "https://kensou.mintlify.app/mcp"
    }
  }
}
```

restart `claude` CLI 後生效。

---

## 接入其他 MCP client

任何支援 Streamable HTTP 的 MCP client 都可用。直接 POST 到 `/mcp`：

```bash
curl -X POST "https://kensou.mintlify.app/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

---

## 實測對話範例

**你問**：「我做 drone VIO，VGGT 能不能取代我的 OpenVINS？」

**Claude（用 MCP）**：
> 不能。我查了 handbook 的 `crossing/slam-vio-migration/vggt_vs_drone_vio.md`：
>
> 1. **Latency**：VGGT 約 100 ms / 視圖；drone autopilot 需要 5-10 ms 端到端 → 差一個量級。
> 2. **Streaming**：VGGT 是 feed-forward batch；VIO 需要 incremental update 每 IMU 樣本（200 Hz）。
> 3. **Metric scale**：VGGT 輸出 up-to-scale；drone position controller 必須米制。
> 4. **Vibration**：VGGT training prior 沒有 propeller-induced motion blur。
>
> Handbook 建議：**hybrid VGGT + 經典 VIO**（VGGT 給 prior，VIO 跑控制環），不是替換。
>
> 詳見 `https://kensou.mintlify.app/crossing/slam-vio-migration/vggt_vs_drone_vio.md`。

---

## 為什麼這比 raw Web 搜索強

1. **零幻覺**：Claude 引用的是你 handbook 的實際 dissection，不是訓練資料
2. **跨頁面綜合**：MCP search 跨 188 md 做 semantic match，超過任何單頁 Ctrl+F
3. **即時同步**：你 push 新 dissection → Mintlify 7 秒 rebuild → MCP 立刻能查到
4. **無 auth**：你可以分享 endpoint URL 給隊友，他們的 Claude / agent 也能用

---

## 已知 caveat

1. **MCP filesystem 路徑用 `.mdx`**（不是 `.md`）— Mintlify 內部轉換。例如要讀 `crossing/overview.md` 在 MCP 裡是 `cat /crossing/overview.mdx`。
2. **每次 call output ≤ 30 KB** — 大文件用 `head -200` 或 `rg -C 3` 替代 `cat`。
3. **無狀態**：每次 call working directory 重置到 `/`。
4. **Mintlify Hobby 已含 MCP**，無需升級。

---

## 相關文檔

- [`mintlify-deployment.md`](./mintlify-deployment.md) — Mintlify 部署細節
- Mintlify MCP 官方說明 — https://mintlify.com/docs/ai/model-context-protocol
- MCP 協議 — https://modelcontextprotocol.io

---

🔗 Live endpoint: https://kensou.mintlify.app/mcp
🔗 MCP discovery: https://kensou.mintlify.app/.well-known/mcp
