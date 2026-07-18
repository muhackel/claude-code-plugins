#!/usr/bin/env bash
set -euo pipefail

# Karin — offizielle Diagramm-Doku (Mermaid + PlantUML) offline vorhalten.
# Der Cache liegt bewusst AUSSERHALB des Git-Repos (XDG) und wird nie eingecheckt.
#
# Zwei Quellen:
#   mermaid   Mermaid-Doku (Markdown) aus dem Upstream-Git — sparse/partial clone
#   plantuml  plantuml.com (wget-Mirror der Diagrammtyp-Seiten) + Language Reference Guide (PDF -> Text)
#
# Kernmechanismus: Altersgate. Ohne Flags wird eine Quelle nur neu gezogen,
# wenn ihr Manifest-Zeitstempel älter als MAX_AGE_DAYS ist (oder fehlt).

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
DIAGRAM_DOCS_DIR="${DIAGRAM_DOCS_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bibliothekarin/diagram-docs}"

MERMAID_DIR="$DIAGRAM_DOCS_DIR/mermaid"
PLANTUML_DIR="$DIAGRAM_DOCS_DIR/plantuml"

MERMAID_REPO="https://github.com/mermaid-js/mermaid"
MERMAID_SPARSE_PATH="packages/mermaid/src/docs"

PLANTUML_SITE="https://plantuml.com"
PLANTUML_GUIDE_URL="https://pdf.plantuml.net/PlantUML_Language_Reference_Guide_en.pdf"
PLANTUML_GUIDE_TXT="PlantUML_Language_Reference_Guide_en.txt"

MAX_AGE_DAYS=14
MAX_AGE_SECS=$(( MAX_AGE_DAYS * 24 * 60 * 60 ))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
c_info=$'\e[34m'; c_ok=$'\e[32m'; c_warn=$'\e[33m'; c_err=$'\e[31m'; c_off=$'\e[0m'
log_info(){ printf '%s[*]%s %s\n' "$c_info" "$c_off" "$*"; }
log_ok(){   printf '%s[+]%s %s\n' "$c_ok"   "$c_off" "$*"; }
log_warn(){ printf '%s[!]%s %s\n' "$c_warn" "$c_off" "$*" >&2; }
log_err(){  printf '%s[x]%s %s\n' "$c_err"  "$c_off" "$*" >&2; }

# ---------------------------------------------------------------------------
# Hilfe
# ---------------------------------------------------------------------------
usage(){
  cat <<EOF
fetch-diagram-docs.sh — offizielle Diagramm-Doku (Mermaid + PlantUML) offline vorhalten.

Verwendung:
  fetch-diagram-docs.sh [OPTIONEN] [QUELLE]

QUELLE (optional, sonst beide):
  mermaid           nur die Mermaid-Doku behandeln
  plantuml          nur die PlantUML-Doku behandeln

OPTIONEN:
  -f, --force       Altersgate ignorieren, Quelle(n) immer neu ziehen
  -s, --status      pro Quelle Pfad + Alter + Zustand zeigen, nichts ziehen
  -h, --help        diese Hilfe

Altersgate: ohne Flags wird eine Quelle nur neu gezogen, wenn ihre Doku
älter als $MAX_AGE_DAYS Tage ist (oder fehlt). Sonst wird sie übersprungen.

Cache-Verzeichnis (außerhalb des Repos, nicht getrackt):
  \$DIAGRAM_DOCS_DIR (default ~/.local/share/bibliothekarin/diagram-docs)
EOF
}

# ---------------------------------------------------------------------------
# Argumente
# ---------------------------------------------------------------------------
FORCE=0
STATUS=0
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--force)  FORCE=1 ;;
    -s|--status) STATUS=1 ;;
    -h|--help)   usage; exit 0 ;;
    mermaid|plantuml)
      if [[ -n "$ONLY" ]]; then log_err "Nur eine Quelle angeben (mermaid ODER plantuml)."; exit 2; fi
      ONLY="$1" ;;
    *) log_err "Unbekanntes Argument: '$1' (siehe --help)."; exit 2 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Tool-Checks (defensiv)
# ---------------------------------------------------------------------------
need_tools(){
  local missing=()
  local t
  for t in "$@"; do
    command -v "$t" >/dev/null 2>&1 || missing+=("$t")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    log_err "Fehlende Tools: ${missing[*]} — in der Nix-Umgebung ausführen: 'nix run .#fetch-docs' oder 'nix develop'."
    return 1
  fi
  return 0
}

# jq wird immer gebraucht (Manifest). Die übrigen je nach Quelle.
need_tools jq date || exit 1

# ---------------------------------------------------------------------------
# Manifest-Helfer
# ---------------------------------------------------------------------------
manifest_path(){ printf '%s/%s/manifest.json' "$DIAGRAM_DOCS_DIR" "$1"; }

# Liest abgerufen_am (Unix-Epoch) aus dem Manifest einer Quelle; leer wenn nicht vorhanden.
manifest_epoch(){
  local m; m="$(manifest_path "$1")"
  [[ -f "$m" ]] || { printf ''; return 0; }
  jq -r '.abgerufen_am // empty' "$m" 2>/dev/null || printf ''
}

# Schreibt/aktualisiert das Manifest einer Quelle atomar.
write_manifest(){
  local src="$1" quelle="$2"
  local dir="$DIAGRAM_DOCS_DIR/$src"
  local m; m="$(manifest_path "$src")"
  local now iso tmp
  now="$(date +%s)"
  iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$dir"
  tmp="$(mktemp)"
  jq -n \
    --arg quelle "$quelle" \
    --argjson abgerufen_am "$now" \
    --arg abgerufen_am_iso "$iso" \
    '{quelle: $quelle, abgerufen_am: $abgerufen_am, abgerufen_am_iso: $abgerufen_am_iso}' \
    >"$tmp"
  mv "$tmp" "$m"
  log_ok "Manifest geschrieben: $m (Stand $iso)"
}

# Zustand einer Quelle ermitteln. Setzt die Globals STATE ("fehlt"|"fällig"|"aktuell")
# und AGE_DAYS (Alter in Tagen bzw. leer, wenn keine Doku vorhanden).
# Bewusst über Globals statt stdout, damit die Werte den Aufrufer erreichen
# (Command-Substitution liefe in einer Subshell und verwürfe AGE_DAYS).
STATE=""
AGE_DAYS=""
source_state(){
  local src="$1"
  local dir="$DIAGRAM_DOCS_DIR/$src"
  local epoch; epoch="$(manifest_epoch "$src")"
  AGE_DAYS=""
  if [[ ! -d "$dir" || -z "$epoch" ]]; then
    STATE="fehlt"; return 0
  fi
  local now age
  now="$(date +%s)"
  age=$(( now - epoch ))
  AGE_DAYS=$(( age / 86400 ))
  if [[ "$age" -ge "$MAX_AGE_SECS" ]]; then
    STATE="fällig"
  else
    STATE="aktuell"
  fi
}

# Entscheidet, ob eine Quelle gezogen werden soll. 0 = ziehen, 1 = überspringen.
should_fetch(){
  local src="$1"
  if [[ "$FORCE" -eq 1 ]]; then
    return 0
  fi
  source_state "$src"
  case "$STATE" in
    fehlt)   log_info "$src: keine Doku vorhanden — wird gezogen."; return 0 ;;
    fällig) log_info "$src: fällig (${AGE_DAYS} Tage alt, >= ${MAX_AGE_DAYS}) — wird gezogen."; return 0 ;;
    aktuell) log_ok   "$src: aktuell (${AGE_DAYS} Tage alt) — übersprungen."; return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# Quelle: Mermaid (sparse/partial git clone)
# ---------------------------------------------------------------------------
fetch_mermaid(){
  need_tools git || return 1
  local repo_dir="$MERMAID_DIR/repo"

  if [[ -d "$repo_dir/.git" ]]; then
    log_info "Mermaid: vorhandenes Repo — pull ..."
    if ! git -C "$repo_dir" pull --ff-only >/dev/null 2>&1; then
      log_err "Mermaid: 'git pull' fehlgeschlagen."
      return 1
    fi
  else
    log_info "Mermaid: partial/sparse clone von $MERMAID_REPO ..."
    rm -rf "$repo_dir"
    mkdir -p "$MERMAID_DIR"
    if ! git clone --filter=blob:none --no-checkout --depth 1 "$MERMAID_REPO" "$repo_dir" >/dev/null 2>&1; then
      log_err "Mermaid: 'git clone' fehlgeschlagen."
      return 1
    fi
    if ! git -C "$repo_dir" sparse-checkout set --no-cone "$MERMAID_SPARSE_PATH" >/dev/null 2>&1; then
      log_err "Mermaid: 'sparse-checkout set' fehlgeschlagen."
      return 1
    fi
    if ! git -C "$repo_dir" checkout >/dev/null 2>&1; then
      log_err "Mermaid: 'git checkout' fehlgeschlagen."
      return 1
    fi
  fi

  if [[ ! -d "$repo_dir/$MERMAID_SPARSE_PATH" ]]; then
    log_err "Mermaid: erwarteter Doku-Pfad fehlt: $MERMAID_SPARSE_PATH"
    return 1
  fi

  write_manifest mermaid "$MERMAID_REPO (Pfad: $MERMAID_SPARSE_PATH)"
  log_ok "Mermaid-Doku bereit: $repo_dir/$MERMAID_SPARSE_PATH"
  return 0
}

# ---------------------------------------------------------------------------
# Quelle: PlantUML (Website-Mirror + Language Reference Guide PDF -> Text)
# ---------------------------------------------------------------------------
fetch_plantuml(){
  need_tools wget pdftotext || return 1
  local site_dir="$PLANTUML_DIR/site"
  local rc=0

  mkdir -p "$PLANTUML_DIR" "$site_dir"

  # 1) Website-Mirror: die englischen Diagrammseiten von plantuml.com — als schnelle,
  # durchsuchbare HTML-Landeseiten. Bewusst schlank gehalten:
  #   * Tiefe 1 (Index + direkt verlinkte Seiten) statt tiefem Fan-out,
  #   * KEINE --page-requisites (Karin grept den Text, Bilder/CSS sind unnötiger Ballast),
  #   * Sprach-/Dark-Theme-Ordner (de/, en/, fr/, *-dark/ …) per --reject-regex raus.
  # Die vollständige Referenz liefert ohnehin das PDF (Schritt 2) — die Website ist der
  # schnelle Einstieg, nicht die Tiefenquelle.
  log_info "PlantUML: Website-Mirror von $PLANTUML_SITE (Diagrammseiten, Tiefe 1, ohne Assets) ..."
  if wget \
      --recursive \
      --level=1 \
      --no-parent \
      --domains=plantuml.com \
      --span-hosts=off \
      --regex-type=posix \
      --reject-regex='plantuml\.com/([a-z]{2}(-[a-z]{2})?)(-dark)?/' \
      --convert-links \
      --adjust-extension \
      --timeout=30 \
      --tries=3 \
      --no-verbose \
      --directory-prefix="$site_dir" \
      "$PLANTUML_SITE/" 2>&1 | tail -n 3; then
    log_ok "PlantUML: Website-Mirror abgelegt unter $site_dir"
  else
    # wget liefert oft Exitcode 8 (Server-Fehlerantworten auf einzelne Assets), obwohl der
    # Mirror brauchbar ist. Nur hart scheitern, wenn gar nichts ankam.
    if [[ -n "$(find "$site_dir" -name '*.html' -print -quit 2>/dev/null)" ]]; then
      log_warn "PlantUML: wget meldete Fehler auf einzelne Ressourcen — Mirror ist aber befüllt."
    else
      log_err "PlantUML: Website-Mirror fehlgeschlagen (keine HTML-Seiten geladen)."
      rc=1
    fi
  fi

  # 2) Language Reference Guide (PDF -> durchsuchbarer Text), atomar
  log_info "PlantUML: Language Reference Guide laden ..."
  local pdf_tmp txt_tmp
  pdf_tmp="$PLANTUML_DIR/guide.pdf.tmp"
  if wget --timeout=60 --tries=3 --no-verbose -O "$pdf_tmp" "$PLANTUML_GUIDE_URL"; then
    mv "$pdf_tmp" "$PLANTUML_DIR/guide.pdf"
    log_ok "PlantUML: guide.pdf geladen."
    txt_tmp="$PLANTUML_DIR/$PLANTUML_GUIDE_TXT.tmp"
    if pdftotext -layout "$PLANTUML_DIR/guide.pdf" "$txt_tmp" 2>/dev/null; then
      mv "$txt_tmp" "$PLANTUML_DIR/$PLANTUML_GUIDE_TXT"
      log_ok "PlantUML: Reference Guide als Text: $PLANTUML_DIR/$PLANTUML_GUIDE_TXT"
    else
      rm -f "$txt_tmp"
      log_err "PlantUML: pdftotext-Konvertierung fehlgeschlagen."
      rc=1
    fi
  else
    rm -f "$pdf_tmp"
    log_err "PlantUML: Download des Reference Guide fehlgeschlagen."
    rc=1
  fi

  if [[ "$rc" -eq 0 ]]; then
    write_manifest plantuml "$PLANTUML_SITE + $PLANTUML_GUIDE_URL"
    log_ok "PlantUML-Doku bereit: $PLANTUML_DIR"
  fi
  return "$rc"
}

# ---------------------------------------------------------------------------
# --status
# ---------------------------------------------------------------------------
print_status(){
  local src age_txt path
  printf '\n%sDiagramm-Doku — Status%s (Cache: %s)\n' "$c_info" "$c_off" "$DIAGRAM_DOCS_DIR"
  for src in mermaid plantuml; do
    [[ -n "$ONLY" && "$ONLY" != "$src" ]] && continue
    source_state "$src"
    path="$DIAGRAM_DOCS_DIR/$src"
    case "$STATE" in
      fehlt)   age_txt="—" ;;
      *)       age_txt="${AGE_DAYS} Tage" ;;
    esac
    printf '  %-10s %-8s Alter: %-10s %s\n' "$src" "$STATE" "$age_txt" "$path"
  done
  printf '\n  Altersgate: %s Tage. fehlt/fällig -> wird gezogen, aktuell -> übersprungen (außer --force).\n\n' "$MAX_AGE_DAYS"
}

# ---------------------------------------------------------------------------
# Ablauf
# ---------------------------------------------------------------------------
mkdir -p "$DIAGRAM_DOCS_DIR"

if [[ "$STATUS" -eq 1 ]]; then
  print_status
  exit 0
fi

overall_rc=0
run_source(){
  local src="$1" fn="$2"
  [[ -n "$ONLY" && "$ONLY" != "$src" ]] && return 0
  if should_fetch "$src"; then
    if ! "$fn"; then
      log_err "$src: Beschaffung fehlgeschlagen."
      overall_rc=1
    fi
  fi
  return 0
}

run_source mermaid  fetch_mermaid
run_source plantuml fetch_plantuml

if [[ "$overall_rc" -ne 0 ]]; then
  log_err "Mindestens eine Quelle ist fehlgeschlagen."
  exit 1
fi

log_ok "Fertig. Offline-Doku unter $DIAGRAM_DOCS_DIR"
exit 0
