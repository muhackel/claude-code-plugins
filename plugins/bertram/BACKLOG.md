# bertram — Backlog

Offene Punkte oben, umgesetzte darunter (jüngste zuerst).

---

## OFFEN — spätere Erweiterungen

- **`net-design`**: Netzarchitektur — Segmentierung, VLAN-/Subnetting-Plan, Routing-Design,
  Firewall-Zonen, Zero-Trust-Ansätze.
- **MikroMCP-Integration**: RouterOS-Geräte via MCP-Server statt reinem SSH inspizieren/operieren
  (typisiert, auditierbar). Als optionaler Zugriffsweg in `net-operate`.
- **Optionaler lokaler Referenz-Cache** (bruce-`gs-cache`-Stil): häufig gebrauchte Befehlsreferenzen/
  Hardening-Guides projekt- oder vault-lokal vorhalten, falls Offline-Zitierfähigkeit gewünscht ist.
- **Weitere Vendor-Packs**: Diagnose-/Config-Spezifika für zusätzliche Plattformen (FortiGate, Extreme,
  Ubiquiti/UniFi …), sobald Bedarf besteht.

---

## ✅ UMGESETZT (2026-07-18): Phase 2 — `net-config` + `net-operate`

Die beiden restlichen Skills ergänzt, Agent-Frontmatter `skills:` auf alle vier erweitert:
- **`net-config`** — Config erzeugen mit Pre-Deployment-Validierung (dangerous commands,
  Subnet-Overlap, doppelte IPs/VLAN-IDs, ACL-Logik, Persistenz/Vollständigkeit), Dialekt-Übersetzung
  über die Konzept-Ebene (IOS ↔ RouterOS ↔ PAN-OS ↔ Aruba ↔ Junos, inkl. Candidate-vs-live-Modell),
  Best-Practice-Templates (VLAN-Segmentierung, Trunk/Access, Firewall-Zonen, Mgmt-Hardening).
- **`net-operate`** — gestufter Live-Zugriff via SSH: Stufe 0 read-only, Stufe 1 schreibend mit
  gesicherter Ist-Config + Bestätigung + Rollback-Netz. Rollback je Vendor (Cisco `reload in`/
  `configure replace`, RouterOS `safe-mode`, PAN-OS `commit`/`revert`, Junos `commit confirmed`,
  Aruba `checkpoint`), Remote-Lockout-Checkliste, MikroMCP als späterer Zugriffsweg vermerkt.

## ✅ UMGESETZT (2026-07-18): Phase 1 — Gerüst + Agent + Reference-first-Kern

Plugin `bertram` angelegt: Persona `agents/bertram.md` (Eiserne Regeln: Reference-first,
Blast-Radius-Respekt, Layer-Disziplin, Vendor-Dialekt-Ehrlichkeit, verifiziert-vs-unsicher),
`/bertram`-Command, README. Zwei Kern-Skills:
- **`net-reference`** — Reference-first-Disziplin: Quellen je Vendor, Workflow (präzisieren → holen →
  verifizieren → zitierfähig ausgeben → anwenden), Best Practices mit Quelle belegen, ehrlicher Umgang
  wenn keine Referenz beschaffbar.
- **`net-diagnose`** — L1→L7-Diagnose-Sequenzen mit Show-Kommandos, Output-Deutung und Anti-Patterns
  (Interface-Health/Duplex, STP/VLAN/MAC, Routing/BGP/OSPF/ACL, Firewall/PMTU/DNS/DHCP).

Registriert in `.claude-plugin/marketplace.json` (v0.1.0).
