# Messung: Persona-Fachwissen erst bei Bedarf laden

- **Datum:** 2026-09-18
- **Branch:** `feature/lazy-skills`
- **Rohwerte:** [`messung-lazy-skills-2026-09-18.csv`](messung-lazy-skills-2026-09-18.csv) (alle Einzelwerte, Formatbeschreibung in der ersten Zeile)

## Zweck

Diese Referenzmessung entstand vor dem Merge von `feature/lazy-skills`. Der Branch baut die Persona-Plugins bertram, christian, it-grundschutz (Persona Bruce) und nixie so um, dass ihr Fachwissen nicht mehr im Kontext der Hauptsitzung steht. Die Agenten lesen ihre Skills erst bei Bedarf (siehe `CLAUDE.md`, Abschnitt „Persona-Plugins: Fachwissen nur im Agenten“).

Gemessen ist in Claude Code und in Codex, wie viel Kontext die Plugins vorher und nachher belegen:

- im Startkontext der Hauptsitzung,
- im ersten Request der Persona,
- über einen typischen Arbeitsauftrag je Persona.

bibliothekarin und tools sind unverändert und laufen als Konstante mit. Die Werte dienen als Vergleichsbasis für spätere Änderungen an den Plugins und für neue CLI-Versionen.

**Die dynamischen Messungen (Arbeitsaufträge) sind Einzelläufe (n=1), so vom User entschieden. Ihre Streuung ist nicht erfasst.** Die statischen Messungen sind deterministisch: Wiederholungen ergaben identische Werte oder Abweichungen von höchstens 2 Tokens.

## Messaufbau

### Stände und Versionen

| | vorher | nachher |
|---|---|---|
| Commit | `main` f22c0dc | `feature/lazy-skills` 71871af |
| bibliothekarin | 0.6.1 | 0.6.1 |
| nixie | 0.4.1 | 0.5.0 |
| it-grundschutz | 0.4.1 | 0.5.0 |
| bertram | 0.1.1 | 0.2.0 |
| christian | 0.2.1 | 0.3.0 |
| tools | 0.2.0 | 0.2.0 |
| `vendors/obsidian-skills` | c4728b3 | c4728b3 |

- **Versionen:**
  - Claude Code 2.1.272, codex-cli 0.154.0.
  - Die Plugin-Versionen sind je Zustand in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` und im Claude-Marketplace gleich.
  - „vorher“ entspricht der beim User installierten Version, in Claude und in Codex.
- **Unveränderte Plugins:** bibliothekarin und tools sind in main und HEAD inhaltsgleich (`git diff --stat main HEAD` findet dort nichts).

### Isolation

- **Quellbäume:**
  - Beide Stände wurden per `git archive` nach `/tmp/lazy-mess/before` bzw. `/tmp/lazy-mess/after` entpackt.
  - Den Inhalt des Vendor-Submoduls hat der Setup-Agent kopiert (`.claude-plugin`, `LICENSE`, `README.md`, `skills/`), ohne die `.git`-Zeigerdatei.
  - Alle 6 Vendor-Symlinks lösen auf.
- **Claude Code:**
  - Aufruf mit `-p --output-format stream-json --verbose --no-session-persistence`, sechsmal `--plugin-dir` auf den jeweiligen Baum.
  - `--settings` legt ein Overlay über die User-Settings, das die sechs installierten `@muhackel-plugins` abschaltet.
  - Im init-Event geprüft:
    - genau 6 Plugins `@inline` mit den richtigen Versionen, 0 Einträge `@muhackel-plugins`;
    - die übrigen User-Settings wirken weiter: permissionMode auto, `~/.claude/CLAUDE.md` als Memory (2,8k), claude.ai-MCP (Docs, Drive), statusLine, env, language;
    - grimm, unslop, ask und philharmonie bleiben wie beim User inaktiv.
- **Codex:**
  - Je Zustand gibt es ein eigenes `CODEX_HOME` (`/tmp/lazy-mess/codex-before` bzw. `codex-after`).
  - `config.toml` ist die User-Config ohne `[marketplaces.muhackel-plugins]` und ohne die Abschnitte `[plugins."*@muhackel-plugins"]`. Der Rest ist byte-gleich: gpt-5.6-sol, Effort high, `approvals_reviewer = "auto_review"`.
  - `AGENTS.md` und `auth.json` sind Symlinks auf `~/.codex`.
  - Die Plugins kamen per lokalem Marketplace auf den jeweiligen Baum. Der Plugin-Cache in `codex-before` ist byte-gleich mit dem User-Cache.
  - `TMPDIR=/tmp/lazy-mess/tmpdir` verhindert die Warnung „Refusing to create helper binaries“ und legt `tmp/arg0` wie beim User an.
- **Schutz:**
  - Claude: ein PreToolUse-Hook (`watchdog.py hook`, Matcher `*`) blockt verbotene Aufrufe vorab. Er kostet 0 Tokens: `/context` zeigt mit und ohne Hook 16,6k.
  - Beide CLIs: ein Stream-Watchdog (`watchdog.py run`) beendet den Lauf bei verbotenen `tool_use`-Aufrufen.
  - Die Regeln sperren:
    - `nixos-rebuild` und `nh` (switch/boot/test/build),
    - `nix build`, `nix-build` und `nix flake check` ohne Dry-Run bzw. `--no-build`,
    - `nix copy` und Deploy-Tools,
    - ssh/scp/rsync auf fremde Hosts,
    - Schreibzugriffe, Umleitungen und mutierende git-Befehle außerhalb `/tmp`,
    - `sudo` und mutierendes `systemctl`.
- **Umgebung der Elternsitzung:** In den dynamischen Claude-Läufen von bertram, christian und bruce entfernt.
  - Betroffen waren `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT=sdk-ts`, `CLAUDE_EFFORT=xhigh`, `CLAUDE_CODE_CHILD_SESSION` und Session-IDs. Bei christian kamen `CLAUDE_CODE_MESSAGING_*` und die Plugin-Cache-Pfade im PATH dazu.
  - Die Request-Bodies von bertram und christian zeigen danach Effort high.
  - Die Berichte zu nixie und zur statischen Messung erwähnen das Thema nicht.

### Modelle

| Messung | Hauptsitzung | Persona / Subagent | Nebenrequests |
|---|---|---|---|
| Claude `/context` | claude-opus-5[1m] (Default) | – | kein Modellaufruf |
| Claude Baseline | `--model sonnet` (claude-sonnet-5); Zusatzreihe mit Default claude-opus-5[1m] | claude-opus-5 | Titel-Request; Auto-Mode-Klassifikator claude-sonnet-5 |
| Claude dynamisch | claude-opus-5[1m] ohne `--model`; Effort high (belegt für bertram und christian) | claude-opus-5 | Klassifikator claude-sonnet-5; WebSearch-/WebFetch-Helfer (bertram, nixie: Haiku; christian: laut `modelUsage` claude-opus-5) |
| Codex prompt-input | `-m gpt-5.6-sol`, kein Modellaufruf | – | – |
| Codex dynamisch | gpt-5.6-sol, Effort high: ohne `-m` gestartet, Wert aus `config.toml` (laut `turn_context`) | gpt-5.6-sol, high | Guardian `codex-auto-review`, Effort low, nur bei Eskalationen (nur bei bruce berichtet) |

### Messungen

| Messung | Was | Läufe |
|---|---|---|
| `context` | `claude -p "/context"` ohne Modellaufruf | je Zustand 4; gewertet Lauf 3 und 4 (identisch), in Lauf 1 und 2 war ein MCP-Server noch `pending` |
| `baseline` | Hauptsitzung startet die Persona per Agent-Tool mit dem Auftrag „Antworte nur mit OK.“ | je Persona und Zustand 1 Lauf ohne Proxy (main_first, Kosten) und 1 mit Proxy (sub_*); bertram zusätzlich wiederholt; Zusatzreihe mit Default-Modell |
| `prompt-input` | `codex debug prompt-input "Hallo"` | je Zustand 1, dazu 1 Kontrolllauf mit `TMPDIR` und 2 aus dem Setup; alle textgleich bis auf den cwd-Pfad |
| `dynamisch` (Claude) | Persona-Command plus Arbeitsauftrag | je Persona und Zustand 1 (bertram nachher: 2. Lauf gewertet, siehe Beobachtungen) |
| `dynamisch-implizit` (Codex) | nur der Arbeitsauftrag | je Persona und Zustand 1 |
| `dynamisch-explizit` (Codex) | `$<plugin>:source-command-<name>` plus Arbeitsauftrag | je Persona und Zustand 1 |

Arbeitsaufträge (User-Text, in beiden CLIs gleich):

| Persona | User-Text |
|---|---|
| bertram | Zwischen zwei Cat9300 (IOS-XE 17.9) steigen die CRC-Fehler auf dem Uplink Te1/1/1. Welche Diagnose-Sequenz schlägst du vor? Nur Vorschlag, nichts ausführen. |
| christian | Ich will zwei Standorte (je ein Debian-Router, LAN 10.1.0.0/24 und 10.2.0.0/24) per WireGuard koppeln. Entwirf die Config für beide Seiten, nur als Vorschlag, nichts ausführen. |
| bruce | Schlag die Anforderung GC.1.1 zitierfähig nach. Nur lesen, nichts ändern. |
| nixie | Schreib mir eine Derivation für ein kleines Go-Tool von GitHub (Platzhalter-Repo). Nur Entwurf ausgeben, nichts bauen, nichts deployen, nichts in Dateien schreiben. |

### Metriken

| Metrik | Definition |
|---|---|
| Tokens je Request (Claude) | `input_tokens + cache_creation_input_tokens + cache_read_input_tokens` aus der API-usage; Output getrennt. Die Summe hängt nicht vom Cache-Zustand ab. |
| Tokens je Request (Codex) | `input_tokens` aus `token_usage_record` (inklusive cached); Output inklusive reasoning |
| `main_first` | erster Request der Hauptsitzung bzw. des Codex-Hauptthreads |
| `main_peak`, `main_sum`, `main_n` | größter Request, Summe und Anzahl der Requests der Hauptsitzung |
| `sub_first`, `sub_peak`, `sub_sum`, `sub_n` | wie oben für die Persona. Claude: Requests mit `cc_is_subagent=true` im Billing-Header und Persona im Systemprompt. Codex: Subagent-Rollout über `parent_thread_id`; bei `fork_turns=all` enthält `sub_first` den Kontext des Hauptthreads. |
| `helfer_*` (Claude) | WebSearch-/WebFetch-Auswertungen, markiert als Subagent, aber ohne Persona; nicht in `sub_*` |
| `klassifikator_*` (Claude) | Auto-Mode-Klassifikator („security monitor“), weder main noch sub; nicht in `total_cost_usd` |
| `guardian_*` (Codex) | Thread des `auto_review`-Reviewers; in `total_*` enthalten |
| `total_*` (Codex) | Haupt + Subagent (+ Guardian); `total_uncached = total_sum − total_cached` |
| `output_sum` (Claude) | Haupt + Persona + Helfer, ohne Klassifikator. Beim Zusammenführen aus Teilwerten vereinheitlicht, weil die Messagenten verschieden gezählt hatten. |
| `files_read` | Plugin-Dateien, die Persona oder Hauptthread gelesen haben (Claude: Read, Codex: Shell-Reads). In Codex zählen die Messagenten teils Lesevorgänge, teils verschiedene Dateien; die Liste steht in der CSV-Anmerkung. |
| `cost_usd` | `total_cost_usd` des einzigen result-Events (Claude); Codex meldet keine USD |
| `duration_s` | Claude: `result.duration_ms`; Codex: Wanduhr des `exec`-Laufs |
| `/context`-Werte | Anzeige der CLI: k-gerundete Kategorien, `~`-Schätzwerte je Skill |
| Codex-Startprompt | Zeichen (Codepoints) und Tokens (tiktoken 0.12.0, `o200k_base`) der 10 `input_text`-Items aus `debug prompt-input` |

### Nicht gemessen

- **Streuung:** Die dynamischen Läufe sind Einzelläufe, Varianz und Konfidenz fehlen.
- **Kosten:** Klassifikator (Claude) und Codex-Läufe haben keinen USD-Wert.
- **Codex-Prompt unvollständig:**
  - `debug prompt-input` enthält keine Base-Instructions, keine Tool-Schemas und kein Framing.
  - Ob gpt-5.6-sol genau `o200k_base` verwendet, ist nicht geprüft.
- **Persona-Kontext:** Den Kontext der Persona zeigt `/context` nicht an. Er ist nur über Proxy und stream-json gemessen.
- **Qualität:** Sie ist nur als Kurzurteil der Messagenten erfasst, ohne Bewertungsschema.
- **Konstanten:** bibliothekarin und tools sind nur statisch erfasst, nicht mit dynamischen Läufen.
- **Codex-Testumgebung:**
  - Die Remote-Plugins des Users (github, openai-templates, plugin-management) und seine Codex-Memories fehlen.
  - Das cwd ist nicht trusted.

## Ergebnisse

### 1. Hauptkontext Claude Code (`/context`)

| Kategorie | vorher | nachher | Δ |
|---|---:|---:|---:|
| System prompt | 2,1k | 2,1k | 0 |
| System tools | 1,9k | 6,4k | +4,5k (Artefakt, siehe unten) |
| MCP tools | 627 | 627 | 0 |
| MCP tools (deferred) | 7,3k | 7,3k | 0 |
| System tools (deferred) | 13,4k | 13,4k | 0 |
| Custom agents | 2,6k | 1,5k | −1,1k |
| Memory files | 2,8k | 2,8k | 0 |
| Skills | 7,6k | 3,1k | −4,5k |
| Messages | 8 | 8 | 0 |
| **Summe (Tokens-Zeile)** | **17,8k** | **16,6k** | **−1,2k** |

Je Plugin, Skill-Einträge als `/context`-Schätzwerte, Agenten exakt:

| Plugin | Skills vorher (Einträge) | Skills nachher | Δ | Agent vorher | Agent nachher | Δ |
|---|---:|---:|---:|---:|---:|---:|
| bibliothekarin | 1.070 (10) | 1.070 (10) | 0 | 461 (2 Agenten) | 461 | 0 |
| nixie | 550 (5) | 0 | −550 | 308 | 260 | −48 |
| it-grundschutz | 1.610 (9) | 0 | −1.610 | 709 | 257 | −452 |
| bertram | 850 (6) | 0 | −850 | 549 | 264 | −285 |
| christian | 1.560 (7) | 0 | −1.560 | 594 | 257 | −337 |
| tools | 0 | 0 | 0 | – | – | – |
| **Plugins gesamt** | **5.640** | **1.070** | **−4.570** | **2.621** | **1.499** | **−1.122** |
| Built-in (13 Skills) | 2.050 | 2.050 | 0 | – | – | – |

- **Skill-Einträge:** Sie enthalten auch die Commands, bei den Personas je 30–40 Tokens. Nachher fehlen alle Einträge von nixie, it-grundschutz, bertram und christian im Listing, auch die Commands, die jetzt `disable-model-invocation: true` tragen.
- **tools** steht in keinem Zustand im Listing.
- **Rechenfehler in `/context`:**
  - `count_tokens` für die 11 eager geladenen System-Tools ergibt in beiden Zuständen 9.545, das Skill-Tool allein 917.
  - `/context` zieht die Skill-Schätzung davon ab: 9.545 − 7.690 ≈ 1,9k und 9.545 − 3.120 ≈ 6,4k.
  - Die Skill-Ersparnis fehlt deshalb in der Summenzeile; die −1,2k dort sind fast nur die Custom agents.
  - Den echten Unterschied im ersten Request zeigen Abschnitt 3 und 4.
- **Werte je Skill:** stehen in der CSV (`messung=context`, `metrik=skill:<name>`).

### 2. Codex-Startprompt (`debug prompt-input`)

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| Prompt gesamt, Zeichen | 35.267 | 22.048 | −13.219 (−37,5 %) |
| Prompt gesamt, Tokens | 9.147 | 5.334 | −3.813 (−41,7 %) |
| Prompt gesamt, UTF-8-Bytes | 35.514 | 22.153 | −13.361 |
| JSON-Ausgabe, Bytes | 38.347 | 24.957 | −13.390 |
| `<skills_instructions>`, Zeichen / Tokens | 19.796 / 5.562 | 6.579 / 1.749 | −13.217 / −3.813 |
| Katalogeinträge gesamt (davon System) | 37 (5) | 14 (5) | −23 |
| Plugin-Einträge, Zeichen / Tokens | 16.212 / 4.594 | 3.796 / 1.080 | −12.416 / −3.514 |
| Skill-Roots: Anzahl / Zeichen / Tokens | 11 / 1.148 / 429 | 4 / 347 / 130 | −7 / −801 / −299 |
| Rest außerhalb Skills (9 Items), Zeichen / Tokens | 15.471 / 3.585 | 15.469 / 3.585 | −2 / 0 |

| Plugin | Einträge v → n | Zeichen v → n (Δ) | Tokens v → n (Δ) |
|---|---|---|---|
| bibliothekarin | 5 → 5 | 1.618 → 1.618 (0) | 436 → 436 (0) |
| nixie | 5 → 1 | 1.827 → 551 (−1.276) | 523 → 160 (−363) |
| it-grundschutz | 9 → 1 | 5.124 → 571 (−4.553) | 1.385 → 162 (−1.223) |
| bertram | 6 → 1 | 2.780 → 501 (−2.279) | 790 → 158 (−632) |
| christian | 7 → 1 | 4.863 → 555 (−4.308) | 1.460 → 164 (−1.296) |
| tools | 0 → 0 | 0 → 0 | 0 → 0 |
| System (`.system`) | 5 → 5 | 2.083 → 2.083 | 459 → 459 |

Der einzige verbleibende Eintrag je Persona ist der migrierte Command. Er ist nachher länger:

| Eintrag | vorher Zeichen / Tokens | nachher Zeichen / Tokens |
|---|---|---|
| nixie:source-command-nixie | 135 / 43 | 551 / 160 |
| it-grundschutz:source-command-bruce | 152 / 42 | 571 / 162 |
| bertram:source-command-bertram | 146 / 42 | 501 / 158 |
| christian:source-command-christian | 167 / 44 | 555 / 164 |

- **Ursachen der Längenzunahme:**
  - Die Beschreibung hat nachher 371–431 statt 63–83 Zeichen.
  - Der Pfad hat 90–99 statt 40–44 Zeichen, weil sich die vier Persona-Plugins nachher den Root `r1 = plugins/cache/muhackel-plugins` teilen.
- **Außerhalb `<skills_instructions>`:** Die 9 übrigen Items sind nach Normierung des cwd-Pfads textgleich. `<plugins_instructions>` ist generisch (1.014 Zeichen / 209 Tokens) und listet keine Plugins.
- **Ausgeblendete Skills:** tools ist in beiden Zuständen nicht im Katalog; seine 7 Skills tragen `allow_implicit_invocation: false`. Nachher gilt das auch für alle Fach-Skills von bertram (5), christian (6), it-grundschutz (8) und nixie (4).

### 3. Persona-Baseline Claude Code (Auftrag „Antworte nur mit OK.“)

Die Hauptsitzung lief mit `--model sonnet`, die Persona mit claude-opus-5. `main_first` stammt aus Läufen ohne Proxy, `sub_*` aus Läufen mit Proxy.

| Persona | main_first vorher | nachher | Δ | sub_first vorher | nachher | Δ |
|---|---:|---:|---:|---:|---:|---:|
| bertram | 43.771 | 35.412 | −8.359 (−19,1 %) | 22.553 | 12.123 | −10.430 (−46,2 %) |
| christian | 43.768 | 35.410 | −8.358 (−19,1 %) | 43.705 | 14.176 | −29.529 (−67,6 %) |
| bruce | 43.775 | 35.416 | −8.359 (−19,1 %) | 35.138 | 13.044 | −22.094 (−62,9 %) |
| nixie | 43.772 | 35.412 | −8.360 (−19,1 %) | 26.506 | 12.633 | −13.873 (−52,3 %) |

| Persona | sub_sum v → n (Δ) | sub_n | sub_peak v → n | cost_usd v → n | duration_s v → n |
|---|---|---|---|---|---|
| bertram | 68.839 → 25.071 (−63,6 %) | 3 → 2 | 23.682 → 12.948 | 0,2340 → 0,1048 | 10,3 → 9,9 |
| christian | 132.257 → 29.177 (−77,9 %) | 3 → 2 | 44.796 → 15.001 | 0,4156 → 0,1468 | 13,4 → 8,3 |
| bruce | 106.791 → 26.913 (−74,8 %) | 3 → 2 | 36.464 → 13.869 | 0,3615 → 0,1386 | 24,0 → 7,4 |
| nixie | 80.654 → 26.091 (−67,7 %) | 3 → 2 | 27.591 → 13.458 | 0,2896 → 0,1358 | 13,8 → 7,2 |

Zusatzreihe mit dem User-Default claude-opus-5[1m] als Hauptsitzung (Proxy):

| Persona | main_first v → n (Δ) | sub_first v → n (Δ) |
|---|---|---|
| bertram | 31.837 → 23.478 (−8.359) | 22.437 → 12.008 (−10.429) |
| christian | 31.834 → 23.477 (−8.357) | 43.588 → 14.061 (−29.527) |
| bruce | 31.841 → 23.482 (−8.359) | 35.021 → 12.928 (−22.093) |
| nixie | 31.836 → 23.476 (−8.360) | 26.389 → 12.516 (−13.873) |

- **Kontrolle ohne Proxy (bertram, Default-Modell):** 32.046 → 23.688 (−8.358). Der Proxy liegt bei diesem Modell konstant etwa 210 Tokens darunter.
- **Vorladen:**
  - Vorher enthält der erste Persona-Request die per Frontmatter `skills:` vorgeladenen Skill-Texte: bertram 5, christian 6, bruce 8, nixie 4.
  - Nachher fehlen sie, der Persona-Systemprompt ist dafür länger (christian 10.786 → 14.157 Zeichen).
- **Verhalten:**
  - Vorher antwortet die Persona mit „OK“ und meldet danach per `SubagentHandback` ausführlich zurück: 3 Requests, 275–539 Output-Tokens.
  - Nachher ruft sie direkt `SubagentHandback("OK")` auf: 2 Requests, 56 Output-Tokens.
  - `files_read` ist überall 0.
- **Nebenkosten je Lauf, in beiden Zuständen gleich:** 1 Titel-Request (etwa 1.240 Tokens) und 2 Klassifikator-Requests (je etwa 45,7k Tokens, überwiegend cache_read).

### 4. Dynamische Läufe (je Zelle ein Lauf)

Überblick Claude Code:

| Persona | main_first Δ | sub_first Δ | sub_sum Δ | cost_usd Δ | Skills nachher gelesen |
|---|---:|---:|---:|---:|---|
| bertram | −7.719 (−23,4 %) | −10.686 (−46,8 %) | −275.372 (−60,7 %) | −0,7782 (−51,5 %) | 2 von 5 |
| christian | −7.727 (−23,5 %) | −30.129 (−67,9 %) | −262.612 (−39,6 %) | −0,8340 (−37,3 %) | 4 von 6 |
| bruce | −7.582 (−23,3 %) | −22.431 (−63,4 %) | −123.845 (−37,6 %) | −0,4016 (−40,5 %) | 1 von 8 |
| nixie | −7.486 (−23,0 %) | −14.319 (−53,2 %) | +34.762 (+12,4 %) | −0,2755 (−24,8 %) | 3 von 4 |

Überblick Codex:

| Persona | Haupt first Δ impl. | Haupt first Δ expl. | Sub first Δ expl. | gesamt sum Δ impl. | gesamt sum Δ expl. | Subagent impl. v → n |
|---|---:|---:|---:|---:|---:|---|
| bertram | −3.820 | −3.411 | −7.148 | −82.111 (−22,7 %) | −150.837 (−28,4 %) | nein → ja |
| christian | −3.462 | −3.379 | −7.170 | +249.671 (+175,2 %) | +31.120 (+9,3 %) | nein → ja |
| bruce | −3.813 | −3.315 | −7.123 | +21.545 (+10,3 %) | −244.945 (−47,9 %) | nein → ja |
| nixie | −3.813 | −3.257 | −6.941 | +145.498 (+341,3 %) | +27.776 (+23,3 %) | nein → ja |

#### bertram

Claude Code, Läufe `bertram-dyn-before` und `bertram-dyn-after2`:

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| main_first | 32.922 | 25.203 | −7.719 (−23,4 %) |
| main_sum (n) | 71.420 (2) | 53.745 (2) | −17.675 |
| sub_first | 22.845 | 12.159 | −10.686 (−46,8 %) |
| sub_peak | 49.330 | 31.319 | −18.011 (−36,5 %) |
| sub_sum (n) | 453.857 (13) | 178.485 (8) | −275.372 (−60,7 %) |
| Helfer Haiku (n / Summe) | 12 / 264.718 | 2 / 40.604 | −224.114 |
| Klassifikator (n / Summe) | 12 / 571.748 | 6 / 280.644 | −291.104 |
| Output Haupt + Persona + Helfer | 20.555 | 11.494 | −9.061 |
| cost_usd | 1,5122 | 0,7340 | −0,7782 (−51,5 %) |
| duration_s | 218,4 | 116,7 | −101,7 |
| Tool-Aufrufe der Persona | 15 (WebSearch 5, WebFetch 7, Bash 3) | 7 (Read 2, WebSearch 1, WebFetch 1, Bash 3) | −8 |
| vorgeladene Skills | 5 (21.984 Zeichen) | 0 | |
| gelesene Dateien | 0 | net-diagnose, net-reference | +2 |
| Spawn-Prompt | 697 Zeichen, eigener Rahmen | 225 Zeichen, User-Text plus Einschränkung | |

- **Qualität vorher:** gelöst. Die Diagnose-Sequenz hat 8 Schritte und arbeitet mit Richtungslogik (Rx A ↔ Tx B), DOM-Deutung und Tauschmatrix. Zitiert sind drei Cisco-Quellen.
- **Qualität nachher:** gelöst. 9 Schritte, je Kommando ein Status; 5 sind gegen die 17.9-Command-Reference verifiziert, 3 als nicht verifiziert markiert. Es gibt nur eine Quelle.

Codex:

| Metrik | vorher impl. | nachher impl. | Δ impl. | vorher expl. | nachher expl. | Δ expl. |
|---|---:|---:|---:|---:|---:|---:|
| Haupt first | 20.740 | 16.920 | −3.820 | 21.293 | 17.882 | −3.411 |
| Haupt peak | 73.587 | 25.418 | −48.169 | 22.389 | 19.075 | −3.314 |
| Haupt sum (n) | 361.394 (8) | 97.654 (5) | −263.740 | 65.165 (3) | 55.118 (3) | −10.047 |
| Sub first | – | 18.978 | n/a | 27.084 | 19.936 | −7.148 |
| Sub peak | – | 45.745 | n/a | 81.101 | 67.761 | −13.340 |
| Sub sum (n) | – | 181.629 (6) | n/a | 466.839 (9) | 326.049 (8) | −140.790 |
| gesamt sum | 361.394 | 279.283 | −82.111 (−22,7 %) | 532.004 | 381.167 | −150.837 (−28,4 %) |
| gesamt ungecacht | 63.538 | 54.387 | −9.151 | 76.324 | 69.743 | −6.581 |
| gesamt Output (reasoning) | 5.222 (3.225) | 5.289 (2.606) | +67 | 4.758 (2.143) | 5.222 (2.609) | +464 |
| gesamt n | 8 | 11 | +3 | 12 | 11 | −1 |
| injizierter Command-Skill | – | – | | 1.857 Zeichen | 3.385 Zeichen | +1.528 |
| gelesene Plugin-Dateien | 2 | 4 | +2 | 2 | 3 | +1 |
| Web-Aufrufe | 6 | 4 | −2 | 7 | 5 | −2 |
| duration_s | 119,3 | 116,4 | −2,9 | 120,7 | 129,0 | +8,3 |

- **Vorher, implizit:** Kein Subagent. Der Hauptthread liest `net-diagnose` und `net-reference` direkt.
- **Nachher, implizit:**
  - Der Hauptthread wählt `source-command-bertram` von selbst und startet einen Subagenten.
  - Der Subagent liest `agents/bertram.md` und die beiden Skills.
  - Danach sucht der Hauptthread noch selbst im Web.
- **Vorher, explizit:** Der Subagent liest nur die Skills, nicht `agents/bertram.md`.
- **Nachher, explizit:** Der Subagent liest `agents/bertram.md` und die Skills.
- **Qualität:** Alle vier Antworten sind laut Messagent fachlich gleichwertig solide. Vorher/implizit ist am ausführlichsten, nachher/implizit am knappsten.

#### christian

Claude Code, Läufe `dyn-christian-claude-before` und `-after` (parallel gestartet):

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| main_first | 32.817 | 25.090 | −7.727 (−23,5 %) |
| main_sum (n) | 75.726 (2) | 57.542 (2) | −18.184 |
| sub_first | 44.379 | 14.250 | −30.129 (−67,9 %) |
| sub_peak | 78.600 | 58.645 | −19.955 (−25,4 %) |
| sub_sum (n) | 663.590 (11) | 400.978 (10) | −262.612 (−39,6 %) |
| Helfer WebFetch (n / Summe) | 7 / 64.288 | 5 / 25.975 | −38.313 |
| Klassifikator (n / Summe) | 12 / 581.988 | 11 / 518.678 | −63.310 |
| Output Haupt + Persona + Helfer | 32.577 | 21.059 | −11.518 |
| alle Requests (n / Summe) | 32 / 1.385.592 | 28 / 1.003.173 | −382.419 |
| cost_usd | 2,2374 | 1,4034 | −0,8340 (−37,3 %) |
| duration_s | 402,6 | 272,3 | −130,3 |
| vorgeladene Skills | 6 (etwa 59,4k Zeichen) | 0 | |
| gelesene Dateien | 0 | vpn-reference, vpn-tunnel, wan-link, router-appliance | +4 |
| Spawn-Prompt | 1.548 Zeichen, `model: opus` explizit | 375 Zeichen, ohne model | |

- **Qualität vorher:** gelöst und belegt (wg(8), wg-quick(8), nftables-Wiki, Debian-Wiki, Kernel-Doku). Wie es der Spawn-Prompt erlaubte, legte die Persona 5 Artefakt-Dateien im Mess-cwd ab.
- **Qualität nachher:** gelöst, mit einer Schwäche. Das MSS-Clamping steht nach `ct state established,related accept`, dadurch wird das SYN/ACK der Gegenrichtung nicht geklemmt. Die Persona hat das nicht als unbelegt markiert.

Codex:

| Metrik | vorher impl. | nachher impl. | Δ impl. | vorher expl. | nachher expl. | Δ expl. |
|---|---:|---:|---:|---:|---:|---:|
| Haupt first | 20.183 | 16.721 | −3.462 | 21.336 | 17.957 | −3.379 |
| Haupt peak | 49.710 | 19.725 | −29.985 | 22.962 | 19.566 | −3.396 |
| Haupt sum (n) | 142.491 (4) | 91.015 (5) | −51.476 | 65.896 (3) | 55.765 (3) | −10.131 |
| Sub first | – | 19.049 | n/a | 27.195 | 20.025 | −7.170 |
| Sub peak | – | 68.764 | n/a | 63.299 | 70.381 | +7.082 |
| Sub sum (n) | – | 301.147 (7) | n/a | 267.970 (6) | 309.221 (7) | +41.251 |
| gesamt sum | 142.491 | 392.162 | +249.671 (+175,2 %) | 333.866 | 364.986 | +31.120 (+9,3 %) |
| gesamt ungecacht | 39.707 | 72.546 | +32.839 | 58.538 | 66.106 | +7.568 |
| gesamt Output (reasoning) | 3.710 (1.765) | 6.945 (3.537) | +3.235 | 6.347 (3.054) | 6.399 (2.897) | +52 |
| gesamt n | 4 | 12 | +8 | 9 | 10 | +1 |
| injizierter Command-Skill | – | – | | 2.050 Zeichen | 3.617 Zeichen | +1.567 |
| gelesene Plugin-Dateien (verschiedene) | 4 | 6 | +2 | 4 | 5 | +1 |
| duration_s | 78,9 | 151,6 | +72,7 | 134,6 | 138,2 | +3,6 |

- **Vorher, implizit:** Kein Subagent. Der Hauptthread liest wan-link, vpn-tunnel, router-appliance und vpn-reference direkt.
- **Nachher, implizit:**
  - Der Hauptthread wählt `source-command-christian`, prüft `agents/christian.md` und startet einen Subagenten.
  - Der Subagent liest `agents/christian.md` und dieselben 4 Skills.
- **Vorher, explizit:** Der Subagent liest die 4 Skills (zwei davon doppelt), `agents/christian.md` nicht.
- **Nachher, explizit:** Der Subagent liest `agents/christian.md` und die 4 Skills.
- **Hauptthread mit Subagent:** In allen Läufen mit Subagent schreibt der Hauptthread dessen Antwort neu. Das kostet etwa 1,4–2,2k Output-Tokens und 20–25 s.
- **Nicht gelesen:** bsd-firewall und openvpn hat kein Lauf gelesen.
- **Qualität:** Alle vier Antworten sind korrekt und gleichwertig.

#### bruce (it-grundschutz)

Claude Code, Läufe `bruce-dyn-before` und `bruce-dyn-after`:

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| main_first | 32.579 | 24.997 | −7.582 (−23,3 %) |
| main_sum (n) | 68.776 (2) | 53.063 (2) | −15.713 |
| sub_first | 35.393 | 12.962 | −22.431 (−63,4 %) |
| sub_peak | 47.769 | 28.299 | −19.470 (−40,8 %) |
| sub_sum (n) | 329.306 (8) | 205.461 (10) | −123.845 (−37,6 %) |
| Helfer | 0 | 0 | 0 |
| Klassifikator (n / Summe / Output) | 9 / 420.361 / 81 | 8 / 368.919 / 1.356 | −51.442 |
| Output Haupt + Persona | 6.943 | 6.348 | −595 |
| cost_usd | 0,9912 | 0,5896 | −0,4016 (−40,5 %) |
| duration_s | 104,9 | 116,1 | +11,1 |
| vorgeladene Skills | 8 (45.408 Zeichen) | 0 | |
| gelesene Dateien | 0 | gs-lookup | +1 |
| Spawn-Prompt | 751 Zeichen, eigener Rahmen | User-Text wörtlich | |

- **Confounder nachher:**
  - Der Klassifikator lehnte `nix run "path:…#gs" -- status` als „Code from External“ ab.
  - Bruce las die Katalogdateien danach direkt per Read.
  - Vorher lief `nix develop "path:$PWD" --command python3 scripts/gs.py …` durch.
- **Qualität:** Beide Läufe sind gelöst und inhaltlich deckungsgleich.
  - Nachher ist mit Datei und Zeilenbereich belegt, der Parameter ist von Hand korrekt aufgelöst.
  - Die Gegenprobe gegen Edition 2023 fehlt nachher; der Spawn-Prompt verlangte sie diesmal nicht.

Codex (Guardian = `auto_review`-Thread, in „gesamt“ enthalten):

| Metrik | vorher impl. | nachher impl. | Δ impl. | vorher expl. | nachher expl. | Δ expl. |
|---|---:|---:|---:|---:|---:|---:|
| Haupt first | 20.711 | 16.898 | −3.813 | 21.221 | 17.906 | −3.315 |
| Haupt peak | 29.652 | 18.778 | −10.874 | 22.280 | 19.151 | −3.129 |
| Haupt sum (n) | 197.682 (8) | 90.315 (5) | −107.367 | 64.943 (3) | 73.720 (4) | +8.777 |
| Sub first | – | 18.909 | n/a | 27.041 | 19.918 | −7.123 |
| Sub peak | – | 26.175 | n/a | 40.203 | 26.803 | −13.400 |
| Sub sum (n) | – | 118.238 (5) | n/a | 407.517 (12) | 170.360 (7) | −237.157 |
| Guardian sum (n) | 11.784 (1) | 22.458 (2) | +10.674 | 39.184 (3) | 22.619 (2) | −16.565 |
| gesamt sum | 209.466 | 231.011 | +21.545 (+10,3 %) | 511.644 | 266.699 | −244.945 (−47,9 %) |
| gesamt ungecacht | 26.810 | 28.771 | +1.961 | 70.172 | 30.155 | −40.017 |
| gesamt Output (reasoning) | 1.807 (537) | 2.750 (888) | +943 | 4.254 (1.269) | 3.092 (823) | −1.162 |
| gesamt n | 9 | 12 | +3 | 18 | 13 | −5 |
| gelesene Plugin-Dateien | 1 | 4 (Lesevorgänge) | +3 | 2 | 2 | 0 |
| Shell-Aufrufe / eskaliert | 7 / 1 | 7 / 2 | | 11 / 3 | 5 / 2 | |
| duration_s | 50,8 | 69,3 | +18,5 | 103,0 | 73,0 | −30,0 |

- **Vorher, implizit:**
  - Kein Subagent. Der Hauptthread liest `gs-lookup` und probiert dann `nix run .#gs` mehrfach.
  - Erfolg erst mit `path:.#gs` plus Eskalation.
- **Nachher, implizit:**
  - Der Hauptthread wählt `source-command-bruce` und startet einen Subagenten.
  - Der Subagent liest `agents/bruce.md` und `gs-lookup` und ruft gs sofort über den absoluten `path:`-Pfad auf.
- **Vorher, explizit:** Der Hauptthread startet einen generischen Subagenten. Der liest `gs-lookup`, `README.md` und `agents/bruce.md` und prüft die Korpus-JSONs direkt.
- **Nachher, explizit:** Der Subagent liest nur `agents/bruce.md` und `gs-lookup`, ohne Fehlversuch.
- **Qualität:**
  - Alle vier Antworten stimmen inhaltlich; der Messagent hat sie gegen `catalog.json` gegengelesen.
  - Bei vorher/implizit und nachher/implizit fehlt die guidance.
  - Nachher/explizit gibt die guidance wörtlich wieder.

#### nixie

Claude Code, Läufe `nixie-dyn-before` und `nixie-dyn-after`:

| Metrik | vorher | nachher | Δ |
|---|---:|---:|---:|
| main_first | 32.525 | 25.039 | −7.486 (−23,0 %) |
| main_sum (n) | 68.963 (2) | 53.451 (2) | −15.512 |
| sub_first | 26.916 | 12.597 | −14.319 (−53,2 %) |
| sub_peak | 42.350 | 54.766 | +12.416 (+29,3 %) |
| sub_sum (n) | 279.655 (8) | 314.417 (9) | +34.762 (+12,4 %) |
| Helfer Haiku (n / Summe) | 4 / 57.491 | 0 / 0 | −57.491 |
| sub_sum inkl. Helfer | 337.146 | 314.417 | −22.729 (−6,7 %) |
| Klassifikator (n / Summe / Output) | 8 / 377.242 / 72 | 9 / 418.858 / 2.203 | +41.616 |
| Output Haupt + Persona + Helfer | 13.037 | 7.780 | −5.257 |
| cost_usd | 1,1110 | 0,8355 | −0,2755 (−24,8 %) |
| duration_s | 135,1 | 129,0 | −6,1 |
| vorgeladene Skills | 4 (30.306 Zeichen) | 0 | |
| gelesene Dateien | 0 | nix-packaging, nix-docs, nix-deploy | +3 |
| Spawn-Prompt | User-Text plus Block „Rahmen“ mit 6 Punkten | User-Text wörtlich | |

- **Qualität vorher:**
  - Gelöst: `buildGoModule (finalAttrs: …)`, belegt per WebFetch.
  - Schwächen: `meta = with lib;` (von Nixie selbst als unbelegt markiert) und ungedrosselte Vorschläge für `nix-build` und `nix flake check`.
- **Qualität nachher:**
  - Gelöst: `tag`, `subPackages`, `versionCheckHook`, `meta` ohne `with lib`, belegt aus der gelockten nixpkgs-Revision im Store.
  - Den gedrosselten `nix flake check` formuliert Nixie erst nach dem Lesen von nix-deploy.
  - Die Endantwort nennt keine Quellen-URLs. `nixos-config` wurde nicht gelesen, obwohl Nixie eine Einbindung ins Repo vorschlägt.

Codex:

| Metrik | vorher impl. | nachher impl. | Δ impl. | vorher expl. | nachher expl. | Δ expl. |
|---|---:|---:|---:|---:|---:|---:|
| Haupt first | 20.744 | 16.931 | −3.813 | 21.182 | 17.925 | −3.257 |
| Haupt peak | 21.888 | 18.726 | −3.162 | 21.646 | 18.523 | −3.123 |
| Haupt sum (n) | 42.632 (2) | 72.023 (4) | +29.391 | 64.144 (3) | 54.637 (3) | −9.507 |
| Sub first | – | 17.158 (fork none) | n/a | 26.914 | 19.973 | −6.941 |
| Sub peak | – | 32.154 | n/a | 28.036 | 25.567 | −2.469 |
| Sub sum (n) | – | 116.107 (5) | n/a | 54.950 (2) | 92.233 (4) | +37.283 |
| gesamt sum | 42.632 | 188.130 | +145.498 (+341,3 %) | 119.094 | 146.870 | +27.776 (+23,3 %) |
| gesamt ungecacht | 20.360 | 36.706 | +16.346 | 21.174 | 19.510 | −1.664 |
| gesamt Output (reasoning) | 989 (579) | 2.907 (1.087) | +1.918 | 1.236 (437) | 2.662 (1.409) | +1.426 |
| gesamt n | 2 | 9 | +7 | 5 | 7 | +2 |
| injizierter Command-Skill | – | – | | 1.530 Zeichen | 3.585 Zeichen | +2.055 |
| gelesene Plugin-Dateien | 1 | 5 (Lesevorgänge) | +4 | 1 | 3 | +2 |
| duration_s | 22,4 | 70,4 | +48,0 | 34,1 | 58,8 | +24,7 |

- **Vorher, implizit:** Kein Subagent. Der Hauptthread wählt `nix-packaging` selbst und liest ihn.
- **Nachher, implizit:**
  - Der Hauptthread wählt `source-command-nixie` über die neue Beschreibung „Proaktiv nutzen …“.
  - Er startet einen frischen Subagenten (`fork_turns` none).
  - Der Subagent liest `agents/nixie.md`, nix-packaging und nix-docs, führt den Nixie-STARTUP aus und sucht einmal im Web.
- **Vorher, explizit:** Der Subagent liest nur nix-packaging, `agents/nixie.md` nie.
- **Nachher, explizit:** Der Subagent liest `agents/nixie.md`, nix-packaging und nix-docs.
- **Qualität:** Alle vier Entwürfe sind praktisch gleichwertig. Die geladene Persona brachte laut Messagent keinen erkennbaren inhaltlichen Mehrwert.

## Beobachtungen

### Wirkung des Umbaus

1. **Erster Request der Hauptsitzung (Claude):**
   - Baseline: −8.357 bis −8.360 Tokens, das sind −19,1 % mit Sonnet und −26,3 % mit dem Opus-Default.
   - Dynamische Läufe: −7.486 bis −7.727 Tokens (−23,0 % bis −23,5 %).
   - Tool-Array und System-Blöcke sind in beiden Zuständen byte-gleich. Es ändern sich nur die Messages:
     - Die System-Message mit Skill- und Agentenliste schrumpft von 34.561–34.950 auf 18.790–18.969 Zeichen.
     - Der expandierte Persona-Command wächst: bertram 1.557 → 2.813, christian 1.741 → 3.009, bruce 1.398 → 2.907 Zeichen.
2. **`/context` taugt für diesen Vergleich nicht:**
   - Die Summe zeigt −1,2k, während der erste Request um 7,5k bis 8,4k Tokens kleiner wird.
   - Die Zeile „System tools“ steigt um 4,5k, weil `/context` die Skill-Schätzung von einem konstanten `count_tokens`-Wert (9.545) abzieht.
3. **Erster Persona-Request (Claude):**
   - Baseline −46,2 % bis −67,6 %, dynamisch −46,8 % bis −67,9 %.
   - Vorher waren 4 bis 8 Skill-Texte vorgeladen, nachher keiner. Der Persona-Systemprompt wächst dabei (bertram 8.230 → 10.251, christian 10.786 → 14.157 Zeichen).
4. **Gelesene Skills (Claude):**
   - Nachher lesen die Personas nur einen Teil ihrer Skills: bertram 2 von 5, christian 4 von 6, bruce 1 von 8, nixie 3 von 4.
   - Vorher gab es in keinem Claude-Lauf einen Read auf Plugin-Dateien.
5. **Summen und Kosten (Claude):**
   - `sub_sum` sinkt bei bertram, christian und bruce (−37,6 % bis −60,7 %) und steigt bei nixie (+12,4 %, `sub_peak` +29,3 %). Mit Helfern gerechnet sinkt sie auch bei nixie (−6,7 %).
   - `cost_usd` sinkt in allen vier Läufen (−24,8 % bis −51,5 %).
   - Die Recherchewege unterscheiden sich zwischen den Läufen (bertram: 15 gegen 7 Tool-Aufrufe der Persona; bruce: Klassifikator-Block). Summen und Kosten lassen sich deshalb bei n=1 nicht allein dem Umbau zuschreiben.
6. **Spawn-Prompts (Claude):**
   - Vorher hat die Hauptsitzung dem User-Text einen eigenen Rahmen mitgegeben (bertram 697, bruce 751, christian 1.548 Zeichen, nixie 6 Punkte).
   - Nachher gibt sie nur den User-Text weiter, bei bertram und christian mit einer kurzen Einschränkung (225 bzw. 375 Zeichen).
7. **Codex-Startprompt:**
   - Er schrumpft um 3.813 Tokens (−41,7 %), die komplette Differenz liegt in `<skills_instructions>`.
   - Katalogeinträge der Plugins: 32 → 9.
   - In den impliziten Läufen sinkt der erste API-Request bei bruce und nixie um genau 3.813 Tokens, das entspricht der tiktoken-Zählung. Bei bertram sind es −3.820, bei christian −3.462.
8. **Codex explizit:** Der erste Request sinkt um 3.257 bis 3.411 Tokens. Der injizierte Command-Skill wächst zugleich von 1.530–2.050 auf 3.385–3.617 Zeichen. `sub_first` sinkt bei allen vier Personas um 6.941 bis 7.170 Tokens.
9. **Codex implizit, Verhaltenswechsel:**
   - Vorher startete keiner der vier Läufe einen Subagenten, der Hauptthread las die sichtbaren Fach-Skills direkt.
   - Nachher wählte der Hauptthread in allen vier Läufen `source-command-<name>` und startete einen Subagenten.
   - Folge für den Hauptthread: `peak` sinkt überall (−3.162 bis −48.169).
   - Folge für die Summe über alle Threads: bertram −22,7 %, bruce +10,3 %, christian +175,2 %, nixie +341,3 %.
10. **Codex explizit, Gesamtsumme:** bertram −28,4 %, bruce −47,9 %, christian +9,3 %, nixie +23,3 %.
11. **Persona-Definition in Codex:**
    - Vorher gab es nur in der expliziten Variante einen Subagenten. Er las `agents/<name>.md` nur bei bruce; bei bertram, christian und nixie arbeitete er ohne Rollenanweisung.
    - Nachher lasen alle acht Subagenten `agents/<name>.md`.
12. **Qualität:** Laut den Messagenten haben alle 24 Läufe die Aufgabe gelöst (8 Claude, 16 Codex). Inhaltliche Abweichungen:
    - christian/Claude nachher: MSS-Clamping-Reihenfolge,
    - nixie/Claude nachher: keine Quellen-URLs, nixos-config nicht gelesen,
    - bruce/Codex implizit in beiden Zuständen: guidance fehlt.

    Eine belastbare Qualitätsdifferenz lässt sich bei n=1 nicht angeben.

### Auffälligkeiten und Messprobleme

1. **Einzelläufe und Parallelität:**
   - Alle 16 Codex-Läufe starteten laut `session_meta` zwischen 22:38:39 und 22:39:05 und liefen parallel zueinander.
   - Die beiden christian-Läufe in Claude liefen parallel.
   - `duration_s` und `cost_usd` (cache-abhängig) sind darum nur grob vergleichbar. Tokensummen hängen nicht vom Cache ab.
2. **Uneinheitliche Proxy-Methoden (Claude):**
   - Statische Messung, christian und bruce: `ANTHROPIC_BASE_URL` plus `ENABLE_TOOL_SEARCH=true`. `/context` zeigt dort System prompt 1,9k statt 2,1k, die Zeile „Autocompact buffer“ fehlt.
   - nixie: `ANTHROPIC_BASE_URL` plus `_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL=1`, ein interner Schalter aus dem Binary; `/context` 16,4k statt 16,6k.
   - bertram: `HTTPS_PROXY` mit TLS-MITM nur für api.anthropic.com. `/context` war dort identisch mit dem direkten Lauf.
   - Ohne Tool-Search-Schalter zeigt `/context` mit Base-URL 39,7k bis 40,9k.
   - Mit `--model sonnet` stehen über den Proxy die Plugin-Skills nur als Namen im Listing (main_first 35.479 → 34.030). Deshalb stammt `main_first` der Baseline aus Läufen ohne Proxy.
   - Alle Abweichungen treffen beide Zustände gleich.
3. **bertram/Claude nachher:**
   - Lauf 1 brach nach 35,9 s ab: Der Watchdog hielt den sed-Ausdruck `s/<[^>]*>//g` für eine Umleitung.
   - Gewertet ist Lauf 2 mit einer privaten Watchdog-Kopie, die Umleitungen nur außerhalb von Quotes erkennt. Das weicht von „genau ein Lauf“ ab.
   - Lauf 1 hatte bis zum Abbruch dasselbe `main_first` und `sub_first` 12.163 statt 12.159.
4. **bruce/Claude:**
   - Nachher lehnte der Klassifikator `nix run` ab. Bruce las die Katalogdateien stattdessen per Read (4 Reads). Der Nachher-Lauf ist darum nur eingeschränkt mit dem Vorher-Lauf vergleichbar.
   - In beiden Zuständen lief ein zusätzlicher PreToolUse-Hook, der Korpus-Ingest, `gs cache --out`, `curl`/`wget -o` außerhalb `/tmp` und `nix flake update/lock` blockt.
5. **Kostenbasis widersprüchlich:**
   - Die dynamischen Messagenten fanden den Sonnet-Klassifikator nicht in `modelUsage` und `total_cost_usd`; er macht 280k bis 582k Tokens je Lauf aus.
   - Der Bericht zur Baseline (Hauptsitzung Sonnet) nennt die Kosten dagegen „inklusive Titel- und Klassifikator-Requests“. Nicht aufgelöst.
6. **Vereinheitlichte Definitionen:**
   - bertram und christian hatten `output_sum` inklusive Klassifikator berichtet (20.663/11.548 bzw. 32.685/21.158); die Tabellen oben rechnen ohne Klassifikator.
   - Der bertram-Bericht nannte „15 gegen 8 Tool-Aufrufe“. Laut stream-json sind es 15 gegen 7 ohne bzw. 16 gegen 8 mit `SubagentHandback`.
7. **Codex-Watchdog ohne Blick auf Subagenten:**
   - `codex exec --json` streamt nur Items des Hauptthreads, ohne `spawn_agent` und ohne die Befehle der Subagenten.
   - Nachträglich wurden alle Shell-Befehle aus den Rollouts geprüft, ohne Treffer: bertram 10, christian 15, bruce 30, nixie 10.
   - Vorbeugend wirkt in Codex nur die Sandbox.
8. **Eskalationen bei bruce/Codex:**
   - `nix run` scheitert in `workspace-write` am Daemon-Socket.
   - Alle 8 Eskalationen hat der Auto-Reviewer genehmigt, diese Befehle liefen ohne Sandbox.
   - `~/.cache/nix` (eval-cache, fetcher-cache) trägt mtimes von 22:39–22:40. Einzelnen Läufen zuordnen lässt sich das nicht, weil parallel andere Agenten Nix aufriefen.
9. **Codex-Modell ohne `-m`:**
   - Laut `turn_context` liefen alle dynamischen Codex-Threads auch ohne `-m` mit gpt-5.6-sol/high aus der `config.toml`.
   - Die Setup-Notiz und die Projekt-`CLAUDE.md` beschreiben für `exec` das Gegenteil. Das gehört nicht zum Messziel, ist aber belegt.
10. **Codex-Homes nicht mehr im Setup-Zustand:**
    - Ab 22:38:39 entstanden dort `*.sqlite` (goals, logs, memories, queue, state, thread_history) und `tmp/arg0/*`.
    - 22:38:39 ist laut `session_meta` der Start der vier christian-Läufe. Ob die Dateien von diesen Läufen stammen, ist nicht geprüft.
    - Beim Start der bruce-Läufe meldete Codex `rate_limits.primary.used_percent = 84.0` (Wochenfenster).
11. **Codex und die Vendor-Skills:** Codex installiert die Vendor-Symlinks von bibliothekarin nicht. In beiden Zuständen und im User-Cache stehen nur 3 der 8 Skills bereit (diagramm-auswahl, mermaid, plantuml). Claude lädt alle 8.
12. **Codex kürzt Skill-Beschreibungen auf 1.024 Zeichen:** Das betraf vorher `christian:bsd-firewall` (Quelle 1.045 Zeichen).
13. **Schreibverhalten der Personas (Claude):**
    - Vorher legten bertram und nixie Downloads per `curl -o` an festen Pfaden unter `/tmp` ab; die Dateien sind gelöscht. christian schrieb 5 Artefakte ins Mess-cwd, was der Spawn-Prompt erlaubte.
    - Nachher streamte bertram nur.
    - nixie führte nachher `nix eval --impure` mit `builtins.getFlake "git+file:///home/muhackel/nixosconfig"` aus. Das ist eine Auswertung, kein Build; ob dabei eine Store-Kopie entstand, ist nicht geprüft. Außerdem las nixie `/etc/nixos/CLAUDE.md`.
14. **Dateien trotz `--no-session-persistence`:** Mit Agent-Spawn legt Claude trotzdem `~/.claude/projects/-tmp-…/<session>/subagents/agent-*.meta.json` an. Alle sind gelöscht.
15. **known_marketplaces.json:** mtime 22:47:07 während paralleler Läufe, keinem Lauf zuzuordnen.
16. **Tools des nixie-Subagenten:** Bash, Read, Write, Edit, WebFetch, WebSearch, SubagentHandback. Glob und Grep aus dem Frontmatter fehlen.
17. **`sub_first` hängt leicht vom Modell der Hauptsitzung ab:** Mit dem Opus-Default sind es 115–117 Tokens weniger als mit Sonnet. Der Body unterscheidet sich nur in cwd und `max_tokens` (64000 bzw. 128000); die Ursache ist nicht belegt.
18. **Leseberechtigung in `-p` mit Modus auto:** Reads außerhalb des cwd (`/etc/hostname`) werden abgelehnt, Reads im Plugin-Root nicht.

## Wiederholen der Messung

Die Hilfsskripte der Messreihe (`run-claude.sh`, `run-codex.sh`, `watchdog.py`, `test-watchdog.sh`, `strip-codex-config.py`, die Claude-Settings-JSONs, `py`) liegen unter [`docs/messung-lazy-skills-2026-09-18/`](./messung-lazy-skills-2026-09-18/README.md) (README dort: Zweck, Voraussetzungen, Umgebungsvariablen `LAZY_MESS`/`LAZY_CWD`). Proxy- und Auswerteskripte lagen nur unter `/tmp/lazy-mess` und sind nicht im Repo. Der Watchdog ist eine Schutzschicht und ändert die Messwerte nicht (0 Tokens laut `/context`).

1. Quellbäume erzeugen (Submodul auf c4728b3):

   ```bash
   set -euo pipefail
   REPO=${REPO:?Pfad zu einem Checkout von claude-code-plugins mit initialisiertem Submodul}
   B=/tmp/lazy-mess
   git -C "$REPO" submodule status vendors/obsidian-skills   # muss c4728b3 zeigen
   for spec in before:f22c0dc after:71871af; do
     z=${spec%%:*}; rev=${spec#*:}
     mkdir -p "$B/$z/vendors/obsidian-skills"
     git -C "$REPO" archive "$rev" | tar -x -C "$B/$z"
     cp -a "$REPO"/vendors/obsidian-skills/{.claude-plugin,LICENSE,README.md,skills} "$B/$z/vendors/obsidian-skills/"
   done
   find "$B"/before/plugins "$B"/after/plugins -xtype l   # muss leer sein
   ```

2. Claude-Overlay: `run-claude.sh` liest `claude-settings-guard.json` automatisch aus seinem eigenen Verzeichnis (Plugins deaktiviert, PreToolUse-Hook auf `watchdog.py hook`), keine manuelle Datei mehr nötig. Die reine `claude-settings.json` (ohne Hook) liegt daneben, falls ein Lauf ohne Watchdog gebraucht wird.

3. Claude-Aufruf je Zustand über `run-claude.sh` (Watchdog inklusive, prüft Nicht-inline-Plugins schon selbst). Die Variablen einer aufrufenden Claude-Sitzung entfernen, sonst gilt deren Effort:

   ```bash
   claude_run() {  # claude_run <before|after> <run-id> <prompt> [weitere claude-Argumente]
     local z=$1 run_id=$2 prompt=$3; shift 3
     env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT -u CLAUDE_EFFORT -u CLAUDE_CODE_CHILD_SESSION \
       LAZY_MESS=/tmp/lazy-mess docs/messung-lazy-skills-2026-09-18/run-claude.sh "$z" "$run_id" "$prompt" "$@"
   }
   ```

   Weitere Variablen der Elternsitzung (Session-IDs, `CLAUDE_CODE_MESSAGING_*`) ebenfalls entfernen.

   Das Log liegt danach unter `/tmp/lazy-mess/logs/runs/<run-id>.jsonl`. Beide MCP-Server müssen `connected` sein:

   ```bash
   jq -r 'select(.type=="system" and .subtype=="init") | .mcp_servers[] | "\(.name) \(.status)"' /tmp/lazy-mess/logs/runs/<run-id>.jsonl
   ```

4. `/context` (Abschnitt 1): `LAZY_CWD=$(mktemp -d -p /tmp/lazy-mess)` je Zustand setzen, dann `claude_run <z> context-<z> "/context"`; die JSONL liegt danach unter `/tmp/lazy-mess/logs/runs/context-<z>.jsonl`. Die Tabelle steht im `result`-Event. Nur Läufe werten, in denen beide MCP-Server verbunden waren.

5. Persona-Baseline (Abschnitt 3):
   - Hauptsitzung mit `--model sonnet`. Sie soll den Agenten `bertram:bertram`, `christian:christian`, `it-grundschutz:bruce` bzw. `nixie:nixie` mit dem Auftrag „Antworte nur mit OK.“ starten. Laut Log war der Spawn-Prompt wörtlich „Antworte nur mit OK.“; der Wortlaut des Hauptprompts ist nicht protokolliert.
   - `main_first`: Lauf ohne Proxy, usage der ersten Hauptsitzungs-Antwort im stream-json (input + cache_creation + cache_read).
   - `sub_*`: Lauf mit Proxy, der je Request die usage mitschreibt. Subagent-Requests erkennt man an `cc_is_subagent=true` im ersten System-Block (Billing-Header) plus Persona-Text im Systemprompt.
   - Nur die Proxy-Variante `HTTPS_PROXY=http://127.0.0.1:<port>` mit TLS-MITM für api.anthropic.com (CA per `NODE_EXTRA_CA_CERTS`) gab `/context` identisch zum direkten Lauf wieder. Eine Variante für alle Läufe festlegen.
   - Mit `ANTHROPIC_BASE_URL` zusätzlich `ENABLE_TOOL_SEARCH=true` setzen, sonst lädt Claude MCP- und System-Tools vorab.

6. Dynamische Claude-Läufe (Abschnitt 4):
   - Je Persona und Zustand ein Lauf in einem frischen `mktemp -d -p /tmp/lazy-mess`, ohne `--model`.
   - Prompt ist Persona-Command plus User-Text aus der Tabelle „Arbeitsaufträge“, zum Beispiel `claude_run after bruce-after "/bruce Schlag die Anforderung GC.1.1 zitierfähig nach. Nur lesen, nichts ändern."`.
   - Die Form `/bruce …` ist aus dem bruce-Lauf belegt. Bei bertram, christian und nixie belegt der expandierte Command-Text im ersten Request den Command-Aufruf, die Schreibweise ist nicht protokolliert. Command-Namen laut init-Event: `bertram:bertram`, `christian:christian`, `it-grundschutz:bruce`, `nixie:nixie`.
   - Zustände nacheinander starten, nicht parallel.
   - Nach dem Lauf die angelegten `~/.claude/projects/-tmp-lazy-mess-*` löschen.

7. Codex-Homes aufbauen. Die Befehle sind aus der CLI-Hilfe von codex-cli 0.154.0 und den Install-Logs der Messreihe rekonstruiert; `strip-codex-config.py` liefert byte-gleich die damals verwendete `config.toml`:

   ```bash
   for z in before after; do
     H=/tmp/lazy-mess/codex-$z
     mkdir -p "$H"
     python3 docs/messung-lazy-skills-2026-09-18/strip-codex-config.py ~/.codex/config.toml "$H/config.toml"
     ln -s ~/.codex/AGENTS.md "$H/AGENTS.md"
     ln -s ~/.codex/auth.json "$H/auth.json"
     CODEX_HOME=$H codex plugin marketplace add "/tmp/lazy-mess/$z" --json
     for p in bibliothekarin nixie it-grundschutz bertram christian tools; do
       CODEX_HOME=$H codex plugin add "$p@muhackel-plugins" --json
     done
   done
   ```

8. Codex-Startprompt (Abschnitt 2):

   ```bash
   CODEX_HOME=/tmp/lazy-mess/codex-before codex -C "$(mktemp -d -p /tmp/lazy-mess)" -s read-only -m gpt-5.6-sol \
     debug prompt-input "Hallo" > prompt-input-before.json
   ```

   Ausgewertet sind alle `content[].text` der 5 Messages. Gezählt wurden Zeichen und Tokens mit tiktoken 0.12.0 `o200k_base`, etwa per `nix shell nixpkgs#python3Packages.tiktoken`. Das Encoding lädt tiktoken beim ersten Aufruf nach, `TIKTOKEN_CACHE_DIR` setzen. Aufgeteilt ist nach dem Block `<skills_instructions>`, den Zeilen `- ` unter `### Available skills` und den Root-Zeilen `` - `rN` = ``.

9. Dynamische Codex-Läufe (Abschnitt 4), je Persona, Zustand und Variante ein Lauf über `run-codex.sh` (setzt Modell und Effort in beiden Zuständen gleich fest, siehe Bullet „Modell“):

   ```bash
   LAZY_MESS=/tmp/lazy-mess docs/messung-lazy-skills-2026-09-18/run-codex.sh before <run-id> "<Prompt>"
   ```

   - **Prompt:** Implizit ist er der User-Text. Explizit steht `$bertram:source-command-bertram`, `$christian:source-command-christian`, `$it-grundschutz:source-command-bruce` bzw. `$nixie:source-command-nixie` davor.
   - **Rollouts:** Die Tokens stehen nicht im Stream, sondern in den Rollouts unter `$CODEX_HOME/sessions/<Jahr>/<Monat>/<Tag>/` (`run-codex.sh` setzt `CODEX_HOME=/tmp/lazy-mess/codex-<before|after>`).
   - **Zuordnung:** Der Hauptthread hat `session_meta.cwd` gleich dem von `run-codex.sh` verwendeten `cwd` (Default `/tmp/lazy-mess/work`, per `LAZY_CWD` überschreibbar). Subagent und Guardian hängen über `parent_thread_id` daran.
   - **Werte:** je `token_usage_record` die `input_tokens` (inklusive cached) und den Output; der Stream (`/tmp/lazy-mess/logs/runs/<run-id>.jsonl`) zeigt in `turn.completed` nur den Hauptthread.
   - **Modell:** `run-codex.sh` setzt `-m gpt-5.6-sol -c 'model_reasoning_effort="high"'` fest, in beiden Zuständen gleich.
