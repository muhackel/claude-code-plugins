import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
from datetime import datetime, timezone


class Error(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise Error(f"JSON nicht lesbar: {path}: {exc}") from exc


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise Error(f"Symlink als Schreibziel abgelehnt: {path}")
    if not isinstance(data, bytes):
        data = data.encode()
    fd, temp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@contextlib.contextmanager
def lock(path, blocking=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise Error(f"Ein anderer Auftrag hält die Sperre: {path.name}") from exc
        yield fd
    finally:
        os.close(fd)


def identifier(value):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value):
        raise Error("ID muss aus Kleinbuchstaben, Ziffern und Bindestrichen bestehen (max. 64).")
    return value


def relative(value):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not value or path == Path("."):
        raise Error(f"Konkreter relativer Pfad erforderlich: {value}")
    if any(part in (".git", ".philharmonie") for part in path.parts):
        raise Error(f"Geschützter Pfad: {value}")
    return path.as_posix()


def inside(root, value):
    root = Path(root).resolve()
    path = root / relative(value)
    for parent in [path, *path.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise Error(f"Symlink im Arbeitsziel abgelehnt: {path}")
    if not path.resolve().is_relative_to(root):
        raise Error(f"Pfad außerhalb des Projekts: {path}")
    return path


def git(root, *args, check=True):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if check and result.returncode:
        raise Error(result.stderr.decode(errors="replace").strip())
    return result.stdout


def project(path):
    root = Path(path).resolve()
    top = git(root, "rev-parse", "--show-toplevel").decode().strip()
    if Path(top).resolve() != root:
        raise Error("Arbeitsverzeichnis muss die Wurzel des Git-Checkouts sein.")
    for folder in (root / ".philharmonie", root / ".philharmonie/local"):
        if folder.is_symlink():
            raise Error(f"Symlink als Zustandsverzeichnis abgelehnt: {folder}")
    return root


def files(root, include=()):
    paths = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0")
    paths += [os.fsencode(name) for name in include]
    result = {}
    for raw in sorted(set(paths)):
        if not raw:
            continue
        name = os.fsdecode(raw)
        if name.split("/")[0] == ".philharmonie":
            continue
        path = root / name
        if path.is_symlink():
            result[name] = {"type": "symlink", "value": os.readlink(path)}
        elif path.is_file():
            result[name] = {"type": "file", "hash": digest(path.read_bytes()),
                            "mode": path.stat().st_mode & 0o777}
        elif path.is_dir():
            raise Error(f"Untermodul/Verzeichnis im Git-Index benötigt eigenen Auftrag: {name}")
    return result


def fingerprint(root):
    data = {"head": git(root, "rev-parse", "HEAD").decode().strip(),
            "index": digest(git(root, "ls-files", "--stage", "-z")), "files": files(root)}
    data["hash"] = digest(json.dumps(data, sort_keys=True).encode())
    return data


def write_preflight(root, allowed, include_dirty=()):
    branch = git(root, "symbolic-ref", "--short", "HEAD", check=False).decode().strip()
    if not branch or branch in ("main", "master"):
        raise Error("Schreibauftrag benötigt einen Feature-Branch.")
    if not allowed:
        raise Error("Mindestens ein freigegebener Schreibpfad ist erforderlich.")
    for name in allowed:
        inside(root, name)
    changed = git(root, "diff", "--name-only", "-z", "HEAD").split(b"\0")
    changed += git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    dirty = {os.fsdecode(x) for x in changed if x and not x.startswith(b".philharmonie/")}
    conflicting = {p for p in dirty if permits(p, allowed) and p not in include_dirty}
    if conflicting:
        raise Error("Vorhandene Änderungen im Schreibbereich zuerst zuordnen (--include-dirty): "
                    + ", ".join(sorted(conflicting)))


def permits(name, allowed):
    return any(name == entry or name.startswith(entry.rstrip("/") + "/") for entry in allowed)


def identity(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        return {"host": socket.gethostname(), "boot": boot, "pid": pid,
                "start": stat[19], "state": stat[0]}
    except FileNotFoundError:
        return None
    except (OSError, IndexError) as exc:
        raise Error(f"Prozessidentität nicht überprüfbar: {pid}") from exc


def alive(record):
    if not record:
        return False
    if record["host"] != socket.gethostname():
        raise Error("Prozess gehört zu einem anderen Host; kein automatischer Neustart.")
    current = identity(record["pid"])
    return bool(current and current["state"] != "Z" and
                all(current[k] == record[k] for k in ("host", "boot", "pid", "start")))
