---
name: nix-docs
description: "Doku-Lookup-Disziplin für Nix/NixOS: NixOS-Optionen (search.nixos.org), lib-Funktionen (noogle.dev), Pakete (nix search), Manpages (man configuration.nix / home-configuration.nix) und nixpkgs-Source lesen — statt zu raten. Nutzen, bevor eine unbekannte Option/Funktion/ein Paket verwendet wird. Recherche macht Nixie selbst; ein Wissensmanagement-Agent ist optional."
---

# Nix-Docs — Nachschlagen statt raten

**Docs-first ist Pflicht.** Bevor eine Option, lib-Funktion oder ein Paket verwendet wird, dessen genaues
Verhalten/Signatur unklar ist: nachschlagen. Keine erfundenen Optionsnamen, keine geratenen Argumente.

## Werkzeuge nach Frage

| Frage | Werkzeug |
|-------|----------|
| NixOS-Option (Name, Typ, Default, Beschreibung) | `search.nixos.org/options` (WebFetch) · `nixos-option <pfad>` auf dem System |
| Paket existiert / Attribut-Name | `nix search nixpkgs <begriff>` (vollständig lesen) · `search.nixos.org/packages` |
| lib-Funktion (Signatur, Beispiele) | `noogle.dev` (WebFetch) · nixpkgs `lib/`-Source lesen |
| Modul-/Option-Doku offline | `man configuration.nix`, `man home-configuration.nix` |
| Flakes-Befehle/Optionen | `man nix3-<cmd>` (z.B. `man nix3-build`), `nix <cmd> --help` |
| Genaues Build-/Phasen-Verhalten | nixpkgs-Source der Derivation lesen (Glob/Grep im nixpkgs-Checkout) |
| `manix`/`nix-doc` falls installiert | schneller lokaler Volltext-Lookup über Optionen/Kommentare |

Tools nur einsetzen, wenn sie in der Nix-Umgebung verfügbar sind — nicht als systemweit installiert annehmen.

## Workflow

1. Frage präzisieren (welche Option/Funktion/welches Paket genau?).
2. Passendstes Werkzeug oben wählen; Ergebnis **vollständig** lesen (kein `tail`).
3. Bei Optionen: Name, Typ, Default und Beschreibung notieren, bevor sie gesetzt wird.
4. Im Zweifel die nixpkgs-Source als Ground Truth heranziehen.

## Recherche: standalone, Wissensmanagement optional

- **Standard — Nixie selbst:** alle Lookups und auch längere Recherche mit den eigenen Werkzeugen. Eine
  Wissensdatenbank wird nicht vorausgesetzt.
- **Optional an einen Wissensmanagement-Agenten geben** (z.B. Karin / `bibliothekarin`, falls installiert):
  bei längerer, mehrquelliger Recherche oder wenn das Ergebnis in einer Knowledge Base dokumentiert werden
  soll. Dann ein knappes Briefing (Frage, bisheriger Stand, gewünschtes Ergebnis) schreiben und dem
  Hauptagenten empfehlen, ihn zu spawnen (`bibliothekarin:bibliothekarin-search` für Recherche/Synthese,
  `bibliothekarin:bibliothekarin` zum Einpflegen). Nixie startet ihn nicht selbst.
- **Kein solcher Agent verfügbar:** kein Sonderfall — Recherche vollständig selbst erledigen.

Hat die Config-Root eine `CLAUDE.md` oder eine begleitende Knowledge Base, sind dort oft bekannte
Build-Probleme dokumentiert — dort zuerst schauen.
