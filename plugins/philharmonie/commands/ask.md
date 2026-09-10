---
name: ask
description: "Mit Philharmonie die andere CLI lesend fragen; ohne Frage ein Standard-Review des Projekts erhalten."
---

Ermittle den Plugin-Root aus dem Pfad dieser Datei: das übergeordnete Verzeichnis mit `.codex-plugin/` oder `.claude-plugin/`. Das gilt auch für migrierte Codex-Commands; `${CLAUDE_PLUGIN_ROOT}` nur verwenden, wenn es ein tatsächlich ersetzter absoluter Pfad ist.

Lies dort `skills/orchestration/SKILL.md`, Abschnitt „Einzelauftrag“ — dort steht auch, wie die Aufgabenklasse `--tier` gewählt wird. Übernimm die Frage aus dem Nutzeraufruf. Ohne Frage starte `nix run "path:<root>" -- -C "<projekt>" ask </dev/null`. Mit Frage ein vollständiges Handover schreiben und mit `ask --handover <datei>` übergeben.

Die Antwort unverändert wiedergeben und danach knapp einordnen. Ein Review erteilt keine Änderungsfreigabe.
