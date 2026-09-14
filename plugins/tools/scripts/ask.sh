#!/usr/bin/env bash
set -euo pipefail

# Cross-CLI-Zweitmeinung: ruft non-interaktiv die jeweils andere CLI auf.
#   Host Claude Code (CLAUDECODE gesetzt) -> codex exec
#   Host Codex / normales Terminal        -> claude -p
# Modell: nach Aufgabenklasse (--tier), nicht pauschal das Flaggschiff.
# Handover (Markdown) kommt per stdin oder --handover FILE; ohne beides: Standard-Review.
# stdout = Antwort der anderen CLI, stderr = Fortschritt/Log.


c_info=$'\e[34m'; c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*" >&2; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*" >&2; }
log_warn(){ printf '%s[!]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }
die(){ log_err "$@"; exit 1; }

usage() {
  cat >&2 <<'EOF'
Usage: ask.sh [--mode ask|execute] [--tier KLASSE] [--target claude|codex] [--handover FILE|-] [--dry-run] [-h]

  --mode ask        read-only (Default). Ohne Handover: Standard-Review des Projekts.
  --mode execute    workspace-write. Handover ist Pflicht.
  --tier KLASSE     Aufgabenklasse: light, standard, advanced, strong.
                    Ohne Angabe: advanced beim Standard-Review, sonst standard.
  --target CLI      Override der Host-Erkennung (Default: CLAUDECODE gesetzt -> codex, sonst claude).
  --handover FILE   Handover-Markdown aus Datei ('-' = stdin). Ohne Flag: stdin, falls kein TTY.
  --dry-run         Kommando und Handover-Vorschau ausgeben, nichts aufrufen.
  -C DIR            Arbeitsverzeichnis (Default: $PWD).
EOF
}

MODE="ask"; TARGET=""; HANDOVER_SRC=""; DRY_RUN=0; WORKDIR="$PWD"
TIER=""; DEFAULT_REVIEW=0; EFFORT=""; CLAUDE_MODEL=""
CODEX_FALLBACK="gpt-5.6-sol"   # Klasse advanced, Rückfall wenn ein Klassenmodell fehlt

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)      [[ $# -ge 2 ]] || die "--mode braucht einen Wert"; MODE="$2"; shift 2 ;;
      --target)    [[ $# -ge 2 ]] || die "--target braucht einen Wert"; TARGET="$2"; shift 2 ;;
      --tier)      [[ $# -ge 2 ]] || die "--tier braucht einen Wert"; TIER="$2"; shift 2 ;;
      --handover)  [[ $# -ge 2 ]] || die "--handover braucht einen Wert"; HANDOVER_SRC="$2"; shift 2 ;;
      -C)          [[ $# -ge 2 ]] || die "-C braucht einen Wert"; WORKDIR="$2"; shift 2 ;;
      --dry-run)   DRY_RUN=1; shift ;;
      -h|--help)   usage; exit 0 ;;
      *)           usage; die "Unbekanntes Argument: $1" ;;
    esac
  done
  case "$MODE" in ask|execute) ;; *) die "--mode muss ask oder execute sein, nicht '$MODE'" ;; esac
  case "$TIER" in ""|light|standard|advanced|strong) ;;
    *) die "--tier muss light, standard, advanced oder strong sein, nicht '$TIER'" ;; esac
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
    DEFAULT_REVIEW=1
    HANDOVER="$(default_review_prompt)"
  fi
}

require_cli() {
  command -v "$TARGET" >/dev/null 2>&1 \
    || die "'$TARGET' ist nicht im PATH. Die Ziel-CLI muss auf dem Host installiert sein (nicht aus nixpkgs)."
  command -v jq >/dev/null 2>&1 || die "jq fehlt (nix develop / nix run liefert es)."
}

# Aufgabenklassen. Die Staffelung entspricht der Subagenten-Staffelung von philharmonie.
#   light    eindeutige Kleinarbeit: String fixen, Datei finden, Formatierung
#   standard einzelnes Modul, Test, lokale Fehleranalyse
#   advanced mehrere Module, Refactoring, schwere Fehlersuche, Projekt-Review
#   strong   Architektur, widersprüchliche Anforderungen, Planung vor der Umsetzung
resolve_tier() {
  if [[ -z "$TIER" ]]; then
    if [[ "$DEFAULT_REVIEW" == "1" ]]; then TIER="advanced"; else TIER="standard"; fi
    log_info "Keine Klasse angegeben -> $TIER"
  fi
  case "$TIER" in
    light)    CLAUDE_MODEL="haiku";  EFFORT="medium" ;;
    standard) CLAUDE_MODEL="sonnet"; EFFORT="high" ;;
    advanced) CLAUDE_MODEL="opus";   EFFORT="high" ;;
    strong)   CLAUDE_MODEL="fable";  EFFORT="high" ;;
  esac
}

# Ist das Modell im Katalog sichtbar und kann es den Effort?
codex_usable() {
  local visible="$1" model="$2" effort="$3"
  [[ -n "$model" ]] || return 1
  jq -e --arg m "$model" --arg e "$effort" \
     '.[] | select(.slug == $m) | .supported_reasoning_levels[] | select(.effort == $e)' <<<"$visible" >/dev/null
}

CODEX_MODEL=""; CODEX_EFFORT=""
codex_model() {
  local catalog visible wish
  # Ohne lesbaren Katalog keine Klassenwahl. Statt abzubrechen entscheidet die CLI selbst.
  catalog="$(codex debug models 2>/dev/null)" || {
    log_warn "codex debug models fehlgeschlagen -> Aufruf ohne Modellwahl"; return; }
  visible="$(jq -c '[.models[] | select(.visibility == "list")]' <<<"$catalog")"
  case "$TIER" in
    light)    wish="gpt-5.6-luna" ;;
    standard) wish="gpt-5.6-terra" ;;
    advanced) wish="gpt-5.6-sol" ;;
    # Die Spitze wird nicht festgeschrieben, sondern aus dem Katalog der installierten Version genommen.
    strong)   wish="$(jq -r 'sort_by(.priority) | .[0].slug // empty' <<<"$visible")" ;;
  esac
  # Fällt ein Slug aus dem Katalog, erst auf advanced zurück, dann der CLI überlassen.
  # Ein Aufruf ohne -m landet bei Codex auf dem Flaggschiff, deshalb ist advanced die Zwischenstufe.
  if codex_usable "$visible" "$wish" "$EFFORT"; then
    CODEX_MODEL="$wish"; CODEX_EFFORT="$EFFORT"
    log_info "Klasse $TIER -> $CODEX_MODEL (effort $CODEX_EFFORT)"
  elif codex_usable "$visible" "$CODEX_FALLBACK" "$EFFORT"; then
    CODEX_MODEL="$CODEX_FALLBACK"; CODEX_EFFORT="$EFFORT"
    log_warn "Klasse $TIER: '$wish' fehlt im Katalog dieser CLI-Version -> $CODEX_MODEL"
  else
    log_warn "Klasse $TIER: weder '$wish' noch '$CODEX_FALLBACK' im Katalog -> Aufruf ohne Modellwahl"
  fi
}

# Kennzeichnet den Aufruf im Resume-Picker beider CLIs.
session_label() { printf '/%s %s %s' "$MODE" "$TIER" "$(basename "$WORKDIR")"; }

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
  CMD=(claude -p --model "$CLAUDE_MODEL" --effort "$EFFORT" --permission-prompts none
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
  log_info "Starte $TARGET (mode $MODE, Klasse $TIER, effort $EFFORT) in $WORKDIR"
  local rc=0
  printf '%s\n' "$HANDOVER" | (cd "$WORKDIR" && "${CMD[@]}") || rc=$?
  if [[ $rc -eq 0 ]]; then log_ok "$TARGET fertig"; else log_err "$TARGET beendet mit Exit $rc"; fi
  return "$rc"
}

main() {
  parse_args "$@"
  detect_host
  read_handover
  resolve_tier
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
