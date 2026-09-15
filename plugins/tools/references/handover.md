# Handover für Cross-CLI-Aufrufe

Die andere CLI startet mit leerem Kontext. Sie sieht weder diese Sitzung noch den Chatverlauf, nur das
Arbeitsverzeichnis und das Handover. Alles, was sie wissen muss, steht im Handover.

## Ablauf

1. Plugin-Root ermitteln (Claude Code: `${CLAUDE_PLUGIN_ROOT}`; Codex: Verzeichnis, das `.codex-plugin/` enthält).
2. Handover nach dem Format unten schreiben. Bei `/tools:ask` ohne Argument entfällt das, das Skript hat ein Standard-Review.
3. `scripts/ask.sh --mode ask|execute` mit dem Handover auf stdin starten (Heredoc). Das Skript erkennt den
   Host, wählt die andere CLI und setzt Modell und Effort nach der Stufe (`--tier`, siehe unten).
   Ohne Handover stdin mit `</dev/null` schließen: das Skript liest stdin bis EOF.
4. stdout ist die Antwort, stderr der Fortschritt (bei Codex auch dessen Trajektorie mit Tool-Aufrufen).
   Welches Modell gearbeitet hat, steht auf stderr: bei Codex im Sitzungskopf (`model:`,
   `reasoning effort:`), bei Claude als `Modell laut claude: …`. Die Selbstauskunft im Antworttext ist
   kein Beleg. Antwort unverändert wiedergeben, dann kurz einordnen.

## Handover-Format

Markdown, Deutsch, so knapp wie möglich und so vollständig wie nötig:

```markdown
# Handover

## Kontext
- Projekt: <Name, ein Satz was es ist>
- Pfad: <absoluter Pfad des Arbeitsverzeichnisses>
- Branch: <git branch>, Arbeitsbaum: <sauber | Ausgabe von git status --short>
- Relevante Dateien (3–8, je ein Halbsatz Zweck):
  - `pfad/datei` — …

## Ziel
<Was soll am Ende erreicht sein, ein bis zwei Sätze>

## Frage / Auftrag
<Die konkrete Frage oder der konkrete Auftrag. Bei mehreren Punkten nummerieren.>

## Erwartete Antwort
<Struktur (z.B. Befundliste mit Datei:Zeile), Umfang, Sprache Deutsch>

## Grenzen
<ask: Nur lesen, keine Dateien ändern.>
<execute: Änderungen nur im Workspace, kein Commit, kein Push, am Ende alle geänderten Dateien auflisten.>
```

Was ins Handover gehört: der Stand der Diskussion, getroffene Entscheidungen, bekannte Sackgassen.
Was nicht hinein gehört: Chat-Verlauf im Wortlaut, Vermutungen als Fakten, Anweisungen an den Host.

## Standard-Review (ohne Argument)

Das Skript nutzt bei `--mode ask` ohne Handover einen festen Review-Auftrag: Projekt charakterisieren
(README, CLAUDE.md/AGENTS.md, Struktur, Git-Log), Befunde in vier Kategorien (Bugs/Risiken, Doku-Drift,
Struktur/Konventionen, uncommitted Changes), je Befund Datei:Zeile plus Empfehlung, maximal zehn
Befunde nach Schwere priorisiert, Deutsch.

## Skript-Aufrufe

```bash
bash "<root>/scripts/ask.sh" --mode ask </dev/null                        # Standard-Review (advanced)
bash "<root>/scripts/ask.sh" --mode ask --tier strong --fast <<'HANDOVER'  # schnelles Urteil des starken Modells
…
HANDOVER
bash "<root>/scripts/ask.sh" --mode execute --tier drone <<'HANDOVER'      # mechanischer Auftrag mit Schreibrechten
…
HANDOVER
bash "<root>/scripts/ask.sh" --dry-run … </dev/null                        # nur Kommando + Standard-Review zeigen
bash "<root>/scripts/ask.sh" --dry-run … <<'HANDOVER'                      # nur Kommando + Handover zeigen
…
HANDOVER
```

Weitere Flags: `--boost`, `--fast`, `--model SLUG`, `--effort STUFE` (siehe Stufe), `--target claude|codex`
(Override der Host-Erkennung), `--handover FILE`, `-C DIR`.

## Stufe

`--tier` bestimmt Modell und Effort. Ohne Angabe gilt in beiden Modi `advanced`.

| Stufe | Wofür | Claude | Codex | Effort | `--boost` | `--fast` | Modus |
|---|---|---|---|---|---|---|---|
| `strong` | Architektur, widersprüchliche Anforderungen, Planung, Urteil | fable | astra | medium | high | low | ask, execute |
| `advanced` | Zweitmeinung, Review, Fehlersuche, Refactoring, Umsetzung mit Spielraum | opus | sol | high | xhigh | – | ask, execute |
| `drone` | mechanische Umsetzung nach klarem, vollständigem Auftrag | sonnet | luna | high | – | – | nur execute |

Die starken Modelle brauchen für dieselbe Qualität weniger Effort, ihr Default liegt darum eine Stufe
unter dem der advanced-Modelle. `--fast` gibt es nur bei `strong`: das starke Modell als schnelle, aber
tiefe Einschätzung. `--boost` gibt es bei `strong` und `advanced`, nicht bei `drone`. Bei Codex steht die
Spitze nicht fest, sie kommt aus dem Katalog der installierten Version (sichtbares Modell mit niedrigster
`priority`).

`ask` startet ohne Angabe auf `advanced`, weil eine Zweitmeinung nicht schwächer sein darf als der
Fragende. `execute` ebenfalls; `drone` ist ein bewusstes „das ist wirklich mechanisch" und verlangt einen
Auftrag, der alles vorgibt. Für wirklich harte Aufgaben lohnt `strong` eher als Planer — den Plan holen,
ihn dann in `advanced` ausführen lassen — als für die Umsetzung selbst.

Freie Wahl: `--model <alias|slug>` setzt das Modell der Ziel-CLI direkt (Claude-Alias wie `sonnet` oder
voller Name, Codex-Slug wie `gpt-5.5`), der Effort ist dann `high`. `--effort low|medium|high|xhigh|max`
überschreibt jeden Effort, auch den aus `--boost`/`--fast`. `--model` schließt `--tier`, `--boost` und
`--fast` aus. Beides nur, wenn der User es ausdrücklich so verlangt.

Fehlt ein Stufenmodell im Codex-Katalog, fällt der Aufruf erst auf `advanced` (sol) zurück und erst danach
auf die Wahl der CLI. Der Umweg ist Absicht: `codex exec` ohne Modellangabe landet auf dem Flaggschiff, ein
direkter Sprung dorthin wäre teurer als die Stufe, die ersetzt werden soll. Im letzten Schritt übergibt das
Skript weder Modell noch Effort, beides entscheidet dann die CLI. Dorthin führt auch ein fehlender oder
unlesbarer Katalog. Der Rückfall steht als Warnung auf stderr. Bei `--model` gibt es keinen Rückfall: ein
Slug, den der Katalog nicht kennt, ist ein Fehler (geprüft wird der volle Katalog, auch versteckte
Modelle); ist der Katalog nicht lesbar, geht der Slug ungeprüft durch.

Der Rückfall passiert im Skript. Bei einer solchen Warnung nicht denselben Aufruf mit einer höheren Stufe
wiederholen — das wäre teurer als der Rückfall, den das Skript schon gewählt hat. Stattdessen melden, dass
die Stufentabelle gegen den Katalog veraltet ist.

## Rechte der anderen CLI

| Modus | Codex (`codex exec`) | Claude (`claude -p`) |
|---|---|---|
| ask | `-s read-only` | `dontAsk`, Tools Read/Glob/Grep/Bash, keine allow-Regeln: Bash nur im eingebauten Read-only-Set; deny für `Edit`, schreibende `git branch`-Formen und `git * --out*` |
| execute | `-s workspace-write` | `acceptEdits`, Edit/Write/Bash, Web verboten; `git push` **nur Prompt-Anweisung plus Textmuster, keine technische Sperre** |

Codex sandboxt das Dateisystem, Claude nicht: bei `execute` mit Ziel Claude sichert nur die Anweisung im
Handover, dass außerhalb des Workspace nichts passiert. Deshalb `execute` nur auf Feature-Branch.

Grenzen der Claude-Regeln (belegt in [Configure permissions](https://code.claude.com/docs/en/permissions)):
Bash-Regeln matchen den Befehlstext, keine Programmgrenze.

- **ask:** Lesend ist, was Claude Code in seinem eingebauten Read-only-Set als „read-only forms of git"
  führt; welche Optionen dazu zählen, ist nicht im Einzelnen dokumentiert. Die deny-Regeln fangen die
  bekannten schreibenden Formen (`git branch -D`, `git log --output=…`) zusätzlich über den Text ab.
- **execute:** Die deny-Regeln `git push *`, `git * push`, `git * push *` fangen auch `git -C . push`, aber
  nicht `git 'push'`, `/usr/bin/git push` oder `sh -c 'git push'`. Ob gepusht wird, entscheidet dort am Ende
  die Anweisung „kein Push". Wer das ausschließen muss, braucht eine Grenze außerhalb von Claude Code
  (etwa fehlende Push-Rechte auf dem Remote).

## Unter Codex

`claude -p` braucht Netz. Die Codex-Sandbox sperrt Netz standardmäßig, der Aufruf muss deshalb mit
`require_escalated` gestartet werden. Das Skript warnt, wenn `CODEX_SANDBOX_NETWORK_DISABLED=1` gesetzt ist.
