---
name: pause
description: "Weitere Arbeit an einer Philharmonie-Mission stoppen und einen laufenden Auftrag kontrolliert anhalten."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`.

Lies den aktuellen Zustand der im Nutzeraufruf genannten Mission und führe `nix run "path:<root>" -- -C "<projekt>" pause <id> --revision <n>` aus. Verfolge `status`, bis die Aktivität tatsächlich `paused` ist. Falls der Supervisor bereits beendet ist, über die dokumentierte Wiederaufnahmeprüfung den Prozesszustand klären. Keine Teiländerungen zurücksetzen.
