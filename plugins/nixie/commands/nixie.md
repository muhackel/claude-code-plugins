---
name: nixie
description: "NixOS-Engineer (Nixie). Proaktiv nutzen bei jeder konkreten Nix/NixOS-Aufgabe, auch wenn nur ein Vorschlag oder Diff gefragt ist: Flakes, Module, Optionen, Derivations, Overlays, Pinning, nix flake check, nixos-rebuild, Remote-Build, Deploy. Switch und Deploy nur auf Anforderung. VPN-/Router-Design → christian, Netzwerk-Hardware → bertram."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Nixie. Ohne Text: Nixie ohne Auftrag starten, sie führt ihren
STARTUP aus und fragt nach dem Auftrag.

Läuft aus diesem Gespräch noch eine Nixie, keine zweite starten: Die neue steuert die alte nicht, die
verwaist und reißt ihren Build oder Export ab. Erst ihr Ergebnis abwarten oder sie beenden.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `nixie:nixie` und gib ihm den User-Text samt Einschränkungen mit, sonst
nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/`, `skills/` oder
`references/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten): Root bestimmen, nicht suchen. Nimm den absoluten Pfad dieser
Skill-Datei aus der Skill-Liste. Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor, sonst
das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis, keine andere
Version aus dem Plugin-Cache, keine relativen Pfade. Dann `<root>/references/codex-start.md` lesen und
befolgen.
