# Testprotokoll vom 27.10.2026

Arbeitsstand: neues Plugin `t3` 0.1.0, Skill `t3-bridge`. Ausgangscommit des
Repositorys: `b0a97eb`. Alle Testagenten lesen den uncommitteten Arbeitsstand im
geteilten Checkout und dürfen keine Dateien ändern. Die Modellantworten sind
simulierte Tool-Sequenzen; nur die gesondert dokumentierte Live-Prüfung führt
tatsächlich eine Delegation zwischen Herstellern aus.

## Strukturprüfung

Bestanden:

- `skill-creator/scripts/quick_validate.py` in `nix-shell -p python3Packages.pyyaml`.
- Gleichheit von Name, Version, Beschreibung, Autor, Lizenz und Keywords in beiden
  Manifesten; beide zeigen auf dasselbe Skill-Verzeichnis.
- Eindeutige Einträge und auflösbare Plugin-Pfade in beiden Marketplaces.
- Skill-Name entspricht dem Verzeichnis; Description im Projektbudget von
  150–250 Zeichen; automatische Auswahl nicht gesperrt.
- Lokale Links des Skills und seiner Referenzen sowie inzwischen 18 eindeutige Fall-IDs.
- `git diff --check`.

## Verhaltensregression, Runde 1

Beide Agenten erhielten Skill, Referenzen und Testeingaben, aber weder die Rubrik
noch vorherige Antworten. Auswertung durch den Hauptagenten gegen `rubric.md` und
die Live-Verträge der betroffenen T3-Tools.

In den Ergebnis-JSONs enthält `cases` die unveränderte strukturierte Child-Ausgabe.
Task-Identität, Modelloptionen, Skill-Hash und `evaluation` wurden vom Hauptagenten
als Nachweis beziehungsweise Bewertung ergänzt; sie sind keine Selbstauskunft des
Testmodells. Die ursprüngliche JSON-Formatierung wurde beim Speichern vereinheitlicht.

- Claude Fable 5.1 (`claudeAgent` / `claude-fable-5-1`, keine expliziten Optionen):
  **15/16 bestanden**. [Vollständige Antwort und Task-ID](results/claude-r1.json).
- Codex (`codex` / `gpt-6-astra`, `reasoningEffort=high`, `serviceTier=default`):
  **15/16 bestanden**. [Vollständige Antwort und Task-ID](results/codex-r1.json).

Beide scheiterten an **R11**: Claude wollte eine Approval mit
`t3_pending_request_read` lesen, Codex mit `t3_pending_request_list` suchen.
Die Tool-Verträge beschränken beide Methoden auf Nutzerfragen. Keiner der Agenten
wollte eine Freigabe erteilen, aber der gewählte Leseweg hätte nicht funktioniert.

Korrektur: Der Skill trennt `hasPendingQuestion` und `pendingApproval` jetzt in
eigene Absätze. Er schließt die gesamte Familie `t3_pending_request_*` für Approvals
aus und nennt Thread-Aktivität beziehungsweise die Oberfläche des Freigabehalters
als Zugang zum aktuellen Kontext. Die Rubrik benennt auch den falschen Lesezugriff
ausdrücklich als Fehler. Alle 16 Fälle wurden in frischen Tasks wiederholt.

Skill-SHA256 in Runde 1:
`37d9411fff9d255d76b919002b3370850e7f9824a3ae357b4be88586a0137dc7`.

Skill-SHA256 nach der Korrektur:
`8faaac9ad1f7ff91163ef507c859fd13e3114d2bcce8c4236e3bb765da40a54e`.

## Verhaltensregression, Runde 2

Frische Tasks mit demselben Prüfauftrag und korrigiertem Skill, ohne Kenntnis der
Ergebnisse aus Runde 1 oder der Rubrik:

- Claude Fable 5.1: **16/16 bestanden**. [Antwort und Task-ID](results/claude-r2.json).
- Codex GPT-6 Astra: **16/16 bestanden**. [Antwort und Task-ID](results/codex-r2.json).

Beide wählen bei R11 nun `t3_thread_read` mit `view: "activity"`, belassen die
Freigabe beim zuständigen Halter und verwenden für R15 weiterhin korrekt die
Nutzerfragen-Tools. Die übrigen 14 Fälle bleiben korrekt. Damit **32/32 bestandene
Fallbearbeitungen** im zweiten Durchlauf; Runde 1 bleibt als Fehlernachweis erhalten.

## Fable-Review und Live-Roundtrip

Das anschließende unabhängige [Fable-Review](results/fable-review-r1.json) beurteilt
den Skill als fachlich richtig und freigabefähig mit zwei kleinen Nachbesserungen.
Beide wurden übernommen:

- Engere Berechtigungsmodi sind keine Nur-Lesen-Garantie; Freigaben bleiben beim
  Menschen. Schreibgrenzen stehen im Auftrag. Neuer Regressionfall R17.
- Das Lesen eines terminalen Ergebnisses bestätigt seine Zustellung. Der Parent
  wertet es sofort aus und wartet nicht auf eine zweite Weckung. Neuer Fall R18.

Außerdem wurde die Herkunft der Bewerter-Annotationen offengelegt. Die nun 18 Fälle
wurden nach diesen Ergänzungen erneut in beiden Hosts durchgespielt.

Der echte Weg **Codex → Fable → Codex → Fable → Codex** ist abgeschlossen.
Fable hat einen Codex-Child gestartet, dessen effektive Optionen geprüft und sein
Ergebnis an den Hauptagenten zurückgegeben. Dieser hat anschließend den
[Codex-Thread direkt gelesen](results/live-roundtrip.json): ein abgeschlossener
Run, Provider `codex`, Modell `gpt-6-astra`, Parent ist der Fable-Review-Thread.
Die Kennung `T3-BRIDGE-ROUNDTRIP-20261027` und das Urteil zur korrekten Trennung
von Fragen und Approvals stehen in der echten terminalen Antwort.

Die vollständigen Task-/Thread-IDs und der Ergebnistext stehen in den verlinkten
JSON-Dateien. Fable bestätigte angeforderte und zurückgegebene Optionen
`reasoningEffort=high`, `serviceTier=default` sowie `status=completed` und
`workState=result_available`. Keine weiteren Live-Nebenwirkungen.

## Abschließender Stand

Fables [Nachprüfung](results/fable-review-r2.json) bestätigt alle Korrekturen:
**freigabefähig, keine weiteren Einwände**. Die beiden verbliebenen Hinweise zur
Protokollpflege (18 Fall-IDs, neuer Hash) sind hier berücksichtigt.

Finaler Skill-SHA256:
`fe2722b64cf740e81faf783e3524b76ee0129758ea2157cacd8c953c5cc92e54`.

Runde 3 auf diesem finalen Skill, erneut frische Tasks ohne Rubrik oder Vorbefunde:

- Claude Fable 5.1: **18/18 bestanden**. [Antwort und Task-ID](results/claude-r3.json).
- Codex GPT-6 Astra: **18/18 bestanden**. [Antwort und Task-ID](results/codex-r3.json).

Damit sind **36/36 Fallbearbeitungen** auf dem finalen Skill bestanden. R17 wird
von beiden als reine Auskunft ohne Delegation beantwortet; R18 verarbeitet das
vorliegende Ergebnis sofort. Alle 16 bisherigen Fälle bleiben korrekt.

## Aussagegrenzen

Die simulierten Fälle prüfen die Entscheidungen zweier Modelle unter vorgegebenen
Zuständen. Sie beweisen keine allgemeine Zuverlässigkeit bei jedem Modell oder
jeder Formulierung. Autor und Bewerter der Regressionen sind derselbe Hauptagent;
Fable hat die Regeln unabhängig geprüft und ausgewählte Bewertungen gegengeprüft,
aber nicht jeden Fall blind bewertet. Die statischen Prüfungen validieren lokale
Paketstruktur und Metadaten, nicht Installation oder automatische Skill-Auswahl in einer neuen
Claude-/Codex-Sitzung. Der ACP-Fallback wird simuliert, nicht in einem echten
ACP-Provider ausgeführt. Ebenso werden Fehler, Approvals und Timeouts nicht live
provoziert; es werden keine neuen Worktrees, Scheduler oder Webhooks angelegt.
