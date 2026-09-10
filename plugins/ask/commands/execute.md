---
name: execute
description: "Die jeweils andere CLI (Codex aus Claude Code, Claude aus Codex) non-interaktiv einen Auftrag im Workspace ausführen lassen — workspace-write, Auftrag ist Pflicht"
---

Lasse die jeweils andere CLI einen Auftrag ausführen. Modus: **execute** (workspace-write). Ablauf und
Handover-Format stehen im Skill `handover` dieses Plugins — erst lesen, dann handeln.

1. **Auftrag prüfen.** Ohne Argument gibt es kein Standard-Verhalten: nachfragen, was ausgeführt werden soll.
   Vor dem Start `git status --short` prüfen. Auf `main`/`master` oder bei uncommitted Changes, die nicht
   zum Auftrag gehören, erst beim User rückfragen (Feature-Branch oder Stash), dann starten.

2. **Aufgabenklasse wählen.** Das Skript wählt das Modell nach Aufgabenklasse, nicht
   pauschal das Flaggschiff. Schätze die Aufgabe ein und übergib sie mit `--tier`:

   | Klasse | Wofür | Claude | Codex |
   |---|---|---|---|
   | `light` | eindeutige Kleinarbeit: String fixen, Datei finden, Formatierung | haiku | luna |
   | `standard` | einzelnes Modul, Test schreiben, lokale Fehleranalyse | sonnet | terra |
   | `advanced` | mehrere Module, Refactoring, schwere Fehlersuche, Projekt-Review | opus | sol |
   | `strong` | Architektur, widersprüchliche Anforderungen, Planung | fable | astra |

   Ohne `--tier` gilt `advanced` beim Standard-Review und sonst `standard`. Im Zweifel die kleinere Klasse:
   eine zu schwache Antwort erkennst du am Ergebnis, verbranntes Budget nicht. Bei wirklich harten Aufgaben
   lohnt sich `strong` eher für einen Plan, den du anschließend in `standard` ausführen lässt, als für die
   Umsetzung selbst.

3. **Plugin-Root ermitteln.** Unter Claude Code `${CLAUDE_PLUGIN_ROOT}`. Beginnt der Wert nicht mit `/`
   (Codex ersetzt den Platzhalter nicht), Root aus dem Pfad dieser Skill-Datei ableiten: das Verzeichnis,
   das `.codex-plugin/` enthält (drei Ebenen über `source-command-execute/SKILL.md`).

4. **Handover schreiben** (Skill-Format, Abschnitt „Grenzen" mit: nur im Workspace ändern, kein Commit,
   kein Push, Änderungsliste am Ende) und per Heredoc starten:

   ```bash
   bash "<root>/scripts/ask.sh" --mode execute --tier <klasse> <<'HANDOVER'
   # Handover
   …
   HANDOVER
   ```

   Unter Codex mit `require_escalated` (Netz für `claude -p`). Der Lauf kann lange dauern, Timeout großzügig setzen.

5. **Ergebnis wiedergeben:** Antwort der anderen CLI (stdout) **unverändert** ausgeben, danach
   `git status --short` und `git diff --stat` zeigen und in wenigen Sätzen bewerten, ob die Änderungen
   dem Auftrag entsprechen. Commit und Push bleiben beim User.
