---
name: gs-crosswalk
description: "Editionswechsel begleiten: Anforderungen zwischen Edition 2023 und Grundschutz++ abgleichen — was kam hinzu, entfiel, wurde zusammengelegt oder umbenannt. Nutzt OSCAL-Profiles und stabile Kennungen (alt-identifier) als Bruecken. Nutzen bei Migration, Delta-Analyse zwischen Editionen oder Mapping auf andere Standards (z.B. ISO 27001)."
---

# gs-crosswalk — Editionen und Standards abgleichen

Der eigentliche Migrations-Skill. Grund: Quellformat **und** Struktur wechseln zwischen den Editionen
(Edition 2023 = DocBook-XML, klassische Schichten ISMS/ORP/CON/OPS/…; Grundschutz++ = OSCAL, prozessorientiert
GC/STM/UMS/PERF/VRB). Ein direkter ID-Vergleich genuegt nicht.

## Bruecken (OSCAL)

| Mechanismus | Zweck |
|---|---|
| **`profiles`** | OSCAL-Profile waehlen Anforderungen aus Katalogen aus und passen sie an — mit Rueckverfolgbarkeit zum Originalkatalog. Das native OSCAL-Mittel fuer Baselines und Mappings. |
| **`props` → `alt-identifier`** | stabile UUID je Anforderung — ueberlebt Umbenennungen, Bruecke ueber Versionsstaende. |
| **`links` / `back-matter`** | Verweise auf andere Kataloge/Standards (z.B. ISO 27001 Annex A), wo das BSI sie pflegt. |

## Workflow (Delta zwischen zwei Korpus-Staenden)

1. Beide Staende lokal vorhalten (`gs-ingest`; fuer Edition 2023 den XML→OSCAL-Adapter, sobald implementiert).
2. Anforderungsmengen je Edition ziehen (`gs.py list <gruppe>` / `gs.py json <id>`).
3. Diff bilden ueber **`alt-identifier`** (stabil) statt ueber die Anzeige-ID (wandert):
   - in beiden, ID gleich → unveraendert / leicht geaendert (Texte vergleichen)
   - in beiden, ID verschieden → **umbenannt/verschoben**
   - nur alt → **entfallen / zusammengelegt** (Ziel ueber `links` suchen)
   - nur neu → **hinzugekommen**
4. Ergebnis als Mapping-Tabelle: `alt-ID (2023) | neue ID (++) | Status | Anmerkung`.

## Mapping auf andere Standards

Das BSI ueberarbeitet das ISO-27001-Mapping. Wo OSCAL-`links`/Profiles ein Mapping liefern, dieses nutzen —
kein eigenes Mapping erfinden. Fehlt es, klar als „nicht offiziell gemappt" kennzeichnen.

## Status

Grundschutz++ ist vorhanden. Der Edition-2023-Adapter (DocBook-XML → OSCAL) ist die naechste Ausbaustufe;
bis dahin ist der Crosswalk auf Grundschutz++-interne Versionsstaende beschraenkt.
