---
name: orchestration
description: "Philharmonie koordiniert abgegrenzte Projektaufträge mit Spec, getrenntem Generator und Evaluator sowie dauerhaftem Zustand. Verwenden für ausdrücklich beauftragte Planung und Umsetzung mit unabhängiger Prüfung oder zum Fortsetzen einer Philharmonie-Mission; einzelne Zweitmeinungen über die Commands ask und execute."
---

# Philharmonie koordinieren

Die Hauptsitzung ist der Koordinator. Kläre echte Entscheidungen mit dem Nutzer und übernimm bereits erteilte Autorisierung. Der Runner führt Generator und Evaluator in frischen CLI-Kontexten aus. Domänenwissen und Vault-Regeln bleiben bei den zuständigen Fachskills; dieser Skill verleiht keine zusätzlichen Schreibrechte.

## Modelle und Aufgaben berichten

Beende jeden vom Nutzer aufgerufenen Philharmonie-Command mit einer kurzen Tabelle `Modell | Aufgabe | Ergebnis`. Übernimm sie sichtbar in die Antwort; ein Verweis auf Logs allein reicht nicht. Das gilt auch für Planung, Rückfragen, Status, Pause, Abbruch und fehlgeschlagene Aufrufe.

Nenne die planende oder koordinierende Hauptsitzung, tatsächlich gestartete eigene Agents und die CLI-Rollen, die im aktuellen Aufruf gearbeitet haben. Verwende für CLI-Rollen `invocation_models` aus der JSON-Ausgabe beziehungsweise die Übersicht auf stderr. Sie unterscheidet Umsetzung, unabhängige Prüfung und Abgleich; die Einträge enthalten konkrete Aufgaben und Ergebnisse. `last_run.model_activity` und Berichte zeigen frühere Arbeit, die du nicht als neuen Modellaufruf darstellen darfst.

Übernimm Modellnamen aus nativen Werkzeugantworten oder Sitzungsmetadaten. Nur konfigurierte Namen als „konfiguriert, nicht bestätigt“ kennzeichnen; unbekannte Namen offenlassen. Keine Modellklasse als tatsächlichen Modellnamen ausgeben. Nicht gestartete Agents weglassen. Bei der Hauptsitzung ihre eigene Aufgabe nennen, etwa „Spec zusammengeführt“ oder „Status eingeordnet“; wenn deren Modell nicht offengelegt ist, „Hauptsitzung: Modell unbekannt“ schreiben.

Unterscheide gemeldete Umsetzung, unabhängiges Prüfurteil und belegte Abnahme. Ein Subagent-Abschluss ist ein Selbstbericht. Bei Fehlern oder fehlenden Abschlussbelegen den entsprechenden Status nennen. Gab es keine zusätzlichen Modellaufträge, genau das angeben; mechanische Prüfkommandos keinem Modell zuschreiben.

## Laufzeit finden

Leite den Plugin-Root aus dem Pfad dieses Skills ab: das übergeordnete Verzeichnis mit `.codex-plugin/plugin.json` oder `.claude-plugin/plugin.json`. Unter Claude Code kann `${CLAUDE_PLUGIN_ROOT}` bereits diesen absoluten Pfad enthalten. Unter Codex ist ein nicht ersetzter Platzhalter kein gültiger Pfad.

Alle folgenden Laufzeitbefehle werden so aufgerufen; `<root>` und `<projekt>` sind durch die tatsächlich gelesenen absoluten Pfade zu ersetzen:

```bash
nix run "path:<root>" -- -C "<projekt>" status
```

Ein installierter Nix-Befehl `philharmonie` ist gleichwertig. Projekt muss ein Git-Checkout mit mindestens einem Commit sein. Schreibaufträge benötigen einen Feature-Branch. Neue Branches oder Worktrees im Umfang des Nutzerauftrags vorbereiten; fremde Änderungen nicht staschen oder überschreiben. Vor tatsächlichen Kopier-/Worktree-Operationen gelten die Projektregeln für Zielpfade. Die internen Run-Snapshots sind Teil des beauftragten Runner-Aufrufs.

CLI-Aufrufe benötigen API-Netz. Wenn die Host-Sandbox das sperrt, beantrage den benötigten Ausführungszugriff. Kein eigenmächtiger Wechsel zu einem ungeschützten Adapter. `doctor` prüft installierte CLI-Verträge und Bubblewrap ohne Modellauftrag.

## Mission planen

Lies dafür [Planner](../planner/SKILL.md), die [Delegationsregeln](../../references/delegation.md) und die [Verträge](../../references/contracts.md). Ermittle Projektregeln, Nutzerabsicht, Scope und nachprüfbare Kriterien. Der Planer setzt für unabhängige Recherchefragen parallel Agents seiner eigenen CLI mit aufgabenabhängiger Modellwahl ein und führt ihre Ergebnisse selbst zusammen. Höchstens drei Agents gleichzeitig, keine weitere Delegation durch diese Agents. Stelle Fragen zu echten Weichen einzeln mit konkreten Optionen. Ein klarer Arbeitsauftrag ist bereits eine Erlaubnis für seine notwendigen Schritte.

1. Lege eine Mission über `new <id> --goal '<ursprünglicher Auftrag>' --planner <claude|codex>` an. Trage die CLI der planenden Hauptsitzung ein; die Gegenprüfung verwendet automatisch die andere CLI. ID ist ein kurzer eindeutiger Slug. `--previous <id>` verknüpft eine Folgemission.
2. Schreibe Spec und Vertrag zunächst als Entwürfe in einen temporären Bereich des Projekts oder nach `/tmp`. Verwende [Spec.md](../../templates/Spec.md) und [contract.json](../../templates/contract.json). Keine erfundenen Freigaben, Kriterien oder Quellen.
3. Lies `status <id> --full`. Reiche den Entwurf mit `spec <id> --file <spec.md> --contract <contract.json> --revision <n>` ein. Der Kern archiviert die Revision.
4. Lies den neuen `status <id> --full` und starte verpflichtend `review-spec <id> --revision <n>`. Die andere CLI prüft Spec, Vertrag und Projektstand unabhängig in einem lesenden Snapshot. Danach erneut `status <id> --full` lesen, weil der Review die Zustandsrevision erhöht. Lies den registrierten Bericht unter `.philharmonie/missions/<id>/specs/`.
5. Zeige den begründeten Spec-Score und getrennt davon Blocker und offene Fragen. Bearbeite nötige Korrekturen, reiche eine geänderte Spec mit Vertrag erneut ein und wiederhole die Gegenprüfung. Bei unveränderter Spec, aber geändertem Projektstand ebenfalls neu prüfen. Verwende für jeden Aufruf die zuletzt gelesene Zustandsrevision.
6. Ist die Umsetzung dieser konkreten geprüften Spec vom bestehenden Auftrag gedeckt und sind keine Review-Blocker offen, übernimm den Wortlaut mit `approve <id> --authorization '<Nutzeranweisung>' --revision <n>`. Sonst lege die Spec zur Entscheidung vor. Ein reiner Planungsauftrag bleibt bei `awaiting_spec`. Das Review allein verlangt keine erneute Nutzerfreigabe; eine leere Bestätigungsfloskel ersetzt keine Autorisierung.

Der Score summiert fünf begründete Teilwertungen: `coverage` 25 Punkte für Auftragsabdeckung, `verification` 25 für Prüfbarkeit, `scope` 20 für Abgrenzung und Schreibrechte, `evidence` 15 für Quellen und `risks` 15 für Randfälle und Risiken. Es gibt keine Mindestscore-Schwelle. Fachliche Blocker verhindern `approve` unabhängig von der Punktzahl; offene Fragen werden getrennt geführt und sperren die Laufzeit nicht pauschal. Fehlende Nutzerentscheidungen klärst du vor der Umsetzung. Ein abgeschlossener Review mit Blockern bleibt in `awaiting_spec` mit `activity=idle`; ein technischer Prüffehler führt zu `blocked`.

Der Gegenreview gilt nur für die registrierte Spec-Revision samt Vertrag und Projektfingerabdruck. Der Kern prüft diese Bindung erneut bei `approve`. Bei einer Altmission ohne `planner_cli` kann `review-spec ... --planner <claude|codex>` die belegte ursprüngliche Planer-CLI binden. Die Zuordnung einer vorhandenen Mission darf damit nicht gewechselt werden.

Für vorhandene Änderungen in erlaubten Pfaden verlangt `approve` ein `--include-dirty <datei>` pro zugehöriger Datei. Lies diese Änderungen vorher. Fremde Änderungen außerhalb des Schreibbereichs bleiben erhalten. Der Vertrag nennt Dateien oder Verzeichnisse; `.` und geschützte Metadaten sind keine gültigen Freigaben.

## Umsetzen und prüfen

Lies den aktuellen `status` und starte `run <id> --revision <n>`. Der Runner übernimmt Generator/Evaluator-Wechsel innerhalb der freigegebenen Spec bis zur Nutzerentscheidung oder einem dokumentierten Hindernis. Gib bei längeren Läufen kurze Fortschrittsmeldungen; frage dafür `status <id>` ab, starte keine zweite Instanz.

`awaiting_acceptance` bedeutet fachlich geprüft. Lies den vollständigen Rundenbericht und übergib das [Review Briefing](../../templates/Review-Briefing.md). Berichte bestätigte Eigenschaften mit Belegen und konkrete Grenzen. Ein PASS ist keine Erlaubnis zu Commit, Push, Merge oder Deployment.

Bei einer eindeutigen Abnahme: `accept <id> --authorization '<Nutzeranweisung>' --revision <n>`. Danach die erzeugte `Summary.md` lesen und verlinken. Bereits vorab vereinbarte objektive Abschlussbedingungen dürfen eine weitere Rückfrage ersetzen, wenn der Nutzer diese ausdrücklich autorisiert hat und sie nachgewiesen sind.

## Korrektur und Wiederaufnahme

| Situation | Laufzeitbefehl und Verhalten |
|---|---|
| Fehlerfeedback im genehmigten Scope nach PASS | `feedback <id> --reason '<Auftrag>' --revision <n>`, dann `run` mit neuer Revision |
| Neue Anforderungen oder geänderte Kriterien | Lauf anhalten; `replan <id> --reason '<Änderungsauftrag>' --revision <n>`, dann neue Spec einreichen |
| Externe Änderung nach PASS | `reevaluate <id> --revision <n>`, dann erneut `run`; altes Urteil nicht übertragen |
| Pause | `pause <id> --revision <n>`; status bis zur bestätigten Pause verfolgen |
| Abbruch | `cancel <id> --revision <n>`; Teiländerungen und Berichte erhalten, tatsächliches Ende prüfen |
| Neue Sitzung oder unterbrochener Auftrag | Erst `status <id> --full`, Run-Protokolle, aktuelle Projektregeln und Git-Änderungen lesen; dann `resume` |

`resume <id> --revision <n>` setzt freigegebene Arbeit fort. Bei `blocked` ergänze `--resolution '<konkreter Beleg>'`, nachdem das Hindernis wirklich beseitigt ist. Unterbrochene Übernahmen anhand von `apply.json`, Snapshot und Arbeitsbaum vergleichen. Ein bloßer Retry-Wunsch ist kein Nachweis. Zusätzliche Korrekturrunden erfordern einen Nutzerauftrag und `--extra-rounds <anzahl>`.

Ein Beobachtungs-Timeout beweist keinen Prozessabbruch. Lebt der alte Prozess, beobachte ihn weiter. Bei unbekannter Erreichbarkeit keine neue Instanz starten. Veraltete `--revision` nicht blind erhöhen: den inzwischen geänderten Zustand lesen und bewerten.

## Einzelauftrag

`ask` und `execute` legen keine Mission an. Schreibe ein [Handover](../../templates/Handover.md) mit dem relevanten Diskussionsstand. Übergib es über `--handover <datei>` oder stdin. Ohne Handover führt `ask` ein lesendes Standard-Review aus. `execute` benötigt einen Auftrag und `--allow <pfad>` für jeden Schreibbereich. Modellantwort unverändert wiedergeben, danach knapp einordnen; bei Ausführung zusätzlich die tatsächlich geänderten Dateien prüfen.

Die Klasse des Auftrags bestimmt das Modell. Ohne `--tier` gilt `advanced` beim Standard-Review und sonst `standard`.

| Klasse | Wofür | Claude | Codex |
|---|---|---|---|
| `light` | eindeutige Kleinarbeit: String fixen, Datei finden, Formatierung | haiku, medium | luna, medium |
| `standard` | einzelnes Modul, Test schreiben, lokale Fehleranalyse | sonnet, high | terra, high |
| `advanced` | mehrere Module, Refactoring, schwere Fehlersuche, Prüfung | opus, high | sol, high |
| `strong` | Architektur, widersprüchliche Anforderungen, Planung | fable, high | astra, high |

Im Zweifel die kleinere Klasse. Für harte Aufgaben lohnt `strong` eher als Planer, dessen Plan anschließend eine kleinere Klasse umsetzt. Missionsrollen wählen ihre Klasse selbst: Generator und Evaluator arbeiten in `advanced`, die Spec-Gegenprüfung in `strong`. `--model` und `--effort` überschreiben die Klasse, wenn eine Vorgabe nötig ist.

Die Modellübersicht auf stderr gemäß [Modelle und Aufgaben berichten](#modelle-und-aufgaben-berichten) anschließend sichtbar wiedergeben und die eigene koordinierende Hauptsitzung ergänzen. stdout bleibt die unveränderte fachliche Antwort.

Weiterführend: [Laufzeitverträge](../../references/contracts.md), [CLI-Quellen und Rechte](../../references/cli-contract.md), [Build und Tests](../../build.md).
