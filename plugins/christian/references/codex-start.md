# Christian unter Codex starten

Gilt nur für Codex. `<root>` ist der absolute Plugin-Root, den der Command `/christian` ermittelt hat.
Prüfe, dass `<root>/agents/christian.md` existiert.

1. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/christian.md` und die Dateien unter `skills/` nicht selbst.
2. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben:
   - `<root>/agents/christian.md` lesen, das Frontmatter ignorieren, den Body als Rollenanweisung befolgen.
   - Vorgeladene Skills gibt es in Codex nicht: `<root>/skills/vpn-reference/SKILL.md` und
     `<root>/skills/vpn-tunnel/SKILL.md` zu Beginn lesen. `openvpn`, `router-appliance`, `bsd-firewall`
     und `wan-link` bei Bedarf per `$christian:<name>` oder als Datei `<root>/skills/<name>/SKILL.md`.
   - Referenzdateien (`references/*.md`) relativ zur jeweiligen `SKILL.md` auflösen.
   - Danach den User-Text bearbeiten.
