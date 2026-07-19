---
name: net-diagnose
description: "Strukturierte Netzwerk-Fehlersuche von L1 bis L7: geordnete Diagnose-Sequenzen statt Raten. Interface-Health (CRC, Drops, Duplex-Mismatch, Flapping, Speed-Negotiation), L2 (STP, VLAN, MAC-Table), L3 (Routing, BGP/OSPF-Nachbarn, ACL), L4+ (Dienste, Firewall, DNS/DHCP). Je Symptom die Check-Reihenfolge, das exakte Show-Kommando, die Bedeutung des Outputs und die häufigen Anti-Patterns. Nutzen bei 'warum spinnt das Netz' und jedem konkreten Störungsbild."
---

# Net-Diagnose — von unten nach oben

**Layer-Disziplin.** Erst messen, dann schließen. Fehlersuche geht strukturiert von L1 (Physik) nach
oben — nicht auf der vermuteten Schicht herumraten. Ein „langsames Netz" kann ein Duplex-Mismatch (L1/2),
eine STP-Neuberechnung (L2), asymmetrisches Routing (L3) oder ein überlastetes DNS (L7) sein. Die
Sequenz trennt das auf.

Exakte Kommando-Syntax je Vendor/Version über `net-reference` belegen — die folgenden Kommandos sind
die gängige Cisco-IOS-Form als Orientierung; RouterOS/PAN-OS/Junos haben eigene Pfade.

## Diagnose-Sequenz (L1 → L7)

### L1 — Physik
- **Symptome:** kein Link, sporadische Ausfälle, hohe Fehlerraten.
- **Checks:** `show interface <if>` → Zeile `up/up`? Transceiver: `show interface <if> transceiver`
  (SFP-Rx/Tx-Power im Budget?). Kabel/Port-Wechsel als Gegenprobe.
- **Anti-Pattern:** SFP-Rx-Power am Rand des Budgets als „ok" durchwinken — grenzwertige Optik erzeugt
  intermittierende CRC-Fehler, die wie ein L2/L3-Problem aussehen.

### L1/L2 — Interface-Health (das häufigste)
- **Checks:** `show interface <if>` — auf diese Zähler achten:
  - **CRC-Errors** → fast immer Physik (Kabel, SFP, EMV) oder ein **Duplex-Mismatch**.
  - **Input/Output Drops** → Congestion / Buffer / QoS, nicht zwingend Fehler.
  - **Runts / Giants** → Duplex-Mismatch bzw. MTU-/Framing-Problem.
  - **Late Collisions** → klassischer **Duplex-Mismatch** (eine Seite Half, andere Full).
  - **Flapping** (`show logging` auf `link-flap`, Interface-Reset-Counter) → Physik oder Autoneg.
- **Speed/Duplex:** beide Seiten prüfen — **entweder beide auto oder beide fest**, nie gemischt. Eine
  feste Seite gegen eine auto-Seite fällt auf Half-Duplex zurück → Late Collisions + CRC.
- **Anti-Pattern:** Interface `err-disabled` übersehen (`show interface status` → `err-disabled`).
  Ursache finden (BPDU-Guard, Port-Security, Flap-Detection), nicht blind `shut/no shut`.

### L2 — Switching
- **VLAN:** `show vlan brief`, `show interface trunk` — ist das VLAN auf dem Trunk **allowed** und aktiv?
  Native-VLAN-Mismatch an beiden Trunk-Enden? MTU über den Trunk konsistent?
- **MAC:** `show mac address-table` — lernt der Switch die MAC am erwarteten Port? MAC-Flapping zwischen
  Ports = **L2-Loop** oder doppelte MAC.
- **STP:** `show spanning-tree` — wer ist Root (erwartet?), welche Ports `BLK`? Häufige TCN
  (Topology-Change) → instabiler Link flappt und triggert Reconvergence. Root-Guard/BPDU-Guard-Status
  prüfen.
- **Anti-Pattern:** einen L2-Loop mit Ping-Tests jagen, statt MAC-Flapping und STP-TCN-Counter
  anzusehen — der Loop zeigt sich dort zuerst.

### L3 — Routing & Reachability
- **Lokal:** `show ip interface brief`, `show ip route <ziel>` — gibt es überhaupt eine Route, und über
  welchen Next-Hop/welches Interface? `show ip arp` — löst der Next-Hop auf?
- **Pfad:** `traceroute`/`ping` von der **richtigen Quell-Adresse** (`ping <ziel> source <if>`) —
  asymmetrisches Routing und Return-Path-Fehler sind sonst unsichtbar.
- **BGP:** `show ip bgp summary` — Nachbar-State. `Idle`/`Active` = kein TCP/keine Adjazenz (L3/ACL/AS
  falsch); `Connect` = TCP-Handshake hängt; `PfxRcd`=0 trotz `Established` = Filter/Route-Map.
  Details: `show ip bgp neighbor <ip>`.
- **OSPF:** `show ip ospf neighbor` — hängt der State in `ExStart`/`Exchange`? Klassiker: **MTU-Mismatch**
  auf dem Link. `Init` = Hellos kommen nur in eine Richtung (ACL/Unicast-Problem). Area-/Timer-/
  Netzwerktyp-Mismatch prüfen.
- **ACL:** `show ip access-lists <name>` — Hit-Counter zeigt, ob Traffic die erwartete Regel trifft.
  Reihenfolge beachten (erste Übereinstimmung gewinnt), implizites `deny` am Ende.
- **Anti-Pattern:** eine Route für vorhanden halten, weil sie „konfiguriert" ist — die RIB/FIB
  (`show ip route`, `show ip cef <ziel>`) zeigt, was tatsächlich gilt.

### L4+ — Dienste, Firewall, Applikation
- **Firewall/State:** Session-/Policy-Table des Geräts prüfen (PAN-OS: `show session all filter ...`;
  Traffic-Log). Wird der Flow von der erwarteten Regel erlaubt/geblockt? Zonen korrekt zugeordnet?
- **Pfad-MTU:** Verbindung baut auf, große Transfers hängen → **PMTU-Blackhole** (ICMP-Frag-Needed
  irgendwo geblockt). Mit `ping <ziel> size <n> df-bit` die tatsächliche MTU einkreisen.
- **Namensauflösung/Adressvergabe:** DNS (Auflösung vs. Erreichbarkeit trennen), DHCP (Scope
  erschöpft? Relay/Helper-Adresse gesetzt?).
- **Anti-Pattern:** ein Applikationsproblem beim Netz abladen, ohne L4 belegt zu haben — erst zeigen,
  dass der Flow das Gerät erwartungsgemäß passiert (State-/Log-Eintrag), dann weiter oben suchen.

## Vorgehen

1. **Symptom scharf machen:** Was genau, seit wann, für wen, reproduzierbar? Ein Endpunkt oder viele?
2. **Ebene eingrenzen:** Betrifft es einen Link (L1/2), ein Subnetz (L3) oder einen Dienst (L4+)?
   Danach in der Sequenz oben an der passenden Stelle einsteigen (nicht stur bei L1 beginnen, wenn das
   Symptom eindeutig L3 ist — aber die darunterliegenden Ebenen als Gegenprobe nicht überspringen).
3. **Messen vor Schließen:** je Schritt das Show-Kommando (Syntax via `net-reference`), Output deuten,
   Hypothese bestätigen oder verwerfen.
4. **Kette dokumentieren:** „gemessen X → daraus folgt Y". Am Ende die belegte Ursache, nicht die erste
   Vermutung.

## Read-only zuerst

Diagnose ist per Default read-only — `show`/`monitor`/`ping`/`traceroute`. Ein Eingriff zur
Fehlerbehebung (Interface reset, Config-Change) läuft über `net-operate` (Bestätigung + Rollback-Netz),
nie beiläufig aus der Diagnose heraus.
