---
name: net-design
description: "Netzarchitektur entwerfen und bewerten: Segmentierung (VLANs/Zonen/VRFs), IP-/Subnetting-Plan, Routing-Design (OSPF-Areas, BGP, Redundanz, Multicast/RP), Firewall-Zonen und Zero-Trust, Resilienz (Stacking, LACP über Chassis, STP-Root-Design, First-Hop-Redundanz). Design-Prinzipien: Hierarchie, Fehlerdomänen, Blast-Radius. Nutzen, wenn ein Netz oder Segment geplant, umgebaut oder gegen Best-Practice-Architektur bewertet wird — die Ebene 'wie soll es aussehen', bevor net-config das 'wie schreibe ich es' liefert."
---

# Net-Design — wie das Netz aussehen soll

Design ist die Ebene **über** der Config: erst die Struktur (Zonen, Adressplan, Routing, Fehlerdomänen),
dann die Umsetzung (`net-config`). Design-Entscheidungen mit Vendor-Design-Guides, RFCs oder anerkannten
Referenzarchitekturen belegen (`net-reference`) — nicht als Geschmack behaupten. Ein Design ist ein
**Dokument** (Zonenkonzept, Adressplan, Netzplan), kein Bauch.

## Design-Prinzipien

- **Hierarchie & Fehlerdomänen:** klare Rollen (Core / Distribution / Access, bzw. Collapsed-Core im
  kleinen Netz). Ein Fehler soll seine Domäne nicht verlassen. Frag bei jedem zentralen Element: *was
  fällt mit ihm aus?* (Blast-Radius) — Single-Chassis-Core, beide LACP-Member auf einem Gerät,
  eine RP für die ganze Domäne sind klassische versteckte SPOFs.
- **Segmentierung nach Schutzbedarf:** Zonen trennen, was unterschiedlichen Schutzbedarf/Vertrauen hat
  (Server, Client, Mgmt/OOB, DMZ, Gast, Einsatz/VPN). Mgmt gehört in ein **eigenes** VLAN/VRF, nie in
  die Produktions-Broadcast-Domäne. Default zwischen Zonen ist **deny**, Übergänge laufen kontrolliert
  über eine Policy-Instanz (Firewall/ACL).
- **Konsistenter Adressplan:** strukturiertes, aggregierbares Subnetting (Summarization an den
  Hierarchie-Grenzen spart Routing-Tabelle und Fehlersuche). Ein nachvollziehbares Schema (Standort /
  Rolle / Zone in den Oktetten) schlägt gewachsenen Wildwuchs. /30 oder /31 (RFC 3021) für
  Punkt-zu-Punkt-Transfernetze.
- **Wachstum & Rückbau mitdenken:** Design überlebt Migrationen. Wird eine Legacy-Zone zurückgebaut,
  dürfen zentrale Dienste (RP/Multicast, NTP/DNS, Default-Route) nicht an ihr hängen — Abhängigkeiten
  vorher auf stabile Adressen umziehen.

## Bausteine

### Segmentierung (L2/Zonen)
- VLAN-/Zonenschema mit klarer Zuordnung Zone → VLAN → Subnetz; Native-VLAN bewusst und ungenutzt;
  ungenutzte Ports in ein Blackhole-VLAN + shutdown. Zonenübergänge nur über die Policy-Instanz.
- VRFs zur **L3-Isolation** dort, wo reine VLAN-Trennung nicht reicht (z.B. isoliertes Einsatz-/VPN-Netz,
  Mgmt-VRF). VRF-Grenzen und die wenigen kontrollierten Leaks explizit dokumentieren.

### Routing-Design (L3)
- **OSPF:** Area-Design nach Fehlerdomäne/Größe; Backbone-Kontinuität (Area 0); Summarization an
  ABR-Grenzen; Router-IDs deterministisch vergeben; Interface-Auth (Key-Chain, rotierbar — **nicht** ein
  netzweiter Einzelschlüssel). Netzwerktyp/MTU/Timer je Link konsistent.
- **BGP** wo Multi-Homing/Policy nötig; klare AS-/Community-Struktur, Prefix-Filter an jeder eBGP-Grenze.
- **Multicast:** RP-Platzierung an eine **stabile, redundierbare** Adresse (Anycast-RP für Redundanz),
  nie an eine Rückbau-Legacy-Adresse. BSR/Static bewusst wählen.
- **First-Hop-Redundanz:** HSRP/VRRP für Gateways in Client-/Server-Zonen; VIP-Konsistenz.

### Firewall-Zonen & Zero-Trust
- Zonenmodell (PAN-OS-Zonen / ZBFW / Segment-ACLs) mit Default-Deny und least-privilege-Übergängen,
  spezifisch vor allgemein, Logging auf Deny. Ost-West-Verkehr im Server-Segment nicht ungefiltert
  lassen (Mikrosegmentierung nach Bedarf/Schutzbedarf).
- Zero-Trust als Richtung, nicht als Produkt: Identität + Kontext vor Zugriff, Mgmt-Plane getrennt und
  am stärksten geschützt.

### Resilienz
- Redundanz **über Fehlerdomänen hinweg**: LACP-Member auf verschiedene Chassis/Stack-Member;
  Stack/VSS/StackWise-Virtual für Core-Redundanz; dual-homed Access wo der Schutzbedarf es trägt.
- **STP deterministisch:** Root und Secondary-Root per Priorität festnageln (nicht dem Zufall der
  Bridge-ID überlassen); Root-Guard an der Access-Kante, Loop-/BPDU-Guard passend.
- Ausfallpfade **testbar** halten (geparkte Redundanz ist nur dann Redundanz, wenn der Umschaltweg
  erprobt ist).

## Arbeitsweise

1. **Anforderung klären:** Zonen/Schutzbedarf, Standorte, Dienste, erwartetes Wachstum, Vorgaben
   (Zonenstandard, Compliance/Grundschutz, vorhandene Hardware).
2. **Ist erfassen** (falls Umbau): vorhandene Topologie/Configs über `net-diagnose` verstehen, SPOFs und
   Abhängigkeiten benennen.
3. **Design vorschlagen:** Zonen-/Adress-/Routing-/Redundanzkonzept, Design-Entscheidungen begründen und
   belegen (`net-reference`), Trade-offs offenlegen (nicht die eine „richtige" Lösung verkaufen, wo es
   eine Abwägung ist).
4. **Migrationspfad:** bei Umbau die Reihenfolge mit Blick auf Blast-Radius und Abhängigkeiten (was muss
   *vor* was), Rückbau-Abhängigkeiten zuerst auflösen.
5. **Übergabe an `net-config`** für die konkrete, validierte Umsetzung; Live-Ausrollen über `net-operate`
   (gestuft, Rollback-Netz). Design selbst ändert nichts am Gerät.

## Dokumentenorientiert

Ergebnis ist ein übernehmbares Design-Dokument: Zonen-/VLAN-Tabelle, Adressplan, Routing-/Redundanz-Skizze
(als Mermaid-Diagramm, wo eine Topologie hilft), Design-Entscheidungen mit Begründung/Quelle und offenen
Trade-offs. Belegt vs. Erfahrung/unsicher trennen.
