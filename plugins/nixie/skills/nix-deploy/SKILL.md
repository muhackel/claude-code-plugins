---
name: nix-deploy
description: "Bauen und Deployen von NixOS: Build-Host dynamisch wählen (Host-Config aus CLAUDE.md oder ~/.config/nixie/hosts.conf, schnellste erreichbare Kiste), resource-aware Drosselung von --max-jobs/--cores gegen OOM bei schweren Builds, nix flake check ohne Truncation, Eskalationsstufen check → build → switch → Remote-Deploy. Nutzen bei nix flake check, nixos-rebuild, Remote-Builds oder Deploy auf andere Hosts."
---

# Nix-Deploy — Bauen, Build-Hosts, Deploy

## Build-Sichtbarkeit (kein tail, kein Background)

Der User beobachtet Builds **live im Terminal** — was gerade gebaut wird, wo es hängt, Logs in Echtzeit.
Darum: `nix build`, `nixos-rebuild`, `nix-build` & vergleichbare Long-Runner **nie** durch `| tail`/`| head`/
`| grep` pipen und **nie** mit `run_in_background: true` starten — beides schneidet die Live-Ausgabe ab (ein
Background-Job ist genauso ein Cut wie `tail`). Builds im **Vordergrund** laufen lassen, ggf. `-L` für volle
Logs. Errors erst **nach** dem Lauf aus dem Drv-Log filtern (`nix log <drv>`), nicht den laufenden Build
pipen. Gilt analog für `cargo build`, `make` u.a. Wenn ein Build sehr lang ist und parallel weitergearbeitet
werden muss, kurz mit dem User klären (sein Standard-Workflow ist `nixos-rebuild switch --sudo` im eigenen
Terminal).

## Lange Builds als Subagent — delegieren statt verwaisen

Läuft Nixie als **Subagent** (via Agent/Task-Tool gespawnt — der Normalfall beim `/nixie`-Command), gilt eine
harte Grenze: Die Harness **detacht jeden Bash-Call nach ~120 s automatisch in den Hintergrund und beendet
den Subagent-Turn** — und ein Subagent wird danach **nicht wieder aufgeweckt** (anders als der Hauptloop, der
auf die Completion-Notification reagiert). Das Kriterium ist **Wanduhr-Dauer > ~120 s**, NICHT „ist es ein
Build". Betroffen sind also nicht nur kompilier-schwere Schritte (`nixos-rebuild build/switch`,
`nix flake check`), sondern **genauso** reine I/O-Long-Runner: `nix-store --export`/`nix copy` großer
Closures, Archiv-Kompression (`zstd`) auf externe/langsame Medien (USB, exFAT). Alle lassen sich als
Subagent **nicht** „im Vordergrund bis durch" fahren — der Schritt verwaist zwangsläufig, läuft führungslos
weiter (bei einem Export reißt dabei die Pipe mittendrin ab → korruptes Teilarchiv) und die Folgeschritte
(Auswertung, commit, switch) bleiben liegen. Das ist KEIN Bug zum Umgehen, sondern die dokumentierte
Architektur (Subagenten = selbstbegrenzte Tasks mit Summary; lange Arbeit gehört zum Hauptagenten).

Regel für den Subagent-Fall:
- **Vorbereiten, nicht durchziehen.** Alles bis zum Build erledigen: `dry-build` lesen, Drosselung berechnen
  (Drosselungs-Sektion), den **exakten, gedrosselten Befehl** fertig zusammenstellen.
- **Den fertigen Befehl an den Aufrufer zurückgeben** (Hauptloop/User), der ihn im resilienten Kontext bzw.
  im eigenen Terminal ausführt — dort bleibt auch die Live-Sichtbarkeit erhalten.
- **Kurze, sicher unter ~120 s terminierende Schritte** macht der Subagent selbst: eval, `dry-build`-Analyse,
  `lsblk`, git, `flake.lock`-Manipulation, Erreichbarkeitstest. Auch eine reine Aktivierung bei warmem Store
  (Build schon im Cache, nur `switch`) darf der Subagent fahren — aber konservativ schätzen; im Zweifel
  delegieren.
- Der Grund ist die **Dauer**, nicht sudo: `nixos-rebuild switch --sudo` läuft beim User passwortlos
  durch — ein kurzer Aktivierungs-`switch` scheitert also nicht am sudo, sondern nur lange Läufe am Detach.
- **Nie eine zweite Nixie starten, solange die erste noch läuft.** Ein Neustart steuert die bereits
  führungslos laufende Erstinstanz nicht — die verwaist nach ~10 min und reißt ihren Job (Build/Export) ab.
  Die „delegieren statt verwaisen"-Regel macht „mit der laufenden Nixie weitersprechen" ohnehin unnötig; ist
  eine Erstinstanz noch aktiv, erst sauber beenden/abwarten.
- **Export-Integrität** (wenn ein Export doch im resilienten Kontext läuft): `set -euo pipefail` (das
  `pipefail` ist essenziell — sonst maskiert ein grüner `zstd` einen abgebrochenen `nix-store --export`
  davor), und die `.sha256` **erst nach** erfolgreichem Integritätscheck (`zstd -t <archiv>`) erzeugen —
  sonst hinterlässt ein abgebrochener Pipe ein Teilarchiv samt falscher, zu früh geschriebener Prüfsumme.

## `nix flake check` — Regel

**Immer vollständig laufen lassen.** Niemals nach `| tail`, `| head` oder `2>/dev/null` pipen — das versteckt
genau die Fehler, die geprüft werden sollen. Volle Ausgabe lesen und auswerten. Läuft vor jeder
Fertigstellung einer Änderung.

**`flake check` IST ein schwerer Build — drosseln ist Pflicht, nicht optional.** Er baut die Toplevels
**aller** Hosts gleichzeitig (jeder `nixosConfigurations.<h>.config.system.build.toplevel`, inkl. *mehrerer*
NVIDIA-Treiber, Kernel-Module, webkitgtk …) und ignoriert `--build-host` — läuft also **immer lokal** auf der
aktuellen Kiste. Das ist der RAM-schwerste nix-Lauf überhaupt. Konsequenzen:
- **Immer mit kalkuliertem `--max-jobs`/`--cores`** starten (Flags stehen direkt am `nix`-Aufruf:
  `nix flake check --max-jobs <MJ> --cores <CO> -L`). Da es keinen praktikablen Dry-Run über alle Hosts gibt,
  defensiv als **heavy** einstufen (siehe Drosselungs-Sektion) — nie ungedrosselt mit Default-Parallelität.
- **Im Vordergrund**, nicht mit `run_in_background` (siehe Build-Sichtbarkeit). Einen bauenden Job nie
  verwaisen lassen — RAM beobachten, bis er durch ist. **Als Subagent gar nicht erst selbst fahren** —
  vorbereiten und den fertigen Befehl delegieren (siehe „Lange Builds als Subagent").
- `--keep-going` (alle Fehler auf einmal) **nur auf einem bereits gedrosselten Lauf** — auf einem
  ungedrosselten verlängert es nur den RAM-Druck und das OOM-Fenster.

## nixos-rebuild (ng) — CLI-Form

Aktueller `nixos-rebuild` ist die ng-Variante (Python-Rewrite). Wichtig:
- **Aktion ist ein positionaler Subcommand:** `switch | boot | test | build | dry-build | dry-activate |
  build-vm | build-image | list-generations | repl | edit`. Den **echten Dry-Run** für „was würde gebaut/
  geladen" liefert `dry-build` (nicht mehr `--dry-run`).
- **Nix-Build-Flags stehen VOR der Aktion:** `nixos-rebuild --max-jobs N --cores M <aktion>`
  (auch `--keep-going`, `--option …`).
- **Aktivierung als Nicht-Root (Elevation):** `--elevate {none,sudo,run0}`; `--sudo` = Alias für
  `--elevate=sudo` und nutzt **passwortloses** sudo **ohne** Prompt — der Default-Weg, lokal wie remote.
  `-S`/`--ask-elevate-password` (Alt-Alias `--ask-sudo-password`) **erzwingt einen interaktiven
  Passwort-Prompt** und impliziert `--elevate=sudo` — im nicht-interaktiven Hauptloop **unbedienbar**, nur
  wenn das Ziel-sudo wirklich ein Passwort verlangt. Für Remote-Aktivierung via `--target-host` mit
  passwortlosem sudo: `--elevate=sudo` **ohne** `-S`; vorab prüfen `ssh -o BatchMode=yes user@<ziel> 'sudo -n true'`.
- **Host-Flags:** `--build-host user@host` (Kompilation dort), `--target-host user@host` (Aktivierung dort);
  beide nehmen einen ssh-erreichbaren Host, SSH-Optionen via `NIX_SSHOPTS`. **Für lokalen Build `--build-host`
  weglassen** (Default = nativer lokaler Build ohne SSH) — `--build-host localhost` erzwingt eine echte
  SSH-Loopback-Verbindung und scheitert an veralteten `known_hosts`-Einträgen (*Host key changed*).
  `--use-substitutes`, wenn der Ziel-/Build-Host schneller am Cache hängt als die Hosts untereinander.
- **Flake-Auswahl:** `--flake .#<host>` (sonst Auto-Erkennung über Hostname).

## Eskalationsstufen (Default = niedrigste)

Die erlaubte Stufe ergibt sich aus der **konkreten Anfrage** des Users — nicht eigenmächtig eskalieren:

1. **check / build (Default):** `nix flake check`, `nixos-rebuild dry-build`, `nixos-rebuild build`,
   `nix build .#…`. Ändert nichts am Live-System.
2. **Lokaler switch:** `nixos-rebuild switch --sudo [--flake .#<host>]` — nur wenn explizit verlangt.
   Vorher ansagen.
3. **Remote-Build:** `nixos-rebuild switch --sudo --build-host user@<fast>` — Kompilation auf der schnellen
   Kiste, Aktivierung lokal.
4. **Remote-Deploy:** `nixos-rebuild switch --target-host user@<ziel> --build-host user@<fast>
   --elevate=sudo [--use-substitutes] --flake .#<ziel>` — baut auf der schnellen Kiste, aktiviert auf einem
   anderen Host. **Kein `-S`** (erzwänge einen unbedienbaren Passwort-Prompt); passwortloses Ziel-sudo vorab
   prüfen: `ssh -o BatchMode=yes user@<ziel> 'sudo -n true'`. Für lokalen Build `--build-host` weglassen.
   Nur auf explizite Anweisung; Ziel-Host vorher nennen und bestätigen lassen.

5. **Offline-Deploy (USB, kein Netz zum Ziel):** Closure auf ein Medium exportieren, am Ziel importieren
   und aktivieren — siehe eigene Sektion unten. Für Hosts, die weder Build- noch Cache-Zugang haben
   (isoliertes Netz, Erstinstallation, Air-Gap).

## Offline-Closure-Deploy (USB, generisch)

Für Ziele ohne Netz/Cache: System-Closure auf der Build-Kiste exportieren, per USB zum Ziel tragen,
dort importieren + aktivieren. Zwei Skripte unter `skills/nix-deploy/assets/` (aus der handgeschriebenen
BFG9000-Blaupause verallgemeinert). Konvention: **ein** Zielverzeichnis `<medium>/nix-offline-deploy` für
alle Hosts — der Hostname steckt im Dateinamen/Manifest, das Deploy-TUI wählt am Ziel aus.

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
- **gum immer + statisch beilegen.** Der Export legt gum **immer** bei (via `nix build`, falls nicht im PATH)
  und bevorzugt `pkgsStatic.gum` (musl-static → einzelnes Binary ohne Store-Abhängigkeiten, läuft auf einem
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

## Build-Host-Auswahl

### Config-Auflösung (Reihenfolge)
1. **Globale `~/.claude/CLAUDE.md`** — Nixie-Block (Sektion `## Nixie` oder Fence `<!-- nixie:hosts -->`).
2. **Lokale/Projekt-`CLAUDE.md`** — gleicher Block.
3. **Fallback `~/.config/nixie/hosts.conf`** — Format mit `#`-Kommentaren, je Zeile:
   ```
   # alias   ssh-target            rolle(build|deploy|local)   notiz
   spielkiste spielkiste.lan       build,deploy                Framework Desktop, schnellste Kiste
   spielkiste spielkiste.wlan.lan  build,deploy                alternativer DNS (WLAN)
   ```

### Zero-Config-Bootstrap (nichts gefunden)
1. Hosts aus dem Flake ermitteln:
   `nix eval .#nixosConfigurations --apply 'builtins.attrNames' 2>/dev/null` (vollständig lesen).
2. Localhost bestimmen: `hostname` mit den Host-Namen abgleichen (ggf.
   `nix eval .#nixosConfigurations.<h>.config.networking.hostName`).
3. **User fragen**, ob einzelne Hosts unter alternativen DNS-Namen/IPs erreichbar sind (z.B. je nach WLAN-/
   LAN-Schnittstelle mehrere Aliase pro Host) — diese mit aufnehmen.
4. Ergebnis schreiben: nach `~/.config/nixie/hosts.conf` (oder, falls der User es will, als Nixie-Block in
   eine CLAUDE.md) und bestätigen lassen.

### Schnellste Kiste wählen (zur Laufzeit)
- **LAN vor WiFi.** Hat ein Host mehrere Adressen (kabelgebunden + WLAN, oft als Namensvariante wie
  `<host>` vs. `<host>-wifi`), zuerst die **LAN-Adresse** (nackter Hostname / kabelgebundener Alias) auf
  Erreichbarkeit testen — schneller und stabiler für Build und Deploy. Einen `-wifi`/`.wlan`-Alias nur als
  Fallback nehmen. Erreichbarkeit **dynamisch** prüfen (z.B. `for h in <host> <host>-wifi; do ping -c1 -W2
  "$h" && break; done`), nie auf feste IPs verlassen — die ändern sich mit DHCP/Umgebung. Den so gefundenen
  Namen dann konsistent für `ssh`/`--build-host`/`--target-host` verwenden.
- Kandidaten = Hosts mit Rolle `build`. Erreichbarkeit + Geschwindigkeit prüfen:
  `ssh <target> 'nproc; cat /proc/loadavg'` (kurzer Timeout, vollständige Ausgabe).
- Höchste freie Kapazität (nproc minus Last) gewinnt. Ist kein `build`-Host erreichbar, lokal bauen; gibt es
  in der Config einen bevorzugten Build-Host (Notiz/Markierung), diesen als Fallback nehmen, sonst fragen.
- **Bei Mehrdeutigkeit fragen** — z.B. wenn ein Flake VMs/mehrere Architekturen baut oder mehrere Kisten
  gleich schnell sind.

## Resource-aware Build-Drosselung (kein OOM)

Die Regel hängt an **„es werden Pakete kompiliert"**, nicht am Befehlsnamen: `nixos-rebuild build/switch`,
`nix build` UND `nix flake check` fallen alle darunter. Schwere C++/Rust-Builds (v.a. parallel) sprengen
RAM. Vorgehen:

```
# 1) Kapazität des Build-Hosts (lokal: /proc/meminfo & nproc; remote: via ssh <target>)
avail = MemAvailable in GiB          # `free -h` Spalte "available" bzw. /proc/meminfo MemAvailable
                                     # NICHT die "free"-Spalte — buff/cache ist reclaimable
nproc = Kernzahl

# 2) Was wird wirklich GEBAUT (nicht aus Cache geholt)?
nixos-rebuild dry-build …            # System-Rebuild: "would be built / would be fetched"
nix build .#<attr> --dry-run …       # einzelnes Flake-Attribut
nix flake check …                    # KEIN praktikabler Dry-Run über alle Hosts → defensiv als heavy
#   (vollständig lesen — kein tail)

# 3) Wird etwas Schweres gebaut? (dann drosseln; sonst nicht)
heavy/medium = chromium | electron | webkitgtk | qtwebengine | firefox | thunderbird |
               llvm | gcc | rustc | qtbase | linux-kernel | … (große C/C++/Rust-Builds)
light        = kleines Einzelpaket ohne Riesen-Dependency → NICHT drosseln (MJ/CO weglassen)

# 4) Bei heavy/medium: Jobs/Cores als Top-Level-Flags VOR der Aktion
# --max-jobs = RAM-Hebel: ~1 schwerer Job pro 16 GiB available (freier RAM, NICHT MemTotal)
MJ = clamp(floor(avail / 16), 1, nproc)
# --cores = NIX_BUILD_CORES PRO Job (man nix.conf): 15/16 der VERBAUTEN Kerne, abgerundet
CO = clamp(floor(nproc * 15 / 16), 1, nproc)     # 32→30, 20→18, 16→15, 4→3

# anwenden:
nixos-rebuild --max-jobs <MJ> --cores <CO> <aktion> …      # z.B. dry-build/build/switch
nix build .#<attr> --max-jobs <MJ> --cores <CO> …
nix flake check   --max-jobs <MJ> --cores <CO> -L
# bei Remote-Build (--build-host) zählen avail/nproc des Remote-Hosts (via ssh ermittelt)
```

- **`--max-jobs` = RAM-Hebel, `--cores` = CPU-Hebel — zwei getrennte Ressourcen.** `--max-jobs` bestimmt,
  wie viele Derivations *parallel* bauen; jeder Job hält seinen eigenen Heap/Link-Peak → **er** treibt den
  RAM. Basis ist der **freie** RAM (`MemAvailable`, nicht `MemTotal`, nicht die `free`-Spalte): ~1 schwerer
  Job pro 16 GiB available. `free -h` als Preflight vor schweren Builds.
- **`--cores` = NIX_BUILD_CORES pro Job** (`man nix.conf`: „the number of CPU cores to use for **each build
  job**", unabhängig von `--max-jobs`, kein geteilter Pool). Fest auf **15/16 der verbauten Kerne, abgerundet**
  (`floor(nproc*15/16)`): lässt ~1/16 der Kerne fürs Desktop frei, ohne die Builds spürbar zu bremsen. Zwei
  Heavy-Jobs treffen ihren Parallel-Peak selten gleichzeitig → das erzeugt keine Dauer-100-%-Last.
- **Swap zählt nicht als Job-Kapazität** — nur als OOM-Puffer für den einzelnen Link-Peak. Swap-Thrashing
  reißt sonst Timeouts/Checks.
- Drosselung greift **nur**, wenn der Dry-Run schwere/mittlere Pakete als "will be built" zeigt. Ein kleines
  Einzelpaket ohne Riesen-Dependency → keine Drosselung.
- Beispiel (spielkiste: 37 GiB available, 32 Cores, heavy): `--max-jobs = floor(37/16) = 2`,
  `--cores = floor(32*15/16) = 30` → `--max-jobs 2 --cores 30`. Weitere Cores-Stützstellen: 20→18, 16→15, 4→3.

### Empfehlung an den User (dokumentieren, nicht erzwingen)
- Disk-Swap ≈ `min(RAM, 64 GiB)`, `vm.swappiness = 10` — fängt den einzelnen Heavy-Link ab.
- Wiederholt schwere Builds: Build-Host mit viel RAM bevorzugen, oder Cache/Cachix nutzen statt selbst bauen.

## Secure Boot

SPIELKISTE nutzt Lanzaboote (kein systemd-boot). Bei Boot-/Loader-Änderungen dort beachten:
`boot.lanzaboote`, `pkiBundle = /var/lib/sbctl`.

## Bootloader-Diagnose (NVRAM vs. ESP)

- **`bootctl list` „(reported/absent)" ≠ NVRAM.** Das sind flüchtige Einträge aus der `LoaderEntries`-
  EFI-Variable (Snapshot vom letzten Boot), die sich beim nächsten Boot selbst neu schreibt — nichts zum
  Löschen, harmlos. Den **echten** Firmware-Booteintrag immer mit `efibootmgr -v` prüfen, nie aus
  `bootctl`-Zeilen auf NVRAM schließen.
- Echte verwaiste NVRAM-Einträge (z.B. auf einer entfernten/toten Partition) mit `efibootmgr -b <NNNN> -B`
  löschen (`nix run nixpkgs#efibootmgr --` falls nicht im PATH). **Windows-Einträge nur mit Freigabe** —
  Dual-Boot-relevant.
- GC räumt die ESP nicht automatisch — manche Configs lösen das per Auto-Resync-Service am `nix-gc.service`
  (`installBootLoader` als `ExecStartPost`), sonst zieht der nächste `switch`/`boot` die ESP nach.

## Build-Environments

Neue Build-Environments bekommen eine `build.md` (Voraussetzungen, Entwicklungsumgebung, Bauen & Starten,
Testen, Projektspezifisches). Die flake muss `nix flake check`, `nix shell` und `nix run` erfüllen.
