---
name: gs-modellierung
description: "Für ein Szenario die zutreffenden Grundschutz-Bausteine und Anforderungen ermitteln: Beschreibung (Komponenten, Prozesse, Schutzbedarf) auf die Schichten/Gruppen und Zielobjektkategorien des Katalogs abbilden (in Grundschutz++ via 'gs list --target', mit Vererbung) und eine begründete, zitierfähige Anforderungsliste erzeugen. Nutzen, wenn 'welche Anforderungen treffen auf X zu' gefragt ist. Nur generisch — keine vertraulichen Verbundsdaten."
---

# gs-modellierung — Bausteine für ein Szenario

Übersetzt ein generisches Szenario in eine nachvollziehbare Liste zutreffender Anforderungen. Arbeitet
gegen den lokalen Katalog (`gs-lookup`), erfindet nichts.

## Wichtig: nur generisch

Dieser Skill modelliert **generische Szenarien** (z.B. „Webanwendung mit Datenbank", „Außenstandort mit
VPN"). **Konkrete, firmeneigene Informationsverbünde mit vertraulichen Daten** gehören nicht in dieses
teilbare Plugin — dafür ein getrenntes, vertrauliches Repo/Vault nutzen. Hier nur die Grundschutz-Ebene.

## Vorgehen

1. **Szenario zerlegen** in Aspekte: Governance/Organisation, Strukturmodellierung, betroffene
   Technik/Prozesse, Risiko, Betrieb/Monitoring, Verbesserung.
2. **Auf Schichten abbilden** (Grundschutz++, 20 Schichten — `gs.py groups` für den aktuellen Baum). Zwei Arten:
   - **Prozess-/Management-Schichten:** `GC` Governance und Compliance, `STM` Strukturmodellierung,
     `UMS` Umsetzung, `VRB` Verbesserung, `PERF` Monitoring-Evaluation, `RISK` Risikomanagement.
   - **Thematische Schichten (hier liegt die Technik/Fachlichkeit):** `ASST` Informationen und Assets,
     `PERS` Personal, `BES` Beschaffungsmanagement, `DLS` Dienstleistersteuerung, `TEST` Änderungen und Tests,
     `GEB` Gebäudemanagement, `SENS` Sensibilisierung, `ARCH` Architektur, `BER` Berechtigung,
     `NOT` Notfallplanung, `DET` Detektion, `REA` Sicherheitsvorfallsbehandlung, `KONF` Konfiguration,
     `DEV` Entwicklung.

   Ein technisches Zielobjekt (z.B. Server) modellierst du primär über die **thematischen** Schichten
   (`KONF` Härtung/Patches/Firewall, `BER` Zugänge, `DET` Logging, `NOT` Backup, `ARCH` Netzeinbindung),
   verankert im Prozessrahmen (`GC`/`STM`). Nicht nur die Management-Schichten betrachten.
3. **Anforderungen ziehen** — entweder je relevanter Gruppe (`gs.py list <gruppe>`) oder, präziser,
   **zielobjektbasiert** über `gs.py list --target <Kategorie>` (siehe unten); thematisch passende per
   `gs.py search`/`get` schärfen.
4. **Begründen und zitieren:** Ergebnis als Tabelle `ID | Titel | Schicht | sec_level | warum relevant`.
   `sec_level`/`effort_level` helfen beim Priorisieren.
5. **Ehrlich zu Lücken:** keine Vollständigkeitsgarantie behaupten. Was bewusst weggelassen wurde,
   benennen — die finale Modellierungsentscheidung trifft der Mensch.

## Zielobjektbasierte Modellierung (Grundschutz++) — der STM-Weg

In Grundschutz++ hängen Anforderungen nicht mehr an Bausteinen (wie `SYS.1.1` in Edition 2023), sondern an
**Zielobjektkategorien** (Strukturmodellierung, Schicht `STM`). Das ist der eigentliche
Modellierungs-Mechanismus und der Ersatz für die alte Baustein-Navigation:

```bash
nix run .#gs -- targets                               # alle Kategorien + Häufigkeit + Vererbung + Synonyme
nix run .#gs -- list --target Hostsysteme             # Anforderungen direkt an "Server" (Synonym Hostsysteme)
nix run .#gs -- list --target Hostsysteme --inherit   # + vererbte Anforderungen der Oberkategorie IT-Systeme
nix run .#gs -- list --target Webanwendungen --inherit    # erbt über Webserver -> Anwendungen
nix run .#gs -- list KONF BER --target Hostsysteme --inherit  # nur diese Schichten, auf das Asset gefiltert
```

- **Synonyme werden aufgelöst** (`Server` → `Hostsysteme`, `Fileserver` → `Dateiserver`, `Computer` → `IT-Systeme`).
- **`--inherit`** zieht die Vererbung gemäß **STM.5.2** hoch: eine Anforderung an `IT-Systeme` gilt auch für ein
  `Hostsystem`. Für ein reales Asset fast immer mit `--inherit` arbeiten — sonst fehlen die generischen
  Anforderungen der Oberkategorien.
- **Asset → Kategorie zuordnen** ist der Schritt aus `STM.4.x` (`gs.py get STM.4.3`); die Kategorienliste mit
  Definitionen liefert `gs.py targets`.

Die Anforderungen **ohne** Zielobjektkategorie (querschnittlich/organisatorisch, vgl. `STM.5.4`) erreichst du
nicht über `--target` — die kommen über die Prozess-Schichten (`GC`/`STM`/`UMS`/…) und Gruppen-Selektoren.

## Output

Eine übernehmbare Anforderungsliste (zitierfähig, mit Edition/Quelle), plus kurze Begründung der
Schicht-/Zielobjektauswahl. Auf Wunsch als Markdown-Tabelle für die ISMS-Doku.
