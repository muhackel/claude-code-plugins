---
name: bruce
description: "Bruce (IT-Grundschutz-Berater) direkt aufrufen — mit optionalem Auftrag"
---

Spawne den `it-grundschutz:bruce`-Agenten und uebergib den User-Text als Arbeitsauftrag.

Routing-Hinweis:
- **Bruce** ist fuer IT-Grundschutz-Arbeit auf Basis des lokalen OSCAL-Korpus: Anforderung/Baustein
  nachschlagen (per ID wie `GC.1.1` oder Thema), Bausteine fuer ein Szenario modellieren, Editionen
  abgleichen (Crosswalk Edition 2023 ↔ Grundschutz++), den Korpus von der BSI-Quelle laden/aktualisieren.
- Geht es um **firmenspezifische, vertrauliche** Modellierung (konkrete Informationsverbuende,
  Umsetzungsstaende) — das gehoert **nicht** in dieses teilbare Plugin. Bruce steuert nur die generische
  Grundschutz-Ebene bei; die vertrauliche Ebene gehoert in ein getrenntes Repo/Vault.
- Geht es um **allgemeine Wissensrecherche/Archivierung ohne Grundschutz-Bezug** und ist ein
  Wissensmanagement-Agent installiert (z.B. **Karin** / `bibliothekarin`), ist dieser die bessere Wahl.

Kein Text angegeben: Bruce ohne Auftrag spawnen — er fuehrt seinen STARTUP aus (Nix-Umgebung,
Korpus-Status) und fragt nach dem Auftrag.
