---
name: christian
description: "Christian (Linux-VPN- & Router-Spezialist) aufrufen: OpenVPN, WireGuard, IPsec und Mesh-VPN entwerfen, prüfen, härten und entstören, Standorte koppeln, Linux-Router und -Firewalls (nftables, FRR, OpenWrt) sowie pfSense/OPNsense bauen, Syntax belegen, Live-Zugriff nur auf Anforderung. Nicht für kommerzielle Hardware (Cisco, MikroTik, Palo Alto, Juniper), reine NixOS-Umsetzung oder Krypto-Bewertung ohne VPN-Aufgabe."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Christian. Kein Text angegeben: Christian ohne Auftrag
starten — er fragt nach Ziel (VPN/Router/WAN), Endpunkten/Netzen und Plattform.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `christian:christian` und gib ihm den User-Text samt Einschränkungen mit,
sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/` oder
`skills/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten):

1. Root bestimmen, nicht suchen: Nimm den absoluten Pfad dieser Skill-Datei aus der Skill-Liste
   (Skill-Root plus Kurzpfad). Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor,
   sonst das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis,
   keine andere Version aus dem Plugin-Cache, keine relativen Pfade. Prüfe, dass
   `<root>/agents/christian.md` existiert.
2. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/christian.md` und die Dateien unter `skills/` nicht selbst.
3. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben: `<root>/agents/christian.md` lesen, das
   Frontmatter ignorieren, den Body als Rollenanweisung befolgen und `${CLAUDE_PLUGIN_ROOT}` darin als
   `<root>` lesen. Danach den User-Text bearbeiten.

Routing-Hinweis:
- **Christian** ist für Linux-VPN- und Router-Arbeit: OpenVPN/WireGuard/IPsec-Tunnel entwerfen und
  gegenprüfen, Linux-Router-Appliances bauen (OpenWrt/DD-WRT/generisches Linux, VyOS/NixOS rudimentär),
  **BSD-Firewall-Appliances pfSense/OPNsense** (pf, config.xml, Gateway-Groups, elementare Plugins),
  nftables-Firewall und FRR-Routing, sichere WAN-Kopplungen zwischen Netzen, Config-/Krypto-/Manpage-
  Referenz-Lookup und — nur auf explizite Anforderung — Live-Zugriff per SSH.
- **pfSense/OPNsense gehören zu Christian**, nicht zu bertram — sie sind Open-Source-BSD-Firewalls,
  keine kommerzielle Hardware.
- Geht es im User-Text um **kommerzielle Netzwerk-Hardware** (Cisco, MikroTik/RouterOS, Palo Alto/
  PAN-OS, Juniper), ist **bertram** die bessere Wahl — dann ihn spawnen statt Christian.
- Geht es um eine **reine NixOS-Umsetzung/Deploy** ohne VPN-/Router-Designanteil, ist **nixie** die
  bessere Wahl.
- Ist es eine **Krypto-Tiefenfrage** (Suite-Bewertung, Compliance-Härtung) ohne konkrete VPN-/Router-
  Aufgabe und ist **bruce** installiert, ist dieser die bessere Wahl.
- Mischfall (Linux-VPN-/Router-Aufgabe, die Nix-Umsetzung oder Krypto-Bewertung braucht): Christian
  spawnen. Er entwirft plattform-agnostisch und liefert ggf. ein Briefing zurück, das du anschließend
  an nixie bzw. bruce gibst.
