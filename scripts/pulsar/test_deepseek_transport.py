#!/usr/bin/env python3
"""Offline DeepSeek transport regressions: synthetic config, keys and HTTP only."""
from __future__ import annotations

import contextlib
import http.client
import importlib.util
import io
import json
import socket
import sys
import traceback
import types
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

DIRECTORY = Path(__file__).resolve().parent
CONFIG = types.ModuleType("_config")
for name, value in {
    "DEEPSEEK_MAX_TOKENS": 65536,
    "DEEPSEEK_MODEL": "deepseek-flash",
    "DEEPSEEK_URL": "https://api.deepseek.com/chat/completions",
    "LLM_PROVIDER": "deepseek",
    "LLM_RETRY": 3,
    "LLM_RETRY_BACKOFF": 5,
    "LLM_TIMEOUT": 10,
}.items():
    setattr(CONFIG, name, value)

# Do not import live configuration or inspect the caller's credentials.
with patch.dict(sys.modules, {"_config": CONFIG}):
    spec = importlib.util.spec_from_file_location("offline_llm", DIRECTORY / "_llm.py")
    llm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(llm)
import _deepseek_http as http_helper

SECRET = "SYNTHETIC_KEY_DO_NOT_LOG"
BODY = "SYNTHETIC_BODY_DO_NOT_LOG"
EXCEPTION = "SYNTHETIC_EXCEPTION_DO_NOT_LOG"
TEXT = "SYNTHETIC_MODEL_TEXT_DO_NOT_LOG"


def envelope(content="answer", finish="stop", **message_fields):
    return {"choices": [{"finish_reason": finish,
                         "message": {"content": content, **message_fields}}]}


class Response(io.BytesIO):
    status = 200

    def __init__(self, value, *, raw=False, piece_size=None):
        super().__init__(value if raw else json.dumps(value).encode("utf-8"))
        self.read_sizes = []
        self.piece_size = piece_size

    def read(self, size=-1):
        self.read_sizes.append(size)
        if size < 0:
            raise AssertionError("unbounded response read")
        return super().read(min(size, self.piece_size) if self.piece_size else size)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict("os.environ", {"DEEPSEEK_API_KEY": SECRET}, clear=True))
        # Any accidentally unmocked dispatch fails locally, before DNS or connect.
        self.stack.enter_context(patch("socket.getaddrinfo", side_effect=AssertionError("network disabled")))
        self.stack.enter_context(patch("socket.socket.connect", side_effect=AssertionError("network disabled")))
        self.urlopen = self.stack.enter_context(patch("urllib.request.urlopen", side_effect=AssertionError("legacy dispatch")))
        self.now = 0.0
        self.stack.enter_context(patch.object(llm.time, "monotonic", side_effect=lambda: self.now))
        self.sleeps = []
        self.stack.enter_context(patch.object(llm.time, "sleep", side_effect=self.sleep))
        self.actions = []
        self.calls = []
        self.budgets = []
        self.opener = self.stack.enter_context(patch.object(llm, "deepseek_opener", side_effect=self.make_opener))
        llm.LAST_MODEL = ""

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.now += delay

    def make_opener(self, timeout):
        self.budgets.append(timeout)
        return Mock(open=self.dispatch)

    def dispatch(self, request, *, timeout):
        self.calls.append((request, timeout))
        action = self.actions.pop(0) if self.actions else Response(envelope())
        if isinstance(action, Exception):
            raise action
        if callable(action):
            return action(timeout)
        return action

    def post(self, timeout=10, **kwargs):
        values = {"url": llm.DEEPSEEK_URL, "api_key": SECRET,
                  "payload": {"model": "deepseek-flash"}, "timeout": timeout,
                  "label": TEXT}
        values.update(kwargs)
        return llm._post(**values)

    def fail_code(self, result, code):
        self.assertEqual(result, {"ok": False, "error": code})
        self.assertLess(len(json.dumps(result)), 100)

    def http_error(self, code):
        body = Mock(spec=io.BytesIO)
        body.read.side_effect = AssertionError("error body must not be read")
        return urllib.error.HTTPError(llm.DEEPSEEK_URL, code, BODY, {}, body), body

    def test_missing_key_does_not_use_legacy_key(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(llm.LLMError, "missing_deepseek_key"):
            llm.chat([], qwen_key=SECRET, qwen_model="qwen-plus")
        self.opener.assert_not_called()
        self.urlopen.assert_not_called()

    def test_legacy_key_is_never_looked_up(self):
        with patch.object(llm.os.environ, "get", side_effect=lambda name, default="": SECRET if name == "DEEPSEEK_API_KEY" else self.fail("unexpected key lookup")):
            self.assertEqual(llm.chat([], qwen_key="old"), "answer")
            self.assertEqual(llm.active_model(), "deepseek-flash")

    def test_other_provider_is_an_error_without_dispatch(self):
        for provider in ("qwen", "openai", "", None):
            with self.subTest(provider=provider), patch.object(llm, "LLM_PROVIDER", provider):
                with self.assertRaisesRegex(llm.LLMError, "unsupported_provider"):
                    llm.chat([], qwen_key=SECRET)
        self.opener.assert_not_called()

    def test_non_deepseek_model_is_an_error_without_dispatch(self):
        for model in ("qwen-plus", "deepseek-", "deepseek-flash\n", None, 1):
            with self.subTest(model=model), patch.object(llm, "DEEPSEEK_MODEL", model):
                with self.assertRaisesRegex(llm.LLMError, "invalid_model"):
                    llm.chat([], qwen_key=SECRET)
        self.opener.assert_not_called()

    def test_post_checks_destination_before_credentials_dispatch(self):
        for url in ("https://evil.invalid/chat/completions", "http://api.deepseek.com/chat/completions",
                    llm.DEEPSEEK_URL + "?secret=x", llm.DEEPSEEK_URL + "#x",
                    "https://api.deepseek.com/v1/chat/completions"):
            with self.subTest(url=url):
                self.fail_code(self.post(url=url), "invalid_destination")
        self.opener.assert_not_called()

    def test_configured_destination_cannot_redirect_transport(self):
        with patch.object(llm, "DEEPSEEK_URL", "https://evil.invalid/chat/completions"):
            with self.assertRaisesRegex(llm.LLMError, "invalid_destination"):
                llm.chat([])
        self.opener.assert_not_called()

    def test_invalid_request_model_and_key(self):
        self.fail_code(self.post(payload={"model": "qwen-plus"}), "invalid_model")
        self.fail_code(self.post(api_key=" "), "missing_deepseek_key")
        self.fail_code(self.post(payload={"model": "deepseek-flash", "bad": object()}), "invalid_request")
        self.opener.assert_not_called()

    def test_success_preserves_request_and_content(self):
        content = "  原样\ncontent  "
        self.actions = [Response(envelope(content))]
        messages = [{"role": "system", "content": "public"}, {"role": "user", "content": "prompt"}]
        self.assertEqual(llm.chat(messages, temperature=.3, max_tokens=40, qwen_key="old",
                                  qwen_model="other", timeout=10), content)
        self.assertEqual(llm.active_model(), "deepseek-flash")
        request, timeout = self.calls[0]
        self.assertEqual(request.full_url, llm.DEEPSEEK_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + SECRET)
        self.assertEqual(json.loads(request.data), {"model": "deepseek-flash", "messages": messages,
                                                  "temperature": .3, "max_tokens": 65536})
        self.assertEqual(timeout, 10)
        self.urlopen.assert_not_called()

    def test_reasoning_floor_survives_a_smaller_configured_budget(self):
        with patch.object(llm, "DEEPSEEK_MAX_TOKENS", 40):
            llm.chat([], max_tokens=1)
        self.assertEqual(json.loads(self.calls[0][0].data)["max_tokens"], 65536)

    def test_salvage_success_and_serialization_are_preserved(self):
        samples = [("prefix {\"type\":\"json_object\"}\n{\"ok\":true}", "object", {"ok": True}),
                   ('```json\n[{"id":1}]\n```', "array", [{"id": 1}]),
                   ('[{"id":1}, {"reason":"bad " quote"}, {"id":3}]', "array", [{"id": 1}, {"id": 3}])]
        for text, kind, expected in samples:
            with self.subTest(kind=kind), contextlib.redirect_stderr(io.StringIO()):
                self.actions = [Response(envelope(text))]
                self.assertEqual(llm.chat([], require_json=kind), json.dumps(expected, ensure_ascii=False))

    def test_bad_required_json_is_fatal_and_does_not_update_attribution(self):
        llm.LAST_MODEL = "deepseek-reasoner"
        self.actions = [Response(envelope(TEXT))]
        with self.assertRaisesRegex(llm.LLMError, "unparseable_json_body"):
            llm.chat([], require_json="object", qwen_key="old")
        self.assertEqual(llm.active_model(), "deepseek-reasoner")
        self.assertEqual(len(self.calls), 1)

    def test_only_stop_is_accepted(self):
        for finish in ("length", "tool_calls", "function_call", "content_filter", "insufficient_system_resource",
                       "invented", None, [], {"bad": TEXT}):
            with self.subTest(finish=finish):
                self.actions = [Response(envelope(TEXT, finish))]
                self.fail_code(self.post(), "unfinished_response")
        self.assertFalse(self.sleeps)

    def test_stop_with_tool_or_refusal_payload_is_rejected(self):
        for fields in ({"tool_calls": [{"name": TEXT}]}, {"function_call": {"name": TEXT}},
                       {"refusal": TEXT}, {"role": "tool"}):
            with self.subTest(fields=fields):
                self.actions = [Response(envelope(TEXT, **fields))]
                self.fail_code(self.post(), "malformed_response")

    def test_empty_or_non_string_content_is_rejected(self):
        for content in (None, "", " \n\t", [], {}, 1, True):
            with self.subTest(content=content):
                self.actions = [Response(envelope(content))]
                self.fail_code(self.post(), "empty_content")

    def test_malformed_shapes_do_not_retry(self):
        values = [None, [], "text", {}, {"choices": {}}, {"choices": []},
                  {"choices": [None]}, {"choices": [{}, {}]},
                  {"choices": [{"finish_reason": "stop", "message": None}]},
                  {**envelope(TEXT), "error": {"message": BODY}}]
        for value in values:
            with self.subTest(value=value):
                self.actions = [Response(value)]
                self.fail_code(self.post(), "malformed_response")
        self.assertEqual(len(self.calls), len(values))
        self.assertFalse(self.sleeps)

    def test_invalid_json_utf8_and_deep_json_are_sanitized(self):
        for raw in (b"not JSON", b"\xff", b"[" * 2000 + b"]" * 2000):
            with self.subTest(raw_size=len(raw)):
                self.actions = [Response(raw, raw=True)]
                self.fail_code(self.post(), "malformed_response")
        self.assertFalse(self.sleeps)

    def test_partial_reads_are_accumulated(self):
        self.actions = [Response(envelope(), piece_size=3)]
        self.assertEqual(self.post(), {"ok": True, "content": "answer"})

    def test_response_byte_limit_exact_boundary_and_overflow(self):
        empty = json.dumps(envelope("")).encode()
        for extra in (0, 1, 100_000):
            with self.subTest(extra=extra):
                response = Response(envelope("x" * (2_000_000 - len(empty) + extra)))
                self.actions = [response]
                result = self.post()
                self.assertEqual(result["ok"], extra == 0)
                if extra:
                    self.fail_code(result, "response_too_large")
                self.assertLessEqual(sum(response.read_sizes), 2_065_536)
                self.assertTrue(response.closed)

    def test_auth_failure_is_single_attempt_with_no_body_read(self):
        error, body = self.http_error(401)
        self.actions = [error]
        self.fail_code(self.post(), "http_401")
        body.read.assert_not_called()
        body.close.assert_called_once()
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.sleeps)

    def test_auth_failure_never_falls_back(self):
        error, body = self.http_error(401)
        self.actions = [error]
        with self.assertRaisesRegex(llm.LLMError, "http_401"):
            llm.chat([], qwen_key="old", label=TEXT)
        self.assertEqual(len(self.calls), 1)
        body.read.assert_not_called()
        self.urlopen.assert_not_called()

    def test_nontransient_http_never_retries_or_reads_body(self):
        for code in (301, 302, 303, 307, 308, 400, 403, 404, 501):
            with self.subTest(code=code):
                error, body = self.http_error(code)
                self.actions = [error]
                self.fail_code(self.post(), "http_" + str(code))
                body.read.assert_not_called()
        self.assertEqual(len(self.calls), 9)
        self.assertFalse(self.sleeps)

    def test_only_existing_transient_http_statuses_retry(self):
        for code in (408, 429, 500, 502, 503, 504):
            with self.subTest(code=code):
                self.now = 0
                error, body = self.http_error(code)
                self.actions = [error, Response(envelope())]
                count = len(self.calls)
                self.assertTrue(self.post(timeout=30)["ok"])
                self.assertEqual(len(self.calls) - count, 2)
                body.read.assert_not_called()

    def test_network_errors_retry_and_are_bounded(self):
        for error in (urllib.error.URLError(EXCEPTION), TimeoutError(EXCEPTION),
                      ConnectionResetError(EXCEPTION), http.client.IncompleteRead(b"partial")):
            with self.subTest(error_type=type(error).__name__):
                self.now = 0
                self.actions = [error, error, error]
                count = len(self.calls)
                self.fail_code(self.post(timeout=30), "network_error")
                self.assertEqual(len(self.calls) - count, 3)

    def test_unexpected_exception_does_not_retry(self):
        self.actions = [ValueError(EXCEPTION)]
        self.fail_code(self.post(), "transport_error")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.sleeps)

    def test_all_failure_channels_are_content_free(self):
        for action in (self.http_error(401)[0], ValueError(EXCEPTION),
                       Response(envelope(TEXT, "length")), Response(envelope(TEXT))):
            self.actions = [action]
            previous_calls = len(self.calls)
            capture = io.StringIO()
            with contextlib.redirect_stderr(capture), contextlib.redirect_stdout(capture):
                try:
                    llm.chat([], require_json="object", label=TEXT, qwen_key=SECRET)
                except llm.LLMError:
                    capture.write(traceback.format_exc())
            output = capture.getvalue()
            # Tracebacks include test source lines, so marker variable names are safe;
            # the actual synthetic values must never occur.
            for marker in (SECRET, BODY, EXCEPTION, TEXT):
                self.assertNotIn(marker, output)
            self.assertEqual(len(self.calls), previous_calls + 1)

    def test_retry_and_backoff_share_one_timeout(self):
        def first(timeout):
            self.now += 2
            raise self.http_error(429)[0]
        def last(timeout):
            self.now += timeout
            raise urllib.error.URLError(EXCEPTION)
        self.actions = [first, last]
        self.fail_code(self.post(), "timeout_exhausted")
        self.assertEqual(self.budgets, [10, 3])
        self.assertEqual([timeout for _, timeout in self.calls], [10, 3])
        self.assertEqual(self.sleeps, [5])
        self.assertEqual(self.now, 10)

    def test_insufficient_backoff_budget_starts_no_work(self):
        def failure(timeout):
            self.now += 8
            raise self.http_error(429)[0]
        self.actions = [failure]
        self.fail_code(self.post(), "timeout_exhausted")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(self.sleeps)
        self.assertEqual(self.now, 8)

    def test_zero_negative_and_nonfinite_timeout_start_no_work(self):
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                self.fail_code(self.post(timeout=timeout), "timeout_exhausted")
        self.opener.assert_not_called()

    def test_no_request_after_backoff_oversleeps(self):
        def oversleep(delay):
            self.now += delay + 10
        self.actions = [urllib.error.URLError(EXCEPTION)]
        with patch.object(llm.time, "sleep", side_effect=oversleep):
            self.fail_code(self.post(), "timeout_exhausted")
        self.assertEqual(len(self.calls), 1)

    def test_no_open_after_opener_setup_exhausts_budget(self):
        def slow_opener(timeout):
            self.now += 10
            return Mock(open=Mock(side_effect=AssertionError("late dispatch")))
        with patch.object(llm, "deepseek_opener", side_effect=slow_opener):
            self.fail_code(self.post(), "timeout_exhausted")
        self.assertFalse(self.calls)

    def test_no_request_after_serialization_exhausts_budget(self):
        dumps = json.dumps
        def slow_dumps(payload):
            self.now += 10
            return dumps(payload)
        with patch.object(llm.json, "dumps", side_effect=slow_dumps):
            self.fail_code(self.post(), "timeout_exhausted")
        self.opener.assert_not_called()

    def test_late_response_is_rejected_and_closed(self):
        response = Response(envelope())
        read = response.read
        def late_read(size):
            self.now = 10
            return read(size)
        response.read = late_read
        self.actions = [response]
        self.fail_code(self.post(), "timeout_exhausted")
        self.assertTrue(response.closed)

    def test_real_helper_is_used_with_redirect_and_deadline_handlers(self):
        error, body = self.http_error(302)
        underlying = Mock()
        underlying.open.side_effect = error
        with patch.object(llm, "deepseek_opener", http_helper.deepseek_opener), \
                patch.object(http_helper.urllib.request, "build_opener", return_value=underlying) as build:
            self.fail_code(self.post(), "http_302")
        handlers = build.call_args.args
        self.assertTrue(any(isinstance(h, http_helper._NoRedirect) for h in handlers))
        self.assertTrue(any(isinstance(h, http_helper._DeadlineHTTPSHandler) for h in handlers))
        body.read.assert_not_called()
        self.assertEqual(underlying.open.call_count, 1)

    def test_active_model_before_success_does_not_read_keys(self):
        with patch.object(llm, "deepseek_key", side_effect=AssertionError("key lookup")):
            self.assertEqual(llm.active_model(), "deepseek-flash")


class HTTPHelperTests(unittest.TestCase):
    def test_destination_validation_precedes_all_dispatch(self):
        underlying = Mock()
        with patch.dict("os.environ", {}, clear=True), \
                patch.object(http_helper.urllib.request, "build_opener", return_value=underlying):
            opener = http_helper.deepseek_opener(10)
            for url in ("https://evil.invalid/chat/completions", "http://api.deepseek.com/chat/completions",
                        "https://api.deepseek.com@evil.invalid/chat/completions",
                        "https://api.deepseek.com/chat/completions?x=1", "https://api.deepseek.com/chat/completions#x",
                        "https://api.deepseek.com:444/chat/completions", "https://api.deepseek.com/other"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    opener.open(urllib.request.Request(url, data=b"{}"))
        underlying.open.assert_not_called()

    def test_all_redirect_codes_are_refused_and_closed(self):
        handler = http_helper._NoRedirect()
        request = urllib.request.Request("https://api.deepseek.com/chat/completions")
        for code in (301, 302, 303, 307, 308):
            response = io.BytesIO(BODY.encode())
            with self.subTest(code=code), self.assertRaises(urllib.error.HTTPError):
                getattr(handler, "http_error_" + str(code))(request, response, code, BODY,
                                                            {"Location": "https://evil.invalid"})
            self.assertTrue(response.closed)

    def test_no_socket_created_when_dns_returns_after_deadline(self):
        clock = [0]
        def dns(*args):
            clock[0] = 11
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443))]
        with patch.object(http_helper.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(http_helper.socket, "getaddrinfo", side_effect=dns), \
                patch.object(http_helper.socket, "socket") as factory:
            with self.assertRaises(TimeoutError):
                http_helper._connect(("api.deepseek.com", 443), 10, None, deadline=10)
        factory.assert_not_called()

    def test_connect_addresses_share_remaining_budget(self):
        clock = [0]
        first, second = Mock(), Mock()
        def failed_connect(address):
            clock[0] += 4
            raise OSError(EXCEPTION)
        first.connect.side_effect = failed_connect
        addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443)),
                     (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.2", 443))]
        with patch.object(http_helper.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(http_helper.socket, "getaddrinfo", return_value=addresses), \
                patch.object(http_helper.socket, "socket", side_effect=[first, second]):
            result = http_helper._connect(("api.deepseek.com", 443), 10, None, deadline=10)
        self.assertIs(result._sock, second)
        first.close.assert_called_once()
        self.assertEqual(second.settimeout.call_args.args, (6,))

    def test_partial_sends_refresh_remaining_budget(self):
        clock = [0]
        native = Mock()
        def send(data, flags):
            clock[0] += 2
            return 1
        native.send.side_effect = send
        with patch.object(http_helper.time, "monotonic", side_effect=lambda: clock[0]):
            http_helper._DeadlineSocket(native, 10).sendall(b"abc")
        self.assertEqual([c.args[0] for c in native.settimeout.call_args_list], [10, 8, 6])

    def test_native_read_after_deadline_is_rejected(self):
        clock = [0]
        raw, native = Mock(), Mock()
        def readinto(buffer):
            clock[0] = 11
            return 1
        raw.readinto.side_effect = readinto
        guarded = http_helper._DeadlineRaw(raw, native, 10)
        with patch.object(http_helper.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                guarded.readinto(bytearray(1))
        native.settimeout.assert_called_once_with(10)
        guarded.close()
        raw.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
