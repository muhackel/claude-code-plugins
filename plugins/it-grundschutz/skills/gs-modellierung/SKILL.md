---
name: gs-modellierung
description: "Fuer ein Szenario die zutreffenden Grundschutz-Bausteine und Anforderungen ermitteln: Beschreibung (Komponenten, Prozesse, Schutzbedarf) auf die Schichten/Gruppen des Katalogs abbilden und eine begruendete, zitierfaehige Anforderungsliste erzeugen. Nutzen, wenn 'welche Anforderungen treffen auf X zu' gefragt ist. Nur generisch — keine vertraulichen Verbundsdaten."
---

# gs-modellierung — Bausteine fuer ein Szenario

Uebersetzt ein generisches Szenario in eine nachvollziehbare Liste zutreffender Anforderungen. Arbeitet
gegen den lokalen Katalog (`gs-lookup`), erfindet nichts.

## Wichtig: nur generisch

Dieser Skill modelliert **generische Szenarien** (z.B. „Webanwendung mit Datenbank", „Aussenstandort mit
VPN"). **Konkrete, firmeneigene Informationsverbuende mit vertraulichen Daten** gehoeren nicht in dieses
teilbare Plugin — dafuer ein getrenntes, vertrauliches Repo/Vault nutzen. Hier nur die Grundschutz-Ebene.

## Vorgehen

1. **Szenario zerlegen** in Aspekte: Governance/Organisation, Strukturmodellierung, betroffene
   Technik/Prozesse, Risiko, Betrieb/Monitoring, Verbesserung.
2. **Auf Schichten abbilden** (Grundschutz++): `GC` Governance und Compliance, `STM` Strukturmodellierung,
   `UMS` Umsetzung, `PERF` Monitoring-Evaluation, `VRB` Verbesserung, `RISK` Risikomanagement, … —
   `gs.py groups` fuer den aktuellen Baum.
3. **Anforderungen ziehen** je relevanter Gruppe (`gs.py list <gruppe>`), thematisch passende per
   `gs.py search`/`get` auswaehlen.
4. **Begruenden und zitieren:** Ergebnis als Tabelle `ID | Titel | Schicht | sec_level | warum relevant`.
   `sec_level`/`effort_level` helfen beim Priorisieren.
5. **Ehrlich zu Luecken:** keine Vollstaendigkeitsgarantie behaupten. Was bewusst weggelassen wurde,
   benennen — die finale Modellierungsentscheidung trifft der Mensch.

## Output

Eine uebernehmbare Anforderungsliste (zitierfaehig, mit Edition/Quelle), plus kurze Begruendung der
Schichtauswahl. Auf Wunsch als Markdown-Tabelle fuer die ISMS-Doku.
