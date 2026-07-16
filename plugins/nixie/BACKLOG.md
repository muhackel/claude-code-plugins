# nixie — Backlog

Offene Punkte oben, behobene darunter (jüngste zuerst). Behobene Einträge verweisen auf die
Skill-Sektion, die sie encodiert.

---

## ✅ BEHOBEN (2026-07-16): Resource-aware Drosselung — konkrete Heuristik encodiert

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md`, Sektion „Resource-aware Build-Drosselung":
- **`--max-jobs` aus freiem RAM**: `MJ = floor(MemAvailable / 16)` — ~1 schwerer Job pro 16 GiB
  *available* (NICHT `MemTotal`, NICHT die `free`-Spalte; buff/cache ist reclaimable). `free -h` als
  Preflight vor schweren Builds.
- **`--cores` = 15/16 der verbauten Kerne, abgerundet**: `CO = floor(nproc * 15/16)` (32→30, 20→18,
  16→15, 4→3). Belegt via `man nix.conf` (cores = NIX_BUILD_CORES **pro Job**, unabhängig von max-jobs).
- Alte, missverständliche Formel (`mem/20`, `CO = nproc − MJ`) und die „`--cores` nicht beschneiden"-
  Doktrin ersetzt. Live erprobter Betriebspunkt spielkiste: `--max-jobs 2 --cores 30` (keine 100-%-Last).

Diese Punkte lagen zuvor provisorisch in `~/.claude/CLAUDE.md` (Sektion „Nix-Builds zur Laufzeit").
Follow-up (globale User-Datei, separat): dort die drei provisorischen Bullets austragen und die Zeile
„`--cores` nicht beschneiden" durch die neue Regel ersetzen.

## ✅ BEHOBEN (2026-07-16): Long-Running-Builds nie pipen/backgrounden

Bereits im Skill: Sektion „Build-Sichtbarkeit (kein tail, kein Background)" — `nix build`/`nixos-rebuild`/
`nix flake check` (und `cargo build`/`make`) im Vordergrund, kein `| tail`/`| head`/`| grep`, kein
`run_in_background`; Errors nach dem Lauf aus `nix log <drv>`.

## ✅ BEHOBEN (2026-07-16): Host-Erreichbarkeit LAN-first

Bereits im Skill: Sektion „Schnellste Kiste wählen (zur Laufzeit)" — LAN vor WiFi, dynamischer
Reachability-Check (`for h in <host> <host>-wifi; do ping -c1 -W2 "$h" && break; done`), nie feste IPs.

## ✅ BEHOBEN (2026-07-16): Delegations-Regel auf jeden Long-Runner > ~120 s (nicht nur Builds)

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md`, Sektion „Lange Builds als Subagent — delegieren statt
verwaisen": Kriterium von „kompilier-schwer" auf **Wanduhr-Dauer > ~120 s** umgestellt — erfasst jetzt
auch reine I/O-Long-Runner (`nix-store --export`/`nix copy` großer Closures, `zstd`-Kompression auf
externe/langsame Medien). **Export-Integrität** ergänzt: `set -euo pipefail` (pipefail maskiert sonst
einen abgebrochenen Export vor grünem `zstd`), `.sha256` erst nach `zstd -t`-Check.

## ✅ BEHOBEN (2026-07-16): Kein Weitersprechen mit laufender Nixie → Zweitinstanz-Verbot

**Fix umgesetzt** in derselben Sektion: Regel ergänzt, **nie eine zweite Nixie zu starten, solange die
erste noch läuft** (die verwaist sonst führungslos und reißt ihren Job ab). Die „delegieren statt
verwaisen"-Regel macht „mit der laufenden Nixie weitersprechen" (fehlendes `SendMessage`) ohnehin unnötig.

## ✅ BEHOBEN (2026-07-16): Untaugliche nixos-rebuild-ng-Flags (`--build-host localhost`, `-S`)

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md`, Sektionen „nixos-rebuild (ng) — CLI-Form" und
Eskalationsstufe 4 (verifiziert via `nixos-rebuild --help`):
- `-S`/`--ask-elevate-password` erzwingt einen interaktiven Prompt → im Hauptloop unbedienbar. Für
  passwortloses Remote-sudo `--elevate=sudo` **ohne** `-S`; Vorab-Check `ssh -o BatchMode=yes user@<ziel> 'sudo -n true'`.
- `--build-host localhost` = SSH-Loopback (scheitert an `known_hosts`); für lokalen Build `--build-host`
  weglassen. Remote-Deploy-Vorlage entsprechend korrigiert.

## ✅ BEHOBEN (2026-06-14): Subagent verwaist bei langen Builds (flake check / switch / nix copy)

**Symptom:** Nixie startet als Subagent einen langen Build; die Harness detacht ihn nach ~120 s und
beendet den Subagent-Turn. Der Subagent wird nicht wieder aufgeweckt → Build läuft führungslos weiter,
Folgeschritte (Auswertung, commit, switch) bleiben liegen. Trat zweimal in Folge auf (flake check, Deploy).

**Ursache:** Subagent-Lebenszyklus endet mit dem Turn; ~120 s Auto-Backgrounding (Bash-Default-Timeout).
Belegt via claude-code-guide aus der offiziellen Doku (Subagenten = selbstbegrenzte Tasks mit Summary;
lange Arbeit gehört zum Hauptagenten/Orchestrator).

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md` (v0.2.3): neue Sektion „Lange Builds als Subagent —
delegieren statt verwaisen" — kompilier-schwere Schritte vorbereiten (dry-build, Drosselung, exakter
Befehl) und an Hauptloop/User zurückgeben statt selbst durchzuziehen; nur sicher <120 s terminierende
Schritte selbst. Verweis an der flake-check-Regel ergänzt. Klargestellt: Grund ist die Build-Dauer, nicht
sudo (`switch --sudo` läuft beim User passwortlos). *(2026-07-16 auf jeden Long-Runner > 120 s verbreitert, s.o.)*

## ✅ BEHOBEN (2026-06-14): `--max-jobs`-Drosselung greift nicht bei `nix flake check`

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md`: `flake check`-Regel um die Drosselungs-Pflicht
erweitert (defensiv als *heavy*, `--max-jobs`/`--cores` direkt am `nix`-Aufruf, Vordergrund statt
Background, `--keep-going` nur gedrosselt); Drosselungs-Sektion auf „hängt am Kompilieren, nicht am
Befehlsnamen" festgenagelt und `flake check` als Build-Quelle aufgenommen. Anlass: realer OOM-Kill auf
SPIELKISTE (Exit 137, ungedrosselter `flake check` über alle Hosts).

<details><summary>ursprüngliche Bug-Beschreibung</summary>

### BUG: `--max-jobs`-Drosselung greift nicht bei `nix flake check`

**Symptom:** User gibt explizit ein Job-Limit vor (z.B. „2 jobs max"). Trotzdem saturiert
die Maschine während des Checks komplett (YouTube wird zur Diashow — CPU/IO-Druck, nicht Swap).

**Ursache:** Die resource-aware Drosselung hängt `--max-jobs`/`--cores` nur an `nixos-rebuild` und
`nix build`. Die `nix flake check`-Regel erwähnt `--max-jobs` gar nicht.

Bei diesem Multi-Host-Flake baut aber **`nix flake check`** die 467 `checks`-Outputs
(KDE/Plasma, Akonadi, webkitgtk …) lokal in den Store — das ist der eigentlich teure,
build-erzeugende Schritt.

**Fix:** `--max-jobs <n>` auch an `nix flake check` durchreichen. Das Throttle gehört an **jeden**
build-erzeugenden `nix`-Aufruf, nicht nur an den finalen `rebuild`-Schritt.

</details>
