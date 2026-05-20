# Connecting Spatial-Intelligence-Handbook to Pulsar

**Status:** Design spec. No production changes have been applied — this doc describes what to change on the Pulsar production server (`/home/admin/.openclaw/cron/jobs.json` + `/home/admin/clawd/memory/`) to retarget the existing pipeline at `spatial` as a new domain alongside `vla` and `ai_app`.

**Why:** Re-using the proven [VLA-Handbook](https://github.com/sou350121/VLA-Handbook) Pulsar pipeline beats writing a new collector. The work is config + hypothesis registry, not new code.

---

## 1 · What carries over unchanged

These pipeline pieces are domain-agnostic and run as-is once the registry knows about `spatial`:

- `scripts/_domain_loader.py` — already iterates over `memory/domains.json`
- 3-pass dedup + 350-cap RSS filter
- LLM 8-segment prompt builder with thinking mode
- DA-rebuttal pass
- Atomic write + retention windows
- Drift / calibration / cross-domain rule engine (only needs spatial hypotheses to do useful work)
- Watchdog (24 checks; will auto-extend to spatial files once they exist)
- Semantic index builder (just point it at the new memory subdir; same chunking)

The takeaway: about 80% of the lift is hypothesis content + RSS source curation, not code.

---

## 2 · Step-by-step changes on production

### Step 1 — register the domain

Add to `/home/admin/clawd/memory/domains.json`:

```json
"spatial": {
  "label": "Spatial Intelligence",
  "telegram_account": "spatial_dailybot",
  "github_repo": "sou350121/Spatial-Intelligence-Handbook",
  "github_config": "github-config-spatial.json",
  "memory_prefix": "spatial",
  "method_families_module": "_spatial_method_families.py"
}
```

### Step 2 — hypothesis registry seed (`memory/assumptions_spatial.json`)

Seed assumptions per PRD §「种子假设举例」, in the same schema as `assumptions.json`:

```json
{
  "S-001": {
    "claim": "Feed-forward 3D (VGGT lineage) will displace per-scene optimization (3DGS) as the mainstream robot spatial perception primitive within 2 years.",
    "score": 0.5,
    "confidence": "moderate",
    "counter_keywords": ["3dgs.*outperform.*vggt", "per.scene.*beats.*feed.forward"]
  },
  "S-002": {
    "claim": "Pure RGB + foundation depth keeps suppressing active sensing for manipulation, but not for outdoor drone.",
    "score": 0.5,
    "confidence": "moderate",
    "counter_keywords": ["active.*ir.*manipulation", "rgbd.*outdoor.*drone"]
  },
  "S-003": {
    "claim": "3DGS-as-simulator becomes product-ready earlier on drones than on manipulation.",
    "score": 0.5,
    "confidence": "low",
    "counter_keywords": ["splat.*sim.*manipulation.*shipping"]
  },
  "S-004": {
    "claim": "World models ship earlier as VLA training data generators than as inference-time planners.",
    "score": 0.5,
    "confidence": "moderate",
    "counter_keywords": ["world.model.*inference.*planner.*shipping"]
  }
}
```

Add 8–12 more S-* hypotheses before going live (one per `crossing/` subdirectory + one per major `embodiments/aerial/*` axis). The cross-domain engine (rule R007 in MEMORY.md) will auto-generate transfer hypotheses linking these to VLA's V-* registry.

### Step 3 — method families (`scripts/_spatial_method_families.py`)

Mirror `_vla_method_families.py`. Initial families with `FAMILY_ADDED_DATE = "2026-05-20"`:

```python
METHOD_FAMILIES = {
    # foundations
    "3dgs":                 [r"\b3dgs\b", r"3d gaussian splat", r"gaussian splatting"],
    "feed_forward_3d":      [r"vggt", r"dust3r", r"mast3r", r"\bpi3\b|π³"],
    "depth_foundation":     [r"depth anything", r"metric3d", r"foundationstereo", r"\bmoge\b"],
    "semantic_3d":          [r"lerf", r"openscene", r"3d scene graph", r"dinov2 .* 3d"],
    "world_model_decision": [r"cosmos|genie .*world model.*(decision|policy|sim)"],

    # crossing wedges
    "scale_migration":      [r"cross.scale", r"depth.foundation.*outdoor", r"scale ambiguity"],
    "vio_replacement":      [r"feed.forward.*vio", r"vggt.*slam", r"learn.*msckf"],
    "3dgs_as_sim":          [r"splat.sim", r"3dgs.*sim.*real", r"gaussian.*simulator"],

    # aerial
    "aerial_vio":           [r"aerial.*vio|drone.*vio|quadrotor.*slam"],
    "champion_racing":      [r"champion.level|drone.racing.*rl"],
    "on_board_3dgs":        [r"3dgs.*jetson|gaussian.*onboard.*drone"],
    "event_camera_aerial":  [r"event.camera.*drone|uzh.rpg.*event"],

    # marine
    "underwater_slam":      [r"underwater.*slam|aqualoc|subpipe"],
}
```

Watchdog will pick up new families automatically (per `audit-method-families.py` in scripts dir).

### Step 4 — RSS sources (`scripts/_spatial_rss_sources.py`)

Reuse VLA + AI App config layout. Initial set:

- arxiv categories: `cs.CV` (filter heavy), `cs.RO`, `cs.GR`, `eess.IV`
- venues: CVPR / ICCV / ICRA / RSS / 3DV
- blogs: NVIDIA developer, Niantic Spatial, World Labs, Skydio engineering, Apple ML, Wayve
- per-source `MAX_AGE_DAYS = 3`, journal `_MUST_INCLUDE_SOURCES = {"Science-Robotics", "IEEE-Spectrum-Robotics"}`

### Step 5 — cron jobs (use `moltbot cron add --session isolated` then `cron edit` per MEMORY.md quirk)

Mirror the VLA daily schedule, offset by 15 min to avoid concurrency with VLA/AI which already saturate 09:00–11:00 on the 3.5 GB box:

| Time | Job | Output |
|---|---|---|
| 08:00 | Spatial RSS collect | rolling 3-day arxiv + venue + blog pull |
| 08:20 | Spatial daily hotspots | `_spatial_hotspots_*.md` |
| 08:35 | Spatial daily rating | `spatial-daily-rating-out-*.json` (⚡🔧📖❌) |
| 08:50 | Spatial social intel | qwen3.5-plus with `enable_search` |
| 09:00 | Spatial SOTA / release tracker | `spatial-sota.json` |
| 09:55 | Entity tracker (extend existing) | adds spatial domain to same `entity-index.json` |
| 09:56 | Field state (extend existing) | adds `spatial-field-state-*.json` |
| 10:05 | Cross-domain v2.1 (extend existing) | adds Spatial ↔ VLA rules R008-R012 |
| 11:30, 13:15, 14:45 | Spatial Theory Deep Dive (3 slots) | written to `foundations/` or `embodiments/` per topic |
| Fri 17:00 | Spatial Weekly Deep Dive | `reports/weekly/spatial-weekly-*.md` |
| every 14d | Spatial Biweekly | `reports/biweekly/spatial-biweekly-*.md` |
| every 14d | Spatial Reflection | prediction-tracking |

⚠️ **RAM caveat:** verified production has 3.5 GB (MEMORY.md's "2 GB only" line is stale — see audit notes). Adding 7+ daily LLM jobs needs sequential timing to avoid the 05-15-style 86% RAM spike. Keep adjacent slots ≥ 15 min apart.

### Step 6 — GitHub config (`scripts/github-config-spatial.json`)

```json
{
  "owner": "sou350121",
  "repo": "Spatial-Intelligence-Handbook",
  "default_branch": "main",
  "paths": {
    "deep_dive": "foundations|embodiments|crossing|bridge-to-vla",
    "weekly":    "reports/weekly",
    "biweekly":  "reports/biweekly"
  },
  "topic_to_module_map": {
    "vggt|feed.forward.3d": "foundations/feed-forward-3d",
    "3dgs|gaussian.splat":  "foundations/3dgs-family",
    "depth.anything|moge":  "foundations/depth-foundation",
    "vio|slam.*aerial":     "embodiments/aerial/vio",
    "sensor|nir|imx":       "foundations/sensor-physics",
    "cross.embodiment":     "crossing"
  }
}
```

The deep-dive writer's `_classify_module()` reads this map to route generated articles to the right subdir, same way `Agent-Playbook`'s router does.

---

## 3 · Rollout gates

Before opening the cron firehose:

1. **Manual dry-run** — `python3 scripts/run-spatial-rss-collect.py --dry-run` should pull ≥ 20 papers and pass the keyword filter.
2. **Single hand-graded day** — run the rating script manually on a sample day; spot-check 5 ⚡ + 5 🔧 + 5 📖 + 5 ❌ for sanity.
3. **Deep-dive sample** — generate one `foundations/feed-forward-3d/<topic>_dissection.md` via the existing AI deep-dive script with `--domain spatial`. Verify it lands in the right repo path.
4. **First weekly** — schedule a Friday 17:00 weekly. Read it before publishing; do not auto-push to repo until manual QA on first 2 weeks.

Watchdog should be extended (check #25 onwards) to alarm if:
- `spatial-daily-rating-out-*.json` missing today after 09:00
- `spatial-field-state-*.json` mtime > 24h
- ⚡ ratio > 30% (over-promotion regression)

---

## 4 · Capacity / cost note

Conservative estimate, assuming the same per-job cost as VLA:

- Daily LLM tokens: ~150k input + 30k output per spatial job × 5 jobs = ~750k input / 150k output per day
- DashScope qwen3.5-plus current rate (CodingPlan Pro) — already paid flat
- Embedding cost (incremental, per new chunk): ~6 chunks/day × 400 words = 2400 tokens — negligible
- Embedding-API key issue (see Pulsar audit notes 2026-05-20): the current `sk-sp-` CodingPlan Pro key has zero embedding authorization. This blocks `Semantic Index Builder` from indexing new spatial content. Fix path: get a standard-plan DashScope key, set `DASHSCOPE_EMBED_KEY` env var on production. Until then, spatial-side semantic search will degrade the same way VLA/AI App side has since 2026-04-01.

---

## 5 · Migration timeline

A pragmatic 4-week rollout:

| Week | Milestone |
|---|---|
| W1 | Steps 1–4 (config files). No crons yet. Manual smoke-test of each script. |
| W2 | Step 5: 5 daily cron jobs, RSS + rating only. Disable deep-dive + weekly. |
| W3 | Enable deep-dive cron, single slot 11:30. Watch quality drift for 7 days. |
| W4 | Enable remaining deep-dive slots + Friday weekly. First biweekly target ~W6. |

---

## 6 · Things this doc deliberately does **not** decide

- Whether spatial gets its own Telegram channel or shares with VLA (defer until first weekly is ready)
- Whether to fork or branch the Pulsar codebase (almost certainly not — config-only changes by design)
- Long-term split into a standalone repo (per main README, only after 50+ deep dives land)

These are deferred to the operator. The pipeline integration above is reversible — every change is a config file or cron job that can be disabled.
