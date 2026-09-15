#!/usr/bin/env python3.11
"""Regression check for the anti-fabrication gates. No network, no LLM, no pytest.

    python3 scripts/pulsar/test_gates.py

Two things must stay true at once, and each has broken the pipeline once:

  * The gate must CATCH fabrication. It is the only thing standing between a
    cheap model and 82 auto-committed articles.
  * The gate must not cry wolf. 2026-08-24: 6 of 7 mechanical findings false,
    fixed in e4bb9b0. 2026-08-28..09-15: the LLM arm was handed a copy of the
    paper truncated 6000 chars SHORTER than the writer's, so every
    correctly-copied number from the tail read as invented — 13 of 13 findings
    false on arXiv 2608.22896, three drafts rejected per run, zero articles for
    eighteen days. A gate that is mostly wrong gets ignored, which is worse than
    no gate; a gate that rejects everything is the same failure wearing a
    different hat.

The cases below are the concrete incidents. Keep them when narrowing the gate.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run_dissection as rd  # noqa: E402
import write_dissection as wd  # noqa: E402


def draft(*body: str) -> str:
    return "\n".join(body)


class CapInvariants(unittest.TestCase):
    """The verifier must never see less of the paper than the writer did."""

    def test_verify_cap_at_least_generation_cap(self):
        self.assertGreaterEqual(wd.VERIFY_CAP, wd.FULLTEXT_CAP)

    def test_audit_cap_at_least_generation_cap(self):
        import audit_dissections as ad
        self.assertGreaterEqual(ad.AUDIT_CAP, wd.FULLTEXT_CAP)

    def test_factcheck_is_shown_the_whole_paper(self):
        """The 2026-08-28 stall in one assertion: factcheck used to slice the
        source to [:24000] while the writer got 30000."""
        seen = {}

        def fake(system, user, api_key, **kw):
            seen["user"] = user
            return '{"verdict": "pass", "issues": []}'

        real, wd.call_qwen = wd.call_qwen, fake
        try:
            # A fact that lives past the old 24000-char slice but inside the cap.
            tail_fact = "SuperMap achieves a competitive accuracy of 55.48%"
            source = ("x" * 25000) + tail_fact + ("y" * 4000)
            wd.factcheck("草稿引用 55.48%", source, "k")
        finally:
            wd.call_qwen = real
        self.assertIn(tail_fact, seen["user"])


class MechanicalGateStillCatchesFabrication(unittest.TestCase):
    """Do not let a narrowing change turn the gate into a rubber stamp."""

    SRC = "We evaluate on ScanNet. Accuracy 55.48%. Code: https://github.com/cmu/supermap"

    def test_invented_number_is_flagged(self):
        d = draft("## 5 · 数据与评测", "SuperMap 在 ScanNet 上达到 91.37% 准确率。")
        self.assertTrue(any("91.37" in i for i in
                            wd.numeric_grounding_issues(d, self.SRC)))

    def test_invented_github_repo_is_flagged(self):
        d = draft("## 8 · GitHub-validated pitfalls",
                  "官方实现见 https://github.com/nobody/totally-made-up 。")
        self.assertTrue(any("GitHub" in i for i in
                            wd.numeric_grounding_issues(d, self.SRC)))

    def test_invented_latency_is_flagged(self):
        d = draft("## 4 · 工程视角", "| 端到端延迟 | 12.7 ms |")
        self.assertTrue(any("12.7" in i for i in
                            wd.numeric_grounding_issues(d, self.SRC)))


class MechanicalGateDoesNotCryWolf(unittest.TestCase):
    """Every case here is a measured false positive from a real audit run."""

    SRC = ("We evaluate on ScanNet. SuperMap Acc 55.48%, RayFronts Acc 56.76%. "
           "Runs on an NVIDIA RTX 4090 Laptop GPU (16GB VRAM). "
           "Project code at https://github.com/cmu/supermap")

    def test_real_number_passes(self):
        d = draft("## 5 · 数据与评测", "SuperMap Acc **55.48**,RayFronts Acc **56.76**。")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])

    def test_tail_of_paper_is_not_fabrication(self):
        """2026-09-15, arXiv 2608.22896. All of Table II/III sat at offset
        25286-30000. Checked against the writer's 30000-char view it is grounded;
        checked against a shorter view every number reads as invented. The gate is
        now handed VERIFY_CAP chars, so the tail is in scope."""
        source = ("padding. " * 5000) + self.SRC          # fact lives ~40k in
        d = draft("## 5 · 数据与评测", "SuperMap Acc **55.48**。")
        # Under the old caps the same true sentence read as a fabrication.
        self.assertTrue(wd.numeric_grounding_issues(d, source[:30000]))
        self.assertEqual(wd.numeric_grounding_issues(d, source[:wd.VERIFY_CAP]), [])

    def test_self_handbook_crossref_is_not_fabrication(self):
        """e4bb9b0: 3 of 82 dissections carry a sibling-handbook link; all 3 were
        accused. They can never appear in the paper being audited."""
        d = draft("## 8 · GitHub-validated pitfalls",
                  "参见 https://github.com/sou350121/VLA-Handbook 的对应章节。")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])

    def test_unverified_estimate_is_exempt(self):
        d = draft("## 4 · 工程视角", "| 端到端延迟 | ~33.3 ms (UNVERIFIED,本文估算) |")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])

    def test_not_reported_is_exempt(self):
        d = draft("## 4 · 工程视角", "| 峰值显存 | 论文未报告 |")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])

    def test_toy_example_numbers_are_exempt(self):
        """§3 demonstration numbers are legitimately invented and say so."""
        d = draft("## 3 · 带数字走一遍", "取 Δd = 0.42 m,log-odds 加 1.386。")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])

    def test_code_fence_is_exempt(self):
        d = draft("## 4 · 工程视角", "```", "latency_budget_ms = 8.75", "```")
        self.assertEqual(wd.numeric_grounding_issues(d, self.SRC), [])


class Plumbing(unittest.TestCase):
    def test_write_one_gates_on_verify_text_not_writer_text(self):
        """Guard the wiring itself: both gates must receive the wide fetch."""
        src = Path(rd.__file__).read_text(encoding="utf-8")
        self.assertIn("wd.numeric_grounding_issues(full, verify_text)", src)
        self.assertIn("wd.factcheck(full, verify_text, api_key)", src)
        self.assertIn("cap=wd.VERIFY_CAP", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
