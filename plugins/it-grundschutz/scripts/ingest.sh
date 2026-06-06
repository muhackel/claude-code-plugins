#!/usr/bin/env bash
set -euo pipefail

# Grundschutz++ OSCAL-Katalog von der BSI-Stand-der-Technik-Bibliothek laden und lokal cachen.
# Quelle: BSI-Bund/Stand-der-Technik-Bibliothek (GitHub) — Lizenz CC BY-SA 4.0
# Der Korpus wird bewusst NICHT ins Plugin-Git eingecheckt (Lizenz-Trennung), sondern hier abgelegt.

RAW_URL="https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/main/Anwenderkataloge/Grundschutz%2B%2B/Grundschutz%2B%2B-catalog.json"
SRC_REPO="BSI-Bund/Stand-der-Technik-Bibliothek"
SRC_PATH="Anwenderkataloge/Grundschutz++/Grundschutz++-catalog.json"
LICENSE_ID="CC BY-SA 4.0"

GS_CORPUS_DIR="${GS_CORPUS_DIR:-$HOME/.local/share/it-grundschutz/corpus}"
DEST_DIR="$GS_CORPUS_DIR/grundschutz-pp"
CATALOG="$DEST_DIR/catalog.json"
MANIFEST="$DEST_DIR/manifest.json"

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

c_info=$'\e[34m'; c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*"; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*"; }
log_warn(){ printf '%s[!]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }

for tool in curl jq python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    log_err "$tool fehlt — in der Nix-Umgebung ausfuehren: 'nix run .#ingest' oder 'nix develop'."; exit 1; }
done

mkdir -p "$DEST_DIR"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

log_info "Lade Grundschutz++-Katalog von $SRC_REPO ..."
curl -fsSL "$RAW_URL" -o "$TMP" || { log_err "Download fehlgeschlagen."; exit 1; }

if ! jq -e '.catalog.metadata' "$TMP" >/dev/null 2>&1; then
  log_err "Antwort ist kein gueltiger OSCAL-Katalog (catalog.metadata fehlt)."; exit 1
fi
NEW_LM="$(jq -r '.catalog.metadata."last-modified" // .catalog.metadata.version // "unbekannt"' "$TMP")"

if [[ -f "$CATALOG" && "$FORCE" -eq 0 ]]; then
  OLD_LM="$(jq -r '.last_modified // "x"' "$MANIFEST" 2>/dev/null || echo x)"
  if [[ "$OLD_LM" == "$NEW_LM" ]]; then
    log_ok "Korpus aktuell (Stand $OLD_LM). Kein Update noetig — '--force' erzwingt."; exit 0
  fi
  log_info "Neuere Version verfuegbar: $OLD_LM -> $NEW_LM"
fi

if command -v sha256sum >/dev/null 2>&1; then SHA="$(sha256sum "$TMP" | cut -d' ' -f1)"
else SHA="$(shasum -a 256 "$TMP" | cut -d' ' -f1)"; fi

mv "$TMP" "$CATALOG"; trap - EXIT

NGROUPS="$(jq '[.catalog.groups[]?] | length' "$CATALOG")"
NCTRL="$(python3 - "$CATALOG" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
def c(n):
    t=len(n.get("controls",[]) or [])
    for g in n.get("groups",[]) or []: t+=c(g)
    return t
print(c(d["catalog"]))
PY
)"

ABG="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg repo "$SRC_REPO" --arg path "$SRC_PATH" --arg url "$RAW_URL" \
  --arg lm "$NEW_LM" --arg abg "$ABG" --arg sha "$SHA" --arg lic "$LICENSE_ID" \
  --argjson ngroups "$NGROUPS" --argjson nctrl "$NCTRL" \
  '{quelle:{repo:$repo,pfad:$path,raw_url:$url},edition:"grundschutz++",
    last_modified:$lm,abgerufen_am:$abg,sha256:$sha,lizenz:$lic,
    anzahl_schichten:$ngroups,anzahl_anforderungen:$nctrl}' > "$MANIFEST"

log_ok  "Korpus gespeichert: $CATALOG"
log_ok  "Schichten: $NGROUPS | Anforderungen: $NCTRL | Stand: $NEW_LM"
log_info "Manifest: $MANIFEST  (Lizenz: $LICENSE_ID)"
