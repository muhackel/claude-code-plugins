# claude-code-plugins

Persoenliche Sammlung von Claude Code Plugins — Skills, Agents, Commands und Hooks.

## Nutzung

### Repo klonen (mit Submodules)

```bash
git clone --recurse-submodules https://github.com/muhackel/claude-code-plugins
# Oder nachtraeglich:
git submodule update --init --recursive
```

### Marketplace registrieren

```bash
# In Claude Code:
/plugin marketplace add muhackel/claude-code-plugins

# Oder lokal:
/plugin marketplace add /pfad/zum/repo
```

### Plugin installieren

```bash
# Global (alle Projekte)
/plugin install plugin-name@muhackel-plugins --scope user

# Projekt-weit (fuer alle Teammitglieder)
/plugin install plugin-name@muhackel-plugins --scope project

# Nur lokal
/plugin install plugin-name@muhackel-plugins --scope local
```

## Struktur

| Verzeichnis | Inhalt |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace-Index |
| `plugins/<name>/` | Einzelne Plugins mit eigenem Manifest |
| `plugins/_template/` | Vorlage fuer neue Plugins |
| `vendors/obsidian-skills/` | Git Submodule: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (MIT) |

## Neues Plugin erstellen

1. `plugins/_template/` nach `plugins/<mein-plugin>/` kopieren
2. `plugin.json` anpassen (Name, Beschreibung, Version, Keywords)
3. Komponenten in `skills/`, `agents/`, `commands/`, `hooks/` anlegen
4. Plugin in `.claude-plugin/marketplace.json` eintragen
5. Testen mit `/plugin marketplace add ./` und `/plugin install <name> --scope local`

## Verfuegbare Plugins

### bibliothekarin

Wissensmanagement-Agent — primaeres Interface fuer den Obsidian Vault.
Wissen einpflegen (INGEST), abrufen und synthetisieren (SYNTH/SEARCH), destillieren (DESTILL) und Vault-Pflege (SCAN, AUDIT, RECHERCHE).
State Machine mit atomaren Tasks. Arbeitet mit `obsidian` CLI und Dateisystem.

Slash Commands:
- `/karin` — Karin direkt aufrufen (routet automatisch zum passenden Agent)
- `/vault` — Schneller Vault-Zugriff ohne Subagent (suchen, lesen, Tags)

Agent-Varianten:
- `bibliothekarin` — Vollstaendig (alle Skills, voller Startup) fuer Ingest, Audit, Scan, Destillation
- `bibliothekarin-search` — Leichtgewichtig (nur obsidian-cli) fuer Suche und Synthese (~8.600 Tokens weniger)

Enthaltene Skills (via Symlink aus [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills), MIT):
- obsidian-markdown, obsidian-bases, obsidian-cli, json-canvas, defuddle

```bash
/plugin install bibliothekarin@muhackel-plugins --scope user
```

### defuddle

Web-Seiten zu sauberem Markdown konvertieren via Defuddle CLI — token-effizienter als WebFetch.
Skill von [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (MIT).

```bash
/plugin install defuddle@muhackel-plugins --scope user
```

## Lizenz

MIT
