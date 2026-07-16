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

## Zwei Modi

**(1) Szenario-Modus (empfohlen, Edition 2023)** — der Satz wird aus den **Asset-Typen des Plans**
abgeleitet (`--targets`, dieselbe Heuristik wie `gs coverage`: komponentengebundene Bausteine +
übergreifende). Ändert sich der Netzplan, wird der Satz beim Rebuild **deckungsgleich** nachgeführt.

**(2) Manuell-Modus** — explizite Baustein-IDs (`SYS.1.1 CON.1 …`), additiv, ohne Pruning. Für
grundschutz-pp der einzige Weg (dort modelliert `coverage` Anforderungen, keine Baustein-Menge).

Bausteine sind **Gruppen** (z.B. `SYS.1.1`) → gerendert werden Übersicht/Gefährdungslage + alle
Anforderungen darunter. Einzelne Anforderungs-IDs (`CON.1.A4`) sind ebenfalls erlaubt.

## Erzeugen (Szenario)

```bash
nix run .#gs -- --edition edition-2023 cache \
  --out <projektpfad>/<Name>-Bausteine-Vorrat.md \
  --title "IAM-Stack" \
  --targets "Server,Netz,Verzeichnisdienst,Virtualisierung" \
  APP.2.3            # optionale Hand-Pins (Bausteine, die die Heuristik nicht liefert)
```

- **`--out`** (Pflicht): Zielpfad **neben den Projektdateien** — meist im Vault-Projektordner. Keinen Ort
  ausdenken; ist es ein externer Ordner, nennt der User ihn. Elternverzeichnis wird angelegt.
- **`--targets`**: Asset-Typen des Plans (Liste via `gs --edition edition-2023 coverage` ohne Argument).
- **Positionale IDs** bei gesetztem `--targets` = **Hand-Pins**: Bausteine, die immer im Vorrat bleiben,
  auch wenn die Heuristik sie nicht ableitet (vgl. die „bedingt/prüfen"-Zeilen einer Modellierungs-Note).
- **`--title`**: Überschrift/Frontmatter-Titel.

Der Vorrat bekommt YAML-Frontmatter (`gs_cache`, `edition`, `targets`, `quelle_sha256`, `erzeugt`,
`bausteine`, `bausteine_manuell`) und je Baustein den Volltext — Anforderungs-Wortlaut **textgleich zu
`gs get`** (Parameter aufgelöst, `sec_level`/`effort_level`, Pfad, Quelle CC BY-SA 4.0).

## Rebuild — aus dem Szenario neu ableiten (mit Pruning)

Der Rebuild ist **dasselbe Kommando erneut**. Im Szenario-Modus wird der Satz aus `targets` **neu
abgeleitet** und **deckungsgleich** gemacht — neue Bausteine rein, weggefallene raus; Hand-Pins bleiben.
Idempotenz über den `sha256` der `catalog.json` + unveränderte `targets`/Pins.

```bash
# Komponente ergänzen (z.B. Windows-Server -> Asset-Typ "Server" liefert SYS.1.2.2; neuer Typ -> dessen Bausteine):
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --targets "Server,Netz,Verzeichnisdienst,Datenbank"
#   -> meldet: nachgezogen: APP.4.3 …

# Komponente entfällt -> targets reduzieren -> deren Bausteine werden gepruned (Hand-Pins bleiben):
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --targets "Server,Netz"
#   -> meldet: entfernt (pruned): …

# Hand-Pin entfernen:
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --unpin APP.2.3

# unverändert -> nichts zu tun;  --force erzwingt Re-Render;  --status zeigt Frische + targets + Pins
nix run .#gs -- --edition edition-2023 cache --out <datei>.md --status
```

- Wird `--targets` beim Rebuild weggelassen, gelten die **gespeicherten** `targets` (nur auffrischen).
- **Manuell-Modus** (keine `targets` gespeichert/übergeben): neue IDs werden additiv **nachgezogen**,
  ohne Pruning; `--unpin` gibt es dort nicht.
- Änderte sich der Korpus (`gs-ingest`), meldet `--status` „VERALTET" → einmal neu bauen frischt alle Texte auf.

## Nutzung durch den Agenten

- Bausteintext/Anforderung für ein Projekt zitieren → **zuerst aus dem Vorrat lesen** (Read-Tool auf die
  `…-Bausteine-Vorrat.md`), nur bei fehlendem/veraltetem Vorrat auf `gs get` zurückfallen.
- Der Vorrat ist ein **generiertes Artefakt** („nicht händisch editieren") — die kuratierte Auswahl-Note
  mit Begründung bleibt getrennt und wird vom Agenten/Karin gepflegt.
- Liegt der Vorrat im Vault: Frontmatter minimal halten; Schreiben in den Vault nur auf Projektauftrag.
