"""Spike tests: hook -> notes store -> API. Temp HERMES_HOME, fake histories, no model, no real data."""
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    plugin = load("spotter_plugin_under_test", ROOT / "__init__.py")
    monkeypatch.setattr(plugin.store, "hermes_root", lambda: tmp_path)
    api = load("spotter_api_under_test", ROOT / "dashboard" / "plugin_api.py")
    monkeypatch.setattr(api.store, "hermes_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(api.router, prefix="/api/plugins/hermes-spotter")
    return plugin, TestClient(app), tmp_path


def history(tool_calls_now, tool_calls_before=0):
    call = {"id": "c", "type": "function", "function": {"name": "terminal", "arguments": "{}"}}
    h = [{"role": "user", "content": "earlier"}]
    h += [{"role": "assistant", "content": "", "tool_calls": [call]} for _ in range(tool_calls_before)]
    h += [{"role": "assistant", "content": "ok"}, {"role": "user", "content": "now do the thing"}]
    h += [{"role": "assistant", "content": "", "tool_calls": [call]} for _ in range(tool_calls_now)]
    h += [{"role": "assistant", "content": "done"}]
    return h


def test_counts_only_this_turn(env):
    plugin, _, _ = env
    assert plugin.store.tool_calls_this_turn(history(3, tool_calls_before=9)) == 3
    assert plugin.store.tool_calls_this_turn(None) == 0


def test_short_turn_records_stat_but_no_note(env):
    plugin, client, home = env
    plugin.make_hook(lambda: "default")(session_id="s1", conversation_history=history(4), platform="cli")
    r = client.get("/api/plugins/hermes-spotter/notes").json()
    assert r["notes"] == [] and r["stats"]["turns"] == 1 and r["stats"]["triggered"] == 0
    assert "now do the thing" not in (home / "spotter" / "turns.jsonl").read_text()  # no content stored


def test_long_turn_writes_note_and_dismiss_works(env):
    plugin, client, _ = env
    plugin.make_hook(lambda: "work")(session_id="s2", conversation_history=history(5), platform="telegram")
    notes = client.get("/api/plugins/hermes-spotter/notes").json()["notes"]
    assert len(notes) == 1 and notes[0]["session"] == "s2" and notes[0]["profile"] == "work"
    assert notes[0]["state"] == "open"
    nid = notes[0]["id"]
    assert client.post(f"/api/plugins/hermes-spotter/notes/{nid}/dismiss", json={"reason": "knew"}).status_code == 200
    assert client.get("/api/plugins/hermes-spotter/notes").json()["notes"][0]["state"] == "knew"
    assert client.post("/api/plugins/hermes-spotter/notes/nope/dismiss", json={}).status_code == 404
    assert client.post(f"/api/plugins/hermes-spotter/notes/{nid}/dismiss", json={"reason": "x"}).status_code == 422


def test_hook_never_raises(env, monkeypatch):
    plugin, _, _ = env
    monkeypatch.setattr(plugin.store, "record_turn", lambda **k: 1 / 0)
    plugin.make_hook(lambda: "default")(conversation_history=history(9))  # swallowed


def test_torn_line_is_skipped(env):
    plugin, client, home = env
    plugin.make_hook(lambda: "default")(session_id="s3", conversation_history=history(6))
    with open(home / "spotter" / "notes.jsonl", "a") as f:
        f.write('{"type":"note","id":"abc"')  # half-written
    assert len(client.get("/api/plugins/hermes-spotter/notes").json()["notes"]) == 1
