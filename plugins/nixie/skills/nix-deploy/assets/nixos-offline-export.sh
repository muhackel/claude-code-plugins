#!/usr/bin/env bash
# Export einer NixOS-System-Closure als Offline-Archiv + Sidecar-Manifest.
#
# Auf der BUILD-Kiste ausführen. Erzeugt im Zielverzeichnis:
#   <host>-<rev>.nar.zst          komprimierte Closure (nix-store --export | zstd)
#   <host>-<rev>.nar.zst.sha256   Prüfsumme (erst NACH Integritätscheck geschrieben)
#   <host>-<rev>.manifest         Metadaten für das Deploy-TUI (host/toplevel/date/rev/version/sha256)
# und legt einmalig das Deploy-TUI (nixos-offline-deploy.sh) + gum-Binary daneben.
#
# Mehrere Hosts teilen sich EIN Zielverzeichnis (Konvention: <medium>/nix-offline-deploy) —
# der Hostname steckt im Dateinamen/Manifest, das Deploy-TUI wählt am Ziel aus.
#
#   ./nixos-offline-export.sh -o /media/STICK/nix-offline-deploy [-t /run/current-system] [-r <rev>] [-l 12]
#
#   -o DIR   Zielverzeichnis (Pflicht; USB-Medium; Konvention: <medium>/nix-offline-deploy)
#   -t PATH  Toplevel (Default: /run/current-system)
#   -r REV   Kurz-Revision fürs Naming/Manifest (Default: git rev-parse --short HEAD im cwd, sonst store-hash)
#   -j N     zstd-Threads (Default: nproc)
#   -l N     zstd-Stufe 1-19 (Default: 12). Store-Closures erreichen mit --long=31 schon bei ~12-15
#            fast die volle Kompression; ab ~17 kostet jede Stufe viel Zeit für kaum kleinere Archive
#            (und -19 --long=31 saturiert nur ~halb so viele Kerne). Für ein Langzeit-Archiv höher.
#   -w DIR   Arbeitsverzeichnis für den lokalen Build (Default: $TMPDIR bzw. /tmp). Das Archiv wird
#            hier gebaut+verifiziert und erst dann auf das (langsame/fragile) USB-Medium kopiert.
#            Genug Platz nötig (~Closure/2). Bei tmpfs-/tmp ggf. auf eine echte Disk zeigen.
set -euo pipefail

C_INFO='\033[1;34m'; C_OK='\033[1;32m'; C_WARN='\033[1;33m'; C_ERR='\033[1;31m'; C_RST='\033[0m'
log_info(){ echo -e "${C_INFO}[*]${C_RST} $*"; }
log_ok(){   echo -e "${C_OK}[+]${C_RST} $*"; }
log_warn(){ echo -e "${C_WARN}[!]${C_RST} $*"; }
log_err(){  echo -e "${C_ERR}[x]${C_RST} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="" TOPLEVEL="/run/current-system" REV="" THREADS="$(nproc 2>/dev/null || echo 4)" LEVEL=12 WORKDIR=""
while getopts ":o:t:r:j:l:w:h" opt; do
  case "$opt" in
    o) OUT="$OPTARG" ;;
    t) TOPLEVEL="$OPTARG" ;;
    r) REV="$OPTARG" ;;
    j) THREADS="$OPTARG" ;;
    l) LEVEL="$OPTARG" ;;
    w) WORKDIR="$OPTARG" ;;
    h) grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    :) log_err "Option -$OPTARG braucht ein Argument."; exit 1 ;;
    \?) log_err "Unbekannte Option -$OPTARG."; exit 1 ;;
  esac
done
if [[ ! "$LEVEL" =~ ^[0-9]+$ ]] || (( LEVEL<1 || LEVEL>19 )); then
  log_err "zstd-Stufe (-l) muss 1-19 sein, nicht '$LEVEL'."; exit 1
fi

for bin in nix-store zstd sha256sum; do
  command -v "$bin" >/dev/null 2>&1 || { log_err "'$bin' nicht im PATH."; exit 1; }
done
[[ -n "$OUT" ]] || { log_err "Zielverzeichnis fehlt (-o)."; exit 1; }
mkdir -p "$OUT"
TOPLEVEL="$(readlink -f "$TOPLEVEL")"
[[ -e "$TOPLEVEL" ]] || { log_err "Toplevel existiert nicht: $TOPLEVEL"; exit 1; }

# Host + Version aus dem Toplevel-Basename ableiten. Der Store-Pfad hat die Form
# /nix/store/<hash>-nixos-system-<HOST>-<VERSION> -> Hash-Präfix bis inkl. "nixos-system-"
# abschneiden, dann am letzten "-<Ziffer...>" in Host und Version trennen.
BASE="$(basename "$TOPLEVEL")"
NAME="${BASE#*nixos-system-}"
if [[ "$NAME" != "$BASE" && "$NAME" =~ ^(.+)-([0-9].*)$ ]]; then
  HOST="${BASH_REMATCH[1]}"; VERSION="${BASH_REMATCH[2]}"
else
  log_warn "Toplevel-Name unerwartet ($BASE) — nutze hostname/leere Version."
  HOST="$(hostname)"; VERSION=""
fi

# Revision: -r, sonst git im cwd, sonst Store-Hash-Präfix
if [[ -z "$REV" ]]; then
  REV="$(git rev-parse --short HEAD 2>/dev/null || true)"
  [[ -n "$REV" ]] || REV="$(basename "$TOPLEVEL" | cut -c1-7)"  # fallback: store-hash-präfix
fi

# Build-Datum: Nix normalisiert Store-mtimes auf 1 -> nutzlos. Das nixpkgs-Datum
# steckt als YYYYMMDD in der Version (z.B. 26.11.20260712.4ebb8d6); sonst heutiges Datum.
if [[ "$VERSION" =~ ([0-9]{4})([0-9]{2})([0-9]{2}) ]]; then
  DATE="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]}"
else
  DATE="$(date +%Y-%m-%d)"
fi

STEM="${HOST,,}-${REV}"

# Erst lokal bauen+verifizieren, dann auf den Stick kopieren. Direkt auf exFAT/USB zu
# komprimieren ist fragil: ein Disconnect unter Last hinterlässt eine "erfolgreich
# geschriebene", aber unvollständige Datei (zstd meldet ok, der Rest wurde nie geflusht).
WORKROOT="${WORKDIR:-${TMPDIR:-/tmp}}"
WORK="$(mktemp -d "$WORKROOT/nixos-offline-export.XXXXXX")" || { log_err "Arbeitsverzeichnis in $WORKROOT nicht anlegbar."; exit 1; }
trap 'rm -rf "$WORK"' EXIT
W_ARCHIVE="$WORK/${STEM}.nar.zst"
W_MANIFEST="$WORK/${STEM}.manifest"

log_info "Host=$HOST  Version=$VERSION  Rev=$REV  Stufe=zstd-$LEVEL"
log_info "Toplevel=$TOPLEVEL"
log_info "Bauen in: $WORK   ->   Ziel (Stick): $OUT"

# Platz-Check: Arbeits-FS braucht grob Closure/2 (Archiv-Obergrenze)
CLOSURE_B="$(nix path-info -S "$TOPLEVEL" 2>/dev/null | awk '{print $NF}')"
if [[ "$CLOSURE_B" =~ ^[0-9]+$ ]]; then
  NEED=$(( CLOSURE_B / 2 ))
  avail_work="$(df -B1 --output=avail "$WORK" 2>/dev/null | tail -1 | tr -dc 0-9)"
  if [[ -n "$avail_work" && "$avail_work" -lt "$NEED" ]]; then
    log_warn "Wenig Platz in $WORK ($((avail_work/1073741824)) GiB frei, ~$((NEED/1073741824)) GiB möglich nötig) — ggf. -w <dir> auf eine größere Disk."
  fi
fi

# 1) Export -> WORK (lokale schnelle Disk). pipefail essenziell: maskiert sonst einen
#    abgebrochenen --export vor grünem zstd.
log_info "Exportiere Closure (nix-store --export | zstd -$LEVEL --long=31 -T$THREADS, das dauert) ..."
# nix-store -qR liefert Store-Pfade ohne Whitespace — word-splitting ist hier gewollt.
# shellcheck disable=SC2046
nix-store --export $(nix-store -qR "$TOPLEVEL") | zstd -T"$THREADS" --long=31 -"$LEVEL" -o "$W_ARCHIVE" -f
log_ok "Archiv gebaut."

# 2) Lokal verifizieren (zuverlässig auf schneller Disk)
log_info "Integrität prüfen (zstd -t, lokal) ..."
zstd -t --long=31 "$W_ARCHIVE"
log_ok "Archiv-Integrität ok."

SHA="$(sha256sum "$W_ARCHIVE" | cut -d' ' -f1)"
echo "$SHA  ${STEM}.nar.zst" > "$W_ARCHIVE.sha256"

# 3) Manifest -> WORK
cat > "$W_MANIFEST" <<EOF
# nixie offline-closure manifest v1
host=$HOST
toplevel=$TOPLEVEL
archive=${STEM}.nar.zst
date=$DATE
rev=$REV
version=$VERSION
sha256=$SHA
EOF
log_ok "Manifest erstellt."

# 4) Deploy-TUI -> WORK
DEPLOY_SRC="$SCRIPT_DIR/nixos-offline-deploy.sh"
[[ -f "$DEPLOY_SRC" ]] && cp -f "$DEPLOY_SRC" "$WORK/nixos-offline-deploy.sh"

# 5) gum IMMER beilegen — möglichst statisch, damit es auf einem nackten Ziel läuft.
#    Reihenfolge: pkgsStatic (musl-static, voll portabel; nach dem 1. Build gecacht) ->
#    gum im PATH -> dynamisches nixpkgs#gum. Ein statisches gum ist ein einzelnes Binary
#    ohne Store-Abhängigkeiten und braucht kein bin/lib-Beiwerk.
log_info "gum beilegen (statisch bevorzugt) ..."
GUM_BIN=""
GUM_STORE="$(nix build nixpkgs#pkgsStatic.gum --no-link --print-out-paths 2>/dev/null | head -1 || true)"
[[ -n "$GUM_STORE" && -x "$GUM_STORE/bin/gum" ]] && GUM_BIN="$GUM_STORE/bin/gum"
[[ -z "$GUM_BIN" ]] && GUM_BIN="$(command -v gum 2>/dev/null || true)"
if [[ -z "$GUM_BIN" ]]; then
  GUM_STORE="$(nix build nixpkgs#gum --no-link --print-out-paths 2>/dev/null | head -1 || true)"
  [[ -n "$GUM_STORE" && -x "$GUM_STORE/bin/gum" ]] && GUM_BIN="$GUM_STORE/bin/gum"
fi
if [[ -n "$GUM_BIN" ]]; then
  GUM_BIN="$(readlink -f "$GUM_BIN")"
  cp -f "$GUM_BIN" "$WORK/gum"; chmod +x "$WORK/gum" 2>/dev/null || true
  if ldd "$WORK/gum" 2>&1 | grep -q 'not a dynamic executable'; then
    log_ok "gum beigelegt (statisch — portabel auf nackte Ziele)."
  else
    log_warn "gum beigelegt, aber DYNAMISCH gelinkt — auf fremdem System evtl. nicht lauffähig; Deploy-TUI fällt dann auf Plain-Bash zurück."
  fi
else
  log_warn "gum konnte nicht beschafft werden — Deploy-TUI nutzt am Ziel den Plain-Bash-Fallback."
fi

# 6) Auf den Stick kopieren
mkdir -p "$OUT"
log_info "Kopiere Paket auf den Stick: $OUT ..."
cp -f "$W_ARCHIVE" "$W_ARCHIVE.sha256" "$W_MANIFEST" "$OUT/"
if [[ -f "$WORK/nixos-offline-deploy.sh" ]]; then cp -f "$WORK/nixos-offline-deploy.sh" "$OUT/"; chmod +x "$OUT/nixos-offline-deploy.sh" 2>/dev/null || true; fi
if [[ -f "$WORK/gum" ]]; then cp -f "$WORK/gum" "$OUT/"; chmod +x "$OUT/gum" 2>/dev/null || true; fi
sync
log_ok "Kopiert."

# 7) Stick-Kopie gegenprüfen — fängt Transferfehler / Disconnect unter Last (premature end etc.)
log_info "Verifiziere Stick-Kopie (sha256 vom Medium) ..."
sync
# Page-Cache für das Archiv gezielt räumen (fadvise DONTNEED, kein root), damit sha256sum
# den echten Medium-Inhalt liest statt der eben geschriebenen Cache-Kopie.
dd if="$OUT/${STEM}.nar.zst" of=/dev/null bs=4M iflag=nocache 2>/dev/null || true
if ( cd "$OUT" && sha256sum -c "${STEM}.nar.zst.sha256" ); then
  log_ok "Stick-Kopie verifiziert — Transfer intakt."
else
  log_err "Stick-Kopie WEICHT AB (Transferfehler/Disconnect?) — Archiv auf dem Stick ist unbrauchbar."
  log_err "Anderen USB-Port/Kabel/Stick versuchen und erneut exportieren."
  exit 1
fi

echo
log_ok "Offline-Deploy-Paket bereit in: $OUT"
log_info "Auf dem Ziel:  cd '$OUT' && ./nixos-offline-deploy.sh"
