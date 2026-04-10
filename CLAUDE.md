# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekttyp

**Projekt** — Git mit Branches, kein Commit direkt auf main. CLAUDE.md und README.md vor jedem Merge/Commit pruefen.

## Was ist das hier?

Ein Claude Code **Marketplace-Repository** — eine persoenliche Sammlung von Plugins (Skills, Agents, Commands, Hooks) die ueber das Plugin-System installierbar sind.

## Architektur

```
.claude-plugin/marketplace.json   # Marketplace-Index — listet alle Plugins
vendors/
  obsidian-skills/                # Git Submodule: kepano/obsidian-skills
plugins/
  _template/                      # Vorlage fuer neue Plugins (nicht im Marketplace)
  <plugin-name>/                  # Jedes Plugin ist eigenstaendig
    .claude-plugin/plugin.json    # Plugin-Manifest (Name, Version, Komponenten)
    skills/                       # SKILL.md Dateien (oder Symlinks nach vendors/)
    agents/                       # Agent-Definitionen (.md)
    commands/                     # Slash Commands (.md)
    hooks/                        # hooks.json
```

## Konventionen

- **Plugin-Namen:** kebab-case, beschreibend, global eindeutig
- **Versionierung:** Semantic Versioning (MAJOR.MINOR.PATCH)
- **Namespace:** Skills werden als `muhackel-plugins:skill-name` referenziert
- **Neues Plugin:** `_template/` kopieren, umbenennen, in `marketplace.json` eintragen
- **Marketplace-Eintrag:** Jedes fertige Plugin braucht einen Eintrag in `.claude-plugin/marketplace.json` mit `name`, `source` (relativ), `description`, `version`

## Plugin registrieren (marketplace.json)

```json
{
  "name": "mein-plugin",
  "source": "./plugins/mein-plugin",
  "description": "Was das Plugin tut",
  "version": "0.1.0"
}
```

## Testen

```bash
# Marketplace lokal registrieren
/plugin marketplace add ./

# Plugin installieren (lokal)
/plugin install plugin-name --scope local
```

## Externe Quellen

- Skills aus **kepano/obsidian-skills** (MIT, Steph Ango) liegen als Git Submodule unter `vendors/obsidian-skills/`. Plugins referenzieren diese per Symlink (`plugins/<name>/skills/<skill> → ../../../vendors/obsidian-skills/skills/<skill>`).
- Update: `git submodule update --remote vendors/obsidian-skills`

## Git-Workflow

- `main` — stabile Releases
- `develop` — Integrationsbranch
- Feature-Branches: `feature/<plugin-name>` oder `feature/<beschreibung>`
