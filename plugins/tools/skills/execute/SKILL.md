---
name: execute
description: "Die jeweils andere CLI (Codex aus Claude Code, Claude aus Codex) non-interaktiv einen Auftrag im Workspace ausführen lassen — workspace-write, Auftrag ist Pflicht"
disable-model-invocation: true
---

Lasse die jeweils andere CLI einen Auftrag ausführen. Modus: **execute** (workspace-write). Ablauf und
Handover-Format stehen in `references/handover.md` im Plugin-Root — erst lesen, dann handeln.

1. **Auftrag prüfen.** Ohne Argument gibt es kein Standard-Verhalten: nachfragen, was ausgeführt werden soll.
   Vor dem Start `git status --short` prüfen. Auf `main`/`master` oder bei uncommitted Changes, die nicht
   zum Auftrag gehören, erst beim User rückfragen (Feature-Branch oder Stash), dann starten.

2. **Stufe wählen.** Das Skript wählt Modell und Effort nach Stufe, nicht pauschal das Flaggschiff.
   Schätze die Aufgabe ein und übergib sie mit `--tier`:

   | Stufe | Wofür | Claude | Codex | Effort | `--boost` | `--fast` |
   |---|---|---|---|---|---|---|
   | `drone` | mechanische Umsetzung nach klarem, vollständigem Auftrag | sonnet | luna | high | – | – |
   | `advanced` | Umsetzung mit Entscheidungsspielraum, Refactoring, Fehlersuche (Default) | opus | sol | high | xhigh | – |
   | `strong` | Architektur, widersprüchliche Anforderungen, Planung | fable | astra | medium | high | low |

   Ohne `--tier` gilt `advanced`. `drone` ist ein bewusstes „das ist wirklich mechanisch": der Auftrag muss
   dann alles vorgeben, das Modell entscheidet nichts. Bei wirklich harten Aufgaben lohnt `strong` eher
   für einen Plan (`/tools:ask`), den du anschließend in `advanced` ausführen lässt. `--model <alias|slug>`
   und `--effort low|medium|high|xhigh|max` setzen Modell und Effort frei (bei `--model` ist der Effort
   high) — nur, wenn der User es ausdrücklich so verlangt.

3. **Plugin-Root ermitteln.** Unter Claude Code `${CLAUDE_PLUGIN_ROOT}`. Beginnt der Wert nicht mit `/`
   (Codex ersetzt den Platzhalter nicht), Root aus dem Pfad dieser Skill-Datei ableiten: das Verzeichnis,
   das `.codex-plugin/` enthält (bei `…/skills/execute/SKILL.md` zwei Ebenen über dem Skill-Verzeichnis).

4. **Handover schreiben** (Format aus `references/handover.md`, Abschnitt „Grenzen" mit: nur im Workspace
   ändern, kein Commit, kein Push, Änderungsliste am Ende) und per Heredoc starten:

   ```bash
   bash "<root>/scripts/ask.sh" --mode execute --tier <stufe> [--boost|--fast] <<'HANDOVER'
   # Handover
   …
   HANDOVER
   ```

   Unter Codex mit `require_escalated` (Netz für `claude -p`). Der Lauf kann lange dauern, Timeout großzügig setzen.

5. **Ergebnis wiedergeben:** Antwort der anderen CLI (stdout) **unverändert** ausgeben, danach
   `git status --short` und `git diff --stat` zeigen und in wenigen Sätzen bewerten, ob die Änderungen
   dem Auftrag entsprechen. Commit und Push bleiben beim User.
