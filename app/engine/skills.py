"""Agent tree = Agent Skills folders (https://agentskills.io/home)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import AGENTS

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(name: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    raw = re.sub(r"-{2,}", "-", raw)
    return (raw or "agent")[:64]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, Any] = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            i += 1
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip(), raw.strip()
        if raw in ("|", ">", "|-", ">-"):
            chunks = []
            i += 1
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                chunks.append(lines[i][2:] if lines[i].startswith("  ") else lines[i])
                i += 1
            meta[key] = "\n".join(chunks).strip()
            continue
        meta[key] = raw.strip("'\"")
        i += 1
    return meta, match.group(2).strip()


def render_skill_md(name: str, description: str, body: str, extra: dict | None = None) -> str:
    extra = extra or {}
    desc = description.replace("\n", " ").strip()[:1024]
    lines = ["---", f"name: {name}", f"description: {desc}"]
    for key in ("license", "compatibility", "metadata"):
        if key in extra and extra[key]:
            lines.append(f"{key}: {extra[key]}")
    if extra.get("allowed_tools"):
        lines.append(f"allowed-tools: {extra['allowed_tools']}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip() + "\n")
    return "\n".join(lines)


@dataclass
class Agent:
    slug: str
    name: str
    description: str
    body: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    cron: dict[str, Any] | None = None
    examples: dict[str, Any] = field(default_factory=dict)

    def l1(self) -> dict[str, str]:
        return {"slug": self.slug, "name": self.name, "description": self.description}

    def files(self) -> list[str]:
        root = self.path.parent
        out = []
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out.append(str(p.relative_to(root)))
        return out


def load_agent(folder: Path) -> Agent | None:
    skill = folder / "SKILL.md"
    if not skill.exists():
        return None
    meta, body = parse_frontmatter(skill.read_text(encoding="utf-8"))
    name = str(meta.get("name") or folder.name)
    description = str(meta.get("description") or "")
    cron = None
    cron_path = folder / "cron.json"
    if cron_path.exists():
        cron = json.loads(cron_path.read_text(encoding="utf-8"))
    examples = {}
    ex_meta = folder / "examples" / "meta.json"
    if ex_meta.exists():
        examples = json.loads(ex_meta.read_text(encoding="utf-8"))
    return Agent(
        slug=folder.name,
        name=name,
        description=description,
        body=body,
        path=skill,
        metadata=meta,
        cron=cron,
        examples=examples,
    )


def list_agents() -> list[Agent]:
    agents = []
    for folder in sorted(AGENTS.iterdir() if AGENTS.exists() else []):
        if folder.is_dir():
            agent = load_agent(folder)
            if agent:
                agents.append(agent)
    return agents


def get_agent(slug: str) -> Agent:
    agent = load_agent(AGENTS / slug)
    if not agent:
        raise KeyError(slug)
    return agent


def save_agent(
    slug: str,
    *,
    name: str | None = None,
    description: str | None = None,
    body: str | None = None,
    extra: dict | None = None,
    scripts: dict[str, str] | None = None,
    references: dict[str, str] | None = None,
    cron: dict | None = None,
    examples: dict | None = None,
) -> Agent:
    slug = slugify(slug)
    if not SLUG_RE.match(slug):
        raise ValueError(f"invalid slug: {slug}")
    folder = AGENTS / slug
    folder.mkdir(parents=True, exist_ok=True)
    existing = load_agent(folder)
    name = name or (existing.name if existing else slug)
    description = description or (existing.description if existing else name)
    body = body if body is not None else (existing.body if existing else "")
    (folder / "SKILL.md").write_text(
        render_skill_md(name, description, body, extra), encoding="utf-8"
    )
    if scripts:
        sdir = folder / "scripts"
        sdir.mkdir(exist_ok=True)
        for fname, content in scripts.items():
            (sdir / Path(fname).name).write_text(content, encoding="utf-8")
    if references:
        rdir = folder / "references"
        rdir.mkdir(exist_ok=True)
        for fname, content in references.items():
            (rdir / Path(fname).name).write_text(content, encoding="utf-8")
    if cron is not None:
        (folder / "cron.json").write_text(json.dumps(cron, indent=2), encoding="utf-8")
    if examples is not None:
        edir = folder / "examples"
        edir.mkdir(exist_ok=True)
        (edir / "meta.json").write_text(json.dumps(examples, indent=2), encoding="utf-8")
        if examples.get("input_text"):
            (edir / "input.txt").write_text(examples["input_text"], encoding="utf-8")
        if examples.get("output_text"):
            (edir / "output.txt").write_text(examples["output_text"], encoding="utf-8")
    return get_agent(slug)


def read_resource(slug: str, rel: str) -> str:
    root = (AGENTS / slug).resolve()
    path = (root / rel).resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("path escapes agent directory")
    return path.read_text(encoding="utf-8", errors="replace")


def write_resource(slug: str, rel: str, content: str) -> None:
    root = (AGENTS / slug).resolve()
    path = (root / rel).resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("path escapes agent directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
