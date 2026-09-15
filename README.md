# claude-code-plugins

Persönliche Sammlung von Plugins — Skills, Agents, Commands und Hooks. Lauffähig sowohl in **Claude Code** als auch in **OpenAI Codex** (geteilter Content, getrennte Manifeste).

## Nutzung

### Repo klonen (mit Submodules)

```bash
git clone --recurse-submodules https://github.com/muhackel/claude-code-plugins
# Oder nachträglich:
git submodule update --init --recursive
```

### Marketplace registrieren

```bash
# In Claude Code:
/plugin marketplace add muhackel/claude-code-plugins

# Oder lokal:
/plugin marketplace add /pfad/zum/repo
```

> **Codex:** Dieselben Plugins sind auch für OpenAI Codex nutzbar — der Codex-Marketplace liegt unter `.agents/plugins/marketplace.json`, die Plugin-Manifeste unter `plugins/<name>/.codex-plugin/`. Den exakten Install-Befehl gegen die aktuelle [Codex-Doku](https://developers.openai.com/codex) prüfen.

### Plugin installieren

```bash
# Global (alle Projekte)
/plugin install plugin-name@muhackel-plugins --scope user

# Projekt-weit (für alle Teammitglieder)
/plugin install plugin-name@muhackel-plugins --scope project

# Nur lokal
/plugin install plugin-name@muhackel-plugins --scope local
```

## Struktur

| Verzeichnis | Inhalt |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace-Index (Claude Code) |
| `.agents/plugins/marketplace.json` | Marketplace-Index (Codex) |
| `plugins/<name>/` | Einzelne Plugins — Manifest je System (`.claude-plugin/` + `.codex-plugin/`), Content geteilt |
| `plugins/_template/` | Vorlage für neue Plugins (beide Manifeste) |
| `vendors/obsidian-skills/` | Git Submodule: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (MIT) |

## Neues Plugin erstellen

1. `plugins/_template/` nach `plugins/<mein-plugin>/` kopieren
2. **Beide** Manifeste anpassen: `.claude-plugin/plugin.json` und `.codex-plugin/plugin.json` (Name, Beschreibung, Version, Keywords)
3. Komponenten in `skills/`, `agents/`, `commands/`, `hooks/` anlegen (geteilt zwischen beiden Systemen)
4. Bei echtem Agenten: `agents/openai.yaml.template` → `openai.yaml` umbenennen und ausfüllen (Codex-Agent-Registry)
5. Plugin in **beide** Marketplaces eintragen: `.claude-plugin/marketplace.json` und `.agents/plugins/marketplace.json`
6. Testen mit `/plugin marketplace add ./` und `/plugin install <name> --scope local`

> Details zum Dual-Manifest-Schema (Claude Code + Codex): siehe [`CLAUDE.md`](CLAUDE.md).

## Verfügbare Plugins

### bibliothekarin

Wissensmanagement-Agent — primäres Interface für den Obsidian Vault.
Wissen einpflegen (INGEST), abrufen und synthetisieren (SYNTH/SEARCH), destillieren (DESTILL) und Vault-Pflege (SCAN, AUDIT, RECHERCHE).
State Machine mit atomaren Tasks. Arbeitet mit `obsidian` CLI und Dateisystem.
Erstellt zudem **Diagramme** (Mermaid/PlantUML) reference-first und empfiehlt die passende Diagrammart.

Slash Commands:
- `/karin` — Karin direkt aufrufen (routet automatisch zum passenden Agent)
- `/vault` — Schneller Vault-Zugriff ohne Subagent (suchen, lesen, Tags)

Agent-Varianten:
- `bibliothekarin` — Vollständig (alle Skills, voller Startup) für Ingest, Audit, Scan, Destillation
- `bibliothekarin-search` — Leichtgewichtig (nur obsidian-cli) für Suche und Synthese (~8.600 Tokens weniger)

Skills via Symlink aus [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (MIT):
- obsidian-markdown, obsidian-bases, obsidian-cli, json-canvas, defuddle

Eigene Diagramm-Skills:
- `mermaid` — native Vault-Diagramme (Obsidian rendert nativ), mit Kollisions-Kernregel (reservierte Wörter nie als `classDef`-Namen)
- `plantuml` — UML-Typen jenseits von Mermaid, mit ehrlichem Rendering-Vorbehalt
- `diagramm-auswahl` — empfiehlt Diagrammart + Tool (Zweck → Typ → Mermaid/PlantUML/json-canvas)

Die offizielle Diagramm-Doku wird **offline** vorgehalten (Mermaid-Repo-Klon + PlantUML-Website/Referenz-PDF), **nicht** im Repo getrackt (liegt unter `~/.local/share/bibliothekarin/diagram-docs`) und per Altersgate (14 Tage) aktuell gehalten. Renderer (`mmdc`, `plantuml`) zur lokalen Validierung liefert die Nix-Umgebung — Details in [`build.md`](plugins/bibliothekarin/build.md):

```bash
nix run ./plugins/bibliothekarin#fetch-docs            # Offline-Doku befüllen/aktualisieren
nix run ./plugins/bibliothekarin#fetch-docs -- --status # Alter je Quelle anzeigen
```

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

IT-Grundschutz-Berater (Persona **Bruce**) auf Basis eines **lokal vorgehaltenen OSCAL-Korpus**.
Schlägt BSI-Anforderungen zitierfähig nach (per ID wie `GC.1.1` oder Thema), modelliert Bausteine für
Szenarien und begleitet Editionswechsel (Crosswalk). Quelle und Logik sind strikt getrennt: der Agent
arbeitet nur gegen ein internes OSCAL-Schema, neue Editionen brauchen nur einen neuen Adapter.

Quelle: BSI Stand-der-Technik-Bibliothek (`BSI-Bund/Stand-der-Technik-Bibliothek`), Grundschutz++ als
OSCAL-Katalog. Der Korpus (Lizenz **CC BY-SA 4.0**) wird per Ingest lokal vorgehalten und **nicht** ins
Repo eingecheckt.

Slash Command:
- `/bruce` — Bruce direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `gs-ingest` — Korpus laden/cachen/aktualisieren: Anwenderkatalog + Methodik + Profile (Manifest je Datei mit sha256)
- `gs-lookup` — Anforderungen zitierfähig nachschlagen (ID/Volltext); zeigt auch die Methodik-Ebene (das Warum)
- `gs-dokument` — Sicherheitsdokumente nach der Methodik führen, als Gerüst erzeugen oder prüfen (Gap)
- `gs-review` — IT-Grundschutz-Check (Soll-Ist): Umsetzungsstatus je Anforderung erheben/auswerten, Erfüllungsgrad + offene Punkte, Audit-Readiness
- `gs-crosswalk` — Editionen abgleichen (Edition 2023 ↔ Grundschutz++): innerhalb einer Edition per stabilem `alt-identifier`-Diff, editionsübergreifend heuristischer Inhaltsvergleich via `gs crosswalk <ID>` (Token-Überlappung, kein offizielles BSI-Mapping)
- `gs-modellierung` — zutreffende Bausteine/Anforderungen für ein Szenario ermitteln (Grundschutz++ zielobjektbasiert via `gs list --target`/`gs coverage` mit STM-Vererbung; Edition 2023 via `gs coverage` über eine heuristische Komponente→Baustein-Hinttabelle)
- `gs-krypto` — kryptographische Verfahren/Schlüssellängen/Cipher-Suiten zitierfähig nach **BSI TR-02102** (Teile -1 bis -4) bewerten, mit NIST/FIPS-Gegenprobe. Kommt **live** aus der offiziellen Quelle (bewusste Ausnahme von der Korpus-first-Regel — Krypto-Fristen verschieben sich jährlich); typischer Zulieferfall ist die VPN-Config-Härtung für `christian`

Build-Umgebung via Nix (`flake.nix`, Details in `build.md`): `nix run .#ingest`, `nix run .#gs -- <cmd>`.

```bash
/plugin install it-grundschutz@muhackel-plugins --scope user
```

### nixie

NixOS-Engineer — baut und pflegt NixOS-Konfigurationen (Flake-first), schreibt eigene Derivations und
Overlays, pinnt lang bauende Pakete und deployt auf die Maschinen im Netz.
Dokumentenorientiert (schlägt vor Annahmen nach), `nix flake check` immer ohne Truncation, Deploy nur auf
explizite Anweisung. Wählt den Build-Host dynamisch (schnellste erreichbare Kiste) und drosselt
`--max-jobs`/`--cores` resource-aware gegen OOM bei schweren Builds. Für Maschinen ohne Netz gibt es
einen generischen Offline-Closure-Deploy (Export auf USB, geführtes TUI am Ziel).

Slash Command:
- `/nixie` — Nixie direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `nixos-config` — Konventionen der NixOS-Config (mkHost, Feature-Flags, Modul-Layout)
- `nix-packaging` — Derivations, Overlays, Paket-Pinning
- `nix-deploy` — Build-Host-Auswahl, resource-aware Builds, Eskalationsstufen, flake check, Offline-Closure-Deploy (USB/TUI)
- `nix-docs` — Doku-Lookup-Disziplin (search.nixos.org, noogle, nix search, Manpages)

Standalone nutzbar — keine Wissensdatenbank vorausgesetzt; Recherche macht Nixie selbst. Optional: ist ein
Wissensmanagement-Agent installiert (z.B. `bibliothekarin`), kann Nixie längere Recherche oder das
Dokumentieren in einer Knowledge Base als Briefing dahin weiterreichen (Orchestrierung über den
Hauptagenten).

```bash
/plugin install nixie@muhackel-plugins --scope user
```

### bertram

Netzwerk-Engineer (Persona **Bertram Fritz**) — vendor-agnostische Diagnose und Konfiguration nach dem
**Reference-first-Prinzip**: CLI-Syntax und Best Practices kommen aus der Vendor-Referenz, nicht aus dem
Gedächtnis. L1–L7-Fehlersuche, Config erzeugen/validieren, Dialekt-Übersetzung (Cisco IOS ↔ RouterOS ↔
PAN-OS ↔ Aruba ↔ Junos) und Architektur-/Segmentierungs-Design. Live-Zugriff ist gestuft: read-only als
Default, schreibende Eingriffe nur auf explizite Anforderung mit Rollback-Netz (Blast-Radius-Respekt).

Slash Command:
- `/bertram` — Bertram direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `net-reference` — Reference-first-Disziplin: Quellen je Vendor, Workflow präzisieren→holen→verifizieren→zitierfähig→anwenden
- `net-diagnose` — L1→L7-Diagnosesequenzen mit Show-Kommandos, Output-Deutung und Anti-Patterns
- `net-config` — Config erzeugen mit Pre-Deployment-Validierung, Dialekt-Übersetzung über die Konzept-Ebene, Best-Practice-Templates
- `net-operate` — gestufter Live-Zugriff via SSH (Stufe 0 read-only, Stufe 1 schreibend mit Rollback je Vendor, Remote-Lockout-Checkliste)
- `net-design` — Architektur-Ebene: Segmentierung (VLANs/Zonen/VRFs), Routing-/Firewall-Design, Resilienz, Migrationspfad-Denken

Standalone nutzbar — kommerzielle Netzwerk-Hardware ist Bertrams Revier; Linux-/Open-Source-VPN und
-Router sowie BSD-Firewall-Appliances (pfSense/OPNsense) gehören zu `christian`.

```bash
/plugin install bertram@muhackel-plugins --scope user
```

### christian

Linux-VPN- & Router-Appliance-Spezialist (Persona **Christian Scheele**) — der VPN-Fachmann für **sichere
WAN-Verbindungen zwischen Netzen**, ebenfalls **Reference-first** (Config-Syntax und Krypto-Parameter aus
Manpage/Projekt-Doku, nie geraten). OpenVPN als Kern-Expertise, dazu WireGuard, IPsec (strongSwan/
Libreswan), Mesh-Overlays und L2-Tunnel; voller Linux-Router-Stack (nftables/FRR/BIRD/NAT); dazu
BSD-Firewall-Appliances pfSense/OPNsense (pf, config.xml, VPN über die GUI-Instanzen). Live-Deploy
gestuft mit Rollback (ein WAN-Link-Change kappt den Standort). Delegiert NixOS-Umsetzung an `nixie` und
Krypto-Freigaben an `bruce` (`it-grundschutz`/`gs-krypto`, TR-02102).

Slash Command:
- `/christian` — Christian direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `vpn-reference` — Reference-first-Herzstück: Quellen je Technik (OpenVPN/WireGuard/strongSwan/FRR/nftables/Mesh-Projekte)
- `openvpn` — Kern-Expertise: PKI (easy-rsa 3), tls-crypt, topology subnet, iroute/push-Routing, Krypto-Härtung, Troubleshooting, Anti-Patterns
- `vpn-tunnel` — die breite Palette: WireGuard, IPsec/IKEv2, L2-Suite (EtherIP/GRETAP/L2TPv3/VXLAN), Mesh-Overlays, SSL-VPN
- `router-appliance` — Linux-Router-Stack: nftables (Zonen/NAT), FRR/BIRD, iproute2/systemd-networkd, Policy-Routing; OpenWrt/DD-WRT sekundär
- `wan-link` — Design-Ebene: Kopplungs-Szenario→Tech-Wahl, L2-vs-L3, Krypto-Härtung (bruce-Konsultation), Failover/BFD, MTU/MSS-Clamping
- `bsd-firewall` — pfSense/OPNsense: pf-Semantik, VPN-GUI-Instanzen, Multi-WAN/Gateway-Groups, Plugins, config.xml

Standalone nutzbar — für die NixOS-Umsetzung oder eine Krypto-Freigabe schreibt Christian ein Briefing und
empfiehlt dem Hauptagenten, `nixie` bzw. `bruce` zu spawnen.

```bash
/plugin install christian@muhackel-plugins --scope user
```

### tools

Werkzeuge, die **nur auf ausdrücklichen Aufruf** laufen und nie automatisch anspringen. Nachfolger der
Plugins `ask`, `unslop` und `grimm`. Jeder Skill trägt `disable-model-invocation: true` (Claude Code)
und eine `agents/openai.yaml` mit `allow_implicit_invocation: false` (Codex).

Skills:
- `/tools:ask` — Cross-CLI-Zweitmeinung, read-only: fragt non-interaktiv die **jeweils andere CLI**
  (aus Claude Code → `codex exec`, aus Codex → `claude -p`) mit Modell und Effort zur **Stufe**
  (`advanced` opus/sol high, `strong` fable/astra medium; `--boost`/`--fast` verschieben den Effort,
  `--model`/`--effort` setzen beides frei). Ohne Argument ein Standard-Review des aktuellen Projekts,
  mit Argument eine eigene Frage.
- `/tools:execute` — dasselbe mit Schreibrechten im Workspace (kein Commit/Push), zusätzlich Stufe
  `drone` (sonnet/luna) für mechanische Aufträge.
- `/tools:unslop` — entfernt typische KI-Muster (62 Erkennungsmerkmale in acht Kategorien) aus einem
  übergebenen Text oder ohne Argument aus dem zuletzt selbst geschriebenen.
- `/tools:grimm` — Behörden-Schreibstilist: überführt Sachverhalte ins nüchterne Verwaltungs- und
  Anordnungsdeutsch und baut ganze Dokumente (Anordnung nach Führungsschema, Vermerk, Konzept,
  Sachstandsbericht). Kern-Prinzip **Form, nicht Fakten**: fehlt ein Fakt, setzt Grimm einen Platzhalter.
- `/tools:orchestrator`, `/tools:orchestrator-review`, `/tools:orchestrator-cross` — Rollen-Prompt für die
  laufende Sitzung: steuern statt arbeiten. Alle drei tragen denselben Kern (zerlegen, Agents der eigenen
  CLI briefen, Ergebnisse abnehmen, keine eigene Umsetzung). Stufe 2 darf Arbeit per ask `strong --fast`
  (komplex: `strong`) gegenprüfen lassen, `--boost` nur nach Rückfrage einmal pro Sitzung. Stufe 3 setzt
  die andere CLI auch per execute (`drone`/`advanced`) ein, Boost nach Abwägung mit Begründung. Weil
  ask/execute für das Modell gesperrt sind, liest der Orchestrator deren `SKILL.md` und folgt ihr.

Für ask/execute schreibt der Host ein Handover ([`references/handover.md`](plugins/tools/references/handover.md)),
die andere CLI startet mit leerem Kontext. Jeder Aufruf erscheint in `ccusage`. Die Ziel-CLIs kommen
bewusst vom Host-PATH, nicht aus nixpkgs. Hilfswerkzeuge und Checks via Nix
(Details in [`build.md`](plugins/tools/build.md)): `nix run ./plugins/tools#ask`, `nix flake check`.

```bash
/plugin install tools@muhackel-plugins --scope user
```

### grimm, ask, unslop (veraltet)

Letzte Versionen `grimm` 0.2.0-final, `ask` 0.4.0-final, `unslop` 0.4.0-final. Funktion unverändert,
ein Hinweis auf den Nachfolger `tools` erscheint bei ask und grimm bei jedem Aufruf, bei unslop
einmal pro Sitzung. Werden später entfernt.

### philharmonie

Projektaufträge mit versionierter Spec, getrenntem Generator und Evaluator sowie dauerhaftem
Missionszustand. Verbindet die Cross-CLI-Aufträge aus ask mit unabhängiger Prüfung und belegter
Abnahme. Die Linux-Laufzeit verwendet Nix und Bubblewrap; Änderungen entstehen in Snapshots und
werden nur für freigegebene Pfade übernommen.

Planer und Generator delegieren unabhängige Teilaufgaben an eigene Agents mit aufgabenbezogener
Modellwahl. Vor der Freigabe bewertet die andere CLI die Spec mit einem begründeten Score und
weist Blocker separat aus.

Nach jedem Aufruf zeigt eine Modellübersicht, wer welche Aufgabe umgesetzt oder geprüft hat und
mit welchem Ergebnis; fehlende oder nur konfigurierte Modellnachweise werden gekennzeichnet.
Die Sitzungsverzeichnisse der Ziel-CLIs sind in die Sandbox eingebunden, sodass jeder Auftrag in
`ccusage` erscheint und im Resume-Picker die Kennung `[Philharmonie …]` trägt.

Commands: `/philharmonie:plan`, `review-spec`, `run`, `status`, `resume`, `pause`, `cancel`, `accept` sowie die
Einzelaufrufe `ask` und `execute`. Unter Codex stehen die Commands als migrierte Skills zur Verfügung.
Die Einzelaufrufe bleiben über `/tools:ask` und `/tools:execute` separat nutzbar.

Details und Betriebsgrenzen in [README](plugins/philharmonie/README.md) und
[build.md](plugins/philharmonie/build.md); Entwurf in [design-ask-tandem.md](docs/design-ask-tandem.md).

## Lizenz

MIT
