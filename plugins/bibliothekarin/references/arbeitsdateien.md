# Formate der Arbeitsdateien

Grundgerüste für INDEX.md, LOG.md und RECHERCHE.md im Vault-Root.

## INDEX.md

```markdown
---
tags:
  - meta/index
description: "Automatisch generierter Vault-Index (BibliotheKarin)"
---
# Vault-Index

> Generiert: DD.MM.YYYY HH:MM | Notes: N | Ordner: N | Tags: N
> Ausgeschlossen: claude/, .trash/, .obsidian/, .git/, .claude/, INDEX.md, LOG.md, RECHERCHE.md

## Verzeichnisname/

| Note | Tags | Beschreibung |
|------|------|-------------|
| [[notename]] | `tag1`, `tag2` | Description aus Frontmatter |

## Nicht-Markdown-Dateien

| Datei | Ordner | Typ |
|-------|--------|-----|
| dateiname.pdf | Ordner/ | PDF |

## Tag-Übersicht

| Namespace | Tags | Häufigste |
|-----------|------|-----------|
| typ/ | N Tags | typ/domaene (X) |
```

## LOG.md

```markdown
---
tags:
  - meta/tracking
description: "Änderungs-Log (BibliotheKarin)"
---
# Vault-Log

## DD.MM.YYYY

### HH:MM — Aktion
- Detail 1
- Detail 2
```

Einträge reverse-chronologisch (neueste oben). Pro Tag eine Sektion.

## RECHERCHE.md

```markdown
---
tags:
  - meta/tracking
  - phase/recherche
description: "Offene Fragen und Wissenslücken im Vault (BibliotheKarin)"
---
# Offene Fragen & Wissenslücken

> Letzte Aktualisierung: DD.MM.YYYY HH:MM | Offen: N | Erledigt: N

## Offen

### Kategorie (z.B. Fehlende Pflichtfelder)

- [ ] [[note]] — Beschreibung des Problems
  *Erkannt: DD.MM.YYYY | Quelle: Scan/Audit/User*

## Erledigt

- [x] ~~Beschreibung~~ 
  *Erkannt: DD.MM.YYYY | Erledigt: DD.MM.YYYY | Entscheidung: ...*
```
