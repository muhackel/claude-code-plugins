---
name: gs-krypto
description: "Kryptographische Verfahren, Schlüssellängen und Cipher-Suiten zitierfähig bewerten — Primärquelle BSI TR-02102 (Teile -1 bis -4) mit internationaler Gegenprobe (NIST SP 800-57, FIPS 140-3/197/186, RFCs). Liefert ein belegtes Urteil (konform / abzulösen / verboten) mit Quelle, Teil, Tabelle/Abschnitt und Stand/Jahr. Nutzen für die Bewertung von symmetrischen/asymmetrischen Verfahren, Hashfunktionen, PFS, Protokoll-Versionen (TLS/IPsec/SSH) und ganzen Cipher-Suiten — besonders als Zulieferung an Christian bei der VPN-Config-Härtung (OpenVPN/WireGuard/IPsec)."
---

# gs-krypto — zitierfähige Krypto-Bewertung nach BSI TR-02102

Bewertet kryptographische Verfahren, Schlüssellängen und Cipher-Suiten **zitierfähig** — für den
Grundschutz-Kontext und als Zulieferung an **Christian** (VPN-Agent) bei der Härtung von OpenVPN-,
WireGuard- und IPsec-Konfigurationen. Ergebnis ist stets ein belegtes Urteil mit Quelle, Teil,
Tabelle/Abschnitt und Stand/Jahr — nicht eine Bauchmeinung.

## WICHTIGE Abgrenzung — die bewusste Ausnahme von der Korpus-first-Regel

Bruce liest Grundschutz-Inhalte **ausschließlich** aus dem lokalen OSCAL-Korpus. **Krypto-Empfehlungen
sind die eine bewusste Ausnahme davon:** Sie kommen **weder** aus dem OSCAL-Korpus **noch** aus dem
Modellgedächtnis, sondern **live** aus den offiziellen Krypto-Quellen (WebFetch). Grund: TR-02102 wird
**jährlich** revidiert, Schlüssellängen und Gültigkeitszeiträume verschieben sich; Trainingswissen dazu
ist stale und fliegt im Audit auf. Grundschutz-Inhalte (Anforderungen, Bausteine, Gefährdungen) bleiben
davon unberührt **strikt korpus-first**.

## Quellen

**Primärquelle — BSI TR-02102** (bsi.bund.de), vier Teile, jährliche Revision → immer die **aktuelle
Fassung** ziehen und **Stand/Jahr** zitieren:

- **TR-02102-1** — Kryptographische Verfahren: Empfehlungen und Schlüssellängen (allgemein: Algorithmen,
  Schlüssellängen, Gültigkeitszeiträume). Die Basis für alle Einzelurteile.
- **TR-02102-2** — Verwendung von Transport Layer Security (TLS).
- **TR-02102-3** — Verwendung von IPsec und IKEv2.
- **TR-02102-4** — Verwendung von Secure Shell (SSH).

**Internationale Gegenprobe (aktiv nutzen — der Nutzer will FIPS/NIST-Hinweise ausdrücklich mit einbezogen):**

- **NIST SP 800-57** — Key-Management, „security strength" (Bit-Sicherheit je Verfahren/Länge).
- **FIPS 140-3** (Krypto-Modul-Anforderungen), **FIPS 197** (AES), **FIPS 186** (DSA/ECDSA).
- **Einschlägige RFCs** — **RFC 8446** (TLS 1.3), **RFC 7296** (IKEv2), **RFC 9142** (SSH-Key-Exchange).

Wo **BSI und NIST voneinander abweichen** (z.B. brainpool- vs. NIST-Kurven, zulässige DH-Gruppen,
Migrationsfristen): **beide nennen** und den Unterschied **kennzeichnen** — nicht stillschweigend eine
Seite bevorzugen.

**Häufigster Stolperstein — Kurven-Layering:** TR-02102-**1** (Anhang B.3) empfiehlt als EC-Kurven
**brainpool**; die Protokoll-Teile **-2 (TLS), -3 (IPsec), -4 (SSH)** heben im jeweiligen Kontext
zusätzlich die **NIST-Kurven** (secp/nistp 256/384/521) auf die Empfehlungsliste. Curve25519/Ed25519
stehen in **keinem** Teil (Stand 2026-01). Im Protokollkontext den **Protokoll-Teil führen lassen** —
sonst lehnt man eine dort zulässige NIST-Kurve fälschlich ab oder gibt curve25519/ed25519 als
„TR-konform" frei, obwohl sie es nicht sind.

### Beschaffung: PDF ziehen, nicht auf WebFetch-Prosa verlassen

TR-02102 und die NIST-SPs liegen als **PDF** vor. WebFetch liefert diese oft nur als
unbrauchbaren Binärstream — die Tabellenwerte gehen dabei verloren, und man landet doch beim
Raten aus dem Gedächtnis. **Zuverlässiger Weg:** das PDF laden und lokal mit `pdftotext` zu Text
wandeln, dann die Tabellen/Abschnitte auswerten:

    nix-shell -p poppler-utils --run 'pdftotext -layout TR02102-1.pdf - | less'

- **BSI TR-02102** — Basis-URL `https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Publikationen/TechnischeRichtlinien/TR02102/`,
  je Teil ein PDF (Stand geprüft 2026-07-18), Query `?__blob=publicationFile` anhängen:

  | Teil | Dateiname | Kontext |
  |------|-----------|---------|
  | **-1** | `BSI-TR-02102.pdf` **(ohne Suffix!)** | Basis: Algorithmen, Schlüssellängen, Fristen |
  | **-2** | `BSI-TR-02102-2.pdf` | TLS |
  | **-3** | `BSI-TR-02102-3.pdf` | IPsec/IKEv2 |
  | **-4** | `BSI-TR-02102-4.pdf` | SSH |

  Vor dem Zitieren die **Versions-/Stand-Angabe im PDF-Kopf** (z.B. „Version 2026-01") ablesen und mitzitieren.
- **NIST SP 800-57 Part 1:** nvlpubs.nist.gov (Rev. 5). Ebenfalls PDF → `pdftotext`.

`-layout` erhält die Tabellenstruktur — ohne das Flag verrutschen die Spalten der Schlüssellängen-Tabellen.

## Was abgedeckt wird

- **Symmetrisch:** AES-128/192/256, Betriebsmodi und **AEAD** (GCM), Abgrenzung zu CBC ohne Integrität.
- **Asymmetrisch + Schlüssellängen:** RSA (≥ 3000 bit gemäß aktueller TR-02102-1), ECC/ECDH/ECDSA-Kurven
  (**brainpool vs. NIST-Kurven** — BSI/NIST-Abweichung kennzeichnen), DH-Gruppen.
- **Hashfunktionen:** SHA-2, SHA-3; **SHA-1 verboten** (Kollisionen), MD5 ohnehin.
- **PFS** (Perfect Forward Secrecy) — ephemere Schlüssel (DHE/ECDHE) als Anforderung.
- **Protokoll-Versionen:** TLS 1.2 / 1.3, IKEv2, SSH — Altversionen (TLS < 1.2, SSLv3, IKEv1) benennen.
- **Cipher-Suiten-Bewertung** — ganze Suiten gegen die TR-02102-Teil-Tabellen prüfen.
- **Gültigkeits-/Migrationszeiträume** — TR-02102 nennt **Jahreszahlen** der Eignung (bis wann ein
  Verfahren empfohlen ist); diese explizit zitieren, nicht „sicher/unsicher" pauschalisieren.
- **PQC-Ausblick** — Post-Quantum-Kryptographie (BSI-Empfehlungen, NIST-PQC-Standards) als Migrationshinweis.

## Workflow

1. **Frage präzisieren:** Welches Verfahren / welche Suite, in welchem Kontext (TLS / IPsec / SSH / VPN)?
   Ohne Kontext lässt sich der richtige TR-02102-Teil nicht wählen.
2. **Quellen holen:** den passenden **TR-02102-Teil** (-1 als Basis + -2/-3/-4 je nach Kontext) **und** das
   **NIST-Pendant** per **WebFetch** ziehen — aktuelle Fassung, Stand/Jahr notieren.
3. **Verifizieren, dann zitieren:** erst den tatsächlichen Inhalt lesen, dann die Tabelle/den Abschnitt als
   Beleg heranziehen — nie einen Wert aus dem Gedächtnis „erinnern".
4. **Urteil fällen:** **konform** / **abzulösen (Migrationsfrist beachten)** / **verboten**, jeweils mit
   **Quelle + Teil + Tabelle/Abschnitt + Stand/Jahr**. **„belegt"** (aus TR/NIST/RFC) und **„Erfahrung"**
   (eigene Einordnung) sauber trennen.

## Anwendung auf VPN-Configs (Anknüpfpunkt für Christian)

Konkrete Config-Zeilen gegen TR-02102 bewerten:

- **OpenVPN:** zwei Ebenen, zwei TR-Teile. Der **Control-Channel** ist TLS → gegen **TR-02102-2**
  (`tls-cipher`/`tls-ciphersuites`, TLS-Version, Kurven). Die **Data-Channel-Primitive**
  (`data-ciphers`, `auth`) → gegen **TR-02102-1** (AEAD-Cipher wie `AES-256-GCM`, kein SHA1-HMAC).
  OpenVPN ist weder reines TLS noch IPsec — diese Trennung explizit machen, sonst zitiert man den
  falschen Teil.
- **IPsec:** eine Proposal-/`ike`/`esp`-Zeile gegen **TR-02102-3** (IKEv2) prüfen — Kombination aus
  Verschlüsselung, Integrität, DH-Gruppe, PFS.
- **WireGuard:** feste moderne Primitive (ChaCha20-Poly1305, Curve25519, BLAKE2s) — keine Suite-Wahl,
  daher Bewertung „by design", aber gegen die TR-02102-Aussagen zu den Einzelprimitiven einordnen.

**Typische Alt-Lasten benennen:** AES-**CBC** ohne AEAD (kein Integritätsschutz), **SHA1-HMAC**,
**DH-Gruppe 2/5** (1024/1536 bit, zu schwach), **TLS < 1.2**. Diese als „abzulösen"/„verboten" mit Beleg
markieren und die konforme Alternative nennen.

## Optional — Belege im Vault ablegen

Kernaussagen/Belege (Tabellenwerte, Migrationsfristen) unter `recherche/<slug>.md` ablegen (globale
Nutzer-Regel: Defuddle, Frontmatter mit **URL + Abrufdatum**) — über **Karin**, falls vorhanden. So bleibt
die Bewertung nachvollziehbar und die Quelle bei der nächsten TR-02102-Revision vergleichbar.

## Kooperation

**Christian** (VPN-Agent) ist der typische Fragesteller: Er delegiert die Krypto-Bewertung an bruce,
bruce liefert das **zitierfähige Urteil** (welches Primitiv/welche Suite ist nach TR-02102 konform,
abzulösen oder verboten), die **Umsetzung** in der VPN-Config macht **Christian**.
