# bertram — Backlog

Offene Punkte oben, umgesetzte darunter (jüngste zuerst).

---

## OFFEN — Phase 2: `net-config` + `net-operate`

- **`net-config`** (Config erzeugen + validieren + Dialekt-Übersetzung):
  - Pre-Deployment-Validierung: dangerous-command-Erkennung, Subnet-Overlap, doppelte IPs,
    ACL-Logikfehler, fehlende `commit`/`write`.
  - Dialekt-Übersetzung über die **Konzept-Ebene** (dasselbe Ziel in Cisco IOS ↔ RouterOS ↔ PAN-OS ↔
    Aruba ↔ Junos), nicht als 1:1-Token-Mapping.
  - Best-Practice-Templates: VLAN-Segmentierung, Trunk/Access, Firewall-Zonen, Management-Hardening.
- **`net-operate`** (gestufter Live-Zugriff via SSH):
  - Eskalationsstufen: (0) read-only show-Kommandos, (1) Config-Change mit Rollback-Netz.
  - Change-Safety je Vendor: Cisco `reload in <min>` / `configure replace`, RouterOS `safe-mode`,
    PAN-OS `commit`/`revert`, Junos `commit confirmed`.
  - Remote-Lockout-Vermeidung als harte Checkliste (ACL/Mgmt-Interface/Default-Route zuletzt anfassen).

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
