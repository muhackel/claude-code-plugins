# build.md — tools

Laufumgebung für das Cross-CLI-Skript `scripts/ask.sh`. Reine Nix-Flake für die Hilfswerkzeuge; die
Ziel-CLIs selbst kommen **bewusst nicht** aus nixpkgs.

## Voraussetzungen

- **Nix mit Flakes** (`experimental-features = nix-command flakes`).
- **`claude` und `codex` auf dem Host installiert und eingeloggt** (im PATH). Das Skript ruft die jeweils
  installierte Version auf, weil Modellkatalog und Aliase von dieser Version abhängen (Codex-Klasse
  `strong` kommt aus deren Katalog). Ein Pinning über nixpkgs würde genau das aushebeln.
- Netzzugang für die API der Ziel-CLI.

## Entwicklungsumgebung

```bash
nix develop          # Shell mit jq, coreutils, shellcheck
# darin direkt:
shellcheck scripts/ask.sh tests/ask-test.sh
scripts/ask.sh --dry-run </dev/null
```

Nur das Werkzeug ohne Entwicklertools: `nix shell ./plugins/tools` (vom Repo-Root) bzw. `nix shell .` (aus
`plugins/tools/`) legt `ask` in den PATH. jq und coreutils bringt der Wrapper mit, `claude`/`codex` kommen
weiter vom Host-PATH.

```bash
nix shell ./plugins/tools -c ask --target codex --dry-run </dev/null
```

## Bauen & Starten

Das „Erzeugnis" ist das Paket `ask` (`packages.<system>.default`), ein Wrapper um `scripts/ask.sh`. Die App
`ask` (`apps.<system>.default`) startet dessen `bin/ask`:

```bash
nix build .#ask                                  # ./result/bin/ask
nix shell ./plugins/tools                        # vom Repo-Root: ask im PATH
nix run .#ask -- --dry-run </dev/null            # Kommando + Handover zeigen, nichts aufrufen
nix run .#ask </dev/null                         # Standard-Review des aktuellen Verzeichnisses (read-only)
nix run .#ask <<'EOF'                            # eigene Frage (read-only)
# Handover
## Frage / Auftrag
Welche drei Dateien sind für einen Einstieg in dieses Repo am wichtigsten?
EOF
nix run .#ask -- --mode execute <<'EOF'          # Auftrag mit Schreibrechten im Workspace
# Handover
…
EOF
nix run .#ask -- --target codex --dry-run </dev/null  # Host-Erkennung überschreiben
nix run .#ask -- --handover /pfad/handover.md    # Handover aus Datei
nix run .#ask -- -C /anderes/projekt </dev/null  # anderes Arbeitsverzeichnis
```

stdout ist die Antwort der anderen CLI, stderr der Fortschritt. Der Exit-Code der CLI wird durchgereicht.

## Testen

```bash
git add -A && nix flake check     # Syntax, shellcheck, Stub-Tests (Flake sieht nur getrackte Dateien)
nix flake check path:. -L         # dasselbe inkl. ungetrackter Dateien, mit Build-Log
nix run .#ask -- --dry-run </dev/null                       # in Claude-Bash: Ziel codex
nix run .#ask -- --mode execute --dry-run </dev/null        # muss mit Fehler enden (Handover Pflicht)
nix run .#ask -- --target claude --dry-run </dev/null       # Env-Guard-Warnung bei nested claude
echo "Nenne die drei wichtigsten Dateien dieses Repos" | nix run .#ask   # echter Lauf
```

Die Stub-Tests (`tests/ask-test.sh`, Check `ask-stubs`) laufen offline mit Stub-`codex`/`claude`, die argv
zeilenweise und ihr stdin vollständig mitschreiben. Sie prüfen: zeitversetzte stdin-Blöcke kommen byte-genau
beim Ziel an (beide CLIs, beide Modi), die Codex-Rückfallkette mit tatsächlichem argv, Warnung und Exit-Code,
den exakten Katalogaufruf `debug models --bundled` sowie die Rechte-Argumente von `claude -p`. Der Check
`package` baut den Wrapper, den `nix shell` und `nix run` nutzen.

## Projektspezifisches

- **Host-Erkennung:** `CLAUDECODE` gesetzt → Ziel `codex`, sonst Ziel `claude`. `--target` überschreibt.
- **Modellwahl nach Aufgabenklasse** (`--tier`; ohne Angabe `advanced` beim Standard-Review, sonst
  `standard`):

  | Klasse | Claude (`--model`, `--effort`) | Codex (`-m`, `model_reasoning_effort`) |
  |---|---|---|
  | `light` | `haiku`, `medium` | `gpt-5.6-luna`, `medium` |
  | `standard` | `sonnet`, `high` | `gpt-5.6-terra`, `high` |
  | `advanced` | `opus`, `high` | `gpt-5.6-sol`, `high` |
  | `strong` | `fable`, `high` | sichtbares Modell mit niedrigster `priority`, `high` |

  Claude bekommt Alias und Effort immer direkt. Codex prüft gegen `codex debug models --bundled` (nur
  `visibility == "list"`), ob das Klassenmodell existiert und den Effort kann. Rückfall: Klassenmodell →
  `gpt-5.6-sol` mit dem Effort der Klasse → Aufruf **ohne `-m` und ohne `model_reasoning_effort`**; dann
  entscheidet die Codex-CLI Modell und Effort selbst (nach Messung das Flaggschiff). Den letzten Schritt
  lösen auch ein fehlschlagender Katalogaufruf und ein unlesbarer Katalog (kein JSON, kein `.models`) aus.
  Jeder Rückfall steht als Warnung auf stderr.
- **stdin:** Ohne `--handover` liest das Skript stdin bis EOF, sobald stdin kein TTY ist, auch wenn die
  Daten verzögert kommen. Eine offene Pipe ohne EOF blockiert deshalb; Aufrufe ohne Handover hängen
  `</dev/null` an. Nur ein leeres Ergebnis (oder stdin als TTY) startet das Standard-Review.
- **Codex-Sandbox:** Ziel `claude` aus einer Codex-Sitzung braucht Netz, also `require_escalated`. Das Skript
  warnt bei `CODEX_SANDBOX_NETWORK_DISABLED=1`.
- **Nested Claude:** Ziel `claude` aus einer Claude-Code-Sitzung (nur per `--target`) läuft mit
  `env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_CHILD_SESSION`.
- **Approvals:** Codex `-c approval_policy="never"` explizit, weil ein konfigurierter `approvals_reviewer`
  den Headless-Default sonst überschreibt. Claude `--permission-prompts none`, damit abgelehnte Tools nicht
  erneut versucht werden.
- **Rechte von `claude -p`** (Mustersemantik aus [Configure permissions](https://code.claude.com/docs/en/permissions),
  abgerufen 2026-09-14):
  - `ask`: `dontAsk`, Tools Read/Glob/Grep/Bash, **keine** allow-Regeln. Ein `*` in einer Bash-Regel steht
    für beliebigen Text; `Bash(git log *)` hätte laut Doku auch `git log --output=<Datei>` freigegeben, und
    `Bash(git branch *)` erlaubt `git branch -D`. Ohne allow-Regel läuft Bash nur mit dem eingebauten
    Read-only-Set („read-only forms of git"), alles andere lehnt `dontAsk` ab. Zusätzliche deny-Regeln
    (`Edit`, `git branch -d/-D/-m/-M/-c/-C/-f/-u …`, `git * --out*`) greifen auch gegen das eingebaute Set:
    laut Doku lässt es sich nur über ask- oder deny-Regeln einschränken, und deny gilt vor allow.
    Grenze: Welche git-Optionen das eingebaute Read-only-Set als lesend einstuft, dokumentiert Claude Code
    nicht im Einzelnen; die deny-Regeln matchen nur den Befehlstext.
  - `execute`: `acceptEdits`, Bash frei, deny `Bash(git push *)`, `Bash(git * push)`, `Bash(git * push *)`,
    WebFetch, WebSearch. Das fängt `git -C . push` und `git -c k=v push …`, aber laut Doku keine Aufrufe
    wie `git 'push'`, `/usr/bin/git push` oder `sh -c 'git push'`. Die Push-Sperre ist damit **nur eine
    Textsperre plus Prompt-Anweisung, keine technische Sperre**. Nebenwirkung: Befehle, die das Wort `push`
    als eigenes Argument enthalten (`git log --grep push …`), werden ebenfalls abgelehnt.
  - Der Prompt steht direkt hinter `-p`, weil `--tools`, `--allowedTools` und `--disallowedTools` laut
    `claude --help` variadisch sind (`<tools...>`) und ein nachgestelltes Argument als Tool-Eintrag
    vereinnahmen können (nicht am echten CLI nachgemessen).
