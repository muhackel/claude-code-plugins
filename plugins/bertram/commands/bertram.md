---
name: bertram
description: "Bertram (Netzwerk-Engineer) aufrufen, vendor-agnostisch (u. a. Cisco, MikroTik, Palo Alto, HP/Aruba, Juniper): Störungsdiagnose L1–L7, Config erzeugen, prüfen und übersetzen, Befehlsreferenz, Segmentierungs-, Firewall- und Routing-Design, Live-Zugriff nur auf Anforderung. Nicht für Linux/BSD-VPN, -Router und -Firewalls inkl. pfSense/OPNsense oder reine NixOS-Umsetzung."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Bertram. Kein Text angegeben: Bertram ohne Auftrag starten —
er fragt nach Vendor/Gerät und Symptom/Ziel.

**Claude Code:** Spawne den Agenten `bertram:bertram`.

**Codex** kennt keine Plugin-Agenten. Der Plugin-Root ist unter Claude Code `${CLAUDE_PLUGIN_ROOT}`; beginnt
dieser Wert nicht mit `/`, bist du in Codex. Dann:

1. Root bestimmen, nicht suchen: Nimm den absoluten Pfad dieser Skill-Datei aus der Skill-Liste
   (Skill-Root plus Kurzpfad). Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor,
   sonst das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis,
   keine andere Version aus dem Plugin-Cache, keine relativen Pfade. Prüfe, dass
   `<root>/agents/bertram.md` existiert.
2. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/bertram.md` und die Dateien unter `skills/` nicht selbst.
3. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben: `<root>/agents/bertram.md` lesen, das
   Frontmatter ignorieren, den Body als Rollenanweisung befolgen und `${CLAUDE_PLUGIN_ROOT}` darin als
   `<root>` lesen. Danach den User-Text bearbeiten.

Routing-Hinweis:
- **Bertram** ist für Netzwerk-Arbeit: Diagnose/Troubleshooting (L1–L7), Konfiguration erzeugen und
  gegenprüfen, Vendor-Dialekt-Übersetzung (Cisco IOS/IOS-XE/NX-OS, MikroTik RouterOS, Palo Alto PAN-OS,
  HP/Aruba, Junos), Befehlsreferenz/Best-Practice-Lookup, Segmentierungs-/Routing-/Firewall-Design und
  — nur auf explizite Anforderung — Live-Zugriff per SSH.
- Geht es um eine **Linux-VPN- oder Router-Appliance-Aufgabe** (OpenVPN/WireGuard/nftables/FRR auf
  Linux), ist **Christian** (`christian:christian`) die bessere Wahl; geht es um **reine
  NixOS-Umsetzung** ohne Netzwerk-Designanteil, ist es **Nixie** (`nixie:nixie`).
- Geht es im User-Text **ausschließlich** um allgemeine Wissensrecherche oder das Dokumentieren in einer
  Knowledge Base ohne konkrete Netzwerk-Aufgabe und ist ein Wissensmanagement-Agent installiert (z.B.
  **Karin** / `bibliothekarin`), ist dieser die bessere Wahl — dann ihn spawnen statt Bertram.
- Mischfall (Netzwerk-Aufgabe, die nebenbei tiefe Recherche braucht): Bertram spawnen. Er recherchiert
  selbst; ist ein Wissensmanagement-Agent installiert, kann er optional ein Recherche-Briefing
  zurückliefern, das du anschließend an diesen gibst.
