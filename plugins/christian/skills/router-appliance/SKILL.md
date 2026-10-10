---
name: router-appliance
description: "Linux-Router-Stack: nftables-Firewall mit Zonen und NAT, Routing mit FRR oder BIRD, iproute2/networkd, OpenWrt als Zweitplattform, gestuftes Live-Ausrollen. Nutzen beim Bauen, Prüfen oder Umsetzen eines Linux-Routers oder Firewall-Gateways."
---

# Router-Appliance — der Linux-Router-Stack

Der volle Stack einer Linux-Router-Box: Firewall (nftables), Routing (FRR/BIRD), Netz-Layer
(iproute2/systemd-networkd) — plus OpenWrt/DD-WRT als sekundäre Plattform. Syntax und Default-Werte
kommen **aus der offiziellen Doku** (`vpn-reference`), nicht aus dem Gedächtnis: eine nft-Direktive,
ein FRR-Default, ein sysctl-Name ist versionsabhängig. Unsichere Optionen unten sind als **per
Manpage/Doku verifizieren** markiert. **Default ist bauen + read-only-Analyse**; Live-Ausrollen läuft
gestuft mit Rollback-Netz (siehe unten), nie beiläufig aus diesem Skill heraus. Plattform-agnostisch
entwerfen — die reproduzierbare NixOS-Umsetzung übergibst du an **nixie** (Briefing → Hauptagent).

## nftables — die Firewall

Quellen-Anker: `wiki.nftables.org`, `man nft(8)`. Syntaxdetails gegen diese belegen.

### Modell: Tabellen / Ketten / Hooks
- **Tabelle** = Namespace je Adressfamilie: `inet` (v4+v6 gemeinsam — Standard für Router), `ip`, `ip6`,
  `arp`, `bridge`. Für ein Router-Regelwerk **eine `inet`-Tabelle** statt getrennt v4/v6.
- **Basis-Kette** bindet an einen **Hook** mit `type`, `hook`, `priority`, `policy`. Die für Router
  relevanten Netfilter-Hooks: `prerouting` → `input` (an den Host) / `forward` (durch den Host) →
  `postrouting`, und lokal erzeugt `output`. **Forwarding-Verkehr läuft über `forward`, nicht `input`** —
  häufiger Denkfehler.
- **Filter-Kette:** `type filter hook forward priority 0; policy drop;`. **Reguläre Ketten** (ohne
  Hook) per `jump`/`goto` aus Basis-Ketten aufrufen — so baust du Zonen-Ketten (siehe unten).
- Prioritäten steuern Reihenfolge mehrerer Ketten am selben Hook (niedriger = früher). Standardwerte
  (`filter`≈0, `srcnat`≈100, `dstnat`≈-100) **per nft(8) verifizieren** — hängen an der Familie.

### Stateful — `ct state`
Erste Regel jeder Filter-Kette ist der Connection-Tracking-Shortcut:
```
ct state established,related accept
ct state invalid drop
```
Danach nur noch **neue** Verbindungen bewusst erlauben. `ct state` deckt das Gros des Traffics ab, bevor
teurere Regeln greifen. NAT setzt CT voraus — ohne CT kein masquerade/dnat.

### Zonen-Denke (WAN / LAN / DMZ / MGMT)
nftables kennt keine „Zonen" als Objekt — du modellierst sie über **Interface-Gruppen + reguläre
Ketten**. Muster:
- Interfaces per `iifname`/`oifname` einer Zone zuordnen (bei mehreren Interfaces pro Zone: `iifname {
  "eth1", "eth2" }` oder ein **`define`**/nftables-Set). Verbose Namen sind stabiler als `iif`-Indizes.
- Pro erlaubtem Zonenübergang eine Regel/Kette: LAN→WAN erlauben, WAN→LAN nur `established,related`,
  DMZ→LAN default-drop, MGMT hat Sonderrechte, alles andere fällt durch auf `policy drop`.
- **Default zwischen Zonen ist deny** — nur die gewollten Übergänge stehen explizit drin.

| Zone | Vertrauen | Typische Übergänge |
|------|-----------|--------------------|
| WAN  | untrusted | nach innen nur established/related; dnat für publizierte Dienste |
| LAN  | trusted   | → WAN erlaubt; → DMZ nur definierte Ports; → MGMT gesperrt |
| DMZ  | semi      | → WAN erlaubt; → LAN default-drop (keine Rückwärts-Initiierung) |
| MGMT | admin     | eigenes VLAN/Interface; SSH/Mgmt nur von hier |

### NAT
Eigene Kette(n) am nat-Hook, `type nat`:
- **masquerade** (dynamische WAN-IP): `oifname $wan masquerade` in `postrouting`. Nimmt die IP des
  Ausgangs-Interfaces automatisch — richtig für DSL/DHCP-WAN.
- **snat** (feste WAN-IP): `snat to <ip>` in `postrouting` — schneller als masquerade, aber IP fest.
- **dnat** (Port-Forward/publizierter Dienst): `dnat to <intern>:<port>` in `prerouting`; die
  zugehörige **`forward`-accept-Regel** nicht vergessen (dnat ändert das Ziel, filtert aber nicht).

### Default-drop
Router-Regelwerk ist **default-deny**: Basis-Ketten `input`/`forward` auf `policy drop`, erlaubte
Flows explizit. `output` je nach Härtungsgrad. **Anti-Pattern: `policy accept` + einzelne Drop-Regeln** —
jede vergessene Regel ist ein Loch.

### MSS-Clamping
Gegen PMTU-Blackholes hinter Tunneln/PPPoE die TCP-MSS an die Pfad-MTU klemmen:
```
tcp flags syn tcp option maxseg size set rt mtu
```
in `forward` (oder `postrouting`). `set rt mtu` klemmt auf die Route-MTU; alternativ fester Wert.
Exakte Syntax **per nft(8) / wiki.nftables.org verifizieren** (Option `maxseg`, `set rt mtu`).

### Anti-Spoofing / rp_filter
- **Reverse-Path** primär über den Kernel-sysctl `net.ipv4.conf.*.rp_filter` (siehe `references/networkd-iproute2.md`),
  nicht in nftables nachbauen — bei asymmetrischem Routing (mehrere Uplinks) `rp_filter=2` (loose)
  statt `1` (strict), sonst kappt der Router legitimen Rückverkehr.
- In nftables ergänzend **Bogon-/Martian-Filter** am WAN-Ingress: RFC1918-Quellen von außen, eigene
  LAN-Prefixe als Quelle vom WAN → drop. `fib saddr . iif oif missing drop` als nft-natives
  Reverse-Path-Konstrukt (**per nft(8) verifizieren**).

### Migration iptables → nftables
- `iptables-translate` / `ip6tables-translate` übersetzt einzelne Regeln; `iptables-restore-translate`
  ein ganzes Ruleset — **als Startpunkt, nicht als fertiges Regelwerk** (erzeugt oft `ip`-Tabellen statt
  konsolidierter `inet`, 1:1 statt idiomatisch).
- Compat-Layer `iptables-nft` fährt iptables-Syntax auf nftables-Backend — Übergang, kein Ziel.
- **Nicht mischen:** legacy-`iptables` (xtables) und `nft` gleichzeitig aktiv = zwei getrennte
  Regelwerke, undurchschaubare Reihenfolge. Einen Stack wählen.

## Routing — FRR / BIRD

Vor FRR-/BIRD-Direktiven, der Wahl zwischen OSPF, BGP und statischem Routing, Fragen zur Kernel-FIB
oder ECMP `references/routing-frr-bird.md` neben dieser Datei lesen.

## iproute2 / systemd-networkd — der Netz-Layer

Vor Adress- und Routen-Konfiguration, Policy-Routing mit `ip rule`, VRF, Forwarding- und
rp_filter-sysctls, Bridges oder VLANs `references/networkd-iproute2.md` neben dieser Datei lesen.

## OpenWrt / DD-WRT — sekundäre Plattform

Bevor du UCI-, opkg- oder firewall4-Zeilen ausgibst oder prüfst oder ein OpenWrt-/DD-WRT-Ziel
anfasst, `references/openwrt.md` neben dieser Datei lesen.

## Appliance-Denke

- **Minimal:** nur die Dienste, die die Rolle braucht (Router ≠ Applikationsserver). Kleinere
  Angriffsfläche, klarere Boot-Reihenfolge, weniger, was den Datenpfad stört.
- **Dienstgetrennt:** Firewall (nftables), Routing (FRR/BIRD), Netz (networkd) als getrennte,
  benannte Konfig-Einheiten — nicht ein Mega-Script. Boot-/Abhängigkeitsreihenfolge mitdenken
  (Interfaces up → Regeln geladen → Routing-Daemon startet → Default-Route steht).
- **Reproduzierbar:** die Box muss aus der Config wiederherstellbar sein. Für den reproduzierbaren,
  deklarativen Bau (NixOS) **Briefing an nixie** (Zielbild, nft-Ruleset, FRR/BIRD-Config,
  networkd-Units, sysctls, offene Punkte) → Hauptagent spawnt nixie. Du entwirfst plattform-agnostisch.

## Anti-Patterns

- **Default-accept-Firewall** (`policy accept` + Drop-Regeln) — jede Lücke ist offen. Immer default-drop.
- **Fehlendes rp_filter / Anti-Spoofing** am WAN — Quell-IP-Spoofing und Rückweg-Chaos.
- **Policy-Routing ohne Rückweg** — asymmetrischer Pfad, den Stateful-Firewall/rp_filter/CGNAT killen.
- **dnat ohne forward-accept** — Port-Forward, der nie durchkommt (dnat filtert nicht).
- **iptables und nftables parallel aktiv** — zwei Regelwerke, unklare Reihenfolge.
- **Krypto/Cipher-Defaults geraten** statt aus der Doku belegt — versionsabhängig, fliegt im Audit auf.

## Live-Ausrollen — gestuft, mit Rollback-Netz

Read-only-Analyse (`ip … show`, `nft list ruleset`, `vtysh -c "show …"`, `birdc show …`) ist unkritisch
und **immer zuerst**. Jeder schreibende Eingriff — besonders nftables-default-drop, Default-Route,
FRR/BIRD-reload — kann den Zugang kappen:

1. **Config-Backup vor dem Schnitt** (`nft list ruleset > backup`, `ip route save`, Config-Dateien
   kopieren).
2. **SSH-keepalive-Fenster** offen halten; nie die eigene Management-Verbindung als Erstes anfassen.
3. **`at`-getriggerter Auto-Rollback:** vor dem riskanten Change einen `at`-Job schedulen, der nach
   n Minuten die Backup-Config zurückspielt — sperrt der Change dich aus, stellt der Job den Zugang
   wieder her. Nach erfolgreichem Test den Job canceln.
4. **Erst testen, dann persistieren:** imperativ (`ip`/`nft -f` transient) anwenden, Erreichbarkeit
   prüfen, **dann** in networkd/sysctl.d/Daemon-Config persistieren. Nie „persistent zuerst".
5. **Ziel-System benennen und bestätigen lassen**, bevor irgendetwas Schreibendes läuft.

Konkrete WAN-/Tunnel-Kopplungen kommen als Design aus `wan-link`; VPN-Endpunkte aus `vpn-tunnel`/
`openvpn`; die Umsetzung landet hier.
