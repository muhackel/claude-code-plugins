---
name: gs-ingest
description: "Den BSI-Korpus lokal vorhalten: die Grundschutz++-OSCAL-Dateien (Anwenderkatalog, Methodik-Quellkatalog, Profile) von der BSI-Stand-der-Technik-Bibliothek (GitHub) laden, ins lokale Datenverzeichnis cachen, mit Manifest (Quelle, Version, sha256, Abrufdatum je Datei) versehen und aktuell halten. Nutzen, bevor nachgeschlagen/modelliert/dokumentiert wird, wenn kein Korpus vorliegt oder ein Update ansteht."
---

# gs-ingest — Korpus laden und aktuell halten

Der Agent arbeitet **nur** gegen einen lokal vorgehaltenen Korpus. Dieser Skill beschafft und pflegt ihn —
in drei Ebenen, die alle aus demselben BSI-Repo stammen.

## Quellen (kanonisch)

Repo: `BSI-Bund/Stand-der-Technik-Bibliothek` (GitHub), Format **OSCAL 1.1.x** (JSON), Lizenz **CC BY-SA 4.0**.

| Ebene | Datei im Repo | lokal |
|-------|---------------|-------|
| **anwender** | `Anwenderkataloge/Grundschutz++/Grundschutz++-catalog.json` | `catalog.json` |
| **methodik** | `Quellkataloge/Methodik-Grundschutz++/BSI-Methodik-Grundschutz++-catalog.json` | `methodik-catalog.json` |
| **profile** | `Quellkataloge/Methodik-Grundschutz++/Grundschutz++-profile.json` | `profile.json` |

`anwender` = konkrete Anforderungen (~651), `methodik` = Vorgehensweise (~61, IDs ⊆ Anwender), `profile`
verknuepft beide. Die `++` im Pfad muessen URL-encodiert werden (`%2B%2B`).

## Datenort (nie ins Plugin-Git)

Wegen CC BY-SA wird der Korpus **nicht** in dieses (MIT-)Plugin eingecheckt:

```
$GS_CORPUS_DIR            (default: ~/.local/share/it-grundschutz/corpus)
  grundschutz-pp/
    catalog.json          # Anwenderkatalog
    methodik-catalog.json # Methodik-Quellkatalog (Vorgehensweise)
    profile.json          # OSCAL-Profile (Methodik <-> Anwender)
    manifest.json         # Liste je Datei: quelle, last_modified, sha256, anzahl; + abgerufen_am, lizenz
  edition-2023/           # spaetere Ausbaustufe (DocBook-XML -> OSCAL)
```

## Nix-Umgebung zuerst

Skripte brauchen `python3`, `curl`, `jq`, `coreutils` — ueber das Flake bereitstellen:

```bash
nix run .#ingest            # alle drei Ebenen laden/aktualisieren
nix run .#ingest -- --force # Neuladen erzwingen (sonst sha-basiert uebersprungen)
nix develop                 # Shell mit den Tools, dann scripts/ direkt
```

## Workflow

1. **Status:** `nix run .#gs -- status` — welche Ebenen liegen vor, welcher Stand, wie viele Anforderungen?
2. **Laden/Aktualisieren:** `nix run .#ingest` zieht je Ebene die Datei, validiert das OSCAL-JSON
   (Katalog vs. Profile), schreibt sie und baut das `manifest.json` neu. Je Datei wird per **sha256**
   entschieden, ob sich etwas geaendert hat — unveraenderte Dateien werden uebersprungen.
3. **Verifizieren:** nach dem Ingest `status` erneut — Zahlen plausibel, `last-modified` aktuell?
4. **Nicht spammen:** nicht bei jeder Sitzung ungefragt neu ziehen; Update anbieten, wenn das Manifest alt ist.

## Spaeter: Edition 2023

Edition 2023 liegt als **DocBook-XML** vor (`bsi.bund.de`). Ein Adapter normalisiert sie nach OSCAL nach
`edition-2023/`, damit `gs-lookup`/`gs-crosswalk` einheitlich dagegen arbeiten. Vorbereitet, noch nicht
implementiert.
