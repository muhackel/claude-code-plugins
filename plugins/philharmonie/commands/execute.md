---
name: execute
description: "Mit Philharmonie einen begrenzten Schreibauftrag an die andere CLI delegieren; Auftrag und Schreibpfade sind erforderlich."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`, Abschnitt „Einzelauftrag“ — dort steht auch, wie die Aufgabenklasse `--tier` gewählt wird.

Übernimm den konkreten Auftrag aus dem Nutzeraufruf. Fehlt er, frage nach. Lies Projektregeln, Branch und vorhandene Änderungen. Leite die Schreibpfade aus dem autorisierten Auftrag ab; fremde Änderungen erhalten. Schreibe ein Handover und starte `nix run "path:<root>" -- -C "<projekt>" execute --handover <datei> --allow <pfad>`. Weitere erlaubte Pfade jeweils mit `--allow` ergänzen; vorhandene zugehörige Änderungen mit `--include-dirty <datei>` ausdrücklich zuordnen.

Prüfe anschließend die tatsächlich übernommenen Änderungen. Gib die Antwort unverändert wieder und ordne sie kurz ein. Commit, Push und Deployment benötigen einen entsprechenden Auftrag.
