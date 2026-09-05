---
name: handover
description: Handover-Format und Ablauf für Cross-CLI-Aufrufe (/ask read-only, /execute workspace-write) — wie ein Auftrag an die jeweils andere CLI (Codex aus Claude Code, Claude aus Codex) formuliert, übergeben und die Antwort wiedergegeben wird. Nutzen, wenn eine unabhängige Zweitmeinung, ein Review des Projektstands oder eine delegierte Ausführung durch die andere CLI gebraucht wird.
---

# Handover für Cross-CLI-Aufrufe

Die andere CLI startet mit leerem Kontext. Sie sieht weder diese Sitzung noch den Chatverlauf, nur das
Arbeitsverzeichnis und das Handover. Alles, was sie wissen muss, steht im Handover.

## Ablauf

1. Plugin-Root ermitteln (Claude Code: `${CLAUDE_PLUGIN_ROOT}`; Codex: Verzeichnis, das `.codex-plugin/` enthält).
2. Handover nach dem Format unten schreiben. Bei `/ask` ohne Argument entfällt das, das Skript hat ein Standard-Review.
3. `scripts/ask.sh --mode ask|execute` mit dem Handover auf stdin starten (Heredoc). Das Skript erkennt den
   Host, wählt die andere CLI, ermittelt deren Flaggschiffmodell und setzt Effort `high`.
4. stdout ist die Antwort, stderr der Fortschritt. Antwort unverändert wiedergeben, dann kurz einordnen.

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
bash "<root>/scripts/ask.sh" --mode ask </dev/null        # Standard-Review
bash "<root>/scripts/ask.sh" --mode ask <<'HANDOVER'       # eigene Frage
…
HANDOVER
bash "<root>/scripts/ask.sh" --mode execute <<'HANDOVER'   # Auftrag mit Schreibrechten
…
HANDOVER
bash "<root>/scripts/ask.sh" --dry-run …                   # nur Kommando + Handover zeigen
```

Weitere Flags: `--target claude|codex` (Override der Host-Erkennung), `--handover FILE`, `-C DIR`.

## Rechte der anderen CLI

| Modus | Codex (`codex exec`) | Claude (`claude -p`) |
|---|---|---|
| ask | `-s read-only`, `--ephemeral` | `dontAsk`, Tools Read/Glob/Grep, Bash nur read-only git |
| execute | `-s workspace-write` | `acceptEdits`, Edit/Write/Bash, `git push` und Web verboten |

Codex sandboxt das Dateisystem, Claude nicht: bei `execute` mit Ziel Claude sichert nur die Anweisung im
Handover, dass außerhalb des Workspace nichts passiert. Deshalb `execute` nur auf Feature-Branch.

## Unter Codex

`claude -p` braucht Netz. Die Codex-Sandbox sperrt Netz standardmäßig, der Aufruf muss deshalb mit
`require_escalated` gestartet werden. Das Skript warnt, wenn `CODEX_SANDBOX_NETWORK_DISABLED=1` gesetzt ist.
