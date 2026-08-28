---
tags: [evaluierung, skills, fremdquelle]
description: Durchsicht der 37 Skills aus mattpocock/skills mit Bewertung, was direkt, angepasst oder gar nicht in die eigenen Workflows passt
---

# Evaluierung: mattpocock/skills

**Quelle:** <https://github.com/mattpocock/skills>
**Stand:** Commit `6654f6b` vom 2026-08-24, durchgesehen am 2026-08-28
**Umfang:** 37 Skills in 5 Buckets (`engineering/`, `productivity/`, `misc/`, `in-progress/`, `deprecated/`)

## Einordnung

Das Repo ist auf TypeScript-App-Entwicklung mit angebundenem Issue-Tracker gebaut. Der verwertbare Teil ist der
**prozessuale** (Interview, Doku, Diagnose, Agenten-Schreibstil), nicht der Coding-Teil.

Matts eigene Systematik trennt zwei Invokations-Arten, die sich auch für dieses Repo lohnt:

- **User-invoked** (`disable-model-invocation: true`): nur per `/name` erreichbar, orchestriert.
- **Model-invoked**: vom Agenten selbst greifbar, hält die wiederverwendbare Disziplin.

Ein user-invoked Skill darf model-invoked Skills aufrufen, aber nie einen anderen user-invoked. Mehrere seiner
`/`-Skills sind nur dünne Wrapper (`grill-me` = "Call the Skill tool with grilling").

## Direkt einbindbar

| Skill | Bucket | Warum |
|---|---|---|
| `writing-for-agents` | productivity | Die stärkste Datei im Repo. Context Pointer, Progressive Disclosure, Completion Criteria (Clarity/Demand), "leading words", No-op-Test, Negations-Falle ("Don't think of an elephant"). Direkt einschlägig für die Pflege der Agenten, Skills und CLAUDE.md in diesem Repo. |
| `diagnosing-bugs` | engineering | Phase 1 lautet: ohne roten, deterministischen, schnellen Feedback-Loop keine Hypothese. Sprachagnostisch, greift 1:1 für NixOS-Build-Fehler und mit kleiner Übersetzung für Netz-Störungsbilder. Ergänzt Bertrams `net-diagnose` um die Loop-Disziplin, die dort fehlt. |
| `to-questionnaire` | productivity | Entscheidung, die man nicht allein beantworten kann, wird zum Markdown-Fragebogen für genau eine Person. Der clevere Teil: "Grill den Versand, nicht das Thema" (Empfänger, Rolle, was zurückkommen muss). Passt auf Behörden-Zuarbeiten; Ausgabe danach durch Grimm. |
| `wait-what` | productivity | Sieben Zeilen: "Das ist nicht angekommen, pitch es neu" in ASD-STE100 Simplified Technical English mit dem Projekt-Glossar. Kostet nichts, wirkt sofort. |
| `handoff` | productivity | Konversation in ein Übergabedokument verdichten, inklusive "suggested skills" für den Folge-Agenten. Bei mehreren parallelen Agenten-Fenstern direkt verwertbar. Speicherort im Original ist das OS-Temp-Verzeichnis. |

## Anpassen, dann einbinden

| Skill | Bucket | Nötiger Umbau |
|---|---|---|
| `grilling` (+ Wrapper `grill-me`) | productivity | Der Kern deckt sich fast wörtlich mit der eigenen CLAUDE.md: Design-Tree, Frontier, Runden, Fakten selbst per Subagent beschaffen statt den Nutzer fragen, Entscheidungen bleiben beim Nutzer. **Konflikt:** Matt formatiert eine Runde als Fließtext mit ❓/➡️, die eigene Regel verlangt `AskUserQuestion` mit sich ausschließenden Optionen und der Empfehlung als erster Option. Umbau: eine Runde = ein `AskUserQuestion`-Call. Danach der beste Kandidat für die "kleine Klärungsrunde" aus dem iterativen Doku-Vorgehen. |
| `domain-modeling` | engineering | Glossar (`CONTEXT.md`) plus ADRs, inline gepflegt während der Diskussion, nicht nachgelagert. Der Wert liegt nicht im Code, sondern in Behörden- und Netzdoku: konsistente Terminologie über ein ganzes Konzept. Umbau: Glossar in den Vault statt `CONTEXT.md`, ADR-Ordner projektlokal. Die ADR-Dreierprobe (schwer reversibel **und** ohne Kontext überraschend **und** Ergebnis eines echten Trade-offs) unverändert übernehmen. |
| `research` | engineering | Konzept passt: Background-Agent, nur Primärquellen, jede Aussage zitiert, Ergebnis eine Markdown-Datei. Umbau: Ablage nach `recherche/<slug>.md` im Vault mit Frontmatter (URL, Abrufdatum), Ausführung über Karin. Sonst konkurriert es mit dem bestehenden Recherche-Pfad. |
| `teach` | productivity | Die Projektart "Wissensaufnahme" hat bisher keine Struktur. Der Skill liefert eine: `MISSION.md`, `RESOURCES.md`, `learning-records/`, Zone of Proximal Development, Trennung Fluency- vs. Storage-Strength, wiederverwendbare Assets. Umbau: HTML-Lektionen zu Obsidian-Notes mit Mermaid, learning-records in den Vault. |
| `retro` | in-progress | Retrospektive nicht über den Code, sondern über die **Agenten-Umgebung**: Navigation, No-ops in Steering-Files, Tool-Ökonomie, was in die CLAUDE.md gehört und was nach unten in Referenzdateien. Bei der Größe der eigenen CLAUDE.md ein echtes Werkzeug. Umbau: Referenzen auf `CODING_STANDARDS.md` raus, eigenes Skill- und Agent-Layout rein. |
| `wizard` | engineering | Generiert ein Bash-Skript, das einen Menschen durch Schritte führt, die nur er tun kann: Dashboard-Klicks, Credentials, einmalige Cutover. Brauchbar für Cisco-Provisionierung, Secure-Boot-Enrollment, Behörden-Portale. Umbau: `template.sh` auf `set -euo pipefail`, eigene `log_*`-Funktionen, Ausführung in `nix-shell`. |

## Nicht übernehmen

| Skill(s) | Grund |
|---|---|
| `code-review` | Namenskollision mit dem eingebauten `/code-review` und setzt `docs/agents/issue-tracker.md` voraus. Die Fowler-Smell-Baseline (12 Smells, je "was es ist → wie man es behebt") lohnt sich trotzdem als reine Referenzdatei ohne den Skill. |
| `to-spec`, `to-tickets`, `triage`, `implement`, `wayfinder`, `setup-matt-pocock-skills` | Hängen alle am konfigurierten Issue-Tracker und aneinander; nur als ganzer Strang sinnvoll. `wayfinder` (Entscheidungs-Tickets als geteilte Karte für Vorhaben, die größer als eine Session sind) hat konzeptionell den meisten Reiz für große Doku-Vorhaben, kostet aber den vollen Umbau auf lokale Dateien. |
| `tdd`, `codebase-design`, `improve-codebase-architecture`, `prototype`, `setup-ts-deep-modules` | TS- und App-zentriert. Die eigenen Codeobjekte sind Nix und Bash. |
| `migrate-to-shoehorn`, `scaffold-exercises`, `setup-pre-commit` | TS-Typassertions, Matts Kursformat, Husky/npm. Paketmanager hier ist Nix. |
| `git-guardrails-claude-code` | Blockt destruktive Git-Befehle per PreToolUse-Hook. Konzept gut, aber besser über die eigene `update-config`-Skill aufsetzen, statt das Skript zu importieren. |
| `writing-beats`, `writing-fragments`, `writing-shape` | Artikel-Schreibprozess, kollidiert mit Grimm und `unslop`. |
| `resolving-merge-conflicts`, `claude-handoff`, `implement-spec`, `loop-me` | Klein, redundant oder von bestehenden Mitteln abgedeckt. |

## Installationsweg

Das Repo bietet zwei Wege, die sich ausschließen (beides zusammen ergibt jeden Skill doppelt):

- `claude plugins install mattpocock-skills` — verwaltetes Bundle, read-only, aktualisiert sich selbst.
- `npx skills@latest add mattpocock/skills` — editierbare Kopien im eigenen Repo.

Da fast alle Kandidaten Umbau brauchen: **kein Plugin-Install**, sondern gezielt einzelne `SKILL.md` aus einem Klon
übernehmen. Der halbe Wert liegt ohnehin in der Anpassung an die eigenen Konventionen (Vault, `AskUserQuestion`,
Nix, Umlaute).

## Lizenz

MIT (siehe `LICENSE` im Quell-Repo). Übernahme mit Herkunftsvermerk im jeweiligen Plugin unproblematisch, analog
zum bestehenden Vorgehen bei `vendors/obsidian-skills`.

## Nächster Schritt

Vorschlag: mit `writing-for-agents` und `grilling` anfangen. Ersteres unverändert, letzteres mit der Umstellung
der Frage-Runden auf `AskUserQuestion`.
