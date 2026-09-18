#!/usr/bin/env bash
# Codex-Messlauf unter Watchdog: run-codex.sh <before|after> <run-id> <prompt> [weitere codex-exec-Argumente ...]
# Umgebung: LAZY_MESS (Default /tmp/lazy-mess, Basis für CODEX_HOME/Logs), LAZY_CWD (Default $LAZY_MESS/work)
# Log: $LAZY_MESS/logs/runs/<run-id>.jsonl
set -euo pipefail

log_info() { printf '\033[34m[INFO]\033[0m %s\n' "$*" >&2; }
log_ok()   { printf '\033[32m[ OK ]\033[0m %s\n' "$*" >&2; }
log_warn() { printf '\033[33m[WARN]\033[0m %s\n' "$*" >&2; }
log_err()  { printf '\033[31m[ERR ]\033[0m %s\n' "$*" >&2; }

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
BASE=${LAZY_MESS:-/tmp/lazy-mess}

if [[ $# -lt 3 ]]; then
  log_err "Aufruf: $0 <before|after> <run-id> <prompt> [codex-exec-Argumente ...]"
  exit 64
fi
state=$1 run_id=$2 prompt=$3
shift 3
case "$state" in before|after) ;; *) log_err "Zustand muss before oder after sein: $state"; exit 64 ;; esac
if [[ ! "$run_id" =~ ^[A-Za-z0-9._-]+$ ]]; then log_err "run-id nur [A-Za-z0-9._-]: $run_id"; exit 64; fi

home=$BASE/codex-$state
[[ -f "$home/config.toml" ]] || { log_err "CODEX_HOME fehlt: $home"; exit 66; }
cwd=${LAZY_CWD:-$BASE/work}
case "$cwd" in /tmp/*) ;; *) log_err "LAZY_CWD muss unter /tmp liegen: $cwd"; exit 64 ;; esac
mkdir -p "$cwd" "$BASE/logs/runs" "$BASE/tmpdir"
logf=$BASE/logs/runs/$run_id.jsonl
errf=$BASE/logs/runs/$run_id.stderr
[[ -e "$logf" ]] && { log_err "Log existiert schon: $logf"; exit 65; }

log_info "codex [$state] run=$run_id CODEX_HOME=$home cwd=$cwd log=$logf"
set +e
CODEX_HOME=$home TMPDIR=$BASE/tmpdir LAZY_MESS=$BASE "$SCRIPT_DIR/py" "$SCRIPT_DIR/watchdog.py" run --log "$logf" --cwd "$cwd" -- \
  codex exec --json --skip-git-repo-check -C "$cwd" -m gpt-5.6-sol -c 'model_reasoning_effort="high"' "$@" -- "$prompt" \
  2> "$errf"
rc=$?
set -e
if [[ $rc -eq 99 ]]; then
  log_warn "Watchdog hat den Lauf abgebrochen, Befund in $BASE/watchdog-events.jsonl"
elif [[ $rc -ne 0 ]]; then
  log_warn "codex rc=$rc, stderr: $errf"
else
  log_ok "fertig"
fi
exit "$rc"
