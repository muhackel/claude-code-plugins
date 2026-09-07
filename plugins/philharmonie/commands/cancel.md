---
name: cancel
description: "Eine Philharmonie-Mission abbrechen, aktive Arbeit beenden und Teiländerungen sowie Belege erhalten."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`.

Lies den aktuellen Zustand der im Nutzeraufruf genannten Mission und führe `nix run "path:<root>" -- -C "<projekt>" cancel <id> --revision <n>` aus. Verifiziere anschließend den tatsächlichen Abbruch. Stelle klar, welche Teiländerungen erhalten sind. Kein automatischer Reset, Stash oder Löschen der Mission. Ein späterer neuer Auftrag wird als Folgemission behandelt.
