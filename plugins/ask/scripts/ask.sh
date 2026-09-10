#!/usr/bin/env bash
set -euo pipefail

# Cross-CLI-Zweitmeinung: ruft non-interaktiv die jeweils andere CLI auf.
#   Host Claude Code (CLAUDECODE gesetzt) -> codex exec
#   Host Codex / normales Terminal        -> claude -p
# Modell: Flaggschiff der installierten CLI-Version, zur Laufzeit ermittelt.
# Handover (Markdown) kommt per stdin oder --handover FILE; ohne beides: Standard-Review.
# stdout = Antwort der anderen CLI, stderr = Fortschritt/Log.

EFFORT="high"

c_info=$'\e[34m'; c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*" >&2; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*" >&2; }
log_warn(){ printf '%s[!]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }
die(){ log_err "$@"; exit 1; }

usage() {
  cat >&2 <<'EOF'
Usage: ask.sh [--mode ask|execute] [--target claude|codex] [--handover FILE|-] [--dry-run] [-h]

  --mode ask        read-only (Default). Ohne Handover: Standard-Review des Projekts.
  --mode execute    workspace-write. Handover ist Pflicht.
  --target CLI      Override der Host-Erkennung (Default: CLAUDECODE gesetzt -> codex, sonst claude).
  --handover FILE   Handover-Markdown aus Datei ('-' = stdin). Ohne Flag: stdin, falls kein TTY.
  --dry-run         Kommando und Handover-Vorschau ausgeben, nichts aufrufen.
  -C DIR            Arbeitsverzeichnis (Default: $PWD).
EOF
}

MODE="ask"; TARGET=""; HANDOVER_SRC=""; DRY_RUN=0; WORKDIR="$PWD"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)      [[ $# -ge 2 ]] || die "--mode braucht einen Wert"; MODE="$2"; shift 2 ;;
      --target)    [[ $# -ge 2 ]] || die "--target braucht einen Wert"; TARGET="$2"; shift 2 ;;
      --handover)  [[ $# -ge 2 ]] || die "--handover braucht einen Wert"; HANDOVER_SRC="$2"; shift 2 ;;
      -C)          [[ $# -ge 2 ]] || die "-C braucht einen Wert"; WORKDIR="$2"; shift 2 ;;
      --dry-run)   DRY_RUN=1; shift ;;
      -h|--help)   usage; exit 0 ;;
      *)           usage; die "Unbekanntes Argument: $1" ;;
    esac
  done
  case "$MODE" in ask|execute) ;; *) die "--mode muss ask oder execute sein, nicht '$MODE'" ;; esac
  [[ -d "$WORKDIR" ]] || die "Arbeitsverzeichnis existiert nicht: $WORKDIR"
  WORKDIR="$(cd "$WORKDIR" && pwd)"
}

detect_host() {
  if [[ -n "$TARGET" ]]; then
    case "$TARGET" in claude|codex) ;; *) die "--target muss claude oder codex sein, nicht '$TARGET'" ;; esac
    log_info "Ziel-CLI per Override: $TARGET"
    return
  fi
  if [[ -n "${CLAUDECODE:-}" ]]; then
    TARGET="codex"; log_info "Host: Claude Code -> Ziel-CLI: codex"
  else
    TARGET="claude"; log_info "Host: Codex/Terminal -> Ziel-CLI: claude"
  fi
}

default_review_prompt() {
  cat <<'EOF'
# Handover

## Ziel

Unabhängiges Review des aktuellen Projektstands im Arbeitsverzeichnis.

## Auftrag

1. Charakterisiere das Projekt kurz (README, CLAUDE.md bzw. AGENTS.md, Verzeichnisstruktur, Git-Log der letzten Commits).
2. Nenne die wichtigsten Befunde in diesen Kategorien:
   - Bugs und Risiken (Logik, Fehlerbehandlung, Sicherheit)
   - Doku-Drift (README/CLAUDE.md gegenüber dem tatsächlichen Code)
   - Struktur und Konventionen (Verstöße gegen die im Projekt dokumentierten Regeln)
   - Uncommitted Changes (git status/diff), falls vorhanden
3. Je Befund: Datei:Zeile, Problem in einem Satz, konkrete Empfehlung.

## Erwartete Antwort

Deutsch. Maximal 10 Befunde, nach Schwere priorisiert. Erst ein Absatz Gesamteindruck, dann die Befundliste.
Kein Lob, keine Zusammenfassung am Ende.

## Grenzen

Nur lesen. Keine Dateien ändern.
EOF
}

read_handover() {
  if [[ -n "$HANDOVER_SRC" ]]; then
    if [[ "$HANDOVER_SRC" == "-" ]]; then
      HANDOVER="$(cat)"
    else
      [[ -r "$HANDOVER_SRC" ]] || die "Handover-Datei nicht lesbar: $HANDOVER_SRC"
      HANDOVER="$(cat "$HANDOVER_SRC")"
    fi
  elif [[ ! -t 0 ]] && read -r -t 0; then
    HANDOVER="$(cat)"
  else
    HANDOVER=""
  fi

  if [[ -z "${HANDOVER//[[:space:]]/}" ]]; then
    [[ "$MODE" == "ask" ]] || die "--mode execute braucht ein Handover (stdin oder --handover FILE)"
    log_info "Kein Handover -> Standard-Review"
    HANDOVER="$(default_review_prompt)"
  fi
}

require_cli() {
  command -v "$TARGET" >/dev/null 2>&1 \
    || die "'$TARGET' ist nicht im PATH. Die Ziel-CLI muss auf dem Host installiert sein (nicht aus nixpkgs)."
  command -v jq >/dev/null 2>&1 || die "jq fehlt (nix develop / nix run liefert es)."
}

CODEX_MODEL=""; CODEX_EFFORT=""
codex_model() {
  local catalog
  catalog="$(codex debug models 2>/dev/null)" || { log_warn "codex debug models fehlgeschlagen -> Codex-Default-Modell"; return; }
  CODEX_MODEL="$(jq -r '[.models[] | select(.visibility == "list")] | sort_by(.priority) | .[0].slug // empty' <<<"$catalog")"
  [[ -n "$CODEX_MODEL" ]] || { log_warn "Kein sichtbares Modell im Katalog -> Codex-Default-Modell"; return; }
  if jq -e --arg m "$CODEX_MODEL" --arg e "$EFFORT" \
       '.models[] | select(.slug == $m) | .supported_reasoning_levels[] | select(.effort == $e)' <<<"$catalog" >/dev/null; then
    CODEX_EFFORT="$EFFORT"
  else
    log_warn "Modell $CODEX_MODEL kennt Effort '$EFFORT' nicht -> Modell-Default"
  fi
  log_info "Codex-Flaggschiff: $CODEX_MODEL${CODEX_EFFORT:+ (effort $CODEX_EFFORT)}"
}

# Kennzeichnet den Aufruf im Resume-Picker beider CLIs.
session_label() { printf '/%s %s' "$MODE" "$(basename "$WORKDIR")"; }

CMD=()
build_cmd_codex() {
  CMD=(codex exec --color never -C "$WORKDIR" -c 'approval_policy="never"')
  [[ -n "$CODEX_MODEL" ]] && CMD+=(-m "$CODEX_MODEL")
  [[ -n "$CODEX_EFFORT" ]] && CMD+=(-c "model_reasoning_effort=\"$CODEX_EFFORT\"")
  if [[ "$MODE" == "ask" ]]; then
    CMD+=(-s read-only
      "[$(session_label)] Bearbeite den Auftrag im <stdin>-Block. Nur lesen, keine Dateien ändern. Antworte auf Deutsch.")
  else
    CMD+=(-s workspace-write
      "[$(session_label)] Bearbeite den Auftrag im <stdin>-Block. Änderungen nur im Workspace, kein Commit, kein Push. Antworte auf Deutsch und liste am Ende alle geänderten Dateien.")
  fi
}

build_cmd_claude() {
  CMD=(claude -p --model fable --effort "$EFFORT" --permission-prompts none
       --name "$(session_label)" --output-format text)
  if [[ "$MODE" == "ask" ]]; then
    CMD+=(--permission-mode dontAsk
      --tools Read Glob Grep Bash
      --allowedTools "Bash(git log *)" "Bash(git diff *)" "Bash(git status *)" "Bash(git show *)" "Bash(git branch *)"
      "Bearbeite den Auftrag aus stdin. Nur lesen, keine Dateien ändern. Antworte auf Deutsch.")
  else
    CMD+=(--permission-mode acceptEdits
      --allowedTools Edit Write MultiEdit NotebookEdit Bash
      --disallowedTools "Bash(git push *)" WebFetch WebSearch
      "Bearbeite den Auftrag aus stdin. Änderungen nur im Workspace, kein Commit, kein Push. Antworte auf Deutsch und liste am Ende alle geänderten Dateien.")
  fi
}

env_guard() {
  [[ "$TARGET" == "claude" ]] || return 0
  if [[ -n "${CLAUDECODE:-}" ]]; then
    log_warn "claude -p aus einer Claude-Code-Sitzung (nested) -> CLAUDECODE-Variablen werden entfernt"
    CMD=(env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_CODE_CHILD_SESSION "${CMD[@]}")
  fi
  if [[ "${CODEX_SANDBOX_NETWORK_DISABLED:-}" == "1" ]]; then
    log_warn "Codex-Sandbox ohne Netz: claude -p braucht API-Zugriff -> Aufruf mit require_escalated starten"
  fi
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    log_info "Dry-Run, Kommando:"
    printf '  %q' "${CMD[@]}" >&2; printf '\n' >&2
    log_info "Handover (stdin):"
    local lines; mapfile -t lines <<<"$HANDOVER"
    printf '  | %s\n' "${lines[@]}" >&2
    return 0
  fi
  log_info "Starte $TARGET (mode $MODE, effort $EFFORT) in $WORKDIR"
  local rc=0
  printf '%s\n' "$HANDOVER" | (cd "$WORKDIR" && "${CMD[@]}") || rc=$?
  if [[ $rc -eq 0 ]]; then log_ok "$TARGET fertig"; else log_err "$TARGET beendet mit Exit $rc"; fi
  return "$rc"
}

main() {
  parse_args "$@"
  detect_host
  read_handover
  if [[ "$DRY_RUN" == "0" ]]; then require_cli; fi
  if [[ "$TARGET" == "codex" ]]; then
    if command -v codex >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then codex_model; fi
    build_cmd_codex
  else
    build_cmd_claude
  fi
  env_guard
  run
}

main "$@"
