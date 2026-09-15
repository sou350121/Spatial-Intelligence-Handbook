#!/usr/bin/env python3
"""check_secrets.py -- refuse to ship a credential in tracked files.

WHY THIS EXISTS
GitHub secret scanning AND push protection are both already enabled on this
repo, and both were useless here: a real DashScope API key sat in MAINTAINER.md
and docs/pulsar-integration.md from the initial skeleton commit (53ab889) until
2026-09-10 (176be4fa), on a PUBLIC repo, and GitHub raised ZERO alerts. Its
scanner simply does not know Alibaba's `sk-...` format.

That key was very likely revoked BY Alibaba's own scraping of public GitHub,
which is what killed the rating pipeline for twelve days. So the cost of this
class of mistake here is measured in weeks of lost output, not in theory.

This checks what GitHub will not. It is deliberately a small, dependency-free
allowlist of patterns we actually use, not a general secret scanner -- a broad
entropy heuristic would fire on arXiv IDs and base64 figures and get muted.

Exit 1 on a hit. Run over tracked files only; untracked scratch files are the
author's business.
"""
from __future__ import annotations

import re
import subprocess
import sys

# Patterns for credentials this project genuinely uses. Each is anchored tightly
# enough that a prose mention of a prefix ("the sk-sp- coding plan key") does not
# fire -- only a string long enough to actually BE the secret does.
PATTERNS = [
    ("DashScope / Bailian", re.compile(r"sk-[0-9a-f]{32}\b")),
    ("DashScope Coding Plan", re.compile(r"sk-sp-[0-9a-f]{32}\b")),
    ("Bailian Token Plan", re.compile(r"sk-sp-[A-Za-z0-9]\.[A-Za-z0-9]{4,}\.[A-Za-z0-9]{3,}\.[A-Za-z0-9_-]{40,}")),
    ("DeepSeek", re.compile(r"sk-[0-9a-f]{32}\b")),
    ("OpenAI / OpenRouter", re.compile(r"sk-(?:or-v1-)?[A-Za-z0-9]{40,}")),
    ("GitHub PAT", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
]

# This file necessarily contains the patterns themselves.
SKIP = {"scripts/pulsar/check_secrets.py"}


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f and f not in SKIP]


def main() -> int:
    hits = []
    for path in tracked_files():
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except (IsADirectoryError, PermissionError, FileNotFoundError):
            continue
        for label, rx in PATTERNS:
            for m in rx.finditer(text):
                s = m.group(0)
                line = text[:m.start()].count("\n") + 1
                # Show enough to locate it, never enough to use it.
                hits.append((path, line, label, s[:8] + "…" + "(%d chars)" % len(s)))

    if not hits:
        print("[secrets] PASS  no credential patterns in %d tracked files"
              % len(tracked_files()))
        return 0

    print("[secrets] FAIL  %d credential-shaped string(s) in tracked files:" % len(hits))
    for path, line, label, masked in hits:
        print("  %s:%d  %s  %s" % (path, line, label, masked))
    print("")
    print("  Do not just delete the line and push -- the value is already in the")
    print("  object store. Revoke the credential first, then remove it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
