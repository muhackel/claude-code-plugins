#!/usr/bin/env bash
set -euo pipefail

# Offline-Regressionstests für scripts/ask.sh mit Stub-CLIs im PATH.
# Aufruf: tests/ask-test.sh PFAD/ZU/ask.sh   (braucht bash, jq, coreutils)

c_info=$'\e[34m'; c_ok=$'\e[32m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*" >&2; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }

[[ $# -eq 1 && -r "$1" ]] || { log_err "Usage: ask-test.sh PFAD/ZU/ask.sh"; exit 2; }
ASK="$1"
command -v jq >/dev/null 2>&1 || { log_err "jq fehlt"; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/proj"

# Shebang aus dem laufenden bash: in der Nix-Sandbox gibt es kein /usr/bin/env.
shebang="#!$BASH"
{ printf '%s\n' "$shebang"; cat <<'EOF'; } >"$WORK/bin/codex"
if [[ "${1:-}" == debug && "${2:-}" == models ]]; then
  printf '%s\n' "$*" >>"$STUB_LOG"
  case "${STUB_CATALOG:-ok}" in
    broken)   echo 'kein json' ;;
    nomodels) echo '{}' ;;
    noterra)  STUB_CATALOG=ok "$0" debug models | jq -c '.models |= map(select(.slug != "gpt-5.6-terra"))' ;;
    *) cat <<'JSON'
{"models":[
 {"slug":"gpt-5.6-astra","visibility":"list","priority":1,"supported_reasoning_levels":[{"effort":"medium"},{"effort":"high"}]},
 {"slug":"gpt-5.6-sol","visibility":"list","priority":2,"supported_reasoning_levels":[{"effort":"medium"},{"effort":"high"}]},
 {"slug":"gpt-5.6-terra","visibility":"list","priority":3,"supported_reasoning_levels":[{"effort":"medium"},{"effort":"high"}]},
 {"slug":"gpt-5.6-luna","visibility":"list","priority":4,"supported_reasoning_levels":[{"effort":"medium"}]},
 {"slug":"gpt-hidden","visibility":"hide","priority":0,"supported_reasoning_levels":[{"effort":"high"}]}
]}
JSON
    ;;
  esac
  exit 0
fi
printf 'codex-argv:'; printf ' %s' "$@"; printf '\n'; cat >/dev/null
EOF
{ printf '%s\n' "$shebang"; cat <<'EOF'; } >"$WORK/bin/claude"
printf 'claude-argv:'; printf ' %s' "$@"; printf '\n'; cat >/dev/null
EOF
chmod +x "$WORK/bin/codex" "$WORK/bin/claude"

export PATH="$WORK/bin:$PATH" STUB_LOG="$WORK/stub.log"
unset CLAUDECODE CODEX_SANDBOX_NETWORK_DISABLED
: >"$STUB_LOG"

FAILS=0
fail(){ log_err "$*"; FAILS=$((FAILS + 1)); }
expect_in(){ grep -qF -- "$2" <<<"$3" || fail "$1: '$2' fehlt"; }
expect_not(){ if grep -qF -- "$2" <<<"$3"; then fail "$1: '$2' unerwartet"; fi; }

# Dry-Run gibt argv mit doppelten Leerzeichen aus; für die Suche normalisieren.
ask(){ bash "$ASK" -C "$WORK/proj" "$@" 2>&1 | tr -s ' '; }
# Schreibt nach einer Pause auf stdout; liest ask.sh nicht, darf das keinen SIGPIPE-Abbruch auslösen.
feed(){ ( trap '' PIPE; sleep "$1"; printf '%s\n' "$2" 2>/dev/null || true ); }

log_info "(a) verzögerte Pipe wird gelesen"
out="$(feed 1 "Frage-verzögert-42" | ask --target codex --dry-run)" || fail "a: ask scheitert"
expect_in a "Frage-verzögert-42" "$out"
expect_not a "Standard-Review" "$out"
out="$(feed 1 "Auftrag-42" | ask --target codex --mode execute --dry-run)" \
  || fail "a: execute mit verzögerter Pipe scheitert"
expect_in a "Auftrag-42" "$out"

log_info "(b) </dev/null -> Standard-Review"
out="$(ask --target codex --dry-run </dev/null)"
expect_in b "Kein Handover -> Standard-Review" "$out"
expect_in b "gpt-5.6-sol" "$out"

log_info "(c) execute ohne Handover scheitert"
if out="$(ask --target codex --mode execute --dry-run </dev/null)"; then
  fail "c: Exit 0 statt Fehler"
fi
expect_in c "braucht ein Handover" "$out"

log_info "(d) kaputter Katalog -> Warnung + Rückfall, kein Abbruch"
for cat in broken nomodels; do
  out="$(feed 0 Frage | STUB_CATALOG="$cat" ask --target codex --tier light)" \
    || fail "d/$cat: Abbruch"
  expect_in "d/$cat" "nicht lesbar" "$out"
  expect_in "d/$cat" "Aufruf ohne Modellwahl" "$out"
  expect_in "d/$cat" "codex-argv: exec" "$out"
  expect_not "d/$cat" " -m " "$out"
  expect_not "d/$cat" "model_reasoning_effort" "$out"
done

log_info "(e) Modell je Klasse im Dry-Run"
grep -q -- "--bundled" "$STUB_LOG" || fail "e: codex debug models ohne --bundled"
declare -A codex_want=([light]="-m gpt-5.6-luna" [standard]="-m gpt-5.6-terra" [advanced]="-m gpt-5.6-sol" [strong]="-m gpt-5.6-astra")
declare -A claude_want=([light]="--model haiku --effort medium" [standard]="--model sonnet --effort high" [advanced]="--model opus --effort high" [strong]="--model fable --effort high")
for tier in light standard advanced strong; do
  out="$(feed 0 Frage | ask --target codex --tier "$tier" --dry-run)" || fail "e/codex/$tier: Abbruch"
  expect_in "e/codex/$tier" "${codex_want[$tier]}" "$out"
  out="$(feed 0 Frage | ask --target claude --tier "$tier" --dry-run)" || fail "e/claude/$tier: Abbruch"
  expect_in "e/claude/$tier" "${claude_want[$tier]}" "$out"
done
out="$(feed 0 Frage | ask --target codex --tier light --dry-run)" || fail "e/light-effort: Abbruch"
expect_in "e/light-effort" 'model_reasoning_effort=\"medium\"' "$out"
out="$(feed 0 Frage | STUB_CATALOG=noterra ask --target codex --tier standard --dry-run)" \
  || fail "e/rückfall: Abbruch"
expect_in "e/rückfall" "fehlt im Katalog" "$out"
expect_in "e/rückfall" "-m gpt-5.6-sol" "$out"

if [[ $FAILS -gt 0 ]]; then log_err "$FAILS Fehler"; exit 1; fi
log_ok "alle ask.sh-Tests grün"
