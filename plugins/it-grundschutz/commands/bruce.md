---
name: bruce
description: "IT-Grundschutz-Berater (Bruce), lokaler BSI-Korpus. Proaktiv nutzen bei jeder konkreten Grundschutz-Aufgabe, auch wenn nur ein Vorschlag gefragt ist: zitierfähig nachschlagen, Szenarien modellieren, Grundschutz-Check, ISMS-Dokumente, Crosswalk, Krypto-Bewertung nach TR-02102. Keine vertraulichen Firmendaten. Config-Umsetzung → christian, bertram."
disable-model-invocation: true
---

Übergib den User-Text als Arbeitsauftrag an Bruce. Ohne Text: Bruce ohne Auftrag starten, er führt seinen
STARTUP aus und fragt nach dem Auftrag.

Plugin-Root: `${CLAUDE_PLUGIN_ROOT}`. Beginnt dieser Wert mit `/`, bist du in Claude Code, sonst in Codex.

**Claude Code:** Spawne den Agenten `it-grundschutz:bruce` und gib ihm den User-Text samt Einschränkungen
mit, sonst nichts. Er bringt Rollenanweisung und Fachwissen selbst mit: keine Anweisung, `agents/`,
`skills/` oder `references/` zu lesen. Der Codex-Teil unten gilt hier nicht.

**Nur Codex** (kennt keine Plugin-Agenten): Root bestimmen, nicht suchen. Nimm den absoluten Pfad dieser
Skill-Datei aus der Skill-Liste. Liegt er unter `.codex-plugin/`, ist der Root das Verzeichnis davor, sonst
das nächste Verzeichnis darüber mit `.codex-plugin/plugin.json`. Nicht das Arbeitsverzeichnis, keine andere
Version aus dem Plugin-Cache, keine relativen Pfade. Dann `<root>/references/codex-start.md` lesen und
befolgen.
