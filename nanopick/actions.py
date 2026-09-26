"""The things nanoPick does to a file once it has been found.

Four actions, each named after what a person asked for, each returning plain
sentences about what happened. Two rules hold everywhere:

1. Nothing is ever moved or deleted. "Send a copy" makes a copy.
2. A copy never overwrites what is already there — a name that exists gets
   " (2)" before its ending, exactly like a browser download would.
"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path


def open_file(path) -> dict:
    """Hand the file to the operating system, the way a double-click would."""
    target = Path(path)
    if not target.is_file():
        return {"ok": False, "said": "That file is not there any more."}
    try:
        if sys.platform == "win32":
            os.startfile(str(target))  # noqa: S606 - the person asked for this file by name
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except OSError as exc:
        return {"ok": False, "said": "The computer refused to open it (%s)." % exc}
    return {"ok": True, "said": "Opened %s." % target.name}


def reveal(path) -> dict:
    """Show the folder the file lives in, with the file chosen."""
    target = Path(path)
    if not target.exists():
        return {"ok": False, "said": "That file is not there any more."}
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent)])
    except OSError as exc:
        return {"ok": False, "said": "The computer refused (%s)." % exc}
    return {"ok": True, "said": "Showing the folder it lives in."}


def unique_path(folder: Path, name: str) -> Path:
    """A name that is not taken yet: report.pdf, then report (2).pdf."""
    candidate = folder / name
    if not candidate.exists():
        return candidate
    stem = Path(name).stem
    ending = Path(name).suffix
    for number in range(2, 1000):
        candidate = folder / ("%s (%d)%s" % (stem, number, ending))
        if not candidate.exists():
            return candidate
    return folder / ("%s-%d%s" % (stem, os.getpid(), ending))


def copy_to(path, destination) -> dict:
    """A copy of the file, in the folder chosen — the original untouched."""
    target = Path(path)
    folder = Path(destination)
    if not target.is_file():
        return {"ok": False, "said": "That file is not there any more."}
    if not folder.is_dir():
        return {"ok": False, "said": "There is no folder at %s to copy into." % folder}
    where = unique_path(folder, target.name)
    try:
        where.write_bytes(target.read_bytes())
    except OSError as exc:
        return {"ok": False, "said": "The copy did not go through (%s)." % exc}
    return {"ok": True, "said": "Copied to %s." % where, "copied_to": str(where)}


def pack(paths, destination) -> dict:
    """Several files become one zip, in the folder chosen. Originals stay."""
    if not paths:
        return {"ok": False, "said": "Nothing was chosen to pack."}
    folder = Path(destination) if destination else Path.home() / "Desktop"
    if not folder.is_dir():
        return {"ok": False, "said": "There is no folder at %s to pack into." % folder}

    files: list[Path] = []
    skipped: list[str] = []
    for item in paths:
        candidate = Path(item)
        if candidate.is_file():
            files.append(candidate)
        else:
            skipped.append(candidate.name)
    if not files:
        return {"ok": False, "said": "None of the chosen things are files that can be packed."}

    name = files[0].stem if len(files) == 1 else "nanoPick bundle"
    where = unique_path(folder, "%s.zip" % name)
    try:
        with zipfile.ZipFile(where, "w", zipfile.ZIP_DEFLATED) as bundle:
            for item in files:
                bundle.write(item, arcname=item.name)
    except OSError as exc:
        return {"ok": False, "said": "The zip did not go through (%s)." % exc}

    said = "Packed %d file%s into %s." % (
        len(files), "" if len(files) == 1 else "s", where.name)
    if skipped:
        said += " %d thing%s %s not files, so they were left out." % (
            len(skipped), "" if len(skipped) == 1 else "s",
            "was" if len(skipped) == 1 else "were")
    return {"ok": True, "said": said, "packed_to": str(where), "count": len(files)}


def pick_folder_dialog() -> dict:
    """Ask the operating system for a folder, if this computer can do that."""
    if sys.platform == "win32":
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;"
            "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
            "$f.Description = 'Where should nanoPick put copies?';"
            "if ($f.ShowDialog() -eq 'OK') { Write-Output $f.SelectedPath }"
        )
        try:
            done = subprocess.run(
                ["powershell", "-NoProfile", "-STA", "-Command", script],
                capture_output=True, text=True, timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "why": "The folder window did not open."}
        chosen = (done.stdout or "").strip()
        if chosen and Path(chosen).is_dir():
            return {"ok": True, "path": chosen}
        return {"ok": False, "why": "No folder was chosen."}
    if sys.platform == "darwin":
        script = 'osascript -e \'POSIX path of (choose folder with prompt "Where should nanoPick put copies?")\''
        try:
            done = subprocess.run(script, shell=True, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return {"ok": False, "why": "The folder window did not open."}
        chosen = (done.stdout or "").strip()
        if chosen and Path(chosen).is_dir():
            return {"ok": True, "path": chosen}
    return {"ok": False, "why": "This computer cannot open a folder window from here — type the folder instead."}
