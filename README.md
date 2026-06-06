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

### it-grundschutz

IT-Grundschutz-Berater (Persona **Gustav**) auf Basis eines **lokal vorgehaltenen OSCAL-Korpus**.
Schlaegt BSI-Anforderungen zitierfaehig nach (per ID wie `GC.1.1` oder Thema), modelliert Bausteine fuer
Szenarien und begleitet Editionswechsel (Crosswalk). Quelle und Logik sind strikt getrennt: der Agent
arbeitet nur gegen ein internes OSCAL-Schema, neue Editionen brauchen nur einen neuen Adapter.

Quelle: BSI Stand-der-Technik-Bibliothek (`BSI-Bund/Stand-der-Technik-Bibliothek`), Grundschutz++ als
OSCAL-Katalog. Der Korpus (Lizenz **CC BY-SA 4.0**) wird per Ingest lokal vorgehalten und **nicht** ins
Repo eingecheckt.

Slash Command:
- `/gustav` — Gustav direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `gs-ingest` — Korpus von der BSI-Quelle laden/cachen/aktualisieren (Manifest mit Version/sha256)
- `gs-lookup` — Anforderungen zitierfaehig nachschlagen (ID/Volltext, mit Edition & Quelle)
- `gs-crosswalk` — Editionen abgleichen (Edition 2023 ↔ Grundschutz++) via OSCAL-Profiles/alt-identifier
- `gs-modellierung` — zutreffende Bausteine fuer ein generisches Szenario ermitteln

Build-Umgebung via Nix (`flake.nix`, Details in `build.md`): `nix run .#ingest`, `nix run .#gs -- <cmd>`.

```bash
/plugin install it-grundschutz@muhackel-plugins --scope user
```

### nixie

NixOS-Engineer — baut und pflegt NixOS-Konfigurationen (Flake-first), schreibt eigene Derivations und
Overlays, pinnt lang bauende Pakete und deployt auf die Maschinen im Netz.
Dokumentenorientiert (schlaegt vor Annahmen nach), `nix flake check` immer ohne Truncation, Deploy nur auf
explizite Anweisung. Waehlt den Build-Host dynamisch (schnellste erreichbare Kiste) und drosselt
`--max-jobs`/`--cores` resource-aware gegen OOM bei schweren Builds.

Slash Command:
- `/nixie` — Nixie direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `nixos-config` — Konventionen der NixOS-Config (mkHost, Feature-Flags, Modul-Layout)
- `nix-packaging` — Derivations, Overlays, Paket-Pinning
- `nix-deploy` — Build-Host-Auswahl, resource-aware Builds, Eskalationsstufen, flake check
- `nix-docs` — Doku-Lookup-Disziplin (search.nixos.org, noogle, nix search, Manpages)

Standalone nutzbar — keine Wissensdatenbank vorausgesetzt; Recherche macht Nixie selbst. Optional: ist ein
Wissensmanagement-Agent installiert (z.B. `bibliothekarin`), kann Nixie laengere Recherche oder das
Dokumentieren in einer Knowledge Base als Briefing dahin weiterreichen (Orchestrierung ueber den
Hauptagenten).

```bash
/plugin install nixie@muhackel-plugins --scope user
```

## Lizenz

MIT
