---
name: ask
description: "Die jeweils andere CLI (Codex aus Claude Code, Claude aus Codex) non-interaktiv fragen — read-only; ohne Argument Standard-Review des Projekts"
---

Hole eine Zweitmeinung von der jeweils anderen CLI. Modus: **ask** (read-only). Ablauf und
Handover-Format stehen im Skill `handover` dieses Plugins — erst lesen, dann handeln.

1. **Plugin-Root ermitteln.** Unter Claude Code ist er `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert nicht
   mit `/` (Codex ersetzt den Platzhalter nicht), leite den Root aus dem Pfad dieser Skill-Datei ab: das
   Verzeichnis, das `.codex-plugin/` enthält (bei
   `…/.codex-plugin/migrated-command-skills/source-command-ask/SKILL.md` drei Ebenen über der Datei).

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

3. **Ohne Argument:** Skript ohne Handover starten, es liefert das Standard-Review des Projekts:

   ```bash
   bash "<root>/scripts/ask.sh" --mode ask --tier advanced </dev/null
   ```

   **Mit Argument** (`$ARGUMENTS`): Handover nach dem Skill-Format schreiben und per Heredoc auf stdin geben:

   ```bash
   bash "<root>/scripts/ask.sh" --mode ask --tier <klasse> <<'HANDOVER'
   # Handover
   …
   HANDOVER
   ```

4. **Unter Codex** den Aufruf mit `require_escalated` starten: `claude -p` braucht Netz, das die
   Codex-Sandbox standardmäßig sperrt. Unter Claude Code läuft der Aufruf normal per Bash.
   Das Skript ermittelt die Ziel-CLI selbst und wählt das Modell nach der Klasse; der Aufruf dauert je nach Umfang mehrere Minuten,
   Timeout großzügig setzen.

5. **Ergebnis wiedergeben:** stdout ist die Antwort der anderen CLI, stderr der Fortschritt. Die Antwort
   **unverändert** ausgeben, danach in wenigen Sätzen einordnen: wo du zustimmst, wo du widersprichst,
   was du übernimmst. Nicht umschreiben, nicht kürzen.
