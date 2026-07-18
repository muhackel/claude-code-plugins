---
name: net-config
description: "Netzwerk-Konfiguration erzeugen, vor der Anwendung validieren und zwischen Vendor-Dialekten übersetzen. Pre-Deployment-Checks (dangerous commands, Subnet-Overlap, doppelte IPs, ACL-Logikfehler, fehlendes commit/write). Übersetzung über die Konzept-Ebene (Cisco IOS/IOS-XE ↔ MikroTik RouterOS ↔ Palo Alto PAN-OS ↔ HP/Aruba ↔ Juniper Junos), nicht als Token-Mapping. Best-Practice-Templates für VLAN-Segmentierung, Trunk/Access, Firewall-Zonen, Management-Hardening. Nutzen beim Erzeugen oder Portieren von Configs."
---

# Net-Config — erzeugen, prüfen, übersetzen

Config wird **erst validiert, dann angewendet**. Syntax je Vendor/Version über `net-reference` belegen —
CLI-Details nie aus dem Gedächtnis. Anwenden am Live-Gerät läuft über `net-operate` (Bestätigung +
Rollback-Netz), nie beiläufig aus diesem Skill heraus.

## Pre-Deployment-Validierung (immer vor Ausgabe)

Jede erzeugte oder portierte Config gegen diese Checks laufen lassen und Befunde **explizit** benennen:

- **Dangerous Commands** — Kommandos, die die Verbindung/das Netz sofort kappen können, gesondert
  markieren: Interface-`shutdown` auf dem Mgmt-/Uplink-Pfad, `no` auf einer aktiven ACL/NAT-Regel,
  Änderung von Routing-Protokoll/Default-Route, `write erase`/`reset`/`factory`, Passwort-/AAA-Änderung,
  die den eigenen Zugang betrifft. → Reihenfolge so wählen, dass der eigene Pfad **zuletzt** angefasst wird.
- **Subnet-Overlap** — neue Subnetze/VLANs/Routen gegen bestehende prüfen; Überlappungen und
  Prefix-Konflikte (z.B. specific vs. summary) benennen.
- **Doppelte IPs / VLAN-IDs / Interface-Zuordnung** — kein Duplikat auf L3-Interfaces, VRRP/HSRP-VIPs,
  DHCP-Scopes; keine widersprüchliche VLAN-zu-Port-Zuordnung.
- **ACL-/Policy-Logik** — Reihenfolge (erste Übereinstimmung gewinnt), implizites `deny` am Ende,
  Richtung (in/out), Objekt-/Zonen-Zuordnung. Eine Regel unterhalb eines breiteren Match ist tot.
- **Vollständigkeit** — fehlt der Persistenz-Schritt (`write memory`/`copy run start`, RouterOS ist
  auto-persistent, PAN-OS/Junos brauchen `commit`)? Fehlt ein Gegenstück (Route ohne Return-Route,
  Trunk ohne allowed-VLAN)?

Befunde als kurze Liste ausgeben, bevor die Config als anwendbar gilt.

## Dialekt-Übersetzung — über die Konzept-Ebene

Nie Token-für-Token übersetzen. Erst das **Ziel** benennen (z.B. „Access-Port in VLAN 20 mit
Port-Security auf 2 MACs"), dann in der Zielsyntax formulieren — Konzepte haben zwischen Vendoren
unterschiedliche Struktur:

- **Config-Modell:** Cisco = zeilenbasiert, laufend aktiv; RouterOS = objekt-/menübasiert (`/interface
  bridge vlan add ...`), auto-persistent; PAN-OS/Junos = **Candidate-Config mit `commit`** (Änderung
  wird erst mit commit aktiv — anderes Sicherheits- und Rollback-Verhalten).
- **VLAN/Bridging:** Cisco `switchport` vs. RouterOS Bridge-VLAN-Filtering vs. Aruba CX — dasselbe Ziel,
  strukturell verschieden. Native/untagged-VLAN-Semantik je Vendor prüfen.
- **Firewall:** Cisco ACL/ZBFW vs. PAN-OS Zonen+Security-Policies vs. RouterOS `/ip firewall filter` —
  zustandsbehaftet vs. -los, Zonen- vs. Interface-Bezug beachten.
- **Was nicht 1:1 geht** ausdrücklich kennzeichnen (Feature fehlt beim Ziel-Vendor, anderes
  Default-Verhalten, andere Reihenfolge-Semantik) — nicht glattbügeln.

## Best-Practice-Templates

Als Startpunkte, immer an den konkreten Fall angepasst und gegen die Referenz belegt:

- **VLAN-Segmentierung:** Access-Ports mit definiertem VLAN + `portfast`/edge + BPDU-Guard; Trunks mit
  explizit `allowed vlan` (kein `all`); Native-VLAN bewusst und beidseitig gleich; ungenutzte Ports in
  ein Blackhole-VLAN + `shutdown`.
- **Trunk/Access:** klare Trennung, kein Auto-Negotiation von Trunk-Mode (`switchport mode` fest);
  DTP wo möglich aus.
- **Firewall-Zonen:** Default-Deny, explizite Allow-Regeln von spezifisch nach allgemein, Logging auf
  Deny; Management aus eigener Zone/eigenem VLAN.
- **Management-Hardening:** SSH statt Telnet, Mgmt-Zugriff per ACL/allowed-address auf Admin-Netz
  begrenzt, unnötige Dienste (HTTP-Server, CDP/LLDP wo unnötig) aus, sichere NTP-/Logging-Quellen.
  Empfehlungen gegen Vendor-Hardening-Guide / CIS-Benchmark belegen (`net-reference`).

## Ausgabeform

Config als zusammenhängenden, kommentierten Block; darüber die Validierungs-Befunde; dazu, für welchen
Vendor/welche Version sie gilt und welche Kommandos vor der Anwendung noch zu verifizieren sind.
