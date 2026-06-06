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

## `nix flake check` — Regel

**Immer vollständig laufen lassen.** Niemals nach `| tail`, `| head` oder `2>/dev/null` pipen — das versteckt
genau die Fehler, die geprüft werden sollen. Volle Ausgabe lesen und auswerten. Läuft vor jeder
Fertigstellung einer Änderung. Bei vielen Checks ggf. `--keep-going`, um alle Fehler auf einmal zu sehen.

## nixos-rebuild (ng) — CLI-Form

Aktueller `nixos-rebuild` ist die ng-Variante (Python-Rewrite). Wichtig:
- **Aktion ist ein positionaler Subcommand:** `switch | boot | test | build | dry-build | dry-activate |
  build-vm | build-image | list-generations | repl | edit`. Den **echten Dry-Run** für „was würde gebaut/
  geladen" liefert `dry-build` (nicht mehr `--dry-run`).
- **Nix-Build-Flags stehen VOR der Aktion:** `nixos-rebuild --max-jobs N --cores M <aktion>`
  (auch `--keep-going`, `--option …`).
- **Aktivierung als Nicht-Root:** `--sudo` (lokal) bzw. `-S`/`--ask-sudo-password` (fragt Sudo-Passwort,
  nötig für Remote-Aktivierung via `--target-host`).
- **Host-Flags:** `--build-host user@host` (Kompilation dort), `--target-host user@host` (Aktivierung dort);
  beide nehmen einen ssh-erreichbaren Host, SSH-Optionen via `NIX_SSHOPTS`. `--use-substitutes`, wenn der
  Ziel-/Build-Host schneller am Cache hängt als die Hosts untereinander.
- **Flake-Auswahl:** `--flake .#<host>` (sonst Auto-Erkennung über Hostname).

## Eskalationsstufen (Default = niedrigste)

Die erlaubte Stufe ergibt sich aus der **konkreten Anfrage** des Users — nicht eigenmächtig eskalieren:

1. **check / build (Default):** `nix flake check`, `nixos-rebuild dry-build`, `nixos-rebuild build`,
   `nix build .#…`. Ändert nichts am Live-System.
2. **Lokaler switch:** `nixos-rebuild switch --sudo [--flake .#<host>]` — nur wenn explizit verlangt.
   Vorher ansagen.
3. **Remote-Build:** `nixos-rebuild switch --sudo --build-host user@<fast>` — Kompilation auf der schnellen
   Kiste, Aktivierung lokal.
4. **Remote-Deploy:** `nixos-rebuild switch --build-host user@<fast> --target-host user@<ziel> -S
   [--use-substitutes] --flake .#<ziel>` — baut auf der schnellen Kiste, aktiviert auf einem anderen Host.
   Nur auf explizite Anweisung; Ziel-Host vorher nennen und bestätigen lassen.

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

Schwere C++/Rust-Builds (v.a. parallel) sprengen RAM. Vorgehen:

```
# 1) Werte des Build-Hosts (lokal: /proc/meminfo & nproc; remote: via ssh <target>)
mem   = MemTotal in GiB
nproc = Kernzahl

# 2) Was wird wirklich GEBAUT (nicht aus Cache geholt)?
nixos-rebuild dry-build …            # System-Rebuild: "would be built / would be fetched"
nix build .#<attr> --dry-run …       # einzelnes Flake-Attribut
#   (vollständig lesen — kein tail)

# 3) Schwerste Klasse in der Build-Liste bestimmen
heavy  = chromium | electron | webkitgtk | qtwebengine | firefox | thunderbird | spidermonkey | …
medium = llvm | gcc | rustc | qtbase | webkit | linux-kernel | … (große C/C++/Rust)
light  = alles andere

# 4) Jobs/Cores setzen — als Top-Level-Flags VOR der Aktion
heavy  → MJ = clamp(floor(mem / 24), 1, nproc)      # Swap NICHT mitzählen
         CO = clamp(floor(nproc / MJ), 4, nproc)
medium → MJ = clamp(floor(mem / 6),  1, nproc)
         CO = clamp(floor(nproc / MJ), 4, nproc)
light  → keine Drosselung (MJ/CO weglassen)

# anwenden:
nixos-rebuild --max-jobs <MJ> --cores <CO> <aktion> …      # z.B. dry-build/build/switch
nix build .#<attr> --max-jobs <MJ> --cores <CO> …
# bei Remote-Build (--build-host) zählen mem/nproc des Remote-Hosts (via ssh ermittelt)
```

- **Swap zählt nicht als Job-Kapazität** — nur als OOM-Puffer für den einzelnen Link-Peak. Swap-Thrashing
  reisst sonst Timeouts/Checks.
- Drosselung greift **nur**, wenn der Dry-Run schwere/mittlere Pakete als "will be built" zeigt. Ein kleines
  Einzelpaket ohne Riesen-Dependency → keine Drosselung.
- Beispiel (128 GiB RAM, heavy): `--max-jobs = floor(128/24) = 5`.

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
