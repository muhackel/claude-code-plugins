# Elementare Pakete und Plugins

Referenz zu `bsd-firewall`, lesen bevor ein Paket (pfSense) oder `os-*`-Plugin (OPNsense) empfohlen, benannt oder installiert wird.

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
