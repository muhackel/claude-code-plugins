---
name: karin
description: "Karin (Wissensmanagerin) direkt aufrufen — mit optionalem Auftrag"
---

Analysiere den User-Text und wähle den passenden Agent:

**`bibliothekarin:bibliothekarin-search`** (leichtgewichtig, ~8.600 Tokens weniger) wenn:
- Wissensfrage: "Was weiß ich über ...", "Fasse zusammen ...", "Suche ..."
- Vault-Recherche ohne Schreibabsicht
- Synthese über mehrere Notes
- Schlüsselwörter: suche, finde, was weiß, zusammenfassung, synthese, recherche (lesend)

**`bibliothekarin:bibliothekarin`** (vollständig) wenn:
- Wissen einpflegen: Note erstellen, URL archivieren, Ingest
- Vault-Pflege: Scan, Audit, Index aktualisieren
- Destillation: Auto-Memory oder claude/-Arbeitskopien überführen
- Wissenslücken identifizieren (RECHERCHE)
- Kein Text angegeben (IDLE-Menü)
- Schlüsselwörter: erstelle, pflege ein, archiviere, scan, audit, destilliere, index

Übergib den User-Text als Arbeitsauftrag an den gewählten Agent.
