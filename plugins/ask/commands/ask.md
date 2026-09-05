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

2. **Ohne Argument:** Skript ohne Handover starten, es liefert das Standard-Review des Projekts:

   ```bash
   bash "<root>/scripts/ask.sh" --mode ask </dev/null
   ```

   **Mit Argument** (`$ARGUMENTS`): Handover nach dem Skill-Format schreiben und per Heredoc auf stdin geben:

   ```bash
   bash "<root>/scripts/ask.sh" --mode ask <<'HANDOVER'
   # Handover
   …
   HANDOVER
   ```

3. **Unter Codex** den Aufruf mit `require_escalated` starten: `claude -p` braucht Netz, das die
   Codex-Sandbox standardmäßig sperrt. Unter Claude Code läuft der Aufruf normal per Bash.
   Das Skript ermittelt Ziel-CLI und Flaggschiffmodell selbst; der Aufruf dauert je nach Umfang mehrere Minuten,
   Timeout großzügig setzen.

4. **Ergebnis wiedergeben:** stdout ist die Antwort der anderen CLI, stderr der Fortschritt. Die Antwort
   **unverändert** ausgeben, danach in wenigen Sätzen einordnen: wo du zustimmst, wo du widersprichst,
   was du übernimmst. Nicht umschreiben, nicht kürzen.
