#!/usr/bin/env bash
set -euo pipefail

# Grundschutz++ aus der BSI-Stand-der-Technik-Bibliothek (GitHub) laden und lokal cachen.
# Quelle: BSI-Bund/Stand-der-Technik-Bibliothek — Lizenz CC BY-SA 4.0
# Der Korpus wird bewusst NICHT ins Plugin-Git eingecheckt (Lizenz-Trennung), sondern hier abgelegt.
#
# Geladen werden vier Quellen:
#   anwender             Anwenderkatalog (konkrete Anforderungen)         -> catalog.json
#   methodik             Methodik-Quellkatalog (Vorgehensweise/das Warum)  -> methodik-catalog.json
#   profile              OSCAL-Profile (verknüpft Methodik <-> Anwender)   -> profile.json
#   zielobjektkategorien Namespace-CSV (Zielobjekte + Vererbung, STM)      -> target_object_categories.csv

BASE="https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/main"
SRC_REPO="BSI-Bund/Stand-der-Technik-Bibliothek"
LICENSE_ID="CC BY-SA 4.0"

# name | pfad-im-repo (roh, +-encodiert) | zieldatei | typ(catalog|profile)
SOURCES=(
  "anwender|Anwenderkataloge/Grundschutz%2B%2B/Grundschutz%2B%2B-catalog.json|catalog.json|catalog"
  "methodik|Quellkataloge/Methodik-Grundschutz%2B%2B/BSI-Methodik-Grundschutz%2B%2B-catalog.json|methodik-catalog.json|catalog"
  "profile|Quellkataloge/Methodik-Grundschutz%2B%2B/Grundschutz%2B%2B-profile.json|profile.json|profile"
  "zielobjektkategorien|Dokumentation/namespaces/target_object_categories.csv|target_object_categories.csv|csv"
)

GS_CORPUS_DIR="${GS_CORPUS_DIR:-$HOME/.local/share/it-grundschutz/corpus}"
DEST_DIR="$GS_CORPUS_DIR/grundschutz-pp"
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
    log_err "$tool fehlt — in der Nix-Umgebung ausführen: 'nix run .#ingest' oder 'nix develop'."; exit 1; }
done

sha256(){ if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
          else shasum -a 256 "$1" | cut -d' ' -f1; fi; }

mkdir -p "$DEST_DIR"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

changed=0
for entry in "${SOURCES[@]}"; do
  IFS='|' read -r name path dest typ <<<"$entry"
  url="$BASE/$path"
  out="$DEST_DIR/$dest"

  log_info "Lade '$name' ..."
  curl -fsSL "$url" -o "$TMP" || { log_err "Download '$name' fehlgeschlagen."; exit 1; }

  case "$typ" in
    catalog) jq -e '.catalog.metadata'  "$TMP" >/dev/null 2>&1 || { log_err "'$name' ist kein gültiger OSCAL-Katalog."; exit 1; } ;;
    profile) jq -e '.profile.metadata'  "$TMP" >/dev/null 2>&1 || { log_err "'$name' ist kein gültiges OSCAL-Profile."; exit 1; } ;;
    csv)     head -1 "$TMP" | grep -q 'Zielobjektkategorie' || { log_err "'$name' ist keine gültige Zielobjektkategorien-CSV."; exit 1; } ;;
  esac

  newsha="$(sha256 "$TMP")"
  oldsha="$(jq -r --arg n "$name" '.dateien[]? | select(.name==$n) | .sha256' "$MANIFEST" 2>/dev/null || true)"
  if [[ -f "$out" && "$FORCE" -eq 0 && "$newsha" == "$oldsha" ]]; then
    log_ok "'$name' unverändert (sha gleich) — übersprungen."
    continue
  fi
  cp "$TMP" "$out"
  changed=1
  log_ok "'$name' aktualisiert -> $dest"
done

# Manifest aus den finalen Dateien neu aufbauen
ABG="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$DEST_DIR" "$MANIFEST" "$SRC_REPO" "$LICENSE_ID" "$ABG" "${SOURCES[@]}" <<'PY'
import hashlib, json, os, sys
dest_dir, manifest, repo, lic, abg = sys.argv[1:6]
sources = sys.argv[6:]

def count_controls(node):
    t = len(node.get("controls", []) or [])
    for g in node.get("groups", []) or []:
        t += count_controls(g)
    return t

dateien = []
for entry in sources:
    name, path, fn, typ = entry.split("|")
    fp = os.path.join(dest_dir, fn)
    if not os.path.exists(fp):
        continue
    raw = open(fp, "rb").read()
    rec = {
        "name": name, "datei": fn, "typ": typ,
        "raw_url": f"https://raw.githubusercontent.com/{repo}/main/{path}",
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if typ == "csv":
        rec["titel"] = "Zielobjektkategorien (Namespace)"
        rec["anzahl_kategorien"] = max(0, len(raw.decode("utf-8").splitlines()) - 1)
    else:
        d = json.loads(raw.decode("utf-8"))
        root = d.get("catalog") or d.get("profile") or {}
        meta = root.get("metadata", {})
        rec["titel"] = meta.get("title")
        rec["last_modified"] = meta.get("last-modified") or meta.get("version")
        if typ == "catalog":
            rec["anzahl_anforderungen"] = count_controls(root)
    dateien.append(rec)

json.dump({"edition": "grundschutz++", "quelle_repo": repo, "lizenz": lic,
           "abgerufen_am": abg, "dateien": dateien},
          open(manifest, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
trap - EXIT; rm -f "$TMP"

[[ "$changed" -eq 0 ]] && log_info "Korpus war bereits aktuell ('--force' erzwingt Neuladen)."
log_ok "Manifest geschrieben: $MANIFEST  (Lizenz: $LICENSE_ID)"
jq -r '.dateien[] | "  \(.name): \(.titel // .datei)" + (if .anzahl_anforderungen then " (\(.anzahl_anforderungen) Anf., Stand \(.last_modified))" else "" end)' "$MANIFEST"
