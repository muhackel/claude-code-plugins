# OpenWrt / DD-WRT

Referenz zu `router-appliance`, lesen bevor UCI-, opkg- oder firewall4-Zeilen ausgegeben oder geprüft werden oder ein OpenWrt-/DD-WRT-Ziel angefasst wird.

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
