"""Everything nanoPick remembers between visits.

The search roots ("only ever look in these folders"), the destination files are
copied to, and the last search — in ``~/.nanopick``. Deleting that folder makes
nanoPick forget everything; the files themselves were never stored here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_DIR_NAME = ".nanopick"

DEFAULT_SETTINGS = {
    # The folders nanoPick may look in. Empty means "the usual places".
    "roots": [],
    # Where "send a copy" goes. Chosen once, remembered.
    "destination": "",
    # The last search, so the page opens where you left off.
    "last_search": "",
}

DEFAULT_ROOTS = ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos", "OneDrive"]


def data_dir() -> Path:
    override = os.environ.get("NANOPICK_HOME")
    base = Path(override) if override else Path.home() / APP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def _settings_path() -> Path:
    return data_dir() / "settings.json"


def settings() -> dict:
    """What is remembered, with sensible answers for anything missing."""
    try:
        stored = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stored = {}
    out = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in stored:
            out[key] = stored[key]
    return out


def save_settings(patch: dict) -> dict:
    """Change what is remembered, and answer with the whole picture."""
    current = settings()
    for key in DEFAULT_SETTINGS:
        if key in patch:
            value = patch[key]
            if key == "roots":
                value = _clean_roots(value)
            elif key == "destination":
                value = str(value or "").strip()
            elif key == "last_search":
                value = str(value or "")[:200]
            current[key] = value
    try:
        _settings_path().write_text(json.dumps(current, indent=2), encoding="utf-8")
    except OSError:
        pass  # a read-only home folder is not worth failing a search over
    return current


def _clean_roots(value) -> list[str]:
    """Roots that exist, with no duplicates, keeping the order given."""
    roots: list[str] = []
    for item in value if isinstance(value, list) else []:
        text = str(item or "").strip()
        if not text:
            continue
        path = Path(text)
        try:
            resolved = str(path.resolve())
        except OSError:
            continue
        if path.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def search_roots() -> list[Path]:
    """The folders to look in: remembered ones, or the usual places."""
    remembered = settings()["roots"]
    if remembered:
        return [Path(r) for r in remembered]
    home = Path.home()
    roots: list[Path] = []
    for name in DEFAULT_ROOTS:
        candidate = home / name
        if candidate.is_dir():
            roots.append(candidate)
    return roots or [home]


def destination() -> str:
    """Where copies go; empty until the person picks a place."""
    return settings()["destination"]
