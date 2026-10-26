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
docs/                             # Evaluierungen fremder Skill-Sammlungen, Entscheidungsnotizen, Messreihen
vendors/
  obsidian-skills/                # Git Submodule: kepano/obsidian-skills
plugins/
  _template/                      # Vorlage für neue Plugins (nicht im Marketplace)
  <plugin-name>/                  # Jedes Plugin ist eigenständig
    .claude-plugin/plugin.json    # Claude-Manifest (Name, Version, Komponenten)
    .codex-plugin/plugin.json     # Codex-Manifest (eigenes Schema, siehe unten)
    skills/                       # SKILL.md Dateien — GETEILT (oder Symlinks nach vendors/)
    commands/                     # Slash Commands (.md) — GETEILT
    agents/                       # Agent-Definitionen (.md) — nur Claude; Codex lädt sie über den Command
    hooks/hooks.json              # Claude-Hooks
    hooks.json                    # Codex-Hooks (Symlink → hooks/hooks.json; nur falls Hooks)
```

## Konventionen

- **Plugin-Namen:** kebab-case, beschreibend, global eindeutig
- **Versionierung:** Semantic Versioning (MAJOR.MINOR.PATCH)
- **Namespace:** Skills werden als `<plugin>:<skill>` referenziert (z.B. `bertram:net-diagnose`)
- **Neues Plugin:** `_template/` kopieren, umbenennen, in **beide** Marketplaces eintragen
- **Marketplace-Eintrag:** Jedes fertige Plugin braucht einen Eintrag in `.claude-plugin/marketplace.json` **und** in `.agents/plugins/marketplace.json`

## ⚠️ Dual-Pflege: Claude Code + Codex

**Jede Änderung, die ein Manifest oder den Marketplace betrifft, muss in BEIDEN Welten nachgezogen werden.** Der Content (`skills/`, `commands/`, `agents/*.md`) ist geteilt und wird nur einmal gepflegt — aber die Manifeste und Marketplace-Indizes existieren doppelt.

| Was | Claude Code | Codex |
|-----|-------------|-------|
| Plugin-Manifest | `plugins/<n>/.claude-plugin/plugin.json` | `plugins/<n>/.codex-plugin/plugin.json` |
| Marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |
| Skills / Commands / Agent-`.md` | **geteilt** — beide Manifeste zeigen auf dieselben Verzeichnisse | |
| Agenten | Frontmatter in `agents/*.md` | keine Plugin-Agenten; der Persona-Command lädt `agents/<n>.md` |
| Hooks | `hooks/hooks.json` | `hooks.json` im Plugin-Root (Symlink → `hooks/hooks.json`) |

**Commands unter Codex:** Codex migriert `commands/<name>.md` beim Install automatisch zu einem Skill
`<plugin>:source-command-<name>` (Frontmatter `name`/`description` wird übernommen). `${CLAUDE_PLUGIN_ROOT}`
wird dort **nicht** ersetzt — Commands, die Skripte aufrufen, leiten den Root aus dem eigenen Skill-Pfad ab
(Verzeichnis, das `.codex-plugin/` enthält). Ein Skill darf nicht so heißen wie ein Command desselben
Plugins (`skills/ask/` würde `/ask` verdecken).

**Checkliste bei jeder Plugin-Änderung** (Version-Bump, neue Skills/Commands, Beschreibung):
1. `.claude-plugin/plugin.json` **und** `.codex-plugin/plugin.json` angleichen (mind. `version`, `description`, `keywords`).
2. Beide Marketplace-Indizes prüfen (neuer Eintrag / geänderte Beschreibung).
3. Nur bei bewusst gesperrten Skills (`tools`): `skills/<name>/agents/openai.yaml` mit `allow_implicit_invocation: false` anlegen. Persona-Skills bleiben offen.
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

Eigenes Schema (belegt aus `openai/plugins`): `interface`-Objekt mit Präsentations-Metadaten, `skills` als Pfad-String. `commands`/`hooks` werden per Konvention gefunden und stehen NICHT im Manifest (Commands als migrierte Skills). `agents/` liest Codex nicht.

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

### Codex-Skill-Sperre (`skills/<name>/agents/openai.yaml`, nur bei gesperrten Skills)

```yaml
interface:
  display_name: "Mein Plugin: Skill"
  short_description: "Kurz, ein Satz"
  default_prompt: "Nutze $mein-plugin:skill, um …"
policy:
  allow_implicit_invocation: false
```

## Testen

**Claude Code:**

```bash
# Marketplace lokal registrieren
/plugin marketplace add ./

# Plugin installieren (lokal)
/plugin install plugin-name --scope local
```

**Lean-Profil (tokensparende Sitzung):** Agenten haben in Claude Code keinen Sperrschalter, nur das Plugin
lässt sich über `enabledPlugins` ausblenden. `profiles/lean.json` schaltet die vier Technik-Personas ab,
`bibliothekarin` und `tools` bleiben:

```bash
claude --settings "$(git rev-parse --show-toplevel)/profiles/lean.json"   # nur diese Sitzung
cp profiles/lean.json <projekt>/.claude/settings.local.json               # dauerhaft je Projekt, nicht in Git
```

Die Quelle `flag` schlägt local, project und user. Kein Pendant für Codex.

**Codex:** Der Marketplace liegt unter `.agents/plugins/marketplace.json`, Plugins unter `plugins/<n>/.codex-plugin/`. Skills werden in Codex über `/skills` bzw. `$skill-name` angesprochen. Den exakten Marketplace-/Plugin-Install-Befehl gegen die aktuelle Codex-Doku prüfen (`developers.openai.com/codex` → Customization/Plugins) — hier bewusst nicht aus dem Gedächtnis dokumentiert.

## Tools: nur explizite Auslösung

`plugins/tools/` bündelt Werkzeuge, die nie automatisch anspringen (`unslop`, `grimm`).
Nachfolger der Plugins `unslop` und `grimm`, die als `-final` markiert bis zur Entfernung bleiben.
`ask`, `execute` und die `orchestrator`-Skills sind mit 0.3.0 entfallen, ebenso das Plugin `ask`:
Cross-CLI-Arbeit und Orchestrierung übernimmt T3 Code über seinen MCP-Server (`delegate_task`).

- Einstiegspunkte sind **Skills, keine Commands und keine Agents**: nur Skills haben in beiden CLIs einen
  belegten Schalter. Claude Code: `disable-model-invocation: true` im Frontmatter. Codex:
  `skills/<name>/agents/openai.yaml` mit `policy.allow_implicit_invocation: false`.
- **Agents** kennen in Claude Code keinen solchen Schalter, Claude delegiert nach `description`. Darum kein
  Agent in `tools`. Skills mit `disable-model-invocation: true` lassen sich auch nicht in Subagenten vorladen.
- Wissen, das ein Tool braucht, liegt als `references/*.md` (kein Skill-Frontmatter), damit es nicht
  selbst als Skill auftaucht.
- Der `plugin-creator`-Validator von Codex lehnt `disable-model-invocation: true` ab, die Codex-Laufzeit
  lädt die Skills trotzdem (mit `tools` 0.1.0 am 2026-09-14 getestet). Das Feld bleibt drin.

## Persona-Plugins: Fachwissen im Agenten, Skills offen

Umgesetzt am 2026-10-10 in `nixie` 0.6.0, `bertram` 0.3.0, `christian` 0.4.0, `it-grundschutz` 0.6.0 und
`bibliothekarin` 0.8.0 (Rückbau des Lazy-Musters aus 0.x vom 2026-09-18).
Hintergrund und Messung: `docs/messung-lazy-skills-2026-09-18.md`, `docs/messung-rueckbau-2026-10-10.md`
sowie die Analyse vom 2026-10-10 im Vault (`KI-Entwicklung/claude-code-plugins-persona-agenten-tokensparend`). Kurz: Agenten haben in Claude
Code keinen Sperrschalter, nur `enabledPlugins` blendet ein Plugin aus; gesperrte Skills sparen darum im
Hauptkontext nichts, was das Lean-Profil nicht auch spart, kosten aber Read-Roundtrips im Agenten.

- Fach-Skills sind **offen** (kein `disable-model-invocation`, keine `agents/openai.yaml`). Ihre
  `description` hat 150 bis 250 Zeichen: Was und Wann, keine Aufzählung der Unterthemen. Das Listing hat
  ein Budget von 1 % des Kontextfensters, bei 200k-Modellen rund 8k Zeichen; überlange Descriptions werden
  dort auf den Namen gekürzt.
- Große Skills sind in einen `SKILL.md`-Kern und `references/*.md` neben der Datei geteilt (Progressive
  Disclosure). Der Kern nennt je Referenz den Fall, in dem sie zu lesen ist. Pfade relativ zur `SKILL.md`.
- Der Agent lädt per `skills:` nur die Skills vor, die praktisch jeder Auftrag braucht (`nixie`:
  `nix-docs`, `nixos-config`; `bertram`: `net-reference`; `christian`: `vpn-reference`, `vpn-tunnel`;
  `bruce`: `gs-lookup`; Karin: `obsidian-cli`). Die übrigen holt er über das Skill-Tool, das darum in `tools:` steht.
  Der Abschnitt „Fachwissen“ im Body nennt je Skill die Achse und den spätesten Zeitpunkt. Das Skill-Tool
  bringt das ganze Skill-Listing in den Subagenten, rund 8k Tokens je Spawn (`docs/messung-rueckbau-2026-10-10.md`);
  Agenten, die nie nachladen, bekommen es nicht (`bibliothekarin-search`: 7,8k statt 17,9k).
- Der Agent-Body enthält Rolle, STARTUP, Kernprinzipien der Domäne, Recherche und Sicherheitsregeln,
  rund 6k Zeichen. Allgemeine Sorgfalt (lesen vor Edit, keine Bulk-Ersetzungen, Umlaute) steht als
  Dreizeiler drin, weil die Plugins ohne die globale `CLAUDE.md` des Users nutzbar bleiben müssen. Kein
  `omitClaudeMd`: `nixie` braucht die Projekt-`CLAUDE.md` des Zielrepos.
- STARTUP ist an den Auftrag gekoppelt: Achse zuerst, Infrastrukturprüfungen (Build-Host-Config, Hostname)
  nur, wenn die Achse sie braucht.
- Agent-`description` rund 300 bis 350 Zeichen, Einstieg „Proaktiv nutzen bei jeder konkreten …-Aufgabe,
  auch wenn nur ein Vorschlag gefragt ist“ (bei `nixie` von 0/3 auf 3/3 Delegationen), eine Einschränkung,
  die Abgrenzung zur nächstliegenden Persona. Die Command-`description` ist textgleich: in Claude ist der
  Command gesperrt und kostet nichts, in Codex ist er der einzige Eintrag der Persona.
- Arbeitsdateien einer Persona (Downloads, Zwischenstände) nur in einem Verzeichnis aus `mktemp -d`, am
  Ende des Auftrags löschen; nie ins Arbeitsverzeichnis des Users oder an einen selbst gewählten Pfad.
- Persona-Commands tragen `disable-model-invocation: true`, der Hauptagent delegiert über das Agent-Tool.
  Codex kennt keine Plugin-Agenten (kein Code in 0.154.0 liest `agents/` im Plugin-Root); dort lädt der
  migrierte Command `agents/<name>.md` als Rollenanweisung. Die Migration verwirft
  `disable-model-invocation`, der migrierte Command ist in Codex also der sichtbare Einstieg.
- Der Command-Body ist ein Adapter von rund 1,5k Zeichen: Claude-Teil „nur den User-Text weitergeben,
  keine Anweisung, `agents/`, `skills/` oder `references/` zu lesen“, Codex-Teil nur die Root-Ermittlung
  und der Verweis auf `references/codex-start.md` im Plugin-Root. Die Root-Ermittlung bleibt im Body, weil
  relative Links im migrierten Command brechen. `codex-start.md` nennt die Dateien, die unter Codex das
  `skills:`-Preload ersetzen. Ohne die Trennung hat die Hauptsitzung die Codex-Schritte an den Subagenten
  weitergereicht, der dann alles vorab las.
- Kein Routing-Hinweis im Command-Body: Die Abgrenzung steht in der Description, die Hauptsitzung hat die
  Agentenliste ohnehin.
- **Ausnahme `bibliothekarin`:** Vault-Zugriff ist kritisch, Karin muss aus jeder Sitzung erreichbar
  bleiben. `/karin` und `/vault` bekommen keine Sperre, der Hauptagent darf sie selbst aufrufen.
  Vendor-Skills, die nur Karin braucht (`obsidian-bases`, `json-canvas`), liegen als Symlink unter
  `references/`, weil sich ihr Frontmatter im Submodul nicht ändern lässt. Claude löst die Symlinks beim
  Install auf (0.7.0 am 2026-09-19 geprüft).

## Externe Quellen

- Skills aus **kepano/obsidian-skills** (MIT, Steph Ango) liegen als Git Submodule unter `vendors/obsidian-skills/`. Plugins referenzieren diese per Symlink (`plugins/<name>/skills/<skill> → ../../../vendors/obsidian-skills/skills/<skill>`, bzw. unter `references/`, wenn nur der Agent sie liest).
- Update: `git submodule update --remote vendors/obsidian-skills`

## Git-Workflow

- `main` — stabile Releases, einziger dauerhafter Branch
- Feature-Branches: `feature/<plugin-name>` oder `feature/<beschreibung>`, kurzlebig
- Merge per PR bzw. `--no-ff`, danach den Branch lokal und auf origin löschen. Die Merge-Commits
  halten fest, welche Commits zusammengehören, der Branch selbst wird nicht mehr gebraucht.
