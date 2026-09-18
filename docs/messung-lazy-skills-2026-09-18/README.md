# Hilfsskripte der Messreihe "lazy-skills"

Diese Skripte haben die Messung in `../messung-lazy-skills-2026-09-18.md` erzeugt
(Rohdaten in `../messung-lazy-skills-2026-09-18.csv`). Sie starten Claude Code
bzw. Codex jeweils vor und nach der Umstellung auf verzögertes Laden von
Fachwissen (`before`/`after`), unter einem Watchdog, der eingreift, falls ein
Messlauf versehentlich außerhalb seiner Sandbox etwas verändert.

## Dateien

- `run-claude.sh` — startet einen Claude-Code-Messlauf unter Watchdog.
- `run-codex.sh` — startet einen Codex-Messlauf unter Watchdog.
- `watchdog.py` — prüft Tool-Aufrufe aus dem Stream (Claude `stream-json`, Codex
  `exec --json`) gegen eine Verbotsliste (Schreibzugriffe außerhalb `/tmp`,
  `nixos-rebuild switch`, `ssh` auf fremde Hosts, `git` außerhalb `/tmp` etc.)
  und bricht den Lauf bei einem Treffer ab.
- `test-watchdog.sh` — Testfälle für `watchdog.py check`, ohne echten Modelllauf.
- `strip-codex-config.py` — entfernt Marketplace-/Plugin-Einträge aus einer
  Codex-`config.toml`, um einen sauberen `before`-Zustand ohne die zu messenden
  Plugins zu erzeugen.
- `claude-settings.json` — Claude-Settings mit deaktivierten Plugins, ohne Watchdog-Hook.
- `claude-settings-guard.json` — dieselben Settings, zusätzlich mit dem
  PreToolUse-Hook auf `watchdog.py hook`.
- `py` — Python-Launcher (bevorzugt einen gepinnten Nix-Store-Pfad, sonst
  `nix shell nixpkgs#python3`).

## Voraussetzungen

- `claude` (Claude Code CLI) und `codex` (Codex CLI) im `PATH`.
- Nix (für `py`, falls der gepinnte Store-Pfad auf der jeweiligen Maschine
  nicht existiert), `shellcheck` und `python3` nur zum Prüfen der Skripte.
- `jq` für die Plugin-Auswertung in `run-claude.sh`.

## Umgebungsvariablen

- `LAZY_MESS` — Basisverzeichnis der Messumgebung (Zustände `before`/`after`,
  `codex-before`/`codex-after`, Logs, Watchdog-Events). Default `/tmp/lazy-mess`.
- `LAZY_CWD` — Arbeitsverzeichnis für den gemessenen Lauf. Default `$LAZY_MESS/work`.
  Muss unter `/tmp` liegen.
- `LAZY_WATCHDOG_EVENTS`, `LAZY_WATCHDOG_FLAGS`, `LAZY_WATCHDOG_TRACE` — einzelne
  Watchdog-Pfade, falls sie nicht aus `LAZY_MESS` abgeleitet werden sollen.

Die Skripte finden `py`, `watchdog.py` und die `claude-settings*.json` immer
relativ zum eigenen Verzeichnis, unabhängig von `LAZY_MESS` — `LAZY_MESS`
bestimmt nur die Messumgebung selbst (Plugin-Zustände, Logs, Events), nicht
den Ort der Skripte.

`claude-settings-guard.json` enthält statt eines festen Pfads den Platzhalter
`__WATCHDOG_HOOK_CMD__` im Hook-Kommando. `run-claude.sh` ersetzt ihn beim
Aufruf durch `<Skriptverzeichnis>/py <Skriptverzeichnis>/watchdog.py hook`,
bevor die Settings per `--settings` an Claude übergeben werden — so funktioniert
der Hook unabhängig davon, wohin dieser Ordner kopiert wird.

## Watchdog ist eine Schutzschicht

Der Watchdog schützt vor versehentlichen Seiteneffekten außerhalb der
Sandbox (`/tmp`), er ist nicht Teil dessen, was gemessen wird. Er beeinflusst
weder Tool-Auswahl noch Antwortverhalten der gemessenen Läufe, solange keine
verbotene Aktion auftritt — die Messwerte selbst (Tool-Calls, Tokens, Dauer)
bleiben unberührt.
