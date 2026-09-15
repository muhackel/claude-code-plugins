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
{ printf '%s\n' "$shebang"; cat <<'EOT'; } >"$WORK/bin/codex"
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
 {"slug":"gpt-6-astra","visibility":"list","priority":1,"supported_reasoning_levels":[{"effort":"low"},{"effort":"medium"},{"effort":"high"},{"effort":"xhigh"},{"effort":"max"}]},
 {"slug":"gpt-5.6-sol","visibility":"list","priority":6,"supported_reasoning_levels":[{"effort":"low"},{"effort":"medium"},{"effort":"high"},{"effort":"xhigh"}]},
 {"slug":"gpt-5.6-luna","visibility":"list","priority":8,"supported_reasoning_levels":[{"effort":"medium"},{"effort":"high"}]},
 {"slug":"gpt-5.5","visibility":"list","priority":12,"supported_reasoning_levels":[{"effort":"medium"},{"effort":"high"}]},
 {"slug":"gpt-hidden","visibility":"hide","priority":0,"supported_reasoning_levels":[{"effort":"high"}]}
]}
JSON
    ;;
  esac
  exit 0
fi
printf '%s\n' "$@" >"$STUB_DIR/codex.argv"
cat >"$STUB_DIR/codex.stdin"
# Wie codex exec: Trajektorie auf stdout, letzte Nachricht in die Datei hinter -o (ohne Zeilenende).
printf 'codex-argv:'; printf ' %s' "$@"; printf '\n'
printf 'codex\nTrajektorie: Tool-Aufruf 1\n'
while [[ $# -gt 0 ]]; do
  if [[ "$1" == -o ]]; then printf 'LETZTE NACHRICHT\nZeile zwei' >"$2"; break; fi
  shift
done
exit "${STUB_EXIT:-0}"
EOT
{ printf '%s\n' "$shebang"; cat <<'EOT'; } >"$WORK/bin/claude"
printf '%s\n' "$@" >"$STUB_DIR/claude.argv"
cat >"$STUB_DIR/claude.stdin"
# Wie claude -p --output-format json: ein Ergebnisobjekt, die Antwort in .result.
if [[ "${STUB_CLAUDE_RAW:-}" == 1 ]]; then printf 'kein json\n'; exit "${STUB_EXIT:-0}"; fi
jq -n --arg r "claude-argv: $*" \
  '{type:"result",subtype:"success",is_error:false,result:$r,modelUsage:{"stub-claude-model":{}}}'
exit "${STUB_EXIT:-0}"
EOT
chmod +x "$WORK/bin/codex" "$WORK/bin/claude"

export PATH="$WORK/bin:$PATH" STUB_LOG="$WORK/stub.log" STUB_DIR="$WORK/stub"
unset CLAUDECODE CODEX_SANDBOX_NETWORK_DISABLED STUB_CATALOG STUB_DROP STUB_STRIP STUB_EXIT STUB_CLAUDE_RAW
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
    rc=0; out="$(feed_blocks | ask --target "$target" --mode "$mode")" || rc=$?
    [[ $rc -eq 0 ]] || fail "a/$target/$mode: Exit $rc"
    expect_not "a/$target/$mode" "Standard-Review" "$out"
    if [[ ! -e "$STUB_DIR/$target.stdin" ]]; then
      fail "a/$target/$mode: Stub nicht aufgerufen"
    elif ! cmp -s "$WORK/expected.stdin" "$STUB_DIR/$target.stdin"; then
      fail "a/$target/$mode: stdin beim Stub weicht ab: $(diff "$WORK/expected.stdin" "$STUB_DIR/$target.stdin" | tr '\n' ' ')"
    fi
  done
done

log_info "(b) </dev/null -> Standard-Review, Stufe advanced"
out="$(ask --target codex --dry-run </dev/null)"
expect_in b "Kein Handover -> Standard-Review" "$out"
expect_in b "Keine Stufe angegeben -> advanced" "$out"
expect_in b "gpt-5.6-sol" "$out"

log_info "(c) execute ohne Handover scheitert"
if out="$(ask --target codex --mode execute --dry-run </dev/null)"; then
  fail "c: Exit 0 statt Fehler"
fi
expect_in c "braucht ein Handover" "$out"

log_info "(d) Rückfallkette mit tatsächlichem argv, Warnung und Exit-Code"
# Fall | Katalog | DROP | STRIP | Modus | Stufe + Zusatzflags | erwartetes Modell (leer = ohne -m) | Effort | Meldung
cases=(
  "fail|fail|||ask|--tier advanced|||codex debug models fehlgeschlagen"
  "broken|broken|||ask|--tier advanced|||nicht lesbar"
  "nomodels|nomodels|||ask|--tier advanced|||nicht lesbar"
  "leer|empty|||ask|--tier advanced|||'gpt-5.6-sol' (effort high) nicht im Katalog"
  "ohne-luna|ok|gpt-5.6-luna||execute|--tier drone|gpt-5.6-sol|high|'gpt-5.6-luna' (effort high) fehlt im Katalog"
  "luna-ohne-high|ok||gpt-5.6-luna:high|execute|--tier drone|gpt-5.6-sol|high|'gpt-5.6-luna' (effort high) fehlt im Katalog"
  "luna-und-sol-ohne-high|ok||gpt-5.6-luna:high gpt-5.6-sol:high|execute|--tier drone|||weder 'gpt-5.6-luna' noch 'gpt-5.6-sol'"
  "sol-ohne-xhigh|ok||gpt-5.6-sol:xhigh|ask|--tier advanced --boost|||'gpt-5.6-sol' (effort xhigh) nicht im Katalog"
  "astra-ohne-low|ok||gpt-6-astra:low|ask|--tier strong --fast|gpt-5.6-sol|low|'gpt-6-astra' (effort low) fehlt im Katalog"
  "ohne-astra|ok|gpt-6-astra||ask|--tier strong|gpt-5.6-sol|medium|Stufe strong -> gpt-5.6-sol (effort medium)"
  "model-ungeprueft|fail|||ask|--model gpt-5.5|gpt-5.5|high|--model gpt-5.5 (effort high) ungeprüft übernommen"
  "model-katalog-kaputt|broken|||ask|--model gpt-5.5|gpt-5.5|high|--model gpt-5.5 (effort high) ungeprüft übernommen"
  "model-nomodels|nomodels|||ask|--model gpt-5.5|gpt-5.5|high|--model gpt-5.5 (effort high) ungeprüft übernommen"
)
for c in "${cases[@]}"; do
  IFS='|' read -r name catalog drop strip mode flags model effort msg <<<"$c"
  reset_stub
  rc=0
  # shellcheck disable=SC2086  # flags sind bewusst mehrere Argumente
  out="$(feed 0 Frage | STUB_CATALOG="$catalog" STUB_DROP="$drop" STUB_STRIP="$strip" \
         ask --target codex --mode "$mode" $flags)" || rc=$?
  [[ $rc -eq 0 ]] || fail "d/$name: Exit $rc"
  expect_in "d/$name" "$msg" "$out"
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
rc=0; out="$(feed 0 Frage | STUB_EXIT=7 ask --target codex)" || rc=$?
[[ $rc -eq 7 ]] || fail "d/exit: Exit-Code der CLI nicht durchgereicht ($rc statt 7)"
expect_in d/exit "beendet mit Exit 7" "$out"

log_info "(e) Modell und Effort je Stufe, Boost, Fast, freie Wahl"
# Fall | Modus | Flags | Claude-Modell | Codex-Modell | Effort | Label
cases=(
  "drone|execute|--tier drone|sonnet|gpt-5.6-luna|high|/execute drone proj"
  "advanced|ask|--tier advanced|opus|gpt-5.6-sol|high|/ask advanced proj"
  "advanced-boost|ask|--tier advanced --boost|opus|gpt-5.6-sol|xhigh|/ask advanced+ proj"
  "strong|ask|--tier strong|fable|gpt-6-astra|medium|/ask strong proj"
  "strong-boost|ask|--tier strong --boost|fable|gpt-6-astra|high|/ask strong+ proj"
  "strong-fast|execute|--tier strong --fast|fable|gpt-6-astra|low|/execute strong- proj"
  "default|execute||opus|gpt-5.6-sol|high|/execute advanced proj"
  "effort|ask|--tier strong --effort max|fable|gpt-6-astra|max|/ask strong proj"
  "effort-nach-boost|ask|--tier advanced --boost --effort low|opus|gpt-5.6-sol|low|/ask advanced+ proj"
  "model|ask|--model gpt-5.5|gpt-5.5|gpt-5.5|high|/ask gpt-5.5 proj"
  "model-effort|ask|--model gpt-5.5 --effort medium|gpt-5.5|gpt-5.5|medium|/ask gpt-5.5 proj"
  "model-versteckt|ask|--model gpt-hidden|gpt-hidden|gpt-hidden|high|/ask gpt-hidden proj"
)
for c in "${cases[@]}"; do
  IFS='|' read -r name mode flags claude_model codex_model effort label <<<"$c"
  reset_stub
  # shellcheck disable=SC2086
  feed 0 Frage | ask --target codex --mode "$mode" $flags >/dev/null || fail "e/codex/$name: Abbruch"
  expect_pair "e/codex/$name" -m "$codex_model" codex
  expect_pair "e/codex/$name" -c "model_reasoning_effort=\"$effort\"" codex
  grep -qF -- "[$label]" "$STUB_DIR/codex.argv" || fail "e/codex/$name: Label '[$label]' fehlt"
  # shellcheck disable=SC2086
  feed 0 Frage | ask --target claude --mode "$mode" $flags >/dev/null || fail "e/claude/$name: Abbruch"
  expect_pair "e/claude/$name" --model "$claude_model" claude
  expect_pair "e/claude/$name" --effort "$effort" claude
  expect_pair "e/claude/$name" --name "$label" claude
done

log_info "(e2) unzulässige Kombinationen scheitern vor dem Aufruf"
# Fall | Ziel | Modus | Flags | Meldung
cases=(
  "drone-ask|codex|ask|--tier drone|drone gibt es nur bei --mode execute"
  "boost-fast|codex|ask|--boost --fast|schließen sich aus"
  "fast-advanced|codex|ask|--tier advanced --fast|--fast gibt es nur bei strong"
  "boost-drone|codex|execute|--tier drone --boost|--boost gibt es nicht bei drone"
  "model-boost|codex|ask|--model gpt-5.5 --boost|--model kennt keine Stufe"
  "model-tier|codex|ask|--tier strong --model gpt-5.5|--model kennt keine Stufe"
  "model-ohne-wert|codex|ask|--model --boost|--model braucht einen Wert"
  "tier-leer|codex|ask|--tier |--tier braucht einen Wert"
  "tier-light|codex|ask|--tier light|--tier muss strong, advanced oder drone sein"
  "effort-ultra|codex|ask|--effort ultra|--effort muss low, medium, high, xhigh oder max sein"
  "model-unbekannt|codex|ask|--model gpt-4|--model 'gpt-4' (effort high) fehlt im Katalog"
  "model-ohne-effort|codex|ask|--model gpt-5.5 --effort xhigh|--model 'gpt-5.5' (effort xhigh) fehlt im Katalog"
)
for c in "${cases[@]}"; do
  IFS='|' read -r name target mode flags msg <<<"$c"
  reset_stub
  rc=0
  # shellcheck disable=SC2086
  out="$(feed 0 Frage | ask --target "$target" --mode "$mode" $flags)" || rc=$?
  [[ $rc -ne 0 ]] || fail "e2/$name: Exit 0 statt Fehler"
  expect_in "e2/$name" "$msg" "$out"
  [[ ! -e "$STUB_DIR/$target.argv" ]] || fail "e2/$name: CLI trotz Fehler aufgerufen"
done

log_info "(e3) Dry-Run liest höchstens den Katalog, startet aber keinen Auftrag"
reset_stub
feed 0 Frage | ask --target codex --dry-run --tier strong >/dev/null || fail "e3/codex: Abbruch"
[[ ! -e "$STUB_DIR/codex.argv" ]] || fail "e3/codex: codex exec trotz --dry-run aufgerufen"
feed 0 Frage | ask --target claude --dry-run --tier strong >/dev/null || fail "e3/claude: Abbruch"
[[ ! -e "$STUB_DIR/claude.argv" ]] || fail "e3/claude: claude trotz --dry-run aufgerufen"

log_info "(e4) Codex: stdout ist nur die letzte Nachricht, Trajektorie geht nach stderr"
reset_stub
rc=0; out_stdout="$(feed 0 Frage | bash "$ASK" -C "$WORK/proj" --target codex 2>"$WORK/e4.stderr")" || rc=$?
[[ $rc -eq 0 ]] || fail "e4: Exit $rc"
[[ "$out_stdout" == $'LETZTE NACHRICHT\nZeile zwei' ]] || fail "e4: stdout ist '$out_stdout'"
grep -qF 'Trajektorie: Tool-Aufruf 1' "$WORK/e4.stderr" || fail "e4: Trajektorie fehlt auf stderr"
last_file="$(awk 'p { print; exit } $0 == "-o" { p = 1 }' "$STUB_DIR/codex.argv")"
[[ -n "$last_file" ]] || fail "e4: -o FILE fehlt im argv"
[[ ! -e "$last_file" ]] || fail "e4: Temp-Datei '$last_file' nicht aufgeräumt"

log_info "(e5) Claude: stdout ist .result, Modell-ID aus .modelUsage auf stderr, Rohausgabe bei kaputtem JSON"
reset_stub
rc=0; out_stdout="$(feed 0 Frage | bash "$ASK" -C "$WORK/proj" --target claude 2>"$WORK/e5.stderr")" || rc=$?
[[ $rc -eq 0 ]] || fail "e5: Exit $rc"
[[ "$out_stdout" == claude-argv:* ]] || fail "e5: stdout ist nicht .result: '$out_stdout'"
[[ "$out_stdout" != *modelUsage* ]] || fail "e5: rohes JSON auf stdout"
grep -qF 'Modell laut claude: stub-claude-model (effort per Flag: high)' "$WORK/e5.stderr" || fail "e5: Modellnachweis fehlt auf stderr"
expect_pair e5 --output-format json claude
last_file="$(awk 'p { print; exit } $0 == "-o" { p = 1 }' "$STUB_DIR/claude.argv")"
[[ -z "$last_file" ]] || fail "e5: -o gehört nicht in den claude-Aufruf"
reset_stub
rc=0; out_stdout="$(feed 0 Frage | STUB_CLAUDE_RAW=1 bash "$ASK" -C "$WORK/proj" --target claude 2>"$WORK/e5b.stderr")" || rc=$?
[[ "$out_stdout" == "kein json" ]] || fail "e5/raw: Rohausgabe nicht durchgereicht: '$out_stdout'"
grep -qF 'kein Ergebnis-JSON' "$WORK/e5b.stderr" || fail "e5/raw: Warnung fehlt"

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
