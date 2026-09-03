from __future__ import annotations

import os
import subprocess
from pathlib import Path

DENIED = {
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLM_API_KEY",
    "GITHUB_TOKEN",
    "HF_TOKEN",
}


def run(
    script: Path,
    *,
    cwd: Path,
    args: list[str] | None = None,
    timeout: int = 30,
    allow_network: bool = False,
) -> dict:
    if not script.exists():
        return {"ok": False, "error": f"missing {script}"}
    if script.suffix not in {".py", ".sh", ".js"}:
        return {"ok": False, "error": f"blocked extension {script.suffix}"}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(cwd), "LANG": "C.UTF-8"}
    if not allow_network:
        env["NO_PROXY"] = env["no_proxy"] = "*"
    if script.suffix == ".py":
        cmd = ["python3", str(script), *(args or [])]
    elif script.suffix == ".js":
        cmd = ["node", str(script), *(args or [])]
    else:
        cmd = ["bash", str(script), *(args or [])]
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout {timeout}s"}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-4000:],
    }


def run_snippet(code: str, *, cwd: Path, timeout: int = 20) -> dict:
    path = cwd / "_snippet.py"
    path.write_text(code, encoding="utf-8")
    try:
        return run(path, cwd=cwd, timeout=timeout)
    finally:
        if path.exists():
            path.unlink()
