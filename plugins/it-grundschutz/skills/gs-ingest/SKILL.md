---
name: gs-ingest
description: "Den BSI-Korpus lokal vorhalten: die Grundschutz++-OSCAL-Dateien (Anwenderkatalog, Methodik-Quellkatalog, Profile) von der BSI-Stand-der-Technik-Bibliothek (GitHub) laden sowie das IT-Grundschutz-Kompendium Edition 2023 (DocBook-XML) per Adapter nach OSCAL normalisieren, ins lokale Datenverzeichnis cachen, mit Manifest (Quelle, Version, sha256, Abrufdatum je Datei) versehen und aktuell halten. Nutzen, bevor nachgeschlagen/modelliert/dokumentiert wird, wenn kein Korpus vorliegt oder ein Update ansteht."
---

# gs-ingest — Korpus laden und aktuell halten

Der Agent arbeitet **nur** gegen einen lokal vorgehaltenen Korpus. Dieser Skill beschafft und pflegt ihn —
für Grundschutz++ in vier Quellen (drei OSCAL-Ebenen + Zielobjekt-Namespace) aus dem BSI-Repo, für
Edition 2023 über einen DocBook-XML→OSCAL-Adapter.
Beide Editionen landen strukturgleich als OSCAL-Katalog im lokalen Datenverzeichnis.

## Quellen (kanonisch)

Repo: `BSI-Bund/Stand-der-Technik-Bibliothek` (GitHub), Format **OSCAL 1.1.x** (JSON), Lizenz **CC BY-SA 4.0**.

| Quelle | Datei im Repo | lokal |
|--------|---------------|-------|
| **anwender** | `Anwenderkataloge/Grundschutz++/Grundschutz++-catalog.json` | `catalog.json` |
| **methodik** | `Quellkataloge/Methodik-Grundschutz++/BSI-Methodik-Grundschutz++-catalog.json` | `methodik-catalog.json` |
| **profile** | `Quellkataloge/Methodik-Grundschutz++/Grundschutz++-profile.json` | `profile.json` |
| **zielobjektkategorien** | `Dokumentation/namespaces/target_object_categories.csv` | `target_object_categories.csv` |

`anwender` = konkrete Anforderungen (~651), `methodik` = Vorgehensweise (~61, IDs ⊆ Anwender), `profile`
verknüpft beide. `zielobjektkategorien` = Zielobjekt-Namespace (CSV) — speist `gs targets` und den Filter
`list`/`checklist --target <Kategorie> [--inherit]` sowie `gs coverage` (Zielobjekt-Vererbung gemäß STM.5.2),
nur Grundschutz++. Die `++` im Pfad müssen URL-encodiert werden (`%2B%2B`).

## Datenort (nie ins Plugin-Git)

Wegen CC BY-SA wird der Korpus **nicht** in dieses (MIT-)Plugin eingecheckt:

```
$GS_CORPUS_DIR            (default: ~/.local/share/it-grundschutz/corpus)
  grundschutz-pp/
    catalog.json          # Anwenderkatalog
    methodik-catalog.json # Methodik-Quellkatalog (Vorgehensweise)
    profile.json          # OSCAL-Profile (Methodik <-> Anwender)
    target_object_categories.csv  # Zielobjekt-Namespace (speist gs targets / --target / coverage)
    manifest.json         # Liste je Datei: quelle, last_modified, sha256, anzahl; + abgerufen_am, lizenz
  edition-2023/           # Edition 2023 (DocBook-XML -> OSCAL via Adapter)
    catalog.json          # normalisierter OSCAL-Katalog (Schichten -> Bausteine -> Anforderungen + G 0.x)
    manifest.json         # quelle_url, quelle_sha256, sha256, anzahl_* ; + abgerufen_am, lizenz
```

## Nix-Umgebung zuerst

Skripte brauchen `python3`, `curl`, `jq`, `coreutils` — über das Flake bereitstellen:

```bash
nix run .#ingest            # Grundschutz++: alle vier Quellen laden/aktualisieren
nix run .#ingest -- --force # Neuladen erzwingen (sonst sha-basiert übersprungen)
nix run .#ingest-2023       # Edition 2023: DocBook-XML laden + nach OSCAL normalisieren
nix develop                 # Shell mit den Tools, dann scripts/ direkt
```

## Workflow Grundschutz++

1. **Status:** `nix run .#gs -- status` — welche Ebenen liegen vor, welcher Stand, wie viele Anforderungen?
2. **Laden/Aktualisieren:** `nix run .#ingest` zieht je Ebene die Datei, validiert das OSCAL-JSON
   (Katalog vs. Profile), schreibt sie und baut das `manifest.json` neu. Je Datei wird per **sha256**
   entschieden, ob sich etwas geändert hat — unveränderte Dateien werden übersprungen.
3. **Verifizieren:** nach dem Ingest `status` erneut — Zahlen plausibel, `last-modified` aktuell?
4. **Nicht spammen:** nicht bei jeder Sitzung ungefragt neu ziehen; Update anbieten, wenn das Manifest alt ist.

## Edition 2023 (DocBook-XML → OSCAL)

Edition 2023 liegt als **DocBook-XML** vor (`bsi.bund.de`, `XML_Kompendium_2023.xml`). Der Adapter
`scripts/adapter-2023.py` normalisiert sie strukturgleich zum Grundschutz++-Katalog nach `edition-2023/`.

```bash
nix run .#ingest-2023                       # lädt das XML von der BSI-Quelle + erzeugt OSCAL
nix run .#ingest-2023 -- --file pfad.xml    # offline: lokale XML-Datei statt Download
```

**Mapping DocBook → OSCAL** (vom Adapter erzeugt):

- Schicht-Kapitel (`SYS IT-Systeme`) → top-level `group` (id=`SYS`).
- Baustein (`SYS.1.1 Allgemeiner Server`) → verschachtelte `group`; `Beschreibung` → `parts` (`overview`),
  `Gefährdungslage` → `parts` (`guidance`, Prosa).
- Anforderung (`SYS.1.1.A5 … (B) [Rolle]`) → `control` mit `id`, `title`, `statement`-Part.
  Qualifizierungsstufe `(B)`/`(S)`/`(H)` → `props` `sec_level` = `Basis`/`Standard`/`erhöht`;
  Rolle → `props` `role`; stabile Kennung → `props` `alt-identifier` (= Anforderungs-ID, das XML hat keine
  eigene UUID je Anforderung). Entfallene Anforderungen tragen `props` `status=entfallen`.
- Elementare Gefährdungen → eigene `group` `G 0` mit je einem `control` `G 0.x`.

**Bewusste Auslassung:** Der formale **Baustein↔Gefährdung-Kreuzbezug** (Kreuzreferenztabellen) ist **nicht**
Teil des Kompendium-XML — die Gefährdungslage je Baustein ist dort nur erläuternde Prosa. Der Adapter loggt
das beim Lauf. Wer den Kreuzbezug braucht, zieht die separaten BSI-Kreuzreferenztabellen nach.

Umfang Edition 2023: **10 Schichten, 111 Bausteine, 2125 Anforderungen** (652 Basis / 1014 Standard /
459 erhöht, davon 290 entfallen) + **47 elementare Gefährdungen**.
