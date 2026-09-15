{
  description = "tools — Cross-CLI-Zweitmeinung (ask/execute): die jeweils andere CLI (Codex/Claude) non-interaktiv fragen, Modell und Effort nach Stufe";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f system (import nixpkgs { inherit system; }));
      # Bewusst ohne claude/codex: die Ziel-CLI muss die auf dem Host installierte Version sein.
      runtime = pkgs: [ pkgs.jq pkgs.coreutils ];
    in
    {
      devShells = forAll (system: pkgs: {
        default = pkgs.mkShell {
          packages = runtime pkgs ++ [ pkgs.shellcheck ];
          shellHook = ''
            echo "tools devShell — scripts/ask.sh [--mode ask|execute] [--tier strong|advanced|drone] [--boost|--fast] [--target claude|codex] [--dry-run]"
            echo "claude/codex kommen vom Host-PATH, nicht aus nixpkgs"
          '';
        };
      });

      packages = forAll (system: pkgs: {
        # Wrapper `ask`: jq/coreutils vorn im PATH, claude/codex weiter vom Host-PATH.
        ask = pkgs.writeShellApplication {
          name = "ask";
          runtimeInputs = runtime pkgs;
          text = ''
            exec ${pkgs.bash}/bin/bash ${./scripts/ask.sh} "$@"
          '';
          meta.description = "Die jeweils andere CLI non-interaktiv fragen (ask read-only / execute workspace-write)";
        };
        default = self.packages.${system}.ask;
      });

      apps = forAll (system: pkgs: {
        ask = {
          type = "app";
          meta.description = "Die jeweils andere CLI non-interaktiv fragen (ask read-only / execute workspace-write)";
          program = "${self.packages.${system}.ask}/bin/ask";
        };
        default = self.apps.${system}.ask;
      });

      checks = forAll (system: pkgs: {
        # Baut den Wrapper mit, damit `nix shell`/`nix run` nicht erst beim Aufruf scheitern.
        package = self.packages.${system}.ask;
        shellcheck = pkgs.runCommand "ask-shellcheck" { nativeBuildInputs = [ pkgs.shellcheck ]; } ''
          shellcheck ${./scripts/ask.sh} ${./tests/ask-test.sh}
          touch $out
        '';
        # Offline: Stub-codex/claude im PATH, keine echten CLI-Aufrufe.
        ask-stubs = pkgs.runCommand "ask-stubs" { nativeBuildInputs = runtime pkgs ++ [ pkgs.bash ]; } ''
          bash ${./tests/ask-test.sh} ${./scripts/ask.sh}
          touch $out
        '';
      });
    };
}
