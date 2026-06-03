---
name: nixos-config
description: "Konventionen und Patterns der NixOS-Konfiguration des Users (Multi-Host-Flake): mkHost-Helper, Feature-Flags unter local.features, Modul-Layout (host/hardware/software), userExtraGroups-Sammelpattern, Home-Manager. Nutzen, wenn an dieser oder einer ähnlich strukturierten NixOS-Config gearbeitet wird — Host/Modul/Feature-Flag hinzufügen, Option setzen, Paket einbauen."
---

# NixOS-Config — Konventionen & Patterns

Gilt für die NixOS-Config-Root, die Nixie zur Laufzeit auflöst (lokales Verzeichnis, sonst `/etc/nixos/` —
siehe Agent-STARTUP). Der User pflegt sie als Multi-Host-Flake. **Hat die Config-Root eine eigene
`CLAUDE.md`, ist diese das verbindliche Regelwerk** — zuerst lesen; bei Konflikt gewinnt sie. Diese Skill
fasst die typischen Patterns zusammen und gibt Rezepte. Pfade unten sind **relativ zur Config-Root**.

## Architektur (verbindliche Quellen)

- `flake.nix` — Einstiegspunkt, definiert `nixosConfigurations` (via `mkHost`) und `checks`. Inputs:
  nixpkgs (nixos-unstable), home-manager, lanzaboote, claude-desktop.
- `lib/default.nix` — der `mkHost`-Helper und die `commonModules`-Liste (alle Hosts gemeinsam).
- `configuration.nix` — gemeinsame Basis (Overlays-Import, Nix-Settings, GC, SSH, Activation Scripts).
- `modules/options.nix` — Feature-Flags (`local.features.*`) und `local.userExtraGroups`.
- `modules/host/<NAME>/` — Host-Entry (hostName, hostId, Hardware-Imports).
- `modules/hardware/<NAME>/` — GPU/Boot/Kernel-Spezifika.
- `modules/software/<bereich>/` — Feature-Module, reagieren auf `config.local.features.<flag>`.
- `modules/user/muhackel/` — User + Home Manager (`home.nix`).
- `overlays/`, `packages/` — siehe `nix-packaging`-Skill.

### Hosts

| Host | Rolle | Hardware | GPU | Besonderheit |
|------|-------|----------|-----|--------------|
| SPIELKISTE | Hauptrechner/Gaming | Framework Desktop | AMD RDNA | Lanzaboote Secure Boot |
| HAL9000 | Notebook | ThinkPad 25 | Nvidia Optimus (legacy_580) | Undervolting, NFC, Autorandr/EDID |
| BFG9000 | Arbeitslaptop | X1 Extreme G3 | Nvidia Optimus (open) | 4K-Skalierung, kein Hamradio |
| datengrab | Heimserver (WIP) | — | — | ZFS, *arr — noch nicht in flake.nix |

## mkHost-Pattern (`lib/default.nix`)

```nix
mkHost = { hostModule, stateVersion ? "26.05", features, extraModules ? [] }:
  lib.nixosSystem {
    modules = [
      { system.stateVersion = stateVersion;
        local.features = features;
        nixpkgs.hostPlatform = "x86_64-linux"; }
      hostModule
    ] ++ extraModules ++ commonModules;
  };
```

- `stateVersion` Default `26.05` — **nicht ändern ohne guten Grund**.
- Hosts werden in `flake.nix` über `commonFeatures` konfiguriert; einzelne Hosts überschreiben mit
  `commonFeatures // { hamradio = false; }`.
- `extraModules` nur für Sonderfälle (z.B. Lanzaboote bei SPIELKISTE).

## Feature-Flag-Pattern

Flag deklarieren in `modules/options.nix`:
```nix
options.local.features.<name> = lib.mkEnableOption "<beschreibung>";
```
Im zugehörigen Modul darauf reagieren — **`lib.mkIf`, kein Top-Level if-then-else**:
```nix
{ config, lib, pkgs, ... }:
let cfg = config.local.features;
in lib.mkIf cfg.<name> {
  environment.systemPackages = with pkgs; [ ... ];
}
```

## userExtraGroups-Sammelpattern

Gruppen **nicht** direkt am User setzen — Feature-Module tragen bei, der User sammelt zentral:
```nix
# im Feature-Modul:
local.userExtraGroups = [ "wireshark" ];
# in modules/user/muhackel/default.nix:
extraGroups = lib.unique (baseGroups ++ config.local.userExtraGroups);
```

## Rezepte

### Feature-Flag + Modul anlegen
1. Flag in `modules/options.nix` deklarieren (`lib.mkEnableOption`).
2. Modul unter `modules/software/<bereich>/` mit Signatur `{ config, lib, pkgs, ... }:` und `lib.mkIf`.
3. Modul in `commonModules` (`lib/default.nix`) eintragen, falls nicht schon ein Sammelmodul es importiert.
4. Flag in `flake.nix` (commonFeatures / Host-Override) setzen.
5. `nix flake check` (vollständig, siehe `nix-deploy`).

### Paket zu den Applications hinzufügen
- In der passenden Liste in `modules/software/applications/default.nix` ergänzen (benannte `let`-Listen mit
  `with pkgs;`, dann zusammengeführt). Lokale Derivation via `(callPackage ../../../packages/<name> {})`.

### Host hinzufügen
1. `modules/host/<NAME>/default.nix` (hostName, hostId — bewusst `DEADBEEF` bei Desktops für ZFS-Portabilität)
   und Hardware-Import unter `modules/hardware/<NAME>/`.
2. Eintrag in `flake.nix` via `mkHost { hostModule = ...; features = ...; }`.
3. `checks` für den Host (`system.build.toplevel`) sicherstellen.

## Stil

- Modul-Signatur immer `{ config, lib, pkgs, ... }:`.
- `lib.mkIf` / `lib.mkMerge` statt verschachteltem `if-then-else` auf Top-Level.
- Paketlisten als benannte Listen in `let`, dann `++`-zusammenführen.
- Keine unnötigen Kommentare; bestehende Patterns fortführen statt neue einzuführen.
