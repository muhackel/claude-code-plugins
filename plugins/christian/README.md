# christian — Linux-VPN- & Router-Spezialist

Christian Scheele, der VPN-Fachmann und Linux-Router-Bauer. Herkunft OpenWrt/DD-WRT, Kern generisches
Linux: baut Router-Appliances (mit/ohne VPN) und koppelt Netze über sichere WAN-Verbindungen. Neben dem
Linux-Stack ein zweiter Plattform-Zweig: die BSD-Firewalls **pfSense/OPNsense** (pf, config.xml,
elementare Plugins). OpenVPN ist die aktuelle Kern-Expertise; WireGuard und IPsec/strongSwan
gleichermaßen, VyOS/NixOS rudimentär.
Kern-Prinzip: **Reference-first** — Config-Syntax, Krypto-Suiten und Manpage-Defaults kommen aus der
offiziellen Doku, nicht aus dem Gedächtnis. Analog zu `bruce` („Korpus-first"), `nixie` („Docs-first")
und `bertram` („Vendor-Referenz-first").

## Philosophie

- **Reference-first:** VPN-/Router-Config-Wissen im Modell ist veraltet und verwechselt Versionen.
  Christian schlägt die Manpage/das HOWTO nach oder fordert es an, bevor er Syntax oder Krypto-Defaults
  ausgibt.
- **Blast-Radius-Respekt:** Ein WAN-Link-, Firewall- oder Routing-Change kann einen Standort aussperren.
  Default ist bauen + read-only-Analyse; Live-Deploys nur auf explizite Anforderung, mit Bestätigung
  und Rollback-Netz (Config-Backup, keepalive-Fenster, `at`-Auto-Rollback).
- **Linux-first:** Zuständig für Linux/Open-Source (OpenWrt, DD-WRT, generisches Linux, VyOS/NixOS
  rudimentär). Kommerzielle Hardware (Cisco/MikroTik/Palo Alto) bleibt bertrams Revier.

## Komponenten

| Typ | Name | Zweck |
|-----|------|-------|
| Agent | `christian:christian` | Linux-VPN-/Router-Persona, orchestriert die Skills |
| Command | `/christian` | Christian direkt aufrufen (mit optionalem Auftrag) |
| Skill | `vpn-reference` | Config-Syntax/Krypto-Suiten/Manpage-Defaults zitierfähig nachschlagen (Reference-first) |
| Skill | `openvpn` | OpenVPN-Kern-Expertise: Server/Client, Krypto-Suite, tls-crypt, Routing/Push |
| Skill | `vpn-tunnel` | Protokoll-übergreifend Tunnel entwerfen (OpenVPN/WireGuard/IPsec), Site-to-Site vs. Client-Server |
| Skill | `router-appliance` | Linux-Router-Appliance bauen — nftables, FRR, Persistenz, gestufter Live-Zugriff |
| Skill | `bsd-firewall` | BSD-Firewall-Appliance pfSense/OPNsense — pf, VPN-Instanzen, Multi-WAN/Gateway-Groups, elementare Plugins, config.xml |
| Skill | `wan-link` | Sichere WAN-Kopplung zwischen Netzen — Routing, Firewall-Zonen, PMTU/MSS, Failover |

Weitere geplante Erweiterungen (VyOS-Tiefe, Appliance-Image-Builds, FRR-Multipoint-Overlays,
PMTU-/MSS-Tooling) in [BACKLOG.md](./BACKLOG.md).

## Nutzung

```
/christian baue eine OpenVPN-Site-to-Site-Kopplung zwischen 10.0.0.0/24 und 10.0.1.0/24
/christian entwirf eine Linux-Router-Appliance mit nftables und WireGuard-Gateway
/christian richte auf einer OPNsense-Box eine OpenVPN-Instanz und Multi-WAN-Failover ein
/christian welche data-ciphers sollte ich bei OpenVPN 2.6 setzen?
```

Ohne Text spawnt der Command Christian, der dann nach Ziel (VPN/Router/WAN), Endpunkten/Netzen und
Plattform fragt.

## Installation (lokal)

```bash
/plugin marketplace add ./
/plugin install christian --scope local
```

## Lizenz

MIT. Struktur und Ideen sind inspiriert von `arsallls/claude-network-skills` (MIT), aber eigenständig
geschrieben.
