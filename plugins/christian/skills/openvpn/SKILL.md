---
name: openvpn
description: "Tiefen-Skill OpenVPN: PKI-Aufbau (easy-rsa 3), tls-crypt/tls-auth-Control-Channel-Härtung, topology subnet, Server-/Client-Config, client-config-dir + iroute für Site-to-Site, Krypto-Härtung (data-ciphers AEAD, tls-version-min, ECDH, remote-cert-tls), systemd-Integration und das häufige Troubleshooting (Routing-Push, MTU/mssfix, TLS-Handshake, Zertifikatsgültigkeit). Nutzen bei jedem OpenVPN-Setup, -Review oder -Störungsbild. Optionen gegen openvpn(8) der Zielversion verifizieren; Krypto-Bewertung über bruce/gs-krypto (TR-02102)."
---

# OpenVPN — Kern-Expertise

**Christians Heimspiel.** Dichte Praktiker-Landkarte mit Quellen-Anker auf `openvpn(8)`. Optionen ändern
sich zwischen 2.4/2.5/2.6 (z.B. `--cipher` deprecated zugunsten `--data-ciphers` in 2.6) — die **konkrete
Version** klären und unsichere Optionen gegen die Manpage der Zielversion verifizieren
(via `vpn-reference`). Krypto-Bewertung ist opinionated (unten), die Freigabe holt `bruce` aus TR-02102.

## PKI-Aufbau (easy-rsa 3)

Reihenfolge — jeder Schritt erzeugt Material, das der nächste braucht:

| Schritt | Kommando (easy-rsa 3) | Ergebnis |
|---------|-----------------------|----------|
| PKI init | `easyrsa init-pki` | leere PKI-Struktur |
| CA erzeugen | `easyrsa build-ca` (`nopass` optional) | `ca.crt` + CA-Key (offline halten) |
| Server-Zert | `easyrsa gen-req <name>` → `easyrsa sign-req server <name>` | Server-Key + -Zert |
| Client-Zert | `easyrsa gen-req <cn>` → `easyrsa sign-req client <cn>` | je Client eigener Key + Zert |
| DH-Params | `easyrsa gen-dh` | `dh.pem` (nur bei klassischem DH-KE nötig) |
| Widerruf | `easyrsa revoke <cn>` → `easyrsa gen-crl` | `crl.pem` |

- **ECDH statt DH:** Mit einer EC-CA / ECDH-Kurve (`dh none` + `ecdh-curve`) entfällt `dh.pem`. Exakte
  Optionsnamen per `openvpn(8)` verifizieren.
- **CRL:** `crl-verify crl.pem` serverseitig einbinden, sonst wirken Widerrufe nicht. CRL läuft ab —
  regelmäßig neu erzeugen.
- **CA-Key offline.** Nie auf dem VPN-Server. Kompromittierte CA = alle Zertifikate wertlos.

## Control-Channel-Härtung: tls-crypt vs. tls-auth

Beide legen einen zusätzlichen PSK über den TLS-Control-Channel — schützt gegen DoS/Portscan und
unauthentisierte Handshakes (nur wer den Key hat, kommt überhaupt zum TLS-Handshake).

| Option | Wirkung | Bewertung |
|--------|---------|-----------|
| `tls-auth ta.key` | **HMAC-signiert** den Control-Channel | älter; Handshake bleibt sichtbar |
| `tls-crypt ta.key` | **verschlüsselt + authentisiert** den Control-Channel | bevorzugt gegenüber tls-auth |
| `tls-crypt-v2` | **pro-Client eigener** tls-crypt-Key | **bevorzugt** — einzeln widerrufbar, kein geteiltes Secret |

Anti-Pattern: **gar keine** Control-Channel-Härtung. Der Server ist dann für jeden scanbar und
handshake-belastbar.

## topology subnet (nicht net30)

`topology subnet` verwenden — moderne, saubere Adressierung (ein IP pro Client aus dem Pool, keine
/30-Verschwendung). `topology net30` ist Alt-Default aus Kompatibilitätsgründen und ein Anti-Pattern für
Neubauten (vergeudet Adressen, tap-untypisch, Legacy-Windows-Artefakt).

## Server- vs. Client-Config

**Server (Kern):** `dev tun` (L3-Routing; `tap` nur wenn L2/Bridging wirklich nötig), `proto udp`
(TCP-over-TCP-Meltdown vermeiden), `port 1194`, `server 10.8.0.0 255.255.255.0` (setzt Pool +
`topology`), `push "route ..."` für erreichbare Subnetze, `push "dhcp-option DNS ..."`,
`keepalive 10 120`, `persist-key`/`persist-tun`.

**Client (Kern):** `client`, `dev tun`, `proto udp`, `remote <host> <port>`, `nobind`,
`remote-cert-tls server`, `persist-key`/`persist-tun`, Zertifikat/Key/CA (oder inline `<ca>...`).

## Client-spezifisches Routing: iroute vs. push route

Der klassische Verwechslungspunkt — die Richtung entscheidet:

- **`push "route <netz>"`** (Server → Client): sagt dem Client, dieses Netz **durch den Tunnel zum
  Server** zu routen. Das ist die Route **zum** Server-seitigen LAN.
- **`iroute <netz>`** in einer `client-config-dir`-Datei (CCD): sagt dem **Server**, dass dieses Netz
  **hinter diesem Client** liegt (Site-to-Site). Ohne `iroute` findet der Server das Client-LAN nicht.
- **Site-to-Site hinter einem Client** braucht **beides**: `iroute` im CCD (Server lernt das Netz vom
  Client) **plus** eine `route`-Direktive in der Server-Config (kernel-Route in die tun) **plus** ggf.
  `push route` an andere Clients, damit die es auch erreichen.

Merksatz: `push route` = „so kommst **du** zu **mir**"; `iroute` = „dieses Netz liegt hinter **dir**".

## Krypto-Härtung (opinionated)

| Parameter | Empfehlung | Warum |
|-----------|-----------|-------|
| `data-ciphers` | `AES-256-GCM:AES-128-GCM` (+ `CHACHA20-POLY1305`) | **AEAD** — Verschlüsselung + Integrität in einem |
| `tls-version-min` | `1.2` (besser 1.3, wenn Build/Peer es tragen) | TLS 1.0/1.1 ausschließen |
| `tls-ciphersuites` / `tls-cipher` | moderne Suites (TLS 1.3: `TLS_AES_256_GCM_SHA384` …) | schwache KEX/Cipher raus |
| `ecdh-curve` | moderne Kurve (z.B. `secp384r1`/`prime256v1`) | statt schwachem klassischem DH |
| `auth` | `SHA256` (bei AEAD-data-ciphers nur Control-Channel-HMAC) | kein SHA1 |
| `remote-cert-tls server` (Client) | Pflicht | verhindert Server-Impersonation via Client-Zert |
| `verify-x509-name <name> ...` | gezielt | bindet an erwarteten CN/SAN, nicht „irgendein gültiges Zert" |

Exakte Suite-Strings und deren Verfügbarkeit gegen `openvpn(8)` der Zielversion prüfen. Ob die gewählten
Parameter **stark genug** sind (Schlüssellänge, Kurve, Hash), bewertet `bruce` (`gs-krypto`, TR-02102) —
nicht aus dem Gedächtnis freigeben.

## systemd-Integration

- **Server:** `systemctl start openvpn-server@<config>` (Config in `/etc/openvpn/server/<config>.conf`).
- **Client:** `systemctl start openvpn-client@<config>` (Config in `/etc/openvpn/client/<config>.conf`).
- Die instanziierten Units (`@`) ersetzen das alte `openvpn@`-Schema. Exakte Pfade/Unit-Namen
  distributionsabhängig — per `systemctl cat openvpn-server@` / Manpage verifizieren.

## Troubleshooting (häufig)

- **Push-Route kommt nicht an:** Client ignoriert `push route`? Prüfen ob `pull` (implizit bei `client`)
  aktiv ist, ob eine `route-nopull`/Firewall die Route verwirft, und ob die Route serverseitig überhaupt
  gepusht wird (`--verb 4`, Log auf „SENT CONTROL … PUSH_REPLY").
- **MTU/Fragmentierung:** großer Transfer hängt, kleiner geht → MTU-Problem. `tun-mtu`,
  `mssfix` (klemmt TCP-MSS, Default-Verhalten versionsabhängig — verifizieren), ggf. `fragment` (nur
  UDP). PMTU-Blackhole (ICMP-Frag-Needed geblockt) unterwegs ausschließen.
- **TLS-Handshake schlägt fehl:** `TLS Error: TLS handshake failed` → Ursachen: tls-crypt/tls-auth-Key
  stimmt nicht überein (eine Seite fehlt/falsch), Cipher-/TLS-Version-Mismatch, Zertifikat abgelaufen
  oder falsche CA. Mit `--verb 4` (bis 6) beide Enden vergleichen.
- **Zeit/Zertifikatsgültigkeit:** falsche Systemzeit → Zert „not yet valid"/„expired". NTP prüfen.
- **`--verb`:** Log-Level hochdrehen (`4` für Diagnose, `6+` für Handshake-Details), danach zurück.

## Anti-Patterns

- Veralteter `cipher BF-CBC` oder `AES-128-CBC` **ohne AEAD** — kein Integritätsschutz, angreifbar.
- **Kein** `tls-crypt`/`tls-auth` — Server offen für Scan/DoS und unauthentisierte Handshakes.
- **Kompression über den Tunnel** (`comp-lzo`, `compress lz4`/`lzo`) — **VORACLE** (CRIME-Klasse):
  Kompression **vor** Verschlüsselung erlaubt das Ausleiten von Klartext-Anteilen. Ersatzlos raus, auf
  **beiden** Seiten. OpenVPN hat `--comp-lzo` deprecatet — gegen das VORACLE-Advisory bzw. `openvpn(8)`
  (`--compress`/`--allow-compression`) der Zielversion verifizieren.
- `topology net30` bei Neubau — Adressverschwendung, Legacy.
- Fehlendes `remote-cert-tls server` am Client — jedes von der CA signierte (auch Client-)Zert kann den
  Server spielen → MITM.
- **`duplicate-cn` bei Site-to-Site** — bricht die CCD/`iroute`-Zuordnung (die braucht einen eindeutigen
  CN pro Client) und lässt ein geleaktes Zert beliebig oft parallel laufen. Nur für anonyme
  Road-Warrior-Pools mit gleichem CN je legitim — nie bei fester Standort-Kopplung.
- CA-Key auf dem VPN-Server liegen lassen.

## Read-only zuerst

Config-Entwurf und Review sind read-only. Tunnel hochziehen / Unit starten / Firewall anpassen läuft über
die `wan-link`/`router-appliance`-Doktrin (Bestätigung + Rollback-Netz), nie beiläufig.
