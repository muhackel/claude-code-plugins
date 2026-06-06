---
name: gs-review
description: "IT-Grundschutz-Check / Soll-Ist-Umsetzungsprüfung: je zutreffender Anforderung den Umsetzungsstatus erheben und auswerten — Schema entbehrlich/ja/teilweise/nein (Grundschutz++ Umsetzung kennt nur ja/nein, siehe UMS.1.1), plus status=entfallen (Edition 2023). Baut auf der Soll-Liste aus gs-modellierung auf, zieht Anforderungstexte zitierfähig via gs-lookup. Liefert Erfüllungsgrad je Schicht/Schutzbedarf, offene Punkte, Realisierungsliste und Audit-/Zertifizierungs-Readiness. Nutzen, wenn 'wie weit ist X umgesetzt' / 'Soll-Ist-Check' / 'Grundschutz-Check' gefragt ist. Nur generisch — der ausgefüllte Check mit realen Statuswerten gehört in ein vertrauliches Repo."
---

# gs-review — IT-Grundschutz-Check (Soll-Ist-Umsetzungsprüfung)

Erhebt und wertet je zutreffender Anforderung den **Umsetzungsstatus** aus: das Ist gegen das Soll. Arbeitet
gegen den lokalen Korpus (`gs-lookup`/`gs.py`), erfindet nichts. Die Methodik des Checks selbst steht im
Korpus (Schicht **UMS** „Umsetzung", flankiert von **PERF**/**VRB**) — nicht aus dem Gedächtnis ableiten.

## Korpus-first: wo der Check verortet ist (Pflicht)

Das Vorgehen wird **nie aus dem Gedächtnis** wiedergegeben — es kommt aus der Methodik-Ebene des Korpus:

```bash
nix run .#gs -- get UMS.1.1     # Ermittlung des Umsetzungsstatus (Kern des Checks)
nix run .#gs -- list UMS        # ganze Umsetzungs-Schicht (Status->Restrisiko->Plan->Termine->Nachverfolgung)
nix run .#gs -- get VRB.6.1     # Wirksamkeitsprüfung (umgesetzt ist nicht gleich wirksam)
nix run .#gs -- get PERF.3.1    # Auditprogramm (intern/extern, Basis für Zertifizierung)
```

Tragende Anforderungen (Grundschutz++, zitierfähig nachschlagen statt zitieren-aus-dem-Kopf):

| ID | Was der Check daraus zieht |
|----|----------------------------|
| **UMS.1.1** | Umsetzungsstatus **vollständig** überprüfen; Status ist **ja/nein**, „ja" nur wenn auch alle abhängigen Anforderungen umgesetzt sind |
| **UMS.2.1** | Restrisiko der **nicht** umgesetzten Anforderungen festlegen |
| **UMS.3.1 / UMS.3.2** | Maßnahmen für die offenen Punkte, Priorisierung |
| **UMS.4.1 / UMS.4.2** | Verantwortliche benennen, realistische Umsetzungsfristen |
| **UMS.5.1 / UMS.5.2** | Ausnahmen autorisieren und mit **Begründung** dokumentieren |
| **UMS.6.1 / UMS.6.2** | Fortschritt nachverfolgen (Soll-Ist-Vergleich), Umsetzungsplan fortschreiben |
| **VRB.6.1** | Wirksamkeit der umgesetzten Maßnahmen prüfen |
| **PERF.3.1 / PERF.4.1 / PERF.5.1** | Auditprogramm, Auditdoku, Managementbewertung (Eignung/Angemessenheit/Wirksamkeit) |

## Status-Schema

Klassische IT-Grundschutz-Check-Stufen — je Anforderung genau eine:

| Status | Bedeutung |
|--------|-----------|
| **entbehrlich** | Anforderung greift im Zielobjekt nicht (z.B. Technik nicht vorhanden) — mit Begründung |
| **ja** | vollständig umgesetzt (inkl. aller abhängigen Anforderungen, UMS.1.1) |
| **teilweise** | begonnen/teilweise wirksam — offener Rest |
| **nein** | nicht umgesetzt |
| **entfallen** | nur Edition 2023: Anforderung aus dem Katalog **gestrichen** (`props status=entfallen`); kein Erhebungsergebnis, sondern editorischer Fakt aus dem Korpus — nicht zu bewerten |

> **Editionsunterschied (wichtig, nicht erfinden):** Grundschutz++ definiert den Umsetzungsstatus in
> **UMS.1.1 ausdrücklich binär** (`„umgesetzt"/„ja"` oder `„nicht umgesetzt"/„nein"`). Die feinere
> Vier-Stufen-Skala (`entbehrlich/ja/teilweise/nein`) ist der klassische IT-Grundschutz-Check (Edition 2023 /
> BSI-Standard 200-2). Wer in Grundschutz++ `teilweise`/`entbehrlich` nutzt, tut das als pragmatische
> Erhebungshilfe — für die formale Bewertung zählt dort `ja` erst bei voller Umsetzung.

Je Eintrag erhoben werden: **Status, Begründung, Verantwortliche(r), Umsetzungstermin/Referenz** (UMS.4.1/4.2,
bei `entbehrlich`/Ausnahme die Begründung gemäß UMS.5.2).

## Eingang: die Soll-Liste

`gs-review` setzt auf dem **Soll** auf, nicht auf dem leeren Katalog:

1. **Soll bestimmen** mit `gs-modellierung` — welche Bausteine/Anforderungen treffen auf das Szenario zu.
2. **Anforderungstexte zitierfähig ziehen** mit `gs-lookup`/`gs.py get`/`list` — Wortlaut, `sec_level`,
   `effort_level`, Edition, Quelle.
3. **Ist erheben** je Anforderung: Status nach obigem Schema + Begründung/Verantwortlich/Termin.

Liegt keine Modellierung vor: erst dorthin (`gs-modellierung`), nicht den ganzen Katalog blind durchprüfen.

## Editionsübergreifend

Funktioniert für beide Editionen über `gs.py --edition …`:

```bash
nix run .#gs -- --edition grundschutz-pp list SYS         # Grundschutz++ (Default)
nix run .#gs -- --edition edition-2023 list SYS.1.1       # Edition 2023, inkl. entfallen-Markierung
```

- **Priorisierung** über die Norm-Props: Grundschutz++ `sec_level` (`normal-SdT`/`erhöht`) und
  `effort_level` (0–5); Edition 2023 `sec_level` (`Basis`/`Standard`/`erhöht`). Basis/`normal-SdT` zuerst,
  niedriger `effort_level` als Quick-Win.
- **`status=entfallen`** (Edition 2023): nicht als offenen Punkt zählen, sondern als entfallen ausweisen.

## Vorlage erzeugen (leerer Check)

`gs.py checklist <selektor…>` gibt die **leere Soll-Ist-Check-Vorlage** als Markdown-Tabelle aus
(`ID | Titel | sec_level | Status | Begründung | Verantwortlich | Termin`) — die Norm-Spalten aus dem Korpus,
die Erhebungsspalten leer. Es nimmt **mehrere Selektoren** (Schicht/Gruppe **oder** exakte Anforderungs-ID,
dedupliziert), sodass die Soll-Liste aus `gs-modellierung` direkt in **eine** kombinierte Vorlage geht —
statt pro Gruppe einzeln:

```bash
nix run .#gs -- checklist UMS                              # eine ganze Schicht (Grundschutz++)
nix run .#gs -- checklist KONF.2 KONF.8.1 BER.3            # modellierte Soll-Liste: Gruppen + exakte IDs
nix run .#gs -- --edition edition-2023 checklist SYS.1.1   # Edition 2023 (entfallen wird vorbelegt)
```

In Grundschutz++ erscheint der Hinweis auf das binäre Status-Schema (UMS.1.1); in Edition 2023 werden
`entfallen`-Anforderungen in der Status-Spalte vorbelegt.

## Auswertung (Ergebnis des Checks)

1. **Erfüllungsgrad** je Schicht und je Schutzbedarfs-/Sicherheitsstufe (`sec_level`): Anteil `ja` an den
   nicht-`entbehrlich`/nicht-`entfallen` Anforderungen. Getrennt nach Stufe ausweisen.
2. **Offene Punkte:** alle `nein`/`teilweise`, nach `sec_level`/`effort_level` priorisiert (Restrisiko nach
   UMS.2.1 benennen, nicht beziffern-aus-dem-Kopf).
3. **Realisierungs-/Maßnahmenliste:** je offenem Punkt Maßnahme, Verantwortliche(r), Termin (UMS.3.x/4.x) —
   das übernehmbare Arbeitsergebnis.
4. **Ausnahmen** (`entbehrlich`/autorisierte Abweichung): mit Begründung dokumentiert (UMS.5.2)?

### Audit-/Zertifizierungs-Readiness (Ausbau)

Auf Wunsch: was fehlt für eine Zertifizierung? Prüfen entlang **PERF** (Auditprogramm PERF.3.1,
Auditdoku PERF.4.1, Managementbewertung PERF.5.1) und **VRB.6.1** (Wirksamkeit). Readiness = offene
Basis-/`normal-SdT`-Anforderungen, undokumentierte Ausnahmen, fehlende Wirksamkeitsnachweise. **Keine
Konformitätsgarantie** — die Bewertung trifft der Mensch/Auditor.

## Abgrenzung zu den Nachbar-Skills (scharf)

| Skill | Frage | Gegenstand |
|-------|-------|-----------|
| **gs-modellierung** | *Was trifft zu?* (Soll) | bestimmt die zutreffenden Bausteine/Anforderungen |
| **gs-review** (hier) | *Wie weit umgesetzt?* (Soll-Ist) | erhebt + wertet den **Umsetzungsstatus in der Realität** je Anforderung |
| **gs-dokument** | *Steht es richtig im Dokument?* | erstellt/führt Dokumente nach der Methodik oder prüft ein Dokument **strukturell** (Gap der Dokumentation) |

- `gs-review` prüft die **Umsetzung in der Realität**, `gs-dokument` (Modus Gap) prüft die **Struktur eines
  Dokuments** gegen die Methodik. Ein vollständig dokumentiertes Konzept kann real unzureichend umgesetzt
  sein — und umgekehrt. Beide ergänzen sich: Modellierung liefert das Soll, gs-review den Umsetzungsstand,
  gs-dokument hält beides revisionssicher fest.

## Firmendaten-Trennung (Pflicht)

- **Generisch (hierher/teilbar):** das Vorgehen, das Status-Schema, die Auswertungslogik, die zitierte Norm,
  eine **leere Check-Vorlage** (`gs.py checklist`).
- **Vertraulich (woanders):** der **ausgefüllte** Check mit realen Statuswerten, Begründungen,
  Verantwortlichen und Terminen — das gehört in ein getrenntes, vertrauliches Repo/Vault, **nie** in dieses
  Plugin. Beim Erzeugen Platzhalter lassen, nichts erfinden.

## Output-Disziplin

- Zitierfähig: IDs, Wortlaut, Edition, Quelle (CC BY-SA 4.0).
- Klar markieren, was **normativ** (aus dem Korpus) und was **Erhebungsergebnis** (Status/Begründung) ist.
- **Keine Konformitäts- oder Vollständigkeitsgarantie** — der Mensch entscheidet und verantwortet.
