{
  description = "Philharmonie: getrennte Agentenrollen mit prüfbaren Projektzuständen";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f (import nixpkgs { inherit system; }));
      python = pkgs: pkgs.python3.withPackages (ps: [ ps.jsonschema ps.pyyaml ]);
      runtime = pkgs: [ (python pkgs) pkgs.git pkgs.bubblewrap pkgs.coreutils ];
      source = pkgs: pkgs.lib.cleanSourceWith {
        src = ./.;
        filter = path: type:
          pkgs.lib.cleanSourceFilter path type
          && builtins.baseNameOf path != "__pycache__"
          && !(pkgs.lib.hasSuffix ".pyc" path);
      };
    in
    {
      packages = forAll (pkgs: {
        default = pkgs.stdenvNoCC.mkDerivation {
          pname = "philharmonie";
          version = "0.1.0";
          src = source pkgs;
          nativeBuildInputs = [ pkgs.makeWrapper ];
          installPhase = ''
            mkdir -p $out/share/philharmonie $out/bin
            cp -r . $out/share/philharmonie/
            makeWrapper ${python pkgs}/bin/python3 $out/bin/philharmonie \
              --add-flags "$out/share/philharmonie/scripts/philharmonie.py" \
              --set PYTHONDONTWRITEBYTECODE 1 \
              --prefix PATH : ${pkgs.lib.makeBinPath (runtime pkgs)}
          '';
          meta = {
            description = "Projektaufträge mit getrennten Agentenrollen und persistentem Zustand";
            platforms = systems;
            license = pkgs.lib.licenses.mit;
          };
        };
      });
      apps = forAll (pkgs: {
        default = {
          type = "app";
          meta.description = "Philharmonie: Aufträge planen, umsetzen und unabhängig prüfen";
          program = "${self.packages.${pkgs.stdenv.hostPlatform.system}.default}/bin/philharmonie";
        };
      });
      devShells = forAll (pkgs: {
        default = pkgs.mkShell { packages = runtime pkgs ++ [ pkgs.shellcheck ]; };
      });
      checks = forAll (pkgs: {
        tests = pkgs.runCommand "philharmonie-tests" {
          nativeBuildInputs = runtime pkgs;
        } ''
          export HOME=$TMPDIR/home
          mkdir -p "$HOME"
          export PYTHONDONTWRITEBYTECODE=1
          python3 -m unittest discover -s ${source pkgs}/tests -v
          touch $out
        '';
      });
    };
}
