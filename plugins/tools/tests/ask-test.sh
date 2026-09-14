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
mkdir -p "$WORK/bin" "$WORK/proj" "$WORK/stub"

# Die Stubs schreiben argv (ein Argument je Zeile) und ihr vollständiges stdin nach $STUB_DIR.
# Katalog-Varianten: STUB_CATALOG=ok|fail|broken|nomodels|empty,
#   STUB_DROP="slug …" entfernt Modelle, STUB_STRIP="slug:effort …" entfernt einzelne Efforts.
# STUB_EXIT setzt den Exit-Code des eigentlichen Aufrufs.
# Shebang aus dem laufenden bash: in der Nix-Sandbox gibt es kein /usr/bin/env.
shebang="#!$BASH"
{ printf '%s\n' "$shebang"; cat <<'EOF'; } >"$WORK/bin/codex"
if [[ "${1:-}" == debug ]]; then
  if [[ $# -ne 3 || "$1 $2 $3" != "debug models --bundled" ]]; then
    printf 'BAD: %s\n' "$*" >>"$STUB_LOG"
    echo "stub-codex: erwartet exakt 'debug models --bundled', bekam: $*" >&2
    exit 97
  fi
  printf '%s\n' "$*" >>"$STUB_LOG"
  case "${STUB_CATALOG:-ok}" in
    fail)     echo "stub-codex: Katalog kaputt" >&2; exit 3 ;;
    broken)   echo 'kein json' ;;
    nomodels) echo '{}' ;;
    empty)    echo '{"models":[]}' ;;
    *) jq -c --arg drop "${STUB_DROP:-}" --arg strip "${STUB_STRIP:-}" '
         ($drop | split(" ")) as $d | ($strip | split(" ")) as $s
         | .models |= map(select(.slug as $x | any($d[]; . == $x) | not)
             | .slug as $x
             | .supported_reasoning_levels |= map(select(($x + ":" + .effort) as $k | any($s[]; . == $k) | not)))' <<'JSON'
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
printf '%s\n' "$@" >"$STUB_DIR/codex.argv"
cat >"$STUB_DIR/codex.stdin"
printf 'codex-argv:'; printf ' %s' "$@"; printf '\n'
exit "${STUB_EXIT:-0}"
EOF
{ printf '%s\n' "$shebang"; cat <<'EOF'; } >"$WORK/bin/claude"
printf '%s\n' "$@" >"$STUB_DIR/claude.argv"
cat >"$STUB_DIR/claude.stdin"
printf 'claude-argv:'; printf ' %s' "$@"; printf '\n'
exit "${STUB_EXIT:-0}"
EOF
chmod +x "$WORK/bin/codex" "$WORK/bin/claude"

export PATH="$WORK/bin:$PATH" STUB_LOG="$WORK/stub.log" STUB_DIR="$WORK/stub"
unset CLAUDECODE CODEX_SANDBOX_NETWORK_DISABLED STUB_CATALOG STUB_DROP STUB_STRIP STUB_EXIT
: >"$STUB_LOG"

FAILS=0
fail(){ log_err "$*"; FAILS=$((FAILS + 1)); }
expect_in(){ grep -qF -- "$2" <<<"$3" || fail "$1: '$2' fehlt"; }
expect_not(){ if grep -qF -- "$2" <<<"$3"; then fail "$1: '$2' unerwartet"; fi; }
# argv-Prüfungen gegen die Datei des Stubs: exakte Argumente statt Teilstrings.
expect_no_arg(){ if grep -qxF -- "$2" "$STUB_DIR/$3.argv"; then fail "$1: Argument '$2' unerwartet"; fi; }
expect_no_arg_prefix(){ if grep -qF -- "$2" "$STUB_DIR/$3.argv"; then fail "$1: Argument mit '$2' unerwartet"; fi; }
# Zwei aufeinanderfolgende Argumente (Option + Wert).
expect_pair(){
  local joined sep=$'\037'
  joined="$sep$(tr '\n' '\037' <"$STUB_DIR/$4.argv")"
  [[ "$joined" == *"$sep$2$sep$3$sep"* ]] || fail "$1: Argumentpaar '$2 $3' fehlt"
}
# Alle Argumente nach FLAG bis zur nächsten Option.
args_after(){
  awk -v f="$1" '$0 == f { on = 1; next } on && /^--/ { on = 0 } on' "$STUB_DIR/$2.argv"
}
reset_stub(){ rm -f "$STUB_DIR"/*; }

# Dry-Run gibt argv mit doppelten Leerzeichen aus; für die Suche normalisieren.
ask(){ bash "$ASK" -C "$WORK/proj" "$@" 2>&1 | tr -s ' '; }
# Schreibt nach einer Pause auf stdout; liest ask.sh nicht, darf das keinen SIGPIPE-Abbruch auslösen.
feed(){ ( trap '' PIPE; sleep "$1"; printf '%s\n' "$2" 2>/dev/null || true ); }
# Mehrere zeitversetzte Blöcke, inklusive Leerzeile, Umlauten und Sonderzeichen.
feed_blocks(){
  ( trap '' PIPE
    { printf '# Handover\n\n## Frage\n'; sleep 0.4
      printf 'Block zwei: Größe %s "q"\n' "\$HOME|*"; sleep 0.4
      printf '\n  eingerückt\tTab\n'; sleep 0.4
      printf 'Block vier Ende\n'; } 2>/dev/null || true )
}
feed_blocks_expected(){
  printf '# Handover\n\n## Frage\nBlock zwei: Größe %s "q"\n\n  eingerückt\tTab\nBlock vier Ende\n' "\$HOME|*"
}

log_info "(a) zeitversetzte stdin-Blöcke kommen vollständig beim Stub an"
feed_blocks_expected >"$WORK/expected.stdin"
for target in codex claude; do
  for mode in ask execute; do
    reset_stub
    rc=0; out="$(feed_blocks | ask --target "$target" --mode "$mode" --tier light)" || rc=$?
    [[ $rc -eq 0 ]] || fail "a/$target/$mode: Exit $rc"
    expect_not "a/$target/$mode" "Standard-Review" "$out"
    if [[ ! -e "$STUB_DIR/$target.stdin" ]]; then
      fail "a/$target/$mode: Stub nicht aufgerufen"
    elif ! cmp -s "$WORK/expected.stdin" "$STUB_DIR/$target.stdin"; then
      fail "a/$target/$mode: stdin beim Stub weicht ab: $(diff "$WORK/expected.stdin" "$STUB_DIR/$target.stdin" | tr '\n' ' ')"
    fi
  done
done

log_info "(b) </dev/null -> Standard-Review"
out="$(ask --target codex --dry-run </dev/null)"
expect_in b "Kein Handover -> Standard-Review" "$out"
expect_in b "gpt-5.6-sol" "$out"

log_info "(c) execute ohne Handover scheitert"
if out="$(ask --target codex --mode execute --dry-run </dev/null)"; then
  fail "c: Exit 0 statt Fehler"
fi
expect_in c "braucht ein Handover" "$out"

log_info "(d) Rückfallkette mit tatsächlichem argv, Warnung und Exit-Code"
# Fall | Katalog | DROP | STRIP | Klasse | erwartetes Modell (leer = ohne -m) | Effort | Warnung
cases=(
  "fail|fail|||light|||codex debug models fehlgeschlagen"
  "broken|broken|||light|||nicht lesbar"
  "nomodels|nomodels|||light|||nicht lesbar"
  "leer|empty|||light|||weder 'gpt-5.6-luna' noch 'gpt-5.6-sol'"
  "ohne-luna-und-sol|ok|gpt-5.6-luna gpt-5.6-sol||light|||weder 'gpt-5.6-luna' noch 'gpt-5.6-sol'"
  "ohne-terra|ok|gpt-5.6-terra||standard|gpt-5.6-sol|high|'gpt-5.6-terra' (effort high) fehlt im Katalog"
  "terra-ohne-high|ok||gpt-5.6-terra:high|standard|gpt-5.6-sol|high|'gpt-5.6-terra' (effort high) fehlt im Katalog"
  "terra-und-sol-ohne-high|ok||gpt-5.6-terra:high gpt-5.6-sol:high|standard|||weder 'gpt-5.6-terra' noch 'gpt-5.6-sol'"
  "luna-ohne-medium|ok||gpt-5.6-luna:medium|light|gpt-5.6-sol|medium|'gpt-5.6-luna' (effort medium) fehlt im Katalog"
)
for c in "${cases[@]}"; do
  IFS='|' read -r name catalog drop strip tier model effort warn <<<"$c"
  reset_stub
  rc=0
  out="$(feed 0 Frage | STUB_CATALOG="$catalog" STUB_DROP="$drop" STUB_STRIP="$strip" \
         ask --target codex --tier "$tier")" || rc=$?
  [[ $rc -eq 0 ]] || fail "d/$name: Exit $rc"
  expect_in "d/$name" "$warn" "$out"
  if [[ ! -e "$STUB_DIR/codex.argv" ]]; then fail "d/$name: codex exec nicht aufgerufen"; continue; fi
  [[ "$(head -n1 "$STUB_DIR/codex.argv")" == exec ]] || fail "d/$name: erstes Argument nicht 'exec'"
  if [[ -z "$model" ]]; then
    expect_in "d/$name" "Aufruf ohne Modellwahl" "$out"
    expect_no_arg "d/$name" "-m" codex
    expect_no_arg_prefix "d/$name" "model_reasoning_effort" codex
  else
    expect_pair "d/$name" -m "$model" codex
    expect_pair "d/$name" -c "model_reasoning_effort=\"$effort\"" codex
  fi
done
reset_stub
rc=0; out="$(feed 0 Frage | STUB_EXIT=7 ask --target codex --tier light)" || rc=$?
[[ $rc -eq 7 ]] || fail "d/exit: Exit-Code der CLI nicht durchgereicht ($rc statt 7)"
expect_in d/exit "beendet mit Exit 7" "$out"

log_info "(e) Modell je Klasse"
declare -A codex_want=([light]="gpt-5.6-luna" [standard]="gpt-5.6-terra" [advanced]="gpt-5.6-sol" [strong]="gpt-5.6-astra")
declare -A effort_want=([light]="medium" [standard]="high" [advanced]="high" [strong]="high")
declare -A claude_want=([light]="haiku" [standard]="sonnet" [advanced]="opus" [strong]="fable")
for tier in light standard advanced strong; do
  reset_stub
  feed 0 Frage | ask --target codex --tier "$tier" >/dev/null || fail "e/codex/$tier: Abbruch"
  expect_pair "e/codex/$tier" -m "${codex_want[$tier]}" codex
  expect_pair "e/codex/$tier" -c "model_reasoning_effort=\"${effort_want[$tier]}\"" codex
  feed 0 Frage | ask --target claude --tier "$tier" >/dev/null || fail "e/claude/$tier: Abbruch"
  expect_pair "e/claude/$tier" --model "${claude_want[$tier]}" claude
  expect_pair "e/claude/$tier" --effort "${effort_want[$tier]}" claude
done

log_info "(f) Katalogaufruf exakt 'debug models --bundled'"
if [[ ! -s "$STUB_LOG" ]]; then
  fail "f: codex debug models nie aufgerufen"
elif bad="$(grep -vxF 'debug models --bundled' "$STUB_LOG")"; then
  fail "f: abweichende Katalogaufrufe: $(tr '\n' ' ' <<<"$bad")"
fi

log_info "(g) Claude ask: keine git-Freigaben, schreibende git-Formen verboten"
reset_stub
feed 0 Frage | ask --target claude --mode ask >/dev/null || fail "g: Abbruch"
expect_pair g --permission-mode dontAsk claude
allow="$(args_after --allowedTools claude)"
[[ -z "$allow" ]] || fail "g: allow-Regeln im ask-Modus: $(tr '\n' ' ' <<<"$allow")"
deny="$(args_after --disallowedTools claude)"
for rule in Edit "Bash(git branch -d *)" "Bash(git branch -D *)" "Bash(git branch --delete *)" \
            "Bash(git branch -m *)" "Bash(git branch -M *)" "Bash(git branch -c *)" "Bash(git branch -C *)" \
            "Bash(git * --out*)"; do
  grep -qxF -- "$rule" <<<"$deny" || fail "g: deny-Regel '$rule' fehlt"
done
tools="$(args_after --tools claude)"
[[ "$(tr '\n' ' ' <<<"$tools")" == "Read Glob Grep Bash " ]] || fail "g: --tools ist '$(tr '\n' ' ' <<<"$tools")'"
# Der Prompt darf nicht hinter einer variadischen Option stehen, sonst wird er als Tool-Name gelesen.
expect_pair g -p "Bearbeite den Auftrag aus stdin. Nur lesen, keine Dateien ändern. Antworte auf Deutsch." claude

log_info "(h) Claude execute: push-Sperre auch mit Optionen vor dem Unterbefehl"
reset_stub
feed 0 Frage | ask --target claude --mode execute >/dev/null || fail "h: Abbruch"
expect_pair h --permission-mode acceptEdits claude
deny="$(args_after --disallowedTools claude)"
for rule in "Bash(git push *)" "Bash(git * push)" "Bash(git * push *)" WebFetch WebSearch; do
  grep -qxF -- "$rule" <<<"$deny" || fail "h: deny-Regel '$rule' fehlt"
done
expect_pair h -p "Bearbeite den Auftrag aus stdin. Änderungen nur im Workspace, kein Commit, kein Push. Antworte auf Deutsch und liste am Ende alle geänderten Dateien." claude

if [[ $FAILS -gt 0 ]]; then log_err "$FAILS Fehler"; exit 1; fi
log_ok "alle ask.sh-Tests grün"
