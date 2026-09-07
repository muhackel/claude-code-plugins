---
name: status
description: "Phase, Aktivität, Revision und offene Hindernisse einer Philharmonie-Mission anzeigen."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`.

Rufe `nix run "path:<root>" -- -C "<projekt>" status` auf. Mit einer im Nutzeraufruf genannten Mission stattdessen `status <id> --full` verwenden. Berichte den fachlichen Stand, einen tatsächlich laufenden Auftrag oder das konkrete Hindernis und die nächste notwendige Handlung. Ein gespeichertes `running` allein beweist keinen lebenden Prozess; bei Zweifel über den Resume-Ablauf prüfen.
