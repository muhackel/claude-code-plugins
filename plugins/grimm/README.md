# grimm — Behörden-Schreibstilist

Grimm, der Referats-Schreiber. Er überführt Sachverhalte in das nüchterne, distanzierte, hoheitliche
Deutsch der öffentlichen Verwaltung — den Ton von innerdienstlicher Anordnung, Vermerk und Konzept.
Diesen Vorgang nennen wir **grimmifizieren**. Kern-Prinzip: **Form, nicht Fakten** — der User liefert
den Sachverhalt, Grimm liefert die verwaltungsförmige Sprache.

Der Stil ist aus dem klassischen Verwaltungs- und Stabsstil destilliert und in generische Stilregeln
gefasst.

## Philosophie

- **Formulieren, nicht erfinden:** Grimm gießt gegebene Fakten in Form. Fehlt ein Datum, ein
  Aktenzeichen, eine Rechtsgrundlage, setzt er einen erkennbaren Platzhalter und weist darauf hin —
  statt plausibel zu raten. Ein erfundenes Az. in einer Anordnung ist ein schwerer Fehler.
- **Verbindlichkeit entsteht grammatisch:** Pflichten stehen als Gebotsform (`ist zu` / `hat zu` /
  „gewährleistet, dass…"), der Ton bleibt durchgängig unpersönlich und dritte Person.
- **Struktur trägt den Text:** Ganze Dokumente folgen dem Führungsschema oder einer der Vorlagen
  (Vermerk, Konzept, Sachstandsbericht) — nicht drauflosschreiben.
- **Sprache, nicht Sache:** Grimm bewertet nicht die fachliche Richtigkeit; er redigiert die Form.

## Komponenten

| Typ | Name | Zweck |
|-----|------|-------|
| Agent | `grimm:grimm` | Behörden-Schreibstilist-Persona, orchestriert die Skills |
| Command | `/grimm` | Grimm direkt aufrufen (mit optionalem Sachverhalt/Auftrag) |
| Skill | `amtsstil` | Mikroebene: Ton, Grammatik, Floskellexikon, Anti-Patterns, Redigier-Checkliste |
| Skill | `dokumentaufbau` | Makroebene: Gliederungsvorlagen (Anordnung/Führungsschema, Vermerk, Konzept, Sachstandsbericht) |

## Nutzung

```
/grimm grimmifiziere: Umzug der Systeme ab April, alle Fachbereiche benennen Ansprechpartner
/grimm bau daraus eine innerdienstliche Anordnung nach Führungsschema
/grimm heb diesen Entwurf ins Amtsdeutsch an: [Text]
/grimm redigiere diesen Vermerk gegen die Amtsstil-Konventionen
```

Ohne Text spawnt der Command Grimm, der dann nach Textsorte (Kurz-Sachverhalt oder ganzes Dokument),
Rohmaterial (Fakten, Beteiligte, Daten, Aktenzeichen, Fristen) sowie Adressat und Zweck fragt.

## Installation (lokal)

```bash
/plugin marketplace add ./
/plugin install grimm --scope local
```

## Lizenz

MIT.
