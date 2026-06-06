---
name: gs-crosswalk
description: "Editionswechsel begleiten: Anforderungen zwischen Edition 2023 und Grundschutz++ abgleichen — was kam hinzu, entfiel, wurde zusammengelegt oder umbenannt. Wichtig: editionsübergreifend gibt es KEINE maschinell nutzbare Brücke (keine gemeinsame Kennung, kein offizielles BSI-Mapping) — das ist ein heuristischer Inhalts-/Wortlautvergleich. Dafür liefert 'gs crosswalk <ID>' heuristische Top-Kandidaten (Token-Überlappung). Der alt-identifier-Diff funktioniert nur zwischen zwei Ständen DERSELBEN Edition. Nutzen bei Migration, Delta-Analyse oder Mapping auf andere Standards (z.B. ISO 27001)."
---

# gs-crosswalk — Editionen und Standards abgleichen

Der Migrations-Skill. Grund: Quellformat **und** Struktur wechseln zwischen den Editionen
(Edition 2023 = DocBook-XML, klassische Schichten ISMS/ORP/CON/OPS/… mit **Bausteinen**; Grundschutz++ =
OSCAL, prozessorientiert GC/STM/UMS/PERF/VRB, **ohne Bausteine** — Anforderungen hängen an
Zielobjektkategorien). Ein direkter ID-Vergleich genügt nicht.

## Zwei verschiedene Crosswalks — nicht verwechseln

Das ist die zentrale Unterscheidung. Beide heißen „Crosswalk", funktionieren aber grundverschieden:

| | **A) Gleiche Edition, zwei Stände** | **B) Editionsübergreifend (2023 ↔ ++)** |
|---|---|---|
| Wann | Grundschutz++ ist agil — Stand X gegen Stand Y | Migration von Edition 2023 auf Grundschutz++ |
| Brücke | **`alt-identifier`** (in ++ eine stabile UUID je Anforderung) — überlebt Umbenennungen | **keine maschinelle Brücke** — siehe unten |
| Methode | ID-/UUID-Diff, dann Texte vergleichen | **heuristischer Inhalts-/Wortlautvergleich** + Zielobjektlogik |
| Verlässlichkeit | hoch (gemeinsamer Schlüssel) | begründete Schätzung, vom Menschen zu prüfen |

> **Die Grenze für B explizit:** Es gibt **keinen gemeinsamen Schlüssel** zwischen den Editionen. In
> Grundschutz++ ist der `alt-identifier` eine UUID (`KONF.2.1` → `8bd05aba-…`), in Edition 2023 ist es die
> Anforderungs-ID selbst (`SYS.1.1.A5` → `SYS.1.1.A5`). Disjunkte Namensräume — ein `alt-identifier`-Diff über
> die Editionsgrenze ist **unmöglich**. Das Grundschutz++-`profile.json` referenziert Edition 2023 nur
> **bibliografisch** (eine Resource mit Weblink + Hash auf die ganze Edition), nicht anforderungsfein. Ein vom
> BSI gepflegtes offizielles OSCAL-Mapping Edition 2023 ↔ Grundschutz++ existiert (Stand jetzt) **nicht**.
> Jedes editionsübergreifende Mapping ist daher heuristisch und entsprechend zu kennzeichnen.

## Korpus je Edition

Beide Editionen liegen strukturgleich als OSCAL-Katalog vor (per `gs-ingest` geladen) und sind über
`gs.py --edition <…>` getrennt abfragbar:

```bash
nix run .#gs -- --edition edition-2023 get SYS.1.1.A5   # Edition 2023
nix run .#gs -- --edition grundschutz-pp get GC.1.1     # Grundschutz++ (Default)
```

## Brücken (OSCAL) — und ihre Reichweite

| Mechanismus | Zweck | Reichweite |
|---|---|---|
| **`props` → `alt-identifier`** | stabile Kennung je Anforderung, überlebt Umbenennungen | nur **innerhalb** einer Edition (in ++ UUID, in 2023 die ID — nicht kompatibel) |
| **`profiles`** | OSCAL-Profile wählen Anforderungen aus Katalogen aus, mit Rückverfolgbarkeit | innerhalb ++; auf Edition 2023 nur bibliografischer Verweis, kein controlfeines Mapping |
| **`links` / `back-matter`** | Verweise auf andere Kataloge/Standards (z.B. ISO 27001 Annex A) | nur wo das BSI sie pflegt; im ++-Korpus verweisen `links` bisher ausschließlich intern |

## Workflow A — Delta zwischen zwei Ständen *derselben* Edition

Funktioniert sauber, weil der `alt-identifier` einen gemeinsamen Schlüssel liefert:

1. Beide Stände lokal vorhalten (`gs-ingest`: ältere Kopie sichern, dann `nix run .#ingest`).
2. Anforderungsmengen ziehen: `gs.py list <gruppe>` / `gs.py json <id>` je Stand.
3. Diff über **`alt-identifier`** (stabil) statt über die Anzeige-ID (kann wandern):
   - in beiden, alt-identifier gleich → unverändert / leicht geändert (Texte vergleichen)
   - in beiden, ID verschieden, alt-identifier gleich → **umbenannt/verschoben**
   - nur alt → **entfallen / zusammengelegt** (Ziel über `links` suchen)
   - nur neu → **hinzugekommen**
4. Ergebnis: `alt-identifier | ID Stand X | ID Stand Y | Status | Anmerkung`.

## Workflow B — Migration Edition 2023 → Grundschutz++ (heuristisch)

Kein gemeinsamer Schlüssel, also **inhaltlich** abbilden — und das Ergebnis ehrlich als Schätzung kennzeichnen:

1. **Quellseite bestätigen:** die relevanten Edition-2023-Bausteine/Anforderungen im Korpus prüfen
   (`gs.py --edition edition-2023 groups | list <baustein> | get <id>`), nicht aus dem Gedächtnis.
2. **Strukturbruch übersetzen:** Grundschutz++ kennt keine Bausteine. Ein Baustein bildet **nicht** 1:1 ab,
   sondern zerfällt nach Wirkprinzip in mehrere ++-Schichten (KONF, ARCH, BER, DEV, DET, NOT, BES/DLS …). Die
   Objektbindung stellt die **Zielobjektkategorie** wieder her: „Baustein SYS.1.1 Server" → Kategorie
   `Hostsysteme`; „APP.3.1 Webanwendungen" → `Webanwendungen`. Dann die ++-Anforderungen zielobjektbasiert
   ziehen — siehe `gs-modellierung`:
   ```bash
   nix run .#gs -- targets                                  # Kategorien-Inventar (für die Zuordnung)
   nix run .#gs -- list --target Hostsysteme --inherit      # ++-Anforderungen zum Ziel "Server"
   ```
3. **Inhaltlich zuordnen — assistiert via `gs.py crosswalk <ID>`:** nimmt die Quell-Anforderung der
   *anderen* Edition, tokenisiert Titel + Statement und rankt die Anforderungen der aktiven Edition nach
   Wortlaut-Überlappung (Titel↔Titel am stärksten gewichtet, Statement-Kanal entrauscht). Ausgabe: Top-N
   `Score | ID | Titel | Zielobjektkategorie | sec_level`. Das ist eine **Heuristik** (kein gemeinsamer
   Schlüssel, kein BSI-Mapping) und ersetzt die Prüfung nicht — Kandidaten per `gs.py get <ID>` verifizieren.
   Entfallene Quell-Anforderungen werden erkannt und ausgewiesen (kein Mapping erzwungen).
   ```bash
   nix run .#gs -- crosswalk SYS.1.1.A5            # Edition-2023-ID → Top-Kandidaten in ++ (heuristisch)
   nix run .#gs -- --edition edition-2023 crosswalk GC.1.1   # umgekehrt: ++-ID → Kandidaten in 2023
   ```
   Status je Anforderung vergeben: `1:1` / `verschoben` / `aufgelöst` (ein Baustein → mehrere
   Kategorien/Schichten) / `neu` / `entfallen` / `kein Mapping`.
4. **Lücken benennen:** wo es kein ++-Pendant gibt (z.B. der DocBook-Kreuzbezug Baustein↔Gefährdung, oder eine
   feingranulare Baustein-Anforderung ohne Entsprechung), das klar als „kein Mapping" ausweisen — nicht
   erzwingen. Ergebnis: `2023-ID (Titel) | ++-Zielobjektkategorie | tragende ++-Anforderungen | Status`.

## Mapping auf andere Standards

Das BSI überarbeitet das ISO-27001-Mapping. Wo OSCAL-`links`/Profiles ein Mapping liefern, dieses nutzen —
kein eigenes Mapping erfinden. Fehlt es, klar als „nicht offiziell gemappt" kennzeichnen.

## Status / Grenze (ehrlich)

Beide Editionen sind vorhanden: Grundschutz++ (OSCAL, agil über GitHub) und Edition 2023 (DocBook-XML, per
Adapter nach OSCAL normalisiert). **Der editionsübergreifende Crosswalk (B) ist möglich, aber heuristisch:**
es gibt weder eine gemeinsame Kennung noch ein offizielles BSI-Mapping. Der `alt-identifier`-Diff (A) ist
zuverlässig, gilt aber nur zwischen zwei Ständen *derselben* Edition. Die finale Mapping-Entscheidung trifft
immer der Mensch.
