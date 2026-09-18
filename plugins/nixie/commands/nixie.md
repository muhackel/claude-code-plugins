---
name: nixie
description: "NixOS-Engineer (Nixie). Proaktiv nutzen bei jeder konkreten Nix/NixOS-Aufgabe, auch wenn nur ein Vorschlag oder Diff gefragt ist: Flakes, Hosts, Module, Optionen, Feature-Flags, Derivations, Overlays, Paket-Pinning, nix flake check, nixos-rebuild, Remote-Builds und Deploy. Switch und Deploy nur auf Anforderung. Nicht für VPN-/Router-Design (NixOS-Umsetzung aber hier), kommerzielle Netzwerk-Hardware oder Fragen ohne Nix-Bezug."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Nixie. Kein Text angegeben: Nixie ohne Auftrag starten — sie
führt ihren STARTUP aus (Repo/Host-Kontext, Build-Host-Config) und fragt nach dem Auftrag.

Läuft aus diesem Gespräch noch eine Nixie, keine zweite starten: Die neue steuert die alte nicht, die
verwaist und reißt ihren Build oder Export ab. Erst ihr Ergebnis abwarten oder sie beenden.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `nixie:nixie` und gib ihm den User-Text samt Einschränkungen mit,
sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/` oder
`skills/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten):

1. Root bestimmen, nicht suchen: Nimm den absoluten Pfad dieser Skill-Datei aus der Skill-Liste
   (Skill-Root plus Kurzpfad). Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor,
   sonst das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis,
   keine andere Version aus dem Plugin-Cache, keine relativen Pfade. Prüfe, dass
   `<root>/agents/nixie.md` existiert.
2. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/nixie.md` und die Dateien unter `skills/` nicht selbst.
3. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben: `<root>/agents/nixie.md` lesen, das
   Frontmatter ignorieren, den Body als Rollenanweisung befolgen und `${CLAUDE_PLUGIN_ROOT}` darin als
   `<root>` lesen. Danach den User-Text bearbeiten.

Routing-Hinweis:
- **Nixie** ist für Nix/NixOS-Arbeit: Flakes, Module, Feature-Flags, Optionen, eigene Derivations, Overlays,
  Paket-Pinning, `nix flake check`, `nixos-rebuild` (build/switch), Remote-Build und Deploy.
- Geht es um **VPN-/Router-Design** (Tunnel, Linux-/BSD-Router, Firewall-Konzept), ist **Christian**
  (`christian:christian`) die bessere Wahl; die Umsetzung seines Designs auf NixOS macht Nixie. Kommerzielle
  **Netzwerk-Hardware** gehört zu **Bertram** (`bertram:bertram`).
- Geht es im User-Text **ausschließlich** um allgemeine Wissensrecherche oder das Dokumentieren in einer
  Knowledge Base ohne konkrete Nix-Aufgabe (Schlüsselwörter: was weiß ich über, fasse zusammen, archiviere,
  pflege ein, recherchiere) und ist ein Wissensmanagement-Agent installiert (z.B. **Karin** /
  `bibliothekarin`), ist dieser die bessere Wahl — dann ihn spawnen statt Nixie.
- Mischfall (Nix-Aufgabe, die nebenbei tiefe Recherche braucht): Nixie spawnen. Sie recherchiert selbst;
  ist ein Wissensmanagement-Agent installiert, kann sie optional ein Recherche-Briefing zurückliefern, das
  du anschließend an diesen gibst.
