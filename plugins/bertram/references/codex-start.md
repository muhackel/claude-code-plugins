# Bertram unter Codex starten

Gilt nur für Codex. `<root>` ist der absolute Plugin-Root, den der Command `/bertram` ermittelt hat. Prüfe,
dass `<root>/agents/bertram.md` existiert.

1. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/bertram.md` und die Dateien unter `skills/` nicht selbst.
2. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben:
   - `<root>/agents/bertram.md` lesen, das Frontmatter ignorieren, den Body als Rollenanweisung befolgen.
   - Vorgeladene Skills gibt es in Codex nicht: `<root>/skills/net-reference/SKILL.md` zu Beginn lesen.
     `net-diagnose`, `net-config`, `net-design` und `net-operate` bei Bedarf per `$bertram:<name>` oder
     als Datei `<root>/skills/<name>/SKILL.md`.
   - Danach den User-Text bearbeiten.
