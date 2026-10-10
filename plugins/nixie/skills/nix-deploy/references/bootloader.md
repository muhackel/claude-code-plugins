# Secure Boot und Bootloader-Diagnose

Referenz zu `nix-deploy`, lesen vor Arbeiten an Bootloader, ESP oder NVRAM-Einträgen.

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

