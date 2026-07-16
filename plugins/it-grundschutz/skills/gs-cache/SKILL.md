---
name: gs-cache
description: "Projekt-lokalen Baustein-Vorrat erzeugen, rebuilden und nachziehen: die Volltexte ausgewählter Bausteine (Übersicht/Gefährdungslage + alle Anforderungen mit aufgelösten Parametern, zitierfähig wie 'gs get') in eine Markdown-Datei neben den Projektdateien materialisieren. Damit liest der Agent die Bausteintexte direkt aus dem Vorrat statt sie für jede ID neu aus dem Korpus zu parsen — beschleunigt Modellierungs-, Soll-Ist- und Dokument-Läufe erheblich. Rebuild ist idempotent (sha256 der catalog.json), zusätzliche IDs werden nachgezogen. Nutzen, wenn für ein Projekt ein fester Satz Bausteine wiederholt gebraucht wird."
---

# gs-cache — projekt-lokaler Baustein-Vorrat

Jeder `gs get <ID>` startet einen Prozess und parst die volle `catalog.json` (~4 MB) neu. Für viele
Anforderungen (Modellierung, Soll-Ist, Dokument) summiert sich das. Dieser Skill **materialisiert** die
Volltexte eines für ein Projekt ausgewählten Baustein-Satzes **einmal** in eine Markdown-Datei neben den
Projektdateien. Der Agent liest danach direkt aus dem Vorrat (Read-Tool) statt den Korpus erneut zu
befragen.

Der Vorrat ist die **Volltext-Ergänzung** zur kuratierten, begründeten Auswahl-Note (Vorbild:
`IAM-Grundschutz-Bausteine`-artige Notizen). Die Auswahl (welche Bausteine) kommt aus `gs-modellierung`
oder einer expliziten Liste; dieser Skill liefert die Texte dazu.

## Baustein-Satz bestimmen

- Aus einer Modellierung: `gs coverage`/`gs list --target …` (siehe `gs-modellierung`) → die zutreffenden
  Baustein-IDs.
- Oder explizit: eine gegebene Liste (z.B. `SYS.1.1 CON.1 ORP.4 NET.3.4 APP.2.1 …`).
- IDs sind **Bausteine** (Gruppen, z.B. `SYS.1.1`) — der Vorrat rendert dann Übersicht/Gefährdungslage +
  alle Anforderungen darunter. Einzelne Anforderungs-IDs (`CON.1.A4`) werden ebenfalls akzeptiert.

## Erzeugen

```bash
nix run .#gs -- [--edition edition-2023] cache \
  --out <projektpfad>/<Name>-Bausteine-Vorrat.md \
  --title "IAM-Stack" \
  SYS.1.1 CON.1 ORP.4 NET.3.4 APP.2.1
```

- **`--out`** (Pflicht): Zielpfad. Die Datei liegt **neben den Projektdateien** — meist im Vault-Projektordner.
  Keinen Ort ausdenken; ist es ein externer Ordner, nennt der User ihn. Elternverzeichnis wird angelegt.
- **`--edition`**: `edition-2023` (klassisches Kompendium) oder `grundschutz-pp` (Default). Muss zur
  Projektmethodik passen.
- **`--title`**: Überschrift/Frontmatter-Titel des Vorrats.

Der Vorrat bekommt YAML-Frontmatter (`gs_cache: true`, `edition`, `quelle_sha256`, `erzeugt`, `bausteine`)
und je Baustein den Volltext — Anforderungs-Wortlaut **textgleich zu `gs get`** (Parameter aufgelöst,
`sec_level`/`effort_level`, Pfad, Quelle CC BY-SA 4.0).

## Rebuild / Nachziehen (idempotent)

Der Rebuild ist einfach **dasselbe Kommando erneut** — Idempotenz über den `sha256` der `catalog.json`:

```bash
# auffrischen (IDs aus der Datei), überspringt wenn Korpus unverändert:
nix run .#gs -- --edition edition-2023 cache --out <datei>.md

# zusätzliche Bausteine nachziehen (werden an den bestehenden Satz ergänzt):
nix run .#gs -- --edition edition-2023 cache --out <datei>.md APP.2.3 APP.6

# Re-Render erzwingen (z.B. nach einer Renderer-Änderung in gs.py, obwohl der Korpus gleich blieb):
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --force

# Frische prüfen (gespeicherter sha vs. aktueller Korpus):
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --status
```

- Ist der Korpus **unverändert** und werden **keine neuen IDs** übergeben (und kein `--force`), meldet der
  Lauf „Vorrat aktuell — nichts zu tun".
- Neue IDs werden zum gespeicherten Satz **gemergt** (nachgezogen), die Datei komplett neu geschrieben.
- Änderte sich der Korpus (`gs-ingest`), meldet `--status` „VERALTET" → einmal ohne `--force` neu bauen
  auffrischt alle Texte.

## Nutzung durch den Agenten

- Bausteintext/Anforderung für ein Projekt zitieren → **zuerst aus dem Vorrat lesen** (Read-Tool auf die
  `…-Bausteine-Vorrat.md`), nur bei fehlendem/veraltetem Vorrat auf `gs get` zurückfallen.
- Der Vorrat ist ein **generiertes Artefakt** („nicht händisch editieren") — die kuratierte Auswahl-Note
  mit Begründung bleibt getrennt und wird vom Agenten/Karin gepflegt.
- Liegt der Vorrat im Vault: Frontmatter minimal halten; Schreiben in den Vault nur auf Projektauftrag.
