"""The linker's only case-write path: POST through MUIOGO's copy-and-solve seam."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def apply_via_muiogo(patch, base_caserun, *, base_url, solver="CBC", timeout_s=21600):
    url = f"{base_url.rstrip('/')}/oglink/applyPatch"
    body = json.dumps({"patch": patch, "base_caserun": base_caserun,
                       "solver": solver}, allow_nan=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_format_http_error(exc)) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"MUIOGO not reachable at {url}: {exc}") from exc
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f"invalid JSON response from {url}") from exc
    if (not isinstance(result, dict) or result.get("status_code") != "success"
            or any(not result.get(key) for key in ("case_copy", "caserun", "csv_dir"))):
        raise RuntimeError(f"applyPatch did not return a successful solved-case record: {result!r}")
    return result


def _format_http_error(exc):
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        return f"applyPatch failed (HTTP {exc.code}): {raw[:1000]}"
    parts = [str(payload.get("message") or "request failed")]
    if payload.get("blocked"):
        parts.append("blocked: " + "; ".join(
            f"change {b.get('change_index', '?')}: {b.get('reason', b)}"
            if isinstance(b, dict) else str(b) for b in payload["blocked"]))
    if payload.get("finding"):
        parts.append(f"finding: {payload['finding']}")
    return f"applyPatch failed (HTTP {exc.code}): " + " | ".join(parts)
