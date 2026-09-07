# Philharmonie

Philharmonie verbindet die Cross-CLI-Aufträge aus ask mit einer Spec, getrennten Generator- und Evaluator-Rollen sowie einem persistenten Missionszustand. Der Name beschreibt eigenständige Stimmen, die einander in Resonanz bringen.

Die Hauptsitzung plant und koordiniert. Ein lokaler Runner führt die Arbeitsrunden aus, begrenzt Schreibzugriffe auf Snapshots und übernimmt nur freigegebene Änderungen. Fachliche Abnahme, Git-Aktionen und Deployment bleiben getrennte Entscheidungen.

Planer und Generator zerlegen teilbare Aufträge und delegieren unabhängige Arbeiten parallel an Agents der eigenen CLI. Die vier Klassen Light, Standard, Advanced und Strong richten sich nach Aufgabe und Fehlerrisiko. Advanced verwendet GPT-5.6 Sol beziehungsweise Opus mit Effort `high` für Änderungen über mehrere Module und schwierige Integration. Einfache Prüfungen laufen zuerst mit deterministischen Werkzeugen. Die koordinierende Rolle prüft und integriert die Ergebnisse. [Aufgaben- und Modellzuordnung](references/delegation.md).

## Einstieg

Die Skills und Commands sind für Claude Code und Codex geteilt. Die Laufzeit benötigt Linux, Nix und die authentifizierten Ziel-CLIs. Bubblewrap prüft und begrenzt die Dateizugriffe des ganzen CLI-Prozesses.

```text
/philharmonie:plan Ergänze die Dokumentation des Startbefehls.
/philharmonie:run <mission>
/philharmonie:status <mission>
/philharmonie:accept <mission>
```

Unter Codex werden Commands als Skills wie `philharmonie:source-command-plan` verfügbar. Der Skill `philharmonie:orchestration` beschreibt den vollständigen Ablauf und kann bei passenden Projektaufträgen gewählt werden.

Für einzelne Fragen oder Änderungen bleiben `/philharmonie:ask` und `/philharmonie:execute` verfügbar. Sie benötigen keine Mission. `execute` verlangt konkrete Schreibpfade und erhält fremde Änderungen. Das bisherige ask-Plugin bleibt eigenständig nutzbar.

## Missionsablauf

Eine Mission durchläuft `planning`, `awaiting_spec`, `implementing`, `evaluating`, `awaiting_acceptance` und `completed`. FAIL führt zu einer Korrekturrunde, fehlende Nachweise zu BLOCKED. Pause, aktive Prozesse und Hindernisse werden getrennt von der fachlichen Phase geführt.

Vor der Umsetzungsfreigabe prüft die jeweils andere CLI die Spec mit `review-spec`. Der Spec-Score umfasst Auftragsabdeckung (25), Prüfbarkeit (25), Scope (20), Quellen (15) und Risiken (15), jeweils mit Begründung und Beleg. Offene Blocker verhindern die Freigabe unabhängig vom Gesamtwert. Es gibt keinen pauschalen Mindestscore. Die Bewertung gilt nur für den geprüften Spec-, Vertrags- und Projektstand; der Score ist keine Implementierungsabnahme.

Weitere Commands sind `resume`, `pause` und `cancel`. Der Runner prüft beim Wiederaufnehmen echte Prozessidentitäten und startet keinen zweiten Auftrag über einen noch laufenden Run. Jede Zustandsänderung verwendet die gelesene Revision.

Spec, Entscheidungen, Rundenberichte und Summary liegen in `.philharmonie/missions/`. Lokale Zustände, Snapshots und Rohlogs liegen in `.philharmonie/local/` und werden nicht versioniert. Ein frischer Klon übernimmt keinen aktiven lokalen Prozesszustand.

## Enthalten

| Komponente | Zweck |
|---|---|
| `orchestration` | Hauptsitzung, Nutzerentscheidungen, Commands und Fortsetzung |
| `planner` | Spec, belegte Randbedingungen und Abnahmekriterien |
| `spec-reviewer` | Gegenprüfung der Spec durch die andere CLI, Score und Blocker |
| `generator` | Umsetzung in den erlaubten Pfaden |
| `evaluator` | Unabhängige Kriterienprüfung mit PASS/FAIL/BLOCKED |
| Python-Laufzeit | Zustandskern, Prozessverwaltung, CLI-Adapter und Snapshot-Übernahme |
| JSON-Schemata und Templates | Spec-Vertrag, strukturierte Ergebnisse und Review Briefing |

Die koordinierenden CLI-Rollen verwenden standardmäßig die Modellauflösung aus ask: Codex aus dem installierten Katalog, Claude über den lokal geprüften Alias `fable`. Modell und Effort können für die Umsetzung ausdrücklich konfiguriert werden. Subagents erhalten eigene Modelle gemäß der Aufgabenregel. Die zusätzliche Implementierungsbewertung über `second_opinion` ist zuschaltbar; der Spec-Gegenreview ist Voraussetzung für `approve`.

Nach jedem Aufruf zeigt Philharmonie, welches Modell welche Aufgabe bearbeitet oder geprüft hat und mit welchem Ergebnis. Die Übersicht umfasst die Hauptsitzung, eingesetzte Subagents und CLI-Rollen. Sie kennzeichnet belegte, nur konfigurierte und unbekannte Modellnamen sowie Fehler und fehlende Abschlussbelege. Ein Statusabruf weist frühere Arbeit als solche aus. Details zu stdout, stderr und den gespeicherten Berichten stehen in [build.md](build.md).

## Rechte und Betriebsgrenzen

Agenten sehen einen separaten Snapshot. Der Evaluator liest Quellen, der Generator darf seinen Snapshot bearbeiten. Vor einer Übernahme prüft der Kern den ursprünglichen Stand und jeden geänderten Pfad. Git-Metadaten bleiben in der Agentensandbox lesend. Eine während der Übernahme unterbrochene Mission erhält ein Journal ihrer Teiländerungen.

Der Nix-Daemon bleibt für Agenten verborgen. Für ausdrücklich genehmigte Prüfkommandos kann `check_nix_daemon` aktiviert werden; damit erhält der Test Zugriff auf einen Host-Dienst. Ohne passende Umgebung bleiben nicht ausführbare Prüfungen als Hindernis sichtbar. Das API-Netz ist verfügbar und nicht auf einzelne Endpunkte beschränkt.

Host-Anmeldedateien werden gezielt lesend eingebunden. Abgelaufene Anmeldungen, die eine Aktualisierung der Datei verlangen, müssen am Host erneuert werden. Mehrere Hosts und gemeinsam genutzte Netzdateisysteme werden nicht koordiniert. Git-Submodule benötigen derzeit einen eigenen Auftrag im jeweiligen Checkout.

Details stehen in [build.md](build.md), den [Laufzeitverträgen](references/contracts.md) und den [geprüften CLI-Verträgen](references/cli-contract.md). Ursprung und Entwurfsentscheidungen sind im [Designdokument](../../docs/design-ask-tandem.md) dokumentiert; dieser Link gilt im Marketplace-Repository.

## Lizenz

MIT. Herkunft und Abhängigkeiten: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
