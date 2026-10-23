"""The ONLY write path from the link into CLEWS: POST a clews_patch.json to MUIOGO's
/oglink/applyPatch and read back the solved result.

The link never writes DataStorage directly -- applyPatch copies the case, validates
all-or-nothing, regenerates the datafile, guards against a structure change, and solves.
This client is urllib-only (stdlib): no requests, no MUIOGO/ogcore import, so the link
env stays isolated.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def apply_via_muiogo(patch: dict, base_caserun: str, *, base_url: str,
                     solver: str = "CBC", timeout_s: int = 21600) -> dict:
    """POST ``patch`` to applyPatch and return the parsed result dict.

    On an HTTP error, raise RuntimeError carrying the endpoint's ``message`` plus any
    structured detail (which change blocked, or that the datafile structure changed), so
    the caller sees the cause rather than a bare status code. On a connection failure,
    raise RuntimeError naming the URL that was unreachable.
    """
    assert isinstance(patch, dict), "patch must be a dict"
    assert isinstance(base_caserun, str) and base_caserun, "base_caserun must be a non-empty string"
    assert isinstance(base_url, str) and base_url, "base_url must be a non-empty string"

    url = f"{base_url.rstrip('/')}/oglink/applyPatch"
    body = json.dumps({"patch": patch, "base_caserun": base_caserun,
                       "solver": solver}).encode("utf-8")
    # No Origin header: the route refuses cross-site browser posts but passes a
    # header-less headless caller through its guard.
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_format_http_error(url, exc)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MUIOGO not reachable at {url}: {exc.reason}") from exc


def _format_http_error(url: str, exc: urllib.error.HTTPError) -> str:
    """Turn applyPatch's structured error body into a single human message.

    Surfaces the endpoint's ``message`` and, when present, WHICH changes blocked or that
    the datafile structure changed -- not a bare HTTP code. Falls back to the raw body
    (truncated) when it is not JSON.
    """
    try:
        raw = exc.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 -- the body is best-effort context on an already-failed call
        raw = ""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        detail = f": {raw[:1000]}" if raw.strip() else ""
        return f"applyPatch failed (HTTP {exc.code}){detail}"

    parts = [payload.get("message") or f"applyPatch failed (HTTP {exc.code})"]
    blocked = payload.get("blocked")
    if blocked:
        reasons = "; ".join(
            f"change {b.get('change_index', '?')}: {b.get('reason', b)}"
            if isinstance(b, dict) else str(b)
            for b in blocked)
        parts.append(f"blocked: {reasons}")
    finding = payload.get("finding")
    if finding:
        parts.append(f"finding: {finding}")
    return f"applyPatch failed (HTTP {exc.code}): " + " | ".join(parts)
