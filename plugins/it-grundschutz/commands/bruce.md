---
name: bruce
description: "Bruce (IT-Grundschutz-Berater) aufrufen, lokaler BSI-Korpus (Grundschutz++, Edition 2023): Korpus pflegen, Anforderungen zitierfähig nachschlagen, Szenarien modellieren, Grundschutz-Check (Soll-Ist), ISMS-Dokumente, Editions-Crosswalk, Krypto-Bewertung live nach TR-02102, nicht aus dem Korpus (auch für christian). Nicht für vertrauliche Firmendaten, Security-Recherche ohne Grundschutz-Bezug, Config-Umsetzung oder Wissensablage."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Bruce. Kein Text angegeben: Bruce ohne Auftrag starten —
er führt seinen STARTUP aus (Nix-Umgebung, Korpus-Status) und fragt nach dem Auftrag.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `it-grundschutz:bruce` und gib ihm den User-Text samt Einschränkungen mit,
sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/` oder
`skills/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten):

1. Root bestimmen, nicht suchen: Nimm den absoluten Pfad dieser Skill-Datei aus der Skill-Liste
   (Skill-Root plus Kurzpfad). Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor,
   sonst das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis,
   keine andere Version aus dem Plugin-Cache, keine relativen Pfade. Prüfe, dass
   `<root>/agents/bruce.md` existiert.
2. Starte einen Subagenten, wenn du das kannst, sonst arbeite selbst. Mit Subagent liest du
   `agents/bruce.md` und die Dateien unter `skills/` nicht selbst.
3. Auftrag an ihn, `<root>` als absoluten Pfad ausgeschrieben: `<root>/agents/bruce.md` lesen, das
   Frontmatter ignorieren, den Body als Rollenanweisung befolgen und `${CLAUDE_PLUGIN_ROOT}` darin als
   `<root>` lesen. Danach den User-Text bearbeiten.

Routing-Hinweis:
- **Bruce** ist für IT-Grundschutz-Arbeit auf Basis des lokalen OSCAL-Korpus: Anforderung/Baustein
  nachschlagen (per ID wie `GC.1.1` oder Thema), Bausteine für ein Szenario modellieren, Editionen
  abgleichen (Crosswalk Edition 2023 ↔ Grundschutz++), den Korpus von der BSI-Quelle laden/aktualisieren,
  Sicherheitsdokumente nach der Methodik erstellen/führen/prüfen, den IT-Grundschutz-Check
  (Soll-Ist-Umsetzungsprüfung) durchführen, einen projekt-lokalen Baustein-Vorrat pflegen sowie
  kryptographische Verfahren/Schlüssellängen/Cipher-Suiten nach BSI TR-02102 zitierfähig bewerten.
- Geht es um **firmenspezifische, vertrauliche** Modellierung (konkrete Informationsverbünde,
  Umsetzungsstände) — das gehört **nicht** in dieses teilbare Plugin. Bruce steuert nur die generische
  Grundschutz-Ebene bei; die vertrauliche Ebene gehört in ein getrenntes Repo/Vault.
- Soll eine Härtung in einer **Config umgesetzt** werden, ist **Christian** (`christian:christian`, Linux/BSD,
  VPN) bzw. **Bertram** (`bertram:bertram`, Netzwerk-Hardware) die bessere Wahl; Bruce liefert die
  Krypto-Bewertung nach TR-02102 zu.
- Geht es um **allgemeine Wissensrecherche/Archivierung ohne Grundschutz-Bezug** und ist ein
  Wissensmanagement-Agent installiert (z.B. **Karin** / `bibliothekarin`), ist dieser die bessere Wahl.
