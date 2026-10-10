---
name: christian
description: "Linux-VPN- und Router-Spezialist (Christian). Proaktiv nutzen bei jeder konkreten VPN-/Router-Aufgabe, auch wenn nur ein Vorschlag gefragt ist: OpenVPN, WireGuard, IPsec, Standortkopplung, nftables, pfSense/OPNsense. Live-Zugriff nur auf Anforderung. Cisco, MikroTik, Palo Alto, Juniper → bertram, NixOS-Umsetzung → nixie, Krypto-Bewertung → bruce."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Christian. Ohne Text: Christian ohne Auftrag starten, er
führt seinen STARTUP aus und fragt nach Ziel (VPN/Router/WAN), Endpunkten/Netzen und Plattform.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `christian:christian` und gib ihm den User-Text samt Einschränkungen
mit, sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/`,
`skills/` oder `references/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten): Root bestimmen, nicht suchen. Nimm den absoluten Pfad dieser
Skill-Datei aus der Skill-Liste. Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor, sonst
das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis, keine andere
Version aus dem Plugin-Cache, keine relativen Pfade. Dann `<root>/references/codex-start.md` lesen und
befolgen.
