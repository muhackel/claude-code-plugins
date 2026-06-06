---
name: gs-lookup
description: "Anforderungen und Bausteine zitierfaehig nachschlagen — per ID (z.B. GC.1.1) oder Volltext-/Themensuche im lokalen OSCAL-Katalog. Liefert Wortlaut (statement/guidance), Pfad (Schicht/Gruppe), sec_level und effort_level, mit Edition und Quelle. Nutzen, sobald konkrete Grundschutz-Inhalte gebraucht werden."
---

# gs-lookup — Zitierfaehig nachschlagen

Liest **ausschliesslich** aus dem lokalen Korpus. Nie Inhalte aus dem Modellgedaechtnis erfinden.

## Datenmodell (OSCAL Catalog)

- **Katalog** → `groups` (Schichten, z.B. `GC` Governance und Compliance, `STM` Strukturmodellierung,
  `UMS` Umsetzung, `PERF` Monitoring-Evaluation, `VRB` Verbesserung, `RISK` Risikomanagement, …).
- Gruppen enthalten **Subgruppen** und schliesslich **`controls`** (= Anforderungen, ID-Schema `GC.1.1`).
- Eine Anforderung hat: `title`, `params`, `props` (u.a. `sec_level` z.B. `normal-SdT`, `effort_level`,
  `alt-identifier` = stabile UUID), `parts` (`statement` = der Anforderungstext, `guidance` = Hinweise).

## Kommandos

```bash
nix run .#gs -- status            # Korpus-Status (Version, Anzahl Anforderungen)
nix run .#gs -- groups            # Schichten/Gruppen-Baum
nix run .#gs -- list GC           # alle Anforderungen einer Schicht/Gruppe
nix run .#gs -- get GC.1.1        # eine Anforderung volltext, zitierfaehig
nix run .#gs -- search "ISMS"     # Volltextsuche in title/statement/guidance -> Trefferliste
nix run .#gs -- json GC.1.1       # rohes OSCAL-Control (fuer crosswalk/debug)
```

(In einer `nix develop`-Shell direkt `scripts/gs.py <cmd>`.)

## Zitierdisziplin (Pflicht)

Jede ausgegebene Anforderung enthaelt:

1. **ID** + **Titel** (`GC.1.1 — Errichtung und Aufrechterhaltung eines ISMS`)
2. **Wortlaut** aus `statement` unveraendert (nicht paraphrasieren), bei Bedarf `guidance`
3. **Kontext:** Pfad (Schicht → Gruppe), `sec_level`, `effort_level`
4. **Edition + Quelle:** `Grundschutz++ (BSI Stand-der-Technik-Bibliothek, Stand <last-modified>)`

Bei Themensuche: zuerst `search`, dann die relevanten Treffer per `get` volltext nachladen. Mehrere Treffer
strukturiert auflisten (Tabelle: ID | Titel | Schicht | sec_level).

## Wenn kein Korpus da ist

Nicht raten — `gs-ingest` ausfuehren, dann erneut nachschlagen.
