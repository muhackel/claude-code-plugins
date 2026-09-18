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
3. Bei gesperrten Skills: `skills/<name>/agents/openai.yaml` mit `allow_implicit_invocation: false` anlegen.
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

**Codex:** Der Marketplace liegt unter `.agents/plugins/marketplace.json`, Plugins unter `plugins/<n>/.codex-plugin/`. Skills werden in Codex über `/skills` bzw. `$skill-name` angesprochen. Den exakten Marketplace-/Plugin-Install-Befehl gegen die aktuelle Codex-Doku prüfen (`developers.openai.com/codex` → Customization/Plugins) — hier bewusst nicht aus dem Gedächtnis dokumentiert.

## Tools: nur explizite Auslösung

`plugins/tools/` bündelt Werkzeuge, die nie automatisch anspringen (`ask`, `execute`, `unslop`, `grimm`,
`orchestrator[-review|-cross]`).
Nachfolger der Plugins `ask`, `unslop` und `grimm`, die als `-final` markiert bis zur Entfernung bleiben.

- Einstiegspunkte sind **Skills, keine Commands und keine Agents**: nur Skills haben in beiden CLIs einen
  belegten Schalter. Claude Code: `disable-model-invocation: true` im Frontmatter. Codex:
  `skills/<name>/agents/openai.yaml` mit `policy.allow_implicit_invocation: false`.
- **Agents** kennen in Claude Code keinen solchen Schalter, Claude delegiert nach `description`. Darum kein
  Agent in `tools`. Skills mit `disable-model-invocation: true` lassen sich auch nicht in Subagenten vorladen.
- Wissen, das ein Tool braucht, liegt als `references/*.md` (kein Skill-Frontmatter), damit es nicht
  selbst als Skill auftaucht.
- Die `orchestrator`-Skills sind Rollen-Prompts in drei kumulativen Stufen; der Kern steht in allen drei
  `SKILL.md` wörtlich gleich (bewusst dreifach, kein Verweis: der Prompt soll beim Aufruf direkt im Kontext
  liegen). Stufe 2 und 3 nutzen `ask`/`execute` über deren `SKILL.md` als Datei, weil die Sperre gegen
  Modell-Aufruf keine Ausnahme für Rollen kennt.
- Der `plugin-creator`-Validator von Codex lehnt `disable-model-invocation: true` ab, die Codex-Laufzeit
  lädt die Skills trotzdem (mit `tools` 0.1.0 am 2026-09-14 getestet). Das Feld bleibt drin.

## Persona-Plugins: Fachwissen nur im Agenten

Umgesetzt in `bertram`, `christian`, `it-grundschutz` und `nixie`; `bibliothekarin` folgt mit der
Ausnahme unten. Jede Datei unter `skills/` steht sonst mit ihrer
Beschreibung im Kontext der Hauptsitzung und jedes Subagenten, und `skills:` im Agent-Frontmatter lädt
zusätzlich den vollen Body beim Start (Claude Code 2.1.272 und Codex 0.154.0 am 2026-09-18 getestet).

- Fachwissens-Skills tragen `disable-model-invocation: true` und `skills/<name>/agents/openai.yaml` mit
  `policy.allow_implicit_invocation: false`. In beiden CLIs fehlen sie damit im Modellkontext; von Hand
  holt man sie per `/<plugin>:<skill>` bzw. `$<plugin>:<skill>`.
- Kein `skills:` im Agenten: Vorladen scheitert an der Sperre still, das Skill-Tool blockt auch im
  Subagenten. Stattdessen führt der Agent-Body eine Tabelle „Datei → lesen, sobald“ mit Pfaden der Form
  `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` (im Agent-Body ersetzt) und liest sie direkt. Die
  Auslöser hängen an der Handlung („bevor du auf ein Gerät zugreifst“), nicht nur am Auftrag.
- In Claude Code bleibt die Agent-`description` als einziger Eintrag im Hauptkontext: ~300–470 Zeichen,
  Trigger und Abgrenzung zu den anderen Personas. Delegiert die Hauptsitzung nicht von selbst, hilft ein
  Einstieg „Proaktiv nutzen bei jeder konkreten …-Aufgabe, auch wenn nur ein Vorschlag gefragt ist“
  (bei `nixie` von 0/3 auf 3/3 Delegationen).
- Arbeitsdateien einer Persona (Downloads, Zwischenstände) nur in einem Verzeichnis aus `mktemp -d`, am
  Ende des Auftrags löschen; nie ins Arbeitsverzeichnis des Users oder an einen selbst gewählten Pfad.
- Persona-Commands tragen `disable-model-invocation: true`, der Hauptagent delegiert über das Agent-Tool.
  Codex kennt keine Plugin-Agenten (kein Code in 0.154.0 liest `agents/` im Plugin-Root, auch nicht
  `agents/openai.yaml`); dort lädt der migrierte Command `agents/<name>.md` als Rollenanweisung. Die
  Migration verwirft `disable-model-invocation`, der migrierte Command ist in Codex also der sichtbare
  Einstieg. Darum trägt seine `description` dieselben Trigger und Abgrenzungen wie die des Agenten.
  Eine `agents/openai.yaml` im Plugin-Root entfällt beim Umbau.
- Der Claude-Teil des Commands sagt ausdrücklich: nur den User-Text weitergeben, keine Anweisung,
  `agents/` oder `skills/` zu lesen; der Codex-Teil ist als „Nur Codex“ markiert. Ohne diese Trennung
  hat die Hauptsitzung die Codex-Schritte an den Subagenten weitergereicht, der dann alles vorab las.
- Skills, die der Hauptagent selbst braucht (etwa `obsidian-cli`), bleiben ungesperrt.
- **Ausnahme `bibliothekarin`:** Vault-Zugriff ist kritisch, Karin muss aus jeder Sitzung erreichbar
  bleiben. `/karin` und `/vault` bekommen keine Sperre, der Hauptagent darf sie selbst aufrufen.

## Externe Quellen

- Skills aus **kepano/obsidian-skills** (MIT, Steph Ango) liegen als Git Submodule unter `vendors/obsidian-skills/`. Plugins referenzieren diese per Symlink (`plugins/<name>/skills/<skill> → ../../../vendors/obsidian-skills/skills/<skill>`).
- Update: `git submodule update --remote vendors/obsidian-skills`

## Philharmonie

`plugins/philharmonie/` enthält Skills und Commands sowie eine Linux-Laufzeit in Python. Zustandsänderungen
laufen ausschließlich über `scripts/philharmonie.py` mit einer erwarteten Revision. Spec und Ergebnisse
werden gegen JSON-Schemata geprüft. CLI-Adapter arbeiten in Bubblewrap-Snapshots; die Übernahme kontrolliert
Ausgangsstand und erlaubte Pfade. Keine direkten Edits an Missionszuständen als Workflow-Abkürzung.

Planer und Generator delegieren nach `references/delegation.md` an native Agents der eigenen CLI.
Vor `approve` ist `review-spec` durch die andere CLI erforderlich. Der begründete Spec-Score ist an
Spec, Vertrag und Projektstand gebunden; offene Blocker verhindern die Freigabe unabhängig vom Score.

Die Laufzeit berichtet Modellarbeit je Aufruf auf stderr und als `invocation_models` in Zustandsausgaben.
Native Modellnachweise und Selbstberichte getrennt halten; gespeicherte Run-Historie ist kein neuer Aufruf.

Modelle werden nach Stufe gewählt, nicht pauschal als Flaggschiff. Philharmonie kennt `light` haiku/luna,
`standard` sonnet/terra, `advanced` opus/sol, `strong` fable/astra (Codex-Spitze aus dem Katalog der
installierten Version); dort entscheidet die Rolle: Generator und Evaluator `advanced`, Spec-Gegenprüfung
`strong`. Die Staffelung ist dieselbe wie bei den Subagenten in `delegation.py` — bei Änderungen beide
Ebenen zusammen halten.

`tools:ask`/`tools:execute` haben eine eigene, bewusst von Philharmonie entkoppelte Tabelle (`--tier`):
`strong` fable/astra mit Effort medium (`--boost` high, `--fast` low), `advanced` opus/sol mit high
(`--boost` xhigh; Default beider Modi), `drone` sonnet/luna mit high (nur execute). `--model` und
`--effort` setzen beides frei, bei `--model` ist der Effort high.

Fehlt ein Klassenmodell im Codex-Katalog, fällt der Aufruf auf `advanced` und erst danach auf die Wahl
der CLI zurück. Nie direkt auf "ohne Modellangabe" ausweichen: `codex exec` nimmt dann das Flaggschiff,
auch wenn `model` in `~/.codex/config.toml` etwas anderes sagt (bei `exec` nachgemessen, greift dort
nicht). Bei Claude ist der Fall nicht vorab prüfbar, weil die CLI keinen Modellkatalog ausgibt; ohne
`--model` läuft dort Opus 5.

Aufträge beider Plugins schreiben Sitzungsdateien der Ziel-CLI und sind darum in `ccusage` sichtbar.
Bei Philharmonie sind dafür die Sitzungsverzeichnisse des Hosts in die Sandbox gebunden — die einzige
Stelle, an der ein Auftrag außerhalb seines Snapshots schreibt. Jeder Auftrag trägt eine Kennung im
Resume-Picker: bei Claude über `--name`, bei Codex als Präfix des Auftrags, weil Codex kein solches
Flag kennt. Ein Codex-Rollout gehört zu einem Auftrag, wenn sein Sitzungskopf dessen Snapshot als
Arbeitsverzeichnis nennt; der Zeitstempel allein reicht nicht, weil Codex fremde Rollouts anfasst.

Tests im Plugin über `nix flake check path:. -L`. Die zusätzlichen Sandbox- und echten CLI-Integrationstests
sind bewusst separat; Aufrufe und Betriebsgrenzen stehen in `plugins/philharmonie/build.md`.

## Git-Workflow

- `main` — stabile Releases, einziger dauerhafter Branch
- Feature-Branches: `feature/<plugin-name>` oder `feature/<beschreibung>`, kurzlebig
- Merge per PR bzw. `--no-ff`, danach den Branch lokal und auf origin löschen. Die Merge-Commits
  halten fest, welche Commits zusammengehören, der Branch selbst wird nicht mehr gebraucht.
