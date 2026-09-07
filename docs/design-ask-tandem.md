---
tags: [design, plugin, philharmonie, ask, tandemkit, orchestration]
description: Entwurf für Philharmonie, ein Claude-Code- und Codex-Plugin mit Cross-CLI-Aufrufen aus ask, getrennten Arbeitsrollen und einer persistenten Projekt-State-Machine
---

# Design: Philharmonie aus ask und TandemKit

Stand: 2026-09-07. Festgelegter Plugin-Name: **Philharmonie** (`philharmonie`). Dieser Entwurf ist die Grundlage der beauftragten Implementierung unter `plugins/philharmonie/`. Umsetzungsentscheidungen und Prüfungen stehen in Abschnitt 10.

Das Plugin verbindet den Cross-CLI-Aufruf von `ask` mit einer überprüfbaren Spezifikation und getrennten Rollen für Umsetzung und Bewertung. Eine laufende Hauptsitzung koordiniert die Arbeit. Aufträge, Entscheidungen und Ergebnisse bleiben im Projekt erhalten, sodass eine neue Sitzung sie fortsetzen kann.

Grundlage ist die [[evaluierung-tandemkit|TandemKit-Evaluierung]]. Die folgende Architektur entstand als eigener Vorschlag. Sebastian hat anschließend mit „... nach dem das jetzt einen namen hat bau mal den skill nach deinem design dokument.“ die Umsetzung beauftragt. Die als Alternativen beschriebenen Varianten bleiben Alternativen; die Implementierung verwendet die empfohlenen Defaults.

## 1. Was übernommen wird

| Herkunft | Übernahme | Anpassung |
|---|---|---|
| `ask` | Handover mit Ziel, Kontext, Auftrag und Grenzen; Aufruf der jeweils anderen CLI | Transport von Rollen und Projektzustand trennen; strukturierte Ergebnisse ergänzen |
| `ask` | Einzelaufrufe zum Fragen und Ausführen | Auch ohne Projektinitialisierung nutzbar halten |
| `ask` | Geteilter Plugin-Inhalt für Claude Code und Codex; Nix-Laufumgebung | Neues Plugin mit beiden Manifesten und beiden Marketplace-Einträgen paketieren |
| TandemKit-Evaluierung | Spec mit Nutzerabsicht, Abnahmekriterien, Entscheidungen und Ausschlüssen | Kriterien mit stabilen IDs und konkreter Prüfmethode versehen |
| TandemKit-Evaluierung | Eigener Evaluator, unabhängige Untersuchung, Review Briefing | Rollen mit frischem Kontext aufrufen; Testausführung gesondert absichern |
| TandemKit-Evaluierung | Generator/Evaluator-Schleife und Klärung wiederholter Meinungsverschiedenheiten | Übergänge durch ein Programm prüfen; Runden begrenzen |
| TandemKit-Evaluierung | Nutzerabnahme nach fachlichem PASS | Vorhandene Autorisierung berücksichtigen; Abschluss von Commit, Merge und Deployment trennen |

TandemKit beschreibt drei Rollen-Sitzungen und zusätzliche Codex-Aufrufe während Planung und Bewertung. Für Philharmonie wird ein Koordinator vorgeschlagen, der Rollen bei Bedarf startet. Dauerhaft wartende Rollen-Sitzungen und dateibasierte Wecksignale entfallen. Das ist eine Architekturentscheidung dieses Entwurfs. [TandemKit README](https://github.com/FlineDev/TandemKit)

Der eingesehene `ask`-Code liefert bisher Text auf stdout, Fortschritt auf stderr und den Exit-Code der Ziel-CLI. Er hat keine dauerhaften Run-IDs, keine Ergebnisvalidierung und keine State-Machine. Die Branch-Prüfung für `/execute` steht im Command, nicht im Shell-Skript. Diese Prüfungen müssen für das neue Plugin im ausführenden Programm liegen. Quellen: [ask.sh](../plugins/ask/scripts/ask.sh), [execute.md](../plugins/ask/commands/execute.md), [Handover-Skill](../plugins/ask/skills/handover/SKILL.md).

## 2. Umfang und Bedienung

Philharmonie soll Nix-/Bash-Projekte sowie konzeptionelle und fachliche Dokumente bearbeiten können. Domänenwissen bleibt bei den vorhandenen Fachplugins. Philharmonie organisiert Auftrag, Zuständigkeit und Prüfung; etwaige Vault-Schreibaufträge gehen nach den bestehenden Regeln an Karin.

Es gibt zwei Nutzungstiefen:

- **Einzelauftrag:** Eine Frage, ein Review oder eine delegierte Änderung. Handover und Ergebnis reichen; es entsteht keine Mission und keine Pflicht zur Planungsschleife.
- **Mission:** Ein abgegrenztes Ergebnis mit Spec, Arbeitsrunden, Prüfung und Abschluss. Ein Projekt kann mehrere Missionen enthalten. Eine Mission ist kein Zustand des gesamten Git-Repositories.

Die folgenden Commands sind die Plugin-Schnittstellen. Der Namespace verhindert Kollisionen mit dem bestehenden `ask`.

| Command | Verhalten |
|---|---|
| `/philharmonie:ask [Frage]` | Andere CLI lesend fragen; ohne Frage das bestehende Standard-Review |
| `/philharmonie:execute <Auftrag>` | Begrenzten Schreibauftrag ausführen; fehlender Auftrag führt zur Rückfrage |
| `/philharmonie:plan <Ziel>` | Projekt untersuchen, offene Entscheidungen klären und eine Spec entwerfen |
| `/philharmonie:run <Mission>` | Erlaubte Arbeits- und Prüfschritte bis zur Nutzerentscheidung, Pause, Blockade oder Abnahme ausführen |
| `/philharmonie:status [Mission]` | Phase, laufenden Auftrag, letzte Belege und nächste notwendige Handlung anzeigen |
| `/philharmonie:resume <Mission>` | Zustand und echte Prozesse prüfen, dann an der belegten Stelle fortsetzen |
| `/philharmonie:pause <Mission>` | Neue Starts verhindern und einen laufenden Schreibauftrag kontrolliert anhalten |
| `/philharmonie:cancel <Mission>` | Mission beenden; Teiländerungen und Belege erhalten |
| `/philharmonie:accept <Mission>` | Das geprüfte Ergebnis nach Nutzeranweisung abnehmen und den Abschluss erzeugen |

Freigaben können auch aus einer eindeutigen Chat-Anweisung stammen. Ein Nutzer muss eine bereits erteilte Erlaubnis nicht noch einmal durch einen Command bestätigen. Bleibt bei mehreren Missionen der Bezug unklar, fragt der Koordinator nach. Es gibt kein globales `currentMission`, dessen Wert alle Sitzungen ungefragt übernehmen.

Solange der Koordinator aktiv ist, setzt er die freigegebene Arbeit selbstständig fort. Nach dem Ende der Hauptsitzung startet kein Dateiwatcher eine neue Sitzung. Eine neue Hauptsitzung übernimmt mit `resume`; noch laufende Kindprozesse werden dabei zuerst geprüft.

## 3. Rollen und technische Zuständigkeiten

Der **Koordinator** ist die Hauptsitzung. Er stellt Fragen, bildet konkrete Aufträge und zeigt Ergebnisse. Ein kleines lokales Programm prüft Zustandsübergänge und verwaltet Prozesse. Die Hauptsitzung darf einen Zustand nicht allein durch das Editieren einer JSON-Datei erzwingen.

Der **Planner** untersucht das Projekt und formuliert kleine, prüfbare Arbeitsziele. Bei offenen Weichen liefert er konkrete Alternativen. Er darf eine technische Vorgabe aus dem Nutzerauftrag nicht zu einer unverbindlichen Empfehlung abschwächen. Die Spec enthält WAS und WARUM; vorgegebene Werkzeuge, Pfade oder Architekturbedingungen bleiben bindende Randbedingungen.

Der **Generator** arbeitet gegen eine bestimmte Spec-Version. Sein Ergebnis umfasst Änderungen, ausgeführte Prüfungen und noch offene Punkte. Er ändert weder Kriterien noch Abnahmestatus. Eine fachlich nötige Scope-Änderung geht zum Planner zurück.

Der **Evaluator** startet mit frischem Kontext. Er erhält die Spec, relevante Projektquellen, den zu prüfenden Stand und den Prüfauftrag. Den Generator-Bericht bekommt er erst nach seiner eigenen Erstprüfung zum Abgleich. Er liest relevante Dateien vollständig, prüft jedes Kriterium und führt die dafür vereinbarten Prüfungen aus. Ein fehlerfreier Diff allein genügt nicht.

Eine Rolle ist nicht fest an Claude oder Codex gebunden. Der Default kann wie bei `ask` die jeweils andere CLI verwenden. Die Zuordnung wird je Mission gespeichert. Zusätzliche Zweitmeinungen sind konfigurierbar; sie gehören bei kleinen Aufträgen nicht automatisch zu jeder Runde. Ein bewusst gewählter Betrieb mit nur einer verfügbaren CLI verwendet getrennte Kontexte und weist diese Einschränkung aus. Eine fehlende zweite CLI führt bei vereinbarter Doppelprüfung zu `blocked`, nicht zu einem stillen Ersatz.

Die technische Aufteilung:

| Komponente | Verantwortung | Darf nicht |
|---|---|---|
| Skills und Commands | Rollenbriefing, Fragen, Ergebnisdarstellung | Zustandsregeln durch eigene Auslegung ersetzen |
| Zustandskern | Schema, Übergänge, Revisionen, Freigabebezüge, Sperren | Aus einem Exit-Code fachlichen Erfolg ableiten |
| Runner | Auftrag starten, Prozess identifizieren, Ausgabe sichern, Abbruch verfolgen | Eigenständig den Scope erweitern oder Rechte erhöhen |
| CLI-Adapter | Claude-/Codex-Aufruf, Modellwahl, Fähigkeiten und Ergebnisnormalisierung | Unbekannte Flags ungeprüft weiterreichen |
| Prüfprofile | Prüfmethode für Nix, Bash oder Dokumente | Ohne Nachweis PASS vergeben |

Vorgeschlagene Umsetzung: Python-Standardbibliothek für Zustand und Prozessverwaltung, kleine Bash-Adapter für die bestehenden CLI-Aufrufe. JSON-Schemata dokumentieren das Austauschformat. Nix stellt Interpreter, Validator und Prüfwerkzeuge bereit. Modellnamen und CLI-Flags bleiben im Adapter; das Design schreibt keine vermeintlich dauerhaften Hersteller-Defaults fest.

## 4. Projektdateien und Verträge

Vorgeschlagener Projektpfad ist `.philharmonie/`. Dieser Pfad gehört zum Entwurf; er wird durch dieses Dokument nicht angelegt.

| Pfad im Projekt | Inhalt | Git |
|---|---|---|
| `.philharmonie/config.json` | Schemaversion, Rollenbelegung, Prüfprofile und Grenzen | Ja, ohne Zugangsdaten und lokale Absolutpfade |
| `.philharmonie/missions/<id>/Spec.md` | Aktuelle Spec mit stabilen Kriterien-IDs | Ja |
| `.philharmonie/missions/<id>/specs/<revision>.md` | Unveränderliche freigegebene Spec-Fassungen | Ja |
| `.philharmonie/missions/<id>/Decisions.md` | Entscheidungen, Alternativen, Urheber und Geltungsbereich | Ja |
| `.philharmonie/missions/<id>/rounds/<n>/` | Handover, Generator-Bericht, Evaluation und Belegverweise | Ja, nach Prüfung auf sensible Inhalte |
| `.philharmonie/missions/<id>/Summary.md` | Abgenommenes Ergebnis, bestätigte und nicht bestätigte Eigenschaften | Ja |
| `.philharmonie/local/<id>/state.json` | Maschinenzustand samt Übergangshistorie und Run-Metadaten | Nein |
| `.philharmonie/local/<id>/runs/<run-id>/` | Rohantworten, stderr, Testlogs, temporäre Ausgaben | Nein |
| `.philharmonie/local/locks/` | Lokale Sperren für Mission und Checkout | Nein |

Die Mission-ID bleibt beim Umbenennen eines Titels gleich. In mehreren Worktrees liegen getrennte Laufzeitverzeichnisse. Ein frischer Klon enthält die fachlichen Dokumente, aber keinen fortsetzbaren lokalen Prozesszustand. Er braucht eine ausdrückliche Übernahmeprüfung; `Summary.md` allein rekonstruiert keinen aktiven Run.

Die Rundenberichte halten die für die Abnahme nötigen Belege dauerhaft fest: geprüfter Stand, Prüfbefehl, Werkzeugversion, Exit-Code und relevante Ausgabe oder Quellenstelle. Ein Verweis auf ein vergängliches lokales Log reicht dafür nicht. Große Rohlogs können lokal bleiben; ihr Umfang und ihre Verfügbarkeit werden ausgewiesen.

### Spec

Die Spec enthält Missionstyp, ursprünglichen Nutzerauftrag im Wortlaut, Ziel, Quellen/Befunde, Abnahmekriterien, Randfälle, Entscheidungen mit Alternativen, Ausschlüsse und mögliche Lösungswege. Eigene Vorschläge und Nutzerfestlegungen sind unterscheidbar. Ein Quellenverweis trägt Pfad oder URL und den geprüften Stand; fachliche Normen brauchen die nach den Projektregeln archivierte Quelle.

Jedes Kriterium erhält eine ID und eine Prüfmethode. Beispiel für einen späteren Runner:

> AC-03: Nach einem Abbruch des Koordinators startet `resume` keinen zweiten Generator, solange der erste Prozess nachweislich läuft. Prüfung durch einen kontrollierten Prozessabbruch und anschließenden Resume-Aufruf; Beleg sind Prozessidentität und Run-Protokoll.

Eine freigegebene Spec hat Revision und Inhalts-Hash. Änderungen erzeugen eine neue Revision und machen betroffene Freigaben sowie Evaluationen ungültig. Offene Kriterien dürfen beim Abschluss nicht verschwinden, um ein PASS zu erreichen.

### Handover und Ergebnis

Das vorhandene Markdown-Handover bleibt lesbar. Ein maschinenlesbarer Umschlag ergänzt `mission_id`, `run_id`, Rolle, Spec-Revision, Arbeitsverzeichnis, Stand-Fingerabdruck, erlaubte Pfade, Rechteprofil und erwartetes Ergebnisschema. Die Daten werden als Datei oder über stdin übergeben, nicht zu Shell-Code zusammengesetzt.

Eine Evaluation enthält für jede Kriterien-ID `pass`, `fail` oder `unverified`, Belegverweise und eine Begründung. Findings bekommen stabile IDs, Schweregrad und betroffene Kriterien. Das Gesamturteil lautet:

- `PASS`: Alle Pflichtkriterien sind nachgewiesen; es fehlen keine vereinbarten Prüfungen und keine blockierenden Befunde sind offen.
- `FAIL`: Mindestens ein Kriterium ist nachweislich verletzt. Weitere ungeprüfte Kriterien bleiben sichtbar.
- `BLOCKED`: Die Prüfung kann kein vollständiges Urteil liefern, etwa wegen fehlender Testumgebung oder Quellen.

Ein belegter Fehler führt zu `FAIL`, auch wenn andere Kriterien noch `unverified` sind. Ohne belegten Fehler, aber mit fehlenden Pflichtnachweisen lautet das Urteil `BLOCKED`. Der Koordinator startet eine Korrektur nur, wenn die dokumentierten Hindernisse diese Arbeit zulassen.

Ein Exit-Code `0` bedeutet nur, dass die Ziel-CLI erfolgreich beendet wurde. Fehlendes oder ungültiges Ergebnis-JSON ist ein Protokollfehler. Rohantwort und stderr bleiben erhalten. Der Koordinator validiert die Struktur; der Evaluator verantwortet die fachlichen Aussagen. Keiner dieser Schritte ersetzt den anderen.

## 5. Projekt-State-Machine

Empfehlung: Eine persistente State-Machine pro Mission mit genau einem aktiven Koordinator. Andere Sitzungen dürfen den Zustand lesen und Ergebnisse einreichen. Sie müssen für die Fortsetzung die Koordination übernehmen. Der ursprüngliche Vorschlag aus der Evaluierung mit zwei dauerhaft offenen Rollen-Sitzungen bleibt eine Alternative, ist hier aber nicht Voraussetzung.

Der Zustand trennt drei Dinge:

- `phase`: Fachlicher Stand der Mission.
- `activity`: Ob neue Arbeit möglich ist (`idle`), ein Auftrag läuft (`running`), der Nutzer pausiert hat (`paused`) oder eine Voraussetzung fehlt (`blocked`).
- `run.status`: Lebenszyklus eines einzelnen CLI-Auftrags: `prepared`, `running`, `succeeded`, `failed`, `interrupted` oder `cancelled`.

Eine offene fachliche Nutzerentscheidung steht in `awaiting_spec` oder `awaiting_acceptance` mit `activity=idle`. `blocked` benennt ein konkretes Hindernis mit zuständiger Stelle und Fortsetzungsbedingung. Ein CLI-Absturz beendet den Run; die fachliche Phase bleibt erhalten. In `completed` und `cancelled` muss `activity=idle` sein und es darf keinen laufenden Run geben.

### Fachliche Übergänge

| Von | Ereignis | Nach | Bedingung |
|---|---|---|---|
| Noch keine Mission | Nutzer beauftragt Planung | `planning` | Ziel und Projektbezug sind bekannt |
| `planning` | Spec ist vorlagefähig | `awaiting_spec` | Kriterien prüfbar, offene Entscheidungen ausgewiesen |
| `awaiting_spec` | Änderungswunsch | `planning` | Feedback zur Spec dokumentiert |
| `awaiting_spec` | Auftrag deckt Umsetzung dieser Spec | `implementing` | Autorisierung an Spec-Revision und Scope gebunden |
| `implementing` | Generator liefert einen Prüfstand | `evaluating` | Run beendet, Änderungen erfasst, Stand eingefroren |
| `evaluating` | Urteil `FAIL` | `implementing` | Befunde belegt, Korrektur im genehmigten Scope möglich |
| `evaluating` | Urteil `BLOCKED` | `evaluating` | `activity=blocked`; fehlenden Nachweis benennen |
| `evaluating` | Urteil `PASS` | `awaiting_acceptance` | Alle Kriterien abgedeckt, Urteil gilt für den vorliegenden Stand |
| `awaiting_acceptance` | Nutzer meldet Fehler im Scope | `implementing` | Feedback als Arbeitsauftrag dokumentiert |
| Jede offene Phase | Neue Anforderungen ändern den Scope | `planning` | Laufende Arbeit angehalten; neue Spec-Revision erforderlich |
| `awaiting_acceptance` | Nutzer nimmt Ergebnis ab | `completed` | Abnahme gilt für diesen Stand; Summary und Belege vorhanden |
| Jede offene Phase | Nutzer bricht ab | `cancelled` | Aktive Runs beendet; Teiländerungen dokumentiert |

Eine erneute Bearbeitung nach `completed` oder `cancelled` erzeugt eine verknüpfte Folgemission. Der abgeschlossene Verlauf wird nicht überschrieben.

Eine klare Anweisung wie „implementiere die freigegebene Spec“ trägt bereits die Umsetzungsfreigabe. Das Plugin fragt nicht erneut, nur weil es intern `awaiting_spec` durchläuft. Der empfohlene Standard verlangt für die fachliche Endabnahme eine Nutzerentscheidung. Eine vorab erteilte Abschlussautorisierung kann diese Entscheidung abdecken, wenn ihre objektiven Bedingungen ausdrücklich festgelegt wurden. Ein PASS allein ist keine Nutzerfreigabe. Commit, Push, Merge oder Deployment benötigen den jeweils passenden Auftrag; sie sind keine impliziten Folgen von `completed`.

### Pause, Fehler und Fortsetzung

`pause` setzt zunächst eine dauerhafte Start-Sperre. Der Runner beendet einen laufenden Auftrag kontrolliert und erfasst dessen tatsächlichen Zustand. Erst danach gilt `activity=paused`; der Run erhält `interrupted`. `cancel` verwendet denselben Stoppmechanismus mit Run-Status `cancelled` und wechselt anschließend die Phase. Beide Operationen erhalten Teiländerungen; automatisches Zurücksetzen oder Stashen findet nicht statt.

`resume` liest Projektregeln, Spec, Zustand, offene Befunde und Git-Stand neu. Es prüft die Prozessidentität anhand von Run-ID, Host, PID und Startzeit oder einem vom Adapter unterstützten Prozess-Handle. Ein fehlender Logeintrag, abgelaufener Beobachtungs-Timeout oder alter Heartbeat beweist keinen Prozessabbruch. Bei unklarer Erreichbarkeit bleibt ein Neustart gesperrt, bis der tatsächliche Zustand geklärt ist.

Ist der alte Prozess nachweislich beendet, erhält ein erneuter Versuch eine neue Run-ID und einen Verweis auf den vorherigen Versuch. Ein unterbrochener Schreibauftrag erfordert zuerst einen Abgleich seiner Teiländerungen. Ein abgestürzter Evaluator kann denselben unveränderten Prüfstand erneut prüfen. Kein Retry verändert unbemerkt Modell, Flags, Rechte oder Auftrag.

`paused` wird nur durch einen Fortsetzungsauftrag aufgehoben, `blocked` erst nach belegter Beseitigung des Hindernisses. Danach steht `activity` zunächst auf `idle` und wechselt beim registrierten Prozessstart zu `running`. Ein beendeter Run gibt den nächsten fachlichen Übergang frei, sofern sein Ergebnis gültig ist; technische Fehler setzen `activity=blocked`. Verspätete Ergebnisse werden nur für ihre ursprüngliche Run-ID, Spec-Revision und ihren Prüfstand angenommen.

### Speicherung und konkurrierende Sitzungen

Der Zustandskern hält eine lokale Betriebssystem-Sperre für kurze Änderungen und prüft zusätzlich `expected_revision`. Er schreibt einen validierten neuen Zustand in eine temporäre Datei im selben Verzeichnis, synchronisiert sie und ersetzt `state.json` atomar. Ein neuer Zustand enthält auch sein Übergangsereignis. Ein separates Ereignislog kann daraus erzeugt werden, ist aber keine zweite maßgebliche Quelle.

Berichte werden zuerst vollständig geschrieben und mit Hash registriert; danach darf ein Übergang auf sie verweisen. Ein Absturz davor hinterlässt höchstens ein unreferenziertes Artefakt. Recovery darf dieses prüfen, aber daraus nicht ungefragt eine abgeschlossene Phase ableiten.

Für Prozessstarts hält ein lokaler Supervisor die Ausführungssperre. Er schreibt zuerst den Run als `prepared`, startet das Kind mit einer Startbarriere und registriert die Prozessidentität, bevor der Auftrag freigegeben wird. Stirbt der Supervisor in dieser Lücke, darf das Kind den Schreibauftrag nicht beginnen. Dieses Startprotokoll muss mit gezielten Absturztests geprüft werden.

Pro Checkout läuft höchstens ein schreibender Generator, auch wenn mehrere Missionen vorhanden sind. Die Evaluation arbeitet auf einem festgehaltenen Prüfstand in einer isolierten Umgebung. Der Fingerabdruck umfasst die Spec, HEAD, Index, Änderungen im Arbeitsbaum und relevante ungetrackte Dateien. Laufzeitlogs und generierte Testausgaben werden nach einer dokumentierten Regel ausgeschlossen. Nur HEAD oder `git diff` zu speichern wäre unzureichend.

Vor einem Schreibauftrag prüft der Runner den Branch und die vorhandenen Änderungen. Auf `main` oder `master` beginnt keine Umsetzung. Fremde Änderungen werden erfasst und dürfen weder überschrieben noch automatisch gestasht werden. Lassen sie sich vom Auftrag nicht trennen, ist ein eigener Arbeitsstand oder eine Nutzerentscheidung nötig.

Unbeteiligte Agenten können Plugin-Sperren ignorieren. Deshalb prüft der Koordinator den Stand vor Übergabe und Abnahme erneut. Bei Änderungen ist das Urteil für den neuen Stand ungültig und eine neue Evaluation nötig. Schreibende Missionen können für Parallelität eigene Worktrees erhalten; deren vollständige Zielpfade sind vor der Anlage nach den Projektregeln abzustimmen. Das MVP garantiert keine Koordination über gemeinsam gemountete Netzdateisysteme oder mehrere Hosts.

### Empfehlungen und Alternativen des Entwurfs

| Entscheidung | Empfehlung im Entwurf | Alternative und Folge |
|---|---|---|
| Steuerung | Ein Koordinator mit persistentem Zustand | Zwei aktive Rollen-Sitzungen; braucht zusätzlich zuverlässige Übergabe und Besitzerwechsel |
| Granularität | State-Machine pro Mission; Arbeitsaufträge innerhalb der Mission | Eigene Task-State-Machines mit Abhängigkeiten; sinnvoll erst bei größeren parallelen Vorhaben |
| Endabnahme | Nutzer nimmt den konkreten Prüfstand ab; vorhandene Abschlussautorisierung gilt weiter | Automatischer Abschluss nach vorab vereinbarter Policy; braucht ebenso klare und objektive Bedingungen |
| Zweitmeinung | Getrennter Evaluator immer, zusätzliches Modell bei festgelegtem Bedarf | Zwei Modelle in jeder Planungs- und Prüfrunde; mehr Aufrufe und längere Laufzeit |

Der Bauauftrag verwendet die empfohlenen Defaults. Das behauptet keine gesonderte Nutzerentscheidung zu jeder Alternative. Die State-Machine lässt sich weiterentwickeln, ohne Transport, Handover-Format und Kriterienmodell erneut zu entwerfen.

## 6. Prüfungen, Rechte und Dissens

Das bestehende `ask` hat zwei Modi. Der Claude-Aufruf im lesenden Modus erlaubt Dateiwerkzeuge und ausgewählte Git-Abfragen; freie Testkommandos gehören nicht dazu. Im schreibenden Modus ist die Begrenzung auf den Workspace laut Handover-Skill bei Claude eine Anweisung und keine Dateisystem-Sandbox. Ein Feature-Branch verhindert keine Schreibzugriffe außerhalb des Projekts. Diese Eigenschaften dürfen im neuen Design nicht als einheitliche technische Isolation ausgegeben werden. [ask.sh](../plugins/ask/scripts/ask.sh), [Handover-Skill](../plugins/ask/skills/handover/SKILL.md)

Philharmonie braucht drei eigene Rechteprofile:

| Profil | Einsatz | Grenze |
|---|---|---|
| `inspect` | Frage, Planung, lesendes Review | Projektquellen lesen; keine Projektänderungen |
| `verify` | Evaluator und Prüfwerkzeuge | Quellen unveränderlich; Build-/Testschreibzugriffe nur in isolierter Prüfumgebung und ausgewiesenen Caches |
| `edit` | Generator | Änderungen am beauftragten Arbeitsstand innerhalb der freigegebenen Pfade |

Diese Profilnamen sind interne Begriffe, keine Hersteller-Flags. Der Adapter muss seine tatsächlich durchsetzbaren Grenzen melden. Bei fehlender Isolation darf er nicht still auf weitergehende Rechte ausweichen. Für `verify` muss die Implementierung eine passende Sandbox oder einen separaten Testbereich bereitstellen. Nix liefert Werkzeuge und reproduzierbare Abhängigkeiten, ist allein aber keine Sandbox für beliebige CLI- und Testprozesse.

Die Prüfstrategie hängt von der Spec ab. Bash erhält Shellcheck und Verhaltenstests für relevante Erfolgs- und Fehlerpfade. Nix-Projekte erhalten ihre vereinbarten Flake-Checks und gegebenenfalls Build- oder Laufzeittests. Dokumente werden auf Kriterienabdeckung, Quellen, innere Widersprüche und vorgegebene Fachfälle geprüft. Ein Build belegt keinen erfolgreichen Live-Deploy; ein plausibler Normenverweis belegt nicht die Existenz der zitierten Anforderung.

Beim ersten Durchgang erfassen zwei beteiligte Prüfer ihre Befunde unabhängig. Erst danach sehen sie die jeweils andere Bewertung. Widersprüche werden anhand der Kriterien und Belege aufgelöst. Eine Mehrheit oder bloße Zustimmung ist kein Nachweis.

Vorgeschlagene Grenze: höchstens drei Abstimmungsrunden je Streitpunkt und drei Generator/Evaluator-Korrekturrunden ohne neue Nutzerentscheidung. Wiederholt sich derselbe erhebliche Dissens oder endet das Rundenbudget, setzt der Koordinator `activity=blocked` mit den Positionen, Belegen und einer konkreten Entscheidungsfrage. Zusätzliche Laufzeit- oder Kostenlimits sind konfigurierbar; gemessene Nutzung und Schätzungen werden getrennt. Ein Budgetende erzeugt kein PASS.

Nach PASS erhält der Nutzer ein Review Briefing mit dem Ergebnis, den bestätigten Eigenschaften samt Belegen und den nicht bestätigten Eigenschaften samt Hindernis. Fehlt ein Nachweis für ein Pflichtkriterium, hätte die Evaluation kein PASS liefern dürfen. Nicht bestätigte Punkte außerhalb des vereinbarten Scopes bleiben als solche sichtbar.

## 7. Plugin-Paket und Übergang von ask

Das neue Plugin wird eigenständig installierbar. Geplanter Paketpfad ist `plugins/philharmonie/`, mit `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, geteilten `commands/` und `skills/`, Laufzeitcode, Schemas, Templates, Tests, `flake.nix`, `README.md` und `build.md`. Rollen können zunächst Skills sein; echte Agent-Definitionen erhalten die im Repository vorgeschriebene zusätzliche Codex-Registry. Hooks gehören erst ins Paket, wenn ihr Nutzen und ihre Verfügbarkeit in beiden Hosts geprüft sind.

Die installierte Variante darf weder einen anderen Plugin-Cache noch den Marketplace-Checkout zur Laufzeit voraussetzen. Der Plugin-Root wird aus dem installierten Artefakt abgeleitet. Die Repository-Regel zu migrierten Codex-Commands bleibt relevant: Commands und Skills brauchen verschiedene Namen. Siehe [CLAUDE.md](../CLAUDE.md).

Für die Entwicklung kann das bestehende `ask` als Referenz und Übergangsadapter verwendet werden. Für den Release wird sein Transport in das neue Paket übernommen und dort zentral gepflegt. Eine dauerhaft getrennte Kopie desselben Transports in zwei aktiven Plugins sollte vermieden werden. Vorschlag für den Übergang:

1. Philharmonie erhält namespacierte Einzelaufrufe und die Mission-Funktionen. `ask` bleibt während der Erprobung unverändert nutzbar.
2. Beide Aufrufrichtungen werden gegen die vereinbarten Rechte und Ausgabeformate geprüft. Ein Golden-Test sichert insbesondere Standard-Review, verpflichtendes Execute-Handover, explizite Zielwahl und Exit-Code-Verhalten.
3. Nach erfolgreicher Erprobung wird entschieden, ob `ask` eingefroren oder durch ein Kompatibilitätspaket aus derselben Transportquelle ersetzt wird. Entfernen oder Umstellen der Installation ist ein eigener Auftrag.

Die in der Evaluierung genannten TandemKit-Formate werden angepasst übernommen. Vor tatsächlicher Text- oder Codeübernahme müssen der dort genannte Commit und die vollständige Lizenzdatei lokal vorliegen. Copyright- und Lizenzhinweise gehören in das ausgelieferte Paket; ein Herkunftslink allein ersetzt sie nicht. Ein `THIRD_PARTY_NOTICES.md` hält Quelle, Revision und übernommene Dateien fest.

## 8. Umsetzung in überprüfbaren Schritten

Jeder Schritt liefert ein vorführbares Stück und endet mit einer Review-Pause. Die Implementierung beginnt erst nach einem entsprechenden Auftrag.

| Schritt | Ergebnis | Abnahme |
|---|---|---|
| 1. Verträge | Spec-, Handover- und Ergebnisschema, Rollenbriefings, festgelegte Zustandsübergänge | Eine Beispielmission lässt sich ohne Interpretationslücken durchspielen |
| 2. Transport | Eigenständiges Paket mit `ask`, `execute`, strukturierten Runs und Fähigkeitserkennung | Mock-Tests plus autorisierte echte Aufrufe in beide Richtungen; Grenzen tatsächlich geprüft |
| 3. Zustand | Initialisierung, Transitionen, Status, Pause, Resume und Abbruch | Ungültige/veraltete Transitionen scheitern; Unterbrechungen erzeugen keine doppelten Schreibaufträge |
| 4. Arbeitsrunde | Planner → Generator → Evaluator → Review Briefing | Eine Bash- und eine Dokument-Mission durchlaufen PASS, FAIL und BLOCKED nachvollziehbar |
| 5. Mehrere Sitzungen | Besitzerwechsel, Worktree-Zuordnung, Erkennung fremder Änderungen | Zwei Sitzungen können denselben Auftrag nicht gleichzeitig schreibend übernehmen |
| 6. Release | Beide Manifeste/Marketplaces, Migration und Build-Dokumentation | Installation und Rollenaufrufe funktionieren aus beliebigen Cache-Pfaden in beiden Hosts |

Die Nix-Umgebung des späteren Plugins muss `nix flake check`, `nix shell` und `nix run` unterstützen; `nix develop` liefert die Entwicklungswerkzeuge. `build.md` dokumentiert Voraussetzungen, Shell, Start, Tests und CLI-Authentifizierung. Authentifizierte Ziel-CLIs können wie bei `ask` vom Host kommen; ihre Versionen und die tatsächlich gewählte Modellkonfiguration werden pro Run erfasst.

Die Zustands- und Rechteprüfungen brauchen gezielte Fehlerfälle: CLI-Ende mit leerem Ergebnis, ungültiges JSON, API-Fehler, verweigerte Tools, Abbruch vor und nach dem Prozessstart, PID-Wiederverwendung, gleichzeitige Besitzerwechsel, geänderte Spec, ungetrackte Datei nach PASS und fehlende fachliche Quelle. Externe Tests erhalten einen temporären Workspace und laufen in der Nix-Umgebung. Ein grüner Test mit einer Mock-CLI ersetzt die Integrationstests der echten Adapter nicht.

## 9. Quellenstand und Grenzen dieses Entwurfs

Die Aussagen über `ask` wurden am 2026-09-07 gegen [Skript](../plugins/ask/scripts/ask.sh), [Commands](../plugins/ask/commands/ask.md), [Handover](../plugins/ask/skills/handover/SKILL.md), [Flake](../plugins/ask/flake.nix) und [Build-Dokumentation](../plugins/ask/build.md) gelesen. Beschrieben ist die lokale Implementierung; daraus folgt keine Garantie für zukünftige CLI-Versionen.

Die TandemKit-Detailbewertung stammt aus der [vorliegenden Evaluierung](evaluierung-tandemkit.md), die Commit `72c4709`, Version 1.4.0 nennt. Das öffentliche [README](https://github.com/FlineDev/TandemKit) wurde zusätzlich am 2026-09-07 geöffnet. Die direkten Abrufe der Spec-Vorlage, des Evaluator-Prompts und des Generator-Skills an der genannten Revision scheiterten. Deshalb behauptet dieses Dokument keine erneute Quellcodeprüfung dieser Revision und enthält keine wörtliche Übernahme daraus.

Hersteller-Flags, Plugin-Installation und Sandbox-Fähigkeiten sind vor der Implementierung gegen die dann verwendeten offiziellen CLI-Dokumentationen und die installierten Versionen zu prüfen. Die hier entworfenen Commands, Rechteprofile und Zustandsregeln sind der Vertrag des eigenen Plugins.

## 10. Umsetzung und Prüfung

Philharmonie 0.1.0 liegt unter [plugins/philharmonie](../plugins/philharmonie/README.md). Die Hauptsitzung übernimmt Koordination und Planung; Generator und Evaluator laufen in frischen CLI-Kontexten. Die Umsetzung verwendet Python auch für die Adapter, damit Zustandskern und Transport keine zweite Shell-Schnittstelle benötigen. JSON Schema validiert die Verträge. Nix paketiert die Laufzeit.

Die Profile werden unter Linux mit Bubblewrap durchgesetzt. Generatoren ändern einen Snapshot; der Kern übernimmt erlaubte Pfade nach erneuter Prüfung des Originals. Tests laufen in eigenen Snapshots. Eine Projektübernahme über mehrere Dateien ist journalisiert, aber keine atomare Gesamttransaktion. Konfiguration und tatsächlich aufgelöste Adapter werden je Mission gebunden. Alle unabhängigen Erstprüfungen laufen vor dem Abgleich mit dem Generatorbericht.

| Entwurfsschritt | Implementierung und Nachweis |
|---|---|
| 1. Verträge | Vier Rollen-Skills, Spec/Handover/Review-Templates und JSON-Schemata; `test_state.py` und `test_audit.py` prüfen Kriterien, Freigaben und Umschläge |
| 2. Transport | `single.py`, `transport.py`, `test_single.py`, `test_transport.py`; echte Missionen mit Claude→Codex und Codex→Claude in `test_integration.py` |
| 3. Zustand | `state.py`, `runner.py`; Revisionen, Spec-Manipulation, PID-Wiederverwendung, Pause/Cancel/Resume, Startbarriere und Prozessabbruch in den Zustands-, Prozess- und Regressionstests |
| 4. Arbeitsrunde | Bash-Mission mit echtem Shellcheck und Laufzeittest, Dokument-Mission mit Quellenvergleich; PASS, FAIL/Korrektur und BLOCKED in `test_missions.py`; Rollenabgleich und Dissens in `test_audit.py` |
| 5. Mehrere Sitzungen | Reale konkurrierende Prozesse an der Checkout-Sperre, getrennte Git-Worktrees sowie Änderungen während Übernahme und Evaluation in `test_process.py`, `test_regressions.py` und `test_audit.py` |
| 6. Release | Beide Manifeste und Marketplace-Einträge; Installation in separaten Claude-/Codex-Testprofilen mit je vier Rollen und neun Commands; Start aus beiden Cache-Pfaden sowie über `nix run` und `nix shell` |

Die automatisierten Rollen-Antworten der Fehlerfalltests sind kontrollierte Fixtures. Die zwei Live-Missionen verwenden dagegen die authentifizierten echten CLIs. Ein grüner Build ersetzt die gesonderten Linux-Sandbox- und Live-Prüfungen nicht. Einzelheiten und reproduzierbare Befehle stehen in [build.md](../plugins/philharmonie/build.md) und den [CLI-Verträgen](../plugins/philharmonie/references/cli-contract.md).

Geprüft am 2026-09-07 auf x86_64-linux mit Codex 0.153.4, Claude Code 2.1.260 und Bubblewrap 0.11.2: `nix flake check` bestand mit 41 Standardtests. Die fünf gesonderten Sandbox-/Szenariotests und beide Live-Missionen bestanden ebenfalls. Beide Live-Zuordnungen wurden zusätzlich aus dem installierten Codex-Cache ausgeführt. Claude meldete 13 Komponenten; der Codex-Cache enthielt vier Rollen und neun migrierte Commands. `nix run` aus beiden Cache-Pfaden sowie `nix shell` aus `/tmp` starteten erfolgreich. Die deklarierte aarch64-linux-Ausgabe wurde hier nicht auf Hardware getestet.

Die Freigabe des Nix-Daemons für Prüfkommandos ist eine gesonderte Konfigurationsoption und bleibt standardmäßig aus. Authentifizierungsdateien werden lesend eingebunden; nötige Token-Erneuerungen erfolgen am Host. API-Netz ist verfügbar. Multi-Host-/Netzdateisystem-Koordination ist nicht enthalten. Git-Submodule erfordern eigene Aufträge in ihren Checkouts. Diese Betriebsgrenzen sind in der Plugin-README ausgewiesen.

Das bestehende ask bleibt unverändert. Es wurde kein TandemKit-Quelltext übernommen; [THIRD_PARTY_NOTICES.md](../plugins/philharmonie/THIRD_PARTY_NOTICES.md) dokumentiert die konzeptionelle Herkunft und Laufzeitabhängigkeiten. Installation in die regulären Nutzerprofile, Commit, Push und Ablösung von ask sind keine Nebenwirkung des Bauauftrags.

## 11. Delegation und Spec-Gegenprüfung

Planer und Generator zerlegen unabhängig bearbeitbare Aufgaben und verwenden native Agents ihrer eigenen CLI. Die [Delegationsregel](../plugins/philharmonie/references/delegation.md) ordnet Modelle nach Aufgabenanforderungen zu, begrenzt gleichzeitige Agents und verlangt getrennte Schreibzuständigkeiten. Der Planer recherchiert lesend und führt die Spec selbst zusammen. Generatoren und `execute` erhalten vier native Agenttypen: Light, Standard, Advanced und Strong. Advanced verwendet GPT-5.6 Sol beziehungsweise Opus mit Effort `high` für Änderungen über mehrere Module, Refactoring und schwierige Integration. Kleine unteilbare Aufgaben können sie begründet selbst erledigen.

`review-spec` ergänzt die fünfte Rolle und den zehnten Command. Die andere CLI bewertet die Spec vor `approve` mit fünf begründeten Teilnoten: Auftragsabdeckung 25, Prüfbarkeit 25, Scope 20, Quellen 15 und Risiken 15 Punkte. Der Zustandskern berechnet die Summe. Blocker verhindern die Freigabe unabhängig vom Score; eine Mindestpunktzahl gibt es nicht. Bericht, Spec-Revision, Spec-Hash, Vertrags-Hash und Projektfingerprint werden vor der Freigabe erneut geprüft. Vorhandene Nutzerautorisierung bleibt im gedeckten Umfang gültig.

Die Erweiterung wurde am 2026-09-07 mit 58 Standardtests und fünf lokalen Sandbox-/Szenariotests geprüft. Vier zusätzliche Live-Tests bestanden: Native Claude-Agents verwendeten Haiku und Sonnet, native Codex-Agents Luna und Terra. Die echte Spec-Gegenprüfung ergab für dieselbe kleine Textaufgabe bei Codex 100/100 und bei Claude 97/100, jeweils mit fünf begründeten Teilnoten und ohne Projektänderung oder Umsetzungsfreigabe. Die beiden zusätzlichen Live-Testdateien und ihre Aktivierungsflags stehen in [build.md](../plugins/philharmonie/build.md).

## 12. Modellübersicht je Aufruf

Jeder Philharmonie-Aufruf endet mit einer sichtbaren Tabelle aus Modell, Aufgabe und Ergebnis. Die Hauptsitzung ergänzt ihre eigene Arbeit und tatsächlich eingesetzte Recherche-Agents; die Laufzeit erfasst die delegierten CLI-Rollen und nativen Subagents. Aktuelle Aufrufe und gespeicherte Missionshistorie bleiben getrennt. Belegte Modellnamen, Konfigurationen und fehlende Metadaten werden unterschieden. Native Abschlussberichte bleiben Selbstberichte; Prüfungen und Abnahme haben eigene Nachweise.

Die Übersicht erscheint auf stderr; Zustandsausgaben enthalten zusätzlich `invocation_models`. Run-Historie und Missionsberichte bewahren die Zuordnung dauerhaft. Native Werkzeug- und Thread-IDs verbinden Subagents mit ihren Modellen und Ergebnissen. Unlesbare Auftragstexte werden nicht aus verschlüsselten Protokollfeldern abgeleitet.

Abschließend geprüft am 2026-09-07: `nix flake check` bestand mit 77 Standardtests; 15 separat aktivierbare Integrationstests wurden dabei übersprungen. Beide Live-Tests der Modellübersicht bestanden zusätzlich: Claude Fable mit Opus und Codex Astra mit GPT-5.6 Sol. Sie prüften native Modellnachweise, Ergebniszuordnung und die Übernahme der erstellten Testdatei. Die endgültige Kurzansicht wurde zusätzlich gegen die erhaltenen echten Protokolle beider CLIs geprüft. Aufrufe und Artefaktpfade stehen in [build.md](../plugins/philharmonie/build.md).
