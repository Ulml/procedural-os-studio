"""Chat correction requests — selectable, then folded back into the skill."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .paths import DATA
from .skills import get_agent, save_agent

STORE = DATA / "memory.json"


def _load() -> list[dict[str, Any]]:
    if not STORE.exists():
        return []
    return json.loads(STORE.read_text(encoding="utf-8")).get("items", [])


def _save(items: list[dict[str, Any]]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps({"items": items}, indent=2, ensure_ascii=False), encoding="utf-8")


def list_items(slug: str | None = None) -> list[dict[str, Any]]:
    items = _load()
    if slug:
        items = [i for i in items if i.get("slug") == slug]
    return items


def add_item(slug: str, text: str, source: str = "chat") -> dict[str, Any]:
    items = _load()
    item = {
        "id": uuid.uuid4().hex[:12],
        "slug": slug,
        "text": text.strip(),
        "source": source,
        "selected": True,
        "applied": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    items.append(item)
    _save(items)
    return item


def set_selected(ids: list[str], selected: bool) -> list[dict[str, Any]]:
    items = _load()
    wanted = set(ids)
    for item in items:
        if item["id"] in wanted:
            item["selected"] = selected
    _save(items)
    return items


def apply_selected(slug: str) -> dict[str, Any]:
    items = _load()
    chosen = [i for i in items if i["slug"] == slug and i.get("selected") and not i.get("applied")]
    if not chosen:
        return {"ok": False, "error": "no selected memory items"}
    agent = get_agent(slug)
    block = "\n\n## Memory corrections\n" + "\n".join(f"- {i['text']}" for i in chosen)
    body = agent.body
    if "## Memory corrections" in body:
        body = body.split("## Memory corrections")[0].rstrip() + block
    else:
        body = body.rstrip() + block + "\n"
    save_agent(slug, body=body)
    for item in items:
        if item in chosen:
            item["applied"] = True
            item["selected"] = False
    _save(items)
    return {"ok": True, "applied": [i["id"] for i in chosen], "body": get_agent(slug).body}
