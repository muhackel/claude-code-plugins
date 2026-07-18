---
name: router-appliance
description: "Linux-Router-Stack als Kernkompetenz: nftables (Tabellen/Ketten/Hooks, stateful ct-state, Zonen WAN/LAN/DMZ/MGMT, NAT masquerade/dnat/snat, default-drop, MSS-Clamping, Anti-Spoofing/rp_filter, iptables→nftables-Migration); Routing mit FRR/BIRD (OSPF/BGP/statisch, Kernel-FIB, ECMP, wann welcher Daemon); iproute2/systemd-networkd (Adressen/Routen, Policy-Routing mit ip rule + mehreren Tabellen, VRF, IP-Forwarding-sysctls, Bridges/VLANs); OpenWrt/DD-WRT (UCI/opkg) als sekundäre Plattform. Appliance-Denke: minimal, dienstgetrennt, reproduzierbar (NixOS-Umsetzung → nixie). Syntax reference-first aus offizieller Doku, nicht aus dem Gedächtnis. Nutzen beim Bauen, Prüfen oder Umsetzen eines Linux-Routers/Firewall-Gateways."
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
- **Reverse-Path** primär über den Kernel-sysctl `net.ipv4.conf.*.rp_filter` (siehe iproute2-Abschnitt),
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

Quellen-Anker: `docs.frrouting.org`, `bird.network.cz` (BIRD-User-Guide). Direktiven dort belegen.

### Wann FRR, wann BIRD
| | FRR | BIRD |
|---|-----|------|
| Stärke | breites Protokoll-Set, Cisco-nahe vtysh-CLI, OSPF/BGP/IS-IS/PIM/BFD | schlanker, sehr performant, mächtige Filtersprache, BGP-Route-Server/RR |
| Passt für | Enterprise-/Campus-Router, Multiprotokoll, wer IOS-Denke gewohnt ist | reine BGP-Boxen, IXP/Route-Server, große Tabellen, feingranulare Policy |
| Config | vtysh (integriert) oder Daemon-Files; reload | eine `bird.conf`, deklarativ; `birdc configure` |

Faustregel: **OSPF + gemischte Protokolle → FRR**; **BGP-lastig/Policy-lastig/Route-Server → BIRD**.

### OSPF / BGP / statisch
- **Statisch** reicht für Stub-/Single-Uplink-Router — kein Daemon, Routen über iproute2 (siehe unten).
  Dynamisches Routing erst, wenn Redundanz/Multi-Path/mehrere Router es rechtfertigen.
- **OSPF:** Area-Design nach Fehlerdomäne, Area 0 als Backbone, Interface-Auth, Router-ID
  deterministisch. FRR: `router ospf` / `network … area …` (vtysh) — Details `docs.frrouting.org`.
- **BGP:** eBGP an jeder Uplink-/Peering-Grenze mit **Prefix-Filter in beide Richtungen** (nichts
  ungefiltert annehmen/ankündigen); AS-/Community-Struktur klar. BIRD-Filter oder FRR-route-maps.

### Integration Kernel-FIB
- FRR/BIRD sind Control-Plane (RIB); die Forwarding-Entscheidung trifft der **Kernel-FIB**. Der Daemon
  installiert selektierte Routen via **Netlink** (FRR: `zebra`; BIRD: `kernel`-Protokoll) in die
  Kernel-Tabelle.
- Route-Herkunft im Blick behalten: `ip route show` zeigt die FIB, `vtysh -c "show ip route"` /
  `birdc show route` die RIB. Diskrepanz = Daemon installiert nicht (Admin-Distanz, `kernel`-Protokoll
  im BIRD nicht auf `export`, VRF-Zuordnung).
- **Policy-Routing-Tabelle** je Daemon beachten: schreibt der Daemon in `main` oder eine eigene Tabelle?
  Muss zur `ip rule`-Logik passen (siehe unten).

### ECMP
- Mehrere gleichwertige Nexthops → Equal-Cost-Multipath. Kernel-seitig `nexthop`-Gruppen; der
  Hash-Algorithmus über `net.ipv4.fib_multipath_hash_policy` (L3 vs. L3+L4) — **per sysctl-Doku
  verifizieren**. Layer-4-Hash streut besser, kann aber PMTU/State-Annahmen brechen.
- FRR/BIRD müssen ECMP-fähig konfiguriert sein (Maximum-Paths). Asymmetrie bedenken → `rp_filter`
  entschärfen.

## iproute2 / systemd-networkd — der Netz-Layer

Quellen-Anker: `man ip(8)` (+ `ip-route`, `ip-rule`, `ip-address`), `man systemd.network(5)`.

### Adressen & Routen (imperativ vs. deklarativ)
- **iproute2** (imperativ, flüchtig bis persistiert): `ip addr add`, `ip route add`, `ip link set`.
  Gut für Diagnose und den Live-Test **vor** dem Persistieren.
- **systemd-networkd** (deklarativ, persistent): `.network`/`.netdev`/`.link`-Units unter
  `/etc/systemd/network/`. `[Match]` bindet ans Interface, `[Network]`/`[Route]`/`[Address]` setzen
  Konfiguration. Für die Appliance der persistente Weg (oder NixOS via nixie).

### Policy-Routing (`ip rule` + mehrere Tabellen)
- Mehrere Routing-Tabellen (`/etc/iproute2/rt_tables` benennt sie), `ip rule` wählt anhand von
  Quelle/Mark/iif die Tabelle. Klassiker: **Multi-Uplink** — Traffic aus Quelle A über Uplink A,
  Rückverkehr symmetrisch.
- **Muster:** je Uplink eine Tabelle mit eigener Default-Route; `ip rule add from <quelle> lookup
  <tabelle>`; eingehend markiertes Antwortpaket per `fwmark` (in nftables `meta mark set`) derselben
  Tabelle zuweisen, damit die Antwort denselben Uplink nimmt.
- **Anti-Pattern: Policy-Routing ohne Rückweg** — Hinweg über Uplink B, Antwort geht per `main`-Default
  über Uplink A → asymmetrisch, `rp_filter=strict` verwirft es, Stateful-Firewall/CGNAT bricht.
  Rückweg-Regel **immer** mitbauen.

### VRF
- Echte L3-Isolation über `ip link add <vrf> type vrf table <n>` + Interfaces `master <vrf>` zuordnen
  (Mgmt-VRF, isoliertes Kundennetz). Jedes VRF hat seine eigene Tabelle; Leaks nur bewusst über
  Route-Leaking. Dienste ans VRF binden (`ip vrf exec`). Exakte Syntax **per ip(8) verifizieren**.

### IP-Forwarding & rp_filter (sysctl)
Ohne diese ist die Box kein Router:
```
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.ipv4.conf.all.rp_filter = 1        # 2 = loose bei asymmetrischem Routing
net.ipv4.conf.default.rp_filter = 1
```
Persistent über `/etc/sysctl.d/*.conf` (oder networkd `IPForward=`/NixOS). **`all` und `default`
zusammen** setzen — `default` greift nur für später erscheinende Interfaces. rp_filter-Semantik (`per-if`
vs. `all` ist ein Maximum) **per Kernel-Doku (`ip-sysctl`) verifizieren**.

### Bridges & VLANs
- **Bridge:** `ip link add br0 type bridge` + Ports `master br0` — für L2-Zusammenschaltung/Switch-Rolle
  der Box. VLAN-Filtering auf der Bridge (`vlan_filtering 1`) für 802.1Q auf der Bridge selbst.
- **VLAN-Interface:** `ip link add link eth0 name eth0.20 type vlan id 20` — tagged Subinterface je
  Zone. In networkd über `.netdev` (`Kind=vlan`) + `.network` (`VLAN=`).

## OpenWrt / DD-WRT — sekundäre Plattform

Quellen-Anker: `openwrt.org` (UCI-, opkg-, firewall4-Doku). Steckenpferd der Herkunft, **nicht** der Kern.

- **UCI** ist die deklarative Config-Schicht: `/etc/config/network`, `/etc/config/firewall`,
  `/etc/config/dhcp`. Dieselben Ziele wie oben, andere Abstraktion — Zonen sind hier **first-class**
  (`config zone` mit `input`/`output`/`forward`-Policy + `forwarding`-Regeln zwischen Zonen).
- **firewall4** (aktuelles OpenWrt) generiert **nftables** aus UCI — das nft-Wissen oben gilt darunter
  weiter; UCI ist der Generator, nicht ein anderer Stack.
- **opkg** installiert Pakete (`opkg update && opkg install <pkg>`), z.B. FRR/BIRD, wireguard-tools.
- **Abbildung:** Linux-Zonenübergang ≙ UCI `config forwarding`; Policy-Routing ≙ `config rule`;
  statische Route ≙ `config route`. Für die Appliance-Denke: dieselben Konzepte, in UCI ausgedrückt.
- DD-WRT ist GUI-/nvram-lastig und heterogener — im Zweifel auf die konkrete Build-Doku stützen, wenig
  aus dem Gedächtnis annehmen.

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
