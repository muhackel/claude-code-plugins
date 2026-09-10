import json
import os
from pathlib import Path
import shutil
import subprocess

from common import Error, read_json


def resolve(target="auto", model=None, effort="high"):
    if target == "auto":
        target = "codex" if os.environ.get("CLAUDECODE") else "claude"
    if target not in ("claude", "codex"):
        raise Error("Ziel muss claude oder codex sein.")
    executable = shutil.which(target)
    if not executable:
        raise Error(f"Ziel-CLI fehlt im Host-PATH: {target}")
    executable = str(Path(executable).resolve())
    version = subprocess.run([executable, "--version"], capture_output=True, text=True,
                             timeout=15, check=True).stdout.strip()
    help_args = [executable, "exec", "--help"] if target == "codex" else [executable, "--help"]
    help_text = subprocess.run(help_args, capture_output=True, text=True,
                               timeout=15, check=True).stdout
    required = (["--ignore-user-config", "--ignore-rules", "--output-schema", "--output-last-message"]
                if target == "codex" else
                ["--safe-mode", "--json-schema", "--permission-prompts", "--permission-mode"])
    if any(flag not in help_text for flag in required):
        raise Error(f"CLI-Version unterstützt den geprüften Vertrag nicht: {version}")
    if model is None and target == "codex":
        process = subprocess.run([executable, "debug", "models", "--bundled"],
                                 capture_output=True, text=True, timeout=15)
        if process.returncode:
            raise Error("Modellkatalog nicht verfügbar; Modell ausdrücklich konfigurieren.")
        catalog = json.loads(process.stdout)
        visible = sorted((m for m in catalog["models"] if m.get("visibility") == "list"),
                         key=lambda m: m["priority"])
        if not visible:
            raise Error("Kein sichtbares Modell im installierten Katalog.")
        model = visible[0]["slug"]
        supported = {e["effort"] for e in visible[0]["supported_reasoning_levels"]}
        if effort not in supported:
            raise Error(f"Gewähltes Modell unterstützt Effort {effort} nicht.")
    if model is None:
        model = "fable"
    return {"target": target, "executable": executable, "version": version,
            "model": model, "effort": effort}


def label_prompt(label, prompt):
    """Kennzeichnet den ersten Turn, damit Philharmonie-Aufrufe im Resume-Picker erkennbar sind."""
    return f"[{label}]\n\n{prompt}"


def command(adapter, workspace, schema, output, profile, delegation=None, label=None):
    if profile not in ("inspect", "verify", "edit"):
        raise Error("Unbekanntes Rechteprofil.")
    if adapter["target"] == "codex":
        argv = [adapter["executable"], "exec", "--color", "never",
                "--ignore-user-config", "--ignore-rules", "-C", str(workspace),
                "-c", 'approval_policy="never"', "-m", adapter["model"],
                "-c", f'model_reasoning_effort={json.dumps(adapter["effort"])}',
                "-s", "workspace-write" if profile == "edit" else "read-only",
                "--json", "--output-schema", str(schema),
                "--output-last-message", str(output), "-"]
        if delegation:
            extra = ["--enable", "multi_agent", "--disable", "multi_agent_v2",
                     "-c", "agents.enabled=true", "-c", "agents.max_concurrent_threads_per_session=3",
                     "-c", "agents.max_depth=1"]
            for name, role in delegation["roles"].items():
                extra += ["-c", f'agents.{name}.description={json.dumps(role["description"])}',
                          "-c", f'agents.{name}.config_file={json.dumps(role["config_file"])}']
            argv[-1:-1] = extra
    else:
        tools = "Read,Glob,Grep,Bash"
        allowed = ("Read,Glob,Grep,Bash(git status:*),Bash(git diff:*),Bash(git log:*),"
                   "Bash(git show:*),Bash(git ls-files:*)") if profile == "inspect" else tools
        if profile == "edit":
            tools += ",Edit,Write"
            allowed = tools
        if delegation:
            tools += ",Agent"
            allowed += "," + ",".join(f"Agent({name})" for name in delegation["roles"])
        argv = [adapter["executable"], "-p", "--safe-mode",
                "--permission-prompts", "none", "--permission-mode", "dontAsk",
                "--model", adapter["model"], "--effort", adapter["effort"],
                *(["--name", label] if label else []),
                "--output-format", "json", "--json-schema", Path(schema).read_text(),
                "--tools", tools, "--allowedTools", allowed,
                "Bearbeite das Handover aus stdin. Gib das angeforderte strukturierte Ergebnis zurück."]
        if delegation:
            argv.remove("--safe-mode")
            argv[argv.index("--output-format") + 1] = "stream-json"
            argv[1:1] = ["--verbose", "--forward-subagent-text", "--setting-sources", "", "--disable-slash-commands",
                         "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                         "--settings", '{"disableAllHooks":true}',
                         "--agents", json.dumps(delegation["roles"], ensure_ascii=False)]
    return argv


def decode(adapter, stdout, output):
    if adapter["target"] == "codex":
        return read_json(output)
    try:
        payload = json.loads(stdout)
    except ValueError as exc:
        try:
            records = [json.loads(line) for line in stdout.splitlines() if line.strip()]
            payload = next(record for record in reversed(records)
                           if isinstance(record, dict) and record.get("type") == "result")
        except (ValueError, StopIteration) as stream_error:
            raise Error("Claude lieferte kein gültiges JSON-Ergebnis.") from stream_error
    if not isinstance(payload, dict) or payload.get("is_error") or not isinstance(payload.get("structured_output"), dict):
        raise Error("Claude meldete einen Fehler oder lieferte kein structured_output.")
    return payload["structured_output"]


def environment():
    allowed = ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "NIX_SSL_CERT_FILE",
               "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY")
    result = {key: os.environ[key] for key in allowed if key in os.environ}
    result.update(CLAUDE_CODE_DISABLE_CLAUDE_MDS="1", CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="1",
                  CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS="3", CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS="1")
    return result


def session_paths():
    """Sitzungsverzeichnisse der Host-CLIs, damit Aufrufe in der Usage-Auswertung auftauchen."""
    return [(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions",
             Path(".codex/sessions")),
            (Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects",
             Path(".claude/projects"))]


def sandbox(workspace, scratch, argv, profile, auth=True, nix_daemon=False, runtime_home=False):
    executable = shutil.which("bwrap")
    if not executable:
        raise Error("Bubblewrap fehlt; kein ungeschützter Ersatzaufruf.")
    workspace, scratch = Path(workspace).resolve(), Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    home = Path("/tmp/philharmonie-home")
    args = [executable, "--die-with-parent", "--new-session", "--unshare-pid",
            "--unshare-ipc", "--unshare-uts", "--ro-bind", "/", "/",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--tmpfs", "/run", "--tmpfs", "/home", "--tmpfs", "/root",
            "--dir", str(home), "--setenv", "HOME", str(home),
            "--setenv", "CODEX_HOME", str(home / ".codex"),
            "--setenv", "CLAUDE_CONFIG_DIR", str(home / ".claude"),
            "--setenv", "XDG_CACHE_HOME", str(home / ".cache"),
            "--setenv", "NIX_REMOTE", "daemon", "--unsetenv", "SSH_AUTH_SOCK",
            "--unsetenv", "DBUS_SESSION_BUS_ADDRESS"]
    if Path("/run/current-system").exists():
        args += ["--ro-bind", "/run/current-system", "/run/current-system"]
    resolver = Path("/etc/resolv.conf").resolve()
    if resolver.is_file():
        args += ["--ro-bind", str(resolver), str(resolver)]
    socket_dir = Path("/nix/var/nix/daemon-socket")
    if socket_dir.exists() and not nix_daemon:
        args += ["--tmpfs", str(socket_dir)]
    if runtime_home:
        runtime = scratch / "runtime"
        runtime.mkdir(mode=0o700, exist_ok=True)
        args += ["--bind", str(runtime), str(home)]
    if auth:
        auth_paths = [(Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json",
                       home / ".codex/auth.json"),
                      (Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) /
                       ".credentials.json", home / ".claude/.credentials.json")]
        for source, destination in auth_paths:
            if source.is_file():
                args += ["--dir", str(destination.parent), "--ro-bind", str(source), str(destination)]
        for source, destination in session_paths():
            source.mkdir(parents=True, exist_ok=True)
            args += ["--dir", str(home / destination.parent), "--bind", str(source), str(home / destination)]
    args += ["--ro-bind", str(scratch.parent), str(scratch.parent),
             "--bind" if profile == "edit" else "--ro-bind", str(workspace), str(workspace),
             "--bind", str(scratch), str(scratch)]
    if (workspace / ".git").exists():
        gitdir = (workspace / ".git").resolve()
        common = gitdir / "commondir"
        if common.is_file():
            gitdir = (gitdir / common.read_text().strip()).resolve()
        args += ["--ro-bind", str(gitdir), str(gitdir)]
    args += ["--chdir", str(workspace), "--", *argv]
    return args


def check_sandbox():
    import tempfile
    with tempfile.TemporaryDirectory(prefix="philharmonie-probe-") as directory:
        base = Path(directory)
        workspace = base / "workspace"
        workspace.mkdir()
        sentinel = workspace / "readonly"
        sentinel.write_text("unverändert")
        argv = sandbox(workspace, base / "scratch", ["sh", "-c",
                       'if echo falsch > readonly 2>/dev/null; then exit 2; fi; '
                       'echo test > "$HOME/probe"'], "inspect", auth=False)
        result = subprocess.run(argv, capture_output=True, env=environment(), timeout=15)
        if result.returncode or sentinel.read_text() != "unverändert":
            raise Error("Sandbox-Probe fehlgeschlagen: " + result.stderr.decode(errors="replace"))
