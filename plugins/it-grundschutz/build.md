# build.md — it-grundschutz

Build-/Laufumgebung fuer die Korpus-Pipeline (Ingest) und das OSCAL-Lookup-CLI. Reine Nix-Flake, keine
systemweiten Abhaengigkeiten.

## Voraussetzungen

- **Nix mit Flakes** (`experimental-features = nix-command flakes`).
- Netzwerkzugang fuer den Ingest (laedt den Katalog von GitHub).
- Kein systemweites Python/jq/curl noetig — alles kommt aus dem Flake.

## Entwicklungsumgebung

```bash
nix develop          # Shell mit python3, curl, jq, coreutils
# darin direkt:
scripts/ingest.sh
scripts/gs.py status
```

## Bauen & Starten

Die „Erzeugnisse" sind drei Apps:

```bash
nix run .#ingest                  # Grundschutz++-Korpus laden/aktualisieren
nix run .#ingest -- --force       # erzwingt Neuladen unabhaengig von last-modified
nix run .#ingest-2023             # Edition 2023 (DocBook-XML) laden + nach OSCAL normalisieren
nix run .#ingest-2023 -- --file kompendium.xml  # offline: lokale XML statt Download

nix run .#gs -- status            # Korpus-Status (= Default-App: nix run . -- status)
nix run .#gs -- groups
nix run .#gs -- list GC
nix run .#gs -- get GC.1.1
nix run .#gs -- search "Notfall"
nix run .#gs -- prozess           # Vorgehensweise als Schrittfolge (Methodik-Ebene)
nix run .#gs -- checklist UMS      # leere Soll-Ist-Check-Vorlage (Markdown-Tabelle) einer Schicht/Gruppe
nix run .#gs -- json GC.1.1       # rohes OSCAL-Control

# Edition 2023 abfragen (--edition vor dem Kommando; alternativ Env GS_EDITION):
nix run .#gs -- --edition edition-2023 status
nix run .#gs -- --edition edition-2023 groups
nix run .#gs -- --edition edition-2023 get SYS.1.1.A5
```

## Testen

```bash
nix flake check                   # Flake-Syntax + Apps validieren
```

Schnelltest der Lookup-Logik gegen einen vorhandenen Korpus:

```bash
nix run .#ingest && nix run .#gs -- status
```

## Projektspezifisches

- **Korpus-Ort:** `$GS_CORPUS_DIR` (default `~/.local/share/it-grundschutz/corpus`). Bewusst ausserhalb des
  Git-Repos — der Korpus steht unter CC BY-SA 4.0 und wird nie eingecheckt. Je Edition ein Unterordner:
  `grundschutz-pp/` und `edition-2023/`.
- **Manifest:** je Edition ein `manifest.json` (Quelle, `sha256`, Abrufdatum, Lizenz, Anzahl). `ingest`
  (Grundschutz++) aktualisiert nur bei geaendertem `last-modified` (oder `--force`).
- **Update-Disziplin:** Grundschutz++ wird agil gepflegt — bei Aktualitaetsbedarf `nix run .#ingest`.
  Edition 2023 ist statisch (Stand 2023) — einmal `nix run .#ingest-2023` genügt.
- **Edition 2023:** `scripts/adapter-2023.py` normalisiert das DocBook-XML
  (`XML_Kompendium_2023.xml`, bsi.bund.de) strukturgleich nach `$GS_CORPUS_DIR/edition-2023/`. Reine
  Python-Stdlib (`xml.etree.ElementTree`, `urllib`) — keine Zusatzpakete im Flake nötig. Abfrage über
  `gs.py --edition edition-2023`; danach kann `gs-crosswalk` zwischen den Editionen mappen.
