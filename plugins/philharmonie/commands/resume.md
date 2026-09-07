---
name: resume
description: "Eine Philharmonie-Mission nach Sitzungswechsel, Pause oder behobenem Hindernis am belegten Stand fortsetzen."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`, insbesondere „Korrektur und Wiederaufnahme“.

Bestimme die Mission aus dem Nutzeraufruf. Lies Zustand, Spec, aktuelle Projektregeln, offene Berichte und Git-Änderungen. Prüfe bei einem unterbrochenen Schreibauftrag auch `apply.json` und erhaltene Snapshots.

Starte `nix run "path:<root>" -- -C "<projekt>" resume <id> --revision <n>`. Bei einem tatsächlich beseitigten Hindernis `--resolution '<Beleg>'` ergänzen. Eine Budgeterweiterung benötigt eine Nutzeranweisung und `--extra-rounds <anzahl>`. Lebt der ursprüngliche Prozess noch, weiter beobachten und keinen zweiten starten.
