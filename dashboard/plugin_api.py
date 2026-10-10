"""Spotter backend routes, mounted at /api/plugins/hermes-spotter/ by Hermes (which supplies auth).

Reads and updates the local notes store. Makes no model or network call.
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


def _load_store():
    here = Path(__file__).resolve().parent
    for candidate in (here.parent / "spotter_store.py", here / "spotter_store.py"):
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("hermes_spotter_store", candidate)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("spotter_store.py not found")


store = _load_store()


class Dismiss(BaseModel):
    reason: str = Field(default="dismissed", pattern="^(dismissed|knew)$")


@router.get("/notes")
def get_notes():
    week = time.time() - 7 * 86400
    return {"notes": store.notes(), "stats": store.turn_stats(since=week)}


@router.post("/notes/{note_id}/dismiss")
def dismiss(note_id: str, body: Dismiss):
    if not note_id.isalnum() or len(note_id) > 32:
        raise HTTPException(400, "bad note id")
    if not any(n["id"] == note_id for n in store.notes()):
        raise HTTPException(404, "note not found")
    store.dismiss(note_id, body.reason)
    return {"ok": True}
