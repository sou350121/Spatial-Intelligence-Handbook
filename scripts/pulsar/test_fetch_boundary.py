"""Offline regression tests for write_one's source-unavailable boundary.

Run directly with Python; no network, credentials, or model provider is needed.
The real fetcher is used except when testing its return contract explicitly.
"""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_dissection as rd
import write_dissection as wd
import _llm


CAND = dict(id='2610.12345', title='Offline Example', axes={}, rating='R')
ZONE = 'foundations/feed-forward-3d'
DRAFT = '# Offline draft\n\nSource-grounded text.\n'
HTML = b'<title>Fetched title</title><p>Source body for offline verification.</p>'


def http_error():
    return urllib.error.HTTPError('https://arxiv.org/html/2610.12345',
                                  404, 'Not Found', {}, None)


def unavailable_errors():
    return [http_error(), urllib.error.URLError(ConnectionRefusedError('offline')),
            urllib.error.URLError(socket.timeout('wrapped timeout')),
            TimeoutError('direct timeout')]


def unexpected_errors():
    # Message content is deliberately misleading: types define the boundary.
    return [kind('HTTP Error 404: programming failure') for kind in
            (RuntimeError, ValueError, TypeError, AttributeError, OSError, PermissionError)]


def forbidden(*args, **kwargs):
    raise AssertionError('Live network/model call forbidden in offline tests')


class FetchBoundary(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        destination = self.root / ZONE
        destination.mkdir(parents=True)
        (destination / 'README.md').write_bytes(b'# Manual index\n')
        self.article = destination / 'offline_example_dissection.md'
        self.stack.enter_context(patch.object(rd, 'REPO', self.root))
        self.opener = self.stack.enter_context(
            patch.object(urllib.request, 'urlopen', side_effect=forbidden))
        self.stack.enter_context(patch.object(socket, 'create_connection', side_effect=forbidden))
        self.stack.enter_context(patch.object(socket.socket, 'connect', side_effect=forbidden))
        self.stack.enter_context(patch.object(_llm, 'chat', side_effect=forbidden))
        self.model = self.stack.enter_context(patch.object(wd, 'call_qwen', side_effect=forbidden))
        self.classifier = self.stack.enter_context(patch.object(rd, 'classify_zone', side_effect=forbidden))
        self.stderr = io.StringIO()
        self.stack.enter_context(redirect_stderr(self.stderr))

    def response(self, body=HTML):
        response = Mock()
        response.read.return_value = body
        return response

    def qualify(self):
        self.opener.side_effect = None
        self.opener.return_value = self.response()
        self.classifier.side_effect = None
        self.classifier.return_value = ZONE
        self.model.side_effect = None
        self.model.return_value = DRAFT
        # These deterministic gate verdicts isolate retry and placement semantics;
        # the pre-existing suites test the actual quality checks themselves.
        self.guard = self.stack.enter_context(patch.object(wd, 'structural_guard', return_value=[]))
        self.numeric = self.stack.enter_context(patch.object(wd, 'numeric_grounding_issues', return_value=[]))
        self.factcheck = self.stack.enter_context(patch.object(wd, 'factcheck', return_value=(True, [])))

    def assert_no_generation(self):
        self.classifier.assert_not_called()
        self.model.assert_not_called()
        self.assertFalse(self.article.exists())

    def assert_escapes(self, error):
        with self.assertRaises(type(error)) as raised:
            rd.write_one(CAND, '', False)
        self.assertIs(raised.exception, error)
        self.assert_no_generation()
        self.assertNotIn('full text fetch failed', self.stderr.getvalue())

    def test_real_fetch_open_and_read_source_unavailable(self):
        for layer in ('open', 'read'):
            for error in unavailable_errors():
                with self.subTest(layer=layer, error=type(error).__name__):
                    response = self.response()
                    self.opener.side_effect = error if layer == 'open' else None
                    self.opener.return_value = response
                    if layer == 'read':
                        response.read.side_effect = error
                    self.assertIsNone(rd.write_one(CAND, '', False))
                    self.assert_no_generation()
                    self.assertIn('full text fetch failed', self.stderr.getvalue())
                    if layer == 'read':
                        response.read.assert_called_once_with()
        self.assertEqual(self.opener.call_count, 8)

    def test_unexpected_fetch_errors_escape_even_when_message_says_404(self):
        for error in unexpected_errors():
            with self.subTest(error=type(error).__name__), \
                 patch.object(wd, 'fetch_fulltext', side_effect=error):
                self.assert_escapes(error)

    def test_real_fetch_unexpected_open_and_read_errors_escape(self):
        for layer in ('open', 'read'):
            for error in unexpected_errors():
                with self.subTest(layer=layer, error=type(error).__name__):
                    response = self.response()
                    self.opener.side_effect = error if layer == 'open' else None
                    self.opener.return_value = response
                    if layer == 'read':
                        response.read.side_effect = error
                    self.assert_escapes(error)

    def test_real_fetch_decode_failure_escapes(self):
        error = ValueError('decoder implementation bug')
        data = Mock()
        data.decode.side_effect = error
        self.opener.side_effect = None
        self.opener.return_value = self.response(data)
        self.assert_escapes(error)

    def test_real_fetch_invalid_parser_input_escapes(self):
        data = Mock()
        data.decode.return_value = None
        self.opener.side_effect = None
        self.opener.return_value = self.response(data)
        with self.assertRaises(TypeError):
            rd.write_one(CAND, '', False)
        self.assert_no_generation()

    def test_real_fetch_parser_exception_escapes(self):
        self.opener.side_effect = None
        self.opener.return_value = self.response()
        error = RuntimeError('parser bug mentioning 404')
        with patch.object(wd.re, 'search', side_effect=error):
            self.assert_escapes(error)

    def test_invalid_fetch_return_shapes_escape(self):
        for value, kind in [(None, TypeError), (('only title',), ValueError),
                            (('title', 'body', 'extra'), ValueError),
                            (('title', None), TypeError), (('title', object()), TypeError)]:
            with self.subTest(value=value), patch.object(wd, 'fetch_fulltext', return_value=value):
                with self.assertRaises(kind):
                    rd.write_one(CAND, '', False)
                self.assert_no_generation()
        self.assertNotIn('full text fetch failed', self.stderr.getvalue())

    def test_unpacking_is_outside_source_boundary(self):
        for error in unavailable_errors() + unexpected_errors():
            class BadResult:
                def __iter__(self):
                    raise error
            with self.subTest(error=type(error).__name__), \
                 patch.object(wd, 'fetch_fulltext', return_value=BadResult()):
                self.assert_escapes(error)

    def test_verify_text_slicing_is_outside_source_boundary(self):
        for error in unavailable_errors() + unexpected_errors():
            class BadText:
                def __getitem__(self, key):
                    raise error
            with self.subTest(error=type(error).__name__), \
                 patch.object(wd, 'fetch_fulltext', return_value=('Title', BadText())):
                self.assert_escapes(error)

    def test_main_allows_next_candidate_after_unavailable_source(self):
        self.qualify()
        for error in unavailable_errors():
            with self.subTest(error=type(error).__name__), ExitStack() as stack:
                self.opener.side_effect = [error, self.response()]
                for call in (self.model, self.classifier, self.factcheck):
                    call.reset_mock()
                second = {**CAND, 'id': '2610.54321'}
                pick = stack.enter_context(patch.object(wd, 'pick_candidate', side_effect=[CAND, second]))
                stack.enter_context(patch.object(rd, 'covered_ids', return_value=set()))
                stack.enter_context(patch.object(rd, 'covered_repr', return_value={}))
                stack.enter_context(patch.object(rd, 'get_env', return_value=''))
                stack.enter_context(patch.object(sys, 'argv', ['run_dissection', '--count', '2']))
                out = stack.enter_context(redirect_stdout(io.StringIO()))
                self.assertEqual(rd.main(), 0)
                self.assertEqual(out.getvalue(), f'path={ZONE}/offline_example_dissection.md\n')
                self.assertEqual(pick.call_count, 2)
                self.assertIn(second['id'], pick.call_args.args[1])
                for call in (self.model, self.classifier, self.factcheck):
                    self.assertEqual(call.call_count, 1)
                self.assertTrue(self.article.exists())
                self.article.unlink()

    def test_success_preserves_bytes_and_distinct_writer_verifier_caps(self):
        self.qualify()
        with patch.object(wd, 'FULLTEXT_CAP', 8), patch.object(wd, 'VERIFY_CAP', 28), \
             patch.object(wd, 'fetch_fulltext', wraps=wd.fetch_fulltext) as fetch:
            self.assertEqual(rd.write_one(CAND, '', False), f'{ZONE}/offline_example_dissection.md')
        fetch.assert_called_once_with(CAND['id'], cap=28)
        # Compute the actual 28-character real-fetch view independently.
        source = 'Fetched title Source body for offline verification.'[:28]
        self.assertTrue(self.model.call_args.args[1].endswith(source[:8]))
        self.assertEqual(self.numeric.call_args.args[1], source)
        self.assertEqual(self.factcheck.call_args.args[1], source)
        expected = rd.safe_markdown(wd.ontology_header({}) + rd.safe_markdown(DRAFT.strip())
                                   + f'\n\n<!-- source: https://arxiv.org/abs/{CAND["id"]} -->\n')
        self.assertEqual(self.article.read_bytes(), expected.replace('\n', os.linesep).encode('utf-8'))
        self.assertEqual((self.root / ZONE / 'README.md').read_bytes(), b'# Manual index\n')
        self.opener.assert_called_once()
        self.assertEqual(self.opener.call_args.kwargs, {'timeout': 40})

    def test_model_failures_escape_at_each_stage(self):
        self.qualify()
        for call in (self.classifier, self.model, self.factcheck):
            error = _llm.LLMError('offline model failure')
            with self.subTest(stage=call):
                previous = call.side_effect
                call.side_effect = error
                try:
                    with self.assertRaises(_llm.LLMError) as raised:
                        rd.write_one(CAND, '', False)
                    self.assertIs(raised.exception, error)
                    self.assertFalse(self.article.exists())
                finally:
                    call.side_effect = previous
        self.assertNotIn('full text fetch failed', self.stderr.getvalue())

    def test_quality_rejections_still_stop_after_three_attempts(self):
        self.qualify()
        for stage in ('guard', 'numeric', 'factcheck'):
            for call in (self.model, self.guard, self.numeric, self.factcheck):
                call.reset_mock()
            target = getattr(self, stage)
            verdict = (False, ['rejected']) if stage == 'factcheck' else ['rejected']
            with self.subTest(stage=stage):
                previous = target.return_value
                target.return_value = verdict
                try:
                    self.assertIsNone(rd.write_one(CAND, '', False))
                    self.assertEqual(self.model.call_count, 3)
                    self.assertEqual(target.call_count, 3)
                    self.assertFalse(self.article.exists())
                    if stage == 'guard':
                        self.numeric.assert_not_called()
                    if stage != 'factcheck':
                        self.factcheck.assert_not_called()
                finally:
                    target.return_value = previous

    def test_existing_article_is_preserved(self):
        self.qualify()
        original = b'EXISTING manual article\r\n'
        self.article.write_bytes(original)
        self.assertIsNone(rd.write_one(CAND, '', False))
        self.assertEqual(self.article.read_bytes(), original)
        self.assertEqual(self.model.call_count, 1)
        self.factcheck.assert_called_once()

    def test_destination_permission_error_escapes(self):
        self.qualify()
        error = PermissionError('destination denied')
        with patch.object(Path, 'open', side_effect=error) as opening:
            with self.assertRaises(PermissionError) as raised:
                rd.write_one(CAND, '', False)
        self.assertIs(raised.exception, error)
        opening.assert_called_once_with('x', encoding='utf-8')
        self.assertFalse(self.article.exists())
        self.factcheck.assert_called_once()

    def test_negative_control_rejects_swallowing_wrapper(self):
        real_write_one = rd.write_one
        def swallowing(*args, **kwargs):
            try:
                return real_write_one(*args, **kwargs)
            except Exception:  # Deliberately invalid implementation, test-only.
                return None
        # The same assertion used above must fail under a swallowing mutation,
        # even though that mutation still passes the intended unavailable skips.
        with patch.object(rd, 'write_one', side_effect=swallowing):
            self.opener.side_effect = http_error()
            self.assertIsNone(rd.write_one(CAND, '', False))
            self.opener.side_effect = TimeoutError('source timeout')
            self.assertIsNone(rd.write_one(CAND, '', False))
            self.stderr.seek(0)
            self.stderr.truncate()
            self.opener.side_effect = RuntimeError('HTTP Error 404: bug')
            with self.assertRaises(AssertionError):
                self.assert_escapes(self.opener.side_effect)


if __name__ == '__main__':
    unittest.main(verbosity=2)
