---
name: gs-dokument
description: "Sicherheitsdokumente nach der Grundschutz++-Methodik erstellen, fuehren oder pruefen. Drei Modi: (1) gefuehrter Prozess entlang der Methodik-Schichten; (2) Dokument-Geruest erzeugen (Template mit eingesetzten Anforderungen + Methodik-Verweisen); (3) bestehendes Dokument gegen Methodik/Anforderungen pruefen (Gap-Analyse). Stuetzt sich auf die Methodik-Ebene des Korpus und die BSI-Komponenten-Vorlagen. Nutzen, wenn ein Sicherheitskonzept/ISMS-Dokument erstellt, strukturiert oder geprueft werden soll. Generisch — ausgefuellte, firmenspezifische Dokumente gehoeren in ein vertrauliches Repo."
---

# gs-dokument — Dokumente nach der Methodik

Erstellt, fuehrt oder prueft Sicherheitsdokumente **entlang der Grundschutz++-Methodik**. Die Methodik ist
das **Vorgehen** (das Warum/Wie), der Anwenderkatalog liefert die **konkreten Anforderungen**. Beide stehen
im Korpus — dieser Skill kodiert nur die *Disziplin*, sie zu einem Dokument zu verbinden.

## Korpus-first (Pflicht)

Die Methodik wird **nie aus dem Gedaechtnis** wiedergegeben — immer aus dem Korpus:

```bash
nix run .#gs -- prozess            # Vorgehensweise als Schrittfolge (Methodik-Ebene)
nix run .#gs -- get GC.5.1         # ein Schritt: Anforderung + Methodik-Ebene (das Warum)
nix run .#gs -- list STM           # Anforderungen einer Schicht
```

Als Vorlagen dienen zusaetzlich die **Implementierungsbeschreibungen/Komponenten** im BSI-Repo
(`AWS Beispiel-Components`, `Netzarchitektur`, `Passwortrichtlinie`, `WLAN`) — Beispiele, kein Pflichtschema.

## Dokument-Rueckgrat: die Methodik-Schichten

Reihenfolge gemaess `gs.py prozess` (massgeblich, nicht raten):

| Schicht | Bedeutung | Typischer Dokument-Beitrag |
|---------|-----------|----------------------------|
| **GC** | Governance und Compliance | Sicherheitsleitlinie, Geltungsbereich, Kontext, Rollen, Ziele |
| **STM** | Strukturmodellierung | Informationsverbund, Strukturanalyse, Schutzbedarf |
| **UMS** | Umsetzung | Massnahmen, Umsetzungsplan, Realisierung |
| **VRB** | Verbesserung | Korrekturmassnahmen, kontinuierliche Verbesserung |
| **PERF** | Monitoring-Evaluation | Kennzahlen, Audits, Wirksamkeitspruefung |

`RISK`/Risikomanagement laeuft als Querschnitt mit (eigene Risikoanalyse-Doku).

## Die drei Modi

### 1. Gefuehrter Prozess
`prozess` abrufen, Schicht fuer Schicht durchgehen. Je Schritt die Methodik-Vorgabe (`get`) zeigen, das
Noetige beim User abfragen, die Antwort als Ergebnis festhalten. Am Ende eine strukturierte Mitschrift.

### 2. Dokument-Geruest erzeugen
Markdown-Geruest entlang der Schichten. Je Abschnitt:
- die zutreffenden Anforderungen (`list`/`get`) **zitierfaehig** einsetzen (ID, Wortlaut, Edition, Quelle),
- den Methodik-Verweis (das Warum) nennen,
- **Platzhalter** fuer die firmenspezifischen Inhalte lassen — nie erfinden.

### 3. Bestehendes pruefen (Gap-Analyse)
Vorhandenes Dokument gegen die Methodik-Schritte und die zutreffenden Anforderungen abgleichen. Ergebnis als
Gap-Tabelle: `Schritt/ID | erwartet | im Dokument | Status (erfuellt/teilweise/fehlt) | Anmerkung`.

## Firmendaten-Trennung (Pflicht)

- **Generisch (hierher/teilbar):** Vorgehen, Template-Struktur, zitierte Norm, Gap-Kriterien.
- **Vertraulich (woanders):** das ausgefuellte Dokument mit Informationsverbund, Schutzbedarfen,
  Umsetzungsstaenden. Das gehoert in ein getrenntes, vertrauliches Repo/Vault — **nie** in dieses Plugin.
- Beim Erzeugen daher Platzhalter statt erfundener Firmeninhalte.

## Output-Disziplin

- Zitierfaehig: IDs, Wortlaut, Edition, Quelle (CC BY-SA 4.0).
- Klar markieren, was **normativ** (aus dem Korpus) und was **auszufuellen** ist.
- Keine Vollstaendigkeits- oder Konformitaetsgarantie — der Mensch entscheidet und verantwortet.
