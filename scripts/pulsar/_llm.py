#!/usr/bin/env python3
"""Shared LLM transport for the Pulsar spatial pipeline — DeepSeek → qwen.

WHY THIS FILE EXISTS
Four scripts each carried a private copy of `call_qwen` (rate.py,
collect_curated.py, run_weekly.py, write_dissection.py). They shared one
single point of failure and no fallback, so when this repo's
DASHSCOPE_API_KEY Actions secret was revoked they all died the same death at
once — and rate.py's per-paper except-branch turned that into a *committed*
report: `reports/spatial-daily/2026-08-31..09-07.md` each list 80 papers as
`⚡0 · 🔧0 · 📖80`, every line reading
`_(rating error: qwen all 3 attempts failed: HTTP Error 401: Unauthorized)_`.
One transport, one fallback policy, one place to fix.

PROVIDER ORDER
  1. DeepSeek `deepseek-flash` (DEEPSEEK_API_KEY)
  2. DashScope qwen            (DASHSCOPE_API_KEY, passed in by the caller)
If DeepSeek fails for ANY reason — HTTP error, empty body, truncation, or an
HTTP 200 whose body will not yield the JSON the caller asked for — we degrade
to qwen. If qwen is unavailable too, we raise LLMError. We never return
something that merely looks like an answer.

DEEPSEEK FACTS THIS TRANSPORT IS BUILT AROUND
All measured 2026-09-10 against this repo's own RATING_PROMPT_SYSTEM, on the
first 5 papers of reports/spatial-daily/2026-09-07.md.

*   **Never send `response_format={"type":"json_object"}`.** On a batched
    ~50-item rating prompt it scored 1/5 valid JSON: DeepSeek emits a literal
    `{"type": "json_object"}` line *before* the real payload. `json_schema`
    strict mode answers "unavailable". This transport therefore sends no
    `response_format` to either provider; the prompt asks for JSON and
    `require_json` + `salvage_json()` enforce it. (qwen3.5-plus is 5/5 either
    way, so dropping it costs the fallback nothing and keeps one payload shape.)
*   **`max_tokens` is a reasoning budget, not an output cap**, and the
    reasoning is billed against it. Starve it and reasoning eats the whole
    budget, leaving truncated JSON. Measured here per paper:
        think-on, max_tokens=65536   → 5/5 valid, ⚡2 🔧1 📖2, avg  8.3 s
        "thinking":{"type":"disabled"} → 5/5 valid, ⚡0 🔧3 📖2, avg  1.0 s
    Reasoning is what buys the rating quality (without it every ⚡ collapses to
    🔧/📖 with ~100-token reasons), so it stays ON and every DeepSeek call gets
    the full DEEPSEEK_MAX_TOKENS floor no matter what the caller asked for.
    `reasoning_effort` does not work; `"thinking":{"type":"disabled"}` is the
    only real off switch and we deliberately do not use it.
*   **HTTP 200 with an unparseable body is a real, observed failure mode.**
    `require_json` makes it a provider failure that falls back to qwen, rather
    than a parse error that silently stamps 📖 on everything.
*   Cost note only, no action taken: DeepSeek peak pricing is UTC 01:00-04:00
    and 06:00-10:00 Mon-Fri, which is exactly when the daily (00:30 UTC),
    weekly (02:00 UTC) and dissection (06:00 UTC) workflows run. Deliberately
    NOT rescheduled — arxiv announcement timing drives the schedule.

Pure stdlib + urllib, to match the rest of the pipeline (no openai SDK).
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _config import (
    DASHSCOPE_BASE_URL, DEEPSEEK_MAX_TOKENS, DEEPSEEK_MODEL, DEEPSEEK_URL,
    LLM_MODEL, LLM_PROVIDER, LLM_RETRY, LLM_RETRY_BACKOFF, LLM_TIMEOUT,
)

# Model id that answered the most recent successful call — for report banners,
# so a report never claims to have been written by a model that never ran.
LAST_MODEL = ""


class LLMError(RuntimeError):
    """Every provider in the chain failed. Callers must treat this as fatal."""


def deepseek_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY", "").strip()


def _post(url: str, api_key: str, payload: dict, timeout: int, label: str) -> dict:
    """POST one chat-completions payload. Returns {ok: bool, content|error}.

    Retries 429/5xx. Never raises — the caller decides whether to fall back.
    """
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(LLM_RETRY):
        # Rebuild the Request every attempt: a consumed urllib Request cannot
        # be replayed (the original four copies all shared one Request object
        # across retries, so retry 2 and 3 were replaying a spent body).
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                obj = json.loads(r.read().decode("utf-8", "replace"))
            choice = (obj.get("choices") or [{}])[0] or {}
            content = ((choice.get("message") or {}).get("content") or "")
            if not content.strip():
                # A reasoning model can burn its entire budget thinking and
                # still come back finish_reason=stop with empty content.
                return {"ok": False, "error": "empty_content"}
            if choice.get("finish_reason") == "length":
                # Truncated JSON parses as garbage; without this check the
                # caller silently downgrades every item instead of falling back.
                return {"ok": False, "error": "truncated_output"}
            return {"ok": True, "content": content}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            if e.code in (408, 429, 500, 502, 503, 504) and attempt < LLM_RETRY - 1:
                print(f"  WARN {label}: HTTP {e.code}, retry {attempt + 1}/{LLM_RETRY}",
                      file=sys.stderr)
                time.sleep(LLM_RETRY_BACKOFF * (attempt + 1))
                continue
            return {"ok": False, "error": f"HTTP {e.code}", "detail": detail}
        except Exception as e:  # URLError, timeout, malformed envelope
            if attempt < LLM_RETRY - 1:
                print(f"  WARN {label}: {str(e)[:120]}, retry {attempt + 1}/{LLM_RETRY}",
                      file=sys.stderr)
                time.sleep(LLM_RETRY_BACKOFF * (attempt + 1))
                continue
            return {"ok": False, "error": str(e)[:200]}
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
    """DeepSeek first, qwen fallback. Returns the assistant text.

    require_json — "object" | "array" | None. When set, a response that yields
    no such JSON counts as a PROVIDER FAILURE (triggering the fallback), not as
    a parse error for the caller to paper over.
    max_tokens   — applies to the qwen leg only; DeepSeek always gets
                   DEEPSEEK_MAX_TOKENS (see the module docstring).
    qwen_key     — the caller's DASHSCOPE_API_KEY; "" disables the fallback.
    qwen_model   — override LLM_MODEL on the fallback leg (write_dissection
                   --model). Must exist in the catalog of DASHSCOPE_BASE_URL.
    Raises LLMError when no provider produced a usable answer.
    """
    global LAST_MODEL
    errors: list[str] = []
    qmodel = qwen_model or LLM_MODEL

    if LLM_PROVIDER == "deepseek":
        ds_key = deepseek_key()
        if not ds_key:
            errors.append("deepseek: DEEPSEEK_API_KEY not set")
            print(f"  WARN {label}: DEEPSEEK_API_KEY not set — trying {qmodel} only",
                  file=sys.stderr)
        else:
            res = _post(DEEPSEEK_URL, ds_key, {
                "model": DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": temperature,
                # Deliberately NOT the caller's max_tokens: theirs is an output
                # cap (40 for run_dissection.classify_zone, 800 for
                # write_dissection.factcheck), DeepSeek's is a reasoning
                # budget. Honouring a small one leaves reasoning no room and
                # returns truncated garbage. See the module docstring.
                "max_tokens": DEEPSEEK_MAX_TOKENS,
                # No "response_format" here, on purpose. See the module docstring.
            }, timeout, f"{label}/deepseek")
            if res["ok"] and require_json and salvage_json(res["content"], require_json) is None:
                # HTTP 200, non-empty, not truncated — and still unusable.
                # Treat it as a failure so we degrade to qwen instead of
                # letting a placeholder through.
                res = {"ok": False, "error": "unparseable_json_body",
                       "detail": res["content"][:160].replace("\n", " ")}
            if res["ok"]:
                LAST_MODEL = DEEPSEEK_MODEL
                return _finish(res["content"], require_json)
            errors.append(f"deepseek({DEEPSEEK_MODEL}): {res['error']} {res.get('detail', '')}".strip())
            print(f"  WARN {label}: deepseek failed ({res['error']}) — "
                  f"falling back to {qmodel}", file=sys.stderr)

    if not qwen_key:
        # Degrade honestly rather than pretending to work. A missing or dead
        # DashScope key is exactly how 8 days of placeholder reports got
        # committed; the caller now gets an exception it can turn into a red run.
        errors.append(f"qwen({qmodel} @ {DASHSCOPE_BASE_URL}): DASHSCOPE_API_KEY not set")
        raise LLMError(f"{label}: no usable LLM provider — " + " | ".join(errors))

    payload: dict = {"model": qmodel, "messages": messages, "temperature": temperature}
    if max_tokens:
        payload["max_tokens"] = max_tokens
    res = _post(f"{DASHSCOPE_BASE_URL}/chat/completions", qwen_key, payload,
                timeout, f"{label}/qwen")
    if res["ok"] and require_json and salvage_json(res["content"], require_json) is None:
        res = {"ok": False, "error": "unparseable_json_body",
               "detail": res["content"][:160].replace("\n", " ")}
    if res["ok"]:
        LAST_MODEL = qmodel
        return _finish(res["content"], require_json)
    errors.append(f"qwen({qmodel} @ {DASHSCOPE_BASE_URL}): "
                  f"{res['error']} {res.get('detail', '')}".strip())
    raise LLMError(f"{label}: all providers failed — " + " | ".join(errors))


def active_model() -> str:
    """Model that actually answered, for report banners. Falls back to the
    configured primary before any call has been made."""
    if LAST_MODEL:
        return LAST_MODEL
    return DEEPSEEK_MODEL if (LLM_PROVIDER == "deepseek" and deepseek_key()) else LLM_MODEL
