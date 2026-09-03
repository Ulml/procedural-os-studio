"""Minimal MCP stdio client. Configure MCP_SERVERS=name|cmd|args..."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any


def servers() -> list[dict[str, Any]]:
    raw = os.environ.get("MCP_SERVERS", "").strip()
    out = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = [p for p in line.split("|") if p]
        if len(parts) < 2:
            continue
        out.append({"name": parts[0], "command": parts[1], "args": parts[2:]})
    return out


def call(server_name: str, method: str, params: dict | None = None) -> dict:
    found = next((s for s in servers() if s["name"] == server_name), None)
    if not found:
        return {"ok": False, "error": f"unknown MCP server {server_name}", "configured": servers()}
    proc = subprocess.Popen(
        [found["command"], *found["args"]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    try:
        stdout, stderr = proc.communicate(json.dumps(payload), timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"ok": False, "error": "mcp timeout"}
    try:
        return {"ok": True, "result": json.loads(stdout.strip().splitlines()[-1])}
    except Exception:
        return {"ok": False, "stderr": stderr[-1000:], "stdout": stdout[-1000:]}
