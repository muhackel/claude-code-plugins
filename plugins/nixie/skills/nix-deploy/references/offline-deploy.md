# Offline-Closure-Deploy (USB, generisch)

Referenz zu `nix-deploy`, lesen vor einem Offline-Deploy (Export auf ein Medium, Import und Aktivierung am Ziel ohne Netz). Die Skripte liegen unter `../assets/` relativ zu dieser Datei.

Für Ziele ohne Netz/Cache: System-Closure auf der Build-Kiste exportieren, per USB zum Ziel tragen,
dort importieren + aktivieren. Zwei Skripte unter `../assets/` relativ zu dieser Datei (aus der
handgeschriebenen BFG9000-Blaupause verallgemeinert); diesen Pfad ab dem Verzeichnis dieser Datei
auflösen, nicht ab dem Arbeitsverzeichnis, und beim Aufruf absolut ausschreiben. Den Export aus der
Config-Root starten: `-r` nimmt per Default deren `git rev-parse`. Konvention: **ein** Zielverzeichnis
`<medium>/nix-offline-deploy` für alle Hosts — der Hostname steckt im Dateinamen/Manifest, das Deploy-TUI
wählt am Ziel aus.

- **`nixos-offline-export.sh`** (Build-Kiste): baut **erst lokal** (`$TMPDIR`/`-w`, schnelle Disk),
  verifiziert dort, kopiert dann aufs Medium und prüft die **Stick-Kopie** per sha256 gegen. Ablauf:
  `nix-store --export | zstd -<l> --long=31` → `zstd -t` (lokal) → sha256 + Manifest → gum beilegen →
  aufs Medium kopieren → `sha256sum -c` vom Medium. Erzeugt `<host>-<rev>.nar.zst` + `.sha256` +
  `<host>-<rev>.manifest`, dazu `nixos-offline-deploy.sh` + `gum`.
  Flags: `-o <ziel>` (Pflicht), `-t <toplevel>` (Default `/run/current-system`), `-r <rev>`, `-j <threads>`,
  `-l <1-19>` (zstd-Stufe, Default **12**), `-w <workdir>` (lokaler Build-Ort, Default `$TMPDIR`/`/tmp`).
- **`nixos-offline-deploy.sh`** (Ziel): TUI über die Manifeste — Host wählen (Default = aktiver `hostname`,
  fremder Host → Hardware-Warnung + Confirm), Closure wählen (nach Build-Datum, installierte `[*]`, aktive
  `<- AKTIV`), Aktion (`switch|boot|test|dry-activate`), dann sha256 → `zstd -d | nix-store --import` →
  Profil setzen → `switch-to-configuration`. **Ohne vorangestelltes sudo starten** — die TUI-Auswahl läuft
  als User, nur die privilegierten Schritte eskalieren intern via `sudo` (wie `nixos-rebuild --sudo`).

**Manifest-Format** (`key=value`, `#`-Kommentare) — das TUI liest ausschließlich diese, nie das Archiv:
```
# nixie offline-closure manifest v1
host=BFG9000
toplevel=/nix/store/<hash>-nixos-system-BFG9000-26.11.20260712.4ebb8d6
archive=bfg9000-0f62e28.nar.zst
date=2026-07-12
rev=0f62e28
version=26.11.20260712.4ebb8d6
sha256=<archiv-sha256>
```

**zstd-Stufe:** Default **12**, nicht 19. Store-Closures erreichen mit `--long=31` schon bei ~12–15 fast die
volle Kompression; `-19 --long=31` kostet ein Vielfaches an Zeit (CPU-bound, saturiert nur ~halb so viele
Kerne) für wenige Prozent kleineres Archiv. Live gemessen (42,7 GiB Closure): `-12` ~2,5 min → 12,2 GB
gegen `-19` ~34 min. Für ein Langzeit-Archiv `-l` hochsetzen.

**Verifizierte Fallstricke (in den Skripten gelöst):**
- **exFAT/USB direkt zu beschreiben ist fragil → erst lokal bauen, dann kopieren + gegenprüfen.** Ein
  USB-Disconnect unter Schreiblast hinterlässt eine „erfolgreich geschriebene", aber unvollständige Datei
  (`zstd` meldet ok, der Rest wird nie geflusht; späteres `zstd -t`: „premature end"). Darum lokal
  bauen+`zstd -t`, dann aufs Medium kopieren und die **Stick-Kopie** per `sha256sum -c` gegenprüfen — den
  Page-Cache vorher gezielt räumen (`dd … iflag=nocache`, kein root), sonst liest man die Cache-Kopie statt
  des Mediums. Fängt Disconnect/Transferfehler sofort, statt beim Deploy. (Reales Symptom war Kernel-
  `I/O error, dev sda` — Port/Kabel unter Last; Hardware, nicht exFAT/FUSE/zstd. Reconnect an anderem Port
  → wieder 770 MB/s.)
- **gum immer + statisch beilegen.** Der Export legt gum **immer** bei (`nix build` wird immer zuerst
  versucht; gum aus dem PATH ist nur der Fallback) und bevorzugt `pkgsStatic.gum` (musl-static → einzelnes Binary ohne Store-Abhängigkeiten, läuft auf einem
  nackten Ziel). Erster static-Build zieht den Go-Compiler (Long-Runner, danach gecacht). Das Deploy-TUI
  nutzt gum nur, wenn `--version` läuft, sonst **still Plain-Bash-Fallback**.
- **Build-Datum ≠ Store-mtime.** Nix normalisiert alle Store-Pfad-mtimes auf `1` (1970) → `stat -c %Y`
  ist nutzlos. Das nixpkgs-Datum steckt als `YYYYMMDD` in der Version (`26.11.20260712.…`) — von dort ziehen.
- **`basename` des Toplevels trägt den Store-Hash-Präfix** (`<hash>-nixos-system-<HOST>-<VER>`). Erst bis
  inkl. `nixos-system-` abschneiden, dann am letzten `-<Ziffer…>` in Host/Version trennen.
- **`[[ … ]] && x` als letzte Anweisung einer Funktion** gibt Exit 1 zurück, wenn die Bedingung false ist →
  unter `set -e` killt das den Funktionsaufruf. Solche Funktionen mit `return 0` abschließen.
- **`test`/`dry-activate` setzen das System-Profil NICHT** (`nix-env --set` nur bei `switch`/`boot`) — sonst
  wird ein „nur mal testen" fälschlich persistent.
- **Dekompression braucht `--long=31`**, wenn beim Export ein großes Long-Distance-Window genutzt wurde
  (sonst „Frame requires too much memory"). `--long=31` deckt jedes kleinere Window mit ab.
- **Export-Integrität** (s. „Lange Builds als Subagent"): `set -euo pipefail` (pipefail deckt einen
  abgebrochenen `--export` vor grünem `zstd` auf), `.sha256`/Manifest erst nach `zstd -t`. Der Export ist
  ein Long-Runner > 120 s → gehört zum Hauptagenten/User, nicht in einen Subagent.
