# nixie — Backlog

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
