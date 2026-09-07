---
name: planner
description: "Philharmonie-Spezifikationen aus einem konkreten Nutzerauftrag entwickeln: Projektquellen lesen, offene Entscheidungen klären und überprüfbare Abnahmekriterien formulieren. Keine Umsetzung ohne passenden Arbeitsauftrag."
---

# Eine Mission spezifizieren

Lies Nutzerauftrag, Projektregeln und die betroffenen Dateien selbst. Trenne belegte Tatsachen, Nutzerfestlegungen und eigene Vorschläge. Übernimm den ursprünglichen Auftrag im Wortlaut. Bei Unklarheiten zur Infrastruktur oder zur Existenz einer Komponente nachfragen; keine Vorgeschichte ergänzen.

Lies vor der Aufgabenaufteilung die [Delegationsregeln](../../references/delegation.md). Lass unabhängig bearbeitbare Recherchefragen parallel von Agents der eigenen CLI untersuchen. Wähle deren Modelle nach Umfang, Kontextbedarf und Fehlerrisiko; begründe die Wahl. Gib jedem Agent konkrete Quellen und einen begrenzten Leseauftrag. Höchstens drei Agents arbeiten gleichzeitig, sie delegieren nicht erneut. Kleine unteilbare Aufgaben bearbeitest du selbst. Prüfe die gelieferten Quellen und führe die Befunde zentral zu einer konsistenten Spec zusammen. Halte Teilaufgabe, Modellwahl, Grund und Ergebnis in der Spec fest; kennzeichne Selbstberichte getrennt von nativen Laufzeitnachweisen.

Verwende [Spec.md](../../templates/Spec.md). Formuliere Ziel und Randbedingungen so, dass ein anderer Generator eine passende Lösung wählen kann. Vom Nutzer vorgegebene Technik, Pfade, Parameter und Architektur bleiben bindend. Mögliche Lösungswege sind als Vorschläge gekennzeichnet.

Jedes Kriterium braucht eine stabile ID, eine konkrete erwartete Eigenschaft und eine Prüfmethode. Beschreibe das beobachtbare Ergebnis; „funktioniert“, „robust“ oder „Best Practices eingehalten“ sind keine Prüfmethode. Alle Kriterien im maschinenlesbaren Vertrag sind Pflichtkriterien. Optionale Verbesserungen gehören ausdrücklich außerhalb der Abnahmebedingungen.

Wähle nur die benötigten Schreibpfade. Prüfungen stehen als argv-Listen im [Vertrag](../../templates/contract.json), beginnen mit `nix` oder `nix-shell` und laufen in einem separaten Test-Snapshot. Bei reinen Dokumenten können `checks` leer sein; der Evaluator prüft dann die vereinbarten Quellen und Inhalte. Quellen und manuelle Prüfmethoden dürfen trotzdem nicht fehlen.

Frage bei echten Weichen mit konkreten, sich ausschließenden Optionen. Arbeite in kleinen Spec-Stücken; lege ein prüfbares Stück vor, statt alle Architekturentscheidungen vorwegzunehmen. Eine bereits autorisierte Umsetzung braucht keine zusätzliche Freigaberunde für dieselbe Entscheidung.

Zeige nach jedem Planungsaufruf sichtbar `Modell | Aufgabe | Ergebnis`, auch wenn der Aufruf mit einer Rückfrage endet. Nenne die eigene Hauptsitzung und tatsächlich eingesetzte Recherche-Agents mit ihrem Beitrag. Verwende belegte Modellnamen und kennzeichne nur konfigurierte oder unbekannte Namen; Details stehen unter [Modelle und Aufgaben berichten](../orchestration/SKILL.md#modelle-und-aufgaben-berichten). Ergänze den Spec-Gegenprüfer, sobald er im selben Aufruf gearbeitet hat.

Der Koordinator bindet beim Anlegen mit `new ... --planner claude` oder `--planner codex` die CLI dieser Planung und reicht Spec und Vertrag über den Zustandskern ein. Vor `approve` ist `review-spec <id> --revision <n>` verpflichtend: Die andere CLI prüft den Entwurf unabhängig im lesenden Snapshot. Eigene Recherche-Agents ersetzen diese Gegenprüfung nicht.

Lies danach `status <id> --full` erneut und den dort registrierten Reviewbericht. Der Spec-Score umfasst `coverage` 25, `verification` 25, `scope` 20, `evidence` 15 und `risks` 15 Punkte; jede Teilwertung braucht Begründung und Quellenstelle. Stelle den Score, fachliche Blocker und offene Fragen getrennt dar. Es gibt keine Mindestpunktzahl zur Freigabe. Offene Blocker verhindern `approve` unabhängig vom Score. Fragen sind keine automatische Sperre; kläre tatsächlich fehlende Nutzerentscheidungen vor der Umsetzung und übernimm Antworten aus vorhandenen Quellen selbst.

Bei einer nötigen Spec-Korrektur den Entwurf über `spec` neu einreichen und erneut gegenprüfen. Auch ein geänderter Vertrag oder Projektstand macht den bisherigen Gegenreview ungültig. Eine vorhandene Autorisierung gilt weiter, soweit sie die konkrete geprüfte Spec deckt; fordere keine erneute Bestätigung nur wegen des Reviews. Direkte Änderungen an `state.json`, freigegebenen Spec-Archiven oder Abnahmekriterien einer laufenden Umsetzung sind unzulässig. Bei Scope-Änderung während der Umsetzung über `replan` eine neue Revision anlegen. Details: [Orchestrierung](../orchestration/SKILL.md).
