#!/usr/bin/env python3
# Watchdog für Mess-Läufe: prüft Tool-Calls aus Claude stream-json bzw. Codex exec --json
# und beendet den Lauf (Prozessgruppe) bei verbotenen Aktionen.
#
# Modi:
#   watchdog.py run --log <datei.jsonl> [--cwd <dir>] -- <cmd ...>
#   watchdog.py hook            (Claude PreToolUse-Hook: JSON auf stdin, exit 2 = blockieren)
#   watchdog.py check <tool> <json-input>   (Einzelprüfung, Test)
#
# Befunde landen als JSON-Zeilen in $LAZY_WATCHDOG_EVENTS (Default $LAZY_MESS/watchdog-events.jsonl,
# LAZY_MESS Default /tmp/lazy-mess).

import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time

LAZY_MESS = os.environ.get("LAZY_MESS", "/tmp/lazy-mess")
EVENTS = os.environ.get("LAZY_WATCHDOG_EVENTS", os.path.join(LAZY_MESS, "watchdog-events.jsonl"))
KILLFLAG_DIR = os.environ.get("LAZY_WATCHDOG_FLAGS", os.path.join(LAZY_MESS, "watchdog-flags"))

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", os.uname().nodename}

WRITE_VERBS = {
    "cp", "mv", "rm", "rmdir", "mkdir", "touch", "ln", "install", "chmod", "chown",
    "chgrp", "truncate", "shred", "unlink", "rsync", "tee",
}

FILE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path",
              "NotebookEdit": "notebook_path"}


def under_tmp(path, cwd):
    if not path:
        return True
    p = os.path.expanduser(path)
    if p.startswith("$HOME") or p.startswith("${HOME}"):
        return False
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    p = os.path.normpath(p)
    return p == "/tmp" or p.startswith("/tmp/") or p in ("/dev/null", "/dev/stdout", "/dev/stderr") \
        or p.startswith("/dev/fd/") or p.startswith("/proc/self/fd/")


def split_segments(cmd):
    return [s for s in re.split(r"(?:&&|\|\||;|\||\n|\$\(|`)", cmd) if s.strip()]


def check_shell(cmd, cwd):
    hits = []
    c = " ".join(shlex.quote(x) for x in cmd) if isinstance(cmd, list) else str(cmd)
    try:
        whole = shlex.split(c, posix=True)
    except ValueError:
        whole = []
    if len(whole) >= 3 and os.path.basename(whole[0]) in ("bash", "sh", "zsh", "dash") \
            and re.match(r"^-\w*c$", whole[1]):
        return check_shell(whole[2], cwd)
    if re.search(r"\bnixos-rebuild\b[^\n;&|]*(?<![\w-])(switch|boot|test|build-vm|build)(?![\w-])", c):
        hits.append("nixos-rebuild switch/boot/test/build")
    if re.search(r"\bswitch-to-configuration\b", c):
        hits.append("switch-to-configuration")
    if re.search(r"\b(nh)\s+(os|home|darwin)\s+(switch|boot|test|build)\b", c):
        hits.append("nh switch/boot/build")
    for seg in split_segments(c):
        if re.search(r"\bnix\s+(?:--[\w-]+\s+\S+\s+)*build\b", seg) and "--dry-run" not in seg:
            hits.append("nix build ohne --dry-run")
        if re.search(r"(^|[\s/])nix-build\b", seg) and "--dry-run" not in seg:
            hits.append("nix-build ohne --dry-run")
        if re.search(r"\bnix\s+flake\s+check\b", seg) and "--no-build" not in seg:
            hits.append("nix flake check ohne --no-build (baut)")
        if re.search(r"\bnix\s+copy\b", seg) or re.search(r"\bnix-copy-closure\b", seg):
            hits.append("nix copy")
        if re.search(r"\b(colmena\s+apply|deploy-rs|nixos-anywhere|home-manager\s+switch|nix\s+profile\s+(install|add|remove|upgrade)|nix-env\s+-[iue])\b", seg):
            hits.append("Deploy/Profil-Änderung")
        if re.search(r"--(target|build)-host\b", seg):
            m = re.search(r"--(?:target|build)-host[= ]+(\S+)", seg)
            host = (m.group(1).split("@")[-1] if m else "?")
            if host not in LOCAL_HOSTS:
                hits.append(f"Remote-Host {host}")
        try:
            toks = shlex.split(seg, posix=True)
        except ValueError:
            toks = seg.split()
        while toks and (toks[0] in ("sudo", "doas", "env", "exec", "command", "time", "nice", "then", "do", "else", "{", "(")
                        or re.match(r"^\w+=", toks[0])):
            if toks[0] in ("sudo", "doas"):
                hits.append("sudo/doas")
            toks = toks[1:]
        if not toks:
            continue
        verb = os.path.basename(toks[0])
        if verb in ("bash", "sh", "zsh", "dash") and len(toks) > 2 and re.match(r"^-\w*c$", toks[1]):
            hits += check_shell(toks[2], cwd)
            continue
        if verb in ("ssh", "scp", "sftp", "mosh", "ssh-copy-id"):
            hosts = [t.split("@")[-1].split(":")[0] for t in toks[1:] if not t.startswith("-")]
            if not hosts or any(h not in LOCAL_HOSTS for h in hosts[:1]):
                hits.append(f"{verb} auf fremden Host")
        if verb == "rsync" and any(re.match(r"^[^/]*[^/\\]:", t) for t in toks[1:] if not t.startswith("-")):
            hits.append("rsync remote")
        if verb == "cd" and len(toks) > 1:
            cwd = toks[1] if os.path.isabs(os.path.expanduser(toks[1])) else os.path.join(cwd or "/", toks[1])
            cwd = os.path.expanduser(cwd)
        if verb in WRITE_VERBS:
            args = [t for t in toks[1:] if not t.startswith("-")]
            targets = args if verb in ("rm", "rmdir", "mkdir", "touch", "chmod", "chown", "chgrp",
                                       "truncate", "shred", "unlink", "tee") else args[-1:]
            if verb in ("chmod", "chown", "chgrp") and args:
                targets = args[1:]
            for t in targets:
                if not under_tmp(t, cwd):
                    hits.append(f"{verb} schreibt außerhalb /tmp: {t}")
        if verb == "sed" and any(t.startswith("-i") or t == "--in-place" for t in toks[1:]):
            for t in toks[1:]:
                if not t.startswith("-") and ("/" in t or "." in t) and os.path.sep in t and not under_tmp(t, cwd):
                    hits.append(f"sed -i außerhalb /tmp: {t}")
        if verb == "dd":
            for t in toks[1:]:
                if t.startswith("of=") and not under_tmp(t[3:], cwd):
                    hits.append(f"dd of= außerhalb /tmp: {t}")
        if verb == "git":
            sub = [t for t in toks[1:] if not t.startswith("-")]
            gitdir = None
            if "-C" in toks:
                i = toks.index("-C")
                gitdir = toks[i + 1] if i + 1 < len(toks) else None
                if gitdir in sub:
                    sub.remove(gitdir)
            mutating = {"commit", "push", "checkout", "switch", "reset", "stash", "merge", "rebase",
                        "cherry-pick", "revert", "tag", "branch", "add", "rm", "mv", "clean", "restore",
                        "apply", "am", "pull", "fetch", "worktree", "submodule", "init", "clone", "config"}
            if sub and sub[0] in mutating:
                target = gitdir or cwd
                if sub[0] == "clone":
                    target = sub[-1] if len(sub) > 2 else cwd
                if not under_tmp(target, cwd):
                    hits.append(f"git {sub[0]} außerhalb /tmp")
        for m in re.finditer(r"(?<![<\d&])(?:\d?>>?|&>>?)\s*([^\s;&|<>]+)", seg):
            tgt = m.group(1).strip("'\"")
            if tgt.startswith("&"):
                continue
            if not under_tmp(tgt, cwd):
                hits.append(f"Umleitung außerhalb /tmp: {tgt}")
        if verb in ("systemctl",) and len(toks) > 1 and any(t in toks for t in
                                                             ("start", "stop", "restart", "enable", "disable", "reload", "mask", "daemon-reload")):
            hits.append("systemctl mutierend")
    return hits


def check_tool(name, inp, cwd):
    hits = []
    if not isinstance(inp, dict):
        inp = {"_raw": inp}
    if name in FILE_TOOLS:
        p = inp.get(FILE_TOOLS[name])
        if not under_tmp(p, cwd):
            hits.append(f"{name} außerhalb /tmp: {p}")
    if name in ("Bash", "BashOutput", "command_execution", "shell", "exec_command", "local_shell"):
        cmd = inp.get("command") or inp.get("cmd") or inp.get("_raw") or ""
        hits += check_shell(cmd, inp.get("cwd") or inp.get("workdir") or cwd)
    if name == "file_change":
        for ch in inp.get("changes", []) or []:
            p = ch.get("path") if isinstance(ch, dict) else None
            if not under_tmp(p, cwd):
                hits.append(f"file_change außerhalb /tmp: {p}")
    if name.startswith("mcp__") or name == "mcp_tool_call":
        blob = json.dumps(inp, ensure_ascii=False)
        if re.search(r"\b(ssh|nixos-rebuild|nix copy)\b", blob):
            hits.append(f"MCP-Aufruf mit verdächtigem Inhalt: {name}")
    return hits


def log_event(ev):
    os.makedirs(os.path.dirname(EVENTS), exist_ok=True)
    ev["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def extract_calls(obj):
    calls = []
    t = obj.get("type")
    if t == "assistant":
        for c in (obj.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                calls.append((c.get("name", "?"), c.get("input", {})))
    if t in ("item.started", "item.updated", "item.completed"):
        it = obj.get("item") or {}
        it_t = it.get("type") or it.get("item_type")
        if it_t == "command_execution":
            calls.append(("command_execution", {"command": it.get("command", "")}))
        elif it_t == "file_change":
            calls.append(("file_change", {"changes": it.get("changes", [])}))
        elif it_t == "mcp_tool_call":
            calls.append(("mcp_tool_call", it))
    return calls


def mode_run(argv):
    log = None
    cwd = os.getcwd()
    if "--" not in argv:
        print("usage: watchdog.py run --log FILE [--cwd DIR] -- cmd ...", file=sys.stderr)
        return 64
    i = argv.index("--")
    opts, cmd = argv[:i], argv[i + 1:]
    for j, o in enumerate(opts):
        if o == "--log":
            log = opts[j + 1]
        if o == "--cwd":
            cwd = opts[j + 1]
    run_id = os.path.basename(log or "run")
    os.makedirs(KILLFLAG_DIR, exist_ok=True)
    flag = os.path.join(KILLFLAG_DIR, run_id + ".kill")
    if os.path.exists(flag):
        os.remove(flag)
    env = dict(os.environ, LAZY_WATCHDOG_FLAG=flag, LAZY_WATCHDOG_CWD=cwd)
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL,
                            start_new_session=True, env=env, text=True, bufsize=1)
    out = open(log, "w", encoding="utf-8") if log else sys.stdout
    killed = None

    def kill(reason):
        nonlocal killed
        killed = reason
        log_event({"run": run_id, "action": "KILL", "reason": reason, "cmd": cmd[:3]})
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            time.sleep(2)
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    for line in proc.stdout:
        out.write(line)
        out.flush()
        if os.path.exists(flag) and not killed:
            kill(open(flag, encoding="utf-8").read().strip() or "Hook-Block")
            break
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        for name, inp in extract_calls(obj):
            hits = check_tool(name, inp, cwd)
            if hits and not killed:
                kill(f"{name}: " + "; ".join(hits) + " | input=" + json.dumps(inp, ensure_ascii=False)[:400])
        if killed:
            break
    rc = proc.wait()
    if not killed and os.path.exists(flag):
        killed = open(flag, encoding="utf-8").read().strip() or "Hook-Block"
        log_event({"run": run_id, "action": "KILL-POST", "reason": killed})
    if log:
        out.close()
    if killed:
        print(f"WATCHDOG: Lauf abgebrochen: {killed}", file=sys.stderr)
        return 99
    return rc


def mode_hook():
    data = json.load(sys.stdin)
    name = data.get("tool_name", "?")
    inp = data.get("tool_input", {})
    cwd = data.get("cwd") or os.environ.get("LAZY_WATCHDOG_CWD") or os.getcwd()
    hits = check_tool(name, inp, cwd)
    trace = os.environ.get("LAZY_WATCHDOG_TRACE", os.path.join(LAZY_MESS, "logs", "hook-trace.jsonl"))
    os.makedirs(os.path.dirname(trace), exist_ok=True)
    with open(trace, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            "run": os.path.basename(os.environ.get("LAZY_WATCHDOG_FLAG", "?")),
                            "tool": name, "block": bool(hits)}, ensure_ascii=False) + "\n")
    if hits:
        reason = f"{name}: " + "; ".join(hits)
        log_event({"run": os.path.basename(os.environ.get("LAZY_WATCHDOG_FLAG", "?")), "action": "HOOK-BLOCK",
                   "reason": reason, "input": inp})
        flag = os.environ.get("LAZY_WATCHDOG_FLAG")
        if flag:
            with open(flag, "w", encoding="utf-8") as f:
                f.write(reason + " | input=" + json.dumps(inp, ensure_ascii=False)[:400])
        print(f"Messumgebung: verbotene Aktion blockiert ({reason}).", file=sys.stderr)
        return 2
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__ or "usage", file=sys.stderr)
        return 64
    m = sys.argv[1]
    if m == "run":
        return mode_run(sys.argv[2:])
    if m == "hook":
        return mode_hook()
    if m == "check":
        hits = check_tool(sys.argv[2], json.loads(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else os.path.join(LAZY_MESS, "work"))
        print(json.dumps(hits, ensure_ascii=False))
        return 1 if hits else 0
    return 64


if __name__ == "__main__":
    sys.exit(main())
