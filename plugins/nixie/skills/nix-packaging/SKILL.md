---
name: nix-packaging
description: "Eigene Nix-Pakete schreiben (stdenv.mkDerivation, buildNpmPackage, stdenvNoCC, callPackage), Overlays anlegen (final: prev:), und lang bauende Pakete pinnen (nixpkgs-Rev, fetchFromGitHub, Binary-Cache/Cachix). Nutzen, wenn eine Derivation/ein Overlay geschrieben, ein Paket gepatcht oder gegen lange Build-Zeiten gepinnt werden soll."
---

# Nix-Packaging — Derivations, Overlays, Pinning

Vorbilder im Repo: `packages/` (eigene Derivations) und `overlays/` (Patches/Pins). Bestehende Muster
fortführen.

## Eigene Derivations (`packages/<name>/default.nix`)

Signatur als callPackage-fähige Funktion, eingebunden via `(callPackage ../../../packages/<name> {})`.

- **Dateien installieren / kein Build** — `stdenv.mkDerivation` mit no-op `buildPhase` und `installPhase`
  (Muster: `packages/gns3extras/default.nix`).
- **npm-Pakete** — `buildNpmPackage` mit eigener `package-lock.json` und `npmDepsHash` (Muster:
  `packages/mcpvault/`).
- **Nur Dateien, kein Compiler nötig** — `stdenvNoCC.mkDerivation` (Muster:
  `packages/pipewire-deepfilternet/`).
- `meta` mit `description` und `platforms` setzen.

## Overlays (`overlays/<name>/`)

Standardform — Funktion `final: prev:`:
```nix
final: prev: {
  paket = prev.paket.overrideAttrs (old: {
    # Patch, Flag, Source-Override …
  });
}
```
- Import in `configuration.nix` (zentral). Ein Overlay **pro Workaround-Paket** — leicht ein-/auszuschalten.
- **Jedes Overlay mit Kommentarblock dokumentieren:** Was, Warum, **Deaktivierungsbedingung** ("Entfernen
  wenn nixpkgs X enthält"). Beispiele in der `CLAUDE.md` der Config-Root (bubblewrap-setuid, ts3-legacy, …).
- Entscheidung Overlay vs. eigenes Paket: kleine Anpassung an einem bestehenden nixpkgs-Paket → Overlay;
  komplett eigenes Artefakt → `packages/`.

## Pinning lang bauender Pakete

Ziel: nicht stundenlang selbst bauen. Optionen in Reihenfolge der Präferenz:

1. **Binary-Cache nutzen statt bauen.** Erst prüfen, ob das Paket im Cache liegt
   (`nix path-info --eval-store auto --store https://cache.nixos.org <drv>` bzw. `nix build --dry-run` zeigt
   "will be fetched" vs. "will be built"). Wenn Cache da: nichts pinnen, einfach bauen lassen. Ggf.
   passenden Cachix-Substituter ergänzen (in `nixConfig`/`nix.settings.substituters` + trusted-public-keys).
2. **Auf eine bekannte gute nixpkgs-Revision pinnen** — separater Flake-Input bzw. Overlay, das das Paket aus
   einem gepinnten nixpkgs zieht (Muster ts3-legacy: Qt-Stack aus älterer nixpkgs-Version). So bleibt das
   restliche System auf unstable, nur das teure Paket ist eingefroren.
3. **Quelle pinnen** via `fetchFromGitHub { owner; repo; rev; hash; }` in einer eigenen Derivation/Override,
   wenn eine bestimmte Version/Build-Variante gewünscht ist.

Pins genauso dokumentieren wie Overlays (Kommentarblock + Auflösungsbedingung).

## Verifikation

- Einzeln bauen: `nix build .#<attr>` bzw. `nix-build -A <attr>` — **vollständige Ausgabe**, kein `tail`.
- Bei schweren Paketen vor dem Build die resource-aware Drosselung aus dem `nix-deploy`-Skill anwenden.
- Abschluss immer mit vollständigem `nix flake check`.
