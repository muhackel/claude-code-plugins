---
name: nixie
description: "Nixie (NixOS-Engineer) direkt aufrufen — mit optionalem Auftrag"
---

Spawne den `nixie:nixie`-Agenten und übergib den User-Text als Arbeitsauftrag.

Routing-Hinweis:
- **Nixie** ist für Nix/NixOS-Arbeit: Flakes, Module, Feature-Flags, Optionen, eigene Derivations, Overlays,
  Paket-Pinning, `nix flake check`, `nixos-rebuild` (build/switch), Remote-Build und Deploy.
- Geht es im User-Text **ausschließlich** um allgemeine Wissensrecherche oder das Dokumentieren in einer
  Knowledge Base ohne konkrete Nix-Aufgabe (Schlüsselwörter: was weiß ich über, fasse zusammen, archiviere,
  pflege ein, recherchiere) und ist ein Wissensmanagement-Agent installiert (z.B. **Karin** /
  `bibliothekarin`), ist dieser die bessere Wahl — dann ihn spawnen statt Nixie.
- Mischfall (Nix-Aufgabe, die nebenbei tiefe Recherche braucht): Nixie spawnen. Sie recherchiert selbst;
  ist ein Wissensmanagement-Agent installiert, kann sie optional ein Recherche-Briefing zurückliefern, das
  du anschliessend an diesen gibst.

Kein Text angegeben: Nixie ohne Auftrag spawnen — sie führt ihren STARTUP aus (Repo/Host-Kontext,
Build-Host-Config) und fragt nach dem Auftrag.
