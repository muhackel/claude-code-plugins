# Nixie unter Codex starten

Gilt nur für Codex. `<root>` ist der absolute Plugin-Root, den der Command `/nixie` ermittelt hat. Prüfe,
dass `<root>/agents/nixie.md` existiert.

1. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/nixie.md` und die Dateien unter `skills/` nicht selbst.
2. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben:
   - `<root>/agents/nixie.md` lesen, das Frontmatter ignorieren, den Body als Rollenanweisung befolgen.
   - Vorgeladene Skills gibt es in Codex nicht: `<root>/skills/nix-docs/SKILL.md` und
     `<root>/skills/nixos-config/SKILL.md` zu Beginn lesen. `nix-packaging` und `nix-deploy` bei Bedarf per
     `$nixie:nix-packaging` bzw. `$nixie:nix-deploy` oder als Datei `<root>/skills/<name>/SKILL.md`.
   - Referenzdateien (`references/*.md`) relativ zur jeweiligen `SKILL.md` auflösen.
   - Danach den User-Text bearbeiten.
