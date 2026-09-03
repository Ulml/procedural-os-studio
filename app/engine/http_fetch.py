from __future__ import annotations

import json
import urllib.request


def fetch(url: str, method: str = "GET", body: str | None = None, headers: dict | None = None) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "only http(s) urls"}
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()[:20000]
            text = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            return {"ok": True, "status": resp.status, "text": text, "json": parsed}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
