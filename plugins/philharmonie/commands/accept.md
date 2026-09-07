---
name: accept
description: "Ein geprüftes Philharmonie-Ergebnis nach eindeutiger Nutzerabnahme abschließen und die Summary erzeugen."
---

Ermittle den Plugin-Root als übergeordnetes Verzeichnis dieser Datei mit `.codex-plugin/` oder `.claude-plugin/`. Lies dort `skills/orchestration/SKILL.md`.

Ordne die Nutzerabnahme eindeutig einer Mission und ihrem geprüften Ergebnis zu. Lies `status <id> --full` und den Rundenbericht. Bei bereits eindeutiger Abnahme nicht erneut fragen. Führe `nix run "path:<root>" -- -C "<projekt>" accept <id> --authorization '<Nutzeranweisung>' --revision <n>` aus.

Der Kern lehnt veraltete Prüfstände ab. Bei Erfolg die erzeugte `Summary.md` lesen und verlinken. Aus dieser fachlichen Abnahme keine zusätzliche Erlaubnis zu Commit, Push, Merge oder Deployment ableiten.
