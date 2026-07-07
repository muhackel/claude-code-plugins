# nixie — Backlog

---
## Aus Auto-Memory migriertes User-Feedback (2026-07-06) — in nix-deploy-Skill encodieren
> Diese drei Punkte stammen aus konsolidierten Feedback-Memorys und werden **provisorisch global** in `~/.claude/CLAUDE.md` (Sektion „Nix-Builds zur Laufzeit") gehalten, bis der Skill sie trägt. Nach dem Encodieren dort entfernen.

### 🔴 OFFEN: Long-Running-Builds nie durch tail/head/grep pipen (User verliert Live-Visibility)
`nix build`/`nixos-rebuild`/`nix flake check` (und `cargo build`/`make`) **nie** durch `| tail -N`/`| head`/`| grep` pipen (auch nicht `2>&1 | tail`), **nie** `run_in_background` — der User beobachtet den Build live im Terminal; jede Pipe/jeder Background-Job macht ihn blind, und ein erneuter sichtbarer Lauf kostet die Wartezeit doppelt. **Fix-Richtung:** `skills/nix-deploy/SKILL.md` → Build-Kommandos im Vordergrund, ggf. `-L`; Errors danach aus dem Drv-Log (`nix log <drv>`); bei sehr langen Läufen mit User klären, ob er selbst rebuildet (`nixos-rebuild switch --sudo`).

### 🔴 OFFEN: RAM-bewusste Drosselung als konkrete Heuristik (ergänzt die BEHOBEN-Einträge unten)
Die max-jobs-Drosselung ist im Skill adressiert (siehe ✅ unten), aber die **konkrete RAM-Heuristik** fehlt noch explizit: vor schweren Builds `free -h`; `--max-jobs = (frei − Puffer) / ~6 GiB pro schwerem Job`; `--cores` **nicht** beschneiden; `--keep-going` nur auf gedrosselten Läufen. Beispiel-Vorfall (2026-06-14): ungedrosselter `nix flake check -L --keep-going` als verwaister Background-Job → OOM-Killer mähte Desktop-Apps + den nix-Prozess selbst trotz 46 GiB. **Fix-Richtung:** Heuristik in die „Resource-aware Build-Drosselung"-Sektion aufnehmen.

### 🔴 OFFEN: Host-Erreichbarkeit LAN-first (nackter Hostname), -wifi nur Fallback
Beim Erreichen/Deployen von Hosts zuerst die LAN-Adresse testen (nackter Hostname ohne Suffix bzw. `<host>.local`), `<host>-wifi` nur wenn LAN nicht erreichbar — LAN ist schneller/stabiler für Remote-Builds und `--target-host`. Namensschema (verifiziert 2026-06-06): `hal9000`→10.0.1.3 (LAN) / `hal9000-wifi`→10.0.1.4; `bfg9000-wifi`→10.0.1.7; `<host>.local` → LAN-IP. **Fix-Richtung:** In der Host-/Target-Auswahl des Skills einen Reachability-Check `for h in <host> <host>-wifi; do ping -c1 -W2 "$h" && break; done` vorsehen und den gefundenen Namen für ssh/`--target-host` nutzen.

---
## 🔴 OFFEN (2026-06-15): Kein Weitersprechen mit laufender Nixie → Neustart erzwingt Verwaisung der Erstinstanz

**Symptom:** Erste Nixie-Instanz läuft als Subagent und hat einen langen Export gestartet. Der Hauptloop
will ihr eine Folge-Entscheidung durchgeben (`SendMessage` an die Agenten-ID), aber das Tool ist in der
Umgebung nicht verfügbar. Workaround war, eine **zweite** Nixie zu starten. Die erste lief derweil
führungslos weiter und verwaiste nach ~10 min — und riss dabei den von ihr gestarteten Export ab.

**Ursache:** Zwei verkettete Lücken. (1) `SendMessage`/Continue-an-Agent steht nicht zuverlässig bereit,
also lässt sich eine in Arbeit befindliche Nixie nicht steuern — man muss neu starten. (2) Der Neustart
ändert nichts an der bereits führungslos laufenden Erstinstanz; deren Detach (~10 min) killt den Job.

**Fix-Richtung:** Nixie/Skill so gestalten, dass langlaufende Arbeit gar nicht erst *in* der Subagenten-
Instanz startet (siehe nix-deploy-Eintrag unten) — dann ist „mit ihr weitersprechen" nicht nötig. Falls
Steuerung doch gebraucht wird: dokumentieren, dass der Hauptloop NICHT eine zweite Instanz parallel zur
noch laufenden ersten starten darf (alte erst sauber beenden/abwarten).

## 🔴 OFFEN (2026-06-15): nix-deploy v0.2.3-Fix greift nicht für lange Exports / `nix copy` auf USB

**Symptom:** Trotz des v0.2.3-Fixes hat die Nixie-Subagenten-Instanz einen langen `nix-store --export | zstd`
(44 GiB Closure → ~12 GiB auf exFAT-USB) **selbst** gestartet statt ihn an den Hauptloop zurückzugeben.
Sie verwaiste nach ~10 min, die Pipe brach mittendrin ab → korruptes Archiv (`zstd -t`: *premature end*),
plus eine zu früh erzeugte (falsche) `.sha256`.

**Ursache:** Der v0.2.3-Text adressiert primär *kompilier-schwere* Schritte (dry-build/Drosselung). Ein
reiner Export/`nix copy` ist nicht CPU-/Build-lastig, fällt aber unter dieselbe Detach-Falle (Dauer ≫ 120 s).
Die „delegieren statt verwaisen"-Regel wird auf Exporte nicht angewandt.

**Fix-Richtung:** In `skills/nix-deploy/SKILL.md` die Delegations-Regel explizit auf **jeden** langlaufenden
Schritt ausweiten — nicht nur Builds, sondern auch `nix-store --export`/`nix copy`/Archiv-Kompression auf
externe Medien. Kriterium = *Wanduhr-Dauer > ~120 s*, nicht *„ist es ein Build"*. Bei Export zusätzlich:
`.sha256` erst NACH erfolgreichem Abschluss + Integritätscheck (`zstd -t`) erzeugen, `set -euo pipefail`
(pipefail!), damit ein abgebrochener Pipe hart fehlschlägt statt ein Teilarchiv zu hinterlassen.

## 🔴 OFFEN (2026-06-15): nix-deploy liefert untaugliche nixos-rebuild-ng-Flags (`--build-host localhost`, `-S`)

**Symptom:** Der von Nixie gelieferte Remote-Deploy-Befehl scheiterte zweimal an Flags:
- `--build-host localhost` erzwingt eine echte SSH-Verbindung zu localhost → scheitert am veralteten
  localhost-Eintrag in `~/.ssh/known_hosts` (*Host key changed*). Für „lokal bauen" ist `--build-host`
  schlicht überflüssig (Default = nativer lokaler Build ohne SSH).
- `-S` / `--ask-elevate-password` erzwingt einen **interaktiven** Passwort-Prompt — im non-interaktiven
  Hauptloop unbedienbar, selbst wenn auf dem Target passwordless sudo verfügbar ist.

**Ursache:** Skill kennt die nixos-rebuild-ng-Semantik (Python-Rewrite) nicht: `-S` = Prompt erzwingen
(nicht „sudo nutzen"); `--build-host localhost` = SSH-Loopback statt nativ.

**Fix-Richtung:** In `skills/nix-deploy/SKILL.md` Remote-Deploy-Vorlage korrigieren:
`nixos-rebuild switch --flake .#HOST --target-host muhackel@<host> --elevate=sudo --use-substitutes`
— **kein** `--build-host` für lokalen Build, **kein** `-S`; `--elevate=sudo` nutzt passwordless sudo ohne
Prompt. Vorab-Check `ssh -o BatchMode=yes muhackel@<host> 'sudo -n true'`. `--max-jobs` nur wenn dry-build
echte heavy-Builds zeigt.

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
sudo (`switch --sudo` läuft beim User passwortlos).

## ✅ BEHOBEN (2026-06-14): `--max-jobs`-Drosselung greift nicht bei `nix flake check`

**Fix umgesetzt** in `skills/nix-deploy/SKILL.md`: `flake check`-Regel (Z. 19 ff.) um die
Drosselungs-Pflicht erweitert (defensiv als *heavy*, `--max-jobs`/`--cores` direkt am `nix`-Aufruf,
Vordergrund statt Background, `--keep-going` nur gedrosselt); Drosselungs-Sektion auf „hängt am
Kompilieren, nicht am Befehlsnamen" festgenagelt und `flake check` als Build-Quelle aufgenommen.
Anlass: realer OOM-Kill auf SPIELKISTE (Exit 137, ungedrosselter `flake check` über alle Hosts).

<details><summary>ursprüngliche Bug-Beschreibung</summary>

### BUG: `--max-jobs`-Drosselung greift nicht bei `nix flake check`

**Symptom:** User gibt explizit ein Job-Limit vor (z.B. „2 jobs max"). Trotzdem saturiert
die Maschine während des Checks komplett (YouTube wird zur Diashow — CPU/IO-Druck, nicht Swap).

**Ursache:** Die resource-aware Drosselung (`skills/nix-deploy/SKILL.md`, Sektion „Resource-aware
Build-Drosselung", Z. 90–126) hängt `--max-jobs`/`--cores` nur an `nixos-rebuild` und `nix build`.
Die `nix flake check`-Regel (Z. 19–23) erwähnt `--max-jobs` gar nicht.

Bei diesem Multi-Host-Flake baut aber **`nix flake check`** die 467 `checks`-Outputs
(KDE/Plasma, Akonadi, webkitgtk …) lokal in den Store — das ist der eigentlich teure,
build-erzeugende Schritt. Läuft er ungedrosselt mit Default = alle Kerne, ist der Store beim
nachfolgenden `nixos-rebuild` längst warm. `--max-jobs 2` am Rebuild ist dann wirkungslos
(„so nützlich wie ein Furunkel").

**Fix:** `--max-jobs <n>` (bzw. `--option max-jobs <n>`, da `nix flake check` ein `nix`-Command
ist, kein `nixos-rebuild`) auch an `nix flake check` durchreichen. Generell: das Throttle gehört
an **jeden** build-erzeugenden `nix`-Aufruf, nicht nur an den finalen `rebuild`-Schritt.

- `nix flake check` → `nix flake check --max-jobs <n> [--cores <m>]`
- Drosselungslogik (Z. 90–126) so erweitern, dass sie für `nix flake check` genauso greift wie
  für `nixos-rebuild`/`nix build`.
- `nix flake check`-Regel (Z. 19–23) um den max-jobs-Hinweis ergänzen.

**Constraint beachten:** `--cores` nicht beschneiden (User-Feedback: RAM-bewusst drosseln über
`--max-jobs`, Cores in Ruhe lassen).

</details>
