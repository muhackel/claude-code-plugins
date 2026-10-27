# Verbindung und Beispiele

## Fehlende Tools

Nach Katalogsuche einen bekannten Aufruf direkt versuchen, in Codex-Code-Mode etwa:

```javascript
const result = await tools.mcp__t3_code__orchestrator_capabilities({});
```

Ein leerer Suchtreffer allein beweist nicht, dass T3 fehlt. Manche Server werden
erst beim Aufruf angebunden. Den tatsächlich angebotenen Tool-Namen benutzen.

Wenn ein ACP-Agent T3-MCP nicht exponiert und `T3_ACP_MCP_NODE` vorhanden ist,
steht der unterstützte Terminaltransport zur Verfügung:

```sh
ELECTRON_RUN_AS_NODE=1 "$T3_ACP_MCP_NODE" ${T3_ACP_MCP_ENTRYPOINT:+"$T3_ACP_MCP_ENTRYPOINT"} acp-mcp-call orchestrator_capabilities '{}'
```

Bei der Standalone-Ausgabe fehlt `T3_ACP_MCP_ENTRYPOINT`; das ist vorgesehen.
Derselbe Transport unterstützt `delegate_task`, `task_status` und `task_cancel`.
JSON-Argumente sicher als **ein** Shell-Argument übergeben; keine Prompt-Inhalte in
ausführbaren Shell-Text interpolieren. Keine Token oder vollständigen Umgebungen
ausgeben. Die Laufzeitvariablen verwenden, keine Ports oder Tokens erfinden.

Fehlen sowohl MCP als auch dieser Transport, den fehlenden T3-Zugriff melden.
Keine fremde CLI oder API als vermeintliche T3-Delegation starten. Ein deaktivierter
Ziel-Provider ist ebenfalls eine echte Einschränkung, kein Anlass zur Umgehung.

## Delegation

Das folgende JSON zeigt nur die Form. `PROVIDER_AUS_KATALOG`, `MODELL_AUS_KATALOG`
und die Request-ID vor Verwendung ersetzen. Auch Optionsnamen aus dem konkreten
Modell-Deskriptor übernehmen.

```json
{
  "task": "Prüfe den unten eingefügten Entwurf nur lesend. Liefere Befunde mit Belegen und offenen Fragen. Kontext: …",
  "title": "Zweitmeinung zum Entwurf",
  "role": "review",
  "target": {
    "providerInstanceId": "PROVIDER_AUS_KATALOG",
    "model": "MODELL_AUS_KATALOG"
  },
  "mode": "async",
  "clientRequestId": "AUFTRAG-review-r1"
}
```

Bei einem Claude-Modell kann `target.options` beispielsweise
`{"effort":"max","fastMode":true}` sein, bei einem Codex-Modell
`{"reasoningEffort":"max","serviceTier":"priority"}`. Das sind **keine**
Zusagen: Bietet das gewählte Modell `fastMode` nicht an, ist dieser Wunsch dort
nicht erfüllbar. Optionen eines anderen Modells nicht übertragen.

## Kreuzkommunikation

Claude → Codex und Codex → Claude verwenden dieselben Tool-Verträge. Für eine
Gegenprüfung übergibt der Parent die erste Antwort samt ursprünglicher Frage an
das zweite Modell. Ein neuer Reviewer erbt weder den Parent- noch den früheren
Reviewer-Verlauf. Halte die Zahl der Runden am Auftrag ausgerichtet; kein offenes
Pingpong. Bei wiederholten Einwänden ohne neue Belege zusammenführen und die
verbleibende Entscheidung benennen.
