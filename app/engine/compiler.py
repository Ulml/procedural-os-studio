"""Compile unformatted natural language + I/O examples into a valid SKILL.md tree."""
from __future__ import annotations
import json, re
from typing import Any
from . import llm
from .skills import save_agent, slugify

COMPILER_PROMPT = (
    "You format Agent Skills (https://agentskills.io/home). Return ONLY valid JSON "
    "with keys name, description, body, script_name, script, cron. "
    "name is kebab-case. body is L2 markdown. script is L3 python or empty."
)

def _heuristic(nl: str, slug: str, example: dict) -> dict[str, Any]:
    title = slug.replace("-", " ")
    first = next((ln.strip() for ln in nl.splitlines() if ln.strip()), title)
    description = first[:500]
    wants_code = bool(re.search(r"https?://|api|docx|xlsx|pptx|script|python|\.md", nl, re.I))
    body = (
        f"# {title}\n\n## When to use\n{description}\n\n## Preconditions\n"
        "- Local workspace unless an HTTP example is provided.\n"
        "- Follow examples/.\n\n## Steps\n"
        + (nl.strip() or "1. Read the user goal.")
        + f"\n\n## Input / output example\n- Input ({example.get('input_kind','prompt')}): "
        + str(example.get('input_text') or example.get('input_ref') or '—')
        + f"\n- Output ({example.get('output_kind','prompt')}): "
        + str(example.get('output_text') or example.get('output_ref') or '—')
        + "\n\n## Tools allowed\n- list_skills, load_skill, run_script, write_artifact, http_fetch, call_mcp\n"
        "\n## Done when\n- Output matches the requested kind.\n\n## On failure\n- Stop after two attempts.\n"
    )
    script = script_name = ""
    if wants_code:
        script_name = "run.py"
        script = (
            "#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n"
            "goal=' '.join(sys.argv[1:]) or 'run'\n"
            "Path('result.md').write_text('# Result\\n\\nGoal: '+goal+'\\n', encoding='utf-8')\n"
            "print(json.dumps({'wrote':'result.md'}))\n"
        )
    cron = None
    m = re.search(r"cron\s*[:=]\s*`?([0-9*/\\- ,]+)`?", nl, re.I)
    if m:
        cron = {"enabled": True, "cron": m.group(1).strip(), "goal": description}
    return {"name": slug, "description": description, "body": body,
            "script_name": script_name, "script": script, "cron": cron}

def compile_skill(raw_nl: str, *, name: str | None = None, example: dict | None = None, use_llm: bool = True) -> dict[str, Any]:
    example = example or {}
    slug = slugify(name or raw_nl.split("\n", 1)[0][:40] or "custom-agent")
    drafted = _heuristic(raw_nl, slug, example)
    if use_llm:
        try:
            message = llm.chat([
                {"role": "system", "content": COMPILER_PROMPT},
                {"role": "user", "content": json.dumps({"natural_language": raw_nl, "preferred_slug": slug, "example": example}, ensure_ascii=False)},
            ])
            content = message.get("content") or ""
            start, end = content.find("{"), content.rfind("}")
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end+1])
                drafted.update({k: parsed[k] for k in drafted if k in parsed and parsed[k]})
                drafted["name"] = slugify(str(parsed.get("name") or slug))
        except Exception:
            pass
    scripts = {}
    if drafted.get("script") and drafted.get("script_name"):
        scripts[drafted["script_name"]] = drafted["script"]
    agent = save_agent(drafted["name"], name=drafted["name"], description=drafted["description"],
                       body=drafted["body"], scripts=scripts or None, cron=drafted.get("cron"), examples=example or None)
    return {"slug": agent.slug, "name": agent.name, "description": agent.description,
            "body": agent.body, "files": agent.files(), "used_llm": use_llm}
