"""Looking for files the way a person describes them.

A lost file is described in words, not paths: *"a picture with receipt in the
name, from last month"*. So the search here is words-in-the-name (all of them,
in any order), a kind of file, and roughly when it was last changed — and the
answers come back with the three things a person checks before anything else:
what it is, where it is, and how long ago.

The walk is capped, so a giant folder cannot make the page hang, and hidden
folders and build swamps are skipped on purpose.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

# How much work one search may do, so nothing can make the page hang.
MAX_SCAN = 20000
MAX_RESULTS = 200

SKIP_DIRS = {
    "$RECYCLE.BIN", "System Volume Information", "__pycache__",
    "node_modules", ".git", ".venv", "venv", "AppData",
}

KINDS = {
    "pictures": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".tif", ".tiff", ".svg"),
    "documents": (".pdf", ".docx", ".doc", ".odt", ".rtf", ".txt", ".md", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".epub"),
    "music": (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"),
    "video": (".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"),
    "archives": (".zip", ".rar", ".7z", ".tar", ".gz"),
}

WHEN_BUCKETS = ("today", "this week", "this month", "this year", "older")

# The file kinds worth reading when somebody asks what is INSIDE a file.
CONTENT_SUFFIXES = {".txt", ".md", ".csv", ".log", ".json", ".py", ".js", ".html", ".css", ".xml", ".yml", ".yaml", ".ini", ".tex", ".srt"}


def kind_of(name: str) -> str:
    """pictures, documents, music, video, archives — or 'other'."""
    suffix = Path(name).suffix.lower()
    for kind, endings in KINDS.items():
        if suffix in endings:
            return kind
    return "other"


def kind_word(kind: str) -> str:
    """The word a person would use, not the internal bucket."""
    words = {
        "pictures": "a picture",
        "documents": "a document",
        "music": "a song",
        "video": "a video",
        "archives": "a zip or archive",
        "other": "a file",
    }
    return words.get(kind, "a file")


def _bucket_for(age_seconds: float) -> str:
    if age_seconds <= 60 * 60 * 24:
        return "today"
    if age_seconds <= 60 * 60 * 24 * 7:
        return "this week"
    if age_seconds <= 60 * 60 * 24 * 30:
        return "this month"
    if age_seconds <= 60 * 60 * 24 * 365:
        return "this year"
    return "older"


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return "%d %s" % (value, unit) if unit == "bytes" else "%.1f %s" % (value, unit)
        value /= 1024
    return "%d bytes" % size


def human_when(seconds_ago: float) -> str:
    """'just now', '3 hours ago', 'last Tuesday-ish' — plain words only."""
    if seconds_ago < 60:
        return "just now"
    if seconds_ago < 60 * 60:
        minutes = int(seconds_ago // 60)
        return "%d minute%s ago" % (minutes, "" if minutes == 1 else "s")
    if seconds_ago < 60 * 60 * 24:
        hours = int(seconds_ago // 3600)
        return "%d hour%s ago" % (hours, "" if hours == 1 else "s")
    days = int(seconds_ago // 86400)
    if days == 1:
        return "yesterday"
    if days < 30:
        return "%d days ago" % days
    if days < 365:
        months = int(days // 30)
        return "%d month%s ago" % (months, "" if months == 1 else "s")
    years = max(1, int(days // 365))
    return "%d year%s ago" % (years, "" if years == 1 else "s")


def _walk(root: Path, seen: list):
    """Every file under root, skipping the swamps; appended into seen."""
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in entries:
        if entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        try:
            if entry.is_dir(follow_symlinks=False):
                _walk(Path(entry.path), seen)
            elif entry.is_file(follow_symlinks=False):
                seen.append(Path(entry.path))
        except OSError:
            continue


def _when_cutoff(bucket: str) -> float | None:
    now = time.time()
    spans = {
        "today": 60 * 60 * 24,
        "this week": 60 * 60 * 24 * 7,
        "this month": 60 * 60 * 24 * 30,
        "this year": 60 * 60 * 24 * 365,
    }
    if bucket in spans:
        return now - spans[bucket]
    if bucket == "older":
        return now - 60 * 60 * 24 * 365
    return None


def search(query: str = "", kind: str = "any", when: str = "any",
           roots=None, sort: str = "newest") -> dict:
    """The files that match the words, the kind and the when — best first.

    Every word in the query must appear in the file's name, in any position —
    "receipt last" matches "receipt-november-last.jpg". An empty query means
    "show me what is here", newest first.
    """
    words = [w.lower() for w in (query or "").split()]
    started = time.time()
    candidates: list[Path] = []
    for root in (roots if roots is not None else _roots_from_settings()):
        _walk(root, candidates)
        if len(candidates) >= MAX_SCAN:
            break
    candidates = candidates[:MAX_SCAN]

    cutoff = _when_cutoff(when)
    found = []
    for path in candidates:
        name = path.name
        lowered = name.lower()
        if any(word not in lowered for word in words):
            continue
        if kind != "any" and kind_of(name) != kind:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if cutoff is not None:
            if when == "older":
                if stat.st_mtime > cutoff:
                    continue
            elif stat.st_mtime < cutoff:
                continue
        found.append(_describe(path, stat))

    if sort == "biggest":
        found.sort(key=lambda item: -item["size"])
    elif sort == "name":
        found.sort(key=lambda item: item["name"].lower())
    else:
        found.sort(key=lambda item: -item["mtime"])

    return {
        "ok": True,
        "took_text": "%.1f seconds" % (time.time() - started),
        "scanned": len(candidates),
        "total": len(found),
        "shown": min(len(found), MAX_RESULTS),
        "results": found[:MAX_RESULTS],
    }


def _roots_from_settings():
    from . import store
    return store.search_roots()


def _describe(path: Path, stat: os.stat_result) -> dict:
    kind = kind_of(path.name)
    return {
        "path": str(path),
        "name": path.name,
        "kind": kind,
        "what": kind_word(kind),
        "folder": str(path.parent),
        "size": stat.st_size,
        "size_text": human_size(stat.st_size),
        "mtime": stat.st_mtime,
        "when": human_when(max(0.0, time.time() - stat.st_mtime)),
        "when_bucket": _bucket_for(max(0.0, time.time() - stat.st_mtime)),
    }


def describe(path) -> dict | None:
    """One file, described — or None when there is nothing there."""
    try:
        path = Path(path)
        stat = path.stat()
    except OSError:
        return None
    return _describe(path, stat)


# --------------------------------------------------------------------------
# Looking INSIDE files, not just at their names
# --------------------------------------------------------------------------
MAX_FILE_BYTES = 512 * 1024  # never read more than this of any one file
MAX_CONTENT_MATCHES = 40     # one page of "it says this here" is enough


def search_inside(query: str, kind: str = "any", roots=None) -> dict:
    """The files whose *contents* contain every word, with the line to show.

    This is the honest version of "search inside files": it reads text files
    only (the same kinds the previews show), never more than 512 KB of any
    one file, and answers with the actual line that matched. Nothing is
    indexed or remembered — each search reads only what it needs to.
    """
    words = [w.lower() for w in (query or "").split()]
    if not words:
        return {"ok": True, "total": 0, "matches": [],
                "why": "Type some words first, then press “look inside files”."}

    candidates: list[Path] = []
    for root in (roots if roots is not None else _roots_from_settings()):
        _walk(root, candidates)
        if len(candidates) >= MAX_SCAN:
            break
    candidates = candidates[:MAX_SCAN]

    matches: list[dict] = []
    for path in candidates:
        if path.suffix.lower() not in CONTENT_SUFFIXES:
            continue
        if kind != "any" and kind_of(path.name) != kind:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            if all(word in lowered for word in words):
                matches.append({
                    "path": str(path),
                    "name": path.name,
                    "what": kind_word(kind_of(path.name)),
                    "line": number,
                    "snippet": line.strip()[:200],
                })
                break  # one matching line per file is enough for a page
        if len(matches) >= MAX_CONTENT_MATCHES:
            break

    return {"ok": True, "total": len(matches), "matches": matches, "why": ""}
