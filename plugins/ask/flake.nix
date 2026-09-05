{
  description = "ask — Cross-CLI-Zweitmeinung: die jeweils andere CLI (Codex/Claude) non-interaktiv mit dem Flaggschiffmodell fragen";

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
            echo "ask devShell — scripts/ask.sh [--mode ask|execute] [--target claude|codex] [--dry-run]"
            echo "claude/codex kommen vom Host-PATH, nicht aus nixpkgs"
          '';
        };
      });

      apps = forAll (system: pkgs: {
        ask = {
          type = "app";
          meta.description = "Die jeweils andere CLI non-interaktiv fragen (ask read-only / execute workspace-write)";
          program = toString (pkgs.writeShellScript "ask" ''
            export PATH=${pkgs.lib.makeBinPath (runtime pkgs)}:$PATH
            exec ${pkgs.bash}/bin/bash ${./scripts/ask.sh} "$@"
          '');
        };
        default = self.apps.${system}.ask;
      });

      checks = forAll (system: pkgs: {
        shellcheck = pkgs.runCommand "ask-shellcheck" { nativeBuildInputs = [ pkgs.shellcheck ]; } ''
          shellcheck ${./scripts/ask.sh}
          touch $out
        '';
      });
    };
}
