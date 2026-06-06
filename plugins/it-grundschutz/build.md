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

Die „Erzeugnisse" sind zwei Apps:

```bash
nix run .#ingest                  # Grundschutz++-Korpus laden/aktualisieren
nix run .#ingest -- --force       # erzwingt Neuladen unabhaengig von last-modified

nix run .#gs -- status            # Korpus-Status (= Default-App: nix run . -- status)
nix run .#gs -- groups
nix run .#gs -- list GC
nix run .#gs -- get GC.1.1
nix run .#gs -- search "Notfall"
nix run .#gs -- json GC.1.1       # rohes OSCAL-Control
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
  Git-Repos — der Korpus steht unter CC BY-SA 4.0 und wird nie eingecheckt.
- **Manifest:** `$GS_CORPUS_DIR/grundschutz-pp/manifest.json` haelt Quelle, `last_modified`, `sha256`,
  Abrufdatum und Lizenz fest. `ingest` aktualisiert nur, wenn sich `last-modified` aendert (oder `--force`).
- **Update-Disziplin:** Grundschutz++ wird agil gepflegt — bei Aktualitaetsbedarf `nix run .#ingest`.
- **Edition 2023 (geplant):** Adapter DocBook-XML → OSCAL nach `$GS_CORPUS_DIR/edition-2023/`; danach kann
  `gs-crosswalk` zwischen den Editionen mappen.
