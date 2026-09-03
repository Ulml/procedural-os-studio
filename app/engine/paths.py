from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENTS = ROOT / "agents"
DATA = ROOT / "data"
WORKSPACE = ROOT / "workspace"
ARTIFACTS = ROOT / "artifacts"
STATIC = ROOT / "app" / "static"

for p in (AGENTS, DATA, WORKSPACE, ARTIFACTS, STATIC):
    p.mkdir(parents=True, exist_ok=True)
