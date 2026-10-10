# Netz-Layer: iproute2 / systemd-networkd

Referenz zu `router-appliance`, lesen vor Adress-/Routen-Konfiguration, Policy-Routing, VRF, Forwarding-/rp_filter-sysctls, Bridges oder VLANs.

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
