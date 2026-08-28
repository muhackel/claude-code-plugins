# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekttyp

**Projekt** — Git mit Branches, kein Commit direkt auf main. CLAUDE.md und README.md vor jedem Merge/Commit prüfen.

## Was ist das hier?

Ein **Marketplace-Repository** — eine persönliche Sammlung von Plugins (Skills, Agents, Commands, Hooks). Die Plugins sind **doppelt lauffähig**: für **Claude Code** UND für **OpenAI Codex**. Beide Systeme teilen sich denselben Content (`skills/`, `commands/`, `agents/*.md`) und unterscheiden sich nur in den Manifesten.

## Architektur

```
.claude-plugin/marketplace.json   # Claude-Marketplace-Index — listet alle Plugins
.agents/plugins/marketplace.json  # Codex-Marketplace-Index (anderes Schema, siehe unten)
docs/                             # Evaluierungen fremder Skill-Sammlungen, Entscheidungsnotizen
vendors/
  obsidian-skills/                # Git Submodule: kepano/obsidian-skills
plugins/
  _template/                      # Vorlage für neue Plugins (nicht im Marketplace)
  <plugin-name>/                  # Jedes Plugin ist eigenständig
    .claude-plugin/plugin.json    # Claude-Manifest (Name, Version, Komponenten)
    .codex-plugin/plugin.json     # Codex-Manifest (eigenes Schema, siehe unten)
    skills/                       # SKILL.md Dateien — GETEILT (oder Symlinks nach vendors/)
    commands/                     # Slash Commands (.md) — GETEILT
    agents/                       # Agent-Definitionen (.md) — GETEILT
      openai.yaml                 # Codex-Agent-Registry (nur Codex; nur bei echten Agents)
    hooks/hooks.json              # Claude-Hooks
    hooks.json                    # Codex-Hooks (Symlink → hooks/hooks.json; nur falls Hooks)
```

## Konventionen

- **Plugin-Namen:** kebab-case, beschreibend, global eindeutig
- **Versionierung:** Semantic Versioning (MAJOR.MINOR.PATCH)
- **Namespace:** Skills werden als `muhackel-plugins:skill-name` referenziert
- **Neues Plugin:** `_template/` kopieren, umbenennen, in **beide** Marketplaces eintragen
- **Marketplace-Eintrag:** Jedes fertige Plugin braucht einen Eintrag in `.claude-plugin/marketplace.json` **und** in `.agents/plugins/marketplace.json`

## ⚠️ Dual-Pflege: Claude Code + Codex

**Jede Änderung, die ein Manifest oder den Marketplace betrifft, muss in BEIDEN Welten nachgezogen werden.** Der Content (`skills/`, `commands/`, `agents/*.md`) ist geteilt und wird nur einmal gepflegt — aber die Manifeste und Marketplace-Indizes existieren doppelt.

| Was | Claude Code | Codex |
|-----|-------------|-------|
| Plugin-Manifest | `plugins/<n>/.claude-plugin/plugin.json` | `plugins/<n>/.codex-plugin/plugin.json` |
| Marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |
| Skills / Commands / Agent-`.md` | **geteilt** — beide Manifeste zeigen auf dieselben Verzeichnisse | |
| Agent-Registry | Frontmatter in `agents/*.md` | zusätzlich `agents/openai.yaml` |
| Hooks | `hooks/hooks.json` | `hooks.json` im Plugin-Root (Symlink → `hooks/hooks.json`) |

**Checkliste bei jeder Plugin-Änderung** (Version-Bump, neue Skills/Commands, Beschreibung):
1. `.claude-plugin/plugin.json` **und** `.codex-plugin/plugin.json` angleichen (mind. `version`, `description`, `keywords`).
2. Beide Marketplace-Indizes prüfen (neuer Eintrag / geänderte Beschreibung).
3. Bei neuem/geändertem Agenten: `agents/openai.yaml` nachziehen.
4. Bei neuen Hooks: `hooks.json`-Symlink im Plugin-Root anlegen.

### Claude-Manifest (`.claude-plugin/plugin.json`)

```json
{
  "name": "mein-plugin",
  "description": "Was das Plugin tut",
  "version": "0.1.0",
  "author": { "name": "Sebastian Rädle", "email": "muhackel@gmail.com" },
  "license": "MIT",
  "keywords": [],
  "skills": "./skills",
  "commands": "./commands"
}
```

### Claude-Marketplace-Eintrag (`.claude-plugin/marketplace.json`)

```json
{ "name": "mein-plugin", "source": "./plugins/mein-plugin", "description": "…", "version": "0.1.0" }
```

### Codex-Manifest (`.codex-plugin/plugin.json`)

Eigenes Schema (belegt aus `openai/plugins`): `interface`-Objekt mit Präsentations-Metadaten, `skills` als Pfad-String. `commands`/`agents`/`hooks` werden per Konvention auto-discovered und stehen NICHT im Manifest.

```json
{
  "name": "mein-plugin",
  "version": "0.1.0",
  "description": "Was das Plugin tut",
  "author": { "name": "Sebastian Rädle", "email": "muhackel@gmail.com" },
  "repository": "https://github.com/muhackel/claude-code-plugins",
  "license": "MIT",
  "keywords": [],
  "skills": "./skills/",
  "interface": {
    "displayName": "Mein Plugin",
    "shortDescription": "Kurz, ein Satz",
    "longDescription": "Zwei bis drei Sätze.",
    "developerName": "Sebastian Rädle",
    "category": "Developer Tools",
    "capabilities": ["Interactive", "Read", "Write"],
    "defaultPrompt": "Typischer Nutzer-Prompt an dieses Plugin.",
    "screenshots": []
  }
}
```

### Codex-Marketplace-Eintrag (`.agents/plugins/marketplace.json`)

```json
{
  "name": "mein-plugin",
  "source": { "source": "local", "path": "./plugins/mein-plugin" },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_USE", "products": ["CODEX"] },
  "category": "Developer Tools"
}
```

### Codex-Agent-Registry (`agents/openai.yaml`, nur bei echtem Agenten)

```yaml
interface:
  display_name: "Mein Plugin"
  short_description: "Kurz, ein Satz"
  default_prompt: "Typischer Nutzer-Prompt an dieses Plugin."
```

## Testen

**Claude Code:**

```bash
# Marketplace lokal registrieren
/plugin marketplace add ./

# Plugin installieren (lokal)
/plugin install plugin-name --scope local
```

**Codex:** Der Marketplace liegt unter `.agents/plugins/marketplace.json`, Plugins unter `plugins/<n>/.codex-plugin/`. Skills werden in Codex über `/skills` bzw. `$skill-name` angesprochen. Den exakten Marketplace-/Plugin-Install-Befehl gegen die aktuelle Codex-Doku prüfen (`developers.openai.com/codex` → Customization/Plugins) — hier bewusst nicht aus dem Gedächtnis dokumentiert.

## Externe Quellen

- Skills aus **kepano/obsidian-skills** (MIT, Steph Ango) liegen als Git Submodule unter `vendors/obsidian-skills/`. Plugins referenzieren diese per Symlink (`plugins/<name>/skills/<skill> → ../../../vendors/obsidian-skills/skills/<skill>`).
- Update: `git submodule update --remote vendors/obsidian-skills`

## Git-Workflow

- `main` — stabile Releases
- `develop` — Integrationsbranch
- Feature-Branches: `feature/<plugin-name>` oder `feature/<beschreibung>`
