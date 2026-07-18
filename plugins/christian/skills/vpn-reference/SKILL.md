---
name: vpn-reference
description: "Reference-first-Disziplin für VPN- und Linux-Router-Stacks: Befehlsreferenz, Config-Syntax und Best Practices der jeweiligen Technik (OpenVPN, WireGuard, strongSwan/Libreswan, FRR/BIRD, nftables, Mesh-Overlays, OpenWrt/UCI) zitierfähig nachschlagen und anwenden, statt Optionen aus dem Gedächtnis zu raten. Nutzen, bevor eine unsichere Option, ein Default-Wert oder ein Feature-Verhalten ausgegeben wird. Quellen erst aufrufen, dann zitieren. Read-only-Default — Live-Deploy läuft über die wan-link/router-appliance-Doktrin."
---

# VPN-Reference — Nachschlagen statt raten

**Reference-first ist Pflicht.** Bevor du eine Config-Option, einen Default-Wert oder ein
Feature-Verhalten ausgibst, dessen genaue Form du nicht sicher belegt hast: nachschlagen. Modellwissen zu
VPN-Stacks ist veraltet, verwechselt Versionen (OpenVPN 2.4 vs. 2.6, strongSwan `ipsec.conf` vs.
`swanctl`) und mischt Vendor-Dialekte. Eine belegte Antwort schlägt fünf plausibel klingende geratene —
besonders bei Krypto-Parametern, wo eine falsche Option still eine schwache Suite aushandelt.

## Quellen nach Technik

Offizielle Referenz zuerst. Community-Quellen (Wiki, HowTo) nur ergänzend und als solche gekennzeichnet.

| Technik | Primärquelle | Typischer Inhalt |
|---------|--------------|------------------|
| OpenVPN | Manpage `openvpn(8)`; Community-HowTo/Wiki (community.openvpn.net) | Option-Syntax, Defaults, Reference Manual je 2.x-Zweig |
| WireGuard | wireguard.com/quickstart; `wg(8)`, `wg-quick(8)` | Peer-/Interface-Syntax, AllowedIPs-Semantik, `wg-quick`-Direktiven |
| strongSwan | docs.strongswan.org (swanctl / `swanctl.conf`) | IKEv2-Proposals, Connection-Layout, `vici`/`swanctl`-CLI |
| Libreswan | libreswan.org/wiki (Doku, `ipsec.conf(5)`) | `conn`-Stanzas, `ipsec` CLI, Interop-Notizen |
| FRR | docs.frrouting.org | BGP/OSPF/Static, vtysh-Syntax, Daemon-Layout |
| BIRD | bird.network.cz/?get_doc (User's Guide) | Protokoll-/Filter-Sprache, Config-Struktur |
| nftables | wiki.nftables.org; `nft(8)` | Ruleset-Syntax, Chains/Hooks/Prioritäten, NAT/`ct` |
| Mesh-Overlays | Projekt-Doku: Headscale, NetBird, Netmaker, ZeroTier, Nebula | Control-Plane-Setup, ACL-Modell, Key/CA-Handling |
| OpenWrt | openwrt.org/docs; UCI-Doku | UCI-Sektionen (`/etc/config/*`), `uci`-CLI, Paket-Optionen |

**Vom User gereichte Referenz** (Manpage-Export, Vendor-PDF, bestehende Config, `openvpn --version`-
Ausgabe) hat Vorrang und wird per `Read` eingelesen — sie ist oft genau die Version, die auf dem
Zielsystem läuft.

## Workflow

1. **Frage präzisieren:** Welche Technik, welches Tool und **welche Version**? Optionen und Defaults
   ändern sich zwischen Releases (OpenVPN `data-ciphers` ab 2.4/2.5, `--cipher` deprecated in 2.6;
   strongSwan `swanctl` löst `ipsec.conf` ab). Fehlt die Version, danach fragen oder aus
   `openvpn --version` / `wg --version` / `swanctl --version` / `nft --version` ableiten.
2. **Quelle holen:** vom User gereichtes Dokument (`Read`) → sonst **Manpage** auf dem System
   (`man openvpn`, `man wg-quick`, `man nft`) → sonst offizielle Projekt-Doku (`WebFetch` der konkreten
   Seite) → `WebSearch` nur, um die offizielle Seite zu finden. Foren/Blogs nur als letzter Ausweg und
   deutlich als unbestätigt kennzeichnen.
3. **Verifizieren, dann zitieren:** Die Seite/Manpage tatsächlich aufrufen und den relevanten Abschnitt
   lesen, bevor du sie als Beleg nennst. Nie einen Link als „genau das" verkaufen, ohne den Inhalt
   geprüft zu haben.
4. **Zitierfähig ausgeben:** Syntax/Verhalten mit **Tool + Version + Quelle** wiedergeben (z.B.
   „`openvpn(8)`, 2.6, Abschnitt Encryption Options"). Bei Best Practices die empfehlende Quelle nennen
   (Projekt-Hardening-Guide, einschlägiger RFC).
5. **Auf die Aufgabe anwenden:** Erst nach Beleg den konkreten Config-Block / die Option formulieren.

## Best Practices belegen

Best-Practice-Aussagen („diese Suite, dieses MTU, dieser DH-Group-Wert") nie als gesetzt behaupten — mit
Quelle belegen: Projekt-Hardening-Guide, einschlägiger RFC (z.B. RFC 7296 IKEv2, RFC 9147 DTLS 1.3), oder
die Projekt-Doku selbst. Wo eine Empfehlung kontextabhängig ist (UDP vs. TCP, L2 vs. L3, Split- vs.
Full-Tunnel), die Abhängigkeit benennen statt eine Universallösung zu verkaufen.

## Krypto-Parameter → bruce / gs-krypto

Für die **Bewertung** von Krypto-Parametern (Cipher-Suites, DH-/ECDH-Gruppen, Schlüssellängen,
Hash-Verfahren, PFS) gegen einen anerkannten Standard ist die BSI **TR-02102** die Referenz — dort über
`bruce` (`gs-krypto`) verweisen, statt Grenzwerte aus dem Gedächtnis zu setzen. Dieser Skill liefert die
**Syntax**, wie man eine Suite konfiguriert; die **Freigabe**, ob sie stark genug ist, kommt aus der TR.

## Wenn keine Referenz beschaffbar ist

Ist die konkrete Syntax nicht belegbar (kein Internet, keine Manpage, keine gereichte Doku): das **offen
sagen**, die konzeptionelle Antwort auf Ebene des Ziels geben („du brauchst eine Peer-Sektion mit
`AllowedIPs`, die das Remote-Subnetz umfasst") und die exakte Option als **zu verifizieren** markieren —
nicht eine erfundene Zeile als Fakt ausgeben.

## Read-only zuerst

Nachschlagen und Config-Entwürfe sind per Default read-only. Ein Live-Eingriff (Tunnel hochziehen,
Ruleset laden, Routing-Change) läuft über die `wan-link`/`router-appliance`-Doktrin (Bestätigung +
Rollback-Netz), nie beiläufig aus der Referenz heraus.
