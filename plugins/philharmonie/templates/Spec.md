# Spezifikation

## Missionstyp

Code, Dokument oder Konzept; den konkreten Typ eintragen.

## Nutzerauftrag

Den ursprünglichen Auftrag hier im Wortlaut übernehmen.

## Ziel

Das beobachtbare Ergebnis beschreiben.

## Befunde und Quellen

Gelesene Projektdateien und externe Quellen mit Pfad beziehungsweise URL und Stand angeben.

## Recherche und Delegation

Die planende CLI angeben. Für jede delegierte Recherche Teilaufgabe, gewähltes Modell, Auswahlgrund, Ergebnis und Quellen festhalten. Selbstberichte von nativen Laufzeitnachweisen unterscheiden. Bei direkter Bearbeitung einer unteilbaren Aufgabe die Entscheidung kurz begründen. Die Synthese und Auflösung widersprüchlicher Befunde verantwortet der Planer.

## Abnahmekriterien

Für jede Kriterien-ID aus dem Vertrag die erwartete Eigenschaft und Prüfmethode erläutern.

## Randfälle

Die für dieses Ziel relevanten Fehler- und Grenzfälle benennen.

## Entscheidungen

Nutzerfestlegungen und eigene Vorschläge unterscheiden; relevante Alternativen und Gründe festhalten.

## Offene Fragen

Noch fehlende Informationen und echte Nutzerentscheidungen getrennt von belegten Blockern benennen. Keine Rückfrage zu Angaben, die bereits in den gelesenen Quellen stehen.

## Gegenprüfung vor Umsetzung

Vor der Freigabe prüft die andere CLI diese Spec über `review-spec`. Ihr Bericht wird separat unter `specs/` gespeichert und über `status` referenziert; nach dem Review diesen Spec-Text nicht bloß zur Übernahme des Scores ändern, weil das den geprüften Stand verändern würde.

Der Bericht begründet `coverage` bis 25, `verification` bis 25, `scope` bis 20, `evidence` bis 15 und `risks` bis 15 Punkte. Blocker und Fragen stehen getrennt. Es gibt keine Mindestpunktzahl; offene Blocker verhindern die Freigabe unabhängig vom Score. Eine geänderte Spec benötigt eine neue Gegenprüfung.

## Außerhalb des Auftrags

Bewusste Ausschlüsse festhalten.

## Mögliche Lösungswege

Unverbindliche Implementierungshinweise; bindende Technikvorgaben gehören zu den Entscheidungen.
