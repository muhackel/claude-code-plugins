# christian — Backlog

Offene Punkte oben, umgesetzte darunter (jüngste zuerst).

---

## OFFEN — spätere Erweiterungen

- **VyOS-Tiefe**: Über das rudimentäre Niveau hinaus — VyOS-Config-Modell (set-Syntax, commit/compare/
  rollback), VPN- und Routing-Stanzas als eigenständiger Plattform-Pfad.
- **pfSense/OPNsense**: BSD-basierte Firewall-/Router-Appliances als weiterer Plattform-Zweig
  (pf statt nftables, Web-/Config-XML-Modell).
- **Konkrete Appliance-Image-Builds**: reproduzierbare Router-Images bauen (OpenWrt ImageBuilder,
  NixOS-Image via nixie), nicht nur Config-Entwurf.
- **DMVPN-artige FRR-Multipoint-Overlays**: dynamische Multipoint-VPN-Topologien (Hub-and-Spoke mit
  automatischem Spoke-to-Spoke) über FRR/WireGuard/GRE statt statischer Punkt-zu-Punkt-Tunnel.
- **PMTU-/MSS-Tooling**: Diagnose und automatisiertes Clamping für Path-MTU-Probleme über Tunnel
  (MSS-Clamping-Regeln, PMTU-Discovery-Blackhole-Erkennung).

---

## ✅ UMGESETZT (2026-07-18): Gerüst + Persona + 5 Skills

Plugin `christian` angelegt: Persona `agents/christian.md` (Eiserne Regeln: Reference-first,
Blast-Radius-Respekt, Krypto opinionated + belegt, Plattform-Ehrlichkeit, verifiziert-vs-unsicher),
`/christian`-Command, README. Fünf Skills als Achsen der Persona:
- **`vpn-reference`** — Reference-first-Disziplin für OpenVPN/WireGuard/strongSwan/FRR/nftables-Manpages.
- **`openvpn`** — OpenVPN-Kern-Expertise (Server/Client, Krypto-Suite, tls-crypt, Routing/Push).
- **`vpn-tunnel`** — protokoll-übergreifender Tunnel-Entwurf (Site-to-Site vs. Client-Server).
- **`router-appliance`** — Linux-Router-Appliance (nftables, FRR, Persistenz, gestufter Live-Zugriff).
- **`wan-link`** — sichere WAN-Kopplung (Routing, Firewall-Zonen, PMTU/MSS, Failover).

Kooperationen: nixie für NixOS-Umsetzung/Deploy, bruce für Krypto-/Sicherheitsbewertung (jeweils per
Briefing → Hauptagent spawnt). Abgrenzung: kommerzielle Hardware → bertram.
