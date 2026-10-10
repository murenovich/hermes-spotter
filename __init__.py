"""Spotter, agent half: watches finished turns.

Hermes calls ``post_llm_call`` once per successful turn, after the tool loop. Spotter counts the tool
calls made during the turn and records that count (no message content) so the trigger rate can be measured.

SPIKE (build card 1): when a turn reaches the threshold it writes a placeholder note. No model is called.
Turns from internal forks are never passed to this hook by Hermes.
"""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 5


def _load_store():
    path = Path(__file__).resolve().parent / "spotter_store.py"
    spec = importlib.util.spec_from_file_location("hermes_spotter_store", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


store = _load_store()


def make_hook(profile_name):
    def on_turn(session_id="", conversation_history=None, platform="", **_):
        try:
            tools = store.tool_calls_this_turn(conversation_history)
            triggered = tools >= DEFAULT_THRESHOLD
            profile = profile_name()
            store.record_turn(profile=profile, platform=platform, session_id=session_id, tools=tools,
                              triggered=triggered)
            if triggered:
                store.add_note(kind="info", headline=f"Spotter saw a {tools}-step turn",
                               detail="Placeholder from the spike: the turn reached the plugin. "
                                      "No model was asked; real notes come in the next step.",
                               profile=profile, platform=platform, session_id=session_id)
        except Exception:  # an observer must never disturb the turn
            logger.debug("spotter: turn hook failed", exc_info=True)
    return on_turn


def register(ctx):
    ctx.register_hook("post_llm_call", make_hook(lambda: getattr(ctx, "profile_name", "default") or "default"))
