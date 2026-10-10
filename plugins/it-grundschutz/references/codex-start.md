# Bruce unter Codex starten

Gilt nur für Codex. `<root>` ist der absolute Plugin-Root, den der Command `/bruce` ermittelt hat. Prüfe,
dass `<root>/agents/bruce.md` existiert.

1. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/bruce.md` und die Dateien unter `skills/` nicht selbst.
2. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben:
   - `<root>/agents/bruce.md` lesen, das Frontmatter ignorieren, den Body als Rollenanweisung befolgen.
     `${CLAUDE_PLUGIN_ROOT}` darin als `<root>` lesen; das gilt vor allem für das Werkzeug `gs`, also
     `nix run "path:<root>#gs" -- <kommando>` und `nix run "path:<root>#ingest"`.
   - Vorgeladene Skills gibt es in Codex nicht: `<root>/skills/gs-lookup/SKILL.md` zu Beginn lesen. Die
     übrigen (`gs-ingest`, `gs-modellierung`, `gs-review`, `gs-dokument`, `gs-crosswalk`, `gs-cache`,
     `gs-krypto`) bei Bedarf per `$it-grundschutz:<name>` oder als Datei `<root>/skills/<name>/SKILL.md`.
   - Danach den User-Text bearbeiten.
