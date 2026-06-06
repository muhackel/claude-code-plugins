---
name: gs-ingest
description: "Den BSI-Korpus lokal vorhalten: Grundschutz++-OSCAL-Katalog von der BSI-Stand-der-Technik-Bibliothek (GitHub) laden, ins lokale Datenverzeichnis cachen, mit Manifest (Quelle, Version, sha256, Abrufdatum) versehen und aktuell halten. Nutzen, bevor nachgeschlagen/modelliert wird, wenn kein Korpus vorliegt oder ein Update ansteht."
---

# gs-ingest — Korpus laden und aktuell halten

Der Agent arbeitet **nur** gegen einen lokal vorgehaltenen Korpus. Dieser Skill beschafft und pflegt ihn.

## Quelle (kanonisch)

| | |
|---|---|
| Repo | `BSI-Bund/Stand-der-Technik-Bibliothek` (GitHub) |
| Datei (Grundschutz++) | `Anwenderkataloge/Grundschutz++/Grundschutz++-catalog.json` |
| Raw-URL | `https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/main/Anwenderkataloge/Grundschutz%2B%2B/Grundschutz%2B%2B-catalog.json` |
| Format | OSCAL 1.1.x **Catalog** (JSON), NIST-Standard |
| Lizenz | **CC BY-SA 4.0** — Attribution + ShareAlike |
| Aktualisierung | laufend (agil); `metadata.version`/`last-modified` ist ein Zeitstempel |

Die `++` im Pfad muessen URL-encodiert werden (`%2B%2B`).

## Datenort (nie ins Plugin-Git)

Wegen der CC-BY-SA-Lizenz wird der Korpus **nicht** in dieses (MIT-)Plugin eingecheckt, sondern im lokalen
Datenverzeichnis vorgehalten:

```
$GS_CORPUS_DIR            (default: ~/.local/share/it-grundschutz/corpus)
  grundschutz-pp/
    catalog.json          # der OSCAL-Anwenderkatalog
    manifest.json         # quelle, raw_url, last_modified, abgerufen_am, sha256, lizenz
  edition-2023/           # spaetere Ausbaustufe (DocBook-XML -> OSCAL)
```

## Nix-Umgebung zuerst

Die Skripte brauchen `python3`, `curl`, `jq`, `coreutils`. Nicht systemweit annehmen — ueber das Plugin-Flake
bereitstellen:

```bash
# im Plugin-Verzeichnis
nix run .#ingest            # Katalog laden/aktualisieren
nix develop                 # Shell mit python3/curl/jq, dann scripts/ direkt aufrufen
```

## Workflow

1. **Status pruefen:** `nix run .#gs -- status` (oder `scripts/gs.py status`) — liegt `catalog.json` vor,
   welche `version`/`last-modified`, wie viele Gruppen/Anforderungen?
2. **Laden/Aktualisieren:** `nix run .#ingest` zieht den Katalog, validiert das JSON, schreibt
   `catalog.json` + `manifest.json`. Bestehender Korpus wird nur bei `--force` oder geaenderter
   `last-modified` ueberschrieben.
3. **Verifizieren:** nach dem Ingest `status` erneut — Anzahl Anforderungen plausibel? `last-modified` neu?
4. **Nicht spammen:** nicht bei jeder Sitzung ungefragt neu ziehen. Update anbieten, wenn das Manifest alt
   ist oder der User explizit Aktualitaet braucht.

## Spaeter: Edition 2023

Edition 2023 liegt als **DocBook-XML** vor (`bsi.bund.de`, XML-Kompendium). Sie ist kein OSCAL — der Adapter
normalisiert sie nach OSCAL-Catalog, damit `gs-lookup`/`gs-crosswalk` einheitlich dagegen arbeiten. Diese
Ausbaustufe ist vorbereitet (Verzeichnis `edition-2023/`), aber noch nicht implementiert.
