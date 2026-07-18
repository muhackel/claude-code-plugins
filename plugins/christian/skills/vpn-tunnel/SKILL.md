---
name: vpn-tunnel
description: "Breite VPN-Landkarte jenseits OpenVPN: WireGuard (wg/wg-quick, AllowedIPs-Routing, PSK, Kill-Switch, PersistentKeepalive), IPsec (strongSwan swanctl / Libreswan, IKEv2, Site-to-Site vs. Transport, AEAD/PFS/NAT-T), L2-über-L3 (EtherIP, GRETAP, L2TPv3, VXLAN) mit MTU-Overhead und wann L2 wirklich nötig ist, Mesh-Overlays self-hosted (Headscale, NetBird, Netmaker, ZeroTier, Nebula) und SSL-VPN (OpenConnect/ocserv, SoftEther). Je Technik: wann/Aufbau-Kern/Krypto-Härtung/Fallstricke mit Quellen-Anker. Nutzen, wenn eine VPN-Technik auszuwählen oder aufzubauen ist. Krypto-Härtung über bruce/TR-02102; OpenVPN-Details im openvpn-Skill; Optionen per Projekt-Doku/Manpage verifizieren."
---

# VPN-Tunnel — die breite Palette

Dichte Praktiker-Landkarte, kein Voll-Tutorial. Je Technik: **wann**, **Aufbau-Kern**, **Krypto-Härtung**,
**Fallstricke** — mit Quellen-Anker. Exakte Optionen gegen die Projekt-Doku/Manpage der Zielversion
verifizieren (via `vpn-reference`). Krypto-Bewertung ist opinionated, die Freigabe holt `bruce` aus
TR-02102. OpenVPN-Tiefe steht im `openvpn`-Skill.

## WireGuard

Quelle: wireguard.com/quickstart, `wg(8)`, `wg-quick(8)`.

- **Wann:** schlank, schnell, im Kernel; erste Wahl für Punkt-zu-Punkt und Roadwarrior über L3. Kein L2.
- **Aufbau-Kern:** Interface mit `PrivateKey` + `Address`; je Gegenstelle eine `[Peer]`-Sektion mit
  `PublicKey`, `Endpoint`, `AllowedIPs`. `wg-quick up <if>` liest die `.conf` und setzt Routen.
- **Routing = AllowedIPs:** doppelte Rolle — (a) welche Quell-IPs vom Peer akzeptiert werden
  (Crypto-Routing) und (b) welche Ziele in den Tunnel geroutet werden. `AllowedIPs = 0.0.0.0/0, ::/0`
  = Full-Tunnel. Überlappende AllowedIPs über mehrere Peers = Konflikt (letzte gewinnt).
- **Krypto-Härtung:** feste, moderne Suite (Curve25519, ChaCha20-Poly1305) — **nicht konfigurierbar**,
  das ist Absicht. `PresharedKey` optional als zusätzliche symmetrische Schicht (PQ-Vorsorge/Defense-in-
  Depth). Schlüsselrotation manuell.
- **Fallstricke:** `PersistentKeepalive = 25` nötig, wenn ein Peer hinter NAT sitzt (hält das Mapping
  offen). **Kill-Switch** über `wg-quick`-`PostUp`/`PostDown`-Firewallregeln oder `AllowedIPs`-Fwmark —
  kein eingebauter Fail-Closed. MTU-Overhead (~60/80 Byte) beachten. Kein L2, kein Broadcast/Multicast.

## IPsec (strongSwan / Libreswan)

Quellen: docs.strongswan.org (swanctl), libreswan.org/wiki.

- **Wann:** Interop mit Fremdgeräten (Firewalls, Cloud-Gateways), Standard-Site-to-Site, wo IKEv2
  gefordert ist. strongSwan `swanctl`/`swanctl.conf` ist der moderne Weg (löst `ipsec.conf` ab);
  Libreswan nutzt `conn`-Stanzas in `ipsec.conf`.
- **Aufbau-Kern:** **IKEv2 bevorzugt** (robuster, MOBIKE, sauberes Rekeying — IKEv1 nur für Legacy-Peer).
  **Site-to-Site** (Tunnel-Mode, ganze Subnetze in `local_ts`/`remote_ts`) vs. **Transport-Mode** (nur
  Host-zu-Host, oft als Träger für GRE/L2TP). Zwei Phasen: IKE-SA (Phase 1) + CHILD-SA (Phase 2).
- **Krypto-Härtung:** **AEAD-Proposals** (AES-GCM), **PFS** einschalten (eigene DH-Gruppe für die
  CHILD-SA), moderne **DH-Gruppen** (ECP/MODP ausreichender Größe), schwache Legacy-Proposals (3DES,
  MODP-1024, SHA1) raus. **NAT-T** (UDP-4500-Encapsulation) automatisch bei NAT dazwischen. Für die
  konkrete Proposal-Härtung an `bruce` / **TR-02102-3** (IPsec/IKE) verweisen.
- **Fallstricke:** Traffic-Selector-/Subnetz-Mismatch = CHILD-SA kommt nicht zustande. Proposal-Mismatch
  zwischen den Enden = Phase-1-Fehler. Rekeying-/Lifetime-Asymmetrie. NAT ohne NAT-T. Exakte
  Config-Syntax (swanctl vs. ipsec.conf) per Doku verifizieren — die beiden Stacks sind nicht
  syntaxkompatibel.

## L2-über-L3-Suite

**Zuerst fragen: braucht es wirklich L2?** L2-Overlays transportieren Broadcast/Multicast und
Nicht-IP-Protokolle über L3 — nötig für Bridging, gemeinsame Broadcast-Domäne, manche Cluster-/Legacy-
Anwendungen. Sonst **L3 bevorzugen** (weniger Overhead, keine Broadcast-Flut über die WAN-Strecke). Alle
vier addieren Encap-Overhead → **MTU/`mssfix` beachten**, sonst Fragmentierung/Blackhole.

| Technik | Encap | NAT | Kern | Wann |
|---------|-------|-----|------|------|
| **EtherIP** | Ethernet-in-IP (RFC 3378), IP-Proto 97 | schlecht (kein Port) | minimal, unverschlüsselt | L2 über bereits gesichertem Träger (z.B. in IPsec-Transport) |
| **GRETAP** | Ethernet-in-GRE | mäßig | GRE mit L2-Payload, **in Bridge einhängen** | einfache L2-Bridge über L3, Linux-nativ |
| **L2TPv3** | L2-Pseudowire, **UDP-Encap möglich** | **gut** (UDP) | Pseudowire, statisch oder gesignalt | L2 über NAT/Internet, wo GRE nicht durchkommt |
| **VXLAN** | Ethernet-in-UDP (VNI 24-Bit) | gut (UDP) | `VNI` + Multicast **oder** Unicast-FDB (statische Peers/EVPN) | viele Segmente/Skalierung, DC-Overlay |

- **GRETAP** wird als L2-Interface in eine Linux-Bridge gehängt (im Gegensatz zu GRE = L3-Punkt-zu-Punkt).
- **L2TPv3** ist der NAT-freundliche Weg (UDP-Encap), wo EtherIP/GRE an fehlenden Ports scheitern.
- **VXLAN** skaliert am besten (24-Bit VNI, Unicast-FDB/EVPN statt Multicast) — Overkill für einen
  einzelnen Punkt-zu-Punkt-Link.
- **Keine dieser vier verschlüsselt** — über IPsec (Transport-Mode) oder WireGuard tunneln, wenn der
  Träger nicht vertrauenswürdig ist. Exakte `ip link add … type {gretap,vxlan,l2tp}`-Syntax per
  Manpage/`ip-link(8)` verifizieren.

## Mesh-Overlays (self-hosted)

Quellen: jeweilige Projekt-Doku (Headscale, NetBird, Netmaker, ZeroTier, Nebula).

- **Wann:** viele Knoten, dynamische Peers, NAT-Traversal ohne manuelles Port-Forwarding, zentrale ACLs.
  Statt N² manueller Tunnel eine Control-Plane, die Peers automatisch verdrahtet.

| Overlay | Datenebene | Control-Plane | Auswahlkriterium |
|---------|-----------|---------------|------------------|
| **Headscale** | WireGuard | self-hosted Tailscale-Control (offen) | Tailscale-Ökosystem ohne SaaS, ACL via Policy |
| **NetBird** | WireGuard | self-hosted Coordination + IdP/SSO | WireGuard-Mesh mit SSO, Zero-Config-NAT |
| **Netmaker** | WireGuard (kernel) | self-hosted Server | Performance/Kernel-WG, feingranular, mehr Ops |
| **ZeroTier** | eigenes (L2-fähig) | self-hosted Controller möglich | **L2-Overlay** (Broadcast), einfache Nutzung |
| **Nebula** | eigenes (Noise) | **koordinationsserverlos**, eigene **CA** | **zertifikatsbasiert**, Lighthouse statt Control-Plane |

- **Auswahlachsen:** WireGuard-basiert (Headscale/NetBird/Netmaker) vs. eigenes Protokoll (ZeroTier L2,
  Nebula Noise); **Koordinationsserver** (Control-Plane) vs. **PKI-basiert** ohne ständige Control-Plane
  (Nebula, eigene CA); L3-only vs. **L2-Overlay** (ZeroTier); NAT-Traversal-Qualität; ACL-Modell.
- **Fallstricke:** self-hosted heißt **du** betreibst die Control-Plane/CA — Verfügbarkeit und
  Key-/CA-Schutz sind deine Aufgabe. ACL-Fehlkonfiguration öffnet das ganze Mesh. Version der
  Projekt-Doku prüfen — das Feld bewegt sich schnell.

## SSL-VPN (Client-Access durch restriktive Netze)

Quellen: ocserv-Doku (OpenConnect), SoftEther-Doku.

- **Wann:** Roadwarrior-Zugang durch restriktive Netze/Proxies, wo UDP/ESP geblockt ist — TCP/443 sieht
  aus wie HTTPS und kommt meist durch. Nicht erste Wahl für Site-to-Site.
- **OpenConnect/ocserv:** offener AnyConnect-kompatibler Server (`ocserv`) + `openconnect`-Client;
  TLS-basiert, TCP + optional DTLS für Durchsatz.
- **SoftEther:** Multi-Protokoll (inkl. SSL-VPN über HTTPS, L2-fähig), gut durch Firewalls, aber
  eigener Stack mit eigener Betriebslast.
- **Fallstricke:** TCP-over-TCP-Meltdown bei reinem TCP-Transport (DTLS/UDP-Datenkanal nutzen, wo
  möglich). Krypto-Härtung wie bei jedem TLS-Dienst (Suites/Version) — über `bruce`/TR-02102 bewerten.

## Verweise & Read-only

- **WireGuard/OpenVPN-Tiefe:** OpenVPN im `openvpn`-Skill; WireGuard-Details hier bzw. `wg-quick(8)`.
- **Krypto-Härtung** aller Techniken opinionated hier + Freigabe über `bruce` (`gs-krypto`, TR-02102).
- Config-Entwurf/Auswahl ist read-only. Tunnel/Overlay/Bridge live schalten läuft über die
  `wan-link`/`router-appliance`-Doktrin (Bestätigung + Rollback-Netz), nie beiläufig.
