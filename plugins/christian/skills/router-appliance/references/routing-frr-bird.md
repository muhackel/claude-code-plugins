# Routing mit FRR / BIRD

Referenz zu `router-appliance`, lesen vor FRR-/BIRD-Direktiven, Protokollwahl (OSPF/BGP/statisch), Fragen zur Kernel-FIB oder ECMP.

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
- **Statisch** reicht für Stub-/Single-Uplink-Router — kein Daemon, Routen über iproute2 (siehe `networkd-iproute2.md` daneben).
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
  Muss zur `ip rule`-Logik passen (siehe `networkd-iproute2.md` daneben).

### ECMP
- Mehrere gleichwertige Nexthops → Equal-Cost-Multipath. Kernel-seitig `nexthop`-Gruppen; der
  Hash-Algorithmus über `net.ipv4.fib_multipath_hash_policy` (L3 vs. L3+L4) — **per sysctl-Doku
  verifizieren**. Layer-4-Hash streut besser, kann aber PMTU/State-Annahmen brechen.
- FRR/BIRD müssen ECMP-fähig konfiguriert sein (Maximum-Paths). Asymmetrie bedenken → `rp_filter`
  entschärfen.
