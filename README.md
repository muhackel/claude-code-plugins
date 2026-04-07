# claude-code-plugins

Persoenliche Sammlung von Claude Code Plugins — Skills, Agents, Commands und Hooks.

## Nutzung

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

## Neues Plugin erstellen

1. `plugins/_template/` nach `plugins/<mein-plugin>/` kopieren
2. `plugin.json` anpassen (Name, Beschreibung, Version, Keywords)
3. Komponenten in `skills/`, `agents/`, `commands/`, `hooks/` anlegen
4. Plugin in `.claude-plugin/marketplace.json` eintragen
5. Testen mit `/plugin marketplace add ./` und `/plugin install <name> --scope local`

## Verfuegbare Plugins

*Noch keine — wird mit der Zeit wachsen.*

## Lizenz

MIT
