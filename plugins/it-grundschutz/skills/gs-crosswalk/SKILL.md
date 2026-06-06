---
name: gs-crosswalk
description: "Editionswechsel begleiten: Anforderungen zwischen Edition 2023 und Grundschutz++ abgleichen — was kam hinzu, entfiel, wurde zusammengelegt oder umbenannt. Nutzt OSCAL-Profiles und stabile Kennungen (alt-identifier) als Brücken. Nutzen bei Migration, Delta-Analyse zwischen Editionen oder Mapping auf andere Standards (z.B. ISO 27001)."
---

# gs-crosswalk — Editionen und Standards abgleichen

Der eigentliche Migrations-Skill. Grund: Quellformat **und** Struktur wechseln zwischen den Editionen
(Edition 2023 = DocBook-XML, klassische Schichten ISMS/ORP/CON/OPS/…; Grundschutz++ = OSCAL, prozessorientiert
GC/STM/UMS/PERF/VRB). Ein direkter ID-Vergleich genügt nicht.

## Korpus je Edition

Beide Editionen liegen strukturgleich als OSCAL-Katalog vor (per `gs-ingest` geladen) und sind über
`gs.py --edition <…>` getrennt abfragbar:

```bash
nix run .#gs -- --edition edition-2023 get SYS.1.1.A5   # Edition 2023
nix run .#gs -- --edition grundschutz-pp get GC.1.1     # Grundschutz++ (Default)
```

## Brücken (OSCAL)

| Mechanismus | Zweck |
|---|---|
| **`profiles`** | OSCAL-Profile wählen Anforderungen aus Katalogen aus und passen sie an — mit Rückverfolgbarkeit zum Originalkatalog. Das native OSCAL-Mittel für Baselines und Mappings. |
| **`props` → `alt-identifier`** | stabile Kennung je Anforderung — überlebt Umbenennungen, Brücke über Versionsstände. Bei Grundschutz++ eine UUID, bei Edition 2023 die Anforderungs-ID (das DocBook-XML hat keine eigene UUID je Anforderung). |
| **`links` / `back-matter`** | Verweise auf andere Kataloge/Standards (z.B. ISO 27001 Annex A), wo das BSI sie pflegt. |

## Workflow (Delta zwischen zwei Korpus-Ständen)

1. Beide Stände lokal vorhalten (`gs-ingest`: `nix run .#ingest` für Grundschutz++, `nix run .#ingest-2023`
   für Edition 2023).
2. Anforderungsmengen je Edition ziehen, jeweils mit der passenden Edition:
   `gs.py --edition edition-2023 list <gruppe>` / `gs.py --edition edition-2023 json <id>`.
3. Diff bilden über **`alt-identifier`** (stabil) statt über die Anzeige-ID (wandert):
   - in beiden, ID gleich → unverändert / leicht geändert (Texte vergleichen)
   - in beiden, ID verschieden → **umbenannt/verschoben**
   - nur alt → **entfallen / zusammengelegt** (Ziel über `links` suchen)
   - nur neu → **hinzugekommen**
4. Ergebnis als Mapping-Tabelle: `alt-ID (2023) | neue ID (++) | Status | Anmerkung`.

## Mapping auf andere Standards

Das BSI überarbeitet das ISO-27001-Mapping. Wo OSCAL-`links`/Profiles ein Mapping liefern, dieses nutzen —
kein eigenes Mapping erfinden. Fehlt es, klar als „nicht offiziell gemappt" kennzeichnen.

## Status

Beide Editionen sind vorhanden: Grundschutz++ (OSCAL, agil über GitHub) und Edition 2023 (DocBook-XML, per
Adapter nach OSCAL normalisiert). Der Crosswalk läuft damit editionsübergreifend.

**Grenze:** Edition 2023 trägt als `alt-identifier` die Anforderungs-ID (keine UUID im Quell-XML); der Diff
über `alt-identifier` ist dort also ID-basiert. Ein vom BSI gepflegtes offizielles Mapping Edition 2023 ↔
Grundschutz++ als OSCAL-Profile gibt es (noch) nicht — solche Mappings sind heuristisch und entsprechend zu
kennzeichnen.
