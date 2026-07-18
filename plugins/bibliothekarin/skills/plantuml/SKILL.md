---
name: plantuml
description: "PlantUML-Diagramme erstellen — reference-first aus einem offline gespiegelten Language Reference Guide, lokal mit plantuml validiert. NICHT Obsidian-nativ (braucht Community-Plugin/Server) — nur wählen, wenn der Mehrwert die Rendering-Hürde rechtfertigt. Use when ein PlantUML- oder UML-Diagramm gebraucht wird, insbesondere Deployment-, Komponenten-, Timing-, Objekt- oder detailtiefe Sequenzdiagramme, Wireframes (Salt) oder Archimate."
---

# plantuml — mächtige UML-Diagramme mit Rendering-Vorbehalt

Erstellt **PlantUML**-Diagramme für Diagrammtypen und Detailtiefen, die Mermaid nicht beherrscht.
Syntax wird **reference-first** aus der offline gespiegelten PlantUML-Doku nachgeschlagen, nie geraten.

## Rendering-Realität — ehrlich benennen

PlantUML ist **nicht** Obsidian-nativ. Ein ```` ```plantuml ````-Block im Vault zeigt ohne Zusatz nur den
**Code**, kein Diagramm. Damit es rendert, braucht der Vault das **PlantUML-Obsidian-Community-Plugin**
oder einen erreichbaren **PlantUML-Server**. Daraus folgt die Wahlregel:

> **PlantUML nur wählen, wenn der Mehrwert die Rendering-Hürde rechtfertigt** — also für Diagrammtypen,
> die Mermaid gar nicht kann (Deployment, Component, Timing, Salt/Wireframe, Archimate, Objektdiagramm),
> oder bei sehr hoher Detailtiefe. Für alles, was Mermaid genauso gut abbildet, **Mermaid nehmen** (sofort
> im Vault sichtbar). Im Zweifel `diagramm-auswahl` entscheiden lassen.

Wird PlantUML gewählt, den Nutzer auf die Rendering-Voraussetzung hinweisen, falls im Vault nicht bereits
vorhanden.

## Reference-first — Offline-Doku

Die PlantUML-Syntax steht offline bereit:

    ${XDG_DATA_HOME:-$HOME/.local/share}/bibliothekarin/diagram-docs/plantuml/

Enthalten sind ein **Website-Mirror** und der aus dem offiziellen PDF extrahierte Volltext
`PlantUML_Language_Reference_Guide_en.txt`. Vor dem Schreiben eines Konstrukts dort per grep nachschlagen:

    grep -in "skinparam" "${XDG_DATA_HOME:-$HOME/.local/share}/bibliothekarin/diagram-docs/plantuml/PlantUML_Language_Reference_Guide_en.txt"

Befüllt/aktualisiert wird die Doku durch `nix run .#fetch-docs`. Das Doku-Alter zeigt:

    nix run .#fetch-docs -- --status

Update-Intervall 14 Tage: bei **≥ 14 Tagen** Alter **einmal** ein Update anbieten, nicht spammen.

## Lokale Validierung

Vor der Übernahme in eine Note in der devShell (`nix develop`) mit **plantuml** rendern:

    plantuml diagramm.puml

Das erzeugt ein PNG (bzw. `-tsvg` für SVG) und **validiert die Syntax**. Java und Graphviz kommen aus dem
Flake — keine systemweite Installation nötig. Rendert es fehlerfrei, ist die Syntax gültig.

## PlantUML-eigene Fallstricke

- **Klammerung:** Jedes Diagramm zwischen `@startuml` / `@enduml` (bzw. `@startsalt`/`@endsalt`,
  `@startmindmap` …). Fehlt das Paar oder passt der Typ nicht, rendert nichts.
- **Reservierte Wörter als Alias:** Keywords (`actor`, `class`, `note`, `end`, `state` …) nicht als Alias
  oder Bezeichner verwenden — führt zu Parse-Fehlern. Sprechenden Alias vergeben (`as svc`).
- **`skinparam`:** Styling über `skinparam` (bzw. neuere `<style>`-Blöcke); Parameternamen exakt aus der
  Referenz übernehmen, falsch geschriebene werden still ignoriert.
- **`!include`:** Eingebundene Dateien/Bibliotheken (z.B. C4, Archimate) müssen erreichbar sein; im Vault
  ist der Pfad-/Netzzugriff oft eingeschränkt — bevorzugt Standard-Library-Includes.
- **Graphviz-Abhängigkeit:** Manche Layouts brauchen Graphviz (im Flake vorhanden); bei Layout-Fehlern
  zuerst das prüfen.

## Diagrammtyp noch offen?

Steht noch nicht fest, welcher Diagrammtyp und welches Tool passt, zuerst über `diagramm-auswahl`
entscheiden — dieser Skill setzt die getroffene Wahl um.

## Referenzen

- Offline: `PlantUML_Language_Reference_Guide_en.txt` + Website-Mirror
- Online-Fallback: <https://plantuml.com/>
