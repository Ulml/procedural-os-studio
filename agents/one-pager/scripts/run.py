#!/usr/bin/env python3
import json, sys
from pathlib import Path
goal = " ".join(sys.argv[1:]) or "run"
out = Path("result.md")
out.write_text(f"# Result\n\nGoal: {goal}\n", encoding="utf-8")
print(json.dumps({"wrote": str(out.resolve())}))
