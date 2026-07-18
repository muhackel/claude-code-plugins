---
name: grimm
description: "Grimm (Behörden-Schreibstilist) direkt aufrufen — mit optionalem Sachverhalt/Auftrag"
---

Spawne den `grimm:grimm`-Agenten und übergib den User-Text als Arbeitsauftrag.

Routing-Hinweis:
- **Grimm** ist für **Formulierungsarbeit im Behörden-/Anordnungsstil**: einen Sachverhalt
  verwaltungsförmig ausformulieren, ein ganzes Dokument nach dem Führungsschema aufbauen (Anordnung,
  Vermerk, Konzept, Sachstandsbericht), vorhandenen Text ins Hoheitliche anheben oder einen Entwurf
  gegen die Amtsstil-Konventionen redigieren.
- Grimm **erfindet keine Fakten** und bewertet nicht die fachliche Richtigkeit — er liefert die Form,
  die Fakten kommen aus dem User-Text. Fehlt Material, setzt er Platzhalter und weist darauf hin.
- Geht es im User-Text um die **inhaltlich-fachliche Sache** (Netzwerk, VPN, IT-Grundschutz, NixOS,
  Wissensrecherche) und nicht um deren Verschriftlichung im Amtsstil, ist der jeweilige Fachagent die
  bessere Wahl. Mischfall — der Fachagent liefert den Sachverhalt, Grimm gießt ihn in Form: dann kann
  der Fachteil vorab geklärt und das Ergebnis anschließend an Grimm übergeben werden.

Kein Text angegeben: Grimm ohne Auftrag spawnen — er fragt nach Textsorte (Kurz-Sachverhalt oder ganzes
Dokument), Rohmaterial (Fakten, Beteiligte, Daten, Aktenzeichen, Fristen) sowie Adressat und Zweck.
