# christian — Backlog

Offene Punkte oben, umgesetzte darunter (jüngste zuerst).

---

## OFFEN — spätere Erweiterungen

- **VyOS-Tiefe**: Über das rudimentäre Niveau hinaus — VyOS-Config-Modell (set-Syntax, commit/compare/
  rollback), VPN- und Routing-Stanzas als eigenständiger Plattform-Pfad.
- **Konkrete Appliance-Image-Builds**: reproduzierbare Router-Images bauen (OpenWrt ImageBuilder,
  NixOS-Image via nixie), nicht nur Config-Entwurf.
- **DMVPN-artige FRR-Multipoint-Overlays**: dynamische Multipoint-VPN-Topologien (Hub-and-Spoke mit
  automatischem Spoke-to-Spoke) über FRR/WireGuard/GRE statt statischer Punkt-zu-Punkt-Tunnel.
- **PMTU-/MSS-Tooling**: Diagnose und automatisiertes Clamping für Path-MTU-Probleme über Tunnel
  (MSS-Clamping-Regeln, PMTU-Discovery-Blackhole-Erkennung).

---

## ✅ UMGESETZT (2026-10-10): 0.4.0 — Rückbau des Lazy-Musters, Skills offen

Die Sperren aus 0.3.0 sind weg (kein `disable-model-invocation`, keine `agents/openai.yaml`), weil Agenten
in Claude Code keinen Sperrschalter haben und die gesperrten Skills nur Read-Roundtrips im Agenten
kosteten. Skill-Descriptions auf 150 bis 250 Zeichen gekürzt. `vpn-reference` und `vpn-tunnel` per
`skills:` vorgeladen, `openvpn`, `router-appliance`, `bsd-firewall` und `wan-link` holt Christian über das
Skill-Tool (neu in `tools:`). `router-appliance` in Kern (nftables, Appliance-Denke, Live-Ausrollen) und
`references/routing-frr-bird.md`, `references/networkd-iproute2.md`, `references/openwrt.md` geteilt;
`bsd-firewall` in Kern (Plattform, pf, VPN-Instanzen, config.xml, Live-Ausrollen) und
`references/routing-multi-wan.md`, `references/plugins.md`, `references/verweise.md`. Agent-Body von 13k
auf rund 6k Zeichen: Lesetabelle und Codex-Pfadabsatz raus, STARTUP an die Achse gekoppelt, Change-Regeln
(transient zuerst, Management-Verbindung nie als Erstes, pf-Systeme nur mit Konsole) bleiben als Eiserne
Regel im Body, Dubletten der globalen Regeln auf einen Sorgfalts-Dreizeiler. Command-Body auf einen
Adapter gekürzt, Codex-Schritte in `references/codex-start.md`, Routing-Hinweis gestrichen (steht in der
Description).

---

## ✅ UMGESETZT (2026-09-18): 0.3.0 — Fachwissen nur im Agenten

Die sechs Skills sind für den automatischen Aufruf gesperrt (Claude `disable-model-invocation`, Codex
`allow_implicit_invocation: false`) und stehen nicht mehr im Kontext der Hauptsitzung. Kein `skills:`
mehr im Agenten: Christian liest die `SKILL.md` erst, wenn ein Auftrag sie braucht (Tabelle im
Agent-Body). Die Change-Regeln, die vor jedem Lesen gelten müssen (transient testen, erst nach
verifizierter Erreichbarkeit persistieren, Management-Verbindung nie zuerst, sperrgefährdete Changes
auf pfSense/OPNsense nur mit Konsole oder Out-of-Band), stehen jetzt in den Sicherheitsregeln des
Agenten. Agent- und Command-Beschreibung gekürzt, `/christian` lädt unter Codex die Rollenanweisung
selbst.

---

## ✅ UMGESETZT (2026-07-19): pfSense/OPNsense-Plattform-Zweig (Skill `bsd-firewall`)

Neuer Skill `bsd-firewall` als zweite Plattform-Achse neben `router-appliance`: die BSD-Firewall-
Appliances **pfSense (Netgate)** und **OPNsense (Deciso)** in einem gemeinsamen Skill, Unterschiede
tabellarisch. Deckt die ganze Appliance ab — **pf**-Packet-Filter (Regel-/NAT-/State-Modell, Aliase,
`quick`, Interface=Zone, Anti-Lockout), **VPN-Instanzen** über die GUI (Design/Krypto bleibt bei
`openvpn`/`vpn-tunnel`/`wan-link`), **Routing & Multi-WAN** (Gateway-Groups, FRR-Paket), die
**elementaren Plugins/Pakete** (pfBlockerNG, Suricata/IDS, HAProxy, FRR, ACME, Monitoring) und
**config.xml**-Backup/Reproduzierbarkeit — reference-first aus docs.netgate.com/docs.opnsense.org/
pf.conf(5). Integriert in Persona (skills-Liste, STARTUP-Achse, Eiserne Regel 4: pfSense/OPNsense sind
Open-Source-BSD und gehören zu Christian, nicht zu bertram), Command-Routing, README und Manifeste
(Version 0.2.0).

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
