# Routing & Multi-WAN auf pfSense / OPNsense

Referenz zu `bsd-firewall`, lesen vor statischen Routen, Gateway-Groups (Failover/Load-Balance), Policy-Routing, der `reply-to`-Semantik oder dem FRR-Paket.

## Routing & Multi-WAN

Quellen-Anker: `docs.netgate.com` (Routing/Multi-WAN/FRR), `docs.opnsense.org` (Dynamic Routing/Multi-WAN).

- **Statische Routen** für Stub-/Single-Uplink. Dynamisches Routing erst, wenn Redundanz/mehrere Router
  es rechtfertigen (gleiche Faustregel wie in `router-appliance`).
- **Gateway-Groups (Multi-WAN):** jedes Gateway bekommt ein **Tier**. **Gleiches Tier = Load-Balance**,
  **unterschiedliches Tier = Failover** (niedrigeres/höheres Tier zuerst — Zuordnung **per Doku
  verifizieren**). Der **Trigger Level** (pfSense: z.B. Member Down / Packet Loss / High Latency)
  bestimmt, **wann** ein Gateway als tot gilt. OPNsense: bis zu fünf Tiers.
- **Policy-Routing:** die Gateway-Group wird im **Gateway-Feld einer Firewall-Regel** ausgewählt →
  passender Verkehr nimmt die Group statt des Default-Gateways. **DNS/Firewall-eigener Verkehr** braucht
  eine separate Regel aufs Default-Gateway, sonst Routing-Schleifen.
- **`reply-to`-Falle:** pf setzt auf WAN-Regeln automatisch `reply-to`, damit Antworten **dieselbe** WAN
  hinausgehen, über die die Anfrage kam — Grundlage für symmetrisches Multi-WAN. Bei ungewöhnlichen
  Topologien (asymmetrischer Rückweg, Transit über ein anderes Interface) kann das Verkehr fehlleiten;
  `reply-to` gezielt abschalten ist möglich (**per Doku verifizieren**).
- **FRR** (Paket/`os-frr`-Plugin) bringt **OSPF (v2)**, **OSPF6/OSPFv3**, **BGP** (IPv4/IPv6), **BFD**
  und **ECMP**; OPNsense listet zusätzlich **RIP** (Protokoll-Verfügbarkeit je Plattform/Version **per
  Doku verifizieren**). Bezug zur FRR-Ebene aus `router-appliance` — dieselbe FRRouting-Basis, hier über
  die GUI konfiguriert.
