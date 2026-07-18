---
name: wan-link
description: "Design-Ebene für sichere WAN-Verbindungen zwischen Netzen/Standorten: Kopplungs-Szenario → Tech-Wahl (Site-to-Site: WireGuard/IPsec/OpenVPN; Road-Warrior: OpenVPN/WireGuard/OpenConnect; Multi-Site-Mesh: Headscale/NetBird/Netmaker/Nebula; durch NAT/CGNAT: UDP-Encap/keepalive/TCP-Fallback/SSL-VPN). L2-vs-L3-Kopplung (GRETAP/L2TPv3/VXLAN/EtherIP nur wenn wirklich L2). Krypto-Härtung (AEAD/PFS, keine Legacy; bei Unsicherheit bruce/BSI TR-02102). Failover/Redundanz (mehrere Tunnel, Metrik/Priorität, BFD/Health-Check). MTU/Fragmentierung (Overhead, PMTU-Blackhole, MSS-Clamping, tun-mtu/mssfix). Blast-Radius: ein WAN-Change kappt den Standort → Rollback-Netz. Umsetzung → vpn-tunnel/openvpn/router-appliance. Nutzen, wenn eine Standort-/Netzkopplung geplant oder bewertet wird — die Ebene 'welche Kopplung', bevor die Umsetzung sie baut."
---

# WAN-Link — wie die Kopplung aussehen soll

Die Design-Ebene **über** der Tunnel-Config: erst die Architektur (welche Tech, L2 oder L3, Krypto,
Redundanz, MTU), dann die Umsetzung (`vpn-tunnel`, bei OpenVPN `openvpn`; Router-/Firewall-/Routing-Teil
`router-appliance`). Tech- und Krypto-Entscheidungen mit der offiziellen Doku belegen (`vpn-reference`) —
nicht als Geschmack behaupten. Ergebnis ist ein **Dokument** (Kopplungskonzept: Tech-Wahl mit Begründung,
Adress-/Routing-Skizze, Krypto-Suite, Failover-, MTU- und Rollback-Plan), kein Bauch. **Ein WAN-Change
kann einen ganzen Standort aussperren** — Blast-Radius ist hier Leitprinzip, nicht Fußnote.

## Kopplungs-Szenario → Tech-Wahl

Erst das **Szenario** benennen, dann die Technik. Umsetzung jeweils über `vpn-tunnel`/`openvpn`.

| Szenario | Charakter | Erste Wahl | Alternativen / wann |
|----------|-----------|------------|---------------------|
| **Site-to-Site** | feste Kopplung, wenige Standorte | **WireGuard** (schlank, schnell, wenig State) | **IPsec/strongSwan** (Vendor-Interop, IKEv2, Compliance-Erwartung); **OpenVPN** (wo TLS-PKI/Flexibilität/Legacy-Gegenstelle) |
| **Road-Warrior / Client-Access** | viele wechselnde Clients, dynamische IPs | **WireGuard** (mobil, schneller Reconnect) oder **OpenVPN** (reife Client-Basis, PKI, granulare Push-Policy) | **OpenConnect** (SSL-VPN, kommt durch restriktive Netze, AnyConnect-kompatibel) |
| **Multi-Site-Mesh** | viele Standorte, jeder-mit-jedem | **Mesh-Overlay:** Headscale (self-hosted Tailscale/WG), NetBird, Netmaker (WG-basiert), **Nebula** (eigenes Protokoll, Lighthouse) | Full-Mesh aus einzelnen WG-Tunneln skaliert nicht (n²) — ab ~4–5 Standorten Overlay |
| **Durch NAT / CGNAT / restriktive Netze** | keine eingehende Erreichbarkeit, Ports gefiltert | **UDP-Encapsulation + persistent-keepalive** (WG/IPsec-NAT-T) | **TCP-Fallback** (OpenVPN `proto tcp`) / **SSL-VPN** (OpenConnect, Port 443) wo nur 443/tcp durchkommt |

Auswahl-Leitplanken:
- **WireGuard** als Default für neue Site-to-Site/Mesh — modern, kleine Angriffsfläche, feste moderne
  Krypto (keine Cipher-Wahl = keine Fehlkonfiguration). Grenze: keine dynamische Push-Policy, kein
  natives „Client bekommt Routen zugewiesen" (Overlay/Mgmt-Layer löst das).
- **IPsec/strongSwan** wenn die Gegenstelle Vendor-Hardware ist, IKEv2/Interop oder eine
  Compliance-Erwartung (BSI/ISO) IPsec verlangt.
- **OpenVPN** wenn TLS-PKI, feingranulare Server-Push-Policy, TCP-Fallback oder eine Legacy-Gegenstelle
  gebraucht wird. Details/Config in `openvpn`.
- **Mesh-Overlays** nehmen dir Key-Distribution und Full-Mesh-Routing ab — dafür ein zusätzlicher
  Kontroll-Layer (Koordinationsserver) als Abhängigkeit/SPOF; self-hosted (Headscale) vs. dessen Ausfall
  abwägen.

Feature-Vergleich, Portnummern und exakte Direktiven **per `vpn-reference` / Projekt-Doku verifizieren** —
nicht aus dem Gedächtnis.

## L2- vs. L3-Kopplung

Default ist **L3** (geroutet). L2 (gleiche Broadcast-Domäne über den WAN-Link) nur, wenn es einen echten
Grund gibt — und dann mit offenen Augen:

- **Wann wirklich L2:** gemeinsame Broadcast-Domäne zwingend nötig — Legacy-/Nicht-IP-Protokolle,
  L2-abhängige Cluster/Heartbeats, Broadcast-Discovery, IP-Mobilität ohne Umadressierung. Dann
  **GRETAP** (L2-GRE), **L2TPv3**, **VXLAN** oder **EtherIP** + Bridge über den Tunnel.
- **Sonst L3:** skaliert (kein Broadcast über den WAN-Link), kleinere Fehlerdomäne, weniger Overhead.
  Der Standort bekommt ein eigenes Subnetz, geroutet über den Tunnel.

Trade-offs von L2-über-WAN klar benennen:
- **Broadcast/Flooding** läuft über den (teureren, latenteren) WAN-Link — ARP-Sturm/Loop trifft **beide**
  Standorte. Ein STP-Problem wird standortübergreifend.
- **Fehlerdomäne** wird zusammengelegt: ein L2-Problem an einem Standort kippt die gemeinsame Domäne.
- **MTU:** L2-Encap (GRETAP + Ethernet-Header + Krypto) frisst besonders viel — MTU-/MSS-Planung
  zwingend (siehe unten).
- Verschlüsselung: reines GRETAP/L2TPv3/VXLAN ist **unverschlüsselt** — über einen verschlüsselten
  Tunnel (WG/IPsec) legen oder IPsec-Transport darunter. Nie L2-Klartext übers WAN.

Faustregel: **L2 nur, wenn L3 die Anforderung nachweislich nicht erfüllt** — und dann so klein wie möglich.

## Krypto-Härtung (opinionated)

Sichere Defaults durchsetzen, Empfehlung mit der Referenz belegen:
- **Moderne AEAD-Cipher:** AES-GCM (128/256) oder ChaCha20-Poly1305. Kein AES-CBC-ohne-AEAD wo
  vermeidbar, **kein BF-CBC, kein 3DES, kein RC4**.
- **Perfect Forward Secrecy:** ephemere DH/ECDH — WG hat es baked-in; IPsec IKEv2 mit PFS-DH-Gruppe;
  OpenVPN über TLS mit ECDHE. DH-Gruppe **nicht unter 2048 bit** (bzw. moderne EC-Kurve).
- **Protokoll-Hygiene:** kein SSLv3/TLS 1.0/1.1, **kein IKEv1** wo IKEv2 geht. OpenVPN-Control-Channel
  mit `tls-crypt`/`tls-auth` härten. `cipher` vs. `data-ciphers` versionsabhängig (OpenVPN 2.4 vs. 2.6) —
  **per `openvpn`/Manpage verifizieren**.
- Schwache Config = **markiertes Risiko**, nicht stillschweigend durchwinken.
- **Bei echter Krypto-Unsicherheit** (Suite-Bewertung, Compliance-Härtung, konkrete Algorithmen-/
  Schlüssellängen-Vorgabe): **bruce** konsultieren (BSI **TR-02102** als maßgebliche Kryptovorgabe).
  Du startest bruce nicht selbst — schreib ein knappes **Briefing** (Tech, geplante Suite, Kontext/
  Schutzbedarf, konkrete Frage) und **empfiehl dem Hauptagenten**, bruce zu spawnen.

## Failover / Redundanz

Ein einzelner Tunnel ist ein SPOF für die Standortanbindung:
- **Mehrere Tunnel** über getrennte Uplinks/Pfade (idealerweise verschiedene Provider). Endpunkte so
  wählen, dass nicht beide am selben Uplink/Gerät hängen (Fehlerdomäne trennen).
- **Routing-Metrik/Priorität:** Primär-/Backup-Tunnel über Routen-Metrik oder Protokoll-Präferenz
  (statisch mit Metrik, oder FRR/BIRD-Präferenz — `router-appliance`). Bei ECMP bewusst entscheiden
  (Load-Sharing vs. aktiv/passiv).
- **Health-Check / schnelle Erkennung:** **BFD** (in FRR/BIRD) für Sub-Sekunden-Ausfallerkennung auf
  gerouteten Tunneln; sonst applikativer Ping-/Reachability-Check, der die Route umzieht. Reiner
  Link-State reicht nicht — der Tunnel kann „up" sein, während die Gegenstelle weg ist.
- **Reconnect-Verhalten** der Tech kennen: WG persistent-keepalive/roaming (reconnected leise nach
  IP-Wechsel); OpenVPN `keepalive`/`ping-restart`; IPsec DPD (Dead-Peer-Detection). Werte
  **per Referenz verifizieren**.
- Failover-Pfad **testbar** halten — geparkte Redundanz ist nur Redundanz, wenn der Umschaltweg erprobt
  ist.

## MTU / Fragmentierung

Jeder Tunnel kostet Header — die häufigste stille WAN-Störung ist ein PMTU-Blackhole:
- **Overhead je Tech** einplanen (Encap + Krypto): WireGuard, IPsec (Transport/Tunnel, mit/ohne NAT-T),
  OpenVPN (UDP vs. TCP), GRE/GRETAP, VXLAN — jeder hat anderen Overhead. **Konkrete Byte-Werte per
  `vpn-reference`/Doku nachschlagen**, nicht aus dem Kopf ansetzen.
- **PMTU-Blackhole:** wird ICMP „Fragmentation Needed"/„Packet Too Big" auf dem Pfad gefiltert (häufig),
  scheitert Path-MTU-Discovery still — kleine Pakete/Handshake klappen, große TCP-Transfers hängen.
  Symptom: „SSH geht, Datei-Download friert ein".
- **Gegenmaßnahmen:** **MSS-Clamping** (`tcp option maxseg`, siehe `router-appliance`) klemmt TCP-MSS an
  die Tunnel-MTU — die robusteste Maßnahme, weil sie nicht auf ICMP angewiesen ist. Bei OpenVPN
  zusätzlich `tun-mtu`/`mssfix` (Werte **per `openvpn`/Manpage verifizieren**). Tunnel-MTU bewusst
  setzen statt Default zu vertrauen.
- L2-Kopplungen (GRETAP/VXLAN) haben den größten Overhead → MTU-Planung dort zwingend.

## Blast-Radius / Deploy

Ein WAN-Change kappt im Fehlerfall den ganzen Standort — der Change **ist** das Risiko. Read-only-Analyse
zuerst (Ist-Tunnel, Routen, Firewall), dann gestuft mit Rollback-Netz:

1. **Config-Backup** vor dem Schnitt (Tunnel-Config, `ip route save`, `nft list ruleset`).
2. **SSH-keepalive-Fenster** offen halten; die Steuer-Verbindung nicht als Erstes durch den neuen Tunnel
   legen.
3. **`at`-getriggerter Auto-Rollback:** vor dem Cutover einen `at`-Job schedulen, der nach n Minuten die
   alte Config zurückspielt / den alten Pfad wiederherstellt — sperrt der Change dich aus, holt der Job
   den Standort zurück. Nach bestätigtem Test canceln.
4. **Erst testen, dann persistieren:** neuen Tunnel/Route transient aufbauen, Erreichbarkeit **beider
   Richtungen** prüfen (nicht nur „Tunnel up", sondern Nutzverkehr + Rückweg), **dann** persistieren.
   Default-Route erst umschwenken, wenn der neue Pfad verifiziert ist.
5. **Ziel-System benennen und bestätigen lassen**, bevor irgendetwas Schreibendes läuft.

**Übergabe:** Design steht → `vpn-tunnel`/`openvpn` liefert die konkrete, geprüfte Tunnel-Config,
`router-appliance` den Firewall-/Routing-/MSS-/Failover-Teil und das gestufte Live-Ausrollen. Dieses Skill
ändert selbst nichts am Gerät.

## Dokumentenorientiert

Ergebnis ist ein übernehmbares Kopplungskonzept: Tech-Wahl mit Begründung und Quelle, L2/L3-Entscheidung
mit Trade-offs, Krypto-Suite, Adress-/Routing-Skizze (Mermaid, wo eine Topologie hilft), Failover- und
MTU-Plan, Rollback-Plan. Belegt vs. Erfahrung/unsicher trennen.
