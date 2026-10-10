# Messung: Rückbau des Lazy-Musters, Skills offen

- **Datum:** 2026-10-10
- **Branch:** `feature/rueckbau-skills`
- **Rohwerte:** [`messung-rueckbau-2026-10-10/messung-rueckbau-2026-10-10.csv`](messung-rueckbau-2026-10-10/messung-rueckbau-2026-10-10.csv), Formatbeschreibung in der ersten Zeile. Daneben `eval.sh` (Auswertung eines stream-json-Logs), `auftraege.txt` (die vier User-Texte) und die beiden `/context`-Ausgaben.

## Zweck

Vergleich des alten Lazy-Musters (`main` 1c580e4: Fach-Skills gesperrt, Agent liest SKILL.md per Read nach
Lesetabelle) mit dem Rückbau (Skills offen, Descriptions 150 bis 250 Zeichen, selektives Preload per
`skills:`, übrige Skills über das Skill-Tool, große Skills in Kern und `references/`, Agent-Bodies um ein
Drittel kürzer). Hintergrund in der Analyse vom 2026-10-10 im Vault
(`KI-Entwicklung/claude-code-plugins-persona-agenten-tokensparend`).

Die Werte sind nicht mit `docs/messung-lazy-skills-2026-09-18.md` vergleichbar: Claude Code 2.1.296 statt
2.1.272, anderes Default-Modell (claude-opus-5-5), kein Proxy. Darum wurde der Lazy-Stand am selben Tag
neu gemessen. **Alle dynamischen Werte sind Einzelläufe (n=1).**

## Messaufbau

- Skripte der alten Reihe (`docs/messung-lazy-skills-2026-09-18/run-claude.sh` mit Watchdog), Zustände
  `before` = Lazy (Export von `main` plus Submodul), `after` = Arbeitsbaum des Branches, jeweils unter
  `/tmp/lazy-mess-2026-10-10/`. Plugins per `--plugin-dir`, installierte Marketplace-Versionen per
  `--settings` abgeschaltet.
- `sub_*` kommt ohne Proxy aus dem stream-json: Assistant-Nachrichten mit `parent_tool_use_id` sind die
  Requests des Subagenten, Tokens je Request wie bisher `input + cache_creation + cache_read`.
- Baseline: Hauptsitzung `--model sonnet`, Auftrag „Spawne den Subagenten X mit genau dem Auftrag
  ‚Antworte nur mit OK.‘“. Dynamisch: Persona-Command plus Arbeitsauftrag (Texte wie in der alten Reihe),
  Default-Modell der Hauptsitzung.
- Codex wurde nicht gemessen.

## Ergebnisse

### Hauptkontext (`/context`)

| Kategorie | Lazy | Neu |
|---|---:|---:|
| Custom agents | 1,4k | 1,1k |
| Skills (Listing) | 4,8k | 7,0k |
| Agent-Einträge je Persona | 259 bis 266 | 195 bis 210 |
| Skill-Einträge der Personas | 0 | 28 à 80 bis 90 |
| `main_first` Baseline | 24,0k | 27,3k |

Der Rückbau kostet im Hauptkontext rund 3,3k Tokens je Request (28 Skill-Einträge minus kürzere
Agent-Descriptions). Die `/context`-Summe (16,5k gegen 16,2k) täuscht, weil die Anzeige die
Skill-Schätzung von den System-Tools abzieht (Rechenfehler aus der alten Reihe, dort Beobachtung 2).

### Baseline je Persona (`sub_first`, erster Request des Subagenten)

| Persona | Lazy | Neu | Δ |
|---|---:|---:|---:|
| nixie | 13.221 | 23.848 | +10,6k |
| bertram | 12.763 | 22.012 | +9,2k |
| christian | 14.822 | 27.545 | +12,7k |
| bruce | 13.732 | 22.604 | +8,9k |
| bibliothekarin | 13.934 | 21.574 | +7,6k |
| bibliothekarin-search | 7.745 | 17.859 mit Skill-Tool und Preload, **7.752** ohne | 0 |

Der Sprung besteht aus drei Teilen: das Skill-Tool bringt das vollständige Skill-Listing in den
Subagenten (mit Built-ins rund 8k Tokens), dazu die Preload-Bodies (nixie 7,5k Zeichen, christian 13k),
abzüglich der kürzeren Agent-Bodies (3 bis 6k Zeichen weniger). Der Search-Agent zeigt das Skill-Tool
isoliert: ohne Skill-Tool und ohne Preload bleibt er bei 7,8k. Darum bekommt er beides nicht.

### Arbeitsauftrag je Persona

| Persona | Metrik | Lazy | Neu |
|---|---|---:|---:|
| bertram | `sub_first` / `sub_sum` / `sub_n` | 12,8k / 184k / 9 | 22,0k / 166k / 6 |
| | `sub_peak` / Kosten / Dauer | 25,9k / 0,51 $ / 114 s | 31,7k / 0,54 $ / 108 s |
| | geladen | Read net-diagnose, net-reference | Preload net-reference, Skill net-diagnose |
| christian | `sub_first` / `sub_sum` / `sub_n` | 14,8k / 386k / 12 | 27,6k / 498k / 12 |
| | `sub_peak` / Kosten / Dauer | 44,2k / 0,76 $ / 149 s | 48,2k / 0,70 $ / 138 s |
| | geladen | Read vpn-tunnel, wan-link, vpn-reference, router-appliance | Preload vpn-reference, vpn-tunnel; Skill wan-link, router-appliance |
| bruce | `sub_first` / `sub_sum` / `sub_n` | 13,6k / 142k / 8 | 22,5k / 99k / 4 |
| | `sub_peak` / Kosten / Dauer | 23,4k / 0,37 $ / 47 s | 27,1k / 0,36 $ / 40 s |
| | geladen | Read gs-lookup | Preload gs-lookup |
| nixie | `sub_first` / `sub_sum` / `sub_n` | 13,2k / 339k / 11 | 23,8k / 225k / 8 |
| | `sub_peak` / Kosten / Dauer | 50,2k / 0,56 $ / 71 s | 32,1k / 0,45 $ / 56 s |
| | geladen | Read nix-packaging, nix-docs, nix-deploy | Preload nix-docs, nixos-config; Skill nix-packaging |

`main_first` der Hauptsitzung in allen dynamischen Läufen: Lazy 25,2k, Neu 27,5 bis 27,6k. `main_sum`
85 bis 92k gegen 91 bis 98k bei je drei Requests.

## Beobachtungen

1. **Das Skill-Tool funktioniert im Subagenten.** Alle drei Personas mit On-Demand-Skills haben es benutzt
   (`Skill(bertram:net-diagnose)`, `Skill(christian:wan-link)`, `Skill(christian:router-appliance)`,
   `Skill(nixie:nix-packaging)`), kein Read auf Plugin-Dateien mehr.
2. **Teurerer Start, günstigerer Verlauf.** `sub_first` steigt um 8 bis 13k, `sub_sum` sinkt bei nixie
   (−34 %), bruce (−31 %) und bertram (−10 %), weil Requests wegfallen (ein Skill-Aufruf statt Read-Roundtrips,
   kein Abschluss-Check, kein Startup-Ritual ohne Bedarf). Kosten und Dauer sinken bei drei von vier
   Personas leicht.
3. **christian ist die Ausnahme:** `sub_sum` +29 %. Zwei Preloads (13k Zeichen) plus zwei nachgeladene
   Skills (wan-link 9,6k, router-appliance 9k Kern) bei gleicher Request-Zahl. nixie zeigt die Gegenrichtung:
   `nix-deploy` wurde dank Achsen-Kopplung nicht mehr geladen (Lazy las es wegen des Abschluss-Checks).
4. **Das Skill-Listing im Subagenten ist der Fixpreis des Musters.** Rund 8k Tokens je Spawn für das Tool
   samt Katalog, unabhängig davon, ob ein Skill gerufen wird. Wer das vermeiden will, braucht wieder
   Read-Pfade im Body (das alte Lazy-Muster) oder volles Preload ohne Skill-Tool. Für Agenten, die nie
   nachladen, Skill-Tool weglassen (so beim Search-Agenten).
5. **Hauptkontext:** +3,3k Tokens je Request der Hauptsitzung durch 28 Skill-Einträge. Das Lean-Profil
   (`profiles/lean.json`) nimmt sie samt Agenten weg.

## Nicht gemessen

- Streuung (n=1), Codex, Qualität der Antworten (nur Plausibilität der Ergebnisköpfe geprüft),
  Delegationsrate der Hauptsitzung mit den gekürzten Descriptions, Verhalten unter `--model sonnet` ohne
  `[1m]` (Skill-Listing-Budget 1 % des Kontexts).
