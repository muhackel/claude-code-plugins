---
name: review-spec
description: "Eine vorgelegte Philharmonie-Spec durch die andere CLI gegenprüfen und begründeten Score, Blocker sowie offene Fragen vor der Freigabe auswerten."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`, Abschnitt „Mission planen“.

Bestimme die Mission aus dem Nutzeraufruf. Lies `status <id> --full`, Spec und Vertrag. Führe `nix run "path:<root>" -- -C "<projekt>" review-spec <id> --revision <n>` mit der gelesenen Zustandsrevision aus. Die Laufzeit benötigt `awaiting_spec` und `activity=idle` und wählt die andere CLI gegenüber dem gespeicherten Planer. Bei einer Altmission ohne Zuordnung nur die belegte Planer-CLI mit `--planner <claude|codex>` ergänzen.

Lies nach Abschluss `status <id> --full` erneut und den registrierten Reviewbericht. Stelle Score und Begründungen nach `coverage` 25, `verification` 25, `scope` 20, `evidence` 15 und `risks` 15 Punkten dar. Führe Blocker und offene Fragen getrennt auf. Es gibt keine Mindestscore-Schwelle; offene Blocker verhindern `approve` unabhängig von der Punktzahl.

Eine nötige Spec-Korrektur über den Zustandskern neu einreichen und erneut gegenprüfen. Ein geänderter Vertrag oder Projektstand macht den Bericht ebenfalls ungültig. Vorhandene Quellen selbst auswerten, echte Nutzerentscheidungen klären. Dieser Reviewauftrag allein erteilt keine Umsetzungsfreigabe. Eine bestehende Autorisierung für die konkrete geprüfte Spec ohne erneute Bestätigung übernehmen.
