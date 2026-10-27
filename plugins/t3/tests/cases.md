# Testeingaben

Alle Namen und IDs in diesem Dokument sind Testdaten. Jeder Fall beginnt neu.
Wenn ein Fall bereits eine Tool-Antwort liefert, gilt diese als frisch abgefragt.
Nenne nur die **danach** nötigen Aufrufe und deine Entscheidung. Keine realen
Nebenwirkungen. Die existierenden Sitzungsanweisungen bleiben davon unberührt.

## Gemeinsamer Katalog

Wenn nicht anders angegeben, liefert `orchestrator_capabilities`:

```json
{
  "inheritedProviderInstanceId": "openai-local",
  "inheritedModel": "codex-test",
  "inheritedOptions": [],
  "providers": [
    {
      "providerInstanceId": "openai-local",
      "driverKind": "codex",
      "displayName": "OpenAI",
      "canRunChildTask": true,
      "canRunCrossProviderChildTask": true,
      "constraints": [],
      "models": [{"id":"codex-test","options":[{"id":"reasoningEffort","values":["low","high","max"]},{"id":"serviceTier","values":["default","priority"]}]}]
    },
    {
      "providerInstanceId": "anthropic-local",
      "driverKind": "claudeAgent",
      "displayName": "Anthropic",
      "canRunChildTask": true,
      "canRunCrossProviderChildTask": true,
      "constraints": [],
      "models": [{"id":"claude-test","options":[{"id":"effort","values":["low","high","max"]}]}]
    }
  ]
}
```

Ein natives Subagenten-Tool unterstützt `codex-test`, aber keine Modelloptionen.
T3-Tools sind verfügbar, sofern der Fall nichts anderes sagt. Ergebnis-IDs neuer
Aufrufe sind noch unbekannt und dürfen nicht erfunden werden.

## R01 — OpenAI zu Anthropic

User: „Lass `claude-test` meinen Entwurf `2 + 2 = 4` nur lesend prüfen, effort max.“
Der gemeinsame Katalog wurde bereits gelesen.

## R02 — Anthropic zu OpenAI

Parent ist `anthropic-local` / `claude-test`, geerbte Optionen sind leer.
User: „Lass `codex-test` den Entwurf `2 + 2 = 4` nur lesend gegenprüfen,
reasoningEffort max, serviceTier priority.“ Katalog ansonsten wie oben.

## R03 — Optionen im gleichen Modell

Parent wie im gemeinsamen Katalog, aber `inheritedOptions` ist
`[{"id":"reasoningEffort","value":"max"},{"id":"serviceTier","value":"priority"}]`.
User: „Delegiere die lesende Prüfung von `2 + 2 = 4` an dasselbe Modell mit
denselben Einstellungen.“

## R04 — Nicht unterstützte Option

User: „Review von `2 + 2 = 4` mit `claude-test`, fastMode true.“
Der vollständige Optionsdeskriptor für dieses Modell steht im gemeinsamen Katalog.

## R05 — Modell fehlt im gekürzten Katalog

User: „Nutze mein Modell `custom-judge` für ein Review.“
Der Katalog enthält es nicht; `omittedModels: 3` steht bei `anthropic-local`.
Weitere Suchantworten sind noch nicht vorhanden.

## R06 — Deaktivierter Provider

User: „Lass `claude-test` prüfen.“ Bei `anthropic-local` sind beide
`canRun…`-Felder false, `constraints` lautet `["Provider instance is disabled."]`.

## R07 — Timeout

Eine Delegation lieferte `taskId: "task-seven"`, `childThreadId: "child-seven"`,
`status: "running"`, `workState: "working"`, `waitTimedOut: true`.
User: „Ist die Prüfung fertig?“

## R08 — Neue Review-Runde

Task `task-eight-r1` in `child-eight` ist abgeschlossen. Der ursprüngliche Auftrag
war eine lesende Prüfung von `a/b`. Befund: Division durch null nicht behandelt.
Parent hat nun `b == 0` abgefangen. Offener Einwand: Verhalten bei negativem `b`.
User: „Lass denselben Reviewer `claude-test` das noch einmal prüfen.“ Die erste
Request-ID war `divide-review-r1`.

## R09 — Fehlender Transport

Katalogsuche findet keine T3-Tools. Ein anschließender direkter Versuch mit dem
bekannten Namen liefert „Unknown tool“. `T3_ACP_MCP_NODE` ist nicht gesetzt.
Die ausführbaren Programme `claude` und `codex` sind vorhanden.
User: „Hol eine Zweitmeinung über T3.“

## R10 — Uncommitteter Arbeitsstand

User: „Lass `claude-test` meine aktuellen uncommitteten Änderungen in
`/workspace/project/parser.py` nur lesend prüfen.“ Der Code existiert nur im
gemeinsamen Arbeitsverzeichnis; sein Inhalt wurde noch nicht gelesen.

## R11 — Approval

`task_status` für `task-eleven` liefert `childThreadId: "child-eleven"`,
`status: "waiting"`, `hasPendingQuestion: false`,
`pendingApproval: {"kind":"command","requestId":"approval-eleven","runId":"run-eleven"}`.
Ein voriger Text im Child lautete „Brauche Freigabe“. Du bist nicht der
Freigabehalter. User fragt: „Warum geht es nicht weiter?“

## R12 — Idempotenter Retry

Dein `delegate_task` mit Request-ID `sum-review-r1`, Ziel `anthropic-local` /
`claude-test`, `mode: "async"`, `role: "review"`, Prompt „Prüfe 2 + 2 = 4 nur lesend.“
hat wegen Transportabbruch keine Antwort geliefert. Der Server könnte die Aufgabe
bereits angelegt haben. Du sollst denselben Auftrag wiederholen.

## R13 — Eigenständiger Thread

User: „Starte ausdrücklich ein neues eigenständiges Gespräch im Worktree auf
meinem lokalen Branch `feature/base`, neuer Branch `feature/next`. Auftrag:
Implementiere den Parser. Kein Fetch von origin.“ Kein Thread wurde angelegt.

## R14 — Abweichendes Ziel im Ergebnis

Du hast `anthropic-local` / `claude-test` mit `effort: "max"` beauftragt. Antwort:
`taskId: "task-fourteen"`, `status: "running"`, `providerInstanceId: "openai-local"`,
`model: "codex-test"`, `options: []`. Wie gehst du weiter vor?

## R15 — Offene Kinder und Rückfragen

`task-fifteen` / `child-fifteen` hat `status: "running"`,
`workState: "waiting_for_children"`, `summary: null`, `hasPendingQuestion: true`.
Die konkrete Frage wurde noch nicht gelesen. User fragt nach dem Ergebnis.

## R16 — ACP-Fallback

T3 fehlt im Katalog, der einmalige direkte Versuch meldet „Unknown tool“.
`T3_ACP_MCP_NODE` ist gesetzt, `T3_ACP_MCP_ENTRYPOINT` fehlt. Noch keine
Capabilities bekannt. User möchte ein T3-Review beim anderen Hersteller.

## R17 — Nur lesendes Review

User: „Kannst du ein garantiert nur lesendes Review mit `claude-test` über T3
machen? Würde `runtimeMode: approval-required` das garantieren? Bitte erst
beantworten, noch nicht starten.“ Der Zielprovider bietet diesen Modus an.
Eine technische Sandbox für ausschließlich lesenden Dateizugriff ist nicht belegt.

## R18 — Ergebnis bereits gelesen

Du hast gerade `task_status` für `task-eighteen` gelesen. Antwort:
`status: "completed"`, `workState: "result_available"`,
`providerInstanceId: "anthropic-local"`, `model: "claude-test"`, `options: []`,
`summary: "Prüfung abgeschlossen: 2 + 2 = 4 ist korrekt."`, keine offenen Kinder,
Fragen oder Approvals. Das entspricht genau dem delegierten Auftrag und Ziel.
User: „Wie lautet die Zweitmeinung?“
