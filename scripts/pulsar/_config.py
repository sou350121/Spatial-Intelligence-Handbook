"""Spatial Intelligence Handbook — Pulsar pipeline config (Phase 1).

Standalone version: runs anywhere with Python 3.9+ + the 4 env vars below.
Future: integrate with Pulsar's `memory/domains.json` multi-domain registry.

Env vars required:
    DASHSCOPE_API_KEY   — Aliyun qwen3.5-plus (OpenAI-compatible)
    TELEGRAM_BOT_TOKEN  — reuse ai_agent_dailybot token
    TELEGRAM_CHAT_ID    — new target for spatial (user provides)

Optional:
    SPATIAL_DRY_RUN=1   — collect + rate, skip TG + reports write
    SPATIAL_DATE        — override "today" in YYYY-MM-DD (for backfill)
"""
from __future__ import annotations
import os
from pathlib import Path

# ---- Paths ----------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = REPO_ROOT / "scripts" / "pulsar" / "state"
REPORTS_DIR = REPO_ROOT / "reports" / "spatial-daily"

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

# ---- Rating prompt (Layer D — LLM) ----------------------------------
# 4-tier rating per VLA-Handbook convention:
#   ⚡  load-bearing breakthrough (foundation, new capability)
#   🔧  engineering value (replication / SOTA / production-ready)
#   📖  reference (survey / textbook / educational)
#   ❌  reject (not spatial AI, weak novelty, OOD)
RATING_PROMPT_SYSTEM = """你是 Spatial Intelligence Handbook 的論文評級助手。

每篇 paper 用 4 級之一評：
- ⚡ load-bearing breakthrough（範式信號 / 新能力 / 高引用潛力）
- 🔧 engineering value（複現 / SOTA / production-ready，但無範式創新）
- 📖 reference（survey / 教學 / 重要 baseline）
- ❌ reject（離題 / 弱 novelty / 已被取代）

評級基於：
1. 是否屬於 Spatial AI 範疇（SLAM / VIO / 3D recon / NeRF / 3DGS / depth / VLA / world model / tracking / pose / sensor / spatial reasoning）
2. 是否有 reproducibility（GitHub repo / 數據集 / 訓練 recipe）
3. 是否解 known limitation 或開新方向
4. 跟 ontology §13 controversies 的關係（是否觸及未解問題）

回答格式（嚴格 JSON）：
{
  "rating": "⚡" | "🔧" | "📖" | "❌",
  "reason": "一句話評理由（中文）",
  "tags": ["axis-1 標籤", ...]  // 從 5 軸選：problem-axis / representation-axis / sensor-axis / paradigm-axis / time-axis
}
"""

# ---- Daily report format --------------------------------------------
REPORT_TOP_N = 5  # top N ⚡/🔧 picks to push + write to markdown
REPORT_RETENTION_DAYS = 90  # auto-clean reports/spatial-daily/ older than N days

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
