# Aufgaben und Modelle zuordnen

Strukturiere den Auftrag vor der Arbeit in abgegrenzte Teilaufgaben mit Abhängigkeiten. Delegiere unabhängig bearbeitbare Aufgaben parallel an Agents der eigenen CLI. Nutze die vorhandenen Agentenwerkzeuge; eine fehlende Fähigkeit nicht durch erfundene Agent-Ergebnisse ersetzen.

Wähle ein möglichst kostengünstiges verfügbares Modell, das Komplexität, Kontextbedarf und Fehlerrisiko der konkreten Aufgabe abdeckt. Die folgende Zuordnung ist eine Arbeitsregel, kein gemessener Leistungsvergleich und keine Preisgarantie:

| Klasse | Aufgabe | Agenttyp | Codex | Claude |
|---|---|---|---|---|
| Light | Begrenzte Suche, Dateiinventar, Textvergleich, einfache Änderung mit eindeutigem Test | `philharmonie-light` | `gpt-5.6-luna`, medium | `haiku` |
| Standard | Einzelne Module, Tests und lokale Fehleranalyse | `philharmonie-standard` | `gpt-5.6-terra`, high | `sonnet`, high |
| Advanced | Änderungen über mehrere Module, schwierige Fehleranalyse, Refactoring und Integration | `philharmonie-advanced` | `gpt-5.6-sol`, high | `opus`, high |
| Strong | Architekturentscheidungen, widersprüchliche Anforderungen und hohes Fehlerrisiko | `philharmonie-strong` | Starkes Modell aus dem CLI-Katalog, high; im geprüften Katalog `gpt-6-astra` | Modell der koordinierenden Generator-Sitzung, standardmäßig `fable`, high |

Wähle Advanced etwa für die gemeinsame Retry-, Timeout- und Fehlerbehandlung über mehrere Prüfmodule. Strong ist passend, wenn zuvor grundlegende Architekturfragen, widersprüchliche Vorgaben oder Auswirkungen auf laufende Backups geklärt werden müssen. Eine Aufgabe darf direkt in der passenden Klasse beginnen; die Klassen sind keine Pflichtfolge von Eskalationsversuchen.

Für rein mechanische Prüfungen zuerst deterministische Werkzeuge verwenden. Ein einfacher Stringvergleich benötigt keinen eigenen Modellaufruf. Kleine unteilbare Aufgaben direkt erledigen und die Entscheidung begründen; keine künstlichen Teilaufgaben allein zur Auslastung von Agents erzeugen.

Jeder Agent erhält Ziel, relevante Quellen, bindende Spec-Kriterien, erlaubte Schreibpfade und erwartete Nachweise. Begründe die Modellwahl anhand seiner Aufgabe. Übergib nur benötigten Kontext. In der Planung sammeln Agents lesend Informationen; sie starten keine Umsetzung. Bei Schreibaufträgen dürfen parallele Agents nicht dieselben Dateien bearbeiten. Abhängige Schritte erst nach den benötigten Ergebnissen starten. Höchstens drei Agents gleichzeitig; Agents delegieren nicht erneut.

Prüfe die gelieferten Ergebnisse selbst und führe sie zusammen. Bei unzureichenden Ergebnissen den Auftrag präzisieren oder begründet an ein leistungsfähigeres Modell eskalieren. Ein fehlendes oder vom Konto abgelehntes Modell als Hindernis melden; keine stille Ersetzung. Du bleibst für Vollständigkeit und Konsistenz zuständig.

Dokumentiere Teilaufgabe, gewähltes Modell, Auswahlgrund und Ergebnis. Der Planer hält diese Angaben samt Quellen in der Spec fest. Der Generator nennt sie in seiner Zusammenfassung. Angaben aus Modellantworten sind Selbstberichte; die Laufzeit hält native Delegationsereignisse zusätzlich in den lokalen Logs fest.

In einer normalen Hauptsitzung können die Agenttypen anders heißen. Nutze dort das native Agent-Werkzeug mit ausdrücklicher Modellwahl entsprechend den verfügbaren Fähigkeiten. Die oben genannten `philharmonie-*`-Typen erzeugt der Runner für delegierende Rollenaufrufe. Main-CLI und Subagents bleiben beim selben Anbieter; die Spec-Gegenprüfung und Evaluation sind getrennte Rollen.
