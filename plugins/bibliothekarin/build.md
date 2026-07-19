# build.md — bibliothekarin

Build-/Laufumgebung für Karins **Offline-Diagramm-Doku** (Mermaid + PlantUML) und das **lokale Rendering**
von Diagrammen. Reine Nix-Flake, keine systemweiten Abhängigkeiten.

## Voraussetzungen

- **Nix mit Flakes** (`experimental-features = nix-command flakes`).
- Netzwerkzugang für das Beschaffen der Doku (Mermaid-Git, plantuml.com, Reference-Guide-PDF).
- Kein systemweites git/wget/pdftotext/jq nötig — alles kommt aus dem Flake.

## Entwicklungsumgebung

```bash
nix develop          # Shell mit mmdc, plantuml, graphviz, git, wget, pdftotext (poppler-utils), jq, coreutils
# darin direkt:
scripts/fetch-diagram-docs.sh --status
scripts/fetch-diagram-docs.sh
```

Enthaltene Tools:

- **mmdc** — Mermaid-CLI zum Rendern von `.mmd` nach SVG/PNG (aus `mermaid-cli`)
- **plantuml** — PlantUML zum Rendern von `.puml` (zieht die JRE, Backend `graphviz`)
- **pdftotext** — aus `poppler-utils`, wandelt den PlantUML-Reference-Guide in durchsuchbaren Text
- **git** — sparse/partial clone der Mermaid-Doku
- **wget** — Mirror der plantuml.com-Diagrammtypseiten + PDF-Download
- **jq** — Manifest-Handling (Altersgate)

## Bauen & Starten

Das „Erzeugnis" ist die App `fetch-docs`, die die Offline-Doku befüllt bzw. aktualisiert:

```bash
nix run .#fetch-docs                 # beide Quellen prüfen und bei Bedarf ziehen (Altersgate)
nix run .#fetch-docs -- --status     # nur Zustand + Alter je Quelle zeigen, nichts ziehen
nix run .#fetch-docs -- --force      # Altersgate ignorieren, immer neu ziehen
nix run .#fetch-docs -- --help       # Kurzhilfe

# optional eine Quelle eingrenzen:
nix run .#fetch-docs -- mermaid
nix run .#fetch-docs -- --force plantuml
```

Nach dem Lauf liegen:

- **Mermaid:** `~/.local/share/bibliothekarin/diagram-docs/mermaid/repo/packages/mermaid/src/docs/` (Markdown)
- **PlantUML:** `~/.local/share/bibliothekarin/diagram-docs/plantuml/site/` (Website-Mirror) und
  `.../plantuml/PlantUML_Language_Reference_Guide_en.txt` (Reference Guide als Text, plus `guide.pdf`)

## Testen

```bash
nix flake check                      # Flake-Syntax + Apps validieren
nix run .#fetch-docs -- --help       # App startet, Hilfe erscheint
```

Rendering-Schnelltest (in `nix develop`):

```bash
# Mermaid
printf 'graph TD; A-->B;' > sample.mmd
mmdc -i sample.mmd -o sample.svg      # erzeugt sample.svg

# PlantUML
printf '@startuml\nA -> B\n@enduml\n' > sample.puml
plantuml sample.puml                  # erzeugt sample.png
```

## Projektspezifisches

- **Cache-Ort:** `$DIAGRAM_DOCS_DIR` (default `~/.local/share/bibliothekarin/diagram-docs`). Bewusst
  **außerhalb des Git-Repos** (XDG-Datenverzeichnis) — die Offline-Doku wird **nie eingecheckt**. Je Quelle
  ein Unterordner: `mermaid/` und `plantuml/`.
- **Env-Override:** `DIAGRAM_DOCS_DIR=/anderer/pfad nix run .#fetch-docs` legt die Doku woanders ab.
- **Manifest:** je Quelle ein `manifest.json` mit `quelle` (URL), `abgerufen_am` (Unix-Epoch) und
  `abgerufen_am_iso` (UTC-Zeitstempel). Steuert das Altersgate.
- **14-Tage-Altersgate:** Ohne Flags wird eine Quelle nur neu gezogen, wenn ihr `abgerufen_am` älter als
  14 Tage ist (oder Manifest/Ordner fehlen). Ist sie jünger, wird sie mit Meldung „aktuell (N Tage alt)"
  übersprungen. `--force` ignoriert das Gate, `--status` zeigt nur den Zustand (fehlt/fällig/aktuell).
- **Quellen:**
  - *Mermaid* — sparse/partial git clone (`--filter=blob:none`, sparse-checkout auf
    `packages/mermaid/src/docs`) aus `github.com/mermaid-js/mermaid`; Update per `git pull`.
  - *PlantUML* — wget-Mirror von `plantuml.com` (Tiefe 1, hostbeschränkt, ohne Wartezeit) plus der
    Language Reference Guide von `pdf.plantuml.net`, per `pdftotext -layout` in Text gewandelt.
- **Wichtig (Nix):** Das nixpkgs-Attribut für `pdftotext` heißt `poppler-utils` (mit Bindestrich) — das
  Unterstrich-Attribut `poppler_utils` existiert nicht mehr.
