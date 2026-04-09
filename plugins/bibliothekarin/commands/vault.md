---
name: vault
description: "Schneller Vault-Zugriff ohne Subagent — suchen, lesen, Tags anzeigen"
---

Führe den folgenden Vault-Befehl direkt via Obsidian CLI aus (kein Subagent nötig).
Vault: Memory. Alle Befehle mit `2>/dev/null` ausführen um stderr zu unterdrücken.

**Kein BibliotheKarin-Subagent spawnen.** Dieses Command ist für schnelle, leichtgewichtige Operationen.

Beispiele:
- `/vault suche OSPF` → `obsidian vault="Memory" search query="OSPF" 2>/dev/null`
- `/vault tags` → `obsidian vault="Memory" tags sort=count counts 2>/dev/null`
- `/vault lies BÜ-Netz` → `obsidian vault="Memory" read file="BÜ-Netz" 2>/dev/null`
- `/vault backlinks Notename` → `obsidian vault="Memory" backlinks file="Notename" 2>/dev/null`

Falls der User-Befehl nicht eindeutig auf einen CLI-Befehl abbildbar ist: das nächstliegende `obsidian`-Kommando wählen.
Falls die Operation komplex ist (Note erstellen, Synthese, Audit): stattdessen den BibliotheKarin-Agent spawnen.
