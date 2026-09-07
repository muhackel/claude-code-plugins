# Laufzeitverträge

Die CLI zeigt nach jedem Zustandswechsel die neue `revision`. Jeder mutierende Missionsbefehl außer `new` benötigt die zuvor gelesene Revision. Die Überprüfung schützt vor konkurrierenden Entscheidungen. Rohdaten stehen unter `status <id> --full`.

## Spec und Autorisierung

`spec` übernimmt zwei Dateien: eine Markdown-Spec und einen JSON-Vertrag mit genau `criteria`, `allowed_paths` und `checks`. Kriterien brauchen eindeutige IDs nach `[a-z0-9][a-z0-9-]{0,63}`, Beschreibung und Prüfmethode. Alle Kriterien sind Pflichtkriterien.

Schreibpfade sind konkrete relative Dateien oder Verzeichnisse. `..`, absolute Pfade, `.`, `.git` und `.philharmonie` sind unzulässig. Symlinks im Zielpfad werden abgelehnt. Neue Dateien können ausdrücklich freigegeben werden. Der Generator arbeitet in einem Snapshot; der Kern übernimmt ausschließlich erlaubte Änderungen, nachdem er den Ausgangsstand erneut geprüft hat.

`checks` enthält Prüfungen mit eindeutiger `id` und einer `argv`-Liste. Beispiele:

```json
[
  {"id": "flake", "argv": ["nix", "flake", "check", "-L"]},
  {"id": "shellcheck", "argv": ["nix", "shell", "nixpkgs#shellcheck", "-c", "shellcheck", "scripts/example.sh"]}
]
```

Jede Prüfung läuft in einem eigenen Snapshot. Der Nix-Daemon bleibt standardmäßig verborgen. Die gesonderte Konfiguration `check_nix_daemon` erlaubt ihn ausschließlich den explizit genehmigten Prüfkommandos; das ist ein Zugriff auf einen Host-Dienst und keine gewöhnliche Cache-Freigabe. Vor dem Aktivieren muss dieser Zugriff vom Nutzerauftrag gedeckt sein. Die Agenten selbst erhalten ihn nicht. Ohne passende Prüfumgebung muss der fehlende Nachweis sichtbar bleiben.

`approve` speichert den Wortlaut der Nutzeranweisung samt Spec-Hash. Es ermittelt nicht selbst, ob dieser Wortlaut wirklich vom Nutzer stammt: Das verantwortet die Hauptsitzung. Die CLI ist eine Konsistenzprüfung, keine Authentifizierung des Chat-Urhebers.

Vor `approve` führt `review-spec <id> --revision <n>` die Spec-Gegenprüfung aus. `new --planner claude` beziehungsweise `--planner codex` bindet die planende CLI; ohne Angabe wird die Haupt-CLI aus dem Aufrufkontext ermittelt. Der Reviewer ist zwingend die andere CLI. Altmissionen ohne Bindung können diese beim ersten Gegenreview über `--planner` erhalten.

Der Zustandskern berechnet den Spec-Score aus fünf begründeten Teilnoten: `coverage` bis 25, `verification` bis 25, `scope` bis 20, `evidence` bis 15 und `risks` bis 15. [spec_reviewer.json](../schemas/spec_reviewer.json) verlangt Begründung und Beleg je Kategorie. Blocker und offene Fragen stehen separat. Offene Blocker verhindern die Freigabe, eine Punkteschwelle gibt es nicht. Eine fehlende bindende Nutzerentscheidung muss als Blocker ausgewiesen werden.

Der Review bindet Spec-Revision, Spec-Hash, Vertrags-Hash und Projektfingerprint. Der Bericht wird archiviert und vor der Freigabe erneut geprüft. Änderungen machen die Bewertung ungültig; eine neue Spec oder `replan` entfernt den aktiven Score. `review-spec` erhöht die Zustandsrevision und bleibt in `awaiting_spec`. Vor dem nächsten Schritt `status --full` lesen. Bereits erteilte Autorisierung wird übernommen, soweit sie die geprüfte Spec deckt.

Planungsagents sammeln lesend Quellen; die Hauptsitzung führt die Spec zusammen. Generatoren und einzelne `execute`-Aufträge erhalten vier native Agenttypen mit ausdrücklicher Modellzuordnung. Teilaufgaben, Abhängigkeiten, Dateizuständigkeiten und Ergebnisse folgen der [Delegationsregel](delegation.md). Selbstberichte im Ergebnis und native Delegationsereignisse in den lokalen Logs werden getrennt erhalten. Ein kleiner unteilbarer Auftrag darf begründet ohne Subagent bearbeitet werden.

## Zustand

Fachliche Phasen: `planning`, `awaiting_spec`, `implementing`, `evaluating`, `awaiting_acceptance`, `completed`, `cancelled`. Die Aktivität ist davon getrennt: `idle`, `running`, `paused`, `blocked`. Runs haben eigene IDs, Prozessidentitäten, Start-/Endzeiten und einen Status (`prepared`, `running`, `succeeded`, `failed`, `interrupted`, `cancelled`).

Der Zustandskern schreibt unter einer lokalen Dateisperre und prüft die erwartete Revision. Zustand und Ereignis werden gemeinsam atomar gespeichert. Ein Koordinator hält die Missionssperre während eines Runs. Eine zusätzliche Checkout-Sperre verhindert überlappende Generator- oder Evaluator-Läufe verschiedener Missionen im selben Arbeitsstand. Für tatsächliche Parallelität können getrennte Worktrees verwendet werden.

Ein Run beginnt hinter einer Pipe-Startbarriere. Erst nach Speicherung seiner Prozessidentität gibt der Supervisor den Auftrag frei. Stirbt er vorher, erhält das Kind keine Starterlaubnis. Bubblewrap beendet seinen Prozessbaum beim Tod des Supervisors. Beim Resume prüft der Kern Host, Boot-ID, PID und Startzeit; eine Datei oder ein Heartbeat genügt nicht.

Snapshots enthalten den erfassten Dateistand. Die Übernahme hält in `apply.json` fest, welche Änderungen bereits im Original angekommen sind. Ein Crash während mehrerer Dateiänderungen ist keine atomare Projekttransaktion: Teiländerungen bleiben erhalten und müssen vor einem neuen Versuch abgeglichen werden. Es gibt keinen automatischen Reset.

## Berichte und Urteile

[generator.json](../schemas/generator.json) und [evaluator.json](../schemas/evaluator.json) sind die Ausgabeformate. `run_id` und `spec_hash` binden die Antwort an den Auftrag. Ein CLI-Exit-Code 0 oder ein gut formulierter Antworttext ersetzt kein gültiges Ergebnis.

Der Evaluator weist jede Kriterien-ID genau einmal aus und ergänzt Belege beziehungsweise konkrete Prüfungshindernisse. `fail` hat Vorrang vor `unverified`; ohne Fehler, aber mit offenen Nachweisen folgt `BLOCKED`. `PASS` verlangt vollständige Nachweise und keine erheblichen Findings. Fehlgeschlagene Pflichtkommandos verhindern PASS zusätzlich im Kern.

Jeder Evaluator prüft zunächst unabhängig und gleicht anschließend seine Bewertung mit dem Generatorbericht ab. Bei Doppelprüfung sehen beide Prüfer im ersten Durchgang nur dieselbe Spec, denselben Snapshot und die automatischen Prüfbelege. Danach erhalten sie beide Bewertungen und den Generatorbericht. Nach höchstens `max_discussions` Abstimmungsrunden zusätzlich zur Erstprüfung bleibt ungelöster Dissens als Blockade stehen. Kriterienstatus sowie IDs, Kriterien und Schweregrade erheblicher Findings müssen übereinstimmen. Die vereinigten Befunde beider Prüfer gehen in den Korrekturauftrag ein.

Rundenberichte werden als JSON und Markdown im Missionsordner erhalten. Sie enthalten Handover, Ergebnisse, Belege, Prüfbefehle, Exit-Codes, Nix-Version und die verwendeten Adapter. Für weitere Prüfwerkzeuge deren Versionsausgabe im vereinbarten Prüfbefehl erfassen. Der Kern registriert den JSON-Bericht mit SHA-256 und prüft ihn vor der Abnahme erneut. Rohantworten und stderr liegen nur unter `.philharmonie/local/`. Review Briefing und Summary verweisen auf die dauerhaften Berichte; weitere Hinweise und nicht bestätigte Generatorangaben bleiben erhalten.

## Konfiguration und Grenzen

`.philharmonie/config.json` enthält die Rollen-Ziele (`auto`, `claude`, `codex`), optional ein ausdrücklich gewähltes Modell, Effort, Zweitmeinung, Runden-/Zeitgrenzen und die gesonderte Nix-Daemon-Freigabe für Prüfkommandos. `auto` wählt bei gesetztem `CLAUDECODE` Codex, sonst Claude. Die Modellauflösung findet vor dem jeweiligen CLI-Aufruf statt und wird protokolliert.

Die lokale Laufzeit ist Linux-spezifisch (Bubblewrap, `/proc`, Dateisperren). Koordination über mehrere Hosts oder Netzdateisysteme ist nicht unterstützt. Ein frischer Klon ohne lokalen Zustand wird nicht als fortsetzbare Mission interpretiert; eine Folgemission kann die vorhandenen Spec-/Ergebnisdokumente als Quellen übernehmen.

Beim ersten Run übernimmt die Mission die Projektkonfiguration. Jede Rolle bindet die tatsächlich aufgelöste CLI, Version, Modell und Effort. Spätere Änderungen der Projektdefaults ändern laufende Missionen nicht. Ein veränderter Adapter erfordert eine neue Planung mit geprüftem Vertrag; `replan` löst die Bindung für die neue Spec. Dadurch wechselt ein Retry seine CLI-Konfiguration nicht stillschweigend.
