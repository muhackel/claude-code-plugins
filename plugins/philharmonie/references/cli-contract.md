# Geprüfte CLI-Verträge

Stand: 2026-09-07. Die lokalen Hilfen wurden in einer Nix-Umgebung gelesen: Codex CLI `0.153.4`, Claude Code `2.1.260`, Bubblewrap `0.11.2`. Die Laufzeit prüft erforderliche Flags vor einem Modellauftrag. Ein vorhandenes Flag oder ein Katalogeintrag beweist keine Accountverfügbarkeit.

## Codex

Der Adapter verwendet `codex exec` mit stdin (`-`), `--ignore-user-config`, `--ignore-rules`, `--json`, `--output-schema <datei>` und `--output-last-message <datei>`. stdout enthält Ereignisse; das fachliche Ergebnis kommt aus der separat geschriebenen letzten Antwort. Modell und Effort werden ausdrücklich gesetzt. Aufrufe schreiben ihren Rollout in das Sitzungsverzeichnis des Hosts, das in die Sandbox gebunden wird; sie setzen keine vorhandene Sitzung fort. Delegierende Aufrufe arbeiten zusätzlich in einem frischen Home unter `scratch/runtime`. [Nichtinteraktive Aufrufe](https://learn.chatgpt.com/docs/non-interactive-mode), [CLI-Referenz](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

Ohne ausdrückliches Modell liest der Adapter den eingebauten Katalog über `codex debug models --bundled`, wählt das sichtbare Modell mit niedrigster Priorität und prüft den gewünschten Effort. Bei Fehlern bricht er ab; er ersetzt Modell oder Effort nicht unbemerkt. Diese Katalogoption wurde an der installierten Hilfe geprüft.

`inspect` und die lesende Evaluator-Rolle nutzen das native Profil `read-only`; der Generator nutzt `workspace-write` in seinem Snapshot. Die äußere Sandbox begrenzt zusätzlich den ganzen CLI-Prozess. Automatische Prüfkommandos laufen gesondert in beschreibbaren Test-Snapshots.

Codex 0.153.4 überspringt bei der Command-Migration Vorlagen mit dem Argument-Platzhalter `$ARGUMENTS`. Deshalb beschreiben die gemeinsamen Commands ihre Eingabe in natürlichem Text. Die erneute Installation muss zehn `source-command-*`-Skills einschließlich `source-command-review-spec` erzeugen. [Migrationsfilter der geprüften Version](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/core-plugins/src/command_migration.rs).

Die Ergebnis-Schemata verwenden Draft 7. Codex lehnt `uniqueItems` im Ausgabevertrag ab; doppelte Generator-Dateinamen prüft daher der Zustandskern. Diese Einschränkung wurde mit echten CLI-Aufrufen reproduziert; daraus folgt kein Nachweis der später ergänzten Delegation.

### Native Delegationsrollen

Generator und schreibender Einzelauftrag erzeugen `philharmonie-light`, `philharmonie-standard`, `philharmonie-advanced` und `philharmonie-strong`. Für Codex verwenden sie Luna mit `medium`, Terra mit `high`, Sol mit `high` und das sichtbare stärkste Katalogmodell mit `high`. Der Adapter prüft Namen und Effort gegen `codex debug models --bundled`. Die aufgabenabhängige Auswahl beschreibt [Delegation](delegation.md); der Planer verwendet dieselben Regeln in seiner Hauptsitzung. Dieselbe Staffelung gilt eine Ebene höher für den Hauptaufruf: Generator und Evaluator arbeiten in `advanced`, die Spec-Gegenprüfung in `strong`, Einzelaufträge nach `--tier` mit `advanced` beim Standard-Review und sonst `standard`. `--model` und `--effort` überschreiben die Klasse. Fehlt ein Klassenmodell im Katalog, fällt der Adapter auf `advanced` zurück und erst danach auf einen Aufruf ohne Modell- und Effortangabe; die Stufe steht als Warnung auf stderr. Der Umweg über `advanced` ist Absicht, weil `codex exec` ohne `-m` das Flaggschiff verwendet.

Der Codex-Aufruf ergänzt folgende Einstellungen; die Rollenpfade zeigen auf die für diesen Run erzeugten TOML-Dateien:

```text
--enable multi_agent
--disable multi_agent_v2
-c agents.enabled=true
-c agents.max_concurrent_threads_per_session=3
-c agents.max_depth=1
-c 'agents.philharmonie-light.description="Begrenzte Recherche und einfache Aufgaben."'
-c 'agents.philharmonie-light.config_file="<absoluter Run-Pfad>/agents/philharmonie-light.toml"'
```

Die Rollen-TOML enthält `model`, `model_reasoning_effort` und `developer_instructions`. Die drei anderen Typen werden entsprechend registriert. `--ignore-user-config` überspringt nur den User-Layer; die CLI-Overrides bleiben wirksam. `max_depth=1` gilt für das hier ausdrücklich gewählte V1-Verfahren. Eine Rollen-TOML erweitert keine Dateisystemrechte. [Konfigurationsfelder 0.153.4](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/config/src/config_toml.rs), [Konfigurationsloader](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/config/src/loader/mod.rs), [Rollenanwendung](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/core/src/agent/role.rs).

## Claude Code

Ohne erzeugte Delegationsrollen verwendet der Adapter `claude -p` mit `--safe-mode`, `--permission-prompts none`, `--permission-mode dontAsk`, expliziter Werkzeugliste, `--name` als Kennung im Resume-Picker und `--output-format json`. Das gilt weiterhin für lesende Einzelaufträge, Spec-Gegenprüfung und Evaluation. Anders als Codex erhält `--json-schema` den JSON-Inhalt als einzelnes Argument. Das erwartete Ergebnis steht in `structured_output`; `result` ist kein Ersatz bei fehlenden strukturierten Daten. [Programmgesteuerte Aufrufe](https://code.claude.com/docs/en/headless), [CLI-Referenz](https://code.claude.com/docs/en/cli-reference).

Die installierte Hilfe dokumentiert `--safe-mode` als Abschalten von Anpassungen wie Skills, Plugins, Hooks und MCP bei erhaltener Authentifizierung. Deshalb enthält das Handover die Projektregeln ausdrücklich. `--bare` wird nicht verwendet: Laut installierter Hilfe liest es keine OAuth-/Keychain-Anmeldung. Der Modellalias `fable` folgt der vorhandenen ask-Implementierung und der installierten Hilfe; ein ausdrückliches Modell überschreibt ihn.

### Eigene Agents ohne Safe Mode

Claude 2.1.260 ignoriert `--agents` im Safe Mode. Die installierte Binärdatei enthält dazu die Meldung `--agents: ignored in safe mode (user-supplied custom agents are disabled)`. Delegierende Aufrufe ersetzen daher `--safe-mode` durch ausdrücklich begrenzte Anpassungen:

```text
--setting-sources ""
--disable-slash-commands
--strict-mcp-config
--mcp-config '{"mcpServers":{}}'
--settings '{"disableAllHooks":true}'
--agents <erzeugtes JSON>
--output-format stream-json
--verbose
--forward-subagent-text
```

Die CLI lädt keine gewöhnlichen User-/Projekt-/Local-Settings und keine Skills oder Commands. MCP erhält eine leere Konfiguration. `disableAllHooks` schaltet gewöhnliche Hooks ab; verwaltete Policy-Hooks bleiben wirksam. Die erzeugten Agentdefinitionen enthalten keine eigenen Hooks oder MCP-Server. [CLI-Flags](https://code.claude.com/docs/en/cli-reference), [Hook-Abschaltung](https://code.claude.com/docs/en/hooks#disable-or-remove-hooks), [Safe-Mode-Verhalten bei Agentdefinitionen](https://code.claude.com/docs/en/errors#invalid-agents-configuration).

Die Hauptsitzung erhält `Agent` in ihrer Werkzeugliste. Unter `dontAsk` genehmigt `--allowedTools` nur `Agent(philharmonie-light)`, `Agent(philharmonie-standard)`, `Agent(philharmonie-advanced)` und `Agent(philharmonie-strong)` zusätzlich zu den jeweiligen Datei-/Shellwerkzeugen. Die erzeugten Definitionen wählen `haiku`, `sonnet`, `opus` beziehungsweise `inherit`, enthalten `maxTurns=20` und `permissionMode=dontAsk`. Standard, Advanced und Strong erhalten `effort=high`; für Haiku wird kein eigener Effort gesetzt. Ihre Werkzeuglisten enthalten kein `Agent`. Modelle und Aliases sind keine Konto-Verfügbarkeitsgarantie. [Subagent-Konfiguration](https://code.claude.com/docs/en/sub-agents), [Modellaliases](https://code.claude.com/docs/en/model-config).

Die Laufzeit setzt `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, `CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS=1`, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` und `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3`. Projektregeln werden im Handover übertragen. Das Concurrency-Limit begrenzt neue Agent-Spawns; laut Hersteller können Wiederaufnahmen es überschreiten. Es ist deshalb keine allgemeine Obergrenze für sämtliche Claude-Aktivitäten. [Umgebungsvariablen](https://code.claude.com/docs/en/env-vars), [Subagent-Limits](https://code.claude.com/docs/en/sub-agents#concurrent-subagent-limit).

## Modellwahl und Laufzeitnachweise

`agents/delegation.json` hält erzeugte Rollen und Modelle fest. Die jeweilige Datei `delegation-events.json` speichert native Delegationsereignisse sowie beobachtete Modellangaben. Ein Eintrag im Rollenvertrag belegt die Konfiguration; ein Selbstbericht des Agents belegt keine erfolgreiche Ausführung auf diesem Modell.

Bei Codex enthält der interne Spawn-Datensatz effektives Modell und Effort, doch `codex exec --json` lässt diese Felder weg. Der Adapter sammelt deshalb zusätzlich `turn_context`-Modellangaben aus `scratch/runtime/.codex/sessions/**/*.jsonl` mit Quellpfad und Zeitstempel. Diese Liste kann auch das Hauptmodell enthalten; für eine konkrete Zuordnung zu einem Kind die referenzierten Rollouts und Spawn-Ereignisse gemeinsam prüfen. [Internes Spawn-Ergebnis](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/core/src/tools/handlers/multi_agents/spawn.rs), [JSONL-Abbildung](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/exec/src/event_processor_with_jsonl_output.rs).

Bei Claude liefern weitergereichte Kindnachrichten `parent_tool_use_id`; der Adapter hält ihre `message.model`-Angabe mit dieser Aufruf-ID fest. Das fachliche Ergebnis liest er aus dem letzten `result`-Datensatz des Streams und prüft weiterhin `structured_output`. [Weitergereichte Subagent-Nachrichten](https://code.claude.com/docs/en/headless#follow-subagent-messages).

`model-activity.json` verknüpft diese Modellnachweise mit Aufgabe, Rolle und Ergebnis. Claude-Aufträge werden über ihre Werkzeug-ID zugeordnet; Codex-Kinder über native Thread- und Parent-Verknüpfungen. Der geprüfte Codex-Live-Aufruf enthielt den Agentstart im Sitzungsprotokoll, aber nicht im JSON-Stream. Deshalb reicht der Stream allein nicht für eine vollständige Übersicht. Eine verfügbare native Kurzbeschreibung dient als `task_summary` für die sichtbare Tabelle; `task` bewahrt den lesbaren vollständigen Auftrag. Liegt ein Auftragstext nur verschlüsselt vor, wird das benannt; der Beitrag bleibt über den zugeordneten nativen Selbstbericht sichtbar. Fehlende Modell- oder Abschlussbelege werden ausdrücklich gekennzeichnet.

Die Live-Tests in `test_delegation.py` prüfen native Agentstarts mit Light/Standard und gesondert mit Advanced in beiden CLIs. Sie verlangen die erwarteten Modelle aus nativen Ereignissen beziehungsweise Rollouts, die Ausgabedateien im Snapshot und einen unveränderten Originalstand. Die Konfiguration allein genügt dafür nicht; ohne ausdrücklich aktivierte Live-Tests bleibt dieser Nachweis für den jeweiligen Testlauf offen.

## Betriebssystemgrenze und Authentifizierung

Bubblewrap bindet den Root schreibgeschützt ein und verdeckt `/home`, `/root`, `/tmp` und `/run`. Nur Snapshot, Run-Unterlagen und temporäre Ausgabe werden gezielt eingebunden. Bei delegierenden Aufrufen liegt das private Home im Run-Verzeichnis `scratch/runtime`. Andere Aufrufe verwenden ein flüchtiges Home. Codex-Rollouts liegen in beiden Fällen im Sitzungsverzeichnis des Hosts; ein Rollout gehört zu einem Auftrag, wenn sein Sitzungskopf dessen Snapshot als Arbeitsverzeichnis nennt. Das private Home erhält bei Agentenaufrufen vorhandene Authentifizierungsdateien als lesende Mounts. Ebenso werden dort die Sitzungsverzeichnisse des Hosts beschreibbar eingebunden, damit jeder Auftrag in der Auswertung der Ziel-CLI erscheint; das ist die einzige Stelle, an der ein Auftrag außerhalb seines Snapshots schreibt. Prüfkommandos bekommen weder Authentifizierungs- noch Sitzungs-Mounts und keine API-Key-Umgebungsvariablen. Die äußere Sandbox schützt auch native Dateiwerkzeuge. [Bubblewrap](https://github.com/containers/bubblewrap), [Claude-Sandbox](https://code.claude.com/docs/en/sandboxing).

Unter Linux verwendet Claude `.credentials.json` im Konfigurationsverzeichnis. Der Adapter bindet diese Datei und Codex' `auth.json` gezielt in das private Home ein, ohne deren Inhalt zu protokollieren. Die Codex-Datei folgt dem vorhandenen Host-Konfigurationspfad; OpenAI dokumentiert ihre Übernahme in Container. Token-Erneuerung durch Schreiben in die eingebundene Originaldatei ist absichtlich nicht erlaubt; eine abgelaufene Anmeldung muss am Host erneuert werden. [Claude-Authentifizierung](https://code.claude.com/docs/en/authentication), [Codex-Authentifizierung](https://learn.chatgpt.com/docs/auth).

Das Netzwerk bleibt für API-Aufrufe verfügbar und ist nicht auf Herstellerendpunkte beschränkt. Der Nix-Daemon ist standardmäßig verborgen. Seine gesonderte Freigabe für vereinbarte Prüfkommandos gewährt Zugriff auf einen Host-Dienst und darf nicht als Dateisystem-Cache beschrieben werden.
