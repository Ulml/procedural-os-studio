"""LLM-agnostic runner. All procedure comes from the selected agent's SKILL.md + L3 files."""
from __future__ import annotations
import json
from typing import Any, Callable
from . import artifacts, http_fetch, llm, mcp_client, sandbox
from .paths import AGENTS, WORKSPACE
from .skills import get_agent, list_agents, read_resource

def _tool(name, desc, props, required=None):
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": schema}}

TOOLS = [
    _tool("list_skills", "L1 catalog", {}),
    _tool("load_skill", "L2 load SKILL.md", {"slug": {"type": "string"}}, ["slug"]),
    _tool("load_skill_resource", "L3 read bundled file", {"slug": {"type": "string"}, "rel": {"type": "string"}}, ["slug", "rel"]),
    _tool("run_script", "Run bundled script sandboxed", {"slug": {"type": "string"}, "rel": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}, "allow_network": {"type": "boolean"}}, ["slug", "rel"]),
    _tool("run_python", "Run a short Python snippet", {"code": {"type": "string"}}, ["code"]),
    _tool("write_artifact", "Create md/docx/xlsx/pptx/chart/image", {"kind": {"type": "string"}, "name": {"type": "string"}, "payload": {"type": "object"}}, ["kind", "name"]),
    _tool("http_fetch", "HTTP GET/POST", {"url": {"type": "string"}, "method": {"type": "string"}, "body": {"type": "string"}}, ["url"]),
    _tool("call_mcp", "Call a configured MCP server", {"server": {"type": "string"}, "method": {"type": "string"}, "params": {"type": "object"}}, ["server", "method"]),
    _tool("finish", "Return the final answer", {"answer": {"type": "string"}}, ["answer"]),
]

class Runner:
    def __init__(self):
        self.loaded: set[str] = set()
        self.created: list[dict] = []

    def dispatch(self, name: str, args: dict) -> dict:
        if name == "list_skills":
            return {"ok": True, "catalog": [a.l1() for a in list_agents()]}
        if name == "load_skill":
            agent = get_agent(args["slug"])
            self.loaded.add(agent.slug)
            return {"ok": True, "slug": agent.slug, "name": agent.name, "description": agent.description,
                    "body": agent.body, "files": agent.files(), "examples": agent.examples}
        if name == "load_skill_resource":
            if args["slug"] not in self.loaded:
                return {"ok": False, "error": "load_skill first"}
            return {"ok": True, "content": read_resource(args["slug"], args["rel"])[:12000]}
        if name == "run_script":
            if args["slug"] not in self.loaded:
                return {"ok": False, "error": "load_skill first"}
            WORKSPACE.mkdir(exist_ok=True)
            return sandbox.run(AGENTS / args["slug"] / args["rel"], cwd=WORKSPACE,
                               args=args.get("args") or [], allow_network=bool(args.get("allow_network")))
        if name == "run_python":
            WORKSPACE.mkdir(exist_ok=True)
            return sandbox.run_snippet(args.get("code") or "", cwd=WORKSPACE)
        if name == "write_artifact":
            result = artifacts.build(args["kind"], args["name"], args.get("payload") or {})
            self.created.append(result)
            return result
        if name == "http_fetch":
            return http_fetch.fetch(args["url"], args.get("method") or "GET", args.get("body"))
        if name == "call_mcp":
            return mcp_client.call(args["server"], args["method"], args.get("params"))
        if name == "finish":
            return {"ok": True, "finished": True, "answer": args.get("answer", "")}
        return {"ok": False, "error": f"unknown tool {name}"}

    def run(self, slug: str, goal: str, on_event: Callable[[dict], None] | None = None, max_steps: int = 10) -> dict:
        agent = get_agent(slug)
        self.loaded.add(slug)
        if not llm.available():
            return self._offline(agent, goal)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": "Follow ONLY the loaded skill. Active: " + agent.slug + "\n\n" + agent.body[:6000]},
            {"role": "user", "content": json.dumps({"goal": goal, "examples": agent.examples, "files": agent.files()}, ensure_ascii=False)},
        ]
        answer = ""
        for _ in range(max_steps):
            message = llm.chat(messages, tools=TOOLS)
            messages.append(message)
            calls = message.get("tool_calls") or []
            if not calls:
                answer = message.get("content") or ""
                break
            for call in calls:
                fn = call["function"]["name"]
                raw = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    args = {}
                result = self.dispatch(fn, args)
                messages.append({"role": "tool", "tool_call_id": call.get("id", "x"),
                                 "content": json.dumps(result, ensure_ascii=False)[:8000]})
                if result.get("finished"):
                    return {"ok": True, "answer": result.get("answer") or "", "artifacts": self.created, "offline": False}
        return {"ok": True, "answer": answer, "artifacts": self.created, "offline": False}

    def _offline(self, agent, goal: str) -> dict:
        scripts = [f for f in agent.files() if f.startswith("scripts/") and f.endswith(".py")]
        notes = []
        if scripts:
            res = self.dispatch("run_script", {"slug": agent.slug, "rel": scripts[0], "args": [goal]})
            notes.append(res.get("stdout") or res.get("error") or "")
        art = self.dispatch("write_artifact", {"kind": "md", "name": agent.slug,
                            "payload": {"title": agent.name, "body": goal + "\n\n" + "\n".join(notes)}})
        return {"ok": True, "answer": f"[hors-ligne] Skill `{agent.slug}` — {art.get('name')}.",
                "artifacts": self.created, "offline": True}
