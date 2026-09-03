"""Honor cron.json sitting in each agent folder."""

from __future__ import annotations

import threading
import time
from datetime import datetime

from .skills import list_agents


def _matches(expr: str, now: datetime) -> bool:
    parts = expr.split()
    if len(parts) != 5:
        return False
    minute, hour, dom, month, dow = parts

    def field(value: int, token: str, minimum: int, maximum: int) -> bool:
        if token == "*":
            return True
        for chunk in token.split(","):
            if chunk.startswith("*/"):
                step = int(chunk[2:] or "1")
                if value % step == 0:
                    return True
            elif "-" in chunk:
                a, b = chunk.split("-", 1)
                if int(a) <= value <= int(b):
                    return True
            elif chunk.isdigit() and int(chunk) == value:
                return True
        return False

    return (
        field(now.minute, minute, 0, 59)
        and field(now.hour, hour, 0, 23)
        and field(now.day, dom, 1, 31)
        and field(now.month, month, 1, 12)
        and field(now.isoweekday() % 7, dow, 0, 6)
    )


class Scheduler:
    def __init__(self, on_due):
        self.on_due = on_due
        self._stop = threading.Event()
        self._fired: set[str] = set()

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            now = datetime.now()
            key_prefix = now.strftime("%Y%m%d%H%M")
            for agent in list_agents():
                cron = agent.cron or {}
                if not cron.get("enabled") or not cron.get("cron"):
                    continue
                stamp = f"{agent.slug}:{key_prefix}"
                if stamp in self._fired:
                    continue
                if _matches(str(cron["cron"]), now):
                    self._fired.add(stamp)
                    try:
                        self.on_due(agent.slug, cron.get("goal") or agent.description)
                    except Exception:
                        pass
            time.sleep(20)
