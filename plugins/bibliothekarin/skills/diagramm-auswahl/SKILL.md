---
name: diagramm-auswahl
description: "Empfiehlt für ein Visualisierungsziel die passende Diagrammart UND das passende Tool (Mermaid vs. PlantUML vs. json-canvas). Standard im Vault ist Mermaid (Obsidian-nativ); PlantUML nur für Typen, die Mermaid nicht kann. Use when unklar ist, welches Diagramm passt, wie sich X visualisieren lässt, oder eine Diagramm-Empfehlung gefragt ist."
---

# diagramm-auswahl — Zweck → Diagrammtyp → Tool

Wählt vor der Erstellung die richtige **Diagrammart** und das richtige **Tool**. Ergebnis ist eine
begründete Empfehlung; die **Erstellung** übernimmt dann `mermaid`, `plantuml` oder `json-canvas`.

## Entscheidungsmatrix

| Zweck / Frage | Diagrammtyp | Tool |
|---|---|---|
| Ablauf, Prozess, Entscheidungslogik | Flowchart | **Mermaid** |
| Interaktion, Nachrichtenfolge über die Zeit | Sequenzdiagramm | **Mermaid** (Detailtiefe hoch → PlantUML) |
| Datenstruktur, Klassen, Beziehungen | Klassendiagramm / ER | **Mermaid** |
| Zustände, Verhalten, Übergänge | State (Zustandsdiagramm) | **Mermaid** |
| Zeitplan, Projektphasen, Termine | Gantt | **Mermaid** |
| Zeitliches Signal-/Pegelverhalten | Timing | **PlantUML** |
| Objektinstanzen mit konkreten Werten | Objektdiagramm | **PlantUML** |
| Infrastruktur, Verteilung, Nodes/Artefakte | Deployment / Component | **PlantUML** |
| UI-Entwurf / Maske | Wireframe (Salt) | **PlantUML** |
| Enterprise-Architektur | Archimate | **PlantUML** |
| Ideensammlung, Themenbaum | MindMap | **Mermaid** (oder json-canvas) |
| Freie räumliche Anordnung, Vault-Mindmap, Notizen verbinden | — | **json-canvas** |

## Tool-Wahl-Regel

1. **Im Vault standardmäßig Mermaid.** Obsidian rendert es **nativ** — das Diagramm ist ohne Zusatz sofort
   sichtbar. Alles, was Mermaid abbilden kann, wird in Mermaid gebaut.
2. **PlantUML nur für Typen, die Mermaid nicht beherrscht** (Deployment, Component, Timing, Salt/Wireframe,
   Archimate, Objektdiagramm) oder bei **sehr hoher Detailtiefe**. Dabei den **Rendering-Vorbehalt**
   nennen: PlantUML ist nicht Obsidian-nativ und braucht das Community-Plugin oder einen PlantUML-Server,
   sonst erscheint nur der Code-Block.
3. **Freie, nicht-textbasierte Anordnung** (räumliches Layout, Karten frei ziehen, Notes/Dateien/Bilder
   mischen) → **`json-canvas`** statt eines textbeschriebenen Diagramms.

Faustregel: **Mermaid, außer der gewünschte Typ oder die Detailtiefe zwingt zu PlantUML** — und die
Rendering-Hürde ist es wert.

## Workflow

1. **Zweck klären:** Was soll das Diagramm zeigen (Ablauf, Interaktion, Struktur, Zustand, Zeit,
   Infrastruktur, Ideen)? Bei Unklarheit kurz nachfragen, nicht raten.
2. **Typ wählen:** über die Matrix den passenden Diagrammtyp bestimmen.
3. **Tool wählen:** Tool-Wahl-Regel anwenden (Default Mermaid; PlantUML mit Vorbehalt; freie Anordnung
   json-canvas).
4. **Übergeben:** die Erstellung an `mermaid` bzw. `plantuml` delegieren (dort reference-first + lokale
   Validierung) oder an `json-canvas`.

## Cross-Referenzen

- `mermaid` — Umsetzung native Vault-Diagramme (Default)
- `plantuml` — Umsetzung UML-Typen jenseits von Mermaid, mit Rendering-Vorbehalt
- `json-canvas` — freie räumliche Anordnung, Vault-Mindmaps, `.canvas`-Dateien
