# build.md — ask

Laufumgebung für das Cross-CLI-Skript `scripts/ask.sh`. Reine Nix-Flake für die Hilfswerkzeuge; die
Ziel-CLIs selbst kommen **bewusst nicht** aus nixpkgs.

## Voraussetzungen

- **Nix mit Flakes** (`experimental-features = nix-command flakes`).
- **`claude` und `codex` auf dem Host installiert und eingeloggt** (im PATH). Das Skript ruft die jeweils
  installierte Version auf, damit das Flaggschiffmodell dieser Version genutzt wird. Ein Pinning über
  nixpkgs würde genau das aushebeln.
- Netzzugang für die API der Ziel-CLI.

## Entwicklungsumgebung

```bash
nix develop          # Shell mit jq, coreutils, shellcheck
# darin direkt:
shellcheck scripts/ask.sh
scripts/ask.sh --dry-run
```

## Bauen & Starten

Das „Erzeugnis" ist die App `ask`:

```bash
nix run .#ask -- --dry-run                       # Kommando + Handover zeigen, nichts aufrufen
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
nix run .#ask -- --target codex --dry-run        # Host-Erkennung überschreiben
nix run .#ask -- --handover /pfad/handover.md    # Handover aus Datei
nix run .#ask -- -C /anderes/projekt </dev/null  # anderes Arbeitsverzeichnis
```

stdout ist die Antwort der anderen CLI, stderr der Fortschritt. Der Exit-Code der CLI wird durchgereicht.

## Testen

```bash
git add -A && nix flake check     # Syntax + shellcheck-Check (Flake sieht nur getrackte Dateien)
nix run .#ask -- --dry-run                                  # in Claude-Bash: Ziel codex
nix run .#ask -- --mode execute --dry-run </dev/null        # muss mit Fehler enden (Handover Pflicht)
nix run .#ask -- --target claude --dry-run </dev/null       # Env-Guard-Warnung bei nested claude
echo "Nenne die drei wichtigsten Dateien dieses Repos" | nix run .#ask   # echter Lauf
```

## Projektspezifisches

- **Host-Erkennung:** `CLAUDECODE` gesetzt → Ziel `codex`, sonst Ziel `claude`. `--target` überschreibt.
- **Modellwahl:** Codex über `codex debug models` (sichtbares Modell mit niedrigster `priority`), Claude über
  den Alias `fable`. Effort `high` (Codex: `model_reasoning_effort`, Claude: `--effort`); kennt das
  Codex-Modell die Stufe nicht, bleibt der Modell-Default.
- **stdin:** Ohne `--handover` liest das Skript stdin nur, wenn dort Daten anliegen (`read -t 0`). Eine
  offene, leere Pipe blockiert damit nicht; wer stdin sicher leer haben will, hängt `</dev/null` an.
- **Codex-Sandbox:** Ziel `claude` aus einer Codex-Sitzung braucht Netz, also `require_escalated`. Das Skript
  warnt bei `CODEX_SANDBOX_NETWORK_DISABLED=1`.
- **Nested Claude:** Ziel `claude` aus einer Claude-Code-Sitzung (nur per `--target`) läuft mit
  `env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_CHILD_SESSION`.
- **Approvals:** Codex `-c approval_policy="never"` explizit, weil ein konfigurierter `approvals_reviewer`
  den Headless-Default sonst überschreibt. Claude `--permission-prompts none`, damit abgelehnte Tools nicht
  erneut versucht werden.
