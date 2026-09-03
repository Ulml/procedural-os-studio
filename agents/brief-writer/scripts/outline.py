#!/usr/bin/env python3
import sys
goal = " ".join(sys.argv[1:]) or "brief"
print(f"# Outline\n\n- Contexte: {goal}\n- Points clés\n- Décision\n- Next step\n")
