---
name: run
description: "Eine freigegebene Philharmonie-Mission durch Generator und Evaluator bis zur Abnahmeentscheidung oder einem Hindernis bearbeiten."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`.

Ermittle die Mission aus dem Nutzeraufruf und dem aktuellen Auftrag. Gibt es mehrere passende Missionen, frage nach. Lies `status <id> --full`, die Spec, Entscheidungen und offene Berichte. Starte `nix run "path:<root>" -- -C "<projekt>" run <id> --revision <n>` nur mit der tatsächlich gelesenen Revision und bestehender Autorisierung.

Beobachte laufende Prozesse und gib Fortschrittsmeldungen. Bei `awaiting_acceptance` das Review Briefing vorlegen; bei `blocked` das konkrete Hindernis bearbeiten. Keine zweite Instanz wegen eines Beobachtungs-Timeouts starten.
