import os
from pathlib import Path
import shutil

from common import (Error, atomic, digest, files, fingerprint, git, inside, permits,
                    write_json)


def capture(root, destination, baseline):
    destination = Path(destination)
    destination.mkdir(parents=True)
    git(root, "clone", "--quiet", "--no-checkout", "--no-hardlinks", "--local", str(root), str(destination))
    for name, info in baseline["files"].items():
        source, target = root / name, destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if info["type"] == "symlink":
            target.symlink_to(info["value"])
        else:
            target.write_bytes(source.read_bytes())
            target.chmod(info["mode"])
    gitdir = Path(git(root, "rev-parse", "--absolute-git-dir").decode().strip())
    if (gitdir / "index").is_file():
        shutil.copyfile(gitdir / "index", destination / ".git/index")
    if fingerprint(root)["hash"] != baseline["hash"]:
        raise Error("Projekt während der Snapshot-Erstellung verändert.")
    if files(destination, baseline["files"]) != baseline["files"]:
        raise Error("Snapshot entspricht nicht dem erfassten Dateistand.")
    return destination


def modifications(baseline, workspace):
    current = files(workspace, baseline["files"])
    changed = sorted(name for name in baseline["files"].keys() | current.keys()
                     if baseline["files"].get(name) != current.get(name))
    return current, changed


def apply(root, workspace, baseline, allowed, transaction, check_stop=lambda: None):
    if (workspace / ".philharmonie").exists():
        raise Error("Generator hat geschützte Projektmetadaten erzeugt.")
    current, changed = modifications(baseline, workspace)
    if fingerprint(root)["hash"] != baseline["hash"]:
        raise Error("Fremde Änderungen während der Generierung; Snapshot bleibt zur Prüfung erhalten.")
    for name in changed:
        if not permits(name, allowed):
            raise Error(f"Generator änderte einen nicht freigegebenen Pfad: {name}")
        inside(root, name)
        if name in current and current[name]["type"] != "file":
            raise Error(f"Neue/geänderte Symlinks werden nicht automatisch übernommen: {name}")
    record = {"baseline": baseline["hash"], "changed": changed, "applied": [], "complete": False}
    write_json(transaction, record)
    for name in changed:
        check_stop()
        target = inside(root, name)
        previous = baseline["files"].get(name)
        if previous and (not target.is_file() or digest(target.read_bytes()) != previous.get("hash")
                         or target.stat().st_mode & 0o777 != previous.get("mode")):
            raise Error(f"Datei vor Übernahme verändert: {name}")
        if not previous and target.exists():
            raise Error(f"Neue fremde Datei vor Übernahme: {name}")
        if name not in current:
            target.unlink()
        else:
            atomic(target, (workspace / name).read_bytes())
            target.chmod(current[name]["mode"])
        record["applied"].append(name)
        write_json(transaction, record)
    record["complete"] = True
    write_json(transaction, record)
    return changed
