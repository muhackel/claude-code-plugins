---
name: gs-lookup
description: "Anforderungen und Bausteine zitierfähig nachschlagen — per ID (z.B. GC.1.1) oder Volltext-/Themensuche im lokalen OSCAL-Katalog. Liefert Wortlaut (statement/guidance, Parameter aufgelöst), Pfad (Schicht/Gruppe), sec_level und effort_level, mit Edition und Quelle — und bei vorhandener Methodik-Ebene zusätzlich das Vorgehen/Warum dahinter. Nutzen, sobald konkrete Grundschutz-Inhalte gebraucht werden."
---

# gs-lookup — Zitierfähig nachschlagen

Liest **ausschließlich** aus dem lokalen Korpus. Nie Inhalte aus dem Modellgedächtnis erfinden.

## Datenmodell (OSCAL Catalog, zwei Ebenen)

- **Katalog** → `groups` (20 Schichten, `gs.py groups` für den aktuellen Baum) → Subgruppen →
  **`controls`** (= Anforderungen, ID-Schema `GC.1.1`). Die Schichten zerfallen in **Prozess-/Management**
  (`GC`, `STM`, `UMS`, `VRB`, `PERF`, `RISK`) und **thematische** Schichten, die die Technik/Fachlichkeit
  tragen (`ASST`, `PERS`, `BES`, `DLS`, `TEST`, `GEB`, `SENS`, `ARCH`, `BER`, `NOT`, `DET`, `REA`, `KONF`,
  `DEV`).
- Eine Anforderung: `title`, `params`, `props` (`sec_level` z.B. `normal-SdT`, `effort_level`,
  `alt-identifier` = stabile UUID), `parts` (`statement` = Anforderungstext, `guidance` = Hinweise).
  Der `statement`-Part trägt zusätzlich die **Zielobjektkategorie** (`target_object_categories`) — darüber
  filtert `list --target`. Parameter-Platzhalter (`{{ insert: param … }}`) werden beim Lookup aufgelöst.
- **Zwei Ebenen, gleiche ID:** *anwender* = die konkrete Anforderung; *methodik* = das Vorgehen/Warum
  dahinter (nur für die ~61 Methodik-IDs). `get` zeigt beide, sofern sie sich unterscheiden.

## Kommandos

```bash
nix run .#gs -- status            # Ebenen, Stand, Anzahl Anforderungen
nix run .#gs -- groups            # Schichten/Gruppen-Baum (Anwenderkatalog)
nix run .#gs -- targets           # Zielobjektkategorien + Häufigkeit/Vererbung (nur Grundschutz++)
nix run .#gs -- list GC KONF.2    # Anforderungen einer/mehrerer Schichten/Gruppen oder exakter IDs
nix run .#gs -- list --target Hostsysteme --inherit   # zielobjektbasiert (Synonyme + STM-Vererbung)
nix run .#gs -- get GC.1.1        # Anforderung volltext + Methodik-Ebene (falls abweichend)
nix run .#gs -- search "ISMS"     # Suche in title/statement/guidance, nach Token-Überlappung (Score) sortiert
nix run .#gs -- prozess           # Vorgehensweise als Schrittfolge (Methodik-Ebene) -> gs-dokument
nix run .#gs -- json GC.1.1       # rohes OSCAL-Control (für crosswalk/debug)
```

(In einer `nix develop`-Shell direkt `scripts/gs.py <cmd>`.)

## Zitierdisziplin (Pflicht)

Jede ausgegebene Anforderung enthält:

1. **ID** + **Titel** (`GC.1.1 — Errichtung und Aufrechterhaltung eines ISMS`)
2. **Wortlaut** aus `statement` unverändert (Parameter aufgelöst, nicht paraphrasieren), bei Bedarf `guidance`
3. **Kontext:** Pfad (Schicht → Gruppe), `sec_level`, `effort_level`
4. **Edition + Quelle + Ebene:** `Grundschutz++ (anwender|methodik, BSI Stand-der-Technik-Bibliothek, Stand <last-modified>)`

Bei Themensuche: zuerst `search`, dann relevante Treffer per `get` volltext. `search` rankt nach
Token-Überlappung (Stopwörter raus, Titel-Treffer höher gewichtet, Komposita per Teilstring) und zeigt je
Treffer einen Score — mehrere Begriffe sind ODER-verknüpft (kein exakter Phrasen-Substring mehr nötig). Bei
sehr generischen Begriffen den Suchbegriff schärfen. Mehrere Treffer als Tabelle (ID | Titel | Schicht | sec_level).

## Wenn kein Korpus da ist

Nicht raten — `gs-ingest` ausführen, dann erneut nachschlagen.
