---
name: net-operate
description: "Gestufter Live-Zugriff auf Netzwerkgeräte per SSH — nur auf explizite Anforderung. Stufe 0 read-only (show/monitor/ping), Stufe 1 Config-Change mit Rollback-Netz und Bestätigung. Vendor-spezifische Change-Safety: Cisco reload-in/configure-replace, MikroTik RouterOS safe-mode, Palo Alto PAN-OS commit/revert, Juniper commit-confirmed. Remote-Lockout-Vermeidung als harte Checkliste. Nutzen, wenn der User Bertram explizit an ein echtes Gerät lässt."
---

# Net-Operate — gestufter Live-Zugriff

**Live-Zugriff ist opt-in.** Default über alle Bertram-Skills ist read-only. Dieser Skill greift nur,
wenn der User **explizit** verlangt, dass Bertram auf ein echtes Gerät zugreift, und er die
Berechtigung dafür hat. Zugriff per SSH über `Bash` (z.B. `ssh admin@<gerät> '<befehl>'` bzw.
netmiko/scrapli, falls in der Umgebung vorhanden). Syntax je Vendor über `net-reference` belegen.

## Eskalationsstufen

- **Stufe 0 — read-only (unkritisch):** `show`/`display`/`monitor`/`ping`/`traceroute`, RouterOS
  `... print`, PAN-OS `show`. Inspektion, Diagnose (`net-diagnose`), Ist-Config sichern. Keine
  Bestätigung nötig, aber Ziel-Gerät nennen.
- **Stufe 1 — schreibender Eingriff (bestätigungspflichtig):** jede Änderung am Live-Gerät.
  Voraussetzungen **vor** der Ausführung:
  1. **Ist-Config sichern** (`show running-config` / `export` / `show config` in eine Datei).
  2. **Exaktes Kommando + Ziel-Gerät nennen** und vom User bestätigen lassen.
  3. **Rollback-Netz aktivieren** (siehe unten) — bei jedem Eingriff, der die Erreichbarkeit
     berühren könnte.
  4. Nach dem Change **verifizieren** (erneut Diagnose/`show`), dann persistieren bzw. bestätigen.

## Rollback-Netz je Vendor

Der eigene Zugang ist das erste Opfer eines falschen Changes. Immer ein automatisches Zurück einbauen,
bevor der Eingriff läuft:

| Vendor | Rollback-Netz |
|--------|---------------|
| Cisco IOS/IOS-XE | `reload in <min>` vor dem Change (auto-Reboot auf letzte gespeicherte Config); nach Erfolg `reload cancel`. Alternativ `configure replace` / `archive` + `configure confirm` (rollback-timer). |
| MikroTik RouterOS | `/system/reboot` ist grob — besser **`safe-mode`** (Strg-X): Änderungen werden bei Verbindungsabbruch automatisch zurückgerollt. Für Reboot-Absicherung `/system scheduler` als Watchdog. |
| Palo Alto PAN-OS | Candidate-Config: `commit` erst nach Prüfung; `revert config` verwirft ungespeicherte Änderungen. Für riskante Commits Rollback über Config-Versionen. |
| Juniper Junos | **`commit confirmed <min>`** — Rollback automatisch, wenn nicht innerhalb der Frist ein zweites `commit` bestätigt. |
| Aruba CX | `checkpoint` vor dem Change; `checkpoint rollback <name>` zum Zurück; `copy running-config checkpoint`. |

Ist für einen Vendor kein automatisches Rollback verfügbar/belegt: das sagen und den Eingriff nur mit
gesicherter Ist-Config und explizitem User-Go durchführen.

## Remote-Lockout-Vermeidung (harte Checkliste)

Vor jedem Stufe-1-Eingriff prüfen:

1. **Läuft mein Zugriff über den Pfad, den ich ändere?** (Mgmt-Interface, Route zum Mgmt-Netz, ACL auf
   dem SSH-Port, NAT-Regel) → diese Elemente **zuletzt** und mit aktivem Rollback-Netz anfassen.
2. **ACL/Firewall-Änderung:** neue Regel testen, bevor die alte entfernt wird; nie den eigenen
   Admin-Zugriff aus der erlaubenden Regel entfernen.
3. **Interface-Shutdown:** nie auf dem Uplink/Mgmt-Port ohne Rollback-Timer.
4. **Routing/Default-Route:** Änderung kann den Rückweg killen — Return-Path mitdenken, Rollback-Netz
   Pflicht.
5. **Persistenz bewusst:** erst **nicht** persistieren (kein `write`), Erreichbarkeit verifizieren,
   **dann** speichern. So rettet ein Reboot den Zustand, falls der Change aussperrt.

## Optional: MCP-Zugriff (später)

Für RouterOS existiert ein MCP-Server (MikroMCP), der Geräte typisiert und auditierbar statt über rohes
SSH ansprechbar macht. Noch nicht Teil dieses Plugins — als möglicher Zugriffsweg vermerkt (siehe
BACKLOG). Solange nicht eingebunden: SSH-Weg oben.

## Was du nicht tust

- Keinen Stufe-1-Eingriff ohne explizite Anforderung, gesicherte Ist-Config, Bestätigung und
  Rollback-Netz.
- Keine Persistenz vor der Erreichbarkeits-Verifikation.
- Keinen Zugriff auf Geräte ohne Berechtigung.
