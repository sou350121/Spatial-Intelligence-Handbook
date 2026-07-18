"""Spatial Intelligence Handbook — Pulsar pipeline config (Phase 1).

Standalone version: runs anywhere with Python 3.9+ + the 4 env vars below.
Future: integrate with Pulsar's `memory/domains.json` multi-domain registry.

Env vars required:
    DASHSCOPE_API_KEY   — Aliyun qwen3.5-plus (OpenAI-compatible)

Env vars optional:
    TELEGRAM_BOT_TOKEN  — enable TG push (skipped gracefully if absent)
    TELEGRAM_CHAT_ID    — TG target chat ID
    SPATIAL_DRY_RUN=1   — collect + rate only, skip writes (dev/test)
    SPATIAL_DATE        — override "today" in YYYY-MM-DD (for backfill)

Default workflow: handbook integration via git (commit reports/spatial-daily/).
TG is optional opt-in.
"""
from __future__ import annotations
import os
from pathlib import Path

# ---- Paths ----------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = REPO_ROOT / "scripts" / "pulsar" / "state"
REPORTS_DIR = REPO_ROOT / "reports" / "spatial-daily"
WEEKLY_DIR = REPO_ROOT / "reports" / "weekly"
# Atlas: append-only stream of 5-axis coordinates for every rated paper, plus a
# generated human/agent-readable summary. This is the star-map data layer.
ATLAS_DIR = REPO_ROOT / "reports" / "atlas"
ATLAS_JSONL = ATLAS_DIR / "atlas.jsonl"
ATLAS_OVERVIEW = ATLAS_DIR / "overview.md"

# ---- LLM ------------------------------------------------------------
# DashScope OpenAI-compatible endpoint (CodingPlan Pro since 2026-04)
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen-plus"  # qwen3.5-plus alias on DashScope; cheaper than max
LLM_TIMEOUT = 180  # seconds; bumped for thinking mode
LLM_RETRY = 3
LLM_RETRY_BACKOFF = 5  # base seconds; (attempt+1) * backoff

# ---- Telegram -------------------------------------------------------
# Reuse ai_agent_dailybot account per user decision 2026-05-24.
# Target chat ID per channel comes from env TELEGRAM_CHAT_ID.
TG_API = "https://api.telegram.org/bot{token}/sendMessage"
TG_PARSE_MODE = "HTML"
TG_MAX_LEN = 4096  # Telegram message limit

# ---- RSS sources ----------------------------------------------------
# arxiv categories most relevant to Spatial AI (per ontology v3 §5.2 / §5.6)
ARXIV_FEEDS = {
    "cs.RO": "http://export.arxiv.org/rss/cs.RO",   # Robotics
    "cs.CV": "http://export.arxiv.org/rss/cs.CV",   # Computer Vision (3DGS/NeRF/VGGT live here)
    "cs.AI": "http://export.arxiv.org/rss/cs.AI",   # AI foundation models
    "cs.LG": "http://export.arxiv.org/rss/cs.LG",   # Learning (for VLA / world models)
}

# Skip arxiv on weekends (no new papers; same as VLA-Handbook)
SKIP_WEEKENDS = True

# ---- Filter keywords (Layer A — broad inclusion) --------------------
# A paper passes Layer A if title or abstract contains any of these.
# Tuned for Spatial AI (per ontology §2 problem axis).
KEYWORDS_A = [
    # Foundation / SLAM
    "SLAM", "VIO", "VINS", "VSLAM", "visual odometry", "visual-inertial",
    "pose estimation", "camera pose", "bundle adjustment", "factor graph",
    # 3D representation
    "NeRF", "Gaussian splatting", "3DGS", "radiance field", "point map",
    "depth estimation", "monocular depth", "stereo", "MVS",
    # Modern feed-forward
    "feed-forward 3D", "DUSt3R", "MASt3R", "VGGT", "MapAnything",
    "foundation model", "world model",
    # VLA / action
    "VLA", "vision-language-action", "embodied AI", "manipulation",
    # Sensors / specific
    "event camera", "LiDAR-Inertial", "scene graph", "occupancy network",
    "BEV", "bird's-eye-view",
    # Tracking
    "object pose", "6-DoF", "point tracking", "multi-object tracking",
]

# ---- Filter keywords (Layer B — boost / promotion signals) ---------
# Papers with these in title get rated higher priority (⚡/🔧 vs 📖).
KEYWORDS_B_BOOST = [
    "drone", "UAV", "quadrotor", "aerial",
    "real-time", "online", "streaming",
    "production", "deployment", "field test",
    "benchmark", "EuRoC", "TUM", "KITTI",
]

# ---- Filter keywords (Layer C — reject / noise) ---------------------
# Papers with these in title are rejected outright (irrelevant).
KEYWORDS_C_REJECT = [
    "medical imaging", "medical image", "tumor", "MRI", "X-ray",
    "satellite imagery", "remote sensing",  # except for cs.RO context
    "ASR", "speech recognition", "audio classification",
    "text classification", "sentiment analysis",
    "drug discovery", "molecule", "protein folding",
]

# ---- Ontology 5-axis controlled vocabulary (v3.2) -------------------
# Single source of truth: the rating prompt, atlas coordinates, and the
# validation in rate.py all derive from this. Values are ordered where the
# axis has a natural progression (paradigm / time) so the atlas can measure
# drift along the axis over time — that ordering is the star-map's backbone.
#
# The paradigm axis is the "money axis": geometric → ... → world-model-as-policy
# traces the field's arc; watching its mass migrate is the whole point of the atlas.
AXIS_VOCAB: dict[str, list[str]] = {
    "problem": [
        "VO", "VIO", "VSLAM", "SfM", "reconstruction", "depth", "pose",
        "tracking", "mapping", "navigation", "occupancy", "VLA", "spatial-reasoning",
    ],
    "representation": [
        "sparse", "pointmap", "NeRF", "3DGS", "voxel", "BEV",
        "scene-graph", "HD-map", "mesh", "implicit-sdf", "feature-grid",
    ],
    "sensor": [
        "mono", "stereo", "RGBD", "IMU", "LiDAR", "event", "sonar",
        "4D-radar", "multi-modal",
    ],
    # ordered: geometric era → learned → hybrid → generative → the 2026 frontier
    "paradigm": [
        "geometric", "learned", "hybrid", "generative",
        "3R-SLAM-hybrid", "VLA", "world-model-as-policy",
    ],
    # ordered: classical filtering → batch → the feed-forward / streaming frontier
    "time": [
        "filter-streaming", "fixed-lag", "incremental",
        "per-scene", "feed-forward", "temporal-transformer-rolling",
    ],
}


def _axis_vocab_block() -> str:
    """Render the controlled vocab as prompt text (keeps prompt in sync with AXIS_VOCAB)."""
    lines = []
    for axis, vals in AXIS_VOCAB.items():
        lines.append(f'  - {axis}: {" / ".join(vals)}')
    return "\n".join(lines)


# ---- Rating prompt (Layer D — LLM) ----------------------------------
# 4-tier rating per VLA-Handbook convention:
#   ⚡  load-bearing breakthrough (foundation, new capability)
#   🔧  engineering value (replication / SOTA / production-ready)
#   📖  reference (survey / textbook / educational)
#   ❌  reject (not spatial AI, weak novelty, OOD)
#
# CALIBRATION (2026-07-09): the first real report rated 45/64 = 70% ⚡ — badly
# inflated. ⚡ must be RARE. Same lesson as VLA-Handbook rating v3: default to 🔧
# and reserve ⚡ for genuine paradigm / new-capability signal, not "solid paper".
RATING_PROMPT_SYSTEM = """你是 Spatial Intelligence Handbook 的論文評級員。評級要**嚴格、不通脹**。

# 4 級（預設 🔧，⚡ 稀有）

- ⚡ **範式信號 / 新能力**：開了一條新的方法軸、引入一類此前不存在的能力、或給 ontology §13
  的某個長期未解爭議一個可量化的解。**一個 arxiv 日批（幾十篇）裡通常只有 0–3 篇夠格 ⚡（≲15%）。**
  拿不準就降到 🔧。
- 🔧 **工程價值**：刷新 SOTA、可複現、production-ready、把既有範式做扎實——但**沒有**範式級創新。
  **大多數好論文屬於這裡。**
- 📖 **參考**：survey / 教學 / 重要 baseline / benchmark 或數據集本身。
- ❌ **拒絕**：離題（非 Spatial AI）/ 弱 novelty / 已被取代。

# ⚡ 反通脹紅線（以下一律**不是** ⚡，最多 🔧）

- 又一個把 VLA / 3DGS / diffusion 套到某新場景（無人機 / 某物體 / 某任務）的**應用**。
- 在某 benchmark 上刷新 SOTA 但**沿用既有範式**。
- 新硬體 / 新平台 demo，但方法無創新。
- 新 benchmark / 數據集 / 評測套件（這是 📖 或 🔧，不是 ⚡——它不解問題，它定義問題）。
- 增量改良（+X% 精度、-Y% 記憶體、更快）。
- 只在 reason 裡寫「高引用潛力 / 開創性」卻說不出**具體**新在哪條軸——降到 🔧。

⚡ 的 reason 必須具體指出**新在哪條軸、解了哪個既有做不到的事**；空泛形容詞不算理由。

# Spatial AI 範疇

SLAM / VIO / 3D recon / NeRF / 3DGS / depth / feed-forward 3D / VLA / world model /
tracking / pose / sensor fusion / spatial reasoning（aerial / drone 是 anchor embodiment）。

# 五軸座標（星圖用）

給每篇一組 ontology 五軸座標，每軸從下列**受控詞彙**選**最貼切的一個**；真的不適用才填 "n/a"：
{axis_vocab}

paradigm 軸最重要（它記錄領域從 geometric 遷往 world-model-as-policy 的漂移），盡量不要 n/a。

# 輸出（嚴格 JSON，勿加多餘欄位）

{
  "rating": "⚡" | "🔧" | "📖" | "❌",
  "reason": "一句話（中文），⚡ 須點名新在哪條軸",
  "axes": {
    "problem": "<受控詞彙之一 或 n/a>",
    "representation": "<受控詞彙之一 或 n/a>",
    "sensor": "<受控詞彙之一 或 n/a>",
    "paradigm": "<受控詞彙之一 或 n/a>",
    "time": "<受控詞彙之一 或 n/a>"
  }
}
""".replace("{axis_vocab}", _axis_vocab_block())

# ---- Daily report format --------------------------------------------
REPORT_TOP_N = 5  # top N ⚡/🔧 picks to push + write to markdown
REPORT_RETENTION_DAYS = 90  # auto-clean reports/spatial-daily/ older than N days

# ---- Weekly synthesis -----------------------------------------------
WEEKLY_TITLE = "Spatial Weekly"   # report H1 / banner label
WEEKLY_LOOKBACK_DAYS = 7        # how many days of dailies to aggregate
WEEKLY_RETENTION_WEEKS = 26     # auto-clean reports/weekly/ older than N weeks
# Forward-looking (前瞻偵察) per VLA convention — weekly = scout, not retrospective.
WEEKLY_PROMPT_SYSTEM = """你是 Spatial Intelligence Handbook 的週度前瞻偵察員。

輸入是本週每日 arxiv 評級裡的 ⚡/🔧 論文（Spatial AI 領域：SLAM / VIO / 3D recon / NeRF / 3DGS /
depth / feed-forward 3D / VLA / world model / tracking / pose / sensor / spatial reasoning，
其中 aerial / drone 是 anchor embodiment）。

週報不是日報的索引，是**前瞻判斷**。寫成 markdown，4 節：
1. **## 本週主軸** — 2-3 個反覆出現的主題/技術方向（每個 1-2 句，點名代表論文）。
2. **## 意外信號** — 1-3 個出乎意料或反共識的點（沒有就寫「本週無明顯意外」）。
3. **## 五軸熱度** — 這週論文在 5 軸（problem/representation/sensor/paradigm/time）上偏向哪裡；
   特別關注 paradigm 軸（geometric→learned→hybrid→feed-forward→world-model-as-policy）這週移動到哪。
4. **## 可證偽觀察清單** — 2-4 條**下週可檢驗**的具體預測或待觀察項（要可證偽，不要空話）。

只依據輸入論文，不要編造不存在的論文或數字。語氣精煉、判斷性強，避免堆砌。
"""

# ---- Memory / dedup -------------------------------------------------
DEDUP_FILE = STATE_DIR / "seen_arxiv_ids.json"
DEDUP_WINDOW_DAYS = 60  # don't re-rate papers seen in last 60 days

# ---- Env vars -------------------------------------------------------
def get_env(name: str, required: bool = True) -> str:
    """Return env var or raise if required."""
    v = os.environ.get(name, "")
    if required and not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def is_dry_run() -> bool:
    return os.environ.get("SPATIAL_DRY_RUN", "") == "1"


def today_str() -> str:
    import datetime
    return os.environ.get("SPATIAL_DATE", datetime.date.today().isoformat())
