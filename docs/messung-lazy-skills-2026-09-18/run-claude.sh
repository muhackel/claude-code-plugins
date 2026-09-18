#!/usr/bin/env bash
# Claude-Messlauf unter Watchdog: run-claude.sh <before|after> <run-id> <prompt> [weitere claude-Argumente ...]
# Umgebung: LAZY_MESS (Default /tmp/lazy-mess, Basis für Zustände/Logs), LAZY_CWD (Default $LAZY_MESS/work)
# Log: $LAZY_MESS/logs/runs/<run-id>.jsonl
set -euo pipefail

log_info() { printf '\033[34m[INFO]\033[0m %s\n' "$*" >&2; }
log_ok()   { printf '\033[32m[ OK ]\033[0m %s\n' "$*" >&2; }
log_warn() { printf '\033[33m[WARN]\033[0m %s\n' "$*" >&2; }
log_err()  { printf '\033[31m[ERR ]\033[0m %s\n' "$*" >&2; }

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
BASE=${LAZY_MESS:-/tmp/lazy-mess}
PLUGINS=(bibliothekarin nixie it-grundschutz bertram christian tools)

if [[ $# -lt 3 ]]; then
  log_err "Aufruf: $0 <before|after> <run-id> <prompt> [claude-Argumente ...]"
  exit 64
fi
state=$1 run_id=$2 prompt=$3
shift 3
case "$state" in before|after) ;; *) log_err "Zustand muss before oder after sein: $state"; exit 64 ;; esac
if [[ ! "$run_id" =~ ^[A-Za-z0-9._-]+$ ]]; then log_err "run-id nur [A-Za-z0-9._-]: $run_id"; exit 64; fi

cwd=${LAZY_CWD:-$BASE/work}
case "$cwd" in /tmp/*) ;; *) log_err "LAZY_CWD muss unter /tmp liegen: $cwd"; exit 64 ;; esac
mkdir -p "$cwd" "$BASE/logs/runs"
logf=$BASE/logs/runs/$run_id.jsonl
[[ -e "$logf" ]] && { log_err "Log existiert schon: $logf"; exit 65; }

# claude-settings-guard.json enthält einen Platzhalter für den Hook-Befehl, der hier mit dem
# tatsächlichen Skriptverzeichnis gefüllt wird (siehe README.md).
guard_settings=$(sed "s#__WATCHDOG_HOOK_CMD__#$SCRIPT_DIR/py $SCRIPT_DIR/watchdog.py hook#" "$SCRIPT_DIR/claude-settings-guard.json")
args=(-p --output-format stream-json --verbose --no-session-persistence
      --settings "$guard_settings")
for p in "${PLUGINS[@]}"; do
  [[ -f "$BASE/$state/plugins/$p/.claude-plugin/plugin.json" ]] || { log_err "Plugin fehlt: $state/$p"; exit 66; }
  args+=(--plugin-dir "$BASE/$state/plugins/$p")
done

log_info "claude [$state] run=$run_id cwd=$cwd log=$logf"
set +e
(cd "$cwd" && LAZY_MESS=$BASE "$SCRIPT_DIR/py" "$SCRIPT_DIR/watchdog.py" run --log "$logf" --cwd "$cwd" -- \
  claude "${args[@]}" "$@" -- "$prompt")
rc=$?
set -e
if [[ $rc -eq 99 ]]; then
  log_warn "Watchdog hat den Lauf abgebrochen, Befund in $BASE/watchdog-events.jsonl"
elif [[ $rc -ne 0 ]]; then
  log_warn "claude rc=$rc"
else
  bad=$(jq -r 'select(.type=="system" and .subtype=="init") | [.plugins[] | select(.source | test("@inline$") | not) | .source] | join(",")' "$logf")
  if [[ -n "$bad" ]]; then log_warn "Nicht-inline-Plugins aktiv: $bad"; else log_ok "nur @inline-Plugins aktiv"; fi
fi
exit "$rc"
