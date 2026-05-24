#!/usr/bin/env python3
"""Orchestrator: collect → rate → post. Single-cron-entry runner.

Usage:
    python3 scripts/pulsar/run_daily.py

Env vars: see _config.py.

Workflow:
  1. collect.py — fetch arxiv → filter → dedup
  2. rate.py    — qwen3.5-plus rate ⚡/🔧/📖/❌, drop ❌
  3. post.py    — write reports/spatial-daily/YYYY-MM-DD.md + TG push

Exits 0 on success, 1 if any stage fails hard. Logs to stderr.
"""
from __future__ import annotations
import subprocess
import sys
import json
import time
from pathlib import Path

THIS = Path(__file__).parent


def run_stage(name: str, cmd: list[str], stdin: str | None = None) -> tuple[int, str]:
    """Run a subprocess, capturing stdout. Stderr passes through."""
    t0 = time.time()
    print(f"\n=== {name} ===", file=sys.stderr)
    result = subprocess.run(
        cmd, input=stdin, capture_output=True, text=True
    )
    # forward stderr live (already captured)
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    dt = time.time() - t0
    print(f"=== {name} done in {dt:.1f}s (exit {result.returncode}) ===", file=sys.stderr)
    return result.returncode, result.stdout


def main() -> int:
    # Stage 1: collect
    code, papers_json = run_stage("COLLECT", [sys.executable, str(THIS / "collect.py")])
    if code != 0:
        print(f"FAIL: collect exited {code}", file=sys.stderr)
        return 1

    papers = json.loads(papers_json) if papers_json.strip() else []
    if not papers:
        print(f"\nNo new papers today. Done.", file=sys.stderr)
        return 0

    # Stage 2: rate
    code, rated_json = run_stage(
        "RATE",
        [sys.executable, str(THIS / "rate.py")],
        stdin=papers_json,
    )
    if code != 0:
        print(f"FAIL: rate exited {code}", file=sys.stderr)
        return 1

    # Stage 3: post
    code, _ = run_stage(
        "POST",
        [sys.executable, str(THIS / "post.py")],
        stdin=rated_json,
    )
    if code != 0:
        print(f"FAIL: post exited {code}", file=sys.stderr)
        return 1

    print(f"\nAll stages OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
