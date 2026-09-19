# Messung: bibliothekarin – Fachwissen erst bei Bedarf laden

- **Datum:** 2026-09-19
- **Branch:** `feature/lazy-karin`
- **Rohwerte:** [`messung-lazy-karin-2026-09-19.csv`](messung-lazy-karin-2026-09-19.csv) (Formatbeschreibung in der ersten Zeile)
- **Vorlage:** [`messung-lazy-skills-2026-09-18.md`](messung-lazy-skills-2026-09-18.md). Messaufbau, Isolation, Begriffe und Metriken gelten wie dort, hier stehen nur die Abweichungen.

## Zweck

Der Umbau auf bibliothekarin 0.7.0 folgt dem Muster der Persona-Plugins (siehe `CLAUDE.md`, Abschnitt „Persona-Plugins: Fachwissen nur im Agenten“, Ausnahme `bibliothekarin`):

- Der Agent `bibliothekarin` lädt per `skills:` nur noch `obsidian-cli` vor statt 8 Skills; den Rest liest er über eine Tabelle bei Bedarf.
- `bibliothekarin-search` lädt nichts mehr vor.
- `diagramm-auswahl`, `mermaid` und `plantuml` tragen `disable-model-invocation: true` und `agents/openai.yaml` mit Sperre.
- `obsidian-bases` und `json-canvas` liegen unter `references/` statt `skills/`.

Gemessen ist nur statisch und mit der Baseline („Antworte nur mit OK.“), keine Arbeitsaufträge.

## Messaufbau

| | vorher | nachher |
|---|---|---|
| Commit | `main` 90c3510 | `feature/lazy-karin` 99d7504 |
| bibliothekarin | 0.6.1 | 0.7.0 |
| nixie / it-grundschutz / bertram / christian / tools | 0.5.0 / 0.5.0 / 0.2.0 / 0.3.0 / 0.2.0 | unverändert |
| `vendors/obsidian-skills` | c4728b3 | c4728b3 |

- **Versionen:** Claude Code 2.1.272, codex-cli 0.154.0, tiktoken 0.12.0, mitmproxy 12.2.3.
- „vorher“ entspricht der beim User installierten bibliothekarin 0.6.1; der Codex-Plugin-Cache in `codex-before` ist byte-gleich mit dem User-Cache.
- Isolation wie in der Vorlage: Quellbäume per `git archive` nach `/tmp/lazy-karin/{before,after}`, Vendor-Inhalt kopiert, alle Vendor-Symlinks von bibliothekarin (je Zustand 5) lösen auf. Claude mit sechsmal `--plugin-dir` und Settings-Overlay; im init-Event genau 6 Plugins `@inline`, keine `@muhackel-plugins`. Codex mit eigenem `CODEX_HOME` je Zustand.

### Modelle

| Messung | Hauptsitzung | Agent | Nebenrequests |
|---|---|---|---|
| Claude `/context` | claude-opus-5[1m] (Default) | – | kein Modellaufruf |
| Claude Baseline | `--model sonnet` (claude-sonnet-5) | claude-opus-5 (Frontmatter `model: opus`) | Titel claude-haiku-4-5-20251001; Auto-Mode-Klassifikator claude-sonnet-5 |
| Codex prompt-input | `-m gpt-5.6-sol`, kein Modellaufruf | – | – |

### Abweichungen von der Vorlage

1. **Watchdog erweitert:** Die Kopie unter `/tmp/lazy-karin/scripts/watchdog.py` blockt zusätzlich jeden `obsidian`-Aufruf, dessen Unterbefehl nicht auf einer Leseliste steht (`read`, `search`, `tags`, `backlinks`, `daily:read` u. a.). Die Vorlage erkennt Vault-Schreibzugriffe über die Obsidian-CLI nicht, weil sie über die App laufen. Default von `LAZY_MESS` auf `/tmp/lazy-karin` umgestellt.
2. **Umgebung:** In allen Claude-Läufen (auch `/context`) entfernt: alle `CLAUDE*`-Variablen der Elternsitzung (u. a. `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_EFFORT`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_MESSAGING_*`, `CLAUDE_PID`), `AI_AGENT` und die Plugin-Cache-Pfade im PATH. Die Vorlage tat das nur in den dynamischen Läufen.
3. **`/context`:** Beide MCP-Server waren schon in Lauf 1 `connected`. Alle 4 Läufe je Zustand sind textgleich und gewertet.
4. **Proxy:** Die Proxy-Skripte der Vorlage liegen nicht im Repo. Nachgebaut ist die dort empfohlene Variante: `HTTPS_PROXY` auf mitmdump mit TLS-MITM nur für api.anthropic.com (`--allow-hosts`), CA per `NODE_EXTRA_CA_CERTS`, ein Addon schreibt je Request usage, Modell und `cc_is_subagent`. Kontrolle: `/context` über den Proxy ist textgleich mit dem direkten Lauf.
5. **main_first über Proxy unverzerrt:** Anders als in der Vorlage stimmt `main_first` mit `--model sonnet` über den Proxy mit dem direkten Lauf überein (35.398 zu 35.400, 34.460 zu 34.459). Gewertet ist trotzdem wie in der Vorlage der direkte Lauf.
6. **Hauptprompt protokolliert:** „Starte per Agent-Tool den Agenten `<agent>` mit dem Auftrag „Antworte nur mit OK.“ (wörtlich als Prompt) und gib danach nur seine Antwort aus.“ Der Spawn-Prompt war in allen 8 Läufen wörtlich „Antworte nur mit OK.“
7. **Keine Zusatzreihe** mit dem Default-Modell als Hauptsitzung, keine Wiederholungen.

## Ergebnisse

### 1. Hauptkontext Claude Code (`/context`)

| Kategorie | vorher | nachher | Δ |
|---|---:|---:|---:|
| System tools | 6,4k | 7k | +0,6k (Artefakt, siehe Vorlage) |
| Custom agents | 1,5k | 1,4k | −0,1k |
| Skills | 3,1k | 2,5k | −0,6k |
| übrige Kategorien | gleich | gleich | 0 |
| **Summe (Tokens-Zeile)** | **16,6k** | **16,5k** | **−0,1k** |

bibliothekarin im Detail (Skills als `/context`-Schätzwerte, Agenten exakt):

| Eintrag | vorher | nachher | Δ |
|---|---:|---:|---:|
| karin, vault (Commands) | 30 + 30 | 30 + 30 | 0 |
| defuddle | 130 | 130 | 0 |
| obsidian-cli | 170 | 170 | 0 |
| obsidian-markdown | 100 | 100 | 0 |
| diagramm-auswahl | 130 | – | −130 |
| mermaid | 130 | – | −130 |
| plantuml | 160 | – | −160 |
| json-canvas | 90 | – | −90 |
| obsidian-bases | 100 | – | −100 |
| **Skills bibliothekarin (Einträge)** | **1.070 (10)** | **460 (5)** | **−610 (−57,0 %)** |
| Agent `bibliothekarin` | 362 | 231 | −131 (−36,2 %) |
| Agent `bibliothekarin-search` | 99 | 99 | 0 |
| **Agenten bibliothekarin** | **461** | **330** | **−131 (−28,4 %)** |

Das System-tools-Artefakt der Vorlage tritt wieder auf: `count_tokens` der System-Tools ist 9.545 in beiden Zuständen, `/context` zieht die Skill-Schätzung davon ab. Die Summenzeile zeigt die Skill-Ersparnis deshalb nicht.

### 2. Codex-Startprompt (`debug prompt-input "Hallo"`)

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| bibliothekarin Einträge | 5 | 2 | −3 |
| bibliothekarin Zeichen | 1.618 | 295 | −1.323 (−81,8 %) |
| bibliothekarin Tokens | 436 | 82 | −354 (−81,2 %) |
| bibliothekarin Skill-Roots (Anzahl / Zeichen / Tokens) | 2 / 229 / 84 | 1 / 129 / 46 | −1 / −100 / −38 |
| `<skills_instructions>` Zeichen / Tokens | 6.587 / 1.749 | 5.162 / 1.357 | −1.425 / −392 |
| Katalogeinträge gesamt (davon System) | 14 (5) | 11 (5) | −3 |
| Rest außerhalb Skills (9 Items), Tokens | 3.573 | 3.575 | +2 (cwd-Pfad) |
| **Prompt gesamt, Zeichen** | **22.022** | **20.597** | **−1.425 (−6,5 %)** |
| **Prompt gesamt, Tokens** | **5.322** | **4.932** | **−390 (−7,3 %)** |

- Nachher stehen von bibliothekarin nur noch `source-command-karin` (146 Zeichen / 41 Tokens) und `source-command-vault` (149 / 41) im Katalog; beide sind unverändert.
- `diagramm-auswahl`, `mermaid` und `plantuml` fehlen wegen `allow_implicit_invocation: false`. Die übrigen fünf Skills standen in Codex schon vorher nicht im Katalog (Vendor-Symlinks, siehe Auffälligkeiten).
- Der Vorher-Prompt liegt nahe am Nachher-Stand der Vorlage (22.048 Zeichen / 5.334 Tokens); die Differenz von 26 Zeichen ist nicht einzeln aufgeschlüsselt.

### 3. Baseline Claude Code (Auftrag „Antworte nur mit OK.“)

Hauptsitzung `--model sonnet`, Agent claude-opus-5. `main_first` und `cost_usd` aus Läufen ohne Proxy, `sub_*` aus Läufen mit Proxy.

| Agent | sub_first vorher | nachher | Δ |
|---|---:|---:|---:|
| `bibliothekarin:bibliothekarin` | 30.318 | 13.463 | −16.855 (−55,6 %) |
| `bibliothekarin:bibliothekarin-search` | 8.455 | 7.344 | −1.111 (−13,1 %) |

| Agent | sub_sum v → n (Δ) | sub_n | sub_peak v → n | main_first v → n (Δ) | cost_usd v → n | duration_s v → n |
|---|---|---|---|---|---|---|
| bibliothekarin | 92.001 → 27.754 (−69,8 %) | 3 → 2 | 31.311 → 14.291 | 35.400 → 34.459 (−941) | 0,3838 → 0,1575 | 13,1 → 14,5 |
| bibliothekarin-search | 26.625 → 15.513 (−41,7 %) | 3 → 2 | 9.664 → 8.169 | 35.401 → 34.462 (−939) | 0,1391 → 0,0956 | 17,7 → 9,8 |

- **Vorladen:** Vorher enthält der erste Request von `bibliothekarin` 8 Skill-Texte als Messages (40.724 Zeichen inklusive Köpfe, davon obsidian-bases 12.807, json-canvas 7.456, obsidian-markdown 5.162). Nachher nur obsidian-cli (2.889 Zeichen). Der Systemprompt des Agenten schrumpft leicht (12.525 → 12.242 Zeichen), weil die Formate der Arbeitsdateien nach `references/arbeitsdateien.md` gewandert sind.
- **`bibliothekarin-search`:** Die Differenz ist genau das nicht mehr vorgeladene obsidian-cli (2.890 Zeichen); der Systemprompt ist gleich (3.409 Zeichen).
- **Verhalten:** Wie in der Vorlage antwortet der Agent vorher erst mit „OK“ und meldet dann per `SubagentHandback` ausführlicher zurück (3 Requests). Nachher ruft er direkt `SubagentHandback` auf (2 Requests). Output Haupt + Agent: 414 → 220 bzw. 610 → 279 Tokens.
- **`files_read`:** in allen 8 Läufen 0. Laut Hook-Trace waren die einzigen Tool-Aufrufe `Agent` (Hauptsitzung) und `SubagentHandback` (Agent). Karin hat den STARTUP nicht ausgeführt, weder Vault noch Plugin-Dateien gelesen und nichts zu schreiben versucht; der Watchdog hat nichts blockiert.
- **Nebenkosten, in beiden Zuständen gleich:** 1 Titel-Request (932–934 Tokens) und 2 Klassifikator-Requests (je 45.658–45.998 Tokens).

## Auffälligkeiten

1. **cost_usd streut:** Der direkte Nachher-Lauf von `bibliothekarin` hat länger zurückgemeldet als der Proxy-Lauf (Opus-Output 323 zu 59 Tokens) und kostet 0,1575 statt 0,1081 USD. Die Richtung ist in allen vier Paaren gleich, die Höhe ist bei n=1 und abhängig vom Cache nur grob belastbar.
2. **main_first sinkt nur um ~940 Tokens (−2,7 %):** Das ist die kürzere Skill- und Agentenliste. Die große Ersparnis liegt im Agenten, nicht in der Hauptsitzung.
3. **Codex installiert die Vendor-Symlinks nicht** (wie in der Vorlage, Auffälligkeit 11): Im Codex-Cache fehlen in beiden Zuständen `obsidian-markdown`, `defuddle`, `obsidian-cli`, und nachher enthält `references/` nur `arbeitsdateien.md`, nicht `json-canvas` und `obsidian-bases`. Die Lesetabelle im Agenten verweist in Codex damit für fünf von acht Dateien ins Leere. Nicht Teil dieser Messung, aber relevant für Karin unter Codex.
4. **Vault unberührt:** Unter `~/Documents/Memory` hat sich seit dem ersten Messlauf keine Datei geändert (letzte Änderung `.git` 07:42, vor dem Setup).
5. **Aufräumen:** Die von Claude trotz `--no-session-persistence` angelegten `~/.claude/projects/-tmp-lazy-karin-*` (nur `subagents/agent-*.meta.json`) sind gelöscht.

## Gemessen und geschätzt

- **Gemessen:** alle Proxy- und stream-json-Werte (Tokens je Request, Kosten, Dauer), die exakten Agentenwerte aus `/context`, alle Codex-Werte (Zeichen exakt, Tokens mit tiktoken `o200k_base`).
- **Geschätzt:** die Skill-Einträge in `/context` (`~`-Werte der CLI) und die k-gerundeten Kategorien. Ob gpt-5.6-sol genau `o200k_base` verwendet, ist wie in der Vorlage nicht geprüft.

## Wiederholen

Wie in der Vorlage, Abschnitt „Wiederholen der Messung“, mit den Commits 90c3510 und 99d7504 und Basis `/tmp/lazy-karin`. Der erweiterte Watchdog, der Umgebungs-Wrapper `claude-run.sh` und das Proxy-Addon lagen nur unter `/tmp/lazy-karin` und sind nicht im Repo.
