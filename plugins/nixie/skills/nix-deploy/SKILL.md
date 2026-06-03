---
name: nix-deploy
description: "Bauen und Deployen von NixOS: Build-Host dynamisch wählen (Host-Config aus CLAUDE.md oder ~/.config/nixie/hosts.conf, schnellste erreichbare Kiste), resource-aware Drosselung von --max-jobs/--cores gegen OOM bei schweren Builds, nix flake check ohne Truncation, Eskalationsstufen check → build → switch → Remote-Deploy. Nutzen bei nix flake check, nixos-rebuild, Remote-Builds oder Deploy auf andere Hosts."
---

# Nix-Deploy — Bauen, Build-Hosts, Deploy

## `nix flake check` — Regel

**Immer vollständig laufen lassen.** Niemals nach `| tail`, `| head` oder `2>/dev/null` pipen — das versteckt
genau die Fehler, die geprüft werden sollen. Volle Ausgabe lesen und auswerten. Läuft vor jeder
Fertigstellung einer Änderung. Bei vielen Checks ggf. `--keep-going`, um alle Fehler auf einmal zu sehen.

## Eskalationsstufen (Default = niedrigste)

Die erlaubte Stufe ergibt sich aus der **konkreten Anfrage** des Users — nicht eigenmächtig eskalieren:

1. **check / build (Default):** `nix flake check`, `nixos-rebuild build`/`dry-build`, `nix build .#…`.
   Ändert nichts am Live-System.
2. **Lokaler switch:** `nixos-rebuild switch --sudo` — nur wenn explizit verlangt. Vorher ansagen.
3. **Remote-Build:** `nixos-rebuild … --build-host <host>` — Kompilation auf der schnellen Kiste, Aktivierung
   lokal.
4. **Remote-Deploy:** `nixos-rebuild … --target-host <host> [--build-host <host>]` — baut (auf der schnellen
   Kiste) und aktiviert auf einem anderen Host. Nur auf explizite Anweisung; Ziel-Host vorher nennen und
   bestätigen lassen.

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
nix build --dry-run … / nixos-rebuild build --dry-run …   → Liste "will be built"
#   (vollständig lesen — kein tail)

# 3) Schwerste Klasse in der Build-Liste bestimmen
heavy  = chromium | electron | webkitgtk | qtwebengine | firefox | thunderbird | spidermonkey | …
medium = llvm | gcc | rustc | qtbase | webkit | linux-kernel | … (große C/C++/Rust)
light  = alles andere

# 4) Jobs/Cores setzen
heavy  → --max-jobs = clamp(floor(mem / 24), 1, nproc)      # Swap NICHT mitzählen
         --cores   = clamp(floor(nproc / max-jobs), 4, nproc)
medium → --max-jobs = clamp(floor(mem / 6),  1, nproc)
         --cores   = clamp(floor(nproc / max-jobs), 4, nproc)
light  → keine Drosselung: --max-jobs auto, --cores 0
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

## Build-Environments

Neue Build-Environments bekommen eine `build.md` (Voraussetzungen, Entwicklungsumgebung, Bauen & Starten,
Testen, Projektspezifisches). Die flake muss `nix flake check`, `nix shell` und `nix run` erfüllen.
