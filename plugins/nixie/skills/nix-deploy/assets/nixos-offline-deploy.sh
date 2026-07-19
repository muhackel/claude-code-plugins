#!/usr/bin/env bash
# Generischer Offline-Closure-Deploy (TUI) für NixOS.
#
# Auf dem ZIEL-Rechner ausführen. Liest im eigenen Verzeichnis nach Closure-Archiven
# (<name>.nar.zst) samt Sidecar-Manifest (<name>.manifest, s. nixos-offline-export.sh),
# gruppiert sie nach Hostname und führt durch:
#   1) Host wählen        (Default = aktiver Hostname; fremder Host -> Warnung)
#   2) Closure wählen      (nach Build-Datum; bereits installierte mit * markiert)
#   3) Aktion wählen       (switch | boot | test | dry-activate)
#   4) Bestätigen -> sha256 prüfen -> importieren -> Profil setzen -> aktivieren
#
#   ./nixos-offline-deploy.sh          # kein vorangestelltes sudo nötig
#
# Die TUI-Auswahl läuft als normaler User; nur die privilegierten Schritte (Import, Profil,
# switch-to-configuration) eskalieren intern via sudo (wie 'nixos-rebuild --sudo'). Als root
# gestartet läuft alles direkt. TUI via gum (neben dem Skript oder im PATH und ausführbar),
# sonst Plain-Bash-Fallback.
set -euo pipefail

C_INFO='\033[1;34m'; C_OK='\033[1;32m'; C_WARN='\033[1;33m'; C_ERR='\033[1;31m'; C_DIM='\033[2m'; C_RST='\033[0m'
log_info(){ echo -e "${C_INFO}[*]${C_RST} $*"; }
log_ok(){   echo -e "${C_OK}[+]${C_RST} $*"; }
log_warn(){ echo -e "${C_WARN}[!]${C_RST} $*"; }
log_err(){  echo -e "${C_ERR}[x]${C_RST} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# UI-Abstraktion: gum wenn nutzbar, sonst Plain-Bash. Nie Abbruch wegen fehlendem gum.
# ---------------------------------------------------------------------------
GUM=""
resolve_gum(){
  local cand
  for cand in "$SCRIPT_DIR/gum" "$(command -v gum 2>/dev/null || true)"; do
    [[ -n "$cand" && -x "$cand" ]] || continue
    if "$cand" --version >/dev/null 2>&1; then GUM="$cand"; return; fi
  done
}
resolve_gum

# ui_choose HEADER DEFAULT ITEM...   -> gewähltes ITEM auf stdout
ui_choose(){
  local header="$1" def="$2"; shift 2
  if [[ -n "$GUM" ]]; then
    "$GUM" choose --header "$header" --selected "$def" "$@"
    return
  fi
  local i=1 idx choice
  echo -e "${C_INFO}$header${C_RST}" >&2
  for choice in "$@"; do
    if [[ "$choice" == "$def" ]]; then
      echo -e "  ${C_OK}$i)${C_RST} $choice ${C_DIM}(Default)${C_RST}" >&2
    else
      echo -e "  $i) $choice" >&2
    fi
    i=$((i+1))
  done
  local defnum=1 j=1
  for choice in "$@"; do [[ "$choice" == "$def" ]] && defnum=$j; j=$((j+1)); done
  read -rp "Auswahl [$defnum]: " idx >&2 || true
  idx="${idx:-$defnum}"
  if [[ ! "$idx" =~ ^[0-9]+$ ]] || (( idx<1 || idx>$# )); then
    log_err "Ungültige Auswahl."; return 1
  fi
  printf '%s\n' "${@:$idx:1}"
}

# ui_confirm PROMPT  -> exit 0 = ja, 1 = nein  (Default = nein)
ui_confirm(){
  local prompt="$1"
  if [[ -n "$GUM" ]]; then "$GUM" confirm --default=false "$prompt"; return; fi
  local ans
  read -rp "$(echo -e "${C_WARN}${prompt}${C_RST} [j/N]: ")" ans >&2 || true
  [[ "$ans" =~ ^[jJyY]$ ]]
}

# ui_note TEXT  -> hervorgehobener Hinweisblock
ui_note(){
  if [[ -n "$GUM" ]]; then "$GUM" style --border rounded --padding "0 1" --border-foreground 214 "$1"; return; fi
  echo -e "${C_WARN}$1${C_RST}"
}

# ---------------------------------------------------------------------------
# Vorbedingungen
# ---------------------------------------------------------------------------
for bin in zstd nix-store nix-env sha256sum; do
  command -v "$bin" >/dev/null 2>&1 || { log_err "'$bin' nicht im PATH."; exit 1; }
done
# Privilegierte Schritte (Import/Profil/Aktivierung) via sudo eskalieren. Als root direkt.
if [[ $EUID -eq 0 ]]; then
  SUDO=()
else
  command -v sudo >/dev/null 2>&1 || { log_err "Nicht root und kein sudo verfügbar — als root starten."; exit 1; }
  SUDO=(sudo)
fi

# ---------------------------------------------------------------------------
# Manifeste einlesen (parallele Arrays)
# ---------------------------------------------------------------------------
declare -a M_HOST M_TOPLEVEL M_ARCHIVE M_DATE M_REV M_VERSION M_SHA M_MANIFEST M_INSTALLED M_ACTIVE
read_manifests(){
  local f host toplevel archive date rev version sha line key val
  shopt -s nullglob
  for f in "$SCRIPT_DIR"/*.manifest; do
    host="" toplevel="" archive="" date="" rev="" version="" sha=""
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      [[ "$line" == *=* ]] || continue
      key="${line%%=*}"; val="${line#*=}"
      case "$key" in
        host)     host="$val" ;;
        toplevel) toplevel="$val" ;;
        archive)  archive="$val" ;;
        date)     date="$val" ;;
        rev)      rev="$val" ;;
        version)  version="$val" ;;
        sha256)   sha="$val" ;;
      esac
    done < "$f"
    [[ -n "$host" && -n "$toplevel" && -n "$archive" ]] || { log_warn "Manifest unvollständig, übersprungen: $(basename "$f")"; continue; }
    if [[ ! -f "$SCRIPT_DIR/$archive" ]]; then
      log_warn "Archiv fehlt zu $(basename "$f"): $archive — übersprungen."; continue
    fi
    M_HOST+=("$host"); M_TOPLEVEL+=("$toplevel"); M_ARCHIVE+=("$archive")
    M_DATE+=("${date:-0000-00-00}"); M_REV+=("${rev:--}"); M_VERSION+=("${version:--}")
    M_SHA+=("$sha"); M_MANIFEST+=("$f"); M_INSTALLED+=("0"); M_ACTIVE+=("0")
  done
  shopt -u nullglob
}
read_manifests
[[ ${#M_TOPLEVEL[@]} -gt 0 ]] || { log_err "Keine gültigen Closure-Manifeste in $SCRIPT_DIR gefunden."; exit 1; }

# Installierte Toplevels ermitteln (Store-Pfade der System-Generationen + aktuell aktiver)
mark_installed(){
  local -a gens=(); local g rp active="" i
  shopt -s nullglob
  for g in /nix/var/nix/profiles/system-*-link; do gens+=("$(readlink -f "$g")"); done
  shopt -u nullglob
  [[ -e /run/current-system ]] && active="$(readlink -f /run/current-system)"
  for i in "${!M_TOPLEVEL[@]}"; do
    for rp in "${gens[@]}"; do [[ "$rp" == "${M_TOPLEVEL[$i]}" ]] && M_INSTALLED[i]=1; done
    [[ -n "$active" && "$active" == "${M_TOPLEVEL[$i]}" ]] && M_ACTIVE[i]=1
  done
  return 0   # letzte [[..]]&& darf die Funktion nicht mit Exit 1 verlassen (set -e)
}
mark_installed

# ---------------------------------------------------------------------------
# 1) Host wählen
# ---------------------------------------------------------------------------
declare -a HOSTS=()
for h in "${M_HOST[@]}"; do
  seen=0; for e in "${HOSTS[@]:-}"; do [[ "$e" == "$h" ]] && seen=1; done
  [[ "$seen" == 0 ]] && HOSTS+=("$h")
done

ACTIVE_HOST="$(hostname 2>/dev/null || echo unknown)"
DEFAULT_HOST="${HOSTS[0]}"
for h in "${HOSTS[@]}"; do
  # case-insensitiver Abgleich (networking.hostName vs. `hostname`)
  [[ "${h,,}" == "${ACTIVE_HOST,,}" ]] && DEFAULT_HOST="$h"
done

log_info "Aktiver Host: ${ACTIVE_HOST}    Closures für: ${HOSTS[*]}"
CHOSEN_HOST="$(ui_choose "Für welchen Host deployen?" "$DEFAULT_HOST" "${HOSTS[@]}")" || exit 1

if [[ "${CHOSEN_HOST,,}" != "${ACTIVE_HOST,,}" ]]; then
  ui_note "FREMDE HOST-CONFIG: '${CHOSEN_HOST}' != aktiver Host '${ACTIVE_HOST}'.
Die Hardware-Konfiguration (Disks, Bootloader, Treiber) kann NICHT passen.
OK bei einer bewussten Neuinstallation auf diese Hardware — sonst bootet das
System evtl. nicht. Bootloader/Disk-Layout des Ziels müssen zur Config passen."
  ui_confirm "Trotzdem mit Host '${CHOSEN_HOST}' fortfahren?" || { log_warn "Abgebrochen."; exit 0; }
fi

# ---------------------------------------------------------------------------
# 2) Closure wählen (Kandidaten des Hosts, nach Datum absteigend)
# ---------------------------------------------------------------------------
declare -a IDX=()
for i in "${!M_HOST[@]}"; do [[ "${M_HOST[$i]}" == "$CHOSEN_HOST" ]] && IDX+=("$i"); done
# nach Datum absteigend sortieren (Index-Liste über die date-Spalte)
mapfile -t IDX < <(for i in "${IDX[@]}"; do printf '%s\t%s\n' "${M_DATE[$i]}" "$i"; done | sort -r | cut -f2)

declare -a LABELS=()
for i in "${IDX[@]}"; do
  mark="   "; note=""
  if [[ "${M_ACTIVE[$i]}" == 1 ]]; then mark="[*]"; note="  <- AKTIV"
  elif [[ "${M_INSTALLED[$i]}" == 1 ]]; then mark="[*]"; note="  (installiert)"; fi
  LABELS+=("$(printf '%s %s  %-8s  v%s%s' "$mark" "${M_DATE[$i]}" "${M_REV[$i]}" "${M_VERSION[$i]}" "$note")")
done
DEFAULT_LABEL="${LABELS[0]}"   # neueste
CHOSEN_LABEL="$(ui_choose "Welche Closure für '${CHOSEN_HOST}'?  ([*] = bereits installiert)" "$DEFAULT_LABEL" "${LABELS[@]}")" || exit 1

SEL=-1
for k in "${!LABELS[@]}"; do [[ "${LABELS[$k]}" == "$CHOSEN_LABEL" ]] && SEL="${IDX[$k]}"; done
[[ "$SEL" -ge 0 ]] || { log_err "Auswahl nicht auflösbar."; exit 1; }

ARCHIVE="${M_ARCHIVE[$SEL]}"; TOPLEVEL="${M_TOPLEVEL[$SEL]}"; SHA="${M_SHA[$SEL]}"

# ---------------------------------------------------------------------------
# 3) Aktion wählen
# ---------------------------------------------------------------------------
ACTION="$(ui_choose "Wie aktivieren?" "switch" \
  "switch" "boot" "test" "dry-activate")" || exit 1

# ---------------------------------------------------------------------------
# 4) Bestätigung + Ausführung
# ---------------------------------------------------------------------------
echo
cat <<EOF
  Host      : $CHOSEN_HOST   (aktiv: $ACTIVE_HOST)
  Closure   : $ARCHIVE
  Toplevel  : $TOPLEVEL
  Aktion    : $ACTION
EOF
if [[ "${M_ACTIVE[$SEL]}" == 1 ]]; then
  log_warn "Diese Closure ist aktuell aktiv."
elif [[ "${M_INSTALLED[$SEL]}" == 1 ]]; then
  log_warn "Diese Closure ist bereits installiert (ältere Generation)."
fi
ui_confirm "Jetzt ausführen?" || { log_warn "Abgebrochen."; exit 0; }

# sudo-Credentials vorab holen, damit kein Passwort-Prompt mitten in der Import-Pipe hängt
if [[ ${#SUDO[@]} -gt 0 ]]; then log_info "sudo-Rechte anfordern ..."; sudo -v; fi

# 4a) Prüfsumme
if [[ -f "$SCRIPT_DIR/$ARCHIVE.sha256" ]]; then
  log_info "Prüfsumme verifizieren ..."
  ( cd "$SCRIPT_DIR" && sha256sum -c "$ARCHIVE.sha256" )
  log_ok "SHA256 ok."
elif [[ -n "$SHA" ]]; then
  log_info "Prüfsumme (aus Manifest) verifizieren ..."
  echo "$SHA  $ARCHIVE" | ( cd "$SCRIPT_DIR" && sha256sum -c - )
  log_ok "SHA256 ok."
else
  log_warn "Keine Prüfsumme vorhanden — überspringe Check."
fi

# 4b) Import (idempotent) — zstd liest als User vom Medium, nix-store schreibt via sudo in den Store
log_info "Importiere Closure ins lokale Store (das dauert) ..."
zstd -d --long=31 -c "$SCRIPT_DIR/$ARCHIVE" | "${SUDO[@]}" nix-store --import >/dev/null
log_ok "Import abgeschlossen."

# 4c) Toplevel validieren
[[ -e "$TOPLEVEL" ]] || { log_err "Toplevel $TOPLEVEL nach Import nicht im Store!"; exit 1; }
log_ok "Toplevel im Store: $TOPLEVEL"

# 4d) System-Profil setzen — nur bei persistenten Aktionen (nicht test/dry-activate)
if [[ "$ACTION" == "switch" || "$ACTION" == "boot" ]]; then
  log_info "Setze System-Profil ..."
  "${SUDO[@]}" nix-env -p /nix/var/nix/profiles/system --set "$TOPLEVEL"
  log_ok "Profil /nix/var/nix/profiles/system -> $TOPLEVEL"
else
  log_warn "Aktion '$ACTION': System-Profil wird NICHT gesetzt (nicht persistent)."
fi

# 4e) Aktivieren
log_info "Aktiviere: switch-to-configuration $ACTION ..."
"${SUDO[@]}" "$TOPLEVEL/bin/switch-to-configuration" "$ACTION"
log_ok "Fertig. Aktion: $ACTION"

case "$ACTION" in
  boot)        log_warn "Nur Bootloader gesetzt — aktiv erst nach Reboot." ;;
  test)        log_warn "Nur live aktiviert (test) — NICHT im Bootloader, nach Reboot weg." ;;
  dry-activate) log_warn "Trockenlauf — nichts wurde aktiviert." ;;
esac
