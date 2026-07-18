# bertram — Netzwerk-Engineer

Bertram Fritz, der Netzwerk-Engineer. Vendor-agnostisch (Cisco, MikroTik/RouterOS, Palo Alto/PAN-OS,
HP/Aruba, Juniper), sattelfest von L1 bis L7. Kern-Prinzip: **Reference-first** — CLI-Syntax und Best
Practices kommen aus der Vendor-Befehlsreferenz, nicht aus dem Gedächtnis. Analog zu `bruce`
(„Korpus-first") und `nixie` („Docs-first").

## Philosophie

- **Reference-first:** Netzwerk-CLI-Wissen im Modell ist veraltet und verwechselt Vendor-Dialekte.
  Bertram schlägt die Referenz nach oder fordert sie an, bevor er Syntax ausgibt.
- **Blast-Radius-Respekt:** Ein Config-Change kann das Netz lahmlegen oder aussperren. Default ist
  read-only; Live-Eingriffe nur auf explizite Anforderung, mit Bestätigung und Rollback-Netz.
- **Layer-Disziplin:** Fehlersuche strukturiert von L1 nach oben — erst messen, dann schließen.

## Komponenten

| Typ | Name | Zweck |
|-----|------|-------|
| Agent | `bertram:bertram` | Netzwerk-Engineer-Persona, orchestriert die Skills |
| Command | `/bertram` | Bertram direkt aufrufen (mit optionalem Auftrag) |
| Skill | `net-reference` | Befehlsreferenz/Best Practices zitierfähig nachschlagen (Reference-first) |
| Skill | `net-diagnose` | L1–L7-Fehlersuche mit geordneten Diagnose-Sequenzen |
| Skill | `net-config` | Config erzeugen, validieren, zwischen Vendor-Dialekten übersetzen |
| Skill | `net-operate` | Gestufter Live-Zugriff (SSH) mit vendor-spezifischer Change-Safety |
| Skill | `net-design` | Netzarchitektur entwerfen/bewerten — Segmentierung, Adressplan, Routing, Resilienz |

Weitere geplante Erweiterungen (MikroMCP-Integration, Offline-Referenz-Cache, weitere Vendor-Packs) in
[BACKLOG.md](./BACKLOG.md).

## Nutzung

```
/bertram warum haben die Uplinks zwischen den beiden Cat9300 CRC-Fehler?
/bertram übersetze diese Cisco-VLAN-Config nach RouterOS
```

Ohne Text spawnt der Command Bertram, der dann nach Vendor/Gerät und Symptom/Ziel fragt.

## Installation (lokal)

```bash
/plugin marketplace add ./
/plugin install bertram --scope local
```

## Lizenz

MIT. Struktur und Ideen der Diagnose-Skills sind inspiriert von `arsallls/claude-network-skills` (MIT),
aber eigenständig geschrieben.
