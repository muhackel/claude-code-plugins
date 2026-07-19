---
name: mermaid
description: "Mermaid-Diagramme für den Vault erstellen — reference-first aus einem offline gespiegelten Mermaid-Doku-Klon, vor dem Commit lokal mit mmdc validiert. Obsidian rendert Mermaid nativ. Use when ein Mermaid-Diagramm, Flussdiagramm, Sequenzdiagramm, Klassendiagramm, Zustandsdiagramm, ER-Diagramm oder Gantt-Chart in einer Note erstellt oder korrigiert werden soll."
---

# mermaid — native Diagramme für den Obsidian-Vault

Erstellt **Mermaid**-Diagramme direkt in Vault-Notes. Obsidian rendert Mermaid **nativ** im
```` ```mermaid ````-Codeblock — kein Zusatz-Plugin nötig, das Diagramm ist im Vault sofort sichtbar.
Das macht Mermaid zur Standardwahl im Vault. Syntax wird **reference-first** aus der offline
gespiegelten Mermaid-Doku nachgeschlagen, nie aus dem Gedächtnis geraten.

## KERNREGEL — reservierte Wörter niemals als classDef-Namen

`classDef <name>` erzeugt in Mermaid eine gleichnamige **CSS-Klasse**. Heißt der Name wie ein
**interner SVG-Container** von Mermaid, greift das Styling auf Mermaids eigene Elemente über.
Verboten sind daher als classDef-Namen (und analog als Node-IDs): **`root`, `default`, `node`,
`edge`, `cluster`, `flowchart`** und ähnliche reservierte Wörter.

Konkret: `classDef root ...` matcht den Wurzel-Container `<g class="root">`, der **alle Kantenlabels**
umschließt → die Labels werden unlesbar. Im **Obsidian-Dark-Theme schwarz auf schwarz**, im **PDF-Export
hell auf hell** — es sieht nach einem Kontrast-/Layout-Problem aus, ist aber in Wahrheit eine
**Namenskollision**. Immer eindeutige, sprechende Namen verwenden: `rootca`, `nodesvc`, `edgewan` statt
`root`, `node`, `edge`.

## Zweite Falle — subgraph-Titel einzeilig halten

Lange `subgraph`-Titel brechen um; die umgebrochenen Folgezeilen verschwinden hinter benachbarten Knoten
und sind weg. Zonen-Titel **kurz und einzeilig** halten. Detail-Infos (IPs, Versionen, Ports) gehören in
die **Knoten**, nicht in den `subgraph`-Titel.

## Reference-first — Offline-Doku

Die Mermaid-Syntax steht als Markdown-Klon des `mermaid-js/mermaid`-Repos offline bereit:

    ${XDG_DATA_HOME:-$HOME/.local/share}/bibliothekarin/diagram-docs/mermaid/repo/

Die eigentliche Diagramm-Syntax liegt unter `packages/mermaid/src/docs/syntax/` (je Diagrammtyp eine
Markdown-Datei, z.B. `flowchart.md`, `sequenceDiagram.md`, `classDiagram.md`). Vor dem Schreiben eines
Konstrukts dort per grep nachschlagen statt zu raten:

    grep -rin "linkStyle" "${XDG_DATA_HOME:-$HOME/.local/share}/bibliothekarin/diagram-docs/mermaid/repo/packages/mermaid/src/docs/syntax/"

Befüllt/aktualisiert wird die Doku durch `nix run .#fetch-docs` (im selben Plugin). Das Doku-Alter zeigt:

    nix run .#fetch-docs -- --status

Update-Intervall 14 Tage: ist die Doku **≥ 14 Tage** alt, **einmal** ein Update anbieten — nicht bei
jedem Aufruf nachfragen.

## Lokale Validierung vor dem Vault-Commit

Bevor das Diagramm in eine Note geschrieben wird, in der devShell (`nix develop`) mit **mmdc**
(mermaid-cli) rendern:

    mmdc -i diagramm.mmd -o diagramm.svg

Rendert es **fehlerfrei**, ist die Syntax gültig. Das fängt sowohl Tippfehler als auch die oben
beschriebenen **Keyword-Kollisionen** ab, bevor sie im Vault landen. Erst nach erfolgreichem Render den
Codeblock in die Note übernehmen.

## Syntax-Anker je Diagrammtyp

Nur Einstiegspunkte — die vollständige Referenz steht offline (s.o.).

- **flowchart** (`flowchart TD` / `graph LR`): Kanten `-->`, Labels `-->|Text|`, Formen über Klammern
  (`[]` Rechteck, `()` rund, `{}` Raute). Richtung `TD`/`LR`/`BT`/`RL`.
- **sequenceDiagram**: `participant A`, Nachrichten `A->>B: Text`, gestrichelte Antwort `B-->>A:`,
  Aktivierung `activate`/`deactivate` oder `A->>+B` / `B-->>-A`.
- **classDiagram**: Beziehungen `A <|-- B` (Vererbung), `A *-- B` (Komposition), `A o-- B` (Aggregation);
  Member mit Sichtbarkeit `+ - # ~`.
- **stateDiagram-v2**: Start/Ende `[*]`, Übergänge `S1 --> S2: Ereignis`, verschachtelte States über
  `state Name { ... }`. (Immer die `-v2`-Variante nutzen.)
- **erDiagram**: `KUNDE ||--o{ BESTELLUNG : gibt` — Kardinalität über die Crow-Foot-Symbole
  (`||` genau eins, `o{` null bis viele).
- **gantt**: `dateFormat YYYY-MM-DD`, `section Phase`, Task `Name :id, 2026-01-01, 5d`; Meilenstein
  `:milestone,`.

## Diagrammtyp noch offen?

Steht noch nicht fest, **welcher** Diagrammtyp und **welches** Tool (Mermaid vs. PlantUML) überhaupt
passt, zuerst über `diagramm-auswahl` entscheiden — dieser Skill setzt die getroffene Wahl um.

## Referenzen

- Offline-Klon: `packages/mermaid/src/docs/` (aus `mermaid-js/mermaid`)
- Online-Fallback: <https://mermaid.js.org/>
