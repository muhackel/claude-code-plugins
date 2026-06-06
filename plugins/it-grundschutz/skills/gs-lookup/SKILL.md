---
name: gs-lookup
description: "Anforderungen und Bausteine zitierfaehig nachschlagen — per ID (z.B. GC.1.1) oder Volltext-/Themensuche im lokalen OSCAL-Katalog. Liefert Wortlaut (statement/guidance, Parameter aufgeloest), Pfad (Schicht/Gruppe), sec_level und effort_level, mit Edition und Quelle — und bei vorhandener Methodik-Ebene zusaetzlich das Vorgehen/Warum dahinter. Nutzen, sobald konkrete Grundschutz-Inhalte gebraucht werden."
---

# gs-lookup — Zitierfaehig nachschlagen

Liest **ausschliesslich** aus dem lokalen Korpus. Nie Inhalte aus dem Modellgedaechtnis erfinden.

## Datenmodell (OSCAL Catalog, zwei Ebenen)

- **Katalog** → `groups` (Schichten: `GC` Governance und Compliance, `STM` Strukturmodellierung,
  `UMS` Umsetzung, `VRB` Verbesserung, `PERF` Monitoring-Evaluation, `RISK` Risikomanagement, …) →
  Subgruppen → **`controls`** (= Anforderungen, ID-Schema `GC.1.1`).
- Eine Anforderung: `title`, `params`, `props` (`sec_level` z.B. `normal-SdT`, `effort_level`,
  `alt-identifier` = stabile UUID), `parts` (`statement` = Anforderungstext, `guidance` = Hinweise).
  Parameter-Platzhalter (`{{ insert: param … }}`) werden beim Lookup aufgeloest.
- **Zwei Ebenen, gleiche ID:** *anwender* = die konkrete Anforderung; *methodik* = das Vorgehen/Warum
  dahinter (nur fuer die ~61 Methodik-IDs). `get` zeigt beide, sofern sie sich unterscheiden.

## Kommandos

```bash
nix run .#gs -- status            # Ebenen, Stand, Anzahl Anforderungen
nix run .#gs -- groups            # Schichten/Gruppen-Baum (Anwenderkatalog)
nix run .#gs -- list GC           # Anforderungen einer Schicht/Gruppe
nix run .#gs -- get GC.1.1        # Anforderung volltext + Methodik-Ebene (falls abweichend)
nix run .#gs -- search "ISMS"     # Volltextsuche in title/statement/guidance
nix run .#gs -- prozess           # Vorgehensweise als Schrittfolge (Methodik-Ebene) -> gs-dokument
nix run .#gs -- json GC.1.1       # rohes OSCAL-Control (fuer crosswalk/debug)
```

(In einer `nix develop`-Shell direkt `scripts/gs.py <cmd>`.)

## Zitierdisziplin (Pflicht)

Jede ausgegebene Anforderung enthaelt:

1. **ID** + **Titel** (`GC.1.1 — Errichtung und Aufrechterhaltung eines ISMS`)
2. **Wortlaut** aus `statement` unveraendert (Parameter aufgeloest, nicht paraphrasieren), bei Bedarf `guidance`
3. **Kontext:** Pfad (Schicht → Gruppe), `sec_level`, `effort_level`
4. **Edition + Quelle + Ebene:** `Grundschutz++ (anwender|methodik, BSI Stand-der-Technik-Bibliothek, Stand <last-modified>)`

Bei Themensuche: zuerst `search`, dann relevante Treffer per `get` volltext. Mehrere Treffer als Tabelle
(ID | Titel | Schicht | sec_level).

## Wenn kein Korpus da ist

Nicht raten — `gs-ingest` ausfuehren, dann erneut nachschlagen.
