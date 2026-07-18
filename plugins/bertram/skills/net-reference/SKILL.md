---
name: net-reference
description: "Reference-first-Disziplin für Netzwerk-CLIs: Befehlsreferenz und Best Practices eines Geräts (Cisco IOS/IOS-XE/NX-OS, MikroTik RouterOS, Palo Alto PAN-OS, HP/Aruba, Juniper Junos) zitierfähig nachschlagen und anwenden, statt CLI-Syntax aus dem Gedächtnis zu raten. Nutzen, bevor eine unsichere Syntax, ein Default-Wert oder ein Feature-Verhalten ausgegeben wird. Quellen erst aufrufen, dann zitieren."
---

# Net-Reference — Nachschlagen statt raten

**Reference-first ist Pflicht.** Bevor du eine CLI-Syntax, einen Default-Wert oder ein Feature-Verhalten
ausgibst, dessen genaue Form du nicht sicher belegt hast: nachschlagen. Modellwissen zu Netzwerk-CLIs
ist veraltet und verwechselt Vendor-Dialekte — die häufigste Fehlerquelle. Eine belegte Antwort schlägt
fünf plausibel klingende geratene.

## Quellen nach Vendor

Offizielle Referenz zuerst. Community-Quellen nur ergänzend und als solche gekennzeichnet.

| Vendor / OS | Primärquelle | Typischer Inhalt |
|-------------|--------------|------------------|
| Cisco IOS / IOS-XE | Command Reference + Configuration Guides auf cisco.com; Feature Navigator | Kommando-Syntax, Feature-Verfügbarkeit je Version/Train |
| Cisco NX-OS | NX-OS Command Reference (cisco.com) | VDC/VPC/Fabric-Spezifika |
| MikroTik RouterOS | help.mikrotik.com (RouterOS-Doku) | Menü-Pfade (`/interface/...`), Property-Namen, Defaults |
| Palo Alto PAN-OS | docs.paloaltonetworks.com (PAN-OS Admin Guide + CLI Reference) | `set`/`configure`-Syntax, Commit-Modell, Zonen |
| HP/Aruba (AOS-CX, ArubaOS) | asp.arubanetworks.com / Aruba Docs | CX-CLI, Controller/AP-Config |
| Juniper Junos | junos-Doku auf juniper.net | `set`-Hierarchie, `commit confirmed` |

**Vom User gereichte Referenz** (PDF, exportierte Doku, Config-Snippet) hat Vorrang und wird per `Read`
eingelesen — sie ist oft genau die Version, die auf dem Zielgerät läuft.

## Workflow

1. **Frage präzisieren:** Welcher Vendor, welches OS und **welche Version**? Ein Kommando kann sich
   zwischen Trains/Releases ändern (Default-Werte, deprecated Syntax). Fehlt die Version, danach fragen
   oder sie aus einem `show version`/`/system resource print` ableiten.
2. **Quelle holen:** vom User gereichtes Dokument (`Read`) → sonst offizielle Vendor-Doku
   (`WebFetch` der konkreten Seite) → `WebSearch` nur, um die offizielle Seite zu finden. Community
   (Foren, Blogs) nur als letzter Ausweg und deutlich als unbestätigt kennzeichnen.
3. **Verifizieren, dann zitieren:** Die Seite tatsächlich aufrufen und den relevanten Abschnitt lesen,
   bevor du sie als Beleg nennst. Nie einen Link als „genau das" verkaufen, ohne den Inhalt geprüft zu
   haben.
4. **Zitierfähig ausgeben:** Syntax/Verhalten mit **Vendor + OS-Version + Quelle** wiedergeben. Bei
   Best Practices die empfehlende Quelle nennen (Vendor-Hardening-Guide, RFC, CIS-Benchmark).
5. **Auf die Aufgabe anwenden:** Erst nach Beleg das Kommando/den Config-Block für den konkreten Fall
   formulieren.

## Best Practices belegen

Best-Practice-Aussagen („MTU so, STP-Guard da, dieses Timeout") nie als gesetzt behaupten — mit Quelle
belegen: Vendor-Hardening/Design-Guide, einschlägiger RFC, oder ein anerkannter Benchmark (CIS). Wo eine
Empfehlung umstritten oder kontextabhängig ist (z.B. STP-Variante, Default-Route-Design), die
Abhängigkeit benennen statt eine Universallösung zu verkaufen.

## Wenn keine Referenz beschaffbar ist

Ist die konkrete Syntax nicht belegbar (kein Internet, keine gereichte Doku): das **offen sagen**, die
konzeptionelle Antwort auf Ebene des Ziels geben („du brauchst eine Route-Map, die … matcht") und die
exakte Syntax als **zu verifizieren** markieren — nicht eine erfundene Kommandozeile als Fakt ausgeben.
