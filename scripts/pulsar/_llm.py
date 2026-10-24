#!/usr/bin/env python3
"""DeepSeek-only transport for the Pulsar spatial pipeline.

Only complete assistant text is usable. Failures return bounded codes, never
provider bodies, model text, caller labels, keys or raw exception messages.
Retries and backoff share one caller timeout. The per-request HTTP helper guards
redirects and native socket operations; blocking DNS still needs the workflow's
external hard timeout.

DeepSeek keeps its 65,536-token reasoning floor and receives no response_format.
The legacy qwen kwargs remain accepted solely for caller compatibility.
"""
from __future__ import annotations
import http.client
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    DEEPSEEK_MAX_TOKENS, DEEPSEEK_MODEL, DEEPSEEK_URL,
    LLM_PROVIDER, LLM_RETRY, LLM_RETRY_BACKOFF, LLM_TIMEOUT,
)
from _deepseek_http import deepseek_opener

LAST_MODEL = ""
_DEEPSEEK_DESTINATION = "https://api.deepseek.com/chat/completions"
_MAX_RESPONSE_BYTES = 2_000_000
_TRANSIENT_HTTP = (408, 429, 500, 502, 503, 504)


class LLMError(RuntimeError):
    """DeepSeek did not produce a usable answer. Callers must treat this as fatal."""


def deepseek_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def _deepseek_model(model) -> bool:
    return isinstance(model, str) and re.fullmatch(
        r"deepseek-[A-Za-z0-9][A-Za-z0-9._-]*", model) is not None


def _post(url: str, api_key: str, payload: dict, timeout: int, label: str) -> dict:
    """Return {ok: bool, content|error}; retry transient failures within one budget."""
    if url != _DEEPSEEK_DESTINATION:
        return {"ok": False, "error": "invalid_destination"}
    if not isinstance(payload, dict) or not _deepseek_model(payload.get("model")):
        return {"ok": False, "error": "invalid_model"}
    if not isinstance(api_key, str) or not api_key.strip():
        return {"ok": False, "error": "missing_deepseek_key"}
    try:
        budget = float(timeout)
        if not math.isfinite(budget) or budget <= 0:
            return {"ok": False, "error": "timeout_exhausted"}
        deadline = time.monotonic() + budget
        data = json.dumps(payload).encode("utf-8")
    except Exception:
        return {"ok": False, "error": "invalid_request"}

    for attempt in range(LLM_RETRY):
        if time.monotonic() >= deadline:
            return {"ok": False, "error": "timeout_exhausted"}
        try:
            # Fresh request and opener, with only this call's remaining budget.
            req = urllib.request.Request(url, data=data, method="POST", headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            })
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"ok": False, "error": "timeout_exhausted"}
            opener = deepseek_opener(remaining)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"ok": False, "error": "timeout_exhausted"}
            with opener.open(req, timeout=remaining) as response:
                if response.status != 200:
                    return {"ok": False, "error": "unexpected_http_status"}
                raw = bytearray()
                while True:
                    if time.monotonic() >= deadline:
                        return {"ok": False, "error": "timeout_exhausted"}
                    # One sentinel byte detects overflow without an unbounded read.
                    chunk = response.read(min(65_536, _MAX_RESPONSE_BYTES + 1 - len(raw)))
                    if time.monotonic() >= deadline:
                        return {"ok": False, "error": "timeout_exhausted"}
                    raw.extend(chunk)
                    if len(raw) > _MAX_RESPONSE_BYTES:
                        return {"ok": False, "error": "response_too_large"}
                    if not chunk:
                        break
            if time.monotonic() >= deadline:
                return {"ok": False, "error": "timeout_exhausted"}
            try:
                obj = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeError, RecursionError):
                return {"ok": False, "error": "malformed_response"}
            if (not isinstance(obj, dict) or "error" in obj
                    or not isinstance(obj.get("choices"), list)
                    or len(obj["choices"]) != 1
                    or not isinstance(obj["choices"][0], dict)):
                return {"ok": False, "error": "malformed_response"}
            choice = obj["choices"][0]
            if choice.get("finish_reason") != "stop":
                return {"ok": False, "error": "unfinished_response"}
            message = choice.get("message")
            if (not isinstance(message, dict)
                    or message.get("role", "assistant") != "assistant"
                    or message.get("tool_calls") or message.get("function_call")
                    or message.get("refusal")):
                return {"ok": False, "error": "malformed_response"}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                return {"ok": False, "error": "empty_content"}
            if time.monotonic() >= deadline:
                return {"ok": False, "error": "timeout_exhausted"}
            return {"ok": True, "content": content}
        except urllib.error.HTTPError as error:
            # Never read error bodies, even for retryable statuses.
            code = error.code
            try:
                error.close()
            except Exception:
                pass
            safe_code = code if type(code) is int and 100 <= code <= 599 else None
            failure = "http_" + str(safe_code) if safe_code is not None else "http_error"
            retryable = safe_code in _TRANSIENT_HTTP
        except (urllib.error.URLError, OSError, http.client.HTTPException):
            failure = "network_error"
            retryable = True
        except Exception:
            return {"ok": False, "error": "transport_error"}

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"ok": False, "error": "timeout_exhausted"}
        if not retryable or attempt == LLM_RETRY - 1:
            return {"ok": False, "error": failure}
        delay = LLM_RETRY_BACKOFF * (attempt + 1)
        if delay >= remaining:
            return {"ok": False, "error": "timeout_exhausted"}
        time.sleep(delay)
    return {"ok": False, "error": "max_retries"}


def salvage_json(content: str, expect: str = "object"):
    """Best-effort recovery of a JSON object/array from a model response.

    Returns the parsed value, or None if nothing usable could be recovered —
    and None is what makes the caller fall back to the other provider.

    Adapted from the sibling VLA rater's `_salvage_rating_array`, which on
    2026-09-10 recovered 49 of 51 papers on a day that had otherwise produced
    zero. Two layers, one per observed failure shape:

      1. **prose prefix** — the model narrates before emitting the payload, or
         (DeepSeek's json_object bug) emits a stray `{"type": "json_object"}`
         line first. Scan opening brackets and `raw_decode` from each in turn,
         skipping degenerate `{"type": ...}`-only objects.
      2. **one malformed element** (arrays only) — typically an unescaped `"`
         inside a Chinese `reason`. Split the array body on element boundaries
         and parse each element alone, dropping only the broken one instead of
         losing the whole sheet.
    """
    if not content:
        return None
    s = content.strip()
    if s.startswith("```"):
        s = "\n".join(l for l in s.splitlines()
                      if not l.strip().startswith("```")).strip()

    want = list if expect == "array" else dict
    open_ch, close_ch = ("[", "]") if expect == "array" else ("{", "}")

    try:
        v = json.loads(s)
        if isinstance(v, want) and v:
            return v
    except Exception:
        pass

    # ---- layer 1: prose / stray-preamble prefix --------------------------
    found = None
    for m in re.finditer(re.escape(open_ch), s):
        try:
            v, _ = json.JSONDecoder().raw_decode(s[m.start():])
        except Exception:
            continue
        if not isinstance(v, want) or not v:
            continue
        # DeepSeek's response_format leak is literally {"type": "json_object"}.
        # Skip it and keep looking for the real payload behind it.
        if isinstance(v, dict) and set(v.keys()) == {"type"}:
            continue
        found = v
        break
    if found is not None:
        return found

    if expect != "array":
        return None

    # ---- layer 2: drop only the malformed element ------------------------
    i = s.find(open_ch)
    if i < 0:
        return None
    j = s.rfind(close_ch)
    body = s[i + 1:j] if j > i else s[i + 1:]
    out = []
    for chunk in re.split(r"\}\s*,\s*\{", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.startswith("{"):
            chunk = "{" + chunk
        if not chunk.endswith("}"):
            chunk = chunk + "}"
        try:
            o = json.loads(chunk)
        except Exception:
            continue
        if isinstance(o, dict):
            out.append(o)
    if out:
        print(f"  salvaged {len(out)} element(s) from a malformed array", file=sys.stderr)
    return out or None


def _finish(content: str, require_json: str | None) -> str:
    """Hand the caller a string it can parse with its existing code.

    When `require_json` is set we re-serialise the salvaged value, so every
    call site keeps working unchanged whether it does `json.loads(raw)` or
    `re.search(r"\\{.*\\}", raw, re.S)`. That is what lets all four original
    `call_qwen` signatures survive this refactor untouched.
    """
    if not require_json:
        return content
    return json.dumps(salvage_json(content, require_json), ensure_ascii=False)


def chat(messages: list[dict], *, temperature: float = 0.2,
         max_tokens: int | None = None, timeout: int = LLM_TIMEOUT,
         require_json: str | None = None, qwen_key: str = "",
         qwen_model: str = "", label: str = "llm") -> str:
    """Return DeepSeek assistant text, or raise a content-free LLMError.

    require_json retains established salvage and serialization behavior.
    max_tokens, qwen_key and qwen_model remain accepted legacy arguments;
    DeepSeek always receives at least its 65,536-token reasoning floor.
    """
    global LAST_MODEL
    if LLM_PROVIDER != "deepseek":
        raise LLMError("deepseek: unsupported_provider")
    if not _deepseek_model(DEEPSEEK_MODEL):
        raise LLMError("deepseek: invalid_model")
    if DEEPSEEK_URL != _DEEPSEEK_DESTINATION:
        raise LLMError("deepseek: invalid_destination")
    ds_key = deepseek_key()
    if not ds_key:
        raise LLMError("deepseek: missing_deepseek_key")
    res = _post(DEEPSEEK_URL, ds_key, {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max(65_536, DEEPSEEK_MAX_TOKENS),
    }, timeout, label)
    if not res["ok"]:
        raise LLMError("deepseek: " + res["error"])
    if require_json and salvage_json(res["content"], require_json) is None:
        raise LLMError("deepseek: unparseable_json_body")
    result = _finish(res["content"], require_json)
    LAST_MODEL = DEEPSEEK_MODEL
    return result


def active_model() -> str:
    """Return the last successful model, or the configured DeepSeek model."""
    if LAST_MODEL:
        return LAST_MODEL
    if LLM_PROVIDER != "deepseek":
        raise LLMError("deepseek: unsupported_provider")
    if not _deepseek_model(DEEPSEEK_MODEL):
        raise LLMError("deepseek: invalid_model")
    return DEEPSEEK_MODEL
