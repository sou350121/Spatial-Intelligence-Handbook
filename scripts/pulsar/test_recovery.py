"""Regression tests for October recovery. No network or model calls."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_dissection as rd
import write_dissection as wd
import _config
import _llm


class Verification(unittest.TestCase):
    def test_unavailable_factcheck_blocks_publication(self):
        with patch.object(wd, 'call_qwen', side_effect=RuntimeError('offline')):
            with self.assertRaises(_llm.LLMError): wd.factcheck('draft', 'source', '')

    def test_invalid_or_contradictory_verdict_blocks_publication(self):
        for value in ['not json', '{}', '{"verdict":"pass"}',
                      '{"verdict":"pass","issues":["invented"]}',
                      '{"verdict":"pass","issues":"none"}']:
            with self.subTest(value=value), patch.object(wd, 'call_qwen', return_value=value):
                with self.assertRaises(_llm.LLMError): wd.factcheck('draft', 'source', '')

    def test_whole_draft_is_checked(self):
        draft = 'x' * 13000 + 'TAIL_CLAIM'
        with patch.object(wd, 'call_qwen', return_value='{"verdict":"pass","issues":[]}') as call:
            self.assertTrue(wd.factcheck(draft, 'source', '')[0])
            self.assertIn('TAIL_CLAIM', call.call_args.args[1])

    def test_writer_and_verifier_get_same_fulltext_capacity(self):
        self.assertEqual(wd.FULLTEXT_CAP, wd.VERIFY_CAP)

    def test_no_protected_zone_can_be_selected(self):
        self.assertNotIn('foundations/sensor-physics', rd.ZONES)
        self.assertFalse(any(z in rd.ZONES for z in ['embodiments/aerial', 'embodiments/driving', 'embodiments/marine']))


class Placement(unittest.TestCase):
    CAND = {'id': '2610.12345', 'axes': {}, 'title': 'Test Paper', 'rating': '🔧'}
    ZONE = 'foundations/feed-forward-3d'

    def setup_tree(self, root):
        p = root / self.ZONE; p.mkdir(parents=True)
        (p / 'README.md').write_text('# Manual index\n')
        return p

    def mocks(self, root):
        return [patch.object(rd, 'REPO', root), patch.object(rd, 'classify_zone', return_value=self.ZONE),
                patch.object(wd, 'fetch_fulltext', return_value=('Test Paper', 'SOURCE')),
                patch.object(wd, 'structural_guard', return_value=[]),
                patch.object(wd, 'numeric_grounding_issues', return_value=[])]

    def test_missing_fulltext_is_nonfatal_and_spends_no_llm_call(self):
        with patch.object(wd, 'fetch_fulltext', side_effect=RuntimeError('HTTP Error 404: Not Found')), \
             patch.object(rd, 'classify_zone') as classify:
            self.assertIsNone(rd.write_one(self.CAND, '', False)); classify.assert_not_called()

    def test_existing_article_and_manual_index_are_preserved(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d); p = self.setup_tree(root)
            article = p / 'test_paper_dissection.md'; article.write_text('IMPORTANT EXISTING ARTICLE')
            for mock in self.mocks(root): stack.enter_context(mock)
            stack.enter_context(patch.object(wd, 'call_qwen', return_value='# New draft'))
            stack.enter_context(patch.object(wd, 'factcheck', return_value=(True, [])))
            self.assertIsNone(rd.write_one(self.CAND, '', False))
            self.assertEqual(article.read_text(), 'IMPORTANT EXISTING ARTICLE')
            self.assertEqual((p / 'README.md').read_text(), '# Manual index\n')

    def test_factcheck_feedback_reaches_next_attempt(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d); self.setup_tree(root)
            for mock in self.mocks(root): stack.enter_context(mock)
            call = stack.enter_context(patch.object(wd, 'call_qwen', return_value='# Draft'))
            stack.enter_context(patch.object(wd, 'factcheck', side_effect=[(False, ['actual RMSE is 0.0440 m']), (True, [])]))
            self.assertIsNotNone(rd.write_one(self.CAND, '', False))
            self.assertIn('actual RMSE is 0.0440 m', call.call_args_list[1].args[1])

    def test_single_ungrounded_claim_blocks_placement(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root = Path(d); p = self.setup_tree(root)
            for mock in self.mocks(root): stack.enter_context(mock)
            stack.enter_context(patch.object(wd, 'call_qwen', return_value='# Draft'))
            stack.enter_context(patch.object(wd, 'numeric_grounding_issues', return_value=['number not in source: 91.37%']))
            check = stack.enter_context(patch.object(wd, 'factcheck'))
            self.assertIsNone(rd.write_one(self.CAND, '', False)); check.assert_not_called()
            self.assertEqual(list(p.glob('*_dissection.md')), [])

    def test_protected_destination_rejected_before_writing(self):
        with patch.object(rd, 'classify_zone', return_value='foundations/sensor-physics'), \
             patch.object(wd, 'fetch_fulltext', return_value=('Test', 'SOURCE')), \
             patch.object(wd, 'call_qwen') as call:
            with self.assertRaises(ValueError): rd.write_one(self.CAND, '', False)
            call.assert_not_called()


class Workflow(unittest.TestCase):
    def test_supported_official_rss_host(self):
        self.assertTrue(all(u.startswith('https://rss.arxiv.org/rss/') for u in _config.ARXIV_FEEDS.values()))

    def run_pipeline(self, code, message):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); fake = p / 'python3'
            fake.write_text('#!/bin/sh\ncase "$1" in *test_gates.py|*test_recovery.py) exit 0;; esac\nprintf "%s\\n" "' + message + '"\nexit ' + str(code) + '\n')
            fake.chmod(0o755)
            source = (rd.REPO / '.github/workflows/pulsar-spatial-dissection.yml').read_text()
            block = source.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
            block = '\n'.join(line[10:] if line.startswith('          ') else line for line in block.splitlines())
            block = block.replace('/tmp/dissect.log', str(p / 'log'))
            import os
            return subprocess.run(['/bin/bash', '-e', '-c', block], env={**os.environ, 'PATH': d + ':/usr/bin:/bin', 'DISSECTIONS_PER_DAY': '3'}, capture_output=True, text=True).returncode

    def test_paper_http404_cannot_discard_a_successful_batch(self):
        self.assertEqual(self.run_pipeline(0, 'skip: full text fetch failed (HTTP Error 404: Not Found); placed=1'), 0)

    def test_real_llm_failure_is_not_swallowed(self):
        self.assertEqual(self.run_pipeline(7, 'LLMError: all providers failed'), 7)


class MdxAndArchive(unittest.TestCase):
    def test_old_and_new_ontology_formats_have_identical_values(self):
        sys.path.insert(0,str(rd.REPO/'scripts'))
        import query_ontology as query
        from _ontology_header import format_header
        block='<!-- ontology-5axis\nproblem: reconstruction\nrepresentation: 3dgs\nsensor: mono\nparadigm: learned\ntime: streaming\n-->'
        self.assertEqual(query.parse_header(block),query.parse_header(format_header(block)))
        self.assertIsNone(query.parse_header(format_header(block.replace('sensor: mono\n',''))))

    def test_invalid_metadata_wrappers_are_rejected(self):
        sys.path.insert(0,str(rd.REPO/'scripts'))
        from _ontology_header import get_header_block
        for s in ['<!-- ontology-5axis\nproblem: x', '[//]: # "<!-- ontology-5axis\nproblem: x\n-->', '[//]: # "<!-- wrong-marker -->"']:
            self.assertIsNone(get_header_block(s))
    def test_ontology_and_source_metadata_comments_are_preserved(self):
        from _mdx_safe import safe_markdown
        s='<!-- ontology-5axis\nproblem: reconstruction\n-->\nText <1000\n<!-- source: https://arxiv.org/abs/2610.12345 -->\n'
        actual=safe_markdown(s)
        self.assertIn('<!-- ontology-5axis\nproblem: reconstruction\n-->',actual)
        self.assertIn('[//]: # "<!-- source: https://arxiv.org/abs/2610.12345 -->"',actual)
        self.assertIn('Text &lt;1000',actual)
        self.assertEqual(safe_markdown(actual),actual)

    def test_existing_math_is_not_rewritten(self):
        from _mdx_safe import safe_markdown
        s='Inline $o_{s,t}<\\tau$ and block\n$$\nx_{t+1}={A}x_t\n$$\n'
        self.assertEqual(safe_markdown(s),s)

    def test_html_line_breaks_keep_their_meaning(self):
        from _mdx_safe import safe_markdown
        self.assertEqual(safe_markdown('first<br>second'), 'first<br />second')
    def test_less_than_number_is_rendered_as_text(self):
        from _mdx_safe import safe_markdown
        self.assertEqual(safe_markdown('若在 <1000 帧有效。'), '若在 &lt;1000 帧有效。')

    def test_braces_cannot_become_javascript(self):
        from _mdx_safe import safe_markdown
        self.assertEqual(safe_markdown('集合 {x, y}'), '集合 &#123;x, y&#125;')

    def test_inline_code_and_fenced_code_are_unchanged(self):
        from _mdx_safe import safe_markdown
        s='`x < 1 {a}`\n```python\nx = {1: 2}\nassert x < 3\n```\n'
        self.assertEqual(safe_markdown(s),s)

    def test_tilde_fences_and_long_inline_delimiters(self):
        from _mdx_safe import safe_markdown
        s='``use `x < 1` here``\n~~~text\n{x} <1\n~~~\n'
        self.assertEqual(safe_markdown(s),s)

    def test_escape_is_idempotent_and_preserves_visible_text(self):
        from _mdx_safe import safe_markdown
        import html
        s='Threshold <1 GB and set {x}; already &lt;3%'
        escaped=safe_markdown(s)
        self.assertEqual(safe_markdown(escaped),escaped)
        self.assertEqual(html.unescape(escaped),html.unescape(s))

    def test_report_index_preserves_manual_prefix_and_suffix(self):
        import sync_report_index as ri
        old='MANUAL BEFORE\n'+ri.START+'\nold auto\n'+ri.END+'\nMANUAL AFTER\n'
        new=ri.update(old,ri.START+'\nnew auto\n'+ri.END)
        self.assertTrue(new.startswith('MANUAL BEFORE\n'));self.assertTrue(new.endswith('\nMANUAL AFTER\n'))

    def test_malformed_managed_region_is_rejected(self):
        import sync_report_index as ri
        for text in [ri.START,ri.END+ri.START,ri.START+ri.START+ri.END]:
            with self.subTest(text=text), self.assertRaises(ValueError):ri.update(text,'new')

    def test_archive_links_reference_real_files(self):
        import sync_report_index as ri
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);folder=p/'reports/weekly';folder.mkdir(parents=True)
            (folder/'2026-W42.md').write_text('# Weekly')
            self.assertIn('./weekly/2026-W42.md',ri.render(p))
            self.assertNotIn('2026-W41',ri.render(p))

    def test_true_post_dry_run_writes_nothing(self):
        import post
        with patch.object(post,'is_dry_run',return_value=True),patch.object(post,'today_str',return_value='2026-10-18'), \
             patch.object(sys,'argv',['post']),patch.object(sys,'stdin',__import__('io').StringIO(json.dumps([{'id':'2610.12345','title':'Test','link':'https://arxiv.org/abs/2610.12345','rating':'📖','reason':'Test'}]))), \
             patch.object(post,'write_report') as write,patch.object(post.atlas,'upsert') as atlas,patch.object(post,'prune_old_reports') as prune,patch.object(post,'push_to_telegram') as telegram:
            self.assertEqual(post.main(),0)
            for call in [write,atlas,prune,telegram]:call.assert_not_called()

    def test_existing_daily_report_cannot_be_overwritten(self):
        import post
        with tempfile.TemporaryDirectory() as d,patch.object(post,'REPORTS_DIR',Path(d)):
            p=Path(d)/'2026-10-16.md';p.write_text('IMPORTANT REPORT')
            with self.assertRaises(FileExistsError):post.write_report('replacement','2026-10-16')
            self.assertEqual(p.read_text(),'IMPORTANT REPORT')

    def test_existing_weekly_report_spends_no_model_call(self):
        import run_weekly as weekly
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'2026-W42.md';p.write_text('IMPORTANT REPORT')
            with patch.object(weekly,'WEEKLY_DIR',Path(d)),patch.object(weekly,'today_str',return_value='2026-10-16'),patch.object(weekly,'is_dry_run',return_value=False),patch.object(weekly,'call_qwen') as call:
                self.assertEqual(weekly.main(),0);call.assert_not_called()
            self.assertEqual(p.read_text(),'IMPORTANT REPORT')

    def test_weekly_ungrounded_draft_is_never_published(self):
        import run_weekly as weekly
        with tempfile.TemporaryDirectory() as d,patch.object(weekly,'WEEKLY_DIR',Path(d)), \
             patch.object(weekly,'today_str',return_value='2026-10-16'),patch.object(weekly,'is_dry_run',return_value=False), \
             patch.object(weekly,'collect_week',return_value=(['SOURCE'],[Path('2026-10-16.md')])),patch.object(weekly,'load_ontology_anchor',return_value=''), \
             patch.object(weekly,'call_qwen',return_value='FABRICATED DRAFT'),patch.object(weekly,'get_env',return_value=''),patch.object(weekly,'grounding_issues',return_value=['invented arxiv ID']):
            with self.assertRaises(ValueError):weekly.main()
            self.assertEqual(list(Path(d).glob('*.md')),[])


if __name__ == '__main__': unittest.main(verbosity=2)
