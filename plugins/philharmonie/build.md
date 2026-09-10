# Build und Betrieb

## Voraussetzungen

Linux auf x86_64 oder aarch64, Nix mit Flakes sowie authentifizierte `claude`- und `codex`-CLIs im Host-PATH. Die Flake stellt Python, jsonschema, PyYAML, Git und Bubblewrap bereit. Die Ziel-CLIs kommen wie bei ask vom Host, damit die installierte Version verwendet wird.

Die folgenden Befehle werden im Plugin-Verzeichnis ausgeführt. `path:.` berücksichtigt auch neue, noch ungetrackte Entwicklungsdateien. Der angegebene Projektpfad muss ein Git-Checkout mit mindestens einem Commit sein; Schreibaufträge benötigen einen Feature-Branch.

## Entwicklungsumgebung

```bash
nix develop path:.
python3 scripts/philharmonie.py --help
```

Die Shell enthält zusätzlich Shellcheck für etwaige Shell-Erweiterungen. Der Runner selbst ist in Python geschrieben.

## Bauen und Starten

```bash
nix build path:.
nix run path:. -- --help
nix shell path:. -c philharmonie --help
nix run path:. -- doctor
nix run path:. -- -C /pfad/zum/projekt status
```

`doctor` ruft nur CLI-Hilfe, Versionsausgabe und den eingebauten Modellkatalog ab und prüft eine temporäre Sandbox. Es startet keinen Modellauftrag. Der Nix-Befehl `philharmonie` kann unabhängig vom Marketplace installiert werden; das Plugin selbst enthält zusätzlich Skills und Commands.

## Testen

```bash
nix flake check path:. -L
nix develop path:. -c python3 -m unittest discover -s tests -v
nix develop path:. -c env PHILHARMONIE_INTEGRATION=1 python3 -m unittest discover -s tests -v
```

Die Flake prüft den Zustandskern, Ergebnisverträge, Übernahme und Fehlerpfade ohne API-Aufträge. Die zusätzliche lokale Integration startet echte Bubblewrap-Prozesse. Sie ist separat, weil eine Nix-Build-Sandbox verschachtelte User-Namespaces verbieten kann. Ein übersprungener Integrationstest ist kein Nachweis einer funktionierenden Host-Sandbox.

Der folgende Test verwendet die vorhandenen Anmeldungen und startet begrenzte echte Modellaufträge in einem temporären Git-Projekt:

```bash
nix develop path:. -c env PHILHARMONIE_LIVE=1 python3 -m unittest discover -s tests -p test_integration.py -v
```

Diese Live-Prüfung ist vom normalen Build getrennt. Sie prüft Claude als Generator mit Codex als Evaluator und die umgekehrte Zuordnung, jeweils einschließlich unabhängigem Ersturteil und anschließendem Abgleich. Quellcode-, Schema- und Mock-Tests ersetzen sie nicht.

Die native Delegation hat eigene Live-Tests. Sie starten je Anbieter Light und Standard parallel sowie Advanced in einem separaten Test, prüfen deren tatsächliche Modelle anhand nativer Ereignisse beziehungsweise Rollouts und kontrollieren getrennte Schreibpfade im Snapshot:

```bash
nix develop path:. -c env PHILHARMONIE_LIVE=1 python3 -m unittest discover -s tests -p test_delegation.py -v
```

Die Spec-Gegenprüfung wird ebenfalls in beiden CLI-Richtungen separat getestet:

```bash
nix develop path:. -c env PHILHARMONIE_LIVE=1 python3 -m unittest discover -s tests -p test_spec_review.py -v
```

Dieser Test prüft fünf begründete Teilnoten, deren Summe und die Bindung an den unveränderten Projektstand. Er erteilt keine Umsetzungsfreigabe. Fachliche Blocker bleiben im echten Ergebnis erhalten.

Die Modellübersicht wird für beide CLIs mit einem echten `execute`-Aufruf und einem Advanced-Agent geprüft:

```bash
nix develop path:. -c env PHILHARMONIE_LIVE=1 python3 -m unittest discover -s tests -p test_activity.py -v
```

Der Test kontrolliert Modellnachweis, Aufgaben- und Ergebniszuordnung, die sichtbare Tabelle sowie die Übernahme der vom Subagent erstellten Datei. Seine Testprojekte und Rohlogs bleiben unter `/tmp/philharmonie-live-activity-*` zur Prüfung erhalten.

## Projektspezifisches

Eine Mission benötigt zuerst Ziel, Spec und Vertrag. Die Templates sind Beispiele und müssen zum Auftrag passen:

```text
philharmonie -C /projekt new readme-start --planner codex --goal "Dokumentiere den vereinbarten Startbefehl."
philharmonie -C /projekt status readme-start --full
philharmonie -C /projekt spec readme-start --file /tmp/Spec.md --contract /tmp/contract.json --revision 1
philharmonie -C /projekt review-spec readme-start --revision 2
philharmonie -C /projekt status readme-start --full
philharmonie -C /projekt approve readme-start --authorization "Setze diese Spec um." --revision <gelesene-revision>
philharmonie -C /projekt run readme-start --revision <revision-nach-approve>
```

Die Befehle sind nach `nix shell path:.` verfügbar. Revisionen im Beispiel gelten nur für diese ununterbrochene Folge; in einer bestehenden Mission immer den tatsächlichen Zustand lesen. `--authorization` dokumentiert einen bereits erteilten Nutzerauftrag und darf nicht erfunden werden.

Einzelaufträge:

```bash
nix run path:. -- -C /projekt ask --dry-run </dev/null
nix run path:. -- -C /projekt ask --handover /tmp/Handover.md
nix run path:. -- -C /projekt execute --handover /tmp/Handover.md --allow README.md
```

`ask` ohne Handover liefert das Standard-Review. `execute` verlangt einen Auftrag und konkrete Schreibpfade. `--include-dirty <datei>` ordnet gelesene vorhandene Änderungen ausdrücklich dem Auftrag zu. Der Einzelaufruf gibt die Antwort auf stdout und Fortschritt/Änderungsliste auf stderr aus; CLI-Fehlercodes werden weitergereicht.

Einzelne Schreibaufträge halten Snapshots, Übernahmejournal und Rohantworten unter `.philharmonie/local/singles/` fest. Für Generatoren und `execute` liegen dort beziehungsweise im Missions-Run außerdem Agentdefinitionen und `delegation-events.json`. Codex-Rollouts liegen im Sitzungsverzeichnis des Hosts und belegen die tatsächlich verwendeten Modelle. Jeder Auftrag trägt dort die Kennung `[Philharmonie …]`, bei Claude zusätzlich als Sitzungsname. Host-Anmeldedateien werden lesend eingebunden. Fehlgeschlagene Fragen behalten ihr temporäres Protokoll; stderr nennt den Pfad. Erfolgreiche Fragen entfernen den temporären Arbeitsbereich.

Jeder Laufzeitaufruf endet mit einer Modellübersicht auf stderr. Die Antwort beziehungsweise das Zustands-JSON auf stdout bleibt maschinenlesbar. Zustandsausgaben enthalten zusätzlich `invocation_models` für die Modellarbeit dieses Aufrufs; `last_run.model_activity` beziehungsweise `runs[].model_activity` enthalten die gespeicherte Missionshistorie. Jeder Modellaufruf erzeugt `model-activity.json` und `model-activity.md` neben seinen Rohlogs. Missionsberichte übernehmen diese Einträge dauerhaft. Bei erfolgreichen `ask`-Aufrufen bleibt die Übersicht auf stderr erhalten, während der temporäre Arbeitsbereich entfernt wird.

Die Tabelle nennt Modell, Aufgabe und Ergebnis und unterscheidet native Modellnachweise von konfigurierten Namen. Nicht gestartete Rollen werden nicht als Arbeit aufgeführt. Bei Status- und anderen Verwaltungsbefehlen nennt die Laufzeit ausdrücklich, dass sie keine zusätzlichen Modellaufträge ausgeführt hat. Der koordinierende Skill ergänzt seine eigene Hauptsitzung und deren direkt eingesetzte Recherche-Agents in der sichtbaren Antwort.

## Installation in den Hosts

Im Marketplace-Repository registrieren die am 2026-09-07 geprüften CLIs das Plugin so:

```bash
claude plugin marketplace add /absoluter/pfad/zu/claude-code-plugins
claude plugin install philharmonie@muhackel-plugins
codex plugin marketplace add /absoluter/pfad/zu/claude-code-plugins
codex plugin add philharmonie@muhackel-plugins
```

Diese Befehle innerhalb der Nix-Entwicklungsumgebung ausführen. Bereits registrierte Marketplaces nicht erneut hinzufügen. Neue Sitzungen laden das installierte Plugin. Für Installationstests lassen sich `CLAUDE_CONFIG_DIR` und `CODEX_HOME` auf getrennte temporäre Profile setzen. Die Prüfung für Version 0.1.0 hat ausschließlich solche Testprofile verwendet.

Bei verweigerten User-Namespaces endet der Runner vor dem Modellstart. Bei fehlender Authentifizierung oder ungültigen Ergebnissen hält er den Fehler fest. Nach einem Sitzungsabbruch `status --full`, Run-Protokoll und gegebenenfalls `apply.json` prüfen; erst mit einem belegten Wiederaufnahmepunkt fortfahren. Die [Laufzeitverträge](references/contracts.md) beschreiben Pause, Resume, Rundenbudgets und Nix-Daemon-Freigabe.
