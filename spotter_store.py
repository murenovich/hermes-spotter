"""Spotter: the local notes store, shared by the turn hook (``__init__.py``) and the backend API
(``dashboard/plugin_api.py``). Both load this file by path.

One folder, ``<hermes root>/spotter/``, shared by every profile of the install so "All chats" works:
  notes.jsonl   one note per line (appended; dismissals are separate "dismiss" lines)
  turns.jsonl   one line per finished turn: time, profile, platform, tool-call count. No message content.
                It exists only to measure how often the threshold would trigger.
Nothing here makes a network or model call.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

try:
    import fcntl  # POSIX
except ImportError:  # pragma: no cover - Windows: appends are still line-sized
    fcntl = None

MAX_NOTES = 500


def hermes_root() -> Path:
    try:
        from hermes_constants import get_default_hermes_root  # type: ignore
        return Path(get_default_hermes_root())
    except Exception:
        return Path(os.environ.get("HERMES_HOME") or Path.home() / ".hermes")


def store_dir() -> Path:
    return hermes_root() / "spotter"


def _append(name: str, record: dict) -> None:
    d = store_dir()
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    fd = os.open(d / name, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line.encode("utf-8"))
    finally:
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read(name: str) -> list[dict]:
    p = store_dir() / name
    out: list[dict] = []
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue  # a torn or foreign line never breaks the pane
                if isinstance(rec, dict):
                    out.append(rec)
    except FileNotFoundError:
        pass
    return out


def tool_calls_this_turn(history) -> int:
    """Tool calls made after the last user message (i.e. during this turn)."""
    if not isinstance(history, list):
        return 0
    last_user = -1
    for i, m in enumerate(history):
        if isinstance(m, dict) and m.get("role") == "user":
            last_user = i
    n = 0
    for m in history[last_user + 1:]:
        if isinstance(m, dict) and m.get("role") == "assistant" and isinstance(m.get("tool_calls"), list):
            n += len(m["tool_calls"])
    return n


def record_turn(*, profile: str, platform: str, session_id: str, tools: int, triggered: bool) -> None:
    _append("turns.jsonl", {"t": time.time(), "profile": profile, "platform": platform or "",
                            "session": session_id or "", "tools": tools, "triggered": triggered})


def add_note(*, kind: str, headline: str, detail: str, more: str = "", profile: str, platform: str,
             session_id: str, title: str = "") -> dict:
    note = {"type": "note", "id": uuid.uuid4().hex[:12], "t": time.time(),
            "kind": "risk" if kind == "risk" else "info", "headline": headline[:160], "detail": detail[:400],
            "more": more[:2000], "profile": profile, "platform": platform or "", "session": session_id or "",
            "title": title[:120]}
    _append("notes.jsonl", note)
    return note


def dismiss(note_id: str, reason: str) -> None:
    _append("notes.jsonl", {"type": "dismiss", "id": note_id, "t": time.time(),
                            "reason": "knew" if reason == "knew" else "dismissed"})


def notes() -> list[dict]:
    """Newest first, with any dismissal folded in as ``state``."""
    recs = _read("notes.jsonl")
    state = {r["id"]: r.get("reason", "dismissed") for r in recs if r.get("type") == "dismiss" and r.get("id")}
    out = [dict(r, state=state.get(r["id"], "open")) for r in recs if r.get("type") == "note" and r.get("id")]
    out.sort(key=lambda r: r.get("t", 0), reverse=True)
    return out[:MAX_NOTES]


def turn_stats(since: float = 0.0) -> dict:
    turns = [r for r in _read("turns.jsonl") if r.get("t", 0) >= since]
    return {"turns": len(turns), "triggered": sum(1 for r in turns if r.get("triggered")),
            "since": min((r["t"] for r in turns), default=None)}
