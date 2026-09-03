from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def settings() -> dict[str, str]:
    return {
        "base_url": os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/"),
        "api_key": os.environ.get("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "ollama")),
        "model": os.environ.get("LLM_MODEL", "llama3.1"),
    }


def available() -> bool:
    try:
        cfg = settings()
        req = urllib.request.Request(cfg["base_url"] + "/models", method="GET")
        req.add_header("Authorization", "Bearer " + cfg["api_key"])
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception:
        return False


def chat(messages: list[dict[str, Any]], tools: list[dict] | None = None, temperature: float = 0.2) -> dict:
    cfg = settings()
    body: dict[str, Any] = {"model": cfg["model"], "messages": messages, "temperature": temperature}
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg["api_key"]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "No LLM endpoint. Start Ollama or set LLM_BASE_URL / LLM_API_KEY / LLM_MODEL."
        ) from exc
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8", errors="replace")[:400]) from exc
    return payload["choices"][0]["message"]
