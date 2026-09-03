"""Commit reformatted skills back to the user's GitHub repository."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .paths import ROOT
from .skills import get_agent


def configured() -> bool:
    return bool(os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPO"))


def _req(method: str, url: str, payload: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8", errors="replace")[:400]) from exc


def push_agent(slug: str, message: str | None = None) -> dict:
    if not configured():
        return {"ok": False, "error": "Set GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO"}
    owner = os.environ.get("GITHUB_OWNER", "")
    repo = os.environ.get("GITHUB_REPO", "")
    branch = os.environ.get("GITHUB_BRANCH", "main")
    agent = get_agent(slug)
    folder = agent.path.parent
    uploaded = []
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        b64 = base64.b64encode(content).decode("ascii")
        api = f"https://api.github.com/repos/{owner}/{repo}/contents/{rel}"
        sha = None
        try:
            existing = _req("GET", api + f"?ref={branch}")
            sha = existing.get("sha")
        except RuntimeError:
            sha = None
        payload = {
            "message": message or f"chore({slug}): reformat skill from Memory tab",
            "content": b64,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        result = _req("PUT", api, payload)
        uploaded.append({"path": rel, "html": result.get("content", {}).get("html_url")})
    return {"ok": True, "files": uploaded, "repo": f"https://github.com/{owner}/{repo}"}
