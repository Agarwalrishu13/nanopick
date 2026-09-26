"""The pages and the addresses the page talks to.

nanoPick can read files (for previews), hand files to the operating system and
write copies — so every address that *does* something refuses requests that did
not come from this app's own page: an ``Origin`` header, if present, must be
this machine, and JSON routes must actually be sent as JSON. A web page in
another tab must not be able to drive it.

Previews only ever serve files that live inside the folders nanoPick was
allowed to look in — a made-up path cannot smuggle anything out.
"""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse

from . import APP_NAME, __version__, actions, finder, store
from .httpbase import App, Bytes, Error, Json

PORT = 8779

_OWN_ORIGINS = ("127.0.0.1", "localhost", "::1", "[::1]")

# Previews never read more than this, so a huge file cannot choke the page.
MAX_IMAGE_PREVIEW = 10 * 1024 * 1024
MAX_TEXT_PREVIEW = 256 * 1024
TEXT_SUFFIXES = (".txt", ".md", ".csv", ".log", ".json", ".py", ".js", ".html", ".css", ".xml", ".yml", ".yaml", ".ini")

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/heic", ".heic")


def create_app() -> App:
    app = App(APP_NAME, Path(__file__).parent / "web", version=__version__)

    def _from_local_page(request, require_json: bool = False) -> bool:
        origin = request.header("Origin")
        if origin:
            host = urlparse(origin).hostname or ""
            if host not in _OWN_ORIGINS:
                return False
        if require_json:
            content_type = (request.header("Content-Type") or "").split(";")[0].strip()
            if content_type != "application/json":
                return False
        return True

    def _in_allowed_roots(path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        for root in store.search_roots():
            try:
                resolved.relative_to(Path(root).resolve())
                return True
            except (ValueError, OSError):
                continue
        return False

    @app.get("/api/health")
    def health(_request):
        return Json({
            "ok": True,
            "app": APP_NAME,
            "version": __version__,
            "roots": [str(r) for r in store.search_roots()],
            "destination": store.destination(),
        })

    @app.get("/api/settings")
    def get_settings(_request):
        return Json({
            "ok": True,
            "roots": [str(r) for r in store.search_roots()],
            "remembered_roots": store.settings()["roots"],
            "destination": store.destination(),
            "last_search": store.settings()["last_search"],
        })

    @app.post("/api/roots")
    def set_roots(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        saved = store.save_settings({"roots": payload.get("roots") or []})
        return Json({"ok": True, "roots": saved["roots"],
                     "why": "" if saved["roots"] else
                     "None of those folders exist, so the usual places are being used."})

    @app.post("/api/destination")
    def set_destination(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        where = str(payload.get("destination") or "").strip()
        if where and not Path(where).is_dir():
            return Error("There is no folder at %s." % where)
        store.save_settings({"destination": where})
        return Json({"ok": True, "destination": where})

    @app.post("/api/pick-folder")
    def pick_folder(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        answer = actions.pick_folder_dialog()
        if not answer.get("ok"):
            return Json({"ok": False, "why": answer.get("why", "No folder was chosen.")})
        return Json({"ok": True, "path": answer["path"]})

    @app.get("/api/search")
    def search(request):
        query = request.q("q", "")
        kind = request.q("kind", "any")
        when = request.q("when", "any")
        sort = request.q("sort", "newest")
        if kind not in ("any", *finder.KINDS):
            kind = "any"
        if when not in ("any", *finder.WHEN_BUCKETS):
            when = "any"
        if sort not in ("newest", "biggest", "name"):
            sort = "newest"
        store.save_settings({"last_search": query})
        return Json(finder.search(query, kind=kind, when=when, sort=sort))

    @app.get("/api/one")
    def one(request):
        path = request.q("path", "")
        facts = finder.describe(path) if path else None
        if not facts:
            return Error("There is nothing to describe at that address.")
        return Json({"ok": True, "file": facts,
                     "previewable": _previewable(Path(facts["path"]))})

    @app.get("/api/preview")
    def preview(request):
        path = Path(request.q("path", ""))
        if not path.is_file() or not _in_allowed_roots(path):
            return Error("nanoPick is not allowed to show that file — it lives outside the folders you let it look in.")
        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            try:
                data = path.read_bytes()[:MAX_TEXT_PREVIEW]
            except OSError:
                return Error("That file could not be read.")
            return Bytes(data, "text/plain; charset=utf-8")
        guessed = mimetypes.guess_type(str(path))[0] or ""
        if not guessed.startswith(("image/", "video/", "audio/")):
            return Error("There is no preview for this kind of file — try “Show me the folder” instead.")
        try:
            size = path.stat().st_size
        except OSError:
            return Error("That file could not be read.")
        if size > MAX_IMAGE_PREVIEW:
            return Error("That file is too big to show here (%s)." % finder.human_size(size))
        try:
            data = path.read_bytes()
        except OSError:
            return Error("That file could not be read.")
        return Bytes(data, guessed)

    def _previewable(path: Path) -> bool:
        suffix = path.suffix.lower()
        if suffix in TEXT_SUFFIXES:
            return True
        guessed = mimetypes.guess_type(str(path))[0] or ""
        return guessed.startswith(("image/", "video/", "audio/"))

    @app.post("/api/open")
    def open_one(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        return Json(actions.open_file((request.json() or {}).get("path", "")))

    @app.post("/api/reveal")
    def reveal_one(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        return Json(actions.reveal((request.json() or {}).get("path", "")))

    @app.post("/api/copy")
    def copy_one(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        where = payload.get("destination") or store.destination()
        if not where:
            return Error("First choose where copies should go — press “Where copies go”.")
        return Json(actions.copy_to(payload.get("path", ""), where))

    @app.post("/api/pack")
    def pack_many(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        payload = request.json() or {}
        where = payload.get("destination") or store.destination()
        if not where:
            return Error("First choose where copies should go — press “Where copies go”.")
        return Json(actions.pack(payload.get("paths") or [], where))

    @app.post("/api/open-destination")
    def open_destination(request):
        if not _from_local_page(request, require_json=True):
            return Error("This app only answers to pages on this computer.", 403)
        where = store.destination()
        if not where:
            return Error("No destination has been chosen yet.")
        return Json(actions.reveal(where) if sys.platform == "win32" else actions.open_file(where))

    return app


def main() -> None:
    app = create_app()
    app.serve(port=PORT)
