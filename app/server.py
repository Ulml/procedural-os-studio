#!/usr/bin/env python3
"""Procedural OS Studio — stdlib HTTP server + JSON API + static UI."""
from __future__ import annotations
import json, os, sys, traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine import compiler, github_sync, llm, memory, mcp_client
from app.engine.paths import ARTIFACTS, STATIC
from app.engine.runner import Runner
from app.engine.scheduler import Scheduler
from app.engine.skills import get_agent, list_agents, save_agent, write_resource

def _json(handler, code: int, payload) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(raw)

def _read(handler) -> dict:
    length = int(handler.headers.get("Content-Length") or 0)
    return json.loads(handler.rfile.read(length).decode("utf-8")) if length else {}

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return _json(self, 200, {"ok": True, "llm": llm.settings(), "llm_up": llm.available(), "mcp": mcp_client.servers()})
        if path == "/api/agents":
            agents = [{**a.l1(), "files": a.files(), "cron": a.cron, "examples": a.examples} for a in list_agents()]
            return _json(self, 200, {"agents": agents})
        if path.startswith("/api/agents/") and path.endswith("/memory"):
            return _json(self, 200, {"items": memory.list_items(path.split("/")[3])})
        if path.startswith("/api/agents/") and path.count("/") == 3:
            slug = path.rstrip("/").split("/")[-1]
            try:
                a = get_agent(slug)
            except KeyError:
                return _json(self, 404, {"error": "unknown agent"})
            return _json(self, 200, {"slug": a.slug, "name": a.name, "description": a.description,
                                     "body": a.body, "files": a.files(), "cron": a.cron,
                                     "examples": a.examples, "metadata": a.metadata})
        if path.startswith("/api/artifacts/"):
            file = ARTIFACTS / path.split("/")[-1]
            if not file.exists():
                return _json(self, 404, {"error": "missing artifact"})
            data = file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f"attachment; filename={file.name}")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/":
            path = "/index.html"
        file = STATIC / path.lstrip("/")
        if file.exists() and file.is_file():
            data = file.read_bytes()
            ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                     ".css": "text/css; charset=utf-8"}.get(file.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        _json(self, 404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = _read(self)
            if path == "/api/agents":
                return _json(self, 200, compiler.compile_skill(
                    body.get("natural_language") or "", name=body.get("name"),
                    example=body.get("example") or {}, use_llm=bool(body.get("use_llm", True))))
            if path.startswith("/api/agents/") and path.endswith("/instruction"):
                slug = path.split("/")[3]
                save_agent(slug, description=body.get("description"), body=body.get("body"),
                           scripts=body.get("scripts"), cron=body.get("cron"))
                if body.get("l3_path") and body.get("l3_content") is not None:
                    write_resource(slug, body["l3_path"], body["l3_content"])
                a = get_agent(slug)
                return _json(self, 200, {"ok": True, "body": a.body, "files": a.files()})
            if path.startswith("/api/agents/") and path.endswith("/chat"):
                slug = path.split("/")[3]
                text = (body.get("message") or "").strip()
                if not text:
                    return _json(self, 400, {"error": "empty message"})
                if body.get("as_memory") or text.lower().startswith(("corrige", "modifie", "ajoute", "change", "fix", "update")):
                    return _json(self, 200, {"kind": "memory", "item": memory.add_item(slug, text)})
                return _json(self, 200, {"kind": "run", **Runner().run(slug, text)})
            if path.startswith("/api/agents/") and path.endswith("/run"):
                slug = path.split("/")[3]
                return _json(self, 200, Runner().run(slug, body.get("goal") or get_agent(slug).description))
            if path.startswith("/api/agents/") and path.endswith("/memory/apply"):
                slug = path.split("/")[3]
                applied = memory.apply_selected(slug)
                if body.get("push_github"):
                    applied["github"] = github_sync.push_agent(slug)
                return _json(self, 200, applied)
            if path == "/api/memory/select":
                return _json(self, 200, {"items": memory.set_selected(body.get("ids") or [], bool(body.get("selected", True)))})
            return _json(self, 404, {"error": "not found"})
        except Exception as exc:
            traceback.print_exc()
            return _json(self, 500, {"error": str(exc)})

def scheduled_run(slug: str, goal: str) -> None:
    try:
        Runner().run(slug, goal)
    except Exception as exc:
        sys.stderr.write(f"cron {slug}: {exc}\n")

def main() -> None:
    host = os.environ.get("APP_HOST", "127.0.0.1")
    port = int(os.environ.get("APP_PORT", "8787"))
    Scheduler(scheduled_run).start()
    print(f"Procedural OS Studio  http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

if __name__ == "__main__":
    main()
