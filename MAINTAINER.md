# Maintainer Notes

> 維護者觀點、路線圖、風險對冲、自動更新管線。**讀者請看 [`README.md`](./README.md) / [`ONBOARDING.md`](./ONBOARDING.md)**。本文是內部 + 公開透明的維護者視角。

---

## Handbook 的 moat（真正的護城河）

這本 handbook 真正的 moat 不在論文數量，在三處：

1. **`crossing/` 5 個章節的對比深度** — 跨 embodiment 比較是唯一沒人做的角度
2. **`foundations/sensor-physics/` 這條 industry 沒人寫的獨家軸** — SWaP-C 視角的 sensor 物理
3. **`embodiments/aerial/` drone 視角的工程細節** — VIO 振動魯棒性、SWaP-C 預算、on-board 3DGS、HKUST 真機 gotchas

守住這三處，handbook 就立得住。

---

## 風險與對冲

| 風險 | 對冲 |
|---|---|
| **範圍爆炸** — 多 embodiment 看起來是百科全書 | 閥門是 `crossing/` 的 5 個維度封閉，新 embodiment 只補 `embodiments/` 子樹，不讓書變厚到失控 |
| **品牌稀釋** — VLA-Handbook 流量被分流 | 第一版作為 VLA-Handbook 姊妹仓發布，README 互鏈，內容超過 50 篇深度文檔再獨立宣傳 |
| **圖形學 lane 的誘惑** — 容易變成生成式 3D 綜述 | 嚴格「是否對具身決策有用」門檻：Genie Sim 收（給 VLA 當數據），Marble 大部分功能不收（用戶是人不是機器人）|
| **sensor-physics 不可持續** — 能寫 NIR 但不能覆蓋全譜 | 第一版只把 active-NIR 寫到深度第一，作為 wedge；其他模態慢慢補，不強求一開始就齊全 |
| **某 embodiment 沉寂** — 水下論文一年沒幾篇 | Pulsar pipeline 讓其他 embodiment 接力自校準；`crossing/` 章節本身不依賴任一 embodiment 的論文流量 |

---

## 自動更新（Pulsar 整合計劃）

複用 VLA-Handbook 的 [Pulsar pipeline](https://github.com/sou350121/Pulsar-KenVersion)：
- 每日論文評級 ⚡/🔧/📖/❌
- 每週深度解析
- 每週日週報
- 每兩週雙週推理報告

本仓的 hypothesis registry 為每個 embodiment 單獨建一組假設 + 一組 cross-embodiment 假設。

### 種子假設舉例

- 「feed-forward 3D（VGGT 系）會在 2 年內取代 per-scene optimization（3DGS）成為機器人空間感知主流」
- 「純 RGB + foundation depth 在 manipulation 範圍內會持續壓制 active sensing，但在 outdoor drone 上不會」
- 「3DGS-as-simulator 比 traditional sim 更早 product-ready 在 drone 上、更晚在 manipulation 上」

完整集成細節見 [`docs/pulsar-integration.md`](./docs/pulsar-integration.md)。寫入權限矩陣見 [`AGENTS.md`](./AGENTS.md)。

---

## v 版本演進

- **v0** — 提案版 / 種子內容
- **v0.1** — 13 zone × ~6 dissection / 36 dissection 全 14-item / Atlas v1（current）
- **v0.2 (planned)** — Pulsar 整合上線 + ontology 雙向校驗 + Math 渲染（KaTeX）
- **v1.0 (planned)** — 自訂域名 `spatial.molt.bot` + 雙語 mirror + i18n

---

## 維護者視角

**v0 提案版** → 正在 ramp 到 v0.1。如果某個 embodiment 連 1 篇 anchor dissection 都沒，標 ⚠ 警示在 zone overview。

當 sensor-physics 超過 30 篇且其中 ≥ 5 篇 dissection 帶 production 案例，可以考慮獨立成 mini-book。

---

## 相關文檔

- [`README.md`](./README.md) — 用戶向 handbook 入口
- [`ONBOARDING.md`](./ONBOARDING.md) — 5 分鐘讀者前門
- [`AGENTS.md`](./AGENTS.md) — 寫作規範 + 14-item 模板 + 5 type 文檔分層
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — PR 流程
- [`docs/mintlify-deployment.md`](./docs/mintlify-deployment.md) — Mintlify 部署
- [`docs/mcp-integration.md`](./docs/mcp-integration.md) — MCP 整合
- [`cheat-sheet/ontology.md`](./cheat-sheet/ontology.md) — 學術 taxonomy v2
