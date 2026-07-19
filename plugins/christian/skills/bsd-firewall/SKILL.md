---
name: bsd-firewall
description: "BSD-Firewall-/Router-Distributionen als Plattform-Achse: pfSense (Netgate; CE vs. Plus) und OPNsense (Deciso) auf gemeinsamer FreeBSD/pf-DNA. pf-Paketfilter (pass/block/match, quick, letzte-Regel-gewinnt, Interface=Zone, stateful, Aliase/Tabellen, NAT outbound automatic/hybrid/manual + Port-Forward/1:1 mit Filter-Rule-Association, Floating Rules, Anti-Lockout); VPN als GUI-Instanzen (OpenVPN/IPsec/WireGuard, interner CA-Manager); Routing & Multi-WAN (statisch, Gateway-Groups mit Tier/Trigger, FRR-Paket OSPF/BGP/BFD); Pakete/Plugins (pfBlockerNG, Suricata/Snort, HAProxy, FRR, ACME, ntopng, Zenarmor/Sensei); config.xml als Single-Source, Backup/Restore/Revert. Design kommt aus wan-link/vpn-tunnel/openvpn/router-appliance, hier die BSD-Umsetzung. Syntax/Defaults/Paketnamen reference-first aus docs.netgate.com/docs.opnsense.org/pf.conf(5), nicht aus dem Gedächtnis. Nutzen beim Bauen, Prüfen oder Umsetzen einer pfSense-/OPNsense-Appliance; Abgrenzung: kommerzielle Hardware → bertram, pfSense/OPNsense sind Open Source und bleiben hier."
---

# BSD-Firewall — pfSense & OPNsense

Die BSD-basierten Open-Source-Firewall-/Router-Distributionen als eigene Plattform-Achse: **pf** statt
nftables, **`config.xml`** statt einzelner Konfig-Dateien, **GUI-getrieben** statt handgeschriebener
Rulesets. Das Design (Zonen, Krypto, WAN-Kopplung, Routing) kommt unverändert aus den anderen
Christian-Skills — hier ist die **BSD-Plattform-Umsetzung** davon. Syntax, Default-Werte, GUI-Pfade und
Paketnamen sind **versionsabhängig** und kommen **aus der offiziellen Doku** (`docs.netgate.com`,
`docs.opnsense.org`, `man pf.conf(5)`), nicht aus dem Gedächtnis — unsichere Stellen unten sind als
**per Doku der Zielversion verifizieren** markiert. **Default ist Config bauen + read-only-Analyse**;
Live-Ausrollen läuft gestuft mit Rollback-Netz (siehe unten), nie beiläufig.

## Plattform-Überblick

Quellen-Anker: `docs.netgate.com`, `docs.opnsense.org`, FreeBSD Handbook (Firewalls → pf).

Beide sind **FreeBSD + pf** unter der Haube, mit einer Web-GUI darüber und `config.xml` als
Single-Source-of-Truth. **pfSense** stammt von **Netgate**, **OPNsense** von **Deciso** (2015 aus
pfSense geforkt). Gleiche pf-DNA, unterschiedliche Verpackung — pf-Wissen (unten) gilt für **beide**.

- **pfSense CE** (Community Edition) = Open Source; **pfSense Plus** = die von Netgate gepflegte Edition
  (ursprünglich für Netgate-Hardware). Editions-/Release-Modell-Details **per Doku verifizieren**.
- **OPNsense** = Open Source (BSD-2-Clause), festes Release-Schema (halbjährliche Major, regelmäßige
  Business-Releases). Genaue Kadenz **per Doku verifizieren**.

| Achse | pfSense | OPNsense |
|-------|---------|----------|
| Herkunft/Pflege | Netgate | Deciso (Fork 2015) |
| Editionen | CE (frei) + Plus | eine Edition, Community + Business-Release |
| Release-Modell | rollierend / Plus-Zyklus (verifizieren) | fixe Major-Releases (verifizieren) |
| Zusatz-Software | **Package Manager** (Pakete) | **`os-*`-Plugins** (System → Firmware → Plugins) |
| GUI-Framework | eigenes (bootstrap-basiert) | eigenes (MVC, Phalcon) |
| Inline-IPS | Suricata/Snort **als Paket** | **Suricata im Basissystem** (IPS via Netmap) |
| FRR | **FRR-Paket** | **`os-frr`-Plugin** |
| Lizenz | Apache 2.0 (CE) | BSD-2-Clause |

**Wichtig für die Agenten-Landkarte:** pfSense/OPNsense sind **Open Source** und gehören zu **Christian**
(Linux/Open-Source-Router). Kommerzielle Firewall-/Router-**Hardware** (Cisco, MikroTik, Palo Alto) ist
**bertram**. Nicht vermischen.

## pf — der Packet Filter

Quellen-Anker: `man pf.conf(5)`, OpenBSD PF FAQ, FreeBSD Handbook (Firewalls → pf).

### Regel-Modell
- Aktionen: **`pass`**, **`block`**, **`match`** (letzteres wertet aus/setzt Optionen, ohne die
  pass/block-Entscheidung zu treffen). `block` = stiller Drop; **`reject`** in der GUI schickt RST/ICMP.
- **Auswertungsreihenfolge: die *letzte* matchende Regel entscheidet** — außer eine Regel trägt
  **`quick`**, dann ist sie sofort die letzte matchende und die Auswertung stoppt (pf.conf(5)).
- **Achtung, GUI-Nuance:** In den **Interface-Tabs** von pfSense **und** OPNsense werden die Regeln
  effektiv **first-match** ausgewertet (die GUI erzeugt sie mit `quick`) — d.h. **die erste Regel, die
  matcht, gewinnt** (pfSense: „Evaluation stops after reaching this match"; OPNsense: bei aktivem
  `quick` „the first rule matching the packet will take precedence"). Nur **Floating Rules** ohne
  `quick` fallen auf die klassische **letzte-Regel-gewinnt**-Semantik zurück. Das ist der häufigste
  Denkfehler beim Umstieg von rohem pf.

### Interface = Zone
- pf filtert **am Interface** in **eingehender Richtung** (Default): eine Regel auf dem LAN-Tab gilt für
  Verkehr, der **aus dem LAN in die Firewall eintritt**. Verkehr muss nur **dort erlaubt werden, wo er
  eintritt** — die Stateful-Engine lässt die Antwort automatisch zurück.
- **WAN / LAN / OPTx** sind die Interface-„Zonen". Neues Segment = neues OPT-Interface + eigener
  Regel-Tab. Default am WAN ist **alles blockiert** (nur State-Rückverkehr + explizite Freigaben).
- Abgrenzung zu `router-appliance` (nftables): **gleiche Konzepte, andere Sprache** — pf `quick` /
  letzte-Regel-gewinnt statt Hook-Ketten-Reihenfolge; **Interface-Regeln (eingehend)** statt
  `forward`/`input`-Ketten am Hook. Wer nftables denkt, muss hier auf „Regel am eingehenden Interface"
  umschalten, nicht auf „Regel am Übergang".

### State (stateful by default)
- Jede `pass`-Regel legt per Default einen **State-Eintrag** an; Pakete, die auf einen State passen,
  gehen **ohne erneute Regelauswertung** durch (pf.conf(5)). Deshalb keine expliziten Rückwege nötig.
- State-Optionen (z.B. `state-type`, `max`, `sloppy`) und `flags` **per pf.conf(5) verifizieren**.

### Aliase (Tabellen)
- **Aliase** = benannte Host-/Netz-/Port-Listen (in pf **`table`** / Makro). In der GUI unter
  Firewall → Aliases; in Regeln statt Einzelwerte referenzieren — zentral pflegbar, schnell
  (Table-Lookups sind billig). Auch verschachtelbar.

### NAT
- **Outbound NAT** — vier Modi, identisch benannt bei beiden Plattformen: **Automatic**, **Hybrid**
  (Auto + manuelle Regeln), **Manual** (nur manuelle), **Disable** (aus, für rein routbare/Bridge-Setups).
  Für Multi-WAN oder feste Quell-IP meist **Hybrid**.
- **Port-Forward (rdr / `rdr-to`)** publiziert einen internen Dienst — **braucht zwingend eine
  Firewall-Regel**, die die umgeleiteten Pakete durchlässt (der Port-Forward ändert nur das Ziel, er
  filtert nicht). Über das Feld **Filter rule association**:
  - pfSense: **„Add associated filter rule"** (Default, mitgeführt), **„Add unassociated filter rule"**,
    **„Pass"** (pf-`pass` inline — **funktioniert nur am Interface mit dem Default-Gateway, nicht bei
    Multi-WAN**), **„None"** (keine Regel → Verkehr bleibt geblockt).
  - OPNsense: **Manual** / **Pass** / **Register rule** (sinngemäß gleich; exakte Labels **per Doku
    verifizieren**).
- **1:1 NAT** bildet eine externe IP bidirektional auf eine interne ab (statt many-to-one).

### Floating Rules
- Regeln über **mehrere Interfaces** und/oder in **explizit gewählter Richtung** (in/out), ausgewertet
  **vor** den Interface-Tabs (OPNsense-Reihenfolge: Floating → Interface-Gruppen → Interface). Ohne
  `quick` gilt hier letzte-Regel-gewinnt — mächtig, aber undurchsichtiger; sparsam einsetzen.

### Anti-Lockout-Regel
- Beide Plattformen erzeugen automatisch eine **Anti-Lockout-Regel**, die den Zugang zur Web-GUI/SSH
  auf dem Management-Interface (meist LAN) offen hält — schützt vor dem klassischen Selbst-Aussperren.
  **Grenze:** greift nur auf dem vorgesehenen Management-Interface; wer das Mgmt aufs WAN legt oder die
  Regel abschaltet, verliert den Schutz. Genauer Deaktivierungs-Pfad **per Doku verifizieren**.

## VPN auf der Appliance

Quellen-Anker: `docs.netgate.com` (OpenVPN/IPsec/WireGuard), `docs.opnsense.org` (VPN).

VPNs werden hier **nicht** als handgeschriebene Configs gebaut, sondern als **GUI-Instanzen** angelegt
(Server/Client, Tunnel-Netz, Krypto-Auswahl, Zertifikate).

- **OpenVPN** und **IPsec** sind im Basissystem beider Plattformen; **WireGuard** ist Paket/Plugin bzw.
  je nach Version im Basissystem (**per Doku verifizieren**).
- **Zertifikate** kommen aus dem **internen CA-Manager** (System → Cert. Manager / Trust) — CA anlegen,
  Server-/Client-Zertifikate ableiten, in die VPN-Instanz einhängen.
- **Trennung Design ↔ Umsetzung:** Das *Krypto- und Tunnel-Design* (Suite-Wahl, PFS, PKI-Aufbau,
  Site-to-Site vs. Roadwarrior) kommt aus Christians `openvpn`/`vpn-tunnel`/`wan-link`-Skills; hier
  überträgst du es nur in die **GUI-Felder**. Die Krypto-Härtung bleibt opinionated (**AEAD**, **PFS**,
  keine Legacy) — die verbindliche Freigabe holt **bruce** aus **TR-02102**. GUI-Feldnamen und
  verfügbare Cipher hängen an der Version → **per Doku verifizieren**, nicht raten.

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

## Elementare Plugins/Pakete

Quellen-Anker: `docs.netgate.com` (Packages), `docs.opnsense.org` (Plugins). **Paketverfügbarkeit und
-namen driften zwischen Versionen** — Namen und Existenz **immer gegen die jeweilige Doku prüfen**, nicht
aus dieser Tabelle raten. Installation: pfSense **System → Package Manager**; OPNsense **System →
Firmware → Plugins**.

| Zweck | pfSense | OPNsense | Anker |
|-------|---------|----------|-------|
| DNSBL/GeoIP-Filter | **pfBlockerNG** (pfBlocker-NG) | Teils Basis (Aliase/URL-Tabellen) + Plugins | Packages-Doku |
| IDS/IPS | **Suricata** und/oder **Snort** (Paket) | **Suricata im Basissystem** (IPS via Netmap) | IDS-Doku |
| Reverse-Proxy/LB | **HAProxy** (Paket) | **`os-haproxy`** | Packages/Plugins |
| Dynamisches Routing | **FRR** (Paket) | **`os-frr`** | FRR/Dynamic-Routing |
| WireGuard | **WireGuard** (Paket bzw. Basis, verifizieren) | Basis bzw. Plugin (verifizieren) | VPN-Doku |
| ACME/Let's Encrypt | **ACME** (Paket) | **`os-acme-client`** | ACME-Doku |
| Monitoring | **ntopng** (Paket) | **`os-ntopng`** / Telegraf | Monitoring-Doku |
| NGFW/App-Control | **Zenarmor/Sensei** (Paket) | **`os-sensei`** (Zenarmor) | Plugin-Doku |

`os-*`-Namen außer `os-frr` (Dynamic-Routing-Doku bestätigt) hier **nicht** einzeln verifiziert →
**per Plugin-Liste der Zielversion prüfen**.

## config.xml / Backup / Reproduzierbarkeit

Quellen-Anker: `docs.netgate.com` (Backup & Restore), `docs.opnsense.org` (Configuration Backups/History).

- **`config.xml`** hält **alle** Einstellungen in **einer** XML-Datei — „this one file can be used to
  restore a system to a fully working state". Das ist das BSD-Pendant zur **Appliance-Denke** aus
  `router-appliance`: die Box ist **aus einer Datei reproduzierbar**, kein Basissystem-Backup nötig.
- **pfSense:** Backup/Restore unter **Diagnostics → Backup & Restore**; **AutoConfigBackup (ACB)** sichert
  bei jeder Änderung automatisch; **Config History** (Diagnostics → Backup & Restore → Config History)
  erlaubt Diff und **Revert** auf frühere Stände.
- **OPNsense:** **System → Configuration → Backups** (lokal, optional passwortgeschützt; Konsolen-
  Einstellungen per Default ausgenommen, damit der Zugang nach Restore erhalten bleibt) und **System →
  Configuration → History** (Diff zwischen Ständen, Download/Restore älterer Versionen); Cloud-Backup
  z.B. Nextcloud.
- **Praxis:** vor jedem Schnitt exportieren, Backups **off-box** halten, Restore periodisch testen. Der
  XML-Export ist auch der Weg zu **reproduzierbaren** Deployments (versionierte Config, Diff-Review).

## Live-Ausrollen — gestuft, mit Rollback-Netz

Read-only zuerst: Config-Export ansehen, Rules/NAT/Gateways in der GUI lesen, `pfctl -sr`/`pfctl -sn`
(Shell/Diagnostics) — unkritisch und **immer zuerst**. Jeder schreibende Eingriff — Regel-Reload,
Default-Route/Gateway-Wechsel, Interface-Umbau, Outbound-NAT-Umstellung — kann **aussperren**:

1. **Config-Backup vor dem Schnitt** (`config.xml` exportieren; ACB/History als zweites Netz).
2. **Anti-Lockout-Regel kennen und ihre Grenzen** — sie hält nur das vorgesehene Management-Interface
   offen. Wer am Mgmt-Interface, an der Anti-Lockout-Regel selbst oder an der WAN-Erreichbarkeit dreht,
   verliert diesen Schutz. Nie die eigene Management-Verbindung als Erstes anfassen.
3. **Regel-/Filter-Reload ist scharf:** ein falscher Default-Block oder eine gekippte Pass-Regel kappt
   die GUI-Sitzung sofort. Kritische Changes über einen **zweiten, unabhängigen Zugang** (Konsole)
   absichern.
4. **Restore-Pfad vorher kennen:** GUI-Restore (Backup einspielen), Config History → Revert, oder als
   letzte Stufe die **Konsolen-Option** (Reset auf letzte/Werks-Config). Ohne Konsolen-/Out-of-Band-
   Zugang keinen sperrgefährdeten Change fahren.
5. **Ziel-System benennen und bestätigen lassen** und den **Blast-Radius** aussprechen (welches Segment
   / welcher Standort hängt an dieser Box) — bevor irgendetwas Schreibendes läuft. Analog zur Doktrin in
   `router-appliance`/`wan-link`.

## Anti-Patterns

- **Port-Forward ohne (richtige) Firewall-Regel** — „Filter rule association" auf „None" oder falsch
  verstanden; der Forward leitet um, aber nichts kommt durch.
- **`Pass` im Port-Forward bei Multi-WAN** — die Inline-`pass`-Option greift nur am Interface mit dem
  Default-Gateway; bei Multi-WAN eine echte assoziierte Regel nutzen.
- **`quick`/Reihenfolge falsch verstanden** — angenommen „letzte gewinnt", während die Interface-Tabs
  effektiv first-match sind (oder umgekehrt bei Floating Rules). Erst die Semantik des jeweiligen Tabs
  klären.
- **Regel am falschen Interface** — Verkehr wird **eingehend am Eintritts-Interface** gefiltert; die
  Regel gehört auf den Tab, wo der Verkehr **hereinkommt**, nicht wo er hinauswill.
- **Multi-WAN ohne symmetrischen Rückweg / `reply-to`-Falle** — Policy-Route/Gateway-Group ohne passendes
  `reply-to`, asymmetrischer Pfad → Stateful-Filter/CGNAT verwirft die Antwort.
- **Krypto- oder Paket-Defaults geraten** statt aus der Doku belegt — Cipher-Auswahl, Paketnamen,
  Protokoll-Verfügbarkeit sind versionsabhängig und fliegen im Audit auf.
- **pfSense- und OPNsense-Wissen vermischen**, ohne die Unterschiede (Package Manager vs. `os-*`,
  Suricata-Paket vs. Basis-IPS, Feld-Labels) zu prüfen — die pf-DNA ist gleich, die Verpackung nicht.

## Verweise

- **Design bleibt bei den Design-Skills:** Kopplungs-Szenario/Tech-Wahl `wan-link`; VPN-Technik/Aufbau
  `vpn-tunnel`; OpenVPN-Tiefe `openvpn`; Linux/nftables-Router-Pendant `router-appliance`. Dieser Skill
  ist nur die **BSD-Umsetzung** davon.
- **Referenz-Lookup-Disziplin:** unsichere Syntax/Defaults/Paketnamen über `vpn-reference` bzw. direkt
  gegen `docs.netgate.com`/`docs.opnsense.org`/`pf.conf(5)` belegen — erst aufrufen, dann behaupten.
- **Krypto-Freigabe:** opinionated hier, verbindliche Bewertung über **bruce** (`gs-krypto`, TR-02102).
- **Abgrenzung:** kommerzielle Netzwerk-**Hardware** (Cisco/MikroTik/Palo Alto) → **bertram**;
  pfSense/OPNsense sind Open Source und bleiben bei **Christian**.
