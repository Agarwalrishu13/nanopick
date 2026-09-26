"""Command line entry point.

Three ways in, and the first one is the only one most people will ever need::

    python start.py              # start the app and open the browser
    python -m nanopick           # the same thing
    python -m nanopick doctor    # say what this computer has, and stop
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import APP_NAME, TAGLINE, __version__, store
from .server import PORT


def _doctor() -> int:
    print()
    print("  %s %s — what this computer has" % (APP_NAME, __version__))
    print("  " + "-" * 62)
    print("  Python %s" % sys.version.split()[0])
    print("  You are in: %s" % Path.cwd())
    print("  nanoPick remembers things in: %s" % store.data_dir())
    print()
    roots = store.search_roots()
    print("  Folders it will look in (%d):" % len(roots))
    for root in roots:
        print("        %s" % root)
    where = store.destination()
    print()
    print("  Where copies go: %s" % (where or "not chosen yet — the page will ask"))
    print()
    return 0


def main(argv: list | None = None) -> int:
    # A Windows console on a legacy code page cannot print every character in
    # the summary, and a crash while printing it would be a silly way to fail.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="nanopick",
        description="%s — %s." % (APP_NAME, TAGLINE),
        epilog="Run it with no arguments and a browser window opens.",
    )
    parser.add_argument("command", nargs="?", default="run", choices=["run", "doctor", "version"])
    parser.add_argument("--port", type=int, default=PORT, help="which port to use (default %d)" % PORT)
    parser.add_argument("--host", default="127.0.0.1", help="address to listen on (default: this computer only)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    parser.add_argument("--version", action="store_true", help="print the version and stop")
    args = parser.parse_args(argv)

    if args.version or args.command == "version":
        print("%s %s" % (APP_NAME, __version__))
        return 0
    if args.command == "doctor":
        return _doctor()

    from .server import create_app

    app = create_app()
    try:
        app.serve(host=args.host, port=args.port, open_browser=not args.no_browser)
    except OSError as exc:
        print("\n  Could not start on %s:%d (%s).\n  Try a different port: --port %d\n"
              % (args.host, args.port, exc, args.port + 1))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
