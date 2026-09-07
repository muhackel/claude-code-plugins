---
name: plan
description: "Eine Philharmonie-Mission mit prüfbarer Spec, geklärten Entscheidungen und abgegrenzten Schreibrechten planen."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md` und `skills/planner/SKILL.md`.

Plane das Ziel aus dem Nutzeraufruf. Falls kein Ziel vorliegt, frage danach. Lies vor Rückfragen die vorhandenen Projektquellen. Verteile unabhängige Recherchefragen nach `references/delegation.md` parallel an Agents der eigenen CLI mit begründeter Modellwahl; führe ihre Befunde selbst zusammen. Keine rekursive Delegation.

Lege die Mission mit `new <id> --goal '<Nutzerauftrag>' --planner <claude|codex>` an; der Planer ist die CLI dieser Hauptsitzung. Reiche Spec und Vertrag nach dem Orchestrierungsablauf ein. Vor jeder Umsetzungsfreigabe `review-spec <id> --revision <n>` ausführen; anschließend `status <id> --full` erneut lesen und den registrierten Bericht prüfen. Die Gegenprüfung verwendet die andere CLI.

Zeige den begründeten Score nach `coverage` 25, `verification` 25, `scope` 20, `evidence` 15 und `risks` 15 Punkten. Blocker und offene Fragen getrennt behandeln. Keine Mindestpunktzahl erfinden; offene Blocker verhindern `approve`. Nötige Korrekturen erneut einreichen und gegenprüfen. Der Planungsauftrag allein startet keine Umsetzung. Deckt eine vorhandene Autorisierung die konkrete geprüfte Spec, nach blockerfreiem Review ohne erneute Bestätigungsrunde fortfahren.
