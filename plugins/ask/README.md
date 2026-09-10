# ask — Cross-CLI-Zweitmeinung

Fragt aus einer laufenden Sitzung heraus die **jeweils andere CLI**: aus Claude Code wird Codex gefragt,
aus Codex Claude Code. Non-interaktiv, mit dem Modell zur **Aufgabenklasse** statt pauschal dem
Flaggschiff. Sinn: eine unabhängige zweite Meinung mit leerem Kontext, die den eigenen blinden Fleck
nicht teilt.

## Commands

| Command | Rechte der anderen CLI | Ohne Argument | Mit Argument |
|---|---|---|---|
| `/ask` | read-only | Standard-Review des aktuellen Projekts | Host schreibt Handover, andere CLI antwortet |
| `/execute` | workspace-write | Rückfrage (Auftrag ist Pflicht) | Host schreibt Handover, andere CLI führt aus |

In Codex werden die Commands beim Install zu Skills: `$ask:source-command-ask` und `$ask:source-command-execute`.

```
/ask
/ask Ist die Fehlerbehandlung in scripts/ingest.sh robust genug für einen Netzabbruch?
/execute Ergänze in README.md einen Abschnitt „Troubleshooting" für die drei häufigsten Fehler aus build.md
```

## Komponenten

| Typ | Name | Zweck |
|-----|------|-------|
| Command | `/ask` | Zweitmeinung oder Review, read-only |
| Command | `/execute` | Delegierter Auftrag mit Schreibrechten im Workspace |
| Skill | `handover` | Handover-Format, Ablauf, Rechte-Matrix, Standard-Review |
| Skript | `scripts/ask.sh` | Host-Erkennung, Modellwahl, CLI-Aufruf |

## Wie es arbeitet

1. Der Host (der Agent, der `/ask` ausführt) schreibt ein Handover: Kontext, Ziel, Frage, erwartete Antwort,
   Grenzen. Die andere CLI startet mit leerem Kontext und kennt nur Arbeitsverzeichnis und Handover.
2. `scripts/ask.sh` erkennt den Host (`CLAUDECODE` gesetzt → Ziel `codex`, sonst `claude`), löst die
   Aufgabenklasse in Modell und Effort auf und startet `codex exec` bzw. `claude -p` mit den Rechten des
   Modus. Codex-Modelle werden gegen `codex debug models` geprüft; fehlt eines im Katalog, bricht der
   Aufruf ab, statt still auf ein teureres auszuweichen.
3. stdout ist die Antwort, stderr der Fortschritt. Der Host gibt die Antwort unverändert wieder und ordnet
   sie kurz ein.

## Aufgabenklassen

`--tier` bestimmt das Modell. Ohne Angabe gilt `advanced` beim Standard-Review und sonst `standard`.

| Klasse | Wofür | Claude | Codex |
|---|---|---|---|
| `light` | eindeutige Kleinarbeit: String fixen, Datei finden, Formatierung | haiku, medium | luna, medium |
| `standard` | einzelnes Modul, Test schreiben, lokale Fehleranalyse | sonnet, high | terra, high |
| `advanced` | mehrere Module, Refactoring, schwere Fehlersuche, Projekt-Review | opus, high | sol, high |
| `strong` | Architektur, widersprüchliche Anforderungen, Planung | fable, high | astra, high |

Die Staffelung entspricht der, mit der philharmonie seine Subagenten besetzt. Bei Codex steht die Spitze
nicht fest, sie kommt aus dem Katalog der installierten Version. Für harte Aufgaben lohnt `strong` eher
als Planer, dessen Plan anschließend eine kleinere Klasse umsetzt.

## Rechte-Matrix

| Modus | Codex (`codex exec`) | Claude (`claude -p`) |
|---|---|---|
| ask | `-s read-only`, `approval_policy=never` | `dontAsk`, Tools Read/Glob/Grep, Bash nur read-only git |
| execute | `-s workspace-write`, `approval_policy=never` | `acceptEdits`, Edit/Write/Bash, `git push` und Web verboten |

Codex sandboxt das Dateisystem, Claude nicht. `execute` deshalb nur auf einem Feature-Branch starten;
Commit und Push bleiben beim User.

## Sitzungen und Abrechnung

Beide Aufrufe schreiben eine Sitzungsdatei in das übliche Verzeichnis der Ziel-CLI. Damit erscheinen sie
in der Auswertung mit `ccusage` und im Resume-Picker. Als Kennung trägt der Aufruf `/<modus> <projekt>`:
Claude bekommt sie über `--name`, Codex kennt kein solches Flag und erhält sie als Präfix des Auftrags.

## Unter Codex

`claude -p` braucht Netz, die Codex-Sandbox sperrt es standardmäßig. Der Command weist den Codex-Host an,
den Aufruf mit `require_escalated` zu starten. Codex ersetzt `${CLAUDE_PLUGIN_ROOT}` nicht; der Command
leitet den Plugin-Root aus dem Pfad des migrierten Skills ab.

## Direkt aus der Shell

```bash
nix run ./plugins/ask#ask </dev/null                 # Standard-Review, Ziel nach Host-Erkennung
echo "Frage?" | nix run ./plugins/ask#ask -- --target codex
```

Details, Flags und Tests in [`build.md`](build.md).

## Installation (lokal)

```bash
/plugin marketplace add ./
/plugin install ask --scope local
```

## Lizenz

MIT
