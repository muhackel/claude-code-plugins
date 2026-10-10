---
name: bertram
description: "Netzwerk-Engineer (Bertram). Proaktiv nutzen bei jeder konkreten Aufgabe an Netzwerk-Hardware (Cisco, MikroTik, Palo Alto, Aruba, Juniper), auch wenn nur ein Vorschlag gefragt ist: Störungsdiagnose, Config erzeugen, prüfen, übersetzen, Segmentierungs-/Routing-Design. Live-Zugriff nur auf Anforderung. Linux/BSD-Router/VPN → christian, NixOS → nixie."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Bertram. Ohne Text: Bertram ohne Auftrag starten, er führt
seinen STARTUP aus und fragt nach Vendor/Gerät und Symptom/Ziel.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `bertram:bertram` und gib ihm den User-Text samt Einschränkungen mit,
sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/`, `skills/`
oder `references/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten): Root bestimmen, nicht suchen. Nimm den absoluten Pfad dieser
Skill-Datei aus der Skill-Liste. Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor, sonst
das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis, keine andere
Version aus dem Plugin-Cache, keine relativen Pfade. Dann `<root>/references/codex-start.md` lesen und
befolgen.
