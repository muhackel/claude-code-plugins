---
name: gs-modellierung
description: "Für ein Szenario die zutreffenden Grundschutz-Bausteine und Anforderungen ermitteln: Beschreibung (Komponenten, Prozesse, Schutzbedarf) auf die Schichten/Gruppen des Katalogs abbilden und eine begründete, zitierfähige Anforderungsliste erzeugen. Nutzen, wenn 'welche Anforderungen treffen auf X zu' gefragt ist. Nur generisch — keine vertraulichen Verbundsdaten."
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
3. **Anforderungen ziehen** je relevanter Gruppe (`gs.py list <gruppe>`), thematisch passende per
   `gs.py search`/`get` auswählen.
4. **Begründen und zitieren:** Ergebnis als Tabelle `ID | Titel | Schicht | sec_level | warum relevant`.
   `sec_level`/`effort_level` helfen beim Priorisieren.
5. **Ehrlich zu Lücken:** keine Vollständigkeitsgarantie behaupten. Was bewusst weggelassen wurde,
   benennen — die finale Modellierungsentscheidung trifft der Mensch.

## Output

Eine übernehmbare Anforderungsliste (zitierfähig, mit Edition/Quelle), plus kurze Begründung der
Schichtauswahl. Auf Wunsch als Markdown-Tabelle für die ISMS-Doku.
