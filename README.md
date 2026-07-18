# claude-code-plugins

Persönliche Sammlung von Claude Code Plugins — Skills, Agents, Commands und Hooks.

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

# Projekt-weit (für alle Teammitglieder)
/plugin install plugin-name@muhackel-plugins --scope project

# Nur lokal
/plugin install plugin-name@muhackel-plugins --scope local
```

## Struktur

| Verzeichnis | Inhalt |
|---|---|
| `.claude-plugin/marketplace.json` | Marketplace-Index |
| `plugins/<name>/` | Einzelne Plugins mit eigenem Manifest |
| `plugins/_template/` | Vorlage für neue Plugins |
| `vendors/obsidian-skills/` | Git Submodule: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (MIT) |

## Neues Plugin erstellen

1. `plugins/_template/` nach `plugins/<mein-plugin>/` kopieren
2. `plugin.json` anpassen (Name, Beschreibung, Version, Keywords)
3. Komponenten in `skills/`, `agents/`, `commands/`, `hooks/` anlegen
4. Plugin in `.claude-plugin/marketplace.json` eintragen
5. Testen mit `/plugin marketplace add ./` und `/plugin install <name> --scope local`

## Verfügbare Plugins

### bibliothekarin

Wissensmanagement-Agent — primäres Interface für den Obsidian Vault.
Wissen einpflegen (INGEST), abrufen und synthetisieren (SYNTH/SEARCH), destillieren (DESTILL) und Vault-Pflege (SCAN, AUDIT, RECHERCHE).
State Machine mit atomaren Tasks. Arbeitet mit `obsidian` CLI und Dateisystem.

Slash Commands:
- `/karin` — Karin direkt aufrufen (routet automatisch zum passenden Agent)
- `/vault` — Schneller Vault-Zugriff ohne Subagent (suchen, lesen, Tags)

Agent-Varianten:
- `bibliothekarin` — Vollständig (alle Skills, voller Startup) für Ingest, Audit, Scan, Destillation
- `bibliothekarin-search` — Leichtgewichtig (nur obsidian-cli) für Suche und Synthese (~8.600 Tokens weniger)

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
`--max-jobs`/`--cores` resource-aware gegen OOM bei schweren Builds.

Slash Command:
- `/nixie` — Nixie direkt aufrufen (mit optionalem Auftrag)

Enthaltene Skills:
- `nixos-config` — Konventionen der NixOS-Config (mkHost, Feature-Flags, Modul-Layout)
- `nix-packaging` — Derivations, Overlays, Paket-Pinning
- `nix-deploy` — Build-Host-Auswahl, resource-aware Builds, Eskalationsstufen, flake check
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
-Router gehören zu `christian`.

```bash
/plugin install bertram@muhackel-plugins --scope user
```

### christian

Linux-VPN- & Router-Appliance-Spezialist (Persona **Christian Scheele**) — der VPN-Fachmann für **sichere
WAN-Verbindungen zwischen Netzen**, ebenfalls **Reference-first** (Config-Syntax und Krypto-Parameter aus
Manpage/Projekt-Doku, nie geraten). OpenVPN als Kern-Expertise, dazu WireGuard, IPsec (strongSwan/
Libreswan), Mesh-Overlays und L2-Tunnel; voller Linux-Router-Stack (nftables/FRR/BIRD/NAT). Live-Deploy
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

Standalone nutzbar — für die NixOS-Umsetzung oder eine Krypto-Freigabe schreibt Christian ein Briefing und
empfiehlt dem Hauptagenten, `nixie` bzw. `bruce` zu spawnen.

```bash
/plugin install christian@muhackel-plugins --scope user
```

## Lizenz

MIT
