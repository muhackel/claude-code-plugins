# Regressionstests für t3-bridge

Die Tests prüfen Entscheidungen eines Agenten, nicht das Vorkommen bestimmter
Wörter im Skill. Es gibt keinen zusätzlichen ausführbaren Plugin-Code.

## Wiederholen

1. In einem T3-Thread den aktuellen Skill und seine Referenzen bereitstellen.
2. Je einen frischen Claude- und Codex-Task mit folgendem Auftrag starten. Modelle
   und Optionen vorher aus `orchestrator_capabilities` ermitteln. Für uncommittete
   Skill-Änderungen `isolation: "shared"` verwenden und nur Lesen erlauben.
3. Die Antworten gegen `rubric.md` auswerten. Bei einem Fehler die tatsächliche
   Tool-Entscheidung nennen; einen fehlenden Lauf als nicht getestet behandeln.
4. Nach Änderungen betroffene Fälle erneut in frischen Tasks prüfen. Alle Fälle
   erneut ausführen, wenn sich Routing, Optionen oder Lebenszyklusregeln ändern.
5. Erst danach einen separaten Review-Task starten. Für neue Review-Runden jeweils
   einen neuen `delegate_task` mit dem bisherigen Befundkontext verwenden.

Testauftrag (Pfade gegen den tatsächlichen Checkout auflösen):

> Lies `plugins/t3/skills/t3-bridge/SKILL.md`, die dort verlinkten Referenzen und
> `plugins/t3/tests/cases.md`. Bearbeite die Fälle unabhängig voneinander mit dem
> Skill. Lies weder rubric.md noch frühere Ergebnisse. Nur lesen, keine Edits.
> Alle T3-Aktionen innerhalb der Fälle sind simuliert: keine echten Delegationen,
> Threads, Scheduler oder Freigaben auslösen. Gib ausschließlich ein JSON-Objekt
> mit `cases` als Liste zurück. Je Fall: `id`, `calls` (Liste aus `tool` und `args`),
> `decision` und `reason`. Tool-Aufrufe in Ausführungsreihenfolge; bei fehlender
> Antwort am nächsten notwendigen Aufruf stoppen. Fakten stammen aus dem jeweiligen
> Fall, nicht aus der realen Sitzung. Keine Musterlösung anfordern.

## Bewertung

Ein Fall besteht nur, wenn seine Pflichtkriterien erfüllt sind und keine verbotene
Aktion vorkommt. Formulierungen sind frei. Simulierte Aufrufe prüfen das Verhalten
bei vorgegebenen Zuständen, nicht die Ausführung im echten Provider-Harness.
Die Erwartungen liegen getrennt, damit die Testagenten sie nicht als Lösung lesen.

Zusätzlich ein echter, kleiner Roundtrip: Codex delegiert einen lesenden Auftrag
an Claude; Claude nutzt den Skill, delegiert einen begrenzten Prüfauftrag zurück
an Codex und liefert dessen Ergebnis mit beiden Task-Identitäten zurück. Auch die
effektiven Modelle/Optionen und der Task-Abschluss müssen nachweisbar sein.

Frontmatter, lokale Referenzpfade, Manifest-Gleichheit und Eintrag in beiden
Marketplaces separat prüfen. Der `skill-creator`-Validator eignet sich für das
Skillformat, ersetzt aber weder die Verhaltensfälle noch einen Installationscheck.
Skripte für solche lokalen Prüfungen in einer Nix-Umgebung ausführen.

Ergebnisse und Testgrenzen: [results.md](results.md).
