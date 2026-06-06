---
name: gs-dokument
description: "Sicherheitsdokumente nach der Grundschutz++-Methodik erstellen, führen oder prüfen. Drei Modi: (1) geführter Prozess entlang der Methodik-Schichten; (2) Dokument-Gerüst erzeugen (Template mit eingesetzten Anforderungen + Methodik-Verweisen); (3) bestehendes Dokument gegen Methodik/Anforderungen prüfen (Gap-Analyse). Stützt sich auf die Methodik-Ebene des Korpus und die BSI-Komponenten-Vorlagen. Nutzen, wenn ein Sicherheitskonzept/ISMS-Dokument erstellt, strukturiert oder geprüft werden soll. Generisch — ausgefüllte, firmenspezifische Dokumente gehören in ein vertrauliches Repo."
---

# gs-dokument — Dokumente nach der Methodik

Erstellt, führt oder prüft Sicherheitsdokumente **entlang der Grundschutz++-Methodik**. Die Methodik ist
das **Vorgehen** (das Warum/Wie), der Anwenderkatalog liefert die **konkreten Anforderungen**. Beide stehen
im Korpus — dieser Skill kodiert nur die *Disziplin*, sie zu einem Dokument zu verbinden.

## Korpus-first (Pflicht)

Die Methodik wird **nie aus dem Gedächtnis** wiedergegeben — immer aus dem Korpus:

```bash
nix run .#gs -- prozess            # Vorgehensweise als Schrittfolge (Methodik-Ebene)
nix run .#gs -- get GC.5.1         # ein Schritt: Anforderung + Methodik-Ebene (das Warum)
nix run .#gs -- list STM           # Anforderungen einer Schicht
```

Als Vorlagen dienen zusätzlich die **Implementierungsbeschreibungen/Komponenten** im BSI-Repo
(`AWS Beispiel-Components`, `Netzarchitektur`, `Passwortrichtlinie`, `WLAN`) — Beispiele, kein Pflichtschema.

## Dokument-Rückgrat: die Methodik-Schichten

Reihenfolge gemäß `gs.py prozess` (maßgeblich, nicht raten):

| Schicht | Bedeutung | Typischer Dokument-Beitrag |
|---------|-----------|----------------------------|
| **GC** | Governance und Compliance | Sicherheitsleitlinie, Geltungsbereich, Kontext, Rollen, Ziele |
| **STM** | Strukturmodellierung | Informationsverbund, Strukturanalyse, Schutzbedarf |
| **UMS** | Umsetzung | Maßnahmen, Umsetzungsplan, Realisierung |
| **VRB** | Verbesserung | Korrekturmaßnahmen, kontinuierliche Verbesserung |
| **PERF** | Monitoring-Evaluation | Kennzahlen, Audits, Wirksamkeitsprüfung |

`RISK`/Risikomanagement läuft als Querschnitt mit (eigene Risikoanalyse-Doku).

## Die drei Modi

### 1. Geführter Prozess
`prozess` abrufen, Schicht für Schicht durchgehen. Je Schritt die Methodik-Vorgabe (`get`) zeigen, das
Nötige beim User abfragen, die Antwort als Ergebnis festhalten. Am Ende eine strukturierte Mitschrift.

### 2. Dokument-Gerüst erzeugen
Markdown-Gerüst entlang der Schichten. Je Abschnitt:
- die zutreffenden Anforderungen (`list`/`get`) **zitierfähig** einsetzen (ID, Wortlaut, Edition, Quelle),
- den Methodik-Verweis (das Warum) nennen,
- **Platzhalter** für die firmenspezifischen Inhalte lassen — nie erfinden.

### 3. Bestehendes prüfen (Gap-Analyse)
Vorhandenes Dokument gegen die Methodik-Schritte und die zutreffenden Anforderungen abgleichen. Ergebnis als
Gap-Tabelle: `Schritt/ID | erwartet | im Dokument | Status (erfüllt/teilweise/fehlt) | Anmerkung`.

## Firmendaten-Trennung (Pflicht)

- **Generisch (hierher/teilbar):** Vorgehen, Template-Struktur, zitierte Norm, Gap-Kriterien.
- **Vertraulich (woanders):** das ausgefüllte Dokument mit Informationsverbund, Schutzbedarfen,
  Umsetzungsständen. Das gehört in ein getrenntes, vertrauliches Repo/Vault — **nie** in dieses Plugin.
- Beim Erzeugen daher Platzhalter statt erfundener Firmeninhalte.

## Output-Disziplin

- Zitierfähig: IDs, Wortlaut, Edition, Quelle (CC BY-SA 4.0).
- Klar markieren, was **normativ** (aus dem Korpus) und was **auszufüllen** ist.
- Keine Vollständigkeits- oder Konformitätsgarantie — der Mensch entscheidet und verantwortet.
