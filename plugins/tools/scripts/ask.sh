#!/usr/bin/env bash
set -euo pipefail

# Cross-CLI-Zweitmeinung: ruft non-interaktiv die jeweils andere CLI auf.
#   Host Claude Code (CLAUDECODE gesetzt) -> codex exec
#   Host Codex / normales Terminal        -> claude -p
# Modell: nach Stufe (--tier), Effort nach Stufe plus --boost/--fast; --model/--effort setzen beides frei.
# Handover (Markdown) kommt per stdin oder --handover FILE; ohne beides: Standard-Review.
# stdout = Antwort der anderen CLI, stderr = Fortschritt/Log. Codex schreibt seine ganze Trajektorie auf
# stdout; das Skript leitet sie nach stderr und gibt nur die letzte Nachricht (-o FILE) auf stdout aus.
# Claude liefert JSON; das Skript gibt .result aus und loggt die Modell-ID aus .modelUsage als Nachweis.


c_info=$'\e[34m'; c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*" >&2; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*" >&2; }
log_warn(){ printf '%s[!]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }
die(){ log_err "$@"; exit 1; }
# Option mit Wert: der Wert darf weder fehlen noch leer sein noch selbst eine Option (--…) sein.
optval(){ [[ $# -ge 2 && -n "$2" && "$2" != --* ]] || die "$1 braucht einen Wert"; }

usage() {
  cat >&2 <<'EOT'
Usage: ask.sh [--mode ask|execute] [--tier STUFE] [--boost|--fast] [--model SLUG] [--effort STUFE]
              [--target claude|codex] [--handover FILE|-] [--dry-run] [-C DIR] [-h]

  --mode ask        read-only (Default). Ohne Handover: Standard-Review des Projekts.
  --mode execute    workspace-write. Handover ist Pflicht.
  --tier STUFE      strong (fable/astra, medium), advanced (opus/sol, high; Default),
                    drone (sonnet/luna, high; nur execute).
  --boost           eine Effort-Stufe mehr: strong -> high, advanced -> xhigh.
  --fast            strong -> low. Nur bei strong.
  --model SLUG      Modell frei wählen (Alias oder Slug der Ziel-CLI), Effort dann high.
  --effort STUFE    Effort frei wählen: low, medium, high, xhigh, max. Überschreibt alles andere.
  --target CLI      Override der Host-Erkennung (Default: CLAUDECODE gesetzt -> codex, sonst claude).
  --handover FILE   Handover-Markdown aus Datei ('-' = stdin). Ohne Flag: stdin bis EOF, falls kein TTY.
                    Ohne Handover stdin schließen: </dev/null.
  --dry-run         Kommando und Handover-Vorschau ausgeben, keinen Auftrag starten (liest nur den Codex-Katalog).
  -C DIR            Arbeitsverzeichnis (Default: $PWD).
EOT
}

MODE="ask"; TARGET=""; HANDOVER_SRC=""; DRY_RUN=0; WORKDIR="$PWD"
TIER=""; BOOST=0; FAST=0; MODEL_OVERRIDE=""; EFFORT_OVERRIDE=""
EFFORT=""; CLAUDE_MODEL=""; CODEX_WISH=""
CODEX_FALLBACK="gpt-5.6-sol"   # Stufe advanced, Rückfall wenn ein Stufenmodell fehlt

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --mode)      optval "$@"; MODE="$2"; shift 2 ;;
      --target)    optval "$@"; TARGET="$2"; shift 2 ;;
      --tier)      optval "$@"; TIER="$2"; shift 2 ;;
      --model)     optval "$@"; MODEL_OVERRIDE="$2"; shift 2 ;;
      --effort)    optval "$@"; EFFORT_OVERRIDE="$2"; shift 2 ;;
      --handover)  optval "$@"; HANDOVER_SRC="$2"; shift 2 ;;
      -C)          optval "$@"; WORKDIR="$2"; shift 2 ;;
      --boost)     BOOST=1; shift ;;
      --fast)      FAST=1; shift ;;
      --dry-run)   DRY_RUN=1; shift ;;
      -h|--help)   usage; exit 0 ;;
      *)           usage; die "Unbekanntes Argument: $1" ;;
    esac
  done
  case "$MODE" in ask|execute) ;; *) die "--mode muss ask oder execute sein, nicht '$MODE'" ;; esac
  case "$TIER" in ""|drone|advanced|strong) ;;
    *) die "--tier muss strong, advanced oder drone sein, nicht '$TIER'" ;; esac
  case "$EFFORT_OVERRIDE" in ""|low|medium|high|xhigh|max) ;;
    *) die "--effort muss low, medium, high, xhigh oder max sein, nicht '$EFFORT_OVERRIDE'" ;; esac
  if [[ "$BOOST" == 1 && "$FAST" == 1 ]]; then die "--boost und --fast schließen sich aus"; fi
  if [[ -n "$MODEL_OVERRIDE" && ( -n "$TIER" || "$BOOST" == 1 || "$FAST" == 1 ) ]]; then
    die "--model kennt keine Stufe: --tier/--boost/--fast weglassen, den Effort mit --effort setzen"
  fi
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
  cat <<'EOT'
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
EOT
}

read_handover() {
  if [[ -n "$HANDOVER_SRC" ]]; then
    if [[ "$HANDOVER_SRC" == "-" ]]; then
      HANDOVER="$(cat)"
    else
      [[ -r "$HANDOVER_SRC" ]] || die "Handover-Datei nicht lesbar: $HANDOVER_SRC"
      HANDOVER="$(cat "$HANDOVER_SRC")"
    fi
  elif [[ ! -t 0 ]]; then
    # Immer bis EOF lesen: eine Pipe kann ihre Daten verzögert liefern. Ohne Handover: </dev/null.
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

# Stufen. Die starken Modelle brauchen für dieselbe Qualität weniger Effort, ihr Default liegt darum
# eine Stufe unter dem der advanced-Modelle.
#   strong   fable / Codex-Katalogspitze   medium   --boost high   --fast low
#   advanced opus  / sol                   high     --boost xhigh
#   drone    sonnet / luna                 high     nur execute: mechanische Umsetzung nach klarem Auftrag
# --model setzt das Modell frei (Effort high), --effort setzt den Effort frei.
resolve_tier() {
  if [[ -z "$TIER" ]]; then
    TIER="advanced"
    if [[ -z "$MODEL_OVERRIDE" ]]; then log_info "Keine Stufe angegeben -> $TIER"; fi
  fi
  if [[ "$TIER" == "drone" && "$MODE" == "ask" ]]; then die "Stufe drone gibt es nur bei --mode execute"; fi
  case "$TIER" in
    drone)    CLAUDE_MODEL="sonnet"; CODEX_WISH="gpt-5.6-luna"; EFFORT="high" ;;
    advanced) CLAUDE_MODEL="opus";   CODEX_WISH="gpt-5.6-sol";  EFFORT="high" ;;
    # Die Codex-Spitze wird nicht festgeschrieben, sondern aus dem Katalog der installierten Version genommen.
    strong)   CLAUDE_MODEL="fable";  CODEX_WISH="";             EFFORT="medium" ;;
  esac
  if [[ "$BOOST" == 1 ]]; then
    case "$TIER" in
      strong)   EFFORT="high" ;;
      advanced) EFFORT="xhigh" ;;
      drone)    die "--boost gibt es nicht bei drone" ;;
    esac
  fi
  if [[ "$FAST" == 1 ]]; then
    [[ "$TIER" == "strong" ]] || die "--fast gibt es nur bei strong"
    EFFORT="low"
  fi
  if [[ -n "$MODEL_OVERRIDE" ]]; then
    CLAUDE_MODEL="$MODEL_OVERRIDE"; CODEX_WISH="$MODEL_OVERRIDE"; EFFORT="high"
  fi
  if [[ -n "$EFFORT_OVERRIDE" ]]; then EFFORT="$EFFORT_OVERRIDE"; fi
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
  local catalog all visible wish="$CODEX_WISH" readable=1
  # Ohne lesbaren Katalog keine Stufenwahl. Statt abzubrechen entscheidet die CLI selbst.
  catalog="$(codex debug models --bundled 2>/dev/null)" || {
    log_warn "codex debug models fehlgeschlagen"; readable=0; }
  if [[ "$readable" == 1 ]]; then
    # Unlesbarer Katalog (kein JSON, kein .models) zählt wie ein fehlgeschlagener Aufruf.
    all="$(jq -c '[.models[]]' <<<"$catalog" 2>/dev/null)" || {
      log_warn "Katalog von codex debug models nicht lesbar"; readable=0; }
  fi
  if [[ "$readable" == 1 ]]; then
    visible="$(jq -c '[.[] | select(.visibility == "list")]' <<<"$all")"
  fi
  # --model: kein Rückfall. Geprüft gegen den vollen Katalog (auch versteckte Modelle), wenn er lesbar ist,
  # sonst ungeprüft durchgereicht.
  if [[ -n "$MODEL_OVERRIDE" ]]; then
    if [[ "$readable" == 0 ]]; then
      log_warn "--model $MODEL_OVERRIDE (effort $EFFORT) ungeprüft übernommen"
    else
      codex_usable "$all" "$MODEL_OVERRIDE" "$EFFORT" \
        || die "--model '$MODEL_OVERRIDE' (effort $EFFORT) fehlt im Katalog dieser Codex-Version"
      log_info "Modell -> $MODEL_OVERRIDE (effort $EFFORT)"
    fi
    CODEX_MODEL="$MODEL_OVERRIDE"; CODEX_EFFORT="$EFFORT"
    return
  fi
  if [[ "$readable" == 0 ]]; then log_warn "-> Aufruf ohne Modellwahl"; return; fi
  if [[ -z "$wish" ]]; then wish="$(jq -r 'sort_by(.priority) | .[0].slug // empty' <<<"$visible")"; fi
  # Fällt ein Slug aus dem Katalog, erst auf advanced zurück, dann der CLI überlassen.
  # Ein Aufruf ohne -m landet bei Codex auf dem Flaggschiff, deshalb ist advanced die Zwischenstufe.
  if codex_usable "$visible" "$wish" "$EFFORT"; then
    CODEX_MODEL="$wish"; CODEX_EFFORT="$EFFORT"
    log_info "Stufe $TIER -> $CODEX_MODEL (effort $CODEX_EFFORT)"
  elif [[ "$wish" != "$CODEX_FALLBACK" ]] && codex_usable "$visible" "$CODEX_FALLBACK" "$EFFORT"; then
    CODEX_MODEL="$CODEX_FALLBACK"; CODEX_EFFORT="$EFFORT"
    log_warn "Stufe $TIER: '$wish' (effort $EFFORT) fehlt im Katalog dieser CLI-Version -> $CODEX_MODEL"
  elif [[ "$wish" != "$CODEX_FALLBACK" ]]; then
    log_warn "Stufe $TIER: weder '$wish' noch '$CODEX_FALLBACK' (effort $EFFORT) im Katalog -> Aufruf ohne Modellwahl"
  else
    log_warn "Stufe $TIER: '$wish' (effort $EFFORT) nicht im Katalog -> Aufruf ohne Modellwahl"
  fi
}

# Kennzeichnet den Aufruf im Resume-Picker beider CLIs: Stufe mit + (boost) / - (fast), oder das freie Modell.
session_label() {
  local stufe="$TIER"
  if [[ -n "$MODEL_OVERRIDE" ]]; then stufe="$MODEL_OVERRIDE"
  elif [[ "$BOOST" == 1 ]]; then stufe+="+"
  elif [[ "$FAST" == 1 ]]; then stufe+="-"
  fi
  printf '/%s %s %s' "$MODE" "$stufe" "$(basename "$WORKDIR")"
}

CMD=()
OUT_FILE=""   # Codex: letzte Nachricht (-o); Claude: JSON-Ergebnis
build_cmd_codex() {
  OUT_FILE="$(mktemp -t ask-codex-last.XXXXXX)"
  trap 'rm -f "$OUT_FILE"' EXIT
  CMD=(codex exec --color never -C "$WORKDIR" -c 'approval_policy="never"' -o "$OUT_FILE")
  if [[ -n "$CODEX_MODEL" ]]; then CMD+=(-m "$CODEX_MODEL"); fi
  if [[ -n "$CODEX_EFFORT" ]]; then CMD+=(-c "model_reasoning_effort=\"$CODEX_EFFORT\""); fi
  if [[ "$MODE" == "ask" ]]; then
    CMD+=(-s read-only
      "[$(session_label)] Bearbeite den Auftrag im <stdin>-Block. Nur lesen, keine Dateien ändern. Antworte auf Deutsch.")
  else
    CMD+=(-s workspace-write
      "[$(session_label)] Bearbeite den Auftrag im <stdin>-Block. Änderungen nur im Workspace, kein Commit, kein Push. Antworte auf Deutsch und liste am Ende alle geänderten Dateien.")
  fi
}

# Mustersemantik laut https://code.claude.com/docs/en/permissions (Stand 2026-09):
# - `*` steht für beliebigen Text inkl. Leerzeichen; `Bash(git log *)` erlaubt auch `git log --output=<Datei>`.
# - deny vor ask vor allow; eine deny-Regel kennt keine allow-Ausnahmen.
# - dontAsk verweigert alles, was sonst nachfragen würde. Ohne Nachfrage laufen Lesezugriffe im
#   Arbeitsverzeichnis und das eingebaute Read-only-Set von Bash, zu dem nur die lesenden git-Formen gehören.
# - Bash-Regeln matchen den Befehlstext, keine Programmgrenze (`git -C . push`, `sh -c '…'`, `/usr/bin/git`).
# ask: keine allow-Regeln für git. Jede allow-Regel mit `*` würde schreibende Optionen mitfreigeben; das
# eingebaute Read-only-Set plus dontAsk ist die engere Grenze. Die deny-Regeln sichern die bekannten
# schreibenden Formen zusätzlich über den Text ab. Die deny-Regel Edit greift auch für Umleitungen (`> datei`).
CLAUDE_ASK_DENY=(
  Edit
  "Bash(git branch -d *)" "Bash(git branch -D *)" "Bash(git branch --delete *)"
  "Bash(git branch -m *)" "Bash(git branch -M *)" "Bash(git branch --move *)"
  "Bash(git branch -c *)" "Bash(git branch -C *)" "Bash(git branch --copy *)"
  "Bash(git branch -f *)" "Bash(git branch --force *)"
  "Bash(git branch -u *)" "Bash(git branch --set-upstream-to*)" "Bash(git branch --unset-upstream*)"
  "Bash(git branch --edit-description*)"
  # --out* statt --output: gitcli(7) erlaubt vielen Befehlen eindeutige Abkürzungen langer Optionen.
  "Bash(git * --out*)"
)
# execute: Bash ist frei, `git push` ist nur über den Befehlstext gesperrt. `git * push` deckt Formen mit
# Optionen vor dem Unterbefehl ab (`git -C . push`, `git -c k=v push origin`); die Variante ohne
# nachgestelltes `*` braucht es, weil ein `*` am Ende den nackten Befehl nur bei einem einzigen Wildcard trifft.
CLAUDE_EXECUTE_DENY=("Bash(git push *)" "Bash(git * push)" "Bash(git * push *)" WebFetch WebSearch)

build_cmd_claude() {
  # Der Prompt steht direkt hinter -p: --tools/--allowedTools/--disallowedTools sind variadisch
  # (<tools...>, claude --help) und können ein nachgestelltes Positionsargument als weiteren Eintrag schlucken.
  local prompt
  if [[ "$MODE" == "ask" ]]; then
    prompt="Bearbeite den Auftrag aus stdin. Nur lesen, keine Dateien ändern. Antworte auf Deutsch."
  else
    prompt="Bearbeite den Auftrag aus stdin. Änderungen nur im Workspace, kein Commit, kein Push. Antworte auf Deutsch und liste am Ende alle geänderten Dateien."
  fi
  OUT_FILE="$(mktemp -t ask-claude-json.XXXXXX)"
  trap 'rm -f "$OUT_FILE"' EXIT
  # JSON statt text: .result ist die Antwort, .modelUsage nennt die tatsächlich verwendete Modell-ID.
  CMD=(claude -p "$prompt" --model "$CLAUDE_MODEL" --effort "$EFFORT" --permission-prompts none
       --name "$(session_label)" --output-format json)
  if [[ "$MODE" == "ask" ]]; then
    CMD+=(--permission-mode dontAsk
      --tools Read Glob Grep Bash
      --disallowedTools "${CLAUDE_ASK_DENY[@]}")
  else
    CMD+=(--permission-mode acceptEdits
      --allowedTools Edit Write MultiEdit NotebookEdit Bash
      --disallowedTools "${CLAUDE_EXECUTE_DENY[@]}")
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

# Antwort aus dem JSON von claude -p: .result auf stdout, Modell-IDs aus .modelUsage als Nachweis auf stderr.
# Kein gültiges JSON (Absturz, Login-Fehler): Ausgabe unverändert durchreichen.
claude_result() {
  local models
  if ! jq -e 'type == "object" and has("result")' "$OUT_FILE" >/dev/null 2>&1; then
    log_warn "claude hat kein Ergebnis-JSON geliefert -> Ausgabe unverändert"
    cat "$OUT_FILE"; return
  fi
  models="$(jq -r '(.modelUsage // {}) | keys | join(", ")' "$OUT_FILE")"
  if [[ -n "$models" ]]; then log_info "Modell laut claude: $models (effort per Flag: $EFFORT)"
  else log_warn "claude nennt kein Modell in modelUsage"; fi
  if [[ "$(jq -r '.is_error // false' "$OUT_FILE")" == "true" ]]; then
    log_warn "claude meldet is_error=true ($(jq -r '.subtype // "?"' "$OUT_FILE"))"
  fi
  jq -r '.result // ""' "$OUT_FILE"
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
  log_info "Starte $TARGET (mode $MODE, Stufe $TIER, effort $EFFORT) in $WORKDIR"
  local rc=0
  if [[ "$TARGET" == "codex" ]]; then
    # Trajektorie (Tool-Aufrufe, Zwischenschritte) nach stderr, auf stdout nur die letzte Nachricht.
    printf '%s\n' "$HANDOVER" | (cd "$WORKDIR" && "${CMD[@]}") >&2 || rc=$?
    if [[ -s "$OUT_FILE" ]]; then
      cat "$OUT_FILE"; [[ "$(tail -c1 "$OUT_FILE")" == "" ]] || printf '\n'
    else
      log_warn "codex hat keine letzte Nachricht geschrieben"
    fi
  else
    printf '%s\n' "$HANDOVER" | (cd "$WORKDIR" && "${CMD[@]}") >"$OUT_FILE" || rc=$?
    claude_result
  fi
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
    if command -v codex >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
      codex_model
    elif [[ -n "$MODEL_OVERRIDE" ]]; then
      CODEX_MODEL="$MODEL_OVERRIDE"; CODEX_EFFORT="$EFFORT"
    fi
    build_cmd_codex
  else
    build_cmd_claude
  fi
  env_guard
  run
}

main "$@"
